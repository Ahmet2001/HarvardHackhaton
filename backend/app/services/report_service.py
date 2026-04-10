from __future__ import annotations

from pathlib import Path

from app.database import Database
from app.models.schemas import DockingJob, LigandRecord, ProteinMetadata


class ReportService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def generate_markdown_report(
        self,
        job: DockingJob,
        protein: ProteinMetadata,
        ligand: LigandRecord,
    ) -> Path:
        output_dir = Path(job.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "report.md"
        best_score = min((score.affinity_kcal_mol for score in job.scores), default=None)
        score_rows = "\n".join(
            f"| {score.mode} | {score.affinity_kcal_mol} | {score.rmsd_lb} | {score.rmsd_ub} |"
            for score in job.scores
        )
        if not score_rows:
            score_rows = "| - | - | - | - |"

        interpretation = (
            f"The best parsed Vina score was {best_score} kcal/mol. More negative scores are "
            "typically stronger predicted binding in Vina, but docking scores are approximate and "
            "must be interpreted with controls, visual inspection, and experimental context."
            if best_score is not None
            else "No docking scores were parsed. Review the workflow logs and external tool setup."
        )

        logs = "\n".join(
            f"- **{entry.step}** [{entry.status}]: {entry.message}"
            for entry in job.logs
        )
        report_path.write_text(
            f"""# Bıdık Docking Report

## Protein
- Name: {protein.name}
- PDB ID: {protein.pdb_id}
- Organism: {protein.organism or "Unknown"}
- Method: {protein.experimental_method or "Unknown"}
- Resolution: {protein.resolution or "Not available"}
- Source: {protein.source_url}

## Ligand
- Name: {ligand.name}
- Format: {ligand.input_format}
- Source file: {ligand.source_path}

## Docking Parameters
- Center: ({job.parameters.center_x}, {job.parameters.center_y}, {job.parameters.center_z})
- Box size: ({job.parameters.size_x}, {job.parameters.size_y}, {job.parameters.size_z})
- Exhaustiveness: {job.parameters.exhaustiveness}
- Number of modes: {job.parameters.num_modes}
- Energy range: {job.parameters.energy_range}

## Scores
| Mode | Affinity kcal/mol | RMSD lower | RMSD upper |
| --- | ---: | ---: | ---: |
{score_rows}

## Interpretation
{interpretation}

## Files
- Output directory: {job.output_dir}
- Receptor PDBQT: {job.receptor_pdbqt or "Not generated"}
- Ligand PDBQT: {job.ligand_pdbqt or "Not generated"}
- Output poses: {job.output_pdbqt or "Not generated"}

## Workflow Log
{logs or "- No log entries recorded."}

## Status
{job.status}

{f"Error: {job.error}" if job.error else ""}
""",
            encoding="utf-8",
        )
        job.report_path = str(report_path)
        self.db.upsert_job(job)
        return report_path

