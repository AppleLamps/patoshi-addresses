# Patoshi Addresses

Every Bitcoin address that received a block reward from **Patoshi**, the early miner whose distinctive nonce pattern dominates blocks mined in 2009 and early 2010. The list covers **22,087 addresses** holding **1,104,352.49 BTC** at issuance, almost all of it never moved. The repository also holds an independent, reproducible audit of where the list came from, whether it matches the chain, which coins have been spent, and how many Patoshi blocks the list misses.

**[Browse and search every address on the website](docs/index.html)**, which also shows the never-spent balance in US dollars (refreshed every 12 hours) and exports any filtered view as CSV or JSON. You can also download the full [address list](patoshi_p2pkh_addresses.csv).

> **Patoshi = Satoshi Nakamoto is a widely held hypothesis, not an assumption of this audit.** The block list is a published classification, not ground truth about who mined each block.

## At a glance

| | |
|---|---|
| Addresses in the original list | **21,953**, blocks 3 to 49,973 (January 2009 to April 2010) |
| Confirmed additions (October 2026) | **134** |
| BTC at issuance | **1,104,352.49** |
| Never spent | **22,035** addresses, **1,101,752.49 BTC** |
| Spent | **52** addresses: 31 from the original list, 21 from the additions |
| Spend status checked through | block 968,902 (27 September 2026) for the original list; 11 October 2026 for the additions |
| Best estimate of all Patoshi blocks | **about 22,481** (95% interval 22,388 to 22,572), about 1.124M BTC ([Phase 8](analysis/phase8/REPORT.md)) |

## The data

| File | What it holds |
|---|---|
| [`patoshi_p2pkh_addresses.csv`](patoshi_p2pkh_addresses.csv) | **The main list.** One row per block: `block_height`, `output_index`, `amount_btc`, the `p2pkh_address`, and the raw coinbase data it comes from |
| [`patoshi_additions_confirmed.csv`](patoshi_additions_confirmed.csv) | The 134 confirmed additions, with tier, evidence note, spend status and coinbase transaction ID |
| [`analysis/phase8/revised_list.csv`](analysis/phase8/revised_list.csv) | Every block from 0 to 54,620 with its Patoshi probability, tier, evidence and address |
| [`analysis/phase2_bigquery/spend_status_all.csv`](analysis/phase2_bigquery/spend_status_all.csv) | Spend status of every original-list address, with the spending transaction where one exists |
| [`patoshi_pubkeys_COMPLETE.csv`](patoshi_pubkeys_COMPLETE.csv) | The original upstream source file in raw coinbase form, kept byte-for-byte for provenance. It is not in address format; use the main list instead |
| [`docs/`](docs/index.html) | The website: the dollar balance, totals, a chart of Patoshi's share of each 250-block range, and a searchable ledger with CSV, JSON and copy export |
| [`docs/price.json`](docs/price.json) | The BTC/USD price behind the dollar balance, refreshed every 12 hours |

Four rewards include transaction fees; every other one is exactly 50 BTC.

| Block | Reward |
|---:|---:|
| 2,817 | 52.01 BTC |
| 19,863 | 50.14 BTC |
| 23,079 | 50.12 BTC |
| 28,507 | 50.22 BTC |

**About the address format.** In 2009 the Bitcoin client paid block rewards in an older output format called P2PK, before `1…` addresses were the norm. Each address in this list is the standard `1…` address for that reward, which is what wallets and block explorers show. Whether a reward was spent depends on its original output, not on later activity at the address. Since 2009, people have also sent 82,151 later payments to these addresses, of which about 7.05 BTC remains unspent; those are separate from the rewards ([Phase 3](analysis/phase3/REPORT.md)).

### Confirmed additions (2026-10-11)

The [134 additions](patoshi_additions_confirmed.csv) were confirmed as Patoshi-mined after the audit below. Each was verified against chain data: the coinbase script was read from the block, the address re-derived, and spend status checked at the original output. None overlap the 21,953.

| Tier | Count | Basis |
|---|---:|---|
| 2A | 6 | Counter-run structural confirmation |
| 2B-confirmed | 44 | 29 structural, 14 upgrades or singletons, 1 gap-fill reclassification; per-block counter-run adjudication |
| replication-confirmed | 84 | Independent replication of the fingerprint (Type-A/B/B) |

21 of the 134 have been spent, all in the replication set, between February 2010 and March 2017.

## What the audit found

**Patoshi mined about 22,481 blocks (95% interval 22,388 to 22,572), worth about 1.124 million BTC**, at heights 1 to 54,619. That is the 21,953 listed blocks, minus about 15 false positives (12 identified), plus about 189 omissions inside the list's span and about 353 blocks after its end at 49,973. The [revised list](analysis/phase8/revised_list.csv) names every height with its tier and evidence, and the [one-page summary](analysis/phase8/REPORT.md) ends with five checks anyone can run in ten minutes. The shipped address list is unchanged; the revision is a separate, probabilistic layer.

| Work | Result | Evidence and limit |
|---|---|---|
| **Revised count** | **22,481 blocks (22,388 to 22,572), ~1.124M BTC.** Remove 12 named false positives; add 111 robust and 307 probable named blocks (about 14 expected wrong); about 140 more estimated but not yet nameable | [Phase 8](analysis/phase8/REPORT.md); combines Phases 4 to 7, intervals exclude shared model assumptions |
| List audit | 21,953 distinct heights, 3–49,973; every address valid and unique; four rewards above 50 BTC | [Phase 1](analysis/phase1/REPORT.md); initially file-only |
| List provenance | Heights exactly equal [Lopp's September 2022 published list](https://github.com/jlopp/bitcoin-utils/blob/45b9eb0f0d71dc7dd66c51fd3058943c1f6df0cb/findPatoshiMiningStreaks.php); the bundled extractor contains only 6,183 of them | [Provenance report](analysis/provenance/REPORT.md); list membership does not prove miner attribution |
| Chain verification | **21,953/21,953** addresses and amounts match the block rewards on chain; zero mismatches | [Phase 2](analysis/phase2_bigquery/REPORT.md); BigQuery, with cryptographic and targeted live checks |
| Spending | **31 spent / 1,550 BTC**, all live-confirmed; **21,922 / 1,096,102.49 BTC** with no spend through the watermark | [Every status](analysis/phase2_bigquery/spend_status_all.csv); the 21,922 are checked against the index, not each against a live node |
| Novelty review | Bounded downstream traces, a census of later payments to the addresses, reset and boundary analyses; no demonstrated hidden message, hash collision, human schedule, weak address generation, or miner identity | [Phase 3](analysis/phase3/REPORT.md); separates replication from possible additions to prior work |
| Debian OpenSSL screen | **0 matches** in 7,339,808 modeled runs of the flawed Debian random-number generator, after reproducing nine published test vectors | [Follow-up](analysis/phase3/debian/REPORT.md); bounded PID, startup and offset window, not a complete exclusion |
| Spending graph vs list | **12 of the 31 spent listed rewards (600 BTC) were swept with 10 to 202 unlisted rewards each**; 8 sit on the sweeping miner's own counter track (7 of 11 sweeps; p = 8 × 10⁻⁸, conservative 4.5 × 10⁻⁵). Implied list inclusion rate for other miners' blocks: 0.33% (CI 0.02% to 1.35%). Block 14,450 is an omission candidate on two independent lines | [Phase 4](analysis/phase4/REPORT.md); common-input ownership is a heuristic |
| Signatures and wallets | **71,407/71,407** verifiable trace signatures verify; no R reuse or small nonces; January 2009 spends match the original client's change logic; 2016 and 2017 sweeps use modern wallet behaviour | [Phase 4](analysis/phase4/REPORT.md); bounded to traced transactions |
| Satoshi-linked identifiers | All five counterparty-documented Satoshi payments (Finney, Trammell, Bohm, Hearn) spend listed rewards in Patoshi-only clusters; **the May 2010 100 BTC went to Gavin Andresen's Faucet on 2010-07-11**; blocks 1 and 2 fit the pattern | [Links](analysis/phase4/LINKS.md); 98 sourced identifiers |
| Co-spend census | **27,898 of 54,620 early rewards spent; 22,959 blocks in the list's span owned by other miners by co-spending, only 12 of them listed**: false-positive rate 0.052% (CI 0.024% to 0.087%), about 15 heights, precision 99.93%. Omissions at most 1,144, estimated about 188 (recall about 99.1%). About 353 Patoshi-like blocks after 49,973, ending near 54,470 | [Phase 5](analysis/phase5/REPORT.md); ownership labels use only co-spent siblings' nonces, never the list |
| Per-block probability | Every block 1 to 54,619 scored from co-spending, nonce band, dormancy and counter tracks. **After the list's end: 318 blocks at P ≥ 0.9, robust core of 70 (50,882 to 54,311, 2010-04-14 to 05-03)**; inside the span: 99 at P ≥ 0.9, robust core of 41. Totals match Phase 5 under every setting | [Phase 6](analysis/phase6/REPORT.md); validated on hidden listed blocks and on known other-miner blocks |
| Independent check | Habits Phase 6 never used confirm it: nonce shape inside the band (Patoshi switches to ~50% low bytes from block 25,000) puts the 70-block tail core at **0.98 Patoshi (p = 5 × 10⁻⁹ if ordinary)**, and the posterior is calibrated bin by bin. The consecutive-block dead time (≥ 312 s) holds for every listed pair from 5,000 except 24,504. List omissions sit after counter restarts; the 11 to 12 January 2009 run is a second concurrent counter, the 28 to 29 January run a missed restart | [Phase 7](analysis/phase7/REPORT.md) |
| Nonce clock | **Ordinary miners' nonces grow with the time since the parent block; Patoshi's do not.** The stock client restarts at nonce 1 on each new block (z = −61 over 17,216 ordinary blocks). Patoshi did not restart its scan on new blocks (p = 0.096, with a positive control and a power check), answering a question Lerner left open in 2020. As a test independent of every earlier classifier, it finds 11 of the 12 contradicted blocks ordinary, the post-49,973 core 0.99 non-stock, and about 132 non-stock blocks among the unresolved. All 22 multi-transaction Patoshi blocks follow the stock transaction order | [Phase 9](analysis/phase9_nonce_clock/REPORT.md), preregistered; [novelty](analysis/phase9_nonce_clock/NOVELTY.md) |
| Clock in the model | **The nonce clock inside the per-block model passes all three preregistered checks**: hidden listed blocks are recovered better (0.65 → 0.80 in the late span), ordinary blocks are wrongly named less often, and the probabilities match nonce shape in every bin. 483 unlisted blocks reach P ≥ 0.9 (about 7 expected false), 418 of them robust; the robust tail runs from 50,882 to 54,316. The count barely moves (model sum about 22,530). A count using the clock alone agrees with Phase 5 (210 and 392 against 188 and 353) | [Phase 10](analysis/phase10_clock_model/REPORT.md), preregistered |
| Public discourse | Critiques, competing counts (21,744 to 22,503), BIP-360/361 and Hourglass, the "Noah Doe" lawsuit, the eCash fork, identity claims | [Ledger](analysis/phase4/DISCOURSE.md); as reported, mostly not re-verified |

The reports label every claim as **(a) a verified observation**, **(b) a statistical or model inference with a stated test**, or **(c) speculation**. BigQuery is a secondary chain index; each report says which material findings were also checked through a live API. An unlisted block is an *unlisted control*, not a proven different miner. BigQuery queries were separate snapshots; later spends or index corrections need a fresh audit.

## How the audit developed

Each phase builds on the ones before it. Expand a phase for its findings.

<details>
<summary><strong>1. Offline structural audit</strong></summary>

[Phase 1](analysis/phase1/REPORT.md) inspected every row of the list before any network retrieval. It checked height and address validity, duplicates, amounts, byte distributions, gaps and vanity patterns, then derived the address list. There are **28,018 unlisted heights in 8,899 intervals** within the height range; the longest interval is **426 heights**. Global and height-local permutation tests found structured gap behavior. No byte-level anomaly survived correction across 765 tests, and the short vanity-like strings, including block 264's `1CFB…` address, were not convincing evidence of intentional vanity mining. These are tests of the supplied list and its addresses, not of the miner's identity or of every possible way the addresses could have been generated.

</details>

<details>
<summary><strong>2. Provenance of the 21,953-block list</strong></summary>

The [provenance comparison](analysis/provenance/REPORT.md) found that the list's heights equal Lopp's 2022 list and the later [`TaintedBySatoshi` array](https://github.com/tehran19r/TaintedBySatoshi/blob/f013a619c7faa5db44de2e55b3423de48edef336/backend/src/data/patoshiBlocks.js), including order. The latter explicitly cites the `bensig/patoshi-addresses` source. The bundled [`extract_patoshi_addresses.py`](extract_patoshi_addresses.py) lists **6,183 heights, all present in the list**, leaving **15,770 heights found only in the shipped file**. It preserves the first 6,157 entries through height 8,044, then becomes sparse; it cannot reproduce the full file, and its default output filename also differs. No evidence establishes who populated the extra rows or which extractor produced them. The chain verification below independently checked their addresses and amounts.

The declared analysis population is the [pinned Lopp height file](analysis/provenance/lopp_patoshi_heights.txt). The older extractor remains as an artifact of the repository's history; running it does **not** regenerate the source file.

</details>

<details>
<summary><strong>3. Chain verification, spending and classifier checks</strong></summary>

[Phase 2](analysis/phase2_bigquery/REPORT.md) first inspected the actual `bigquery-public-data.crypto_bitcoin` schema and passed a ten-block smoke test, including the 52.01 BTC control. One bulk coinbase comparison then matched **all 21,953 complete P2PK scripts and amounts**. All queried coinbase transaction IDs were reconstructed; 54,620 consecutive block headers and their proof of work were checked. For **21,775** listed single-transaction blocks, the header Merkle root also directly binds the reconstructed coinbase. The remaining **178 multi-transaction blocks** have matching indexed outputs but no exhaustive independent Merkle-proof audit.

A whole-input-index outpoint join found **31 spent rewards**, each checked live through [mempool.space](https://mempool.space/docs/api/rest). The earliest is block 9's reward, spent at block 170; the latest listed spend occurred in December 2017. The count agrees with [Bitquery's September 2026 audit](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth), so the spend count is a verification, not a newly discovered movement. The other 21,922 have no spend reference through the BigQuery watermark, **block 968,902, timestamped 2026-09-27 23:24:41 UTC**. Query CSVs, SQL, metadata, spend statuses, live-check receipts and a [checksummed manifest](analysis/phase2_bigquery/manifest.json) are committed; full API and REST envelopes remain in an ignored local cache.

The same chain data were used to reproduce broad nonce-LSB and extraNonce *signatures*, not Lerner's original labeling process. All 21,953 listed blocks meet the broad nonce rule, but so do **602/3,000 unlisted controls**. The extraNonce consistency model accepts **4,075/4,290 evaluable held-out listed blocks** and **13/2,735 evaluable unlisted controls**. Its **1,005 review flags are not 1,005 proven misclassifications**. Block **37,808** alone fails Lerner's tighter 2020 nonce bound and remains a disputed attribution. Ten sampled unlisted blocks near the endpoint pass the local screening rules; none is promoted to a verified omission. No significant UTC hour or weekday pattern survived the specified temporal tests. [Methods, controls and limits](analysis/phase2_bigquery/METHODS.md).

</details>

<details>
<summary><strong>4. Novelty hunt and bounded null screens</strong></summary>

[Phase 3](analysis/phase3/REPORT.md) compared candidate findings with [Lerner's work](https://bitslog.com/2013/04/17/the-well-deserved-fortune-of-satoshi-nakamoto/), [BitMEX Research](https://web.archive.org/web/20241223083952/https://blog.bitmex.com/satoshis-1-million-bitcoin/), [Lopp](https://blog.lopp.net/was-satoshi-a-greedy-miner/) and [Bitquery](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth). The [literature ledger](analysis/phase3/SOURCES.md) records what was already published. Search absence cannot prove universal novelty.

- **Downstream trace:** the 31 spent rewards enter 20 first-spending transactions. Three further generations yielded 1,259 reconstructed transaction IDs and 1,474 explicit outpoint edges. A May 2010 **100 BTC** path has verified later 95/5 and 5/90 BTC splits; the related **500 BTC** path joins a previously discussed 9,000 BTC consolidation. Tracing stops at a documented frontier. Output-to-output "taint" allocations are heuristics, not ownership or physical coin tracking.
- **Later payments to the addresses:** exact script matching found 82,151 historical payments to 21,926 of the addresses. At the watermark, 82,149 of them, totaling **7.05258112 BTC**, had no spend reference. This is separate from the original reward balance. The two spent payments were genuine spends from the matching addresses, not a hash collision.
- **Counter and boundary review:** filtered extraNonce decreases produce an approximately several-day reset-candidate cadence, but a decrease is not proof of a reboot or backup. No reset-hour or weekday scheduling signal survived permutation testing. A separate multi-track classifier supported **41 of the 50 largest Phase 2 residual flags**; nine remain unresolved. Its recall is too low to replace the published block list. Candidate blocks around 49,973 and block 37,808 remain attribution questions.
- **Weak-address and coinbase screens:** none of the addresses came from the tested small or structured secrets or appears in the pinned Milk Sad corpus; no two share a HASH160; no tested 100-position ordering artifact; no extra coinbase message bytes or nonstandard script layout. These are bounded nulls. The stock client's 100-address pool was introduced after this block range, so a 100-reward refill premise is unsupported.
- **Quantum exposure:** the 21,922 never-spent original rewards, **1,096,102.49 BTC**, sit in P2PK outputs, which reveal more on chain than a modern address does. This is a conditional future quantum-risk measurement, not a demonstrated present-day attack. The report records a **September 28, 2026** BTC/USD quote for a historical snapshot; it is not a live valuation.

The later [Debian OpenSSL CVE-2008-0166 follow-up](analysis/phase3/debian/REPORT.md) searched published corpora of weak Debian output, modeled the historical random-number generator from source, reproduced **nine published P-256 test vectors**, then checked **7,339,808 modeled secp256k1 generator runs** against every address in the list with **zero matches**. It covers PIDs 1–32,767, little- and big-endian paths and the first 16 consecutive modeled runs across specified startup states. PID 0 or raised PID limits, deeper offsets, other preceding RNG calls and other process histories remain untested. This null does not show that the actual miner used Debian, or that every vulnerable output was excluded.

</details>

<details>
<summary><strong>5. Spending graph, signatures and public discourse</strong></summary>

[Phase 4](analysis/phase4/REPORT.md) turns the spending graph back on the list. Using only committed data, it splits the 20 first-spending transactions by their other inputs. Eleven of them, from 2010 to 2017, sweep one or two listed rewards together with **568 unlisted rewards** that pass Lerner's nonce band at the 21.7% chance rate of an ordinary miner. In 8 of those 12 listed cases, the listed block sits exactly on the sweeping miner's own extraNonce track: for example, unlisted 2,575 (649) → listed **2,577** (651) → unlisted 2,581 (655). Common-input ownership therefore says the headline "31 spent Patoshi rewards" overstates Patoshi spending. **19 rewards / 950 BTC** remain in Patoshi-only or Patoshi-majority spends. The same sweeps give a model-based list inclusion rate of **0.33%** for other miners' blocks, far below the 19.53% nonce-byte "floor" cited publicly.

In the other direction, unlisted block **14,450** was spent with nine listed rewards in May 2010 and fits the listed counter run 12 → 14 → 28. A full scan of all unlisted heights finds fits in 17 anchor windows against 15.3 expected by chance, so the list is close to complete for short runs. A five-block run at 27,474 to 27,478 is suggestive but not established once correlated counters are allowed for. All 71,407 verifiable signatures in the trace verify, with no nonce reuse.

Primary-source identifiers support the split: every payment that Hal Finney, Dustin Trammell, Nicholas Bohm or Mike Hearn documented as coming from Satoshi spends listed rewards in Patoshi-only clusters. On 2010-07-11 the May 2010 100 BTC went to [Gavin Andresen's Faucet donation address](https://satoshi.nakamotoinstitute.org/posts/bitcointalk/threads/88/) and was paid out 5 BTC at a time. The report also contains a [public discourse ledger](analysis/phase4/DISCOURSE.md), a [cross-reference of Satoshi-linked identifiers](analysis/phase4/LINKS.md) and a prioritised plan for extending this work.

</details>

<details>
<summary><strong>6. Complete co-spend census</strong></summary>

[Phase 5](analysis/phase5/REPORT.md) ran one BigQuery query over every block reward at heights 0 to 54,619 and every transaction that spent one: 0.576 TB, 2,644 transactions, 27,898 spent rewards. Each block's owner was labelled only from the nonce band of the *other* blocks spent with it, so the list and the block's own nonce never vote. Other miners' blocks, identified that way, pass the nonce band at 19.61%, the chance rate. Of **22,959 blocks in the list's span owned by other miners, 12 are listed**: a measured false-positive rate of **0.052%** (CI 0.024% to 0.087%), about 15 heights, or **99.93% precision**. This replaces Phase 4's model-based 0.33%.

Omissions are bounded because an omitted Patoshi block must pass the band and cannot have been swept by another miner. At most 1,144 unlisted heights qualify, and the excess over chance implies about 188 omitted blocks (recall about 99.1%), mostly at 25,000 to 29,999. The late-era undercount claimed at 40,000 to 44,999 finds about 8 there. Past the list's end, about **353 Patoshi-like blocks** appear between roughly 50,974 and 54,470, in line with public extensions of the pattern. Those are aggregate estimates, not named blocks.

</details>

<details>
<summary><strong>7. A probability for every block</strong></summary>

[Phase 6](analysis/phase6/REPORT.md) turns those aggregates into named blocks. Each block from 1 to 54,619 is scored from four kinds of evidence, none of which uses its own list membership: co-spending (Phase 5), the nonce band, dormancy, and whether its extraNonce sits on the time-line of neighbouring Patoshi-like blocks. Ordinary-miner rates come from blocks that fail the band; Patoshi's track rate and each window's share are fitted by EM.

After the list's end, **318 unlisted blocks score P ≥ 0.9, and 70 of them stay there under every track-test setting, from block 50,882 (14 April 2010) to 54,311 (3 May 2010)**. Inside the span, 99 blocks score P ≥ 0.9 (41 robust), clustered in January 2009 and at 25,000 to 27,499. The probabilities sum to Phase 5's independent totals. Hidden listed blocks are recovered at 97% (early) and 65% (late), even when excluded from every anchor set, and known other-miner blocks made to look like candidates are wrongly named 0.25% to 6% of the time, in line with the model's own error estimates. Nothing is added to the pinned list; the per-block file carries the evidence.

</details>

<details>
<summary><strong>8. Checking the probabilities with habits the model never saw</strong></summary>

[Phase 7](analysis/phase7/REPORT.md) tests Phase 6 against evidence it did not use. Patoshi's nonce *shape* inside the band changes around block 22,500: from 25,000 on, about half of its in-band low bytes are 0 to 9, against about a fifth for everyone else. On that basis alone the 70 post-endpoint core blocks are about 98% Patoshi (p = 5 × 10⁻⁹ if they were ordinary), the other 248 named blocks about 89%, and blocks the model rejected mostly not. The posterior is calibrated bin by bin, though it probably misses some late in-span omissions.

The published dead-time habit (consecutive Patoshi blocks at least ~312 s apart) holds for 10,243 of 10,244 listed pairs from height 5,000; the exception, 24,504, is the block Phase 4 found swept by another miner. The January 2009 "second machine" splits in two: 28 to 29 January is Patoshi's main counter after a restart that the list missed, while 11 to 12 January is a genuine second counter running alongside the first. More generally, 83% of named in-span omissions sit just after a counter restart or on a concurrent counter.

</details>

<details>
<summary><strong>9. One revised answer</strong></summary>

[Phase 8](analysis/phase8/REPORT.md) combines the measured pieces into one count and one list. The count is 21,953 − 14.7 + 189 + 353 + 2 ≈ **22,481 blocks (95% interval 22,388 to 22,572), about 1.124M BTC**. A Monte Carlo run carries through the sampling noise, the uncertainty in the ordinary miners' band rate (shared by both omission estimates) and the false-positive interval. The total agrees with the extended public counts (Whale Alert 22,503; satoshi-onchain ~22,540), now with measured error rates and named blocks.

[Every height is tiered](analysis/phase8/revised_list.csv): 21,941 listed and uncontradicted, 12 listed but contradicted, 111 robust additions, 307 probable, 94 possible, 1,296 unresolved, and the rest other miners' or without Patoshi evidence. The report ends with five checks, each verifiable from raw headers or one transaction.

</details>

<details>
<summary><strong>10. The nonce clock</strong></summary>

[Phase 9](analysis/phase9_nonce_clock/REPORT.md) asks whether a block's nonce records how long its miner had been working since the parent block. Its hypotheses and pass/fail rules were written down first ([preregistration](analysis/phase9_nonce_clock/PREREGISTRATION.md)).

- **Ordinary miners: yes.** The stock client restarts at nonce 1 whenever a new block arrives, so an ordinary miner's nonce grows with the gap: a median of 0.04% of the nonce space within 10 s of the parent, 7.4% after 10 to 60 minutes.
- **Patoshi: no.** Its scan position inside Lerner's nonce subranges does not depend on the gap (p = 0.096). A restart in even 10 to 20% of blocks would have been detected. Nor does the position advance steadily between its own blocks (p = 0.52).

That difference gives a test of who mined a block that uses none of the evidence earlier phases relied on. It confirms 11 of the 12 contradicted blocks as ordinary and the post-49,973 core as non-stock (0.99). It finds about 132 non-stock blocks among the 1,296 unresolved ones, and Patoshi's nonce shape confirms them independently. It caps possible Patoshi blocks outside the nonce band at about 60 to 90.

All 321 early blocks with two or more non-coinbase transactions, including 22 of Patoshi's, match the stock client's transaction order through their Merkle roots. So Patoshi changed the hashing loop, not block assembly. A 2026 claim that Patoshi restarted "from a low nonce each block" does not hold on this list. Novelty is bounded by the sources in [NOVELTY.md](analysis/phase9_nonce_clock/NOVELTY.md).

</details>

<details>
<summary><strong>11. The clock inside the per-block model</strong></summary>

[Phase 10](analysis/phase10_clock_model/REPORT.md) builds the nonce clock into Phase 6's model as one more piece of evidence and refits it. With the clock switched off, the code reproduces Phase 6 exactly. Switched on, it passes all three preregistered checks:

- hidden listed blocks are recovered more often (0.65 to 0.80 at P ≥ 0.9 in the late span);
- known ordinary blocks are wrongly named less often in every era;
- the probabilities agree with Patoshi's nonce shape, which the model never sees.

483 unlisted blocks now reach P ≥ 0.9, with about 7 expected false; 418 of them are robust to every counter-track setting. 119 are newly named, mostly from the unresolved and possible tiers, and 54 with stock-like nonces drop out, including part of the 27,474 to 27,478 run. The count barely moves. A count from the clock alone agrees with Phase 5's nonce-band estimates.

The clock also sees about 43 extra stock-like nonces among listed blocks without a counter-track fit. Only one of them was ever spent (44,838), where ordinary miners' blocks would give about 11, so they are not the list's usual kind of error.

</details>

## Files and reproduction

| Area | Primary files |
|---|---|
| Address data and website | [address list](patoshi_p2pkh_addresses.csv), [additions](patoshi_additions_confirmed.csv), [upstream source file](patoshi_pubkeys_COMPLETE.csv), [website](docs/index.html) built by [`scripts/build_site_data.py`](scripts/build_site_data.py) |
| Offline audit | [report](analysis/phase1/REPORT.md), [script](scripts/phase1_offline.py), [results](analysis/phase1/results.json) |
| Provenance | [report](analysis/provenance/REPORT.md), [comparison script](scripts/provenance_compare.py), [pinned heights](analysis/provenance/lopp_patoshi_heights.txt) |
| Chain verification | [report](analysis/phase2_bigquery/REPORT.md), [methods](analysis/phase2_bigquery/METHODS.md), [SQL](analysis/phase2_bigquery/sql/), [all spend statuses](analysis/phase2_bigquery/spend_status_all.csv) |
| Novelty work | [report](analysis/phase3/REPORT.md), [methods](analysis/phase3/METHODS.md), [source ledger](analysis/phase3/SOURCES.md), [cached query CSVs](analysis/phase3/results/) |
| Debian screen | [report](analysis/phase3/debian/REPORT.md), [model and screen](scripts/debian_weak_screen.py), [result](analysis/phase3/debian/result.json), [checksums](analysis/phase3/debian/manifest.json) |
| Phase 4 | [report](analysis/phase4/REPORT.md), [script](scripts/phase4_offline.py), [co-spend clusters](analysis/phase4/cospend_clusters.csv), [omission scan](analysis/phase4/sandwich_candidates.csv), [discourse](analysis/phase4/DISCOURSE.md), [identifier links](analysis/phase4/LINKS.md), [checksums](analysis/phase4/manifest.json) |
| Phase 5 | [report](analysis/phase5/REPORT.md), [methods](analysis/phase5/METHODS.md), [census SQL](analysis/phase5/sql/cospend_census.sql), [query result](analysis/phase5/results/cospend_census.csv), [every block's label](analysis/phase5/census_blocks.csv), [eras](analysis/phase5/census_eras.csv), [checksums](analysis/phase5/manifest.json) |
| Phase 6 | [report](analysis/phase6/REPORT.md), [script](scripts/phase6_posterior.py), [probability per block](analysis/phase6/posterior_blocks.csv), [ranked candidates](analysis/phase6/posterior_candidates.csv), [checksums](analysis/phase6/manifest.json) |
| Phase 7 | [report](analysis/phase7/REPORT.md), [script](scripts/phase7_verify.py), [habit tests](analysis/phase7/habit_tests.csv), [calibration](analysis/phase7/calibration_by_posterior.csv), [January 2009 episodes](analysis/phase7/second_sequence_blocks.csv), [checksums](analysis/phase7/manifest.json) |
| Phase 8 | [report](analysis/phase8/REPORT.md), [script](scripts/phase8_synthesis.py), [address query](scripts/phase8_pubkeys.py), [revised list](analysis/phase8/revised_list.csv), [tiers](analysis/phase8/tier_summary.csv), [estimate](analysis/phase8/revised_estimate.json), [checksums](analysis/phase8/manifest.json) |
| Phase 9 | [report](analysis/phase9_nonce_clock/REPORT.md), [preregistration](analysis/phase9_nonce_clock/PREREGISTRATION.md), [novelty](analysis/phase9_nonce_clock/NOVELTY.md), [script](scripts/phase9_nonce_clock.py), [transaction query](scripts/phase9_blocktx.py), [results](analysis/phase9_nonce_clock/results/), [checksums](analysis/phase9_nonce_clock/manifest.json) |
| Phase 10 | [report](analysis/phase10_clock_model/REPORT.md), [preregistration](analysis/phase10_clock_model/PREREGISTRATION.md), [script](scripts/phase10_clock_model.py), [probability per block](analysis/phase10_clock_model/posterior_m10.csv), [tier changes](analysis/phase10_clock_model/tier_changes.csv), [checksums](analysis/phase10_clock_model/manifest.json) |

### Website

The site in `docs/` is static and needs no build step to view. To publish it, enable GitHub Pages for the `main` branch and the `/docs` folder. After changing any of the address CSVs, regenerate its data file:

```sh
python scripts/build_site_data.py
```

The dollar balance is the never-spent BTC times the price in [`docs/price.json`](docs/price.json). The [Update BTC price](.github/workflows/update-price.yml) workflow runs [`scripts/update_price.py`](scripts/update_price.py) at 00:23 and 12:23 UTC. It records the median of the Coinbase, Kraken and CoinGecko spot prices and commits the file. To refresh it by hand, run the workflow from the Actions tab or run the script locally. An open page also reloads the price every 12 hours.

The export buttons above the ledger save exactly the addresses shown after search and filters, as CSV or JSON, or copy them to the clipboard one per line.

### Rerunning the analysis

Install the [analysis dependencies](requirements-analysis.txt) in a Python environment. These run offline, without cloud credentials:

| Phase | Command | Time |
|---|---|---|
| 1 | `python scripts/phase1_offline.py --permutations 1999` | |
| Provenance | `python scripts/provenance_compare.py --source lopp=analysis/provenance/sources/lopp_streaks_2022.php --source tehran=analysis/provenance/sources/tehran_patoshiBlocks_initial.js` | |
| 4 | `python scripts/phase4_offline.py cospend sandwich fingerprint signatures`, then `python scripts/phase4_links.py`, then `python scripts/phase4_offline.py manifest` | |
| 5 | `python scripts/phase5_offline.py census manifest` (from the committed query result) | |
| 6 | `python scripts/phase6_posterior.py posterior manifest` | about 40 s |
| 7 | `python scripts/phase7_verify.py verify second manifest` | |
| 8 | `python scripts/phase8_synthesis.py list estimate manifest` | |
| 9 | `python scripts/phase9_nonce_clock.py primary power amendment clock update stress clock_sensitivity assembly exploratory manifest` | about 8 min |
| 10 | `python scripts/phase10_clock_model.py model suspects manifest` | about 1 min |

Repeating the Phase 5 query (`python scripts/phase5_bigquery.py census`, dry run first, then `--execute`) needs BigQuery credentials; see its [methods](analysis/phase5/METHODS.md). For Phase 2, the committed [query results](analysis/phase2_bigquery/results/) and [methods](analysis/phase2_bigquery/METHODS.md) preserve the schema, SQL, query identities, output comparisons, spend statuses and watermark. Repeating the BigQuery collection requires Google application-default credentials and may process substantial data; a matching completed query reuses its committed CSV. Phase 3 offline reanalysis and its separately cached sources are documented in [Phase 3 methods](analysis/phase3/METHODS.md). The Debian report includes the four commands to validate vectors, rerun the bounded screen, aggregate and checksum it; the full screen is computationally expensive.

Ignored local caches contain raw BigQuery and live API responses, source downloads and progress files. A fresh clone has the committed result CSVs and receipts, but not every raw response envelope or external source archive. This distinction is recorded in the manifests and methods. The earlier per-block API collector was stopped when BigQuery became the bulk source; its files remain for audit history.

## Credits and interpretation

[Sergio Demian Lerner](https://bitslog.com/2013/04/17/the-well-deserved-fortune-of-satoshi-nakamoto/) identified the Patoshi patterns; [Jameson Lopp](https://blog.lopp.net/was-satoshi-a-greedy-miner/) published the height list used here. This audit checks that list's artifacts and chain consequences. It does not establish that every listed block came from one miner, that the miner was Satoshi, that observed spending identifies a person, or that an unlisted block cannot share the same mining pattern.
