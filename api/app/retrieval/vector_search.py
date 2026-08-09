import re
from dataclasses import dataclass

from pgvector import Vector
from pgvector.psycopg import register_vector_async
from psycopg import AsyncConnection

# table_name always originates from a migration (DATA_MODEL.md §1.3), never
# from request input, but it's still interpolated into raw SQL below, so it's
# validated defensively before use.
_TABLE_NAME_RE = re.compile(r"^clause_embeddings_[a-z0-9_]+$")


class RetrievalError(Exception):
    pass


@dataclass
class ClauseMatch:
    clause_id: str
    document_id: str
    clause_number: str
    heading: str | None
    text: str
    score: float


async def _resolve_table(conn: AsyncConnection, embedding_model_id: str) -> str:
    row = await (
        await conn.execute(
            "SELECT table_name, status FROM embedding_models WHERE embedding_model_id = %s",
            (embedding_model_id,),
        )
    ).fetchone()
    if row is None or row[1] != "ready":
        raise RetrievalError(f"{embedding_model_id} has no ready embedding index")
    table_name = str(row[0])
    if not _TABLE_NAME_RE.match(table_name):
        raise RetrievalError(f"refusing to use unexpected table name: {table_name}")
    return table_name


async def search_clauses(
    conn: AsyncConnection,
    query_embedding: list[float],
    embedding_model_id: str,
    *,
    top_k: int = 20,
    regulator: str | None = None,
    document_type: str | None = None,
) -> list[ClauseMatch]:
    await register_vector_async(conn)
    table_name = await _resolve_table(conn, embedding_model_id)

    filters = []
    params: list[object] = [Vector(query_embedding)]
    if regulator is not None:
        filters.append("d.regulator = %s")
        params.append(regulator)
    if document_type is not None:
        filters.append("d.document_type = %s")
        params.append(document_type)
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.append(top_k)

    rows = await (
        await conn.execute(
            f"""
            SELECT c.clause_id, c.document_id, c.clause_number, c.heading, c.text,
                   e.embedding <=> %s AS distance
            FROM {table_name} e
            JOIN clauses c ON c.clause_id = e.clause_id
            JOIN documents d ON d.document_id = c.document_id
            {where_clause}
            ORDER BY distance
            LIMIT %s
            """,  # noqa: S608 - table_name validated above, not request input
            params,
        )
    ).fetchall()

    return [
        ClauseMatch(
            clause_id=row[0],
            document_id=row[1],
            clause_number=row[2],
            heading=row[3],
            text=row[4],
            score=float(row[5]),
        )
        for row in rows
    ]
