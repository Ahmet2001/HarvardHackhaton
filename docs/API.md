# Bıdık API

The backend is a FastAPI application. Once running, interactive docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Health

`GET /api/health`

Returns backend status.

## Proteins

`GET /api/proteins/search?query=EGFR`

Searches RCSB PDB by full-text query.

`POST /api/proteins/fetch`

```json
{
  "query": "1CRN"
}
```

Resolves a PDB ID or keyword, downloads the selected PDB file, stores metadata in SQLite, and returns the protein record.

`GET /api/proteins/{protein_id}/download`

Downloads the stored PDB file.

## Ligands

`POST /api/ligands`

```json
{
  "name": "Aspirin control",
  "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
  "input_format": "smiles"
}
```

Stores a SMILES ligand as a `.smi` file.

`GET /api/ligands/search?query=aspirin`

Looks up a public compound by name through PubChem PUG REST and returns candidate SMILES records.

`POST /api/ligands/lookup`

```json
{
  "name": "aspirin"
}
```

Imports the top PubChem hit as the active ligand source record.

`POST /api/ligands/upload`

Multipart file upload for `.mol`, `.mol2`, `.sdf`, `.pdbqt`, `.smi`, or `.smiles`.

## Docking

`POST /api/docking/prepare`

```json
{
  "protein_id": "protein_abc123",
  "ligand_id": "ligand_def456",
  "parameters": {
    "center_x": null,
    "center_y": null,
    "center_z": null,
    "size_x": 22,
    "size_y": 22,
    "size_z": 22,
    "exhaustiveness": 8,
    "num_modes": 9,
    "energy_range": 3,
    "autobox_from_receptor": true
  }
}
```

Prepares the receptor and optional ligand. If Open Babel is missing, the job is marked failed and the error explains how to continue.

`POST /api/docking/run`

Runs the preparation steps and AutoDock Vina. This endpoint never fabricates scores. If `vina` or `obabel` is missing, the returned job has `status: "failed"`.

`GET /api/docking/jobs/{job_id}/report`

Downloads a Markdown report when one exists.

## Agent

`GET /api/agent/status`

Shows whether the Gemini planner is enabled. The endpoint never returns the secret key.

Example response when no key is configured:

```json
{
  "agent_mode": "deterministic_router",
  "gemini": {
    "provider": "gemini",
    "enabled": false,
    "api_key_configured": false,
    "model": "gemini-2.5-flash",
    "fallback": "deterministic_router"
  }
}
```

`POST /api/agent/message`

```json
{
  "session_id": null,
  "message": "Fetch PDB ID 1CRN",
  "ligand_smiles": null,
  "docking_parameters": null
}
```

Returns structured actions, updated session context, and any fetched protein, ligand, or job payloads.

If `GEMINI_API_KEY` is set, the message first goes to the Gemini intent planner. Bıdık then executes the selected local workflow tools itself, so protein retrieval and docking status remain auditable.
