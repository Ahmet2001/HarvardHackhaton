from __future__ import annotations

from pathlib import Path

from app.models.schemas import LigandRecord
from app.services.ligand_service import LigandService


def create_ligand_from_smiles(
    service: LigandService,
    smiles: str,
    name: str | None = None,
) -> LigandRecord:
    return service.create_from_smiles(smiles, name=name)


def prepare_ligand(
    service: LigandService,
    ligand: LigandRecord,
    output_dir: Path,
) -> LigandRecord:
    return service.prepare_ligand(ligand, output_dir)

