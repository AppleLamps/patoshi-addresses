"""Phase 4 offline analyses on committed chain exports; no network, no key recovery, no spending.

cospend      common-input clusters of the 20 first-spending transactions
sandwich     full scan of unlisted heights for Patoshi-run fits, with an expected-false-positive null
signatures   DER/sighash/low-S/R-reuse/small-k forensics and ECDSA verification of trace inputs
fingerprint  wallet-behaviour features of the first-spending transactions
manifest     SHA-256 of inputs, outputs and this script
"""
import bisect, collections, csv, hashlib, json, math, sys
from datetime import datetime
from pathlib import Path
import numpy as np
csv.field_size_limit(1_000_000_000)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase2_collect import extra_nonce
from phase2_analyze import nonce_pass, inner_pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase4'
P2 = ROOT / 'analysis/phase2_bigquery'
P3 = ROOT / 'analysis/phase3'
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def offline(event, args):
    if event.startswith('socket.'):
        raise RuntimeError('Offline analysis forbids sockets')


sys.addaudithook(offline)


def read(p):
    with p.open(newline='', encoding='utf8') as f:
        return list(csv.DictReader(f))


def save(name, x):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(x, indent=2) + '\n', encoding='utf8', newline='\n')


def table(name, rows, fields=None):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open('w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def sha256d(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def hash160(b):
    return hashlib.new('ripemd160', hashlib.sha256(b).digest()).digest()


# ---------------------------------------------------------------- shared data

def load_headers():
    headers = {}
    for r in read(P2 / 'results/headers.csv'):
        h = int(r['height'])
        headers[h] = {'h': h, 't': r['timestamp'], 'n': int(r['nonce'], 16),
                      'en': extra_nonce(r['coinbase_param']).get('extra_nonce'),
                      'merkle': r['merkle_root'], 'txcount': int(r['transaction_count'])}
    return headers


def load_listed():
    return {int(r['Block Height']): r['Address/Pubkey'] for r in read(ROOT / 'patoshi_pubkeys_COMPLETE.csv')}


def coinbase_heights(headers):
    """Coinbase txid -> height. Single-transaction blocks: txid equals the header Merkle root."""
    cb = {h['merkle']: h['h'] for h in headers.values() if h['txcount'] == 1}
    for f in ('results/context.csv', 'results/pubkeys.csv'):
        for r in read(P2 / f):
            cb[r['coinbase_txid']] = int(r['height'])
    return cb


def load_seeds():
    return json.loads((P3 / 'trace_seed_transactions.json').read_text(encoding='utf8'))


def load_trace():
    txs = {}
    for g in (1, 2, 3):
        for r in read(P3 / f'results/trace_transactions_{g}.csv'):
            r['inputs'] = json.loads(r['inputs_json'])
            r['outputs'] = json.loads(r['outputs_json'])
            r['generation'] = g
            txs[r['txid']] = r
    return txs


def neighbours(h, listed_sorted):
    i = bisect.bisect_left(listed_sorted, h)
    left = listed_sorted[i - 1] if i > 0 else None
    right = listed_sorted[i + 1] if i + 1 < len(listed_sorted) and listed_sorted[i] == h else (
        listed_sorted[i] if i < len(listed_sorted) and listed_sorted[i] != h else None)
    return left, right


def run_fit(h, headers, listed_sorted):
    """Does height h sit inside a monotone listed extraNonce run, in both counter and time?"""
    left, right = neighbours(h, listed_sorted)
    if left is None or right is None:
        return {'left': left, 'right': right, 'sandwich': False}
    a, b, x = headers[left], headers[right], headers[h]
    ok = (a['en'] is not None and b['en'] is not None and x['en'] is not None
          and a['en'] < x['en'] < b['en'])
    return {'left': left, 'right': right, 'left_en': a['en'], 'right_en': b['en'],
            'window': (b['en'] - a['en'] + 1) if a['en'] is not None and b['en'] is not None else None,
            'sandwich': bool(ok)}


# ---------------------------------------------------------------- 1. co-spend clusters

def zt_binomial_mle(clusters):
    """Zero-truncated binomial MLE of p from (n, k) pairs, each observed only because k >= 1."""
    def nll(p):
        return -sum(k * math.log(p) + (n - k) * math.log1p(-p) - math.log1p(-(1 - p) ** n) for n, k in clusters)
    grid = np.exp(np.linspace(math.log(1e-6), math.log(0.5), 4000))
    vals = [nll(p) for p in grid]
    i = int(np.argmin(vals))
    best = float(grid[i])
    # profile-likelihood 95% interval (chi-square 1 df, 3.841/2)
    ok = [float(p) for p, v in zip(grid, vals) if v - vals[i] <= 1.9207]
    return {'p_hat': best, 'ci95_profile': [min(ok), max(ok)]}


def poisson_binomial_tail(k, ps):
    dist = [1.0]
    for p in ps:
        dist = [a * (1 - p) + b * p for a, b in zip(dist + [0.0], [0.0] + dist)]
    return float(sum(dist[k:]))


def cospend():
    headers, listed, seeds = load_headers(), load_listed(), load_seeds()
    lsorted = sorted(listed)
    cb = coinbase_heights(headers)
    rows, clusters = [], []
    for t in sorted(seeds.values(), key=lambda t: t['status']['block_height']):
        ins = []
        for vi, v in enumerate(t['vin']):
            h = cb.get(v['txid'])
            r = {'spending_txid': t['txid'], 'spending_height': t['status']['block_height'], 'vin': vi,
                 'prev_txid': v['txid'], 'prev_vout': v['vout'], 'value_sats': v['prevout']['value'],
                 'prev_type': v['prevout']['scriptpubkey_type'], 'coinbase_height': h if h is not None else '',
                 'listed': h in listed if h is not None else ''}
            if h is not None:
                x = headers[h]
                fit = run_fit(h, headers, lsorted)
                r.update({'nonce_lsb': x['n'] & 255, 'broad_nonce_pass': nonce_pass(x['n']),
                          'tight_nonce_pass': inner_pass(x['n']), 'extra_nonce': x['en'],
                          'left_listed': fit['left'], 'right_listed': fit['right'],
                          'left_en': fit.get('left_en', ''), 'right_en': fit.get('right_en', ''),
                          'run_sandwich': fit['sandwich'], 'block_time': x['t']})
            ins.append(r)
        rows += ins
        cbs = [r for r in ins if r['coinbase_height'] != '']
        nl = sum(1 for r in cbs if r['listed'])
        nu = len(cbs) - nl
        unl = [r for r in cbs if not r['listed']]
        clusters.append({
            'spending_txid': t['txid'], 'spending_height': t['status']['block_height'],
            'inputs': len(ins), 'mapped_coinbases': len(cbs), 'listed': nl, 'unlisted': nu,
            'unmapped_inputs': len(ins) - len(cbs),
            'listed_heights': ' '.join(str(r['coinbase_height']) for r in cbs if r['listed']),
            'unlisted_heights_min': min((r['coinbase_height'] for r in unl), default=''),
            'unlisted_heights_max': max((r['coinbase_height'] for r in unl), default=''),
            'unlisted_broad_nonce_pass': sum(1 for r in unl if r['broad_nonce_pass']),
            'unlisted_tight_nonce_pass': sum(1 for r in unl if r['tight_nonce_pass']),
            'cluster_class': 'listed_only' if nu == 0 else ('listed_majority' if nl > nu else 'unlisted_majority'),
        })
    # For listed members of unlisted-majority clusters: does the co-spending miner's own counter track explain them?
    track = []
    for c in clusters:
        if c['cluster_class'] != 'unlisted_majority':
            continue
        members = sorted((r['coinbase_height'], r['extra_nonce'], r['block_time']) for r in rows
                         if r['spending_txid'] == c['spending_txid'] and r['coinbase_height'] != '' and not r['listed'])
        for h in map(int, c['listed_heights'].split()):
            before = [m for m in members if m[0] < h]
            after = [m for m in members if m[0] > h]
            b, a, x = (before[-1] if before else None), (after[0] if after else None), headers[h]
            track.append({'listed_height': h, 'spending_txid': c['spending_txid'], 'extra_nonce': x['en'],
                          'block_time': x['t'], 'tight_nonce_pass': inner_pass(x['n']),
                          'cluster_prev_height': b[0] if b else '', 'cluster_prev_en': b[1] if b else '',
                          'cluster_next_height': a[0] if a else '', 'cluster_next_en': a[1] if a else '',
                          'height_gap': (a[0] - b[0]) if a and b else '',
                          'other_miner_track_sandwich': bool(a and b and b[1] is not None and a[1] is not None
                                                             and b[1] < x['en'] < a[1] and b[2] < x['t'] < a[2]),
                          'patoshi_run_sandwich': run_fit(h, headers, lsorted)['sandwich']})
    # Calibration: how often does any listed block in the same height span fit that miner's track by chance?
    for t in track:
        c = next(c for c in clusters if c['spending_txid'] == t['spending_txid'])
        members = sorted((r['coinbase_height'], r['extra_nonce'], r['block_time']) for r in rows
                         if r['spending_txid'] == c['spending_txid'] and r['coinbase_height'] != '' and not r['listed'])
        hs = [m[0] for m in members]
        fits = total = 0
        for h in lsorted:
            if not hs[0] < h < hs[-1] or h == t['listed_height']:
                continue
            j = bisect.bisect_left(hs, h)
            b, a, x = members[j - 1], members[j], headers[h]
            if a[0] - b[0] > 400 or b[1] is None or a[1] is None or x['en'] is None:
                continue
            total += 1
            fits += b[1] < x['en'] < a[1] and b[2] < x['t'] < a[2]
        t['span_listed_blocks_evaluated'] = total
        t['span_listed_blocks_fitting_track'] = fits
        t['chance_fit_rate'] = round(fits / total, 4) if total else ''
    table('cospend_listed_in_other_miner_clusters.csv', track)
    fields = ['spending_txid', 'spending_height', 'vin', 'prev_txid', 'prev_vout', 'value_sats', 'prev_type',
              'coinbase_height', 'listed', 'block_time', 'nonce_lsb', 'broad_nonce_pass', 'tight_nonce_pass',
              'extra_nonce', 'left_listed', 'right_listed', 'left_en', 'right_en', 'run_sandwich']
    table('cospend_inputs.csv', rows, fields)
    table('cospend_clusters.csv', clusters)
    mixed = [c for c in clusters if c['cluster_class'] == 'unlisted_majority']
    clean = [c for c in clusters if c['cluster_class'] != 'unlisted_majority']
    unl_mixed = [r for r in rows if r['coinbase_height'] != '' and not r['listed']
                 and any(r['spending_txid'] == c['spending_txid'] for c in mixed)]
    unl_clean = [r for r in rows if r['coinbase_height'] != '' and not r['listed']
                 and any(r['spending_txid'] == c['spending_txid'] for c in clean)]
    listed_mixed = [r for r in rows if r['listed'] is True and any(r['spending_txid'] == c['spending_txid'] for c in mixed)]
    uniform_broad = 50 / 256
    uniform_tight = (163840000 + (983040000 - 327680000)) / 2**32
    k_b = sum(r['broad_nonce_pass'] for r in unl_mixed)
    k_t = sum(r['tight_nonce_pass'] for r in unl_mixed)
    n_u = len(unl_mixed)

    def binom_tail(k, n, p):
        return float(sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1)))

    save('cospend_summary.json', {
        'first_spending_transactions': len(clusters),
        'listed_coinbases_spent': sum(c['listed'] for c in clusters),
        'clusters_by_class': dict(collections.Counter(c['cluster_class'] for c in clusters)),
        'listed_in_unlisted_majority_clusters': {
            'count': len(listed_mixed), 'btc': sum(r['value_sats'] for r in listed_mixed) / 1e8,
            'heights': sorted(r['coinbase_height'] for r in listed_mixed),
            'run_sandwich_true': sum(bool(r['run_sandwich']) for r in listed_mixed),
            'tight_nonce_pass': sum(bool(r['tight_nonce_pass']) for r in listed_mixed)},
        'other_miner_track_sandwich': {
            'observed': sum(t['other_miner_track_sandwich'] for t in track), 'of': len(track),
            'expected_if_chance': round(sum(t['chance_fit_rate'] or 0 for t in track), 4),
            'poisson_binomial_upper_tail_p': poisson_binomial_tail(
                sum(t['other_miner_track_sandwich'] for t in track), [t['chance_fit_rate'] or 0 for t in track]),
            'note': 'chance rate = share of other listed blocks in the cluster height span that fit the same track'},
        'listed_in_listed_majority_or_only_clusters': sum(c['listed'] for c in clean),
        'unlisted_coinbases_in_unlisted_majority_clusters': {
            'n': n_u, 'broad_nonce_pass': k_b, 'tight_nonce_pass': k_t,
            'uniform_expectation_broad': uniform_broad, 'uniform_expectation_tight': uniform_tight,
            'observed_rate_broad': k_b / n_u if n_u else None,
            'upper_tail_p_broad': binom_tail(k_b, n_u, uniform_broad) if n_u else None,
            'upper_tail_p_tight': binom_tail(k_t, n_u, uniform_tight) if n_u else None},
        'unlisted_coinbases_in_listed_majority_clusters': [
            {k: r[k] for k in ('coinbase_height', 'spending_txid', 'nonce_lsb', 'tight_nonce_pass', 'extra_nonce',
                               'left_listed', 'right_listed', 'left_en', 'right_en', 'run_sandwich')} for r in unl_clean],
        'list_inclusion_rate_for_cospent_other_miner_blocks_zero_truncated_mle':
            zt_binomial_mle([(c['mapped_coinbases'], c['listed']) for c in mixed]),
        'assumptions': ('Common-input ownership: inputs of one 2009-2018 consolidation are controlled by one entity. '
                        'Unlisted-majority clusters are treated as another miner; their listed members as list '
                        'false positives. Clusters are observed only because they contain a listed coinbase, hence '
                        'the zero-truncated likelihood. Coinbases of multi-transaction blocks outside the committed '
                        'context rows are unmapped and excluded from counts.'),
    })


# ---------------------------------------------------------------- 2. sandwich scan

STRATA = [('fp<0.002', 0.002), ('0.002<=fp<0.01', 0.01), ('fp>=0.01', 2.0)]


def poisson_tail(k, lam):
    if lam <= 0:
        return 0.0 if k > 0 else 1.0
    return float(max(0.0, 1 - sum(math.exp(-lam + i * math.log(lam) - math.lgamma(i + 1)) for i in range(k))))


def sandwich():
    headers, listed = load_headers(), load_listed()
    lsorted = sorted(listed)
    hi = max(listed)
    unl = [h for h in range(3, hi) if h not in listed]
    # background counter values of blocks unlikely to be Patoshi (fail the broad nonce rule)
    bg_h = [h for h in unl if not nonce_pass(headers[h]['n']) and headers[h]['en'] is not None]
    bg_en = {h: headers[h]['en'] for h in bg_h}
    p_tight = (163840000 + (983040000 - 327680000)) / 2**32
    rows, expected, evaluated = [], 0.0, 0
    strata = {k: {'windows': 0, 'expected': 0.0, 'observed': 0} for k, _ in STRATA}
    for h in unl:
        x = headers[h]
        fit = run_fit(h, headers, lsorted)
        l, r = fit['left'], fit['right']
        if l is None or r is None:
            continue
        a, b = headers[l], headers[r]
        if a['en'] is None or b['en'] is None or b['en'] < a['en']:
            continue
        # a short, strictly time-ordered monotone run: at most 3 hours and 60 counter steps between anchors
        if not (a['t'] < x['t'] < b['t']) or (b['en'] - a['en']) > 60:
            continue
        if (datetime.fromisoformat(b['t']) - datetime.fromisoformat(a['t'])).total_seconds() > 3 * 3600:
            continue
        evaluated += 1
        # probability a non-Patoshi block lands in the window: local background counter distribution
        near = [bg_en[k] for k in bg_h[max(0, bisect.bisect_left(bg_h, h) - 150): bisect.bisect_left(bg_h, h) + 150]]
        p_win = sum(1 for e in near if a['en'] < e < b['en']) / len(near) if near else 0.0
        expected += p_tight * p_win
        fp = p_tight * p_win
        stratum = next(k for k, hi_ in STRATA if fp < hi_)
        strata[stratum]['expected'] += fp
        strata[stratum]['windows'] += 1
        if fit['sandwich'] and inner_pass(x['n']):
            rows.append({'height': h, 'block_time': x['t'], 'nonce_lsb': x['n'] & 255, 'extra_nonce': x['en'],
                         'left_listed': l, 'left_en': a['en'], 'left_time': a['t'],
                         'right_listed': r, 'right_en': b['en'], 'right_time': b['t'],
                         'window_width': b['en'] - a['en'] + 1, 'background_window_prob': round(p_win, 5),
                         'false_positive_prob': round(fp, 5), 'fp_stratum': stratum})
            strata[stratum]['observed'] += 1
    if rows:
        table('sandwich_candidates.csv', rows)
    save('sandwich_summary.json', {
        'unlisted_heights_in_range': len(unl), 'evaluable_short_monotone_windows': evaluated,
        'candidates_observed': len(rows),
        'candidates_expected_if_no_omissions': round(expected, 3),
        'excess': round(len(rows) - expected, 3),
        'poisson_upper_tail_p': poisson_tail(len(rows), expected),
        'by_false_positive_stratum': {k: {'windows': v['windows'], 'expected': round(v['expected'], 3),
                                          'observed': v['observed'],
                                          'poisson_upper_tail_p': poisson_tail(v['observed'], v['expected'])}
                                      for k, v in strata.items()},
        'includes_14450': any(r['height'] == 14450 for r in rows),
        'rule': ('Unlisted height h between consecutive listed heights L<h<R with time(L)<time(h)<time(R), '
                 'time(R)-time(L)<=3h, 0<=en(R)-en(L)<=60, en(L)<en(h)<en(R) (the counter never repeats between Patoshi blocks), and Lerner-2020 tight nonce pass. '
                 'Null: P(tight nonce)=0.1907 for a uniform nonce times the share of nearby broad-nonce-failing '
                 'blocks (+/-150) whose extraNonce falls in [en(L),en(R)]. Exploratory; not a replacement list.'),
    })


# ---------------------------------------------------------------- 3. signatures

def parse_der(sig):
    """Return (r, s, strict) for a DER signature without sighash byte; strict = BIP66-canonical."""
    strict = True
    if len(sig) < 8 or sig[0] != 0x30:
        return None
    if sig[1] != len(sig) - 2:
        strict = False
    i = 2
    out = []
    for _ in range(2):
        if sig[i] != 0x02:
            return None
        ln = sig[i + 1]
        v = sig[i + 2:i + 2 + ln]
        if ln == 0 or v[0] & 0x80 or (ln > 1 and v[0] == 0 and not v[1] & 0x80):
            strict = False
        out.append(int.from_bytes(v, 'big'))
        i += 2 + ln
    if i != len(sig):
        strict = False
    return out[0], out[1], strict


def pushes(script):
    b, i, out = bytes.fromhex(script), 0, []
    while i < len(b):
        op = b[i]
        i += 1
        if 1 <= op <= 75:
            out.append(b[i:i + op]); i += op
        elif op == 76:
            n = b[i]; out.append(b[i + 1:i + 1 + n]); i += 1 + n
        elif op == 77:
            n = int.from_bytes(b[i:i + 2], 'little'); out.append(b[i + 2:i + 2 + n]); i += 2 + n
        else:
            out.append(bytes([op]) if op == 0 else None)
    return out


def varint(n):
    return bytes([n]) if n < 0xfd else (b'\xfd' + n.to_bytes(2, 'little') if n <= 0xffff else b'\xfe' + n.to_bytes(4, 'little'))


def legacy_sighash(tx, i, subscript, hashtype):
    """Pre-segwit SIGHASH_ALL digest. Other hash types are reported, not computed."""
    if hashtype != 1:
        return None
    b = tx['version'].to_bytes(4, 'little') + varint(len(tx['vin']))
    for j, v in enumerate(tx['vin']):
        s = subscript if j == i else b''
        b += bytes.fromhex(v['txid'])[::-1] + v['vout'].to_bytes(4, 'little') + varint(len(s)) + s + v['sequence'].to_bytes(4, 'little')
    b += varint(len(tx['vout']))
    for o in tx['vout']:
        s = bytes.fromhex(o['script'])
        b += o['value'].to_bytes(8, 'little') + varint(len(s)) + s
    b += tx['locktime'].to_bytes(4, 'little') + hashtype.to_bytes(4, 'little')
    return sha256d(b)


def normalise(seeds, trace):
    """Common tx shape; prevout script where it is recoverable from committed data."""
    outs = {}
    txs = []
    for t in seeds.values():
        x = {'txid': t['txid'], 'height': t['status']['block_height'], 'version': t['version'], 'locktime': t['locktime'],
             'source': 'seed',
             'vin': [{'txid': v['txid'], 'vout': v['vout'], 'sequence': v['sequence'], 'scriptsig': v['scriptsig'],
                      'prev_script': v['prevout']['scriptpubkey'], 'prev_type': v['prevout']['scriptpubkey_type'],
                      'witness': v.get('witness')} for v in t['vin']],
             'vout': [{'value': o['value'], 'script': o['scriptpubkey']} for o in t['vout']]}
        txs.append(x)
    for t in trace.values():
        x = {'txid': t['txid'], 'height': int(t['height']), 'version': int(t['version']), 'locktime': int(t['lock_time']),
             'source': f"generation_{t['generation']}",
             'vin': [{'txid': v['spent_transaction_hash'], 'vout': int(v['spent_output_index']), 'sequence': int(v['sequence']),
                      'scriptsig': v.get('script_hex') or '', 'prev_script': None, 'prev_type': v.get('type'),
                      'witness': None} for v in sorted(t['inputs'], key=lambda v: v['index'])],
             'vout': [{'value': int(o['value']), 'script': o['script_hex']} for o in sorted(t['outputs'], key=lambda o: o['index'])]}
        txs.append(x)
    for x in txs:
        for k, o in enumerate(x['vout']):
            outs[(x['txid'], k)] = o['script']
    return txs, outs


def small_k_table(limit):
    x, y = G
    table_ = {x: 1}
    for k in range(2, limit + 1):
        if k == 2:
            s = (3 * x * x) * pow(2 * y, -1, P) % P
        else:
            s = (y - G[1]) * pow(x - G[0], -1, P) % P
        nx = (s * s - x - G[0]) % P if k > 2 else (s * s - 2 * x) % P
        y = (s * (x - nx) - y) % P
        x = nx
        table_[x] = k
    return table_


def signatures():
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidSignature
    seeds, trace, listed = load_seeds(), load_trace(), load_listed()
    listed_keys = {v: h for h, v in listed.items()}
    txs, outs = normalise(seeds, trace)
    for r in read(P2 / 'results/context.csv') + read(P2 / 'results/pubkeys.csv'):
        outs.setdefault((r['coinbase_txid'], int(r['output_index'])), r['output_script'])
    klim = 2**16
    smallk = small_k_table(klim)
    half = (N + 1) // 2  # k = 1/2 mod n, a known non-random nonce
    rows, stats_ = [], collections.Counter()
    seen = collections.defaultdict(list)
    for x in txs:
        for i, v in enumerate(x['vin']):
            if v['witness'] or v['prev_type'] in ('witness_v0_keyhash', 'witness_v0_scripthash', 'v0_p2wpkh', 'v0_p2wsh'):
                stats_['segwit_inputs_skipped'] += 1
                continue
            try:
                ps = pushes(v['scriptsig'])
            except Exception:
                stats_['unparsed_scriptsig'] += 1
                continue
            prev = v['prev_script'] or outs.get((v['txid'], v['vout']))
            pub = None
            if prev and len(prev) in (70, 134) and prev.endswith('ac'):
                pub = prev[2:-2]
            elif len(ps) == 2 and ps[1] and len(ps[1]) in (33, 65):
                pub = ps[1].hex()
                if not prev:
                    prev = '76a914' + hash160(ps[1]).hex() + '88ac'
            sigs = [p for p in ps if p and len(p) > 8 and p[0] == 0x30]
            for sig in sigs:
                d = parse_der(sig[:-1])
                if d is None:
                    stats_['unparsed_der'] += 1
                    continue
                r_, s_, strict = d
                ht = sig[-1]
                row = {'txid': x['txid'], 'vin': i, 'height': x['height'], 'source': x['source'],
                       'prev_type': v['prev_type'], 'listed_key_height': listed_keys.get(pub, '') if pub else '',
                       'pubkey_known': bool(pub), 'sighash_type': ht, 'der_strict': strict, 'low_s': s_ <= N // 2,
                       'r_hex': format(r_, '064x'), 'small_k': smallk.get(r_, 'half' if r_ == 0x00000000000000000000003b78ce563f89a0ed9414f5aa28ad0d96d6795f9c63 else ''),
                       'verified': ''}
                single_sig = len(sigs) == 1 and pub is not None and prev is not None
                if single_sig:
                    z = legacy_sighash(x, i, bytes.fromhex(prev), ht)
                    if z is None:
                        row['verified'] = 'unsupported_hashtype'
                    else:
                        try:
                            key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), bytes.fromhex(pub))
                            key.verify(utils.encode_dss_signature(r_, s_), z, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
                            row['verified'] = True
                        except InvalidSignature:
                            row['verified'] = False
                        except ValueError:
                            row['verified'] = 'bad_pubkey'
                    seen[r_].append((pub, z, x['txid'], i))
                else:
                    seen[r_].append((pub, None, x['txid'], i))
                rows.append(row)
    same_key, cross_key = [], []
    for r_, uses in seen.items():
        if len(uses) < 2:
            continue
        keys_ = {u[0] for u in uses}
        digests = {u[1] for u in uses if u[1] is not None}
        item = {'r_prefix': format(r_, '064x')[:16], 'uses': len(uses), 'distinct_pubkeys': len(keys_),
                'distinct_known_digests': len(digests),
                'listed_key_involved': any(u[0] in listed_keys for u in uses if u[0]),
                'txids': sorted({u[2] for u in uses})[:6]}
        (same_key if any(sum(1 for u in uses if u[0] == k and k) > 1 for k in keys_) else cross_key).append(item)
    # Commit only the forensic subset (first spends, listed keys, pre-2011 follow-ons); the rest is summarised.
    table('signature_inputs.csv', [r for r in rows if r['source'] == 'seed' or r['listed_key_height'] != '' or r['height'] < 100000])
    listed_rows = [r for r in rows if r['listed_key_height'] != '']
    save('signature_summary.json', {
        'signatures_parsed': len(rows),
        'transactions': len(txs), 'stats': dict(stats_),
        'verified': dict(collections.Counter(str(r['verified']) for r in rows)),
        'unverified_by_prev_type': dict(collections.Counter(r['prev_type'] for r in rows if r['verified'] == '')),
        'der_strict_false': sum(1 for r in rows if not r['der_strict']),
        'high_s': sum(1 for r in rows if not r['low_s']),
        'high_s_by_era': {era: {'signatures': sum(1 for r in rows if lo <= r['height'] < hi),
                                'high_s': sum(1 for r in rows if lo <= r['height'] < hi and not r['low_s'])}
                          for era, lo, hi in (('before_height_100000', 0, 100000), ('100000_to_390999', 100000, 391000),
                                              ('391000_and_later', 391000, 10**7))},
        'sighash_types': dict(collections.Counter(r['sighash_type'] for r in rows)),
        'listed_key_signatures': {
            'n': len(listed_rows), 'verified_true': sum(1 for r in listed_rows if r['verified'] is True),
            'high_s': sum(1 for r in listed_rows if not r['low_s']),
            'der_strict_false': sum(1 for r in listed_rows if not r['der_strict'])},
        'small_k_screen': {'k_range': [1, klim], 'plus_k_half': True,
                           'hits': sum(1 for r in rows if r['small_k'] != ''),
                           'listed_key_hits': sum(1 for r in listed_rows if r['small_k'] != '')},
        'r_reuse_same_pubkey': {'groups': len(same_key), 'listed_key_groups': sum(g['listed_key_involved'] for g in same_key),
                                'examples': same_key[:10]},
        'r_reuse_cross_pubkey': {'groups': len(cross_key), 'examples': cross_key[:10]},
        'policy': ('Reuse is reported only as counts and transaction references. No private key is computed. '
                   'Multisig inputs are parsed but not verified; their R values are included in reuse counts without a digest.'),
    })


# ---------------------------------------------------------------- 4. wallet fingerprint

def fingerprint():
    seeds, trace, listed = load_seeds(), load_trace(), load_listed()
    headers = load_headers()
    cb = coinbase_heights(headers)
    rows = []
    for t in sorted(seeds.values(), key=lambda t: t['status']['block_height']):
        h = t['status']['block_height']
        inkeys = {v['prevout']['scriptpubkey'] for v in t['vin']}
        types = [o['scriptpubkey_type'] for o in t['vout']]
        hs = [cb.get(v['txid']) for v in t['vin']]
        mapped = [x for x in hs if x is not None]
        seq = {v['sequence'] for v in t['vin']}
        lt = t['locktime']
        rows.append({
            'spending_txid': t['txid'], 'spending_height': h, 'time': t['status']['block_time'], 'version': t['version'],
            'locktime': lt, 'locktime_class': 'zero' if lt == 0 else ('height_near_tip' if 0 < h - lt <= 100 else ('height' if lt < 500_000_000 else 'time')),
            'sequences': ' '.join(format(s, 'x') for s in sorted(seq)),
            'rbf_signal': any(s < 0xfffffffe for s in seq), 'inputs': len(t['vin']), 'outputs': len(t['vout']),
            'output_types': ' '.join(types), 'change_to_input_key': any(o['scriptpubkey'] in inkeys for o in t['vout']),
            'payee_first': bool(t['vout'][-1]['scriptpubkey'] in inkeys) if len(t['vout']) > 1 else '',
            'fee_sats': t['fee'], 'fee_rate_sat_vb': round(t['fee'] / (t['weight'] / 4), 3),
            'inputs_height_sorted': mapped == sorted(mapped) if len(mapped) > 1 else '',
            'inputs_txid_sorted_bip69': ([ (bytes.fromhex(v['txid']), v['vout']) for v in t['vin']] ==
                                         sorted((bytes.fromhex(v['txid']), v['vout']) for v in t['vin'])) if len(t['vin']) > 1 else '',
            'round_payment': any(o['value'] % 10**8 == 0 for o in t['vout']),
            'listed_inputs': sum(1 for x in mapped if x in listed),
        })
    table('wallet_fingerprint.csv', rows)
    # follow-on: does the 2009 spender keep returning change to the same key?
    chain = []
    for t in trace.values():
        ins = t['inputs']
        if int(t['height']) > 20000:
            continue
        inaddrs = {a for v in ins for a in (v.get('addresses') or [])}
        outaddrs = [(o['index'], (o.get('addresses') or [''])[0], int(o['value'])) for o in t['outputs']]
        chain.append({'txid': t['txid'], 'height': int(t['height']), 'time': t['block_timestamp'],
                      'inputs': len(ins), 'outputs': len(outaddrs),
                      'change_to_input_address': any(a in inaddrs for _, a, _ in outaddrs),
                      'output_types': ' '.join(o.get('type', '') for o in t['outputs'])})
    chain.sort(key=lambda r: r['height'])
    table('early_followon_behaviour.csv', chain)


def manifest():
    inputs = ['patoshi_pubkeys_COMPLETE.csv', 'analysis/phase2_bigquery/results/headers.csv',
              'analysis/phase2_bigquery/results/context.csv', 'analysis/phase2_bigquery/results/pubkeys.csv',
              'analysis/phase3/trace_seed_transactions.json'] + [f'analysis/phase3/results/trace_transactions_{g}.csv' for g in (1, 2, 3)]
    digest = lambda f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
    outputs = sorted(str(f.relative_to(ROOT)).replace('\\', '/') for f in OUT.iterdir() if f.is_file() and f.name != 'manifest.json')
    save('manifest.json', {'inputs': {f: digest(f) for f in inputs}, 'outputs': {f: digest(f) for f in outputs},
                           'script': {'scripts/phase4_offline.py': digest('scripts/phase4_offline.py')}})


def main():
    cmds = {'cospend': cospend, 'sandwich': sandwich, 'signatures': signatures, 'fingerprint': fingerprint,
            'manifest': manifest}
    todo = sys.argv[1:] or list(cmds)
    for c in todo:
        cmds[c]()
        print('done', c)


if __name__ == '__main__':
    main()
