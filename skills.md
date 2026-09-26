# GridLock implementation workflows

This is a shared project playbook. Read [AGENTS.md](AGENTS.md) for working rules
and [context.md](context.md) for the authoritative handoff contract. Dependencies,
schemas, API contracts, and deployment decisions require the agreement described
there. The workflows below describe intended work, not completed capabilities.

## 1. Extract and validate projects

**Initial lead:** Data science.

1. Inspect the supplied PDF/XLSX sources and identify actual future transmission
   projects from both utilities. Review the location guide before enrichment.
2. Use Gemini for a meaningful extraction task; ask for contract-shaped records
   with source locators, nulls for missing values, and no invented facts.
3. Check extracted fields against the source. Preserve original schedule wording
   and distinguish in-service milestones from construction intervals.
4. Research coordinates using public evidence. Record the method, source, and
   whether the result is a verified facility point or an approximation.
5. Assign stable IDs, resolve duplicates, validate the contract, and mark reviewed
   records validated. Keep unresolved records visible as needs_review.

**Handoff:** A versioned JSON batch, source references, and a short list of unresolved
records. Include both utilities early so integration can begin with a small sample.

## 2. Store and load data

**Initial lead:** Boris, data engineering.

1. Verify Tiger Data connectivity and available geospatial capabilities without
   exposing credentials. Propose a minimal schema mapped to the shared contract.
2. Obtain agreement before creating/changing the schema or adding dependencies.
   Store source references and uncertainty, not only coordinates and names.
3. Validate before writing. Load in a transaction using parameterized queries;
   make repeated imports update the same stable IDs rather than duplicate rows.
4. Produce a concise import report: inserted, updated, rejected, and reasons.
   Preserve the previous valid data when a batch fails validation.
5. Verify counts by utility and retrieve a sample through the intended query path.

**Handoff:** Approved schema/migration, repeatable load instructions, import report,
and connection environment-variable names. Never include secret values.

## 3. Calculate coordination opportunities

**Lead:** Assign between data engineering and backend before implementation.

1. Use validated real projects with coordinates and compare different utilities.
2. Choose one distance implementation after checking actual database support.
   With PostGIS, use geography in meters or an appropriate projection, not raw
   longitude/latitude geometry distances. Convert 25 miles to 40,233.6 meters.
3. Deduplicate unordered pairs; apply the agreed 25-mile boundary convention.
4. Calculate timeline status using the agreed date-precision and missing-data
   rules. Keep location uncertainty in the opportunity output.
5. Apply the agreed deterministic ranking and generate a factual reason for each
   result. Gemini may explain evidence but must not invent feasibility or savings.

**Verification:** Same-point distance, just below/at/above threshold, same-utility
exclusion, duplicate pair exclusion, missing coordinates, overlapping/disjoint
windows, year-only dates, and missing construction dates.

**Handoff:** Candidate pairs, method description, ranking rule, and check results.

## 4. Build and test the API

**Initial lead:** Backend; Boris can assist with Postman.

1. Agree exact endpoint payloads with data engineering and frontend before
   implementation. Use one common sample payload to unblock UI work.
2. Keep database and Gemini credentials on the server. Use parameterized database
   access and validate any accepted filters.
3. Return consistent JSON, explicit nulls, and clear error status codes. Do not
   expose credentials or internal connection details in errors.
4. Save reproducible Postman requests with environment placeholders. Check health,
   projects from both utilities, opportunities, empty results, invalid inputs
   where supported, and a database failure response.

**Handoff:** Base URL, endpoint examples, Postman collection without secrets, and
known limitations. Confirm the frontend can consume the actual service.

## 5. Build the interactive view

**Initial lead:** Frontend.

1. Choose the map library with the team and build against the shared sample payload.
2. Display both utilities distinctly, with project details and source evidence.
   Show approximate locations and missing dates honestly.
3. Connect the ranked opportunities to the map so selecting a pair reveals both
   projects, distance, timing, and the reason for the ranking.
4. Include loading, empty, and failure states. Projects without coordinates should
   remain accessible in the list rather than appearing at a fake map location.
5. Replace fixtures with the real API and check map interaction and selection.

**Handoff:** Working view, configuration-variable names, screenshots, and a short
walkthrough of the demo path.

## 6. Integrate and present

**Lead:** All four teammates, with one agreed demo owner.

1. Trace a real source record through extraction, storage, API, and the interface.
2. Confirm ranked pairs are backed by real records and recomputable distances.
   If the validated data yields no matches, explain that result honestly.
3. Demonstrate meaningful Gemini use and actual Tiger Data storage/querying.
4. Explain the representative-point limitation and any uncertain dates/locations.
5. Add a cost/impact estimate only if time remains; label assumptions and estimates.
6. Agree deployment settings, run the demo once in the target environment, and
   prepare a local fallback with clearly labeled cached results if needed.
7. Use the AGENTS.md PR format for changes and document the final run instructions
   once executable commands actually exist.
