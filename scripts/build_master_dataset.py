#!/usr/bin/env python3
"""Build the two-utility master handoff without relabeling other sponsors."""

from __future__ import annotations

import json
import re
from pathlib import Path


VALIDATED_PATH = Path("data/validated_projects.json")
GEMINI_GEORGIA_PATH = Path("data/gemini_georgia_candidates.json")
PDF_CANDIDATES_PATH = Path("data/all_pdf_project_candidates.json")
GEORGIA_LOCATIONS_PATH = Path("data/georgia_location_confirmations.json")
OUTPUT_PATH = Path("data/master_projects.json")
EXCEL_REFERENCE = "Challenge Docs/Projects_Overlaps.xlsx"

EXCEL_GPC = {
    "20793": ("GPC_1", "projects!row 7", "GA"),
    "20277": ("GPC_2", "projects!row 8", "GA"),
    "20065": ("GPC_3", "projects!row 9", "GA"),
    "18492": ("GPC_4", "projects!row 10", "GA"),
    "11821": ("GPC_5", "projects!row 11", "GA"),
}

GPC_SPONSORS = {"GPC", "Georgia Power Company"}


def generated_id(source_project_id: str) -> str:
    token = re.sub(r"[^A-Z0-9]+", "_", source_project_id.upper()).strip("_")
    return f"GPC_{token}"


def main() -> int:
    validated = json.loads(VALIDATED_PATH.read_text(encoding="utf-8"))["projects"]
    dominion = [item for item in validated if item["utility_id"] == "dominion_sc"]
    existing_gpc = {item["project_id"]: item for item in validated if item["utility_id"] == "georgia_power"}
    gemini = json.loads(GEMINI_GEORGIA_PATH.read_text(encoding="utf-8"))["projects"]
    raw = json.loads(PDF_CANDIDATES_PATH.read_text(encoding="utf-8"))["projects"]
    descriptions = {
        str(item["source_project_id"]): item.get("description")
        for item in raw
        if item.get("source_project_id") is not None
    }
    location_data = json.loads(GEORGIA_LOCATIONS_PATH.read_text(encoding="utf-8"))["terminals"]
    locations = {
        item["terminal"]: item
        for item in location_data
        if item["status"] == "confirmed"
    }

    georgia = []
    for item in gemini:
        source_id = str(item["source_project_id"])
        if item.get("company") not in GPC_SPONSORS and source_id not in EXCEL_GPC:
            continue
        excel = EXCEL_GPC.get(source_id)
        project_id = excel[0] if excel else generated_id(source_id)
        terminals = [value for value in (item.get("terminal_a"), item.get("terminal_b")) if value]
        confirmed = [locations[name] for name in terminals if name in locations]

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

        sources = []
        if excel:
            sources.append({"reference": EXCEL_REFERENCE, "locator": excel[1], "supports": ["project_id", "state"]})
        supported = ["utility_id", "project_name", "project_type", "description", "location_text", "construction_start", "construction_end", "in_service_date", "schedule_text"]
        page = min(evidence["pdf_page"] for evidence in item["evidence"])
        printed_page = next((evidence.get("printed_page") for evidence in item["evidence"] if evidence.get("printed_page")), None)
        sources.append(
            {
                "reference": "Challenge Docs/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf",
                "locator": f"PDF page {page} (printed {printed_page})",
                "supports": supported,
            }
        )
        if confirmed:
            coordinate_supports = ["latitude", "longitude", "location_quality", "location_method"]
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
                            "supports": coordinate_supports,
                        }
                    )

        notes = [f"Source project ID {source_id}; sponsor Georgia Power."]
        if item.get("need_date"):
            notes.append(f"Need Date {item['need_date']} is preserved in schedule_text and is not an in-service date.")
        missing_terminals = [name for name in terminals if name not in locations]
        if missing_terminals:
            notes.append(f"Unconfirmed terminals: {', '.join(missing_terminals)}.")
        if len(confirmed) == 1:
            notes.append("Representative point is one endpoint, not the route midpoint.")
        if not confirmed:
            notes.append("No terminal coordinates passed OSM/HIFLD confirmation; coordinates remain null.")
        notes.extend(item.get("uncertainties") or [])
        georgia.append(
            {
                "project_id": project_id,
                "utility_id": "georgia_power",
                "project_name": item["project_name"],
                "project_type": item["project_type"],
                "state": excel[2] if excel else None,
                "description": descriptions.get(source_id),
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

    # Preserve reviewed GPC records from pages not yet present in the Gemini batch.
    generated_ids = {item["project_id"] for item in georgia}
    for project_id, project in existing_gpc.items():
        if project_id not in generated_ids:
            georgia.append(project)

    projects = sorted(dominion + georgia, key=lambda item: item["project_id"])
    output = {"schema_version": "1.0", "projects": projects}
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    located = sum(item["latitude"] is not None for item in georgia)
    validated_count = sum(item["review_status"] == "validated" for item in georgia)
    print(
        f"Wrote {len(projects)} master projects: {len(dominion)} Dominion and "
        f"{len(georgia)} Georgia Power ({located} located, {validated_count} validated)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
