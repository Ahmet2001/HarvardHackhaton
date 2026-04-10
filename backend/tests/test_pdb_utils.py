from pathlib import Path

from app.utils.pdb import clean_pdb_for_docking, estimate_binding_box_from_pdb


def test_clean_pdb_keeps_atoms_and_removes_water(tmp_path: Path) -> None:
    source = tmp_path / "input.pdb"
    target = tmp_path / "cleaned.pdb"
    source.write_text(
        """ATOM      1  N   ALA A   1      11.104  13.207   2.100  1.00 20.00           N
HETATM    2  O   HOH A   2      12.000  14.000   3.000  1.00 20.00           O
TER
END
""",
        encoding="utf-8",
    )

    kept = clean_pdb_for_docking(source, target)

    assert kept == 1
    cleaned = target.read_text(encoding="utf-8")
    assert "ALA" in cleaned
    assert "HOH" not in cleaned


def test_estimate_binding_box(tmp_path: Path) -> None:
    pdb_path = tmp_path / "input.pdb"
    pdb_path.write_text(
        """ATOM      1  N   ALA A   1      10.000  10.000  10.000  1.00 20.00           N
ATOM      2  C   ALA A   1      20.000  30.000  40.000  1.00 20.00           C
END
""",
        encoding="utf-8",
    )

    box = estimate_binding_box_from_pdb(pdb_path)

    assert box["center_x"] == 15
    assert box["center_y"] == 20
    assert box["center_z"] == 25
    assert box["size_x"] >= 12

