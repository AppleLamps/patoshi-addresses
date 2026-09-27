#!/usr/bin/env python3
"""Reproduce secondary source/history checks from the local download cache.

Requires ignored cached originals and commit patches; re-fetch their receipt URLs
with cache_provenance_sources.py if absent. This script itself is entirely offline.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from provenance_compare import canonical_sha, external_list

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / "analysis" / "provenance" / "sources"
    # Verify all available cached bodies, including any failed responses.
    for metadata in directory.glob("*.metadata.json"):
        record = json.loads(metadata.read_text(encoding="utf-8"))
        body = directory / metadata.name.removesuffix(".metadata.json")
        if body.exists() and hashlib.sha256(body.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"Cached response hash mismatch: {body}")
    def successful_bytes(name):
        receipt = json.loads((directory / (name + ".metadata.json")).read_text(encoding="utf-8"))
        if receipt["status"] != 200:
            raise ValueError(f"Source was not retrieved successfully: {name}")
        return (directory / name).read_bytes()
    checks = {}
    for local, remote in (("patoshi_pubkeys_COMPLETE.csv", "bensig_csv.csv"),
                          ("extract_patoshi_addresses.py", "bensig_extractor.py")):
        a = (ROOT / local).read_bytes().replace(b"\r\n", b"\n")
        b = successful_bytes(remote)
        checks[local] = {"lf_normalized_identical_to_bensig": a == b,
                         "lf_sha256": hashlib.sha256(a).hexdigest()}
    for a, b in (("lopp_streaks_2022.php", "lopp_streaks.php"),
                 ("tehran_patoshiBlocks_initial.js", "tehran_patoshiBlocks.js")):
        checks[a] = {"identical_to_current_cached_copy": successful_bytes(a) == successful_bytes(b),
                     "other": b}
    successful_bytes("lopp_deltas.php")
    secondary = external_list(directory / "lopp_deltas.php")
    primary = external_list(directory / "lopp_streaks_2022.php")
    checks["lopp_secondary_list"] = {"count": len(secondary), "identical_to_primary_sequence": secondary == primary,
                                      "canonical_set_sha256": canonical_sha(secondary)}
    checks["history"] = {}
    for key, filename in (("lopp", "lopp_commit.patch"), ("tehran", "tehran_commit.patch")):
        text = successful_bytes(filename).decode("utf-8")
        checks["history"][key] = {
            "commit": re.search(r"^From ([a-f0-9]{40}) ", text).group(1),
            "date_header": re.search(r"^Date: (.*)$", text, re.M).group(1),
            "subject": re.search(r"^Subject: (.*)$", text, re.M).group(1),
        }
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    checks["local_initial_commit"] = {
        "commit": "414637ce52aa4819926bf1934b2235ed182a0280",
        "committer_date": git("show", "-s", "--format=%cI", "414637c").strip(),
        "source_file_commits": git("log", "--format=%H", "--", "extract_patoshi_addresses.py",
                                    "patoshi_pubkeys_COMPLETE.csv").splitlines(),
    }
    (directory.parent / "source_checks.json").write_text(json.dumps(checks, indent=2) + "\n",
                                                         encoding="utf-8", newline="\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
