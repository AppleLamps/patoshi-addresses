"""Phase 5 census: labelling rule, clustering, measurement, Phase 4 replication and the census SQL's semantics."""
import importlib.util
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("phase5", ROOT / "scripts" / "phase5_offline.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def cb_row(h, txid, vout=0, address=''):
    return {'row_kind': 'coinbase_output', 'height': str(h), 'txid': txid, 'idx': str(vout), 'time': '',
            'prev_txid': '', 'prev_vout': '', 'value_sats': '5000000000', 'output_type': 'pubkey',
            'address': address, 'coinbase_height': ''}


def in_row(txid, height, vin, prev, vout, cb_height=None):
    return {'row_kind': 'spending_input', 'height': str(height), 'txid': txid, 'idx': str(vin), 'time': '',
            'prev_txid': prev, 'prev_vout': str(vout), 'value_sats': '', 'output_type': '', 'address': '',
            'coinbase_height': '' if cb_height is None else str(cb_height)}


class Labels(unittest.TestCase):
    def test_weights_and_threshold(self):
        self.assertEqual(p.nonce_label(0, 0), 'unclustered')
        self.assertEqual(p.nonce_label(1, 1), 'undetermined')      # one passing co-member is not enough
        self.assertEqual(p.nonce_label(0, 2), 'other')             # two failures are decisive
        self.assertEqual(p.nonce_label(5, 5), 'patoshi')
        self.assertEqual(p.nonce_label(4, 4), 'undetermined')
        self.assertEqual(p.nonce_label(9, 10), 'patoshi')          # one failure tolerated in a large cluster
        self.assertAlmostEqual(p.nonce_llr(1, 2), p.W_PASS + p.W_FAIL)

    def test_error_rates(self):
        op, po = p.label_error_rates(5)
        self.assertAlmostEqual(op, p.PASS_OTHER ** 5)
        self.assertAlmostEqual(p.label_error_rates(2)[1], p.EPS ** 2)
        self.assertEqual(p.label_error_rates(0), (0.0, 0.0))
        op, po = p.label_error_rates(3000)                          # a very large sweep must not overflow
        self.assertLess(op, 1e-100)
        self.assertLess(po, 1e-100)

    def test_intervals(self):
        lo, hi = p.wilson(5, 100)
        self.assertLess(lo, 0.05)
        self.assertGreater(hi, 0.05)
        lo, hi = p.cluster_bootstrap([(1, 10)] * 20)
        self.assertAlmostEqual(lo, 0.1)
        self.assertAlmostEqual(hi, 0.1)


class Core(unittest.TestCase):
    def setUp(self):
        # Blocks 1-4 swept by one miner (nonces fail), 10-15 by Patoshi (nonces pass), 20 key-reuses block 21's address.
        passes = {h: False for h in range(30)}
        passes.update({h: True for h in (3, 10, 11, 12, 13, 14, 15)})
        listed = {3, 10, 11, 12, 13, 14}
        rows = [cb_row(h, f'cb{h}', address=f'k{h}') for h in range(30) if h not in (20, 21)]
        rows += [cb_row(20, 'cb20', address='shared'), cb_row(21, 'cb21', address='shared'), cb_row(21, 'cb21', 1, 'x')]
        rows += [in_row('sweep', 100, i, f'cb{h}', 0, h) for i, h in enumerate((1, 2, 3, 4))]
        rows += [in_row('sweep', 100, 4, 'change', 1)]
        rows += [in_row('pat', 200, i, f'cb{h}', 0, h) for i, h in enumerate(range(10, 16))]
        rows += [in_row('lone', 300, 0, 'cb21', 1, 21)]
        self.blocks, self.txs, self.clusters = p.census_core(rows, listed, passes)

    def test_clusters_and_labels(self):
        b = self.blocks
        self.assertEqual(b[3]['cluster_blocks'], 4)
        self.assertEqual(b[3]['loo_label'], 'other')          # listed, but its co-members are another miner
        self.assertEqual(b[15]['loo_label'], 'patoshi')       # unlisted, but spent with five Patoshi blocks
        self.assertEqual(b[5]['loo_label'], 'unclustered')
        self.assertTrue(b[21]['spent'] and not b[20]['spent'])
        self.assertEqual(b[21]['outputs'], 2)
        self.assertEqual(b[20]['address_cluster_id'], b[21]['address_cluster_id'])
        self.assertNotEqual(b[20]['cluster_id'], b[21]['cluster_id'])
        self.assertEqual(self.txs['sweep']['inputs'], 5)
        self.assertEqual(self.clusters[1]['list_majority'], 'unlisted_majority')

    def test_measure(self):
        m = p.measure(self.blocks, self.clusters, (3, 14), 5, 6)
        fp = m['list_false_positive_rate_among_other_miner_blocks']
        # In span 3..14 the 'other' blocks are 3 and 4; block 3 is listed.
        self.assertEqual((fp['hits'], fp['blocks']), (1, 2))
        om = m['list_omission_rate_among_patoshi_owned_blocks']
        self.assertEqual((om['hits'], om['blocks']), (0, 5))   # 15 is outside the span
        self.assertAlmostEqual(fp['implied_false_positive_heights'], 5.0)


class Replication(unittest.TestCase):
    def test_phase4_first_spends_reproduced(self):
        summary, blocks, txs, clusters = p.analyse(p.replicate_rows(), write=False)
        r = summary['phase4_comparison']['phase4_first_spends']
        self.assertEqual((r['found_in_census'], r['listed_counts_equal']), (20, 20))
        t = summary['track_test']
        self.assertEqual((t['observed_fits'], t['listed_blocks_with_other_miner_co_members']), (8, 12))
        self.assertAlmostEqual(t['cluster_level']['poisson_binomial_upper_tail_p'], 8.0e-8, delta=0.1e-8)
        self.assertEqual(blocks[14450]['loo_label'], 'patoshi')
        self.assertAlmostEqual(summary['phase4_comparison']['list_majority_zero_truncated_mle']['p_hat'], 0.0033, places=4)


@unittest.skipUnless(importlib.util.find_spec('duckdb') and importlib.util.find_spec('sqlglot'),
                     'duckdb and sqlglot are needed to execute the census SQL locally')
class CensusSQL(unittest.TestCase):
    def test_semantics_on_synthetic_chain(self):
        for name in ('cospend_census.sql', 'cospend_census_semijoin.sql'):
            with self.subTest(sql=name):
                self.check(name)

    def check(self, name):
        import duckdb, sqlglot
        sql = sqlglot.transpile((ROOT / 'analysis/phase5/sql' / name).read_text(), read='bigquery', write='duckdb')[0]
        db = duckdb.connect()
        db.execute('ATTACH \':memory:\' AS "bigquery-public-data"')
        db.execute('CREATE SCHEMA "bigquery-public-data".crypto_bitcoin')
        db.execute('''CREATE TABLE "bigquery-public-data".crypto_bitcoin.transactions (
            hash VARCHAR, block_number BIGINT, block_timestamp TIMESTAMP, block_timestamp_month DATE,
            is_coinbase BOOLEAN, outputs STRUCT("index" BIGINT, value DECIMAL(38, 0), type VARCHAR, addresses VARCHAR[])[])''')
        db.execute('''CREATE TABLE "bigquery-public-data".crypto_bitcoin.inputs (
            transaction_hash VARCHAR, block_number BIGINT, block_timestamp TIMESTAMP, "index" BIGINT,
            spent_transaction_hash VARCHAR, spent_output_index BIGINT)''')
        coinbases = [('c1', 1, '2009-01-09'), ('c2', 2, '2009-01-09'), ('c3', 54619, '2010-05-05'),
                     ('c4', 54620, '2010-05-05')]
        for txid, h, day in coinbases:
            outs = [(0, 5000000000, 'pubkey', [f'addr{h}'])] + ([(1, 1, 'pubkeyhash', ['extra'])] if h == 2 else [])
            db.execute('INSERT INTO "bigquery-public-data".crypto_bitcoin.transactions VALUES (?, ?, ?, ?, true, ?)',
                       [txid, h, day, day[:8] + '01', [dict(zip(('index', 'value', 'type', 'addresses'), o)) for o in outs]])
        db.execute('INSERT INTO "bigquery-public-data".crypto_bitcoin.transactions VALUES '
                   "('p1', 3, '2009-01-09', '2009-01-01', false, [])")
        inputs = [('sweep', 900, 0, 'c1', 0), ('sweep', 900, 1, 'p1', 1), ('sweep', 900, 2, 'c2', 1),  # co-spend
                  ('other', 900, 0, 'p1', 0),                                     # spends nothing early
                  ('late', 60000, 0, 'c4', 0),                                     # coinbase above 54,619
                  ('future', 968903, 0, 'c3', 0),                                  # after the watermark
                  ('wrongvout', 950, 0, 'c1', 5)]                                  # no such coinbase output
        for t, h, i, prev, vout in inputs:
            db.execute('INSERT INTO "bigquery-public-data".crypto_bitcoin.inputs VALUES (?, ?, ?, ?, ?, ?)',
                       [t, h, '2011-01-01', i, prev, vout])
        cur = db.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        self.assertEqual(cols, ['row_kind', 'height', 'txid', 'idx', 'time', 'prev_txid', 'prev_vout', 'value_sats',
                                'output_type', 'address', 'coinbase_height'])
        outs = [(r['height'], r['idx']) for r in rows if r['row_kind'] == 'coinbase_output']
        self.assertEqual(outs, [(1, 0), (2, 0), (2, 1), (54619, 0)])
        ins = [(r['txid'], r['idx'], r['prev_txid'], r['coinbase_height']) for r in rows if r['row_kind'] == 'spending_input']
        self.assertEqual(ins, [('sweep', 0, 'c1', 1), ('sweep', 1, 'p1', None), ('sweep', 2, 'c2', 2)])
        # The exported rows feed the analysis unchanged (None becomes '' in the committed CSV).
        text = [{k: '' if v is None else str(v) for k, v in r.items()} for r in rows]
        blocks, txs, clusters = p.census_core(text, set(), {1: False, 2: False, 54619: False})
        self.assertEqual(blocks[1]['cluster_id'], blocks[2]['cluster_id'])
        self.assertFalse(blocks[54619]['spent'])


if __name__ == '__main__':
    unittest.main()
