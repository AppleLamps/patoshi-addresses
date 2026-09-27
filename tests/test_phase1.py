"""Offline numerical/encoding checks, independent of the CSV observations."""
import importlib.util
import itertools
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("phase1", Path(__file__).parents[1] / "scripts" / "phase1_offline.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class OfflinePrimitives(unittest.TestCase):
    def test_known_generator_address(self):
        key = bytes.fromhex("0479be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
                            "483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8")
        self.assertTrue(p.valid_key(key))
        self.assertEqual(p.address_from_hash(p.hash160(key)), "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm")
        self.assertFalse(p.valid_key(key[:-1] + b"\0"))
        self.assertFalse(p.valid_key(b"\x04" + p.FIELD.to_bytes(32, "big") + key[33:]))

    def test_base58_leading_zeros(self):
        for raw in (b"", b"\0", b"\0\0", b"\0\0\xff", bytes(range(25))):
            self.assertEqual(p.b58decode(p.b58encode(raw)), raw)

    def test_gamma_closed_forms(self):
        for x in (.001, .1, 1, 4, 10, 100):
            self.assertAlmostEqual(p.gamma_q(1, x), math.exp(-x), places=12)
            self.assertAlmostEqual(p.gamma_q(.5, x), math.erfc(math.sqrt(x)), places=12)
            self.assertAlmostEqual(p.gamma_q(3, x), math.exp(-x) * (1 + x + x*x/2), places=12)
        # Published standard 95th percentile chi-square(255), rounded tolerance.
        self.assertAlmostEqual(p.gamma_q(255/2, 293.2478/2), .05, delta=1e-5)

    def test_prefix_probability_partition(self):
        self.assertEqual(p.prefix_probability("1"), 1)
        self.assertEqual(p.prefix_probability("0"), 0)
        self.assertAlmostEqual(p.prefix_probability("11"), 1/256, places=15)
        self.assertAlmostEqual(sum(p.prefix_probability("1" + c) for c in p.ALPHABET), 1, places=14)
        self.assertAlmostEqual(sum(p.prefix_probability("1CF" + c) for c in p.ALPHABET),
                               p.prefix_probability("1CF"), places=16)

    def test_holm(self):
        tests = [{"p_raw": x} for x in [.02, .001, .03]]
        p.holm(tests)
        self.assertEqual([t["p_holm"] for t in tests], [.04, .003, .04])

    def test_gap_metrics(self):
        self.assertEqual(p.run_metrics(p.np.array([True, False, False, True, False])), (4, 2))
        self.assertEqual(p.intervals([3, 4, 7]), [
            {"start_height": 3, "end_height": 4, "length": 2},
            {"start_height": 7, "end_height": 7, "length": 1}])

    def test_stratified_runs_expectation_against_exhaustive_enumeration(self):
        windows = ([True, False, False], [True, True, False])
        trials = [p.run_metrics(p.np.array(a + b))[0]
                  for a in set(itertools.permutations(windows[0]))
                  for b in set(itertools.permutations(windows[1]))]
        self.assertAlmostEqual(p.expected_runs(p.np.array(windows[0] + windows[1]), [(0, 3), (3, 6)]),
                               sum(trials) / len(trials))


if __name__ == "__main__":
    unittest.main()
