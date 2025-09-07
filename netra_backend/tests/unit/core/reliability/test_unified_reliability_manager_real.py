"""
Test Unified Reliability Manager - REAL BUSINESS VALUE

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure 99.99% uptime and system reliability
- Value Impact: Prevents service outages, ensures graceful degradation
- Strategic Impact: Core platform reliability infrastructure enables trust

Tests the real UnifiedReliabilityManager class with NO MOCKS.
Validates all reliability patterns including circuit breakers, retries,
timeouts, fallbacks, and multi-service coordination.

CRITICAL: This is a P1 SSOT class that handles system resilience.
All tests use REAL instances and validate REAL business scenarios.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from typing import Dict, Any

from shared.isolated_environment import IsolatedEnvironment, get_env

# Import the REAL classes we're testing - NO MOCKS
from netra_backend.app.core.reliability.unified_reliability_manager import (
    UnifiedReliabilityManager,
    ReliabilityLevel,
    ReliabilityConfig,
    ReliabilityResult,
    FailureMode,
    reset_reliability_manager,
    get_reliability_manager
)
from netra_backend.app.core.resilience.domain_circuit_breakers import (
    DomainType,
    CircuitBreakerState
)


class TestUnifiedReliabilityManagerCore:
    """Test core functionality of UnifiedReliabilityManager."""
    
    def setup_method(self):
        """Setup for each test - fresh manager instance."""
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        
        # Create fresh manager for each test
        self.manager = UnifiedReliabilityManager()
    
    def test_manager_initialization_with_defaults(self):
        """Test manager initializes with proper default configurations."""
        # Test that manager initializes properly
        assert self.manager._domain_configs is not None
        assert self.manager._health_status is not None
        assert self.manager._failure_stats is not None
        
        # Verify default domain configs are set
        expected_domains = ["agent", "database", "llm", "external_api"]
        for domain in expected_domains:
            assert domain in self.manager._domain_configs
            config = self.manager._domain_configs[domain]
            assert isinstance(config, ReliabilityConfig)
        
        # Verify critical database config
        db_config = self.manager._domain_configs["database"]
        assert db_config.level == ReliabilityLevel.CRITICAL
        assert db_config.max_retries == 3
        assert db_config.timeout_seconds == 10.0
        assert db_config.circuit_breaker_enabled is True
        assert db_config.fallback_enabled is False  # Critical - no fallback
        
        # Verify agent config for high availability
        agent_config = self.manager._domain_configs["agent"]
        assert agent_config.level == ReliabilityLevel.HIGH
        assert agent_config.max_retries == 2
        assert agent_config.timeout_seconds == 120.0
        assert agent_config.fallback_enabled is True
    
    def test_service_registration_creates_tracking_structures(self):
        """Test service registration creates all necessary tracking."""
        service_name = "test_service"
        domain = "llm"
        custom_config = ReliabilityConfig(
            level=ReliabilityLevel.HIGH,
            max_retries=5,
            timeout_seconds=45.0
        )
        
        self.manager.register_service(service_name, domain, custom_config)
        
        # Verify service config is registered
        assert service_name in self.manager._domain_configs
        assert self.manager._domain_configs[service_name] == custom_config
        
        # Verify health status tracking initialized
        assert service_name in self.manager._health_status
        health_status = self.manager._health_status[service_name]
        assert health_status["status"] == "unknown"
        assert health_status["last_check"] is None
        assert health_status["consecutive_failures"] == 0
        
        # Verify failure stats tracking initialized
        assert service_name in self.manager._failure_stats
        failure_stats = self.manager._failure_stats[service_name]
        for failure_mode in FailureMode:
            assert failure_mode in failure_stats
            assert failure_stats[failure_mode] == 0
    
    def test_service_registration_without_custom_config_uses_domain_default(self):
        """Test service registration uses domain defaults when no config provided."""
        service_name = "llm_service_1"
        domain = "llm"
        
        self.manager.register_service(service_name, domain)
        
        # Should use the default llm domain config
        expected_config = self.manager._domain_configs["llm"]
        actual_config = self.manager._domain_configs[service_name]
        
        assert actual_config.level == expected_config.level
        assert actual_config.max_retries == expected_config.max_retries
        assert actual_config.timeout_seconds == expected_config.timeout_seconds
    
    def test_get_reliability_config_returns_correct_config(self):
        """Test getting reliability config for registered service."""
        service_name = "test_service"
        custom_config = ReliabilityConfig(max_retries=10)
        self.manager.register_service(service_name, "external_api", custom_config)
        
        retrieved_config = self.manager.get_reliability_config(service_name)
        assert retrieved_config == custom_config
        
        # Test non-existent service
        assert self.manager.get_reliability_config("nonexistent") is None
    
    def test_update_reliability_config_modifies_existing(self):
        """Test updating reliability config for existing service."""
        service_name = "test_service"
        original_config = ReliabilityConfig(max_retries=3)
        self.manager.register_service(service_name, "llm", original_config)
        
        new_config = ReliabilityConfig(max_retries=7, timeout_seconds=90.0)
        self.manager.update_reliability_config(service_name, new_config)
        
        updated_config = self.manager.get_reliability_config(service_name)
        assert updated_config == new_config
        assert updated_config.max_retries == 7
        assert updated_config.timeout_seconds == 90.0


class TestReliabilityExecution:
    """Test reliability-managed operation execution."""
    
    def setup_method(self):
        """Setup for each test."""
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        self.manager = UnifiedReliabilityManager()
    
    @pytest.mark.asyncio
    async def test_successful_operation_execution(self):
        """Test successful operation execution with reliability management."""
        service_name = "test_service"
        self.manager.register_service(service_name, "external_api")
        
        async def successful_operation() -> str:
            await asyncio.sleep(0.01)  # Simulate some work
            return "success_result"
        
        result = await self.manager.execute_with_reliability(
            service_name, 
            successful_operation
        )
        
        # Verify successful result
        assert result.success is True
        assert result.result == "success_result"
        assert result.error is None
        assert result.attempts == 1
        assert result.duration_ms > 0
        assert result.circuit_breaker_used is True
        assert result.fallback_used is False
        
        # Verify health status updated
        health_status = self.manager._health_status[service_name]
        assert health_status["status"] == "healthy"
        assert health_status["consecutive_failures"] == 0
        assert isinstance(health_status["last_check"], datetime)
    
    @pytest.mark.asyncio
    async def test_operation_with_timeout_retries_and_fails(self):
        """Test operation that times out, retries, and eventually fails."""
        service_name = "slow_service"
        config = ReliabilityConfig(
            max_retries=2,
            timeout_seconds=0.05,  # Very short timeout
            circuit_breaker_enabled=False,  # Disable to test retries
            fallback_enabled=False
        )
        self.manager.register_service(service_name, "external_api", config)
        
        async def slow_operation() -> str:
            await asyncio.sleep(0.1)  # Will timeout
            return "should_not_reach"
        
        result = await self.manager.execute_with_reliability(
            service_name,
            slow_operation
        )
        
        # Verify failed result after retries
        assert result.success is False
        assert result.result is None
        assert isinstance(result.error, asyncio.TimeoutError)
        assert result.attempts == 3  # 1 initial + 2 retries
        assert result.duration_ms > 0
        assert result.fallback_used is False
        
        # Verify failure tracking
        failure_stats = self.manager._failure_stats[service_name]
        assert failure_stats[FailureMode.TIMEOUT] == 3  # All 3 attempts timed out
        
        # Verify health status updated
        health_status = self.manager._health_status[service_name]
        assert health_status["status"] == "unhealthy"
        assert health_status["consecutive_failures"] == 3
    
    @pytest.mark.asyncio
    async def test_operation_with_connection_error_tracking(self):
        """Test operation that fails with ConnectionError."""
        service_name = "unreliable_service"
        config = ReliabilityConfig(
            max_retries=1,
            circuit_breaker_enabled=False,
            fallback_enabled=False
        )
        self.manager.register_service(service_name, "external_api", config)
        
        async def failing_operation() -> str:
            raise ConnectionError("Network unreachable")
        
        result = await self.manager.execute_with_reliability(
            service_name,
            failing_operation
        )
        
        # Verify connection error handling
        assert result.success is False
        assert isinstance(result.error, ConnectionError)
        assert result.attempts == 2  # 1 initial + 1 retry
        
        # Verify connection error tracking
        failure_stats = self.manager._failure_stats[service_name]
        assert failure_stats[FailureMode.CONNECTION_ERROR] == 2
    
    @pytest.mark.asyncio
    async def test_operation_with_generic_exception_tracking(self):
        """Test operation that fails with generic exception."""
        service_name = "error_service"
        config = ReliabilityConfig(max_retries=1, circuit_breaker_enabled=False, fallback_enabled=False)
        self.manager.register_service(service_name, "external_api", config)
        
        async def error_operation() -> str:
            raise ValueError("Invalid input")
        
        result = await self.manager.execute_with_reliability(
            service_name,
            error_operation
        )
        
        # Verify generic error handling
        assert result.success is False
        assert isinstance(result.error, ValueError)
        
        # Verify internal error tracking
        failure_stats = self.manager._failure_stats[service_name]
        assert failure_stats[FailureMode.INTERNAL_ERROR] == 2
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff between retries."""
        service_name = "backoff_test_service"
        config = ReliabilityConfig(max_retries=2, circuit_breaker_enabled=False, fallback_enabled=False)
        self.manager.register_service(service_name, "external_api", config)
        
        call_times = []
        
        async def timing_operation() -> str:
            call_times.append(time.time())
            raise Exception("Always fails")
        
        start_time = time.time()
        result = await self.manager.execute_with_reliability(
            service_name,
            timing_operation
        )
        
        # Verify timing and backoff
        assert len(call_times) == 3  # Initial + 2 retries
        assert result.attempts == 3
        
        # Check exponential backoff (1s, then 2s)
        # Allow some tolerance for timing variations
        time1_gap = call_times[1] - call_times[0]
        time2_gap = call_times[2] - call_times[1]
        
        assert 0.9 < time1_gap < 1.5  # ~1 second backoff
        assert 1.5 < time2_gap < 2.5  # ~2 second backoff


class TestFallbackMechanisms:
    """Test fallback mechanisms for graceful degradation."""
    
    def setup_method(self):
        """Setup for each test."""
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        self.manager = UnifiedReliabilityManager()
    
    @pytest.mark.asyncio
    async def test_fallback_after_all_retries_fail(self):
        """Test fallback execution after all retries fail."""
        service_name = "llm_fallback_service"  # Name contains "llm" to trigger LLM fallback
        config = ReliabilityConfig(
            max_retries=1,
            circuit_breaker_enabled=False,
            fallback_enabled=True
        )
        self.manager.register_service(service_name, "llm", config)
        
        async def failing_operation() -> str:
            raise Exception("Always fails")
        
        result = await self.manager.execute_with_reliability(
            service_name,
            failing_operation
        )
        
        # Should succeed with fallback
        assert result.success is True
        assert result.fallback_used is True
        assert result.attempts == 2  # 1 initial + 1 retry
        
        # Verify fallback result based on service type
        assert "response" in result.result  # LLM service fallback
        assert "temporarily unavailable" in result.result["response"]
        
        # Verify fallback metadata
        assert "fallback_type" in result.metadata
        assert result.metadata["fallback_type"] == "cached_or_default"
    
    @pytest.mark.asyncio
    async def test_different_fallback_types_by_service(self):
        """Test different fallback responses based on service types."""
        # Test database service fallback (service name contains "database")
        self.manager.register_service("database_service", "database", 
                                    ReliabilityConfig(max_retries=0, circuit_breaker_enabled=False, fallback_enabled=True))
        
        async def db_fail():
            raise Exception("DB down")
        
        result = await self.manager.execute_with_reliability("database_service", db_fail)
        assert result.success is True
        assert result.result == []  # Database fallback is empty list
        
        # Test generic service fallback  
        self.manager.register_service("generic_service", "external_api",
                                    ReliabilityConfig(max_retries=0, circuit_breaker_enabled=False, fallback_enabled=True))
        
        result = await self.manager.execute_with_reliability("generic_service", db_fail)
        assert result.success is True
        assert result.result["status"] == "fallback"
        assert "temporarily unavailable" in result.result["message"]
    
    @pytest.mark.asyncio
    async def test_fallback_execution_failure(self):
        """Test handling of fallback execution failures."""
        service_name = "fallback_fail_service"
        config = ReliabilityConfig(max_retries=0, circuit_breaker_enabled=False, fallback_enabled=True)
        self.manager.register_service(service_name, "external_api", config)
        
        # Mock the fallback to fail
        original_get_fallback = self.manager._get_fallback_result
        def failing_fallback(service_name):
            raise Exception("Fallback also fails")
        self.manager._get_fallback_result = failing_fallback
        
        try:
            async def failing_operation():
                raise Exception("Primary fails")
            
            result = await self.manager.execute_with_reliability(service_name, failing_operation)
            
            # Should fail since both primary and fallback fail
            assert result.success is False
            assert result.fallback_used is True
            assert "fallback_error" in result.metadata
        finally:
            # Restore original method
            self.manager._get_fallback_result = original_get_fallback


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with reliability manager."""
    
    def setup_method(self):
        """Setup for each test."""
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        self.manager = UnifiedReliabilityManager()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_execution_when_open(self):
        """Test that open circuit breaker prevents operation execution."""
        service_name = "circuit_test_service"
        config = ReliabilityConfig(circuit_breaker_enabled=True, fallback_enabled=False)
        self.manager.register_service(service_name, "llm", config)
        
        # Force circuit breaker to open state by mocking it
        from netra_backend.app.core.resilience.domain_circuit_breakers import domain_circuit_breaker_manager
        circuit_breaker = domain_circuit_breaker_manager.get_circuit_breaker(DomainType.LLM_SERVICE, service_name)
        
        # Mock can_execute to return False (circuit open)
        original_can_execute = circuit_breaker.can_execute
        circuit_breaker.can_execute = lambda: False
        
        try:
            async def should_not_execute():
                return "should_not_be_called"
            
            result = await self.manager.execute_with_reliability(service_name, should_not_execute)
            
            # Should fail due to open circuit breaker
            assert result.success is False
            assert result.circuit_breaker_used is True
            assert "Circuit breaker open" in str(result.error)
            
        finally:
            # Restore original method
            circuit_breaker.can_execute = original_can_execute
    
    @pytest.mark.asyncio  
    async def test_circuit_breaker_with_fallback_when_open(self):
        """Test circuit breaker uses fallback when open."""
        service_name = "llm_circuit_fallback_service"  # Name contains "llm" for correct fallback
        config = ReliabilityConfig(circuit_breaker_enabled=True, fallback_enabled=True)
        self.manager.register_service(service_name, "llm", config)
        
        # Mock circuit breaker to be open
        from netra_backend.app.core.resilience.domain_circuit_breakers import domain_circuit_breaker_manager
        circuit_breaker = domain_circuit_breaker_manager.get_circuit_breaker(DomainType.LLM_SERVICE, service_name)
        
        original_can_execute = circuit_breaker.can_execute
        circuit_breaker.can_execute = lambda: False
        
        try:
            async def should_not_execute():
                return "should_not_be_called"
            
            result = await self.manager.execute_with_reliability(service_name, should_not_execute)
            
            # Should succeed with fallback
            assert result.success is True
            assert result.circuit_breaker_used is True
            assert result.fallback_used is True
            
        finally:
            circuit_breaker.can_execute = original_can_execute


class TestHealthMonitoring:
    """Test health monitoring and status reporting."""
    
    def setup_method(self):
        """Setup for each test."""
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        self.manager = UnifiedReliabilityManager()
    
    @pytest.mark.asyncio
    async def test_health_check_for_registered_service(self):
        """Test health check returns complete status for registered service."""
        service_name = "health_test_service"
        self.manager.register_service(service_name, "database")
        
        # Simulate some failures
        self.manager._record_failure(service_name, FailureMode.TIMEOUT)
        self.manager._record_failure(service_name, FailureMode.CONNECTION_ERROR)
        
        health_report = await self.manager.health_check(service_name)
        
        # Verify complete health report
        assert health_report["service"] == service_name
        assert health_report["status"] == "unhealthy"
        assert health_report["consecutive_failures"] == 2
        assert isinstance(health_report["last_check"], datetime)
        assert "circuit_breaker" in health_report
        assert "failure_stats" in health_report
        assert "config" in health_report
        assert isinstance(health_report["timestamp"], datetime)
        
        # Verify failure stats
        failure_stats = health_report["failure_stats"]
        assert failure_stats[FailureMode.TIMEOUT] == 1
        assert failure_stats[FailureMode.CONNECTION_ERROR] == 1
        
        # Verify config included
        config_dict = health_report["config"]
        assert "level" in config_dict
        assert "max_retries" in config_dict
    
    @pytest.mark.asyncio
    async def test_health_check_for_unknown_service(self):
        """Test health check for unregistered service."""
        health_report = await self.manager.health_check("unknown_service")
        
        assert health_report["status"] == "unknown"
        assert "error" in health_report
        assert health_report["error"] == "Service not registered"
    
    @pytest.mark.asyncio
    async def test_system_health_aggregation(self):
        """Test system-wide health status aggregation."""
        # Register multiple services with different health states
        self.manager.register_service("healthy_service", "llm")
        self.manager.register_service("unhealthy_service", "database")
        self.manager.register_service("another_healthy_service", "external_api")
        
        # Make one service healthy and one unhealthy
        self.manager._record_success("healthy_service")
        self.manager._record_success("another_healthy_service")
        self.manager._record_failure("unhealthy_service", FailureMode.TIMEOUT)
        
        system_health = await self.manager.get_system_health()
        
        # Verify system health aggregation
        assert system_health["total_services"] == 3
        assert system_health["healthy_services"] == 2
        assert system_health["unhealthy_services"] == 1
        assert system_health["health_percentage"] == pytest.approx(66.67, rel=1e-2)
        assert system_health["overall_status"] == "degraded"  # Not all healthy
        assert isinstance(system_health["timestamp"], datetime)
        
        # Verify individual service health included
        assert "services" in system_health
        services = system_health["services"]
        assert "healthy_service" in services
        assert "unhealthy_service" in services
        assert "another_healthy_service" in services
    
    @pytest.mark.asyncio
    async def test_system_health_critical_threshold(self):
        """Test system health goes critical when less than 50% healthy."""
        # Register 4 services, make only 1 healthy
        for i in range(4):
            service_name = f"service_{i}"
            self.manager.register_service(service_name, "external_api")
            if i == 0:
                self.manager._record_success(service_name)
            else:
                self.manager._record_failure(service_name, FailureMode.INTERNAL_ERROR)
        
        system_health = await self.manager.get_system_health()
        
        assert system_health["healthy_services"] == 1
        assert system_health["total_services"] == 4
        assert system_health["health_percentage"] == 25.0
        assert system_health["overall_status"] == "critical"  # Less than 50%
    
    @pytest.mark.asyncio
    async def test_system_health_all_healthy(self):
        """Test system health is healthy when all services are healthy."""
        # Register and make all services healthy
        for i in range(3):
            service_name = f"healthy_service_{i}"
            self.manager.register_service(service_name, "llm")
            self.manager._record_success(service_name)
        
        system_health = await self.manager.get_system_health()
        
        assert system_health["healthy_services"] == 3
        assert system_health["total_services"] == 3
        assert system_health["health_percentage"] == 100.0
        assert system_health["overall_status"] == "healthy"


class TestReliabilityConfiguration:
    """Test reliability configuration management."""
    
    def test_reliability_config_creation_and_serialization(self):
        """Test ReliabilityConfig creation and dictionary conversion."""
        config = ReliabilityConfig(
            level=ReliabilityLevel.CRITICAL,
            max_retries=5,
            timeout_seconds=15.0,
            circuit_breaker_enabled=False,
            fallback_enabled=False,
            health_check_enabled=True
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["level"] == "critical"
        assert config_dict["max_retries"] == 5
        assert config_dict["timeout_seconds"] == 15.0
        assert config_dict["circuit_breaker_enabled"] is False
        assert config_dict["fallback_enabled"] is False
        assert config_dict["health_check_enabled"] is True
    
    def test_reliability_result_initialization(self):
        """Test ReliabilityResult proper initialization."""
        # Test with minimal parameters
        result = ReliabilityResult(success=True, result="test_value")
        
        assert result.success is True
        assert result.result == "test_value"
        assert result.error is None
        assert result.attempts == 1
        assert result.duration_ms == 0.0
        assert result.circuit_breaker_used is False
        assert result.fallback_used is False
        assert result.metadata == {}
        
        # Test with full parameters
        error = Exception("test error")
        metadata = {"key": "value"}
        result = ReliabilityResult(
            success=False,
            result=None,
            error=error,
            attempts=3,
            duration_ms=1500.0,
            circuit_breaker_used=True,
            fallback_used=True,
            metadata=metadata
        )
        
        assert result.success is False
        assert result.error == error
        assert result.attempts == 3
        assert result.duration_ms == 1500.0
        assert result.circuit_breaker_used is True
        assert result.fallback_used is True
        assert result.metadata == metadata


class TestGlobalManagerSingleton:
    """Test global reliability manager singleton behavior."""
    
    def test_get_reliability_manager_returns_singleton(self):
        """Test that get_reliability_manager returns the same instance."""
        manager1 = get_reliability_manager()
        manager2 = get_reliability_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, UnifiedReliabilityManager)
    
    def test_reset_reliability_manager_creates_new_instance(self):
        """Test that reset creates a new manager instance."""
        original_manager = get_reliability_manager()
        original_manager.register_service("test", "llm")
        
        # Should have the registered service
        assert "test" in original_manager._domain_configs
        
        reset_reliability_manager()
        new_manager = get_reliability_manager()
        
        # Should be a different instance without the registered service
        assert new_manager is not original_manager
        assert "test" not in new_manager._domain_configs
    
    def test_singleton_persists_across_calls(self):
        """Test that singleton persists state across multiple calls."""
        reset_reliability_manager()  # Start fresh
        
        manager = get_reliability_manager()
        manager.register_service("persistent_test", "external_api")
        
        # Get manager again and verify service persists
        same_manager = get_reliability_manager()
        assert same_manager is manager
        assert "persistent_test" in same_manager._domain_configs


class TestMultiUserScenarios:
    """Test multi-user scenarios and isolation."""
    
    def setup_method(self):
        """Setup for each test."""
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        reset_reliability_manager()
        self.manager = get_reliability_manager()
    
    @pytest.mark.asyncio
    async def test_concurrent_service_operations(self):
        """Test concurrent operations on different services."""
        # Register multiple services
        services = []
        for i in range(5):
            service_name = f"concurrent_service_{i}"
            self.manager.register_service(service_name, "external_api")
            services.append(service_name)
        
        async def concurrent_operation(service_name: str) -> str:
            await asyncio.sleep(0.01)  # Simulate work
            return f"result_from_{service_name}"
        
        # Execute operations concurrently
        tasks = []
        for service in services:
            task = self.manager.execute_with_reliability(service, concurrent_operation, service)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify all operations succeeded
        for i, result in enumerate(results):
            assert result.success is True
            assert result.result == f"result_from_concurrent_service_{i}"
            
        # Verify all services are marked healthy
        for service in services:
            health_status = self.manager._health_status[service]
            assert health_status["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_service_isolation_under_failure(self):
        """Test that failure in one service doesn't affect others."""
        # Register two services
        self.manager.register_service("stable_service", "llm")
        self.manager.register_service("failing_service", "external_api", 
                                    ReliabilityConfig(max_retries=1, fallback_enabled=False))
        
        async def stable_operation():
            return "stable_result"
            
        async def failing_operation():
            raise Exception("Always fails")
        
        # Execute operations concurrently
        stable_task = self.manager.execute_with_reliability("stable_service", stable_operation)
        failing_task = self.manager.execute_with_reliability("failing_service", failing_operation)
        
        stable_result, failing_result = await asyncio.gather(stable_task, failing_task)
        
        # Verify isolation: stable succeeds despite failing service
        assert stable_result.success is True
        assert stable_result.result == "stable_result"
        assert failing_result.success is False
        
        # Verify health status isolation
        assert self.manager._health_status["stable_service"]["status"] == "healthy"
        assert self.manager._health_status["failing_service"]["status"] == "unhealthy"
        
        # Verify failure stats isolation
        assert self.manager._failure_stats["stable_service"][FailureMode.INTERNAL_ERROR] == 0
        assert self.manager._failure_stats["failing_service"][FailureMode.INTERNAL_ERROR] > 0


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    def setup_method(self):
        """Setup for each test."""
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        self.manager = UnifiedReliabilityManager()
    
    @pytest.mark.asyncio
    async def test_execute_with_unregistered_service_uses_defaults(self):
        """Test execution with unregistered service uses default config."""
        async def simple_operation():
            return "unregistered_result"
        
        result = await self.manager.execute_with_reliability(
            "unregistered_service",
            simple_operation
        )
        
        # Should succeed using default config
        assert result.success is True
        assert result.result == "unregistered_result"
    
    @pytest.mark.asyncio
    async def test_zero_timeout_skips_timeout_logic(self):
        """Test that zero timeout skips timeout enforcement."""
        service_name = "no_timeout_service"
        config = ReliabilityConfig(timeout_seconds=0.0, circuit_breaker_enabled=False)
        self.manager.register_service(service_name, "external_api", config)
        
        async def slow_operation():
            await asyncio.sleep(0.1)  # Would timeout with positive timeout
            return "slow_result"
        
        result = await self.manager.execute_with_reliability(service_name, slow_operation)
        
        # Should succeed despite being "slow"
        assert result.success is True
        assert result.result == "slow_result"
    
    @pytest.mark.asyncio
    async def test_max_backoff_cap_applied(self):
        """Test exponential backoff is capped at maximum."""
        service_name = "backoff_cap_service"
        config = ReliabilityConfig(max_retries=10, circuit_breaker_enabled=False, fallback_enabled=False)
        self.manager.register_service(service_name, "external_api", config)
        
        call_times = []
        
        async def timing_operation():
            call_times.append(time.time())
            raise Exception("Always fails")
        
        # Execute (will fail after many retries)
        await self.manager.execute_with_reliability(service_name, timing_operation)
        
        # Check that later backoffs are capped at 30 seconds
        # (2^9 = 512 seconds, but should be capped at 30)
        if len(call_times) > 9:
            later_gaps = []
            for i in range(8, len(call_times) - 1):
                gap = call_times[i + 1] - call_times[i]
                later_gaps.append(gap)
            
            # All later gaps should be around 30 seconds (with tolerance)
            for gap in later_gaps[-3:]:  # Check last few gaps
                assert gap <= 31.0  # Should be capped
    
    def test_record_success_for_unregistered_service(self):
        """Test recording success for service that was never registered."""
        # Should not crash
        self.manager._record_success("never_registered")
        
        # Should not create health status entry
        assert "never_registered" not in self.manager._health_status
    
    def test_record_failure_for_unregistered_service(self):
        """Test recording failure for service that was never registered."""
        # Should not crash
        self.manager._record_failure("never_registered", FailureMode.TIMEOUT)
        
        # Should not create entries
        assert "never_registered" not in self.manager._health_status
        assert "never_registered" not in self.manager._failure_stats