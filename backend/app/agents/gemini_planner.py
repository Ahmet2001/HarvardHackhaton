from __future__ import annotations

import json
from typing import Any

from app.config import Settings
from app.models.schemas import AgentRequest, SessionContext

PLANNER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intents": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "fetch_protein",
                    "store_ligand",
                    "prepare_docking",
                    "run_docking",
                    "show_results",
                    "download_pdb",
                    "list_candidate_ligands",
                    "chat",
                    "unknown",
                ],
            },
        },
        "protein_query": {"type": ["string", "null"]},
        "ligand_smiles": {"type": ["string", "null"]},
        "ligand_name": {"type": ["string", "null"]},
        "plain_language_goal": {"type": "string"},
        "assistant_message": {"type": ["string", "null"]},
        "missing_information": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "intents",
        "protein_query",
        "ligand_smiles",
        "ligand_name",
        "plain_language_goal",
        "assistant_message",
        "missing_information",
    ],
    "additionalProperties": False,
}


class GeminiIntentPlanner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.enable_gemini_agent and self.settings.gemini_api_key)

    def status(self) -> dict[str, object]:
        return {
            "provider": "gemini",
            "enabled": self.enabled,
            "api_key_configured": bool(self.settings.gemini_api_key),
            "model": self.settings.gemini_model,
            "fallback": "deterministic_router",
        }

    def plan(self, request: AgentRequest, context: SessionContext) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Gemini planner is not enabled because GEMINI_API_KEY is not configured.")

        from google import genai

        client = genai.Client(api_key=self.settings.gemini_api_key)
        payload = {
            "user_message": request.message,
            "explicit_ligand_smiles": request.ligand_smiles,
            "explicit_ligand_name": request.ligand_name,
            "active_protein_id": context.active_protein_id,
            "active_ligand_id": context.active_ligand_id,
            "last_job_id": context.last_job_id,
        }
        prompt = (
            "You are the intent planner for BioDockX, an agentic bioinformatics workflow app.\n"
            "Return only JSON matching the schema. Do not claim scientific work has run.\n"
            "Be friendly and conversational for greetings or general chat: use intent 'chat' and write assistant_message.\n"
            "For workflow requests, choose tool intents and keep assistant_message null unless the user is only chatting.\n"
            "Prefer asking for missing protein or ligand data over inventing it, but tolerate typos.\n"
            "Protein queries may be PDB IDs, gene names, or protein names. Normalize obvious gene typos like 'efgr' to 'EGFR'.\n"
            "For ligand/drug names like aspirin, caffeine, imatinib, or ibuprofen, use intent 'store_ligand' and set ligand_name.\n"
            "Extract SMILES only when the user provided one; otherwise keep ligand_smiles null and use ligand_name.\n\n"
            f"Planner input:\n{json.dumps(payload, ensure_ascii=True)}"
        )
        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": PLANNER_SCHEMA,
            },
        )
        if not response.text:
            raise RuntimeError("Gemini planner returned no structured output text.")
        parsed = json.loads(response.text)
        if not isinstance(parsed, dict):
            raise RuntimeError("Gemini planner returned an invalid plan.")
        return parsed
