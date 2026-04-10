from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ChainInfo(BaseModel):
    chain_id: str
    entity_id: str | None = None
    description: str | None = None
    molecule_type: str | None = None
    organism: str | None = None


class ProteinSearchResult(BaseModel):
    pdb_id: str
    title: str | None = None
    score: float | None = None
    source_url: str


class ProteinMetadata(BaseModel):
    id: str = Field(default_factory=lambda: new_id("protein"))
    pdb_id: str
    query: str | None = None
    name: str
    organism: str | None = None
    experimental_method: str | None = None
    resolution: float | None = None
    chains: list[ChainInfo] = Field(default_factory=list)
    source_url: str
    pdb_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class ProteinFetchRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["1CRN", "EGFR", "P53"])


class ProteinFetchResponse(BaseModel):
    protein: ProteinMetadata
    candidates: list[ProteinSearchResult] = Field(default_factory=list)
    message: str


class LigandCreateRequest(BaseModel):
    name: str | None = Field(default=None, examples=["Imatinib"])
    smiles: str | None = Field(default=None, examples=["CC(=O)OC1=CC=CC=C1C(=O)O"])
    input_format: Literal["smiles"] = "smiles"


class LigandLookupRequest(BaseModel):
    name: str = Field(..., min_length=1, examples=["aspirin", "imatinib", "caffeine"])


class LigandSearchResult(BaseModel):
    cid: int
    name: str
    smiles: str
    molecular_formula: str | None = None
    molecular_weight: str | None = None
    inchikey: str | None = None
    source_url: str


class LigandRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ligand"))
    name: str
    input_format: str
    source_path: str
    smiles: str | None = None
    prepared_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class DockingParameters(BaseModel):
    center_x: float | None = None
    center_y: float | None = None
    center_z: float | None = None
    size_x: float = 22.0
    size_y: float = 22.0
    size_z: float = 22.0
    exhaustiveness: int = Field(default=8, ge=1, le=64)
    num_modes: int = Field(default=9, ge=1, le=50)
    energy_range: float = Field(default=3.0, ge=0.0, le=20.0)
    autobox_from_receptor: bool = True


class DockingRunRequest(BaseModel):
    protein_id: str
    ligand_id: str
    parameters: DockingParameters = Field(default_factory=DockingParameters)


class DockingPrepareRequest(BaseModel):
    protein_id: str
    ligand_id: str | None = None
    parameters: DockingParameters = Field(default_factory=DockingParameters)


class DockingScore(BaseModel):
    mode: int
    affinity_kcal_mol: float
    rmsd_lb: float | None = None
    rmsd_ub: float | None = None


class WorkflowLog(BaseModel):
    step: str
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    message: str
    detail: str | None = None
    created_at: datetime = Field(default_factory=now_utc)


class DockingJob(BaseModel):
    id: str = Field(default_factory=lambda: new_id("dock"))
    protein_id: str
    ligand_id: str | None = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    parameters: DockingParameters = Field(default_factory=DockingParameters)
    scores: list[DockingScore] = Field(default_factory=list)
    output_dir: str
    receptor_pdbqt: str | None = None
    ligand_pdbqt: str | None = None
    output_pdbqt: str | None = None
    report_path: str | None = None
    logs: list[WorkflowLog] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class SessionContext(BaseModel):
    active_protein_id: str | None = None
    active_ligand_id: str | None = None
    last_job_id: str | None = None
    last_candidates: list[ProteinSearchResult] = Field(default_factory=list)


class AgentRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1)
    ligand_smiles: str | None = None
    ligand_name: str | None = None
    docking_parameters: DockingParameters | None = None


class AgentAction(BaseModel):
    tool: str
    status: Literal["completed", "failed", "needs_input", "skipped"]
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    session_id: str
    message: str
    actions: list[AgentAction] = Field(default_factory=list)
    context: SessionContext
    data: dict[str, Any] = Field(default_factory=dict)
