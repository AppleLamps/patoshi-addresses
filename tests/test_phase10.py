import csv
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase10_clock_model as m  # noqa: E402


class ClockFactor(unittest.TestCase):
    def test_factor_uses_cell_q_and_era_rate(self):
        b = {'band': True, 'loo_label': 'unclustered', 'spent': False, 'track': None, 'clock': True, 'q': 0.9}
        orate = {'unspent': 0.8, 'track_evaluable': 0.5, 'track_fit': 0.1, 'clock_inconsistent': 0.05}
        prate = {'unspent': 0.999, 'band': 0.99}
        m.USE_CLOCK = False
        lp0, lo0 = m.likelihoods(b, orate, prate, 0.9, 0.9)
        m.USE_CLOCK = True
        lp1, lo1 = m.likelihoods(b, orate, prate, 0.9, 0.9)
        self.assertAlmostEqual(lp1 / lp0, 0.9)
        self.assertAlmostEqual(lo1 / lo0, 0.05)
        lp2, lo2 = m.likelihoods(dict(b, clock=False), orate, prate, 0.9, 0.9)
        self.assertAlmostEqual(lp2 / lp0, 0.1)
        self.assertAlmostEqual(lo2 / lo0, 0.95)
        self.assertEqual(m.likelihoods(dict(b, clock=None), orate, prate, 0.9, 0.9), (lp0, lo0))


class Reproduction(unittest.TestCase):
    def test_clock_off_reproduces_phase6(self):
        post = m.fit(False)[-1]
        p6 = {int(r['height']): float(r['posterior']) for r in csv.DictReader(open(m.ROOT / 'analysis/phase6/posterior_blocks.csv'))}
        self.assertLess(max(abs(post[h] - p6[h]) for h in post), 1e-5)

    def test_committed_posteriors_match_fresh_fit(self):
        post = m.fit(True)[-1]
        rows = {int(r['height']): r for r in csv.DictReader(open(m.OUT / 'posterior_m10.csv'))}
        self.assertLess(max(abs(post[h] - float(rows[h]['posterior_m10'])) for h in post), 1e-5)
        p6 = next(csv.reader(open(m.ROOT / 'analysis/phase6/posterior_blocks.csv')))
        self.assertEqual(list(rows[1])[:len(p6)], p6)            # every Phase 6 column kept, in order

    def test_committed_summary(self):
        s = json.loads((m.OUT / 'model_summary.json').read_text())
        self.assertTrue(s['V1_holdout']['pass'] and s['V2_null_test_half']['pass'] and s['V3_shape_calibration']['pass'])
        self.assertTrue(s['adopted_as_calibrated'])
        rows = list(csv.DictReader(open(m.OUT / 'posterior_m10.csv')))
        self.assertEqual(len(rows), 54_619)
        self.assertEqual(sum(r['tier_m10'] == 'added_robust' for r in rows), s['tiers']['added_robust']['tier_m10'])


if __name__ == '__main__':
    unittest.main()
