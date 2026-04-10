import type { DockingJob, DockingParameters, LigandRecord, ProteinMetadata } from "../types";
import { StatusPill } from "./StatusPill";

type NumericParameterKey =
  | "center_x"
  | "center_y"
  | "center_z"
  | "size_x"
  | "size_y"
  | "size_z"
  | "exhaustiveness"
  | "num_modes"
  | "energy_range";

type DockingPanelProps = {
  protein?: ProteinMetadata;
  ligand?: LigandRecord;
  job?: DockingJob;
  parameters: DockingParameters;
  setParameters: (parameters: DockingParameters) => void;
  prepareDocking: (
    proteinId: string,
    ligandId: string | null,
    parameters: DockingParameters
  ) => Promise<DockingJob>;
  runDocking: (proteinId: string, ligandId: string, parameters: DockingParameters) => Promise<DockingJob>;
  onJob: (job: DockingJob) => void;
  onError: (message: string) => void;
};

export function DockingPanel({
  protein,
  ligand,
  job,
  parameters,
  setParameters,
  prepareDocking,
  runDocking,
  onJob,
  onError
}: DockingPanelProps) {
  function updateNumber(key: NumericParameterKey, value: string) {
    const nextValue = value === "" && key.startsWith("center_") ? null : Number(value);
    setParameters({
      ...parameters,
      [key]: nextValue
    } as DockingParameters);
  }

  async function prepare() {
    if (!protein) {
      onError("Fetch a protein before preparing docking inputs.");
      return;
    }
    try {
      onJob(await prepareDocking(protein.id, ligand?.id ?? null, parameters));
    } catch (error) {
      onError(error instanceof Error ? error.message : "Preparation failed.");
    }
  }

  async function run() {
    if (!protein || !ligand) {
      onError("Protein and ligand are required before running docking.");
      return;
    }
    try {
      onJob(await runDocking(protein.id, ligand.id, parameters));
    } catch (error) {
      onError(error instanceof Error ? error.message : "Docking failed.");
    }
  }

  return (
    <section className="panel docking-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Docking</p>
          <h2>Preparation and Vina run</h2>
        </div>
        {job ? <StatusPill status={job.status} /> : null}
      </div>
      <div className="parameter-grid">
        <label>
          Center X
          <input
            type="number"
            value={parameters.center_x ?? ""}
            onChange={(event) => updateNumber("center_x", event.target.value)}
            disabled={parameters.autobox_from_receptor}
          />
        </label>
        <label>
          Center Y
          <input
            type="number"
            value={parameters.center_y ?? ""}
            onChange={(event) => updateNumber("center_y", event.target.value)}
            disabled={parameters.autobox_from_receptor}
          />
        </label>
        <label>
          Center Z
          <input
            type="number"
            value={parameters.center_z ?? ""}
            onChange={(event) => updateNumber("center_z", event.target.value)}
            disabled={parameters.autobox_from_receptor}
          />
        </label>
        <label>
          Size X
          <input type="number" value={parameters.size_x} onChange={(event) => updateNumber("size_x", event.target.value)} />
        </label>
        <label>
          Size Y
          <input type="number" value={parameters.size_y} onChange={(event) => updateNumber("size_y", event.target.value)} />
        </label>
        <label>
          Size Z
          <input type="number" value={parameters.size_z} onChange={(event) => updateNumber("size_z", event.target.value)} />
        </label>
        <label>
          Exhaustiveness
          <input
            type="number"
            min={1}
            max={64}
            value={parameters.exhaustiveness}
            onChange={(event) => updateNumber("exhaustiveness", event.target.value)}
          />
        </label>
        <label>
          Modes
          <input
            type="number"
            min={1}
            max={50}
            value={parameters.num_modes}
            onChange={(event) => updateNumber("num_modes", event.target.value)}
          />
        </label>
      </div>
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={parameters.autobox_from_receptor}
          onChange={(event) =>
            setParameters({
              ...parameters,
              autobox_from_receptor: event.target.checked
            })
          }
        />
        Estimate box from receptor when coordinates are missing
      </label>
      <div className="action-row">
        <button type="button" onClick={prepare} disabled={!protein}>
          Prepare inputs
        </button>
        <button type="button" onClick={run} disabled={!protein || !ligand}>
          Run docking
        </button>
      </div>
      {job?.logs.length ? (
        <div className="log-list">
          {job.logs.map((entry, index) => (
            <p key={`${entry.step}-${index}`}>
              <strong>{entry.step}</strong> [{entry.status}]: {entry.message}
            </p>
          ))}
        </div>
      ) : (
        <p className="empty-state">Preparation and docking logs will appear here.</p>
      )}
    </section>
  );
}
