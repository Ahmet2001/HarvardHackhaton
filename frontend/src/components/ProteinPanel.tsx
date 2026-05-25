import { FormEvent, useState } from "react";
import { API_BASE_URL } from "../api";
import type { ProteinFetchResponse, ProteinMetadata } from "../types";
import { FieldHint } from "./FieldHint";
import { InlineNotice } from "./InlineNotice";
import { LoadingButton } from "./LoadingButton";
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

  const canFetch = query.trim().length > 0 && !busy;

  return (
    <section aria-labelledby="protein-panel-title" className="panel protein-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Protein</p>
          <h2 id="protein-panel-title">Structure retrieval and viewer</h2>
        </div>
      </div>
      <form className="inline-form" onSubmit={submit}>
        <label htmlFor="protein-query">
          PDB ID, gene, or protein name
          <input
            aria-describedby="protein-query-help"
            autoComplete="off"
            id="protein-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="1CRN, P53, EGFR"
          />
        </label>
        <LoadingButton type="submit" busy={busy} busyLabel="Fetching structure" disabled={!canFetch}>
          Fetch
        </LoadingButton>
      </form>
      <FieldHint id="protein-query-help">Search by a known PDB ID or use a gene/protein keyword and BioDockX will pick the best available structure.</FieldHint>
      {message ? (
        <InlineNotice tone="success">
          <p>{message}</p>
        </InlineNotice>
      ) : null}
      {protein ? (
        <div aria-live="polite" className="protein-content">
          <div aria-label="Protein metadata" className="metadata-grid">
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
          <div aria-label="Chain highlight controls" className="chain-row" role="group">
            <button aria-pressed={!selectedChain} type="button" className={!selectedChain ? "selected" : ""} onClick={() => setSelectedChain(null)}>
              All chains
            </button>
            {protein.chains.map((chain) => (
              <button
                aria-pressed={selectedChain === chain.chain_id}
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
          <a aria-label={`Download ${protein.pdb_id} PDB file`} className="download-link" href={`${API_BASE_URL}/api/proteins/${protein.id}/download`}>
            Download PDB file
          </a>
        </div>
      ) : (
        <InlineNotice>
          <p>Fetch a protein to populate metadata and the 3D viewer.</p>
        </InlineNotice>
      )}
    </section>
  );
}
