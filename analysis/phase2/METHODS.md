# Phase 2 methods and operations

**SUPERSEDED:** The user replaced this API collection plan with BigQuery during
the run. Both background collectors were stopped and their heartbeat disabled.
Do not resume this collector. Current results and methods are in
[`../phase2_bigquery/REPORT.md`](../phase2_bigquery/REPORT.md).

## Status and scope

The full collection was launched September 27, 2026 after all four amount controls passed. `REPORT.md` and `summary.json` are dated snapshots, not a claim of completion unless coverage explicitly says so. All chain requests use [mempool.space](https://mempool.space/docs/api/rest), with [blockstream.info](https://github.com/Blockstream/esplora/blob/master/API.md) only after primary failures. No third chain-data provider is used.

The pinned input is `analysis/provenance/lopp_patoshi_heights.txt`, SHA-256 `33a74d805c95c368636c4a7334e3cff80d8624fd4b0182bde84eca9e4749465f`. The original CSV remains unchanged. The list is an attribution hypothesis; verifying its keys does not validate that hypothesis.

## Collection, cache and resumption

```text
python scripts/phase2_collect.py --mode controls
python scripts/phase2_collect.py --mode full --rate 3 --workers 4
python scripts/phase2_analyze.py --permutations 1999
python -m unittest discover -s tests -p test_phase2.py -v
```

The collector is standard-library Python; the offline analyzer additionally uses NumPy. On this machine the working interpreter is `C:\Users\lucas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

- An OS-held lock prevents concurrent collectors. A crash releases the lock automatically. `analysis/phase2/job.json` records the background PID; `progress.json` is updated after each batch of 32 tasks. `collector.log` and `collector-error.log` hold stdout/stderr.
- The launch uses PowerShell `Start-Process -WindowStyle Hidden`, with explicit repository working directory and stdout/stderr redirection. A computer shutdown stops it; restart with the identical `full` command. Resume reuses successful responses and normalized results.
- `cache/chain.sqlite3` stores every response body compressed with zlib, height, endpoint, provider, attempt, HTTP status, response headers, UTC observation time, SHA-256 and transport error. SQLite WAL with full synchronous commits preserves each completed response before proceeding. A crash between HTTP receipt and commit can require that in-flight request again; already committed successes are never fetched again.
- A global request-start limiter caps the entire four-worker process at three requests/second, including retries. Batches are scheduling units; only headers have a server bulk endpoint (`/blocks/{height}`, ten per response). Transport/HTTP failures get at most three attempts per provider, with exponential retry waits. HTTP 429 additionally pauses all new requests for at least 30/60/120 seconds, respecting a numeric `Retry-After` when longer. Exhausted attempts stay exhausted across resumes and are reported as unknown. Invalid HTTP-200 payloads remain cached and are surfaced as validation failures.
- A successful outspend response is a dated observation, never refreshed on resume. Thus the final spend audit covers a range of observation times, not one simultaneous UTXO snapshot.
- Raw SQLite/logs stay local and ignored. `response_manifest.csv.gz` records every response's height, endpoint, provider, attempt, observation time, status and exact decompressed-body SHA-256. The analyzer verifies all body hashes. `summary.json` fingerprints the manifest and its logical receipt stream. Copies of the cache should include WAL/SHM while a writer is active; preferably use SQLite's backup API or copy after shutdown/checkpoint. A bare live database-file checksum would be misleading and is intentionally not used.

## Order and deterministic samples

1. Heights 2817, 19863, 23079 and 28507: fetch hash, coinbase page and header batch; require exact output-0 and total coinbase amounts of 5,201,000,000; 5,014,000,000; 5,012,000,000; 5,022,000,000 satoshis. Require matching CSV keys and successful Merkle/header verification before full collection.
2. All 21,953 listed heights: `/block-height/{h}`, `/block/{hash}/txs/0`. Verify confirmed block association and coinbase status; reconstruct non-witness transaction serialization and its txid. Compare the **entire** script to `41 + CSV uncompressed public key + ac`, not an address string. Amounts are integer satoshis, compared to decimal-parsed CSV amounts.
3. All listed coinbase txids: `/tx/{txid}/outspends`, output zero. If spent, retrieve the spending transaction, reconstruct its txid, and verify its actual referenced input. Unknown and failed checks are never counted as unspent.
4. Fetch all headers at heights 0–54,619 in ten-block batches. Reconstruct each 80-byte header, double-SHA-256 it, verify the stated block hash and difficulty target, and check adjacent previous-hash links. This verifies a linked proof-of-work header sequence as supplied by the explorer, not independent full-node consensus or best-chain validation.
5. Check coinbase inclusion: when the first transaction page contains all block txids, calculate the complete Merkle root. Otherwise fetch `/tx/{txid}/merkle-proof` and require position zero and the same height/root. This cryptographically binds the reconstructed coinbase to the checked header, unlike trusting JSON labels alone.
6. Deterministic controls: 60 uniformly sampled **unlisted** heights per 1,000-height bin, clipped to 3–49,973, seed 20260927: exactly 3,000. Unlisted is not known non-Patoshi. Selection is fixed before these chain observations.
7. Boundary sample: all heights in the ten longest internal gaps; 0–2; 49,974–50,273; 54,016–54,616 (the latter brackets the later endpoint discussed in [Lopp's article](https://blog.lopp.net/was-satoshi-a-greedy-miner/)). These are scoped samples, not exhaustive coverage of the entire post-49,973 interval. Controls/boundary overlap is fetched once. All sampled coinbases get the same txid and inclusion checks.

`selection.json` commits every selected height. Base workload: approximately 82,227 requests before retries and occasional inclusion-proof/spender requests. At three requests/second the rate-limit floor is 7.61 hours; actual runtime includes server latency, backoff and local work.

## Classifier reproduction and limits

**(a)** Extract `nonce & 255` from reconstructed headers. Tabulate all 256 values by listed/control/boundary group. Reproduce [Lerner's 2013/2019 signature](https://bitslog.com/2019/04/16/the-return-of-the-deniers-and-the-revenge-of-patoshi/): inclusive LSB ranges 0–9 and 19–58. Also apply the [2020 refined bounds](https://bitslog.com/2020/08/22/the-patoshi-mining-machine/) to the byte-reversed 32-bit nonce: `[0,163840000)` union `[327680000,983040000)`. Endpoint convention is explicit. A block failing either condition is listed for review; no nonce-only test proves miner identity.

**(b)** Parse scriptSig push opcodes directly. Exactly two pushes with a second operand at most eight bytes yield a signed little-endian Script-number extraNonce **candidate**, not a universally defined protocol field. Preserve raw scripts, pushes, parse status and sequence. Unrecognized scripts remain unknown. Consecutive-listed delta tables expose increases, plateaus, decreases/reset candidates, rate per hour and cases where nonnegative extraNonce delta is smaller than block-height delta. Other miners mixed into the control sample make consecutive-control rates difficult to interpret.

**(b)** Independently implemented interpolation supplies a reproducible extraNonce consistency check. It is not presented as an exact recreation of Lerner's original hand/algorithmic tagger. Fixed split by `height % 5`: residues 0–2 are anchors, 3 calibrates, 4 evaluates. A target needs anchors on both sides, each within 200 heights, strictly bracketing timestamps, a nondecreasing anchor extraNonce and at most 48 hours between anchors. Interpolate extraNonce in timestamp; scale absolute residual by `max(4, anchor extraNonce increment)`. Threshold is the calibration group's 95th percentile. Report evaluation coverage and held-out pass rate. Combined pass requires LSB membership and extraNonce fit. Training anchors get no purported held-out score. Unsupported blocks remain unclassified. The learned threshold and source labels mean this is a consistency check; reset regions and overlapping slopes can flag genuine listed blocks. Do not describe flagged blocks as proven misclassifications.

## Temporal tests

**(a)** Preserve signed successive-listed timestamp differences, including negative differences, and tabulate gaps over 6/12/24/48/72 hours. Compare UTC hour and weekday distributions to all-block exposure in the same height span. Tabulate listed density and nonce pass count per 1,000 heights, reporting largest adjacent density changes descriptively.

**(b)** Two prespecified schedule tests: Pearson discrepancy between listed hour/weekday counts and expectations conditioned on each 1,000-height stratum's all-block timestamps and listed count. Obtain p-values with 1,999 independent within-stratum circular shifts of the full binary label sequence, preserving counts and most serial dependence; `(exceedances+1)/(1999+1)`, seed 20260927. Holm adjusts across these two tests. Circular wraparound and choice of strata are limitations; sensitivity analysis should precede a strong schedule claim. Timezones or sleep-window choices discovered after looking are exploratory, not additional prespecified tests.

**(c)** A mining-output gap need not mean the miner was offline; elapsed header time need not equal elapsed wall time. Sleep, location, intentional pauses, and Satoshi identity remain hypotheses. No automatic novelty claim follows from these analyses.

## Final review checklist

Before marking the deliverable complete, inspect all unknown/mismatch/spend rows, control coverage, inclusion counts, header-link failures, held-out classifier coverage, and boundary candidates. Explain failures and plausible ambiguity rather than forcing a label. Add concrete findings and null results to the generated concise report. Commit the final report, normalized evidence, scripts and checksummed manifest; retain raw responses locally. The hourly thread follow-up is responsible for finishing this review and commit after background collection ends.
