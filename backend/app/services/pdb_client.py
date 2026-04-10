from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import requests
from requests import JSONDecodeError

from app.config import Settings
from app.models.schemas import ChainInfo, ProteinMetadata, ProteinSearchResult

logger = logging.getLogger(__name__)

PDB_ID_PATTERN = re.compile(r"^[0-9][A-Za-z0-9]{3}$")


class RCSBClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def looks_like_pdb_id(query: str) -> bool:
        return bool(PDB_ID_PATTERN.match(query.strip()))

    def search(self, query: str, limit: int = 10) -> list[ProteinSearchResult]:
        payload: dict[str, Any] = {
            "query": {
                "type": "terminal",
                "service": "full_text",
                "parameters": {"value": query},
            },
            "return_type": "entry",
            "request_options": {
                "paginate": {"start": 0, "rows": limit},
                "scoring_strategy": "combined",
            },
        }
        response = requests.post(
            self.settings.rcsb_search_api_url,
            json=payload,
            timeout=self.settings.http_timeout_seconds,
        )
        response.raise_for_status()
        if not response.text.strip():
            return []
        try:
            body = response.json()
        except JSONDecodeError as exc:
            logger.warning(
                "RCSB search returned non-JSON content for query %r: %s",
                query,
                response.text[:200],
            )
            raise ValueError(
                "RCSB PDB search returned an unreadable response. Try a PDB ID or a clearer protein name."
            ) from exc
        candidates: list[ProteinSearchResult] = []
        for result in body.get("result_set", []):
            pdb_id = str(result["identifier"]).upper()
            candidates.append(
                ProteinSearchResult(
                    pdb_id=pdb_id,
                    title=self._entry_title(pdb_id),
                    score=result.get("score"),
                    source_url=f"https://www.rcsb.org/structure/{pdb_id}",
                )
            )
        return candidates

    def resolve_query(self, query: str) -> tuple[str, list[ProteinSearchResult]]:
        clean_query = query.strip()
        if self.looks_like_pdb_id(clean_query):
            pdb_id = clean_query.upper()
            return pdb_id, [
                ProteinSearchResult(
                    pdb_id=pdb_id,
                    title=self._entry_title(pdb_id),
                    source_url=f"https://www.rcsb.org/structure/{pdb_id}",
                )
            ]

        candidates = self.search(clean_query, limit=8)
        if not candidates:
            raise ValueError(f"No RCSB PDB entries were found for '{query}'.")
        return candidates[0].pdb_id, candidates

    def fetch_metadata(self, pdb_id: str, query: str | None, pdb_path: Path) -> ProteinMetadata:
        entry = self._get_json(f"{self.settings.rcsb_data_api_url}/entry/{pdb_id}")
        chain_infos = self._fetch_chain_info(pdb_id, entry)
        resolution_values = entry.get("rcsb_entry_info", {}).get("resolution_combined") or []
        resolution = None
        for value in resolution_values:
            if value is None:
                continue
            try:
                resolution = float(value)
                break
            except (TypeError, ValueError):
                continue
        method = None
        if entry.get("exptl"):
            method = entry["exptl"][0].get("method")

        organism = next((chain.organism for chain in chain_infos if chain.organism), None)
        title = entry.get("struct", {}).get("title") or f"PDB {pdb_id}"
        return ProteinMetadata(
            pdb_id=pdb_id.upper(),
            query=query,
            name=title,
            organism=organism,
            experimental_method=method,
            resolution=resolution,
            chains=chain_infos,
            source_url=f"https://www.rcsb.org/structure/{pdb_id.upper()}",
            pdb_path=str(pdb_path),
            metadata={
                "deposition_date": entry.get("rcsb_accession_info", {}).get("deposit_date"),
                "revision_date": entry.get("rcsb_accession_info", {}).get("revision_date"),
                "entity_ids": entry.get("rcsb_entry_container_identifiers", {}).get(
                    "polymer_entity_ids", []
                ),
            },
        )

    def download_pdb(self, pdb_id: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        url = f"{self.settings.pdb_download_base_url}/{pdb_id.upper()}.pdb"
        response = requests.get(url, timeout=self.settings.http_timeout_seconds)
        response.raise_for_status()
        if not response.text.startswith(("HEADER", "TITLE", "ATOM", "REMARK")):
            logger.warning("Downloaded PDB %s did not start with a typical PDB record.", pdb_id)
        destination.write_text(response.text, encoding="utf-8")
        return destination

    def _entry_title(self, pdb_id: str) -> str | None:
        try:
            entry = self._get_json(f"{self.settings.rcsb_data_api_url}/entry/{pdb_id}")
            return entry.get("struct", {}).get("title")
        except requests.RequestException:
            logger.info("Could not enrich PDB search result %s with title.", pdb_id)
            return None

    def _fetch_chain_info(self, pdb_id: str, entry: dict[str, Any]) -> list[ChainInfo]:
        entity_ids = entry.get("rcsb_entry_container_identifiers", {}).get("polymer_entity_ids", [])
        chains: list[ChainInfo] = []
        for entity_id in entity_ids:
            try:
                entity = self._get_json(
                    f"{self.settings.rcsb_data_api_url}/polymer_entity/{pdb_id}/{entity_id}"
                )
            except requests.RequestException as exc:
                logger.warning("Failed to fetch entity metadata for %s entity %s: %s", pdb_id, entity_id, exc)
                continue

            identifiers = entity.get("rcsb_polymer_entity_container_identifiers", {})
            chain_ids = identifiers.get("auth_asym_ids") or identifiers.get("asym_ids") or []
            description = entity.get("rcsb_polymer_entity", {}).get("pdbx_description")
            molecule_type = entity.get("entity_poly", {}).get("rcsb_entity_polymer_type")
            organism = None
            source_organisms = entity.get("rcsb_entity_source_organism") or []
            if source_organisms:
                organism = source_organisms[0].get("scientific_name")

            for chain_id in chain_ids:
                chains.append(
                    ChainInfo(
                        chain_id=str(chain_id),
                        entity_id=str(entity_id),
                        description=description,
                        molecule_type=molecule_type,
                        organism=organism,
                    )
                )

        return chains

    def _get_json(self, url: str) -> dict[str, Any]:
        response = requests.get(url, timeout=self.settings.http_timeout_seconds)
        response.raise_for_status()
        return response.json()
