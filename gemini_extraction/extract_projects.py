#!/usr/bin/env python3
"""Extract source-backed utility projects from a PDF with the Gemini REST API."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = Path(__file__).with_name("project_schema.json")
DEFAULT_MODEL = "gemini-3.8-flash"
API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
GEORGIA_SOURCE_NAME = "2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf"


def ssl_context() -> ssl.SSLContext:
    """Use Python's CA bundle, certifi when present, or the macOS system bundle."""
    candidates: list[str] = []
    default_paths = ssl.get_default_verify_paths()
    if default_paths.cafile:
        candidates.append(default_paths.cafile)
    try:
        import certifi  # type: ignore[import-not-found]

        candidates.append(certifi.where())
    except ImportError:
        pass
    candidates.extend(("/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


def parse_pages(value: str | None) -> list[int]:
    if not value:
        return []
    pages: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = int(start_text), int(end_text)
            if start < 1 or end < start:
                raise ValueError(f"invalid page range: {part}")
            pages.update(range(start, end + 1))
        else:
            page = int(part)
            if page < 1:
                raise ValueError(f"invalid page: {part}")
            pages.add(page)
    return sorted(pages)


def build_prompt(source_reference: str, pages: list[int]) -> str:
    page_scope = (
        f"Extract projects only from physical PDF pages: {', '.join(map(str, pages))}."
        if pages
        else "Extract every project in the PDF."
    )
    return f"""You extract electric transmission project facts from a supplied PDF.
Source reference: {source_reference}
{page_scope}

Return only JSON matching the supplied schema.

Rules:
- Use one-based physical PDF page numbers in evidence.pdf_page. Keep printed page labels separately.
- Preserve the exact project name, capitalization, voltage spacing, punctuation, and source ID.
- Set in_service_date only when explicitly labeled In-Service or Planned In-Service.
- Keep Need Date in need_date. Never copy a Need Date into in_service_date.
- Set construction_start or construction_end only from an explicit Start Date, Construction Start, End Date, or Construction End label for that project.
- Status, budget years, and Need Date do not establish a construction window.
- Extract terminals only when the title or description supports them. Explain conflicting title endpoints and described work segments in uncertainties.
- Do not invent coordinates, dates, terminals, company names, or redacted content.
- Every populated factual field must be supported by at least one short evidence item.
- Mention confidentiality, CEII, or redistribution warnings in uncertainties.
"""


def build_request(pdf_path: Path, source_reference: str, pages: list[int], schema: dict) -> dict:
    encoded_pdf = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": "application/pdf", "data": encoded_pdf}},
                    {"text": build_prompt(source_reference, pages)},
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
            "temperature": 0,
        },
    }


def normalize_date(value: object) -> object:
    if not isinstance(value, str):
        return value
    for source_format in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return dt.datetime.strptime(value, source_format).date().isoformat()
        except ValueError:
            pass
    return value


def normalize_result(result: dict) -> dict:
    for project in result.get("projects", []):
        for field in ("in_service_date", "construction_start", "construction_end", "need_date"):
            original = project.get(field)
            normalized = normalize_date(original)
            if isinstance(normalized, str) and not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", normalized):
                if not project.get("schedule_text"):
                    project["schedule_text"] = original
                message = f"{field} contains multiple or unsupported source dates; review schedule_text."
                uncertainties = project.setdefault("uncertainties", [])
                if message not in uncertainties:
                    uncertainties.append(message)
                normalized = None
            project[field] = normalized
    return result


def call_gemini(payload: dict, model: str, api_key: str, timeout: int, retries: int = 3) -> dict:
    model_path = urllib.parse.quote(model, safe="")
    url = f"{API_ROOT}/models/{model_path}:generateContent"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    transient_codes = {429, 500, 502, 503, 504}
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_context()) as response:
                body = json.load(response)
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code not in transient_codes or attempt == retries:
                raise RuntimeError(f"Gemini API returned HTTP {exc.code}: {detail[:1000]}") from exc
            delay = min(2**attempt, 8)
            print(
                f"Gemini returned HTTP {exc.code}; retrying in {delay}s "
                f"({attempt + 1}/{retries})...",
                file=sys.stderr,
            )
            time.sleep(delay)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Gemini API request failed: {exc.reason}") from exc

    try:
        text = "".join(
            part.get("text", "")
            for part in body["candidates"][0]["content"]["parts"]
        )
        return json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini returned no usable structured JSON") from exc


def validate_result(result: dict, requested_pages: list[int]) -> list[str]:
    errors: list[str] = []
    projects = result.get("projects")
    if not isinstance(projects, list):
        return ["projects must be an array"]
    requested = set(requested_pages)
    for index, project in enumerate(projects, start=1):
        label = project.get("source_project_id") or project.get("project_name") or f"project {index}"
        evidence = project.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{label}: evidence must be non-empty")
            continue
        for item in evidence:
            page = item.get("pdf_page") if isinstance(item, dict) else None
            if not isinstance(page, int) or page < 1:
                errors.append(f"{label}: invalid evidence page")
            elif requested and page not in requested:
                errors.append(f"{label}: evidence page {page} was outside the requested pages")
        schedule = (project.get("schedule_text") or "").lower()
        if "need date" in schedule and "in-service" not in schedule and "in service" not in schedule:
            if project.get("in_service_date") is not None:
                errors.append(f"{label}: Need Date cannot populate in_service_date")
        for field in ("in_service_date", "construction_start", "construction_end", "need_date"):
            value = project.get(field)
            if value is not None and not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", value):
                errors.append(f"{label}: {field} must use YYYY, YYYY-MM, YYYY-MM-DD, or null")
    return errors


def relative_source(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--pages", help="Physical PDF pages, for example 31 or 189,410")
    parser.add_argument("--output", type=Path, default=Path("data/gemini_candidates.json"))
    parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without sending the PDF")
    parser.add_argument(
        "--allow-sensitive-source",
        action="store_true",
        help="Acknowledge that the source carries confidentiality or CEII warnings",
    )
    args = parser.parse_args()

    if not args.pdf.is_file() or args.pdf.suffix.lower() != ".pdf":
        parser.error("pdf must point to an existing PDF file")
    try:
        pages = parse_pages(args.pages)
    except ValueError as exc:
        parser.error(str(exc))

    if args.pdf.name == GEORGIA_SOURCE_NAME and not args.allow_sensitive_source:
        parser.error(
            "the Georgia source carries a CEII/confidentiality warning; obtain team approval "
            "before rerunning with --allow-sensitive-source"
        )

    schema = json.loads(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
    source_reference = relative_source(args.pdf)
    if args.dry_run:
        scope = pages or "all pages"
        print(f"Dry run OK: {source_reference}; pages={scope}; model={args.model}")
        return 0

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        parser.error("set GEMINI_API_KEY in the environment; never commit the key")

    payload = build_request(args.pdf, source_reference, pages, schema)
    result = normalize_result(call_gemini(payload, args.model, api_key, args.timeout, args.retries))
    errors = validate_result(result, pages)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    output = {
        "schema_version": "1.0",
        "source_reference": source_reference,
        "model": args.model,
        "review_status": "needs_review",
        "projects": result["projects"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(output['projects'])} Gemini candidates to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
