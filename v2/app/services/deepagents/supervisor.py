
import logging
from typing import Any, Dict, List
from app.services.deepagents.base import BaseAgent
from app.schemas import AnalysisRequest
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.connection_manager import manager

# Import all the sub-agents
from app.services.deepagents.triage_sub_agent import TriageSubAgent
from app.services.deepagents.data_sub_agent import DataSubAgent
from app.services.deepagents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.services.deepagents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.services.deepagents.reporting_sub_agent import ReportingSubAgent

logger = logging.getLogger(__name__)

class Supervisor(BaseAgent):
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager, websocket_manager: any):
        super().__init__(db_session, llm_manager, websocket_manager)
        self.sub_agents: List[BaseAgent] = [
            TriageSubAgent(db_session, llm_manager, websocket_manager),
            DataSubAgent(db_session, llm_manager, websocket_manager),
            OptimizationsCoreSubAgent(db_session, llm_manager, websocket_manager),
            ActionsToMeetGoalsSubAgent(db_session, llm_manager, websocket_manager),
            ReportingSubAgent(db_session, llm_manager, websocket_manager),
        ]
        self.run_states = {}

    async def run(self, analysis_request: AnalysisRequest, run_id: str, stream_updates: bool) -> Dict[str, Any]:
        logger.info(f"Supervisor starting for run_id: {run_id}")
        self.run_states[run_id] = {"status": "running", "current_step": 0, "total_steps": len(self.sub_agents)}
        
        if stream_updates:
            await manager.send_to_run(
                {
                    "run_id": run_id,
                    "event": "agent_started",
                    "data": self.run_states[run_id]
                }
            )

        current_data = analysis_request
        for i, agent in enumerate(self.sub_agents):
            self.run_states[run_id]["current_step"] = i + 1
            if stream_updates:
                await manager.send_to_run(
                    {
                        "run_id": run_id,
                        "event": "agent_step_started",
                        "data": {
                            "step": i + 1,
                            "agent": agent.__class__.__name__
                        }
                    }
                )
            
            # Pass the output of the previous agent to the next
            current_data = await agent.run(current_data, run_id, stream_updates)

            if stream_updates:
                await manager.send_to_run(
                    {
                        "run_id": run_id,
                        "event": "agent_step_finished",
                        "data": {
                            "step": i + 1,
                            "agent": agent.__class__.__name__,
                            "result": current_data
                        }
                    }
                )

        self.run_states[run_id]["status"] = "finished"
        logger.info(f"Supervisor finished for run_id: {run_id}")
        return current_data

    async def get_agent_state(self, run_id: str) -> Dict[str, Any]:
        return self.run_states.get(run_id, {"status": "not_found"})
