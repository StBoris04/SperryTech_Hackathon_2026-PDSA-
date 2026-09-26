# GridLock project context

## Status and purpose

Initial team draft for a four-person hackathon with approximately 12 hours total.
The repository currently contains source documents, an XLSX workbook, and a minimal
README; no application implementation or configured integration has been verified.

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

## Selected tracks and proposed stack

Selected tracks: **Sperry Tech + Gemini API + Tiger Data**. Official Gemini and
Tiger Data prize submission requirements still need checking before submission.

| Layer | Team proposal | Decision status |
| --- | --- | --- |
| Frontend | React + Tailwind CSS | Proposed baseline |
| Map | Leaflet or Mapbox GL JS | Selection pending |
| Backend | Python + FastAPI | Proposed baseline |
| Storage | Tiger Data / PostgreSQL | Selected track; instance/schema pending |
| AI | Gemini API for structured extraction; optional explanations | Selected track; integration pending |
| Geography | PostGIS if supported by the actual Tiger Data instance | Verify capability before choosing |
| Python geography | GeoPy, Shapely, GeoPandas as needed | Alternatives; do not install all by default |
| API testing | Postman | Team preference |
| Version control | GitHub | Team preference |
| Deployment | Vercel frontend; Render or Railway backend | Undecided; choose a fast viable path |

Intended flow: public PDF/XLSX -> extraction and validation -> shared JSON records
-> Tiger Data -> overlap analysis and API -> interactive map and ranked list.
The team must assign one owner for overlap computation across backend and data
engineering so that there is one authoritative implementation.

## Available source files

- `Challenge Docs/ShellHacks_Challenge_Gridlock.pdf`: challenge requirements.
- `Challenge Docs/Finding_Real_Locations_Guide.pdf`: location research guide; review before enrichment.
- `Challenge Docs/Projects_Overlaps.xlsx`: supplied workbook; contents and assumptions not yet audited.
- `Challenge Docs/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf`.
- `Challenge Docs/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf`.

Start with Dominion Energy South Carolina and Georgia Power. Public project pages,
SCRTP, and public GIS/HIFLD are potential enrichment sources, not yet verified
matches for any record. Preserve original files.

## Shared project handoff contract: v1 draft

Accepted decision: keep `construction_start`, `construction_end`, and
`in_service_date` as separate fields. Missing construction dates remain null;
an in-service milestone does not establish a construction window. Preserve the
source's date precision. This decision approves the date-field distinction;
the remaining contract and analysis proposals still need review.

This is the initial interface proposal for team review, not an implemented database
schema. Once accepted, changes follow the approval rule in AGENTS.md. Use a UTF-8
JSON object containing `schema_version: "1.0"` and a `projects` array. All fields
below are present; use JSON null for unavailable scalar values, never empty strings
or placeholder coordinates. Each array member represents one project.

| Field | Type | Meaning |
| --- | --- | --- |
| project_id | string | Stable identifier assigned at extraction; reused on reimport |
| utility_id | string | Controlled ID: dominion_sc or georgia_power initially |
| project_name | string | Source-backed project name |
| project_type | string | transmission_line, substation, other, or unknown |
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

## Analysis and API handoff: proposal

For every candidate pair, preserve the two project IDs, `distance_miles`,
`distance_method`, `location_uncertain`, `timeline_status`, and `reason`.
Use canonical project-ID order so that A/B and B/A are not duplicated.
Timeline status is `overlap`, `no_overlap`, or `unknown`.

For two complete construction windows, compare inclusive intervals. Expand coarse
start dates to the first day of the stated period and coarse end dates to the last
day only inside the calculation. Report the result as based on the source's date
precision. If either window is incomplete, report unknown rather than inventing
missing bounds.

Initial ranking proposal: filter to cross-utility pairs within 25 miles; sort by
distance ascending, then timeline status (overlap, unknown, no_overlap), then
project IDs for stable ties. This deliberately simple baseline keeps geography
primary. Agree on any richer scoring formula before implementation; do not invent
an unexplained opportunity score.

Suggested endpoints for backend/frontend review:

- `GET /health`: service health without secrets.
- `GET /projects`: `{ "schema_version": "1.0", "projects": [...] }`.
- `GET /opportunities`: `{ "schema_version": "1.0", "opportunities": [...] }`.

Opportunity object shape, filters, error responses, and pagination remain to be
agreed before implementation. Postman examples and frontend fixtures should use
the agreed payloads. No ingestion/admin endpoint is required for the MVP.

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

1. Review the remaining v1 project contract and analysis proposal; the separate
   construction-start, construction-end, and in-service fields are accepted.
2. Assign the overlap-computation owner; team roles are recorded in AGENTS.md.
3. Confirm stack choices and Tiger Data/PostGIS access.
4. Agree endpoint responses and one shared sample payload.
5. Choose the demo dataset and deployment destination.
