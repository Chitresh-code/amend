from app.graph.schema import apply_constraints


def _constraint_names(driver):
    with driver.session() as session:
        return {row["name"] for row in session.run("SHOW CONSTRAINTS YIELD name RETURN name")}


def _index_names(driver):
    with driver.session() as session:
        return {row["name"] for row in session.run("SHOW INDEXES YIELD name RETURN name")}


def test_apply_constraints_creates_documented_schema(neo4j_driver):
    apply_constraints(neo4j_driver)

    constraints = _constraint_names(neo4j_driver)
    assert {
        "document_id_unique",
        "clause_id_unique",
        "entity_name_unique",
        "concept_name_unique",
        "regulator_name_unique",
    } <= constraints
    assert "clause_effective_range" in _index_names(neo4j_driver)


def test_apply_constraints_is_idempotent(neo4j_driver):
    apply_constraints(neo4j_driver)
    apply_constraints(neo4j_driver)  # must not raise on the second application

    assert "document_id_unique" in _constraint_names(neo4j_driver)
