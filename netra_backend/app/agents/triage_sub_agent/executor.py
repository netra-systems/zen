"""Modernized Triage Execution Orchestrator with BaseExecutionEngine integration.

Integrates modern execution patterns: BaseExecutionEngine, ReliabilityManager,
ExecutionMonitor, and ExecutionErrorHandler for robust triage operations.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent

from netra_backend.app.agents.base.errors import ValidationError
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.triage_sub_agent.execution_helpers import (
    TriageExecutionHelpers, TriageValidationHelpers
)
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TriageExecutor:
    """Modernized triage execution orchestrator with BaseExecutionEngine patterns."""
    
    def __init__(self, agent: 'TriageSubAgent'):
        """Initialize with agent and modern execution infrastructure."""
        self.agent = agent
        self.logger = logger
        self._init_modern_components(agent)
        self._init_helper_classes()
    
    def _init_modern_components(self, agent: 'TriageSubAgent') -> None:
        """Initialize modern execution components."""
        self.monitor = getattr(agent, 'monitor', ExecutionMonitor())
        self.error_handler = ExecutionErrorHandler
        self.reliability_manager = getattr(agent, 'reliability_manager', None)
    
    def _init_helper_classes(self) -> None:
        """Initialize helper classes for execution and validation."""
        self.execution_helpers = TriageExecutionHelpers()
        self.validation_helpers = TriageValidationHelpers()
    
    async def execute_triage_workflow(
        self, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Execute complete triage workflow with modern patterns."""
        context = self._create_execution_context(state, run_id, stream_updates)
        await self._execute_with_monitoring(context)
    
    def _create_execution_context(self, state: DeepAgentState, run_id: str, 
                                 stream_updates: bool) -> ExecutionContext:
        """Create execution context for monitoring and reliability."""
        return ExecutionContext(
            run_id=run_id,
            agent_name=self.agent.name,
            state=state,
            stream_updates=stream_updates
        )
    
    async def _execute_with_monitoring(self, context: ExecutionContext) -> None:
        """Execute triage workflow with comprehensive monitoring."""
        # Store context info for notifications
        self._current_run_id = context.run_id
        self._current_thread_id = getattr(context, 'thread_id', context.run_id)
        
        self.monitor.start_execution(context)
        try:
            await self._execute_core_triage_workflow(context)
        except Exception as e:
            await self._handle_monitored_execution_error(context, e)
        finally:
            self._finalize_execution_monitoring(context)
    
    async def _execute_core_triage_workflow(self, context: ExecutionContext) -> None:
        """Execute core triage workflow with reliability patterns."""
        if self.reliability_manager:
            await self._execute_with_reliability(context)
        else:
            await self._execute_direct_workflow(context)
    
    async def _execute_with_reliability(self, context: ExecutionContext) -> None:
        """Execute with reliability manager patterns."""
        triage_operation = self._create_main_triage_operation(context)
        result = await self.reliability_manager.execute_with_reliability(
            context, triage_operation
        )
        await self._process_reliability_result(context, result)
    
    def _create_main_triage_operation(self, context: ExecutionContext):
        """Create main triage operation function."""
        async def _main_triage_operation():
            return await self._execute_direct_workflow(context)
        return _main_triage_operation
    
    async def _execute_direct_workflow(self, context: ExecutionContext) -> None:
        """Execute triage workflow directly with WebSocket notifications."""
        self._log_execution_start(context.run_id)
        
        # Send thinking notification about analyzing request
        await self._send_thinking_notification(context, "Analyzing request details...")
        
        triage_operation = self._create_legacy_triage_operation(context)
        result = await self._execute_with_fallback(triage_operation)
        await self._process_triage_result(result, context)
    
    async def _send_thinking_notification(self, context: ExecutionContext, thought: str) -> None:
        """Send thinking notification if WebSocket manager available."""
        if hasattr(self.agent, 'websocket_manager') and self.agent.websocket_manager:
            try:
                notifier = self.agent._get_websocket_notifier()
                ws_context = self.agent._create_websocket_context(context)
                await notifier.send_agent_thinking(ws_context, thought)
            except Exception as e:
                logger.debug(f"Failed to send thinking notification: {e}")
    
    def _create_legacy_triage_operation(self, context: ExecutionContext):
        """Create legacy triage operation for backward compatibility."""
        async def _legacy_triage_operation():
            return await self.agent.llm_processor.execute_triage_with_llm(
                context.state, context.run_id, context.stream_updates
            )
        return _legacy_triage_operation
    
    async def _execute_with_fallback(self, triage_operation):
        """Execute triage operation with fallback handling and notifications."""
        # Send progress notification about LLM processing
        await self._send_progress_notification("Processing with AI model...")
        
        if hasattr(self.agent, 'llm_fallback_handler'):
            return await self.agent.llm_fallback_handler.execute_with_fallback(
                triage_operation, "triage_analysis", "triage", "triage"
            )
        return await triage_operation()
    
    async def _send_progress_notification(self, message: str) -> None:
        """Send progress notification if WebSocket manager available."""
        if hasattr(self.agent, 'websocket_manager') and self.agent.websocket_manager:
            try:
                notifier = self.agent._get_websocket_notifier()
                # Create a minimal context for progress notifications
                from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
                context = AgentExecutionContext(
                    agent_name=self.agent.name,
                    run_id=getattr(self, '_current_run_id', 'unknown'),
                    thread_id=getattr(self, '_current_thread_id', 'unknown')
                )
                await notifier.send_partial_result(context, message, is_complete=False)
            except Exception as e:
                logger.debug(f"Failed to send progress notification: {e}")
    
    async def _process_triage_result(
        self, result: Any, context: ExecutionContext
    ) -> None:
        """Process triage result based on type."""
        if isinstance(result, dict):
            await self._handle_successful_result(result, context)
        else:
            await self._handle_fallback_result(context)
    
    async def _process_reliability_result(self, context: ExecutionContext, 
                                        result: ExecutionResult) -> None:
        """Process result from reliability manager."""
        if result.success and result.result:
            await self._handle_successful_result(result.result, context)
        else:
            await self._handle_reliability_error(context, result.error)
    
    async def _handle_successful_result(
        self, result: dict, context: ExecutionContext
    ) -> None:
        """Handle successful triage result with monitoring and notifications."""
        # Send thinking notification about processing results
        await self._send_thinking_notification(context, "Processing analysis results...")
        
        processed_result = self.agent.result_processor.process_result(
            result, context.state.user_request
        )
        self._update_state_with_result(context.state, processed_result)
        await self._send_success_updates(context, processed_result)
    
    def _update_state_with_result(self, state: DeepAgentState, result) -> None:
        """Update state with triage result and record metrics."""
        triage_result = self.execution_helpers.ensure_triage_result_type(result)
        # Ensure status field is present for tests
        if isinstance(triage_result, dict) and 'status' not in triage_result:
            triage_result['status'] = 'success'
        state.triage_result = triage_result
        state.step_count += 1
        self._record_successful_execution_metrics(result)
    
    def _ensure_triage_result_type(self, result):
        """Ensure result is proper TriageResult object - delegated to helpers."""
        return self.execution_helpers.ensure_triage_result_type(result)
    
    async def _handle_fallback_result(self, context: ExecutionContext) -> None:
        """Handle fallback triage result with error tracking."""
        fallback_result = await self._create_emergency_fallback(
            context.state, context.run_id
        )
        self._update_state_with_result(context.state, fallback_result)
        await self._send_fallback_updates(context, fallback_result)
    
    async def _create_emergency_fallback(self, state: DeepAgentState, run_id: str):
        """Create emergency fallback when all else fails."""
        logger.error(f"Emergency fallback activated for triage {run_id}")
        try:
            return self.agent.triage_core.create_fallback_result(state.user_request)
        except Exception:
            return self.execution_helpers.create_emergency_fallback_result()
    
    async def _send_success_updates(self, context: ExecutionContext, result) -> None:
        """Send success updates with modern pattern."""
        if context.stream_updates:
            await self._send_completion_update(context.run_id, result)
        await self.agent.send_status_update(context, "completed", 
                                          f"Triage completed successfully")
    
    async def _send_completion_update(self, run_id: str, result) -> None:
        """Send completion update with result details."""
        result_dict, category = self._extract_result_data(result)
        status = self._determine_completion_status(result_dict)
        await self.agent._send_update(run_id, self._build_completion_message(
            status, category, result_dict
        ))
    
    def _extract_result_data(self, result) -> tuple:
        """Extract result dictionary and category - delegated to helpers."""
        return self.execution_helpers.extract_result_data(result)
    
    def _determine_completion_status(self, result_dict: dict) -> str:
        """Determine completion status - delegated to helpers."""
        return self.execution_helpers.determine_completion_status(result_dict)
    
    async def _send_fallback_updates(self, context: ExecutionContext, result) -> None:
        """Send fallback updates with modern pattern."""
        if context.stream_updates:
            await self._send_emergency_update(context.run_id, result)
        await self.agent.send_status_update(context, "completed_with_fallback", 
                                          "Triage completed using fallback")
    
    async def _send_emergency_update(self, run_id: str, result) -> None:
        """Send emergency fallback update."""
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else result
        await self.agent._send_update(run_id, self._build_emergency_message(result_dict))
    
    async def _handle_monitored_execution_error(
        self, context: ExecutionContext, error: Exception
    ) -> None:
        """Handle execution error with monitoring and modern error handling."""
        self.monitor.record_error(context, error)
        error_result = await self.error_handler.handle_execution_error(error, context)
        await self._process_error_result(context, error_result)
    
    async def _handle_reliability_error(self, context: ExecutionContext, 
                                      error_message: str) -> None:
        """Handle reliability manager error."""
        error_result = self._create_error_result(error_message)
        self._update_state_with_result(context.state, error_result)
        await self._send_error_updates(context, error_message)
    
    def _create_error_result(self, error_message: str):
        """Create result object for error cases - delegated to helpers."""
        return self.execution_helpers.create_error_result(error_message)
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have a user request to triage."""
        if not state.user_request:
            self.logger.warning(f"No user request provided for triage in run_id: {run_id}")
            return False
        
        return await self._validate_user_request(state, run_id)
    
    async def _validate_user_request(self, state: DeepAgentState, run_id: str) -> bool:
        """Validate user request using triage core."""
        validation = self.agent.triage_core.validator.validate_request(state.user_request)
        return self._process_validation_result(validation, state, run_id)
    
    def _process_validation_result(self, validation, state: DeepAgentState, run_id: str) -> bool:
        """Process validation result and handle errors - delegated to helpers."""
        return self.validation_helpers.process_validation_result(validation, state, run_id)
    
    # Modern execution helper methods
    def _log_execution_start(self, run_id: str) -> None:
        """Log the start of triage execution."""
        self.logger.info(f"TriageSubAgent starting execution for run_id: {run_id}")
    
    def _finalize_execution_monitoring(self, context: ExecutionContext) -> None:
        """Finalize execution monitoring."""
        # Monitor automatically handles completion tracking
        pass
    
    def _record_successful_execution_metrics(self, result) -> None:
        """Record metrics for successful execution."""
        # Metrics are automatically recorded by the monitor
        pass
    
    async def _process_error_result(self, context: ExecutionContext, 
                                  result: ExecutionResult) -> None:
        """Process error result from error handler."""
        error_result = self._create_error_result(result.error or "Unknown error")
        self._update_state_with_result(context.state, error_result)
    
    async def _send_error_updates(self, context: ExecutionContext, 
                                error_message: str) -> None:
        """Send error updates with modern pattern."""
        await self.agent.send_status_update(context, "error", 
                                          f"Triage failed: {error_message}")
    
    def _build_completion_message(self, status: str, category: str, 
                                result_dict: dict) -> dict:
        """Build completion message dictionary - delegated to helpers."""
        return self.execution_helpers.build_completion_message(status, category, result_dict)
    
    def _build_emergency_message(self, result_dict: dict) -> dict:
        """Build emergency fallback message - delegated to helpers."""
        return self.execution_helpers.build_emergency_message(result_dict)