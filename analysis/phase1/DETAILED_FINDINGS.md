# Phase 1 — detailed evidence and methods

**The CSV contains four rewards above 50 BTC; its total is 1,097,652.49 BTC. The supplied extractor cannot reproduce the full height list. The strongest statistical finding is a scale-dependent gap pattern. No convincing key bias or intentional vanity signal was found.**

Scope: all 21,953 rows, with **zero network requests**. The original extractor was inspected as text/AST, never executed. Source snapshot: `414637ce52aa4819926bf1934b2235ed182a0280`. CSV SHA-256: `e04316e814d9dc397578dc051ac3449b1dfc68603114812de42a26e5eb6a123d`.

Claim labels: **(a)** means independently verified on-chain; **(b)** means statistical inference under a stated null; **(c)** means speculation. **“CSV only; (a) pending”** marks deterministic local measurements, which cannot honestly be called on-chain facts in this phase. Nothing here establishes that Patoshi was Satoshi, that all listed blocks share one miner, or that a result is previously unpublished.

## Verified facts

**(a): None yet.** Phase 1 has no chain data independent of the supplied CSV.

**CSV only; (a) pending:** 21,953 rows and distinct heights, sorted, spanning 3–49,973 inclusive; every output index is 0 and every script-type field says `p2pk`. All 21,953 public keys are 65-byte uncompressed `04 || X || Y` encodings with coordinates in range and satisfying `Y² = X³ + 7 (mod p)` for secp256k1. Independent cryptography/OpenSSL decoding and reserialization also passed for every key. There are no duplicate pubkeys, X coordinates, HASH160 values, or derived addresses. No malformed keys were found. The CSV does not contain the actual scriptPubKeys or transaction IDs, so the script labels and coinbase association await validation.

**CSV only; (a) pending:** 21,949 amounts equal 50.0 BTC. The exceptions are:

| Height | CSV amount (BTC) | Excess over 50 BTC |
|---:|---:|---:|
| 2,817 | 52.01 | 2.01 |
| 19,863 | 50.14 | 0.14 |
| 23,079 | 50.12 | 0.12 |
| 28,507 | 50.22 | 0.22 |
| **Total** | **1,097,652.49 across all rows** | **2.49** |

**CSV only; (a) pending:** [patoshi_p2pkh_addresses.csv](../../patoshi_p2pkh_addresses.csv) contains the complete derived list, retaining height, output index, original amount, and pubkey. Each address is Base58Check(`0x00 || RIPEMD160(SHA256(uncompressed_pubkey))`), with a four-byte double-SHA256 checksum. Every address passed decode/checksum roundtrip; a known generator-point address vector also passed. These are P2PKH encodings associated with the keys. They do not change the original P2PK locking scripts; an address balance lookup alone cannot settle the spend status of these coinbase outputs.

## New findings with evidence — novelty not yet established

**CSV only; (a) pending — reproducibility discrepancy:** the bundled extractor contains only **6,183** distinct heights, all present in the CSV. **15,770 CSV heights are absent from its input list.** Its default loop only visits that list, so the checked-in script cannot regenerate this full dataset as supplied. The complete difference is in [csv_heights_absent_from_extractor.csv](csv_heights_absent_from_extractor.csv). This establishes an internal provenance gap, not fabricated data or incorrect attribution.

**CSV only; (a) pending — complete gap map:** the inclusive interval contains 49,971 heights. **28,018 are absent**, forming **8,899 missing-height intervals**; listed heights cover 43.93%. “Missing” means absent from this attributed list, not absent from Bitcoin. Every missing height is in [missing_heights.csv](missing_heights.csv); contiguous intervals are in [gap_ranges.csv](gap_ranges.csv).

| Largest missing interval | Length in blocks |
|---|---:|
| 37,312–37,737 | 426 |
| 49,484–49,796 | 313 |
| 35,204–35,510 | 307 |
| 21,309–21,466 | 158 |
| 20,343–20,441 | 99 |

**(b) — broad clustering, local excess alternation:** encode every height as listed/unlisted and count runs of either state. There are **17,799 runs**, versus **24,618.44** expected if 21,953 listed labels were uniformly placed over the interval. However, preserving the listed count separately within each 1,000-height window gives **16,751.95** expected runs. The observed sequence therefore has substantially **more local alternation** than that model predicts. Both two-sided permutation tests give Monte Carlo `p = 0.0005` with 1,999 permutations; Holm-adjusted `p = 0.005` across the ten gap tests. Exploratory sensitivity checks at 250, 500, and 2,000 heights preserve the direction and significance. They reuse the same data and are not independent replication.

**(b) — unusually long empty intervals coexist with that alternation:** the 426-height maximum gap exceeds all 1,999 simulations under both the global and primary 1,000-window nulls (`p = 0.0005`; Holm `p = 0.005`). For the primary local null, simulated maxima averaged 74.06 heights, with a 95th percentile of 102 and a largest simulated value of 143. The 250-height sensitivity test was less extreme (`p = 0.0015`) and still significant after the same correction. The scan tests the maximum over the entire interval, accounting for selecting the longest gap. It does not account for every possible analytical choice. These results describe the supplied labels, not an independently observed mining schedule. Full statistics: [gap_tests.csv](gap_tests.csv), [results.json](results.json), [height_windows.csv](height_windows.csv).

**(c):** fees could explain the 2.49 BTC excess. Mining interruptions, other miners, classifier rules, or selection mistakes could explain the label pattern. The CSV cannot distinguish these explanations. No duration, sleep-cycle, or identity inference is justified without timestamps and the underlying nonce/extraNonce data.

## Null results

**(b) — no detected key-distribution anomaly after correction:** 765 tests cover all 84 byte positions of X, Y and HASH160, three pooled-byte distributions, 672 individual bit balances, and six height/lag-one correlations. Pearson chi-square, binomial normal approximations and large-sample Fisher-z correlation tests were used, followed by Holm correction at familywise alpha 0.05. Of 765 tests, 46 have uncorrected `p < 0.05`, but **none survives correction**. The smallest raw p-value is 0.000211 for X bit 170, becoming **0.1615** after Holm correction. This is a failure to detect the tested biases, not proof of random private keys or secure key generation. X and Y are mathematically dependent. No familywise correction assumes test independence.

| First informative byte | Chi-square (255 df) | Raw p |
|---|---:|---:|
| X[0] | 233.80 | 0.8254 |
| Y[0] | 201.71 | 0.9941 |
| HASH160[0] | 275.15 | 0.1843 |

The constant `04` encoding marker is excluded. Evidence: [randomness_tests.csv](randomness_tests.csv) and [byte_frequencies.csv](byte_frequencies.csv). The tests assess departures toward larger chi-square values; low dispersion is not a separately tested alternative.

**CSV only; (a) pending — vanity scan results:** all keys and their HASH160s were scanned for the fixed dictionaries, repeated hex digits, and ordered hexadecimal sequences recorded in `results.json`. The scan logged 354 candidates: 343 short hex-word occurrences, ten repeated-digit candidates, and the single `1CFB` address. There were no ASCII dictionary matches, no eight-digit ascending/descending sequences, and no address matches for the specified case-insensitive full words. Examples worth making inspectable, without implying intent:

| Height | Local observation |
|---:|---|
| 264 | `1CFBdvaiZgZPTZERqnezAtDQJuGHKoHSzg` — the sole `1CFB` address prefix |
| 14,830 | X begins `babe4715…` |
| 17,372 | HASH160 begins `beeffbbb…` |
| 13,720 / 32,693 | HASH160 begins `1cfb…`; neither is another `1CFB` address |
| 10,194 / 38,967 / 46,528 | Six identical hex digits internally: `eeeeee`, `888888`, `999999` |

**(b):** these are consistent with chance at this scan size. The six short dictionary prefixes across XY and HASH160 have approximately **4.02 expected hits**, versus four observed. Six identical hex digits anywhere have approximately **3.31 expected matching windows**, versus three observed. The longest shared X prefix is seven hex digits (`725794a`, heights 14,733 and 48,528); the birthday approximation gives a 59.25% probability of at least one such pair in X alone. None supports deliberate vanity.

**(b):** a correctly weighted Base58 prefix calculation gives approximately **0.284 expected `1CFB` addresses** and a **24.76% chance of at least one** in a set this size under uniform HASH160. Base58 leading characters are not uniformly distributed; `58^-3` would be the wrong model. The calculation uses a uniform HASH160-plus-checksum integer approximation, with negligible boundary error for this short prefix. Since the prefix was supplied from a known example, this is chance calibration, not a discovery p-value or evidence against every possible vanity hypothesis. Full candidate values and offsets: [vanity_candidates.csv](vanity_candidates.csv); hex offsets exclude the `04` marker and ASCII offsets count bytes.

## Open questions and what would settle them

| Status | Question | Evidence needed |
|---|---|---|
| (a) pending | Are the amounts, keys, P2PK scripts and height mappings authentic? | Fetch each actual coinbase and match output 0, full script and satoshi amount. For the four exceptions, calculate transaction fees from inputs and outputs. |
| (a) pending | Which of the 21,953 coinbase outputs have been spent? | Audit actual `(coinbase_txid, vout)` outpoints exhaustively, cache observation times and spend responses, and inspect spending transactions. Report failures as unknown. |
| (b) pending | Does the classifier independently support every label, and what was missed? | Fetch headers and coinbase scriptSigs for listed blocks, declared control samples, gap interiors and boundaries. Fit on training data, report held-out fit and ambiguous cases; do not define the fingerprint from all labels and score those same labels as validation. |
| (b) pending | Do the height gaps correspond to temporal sessions or schedules? | Header timestamps and a competing-miner baseline, with checks for timestamp noise, changing total hash rate and multiple schedule searches. |
| (c) | Why does the extractor omit 15,770 included heights? | Dataset construction history or the missing extraction input/script. |
| (c) | Are any findings absent from earlier literature? | Compare exact claims against Lerner, BitMEX and Bitquery publications. No literature was fetched in Phase 1. Under a continuing mempool-only network rule, supply those sources locally or allow a separate literature-reading step. |

Phase 2 has **not started**. No spend, nonce, extraNonce, timestamp, miner-identity or literature-novelty claim is made here.

## Reproduction and source attribution

Run from the repository root with Python and the dependencies in `requirements-analysis.txt`:

```text
python -m unittest discover -s tests -v
python scripts/phase1_offline.py --permutations 1999
```

The executed environment was Python 3.12.14 and NumPy 2.3.5. RNG seeds are `20260927 + window_width`, with width zero for the global null. Monte Carlo p-values use `(extreme + 1)/(1999 + 1)`; 0.0005 is the simulation resolution, not an assertion that the true p-value is exactly that small. All ten gap comparisons are one Holm family; the 765 key tests are another. The window-size sensitivity analysis is explicitly exploratory. Exact BTC arithmetic uses `Decimal`.

Local copies of these repository sources were used; the URLs were **not fetched**:

- [Source CSV at the analyzed commit](https://github.com/AppleLamps/patoshi-addresses/blob/414637ce52aa4819926bf1934b2235ed182a0280/patoshi_pubkeys_COMPLETE.csv).
- [Extractor at the analyzed commit](https://github.com/AppleLamps/patoshi-addresses/blob/414637ce52aa4819926bf1934b2235ed182a0280/extract_patoshi_addresses.py).
- [README claims at the analyzed commit](https://github.com/AppleLamps/patoshi-addresses/blob/414637ce52aa4819926bf1934b2235ed182a0280/README.md).

No external publication is represented as consulted. [manifest.json](manifest.json) records SHA-256 hashes of the source CSV, extractor, analysis script, derived address list and machine-readable results. The source checkout uses CRLF line endings; `results.json` also supplies LF-normalized source hashes for comparison across platforms. The LF-normalized CSV hash is `f649579e286085325a881bec1168e88bbb6f5d67e10b7ef8cb5c65e916a34a2e`. Generated artifacts use LF consistently.
