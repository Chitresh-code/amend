import hashlib
import re

_RBI_ID_RE = re.compile(r"[?&]id=(\d+)")
_SEBI_ID_RE = re.compile(r"_(\d+)\.html$")


def generate_document_id(regulator: str, landing_url: str, source_url: str) -> str:
    # Both regulators' own site IDs (RBI's ?id=NNNNN, SEBI's trailing _NNNNN.html)
    # are already stable, unique identifiers for a document on their site, more
    # reliable than trying to parse a reference number back out of PDF text.
    if regulator == "RBI":
        match = _RBI_ID_RE.search(landing_url)
        if match:
            return f"rbi:{match.group(1)}"
    elif regulator == "SEBI":
        match = _SEBI_ID_RE.search(landing_url)
        if match:
            return f"sebi:{match.group(1)}"

    digest = hashlib.sha256(source_url.encode()).hexdigest()[:16]
    return f"{regulator.lower()}:{digest}"


def generate_clause_id(document_id: str, sequence_index: int) -> str:
    return f"{document_id}:{sequence_index:04d}"
