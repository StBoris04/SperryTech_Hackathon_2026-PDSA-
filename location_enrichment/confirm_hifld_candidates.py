#!/usr/bin/env python3
"""Confirm exact OSM terminal candidates against the public HIFLD ArcGIS layer."""

from __future__ import annotations

import argparse
import json
import math
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from location_enrichment.fetch_osm_candidates import normalized
except ModuleNotFoundError:  # Direct script execution.
    from fetch_osm_candidates import normalized


LAYER_URL = "https://services2.arcgis.com/6VIt2tukGNSxkmi6/arcgis/rest/services/DEMO_Substations/FeatureServer/8"
QUERY_URL = f"{LAYER_URL}/query"


def ssl_context() -> ssl.SSLContext:
    for path in ("/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem"):
        if Path(path).is_file():
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


def fetch_hifld() -> dict:
    features = []
    offset = 0
    while True:
        params = {
            "where": "STATE IN ('SC','GA')",
            "outFields": "ID,NAME,CITY,STATE,STATUS,LATITUDE,LONGITUDE,SOURCE,SOURCEDATE,VAL_METHOD,VAL_DATE,MAX_VOLT",
            "returnGeometry": "false",
            "orderByFields": "OBJECTID",
            "f": "json",
            "resultOffset": str(offset),
            "resultRecordCount": "2000",
        }
        url = f"{QUERY_URL}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"User-Agent": "GridLock-Hackathon/1.0 public-location-validation"})
        with urllib.request.urlopen(request, timeout=120, context=ssl_context()) as response:
            page = json.load(response)
        if "error" in page:
            raise RuntimeError(f"HIFLD query failed: {page['error']}")
        page_features = page.get("features", [])
        features.extend(page_features)
        if len(page_features) < 2000:
            return {"features": features}
        offset += len(page_features)


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radius_miles * math.asin(math.sqrt(a))


def confirm(
    osm_data: dict,
    hifld_data: dict,
    tolerance_miles: float,
    spatial_tolerance_miles: float = 0.1,
) -> list[dict]:
    by_name: dict[str, list[dict]] = {}
    for feature in hifld_data.get("features", []):
        attrs = feature.get("attributes") or {}
        if attrs.get("NAME") and attrs.get("LATITUDE") is not None and attrs.get("LONGITUDE") is not None:
            by_name.setdefault(normalized(attrs["NAME"]), []).append(attrs)

    results = []
    for item in osm_data["terminals"]:
        if item["status"] != "exact_candidate" or not item["candidates"]:
            continue
        osm = item["candidates"][0]
        exact_name_matches = []
        all_matches = []
        for feature in hifld_data.get("features", []):
            attrs = feature.get("attributes") or {}
            if attrs.get("LATITUDE") is None or attrs.get("LONGITUDE") is None:
                continue
            distance = haversine_miles(osm["latitude"], osm["longitude"], attrs["LATITUDE"], attrs["LONGITUDE"])
            all_matches.append((distance, attrs))
            if normalized(attrs.get("NAME") or "") == normalized(item["terminal"]):
                exact_name_matches.append((distance, attrs))
        exact_name_matches.sort(key=lambda pair: pair[0])
        all_matches.sort(key=lambda pair: pair[0])
        exact_nearest = exact_name_matches[0] if exact_name_matches else None
        spatial_nearest = all_matches[0] if all_matches else None
        nearest = exact_nearest if exact_nearest and exact_nearest[0] <= tolerance_miles else spatial_nearest
        confirmed_by_name = exact_nearest is not None and exact_nearest[0] <= tolerance_miles
        confirmed_by_space = spatial_nearest is not None and spatial_nearest[0] <= spatial_tolerance_miles
        confirmed = confirmed_by_name or confirmed_by_space
        method = "exact name across OSM and HIFLD" if confirmed_by_name else "exact PDF/OSM name plus colocated HIFLD facility"
        results.append(
            {
                "terminal": item["terminal"],
                "status": "confirmed" if confirmed else "needs_review",
                "distance_between_sources_miles": round(nearest[0], 4) if nearest else None,
                "recommended_latitude": osm["latitude"] if confirmed else None,
                "recommended_longitude": osm["longitude"] if confirmed else None,
                "location_quality": "verified" if confirmed else "unknown",
                "osm": osm,
                "hifld": nearest[1] if nearest else None,
                "sources": [osm["source"], LAYER_URL] if confirmed else [osm["source"]],
                "notes": f"Confirmed by {method}."
                if confirmed
                else "No sufficiently close exact-name HIFLD confirmation; do not use coordinates yet.",
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osm", type=Path, default=Path("data/location_candidates_dominion.json"))
    parser.add_argument("--cache", type=Path, default=Path("data/hifld_substations_sc_ga.json"))
    parser.add_argument("--output", type=Path, default=Path("data/dominion_location_confirmations.json"))
    parser.add_argument("--tolerance-miles", type=float, default=2.0)
    parser.add_argument("--spatial-tolerance-miles", type=float, default=0.1)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    if args.cache.exists() and not args.refresh:
        hifld = json.loads(args.cache.read_text(encoding="utf-8"))
    else:
        hifld = fetch_hifld()
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        args.cache.write_text(json.dumps(hifld, ensure_ascii=False) + "\n", encoding="utf-8")
    osm = json.loads(args.osm.read_text(encoding="utf-8"))
    confirmations = confirm(osm, hifld, args.tolerance_miles, args.spatial_tolerance_miles)
    output = {
        "schema_version": "1.0",
        "method": "exact normalized terminal name plus OSM/HIFLD separation <= tolerance",
        "tolerance_miles": args.tolerance_miles,
        "spatial_tolerance_miles": args.spatial_tolerance_miles,
        "hifld_source": LAYER_URL,
        "terminals": confirmations,
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    confirmed_count = sum(item["status"] == "confirmed" for item in confirmations)
    print(f"Confirmed {confirmed_count}/{len(confirmations)} exact OSM terminal candidates; wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
