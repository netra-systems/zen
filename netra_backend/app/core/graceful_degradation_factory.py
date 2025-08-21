"""Factory functions for graceful degradation strategies.

Provides convenient factory functions to create degradation strategies
for common service types.
"""

from typing import Dict, List

from netra_backend.app.core.degradation_strategies import (
    DatabaseDegradationStrategy,
    LLMDegradationStrategy,
    WebSocketDegradationStrategy
)


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
