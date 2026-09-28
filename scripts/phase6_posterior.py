"""Phase 6: per-block posterior probability of Patoshi ownership, on committed Phase 2 and Phase 5 data; offline.

posterior  fit the two-class mixture and write a probability for every height 1 to 54,619
manifest   SHA-256 of inputs, outputs and scripts

Evidence per block, all measured without using list membership as a label for the block itself:
  co-spend  Phase 5 leave-one-out label; a block swept with another miner's coins has probability 0
  band      broad nonce low-byte band (0-9, 19-58)
  dormancy  never spent vs spent (to the Phase 5 watermark)
  track     extraNonce lies on the time-line between its nearest anchors, where anchors are listed blocks plus
            unlisted dormant band-passing blocks (leave-one-out)
Ordinary-miner rates are measured on reference blocks that fail the band, since Patoshi blocks pass it. Patoshi's
band and dormancy rates come from the list; its track-fit rate for unlisted blocks and each window's Patoshi share
are fitted by EM. Features are assumed conditionally independent given the class.
"""
import bisect, collections, csv, hashlib, json, math, sys
from datetime import datetime
from pathlib import Path
csv.field_size_limit(1_000_000_000)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase2_collect import extra_nonce

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase6'
P5 = ROOT / 'analysis/phase5'
MAX_HEIGHT = 54619
LIST_END = 49973
WINDOW = 2500
ERAS = [(1, 24999), (25000, LIST_END), (LIST_END + 1, MAX_HEIGHT)]
MAX_GAP = 6 * 3600          # anchors further apart in time than this are not a track
# Track-test settings (absolute tolerance, relative tolerance, anchors tried per side). The first is primary; the
# others are the sensitivity grid. A block's robust score is its minimum posterior over all of them.
SETTINGS = [(10, 0.15, 3), (3, 0.15, 3), (3, 0.10, 3), (10, 0.15, 1), (3, 0.10, 1)]
BAND_PATOSHI = 0.99
SEED = 20260928
CO_SPEND_LR = 1000       # Phase 5 labelling threshold: a 'patoshi' co-spend label is at least 1000:1


def offline(event, args):
    if event.startswith('socket.'):
        raise RuntimeError('Offline analysis forbids sockets')


sys.addaudithook(offline)


def read(p):
    with p.open(newline='', encoding='utf8') as f:
        return list(csv.DictReader(f))


def write_csv(name, rows, fields=None):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open('w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def save(name, x):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(x, indent=2) + '\n', encoding='utf8', newline='\n')


# ---------------------------------------------------------------- evidence

def track_fit(h, anchors, T, E, setting=SETTINGS[0]):
    """True/False when h sits between two anchors close in time; None when no anchor pair brackets it.

    anchors: sorted heights. Up to k nearest anchors below and k above h (excluding h) are paired; a pair is usable
    when it brackets h in time, is at most MAX_GAP apart and has increasing counters. h fits if its counter is within
    tolerance of the time-interpolated value of any usable pair. Several pairs are tried because Patoshi ran several
    counters at once, so the nearest anchor is often from another machine; the ordinary-miner null is measured with
    the same search, so the extra chance fits are priced in."""
    abs_tol, rel_tol, k = setting
    i = bisect.bisect_left(anchors, h)
    j = i + 1 if i < len(anchors) and anchors[i] == h else i
    below, above = anchors[max(0, i - k):i], anchors[j:j + k]
    t, e = T[h], E[h]
    if e is None:
        return None
    usable = False
    for lo in below:
        for hi in above:
            tl, th, el, eh = T[lo], T[hi], E[lo], E[hi]
            if None in (el, eh) or not tl < t < th or th - tl > MAX_GAP or not el < eh:
                continue
            usable = True
            if el < e < eh and abs(e - (el + (eh - el) * (t - tl) / (th - tl))) <= max(abs_tol, rel_tol * (eh - el)):
                return True
    return False if usable else None


def era_of(h):
    return next(i for i, (a, b) in enumerate(ERAS) if a <= h <= b)


def load():
    T, E = {}, {}
    for r in read(ROOT / 'analysis/phase2_bigquery/results/headers.csv'):
        h = int(r['height'])
        T[h] = datetime.fromisoformat(r['timestamp'].replace('+00', '+00:00')).timestamp()
        E[h] = extra_nonce(r['coinbase_param']).get('extra_nonce')
    blocks = {}
    for b in read(P5 / 'census_blocks.csv'):
        h = int(b['height'])
        if h == 0:
            continue                                   # genesis output is unspendable
        blocks[h] = {'height': h, 'listed': b['listed'] == 'True', 'band': b['broad_nonce_pass'] == 'True',
                     'spent': b['spent'] == 'True', 'loo_label': b['loo_label'], 'cluster_blocks': int(b['cluster_blocks'])}
    return blocks, T, E


def features(blocks, T, E, setting=SETTINGS[0], exclude=frozenset()):
    """Add the track feature. Anchors: listed blocks plus unlisted dormant band-passing blocks not owned by others."""
    cand = {h for h, b in blocks.items() if not b['listed'] and b['band'] and not b['spent'] and b['loo_label'] != 'other'}
    anchors = sorted(({h for h, b in blocks.items() if b['listed']} | cand) - set(exclude))
    for h, b in blocks.items():
        b['candidate'] = h in cand
        b['track'] = track_fit(h, anchors, T, E, setting)
    return blocks


# ---------------------------------------------------------------- model

def ordinary_rates(blocks):
    """Per era, rates for ordinary miners among blocks not owned by another miner, from band-failing references."""
    rates = []
    for a, z in ERAS:
        ref = [b for b in blocks.values() if a <= b['height'] <= z and not b['listed'] and not b['band']
               and b['loo_label'] != 'other']
        ev = [b for b in ref if b['track'] is not None]
        rates.append({'reference_blocks': len(ref),
                      'unspent': sum(not b['spent'] for b in ref) / len(ref),
                      'track_evaluable': len(ev) / len(ref),
                      'track_fit': sum(b['track'] for b in ev) / len(ev) if ev else 0.0})
    return rates


def patoshi_rates(blocks):
    listed = [b for b in blocks.values() if b['listed']]
    return {'unspent': sum(not b['spent'] for b in listed) / len(listed), 'band': BAND_PATOSHI}


def likelihoods(b, orate, prate, f1, e1):
    """P(features | Patoshi), P(features | ordinary). Track evaluability is modelled too, so a non-evaluable block
    carries the (weak) information that no track brackets it."""
    band_p, band_o = (prate['band'], PASS_OTHER) if b['band'] else (1 - prate['band'], 1 - PASS_OTHER)
    if b['loo_label'] == 'patoshi':
        # Spent inside a Patoshi sweep: the spend is evidence for Patoshi, at the labelling threshold, not against.
        sp_p, sp_o = CO_SPEND_LR, 1.0
    else:
        sp_p, sp_o = ((prate['unspent'], orate['unspent']) if not b['spent']
                      else (1 - prate['unspent'], 1 - orate['unspent']))
    if b['track'] is None:
        tr_p, tr_o = 1 - e1, 1 - orate['track_evaluable']
    elif b['track']:
        tr_p, tr_o = e1 * f1, orate['track_evaluable'] * orate['track_fit']
    else:
        tr_p, tr_o = e1 * (1 - f1), orate['track_evaluable'] * (1 - orate['track_fit'])
    return band_p * sp_p * tr_p, band_o * sp_o * tr_o


PASS_OTHER = 0.19610406589096613   # Phase 5 measured background (census_summary non_patoshi_background_pass_rate)


def fit_em(blocks, orates, prate, iters=500, tol=1e-10):
    """EM over unlisted, not-other blocks: per-window prior pi and per-era Patoshi track rates (evaluable e1, fit f1).

    Listed blocks are not in the mixture, so the list never labels the blocks being scored."""
    pool = [b for b in blocks.values() if not b['listed'] and b['loo_label'] != 'other']
    windows = sorted({b['height'] // WINDOW for b in pool})
    pi = {w: 0.05 for w in windows}
    f1 = [0.3] * len(ERAS)
    e1 = [0.9] * len(ERAS)
    for _ in range(iters):
        post = {}
        for b in pool:
            e = era_of(b['height'])
            lp, lo = likelihoods(b, orates[e], prate, f1[e], e1[e])
            p = pi[b['height'] // WINDOW]
            post[b['height']] = p * lp / (p * lp + (1 - p) * lo)
        new_pi = {}
        for w in windows:
            ps = [post[b['height']] for b in pool if b['height'] // WINDOW == w]
            new_pi[w] = min(max(sum(ps) / len(ps), 1e-6), 1 - 1e-6)
        new_f1, new_e1 = [], []
        for e in range(len(ERAS)):
            eb = [b for b in pool if era_of(b['height']) == e]
            wsum = sum(post[b['height']] for b in eb)
            ev = sum(post[b['height']] for b in eb if b['track'] is not None)
            fit = sum(post[b['height']] for b in eb if b['track'])
            new_e1.append((ev + 1) / (wsum + 2))          # add-one smoothing keeps sparse eras off 0 and 1
            new_f1.append((fit + 1) / (ev + 2))
        delta = max([abs(new_pi[w] - pi[w]) for w in windows] + [abs(x - y) for x, y in zip(new_f1, f1)]
                    + [abs(x - y) for x, y in zip(new_e1, e1)])
        pi, f1, e1 = new_pi, new_f1, new_e1
        if delta < tol:
            break
    return pi, f1, e1, post


def score(blocks, orates, prate, pi, f1, e1):
    """Posterior for every block. 'other' co-spend label gives 0. Listed blocks are scored by the same model as a
    diagnostic (their track anchors include other listed blocks, so their scores are optimistic)."""
    out = {}
    for h, b in blocks.items():
        if b['loo_label'] == 'other':
            out[h] = 0.0
            continue
        e = era_of(h)
        lp, lo = likelihoods(b, orates[e], prate, f1[e], e1[e])
        p = pi.get(h // WINDOW, 1e-6)
        out[h] = p * lp / (p * lp + (1 - p) * lo)
    return out


# ---------------------------------------------------------------- command

def run(blocks, T, E, setting=SETTINGS[0], exclude=frozenset()):
    features(blocks, T, E, setting, exclude)
    orates = ordinary_rates(blocks)
    prate = patoshi_rates(blocks)
    pi, f1, e1, _ = fit_em(blocks, orates, prate)
    return orates, prate, pi, f1, e1, score(blocks, orates, prate, pi, f1, e1)


def holdout(T, E, fraction=0.1, seed=SEED):
    """Sensitivity: hide a random fraction of listed blocks (not co-spent with others), rerun everything with them
    unlisted, and report how they score. Two variants: 'as_omissions' lets hidden blocks anchor each other as
    unlisted candidates, exactly as real omissions do in the main run; 'strict' excludes them from every anchor set,
    so each is scored only against the blocks that remain listed and the genuine candidates."""
    import random
    base, _, _ = load()
    rng = random.Random(seed)
    pool = sorted(h for h, b in base.items() if b['listed'] and b['loo_label'] != 'other')
    hidden = set(rng.sample(pool, int(fraction * len(pool))))
    result = {'hidden_fraction': fraction, 'seed': seed, 'hidden': len(hidden)}
    for variant, exclude in (('as_omissions', frozenset()), ('strict', frozenset(hidden))):
        blocks = load()[0]
        for h in hidden:
            blocks[h]['listed'] = False
        post = run(blocks, T, E, SETTINGS[0], exclude)[-1]
        out = []
        for a, z in ERAS:
            hs = [h for h in hidden if a <= h <= z]
            if hs:
                out.append({'era': [a, z], 'hidden': len(hs), 'mean_posterior': round(sum(post[h] for h in hs) / len(hs), 4),
                            'p_ge_0_5': round(sum(post[h] >= 0.5 for h in hs) / len(hs), 4),
                            'p_ge_0_9': round(sum(post[h] >= 0.9 for h in hs) / len(hs), 4)})
        result[variant] = out
    return result


def null_check(blocks, orates, prate, pi, f1, e1):
    """False positives: ordinary blocks known from co-spending, passing the band, rescored as if dormant and never
    co-spent. This is the hardest ordinary case, the one that looks like a candidate on band and dormancy alone."""
    out = []
    for e, (a, z) in enumerate(ERAS):
        ref = [b for b in blocks.values() if a <= b['height'] <= z and b['loo_label'] == 'other' and b['band']]
        ps = []
        for b in ref:
            fake = dict(b, spent=False, loo_label='unclustered')
            lp, lo = likelihoods(fake, orates[e], prate, f1[e], e1[e])
            p = pi.get(b['height'] // WINDOW, 1e-6)
            ps.append(p * lp / (p * lp + (1 - p) * lo))
        ev = [b for b in ref if b['track'] is not None]
        out.append({'era': [a, z], 'ordinary_band_passing_blocks': len(ref),
                    'track_fit_rate': round(sum(b['track'] for b in ev) / len(ev), 4) if ev else None,
                    'reference_track_fit_rate_band_failing': round(orates[e]['track_fit'], 4),
                    'mean_posterior': round(sum(ps) / len(ps), 4) if ps else None,
                    'p_ge_0_5': round(sum(x >= 0.5 for x in ps) / len(ps), 4) if ps else None,
                    'p_ge_0_9': round(sum(x >= 0.9 for x in ps) / len(ps), 4) if ps else None})
    return out


def posterior():
    blocks, T, E = load()
    grid = []
    for setting in SETTINGS[1:]:
        gb = load()[0]
        g = run(gb, T, E, setting)
        grid.append({'setting': setting, 'f0': [round(o['track_fit'], 4) for o in g[0]], 'f1': [round(x, 4) for x in g[3]],
                     'post': g[-1]})
    orates, prate, pi, f1, e1, post = run(blocks, T, E)
    robust = {h: min([post[h]] + [g['post'][h] for g in grid]) for h in blocks}
    named_in = {h: (post[h] >= 0.9) + sum(g['post'][h] >= 0.9 for g in grid) for h in blocks}
    rows = []
    for h in sorted(blocks):
        b = blocks[h]
        rows.append({'height': h, 'listed': b['listed'], 'co_spend_label': b['loo_label'], 'band': b['band'],
                     'spent': b['spent'], 'track_fit': '' if b['track'] is None else b['track'],
                     'window_prior': round(pi.get(h // WINDOW, 0.0), 5), 'posterior': round(post[h], 5),
                     'posterior_min_over_settings': round(robust[h], 5), 'settings_naming_at_0_9': named_in[h],
                     'extra_nonce': '' if E[h] is None else E[h],
                     'time': datetime.utcfromtimestamp(T[h]).strftime('%Y-%m-%d %H:%M:%S')})
    write_csv('posterior_blocks.csv', rows)
    unl = [r for r in rows if not r['listed'] and r['posterior'] >= 0.5]
    write_csv('posterior_candidates.csv', sorted(unl, key=lambda r: (-r['posterior_min_over_settings'], -r['posterior'],
                                                                      r['height'])), list(rows[0]))
    p5 = json.loads((P5 / 'census_summary.json').read_text())
    by_window = []
    for w in sorted(pi):
        hs = [h for h in blocks if h // WINDOW == w]
        u = [h for h in hs if not blocks[h]['listed']]
        by_window.append({'heights': f'{w * WINDOW}-{min((w + 1) * WINDOW - 1, MAX_HEIGHT)}',
                          'listed': sum(blocks[h]['listed'] for h in hs),
                          'unlisted_patoshi_prior': round(pi[w], 4),
                          'expected_unlisted_patoshi': round(sum(post[h] for h in u), 1),
                          'unlisted_p_ge_0_5': sum(post[h] >= 0.5 for h in u),
                          'unlisted_p_ge_0_9': sum(post[h] >= 0.9 for h in u)})
    write_csv('posterior_windows.csv', by_window)

    def group(lo, hi):
        u = [h for h in blocks if lo <= h <= hi and not blocks[h]['listed']]
        named = [h for h in u if post[h] >= 0.5]
        strong = [h for h in u if post[h] >= 0.9]
        core = [h for h in u if robust[h] >= 0.9]
        return {'expected_patoshi': round(sum(post[h] for h in u), 1),
                'expected_patoshi_range_over_settings': [round(min(sum(g['post'][h] for h in u) for g in grid + [{'post': post}]), 1),
                                                         round(max(sum(g['post'][h] for h in u) for g in grid + [{'post': post}]), 1)],
                'named_p_ge_0_5': len(named), 'expected_false_among_named': round(sum(1 - post[h] for h in named), 1),
                'named_p_ge_0_9': len(strong), 'expected_false_among_p_ge_0_9': round(sum(1 - post[h] for h in strong), 1),
                'robust_core_p_ge_0_9_all_settings': len(core),
                'robust_core_expected_false': round(sum(1 - robust[h] for h in core), 1),
                'robust_core_heights': [min(core), max(core)] if core else None}

    known = {h: {'posterior': round(post[h], 4), 'min_over_settings': round(robust[h], 4)}
             for h in (1, 2, 3358, 14450, 27474, 27475, 27476, 27477, 27478) if h in post}
    summary = {
        'model': {'window': WINDOW, 'eras': ERAS, 'track_max_gap_hours': MAX_GAP / 3600,
                  'track_settings_abs_rel_neighbours': SETTINGS, 'primary_setting': SETTINGS[0],
                  'band_rate_patoshi': BAND_PATOSHI, 'band_rate_ordinary': PASS_OTHER},
        'ordinary_rates_by_era': orates, 'patoshi_rates': prate,
        'patoshi_track_rates_fitted': [{'era': ERAS[e], 'evaluable': round(e1[e], 4), 'fit_given_evaluable': round(f1[e], 4)}
                                       for e in range(len(ERAS))],
        'unlisted_in_span': group(3, LIST_END), 'after_list_end': group(LIST_END + 1, MAX_HEIGHT),
        'phase5_aggregate_for_comparison': {
            'in_span_estimated_omitted': p5['omission_bound']['estimated_omitted'],
            'in_span_ci95': p5['omission_bound']['estimated_omitted_ci95'],
            'after_list_end_estimated': p5['after_list_end']['estimated_omitted'],
            'after_list_end_ci95': p5['after_list_end']['estimated_omitted_ci95']},
        'sensitivity_grid': [{k: v for k, v in g.items() if k != 'post'} for g in grid],
        'validation_holdout_listed': holdout(T, E),
        'validation_null_ordinary': null_check(blocks, orates, prate, pi, f1, e1),
        'known_cases': known,
        'assumptions': ('Two classes. Band, dormancy and track evidence independent given the class. Ordinary rates '
                        'from band-failing unlisted blocks not owned by another miner, per era. Patoshi band and '
                        'dormancy rates from the list; its track rates and the per-window share fitted by EM on '
                        'unlisted blocks only. Blocks swept with another miner (Phase 5) are fixed at 0.'),
    }
    save('posterior_summary.json', summary)
    print(json.dumps({k: summary[k] for k in ('unlisted_in_span', 'after_list_end', 'validation_holdout_listed',
                                              'validation_null_ordinary', 'known_cases')}, indent=1))


def manifest():
    inputs = ['analysis/phase2_bigquery/results/headers.csv', 'analysis/phase5/census_blocks.csv',
              'analysis/phase5/census_summary.json']
    digest = lambda f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
    outputs = sorted(str(f.relative_to(ROOT)).replace('\\', '/') for f in OUT.glob('posterior_*') if f.is_file())
    save('manifest.json', {'inputs': {f: digest(f) for f in inputs}, 'outputs': {f: digest(f) for f in outputs},
                           'scripts': {f: digest(f) for f in ('scripts/phase6_posterior.py', 'scripts/phase2_collect.py')}})


def main():
    cmds = {'posterior': posterior, 'manifest': manifest}
    for c in sys.argv[1:] or ['posterior', 'manifest']:
        cmds[c]()
        print('done', c)


if __name__ == '__main__':
    main()
