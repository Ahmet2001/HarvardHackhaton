from __future__ import annotations

import re
from pathlib import Path

from app.models.schemas import DockingScore


VINA_SCORE_LINE = re.compile(
    r"^\s*(?P<mode>\d+)\s+(?P<affinity>-?\d+(?:\.\d+)?)\s+"
    r"(?P<rmsd_lb>-?\d+(?:\.\d+)?)\s+(?P<rmsd_ub>-?\d+(?:\.\d+)?)\s*$"
)


def parse_vina_log(log_path: Path) -> list[DockingScore]:
    if not log_path.exists():
        return []

    scores: list[DockingScore] = []
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = VINA_SCORE_LINE.match(line)
        if not match:
            continue
        scores.append(
            DockingScore(
                mode=int(match.group("mode")),
                affinity_kcal_mol=float(match.group("affinity")),
                rmsd_lb=float(match.group("rmsd_lb")),
                rmsd_ub=float(match.group("rmsd_ub")),
            )
        )
    return scores

