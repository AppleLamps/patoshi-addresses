# Phase 4: what the spending graph says about the list, plus public discourse and next steps

Completed 2026-09-28 UTC. Population: the unchanged 21,953-height list. All analyses are **offline** on data already committed by Phases 2 and 3 (54,620 headers, the 20 first-spending transactions with full prevouts, and 1,239 reconstructed downstream transactions). No network, key recovery, signing or fund movement. Labels follow the earlier reports: **(a)** verified observation, **(b)** statistical or model inference with a stated test, **(c)** speculation. "Patoshi = Satoshi" is not assumed.

Two companion documents:

- [DISCOURSE.md](DISCOURSE.md) is a ledger of what the public is saying (2024 to September 2026): critiques, competing lists, the quantum debate, the "Noah Doe" lawsuit, the eCash fork and identity claims.
- [LINKS.md](LINKS.md) cross-references Satoshi-associated identifiers from primary sources against the dataset.

## Headline results

| # | Result | Label | Evidence |
|---|---|---|---|
| 1 | **12 of the 31 spent listed coinbases (600 BTC) were swept together with 10 to 202 unlisted coinbases each** (568 unlisted in total) by 11 transactions from 2010 to 2017. Common-input ownership says those 12 belonged to other miners. | (a) data, (b) ownership inference | [clusters](cospend_clusters.csv), [inputs](cospend_inputs.csv) |
| 2 | **8 of those 12 sit exactly on the co-spending miner's own extraNonce track** (for example 2575 → **2577** → 2581, counters 649 → 651 → 655). Counting one trial per sweep, 7 of 11 sweeps contain a fit against 0.71 expected by chance: p = 8 × 10⁻⁸, or 4.5 × 10⁻⁵ with conservative (Wilson upper-bound) chance rates. | (b) | [track test](cospend_listed_in_other_miner_clusters.csv) |
| 3 | The co-spent unlisted coinbases pass Lerner's nonce rule at **21.7%** (123/568), matching the 19.5% chance rate for an ordinary miner (p = 0.11), not the ~100% expected for Patoshi. | (b) | [summary](cospend_summary.json) |
| 4 | A zero-truncated binomial fit gives a **list inclusion rate of 0.33% (95% profile CI 0.02% to 1.35%)** for other miners' blocks. Taken naively over ~28,000 non-Patoshi heights, that is roughly **90 false-positive heights (CI ~5 to ~380)**, i.e. roughly 99.6% precision. This is far from the "19.53% false-positive floor" circulating publicly, which describes the nonce byte alone, not the published list. | (b), generalisation is (c) | [summary](cospend_summary.json) |
| 5 | **Block 14,450 is an omission candidate supported by two independent lines**: it was spent with nine listed coinbases in the May 2010 500 BTC transaction, and it fits the listed Patoshi counter run 12 → **14** → 28 in time order with a passing tight nonce. | (a) data, (b) inference | [clusters](cospend_clusters.csv) |
| 6 | A full scan of all 28,018 unlisted heights finds 21 short-run fits in **17 anchor windows against 15.3 expected by chance** (p = 0.36). The list is close to complete *for short monotone runs*, and this test cannot see late-era omissions. Standouts: block **3,358**, and a **five-block run 27,474 to 27,478** inside one window (p ≈ 4 × 10⁻⁵ after correcting for all 7,959 windows under independence, but only 0.23 if one miner's counters are fully correlated). | (b) | [candidates](sandwich_candidates.csv), [summary](sandwich_summary.json) |
| 7 | **71,407 of 71,407 verifiable signatures in the trace verify**, including all 36 made by listed keys. No reused R value (same or different key), no nonce k in 1 to 65,536 or k = ½, and no non-canonical DER. | (a) | [summary](signature_summary.json), [forensic subset](signature_inputs.csv) |
| 8 | **Documented Satoshi payments validate the split.** All five first spends documented by the counterparties (Hal Finney, Dustin Trammell, Nicholas Bohm twice, Mike Hearn) are funded by listed coinbases in Patoshi-only clusters. None of the 12 ownership-contradicted blocks appears in any documented Satoshi transaction. | (a) | [LINKS.md](LINKS.md) |
| 9 | **The May 2010 100 BTC (listed coinbases 877 and 15,625) went on 2010-07-11 to Gavin Andresen's Bitcoin Faucet donation address `15VjRaDX…`.** The "95/5 then 5/90" splits Phase 3 reported are two 5 BTC faucet payouts. | (a) chain and forum post; (c) donor identity | [LINKS.md](LINKS.md) section 2 |
| 10 | Blocks **1 and 2** pass the tight nonce test and lead monotonically into listed blocks 3 and 4 (counters 4 → 11 → 14 → 26 within 22 minutes). They are omission candidates at the start of the list. Documented non-Satoshi blocks 78 (Finney) and 309 (Trammell) fail the nonce band, as they should. | (b) | [LINKS.md](LINKS.md) section 3 |
| 11 | The January 2009 spends (blocks 170 to 546) match the original client's `CreateTransaction` exactly: payee first, change second, **change back to the same key**. The 2016 and 2017 sweeps use anti-fee-sniping locktimes, `0xfffffffe` sequences, version 2 and low-S signatures. That is modern wallet behaviour. | (a) data, (b) software attribution | [fingerprint](wallet_fingerprint.csv), [follow-ons](early_followon_behaviour.csv) |

**Summary of the first spends.** The 20 first-spending transactions now split three ways. Five are Satoshi payments documented by the other party. The May 2010 100 BTC ended up as a Faucet donation. Eleven are other miners' sweeps. The rest (the May 2010 500 BTC, and single spends at 69,714 and 479,599) have no documented counterparty.

**The most consequential point:** the widely repeated "31 Patoshi coinbases / 1,550 BTC have moved" overstates Patoshi spending. Genuine Patoshi coins almost never move, so the spent subset is heavily enriched for list false positives. After removing the 12 co-spent with other miners, **19 coinbases / 950 BTC** remain in Patoshi-only or Patoshi-majority spends. Of those, block 44,838 (a lone 2017 spend by modern software, counter 59 not on any listed run, already flagged in Phase 2) is also doubtful. [satoshi-onchain](https://github.com/satoshi-onchain/satoshi-onchain) argues the same direction from dormancy rates (6.2% vs 86.7% spent). The ownership-based decomposition, the counter-track confirmation and the list-precision estimate were not found in the sources in [DISCOURSE.md](DISCOURSE.md) or [SOURCES.md](../phase3/SOURCES.md). Search absence is not proof of novelty.

## 1. Common-input clusters of the first spends

**(a)** The 20 first-spending transactions were split by their other inputs. Coinbase heights are recovered from committed header Merkle roots (single-transaction blocks) and committed coinbase rows, giving 53,720 mapped coinbase txids. Unmapped inputs (40 of 640: 13 are 50 BTC P2PK outputs, probably coinbases of multi-transaction blocks; 27 are 0.0001 to 0.001 BTC P2PKH outputs) are excluded from counts.

| Class | Transactions | Listed coinbases | Examples |
|---|---:|---:|---|
| Listed only | 8 | 10 | 170 (block 9 → Hal Finney), 524, 2616, 2754, 11408, 56180 (May 2010 100 BTC), 69714, 479599 |
| Listed majority | 1 | 9 | 56173: nine listed plus unlisted 14,450 (May 2010 500 BTC) |
| Unlisted majority | 11 | 12 | 128196 (June 2011): 1 listed + 202 unlisted from 2,163 to 7,663; 498031 (Dec 2017): 1 + 79 |

**(b)** In the unlisted-majority sweeps the non-listed coinbases behave like an ordinary miner. Their nonce low byte passes the Patoshi band at 21.7%, against 19.5% for a uniform byte. The listed member of each sweep is the odd one out, and in 8 of 12 cases it also sits between the sweeping miner's own neighbouring blocks in counter *and* time:

| Listed height | Co-spending miner's neighbours (height: counter) | Listed counter | Chance fit rate |
|---:|---|---:|---:|
| 2,577 | 2,575: 649 → 2,581: 655 | 651 | 1.3% |
| 34,813 | 34,780: 103 → 34,817: 140 | 136 | 0.5% |
| 35,573 | 35,564: 330 → 35,588: 354 | 339 | 5.1% |
| 35,599 | 35,597: 363 → 35,617: 384 | 365 | 5.1% |
| 39,647 | 39,632: 180 → 39,671: 215 | 181 | 1.1% |
| 48,277 | 48,232: 10 → 48,279: 54 | 52 | 2.7% |
| 49,174 | 48,998: 4,150 → 49,380: 4,574 | 4,360 | 10.6% |
| 37,808 | 37,729: 84 → 37,844: 920 | 152 | 11.6% |

"Chance fit rate" is the share of all other listed blocks in the same height span that happen to fit the same miner's track. Block-level trials inside one sweep share a track and a calibration sample (35,573 and 35,599 come from the same transaction), so the test counts one trial per sweep: "does any listed member fit?". Its chance probability is 1 − ∏(1 − rate), which is generous to the null. Seven of the 11 sweeps have a fit against 0.71 expected, Poisson-binomial p = 8.0 × 10⁻⁸. Replacing every rate by its Wilson 95% upper bound (expected 1.76) gives p = 4.5 × 10⁻⁵. These blocks also fit a listed Patoshi run (10 of 12), which is the known overlapping-slope problem ([BitMEX 2018](https://web.archive.org/web/20241223083952/https://blog.bitmex.com/satoshis-1-million-bitcoin/)). Spending history breaks the tie that the mining fingerprint alone cannot.

**Assumptions and limits.** Common-input ownership is a heuristic. It is strong for 2010 to 2017 sweeps of dozens of P2PK coinbases into one or two outputs, but not proof: a buyer of private keys or a custodian could combine coins. The track test uses nearest cluster neighbours and does not model counter resets. Block 37,808 was already disputed on nonce grounds (Phase 3); here it gains a second, independent strike.

**List precision (b/c).** Each unlisted-majority sweep is observed only because it contains at least one listed coinbase, so the per-block inclusion rate is fitted with a zero-truncated binomial over the 11 sweeps (n = mapped coinbases, k = listed). The estimate is 0.33% (0.02% to 1.35%). Carrying it to all ~28,000 non-Patoshi heights assumes that these sweeping miners are typical and that inclusion errors are independent. Both are uncheckable here, so the ~90 figure is an order of magnitude, not a count.

## 2. Omission candidates

**Block 14,450 (a/b).** Mined 2009-05-14 20:23:07 UTC with tight nonce pass (low byte 31) and extraNonce 14. Listed neighbours: 14,449 at 20:05:29 (counter 12) and 14,453 at 20:45:24 (counter 28), just after a Patoshi reset at 14,445 (counter 3). It was spent on 2010-05-17 in [499d0f…](https://mempool.space/tx/499d0f5d452891ebe18a8c23cc0a554459a0ba3341ef021f3fae15926a977ffd) with nine listed coinbases. Phase 3 noted "one 50 BTC coinbase outside" the pinned population in that path; this identifies it and shows it fits the Patoshi counter. Low post-reset counters overlap with ordinary miners, which plausibly explains why a list builder would leave it out.

**Full scan (b).** An unlisted height counts as a candidate when it lies between consecutive listed heights L and R such that:

- the time from L to R is at most 3 hours;
- 0 ≤ counter(R) − counter(L) ≤ 60;
- time(L) < time(h) < time(R);
- counter(L) < counter(h) < counter(R), strictly, because the counter never repeats between Patoshi blocks;
- the tight nonce test passes.

The null for each evaluable height is 0.1907 (the chance a uniform nonce passes the tight test) times the share of nearby broad-nonce-failing blocks whose counters fall strictly inside the window. Candidates sharing an anchor window are not independent, so inference is per window: an event is at least one candidate, with chance 1 − ∏(1 − p) over the window's heights. Result: 20,818 evaluable heights in 7,959 windows, **21 candidate heights in 17 windows, 15.28 windows expected** (Poisson-binomial p = 0.36). By window false-positive stratum (below 0.002, 0.002 to 0.01, 0.01 and above), observed/expected is 1/1.16, 6/3.83 and 10/10.29. As a group, the scan shows no excess over chance.

- **27,474 to 27,478**: five consecutive unlisted blocks, counters 101, 112, 118, 123, 132 between listed 27,473 (92) and 27,479 (149), all tight-nonce passes, monotone timestamps from 03:09 to 04:51 UTC on 2009-11-19. They fill their window entirely. Under independent heights, five hits have p = 4.7 × 10⁻⁹, or 3.8 × 10⁻⁵ after multiplying by all 7,959 windows. An ordinary miner's consecutive blocks have correlated counters, though. The conservative bound keeps only the five nonce passes independent (0.19⁴ times the largest single-height probability, times the number of 5-height combinations) and gives 2.9 × 10⁻⁵ per window, **0.23 after the window correction**. That makes this run suggestive, not established. Phase 2 accepted 27,474 as an unlisted control; Phase 3's fixed slope model rejects all five (residual about −120) because its track sits on a different line.
- **3,358**: counter 1,336 between 1,318 and 1,341, where ordinary miners' counters are nowhere near (null probability ~0). Phase 3's slope model also accepts it (residual +9.0).

**Limits.** The rule only sees short, dense runs. Later in the series the counter step between Patoshi blocks grows into the hundreds. [Szpili/patoshi-forensics](https://github.com/Szpili/patoshi-forensics) argues the list undercounts there (about 14% estimated share vs about 2% listed at 40,000 to 44,999). This scan cannot confirm or refute that. None of these candidates is promoted into the pinned list.

## 3. Signature forensics

**(a)** All 88,865 input signatures in the 1,259 transactions were parsed. Every single-signature legacy input whose previous output script is recoverable from committed data (71,407) was verified with a from-scratch legacy SIGHASH_ALL digest; there were **zero failures**. Not verified: 17,016 P2SH (multisig) signatures and 442 P2PK signatures whose previous output lies outside the committed data. Their R values still enter the reuse check. Six segwit inputs were skipped. The unit test reproduces the block 170 signature and shows that a one-satoshi change breaks it.

- All 36 signatures by listed keys verify. They cover the 31 coinbase spends plus five later January 2009 spends of change returned to keys 9 and 286.
- **No R reuse**, same-key or cross-key. Same-key reuse would expose a private key; none exists in this trace. No R value equals x(kG) for k in 1 to 65,536 or for k = ½.
- All signatures are strict DER. High-S signatures make up 690/1,311 before height 100,000 and 310/631 from 100,000 to 390,999, which is what random signing gives. From height 391,000 on it is **0 of 86,923**, consistent with post-2015 low-S wallets.

These are bounded nulls: they cover only the traced transactions and cannot say anything about the 21,922 unspent keys, which have never signed.

## 4. Wallet fingerprints

**(a)** The original client's `CreateTransaction` puts the payee in `vout[0]` and change in `vout[1]`, and "use[s] the same key as one of the coins" for change ([original source](https://github.com/trottier/original-bitcoin/blob/master/src/main.cpp)). Transactions at heights 170, 181, 182, 183, 524, 545 and the first of two at 546 all follow that layout with P2PK outputs; 181 to 183 are successive spends of the block 9 key's returned change (10, 1 and 1 BTC payments). The February 2009 first spends at 2616 and 2754 pay a whole coinbase amount to a single P2PKH output without change.

**(b)** The 2016 and 2017 unlisted-majority sweeps have:

- non-zero `nLockTime` in all seven, within 100 blocks of the tip in six (anti-fee-sniping);
- `0xfffffffe` sequences (one uses `0xfffffffd`, the opt-in replace-by-fee signal);
- version 2 in four of them;
- P2SH outputs in five, and only low-S signatures.
- in the two late-2017 sweeps (86 and 81 inputs), inputs sorted in BIP69 order, which random ordering would essentially never produce. That points to a wallet implementing BIP69 input sorting.

That profile belongs to modern wallet software, not the 2009 codebase. The lone 2017 spend of listed block 44,838 has the same modern profile. Software does not identify an owner. It does show these sweeps were not made with the original client.

## 5. What people are saying (summary of [DISCOURSE.md](DISCOURSE.md))

- **Sceptics have shifted from "no Patoshi" to "not as much, and unprovable".** Adam Back (April 2026) stresses that 60 to 80% of first-year hashrate was other miners. Bitquery's September 2026 audit gives just under 0.9M BTC under strict rules and about 1.17M under generous ones. Szpili/patoshi-forensics (August 2026) argues the classifier manufactures gaps and undercounts late.
- **Competing counts** range over 21,744, 21,923 (Galaxy), 21,953 (Lopp, this repository), about 22,000 (Arkham) and 22,503 (Whale Alert). **(c)** Galaxy's 21,923 is within one of this audit's 21,922 unspent listed outputs, which suggests "listed minus spent" as a reconciliation. This was not confirmed with Galaxy.
- **Legal and fork actors now depend on these lists.** The "Noah Doe" New York lost-property suit names about 21,923 Patoshi addresses among 39,069, and Paul Sztorc's eCash fork reassigns Patoshi balances on its own chain. Result 1 matters to both: some addresses they treat as Satoshi's are, on ownership evidence, other miners'.
- **Quantum policy.** BIP-360 (P2MR) and BIP-361 (legacy signature sunset) are Drafts, and Hourglass V2 has no number. Every Patoshi output is bare P2PK, so each is exposed and would be frozen or rate-limited under these proposals.
- **Identity work** (the NYT piece on Back, the *Finding Satoshi* film, Peter Miller's conference-gap time-zone argument) mostly does not use the chain rigorously. Miller's gap alignment conflicts with Szpili's finding that many gaps are classifier artefacts.

## 6. How to expand from here (prioritised)

0. **Collect more counterparty documents.** Section 1 of [LINKS.md](LINKS.md) shows that emails from people Satoshi paid are the only evidence tying listed keys to Satoshi *by name*. Other 2009 to 2010 correspondents (for example the unidentified recipients of 10, 1, 1 and 10 BTC at blocks 181, 182, 183 and 248, and whoever held `1H5wBiJ…` and `1PYYjU95…` in May 2010) are the most direct remaining leads.

1. **Complete co-spend census (highest yield).** Extend Result 1 from the 20 first spends to *every* spent coinbase at heights up to 54,619, which needs one BigQuery join. Clustering all early miners by co-spending gives labelled negatives for the whole era: a ground-truth set to measure list precision and recall directly, replacing the extrapolation in Result 4. It also finds every unlisted block swept together with listed ones, not only 14,450. **Prepared, not yet run:** the query, the offline analysis and their tests are in [Phase 5](../phase5/METHODS.md). The analysis reproduces this report's Results 1, 2, 4 and 5 from the census format; one `--execute` run (about 0.58 TB) completes it.
2. **Per-block posterior list.** Combine nonce band, counter-run fit, spacing, and co-spend evidence into a published probability per height instead of a binary list. Report the 12 ownership-contradicted heights and the omission candidates as sensitivity cases. This answers the "19.53% floor" critique with a measured number.
3. **Late-era estimator.** Test Szpili's undercount claim with a mixture model of the nonce band per window (Patoshi 100% in band vs background 19.5%), which needs no counter chains, and compare it with the list's share and the 49,973 endpoint.
4. **Deeper, labelled tracing of the remaining May 2010 path.** Only 19 coinbases remain plausibly Patoshi-spent, and the 100 BTC path now ends at the Faucet ([LINKS.md](LINKS.md)). Tracing the 500 BTC output forward with exchange-cluster labels (for example a WalletExplorer-style Mt. Gox or early-exchange cluster) is the only on-chain route to "where did Patoshi coins go". Any label still identifies a destination, not the source owner.
5. **Dormancy watch.** A small script that, on any movement of a listed outpoint or key hash, classifies the mover using this report's tests (co-spent coinbases, nonce band, counter track, wallet fingerprint). The discourse ledger shows repeated "Satoshi-era wallet moved" false alarms (July 2025, May 2026, September 2026) that such a tool would settle quickly.
6. **Time-of-day with gaps corrected.** Re-run diurnal and "conference gap" tests only on gaps that survive the omission scan, with the permutation nulls from Phase 3. Report nulls as nulls.
7. **Quantum exposure by proposal.** Model per-output outcomes of BIP-361 Phase B, Hourglass V2 (one P2PK spend and 1 BTC per block) and PACTs for the 21,922 unspent outputs, separating the 12 likely non-Patoshi heights.

## Reproduction

```powershell
python scripts/phase4_offline.py cospend sandwich fingerprint signatures
python scripts/phase4_links.py
python scripts/phase4_offline.py manifest
python -m unittest tests.test_phase4
```

The whole phase runs in under a minute (`signatures` takes about 45 s) and reads only committed files. It needs NumPy and `cryptography`. The committed `signature_inputs.csv` is the forensic subset: first spends, listed keys and pre-2011 transactions. The script recomputes the full 88,865-row table in memory for the summary counts.
