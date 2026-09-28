# Patoshi addresses: dataset and independent audit

This repository contains public keys from **21,953 early Bitcoin coinbase outputs** attributed to the hypothesized “Patoshi” miner. It also contains an independent audit of the CSV, its block-list provenance, chain data, spending, and bounded forensic screens. **“Patoshi = Satoshi Nakamoto” is a hypothesis, not an assumption of this audit.** The block list is a published classification, not ground truth about who mined each block.

The chain-data balance watermark is **block 968,902, timestamped 2026-09-27 23:24:41 UTC**. BigQuery queries were separate snapshots, and the 21,922 outputs with no indexed spend were not each checked against a live node at the tip. Later spends or index corrections require a fresh audit.

## Results at a glance

| Work | Result | Evidence and limit |
|---|---|---|
| CSV audit | 21,953 distinct heights, 3–49,973; valid, unique uncompressed secp256k1 keys; four amounts above 50 BTC | [Phase 1](analysis/phase1/REPORT.md); initially CSV-only |
| List provenance | CSV heights exactly equal [Lopp's September 2022 published list](https://github.com/jlopp/bitcoin-utils/blob/45b9eb0f0d71dc7dd66c51fd3058943c1f6df0cb/findPatoshiMiningStreaks.php); bundled extractor contains only 6,183 of them | [Provenance report](analysis/provenance/REPORT.md); list membership does not prove miner attribution |
| Coinbase verification | **21,953/21,953** CSV pubkeys and amounts match indexed coinbase output-zero scripts; zero mismatches | [Phase 2](analysis/phase2_bigquery/REPORT.md); BigQuery, with cryptographic and targeted live checks |
| Coinbase spends | **31 spent outputs / 1,550 BTC**, all spend hits live-confirmed; **21,922 outputs / 1,096,102.49 BTC** have no spend reference through the watermark | [Every status](analysis/phase2_bigquery/spend_status_all.csv); the 21,922 are dataset-bounded, not individually live-confirmed |
| Novelty review | Bounded downstream traces, a P2PKH funding census, reset and boundary analyses; no demonstrated hidden message, hash collision, human schedule, key weakness, or miner identity | [Phase 3](analysis/phase3/REPORT.md); distinguishes replication from possible additions to prior work |
| Debian OpenSSL screen | **0 matches / 7,339,808 modeled keygen slots**, after reproducing nine published weak-key vectors | [Follow-up](analysis/phase3/debian/REPORT.md); PID/startup/offset window only, not an exhaustive Debian-weak-key exclusion |
| Spending graph vs list | **12 of the 31 spent listed coinbases (600 BTC) were swept with 10 to 202 unlisted coinbases each**; 8 sit on the sweeping miner's own counter track (7 of 11 sweeps; p = 8 × 10⁻⁸, conservative 4.5 × 10⁻⁵). Implied list inclusion rate for other miners' blocks: 0.33% (CI 0.02% to 1.35%). Block 14,450 is an omission candidate on two independent lines | [Phase 4](analysis/phase4/REPORT.md); common-input ownership is a heuristic |
| Signatures and wallets | **71,407/71,407** verifiable trace signatures verify; no R reuse or small nonces; January 2009 spends match the original client's change logic; 2016 and 2017 sweeps use modern wallet behaviour | [Phase 4](analysis/phase4/REPORT.md); bounded to traced transactions |
| Satoshi-linked identifiers | All five counterparty-documented Satoshi payments (Finney, Trammell, Bohm, Hearn) spend listed coinbases in Patoshi-only clusters; **the May 2010 100 BTC went to Gavin Andresen's Faucet on 2010-07-11**; blocks 1 and 2 fit the pattern | [Links](analysis/phase4/LINKS.md); 98 sourced identifiers |
| Co-spend census | **27,898 of 54,620 early coinbases spent; 22,959 blocks in the list's span owned by other miners by co-spending, only 12 of them listed**: list false-positive rate 0.052% (CI 0.024% to 0.087%), about 15 false-positive heights, precision 99.93%. Omissions at most 1,144, estimated about 188 (recall about 99.1%). About 353 Patoshi-like blocks after 49,973, ending near 54,470 | [Phase 5](analysis/phase5/REPORT.md); ownership labels use only co-spent siblings' nonces, never the list |
| Public discourse | Critiques, competing counts (21,744 to 22,503), BIP-360/361 and Hourglass, the "Noah Doe" lawsuit, the eCash fork, identity claims | [Ledger](analysis/phase4/DISCOURSE.md); as reported, mostly not re-verified |

Labels in the reports distinguish **(a) verified observations**, **(b) statistical or model inferences with stated tests**, and **(c) speculation**. BigQuery is a secondary chain index; each report says which material findings were also checked through a live API. An unlisted block is an *unlisted control*, not a proven different miner.

## What the dataset contains

[`patoshi_pubkeys_COMPLETE.csv`](patoshi_pubkeys_COMPLETE.csv) has `Block Height`, `Output Index`, `Address/Pubkey`, `Amount (BTC)`, and `Script Type`. All 21,953 listed outputs are **output zero, pay-to-public-key (P2PK)**. The `Address/Pubkey` field is an uncompressed `04…` public key, not a P2PKH address. The four fee-inclusive coinbases are:

| Height | Coinbase amount |
|---:|---:|
| 2,817 | 52.01 BTC |
| 19,863 | 50.14 BTC |
| 23,079 | 50.12 BTC |
| 28,507 | 50.22 BTC |

The other 21,949 rows are 50 BTC, giving **1,097,652.49 BTC** in the CSV. The four amounts were reproduced from the chain in the BigQuery smoke and full runs. [`patoshi_p2pkh_addresses.csv`](patoshi_p2pkh_addresses.csv) contains Base58Check P2PKH encodings derived from the same public keys. These are useful for looking up payments to the key hashes, but **spending the original coinbases is determined by their P2PK outpoints**, not by activity at the derived addresses.

## How the audit developed

### 1. Offline structural and key audit

[Phase 1](analysis/phase1/REPORT.md) inspected every CSV row before network retrieval. It checked height and key validity, duplicates, amounts, key-byte distributions, gaps and vanity patterns, then derived the address list. There are **28,018 unlisted heights in 8,899 intervals** within the height range; the longest interval is **426 heights**. Global and height-local permutation tests found structured gap behavior. No pubkey-byte anomaly survived correction across 765 tests, and the short vanity-like strings, including block 264's `1CFB…` address, were not convincing evidence of intentional vanity mining. These are tests of the supplied list and keys, not tests of the miner's identity or the security of every possible key generator.

### 2. Provenance of the 21,953-height list

The [provenance comparison](analysis/provenance/REPORT.md) found that the CSV's heights equal Lopp's 2022 list and the later [`TaintedBySatoshi` array](https://github.com/tehran19r/TaintedBySatoshi/blob/f013a619c7faa5db44de2e55b3423de48edef336/backend/src/data/patoshiBlocks.js), including order. The latter explicitly cites the `bensig/patoshi-addresses` source. The bundled [`extract_patoshi_addresses.py`](extract_patoshi_addresses.py) lists **6,183 heights, all present in the CSV**, leaving **15,770 CSV-only heights**. It preserves the first 6,157 CSV entries through height 8,044, then becomes sparse; it cannot reproduce the shipped full CSV. Its default output filename also differs. No evidence establishes who populated the extra CSV rows or which extractor produced them. The chain verification below independently checked their pubkeys and amounts.

The declared analysis population is the [pinned Lopp height file](analysis/provenance/lopp_patoshi_heights.txt). The older extractor remains as an artifact of the repository's history; running it does **not** regenerate `patoshi_pubkeys_COMPLETE.csv`.

### 3. Chain verification, spending and classifier checks

[Phase 2](analysis/phase2_bigquery/REPORT.md) first inspected the actual `bigquery-public-data.crypto_bitcoin` schema and passed a ten-block smoke test, including the 52.01 BTC control. One bulk coinbase comparison then matched **all 21,953 complete P2PK scripts and amounts**. All queried coinbase transaction IDs were reconstructed; 54,620 consecutive block headers and their proof of work were checked. For **21,775** listed single-transaction blocks, the header Merkle root also directly binds the reconstructed coinbase. The remaining **178 multi-transaction blocks** have matching indexed outputs but no exhaustive independent Merkle-proof audit.

A whole-input-index outpoint join found **31 spent coinbases**, each checked live through [mempool.space](https://mempool.space/docs/api/rest). The earliest is block 9's coinbase, spent at block 170; the latest listed spend occurred in December 2017. The count agrees with [Bitquery's September 2026 audit](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth), so the spend count is a verification, not a newly discovered movement. The other 21,922 have no spend reference through the stated BigQuery watermark. Query CSVs, SQL, metadata, spend statuses, live-check receipts and a [checksummed manifest](analysis/phase2_bigquery/manifest.json) are committed; full API/REST envelopes remain in ignored local cache.

The same chain data were used to reproduce broad nonce-LSB and extraNonce *signatures*, not Lerner's original labeling process. All 21,953 listed blocks meet the broad nonce rule, but so do **602/3,000 unlisted controls**. The extraNonce consistency model accepts **4,075/4,290 evaluable held-out listed blocks** and **13/2,735 evaluable unlisted controls**. Its **1,005 review flags are not 1,005 proven misclassifications**. Block **37,808** alone fails Lerner's tighter 2020 nonce bound and remains a disputed attribution. Ten sampled unlisted blocks near the endpoint pass the local screening rules; none is promoted to a verified omission. No significant UTC hour or weekday pattern survived the specified temporal tests. [Methods, controls and limits](analysis/phase2_bigquery/METHODS.md).

### 4. Novelty hunt and bounded null screens

[Phase 3](analysis/phase3/REPORT.md) compared candidate findings with [Lerner's work](https://bitslog.com/2013/04/17/the-well-deserved-fortune-of-satoshi-nakamoto/), [BitMEX Research](https://web.archive.org/web/20241223083952/https://blog.bitmex.com/satoshis-1-million-bitcoin/), [Lopp](https://blog.lopp.net/was-satoshi-a-greedy-miner/) and [Bitquery](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth). The [literature ledger](analysis/phase3/SOURCES.md) records what was already published. Search absence cannot prove universal novelty.

- **Downstream trace:** the 31 spent coinbases enter 20 first-spending transactions. Three further generations yielded 1,259 reconstructed transaction IDs and 1,474 explicit outpoint edges. A May 2010 **100 BTC** path has verified later 95/5 and 5/90 BTC splits; the related **500 BTC** path joins a previously discussed 9,000 BTC consolidation. Tracing stops at a documented frontier. Output-to-output “taint” allocations are heuristics, not ownership or physical coin tracking.
- **Additional P2PKH funding:** exact script matching found 82,151 historical P2PKH outputs to 21,926 derived key hashes. At the watermark, 82,149 outputs totaling **7.05258112 BTC** had no spend reference. This is distinct from the original P2PK coinbase balance. The two spent P2PKH hits revealed the expected public keys, not a collision.
- **Counter and boundary review:** filtered extraNonce decreases produce an approximately several-day reset-candidate cadence, but a decrease is not proof of a reboot or backup. No reset-hour or weekday scheduling signal survived permutation testing. A separate multi-track classifier supported **41 of the 50 largest Phase 2 residual flags**; nine remain unresolved. Its recall is too low to replace the published block list. Candidate blocks around 49,973 and block 37,808 remain attribution questions.
- **Key and coinbase screens:** no match in the stated small/structured private-key classes or the pinned Milk Sad address corpus; no internal HASH160 duplicate; no tested 100-position key-order artifact; no extra coinbase message bytes or nonstandard script layout. These are bounded nulls. The stock client's 100-key pool was introduced after this block range, so a 100-reward refill premise is unsupported.
- **Public-key exposure:** the 21,922 original outputs with no indexed spend expose **1,096,102.49 BTC** in P2PK public keys. This is a conditional future quantum-risk measurement, not a demonstrated present-day key recovery. The report records a **September 28, 2026** BTC/USD quote for a historical snapshot; it is not a live valuation.

The later [Debian OpenSSL CVE-2008-0166 follow-up](analysis/phase3/debian/REPORT.md) searched published weak-key corpora, modeled the historical PRNG from source, reproduced **nine published P-256 weak keys**, then checked **7,339,808 secp256k1 candidate keygen slots** against all CSV pubkeys with **zero matches**. It covers PIDs 1–32,767, little/big-endian paths and the first 16 consecutive modeled keygens across specified startup states. PID 0 or raised PID limits, deeper offsets, other preceding RNG calls and other process histories remain untested. This null does not show that the actual miner used Debian or that every vulnerable key was excluded.

### 5. Spending graph, signatures and public discourse

[Phase 4](analysis/phase4/REPORT.md) turns the spending graph back on the list. Using only committed data, it splits the 20 first-spending transactions by their other inputs. Eleven of them, from 2010 to 2017, sweep one or two listed coinbases together with **568 unlisted coinbases** that pass Lerner's nonce band at the 21.7% chance rate of an ordinary miner. In 8 of those 12 listed cases, the listed block sits exactly on the sweeping miner's own extraNonce track: for example, unlisted 2,575 (649) → listed **2,577** (651) → unlisted 2,581 (655). Common-input ownership therefore says the headline "31 spent Patoshi coinbases" overstates Patoshi spending. **19 coinbases / 950 BTC** remain in Patoshi-only or Patoshi-majority spends. The same sweeps give a model-based list inclusion rate of **0.33%** for other miners' blocks, far below the 19.53% nonce-byte "floor" cited publicly. In the other direction, unlisted block **14,450** was spent with nine listed coinbases in May 2010 and fits the listed counter run 12 → 14 → 28. A full scan of all unlisted heights finds fits in 17 anchor windows against 15.3 expected by chance, so the list is close to complete for short runs. A five-block run at 27,474 to 27,478 is suggestive but not established once correlated counters are allowed for. All 71,407 verifiable signatures in the trace verify, with no nonce reuse. Primary-source identifiers support the split: every payment that Hal Finney, Dustin Trammell, Nicholas Bohm or Mike Hearn documented as coming from Satoshi spends listed coinbases in Patoshi-only clusters. On 2010-07-11 the May 2010 100 BTC went to [Gavin Andresen's Faucet donation address](https://satoshi.nakamotoinstitute.org/posts/bitcointalk/threads/88/) and was paid out 5 BTC at a time. The report also contains a [public discourse ledger](analysis/phase4/DISCOURSE.md), a [cross-reference of Satoshi-linked identifiers](analysis/phase4/LINKS.md) and a prioritised plan for extending this work.

### 6. Complete co-spend census

[Phase 5](analysis/phase5/REPORT.md) ran one BigQuery query over every coinbase at heights 0 to 54,619 and every transaction that spent one: 0.576 TB, 2,644 transactions, 27,898 spent coinbases. Each block's owner was labelled only from the nonce band of the *other* blocks spent with it, so the list and the block's own nonce never vote. Other miners' blocks, identified that way, pass the nonce band at 19.61%, the chance rate. Of **22,959 blocks in the list's span owned by other miners, 12 are listed**: a measured false-positive rate of **0.052%** (CI 0.024% to 0.087%), about 15 heights, or **99.93% precision**. This replaces Phase 4's model-based 0.33%. Omissions are bounded because an omitted Patoshi block must pass the band and cannot have been swept by another miner. At most 1,144 unlisted heights qualify, and the excess over chance implies about 188 omitted blocks (recall about 99.1%), mostly at 25,000 to 29,999. The late-era undercount claimed at 40,000 to 44,999 finds about 8 there. Past the list's end, about **353 Patoshi-like blocks** appear between roughly 50,974 and 54,470, in line with public extensions of the pattern. Those are aggregate estimates, not named blocks.

## Files and reproduction

| Area | Primary files |
|---|---|
| Dataset and derived encodings | [coinbase CSV](patoshi_pubkeys_COMPLETE.csv), [P2PKH list](patoshi_p2pkh_addresses.csv) |
| Offline audit | [report](analysis/phase1/REPORT.md), [script](scripts/phase1_offline.py), [results](analysis/phase1/results.json) |
| Provenance | [report](analysis/provenance/REPORT.md), [comparison script](scripts/provenance_compare.py), [pinned heights](analysis/provenance/lopp_patoshi_heights.txt) |
| Chain verification | [report](analysis/phase2_bigquery/REPORT.md), [methods](analysis/phase2_bigquery/METHODS.md), [SQL](analysis/phase2_bigquery/sql/), [all spend statuses](analysis/phase2_bigquery/spend_status_all.csv) |
| Novelty work | [report](analysis/phase3/REPORT.md), [methods](analysis/phase3/METHODS.md), [source ledger](analysis/phase3/SOURCES.md), [cached query CSVs](analysis/phase3/results/) |
| Debian screen | [report](analysis/phase3/debian/REPORT.md), [model/screen](scripts/debian_weak_screen.py), [result](analysis/phase3/debian/result.json), [checksums](analysis/phase3/debian/manifest.json) |
| Phase 4 | [report](analysis/phase4/REPORT.md), [script](scripts/phase4_offline.py), [co-spend clusters](analysis/phase4/cospend_clusters.csv), [omission scan](analysis/phase4/sandwich_candidates.csv), [discourse](analysis/phase4/DISCOURSE.md), [identifier links](analysis/phase4/LINKS.md), [checksums](analysis/phase4/manifest.json) |
| Phase 5 | [report](analysis/phase5/REPORT.md), [methods](analysis/phase5/METHODS.md), [census SQL](analysis/phase5/sql/cospend_census.sql), [query result](analysis/phase5/results/cospend_census.csv), [every block's label](analysis/phase5/census_blocks.csv), [eras](analysis/phase5/census_eras.csv), [checksums](analysis/phase5/manifest.json) |

Install the [analysis dependencies](requirements-analysis.txt) in a Python environment. Offline Phase 1, the committed provenance comparison and all of Phase 4 (`python scripts/phase4_offline.py cospend sandwich fingerprint signatures`, then `python scripts/phase4_links.py` for the identifier cross-reference, then `python scripts/phase4_offline.py manifest`) can be reproduced without cloud credentials:

```powershell
python scripts/phase1_offline.py --permutations 1999
python scripts/provenance_compare.py --source lopp=analysis/provenance/sources/lopp_streaks_2022.php --source tehran=analysis/provenance/sources/tehran_patoshiBlocks_initial.js
```

The Phase 5 co-spend census reruns offline from its committed query result with `python scripts/phase5_offline.py census manifest`; repeating the query (`python scripts/phase5_bigquery.py census`, dry run first, then `--execute`) needs BigQuery credentials. See its [methods](analysis/phase5/METHODS.md).

For Phase 2, the committed [query results](analysis/phase2_bigquery/results/) and [methods](analysis/phase2_bigquery/METHODS.md) preserve the schema, SQL, query identities, output comparisons, spend statuses and watermark. Repeating the **BigQuery collection** requires Google application-default credentials and may process substantial data; a matching completed query reuses its committed CSV. Phase 3 offline reanalysis and its separately cached sources are documented in [Phase 3 methods](analysis/phase3/METHODS.md). The Debian report includes the four commands to validate vectors, rerun the bounded screen, aggregate and checksum it; the full screen is computationally expensive.

Ignored local caches contain raw BigQuery and live API responses, source downloads and progress files. A fresh clone has the committed result CSVs and receipts, but not every raw response envelope or external source archive. This distinction is recorded in the manifests and methods. The earlier per-block API collector was stopped when BigQuery became the bulk source; its files remain for audit history.

## Credits and interpretation

[Sergio Demian Lerner](https://bitslog.com/2013/04/17/the-well-deserved-fortune-of-satoshi-nakamoto/) identified the Patoshi patterns; [Jameson Lopp](https://blog.lopp.net/was-satoshi-a-greedy-miner/) published the height list used here. This audit checks that list's artifacts and chain consequences. It does not establish that every listed block came from one miner, that the miner was Satoshi, that observed spending identifies a person, or that an unlisted block cannot share the same mining pattern.
