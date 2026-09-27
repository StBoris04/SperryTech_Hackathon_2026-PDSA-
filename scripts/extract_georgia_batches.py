#!/usr/bin/env python3
"""Extract every Georgia project page with Gemini in resumable batches."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


PDF = Path("Challenge Docs/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf")
FIRST_PAGE = 214
LAST_PAGE = 425


def page_ranges(size: int, first_page: int = FIRST_PAGE) -> list[tuple[int, int]]:
    return [(start, min(start + size - 1, LAST_PAGE)) for start in range(first_page, LAST_PAGE + 1, size)]


def extract_range(start: int, end: int, directory: Path, dry_run: bool, failed_pages: list[int]) -> list[Path]:
    output = directory / f"georgia_{start}_{end}.json"
    if output.exists() and not dry_run:
        print(f"Skipping completed batch {start}-{end}")
        return [output]
    command = [
        sys.executable,
        "gemini_extraction/extract_projects.py",
        str(PDF),
        "--pages",
        f"{start}-{end}",
        "--allow-sensitive-source",
        "--timeout",
        "600",
        "--retries",
        "6",
        "--output",
        str(output),
    ]
    if dry_run:
        command.append("--dry-run")
    print(f"Extracting pages {start}-{end}...")
    result = subprocess.run(command)
    if result.returncode == 0:
        return [output]
    page_count = end - start + 1
    if dry_run:
        raise RuntimeError(f"Gemini failed for pages {start}-{end}")
    if page_count <= 1:
        failed_pages.append(start)
        print(f"Page {start} remains pending; continuing with later pages.", file=sys.stderr)
        return []
    midpoint = (start + end) // 2
    print(f"Batch {start}-{end} failed; retrying as {start}-{midpoint} and {midpoint + 1}-{end}.", file=sys.stderr)
    return extract_range(start, midpoint, directory, False, failed_pages) + extract_range(midpoint + 1, end, directory, False, failed_pages)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--start-page", type=int, default=FIRST_PAGE)
    parser.add_argument("--directory", type=Path, default=Path("data/georgia_batches"))
    parser.add_argument("--output", type=Path, default=Path("data/gemini_georgia_candidates.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 40:
        parser.error("--batch-size must be between 1 and 40")
    if args.start_page < FIRST_PAGE or args.start_page > LAST_PAGE:
        parser.error(f"--start-page must be between {FIRST_PAGE} and {LAST_PAGE}")
    if not PDF.is_file():
        parser.error(f"missing PDF: {PDF}")
    if not args.dry_run and not os.environ.get("GEMINI_API_KEY"):
        parser.error("set GEMINI_API_KEY in this terminal first")

    args.directory.mkdir(parents=True, exist_ok=True)
    batches: list[Path] = []
    failed_pages: list[int] = []
    for start, end in page_ranges(args.batch_size, args.start_page):
        batches.extend(extract_range(start, end, args.directory, args.dry_run, failed_pages))

    if args.dry_run:
        print(f"Dry run OK: {len(batches)} batches cover pages {args.start_page}-{LAST_PAGE}")
        return 0
    all_batches = sorted(args.directory.glob("georgia_*.json"))
    subprocess.run([sys.executable, "scripts/merge_gemini_batches.py", *map(str, all_batches), "--output", str(args.output)], check=True)
    failed_path = args.directory / "failed_pages.json"
    failed_path.write_text(json.dumps({"failed_pages": failed_pages}, indent=2) + "\n", encoding="utf-8")
    if failed_pages:
        print(f"Pending Gemini pages: {failed_pages}. See {failed_path}.", file=sys.stderr)
    print(f"Georgia extraction complete: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
