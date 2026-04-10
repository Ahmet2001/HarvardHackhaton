from __future__ import annotations

from pathlib import Path

from app.models.schemas import DockingJob, LigandRecord, ProteinMetadata
from app.services.report_service import ReportService


def generate_report(
    service: ReportService,
    job: DockingJob,
    protein: ProteinMetadata,
    ligand: LigandRecord,
) -> Path:
    return service.generate_markdown_report(job, protein, ligand)

