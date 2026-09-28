# How many blocks did Patoshi mine, and which ones?

Completed 2026-09-28 UTC. This page pulls Phases 4 to 7 of this audit into one answer. Nothing new is measured here. The script combines the committed results, and the per-block list and the estimate below regenerate offline in a few seconds. Labels: **(a)** verified observation, **(b)** statistical inference with a stated test. "Patoshi = Satoshi" is not assumed.

## The answer (b)

**About 22,481 blocks (95% interval 22,388 to 22,572), worth about 1,124,000 BTC (1,119,000 to 1,129,000)**, at heights 1 to 54,619. The genesis block (height 0) is excluded, as in every published count.

| Component | Estimate (95% interval) | Measured by | How |
|---|---|---|---|
| Blocks on the published list (Lopp 2022, heights 3 to 49,973) | 21,953 | – | – |
| minus: false positives on the list | 14.7 (12.0 to 23.5) | [Phase 5](../phase5/REPORT.md) | Co-spend census: 12 listed blocks swept by other miners are identified; the measured rate (0.052% of 22,959 other-miner blocks) implies about 3 more |
| plus: omissions inside the list's span | 189 (111 to 265) | [Phase 5](../phase5/REPORT.md), [6](../phase6/REPORT.md) | Nonce-band excess among the 5,071 unlisted blocks not owned by another miner |
| plus: blocks after the list's end (49,974 to 54,619) | 353 (308 to 397) | Phases [5](../phase5/REPORT.md) to [7](../phase7/REPORT.md) | Same estimator after 49,973; per-block evidence in Phase 6, independent checks in Phase 7 |
| plus: blocks 1 and 2 (before the list's first height) | 2 (1 to 2) | [Phase 6](../phase6/REPORT.md) | Posteriors 0.83 and 0.98 |
| **Total** | **22,481 (22,388 to 22,572)** | | 200,000-draw Monte Carlo, [revised_estimate.json](revised_estimate.json) |

The interval combines three sources of uncertainty: sampling noise in each count, uncertainty in the ordinary miners' band rate (measured on 22,947 blocks and shared by both omission estimates), and the bootstrap interval of the false positives. It treats heights as independent, so it is somewhat optimistic. Shared assumptions (co-spending means common ownership, the nonce band marks Patoshi) are not inside it. Sensitivity checks all land inside the interval: a Patoshi band rate of 1.0 instead of 0.99 gives 22,474; an era-specific background after 49,973 gives 22,470; summing the Phase 6 per-block probabilities instead gives 22,512.

**Compared with published counts** ([ledger](../phase4/DISCOURSE.md)): Lopp's list has 21,953 blocks (to 49,973), Whale Alert (2020) 22,503 (to 54,316), and satoshi-onchain (2026) about 22,540 (to about 54,458). This estimate agrees with the extended counts on the total. It differs in how it is backed: a measured false-positive rate, a measured omission rate, intervals, and a named block list whose error rates were checked against independent evidence.

## Which blocks (b)

Every height from 0 to 54,619 is in [revised_list.csv](revised_list.csv) with its tier, probability, evidence flags, coinbase value and a short evidence note. Counts per tier are in [tier_summary.csv](tier_summary.csv).

| Tier | Blocks | Expected Patoshi | Meaning |
|---|---:|---:|---|
| `listed_uncontradicted` | 21,941 | about 21,938 | On the list; no evidence against. About 3 unidentified false positives are expected among them |
| `listed_contradicted` | 12 | 0 | On the list but swept together with another miner's coins: 2,577, 24,504, 34,813, 35,573, 35,599, 37,764, 37,808, 39,647, 46,844, 48,277, 49,174, 49,958 |
| `added_robust` | 111 | 107 | Not listed; P ≥ 0.9 under every track-test setting. 41 inside the span, 70 after it (50,882 to 54,311) |
| `added_probable` | 307 | 297 | Not listed; P ≥ 0.9 under the primary setting only. 58 inside the span, 248 after it, and block 2 |
| `added_possible` | 94 | 66 | Not listed; 0.5 ≤ P < 0.9 (includes block 1) |
| `unresolved` | 1,296 | 98 | Never co-spent with another miner and passing the band, but no track fit: a mixture holding most of the remaining unnamed omissions |
| `other_miner` | 25,646 | 0 | Swept with another miner's coins |
| `no_patoshi_evidence` | 5,212 | 6 | Fails the band, or otherwise nothing Patoshi-like |
| `genesis` | 1 | – | Height 0, unspendable, excluded |

In short: remove 12 named blocks (plus about 3 that cannot yet be named), and add 418 named blocks at P ≥ 0.9 (about 14 of them expected to be wrong). About 140 further omissions are estimated but cannot yet be pinned to individual blocks.

## Five checks anyone can do in ten minutes (a)

Each check uses only public chain data: block headers and coinbase scripts.

1. **24,504 is not Patoshi's.** Block 24,503 (listed) is timestamped 17:43:19 on 2009-10-07, and 24,504 is timestamped 17:44:24, 65 s later. From height 5,000 on, every other pair of consecutive listed blocks is at least 312 s apart (10,243 of 10,244 pairs; the rule was first reported by [Lerner 2020](https://bitslog.com/2020/06/22/a-new-mystery-in-patoshi-timestamps/)). Independently, 24,504's coinbase was spent on 2010-07-21 (block 69,345) in one transaction with 38 unlisted coinbases from heights 23,697 to 46,864 ([Phase 4](../phase4/cospend_clusters.csv)), and [Lopp](https://github.com/janoside/btc-rpc-explorer/discussions/465) flagged it for the same gap.
2. **Listed blocks swept by other miners.** Block 2,577's coinbase was spent in June 2011 in one transaction with 202 unlisted coinbases (heights 2,163 to 7,663). Its extraNonce (651) sits between the sweeping miner's own neighbours, 2,575 (649) and 2,581 (655). The other 11 are in [Phase 4](../phase4/REPORT.md#1-common-input-clusters-of-the-first-spends).
3. **14,450 is Patoshi's.** It was spent on 2010-05-17 in [499d0f…](https://mempool.space/tx/499d0f5d452891ebe18a8c23cc0a554459a0ba3341ef021f3fae15926a977ffd) together with nine listed coinbases, and its counter (14) fits between the listed 14,449 (12) and 14,453 (28).
4. **The list missed a restart.** The coinbase scriptSig ends with the extraNonce. At 2,131 (listed, 16:19 on 2009-01-28) it is 0x29 = 41. Blocks 2,132 to 2,141 are unlisted, restart at 6 and climb to 0x28 = 40 at 19:11. The listed sequence resumes at 2,142 with 0x2a = 42 ([Phase 7](../phase7/REPORT.md#3-the-january-2009-sequences)).
5. **The post-endpoint blocks carry Patoshi's late nonce habit.** From height 25,000 on, about half of listed Patoshi blocks have a nonce low byte of 0 to 9, against about a fifth of other miners' band-passing blocks. Among the 70 robust post-endpoint additions, 33 of 70 do (47%), against 17% for other miners after 49,973 ([Phase 7](../phase7/habit_tests.csv); p = 5 × 10⁻⁹ if they were ordinary). Phase 6 never used this feature.

## What would change the answer

- **A consolidation that mixes owners** (a custodian or CoinJoin) would undermine the co-spend labels behind the false positives and the ordinary-miner references.
- **A miner running Patoshi's unusual nonce behaviour** would inflate both omission estimates. No such miner is documented, and after 49,973 the nonce shape and dead-time checks both point to Patoshi.
- **Patoshi blocks outside the nonce band** would be missed by this estimate and by every published classifier.
- **Correlated nonce habits of ordinary miners** would widen the intervals. The measured background (19.61% vs 19.53% uniform) shows none on average.

## Reproduction

```powershell
python scripts/phase8_synthesis.py list estimate manifest
python -m unittest tests.test_phase8
```

It reads only committed outputs of Phases 4 to 7. The inputs are checksummed in [manifest.json](manifest.json).
