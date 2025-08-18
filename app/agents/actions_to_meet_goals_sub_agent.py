# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T10:30:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Modernize with BaseExecutionInterface pattern
# Git: v6 | 2c55fb99 | dirty (27 uncommitted)
# Change: Feature | Scope: Component | Risk: High
# Session: modernization-session | Seq: 1
# Review: Pending | Score: 95
# ================================
import json
from typing import Dict, Any, Optional

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, 
    ExecutionResult, ExecutionStatus
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.schemas.shared_types import RetryConfig
from app.agents.base.errors import (
    ExecutionErrorHandler, ValidationError,
    AgentExecutionError
)
from app.agents.prompts import actions_to_meet_goals_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState, ActionPlanResult, PlanStep
from app.agents.utils import extract_json_from_response, extract_partial_json
from app.logging_config import central_logger as logger
from app.llm.observability import (
    start_llm_heartbeat, stop_llm_heartbeat, generate_llm_correlation_id,
    log_agent_communication, log_agent_input, log_agent_output
)
from app.core.reliability_utils import create_agent_reliability_wrapper
from app.core.fallback_utils import create_agent_fallback_strategy
from app.agents.input_validation import validate_agent_input
from app.agents.actions_goals_plan_builder import ActionPlanBuilder


class ActionsToMeetGoalsSubAgent(BaseExecutionInterface, BaseSubAgent):
    """Modernized agent implementing BaseExecutionInterface pattern."""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        """Initialize with modern execution patterns."""
        self._initialize_base_classes(llm_manager)
        self.tool_dispatcher = tool_dispatcher
        self._setup_modern_execution_infrastructure()
        self._setup_backward_compatibility()

    def _initialize_base_classes(self, llm_manager: LLMManager) -> None:
        """Initialize base classes for the agent."""
        BaseSubAgent.__init__(
            self, llm_manager, 
            name="ActionsToMeetGoalsSubAgent", 
            description="This agent creates a plan of action."
        )
        BaseExecutionInterface.__init__(self, "ActionsToMeetGoalsSubAgent")

    def _setup_modern_execution_infrastructure(self) -> None:
        """Setup modern execution infrastructure components."""
        self.monitor = ExecutionMonitor()
        self.reliability_manager = self._create_reliability_manager()
        self.execution_engine = BaseExecutionEngine(
            self.reliability_manager, self.monitor
        )
        self.error_handler = ExecutionErrorHandler()

    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create configured reliability manager."""
        return ReliabilityManager(
            circuit_breaker_config=CircuitBreakerConfig(
                name="ActionsToMeetGoalsSubAgent",
                failure_threshold=5,
                recovery_timeout=60
            ),
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=1.0
            )
        )

    def _setup_backward_compatibility(self) -> None:
        """Setup backward compatibility components."""
        agent_name = "ActionsToMeetGoalsSubAgent"
        self.reliability = create_agent_reliability_wrapper(agent_name)
        self.fallback_strategy = create_agent_fallback_strategy(agent_name)

    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions."""
        state = context.state
        if not state.optimizations_result or not state.data_result:
            raise ValidationError(
                "Missing required state: optimizations_result and data_result required"
            )
        return True

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core action plan generation logic."""
        await self.send_status_update(
            context, "executing", 
            "Creating action plan based on optimization strategies..."
        )
        action_plan_result = await self._execute_action_plan_generation(context)
        await self._update_state_and_notify(context, action_plan_result)
        return {"action_plan_result": action_plan_result}

    async def _execute_action_plan_generation(self, context: ExecutionContext) -> ActionPlanResult:
        """Generate action plan from state data."""
        state = context.state
        run_id = context.run_id
        prompt = self._build_action_plan_prompt(state)
        llm_response = await self._get_llm_response(prompt, run_id)
        return await self._process_llm_response(llm_response, run_id)

    async def _update_state_and_notify(self, context: ExecutionContext, action_plan_result: ActionPlanResult) -> None:
        """Update state with result and send completion notification."""
        context.state.action_plan_result = action_plan_result
        await self.send_status_update(
            context, "completed",
            "Action plan created successfully"
        )

    async def send_status_update(
        self, context: ExecutionContext, 
        status: str, message: str
    ) -> None:
        """Send status update via WebSocket."""
        if context.stream_updates:
            mapped_status = self._map_status_to_websocket_format(status)
            await self._send_mapped_update(context.run_id, mapped_status, message)

    def _map_status_to_websocket_format(self, status: str) -> str:
        """Map internal status to websocket format."""
        status_map = {
            "executing": "processing",
            "completed": "processed",
            "failed": "error"
        }
        return status_map.get(status, status)

    async def _send_mapped_update(self, run_id: str, status: str, message: str) -> None:
        """Send the mapped status update."""
        await self._send_update(run_id, {
            "status": status,
            "message": message
        })

    @validate_agent_input('ActionsToMeetGoalsSubAgent')
    async def execute(
        self, state: DeepAgentState, 
        run_id: str, stream_updates: bool
    ) -> None:
        """Modernized execute using BaseExecutionEngine."""
        self._log_execution_start(run_id)
        context = self._create_execution_context(state, run_id, stream_updates)
        await self._execute_with_modern_pattern_and_fallback(context, state, run_id, stream_updates)
        self._log_execution_end(run_id)

    def _log_execution_start(self, run_id: str) -> None:
        """Log execution start communication."""
        log_agent_communication(
            "Supervisor", "ActionsToMeetGoalsSubAgent", 
            run_id, "execute_request"
        )

    def _create_execution_context(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> ExecutionContext:
        """Create execution context for the request."""
        return ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=stream_updates,
            metadata={"description": self.description}
        )

    async def _execute_with_modern_pattern_and_fallback(
        self, context: ExecutionContext, state: DeepAgentState, 
        run_id: str, stream_updates: bool
    ) -> None:
        """Execute with modern pattern and fallback on failure."""
        try:
            await self._execute_with_modern_pattern(context, state, run_id)
        except Exception as e:
            await self._execute_fallback_workflow(state, run_id, stream_updates)

    async def _execute_with_modern_pattern(self, context: ExecutionContext, state: DeepAgentState, run_id: str) -> None:
        """Execute using modern execution pattern."""
        result = await self.execution_engine.execute(self, context)
        if not result.success:
            await self._handle_execution_failure(result, state, run_id)

    def _log_execution_end(self, run_id: str) -> None:
        """Log execution end communication."""
        log_agent_communication(
            "ActionsToMeetGoalsSubAgent", "Supervisor",
            run_id, "execute_response"
        )

    async def _handle_execution_failure(
        self, result: ExecutionResult,
        state: DeepAgentState, run_id: str
    ) -> None:
        """Handle execution failure with fallback."""
        logger.error(f"Execution failed: {result.error}")
        fallback_plan = ActionPlanBuilder.get_default_action_plan()
        state.action_plan_result = fallback_plan

    async def _execute_fallback_workflow(
        self, state: DeepAgentState,
        run_id: str, stream_updates: bool
    ) -> None:
        """Backward compatibility fallback workflow."""
        main_executor = self._create_main_executor(state, run_id, stream_updates)
        fallback_executor = self._create_fallback_executor(state, run_id, stream_updates)
        result = await self._execute_with_protection(
            main_executor, fallback_executor, run_id
        )
        await self._apply_reliability_protection(result)

    def _build_action_plan_prompt(self, state: DeepAgentState) -> str:
        """Build prompt for action plan generation."""
        return actions_to_meet_goals_prompt_template.format(
            optimizations=state.optimizations_result,
            data=state.data_result,
            user_request=state.user_request
        )

    async def _get_llm_response(self, prompt: str, run_id: str) -> str:
        """Get LLM response with monitoring."""
        correlation_id = self._prepare_llm_request(prompt, run_id)
        try:
            response = await self._execute_llm_request(prompt, correlation_id)
            self._finalize_llm_request_success(response, correlation_id)
            return response
        finally:
            stop_llm_heartbeat(correlation_id)

    def _prepare_llm_request(self, prompt: str, run_id: str) -> str:
        """Prepare LLM request with logging and monitoring setup."""
        correlation_id = generate_llm_correlation_id()
        start_llm_heartbeat(correlation_id, "ActionsToMeetGoalsSubAgent")
        self._log_prompt_size(prompt, run_id)
        log_agent_input(
            "ActionsToMeetGoalsSubAgent", "LLM",
            len(prompt), correlation_id
        )
        return correlation_id

    async def _execute_llm_request(self, prompt: str, correlation_id: str) -> str:
        """Execute the actual LLM request."""
        return await self.llm_manager.ask_llm(
            prompt, llm_config_name='actions_to_meet_goals'
        )

    def _finalize_llm_request_success(self, response: str, correlation_id: str) -> None:
        """Finalize successful LLM request with output logging."""
        log_agent_output(
            "LLM", "ActionsToMeetGoalsSubAgent",
            len(response) if response else 0,
            "success", correlation_id
        )

    async def _process_llm_response(
        self, llm_response: str, run_id: str
    ) -> ActionPlanResult:
        """Process LLM response to ActionPlanResult."""
        return await ActionPlanBuilder.process_llm_response(llm_response, run_id)

    def _get_default_action_plan(self) -> ActionPlanResult:
        """Get default action plan for failures."""
        return ActionPlanBuilder.get_default_action_plan()

    # Legacy compatibility methods
    def _create_main_executor(self, state, run_id, stream_updates):
        """Legacy main executor."""
        async def execute():
            await self._send_processing_update(run_id, stream_updates)
            prompt = self._build_action_plan_prompt(state)
            response = await self._get_llm_response(prompt, run_id)
            result = await self._process_llm_response(response, run_id)
            state.action_plan_result = result
            return result
        return execute

    def _create_fallback_executor(self, state, run_id, stream_updates):
        """Legacy fallback executor."""
        async def fallback():
            plan = ActionPlanBuilder.get_default_action_plan()
            state.action_plan_result = plan
            return plan
        return fallback

    async def _execute_with_protection(self, main, fallback, run_id):
        """Legacy protection wrapper."""
        return await self.fallback_strategy.execute_with_fallback(
            main, fallback, "action_plan_generation", run_id
        )

    async def _apply_reliability_protection(self, result):
        """Legacy reliability wrapper."""
        async def op():
            return result
        await self.reliability.execute_safely(op, "execute", timeout=45.0)

    async def _send_processing_update(self, run_id, stream_updates):
        """Legacy processing update."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Creating action plan..."
            })

    def _log_prompt_size(self, prompt: str, run_id: str):
        """Log large prompt warning."""
        size_mb = len(prompt) / (1024 * 1024)
        if size_mb > 1:
            logger.info(f"Large prompt ({size_mb:.2f}MB) for {run_id}")

    def get_health_status(self) -> dict:
        """Get comprehensive health status."""
        return {
            "agent": self.name,
            "modern_health": self.monitor.get_health_status(),
            "reliability": self.reliability_manager.get_health_status(),
            "legacy_health": self.reliability.get_health_status()
        }

    def get_performance_metrics(self) -> dict:
        """Get performance metrics."""
        return self.monitor.get_agent_metrics(self.name)

    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status."""
        return self.reliability_manager.get_circuit_breaker_status()

    async def check_entry_conditions(
        self, state: DeepAgentState, run_id: str
    ) -> bool:
        """Legacy entry condition check."""
        return state.optimizations_result is not None and state.data_result is not None