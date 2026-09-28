# Phase 7: checking Phase 6 against habits it never used, and the January 2009 "second machine"

Completed 2026-09-28 UTC. Offline, on committed data only: Phase 2 headers and the Phase 6 per-block file. Labels follow the earlier reports: **(a)** verified observation, **(b)** statistical inference with a stated test, **(c)** speculation. Outputs:

- [habit tests by group](habit_tests.csv)
- [calibration of the Phase 6 posterior](calibration_by_posterior.csv)
- [Patoshi nonce-shape history](nonce_shape_history.csv)
- [January 2009 episodes, block by block](second_sequence_blocks.csv) and their [summary](second_sequence_summary.json)
- [checksums](manifest.json)

Phase 6 scored every block using the nonce *band*, dormancy and counter tracks. A fair check has to use evidence that model never saw. Three habits qualify:

- **Nonce shape:** where inside the band (0 to 9 vs 19 to 58) the nonce low byte falls. Phase 6 used only in or out.
- **Dead time:** two consecutive Patoshi blocks are at least about 312 s apart. First reported by [Lerner (2020)](https://bitslog.com/2020/06/22/a-new-mystery-in-patoshi-timestamps/) and summarised by [Lopp (2022)](https://blog.lopp.net/was-satoshi-a-greedy-miner/).
- **Clock offset:** a block's timestamp minus the median of the six blocks either side.

## Headline results

| # | Result | Label |
|---|---|---|
| 1 | **Patoshi's nonce shape changed around block 22,500.** Up to 22,499 its in-band share at 0 to 9 is 0.17 to 0.22, like any miner. At 22,500 to 24,999 it drops to 0.04. From 25,000 on it is 0.38 to 0.52. Other miners stay at 0.16 to 0.25 throughout. This makes nonce shape an independent Patoshi signature from 25,000 on. | (a) data, (b) interpretation |
| 2 | **The post-endpoint core passes the shape test.** The 70 robust-core blocks after 49,973 imply a Patoshi fraction of **0.98** (CI 0.62 to 1.36). The chance of that shape from ordinary blocks is p = 4.6 × 10⁻⁹. The other 248 blocks named at P ≥ 0.9 give **0.89** (CI 0.70 to 1.10, p = 6 × 10⁻²⁴). | (b) |
| 3 | **Phase 6 is calibrated.** Binning post-endpoint unlisted band-passing blocks by their Phase 6 posterior, the shape-only Patoshi fraction tracks the posterior: 0.03 vs 0.00, 0.43 vs 0.31, 0.91 vs 0.97. A control of ordinary blocks that wrongly passed the Phase 6 track test shows no Patoshi shape (p = 0.21), so the track test does not select for it. | (b) |
| 4 | **The dead-time rule holds for the list, with one exception: block 24,504.** From height 5,000 on, 10,243 of 10,244 consecutive listed pairs are at least 312 s apart. Other miners' consecutive pairs fall under 300 s 43.5% of the time. The one violation, 24,504 (65 s), is the block Lopp flagged and Phase 4 found swept by another miner. Three independent lines agree on it. | (a) |
| 5 | **Named blocks respect dead time**, but the sample is small. All 5 consecutive pairs among the 318 named post-endpoint blocks (4 outside the core), and all 4 among the late in-span core, are at least 300 s apart (the chance that all would respect it if the blocks were ordinary: 0.06 for 5 pairs, 0.10 for 4). The dormant band-passing blocks Phase 6 rejected break the rule in 4 of 5 pairs. | (b) |
| 6 | **Clock offset is not a Patoshi habit.** It does not separate listed Patoshi blocks from other miners (Mann-Whitney p = 0.12), so it is reported as a null and not used. | (b) |
| 7 | **"Second machine": two different things.** 28 to 29 January 2009 (2,132 to 2,141, 2,172) is **not** a second machine: it is the start of Patoshi's main counter after a restart, which the list missed. 11 to 12 January 2009 (163 to 197) **is** two counters running at once, a short "double helix" of which the list captured one strand and parts of the other. | (b) |
| 8 | **Why the list misses blocks.** 83% of Phase 6's named in-span omissions (34 of the 41-block core, 82 of 99 named) have a counter below that of the listed block just before them, against 1.3% of listed blocks. The list systematically drops blocks just after a counter restart or on a second concurrent counter, where low counters look like an ordinary miner's. | (b) |

## 1. Nonce shape: an independent signature from block 25,000

**(a)** Share of in-band nonces with low byte 0 to 9, per 2,500 heights ([table](nonce_shape_history.csv)):

| Heights | Listed Patoshi | Other miners |
|---|---:|---:|
| 0 to 22,499 (nine windows) | 0.17 to 0.22 | 0.19 to 0.22 |
| 22,500 to 24,999 | **0.04** | 0.23 |
| 25,000 to 27,499 | 0.38 | 0.21 |
| 27,500 to 49,999 (nine windows) | **0.47 to 0.52** | 0.16 to 0.25 |

Before 22,500 the shape carries no information. From 25,000 it roughly doubles the odds per band-passing block. The switch fits a change in how Patoshi's miner split or scanned the nonce space; Lopp's multi-threading hypothesis would allow such a change. That is (c). The phenomenon was not found in the sources checked ([SOURCES.md](../phase3/SOURCES.md), and the Lerner, Lopp and Bitslog posts linked above). A thesis ([Guðmundsson, Skemman](https://skemman.is/bitstream/1946/42021/1/Blockchain%20network%20analysis%20-%20Steindor%20Gudmundsson.pdf)) discusses era-dependent nonce distributions, so novelty is not claimed.

## 2. The post-endpoint tail against independent habits

**(b)** References: Patoshi = listed blocks 25,000 to 49,973 (in-band low share 0.477, from 4,254 blocks); ordinary = other-miner blocks after 49,973 (0.169). A group's Patoshi fraction *f* solves share = *f* × 0.477 + (1 − *f*) × 0.169 ([all groups](habit_tests.csv)).

| Group (after 49,973) | Blocks | Mean Phase 6 posterior | Low share | Patoshi fraction from shape (95% CI) | p if ordinary |
|---|---:|---:|---:|---|---|
| Robust core | 70 | 0.97 | 0.471 | **0.98** (0.62 to 1.36) | 4.6 × 10⁻⁹ |
| Named at ≥ 0.9, not core | 248 | 0.97 | 0.444 | **0.89** (0.70 to 1.10) | 6 × 10⁻²⁴ |
| Dormant band-passing, rejected (< 0.5) | 164 | 0.30 | 0.299 | 0.42 (0.21 to 0.66) | 2.9 × 10⁻⁵ |
| Control: other-miner blocks with a false track fit | 203 | 0 | 0.235 | 0.22 (−0.15 to 0.75) | 0.21 |

**Calibration.** Post-endpoint unlisted band-passing blocks, not owned by another miner, binned by Phase 6 posterior ([table](calibration_by_posterior.csv)):

| Posterior bin | Blocks | Mean posterior | Shape-only Patoshi fraction (95% CI) |
|---|---:|---:|---|
| 0 to 0.1 | 181 | 0.00 | 0.03 (−0.13 to 0.23) |
| 0.1 to 0.5 | 163 | 0.31 | 0.43 (0.22 to 0.67) |
| 0.9 to 1 | 318 | 0.97 | 0.91 (0.74 to 1.09) |

In the late span (25,000 to 49,973) the same check gives 0.10 (0.01 to 0.20) for the 0 to 0.1 bin, 0.17 for 0.1 to 0.5, 0.80 for 0.5 to 0.9, and 0.79 (0.43 to 1.18) for 0.9 to 1. Phase 6 is well calibrated at the top. Its lowest bin in the late span, however, still holds a few percent of Patoshi blocks, about 50 of 666 by point estimate, so **Phase 6 probably undercounts late in-span omissions** that have no track fit.

**Dead time.** The tail has few consecutive Patoshi pairs because Patoshi's share there is small. All 5 pairs among the 318 named blocks respect the rule. The rejected dormant blocks break it in 4 of 5 pairs, which agrees with their low posterior.

**Conclusion for the tail (b).** Two habits the Phase 6 model never saw, nonce shape and dead time, both say the named post-endpoint blocks are Patoshi's and the rejected ones mostly are not. The 70-block core, 50,882 to 54,311 (14 April to 3 May 2010), is supported at about the level Phase 6 claimed.

## 3. The January 2009 sequences

**(b)** Phase 6 named runs of unlisted, band-passing, never-spent blocks on 11 to 12 January and 28 to 29 January 2009. Nonce shape cannot help this early (Patoshi and others are both near 0.2), and before height 5,000 even listed pairs break the dead-time rule 4.8% of the time. Two things remain. First, the band itself on a set fixed before looking: *every* unlisted block in each window, band-passing or not (the named sequences were selected on band and dormancy, so their own band and dormancy prove nothing). Second, how the counters fit together.

| Episode | Unlisted blocks in window | Pass the band | Expected if ordinary | p | Unspent: band-passing vs band-failing |
|---|---:|---:|---:|---|---|
| 11 to 12 Jan (150 to 210) | 24 | 20 | 4.7 | 3 × 10⁻¹¹ | 20/20 vs 4/4 (nothing in the window was spent; uninformative) |
| 28 to 29 Jan (2,120 to 2,180) | 23 | 12 | 4.5 | 5 × 10⁻⁴ | 10/12 vs 1/11 (Fisher p = 5 × 10⁻⁴) |

The counter analysis below uses the selected blocks, so it describes structure rather than testing it. The table counts counter decreases in time order:

| Episode | Decreases (blocks), listed alone | Unlisted alone | Combined | Reading |
|---|---:|---:|---:|---|
| 28 to 29 Jan (2,120 to 2,180) | 2 (38) | 1 (10) | 4 (48) | One counter |
| 11 to 12 Jan (150 to 210) | 2 (37) | 6 (18) | 12 (55) | Two concurrent counters |

**28 to 29 January: one counter, missed after a restart.** Listed block 2,131 has counter 41 at 16:19. There are no listed blocks from 2,132 to 2,141, while the unlisted blocks restart and climb 6, 9, 17, 19, 22, 23, 27, 34, 40 until 19:11. Listed blocks resume at 2,142 with counter **42**, then 54 and 88. Combining adds only the restart points, and no gap between these blocks is under 300 s. In the window as a whole, band-passing and dormancy go together (table above), which points to a separate owner for these blocks; the two spent band-passers there (2,147, 2,161) are what chance predicts among ordinary blocks. This is Patoshi's main counter; the list builder lost it for nine blocks after the restart. It is the same mechanism Phase 4 described for block 14,450.

**11 to 12 January: a short double helix.** From about 03:30 to 09:10 on 12 January, two counters climb side by side. For example, listed 2 → 17 → 26 → 33 runs alongside unlisted 3 → 11 → 13 → 15 → 17 → 26 → 28 → 31, and the list then continues at 36 and 48 on the *unlisted* strand. Listed blocks sometimes follow unlisted ones within 33 to 84 s. That is what two independent miners produce, and it is why Lopp excluded his known double helix (blocks 1,400 to 1,916) from timestamp statistics. Across all 24 unlisted blocks in this window, 20 pass the band against 4.7 expected (p = 3 × 10⁻¹¹); nothing in the window was ever spent, so dormancy adds nothing here. Most economical reading: a second Patoshi instance ran for a few hours, and the list recorded one strand plus parts of the other. **Alternative that cannot be excluded:** another miner running the same unusual software; no such miner is documented. [Lopp](https://blog.lopp.net/was-satoshi-a-greedy-miner/) already reports concurrent Patoshi miners, so the concept is not new; these particular unlisted blocks are the addition.

**Is it worth more work? (c)** Only a little. Together the two episodes are 28 blocks (1,400 BTC). Neither changes the picture of Patoshi's holdings. The finding that matters more is general (result 8): omissions concentrate after restarts and on concurrent counters, and a list-building method that follows one counter at a time will keep missing them. The list's published script contains only the height list, so its exact exclusion rule cannot be checked here.

## 4. Limits

- The shape test has wide intervals for small groups (70 blocks gives ±0.37) and is uninformative before 22,500.
- Dead-time evidence for the tail rests on 5 pairs. It supports the result but is not strong on its own.
- The Patoshi references are listed blocks, so any list errors enter them. Phase 5 puts those at about 15 of 21,953.
- Reading the counter sequences as "one counter" or "two counters" is an inference from monotonicity. Two machines restarted at the same moment could in principle mimic one counter.

## Reproduction

```powershell
python scripts/phase7_verify.py verify second manifest
python -m unittest tests.test_phase7
```
