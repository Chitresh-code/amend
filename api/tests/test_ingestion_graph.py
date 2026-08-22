from datetime import date

from app.ingestion.graph_writer import (
    ClauseRecord,
    DocumentRelationship,
    write_document_graph,
    write_document_relationships,
)


def _write(driver, document_id: str, clauses: list[ClauseRecord], *, regulator: str = "RBI"):
    write_document_graph(
        driver,
        document_id=document_id,
        regulator=regulator,
        document_type="master_direction",
        title="Test document",
        reference_number=None,
        publication_date=date(2024, 1, 15),
        source_url="https://rbidocs.rbi.org.in/rdocs/notification/PDFs/test.PDF",
        checksum="deadbeef",
        clauses=clauses,
    )


def test_write_document_graph_creates_nodes_and_relationships(neo4j_driver):
    clauses = [
        ClauseRecord(
            clause_id="rbi:test-1#0", clause_number="1", heading="Scope", text="...", page_number=1
        ),
        ClauseRecord(
            clause_id="rbi:test-1#1",
            clause_number="2",
            heading="Applicability",
            text="...",
            page_number=2,
        ),
    ]
    _write(neo4j_driver, "rbi:test-1", clauses)

    with neo4j_driver.session() as session:
        doc = session.run(
            "MATCH (r:Regulator {name: 'RBI'})-[:ISSUES]->(d:Document {document_id: $id}) "
            "RETURN d.title AS title, d.status AS status",
            id="rbi:test-1",
        ).single()
        assert doc is not None
        assert doc["title"] == "Test document"
        assert doc["status"] == "active"

        clause_count = session.run(
            "MATCH (:Document {document_id: $id})-[:CONTAINS]->(c:Clause) RETURN count(c) AS n",
            id="rbi:test-1",
        ).single()["n"]
        assert clause_count == 2

        clause = session.run(
            "MATCH (c:Clause {clause_id: 'rbi:test-1#0'}) "
            "RETURN c.clause_number AS number, c.heading AS heading, c.status AS status",
        ).single()
        assert clause["number"] == "1"
        assert clause["heading"] == "Scope"
        assert clause["status"] == "active"


def test_reingesting_replaces_clause_nodes(neo4j_driver):
    first_clauses = [
        ClauseRecord(
            clause_id="rbi:test-2#0", clause_number="1", heading="Old", text="...", page_number=1
        )
    ]
    _write(neo4j_driver, "rbi:test-2", first_clauses)

    second_clauses = [
        ClauseRecord(
            clause_id="rbi:test-2#0-v2",
            clause_number="1",
            heading="New",
            text="...",
            page_number=1,
        )
    ]
    _write(neo4j_driver, "rbi:test-2", second_clauses)

    with neo4j_driver.session() as session:
        stale = session.run("MATCH (c:Clause {clause_id: 'rbi:test-2#0'}) RETURN c").single()
        assert stale is None

        current = session.run(
            "MATCH (:Document {document_id: 'rbi:test-2'})-[:CONTAINS]->(c:Clause) "
            "RETURN c.clause_id AS clause_id"
        ).single()
        assert current["clause_id"] == "rbi:test-2#0-v2"

        doc_count = session.run(
            "MATCH (d:Document {document_id: 'rbi:test-2'}) RETURN count(d) AS n"
        ).single()["n"]
        assert doc_count == 1


def test_documents_from_same_regulator_share_regulator_node(neo4j_driver):
    _write(neo4j_driver, "rbi:test-3", [])
    _write(neo4j_driver, "rbi:test-4", [])

    with neo4j_driver.session() as session:
        regulator_count = session.run(
            "MATCH (r:Regulator {name: 'RBI'}) RETURN count(r) AS n"
        ).single()["n"]
        assert regulator_count == 1

        issued_count = session.run(
            "MATCH (:Regulator {name: 'RBI'})-[:ISSUES]->(d:Document) RETURN count(d) AS n"
        ).single()["n"]
        assert issued_count == 2


def test_write_document_relationships_creates_edge_with_provenance(neo4j_driver):
    _write(neo4j_driver, "rbi:source-1", [])
    _write(neo4j_driver, "rbi:target-1", [])

    write_document_relationships(
        neo4j_driver,
        source_document_id="rbi:source-1",
        relationships=[
            DocumentRelationship(
                relationship_type="SUPERSEDES", target_document_id="rbi:target-1", confidence=0.9
            )
        ],
    )

    with neo4j_driver.session() as session:
        edge = session.run(
            "MATCH (:Document {document_id: 'rbi:source-1'})-[r:SUPERSEDES]->"
            "(:Document {document_id: 'rbi:target-1'}) "
            "RETURN r.extraction_method AS method, r.confidence AS confidence, "
            "r.review_status AS review_status"
        ).single()
        assert edge is not None
        assert edge["method"] == "explicit_reference"
        assert edge["confidence"] == 0.9
        assert edge["review_status"] == "automatic"


def test_write_document_relationships_replaces_stale_edges(neo4j_driver):
    _write(neo4j_driver, "rbi:source-2", [])
    _write(neo4j_driver, "rbi:target-2a", [])
    _write(neo4j_driver, "rbi:target-2b", [])

    write_document_relationships(
        neo4j_driver,
        source_document_id="rbi:source-2",
        relationships=[
            DocumentRelationship(
                relationship_type="SUPERSEDES",
                target_document_id="rbi:target-2a",
                confidence=0.9,
            )
        ],
    )
    write_document_relationships(
        neo4j_driver,
        source_document_id="rbi:source-2",
        relationships=[
            DocumentRelationship(
                relationship_type="AMENDS", target_document_id="rbi:target-2b", confidence=0.85
            )
        ],
    )

    with neo4j_driver.session() as session:
        stale = session.run(
            "MATCH (:Document {document_id: 'rbi:source-2'})-[r:SUPERSEDES]->() RETURN r"
        ).single()
        assert stale is None

        current = session.run(
            "MATCH (:Document {document_id: 'rbi:source-2'})-[r:AMENDS]->"
            "(t:Document) RETURN t.document_id AS target"
        ).single()
        assert current["target"] == "rbi:target-2b"
