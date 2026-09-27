# Phase 1 report — CSV only

**Completed offline; zero network requests.** All 21,953 rows were examined. Novelty relative to the literature remains unassessed. Detailed methods, test results, caveats and source fingerprints are in [DETAILED_FINDINGS.md](DETAILED_FINDINGS.md).

Labels: **(a)** verified on-chain fact; **(b)** statistical inference; **(c)** speculation. Deterministic local observations are marked **“CSV only; (a) pending”** because they are not independently verified on-chain.

## Verified facts

**(a): None yet.** The CSV is the only blockchain evidence used in this phase.

**CSV only; (a) pending:** exactly 21,953 distinct heights, spanning 3–49,973. Every script-type field says `p2pk`; every output index is zero. All keys are valid uncompressed secp256k1 points, independently checked with cryptography/OpenSSL. No malformed keys or duplicate pubkeys, X coordinates, HASH160 values or derived addresses were found.

**CSV only; (a) pending:** the requested “all amounts exactly 50” check **fails**:

| Height | CSV amount, BTC |
|---:|---:|
| 2,817 | 52.01 |
| 19,863 | 50.14 |
| 23,079 | 50.12 |
| 28,507 | 50.22 |

The other 21,949 rows equal 50.0 BTC. The sum is **1,097,652.49 BTC**, exceeding the stated total by **2.49 BTC**. **(c):** transaction fees are a possible explanation requiring chain verification.

**CSV only; (a) pending:** the [complete P2PKH list](../../patoshi_p2pkh_addresses.csv) was derived from each original uncompressed key; every Base58Check roundtrip passed. These address encodings do not replace the original P2PK scripts. Spend verification must query the actual coinbase outpoints.

## New findings with evidence — novelty unconfirmed

**CSV only; (a) pending — provenance discrepancy:** the bundled extractor lists only **6,183 heights**. Another **15,770 CSV heights** are absent, so that script cannot reproduce the full dataset as supplied. [Complete difference](csv_heights_absent_from_extractor.csv).

**CSV only; (a) pending — gap map:** **28,018 heights** are unlisted, forming **8,899 intervals**. The largest are **37,312–37,737 (426 blocks)**, **49,484–49,796 (313)** and **35,204–35,510 (307)**. These are omissions from the attribution list, not missing Bitcoin blocks. [All missing heights](missing_heights.csv); [all intervals](gap_ranges.csv).

**(b) — the gap pattern changes with scale:** there are **17,799 runs** of listed/unlisted status, versus **24,618.44** expected under globally random placement: broad clustering. Preserving the listed count within each 1,000-height window instead predicts **16,751.95 runs**: the observed labels have **excess local alternation**. Both tests have permutation `p = 0.0005`, Holm-adjusted `p = 0.005`. Exploratory checks at 250, 500 and 2,000 heights retain the direction and significance.

**(b):** the longest gap is also unusual under the local null: **426 observed versus 74.06 mean simulated**, Holm-adjusted `p = 0.005`. Each test used 1,999 permutations; adjustment covers ten gap comparisons. These findings describe the supplied classifier labels. **(c):** mining behavior, classification rules or selection errors could explain them. [Statistics and null models](results.json).

## Null results

**(b):** no key-distribution anomaly survives Holm correction across **765 tests** of byte distributions, bit balances and height/lag correlations. The smallest adjusted p-value is **0.1615**. First informative byte uniformity gives raw p-values **0.8254 for X**, **0.9941 for Y**, and **0.1843 for HASH160**; the mandatory `04` marker is excluded. This does not prove secure key generation. [All tests](randomness_tests.csv).

**CSV only; (a) pending:** vanity scans found X beginning `babe…` at **14,830**, HASH160 beginning `beef…` at **17,372**, and three internal six-identical-digit strings. No specified ASCII words or eight-digit ordered hex sequences appeared. Block **264** gives `1CFBdvaiZgZPTZERqnezAtDQJuGHKoHSzg`, the only `1CFB` address. [All 354 candidates and exact scan rules](DETAILED_FINDINGS.md#null-results).

**(b):** short hex prefixes and repeated digits occur at rates compatible with chance. A Base58-aware model gives approximately **24.76% probability of at least one `1CFB` address** in this sample size. That prefix was selected from a known example, so this is chance calibration, not a discovery p-value. No convincing intentional-vanity signal was detected.

## Open questions and what would settle them

| Claim status | Open question | Required evidence |
|---|---|---|
| (a) pending | Authentic keys, amounts and spends? | Exhaustive coinbase-output matching and actual outpoint spend queries; failures remain unknown. |
| (b) pending | Correct classification and missed blocks? | Headers and coinbase scriptSigs, declared controls, independent fit evaluation, and gap/boundary samples. |
| (b) pending | Sessions or human schedules? | Timestamps, comparison miners, and controls for timestamp noise and multiple searches. |
| (c) | Why the extraction-list mismatch? | Dataset construction history or missing extraction inputs. |
| (c) | Previously unpublished findings? | Direct comparison with Lerner, BitMEX and Bitquery publications; supply them locally or permit separate literature access under the mempool-only constraint. |

**Phase 2 has not started. No spend status or miner identity is established.**

Sources used locally, URLs not fetched: [CSV](https://github.com/AppleLamps/patoshi-addresses/blob/414637ce52aa4819926bf1934b2235ed182a0280/patoshi_pubkeys_COMPLETE.csv), [extractor](https://github.com/AppleLamps/patoshi-addresses/blob/414637ce52aa4819926bf1934b2235ed182a0280/extract_patoshi_addresses.py), [original README](https://github.com/AppleLamps/patoshi-addresses/blob/414637ce52aa4819926bf1934b2235ed182a0280/README.md). [Reproduction instructions](DETAILED_FINDINGS.md#reproduction-and-source-attribution).
