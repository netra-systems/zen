"""Supervisor Agent Module

This module provides the main Supervisor implementation that orchestrates sub-agents.
It has been refactored to use the consolidated supervisor for improved architecture
while maintaining backward compatibility.
"""

from app.logging_config import central_logger
from typing import Any, Dict, List, Optional
from app.agents.base import BaseSubAgent
from app.schemas import SubAgentLifecycle, WebSocketMessage, AgentStarted, SubAgentUpdate, AgentCompleted, SubAgentState
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.services.state_persistence_service import state_persistence_service
from starlette.websockets import WebSocketDisconnect

# Import the consolidated supervisor
try:
    from app.agents.supervisor_consolidated import SupervisorAgent as ConsolidatedSupervisor
    USE_CONSOLIDATED = True
except ImportError:
    USE_CONSOLIDATED = False
    # Import all the sub-agents for legacy implementation
    from app.agents.triage_sub_agent import TriageSubAgent
    from app.agents.data_sub_agent import DataSubAgent
    from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
    from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
    from app.agents.reporting_sub_agent import ReportingSubAgent

logger = central_logger.get_logger(__name__)

class Supervisor(BaseSubAgent):
    """Main Supervisor class with backward compatibility
    
    This class either delegates to the consolidated supervisor for improved functionality
    or falls back to the legacy implementation if the consolidated version is not available.
    """
    
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager, websocket_manager: any, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="Supervisor", description="The supervisor agent that orchestrates the sub-agents.")
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.tool_dispatcher = tool_dispatcher
        self.thread_id = None  # Will be set by AgentService
        self.user_id = None  # Will be set by AgentService
        
        if USE_CONSOLIDATED:
            # Use the improved consolidated supervisor
            self._impl = ConsolidatedSupervisor(
                db_session=db_session,
                llm_manager=llm_manager,
                websocket_manager=websocket_manager,
                tool_dispatcher=tool_dispatcher
            )
            logger.info("Using consolidated supervisor implementation")
        else:
            # Legacy implementation
            self.sub_agents: List[BaseSubAgent] = [
                TriageSubAgent(llm_manager, self.tool_dispatcher),
                DataSubAgent(llm_manager, self.tool_dispatcher),
                OptimizationsCoreSubAgent(llm_manager, self.tool_dispatcher),
                ActionsToMeetGoalsSubAgent(llm_manager, self.tool_dispatcher),
                ReportingSubAgent(llm_manager, self.tool_dispatcher),
            ]
            self.run_states = {}
            self.state_persistence = state_persistence_service
            self._impl = None
            logger.info("Using legacy supervisor implementation")

    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the supervisor's orchestration logic."""
        if self._impl and hasattr(self._impl, 'execute'):
            await self._impl.execute(state, run_id, stream_updates)
        else:
            # The supervisor doesn't use the standard execute pattern since it has its own run method
            # This is here to satisfy the abstract method requirement
            pass
    
    async def run(self, user_request: str, run_id: str, stream_updates: bool) -> DeepAgentState:
        """Run the supervisor workflow"""
        
        # Delegate to consolidated implementation if available
        if self._impl:
            self._impl.thread_id = self.thread_id
            self._impl.user_id = self.user_id
            return await self._impl.run(user_request, run_id, stream_updates)
        
        # Legacy implementation
        logger.info(f"Supervisor starting for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.RUNNING)
        self.run_states[run_id] = {"status": "running", "current_step": 0, "total_steps": len(self.sub_agents)}

        # Use user_id for WebSocket messages (run_id is used internally)
        ws_user_id = self.user_id if self.user_id else run_id

        if stream_updates:
            try:
                await self.websocket_manager.send_message(
                    ws_user_id,
                    WebSocketMessage(type="agent_started", payload=AgentStarted(run_id=run_id).model_dump()).model_dump()
                )
            except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                logger.info(f"WebSocket disconnected when sending agent_started: {e}")
                # Continue processing even if WebSocket is disconnected

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
            agent.user_id = ws_user_id  # Pass user_id to sub-agent
            
            agent.set_state(SubAgentLifecycle.RUNNING)
            if stream_updates:
                try:
                    sub_agent_state = SubAgentState(
                        messages=[],
                        next_node="",
                        lifecycle=agent.get_state()
                    )
                    await self.websocket_manager.send_message(
                        ws_user_id,
                        WebSocketMessage(
                            type="sub_agent_update",
                            payload=SubAgentUpdate(
                                sub_agent_name=agent.name,
                                state=sub_agent_state
                            ).model_dump()
                        ).model_dump()
                    )
                except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                    logger.debug(f"WebSocket disconnected when sending sub_agent_update: {e}")
            
            try:
                await agent.run(state, run_id, stream_updates)
            except WebSocketDisconnect as e:
                logger.info(f"WebSocket disconnected during {agent.name} execution: {e}")
                # Continue processing even if WebSocket is disconnected
                stream_updates = False  # Disable further streaming
            except Exception as e:
                self.logger.error(f"Error in {agent.name}: {e}")
                if stream_updates:
                    try:
                        await self.websocket_manager.send_error(
                            ws_user_id,
                            f"Error in {agent.name}: {str(e)}",
                            agent.name
                        )
                    except (WebSocketDisconnect, RuntimeError, ConnectionError):
                        logger.debug(f"WebSocket disconnected when sending error")
                        stream_updates = False  # Disable further streaming
                # Continue with next agent despite the error
                continue
            
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
                try:
                    sub_agent_state = SubAgentState(
                        messages=[],
                        next_node="",
                        lifecycle=agent.get_state()
                    )
                    await self.websocket_manager.send_message(
                        ws_user_id,
                        WebSocketMessage(
                            type="sub_agent_update",
                            payload=SubAgentUpdate(
                                sub_agent_name=agent.name,
                                state=sub_agent_state
                            ).model_dump()
                        ).model_dump()
                    )
                except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                    logger.debug(f"WebSocket disconnected when sending completion update: {e}")
                    stream_updates = False  # Disable further streaming
                
                # Send sub_agent_completed message
                if stream_updates:
                    try:
                        await self.websocket_manager.send_message(
                            ws_user_id,
                            WebSocketMessage(
                                type="sub_agent_completed",
                                payload={
                                    "sub_agent_name": agent.name,
                                    "result": state.model_dump()
                                }
                            ).model_dump()
                        )
                    except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                        logger.debug(f"WebSocket disconnected when sending sub_agent_completed: {e}")
                        stream_updates = False  # Disable further streaming

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
            try:
                await self.websocket_manager.send_message(
                    ws_user_id,
                    WebSocketMessage(type="agent_completed", payload=AgentCompleted(run_id=run_id, result=state.model_dump()).model_dump()).model_dump()
                )
            except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                logger.info(f"WebSocket disconnected when sending agent_completed: {e}")
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