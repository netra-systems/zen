"""LLM Provider Failover L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise (mission-critical AI operations)
- Business Goal: Uninterrupted AI service availability
- Value Impact: Protects $12K MRR from provider outages and failures
- Strategic Impact: Ensures 99.9% uptime for AI-powered features

Critical Path: Provider health -> Circuit breaker -> Failover -> Recovery -> Load balancing
Coverage: Real provider switching, health monitoring, graceful degradation
"""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.config import get_settings
from netra_backend.app.db.database_manager import DatabaseManager as ConnectionManager

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class ProviderStatus(Enum):
    """LLM Provider status states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

class FailoverStrategy(Enum):
    """Failover strategies."""
    ROUND_ROBIN = "round_robin"
    PRIORITY = "priority"
    LOAD_BALANCED = "load_balanced"
    COST_OPTIMIZED = "cost_optimized"

@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    provider_type: str  # openai, anthropic, etc.
    endpoint: str
    api_key: str
    models: List[str]
    priority: int = 1  # Lower = higher priority
    max_tokens: int = 4096
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 90000
    timeout_seconds: int = 30
    retry_attempts: int = 3
    cost_per_1k_tokens: float = 0.03
    health_check_interval: int = 60
    circuit_breaker_config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

@dataclass
class LLMRequest:
    """Represents an LLM request."""
    request_id: str
    model: str
    messages: List[Dict[str, str]]
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class LLMResponse:
    """Represents an LLM response."""
    request_id: str
    provider_name: str
    model: str
    content: str
    tokens_used: int
    cost: float
    latency_ms: int
    success: bool
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

class ProviderHealthChecker:
    """Monitors health of LLM providers."""
    
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        self.health_cache = {}
        self.check_intervals = {}
        
    async def check_provider_health(self, config: ProviderConfig) -> ProviderStatus:
        """Check health of a specific provider."""
        try:
            # Simulate health check with actual API call
            health_result = await self._perform_health_check(config)
            
            # Cache health status
            await self._cache_health_status(config.name, health_result)
            
            return health_result
            
        except Exception as e:
            logger.error(f"Health check failed for {config.name}: {e}")
            await self._cache_health_status(config.name, ProviderStatus.UNHEALTHY)
            return ProviderStatus.UNHEALTHY
    
    async def _perform_health_check(self, config: ProviderConfig) -> ProviderStatus:
        """Perform actual health check against provider."""
        start_time = time.time()
        
        # Mock different provider responses
        if "unreliable" in config.name.lower():
            # Simulate intermittent failures
            if time.time() % 10 < 3:  # Fail 30% of the time
                raise Exception("Provider unavailable")
        
        if "slow" in config.name.lower():
            # Simulate slow responses
            await asyncio.sleep(0.5)
            if time.time() - start_time > config.timeout_seconds:
                return ProviderStatus.DEGRADED
        
        # Simulate successful health check
        await asyncio.sleep(0.1)  # Mock API call
        return ProviderStatus.HEALTHY
    
    async def _cache_health_status(self, provider_name: str, status: ProviderStatus):
        """Cache provider health status in Redis."""
        cache_key = f"provider_health:{provider_name}"
        health_data = {
            "status": status.value,
            "timestamp": datetime.now().isoformat(),
            "ttl": 300  # 5 minutes
        }
        
        await self.redis_service.client.setex(
            cache_key,
            300,
            json.dumps(health_data)
        )
    
    async def get_cached_health(self, provider_name: str) -> Optional[ProviderStatus]:
        """Get cached health status."""
        cache_key = f"provider_health:{provider_name}"
        cached_data = await self.redis_service.client.get(cache_key)
        
        if cached_data:
            health_data = json.loads(cached_data)
            return ProviderStatus(health_data["status"])
        
        return None
    
    async def start_health_monitoring(self, configs: List[ProviderConfig]):
        """Start continuous health monitoring."""
        for config in configs:
            asyncio.create_task(self._monitor_provider_health(config))
    
    async def _monitor_provider_health(self, config: ProviderConfig):
        """Continuously monitor a provider's health."""
        while True:
            try:
                await self.check_provider_health(config)
                await asyncio.sleep(config.health_check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error for {config.name}: {e}")
                await asyncio.sleep(30)  # Retry after 30 seconds on error

class ProviderCircuitBreaker:
    """Circuit breaker for LLM providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self.failure_threshold = config.circuit_breaker_config.get("failure_threshold", 5)
        self.recovery_timeout = config.circuit_breaker_config.get("recovery_timeout", 60)
        self.success_threshold = config.circuit_breaker_config.get("success_threshold", 3)
        self.half_open_success_count = 0
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                self.half_open_success_count = 0
            else:
                raise Exception(f"Circuit breaker OPEN for {self.config.name}")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful request."""
        if self.state == "half_open":
            self.half_open_success_count += 1
            if self.half_open_success_count >= self.success_threshold:
                self.state = "closed"
                self.failure_count = 0
        elif self.state == "closed":
            self.failure_count = max(0, self.failure_count - 1)
    
    def _on_failure(self):
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
        elif self.state == "half_open":
            self.state = "open"
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset circuit breaker."""
        if self.last_failure_time is None:
            return False
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "can_execute": self.state != "open" or self._should_attempt_reset()
        }

class MockLLMProvider:
    """Mock LLM provider for testing."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.request_count = 0
        self.total_tokens = 0
        
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a mock response."""
        start_time = time.time()
        
        # Simulate different provider behaviors
        if "slow" in self.config.name.lower():
            await asyncio.sleep(0.3)
        elif "fast" in self.config.name.lower():
            await asyncio.sleep(0.05)
        else:
            await asyncio.sleep(0.1)
        
        # Simulate failures for unreliable providers
        if "unreliable" in self.config.name.lower():
            if self.request_count % 4 == 0:  # Fail every 4th request
                raise Exception("Provider temporarily unavailable")
        
        self.request_count += 1
        tokens_used = 150 + (len(request.messages) * 25)
        self.total_tokens += tokens_used
        
        latency_ms = int((time.time() - start_time) * 1000)
        cost = (tokens_used / 1000) * self.config.cost_per_1k_tokens
        
        return LLMResponse(
            request_id=request.request_id,
            provider_name=self.config.name,
            model=request.model,
            content=f"Mock response from {self.config.name} for: {request.messages[-1].get('content', '')}",
            tokens_used=tokens_used,
            cost=cost,
            latency_ms=latency_ms,
            success=True
        )

class LLMProviderManager:
    """Manages multiple LLM providers with failover."""
    
    def __init__(self, health_checker: ProviderHealthChecker):
        self.providers: Dict[str, MockLLMProvider] = {}
        self.configs: Dict[str, ProviderConfig] = {}
        self.circuit_breakers: Dict[str, ProviderCircuitBreaker] = {}
        self.health_checker = health_checker
        self.failover_strategy = FailoverStrategy.PRIORITY
        self.current_provider_index = 0
        
    def register_provider(self, config: ProviderConfig):
        """Register a new LLM provider."""
        self.configs[config.name] = config
        self.providers[config.name] = MockLLMProvider(config)
        self.circuit_breakers[config.name] = ProviderCircuitBreaker(config)
    
    async def get_available_providers(self, model: str) -> List[str]:
        """Get list of available providers for a specific model."""
        available = []
        
        for name, config in self.configs.items():
            if not config.enabled:
                continue
                
            if model not in config.models:
                continue
            
            # Check circuit breaker state
            cb_state = self.circuit_breakers[name].get_state()
            if not cb_state["can_execute"]:
                continue
            
            # Check health status
            health = await self.health_checker.get_cached_health(name)
            if health in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]:
                available.append(name)
        
        return self._sort_providers_by_strategy(available)
    
    def _sort_providers_by_strategy(self, provider_names: List[str]) -> List[str]:
        """Sort providers based on failover strategy."""
        if self.failover_strategy == FailoverStrategy.PRIORITY:
            return sorted(provider_names, key=lambda name: self.configs[name].priority)
        elif self.failover_strategy == FailoverStrategy.COST_OPTIMIZED:
            return sorted(provider_names, key=lambda name: self.configs[name].cost_per_1k_tokens)
        elif self.failover_strategy == FailoverStrategy.ROUND_ROBIN:
            # Simple round-robin rotation
            sorted_providers = sorted(provider_names)
            if sorted_providers:
                self.current_provider_index = (self.current_provider_index + 1) % len(sorted_providers)
                return sorted_providers[self.current_provider_index:] + sorted_providers[:self.current_provider_index]
        
        return provider_names
    
    async def execute_request(self, request: LLMRequest) -> LLMResponse:
        """Execute LLM request with failover support."""
        available_providers = await self.get_available_providers(request.model)
        
        if not available_providers:
            raise Exception(f"No available providers for model {request.model}")
        
        last_error = None
        
        for provider_name in available_providers:
            try:
                provider = self.providers[provider_name]
                circuit_breaker = self.circuit_breakers[provider_name]
                
                # Execute with circuit breaker protection
                response = await circuit_breaker.call(
                    provider.generate_response,
                    request
                )
                
                logger.info(f"Request {request.request_id} served by {provider_name}")
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_name} failed for request {request.request_id}: {e}")
                continue
        
        # All providers failed
        raise Exception(f"All providers failed. Last error: {last_error}")
    
    async def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all providers."""
        stats = {}
        
        for name, provider in self.providers.items():
            cb_state = self.circuit_breakers[name].get_state()
            health = await self.health_checker.get_cached_health(name)
            
            stats[name] = {
                "request_count": provider.request_count,
                "total_tokens": provider.total_tokens,
                "circuit_breaker_state": cb_state["state"],
                "failure_count": cb_state["failure_count"],
                "health_status": health.value if health else "unknown",
                "enabled": self.configs[name].enabled
            }
        
        return stats

class FailoverTestManager:
    """Manages LLM provider failover testing."""
    
    def __init__(self):
        self.redis_service = None
        self.health_checker = None
        self.provider_manager = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.health_checker = ProviderHealthChecker(self.redis_service)
        self.provider_manager = LLMProviderManager(self.health_checker)
        
        # Set up test providers
        await self.setup_test_providers()
    
    async def setup_test_providers(self):
        """Set up test LLM providers."""
        providers = [
            ProviderConfig(
                name="primary_openai",
                provider_type="openai",
                endpoint="https://api.openai.com/v1",
                api_key="test_key_1",
                models=[LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value],
                priority=1,
                cost_per_1k_tokens=0.03,
                circuit_breaker_config={
                    "failure_threshold": 3,
                    "recovery_timeout": 30,
                    "success_threshold": 2
                }
            ),
            ProviderConfig(
                name="backup_anthropic",
                provider_type="anthropic",
                endpoint="https://api.anthropic.com/v1",
                api_key="test_key_2",
                models=["claude-3", "claude-2"],
                priority=2,
                cost_per_1k_tokens=0.025,
                circuit_breaker_config={
                    "failure_threshold": 5,
                    "recovery_timeout": 60,
                    "success_threshold": 3
                }
            ),
            ProviderConfig(
                name="unreliable_provider",
                provider_type="test",
                endpoint="https://test.api.com/v1",
                api_key="test_key_3",
                models=[LLMModel.GEMINI_2_5_FLASH.value],
                priority=3,
                cost_per_1k_tokens=0.02,
                circuit_breaker_config={
                    "failure_threshold": 2,
                    "recovery_timeout": 15,
                    "success_threshold": 1
                }
            ),
            ProviderConfig(
                name="slow_provider",
                provider_type="test",
                endpoint="https://slow.api.com/v1",
                api_key="test_key_4",
                models=[LLMModel.GEMINI_2_5_FLASH.value],
                priority=4,
                cost_per_1k_tokens=0.01
            )
        ]
        
        for config in providers:
            self.provider_manager.register_provider(config)
        
        # Start health monitoring
        await self.health_checker.start_health_monitoring(providers)
    
    def create_test_request(self, request_id: str = None, model: str = LLMModel.GEMINI_2_5_FLASH.value) -> LLMRequest:
        """Create a test LLM request."""
        return LLMRequest(
            request_id=request_id or f"req_{int(time.time() * 1000)}",
            model=model,
            messages=[
                {"role": "user", "content": "Hello, this is a test request"}
            ],
            max_tokens=150,
            temperature=0.7
        )
    
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()

@pytest.fixture
async def failover_manager():
    """Create failover test manager."""
    manager = FailoverTestManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_provider_registration_and_health(failover_manager):
    """Test provider registration and health checking."""
    manager = failover_manager
    
    # Check that providers are registered
    assert "primary_openai" in manager.provider_manager.configs
    assert "backup_anthropic" in manager.provider_manager.configs
    
    # Test health checking
    primary_config = manager.provider_manager.configs["primary_openai"]
    health_status = await manager.health_checker.check_provider_health(primary_config)
    
    assert health_status == ProviderStatus.HEALTHY
    
    # Test cached health retrieval
    cached_health = await manager.health_checker.get_cached_health("primary_openai")
    assert cached_health == ProviderStatus.HEALTHY

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_basic_request_execution(failover_manager):
    """Test basic LLM request execution."""
    manager = failover_manager
    
    # Create test request
    request = manager.create_test_request("test_basic_001")
    
    # Execute request
    response = await manager.provider_manager.execute_request(request)
    
    assert response.success is True
    assert response.request_id == "test_basic_001"
    assert response.provider_name == "primary_openai"  # Should use highest priority
    assert response.tokens_used > 0
    assert response.cost > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_provider_failover_on_circuit_breaker(failover_manager):
    """Test failover when circuit breaker opens."""
    manager = failover_manager
    
    # Trigger failures on unreliable provider to open circuit breaker
    unreliable_config = manager.provider_manager.configs["unreliable_provider"]
    unreliable_config.priority = 1  # Make it highest priority
    
    # Execute requests until circuit breaker opens
    failures = 0
    for i in range(5):
        try:
            request = manager.create_test_request(f"cb_test_{i}")
            await manager.provider_manager.execute_request(request)
        except Exception:
            failures += 1
    
    # Check circuit breaker state
    cb_state = manager.provider_manager.circuit_breakers["unreliable_provider"].get_state()
    assert cb_state["state"] == "open"
    
    # Next request should failover to backup provider
    request = manager.create_test_request("failover_test")
    response = await manager.provider_manager.execute_request(request)
    
    assert response.success is True
    assert response.provider_name != "unreliable_provider"

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_provider_priority_ordering(failover_manager):
    """Test provider selection based on priority."""
    manager = failover_manager
    
    # Get available providers for gpt-4
    available = await manager.provider_manager.get_available_providers(LLMModel.GEMINI_2_5_FLASH.value)
    
    # Should be ordered by priority (lower number = higher priority)
    priorities = [manager.provider_manager.configs[name].priority for name in available]
    assert priorities == sorted(priorities)

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_round_robin_strategy(failover_manager):
    """Test round-robin failover strategy."""
    manager = failover_manager
    
    # Switch to round-robin strategy
    manager.provider_manager.failover_strategy = FailoverStrategy.ROUND_ROBIN
    
    # Execute multiple requests and track which providers are used
    used_providers = []
    
    for i in range(6):
        request = manager.create_test_request(f"rr_test_{i}")
        response = await manager.provider_manager.execute_request(request)
        used_providers.append(response.provider_name)
    
    # Should use different providers in rotation
    unique_providers = set(used_providers)
    assert len(unique_providers) > 1

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_cost_optimized_strategy(failover_manager):
    """Test cost-optimized failover strategy."""
    manager = failover_manager
    
    # Switch to cost-optimized strategy
    manager.provider_manager.failover_strategy = FailoverStrategy.COST_OPTIMIZED
    
    # Get available providers sorted by cost
    available = await manager.provider_manager.get_available_providers(LLMModel.GEMINI_2_5_FLASH.value)
    
    # Should be ordered by cost (lowest first)
    costs = [manager.provider_manager.configs[name].cost_per_1k_tokens for name in available]
    assert costs == sorted(costs)

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_circuit_breaker_recovery(failover_manager):
    """Test circuit breaker recovery mechanism."""
    manager = failover_manager
    
    # Get circuit breaker for unreliable provider
    cb = manager.provider_manager.circuit_breakers["unreliable_provider"]
    
    # Force circuit breaker to open
    cb.state = "open"
    cb.failure_count = 10
    cb.last_failure_time = time.time() - 70  # 70 seconds ago
    
    # Should attempt reset due to recovery timeout
    assert cb._should_attempt_reset() is True
    
    # Execute request - should move to half_open
    request = manager.create_test_request("recovery_test")
    
    try:
        await cb.call(lambda: "test_success")
        # If successful, should move to closed after enough successes
    except Exception:
        # If failed, should move back to open
        pass
    
    # Verify state changed from open
    assert cb.state != "open" or cb._should_attempt_reset()

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_no_available_providers_error(failover_manager):
    """Test error when no providers are available."""
    manager = failover_manager
    
    # Disable all providers
    for config in manager.provider_manager.configs.values():
        config.enabled = False
    
    # Request should fail with appropriate error
    request = manager.create_test_request("no_providers_test")
    
    with pytest.raises(Exception) as exc_info:
        await manager.provider_manager.execute_request(request)
    
    assert "No available providers" in str(exc_info.value)

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_provider_statistics_tracking(failover_manager):
    """Test provider statistics tracking."""
    manager = failover_manager
    
    # Execute several requests
    for i in range(5):
        request = manager.create_test_request(f"stats_test_{i}")
        await manager.provider_manager.execute_request(request)
    
    # Get provider statistics
    stats = await manager.provider_manager.get_provider_stats()
    
    assert "primary_openai" in stats
    primary_stats = stats["primary_openai"]
    
    assert primary_stats["request_count"] >= 5
    assert primary_stats["total_tokens"] > 0
    assert "circuit_breaker_state" in primary_stats
    assert "health_status" in primary_stats

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_concurrent_requests_with_failover(failover_manager):
    """Test concurrent requests with failover handling."""
    manager = failover_manager
    
    # Execute many concurrent requests
    tasks = []
    for i in range(20):
        request = manager.create_test_request(f"concurrent_{i}")
        task = manager.provider_manager.execute_request(request)
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count successful responses
    successful = [r for r in responses if isinstance(r, LLMResponse) and r.success]
    failed = [r for r in responses if isinstance(r, Exception)]
    
    assert len(successful) >= 15  # At least 75% success rate
    
    # Verify responses have valid data
    for response in successful:
        assert response.tokens_used > 0
        assert response.latency_ms > 0
        assert response.provider_name in manager.provider_manager.configs

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_failover_performance_benchmarks(failover_manager):
    """Benchmark failover performance."""
    manager = failover_manager
    
    # Benchmark normal operations
    start_time = time.time()
    
    tasks = []
    for i in range(100):
        request = manager.create_test_request(f"perf_{i}")
        task = manager.provider_manager.execute_request(request)
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    successful_responses = [r for r in responses if isinstance(r, LLMResponse)]
    
    assert len(successful_responses) >= 90  # 90% success rate
    
    # Performance assertions
    assert total_time < 15.0  # 100 requests in under 15 seconds
    avg_time = total_time / len(successful_responses)
    assert avg_time < 0.15  # Average under 150ms per request
    
    # Calculate average latency
    avg_latency = sum(r.latency_ms for r in successful_responses) / len(successful_responses)
    assert avg_latency < 500  # Average latency under 500ms
    
    logger.info(f"Failover Performance: {avg_time*1000:.1f}ms avg total, {avg_latency:.1f}ms avg latency")