# Reproduction and evidence

**(a)** The comparison is offline and never evaluates upstream JavaScript, PHP or the original Python extractor. Python AST literal extraction reads the local array; strict integer-array parsing reads the upstream arrays. No extra packages are required for the provenance scripts.

```text
python -m unittest discover -s tests -p test_provenance.py -v
python scripts/provenance_compare.py --source lopp=analysis/provenance/sources/lopp_streaks_2022.php --source tehran=analysis/provenance/sources/tehran_patoshiBlocks_initial.js
```

**(a)** This writes all pairwise differences, density windows, consecutive-height distances, omitted CSV-rank runs, exact summaries and the canonical Lopp list. Counts are not inferred from README claims. Duplicates and list order are checked separately from set equality. Percentiles use the nearest-rank convention. A gap of distance `d` contains `d-1` intervening heights. The descriptive empirical-CDF/KS distance between E and CSV-only is recorded, without a population p-value that would conflate height selection with miner behavior.

**(b)** The random-subset diagnostic conditions on exactly 6,183 selected CSV rows. Its log probability is `sum(log10((6183-j)/(21953-j)), j=0..6156)`. It answers only whether a uniform subset plausibly retains that initial run. The apparent cutoff and all descriptive windows are exploratory; these are not independently replicated classifier tests.

**(a)** The canonical list fingerprint is SHA-256 of sorted unique decimal heights, one per line, including a final LF. Raw source hashes and LF-normalized hashes are both recorded. The primary source snapshots are pinned to immutable commit URLs:

| Artifact | Commit | SHA-256 of downloaded bytes |
|---|---|---|
| Lopp streak script | `45b9eb0f0d71dc7dd66c51fd3058943c1f6df0cb` | `0063a387a4e9b29769d56bf20b5990e3a0e02f6dc37aad15a997dd4bd556ec84` |
| TaintedBySatoshi array | `f013a619c7faa5db44de2e55b3423de48edef336` | `ecfa826e974aa1532014121a7b3c45ea98b9799f81995e888b00aa9250e8786f` |
| bensig CSV | `414637ce52aa4819926bf1934b2235ed182a0280` | `f649579e286085325a881bec1168e88bbb6f5d67e10b7ef8cb5c65e916a34a2e` |
| bensig extractor | same | `4ae2d4e26d7d4d9010c2627c86657c04ece94f9ecfc8d8c1c497514d299c8c36` |

**(a)** Downloaded snapshots and `*.metadata.json` receipt files are under `sources/`. Receipts preserve URL, HTTP status, fetch time, response headers, byte count and SHA-256. Primary array files and receipts are committed. Bulky HTML/prose, patches and redundant source copies remain in the ignored local cache; their receipts are retained. The original CSV/extractor already exist in this repository, so redundant downloads are not committed again. [source_checks.json](source_checks.json) records the additional historical/current-file and bensig equivalence checks.

`python scripts/provenance_source_checks.py` regenerates those secondary checks from the complete local cache. On a fresh clone, retrieve the ignored source copies and patches from the URLs in their committed receipts first. The main set comparison needs only the committed arrays and runs entirely offline on a fresh clone.

**(a)** To reconstruct a missing cached response, use its receipt's `requested_url` with the static-page downloader, for example:

```text
python scripts/cache_provenance_sources.py --fetch lopp_streaks_2022.php=https://raw.githubusercontent.com/jlopp/bitcoin-utils/45b9eb0f0d71dc7dd66c51fd3058943c1f6df0cb/findPatoshiMiningStreaks.php
```

The downloader accepts only public source hosts, refuses API paths, caches both successes and failures, reuses existing responses and pauses one second between requests. Files are never executed. Fetch time is an observation timestamp; commit dates are supplied by Git metadata. Neither is proof of the actual first moment a list was authored.

**(a)** Local subset/distribution analysis was finished before external retrieval. External discovery followed the article's actual script links, the requested repository's default branch and its explicit bensig source attribution. No blockchain data, spend endpoints, block headers or coinbase APIs were queried for this investigation.
