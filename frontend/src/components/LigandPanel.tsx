import { ChangeEvent, FormEvent, useState } from "react";
import { API_BASE_URL } from "../api";
import type { LigandRecord, LigandSearchResult } from "../types";
import { FieldHint } from "./FieldHint";
import { InlineNotice } from "./InlineNotice";
import { LoadingButton } from "./LoadingButton";

type LigandPanelProps = {
  ligand?: LigandRecord;
  onLigand: (ligand: LigandRecord) => void;
  createLigand: (name: string, smiles: string) => Promise<LigandRecord>;
  searchLigands: (query: string) => Promise<LigandSearchResult[]>;
  lookupLigand: (name: string) => Promise<LigandRecord>;
  uploadLigand: (file: File) => Promise<LigandRecord>;
  onError: (message: string) => void;
};

type BusyAction = "search" | "store" | "upload" | "import" | null;

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
  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const [importingCid, setImportingCid] = useState<number | null>(null);

  const busy = busyAction !== null;

  async function submitSmiles(event: FormEvent) {
    event.preventDefault();
    if (!smiles.trim()) {
      return;
    }
    setBusyAction("store");
    try {
      const created = await createLigand(name || "SMILES ligand", smiles);
      onLigand(created);
      setName("");
      setSmiles("");
    } catch (error) {
      onError(error instanceof Error ? error.message : "Ligand creation failed.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setBusyAction("upload");
    try {
      const created = await uploadLigand(file);
      onLigand(created);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Ligand upload failed.");
    } finally {
      setBusyAction(null);
      event.target.value = "";
    }
  }

  async function searchByName(event: FormEvent) {
    event.preventDefault();
    if (!lookupName.trim()) {
      return;
    }
    setBusyAction("search");
    try {
      const results = await searchLigands(lookupName);
      setLookupResults(results);
      if (!results.length) {
        onError(`No PubChem ligand found for ${lookupName}.`);
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : "Ligand lookup failed.");
    } finally {
      setBusyAction(null);
    }
  }

  async function importByName(nameToImport: string, cid: number) {
    setBusyAction("import");
    setImportingCid(cid);
    try {
      const created = await lookupLigand(nameToImport);
      onLigand(created);
      setName(created.name);
      setSmiles(created.smiles ?? "");
    } catch (error) {
      onError(error instanceof Error ? error.message : "Ligand import failed.");
    } finally {
      setBusyAction(null);
      setImportingCid(null);
    }
  }

  const canSearch = lookupName.trim().length > 0 && !busy;
  const canStoreSmiles = smiles.trim().length > 0 && !busy;

  return (
    <section aria-labelledby="ligand-panel-title" className="panel ligand-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Ligand</p>
          <h2 id="ligand-panel-title">Input and preparation</h2>
        </div>
      </div>
      <form className="stack-form" onSubmit={searchByName}>
        <label htmlFor="ligand-lookup">
          Drug or ligand name
          <input
            aria-describedby="ligand-lookup-help"
            autoComplete="off"
            id="ligand-lookup"
            value={lookupName}
            onChange={(event) => setLookupName(event.target.value)}
            placeholder="aspirin, imatinib, caffeine"
          />
        </label>
        <FieldHint id="ligand-lookup-help">Search PubChem, review the candidates, then import the intended ligand for docking.</FieldHint>
        <LoadingButton type="submit" busy={busyAction === "search"} busyLabel="Searching PubChem" disabled={!canSearch}>
          Search PubChem
        </LoadingButton>
      </form>
      {lookupResults.length ? (
        <ul aria-label="PubChem ligand search results" className="ligand-results">
          {lookupResults.slice(0, 5).map((result) => (
            <li className="ligand-result" key={result.cid}>
              <div>
                <span>PubChem CID {result.cid}</span>
                <strong>{result.name}</strong>
                <p>{result.molecular_formula ?? "Formula not listed"} · {result.molecular_weight ?? "MW not listed"}</p>
                <code>{result.smiles}</code>
                <a href={result.source_url} rel="noreferrer" target="_blank">
                  View PubChem record
                </a>
              </div>
              <LoadingButton
                aria-label={`Use ${result.name} as the active ligand`}
                type="button"
                busy={importingCid === result.cid}
                busyLabel="Importing ligand"
                disabled={busy}
                onClick={() => importByName(result.name, result.cid)}
              >
                Use ligand
              </LoadingButton>
            </li>
          ))}
        </ul>
      ) : null}
      <form className="stack-form" onSubmit={submitSmiles}>
        <label htmlFor="ligand-name">
          Ligand name
          <input id="ligand-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Aspirin control" />
        </label>
        <label htmlFor="ligand-smiles">
          SMILES
          <textarea
            aria-describedby="ligand-smiles-help"
            id="ligand-smiles"
            value={smiles}
            onChange={(event) => setSmiles(event.target.value)}
            placeholder="CC(=O)OC1=CC=CC=C1C(=O)O"
            rows={3}
          />
        </label>
        <FieldHint id="ligand-smiles-help">Use canonical or isomeric SMILES. File uploads are still available for MOL, MOL2, SDF, PDBQT, SMI, or SMILES.</FieldHint>
        <LoadingButton type="submit" busy={busyAction === "store"} busyLabel="Storing ligand" disabled={!canStoreSmiles}>
          Store SMILES ligand
        </LoadingButton>
      </form>
      <label aria-busy={busyAction === "upload"} className="upload-box" htmlFor="ligand-upload">
        <span>{busyAction === "upload" ? "Uploading ligand file" : "Upload ligand file"}</span>
        <small>MOL, MOL2, SDF, PDBQT, SMI, or SMILES are accepted.</small>
        <input id="ligand-upload" type="file" onChange={handleUpload} accept=".mol,.mol2,.sdf,.pdbqt,.smi,.smiles" disabled={busy} />
      </label>
      {ligand ? (
        <div aria-live="polite" className="summary-block">
          <span>Active ligand</span>
          <strong>{ligand.name}</strong>
          <p>{ligand.input_format.toUpperCase()}</p>
          {ligand.smiles ? <code>{ligand.smiles}</code> : null}
          <a className="download-link secondary-link" href={`${API_BASE_URL}/api/ligands/${ligand.id}/download`}>
            Download ligand file
          </a>
        </div>
      ) : (
        <InlineNotice>
          <p>Add a ligand before running docking.</p>
        </InlineNotice>
      )}
    </section>
  );
}
