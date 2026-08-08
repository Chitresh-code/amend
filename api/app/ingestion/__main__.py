import logging

import psycopg

from app.config import settings
from app.ingestion.run import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    with psycopg.connect(settings.postgres_dsn, autocommit=True) as conn:
        summary = run(conn)
    logger.info(
        "ingestion run complete: succeeded=%d skipped=%d failed=%d",
        summary.succeeded,
        summary.skipped,
        summary.failed,
    )


if __name__ == "__main__":
    main()
