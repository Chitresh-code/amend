import re
from dataclasses import dataclass
from typing import Literal

from app.ingestion.parser import ParsedPage

RelationshipType = Literal["AMENDS", "SUPERSEDES", "CLARIFIES", "CONSOLIDATES", "WITHDRAWS"]

# Regulator reference numbers are heterogeneous across RBI/SEBI departments
# ("RBI/FED/2016-17/12", "HO/49/14/15(3)2026-CFD-POD1/I/16178/2026",
# "DBR.No.BP.BC.99/21.04.048/2019-20"): 2+ leading uppercase letters, then 2+
# "."/"/"-separated segments. This misses documents that cite a prior circular
# only by date or informal name, and can false-positive on other slash/dot-heavy
# uppercase tokens that aren't actually reference numbers - same kind of
# heuristic tradeoff as _HEADING_RE in clauses.py. Revisit once a full corpus
# run surfaces the real failure shapes.
_REFERENCE_NUMBER_RE = re.compile(r"\b[A-Z]{2,}(?:[./][A-Z0-9()-]+){2,}\b")

# (cue phrase regex, relationship type, confidence). Confidence values are
# heuristic constants chosen from the two real fixtures available at the time
# this was written, not a calibrated model - expect to revisit once ingestion
# runs against a fuller corpus.
_CUE_PATTERNS: tuple[tuple[re.Pattern[str], RelationshipType, float], ...] = (
    (re.compile(r"in supersession of|supersedes", re.I), "SUPERSEDES", 0.9),
    (re.compile(r"withdrawal of|hereby withdraw", re.I), "WITHDRAWS", 0.9),
    (
        re.compile(r"in partial modification of|in modification of|amended by", re.I),
        "AMENDS",
        0.85,
    ),
    (re.compile(r"consolidat|incorporate the provisions of", re.I), "CONSOLIDATES", 0.85),
    (re.compile(r"clarif", re.I), "CLARIFIES", 0.8),
)

# RBI/SEBI documents commonly cite several prior circulars off one cue phrase
# ("... to incorporate the provisions of the Circulars ... bearing reference
# numbers X, Y & Z ..."), so the window is scanned forward from the cue rather
# than backward from each reference number - otherwise only the reference
# nearest the cue would be attributed to it. 350 chars comfortably covers a
# three-item list in the real SEBI fixture; a much longer list, or unrelated
# text that happens to follow within that span, are the known failure modes.
_CUE_WINDOW_CHARS = 350
_HEADER_LINES_SCANNED = 15


@dataclass
class ExtractedReference:
    reference_number: str
    relationship_type: RelationshipType
    confidence: float


def normalize_reference_number(raw: str) -> str:
    return re.sub(r"\s*([./])\s*", r"\1", raw.strip()).upper()


def extract_reference_number(pages: list[ParsedPage]) -> str | None:
    """A document's own reference number sits in its page-1 header, before the
    first numbered clause - text segment_clauses never captures (clauses.py
    only appends to an already-started clause). Bounding the scan to the first
    few lines avoids picking up an unrelated reference-shaped token later on
    page 1."""
    if not pages:
        return None

    header_lines = pages[0].text.splitlines()[:_HEADER_LINES_SCANNED]
    for line in header_lines:
        match = _REFERENCE_NUMBER_RE.search(line)
        if match is not None:
            return normalize_reference_number(match.group(0))
    return None


def extract_referenced_documents(text: str) -> list[ExtractedReference]:
    best: dict[tuple[str, RelationshipType], float] = {}

    for pattern, relationship_type, confidence in _CUE_PATTERNS:
        for cue_match in pattern.finditer(text):
            window = text[cue_match.end() : cue_match.end() + _CUE_WINDOW_CHARS]
            for ref_match in _REFERENCE_NUMBER_RE.finditer(window):
                reference_number = normalize_reference_number(ref_match.group(0))
                key = (reference_number, relationship_type)
                best[key] = max(confidence, best.get(key, 0.0))

    return [
        ExtractedReference(reference_number=ref, relationship_type=rel, confidence=confidence)
        for (ref, rel), confidence in best.items()
    ]
