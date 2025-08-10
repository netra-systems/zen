from app.logging_config import central_logger
from typing import Any, Dict, List, Optional
from app.agents.base import BaseSubAgent
from app.schemas import SubAgentLifecycle, WebSocketMessage, AgentStarted, SubAgentUpdate, AgentCompleted, SubAgentState
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.services.state_persistence_service import state_persistence_service

# Import all the sub-agents
from app.agents.triage_sub_agent import TriageSubAgent
from app.agents.data_sub_agent import DataSubAgent
from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.reporting_sub_agent import ReportingSubAgent

logger = central_logger.get_logger(__name__)

class Supervisor(BaseSubAgent):
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager, websocket_manager: any, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="Supervisor", description="The supervisor agent that orchestrates the sub-agents.")
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.tool_dispatcher = tool_dispatcher
        self.thread_id = None  # Will be set by AgentService
        self.user_id = None  # Will be set by AgentService
        self.sub_agents: List[BaseSubAgent] = [
            TriageSubAgent(llm_manager, self.tool_dispatcher),
            DataSubAgent(llm_manager, self.tool_dispatcher),
            OptimizationsCoreSubAgent(llm_manager, self.tool_dispatcher),
            ActionsToMeetGoalsSubAgent(llm_manager, self.tool_dispatcher),
            ReportingSubAgent(llm_manager, self.tool_dispatcher),
        ]
        self.run_states = {}
        self.state_persistence = state_persistence_service

    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the supervisor's orchestration logic."""
        # The supervisor doesn't use the standard execute pattern since it has its own run method
        # This is here to satisfy the abstract method requirement
        pass
    
    async def run(self, user_request: str, run_id: str, stream_updates: bool) -> DeepAgentState:
        logger.info(f"Supervisor starting for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.RUNNING)
        self.run_states[run_id] = {"status": "running", "current_step": 0, "total_steps": len(self.sub_agents)}

        if stream_updates:
            await self.websocket_manager.send_message(
                run_id,
                WebSocketMessage(type="agent_started", payload=AgentStarted(run_id=run_id).model_dump()).model_dump()
            )

        # Try to load existing state from previous runs in this thread
        state = None
        if self.thread_id and self.db_session:
            thread_context = await self.state_persistence.get_thread_context(self.thread_id)
            if thread_context and thread_context.get("current_run_id"):
                # Try to load state from the most recent run
                previous_state = await self.state_persistence.load_agent_state(
                    thread_context["current_run_id"],
                    self.db_session
                )
                if previous_state:
                    logger.info(f"Loaded previous state from run {thread_context['current_run_id']}")
                    # Start with previous state but update the user request
                    state = previous_state
                    state.user_request = user_request
        
        if not state:
            state = DeepAgentState(user_request=user_request)
        
        # Save initial state
        if self.thread_id and self.user_id and self.db_session:
            await self.state_persistence.save_agent_state(
                run_id=run_id,
                thread_id=self.thread_id,
                user_id=self.user_id,
                state=state,
                db_session=self.db_session
            )

        for i, agent in enumerate(self.sub_agents):
            self.run_states[run_id]["current_step"] = i + 1
            
            # Set the websocket manager for streaming updates
            agent.websocket_manager = self.websocket_manager
            
            agent.set_state(SubAgentLifecycle.RUNNING)
            if stream_updates:
                sub_agent_state = SubAgentState(
                    messages=[],
                    next_node="",
                    lifecycle=agent.get_state()
                )
                await self.websocket_manager.send_message(
                    run_id,
                    WebSocketMessage(
                        type="sub_agent_update",
                        payload=SubAgentUpdate(
                            sub_agent_name=agent.name,
                            state=sub_agent_state
                        ).model_dump()
                    ).model_dump()
                )
            
            await agent.run(state, run_id, stream_updates)
            
            # Save sub-agent result
            if self.thread_id and self.db_session:
                result_field_map = {
                    "TriageSubAgent": "triage_result",
                    "DataSubAgent": "data_result",
                    "OptimizationsCoreSubAgent": "optimizations_result",
                    "ActionsToMeetGoalsSubAgent": "action_plan_result",
                    "ReportingSubAgent": "report_result"
                }
                
                if agent.name in result_field_map:
                    result_data = getattr(state, result_field_map[agent.name])
                    if result_data:
                        await self.state_persistence.save_sub_agent_result(
                            run_id=run_id,
                            agent_name=agent.name,
                            result=result_data,
                            db_session=self.db_session
                        )
                
                # Save full state after each agent completes
                await self.state_persistence.save_agent_state(
                    run_id=run_id,
                    thread_id=self.thread_id,
                    user_id=self.user_id,
                    state=state,
                    db_session=self.db_session
                )

            agent.set_state(SubAgentLifecycle.COMPLETED)
            if stream_updates:
                sub_agent_state = SubAgentState(
                    messages=[],
                    next_node="",
                    lifecycle=agent.get_state()
                )
                await self.websocket_manager.send_message(
                    run_id,
                    WebSocketMessage(
                        type="sub_agent_update",
                        payload=SubAgentUpdate(
                            sub_agent_name=agent.name,
                            state=sub_agent_state
                        ).model_dump()
                    ).model_dump()
                )
                await self.websocket_manager.send_message(
                    run_id,
                    WebSocketMessage(
                        type="sub_agent_completed",
                        payload={
                            "sub_agent_name": agent.name,
                            "result": state.model_dump()
                        }
                    ).model_dump()
                )

        self.run_states[run_id]["status"] = "finished"
        self.set_state(SubAgentLifecycle.COMPLETED)
        
        # Save final state
        if self.thread_id and self.user_id and self.db_session:
            await self.state_persistence.save_agent_state(
                run_id=run_id,
                thread_id=self.thread_id,
                user_id=self.user_id,
                state=state,
                db_session=self.db_session
            )
        
        if stream_updates:
            await self.websocket_manager.send_message(
                run_id,
                WebSocketMessage(type="agent_completed", payload=AgentCompleted(run_id=run_id, result=state.model_dump()).model_dump()).model_dump()
            )
        logger.info(f"Supervisor finished for run_id: {run_id}")
        return state

    async def get_agent_state(self, run_id: str) -> Dict[str, Any]:
        # Try to get from memory first
        if run_id in self.run_states:
            return self.run_states[run_id]
        
        # Try to load from persistence
        if self.db_session:
            saved_state = await self.state_persistence.load_agent_state(run_id, self.db_session)
            if saved_state:
                return {
                    "status": "completed",
                    "state": saved_state.model_dump()
                }
        
        return {"status": "not_found"}

    async def shutdown(self):
        logger.info("Supervisor shutdown initiated.")
        self.set_state(SubAgentLifecycle.SHUTDOWN)
        
        # Shutdown all sub-agents
        for agent in self.sub_agents:
            try:
                await agent.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {agent.name}: {e}")
        
        logger.info("Supervisor shutdown complete.")