"""Refactored Supervisor Agent

Uses the orchestrator for better separation of concerns.
"""

from typing import Dict, Any, Optional, List
from app.logging_config import central_logger
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState
from app.agents.orchestration.orchestrator import (
    AgentOrchestrator, 
    AgentExecutionContext,
    ExecutionStrategy
)
from app.schemas import SubAgentLifecycle, WebSocketMessage, AgentStarted, AgentCompleted
from sqlalchemy.ext.asyncio import AsyncSession

logger = central_logger.get_logger(__name__)

class SupervisorAgent:
    """Supervisor agent with improved architecture"""
    
    def __init__(self, 
                 db_session: AsyncSession,
                 websocket_manager: Any,
                 state_persistence_service: Any):
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.state_persistence = state_persistence_service
        self.orchestrator = AgentOrchestrator()
        self.thread_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self._setup_orchestrator()
    
    def _setup_orchestrator(self) -> None:
        """Setup orchestrator with hooks"""
        self.orchestrator.register_hook("before_agent", self._before_agent_hook)
        self.orchestrator.register_hook("after_agent", self._after_agent_hook)
        self.orchestrator.register_hook("on_error", self._on_error_hook)
        self.orchestrator.register_hook("on_retry", self._on_retry_hook)
    
    def register_agent(self, name: str, agent: BaseSubAgent) -> None:
        """Register an agent with the orchestrator"""
        agent.websocket_manager = self.websocket_manager
        self.orchestrator.register_agent(name, agent)
    
    async def run(self, 
                 user_request: str, 
                 run_id: str, 
                 stream_updates: bool = True) -> DeepAgentState:
        """Run the supervisor workflow"""
        logger.info(f"Supervisor starting for run_id: {run_id}")
        
        if stream_updates:
            await self._send_start_notification(run_id)
        
        state = await self._initialize_state(user_request, run_id)
        
        context = AgentExecutionContext(
            agent_name="Supervisor",
            run_id=run_id,
            user_id=self.user_id or "",
            thread_id=self.thread_id or ""
        )
        
        try:
            pipeline = self._build_execution_pipeline()
            state = await self.orchestrator.execute_pipeline(state, pipeline, context)
            
            await self._save_final_state(run_id, state)
            
            if stream_updates:
                await self._send_completion_notification(run_id, state)
            
            logger.info(f"Supervisor completed for run_id: {run_id}")
            return state
            
        except Exception as e:
            logger.error(f"Supervisor failed for run_id {run_id}: {e}")
            
            if stream_updates:
                await self._send_error_notification(run_id, str(e))
            
            raise
    
    def _build_execution_pipeline(self) -> List[Dict[str, Any]]:
        """Build the agent execution pipeline"""
        return [
            {
                "agent": "TriageSubAgent",
                "condition": None
            },
            {
                "agent": "DataSubAgent",
                "condition": {
                    "type": "has_data",
                    "field": "triage_result"
                }
            },
            {
                "agent": "OptimizationsCoreSubAgent",
                "condition": {
                    "type": "has_data",
                    "field": "data_result"
                }
            },
            {
                "agent": "ActionsToMeetGoalsSubAgent",
                "condition": {
                    "type": "has_data",
                    "field": "optimizations_result"
                }
            },
            {
                "agent": "ReportingSubAgent",
                "condition": {
                    "type": "custom",
                    "function": lambda state: any([
                        state.triage_result,
                        state.data_result,
                        state.optimizations_result,
                        state.action_plan_result
                    ])
                }
            }
        ]
    
    async def _initialize_state(self, user_request: str, run_id: str) -> DeepAgentState:
        """Initialize or load state"""
        state = None
        
        if self.thread_id and self.db_session:
            thread_context = await self.state_persistence.get_thread_context(self.thread_id)
            
            if thread_context and thread_context.get("current_run_id"):
                state = await self.state_persistence.load_agent_state(
                    thread_context["current_run_id"],
                    self.db_session
                )
                
                if state:
                    logger.info(f"Loaded previous state from run {thread_context['current_run_id']}")
                    state.user_request = user_request
        
        if not state:
            state = DeepAgentState(user_request=user_request)
        
        if self.thread_id and self.user_id and self.db_session:
            await self.state_persistence.save_agent_state(
                run_id=run_id,
                thread_id=self.thread_id,
                user_id=self.user_id,
                state=state,
                db_session=self.db_session
            )
        
        return state
    
    async def _save_final_state(self, run_id: str, state: DeepAgentState) -> None:
        """Save the final state"""
        if self.thread_id and self.user_id and self.db_session:
            await self.state_persistence.save_agent_state(
                run_id=run_id,
                thread_id=self.thread_id,
                user_id=self.user_id,
                state=state,
                db_session=self.db_session
            )
    
    async def _before_agent_hook(self, context: AgentExecutionContext, state: DeepAgentState) -> None:
        """Hook called before agent execution"""
        logger.info(f"Starting agent: {context.agent_name}")
        
        if self.websocket_manager:
            await self.websocket_manager.send_message(
                context.run_id,
                {
                    "type": "agent_starting",
                    "agent": context.agent_name,
                    "timestamp": context.started_at.isoformat()
                }
            )
    
    async def _after_agent_hook(self, context: AgentExecutionContext, state: DeepAgentState) -> None:
        """Hook called after agent execution"""
        logger.info(f"Completed agent: {context.agent_name}")
        
        if self.db_session and context.agent_name:
            result_field_map = {
                "TriageSubAgent": "triage_result",
                "DataSubAgent": "data_result",
                "OptimizationsCoreSubAgent": "optimizations_result",
                "ActionsToMeetGoalsSubAgent": "action_plan_result",
                "ReportingSubAgent": "report_result"
            }
            
            if context.agent_name in result_field_map:
                result_data = getattr(state, result_field_map[context.agent_name])
                if result_data:
                    await self.state_persistence.save_sub_agent_result(
                        context.run_id,
                        context.agent_name,
                        result_data,
                        self.db_session
                    )
        
        if self.websocket_manager:
            await self.websocket_manager.send_message(
                context.run_id,
                {
                    "type": "agent_completed",
                    "agent": context.agent_name,
                    "duration": (context.completed_at - context.started_at).total_seconds() if context.completed_at else 0
                }
            )
    
    async def _on_error_hook(self, context: AgentExecutionContext, state: DeepAgentState) -> None:
        """Hook called on agent error"""
        logger.error(f"Agent {context.agent_name} failed: {context.error}")
        
        if self.websocket_manager:
            await self.websocket_manager.send_message(
                context.run_id,
                {
                    "type": "agent_error",
                    "agent": context.agent_name,
                    "error": context.error
                }
            )
    
    async def _on_retry_hook(self, context: AgentExecutionContext, state: DeepAgentState) -> None:
        """Hook called on agent retry"""
        logger.info(f"Retrying agent {context.agent_name}, attempt {context.retry_count}")
        
        if self.websocket_manager:
            await self.websocket_manager.send_message(
                context.run_id,
                {
                    "type": "agent_retry",
                    "agent": context.agent_name,
                    "retry_count": context.retry_count,
                    "max_retries": context.max_retries
                }
            )
    
    async def _send_start_notification(self, run_id: str) -> None:
        """Send start notification"""
        await self.websocket_manager.send_message(
            run_id,
            WebSocketMessage(
                type="agent_started",
                payload=AgentStarted(run_id=run_id).model_dump()
            ).model_dump()
        )
    
    async def _send_completion_notification(self, run_id: str, state: DeepAgentState) -> None:
        """Send completion notification"""
        await self.websocket_manager.send_message(
            run_id,
            WebSocketMessage(
                type="agent_completed",
                payload=AgentCompleted(run_id=run_id, result=state.model_dump()).model_dump()
            ).model_dump()
        )
    
    async def _send_error_notification(self, run_id: str, error: str) -> None:
        """Send error notification"""
        await self.websocket_manager.send_message(
            run_id,
            {
                "type": "agent_failed",
                "run_id": run_id,
                "error": error
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return self.orchestrator.get_execution_stats()