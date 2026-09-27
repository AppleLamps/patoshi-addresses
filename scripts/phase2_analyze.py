"""Offline Phase 2 analysis and cache manifest. Safe to snapshot a running collector.

Only complete data permit full-set classifier/temporal claims. Never fetches HTTP.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3
import sys
import zlib
from datetime import datetime, timezone

import numpy as np

from phase2_collect import OUT, PIN, ROOT, atomic_json, inputs, now, sha


def no_network(event, args):
    if event in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.sendto"):
        raise RuntimeError("Analysis is strictly offline")


sys.addaudithook(no_network)


def csv_out(name, rows, columns):
    with (OUT / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def stats(values):
    if not values:
        return {"n": 0}
    x = np.array(values, dtype=float)
    return {"n": len(values), "min": float(x.min()), "median": float(np.median(x)), "mean": float(x.mean()), "p90": float(np.quantile(x, .9)), "p99": float(np.quantile(x, .99)), "max": float(x.max())}


def nonce_pass(nonce):
    return 0 <= nonce & 255 <= 9 or 19 <= nonce & 255 <= 58


def inner_pass(nonce):
    inner = int.from_bytes(nonce.to_bytes(4, "little"), "big")
    return inner < 163840000 or 327680000 <= inner < 983040000


def local_prediction(h, anchors, cb, headers):
    """Exploratory interpolation, explicitly not Lerner's unpublished tagger."""
    i = bisect.bisect_left(anchors, h)
    if i == 0 or i == len(anchors):
        return None
    a, b = anchors[i - 1], anchors[i]
    if h == b:
        if i + 1 == len(anchors):
            return None
        b = anchors[i + 1]
    if h - a > 200 or b - h > 200:
        return None
    ea, eb = cb[a].get("extra_nonce"), cb[b].get("extra_nonce")
    ta, tb, t = headers[a]["timestamp"], headers[b]["timestamp"], headers[h]["timestamp"]
    if ea is None or eb is None or eb < ea or not ta < t < tb or tb - ta > 172800:
        return None
    predicted = ea + (eb - ea) * (t - ta) / (tb - ta)
    return {"anchor_left": a, "anchor_right": b, "predicted_extra_nonce": predicted, "anchor_increment": eb - ea}


def classifier(heights, cb, headers, sample):
    # The original labels are a reference, never ground truth for miner identity.
    usable = [h for h in heights if h in headers and h in cb]
    control = [h for h in sample["controls"] if h in cb and h in headers]
    boundary = [h for h in sample["boundary"] if h in cb and h in headers]
    hist = []
    summary = {}
    for label, hs in [("listed", usable), ("unlisted_controls", control), ("boundary", boundary)]:
        counts = collections.Counter(headers[h]["nonce"] & 255 for h in hs)
        hist.extend({"group": label, "nonce_lsb": k, "count": counts[k]} for k in range(256))
        summary[label] = {"n": len(hs), "lsb_pass": sum(nonce_pass(headers[h]["nonce"]) for h in hs), "inner_range_pass": sum(inner_pass(headers[h]["nonce"]) for h in hs), "extra_nonce_parseable": sum(cb[h].get("extra_nonce") is not None for h in hs)}
    csv_out("nonce_histogram.csv", hist, ["group", "nonce_lsb", "count"])
    # Modulo-5 split fixed before collection: 60% anchors, 20% calibration, 20% evaluation.
    anchors = [h for h in usable if h % 5 in (0, 1, 2) and cb[h].get("extra_nonce") is not None]
    calibration, evaluation, full = [], [], []
    for label, hs in [("listed", usable), ("unlisted_controls", control), ("boundary", boundary)]:
        for h in hs:
            n = headers[h]["nonce"]
            row = {"group": label, "height": h, "nonce": n, "nonce_lsb": n & 255, "lsb_pass": nonce_pass(n), "inner_range_pass": inner_pass(n), "extra_nonce": cb[h].get("extra_nonce"), "interpolation_supported": False}
            # For anchors, local_prediction excludes the target itself. These are
            # explicitly leave-one-out diagnostic scores, never held-out evaluation.
            row["interpolation_role"] = ("calibration" if h % 5 == 3 else "held_out" if h % 5 == 4 else "anchor_leave_one_out") if label == "listed" else label
            prediction = local_prediction(h, anchors, cb, headers)
            if prediction and row["extra_nonce"] is not None:
                row.update(prediction)
                row["interpolation_supported"] = True
                row["absolute_residual"] = abs(row["extra_nonce"] - prediction["predicted_extra_nonce"])
                row["scaled_residual"] = row["absolute_residual"] / max(4, prediction["anchor_increment"])
                if label == "listed" and h % 5 in (3, 4):
                    (calibration if h % 5 == 3 else evaluation).append(row)
            full.append(row)
    threshold = float(np.quantile([r["scaled_residual"] for r in calibration], .95)) if len(calibration) >= 20 else None
    for row in full:
        if threshold is not None and row["interpolation_supported"]:
            row["extra_nonce_fit"] = row["scaled_residual"] <= threshold
            row["combined_fit"] = row["lsb_pass"] and row["extra_nonce_fit"]
    columns = ["group", "height", "nonce", "nonce_lsb", "lsb_pass", "inner_range_pass", "extra_nonce", "interpolation_role", "interpolation_supported", "anchor_left", "anchor_right", "predicted_extra_nonce", "anchor_increment", "absolute_residual", "scaled_residual", "extra_nonce_fit", "combined_fit"]
    csv_out("classifier_blocks.csv", full, columns)
    flags = [r for r in full if r["group"] == "listed" and (not r["lsb_pass"] or not r["inner_range_pass"] or r.get("extra_nonce_fit") is False)]
    csv_out("classifier_flags.csv", flags, columns)
    candidates = [r for r in full if r["group"] != "listed" and r["lsb_pass"]]
    csv_out("boundary_and_control_candidates.csv", candidates, columns)
    summary["interpolation"] = {"anchors": len(anchors), "calibration_n": len(calibration), "evaluation_n": len(evaluation), "calibration_95pct_scaled_residual": threshold, "evaluation_residual": stats([r["absolute_residual"] for r in evaluation]), "evaluation_combined_fit": sum(r.get("combined_fit", False) for r in evaluation), "listed_flag_count": len(flags), "limitations": "Interpolation threshold is learned from reference labels; not an independent replication of the original manual/algorithmic label assignment. Unsupported blocks remain unclassified. Flags require review, not automatic relabeling."}
    for label in ("listed", "unlisted_controls", "boundary"):
        rs = [r for r in full if r["group"] == label and "combined_fit" in r]
        summary[label].update(combined_evaluable=len(rs), combined_pass=sum(r["combined_fit"] for r in rs))
    pairs = []
    for a, b in zip(usable, usable[1:]):
        ea, eb = cb[a].get("extra_nonce"), cb[b].get("extra_nonce")
        if ea is None or eb is None:
            continue
        delta, dt, gap = eb - ea, headers[b]["timestamp"] - headers[a]["timestamp"], b - a
        pairs.append({"height_left": a, "height_right": b, "height_delta": gap, "seconds": dt, "extra_nonce_delta": delta, "increment_per_hour": delta * 3600 / dt if delta >= 0 and dt > 0 else "", "fewer_increments_than_height_delta": 0 <= delta < gap, "decrease_or_reset_candidate": delta < 0})
    csv_out("extra_nonce_increments.csv", pairs, list(pairs[0]) if pairs else ["height_left", "height_right"])
    summary["increments"] = {"pairs": len(pairs), "negative_deltas": sum(r["extra_nonce_delta"] < 0 for r in pairs), "zero_deltas": sum(r["extra_nonce_delta"] == 0 for r in pairs), "nonnegative_deltas_smaller_than_height_delta": sum(r["fewer_increments_than_height_delta"] for r in pairs), "positive_time_nonnegative_increment_rate_per_hour": stats([r["increment_per_hour"] for r in pairs if r["increment_per_hour"] != ""])}
    # Control sample combines unknown miners; consecutive-control increments are descriptive only.
    summary["control_adjacent_extra_nonce_delta"] = stats([cb[b]["extra_nonce"] - cb[a]["extra_nonce"] for a, b in zip(control, control[1:]) if cb[a].get("extra_nonce") is not None and cb[b].get("extra_nonce") is not None])
    return summary


def temporal(heights, headers, permutations):
    hs = np.arange(3, 49974)
    timestamps = np.array([headers[int(h)]["timestamp"] for h in hs])
    labels = np.isin(hs, heights)
    hours = (timestamps // 3600 % 24).astype(int)
    weekdays = ((timestamps // 86400 + 3) % 7).astype(int)  # Monday=0.
    strata = [np.flatnonzero(hs // 1000 == k) for k in range(50)]
    tests, tables = [], []
    for name, cats, size in [("hour_utc", hours, 24), ("weekday_utc", weekdays, 7)]:
        expected = np.zeros(size)
        for ids in strata:
            expected += np.bincount(cats[ids], minlength=size) * labels[ids].mean()
        observed = np.bincount(cats[labels], minlength=size)
        statistic = float(np.sum((observed - expected) ** 2 / expected))
        tests.append({"name": name, "statistic": statistic, "exceedances": 0})
        for k in range(size):
            total = int(np.sum(cats == k))
            tables.append({"group": name, "bin": k, "listed": int(observed[k]), "all_blocks": total, "listed_fraction": float(observed[k] / total), "stratified_expected": float(expected[k])})
    rng = np.random.default_rng(20260927)
    expected_by_test = [np.array([r["stratified_expected"] for r in tables if r["group"] == t["name"]]) for t in tests]
    for _ in range(permutations):
        perm = labels.copy()
        for ids in strata:
            perm[ids] = np.roll(labels[ids], int(rng.integers(len(ids))))
        for t, cats, expected in zip(tests, [hours, weekdays], expected_by_test):
            obs = np.bincount(cats[perm], minlength=len(expected))
            statistic = float(np.sum((obs - expected) ** 2 / expected))
            t["exceedances"] += statistic >= t["statistic"] - 1e-12
    for t in tests:
        t["p"] = (1 + t.pop("exceedances")) / (permutations + 1)
    running = 0
    for i, t in enumerate(sorted(tests, key=lambda t: t["p"])):
        running = max(running, (len(tests) - i) * t["p"])
        t["holm_p"] = min(1, running)
    csv_out("temporal_distributions.csv", tables, list(tables[0]))
    gaps = []
    for a, b in zip(heights, heights[1:]):
        ta, tb = headers[a]["timestamp"], headers[b]["timestamp"]
        gaps.append({"height_left": a, "height_right": b, "missing_heights": b - a - 1, "seconds": tb - ta, "left_utc": datetime.fromtimestamp(ta, timezone.utc).isoformat(), "right_utc": datetime.fromtimestamp(tb, timezone.utc).isoformat()})
    csv_out("temporal_gaps.csv", sorted(gaps, key=lambda r: r["seconds"], reverse=True), list(gaps[0]))
    windows = []
    height_set = set(heights)
    for ids in strata:
        start, end = int(hs[ids[0]]), int(hs[ids[-1]])
        selected = [int(h) for h in hs[ids] if int(h) in height_set]
        windows.append({"start_height": start, "end_height": end, "listed": len(selected), "total": len(ids), "listed_fraction": len(selected) / len(ids), "first_timestamp": int(timestamps[ids[0]]), "last_timestamp": int(timestamps[ids[-1]]), "lsb_pass": sum(nonce_pass(headers[h]["nonce"]) for h in selected)})
    csv_out("temporal_height_windows.csv", windows, list(windows[0]))
    changes = sorted([{"boundary_height": b["start_height"], "fraction_change": b["listed_fraction"] - a["listed_fraction"]} for a, b in zip(windows, windows[1:])], key=lambda r: abs(r["fraction_change"]), reverse=True)
    return {"inter_listed_timestamp_seconds": stats([g["seconds"] for g in gaps]), "timestamp_reversals": sum(g["seconds"] < 0 for g in gaps), "gaps_exceeding_hours": {str(t): sum(g["seconds"] > t * 3600 for g in gaps) for t in (6, 12, 24, 48, 72)}, "longest_gaps": sorted(gaps, key=lambda r: r["seconds"], reverse=True)[:10], "schedule_tests": tests, "permutations": permutations, "null": "Independent circular shifts of the listed-label sequence within each 1000-height stratum, preserving counts and most local serial dependence. Pearson discrepancy against per-stratum all-block timestamp exposure. Two hypotheses, Holm correction. This null is an approximation, not a human sleep detector.", "largest_adjacent_1000_height_density_changes": changes[:10]}


def manifest(db):
    """Hash every decompressed cached body; stable compressed receipt export."""
    columns = ["response_id", "height", "endpoint", "host", "attempt", "fetched_at", "status", "sha256", "body_bytes", "error"]
    path = OUT / "response_manifest.csv.gz"
    total, digest = 0, hashlib.sha256()
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
            with io.TextIOWrapper(gz, encoding="utf-8", newline="") as text:
                w = csv.writer(text, lineterminator="\n")
                w.writerow(columns)
                for row in db.execute("SELECT id,height,endpoint,host,attempt,fetched_at,status,sha256,body_zlib,error FROM responses ORDER BY id"):
                    body = zlib.decompress(row[8])
                    assert sha(body) == row[7], f"Cache checksum failed at response {row[0]}"
                    receipt = [*row[:8], len(body), row[9]]
                    w.writerow(receipt)
                    digest.update((json.dumps(receipt, separators=(",", ":")) + "\n").encode())
                    total += 1
    return {"response_count": total, "logical_receipt_sha256": digest.hexdigest(), "manifest_sha256": sha(path.read_bytes()), "raw_cache": "analysis/phase2/cache/chain.sqlite3", "body_encoding": "zlib compressed exact response bytes in responses.body_zlib", "all_body_checksums_verified": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--permutations", type=int, default=1999)
    args = p.parse_args()
    heights, rows = inputs()
    dbpath = OUT / "cache/chain.sqlite3"
    db = sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True)
    db.execute("BEGIN")  # Consistent snapshot while background collection continues.
    data = collections.defaultdict(dict)
    for kind, h, body in db.execute("SELECT kind,height,data FROM results"):
        data[kind][h] = json.loads(body)
    failures = [dict(zip(["stage", "height", "at", "error"], r)) for r in db.execute("SELECT stage,height,at,error FROM failures ORDER BY stage,height")]
    receipts = manifest(db)
    db.rollback()
    db.close()
    cb, spends, inc, headers = (data[k] for k in ("coinbase", "spend", "inclusion", "header"))
    output = []
    for h in heights:
        c, s = cb.get(h), spends.get(h)
        row = {"height": h, "csv_pubkey": rows[h]["Address/Pubkey"], "pubkey_status": "unknown", "spend_status": "unknown", "inclusion_verified": h in inc}
        if c:
            row.update({k: c.get(k) for k in ("block_hash", "txid", "chain_pubkey", "scriptpubkey", "value_sats", "csv_value_sats", "amount_match", "scriptsig", "sequence", "extra_nonce", "parse_status")})
            row["pubkey_status"] = "match" if c["pubkey_match"] else "mismatch"
            row["pubkey_observed_at"] = c["tx_response"]["observed_at"]
        if s:
            row.update(spend_status="spent" if s["spent"] else "unspent", spending_txid=s.get("spending_txid"), spend_observed_at=s["response"]["observed_at"], spending_input_verified=s.get("spending_input_verified", False))
        output.append(row)
    cols = ["height", "csv_pubkey", "chain_pubkey", "scriptpubkey", "pubkey_status", "block_hash", "txid", "value_sats", "csv_value_sats", "amount_match", "pubkey_observed_at", "inclusion_verified", "scriptsig", "sequence", "extra_nonce", "parse_status", "spend_status", "spending_txid", "spend_observed_at", "spending_input_verified"]
    csv_out("verification.csv", output, cols)
    mismatches = [r for r in output if r["pubkey_status"] == "mismatch"]
    spent = [r for r in output if r["spend_status"] == "spent"]
    csv_out("pubkey_mismatches.csv", mismatches, cols)
    csv_out("spent_outputs.csv", spent, cols)
    csv_out("amount_mismatches.csv", [r for r in output if r.get("amount_match") is False], cols)
    csv_out("failures.csv", failures, ["stage", "height", "at", "error"])
    csv_out("headers.csv", [headers[h] for h in sorted(headers)], ["height", "id", "version", "timestamp", "mediantime", "nonce", "bits", "merkle_root", "previousblockhash", "tx_count", "header_hex"])
    counts = {"pinned_heights": len(heights), "coinbases_fetched": sum(h in cb for h in heights), "pubkey_matches": sum(r["pubkey_status"] == "match" for r in output), "pubkey_mismatches": len(mismatches), "pubkey_unknown": sum(r["pubkey_status"] == "unknown" for r in output), "inclusion_verified": sum(h in inc for h in heights), "spent": len(spent), "unspent": sum(r["spend_status"] == "unspent" for r in output), "spend_unknown": sum(r["spend_status"] == "unknown" for r in output)}
    summary = {"snapshot_at": now(), "counts": counts, "cache_manifest": receipts, "pinned_height_sha256": PIN, "failures": len(failures), "complete": False}
    sample_path = OUT / "selection.json"
    if sample_path.exists():
        sample = json.loads(sample_path.read_text())
        all_samples = set(sample["controls"] + sample["boundary"])
        ready = all(h in headers for h in range(sample["maximum_header_height"] + 1)) and all(h in cb and h in inc for h in heights) and all(h in cb and h in inc for h in all_samples)
        summary["analysis_ready"] = ready
        summary["sample_coverage"] = {"controls_expected": len(sample["controls"]), "controls_fetched": sum(h in cb for h in sample["controls"]), "boundary_expected": len(sample["boundary"]), "boundary_fetched": sum(h in cb for h in sample["boundary"])}
        if ready:
            summary["classifier"] = classifier(heights, cb, headers, sample)
            summary["temporal"] = temporal(heights, headers, args.permutations)
            summary["complete"] = counts["spend_unknown"] == 0 and not failures
    atomic_json(OUT / "summary.json", summary)
    report(summary, mismatches, spent)
    print(json.dumps(summary, indent=2))


def report(s, mismatches, spent):
    c = s["counts"]
    status = "COMPLETE COLLECTION" if s["complete"] else "IN PROGRESS / INCOMPLETE COVERAGE"
    matched = c["pubkey_matches"] / c["coinbases_fetched"] * 100 if c["coinbases_fetched"] else 0
    text = f"""# Phase 2 chain verification

**{status}.** Snapshot: {s['snapshot_at']}. Input: pinned Lopp September 2022 list, 21,953 heights, SHA-256 `{PIN}`.

Labels: **(a)** verified blockchain content or explicitly dated explorer observation; **(b)** statistical inference with stated method; **(c)** speculation. Explorer assertions about unspent status are not cryptographic proofs of the current UTXO set. No identity of the miner is assumed.

## Verified facts

**(a)** The four mandatory controls reproduce exactly: height 2817 = 52.01 BTC; 19863 = 50.14; 23079 = 50.12; 28507 = 50.22. Their CSV pubkeys, reconstructed transaction IDs, Merkle roots, header hashes and proof of work pass. [Control evidence](controls.json).

**(a)** Pubkey scripts checked: **{c['coinbases_fetched']:,}/21,953**. Matches: **{c['pubkey_matches']:,}** ({matched:.6f}% of fetched); mismatches: **{c['pubkey_mismatches']:,}**; unknown: **{c['pubkey_unknown']:,}**. Inclusion in a validated block header checked for **{c['inclusion_verified']:,}** listed coinbases. Exact scripts, keys, amounts and observation times: [all 21,953 statuses](verification.csv); [every mismatch](pubkey_mismatches.csv).

**(a)** Dated outpoint observations: **{c['unspent']:,} unspent**, **{c['spent']:,} spent**, **{c['spend_unknown']:,} unknown**. [Spent outputs](spent_outputs.csv) contains each observed spender and amount; a reported spender is accepted only after reconstructing its transaction ID and checking its input against the coinbase outpoint. Historical cached observations are never refreshed; this is not a simultaneous current-state snapshot.

## Findings and null results

"""
    if mismatches:
        text += "**(a)** Pubkey mismatches require individual investigation; no mismatch is discarded. Heights: " + ", ".join(str(r["height"]) for r in mismatches) + ".\n\n"
    else:
        text += "**(a)** No pubkey mismatch among the fetched rows. This statement does not extend to unknown rows.\n\n"
    if spent:
        text += "**(a)** Spends were observed at heights " + ", ".join(str(r["height"]) for r in spent) + ". A spend does not itself establish miner identity or historical novelty.\n\n"
    if "classifier" in s:
        k = s["classifier"]
        text += f"**(a)** Listed nonce LSB rule passes: {k['listed']['lsb_pass']:,}/{k['listed']['n']:,}; unlisted sampled controls: {k['unlisted_controls']['lsb_pass']:,}/{k['unlisted_controls']['n']:,}. The stricter byte-reversed inner-nonce bounds are tabulated separately.\n\n"
        x = k["interpolation"]
        text += f"**(b)** The independently implemented extraNonce consistency model uses listed anchors, separate calibration and evaluation partitions. Supported evaluation blocks passing the combined signature: {x['evaluation_combined_fit']}/{x['evaluation_n']}. Listed review flags: {x['listed_flag_count']}. See [every classifier result](classifier_blocks.csv), [flags](classifier_flags.csv), [unlisted candidates](boundary_and_control_candidates.csv). These are consistency flags, not proven misclassifications; this model does not reproduce the original undocumented labeling decisions.\n\n"
        t = s["temporal"]
        text += "**(b)** Time-of-day and weekday tests use 1,000-height strata and circular-shift permutations, with Holm correction across the two tests: " + "; ".join(f"{r['name']} adjusted p={r['holm_p']:.6g}" for r in t["schedule_tests"]) + ". [Distributions](temporal_distributions.csv); [timestamp gaps](temporal_gaps.csv).\n\n"
        longest = t["longest_gaps"][0]
        text += f"**(a)** Longest consecutive-listed header-time gap: {longest['seconds'] / 86400:.4f} days, heights {longest['height_left']} to {longest['height_right']}. Negative timestamp deltas: {t['timestamp_reversals']}. Header timestamps are miner-supplied; they are not precise arrival times or evidence of sleep.\n\n"
    else:
        text += "Classifier, temporal and boundary results are pending complete headers and sampled coinbases. No partial-run null is presented as a full-set conclusion.\n\n"
    text += f"""## Open questions and limits

**(b)** Validating keys establishes what the pinned CSV represents, not who mined those blocks. Attribution needs stronger, independently assessed evidence. Unlisted blocks are controls by list membership, not known different miners. Sampled boundary coverage cannot establish completeness beyond the tested ranges.

**(c)** Human schedules, sleep cycles, intentional mining pauses, and Patoshi = Satoshi remain hypotheses. Repeated temporal patterns surviving exposure and serial-dependence controls, independent arrival-time evidence and historical corroboration would be needed to strengthen them.

Outstanding fetch/validation failure records: **{s['failures']}**; [details](failures.csv). Unknowns are never treated as matches or unspent. The local immutable cache has **{s['cache_manifest']['response_count']:,}** responses; every body checksum in this snapshot was verified. [Manifest](response_manifest.csv.gz), [machine-readable summary](summary.json), [methods and resumption](METHODS.md).

## Sources

- [mempool.space API](https://mempool.space/docs/api/rest); [Esplora endpoint documentation and response definitions](https://github.com/Blockstream/esplora/blob/master/API.md).
- [Pinned Lopp list](https://github.com/jlopp/bitcoin-utils/blob/45b9eb0f0d71dc7dd66c51fd3058943c1f6df0cb/findPatoshiMiningStreaks.php).
- [Lerner 2013 extraNonce labeling](https://bitslog.com/2013/04/24/satoshi-s-fortune-a-more-accurate-figure/); [2013 nonce observation](https://bitslog.com/2013/09/03/new-mystery-about-satoshi/); [2019 nonce-range and increment discussion](https://bitslog.com/2019/04/16/the-return-of-the-deniers-and-the-revenge-of-patoshi/); [2020 refined inner-nonce boundaries](https://bitslog.com/2020/08/22/the-patoshi-mining-machine/).

No novelty claim is made solely from agreement or disagreement with this reference list.
"""
    (OUT / "REPORT.md").write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
