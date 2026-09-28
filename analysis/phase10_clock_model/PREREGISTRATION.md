# Phase 10 preregistration: the nonce clock inside the per-block model

Written 2026-09-28 16:42 UTC, before any Phase 10 number was computed. The script logs this file's SHA-256 on every run.

## Why

Phase 9 multiplied the clock's likelihood ratio onto Phase 6's finished posteriors. Its preregistered independence check (ii) failed, so the 100 top candidates could be published only as a ranking. The failure was a raw-rate comparison: listed blocks with a track fit were 88.9% clock-inconsistent, those without 83.6%. Most of that gap is the mix of timing cells (after cell adjustment, g = 1.00 against 0.95). Phase 10 puts the clock inside the model with per-block, cell-level rates, refits it, and validates it the way Phase 6 was validated. The remaining 5% gap is treated as a separate question (section 4).

## 1. Model M10

Phase 6's model is unchanged: the same code, band, dormancy, co-spend label and track evidence, and the same EM over unlisted, not-other blocks. One factor is added.

- **Clock cell and reference.** Exactly Phase 9's A2: height era, Δt bin, and the reference half of `other_miner` blocks (seed 20260928). A block is clock-inconsistent if π < 0.05. Blocks with Δt < 0 or a reference cell under 20 blocks are unscored and get factor 1.
- **P(inconsistent | Patoshi) = q_cell(h),** the share of a uniform nonce falling above the reference's 95th percentile in h's cell. This is theory, not a fit: a Patoshi nonce is uniform on [0, 2³²).
- **P(inconsistent | ordinary) = r_O(era),** measured on Phase 6's own ordinary reference: unlisted, band-failing, not-other blocks in the era. It is not taken from the `other_miner` half that defines the cells.
- Consistent blocks use the complements.

## 2. Validation and adoption criteria (declared)

- **V1, hidden listed blocks.** Phase 6's holdout: 10% of listed blocks not co-spent with others, seed 20260928, "as_omissions" variant. **Pass** if the share reaching P ≥ 0.9 is at least Phase 6's (0.975 before 25,000; 0.646 for 25,000 to 49,973) minus 0.02 in each era.
- **V2, known ordinary blocks.** Phase 6's null check: band-passing `other_miner` blocks rescored as dormant and unclustered, but only from the **test half**, so none of them helped define a clock cell. **Pass** if the share wrongly named at P ≥ 0.9 is no higher than Phase 6's for the same blocks, in each era.
- **V3, calibration against a habit the model never sees.** Nonce shape, Phase 7's method: the in-band share of low bytes 0 to 9, with the Patoshi reference 0.477 and the ordinary reference being `other_miner` blocks at the same heights. Unlisted, not-other, band-passing blocks at heights ≥ 25,000 are binned by M10 posterior (0 to 0.1, 0.1 to 0.5, 0.5 to 0.9, 0.9 to 1). **Pass** if, in every bin with at least 30 blocks, the mean posterior lies inside the shape-based 95% interval.
- **Adoption.** M10's posteriors are reported as calibrated probabilities only if V1, V2 and V3 all pass. Otherwise they are reported as a ranking, and Phase 6 stays the reference.

## 3. Outputs

- The per-block file, with the same columns as Phase 6 plus `clock_pi`, `clock_inconsistent`, `posterior_m10` and `min_over_settings_m10`, using the same five track settings.
- Tier counts under Phase 8's rules applied to M10: robust means P ≥ 0.9 under all five settings, and so on.
- Blocks newly at P ≥ 0.9 relative to Phase 6, and blocks that drop below 0.9.
- **E1, an aggregate check that uses no model.** Among all unlisted, not-other blocks with a clock score, the non-stock fraction g (Phase 9's estimator) times the count gives the number of unlisted non-stock blocks, in span and after 49,973. It is compared with Phase 5's omission estimates, 188 (119 to 258) and 353 (310 to 396). If ordinary miners are all stock and Patoshi is always non-stock, the two should agree.

## 4. The suspect listed blocks (declared)

**Suspects.** `listed_uncontradicted` blocks with no counter-track fit under Phase 6's primary setting (track False or None) that are clock-consistent (π ≥ 0.05).

- **Clock-only estimate of the list's false positives among trackless blocks:** m = (observed consistent − Σ(1 − q_cell)) / (1 − r_O), with a Wilson interval on the observed count.

**Independent tests of whether suspects are ordinary blocks** (none uses the clock or the track):

- **(a) Spending.** Ordinary blocks were spent at 19 to 58% by era (Phase 6's reference); listed blocks almost never. Under H_FP, the expected number of spent suspects is m × the era spend rate. Report observed against expected under H_FP and under H0 (no excess, which gives listed blocks' own spend rate).
- **(b) Nonce shape, heights ≥ 25,000.** The low share among suspects against listed blocks with a track fit. Fisher two-sided.
- **(c) Dead time, heights ≥ 5,000, excluding 1,400 to 1,916.** The share of suspects whose gap to the previous *listed* block is under 300 s, against listed blocks with a fit. Under H0 both are about 0.

**Criterion.** "Excess list false positives among trackless listed blocks" is claimed only if at least two of (a), (b), (c) point the same way at p < 0.01. Otherwise the clock-only m is reported as unexplained by the independent checks.

## Amendments

None at the time of writing.
