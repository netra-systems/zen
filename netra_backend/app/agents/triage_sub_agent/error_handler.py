"""Modular error handler for Triage Sub Agent operations.

Provides specialized error recovery for triage operations including
intent detection failures, entity extraction errors, and tool recommendation issues.
"""

from typing import Any, Dict

from netra_backend.app.agents.triage_sub_agent.error_core import TriageErrorHandler
from netra_backend.app.agents.triage_sub_agent.error_reporting import (
    TriageErrorReporter,
)
from netra_backend.app.core.error_recovery import TriageErrorRecovery
from netra_backend.app.core.error_types import (
    EntityExtractionError,
    IntentDetectionError,
    ToolRecommendationError,
    TriageCacheCompensation,
    TriageError,
    TriageStateCompensation,
)

# Export main classes for backward compatibility
__all__ = [
    'TriageErrorHandler',
    'TriageError',
    'IntentDetectionError', 
    'EntityExtractionError',
    'ToolRecommendationError',
    'TriageCacheCompensation',
    'TriageStateCompensation',
    'TriageErrorRecovery',
    'TriageErrorReporter',
    'triage_error_handler'
]

# Global triage error handler instance
triage_error_handler = TriageErrorHandler()


# Convenience functions for backward compatibility
async def handle_intent_detection_error(user_input: str, run_id: str, original_error: Exception) -> Dict[str, Any]:
    """Handle intent detection failures."""
    return await triage_error_handler.handle_intent_detection_error(user_input, run_id, original_error)


async def handle_entity_extraction_error(failed_entities: list, user_input: str, run_id: str, original_error: Exception) -> Dict[str, Any]:
    """Handle entity extraction failures."""
    return await triage_error_handler.handle_entity_extraction_error(failed_entities, user_input, run_id, original_error)


async def handle_tool_recommendation_error(intent: str, entities: Dict[str, Any], run_id: str, original_error: Exception) -> Dict[str, Any]:
    """Handle tool recommendation failures."""
    return await triage_error_handler.handle_tool_recommendation_error(intent, entities, run_id, original_error)


async def handle_with_retry(operation_func, operation_name: str, run_id: str, max_retries: int = 2, **kwargs) -> Any:
    """Handle operation with automatic retry and error recovery."""
    return await triage_error_handler.handle_with_retry(operation_func, operation_name, run_id, max_retries, **kwargs)


def get_error_metrics() -> Dict[str, Any]:
    """Get comprehensive error metrics."""
    return triage_error_handler.get_error_metrics()


def reset_metrics() -> None:
    """Reset error metrics."""
    triage_error_handler.reset_metrics()