#!/usr/bin/env python3
"""Validate the complete PDF-extraction candidate dataset."""

from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path


PATH = Path("data/all_pdf_project_candidates.json")
FIELDS = {
    "candidate_id",
    "source_project_id",
    "company",
    "project_name",
    "project_type",
    "terminal_a",
    "terminal_b",
    "description",
    "in_service_date",
    "construction_start",
    "construction_end",
    "need_date",
    "schedule_text",
    "source",
    "review_status",
    "uncertainties",
}


def main() -> int:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    projects = data.get("projects", [])
    ids: set[str] = set()

    if data.get("dataset_kind") != "pdf_extraction_candidates":
        errors.append("unexpected dataset_kind")

    for index, project in enumerate(projects, start=1):
        label = project.get("candidate_id", f"row {index}")
        if set(project) != FIELDS:
            errors.append(f"{label}: fields do not match the candidate schema")
        if label in ids:
            errors.append(f"{label}: duplicate candidate_id")
        ids.add(label)
        if not project.get("project_name") or not project.get("company"):
            errors.append(f"{label}: project_name and company are required")
        if project.get("review_status") not in {"needs_review", "validated"}:
            errors.append(f"{label}: invalid review_status")
        if project.get("project_type") not in {"transmission_line", "substation", "other", "unknown"}:
            errors.append(f"{label}: invalid project_type")
        for field in ("in_service_date", "construction_start", "construction_end", "need_date"):
            value = project.get(field)
            if value is not None:
                try:
                    dt.date.fromisoformat(value)
                except (TypeError, ValueError):
                    errors.append(f"{label}: invalid {field}: {value!r}")
        source = project.get("source", {})
        if not source.get("reference") or not isinstance(source.get("pdf_page"), int):
            errors.append(f"{label}: source reference and integer PDF page are required")

    references = Counter(project.get("source", {}).get("reference") for project in projects)
    expected = {
        "Challenge Docs/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf": 44,
        "Challenge Docs/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf": 208,
    }
    if references != expected:
        errors.append(f"unexpected source counts: {dict(references)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(projects)} PDF project candidates: 44 Dominion and 208 Georgia plan records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
