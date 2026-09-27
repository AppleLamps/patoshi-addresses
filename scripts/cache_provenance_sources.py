#!/usr/bin/env python3
"""Cache explicitly named public source files/pages, never blockchain/API endpoints.

Example: python scripts/cache_provenance_sources.py --fetch name.html=https://github.com/owner/repo
Requests are sequential with a one-second pause. Existing responses are reused.
Downloaded scripts are data only: this program never executes them.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {"github.com", "raw.githubusercontent.com", "blog.lopp.net", "bitslog.com", "satoshiblocks.info"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="append", required=True, help="local_name=public_URL")
    args = parser.parse_args()
    directory = ROOT / "analysis" / "provenance" / "sources"
    directory.mkdir(parents=True, exist_ok=True)
    for specification in args.fetch:
        name, url = specification.split("=", 1)
        parsed = urllib.parse.urlparse(url)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in (".", ".."):
            raise ValueError("Use a simple local filename")
        if parsed.scheme != "https" or parsed.hostname not in HOSTS or "/api/" in parsed.path:
            raise ValueError("Only allowlisted public HTTPS source pages/files are permitted")
        path = directory / name
        metadata = directory / (name + ".metadata.json")
        if path.exists() and metadata.exists():
            saved = json.loads(metadata.read_text())
            if saved["requested_url"] != url or hashlib.sha256(path.read_bytes()).hexdigest() != saved["sha256"]:
                raise ValueError("Cache URL/hash mismatch; select a new filename")
            print(json.dumps({"cached": True, **saved}))
            continue
        record = {"requested_url": url, "fetched_at_utc": datetime.now(timezone.utc).isoformat()}
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "PatoshiProvenanceResearch/1.0"})
            with urllib.request.urlopen(request, timeout=40) as response:
                body = response.read()
                record.update(status=response.status, final_url=response.url,
                              headers=dict(response.headers.items()))
        except urllib.error.HTTPError as error:
            body = error.read()
            record.update(status=error.code, final_url=error.url, error=str(error), headers=dict(error.headers.items()))
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            body = b""
            record.update(status=None, error=str(error))
        record.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        path.write_bytes(body)
        metadata.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({k:v for k,v in record.items() if k != "headers"}), flush=True)
        time.sleep(1)


if __name__ == "__main__":
    main()
