import csv
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase2_bigquery import BigQuery, OUT, heights_parameter


class BigQueryEvidenceTests(unittest.TestCase):
    def test_smoke_cache_replay_without_auth_or_network(self):
        sql = (OUT / "sql/coinbases.sql").read_text()
        heights = [1, 3, 4, 264, 2817, 10000, 19863, 23079, 28507, 49973]
        with patch.object(BigQuery, "auth", side_effect=AssertionError("must not authenticate")), patch("urllib.request.urlopen", side_effect=AssertionError("must not query")):
            rows = BigQuery().query("smoke", sql, heights_parameter(heights), dry=False)
        self.assertEqual(len(rows), 10)
        self.assertEqual(next(r for r in rows if r["height"] == "2817")["output_value_raw"], "5201000000")

    def test_complete_evidence_and_live_spenders(self):
        summary = json.loads((OUT / "summary.json").read_text())
        self.assertEqual(summary["counts"]["listed"], 21953)
        with (OUT / "verification.csv").open(newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len({r["height"] for r in rows}), 21953)
        self.assertTrue(all(r["txid_reconstructed"] == "True" for r in rows))
        with (OUT / "spend_status_all.csv").open(newline="") as f:
            statuses = list(csv.DictReader(f))
        self.assertEqual(len(statuses), 21953)
        hits = [r for r in statuses if r["dataset_status"] == "spent"]
        self.assertEqual(len(hits), summary["counts"]["spend_hits"])
        self.assertTrue(all(r["live_confirmed_spend"] == "True" for r in hits))


if __name__ == "__main__":
    unittest.main()
