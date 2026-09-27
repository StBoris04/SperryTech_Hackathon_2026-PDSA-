# Backend verification — 2026-09-27

The approved fixes are implemented on `codex/backend-api`, starting from
`a5e5ae6`. The changes include the API contract/models,
opportunity endpoint, dependency setup, migration 002, tests, Postman handoff,
and synchronized documentation. This report records verification before the
requested Git commit; no push, PR, or deployment was part of that verification.

## Resolved inconsistencies

| Initial issue | Resolution |
| --- | --- |
| Database contained only the earlier 45-record batch | Imported the 166-record master: 121 inserted, 45 updated, 227 source references upserted |
| Existing state/source fields differed from the master | Added source-supported states and support annotations; all previous references were retained; readback exactly matches master |
| API dependencies undeclared | Root `requirements.txt` declares FastAPI 0.141.1, Uvicorn 0.54.0, and the existing database package; clean environment installation passed |
| `/opportunities` returned 404 | Implemented the agreed seven-field objects in the v1 envelope, with explicit OpenAPI models and sanitized 503 errors |
| Complete year/month windows returned unknown | Migration 002 expands bounds only inside calculations and handles leap years and inclusive endpoints |
| View rounded distance before ranking | View retains full precision; API sorts by distance, overlap/unknown/no_overlap, then canonical IDs |
| Synthetic fixtures could qualify if marked validated | View excludes projects with `synthetic-fixture` evidence; no synthetic rows were inserted |
| API handoff and status docs were stale | Updated README/context/workflows/database audit; added `docs/api.md` and a three-request Postman collection/environment |

The requesting user explicitly approved these data, dependency, endpoint, and
schema changes in this chat on 2026-09-27. The PostGIS view remains the single
source of distance and timeline calculations; the backend adds ordering and
factual reason text. No construction dates, coordinates, reviews, or matches
were fabricated.

## Verification performed

| Check | Result |
| --- | --- |
| API tests | 12 passed, including two opt-in live checks |
| Existing extraction/enrichment unit tests | 14 passed |
| Existing importer unit tests | 4 passed |
| Deployed opportunity query and API ordering | 19 of 19 checks passed |
| Master import dry-run | 166 records passed |
| Earlier source-checked batch validation | 45 records passed |
| Raw PDF candidate validation | 252 records passed |
| Clean environment install and `pip check` | Passed; no broken requirements |
| Real Uvicorn HTTP requests | Health, 166 projects, opportunities, and OpenAPI returned 200 |
| Actual failed database connection over HTTP | Both list endpoints returned the exact sanitized 503 bodies; health remained 200 |
| Postman artifacts | JSON and saved responses parsed; assertion JavaScript syntax checked |
| Whitespace checks | Passed |

The API unit tests exercise FastAPI's ASGI routing and JSON serialization.
They cover the full project shape, both utilities, null coordinates, original
date precision, evidence, review status, empty responses, distance serialization,
uncertainty reasons, database/configuration failures, and OpenAPI schemas.
The live project test compares every field against the master batch, allowing
only source-array ordering differences.

The 19 opportunity checks use the deployed view definition and the API's actual
ordering query. In-memory synthetic CTEs cover same-point distance; just below,
at, and above 25 miles; same-utility/review/location exclusion; duplicate-free
canonical pairs; exact and coarse construction windows; touching endpoints;
leap day and month-end behavior; incomplete and reversed windows; approximate
locations; synthetic evidence exclusion; and full-precision distance precedence,
timeline ties, and ID ties. No test fixture is written to the database.

The Postman desktop runner was not exercised. Equivalent real HTTP requests
were checked with Uvicorn and the standard-library HTTP client. The temporary
server was stopped after testing. No frontend exists yet, so the complete
interactive browser demo and cross-origin deployment remain unverified.

## Database result and recovery

Tiger Cloud now matches `data/master_projects.json`: 44 Dominion and 122 Georgia
Power projects. There are 24 validated Dominion records with coordinates and
142 `needs_review` records with null coordinates. The real opportunity endpoint
correctly returns `{"schema_version":"1.0","opportunities":[]}` because no
Georgia record is yet validated with coordinates. Data science must verify those
records before the system can produce real cross-utility opportunities.

Reconciliation found that the previous 45 states were null; the master adds
44 SC states and one GA state with corresponding evidence-support annotations.
There were no live-only IDs or source references requiring deletion. All other
existing project values were unchanged. Before the write, the sync checked for
unexpected changes, locked project/source writes, and saved a recovery snapshot.
Migration, deterministic checks, upserts, and exact payload readback completed
in one transaction before the database commit.

The snapshot is local and ignored by Git at
`database/backups/20260927T061448Z/`. See
[database/README.md](../database/README.md#verify-and-recover) for recovery steps.
No credentials or database backups are included in the handoff artifacts.

## Reproduce

Follow [docs/api.md](api.md) for installation, startup, endpoint examples,
Postman, and verification commands. Ordinary unit tests skip live database
checks unless `GRIDLOCK_TEST_DATABASE=1`. The separate opportunity probe opens
a read-only connection and exits nonzero if any contract check fails.
