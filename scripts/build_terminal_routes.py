#!/usr/bin/env python3
"""Build a frontend route asset from already-reviewed terminal evidence."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compact(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def source_id(project):
    match = re.search(r"Source [Pp]roject ID\s+([^.;]+)", project.get("notes") or "")
    return compact(match.group(1) if match else re.sub(r"^(DESC|GPC)_", "", project["project_id"]))


def load_json(path):
    return json.loads((ROOT / path).read_text())


def main():
    projects = load_json("data/master_projects.json")["projects"]
    configs = {
        "dominion_sc": ("data/gemini_dominion_candidates.json", "data/dominion_location_confirmations.json"),
        "georgia_power": ("data/gemini_georgia_candidates.json", "data/georgia_location_confirmations.json"),
    }
    routes = []
    for utility_id, (candidate_path, confirmation_path) in configs.items():
        candidates = {compact(item.get("source_project_id")): item for item in load_json(candidate_path)["projects"]}
        confirmed = {
            item["terminal"].casefold(): item
            for item in load_json(confirmation_path)["terminals"]
            if item.get("status") == "confirmed"
        }
        for project in projects:
            if project["utility_id"] != utility_id:
                continue
            candidate = candidates.get(source_id(project))
            if not candidate:
                continue
            terminals = []
            for field in ("terminal_a", "terminal_b"):
                name = candidate.get(field)
                evidence = confirmed.get(name.casefold()) if name else None
                if evidence:
                    terminals.append({
                        "name": evidence["terminal"],
                        "latitude": evidence["recommended_latitude"],
                        "longitude": evidence["recommended_longitude"],
                        "location_quality": evidence["location_quality"],
                    })
            if terminals:
                routes.append({"project_id": project["project_id"], "terminals": terminals})

    output = {"schema_version": "1.0", "routes": routes}
    destination = ROOT / "public/terminal_routes.json"
    destination.write_text(json.dumps(output, indent=2) + "\n")
    complete = sum(len(route["terminals"]) == 2 for route in routes)
    print(f"Wrote {len(routes)} reviewed terminal records ({complete} complete routes) to {destination}")


if __name__ == "__main__":
    main()
