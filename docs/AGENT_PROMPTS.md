# Example Agent Prompts

- `Fetch PDB ID 1CRN`
- `Get the 3D structure of EGFR`
- `Fetch the structure of P53`
- `Download the PDB file`
- `Prepare this protein for docking`
- `Use aspirin as ligand`
- `Dock with imatinib`
- `Use SMILES: CC(=O)OC1=CC=CC=C1C(=O)O`
- `Run docking for this protein with the current ligand`
- `Show docking results`
- `Show me the best docking score`
- `Summarize the simulation results in simple language`
- `List candidate ligands`

If `GEMINI_API_KEY` is configured, BioDockX uses Gemini first to produce a structured workflow plan, then executes local tools through the deterministic router. If the key is missing or the planner fails, the router still maps these requests to tool calls and returns tool names and statuses in every agent response.

Check planner status:

```bash
curl http://localhost:8000/api/agent/status
```
