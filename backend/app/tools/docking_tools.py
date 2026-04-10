from __future__ import annotations

from app.models.schemas import DockingJob, DockingParameters, LigandRecord, ProteinMetadata
from app.services.docking_service import DockingService


def prepare_inputs_for_docking(
    service: DockingService,
    protein: ProteinMetadata,
    ligand: LigandRecord | None = None,
    parameters: DockingParameters | None = None,
) -> DockingJob:
    return service.prepare_inputs(protein, ligand, parameters)


def run_docking(
    service: DockingService,
    protein: ProteinMetadata,
    ligand: LigandRecord,
    parameters: DockingParameters | None = None,
) -> DockingJob:
    return service.run_docking(protein, ligand, parameters)


def parse_docking_results(job: DockingJob) -> dict[str, object]:
    best = min(job.scores, key=lambda score: score.affinity_kcal_mol) if job.scores else None
    return {
        "status": job.status,
        "best_score": best.model_dump(mode="json") if best else None,
        "scores": [score.model_dump(mode="json") for score in job.scores],
        "output_pdbqt": job.output_pdbqt,
        "report_path": job.report_path,
        "error": job.error,
    }

