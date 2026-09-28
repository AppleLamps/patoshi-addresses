# Patoshi Addresses

Dataset of 21,953 Bitcoin blocks attributed to the hypothesized "Patoshi" miner,
with their public keys. Attribution, completeness, and the hypothesis that Patoshi
was Satoshi Nakamoto require independent verification.

## Credits

Based on the work of:
- **Sergio Demian Lerner** ([@SDLerner](https://github.com/SDLerner)) - Discovered the Patoshi pattern
- **Jameson Lopp** ([@jlopp](https://github.com/jlopp)) - Curated the Patoshi blocks dataset

## Dataset

- **Blocks**: 21,953 (blocks 3-49,973)
- **Total BTC in CSV**: 1,097,652.49 BTC (1,097,650 BTC at 50 per row, plus 2.49 BTC)
- **Format**: CSV with columns: Block Height, Output Index, Address/Pubkey, Amount (BTC), Script Type

## Usage

```bash
# Extract the 6,183 heights in the bundled script (not the full CSV)
python3 extract_patoshi_addresses.py

# View the data
head patoshi_pubkeys_COMPLETE.csv
```

## Files

- `patoshi_pubkeys_COMPLETE.csv` - The complete dataset
- `extract_patoshi_addresses.py` - Script to generate the dataset from block numbers
- `README.md` - This file

## Independent offline audit

See [the Phase 1 report](analysis/phase1/REPORT.md) for the reproducible CSV-only audit,
including its limitations. It finds four amounts above 50 BTC (CSV total
**1,097,652.49 BTC**) and 15,770 CSV heights absent from the bundled extractor's
input list. These are local observations, not independent on-chain verification.

- [Derived P2PKH addresses](patoshi_p2pkh_addresses.csv) preserve the original
  public keys, amounts, heights and output indexes. These encodings do not replace
  the original P2PK output scripts and cannot alone establish spend status.
- [Offline analysis script](scripts/phase1_offline.py), with dependencies in
  `requirements-analysis.txt`.
- [Gap maps, statistical tests and provenance hashes](analysis/phase1/).

```bash
python -m unittest discover -s tests -v
python scripts/phase1_offline.py --permutations 1999
```

No network access is used by the Phase 1 analysis. See the completed Phase 2
verification below for chain-data comparisons and spend status.

## Provenance investigation

The [provenance report](analysis/provenance/REPORT.md) establishes that the CSV's
21,953 heights exactly match Lopp's published 2022 list and the list in
`tehran19r/TaintedBySatoshi`, in the same order. The extractor is a strict subset:
6,183 shared heights, zero extractor-only heights, and 15,770 CSV-only heights.

Use the [pinned Lopp height list](analysis/provenance/lopp_patoshi_heights.txt) as
the declared population for subsequent verification. Exact list agreement does
not independently verify the CSV's pubkeys, amounts, spend status or miner attribution.
The [comparison script](scripts/provenance_compare.py) and
[reproduction instructions](analysis/provenance/METHODS.md) work offline using
the committed source snapshots.

## Phase 2 — BigQuery chain verification

The [verification report](analysis/phase2_bigquery/REPORT.md) finds **21,953/21,953
pubkey matches** and **31 live-confirmed spent coinbase outputs (1,550 BTC)**.
The remaining 21,922 have no spend in the BigQuery input index through its
September 27, 2026 watermark; they were not individually rechecked live.
The spend count reproduces published research and does not establish miner identity.

[SQL and methods](analysis/phase2_bigquery/METHODS.md),
[every output's status](analysis/phase2_bigquery/spend_status_all.csv),
[cached query results](analysis/phase2_bigquery/results/), and
[checksums](analysis/phase2_bigquery/manifest.json) are committed for reproduction.
The earlier API collector was stopped when BigQuery was selected and must not be resumed.

## Phase 3 — novelty hunt

The [novelty report](analysis/phase3/REPORT.md) separates bounded new measurements
from established findings. It adds downstream transaction paths, a P2PKH funding
census, reset-time tests, and an exploratory slope classifier. No demonstrated
key weakness, hash collision, embedded message, or new miner attribution was found.
The [Debian OpenSSL follow-up](analysis/phase3/debian/REPORT.md) screens 7,339,808
modeled keygen slots against the full CSV, with nine published weak-key validation
vectors. It finds zero matches within that stated space; other process histories
remain untested. Every novelty candidate states its prior-art comparison and
limitations.

[Methods](analysis/phase3/METHODS.md) · [Literature ledger](analysis/phase3/SOURCES.md)
· [Cached BigQuery results](analysis/phase3/results/) · [Manifest](analysis/phase3/manifest.json).
