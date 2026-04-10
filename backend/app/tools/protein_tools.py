from __future__ import annotations

from app.models.schemas import ProteinFetchResponse, ProteinSearchResult
from app.services.protein_service import ProteinService


def search_protein_by_name(service: ProteinService, query: str) -> list[ProteinSearchResult]:
    return service.search(query)


def fetch_protein_structure(service: ProteinService, query: str) -> ProteinFetchResponse:
    return service.fetch(query)

