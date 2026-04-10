from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.agents.orchestrator import AgentOrchestrator
from app.services.docking_service import DockingService
from app.services.ligand_service import LigandService
from app.services.protein_service import ProteinService
from app.services.report_service import ReportService


@dataclass(frozen=True)
class AppServices:
    protein_service: ProteinService
    ligand_service: LigandService
    docking_service: DockingService
    report_service: ReportService
    agent: AgentOrchestrator


def get_services(request: Request) -> AppServices:
    return request.app.state.services

