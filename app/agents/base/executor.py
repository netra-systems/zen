"""Base Execution Engine

Core execution orchestration with standardized patterns:
- Error handling and recovery
- Retry logic with exponential backoff
- Circuit breaker integration
- State management
- WebSocket notifications

Business Value: Eliminates 40+ duplicate execution patterns.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.base.interface import BaseExecutionInterface

from app.logging_config import central_logger
from app.agents.base.interface import (
    ExecutionContext, ExecutionResult, ExecutionStatus
)
from app.agents.base.errors import ExecutionErrorHandler, AgentExecutionError
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.reliability import ReliabilityManager

logger = central_logger.get_logger(__name__)


class BaseExecutionEngine:
    """Orchestrates standardized agent execution workflow.
    
    Provides consistent execution patterns across all agent types with:
    - Pre-execution validation
    - Core logic execution
    - Error handling and recovery
    - Post-execution cleanup
    - Comprehensive monitoring
    """
    
    def __init__(self, reliability_manager: Optional[ReliabilityManager] = None,
                 monitor: Optional[ExecutionMonitor] = None):
        self.reliability_manager = reliability_manager
        self.monitor = monitor or ExecutionMonitor()
        self.error_handler = ExecutionErrorHandler()
        
    async def execute(self, agent: 'BaseExecutionInterface', 
                     context: ExecutionContext) -> ExecutionResult:
        """Execute agent with full orchestration workflow."""
        await self._initialize_execution(context)
        result = await self._execute_with_monitoring(agent, context)
        await self._finalize_execution(context, result)
        return result
    
    async def _initialize_execution(self, context: ExecutionContext) -> None:
        """Initialize execution with status updates."""
        context.start_time = time.time()
        self.monitor.start_execution(context)
        
    async def _execute_with_monitoring(self, agent: 'BaseExecutionInterface',
                                     context: ExecutionContext) -> ExecutionResult:
        """Execute with comprehensive monitoring."""
        try:
            return await self._execute_core_workflow(agent, context)
        except Exception as e:
            return await self._handle_execution_failure(context, e)
    
    async def _execute_core_workflow(self, agent: 'BaseExecutionInterface',
                                   context: ExecutionContext) -> ExecutionResult:
        """Execute core workflow with reliability patterns."""
        if self.reliability_manager:
            return await self._execute_with_reliability(agent, context)
        return await self._execute_direct(agent, context)
    
    async def _execute_with_reliability(self, agent: 'BaseExecutionInterface',
                                      context: ExecutionContext) -> ExecutionResult:
        """Execute with reliability manager (circuit breaker, retry)."""
        execute_func = lambda: self._execute_direct(agent, context)
        return await self.reliability_manager.execute_with_reliability(context, execute_func)
    
    async def _execute_direct(self, agent: 'BaseExecutionInterface',
                            context: ExecutionContext) -> ExecutionResult:
        """Execute agent directly with basic error handling."""
        try:
            return await self._execute_agent_workflow(agent, context)
        except AgentExecutionError as e:
            return self._create_error_result(context, str(e))
        except Exception as e:
            return await self.error_handler.handle_unexpected_error(context, e)
    
    async def _execute_agent_workflow(self, agent: 'BaseExecutionInterface',
                                    context: ExecutionContext) -> ExecutionResult:
        """Execute complete agent workflow."""
        await self._validate_and_notify(agent, context)
        result_data = await self._execute_and_measure(agent, context)
        return self._create_success_result(context, result_data)
    
    async def _validate_and_notify(self, agent: 'BaseExecutionInterface',
                                 context: ExecutionContext) -> None:
        """Validate preconditions and send status update."""
        if not await agent.validate_preconditions(context):
            raise AgentExecutionError("Preconditions not met")
        await agent.send_status_update(context, "executing", "Starting execution")
    
    async def _execute_and_measure(self, agent: 'BaseExecutionInterface',
                                 context: ExecutionContext) -> Dict[str, Any]:
        """Execute core logic with performance measurement."""
        start_time = time.time()
        result_data = await agent.execute_core_logic(context)
        self.monitor.record_execution_time(context, time.time() - start_time)
        return result_data
    
    def _create_success_result(self, context: ExecutionContext,
                             result_data: Dict[str, Any]) -> ExecutionResult:
        """Create successful execution result."""
        execution_time = self._calculate_execution_time(context)
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED,
            result=result_data,
            execution_time_ms=execution_time,
            retry_count=context.retry_count,
            metrics=self.monitor.get_execution_metrics(context)
        )
    
    def _create_error_result(self, context: ExecutionContext, 
                           error_message: str) -> ExecutionResult:
        """Create error execution result."""
        execution_time = self._calculate_execution_time(context)
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=error_message,
            execution_time_ms=execution_time,
            retry_count=context.retry_count,
            metrics=self.monitor.get_execution_metrics(context)
        )
    
    async def _handle_execution_failure(self, context: ExecutionContext,
                                      error: Exception) -> ExecutionResult:
        """Handle execution failure with structured error handling."""
        logger.error(f"Execution failed for {context.agent_name}: {error}")
        self.monitor.record_error(context, error)
        return await self.error_handler.handle_execution_error(context, error)
    
    async def _finalize_execution(self, context: ExecutionContext,
                                result: ExecutionResult) -> None:
        """Finalize execution with cleanup and notifications."""
        self.monitor.complete_execution(context, result)
        await self._send_completion_update(context, result)
    
    async def _send_completion_update(self, context: ExecutionContext,
                                    result: ExecutionResult) -> None:
        """Send completion status update."""
        status = "completed" if result.success else "failed"
        message = self._create_completion_message(result)
        # Note: This would need the agent instance to send updates
        # For now, monitoring handles the final status
    
    def _create_completion_message(self, result: ExecutionResult) -> str:
        """Create completion message based on result."""
        if result.success:
            time_ms = result.execution_time_ms
            return f"Execution completed in {time_ms:.2f}ms"
        return f"Execution failed: {result.error}"
    
    def _calculate_execution_time(self, context: ExecutionContext) -> float:
        """Calculate execution time in milliseconds."""
        if not context.start_time:
            return 0.0
        return (time.time() - context.start_time) * 1000
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get execution engine health status."""
        status = {
            "monitor": self.monitor.get_health_status(),
            "error_handler": self.error_handler.get_health_status()
        }
        if self.reliability_manager:
            status["reliability"] = self.reliability_manager.get_health_status()
        return status


class ExecutionWorkflowBuilder:
    """Builder for creating customized execution workflows.
    
    Allows agents to customize execution behavior while maintaining
    standardized patterns.
    """
    
    def __init__(self):
        self._pre_execution_hooks = []
        self._post_execution_hooks = []
        self._error_handlers = []
        
    def add_pre_execution_hook(self, hook: Callable) -> 'ExecutionWorkflowBuilder':
        """Add pre-execution hook."""
        self._pre_execution_hooks.append(hook)
        return self
    
    def add_post_execution_hook(self, hook: Callable) -> 'ExecutionWorkflowBuilder':
        """Add post-execution hook."""
        self._post_execution_hooks.append(hook)
        return self
    
    def add_error_handler(self, handler: Callable) -> 'ExecutionWorkflowBuilder':
        """Add custom error handler."""
        self._error_handlers.append(handler)
        return self
    
    def build(self) -> BaseExecutionEngine:
        """Build configured execution engine."""
        engine = BaseExecutionEngine()
        # Configure engine with hooks (implementation would extend engine)
        return engine