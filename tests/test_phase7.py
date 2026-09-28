"""Phase 7 helpers: binomial tail, mixture fraction, Mann-Whitney, nonce-shape counts and dead-time pairs."""
import importlib.util
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("phase7", Path(__file__).parents[1] / "scripts" / "phase7_verify.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class Stats(unittest.TestCase):
    def test_binomial_tail(self):
        exact = sum(math.comb(10, i) * 0.2**i * 0.8**(10 - i) for i in range(4, 11))
        self.assertAlmostEqual(p.binom_upper(4, 10, 0.2), exact, places=12)
        self.assertEqual(p.binom_upper(0, 10, 0.2), 1.0)

    def test_mixture_fraction(self):
        # Half Patoshi (p1 = 0.5) and half ordinary (p0 = 0.2) gives a share of 0.35.
        m = p.mixture_fraction(35, 100, 0.2, 0.5)
        self.assertAlmostEqual(m['estimate'], 0.5, places=6)
        self.assertLess(m['ci95'][0], 0.5)
        self.assertGreater(m['ci95'][1], 0.5)
        self.assertIsNone(p.mixture_fraction(0, 0, 0.2, 0.5))

    def test_fisher_exact(self):
        # [[3, 0], [0, 3]]: the only table at least this extreme; P = 1 / C(6, 3) = 0.05.
        self.assertAlmostEqual(p.fisher_greater(3, 0, 0, 3), 0.05, places=12)
        self.assertAlmostEqual(p.fisher_greater(0, 3, 3, 0), 1.0, places=12)

    def test_mann_whitney(self):
        z, pv = p.mann_whitney([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        self.assertAlmostEqual(z, 0.0)
        self.assertAlmostEqual(pv, 1.0)
        z, pv = p.mann_whitney(list(range(100)), list(range(50, 150)))
        self.assertLess(z, 0)
        self.assertLess(pv, 1e-6)


class Habits(unittest.TestCase):
    def test_shape_counts_ignore_out_of_band(self):
        H = {1: {'lsb': 3}, 2: {'lsb': 30}, 3: {'lsb': 12}, 4: {'lsb': 9}}
        self.assertEqual(p.shape_counts(H, [1, 2, 3, 4]), (2, 3))       # 12 is outside the band

    def test_dead_time_pairs(self):
        H = {h: {'t': t} for h, t in ((1, 0), (2, 400), (3, 450), (4, 1000))}
        n, k, _ = p.dead_time_pairs(H, [2, 3, 4], {1, 2, 3})
        self.assertEqual((n, k), (3, 1))                                # 3 follows 2 by 50 s


if __name__ == '__main__':
    unittest.main()
