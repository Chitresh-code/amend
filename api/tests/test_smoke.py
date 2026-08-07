"""Environment smoke test: no application code exists yet, so this only
verifies the declared runtime and dependencies actually install and import.
"""

import sys


def test_python_version() -> None:
    assert sys.version_info >= (3, 12)


def test_core_dependencies_import() -> None:
    import cryptography  # noqa: F401
    import fastapi  # noqa: F401
    import neo4j  # noqa: F401
    import pgvector  # noqa: F401
    import psycopg  # noqa: F401
    import pydantic  # noqa: F401
    import pydantic_settings  # noqa: F401
    import redis  # noqa: F401
    import strands  # noqa: F401
