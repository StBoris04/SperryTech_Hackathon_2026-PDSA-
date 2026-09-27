#!/usr/bin/env python3
"""Validate a GridLock project handoff batch using only the Python standard library."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path


PROJECT_FIELDS = {
    "project_id",
    "utility_id",
    "project_name",
    "project_type",
    "state",
    "description",
    "location_text",
    "latitude",
    "longitude",
    "location_quality",
    "location_method",
    "construction_start",
    "construction_end",
    "in_service_date",
    "schedule_text",
    "sources",
    "review_status",
    "notes",
}
DATE_PATTERN = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")


def validate_date(value: object, field: str, project_id: str, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        errors.append(f"{project_id}: {field} must be YYYY, YYYY-MM, YYYY-MM-DD, or null")
        return
    try:
        if len(value) == 4:
            dt.date(int(value), 1, 1)
        elif len(value) == 7:
            dt.date.fromisoformat(f"{value}-01")
        else:
            dt.date.fromisoformat(value)
    except ValueError:
        errors.append(f"{project_id}: {field} is not a valid calendar date: {value}")


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        batch = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read valid JSON from {path}: {exc}"]

    if batch.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    projects = batch.get("projects")
    if not isinstance(projects, list):
        return errors + ["projects must be an array"]

    seen_ids: set[str] = set()
    for index, project in enumerate(projects, start=1):
        if not isinstance(project, dict):
            errors.append(f"projects[{index}] must be an object")
            continue
        project_id = project.get("project_id") or f"projects[{index}]"
        missing = PROJECT_FIELDS - project.keys()
        extra = project.keys() - PROJECT_FIELDS
        if missing:
            errors.append(f"{project_id}: missing fields {sorted(missing)}")
        if extra:
            errors.append(f"{project_id}: unexpected fields {sorted(extra)}")
        if project_id in seen_ids:
            errors.append(f"{project_id}: duplicate project_id")
        seen_ids.add(project_id)

        if project.get("project_type") not in {"transmission_line", "substation", "other", "unknown"}:
            errors.append(f"{project_id}: invalid project_type")
        state = project.get("state")
        if state is not None and (not isinstance(state, str) or not re.fullmatch(r"[A-Z]{2}", state)):
            errors.append(f"{project_id}: state must be a two-letter uppercase code or null")
        if project.get("location_quality") not in {"verified", "approximate", "unknown"}:
            errors.append(f"{project_id}: invalid location_quality")
        if project.get("review_status") not in {"needs_review", "validated"}:
            errors.append(f"{project_id}: invalid review_status")

        latitude = project.get("latitude")
        longitude = project.get("longitude")
        if (latitude is None) != (longitude is None):
            errors.append(f"{project_id}: latitude and longitude must both be null or both be present")
        if latitude is not None and not (-90 <= latitude <= 90):
            errors.append(f"{project_id}: latitude is out of range")
        if longitude is not None and not (-180 <= longitude <= 180):
            errors.append(f"{project_id}: longitude is out of range")
        if latitude is None and project.get("location_quality") != "unknown":
            errors.append(f"{project_id}: missing coordinates require unknown location_quality")
        if latitude is not None and not project.get("location_method"):
            errors.append(f"{project_id}: coordinates require location_method")

        for field in ("construction_start", "construction_end", "in_service_date"):
            validate_date(project.get(field), field, project_id, errors)

        start = project.get("construction_start")
        end = project.get("construction_end")
        if start and end and len(start) == 10 and len(end) == 10 and start > end:
            errors.append(f"{project_id}: construction_start is after construction_end")

        schedule = project.get("schedule_text") or ""
        has_need = "need date" in schedule.lower()
        has_in_service_label = "in-service" in schedule.lower() or "in service" in schedule.lower()
        if has_need and not has_in_service_label and project.get("in_service_date") is not None:
            errors.append(f"{project_id}: a Need Date cannot populate in_service_date")

        sources = project.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{project_id}: sources must be a non-empty array")
        else:
            for source_index, source in enumerate(sources, start=1):
                label = f"{project_id}: sources[{source_index}]"
                if not isinstance(source, dict):
                    errors.append(f"{label} must be an object")
                    continue
                if set(source) != {"reference", "locator", "supports"}:
                    errors.append(f"{label} must contain only reference, locator, and supports")
                supports = source.get("supports")
                if not isinstance(supports, list) or not supports:
                    errors.append(f"{label}.supports must be a non-empty array")
                elif not set(supports) <= PROJECT_FIELDS:
                    errors.append(f"{label}.supports includes unknown project fields")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=Path("data/validated_projects.json"))
    args = parser.parse_args()
    errors = validate(args.path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    count = len(json.loads(args.path.read_text(encoding="utf-8"))["projects"])
    print(f"Validated {count} project records in {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
