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


if __name__ == '__main__':
    unittest.main()
