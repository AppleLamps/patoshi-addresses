# Phase 9 preregistration: does Patoshi's nonce encode the time since the parent block?

Written 2026-09-28 15:47 UTC, **before** any nonce-versus-timing statistic was computed. The only data examined up to this point are the counts of multi-transaction blocks per tier, used to judge gap 2's power. The SHA-256 of this file is recorded in `results/run_log.txt` when the analysis script first runs. Any later change to it is listed at the end under "Amendments".

## 1. What is already known (compact ledger)

| Source (date) | What it establishes |
|---|---|
| [Lerner, "The Patoshi Mining Machine"](https://bitslog.com/2020/08/22/the-patoshi-mining-machine/) (2020-08-22) | Reversed-nonce subrange bounds at multiples of 163,840,000. Five subranges. Re-mining of the first 13.2k Patoshi blocks shows the real solution is the *highest* nonce in its subrange 94 to 97% of the time, which he reads as inner-negative (decrementing) scanning, five subranges in parallel, and nTime updated about once a minute. Non-Patoshi nonce histograms decay exponentially because stock miners reset the nonce per block. Patoshi's histogram does not decay. His words: "It seems that Patoshi was not resetting the nonce on new blocks… I couldn't find evidence of this property." **Open.** |
| [Lerner, "Re-mining Patoshi Blocks for Dummies"](https://bitslog.com/2020/09/03/re-mining-patoshi-blocks-for-dummies/) (2020-09-03) | Restates five parallel sequential scanners (five threads). |
| [Lerner, "A New Mystery in Patoshi Timestamps"](https://bitslog.com/2020/06/22/a-new-mystery-in-patoshi-timestamps/) (2020-06-22) | Patoshi-to-Patoshi timestamp gaps start at about 312 s. There are two hypotheses: the miner slept, or it pushed the next timestamp forward. His comment of 2020-08-27 says the five threads may "synchronize to sleep after the first block has been created". Patoshi-after-other deltas "look quite normal". **Mechanism open.** |
| [Lopp, "Was Satoshi a Greedy Miner?"](https://blog.lopp.net/was-satoshi-a-greedy-miner/) (2022-09-16) | Argues "the machine slept", from the timestamps of the following non-Patoshi child blocks. States that Patoshi's ExtraNonce is free-running and that, unlike the stock client, it does not seem to increment on external blocks. Hashrate about 4.35 MH/s, maximum about 6 MH/s. |
| [Óskarsdóttir et al., PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0258001) (2021-09-30) | Frequency anomalies in nonce hex digits (the "extended Patoshi" first-nibble anomaly). No timing link. |
| Original client source, [0.1.0](sources/bitcoin-0.1.0_main.cpp) and [v0.3.0](sources/bitcoin-v0.3.0_main.cpp) | `nNonce = 1` at every template build. The template is rebuilt when `pindexPrev != pindexBest` (checked every 0x40000 hashes in 0.1.0), on nonce wrap, or on new transactions after 60 s. |
| This repository, Phases 1 to 8 | Membership, false positives, omissions, dead-time rule holding for listed pairs, nonce-band and nonce-shape habits, counter tracks. Nonce *value* against *timing* is never joined. |

## 2. Three gaps that survive the review

1. **The nonce clock (joins nonce structure, inter-block timestamps and co-spend ownership).** In the stock client, the nonce counts hashes since the last new tip, so a block found *t* seconds after its parent must have a nonce of at most about hashrate × *t*. If Patoshi's scanners also restarted on a new tip, its within-subrange scan progress should be small when the parent is recent. If they did not restart, which is Lerner's open alternative, progress should not depend on the gap. This also gives a route to the dead-time mechanism (sleep then restart, against immediate restart with a shifted timestamp) and a nonce-based estimate of per-scanner hashrate.
2. **Block-assembly fingerprint.** The stock client orders transactions by passes over `std::map<uint256, CTransaction>`, that is, by txid. Is the order inside Patoshi's multi-transaction blocks the same? Only 22 listed and 20 added blocks have two or more non-coinbase transactions. It needs per-block transaction lists (a small paid query or an API) and is verifiable against the committed Merkle roots.
3. **Self-inclusion.** Were the documented Satoshi payments (LINKS.md) confirmed in Patoshi blocks more often than Patoshi's hashrate share at the time? This joins the counterparty documents with block attribution. There are about 10 to 20 transactions, so power is low.

**Ranking.** Gap 1 ranks first on every criterion:

- It answers a question two prior authors left open.
- It uses only committed headers, offline and at no cost.
- Its evidence (nonce position against the parent's timestamp) is not used by any existing classifier. The band uses only the nonce's low byte as a set, and nonce position within a subrange is never used.
- It has a built-in positive control: ordinary miners running the stock client must show the effect.

Gap 2 is second (moderate importance, small n, needs new data). Gap 3 is third (very small n).

## 3. Primary hypothesis, null, population, controls

**Data.** `analysis/phase2_bigquery/results/headers.csv` (54,621 headers, hashes and proof of work validated in Phase 2) and the tiers in `analysis/phase8/revised_list.csv`. No new chain data.

**Definitions.**

- *N* is the header nonce as an unsigned 32-bit integer. *R* = bswap32(*N*), Lerner's "inner" nonce, whose top byte is *N*'s low byte.
- *P* = 163,840,000. The Patoshi subranges of *R* are [0, P), [2P, 3P), [3P, 4P), [4P, 5P) and [5P, 6P). A block with *R* outside them is excluded from the Patoshi tests and counted.
- Scan progress under inner-negative scanning, the **primary** direction taken from Lerner's re-mining result: *u*_IN = (hi − 1 − *R*) / P, where [lo, hi) is the block's subrange. The inner-positive alternative is *u*_IP = (*R* − lo) / P.
- Stock scan progress: *u*_S = (*N* − 1) / 2³².
- Δt = timestamp(h) − timestamp(h − 1), in seconds.

**Groups.**

- *C_P* (Patoshi child, non-Patoshi parent): tier(h) = `listed_uncontradicted` and tier(h − 1) ∈ {`other_miner`, `no_patoshi_evidence`}.
- *C_S* (positive control, ordinary child, non-Patoshi parent): tier(h) = `other_miner`, an ownership label from co-spent siblings that is independent of the block's own nonce, and tier(h − 1) ∈ {`other_miner`, `no_patoshi_evidence`}.
- Short gap: 0 ≤ Δt ≤ 60 s. Long gap: 600 ≤ Δt ≤ 3,600 s.

**H_reset (primary).** Patoshi restarted each subrange scan from its start when a new external block arrived. It predicts *u*_IN is stochastically smaller in the short-gap group than in the long-gap group of *C_P*.

**H0 (null, Lerner's alternative).** The scan continued across new tips, so *u*_IN is independent of Δt.

**Tests.**

- **T0, positive control:** one-sided Mann-Whitney on *u*_S, short < long, in *C_S*. The design counts as informative only if p < 10⁻⁶. Otherwise the timestamps are too noisy for a nonce clock and T1 is not interpreted.
- **T1, primary:** one-sided Mann-Whitney on *u*_IN, short < long, in *C_P*. It is run with *u*_IP as a second direction, with Holm correction over the two at family α = 0.01.

**Criteria.**

- **Success (reset supported):** T0 passes; T1 on *u*_IN has a Holm-adjusted p < 0.01, and the short-gap median of *u*_IN is below the long-gap median.
- **Failure (reset not supported):** T0 passes but T1 gives p ≥ 0.05 in both directions. In that case the result is reported as evidence for Lerner's "not resetting" alternative, with a power statement: the smallest reset fraction detectable at 80% power, from a mixture simulation.
- **Inconclusive:** p between 0.01 and 0.05.
- **Wrong-direction outcome:** if only *u*_IP is significant, that is reported as contradicting Lerner's inner-negative inference and treated as a new finding requiring replication, not as success.

## 4. Secondary analyses (declared now, interpreted only if T1 succeeds)

- **S1, per-scanner hashrate.** Fit *u*_IN ~ Uniform(0, min(1, (Δt + δ)/T)) by maximum likelihood on *C_P* with 0 ≤ Δt ≤ 600. T is the subrange exhaustion time; δ absorbs parent-clock skew and latency. The implied scanner rate is P/T. The implied number of parallel scanners is n = H·T/P, with Patoshi's hashrate H from its block rate in the same eras (difficulty-1 era only, heights < 32,256). Lerner's model predicts n ≈ 5. A stock-miner analogue is reported for *C_S*.
- **S2, dead-time mechanism.** In Patoshi-after-Patoshi pairs (both listed, h ≥ 5,000, excluding 1,400 to 1,916), compare *u*_IN for Δt ∈ [312, 372] s against Δt ≥ 900 s (one-sided Mann-Whitney). Sleep-then-restart predicts smaller *u*_IN just after the floor. Immediate restart with a pushed timestamp predicts no difference. This is only informative if S1 gives T well above 60 s.
- **S3, classifier check.** For short-gap blocks in other tiers (the 12 `listed_contradicted`, `added_robust`, `added_probable`, and the tail after 49,973), report whether *u*_IN or *u*_S is small, as an independent check on the tiers. Descriptive; n will be small.

## 5. Stress tests (declared)

- Era splits: h < 18,000, 18,000 ≤ h ≤ 32,255, and h ≥ 32,256.
- Double helix (1,400 to 1,916) excluded.
- Parent restricted to co-spend `other_miner` only.
- Short-gap threshold at 30 s and at 120 s.
- A permutation null (Δt shuffled within era) for T1.
- The 12 contradicted blocks are never in *C_P*; a variant that adds them is reported.
- Holm correction across all secondary p-values.

## Amendments

### A1, written 2026-09-28 after the primary result and before any of the analyses below were computed

**Primary outcome.**

- T0 passed: stock *u*_S median 0.0022 (short, n = 1,661) against 0.0737 (long, n = 5,354), z = −61.
- T1 met the preregistered **failure** criterion: *u*_IN median 0.463 (n = 424) against 0.483 (n = 3,943), one-sided p = 0.096; *u*_IP p = 0.90.
- S1 and S2 as written depended on T1 succeeding, so they are not run in their original form.

The following were declared before looking.

**A1.1, power.** For the failure branch (as §3 requires), simulate a reset in a fraction *f* of *C_P* blocks: *u* ~ Uniform(0, min(1, max(Δt + δ, 1)/T)), with δ ~ Normal(0, σ) and σ ∈ {0, 30, 60} s. Use T ∈ {30, 60, 120, 188, 300} s. Report the smallest *f* detected by T1 at 80% power, from 400 simulations per cell.

**A1.2, continuation test (new primary for the amendment).**

- **H_cont:** Patoshi's scanners neither restarted on new tips nor after its own blocks. Positions advanced in lockstep at a common rate and wrapped at the subrange end.
- **Prediction:** for consecutive `listed_uncontradicted` blocks a → b, the phase advance du = (*u*_IN(b) − *u*_IN(a)) mod 1 equals τ/T (mod 1) plus noise, where τ = t_b − t_a.
- **H0:** du is independent of τ.
- **Pairs:** consecutive listed blocks with 0 < τ ≤ 3,600 s and extraNonce(b) ≥ extraNonce(a), so no counter restart between them. extraNonce comes from Phase 3's `coinbase_encoding.csv`.
- **Statistic:** max over a grid of T from 20 to 2,000 s (step 0.5 s) of the Rayleigh resultant *R*(T) = |mean exp(2πi(du − τ/T))|.
- **Null:** 999 permutations of du among pairs within 5,000-height eras.
- **Direction variant:** the same statistic on *u*_IP, reported as a direction check. Holm over the two.
- **Success:** permutation p < 0.001 in at least one direction. The report then states the best T per era, the direction, and whether the phase offset suggests a fixed pause.
- **Failure:** p ≥ 0.05 in both directions. The report then says that neither a reset on new tips nor lockstep continuation fits, and that positions look independently drawn per block.

**A1.3, same-subrange variant.** A1.2 restricted to pairs whose two blocks lie in the same subrange. This tests continuation without assuming lockstep across scanners. Holm over A1.2 and A1.3.

**A1.4, cross-validation (only if A1.2 succeeds).** Compare the phase-derived T with:

- the extraNonce increment rate between the same pairs, extraNonce(b) − extraNonce(a) over τ;
- Patoshi's block-rate hashrate H at difficulty 1, via n = H·T/P parallel scanners.

Lerner's model predicts n ≈ 5.

### A2, written 2026-09-28 while A1.2 was running, before any per-tier statistic below was computed

**Observation motivating A2 (from T0; descriptive only).** Stock-client blocks have *u*_S tightly bounded by their parent gap. The upper byte of *N*, which *u*_S depends on, is independent of the low byte that the nonce band uses. That makes the stock nonce clock a per-block signature independent of every existing classifier (band, nonce shape, counter tracks, dormancy, co-spending, dead time).

**Question.** Do blocks in each Phase 8 tier have nonces too large for their parent gap to come from a stock client? Stock blocks must look stock; listed Patoshi blocks and the added tiers should not.

**Reference.** Stock blocks are tier `other_miner`, split at random (seed 20260928) into a reference half and a test half.

**Statistic.** For block h with gap Δt:

- π(h) is the fraction of reference blocks with u_S ≥ u_S(h), among those in the same height era (0 to 24,999; 25,000 to 49,973; 49,974 to 54,619) and the same Δt bin (edges 0, 30, 60, 120, 300, 600, 1,200, 3,600, ∞ s; Δt < 0 excluded).
- A block is "clock-inconsistent" if π(h) < 0.05.

**Estimate.** For each group, the non-stock fraction g solves observed_rate = 0.05 + g·(q̄ − 0.05). Here q̄ is the group-average probability that a Uniform(0, 1) *u* would be clock-inconsistent in the block's own era and bin, i.e. 1 minus the reference 95th percentile of *u*_S. Wilson intervals on the rate are carried through, with g clamped to [0, 1] and unclamped values kept.

**Groups.**

- `other_miner` test half (negative control; expected g ≈ 0).
- `listed_uncontradicted` (positive control; expected g ≈ 1).
- `listed_contradicted` (12).
- `added_robust` in span and after 49,973.
- `added_probable` in span and after 49,973.
- `added_possible`.
- `unresolved`.
- `no_patoshi_evidence`.

**Criteria.** The check is valid only if the negative control's g interval contains 0 and the positive control's lower bound exceeds 0.8. Given validity:

- **Tail confirmed independently:** the `added_robust` after-49,973 lower bound exceeds 0.5.
- **Contradicted blocks confirmed as stock:** the 12 have a g interval containing 0, reported with their individual π values, since n is small.

Holm correction is not applied to these descriptive group estimates. They are intervals, not tests.

### A3, written 2026-09-28 after A2's group results and before any per-block update was computed

A2 was valid. The `unresolved` tier gave g = 0.104 (0.084 to 0.127), roughly 130 non-stock blocks the earlier phases could not name. A3 turns the clock into per-block evidence.

**Likelihood ratio.** For each scored block (Δt ≥ 0, in a reference cell):

- LR = q_cell / 0.05 if π < 0.05;
- LR = (1 − q_cell) / 0.95 otherwise.

Here q_cell is the probability that a uniform nonce is clock-inconsistent in that cell. A Patoshi nonce is uniform on [0, 2³²), because its high byte is the inner nonce's low byte.

**Update.** Updated odds = Phase 6 posterior odds × LR, with the Phase 6 posterior clipped to [10⁻⁶, 1 − 10⁻⁶]. This applies to the unlisted tiers `added_robust`, `added_probable`, `added_possible`, `unresolved` and `no_patoshi_evidence`. Listed and `other_miner` tiers are unchanged. The update assumes clock evidence is independent of Phase 6's band, dormancy and track evidence given the class.

**Independence checks, declared.**

- (i) In the `other_miner` test half, the clock-inconsistent rate for band-passing and band-failing blocks, which should be equal at about 5% (Fisher two-sided).
- (ii) In listed blocks, the clock-inconsistent rate with and without a Phase 6 track fit, which should be equal at about 89%.

**Outputs.**

- Per tier: blocks at updated P ≥ 0.9, and the expected Patoshi count (sum of updated P), before and after.
- `named_by_clock.csv`, listing unlisted blocks whose updated P ≥ 0.9 while Phase 6 P < 0.9.
- A leave-one-era-out check: the clock reference is rebuilt excluding the scored block's own era, for the tail only, to show it is not self-calibrated.

**Criterion for reporting "named omissions".** Both independence checks must give p > 0.01. Otherwise the per-block update is reported only as a ranking, not as probabilities.

### A4, gap 2: block-assembly order, written 2026-09-28 before any transaction list was fetched

**Mechanism.** Both stock clients (0.1.0 lines 2235 to 2262 and v0.3.0 lines 2597 to 2622 of the saved sources) fill a block by repeated passes over `std::map<uint256, CTransaction>`. Within a pass that means ascending txid as a 256-bit integer, which is the displayed hex compared as a string. A transaction is added in the first pass in which its in-block parents are already present.

**Prediction.** For every block with two or more non-coinbase transactions, the header Merkle root equals the root of [coinbase] + stock order. That order is simulated by passes over the included transactions sorted by displayed txid, adding each once its in-block parents are in.

**Hypotheses.**

- **H_stock_P:** Patoshi's blocks (`listed_uncontradicted`) follow stock order at the same rate as ordinary blocks.
- **Alternative:** Patoshi's assembly differs, in either direction.

**Groups.**

- Patoshi: `listed_uncontradicted`.
- Ordinary: `other_miner` plus `no_patoshi_evidence`.
- Added tiers, reported descriptively.

**Test.** Two-sided Fisher exact test on stock-order match / no match, Patoshi against ordinary.

**Criteria.**

- A Patoshi assembly fingerprint is claimed only if p < 0.01, with a Patoshi mismatch rate above the ordinary rate and at least 5 Patoshi mismatches.
- If all or nearly all blocks match in both groups, the result is a null: Patoshi's block assembly was indistinguishable from the stock client's.
- Any non-matching block is checked for one-pass sorted order (no dependency passes) and for a Merkle root computed on reversed txid bytes, to separate a simulation error from a real deviation.

**Data.** One BigQuery query for the txids and input previous-txids of all transactions in blocks with three or more transactions at heights ≤ 54,619, from the transaction count in the committed headers. Dry run first; execute only if the dry run is under 1 GB. Every returned block is verified by recomputing its Merkle root in *some* order: an unordered-set check that the txid set is complete (a set is complete if some order reproduces the root, and the stock-order test itself provides that for matches), plus the transaction count.
