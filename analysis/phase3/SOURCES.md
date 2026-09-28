# Literature and novelty ledger

Every substantive conclusion in REPORT.md links its evidence. This ledger records the scope of prior art actually reviewed. Cached documents and search results are in `.firecrawl/`; raw structured sources are in `analysis/phase3/cache/`. Their checksums appear in `manifest.json`.

| Source | What it already establishes; consequence for novelty |
|---|---|
| [Lerner, April17 2013](https://bitslog.com/2013/04/17/the-well-deserved-fortune-of-satoshi-nakamoto/) and [April24 refinement](https://bitslog.com/2013/04/24/satoshi-s-fortune-a-more-accurate-figure/) | ExtraNonce slope attribution and spent/unspent comparisons are old findings. Manual masking uncertainty is explicit. |
| [Lerner, September3 2013](https://bitslog.com/2013/09/03/new-mystery-about-satoshi/) | Nonce-byte anomaly predates this audit. |
| [Lerner, April2019](https://bitslog.com/2019/04/16/the-return-of-the-deniers-and-the-revenge-of-patoshi/) | Restricted LSB ranges, counter behavior and a roughly ten-day interruption are published. |
| [Lerner, June2020](https://bitslog.com/2020/06/22/a-new-mystery-in-patoshi-timestamps/) | Timestamp regularity and mining delays are published. |
| [Lerner, August2020](https://bitslog.com/2020/08/22/the-patoshi-mining-machine/) | Inner-nonce bounds and mining-machine hypotheses are published; this supplies the tight rule, not an unquestionable attribution oracle. |
| [BitMEX, August2018, archived original](https://web.archive.org/web/20241223083952/https://blog.bitmex.com/satoshis-1-million-bitcoin/) | Slopes overlap; allocations weaken in later months; numerical totals depend on judgment. Both current article URLs returned404, so the archived original was read. |
| [Lopp, September2022](https://blog.lopp.net/was-satoshi-a-greedy-miner/) | Timing, mining streaks and throttling are prior work. Uses an identity assumption which this audit does not adopt. |
| [Bitquery, September2026](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth), [per-block data](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth/patoshi-audit-dataset.csv), [method log](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth/method-changelog.md) | Published spend count, May transactions, counter cadence, grades and exclusions. Seven supplied boundary candidates are already positive at low confidence;37,808 is excluded. Methods acknowledge substantial candidate false positives and deferred deeper tracing. |
| [Keypool announcement, October2010](https://bitcointalk.org/index.php?topic=1414.0), [release0.3.14](https://bitcointalk.org/index.php?topic=1528.0), [original client source](https://github.com/blaesus/bitcoin-0.0.1/blob/master/src/main.cpp) | Corrects the 100-key-pool premise for this earlier block range. |
| [Debian advisory](https://www.debian.org/security/2008/dsa-1571), [badkeys Debian coverage](https://badkeys.info/docs/debian.html) | Historical flaw and coverage limits. P-256/P-384 datasets cannot be treated as secp256k1 screening. |
| [Milk Sad research](https://milksad.info/), [pinned corpus](https://git.distrust.co/milksad/data/src/commit/81d1eb74585403e0042f9d507089ee4660a18502) | Published weak-wallet address corpus. Its intersection is a new audit result; the vulnerabilities themselves are established. |
| [btc-rpc-explorer discussion465](https://github.com/janoside/btc-rpc-explorer/discussions/465) | Both 10,000-satoshi P2PKH spends and concerns about35,573/35,599 are already public. |
| [November2023 tracing discussion](https://bitcointalk.org/index.php?topic=5473726.20) | The 9,000 BTC consolidation appears explicitly; disqualifies its discovery as novel here. A linked/indexed [archaeology thesis](https://skemman.is/bitstream/1946/42021/1/Blockchain%20network%20analysis%20-%20Steindor%20Gudmundsson.pdf) was CAPTCHA-blocked; its body was not read or used to support a factual conclusion. |
| [June2022 forum transaction export](https://bitcointalk.org/index.php?topic=5402488.msg60403902#msg60403902) | Contains the May100 BTC txid and destination. Wallet-export local time is not treated as UTC chain time. |
| [ChainQuery quantum exposure](https://chainquery.com/reports/quantum-exposure), [Shor's algorithm](https://arxiv.org/abs/quant-ph/9508027) | Exposed-key vulnerability is established, conditional on a suitable quantum computer. Exact scoped balances are measurements, not discovery of quantum risk. |
| [Coinbase spot endpoint](https://api.coinbase.com/v2/prices/BTC-USD/spot) | Timestamped BTC/USD conversion, not a historical price at the chain watermark. |

## Search scope and dead ends

Searches covered Patoshi keypool/reset timing, Debian/secp256k1 corpora, Milk Sad data, P2PKH funding/quantum exposure, overlapping slopes, and exact May-path transaction IDs and addresses. Exact `f81569…` found prior discussion; exact `a3a9e5…` and a grouped prefix search for the 100 BTC successors returned no results. These absences constrain wording; they do not prove global novelty.

Current BitMEX URLs and an initially guessed badkeys blocklist documentation URL failed; archive/actual documentation resolved them. The archaeology thesis remained blocked. Searches also surfaced secondary entity/identity claims; no independently substantiated entity label was acquired, and those claims are not adopted. No applicable complete Debian secp256k1 list was found. No email, forum post or third-party message was sent.
