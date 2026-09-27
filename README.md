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

No network access is used by this analysis. Attribution and spend status remain
unverified until a separate on-chain audit.
