# Phase 6: a Patoshi probability for every early block

Completed 2026-09-28 UTC. Offline, on committed data only: the 54,620 Phase 2 headers and the Phase 5 census. No new queries. Labels follow the earlier reports: **(a)** verified observation, **(b)** statistical or model inference with a stated test, **(c)** speculation. "Patoshi = Satoshi" is not assumed.

Phase 5 estimated omissions in aggregate: about 188 unlisted Patoshi blocks inside the list's span, and about 353 after its end at 49,973. It could not say *which* blocks. This phase scores every block from 1 to 54,619 and names the candidates, with calibrated error rates. Outputs:

- [probability per block](posterior_blocks.csv)
- [ranked unlisted candidates](posterior_candidates.csv)
- [per-window table](posterior_windows.csv)
- [summary with validations](posterior_summary.json)
- [checksums](manifest.json)

## Headline results

| # | Result | Label |
|---|---|---|
| 1 | **Named blocks after the list's end.** 318 unlisted blocks after 49,973 score P ≥ 0.9 (about 9.5 expected false). A **robust core of 70** stays at P ≥ 0.9 under every track-test setting (about 2 expected false). The core runs from **block 50,882 (2010-04-14) to 54,311 (2010-05-03)**, which puts a date on the end of Patoshi-like mining and matches the public estimates of about 54,316 to 54,458. | (b) |
| 2 | **Named omissions inside the span.** 99 unlisted blocks score P ≥ 0.9 (about 5 expected false), and a robust core of 41 survives every setting (about 2 expected false). They cluster in the list's earliest days (29, 193 to 197, 2,133 to 2,141) and at **25,000 to 27,499**, the window where Phase 5 found the excess. | (b) |
| 3 | **The totals agree with Phase 5 under every setting**, although Phase 5 used only aggregate nonce-band counts: expected Patoshi blocks 180 to 209 inside the span (Phase 5: 188, CI 119 to 258) and 357 to 363 after it (Phase 5: 353, CI 310 to 396). | (b) |
| 4 | **Validated on known blocks.** Hidden listed blocks are recovered at P ≥ 0.9 in 97% of cases before height 25,000 and 65% after (87% to 88% at P ≥ 0.5), whether or not they may anchor each other. Ordinary blocks known from co-spending, made to look dormant and band-passing, are wrongly named at P ≥ 0.9 in 0.25%, 0.57% and 6.1% of cases in the three eras. The last figure matches the model's own error estimate after the list's end. | (b) |
| 5 | **Known cases.** 14,450 scores 0.999 (min over settings 0.91). The five-block run 27,474 to 27,478 scores 0.94, and 27,476 to 27,477 stay above 0.93 under every setting. Block 1 scores 0.83 (min 0.83). Block 2 (0.98) and 3,358 (0.87) are high only when the track test may search several anchor pairs, so they are not in the robust core. | (b) |

## 1. Evidence and model

**(b)** For each block, four kinds of evidence. None of them uses the block's own list membership.

| Evidence | Patoshi rate | Ordinary rate | Source of the rates |
|---|---|---|---|
| Co-spent with another miner (Phase 5 label) | 0 | – | Such blocks are fixed at probability 0 |
| Co-spent inside a Patoshi sweep | ≥ 1000:1 for | – | Phase 5 labelling threshold (only block 14,450 among unlisted blocks) |
| Nonce low byte in the band | 0.99 | 0.1961 | Phase 5 measured background |
| Never spent | 0.9986 | 0.81, 0.71, 0.42 by era | List; ordinary from band-failing unlisted blocks not owned by another miner |
| Counter on a track | fitted by EM | 2.5%, 8.9%, 9.6% by era | Same ordinary reference blocks, same anchors |

**Track test.** Patoshi's extraNonce rises steadily with time within a session: in April 2010, 2,993 to 6,504 over 46 hours. Several machines ran at once, and counters reset on restart. A block fits if its counter lies within tolerance of the time-interpolated value between two anchors that bracket it within 6 hours and have increasing counters. The anchors are listed blocks plus unlisted dormant band-passing blocks, with the block itself left out. With no listed blocks after 49,973, the candidates have to anchor each other. The ordinary rate is measured against exactly the same anchors, so any chance fits this adds are priced in.

**Mixture.** Unlisted blocks not owned by another miner are modelled as Patoshi or ordinary. EM fits each 2,500-height window's Patoshi share and each era's Patoshi track rates. Listed blocks are not in the mixture, so the list never labels the blocks being scored. The fitted Patoshi track-fit rates are 0.93, 0.77 and 0.88 by era, against 0.025 to 0.096 for ordinary blocks.

## 2. After the list's endpoint

**(b)** The model gives 362 expected Patoshi blocks from 49,974 to 54,619 (357 to 363 across settings). With the primary setting, all 318 blocks named at P ≥ 0.9 are counter-track fits. The dormant band-passing blocks without a fit (164) all score below 0.36. The first named block is 50,762. The 70-block robust core starts at 50,882 and ends at 54,311. This fits Phase 5's per-500-height excess, which was near zero from 49,974 to 50,473.

The picture is of a miner whose blocks the list stops tracking after a series of counter resets (49,415 to 49,483, then a listing gap to 49,797). The miner keeps going, at a lower share, until early May 2010. Per 2,500 heights, the fitted Patoshi share of unlisted, not-other blocks is 0.16 (50,000 to 52,499) and 0.21 (52,500 to 54,619).

## 3. Inside the span

**(b)** Expected omissions per window are near zero in most of the span. Two places stand out:

- **0 to 2,499** (32 expected; 26 named at P ≥ 0.9). January 2009 has runs of consecutive unlisted blocks, all passing the band and never spent, whose counters form a second low-count sequence interleaved with the listed one. Around 168 to 197, the listed counters are 14, 21, 22, 31, 40 and the unlisted ones 3, 1, 2, 6, 19, 7, 18. Ten consecutive band passes would have chance probability about 10⁻⁷ for an ordinary miner. These look like a second Patoshi machine that the list's track logic did not follow. Blocks 1 and 2, whose counters lead into listed blocks 3 and 4 (Phase 4), also score high.
- **25,000 to 27,499** (87 expected; 68 named). This window is where Phase 5's excess sits, and it contains the 27,474 to 27,478 run.

Elsewhere the windows show 0 to 19 expected omissions each, mostly spread thin over dormant band-passing blocks without a track fit. That is the Phase 5 aggregate excess, now spread across blocks the model cannot tell apart.

## 4. Validation

- **Holdout (sensitivity).** A random 10% of listed blocks (2,194, not co-spent with others; seed 20260928) were made unlisted and everything was refitted, in two variants.
  - *As omissions:* hidden blocks that are dormant and band-passing may anchor each other, exactly as real omissions do in the main run. Before height 25,000, 97.5% score P ≥ 0.9 (mean 0.985). From 25,000 to 49,973, 64.6% score P ≥ 0.9 and 87.7% P ≥ 0.5 (mean 0.83).
  - *Strict:* hidden blocks are excluded from every anchor set, so each is scored only against the blocks still listed and the genuine candidates. The rates are 97.1%, 65.0% and 87.3%, nearly the same.
  
  Hidden blocks are still easier than true omissions, because their neighbours stay listed.
- **Null (false positives).** Ordinary blocks known from co-spending that pass the band were rescored as if dormant and never co-spent. That is the hardest ordinary case. Their own track-fit rates (1.9%, 8.0%, 8.3%) match the band-failing reference rates (2.5%, 8.9%, 9.6%), which supports the model's independence assumption. The share wrongly named at P ≥ 0.9 is 0.25%, 0.57% and 6.1%. After the list's end there are about 130 such look-alikes (482 dormant band-passing blocks minus about 353 Patoshi), and 6.1% of them is about 8 false names, close to the model's own 9.5.
- **Sensitivity grid.** Five settings of the track test were run: absolute tolerance 3 or 10, relative tolerance 0.10 or 0.15, and 1 or 3 anchors per side.
  - Expected totals barely move: 180 to 209 inside the span, 357 to 363 after it.
  - The number of named blocks moves a lot: 47 to 99 inside the span, 70 to 318 after it.
  - The robust core is the set that survives all five settings. Each block's minimum posterior and its count of naming settings are in the per-block file.

**Independent check.** [Phase 7](../phase7/REPORT.md) tests these results against habits this model never used (nonce shape within the band, consecutive-block dead time) and finds the named post-endpoint blocks Patoshi-like and the posterior calibrated, with one caveat: some late in-span omissions probably score below 0.1 here.

## 5. Limits

- **The settings were chosen after looking.** The first run used one anchor pair per side and an absolute tolerance of 10. The primary setting (three pairs) was chosen after that run showed the nearest anchor is often another machine's. The robust core and the grid exist because of this. Quote the core when a conservative list is needed.
- **Independence.** Band, dormancy and track evidence are multiplied as if independent given the class. The null check supports this for band vs track. Dormancy vs track is not tested.
- **Local calibration.** Ordinary track-fit rates are per era, not per block. Where counters are small (early January 2009) a fit is easier to get by chance than the era rate says. The early named blocks rest mostly on runs of band passes and dormancy, and block 2 and 3,358 drop out of the core for this reason.
- **Priors.** The per-window Patoshi share drives the posterior of blocks without a track fit. In windows where EM finds a share near zero, a lone dormant band-passing block scores low even if it is Patoshi.
- **Nothing is added to the pinned list.** These are probabilities. The per-block file carries the evidence for anyone who wants to adopt a threshold.

## Reproduction

```powershell
python scripts/phase6_posterior.py posterior manifest   # about 40 s
python -m unittest tests.test_phase6
```
