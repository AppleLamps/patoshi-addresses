# Phase 10: the nonce clock inside the per-block model

Completed 2026-09-28 UTC. Offline, from committed files. Labels: **(a)** verified observation, **(b)** statistical inference with a stated test, **(c)** speculation. The model, the validation checks and their pass rules were written down first in [PREREGISTRATION.md](PREREGISTRATION.md). Each run logs that file's hash to [run_log.txt](run_log.txt).

## Why

[Phase 9](../phase9_nonce_clock/REPORT.md) found that ordinary miners' nonces grow with the time since the parent block and Patoshi's do not. That makes the nonce a check on who mined a block, independent of the earlier evidence. Phase 9 applied it on top of Phase 6's finished probabilities. A preregistered independence check failed there, so its candidates could only be published as a ranking.

Phase 10 builds the clock into Phase 6's model as one extra piece of evidence, refits it, and validates it the way Phase 6 was validated. With the clock switched off, the code reproduces Phase 6 to within 5 × 10⁻⁶ on every block.

## Results

| # | Result | Label |
|---|---|---|
| 1 | **All three preregistered checks pass, so the new probabilities replace Phase 6's.** Hidden listed blocks are recovered better. Known ordinary blocks are wrongly named less often. The posterior matches nonce shape, a habit the model never sees, in every bin. | (b) |
| 2 | **483 unlisted blocks now reach P ≥ 0.9** (Phase 8: 418), with about 7 expected false (Phase 8: about 14). **418 are robust**, meaning P ≥ 0.9 under all five counter-track settings (Phase 8: 111): 106 inside the list's span and 312 after it. The post-49,973 robust core now runs from **50,882 to 54,316**, and 54,316 is exactly the endpoint Whale Alert published in 2020. | (b) |
| 3 | **119 blocks are newly named at P ≥ 0.9**: 57 of them were unresolved and 62 possible. **54 drop below 0.9.** All of those have stock-like nonces, and they include 27,474 to 27,476 of the five-block run Phase 4 called suggestive. | (b) |
| 4 | **The count barely moves.** Expected unlisted Patoshi blocks: 216 inside the span (Phase 6: 209) and 374 after it (Phase 6: 363). The model-based total is about **22,530**, inside Phase 8's interval (22,388 to 22,572; Phase 8's own "sum of probabilities" check gave 22,512). | (b) |
| 5 | **A count that uses no model agrees with Phase 5.** From the clock alone, unlisted blocks not owned by another miner contain 210 non-stock blocks inside the span (167 to 256) and 392 after it (352 to 434). Phase 5's nonce-band estimates were 188 (119 to 258) and 353 (310 to 396). | (b) |
| 6 | **No excess list errors among trackless listed blocks.** The clock alone sees about 43 (20 to 70) more stock-like nonces than chance among the 1,029 listed blocks without a counter-track fit. Spending contradicts the idea that they are ordinary miners' blocks: only 1 of 169 was ever spent (44,838, already doubted in Phase 4), where about 11 would be. Nonce shape leans slightly ordinary (p = 0.045) and dead time shows nothing. Under the preregistered rule, no excess false positives are claimed. | (b) |

## 1. Model

Everything in Phase 6 is kept: band, dormancy, co-spend label, counter track, and the same EM fit per window and era over unlisted blocks not owned by another miner. One factor is added:

- **A Patoshi block** is clock-inconsistent with probability q_cell. That is the chance a uniform nonce lands above the ordinary 95th percentile for that block's era and parent-gap bin. It follows from theory, not a fit.
- **An ordinary block** is clock-inconsistent at the era rate r_O, measured on Phase 6's own ordinary reference (unlisted, band-failing, not co-spent with others): 8.6%, 4.0% and 6.3% in the three eras, from 858, 2,975 and 1,255 blocks.
- **Unscored blocks** (negative gap, or a sparse cell) get no clock factor.

Using q_cell per block, instead of one Patoshi rate, is what removes most of the dependence that failed Phase 9's check.

## 2. Validation ([model_summary.json](model_summary.json))

| Check | Phase 6 | New model | Rule | Result |
|---|---|---|---|---|
| **V1** hidden listed blocks at P ≥ 0.9, before 25,000 | 0.975 | **0.983** | ≥ 0.955 | pass |
| **V1** same, 25,000 to 49,973 | 0.646 | **0.799** | ≥ 0.626 | pass |
| **V2** known ordinary blocks wrongly named at P ≥ 0.9, before 25,000 (554 blocks) | 0.54% | **0.36%** | no higher | pass |
| **V2** same, 25,000 to 49,973 (1,579) | 0.63% | **0.51%** | no higher | pass |
| **V2** same, after 49,973 (257) | 4.67% | **2.72%** | no higher | pass |
| **V3** nonce-shape calibration, late span and tail separately | | mean posterior inside the shape interval in all 7 counted bins | all bins with ≥ 30 blocks | pass |

The V3 bins, as mean posterior against the fraction inferred from nonce shape. Each range uses an ordinary reference from the same heights: amendment A1, after a review comment on the first run, which had pooled the two ranges.

| Posterior bin | Late span 25,000 to 49,973: blocks, mean posterior, shape fraction (95% CI) | Tail 49,974 to 54,619: blocks, mean posterior, shape fraction (95% CI) |
|---|---|---|
| 0 to 0.1 | 694, 0.005, (0 to 0.07) | 270, 0.014, (0 to 0.14) |
| 0.1 to 0.5 | 34, 0.26, (0 to 0.60) | 14 (too few to count), 0.34, (0 to 1) |
| 0.5 to 0.9 | 40, 0.68, (0.22 to 1) | 60, 0.82, (0.58 to 1) |
| 0.9 to 1 | 124, 0.98, (0.54 to 1) | 318, 0.99, (0.78 to 1) |

The Patoshi shape reference is listed blocks at 25,000 to 49,973 (0.477). The ordinary references are co-spent ordinary blocks at the same heights: 0.205 from 3,313 blocks in the late span and 0.169 from 544 in the tail. In Phase 7 the lowest bin of the late span still held a few percent of Patoshi blocks (0.10, CI 0.01 to 0.20); here its upper bound is 0.07.

**V2 uses only the half of the ordinary blocks that played no part in defining the clock's reference cells.**

**A bug caught before the result was used.** The first run reported the Phase 6 V2 baseline with the clock accidentally still on. The likelihood reads a global flag, and the preceding fit had left it on. That made the baseline look better than Phase 6 really was, so V2 appeared to fail. The fix sets the flag explicitly, and the corrected baseline reproduces Phase 6's own figure on the full set (6.07% in the last era). The rule and the thresholds were not changed.

## 3. What changed per block ([tier_changes.csv](tier_changes.csv), [posterior_m10.csv](posterior_m10.csv))

| From (Phase 8) | To (Phase 10) | Blocks |
|---|---|---:|
| added_probable | added_robust | 246 |
| unresolved | added_possible | 68 |
| unresolved | added_robust | 53 |
| added_possible | added_probable | 42 |
| added_probable | added_possible | 29 |
| added_possible | unresolved | 27 |
| added_possible | added_robust | 20 |
| added_probable | unresolved | 13 |
| added_robust | added_possible | 12 |
| unresolved | added_probable | 4 |
| no_patoshi_evidence | added_possible | 2 |

**New tier counts:** robust 418, probable 65, possible 116, unresolved 1,211, no Patoshi evidence 5,210. Listed, contradicted and other-miner tiers are unchanged.

Cases the earlier phases discussed:

| Block | Earlier finding | Now |
|---|---|---|
| 14,450 | Omission on two lines (Phase 4) | Stays robust (0.9999) |
| 3,358 | Scored 0.87 (Phase 6) | 0.987, probable |
| 2 | 0.98 | 0.998, probable; drops below robust under one track setting |
| 1 | 0.83 | 0.84; its nonce is stock-consistent |
| 27,474 to 27,478 | Suggestive five-block run (Phase 4) | Splits in two: 27,474 to 27,476 have stock-like nonces (clock π 0.99, 0.83, 0.20) and fall to possible; 27,477 and 27,478 are strongly non-stock and become robust |
| 54,316 | Unresolved (no track fit) | Robust (0.916) |

For the run, the most economical reading **(c)** is that an ordinary miner and Patoshi interleaved there.

## 4. The suspect listed blocks ([suspects_summary.json](suspects_summary.json), [suspects.csv](suspects.csv))

Of the 1,029 scored listed blocks without a counter-track fit, 169 have stock-consistent nonces. If all were Patoshi, 128 would be expected. That leaves about 43 (20 to 70) extra.

| Independent test | Suspects | Listed blocks with a fit | What an ordinary-miner explanation predicts | Verdict |
|---|---|---|---|---|
| (a) ever spent | **1 of 169** (44,838) | | about 10.6 | Contradicts it (p = 0.0003 for 1 or fewer) |
| (b) low-byte share, heights ≥ 25,000 | 0.366 (93 in band) | 0.474 (3,613) | about 0.2 | Slight lean, p = 0.045, below the 0.01 bar |
| (c) gap under 300 s to the previous listed block | 0 of 160 | 0 of 17,153 | some violations | No signal |

**(b)** The excess cannot be the list's usual kind of error: ordinary miners' blocks were spent 19 to 58% of the time, and these almost never were. The stock-like nonces in trackless Patoshi blocks remain unexplained. One candidate **(c)** is short periods when Patoshi ran something closer to a stock loop, for example around restarts. 44,838, the one spent suspect and a 2017 modern-wallet spend, stays the single most doubtful listed block outside the 12 contradicted ones.

## 5. Limits

- The clock enters as independent of band, dormancy and track given the class. The independence problem Phase 9 found is handled by per-cell rates; the unexplained 5% in trackless blocks (section 4) is left as residual dependence.
- After 49,973, ordinary miners were getting faster, so their clock rate rises. The model uses the band-failing reference rate for that era (6.3%). V2 checks the effect directly and the new model still does better than Phase 6.
- 111 unlisted blocks in the span and 40 after it could not be scored by the clock (negative gap or sparse cell); they keep the Phase 6 evidence only.
- The total in result 4 is a sum of probabilities. The headline estimate with a full uncertainty budget stays Phase 8's Monte Carlo, which rests on Phase 5's aggregates. Both agree.

## Reproduction

```powershell
python scripts/phase10_clock_model.py model suspects manifest   # about 1 minute
python -m unittest tests.test_phase10
```

Inputs, outputs and scripts are checksummed in [manifest.json](manifest.json). The model code is Phase 6's, imported unchanged. The clock cells are Phase 9's.
