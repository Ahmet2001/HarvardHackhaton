from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _path_from_env(name: str, default: str) -> Path:
    return Path(os.getenv(name, default)).expanduser().resolve()


def _bool_from_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("BIDIK_APP_NAME", "Bıdık")
    environment: str = os.getenv("BIDIK_ENV", "development")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "BIDIK_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
        ).split(",")
        if origin.strip()
    )
    database_path: Path = _path_from_env("BIDIK_DATABASE_PATH", "./data/bidik.db")
    data_dir: Path = _path_from_env("BIDIK_DATA_DIR", "./data")
    jobs_dir: Path = _path_from_env("BIDIK_JOBS_DIR", "./jobs")
    pdb_download_base_url: str = os.getenv(
        "BIDIK_PDB_DOWNLOAD_BASE_URL", "https://files.rcsb.org/download"
    )
    pubchem_pug_rest_url: str = os.getenv(
        "BIDIK_PUBCHEM_PUG_REST_URL", "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    )
    rcsb_data_api_url: str = os.getenv(
        "BIDIK_RCSB_DATA_API_URL", "https://data.rcsb.org/rest/v1/core"
    )
    rcsb_search_api_url: str = os.getenv(
        "BIDIK_RCSB_SEARCH_API_URL", "https://search.rcsb.org/rcsbsearch/v2/query"
    )
    vina_binary: str = os.getenv("BIDIK_VINA_BINARY", "vina")
    obabel_binary: str = os.getenv("BIDIK_OBABEL_BINARY", "obabel")
    command_timeout_seconds: int = int(os.getenv("BIDIK_COMMAND_TIMEOUT_SECONDS", "900"))
    http_timeout_seconds: int = int(os.getenv("BIDIK_HTTP_TIMEOUT_SECONDS", "30"))
    enable_gemini_agent: bool = _bool_from_env("BIDIK_ENABLE_GEMINI_AGENT", True)
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or os.getenv("BIDIK_GEMINI_API_KEY")
    gemini_model: str = os.getenv("BIDIK_GEMINI_MODEL", "gemini-2.5-flash")

    @property
    def proteins_dir(self) -> Path:
        return self.data_dir / "proteins"

    @property
    def ligands_dir(self) -> Path:
        return self.data_dir / "ligands"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.proteins_dir.mkdir(parents=True, exist_ok=True)
    settings.ligands_dir.mkdir(parents=True, exist_ok=True)
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
