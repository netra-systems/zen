"""
LLM Fixtures Advanced - Advanced LLM testing patterns

Error simulation, provider switching, performance monitoring, and circuit breaker patterns.
Each function is  <= 8 lines, following modular architecture.
"""

import asyncio
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.tests.llm_fixtures_core import create_basic_llm_manager

# Type aliases
ProviderKey = str

class LLMProvider(Enum):
    """LLM provider types for testing."""
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    MOCK = "mock"

def create_error_simulating_manager(error_rate: float = 0.5) -> Mock:
    """Create LLM manager that simulates various error conditions."""
    manager = create_basic_llm_manager()
    _setup_error_simulation(manager, error_rate)
    return manager

def _setup_error_simulation(manager: Mock, error_rate: float) -> None:
    """Setup error simulation with configurable failure rate."""
    async def error_prone_call(*args, **kwargs):
        if __import__('random').random() < error_rate:
            raise NetraException("Simulated LLM failure")
        return {"content": "Success after potential failure"}
    
    manager.call_llm = AsyncMock(side_effect=error_prone_call)

def create_provider_switching_manager(providers: List[LLMProvider]) -> Mock:
    """Create LLM manager with provider switching capabilities."""
    manager = create_basic_llm_manager()
    _setup_provider_switching(manager, providers)
    return manager

def _setup_provider_switching(manager: Mock, providers: List[LLMProvider]) -> None:
    """Setup provider switching logic."""
    provider_index = 0
    
    async def switch_provider_call(*args, **kwargs):
        nonlocal provider_index
        current_provider = providers[provider_index % len(providers)]
        provider_index += 1
        return {"content": f"[{current_provider.value}] Response", "provider": current_provider.value}
    
    manager.call_llm = AsyncMock(side_effect=switch_provider_call)

def create_timeout_simulating_manager(timeout_ms: int = 5000) -> Mock:
    """Create LLM manager that simulates timeouts."""
    manager = create_basic_llm_manager()
    _setup_timeout_simulation(manager, timeout_ms)
    return manager

def _setup_timeout_simulation(manager: Mock, timeout_ms: int) -> None:
    """Setup timeout simulation."""
    async def timeout_call(*args, **kwargs):
        await asyncio.sleep(timeout_ms / 1000)
        return {"content": "Response after timeout simulation"}
    
    manager.call_llm = AsyncMock(side_effect=timeout_call)

def create_load_balancing_manager(weights: Dict[ProviderKey, float]) -> Mock:
    """Create LLM manager with weighted load balancing."""
    manager = create_basic_llm_manager()
    _setup_load_balancing(manager, weights)
    return manager

def _setup_load_balancing(manager: Mock, weights: Dict[ProviderKey, float]) -> None:
    """Setup weighted load balancing logic."""
    async def balanced_call(*args, **kwargs):
        provider = _select_weighted_provider(weights)
        return {"content": f"Response from {provider}", "provider": provider}
    
    manager.call_llm = AsyncMock(side_effect=balanced_call)

def _select_weighted_provider(weights: Dict[ProviderKey, float]) -> ProviderKey:
    """Select provider based on weights."""
    import random
    total = sum(weights.values())
    r = random.uniform(0, total)
    cumulative = 0
    for provider, weight in weights.items():
        cumulative += weight
        if r <= cumulative:
            return provider
    return list(weights.keys())[0]

def create_performance_monitoring_manager() -> Mock:
    """Create LLM manager with performance monitoring."""
    manager = create_basic_llm_manager()
    metrics = {"calls": 0, "total_time": 0, "errors": 0}
    _setup_performance_monitoring(manager, metrics)
    return manager

def _setup_performance_monitoring(manager: Mock, metrics: Dict[str, Any]) -> None:
    """Setup performance monitoring capabilities."""
    async def monitored_call(*args, **kwargs):
        start_time = datetime.now(UTC)
        try:
            metrics["calls"] += 1
            response = {"content": "Monitored response"}
            metrics["total_time"] += (datetime.now(UTC) - start_time).total_seconds()
            return response
        except Exception:
            metrics["errors"] += 1
            raise
    
    manager.call_llm = AsyncMock(side_effect=monitored_call)

def create_circuit_breaker_manager(failure_threshold: int = 5) -> Mock:
    """Create LLM manager with circuit breaker pattern."""
    manager = create_basic_llm_manager()
    state = {"failures": 0, "open": False, "last_failure": None}
    _setup_circuit_breaker(manager, state, failure_threshold)
    return manager

def _setup_circuit_breaker(manager: Mock, state: Dict[str, Any], threshold: int) -> None:
    """Setup circuit breaker functionality."""
    async def circuit_breaker_call(*args, **kwargs):
        if state["open"]:
            raise NetraException("Circuit breaker is open")
        
        try:
            response = {"content": "Circuit breaker protected response"}
            state["failures"] = 0
            return response
        except Exception:
            state["failures"] += 1
            if state["failures"] >= threshold:
                state["open"] = True
            raise
    
    manager.call_llm = AsyncMock(side_effect=circuit_breaker_call)