"""Phase 9: does Patoshi's nonce encode the time since the parent block? (the "nonce clock")

    python scripts/phase9_nonce_clock.py primary            # preregistered T0 (positive control) and T1 (primary)
    python scripts/phase9_nonce_clock.py power amendment    # A1.1 power, A1.2/A1.3 continuation tests
    python scripts/phase9_nonce_clock.py clock update       # A2 clock check by tier, A3 per-block ranking
    python scripts/phase9_nonce_clock.py stress clock_sensitivity
    python scripts/phase9_nonce_clock.py assembly           # A4 block-assembly order (needs results/block_transactions.csv)
    python scripts/phase9_nonce_clock.py exploratory live manifest

S1 to S3 were preregistered as conditional on T1 succeeding. T1 failed, so they are not run (see A1).

Offline. Reads only committed headers (Phase 2) and tiers (Phase 8). Definitions follow
analysis/phase9_nonce_clock/PREREGISTRATION.md exactly.
"""
import csv, hashlib, json, math, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase9_nonce_clock'
RES = OUT / 'results'
HEADERS = ROOT / 'analysis/phase2_bigquery/results/headers.csv'
TIERS = ROOT / 'analysis/phase8/revised_list.csv'
PREREG = OUT / 'PREREGISTRATION.md'

P = 163_840_000                      # Lerner's subrange width in the reversed nonce
SUB_LO = [0, 2 * P, 3 * P, 4 * P, 5 * P]
NON_PATOSHI_PARENT = {'other_miner', 'no_patoshi_evidence'}
SHORT, LONG = (0, 60), (600, 3600)
SEED = 20260928
DIFF1_END = 32_255                   # last height at difficulty 1 (difficulty 2 from 40,320; see note in secondary)


def read(p):
    with p.open(newline='', encoding='utf8') as f:
        return list(csv.DictReader(f))


def bswap32(n):
    return int.from_bytes(n.to_bytes(4, 'little'), 'big')


def subrange(r):
    for lo in SUB_LO:
        if lo <= r < lo + P:
            return lo
    return None


def u_in(r):
    lo = subrange(r)
    return None if lo is None else (lo + P - 1 - r) / P


def u_ip(r):
    lo = subrange(r)
    return None if lo is None else (r - lo) / P


def u_s(n):
    return (n - 1) / 2 ** 32


def load():
    tiers = {int(r['height']): r['tier'] for r in read(TIERS)}
    blocks = {}
    for r in read(HEADERS):
        h = int(r['height'])
        t = datetime.strptime(r['timestamp'].replace('+00', ''), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        n = int(r['nonce'], 16)
        blocks[h] = {'h': h, 't': int(t.timestamp()), 'n': n, 'r': bswap32(n), 'tier': tiers[h],
                     'txs': int(r['transaction_count']), 'hash': r['block_hash']}
    for h in range(1, len(blocks)):
        blocks[h]['dt'] = blocks[h]['t'] - blocks[h - 1]['t']
        blocks[h]['ptier'] = blocks[h - 1]['tier']
    return blocks


def mw_less(x, y):
    """One-sided Mann-Whitney, alternative: x stochastically smaller than y. Normal approximation with
    tie correction. Returns dict with n, medians, z, one-sided p and the common-language effect P(x<y)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n1, n2 = len(x), len(y)
    allv = np.concatenate([x, y])
    order = np.argsort(allv, kind='mergesort')
    ranks = np.empty(len(allv))
    sv = allv[order]
    i = 0
    ties = 0.0
    while i < len(sv):
        j = i
        while j < len(sv) and sv[j] == sv[i]:
            j += 1
        ranks[order[i:j]] = (i + j + 1) / 2
        ties += (j - i) ** 3 - (j - i)
        i = j
    u = ranks[:n1].sum() - n1 * (n1 + 1) / 2
    n = n1 + n2
    var = n1 * n2 / 12 * ((n + 1) - ties / (n * (n - 1)))
    z = (u - n1 * n2 / 2) / math.sqrt(var)
    p = 0.5 * math.erfc(-z / math.sqrt(2))
    return {'n_short': n1, 'n_long': n2, 'median_short': round(float(np.median(x)), 4),
            'median_long': round(float(np.median(y)), 4), 'z': round(z, 3), 'p_one_sided': p,
            'P_short_below_long': round(1 - u / (n1 * n2), 4)}


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - k) * ps[i]))
        adj[i] = run
    return adj


def groups(blocks, child, parent=NON_PATOSHI_PARENT, lo=1, hi=54_619, exclude=()):
    return [b for h, b in blocks.items() if lo <= h <= hi and h not in exclude and b['tier'] in child
            and b.get('ptier') in parent]


def split(bs, f, short=SHORT, long=LONG):
    s = [f(b) for b in bs if short[0] <= b['dt'] <= short[1] and f(b) is not None]
    l = [f(b) for b in bs if long[0] <= b['dt'] <= long[1] and f(b) is not None]
    return s, l


def log(line):
    RES.mkdir(parents=True, exist_ok=True)
    with (RES / 'run_log.txt').open('a', encoding='utf8') as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {line}\n")


def save(name, obj):
    RES.mkdir(parents=True, exist_ok=True)
    (RES / name).write_text(json.dumps(obj, indent=1, default=float) + '\n', encoding='utf8')


# ---------------------------------------------------------------- primary

def primary():
    log(f"primary: PREREGISTRATION.md sha256 {hashlib.sha256(PREREG.read_bytes()).hexdigest()}")
    B = load()
    cs = groups(B, {'other_miner'})
    cp = groups(B, {'listed_uncontradicted'})
    t0 = mw_less(*split(cs, lambda b: u_s(b['n'])))
    outside = sum(1 for b in cp if subrange(b['r']) is None)
    t1_in = mw_less(*split(cp, lambda b: u_in(b['r'])))
    t1_ip = mw_less(*split(cp, lambda b: u_ip(b['r'])))
    adj = holm([t1_in['p_one_sided'], t1_ip['p_one_sided']])
    t0_ok = t0['p_one_sided'] < 1e-6
    success = t0_ok and adj[0] < 0.01 and t1_in['median_short'] < t1_in['median_long']
    failure = t0_ok and t1_in['p_one_sided'] >= 0.05 and t1_ip['p_one_sided'] >= 0.05
    verdict = ('success: reset supported' if success else 'failure: reset not supported' if failure
               else 'positive control failed: not interpretable' if not t0_ok
               else 'wrong direction (IP only)' if adj[1] < 0.01 and adj[0] >= 0.01 else 'inconclusive')
    out = {'groups': {'C_S_positive_control': len(cs), 'C_P_patoshi_after_non_patoshi': len(cp),
                      'C_P_outside_subranges_excluded': outside},
           'T0_positive_control_stock_u_S': t0,
           'T1_primary_u_IN': dict(t1_in, p_holm=adj[0]),
           'T1_alternative_u_IP': dict(t1_ip, p_holm=adj[1]),
           'verdict': verdict}
    save('primary.json', out)
    log(f"primary verdict: {verdict}")
    print(json.dumps(out, indent=1, default=float))


# ---------------------------------------------------------------- amendment A1

def power():
    """A1.1: smallest reset fraction f that T1 would detect at 80% power."""
    B = load()
    cp = [b for b in groups(B, {'listed_uncontradicted'})
          if (SHORT[0] <= b['dt'] <= SHORT[1] or LONG[0] <= b['dt'] <= LONG[1])]
    dt = np.array([b['dt'] for b in cp], float)
    u0 = np.array([u_in(b['r']) for b in cp])
    short = dt <= SHORT[1]
    rng = np.random.default_rng(SEED)
    rows = []
    for sigma in (0, 30, 60):
        for T in (30, 60, 120, 188, 300):
            for f in (0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0):
                hits = 0
                for _ in range(400):
                    u = u0.copy()
                    m = rng.random(len(u)) < f
                    top = np.clip(np.maximum(dt + rng.normal(0, sigma, len(u)) if sigma else dt, 1) / T, 0, 1)
                    u[m] = rng.random(m.sum()) * top[m]
                    hits += mw_less(u[short], u[~short])['p_one_sided'] < 0.005   # Holm first step at 0.01/2
                rows.append({'sigma_s': sigma, 'T_s': T, 'reset_fraction': f, 'power': hits / 400})
    with (RES / 'power.csv').open('w', newline='', encoding='utf8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    mins = {}
    for r in rows:
        k = f"sigma={r['sigma_s']},T={r['T_s']}"
        if r['power'] >= 0.8 and k not in mins:
            mins[k] = r['reset_fraction']
    save('power_summary.json', {'min_reset_fraction_at_80pct_power': mins, 'simulations_per_cell': 400,
                                'alpha_one_sided': 0.005})
    print(json.dumps(mins, indent=1))


def extranonces():
    return {int(r['height']): int(r['extra_nonce']) for r in read(ROOT / 'analysis/phase3/coinbase_encoding.csv')}


def listed_pairs(B, f=u_in, same_sub=False, tmax=3600):
    en = extranonces()
    L = sorted(h for h, b in B.items() if b['tier'] == 'listed_uncontradicted')
    out = []
    for a, b in zip(L, L[1:]):
        tau = B[b]['t'] - B[a]['t']
        if not (0 < tau <= tmax) or en[b] < en[a]:
            continue
        ua, ub = f(B[a]['r']), f(B[b]['r'])
        if ua is None or ub is None:
            continue
        if same_sub and subrange(B[a]['r']) != subrange(B[b]['r']):
            continue
        out.append({'a': a, 'b': b, 'tau': tau, 'du': (ub - ua) % 1.0, 'den': en[b] - en[a],
                    'era': a // 5000, 'sub_a': subrange(B[a]['r']), 'sub_b': subrange(B[b]['r'])})
    return out


T_GRID = np.arange(20, 2000.5, 0.5)


def rayleigh_scan(du, tau, perms=None):
    """R(T) = |mean exp(2 pi i (du - tau/T))| over T_GRID; rows of perms are permuted du vectors."""
    E = np.exp(-2j * np.pi * np.outer(tau, 1 / T_GRID)).astype(np.complex64)     # n x F
    W = np.exp(2j * np.pi * (du if perms is None else perms)).astype(np.complex64)
    W = W[None, :] if W.ndim == 1 else W
    return np.abs(W @ E) / len(du)


def continuation(name, f, same_sub, n_perm=999):
    B = load()
    pr = listed_pairs(B, f, same_sub)
    du = np.array([p['du'] for p in pr])
    tau = np.array([p['tau'] for p in pr], float)
    era = np.array([p['era'] for p in pr])
    R = rayleigh_scan(du, tau)[0]
    k = int(np.argmax(R))
    rng = np.random.default_rng(SEED)
    maxes = []
    for start in range(0, n_perm, 50):
        batch = []
        for _ in range(min(50, n_perm - start)):
            d = du.copy()
            for e in np.unique(era):
                idx = np.where(era == e)[0]
                d[idx] = d[rng.permutation(idx)]
            batch.append(d)
        maxes.extend(rayleigh_scan(du, tau, np.array(batch)).max(axis=1).tolist())
    p = (1 + sum(m >= R[k] for m in maxes)) / (n_perm + 1)
    top = sorted(range(len(R)), key=lambda i: -R[i])[:5]
    res = {'variant': name, 'pairs': len(pr), 'best_T_s': float(T_GRID[k]), 'R_max': float(R[k]),
           'perm_p': p, 'null_R_max_median': float(np.median(maxes)), 'null_R_max_99pct': float(np.percentile(maxes, 99)),
           'top5_T': [float(T_GRID[i]) for i in top], 'top5_R': [round(float(R[i]), 4) for i in top],
           'expected_R_if_uniform': round(1 / math.sqrt(len(pr)), 4)}
    np.save(RES / f'rayleigh_{name}.npy', R)
    return res


def amendment():
    RES.mkdir(parents=True, exist_ok=True)
    log(f"amendment A1: PREREGISTRATION.md sha256 {hashlib.sha256(PREREG.read_bytes()).hexdigest()}")
    res = [continuation('all_pairs_IN', u_in, False), continuation('all_pairs_IP', u_ip, False),
           continuation('same_subrange_IN', u_in, True)]
    ps = [r['perm_p'] for r in res]
    dir_adj = holm(ps[:2])
    sub_adj = holm([ps[0], ps[2]])
    res[0]['p_holm_direction'], res[1]['p_holm_direction'] = dir_adj
    res[0]['p_holm_vs_same_subrange'], res[2]['p_holm_vs_same_subrange'] = sub_adj
    ok = min(dir_adj) < 0.001
    fail = all(p >= 0.05 for p in ps[:2])
    res.append({'A1.2_verdict': 'success: lockstep continuation supported' if ok else
                'failure: no phase continuation' if fail else 'inconclusive'})
    save('continuation.json', res)
    log(f"amendment A1.2 verdict: {res[-1]}")
    print(json.dumps(res, indent=1))


# ---------------------------------------------------------------- amendment A2: stock nonce clock vs tiers

ERAS = [(0, 24_999), (25_000, 49_973), (49_974, 54_619)]
DT_EDGES = [0, 30, 60, 120, 300, 600, 1200, 3600, float('inf')]
MIN_REF = 20


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def cell(b):
    if b.get('dt') is None or b['dt'] < 0:
        return None
    e = next(i for i, (lo, hi) in enumerate(ERAS) if lo <= b['h'] <= hi)
    k = next(i for i in range(len(DT_EDGES) - 1) if DT_EDGES[i] <= b['dt'] < DT_EDGES[i + 1])
    return (e, k)


def clock_check():
    B = load()
    rng = np.random.default_rng(SEED)
    other = sorted(h for h, b in B.items() if b['tier'] == 'other_miner' and h >= 1)
    mask = rng.random(len(other)) < 0.5
    ref_h = {h for h, m in zip(other, mask) if m}
    test_h = set(other) - ref_h
    ref = {}
    for h in ref_h:
        c = cell(B[h])
        if c is not None:
            ref.setdefault(c, []).append(u_s(B[h]['n']))
    ref = {c: np.sort(v) for c, v in ref.items()}
    q95 = {c: float(np.quantile(v, 0.95)) for c, v in ref.items() if len(v) >= MIN_REF}

    def score(h):
        c = cell(B[h])
        if c is None or c not in q95:
            return None
        v = ref[c]
        u = u_s(B[h]['n'])
        pi = (len(v) - np.searchsorted(v, u, side='left')) / len(v)
        return {'pi': float(pi), 'q': 1 - q95[c], 'cell': c}

    def by(tier, span=None):
        hs = [h for h, b in B.items() if h >= 1 and b['tier'] == tier]
        if span == 'in':
            hs = [h for h in hs if h <= 49_973]
        elif span == 'after':
            hs = [h for h in hs if h > 49_973]
        return hs

    groups_ = {'other_miner_test_half (negative control)': sorted(test_h),
               'listed_uncontradicted (positive control)': by('listed_uncontradicted'),
               'listed_contradicted': by('listed_contradicted'),
               'added_robust_in_span': by('added_robust', 'in'), 'added_robust_after_49973': by('added_robust', 'after'),
               'added_probable_in_span': by('added_probable', 'in'), 'added_probable_after_49973': by('added_probable', 'after'),
               'added_possible': by('added_possible'), 'unresolved': by('unresolved'),
               'no_patoshi_evidence': by('no_patoshi_evidence')}
    rows, per_block = [], []
    for name, hs in groups_.items():
        sc = [(h, score(h)) for h in hs]
        sc = [(h, s) for h, s in sc if s is not None]
        n = len(sc)
        k = sum(s['pi'] < 0.05 for _, s in sc)
        qbar = float(np.mean([s['q'] for _, s in sc])) if n else float('nan')
        lo, hi = wilson(k, n)
        g = lambda r: (r - 0.05) / (qbar - 0.05)
        rows.append({'group': name, 'blocks': len(hs), 'scored': n, 'clock_inconsistent': k,
                     'rate': round(k / n, 4) if n else '', 'rate_lo': round(lo, 4), 'rate_hi': round(hi, 4),
                     'q_bar_uniform': round(qbar, 4), 'g_unclamped': round(g(k / n), 3) if n else '',
                     'g': round(min(1, max(0, g(k / n))), 3) if n else '',
                     'g_lo': round(min(1, max(0, g(lo))), 3), 'g_hi': round(min(1, max(0, g(hi))), 3)})
        if name in ('listed_contradicted', 'added_robust_after_49973', 'added_robust_in_span'):
            for h, s in sc:
                per_block.append({'group': name, 'height': h, 'dt_s': B[h]['dt'], 'nonce': B[h]['n'],
                                  'u_S': round(u_s(B[h]['n']), 5), 'pi_stock': round(s['pi'], 4),
                                  'u_IN': round(u_in(B[h]['r']), 4) if u_in(B[h]['r']) is not None else ''})
    for name, data in (('clock_check_groups.csv', rows), ('clock_check_blocks.csv', per_block)):
        with (RES / name).open('w', newline='', encoding='utf8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]), lineterminator='\n')
            w.writeheader()
            w.writerows(data)
    neg = rows[0]
    pos = rows[1]
    tail = next(r for r in rows if r['group'] == 'added_robust_after_49973')
    contra = next(r for r in rows if r['group'] == 'listed_contradicted')
    valid = neg['g_lo'] == 0 and pos['g_lo'] > 0.8
    summary = {'valid': valid, 'tail_confirmed': valid and tail['g_lo'] > 0.5,
               'contradicted_interval_contains_0': contra['g_lo'] == 0,
               'reference_blocks': len(ref_h), 'test_blocks': len(test_h),
               'cells_with_reference': len(q95)}
    save('clock_check_summary.json', {'summary': summary, 'groups': rows})
    log(f"A2 clock check: {summary}")
    for r in rows:
        print(r)
    print(summary)


# ---------------------------------------------------------------- amendment A3: per-block update

def fisher_two_sided(a, b, c, d):
    """Two-sided Fisher exact p for the table [[a, b], [c, d]] (log space)."""
    n1, n2, m = a + b, c + d, a + c
    lf = lambda x: math.lgamma(x + 1)
    def lp(x):
        return lf(n1) - lf(x) - lf(n1 - x) + lf(n2) - lf(m - x) - lf(n2 - m + x) - (lf(n1 + n2) - lf(m) - lf(n1 + n2 - m))
    lo, hi = max(0, m - n2), min(n1, m)
    obs = lp(a)
    return min(1.0, sum(math.exp(lp(x)) for x in range(lo, hi + 1) if lp(x) <= obs + 1e-9))


def clock_reference(B, exclude_era=None):
    rng = np.random.default_rng(SEED)
    other = sorted(h for h, b in B.items() if b['tier'] == 'other_miner' and h >= 1)
    mask = rng.random(len(other)) < 0.5
    ref_h = [h for h, m in zip(other, mask) if m]
    ref = {}
    for h in ref_h:
        c = cell(B[h])
        if c is None:
            continue
        key = c if exclude_era is None else c[1]
        if exclude_era is not None and c[0] == exclude_era:
            continue
        ref.setdefault(key, []).append(u_s(B[h]['n']))
    ref = {c: np.sort(v) for c, v in ref.items() if len(v) >= MIN_REF}
    return ref, set(other) - set(ref_h)


def clock_lr(B, h, ref, pooled=False):
    c = cell(B[h])
    if c is None:
        return None
    key = c[1] if pooled else c
    if key not in ref:
        return None
    v = ref[key]
    q = 1 - float(np.quantile(v, 0.95))
    u = u_s(B[h]['n'])
    pi = (len(v) - np.searchsorted(v, u, side='left')) / len(v)
    inc = pi < 0.05
    return {'pi': float(pi), 'q': q, 'inconsistent': inc, 'lr': q / 0.05 if inc else (1 - q) / 0.95}


UPDATE_TIERS = ['added_robust', 'added_probable', 'added_possible', 'unresolved', 'no_patoshi_evidence']


def update():
    B = load()
    post = {int(r['height']): r for r in read(ROOT / 'analysis/phase6/posterior_blocks.csv')}
    ref, test_h = clock_reference(B)
    # independence checks
    band = {h: post[h]['band'] == 'True' for h in post}
    om = [(band[h], clock_lr(B, h, ref)) for h in test_h if h in post]
    om = [(bd, s['inconsistent']) for bd, s in om if s]
    a = sum(1 for bd, i in om if bd and i); b_ = sum(1 for bd, i in om if bd and not i)
    c = sum(1 for bd, i in om if not bd and i); d = sum(1 for bd, i in om if not bd and not i)
    chk1 = {'band_pass_inconsistent': a, 'band_pass_n': a + b_, 'band_fail_inconsistent': c, 'band_fail_n': c + d,
            'rate_pass': round(a / (a + b_), 4), 'rate_fail': round(c / (c + d), 4), 'fisher_p': fisher_two_sided(a, b_, c, d)}
    li = [(post[h]['track_fit'] == 'True', clock_lr(B, h, ref)) for h, b in B.items()
          if b['tier'] == 'listed_uncontradicted' and h in post]
    li = [(t, s['inconsistent']) for t, s in li if s]
    a = sum(1 for t, i in li if t and i); b_ = sum(1 for t, i in li if t and not i)
    c = sum(1 for t, i in li if not t and i); d = sum(1 for t, i in li if not t and not i)
    chk2 = {'track_fit_inconsistent': a, 'track_fit_n': a + b_, 'no_fit_inconsistent': c, 'no_fit_n': c + d,
            'rate_fit': round(a / (a + b_), 4) if a + b_ else '', 'rate_no_fit': round(c / (c + d), 4) if c + d else '',
            'fisher_p': fisher_two_sided(a, b_, c, d) if (a + b_) and (c + d) else ''}
    valid = chk1['fisher_p'] > 0.01 and (chk2['fisher_p'] == '' or chk2['fisher_p'] > 0.01)
    rows, named, tiers = [], [], {}
    for h, b in sorted(B.items()):
        if b['tier'] not in UPDATE_TIERS or h not in post:
            continue
        p0 = min(1 - 1e-6, max(1e-6, float(post[h]['posterior'])))
        s = clock_lr(B, h, ref)
        p1 = p0 if s is None else (p0 / (1 - p0) * s['lr']) / (1 + p0 / (1 - p0) * s['lr'])
        t = tiers.setdefault(b['tier'], {'blocks': 0, 'scored': 0, 'expected_before': 0.0, 'expected_after': 0.0,
                                         'p_ge_0_9_before': 0, 'p_ge_0_9_after': 0})
        t['blocks'] += 1
        t['scored'] += s is not None
        t['expected_before'] += p0
        t['expected_after'] += p1
        t['p_ge_0_9_before'] += p0 >= 0.9
        t['p_ge_0_9_after'] += p1 >= 0.9
        row = {'height': h, 'tier': b['tier'], 'phase6_p': round(p0, 5), 'dt_s': b['dt'], 'nonce': b['n'],
               'u_S': round(u_s(b['n']), 5), 'pi_stock': round(s['pi'], 4) if s else '',
               'clock_lr': round(s['lr'], 3) if s else '', 'updated_p': round(p1, 5)}
        rows.append(row)
        if p1 >= 0.9 and p0 < 0.9:
            named.append(row)
    for t in tiers.values():
        t['expected_before'] = round(t['expected_before'], 1)
        t['expected_after'] = round(t['expected_after'], 1)
    for name, data in (('updated_posterior.csv', rows), ('named_by_clock.csv', named)):
        with (RES / name).open('w', newline='', encoding='utf8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n')
            w.writeheader()
            w.writerows(data)
    # leave-own-era-out for the tail: pooled-bin reference built from eras 0 and 1 only
    ref_lo, _ = clock_reference(B, exclude_era=2)
    tail = [h for h, b in B.items() if h > 49_973 and b['tier'] in ('added_robust', 'added_probable')]
    sc = [clock_lr(B, h, ref_lo, pooled=True) for h in tail]
    sc = [s for s in sc if s]
    loo = {'tail_blocks_scored': len(sc), 'inconsistent': sum(s['inconsistent'] for s in sc),
           'rate': round(sum(s['inconsistent'] for s in sc) / len(sc), 4),
           'q_bar': round(float(np.mean([s['q'] for s in sc])), 4)}
    om_tail = [clock_lr(B, h, ref_lo, pooled=True) for h in test_h if h > 49_973]
    om_tail = [s for s in om_tail if s]
    loo['other_miner_tail_test_half_rate'] = round(sum(s['inconsistent'] for s in om_tail) / len(om_tail), 4)
    loo['other_miner_tail_test_half_n'] = len(om_tail)
    out = {'independence_check_i_other_miner_band': chk1, 'independence_check_ii_listed_track': chk2,
           'valid_for_probabilities': valid, 'by_tier': tiers, 'named_by_clock': len(named),
           'named_by_clock_by_tier': {t: sum(1 for r in named if r['tier'] == t) for t in UPDATE_TIERS},
           'tail_leave_own_era_out': loo}
    save('update_summary.json', out)
    log(f"A3 update: valid={valid}, named={len(named)}")
    print(json.dumps(out, indent=1, default=float))


# ---------------------------------------------------------------- stress tests (declared in section 5)

def stress():
    B = load()
    rows = []

    def run(name, child=frozenset({'listed_uncontradicted'}), parent=NON_PATOSHI_PARENT, lo=1, hi=54_619,
            exclude=(), short=SHORT, long=LONG):
        cp = groups(B, set(child), set(parent), lo, hi, exclude)
        t = mw_less(*split(cp, lambda b: u_in(b['r']), short, long))
        cs = groups(B, {'other_miner'}, set(parent), lo, hi, exclude)
        c = mw_less(*split(cs, lambda b: u_s(b['n']), short, long)) if cs else None
        rows.append({'variant': name, 'n_short': t['n_short'], 'n_long': t['n_long'], 'median_short': t['median_short'],
                     'median_long': t['median_long'], 'z': t['z'], 'p_one_sided': t['p_one_sided'],
                     'control_z': c['z'] if c else '', 'control_p': c['p_one_sided'] if c else ''})

    run('primary (as preregistered)')
    run('era h < 18,000', hi=17_999)
    run('era 18,000 to 32,255', lo=18_000, hi=32_255)
    run('era h >= 32,256', lo=32_256)
    run('double helix 1,400 to 1,916 excluded', exclude=set(range(1400, 1917)))
    run('parent co-spend other_miner only', parent={'other_miner'})
    run('short gap 0 to 30 s', short=(0, 30))
    run('short gap 0 to 120 s', short=(0, 120))
    run('child adds the 12 listed_contradicted', child={'listed_uncontradicted', 'listed_contradicted'})
    ps = [r['p_one_sided'] for r in rows[1:]]
    for r, a in zip(rows[1:], holm(ps)):
        r['p_holm_over_variants'] = a
    rows[0]['p_holm_over_variants'] = ''
    # permutation null for T1: shuffle dt within era among C_P, recompute z
    cp = groups(B, {'listed_uncontradicted'})
    dt = np.array([b['dt'] for b in cp], float)
    u = np.array([u_in(b['r']) for b in cp])
    era = np.array([b['h'] // 5000 for b in cp])
    rng = np.random.default_rng(SEED)
    z_obs = rows[0]['z']
    zs = []
    for _ in range(999):
        d = dt.copy()
        for e in np.unique(era):
            idx = np.where(era == e)[0]
            d[idx] = d[rng.permutation(idx)]
        s = (d >= SHORT[0]) & (d <= SHORT[1])
        l = (d >= LONG[0]) & (d <= LONG[1])
        zs.append(mw_less(u[s], u[l])['z'])
    perm_p = (1 + sum(z <= z_obs for z in zs)) / 1000
    with (RES / 'stress_primary.csv').open('w', newline='', encoding='utf8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    save('stress_permutation.json', {'z_observed': z_obs, 'perm_p_one_sided': perm_p, 'permutations': 999})
    for r in rows:
        print(r)
    print('permutation p', perm_p)


def clock_sensitivity():
    """A2 at alternative inconsistency thresholds (0.01, 0.10): g per key group."""
    B = load()
    ref, test_h = clock_reference(B)
    out = []
    keys = {'other_miner_test_half': sorted(test_h),
            'listed_uncontradicted': [h for h, b in B.items() if b['tier'] == 'listed_uncontradicted'],
            'listed_contradicted': [h for h, b in B.items() if b['tier'] == 'listed_contradicted'],
            'added_robust_after_49973': [h for h, b in B.items() if b['tier'] == 'added_robust' and h > 49_973],
            'unresolved': [h for h, b in B.items() if b['tier'] == 'unresolved'],
            'no_patoshi_evidence': [h for h, b in B.items() if b['tier'] == 'no_patoshi_evidence' and h >= 1]}
    for thr in (0.01, 0.05, 0.10):
        for name, hs in keys.items():
            sc = []
            for h in hs:
                c = cell(B[h])
                if c is None or c not in ref:
                    continue
                v = ref[c]
                pi = (len(v) - np.searchsorted(v, u_s(B[h]['n']), side='left')) / len(v)
                sc.append((pi < thr, 1 - float(np.quantile(v, 1 - thr))))
            n = len(sc)
            k = sum(i for i, _ in sc)
            q = float(np.mean([x for _, x in sc]))
            lo, hi = wilson(k, n)
            g = lambda r: min(1, max(0, (r - thr) / (q - thr)))
            out.append({'threshold': thr, 'group': name, 'scored': n, 'inconsistent': k, 'g': round(g(k / n), 3),
                        'g_lo': round(g(lo), 3), 'g_hi': round(g(hi), 3)})
    with (RES / 'clock_sensitivity.csv').open('w', newline='', encoding='utf8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(out)
    for r in out:
        print(r)


# ---------------------------------------------------------------- A4, gap 2: block-assembly order

def merkle_root(txids_display):
    layer = [bytes.fromhex(t)[::-1] for t in txids_display]
    d2 = lambda b: hashlib.sha256(hashlib.sha256(b).digest()).digest()
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [d2(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
    return layer[0][::-1].hex()


def stock_order(txs, parents):
    """Passes over txids in ascending displayed-hex order; add a tx once its in-block parents are added."""
    remaining, done, order = sorted(txs), set(), []
    while remaining:
        progressed, rest = False, []
        for t in remaining:
            if all(p in done or p not in txs for p in parents[t]):
                order.append(t)
                done.add(t)
                progressed = True
            else:
                rest.append(t)
        if not progressed:
            return None
        remaining = rest
    return order


def valid_orders(txs, parents):
    """Number of orders of txs in which every in-block parent precedes its child (subset DP; None above 20)."""
    ids = sorted(txs)
    n = len(ids)
    if n > 20:
        return None
    idx = {t: i for i, t in enumerate(ids)}
    pm = [sum(1 << idx[q] for q in set(parents[t]) if q in idx) for t in ids]
    memo = {(1 << n) - 1: 1}

    def f(mask):
        if mask not in memo:
            memo[mask] = sum(f(mask | 1 << i) for i in range(n) if not mask >> i & 1 and pm[i] & mask == pm[i])
        return memo[mask]
    return f(0)


def assembly():
    log(f"A4 assembly: PREREGISTRATION.md sha256 {hashlib.sha256(PREREG.read_bytes()).hexdigest()}")
    B = load()
    hdr = {int(r['height']): r for r in read(HEADERS)}
    blocks = {}
    for r in read(RES / 'block_transactions.csv'):
        blocks.setdefault(int(r['height']), []).append(r)
    rows = []
    for h, txl in sorted(blocks.items()):
        cb = [r['txid'] for r in txl if r['is_coinbase'] == 'true']
        nc = {r['txid'] for r in txl if r['is_coinbase'] != 'true'}
        parents = {r['txid']: [p for p in r['prev_txids'].split(';') if p] for r in txl if r['is_coinbase'] != 'true'}
        count_ok = len(txl) == int(hdr[h]['transaction_count']) and len(cb) == 1
        so = stock_order(nc, parents)
        root = hdr[h]['merkle_root']
        match = bool(so) and merkle_root(cb + so) == root
        one_pass = merkle_root(cb + sorted(nc)) == root
        rev = merkle_root(cb + sorted(nc, key=lambda t: t[::-1])) == root
        in_block_deps = sum(1 for t in nc for p in parents[t] if p in nc)
        vo = valid_orders(nc, parents)
        rows.append({'height': h, 'tier': B[h]['tier'], 'transactions': len(txl), 'count_ok': count_ok,
                     'in_block_dependencies': in_block_deps, 'stock_order_matches_merkle_root': match,
                     'one_pass_sorted_matches': one_pass, 'reverse_byte_sorted_matches': rev,
                     'valid_orders': vo if vo is not None else ''})
    with (RES / 'assembly_blocks.csv').open('w', newline='', encoding='utf8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    grp = lambda f: [r for r in rows if f(r['tier'])]
    pat = grp(lambda t: t == 'listed_uncontradicted')
    ordi = grp(lambda t: t in ('other_miner', 'no_patoshi_evidence'))
    summ = lambda rs: {'blocks': len(rs), 'stock_order_match': sum(r['stock_order_matches_merkle_root'] for r in rs),
                       'count_ok': sum(r['count_ok'] for r in rs)}
    a, n1 = summ(pat)['stock_order_match'], len(pat)
    c, n2 = summ(ordi)['stock_order_match'], len(ordi)
    out = {'patoshi_listed_uncontradicted': summ(pat), 'ordinary_other_or_no_evidence': summ(ordi),
           'by_tier': {t: summ(grp(lambda x, t=t: x == t)) for t in sorted({r['tier'] for r in rows})},
           'fisher_two_sided_p': fisher_two_sided(a, n1 - a, c, n2 - c),
           'patoshi_log10_valid_orders': round(sum(math.log10(r['valid_orders']) for r in pat), 3),
           'all_blocks': summ(rows),
           'non_matching': [r for r in rows if not r['stock_order_matches_merkle_root']]}
    save('assembly_summary.json', out)
    log(f"A4 assembly: {summ(rows)}")
    print(json.dumps({k: v for k, v in out.items() if k != 'non_matching'}, indent=1, default=float))
    print('non-matching:', out['non_matching'][:20])


# ---------------------------------------------------------------- exploratory (post hoc, labelled as such)

def exploratory():
    B = load()
    ref, _ = clock_reference(B)
    cp = groups(B, {'listed_uncontradicted'})
    cs = groups(B, {'other_miner'})
    out = {}
    # 1. position and stock nonce by parent-gap bin
    bins = [(-600, -1), (0, 10), (10, 20), (20, 30), (30, 60), (60, 120), (120, 300), (300, 600), (600, 3600), (3600, 10 ** 7)]
    tab = []
    for a, b in bins:
        x = [u_in(k['r']) for k in cp if a <= k['dt'] <= b]
        y = [u_s(k['n']) for k in cs if a <= k['dt'] <= b]
        tab.append({'dt_from': a, 'dt_to': b, 'patoshi_n': len(x), 'patoshi_mean_u_IN': round(float(np.mean(x)), 3),
                    'patoshi_frac_u_IN_below_0_25': round(float(np.mean(np.array(x) < 0.25)), 3),
                    'stock_n': len(y), 'stock_median_u_S': round(float(np.median(y)), 5),
                    'stock_q90_u_S': round(float(np.quantile(y, 0.9)), 5)})
    with (RES / 'position_by_gap.csv').open('w', newline='', encoding='utf8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(tab[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(tab)
    # 2. short-gap deficit in both directions (switch latency vs clock offset)
    def gap_stats(bs):
        n = len(bs)
        a = sum(0 <= b['dt'] < 10 for b in bs)
        c = sum(10 <= b['dt'] < 60 for b in bs)
        lo, hi = wilson(a, a + c)
        f = lambda s: (s / 10) / ((1 - s) / 50)
        return {'n': n, 'negative_dt': sum(b['dt'] < 0 for b in bs), 'negative_share': round(sum(b['dt'] < 0 for b in bs) / n, 4),
                'n_0_10': a, 'n_10_60': c, 'density_ratio': round(f(a / (a + c)), 3), 'ratio_lo': round(f(lo), 3),
                'ratio_hi': round(f(hi), 3)}
    out['gap_direction'] = {
        'patoshi_child_non_patoshi_parent': gap_stats(cp),
        'stock_child_non_patoshi_parent': gap_stats(cs),
        'stock_child_patoshi_parent': gap_stats(groups(B, {'other_miner'}, {'listed_uncontradicted'})),
        'band_fail_child_patoshi_parent': gap_stats(groups(B, {'no_patoshi_evidence'}, {'listed_uncontradicted'})),
        'band_fail_child_non_patoshi_parent': gap_stats(groups(B, {'no_patoshi_evidence'}))}
    g1, g2 = out['gap_direction']['patoshi_child_non_patoshi_parent'], out['gap_direction']['stock_child_non_patoshi_parent']
    out['gap_direction']['fisher_patoshi_vs_stock_0_10_vs_10_60'] = fisher_two_sided(g1['n_0_10'], g1['n_10_60'], g2['n_0_10'], g2['n_10_60'])
    # 3. top-nibble-zero share (comparison with satoshi-onchain EXCAVATION.md section 10)
    def nib(tiers, hi=54_619):
        bs = [b for b in B.values() if b['tier'] in tiers and 1 <= b['h'] <= hi]
        k = sum(b['n'] < 2 ** 28 for b in bs)
        lo, h2 = wilson(k, len(bs))
        return {'blocks': len(bs), 'top_nibble_0': k, 'share': round(k / len(bs), 4), 'lo': round(lo, 4), 'hi': round(h2, 4)}
    out['top_nibble_zero'] = {'uniform': 0.0625, 'listed_uncontradicted': nib({'listed_uncontradicted'}),
                              'listed_uncontradicted_difficulty_1': nib({'listed_uncontradicted'}, 32_255),
                              'other_miner_difficulty_1': nib({'other_miner'}, 32_255)}
    L = out['top_nibble_zero']['listed_uncontradicted_difficulty_1']['share']
    S = out['top_nibble_zero']['other_miner_difficulty_1']['share']
    out['top_nibble_zero']['stock_contamination_that_would_give_0.113'] = round((0.113 - L) / (S - L), 3)
    out['top_nibble_zero']['stock_contamination_that_would_give_0.263'] = round((0.263 - L) / (S - L), 3)
    # 4. independent nonce-shape check of the clock split (h >= 25,000; Phase 7 shape habit)
    om_share = None
    shape = {}
    for tier in ('other_miner', 'unresolved', 'added_possible', 'listed_uncontradicted'):
        for inc in (True, False):
            hs = [h for h, b in B.items() if b['tier'] == tier and h >= 25_000]
            hs = [h for h in hs if (s := clock_lr(B, h, ref)) and s['inconsistent'] == inc]
            x = [(B[h]['n'] & 255) <= 9 for h in hs if (B[h]['n'] & 255) <= 9 or 19 <= (B[h]['n'] & 255) <= 58]
            k, n = sum(x), len(x)
            lo, hi = wilson(k, n)
            shape[f'{tier}|clock_inconsistent={inc}'] = {'in_band': n, 'low_0_9': k, 'share': round(k / n, 3) if n else None,
                                                         'lo': round(lo, 3), 'hi': round(hi, 3)}
    om_share = shape['other_miner|clock_inconsistent=False']['share']
    pat_share = 0.477                                   # Phase 7: listed 25,000 to 49,973
    for k, v in shape.items():
        if v['in_band']:
            f = lambda s: round((s - om_share) / (pat_share - om_share), 2)
            v['patoshi_fraction_from_shape'] = f(v['share'])
            v['ci'] = [f(v['lo']), f(v['hi'])]
    out['shape_check_h_ge_25000'] = {'ordinary_reference_share_era_matched': om_share, 'patoshi_reference_share': pat_share,
                                     'groups': shape}
    save('exploratory.json', out)
    print(json.dumps(out, indent=1, default=float))


def live():
    """Spot-check nonce and timestamp of material blocks against mempool.space (network required)."""
    import subprocess, time
    B = load()
    hs = [2577, 24504, 34813, 35573, 35599, 37764, 37808, 39647, 46844, 48277, 49174, 49958,
          50882, 54311, 14450, 1, 2, 27476, 3358, 20000]
    out = []
    for h in hs:
        b = B[h]
        r = subprocess.run(['curl', '-sS', '-m', '30', f"https://mempool.space/api/block/{b['hash']}"], capture_output=True, text=True)
        try:
            j = json.loads(r.stdout)
            out.append({'height': h, 'hash': b['hash'], 'live_height': j['height'], 'live_nonce': j['nonce'],
                        'live_timestamp': j['timestamp'], 'local_nonce': b['n'], 'local_timestamp': b['t'],
                        'match': j['height'] == h and j['nonce'] == b['n'] and j['timestamp'] == b['t'], 'error': ''})
        except Exception:
            out.append({'height': h, 'hash': b['hash'], 'error': (r.stdout + r.stderr)[:200]})
        time.sleep(0.3)
    with (RES / 'live_header_checks.csv').open('w', newline='', encoding='utf8') as fh:
        w = csv.DictWriter(fh, fieldnames=['height', 'hash', 'live_height', 'live_nonce', 'live_timestamp', 'local_nonce',
                                           'local_timestamp', 'match', 'error'], lineterminator='\n')
        w.writeheader()
        w.writerows(out)
    log(f"live: {sum(1 for o in out if o.get('match'))} of {len(out)} match mempool.space")
    print(sum(1 for o in out if o.get('match')), 'of', len(out), 'match')


def manifest():
    digest = lambda f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
    inputs = ['analysis/phase2_bigquery/results/headers.csv', 'analysis/phase8/revised_list.csv',
              'analysis/phase6/posterior_blocks.csv', 'analysis/phase3/coinbase_encoding.csv',
              'analysis/phase9_nonce_clock/results/block_transactions.csv',
              'analysis/phase9_nonce_clock/results/block_transactions.metadata.json',
              'analysis/phase9_nonce_clock/sources/bitcoin-0.1.0_main.cpp',
              'analysis/phase9_nonce_clock/sources/bitcoin-v0.3.0_main.cpp']
    outputs = sorted(str(f.relative_to(ROOT)) for f in RES.iterdir() if f.is_file()
                     and f.name not in ('block_transactions.csv', 'block_transactions.metadata.json'))
    save_path = OUT / 'manifest.json'
    save_path.write_text(json.dumps({'inputs': {f: digest(f) for f in inputs}, 'outputs': {f: digest(f) for f in outputs},
                                     'scripts': {f: digest(f) for f in ('scripts/phase9_nonce_clock.py', 'scripts/phase9_blocktx.py',
                                                                        'analysis/phase9_nonce_clock/sql/block_transactions.sql',
                                                                        'analysis/phase9_nonce_clock/PREREGISTRATION.md')}},
                                    indent=1) + '\n', encoding='utf8')
    print('done manifest')


if __name__ == '__main__':
    cmds = {'primary': primary, 'power': power, 'amendment': amendment, 'clock': clock_check, 'update': update,
            'stress': stress, 'clock_sensitivity': clock_sensitivity, 'assembly': assembly,
            'exploratory': exploratory, 'live': live, 'manifest': manifest}
    for c in sys.argv[1:] or ['primary']:
        cmds[c]()
