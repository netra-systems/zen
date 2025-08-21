"""Graceful degradation strategies for system resilience.

Provides mechanisms to gracefully degrade functionality when system components
fail, ensuring core operations continue with reduced but acceptable performance.

This module consolidates all graceful degradation functionality and re-exports
components from their single sources of truth for backward compatibility.
"""

from typing import Dict, List

from app.core.degradation_types import (
    DegradationLevel,
    DegradationPolicy,
    DegradationStrategy,
    ServiceStatus,
    ServiceTier
)
from app.core.degradation_strategies import (
    DatabaseDegradationStrategy,
    LLMDegradationStrategy,
    WebSocketDegradationStrategy
)
from app.core.degradation_manager import (
    GracefulDegradationManager,
    degradation_manager
)
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Re-export consolidated components for backward compatibility
__all__ = [
    'DegradationLevel',
    'DegradationPolicy', 
    'DegradationStrategy',
    'ServiceStatus',
    'ServiceTier',
    'DatabaseDegradationStrategy',
    'LLMDegradationStrategy',
    'WebSocketDegradationStrategy',
    'GracefulDegradationManager',
    'degradation_manager',
    'create_database_degradation_strategy',
    'create_llm_degradation_strategy',
    'create_websocket_degradation_strategy'
]


# Factory functions for backward compatibility
def create_database_degradation_strategy(
    read_replicas: List[str],
    cache_manager
) -> DatabaseDegradationStrategy:
    """Create database degradation strategy."""
    return DatabaseDegradationStrategy(read_replicas, cache_manager)


def create_llm_degradation_strategy(
    fallback_models: List[str],
    template_responses: Dict[str, str]
) -> LLMDegradationStrategy:
    """Create LLM degradation strategy."""
    return LLMDegradationStrategy(fallback_models, template_responses)


def create_websocket_degradation_strategy(
    polling_fallback: bool = True
) -> WebSocketDegradationStrategy:
    """Create WebSocket degradation strategy."""
    return WebSocketDegradationStrategy(polling_fallback)