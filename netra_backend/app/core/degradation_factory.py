"""Factory functions for creating degradation strategies.

This module provides factory functions for creating common
degradation strategies with standard configurations.
"""

from typing import Dict, List

from netra_backend.app.core.degradation_manager import GracefulDegradationManager
from netra_backend.app.core.degradation_strategies import (
    DatabaseDegradationStrategy,
    LLMDegradationStrategy,
    WebSocketDegradationStrategy,
)


def create_database_degradation_strategy(
    read_replicas: List[str],
    cache_manager
) -> DatabaseDegradationStrategy:
    """Create database degradation strategy with replicas and cache."""
    return DatabaseDegradationStrategy(read_replicas, cache_manager)


def create_llm_degradation_strategy(
    fallback_models: List[str],
    template_responses: Dict[str, str]
) -> LLMDegradationStrategy:
    """Create LLM degradation strategy with fallbacks and templates."""
    return LLMDegradationStrategy(fallback_models, template_responses)


def create_websocket_degradation_strategy(
    polling_fallback: bool = True
) -> WebSocketDegradationStrategy:
    """Create WebSocket degradation strategy with polling fallback."""
    return WebSocketDegradationStrategy(polling_fallback)


def create_default_template_responses() -> Dict[str, str]:
    """Create default template responses for LLM degradation."""
    return {
        'general': 'I apologize, but AI services are temporarily limited. Please try again later.',
        'search': 'Search functionality is temporarily unavailable. Please try again later.',
        'analysis': 'Analysis services are temporarily limited. Please try a simpler request.',
        'generation': 'Content generation is temporarily unavailable. Please try again later.'
    }


def create_default_fallback_models() -> List[str]:
    """Create default list of fallback models."""
    return [
        'gpt-3.5-turbo',
        'claude-instant',
        'text-davinci-002'
    ]


# Global degradation manager instance
degradation_manager = GracefulDegradationManager()