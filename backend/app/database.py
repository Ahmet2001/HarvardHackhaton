from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.schemas import (
    DockingJob,
    LigandRecord,
    ProteinMetadata,
    SessionContext,
)


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _dumps(value: Any) -> str:
    return json.dumps(value, default=_json_default)


def _loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_schema(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS proteins (
                    id TEXT PRIMARY KEY,
                    pdb_id TEXT NOT NULL,
                    query TEXT,
                    name TEXT NOT NULL,
                    organism TEXT,
                    experimental_method TEXT,
                    resolution REAL,
                    chains_json TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    pdb_path TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ligands (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    input_format TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    smiles TEXT,
                    prepared_path TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS docking_jobs (
                    id TEXT PRIMARY KEY,
                    protein_id TEXT NOT NULL,
                    ligand_id TEXT,
                    status TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    scores_json TEXT NOT NULL,
                    output_dir TEXT NOT NULL,
                    receptor_pdbqt TEXT,
                    ligand_pdbqt TEXT,
                    output_pdbqt TEXT,
                    report_path TEXT,
                    logs_json TEXT NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    context_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def upsert_protein(self, protein: ProteinMetadata) -> ProteinMetadata:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO proteins (
                    id, pdb_id, query, name, organism, experimental_method, resolution,
                    chains_json, source_url, pdb_path, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    query = excluded.query,
                    name = excluded.name,
                    organism = excluded.organism,
                    experimental_method = excluded.experimental_method,
                    resolution = excluded.resolution,
                    chains_json = excluded.chains_json,
                    source_url = excluded.source_url,
                    pdb_path = excluded.pdb_path,
                    metadata_json = excluded.metadata_json
                """,
                (
                    protein.id,
                    protein.pdb_id,
                    protein.query,
                    protein.name,
                    protein.organism,
                    protein.experimental_method,
                    protein.resolution,
                    _dumps([chain.model_dump(mode="json") for chain in protein.chains]),
                    protein.source_url,
                    protein.pdb_path,
                    _dumps(protein.metadata),
                    protein.created_at.isoformat(),
                ),
            )
        return protein

    def get_protein(self, protein_id: str) -> ProteinMetadata | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM proteins WHERE id = ?", (protein_id,)).fetchone()
        return self._row_to_protein(row) if row else None

    def find_protein_by_pdb_id(self, pdb_id: str) -> ProteinMetadata | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM proteins WHERE pdb_id = ? ORDER BY created_at DESC LIMIT 1",
                (pdb_id.upper(),),
            ).fetchone()
        return self._row_to_protein(row) if row else None

    def list_proteins(self, limit: int = 20) -> list[ProteinMetadata]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM proteins ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_protein(row) for row in rows]

    def create_ligand(self, ligand: LigandRecord) -> LigandRecord:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO ligands (
                    id, name, input_format, source_path, smiles, prepared_path,
                    metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ligand.id,
                    ligand.name,
                    ligand.input_format,
                    ligand.source_path,
                    ligand.smiles,
                    ligand.prepared_path,
                    _dumps(ligand.metadata),
                    ligand.created_at.isoformat(),
                ),
            )
        return ligand

    def update_ligand(self, ligand: LigandRecord) -> LigandRecord:
        with self.connect() as db:
            db.execute(
                """
                UPDATE ligands
                SET name = ?, input_format = ?, source_path = ?, smiles = ?,
                    prepared_path = ?, metadata_json = ?
                WHERE id = ?
                """,
                (
                    ligand.name,
                    ligand.input_format,
                    ligand.source_path,
                    ligand.smiles,
                    ligand.prepared_path,
                    _dumps(ligand.metadata),
                    ligand.id,
                ),
            )
        return ligand

    def get_ligand(self, ligand_id: str) -> LigandRecord | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM ligands WHERE id = ?", (ligand_id,)).fetchone()
        return self._row_to_ligand(row) if row else None

    def list_ligands(self, limit: int = 20) -> list[LigandRecord]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM ligands ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_ligand(row) for row in rows]

    def upsert_job(self, job: DockingJob) -> DockingJob:
        job.updated_at = datetime.now(timezone.utc)
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO docking_jobs (
                    id, protein_id, ligand_id, status, parameters_json, scores_json,
                    output_dir, receptor_pdbqt, ligand_pdbqt, output_pdbqt,
                    report_path, logs_json, error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    parameters_json = excluded.parameters_json,
                    scores_json = excluded.scores_json,
                    receptor_pdbqt = excluded.receptor_pdbqt,
                    ligand_pdbqt = excluded.ligand_pdbqt,
                    output_pdbqt = excluded.output_pdbqt,
                    report_path = excluded.report_path,
                    logs_json = excluded.logs_json,
                    error = excluded.error,
                    updated_at = excluded.updated_at
                """,
                (
                    job.id,
                    job.protein_id,
                    job.ligand_id,
                    job.status,
                    job.parameters.model_dump_json(),
                    _dumps([score.model_dump(mode="json") for score in job.scores]),
                    job.output_dir,
                    job.receptor_pdbqt,
                    job.ligand_pdbqt,
                    job.output_pdbqt,
                    job.report_path,
                    _dumps([entry.model_dump(mode="json") for entry in job.logs]),
                    job.error,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                ),
            )
        return job

    def get_job(self, job_id: str) -> DockingJob | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM docking_jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(self, limit: int = 20) -> list[DockingJob]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM docking_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def get_or_create_session(self, session_id: str) -> SessionContext:
        with self.connect() as db:
            row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row:
                return SessionContext.model_validate_json(row["context_json"])
            now = _now()
            context = SessionContext()
            db.execute(
                "INSERT INTO sessions (id, context_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, context.model_dump_json(), now, now),
            )
        return context

    def save_session(self, session_id: str, context: SessionContext) -> None:
        now = _now()
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO sessions (id, context_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    context_json = excluded.context_json,
                    updated_at = excluded.updated_at
                """,
                (session_id, context.model_dump_json(), now, now),
            )

    def _row_to_protein(self, row: sqlite3.Row) -> ProteinMetadata:
        return ProteinMetadata(
            id=row["id"],
            pdb_id=row["pdb_id"],
            query=row["query"],
            name=row["name"],
            organism=row["organism"],
            experimental_method=row["experimental_method"],
            resolution=row["resolution"],
            chains=_loads(row["chains_json"], []),
            source_url=row["source_url"],
            pdb_path=row["pdb_path"],
            metadata=_loads(row["metadata_json"], {}),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_ligand(self, row: sqlite3.Row) -> LigandRecord:
        return LigandRecord(
            id=row["id"],
            name=row["name"],
            input_format=row["input_format"],
            source_path=row["source_path"],
            smiles=row["smiles"],
            prepared_path=row["prepared_path"],
            metadata=_loads(row["metadata_json"], {}),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_job(self, row: sqlite3.Row) -> DockingJob:
        return DockingJob(
            id=row["id"],
            protein_id=row["protein_id"],
            ligand_id=row["ligand_id"],
            status=row["status"],
            parameters=_loads(row["parameters_json"], {}),
            scores=_loads(row["scores_json"], []),
            output_dir=row["output_dir"],
            receptor_pdbqt=row["receptor_pdbqt"],
            ligand_pdbqt=row["ligand_pdbqt"],
            output_pdbqt=row["output_pdbqt"],
            report_path=row["report_path"],
            logs=_loads(row["logs_json"], []),
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
