"""Error handler specific to Triage Sub Agent operations.

Provides specialized error recovery for triage operations including
intent detection failures, entity extraction errors, and tool recommendation issues.
"""

import asyncio
from typing import Any, Dict, Optional, List
from datetime import datetime

from app.core.error_recovery import (
    CompensationAction,
    RecoveryContext,
    OperationType
)
from app.core.error_codes import ErrorSeverity
from app.agents.error_handler import AgentError, ErrorContext, global_error_handler
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TriageError(AgentError):
    """Specific error type for triage operations."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        user_input: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ):
        """Initialize triage error with specific context."""
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=True
        )
        self.operation = operation
        self.user_input = user_input


class IntentDetectionError(TriageError):
    """Error when intent detection fails."""
    
    def __init__(self, user_input: str, context: Optional[ErrorContext] = None):
        """Initialize intent detection error."""
        super().__init__(
            message=f"Failed to detect intent from user input: {user_input[:100]}...",
            operation="intent_detection",
            user_input=user_input,
            context=context
        )


class EntityExtractionError(TriageError):
    """Error when entity extraction fails."""
    
    def __init__(self, entities: List[str], context: Optional[ErrorContext] = None):
        """Initialize entity extraction error."""
        super().__init__(
            message=f"Failed to extract entities: {', '.join(entities)}",
            operation="entity_extraction",
            context=context
        )
        self.failed_entities = entities


class ToolRecommendationError(TriageError):
    """Error when tool recommendation fails."""
    
    def __init__(self, intent: str, context: Optional[ErrorContext] = None):
        """Initialize tool recommendation error."""
        super().__init__(
            message=f"Failed to recommend tools for intent: {intent}",
            operation="tool_recommendation",
            context=context
        )
        self.intent = intent


class TriageCacheCompensation(CompensationAction):
    """Compensation action for triage cache operations."""
    
    def __init__(self, cache_manager):
        """Initialize with cache manager."""
        self.cache_manager = cache_manager
    
    async def execute(self, context: RecoveryContext) -> bool:
        """Execute cache compensation for triage operations."""
        try:
            cache_keys = context.metadata.get('triage_cache_keys', [])
            if cache_keys:
                await self.cache_manager.invalidate_keys(cache_keys)
                logger.info(f"Invalidated triage cache keys: {cache_keys}")
            return True
        except Exception as e:
            logger.error(f"Triage cache compensation failed: {e}")
            return False
    
    def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if can compensate triage cache operations."""
        return (
            context.operation_type == OperationType.CACHE_OPERATION and
            'triage_cache_keys' in context.metadata
        )


class TriageErrorHandler:
    """Specialized error handler for triage sub agent."""
    
    def __init__(self, cache_manager=None):
        """Initialize triage error handler."""
        self.cache_manager = cache_manager
        self.fallback_strategies = {
            'intent_detection': self._fallback_intent_detection,
            'entity_extraction': self._fallback_entity_extraction,
            'tool_recommendation': self._fallback_tool_recommendation,
        }
    
    async def handle_intent_detection_error(
        self,
        user_input: str,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle intent detection failures with fallback strategies."""
        context = ErrorContext(
            agent_name="triage_sub_agent",
            operation_name="intent_detection",
            run_id=run_id,
            additional_data={
                'user_input': user_input,
                'input_length': len(user_input),
                'original_error': str(original_error)
            }
        )
        
        error = IntentDetectionError(user_input, context)
        
        try:
            # Attempt recovery with fallback
            fallback_result = await self._fallback_intent_detection(user_input)
            
            logger.info(
                f"Intent detection recovered with fallback",
                run_id=run_id,
                input_preview=user_input[:50],
                fallback_intent=fallback_result.get('intent')
            )
            
            return fallback_result
            
        except Exception as fallback_error:
            # If fallback also fails, use global error handler
            await global_error_handler.handle_error(error, context)
            raise error
    
    async def handle_entity_extraction_error(
        self,
        entities: List[str],
        user_input: str,
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle entity extraction failures."""
        context = ErrorContext(
            agent_name="triage_sub_agent",
            operation_name="entity_extraction",
            run_id=run_id,
            additional_data={
                'failed_entities': entities,
                'user_input': user_input,
                'original_error': str(original_error)
            }
        )
        
        error = EntityExtractionError(entities, context)
        
        try:
            # Attempt partial extraction fallback
            fallback_result = await self._fallback_entity_extraction(
                user_input, entities
            )
            
            logger.info(
                f"Entity extraction recovered with partial results",
                run_id=run_id,
                extracted_entities=fallback_result.get('entities', [])
            )
            
            return fallback_result
            
        except Exception as fallback_error:
            await global_error_handler.handle_error(error, context)
            raise error
    
    async def handle_tool_recommendation_error(
        self,
        intent: str,
        entities: Dict[str, Any],
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle tool recommendation failures."""
        context = ErrorContext(
            agent_name="triage_sub_agent",
            operation_name="tool_recommendation",
            run_id=run_id,
            additional_data={
                'intent': intent,
                'entities': entities,
                'original_error': str(original_error)
            }
        )
        
        error = ToolRecommendationError(intent, context)
        
        try:
            # Use default recommendation fallback
            fallback_result = await self._fallback_tool_recommendation(intent, entities)
            
            logger.info(
                f"Tool recommendation recovered with default tools",
                run_id=run_id,
                intent=intent,
                recommended_tools=fallback_result.get('tools', [])
            )
            
            return fallback_result
            
        except Exception as fallback_error:
            await global_error_handler.handle_error(error, context)
            raise error
    
    async def _fallback_intent_detection(self, user_input: str) -> Dict[str, Any]:
        """Fallback strategy for intent detection."""
        # Simple keyword-based intent detection
        user_input_lower = user_input.lower()
        
        # Define intent keywords
        intent_keywords = {
            'data_analysis': ['analyze', 'analysis', 'data', 'metrics', 'performance'],
            'corpus_management': ['corpus', 'documents', 'upload', 'manage'],
            'optimization': ['optimize', 'improve', 'performance', 'cost'],
            'general_inquiry': ['help', 'what', 'how', 'explain', 'info'],
        }
        
        # Find best matching intent
        best_intent = 'general_inquiry'
        max_matches = 0
        
        for intent, keywords in intent_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in user_input_lower)
            if matches > max_matches:
                max_matches = matches
                best_intent = intent
        
        return {
            'intent': best_intent,
            'confidence': min(0.8, max_matches * 0.2),
            'method': 'keyword_fallback',
            'matched_keywords': max_matches
        }
    
    async def _fallback_entity_extraction(
        self,
        user_input: str,
        failed_entities: List[str]
    ) -> Dict[str, Any]:
        """Fallback strategy for entity extraction."""
        # Simple regex-based entity extraction
        entities = {}
        
        # Basic patterns for common entities
        patterns = {
            'date': r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}',
            'number': r'\d+',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'url': r'https?://[^\s]+',
        }
        
        import re
        for entity_type, pattern in patterns.items():
            if entity_type in failed_entities:
                matches = re.findall(pattern, user_input)
                if matches:
                    entities[entity_type] = matches[0] if len(matches) == 1 else matches
        
        return {
            'entities': entities,
            'method': 'regex_fallback',
            'extracted_count': len(entities)
        }
    
    async def _fallback_tool_recommendation(
        self,
        intent: str,
        entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback strategy for tool recommendation."""
        # Default tool mappings based on intent
        default_tools = {
            'data_analysis': [
                'data_fetcher',
                'metrics_analyzer',
                'performance_analyzer'
            ],
            'corpus_management': [
                'corpus_uploader',
                'document_manager',
                'corpus_validator'
            ],
            'optimization': [
                'cost_optimizer',
                'performance_optimizer',
                'resource_optimizer'
            ],
            'general_inquiry': [
                'general_assistant',
                'help_provider',
                'information_retriever'
            ]
        }
        
        recommended_tools = default_tools.get(intent, default_tools['general_inquiry'])
        
        return {
            'tools': recommended_tools,
            'confidence': 0.6,
            'method': 'default_fallback',
            'intent': intent
        }
    
    def _calculate_retry_delay(self, attempt: int) -> int:
        """Calculate exponential backoff delay for retry attempt."""
        return 2 ** attempt
    
    async def _log_retry_warning(
        self, 
        operation_name: str, 
        attempt: int, 
        max_retries: int, 
        delay: int, 
        error: Exception
    ) -> None:
        """Log warning for retry attempt."""
        logger.warning(
            f"Triage operation failed, retrying in {delay}s",
            operation=operation_name,
            attempt=attempt + 1,
            max_retries=max_retries,
            error=str(error)
        )
    
    def _should_retry(self, attempt: int, max_retries: int) -> bool:
        """Determine if operation should be retried."""
        return attempt < max_retries
    
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
    
    async def _handle_retry_attempt(
        self, 
        operation_name: str, 
        attempt: int, 
        max_retries: int, 
        error: Exception
    ) -> None:
        """Handle retry delay and logging for failed attempt."""
        delay = self._calculate_retry_delay(attempt)
        await self._log_retry_warning(operation_name, attempt, max_retries, delay, error)
        await asyncio.sleep(delay)
    
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
                if self._should_retry(attempt, max_retries):
                    await self._handle_retry_attempt(operation_name, attempt, max_retries, error)
                else:
                    return await self._handle_operation_specific_error(operation_name, kwargs, run_id, error)
    
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


# Global triage error handler instance
triage_error_handler = TriageErrorHandler()