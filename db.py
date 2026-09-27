import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


ENV_PATH = Path(__file__).resolve().parent / "database" / ".env"
load_dotenv(ENV_PATH)


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    return psycopg.connect(
        database_url,
        connect_timeout=10,
        row_factory=dict_row,
    )


PROJECTS_QUERY = """
    SELECT
        p.project_id,
        p.utility_id,
        p.project_name,
        p.project_type,
        p.state,
        p.description,
        p.location_text,
        ST_Y(p.location::geometry) AS latitude,
        ST_X(p.location::geometry) AS longitude,
        p.location_quality,
        p.location_method,
        p.construction_start,
        p.construction_end,
        p.in_service_date,
        p.schedule_text,
        COALESCE(
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'reference', s.reference,
                        'locator', s.locator,
                        'supports', s.supports
                    )
                    ORDER BY s.reference, s.locator
                )
                FROM public.project_sources AS s
                WHERE s.project_id = p.project_id
            ),
            '[]'::jsonb
        ) AS sources,
        p.review_status,
        p.notes
    FROM public.projects AS p
    ORDER BY p.project_id
"""


def get_projects():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(PROJECTS_QUERY)
            return cursor.fetchall()


OPPORTUNITIES_QUERY = """
    SELECT project_id_a, project_id_b, distance_miles,
           distance_method, location_uncertain, timeline_status
    FROM public.coordination_opportunities
    ORDER BY distance_miles,
             CASE timeline_status
                 WHEN 'overlap' THEN 0
                 WHEN 'unknown' THEN 1
                 WHEN 'no_overlap' THEN 2
             END,
             project_id_a, project_id_b
"""


def opportunity_reason(opportunity):
    timeline = {
        "overlap": "Construction windows overlap using the source date precision.",
        "no_overlap": "Construction windows do not overlap using the source date precision.",
        "unknown": "Construction timing is unknown because at least one window is incomplete or invalid.",
    }[opportunity["timeline_status"]]
    uncertainty = (
        " At least one location is approximate; this opportunity is provisional."
        if opportunity["location_uncertain"] else ""
    )
    return (
        f"Cross-utility representative points are {opportunity['distance_miles']:.2f} miles apart "
        f"(within the inclusive 25-mile threshold). {timeline}{uncertainty} "
        "Point distance does not establish route separation or resource-sharing feasibility."
    )


def get_opportunities():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(OPPORTUNITIES_QUERY)
            opportunities = cursor.fetchall()
    for opportunity in opportunities:
        opportunity["reason"] = opportunity_reason(opportunity)
    return opportunities
