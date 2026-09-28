# Satoshi-linked identifiers vs the dataset

This file answers one question: which transactions that people *documented* as Satoshi's touch the Patoshi list, and what do they say about Phase 4's co-spend split?

- **Inputs.** The [identifier table](satoshi_linked_identifiers.csv) has 98 identifiers (33 txids, 31 addresses, 21 pubkeys, 13 heights). Each carries a source URL and an evidence label, and [notes](satoshi_linked_identifiers.md) record how they were compiled. Every value was copied from a fetched source: an email archive, a forum post, a participant's blog, or an explorer response. Pubkeys placed in the CSV match it byte for byte. The 15 other pubkeys hash to the addresses that separate sources give for them.
- **Method.** [`scripts/phase4_links.py`](../../scripts/phase4_links.py) checks each identifier offline against the listed keys, the derived P2PKH list, the 1,259 traced transactions and the 54,620 headers. Results are in the [matches](satoshi_linked_matches.csv) table: 73 of 98 identifiers match something in the committed data.

## 1. Every documented Satoshi payment is funded by a listed coinbase in a Patoshi-only cluster

**(a)** Four counterparties published their emails or accounts, and each payment matches the chain exactly:

| First spend (height) | Listed coinbases | Documented as | Source type |
|---|---|---|---|
| `f4184f…` (170) | 9 | 10 BTC to Hal Finney | Finney's own account |
| `d71fd2…` (524) | 286 | 25 BTC to Dustin Trammell, pay-to-IP | [Trammell's blog and emails](https://blog.dustintrammell.com/block-286-and-satoshis-coins/) |
| `7d7320…` (2616) | 2459, 2485 | 100 BTC to Nicholas Bohm | Bohm emails disclosed in COPA v Wright |
| `4b9665…` (2754) → `66ac54…` (2915) | 688 | 50 BTC moved to `18jANvQ6…`, then 19.01 BTC refunded to Bohm | Bohm emails plus chain |
| `ea84d3…` (11408) | 5326 | "+50" to Mike Hearn | Hearn's published emails |

These are 5 of the 8 "listed-only" first-spend clusters in [REPORT.md](REPORT.md) section 1. **None of the 12 listed coinbases that Phase 4 attributes to other miners appears in any documented Satoshi transaction.** The documented spends and the co-spend split agree independently. The documents also tie the Patoshi keys to Satoshi *as a sender*: Satoshi's email names the payment, and the funding coinbase is on the list. That is still evidence about who controlled particular keys in 2009, not about every listed block.

**(a)** Two non-coinbase keys used by Satoshi were exposed on-chain by these payments. `04f9f7d1…` holds the 30.99 BTC change of the Bohm refund. `04a2b359…` is behind `1PhUXucR…`, the address Satoshi gave Hearn. Neither is a listed coinbase key. Both belong in any future key-reuse search beyond the coinbase set.

## 2. The May 2010 100 BTC went to Gavin Andresen's Bitcoin Faucet

**(a)** The path below is confirmed in committed trace data:

- 2010-05-17: listed coinbases 877 and 15,625 are swept into `028ad2…`, paying 100 BTC to `1H5wBiJ…`.
- 2010-07-11 22:33:11 UTC: that output alone is paid in [`c7d4fd…`](https://mempool.space/tx/c7d4fd1b42881d8968949ece19085f432b7bc5b68ed2d3c6723b349fb87f055f) to **`15VjRaDX9zpbA8LVnbrCAFzrVzN7ixHNsC`**.

In the thread "[Donations to freebitcoins.appspot.com needed!](https://satoshi.nakamotoinstitute.org/posts/bitcointalk/threads/88/)", Gavin Andresen gives that address: "Fountain donation address is: 15VjRaDX9zpbA8LVnbrCAFzrVzN7ixHNsC". In the same post he asks "early adopters who generated tens of thousands of coins back in the early days" to donate. Later in the thread he writes "Thanks for the donations... whoever you are who donated!". Twenty-one minutes after the donation, the address pays **95 + 5 BTC**, and the 95 immediately becomes **5 + 90 BTC** ([`a3a9e5…`](https://mempool.space/tx/a3a9e58a1cec7679216bd1f59562c5a20f1b58946bb68a31080828422287ea9d), [`38f20c…`](https://mempool.space/tx/38f20c967fba99dcaed706ccb92a162594fea185dc11e76cf4b1fb53660e6715)). Those are two consecutive faucet payouts of 5 BTC with change, matching the thread's "5 bitcoins" per visitor.

**Interpretation.**

- **(b)** This resolves the Phase 3 "95/5 and 5/90 split" as faucet disbursements, not a payment pattern of the Patoshi owner. The 100 BTC left Patoshi-list control on July 11, 2010.
- **(c)** The thread describes the Faucet being "slashdotted"; the Bitcoin v0.3 Slashdot story is commonly dated to that same weekend, but its date was not re-verified here. That a holder of two listed coinbases answered this call is consistent with Satoshi supporting the Faucet. It does not prove the donor was Satoshi. `1H5wBiJ…` could have belonged to anyone who received the 100 BTC in May, and no source found names that address's owner.

**Novelty.** [Bitquery](https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth) stops at the July hop, and Phase 3 searches found no narrative of it. The identification came from matching the trace against Gavin's published address. Search absence is not proof of novelty.

## 3. Controls and the start of the list

- **(a) Blocks 78 (Hal Finney) and 309 (Dustin Trammell)** are unlisted, and their nonce low bytes (228 and 235) fail the Patoshi band. These are good negative controls: miners documented as not Satoshi fall outside the pattern.
- **(b) Blocks 1 and 2 fit the Patoshi pattern and are omission candidates.** Nonce low bytes 1 and 8 pass the tight test, and extraNonces 4 → 11 lead straight into listed blocks 3 (14) and 4 (26) within 22 minutes. Lopp's list starts at 3, and no source found explains why; [Szpili/patoshi-forensics](https://github.com/Szpili/patoshi-forensics) likewise reports the pattern reaching block 0. Both coinbases are unspent, so including them would add 100 BTC to the dormant total. The genesis block (0) passes the nonce band but has no extraNonce and is unspendable.
- **(a) `12ib7dAp…`**, the address Craig Wright claimed, receives the 9,000 BTC consolidation that the May 2010 500 BTC joined. Two hops and an 11-input merge separate it from the listed coinbases, and the COPA v Wright judgment found Wright is not Satoshi. No ownership link follows.

## 4. Corrections recorded while compiling

- `15VjRaDX…` is Gavin's Faucet donation address, not a Satoshi or bitcoin.org address, as some secondary sources imply.
- The 32.51 BTC exchange was with Mike Hearn, not the Faucet.
- The 5,050 BTC sale for $5.02 was Martti Malmi's, not Satoshi's.
- `1FeexV6b…` is the Mt. Gox theft address and unrelated.
