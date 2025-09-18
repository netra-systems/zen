"""Base Execution Engine with Strategy Pattern Support

Core execution orchestration with standardized patterns:
- Error handling and recovery
- Retry logic with exponential backoff
- Circuit breaker integration
- State management
- WebSocket notifications
- Strategy pattern support (Sequential, Pipeline, Parallel)
- Extension hooks for agent-specific logic

Business Value: Eliminates 40+ duplicate execution patterns.
SSOT for all agent execution workflows.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Protocol

if TYPE_CHECKING:
    from typing import Protocol
    
    class AgentExecutionProtocol(Protocol):
        """Protocol for agent execution methods."""
        async def validate_preconditions(self, context: 'ExecutionContext') -> bool: ...
        async def execute_core_logic(self, context: 'ExecutionContext') -> Dict[str, Any]: ...
        async def send_status_update(self, context: 'ExecutionContext', status: str, message: str) -> None: ...

from netra_backend.app.agents.base.errors import (
    AgentExecutionError,
)
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult,
)
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability import ReliabilityManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionStrategy(Enum):
    """Execution strategy patterns."""
    SEQUENTIAL = "sequential"  # Execute phases one after another
    PIPELINE = "pipeline"      # Execute phases with data flowing between them
    PARALLEL = "parallel"      # Execute phases concurrently where possible


class ExecutionPhase(Protocol):
    """Protocol for execution phases."""
    name: str
    dependencies: List[str]
    
    async def execute(self, context: 'ExecutionContext', previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute this phase."""
        ...


class BaseExecutionPhase:
    """Base implementation for execution phases."""
    
    def __init__(self, name: str, dependencies: Optional[List[str]] = None):
        self.name = name
        self.dependencies = dependencies or []
    
    async def execute(self, context: 'ExecutionContext', previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute this phase - to be implemented by subclasses."""
        raise NotImplementedError(f"Phase {self.name} must implement execute method")


class ExecutionStrategyHandler(ABC):
    """Abstract handler for execution strategies."""
    
    @abstractmethod
    async def execute_phases(self, phases: List[ExecutionPhase], context: 'ExecutionContext') -> Dict[str, Any]:
        """Execute phases according to strategy."""
        pass


class SequentialStrategyHandler(ExecutionStrategyHandler):
    """Sequential execution strategy - one phase after another."""
    
    async def execute_phases(self, phases: List[ExecutionPhase], context: 'ExecutionContext') -> Dict[str, Any]:
        """Execute phases sequentially."""
        results = {}
        
        for phase in phases:
            try:
                await self._notify_phase_start(phase, context)
                phase_result = await phase.execute(context, results)
                results[phase.name] = phase_result
                await self._notify_phase_complete(phase, context)
            except Exception as e:
                await self._notify_phase_error(phase, context, e)
                raise
        
        return results
    
    async def _notify_phase_start(self, phase: ExecutionPhase, context: 'ExecutionContext') -> None:
        """Notify phase start."""
        if hasattr(context, 'websocket_manager') and context.websocket_manager:
            await context.websocket_manager.send_tool_executing(
                context.run_id, context.agent_name, phase.name, {"phase": phase.name}
            )
    
    async def _notify_phase_complete(self, phase: ExecutionPhase, context: 'ExecutionContext') -> None:
        """Notify phase completion."""
        if hasattr(context, 'websocket_manager') and context.websocket_manager:
            await context.websocket_manager.send_tool_completed(
                context.run_id, context.agent_name, phase.name, {"phase": phase.name}
            )
    
    async def _notify_phase_error(self, phase: ExecutionPhase, context: 'ExecutionContext', error: Exception) -> None:
        """Notify phase error."""
        if hasattr(context, 'websocket_manager') and context.websocket_manager:
            await context.websocket_manager.send_agent_error(
                context.run_id, context.agent_name, f"Phase {phase.name} failed: {str(error)}"
            )


class PipelineStrategyHandler(ExecutionStrategyHandler):
    """Pipeline execution strategy - phases with data flow."""
    
    async def execute_phases(self, phases: List[ExecutionPhase], context: 'ExecutionContext') -> Dict[str, Any]:
        """Execute phases in pipeline with dependency resolution."""
        executed_phases = set()
        results = {}
        phases_to_execute = phases.copy()
        
        while phases_to_execute:
            ready_phases = self._get_ready_phases(phases_to_execute, executed_phases)
            
            if not ready_phases:
                raise RuntimeError("Circular dependency or unsatisfied dependency in phases")
            
            for phase in ready_phases:
                try:
                    await self._notify_phase_start(phase, context)
                    phase_result = await phase.execute(context, results)
                    results[phase.name] = phase_result
                    executed_phases.add(phase.name)
                    phases_to_execute.remove(phase)
                    await self._notify_phase_complete(phase, context)
                except Exception as e:
                    await self._notify_phase_error(phase, context, e)
                    raise
        
        return results
    
    def _get_ready_phases(self, phases: List[ExecutionPhase], executed_phases: set) -> List[ExecutionPhase]:
        """Get phases ready to execute."""
        ready = []
        for phase in phases:
            if all(dep in executed_phases for dep in phase.dependencies):
                ready.append(phase)
        return ready
    
    async def _notify_phase_start(self, phase: ExecutionPhase, context: 'ExecutionContext') -> None:
        """Notify phase start."""
        if hasattr(context, 'websocket_manager') and context.websocket_manager:
            await context.websocket_manager.send_tool_executing(
                context.run_id, context.agent_name, phase.name, 
                {"phase": phase.name, "dependencies": phase.dependencies}
            )
    
    async def _notify_phase_complete(self, phase: ExecutionPhase, context: 'ExecutionContext') -> None:
        """Notify phase completion."""
        if hasattr(context, 'websocket_manager') and context.websocket_manager:
            await context.websocket_manager.send_tool_completed(
                context.run_id, context.agent_name, phase.name, {"phase": phase.name}
            )
    
    async def _notify_phase_error(self, phase: ExecutionPhase, context: 'ExecutionContext', error: Exception) -> None:
        """Notify phase error."""
        if hasattr(context, 'websocket_manager') and context.websocket_manager:
            await context.websocket_manager.send_agent_error(
                context.run_id, context.agent_name, f"Phase {phase.name} failed: {str(error)}"
            )


class ParallelStrategyHandler(ExecutionStrategyHandler):
    """Parallel execution strategy - concurrent phase execution."""
    
    async def execute_phases(self, phases: List[ExecutionPhase], context: 'ExecutionContext') -> Dict[str, Any]:
        """Execute phases in parallel where dependencies allow."""
        executed_phases = set()
        results = {}
        phases_remaining = phases.copy()
        
        while phases_remaining:
            ready_phases = self._get_ready_phases(phases_remaining, executed_phases)
            
            if not ready_phases:
                raise RuntimeError("Circular dependency or unsatisfied dependency in phases")
            
            # Execute ready phases in parallel
            tasks = []
            for phase in ready_phases:
                task = asyncio.create_task(self._execute_phase_with_notifications(phase, context, results))
                tasks.append((phase, task))
            
            # Wait for all tasks to complete
            for phase, task in tasks:
                try:
                    phase_result = await task
                    results[phase.name] = phase_result
                    executed_phases.add(phase.name)
                    phases_remaining.remove(phase)
                except Exception as e:
                    await self._notify_phase_error(phase, context, e)
                    # Cancel remaining tasks
                    for _, remaining_task in tasks:
                        if not remaining_task.done():
                            remaining_task.cancel()
                    raise
        
        return results
    
    async def _execute_phase_with_notifications(self, phase: ExecutionPhase, context: 'ExecutionContext', results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute phase with notifications."""
        await self._notify_phase_start(phase, context)
        try:
            result = await phase.execute(context, results)
            await self._notify_phase_complete(phase, context)
            return result
        except Exception as e:
            await self._notify_phase_error(phase, context, e)
            raise
    
    def _get_ready_phases(self, phases: List[ExecutionPhase], executed_phases: set) -> List[ExecutionPhase]:
        """Get phases ready to execute."""
        ready = []
        for phase in phases:
            if all(dep in executed_phases for dep in phase.dependencies):
                ready.append(phase)
        return ready
    
    async def _notify_phase_start(self, phase: ExecutionPhase, context: 'ExecutionContext') -> None:
        """Notify phase start."""
        if hasattr(context, 'websocket_manager') and context.websocket_manager:
            await context.websocket_manager.send_tool_executing(
                context.run_id, context.agent_name, phase.name, 
                {"phase": phase.name, "parallel": True}
            )
    
    async def _notify_phase_complete(self, phase: ExecutionPhase, context: 'ExecutionContext') -> None:
        """Notify phase completion."""
        if hasattr(context, 'websocket_manager') and context.websocket_manager:
            await context.websocket_manager.send_tool_completed(
                context.run_id, context.agent_name, phase.name, {"phase": phase.name}
            )
    
    async def _notify_phase_error(self, phase: ExecutionPhase, context: 'ExecutionContext', error: Exception) -> None:
        """Notify phase error."""
        if hasattr(context, 'websocket_manager') and context.websocket_manager:
            await context.websocket_manager.send_agent_error(
                context.run_id, context.agent_name, f"Phase {phase.name} failed: {str(error)}"
            )


class BaseExecutionEngine:
    """Orchestrates standardized agent execution workflow with strategy pattern support.
    
    Provides consistent execution patterns across all agent types with:
    - Pre-execution validation
    - Core logic execution
    - Error handling and recovery
    - Post-execution cleanup
    - Comprehensive monitoring
    - Strategy pattern support (Sequential, Pipeline, Parallel)
    - Extension hooks for agent-specific logic
    """
    
    def __init__(self, reliability_manager: Optional[ReliabilityManager] = None,
                 monitor: Optional[ExecutionMonitor] = None,
                 strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL):
        # DEPRECATION WARNING: This execution engine is being phased out in favor of UserExecutionEngine
        import warnings
        warnings.warn(
            "This execution engine is deprecated. Use UserExecutionEngine via ExecutionEngineFactory.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.reliability_manager = reliability_manager
        self.monitor = monitor or ExecutionMonitor()
        self.error_handler = ExecutionErrorHandler
        self.strategy = strategy
        self._strategy_handlers = {
            ExecutionStrategy.SEQUENTIAL: SequentialStrategyHandler(),
            ExecutionStrategy.PIPELINE: PipelineStrategyHandler(),
            ExecutionStrategy.PARALLEL: ParallelStrategyHandler()
        }
        self._phases: List[ExecutionPhase] = []
        self._pre_execution_hooks: List[Callable] = []
        self._post_execution_hooks: List[Callable] = []
        
    async def execute(self, agent: 'AgentExecutionProtocol', 
                     context: ExecutionContext) -> ExecutionResult:
        """Execute agent with full orchestration workflow."""
        await self._initialize_execution(context)
        result = await self._execute_with_monitoring(agent, context)
        await self._finalize_execution(context, result)
        return result
    
    async def execute_phases(self, context: ExecutionContext) -> ExecutionResult:
        """Execute agent using phase-based strategy pattern."""
        if not self._phases:
            raise ValueError("No phases configured for execution")
        
        await self._initialize_execution(context)
        
        try:
            # Run pre-execution hooks
            await self._run_pre_execution_hooks(context)
            
            # Execute phases using selected strategy
            strategy_handler = self._strategy_handlers[self.strategy]
            phase_results = await strategy_handler.execute_phases(self._phases, context)
            
            # Run post-execution hooks
            await self._run_post_execution_hooks(context, phase_results)
            
            # Create successful result
            result = self._create_success_result_from_phases(context, phase_results)
            
        except Exception as e:
            result = await self._handle_execution_failure(context, e)
        
        await self._finalize_execution(context, result)
        return result
    
    def add_phase(self, phase: ExecutionPhase) -> 'BaseExecutionEngine':
        """Add execution phase - builder pattern."""
        self._phases.append(phase)
        return self
    
    def add_phases(self, phases: List[ExecutionPhase]) -> 'BaseExecutionEngine':
        """Add multiple execution phases - builder pattern."""
        self._phases.extend(phases)
        return self
    
    def set_strategy(self, strategy: ExecutionStrategy) -> 'BaseExecutionEngine':
        """Set execution strategy - builder pattern."""
        self.strategy = strategy
        return self
    
    def add_pre_execution_hook(self, hook: Callable) -> 'BaseExecutionEngine':
        """Add pre-execution hook - builder pattern."""
        self._pre_execution_hooks.append(hook)
        return self
    
    def add_post_execution_hook(self, hook: Callable) -> 'BaseExecutionEngine':
        """Add post-execution hook - builder pattern."""
        self._post_execution_hooks.append(hook)
        return self
    
    async def _initialize_execution(self, context: ExecutionContext) -> None:
        """Initialize execution with status updates."""
        context.start_time = time.time()
        self.monitor.start_execution(context)
        
    async def _execute_with_monitoring(self, agent: 'AgentExecutionProtocol',
                                     context: ExecutionContext) -> ExecutionResult:
        """Execute with comprehensive monitoring."""
        try:
            return await self._execute_core_workflow(agent, context)
        except Exception as e:
            return await self._handle_execution_failure(context, e)
    
    async def _execute_core_workflow(self, agent: 'AgentExecutionProtocol',
                                   context: ExecutionContext) -> ExecutionResult:
        """Execute core workflow with reliability patterns."""
        if self.reliability_manager:
            return await self._execute_with_reliability(agent, context)
        return await self._execute_direct(agent, context)
    
    async def _execute_with_reliability(self, agent: 'AgentExecutionProtocol',
                                      context: ExecutionContext) -> ExecutionResult:
        """Execute with reliability manager (circuit breaker, retry)."""
        async def execute_func():
            return await self._execute_direct(agent, context)
        return await self.reliability_manager.execute_with_reliability(context, execute_func)
    
    async def _execute_direct(self, agent: 'AgentExecutionProtocol',
                            context: ExecutionContext) -> ExecutionResult:
        """Execute agent directly with basic error handling."""
        try:
            return await self._execute_agent_workflow(agent, context)
        except AgentExecutionError as e:
            return self._create_error_result(context, str(e))
        except Exception as e:
            error = await self.error_handler.handle_execution_error(e, context)
            # Wrap AgentError in ExecutionResult for compatibility
            if hasattr(error, 'message'):
                return self._create_error_result(context, error.message)
            return self._create_error_result(context, str(error))
    
    async def _execute_agent_workflow(self, agent: 'AgentExecutionProtocol',
                                    context: ExecutionContext) -> ExecutionResult:
        """Execute complete agent workflow."""
        await self._validate_and_notify(agent, context)
        result_data = await self._execute_and_measure(agent, context)
        return self._create_success_result(context, result_data)
    
    async def _validate_and_notify(self, agent: 'AgentExecutionProtocol',
                                 context: ExecutionContext) -> None:
        """Validate preconditions and send status update."""
        if not await agent.validate_preconditions(context):
            raise AgentExecutionError("Preconditions not met")
        await agent.send_status_update(context, "executing", "Starting execution")
    
    async def _execute_and_measure(self, agent: 'AgentExecutionProtocol',
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
            status=ExecutionStatus.COMPLETED,
            request_id=context.request_id,
            data=result_data,
            execution_time_ms=execution_time,
            metrics=self.monitor.get_execution_metrics(context)
        )
    
    def _create_error_result(self, context: ExecutionContext, 
                           error_message: str) -> ExecutionResult:
        """Create error execution result."""
        execution_time = self._calculate_execution_time(context)
        return ExecutionResult(
            status=ExecutionStatus.FAILED,
            request_id=context.request_id,
            error_message=error_message,
            execution_time_ms=execution_time,
            metrics=self.monitor.get_execution_metrics(context)
        )
    
    async def _handle_execution_failure(self, context: ExecutionContext,
                                      error: Exception) -> ExecutionResult:
        """Handle execution failure with structured error handling."""
        logger.error(f"Execution failed for {context.agent_name}: {error}")
        self.monitor.record_error(context, error)
        
        # Ensure we always return an ExecutionResult
        try:
            error_result = await self.error_handler.handle_execution_error(error, context)
            # If error_handler returns ExecutionResult, use it
            if hasattr(error_result, 'success'):
                return error_result
        except Exception as handler_error:
            logger.error(f"Error handler failed: {handler_error}")
        
        # Fallback: create our own ExecutionResult
        return self._create_error_result(context, str(error))
    
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
    
    async def _run_pre_execution_hooks(self, context: ExecutionContext) -> None:
        """Run pre-execution hooks."""
        for hook in self._pre_execution_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(context)
                else:
                    hook(context)
            except Exception as e:
                logger.error(f"Pre-execution hook failed: {e}")
                # Continue execution - hooks shouldn't break the main flow
    
    async def _run_post_execution_hooks(self, context: ExecutionContext, phase_results: Dict[str, Any]) -> None:
        """Run post-execution hooks."""
        for hook in self._post_execution_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(context, phase_results)
                else:
                    hook(context, phase_results)
            except Exception as e:
                logger.error(f"Post-execution hook failed: {e}")
                # Continue execution - hooks shouldn't break the main flow
    
    def _create_success_result_from_phases(self, context: ExecutionContext, 
                                          phase_results: Dict[str, Any]) -> ExecutionResult:
        """Create successful execution result from phase results."""
        execution_time = self._calculate_execution_time(context)
        return ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id=context.request_id,
            data=phase_results,
            execution_time_ms=execution_time,
            metrics=self.monitor.get_execution_metrics(context)
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get execution engine health status."""
        status = {
            "monitor": self.monitor.get_health_status(),
            "error_handler": self.error_handler.get_health_status(),
            "strategy": self.strategy.value,
            "phases_count": len(self._phases),
            "hooks_count": {
                "pre_execution": len(self._pre_execution_hooks),
                "post_execution": len(self._post_execution_hooks)
            }
        }
        if self.reliability_manager:
            status["reliability"] = self.reliability_manager.get_health_status()
        return status


class ExecutionWorkflowBuilder:
    """Builder for creating customized execution workflows with strategy pattern support.
    
    Allows agents to customize execution behavior while maintaining
    standardized patterns.
    """
    
    def __init__(self):
        self._phases: List[ExecutionPhase] = []
        self._strategy = ExecutionStrategy.SEQUENTIAL
        self._pre_execution_hooks = []
        self._post_execution_hooks = []
        self._reliability_manager: Optional[ReliabilityManager] = None
        self._monitor: Optional[ExecutionMonitor] = None
        
    def add_phase(self, phase: ExecutionPhase) -> 'ExecutionWorkflowBuilder':
        """Add execution phase."""
        self._phases.append(phase)
        return self
    
    def add_phases(self, phases: List[ExecutionPhase]) -> 'ExecutionWorkflowBuilder':
        """Add multiple execution phases."""
        self._phases.extend(phases)
        return self
    
    def set_strategy(self, strategy: ExecutionStrategy) -> 'ExecutionWorkflowBuilder':
        """Set execution strategy."""
        self._strategy = strategy
        return self
    
    def add_pre_execution_hook(self, hook: Callable) -> 'ExecutionWorkflowBuilder':
        """Add pre-execution hook."""
        self._pre_execution_hooks.append(hook)
        return self
    
    def add_post_execution_hook(self, hook: Callable) -> 'ExecutionWorkflowBuilder':
        """Add post-execution hook."""
        self._post_execution_hooks.append(hook)
        return self
    
    def set_reliability_manager(self, manager: ReliabilityManager) -> 'ExecutionWorkflowBuilder':
        """Set reliability manager."""
        self._reliability_manager = manager
        return self
    
    def set_monitor(self, monitor: ExecutionMonitor) -> 'ExecutionWorkflowBuilder':
        """Set execution monitor."""
        self._monitor = monitor
        return self
    
    def build(self) -> BaseExecutionEngine:
        """Build configured execution engine."""
        engine = BaseExecutionEngine(
            reliability_manager=self._reliability_manager,
            monitor=self._monitor,
            strategy=self._strategy
        )
        
        # Configure phases
        engine.add_phases(self._phases)
        
        # Configure hooks
        for hook in self._pre_execution_hooks:
            engine.add_pre_execution_hook(hook)
        for hook in self._post_execution_hooks:
            engine.add_post_execution_hook(hook)
        
        return engine


# Helper classes for common phase patterns

class LambdaExecutionPhase(BaseExecutionPhase):
    """Execution phase that wraps a lambda function."""
    
    def __init__(self, name: str, func: Callable, dependencies: Optional[List[str]] = None):
        super().__init__(name, dependencies)
        self.func = func
    
    async def execute(self, context: 'ExecutionContext', previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the wrapped function."""
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(context, previous_results)
        else:
            return self.func(context, previous_results)


class AgentMethodExecutionPhase(BaseExecutionPhase):
    """Execution phase that calls an agent method."""
    
    def __init__(self, name: str, agent: Any, method_name: str, dependencies: Optional[List[str]] = None):
        super().__init__(name, dependencies)
        self.agent = agent
        self.method_name = method_name
    
    async def execute(self, context: 'ExecutionContext', previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent method."""
        method = getattr(self.agent, self.method_name)
        
        if asyncio.iscoroutinefunction(method):
            return await method(context, previous_results)
        else:
            return method(context, previous_results)