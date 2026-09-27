#!/usr/bin/env python3
"""Build the two-utility master handoff without relabeling other sponsors."""

from __future__ import annotations

import json
import re
from pathlib import Path


VALIDATED_PATH = Path("data/validated_projects.json")
CANDIDATES_PATH = Path("data/all_pdf_project_candidates.json")
GEMINI_GEORGIA_PATH = Path("data/gemini_georgia_candidates.json")
GEORGIA_LOCATIONS_PATH = Path("data/georgia_location_confirmations.json")
OUTPUT_PATH = Path("data/master_projects.json")
EXCEL_REFERENCE = "Challenge Docs/Projects_Overlaps.xlsx"

EXCEL_GPC = {
    "20793": ("GPC_1", "projects!row 7", "GA"),
    "18492": ("GPC_4", "projects!row 10", "GA"),
    "11821": ("GPC_5", "projects!row 11", "GA"),
}


def generated_id(source_project_id: str) -> str:
    token = re.sub(r"[^A-Z0-9]+", "_", source_project_id.upper()).strip("_")
    return f"GPC_{token}"


def main() -> int:
    validated = json.loads(VALIDATED_PATH.read_text(encoding="utf-8"))["projects"]
    dominion = [item for item in validated if item["utility_id"] == "dominion_sc"]
    raw = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))["projects"]

    # Terminal names for Georgia Power come from a later Gemini pass that assigned
    # them; all_pdf_project_candidates.json left terminal_a/terminal_b null for
    # every Georgia record. Join by source_project_id only within the Georgia
    # Power records already selected below, never by name.
    gemini_terminals: dict[str, tuple[str | None, str | None]] = {}
    if GEMINI_GEORGIA_PATH.exists():
        for entry in json.loads(GEMINI_GEORGIA_PATH.read_text(encoding="utf-8"))["projects"]:
            gemini_terminals[str(entry["source_project_id"])] = (
                entry.get("terminal_a"),
                entry.get("terminal_b"),
            )

    confirmed_locations: dict[str, dict] = {}
    if GEORGIA_LOCATIONS_PATH.exists():
        confirmed_locations = {
            entry["terminal"]: entry
            for entry in json.loads(GEORGIA_LOCATIONS_PATH.read_text(encoding="utf-8"))["terminals"]
            if entry["status"] == "confirmed"
        }

    georgia = []
    for item in raw:
        if item.get("company") != "Georgia Power":
            continue
        source_id = str(item["source_project_id"])
        excel = EXCEL_GPC.get(source_id)
        project_id = excel[0] if excel else generated_id(source_id)

        gemini_a, gemini_b = gemini_terminals.get(source_id, (None, None))
        terminals = [value for value in (gemini_a, gemini_b, item.get("terminal_a"), item.get("terminal_b")) if value]
        # De-duplicate while keeping order (a source can repeat a name via both files).
        terminals = list(dict.fromkeys(terminals))
        confirmed = [confirmed_locations[name] for name in terminals if name in confirmed_locations]

        latitude = longitude = None
        location_quality = "unknown"
        location_method = None
        if confirmed:
            latitude = sum(entry["recommended_latitude"] for entry in confirmed) / len(confirmed)
            longitude = sum(entry["recommended_longitude"] for entry in confirmed) / len(confirmed)
            location_quality = "approximate"
            location_method = (
                "Midpoint of two terminal coordinates independently corroborated by OSM and HIFLD"
                if len(confirmed) == 2
                else f"Representative point uses confirmed terminal {confirmed[0]['terminal']}; other terminal unavailable"
            )

        sources = []
        if excel:
            sources.append({"reference": EXCEL_REFERENCE, "locator": excel[1], "supports": ["project_id", "state"]})
        supported = ["utility_id", "project_name", "project_type", "description", "location_text", "construction_start", "construction_end", "in_service_date", "schedule_text"]
        sources.append(
            {
                "reference": item["source"]["reference"],
                "locator": f"PDF page {item['source']['pdf_page']} (printed {item['source'].get('printed_page')})",
                "supports": supported,
            }
        )
        if confirmed:
            location_supported = ["latitude", "longitude", "location_quality", "location_method"]
            seen_references = set()
            for entry in confirmed:
                for reference in entry["sources"]:
                    if reference in seen_references:
                        continue
                    seen_references.add(reference)
                    sources.append(
                        {
                            "reference": reference,
                            "locator": f"Terminal: {entry['terminal']}",
                            "supports": location_supported,
                        }
                    )

        notes = [f"Source project ID {source_id}; sponsor Georgia Power."]
        if item.get("need_date"):
            notes.append(f"Need Date {item['need_date']} is preserved in schedule_text and is not an in-service date.")
        missing_terminals = [name for name in terminals if name not in confirmed_locations]
        if missing_terminals:
            notes.append(f"Unconfirmed terminals: {', '.join(missing_terminals)}.")
        if len(confirmed) == 1:
            notes.append("Representative point is one endpoint, not the route midpoint.")
        if terminals and not confirmed:
            notes.append("No terminal coordinates passed OSM/HIFLD confirmation; coordinates remain null.")
        stale_note = "Terminals were not assigned automatically; review the title and description."
        notes.extend(
            note for note in (item.get("uncertainties") or [])
            if not (gemini_a or gemini_b) or note != stale_note
        )
        georgia.append(
            {
                "project_id": project_id,
                "utility_id": "georgia_power",
                "project_name": item["project_name"],
                "project_type": item["project_type"],
                "state": excel[2] if excel else None,
                "description": item.get("description"),
                "location_text": " - ".join(terminals) if terminals else None,
                "latitude": round(latitude, 7) if latitude is not None else None,
                "longitude": round(longitude, 7) if longitude is not None else None,
                "location_quality": location_quality,
                "location_method": location_method,
                "construction_start": item.get("construction_start"),
                "construction_end": item.get("construction_end"),
                "in_service_date": item.get("in_service_date"),
                "schedule_text": item.get("schedule_text"),
                "sources": sources,
                "review_status": "validated" if confirmed else "needs_review",
                "notes": " ".join(notes),
            }
        )

    projects = sorted(dominion + georgia, key=lambda item: item["project_id"])
    output = {"schema_version": "1.0", "projects": projects}
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(projects)} master projects: {len(dominion)} Dominion and {len(georgia)} Georgia Power")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
