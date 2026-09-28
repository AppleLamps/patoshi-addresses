#!/usr/bin/env python3
"""Bounded Debian OpenSSL 0.9.8c-era/CVE-2008-0166 public-key screen.

Never writes candidate private scalars. Historical OpenSSL behavior is modeled
from md_rand.c, rand_unix.c, bn_rand.c and ec_key.c; see the companion report.
"""

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "phase3" / "debian"
CACHE = ROOT / "analysis" / "phase3" / "cache" / "debian"
CSV = ROOT / "patoshi_pubkeys_COMPLETE.csv"
ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
ARCHES = (("le64", 8, "little"), ("le32", 4, "little"),
          ("be32", 4, "big"), ("be64-synthetic", 8, "big"))
PATHS = ("poll-first", "keygen-first", "old-cli-nornd", "cli-rnd")
STAT_BYTES = {"le64": 144, "le32": 88, "be32": 88}
VECTORS = {
    "le64": ("baa8d5620e1abed385dc25b9642d8e7f93bb5f82268bd742d64ba216eafb0925",
             "72acf44b7600b66afe30f912e1f2a7ddfc241e91c3a4300febc9e48f64764dfc"),
    "le32": ("5e4c441127c7c1411ed65526511a95b5777856f1c704c7836eec8063aeae188c",
             "2712998f17bb7f11feeb7c3101ce6be4f072b0410a471840229502d5d10a4876"),
    "be32": ("15a69e96dfe0e0df516a7b9d9b01ca3fd25997e8de6ef876c7325f69920615ea",
             "480b5d064246f3973ec3506cba8ba8b34df730e1a6739c165aa08f34c2076bf9"),
}
OTHER_VECTORS = {
    "old-cli-nornd": {
        "le64": ("51b4046e700a439c8b61c529aeaa3c40095ef19b4311c0586b4bb1639b74514b",
                 "abbc41cc42b97550711bcb79505f6b73c5ff247ad9b298e4ff231c665b846502"),
        "le32": ("fbf51e061a6b859a492f7f02fb7c1be33457c0142f05e76fa737a98a78d2a6b8",
                 "80fa2da8fb024749af7bcbe878583dad63999bf661df5b43685fa83e371811d1"),
        "be32": ("0e28e6c6b63181f6dcd94c990089ce1ad1ee1a041525e66ae43a6f9cb4efb4ba",
                 "169597f9c42a010804f4e1d21b2bbe886f322d9e3a13e6425d3d003cfbe80dd5"),
    },
    "cli-rnd": {
        "le64": ("2aae6eedfb4b5916c3dee26346493c2e2a018904343292c0d1760e813054894f",
                 "f9d282434687b7a13c0030ff8f516817407a91e6980813af4add47a46c685114"),
        "le32": ("47225109bc9fd00eb958fc065a0a6adf90890da8a8d96553471fcad7363a76fe",
                 "7856362b44ca8d789b4e09547b9fcd6aa710c396d2d4be6addc38552303493d4"),
        "be32": ("d9a676655a5ba9355bf1421552e56e81d7a611719c89e841431ffbe7b9b0d713",
                 "8de1e14d4378470eac2bbfaa3c272472ffd65ee78dfb75431fab4e80a3297f6a"),
    },
}


def startup(rng, arch, mode):
    if mode == "poll-first":
        rng.poll()
    elif mode == "keygen-first":
        pass
    elif mode == "old-cli-nornd":
        rng.add(STAT_BYTES[arch])
        rng.poll()
    elif mode == "cli-rnd":
        rng.add(STAT_BYTES[arch])
        rng.add(1024, 1024)
    else:
        raise ValueError(mode)


class DebianRNG:
    """SHA-1 SSLeay RNG with both Debian-disabled MD_Update(buf) calls."""

    def __init__(self, pid: int, word_bytes: int, endian: str):
        self.pid, self.word_bytes, self.endian = pid, word_bytes, endian
        self.state = bytearray(1023)
        self.md = bytes(20)
        self.count = [0, 0]
        self.index = self.state_num = 0
        self.entropy = 0
        self.initialized = self.stirred = False

    def words(self, values):
        return b"".join(x.to_bytes(self.word_bytes, self.endian) for x in values)

    def segment(self, start, length, modulus):
        return bytes(self.state[(start + i) % modulus] for i in range(length))

    def add(self, length, credited_entropy=0):
        # The patched RAND_add ignores the input bytes, but their length advances
        # state_index and md_count. Replaying call sizes is therefore essential.
        index, local_count, local_md = self.index, self.count.copy(), self.md
        self.index += length
        if self.index >= 1023:
            self.index %= 1023
            self.state_num = 1023
        else:
            self.state_num = max(self.state_num, self.index)
        self.count[1] += (length + 19) // 20
        for offset in range(0, length, 20):
            width = min(length - offset, 20)
            local_md = hashlib.sha1(local_md + self.segment(index, width, 1023)
                                    + self.words(local_count)).digest()
            local_count[1] += 1
            for i in range(width):
                self.state[(index + i) % 1023] ^= local_md[i]
            index = (index + width) % 1023
        self.md = bytes(a ^ b for a, b in zip(self.md, local_md))
        self.entropy = min(32, self.entropy + credited_entropy)

    def poll(self):
        # Linux rand_unix.c: 32 bytes from /dev/urandom, then PID, UID, time
        # as three unsigned longs. Their values have no effect under this patch.
        self.add(32, 32)
        for _ in range(3):
            self.add(self.word_bytes)
        self.initialized = True

    def rand_bytes(self, length):
        if not self.initialized:
            self.poll()
        ok = self.entropy >= 32
        if not ok:
            self.entropy = max(0, self.entropy - length)
        if not self.stirred:
            remaining = 1023
            while remaining > 0:
                self.add(20)
                remaining -= 20
            if ok:
                self.stirred = True
        index, modulus, local_count, local_md = (
            self.index, self.state_num, self.count.copy(), self.md)
        rounded = ((length + 9) // 10) * 10
        self.index += rounded
        if self.index > self.state_num:
            self.index %= self.state_num
        self.count[0] += 1
        out = bytearray()
        first = True
        while length:
            take = min(length, 10)
            length -= take
            pid_bytes = self.pid.to_bytes(4, self.endian) if first else b""
            first = False
            local_md = hashlib.sha1(pid_bytes + local_md + self.words(local_count)
                                    + self.segment(index, 10, modulus)).digest()
            for i in range(10):
                self.state[index] ^= local_md[i]
                index = (index + 1) % modulus
            out.extend(local_md[10:10 + take])
        self.md = hashlib.sha1(self.words(local_count) + local_md + self.md).digest()
        return bytes(out)

    def ec_keygen(self, order):
        # ec_key.c: EC_KEY_generate_key -> BN_rand_range. bn_rand.c calls
        # RAND_add(time_t, sizeof(time_t), 0) immediately before RAND_bytes.
        # For the historical Linux ABIs here, sizeof(time_t) == sizeof(long).
        while True:
            self.add(self.word_bytes)
            scalar = self.rand_bytes(32)
            value = int.from_bytes(scalar, "big")
            if 0 < value < order:
                return value


def target_keys():
    targets = {}
    with CSV.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            raw = bytes.fromhex(row["Address/Pubkey"])
            assert len(raw) == 65 and raw[0] == 4
            compressed = bytes([2 + (raw[-1] & 1)]) + raw[1:33]
            assert compressed not in targets
            targets[compressed] = (int(row["Block Height"]), raw.hex())
    assert len(targets) == 21953
    return targets


def validate_vectors(download=False):
    records = []
    CACHE.mkdir(parents=True, exist_ok=True)
    for arch, size, endian in ARCHES[:3]:
        for mode, suffix in (("poll-first", "nornd-new"),
                             ("old-cli-nornd", "nornd-old"),
                             ("cli-rnd", "rnd")):
            hashes = VECTORS[arch] if mode == "poll-first" else OTHER_VECTORS[mode][arch]
            url = ("https://raw.githubusercontent.com/badkeys/debianopenssl/main/"
                   f"ecp256/ssl/{arch}/1-{suffix}.key")
            path = CACHE / f"vector_{arch}_pid1_{suffix}.pem"
            if not path.exists():
                if not download:
                    raise FileNotFoundError(f"{path}; rerun with --download-vectors")
                path.write_bytes(urllib.request.urlopen(url, timeout=30).read())
            source = path.read_bytes()
            digest = hashlib.sha256(source).hexdigest()
            assert digest == hashes[0], (arch, suffix, "source changed", digest)
            key = serialization.load_pem_private_key(source, password=None)
            assert isinstance(key.curve, ec.SECP256R1)
            expected = key.private_numbers().private_value
            rng = DebianRNG(1, size, endian)
            startup(rng, arch, mode)
            actual = rng.ec_keygen(1 << 256)
            assert actual == expected, (arch, suffix, "PRNG did not reproduce published key")
            pub = ec.derive_private_key(actual, ec.SECP256R1()).public_key()
            x = pub.public_numbers().x
            assert x == int(hashes[1], 16)
            assert pub.public_numbers() == key.public_key().public_numbers()
            records.append({"architecture": arch, "startup": mode,
                            "pid": 1, "source": url, "pem_sha256": digest,
                            "public_x": f"{x:064x}",
                            "prng_scalar_matches_published": True,
                            "derived_public_key_matches_published": True})
    return records


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix(path.suffix + ".tmp")
    with staging.open("w", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    # OneDrive can hold the destination open briefly while syncing checkpoints.
    for attempt in range(20):
        try:
            staging.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.25)


def csv_sha256():
    # Git stores this CSV with LF; Windows working trees may check it out CRLF.
    return hashlib.sha256(CSV.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def scan(args, validations, targets):
    started = time.time()
    selected = [(a, w, e, p) for a, w, e in ARCHES for p in PATHS
                if (args.arch is None or args.arch == a)
                and (args.path is None or args.path == p)]
    selected = [s for s in selected if s[3] in PATHS[:2] or s[0] in STAT_BYTES]
    assert selected
    stop_path = CACHE / "stop_on_hit"
    for arch, width, endian, path in selected:
            label = f"{arch}/{path}"
            progress_path = CACHE / f"progress_{arch}_{path}.json"
            progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
            last = progress.get("last_pid", 0)
            if last >= args.max_pid:
                continue
            scanned = 0
            for pid in range(last + 1, args.max_pid + 1):
                if stop_path.exists():
                    print("STOP SIGNAL FOUND; abandoning", label, flush=True)
                    return 2
                rng = DebianRNG(pid, width, endian)
                startup(rng, arch, path)
                for offset in range(16):
                    candidate = rng.ec_keygen(ORDER)
                    pub = ec.derive_private_key(candidate, ec.SECP256K1()).public_key()
                    compressed = pub.public_bytes(
                        serialization.Encoding.X962,
                        serialization.PublicFormat.CompressedPoint)
                    scanned += 1
                    if compressed in targets:
                        height, csv_pub = targets[compressed]
                        chain_pub = pub.public_bytes(
                            serialization.Encoding.X962,
                            serialization.PublicFormat.UncompressedPoint).hex()
                        assert chain_pub == csv_pub
                        hit = {"height": height, "pid": pid, "architecture": arch,
                               "path": path, "keygen_offset_zero_based": offset,
                               "csv_public_key": csv_pub,
                               "derived_public_key": chain_pub,
                               "status": "STOPPED FOR INDEPENDENT ON-CHAIN VERIFICATION"}
                        write_json(OUT / "hit_pending.json", hit)
                        stop_path.write_text("candidate match; independent chain check required\n")
                        print("HIT -- STOPPED -- see", OUT / "hit_pending.json", flush=True)
                        return 2
                # Checkpoints contain counts only. No candidate scalar or key bytes.
                if pid % 128 == 0 or pid == args.max_pid:
                    progress = {"label": label, "last_pid": pid}
                    write_json(progress_path, progress)
                    rate = scanned / max(time.time() - started, .001)
                    print(f"{label} PID {pid}/{args.max_pid}; {scanned} candidates this run; "
                          f"{rate:.1f}/s", flush=True)
            result = {"status": "bounded_null", "label": label,
                      "target_public_keys": len(targets),
                      "pid_range_inclusive": [1, args.max_pid],
                      "keygen_offsets_zero_based": [0, 15],
                      "enumerated_candidate_slots": args.max_pid * 16,
                      "hits": 0, "target_csv_sha256": csv_sha256(),
                      "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            write_json(OUT / f"worker_{arch}_{path}.json", result)
            print("COMPLETE", label, result["enumerated_candidate_slots"], flush=True)
    return 0


def aggregate(validations):
    workers = []
    for arch, _, _ in ARCHES:
        for path in (PATHS if arch in STAT_BYTES else PATHS[:2]):
            p = OUT / f"worker_{arch}_{path}.json"
            data = json.loads(p.read_text())
            assert data["label"] == f"{arch}/{path}"
            assert data["pid_range_inclusive"] == [1, 32767]
            assert data["keygen_offsets_zero_based"] == [0, 15]
            assert data["status"] == "bounded_null" and data["hits"] == 0
            assert data["target_csv_sha256"] == csv_sha256()
            workers.append(data)
    assert not (OUT / "hit_pending.json").exists()
    result = {"status": "bounded_null", "target_public_keys": 21953,
              "pid_range_inclusive": [1, 32767],
              "architectures": [a for a, _, _ in ARCHES],
              "paths_by_architecture": {a: list(PATHS if a in STAT_BYTES else PATHS[:2])
                                        for a, _, _ in ARCHES},
              "keygen_offsets_zero_based": [0, 15],
              "enumerated_candidate_slots": sum(x["enumerated_candidate_slots"] for x in workers),
              "hits": 0, "vector_validations": validations,
              "target_csv_sha256": csv_sha256(),
              "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_json(OUT / "result.json", result)
    print("COMPLETE", result["enumerated_candidate_slots"], flush=True)


def manifest():
    paths = [CSV, Path(__file__), OUT / "REPORT.md", OUT / "validation.json",
             OUT / "result.json", *sorted(OUT.glob("worker_*.json"))]
    assert len(paths) == 19  # pinned input, code, report, validation, result, 14 workers
    records = []
    for path in paths:
        data = path.read_bytes()
        entry = {"path": str(path.relative_to(ROOT)).replace("\\", "/")}
        if path == CSV:
            data = data.replace(b"\r\n", b"\n")
            entry["normalization"] = "CRLF to LF"
        entry.update({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        records.append(entry)
    write_json(OUT / "manifest.json", {"files": records})
    print("Checksummed", len(records), "files", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("vectors", "scan", "aggregate", "manifest"))
    parser.add_argument("--download-vectors", action="store_true")
    parser.add_argument("--max-pid", type=int, default=32767)
    parser.add_argument("--arch", choices=[a for a, _, _ in ARCHES])
    parser.add_argument("--path", choices=PATHS)
    args = parser.parse_args()
    assert 1 <= args.max_pid <= 32767
    if args.action == "manifest":
        manifest()
        return 0
    validations = validate_vectors(args.download_vectors)
    write_json(OUT / "validation.json", {"published_p256_vectors": validations})
    print(f"Validated {len(validations)} published Debian weak P-256 vectors", flush=True)
    if args.action == "vectors":
        return 0
    if args.action == "aggregate":
        aggregate(validations)
        return 0
    return scan(args, validations, target_keys())


if __name__ == "__main__":
    sys.exit(main())
