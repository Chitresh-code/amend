from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveredDocument:
    regulator: str
    document_type: str
    title: str
    publication_date_text: str | None
    landing_url: str
