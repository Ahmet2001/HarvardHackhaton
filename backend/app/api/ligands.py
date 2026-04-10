from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
import requests

from app.api.deps import AppServices, get_services
from app.models.schemas import LigandCreateRequest, LigandLookupRequest, LigandRecord, LigandSearchResult

router = APIRouter(prefix="/ligands", tags=["ligands"])


@router.get("", response_model=list[LigandRecord])
def list_ligands(
    limit: int = Query(default=20, ge=1, le=100),
    services: AppServices = Depends(get_services),
) -> list[LigandRecord]:
    return services.ligand_service.list_recent(limit=limit)


@router.post("", response_model=LigandRecord)
def create_ligand(
    request: LigandCreateRequest,
    services: AppServices = Depends(get_services),
) -> LigandRecord:
    if not request.smiles:
        raise HTTPException(status_code=422, detail="SMILES input is required for this endpoint.")
    try:
        return services.ligand_service.create_from_smiles(request.smiles, request.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/search", response_model=list[LigandSearchResult])
def search_ligands(
    query: str = Query(..., min_length=1),
    services: AppServices = Depends(get_services),
) -> list[LigandSearchResult]:
    try:
        return services.ligand_service.search_pubchem_by_name(query)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"PubChem ligand search failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/lookup", response_model=LigandRecord)
def lookup_ligand(
    request: LigandLookupRequest,
    services: AppServices = Depends(get_services),
) -> LigandRecord:
    try:
        return services.ligand_service.create_from_pubchem_name(request.name)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"PubChem ligand lookup failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/upload", response_model=LigandRecord)
async def upload_ligand(
    file: UploadFile = File(...),
    services: AppServices = Depends(get_services),
) -> LigandRecord:
    content = await file.read()
    try:
        return services.ligand_service.create_from_upload(file.filename or "ligand.sdf", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{ligand_id}", response_model=LigandRecord)
def get_ligand(
    ligand_id: str,
    services: AppServices = Depends(get_services),
) -> LigandRecord:
    try:
        return services.ligand_service.get(ligand_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{ligand_id}/prepare", response_model=LigandRecord)
def prepare_ligand(
    ligand_id: str,
    services: AppServices = Depends(get_services),
) -> LigandRecord:
    try:
        ligand = services.ligand_service.get(ligand_id)
        return services.ligand_service.prepare_ligand(
            ligand,
            services.docking_service.settings.jobs_dir / f"ligand_{ligand_id}",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc


@router.get("/{ligand_id}/download")
def download_ligand(
    ligand_id: str,
    services: AppServices = Depends(get_services),
) -> FileResponse:
    try:
        ligand = services.ligand_service.get(ligand_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    path = Path(ligand.prepared_path or ligand.source_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Ligand file is missing: {path}")
    return FileResponse(path=path, filename=path.name)
