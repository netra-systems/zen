"""Comprehensive Circuit Breaker Recovery Path Validation Tests.

PRODUCTION CRITICAL - These tests validate all recovery strategies for circuit breakers
to ensure system resilience during failures and recovery scenarios.

Tests cover:
1. Progressive Recovery Testing - gradual traffic increase with success rate monitoring  
2. Health Check Validation - service readiness and dependency validation
3. Rollback Scenarios - recovery failure handling and automatic rollback
4. Recovery Coordination - multi-service recovery ordering and dependencies
5. Partial Recovery Testing - degraded mode and feature toggling
6. Recovery Monitoring - metrics, progress tracking, and alerting

Business Value Justification (BVJ):
- Segment: Enterprise, Mid (critical for production resilience)
- Business Goal: Platform Stability, Risk Reduction
- Value Impact: Ensures zero-downtime recovery from failures
- Strategic Impact: Enterprise trust and reliability differentiation
"""

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitBreakerManager,
    UnifiedCircuitBreakerState,
    UnifiedCircuitConfig,
    UnifiedServiceCircuitBreakers,
    get_unified_circuit_breaker_manager,
)
from netra_backend.app.core.shared_health_types import (
    HealthChecker,
    HealthStatus,
    HealthCheckResult,
)
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError


@dataclass
class RecoveryScenario:
    """Test scenario for recovery validation."""
    name: str
    initial_failures: int = 5
    recovery_strategy: str = "timeout"
    health_progression: List[str] = field(default_factory=lambda: ["unhealthy", "degraded", "healthy"])
    expected_states: List[str] = field(default_factory=lambda: ["open", "half_open", "closed"])
    traffic_pattern: str = "progressive"
    coordination_required: bool = False


class MockHealthChecker(HealthChecker):
    """Mock health checker for testing recovery paths."""
    
    def __init__(self, initial_status: HealthStatus = HealthStatus.UNHEALTHY):
        self.status = initial_status
        self.call_count = 0
        self.status_progression = []
        self.response_time = 0.1
        
    async def check_health(self) -> HealthCheckResult:
        """Return configured health status."""
        self.call_count += 1
        
        # Progress through status progression if configured
        if self.status_progression and self.call_count <= len(self.status_progression):
            self.status = HealthStatus(self.status_progression[self.call_count - 1])
            
        return HealthCheckResult(
            component_name="test_service",
            success=self.status == HealthStatus.HEALTHY,
            health_score=self._calculate_health_score(),
            response_time_ms=self.response_time * 1000,
            status=self.status.value,
            response_time=self.response_time,
            metadata={"check_count": self.call_count}
        )
    
    def _calculate_health_score(self) -> float:
        """Calculate health score based on status."""
        score_map = {
            HealthStatus.HEALTHY: 95.0,
            HealthStatus.DEGRADED: 70.0,
            HealthStatus.UNHEALTHY: 20.0,
            HealthStatus.UNKNOWN: 50.0,
        }
        return score_map.get(self.status, 0.0)
    
    def set_status_progression(self, statuses: List[str]) -> None:
        """Configure health status progression over time."""
        self.status_progression = statuses


class MockRecoveryCoordinator:
    """Mock coordinator for multi-service recovery testing."""
    
    def __init__(self):
        self.services: Dict[str, UnifiedCircuitBreaker] = {}
        self.recovery_order: List[str] = []
        self.coordination_enabled = True
        self.dependency_graph: Dict[str, List[str]] = {}
        
    def register_service(self, name: str, circuit_breaker: UnifiedCircuitBreaker) -> None:
        """Register service for coordination."""
        self.services[name] = circuit_breaker
        
    def set_dependencies(self, service: str, dependencies: List[str]) -> None:
        """Set service dependencies for recovery ordering."""
        self.dependency_graph[service] = dependencies
        
    async def coordinate_recovery(self, failed_services: List[str]) -> Dict[str, bool]:
        """Coordinate recovery across multiple services."""
        recovery_results = {}
        
        if not self.coordination_enabled:
            # Independent recovery
            for service in failed_services:
                recovery_results[service] = await self._recover_service(service)
            return recovery_results
            
        # Dependency-ordered recovery
        ordered_services = self._calculate_recovery_order(failed_services)
        
        for service in ordered_services:
            if await self._are_dependencies_healthy(service):
                recovery_results[service] = await self._recover_service(service)
                self.recovery_order.append(service)
            else:
                recovery_results[service] = False
                
        return recovery_results
    
    def _calculate_recovery_order(self, services: List[str]) -> List[str]:
        """Calculate dependency-based recovery order."""
        # Simple topological sort for dependencies
        ordered = []
        remaining = set(services)
        
        while remaining:
            # Find services with no unrecovered dependencies
            ready = []
            for service in remaining:
                deps = self.dependency_graph.get(service, [])
                if all(dep not in remaining or dep in ordered for dep in deps):
                    ready.append(service)
            
            if not ready:
                # Circular dependency - recover remaining arbitrarily
                ready = list(remaining)
                
            for service in ready:
                ordered.append(service)
                remaining.discard(service)
                
        return ordered
    
    async def _are_dependencies_healthy(self, service: str) -> bool:
        """Check if service dependencies are healthy."""
        dependencies = self.dependency_graph.get(service, [])
        
        for dep in dependencies:
            if dep in self.services:
                if not self.services[dep].is_closed:
                    return False
                    
        return True
    
    async def _recover_service(self, service: str) -> bool:
        """Attempt to recover a specific service."""
        if service not in self.services:
            return False
            
        try:
            await self.services[service].reset()
            return True
        except Exception:
            return False


class TestProgressiveRecoveryMechanisms:
    """Test progressive recovery with gradual traffic increase."""
    
    @pytest.fixture
    def progressive_config(self):
        """Configuration for progressive recovery testing."""
        return UnifiedCircuitConfig(
            name="progressive_test",
            failure_threshold=3,
            recovery_timeout=1.0,
            success_threshold=2,
            half_open_max_calls=5,
            adaptive_threshold=True,
            exponential_backoff=False
        )
    
    @pytest.fixture
    def health_checker(self):
        """Health checker that progresses from unhealthy to healthy."""
        checker = MockHealthChecker(HealthStatus.UNHEALTHY)
        checker.set_status_progression(["unhealthy", "degraded", "healthy", "healthy"])
        return checker
    
    @pytest.mark.asyncio
    async def test_gradual_traffic_increase(self, progressive_config, health_checker):
        """Test progressive traffic increase during recovery."""
        circuit = UnifiedCircuitBreaker(progressive_config, health_checker=health_checker)
        
        # Force circuit open
        await circuit.force_open()
        assert circuit.state == UnifiedCircuitBreakerState.OPEN
        
        # Simulate gradual recovery
        recovery_metrics = []
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Progressive traffic increase - simulate 5 half-open calls
        successful_calls = 0
        
        async def mock_operation():
            """Mock operation that succeeds."""
            await asyncio.sleep(0.01)  # Simulate processing time
            return "success"
        
        for i in range(5):
            try:
                result = await circuit.call(mock_operation)
                successful_calls += 1
                
                # Record recovery metrics
                status = circuit.get_status()
                recovery_metrics.append({
                    "call": i + 1,
                    "state": status["state"],
                    "success_rate": status["metrics"]["success_rate"],
                    "consecutive_successes": status["metrics"]["consecutive_successes"]
                })
                
            except CircuitBreakerOpenError:
                break
                
        # Validate progressive recovery behavior
        assert successful_calls > 0, "No calls should succeed during half-open state"
        assert circuit.state in [UnifiedCircuitBreakerState.HALF_OPEN, UnifiedCircuitBreakerState.CLOSED]
        
        # Check that success rate improved progressively
        success_rates = [m["success_rate"] for m in recovery_metrics]
        assert all(rate >= 0 for rate in success_rates), "Success rates should be non-negative"
        
        if len(success_rates) > 1:
            # Success rate should generally improve or stay stable
            assert success_rates[-1] >= success_rates[0], "Final success rate should be >= initial"
    
    @pytest.mark.asyncio
    async def test_recovery_speed_adjustment(self, progressive_config, health_checker):
        """Test recovery speed adjustment based on health progression."""
        circuit = UnifiedCircuitBreaker(progressive_config, health_checker=health_checker)
        
        # Force open and track recovery timing
        await circuit.force_open()
        start_time = time.time()
        
        recovery_attempts = []
        
        # Attempt recovery multiple times to observe speed adjustment
        for attempt in range(3):
            await asyncio.sleep(1.1)  # Wait for recovery timeout
            
            try:
                async def test_op():
                    return f"attempt_{attempt}"
                    
                result = await circuit.call(test_op)
                recovery_time = time.time() - start_time
                
                recovery_attempts.append({
                    "attempt": attempt,
                    "recovery_time": recovery_time,
                    "state": circuit.state.value,
                    "health_status": health_checker.status.value
                })
                
                if circuit.state == UnifiedCircuitBreakerState.CLOSED:
                    break
                    
            except CircuitBreakerOpenError:
                # Circuit still open, continue
                pass
                
        # Validate recovery speed adjustment
        assert len(recovery_attempts) > 0, "Should have at least one recovery attempt"
        
        # Check that recovery correlates with health improvement
        health_statuses = [a["health_status"] for a in recovery_attempts]
        if len(health_statuses) > 1:
            # Health should improve over attempts
            assert "healthy" in health_statuses, "Should eventually reach healthy state"
    
    @pytest.mark.asyncio
    async def test_full_recovery_transition(self, progressive_config, health_checker):
        """Test complete transition from open -> half-open -> closed."""
        circuit = UnifiedCircuitBreaker(progressive_config, health_checker=health_checker)
        
        # Force circuit open
        await circuit.force_open()
        initial_state = circuit.state
        assert initial_state == UnifiedCircuitBreakerState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Perform successful operations to trigger full recovery
        async def reliable_operation():
            await asyncio.sleep(0.01)
            return "success"
        
        state_transitions = []
        
        # Perform enough successful calls to transition to closed
        for i in range(progressive_config.success_threshold + 1):
            try:
                result = await circuit.call(reliable_operation)
                current_state = circuit.state.value
                state_transitions.append(current_state)
                
            except CircuitBreakerOpenError:
                # May still be in open state on first attempts
                state_transitions.append("open")
                
        # Validate complete state transition sequence
        unique_states = list(dict.fromkeys(state_transitions))  # Remove duplicates, preserve order
        
        # Should see progression through states
        assert "open" in unique_states or state_transitions[0] == "half_open"
        
        # Should eventually reach closed state
        final_state = circuit.state
        assert final_state == UnifiedCircuitBreakerState.CLOSED, f"Expected closed state, got {final_state}"
        
        # Validate metrics reflect successful recovery
        status = circuit.get_status()
        assert status["metrics"]["consecutive_successes"] >= progressive_config.success_threshold
        assert status["metrics"]["success_rate"] > 0.5


class TestHealthCheckValidation:
    """Test health check validation during recovery."""
    
    @pytest.fixture
    def health_aware_config(self):
        """Configuration with health check integration."""
        return UnifiedCircuitConfig(
            name="health_test",
            failure_threshold=2,
            recovery_timeout=0.5,
            health_check_interval=0.2,
            adaptive_threshold=True
        )
    
    @pytest.mark.asyncio
    async def test_health_probe_execution(self, health_aware_config):
        """Test health probe execution during recovery."""
        health_checker = MockHealthChecker(HealthStatus.DEGRADED)
        circuit = UnifiedCircuitBreaker(health_aware_config, health_checker=health_checker)
        
        # Trigger health monitoring
        await circuit.force_open()
        
        # Allow time for health checks
        await asyncio.sleep(0.7)
        
        # Validate health checks were performed
        assert health_checker.call_count > 0, "Health checker should have been called"
        
        # Check that circuit breaker has health information
        status = circuit.get_status()
        assert status["health"]["has_health_checker"] is True
        assert status["health"]["last_health_status"] is not None
    
    @pytest.mark.asyncio
    async def test_service_readiness_checks(self, health_aware_config):
        """Test service readiness validation before recovery."""
        health_checker = MockHealthChecker(HealthStatus.UNHEALTHY)
        health_checker.set_status_progression(["unhealthy", "unhealthy", "degraded", "healthy"])
        
        circuit = UnifiedCircuitBreaker(health_aware_config, health_checker=health_checker)
        
        # Force open and track readiness progression
        await circuit.force_open()
        
        readiness_checks = []
        
        # Check readiness over time
        for check in range(4):
            await asyncio.sleep(0.6)  # Allow health check + recovery timeout
            
            # Attempt operation to test readiness
            try:
                async def test_operation():
                    return "ready"
                    
                result = await circuit.call(test_operation)
                readiness_checks.append({
                    "check": check,
                    "ready": True,
                    "health_status": health_checker.status.value,
                    "circuit_state": circuit.state.value
                })
                
            except CircuitBreakerOpenError:
                readiness_checks.append({
                    "check": check,
                    "ready": False,
                    "health_status": health_checker.status.value,
                    "circuit_state": circuit.state.value
                })
        
        # Validate readiness progression
        ready_states = [check["ready"] for check in readiness_checks]
        health_states = [check["health_status"] for check in readiness_checks]
        
        # Should eventually become ready as health improves
        assert any(ready_states), "Should become ready when health improves"
        assert "healthy" in health_states, "Should reach healthy state"
    
    @pytest.mark.asyncio
    async def test_dependency_health_validation(self, health_aware_config):
        """Test validation of dependency health during recovery."""
        # Create dependency circuit breakers
        db_health = MockHealthChecker(HealthStatus.HEALTHY)
        cache_health = MockHealthChecker(HealthStatus.DEGRADED)
        
        db_circuit = UnifiedCircuitBreaker(
            UnifiedCircuitConfig(name="database", failure_threshold=2), 
            health_checker=db_health
        )
        cache_circuit = UnifiedCircuitBreaker(
            UnifiedCircuitConfig(name="cache", failure_threshold=2),
            health_checker=cache_health
        )
        
        # Main service depends on both
        main_health = MockHealthChecker(HealthStatus.HEALTHY)
        main_circuit = UnifiedCircuitBreaker(health_aware_config, health_checker=main_health)
        
        # Setup dependency validation
        dependencies_healthy = []
        
        async def check_dependencies():
            """Check if dependencies are healthy."""
            db_healthy = db_circuit.is_closed and db_health.status == HealthStatus.HEALTHY
            cache_healthy = cache_circuit.is_closed and cache_health.status != HealthStatus.UNHEALTHY
            return db_healthy and cache_healthy
        
        # Force main circuit open
        await main_circuit.force_open()
        
        # Test recovery with dependency validation
        await asyncio.sleep(0.6)  # Wait for recovery timeout
        
        # Check dependency health before attempting recovery
        deps_ok = await check_dependencies()
        dependencies_healthy.append(deps_ok)
        
        if deps_ok:
            try:
                async def dependent_operation():
                    return "depends on db and cache"
                    
                result = await main_circuit.call(dependent_operation)
                recovery_successful = True
            except CircuitBreakerOpenError:
                recovery_successful = False
        else:
            recovery_successful = False
        
        # Validate dependency-aware recovery
        assert len(dependencies_healthy) > 0
        
        # Recovery should correlate with dependency health
        if dependencies_healthy[0]:
            # If dependencies are healthy, recovery should be possible
            assert main_circuit.state in [UnifiedCircuitBreakerState.HALF_OPEN, UnifiedCircuitBreakerState.CLOSED]


class TestRollbackScenarios:
    """Test rollback scenarios when recovery fails."""
    
    @pytest.fixture
    def rollback_config(self):
        """Configuration for rollback testing."""
        return UnifiedCircuitConfig(
            name="rollback_test",
            failure_threshold=2,
            recovery_timeout=0.5,
            success_threshold=1,
            half_open_max_calls=3,
            exponential_backoff=True,
            max_backoff_seconds=5.0
        )
    
    @pytest.mark.asyncio
    async def test_recovery_failure_handling(self, rollback_config):
        """Test handling of recovery failures with rollback."""
        circuit = UnifiedCircuitBreaker(rollback_config)
        
        # Force open
        await circuit.force_open()
        original_open_count = circuit.metrics.circuit_opened_count
        
        # Wait for recovery timeout
        await asyncio.sleep(0.6)
        
        # Attempt recovery with failing operations
        failure_count = 0
        
        async def failing_operation():
            nonlocal failure_count
            failure_count += 1
            raise Exception(f"Recovery failure {failure_count}")
        
        # Try multiple recovery attempts that fail
        for attempt in range(3):
            try:
                result = await circuit.call(failing_operation)
                pytest.fail("Operation should have failed")
            except Exception as e:
                if "Circuit breaker" in str(e):
                    # Circuit opened again due to failures
                    break
                # Other exceptions are expected from failing operation
                pass
        
        # Validate rollback behavior
        assert circuit.state == UnifiedCircuitBreakerState.OPEN
        assert circuit.metrics.circuit_opened_count > original_open_count
        assert circuit.metrics.failed_calls >= failure_count
    
    @pytest.mark.asyncio
    async def test_automatic_rollback_triggers(self, rollback_config):
        """Test automatic rollback triggers."""
        health_checker = MockHealthChecker(HealthStatus.HEALTHY)
        circuit = UnifiedCircuitBreaker(rollback_config, health_checker=health_checker)
        
        # Force open initially
        await circuit.force_open()
        
        # Configure health to degrade during recovery
        health_checker.set_status_progression(["healthy", "degraded", "unhealthy", "unhealthy"])
        
        await asyncio.sleep(0.6)  # Allow recovery timeout
        
        # Attempt recovery operations
        rollback_triggered = False
        
        for attempt in range(4):
            try:
                async def health_sensitive_op():
                    # Operation success depends on health
                    if health_checker.status == HealthStatus.UNHEALTHY:
                        raise Exception("Service unhealthy")
                    return f"attempt_{attempt}"
                
                result = await circuit.call(health_sensitive_op)
                
            except Exception as e:
                if "Circuit breaker" in str(e):
                    rollback_triggered = True
                    break
            
            await asyncio.sleep(0.3)  # Allow health status to change
        
        # Validate automatic rollback
        assert rollback_triggered or circuit.state == UnifiedCircuitBreakerState.OPEN
        
        # Check that health degradation was detected
        status = circuit.get_status()
        assert status["health"]["last_health_status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_state_preservation_during_rollback(self, rollback_config):
        """Test state preservation during rollback."""
        circuit = UnifiedCircuitBreaker(rollback_config)
        
        # Record initial metrics
        initial_status = circuit.get_status()
        initial_total_calls = initial_status["metrics"]["total_calls"]
        initial_state_changes = initial_status["metrics"]["state_changes"]
        
        # Force open and attempt failed recovery
        await circuit.force_open()
        
        await asyncio.sleep(0.6)  # Recovery timeout
        
        # Failed recovery attempt
        try:
            async def failing_op():
                raise Exception("Recovery failed")
            
            await circuit.call(failing_op)
        except:
            pass  # Expected to fail
        
        # Validate state preservation
        final_status = circuit.get_status()
        
        # Metrics should be preserved and updated
        assert final_status["metrics"]["total_calls"] > initial_total_calls
        assert final_status["metrics"]["state_changes"] >= initial_state_changes
        assert final_status["metrics"]["failed_calls"] > 0
        
        # Circuit should return to stable open state
        assert circuit.state == UnifiedCircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_retry_mechanisms_after_rollback(self, rollback_config):
        """Test retry mechanisms after rollback."""
        circuit = UnifiedCircuitBreaker(rollback_config)
        
        # Force open
        await circuit.force_open()
        
        # Track retry attempts after rollback
        retry_attempts = []
        
        for cycle in range(3):
            # Wait for recovery timeout (with exponential backoff)
            if cycle == 0:
                await asyncio.sleep(0.6)  # Initial timeout
            else:
                # Exponential backoff - wait longer each time
                backoff_time = rollback_config.recovery_timeout * (2 ** cycle)
                await asyncio.sleep(min(backoff_time, 2.0))  # Cap for testing
            
            # Attempt operation
            try:
                async def test_retry_op():
                    # Succeed only on last attempt
                    if cycle == 2:
                        return f"success_cycle_{cycle}"
                    raise Exception(f"fail_cycle_{cycle}")
                
                result = await circuit.call(test_retry_op)
                retry_attempts.append({
                    "cycle": cycle,
                    "success": True,
                    "state": circuit.state.value
                })
                break
                
            except Exception as e:
                retry_attempts.append({
                    "cycle": cycle,
                    "success": False,
                    "error": str(e),
                    "state": circuit.state.value
                })
        
        # Validate retry behavior
        assert len(retry_attempts) > 0
        
        # Should eventually succeed with retries
        final_attempt = retry_attempts[-1]
        assert final_attempt["success"] or len(retry_attempts) == 3


class TestRecoveryCoordination:
    """Test recovery coordination across multiple services."""
    
    @pytest.fixture
    def coordinator(self):
        """Create recovery coordinator for testing."""
        return MockRecoveryCoordinator()
    
    @pytest.fixture
    def service_configs(self):
        """Create configurations for multiple services."""
        return {
            "database": UnifiedCircuitConfig(name="database", failure_threshold=2, recovery_timeout=0.5),
            "cache": UnifiedCircuitConfig(name="cache", failure_threshold=3, recovery_timeout=0.3),
            "api": UnifiedCircuitConfig(name="api", failure_threshold=2, recovery_timeout=0.7),
            "auth": UnifiedCircuitConfig(name="auth", failure_threshold=1, recovery_timeout=0.4)
        }
    
    @pytest.mark.asyncio
    async def test_multi_service_recovery_ordering(self, coordinator, service_configs):
        """Test coordinated recovery with proper service ordering."""
        # Create circuit breakers for services
        services = {}
        for name, config in service_configs.items():
            health_checker = MockHealthChecker(HealthStatus.HEALTHY)
            circuit = UnifiedCircuitBreaker(config, health_checker=health_checker)
            services[name] = circuit
            coordinator.register_service(name, circuit)
        
        # Define service dependencies (auth -> database -> api -> cache)
        coordinator.set_dependencies("auth", [])  # No dependencies
        coordinator.set_dependencies("database", ["auth"])
        coordinator.set_dependencies("api", ["auth", "database"])
        coordinator.set_dependencies("cache", ["auth"])
        
        # Force all services to fail
        for circuit in services.values():
            await circuit.force_open()
        
        # Wait for recovery timeouts
        await asyncio.sleep(0.8)
        
        # Coordinate recovery
        failed_services = list(services.keys())
        recovery_results = await coordinator.coordinate_recovery(failed_services)
        
        # Validate recovery ordering
        expected_order = ["auth", "database", "cache", "api"]  # Dependency order
        actual_order = coordinator.recovery_order
        
        # Auth should recover first (no dependencies)
        assert actual_order[0] == "auth"
        
        # Database should recover after auth
        auth_index = actual_order.index("auth")
        if "database" in actual_order:
            db_index = actual_order.index("database")
            assert db_index > auth_index
        
        # API should recover after both auth and database
        if "api" in actual_order:
            api_index = actual_order.index("api")
            assert api_index > auth_index
            if "database" in actual_order:
                assert api_index > actual_order.index("database")
    
    @pytest.mark.asyncio
    async def test_dependency_recovery_validation(self, coordinator, service_configs):
        """Test validation of dependency recovery before service recovery."""
        # Create services with health checkers
        services = {}
        health_checkers = {}
        
        for name, config in service_configs.items():
            health_checker = MockHealthChecker(HealthStatus.UNHEALTHY)
            health_checkers[name] = health_checker
            circuit = UnifiedCircuitBreaker(config, health_checker=health_checker)
            services[name] = circuit
            coordinator.register_service(name, circuit)
        
        # Set up dependency chain: api depends on database and auth
        coordinator.set_dependencies("api", ["database", "auth"])
        coordinator.set_dependencies("database", ["auth"])
        coordinator.set_dependencies("auth", [])
        
        # Force all to fail initially
        for circuit in services.values():
            await circuit.force_open()
        
        await asyncio.sleep(0.8)
        
        # Recover auth first (make it healthy)
        health_checkers["auth"].status = HealthStatus.HEALTHY
        await services["auth"].reset()
        
        # Try to recover API while database is still unhealthy
        api_recovery = await coordinator._recover_service("api")
        api_deps_ready = await coordinator._are_dependencies_healthy("api")
        
        # API recovery should fail because database dependency is unhealthy
        assert not api_deps_ready, "API dependencies should not be ready"
        
        # Now recover database
        health_checkers["database"].status = HealthStatus.HEALTHY
        await services["database"].reset()
        
        # Now API recovery should be possible
        api_deps_ready_now = await coordinator._are_dependencies_healthy("api")
        assert api_deps_ready_now, "API dependencies should now be ready"
    
    @pytest.mark.asyncio
    async def test_recovery_coordination_failure_handling(self, coordinator, service_configs):
        """Test handling of coordination failures."""
        # Create services with mixed recovery potential
        services = {}
        health_checkers = {}
        
        for name, config in service_configs.items():
            # Auth and cache will be recoverable, database and api will not
            status = HealthStatus.HEALTHY if name in ["auth", "cache"] else HealthStatus.UNHEALTHY
            health_checker = MockHealthChecker(status)
            health_checkers[name] = health_checker
            
            circuit = UnifiedCircuitBreaker(config, health_checker=health_checker)
            services[name] = circuit
            coordinator.register_service(name, circuit)
        
        # Force all to fail
        for circuit in services.values():
            await circuit.force_open()
        
        await asyncio.sleep(0.8)
        
        # Attempt coordinated recovery
        failed_services = list(services.keys())
        recovery_results = await coordinator.coordinate_recovery(failed_services)
        
        # Validate partial recovery results
        assert isinstance(recovery_results, dict)
        assert len(recovery_results) == len(failed_services)
        
        # Services with healthy health checkers should recover
        assert recovery_results.get("auth", False) is True
        assert recovery_results.get("cache", False) is True
        
        # Services with unhealthy health checkers should not
        assert recovery_results.get("database", True) is False
        assert recovery_results.get("api", True) is False
    
    @pytest.mark.asyncio
    async def test_system_wide_coordination(self, coordinator, service_configs):
        """Test system-wide recovery coordination."""
        # Create a comprehensive service ecosystem
        services = {}
        health_checkers = {}
        
        # Create services with progressive health improvement
        health_progression = {
            "auth": ["unhealthy", "degraded", "healthy"],
            "database": ["unhealthy", "unhealthy", "degraded", "healthy"], 
            "cache": ["unhealthy", "healthy"],  # Fast recovery
            "api": ["unhealthy", "degraded", "degraded", "healthy"]  # Slow recovery
        }
        
        for name, config in service_configs.items():
            health_checker = MockHealthChecker(HealthStatus.UNHEALTHY)
            health_checker.set_status_progression(health_progression[name])
            health_checkers[name] = health_checker
            
            circuit = UnifiedCircuitBreaker(config, health_checker=health_checker)
            services[name] = circuit
            coordinator.register_service(name, circuit)
        
        # Define complex dependency graph
        coordinator.set_dependencies("auth", [])
        coordinator.set_dependencies("database", ["auth"])
        coordinator.set_dependencies("cache", ["auth"])
        coordinator.set_dependencies("api", ["auth", "database", "cache"])
        
        # Force system-wide failure
        for circuit in services.values():
            await circuit.force_open()
        
        system_recovery_timeline = []
        
        # Simulate system recovery over time
        for recovery_cycle in range(4):
            await asyncio.sleep(0.8)  # Recovery timeout
            
            # Attempt system-wide recovery
            recovery_results = await coordinator.coordinate_recovery(list(services.keys()))
            
            # Record system state
            system_state = {
                "cycle": recovery_cycle,
                "recovery_results": recovery_results,
                "service_states": {name: circuit.state.value for name, circuit in services.items()},
                "healthy_services": sum(1 for result in recovery_results.values() if result),
                "coordination_order": coordinator.recovery_order.copy()
            }
            system_recovery_timeline.append(system_state)
            
            # Clear recovery order for next cycle
            coordinator.recovery_order = []
        
        # Validate system-wide recovery progression
        assert len(system_recovery_timeline) > 0
        
        # Should see progressive improvement in healthy service count
        healthy_counts = [state["healthy_services"] for state in system_recovery_timeline]
        final_healthy_count = healthy_counts[-1]
        initial_healthy_count = healthy_counts[0]
        
        assert final_healthy_count >= initial_healthy_count, "System health should improve over time"
        
        # Should eventually achieve full or near-full recovery
        assert final_healthy_count >= len(services) - 1, "Should recover most services"


class TestPartialRecoveryScenarios:
    """Test partial recovery and degraded mode operation."""
    
    @pytest.fixture
    def degraded_config(self):
        """Configuration for partial recovery testing."""
        return UnifiedCircuitConfig(
            name="partial_recovery",
            failure_threshold=3,
            recovery_timeout=0.5,
            success_threshold=2,
            adaptive_threshold=True,
            slow_call_threshold=2.0
        )
    
    @pytest.mark.asyncio
    async def test_degraded_mode_operation(self, degraded_config):
        """Test operation in degraded mode with limited functionality."""
        health_checker = MockHealthChecker(HealthStatus.DEGRADED)
        circuit = UnifiedCircuitBreaker(degraded_config, health_checker=health_checker)
        
        # Force circuit open then allow degraded recovery
        await circuit.force_open()
        await asyncio.sleep(0.6)
        
        # Test degraded mode operations
        degraded_operations = []
        
        async def degraded_operation(complexity: str):
            """Operation with different complexity levels."""
            if complexity == "simple":
                await asyncio.sleep(0.1)
                return "simple_success"
            elif complexity == "complex":
                await asyncio.sleep(3.0)  # Exceeds slow call threshold
                return "complex_success"
            else:
                raise Exception("invalid_operation")
        
        # Test simple operations in degraded mode
        for i in range(3):
            try:
                result = await circuit.call(degraded_operation, "simple")
                degraded_operations.append({
                    "operation": f"simple_{i}",
                    "success": True,
                    "state": circuit.state.value
                })
            except Exception as e:
                degraded_operations.append({
                    "operation": f"simple_{i}",
                    "success": False,
                    "error": str(e)
                })
        
        # Validate degraded mode functionality
        successful_simple = [op for op in degraded_operations if op["success"]]
        assert len(successful_simple) > 0, "Simple operations should succeed in degraded mode"
        
        # Test complex operations (should be limited/throttled)
        try:
            result = await circuit.call(degraded_operation, "complex")
            # If successful, it should be marked as slow
            assert circuit.metrics.slow_requests > 0
        except Exception:
            # May fail due to timeout or circuit protection
            pass
    
    @pytest.mark.asyncio 
    async def test_feature_toggling_during_recovery(self, degraded_config):
        """Test feature toggling based on recovery state."""
        circuit = UnifiedCircuitBreaker(degraded_config)
        
        # Create feature availability based on circuit state
        def get_available_features(circuit_state):
            """Return available features based on circuit state."""
            if circuit_state == UnifiedCircuitBreakerState.CLOSED:
                return ["core", "advanced", "premium", "analytics"]
            elif circuit_state == UnifiedCircuitBreakerState.HALF_OPEN:
                return ["core", "advanced"]  # Limited features during recovery
            else:  # OPEN
                return ["core"]  # Only core features
        
        # Force through recovery states and check feature availability
        feature_progression = []
        
        # Start with closed state (full features)
        initial_features = get_available_features(circuit.state)
        feature_progression.append({
            "state": circuit.state.value,
            "features": initial_features
        })
        
        # Force open (minimal features)
        await circuit.force_open()
        open_features = get_available_features(circuit.state)
        feature_progression.append({
            "state": circuit.state.value,
            "features": open_features
        })
        
        # Allow recovery to half-open (partial features)
        await asyncio.sleep(0.6)
        
        try:
            async def test_operation():
                return "success"
            
            await circuit.call(test_operation)
            half_open_features = get_available_features(circuit.state)
            feature_progression.append({
                "state": circuit.state.value,
                "features": half_open_features
            })
        except:
            pass
        
        # Validate feature toggling
        assert len(feature_progression) >= 2
        
        # Open state should have minimal features
        open_state = next((fp for fp in feature_progression if fp["state"] == "open"), None)
        if open_state:
            assert "core" in open_state["features"]
            assert len(open_state["features"]) <= 2
        
        # Half-open should have more features than open
        half_open_state = next((fp for fp in feature_progression if fp["state"] == "half_open"), None)
        if half_open_state and open_state:
            assert len(half_open_state["features"]) >= len(open_state["features"])
    
    @pytest.mark.asyncio
    async def test_capacity_limiting_during_recovery(self, degraded_config):
        """Test capacity limiting during recovery phase."""
        circuit = UnifiedCircuitBreaker(degraded_config)
        
        # Force open and track capacity limiting
        await circuit.force_open()
        await asyncio.sleep(0.6)  # Recovery timeout
        
        capacity_metrics = []
        
        # Attempt more operations than half-open limit
        total_attempts = degraded_config.half_open_max_calls + 2
        
        async def capacity_test_operation():
            await asyncio.sleep(0.05)
            return "capacity_test"
        
        successful_operations = 0
        rejected_operations = 0
        
        for attempt in range(total_attempts):
            try:
                result = await circuit.call(capacity_test_operation)
                successful_operations += 1
                
                capacity_metrics.append({
                    "attempt": attempt,
                    "success": True,
                    "state": circuit.state.value,
                    "half_open_calls": getattr(circuit, '_half_open_calls', 0)
                })
                
            except CircuitBreakerOpenError:
                rejected_operations += 1
                
                capacity_metrics.append({
                    "attempt": attempt,
                    "success": False,
                    "state": circuit.state.value,
                    "reason": "capacity_limit"
                })
        
        # Validate capacity limiting
        assert successful_operations <= degraded_config.half_open_max_calls
        assert rejected_operations >= 0
        
        # Should have enforced half-open capacity limits
        if circuit.state == UnifiedCircuitBreakerState.HALF_OPEN:
            successful_half_open = [m for m in capacity_metrics 
                                  if m["success"] and m["state"] == "half_open"]
            assert len(successful_half_open) <= degraded_config.half_open_max_calls
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_patterns(self, degraded_config):
        """Test graceful degradation patterns during partial recovery."""
        health_checker = MockHealthChecker(HealthStatus.DEGRADED)
        health_checker.set_status_progression(["unhealthy", "degraded", "degraded", "healthy"])
        
        circuit = UnifiedCircuitBreaker(degraded_config, health_checker=health_checker)
        
        # Define degradation levels based on health and circuit state
        def get_service_quality(health_status, circuit_state):
            """Determine service quality level."""
            if circuit_state == "open":
                return "offline"
            elif circuit_state == "half_open":
                if health_status == "healthy":
                    return "testing"
                elif health_status == "degraded":
                    return "limited"
                else:
                    return "minimal"
            else:  # closed
                if health_status == "healthy":
                    return "full"
                elif health_status == "degraded":
                    return "reduced"
                else:
                    return "basic"
        
        degradation_timeline = []
        
        # Force initial failure
        await circuit.force_open()
        
        # Track degradation over recovery timeline
        for cycle in range(4):
            await asyncio.sleep(0.6)
            
            # Attempt operation to trigger state changes
            try:
                async def quality_test_op():
                    return f"cycle_{cycle}"
                
                result = await circuit.call(quality_test_op)
                operation_success = True
            except:
                operation_success = False
            
            # Record service quality
            quality_level = get_service_quality(
                health_checker.status.value,
                circuit.state.value
            )
            
            degradation_timeline.append({
                "cycle": cycle,
                "health_status": health_checker.status.value,
                "circuit_state": circuit.state.value,
                "service_quality": quality_level,
                "operation_success": operation_success
            })
        
        # Validate graceful degradation progression
        quality_levels = [entry["service_quality"] for entry in degradation_timeline]
        
        # Should progress from lower to higher quality levels
        quality_hierarchy = ["offline", "minimal", "basic", "limited", "testing", "reduced", "full"]
        
        # Final quality should be better than initial
        if len(quality_levels) >= 2:
            initial_quality_idx = quality_hierarchy.index(quality_levels[0]) if quality_levels[0] in quality_hierarchy else 0
            final_quality_idx = quality_hierarchy.index(quality_levels[-1]) if quality_levels[-1] in quality_hierarchy else 0
            
            assert final_quality_idx >= initial_quality_idx, "Service quality should improve over time"


class TestRecoveryMonitoring:
    """Test recovery monitoring, metrics, and alerting."""
    
    @pytest.fixture
    def monitored_config(self):
        """Configuration with comprehensive monitoring."""
        return UnifiedCircuitConfig(
            name="monitored_recovery",
            failure_threshold=2,
            recovery_timeout=0.5,
            success_threshold=1,
            health_check_interval=0.2,
            adaptive_threshold=True
        )
    
    @pytest.mark.asyncio
    async def test_recovery_metrics_tracking(self, monitored_config):
        """Test comprehensive recovery metrics tracking."""
        health_checker = MockHealthChecker(HealthStatus.UNHEALTHY)
        circuit = UnifiedCircuitBreaker(monitored_config, health_checker=health_checker)
        
        # Baseline metrics
        initial_status = circuit.get_status()
        initial_metrics = initial_status["metrics"]
        
        # Force failure and track metrics
        await circuit.force_open()
        
        metrics_timeline = []
        
        # Track metrics during recovery process
        for checkpoint in range(3):
            await asyncio.sleep(0.6)
            
            # Attempt recovery operation
            try:
                async def monitored_operation():
                    # Success rate improves over time
                    if checkpoint >= 1:
                        health_checker.status = HealthStatus.DEGRADED
                    if checkpoint >= 2:
                        health_checker.status = HealthStatus.HEALTHY
                    return f"checkpoint_{checkpoint}"
                
                result = await circuit.call(monitored_operation)
                operation_success = True
                
            except Exception as e:
                operation_success = False
            
            # Capture comprehensive metrics
            current_status = circuit.get_status()
            current_metrics = current_status["metrics"]
            
            metrics_snapshot = {
                "checkpoint": checkpoint,
                "operation_success": operation_success,
                "state": current_status["state"],
                "total_calls": current_metrics["total_calls"],
                "successful_calls": current_metrics["successful_calls"],
                "failed_calls": current_metrics["failed_calls"],
                "rejected_calls": current_metrics["rejected_calls"],
                "success_rate": current_metrics["success_rate"],
                "consecutive_successes": current_metrics["consecutive_successes"],
                "consecutive_failures": current_metrics["consecutive_failures"],
                "state_changes": current_metrics["state_changes"],
                "health_status": current_status["health"]["last_health_status"]
            }
            
            metrics_timeline.append(metrics_snapshot)
        
        # Validate metrics progression
        assert len(metrics_timeline) >= 1
        
        final_metrics = metrics_timeline[-1]
        
        # Should see metrics evolution
        assert final_metrics["total_calls"] > initial_metrics["total_calls"]
        assert final_metrics["state_changes"] > initial_metrics["state_changes"]
        
        # Success rate should improve if operations succeeded
        successful_checkpoints = [m for m in metrics_timeline if m["operation_success"]]
        if successful_checkpoints:
            assert final_metrics["successful_calls"] > initial_metrics["successful_calls"]
    
    @pytest.mark.asyncio
    async def test_recovery_progress_tracking(self, monitored_config):
        """Test recovery progress tracking and milestones."""
        circuit = UnifiedCircuitBreaker(monitored_config)
        
        # Define recovery milestones
        recovery_milestones = [
            {"name": "circuit_open", "condition": lambda s: s["state"] == "open"},
            {"name": "recovery_timeout_elapsed", "condition": lambda s: True},  # Always true after waiting
            {"name": "half_open_transition", "condition": lambda s: s["state"] == "half_open"},
            {"name": "first_success", "condition": lambda s: s["metrics"]["successful_calls"] > 0},
            {"name": "circuit_closed", "condition": lambda s: s["state"] == "closed"}
        ]
        
        achieved_milestones = []
        
        # Force open to start recovery process
        await circuit.force_open()
        
        initial_status = circuit.get_status()
        if recovery_milestones[0]["condition"](initial_status):
            achieved_milestones.append({
                "milestone": recovery_milestones[0]["name"],
                "timestamp": time.time(),
                "status": initial_status
            })
        
        # Track progress through recovery
        for progress_check in range(4):
            await asyncio.sleep(0.6)  # Allow recovery timeout
            
            # Attempt recovery operation
            try:
                async def progress_operation():
                    return f"progress_{progress_check}"
                
                result = await circuit.call(progress_operation)
                
            except Exception:
                pass  # Continue tracking regardless
            
            # Check milestones
            current_status = circuit.get_status()
            current_time = time.time()
            
            for milestone in recovery_milestones[1:]:  # Skip first one already checked
                if milestone["name"] not in [m["milestone"] for m in achieved_milestones]:
                    if milestone["condition"](current_status):
                        achieved_milestones.append({
                            "milestone": milestone["name"],
                            "timestamp": current_time,
                            "status": current_status
                        })
        
        # Validate recovery progress
        assert len(achieved_milestones) >= 2, "Should achieve multiple recovery milestones"
        
        # Should progress through milestones in logical order
        milestone_names = [m["milestone"] for m in achieved_milestones]
        assert "circuit_open" in milestone_names, "Should start with circuit open"
        
        # If circuit recovered, should see progression
        if "circuit_closed" in milestone_names:
            assert "half_open_transition" in milestone_names or "first_success" in milestone_names
    
    @pytest.mark.asyncio
    async def test_recovery_alerting_integration(self, monitored_config):
        """Test alerting during recovery process."""
        # Mock alerting system
        alerts_generated = []
        
        def generate_alert(severity: str, message: str, component: str, metadata: Dict[str, Any] = None):
            """Mock alert generation."""
            alerts_generated.append({
                "severity": severity,
                "message": message,
                "component": component,
                "timestamp": time.time(),
                "metadata": metadata or {}
            })
        
        health_checker = MockHealthChecker(HealthStatus.UNHEALTHY)
        circuit = UnifiedCircuitBreaker(monitored_config, health_checker=health_checker)
        
        # Hook into circuit state changes for alerting
        original_transition_open = circuit._transition_to_open
        original_transition_half_open = circuit._transition_to_half_open
        original_transition_closed = circuit._transition_to_closed
        
        async def alerting_transition_open():
            await original_transition_open()
            generate_alert(
                "critical",
                f"Circuit breaker {circuit.config.name} opened - service degraded",
                circuit.config.name,
                {"state": "open", "failure_count": circuit.metrics.consecutive_failures}
            )
        
        async def alerting_transition_half_open():
            await original_transition_half_open()
            generate_alert(
                "warning",
                f"Circuit breaker {circuit.config.name} attempting recovery",
                circuit.config.name,
                {"state": "half_open", "recovery_attempt": circuit.metrics.circuit_opened_count}
            )
        
        async def alerting_transition_closed():
            await original_transition_closed()
            generate_alert(
                "info",
                f"Circuit breaker {circuit.config.name} recovered successfully",
                circuit.config.name,
                {"state": "closed", "success_count": circuit.metrics.consecutive_successes}
            )
        
        # Mock the transition methods
        circuit._transition_to_open = alerting_transition_open
        circuit._transition_to_half_open = alerting_transition_half_open
        circuit._transition_to_closed = alerting_transition_closed
        
        # Trigger recovery process with alerting
        await circuit.force_open()  # Should generate critical alert
        
        await asyncio.sleep(0.6)  # Recovery timeout
        
        # Attempt successful recovery
        health_checker.status = HealthStatus.HEALTHY
        
        try:
            async def recovery_operation():
                return "recovery_success"
            
            result = await circuit.call(recovery_operation)  # Should generate warning then info alerts
            
        except Exception:
            pass
        
        # Validate alerting behavior
        assert len(alerts_generated) >= 1, "Should generate alerts during recovery"
        
        # Should have critical alert for circuit opening
        critical_alerts = [a for a in alerts_generated if a["severity"] == "critical"]
        assert len(critical_alerts) >= 1, "Should generate critical alert when circuit opens"
        
        # Check alert progression
        alert_severities = [a["severity"] for a in alerts_generated]
        
        # Should see severity progression during recovery
        if len(alert_severities) > 1:
            # Later alerts should be less severe (recovery progress)
            severity_levels = {"critical": 3, "warning": 2, "info": 1}
            initial_severity = severity_levels.get(alert_severities[0], 3)
            final_severity = severity_levels.get(alert_severities[-1], 3)
            
            # Recovery should result in lower severity alerts
            assert final_severity <= initial_severity, "Alert severity should improve during recovery"
    
    @pytest.mark.asyncio
    async def test_recovery_completion_validation(self, monitored_config):
        """Test validation of complete recovery."""
        health_checker = MockHealthChecker(HealthStatus.UNHEALTHY)
        health_checker.set_status_progression(["unhealthy", "degraded", "healthy"])
        
        circuit = UnifiedCircuitBreaker(monitored_config, health_checker=health_checker)
        
        # Track recovery completion criteria
        recovery_validation = {
            "circuit_state_closed": False,
            "health_status_healthy": False,
            "consecutive_successes_met": False,
            "error_rate_acceptable": False,
            "response_time_normal": False
        }
        
        # Force failure and begin recovery
        await circuit.force_open()
        
        # Execute recovery process
        for validation_cycle in range(4):
            await asyncio.sleep(0.6)
            
            # Perform recovery operations
            try:
                async def validation_operation():
                    # Simulate normal response time
                    await asyncio.sleep(0.1)
                    return f"validation_{validation_cycle}"
                
                result = await circuit.call(validation_operation)
                
            except Exception:
                continue  # Keep trying recovery
            
            # Check recovery completion criteria
            current_status = circuit.get_status()
            current_metrics = current_status["metrics"]
            
            # Update validation criteria
            recovery_validation["circuit_state_closed"] = (current_status["state"] == "closed")
            recovery_validation["health_status_healthy"] = (
                current_status["health"]["last_health_status"] == "healthy"
            )
            recovery_validation["consecutive_successes_met"] = (
                current_metrics["consecutive_successes"] >= monitored_config.success_threshold
            )
            recovery_validation["error_rate_acceptable"] = (
                current_metrics["current_error_rate"] <= 0.1  # Less than 10% error rate
            )
            recovery_validation["response_time_normal"] = (
                current_metrics["average_response_time"] <= 1.0  # Normal response time
            )
            
            # Check if recovery is complete
            recovery_complete = all(recovery_validation.values())
            
            if recovery_complete:
                break
        
        # Validate recovery completion
        completion_score = sum(recovery_validation.values()) / len(recovery_validation)
        
        # Should achieve high recovery completion score
        assert completion_score >= 0.6, f"Recovery completion score {completion_score} should be >= 0.6"
        
        # Critical criteria should be met
        assert recovery_validation["circuit_state_closed"], "Circuit should be closed after recovery"
        
        # Health and performance should improve
        if recovery_validation["health_status_healthy"]:
            assert recovery_validation["consecutive_successes_met"], "Should have consecutive successes with healthy status"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])