# Post-cutoff Patoshi extension

The November 28, 2026 public update adds **273 inferred Patoshi rewards**, heights **50,882 to 54,311**. The mining evidence supports attribution; the chain proves the output and amount, not the miner's identity.

## Selection and cross-check

- Start with the **318** blocks after the original cutoff (49,973) that Phase 10 scores at 0.90 or higher.
- Require 0.90 or higher under **all five** of its tested counter-track settings, leaving **312**.
- Also require a 0.90 or higher score before the nonce clock was added, a primary counter-track fit, a passing nonce band, an evaluable nonce clock inconsistent with the stock miner, and no conflicting co-spend label. **273** remain. The other **45** are held out, not declared ordinary miners.
- Of the 273 selected blocks, **125 (45.8%)** have nonce low bytes 0 to 9, versus **92 of 544 (16.9%)** in the tail's in-band other-miner comparison set. The shape feature was not directly used in the selection. The only adjacent-height pair is 1,936 seconds apart. These are checks on the cohort, not proof for each block.
- Phase 10's minimum score across settings is at least 0.91579 for every published addition. The old list and its 30 exclusions remain unchanged. The 273 are already within the audit's estimated total, not additional to that estimate.

## Coinbase and balance checks

For each candidate I reproduced the original coinbase transaction ID, verified the output-0 script and amount and the block-header hash, and verified coinbase inclusion through the Merkle root, using the empty branch when the coinbase was the only transaction. The live block hashes at heights 50,882 and 54,311 matched the committed headers. All 273 original output-0 outpoints came back unspent from mempool.space at an observed chain tip of **977,922**. Each output held **50 BTC**, adding **13,650 BTC**. This check did not re-scan balances of the 22,057 previously included records.

The [outpoint receipts](tail_outpoint_receipts.csv) preserve the transaction bytes, block hash, Merkle branch, outspend response and check time. Independently repeat the live checks with:

```sh
python scripts/audit_tail_outpoints.py /tmp/patoshi-tail-audit
```

Rebuild the published sidecar and manifest from the committed receipts, using a full clone:

```sh
git show 6ecf2b759c1727be86c5ba7c6d2c962cbcdc4f67:docs/data.json > /tmp/patoshi-base-manifest.json
python scripts/build_tail_extension.py analysis/public_index/tail_outpoint_receipts.csv 977922 --base-manifest /tmp/patoshi-base-manifest.json
```
