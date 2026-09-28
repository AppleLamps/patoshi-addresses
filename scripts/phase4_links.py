"""Cross-reference Satoshi-associated identifiers from primary sources against committed Patoshi data. Offline."""
import csv, hashlib, json, sys
from pathlib import Path
csv.field_size_limit(1_000_000_000)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase4_offline as p4

ROOT = p4.ROOT
IDS = ROOT / 'analysis/phase4/satoshi_linked_identifiers.csv'
B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def b58check(payload):
    raw = payload + hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    n, out = int.from_bytes(raw, 'big'), ''
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    return '1' * (len(raw) - len(raw.lstrip(b'\0'))) + out


def main():
    listed = p4.load_listed()
    key_height = {v: h for h, v in listed.items()}
    addr_height = {r['p2pkh_address']: int(r['block_height']) for r in p4.read(ROOT / 'patoshi_p2pkh_addresses.csv')}
    headers = p4.load_headers()
    cb = p4.coinbase_heights(headers)
    seeds, trace = p4.load_seeds(), p4.load_trace()
    txs, outs = p4.normalise(seeds, trace)
    txids = {t['txid']: t for t in txs}
    spent_prev = {(v['txid'], v['vout']): t['txid'] for t in txs for v in t['vin']}
    out_addr = {}
    for t in trace.values():
        for o in t['outputs']:
            for a in o.get('addresses') or []:
                out_addr.setdefault(a, []).append((t['txid'], o['index']))
    for t in seeds.values():
        for k, o in enumerate(t['vout']):
            s = o['scriptpubkey']
            if o['scriptpubkey_type'] == 'p2pk':
                a = b58check(b'\0' + p4.hash160(bytes.fromhex(s[2:-2])))
            elif o['scriptpubkey_type'] == 'p2pkh':
                a = b58check(b'\0' + bytes.fromhex(s[6:46]))
            else:
                continue
            out_addr.setdefault(a, []).append((t['txid'], k))
    rows = []
    for r in p4.read(IDS):
        i, kind = r['identifier'].strip(), r['id_type'].strip().lower()
        res = {'identifier': i, 'id_type': kind, 'relationship': r['relationship'], 'evidence_strength': r['evidence_strength']}
        hits = []
        if kind == 'pubkey':
            a = b58check(b'\0' + p4.hash160(bytes.fromhex(i)))
            if i in key_height:
                hits.append(f'listed coinbase key of height {key_height[i]}')
            if a in out_addr:
                hits.append(f'receives {len(out_addr[a])} traced output(s), first {out_addr[a][0][0][:12]}:{out_addr[a][0][1]}')
            res['derived_p2pkh'] = a
        elif kind == 'address':
            if i in addr_height:
                hits.append(f'P2PKH encoding of listed key, height {addr_height[i]}')
            if i in out_addr:
                hits.append(f'receives {len(out_addr[i])} traced output(s), first {out_addr[i][0][0][:12]}:{out_addr[i][0][1]}')
        elif kind == 'txid':
            if i in txids:
                t = txids[i]
                ins = [cb.get(v['txid']) for v in t['vin']]
                hits.append(f"in trace ({t['source']}, height {t['height']}); coinbase inputs {[h for h in ins if h is not None]}; "
                            f"listed {[h for h in ins if h in listed]}")
            if i in cb:
                h = cb[i]
                hits.append(f"coinbase of height {h} ({'listed' if h in listed else 'unlisted'})")
            spent = sorted({s for (tx, _), s in spent_prev.items() if tx == i})
            if spent:
                hits.append('outputs spent in traced tx ' + ', '.join(x[:12] for x in spent))
        elif kind in ('height', 'block'):
            h = int(i)
            x = headers.get(h)
            if x:
                hits.append(f"{'listed' if h in listed else 'unlisted'}; nonce low byte {x['n'] & 255}, "
                            f"tight nonce {p4.inner_pass(x['n'])}, extraNonce {x['en']}")
        res['matches'] = ' | '.join(hits) if hits else 'no match in committed data'
        rows.append(res)
    p4.table('satoshi_linked_matches.csv', rows, ['identifier', 'id_type', 'relationship', 'evidence_strength', 'derived_p2pkh', 'matches'])
    print(json.dumps({'identifiers': len(rows), 'with_matches': sum(r['matches'] != 'no match in committed data' for r in rows)}))


if __name__ == '__main__':
    main()
