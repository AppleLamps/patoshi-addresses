# Provenance investigation

**(b) Recommendation: retain the 21,953-height population for Phase 2, pinned to Lopp's published source. Do not replace it with the incomplete 6,183-height extractor list. Treat the CSV's pubkeys, amounts and script labels as an extraction cache requiring independent chain verification.** Exact membership provenance is now supported; the extraction process and miner attribution remain unverified.

Labels throughout: **(a)** verified artifact/document fact, **(b)** inference with stated reasoning, **(c)** speculation. Here (a) does not mean on-chain verification. Local comparison preceded source retrieval; no blockchain or GitHub API endpoints were called. Public source files and web pages were fetched and cached.

## 1. Exact subset and upstream comparison

**(a)** Let E = extractor heights, C = CSV heights, L = Lopp's published list and T = the requested `tehran19r/TaintedBySatoshi` list. **E is a strict subset of C, and C = L = T, including ordering.** Every list is sorted and duplicate-free.

| Compared artifacts | Shared heights | Only in first | Only in second |
|---|---:|---:|---:|
| Extractor / CSV | 6,183 | 0 | 15,770 |
| Extractor / Lopp | 6,183 | 0 | 15,770 |
| Extractor / TaintedBySatoshi | 6,183 | 0 | 15,770 |
| CSV / Lopp | 21,953 | 0 | 0 |
| CSV / TaintedBySatoshi | 21,953 | 0 | 0 |
| Lopp / TaintedBySatoshi | 21,953 | 0 | 0 |

**(a)** C, L and T span 3–49,973 and share the canonical set SHA-256 `33a74d805c95c368636c4a7334e3cff80d8624fd4b0182bde84eca9e4749465f` (sorted decimal heights, one per LF-terminated line). The exact upstream list is saved as [lopp_patoshi_heights.txt](lopp_patoshi_heights.txt). All pairwise differences, including empty ones, are saved alongside [comparison.json](comparison.json).

## 2. What the extra 15,770 heights look like

**(a)** The extractor preserves the CSV's **first 6,157 entries exactly**, through height **8,044**. Its first omission is **8,047**. Only **26** entries follow that shared prefix in the extractor: 25 scattered heights through 10,319, plus 49,973. The CSV-only set spans **8,047–49,958**, with median **18,968.5**, versus **4,047** for E. It is strongly later-skewed relative to E, but most additions precede height 30,000.

| Height interval | Extractor | CSV-only | Full CSV |
|---|---:|---:|---:|
| 3–4,999 | 3,765 | 0 | 3,765 |
| 5,000–9,999 | 2,410 | 1,446 | 3,856 |
| 10,000–14,999 | 7 | 3,664 | 3,671 |
| 15,000–19,999 | 0 | 3,506 | 3,506 |
| 20,000–24,999 | 0 | 2,891 | 2,891 |
| 25,000–29,999 | 0 | 1,453 | 1,453 |
| 30,000–34,999 | 0 | 893 | 893 |
| 35,000–39,999 | 0 | 636 | 636 |
| 40,000–44,999 | 0 | 661 | 661 |
| 45,000–49,973 | 1 | 620 | 621 |

**(a)** The largest omission in CSV row order is **14,053 consecutive CSV entries**, heights 10,320–49,958. E jumps directly from 10,319 to 49,973, leaving **39,653 intervening heights** unlisted. The CSV-only set's largest gap is just **426 intervening heights**, 37,312–37,737; its eight largest gaps coincide with the full CSV's eight largest gaps. Median consecutive-height distance is 1 for both E and CSV-only, but their 90th percentiles are 2 versus 6, and their means are 8.083 versus 2.658; E's mean is dominated by its huge final jump. [Gap data](consecutive_height_gaps.csv); [omitted row runs](omitted_csv_rank_runs.csv).

**(b)** This is not a random subsample. Under the explicit null of choosing 6,183 of the 21,953 CSV positions uniformly without replacement, the probability of including the first 6,157 positions is approximately `10^-5583.25`, calculated as the product of conditional inclusion probabilities. This tests the artifact selection pattern, not miner identity or the nonce classifier.

**(a)** Around the cutoff, full-CSV density is 6,157/8,042 = **76.56%** through 8,044, then 1,742/2,275 = **76.57%** through 10,319. Equal 2,000-height windows immediately before/after the cutoff contain **1,549 versus 1,504 CSV entries**, while E collapses from 1,549 to **18**. [Window data](height_windows.csv).

**(b)** The sharp discontinuity belongs to the extractor. The CSV continues with similar local density, then declines over later ranges. Together with the exact Lopp match, this supports a coherent continuation of the *same published classification*. Different unconditional gap distributions do not establish different miners or classifier versions: the sets occupy different height ranges. Nonce/extraNonce fit still requires Phase 2.

## 3. Source trail and limits

**(a)** Lopp's [September 16, 2022 analysis](https://blog.lopp.net/was-satoshi-a-greedy-miner/) links to `findPatoshiMiningStreaks.php`. Its [file-creation commit dated September 13, 2022](https://github.com/jlopp/bitcoin-utils/commit/45b9eb0f0d71dc7dd66c51fd3058943c1f6df0cb) contains [all 21,953 matching heights](https://github.com/jlopp/bitcoin-utils/blob/45b9eb0f0d71dc7dd66c51fd3058943c1f6df0cb/findPatoshiMiningStreaks.php). The historical and currently retrieved versions are byte-identical. A [second script linked from the article](https://github.com/jlopp/bitcoin-utils/blob/eb5b7cfe98ea846a30ffd87b04e9a4137cf3bde7/findNonPatoshiDeltasAfterFastPatoshiBlocks.php) has the same set. This verifies publication by Lopp, not who first assembled or individually classified every entry.

**(a)** `bensig/patoshi-addresses` exposes the same initial commit as this repository, [414637c, dated July 15, 2025](https://github.com/bensig/patoshi-addresses/commit/414637ce52aa4819926bf1934b2235ed182a0280). Its [CSV](https://github.com/bensig/patoshi-addresses/blob/414637ce52aa4819926bf1934b2235ed182a0280/patoshi_pubkeys_COMPLETE.csv) and [extractor](https://github.com/bensig/patoshi-addresses/blob/414637ce52aa4819926bf1934b2235ed182a0280/extract_patoshi_addresses.py) are byte-identical to the local originals after CRLF-to-LF normalization. The inconsistency therefore exists in that shared source commit; it was not introduced by our Phase 1 work.

**(a)** The requested repository is displayed as a [fork of MikelCalvo/TaintedBySatoshi](https://github.com/tehran19r/TaintedBySatoshi). Its [list-creation commit dated January 7, 2026](https://github.com/tehran19r/TaintedBySatoshi/commit/f013a619c7faa5db44de2e55b3423de48edef336) contains the exact matching [21,953-height array](https://github.com/tehran19r/TaintedBySatoshi/blob/f013a619c7faa5db44de2e55b3423de48edef336/backend/src/data/patoshiBlocks.js). The file explicitly identifies `bensig/patoshi-addresses` as its source; its initial and current copies match byte-for-byte. Thus this is an attributed downstream copy, not independent classifier validation. Commit dates are repository metadata, not independently authenticated creation times.

**(b) Best-supported account:** all 15,770 CSV-only heights were already present in Lopp's published full list. The CSV carries that entire height classification, while the accompanying extractor carries an incomplete subset. The `TaintedBySatoshi` match corroborates reuse of the list and identifies a downstream source claim. It does **not** explain which extraction program populated the CSV's pubkeys and amounts, or prove a direct Lopp-to-bensig copying route rather than an intermediary.

## 4. Script archaeology and dead ends

**(a)** The hardcoded list is syntactically complete, closed, sorted and stored on line 24. It has 6,183 entries, not a round entry count; the assignment line is **30,009 characters**. It preserves the terminal height 49,973, so it is not simply the prefix of a file cut off at 8,044. There is no ellipsis, incomplete-list warning, source URL, version identifier or append operation. The comment credits Lerner and Lopp but identifies no exact source revision.

**(a)** The code only filters that list with `--start-block`, fetches each selected block's first transaction and emits its outputs. It contains **no Patoshi classifier**, no second height source and no logic that can add the missing heights. `--chunk-size` controls progress logging, not membership. The default filename is `patoshi_addresses.csv`, differing from the shipped `patoshi_pubkeys_COMPLETE.csv`; output is opened in write mode. Fetch failures can remove heights but cannot create the 15,770 absent ones. The sole historical commit touching the original script/CSV adds both together and describes a full block array, which the stored data contradicts.

**(b)** The preserved prefix plus sparse tail makes incomplete copying/assembly more plausible than a coherent earlier classifier version. **(c)** A roughly 30,000-character size limit is one possible explanation; no such limit or tool is documented. Neither the person responsible, the omission mechanism, nor an older 6,183-height classifier version was established. The `main` URL for TaintedBySatoshi returned 404; the actual file is on `master`. No chain query was necessary to settle these artifact relationships.

## Phase 2 decision

**(b)** Use the pinned [Lopp height file](lopp_patoshi_heights.txt) as the declared candidate population; it selects exactly the same blocks as the CSV. Re-fetch and compare actual coinbase outputs before trusting cached pubkeys or balances. Treat unlisted controls as *unlisted*, not proven non-Patoshi. Preserve disagreements instead of silently replacing labels.

**(a)** Lopp's article discusses height 54,316 although the accompanying list ends at 49,973. **(b)** Therefore this matched list is not evidence that all Patoshi activity ended at its last entry; the boundary investigation should explicitly consider the larger range. Exact agreement across copied lists establishes membership provenance, not classifier accuracy, spend status, or the Patoshi=Satoshi hypothesis.

See [METHODS.md](METHODS.md) for reproduction and cached-source details.
