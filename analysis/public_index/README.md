# Public index exclusions

The November 28, 2026 curation excludes 30 coinbase outputs from the searchable index, CSV/JSON downloads and headline totals. It does not change the historical research datasets or treat a co-spend heuristic as proof of a miner's identity.

- **12** original-list placements: Phase 10 retained the Phase 8 `listed_contradicted` tier.
- **18** October additions: Phase 10 marks them `other_miner`. All 30 exclusions have a Phase 5 leave-one-out co-spend label of `other`.

[`excluded_outpoints.csv`](excluded_outpoints.csv) records the previous public row, the source list, the Phase 10 tier, the co-spend cluster, the other early-reward inputs and how many passed the nonce band, and the spending transaction. [`october_additions_source.csv`](october_additions_source.csv) is the historical, uncurated input. The original published list and the phase reports remain unchanged.

All 30 exclusions were already spent. The index now contains **22,057** outputs, with **1,102,852.49 BTC at issuance**, **22 spent** and **22,035 with no spend found**. The two recorded snapshots still show **1,101,752.49 BTC** unspent. No new spend scan was performed.

Reproduce the curation manifest and this directory's exclusion CSV from a full clone:

```sh
git show d87d1e348084f6c3c08c4ef5d5414c984a3762a1:docs/data.json |
  python scripts/curate_public_index.py
```

The website reads that pinned snapshot and applies the manifest before enabling search or exports. It fails closed if the number of exclusions, record count, spend count or BTC totals do not reconcile.
