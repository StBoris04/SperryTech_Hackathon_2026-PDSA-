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

def get_projects():
    query = """
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

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()