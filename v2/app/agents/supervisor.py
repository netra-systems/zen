import logging
from typing import Any, Dict, List
from app.agents.base import BaseSubAgent
from app.schemas import SubAgentLifecycle, WebSocketMessage, AgentStarted, SubAgentUpdate, AgentCompleted, SubAgentState
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState

# Import all the sub-agents
from app.agents.triage_sub_agent import TriageSubAgent
from app.agents.data_sub_agent import DataSubAgent
from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.reporting_sub_agent import ReportingSubAgent

logger = logging.getLogger(__name__)

class Supervisor(BaseSubAgent):
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager, websocket_manager: any, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="Supervisor", description="The supervisor agent that orchestrates the sub-agents.")
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.tool_dispatcher = tool_dispatcher
        self.sub_agents: List[BaseSubAgent] = [
            TriageSubAgent(llm_manager, self.tool_dispatcher),
            DataSubAgent(llm_manager, self.tool_dispatcher),
            OptimizationsCoreSubAgent(llm_manager, self.tool_dispatcher),
            ActionsToMeetGoalsSubAgent(llm_manager, self.tool_dispatcher),
            ReportingSubAgent(llm_manager, self.tool_dispatcher),
        ]
        self.run_states = {}

    async def run(self, user_request: str, run_id: str, stream_updates: bool) -> DeepAgentState:
        logger.info(f"Supervisor starting for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.RUNNING)
        self.run_states[run_id] = {"status": "running", "current_step": 0, "total_steps": len(self.sub_agents)}

        if stream_updates:
            await self.websocket_manager.send_to_client(
                run_id,
                WebSocketMessage(type="agent_started", payload=AgentStarted(run_id=run_id))
            )

        state = DeepAgentState(user_request=user_request)

        for i, agent in enumerate(self.sub_agents):
            self.run_states[run_id]["current_step"] = i + 1
            
            agent.set_state(SubAgentLifecycle.RUNNING)
            if stream_updates:
                sub_agent_state = SubAgentState(
                    messages=[],
                    next_node="",
                    lifecycle=agent.get_state()
                )
                await self.websocket_manager.send_to_client(
                    run_id,
                    WebSocketMessage(
                        type="sub_agent_update",
                        payload=SubAgentUpdate(
                            sub_agent_name=agent.name,
                            state=sub_agent_state
                        )
                    )
                )
            
            await agent.run(state, run_id, stream_updates)

            agent.set_state(SubAgentLifecycle.COMPLETED)
            if stream_updates:
                sub_agent_state = SubAgentState(
                    messages=[],
                    next_node="",
                    lifecycle=agent.get_state()
                )
                await self.websocket_manager.send_to_client(
                    run_id,
                    WebSocketMessage(
                        type="sub_agent_update",
                        payload=SubAgentUpdate(
                            sub_agent_name=agent.name,
                            state=sub_agent_state
                        )
                    )
                )
                await self.websocket_manager.send_to_client(
                    run_id,
                    WebSocketMessage(
                        type="sub_agent_completed",
                        payload={
                            "sub_agent_name": agent.name,
                            "result": state.dict()
                        }
                    )
                )

        self.run_states[run_id]["status"] = "finished"
        self.set_state(SubAgentLifecycle.COMPLETED)
        if stream_updates:
            await self.websocket_manager.send_to_client(
                run_id,
                WebSocketMessage(type="agent_completed", payload=AgentCompleted(run_id=run_id, result=state.dict()))
            )
        logger.info(f"Supervisor finished for run_id: {run_id}")
        return state

    async def get_agent_state(self, run_id: str) -> Dict[str, Any]:
        return self.run_states.get(run_id, {"status": "not_found"})

    async def shutdown(self):
        logger.info("Supervisor shutdown.")
        self.set_state(SubAgentLifecycle.SHUTDOWN)
