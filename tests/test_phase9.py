import csv
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase9_nonce_clock as p  # noqa: E402


class Definitions(unittest.TestCase):
    def test_bswap_and_subranges(self):
        self.assertEqual(p.bswap32(0x7c2bac1d), 0x1dac2b7c)
        self.assertEqual(p.subrange(0), 0)
        self.assertIsNone(p.subrange(p.P))                  # the gap between [0, P) and [2P, 3P)
        self.assertEqual(p.subrange(6 * p.P - 1), 5 * p.P)
        self.assertIsNone(p.subrange(6 * p.P))              # Lerner's 983,040,000 upper bound
        self.assertAlmostEqual(p.u_in(p.P - 1), 0.0)        # top of a subrange is the start of a decrementing scan
        self.assertAlmostEqual(p.u_ip(2 * p.P), 0.0)

    def test_one_sided_mann_whitney_direction(self):
        r = p.mw_less([0.1, 0.2, 0.3] * 20, [0.6, 0.7, 0.8] * 20)
        self.assertLess(r['p_one_sided'], 1e-6)
        self.assertGreater(p.mw_less([0.6] * 30, [0.1] * 30)['p_one_sided'], 0.99)

    def test_holm(self):
        self.assertEqual(p.holm([0.01, 0.04]), [0.02, 0.04])


class Assembly(unittest.TestCase):
    def test_stock_order_respects_dependencies(self):
        txs = {'bb', 'aa', 'cc'}
        parents = {'aa': ['cc'], 'bb': [], 'cc': []}         # aa spends cc, so it waits for the second pass
        self.assertEqual(p.stock_order(txs, parents), ['bb', 'cc', 'aa'])

    def test_merkle_root_single_and_committed_block(self):
        cb = '0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098'
        self.assertEqual(p.merkle_root([cb]), cb)            # block 1: root equals the coinbase txid
        rows = [r for r in csv.DictReader(open(p.RES / 'block_transactions.csv')) if r['height'] == '546']
        hdr = next(r for r in csv.DictReader(open(p.HEADERS)) if r['height'] == '546')
        cbs = [r['txid'] for r in rows if r['is_coinbase'] == 'true']
        nc = {r['txid'] for r in rows if r['is_coinbase'] != 'true'}
        par = {r['txid']: [x for x in r['prev_txids'].split(';') if x] for r in rows if r['is_coinbase'] != 'true'}
        self.assertEqual(p.merkle_root(cbs + p.stock_order(nc, par)), hdr['merkle_root'])


class CommittedResults(unittest.TestCase):
    def test_primary_verdict_is_reproducible(self):
        import json
        committed = json.loads((p.RES / 'primary.json').read_text())
        B = p.load()
        cp = p.groups(B, {'listed_uncontradicted'})
        t1 = p.mw_less(*p.split(cp, lambda b: p.u_in(b['r'])))
        self.assertEqual(t1['n_short'], committed['T1_primary_u_IN']['n_short'])
        self.assertAlmostEqual(t1['p_one_sided'], committed['T1_primary_u_IN']['p_one_sided'])
        self.assertEqual(committed['verdict'], 'failure: reset not supported')


if __name__ == '__main__':
    unittest.main()
