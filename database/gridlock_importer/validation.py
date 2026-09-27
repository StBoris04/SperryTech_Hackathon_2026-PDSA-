import calendar
import re
from datetime import date
from typing import Any


SCHEMA_VERSION = "1.0"
UTILITY_IDS = {"dominion_sc", "georgia_power"}
PROJECT_TYPES = {"transmission_line", "substation", "other", "unknown"}
LOCATION_QUALITIES = {"verified", "approximate", "unknown"}
REVIEW_STATUSES = {"needs_review", "validated"}
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
SOURCE_FIELDS = {"reference", "locator", "supports"}
PARTIAL_DATE_PATTERN = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")
STATE_PATTERN = re.compile(r"^[A-Z]{2}$")


class BatchValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_nullable_string(
    project: dict[str, Any], field: str, path: str, errors: list[str]
) -> None:
    value = project[field]
    if value is not None and not isinstance(value, str):
        errors.append(f"{path}.{field}: must be a string or null")


def _partial_date_bounds(value: str) -> tuple[date, date]:
    if not PARTIAL_DATE_PATTERN.fullmatch(value):
        raise ValueError("must use YYYY, YYYY-MM, or YYYY-MM-DD")

    if len(value) == 4:
        year = int(value)
        return date(year, 1, 1), date(year, 12, 31)

    if len(value) == 7:
        year, month = (int(part) for part in value.split("-"))
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    parsed = date.fromisoformat(value)
    return parsed, parsed


def _validate_project(
    project: Any, index: int, errors: list[str]
) -> dict[str, Any] | None:
    path = f"projects[{index}]"
    if not isinstance(project, dict):
        errors.append(f"{path}: must be an object")
        return None

    missing = sorted(PROJECT_FIELDS - project.keys())
    unexpected = sorted(project.keys() - PROJECT_FIELDS)
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
    if unexpected:
        errors.append(f"{path}: unexpected fields: {', '.join(unexpected)}")
    if missing or unexpected:
        return None

    project_id = project["project_id"]
    if not isinstance(project_id, str) or not project_id.strip():
        errors.append(f"{path}.project_id: must be a non-empty string")

    utility_id = project["utility_id"]
    if not isinstance(utility_id, str) or utility_id not in UTILITY_IDS:
        errors.append(f"{path}.utility_id: unsupported utility ID")

    project_name = project["project_name"]
    if not isinstance(project_name, str) or not project_name.strip():
        errors.append(f"{path}.project_name: must be a non-empty string")

    if (
        not isinstance(project["project_type"], str)
        or project["project_type"] not in PROJECT_TYPES
    ):
        errors.append(f"{path}.project_type: unsupported project type")

    state = project["state"]
    if state is not None and (
        not isinstance(state, str) or not STATE_PATTERN.fullmatch(state)
    ):
        errors.append(f"{path}.state: must be two uppercase letters or null")

    for field in (
        "description",
        "location_text",
        "location_method",
        "schedule_text",
        "notes",
    ):
        _validate_nullable_string(project, field, path, errors)

    latitude = project["latitude"]
    longitude = project["longitude"]
    if latitude is not None and (not _is_number(latitude) or not -90 <= latitude <= 90):
        errors.append(f"{path}.latitude: must be between -90 and 90 or null")
    if longitude is not None and (
        not _is_number(longitude) or not -180 <= longitude <= 180
    ):
        errors.append(f"{path}.longitude: must be between -180 and 180 or null")
    if (latitude is None) != (longitude is None):
        errors.append(f"{path}: latitude and longitude must both be set or both be null")

    location_quality = project["location_quality"]
    if (
        not isinstance(location_quality, str)
        or location_quality not in LOCATION_QUALITIES
    ):
        errors.append(f"{path}.location_quality: unsupported value")
    elif latitude is None:
        if location_quality != "unknown":
            errors.append(f"{path}.location_quality: must be unknown without coordinates")
        if project["location_method"] is not None:
            errors.append(f"{path}.location_method: must be null without coordinates")
    elif location_quality == "unknown":
        errors.append(f"{path}.location_quality: must assess coordinates as approximate or verified")
    elif not isinstance(project["location_method"], str) or not project[
        "location_method"
    ].strip():
        errors.append(f"{path}.location_method: required when coordinates are present")

    date_bounds: dict[str, tuple[date, date]] = {}
    for field in ("construction_start", "construction_end", "in_service_date"):
        value = project[field]
        if value is None:
            continue
        if not isinstance(value, str):
            errors.append(f"{path}.{field}: must be a partial date string or null")
            continue
        try:
            date_bounds[field] = _partial_date_bounds(value)
        except (ValueError, OverflowError) as exc:
            errors.append(f"{path}.{field}: {exc}")

    if "construction_start" in date_bounds and "construction_end" in date_bounds:
        start_lower = date_bounds["construction_start"][0]
        end_upper = date_bounds["construction_end"][1]
        if start_lower > end_upper:
            errors.append(f"{path}: construction_start is after construction_end")

    if (
        not isinstance(project["review_status"], str)
        or project["review_status"] not in REVIEW_STATUSES
    ):
        errors.append(f"{path}.review_status: unsupported value")

    sources = project["sources"]
    if not isinstance(sources, list) or not sources:
        errors.append(f"{path}.sources: must contain at least one source")
    else:
        for source_index, source in enumerate(sources):
            source_path = f"{path}.sources[{source_index}]"
            if not isinstance(source, dict):
                errors.append(f"{source_path}: must be an object")
                continue
            source_missing = sorted(SOURCE_FIELDS - source.keys())
            source_unexpected = sorted(source.keys() - SOURCE_FIELDS)
            if source_missing:
                errors.append(
                    f"{source_path}: missing fields: {', '.join(source_missing)}"
                )
            if source_unexpected:
                errors.append(
                    f"{source_path}: unexpected fields: {', '.join(source_unexpected)}"
                )
            if source_missing or source_unexpected:
                continue
            for field in ("reference", "locator"):
                if not isinstance(source[field], str) or not source[field].strip():
                    errors.append(f"{source_path}.{field}: must be a non-empty string")
            supports = source["supports"]
            if not isinstance(supports, list) or not supports:
                errors.append(f"{source_path}.supports: must be a non-empty array")
            elif any(not isinstance(item, str) or item not in PROJECT_FIELDS for item in supports):
                errors.append(f"{source_path}.supports: contains an unknown project field")

    return project


def validate_batch(payload: Any) -> list[dict[str, Any]]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        raise BatchValidationError(["batch: must be a JSON object"])

    expected_batch_fields = {"schema_version", "projects"}
    missing = sorted(expected_batch_fields - payload.keys())
    unexpected = sorted(payload.keys() - expected_batch_fields)
    if missing:
        errors.append(f"batch: missing fields: {', '.join(missing)}")
    if unexpected:
        errors.append(f"batch: unexpected fields: {', '.join(unexpected)}")
    if errors:
        raise BatchValidationError(errors)

    if payload["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version: must be {SCHEMA_VERSION}")

    projects_value = payload["projects"]
    if not isinstance(projects_value, list) or not projects_value:
        errors.append("projects: must be a non-empty array")
        projects: list[dict[str, Any]] = []
    else:
        projects = []
        for index, project in enumerate(projects_value):
            validated = _validate_project(project, index, errors)
            if validated is not None:
                projects.append(validated)

    project_ids = [
        project.get("project_id")
        for project in projects
        if isinstance(project.get("project_id"), str)
    ]
    duplicates = sorted(
        project_id
        for project_id in set(project_ids)
        if project_id is not None and project_ids.count(project_id) > 1
    )
    if duplicates:
        errors.append(f"projects: duplicate project IDs: {', '.join(duplicates)}")

    if errors:
        raise BatchValidationError(errors)
    return projects
