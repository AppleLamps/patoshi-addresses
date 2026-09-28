# Satoshi-linked identifiers vs the dataset

**Status: provisional.** This first version checks only identifiers read directly from committed chain data. A wider set compiled from primary sources (published emails, forum posts, participant testimony) is being added. Cross-reference script: [`scripts/phase4_links.py`](../../scripts/phase4_links.py). Inputs: [identifiers](satoshi_linked_identifiers.csv). Results: [matches](satoshi_linked_matches.csv).

| Identifier | Result |
|---|---|
| Block 170 transaction `f4184f…` | In the trace as a first spend; its only input is listed coinbase 9; its outputs are spent in `a16f3c…` (block 181, change returned to the block 9 key) and `ea44e9…` (Hal Finney's own spend) |
| Hal Finney's key `04ae1a…` | Receives the 10 BTC output of block 170; it is not a listed coinbase key |
| Block 9 key `0411db…` | Listed coinbase key (height 9); receives four traced outputs, the change of 170, 181, 182 and 183 |
| Height 14,450 | Unlisted; nonce low byte 31, tight nonce passes, extraNonce 14 (see [REPORT.md](REPORT.md) section 2) |
