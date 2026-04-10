import { FormEvent, useState } from "react";
import { API_BASE_URL } from "../api";
import type { ProteinFetchResponse, ProteinMetadata } from "../types";
import { StructureViewer } from "./StructureViewer";

type ProteinPanelProps = {
  protein?: ProteinMetadata;
  onProtein: (protein: ProteinMetadata) => void;
  fetchProtein: (query: string) => Promise<ProteinFetchResponse>;
  onError: (message: string) => void;
};

export function ProteinPanel({ protein, onProtein, fetchProtein, onError }: ProteinPanelProps) {
  const [query, setQuery] = useState("");
  const [selectedChain, setSelectedChain] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) {
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await fetchProtein(query);
      onProtein(response.protein);
      setSelectedChain(null);
      setMessage(response.message);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Protein fetch failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel protein-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Protein</p>
          <h2>Structure retrieval and viewer</h2>
        </div>
      </div>
      <form className="inline-form" onSubmit={submit}>
        <label>
          PDB ID, gene, or protein name
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="1CRN, P53, EGFR"
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Fetching" : "Fetch"}
        </button>
      </form>
      {message ? <p className="notice">{message}</p> : null}
      {protein ? (
        <div className="protein-content">
          <div className="metadata-grid">
            <div>
              <span>Name</span>
              <strong>{protein.name}</strong>
            </div>
            <div>
              <span>PDB ID</span>
              <strong>{protein.pdb_id}</strong>
            </div>
            <div>
              <span>Organism</span>
              <strong>{protein.organism ?? "Unknown"}</strong>
            </div>
            <div>
              <span>Method</span>
              <strong>{protein.experimental_method ?? "Unknown"}</strong>
            </div>
            <div>
              <span>Resolution</span>
              <strong>{protein.resolution ? `${protein.resolution} Å` : "Not available"}</strong>
            </div>
            <div>
              <span>Source</span>
              <a href={protein.source_url} target="_blank" rel="noreferrer">
                RCSB PDB
              </a>
            </div>
          </div>
          <div className="chain-row">
            <button type="button" className={!selectedChain ? "selected" : ""} onClick={() => setSelectedChain(null)}>
              All chains
            </button>
            {protein.chains.map((chain) => (
              <button
                type="button"
                className={selectedChain === chain.chain_id ? "selected" : ""}
                key={`${chain.entity_id}-${chain.chain_id}`}
                onClick={() => setSelectedChain(chain.chain_id)}
                title={chain.description ?? undefined}
              >
                Chain {chain.chain_id}
              </button>
            ))}
          </div>
          <StructureViewer
            structureUrl={`${API_BASE_URL}/api/proteins/${protein.id}/download`}
            selectedChain={selectedChain}
          />
          <a className="download-link" href={`${API_BASE_URL}/api/proteins/${protein.id}/download`}>
            Download PDB file
          </a>
        </div>
      ) : (
        <p className="empty-state">Fetch a protein to populate metadata and the 3D viewer.</p>
      )}
    </section>
  );
}

