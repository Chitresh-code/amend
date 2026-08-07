"""Apply pending SQL migrations from migrations/ in filename order.

No ORM is in use (psycopg only), so migrations are plain numbered .sql files
rather than an Alembic autogenerate setup. Each file runs once, in one
transaction, tracked in schema_migrations.
"""

import sys
from pathlib import Path

import psycopg

from app.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def applied_migrations(conn: psycopg.Connection) -> set[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    rows = conn.execute("SELECT filename FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def main() -> None:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("No migration files found.")
        return

    with psycopg.connect(settings.postgres_dsn, autocommit=False) as conn:
        applied = applied_migrations(conn)
        conn.commit()

        pending = [f for f in files if f.name not in applied]
        if not pending:
            print("Nothing to apply, up to date.")
            return

        for path in pending:
            print(f"Applying {path.name} ...")
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            print(f"Applied {path.name}")


if __name__ == "__main__":
    try:
        main()
    except psycopg.Error as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        sys.exit(1)
