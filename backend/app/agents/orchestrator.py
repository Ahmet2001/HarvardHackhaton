from __future__ import annotations

from uuid import uuid4

from app.agents.gemini_planner import GeminiIntentPlanner
from app.agents.intent import (
    extract_ligand_name,
    extract_protein_query,
    extract_smiles,
    is_casual_message,
    normalize_protein_query,
    wants_download,
    wants_fetch,
    wants_ligand_list,
    wants_prepare,
    wants_results,
    wants_run_docking,
)
from app.database import Database
from app.models.schemas import AgentAction, AgentRequest, AgentResponse, DockingJob, SessionContext
from app.services.docking_service import DockingService
from app.services.ligand_service import LigandService
from app.services.protein_service import ProteinService
from app.tools.docking_tools import parse_docking_results, prepare_inputs_for_docking, run_docking
from app.tools.ligand_tools import create_ligand_from_smiles
from app.tools.protein_tools import fetch_protein_structure
from app.tools.visualization_tools import visualize_structure


class AgentOrchestrator:
    """Deterministic task router for scientific workflows.

    The MVP intentionally avoids claiming opaque model reasoning. It exposes the
    selected tools, stores session context, and reports failures from real tools.
    A hosted LLM can later be inserted in front of this router to improve language
    understanding while preserving the same tool contracts.
    """

    def __init__(
        self,
        db: Database,
        protein_service: ProteinService,
        ligand_service: LigandService,
        docking_service: DockingService,
        llm_planner: GeminiIntentPlanner | None = None,
    ) -> None:
        self.db = db
        self.protein_service = protein_service
        self.ligand_service = ligand_service
        self.docking_service = docking_service
        self.llm_planner = llm_planner

    def handle(self, request: AgentRequest) -> AgentResponse:
        session_id = request.session_id or f"session_{uuid4().hex[:12]}"
        context = self.db.get_or_create_session(session_id)
        actions: list[AgentAction] = []
        data: dict[str, object] = {}
        message = request.message.strip()
        llm_plan = self._plan_with_gemini(request, context, actions)
        plan_intents = set(llm_plan.get("intents", [])) if llm_plan else set()
        if llm_plan:
            data["agent_plan"] = llm_plan

        ligand_smiles = request.ligand_smiles or (llm_plan or {}).get("ligand_smiles") or extract_smiles(message)
        if ligand_smiles:
            try:
                ligand = create_ligand_from_smiles(
                    self.ligand_service,
                    ligand_smiles,
                    name=request.ligand_name or (llm_plan or {}).get("ligand_name"),
                )
                context.active_ligand_id = ligand.id
                data["ligand"] = ligand.model_dump(mode="json")
                actions.append(
                    AgentAction(
                        tool="prepare_ligand_input",
                        status="completed",
                        message=f"Stored ligand '{ligand.name}' from SMILES input.",
                        data={"ligand_id": ligand.id},
                    )
                )
            except Exception as exc:
                actions.append(
                    AgentAction(
                        tool="prepare_ligand_input",
                        status="failed",
                        message=str(exc),
                    )
                )

        ligand_name = request.ligand_name or (llm_plan or {}).get("ligand_name") or extract_ligand_name(message)
        if not ligand_smiles and ligand_name and ("store_ligand" in plan_intents or extract_ligand_name(message)):
            try:
                ligand = self.ligand_service.create_from_pubchem_name(str(ligand_name))
                context.active_ligand_id = ligand.id
                data["ligand"] = ligand.model_dump(mode="json")
                actions.append(
                    AgentAction(
                        tool="lookup_ligand_pubchem",
                        status="completed",
                        message=f"Fetched ligand '{ligand.name}' from PubChem and stored its SMILES.",
                        data={"ligand_id": ligand.id, "source": ligand.metadata.get("source_url")},
                    )
                )
            except Exception as exc:
                actions.append(
                    AgentAction(
                        tool="lookup_ligand_pubchem",
                        status="failed",
                        message=str(exc),
                    )
                )

        protein_query = normalize_protein_query((llm_plan or {}).get("protein_query")) or extract_protein_query(message)
        should_fetch = (
            "fetch_protein" in plan_intents
            or wants_fetch(message)
            or (protein_query is not None and not context.active_protein_id)
        )
        if should_fetch and protein_query:
            try:
                fetch_result = fetch_protein_structure(self.protein_service, protein_query)
                context.active_protein_id = fetch_result.protein.id
                context.last_candidates = fetch_result.candidates
                data["protein"] = fetch_result.protein.model_dump(mode="json")
                data["candidates"] = [candidate.model_dump(mode="json") for candidate in fetch_result.candidates]
                actions.append(
                    AgentAction(
                        tool="fetch_protein_structure",
                        status="completed",
                        message=fetch_result.message,
                        data={
                            "protein_id": fetch_result.protein.id,
                            "pdb_id": fetch_result.protein.pdb_id,
                        },
                    )
                )
                actions.append(
                    AgentAction(
                        tool="visualize_structure",
                        status="completed",
                        message="Structure is ready for the 3D viewer.",
                        data=visualize_structure(fetch_result.protein),
                    )
                )
            except Exception as exc:
                actions.append(
                    AgentAction(
                        tool="fetch_protein_structure",
                        status="failed",
                        message=str(exc),
                    )
                )
        elif wants_fetch(message) and not protein_query:
            actions.append(
                AgentAction(
                    tool="fetch_protein_structure",
                    status="needs_input",
                    message="Tell me a PDB ID, gene, or protein name to fetch.",
                )
            )

        if "list_candidate_ligands" in plan_intents or wants_ligand_list(message):
            actions.append(
                AgentAction(
                    tool="list_candidate_ligands",
                    status="completed",
                    message=(
                        "This MVP does not rank scientific candidate ligands yet. For pipeline testing, "
                        "you can paste a known SMILES string or upload SDF/MOL2/PDBQT. Future ChEMBL/PubChem "
                        "integration should separate real candidate selection from demo inputs."
                    ),
                    data={
                        "example_smiles": [
                            {"name": "Aspirin control example", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
                            {"name": "Caffeine control example", "smiles": "Cn1cnc2c1c(=O)n(C)c(=O)n2C"},
                        ]
                    },
                )
            )

        should_run_docking = "run_docking" in plan_intents or wants_run_docking(message)
        should_prepare = "prepare_docking" in plan_intents or wants_prepare(message)
        if should_prepare and not should_run_docking:
            job = self._prepare_current_context(context, request)
            if job:
                data["job"] = job.model_dump(mode="json")
                context.last_job_id = job.id
                actions.append(
                    AgentAction(
                        tool="prepare_protein_for_docking",
                        status="completed" if job.status == "completed" else "failed",
                        message=self._job_summary(job),
                        data={"job_id": job.id, "status": job.status},
                    )
                )
            else:
                actions.append(
                    AgentAction(
                        tool="prepare_protein_for_docking",
                        status="needs_input",
                        message="Fetch or select a protein first. A ligand is optional for protein-only preparation.",
                    )
                )

        if should_run_docking:
            job_action, job = self._run_current_context(context, request)
            actions.append(job_action)
            if job:
                context.last_job_id = job.id
                data["job"] = job.model_dump(mode="json")

        if "show_results" in plan_intents or wants_results(message):
            result_action = self._summarize_results(context, data)
            actions.append(result_action)

        if "download_pdb" in plan_intents or wants_download(message):
            actions.append(self._download_hint(context))

        if "chat" in plan_intents and self._has_no_visible_workflow_actions(actions):
            actions.append(self._chat_response(message, llm_plan))

        if not [action for action in actions if action.tool != "gemini_intent_planner"]:
            actions.append(self._chat_response(message, llm_plan))

        self.db.save_session(session_id, context)
        return AgentResponse(
            session_id=session_id,
            message=self._compose_message(actions),
            actions=actions,
            context=context,
            data=data,
        )

    def status(self) -> dict[str, object]:
        if not self.llm_planner:
            return {
                "agent_mode": "deterministic_router",
                "gemini": {
                    "provider": "gemini",
                    "enabled": False,
                    "api_key_configured": False,
                    "model": None,
                    "fallback": "deterministic_router",
                },
            }
        gemini_status = self.llm_planner.status()
        return {
            "agent_mode": "gemini_planner_plus_router" if gemini_status["enabled"] else "deterministic_router",
            "gemini": gemini_status,
        }

    def _plan_with_gemini(
        self,
        request: AgentRequest,
        context: SessionContext,
        actions: list[AgentAction],
    ) -> dict[str, object] | None:
        if not self.llm_planner or not self.llm_planner.enabled:
            return None

    @staticmethod
    def _has_no_visible_workflow_actions(actions: list[AgentAction]) -> bool:
        workflow_tools = {
            "prepare_ligand_input",
            "fetch_protein_structure",
            "visualize_structure",
            "list_candidate_ligands",
            "prepare_protein_for_docking",
            "run_docking",
            "parse_docking_results",
            "download_pdb_file",
            "lookup_ligand_pubchem",
        }
        return not any(action.tool in workflow_tools for action in actions)

    @staticmethod
    def _chat_response(message: str, llm_plan: dict[str, object] | None) -> AgentAction:
        assistant_message = (llm_plan or {}).get("assistant_message")
        if isinstance(assistant_message, str) and assistant_message.strip():
            text = assistant_message.strip()
        elif is_casual_message(message):
            text = (
                "Merhaba, ben Bıdık. Protein arama, ligand hazırlama ve docking akışında yardımcı olurum. "
                "İstersen direkt 'EGFR yapısını getir' ya da 'P53 fetch' diye yazabilirsin."
            )
        else:
            text = (
                "Seni anladım, ama bunu hangi biyoinformatik adıma çevireceğimden emin olamadım. "
                "Bir protein adı/PDB ID yazarsan yapıyı getirebilirim; örnek: 'EGFR getir' veya '1CRN fetch'."
            )
        return AgentAction(
            tool="chat",
            status="completed",
            message=text,
        )
        try:
            plan = self.llm_planner.plan(request, context)
            actions.append(
                AgentAction(
                    tool="gemini_intent_planner",
                    status="completed",
                    message="Gemini planner produced a workflow plan.",
                    data=plan,
                )
            )
            return plan
        except Exception as exc:
            actions.append(
                AgentAction(
                    tool="gemini_intent_planner",
                    status="skipped",
                    message="Gemini planner was unavailable; using deterministic router fallback.",
                    data={"error": str(exc)},
                )
            )
            return None

    def _prepare_current_context(
        self,
        context: SessionContext,
        request: AgentRequest,
    ) -> DockingJob | None:
        if not context.active_protein_id:
            return None
        protein = self.protein_service.get(context.active_protein_id)
        ligand = self.ligand_service.get(context.active_ligand_id) if context.active_ligand_id else None
        return prepare_inputs_for_docking(
            self.docking_service,
            protein,
            ligand,
            request.docking_parameters,
        )

    def _run_current_context(
        self,
        context: SessionContext,
        request: AgentRequest,
    ) -> tuple[AgentAction, DockingJob | None]:
        if not context.active_protein_id:
            return (
                AgentAction(
                    tool="run_docking",
                    status="needs_input",
                    message="Fetch or select a protein before running docking.",
                ),
                None,
            )
        if not context.active_ligand_id:
            return (
                AgentAction(
                    tool="run_docking",
                    status="needs_input",
                    message="Provide a ligand as SMILES or upload a ligand file before running docking.",
                ),
                None,
            )

        protein = self.protein_service.get(context.active_protein_id)
        ligand = self.ligand_service.get(context.active_ligand_id)
        job = run_docking(self.docking_service, protein, ligand, request.docking_parameters)
        return (
            AgentAction(
                tool="run_docking",
                status="completed" if job.status == "completed" else "failed",
                message=self._job_summary(job),
                data=parse_docking_results(job),
            ),
            job,
        )

    def _summarize_results(self, context: SessionContext, data: dict[str, object]) -> AgentAction:
        if not context.last_job_id:
            return AgentAction(
                tool="parse_docking_results",
                status="needs_input",
                message="No docking or preparation job is active in this session yet.",
            )
        job = self.docking_service.get_job(context.last_job_id)
        data["job"] = job.model_dump(mode="json")
        parsed = parse_docking_results(job)
        best = parsed.get("best_score")
        if best:
            message = (
                f"Best parsed docking score: {best['affinity_kcal_mol']} kcal/mol "
                f"from mode {best['mode']}."
            )
        elif job.error:
            message = f"The job did not produce docking scores. Last error: {job.error}"
        else:
            message = "The job has no parsed docking scores yet."
        return AgentAction(
            tool="parse_docking_results",
            status="completed" if job.status == "completed" else "failed",
            message=message,
            data=parsed,
        )

    def _download_hint(self, context: SessionContext) -> AgentAction:
        if not context.active_protein_id:
            return AgentAction(
                tool="download_pdb_file",
                status="needs_input",
                message="Fetch or select a protein before downloading the PDB file.",
            )
        protein = self.protein_service.get(context.active_protein_id)
        return AgentAction(
            tool="download_pdb_file",
            status="completed",
            message=f"PDB file is available from /api/proteins/{protein.id}/download.",
            data={"protein_id": protein.id, "pdb_path": protein.pdb_path},
        )

    @staticmethod
    def _job_summary(job: DockingJob) -> str:
        if job.status == "completed" and job.scores:
            best = min(job.scores, key=lambda score: score.affinity_kcal_mol)
            return f"Docking completed. Best parsed Vina score: {best.affinity_kcal_mol} kcal/mol."
        if job.status == "completed":
            return "Preparation completed. No docking scores were expected for this step."
        return f"Workflow failed: {job.error or 'unknown error'}"

    @staticmethod
    def _compose_message(actions: list[AgentAction]) -> str:
        visible_actions = [action for action in actions if action.tool != "gemini_intent_planner"]
        failed = [action for action in visible_actions if action.status == "failed"]
        needs_input = [action for action in visible_actions if action.status == "needs_input"]
        if failed:
            return failed[-1].message
        if needs_input:
            return needs_input[-1].message
        return " ".join(action.message for action in visible_actions if action.message)
