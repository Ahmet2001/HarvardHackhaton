from pathlib import Path

from app.utils.vina import parse_vina_log


def test_parse_vina_log_scores(tmp_path: Path) -> None:
    log_path = tmp_path / "vina.log"
    log_path.write_text(
        """
-----+------------+----------+----------
   1       -7.4      0.000      0.000
   2       -6.8      1.312      2.101
""",
        encoding="utf-8",
    )

    scores = parse_vina_log(log_path)

    assert len(scores) == 2
    assert scores[0].mode == 1
    assert scores[0].affinity_kcal_mol == -7.4
    assert scores[1].rmsd_lb == 1.312


def test_parse_vina_log_scores_from_captured_stdout(tmp_path: Path) -> None:
    log_path = tmp_path / "vina.log"
    log_path.write_text(
        """
$ vina --receptor receptor.pdbqt --ligand ligand.pdbqt --out poses.pdbqt
Output will be poses.pdbqt
-----+------------+----------+----------
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1       -8.1          0          0
   2       -7.2      1.544      2.033
""",
        encoding="utf-8",
    )

    scores = parse_vina_log(log_path)

    assert [score.affinity_kcal_mol for score in scores] == [-8.1, -7.2]
