from pathlib import Path

from app.ingestion.clauses import segment_clauses
from app.ingestion.parser import parse_pdf

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_parse_pdf_extracts_pages_with_text():
    pages = parse_pdf(_load("rbi_master_direction_import_goods_services.pdf"))
    assert len(pages) > 1
    assert pages[0].page_number == 1
    assert any(p.text for p in pages)


def test_segment_clauses_builds_expected_structure():
    pages = parse_pdf(_load("rbi_master_direction_import_goods_services.pdf"))
    clauses = segment_clauses(pages)

    assert len(clauses) > 10
    # The RBI fixture has an index page listing section titles with the same
    # numbering as the real clauses that follow (no distinguishing dot-leaders,
    # unlike the SEBI fixture's table of contents) - pick the instance with
    # real body text, not the bare index listing, to check nesting.
    top_level = next(c for c in clauses if c.clause_number == "B.6" and len(c.text_lines) > 1)
    assert "Import of Foreign Exchange" in (top_level.heading or "")
    assert top_level.parent_index is None

    nested = next(c for c in clauses if c.clause_number == "B.6.1")
    parent_index = nested.parent_index
    assert parent_index is not None
    assert clauses[parent_index].clause_number == "B.6"


def test_segment_clauses_skips_table_of_contents_leaders():
    pages = parse_pdf(_load("sebi_master_circular_merchant_bankers.pdf"))
    clauses = segment_clauses(pages)
    assert not any(c.heading and "...." in c.heading for c in clauses)
