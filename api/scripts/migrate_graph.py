"""Apply the Neo4j schema (constraints/indexes) from docs/DATA_MODEL.md §2.3.

Neo4j has no migration-file history the way Postgres does (scripts/migrate.py):
every statement in app.graph.schema.CONSTRAINTS is declarative and IF NOT
EXISTS, so applying the whole set is always safe and there's nothing to track.
"""

import sys

from neo4j.exceptions import Neo4jError

from app.graph.db import get_driver
from app.graph.schema import apply_constraints


def main() -> None:
    driver = get_driver()
    try:
        apply_constraints(driver)
    finally:
        driver.close()
    print("Graph schema applied.")


if __name__ == "__main__":
    try:
        main()
    except Neo4jError as exc:
        print(f"Graph schema apply failed: {exc}", file=sys.stderr)
        sys.exit(1)
