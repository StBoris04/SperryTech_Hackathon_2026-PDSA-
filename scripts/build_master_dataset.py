#!/usr/bin/env python3
"""Build the two-utility master handoff without relabeling other sponsors."""

from __future__ import annotations

import json
import re
from pathlib import Path


VALIDATED_PATH = Path("data/validated_projects.json")
CANDIDATES_PATH = Path("data/all_pdf_project_candidates.json")
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
    existing_gpc = {item["project_id"]: item for item in validated if item["utility_id"] == "georgia_power"}
    raw = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))["projects"]

    georgia = []
    for item in raw:
        if item.get("company") != "Georgia Power":
            continue
        source_id = str(item["source_project_id"])
        excel = EXCEL_GPC.get(source_id)
        project_id = excel[0] if excel else generated_id(source_id)
        if project_id in existing_gpc:
            georgia.append(existing_gpc[project_id])
            continue

        terminals = [value for value in (item.get("terminal_a"), item.get("terminal_b")) if value]
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
        notes = [f"Source project ID {source_id}; sponsor Georgia Power."]
        if item.get("need_date"):
            notes.append(f"Need Date {item['need_date']} is preserved in schedule_text and is not an in-service date.")
        notes.extend(item.get("uncertainties") or [])
        georgia.append(
            {
                "project_id": project_id,
                "utility_id": "georgia_power",
                "project_name": item["project_name"],
                "project_type": item["project_type"],
                "state": excel[2] if excel else None,
                "description": item.get("description"),
                "location_text": " - ".join(terminals) if terminals else None,
                "latitude": None,
                "longitude": None,
                "location_quality": "unknown",
                "location_method": None,
                "construction_start": item.get("construction_start"),
                "construction_end": item.get("construction_end"),
                "in_service_date": item.get("in_service_date"),
                "schedule_text": item.get("schedule_text"),
                "sources": sources,
                "review_status": "needs_review",
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
