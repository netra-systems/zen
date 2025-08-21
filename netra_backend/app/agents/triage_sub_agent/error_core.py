"""Core error handling coordination for Triage Sub Agent operations."""

import asyncio
from typing import Any, Dict, Optional

from netra_backend.app.agents.error_handler import ErrorContext, global_error_handler
from netra_backend.app.logging_config import central_logger

from netra_backend.app.error_types import IntentDetectionError, EntityExtractionError, ToolRecommendationError
from netra_backend.app.error_recovery import TriageErrorRecovery
from netra_backend.app.error_reporting import TriageErrorReporter

logger = central_logger.get_logger(__name__)


class TriageErrorHandler:
    """Central error handler for triage operations with recovery and reporting."""
    
    def __init__(self):
        self.recovery = TriageErrorRecovery()
        self.reporter = TriageErrorReporter()
    
    async def handle_intent_detection_error(
        self,
        user_input: str,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle intent detection failures."""
        context = self._create_intent_error_context(user_input, run_id, original_error)
        error = IntentDetectionError(user_input, context)
        return await self._process_intent_error_with_fallback(error, user_input, run_id)
    
    def _create_intent_error_context(self, user_input: str, run_id: str, original_error: Exception) -> ErrorContext:
        """Create error context for intent detection errors."""
        additional_data = self._build_intent_additional_data(user_input, original_error)
        return ErrorContext(
            agent_name="triage_sub_agent",
            operation_name="intent_detection",
            run_id=run_id,
            additional_data=additional_data
        )
    
    def _build_intent_additional_data(self, user_input: str, original_error: Exception) -> Dict[str, Any]:
        """Build additional data for intent error context."""
        return {
            'user_input': user_input[:200],  # Truncate for logging
            'original_error': str(original_error)
        }
    
    async def _process_intent_error_with_fallback(self, error: IntentDetectionError, user_input: str, run_id: str) -> Dict[str, Any]:
        """Process intent error with fallback handling."""
        try:
            return await self._execute_intent_fallback_recovery(user_input, run_id)
        except Exception:
            await self._handle_intent_fallback_failure(error)
    
    async def _execute_intent_fallback_recovery(self, user_input: str, run_id: str) -> Dict[str, Any]:
        """Execute intent fallback recovery."""
        fallback_result = await self.recovery.fallback_intent_detection(user_input)
        self.reporter.log_intent_recovery(run_id, fallback_result)
        return fallback_result
    
    async def _handle_intent_fallback_failure(self, error: IntentDetectionError) -> None:
        """Handle intent fallback failure."""
        await global_error_handler.handle_error(error, error.context)
        raise error
    
    async def handle_entity_extraction_error(
        self,
        failed_entities: list,
        user_input: str,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle entity extraction failures."""
        context = self._create_entity_error_context(failed_entities, user_input, run_id, original_error)
        error = EntityExtractionError(failed_entities, context)
        return await self._process_entity_error_with_fallback(error, failed_entities, user_input, run_id)
    
    def _create_entity_error_context(self, failed_entities: list, user_input: str, run_id: str, original_error: Exception) -> ErrorContext:
        """Create error context for entity extraction errors."""
        additional_data = self._build_entity_additional_data(failed_entities, user_input, original_error)
        return ErrorContext(
            agent_name="triage_sub_agent",
            operation_name="entity_extraction",
            run_id=run_id,
            additional_data=additional_data
        )
    
    def _build_entity_additional_data(self, failed_entities: list, user_input: str, original_error: Exception) -> Dict[str, Any]:
        """Build additional data for entity error context."""
        return {
            'failed_entities': failed_entities,
            'user_input': user_input[:200],  # Truncate for logging
            'original_error': str(original_error)
        }
    
    async def _process_entity_error_with_fallback(self, error: EntityExtractionError, failed_entities: list, user_input: str, run_id: str) -> Dict[str, Any]:
        """Process entity error with fallback handling."""
        try:
            return await self._execute_entity_fallback_recovery(failed_entities, user_input, run_id)
        except Exception:
            await self._handle_entity_fallback_failure(error)
    
    async def _execute_entity_fallback_recovery(self, failed_entities: list, user_input: str, run_id: str) -> Dict[str, Any]:
        """Execute entity fallback recovery."""
        fallback_result = await self.recovery.fallback_entity_extraction(user_input, failed_entities)
        self.reporter.log_entity_recovery(run_id, fallback_result)
        return fallback_result
    
    async def _handle_entity_fallback_failure(self, error: EntityExtractionError) -> None:
        """Handle entity fallback failure."""
        await global_error_handler.handle_error(error, error.context)
        raise error
    
    async def handle_tool_recommendation_error(
        self,
        intent: str,
        entities: Dict[str, Any],
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle tool recommendation failures."""
        context = self._create_tool_error_context(intent, entities, run_id, original_error)
        error = ToolRecommendationError(intent, context)
        return await self._process_tool_error_with_fallback(error, intent, entities, run_id)
    
    def _create_tool_error_context(self, intent: str, entities: Dict[str, Any], run_id: str, original_error: Exception) -> ErrorContext:
        """Create error context for tool recommendation errors."""
        additional_data = self._build_tool_additional_data(intent, entities, original_error)
        return ErrorContext(
            agent_name="triage_sub_agent",
            operation_name="tool_recommendation",
            run_id=run_id,
            additional_data=additional_data
        )
    
    def _build_tool_additional_data(self, intent: str, entities: Dict[str, Any], original_error: Exception) -> Dict[str, Any]:
        """Build additional data for tool error context."""
        return {
            'intent': intent,
            'entities': entities,
            'original_error': str(original_error)
        }
    
    async def _process_tool_error_with_fallback(self, error: ToolRecommendationError, intent: str, entities: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Process tool error with fallback handling."""
        try:
            return await self._execute_tool_fallback_recovery(intent, entities, run_id)
        except Exception:
            await self._handle_tool_fallback_failure(error)
    
    async def _execute_tool_fallback_recovery(self, intent: str, entities: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Execute tool fallback recovery."""
        fallback_result = await self.recovery.fallback_tool_recommendation(intent, entities)
        self.reporter.log_tool_recovery(run_id, intent, fallback_result)
        return fallback_result
    
    async def _handle_tool_fallback_failure(self, error: ToolRecommendationError) -> None:
        """Handle tool fallback failure."""
        await global_error_handler.handle_error(error, error.context)
        raise error
    
    async def handle_with_retry(
        self,
        operation_func,
        operation_name: str,
        run_id: str,
        max_retries: int = 2,
        **kwargs
    ) -> Any:
        """Handle operation with automatic retry and error recovery."""
        return await self._attempt_operation_with_retry_logic(
            operation_func, operation_name, run_id, max_retries, **kwargs
        )
    
    async def _attempt_operation_with_retry_logic(
        self, 
        operation_func, 
        operation_name: str, 
        run_id: str, 
        max_retries: int, 
        **kwargs
    ) -> Any:
        """Perform single attempt with retry logic."""
        for attempt in range(max_retries + 1):
            try:
                return await operation_func(**kwargs)
            except Exception as error:
                should_continue = await self._handle_retry_or_fallback(
                    operation_name, attempt, max_retries, kwargs, run_id, error
                )
                if not should_continue:
                    return await self._handle_operation_specific_error(operation_name, kwargs, run_id, error)
    
    async def _handle_retry_or_fallback(
        self, 
        operation_name: str, 
        attempt: int, 
        max_retries: int, 
        kwargs: Dict[str, Any], 
        run_id: str, 
        error: Exception
    ) -> bool:
        """Handle retry decision or fallback."""
        if self.reporter.should_retry(attempt, max_retries):
            await self._handle_retry_attempt(operation_name, attempt, max_retries, error)
            return True
        return False
    
    async def _handle_retry_attempt(
        self, 
        operation_name: str, 
        attempt: int, 
        max_retries: int, 
        error: Exception
    ) -> None:
        """Handle retry delay and logging for failed attempt."""
        delay = self.reporter.calculate_retry_delay(attempt)
        await self.reporter.log_retry_warning(operation_name, attempt, max_retries, delay, error)
        await asyncio.sleep(delay)
    
    async def _handle_operation_specific_error(
        self, 
        operation_name: str, 
        kwargs: Dict[str, Any], 
        run_id: str, 
        error: Exception
    ) -> Any:
        """Route to specific error handler based on operation type."""
        error_handlers = self._get_operation_error_handlers()
        if operation_name in error_handlers:
            return await error_handlers[operation_name](kwargs, run_id, error)
        else:
            await self._handle_generic_error_fallback(operation_name, run_id, error)
    
    def _get_operation_error_handlers(self) -> Dict[str, Any]:
        """Get mapping of operation names to error handlers."""
        return {
            'intent_detection': self._handle_intent_detection_fallback,
            'entity_extraction': self._handle_entity_extraction_fallback,
            'tool_recommendation': self._handle_tool_recommendation_fallback
        }
    
    async def _handle_intent_detection_fallback(
        self, 
        kwargs: Dict[str, Any], 
        run_id: str, 
        error: Exception
    ) -> Dict[str, Any]:
        """Handle intent detection error fallback."""
        return await self.handle_intent_detection_error(
            kwargs.get('user_input', ''),
            run_id,
            error
        )
    
    async def _handle_entity_extraction_fallback(
        self, 
        kwargs: Dict[str, Any], 
        run_id: str, 
        error: Exception
    ) -> Dict[str, Any]:
        """Handle entity extraction error fallback."""
        return await self.handle_entity_extraction_error(
            kwargs.get('entities', []),
            kwargs.get('user_input', ''),
            run_id,
            error
        )
    
    async def _handle_tool_recommendation_fallback(
        self, 
        kwargs: Dict[str, Any], 
        run_id: str, 
        error: Exception
    ) -> Dict[str, Any]:
        """Handle tool recommendation error fallback."""
        return await self.handle_tool_recommendation_error(
            kwargs.get('intent', ''),
            kwargs.get('entities', {}),
            run_id,
            error
        )
    
    async def _handle_generic_error_fallback(
        self, 
        operation_name: str, 
        run_id: str, 
        error: Exception
    ) -> None:
        """Handle generic error fallback."""
        context = self._create_generic_error_context(operation_name, run_id)
        await global_error_handler.handle_error(error, context)
        raise error
    
    def _create_generic_error_context(self, operation_name: str, run_id: str) -> ErrorContext:
        """Create generic error context."""
        return ErrorContext(
            agent_name="triage_sub_agent",
            operation_name=operation_name,
            run_id=run_id
        )
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get comprehensive error metrics."""
        return self.reporter.generate_error_report()
    
    def reset_metrics(self) -> None:
        """Reset error metrics."""
        self.reporter.reset_error_metrics()