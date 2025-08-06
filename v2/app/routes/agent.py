
from fastapi import APIRouter, Depends, WebSocket, Request
from app.services.agent_service import AgentService
from app.services.streaming_agent.supervisor import StreamingAgentSupervisor
from app.db.models_clickhouse import AnalysisRequest
from app.auth_dependencies import ActiveUserDep, ActiveUserWsDep

router = APIRouter()

def get_agent_service(request: Request) -> AgentService:
    return request.app.state.agent_service

@router.post("/start_agent/{client_id}")
async def start_agent(
    analysis_request: AnalysisRequest,
    client_id: str,
    current_user: ActiveUserDep,
    agent_service: AgentService = Depends(get_agent_service),
):
    """
    Starts the agent.
    """
    try:
        return await agent_service.start_agent(analysis_request, client_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, current_user: ActiveUserWsDep):
    agent_service: AgentService = websocket.app.state.agent_service
    """
    Handles the WebSocket connection for the agent.
    """
    await agent_service.handle_websocket(websocket, run_id)
