"""Small offline checks of the parsers and set/rank comparison primitives."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("provenance", Path(__file__).parents[1] / "scripts" / "provenance_compare.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ProvenancePrimitives(unittest.TestCase):
    def test_equivalent_list_formats(self):
        for text in ("[3, 4, 8]", "3\n4\n8\n", "const PATOSHI_BLOCKS = [3,4,8,]; module.exports = {};",
                     "<?php $patoshiBlocks = array(3,4,8); ?>"):
            with tempfile.TemporaryDirectory() as d:
                f = Path(d) / "source.txt"
                f.write_text(text)
                self.assertEqual(p.external_list(f), [3,4,8])

    def test_executable_expression_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "bad.js"
            f.write_text("const PATOSHI_BLOCKS = [3, process.exit(1), 8];")
            with self.assertRaises(ValueError):
                p.external_list(f)

    def test_canonical_hash_ignores_order_and_duplicates(self):
        self.assertEqual(p.canonical_sha([3,4,8]), p.canonical_sha([8,3,4,3]))
        self.assertNotEqual(p.canonical_sha([3,4,8]), p.canonical_sha([3,4,9]))

    def test_rank_intervals_do_not_count_unlisted_heights(self):
        self.assertEqual(p.missing_rank_runs([3,4,8,9,20], {3,20}), [
            {"first_csv_rank_1based": 2, "last_csv_rank_1based": 4,
             "first_height": 4, "last_height": 9, "omitted_csv_rows": 3}])


if __name__ == "__main__":
    unittest.main()
