from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.deps import AppServices, get_services
from app.models.schemas import DockingJob, DockingPrepareRequest, DockingRunRequest

router = APIRouter(prefix="/docking", tags=["docking"])


@router.get("/jobs", response_model=list[DockingJob])
def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    services: AppServices = Depends(get_services),
) -> list[DockingJob]:
    return services.docking_service.list_jobs(limit=limit)


@router.post("/prepare", response_model=DockingJob)
def prepare_docking_inputs(
    request: DockingPrepareRequest,
    services: AppServices = Depends(get_services),
) -> DockingJob:
    try:
        protein = services.protein_service.get(request.protein_id)
        ligand = services.ligand_service.get(request.ligand_id) if request.ligand_id else None
        return services.docking_service.prepare_inputs(protein, ligand, request.parameters)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/run", response_model=DockingJob)
def run_docking(
    request: DockingRunRequest,
    services: AppServices = Depends(get_services),
) -> DockingJob:
    try:
        protein = services.protein_service.get(request.protein_id)
        ligand = services.ligand_service.get(request.ligand_id)
        return services.docking_service.run_docking(protein, ligand, request.parameters)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=DockingJob)
def get_job(
    job_id: str,
    services: AppServices = Depends(get_services),
) -> DockingJob:
    try:
        return services.docking_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs/{job_id}/report")
def download_report(
    job_id: str,
    services: AppServices = Depends(get_services),
) -> FileResponse:
    try:
        job = services.docking_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not job.report_path:
        raise HTTPException(status_code=404, detail="No report has been generated for this job.")
    report_path = Path(job.report_path)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"Report file is missing: {report_path}")
    return FileResponse(path=report_path, filename=f"{job.id}_report.md", media_type="text/markdown")


@router.get("/jobs/{job_id}/poses")
def download_poses(
    job_id: str,
    services: AppServices = Depends(get_services),
) -> FileResponse:
    try:
        job = services.docking_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not job.output_pdbqt:
        raise HTTPException(status_code=404, detail="No output pose file is available for this job.")
    output_path = Path(job.output_pdbqt)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail=f"Pose file is missing: {output_path}")
    return FileResponse(path=output_path, filename=f"{job.id}_poses.pdbqt")

