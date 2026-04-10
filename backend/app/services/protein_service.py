from __future__ import annotations

import logging
from pathlib import Path

from app.database import Database
from app.models.schemas import ProteinFetchResponse, ProteinMetadata, ProteinSearchResult
from app.services.pdb_client import RCSBClient

logger = logging.getLogger(__name__)


class ProteinService:
    def __init__(self, db: Database, pdb_client: RCSBClient, proteins_dir: Path) -> None:
        self.db = db
        self.pdb_client = pdb_client
        self.proteins_dir = proteins_dir

    def search(self, query: str, limit: int = 10) -> list[ProteinSearchResult]:
        return self.pdb_client.search(query, limit=limit)

    def fetch(self, query: str) -> ProteinFetchResponse:
        pdb_id, candidates = self.pdb_client.resolve_query(query)
        existing = self.db.find_protein_by_pdb_id(pdb_id)
        if existing and Path(existing.pdb_path).exists():
            return ProteinFetchResponse(
                protein=existing,
                candidates=candidates,
                message=f"Using cached PDB structure {pdb_id}.",
            )

        pdb_path = self.proteins_dir / f"{pdb_id}.pdb"
        logger.info("Downloading PDB structure %s to %s", pdb_id, pdb_path)
        self.pdb_client.download_pdb(pdb_id, pdb_path)
        protein = self.pdb_client.fetch_metadata(pdb_id, query=query, pdb_path=pdb_path)
        self.db.upsert_protein(protein)
        return ProteinFetchResponse(
            protein=protein,
            candidates=candidates,
            message=f"Downloaded PDB structure {pdb_id}.",
        )

    def get(self, protein_id: str) -> ProteinMetadata:
        protein = self.db.get_protein(protein_id)
        if not protein:
            raise KeyError(f"Protein '{protein_id}' was not found.")
        return protein

    def list_recent(self, limit: int = 20) -> list[ProteinMetadata]:
        return self.db.list_proteins(limit=limit)

