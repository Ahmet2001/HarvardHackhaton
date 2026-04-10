from __future__ import annotations

from pathlib import Path


def clean_pdb_for_docking(input_path: Path, output_path: Path) -> int:
    """Remove common non-receptor records while preserving atom coordinates."""
    kept = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8", errors="ignore") as source, output_path.open(
        "w", encoding="utf-8"
    ) as target:
        for line in source:
            record = line[:6].strip()
            if record == "ATOM":
                residue = line[17:20].strip()
                if residue not in {"HOH", "WAT", "DOD"}:
                    target.write(line)
                    kept += 1
            elif record == "TER":
                target.write(line)
        target.write("END\n")
    return kept


def estimate_binding_box_from_pdb(input_path: Path, padding: float = 8.0) -> dict[str, float]:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    with input_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith("ATOM"):
                continue
            try:
                xs.append(float(line[30:38]))
                ys.append(float(line[38:46]))
                zs.append(float(line[46:54]))
            except ValueError:
                continue

    if not xs:
        raise ValueError("No ATOM coordinates were found in the receptor PDB file.")

    def center(values: list[float]) -> float:
        return (min(values) + max(values)) / 2.0

    def size(values: list[float]) -> float:
        return min(max((max(values) - min(values)) + padding, 12.0), 30.0)

    return {
        "center_x": round(center(xs), 3),
        "center_y": round(center(ys), 3),
        "center_z": round(center(zs), 3),
        "size_x": round(size(xs), 3),
        "size_y": round(size(ys), 3),
        "size_z": round(size(zs), 3),
    }

