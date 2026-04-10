import type {
  AgentResponse,
  DockingJob,
  DockingParameters,
  LigandRecord,
  LigandSearchResult,
  ProteinFetchResponse,
  ProteinMetadata,
  ProteinSearchResult
} from "./types";

export const API_BASE_URL = import.meta.env.VITE_BIDIK_API_URL ?? "http://localhost:8000";

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => requestJson<{ status: string }>("/api/health"),
  listProteins: () => requestJson<ProteinMetadata[]>("/api/proteins"),
  searchProteins: (query: string) =>
    requestJson<ProteinSearchResult[]>(`/api/proteins/search?query=${encodeURIComponent(query)}`),
  fetchProtein: (query: string) =>
    requestJson<ProteinFetchResponse>("/api/proteins/fetch", {
      method: "POST",
      body: JSON.stringify({ query })
    }),
  createLigand: (name: string, smiles: string) =>
    requestJson<LigandRecord>("/api/ligands", {
      method: "POST",
      body: JSON.stringify({ name, smiles, input_format: "smiles" })
    }),
  searchLigands: (query: string) =>
    requestJson<LigandSearchResult[]>(`/api/ligands/search?query=${encodeURIComponent(query)}`),
  lookupLigand: (name: string) =>
    requestJson<LigandRecord>("/api/ligands/lookup", {
      method: "POST",
      body: JSON.stringify({ name })
    }),
  uploadLigand: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/api/ligands/upload`, {
      method: "POST",
      body: formData
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(body.detail ?? response.statusText);
    }
    return response.json() as Promise<LigandRecord>;
  },
  prepareDocking: (proteinId: string, ligandId: string | null, parameters: DockingParameters) =>
    requestJson<DockingJob>("/api/docking/prepare", {
      method: "POST",
      body: JSON.stringify({ protein_id: proteinId, ligand_id: ligandId, parameters })
    }),
  runDocking: (proteinId: string, ligandId: string, parameters: DockingParameters) =>
    requestJson<DockingJob>("/api/docking/run", {
      method: "POST",
      body: JSON.stringify({ protein_id: proteinId, ligand_id: ligandId, parameters })
    }),
  sendAgentMessage: (
    message: string,
    sessionId?: string,
    ligandSmiles?: string,
    dockingParameters?: DockingParameters
  ) =>
    requestJson<AgentResponse>("/api/agent/message", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        message,
        ligand_smiles: ligandSmiles || undefined,
        docking_parameters: dockingParameters
      })
    })
};
