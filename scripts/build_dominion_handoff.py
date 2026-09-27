#!/usr/bin/env python3
"""Build the shared v1 project handoff from reviewed Dominion extraction artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path


GEMINI_PATH = Path("data/gemini_dominion_candidates.json")
PDF_CANDIDATES_PATH = Path("data/all_pdf_project_candidates.json")
LOCATIONS_PATH = Path("data/dominion_location_confirmations.json")
OUTPUT_PATH = Path("data/validated_projects.json")
PDF_REFERENCE = "Challenge Docs/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf"
EXCEL_REFERENCE = "Challenge Docs/Projects_Overlaps.xlsx"

EXCEL_IDS = {
    "6809 E": ("DESC_1", "projects!row 2"),
    "6810 A": ("DESC_2", "projects!row 3"),
    "06367 D - G": ("DESC_3", "projects!row 4"),
    "6807 B": ("DESC_4", "projects!row 5"),
    "6808 S": ("DESC_5", "projects!row 6"),
}


def generated_id(source_project_id: str) -> str:
    token = re.sub(r"[^A-Z0-9]+", "_", source_project_id.upper()).strip("_")
    return f"DESC_{token}"


def main() -> int:
    gemini = json.loads(GEMINI_PATH.read_text(encoding="utf-8"))["projects"]
    raw = json.loads(PDF_CANDIDATES_PATH.read_text(encoding="utf-8"))["projects"]
    descriptions = {
        item["source_project_id"]: item.get("description")
        for item in raw
        if item.get("company") == "Dominion Energy South Carolina"
    }
    location_data = json.loads(LOCATIONS_PATH.read_text(encoding="utf-8"))["terminals"]
    locations = {
        item["terminal"]: item
        for item in location_data
        if item["status"] == "confirmed"
    }

    existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))["projects"]
    non_dominion = [item for item in existing if item.get("utility_id") != "dominion_sc"]
    projects = []
    for item in gemini:
        source_id = item["source_project_id"]
        excel = EXCEL_IDS.get(source_id)
        project_id = excel[0] if excel else generated_id(source_id)
        terminal_names = [name for name in (item.get("terminal_a"), item.get("terminal_b")) if name]
        confirmed = [locations[name] for name in terminal_names if name in locations]

        latitude = longitude = None
        location_quality = "unknown"
        location_method = None
        if confirmed:
            latitude = sum(location["recommended_latitude"] for location in confirmed) / len(confirmed)
            longitude = sum(location["recommended_longitude"] for location in confirmed) / len(confirmed)
            location_quality = "approximate"
            location_method = (
                "Midpoint of two terminal coordinates independently corroborated by OSM and HIFLD"
                if len(confirmed) == 2
                else f"Representative point uses confirmed terminal {confirmed[0]['terminal']}; other terminal unavailable"
            )

        page = min(evidence["pdf_page"] for evidence in item["evidence"])
        sources = []
        if excel:
            sources.append({"reference": EXCEL_REFERENCE, "locator": excel[1], "supports": ["project_id", "state"]})
        sources.append(
            {
                "reference": PDF_REFERENCE,
                "locator": f"PDF page {page} (printed Project {page} of 44)",
                "supports": [
                    "utility_id",
                    "state",
                    "project_name",
                    "project_type",
                    "description",
                    "location_text",
                    "in_service_date",
                    "schedule_text",
                ],
            }
        )
        if confirmed:
            supports = ["latitude", "longitude", "location_quality", "location_method"]
            seen_references = set()
            for location in confirmed:
                for reference in location["sources"]:
                    if reference in seen_references:
                        continue
                    seen_references.add(reference)
                    sources.append(
                        {
                            "reference": reference,
                            "locator": f"Terminal: {location['terminal']}",
                            "supports": supports,
                        }
                    )

        missing_terminals = [name for name in terminal_names if name not in locations]
        notes = [f"Source Project ID {source_id}."]
        if missing_terminals:
            notes.append(f"Unconfirmed terminals: {', '.join(missing_terminals)}.")
        if len(confirmed) == 1:
            notes.append("Representative point is one endpoint, not the route midpoint.")
        if not confirmed:
            notes.append("No terminal coordinates passed OSM/HIFLD confirmation; coordinates remain null.")
        if item.get("uncertainties"):
            notes.extend(item["uncertainties"])

        projects.append(
            {
                "project_id": project_id,
                "utility_id": "dominion_sc",
                "project_name": item["project_name"],
                "project_type": item["project_type"],
                "state": "SC",
                "description": descriptions.get(source_id),
                "location_text": " - ".join(terminal_names) if terminal_names else None,
                "latitude": round(latitude, 7) if latitude is not None else None,
                "longitude": round(longitude, 7) if longitude is not None else None,
                "location_quality": location_quality,
                "location_method": location_method,
                "construction_start": item["construction_start"],
                "construction_end": item["construction_end"],
                "in_service_date": item["in_service_date"],
                "schedule_text": item.get("schedule_text"),
                "sources": sources,
                "review_status": "validated" if confirmed else "needs_review",
                "notes": " ".join(notes),
            }
        )

    projects.sort(key=lambda project: project["project_id"])
    output = {"schema_version": "1.0", "projects": projects + non_dominion}
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    validated = sum(project["review_status"] == "validated" for project in projects)
    located = sum(project["latitude"] is not None for project in projects)
    print(f"Wrote {len(projects)} Dominion projects: {located} located, {validated} validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
