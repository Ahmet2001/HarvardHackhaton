import { useEffect, useState } from "react";
import { api } from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { DockingPanel } from "./components/DockingPanel";
import { LigandPanel } from "./components/LigandPanel";
import { ProteinPanel } from "./components/ProteinPanel";
import { ResultsPanel } from "./components/ResultsPanel";
import type { AgentResponse, DockingJob, DockingParameters, LigandRecord, ProteinMetadata } from "./types";

const defaultParameters: DockingParameters = {
  center_x: null,
  center_y: null,
  center_z: null,
  size_x: 22,
  size_y: 22,
  size_z: 22,
  exhaustiveness: 8,
  num_modes: 9,
  energy_range: 3,
  autobox_from_receptor: true
};

function App() {
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [protein, setProtein] = useState<ProteinMetadata | undefined>();
  const [ligand, setLigand] = useState<LigandRecord | undefined>();
  const [job, setJob] = useState<DockingJob | undefined>();
  const [parameters, setParameters] = useState<DockingParameters>(defaultParameters);
  const [apiStatus, setApiStatus] = useState("checking");
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    api
      .health()
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));
  }, []);

  function handleAgentResponse(response: AgentResponse) {
    setSessionId(response.session_id);
    if (response.data.protein) {
      setProtein(response.data.protein);
    }
    if (response.data.ligand) {
      setLigand(response.data.ligand);
    }
    if (response.data.job) {
      setJob(response.data.job);
      setParameters(response.data.job.parameters);
    }
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">AI-assisted bioinformatics</p>
          <h1>Bıdık</h1>
          <p>Retrieve protein structures, prepare docking inputs, run Vina, and review traceable outputs.</p>
        </div>
        <div className={`api-indicator ${apiStatus}`}>
          <span />
          API {apiStatus}
        </div>
      </header>
      {error ? (
        <div className="error-banner" role="alert">
          <strong>Workflow notice</strong>
          <p>{error}</p>
          <button type="button" onClick={() => setError(undefined)}>
            Dismiss
          </button>
        </div>
      ) : null}
      <div className="dashboard-grid">
        <ChatPanel
          sessionId={sessionId}
          dockingParameters={parameters}
          sendMessage={api.sendAgentMessage}
          onAgentResponse={handleAgentResponse}
          onError={setError}
        />
        <ProteinPanel protein={protein} onProtein={setProtein} fetchProtein={api.fetchProtein} onError={setError} />
        <LigandPanel
          ligand={ligand}
          onLigand={setLigand}
          createLigand={api.createLigand}
          searchLigands={api.searchLigands}
          lookupLigand={api.lookupLigand}
          uploadLigand={api.uploadLigand}
          onError={setError}
        />
        <DockingPanel
          protein={protein}
          ligand={ligand}
          job={job}
          parameters={parameters}
          setParameters={setParameters}
          prepareDocking={api.prepareDocking}
          runDocking={api.runDocking}
          onJob={setJob}
          onError={setError}
        />
        <ResultsPanel protein={protein} ligand={ligand} job={job} />
      </div>
    </main>
  );
}

export default App;
