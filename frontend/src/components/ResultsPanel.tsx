import { API_BASE_URL } from "../api";
import type { DockingJob, LigandRecord, ProteinMetadata } from "../types";
import { InlineNotice } from "./InlineNotice";
import { StatusPill } from "./StatusPill";

type ResultsPanelProps = {
  protein?: ProteinMetadata;
  ligand?: LigandRecord;
  job?: DockingJob;
};

type DownloadActionProps = {
  enabled: boolean;
  href: string;
  label: string;
};

function DownloadAction({ enabled, href, label }: DownloadActionProps) {
  if (!enabled) {
    return (
      <span aria-disabled="true" className="download-link disabled" role="link">
        {label}
      </span>
    );
  }

  return (
    <a className="download-link" href={href}>
      {label}
    </a>
  );
}

export function ResultsPanel({ protein, ligand, job }: ResultsPanelProps) {
  const bestScore = job?.scores.length
    ? [...job.scores].sort((a, b) => a.affinity_kcal_mol - b.affinity_kcal_mol)[0]
    : undefined;

  return (
    <section aria-labelledby="results-panel-title" className="panel results-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Results</p>
          <h2 id="results-panel-title">Scores and report</h2>
        </div>
        {job ? <StatusPill status={job.status} /> : null}
      </div>
      <div aria-label="Selected workflow summary" className="summary-strip">
        <div>
          <span>Protein</span>
          <strong>{protein ? `${protein.name} (${protein.pdb_id})` : "None selected"}</strong>
        </div>
        <div>
          <span>Ligand</span>
          <strong>{ligand?.name ?? "None selected"}</strong>
        </div>
        <div>
          <span>Best score</span>
          <strong>{bestScore ? `${bestScore.affinity_kcal_mol} kcal/mol` : "Not available"}</strong>
        </div>
      </div>
      {job?.scores.length ? (
        <div aria-label="Docking scores table" className="table-scroll" tabIndex={0}>
          <table className="score-table">
            <caption>Ranked AutoDock Vina poses for the active protein and ligand.</caption>
            <thead>
              <tr>
                <th scope="col">Mode</th>
                <th scope="col">Affinity (kcal/mol)</th>
                <th scope="col">RMSD lower (Å)</th>
                <th scope="col">RMSD upper (Å)</th>
              </tr>
            </thead>
            <tbody>
              {job.scores.map((score) => (
                <tr key={score.mode}>
                  <td>{score.mode}</td>
                  <td>{score.affinity_kcal_mol.toFixed(2)}</td>
                  <td>{score.rmsd_lb?.toFixed(2) ?? "-"}</td>
                  <td>{score.rmsd_ub?.toFixed(2) ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <InlineNotice tone={job?.status === "failed" ? "error" : "info"}>
          <p>{job?.error ? job.error : "Docking scores will appear after a successful Vina run."}</p>
        </InlineNotice>
      )}
      {job ? (
        <div className="action-row">
          <DownloadAction enabled={Boolean(job.report_path)} href={`${API_BASE_URL}/api/docking/jobs/${job.id}/report`} label="Download report" />
          <DownloadAction enabled={Boolean(job.output_pdbqt)} href={`${API_BASE_URL}/api/docking/jobs/${job.id}/poses`} label="Download poses" />
        </div>
      ) : null}
    </section>
  );
}
