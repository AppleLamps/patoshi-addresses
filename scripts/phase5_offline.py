"""Phase 5 co-spend census analysis on the committed BigQuery export; no network, no key recovery, no spending.

census     cluster every early coinbase by co-spending and measure the list against ownership-labelled clusters
replicate  rebuild census-format rows from the Phase 4 first spends only and check that Phase 4 is reproduced
manifest   SHA-256 of inputs, outputs and scripts

Ownership labels never use list membership. A block's owner is labelled from the nonce band of the OTHER blocks
spent with it (leave-one-out), so a listed block's own nonce, which the list was built from, cannot vote.
"""
import bisect, collections, csv, functools, hashlib, json, math, sys
from pathlib import Path
import numpy as np
csv.field_size_limit(1_000_000_000)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase4_offline as p4
from phase2_analyze import nonce_pass, inner_pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase5'
CENSUS = OUT / 'results/cospend_census.csv'
MAX_HEIGHT = 54619

# Nonce-band likelihood ratio. Patoshi blocks pass the broad low-byte band (0-9, 19-58) essentially always; the
# 1% slack keeps one failing co-member from being decisive. Ordinary miners pass at the uniform rate 50/256.
PASS_OTHER = 50 / 256
EPS = 0.01
W_PASS = math.log((1 - EPS) / PASS_OTHER)
W_FAIL = math.log(EPS / (1 - PASS_OTHER))
THRESHOLD = math.log(1000)
BOOTSTRAP_REPS = 4000
SEED = 20260928


def read(p):
    with p.open(newline='', encoding='utf8') as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- labels and statistics

def nonce_llr(k, n):
    """log P(k of n pass | Patoshi) - log P(k of n pass | ordinary miner), binomial coefficient cancels."""
    return k * W_PASS + (n - k) * W_FAIL


def nonce_label(k, n):
    if n == 0:
        return 'unclustered'
    llr = nonce_llr(k, n)
    return 'patoshi' if llr >= THRESHOLD else ('other' if llr <= -THRESHOLD else 'undetermined')


@functools.lru_cache(maxsize=None)
def label_error_rates(n):
    """Chance that n co-members of one class are labelled as the other class (log-space, safe for large sweeps)."""
    if n == 0:
        return 0.0, 0.0
    ks = range(n + 1)
    pmf = lambda k, p: math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                                + k * math.log(p) + (n - k) * math.log1p(-p))
    other_as_patoshi = sum(pmf(k, PASS_OTHER) for k in ks if nonce_llr(k, n) >= THRESHOLD)
    patoshi_as_other = sum(pmf(k, 1 - EPS) for k in ks if nonce_llr(k, n) <= -THRESHOLD)
    return other_as_patoshi, patoshi_as_other


def wilson(k, n, z=1.959964):
    if n == 0:
        return [0.0, 1.0]
    p = k / n
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [max(0.0, mid - half), min(1.0, mid + half)]


def cluster_bootstrap(groups, reps=BOOTSTRAP_REPS, seed=SEED):
    """Percentile 95% interval of sum(k)/sum(n), resampling clusters. groups: list of (k, n)."""
    if not groups:
        return [None, None]
    k = np.array([g[0] for g in groups], dtype=float)
    n = np.array([g[1] for g in groups], dtype=float)
    rng = np.random.default_rng(seed)
    ratio = []
    for start in range(0, reps, 250):
        idx = rng.integers(0, len(groups), size=(min(250, reps - start), len(groups)))
        ratio.append(k[idx].sum(axis=1) / n[idx].sum(axis=1))
    ratio = np.concatenate(ratio)
    return [float(np.quantile(ratio, 0.025)), float(np.quantile(ratio, 0.975))]


class Union:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def join(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


# ---------------------------------------------------------------- core

def census_core(rows, listed, passes):
    """rows: census CSV rows. listed: set of listed heights. passes: height -> broad nonce pass (bool).

    Returns blocks (height -> dict), transactions (txid -> dict) and clusters (id -> dict). A block is the ownership
    unit: every output of its coinbase is assumed to belong to whoever mined it."""
    outputs = [r for r in rows if r['row_kind'] == 'coinbase_output']
    inputs = [r for r in rows if r['row_kind'] == 'spending_input']
    blocks = {}
    for r in outputs:
        h = int(r['height'])
        b = blocks.setdefault(h, {'height': h, 'coinbase_txid': r['txid'], 'outputs': 0, 'value_sats': 0,
                                  'addresses': set(), 'spending_txids': set()})
        b['outputs'] += 1
        b['value_sats'] += int(r['value_sats'] or 0)
        if r['address']:
            b['addresses'].add(r['address'])
    txs = {}
    for r in inputs:
        t = txs.setdefault(r['txid'], {'txid': r['txid'], 'height': int(r['height']), 'time': r['time'],
                                       'inputs': 0, 'coinbase_heights': set()})
        t['inputs'] += 1
        if r['coinbase_height'] != '':
            h = int(r['coinbase_height'])
            t['coinbase_heights'].add(h)
            blocks[h]['spending_txids'].add(r['txid'])
    # Strict clusters: co-spent in one transaction (each outpoint is spent once, so this is per transaction, joined
    # only where one block's several outputs were spent in different transactions).
    strict, extended = Union(), Union()
    for h in blocks:
        strict.find(h)
        extended.find(h)
    for t in txs.values():
        hs = sorted(t['coinbase_heights'])
        for h in hs[1:]:
            strict.join(hs[0], h)
            extended.join(hs[0], h)
    # Extended clusters add payout-key reuse: coinbases paying the same address share an owner, spent or not.
    by_address = collections.defaultdict(list)
    for h, b in blocks.items():
        for a in b['addresses']:
            by_address[a].append(h)
    for hs in by_address.values():
        for h in hs[1:]:
            extended.join(hs[0], h)
    members = collections.defaultdict(list)
    for h in blocks:
        members[strict.find(h)].append(h)
    ext_size = collections.Counter(extended.find(h) for h in blocks)
    clusters = {}
    for cid, hs in members.items():
        hs.sort()
        k = sum(passes[h] for h in hs)
        nl = sum(h in listed for h in hs)
        clusters[cid] = {'cluster_id': cid, 'blocks': len(hs), 'listed': nl, 'unlisted': len(hs) - nl,
                         'broad_nonce_pass': k, 'nonce_llr': round(nonce_llr(k, len(hs)), 3),
                         'nonce_label': nonce_label(k, len(hs)) if len(hs) > 1 else 'unclustered',
                         'list_majority': ('listed_only' if nl == len(hs) else 'unlisted_only' if nl == 0 else
                                           'listed_majority' if 2 * nl > len(hs) else
                                           'unlisted_majority' if 2 * nl < len(hs) else 'tie'),
                         'heights': hs,
                         'spending_txids': sorted({x for h in hs for x in blocks[h]['spending_txids']})}
    for h, b in blocks.items():
        c = clusters[strict.find(h)]
        n_other, k_other = c['blocks'] - 1, c['broad_nonce_pass'] - passes[h]
        b.update({'listed': h in listed, 'broad_nonce_pass': passes[h], 'spent': bool(b['spending_txids']),
                  'cluster_id': c['cluster_id'], 'cluster_blocks': c['blocks'], 'cluster_listed': c['listed'],
                  'co_members': n_other, 'co_members_pass': k_other,
                  'loo_llr': round(nonce_llr(k_other, n_other), 3) if n_other else '',
                  'loo_label': nonce_label(k_other, n_other),
                  'address_cluster_id': extended.find(h), 'address_cluster_blocks': ext_size[extended.find(h)]})
    return blocks, txs, clusters


def measure(blocks, clusters, span, unlisted_in_span, listed_count):
    """List precision and omission rates from leave-one-out ownership labels, restricted to the list's height span."""
    lo, hi = span
    in_span = [b for b in blocks.values() if lo <= b['height'] <= hi]

    def rate(label, hit):
        group = [b for b in in_span if b['loo_label'] == label]
        per_cluster = collections.defaultdict(lambda: [0, 0])
        for b in group:
            per_cluster[b['cluster_id']][0] += hit(b)
            per_cluster[b['cluster_id']][1] += 1
        k, n = sum(hit(b) for b in group), len(group)
        return {'blocks': n, 'hits': k, 'rate': k / n if n else None, 'wilson95': wilson(k, n),
                'cluster_bootstrap95': cluster_bootstrap([tuple(v) for v in per_cluster.values()]),
                'clusters': len(per_cluster)}

    fp = rate('other', lambda b: b['listed'])
    om = rate('patoshi', lambda b: not b['listed'])

    def implied_fp(p):
        return None if p is None or p >= 1 else p / (1 - p) * unlisted_in_span

    fp['implied_false_positive_heights'] = implied_fp(fp['rate'])
    fp['implied_false_positive_heights_ci'] = [implied_fp(x) for x in fp['cluster_bootstrap95']]
    fp['implied_precision'] = (1 - fp['implied_false_positive_heights'] / listed_count
                               if fp['implied_false_positive_heights'] is not None else None)
    om['implied_omitted_heights'] = (om['rate'] / (1 - om['rate']) * listed_count
                                     if om['rate'] is not None and om['rate'] < 1 else None)
    om['implied_recall'] = 1 - om['rate'] if om['rate'] is not None else None
    confusion = collections.Counter((b['loo_label'], 'listed' if b['listed'] else 'unlisted') for b in in_span)
    return {'list_false_positive_rate_among_other_miner_blocks': fp,
            'list_omission_rate_among_patoshi_owned_blocks': om,
            'confusion_loo_label_by_list': {f'{a}|{b}': v for (a, b), v in sorted(confusion.items())}}


def track_tests(blocks, clusters, headers, lsorted):
    """Phase 4's counter-track test, applied to every listed block whose co-members are labelled another miner."""
    track = []
    for b in sorted(blocks.values(), key=lambda b: b['height']):
        if not (b['listed'] and b['loo_label'] == 'other'):
            continue
        c = clusters[b['cluster_id']]
        members = [(m, headers[m]['en'], headers[m]['t']) for m in c['heights'] if not blocks[m]['listed']]
        h, x = b['height'], headers[b['height']]
        before = [m for m in members if m[0] < h]
        after = [m for m in members if m[0] > h]
        p, a = (before[-1] if before else None), (after[0] if after else None)
        hs = [m[0] for m in members]
        fits = total = 0
        if len(hs) >= 2:
            for g in lsorted[bisect.bisect_right(lsorted, hs[0]):bisect.bisect_left(lsorted, hs[-1])]:
                if g == h:
                    continue
                j = bisect.bisect_left(hs, g)
                lb, la, y = members[j - 1], members[j], headers[g]
                if la[0] - lb[0] > 400 or lb[1] is None or la[1] is None or y['en'] is None:
                    continue
                total += 1
                fits += lb[1] < y['en'] < la[1] and lb[2] < y['t'] < la[2]
        track.append({'listed_height': h, 'spending_txid': ' '.join(c['spending_txids']), 'cluster_id': c['cluster_id'],
                      'cluster_blocks': c['blocks'], 'extra_nonce': x['en'], 'block_time': x['t'],
                      'tight_nonce_pass': inner_pass(x['n']),
                      'cluster_prev_height': p[0] if p else '', 'cluster_prev_en': p[1] if p else '',
                      'cluster_next_height': a[0] if a else '', 'cluster_next_en': a[1] if a else '',
                      'other_miner_track_sandwich': bool(p and a and p[1] is not None and a[1] is not None
                                                         and x['en'] is not None
                                                         and p[1] < x['en'] < a[1] and p[2] < x['t'] < a[2]),
                      'patoshi_run_sandwich': p4.run_fit(h, headers, lsorted)['sandwich'],
                      'span_listed_blocks_evaluated': total, 'span_listed_blocks_fitting_track': fits,
                      'chance_fit_rate': round(fits / total, 4) if total else ''})
    return track


def background_pass_rate(blocks, span):
    """Own-nonce pass rate of unlisted blocks whose co-members are another miner: the measured non-Patoshi rate."""
    bs = [b for b in blocks.values() if span[0] <= b['height'] <= span[1] and not b['listed'] and b['loo_label'] == 'other']
    k = sum(b['broad_nonce_pass'] for b in bs)
    return {'blocks': len(bs), 'passes': k, 'rate': k / len(bs) if bs else None, 'wilson95': wilson(k, len(bs)),
            'uniform_rate': PASS_OTHER}


def omission_room(bs, background, patoshi_rate=1 - EPS):
    """Unlisted blocks that could still be omitted Patoshi blocks: not owned by another miner, and passing the band.

    Any omitted Patoshi block must be in this set (assuming Patoshi blocks always pass the band), so its size is an
    upper bound. With M omitted blocks among n, expected passes are patoshi_rate * M + background * (n - M), so the
    excess over background * n estimates (patoshi_rate - background) * M; dividing by that gives the block count."""
    free = [b for b in bs if not b['listed'] and b['loo_label'] != 'other']
    n, k = len(free), sum(b['broad_nonce_pass'] for b in free)
    expected = background * n
    sd = math.sqrt(n * background * (1 - background))
    excess, lo, hi = k - expected, max(0.0, k - expected - 1.96 * sd), k - expected + 1.96 * sd
    scale = patoshi_rate - background
    return {'unlisted_not_other_miner': n, 'of_which_pass_band': k,
            'of_which_pass_band_unspent': sum(b['broad_nonce_pass'] and not b['spent'] for b in free),
            'chance_passes': round(expected, 1), 'excess_passes': round(excess, 1),
            'excess_passes_ci95': [round(lo, 1), round(hi, 1)],
            'estimated_omitted': round(excess / scale, 1),
            'estimated_omitted_ci95': [round(lo / scale, 1), round(hi / scale, 1)]}


def era_table(blocks, background, span, width=5000):
    rows = []
    for lo in range(0, MAX_HEIGHT + 1, width):
        bs = [b for b in blocks.values() if lo <= b['height'] < lo + width]
        other = [b for b in bs if b['loo_label'] == 'other']
        pat = [b for b in bs if b['loo_label'] == 'patoshi']
        room = omission_room([b for b in bs if span[0] <= b['height'] <= span[1]], background)
        rows.append({'heights': f'{lo}-{min(lo + width, MAX_HEIGHT + 1) - 1}', 'blocks': len(bs),
                     'listed': sum(b['listed'] for b in bs), 'spent': sum(b['spent'] for b in bs),
                     'listed_spent': sum(b['spent'] and b['listed'] for b in bs),
                     'in_multi_block_cluster': sum(b['cluster_blocks'] > 1 for b in bs),
                     'loo_other': len(other), 'loo_other_listed': sum(b['listed'] for b in other),
                     'loo_patoshi': len(pat), 'loo_patoshi_unlisted': sum(not b['listed'] for b in pat),
                     'loo_undetermined': sum(b['loo_label'] == 'undetermined' for b in bs),
                     'in_span_unlisted_not_other_miner': room['unlisted_not_other_miner'],
                     'in_span_omission_bound_pass_band': room['of_which_pass_band'],
                     'in_span_chance_passes': room['chance_passes'], 'in_span_excess_passes': room['excess_passes'],
                     'in_span_estimated_omitted': room['estimated_omitted'],
                     'in_span_estimated_omitted_lo95': room['estimated_omitted_ci95'][0],
                     'in_span_estimated_omitted_hi95': room['estimated_omitted_ci95'][1]})
    return rows


def expected_mislabels(blocks):
    """Expected wrong labels over all clustered blocks if every block's co-members were ordinary miners (would still
    be labelled patoshi) or all Patoshi (would still be labelled other). Worst cases, not estimates."""
    e_op = e_po = 0.0
    for b in blocks.values():
        op, po = label_error_rates(b['co_members'])
        e_op += op
        e_po += po
    return {'patoshi_labels_if_all_co_members_were_other_miners': round(e_op, 4),
            'other_labels_if_all_co_members_were_patoshi': round(e_po, 4)}


# ---------------------------------------------------------------- commands

def load_context():
    headers, listed = p4.load_headers(), set(p4.load_listed())
    passes = {h: nonce_pass(x['n']) for h, x in headers.items()}
    return headers, listed, passes


def analyse(rows, write=True):
    headers, listed, passes = load_context()
    blocks, txs, clusters = census_core(rows, listed, passes)
    missing = sorted(set(range(MAX_HEIGHT + 1)) - set(blocks))
    lsorted = sorted(listed)
    span = (lsorted[0], lsorted[-1])
    unlisted_in_span = sum(1 for h in range(span[0], span[1] + 1) if h not in listed)
    result = measure(blocks, clusters, span, unlisted_in_span, len(listed))
    background = background_pass_rate(blocks, span)
    room = omission_room([b for b in blocks.values() if span[0] <= b['height'] <= span[1]], background['rate'] or PASS_OTHER)
    tp = len(listed) - (result['list_false_positive_rate_among_other_miner_blocks']['implied_false_positive_heights'] or 0)
    room['recall_lower_bound'] = tp / (tp + room['of_which_pass_band'])
    room['recall_estimate'] = tp / (tp + max(0.0, room['estimated_omitted']))
    room['recall_estimate_ci95'] = [tp / (tp + room['estimated_omitted_ci95'][1]), tp / (tp + room['estimated_omitted_ci95'][0])]
    track = track_tests(blocks, clusters, headers, lsorted)
    omission = []
    for b in sorted(blocks.values(), key=lambda b: b['height']):
        if b['listed'] or b['loo_label'] != 'patoshi':
            continue
        x, fit = headers[b['height']], p4.run_fit(b['height'], headers, lsorted)
        omission.append({'height': b['height'], 'cluster_id': b['cluster_id'], 'cluster_blocks': b['cluster_blocks'],
                         'cluster_listed': b['cluster_listed'], 'spending_txid': ' '.join(sorted(b['spending_txids'])),
                         'nonce_lsb': x['n'] & 255, 'broad_nonce_pass': b['broad_nonce_pass'],
                         'tight_nonce_pass': inner_pass(x['n']), 'extra_nonce': x['en'], 'block_time': x['t'],
                         'left_listed': fit['left'], 'right_listed': fit['right'],
                         'left_en': fit.get('left_en', ''), 'right_en': fit.get('right_en', ''),
                         'run_sandwich': fit['sandwich']})
    multi = [c for c in clusters.values() if c['blocks'] > 1]
    list_majority_other = [c for c in multi if c['list_majority'] in ('unlisted_majority',) and c['listed']]
    unl_in_lm_other = [h for c in multi if c['list_majority'] in ('unlisted_majority', 'unlisted_only')
                       for h in c['heights'] if h not in listed]
    ext_sizes = collections.Counter(b['address_cluster_id'] for b in blocks.values())
    summary = {
        'population': {'heights': f'0-{MAX_HEIGHT}', 'blocks_with_coinbase_rows': len(blocks),
                       'heights_missing_coinbase_rows': missing[:50], 'heights_missing_count': len(missing),
                       'list_span': list(span), 'listed': len(listed), 'unlisted_in_span': unlisted_in_span},
        'spending': {'spending_transactions': len(txs),
                     'spending_transactions_with_two_or_more_early_coinbases': sum(len(t['coinbase_heights']) > 1 for t in txs.values()),
                     'blocks_spent': sum(b['spent'] for b in blocks.values()),
                     'listed_blocks_spent': sum(b['spent'] and b['listed'] for b in blocks.values()),
                     'blocks_with_outputs_spent_in_different_transactions': sum(len(b['spending_txids']) > 1 for b in blocks.values()),
                     'multi_output_coinbases': sum(b['outputs'] > 1 for b in blocks.values()),
                     'spend_height_range': [min((t['height'] for t in txs.values()), default=None),
                                            max((t['height'] for t in txs.values()), default=None)]},
        'clusters': {'multi_block_clusters': len(multi),
                     'blocks_in_multi_block_clusters': sum(c['blocks'] for c in multi),
                     'largest_cluster_blocks': max((c['blocks'] for c in multi), default=0),
                     'by_nonce_label': dict(collections.Counter(c['nonce_label'] for c in multi)),
                     'by_list_majority': dict(collections.Counter(c['list_majority'] for c in multi)),
                     'address_linked_largest_cluster_blocks': max(ext_sizes.values(), default=0),
                     'address_linked_multi_block_clusters': sum(v > 1 for v in ext_sizes.values())},
        'nonce_label_rule': {'pass_rate_other_miner': PASS_OTHER, 'pass_rate_patoshi': 1 - EPS,
                             'threshold_likelihood_ratio': 1000,
                             'weights_per_co_member': {'pass': round(W_PASS, 4), 'fail': round(W_FAIL, 4)},
                             'expected_mislabels': expected_mislabels(blocks)},
        'measurement': result,
        'non_patoshi_background_pass_rate': background,
        'omission_bound': room,
        'after_list_end': omission_room([b for b in blocks.values() if b['height'] > span[1]], background['rate'] or PASS_OTHER),
        'phase4_comparison': {
            'list_majority_zero_truncated_mle': p4.zt_binomial_mle([(c['blocks'], c['listed']) for c in list_majority_other])
            if list_majority_other else None,
            'list_majority_unlisted_majority_clusters_with_a_listed_member': len(list_majority_other),
            'unlisted_blocks_in_unlisted_clusters_broad_nonce_rate': (sum(passes[h] for h in unl_in_lm_other) / len(unl_in_lm_other)
                                                                     if unl_in_lm_other else None),
            'phase4_first_spends': phase4_consistency(txs, listed)},
        'track_test': {'listed_blocks_with_other_miner_co_members': len(track),
                       'observed_fits': sum(t['other_miner_track_sandwich'] for t in track),
                       'cluster_level': p4.cluster_track_test(
                           [dict(t, spending_txid=t['cluster_id']) for t in track]) if track else None},
        'omission_candidates': {'unlisted_blocks_with_patoshi_co_members': len(omission),
                                'tight_nonce_pass': sum(o['tight_nonce_pass'] for o in omission),
                                'run_sandwich': sum(o['run_sandwich'] for o in omission)},
        'assumptions': ('Common-input ownership: all inputs of one transaction are controlled by one entity, and every output '
                        'of a coinbase belongs to its miner. Ownership labels come only from the nonce band of the other '
                        'blocks spent together (leave-one-out likelihood ratio at 1000:1), never from the list. Blocks '
                        'never co-spent with another early coinbase carry no ownership label. Spent blocks may not be '
                        'representative of unspent ones, and custodial or CoinJoin transactions would merge owners.'),
    }
    if write:
        out_blocks = [{k: (' '.join(sorted(v)) if isinstance(v, set) else v) for k, v in b.items() if k != 'addresses'}
                      | {'addresses': ' '.join(sorted(b['addresses']))} for b in sorted(blocks.values(), key=lambda b: b['height'])]
        p4.OUT = OUT
        p4.table('census_blocks.csv', out_blocks)
        p4.table('census_transactions.csv', [{'txid': t['txid'], 'height': t['height'], 'time': t['time'],
                                               'inputs': t['inputs'], 'early_coinbases': len(t['coinbase_heights']),
                                               'listed': sum(h in listed for h in t['coinbase_heights']),
                                               'cluster_id': blocks[min(t['coinbase_heights'])]['cluster_id']}
                                              for t in sorted(txs.values(), key=lambda t: (t['height'], t['txid']))])
        p4.table('census_clusters.csv', [{k: (' '.join(map(str, v)) if isinstance(v, list) else v) for k, v in c.items()}
                                         for c in sorted(multi, key=lambda c: c['cluster_id'])])
        track_fields = list(track[0]) if track else ['listed_height']
        p4.table('census_listed_with_other_miner_co_members.csv', track, track_fields)
        p4.table('census_omission_candidates.csv', omission, list(omission[0]) if omission else ['height'])
        p4.table('census_eras.csv', era_table(blocks, background['rate'] or PASS_OTHER, span))
        p4.save('census_summary.json', summary)
    return summary, blocks, txs, clusters


def phase4_consistency(txs, listed):
    p = ROOT / 'analysis/phase4/cospend_clusters.csv'
    if not p.exists():
        return None
    rows = []
    for c in p4.read(p):
        t = txs.get(c['spending_txid'])
        rows.append({'spending_txid': c['spending_txid'], 'phase4_listed': int(c['listed']),
                     'phase4_unlisted': int(c['unlisted']), 'phase4_unmapped_inputs': int(c['unmapped_inputs']),
                     'census_listed': sum(h in listed for h in t['coinbase_heights']) if t else None,
                     'census_unlisted': sum(h not in listed for h in t['coinbase_heights']) if t else None})
    return {'transactions': len(rows), 'found_in_census': sum(r['census_listed'] is not None for r in rows),
            'listed_counts_equal': sum(r['census_listed'] == r['phase4_listed'] for r in rows),
            'unlisted_gained_from_previously_unmapped_inputs': sum((r['census_unlisted'] or 0) - r['phase4_unlisted'] for r in rows
                                                                   if r['census_unlisted'] is not None),
            'rows': rows}


def census():
    if not CENSUS.exists():
        raise SystemExit(f'{CENSUS.relative_to(ROOT)} is missing: run  python scripts/phase5_bigquery.py census --execute  first')
    summary = analyse(read(CENSUS))[0]
    m = summary['measurement']['list_false_positive_rate_among_other_miner_blocks']
    print(json.dumps({'blocks_spent': summary['spending']['blocks_spent'],
                      'multi_block_clusters': summary['clusters']['multi_block_clusters'],
                      'false_positive_rate': m['rate'], 'bootstrap95': m['cluster_bootstrap95'],
                      'implied_precision': m['implied_precision']}))


def replicate_rows():
    """Census-format rows built only from committed Phase 2 to 4 data: the 20 first-spending transactions."""
    headers = p4.load_headers()
    cb = p4.coinbase_heights(headers)
    rows = []
    for txid, h in cb.items():
        rows.append({'row_kind': 'coinbase_output', 'height': str(h), 'txid': txid, 'idx': '0', 'time': headers[h]['t'],
                     'prev_txid': '', 'prev_vout': '', 'value_sats': '5000000000', 'output_type': 'pubkey',
                     'address': '', 'coinbase_height': ''})
    for t in p4.load_seeds().values():
        for vi, v in enumerate(t['vin']):
            h = cb.get(v['txid']) if v['vout'] == 0 else None
            rows.append({'row_kind': 'spending_input', 'height': str(t['status']['block_height']), 'txid': t['txid'],
                         'idx': str(vi), 'time': '', 'prev_txid': v['txid'], 'prev_vout': str(v['vout']),
                         'value_sats': '', 'output_type': '', 'address': '', 'coinbase_height': '' if h is None else str(h)})
    return rows


def replicate():
    summary, blocks, txs, clusters = analyse(replicate_rows(), write=False)
    r = summary['phase4_comparison']['phase4_first_spends']
    print(json.dumps({k: v for k, v in r.items() if k != 'rows'}))
    assert r['found_in_census'] == r['transactions'] == 20
    assert r['listed_counts_equal'] == 20 and r['unlisted_gained_from_previously_unmapped_inputs'] == 0


def manifest():
    inputs = ['patoshi_pubkeys_COMPLETE.csv', 'analysis/phase2_bigquery/results/headers.csv',
              'analysis/phase5/sql/cospend_census.sql', 'analysis/phase5/sql/cospend_census_semijoin.sql']
    for f in ('analysis/phase5/results/cospend_census.csv', 'analysis/phase5/results/cospend_census.metadata.json'):
        if (ROOT / f).exists():
            inputs.append(f)
    digest = lambda f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
    outputs = sorted(str(f.relative_to(ROOT)).replace('\\', '/') for f in OUT.glob('census_*') if f.is_file())
    p4.OUT = OUT
    p4.save('manifest.json', {'inputs': {f: digest(f) for f in inputs}, 'outputs': {f: digest(f) for f in outputs},
                              'scripts': {f: digest(f) for f in ('scripts/phase5_offline.py', 'scripts/phase5_bigquery.py',
                                                                 'scripts/phase4_offline.py', 'scripts/phase2_analyze.py')}})


def main():
    cmds = {'census': census, 'replicate': replicate, 'manifest': manifest}
    for c in sys.argv[1:] or ['census', 'manifest']:
        cmds[c]()
        print('done', c)


if __name__ == '__main__':
    main()
