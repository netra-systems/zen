"""Triage Execution Orchestrator

Handles the main execution flow and coordination of triage operations.
Keeps functions under 8 lines and module under 300 lines.
"""

import time
import asyncio
from typing import Optional, Any, Dict

from app.logging_config import central_logger
from app.agents.state import DeepAgentState

logger = central_logger.get_logger(__name__)


class TriageExecutor:
    """Orchestrates triage execution flow and coordination."""
    
    def __init__(self, agent):
        """Initialize with reference to main agent."""
        self.agent = agent
        self.logger = logger
    
    async def execute_triage_workflow(
        self, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Execute complete triage workflow."""
        self._log_execution_start(run_id)
        start_time = time.time()
        
        try:
            await self._execute_with_fallback_protection(state, run_id, stream_updates)
        except Exception as e:
            await self._handle_execution_error(e, state, run_id, stream_updates)
    
    def _log_execution_start(self, run_id: str) -> None:
        """Log the start of triage execution."""
        self.logger.info(f"TriageSubAgent starting execution for run_id: {run_id}")
    
    async def _execute_with_fallback_protection(
        self, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Execute triage with fallback protection."""
        triage_operation = self._create_main_triage_operation(state, run_id, stream_updates)
        result = await self._execute_with_fallback(triage_operation)
        await self._process_triage_result(result, state, run_id, stream_updates)
    
    def _create_main_triage_operation(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Create main triage operation function."""
        async def _main_triage_operation():
            return await self.agent.llm_processor.execute_triage_with_llm(state, run_id, stream_updates)
        return _main_triage_operation
    
    async def _execute_with_fallback(self, triage_operation):
        """Execute triage operation with fallback handling."""
        return await self.agent.llm_fallback_handler.execute_with_fallback(
            triage_operation, "triage_analysis", "triage", "triage"
        )
    
    async def _process_triage_result(
        self, result: Any, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Process triage result based on type."""
        if isinstance(result, dict):
            await self._handle_successful_result(result, state, run_id, stream_updates)
        else:
            await self._handle_fallback_result(state, run_id, stream_updates)
    
    async def _handle_successful_result(
        self, result: dict, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Handle successful triage result."""
        processed_result = self.agent.result_processor.process_result(result, state.user_request)
        self._update_state_with_result(state, processed_result)
        
        if stream_updates:
            await self._send_completion_update(run_id, processed_result)
    
    def _update_state_with_result(self, state: DeepAgentState, result) -> None:
        """Update state with triage result."""
        state.triage_result = result
        state.step_count += 1
    
    async def _handle_fallback_result(
        self, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Handle fallback triage result."""
        fallback_result = await self._create_emergency_fallback(state, run_id)
        self._update_state_with_result(state, fallback_result)
        
        if stream_updates:
            await self._send_emergency_update(run_id, fallback_result)
    
    async def _create_emergency_fallback(self, state: DeepAgentState, run_id: str) -> dict:
        """Create emergency fallback when all else fails."""
        logger.error(f"Emergency fallback activated for triage {run_id}")
        
        try:
            fallback_result = self.agent.triage_core.create_fallback_result(state.user_request)
            return fallback_result.model_dump()
        except Exception:
            return self._create_basic_emergency_fallback()
    
    def _create_basic_emergency_fallback(self) -> dict:
        """Create basic emergency fallback response."""
        return {
            "category": "General Inquiry",
            "confidence_score": 0.3,
            "priority": "medium",
            "extracted_entities": {},
            "tool_recommendations": [],
            "metadata": {
                "fallback_used": True,
                "fallback_type": "emergency"
            }
        }
    
    async def _send_completion_update(self, run_id: str, result) -> None:
        """Send completion update with result details."""
        result_dict, category = self._extract_result_data(result)
        status = self._determine_completion_status(result_dict)
        
        await self.agent._send_update(run_id, {
            "status": status,
            "message": f"Request categorized as: {category}",
            "result": result_dict
        })
    
    def _extract_result_data(self, result) -> tuple:
        """Extract result dictionary and category from result object."""
        if hasattr(result, 'model_dump'):
            result_dict = result.model_dump()
            category = result.category if hasattr(result, 'category') else 'Unknown'
        else:
            result_dict = result if isinstance(result, dict) else {}
            category = result_dict.get('category', 'Unknown')
        return result_dict, category
    
    def _determine_completion_status(self, result_dict: dict) -> str:
        """Determine completion status based on result metadata."""
        metadata = result_dict.get("metadata", {}) or {}
        fallback_used = metadata.get("fallback_used", False)
        return "completed_with_fallback" if fallback_used else "completed"
    
    async def _send_emergency_update(self, run_id: str, result: dict) -> None:
        """Send emergency fallback update."""
        await self.agent._send_update(run_id, {
            "status": "completed_with_emergency_fallback",
            "message": "Triage completed using emergency fallback",
            "result": result
        })
    
    async def _handle_execution_error(
        self, error: Exception, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Handle execution error and log appropriately."""
        logger.error(f"Triage execution failed for run_id {run_id}: {error}")
        # Create error result for state
        error_result = self._create_error_result(str(error))
        self._update_state_with_result(state, error_result)
    
    def _create_error_result(self, error_message: str) -> dict:
        """Create result object for error cases."""
        return {
            "category": "Error",
            "confidence_score": 0.0,
            "error": error_message,
            "metadata": {
                "error_occurred": True,
                "fallback_used": True
            }
        }
    
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
        """Process validation result and handle errors."""
        if not validation.is_valid:
            self._handle_validation_error(state, run_id, validation)
            return False
        return True
    
    def _handle_validation_error(self, state: DeepAgentState, run_id: str, validation) -> None:
        """Handle validation error by creating error result."""
        self.logger.error(f"Invalid request for run_id {run_id}: {validation.validation_errors}")
        error_result = self._create_validation_error_result(validation)
        state.triage_result = error_result
        state.step_count += 1
    
    def _create_validation_error_result(self, validation) -> dict:
        """Create validation error result."""
        from .models import TriageResult
        return TriageResult(
            category="Validation Error",
            confidence_score=0.0,
            validation_status=validation
        ).model_dump()