import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from gridlock_importer.repository import import_projects
from gridlock_importer.validation import BatchValidationError, validate_batch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and import a GridLock project JSON batch."
    )
    parser.add_argument("batch", type=Path, help="Path to the versioned JSON batch")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the entire batch without connecting to Tiger Cloud",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()

    try:
        with args.batch.open(encoding="utf-8") as stream:
            payload = json.load(stream)
    except FileNotFoundError:
        print(f"Batch not found: {args.batch}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read batch: {exc}", file=sys.stderr)
        return 2

    try:
        projects = validate_batch(payload)
    except BatchValidationError as exc:
        print(f"Validation failed with {len(exc.errors)} error(s):", file=sys.stderr)
        for error in exc.errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"Validation passed: {len(projects)} project(s); no database changes.")
        return 0

    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print(
            "DATABASE_URL is not configured. Copy database/.env.example to database/.env.",
            file=sys.stderr,
        )
        return 2

    try:
        report = import_projects(database_url, projects)
    except psycopg.Error as exc:
        message = exc.diag.message_primary or exc.__class__.__name__
        print(f"Database import failed: {message}", file=sys.stderr)
        return 3

    print(
        "Import complete: "
        f"{report.inserted_projects} inserted, "
        f"{report.updated_projects} updated, "
        f"{report.imported_sources} source record(s) imported."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
