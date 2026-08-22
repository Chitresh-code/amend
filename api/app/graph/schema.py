from neo4j import Driver

# DATA_MODEL.md §2.3. IF NOT EXISTS makes every statement safe to re-run.
CONSTRAINTS: tuple[str, ...] = (
    "CREATE CONSTRAINT document_id_unique IF NOT EXISTS "
    "FOR (d:Document) REQUIRE d.document_id IS UNIQUE",
    "CREATE CONSTRAINT clause_id_unique IF NOT EXISTS FOR (c:Clause) REQUIRE c.clause_id IS UNIQUE",
    "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
    "FOR (e:Entity) REQUIRE e.canonical_name IS UNIQUE",
    "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS "
    "FOR (rc:RegulatoryConcept) REQUIRE rc.name IS UNIQUE",
    "CREATE CONSTRAINT regulator_name_unique IF NOT EXISTS "
    "FOR (r:Regulator) REQUIRE r.name IS UNIQUE",
    "CREATE INDEX clause_effective_range IF NOT EXISTS "
    "FOR (c:Clause) ON (c.effective_from, c.effective_until)",
)


def apply_constraints(driver: Driver) -> None:
    with driver.session() as session:
        for statement in CONSTRAINTS:
            session.run(statement)
