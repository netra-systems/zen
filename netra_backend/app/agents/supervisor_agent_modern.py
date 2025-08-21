"""Modern Supervisor Agent Implementation.

Fully compliant with unified spec requirements.
Business Value: Foundation for all AI optimization workflows and value creation.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher

# Import modular components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.lifecycle_manager import SupervisorLifecycleManager
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.circuit_breaker_integration import SupervisorCircuitBreakerIntegration
from netra_backend.app.agents.supervisor.comprehensive_observability import SupervisorObservability
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine

logger = central_logger.get_logger(__name__)


class ModernSupervisorAgent(BaseExecutionInterface, BaseSubAgent):
    """Modern supervisor agent with unified spec compliance.
    
    Implements complete supervisor pattern with:
    - Proper agent lifecycle management
    - Circuit breaker protection
    - Comprehensive observability
    - Real-time WebSocket updates
    """
    
    def __init__(self, 
                 db_session: AsyncSession,
                 llm_manager: LLMManager,
                 websocket_manager,
                 tool_dispatcher: ToolDispatcher):
        # Initialize base classes
        BaseSubAgent.__init__(self, llm_manager, name="ModernSupervisor", 
                            description="Modern supervisor agent with unified spec compliance")
        BaseExecutionInterface.__init__(self, "ModernSupervisor", websocket_manager)
        
        # Core dependencies
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.tool_dispatcher = tool_dispatcher
        
        # Initialize modular components
        self._init_core_components()
        self._init_monitoring_components()
        
        # Execution state
        self._execution_lock = asyncio.Lock()
    
    def _init_core_components(self) -> None:
        """Initialize core supervisor components."""
        self.agent_registry = AgentRegistry(self.llm_manager, self.tool_dispatcher)
        self.agent_registry.set_websocket_manager(self.websocket_manager)
        self.agent_registry.register_default_agents()
        
        self.lifecycle_manager = SupervisorLifecycleManager()
        self.execution_engine = ExecutionEngine(self.agent_registry, self.websocket_manager)
        self.workflow_orchestrator = WorkflowOrchestrator(
            self.agent_registry, self.execution_engine, self.websocket_manager
        )
    
    def _init_monitoring_components(self) -> None:
        """Initialize monitoring and reliability components."""
        self.circuit_breaker_integration = SupervisorCircuitBreakerIntegration()
        self.observability = SupervisorObservability()
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions per unified spec."""
        return await self.lifecycle_manager.validate_entry_conditions(context)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core supervisor orchestration logic."""
        # Start observability tracking
        self.observability.start_workflow_trace(context)
        
        try:
            # Execute workflow with circuit breaker protection
            results = await self._execute_protected_workflow(context)
            
            # Check exit conditions
            final_result = results[-1] if results else ExecutionResult(
                success=False, status="failed", error="No workflow results"
            )
            
            await self.lifecycle_manager.check_exit_conditions(context, final_result)
            
            return {
                "supervisor_result": "completed" if final_result.success else "failed",
                "workflow_results": [r.__dict__ for r in results],
                "total_steps": len(results)
            }
        
        except Exception as e:
            self.observability.record_agent_error("supervisor", str(e))
            raise
        
        finally:
            # Complete observability tracking
            final_result = ExecutionResult(success=True, status="completed")
            self.observability.complete_workflow_trace(context, final_result)
    
    async def _execute_protected_workflow(self, context: ExecutionContext):
        """Execute workflow with circuit breaker protection."""
        async def workflow_func():
            return await self.workflow_orchestrator.execute_standard_workflow(context)
        
        result = await self.circuit_breaker_integration.execute_with_circuit_protection(
            context, workflow_func
        )
        
        if hasattr(result, 'result') and result.result:
            return result.result
        return []
    
    async def execute(self, state: DeepAgentState, 
                     run_id: str, stream_updates: bool) -> None:
        """Execute supervisor workflow with modern patterns."""
        context = self._create_execution_context(state, run_id, stream_updates)
        
        async with self._execution_lock:
            self.lifecycle_manager.track_active_context(context)
            
            try:
                await self.lifecycle_manager.execute_lifecycle_hooks(
                    "pre_execution", context
                )
                
                result = await self._execute_with_error_handling(context)
                
                await self.lifecycle_manager.execute_lifecycle_hooks(
                    "post_execution", context, result=result
                )
                
            finally:
                self.lifecycle_manager.clear_active_context(run_id)
    
    def _create_execution_context(self, state: DeepAgentState, 
                                 run_id: str, stream_updates: bool) -> ExecutionContext:
        """Create execution context for supervisor."""
        return ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=stream_updates,
            thread_id=getattr(state, 'chat_thread_id', run_id),
            user_id=getattr(state, 'user_id', 'default_user'),
            start_time=datetime.utcnow(),
            metadata={"description": self.description}
        )
    
    async def _execute_with_error_handling(self, context: ExecutionContext) -> ExecutionResult:
        """Execute with comprehensive error handling."""
        try:
            result_data = await self.execute_core_logic(context)
            return ExecutionResult(
                success=True,
                status="completed",
                result=result_data,
                execution_time_ms=0.0  # Will be calculated by observability
            )
        except Exception as e:
            self.observability.record_agent_error(self.name, str(e))
            await self.lifecycle_manager.execute_lifecycle_hooks(
                "on_error", context, error=e
            )
            raise
    
    async def run(self, user_prompt: str, thread_id: str, 
                  user_id: str, run_id: str) -> DeepAgentState:
        """Legacy compatibility method."""
        # Create state from parameters
        state = DeepAgentState()
        state.user_request = user_prompt
        state.chat_thread_id = thread_id
        state.user_id = user_id
        
        # Execute using modern pattern
        await self.execute(state, run_id, stream_updates=True)
        
        return state
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        return {
            "supervisor_health": self.circuit_breaker_integration.get_health_summary(),
            "observability_metrics": self.observability.get_metrics_snapshot(),
            "active_contexts": len(self.lifecycle_manager.get_active_contexts()),
            "registered_agents": len(self.agent_registry.agents),
            "workflow_definition": self.workflow_orchestrator.get_workflow_definition()
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return self.observability.get_metrics_snapshot()
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return self.circuit_breaker_integration.get_circuit_breaker_status()
    
    def register_agent(self, name: str, agent: BaseSubAgent) -> None:
        """Register a sub-agent."""
        self.agent_registry.register(name, agent)
    
    def register_lifecycle_hook(self, event: str, handler) -> None:
        """Register lifecycle event hook."""
        self.lifecycle_manager.register_lifecycle_hook(event, handler)
