"""API contract checks; live database reads require GRIDLOCK_TEST_DATABASE=1.

Uses unittest and the application's ASGI interface, without a test-client package.
Synthetic records stay in memory and are never loaded into the database.
"""

import asyncio
import copy
from decimal import Decimal
import json
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import psycopg

import db
import main
from database.gridlock_importer.validation import validate_batch
from recommendations.engine import self_test_data


ROOT = Path(__file__).resolve().parents[1]


async def asgi_get(path, method="GET", headers=()):
    messages = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(k.encode(), v.encode()) for k, v in headers],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await main.app(scope, receive, send)
    start = next(m for m in messages if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    headers = dict(start["headers"])
    if headers.get(b"content-type") == b"application/json":
        body = json.loads(body)
    return start["status"], headers, body


def get(path, method="GET", headers=()):
    return asyncio.run(asgi_get(path, method, headers))


class BackendApiTests(unittest.TestCase):
    def setUp(self):
        self.sample = json.loads(
            (ROOT / "database/examples/projects.sample.json").read_text()
        )["projects"][0]

    def test_health_is_json_and_does_not_require_database(self):
        with patch("db.get_connection", side_effect=AssertionError("DB accessed")):
            status, headers, body = get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(headers[b"content-type"], b"application/json")
        self.assertEqual(body, {"status": "ok"})

    def test_cors_allows_local_frontend_origin_for_get(self):
        origin = ("origin", "http://localhost:5173")
        status, headers, _ = get("/health", headers=[origin])
        self.assertEqual(status, 200)
        self.assertEqual(
            headers[b"access-control-allow-origin"], b"http://localhost:5173"
        )
        status, headers, _ = get(
            "/projects",
            method="OPTIONS",
            headers=[origin, ("access-control-request-method", "GET")],
        )
        self.assertEqual(status, 200)
        self.assertIn(b"GET", headers[b"access-control-allow-methods"])

    def test_cors_rejects_unlisted_origin(self):
        status, headers, _ = get(
            "/health", headers=[("origin", "https://example.invalid")]
        )
        self.assertEqual(status, 200)
        self.assertNotIn(b"access-control-allow-origin", headers)

    def test_projects_preserve_contract_and_both_utilities(self):
        other = copy.deepcopy(self.sample)
        other.update(project_id="fixture-georgia-001", utility_id="georgia_power")
        rows = [self.sample, other]
        with patch("main.fetch_projects", return_value=rows):
            status, headers, body = get("/projects")
        self.assertEqual(status, 200)
        self.assertEqual(headers[b"content-type"], b"application/json")
        self.assertEqual(body, {"schema_version": "1.0", "projects": rows})
        validate_batch(body)

    def test_projects_preserve_date_precision_nulls_and_evidence(self):
        for date in (None, "2027", "2027-02", "2027-02-28"):
            with self.subTest(date=date):
                row = copy.deepcopy(self.sample)
                row.update(
                    construction_start=None,
                    construction_end=None,
                    in_service_date=date,
                )
                with patch("main.fetch_projects", return_value=[row]):
                    status, _, body = get("/projects")
                self.assertEqual(status, 200)
                self.assertEqual(body["projects"][0], row)
                self.assertIsNone(body["projects"][0]["latitude"])
                self.assertIsNone(body["projects"][0]["longitude"])
                self.assertEqual(body["projects"][0]["sources"], row["sources"])
                validate_batch(body)

    def test_projects_preserve_approximate_location_and_review_status(self):
        row = copy.deepcopy(self.sample)
        row.update(
            latitude=33.0,
            longitude=-81.0,
            location_quality="approximate",
            location_method="Synthetic test point; not a real facility",
            review_status="needs_review",
        )
        row["sources"][0]["supports"].extend(
            ["latitude", "longitude", "location_quality", "location_method"]
        )
        with patch("main.fetch_projects", return_value=[row]):
            status, _, body = get("/projects")
        self.assertEqual(status, 200)
        self.assertEqual(body["projects"], [row])
        validate_batch(body)

    def test_empty_projects_remain_versioned(self):
        with patch("main.fetch_projects", return_value=[]):
            status, _, body = get("/projects")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"schema_version": "1.0", "projects": []})

    def test_database_failures_return_sanitized_503(self):
        for error_type in (psycopg.OperationalError, psycopg.ProgrammingError):
            for endpoint, label in (("projects", "Project"), ("opportunities", "Opportunity")):
                with self.subTest(error=error_type.__name__, endpoint=endpoint):
                    with patch(
                        "db.get_connection",
                        side_effect=error_type("PRIVATE_CONNECTION_DETAILS"),
                    ):
                        status, _, body = get(f"/{endpoint}")
                    self.assertEqual(status, 503)
                    self.assertEqual(
                        body, {"detail": f"{label} data is temporarily unavailable."}
                    )
                    self.assertNotIn("PRIVATE_CONNECTION_DETAILS", json.dumps(body))

    def test_missing_database_configuration_returns_sanitized_503(self):
        for endpoint, label in (("projects", "Project"), ("opportunities", "Opportunity")):
            with self.subTest(endpoint=endpoint), patch.dict(os.environ, {}, clear=True):
                status, _, body = get(f"/{endpoint}")
            self.assertEqual(status, 503)
            self.assertEqual(body, {"detail": f"{label} data is temporarily unavailable."})

    def test_empty_opportunities_remain_versioned(self):
        with patch("main.fetch_opportunities", return_value=[]):
            status, _, body = get("/opportunities")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"schema_version": "1.0", "opportunities": []})

    def test_recommendations_explain_backend_results(self):
        projects, opportunities = self_test_data()
        with (
            patch("main.fetch_projects", return_value=list(projects.values())),
            patch("main.fetch_opportunities", return_value=opportunities),
        ):
            status, _, body = get("/recommendations")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(len(body["recommendations"]), 1)
        recommendation = body["recommendations"][0]
        self.assertEqual(recommendation["project_id_a"], "TEST_A")
        self.assertEqual(recommendation["project_id_b"], "TEST_B")
        self.assertEqual(recommendation["distance_miles"], 8.77)
        self.assertIn("within the 25-mile threshold", recommendation["why_flagged"])

    def test_opportunities_serialize_distance_and_explain_uncertainty(self):
        for timeline in ("overlap", "no_overlap", "unknown"):
            with self.subTest(timeline=timeline):
                row = {
                    "project_id_a": "fixture-a", "project_id_b": "fixture-b",
                    "distance_miles": Decimal("1.000123456"),
                    "distance_method": "postgis_geography",
                    "location_uncertain": True, "timeline_status": timeline,
                }
                connection = MagicMock()
                connection.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchall.return_value = [row]
                with patch("db.get_connection", return_value=connection):
                    status, _, body = get("/opportunities")
                self.assertEqual(status, 200)
                self.assertEqual(body["schema_version"], "1.0")
                result = body["opportunities"][0]
                self.assertEqual(set(result), {
                    "project_id_a", "project_id_b", "distance_miles", "distance_method",
                    "location_uncertain", "timeline_status", "reason",
                })
                self.assertEqual(result["distance_miles"], 1.000123456)
                self.assertEqual(result["timeline_status"], timeline)
                self.assertIn("provisional", result["reason"])
                self.assertIn("Point distance does not establish", result["reason"])
                expected = {
                    "overlap": "windows overlap using the source date precision",
                    "no_overlap": "windows do not overlap using the source date precision",
                    "unknown": "timing is unknown",
                }[timeline]
                self.assertIn(expected, result["reason"])

    def test_openapi_exposes_agreed_response_contracts(self):
        status, _, document = get("/openapi.json")
        self.assertEqual(status, 200)
        self.assertEqual(set(document["paths"]), {"/health", "/projects", "/opportunities", "/recommendations"})
        models = document["components"]["schemas"]
        self.assertEqual(set(models["Project"]["required"]), set(self.sample))
        self.assertEqual(len(models["Opportunity"]["required"]), 7)

    @unittest.skipUnless(
        os.getenv("GRIDLOCK_TEST_DATABASE") == "1", "live database check is opt-in"
    )
    def test_live_projects_match_contract_and_include_both_utilities(self):
        original_connection = db.get_connection

        def read_only_connection():
            connection = original_connection()
            connection.read_only = True
            return connection

        with patch("db.get_connection", side_effect=read_only_connection):
            status, _, body = get("/projects")
        self.assertEqual(status, 200, body)
        projects = validate_batch(body)
        self.assertEqual(
            {p["utility_id"] for p in projects}, {"dominion_sc", "georgia_power"}
        )
        ids = [p["project_id"] for p in projects]
        self.assertEqual(ids, sorted(ids))
        master = json.loads((ROOT / "data/master_projects.json").read_text())["projects"]

        def normalize(records):
            return {
                p["project_id"]: p | {"sources": sorted(
                    p["sources"], key=lambda s: (s["reference"], s["locator"])
                )} for p in records
            }

        self.assertEqual(normalize(projects), normalize(master))

    @unittest.skipUnless(
        os.getenv("GRIDLOCK_TEST_DATABASE") == "1", "live database check is opt-in"
    )
    def test_live_opportunities_are_ranked_and_backed_by_eligible_projects(self):
        original_connection = db.get_connection

        def read_only_connection():
            connection = original_connection()
            connection.read_only = True
            return connection

        with patch("db.get_connection", side_effect=read_only_connection):
            projects = {p["project_id"]: p for p in db.get_projects()}
            status, _, body = get("/opportunities")
        self.assertEqual(status, 200, body)
        opportunities = body["opportunities"]
        order = {"overlap": 0, "unknown": 1, "no_overlap": 2}
        self.assertEqual(opportunities, sorted(opportunities, key=lambda o: (
            o["distance_miles"], order[o["timeline_status"]], o["project_id_a"], o["project_id_b"]
        )))
        pairs = set()
        for item in opportunities:
            pair = (item["project_id_a"], item["project_id_b"])
            self.assertLess(*pair)
            self.assertNotIn(pair, pairs)
            pairs.add(pair)
            a, b = (projects[project_id] for project_id in pair)
            self.assertNotEqual(a["utility_id"], b["utility_id"])
            self.assertLessEqual(item["distance_miles"], 25)
            for project in (a, b):
                self.assertEqual(project["review_status"], "validated")
                self.assertIsNotNone(project["latitude"])
                self.assertNotIn("synthetic-fixture", [s["reference"] for s in project["sources"]])


if __name__ == "__main__":
    unittest.main()
