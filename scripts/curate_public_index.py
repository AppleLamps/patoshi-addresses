"""Rebuild the curated index from its pinned pre-curation snapshot.

Usage: git show d87d1e348084f6c3c08c4ef5d5414c984a3762a1:docs/data.json |
       python scripts/curate_public_index.py
"""
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "analysis/public_index"
DOCS = ROOT / "docs"
BASELINE = "d87d1e348084f6c3c08c4ef5d5414c984a3762a1"


def read_by_height(path, key):
    with path.open(newline="", encoding="utf-8") as f:
        return {int(row[key]): row for row in csv.DictReader(f)}


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def curate(baseline, published, additions, model, census):
    schema = baseline["meta"]["schema"]
    source = {r[0]: dict(zip(schema, r)) for r in baseline["records"]}
    if len(source) != 22087 or len(published) != 21953 or len(additions) != 134:
        raise ValueError("Unexpected pre-curation counts")
    if published.keys() & additions.keys() or source.keys() != published.keys() | additions.keys():
        raise ValueError("Source lists do not partition the frozen public index")
    rejected_original = {h for h in published if model[h]["tier_m10"] == "listed_contradicted"}
    rejected_additions = {h for h in additions if model[h]["tier_m10"] == "other_miner"}
    if (len(rejected_original), len(rejected_additions)) != (12, 18):
        raise ValueError("Unexpected exclusion count; review before publishing")
    rejected = rejected_original | rejected_additions
    if any(census[h]["loo_label"] != "other" or not source[h]["spent"] for h in rejected):
        raise ValueError("An exclusion does not have the expected co-spend evidence")
    included = [r for h, r in source.items() if h not in rejected]
    excluded = []
    for h in sorted(rejected):
        c = census[h]
        excluded.append(dict(
            source[h],
            source_list="published_list" if h in rejected_original else "october_additions",
            exclusion_reason="Phase 5 co-spend classification points to another miner",
            phase10_tier=model[h]["tier_m10"],
            co_spend_label=c["loo_label"],
            cluster_id=c["cluster_id"],
            cluster_blocks=c["cluster_blocks"],
            co_members=c["co_members"],
            co_members_nonce_band_pass=c["co_members_pass"],
            census_spending_txids=c["spending_txids"],
        ))
    meta = dict(baseline["meta"])
    meta.update(
        count=len(included),
        published_count=len(published) - len(rejected_original),
        replication_confirmed_additions=sum(r["tier"] == "replication-confirmed" for r in included),
        confirmed_additions_spent=sum(r["spent"] for r in included if r["height"] in additions),
        confirmed_additions_unspent=sum(not r["spent"] for r in included
                                       if r["height"] in additions and r["tier"] != "candidate_95_plus"),
        original_list_exclusions=len(rejected_original),
        addition_exclusions=len(rejected_additions),
        total_original_sats=sum(r["original_sats"] for r in included),
        total_balance_sats=sum(r["balance_sats"] for r in included),
        spent_count=sum(r["spent"] for r in included),
        unspent_count=sum(not r["spent"] for r in included),
        first_height=min(r["height"] for r in included),
        last_height=max(r["height"] for r in included),
        note=("Curated index: 12 original-list and 18 October-addition entries excluded on co-spend evidence. "
              "Balances are original P2PK coinbase outpoints at the recorded spend snapshots, not live UTXO balances. "
              "Derived P2PKH-address activity is excluded."),
    )
    index = {"meta": meta, "records": [[r.get(k) for k in schema] for r in included]}
    return index, included, excluded


def main():
    index, _, excluded = curate(
        json.load(sys.stdin),
        read_by_height(ROOT / "patoshi_p2pkh_addresses.csv", "block_height"),
        read_by_height(AUDIT / "october_additions_source.csv", "block_height"),
        read_by_height(ROOT / "analysis/phase10_clock_model/posterior_m10.csv", "height"),
        read_by_height(ROOT / "analysis/phase5/census_blocks.csv", "height"),
    )
    manifest = {
        "baseline_commit": BASELINE,
        "excluded_heights": [r["height"] for r in excluded],
        "meta": index["meta"],
    }
    (DOCS / "data.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evidence_fields = [k for k in excluded[0] if k not in index["meta"]["schema"]]
    write_csv(AUDIT / "excluded_outpoints.csv", index["meta"]["schema"] + evidence_fields, excluded)


if __name__ == "__main__":
    main()
