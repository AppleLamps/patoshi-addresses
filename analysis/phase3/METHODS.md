# Phase 3 methods and reproduction

## Design and scope

- Population and historical balance ceiling: the Phase 2 pinned list and height **968902**. Queries were made September 28 UTC, with `block_number <= 968902`. Provider backfills remain possible; this is not a BigQuery time-travel snapshot.
- Review source documents before interpreting discoveries. Follow-up searches specifically challenge the novelty of candidate results. Full downloaded prose, datasets and failed/blocked retrievals remain local, with hashes in the manifest.
- No private key export, signing, wallet import, fund movement, or ownership inference. Small-scalar screening emits only height/class if a match exists. Published weak-wallet archives are read for address files only; files containing private keys are not inspected by the screen.
- Numbers labeled (a) are directly computed observations, with BigQuery's secondary-source status explicit. Model acceptance and hypotheses remain (b)/(c).

## Bulk queries and caching

`scripts/phase3_bigquery.py` reuses the Phase 2 authenticated REST runner. Inspected Phase 2 schemas supply actual field names. Each query has a dry run and a **3 TB per-query maximum billed-byte cap**. Query identities include exact SQL, parameters and project; successful CSVs and checksum metadata are reused, without authenticating or re-querying. Full response envelopes and SQL parameter bodies remain in `cache/` locally. Seven actual queries processed **8,307,912,306,944 bytes** in total; this is processed volume, not a statement of billed cost.

- `funded_keyhashes.sql` intersects exact `76a914{hash160}88ac` scripts with outputs, then joins all matching input references. It avoids the address field, which can synthesize a P2PKH label for a P2PK output. This is equivalent to testing these addresses against the full indexed P2PKH UTXO population; it does not download every unrelated address. Spent matches are retained to inspect revealed public keys.
- The trace starts with the **20 unique first-spending transactions** already cached and live-confirmed in Phase 2. Three iterations query all referenced outputs of the current frontier, then fetch the successor transactions using exact txids and timestamp bounds. A 5,000-transaction frontier cap is implemented; it was never reached. No change outputs or “uninteresting” branches are pruned.
- All **1,259** transaction IDs are reconstructed from serialized fields. A topological ordering, including dependencies within the same block, supplies proportional allocations. All known parent-child references are recognized, including convergence within the last generation. Source value plus output allocations and allocated fees must balance to within 0.001 satoshi of arithmetic precision. This is a check on a heuristic model, not a claim that Bitcoin tracks taint.
- All seven successor transactions on the May paths were checked live. Large and seeded random funding samples, both spent funding hits, reset examples, counter-track examples and boundary anchors were also checked. `live_confirmations.json` records successes or errors. Old Phase 2 receipts are reused without refetching; new responses use the rate-limited SQLite collector at two requests/second. Bulk API scraping remains disabled.
- The final confirmation set is **72/72 successful checks**:24 transactions,17 funding outpoints,31 block/coinbase pairs. These are targeted checks, not independent live confirmation of every census row.

## Offline screens

**Weak keys.** Sequential secp256k1 point addition checks positive scalars through 2²⁰ and their negatives; an independent `cryptography` scalar multiplication checks the final point. Further explicit scalars cover powers of two, their negatives modulo the curve order, and repeated bytes. This cannot detect arbitrary weak seeds. The Milk Sad archive is pinned by commit and SHA256. Forty-five Bitcoin address files yield 314,781 distinct strings. Four standard encodings per target point are compared; no claim covers all conceivable derivation paths or all vulnerable seeds. Debian secp256k1 screening is explicitly incomplete.

**Key order.** Leading X, Y and hash160 bytes are tested for 100-position phase variation (one combined statistic) and autocorrelation at lags 1,99,100,101 (12 tests). Independent random permutations of order, seed3301, 1,999 repetitions, empirical p=(exceedances+1)/2000; Holm correction over 13 tests. These are narrow feature screens. Public-key order does not reveal key generation order or keypool refills.

**Reset timing.** Start with every consecutive-listed extraNonce decrease. Moderate filter: previous counter >=100, destination <=100 and <=20% of previous, with five nondecreasing observations before and after. Conservative changes previous minimum to1000 and ratio to10%. Filters do not use clock-of-day outcomes. Event time is the first observed low-counter block, not a known boot time. Compare hour and weekday counts against expected counts conditioned on listed-block opportunities within 1,000-height strata. Circularly shift event labels separately in each stratum, preserving much local clustering; seed3302, 4,999 permutations. Holm correction covers all six tests. Stratum boundaries, timestamp accuracy, filtering and observation delay limit power and interpretation. No conclusion about backup purpose follows.

**Boundary fits.** Publish raw fields, nearest-listed interpolation, a broad neighborhood Theil–Sen fit, and a fit clipped at observed counter decreases. Broad fits crossing resets are retained as failure diagnostics, not used for attribution. Require at least ten clipped neighbors and time bracketing for support. Compare against the downloaded Bitquery per-block dataset, including negative results. Individual local fits are exploratory, not independent truth labels.

**Multi-track classifier.** `phase3_slopes.py`: all nonce-LSB-eligible blocks1–54619, 2,000-height windows with 1,000 stride, up to12 RANSAC lines/window; 1,000 pair proposals, slopes0.15–12 EN/height, absolute residual15, at least50 inliers, seed3307. Two inlier least-squares refinements. Exclude h%5==4 and all50 top residual flags from training. Require two fitted neighbors within200 heights to score a target. Overlapping windows can duplicate tracks; choose the smallest absolute supported residual. Original list labels are used only for evaluation. Controls are not all held out. Fixed thresholds produced low recall and were not tuned afterward. Per-block evidence is in `top50_slope_adjudication.csv`; these are model adjudications, not a claim of manual or conclusive miner classification.

**Coinbase encoding.** Parse the whole script, require exactly two direct pushes, match first number to header nBits, require minimally encoded nonnegative second number, and reconstruct the full script byte-for-byte. No unmatched data remains. This excludes literal extra messages, not steganography encoded in otherwise valid counters.

## Reproduction

Python with NumPy and `cryptography` is required. From the repository root:

```powershell
python scripts/phase3_offline.py weak_keys
python scripts/phase3_offline.py key_order
python scripts/phase3_offline.py sessions
python scripts/phase3_offline.py boundary
python scripts/phase3_offline.py archaeology
python scripts/phase3_keyhashes.py
python scripts/phase3_slopes.py
python scripts/phase3_trace_analyze.py
python scripts/phase3_manifest.py
```

The analytical modules block socket operations. `weak_keys` reuses its completed local result; remove that single result only if intentionally recomputing the scalar screen. Boundary comparison and corpus screening require the documented local raw source cache. A fresh checkout can retrieve those sources with `phase3_fetch.py`, comparing the resulting hashes with the manifest; changed upstream content must not silently be treated as the original snapshot. The snapshot price is in `quantum_exposure.json`; fetching a new price does not reproduce the original quote.

The committed BigQuery results suffice for trace reanalysis. Their largest CSV has large JSON fields, so scripts explicitly raise the CSV field-size limit. Network entry points, if intentionally needed, are:

```powershell
python scripts/phase3_fetch.py
python scripts/phase3_bigquery.py funding
python scripts/phase3_bigquery.py trace
python scripts/phase3_live.py
```

The raw REST cache, SQLite responses, source archive and Firecrawl prose remain local and are checksummed. Query CSVs, metadata, SQL, derived results and scripts are committed. Local-only caches are identified in the manifest; their absence on a fresh clone is not a failed scientific null. No claim of complete Debian coverage, ultimate tracing, or universal literature coverage is made.
