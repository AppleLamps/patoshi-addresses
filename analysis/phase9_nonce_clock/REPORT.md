# Phase 9: the nonce clock

Completed 2026-09-28 UTC. The question was whether a block's nonce records how long its miner had been working since the parent block, and what that says about Patoshi. Labels: **(a)** verified chain observation, **(b)** statistical inference with a stated test, **(c)** speculation. "Patoshi = Satoshi" is not assumed.

The hypotheses, controls and pass/fail criteria were written down in [PREREGISTRATION.md](PREREGISTRATION.md) before the corresponding numbers were computed. Four dated amendments (A1 to A4) record each later step. The file's hash at each stage is in [results/run_log.txt](results/run_log.txt). Prior work is compared in [NOVELTY.md](NOVELTY.md).

## Summary

| # | Result | Label | Strength |
|---|---|---|---|
| 1 | **Ordinary miners' nonces are a clock.** Among 17,216 blocks owned by other miners (by co-spending), the nonce grows in proportion to the time since the parent: median 0.04% of the nonce space at 0 to 10 s, 0.7% at 60 to 120 s, 7.4% at 10 to 60 min (z = −61). This is what the stock client's `nNonce = 1` restart on every new best block predicts. | (a) data, (b) test | Very strong |
| 2 | **Patoshi's nonce is not.** Among 8,585 listed blocks whose parent was another miner's, the scan position inside Lerner's subranges does not depend on the gap (median 0.463 at ≤ 60 s against 0.483 at 10 to 60 min, one-sided p = 0.096; the other scan direction p = 0.90). **Preregistered verdict: Patoshi did not restart its scan from the subrange start when a new external block arrived.** Power: a reset in 10 to 20% of blocks would have been detected at 80% power if a subrange took ≥ 60 s to scan, and Patoshi's hashrate implies about 140 to 210 s. | (b) | Strong null |
| 3 | **Nor did Patoshi's scan simply continue.** Across 19,704 consecutive listed pairs, the change in scan position shows no phase coherence with elapsed time for any period from 20 to 2,000 s (permutation p = 0.52; same-subrange pairs p = 0.62). "Continuous scan plus a fixed-length pause" is ruled out. Each block's position behaves as if freshly drawn. | (b) | Strong null |
| 4 | **The clock is a new, independent test of who mined a block.** A block whose nonce is too large for its parent gap was not mined by a stock client. It uses the nonce's upper bytes and the timestamps, which no earlier classifier uses. Calibration: other miners' held-out blocks 0.2% non-stock (0 to 0.7%); listed Patoshi blocks 99.8% (99.3 to 100%). | (b) | Strong |
| 5 | **It independently confirms earlier phases.** 11 of the 12 listed blocks that co-spending says belong to other miners have stock-clock nonces (non-stock fraction 0.04, CI 0 to 0.35). The 70-block post-49,973 core is 0.99 non-stock (0.89 to 1). | (b) | Strong for the tail, moderate for the 12 |
| 6 | **It names blocks the earlier phases could not.** The 1,296 "unresolved" blocks contain about 132 non-stock blocks (107 to 162). A second habit the clock never sees, Patoshi's late nonce shape, agrees: the clock-inconsistent unresolved blocks are 0.63 Patoshi-shaped (0.37 to 0.91), the rest −0.04 (−0.13 to 0.05). The 100 top-ranked candidates are in [named_by_clock.csv](results/named_by_clock.csv). | (b) | Moderate; ranking, not calibrated probabilities |
| 7 | **Patoshi blocks outside the nonce band are rare.** Unlisted blocks that fail the band are 0.4% non-stock (0 to 1.2%; 1.3% at the strictest threshold). That caps possible out-of-band Patoshi blocks at about 60 to 90. Phase 8 had listed this as an untestable assumption. | (b) | Moderate (bound) |
| 8 | **Patoshi's blocks were assembled by stock code.** In all 321 blocks with two or more non-coinbase transactions, including all 22 Patoshi blocks, the header Merkle root matches the stock client's order: txid-sorted passes, with a child waiting for its in-block parent. The chance of all 22 Patoshi matches under random ordering is about 10⁻¹⁴·⁶. | (a) | Verified, but shared with every miner |
| 9 | **A published inference is contradicted.** [satoshi-onchain](https://github.com/satoshi-onchain/satoshi-onchain/blob/main/EXCAVATION.md) reads a 2× excess of low nonces (top nibble 0 in 11.3% of its set) as Patoshi "restarting from a low nonce each block". In the Lopp list the share is 6.45% (6.13 to 6.78%), the uniform value (6.25%). Other miners are at 72.6%, so about 7% contamination by ordinary blocks reproduces the 11.3%. | (a) | Strong |

**In one sentence:** Patoshi's software kept the stock client's block assembly but replaced the hashing loop with one whose nonce position carries no timing. Every ordinary miner of the era left a timing trace in its nonce. That difference gives a new test of who mined a block, independent of every earlier one, and it agrees with the co-spending, counter-track and nonce-shape evidence wherever they overlap.

## 1. Population, data and provenance

- **Blocks:** heights 1 to 54,619. Headers from [Phase 2](../phase2_bigquery/results/headers.csv) (54,621 rows). Phase 2 validated their hashes, links and proof of work, so every nonce and timestamp used here is bound to the block hash. **20 of 20** material headers (the 12 contradicted blocks, both ends of the tail core, 1, 2, 3,358, 14,450, 27,476 and 20,000) were re-checked live against mempool.space on 2026-09-28 ([live_header_checks.csv](results/live_header_checks.csv)).
- **Labels:** Phase 8 tiers ([revised_list.csv](../phase8/revised_list.csv)), Phase 6 posteriors, and Phase 3 extraNonce values. `other_miner` means co-spent with another miner's coins (Phase 5). It never uses the block's own nonce.
- **New chain data:** one BigQuery query ([SQL](sql/block_transactions.sql), [script](../../scripts/phase9_blocktx.py)). Job `job_82M47CgmrMjpyzl515PzJkz9biyu`, dry run 9.3 MB, 2.6 MB processed, inside the free tier. It returned the txids and input previous-txids of all 4,184 transactions in the 321 blocks with three or more transactions. For every one of the 321 blocks, the transaction count matches the header and the Merkle root was reproduced, which proves the lists complete.
- **Software sources:** Bitcoin [0.1.0](sources/bitcoin-0.1.0_main.cpp) and [v0.3.0](sources/bitcoin-v0.3.0_main.cpp) `main.cpp`, with checksums in [manifest.json](manifest.json). In both, `BitcoinMiner` sets `nNonce = 1` for every new block template and rebuilds the template when `pindexPrev != pindexBest`. Both fill blocks by passes over `std::map<uint256, CTransaction>`.
- **Watermark:** not relevant to this phase. It uses no spend status beyond the Phase 5 labels, which were read to block 968,902.

**Definitions.**

- *N* is the header nonce and *R* its byte reversal, Lerner's "inner nonce".
- Lerner's subranges of *R* are [0, P) and [2P, 6P) split into four, with P = 163,840,000.
- *u*_IN is the scan progress from the top of the block's subrange (decrementing scan). *u*_IP is progress from the bottom.
- *u*_S = (*N* − 1)/2³² is a stock miner's progress.
- Δt is the block's timestamp minus its parent's.

## 2. The ordinary miners' clock (positive control)

**(a)** Median stock progress by parent gap, other-miner blocks after non-Patoshi parents ([position_by_gap.csv](results/position_by_gap.csv)):

| Gap | Blocks | Median *u*_S | 90th percentile |
|---|---:|---:|---:|
| 0 to 10 s | 213 | 0.0004 | 0.0017 |
| 30 to 60 s | 899 | 0.0033 | 0.0054 |
| 120 to 300 s | 4,128 | 0.0152 | 0.0246 |
| 600 to 3,600 s | 5,354 | 0.0737 | 0.1493 |

The median rises roughly linearly, about 7 × 10⁻⁵ of the nonce space per second, or about 0.3 MH/s for a typical winning miner. That is in line with the unoptimized 2009 client. The preregistered test T0 gives z = −61 (short gap ≤ 60 s against 600 to 3,600 s). The unconditioned consequence, that ordinary nonces pile up at low values, was shown by Lerner in 2020. Conditioning on the parent gap is what turns it into a per-block test.

## 3. Patoshi did not restart on new blocks (preregistered primary)

**(b)** Group *C_P*: 8,585 listed, uncontradicted blocks whose parent is `other_miner` or `no_patoshi_evidence`. All lie inside Lerner's subranges.

| Test | Short gap (≤ 60 s) | Long gap (600 to 3,600 s) | One-sided p | Holm |
|---|---|---|---|---|
| *u*_IN (decrementing, primary) | median 0.463, n = 424 | median 0.483, n = 3,943 | 0.096 | 0.19 |
| *u*_IP (incrementing) | 0.537 | 0.517 | 0.90 | 0.90 |

This meets the preregistered failure criterion for H_reset.

**Power** ([power_summary.json](results/power_summary.json), 400 simulations per cell). If a fraction *f* of blocks had restarted from the subrange start, with the parent's clock off by up to σ = 60 s, T1 detects:

- f = 0.10 at 80% power for a subrange scan time T ≥ 120 s;
- f = 0.20 for T = 60 s;
- only f ≥ 0.2 to 0.75 when T = 30 s.

T is fixed by the hashrate: T = 5P/H, whatever the thread count. Patoshi's 3.9 to 6 MH/s (satoshi-onchain, Lopp) gives T ≈ 140 to 210 s. A T ≤ 30 s would need about 27 MH/s, far beyond the machine's measured rate.

**Stress tests** ([stress_primary.csv](results/stress_primary.csv)): all nine variants are null (smallest Holm-adjusted p = 0.41).

- By era: p = 0.22, 0.67, 0.05.
- Double helix excluded.
- Parents labelled by co-spending only.
- Short-gap cut at 30 s or 120 s.
- The 12 contradicted blocks added.

A permutation null (Δt shuffled within 5,000-height eras) gives p = 0.088. The stock control passes in every variant, with z from −11 to −77.

**Why timestamps do not hide a reset.** Patoshi's header times run *ahead* of the network by variable amounts (Lerner's 2019 inversion table). The data confirm this: ordinary blocks after a Patoshi parent are timestamped before it 4.8% of the time, against 1.1% after ordinary parents ([exploratory.json](results/exploratory.json)). A Patoshi clock that runs ahead can only make a short header gap *longer* than the true one, so the short-gap group is, if anything, conservative.

## 4. Nor did the scan run on continuously (amendment A1.2)

**(b)** If Patoshi's scanners had kept running through new tips and its own blocks, consecutive listed blocks a → b would show du = *u*(b) − *u*(a) ≡ τ/T (mod 1), where τ is the time between them. Over 19,704 pairs (0 < τ ≤ 1 h, no extraNonce restart), the Rayleigh resultant maximised over T from 20 to 2,000 s is 0.0165. The permutation null has median 0.0166 and 99th percentile 0.0219, so p = 0.52 ([continuation.json](results/continuation.json)). The incrementing direction gives p = 0.96, and same-subrange pairs p = 0.62.

With timestamp noise of up to about a minute, a true continuation at T ≈ 190 s would still give a resultant near 0.7, forty times the observed value.

**(c)** One model fits all of this together with Lerner's re-mining evidence of sequential scanning over nTime slots of about a minute and Lopp's faster-than-expected extraNonce growth. In it, Patoshi's miner rebuilt its header often and started each scan at an arbitrary point, so the winning position carries no memory of when the parent arrived. This cannot be tested further from headers alone.

## 5. The clock as an independent classifier (amendment A2)

**(b)** For each block, π is the share of held-out stock blocks in the same era and Δt bin whose *u*_S is at least as large. π < 0.05 marks a nonce too large for a stock client. Patoshi's nonce is uniform on [0, 2³²), because its top byte is the inner nonce's bottom byte. It is also independent of the band, which reads the *bottom* byte of *N*. A group's non-stock fraction g is estimated against the uniform expectation for each block's own cell ([clock_check_groups.csv](results/clock_check_groups.csv)).

| Group | Scored | Clock-inconsistent | Non-stock fraction g (95% CI) |
|---|---:|---:|---|
| Other miners, held-out half (negative control) | 12,428 | 5.2% | **0.002** (0 to 0.007) |
| Listed, uncontradicted (positive control) | 21,869 | 88.7% | **0.998** (0.993 to 1) |
| Listed but contradicted by co-spending (12) | 12 | 1 | **0.04** (0 to 0.35) |
| Added, robust, in span | 41 | 33 | 0.94 (0.76 to 1) |
| **Added, robust, after 49,973** | 69 | 63 | **0.99** (0.89 to 1) |
| Added, probable, in span / after | 59 / 247 | 49 / 212 | 0.95 (0.81 to 1) / 0.92 (0.87 to 0.96) |
| Added, possible | 93 | 62 | 0.72 (0.61 to 0.83) |
| **Unresolved** | 1,272 | 180 | **0.104** (0.084 to 0.127) |
| No Patoshi evidence (band fails) | 5,088 | 273 | **0.004** (0 to 0.012) |

The same conclusions hold at thresholds of 0.01 and 0.10 ([clock_sensitivity.csv](results/clock_sensitivity.csv)). For the tail, with the reference rebuilt from earlier eras only, the clock-inconsistent rate is 87% for the 316 tail additions against 8.5% for other miners in the same window.

**The 12 contradicted blocks** ([clock_check_blocks.csv](results/clock_check_blocks.csv)). Eleven have stock-consistent nonces. For example:

- 24,504: Δt 65 s, *N* = 51,583,262, π = 0.17.
- 35,573: 64 s, 22,433,818, π = 0.72.
- 39,647: 77 s, 21,266,723, π = 0.74.

A uniformly placed Patoshi nonce would be this small with probability 0.5 to 1.2%, and exactly what a stock miner produces. The exception is **48,277** (117 s, *N* = 51,349,512, π = 0.040), which sits at the edge. It is also on its sweeping miner's own counter track (Phase 4), so its attribution to another miner still stands. This is a fourth independent line on these blocks, after co-spending, counter tracks and (for 24,504) dead time.

**Independent cross-check of result 6** ([exploratory.json](results/exploratory.json)). From height 25,000, Patoshi places about 48% of in-band low bytes at 0 to 9, against about 20% for other miners (Phase 7). The clock does not see the low byte. Among unresolved blocks at heights ≥ 25,000:

- the 150 clock-inconsistent ones are 0.63 Patoshi-shaped (0.37 to 0.91);
- the 922 clock-consistent ones are −0.04 (−0.13 to 0.05).

The clock model alone predicts about 0.67 for the first group (roughly 50 of the 150 are expected stock false alarms). Two unrelated habits therefore agree block by block. In the other direction, listed blocks the clock calls stock-consistent are still 0.82 Patoshi-shaped (0.66 to 0.98), which fits the roughly 11% of true Patoshi nonces that land in the stock range by chance.

## 6. Per-block update: a ranking, not probabilities (amendment A3)

Combining the clock's likelihood ratio (about 18 for a clock-inconsistent block, 0.08 to 0.15 otherwise) with each block's Phase 6 posterior gives [updated_posterior.csv](results/updated_posterior.csv). The preregistered independence check (ii) **failed**. Listed blocks without a Phase 6 counter-track fit are clock-inconsistent at 83.6% against 88.9% with a fit (p = 5 × 10⁻⁷). After adjusting for their different Δt mix, g is 1.00 with a fit and 0.95 without.

Under the preregistered rule, the updated values are therefore reported as a **ranking**. The top 100 are in [named_by_clock.csv](results/named_by_clock.csv): 62 `added_possible` and 38 `unresolved` blocks. Expected Patoshi counts move from 97.8 to 114.1 in `unresolved` and from 6.2 to 4.6 in `no_patoshi_evidence`. Both shifts sit inside Phase 8's interval for the total (22,388 to 22,572), so the Phase 8 answer stands.

**Open lead (c).** The 5% of trackless listed blocks that look stock-like are about 30 to 50 blocks spread over heights 184 to 49,000. They could be list false positives beyond Phase 5's estimate of about 15, or Patoshi instances briefly running a stock loop. The clock's own estimate of the list's non-Patoshi share, 0.2% (0 to 0.7%), cannot separate these readings.

## 7. Block assembly (amendment A4, gap 2)

**(a)** All 321 blocks at heights ≤ 54,619 with three or more transactions reproduce their header Merkle root under the stock order ([assembly_blocks.csv](results/assembly_blocks.csv)):

- 22/22 listed Patoshi blocks;
- 253/253 ordinary blocks;
- 5/5 robust and 15/15 probable additions;
- 26/26 unresolved.

In 83 blocks, 6 of them Patoshi's, the root is reproduced only when a transaction waits a pass for its in-block parent. That is the stock client's exact logic, not just a sort. The Fisher test is p = 1, so the preregistered result is a **null for discrimination**. It is still a positive fact about Patoshi's software: its template code was the stock client's, at odds of about 10¹⁴·⁶ to 1 against random ordering. Its hashing loop was not.

## 8. Falsified along the way (exploratory, recorded)

**Switch latency.** Patoshi blocks almost never arrive in the first 10 s after an external block: density 0.18 (0.10 to 0.30) of the 10 to 60 s level, against 0.64 for stock miners (p = 1.3 × 10⁻⁷, in all three eras). A slower switch to new tips was the first reading. The reverse direction refutes the need for it. Ordinary blocks *after* Patoshi blocks show the matching excess of negative gaps (4.8% against 1.1%) and their own short-gap deficit (0.38), which is the signature of Patoshi timestamps running ahead of the network, already known from Lerner's inversions. No latency claim is made.

## 9. What would change these conclusions

- **A subrange scan time under about 30 s** would make a reset invisible to T1. It would need Patoshi to hash about five times faster than its block rate implies.
- **Another non-stock miner.** Then clock-inconsistency would mean "not stock", not "Patoshi". Among co-spent ordinary blocks, non-stock miners are at most 0.7% overall. In the tail, other miners are 8.5% clock-inconsistent, so some faster or modified software was appearing by April 2010. That is why the tail results lean on shape and counter tracks as well.
- **Timestamp errors in parent blocks.** They are measured, not assumed: the negative control's 5.2% inconsistent rate at a 5% threshold absorbs them.
- **Shared labels.** The groups come from Phase 8. Where the clock agrees with them it adds independent weight. It does not validate the co-spending heuristic itself.

## Reproduction

```powershell
python scripts/phase9_nonce_clock.py primary power amendment clock update stress clock_sensitivity assembly exploratory manifest
python scripts/phase9_nonce_clock.py live            # needs network; re-checks 20 headers against mempool.space
python scripts/phase9_blocktx.py                     # BigQuery dry run; the committed result is reused
python -m unittest tests.test_phase9
```

`power` takes about 3 minutes and `amendment` about 4. Everything else takes seconds. All steps except `live` and the BigQuery query run offline from committed files. Inputs, outputs, scripts and the preregistration are checksummed in [manifest.json](manifest.json).
