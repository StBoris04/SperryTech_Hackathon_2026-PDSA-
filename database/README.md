# GridLock database

The database layer uses Tiger Cloud PostgreSQL with PostGIS. It stores projects
at both review statuses and calculates cross-utility opportunities within 25 miles
using only validated records with coordinates, excluding synthetic evidence.

## Apply the initial schema

In the Tiger Cloud SQL editor, run:

1. `migrations/001_initial_schema.sql`
2. `migrations/002_opportunity_timeline.sql`
3. `verify.sql`

The migration is transactional and safe to rerun for the initial hackathon
workflow. It creates the `utilities`, `projects`, and `project_sources` tables,
their constraints and indexes, and the `coordination_opportunities` view.

Migration 002 fixes inclusive comparisons of year/month construction dates and
keeps unrounded distances for ranking. It preserves the existing view's column
names and types. Both migrations are transactional and rerunnable; always apply
002 after 001, because rerunning 001 alone restores the initial view definition.
For an existing database with 001 applied, apply only 002.

## Install and test the importer

From `database/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
gridlock-import examples/projects.sample.json --dry-run
```

The included sample is synthetic and remains `needs_review`. Do not load it into
the shared Tiger Cloud service.

## Configure Tiger Cloud locally

Copy `.env.example` to `.env`, then place the rotated Tiger Cloud connection URI
in `DATABASE_URL`. The repository ignores `.env` files.

Verify local connectivity and the required schema without changing data:

```bash
python -m gridlock_importer.health
```

Validate Piero's complete batch before making database changes:

```bash
gridlock-import ../data/master_projects.json --dry-run
```

After validation passes, import the same file:

```bash
gridlock-import ../data/master_projects.json
```

The importer validates the complete batch before connecting, then uses one short
transaction and atomic upserts. Reimporting a stable `project_id` updates the same
row and upserts its evidence records.

These commands assume the current directory is `database/`. From the repository
root use `data/master_projects.json`. The API environment installed by the root
`requirements.txt` also provides `gridlock-import`.

The master contains 166 projects from the two selected utilities. The older
45-record `validated_projects.json` is an input to the master builder, not the
current full import batch. The 252-row raw extraction file is not import-ready
and includes 86 records from other utilities. Validation checks the payload
structure; it does not promote `needs_review` records or establish coordinates.

On 2026-09-27 the approved master sync inserted 121 projects and updated 45,
upserting 227 source references. All 45 previous state values were null; the
master adds source-supported states and updates those sources' `supports`
arrays. Every prior source reference was preserved. Full readback matched the
master, including review statuses and nulls. No records were deleted.

## Connection configuration

Applications should receive the Tiger Cloud connection URI through a local or
deployment environment variable:

```text
DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require
```

Do not commit a real URI, downloaded Tiger Cloud credential file, password, or
`.env` file. Use SSL mode `require` when connecting to Tiger Cloud.

## Data rules

- Import project IDs idempotently with an upsert.
- Keep extracted records as `needs_review` until their evidence is checked.
- Only `validated` records enter `coordination_opportunities`.
- A `synthetic-fixture` source reference excludes a project even if incorrectly
  marked validated. Keep all synthetic fixtures out of the shared database.
- Store partial dates at their source precision instead of inventing a day.
- Create locations with longitude first:

```sql
st_setsrid(st_makepoint(:longitude, :latitude), 4326)::geography
```

- Store at least one `project_sources` row for every project before promoting it
  to `validated`.

## Verify and recover

From the repository root, in the API environment:

```bash
python -m scripts.check_opportunity_view
GRIDLOCK_TEST_DATABASE=1 python -m unittest discover -s tests -p test_backend_api.py -v
```

The checks are read-only. The opportunity tests use in-memory synthetic CTEs,
never inserted rows, to verify distance boundaries, timeline precision,
eligibility, synthetic exclusion, and the API's exact ranking query.

Before synchronization, a local recovery snapshot was saved under ignored
`database/backups/20260927T061448Z/`: `projects.before.json`, `view.before.sql`,
and `added-project-ids.json`. No credentials are included. Do not commit backups.
The sync and migration were applied in one transaction and validated before
commit; a failed check would have rolled back both.

For recovery, stop imports and review subsequent team changes first. Reimporting
`projects.before.json` restores the original 45 project payloads; it does not
remove the 121 added rows. Execute the saved `view.before.sql` in a transaction
to restore the old view if necessary (this reintroduces the known coarse-date
limitation). Keep the added-ID list for any separately approved removal; never
blindly delete rows that may have been updated since the snapshot. The new date
helper can remain unused after restoring the view.
