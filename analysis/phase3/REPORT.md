# Phase 3 — novelty hunt

Completed 2026-09-28 UTC (September 27 local time). Population: the unchanged 21,953-height list. **No demonstrated cryptographic weakness, hidden message, new miner identity, or defensible new block attribution was found.** The useful additions are a bounded downstream trace, a precise funding census, and a diagnosis of the earlier classifier's flags. None is claimed to be the first observation anywhere in the world.

Labels throughout: **(a)** verified data/fact, with BigQuery-only census results identified; **(b)** statistical or model inference; **(c)** speculation. “Patoshi = Satoshi” is not assumed. The balance watermark remains **968,902 / 2026-09-27 23:24:41 UTC**. A later query with a height ceiling is not an atomic historical database snapshot.

## Ranked additions to the reviewed literature

### 1. The 100 BTC May transfer: a documented downstream split

**Novelty: moderate, provisional. Confidence: high in the transaction edges; none in identity attribution.**

**(a; all seven May-path successor transactions live-confirmed)** The May 17, 2010, 100 BTC transfer follows this path:

| UTC date | Transaction | Verified inputs → outputs |
|---|---|---|
| May 17 | [028ad2…](https://mempool.space/tx/028ad2c836163295e4723a49dd418ee8fb55a14613b1186675f01124b60fb763) | Two coinbases → 100 BTC |
| July 11, 22:33:11 | [c7d4fd…](https://mempool.space/tx/c7d4fd1b42881d8968949ece19085f432b7bc5b68ed2d3c6723b349fb87f055f) | That output alone → 100 BTC |
| July 11, 22:53:58 | [a3a9e5…](https://mempool.space/tx/a3a9e58a1cec7679216bd1f59562c5a20f1b58946bb68a31080828422287ea9d) | That output alone → 95 + 5 BTC |
| Same block 65,543 | [38f20c…](https://mempool.space/tx/38f20c967fba99dcaed706ccb92a162594fea185dc11e76cf4b1fb53660e6715) | The 95 BTC output alone → 5 + 90 BTC |
| September 4, 2011 | [b08431…](https://mempool.space/tx/b08431960b09af8dd83073c99304f7ae5efd3153c4d35f90a5701f8ca6ea60be) | The first 5 BTC output + another 4.708 BTC → 0.63994596 + 9.06805404 BTC |

**Novelty statement.** [Bitquery](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth) describes the original transfer and its July movement, but explicitly stops its trace at the first hop. Exact and prefix transaction searches did not locate a prior narrative of these subsequent 95/5 and 5/90 splits. The addition is these precise later edges, not discovery of the original transfer. That original txid also appears in a [June 2022 forum post](https://bitcointalk.org/index.php?topic=5402488.msg60403902#msg60403902), which is another reason not to call it new. Search absence cannot establish universal novelty.

**Limitations.** These single-input transitions preserve an explicit outpoint path. They establish neither a payment purpose nor the same owner across outputs. At the 2011 two-input transaction, allocation among outputs becomes heuristic. No substantiated exchange/entity label was obtained. No identity conclusion follows from 5 BTC denominations. [Every May edge and output](may2010_paths.csv).

### 2. A precise census of additional funds sent to the exposed key hashes

**Novelty: modest quantitative extension. Confidence: high within the indexed dataset, with live samples.**

**(a; BigQuery census)** Exact P2PKH script matching across the chain found **82,151 historical outputs** to **21,926** of the derived key hashes, in **23,311 transactions**. At the watermark, **82,149 outputs / 21,924 key hashes**, totaling **7.05258112 BTC**, have no spend reference. These are additional P2PKH outputs, distinct from the original P2PK coinbases. Seventeen selected funding outpoints, including large outputs and both spent hits, received live checks.

**(a)** The only two spent P2PKH matches are 10,000 satoshis each, associated with listed heights **35,573 and 35,599**. Both reveal exactly the expected original public key; neither is a hash collision. **No internal hash160 duplicate or different-public-key/same-hash example was found.** For unspent P2PKH outputs the spender's key is unobserved, so matching an address cannot demonstrate a collision or rule out an unknown second preimage.

**Novelty statement.** P2PKH donations and these two spends were explicitly discussed in [btc-rpc-explorer discussion 465](https://github.com/janoside/btc-rpc-explorer/discussions/465). General exposure of reused/revealed keys is also documented by [ChainQuery](https://chainquery.com/reports/quantum-exposure). The addition here is the exact, reproducible census for this pinned list and watermark. It is not a new vulnerability or evidence of activity by the key owner. [Per-key funding](funding_by_keyhash.csv), [full query result](results/funded_keyhashes.csv), [summary](funding_summary.json).

### 3. The largest Phase 2 flags mostly diagnose interpolation failure

**Novelty: specific to this audit's method. Confidence: high in the diagnostic, limited in miner attribution.**

**(a)** All **50 largest scaled-residual flags** span an extraNonce decrease between their original anchors. Forty-nine are at heights 1,460–1,891; one is 46,776. This is not a set of “highest-confidence misclassifications”: residual magnitude was never calibrated to attribution confidence.

**(b)** A separately implemented multi-track RANSAC classifier, using nonce-eligible blocks rather than the published labels as training positives, supports **41/50** on counter tracks. All 50 targets were excluded from fitting. Nine remain unresolved. Example: height **1,756**, counter **898**, was compared in Phase 2 with counters **946 and 948** at heights 1,755 and 1,757; the separate track's residual is **−12.78**, within the fixed ±15 tolerance. This supports retaining it as a candidate, not removing it because of the original interpolation result.

**Novelty statement.** Overlapping slopes and uncertainty are already central to [BitMEX's 2018 analysis](https://web.archive.org/web/20241223083952/https://blog.bitmex.com/satoshis-1-million-bitcoin/) and [Bitquery's methods](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth/method-changelog.md). The new result is the diagnosis of our specific 50 flags, not discovery of overlapping miners or a superior attribution list.

**Limitations.** The fixed model accepts only **2,537/4,379 held-out listed blocks**; 3,282 have bracketed model support. It is too conservative/incomplete to replace the pinned list. Ten of 3,000 unlisted controls pass, but some controls participated in fitting, so this is not a held-out false-positive estimate. No parameters were retuned to improve these results. [Per-block adjudication and supporting anchors](top50_slope_adjudication.csv), [all line fits](slope_lines.csv), [design](METHODS.md).

## Confirmed, not novel

### Quantum exposure

**(a; dataset-bounded accounting)** **21,922 original unspent P2PK outputs / 1,096,102.49 BTC** expose their public keys. At the cached [Coinbase BTC/USD spot quote](https://api.coinbase.com/v2/prices/BTC-USD/spot), **$84,472.06** observed **2026-09-28 00:01:45 UTC**, this is **$92,590,035,301.43**. The additional P2PKH census above also refers to already public keys. The balance date and price observation time are different.

**(b)** “Shor-vulnerable” is conditional on a sufficiently capable fault-tolerant quantum computer: exposed keys allow the discrete-log attack described by [Shor](https://arxiv.org/abs/quant-ph/9508027). This is not a demonstrated present-day key recovery, loss forecast, or novel vulnerability. [Exact arithmetic and quote receipt](quantum_exposure.json).

### All 31 first spends, plus three downstream generations

**(a)** The 31 coinbases enter **20 first-spending transactions**. We collected three further generations across every branch, reconstructing **1,259 transaction IDs** and **1,474 explicit outpoint edges**, including edges discovered where fetched branches converge. The final generation contains **1,033 transactions** whose remaining outputs were not exhaustively followed. The trace is bounded, not an ultimate-destination census.

**(a; live-confirmed May path)** The 500 BTC May output passes through `56e3e3…`, joins a **9,000 BTC / 11-input consolidation** `f81569…` on June 9, and then enters `064bc0…`, producing **8,000 and 1,000 BTC**. The 9,000 BTC transaction was already [discussed in November 2023](https://bitcointalk.org/index.php?topic=5473726.20); search also identified a thesis containing it, whose full PDF was CAPTCHA-blocked. This line produced replication, not a novel discovery.

**(a)** The 500 BTC branch contains **450 BTC from the pinned population**, plus one 50 BTC coinbase outside it; the 100 BTC branch contains two listed coinbases. The proportional model injects only the pinned 1,550 BTC, not all funds in transactions that happen to spend them.

**(b)** A proportional allocation model conserves the original 1,550 BTC across outputs and fees. Approximately **216.05982206 BTC** of that *modeled allocation* reaches outputs with no spend reference; **1,333.91770007 BTC** reaches the unqueried frontier; **0.02247787 BTC** is allocated to fees. These are not physically identifiable satoshis, current balances, or owner holdings. The same-block ordering and branch-convergence checks prevent double counting. [Edges](trace_edges.csv), [output-by-output model](trace_outputs.csv), [assumptions](trace_summary.json).

### Boundary cases and 37,808

**(a)** All ten supplied candidates are **below 49,973**. Seven—49,875; 49,878; 49,880; 49,905; 49,918; 49,919; 49,933—already occur in Bitquery's published low-confidence set. The other three do not. All ten pass the tighter nonce bounds, and their timestamps lie between their neighboring listed blocks.

**(b)** They do not form one uninterrupted increasing counter sequence: the ordered extraNonces include **76 → 43 → 9** and **251 → 219 → 160**. Only four listed points support the nearby monotone run. Neighbor interpolation residuals vary from approximately −87 to +82; a wider fit crosses resets and is not reliable. Neither local continuity nor the new fixed slope model supports promoting these to verified omissions. The latter admits no block after 49,973 through its examined endpoint 54,619; its low recall makes that a model null, not proof that mining ended there. Among the first 300 post-list blocks, Bitquery already flags 38 at low confidence. [Full per-block comparison](boundary_deep_dive.csv).

**(a/b), best case for 37,808:** its timestamp lies between 37,804 and 37,809; counters are **146 → 152 → 166**. Nearest-time interpolation misses by only **−8.36**, and a reset-clipped 24-neighbor fit by **−11.60**. It passes the original nonce-LSB rule. **Best case against:** its reversed nonce **986,001,416** is **2,961,416 above** the [2020 upper bound](https://bitslog.com/2020/08/22/the-patoshi-mining-machine/), and Bitquery independently excludes it. Its eventual spend is not a logically independent disqualifier. Verdict: disputed attribution; retain the pinned population for reproducibility, report strict-nonce exclusion in sensitivity analyses. No new definitive classification is claimed.

## Checked and empty

| Screen | Result and exact scope |
|---|---|
| **(a)** Small/structured key classes | Zero matches across 21,953 keys against scalars **1…2²⁰**, **n−2²⁰…n−1**, and **766** valid structured scalars: powers of two, order minus powers of two, repeated-byte values. Only class/height would be emitted on a hit; no spending operations. |
| **(a)** Published weak-wallet corpus | Zero matches against **314,781 distinct Bitcoin addresses in 45 files**, pinned Milk Sad data commit `81d1eb74585403e0042f9d507089ee4660a18502`. Compared **87,812 encodings**: uncompressed/compressed P2PKH, compressed P2WPKH, and nested P2WPKH. This is a corpus intersection, not exhaustive coverage of those vulnerable generators. [Corpus source](https://git.distrust.co/milksad/data), [file checksums](corpus_files.csv). |
| **(a)** Debian OpenSSL CVE-2008-0166 | A later, source-grounded screen found zero matches in **7,339,808 modeled secp256k1 keygen slots**: PID 1–32,767, three validated native-width/endian architectures plus synthetic 64-bit big endian, four startup modes where validated, first 16 consecutive keygens. This is a bounded null, **not exhaustive coverage of vulnerable process histories**. The model reproduced nine published weak P-256 keys before screening. [Exact method and untested remainder](debian/REPORT.md). |
| **(b)** Key ordering / batches | Thirteen permutation tests: 100-position phase means and lags 1, 99, 100, 101 of leading X/Y/hash160 bytes. All Holm-adjusted p-values **1.0**, 1,999 permutations. This tests those features, not every possible dependency. |
| **(a)** Hash collisions | Zero internal duplicate hash160 values; both externally spent matching P2PKH scripts revealed the expected pubkeys. Unspent matches alone are not collisions. |
| **(b)** Reset scheduling | No hour/weekday signal under any of three definitions, 4,999 permutations, six-test Holm adjustment: all adjusted p-values **1.0**. Moderate-filter hour p=.5432, weekday p=.7852. [Tests](session_summary.json). |
| **(a)** Coinbase messages/encoding | Every script has exactly **two direct pushes**: matching difficulty bits and a minimally encoded nonnegative counter. **1,549 seven-byte scripts; 20,404 eight-byte scripts**. No trailing bytes, extra fields, difficulty mismatch, or encoding anomaly. Printable counter bytes are not evidence of messages. [Every script](coinbase_encoding.csv). |

**(a), important correction:** the stock client's 100-key pool was introduced in **October 2010**, after this population's last block. The [original announcement](https://bitcointalk.org/index.php?topic=1414.0) describes a replenished queue, not necessarily isolated batches of 100 mined rewards. The [v0.0.1 source](https://github.com/blaesus/bitcoin-0.0.1/blob/master/src/main.cpp) generates a key when mining starts and another after finding a block. **(c)** A private custom implementation could differ, but there is no evidence here of its keypool architecture. No on-chain refill boundaries can be directly measured.

**(a/b), reset detail:** 286 raw decreases shrink to **100 moderate / 64 conservative reset candidates** when requiring a low destination, a substantial fall, and five monotone observations on either side. Moderate inter-event median **4.29696 days**, **32/99** intervals in 4–6 days; conservative median **5.68625 days**, **26/63** in that interval. Only **one inter-listed observation gap** actually lasts 4–6 days: 20,342→20,442, **5.39406 days**. **181/286 raw decreases occur before height 2,000**, demonstrating why treating every decline as a reboot is unsafe. The moderate median observation bracket is **82.16 minutes**. Bitquery's few-day cadence is supported descriptively, but a backup purpose remains **(c)** speculation. The new scheduling test is a null, not a new human schedule.

## Open questions and what would settle them

- **Debian OpenSSL beyond the bounded screen?** The [2008 advisory](https://www.debian.org/security/2008/dsa-1571) concerns a specific vulnerable implementation. The [follow-up screen](debian/REPORT.md) closes the first-16-keygen, standard-PID, modeled-startup window with a null, but raised PIDs, deeper offsets, arbitrary earlier RNG calls, other process histories and unvalidated architectures remain. An independently preserved vulnerable miner build or comprehensive process-state corpus would narrow that remainder; a public key does not encode its generation date.
- **Unpublished everywhere?** Unsettled. The novelty review covers the sources in [SOURCES.md](SOURCES.md) and recorded searches, not private research or every historical forum. A prior description of the 100 BTC split would move finding 1 to confirmed-not-novel.
- **Exchanges or ultimate destinations?** No defensible entity attribution from the acquired evidence. An authenticated label source, independent corroboration and additional explicitly bounded tracing would be required. A payment into a labeled entity would still not identify the source owner.
- **Classifier truth?** Nine top-50 flags remain unresolved; the other 955 were not individually adjudicated. A validated model with independent positive/negative examples is needed before changing the block list. Passing a counter-track model is not ground truth.

[Methods and reproduction](METHODS.md) · [Source review](SOURCES.md) · [Checksummed manifest](manifest.json).
