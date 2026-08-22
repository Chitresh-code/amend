from app.ingestion.parser import ParsedPage
from app.ingestion.references import extract_reference_number, extract_referenced_documents


def test_extract_reference_number_rbi_header():
    pages = [
        ParsedPage(
            page_number=1,
            text=(
                "RBI/FED/2016-17/12\n"
                "FED Master Direction No. 17/2016-17 January 1, 2016\n"
                "To\n"
                "All Authorised Dealer Category – I banks\n"
            ),
        )
    ]
    assert extract_reference_number(pages) == "RBI/FED/2016-17/12"


def test_extract_reference_number_sebi_header():
    pages = [
        ParsedPage(
            page_number=1,
            text=(
                "MASTER CIRCULAR\n"
                "HO/49/14/15(3)2026-CFD-POD1/I/16178/2026 Issued on: September 26, 2023\n"
                "Last updated on: July 14, 2026\n"
            ),
        )
    ]
    assert extract_reference_number(pages) == "HO/49/14/15(3)2026-CFD-POD1/I/16178/2026"


def test_extract_reference_number_returns_none_when_absent():
    pages = [ParsedPage(page_number=1, text="To\nAll Regulated Entities\nDear Sir / Madam,\n")]
    assert extract_reference_number(pages) is None


def test_extract_reference_number_returns_none_for_empty_pages():
    assert extract_reference_number([]) is None


def test_extract_referenced_documents_from_real_sebi_consolidation_text():
    text = (
        "This Master Circular has been updated to reconcile with the MB Regulations as amended "
        "vide notification dated December 5, 2025 which has come into effect from January 3, "
        "2026 and to incorporate the provisions of the Circulars dated May 02, 2017, January "
        "02, 2026 & June 11, 2026 and bearing reference numbers "
        "SEBI/HO/MIRSD/MIRSD1/CIR/P/2017/38,\n"
        "HO/49/11/11(106)2025-CFD-RAC-DIL3/I/1796/2026 & "
        "HO/49/14/15(2)2026-CFD-POD1/I/13567/2026 on the subjects."
    )

    extracted = extract_referenced_documents(text)

    references = {item.reference_number for item in extracted}
    assert references == {
        "SEBI/HO/MIRSD/MIRSD1/CIR/P/2017/38",
        "HO/49/11/11(106)2025-CFD-RAC-DIL3/I/1796/2026",
        "HO/49/14/15(2)2026-CFD-POD1/I/13567/2026",
    }
    assert all(item.relationship_type == "CONSOLIDATES" for item in extracted)


def test_extract_referenced_documents_requires_a_nearby_cue_phrase():
    text = "Contact the department at DOR.No.BP.BC.99/21.04.048/2019-20 for further queries."
    assert extract_referenced_documents(text) == []


def test_extract_referenced_documents_deduplicates_repeated_mentions():
    text = (
        "In supersession of circular RBI/2015-16/380, ... "
        "This circular supersedes RBI/2015-16/380 in its entirety."
    )

    extracted = extract_referenced_documents(text)

    assert len(extracted) == 1
    assert extracted[0].reference_number == "RBI/2015-16/380"
    assert extracted[0].relationship_type == "SUPERSEDES"
