import { useState } from "react";
import type { DockingJob, DockingParameters, LigandRecord, ProteinMetadata } from "../types";
import { FieldHint } from "./FieldHint";
import { InlineNotice } from "./InlineNotice";
import { LoadingButton } from "./LoadingButton";
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

type BusyAction = "prepare" | "run" | null;

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

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

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
  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  function updateNumber(key: NumericParameterKey, value: string) {
    const parsed = value === "" ? null : Number(value);
    if (parsed !== null && !Number.isFinite(parsed)) {
      return;
    }

    setValidationError(null);
    setParameters({
      ...parameters,
      [key]: parsed === null && !key.startsWith("center_") ? 0 : parsed
    } as DockingParameters);
  }

  function validateParameters() {
    const positiveFields: Array<[number, string]> = [
      [parameters.size_x, "Size X"],
      [parameters.size_y, "Size Y"],
      [parameters.size_z, "Size Z"]
    ];

    for (const [value, label] of positiveFields) {
      if (!Number.isFinite(value) || value <= 0) {
        return `${label} must be greater than 0 Å.`;
      }
    }

    if (!Number.isInteger(parameters.exhaustiveness) || parameters.exhaustiveness < 1 || parameters.exhaustiveness > 64) {
      return "Exhaustiveness must be a whole number between 1 and 64.";
    }
    if (!Number.isInteger(parameters.num_modes) || parameters.num_modes < 1 || parameters.num_modes > 50) {
      return "Modes must be a whole number between 1 and 50.";
    }
    if (!Number.isFinite(parameters.energy_range) || parameters.energy_range < 0) {
      return "Energy range must be 0 or greater.";
    }
    if (!parameters.autobox_from_receptor) {
      const centers = [
        [parameters.center_x, "Center X"],
        [parameters.center_y, "Center Y"],
        [parameters.center_z, "Center Z"]
      ] as const;
      const missingCenter = centers.find(([value]) => !isFiniteNumber(value));
      if (missingCenter) {
        return `${missingCenter[1]} is required when receptor autoboxing is off.`;
      }
    }

    return null;
  }

  async function prepare() {
    if (!protein) {
      onError("Fetch a protein before preparing docking inputs.");
      return;
    }

    const issue = validateParameters();
    if (issue) {
      setValidationError(issue);
      onError(issue);
      return;
    }

    setBusyAction("prepare");
    setValidationError(null);
    try {
      onJob(await prepareDocking(protein.id, ligand?.id ?? null, parameters));
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Preparation failed.";
      setValidationError(detail);
      onError(detail);
    } finally {
      setBusyAction(null);
    }
  }

  async function run() {
    if (!protein || !ligand) {
      onError("Protein and ligand are required before running docking.");
      return;
    }

    const issue = validateParameters();
    if (issue) {
      setValidationError(issue);
      onError(issue);
      return;
    }

    setBusyAction("run");
    setValidationError(null);
    try {
      onJob(await runDocking(protein.id, ligand.id, parameters));
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Docking failed.";
      setValidationError(detail);
      onError(detail);
    } finally {
      setBusyAction(null);
    }
  }

  const coordinatesRequired = !parameters.autobox_from_receptor;
  const controlsBusy = busyAction !== null;

  return (
    <section aria-labelledby="docking-panel-title" className="panel docking-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Docking</p>
          <h2 id="docking-panel-title">Preparation and Vina run</h2>
        </div>
        {job ? <StatusPill status={job.status} /> : null}
      </div>
      <div className="parameter-grid" role="group" aria-describedby="docking-parameter-help" aria-label="Docking box and search parameters">
        <label htmlFor="center-x">
          Center X
          <input
            aria-describedby="docking-parameter-help"
            aria-invalid={coordinatesRequired && !isFiniteNumber(parameters.center_x)}
            disabled={parameters.autobox_from_receptor}
            id="center-x"
            inputMode="decimal"
            step="0.1"
            type="number"
            value={parameters.center_x ?? ""}
            onChange={(event) => updateNumber("center_x", event.target.value)}
          />
        </label>
        <label htmlFor="center-y">
          Center Y
          <input
            aria-describedby="docking-parameter-help"
            aria-invalid={coordinatesRequired && !isFiniteNumber(parameters.center_y)}
            disabled={parameters.autobox_from_receptor}
            id="center-y"
            inputMode="decimal"
            step="0.1"
            type="number"
            value={parameters.center_y ?? ""}
            onChange={(event) => updateNumber("center_y", event.target.value)}
          />
        </label>
        <label htmlFor="center-z">
          Center Z
          <input
            aria-describedby="docking-parameter-help"
            aria-invalid={coordinatesRequired && !isFiniteNumber(parameters.center_z)}
            disabled={parameters.autobox_from_receptor}
            id="center-z"
            inputMode="decimal"
            step="0.1"
            type="number"
            value={parameters.center_z ?? ""}
            onChange={(event) => updateNumber("center_z", event.target.value)}
          />
        </label>
        <label htmlFor="size-x">
          Size X
          <input id="size-x" min={0.1} step="0.1" type="number" value={parameters.size_x} onChange={(event) => updateNumber("size_x", event.target.value)} />
        </label>
        <label htmlFor="size-y">
          Size Y
          <input id="size-y" min={0.1} step="0.1" type="number" value={parameters.size_y} onChange={(event) => updateNumber("size_y", event.target.value)} />
        </label>
        <label htmlFor="size-z">
          Size Z
          <input id="size-z" min={0.1} step="0.1" type="number" value={parameters.size_z} onChange={(event) => updateNumber("size_z", event.target.value)} />
        </label>
        <label htmlFor="exhaustiveness">
          Exhaustiveness
          <input
            id="exhaustiveness"
            min={1}
            max={64}
            step={1}
            type="number"
            value={parameters.exhaustiveness}
            onChange={(event) => updateNumber("exhaustiveness", event.target.value)}
          />
        </label>
        <label htmlFor="num-modes">
          Modes
          <input
            id="num-modes"
            min={1}
            max={50}
            step={1}
            type="number"
            value={parameters.num_modes}
            onChange={(event) => updateNumber("num_modes", event.target.value)}
          />
        </label>
        <label htmlFor="energy-range">
          Energy range
          <input
            id="energy-range"
            min={0}
            step="0.1"
            type="number"
            value={parameters.energy_range}
            onChange={(event) => updateNumber("energy_range", event.target.value)}
          />
        </label>
      </div>
      <FieldHint id="docking-parameter-help">
        Use receptor autoboxing for quick screening. Turn it off only when you know the binding-site center coordinates.
      </FieldHint>
      <label className="checkbox-row" htmlFor="autobox-from-receptor">
        <input
          id="autobox-from-receptor"
          type="checkbox"
          checked={parameters.autobox_from_receptor}
          onChange={(event) => {
            setValidationError(null);
            setParameters({
              ...parameters,
              autobox_from_receptor: event.target.checked
            });
          }}
        />
        Estimate box from receptor when coordinates are missing
      </label>
      {validationError ? (
        <InlineNotice tone="error">
          <p>{validationError}</p>
        </InlineNotice>
      ) : null}
      <div className="action-row">
        <LoadingButton type="button" onClick={prepare} busy={busyAction === "prepare"} busyLabel="Preparing inputs" disabled={!protein || controlsBusy}>
          Prepare inputs
        </LoadingButton>
        <LoadingButton type="button" onClick={run} busy={busyAction === "run"} busyLabel="Running docking" disabled={!protein || !ligand || controlsBusy}>
          Run docking
        </LoadingButton>
      </div>
      {job?.logs.length ? (
        <div aria-label="Docking workflow log" className="log-list" role="log">
          {job.logs.map((entry, index) => (
            <p key={`${entry.step}-${index}`}>
              <strong>{entry.step}</strong> [{entry.status}]: {entry.message}
            </p>
          ))}
        </div>
      ) : (
        <InlineNotice>
          <p>Preparation and docking logs will appear here.</p>
        </InlineNotice>
      )}
    </section>
  );
}
