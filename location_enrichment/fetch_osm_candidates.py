#!/usr/bin/env python3
"""Fetch OSM substations once and rank location candidates for project terminals."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_BBOX = "32.0,-83.5,35.3,-78.4"


def normalized(value: str) -> str:
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"\b(substation|sub|station)\b", " ", value)
    return " ".join(re.findall(r"[a-z0-9]+", value))


def ssl_context() -> ssl.SSLContext:
    for path in ("/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem"):
        if Path(path).is_file():
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


def fetch_substations(bbox: str, terminals: list[str]) -> dict:
    names = []
    for terminal in terminals:
        name = re.sub(r"\b(substation|sub)\b", "", terminal, flags=re.IGNORECASE).strip()
        if name:
            names.append(re.escape(name))
    name_pattern = "^(" + "|".join(sorted(set(names))) + ")( Substation)?$"
    query = f"""[out:json][timeout:90];
    nwr["power"="substation"]["name"~"{name_pattern}",i]({bbox});
    out center tags;"""
    request = urllib.request.Request(
        OVERPASS_URL,
        data=urllib.parse.urlencode({"data": query}).encode("utf-8"),
        headers={"User-Agent": "GridLock-Hackathon/1.0 location-candidate-research"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120, context=ssl_context()) as response:
        return json.load(response)


def coordinates(element: dict) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    center = element.get("center") or {}
    if "lat" in center and "lon" in center:
        return center["lat"], center["lon"]
    return None


def extract_terminals(projects_path: Path) -> list[str]:
    data = json.loads(projects_path.read_text(encoding="utf-8"))
    return sorted(
        {
            terminal.strip()
            for project in data["projects"]
            for terminal in (project.get("terminal_a"), project.get("terminal_b"))
            if terminal and terminal.strip()
        }
    )


def rank_candidates(terminals: list[str], osm: dict) -> list[dict]:
    features = []
    for element in osm.get("elements", []):
        name = (element.get("tags") or {}).get("name")
        point = coordinates(element)
        if not name or point is None:
            continue
        features.append((element, name, point, normalized(name)))

    results = []
    for terminal in terminals:
        key = normalized(terminal)
        ranked = []
        for element, name, point, feature_key in features:
            score = difflib.SequenceMatcher(None, key, feature_key).ratio()
            if score < 0.58:
                continue
            exact = key == feature_key
            ranked.append(
                {
                    "name": name,
                    "latitude": point[0],
                    "longitude": point[1],
                    "operator": (element.get("tags") or {}).get("operator"),
                    "osm_type": element["type"],
                    "osm_id": element["id"],
                    "source": f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
                    "name_score": round(score, 4),
                    "exact_normalized_name": exact,
                }
            )
        ranked.sort(key=lambda item: (not item["exact_normalized_name"], -item["name_score"], item["name"]))
        top = ranked[:3]
        exact_count = sum(item["exact_normalized_name"] for item in ranked)
        results.append(
            {
                "terminal": terminal,
                "status": "exact_candidate" if exact_count == 1 else "needs_review" if top else "unknown",
                "candidates": top,
                "notes": "Coordinates are OSM candidates only; confirm against the project PDF and another public source before validation.",
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects", type=Path, default=Path("data/gemini_dominion_candidates.json"))
    parser.add_argument("--output", type=Path, default=Path("data/location_candidates_dominion.json"))
    parser.add_argument("--cache", type=Path, default=Path("data/osm_substations_sc_ga.json"))
    parser.add_argument("--bbox", default=DEFAULT_BBOX, help="south,west,north,east")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    terminals = extract_terminals(args.projects)
    if args.cache.exists() and not args.refresh:
        osm = json.loads(args.cache.read_text(encoding="utf-8"))
    else:
        try:
            osm = fetch_substations(args.bbox, terminals)
            args.cache.parent.mkdir(parents=True, exist_ok=True)
            args.cache.write_text(json.dumps(osm, ensure_ascii=False) + "\n", encoding="utf-8")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if not args.cache.exists():
                raise
            print(f"Overpass unavailable ({exc}); using existing cache {args.cache}", file=sys.stderr)
            osm = json.loads(args.cache.read_text(encoding="utf-8"))

    matches = rank_candidates(terminals, osm)
    output = {
        "schema_version": "1.0",
        "source": OVERPASS_URL,
        "bbox": args.bbox,
        "projects_reference": str(args.projects),
        "terminals": matches,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = {status: sum(item["status"] == status for item in matches) for status in ("exact_candidate", "needs_review", "unknown")}
    print(f"Wrote {len(matches)} terminal matches to {args.output}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
