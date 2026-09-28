"""Phase 8 synthesis: tier rules, the omission estimator and the Monte Carlo combination."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("phase8", Path(__file__).parents[1] / "scripts" / "phase8_synthesis.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def row(h, listed=False, label='unclustered', post=0.0, pmin=0.0, band=True):
    return {'height': str(h), 'listed': str(listed), 'co_spend_label': label, 'posterior': str(post),
            'posterior_min_over_settings': str(pmin), 'band': str(band)}


class Tiers(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(p.tier(row(0)), 'genesis')
        self.assertEqual(p.tier(row(5, listed=True)), 'listed_uncontradicted')
        self.assertEqual(p.tier(row(5, listed=True, label='other')), 'listed_contradicted')
        self.assertEqual(p.tier(row(5, label='other', post=0.99, pmin=0.99)), 'other_miner')
        self.assertEqual(p.tier(row(5, post=0.95, pmin=0.92)), 'added_robust')
        self.assertEqual(p.tier(row(5, post=0.95, pmin=0.2)), 'added_probable')
        self.assertEqual(p.tier(row(5, post=0.6)), 'added_possible')
        self.assertEqual(p.tier(row(5, post=0.1)), 'unresolved')
        self.assertEqual(p.tier(row(5, post=0.1, band=False)), 'no_patoshi_evidence')


class Estimate(unittest.TestCase):
    def test_omission_estimator(self):
        # 100 ordinary blocks at b = 0.2 give 20 passes; 50 Patoshi at q = 1 give 50: k = 70, n = 150.
        self.assertAlmostEqual(p.omission(70, 150, 0.2, q=1.0), 50.0)

    def test_simulation_recovers_point_values(self):
        inp = {'listed': 1000, 'fee_btc': 0.0, 'b': 0.2, 'b_sd': 1e-12, 'fp': 20.0, 'fp_sd': 1e-12,
               'fp_identified': 10, 'in_span': {'k': 70, 'n': 150, 'floor': 0}, 'after_end': {'k': 70, 'n': 150, 'floor': 0},
               'pre': [1.0, 0.0]}
        out = p.simulate(inp, draws=20000, q=1.0)
        lo, mid, hi = out['total_blocks']
        # 1000 - 20 + 50 + 50 + 1, with sampling noise only from the band counts
        self.assertAlmostEqual(mid, 1081, delta=1.5)
        self.assertLess(lo, mid)
        self.assertGreater(hi, mid)
        self.assertEqual(out['false_positives'][1], 20.0)

    def test_false_positives_never_below_identified(self):
        inp = {'listed': 1000, 'fee_btc': 0.0, 'b': 0.2, 'b_sd': 1e-12, 'fp': 5.0, 'fp_sd': 1e-12,
               'fp_identified': 12, 'in_span': {'k': 30, 'n': 150, 'floor': 0}, 'after_end': {'k': 30, 'n': 150, 'floor': 0},
               'pre': []}
        self.assertEqual(p.simulate(inp, draws=1000)['false_positives'], [12.0, 12.0, 12.0])


class CommittedArtifacts(unittest.TestCase):
    """The committed outputs must be what the script produces from the committed inputs."""

    def test_list_covers_every_height_and_matches_tier_summary(self):
        import csv
        rows = p.build_list()
        self.assertEqual([r['height'] for r in rows], list(range(54620)))
        committed = {r['tier']: int(r['blocks']) for r in csv.DictReader(open(p.OUT / 'tier_summary.csv'))}
        self.assertEqual({t['tier']: t['blocks'] for t in p.tier_table(rows)}, committed)
        self.assertEqual(sum(committed.values()), 54620)

    def test_committed_list_matches_fresh_build_including_keys(self):
        import csv
        committed = list(csv.DictReader(open(p.OUT / 'revised_list.csv')))
        fresh = p.build_list()
        # Every column, as the CSV writer renders it, so a regression in any existing column also fails.
        self.assertEqual(committed, [{k: str(v) for k, v in r.items()} for r in fresh])
        self.assertEqual(committed[0]['p2pkh_address'], '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa')   # genesis
        self.assertEqual(len({r['pubkey'] for r in committed}), 54620)

    def test_p2pkh_derivation(self):
        # Block 3's key and address, as shipped in patoshi_p2pkh_addresses.csv.
        k = ('0494b9d3e76c5b1629ecf97fff95d7a4bbdac87cc26099ada28066c6ff1eb9191223cd897194a08d0c2726c5747f1db49e8c'
             'f90e75dc3e3550ae9b30086f3cd5aa')
        self.assertEqual(p.p2pkh(k), '1FvzCLoTPGANNjWoUo6jUGuAG3wg1w4YjR')

    def test_estimate_matches_committed(self):
        import json
        committed = json.loads((p.OUT / 'revised_estimate.json').read_text())
        fresh = p.simulate(p.inputs_from_phases())
        self.assertEqual(fresh['total_blocks'], committed['answer']['total_blocks_median_and_95ci'])
        self.assertEqual(fresh['total_btc'], committed['answer']['total_btc_median_and_95ci'])


if __name__ == '__main__':
    unittest.main()
