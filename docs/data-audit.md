# Supplied workbook audit

## Scope

This audit covers `Challenge Docs/Projects_Overlaps.xlsx` as a read-only input.
It records what can be used for the GridLock MVP, how it maps to the proposed v1
project contract, and what must remain uncertain. It does not validate each value
against the original utility PDFs.

## Inventory

| Sheet | Records | Purpose |
| --- | ---: | --- |
| `projects` | 10 | Five Dominion Energy South Carolina and five Georgia Power projects |
| `overlaps` | 6 | Cross-utility project pairs within 25 miles |

The six supplied distances reproduce to two decimal places with an independent
Haversine calculation using the cached `lat_center` and `lon_center` values. They
are also the complete set of cross-utility pairs within 25 miles among the ten
supplied projects.

## Import mapping

| Workbook field | v1 contract field | Import treatment |
| --- | --- | --- |
| `project_id` | `project_id` | Preserve as the stable ID for this dataset |
| `utility` | `utility_id` | Map to `dominion_sc` or `georgia_power` |
| `project_name` | `project_name` | Preserve |
| `state` | `state` | Accepted nullable two-letter field in the v1 contract; preserve source evidence |
| `name_a`, `name_b` | `location_text` | Join as an endpoint description without implying a full route |
| `lat_center`, `lon_center` | `latitude`, `longitude` | Use as the representative point after formula evaluation |
| endpoint coordinates | `location_method` and raw import data | Describe whether the center used one known endpoint or the arithmetic midpoint of two endpoints |
| `in_service_date` | `in_service_date` | Parse and emit ISO text at the precision actually present |
| `overlap_count`, `overlap_1..3` | None | Do not import as authoritative data; recompute opportunities |

Fields absent from the workbook remain null until supported by source evidence:
`description`, `construction_start`, `construction_end`, and `schedule_text`.
`project_type`, `sources`, `review_status`, and `notes` require enrichment or
review before a record can be marked validated.

## Data-quality findings

1. `in_service_date` mixes Excel date values and text such as `12/31/2024` and
   `6/1/2033`. The importer must parse both and output one ISO representation.
2. `lat_center` and `lon_center` are formulas. When both endpoint coordinates are
   present, they calculate the arithmetic midpoint. When only one endpoint is
   present, they use that endpoint. These points are approximations and are not
   verified transmission-route geometries.
3. Several endpoint coordinate pairs are incomplete. The representative point is
   still usable for an MVP if it is labeled approximate and its method is retained.
4. The `overlaps` sheet contains absolute gaps between in-service dates. It does
   not prove that construction windows overlap. GridLock should report timeline
   status as unknown until actual construction start and end dates are available.
5. The workbook does not contain per-field source locators. Records should remain
   `needs_review` until data science ties the relevant values to PDF pages or other
   public evidence.
6. The workbook file properties contain an author/editor name. Review or sanitize
   document metadata before public distribution if the team did not intend to
   publish it.

## Recommended MVP treatment

- Import the ten projects only after converting them to the shared JSON contract.
- Treat center coordinates as approximate representative points and expose that
  limitation in the API and interface.
- Recompute all cross-utility distances instead of trusting stored overlap IDs.
- Use the supplied six pairs as regression fixtures for the distance calculation.
- Keep `construction_start` and `construction_end` null. Do not reinterpret the
  in-service date as a construction window.
- Preserve the original workbook unchanged under `Challenge Docs/`.

## Decision status after the initial audit

1. Accepted: the shared contract includes a nullable two-letter `state` field.
2. Accepted: for the 12-hour MVP, use the representative point in the contract while
   preserving endpoint names and coordinates in raw import data. A future version
   can add route geometry or a separate project-location structure.
3. Accepted: workbook rows start as `needs_review`; only promote records to
   `validated` after source locators are attached.
4. Resolved: Boris maintains the authoritative PostGIS overlap view; the backend
   consumes it. See context.md for the current dataset and API decisions.
