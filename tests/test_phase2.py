"""Pipeline validation uses cached real control responses; never calls a network."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase2_collect as c


class Phase2Tests(unittest.TestCase):
    def test_pinned_inputs_and_selection(self):
        heights, rows = c.inputs()
        self.assertEqual(len(heights), 21953)
        sample = json.loads((c.OUT / "selection.json").read_text())
        self.assertEqual(len(sample["controls"]), 3000)
        self.assertEqual(len(set(sample["controls"])), 3000)
        self.assertFalse(set(heights) & set(sample["controls"]))
        self.assertFalse(set(heights) & set(sample["boundary"]))

    def test_real_controls(self):
        path = c.OUT / "cache/chain.sqlite3"
        if not path.exists():
            self.skipTest("Raw local cache unavailable; run controls collector first")
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        for h, expected in c.CONTROLS.items():
            cb = json.loads(db.execute("SELECT data FROM results WHERE kind='coinbase' AND height=?", (h,)).fetchone()[0])
            header = json.loads(db.execute("SELECT data FROM results WHERE kind='header' AND height=?", (h,)).fetchone()[0])
            raw = db.execute("SELECT body_zlib,sha256 FROM responses WHERE id=?", (cb["tx_response"]["response_id"],)).fetchone()
            body = zlib.decompress(raw[0])
            self.assertEqual(c.sha(body), raw[1])
            txs = json.loads(body)
            self.assertEqual(c.txid_from_json(txs[0]), cb["txid"])
            self.assertEqual(c.merkle_root([t["txid"] for t in txs]), header["merkle_root"])
            self.assertEqual(c.check_header(header), header["header_hex"])
            self.assertEqual(cb["value_sats"], expected)
            self.assertTrue(cb["pubkey_match"])
            self.assertEqual(cb["scriptpubkey"], "41" + cb["csv_pubkey"] + "ac")
        db.close()

    def test_successful_cache_replay_never_refetches(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, "OUT", Path(tmp)):
            store = c.Store(3)
            body = b'{"verified":true}'
            with store.db:
                store.db.execute("INSERT INTO responses(height,endpoint,host,attempt,fetched_at,status,headers,sha256,body_zlib) VALUES(?,?,?,?,?,?,?,?,?)", (2817, "/test", c.HOSTS[0], 1, "2026-09-27", 200, "{}", c.sha(body), zlib.compress(body)))
            with patch("urllib.request.urlopen", side_effect=AssertionError("network must not be called")):
                self.assertEqual(store.fetch(2817, "/test")[0], {"verified": True})
                self.assertEqual(store.fetch(2817, "/test")[0], {"verified": True})
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0], 1)
            store.db.close()

    def test_extra_nonce_parser(self):
        self.assertEqual(c.extra_nonce("04ffff001d020001")["extra_nonce"], 256)
        self.assertEqual(c.extra_nonce("04ffff001d0181")["extra_nonce"], -1)
        self.assertIsNone(c.extra_nonce("04ffff001d02ff")["extra_nonce"])
        self.assertEqual(c.extra_nonce("04ffff001d51")["extra_nonce"], 1)

    def test_bulk_controls_equal_direct_responses(self):
        path = c.OUT / "cache/chain.sqlite3"
        if not path.exists():
            self.skipTest("Local cache unavailable")
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        cached = db.execute("SELECT body_zlib FROM responses WHERE height=2817 AND endpoint LIKE 'POST /scripthashes/txs %' AND status=200").fetchone()
        if not cached:
            self.skipTest("Bulk controls probe unavailable")
        bulk = json.loads(zlib.decompress(cached[0]))
        self.assertEqual({tx["status"]["block_height"] for tx in bulk}, set(c.CONTROLS))
        for tx in bulk:
            h = tx["status"]["block_height"]
            direct = json.loads(db.execute("SELECT data FROM results WHERE kind='coinbase' AND height=?", (h,)).fetchone()[0])
            self.assertEqual(c.txid_from_json(tx), direct["txid"])
            self.assertEqual(tx["vout"][0]["scriptpubkey"], direct["scriptpubkey"])
            self.assertEqual(tx["vout"][0]["value"], c.CONTROLS[h])
            self.assertEqual(tx["vin"][0]["scriptsig"], direct["scriptsig"])
        db.close()

    def test_bulk_omissions_force_direct_lookup(self):
        from unittest.mock import MagicMock
        store = MagicMock()
        store.get.return_value = None
        store.fetch.return_value = ([], {"response_id": 1})
        _, rows = c.inputs()
        with patch.object(c, "coinbase") as direct, patch.object(c, "inclusion") as proof:
            c.bulk_coinbases(store, list(c.CONTROLS), rows)
        self.assertEqual([call.args[1] for call in direct.call_args_list], list(c.CONTROLS))
        self.assertEqual(proof.call_count, 4)


if __name__ == "__main__":
    unittest.main()
