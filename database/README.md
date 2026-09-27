# GridLock database

The database layer uses Tiger Cloud PostgreSQL with PostGIS. It stores validated
utility projects and calculates cross-utility opportunities within 25 miles.

## Apply the initial schema

In the Tiger Cloud SQL editor, run:

1. `migrations/001_initial_schema.sql`
2. `verify.sql`

The migration is transactional and safe to rerun for the initial hackathon
workflow. It creates the `utilities`, `projects`, and `project_sources` tables,
their constraints and indexes, and the `coordination_opportunities` view.

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
gridlock-import path/to/projects.json --dry-run
```

After validation passes, import the same file:

```bash
gridlock-import path/to/projects.json
```

The importer validates the complete batch before connecting, then uses one short
transaction and atomic upserts. Reimporting a stable `project_id` updates the same
row and upserts its evidence records.

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
- Store partial dates at their source precision instead of inventing a day.
- Create locations with longitude first:

```sql
st_setsrid(st_makepoint(:longitude, :latitude), 4326)::geography
```

- Store at least one `project_sources` row for every project before promoting it
  to `validated`.
