#!/usr/bin/env python3
"""Reproducible CSV-only forensics. No network access; original extractor is never run.

Dependencies: numpy. Optional independent key validation: cryptography.
Run: python scripts/phase1_offline.py --permutations 1999
"""
from __future__ import annotations

import argparse
import ast
import collections
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIELD = 2**256 - 2**32 - 977
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
SEED = 20260927
# Fixed exploratory rules, declared before running the scan. These are not an
# exhaustive dictionary of all strings a human might decide are meaningful.
HEX_WORDS = ("deadbeef", "cafebabe", "feedface", "decafbad", "face", "babe", "cafe", "dead", "beef", "1cfb")
ASCII_WORDS = ("satoshi", "bitcoin", "patoshi", "nakamoto", "genesis", "finney", "hal")
ADDRESS_WORDS = ("satoshi", "bitcoin", "patoshi", "nakamoto", "genesis", "finney")


def prohibit_network(event, args):
    if event in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.sendto"):
        raise RuntimeError("Phase 1 prohibits network access")


sys.addaudithook(prohibit_network)


def sha256(data):
    return hashlib.sha256(data).digest()


def hash160(key):
    return hashlib.new("ripemd160", sha256(key)).digest()


def b58encode(raw):
    n = int.from_bytes(raw, "big")
    chars = []
    while n:
        n, digit = divmod(n, 58)
        chars.append(ALPHABET[digit])
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + "".join(reversed(chars))


def b58decode(text):
    n = 0
    for char in text:
        n = n * 58 + ALPHABET.index(char)
    return b"\0" * (len(text) - len(text.lstrip("1"))) + n.to_bytes((n.bit_length() + 7) // 8, "big")


def address_from_hash(digest):
    payload = b"\0" + digest
    return b58encode(payload + sha256(sha256(payload))[:4])


def valid_key(key):
    if len(key) != 65 or key[0] != 4:
        return False
    x, y = int.from_bytes(key[1:33], "big"), int.from_bytes(key[33:], "big")
    return x < FIELD and y < FIELD and (y * y - x * x * x - 7) % FIELD == 0


def gamma_q(a, x):
    """Regularized upper incomplete gamma, series / continued fraction.

    This avoids downloading SciPy. Numerical checks are in tests/test_phase1.py.
    Underflow is rendered as '<1e-300' in reports, never 'impossible'.
    """
    if x <= 0:
        return 1.0
    factor = math.exp(a * math.log(x) - x - math.lgamma(a))
    if x < a + 1:
        term = total = 1 / a
        for j in range(1, 10000):
            term *= x / (a + j)
            total += term
            if abs(term) < abs(total) * 1e-14:
                return max(0.0, min(1.0, 1 - factor * total))
    else:
        tiny = 1e-300
        b = x + 1 - a
        c, d = 1 / tiny, 1 / b
        total = d
        for j in range(1, 10000):
            an = -j * (j - a)
            b += 2
            d = an * d + b
            if abs(d) < tiny:
                d = tiny
            c = b + an / c
            if abs(c) < tiny:
                c = tiny
            d = 1 / d
            change = d * c
            total *= change
            if abs(change - 1) < 1e-14:
                return max(0.0, min(1.0, factor * total))
    raise ArithmeticError("Incomplete gamma did not converge")


def chi2(counts):
    counts = np.asarray(counts)
    expected = float(counts.sum()) / counts.size
    statistic = float(((counts - expected) ** 2 / expected).sum())
    return statistic, gamma_q((counts.size - 1) / 2, statistic / 2)


def holm(tests):
    running = 0.0
    for rank, test in enumerate(sorted(tests, key=lambda t: t["p_raw"])):
        running = max(running, min(1.0, (len(tests) - rank) * test["p_raw"]))
        test["p_holm"] = running


def write_csv(path, rows, fields=None):
    rows = list(rows)
    fields = fields or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def intervals(values):
    values = list(values)
    if not values:
        return []
    result, start, end = [], values[0], values[0]
    for value in values[1:]:
        if value == end + 1:
            end = value
        else:
            result.append({"start_height": start, "end_height": end, "length": end - start + 1})
            start = end = value
    result.append({"start_height": start, "end_height": end, "length": end - start + 1})
    return result


def run_metrics(mask):
    transitions = np.flatnonzero(mask[1:] != mask[:-1]) + 1
    edges = np.r_[0, transitions, len(mask)]
    lengths = np.diff(edges)
    states = mask[edges[:-1]]
    return int(len(lengths)), int(lengths[~states].max(initial=0))


def expected_runs(mask, slices):
    proportions = [float(mask[a:b].mean()) for a, b in slices]
    expectation = 1 + sum(2 * int(mask[a:b].sum()) * int((~mask[a:b]).sum()) / (b - a)
                          for a, b in slices)
    return expectation + sum(a * (1 - b) + (1 - a) * b for a, b in zip(proportions, proportions[1:]))


def gap_analysis(heights, out, permutations):
    lo, hi = min(heights), max(heights)
    listed = set(heights)
    missing = [h for h in range(lo, hi + 1) if h not in listed]
    gaps = intervals(missing)
    write_csv(out / "missing_heights.csv", ({"block_height": h} for h in missing))
    write_csv(out / "gap_ranges.csv", gaps)
    mask = np.isin(np.arange(lo, hi + 1), heights)
    observed_runs, observed_max = run_metrics(mask)
    n1, n0 = int(mask.sum()), int((~mask).sum())
    size = n1 + n0
    expected = 1 + 2 * n1 * n0 / size
    variance = 2 * n1 * n0 * (2 * n1 * n0 - size) / (size**2 * (size - 1))
    z = (observed_runs - expected) / math.sqrt(variance)
    windows = []
    for start in range(0, hi + 1, 1000):
        a, b = max(start, lo), min(start + 999, hi)
        if b < a:
            continue
        piece = mask[a - lo:b - lo + 1]
        windows.append({"start_height": a, "end_height": b, "listed": int(piece.sum()),
                        "total": len(piece), "listed_fraction": float(piece.mean())})
    write_csv(out / "height_windows.csv", windows)
    nulls = {}
    # 1,000 is the primary local null. Other widths are explicitly exploratory
    # sensitivity checks after the primary result, not independent replication.
    for width in (0, 1000, 250, 500, 2000):
        mode = "global_fixed_count" if width == 0 else f"within_{width}_height_windows"
        rng = np.random.default_rng(SEED + width)
        slices = ([(0, len(mask))] if width == 0 else
                  [(max(start, lo) - lo, min(start + width, hi + 1) - lo)
                   for start in range(0, hi + 1, width) if min(start + width, hi + 1) > max(start, lo)])
        exact_expected_runs = expected_runs(mask, slices)
        simulated_runs, simulated_max = [], []
        for _ in range(permutations):
            if mode == "global_fixed_count":
                trial = rng.permutation(mask)
            else:
                trial = np.concatenate([rng.permutation(mask[a:b]) for a, b in slices])
            count, longest = run_metrics(trial)
            simulated_runs.append(count)
            simulated_max.append(longest)
        nulls[mode] = {
            "permutations": permutations,
            "p_fewer_runs": (1 + sum(x <= observed_runs for x in simulated_runs)) / (permutations + 1),
            "p_more_runs": (1 + sum(x >= observed_runs for x in simulated_runs)) / (permutations + 1),
            "p_runs_two_sided": (1 + sum(abs(x - exact_expected_runs) >= abs(observed_runs - exact_expected_runs)
                                         for x in simulated_runs)) / (permutations + 1),
            "p_longest_gap": (1 + sum(x >= observed_max for x in simulated_max)) / (permutations + 1),
            "runs_exact_expectation": exact_expected_runs,
            "runs_mean": float(np.mean(simulated_runs)),
            "runs_sd": float(np.std(simulated_runs, ddof=1)),
            "longest_gap_mean": float(np.mean(simulated_max)),
            "longest_gap_95pct": float(np.quantile(simulated_max, .95)),
            "longest_gap_max_simulated": max(simulated_max),
        }
    gap_tests = [{"test": f"{mode}/{metric}", "p_raw": result[metric]}
                 for mode, result in nulls.items() for metric in ("p_runs_two_sided", "p_longest_gap")]
    holm(gap_tests)
    write_csv(out / "gap_tests.csv", gap_tests)
    return {"range_size": size, "missing_count": n0, "listed_fraction": n1 / size,
            "gap_count": len(gaps), "longest_gaps": sorted(gaps, key=lambda g: -g["length"])[:12],
            "runs": observed_runs, "runs_expected_global": expected, "runs_z_global": z,
            "runs_p_normal_approx": math.erfc(abs(z) / math.sqrt(2)),
            "permutation_nulls": nulls, "permutation_tests_holm": gap_tests,
            "windows": windows}


def randomness(keys, digests, heights, out):
    coordinates = np.array([list(key[1:]) for key in keys], dtype=np.uint8)
    hashes = np.array([list(d) for d in digests], dtype=np.uint8)
    groups = {"x": coordinates[:, :32], "y": coordinates[:, 32:], "hash160": hashes}
    tests, frequencies = [], []
    for name, matrix in groups.items():
        for position in range(matrix.shape[1]):
            counts = np.bincount(matrix[:, position], minlength=256)
            statistic, p = chi2(counts)
            tests.append({"test": f"{name}/byte_{position:02d}/uniform", "statistic": statistic,
                          "p_raw": p, "method": "Pearson chi-square df=255"})
            frequencies.extend({"component": name, "byte_position": position, "value": value,
                                "count": int(count)} for value, count in enumerate(counts))
        statistic, p = chi2(np.bincount(matrix.ravel(), minlength=256))
        tests.append({"test": f"{name}/pooled_bytes/uniform", "statistic": statistic,
                      "p_raw": p, "method": "Pearson chi-square df=255; approximate independent-byte null"})
        bits = np.unpackbits(matrix, axis=1)
        for position, count in enumerate(bits.sum(axis=0)):
            z = (float(count) - len(matrix) / 2) / math.sqrt(len(matrix) / 4)
            tests.append({"test": f"{name}/bit_{position:03d}/balance", "statistic": z,
                          "p_raw": math.erfc(abs(z) / math.sqrt(2)),
                          "method": "two-sided binomial normal approximation"})
        # A 53-bit leading coordinate approximates a uniform real without float overflow.
        values = np.array([int.from_bytes(bytes(row[:7]), "big") >> 3 for row in matrix], dtype=float)
        for label, left, right in (("height_correlation", values, np.asarray(heights)),
                                   ("lag1_correlation", values[:-1], values[1:])):
            r = float(np.corrcoef(left, right)[0, 1])
            z = math.atanh(r) * math.sqrt(len(left) - 3)
            tests.append({"test": f"{name}/{label}", "statistic": r,
                          "p_raw": math.erfc(abs(z) / math.sqrt(2)),
                          "method": "Pearson r; large-sample Fisher-z approximation"})
    holm(tests)
    write_csv(out / "randomness_tests.csv", tests)
    write_csv(out / "byte_frequencies.csv", frequencies)
    return {"test_count": len(tests), "familywise_alpha": .05,
            "uncorrected_below_005": sum(t["p_raw"] < .05 for t in tests),
            "holm_significant": [t for t in tests if t["p_holm"] < .05],
            "smallest_p_tests": sorted(tests, key=lambda t: t["p_raw"])[:12],
            "first_byte_tests": [t for t in tests if "/byte_00/" in t["test"]],
            "assumption": "Independent near-uniform curve coordinates and uniform HASH160; 04 marker excluded. "
                          "X and Y are mathematically dependent, so these are diagnostics, not an entropy proof."}


def prefix_probability(prefix):
    """Base58 prefix mass over uniform 192-bit HASH160||checksum integers.

    Handles version-zero leading ones and variable address lengths. Real checksum
    is deterministic, so this is an approximation; the boundary error is tiny
    compared with probabilities of the short prefixes examined here.
    """
    if not prefix or any(c not in ALPHABET for c in prefix):
        return 0.0
    total = 0
    for zeros in range(1, 25):
        leading = "1" * zeros
        lower, upper = 256 ** (24 - zeros), 256 ** (25 - zeros) - 1
        if leading.startswith(prefix):
            total += upper - lower + 1
            continue
        if not prefix.startswith(leading):
            continue
        tail = prefix[zeros:]
        if tail.startswith("1"):
            continue
        number = 0
        for char in tail:
            number = number * 58 + ALPHABET.index(char)
        for digits in range(len(tail), 34):
            unit = 58 ** (digits - len(tail))
            a = max(lower, 58 ** (digits - 1), number * unit)
            b = min(upper, 58**digits - 1, (number + 1) * unit - 1)
            total += max(0, b - a + 1)
    if ("1" * 25).startswith(prefix):
        total += 1  # all-zero integer in the surrogate distribution
    return total / 2**192


def common_prefix(a, b):
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))


def vanity_scan(keys, digests, addresses, heights, out):
    candidates = []
    longest_repeat = {"length": 0}
    for height, key, digest, address in zip(heights, keys, digests, addresses):
        for name, raw in (("pubkey_xy", key[1:]), ("hash160", digest)):
            value = raw.hex()
            for word in HEX_WORDS:
                for match in re.finditer(f"(?={word})", value):
                    candidates.append({"height": height, "component": name, "rule": "hex_dictionary",
                                       "pattern": word, "offset": match.start(), "value": value})
            for match in re.finditer(r"([0-9a-f])\1{3,}", value):
                length = len(match.group())
                if length > longest_repeat["length"]:
                    longest_repeat = {"length": length, "height": height, "component": name,
                                      "pattern": match.group(), "offset": match.start()}
                if length >= 6 or match.start() == 0:
                    candidates.append({"height": height, "component": name, "rule": "repeated_hex",
                                       "pattern": match.group(), "offset": match.start(), "value": value})
            for word in ASCII_WORDS:
                start = raw.lower().find(word.encode("ascii"))
                if start >= 0:
                    candidates.append({"height": height, "component": name, "rule": "ascii_dictionary",
                                       "pattern": word, "offset": start, "value": value})
            for sequence in ("0123456789abcdef", "fedcba9876543210"):
                for start in range(9):
                    word = sequence[start:start + 8]
                    if word in value:
                        candidates.append({"height": height, "component": name, "rule": "eight_hex_sequence",
                                           "pattern": word, "offset": value.index(word), "value": value})
        if address.startswith("1CFB"):
            candidates.append({"height": height, "component": "p2pkh", "rule": "user_named_1CFB_prefix",
                               "pattern": "1CFB", "offset": 0, "value": address})
        for word in ADDRESS_WORDS:
            if word in address.lower():
                candidates.append({"height": height, "component": "p2pkh", "rule": "address_word_case_insensitive",
                                   "pattern": word, "offset": address.lower().index(word), "value": address})
    write_csv(out / "vanity_candidates.csv", candidates,
              ["height", "component", "rule", "pattern", "offset", "value"])
    prefixes = []
    for name, values in (("x", [k[1:33].hex() for k in keys]),
                         ("y", [k[33:].hex() for k in keys]),
                         ("hash160", [d.hex() for d in digests])):
        ordered = sorted(zip(values, heights))
        best = max(((common_prefix(a[0], b[0]), a, b) for a, b in zip(ordered, ordered[1:])), key=lambda t: t[0])
        length, a, b = best
        lam = len(keys) * (len(keys) - 1) / 2 / 16**length
        prefixes.append({"component": name, "hex_digits": length, "prefix": a[0][:length],
                         "heights": [a[1], b[1]], "expected_pairs_at_least_this_long": lam,
                         "p_birthday_poisson_approx": -math.expm1(-lam),
                         "p_bonferroni_three_components": min(1.0, 3 * -math.expm1(-lam))})
    run = longest_repeat["length"]
    opportunities = len(keys) * ((128 - run + 1) + (40 - run + 1))
    repeat_bound = min(1.0, opportunities * 16 ** (1 - run))
    hits = [{"height": h, "address": a} for h, a in zip(heights, addresses) if a.startswith("1CFB")]
    prob = prefix_probability("1CFB")
    return {"candidate_count": len(candidates), "rule_counts": dict(collections.Counter(c["rule"] for c in candidates)),
            "longest_repeated_hex": longest_repeat,
            "longest_repeat_familywise_union_bound": repeat_bound,
            "longest_common_prefixes": prefixes,
            "1CFB": {"hits": hits, "single_address_probability_approx": prob,
                     "expected_hits": len(keys) * prob,
                     "probability_at_least_one_approx": -math.expm1(len(keys) * math.log1p(-prob)),
                     "selection_caveat": "1CFB was selected from a known example, so this is chance calibration, not a discovery p-value."},
            "rules": {"hex_words": HEX_WORDS, "ascii_words_case_insensitive": ASCII_WORDS,
                      "address_words_case_insensitive": ADDRESS_WORDS,
                      "repeat": "at least 6 identical hex digits anywhere, or at least 4 at the start of XY/HASH160",
                      "sequence": "8 consecutive ascending or descending hexadecimal digits"},
            "interpretation": "Exploratory candidates are not evidence of intentional vanity. "
                              "No finite semantic dictionary excludes every recognizable string."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "patoshi_pubkeys_COMPLETE.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "analysis" / "phase1")
    parser.add_argument("--permutations", type=int, default=1999)
    args = parser.parse_args()
    if args.permutations < 1:
        parser.error("--permutations must be positive")
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    raw_csv = args.input.read_bytes()
    with args.input.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    records, malformed = [], []
    for line, row in enumerate(rows, 2):
        height = int(row["Block Height"])
        text = row["Address/Pubkey"]
        if not re.fullmatch(r"04[0-9a-fA-F]{128}", text):
            malformed.append({"line": line, "height": height, "reason": "invalid uncompressed hex encoding"})
            continue
        key = bytes.fromhex(text)
        if not valid_key(key):
            malformed.append({"line": line, "height": height, "reason": "not a secp256k1 curve point"})
        records.append((height, int(row["Output Index"]), key, Decimal(row["Amount (BTC)"]), row["Script Type"]))
    if malformed:
        (out / "malformed_keys.json").write_text(json.dumps(malformed, indent=2) + "\n", encoding="utf-8", newline="\n")
        raise ValueError("Malformed keys; stopped address derivation. See malformed_keys.json")
    records.sort(key=lambda r: (r[0], r[1]))
    heights = [r[0] for r in records]
    keys = [r[2] for r in records]
    digests = [hash160(key) for key in keys]
    addresses = [address_from_hash(d) for d in digests]
    for digest, address in zip(digests, addresses):
        decoded = b58decode(address)
        assert decoded[:21] == b"\0" + digest
        assert decoded[21:] == sha256(sha256(decoded[:21]))[:4]
    independent_validation = "unavailable"
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        for key in keys:
            parsed = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), key)
            assert parsed.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint) == key
        independent_validation = "all keys decoded and reserialized by cryptography/OpenSSL"
    except ImportError:
        pass
    derived = [{"block_height": h, "output_index": index, "amount_btc": str(amount),
                "pubkey_uncompressed": key.hex(), "hash160": digest.hex(), "p2pkh_address": address}
               for (h, index, key, amount, _), digest, address in zip(records, digests, addresses)]
    write_csv(ROOT / "patoshi_p2pkh_addresses.csv", derived)
    extractor_path = ROOT / "extract_patoshi_addresses.py"
    tree = ast.parse(extractor_path.read_text(encoding="utf-8"))
    extractor_heights = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                             and any(isinstance(t, ast.Name) and t.id == "PATOSHI_BLOCKS" for t in node.targets))
    csv_only = sorted(set(heights) - set(extractor_heights))
    write_csv(out / "csv_heights_absent_from_extractor.csv", ({"block_height": h} for h in csv_only), ["block_height"])
    total = sum((r[3] for r in records), Decimal(0))
    structural = {
        "rows": len(rows), "min_height": min(heights), "max_height": max(heights),
        "height_duplicates": len(heights) - len(set(heights)),
        "outpoint_coordinate_duplicates": len(records) - len(set((r[0], r[1]) for r in records)),
        "pubkey_duplicates": len(keys) - len(set(keys)), "hash160_duplicates": len(digests) - len(set(digests)),
        "address_duplicates": len(addresses) - len(set(addresses)),
        "x_coordinate_duplicates": len(keys) - len(set(k[1:33] for k in keys)),
        "all_rows_within_stated_range": all(3 <= h <= 49973 for h in heights),
        "input_sorted_by_height": [int(r["Block Height"]) for r in rows] == heights,
        "script_type_counts": dict(collections.Counter(r[4] for r in records)),
        "output_index_counts": dict(collections.Counter(r[1] for r in records)),
        "amount_counts": dict(collections.Counter(str(r[3]) for r in records)),
        "amount_exceptions": [{"height": h, "amount_btc": str(amount), "excess_over_50_btc": str(amount - 50)}
                              for h, _, _, amount, _ in records if amount != 50],
        "csv_total_btc": str(total), "fifty_per_row_btc": str(50 * len(rows)),
        "excess_over_fifty_per_row_btc": str(total - 50 * len(rows)),
        "malformed_keys": malformed, "independent_key_validation": independent_validation,
        "all_base58check_roundtrips_passed": True,
        "extractor_list_count": len(extractor_heights), "extractor_unique_heights": len(set(extractor_heights)),
        "csv_only_heights_count": len(csv_only),
        "extractor_only_heights": sorted(set(extractor_heights) - set(heights)),
    }
    print("Structural audit and address derivation complete", flush=True)
    gaps = gap_analysis(heights, out, args.permutations)
    print("Gap permutation tests complete", flush=True)
    random = randomness(keys, digests, heights, out)
    vanity = vanity_scan(keys, digests, addresses, heights, out)
    results = {
        "phase": "1: offline, CSV evidence only; zero on-chain verification",
        "source_sha256": hashlib.sha256(raw_csv).hexdigest(),
        "source_lf_normalized_sha256": hashlib.sha256(raw_csv.replace(b"\r\n", b"\n")).hexdigest(),
        "extractor_sha256": hashlib.sha256(extractor_path.read_bytes()).hexdigest(),
        "extractor_lf_normalized_sha256": hashlib.sha256(extractor_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "seed": SEED},
        "structure": structural, "gaps": gaps, "randomness": random, "vanity": vanity,
        "block_264": next((r for r in derived if r["block_height"] == 264), None),
    }
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n")
    artifacts = [args.input, extractor_path, Path(__file__), ROOT / "patoshi_p2pkh_addresses.csv"]
    artifacts += sorted(p for p in out.iterdir() if p.name != "manifest.json" and p.suffix in (".csv", ".json"))
    (out / "manifest.json").write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\', '/'):
                                               hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
    print(json.dumps({"structure": structural, "gap_runs": gaps["runs"],
                      "gap_nulls": gaps["permutation_nulls"], "significant": random["holm_significant"],
                      "vanity": vanity}, indent=2))


if __name__ == "__main__":
    main()
