"""Write docs/price.json with the current BTC/USD price for the website.

Queries several public spot-price endpoints and records the median of the
ones that answer, so one stale or failing exchange cannot skew the value.
Run by .github/workflows/update-price.yml every 12 hours.
"""
import json
import statistics
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "price.json"

SOURCES = {
    "Coinbase": ("https://api.coinbase.com/v2/prices/BTC-USD/spot",
                 lambda d: d["data"]["amount"]),
    "Kraken": ("https://api.kraken.com/0/public/Ticker?pair=XBTUSD",
               lambda d: next(iter(d["result"].values()))["c"][0]),
    "CoinGecko": ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
                  lambda d: d["bitcoin"]["usd"]),
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "patoshi-addresses-price/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def main():
    quotes = {}
    for name, (url, pick) in SOURCES.items():
        try:
            value = float(pick(fetch(url)))
        except Exception as exc:  # one failing source should not stop the update
            print(f"{name}: failed ({exc})", file=sys.stderr)
            continue
        if value > 0:
            quotes[name] = value
            print(f"{name}: {value:,.2f}")
    if not quotes:
        sys.exit("No price source answered; docs/price.json left unchanged.")

    out = {
        "btc_usd": round(statistics.median(quotes.values()), 2),
        "sources": sorted(quotes),
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
