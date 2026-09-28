"""Phase 6 posterior: track test, likelihood rules and EM recovery on a planted mixture."""
import importlib.util
import random
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("phase6", Path(__file__).parents[1] / "scripts" / "phase6_posterior.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class Track(unittest.TestCase):
    def setUp(self):
        # Machine A: counter = minutes since t0. Machine B: counter = 500 + minutes. One block per 10 minutes.
        self.T = {h: h * 600.0 for h in range(40)}
        self.E = {h: (h * 10 if h % 2 == 0 else 500 + h * 10) for h in range(40)}

    def test_fits_on_the_line_and_not_off_it(self):
        anchors = [0, 2, 6, 8]
        self.assertTrue(p.track_fit(4, anchors, self.T, self.E, (3, 0.10, 1)))
        self.E[4] = 55                                   # between the anchors in value, but far off the time-line
        self.assertIs(p.track_fit(4, anchors, self.T, self.E, (3, 0.10, 1)), False)

    def test_not_evaluable_without_a_close_bracket(self):
        self.assertIsNone(p.track_fit(4, [0, 38], {**self.T, 38: 40 * 3600.0}, self.E, (3, 0.10, 1)))
        self.assertIsNone(p.track_fit(4, [6, 8], self.T, self.E, (3, 0.10, 1)))    # nothing below

    def test_several_anchor_pairs_find_a_second_machine(self):
        # Nearest anchors (4, 6) are a usable machine-A pair; block 5 is on machine B, whose anchors (1, 7) are further out.
        anchors = [1, 4, 6, 7]
        self.assertIs(p.track_fit(5, anchors, self.T, self.E, (3, 0.10, 1)), False)
        self.assertIs(p.track_fit(5, anchors, self.T, self.E, (3, 0.10, 3)), True)


def block(h, band, spent, track, label='unclustered', listed=False):
    return {'height': h, 'listed': listed, 'band': band, 'spent': spent, 'loo_label': label, 'track': track,
            'cluster_blocks': 1}


ORATE = {'unspent': 0.3, 'track_evaluable': 0.9, 'track_fit': 0.05}
PRATE = {'unspent': 0.998, 'band': 0.99}


class Likelihood(unittest.TestCase):
    def test_patoshi_co_spend_turns_a_spend_into_evidence_for(self):
        lp, lo = p.likelihoods(block(1, True, True, None, 'patoshi'), ORATE, PRATE, 0.5, 0.9)
        lp2, lo2 = p.likelihoods(block(1, True, True, None), ORATE, PRATE, 0.5, 0.9)
        self.assertGreater(lp / lo, 100)
        self.assertLess(lp2 / lo2, 0.1)

    def test_other_co_spend_is_zero(self):
        blocks = {1: block(1, True, False, True, 'other')}
        post = p.score(blocks, [ORATE] * 3, PRATE, {0: 0.5}, [0.5] * 3, [0.9] * 3)
        self.assertEqual(post[1], 0.0)


class EM(unittest.TestCase):
    def test_recovers_planted_share_and_track_rate(self):
        rng = random.Random(7)
        blocks, truth = {}, {}
        for h in range(1, 2001):
            pat = rng.random() < 0.2
            truth[h] = pat
            band = rng.random() < (0.99 if pat else p.PASS_OTHER)
            spent = rng.random() >= (0.998 if pat else 0.3)
            ev = rng.random() < 0.9
            track = (rng.random() < (0.7 if pat else 0.05)) if ev else None
            blocks[h] = block(h, band, spent, track)
        orates = [ORATE] * 3
        pi, f1, e1, post = p.fit_em(blocks, orates, PRATE)
        self.assertAlmostEqual(pi[0], sum(truth.values()) / 2000, delta=0.03)
        self.assertAlmostEqual(f1[0], 0.7, delta=0.07)
        self.assertAlmostEqual(sum(post.values()), sum(truth.values()), delta=40)


if __name__ == '__main__':
    unittest.main()
