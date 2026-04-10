export type ChainInfo = {
  chain_id: string;
  entity_id?: string | null;
  description?: string | null;
  molecule_type?: string | null;
  organism?: string | null;
};

export type ProteinSearchResult = {
  pdb_id: string;
  title?: string | null;
  score?: number | null;
  source_url: string;
};

export type ProteinMetadata = {
  id: string;
  pdb_id: string;
  query?: string | null;
  name: string;
  organism?: string | null;
  experimental_method?: string | null;
  resolution?: number | null;
  chains: ChainInfo[];
  source_url: string;
  pdb_path: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ProteinFetchResponse = {
  protein: ProteinMetadata;
  candidates: ProteinSearchResult[];
  message: string;
};

export type LigandRecord = {
  id: string;
  name: string;
  input_format: string;
  source_path: string;
  smiles?: string | null;
  prepared_path?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type LigandSearchResult = {
  cid: number;
  name: string;
  smiles: string;
  molecular_formula?: string | null;
  molecular_weight?: string | null;
  inchikey?: string | null;
  source_url: string;
};

export type DockingParameters = {
  center_x?: number | null;
  center_y?: number | null;
  center_z?: number | null;
  size_x: number;
  size_y: number;
  size_z: number;
  exhaustiveness: number;
  num_modes: number;
  energy_range: number;
  autobox_from_receptor: boolean;
};

export type DockingScore = {
  mode: number;
  affinity_kcal_mol: number;
  rmsd_lb?: number | null;
  rmsd_ub?: number | null;
};

export type WorkflowLog = {
  step: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  message: string;
  detail?: string | null;
  created_at: string;
};

export type DockingJob = {
  id: string;
  protein_id: string;
  ligand_id?: string | null;
  status: "pending" | "running" | "completed" | "failed";
  parameters: DockingParameters;
  scores: DockingScore[];
  output_dir: string;
  receptor_pdbqt?: string | null;
  ligand_pdbqt?: string | null;
  output_pdbqt?: string | null;
  report_path?: string | null;
  logs: WorkflowLog[];
  error?: string | null;
  created_at: string;
  updated_at: string;
};

export type SessionContext = {
  active_protein_id?: string | null;
  active_ligand_id?: string | null;
  last_job_id?: string | null;
  last_candidates: ProteinSearchResult[];
};

export type AgentAction = {
  tool: string;
  status: "completed" | "failed" | "needs_input" | "skipped";
  message: string;
  data: Record<string, unknown>;
};

export type AgentResponse = {
  session_id: string;
  message: string;
  actions: AgentAction[];
  context: SessionContext;
  data: {
    protein?: ProteinMetadata;
    ligand?: LigandRecord;
    job?: DockingJob;
    candidates?: ProteinSearchResult[];
  } & Record<string, unknown>;
};
