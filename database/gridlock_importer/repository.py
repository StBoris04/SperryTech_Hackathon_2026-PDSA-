from dataclasses import dataclass
from typing import Any

import psycopg


PROJECT_UPSERT = """
insert into public.projects (
    project_id,
    utility_id,
    project_name,
    project_type,
    state,
    description,
    location_text,
    location,
    location_quality,
    location_method,
    construction_start,
    construction_end,
    in_service_date,
    schedule_text,
    review_status,
    notes
)
values (
    %(project_id)s,
    %(utility_id)s,
    %(project_name)s,
    %(project_type)s,
    %(state)s,
    %(description)s,
    %(location_text)s,
    case
        when %(longitude)s::double precision is null then null
        else st_setsrid(
            st_makepoint(%(longitude)s, %(latitude)s),
            4326
        )::geography
    end,
    %(location_quality)s,
    %(location_method)s,
    %(construction_start)s,
    %(construction_end)s,
    %(in_service_date)s,
    %(schedule_text)s,
    %(review_status)s,
    %(notes)s
)
on conflict (project_id) do update
set
    utility_id = excluded.utility_id,
    project_name = excluded.project_name,
    project_type = excluded.project_type,
    state = excluded.state,
    description = excluded.description,
    location_text = excluded.location_text,
    location = excluded.location,
    location_quality = excluded.location_quality,
    location_method = excluded.location_method,
    construction_start = excluded.construction_start,
    construction_end = excluded.construction_end,
    in_service_date = excluded.in_service_date,
    schedule_text = excluded.schedule_text,
    review_status = excluded.review_status,
    notes = excluded.notes
"""

SOURCE_UPSERT = """
insert into public.project_sources (
    project_id,
    reference,
    locator,
    supports
)
values (%s, %s, %s, %s)
on conflict (project_id, reference, locator) do update
set supports = excluded.supports
"""


@dataclass(frozen=True)
class ImportReport:
    inserted_projects: int
    updated_projects: int
    imported_sources: int


def import_projects(database_url: str, projects: list[dict[str, Any]]) -> ImportReport:
    project_ids = [project["project_id"] for project in projects]

    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("set local statement_timeout = '15s'")
                cursor.execute(
                    "select project_id from public.projects where project_id = any(%s)",
                    (project_ids,),
                )
                existing_ids = {row[0] for row in cursor.fetchall()}

                source_count = 0
                for project in projects:
                    cursor.execute(PROJECT_UPSERT, project)
                    for source in project["sources"]:
                        cursor.execute(
                            SOURCE_UPSERT,
                            (
                                project["project_id"],
                                source["reference"],
                                source["locator"],
                                source["supports"],
                            ),
                        )
                        source_count += 1

    updated_count = len(existing_ids)
    return ImportReport(
        inserted_projects=len(projects) - updated_count,
        updated_projects=updated_count,
        imported_sources=source_count,
    )
