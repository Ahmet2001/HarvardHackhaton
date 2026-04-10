from __future__ import annotations

import re

PDB_ID_PATTERN = re.compile(r"\b([0-9][A-Za-z0-9]{3})\b")
SMILES_PATTERN = re.compile(r"(?:smiles\s*[:=]\s*)(?P<smiles>[A-Za-z0-9@+\-\[\]\(\)=#$\\/%.]+)", re.I)

FETCH_TERMS = ("fetch", "get", "retrieve", "download", "structure")
FETCH_LIKE_TERMS = FETCH_TERMS + ("structer", "strcture", "protein")
PREPARE_TERMS = ("prepare", "clean", "preprocess")
RUN_TERMS = ("run docking", "dock ", "dock it", "docking for", "use this ligand")
RESULT_TERMS = ("show docking results", "summarize", "summary", "best score", "results")
DOWNLOAD_TERMS = ("download pdb", "download the pdb", "pdb file")
LIGAND_TERMS = ("ligand", "smiles", "sdf", "mol2", "mol ")
CANDIDATE_TERMS = ("candidate ligands", "list ligands", "suggest ligands")
LIGAND_NAME_PATTERNS = [
    r"(?:use|add|lookup|search|find|get)\s+(?P<target>[A-Za-z][A-Za-z0-9 -]{1,60}?)\s+(?:as\s+)?(?:a\s+)?ligand",
    r"(?:ligand|drug)\s+(?:is\s+|name\s+is\s+)?(?P<target>[A-Za-z][A-Za-z0-9 -]{1,60})",
    r"(?:dock|docking)\s+(?:with|using|ile)\s+(?P<target>[A-Za-z][A-Za-z0-9 -]{1,60})",
    r"(?P<target>[A-Za-z][A-Za-z0-9 -]{1,60})\s+(?:ile|with)\s+(?:dock|docking)",
]
GREETING_TERMS = {"hello", "hi", "hey", "merhaba", "selam", "sa", "naber", "nasilsin", "nasılsın"}
COMMON_PROTEIN_ALIASES = {
    "efgr": "EGFR",
    "egfr": "EGFR",
    "p53": "P53",
    "tp53": "TP53",
    "brca1": "BRCA1",
    "brca2": "BRCA2",
}


def wants_fetch(message: str) -> bool:
    text = message.lower()
    if "result" in text or wants_download(message):
        return False
    return any(term in text for term in FETCH_LIKE_TERMS)


def is_casual_message(message: str) -> bool:
    clean = re.sub(r"[^\wığüşöçİĞÜŞÖÇ]+", " ", message.lower()).strip()
    if not clean:
        return False
    words = set(clean.split())
    return clean in GREETING_TERMS or bool(words & GREETING_TERMS)


def wants_prepare(message: str) -> bool:
    text = message.lower()
    return any(term in text for term in PREPARE_TERMS)


def wants_run_docking(message: str) -> bool:
    text = f" {message.lower()} "
    return any(term in text for term in RUN_TERMS) or ("run" in text and "docking" in text)


def wants_results(message: str) -> bool:
    text = message.lower()
    return any(term in text for term in RESULT_TERMS)


def wants_download(message: str) -> bool:
    text = message.lower()
    return any(term in text for term in DOWNLOAD_TERMS)


def wants_ligand_list(message: str) -> bool:
    text = message.lower()
    return any(term in text for term in CANDIDATE_TERMS)


def extract_smiles(message: str) -> str | None:
    match = SMILES_PATTERN.search(message)
    return match.group("smiles") if match else None


def extract_ligand_name(message: str) -> str | None:
    if extract_smiles(message):
        return None
    for pattern in LIGAND_NAME_PATTERNS:
        match = re.search(pattern, message, re.I)
        if not match:
            continue
        target = match.group("target")
        target = re.split(r"\s+(?:and|then|sonra|for protein|protein)\s+", target, maxsplit=1, flags=re.I)[0]
        target = re.sub(r"^(?:the|this|a|an|bir)\s+", "", target.strip(), flags=re.I)
        target = target.strip(" :")
        if target and target.lower() not in {"ligand", "drug", "protein"}:
            return target
    return None


def extract_protein_query(message: str) -> str | None:
    pdb_match = PDB_ID_PATTERN.search(message)
    if pdb_match:
        return pdb_match.group(1).upper()

    if is_casual_message(message):
        return None

    clean_message = message.strip(" :")
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{1,8}", clean_message):
        return normalize_protein_query(clean_message)

    patterns = [
        r"(?:structure|structer|strcture)\s+(?:of|for)\s+(?P<target>[^,.?;]+)",
        r"(?:protein\s+)?(?:structure|structer|strcture)\s+of\s+(?P<target>[^,.?;]+)",
        r"(?:fetch|get|retrieve|download)\s+(?:the\s+)?(?:3d\s+)?(?:(?:structure|structer|strcture)\s+)?(?:of\s+)?(?P<target>[^,.?;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.I)
        if not match:
            continue
        target = match.group("target")
        target = re.split(r"\s+(?:and|then|with|for docking|using)\s+", target, maxsplit=1, flags=re.I)[0]
        target = re.sub(r"^(?:pdb id|protein|the|this)\s+", "", target.strip(), flags=re.I)
        target = re.sub(r"^(?:structure|structer|strcture)\s+(?:of|for)\s+", "", target, flags=re.I)
        target = target.strip(" :")
        if target and target.lower() not in {"protein", "this protein", "it", "structure", "structer"}:
            return normalize_protein_query(target)
    return None


def normalize_protein_query(query: str | None) -> str | None:
    if not query:
        return None
    clean = query.strip(" :")
    clean = re.sub(r"\s+", " ", clean)
    alias = COMMON_PROTEIN_ALIASES.get(clean.lower())
    if alias:
        return alias
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{1,8}", clean):
        return clean.upper()
    return clean


def message_mentions_ligand(message: str) -> bool:
    return any(term in message.lower() for term in LIGAND_TERMS)
