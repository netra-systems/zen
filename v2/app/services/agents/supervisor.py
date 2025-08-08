import logging
from typing import Any, Dict, List
from app.services.agents.base import BaseSubAgent
from app.schemas import AnalysisRequest, SubAgentLifecycle
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.connection_manager import manager

# Import all the sub-agents
from app.services.agents.triage_sub_agent import TriageSubAgent
from app.services.agents.data_sub_agent import DataSubAgent
from app.services.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.services.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.services.agents.reporting_sub_agent import ReportingSubAgent

logger = logging.getLogger(__name__)

class Supervisor(BaseSubAgent):
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager, websocket_manager: any):
        super().__init__(llm_manager)
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.sub_agents: List[BaseSubAgent] = [
            TriageSubAgent(llm_manager),
            DataSubAgent(llm_manager),
            OptimizationsCoreSubAgent(llm_manager),
            ActionsToMeetGoalsSubAgent(llm_manager),
            ReportingSubAgent(llm_manager),
        ]
        self.run_states = {}

    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        logger.info(f"Supervisor starting for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.RUNNING)
        self.run_states[run_id] = {"status": "running", "current_step": 0, "total_steps": len(self.sub_agents)}
        
        if stream_updates:
            await manager.broadcast_to_client(
                run_id,
                {
                    "event": "agent_started",
                    "data": self.run_states[run_id]
                }
            )

        current_data = input_data
        for i, agent in enumerate(self.sub_agents):
            self.run_states[run_id]["current_step"] = i + 1
            if stream_updates:
                await manager.broadcast_to_client(
                    run_id,
                    {
                        "event": "agent_step_started",
                        "data": {
                            "step": i + 1,
                            "agent": agent.__class__.__name__
                        }
                    }
                )
            
            current_data = await agent.run(current_data, run_id, stream_updates)

            if stream_updates:
                await manager.broadcast_to_client(
                    run_id,
                    {
                        "event": "agent_step_finished",
                        "data": {
                            "step": i + 1,
                            "agent": agent.__class__.__name__,
                            "result": current_data
                        }
                    }
                )

        self.run_states[run_id]["status"] = "finished"
        self.set_state(SubAgentLifecycle.COMPLETED)
        logger.info(f"Supervisor finished for run_id: {run_id}")
        return current_data

    async def get_agent_state(self, run_id: str) -> Dict[str, Any]:
        return self.run_states.get(run_id, {"status": "not_found"})

    async def shutdown(self):
        logger.info("Supervisor shutdown.")
        self.set_state(SubAgentLifecycle.SHUTDOWN)
