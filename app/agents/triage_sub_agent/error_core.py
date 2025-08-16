"""Core error handling coordination for Triage Sub Agent operations."""

import asyncio
from typing import Any, Dict, Optional

from app.agents.error_handler import ErrorContext, global_error_handler
from app.logging_config import central_logger

from .error_types import IntentDetectionError, EntityExtractionError, ToolRecommendationError
from .error_recovery import TriageErrorRecovery
from .error_reporting import TriageErrorReporter

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
        return ErrorContext(
            agent_name="triage_sub_agent",
            operation_name="intent_detection",
            run_id=run_id,
            additional_data={
                'user_input': user_input[:200],  # Truncate for logging
                'original_error': str(original_error)
            }
        )
    
    async def _process_intent_error_with_fallback(self, error: IntentDetectionError, user_input: str, run_id: str) -> Dict[str, Any]:
        """Process intent error with fallback handling."""
        try:
            fallback_result = await self.recovery.fallback_intent_detection(user_input)
            self.reporter.log_intent_recovery(run_id, fallback_result)
            return fallback_result
        except Exception:
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
        return ErrorContext(
            agent_name="triage_sub_agent",
            operation_name="entity_extraction",
            run_id=run_id,
            additional_data={
                'failed_entities': failed_entities,
                'user_input': user_input[:200],  # Truncate for logging
                'original_error': str(original_error)
            }
        )
    
    async def _process_entity_error_with_fallback(self, error: EntityExtractionError, failed_entities: list, user_input: str, run_id: str) -> Dict[str, Any]:
        """Process entity error with fallback handling."""
        try:
            fallback_result = await self.recovery.fallback_entity_extraction(user_input, failed_entities)
            self.reporter.log_entity_recovery(run_id, fallback_result)
            return fallback_result
        except Exception:
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
        return ErrorContext(
            agent_name="triage_sub_agent",
            operation_name="tool_recommendation",
            run_id=run_id,
            additional_data={
                'intent': intent,
                'entities': entities,
                'original_error': str(original_error)
            }
        )
    
    async def _process_tool_error_with_fallback(self, error: ToolRecommendationError, intent: str, entities: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Process tool error with fallback handling."""
        try:
            fallback_result = await self.recovery.fallback_tool_recommendation(intent, entities)
            self.reporter.log_tool_recovery(run_id, intent, fallback_result)
            return fallback_result
        except Exception:
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
                if self.reporter.should_retry(attempt, max_retries):
                    await self._handle_retry_attempt(operation_name, attempt, max_retries, error)
                else:
                    return await self._handle_operation_specific_error(operation_name, kwargs, run_id, error)
    
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
        if operation_name == 'intent_detection':
            return await self._handle_intent_detection_fallback(kwargs, run_id, error)
        elif operation_name == 'entity_extraction':
            return await self._handle_entity_extraction_fallback(kwargs, run_id, error)
        elif operation_name == 'tool_recommendation':
            return await self._handle_tool_recommendation_fallback(kwargs, run_id, error)
        else:
            await self._handle_generic_error_fallback(operation_name, run_id, error)
    
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
        context = ErrorContext(
            agent_name="triage_sub_agent",
            operation_name=operation_name,
            run_id=run_id
        )
        await global_error_handler.handle_error(error, context)
        raise error
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get comprehensive error metrics."""
        return self.reporter.generate_error_report()
    
    def reset_metrics(self) -> None:
        """Reset error metrics."""
        self.reporter.reset_error_metrics()