from app.agents.intent import (
    extract_ligand_name,
    extract_protein_query,
    extract_smiles,
    is_casual_message,
    normalize_protein_query,
    wants_download,
    wants_fetch,
    wants_run_docking,
)


def test_extract_pdb_id_from_command() -> None:
    assert extract_protein_query("Get PDB structure 1CRN") == "1CRN"


def test_extract_keyword_from_structure_request() -> None:
    assert extract_protein_query("Fetch the 3D structure of EGFR") == "EGFR"


def test_normalize_common_protein_typo() -> None:
    assert normalize_protein_query("efgr") == "EGFR"


def test_extract_fetch_keyword_with_common_typo() -> None:
    assert extract_protein_query("get efgr") == "EGFR"


def test_extract_bare_common_protein_typo() -> None:
    assert extract_protein_query("efgr") == "EGFR"


def test_extract_keyword_from_misspelled_structure_request() -> None:
    assert extract_protein_query("Fetch 3d structer of P53") == "P53"


def test_download_request_is_not_fetch_request() -> None:
    assert wants_download("Download the PDB file")
    assert not wants_fetch("Download the PDB file")


def test_extract_inline_smiles() -> None:
    assert extract_smiles("Use SMILES: CC(=O)OC1=CC=CC=C1C(=O)O") == "CC(=O)OC1=CC=CC=C1C(=O)O"


def test_extract_ligand_name() -> None:
    assert extract_ligand_name("use aspirin as ligand") == "aspirin"
    assert extract_ligand_name("dock with imatinib") == "imatinib"


def test_run_docking_intent() -> None:
    assert wants_run_docking("Run docking for this protein")


def test_casual_message_detection() -> None:
    assert is_casual_message("hello")
    assert is_casual_message("selam nasılsın")


def test_casual_message_is_not_protein_query() -> None:
    assert extract_protein_query("hello") is None
