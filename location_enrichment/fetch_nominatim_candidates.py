#!/usr/bin/env python3
"""Find missing Dominion terminal candidates with a slow, cached Nominatim pass."""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from location_enrichment.fetch_osm_candidates import normalized, ssl_context
except ModuleNotFoundError:
    from fetch_osm_candidates import normalized, ssl_context

SEARCH_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "GridLock-Hackathon/1.0 one-time-cached-terminal-research"


def search(terminal: str) -> list[dict]:
    params = {"q": f"{terminal} substation, South Carolina, USA", "format": "jsonv2", "limit": "3", "countrycodes": "us", "viewbox": "-83.5,35.3,-78.4,32.0", "bounded": "1", "addressdetails": "1", "extratags": "1"}
    request = urllib.request.Request(f"{SEARCH_URL}?{urllib.parse.urlencode(params)}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60, context=ssl_context()) as response:
        return json.load(response)


def candidate(item: dict) -> dict:
    osm_type = {"node": "node", "way": "way", "relation": "relation"}.get(item.get("osm_type"))
    osm_id = item.get("osm_id")
    return {"name": item.get("name") or item.get("display_name", "").split(",", 1)[0], "display_name": item.get("display_name"), "latitude": float(item["lat"]), "longitude": float(item["lon"]), "category": item.get("category"), "type": item.get("type"), "osm_type": osm_type, "osm_id": osm_id, "source": f"https://www.openstreetmap.org/{osm_type}/{osm_id}" if osm_type and osm_id else SEARCH_URL}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--existing", type=Path, default=Path("data/location_candidates_dominion.json"))
    parser.add_argument("--cache", type=Path, default=Path("data/nominatim_dominion_cache.json"))
    parser.add_argument("--output", type=Path, default=Path("data/nominatim_candidates_dominion.json"))
    parser.add_argument("--delay", type=float, default=1.1)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    existing = json.loads(args.existing.read_text(encoding="utf-8"))
    terminals = [item["terminal"] for item in existing["terminals"] if item["status"] != "exact_candidate"]
    cache = json.loads(args.cache.read_text(encoding="utf-8")) if args.cache.exists() else {}
    for terminal in terminals:
        if terminal in cache and not args.refresh:
            continue
        cache[terminal] = search(terminal)
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        args.cache.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        time.sleep(max(args.delay, 1.0))

    results = []
    for terminal in terminals:
        candidates = [candidate(item) for item in cache.get(terminal, [])]
        results.append({"terminal": terminal, "normalized_terminal": normalized(terminal), "status": "candidate" if candidates else "unknown", "candidates": candidates, "notes": "Search result only; coordinates require independent HIFLD corroboration."})
    output = {"schema_version": "1.0", "source": SEARCH_URL, "method": "one-time sequential cached search, maximum one request per second", "terminals": results}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} missing-terminal searches to {args.output}; {sum(bool(x['candidates']) for x in results)} have candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
