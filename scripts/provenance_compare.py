#!/usr/bin/env python3
"""Offline set/provenance comparison. Does not fetch or execute upstream code.

Run from anywhere: python scripts/provenance_compare.py
Optional cached upstream lists: --source name=path (repeatable).
Files must contain a JSON integer array, a JavaScript/PHP patoshiBlocks integer array,
or a newline/comma/whitespace-delimited list of integer heights.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def table(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def script_list(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    return next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "PATOSHI_BLOCKS" for t in node.targets))


def external_list(path):
    text = path.read_text(encoding="utf-8-sig")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        found = re.search(r"\b(?:patoshiBlocks|PATOSHI_BLOCKS)\s*=\s*(?:\[|array\s*\()([\s\S]*?)(?:\]|\))", text)
        if found:
            text = found.group(1)
        if not re.fullmatch(r"[\d\s,]+", text):
            raise ValueError(f"Unrecognized integer-list format: {path}")
        value = [int(n) for n in re.findall(r"\d+", text)]
    if not isinstance(value, list) or not all(type(h) is int and h >= 0 for h in value):
        raise ValueError(f"Expected array of nonnegative integer heights: {path}")
    if not value:
        raise ValueError(f"Empty list: {path}")
    return value


def canonical_sha(heights):
    return hashlib.sha256(("\n".join(map(str, sorted(set(heights)))) + "\n").encode()).hexdigest()


def distribution(values):
    values = sorted(values)
    if not values:
        return None
    n = len(values)
    return {"n": n, "min": values[0], "median": statistics.median(values),
            "mean": statistics.mean(values), "p90_nearest_rank": values[math.ceil(.90*n)-1],
            "p99_nearest_rank": values[math.ceil(.99*n)-1], "max": values[-1]}


def gap_rows(name, heights):
    return [{"set": name, "left_height": a, "right_height": b, "delta": b-a, "missing_between": b-a-1}
            for a, b in zip(heights, heights[1:])]


def missing_rank_runs(full, selected):
    result = []
    for missing, group in itertools.groupby(enumerate(full, 1), key=lambda ih: ih[1] not in selected):
        if missing:
            rows = list(group)
            result.append({"first_csv_rank_1based": rows[0][0], "last_csv_rank_1based": rows[-1][0],
                           "first_height": rows[0][1], "last_height": rows[-1][1], "omitted_csv_rows": len(rows)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", default=[], help="name=local_path")
    args = parser.parse_args()
    out = ROOT / "analysis" / "provenance"
    out.mkdir(parents=True, exist_ok=True)
    extractor_path, csv_path = ROOT / "extract_patoshi_addresses.py", ROOT / "patoshi_pubkeys_COMPLETE.csv"
    extractor = script_list(extractor_path)
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_heights = [int(r["Block Height"]) for r in csv.DictReader(handle)]
    sets = {"extractor": extractor, "csv": csv_heights}
    sources = {"extractor": extractor_path, "csv": csv_path}
    for specification in args.source:
        name, source_path = specification.split("=", 1)
        if name in sets or not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
            raise ValueError("Source names must be distinct simple identifiers")
        path = Path(source_path)
        sets[name] = external_list(path)
        sources[name] = path
    summary = {}
    for name, heights in sets.items():
        ordered = sorted(set(heights))
        deltas = [b-a for a, b in zip(ordered, ordered[1:])]
        summary[name] = {"rows": len(heights), "unique": len(ordered), "duplicates": len(heights)-len(ordered),
                         "sorted": heights == sorted(heights), "heights": distribution(ordered),
                         "interlisted_delta": distribution(deltas), "canonical_set_sha256": canonical_sha(heights),
                         "source_file": str(sources[name].resolve().relative_to(ROOT)).replace("\\", "/"),
                         "source_raw_sha256": hashlib.sha256(sources[name].read_bytes()).hexdigest(),
                         "source_lf_sha256": hashlib.sha256(sources[name].read_bytes().replace(b"\r\n", b"\n")).hexdigest()}
        if name == "lopp":
            (out / "lopp_patoshi_heights.txt").write_text("\n".join(map(str, ordered)) + "\n",
                                                        encoding="utf-8", newline="\n")
    pairwise = []
    for left, right in itertools.combinations(sets, 2):
        a, b = set(sets[left]), set(sets[right])
        differences = [{"side": left, "height": h} for h in sorted(a-b)] + [
                       {"side": right, "height": h} for h in sorted(b-a)]
        table(out / f"difference_{left}_vs_{right}.csv", differences, ["side", "height"])
        pairwise.append({"left": left, "right": right, "intersection": len(a&b),
                         "left_only": len(a-b), "right_only": len(b-a), "union": len(a|b),
                         "jaccard": len(a&b)/len(a|b), "identical_sequence": sets[left] == sets[right]})
    e, c = set(extractor), set(csv_heights)
    extra = sorted(c-e)
    full = sorted(c)
    prefix = next((i for i,h in enumerate(full) if h not in e), len(full))
    cutoff = full[prefix-1] if prefix else None
    groups = {"extractor": sorted(e), "csv_only": extra, "csv": full}
    windows = []
    for width in (1000, 5000):
        for start in range(0, 50000, width):
            low, high = max(3, start), min(start+width-1, 49973)
            row = {"width": width, "low": low, "high": high, "span": high-low+1}
            for name, heights in groups.items():
                count = sum(low <= h <= high for h in heights)
                row[name] = count
                row[name+"_density"] = count/(high-low+1)
            windows.append(row)
    table(out / "height_windows.csv", windows, list(windows[0]))
    gaps = [row for name, heights in groups.items() for row in gap_rows(name, heights)]
    table(out / "consecutive_height_gaps.csv", gaps, ["set", "left_height", "right_height", "delta", "missing_between"])
    ranks = missing_rank_runs(full, e)
    table(out / "omitted_csv_rank_runs.csv", ranks,
          ["first_csv_rank_1based", "last_csv_rank_1based", "first_height", "last_height", "omitted_csv_rows"])
    # A two-sample empirical KS distance is descriptive here: height selection
    # differs by construction. No miner/classifier inference is licensed by it.
    count_e = count_x = 0
    ks = 0
    for height in full:
        count_e += height in e
        count_x += height not in e
        ks = max(ks, abs(count_e / len(e) - count_x / len(extra)))
    log_random_prefix = sum(math.log10((len(e)-j)/(len(c)-j)) for j in range(prefix))
    transition = []
    for low, high in ((3, 8044), (8045, 10319), (10320, 49972), (49973, 49973),
                      (6045, 8044), (8045, 10044)):
        transition.append({"low": low, "high": high, "span": high-low+1,
                           **{name: sum(low <= h <= high for h in heights) for name, heights in groups.items()}})
    script_text = extractor_path.read_text(encoding="utf-8")
    script_tree = ast.parse(script_text)
    assignment = next(n for n in script_tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "PATOSHI_BLOCKS" for t in n.targets))
    archaeology = {"assignment_line": assignment.lineno, "assignment_end_line": assignment.end_lineno,
                   "assignment_line_characters": len(script_text.splitlines()[assignment.lineno-1]),
                   "list_entry_count": len(extractor), "last_entries": extractor[-30:],
                   "functions": {n.name: {"line": n.lineno, "end_line": n.end_lineno} for n in script_tree.body
                                 if isinstance(n, ast.FunctionDef)}}
    result = {"artifacts": summary, "pairwise": pairwise, "script_archaeology": archaeology,
              "local": {"strict_subset": e < c, "csv_only_count": len(extra),
                        "csv_only_heights": distribution(extra),
                        "csv_only_interlisted_delta": distribution([b-a for a,b in zip(extra, extra[1:])]),
                        "matching_initial_csv_prefix_rows": prefix, "last_prefix_height": cutoff,
                        "first_omitted_height": full[prefix], "extractor_tail_after_prefix": [h for h in extractor if h > cutoff],
                        "descriptive_height_KS_distance_extractor_vs_extra": ks,
                        "log10_probability_initial_prefix_under_uniform_random_subset": log_random_prefix,
                        "transition_windows": transition,
                        "largest_omitted_csv_rank_runs": sorted(ranks, key=lambda r: -r["omitted_csv_rows"])[:10],
                        "largest_gaps": {name: sorted([g for g in gaps if g["set"] == name], key=lambda g: -g["delta"])[:8]
                                         for name in groups}}}
    dump(out / "comparison.json", result)
    table(out / "pairwise.csv", pairwise, list(pairwise[0]))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
