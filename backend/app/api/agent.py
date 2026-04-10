from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import AppServices, get_services
from app.models.schemas import AgentRequest, AgentResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/message", response_model=AgentResponse)
def handle_agent_message(
    request: AgentRequest,
    services: AppServices = Depends(get_services),
) -> AgentResponse:
    return services.agent.handle(request)


@router.get("/status")
def get_agent_status(
    services: AppServices = Depends(get_services),
) -> dict[str, object]:
    return services.agent.status()
