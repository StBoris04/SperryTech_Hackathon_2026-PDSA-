# GridLock project context

## Status and purpose

Initial team draft for a four-person hackathon with approximately 12 hours total.
The repository contains the source documents, an XLSX workbook, and a Tiger Cloud
PostgreSQL/PostGIS schema with a JSON importer. The backend implements
`GET /health`, `GET /projects`, and `GET /opportunities`; the application UI
remains to be built. See [the backend validation report](docs/backend-api-validation.md)
for verified behavior and remaining gaps.

GridLock helps electric utilities identify potentially useful coordination between
planned transmission projects: shared crews, equipment, rights-of-way, or other
infrastructure. A flagged pair is a candidate for investigation, not proof that
resource sharing is feasible.

## Required outcome

The local `Challenge Docs/ShellHacks_Challenge_Gridlock.pdf` is the source of challenge requirements:

- Ingest public future-construction data for at least two electric utilities.
- Show both utilities' projects in an interactive UI and highlight overlaps.
- Produce a ranked list of coordination opportunities.
- Use geographic proximity within 25 miles as the primary signal and overlapping
  construction windows as a strong secondary signal.
- Expect most projects not to overlap. Do not manufacture matches.
- Bonus: a rough cost or impact estimate for at least one opportunity.
- Use only public sources; confidential/CEII information is out of scope.

Initial boundary convention for implementation: distance <= 25 miles qualifies;
include a boundary check and document this convention in the UI/methodology.

## Selected tracks and stack decisions

Selected tracks: **Sperry Tech + Gemini API + Tiger Data**. Official Gemini and
Tiger Data prize submission requirements still need checking before submission.

| Layer | Team choice | Decision status |
| --- | --- | --- |
| Frontend | React + Tailwind CSS | Selected; implementation pending |
| Map | Leaflet or Mapbox GL JS | Selection pending |
| Backend | Python + FastAPI | Health, project, and opportunity endpoints implemented |
| Storage | Tiger Data / PostgreSQL | Tiger Cloud service and initial schema verified |
| AI | Gemini API for structured extraction; optional explanations | Selected track; integration pending |
| Geography | PostGIS | Verified in Tiger Cloud |
| Python geography | GeoPy, Shapely, GeoPandas as needed | Optional; choose only if a concrete task needs them |
| API testing | Postman | Selected |
| Version control | GitHub | Selected |
| Deployment | Vercel frontend; Render or Railway backend | Undecided; choose a fast viable path |

Intended flow: public PDF/XLSX -> extraction and validation -> shared JSON records
-> Tiger Data -> overlap analysis and API -> interactive map and ranked list.
The PostGIS `coordination_opportunities` view is the authoritative overlap
implementation, maintained by Boris in data engineering. The backend consumes it
and applies the documented ordering and factual reason text; it does not compute
a second set of distances or timeline classifications.

## Available source files

- `Challenge Docs/ShellHacks_Challenge_Gridlock.pdf`: challenge requirements.
- `Challenge Docs/Finding_Real_Locations_Guide.pdf`: location research guide; review before enrichment.
- `Challenge Docs/Projects_Overlaps.xlsx`: supplied workbook; audit and limitations are in `docs/data-audit.md`.
- `Challenge Docs/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf`.
- `Challenge Docs/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf`.

The selected utilities are Dominion Energy South Carolina and Georgia Power.
Reviewed Dominion records include OSM/HIFLD location evidence; verify references
per record. Public project pages and SCRTP remain potential enrichment sources.
Preserve original files.

## Shared project handoff contract: v1

Selected contract: keep `construction_start`, `construction_end`, and
`in_service_date` as separate fields. Missing construction dates remain null;
an in-service milestone does not establish a construction window. Preserve the
source's date precision. The v1 project payload below is the selected handoff
contract for extraction and loading.

The database schema and JSON importer implement this project handoff contract.
Further changes follow the approval rule in AGENTS.md. Use a UTF-8
JSON object containing `schema_version: "1.0"` and a `projects` array. All fields
below are present; use JSON null for unavailable scalar values, never empty strings
or placeholder coordinates. Each array member represents one project.

| Field | Type | Meaning |
| --- | --- | --- |
| project_id | string | Stable identifier assigned at extraction; reused on reimport |
| utility_id | string | Controlled ID: dominion_sc or georgia_power initially |
| project_name | string | Source-backed project name |
| project_type | string | transmission_line, substation, other, or unknown |
| state | string or null | Two-letter uppercase state code when source-backed |
| description | string or null | Source-backed summary |
| location_text | string or null | Location as described by the source |
| latitude | number or null | WGS84 latitude, -90 to 90 |
| longitude | number or null | WGS84 longitude, -180 to 180 |
| location_quality | string | verified, approximate, or unknown |
| location_method | string or null | How the representative point was found |
| construction_start | string or null | YYYY, YYYY-MM, or YYYY-MM-DD at source precision |
| construction_end | string or null | Same supported formats; actual construction window only |
| in_service_date | string or null | Separate milestone, same supported date formats |
| schedule_text | string or null | Original wording explaining dates or uncertainty |
| sources | array of objects | At least one evidence reference, format below |
| review_status | string | needs_review or validated |
| notes | string or null | Uncertainty or interpretation relevant to downstream users |

Each source object has `reference` (repository-relative file path or public URL),
`locator` (PDF page, or XLSX sheet and row, or webpage section), and `supports`
(array of field names supported by that reference). Use 1-based PDF page numbers;
identify printed page numbers separately if they differ. Add enrichment references
for coordinates rather than implying that a planning PDF supplied them.

Illustrative fixture only; this is not a real utility project:

```json
{
  "schema_version": "1.0",
  "projects": [
    {
      "project_id": "fixture-dominion-001",
      "utility_id": "dominion_sc",
      "project_name": "Illustrative project",
      "project_type": "substation",
      "state": null,
      "description": null,
      "location_text": null,
      "latitude": null,
      "longitude": null,
      "location_quality": "unknown",
      "location_method": null,
      "construction_start": null,
      "construction_end": null,
      "in_service_date": null,
      "schedule_text": null,
      "sources": [
        {
          "reference": "synthetic-fixture",
          "locator": "example only",
          "supports": ["project_name", "utility_id", "project_type"]
        }
      ],
      "review_status": "needs_review",
      "notes": "Synthetic contract example; exclude from real rankings."
    }
  ]
}
```

Validation rules:

- Reject duplicate IDs in a batch, invalid types, invalid dates, reversed windows,
  out-of-range coordinates, or a latitude/longitude pair with only one value.
- Unknown location requires both coordinates null. A coordinate pair requires a
  location method, quality assessment, and source evidence.
- Do not infer a construction window from an in-service date. Do not convert a
  year-only date into an apparently exact date in the shared payload.
- Reimports reuse project IDs. Resolve potential duplicates before insertion;
  names alone are not globally unique identifiers.
- Only validated real records enter the main ranking. Approximate locations may
  produce provisional opportunities with visible uncertainty. Records lacking
  coordinates remain in the project list but cannot enter distance calculations.
- This v1 uses representative points. Distances between these points do not
  establish the minimum separation between full transmission routes.

## Analysis and API handoff: selected baseline

For every candidate pair, preserve the two project IDs, `distance_miles`,
`distance_method`, `location_uncertain`, `timeline_status`, and `reason`.
Use canonical project-ID order so that A/B and B/A are not duplicated.
Timeline status is `overlap`, `no_overlap`, or `unknown`.

For two complete construction windows, compare inclusive intervals. Expand coarse
start dates to the first day of the stated period and coarse end dates to the last
day only inside the calculation. Report the result as based on the source's date
precision. If either window is incomplete, report unknown rather than inventing
missing bounds.

Initial ranking rule: filter to cross-utility pairs within 25 miles; sort by
distance ascending, then timeline status (overlap, unknown, no_overlap), then
project IDs for stable ties. This deliberately simple baseline keeps geography
primary. Agree on any richer scoring formula before implementation; do not invent
an unexplained opportunity score.

Selected initial endpoints for backend/frontend implementation:

- `GET /health`: service health without secrets.
- `GET /projects`: `{ "schema_version": "1.0", "projects": [...] }`.
- `GET /opportunities`: `{ "schema_version": "1.0", "opportunities": [...] }`.

The requesting user approved implementation of these backend fixes on 2026-09-27.
The opportunity object has exactly these fields:

| Field | Type | Meaning |
| --- | --- | --- |
| project_id_a, project_id_b | string | Canonical ascending IDs; join to `/projects` for project details |
| distance_miles | number | Unrounded PostGIS geography distance in miles; round only for display |
| distance_method | string | `postgis_geography` |
| location_uncertain | boolean | True when either representative point is approximate |
| timeline_status | string | `overlap`, `unknown`, or `no_overlap` |
| reason | string | Deterministic explanation of distance, timing, uncertainty, and point limitations |

No filters or pagination are implemented for this MVP; all eligible records are
returned. Unknown query parameters are ignored, not interpreted as filters.
`GET /health` is a liveness check returning `200 {"status":"ok"}`; it does not
check database readiness. Database/configuration failures return HTTP 503 with
`{"detail":"Project data is temporarily unavailable."}` or
`{"detail":"Opportunity data is temporarily unavailable."}`, respectively.
Empty results return HTTP 200 with the normal versioned envelope and an empty
array. See [docs/api.md](docs/api.md) and the [Postman collection](postman/GridLock.postman_collection.json).
No ingestion/admin endpoint is required for the MVP.

## Dataset roles and synchronization

`data/master_projects.json` is the current database import batch: 166 projects
(44 Dominion, 122 Georgia Power). It supersedes the 45-record
`data/validated_projects.json` batch for loading; that older filename does not
mean every record is validated. The raw `all_pdf_project_candidates.json`
contains 252 extraction candidates, including 86 from other utilities outside
this two-utility contract. Those records must not be relabeled as Georgia Power.

Tiger Cloud was synchronized to the master batch on 2026-09-27, then
re-synchronized the same day after Georgia Power location enrichment
([PR #7](https://github.com/StBoris04/SperryTech_Hackathon_2026-PDSA-/pull/7)):
24 validated Dominion records, 6 validated Georgia Power records (of 122;
OSM/HIFLD confirmed 17 of 205 unique terminal names), and 136 records needing
review. The latter retain null coordinates. `/projects` includes both groups;
`/opportunities` excludes unvalidated records and records without coordinates.
Known synthetic fixtures must use `sources[].reference = "synthetic-fixture"`;
the view excludes them even if incorrectly marked validated. No synthetic
fixtures are loaded in Tiger Cloud.

The real opportunity response is expected to still be empty: the closest
validated Dominion-Georgia pair sits around 34 miles apart (a straight-line
sanity check, not the authoritative PostGIS distance), outside the 25-mile
boundary. Confirm against the live `/opportunities` response rather than
assuming either way. A Git checkout does not import JSON into the database.

## Suggested 12-hour plan

| Elapsed time | Target |
| --- | --- |
| 0-1 hours | Accept the shared contract, assign owners, choose stack options, check access |
| 1-3 hours | Load a few validated records from both utilities and display them through the API |
| 3-7 hours | Expand data, calculate candidate pairs, connect map and ranking |
| 7-10 hours | Validate location/timeline handling, integrate Gemini, prepare deployment |
| 10-12 hours | Freeze scope, rehearse demo, fix blockers, prepare submission |

Move Gemini integration earlier if it is required for the initial extraction path.
If time runs short, reduce dataset breadth and optional polish first. Preserve a
working demo and meaningful use of the selected sponsor technologies.

## Next team decisions

1. Validate source evidence and locations for Georgia Power records before ranking.
2. Select Leaflet or Mapbox GL JS for the map and connect the documented API.
3. Choose the deployment destination and agree browser-origin configuration.
4. Confirm sponsor submission requirements and rehearse the full demo.
