"""Small cached live capability probes using the same provider and rate limiter."""
import json
from phase2_collect import CONTROLS, HOSTS, OUT, Store, atomic_json, now

s = Store(2)
txids = [s.get("coinbase", h)["txid"] for h in CONTROLS]
probes = [
    (2817, "/v1/blocks-bulk/2817/2818"),
    (2817, "/txs/outspends?txids=" + ",".join(txids)),
]
report = []
for h, endpoint in probes:
    try:
        data, ref = s.fetch(h, endpoint, hosts=HOSTS[:1], max_attempts=1)
        item = {"endpoint": endpoint, "ok": True, "response": ref, "count": len(data), "sample": data[0]}
    except Exception as e:
        item = {"endpoint": endpoint, "ok": False, "error": str(e)}
    report.append(item)
    print(json.dumps(item), flush=True)
atomic_json(OUT / "bulk_probe.json", {"at": now(), "probes": report})
s.db.close()
