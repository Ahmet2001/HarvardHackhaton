from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from requests import RequestException

from app.api.deps import AppServices, get_services
from app.models.schemas import ProteinFetchRequest, ProteinFetchResponse, ProteinMetadata, ProteinSearchResult

router = APIRouter(prefix="/proteins", tags=["proteins"])


@router.get("", response_model=list[ProteinMetadata])
def list_proteins(
    limit: int = Query(default=20, ge=1, le=100),
    services: AppServices = Depends(get_services),
) -> list[ProteinMetadata]:
    return services.protein_service.list_recent(limit=limit)


@router.get("/search", response_model=list[ProteinSearchResult])
def search_proteins(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=25),
    services: AppServices = Depends(get_services),
) -> list[ProteinSearchResult]:
    try:
        return services.protein_service.search(query, limit=limit)
    except RequestException as exc:
        raise HTTPException(status_code=502, detail=f"RCSB PDB search failed: {exc}") from exc


@router.post("/fetch", response_model=ProteinFetchResponse)
def fetch_protein(
    request: ProteinFetchRequest,
    services: AppServices = Depends(get_services),
) -> ProteinFetchResponse:
    try:
        return services.protein_service.fetch(request.query)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RequestException as exc:
        raise HTTPException(status_code=502, detail=f"RCSB PDB request failed: {exc}") from exc


@router.get("/{protein_id}", response_model=ProteinMetadata)
def get_protein(
    protein_id: str,
    services: AppServices = Depends(get_services),
) -> ProteinMetadata:
    try:
        return services.protein_service.get(protein_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{protein_id}/download")
def download_protein(
    protein_id: str,
    services: AppServices = Depends(get_services),
) -> FileResponse:
    try:
        protein = services.protein_service.get(protein_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pdb_path = Path(protein.pdb_path)
    if not pdb_path.exists():
        raise HTTPException(status_code=404, detail=f"PDB file is missing: {pdb_path}")
    return FileResponse(
        path=pdb_path,
        filename=f"{protein.pdb_id}.pdb",
        media_type="chemical/x-pdb",
    )

