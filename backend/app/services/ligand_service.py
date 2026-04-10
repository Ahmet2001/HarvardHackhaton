from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import quote

import requests
from requests import JSONDecodeError

from app.config import Settings
from app.database import Database
from app.models.schemas import LigandRecord, LigandSearchResult
from app.utils.command_runner import binary_exists, run_command

logger = logging.getLogger(__name__)

SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


class LigandService:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def create_from_smiles(self, smiles: str, name: str | None = None) -> LigandRecord:
        smiles = smiles.strip()
        if not smiles:
            raise ValueError("SMILES input is empty.")

        ligand_name = name.strip() if name and name.strip() else "SMILES ligand"
        ligand = LigandRecord(
            name=ligand_name,
            input_format="smiles",
            source_path="",
            smiles=smiles,
            metadata={"preparation_status": "not_prepared"},
        )
        source_path = self.settings.ligands_dir / f"{ligand.id}.smi"
        source_path.write_text(f"{smiles}\t{ligand_name}\n", encoding="utf-8")
        ligand.source_path = str(source_path)
        return self.db.create_ligand(ligand)

    def search_pubchem_by_name(self, name: str) -> list[LigandSearchResult]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Ligand name is empty.")

        encoded_name = quote(clean_name, safe="")
        url = (
            f"{self.settings.pubchem_pug_rest_url}/compound/name/{encoded_name}/property/"
            "Title,SMILES,ConnectivitySMILES,MolecularFormula,MolecularWeight,InChIKey/JSON"
        )
        response = requests.get(url, timeout=self.settings.http_timeout_seconds)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.text.strip():
            return []
        try:
            body = response.json()
        except JSONDecodeError as exc:
            raise ValueError("PubChem returned an unreadable ligand response.") from exc

        properties = body.get("PropertyTable", {}).get("Properties", [])
        results: list[LigandSearchResult] = []
        for item in properties:
            smiles = item.get("SMILES") or item.get("ConnectivitySMILES")
            cid = item.get("CID")
            if not smiles or cid is None:
                continue
            title = item.get("Title") or clean_name
            results.append(
                LigandSearchResult(
                    cid=int(cid),
                    name=str(title),
                    smiles=str(smiles),
                    molecular_formula=item.get("MolecularFormula"),
                    molecular_weight=str(item.get("MolecularWeight"))
                    if item.get("MolecularWeight") is not None
                    else None,
                    inchikey=item.get("InChIKey"),
                    source_url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                )
            )
        return results

    def create_from_pubchem_name(self, name: str) -> LigandRecord:
        results = self.search_pubchem_by_name(name)
        if not results:
            raise ValueError(f"No PubChem compound was found for ligand '{name}'.")
        selected = results[0]
        ligand = self.create_from_smiles(selected.smiles, name=selected.name)
        ligand.metadata.update(
            {
                "source_database": "PubChem",
                "pubchem_cid": selected.cid,
                "source_url": selected.source_url,
                "molecular_formula": selected.molecular_formula,
                "molecular_weight": selected.molecular_weight,
                "inchikey": selected.inchikey,
                "lookup_query": name,
            }
        )
        return self.db.update_ligand(ligand)

    def create_from_upload(self, filename: str, content: bytes) -> LigandRecord:
        suffix = Path(filename).suffix.lower().lstrip(".")
        allowed = {"mol", "mol2", "sdf", "pdbqt", "smi", "smiles"}
        if suffix not in allowed:
            raise ValueError(
                f"Unsupported ligand file type '.{suffix}'. Use MOL, MOL2, SDF, PDBQT, SMI, or SMILES."
            )

        safe_stem = SAFE_NAME_PATTERN.sub("_", Path(filename).stem).strip("_") or "ligand"
        ligand = LigandRecord(
            name=safe_stem,
            input_format="smiles" if suffix in {"smi", "smiles"} else suffix,
            source_path="",
            metadata={"preparation_status": "not_prepared", "original_filename": filename},
        )
        source_path = self.settings.ligands_dir / f"{ligand.id}.{suffix}"
        source_path.write_bytes(content)
        ligand.source_path = str(source_path)
        if suffix == "pdbqt":
            ligand.prepared_path = str(source_path)
            ligand.metadata["preparation_status"] = "already_pdbqt"
        return self.db.create_ligand(ligand)

    def get(self, ligand_id: str) -> LigandRecord:
        ligand = self.db.get_ligand(ligand_id)
        if not ligand:
            raise KeyError(f"Ligand '{ligand_id}' was not found.")
        return ligand

    def list_recent(self, limit: int = 20) -> list[LigandRecord]:
        return self.db.list_ligands(limit=limit)

    def prepare_ligand(self, ligand: LigandRecord, output_dir: Path) -> LigandRecord:
        if ligand.prepared_path and Path(ligand.prepared_path).exists():
            return ligand

        if not binary_exists(self.settings.obabel_binary):
            ligand.metadata["preparation_status"] = "failed"
            ligand.metadata["preparation_error"] = (
                "Open Babel is required to convert ligand inputs to PDBQT. "
                "Install 'obabel' or upload a ligand that is already in PDBQT format."
            )
            self.db.update_ligand(ligand)
            raise RuntimeError(ligand.metadata["preparation_error"])

        output_dir.mkdir(parents=True, exist_ok=True)
        prepared_path = output_dir / f"{ligand.id}.pdbqt"
        command = [
            self.settings.obabel_binary,
            ligand.source_path,
            "-O",
            str(prepared_path),
            "--gen3d",
        ]
        logger.info("Preparing ligand %s with Open Babel.", ligand.id)
        result = run_command(
            command,
            cwd=output_dir,
            timeout_seconds=self.settings.command_timeout_seconds,
        )
        if not result.ok or not prepared_path.exists():
            ligand.metadata["preparation_status"] = "failed"
            ligand.metadata["preparation_error"] = result.stderr or result.stdout or "Open Babel failed."
            self.db.update_ligand(ligand)
            raise RuntimeError(ligand.metadata["preparation_error"])

        ligand.prepared_path = str(prepared_path)
        ligand.metadata["preparation_status"] = "prepared"
        ligand.metadata["obabel_stdout"] = result.stdout
        ligand.metadata["obabel_stderr"] = result.stderr
        return self.db.update_ligand(ligand)
