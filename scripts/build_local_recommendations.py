#!/usr/bin/env python3
"""Build an offline recommendation snapshot from the reviewed master dataset."""

import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from recommendations.engine import build_recommendations, index_projects


def distance_miles(a, b):
    lat1, lat2 = math.radians(a["latitude"]), math.radians(b["latitude"])
    delta_lat = math.radians(b["latitude"] - a["latitude"])
    delta_lon = math.radians(b["longitude"] - a["longitude"])
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(value))


def main():
    payload = json.loads((ROOT / "data/master_projects.json").read_text())
    projects = [
        project for project in payload["projects"]
        if project["review_status"] == "validated"
        and project.get("latitude") is not None
        and project.get("longitude") is not None
    ]
    opportunities = []
    for index, project_a in enumerate(projects):
        for project_b in projects[index + 1:]:
            if project_a["utility_id"] == project_b["utility_id"]:
                continue
            distance = distance_miles(project_a, project_b)
            if distance > 25:
                continue
            first, second = sorted((project_a["project_id"], project_b["project_id"]))
            opportunities.append({
                "project_id_a": first,
                "project_id_b": second,
                "distance_miles": distance,
                "distance_method": "haversine_wgs84_local_snapshot",
                "location_uncertain": project_a["location_quality"] != "verified" or project_b["location_quality"] != "verified",
                "timeline_status": "unknown",
                "reason": "Local deterministic snapshot: validated cross-utility representative points within 25 miles; timing remains unknown.",
            })
    opportunities.sort(key=lambda item: (item["distance_miles"], item["project_id_a"], item["project_id_b"]))
    result = build_recommendations(opportunities, index_projects(payload))
    result["source"] = "local_deterministic_snapshot"
    destination = ROOT / "public/recommendations.json"
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {len(result['recommendations'])} local recommendations to {destination}")


if __name__ == "__main__":
    main()
