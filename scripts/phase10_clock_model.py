"""Phase 10: the Phase 9 nonce clock inside the Phase 6 per-block model.

    python scripts/phase10_clock_model.py model       # M10 fit, five track settings, V1 to V3, tiers, E1
    python scripts/phase10_clock_model.py suspects    # section 4: trackless listed blocks with stock-like nonces
    python scripts/phase10_clock_model.py manifest

Offline, from committed files. Definitions follow analysis/phase10_clock_model/PREREGISTRATION.md. Phase 6's model code is
reused unchanged; the clock enters as one extra likelihood factor, switched off to reproduce the Phase 6 baseline.
"""
import csv, hashlib, json, math, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase6_posterior as p6
import phase8_synthesis as p8
import phase9_nonce_clock as p9

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase10_clock_model'
PREREG = OUT / 'PREREGISTRATION.md'
USE_CLOCK = True
PATOSHI_SHAPE = 0.477                  # Phase 7: in-band share of low bytes 0 to 9, listed 25,000 to 49,973

# ---------------------------------------------------------------- clock evidence per height (Phase 9, A2 cells)

B9 = p9.load()
REF, TEST_HALF = p9.clock_reference(B9)
CLOCK = {}
for _h in B9:
    _s = p9.clock_lr(B9, _h, REF) if _h >= 1 else None
    CLOCK[_h] = None if _s is None else (_s['inconsistent'], _s['q'], _s['pi'])

_load6, _orates6, _lik6 = p6.load, p6.ordinary_rates, p6.likelihoods


def load():
    blocks, T, E = _load6()
    for h, b in blocks.items():
        c = CLOCK.get(h)
        b['clock'], b['q'], b['pi'] = (None, None, None) if c is None else c
    return blocks, T, E


def ordinary_rates(blocks):
    rates = _orates6(blocks)
    for e, (a, z) in enumerate(p6.ERAS):
        ref = [b for b in blocks.values() if a <= b['height'] <= z and not b['listed'] and not b['band']
               and b['loo_label'] != 'other' and b['clock'] is not None]
        rates[e]['clock_reference_blocks'] = len(ref)
        rates[e]['clock_inconsistent'] = sum(b['clock'] for b in ref) / len(ref)
    return rates


def likelihoods(b, orate, prate, f1, e1):
    lp, lo = _lik6(b, orate, prate, f1, e1)
    if not USE_CLOCK or b.get('clock') is None:
        return lp, lo
    q, r = b['q'], orate['clock_inconsistent']
    return (lp * q, lo * r) if b['clock'] else (lp * (1 - q), lo * (1 - r))


p6.load, p6.ordinary_rates, p6.likelihoods = load, ordinary_rates, likelihoods


def log(line):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'run_log.txt').open('a', encoding='utf8') as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {line}\n")


def save(name, x):
    (OUT / name).write_text(json.dumps(x, indent=1, default=float) + '\n', encoding='utf8')


def write_csv(name, rows):
    with (OUT / name).open('w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- model runs

def fit(clock, setting=p6.SETTINGS[0], hidden=frozenset()):
    global USE_CLOCK
    USE_CLOCK = clock
    blocks, T, E = load()
    for h in hidden:
        blocks[h]['listed'] = False
    orates, prate, pi, f1, e1, post = p6.run(blocks, T, E, setting)
    return blocks, orates, prate, pi, f1, e1, post


def null_rates(clock, blocks, orates, prate, pi, f1, e1):
    """V2: band-passing other_miner blocks from the Phase 9 test half, rescored as dormant and unclustered.
    The clock flag is set explicitly: the likelihood reads it at call time."""
    global USE_CLOCK
    USE_CLOCK = clock
    out = []
    for e, (a, z) in enumerate(p6.ERAS):
        ref = [b for b in blocks.values() if a <= b['height'] <= z and b['loo_label'] == 'other' and b['band']
               and b['height'] in TEST_HALF]
        ps = []
        for b in ref:
            fake = dict(b, spent=False, loo_label='unclustered')
            lp, lo = p6.likelihoods(fake, orates[e], prate, f1[e], e1[e])
            p = pi.get(b['height'] // p6.WINDOW, 1e-6)
            ps.append(p * lp / (p * lp + (1 - p) * lo))
        out.append({'era': [a, z], 'blocks': len(ref), 'p_ge_0_9': round(sum(x >= 0.9 for x in ps) / len(ps), 4),
                    'p_ge_0_5': round(sum(x >= 0.5 for x in ps) / len(ps), 4)})
    return out


def holdout_rates(clock):
    import random
    base = load()[0]
    pool = sorted(h for h, b in base.items() if b['listed'] and b['loo_label'] != 'other')
    hidden = set(random.Random(p6.SEED).sample(pool, int(0.1 * len(pool))))
    post = fit(clock, hidden=hidden)[-1]
    out = []
    for a, z in p6.ERAS:
        hs = [h for h in hidden if a <= h <= z]
        if hs:
            out.append({'era': [a, z], 'hidden': len(hs), 'p_ge_0_9': round(sum(post[h] >= 0.9 for h in hs) / len(hs), 4),
                        'p_ge_0_5': round(sum(post[h] >= 0.5 for h in hs) / len(hs), 4)})
    return out


def shape_calibration(blocks, post, lo=25_000, hi=p6.MAX_HEIGHT):
    """V3: nonce-shape Patoshi fraction per posterior bin, heights lo to hi. The ordinary reference is band-passing
    other-miner blocks at the same heights (amendment A1); the Patoshi reference is Phase 7's 0.477."""
    low = lambda h: (B9[h]['n'] & 255) <= 9
    ref = [h for h, b in blocks.items() if lo <= h <= hi and b['loo_label'] == 'other' and b['band']]
    o_share = sum(low(h) for h in ref) / len(ref)
    cand = [h for h, b in blocks.items() if lo <= h <= hi and not b['listed'] and b['loo_label'] != 'other' and b['band']]
    rows = []
    for lo_, hi_ in ((0, 0.1), (0.1, 0.5), (0.5, 0.9), (0.9, 1.0001)):
        hs = [h for h in cand if lo_ <= post[h] < hi_]
        if not hs:
            continue
        k = sum(low(h) for h in hs)
        wl, wh = p9.wilson(k, len(hs))
        f = lambda s: (s - o_share) / (PATOSHI_SHAPE - o_share)
        mean_p = sum(post[h] for h in hs) / len(hs)
        lo_f, hi_f = max(0.0, f(wl)), min(1.0, f(wh))
        rows.append({'bin': f'{lo_}-{min(hi_, 1)}', 'blocks': len(hs), 'mean_posterior': round(mean_p, 3),
                     'shape_fraction': round(f(k / len(hs)), 3), 'shape_lo': round(lo_f, 3), 'shape_hi': round(hi_f, 3),
                     'inside': lo_f <= mean_p <= hi_f, 'counts_for_V3': len(hs) >= 30})
    return rows, round(o_share, 4), len(ref)


def e1_aggregate():
    """E1: model-free count of unlisted non-stock blocks from the clock alone (Phase 9 estimator)."""
    out = {}
    for name, lo, hi in (('in_span', 3, p6.LIST_END), ('after_list_end', p6.LIST_END + 1, p6.MAX_HEIGHT)):
        hs = [h for h, b in B9.items() if lo <= h <= hi and b['tier'] not in ('listed_uncontradicted', 'listed_contradicted',
                                                                               'other_miner') and CLOCK.get(h)]
        k = sum(CLOCK[h][0] for h in hs)
        n = len(hs)
        qbar = float(np.mean([CLOCK[h][1] for h in hs]))
        wl, wh = p9.wilson(k, n)
        g = lambda r: (r - 0.05) / (qbar - 0.05)
        unscored = sum(1 for h, b in B9.items() if lo <= h <= hi and b['tier'] not in (
            'listed_uncontradicted', 'listed_contradicted', 'other_miner') and not CLOCK.get(h))
        out[name] = {'scored_unlisted_not_other': n, 'unscored': unscored, 'clock_inconsistent': k,
                     'non_stock_blocks': round(g(k / n) * n, 1), 'ci95': [round(max(0, g(wl)) * n, 1), round(g(wh) * n, 1)]}
    p5 = json.loads((ROOT / 'analysis/phase5/census_summary.json').read_text())
    out['phase5_for_comparison'] = {'in_span': [p5['omission_bound']['estimated_omitted'], p5['omission_bound']['estimated_omitted_ci95']],
                                    'after_list_end': [p5['after_list_end']['estimated_omitted'], p5['after_list_end']['estimated_omitted_ci95']]}
    return out


def model():
    log(f"model: PREREGISTRATION.md sha256 {hashlib.sha256(PREREG.read_bytes()).hexdigest()}")
    base = fit(False)
    blocks, orates, prate, pi, f1, e1, post = fit(True)
    grid = [fit(True, s)[-1] for s in p6.SETTINGS[1:]]
    robust = {h: min([post[h]] + [g[h] for g in grid]) for h in blocks}
    p6rows = {int(r['height']): r for r in p8.read(ROOT / 'analysis/phase6/posterior_blocks.csv')}
    # sanity: the clock-off run reproduces the committed Phase 6 primary posterior
    repro = max(abs(base[-1][h] - float(p6rows[h]['posterior'])) for h in blocks)
    rows = []
    for h in sorted(blocks):
        b, r = blocks[h], p6rows[h]
        m = dict(r, posterior=post[h], posterior_min_over_settings=robust[h])
        row = dict(r)                                   # every Phase 6 column, unchanged
        row.update({'clock_pi': '' if b['pi'] is None else round(b['pi'], 4),
                    'clock_inconsistent': '' if b['clock'] is None else b['clock'],
                    'posterior_m10': round(post[h], 5), 'min_over_settings_m10': round(robust[h], 5),
                    'tier_phase8': p8.tier(r), 'tier_m10': p8.tier({k: str(v) for k, v in m.items()})})
        rows.append(row)
    write_csv('posterior_m10.csv', rows)
    tiers = {}
    for r in rows:
        for key in ('tier_phase8', 'tier_m10'):
            tiers.setdefault(r[key], {'tier_phase8': 0, 'tier_m10': 0})[key] += 1
    moved = [{'height': r['height'], 'from': r['tier_phase8'], 'to': r['tier_m10'], 'p6': r['posterior'],
              'm10': r['posterior_m10'], 'min_m10': r['min_over_settings_m10'], 'clock_inconsistent': r['clock_inconsistent']}
             for r in rows if r['tier_phase8'] != r['tier_m10']]
    write_csv('tier_changes.csv', moved)

    def expected(lo, hi, key):
        return round(sum(float(r[key]) for r in rows if lo <= int(r['height']) <= hi and r['listed'] != 'True'
                         and r['co_spend_label'] != 'other'), 1)
    v1_base, v1 = holdout_rates(False), holdout_rates(True)
    v2_base, v2 = null_rates(False, *base[:6]), null_rates(True, blocks, orates, prate, pi, f1, e1)
    v3_pooled, o_pooled, _ = shape_calibration(blocks, post)
    v3 = {name: dict(zip(('bins', 'ordinary_shape_reference', 'ordinary_reference_blocks'), shape_calibration(blocks, post, lo, hi)))
          for name, lo, hi in (('late_span_25000_49973', 25_000, p6.LIST_END), ('tail_49974_54619', p6.LIST_END + 1, p6.MAX_HEIGHT))}
    global USE_CLOCK
    USE_CLOCK = True
    prereg_v1 = {0: 0.975, 1: 0.646}
    v1_pass = all(v1[i]['p_ge_0_9'] >= prereg_v1[i] - 0.02 for i in (0, 1))
    v2_pass = all(v2[i]['p_ge_0_9'] <= v2_base[i]['p_ge_0_9'] for i in range(len(v2)))
    v3_pass = all(r['inside'] for part in v3.values() for r in part['bins'] if r['counts_for_V3'])
    summary = {
        'reproduces_phase6_when_clock_off_max_abs_diff': repro,
        'ordinary_clock_inconsistent_by_era': [round(o['clock_inconsistent'], 4) for o in orates],
        'ordinary_clock_reference_blocks': [o['clock_reference_blocks'] for o in orates],
        'patoshi_track_rates_fitted_m10': [[round(x, 4) for x in e1], [round(x, 4) for x in f1]],
        'expected_unlisted_patoshi': {'in_span_phase6': expected(3, p6.LIST_END, 'posterior'),
                                      'in_span_m10': expected(3, p6.LIST_END, 'posterior_m10'),
                                      'after_end_phase6': expected(p6.LIST_END + 1, p6.MAX_HEIGHT, 'posterior'),
                                      'after_end_m10': expected(p6.LIST_END + 1, p6.MAX_HEIGHT, 'posterior_m10'),
                                      'blocks_1_2_m10': [round(post[1], 4), round(post[2], 4)]},
        'V1_holdout': {'phase6_baseline': v1_base, 'm10': v1, 'preregistered_floor': prereg_v1, 'pass': v1_pass},
        'V2_null_test_half': {'phase6_baseline': v2_base, 'm10': v2, 'pass': v2_pass},
        'V3_shape_calibration': {'by_range': v3, 'patoshi_shape_reference': PATOSHI_SHAPE, 'pass': v3_pass,
                                 'first_run_pooled_superseded_by_A1': {'ordinary_shape_reference': o_pooled, 'bins': v3_pooled}},
        'adopted_as_calibrated': v1_pass and v2_pass and v3_pass,
        'tiers': tiers, 'tier_changes': len(moved),
        'E1_model_free_aggregate': e1_aggregate(),
    }
    save('model_summary.json', summary)
    log(f"model: V1 {v1_pass} V2 {v2_pass} V3 {v3_pass}; adopted {summary['adopted_as_calibrated']}")
    print(json.dumps(summary, indent=1, default=float))


# ---------------------------------------------------------------- section 4: suspects

def suspects():
    log(f"suspects: PREREGISTRATION.md sha256 {hashlib.sha256(PREREG.read_bytes()).hexdigest()}")
    blocks, orates, *_ = fit(True)
    p6rows = {int(r['height']): r for r in p8.read(ROOT / 'analysis/phase6/posterior_blocks.csv')}
    listed = [h for h, b in B9.items() if b['tier'] == 'listed_uncontradicted' and CLOCK.get(h)]
    trackless = [h for h in listed if p6rows[h]['track_fit'] != 'True']
    fitted = [h for h in listed if p6rows[h]['track_fit'] == 'True']
    sus = [h for h in trackless if not CLOCK[h][0]]
    exp_consistent = sum(1 - CLOCK[h][1] for h in trackless)
    r_o = float(np.mean([orates[p6.era_of(h)]['clock_inconsistent'] for h in trackless]))
    wl, wh = p9.wilson(len(sus), len(trackless))
    m = (len(sus) - exp_consistent) / (1 - r_o)
    m_ci = [round((wl * len(trackless) - exp_consistent) / (1 - r_o), 1), round((wh * len(trackless) - exp_consistent) / (1 - r_o), 1)]
    # (a) spending
    spend_rate = [1 - o['unspent'] for o in orates]
    spent = [h for h in sus if blocks[h]['spent']]
    listed_spend = sum(blocks[h]['spent'] for h in listed) / len(listed)
    exp_fp = sum(spend_rate[p6.era_of(h)] for h in sus) / len(sus) * max(m, 0)
    exp_h0 = listed_spend * len(sus)
    # Poisson tail probabilities for the observed count under each hypothesis
    pois_le = lambda k, lam: sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k + 1))
    a = {'suspects': len(sus), 'spent': len(spent), 'spent_heights': spent, 'expected_if_m_false_positives': round(exp_fp, 2),
         'expected_if_no_excess': round(exp_h0, 3), 'p_observed_or_fewer_under_H_FP': pois_le(len(spent), exp_fp),
         'p_observed_or_more_under_H0': 1 - pois_le(len(spent) - 1, exp_h0) if spent else 1.0}
    # (b) nonce shape, h >= 25,000
    inband = lambda hs: [(B9[h]['n'] & 255) <= 9 for h in hs if h >= 25_000]
    xs, xf = inband(sus), inband(fitted)
    b_ = {'suspects_in_band': len(xs), 'suspects_low': sum(xs), 'suspects_share': round(sum(xs) / len(xs), 3) if xs else None,
          'fitted_in_band': len(xf), 'fitted_low': sum(xf), 'fitted_share': round(sum(xf) / len(xf), 3),
          'fisher_p': p9.fisher_two_sided(sum(xs), len(xs) - sum(xs), sum(xf), len(xf) - sum(xf)) if xs else None}
    # (c) dead time
    L = sorted(h for h, b in B9.items() if b['tier'] in ('listed_uncontradicted', 'listed_contradicted'))
    prev = {b: a for a, b in zip(L, L[1:])}
    def dead(hs):
        ok = [h for h in hs if h >= 5000 and not 1400 <= h <= 1916 and h in prev]
        v = [B9[h]['t'] - B9[prev[h]]['t'] < 300 for h in ok]
        return len(v), sum(v)
    ns, ks = dead(sus)
    nf, kf = dead(fitted)
    c = {'suspects': ns, 'suspects_under_300s': ks, 'fitted': nf, 'fitted_under_300s': kf,
         'fisher_p': p9.fisher_two_sided(ks, ns - ks, kf, nf - kf)}
    signals = [a['p_observed_or_more_under_H0'] < 0.01, (b_['fisher_p'] or 1) < 0.01 and b_['suspects_share'] < b_['fitted_share'],
               c['fisher_p'] < 0.01 and ks / max(ns, 1) > kf / max(nf, 1)]
    out = {'trackless_listed_scored': len(trackless), 'clock_consistent_suspects': len(sus),
           'expected_consistent_if_all_patoshi': round(exp_consistent, 1),
           'clock_only_false_positive_estimate_m': round(m, 1), 'm_ci95': m_ci,
           'a_spending': a, 'b_shape': b_, 'c_dead_time': c,
           'excess_false_positives_claimed': sum(signals) >= 2}
    write_csv('suspects.csv', [{'height': h, 'clock_pi': round(CLOCK[h][2], 4), 'track_fit': p6rows[h]['track_fit'],
                                'spent': blocks[h]['spent'], 'nonce_low_byte': B9[h]['n'] & 255,
                                'gap_to_previous_listed_s': B9[h]['t'] - B9[prev[h]]['t'] if h in prev else ''} for h in sus])
    save('suspects_summary.json', out)
    log(f"suspects: claimed={out['excess_false_positives_claimed']}")
    print(json.dumps(out, indent=1, default=float))


def manifest():
    digest = lambda f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
    inputs = ['analysis/phase2_bigquery/results/headers.csv', 'analysis/phase5/census_blocks.csv',
              'analysis/phase5/census_summary.json', 'analysis/phase6/posterior_blocks.csv', 'analysis/phase8/revised_list.csv']
    outputs = sorted(f.relative_to(ROOT).as_posix() for f in OUT.iterdir() if f.suffix in ('.csv', '.json') and f.name != 'manifest.json')
    scripts = ['scripts/phase10_clock_model.py', 'scripts/phase6_posterior.py', 'scripts/phase9_nonce_clock.py',
               'analysis/phase10_clock_model/PREREGISTRATION.md']
    (OUT / 'manifest.json').write_text(json.dumps({'inputs': {f: digest(f) for f in inputs}, 'outputs': {f: digest(f) for f in outputs},
                                                   'scripts': {f: digest(f) for f in scripts}}, indent=1) + '\n', encoding='utf8')
    print('done manifest')


if __name__ == '__main__':
    cmds = {'model': model, 'suspects': suspects, 'manifest': manifest}
    for c in sys.argv[1:] or ['model', 'suspects', 'manifest']:
        cmds[c]()
