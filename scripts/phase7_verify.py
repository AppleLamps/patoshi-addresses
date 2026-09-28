"""Phase 7: verify Phase 6 with Patoshi habits it never used, and characterise the January 2009 second sequence.

verify    independent-habit tests of the post-endpoint tail and a calibration check of the Phase 6 posterior
second    the unlisted low-counter sequences of 11-12 and 28-29 January 2009
manifest  SHA-256 of inputs, outputs and scripts

Habits used here, none of which enters the Phase 6 model:
  nonce shape   where inside the band (0-9 vs 19-58) the nonce low byte falls; Patoshi's share at 0-9 rises from
                about 0.20 before height 20,000 to about 0.5 from 25,000, while other miners stay near 0.2
  dead time     two consecutive Patoshi blocks are at least ~312 s apart from height 5,000 on (Lerner 2020,
                "A New Mystery in Patoshi Timestamps"); ordinary consecutive pairs fall under 300 s ~46% of the time
  clock offset  timestamp minus the median of the six blocks either side
Offline: reads committed Phase 2 headers and the Phase 5 and 6 outputs.
"""
import collections, csv, hashlib, json, math, statistics, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase7'
LIST_END = 49973
DEAD_TIME = 300
LATE = (25000, LIST_END)            # era where Patoshi's in-band nonce shape differs from other miners'
TAIL = (LIST_END + 1, 54619)
EPISODES = {'2009-01-11/12': (150, 210), '2009-01-28/29': (2120, 2180)}


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


# ---------------------------------------------------------------- statistics

def in_band(lsb):
    return lsb <= 9 or 19 <= lsb <= 58


def binom_upper(k, n, p):
    """P(X >= k), X ~ Binomial(n, p), in log space."""
    if k <= 0:
        return 1.0
    terms = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * math.log(p) + (n - i) * math.log1p(-p)
             for i in range(k, n + 1)]
    m = max(terms)
    return min(1.0, math.exp(m) * sum(math.exp(t - m) for t in terms))


def wilson(k, n, z=1.959964):
    if n == 0:
        return [0.0, 1.0]
    p = k / n
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [max(0.0, mid - half), min(1.0, mid + half)]


def mixture_fraction(k, n, p0, p1):
    """Patoshi fraction implied by a shape count: rate = f * p1 + (1 - f) * p0. Point estimate and Wilson-based CI."""
    if n == 0 or p1 == p0:
        return None
    f = lambda r: (r - p0) / (p1 - p0)
    lo, hi = wilson(k, n)
    return {'estimate': round(f(k / n), 3), 'ci95': [round(f(lo), 3), round(f(hi), 3)]}


def mann_whitney(x, y):
    """Two-sided normal-approximation Mann-Whitney U test with tie correction. Returns (z, p)."""
    allv = sorted((v, g) for g, vs in ((0, x), (1, y)) for v in vs)
    ranks, i = {}, 0
    rank_sum = [0.0, 0.0]
    ties = 0.0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        r = (i + j + 1) / 2
        t = j - i
        ties += t ** 3 - t
        for k in range(i, j):
            rank_sum[allv[k][1]] += r
        i = j
    n1, n2 = len(x), len(y)
    u = rank_sum[0] - n1 * (n1 + 1) / 2
    n = n1 + n2
    var = n1 * n2 / 12 * ((n + 1) - ties / (n * (n - 1)))
    z = (u - n1 * n2 / 2) / math.sqrt(var) if var > 0 else 0.0
    return round(z, 3), math.erfc(abs(z) / math.sqrt(2))


# ---------------------------------------------------------------- data

def load():
    H = {}
    for r in read(ROOT / 'analysis/phase2_bigquery/results/headers.csv'):
        H[int(r['height'])] = {'t': datetime.fromisoformat(r['timestamp'].replace('+00', '+00:00')).timestamp(),
                               'lsb': int(r['nonce'], 16) & 255}
    P = {int(r['height']): r for r in read(ROOT / 'analysis/phase6/posterior_blocks.csv')}
    return H, P


def clock_offset(H, h, k=6):
    nb = [H[x]['t'] for x in range(h - k, h + k + 1) if x != h and x in H]
    return H[h]['t'] - statistics.median(nb)


def groups(P):
    f = lambda r, k: float(r[k])
    tail = lambda h: TAIL[0] <= h <= TAIL[1]
    return {
        'patoshi_reference_listed_25000_49973': [h for h, r in P.items() if LATE[0] <= h <= LATE[1] and r['listed'] == 'True'
                                                  and r['co_spend_label'] != 'other'],
        'ordinary_reference_other_miner_tail': [h for h, r in P.items() if tail(h) and r['co_spend_label'] == 'other'],
        'tail_robust_core': [h for h, r in P.items() if tail(h) and f(r, 'posterior_min_over_settings') >= 0.9],
        'tail_named_not_core': [h for h, r in P.items() if tail(h) and f(r, 'posterior') >= 0.9
                                and f(r, 'posterior_min_over_settings') < 0.9],
        'tail_dormant_band_passing_rejected': [h for h, r in P.items() if tail(h) and r['band'] == 'True'
                                               and r['spent'] == 'False' and r['co_spend_label'] != 'other'
                                               and f(r, 'posterior') < 0.5],
        'control_other_miner_tail_with_track_fit': [h for h, r in P.items() if tail(h) and r['co_spend_label'] == 'other'
                                                    and r['track_fit'] == 'True'],
        'span_robust_core_late': [h for h, r in P.items() if LATE[0] <= h <= LATE[1] and r['listed'] == 'False'
                                  and f(r, 'posterior_min_over_settings') >= 0.9],
    }


def shape_counts(H, hs):
    band = [h for h in hs if in_band(H[h]['lsb'])]
    return sum(H[h]['lsb'] <= 9 for h in band), len(band)


def dead_time_pairs(H, members, previous):
    gaps = [H[h]['t'] - H[h - 1]['t'] for h in members if (h - 1) in previous]
    return len(gaps), sum(g < DEAD_TIME for g in gaps), sorted(gaps)[:3]


# ---------------------------------------------------------------- commands

def verify():
    H, P = load()
    G = groups(P)
    ref_p, ref_o = G['patoshi_reference_listed_25000_49973'], G['ordinary_reference_other_miner_tail']
    k1, n1 = shape_counts(H, ref_p)
    k0, n0 = shape_counts(H, ref_o)
    p1, p0 = k1 / n1, k0 / n0
    listed = {h for h, r in P.items() if r['listed'] == 'True'}
    other = {h for h, r in P.items() if r['co_spend_label'] == 'other'}
    # Dead-time rates on the references, from height 5,000 (before that Patoshi's pairs break the rule ~5% of the time).
    dn1, dk1, dmin1 = dead_time_pairs(H, [h for h in listed if h >= 5000], listed)
    dn0, dk0, _ = dead_time_pairs(H, [h for h in other if h >= 5000], other)
    q0 = dk0 / dn0
    clock_o = [clock_offset(H, h) for h in ref_o]
    rows = []
    for g, hs in G.items():
        k, n = shape_counts(H, hs)
        s = set(hs)
        dn, dk, dmin = dead_time_pairs(H, hs, s)
        clock = [clock_offset(H, h) for h in hs]
        z, pv = mann_whitney(clock, clock_o) if g != 'ordinary_reference_other_miner_tail' else (None, None)
        post = [float(P[h]['posterior']) for h in hs]
        rows.append({'group': g, 'blocks': len(hs), 'mean_phase6_posterior': round(sum(post) / len(post), 3),
                     'in_band': n, 'in_band_low_0_9': k, 'low_share': round(k / n, 3) if n else '',
                     'shape_patoshi_fraction': json.dumps(mixture_fraction(k, n, p0, p1)),
                     'shape_p_vs_ordinary': binom_upper(k, n, p0) if n else '',
                     'consecutive_pairs': dn, 'pairs_under_300s': dk,
                     'pairs_p_all_respect_if_ordinary': round((1 - q0) ** dn, 4) if dk == 0 and dn else '',
                     'clock_offset_median_s': round(statistics.median(clock), 1), 'clock_mw_z_vs_ordinary': z,
                     'clock_mw_p_vs_ordinary': pv if pv is None else float(f'{pv:.3g}')})
    write_csv('habit_tests.csv', rows)
    # Calibration: bin unlisted band-passing blocks by Phase 6 posterior; the nonce shape alone estimates each bin's
    # Patoshi fraction. Done separately for the tail and for the late span, where the shape is informative.
    cal = []
    bins = [(0, 0.1), (0.1, 0.5), (0.5, 0.9), (0.9, 1.01)]
    for region, (a, z) in (('tail', TAIL), ('late_span', LATE)):
        pool = [h for h, r in P.items() if a <= h <= z and r['listed'] == 'False' and r['band'] == 'True'
                and r['co_spend_label'] != 'other']
        for lo, hi in bins:
            hs = [h for h in pool if lo <= float(P[h]['posterior']) < hi]
            k, n = shape_counts(H, hs)
            mf = mixture_fraction(k, n, p0, p1)
            cal.append({'region': region, 'posterior_bin': f'{lo}-{min(hi, 1.0)}', 'blocks': n,
                        'mean_phase6_posterior': round(sum(float(P[h]['posterior']) for h in hs) / n, 3) if n else '',
                        'low_share': round(k / n, 3) if n else '',
                        'shape_patoshi_fraction': mf['estimate'] if mf else '',
                        'shape_ci95_lo': mf['ci95'][0] if mf else '', 'shape_ci95_hi': mf['ci95'][1] if mf else ''})
    write_csv('calibration_by_posterior.csv', cal)
    # Nonce-shape history of the listed blocks, which is what makes the test era-dependent.
    hist = []
    for lo in range(0, 50000, 2500):
        hs = [h for h in listed if lo <= h < lo + 2500 and P[h]['co_spend_label'] != 'other']
        k, n = shape_counts(H, hs)
        ko, no = shape_counts(H, [h for h in other if lo <= h < lo + 2500 and in_band(H[h]['lsb'])])
        hist.append({'heights': f'{lo}-{lo + 2499}', 'listed_in_band': n, 'listed_low_share': round(k / n, 3) if n else '',
                     'other_miner_in_band': no, 'other_miner_low_share': round(ko / no, 3) if no else ''})
    write_csv('nonce_shape_history.csv', hist)
    save('verify_summary.json', {
        'references': {'patoshi_low_share': round(p1, 4), 'patoshi_in_band': n1,
                       'ordinary_low_share': round(p0, 4), 'ordinary_in_band': n0,
                       'dead_time_listed_pairs_from_5000': {'pairs': dn1, 'under_300s': dk1, 'shortest_s': dmin1},
                       'dead_time_other_miner_pairs_from_5000': {'pairs': dn0, 'under_300s': dk0, 'rate': round(q0, 4)},
                       'clock_offset_median_s_ordinary_tail': round(statistics.median(clock_o), 1)},
        'groups': rows, 'calibration': cal,
        'notes': ('Shape test: Patoshi fraction f solves share = f*p1 + (1-f)*p0 with p1 from listed 25,000-49,973 and '
                  'p0 from other-miner blocks in the tail. Dead time: probability that all pairs respect the 300 s rule '
                  'if the blocks were ordinary. Clock offset: two-sided Mann-Whitney against the ordinary tail reference.')})
    for r in rows:
        print({k: r[k] for k in ('group', 'blocks', 'mean_phase6_posterior', 'low_share', 'shape_patoshi_fraction',
                                 'shape_p_vs_ordinary', 'consecutive_pairs', 'pairs_under_300s', 'clock_offset_median_s',
                                 'clock_mw_p_vs_ordinary')})
    for c in cal:
        print(c)


def second():
    H, P = load()
    en = {h: (int(r['extra_nonce']) if r['extra_nonce'] else None) for h, r in P.items()}
    listed = {h for h, r in P.items() if r['listed'] == 'True'}
    rows, summary = [], {}
    for name, (a, z) in EPISODES.items():
        seq = [h for h in range(a, z + 1) if P[h]['listed'] == 'False' and P[h]['band'] == 'True'
               and P[h]['spent'] == 'False' and P[h]['co_spend_label'] != 'other' and float(P[h]['posterior']) >= 0.5]
        lst = [h for h in range(a, z + 1) if h in listed]
        others = [h for h in range(a, z + 1) if h not in listed and h not in seq]
        for h in range(a, z + 1):
            rows.append({'episode': name, 'height': h, 'time': P[h]['time'],
                         'role': 'listed' if h in listed else ('second_sequence' if h in seq else 'other'),
                         'extra_nonce': en[h], 'nonce_lsb': H[h]['lsb'], 'band': P[h]['band'], 'spent': P[h]['spent'],
                         'phase6_posterior': P[h]['posterior'], 'gap_to_previous_s': int(H[h]['t'] - H[h - 1]['t'])})
        s_set, l_set = set(seq), set(lst)
        k_s, n_s = shape_counts(H, seq)
        k_l, n_l = shape_counts(H, lst)
        summary[name] = {
            'heights': [a, z], 'second_sequence_blocks': len(seq), 'listed_blocks': len(lst), 'other_blocks': len(others),
            'second_sequence_heights': seq,
            'all_pass_band_p_if_ordinary': 0.19610406589096613 ** len(seq),
            'never_spent': all(P[h]['spent'] == 'False' for h in seq),
            'extra_nonce_range': {'second_sequence': [min(en[h] for h in seq), max(en[h] for h in seq)],
                                  'listed': [min(en[h] for h in lst), max(en[h] for h in lst)]},
            'in_band_low_share': {'second_sequence': f'{k_s}/{n_s}', 'listed_same_window': f'{k_l}/{n_l}',
                                  'note': 'uninformative before height 20,000: Patoshi and other miners both near 0.2'},
            'gaps_under_300s': {
                'second_after_second': dead_time_pairs(H, seq, s_set)[:2],
                'second_after_listed': dead_time_pairs(H, seq, l_set)[:2],
                'listed_after_second': dead_time_pairs(H, lst, s_set)[:2],
                'listed_after_listed': dead_time_pairs(H, lst, l_set)[:2],
                'note': '(pairs, under 300 s). Before height 5,000 listed pairs break the rule ~5% of the time.'},
            'time_span': [P[seq[0]]['time'], P[seq[-1]]['time']]}
    write_csv('second_sequence_blocks.csv', rows)
    save('second_sequence_summary.json', summary)
    print(json.dumps(summary, indent=1))


def manifest():
    inputs = ['analysis/phase2_bigquery/results/headers.csv', 'analysis/phase6/posterior_blocks.csv']
    digest = lambda f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
    outputs = sorted(str(f.relative_to(ROOT)).replace('\\', '/') for f in OUT.iterdir()
                     if f.is_file() and f.suffix in ('.csv', '.json') and f.name != 'manifest.json')
    save('manifest.json', {'inputs': {f: digest(f) for f in inputs}, 'outputs': {f: digest(f) for f in outputs},
                           'scripts': {'scripts/phase7_verify.py': digest('scripts/phase7_verify.py')}})


def main():
    cmds = {'verify': verify, 'second': second, 'manifest': manifest}
    for c in sys.argv[1:] or ['verify', 'second', 'manifest']:
        cmds[c]()
        print('done', c)


if __name__ == '__main__':
    main()
