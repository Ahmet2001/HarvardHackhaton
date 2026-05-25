type StatusPillProps = {
  status?: string;
};

function formatStatus(status: string) {
  return status.replace(/_/g, " ");
}

export function StatusPill({ status = "idle" }: StatusPillProps) {
  const label = formatStatus(status);

  return (
    <span aria-label={`Status: ${label}`} className={`status-pill status-${status}`} role="status">
      {label}
    </span>
  );
}
