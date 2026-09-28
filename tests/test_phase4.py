"""Phase 4 primitives: sighash, DER parsing, small-k table and truncated-binomial likelihood."""
import importlib.util
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("phase4", Path(__file__).parents[1] / "scripts" / "phase4_offline.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

# Block 170: Satoshi to Hal Finney, spending the block 9 coinbase (public, widely reproduced transaction).
BLOCK9_KEY = ("0411db93e1dcdb8a016b49840f8c53bc1eb68a382e97b1482ecad7b148a6909a5cb2e0eaddfb84ccf9744464f82e160bfa9b"
              "8b64f9d4c03f999b8643f656b412a3")
TX170 = {
    'version': 1, 'locktime': 0,
    'vin': [{'txid': '0437cd7f8525ceed2324359c2d0ba26006d92d856a9c20fa0241106ee5a597c9', 'vout': 0, 'sequence': 0xffffffff}],
    'vout': [{'value': 1000000000, 'script': '4104ae1a62fe09c5f51b13905f07f06b99a2f7159b2225f374cd378d71302fa28414e7aab37397f554a7df5f142c21c1b7303b8a0626f1baded5c72a704f7e6cd84cac'},
             {'value': 4000000000, 'script': '41' + BLOCK9_KEY + 'ac'}],
}
SIG170 = bytes.fromhex("304402204e45e16932b8af514961a1d3a1a25fdf3f4f7732e9d624c6c61548ab5fb8cd410220181522ec8eca07de4860a4acdd12909d831cc56cbbac4622082221a8768d1d09")


class Phase4Primitives(unittest.TestCase):
    def test_block170_signature_verifies(self):
        from cryptography.hazmat.primitives.asymmetric import ec, utils
        from cryptography.hazmat.primitives import hashes
        z = p.legacy_sighash(TX170, 0, bytes.fromhex('41' + BLOCK9_KEY + 'ac'), 1)
        r, s, strict = p.parse_der(SIG170)
        self.assertTrue(strict)
        key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), bytes.fromhex(BLOCK9_KEY))
        key.verify(utils.encode_dss_signature(r, s), z, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        # A changed output must break the signature.
        bad = dict(TX170, vout=[dict(TX170['vout'][0], value=1000000001), TX170['vout'][1]])
        z2 = p.legacy_sighash(bad, 0, bytes.fromhex('41' + BLOCK9_KEY + 'ac'), 1)
        with self.assertRaises(Exception):
            key.verify(utils.encode_dss_signature(r, s), z2, ec.ECDSA(utils.Prehashed(hashes.SHA256())))

    def test_non_canonical_der_is_flagged(self):
        r, s, strict = p.parse_der(SIG170)
        padded = bytes([0x30, SIG170[1] + 1, 0x02, 0x21, 0x00]) + SIG170[4:]
        r2, s2, strict2 = p.parse_der(padded)
        self.assertEqual((r, s), (r2, s2))
        self.assertFalse(strict2)

    def test_small_k_table(self):
        t = p.small_k_table(16)
        self.assertEqual(t[p.G[0]], 1)
        from cryptography.hazmat.primitives.asymmetric import ec
        for k in (2, 3, 7, 16):
            x = ec.derive_private_key(k, ec.SECP256K1()).public_key().public_numbers().x
            self.assertEqual(t[x], k)

    def test_zero_truncated_binomial(self):
        # Many clusters with exactly one hit in large n imply a small rate; the MLE must be well below 1/n.
        est = p.zt_binomial_mle([(200, 1), (80, 1), (40, 1)])
        self.assertLess(est['p_hat'], 1 / 40)
        self.assertLessEqual(est['ci95_profile'][0], est['p_hat'])
        self.assertGreaterEqual(est['ci95_profile'][1], est['p_hat'])

    def test_tails(self):
        self.assertAlmostEqual(p.poisson_tail(0, 3.0), 1.0)
        self.assertAlmostEqual(p.poisson_tail(1, 2.0), 1 - math.exp(-2), places=12)
        self.assertAlmostEqual(p.poisson_binomial_tail(2, [0.5, 0.5]), 0.25, places=12)
        self.assertAlmostEqual(p.poisson_binomial_tail(1, [0.1, 0.2]), 1 - 0.9 * 0.8, places=12)


if __name__ == '__main__':
    unittest.main()
