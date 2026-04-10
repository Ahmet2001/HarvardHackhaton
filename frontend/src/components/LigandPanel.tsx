import { ChangeEvent, FormEvent, useState } from "react";
import { API_BASE_URL } from "../api";
import type { LigandRecord, LigandSearchResult } from "../types";

type LigandPanelProps = {
  ligand?: LigandRecord;
  onLigand: (ligand: LigandRecord) => void;
  createLigand: (name: string, smiles: string) => Promise<LigandRecord>;
  searchLigands: (query: string) => Promise<LigandSearchResult[]>;
  lookupLigand: (name: string) => Promise<LigandRecord>;
  uploadLigand: (file: File) => Promise<LigandRecord>;
  onError: (message: string) => void;
};

export function LigandPanel({
  ligand,
  onLigand,
  createLigand,
  searchLigands,
  lookupLigand,
  uploadLigand,
  onError
}: LigandPanelProps) {
  const [name, setName] = useState("");
  const [smiles, setSmiles] = useState("");
  const [lookupName, setLookupName] = useState("");
  const [lookupResults, setLookupResults] = useState<LigandSearchResult[]>([]);
  const [busy, setBusy] = useState(false);

  async function submitSmiles(event: FormEvent) {
    event.preventDefault();
    if (!smiles.trim()) {
      return;
    }
    setBusy(true);
    try {
      const created = await createLigand(name || "SMILES ligand", smiles);
      onLigand(created);
      setName("");
      setSmiles("");
    } catch (error) {
      onError(error instanceof Error ? error.message : "Ligand creation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setBusy(true);
    try {
      const created = await uploadLigand(file);
      onLigand(created);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Ligand upload failed.");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function searchByName(event: FormEvent) {
    event.preventDefault();
    if (!lookupName.trim()) {
      return;
    }
    setBusy(true);
    try {
      const results = await searchLigands(lookupName);
      setLookupResults(results);
      if (!results.length) {
        onError(`No PubChem ligand found for ${lookupName}.`);
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : "Ligand lookup failed.");
    } finally {
      setBusy(false);
    }
  }

  async function importByName(nameToImport: string) {
    setBusy(true);
    try {
      const created = await lookupLigand(nameToImport);
      onLigand(created);
      setName(created.name);
      setSmiles(created.smiles ?? "");
    } catch (error) {
      onError(error instanceof Error ? error.message : "Ligand import failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel ligand-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Ligand</p>
          <h2>Input and preparation</h2>
        </div>
      </div>
      <form className="stack-form" onSubmit={searchByName}>
        <label>
          Drug or ligand name
          <input
            value={lookupName}
            onChange={(event) => setLookupName(event.target.value)}
            placeholder="aspirin, imatinib, caffeine"
          />
        </label>
        <button type="submit" disabled={busy}>
          Search PubChem
        </button>
      </form>
      {lookupResults.length ? (
        <div className="ligand-results">
          {lookupResults.slice(0, 5).map((result) => (
            <div className="ligand-result" key={result.cid}>
              <div>
                <span>PubChem CID {result.cid}</span>
                <strong>{result.name}</strong>
                <p>{result.molecular_formula ?? "Formula not listed"} · {result.molecular_weight ?? "MW not listed"}</p>
                <code>{result.smiles}</code>
              </div>
              <button type="button" disabled={busy} onClick={() => importByName(result.name)}>
                Use ligand
              </button>
            </div>
          ))}
        </div>
      ) : null}
      <form className="stack-form" onSubmit={submitSmiles}>
        <label>
          Ligand name
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Aspirin control" />
        </label>
        <label>
          SMILES
          <textarea
            value={smiles}
            onChange={(event) => setSmiles(event.target.value)}
            placeholder="CC(=O)OC1=CC=CC=C1C(=O)O"
            rows={3}
          />
        </label>
        <button type="submit" disabled={busy}>
          Store SMILES ligand
        </button>
      </form>
      <label className="upload-box">
        Upload MOL, MOL2, SDF, PDBQT, SMI, or SMILES
        <input type="file" onChange={handleUpload} accept=".mol,.mol2,.sdf,.pdbqt,.smi,.smiles" />
      </label>
      {ligand ? (
        <div className="summary-block">
          <span>Active ligand</span>
          <strong>{ligand.name}</strong>
          <p>{ligand.input_format.toUpperCase()}</p>
          {ligand.smiles ? <code>{ligand.smiles}</code> : null}
          <a href={`${API_BASE_URL}/api/ligands/${ligand.id}/download`}>Download ligand file</a>
        </div>
      ) : (
        <p className="empty-state">Add a ligand before running docking.</p>
      )}
    </section>
  );
}
