"""Phase 8: one revised answer to "how many blocks did Patoshi mine, and which ones", from Phases 4 to 7; offline.

list      tier every height 0 to 54,619 and write the evidence behind each tier
estimate  combine the measured components into one count with an interval (Monte Carlo), plus sensitivity checks
manifest  SHA-256 of inputs, outputs and scripts

Count = listed - false positives + omissions inside the span + omissions after it + blocks 1 and 2.
Each component comes from the phase that measured it:
  false positives        Phase 5 (co-spend census): 12 identified, ~14.7 implied (cluster-bootstrap interval)
  omissions, 3-49,973    Phase 5 nonce-band excess among unlisted blocks not owned by another miner
  omissions, 49,974-     the same estimator after the list's end
  blocks 1 and 2         Phase 6 posteriors (they lie before the list's first height, 3)
The background band rate b is shared by both omission estimates, so it is drawn once per simulation run.
Which blocks: Phase 6 posteriors, with Phase 7's independent checks as the reason to trust them.
"""
import csv, hashlib, json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase8'
LIST_END = 49973
Q = 0.99                      # Patoshi band pass rate used by Phases 5 and 6
DRAWS = 200_000
SEED = 20260928
TIERS = ['listed_uncontradicted', 'listed_contradicted', 'added_robust', 'added_probable', 'added_possible',
         'unresolved', 'other_miner', 'no_patoshi_evidence', 'genesis']


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


# ---------------------------------------------------------------- tiers

def tier(r):
    """Tier of one Phase 6 row (plus the genesis block). Thresholds are Phase 6's: robust = P >= 0.9 under every
    track-test setting, probable = P >= 0.9 under the primary setting, possible = 0.5 <= P < 0.9."""
    h = int(r['height'])
    if h == 0:
        return 'genesis'
    if r['listed'] == 'True':
        return 'listed_contradicted' if r['co_spend_label'] == 'other' else 'listed_uncontradicted'
    if r['co_spend_label'] == 'other':
        return 'other_miner'
    p, pmin = float(r['posterior']), float(r['posterior_min_over_settings'])
    if pmin >= 0.9:
        return 'added_robust'
    if p >= 0.9:
        return 'added_probable'
    if p >= 0.5:
        return 'added_possible'
    if r['band'] == 'True':
        return 'unresolved'
    return 'no_patoshi_evidence'


def load():
    P = {int(r['height']): r for r in read(ROOT / 'analysis/phase6/posterior_blocks.csv')}
    C = {int(r['height']): r for r in read(ROOT / 'analysis/phase5/census_blocks.csv')}
    return P, C


B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def p2pkh(pubkey_hex):
    """Base58Check P2PKH address of a public key (version byte 0)."""
    h = hashlib.new('ripemd160', hashlib.sha256(bytes.fromhex(pubkey_hex)).digest()).digest()
    raw = b'\0' + h + hashlib.sha256(hashlib.sha256(b'\0' + h).digest()).digest()[:4]
    n, out = int.from_bytes(raw, 'big'), ''
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    return '1' * (len(raw) - len(raw.lstrip(b'\0'))) + out


def load_pubkeys(C):
    """Coinbase public keys from analysis/phase8/results/coinbase_pubkeys.csv (scripts/phase8_pubkeys.py).

    Every key is checked against three independent references before use: the coinbase txid and value in the
    Phase 5 census, the census address (which must equal the key's derived P2PKH address), and, for listed
    heights, the shipped patoshi_pubkeys_COMPLETE.csv."""
    shipped = {int(r['Block Height']): r['Address/Pubkey'] for r in read(ROOT / 'patoshi_pubkeys_COMPLETE.csv')}
    keys = {}
    for r in read(OUT / 'results/coinbase_pubkeys.csv'):
        h, s = int(r['height']), r['output_script']
        assert r['output_index'] == '0' and r['output_type'] == 'pubkey', h
        assert len(s) == 134 and s[:2] == '41' and s[-2:] == 'ac' and s[2:4] == '04', h
        k = s[2:-2]
        c = C[h]
        assert r['coinbase_txid'] == c['coinbase_txid'] and int(r['value_raw']) == int(c['value_sats']), h
        a = p2pkh(k)
        assert a == c['addresses'], h
        assert h not in shipped or shipped[h] == k, h
        keys[h] = (k, a)
    assert set(keys) == set(C), 'missing coinbase keys'
    return keys


def notes_index():
    """Specific evidence from earlier phases, keyed by height."""
    notes = {}
    add = lambda h, s: notes.setdefault(h, []).append(s)
    for r in read(ROOT / 'analysis/phase4/cospend_listed_in_other_miner_clusters.csv'):
        h = int(r['listed_height'])
        add(h, 'swept with another miner (Phase 4/5)')
        if r['other_miner_track_sandwich'] == 'True':
            add(h, "on the sweeping miner's own counter track (Phase 4)")
    add(24504, 'follows a listed block by 65 s, breaking the dead-time rule (Lopp 2022; Phase 7)')
    add(14450, 'spent inside a Patoshi sweep, fits the listed counter run (Phase 4)')
    ep = json.loads((ROOT / 'analysis/phase7/second_sequence_summary.json').read_text())
    for name, e in ep.items():
        kind = ('second concurrent counter' if name.startswith('2009-01-11') else "main counter after a restart the list missed")
        for h in e['second_sequence_heights']:
            add(h, f'January 2009 episode {name}: {kind} (Phase 7)')
    for r in read(ROOT / 'analysis/phase7/omission_position.csv'):
        if r['counter_below_previous_listed'] == 'True':
            add(int(r['height']), 'counter below the preceding listed block: after a restart or on a second counter (Phase 7)')
    return notes


def build_list():
    P, C = load()
    notes = notes_index()
    keys = load_pubkeys(C)
    rows = []
    for h in sorted(P):
        r = P[h]
        t = tier(r)
        ev = list(notes.get(h, []))
        if t in ('added_robust', 'added_probable') and h > LIST_END:
            ev.append('after the list\'s end: counter-track fit (Phase 6); group passes the nonce-shape and dead-time checks (Phase 7)')
        rows.append({'height': h, 'tier': t, 'listed': r['listed'] == 'True',
                     'p_patoshi': round(float(r['posterior']), 5) if t not in ('genesis', 'listed_uncontradicted', 'listed_contradicted') else '',
                     'p_min_over_settings': round(float(r['posterior_min_over_settings']), 5) if not r['listed'] == 'True' else '',
                     'co_spend_label': r['co_spend_label'], 'nonce_band': r['band'], 'spent': r['spent'],
                     'track_fit': r['track_fit'], 'coinbase_btc': int(C[h]['value_sats']) / 1e8, 'time_utc': r['time'],
                     'pubkey': keys[h][0], 'p2pkh_address': keys[h][1], 'evidence': '; '.join(ev)})
    # Genesis is not in the Phase 6 file (its output is unspendable); add it for completeness.
    rows.insert(0, {'height': 0, 'tier': 'genesis', 'listed': False, 'p_patoshi': '', 'p_min_over_settings': '',
                    'co_spend_label': '', 'nonce_band': '', 'spent': False, 'track_fit': '',
                    'coinbase_btc': int(C[0]['value_sats']) / 1e8, 'time_utc': '2009-01-03 18:15:05',
                    'pubkey': keys[0][0], 'p2pkh_address': keys[0][1], 'evidence': 'genesis block; output unspendable; excluded from every published count'})
    return rows


def tier_table(rows):
    out = []
    for t in TIERS:
        rs = [r for r in rows if r['tier'] == t]
        spans = {'in_span': [r for r in rs if 3 <= r['height'] <= LIST_END],
                 'after_end': [r for r in rs if r['height'] > LIST_END],
                 'before_start': [r for r in rs if r['height'] < 3]}
        exp = sum(r['p_patoshi'] for r in rs if r['p_patoshi'] != '')
        out.append({'tier': t, 'blocks': len(rs), 'in_span': len(spans['in_span']), 'after_end': len(spans['after_end']),
                    'before_start': len(spans['before_start']), 'btc': round(sum(r['coinbase_btc'] for r in rs), 2),
                    'expected_patoshi_blocks': round(exp, 1) if exp else ''})
    return out


# ---------------------------------------------------------------- estimate

def omission(k, n, b, q=Q, noise=0.0):
    """Phase 5 estimator: M = (k - b n) / (q - b), with optional sampling noise added to k."""
    return (k + noise - b * n) / (q - b)


def simulate(inputs, draws=DRAWS, seed=SEED, q=Q, b_tail=None):
    rng = np.random.default_rng(seed)
    b = rng.normal(inputs['b'], inputs['b_sd'], draws)
    bt = b if b_tail is None else rng.normal(b_tail, inputs['b_sd'], draws)
    ins, post = inputs['in_span'], inputs['after_end']
    o_in = omission(ins['k'], ins['n'], b, q, rng.normal(0, 1, draws) * np.sqrt(ins['n'] * b * (1 - b)))
    o_post = omission(post['k'], post['n'], bt, q, rng.normal(0, 1, draws) * np.sqrt(post['n'] * bt * (1 - bt)))
    o_in = np.clip(o_in, ins['floor'], ins['k'] / q)
    o_post = np.clip(o_post, post['floor'], post['k'] / q)
    fp = np.clip(rng.normal(inputs['fp'], inputs['fp_sd'], draws), inputs['fp_identified'], None)
    pre = sum((rng.random(draws) < p).astype(float) for p in inputs['pre'])
    total = inputs['listed'] - fp + o_in + o_post + pre
    q_ = lambda x: [round(float(v), 1) for v in np.percentile(x, [2.5, 50, 97.5])]
    return {'total_blocks': q_(total), 'false_positives': q_(fp), 'omitted_in_span': q_(o_in),
            'after_list_end': q_(o_post), 'before_list_start': q_(pre),
            'total_btc': [round(v * 50 + inputs['fee_btc'], 0) for v in q_(total)]}


def inputs_from_phases():
    s5 = json.loads((ROOT / 'analysis/phase5/census_summary.json').read_text())
    s6 = json.loads((ROOT / 'analysis/phase6/posterior_summary.json').read_text())
    P, C = load()
    bg = s5['non_patoshi_background_pass_rate']
    fp = s5['measurement']['list_false_positive_rate_among_other_miner_blocks']
    lo, hi = fp['implied_false_positive_heights_ci']
    listed = [h for h, r in P.items() if r['listed'] == 'True']
    fee = lambda h: int(C[h]['value_sats']) - 5_000_000_000
    return {
        'listed': len(listed),
        # Fees on top of the 50 BTC subsidy, per component: actual fees of listed blocks not contradicted by
        # co-spending, plus probability-weighted fees of unlisted blocks (the 12 contradicted blocks carry none).
        'fee_btc': round((sum(fee(h) for h in listed if P[h]['co_spend_label'] != 'other')
                          + sum(fee(h) * float(r['posterior']) for h, r in P.items()
                                if r['listed'] == 'False' and r['co_spend_label'] != 'other')) / 1e8, 2),
        'b': bg['rate'], 'b_sd': (bg['wilson95'][1] - bg['wilson95'][0]) / 3.92,
        'fp': fp['implied_false_positive_heights'], 'fp_sd': (hi - lo) / 3.92, 'fp_identified': fp['hits'],
        'in_span': {'k': s5['omission_bound']['of_which_pass_band'], 'n': s5['omission_bound']['unlisted_not_other_miner'],
                    'floor': s6['unlisted_in_span']['robust_core_p_ge_0_9_all_settings']},
        'after_end': {'k': s5['after_list_end']['of_which_pass_band'], 'n': s5['after_list_end']['unlisted_not_other_miner'],
                      'floor': s6['after_list_end']['robust_core_p_ge_0_9_all_settings']},
        'pre': [float(P[1]['posterior']), float(P[2]['posterior'])],
    }


# ---------------------------------------------------------------- commands

def list_cmd():
    rows = build_list()
    write_csv('revised_list.csv', rows)
    table = tier_table(rows)
    write_csv('tier_summary.csv', table)
    for t in table:
        print(t)


def estimate():
    inp = inputs_from_phases()
    main = simulate(inp)
    tail_other = [r for r in read(ROOT / 'analysis/phase6/posterior_blocks.csv')
                  if int(r['height']) > LIST_END and r['co_spend_label'] == 'other']
    b_tail = sum(r['band'] == 'True' for r in tail_other) / len(tail_other)
    sens = {
        'patoshi_band_rate_1.0': simulate(inp, q=1.0)['total_blocks'],
        'tail_background_from_tail_other_miners': simulate(inp, b_tail=b_tail)['total_blocks'],
        'tail_background_rate_used': round(b_tail, 4),
        'phase6_sum_of_posteriors_instead': round(inp['listed'] - inp['fp'] + sum(
            float(r['posterior']) for r in read(ROOT / 'analysis/phase6/posterior_blocks.csv')
            if r['listed'] == 'False' and int(r['height']) > 0), 1),
        'phase5_intervals_without_background_uncertainty': simulate(dict(inp, b_sd=1e-12))['total_blocks'],
    }
    rows = build_list()
    named = {t: sum(1 for r in rows if r['tier'] == t) for t in TIERS}
    summary = {
        'answer': {'total_blocks_median_and_95ci': main['total_blocks'], 'total_btc_median_and_95ci': main['total_btc']},
        'components': main, 'inputs': inp,
        'sensitivity_total_blocks_95ci': sens,
        'named_by_tier': named,
        'comparison': {'lopp_2022_list': 21953, 'whale_alert_2020_to_54316': 22503, 'satoshi_onchain_2026_to_54458': 22540},
        'notes': ('Intervals combine sampling noise in each band count, uncertainty in the shared background band rate '
                  '(measured on 22,947 other-miner blocks), and the cluster-bootstrap interval of false positives, '
                  'floored at the 12 identified. Omission estimates are clipped to at least the robust-core count and '
                  'at most the candidate bound. Heights are treated as independent, as in Phase 5, so intervals are '
                  'optimistic; shared model assumptions (co-spend ownership, the band as a Patoshi signature) are not '
                  'in the interval. The tail-background sensitivity run uses the band pass rate of other-miner blocks '
                  'after 49,973 for the post-endpoint estimate instead of the all-era rate.'),
    }
    save('revised_estimate.json', summary)
    print(json.dumps({k: summary[k] for k in ('answer', 'components', 'sensitivity_total_blocks_95ci')}, indent=1))


def manifest():
    inputs = ['analysis/phase5/census_summary.json', 'analysis/phase5/census_blocks.csv', 'analysis/phase6/posterior_blocks.csv',
              'analysis/phase6/posterior_summary.json', 'analysis/phase7/verify_summary.json',
              'analysis/phase7/second_sequence_summary.json', 'analysis/phase7/omission_position.csv',
              'analysis/phase4/cospend_listed_in_other_miner_clusters.csv', 'patoshi_pubkeys_COMPLETE.csv',
              'analysis/phase8/results/coinbase_pubkeys.csv', 'analysis/phase8/results/coinbase_pubkeys.metadata.json']
    digest = lambda f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
    outputs = sorted(str(f.relative_to(ROOT)).replace('\\', '/') for f in OUT.iterdir()
                     if f.is_file() and f.suffix in ('.csv', '.json') and f.name != 'manifest.json')
    save('manifest.json', {'inputs': {f: digest(f) for f in inputs}, 'outputs': {f: digest(f) for f in outputs},
                           'scripts': {f: digest(f) for f in ('scripts/phase8_synthesis.py', 'scripts/phase8_pubkeys.py',
                                                              'analysis/phase8/sql/coinbase_pubkeys.sql')}})


def main():
    cmds = {'list': list_cmd, 'estimate': estimate, 'manifest': manifest}
    for c in sys.argv[1:] or ['list', 'estimate', 'manifest']:
        cmds[c]()
        print('done', c)


if __name__ == '__main__':
    main()
