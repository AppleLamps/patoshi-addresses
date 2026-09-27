# Phase 2 — chain verification

**Completed September 27, 2026.** Population: the pinned 21,953-height Lopp list, unchanged. **The CSV keys are accurate in the queried data, but the premise that every listed output is unspent is false.**

Labels: **(a)** verified chain content, with secondary-source observations explicitly identified; **(b)** statistical inference and model results; **(c)** speculation. BigQuery is a secondary source. Attribution to one miner, and especially “Patoshi = Satoshi,” is not established by this audit.

## Verified facts

**(a; BigQuery comparison)** All **21,953/21,953 pubkeys match — 100%**, with **zero mismatches** and zero missing/duplicate heights. Every complete P2PK script was compared against `41 + CSV pubkey + ac`; every amount matches too. All four controls reproduce **52.01, 50.14, 50.12 and 50.22 BTC**. Total: **1,097,652.49 BTC**. [Every comparison](verification.csv), [mismatch list](pubkey_mismatches.csv), [controls](controls.json).

**(a; cryptographic checks)** Reconstructed all 27,406 queried coinbase transaction IDs, including controls/boundaries, and validated a linked sequence of **54,620 header hashes and proof-of-work values**. Four previously cached live headers agree exactly. **21,775 listed coinbases** are single-transaction blocks, so their reconstructed txids also prove inclusion directly through the header Merkle root. The remaining **178** have matching BigQuery outputs but did not receive an exhaustive independent Merkle-proof audit. This is a stated verification limit, not a hidden match failure.

**(a; live-confirmed)** **31 listed output-zero outpoints were spent, totaling 1,550 BTC.** Every hit was checked against mempool.space; each spending transaction ID was reconstructed and its actual input checked. The complete height / coinbase txid / spending txid / amount table is [confirmed_spends.csv](results/confirmed_spends.csv). The first spend is block 9’s output at spending height 170; the latest is block 34,813’s output, spent at height **498,031 on December 7, 2017**. The 31-output aggregate and last-spend month reproduce the published [Bitquery September 2026 audit](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth); this is **not a newly discovered movement**.

**(a; dataset-bounded)** No referencing input was found for the other **21,922 outputs**, totaling **1,096,102.49 BTC**. [All 21,953 spend statuses](spend_status_all.csv). This means no spend in the queried input index, not a live unspent check of those 21,922 outputs. Blocks, inputs and transactions all reach **height 968,902**, whose timestamp is **2026-09-27 23:24:41 UTC**. Queries ran during 23:29–23:37 UTC; these are separate query snapshots, not a single atomic dataset snapshot. [Watermarks](results/watermarks.csv).

## Classifier and boundary findings

**(a)** All **21,953 listed blocks** satisfy the broad nonce-LSB ranges **0–9 or 19–58**. So do **602/3,000 unlisted controls** (20.07%). Nonce membership alone cannot assign miner identity. These reproduce the signature described by [Lerner](https://bitslog.com/2019/04/16/the-return-of-the-deniers-and-the-revenge-of-patoshi/).

**(a)** Exactly one listed block, **37,808**, fails the [tighter 2020 inner-nonce bounds](https://bitslog.com/2020/08/22/the-patoshi-mining-machine/). Its nonce is **137,413,946**; byte reversal gives **986,001,416**, above the **983,040,000** upper bound. Its nonce, coinbase and spend were live-confirmed. **(b)** This is a concrete attribution-review candidate under that particular rule, not proof of misclassification. Novelty is unestablished.

**(b)** An independently implemented extraNonce interpolation check, calibrated on a separate partition, accepts **4,075/4,290 evaluable held-out listed blocks (94.99%)**, versus **13/2,735 evaluable unlisted controls (0.48%)**. ExtraNonce parsing succeeds for every listed block. Across consecutive listed blocks there are **286 decreases/reset candidates** and **1,495 nonnegative increments smaller than the height increment**. These support a distinctive counter pattern without identifying its owner. [Increment evidence](extra_nonce_increments.csv).

**(b)** Every listed block receives nonce checks; extraNonce scoring covers **21,497**, leaving **456 unsupported** near resets, time-order problems or distant anchors. The review file contains **1,005 flags**: 1,004 interpolation outliers plus the tighter-nonce exception. Because the threshold intentionally excludes roughly 5% of calibration cases, these are **not 1,005 demonstrated misclassifications**. Anchor scores use leave-one-out interpolation; only the separate held-out partition supplies the quoted fit. [All scores](classifier_blocks.csv), [flags](classifier_flags.csv). This reproduces signatures and evaluates consistency; it does **not** recreate Lerner’s original undocumented labeling decisions.

**(b)** Among 2,583 boundary/gap samples, **530** pass the broad nonce rule; **10/158** with supported interpolation pass both checks: **49,829; 49,845; 49,870; 49,875; 49,878; 49,880; 49,905; 49,918; 49,919; 49,933**. Their chain fields were live-confirmed. They are possible omissions requiring better slope attribution. Beyond the endpoint, 62/300 blocks at 49,974–50,273 and 150/601 near 54,316 pass the nonce rule, but the anchored extraNonce model cannot attribute those distant blocks. [Candidates](boundary_and_control_candidates.csv).

## Temporal findings and null results

**(a)** The longest consecutive-listed timestamp gap is **862,029 seconds (9.977 days)**, from block **21,308 to 21,467**, August 14–24, 2009; both endpoints were live-confirmed. There are **14 gaps over 24 hours**, including **five over 48 hours**. No negative successive-listed timestamp deltas occur. The largest adjacent 1,000-height density change is a **21.8 percentage-point decline at height 24,000**. These describe the selected block list, not directly observed miner uptime. [Gaps](temporal_gaps.csv), [windows](temporal_height_windows.csv).

**(b)** No significant UTC hour-of-day or weekday pattern was detected: circular-shift permutation p-values **0.519** and **0.639**, respectively; both Holm-adjusted p-values are **1.0**. Tests condition on all-block timestamp exposure and preserve local label clustering within 1,000-height strata. A null result does not prove constant activity. [Distributions](temporal_distributions.csv).

## Open questions

**(b)** An independent slope-tracking classifier, validated against withheld positive and negative examples, is needed to adjudicate the review flags and candidate omissions. Merkle proofs for the remaining 178 multi-transaction blocks would complete that additional cryptographic inclusion check. Current live outpoint checks would extend the unspent conclusion beyond the BigQuery watermark.

**(c)** Sleep cycles, location, deliberate pauses, and Satoshi identity remain hypotheses. Header timestamps and list gaps alone cannot establish them. No scientifically new miner behavior is claimed here.

[Methods, SQL, caching and limitations](METHODS.md) · [Machine-readable summary](summary.json) · [Checksummed manifest](manifest.json).
