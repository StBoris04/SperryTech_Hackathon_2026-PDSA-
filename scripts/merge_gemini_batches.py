#!/usr/bin/env python3
"""Merge Gemini batch outputs without treating candidates as validated."""

import argparse
import json
from pathlib import Path


def source_page(project: dict) -> int:
    pages = {
        item.get("pdf_page")
        for item in project.get("evidence", [])
        if isinstance(item, dict) and isinstance(item.get("pdf_page"), int)
    }
    if not pages:
        raise ValueError(f"project has no evidence page: {project.get('source_project_id') or project.get('project_name')}")
    return min(pages)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    projects = {}
    source_reference = None
    models = set()
    for path in args.inputs:
        batch = json.loads(path.read_text(encoding="utf-8"))
        if source_reference and batch.get("source_reference") != source_reference:
            parser.error(f"source mismatch in {path}")
        source_reference = batch.get("source_reference")
        models.add(batch.get("model"))
        for project in batch.get("projects", []):
            key = (str(project.get("source_project_id") or project.get("project_name")), source_page(project))
            if key in projects and projects[key] != project:
                parser.error(f"conflicting duplicate {key} in {path}")
            projects[key] = project
    output = {"schema_version": "1.0", "source_reference": source_reference, "model": ",".join(sorted(x for x in models if x)), "review_status": "needs_review", "projects": sorted(projects.values(), key=lambda p: (source_page(p), str(p.get("source_project_id") or "")))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Merged {len(args.inputs)} batches into {len(projects)} candidates at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
