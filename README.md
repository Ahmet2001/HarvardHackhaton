# Bıdık

Bıdık is a production-minded MVP for an AI-agent-powered bioinformatics platform. It retrieves 3D protein structures from RCSB PDB, stores metadata locally, visualizes structures in the browser, prepares receptor and ligand inputs for molecular docking, runs AutoDock Vina when available, and reports workflow results through a structured UI and API.

The project is intentionally honest about scientific execution. If Open Babel or AutoDock Vina is missing, docking jobs fail with actionable errors. The app does not fabricate scores.

## Project Overview

Core workflows:

1. Fetch a protein by PDB ID, gene, protein name, or keyword.
2. Show protein metadata and a 3D NGL Viewer structure.
3. Add a ligand from SMILES or upload MOL, MOL2, SDF, PDBQT, SMI, or SMILES.
4. Prepare receptor and ligand inputs for docking.
5. Run AutoDock Vina with configurable grid parameters.
6. Parse scores, show ranked poses, and export a Markdown report.
7. Use the agent command panel for natural language workflows such as `Fetch PDB ID 1CRN` or `Run docking for this protein`.

## Architecture Decisions

- Backend: Python + FastAPI for typed APIs and generated OpenAPI docs.
- Frontend: React + Vite for a responsive desktop workflow UI.
- Agent orchestration: optional Gemini intent planner plus a deterministic execution router. The Gemini layer interprets natural language when `GEMINI_API_KEY` is configured; the router remains the source of truth for tool execution.
- Protein data: RCSB PDB REST/search APIs and local PDB file storage.
- Ligand data: PubChem PUG REST name lookup for public compound SMILES; manual SMILES and file upload remain supported.
- Visualization: NGL Viewer in the browser.
- Docking: Open Babel for PDBQT conversion and AutoDock Vina for docking execution when installed.
- Storage: SQLite metadata plus local files under `data/` and `jobs/`.
- Reporting: Markdown report per docking job.
- Containerization: Dockerfiles and Compose for backend/frontend services.

## Folder Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── agents/        # Intent detection and task orchestration
│   │   ├── api/           # FastAPI routers
│   │   ├── models/        # Pydantic request/response schemas
│   │   ├── services/      # RCSB, ligand, docking, reporting services
│   │   ├── tools/         # Agent-callable tool wrappers
│   │   ├── utils/         # Command runner, PDB cleanup, Vina parser
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── api.ts
│   │   ├── App.tsx
│   │   └── styles.css
│   └── package.json
├── data/
├── docs/
├── jobs/
├── samples/
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Built By Phase

Phase 1:

- Project scaffold with modular backend/frontend layout.
- FastAPI app, RCSB PDB integration, SQLite storage, protein fetch/search/download endpoints.
- React protein panel with metadata and NGL-based 3D viewer.
- Basic command panel backed by `/api/agent/message`.

Phase 2:

- SMILES and ligand upload support.
- Receptor cleanup, ligand preparation interface, Open Babel PDBQT conversion path.
- AutoDock Vina execution path, score parser, job logs, pose/report file links.
- Docking parameter controls for center, box size, exhaustiveness, modes, and energy range.

Phase 3:

- Session-aware agent context for active protein, ligand, and last job.
- Agent tool wrappers for protein retrieval, ligand creation, docking preparation, docking execution, result parsing, and report hints.
- Markdown reporting and improved UX around loading/error states.

## Setup Instructions

### Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

To enable the LLM-backed agent planner, edit `.env`:

```bash
GEMINI_API_KEY=your_api_key_here
BIDIK_ENABLE_GEMINI_AGENT=true
BIDIK_GEMINI_MODEL=gemini-2.5-flash
```

The real API key must stay in `.env` or your shell environment. It is ignored by git.

Open API docs:

```text
http://localhost:8000/docs
```

### Frontend

Node is required for the frontend.

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

### Docker

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY for the Gemini planner
docker compose up --build
```

The backend is exposed on `http://localhost:8000` and the frontend on `http://localhost:5173`.

## Docking Tool Enablement

For full docking, install:

- Open Babel as `obabel`
- AutoDock Vina as `vina`

Then set paths if needed:

```bash
export BIDIK_OBABEL_BINARY=/path/to/obabel
export BIDIK_VINA_BINARY=/path/to/vina
```

Without these binaries, protein retrieval and ligand storage still work. Preparation and docking jobs return failed statuses with explicit dependency messages.

More detail: [`docs/DOCKING_SETUP.md`](docs/DOCKING_SETUP.md)

## Ligand And Drug Lookup

The MVP now supports PubChem ligand lookup by drug/compound name. In the Ligand panel, search names such as `aspirin`, `imatinib`, or `caffeine`, then choose `Use ligand` to store the retrieved SMILES locally.

DrugBank is not wired as a default public fetch source because DrugBank data/API access normally requires an account/API key and licensing terms. Add it later as an authenticated provider if you have DrugBank credentials and the project license allows that use.

## Example User Interactions

Agent prompts:

```text
Fetch PDB ID 1CRN
Get the 3D structure of EGFR
Prepare this protein for docking
Use SMILES: CC(=O)OC1=CC=CC=C1C(=O)O
Use aspirin as ligand
Dock with imatinib
Run docking for this protein with the current ligand
Show me the best docking score
Summarize the simulation results
Download the PDB file
List candidate ligands
```

API request:

```bash
curl -X POST http://localhost:8000/api/proteins/fetch \
  -H "Content-Type: application/json" \
  -d '{"query":"1CRN"}'
```

Store a ligand:

```bash
curl -X POST http://localhost:8000/api/ligands \
  -H "Content-Type: application/json" \
  -d '{"name":"Aspirin control","smiles":"CC(=O)OC1=CC=CC=C1C(=O)O","input_format":"smiles"}'
```

## Backend Code

Important entry points:

- [`backend/app/main.py`](backend/app/main.py)
- [`backend/app/api/proteins.py`](backend/app/api/proteins.py)
- [`backend/app/api/ligands.py`](backend/app/api/ligands.py)
- [`backend/app/api/docking.py`](backend/app/api/docking.py)
- [`backend/app/api/agent.py`](backend/app/api/agent.py)
- [`backend/app/services/pdb_client.py`](backend/app/services/pdb_client.py)
- [`backend/app/services/docking_service.py`](backend/app/services/docking_service.py)
- [`backend/app/agents/gemini_planner.py`](backend/app/agents/gemini_planner.py)

## Frontend Code

Important entry points:

- [`frontend/src/App.tsx`](frontend/src/App.tsx)
- [`frontend/src/components/ChatPanel.tsx`](frontend/src/components/ChatPanel.tsx)
- [`frontend/src/components/ProteinPanel.tsx`](frontend/src/components/ProteinPanel.tsx)
- [`frontend/src/components/StructureViewer.tsx`](frontend/src/components/StructureViewer.tsx)
- [`frontend/src/components/LigandPanel.tsx`](frontend/src/components/LigandPanel.tsx)
- [`frontend/src/components/DockingPanel.tsx`](frontend/src/components/DockingPanel.tsx)
- [`frontend/src/components/ResultsPanel.tsx`](frontend/src/components/ResultsPanel.tsx)

## AI Agent Logic

The MVP agent lives in [`backend/app/agents/orchestrator.py`](backend/app/agents/orchestrator.py). It provides:

- optional Gemini intent planning through [`backend/app/agents/gemini_planner.py`](backend/app/agents/gemini_planner.py)
- intent detection for fetch, ligand input, preparation, docking, result summary, downloads, and ligand-list requests
- session context for active protein, active ligand, and last job
- tool selection through wrappers in [`backend/app/tools`](backend/app/tools)
- structured action outputs with `completed`, `failed`, or `needs_input` status

When `GEMINI_API_KEY` is missing or the Gemini planner fails, the deterministic router continues to work and reports the fallback through structured agent actions. Check `/api/agent/status` to confirm whether the Gemini planner is enabled.

## Docking Workflow Integration

The docking pipeline lives in [`backend/app/services/docking_service.py`](backend/app/services/docking_service.py):

1. Clean PDB receptor records.
2. Convert receptor to PDBQT with Open Babel.
3. Convert ligand to PDBQT with Open Babel or accept uploaded PDBQT.
4. Estimate a receptor-derived box when coordinates are missing.
5. Run AutoDock Vina.
6. Parse Vina scores.
7. Generate a Markdown report.

## Tests

```bash
PYTHONPATH=backend pytest backend/tests
```

## Limitations And Next Steps

- The agent uses Gemini when configured and falls back to the deterministic router when the key is missing or the model call fails. LangGraph or a richer planner can be added later if the workflows grow.
- Receptor preparation is MVP-level. Add pH/protonation handling, alternate conformer choices, cofactors, metals, and explicit water policies.
- Ligand preparation is MVP-level. Add RDKit standardization, tautomer/protomer enumeration, charge handling, and conformer generation controls.
- Candidate ligand discovery is PubChem name lookup, not target-aware scientific ranking yet. Add ChEMBL/DrugBank providers and target-aware filtering later.
- Docking currently runs synchronously. Add a queue such as Celery/RQ and progress streaming for longer jobs.
- Add authentication, per-user projects, object storage, audit logs, and stronger validation before production use.
