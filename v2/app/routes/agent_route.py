from fastapi import APIRouter, Depends, HTTPException, Request
from app.agents.supervisor import Supervisor
from app.schemas import RequestModel
from typing import Dict, Any

router = APIRouter()

class AgentRoutes:

    def get_agent_supervisor(self, request: Request) -> Supervisor:
        return request.app.state.agent_supervisor

    @router.post("/run_agent")
    async def run_agent(
        self,
        request_model: RequestModel,
        supervisor: Supervisor = Depends(get_agent_supervisor),
    ) -> Dict[str, Any]:
        """
        Starts the agent to analyze the user's request.
        """
        try:
            result = await supervisor.run(
                request_model.model_dump(), 
                request_model.id, 
                stream_updates=True)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/{run_id}/status")
    async def get_agent_status(self, run_id: str, supervisor: Supervisor = Depends(get_agent_supervisor)) -> Dict[str, Any]:
        state = await supervisor.get_agent_state(run_id)
        if not state or state.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Agent run not found")
        
        return {
            "run_id": run_id,
            "status": state.get("status", "unknown"),
            "current_step": state.get("current_step", 0),
            "total_steps": state.get("total_steps", 0),
        }
