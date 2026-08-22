from dataclasses import dataclass
from datetime import date

from neo4j import Driver, ManagedTransaction

from app.ingestion.references import RelationshipType

# DATA_MODEL.md §2.1: Document/Clause node properties mirror the Postgres row
# for the same id. Only what's actually populated during ingestion today is
# written here; effective_date (Document) and effective_from/effective_until
# (Clause) stay unset in both stores until extraction logic for them exists.
_WRITE_DOCUMENT_GRAPH = """
MERGE (r:Regulator {name: $regulator})
MERGE (d:Document {document_id: $document_id})
SET d.title = $title,
    d.document_type = $document_type,
    d.reference_number = $reference_number,
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
    reference_number: str | None,
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
        reference_number=reference_number,
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
    reference_number: str | None,
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
            reference_number=reference_number,
            publication_date=publication_date,
            source_url=source_url,
            checksum=checksum,
            clauses=clauses,
        )


@dataclass
class DocumentRelationship:
    relationship_type: RelationshipType
    target_document_id: str
    confidence: float


# Cypher relationship types can't be parameterized, so this is one fixed query
# string per type rather than an f-string built from relationship_type -
# relationship_type is always one of the Literal values in
# app.ingestion.references, never text taken directly from a document.
_RELATIONSHIP_QUERIES: dict[RelationshipType, str] = {
    "AMENDS": """
        MATCH (a:Document {document_id: $source}), (b:Document {document_id: $target})
        MERGE (a)-[r:AMENDS]->(b)
        SET r.extraction_method = $extraction_method,
            r.confidence = $confidence,
            r.review_status = $review_status
    """,
    "SUPERSEDES": """
        MATCH (a:Document {document_id: $source}), (b:Document {document_id: $target})
        MERGE (a)-[r:SUPERSEDES]->(b)
        SET r.extraction_method = $extraction_method,
            r.confidence = $confidence,
            r.review_status = $review_status
    """,
    "CLARIFIES": """
        MATCH (a:Document {document_id: $source}), (b:Document {document_id: $target})
        MERGE (a)-[r:CLARIFIES]->(b)
        SET r.extraction_method = $extraction_method,
            r.confidence = $confidence,
            r.review_status = $review_status
    """,
    "CONSOLIDATES": """
        MATCH (a:Document {document_id: $source}), (b:Document {document_id: $target})
        MERGE (a)-[r:CONSOLIDATES]->(b)
        SET r.extraction_method = $extraction_method,
            r.confidence = $confidence,
            r.review_status = $review_status
    """,
    "WITHDRAWS": """
        MATCH (a:Document {document_id: $source}), (b:Document {document_id: $target})
        MERGE (a)-[r:WITHDRAWS]->(b)
        SET r.extraction_method = $extraction_method,
            r.confidence = $confidence,
            r.review_status = $review_status
    """,
}

_CLEAR_RELATIONSHIPS = """
MATCH (a:Document {document_id: $source})-[r:AMENDS|SUPERSEDES|CLARIFIES|CONSOLIDATES|WITHDRAWS]->()
DELETE r
"""


def _write_relationships(
    tx: ManagedTransaction,
    *,
    source_document_id: str,
    relationships: list[DocumentRelationship],
) -> None:
    tx.run(_CLEAR_RELATIONSHIPS, source=source_document_id)
    for relationship in relationships:
        tx.run(
            _RELATIONSHIP_QUERIES[relationship.relationship_type],
            source=source_document_id,
            target=relationship.target_document_id,
            extraction_method="explicit_reference",
            confidence=relationship.confidence,
            review_status="automatic",
        )


def write_document_relationships(
    driver: Driver,
    *,
    source_document_id: str,
    relationships: list[DocumentRelationship],
) -> None:
    with driver.session() as session:
        session.execute_write(
            _write_relationships,
            source_document_id=source_document_id,
            relationships=relationships,
        )
