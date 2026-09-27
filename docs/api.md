# GridLock API handoff

Backend owners: Adrian and Boris. Boris maintains the authoritative PostGIS
opportunity view. The implementation follows the v1 contract in
[context.md](../context.md), with the dataset, dependency, endpoint, and migration
changes approved by the requesting user on 2026-09-27.

## Start locally

From the repository root, with Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Set `DATABASE_URL` in the process environment or ignored `database/.env`.
An exported value takes precedence over the file. Use `sslmode=require` for
Tiger Cloud. Do not put database credentials in frontend code or Postman.
For a fresh database, follow [database/README.md](../database/README.md): apply
migrations 001 and 002 in order, then validate/import `data/master_projects.json`.
The server never imports JSON or migrates the database at startup.

Base URL: `http://127.0.0.1:8000`. Interactive schemas and requests are at `/docs`;
the machine-readable contract is `/openapi.json`. Responses include explicit
nulls and preserve source date strings. No authentication, filters, pagination,
or ingestion endpoints are configured for this local read-only MVP. Unknown
query parameters are ignored.

CORS allows browser `GET` requests only from the origins in the comma-separated
`GRIDLOCK_CORS_ORIGINS` environment variable, which defaults to the Vite dev
server (`http://localhost:5173,http://127.0.0.1:5173`). Postman and curl ignore
CORS, so a request that works there can still be blocked in a browser. Add the
deployed frontend URL to this variable once deployment is agreed. See
[frontend/README.md](../frontend/README.md) for the browser integration check.

## Endpoints

| Request | Success | Database unavailable |
| --- | --- | --- |
| `GET /health` | `200 {"status":"ok"}` | Still 200: liveness only, no database query |
| `GET /projects` | `200 {"schema_version":"1.0","projects":[...]}` | `503 {"detail":"Project data is temporarily unavailable."}` |
| `GET /opportunities` | `200 {"schema_version":"1.0","opportunities":[...]}` | `503 {"detail":"Opportunity data is temporarily unavailable."}` |

Both list endpoints return an empty array with HTTP 200 when there are no rows.
Error bodies do not expose credentials or internal connection details.

### Projects

All stored projects are returned in project-ID order, including records needing
review and projects without coordinates. Each project contains exactly the 18
fields in [context.md](../context.md). Source evidence remains an array of
`reference`, `locator`, and `supports` objects. Use `project_id` to join an
opportunity to these full records. Never place a project with null coordinates
at an invented map location.

The current database has 166 projects (44 Dominion, 122 Georgia Power), matching
`data/master_projects.json`. The saved Postman response contains one real project
from each utility as a **subset example**, not the complete API result.

### Opportunities

Each opportunity contains exactly:

| Field | Type | Meaning |
| --- | --- | --- |
| project_id_a | string | First project ID, less than project_id_b |
| project_id_b | string | Second project ID |
| distance_miles | number | Unrounded distance between representative points |
| distance_method | string | `postgis_geography` (WGS84 geography, meters / 1609.344) |
| location_uncertain | boolean | Either location is approximate; show as provisional |
| timeline_status | string | `overlap`, `unknown`, or `no_overlap` |
| reason | string | Deterministic explanation; no inferred savings or feasibility |

Eligibility requires different utilities, both validated, both with coordinates,
and distance **less than or equal to 25 miles** (40,233.6 meters). A source with
reference `synthetic-fixture` excludes its project even if marked validated.
Rank by unrounded distance ascending, then overlap/unknown/no_overlap, then both
IDs ascending. Only round distances for display. Reasons round distance to two
decimals for readability; the numeric field and sorting retain full precision.

Construction windows are inclusive. A start of `2027` means January 1 only inside
the calculation; an end of `2027-02` means February 28 only inside the calculation.
Leap years are respected. Missing or invalid bounds yield `unknown`. An in-service
milestone never supplies a missing construction bound. Original project strings
are unchanged. Point proximity is a screening signal, not minimum route separation
or proof of resource-sharing feasibility.

As of the 2026-09-27 Georgia Power location enrichment
([PR #7](https://github.com/StBoris04/SperryTech_Hackathon_2026-PDSA-/pull/7)),
there are 24 validated Dominion projects and 6 validated Georgia Power projects
(of 122), with 136 total still needing review. The response is expected to
remain:

```json
{"schema_version":"1.0","opportunities":[]}
```

because the closest validated cross-utility pair is roughly 34 miles apart (a
straight-line sanity check, not the authoritative PostGIS distance) — outside
the 25-mile boundary. Confirm against the live response rather than assuming;
more Georgia terminals need to be confirmed against OSM/HIFLD before a real
match within range is likely.

## Postman

Import [GridLock.postman_collection.json](../postman/GridLock.postman_collection.json)
and [GridLock.local.postman_environment.json](../postman/GridLock.local.postman_environment.json).
Select **GridLock local**, start the API, and run the three requests in order.
The only environment setting is `base_url`; no keys or database URL are needed.
Assertions cover health, project fields/nulls/evidence, opportunity fields,
eligibility distance, and deterministic ordering. Saved examples include both
success and sanitized 503 responses. Empty opportunity results are expected.

To manually exercise 503 responses, stop the API and launch a temporary instance
with an intentionally unreachable local database:

```bash
DATABASE_URL='postgresql://invalid:invalid@127.0.0.1:1/invalid?connect_timeout=1' \
  python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Point a duplicate Postman environment at port 8001: health returns 200; both list
requests return their documented 503 bodies. The normal collection's success
assertions will intentionally fail in this mode. Stop that instance afterward.
This overrides configuration only for the test process and changes no database.

## Automated checks

```bash
python -m pip install -e './database[dev]'
python -m unittest discover -s tests -v
python -m pytest database/tests -q
gridlock-import data/master_projects.json --dry-run
python3 scripts/validate_pdf_candidates.py
```

Unit tests require no network; they skip two opt-in live checks. With Tiger Cloud
access, run the database-to-API and analysis checks:

```bash
GRIDLOCK_TEST_DATABASE=1 python -m unittest discover -s tests -p test_backend_api.py -v
python -m scripts.check_opportunity_view
```

Both commands use read-only connections. Synthetic boundary/timeline/ranking
fixtures exist only in SQL CTEs and never enter stored projects or real rankings.
See [backend-api-validation.md](backend-api-validation.md) for actual results.
