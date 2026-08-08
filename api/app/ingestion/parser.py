import io
from dataclasses import dataclass

import pdfplumber


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str


def parse_pdf(content: bytes) -> list[ParsedPage]:
    pages: list[ParsedPage] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            pages.append(ParsedPage(page_number=index, text=page.extract_text() or ""))
    return pages
