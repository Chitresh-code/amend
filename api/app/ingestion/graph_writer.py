from dataclasses import dataclass
from datetime import date

from neo4j import Driver, ManagedTransaction

# DATA_MODEL.md §2.1: Document/Clause node properties mirror the Postgres row
# for the same id. Only what's actually populated during ingestion today is
# written here; effective_date/reference_number (Document) and
# effective_from/effective_until (Clause) stay unset in both stores until
# extraction logic for them exists.
_WRITE_DOCUMENT_GRAPH = """
MERGE (r:Regulator {name: $regulator})
MERGE (d:Document {document_id: $document_id})
SET d.title = $title,
    d.document_type = $document_type,
    d.publication_date = $publication_date,
    d.source_url = $source_url,
    d.checksum = $checksum,
    d.status = 'active'
MERGE (r)-[:ISSUES]->(d)
WITH d
OPTIONAL MATCH (d)-[:CONTAINS]->(existing:Clause)
DETACH DELETE existing
WITH d
UNWIND $clauses AS clause
MERGE (c:Clause {clause_id: clause.clause_id})
SET c.clause_number = clause.clause_number,
    c.heading = clause.heading,
    c.text = clause.text,
    c.page_number = clause.page_number,
    c.effective_from = null,
    c.effective_until = null,
    c.status = 'active'
MERGE (d)-[:CONTAINS]->(c)
"""


@dataclass
class ClauseRecord:
    clause_id: str
    clause_number: str
    heading: str | None
    text: str
    page_number: int


def _write(
    tx: ManagedTransaction,
    *,
    document_id: str,
    regulator: str,
    document_type: str,
    title: str,
    publication_date: date | None,
    source_url: str,
    checksum: str,
    clauses: list[ClauseRecord],
) -> None:
    tx.run(
        _WRITE_DOCUMENT_GRAPH,
        document_id=document_id,
        regulator=regulator,
        document_type=document_type,
        title=title,
        publication_date=publication_date.isoformat() if publication_date else None,
        source_url=source_url,
        checksum=checksum,
        clauses=[
            {
                "clause_id": clause.clause_id,
                "clause_number": clause.clause_number,
                "heading": clause.heading,
                "text": clause.text,
                "page_number": clause.page_number,
            }
            for clause in clauses
        ],
    )


def write_document_graph(
    driver: Driver,
    *,
    document_id: str,
    regulator: str,
    document_type: str,
    title: str,
    publication_date: date | None,
    source_url: str,
    checksum: str,
    clauses: list[ClauseRecord],
) -> None:
    with driver.session() as session:
        session.execute_write(
            _write,
            document_id=document_id,
            regulator=regulator,
            document_type=document_type,
            title=title,
            publication_date=publication_date,
            source_url=source_url,
            checksum=checksum,
            clauses=clauses,
        )
