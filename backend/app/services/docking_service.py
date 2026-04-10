from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings
from app.database import Database
from app.models.schemas import (
    DockingJob,
    DockingParameters,
    LigandRecord,
    ProteinMetadata,
    WorkflowLog,
)
from app.services.ligand_service import LigandService
from app.services.report_service import ReportService
from app.utils.command_runner import binary_exists, run_command
from app.utils.pdb import clean_pdb_for_docking, estimate_binding_box_from_pdb
from app.utils.vina import parse_vina_log

logger = logging.getLogger(__name__)


class DockingService:
    def __init__(
        self,
        db: Database,
        ligand_service: LigandService,
        report_service: ReportService,
        settings: Settings,
    ) -> None:
        self.db = db
        self.ligand_service = ligand_service
        self.report_service = report_service
        self.settings = settings

    def prepare_inputs(
        self,
        protein: ProteinMetadata,
        ligand: LigandRecord | None = None,
        parameters: DockingParameters | None = None,
    ) -> DockingJob:
        job = DockingJob(
            protein_id=protein.id,
            ligand_id=ligand.id if ligand else None,
            status="running",
            parameters=parameters or DockingParameters(),
            output_dir=str(
                self.settings.jobs_dir / f"prepare_{protein.pdb_id}_{ligand.id if ligand else 'receptor'}"
            ),
        )
        self.db.upsert_job(job)
        try:
            self._prepare_receptor(job, protein)
            if ligand:
                self._prepare_ligand(job, ligand)
            self._apply_binding_box(job, protein)
            job.status = "completed"
            message = (
                "Protein and ligand inputs are ready for docking."
                if ligand
                else "Protein receptor input is ready for docking."
            )
            self._log(job, "prepare_inputs", "completed", message)
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            self._log(job, "prepare_inputs", "failed", str(exc))
        self.db.upsert_job(job)
        return job

    def run_docking(
        self,
        protein: ProteinMetadata,
        ligand: LigandRecord,
        parameters: DockingParameters | None = None,
    ) -> DockingJob:
        job = DockingJob(
            protein_id=protein.id,
            ligand_id=ligand.id,
            status="running",
            parameters=parameters or DockingParameters(),
            output_dir=str(self.settings.jobs_dir / f"{protein.pdb_id}_{ligand.id}"),
        )
        self.db.upsert_job(job)
        try:
            self._prepare_receptor(job, protein)
            ligand = self._prepare_ligand(job, ligand)
            self._apply_binding_box(job, protein)
            self._run_vina(job)
            job.status = "completed"
            self._log(job, "run_docking", "completed", "Docking completed and Vina output was parsed.")
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            self._log(job, "run_docking", "failed", str(exc))

        protein_record = self.db.get_protein(job.protein_id)
        ligand_record = self.db.get_ligand(job.ligand_id)
        if protein_record and ligand_record:
            self.report_service.generate_markdown_report(job, protein_record, ligand_record)
        self.db.upsert_job(job)
        return job

    def get_job(self, job_id: str) -> DockingJob:
        job = self.db.get_job(job_id)
        if not job:
            raise KeyError(f"Docking job '{job_id}' was not found.")
        return job

    def list_jobs(self, limit: int = 20) -> list[DockingJob]:
        return self.db.list_jobs(limit=limit)

    def _prepare_receptor(self, job: DockingJob, protein: ProteinMetadata) -> None:
        output_dir = Path(job.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        source_pdb = Path(protein.pdb_path)
        if not source_pdb.exists():
            raise FileNotFoundError(f"Protein PDB file is missing: {source_pdb}")

        cleaned_pdb = output_dir / "receptor_clean.pdb"
        atoms = clean_pdb_for_docking(source_pdb, cleaned_pdb)
        if atoms == 0:
            raise RuntimeError("No receptor atoms remained after PDB cleanup.")
        self._log(job, "protein_cleanup", "completed", f"Cleaned receptor PDB with {atoms} ATOM records.")

        receptor_pdbqt = output_dir / "receptor.pdbqt"
        if not binary_exists(self.settings.obabel_binary):
            raise RuntimeError(
                "Open Babel is required to convert the receptor PDB to PDBQT. "
                "Install 'obabel' or provide a prepared receptor PDBQT in a future workflow."
            )

        result = run_command(
            [self.settings.obabel_binary, str(cleaned_pdb), "-O", str(receptor_pdbqt), "-xr"],
            cwd=output_dir,
            timeout_seconds=self.settings.command_timeout_seconds,
        )
        if not result.ok or not receptor_pdbqt.exists():
            raise RuntimeError(result.stderr or result.stdout or "Open Babel receptor conversion failed.")
        job.receptor_pdbqt = str(receptor_pdbqt)
        self._log(job, "protein_pdbqt", "completed", "Converted cleaned receptor to PDBQT with Open Babel.")
        self.db.upsert_job(job)

    def _prepare_ligand(self, job: DockingJob, ligand: LigandRecord) -> LigandRecord:
        prepared = self.ligand_service.prepare_ligand(ligand, Path(job.output_dir))
        job.ligand_pdbqt = prepared.prepared_path
        self._log(job, "ligand_pdbqt", "completed", "Prepared ligand PDBQT input.")
        self.db.upsert_job(job)
        return prepared

    def _apply_binding_box(self, job: DockingJob, protein: ProteinMetadata) -> None:
        params = job.parameters
        missing_center = params.center_x is None or params.center_y is None or params.center_z is None
        if missing_center and params.autobox_from_receptor:
            box = estimate_binding_box_from_pdb(Path(protein.pdb_path))
            params.center_x = box["center_x"]
            params.center_y = box["center_y"]
            params.center_z = box["center_z"]
            params.size_x = box["size_x"]
            params.size_y = box["size_y"]
            params.size_z = box["size_z"]
            self._log(
                job,
                "binding_box",
                "completed",
                "Estimated a docking box from receptor coordinates. Specify binding-site coordinates for real studies.",
            )
        elif missing_center:
            raise ValueError("Docking center coordinates are required when autobox_from_receptor is disabled.")
        else:
            self._log(job, "binding_box", "completed", "Using user-provided docking box parameters.")
        self.db.upsert_job(job)

    def _run_vina(self, job: DockingJob) -> None:
        if not binary_exists(self.settings.vina_binary):
            raise RuntimeError(
                "AutoDock Vina is not installed or not on PATH. Install Vina and set BIDIK_VINA_BINARY "
                "if the executable has a custom location."
            )
        if not job.receptor_pdbqt or not job.ligand_pdbqt:
            raise RuntimeError("Prepared receptor and ligand PDBQT files are required before running Vina.")

        output_dir = Path(job.output_dir)
        output_pdbqt = output_dir / "poses.pdbqt"
        log_path = output_dir / "vina.log"
        params = job.parameters
        command = [
            self.settings.vina_binary,
            "--receptor",
            job.receptor_pdbqt,
            "--ligand",
            job.ligand_pdbqt,
            "--center_x",
            str(params.center_x),
            "--center_y",
            str(params.center_y),
            "--center_z",
            str(params.center_z),
            "--size_x",
            str(params.size_x),
            "--size_y",
            str(params.size_y),
            "--size_z",
            str(params.size_z),
            "--exhaustiveness",
            str(params.exhaustiveness),
            "--num_modes",
            str(params.num_modes),
            "--energy_range",
            str(params.energy_range),
            "--out",
            str(output_pdbqt),
        ]
        self._log(job, "vina", "running", "Starting AutoDock Vina.")
        result = run_command(
            command,
            cwd=output_dir,
            timeout_seconds=self.settings.command_timeout_seconds,
        )
        log_path.write_text(
            "\n".join(
                [
                    "$ " + " ".join(command),
                    "",
                    result.stdout,
                    result.stderr,
                ]
            ),
            encoding="utf-8",
        )
        if not result.ok:
            raise RuntimeError(result.stderr or result.stdout or "AutoDock Vina failed.")

        job.output_pdbqt = str(output_pdbqt)
        job.scores = parse_vina_log(log_path)
        if not job.scores:
            raise RuntimeError("Vina completed, but no docking scores were parsed from the log.")
        self._log(job, "vina", "completed", f"Parsed {len(job.scores)} docking score(s).")
        self.db.upsert_job(job)

    def _log(self, job: DockingJob, step: str, status: str, message: str, detail: str | None = None) -> None:
        job.logs.append(
            WorkflowLog(
                step=step,
                status=status,  # type: ignore[arg-type]
                message=message,
                detail=detail,
            )
        )
        logger.info("%s [%s]: %s", step, status, message)
