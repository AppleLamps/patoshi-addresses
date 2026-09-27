# BigQuery verification methods

## Authentication and inspected schema

Existing Google Cloud user authentication and application-default credentials were usable. The installed `bq` CLI failed with `AttributeError: module 'absl.flags' has no attribute 'FLAGS'`; the same authenticated [official BigQuery REST API](https://cloud.google.com/bigquery/docs/reference/rest/v2/jobs/query) was used instead. No credentials or tokens are written to the repository.

The actual `bigquery-public-data.crypto_bitcoin` inventory and schemas were read before SQL was written. All four named objects exist as **views**: `blocks`, `transactions`, `inputs`, `outputs`. Metadata `numRows=0` for a view does not imply empty data. Schema receipts are committed under `cache/schema_*.json`.

| Required concept | Observed field |
|---|---|
| Block height / hash | `blocks.number` / `blocks.hash` |
| Block nonce / bits | `blocks.nonce` / `blocks.bits`, hexadecimal strings |
| Timestamp / version | `blocks.timestamp` / `blocks.version` |
| Coinbase identification | `transactions.is_coinbase` |
| Output script and value | repeated `transactions.outputs`: `script_hex`, `value`, `index` |
| Coinbase input script / sequence | repeated `transactions.inputs`: `script_hex`, `sequence` |
| Spending input reference | `inputs.spent_transaction_hash`, `inputs.spent_output_index` |
| Spending transaction | `inputs.transaction_hash` |

The 10-block smoke test used heights 1, 3, 4, 264, 2817, 10000, 19863, 23079, 28507, 49973. Its 52.01 BTC control established that `value` is reported in **satoshis**, despite its SQL NUMERIC type. All four amount controls subsequently passed. Nonce/bits strings are interpreted in base 16 and checked by reconstructing block headers, preventing a silent endian or unit error.

## Queries and cache

[`scripts/phase2_bigquery.py`](../../scripts/phase2_bigquery.py) uses ADC without displaying its token. The project used for jobs is recorded in `query_jobs.json`; no new Google Cloud resources, credentials or accounts were provisioned.

```text
python scripts/phase2_bigquery.py schema
python scripts/phase2_bigquery.py smoke-dry
python scripts/phase2_bigquery.py smoke
python scripts/phase2_bigquery.py pubkeys
python scripts/phase2_bigquery.py spends-dry
python scripts/phase2_bigquery.py spends
python scripts/phase2_bigquery.py context
python scripts/phase2_bigquery.py headers
python scripts/phase2_bigquery.py snapshot
python scripts/phase2_bigquery.py watermarks
python scripts/phase2_confirm_spends.py
python scripts/phase2_bigquery_analyze.py
python scripts/phase2_confirm_candidates.py
python scripts/phase2_bigquery_analyze.py
```

The runner fingerprints the exact SQL, parameters and project. Committed result CSVs have accompanying metadata/checksums. Rerunning an identical completed query uses those local CSVs **without authentication or a new query**, including on a fresh clone. A changed query identity is rejected instead of silently replacing evidence. Full REST response envelopes, including request parameters, errors, job IDs, polls and pagination, remain in the local ignored cache and are fingerprinted in `manifest.json`. Each query page is cached. Polling an existing unfinished job is distinguished from submitting a new query.

Dry runs precede execution; early-data queries use a 100 GB maximum billed scan, and the exhaustive spend query uses a 1 TB maximum. The latter scanned **575,565,240,356 bytes**. The table-specific freshness query scanned 79,329,963,728 bytes. These are processed bytes, not a claimed bill; free allowances, pricing and actual billing belong to the Google Cloud account.

`coinbases.sql` is executed once for all pinned heights, and separately for the smoke test and distinct control/boundary sample. It returns output zero, every output needed to reconstruct the transaction, input script/sequence and block metadata. It restricts these early coinbases to 2009–2010 for partition pruning; exact height-set equality is then required, so an omitted height cannot silently pass. `spends.sql` has **no time restriction** and joins cached coinbase outpoints against the entire input view. Inputs and transactions have their own explicit watermarks; block-table freshness is not substituted for input-index freshness.

No single atomic snapshot across views/queries is asserted. Query receipt times and observed maximum block height/timestamp are retained. Results are bounded by the completeness of the secondary provider's index, not an independent proof that its historical input coverage has no holes.

## Chain-data checks and source hierarchy

All amounts use Decimal-to-integer conversion. Every listed output's full script is compared to `41 + original uncompressed pubkey + ac`; mismatches and amount discrepancies have separate files, including headers when empty. CSV rows are not silently deduplicated or dropped. Exact pinned set equality is required.

All queried coinbases are serialized from actual fields: transaction version, one coinbase input, scriptSig, sequence, all outputs and locktime. Double-SHA-256 must reproduce the claimed txid. Header reconstruction uses the previous height's hash, metadata fields and numeric nonce/bits; its hash and proof-of-work target must pass. The 54,620-header sequence is contiguous from genesis. Four original live control headers match. For 21,775 single-transaction listed blocks, txid = Merkle root directly binds the reconstructed coinbase to the header. The 178 multi-transaction listed blocks retain the explicitly reported secondary-source inclusion limitation.

After the user changed transport, the general mempool collectors were stopped and their heartbeat paused. The old scripts/cache remain as provenance and reusable serialization helpers; **do not resume them**. The BigQuery workflow uses mempool.space only to confirm specific findings: 31 spend hits and 25 classifier/candidate/time-gap checks, totaling 112 successful requests. Each spend confirmation verifies `/tx/{coinbase}/outspends`, reconstructs the reported spending transaction's ID and checks its actual referenced input. It verifies confirmation and spending height against BigQuery. All live API bodies are cached in the separate local `cache/chain.sqlite3`; `response_manifest.csv.gz` fingerprints their exact decompressed bytes.

Public technical sources: [BigQuery jobs.query](https://cloud.google.com/bigquery/docs/reference/rest/v2/jobs/query), [jobs.getQueryResults](https://cloud.google.com/bigquery/docs/reference/rest/v2/jobs/getQueryResults), [mempool API](https://mempool.space/docs/api/rest), [Esplora transaction/outspend definitions](https://github.com/Blockstream/esplora/blob/master/API.md).

## Classifier and samples

The pinned list is [Lopp's September 2022 artifact](https://github.com/jlopp/bitcoin-utils/blob/45b9eb0f0d71dc7dd66c51fd3058943c1f6df0cb/findPatoshiMiningStreaks.php), SHA-256 `33a74d805c95c368636c4a7334e3cff80d8624fd4b0182bde84eca9e4749465f`. The deterministic sample was selected before fetching its chain data: 60 unlisted heights per 1,000-height bin within 3–49,973, seed 20260927, exactly 3,000. They are unlisted controls, not known other miners.

Boundary coverage is all ten largest internal gaps, heights 0–2, 49,974–50,273 and 54,016–54,616: 2,583 heights, overlapping the controls at 130 heights. Thus context contains 5,453 distinct coinbases. Full sample membership is in [`../phase2/selection.json`](../phase2/selection.json). The later boundary window follows the later endpoint discussed in [Lopp's article](https://blog.lopp.net/was-satoshi-a-greedy-miner/). This is not an exhaustive search beyond the list's endpoint.

**(b)** The broad nonce rule is `nonce & 255 in 0..9 or 19..58`, from [Lerner 2019](https://bitslog.com/2019/04/16/the-return-of-the-deniers-and-the-revenge-of-patoshi/). Separately, [Lerner 2020](https://bitslog.com/2020/08/22/the-patoshi-mining-machine/) gives refined inner-nonce bounds; byte-reverse the nonce and test `[0,163840000)` union `[327680000,983040000)`. These are independently implemented rules, not an identification oracle.

**(b)** ScriptSig push opcodes are parsed directly. Exactly two pushes with a second operand at most eight bytes yield a signed little-endian Script-number extraNonce candidate. Other layouts remain unsupported. Preserve every raw script and sequence; protocol itself does not define a universal extraNonce field.

**(b)** Interpolation is a transparent consistency model, not the original labeler. Fixed `height % 5` split: 0–2 anchor, 3 calibrate, 4 evaluate. Targets need anchors within 200 heights on each side, nondecreasing extraNonce, strictly bracketing timestamps and at most 48 hours between anchors. Interpolate in timestamp, scale absolute residual by `max(4, anchor increment)`, and calibrate the cutoff to the 95th percentile (0.49163097080738594). Combine with the broad nonce rule. The threshold is not retuned against the held-out group. For anchor diagnostics, exclude the target itself and explicitly label scores `anchor_leave_one_out`; do not call these held-out performance. Reset regions, overlapping slopes, timestamps and arbitrary support limits can all produce flags. The 1,005 flags are not a count of proven errors; 456 listed blocks have unsupported extraNonce scores.

## Temporal inference

**(b)** Hour and weekday are UTC. Compare listed counts with expectations obtained from all-block timestamps and listed fractions in 1,000-height strata. Use a Pearson discrepancy statistic. For each of 1,999 permutations, independently circular-shift the label sequence within each stratum; preserve counts and most local serial structure. Seed 20260927, p = `(exceedances+1)/2000`, Holm across the two tests. Circular wraparound and choice of strata are limitations. Report all signed inter-listed timestamp deltas and session-gap thresholds of 6, 12, 24, 48 and 72 hours. Density changes are descriptive, not separately significant change-point discoveries.

**(c)** Neither a block gap nor a timestamp gap establishes an offline miner. Human schedules and intentional pauses need additional evidence. No timezone fitting, identity claim or novelty claim is inferred from the null schedule tests.

## Validation

```text
python -m unittest discover -s tests -p test_phase2.py -v
python -m unittest discover -s tests -p test_phase2_bigquery.py -v
```

Validation covers real fee controls, transaction/header/Merkle reconstruction on those controls, cache replay without HTTP, complete result coverage, every live-confirmed spend, and BigQuery smoke replay with authentication/network disabled. Raw-cache-dependent tests explicitly skip on a clone lacking that local evidence. Analysis itself prohibits network calls. No failed fetch or unsupported classifier case is synthesized into a success.
