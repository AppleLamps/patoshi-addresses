# Phase 5: complete co-spend census of every early coinbase

Completed 2026-09-28 UTC. Population: all 54,620 coinbases at heights 0 to 54,619, and the unchanged 21,953-height list. Spends were read to the frozen watermark (block 968,902). Labels follow the earlier reports: **(a)** verified observation, **(b)** statistical or model inference with a stated test, **(c)** speculation. "Patoshi = Satoshi" is not assumed. Methods, validation and limits are in [METHODS.md](METHODS.md).

**Data.** One BigQuery query ([SQL](sql/cospend_census.sql)) was run as job `job_l81CCOsoTsImvjjfGK_KZ6oZk7vW`, processing 0.576 TB (the dry run estimated 0.576 TB). It returned 88,285 rows: one coinbase output for each of the 54,620 heights (no coinbase in range has a second output) and all 33,665 inputs of the 2,644 transactions that spent any of them. The [result CSV](results/cospend_census.csv) and its [query metadata](results/cospend_census.metadata.json) are committed. The analysis is offline, took about 3 seconds, and its outputs are checksummed in [manifest.json](manifest.json).

## Headline results

| # | Result | Label | Evidence |
|---|---|---|---|
| 1 | **27,898 of the 54,620 early coinbases (51%) have been spent**, 26,723 of them in 1,469 transactions that co-spend two or more. The largest sweep takes 886 coinbases (heights 2,147 to 54,287). Most moved in 2010 and 2011 (23,375 coinbases). Only **31 listed coinbases** ever moved, the same 31 found in Phase 2. | (a) | [transactions](census_transactions.csv), [clusters](census_clusters.csv) |
| 2 | Each block's owner was labelled from the nonce band of the **other** blocks spent with it, never from the list. **22,959 blocks in the list's span are owned by other miners, and only 12 of them are listed.** List false-positive rate: **0.052%** (cluster bootstrap 95% CI 0.024% to 0.087%). | (b) | [summary](census_summary.json) |
| 3 | That implies **about 15 false-positive heights in the list (CI 7 to 24), i.e. precision 99.93% (99.89% to 99.97%)**. This replaces Phase 4's model-based extrapolation (0.33%, about 90 heights) with a direct measurement over 81.9% of all unlisted heights in the span. | (b) | [summary](census_summary.json) |
| 4 | The nonce band is a clean separator. Other miners' own blocks pass it at **19.61% (CI 19.10% to 20.13%)** over 22,947 blocks, which is the 19.53% chance rate for a uniform byte. | (b) | [summary](census_summary.json) |
| 5 | **Omissions are bounded.** An omitted Patoshi block cannot be owned by another miner, and it must pass the band. Only **1,144** unlisted heights in the span meet both conditions, so recall is at least **95.0%** (hard bound). About 994 of them are expected by chance, which leaves an excess of **about 150 omitted blocks (CI 94 to 205), recall about 99.3% (99.1% to 99.6%)**. | (b) | [eras](census_eras.csv) |
| 6 | **The late-era undercount claim is not supported.** At 40,000 to 44,999 the list holds 661 of 5,000 heights (13.2%), and 3,547 of the 4,339 unlisted heights there are owned by other miners. At most 162 unlisted heights (3.2%) could be omitted Patoshi blocks, and the excess over chance is **about 7 (CI 0 to 29)**. A residual ~14% share missed there would need about 700. | (b) | [eras](census_eras.csv) |
| 7 | **The pattern appears to continue past the list's end at 49,973.** From 49,974 to 54,619, unlisted heights not owned by another miner pass the band at 34.0%, against 20.2% for other miners' own blocks in the same window. That is an excess of **about 280 Patoshi-like blocks (CI 246 to 315)**, concentrated from about 50,974 and fading out around height 54,470. This agrees with public extensions of the pattern to about 54,316 to 54,458. | (b) | [summary](census_summary.json) |
| 8 | Across the whole early chain, the census finds **no listed block swept by another miner beyond Phase 4's 12**, and **no unlisted block swept with Patoshi coins beyond 14,450**. Phase 4's counter-track result is unchanged: 8 of 12, 7 of 11 sweeps, p = 8.0 × 10⁻⁸ (conservative 4.5 × 10⁻⁵). | (a) data, (b) inference | [false-positive list](census_listed_with_other_miner_co_members.csv), [omission list](census_omission_candidates.csv) |

**Summary.** For blocks owned by other miners, the published list is almost exactly right: roughly 15 false positives in 21,953, not the thousands implied by the "19.53% floor". Its main weaknesses are at the edges. There are about 150 omissions inside the span, concentrated at 25,000 to 29,999. And there is a tail of about 280 Patoshi-like blocks after the list stops. The census cannot measure recall directly from Patoshi-labelled clusters, because Patoshi coins almost never moved (10 blocks, one transaction). The recall figures come from the bound in result 5 instead.

## 1. What was spent, and when

**(a)** 2,644 transactions spent at least one early coinbase, from block 170 (January 2009) to block 965,646 (September 2026). Coinbases moved per year: 2,752 in 2009, 15,462 in 2010, 7,913 in 2011, then a long tail. That tail includes 531 in 2017 (the year of Phase 4's modern-wallet sweeps) and 12 so far in 2026, none of them listed. Cluster sizes: 357 transactions spend exactly two early coinbases, and 538 spend ten or more, covering 23,253 coinbases. No coinbase in range has more than one output, so every block's ownership unit is its single output-zero outpoint.

**Address reuse.** Joining coinbases that pay the same address adds no links: all 54,620 coinbases pay distinct addresses. Early miners, like Patoshi, used a fresh key per block.

## 2. Ownership labels, without the list

**(b)** Each block is labelled from the broad-nonce results of its co-spent siblings only (leave-one-out likelihood ratio, Patoshi 0.99 pass vs ordinary 50/256, threshold 1000:1; see [METHODS.md](METHODS.md)). Within the list's span (3 to 49,973):

| Label | Listed | Unlisted |
|---|---:|---:|
| other miner | 12 | 22,947 |
| Patoshi | 9 | 1 |
| undetermined (small or mixed sweeps) | 4 | 658 |
| unclustered (never spent with another early coinbase) | 21,928 | 4,412 |

If every labelled block's co-members were in fact the opposite class, the expected number of wrong labels would be 0.16 (false Patoshi) and 0.24 (false other-miner). The label error is therefore negligible next to the counts above.

**Calibration (b).** The labeller never looks at a block's own nonce, so the own-nonce pass rate of other-miner blocks is an unbiased measure of the non-Patoshi background. It is 4,500 of 22,947 = 19.61% (Wilson 19.10% to 20.13%), matching a uniform nonce low byte. In the 11 list-majority sweeps of Phase 4 the unlisted members passed at 21.7%. Over the full census the list-majority equivalent is 19.62%.

## 3. List precision, measured

**(b)** Of the 22,959 blocks in the span whose co-members identify another miner, 12 are listed: 0.052%. The 95% interval resamples whole clusters (901 of them), because one miner's sweep is not 901 independent draws; the Wilson interval (0.030% to 0.091%) is similar. The 22,947 unlisted blocks labelled other-miner are 81.9% of all 28,018 unlisted heights in the span. Carrying the rate to the rest gives about 15 false-positive heights (7 to 24) and precision 99.93%.

This assumes that a false-positive block, owned by an ordinary miner, was swept as often as that miner's other blocks. The sweeps are wallet consolidations that take every coin the owner holds, so nothing obvious would leave list false positives behind. The 12 contradicted blocks are the same 12 that Phase 4 found, and 8 of them sit on the sweeping miner's own extraNonce track (Phase 4, Result 2), so they are well supported.

**Comparison with Phase 4 (b).** The zero-truncated model over the same 11 sweeps now gives 0.327% (profile CI 0.019% to 1.33%), essentially unchanged. The census now maps 9 more unlisted members of those sweeps: Phase 4 left them as "probably coinbases of multi-transaction blocks", and they are. The model and the direct measurement agree within the model's wide interval, and the direct interval is about twenty times narrower.

## 4. Omissions: an upper bound and an estimate

**(b)** The census cannot measure recall directly, because only one sweep (the May 2010 500 BTC transaction, 10 blocks) is labelled Patoshi. Its one unlisted member is **14,450**, already identified in Phase 4 (tight nonce pass, fits the listed counter run 12 → 14 → 28). The census does bound omissions from the other side:

- An omitted Patoshi block cannot have been swept by another miner, which rules out 22,947 of the 28,018 unlisted heights in the span.
- It must pass the nonce band, as every listed block does. 1,144 of the remaining 5,071 do (893 of them unspent).
- Ordinary blocks among the 5,071 pass at the background rate, so about 994 passes are expected. The excess of about 150 (CI 94 to 205) estimates the omissions. The CI treats heights as independent, so it is optimistic.

| Heights | Listed | Unlisted not other-miner | Of which pass band | Expected by chance | Excess (95% CI) |
|---|---:|---:|---:|---:|---|
| 3 to 4,999 | 3,765 | 331 | 84 | 64.9 | 19 (5 to 33) |
| 5,000 to 9,999 | 3,856 | 140 | 26 | 27.5 | −2 (0 to 8) |
| 10,000 to 14,999 | 3,671 | 298 | 67 | 58.4 | 9 (0 to 22) |
| 15,000 to 19,999 | 3,506 | 193 | 45 | 37.8 | 7 (0 to 18) |
| 20,000 to 24,999 | 2,891 | 194 | 30 | 38.0 | −8 (0 to 3) |
| **25,000 to 29,999** | 1,453 | 731 | 200 | 143.4 | **57 (36 to 78)** |
| 30,000 to 34,999 | 893 | 817 | 183 | 160.2 | 23 (0 to 45) |
| 35,000 to 39,999 | 636 | 496 | 123 | 97.3 | 26 (8 to 43) |
| 40,000 to 44,999 | 661 | 792 | 162 | 155.3 | 7 (0 to 29) |
| 45,000 to 49,973 | 621 | 1,079 | 224 | 211.6 | 12 (0 to 38) |

The one clearly positive window, 25,000 to 29,999, contains Phase 4's suggestive five-block run 27,474 to 27,478. The excess is an aggregate: it does not say *which* of the 200 band-passing heights are the omitted ones. Picking them out is the per-block posterior (plan item 2 below).

**On the late-era undercount claim.** Phase 4 recorded [Szpili/patoshi-forensics](https://github.com/Szpili/patoshi-forensics) as estimating about 14% Patoshi share at 40,000 to 44,999 with "about 2% listed". The list itself holds 13.2% of that window, so the 2% figure does not describe this list. Read as "about 14% of blocks missed", the claim needs about 700 omitted blocks where the census leaves room for at most 162 and estimates about 7.

## 5. After the list's endpoint

**(b)** The list stops at 49,973, while Whale Alert and satoshi-onchain extend the pattern to about 54,316 to 54,458 ([DISCOURSE.md](../phase4/DISCOURSE.md)). The same test from 49,974 to 54,619 gives 1,947 unlisted heights not owned by another miner, of which 662 pass the band (34.0%). Other miners' own blocks in the same window pass at 20.2% (544 of 2,699), and the chance expectation is 382. The excess is **about 280 (CI 246 to 315)**. Per 500 heights, the excess is near zero at 49,974 to 50,473 (28 passing vs 29 expected). It is 9 at 50,474 to 50,973, then 27 to 51 per window from 50,974 to 54,473, and gone at 54,474 to 54,619 (8 vs 12). A Patoshi-like miner therefore appears to have kept mining, at a lower share, for about 3,500 blocks after a short pause following the list's endpoint. The tail stops around 54,470, near the public estimates.

This is an aggregate inference, not a list of blocks, and it assumes the nonce band still marks the same miner. Extending the pinned list would need per-block evidence, such as counter tracks.

## 6. What changes in earlier reports

- Phase 4 Result 4 (0.33%, about 90 false-positive heights, precision about 99.6%) is superseded by Results 2 and 3 above (0.052%, about 15 heights, 99.93%). Phase 4's direction was right, and its interval contained the measured value.
- Phase 4's "19 coinbases / 950 BTC in Patoshi-only or Patoshi-majority spends" stands. The census finds no further listed block in another miner's sweep.
- The Phase 4 limit "this scan cannot see late-era omissions" is addressed in section 4. Late-era omissions are small inside the span, but there is a tail after it.

## 7. Limits

- **Common-input ownership** is a heuristic. The 1,285 other-miner sweeps are mostly consolidations of dozens to hundreds of P2PK coinbases, where it is strong. Small sweeps get no label.
- **Spent vs unspent.** Precision is measured on swept blocks (81.9% of unlisted heights in the span), and the omission bound uses the unswept rest. Both assume a block's chance of being swept does not depend on whether the list includes it.
- **The nonce band as a necessary condition.** Every listed block passes it by construction, and the bound assumes genuine Patoshi blocks do too. A Patoshi block outside the band would escape the bound. It would also escape every published classifier.
- **Independence.** The omission intervals treat heights as independent. One miner's correlated nonce habits would widen them, but the measured background (19.61% on 22,947 blocks) shows no such habit on average.

## 8. Next steps (updated plan)

1. **Per-block posterior.** Combine the census ownership label, the nonce band, counter-track and run fits into one probability per height. Rank the 1,144 in-span and 662 post-endpoint band-passing candidates. This turns results 5 and 7 into named blocks.
2. **Late-era estimator.** Phase 4's plan item 3 is partly answered by section 4. What remains is to fit the Patoshi share per window as a mixture, now with the measured 19.61% background instead of the assumed 19.5%.
3. The remaining Phase 4 plan items (counterparty documents, labelled tracing of the May 2010 path, the dormancy watch, gap-corrected time of day, quantum exposure) are unchanged.

## Reproduction

```powershell
python scripts/phase5_bigquery.py census             # dry run; reuses the committed result when present
python scripts/phase5_offline.py census manifest
python -m unittest tests.test_phase5
```

A fresh BigQuery run needs gcloud application-default credentials, or `GOOGLE_APPLICATION_CREDENTIALS` pointing to a service-account key with BigQuery job permission. The committed CSV lets everything after the query run offline.
