from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.orchestrator import AgentOrchestrator
from app.agents.gemini_planner import GeminiIntentPlanner
from app.api import agent, docking, health, ligands, proteins
from app.api.deps import AppServices
from app.config import get_settings
from app.database import Database
from app.logging_config import configure_logging
from app.services.docking_service import DockingService
from app.services.ligand_service import LigandService
from app.services.pdb_client import RCSBClient
from app.services.protein_service import ProteinService
from app.services.report_service import ReportService


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    db = Database(settings.database_path)
    pdb_client = RCSBClient(settings)
    protein_service = ProteinService(db, pdb_client, settings.proteins_dir)
    ligand_service = LigandService(db, settings)
    report_service = ReportService(db)
    docking_service = DockingService(db, ligand_service, report_service, settings)
    gemini_planner = GeminiIntentPlanner(settings)
    agent_orchestrator = AgentOrchestrator(
        db,
        protein_service,
        ligand_service,
        docking_service,
        llm_planner=gemini_planner,
    )

    app = FastAPI(
        title="BioDockX API",
        version="0.1.0",
        description=(
            "AI-agent-powered bioinformatics MVP for protein retrieval, docking preparation, "
            "AutoDock Vina execution, and structured result reporting."
        ),
    )
    app.state.services = AppServices(
        protein_service=protein_service,
        ligand_service=ligand_service,
        docking_service=docking_service,
        report_service=report_service,
        agent=agent_orchestrator,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(proteins.router, prefix="/api")
    app.include_router(ligands.router, prefix="/api")
    app.include_router(docking.router, prefix="/api")
    app.include_router(agent.router, prefix="/api")
    return app


app = create_app()
