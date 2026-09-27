"""Read-only tests of deployed analysis and the API's actual ranking query.

Run python -m scripts.check_opportunity_view. Synthetic records exist only in a
query CTE; they are never inserted. Exit 1 means a contract failure, 2 an error.
"""
import re

from psycopg.types.json import Jsonb

import db

CASES = [
    ("same point", {}, 1, "unknown"),
    ("below 25 miles", {"meters": 40233.59}, 1, "unknown"),
    ("exactly 25 miles", {"meters": 40233.6}, 1, "unknown"),
    ("above 25 miles", {"meters": 40233.61}, 0, None),
    ("same utility", {"utility_b": "dominion_sc"}, 0, None),
    ("needs review", {"review_b": "needs_review"}, 0, None),
    ("missing coordinates", {"located_b": False}, 0, None),
    ("exact overlap", {"start_a": "2027-01-01", "end_a": "2027-06-30", "start_b": "2027-06-01", "end_b": "2027-12-31"}, 1, "overlap"),
    ("inclusive touching endpoints", {"start_a": "2027-01-01", "end_a": "2027-06-30", "start_b": "2027-06-30", "end_b": "2027-12-31"}, 1, "overlap"),
    ("exact disjoint windows", {"start_a": "2027-01-01", "end_a": "2027-06-30", "start_b": "2027-07-01", "end_b": "2027-12-31"}, 1, "no_overlap"),
    ("year precision overlap", {"start_a": "2027", "end_a": "2027", "start_b": "2027-06", "end_b": "2027-07"}, 1, "overlap"),
    ("month precision disjoint", {"start_a": "2027-01", "end_a": "2027-02", "start_b": "2027-03", "end_b": "2027-04"}, 1, "no_overlap"),
    ("incomplete window", {"start_a": "2027", "end_a": "2027", "start_b": "2027"}, 1, "unknown"),
    ("approximate location", {"quality_b": "approximate"}, 1, "unknown"),
]
CASES.extend([
    ("leap day inclusion", {"start_a": "2028-02", "end_a": "2028-02", "start_b": "2028-02-29", "end_b": "2028-02-29"}, 1, "overlap"),
    ("month-end exclusion", {"start_a": "2027-02", "end_a": "2027-02", "start_b": "2027-03-01", "end_b": "2027-03-01"}, 1, "no_overlap"),
    ("reversed window", {"start_a": "2028", "end_a": "2027", "start_b": "2027", "end_b": "2028"}, 1, "unknown"),
    ("synthetic evidence", {"synthetic_b": True}, 0, None),
])
DEFAULTS = dict(meters=0, utility_b="georgia_power", review_b="validated",
                located_b=True, quality_b="verified", start_a=None, end_a=None,
                start_b=None, end_b=None, synthetic_b=False)
FIXTURES = """WITH review_input AS (
    SELECT * FROM jsonb_to_recordset(%(records)s) AS r(
        project_id text, utility_id text, meters double precision,
        location_quality text, review_status text, construction_start text,
        construction_end text, reference text
    )
), review_projects AS (
    SELECT project_id, utility_id, 'Synthetic in-memory test'::text AS project_name,
           CASE WHEN meters IS NOT NULL THEN ST_Project(
               ST_SetSRID(ST_MakePoint(-81, 33), 4326)::geography, meters, 0
           ) ELSE NULL::geography END AS location,
           location_quality, review_status, construction_start, construction_end
    FROM review_input
), review_sources AS (
    SELECT project_id, reference FROM review_input
)
"""


def project(project_id, utility_id="georgia_power", meters=0, start=None, end=None):
    return dict(project_id=project_id, utility_id=utility_id, meters=meters,
                construction_start=start, construction_end=end,
                location_quality="verified", review_status="validated",
                reference="in-memory-test-only")


def probe_query(connection):
    definition = connection.execute(
        "SELECT pg_get_viewdef(%s::regclass, true) AS definition",
        ("public.coordination_opportunities",),
    ).fetchone()["definition"]
    definition, count = re.subn(
        r"\b(?:public\.)?projects(?=\s+project_[ab]\b)",
        "review_projects", definition,
    )
    assert count == 2, "Unexpected view shape; refusing to probe live projects"
    definition, count = re.subn(
        r"\b(?:public\.)?project_sources(?=\s+evidence\b)",
        "review_sources", definition,
    )
    assert count == 1, "Expected synthetic evidence exclusion"
    return (FIXTURES + ", review_opportunities AS (" + definition.strip().rstrip(";")
            + ") " + db.OPPORTUNITIES_QUERY.replace(
                "public.coordination_opportunities", "review_opportunities"))


def check(connection):
    query = probe_query(connection)
    failures = 0
    for name, overrides, expected_count, expected_timeline in CASES:
        values = DEFAULTS | overrides
        a = project("test-a", "dominion_sc", start=values["start_a"], end=values["end_a"])
        b = project("test-b", values["utility_b"],
                    values["meters"] if values["located_b"] else None,
                    values["start_b"], values["end_b"])
        b.update(review_status=values["review_b"], location_quality=values["quality_b"])
        if values["synthetic_b"]:
            b["reference"] = "synthetic-fixture"
        rows = connection.execute(query, {"records": Jsonb([a, b])}).fetchall()
        timeline = rows[0]["timeline_status"] if rows else None
        passed = len(rows) == expected_count and timeline == expected_timeline
        if rows:
            passed = passed and rows[0]["project_id_a"] < rows[0]["project_id_b"]
            passed = passed and rows[0]["location_uncertain"] == (values["quality_b"] == "approximate")
        failures += not passed
        print(f'{"PASS" if passed else "FAIL"}: {name}')

    # All counterparts share a utility, so only pairs with test-a are eligible.
    # The closest pair must outrank overlap even when both distances display 1.00.
    records = [
        project("test-a", "dominion_sc", start="2027", end="2027"),
        project("test-near", meters=1609.344, start="2028", end="2028"),
        project("test-far", meters=1609.345, start="2027", end="2027"),
        project("test-z-overlap", meters=3200, start="2027", end="2027"),
        project("test-y-unknown", meters=3200),
        project("test-b-disjoint", meters=3200, start="2028", end="2028"),
        project("test-c-disjoint", meters=3200, start="2028", end="2028"),
    ]
    rows = connection.execute(query, {"records": Jsonb(records)}).fetchall()
    expected = ["test-near", "test-far", "test-z-overlap", "test-y-unknown",
                "test-b-disjoint", "test-c-disjoint"]
    passed = [r["project_id_b"] for r in rows] == expected
    failures += not passed
    print(f'{"PASS" if passed else "FAIL"}: full-precision distance, timeline, ID ranking')
    total = len(CASES) + 1
    print(f"{total - failures}/{total} opportunity checks passed")
    return failures


def main():
    try:
        with db.get_connection() as connection:
            connection.read_only = True
            connection.execute("SET LOCAL statement_timeout = '15s'")
            return 1 if check(connection) else 0
    except Exception as exc:
        print("PROBE_ERROR:", type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
