import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv


REQUIRED_RELATIONS = (
    "public.utilities",
    "public.projects",
    "public.project_sources",
    "public.coordination_opportunities",
)


def main() -> int:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print(
            "DATABASE_URL is not configured. Copy database/.env.example to database/.env.",
            file=sys.stderr,
        )
        return 2

    try:
        with psycopg.connect(database_url, connect_timeout=10) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "select current_database(), current_user, postgis_version()"
                )
                database_name, database_user, postgis_version = cursor.fetchone()
                cursor.execute(
                    "select relation_name, to_regclass(relation_name) is not null "
                    "from unnest(%s::text[]) as relation_name",
                    (list(REQUIRED_RELATIONS),),
                )
                missing = [name for name, exists in cursor.fetchall() if not exists]
    except psycopg.Error as exc:
        message = exc.diag.message_primary or exc.__class__.__name__
        print(f"Database check failed: {message}", file=sys.stderr)
        return 3

    if missing:
        print(f"Database check failed: missing {', '.join(missing)}", file=sys.stderr)
        return 1

    print(
        f"Database ready: {database_name} as {database_user}; "
        f"PostGIS {postgis_version}; schema complete."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
