from __future__ import annotations

from app.models.schemas import ProteinMetadata


def visualize_structure(protein: ProteinMetadata) -> dict[str, str]:
    return {
        "viewer": "NGL Viewer",
        "structure_url": f"/api/proteins/{protein.id}/download",
        "message": "Load this PDB URL in the frontend structure viewer.",
    }

