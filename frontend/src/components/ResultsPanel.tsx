import { API_BASE_URL } from "../api";
import type { DockingJob, LigandRecord, ProteinMetadata } from "../types";
import { StatusPill } from "./StatusPill";

type ResultsPanelProps = {
  protein?: ProteinMetadata;
  ligand?: LigandRecord;
  job?: DockingJob;
};

export function ResultsPanel({ protein, ligand, job }: ResultsPanelProps) {
  const bestScore = job?.scores.length
    ? [...job.scores].sort((a, b) => a.affinity_kcal_mol - b.affinity_kcal_mol)[0]
    : undefined;

  return (
    <section className="panel results-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Results</p>
          <h2>Scores and report</h2>
        </div>
        {job ? <StatusPill status={job.status} /> : null}
      </div>
      <div className="summary-strip">
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
        <table className="score-table">
          <thead>
            <tr>
              <th>Mode</th>
              <th>Affinity</th>
              <th>RMSD lower</th>
              <th>RMSD upper</th>
            </tr>
          </thead>
          <tbody>
            {job.scores.map((score) => (
              <tr key={score.mode}>
                <td>{score.mode}</td>
                <td>{score.affinity_kcal_mol}</td>
                <td>{score.rmsd_lb ?? "-"}</td>
                <td>{score.rmsd_ub ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty-state">
          {job?.error ? job.error : "Docking scores will appear after a successful Vina run."}
        </p>
      )}
      {job ? (
        <div className="action-row">
          <a className={job.report_path ? "download-link" : "download-link disabled"} href={`${API_BASE_URL}/api/docking/jobs/${job.id}/report`}>
            Download report
          </a>
          <a className={job.output_pdbqt ? "download-link" : "download-link disabled"} href={`${API_BASE_URL}/api/docking/jobs/${job.id}/poses`}>
            Download poses
          </a>
        </div>
      ) : null}
    </section>
  );
}

