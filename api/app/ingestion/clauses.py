import re
from dataclasses import dataclass, field

from app.ingestion.parser import ParsedPage

# ponytail: plain-text regex heuristics on a dotted/lettered numbering prefix
# ("4.2.", "B.6.1.", "5.1.2.5.") at the start of a line. Misses documents that
# number clauses another way (roman numerals, unnumbered headings, bounding-box
# based layout with no textual numbering), and can pick up numbered footnotes
# as spurious shallow clauses. Upgrade path: revisit once a full corpus run
# surfaces the real failure shapes in api/tests/fixtures/.
_HEADING_RE = re.compile(r"^(?P<number>(?:[A-Z]\.)?\d+(?:\.\d+)*\.)\s+(?P<heading>\S.+)$")
# A table-of-contents line looks like a heading match too ("Foo .......... 6"),
# but ends in dot-leaders and a page number rather than being real clause text.
_TOC_LEADER_RE = re.compile(r"\.{3,}\s*\d+\s*$")


@dataclass
class RawClause:
    clause_number: str
    heading: str | None
    page_number: int
    depth: int
    parent_index: int | None
    text_lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.text_lines).strip()


def _depth(clause_number: str) -> int:
    numeric_part = clause_number[2:] if clause_number[1:2] == "." else clause_number
    return len(numeric_part.rstrip(".").split("."))


def segment_clauses(pages: list[ParsedPage]) -> list[RawClause]:
    clauses: list[RawClause] = []
    stack: list[tuple[int, int]] = []  # (depth, clause_index), shallowest first
    current: RawClause | None = None

    for page in pages:
        for line in page.text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            match = _HEADING_RE.match(stripped)
            if match is None or _TOC_LEADER_RE.search(match.group("heading")):
                if current is not None:
                    current.text_lines.append(stripped)
                continue

            depth = _depth(match.group("number"))
            while stack and stack[-1][0] >= depth:
                stack.pop()
            parent_index = stack[-1][1] if stack else None

            current = RawClause(
                clause_number=match.group("number").rstrip("."),
                heading=match.group("heading"),
                page_number=page.page_number,
                depth=depth,
                parent_index=parent_index,
                text_lines=[stripped],
            )
            clauses.append(current)
            stack.append((depth, len(clauses) - 1))

    return clauses
