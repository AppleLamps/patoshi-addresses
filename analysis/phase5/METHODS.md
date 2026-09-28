# Phase 5: complete co-spend census (methods, ready to run)

Status: **the query has not been run yet.** Everything below is built and tested offline against committed data. The census itself needs one BigQuery query under the project's Google Cloud credentials, which were not available in the session that prepared it. This implements item 1 of the plan in [Phase 4, section 6](../phase4/REPORT.md#6-how-to-expand-from-here-prioritised).

## What it answers

Phase 4 used the 20 first-spending transactions of listed coinbases. Those transactions were selected *because* they contain a listed block, so the list's error rate had to be estimated with a zero-truncated model (0.33%, CI 0.02% to 1.35%) and then extrapolated. The census removes that selection. It takes **every coinbase at heights 0 to 54,619**, finds every transaction that spent any of them, and groups blocks spent together. Then:

- each block that was co-spent gets an **ownership label (Patoshi-like or another miner) that does not use the list**;
- the list is scored directly against those labels: how often a block owned by another miner is listed (false positives, which give precision) and how often a Patoshi-owned block is not listed (omissions, which give recall);
- every contradiction is written out block by block, with Phase 4's counter-track test applied to each one.

## How to run it

```powershell
python scripts/phase5_bigquery.py census             # free dry run: validates the SQL, prints TB and cost
python scripts/phase5_bigquery.py census --execute   # billed query, capped at --max-tb (default 2 TB)
python scripts/phase5_offline.py census manifest     # offline analysis and checksums, under a minute
python -m unittest tests.test_phase5
```

Authentication is the same gcloud application-default login as Phase 2 (`gcloud auth application-default login`). Set `GCLOUD` to the gcloud executable if it is not at the Phase 2 Windows path, and `BQ_PROJECT` to bill a different project.

**Expected cost.** The query reads the same six columns of the `inputs` view (`transaction_hash`, `index`, `spent_transaction_hash`, `spent_output_index`, `block_number`, `block_timestamp`) as Phase 3's `trace_edges` queries. Those processed 0.576 TB each. The coinbase part is partition-pruned to 2009 to May 2010 (Phase 2's equivalent read 0.45 GB). So about **0.58 TB, roughly US$3.30 at on-demand prices or free within the monthly 1 TiB tier**. The dry run prints the actual figure before anything is billed. `--execute` refuses to run if the estimate exceeds the cap.

**If BigQuery reports exceeded resources.** The main query keeps whole transactions with one window over the full `inputs` view, so it scans once. `--semijoin` runs [the fallback](sql/cospend_census_semijoin.sql), which has identical output but re-reads the view and may bill two scans (about 1.2 TB). As in Phase 2, failed responses are cached; delete the matching file in `analysis/phase5/cache/` before retrying.

## The query

[`sql/cospend_census.sql`](sql/cospend_census.sql) returns one CSV, `results/cospend_census.csv`, with two kinds of rows:

| `row_kind` | One row per | Key columns |
|---|---|---|
| `coinbase_output` | output of every coinbase at heights 0 to 54,619 (about 54,650) | `height`, `txid`, `idx` (vout), `value_sats`, `output_type`, `address` |
| `spending_input` | input of every transaction, to the frozen watermark 968,902, that spends at least one of those outputs | `height` (spending block), `txid`, `idx` (vin), `prev_txid`, `prev_vout`, `coinbase_height` (set when that input is an early coinbase output) |

All inputs of each spending transaction are returned, including inputs that are not early coinbases, so input counts are complete. The existing Phase 2 cache machinery records the query identity, job reference, bytes processed and CSV checksum, and refuses to reuse a cached result if the SQL changes.

## The analysis

[`scripts/phase5_offline.py`](../../scripts/phase5_offline.py), offline (it installs the same socket-blocking audit hook as Phase 4).

**Clusters.** A block is the ownership unit. Blocks whose coinbase outputs are spent in the same transaction are joined (common-input ownership). Each outpoint is spent once, so strict clusters are per transaction. They are merged only where one block's several outputs went to different transactions. A second, *address-linked* clustering also joins blocks whose coinbases pay the same address (payout-key reuse). This works for unspent blocks too. It is reported alongside the strict clusters and not used for the measurement.

**Ownership label, leave-one-out.** For each block, the labeller looks only at the *other* blocks in its cluster and counts how many pass Lerner's broad nonce band (low byte 0 to 9 or 19 to 58). The log-likelihood ratio is Patoshi (pass rate 0.99) against an ordinary miner (pass rate 50/256 = 0.195): +1.62 per passing co-member and −4.39 per failing one. At a ratio of 1000:1 or more the label is `patoshi`; at 1:1000 or less it is `other`; anything in between is `undetermined`. Blocks never spent with another early coinbase are `unclustered`. Two failing co-members are enough for `other`; `patoshi` needs at least five passing co-members and no failures (or more passes to absorb a failure). The block's own nonce and its list membership never enter its label. That matters because the list was built from the nonce, so a listed block's own nonce always passes. The summary gives two worst-case error counts over all clustered blocks. One is how many would still be labelled `patoshi` if every block's co-members were ordinary miners. The other is how many would be labelled `other` if they were all Patoshi.

**Measurements, within the list's height span (3 to 49,973).**

- *False-positive rate* = listed blocks ÷ all blocks labelled `other`. Implied false-positive heights = rate ÷ (1 − rate) × 28,018 unlisted heights, and implied precision = 1 − that ÷ 21,953.
- *Omission rate* = unlisted blocks ÷ all blocks labelled `patoshi`, giving implied recall.
- Both come with Wilson intervals and a **cluster bootstrap** (4,000 resamples of whole clusters, fixed seed). Errors within one miner's sweep are not independent, so the bootstrap is the interval to quote.
- A confusion table (label × listed), and the same counts per 5,000-height era. The era table bears on the late-era undercount claim that Phase 4 section 2 could not test.

**Contradictions, block by block.**

- `census_listed_with_other_miner_co_members.csv`: every listed block labelled `other`, with Phase 4's counter-track test (does it sit between the sweeping miner's own neighbouring blocks in extraNonce *and* time?), its chance-fit calibration, and the cluster-level Poisson-binomial test.
- `census_omission_candidates.csv`: every unlisted block labelled `patoshi`, with nonce, extraNonce and whether it fits the listed Patoshi run around it.

**For comparison with Phase 4**, the summary also gives the list-majority classes, the zero-truncated MLE over census clusters, and a per-transaction check of the 20 Phase 4 first spends. Phase 4 left 13 inputs as "probably coinbases of multi-transaction blocks"; the census maps them.

## Outputs (written by `census`)

| File | Contents |
|---|---|
| `census_blocks.csv` | every height 0 to 54,619: listed, nonce pass, spent, spending transaction(s), cluster, co-member counts, leave-one-out label and ratio, address-linked cluster |
| `census_transactions.csv` | every spending transaction: height, inputs, early coinbases, listed count, cluster |
| `census_clusters.csv` | every cluster of two or more blocks: size, listed, nonce passes, label, list-majority class, heights |
| `census_listed_with_other_miner_co_members.csv` | list false-positive candidates with the track test |
| `census_omission_candidates.csv` | list omission candidates with the run test |
| `census_eras.csv` | coverage and both rates per 5,000 heights |
| `census_summary.json` | all counts, rates, intervals, tests and assumptions |

## Validation already done (without the query)

1. **Phase 4 is reproduced from census-format rows.** `python scripts/phase5_offline.py replicate` rebuilds the census input from committed Phase 2 to 4 data (only the 20 first spends) and runs the same analysis. It reproduces Phase 4 exactly: 20 of 20 transactions with equal listed counts, 12 listed blocks labelled `other`, **8 of 12 track fits (7 of 11 sweeps, p = 8.0 × 10⁻⁸; Wilson-conservative 4.5 × 10⁻⁵)**, the 0.33% zero-truncated MLE, the 21.7% nonce rate of the co-spent unlisted blocks, and block **14,450** as the single omission candidate. The leave-one-out rule labels the same 12 blocks `other` as Phase 4's list-majority rule did, without using the list. It also labels the nine listed blocks of the May 2010 500 BTC transaction `patoshi`. (On this subset the direct rate is 12/548 = 2.2%. That figure is **biased upward** because these sweeps were picked for containing a listed block, which is why Phase 4 needed the zero-truncated fit. The census has no such selection.)
2. **The SQL was executed.** The BigQuery SQL was transpiled with sqlglot and run in DuckDB on a synthetic chain whose tables mirror the `crypto_bitcoin` schema. Both variants return every output of in-range coinbases (including a second output), return all inputs of a spending transaction (including a non-coinbase input), and exclude spends after the watermark, coinbases above 54,619, transactions spending no early coinbase, and references to nonexistent outputs. Their rows feed the analysis unchanged. This checks the logic, not BigQuery-specific behaviour. The dry run checks the latter for free.
3. Unit tests cover the label weights and thresholds, the misclassification rates, the intervals, the clustering (including a coinbase whose outputs were spent separately and address-linked blocks) and the measurement arithmetic.

## Limits, stated before the result

- **Common-input ownership is a heuristic.** A buyer of private keys, a custodian or a CoinJoin would merge different owners. Sweeps of dozens of P2PK coinbases are strong evidence; two-input spends much less so. The leave-one-out rule gives small clusters no label.
- **Spent blocks may not represent unspent ones.** Patoshi blocks almost never moved, so Patoshi-labelled clusters will be few and the omission rate will be imprecise. Other miners' blocks that were never consolidated are not observed. The false-positive rate measures the list on consolidated other-miner blocks, and carrying it to all 28,018 unlisted heights is still an assumption. It is a much weaker one than Phase 4's, though, and the era table shows whether the rate is stable over height.
- The nonce label assumes ordinary miners' nonce low bytes are uniform. Phase 4 found 21.7% against 19.5% in co-spent sweeps, close to uniform. A miner with a non-uniform nonce pattern could be labelled `patoshi` by mistake, so the track test and run fit are reported beside every contradiction.
- Heights 54,620 and later are out of scope, like the Phase 2 header range. Co-spent coinbases above that height count as inputs but not as blocks.
