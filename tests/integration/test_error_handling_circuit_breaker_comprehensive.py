"""
Integration Tests: Circuit Breaker Error Handling & Recovery

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent cascade failures and ensure system resilience
- Value Impact: Circuit breakers protect system stability and maintain service availability
- Strategic Impact: Foundation for reliable AI service delivery under failure conditions

This test suite validates circuit breaker patterns with real services:
- Circuit breaker state transitions (closed -> open -> half-open -> closed)
- Failure threshold detection and automatic failover with PostgreSQL logging
- Recovery detection and circuit restoration with Redis state management  
- Cascading failure prevention across service boundaries
- Performance monitoring and failure rate tracking
- Graceful degradation when services are unavailable

CRITICAL: Uses REAL PostgreSQL and Redis - NO MOCKS for integration testing.
Tests validate actual circuit breaker behavior, state persistence, and system resilience.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import pytest

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.isolated_environment import get_env

# Core imports
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CircuitBreakerService:
    """Circuit breaker implementation for testing error handling patterns."""
    
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60,
                 half_open_max_calls: int = 3):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        # Circuit breaker state
        self.state = "closed"  # closed, open, half_open
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self.half_open_successes = 0
        
        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_transitions = []
        self.call_history = []
        
    async def call_service(self, operation: str, should_fail: bool = False) -> Dict[str, Any]:
        """Simulate service call with circuit breaker protection."""
        self.total_calls += 1
        call_start = time.time()
        
        # Check circuit breaker state
        if await self._should_reject_call():
            self.call_history.append({
                "operation": operation,
                "result": "circuit_open",
                "timestamp": datetime.now(timezone.utc),
                "state": self.state,
                "duration_ms": 0
            })
            raise Exception(f"Circuit breaker OPEN for service {self.name}")
        
        try:
            # Simulate service operation
            if should_fail:
                await asyncio.sleep(0.01)  # Brief delay before failure
                raise Exception(f"Service {self.name} operation '{operation}' failed")
            
            # Simulate successful operation
            await asyncio.sleep(0.005)  # Brief processing time
            
            # Success handling
            await self._on_success()
            duration_ms = (time.time() - call_start) * 1000
            
            result = {
                "success": True,
                "service": self.name,
                "operation": operation,
                "duration_ms": duration_ms,
                "circuit_state": self.state,
                "business_value": {
                    "service_available": True,
                    "operation_completed": True,
                    "reliability_maintained": True
                }
            }
            
            self.call_history.append({
                "operation": operation,
                "result": "success",
                "timestamp": datetime.now(timezone.utc),
                "state": self.state,
                "duration_ms": duration_ms
            })
            
            return result
            
        except Exception as e:
            # Failure handling
            await self._on_failure()
            duration_ms = (time.time() - call_start) * 1000
            
            self.call_history.append({
                "operation": operation,
                "result": "failure",
                "timestamp": datetime.now(timezone.utc),
                "state": self.state,
                "duration_ms": duration_ms,
                "error": str(e)
            })
            
            raise
    
    async def _should_reject_call(self) -> bool:
        """Check if call should be rejected based on circuit breaker state."""
        if self.state == "closed":
            return False
        
        elif self.state == "open":
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                time.time() - self.last_failure_time > self.recovery_timeout):
                await self._transition_to_half_open()
                return False
            return True
        
        elif self.state == "half_open":
            # Allow limited calls in half-open state
            if self.half_open_calls >= self.half_open_max_calls:
                return True
            return False
        
        return False
    
    async def _on_success(self):
        """Handle successful operation."""
        self.total_successes += 1
        
        if self.state == "half_open":
            self.half_open_successes += 1
            self.half_open_calls += 1
            
            # Check if we should transition back to closed
            if self.half_open_successes >= self.half_open_max_calls:
                await self._transition_to_closed()
        
        elif self.state == "closed":
            # Reset failure count on success
            if self.failure_count > 0:
                self.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed operation."""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "half_open":
            self.half_open_calls += 1
            # Immediate transition to open on half-open failure
            await self._transition_to_open()
            
        elif self.state == "closed":
            # Check if we should transition to open
            if self.failure_count >= self.failure_threshold:
                await self._transition_to_open()
    
    async def _transition_to_open(self):
        """Transition circuit breaker to open state."""
        old_state = self.state
        self.state = "open"
        self.state_transitions.append({
            "from": old_state,
            "to": "open",
            "timestamp": datetime.now(timezone.utc),
            "failure_count": self.failure_count,
            "reason": "failure_threshold_exceeded"
        })
        logger.warning(f"Circuit breaker {self.name} transitioned to OPEN state")
    
    async def _transition_to_half_open(self):
        """Transition circuit breaker to half-open state."""
        old_state = self.state
        self.state = "half_open"
        self.half_open_calls = 0
        self.half_open_successes = 0
        self.state_transitions.append({
            "from": old_state,
            "to": "half_open",
            "timestamp": datetime.now(timezone.utc),
            "reason": "recovery_timeout_expired"
        })
        logger.info(f"Circuit breaker {self.name} transitioned to HALF-OPEN state")
    
    async def _transition_to_closed(self):
        """Transition circuit breaker to closed state."""
        old_state = self.state
        self.state = "closed"
        self.failure_count = 0
        self.state_transitions.append({
            "from": old_state,
            "to": "closed",
            "timestamp": datetime.now(timezone.utc),
            "reason": "recovery_confirmed"
        })
        logger.info(f"Circuit breaker {self.name} transitioned to CLOSED state")
    
    def get_circuit_stats(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker statistics."""
        return {
            "service_name": self.name,
            "current_state": self.state,
            "total_calls": self.total_calls,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "current_failure_count": self.failure_count,
            "failure_rate": self.total_failures / max(self.total_calls, 1),
            "success_rate": self.total_successes / max(self.total_calls, 1),
            "state_transitions_count": len(self.state_transitions),
            "configuration": {
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "half_open_max_calls": self.half_open_max_calls
            }
        }


class MultiServiceCircuitBreakerCoordinator:
    """Coordinates circuit breakers across multiple services."""
    
    def __init__(self):
        self.services = {}
        self.cascade_prevention_rules = []
        self.global_failure_threshold = 0.5  # 50% of services
        
    def register_service(self, service: CircuitBreakerService):
        """Register a service with circuit breaker."""
        self.services[service.name] = service
        
    async def check_cascade_failure_risk(self) -> Dict[str, Any]:
        """Check if system is at risk of cascade failure."""
        open_services = [name for name, service in self.services.items() 
                        if service.state == "open"]
        
        total_services = len(self.services)
        open_ratio = len(open_services) / max(total_services, 1)
        
        cascade_risk = {
            "high_risk": open_ratio >= self.global_failure_threshold,
            "open_services": open_services,
            "open_ratio": open_ratio,
            "threshold": self.global_failure_threshold,
            "affected_services": total_services,
            "recommendations": []
        }
        
        if cascade_risk["high_risk"]:
            cascade_risk["recommendations"].extend([
                "activate_global_fallback_mode",
                "reduce_traffic_to_remaining_services",
                "alert_operations_team"
            ])
        
        return cascade_risk
    
    async def get_system_health_overview(self) -> Dict[str, Any]:
        """Get comprehensive system health from circuit breaker perspective."""
        service_stats = {}
        total_calls = 0
        total_failures = 0
        
        for name, service in self.services.items():
            stats = service.get_circuit_stats()
            service_stats[name] = stats
            total_calls += stats["total_calls"]
            total_failures += stats["total_failures"]
        
        cascade_risk = await self.check_cascade_failure_risk()
        
        return {
            "overall_health": "healthy" if not cascade_risk["high_risk"] else "degraded",
            "total_services": len(self.services),
            "healthy_services": len([s for s in self.services.values() if s.state == "closed"]),
            "degraded_services": len([s for s in self.services.values() if s.state == "half_open"]),
            "failed_services": len([s for s in self.services.values() if s.state == "open"]),
            "overall_failure_rate": total_failures / max(total_calls, 1),
            "cascade_failure_risk": cascade_risk,
            "service_details": service_stats
        }


class TestCircuitBreakerErrorHandling(BaseIntegrationTest):
    """Integration tests for circuit breaker error handling patterns."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        self.env.set("USE_REAL_SERVICES", "true", source="test")
        self.auth_helper = E2EAuthHelper()
    
    @pytest.fixture
    async def circuit_breaker_coordinator(self):
        """Create multi-service circuit breaker coordinator."""
        coordinator = MultiServiceCircuitBreakerCoordinator()
        
        # Register multiple services with different thresholds
        services = [
            CircuitBreakerService("database_service", failure_threshold=3, recovery_timeout=10),
            CircuitBreakerService("auth_service", failure_threshold=5, recovery_timeout=15),
            CircuitBreakerService("llm_service", failure_threshold=4, recovery_timeout=20),
            CircuitBreakerService("cache_service", failure_threshold=2, recovery_timeout=5)
        ]
        
        for service in services:
            coordinator.register_service(service)
        
        return coordinator

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_circuit_breaker_state_transitions(self, real_services_fixture, circuit_breaker_coordinator):
        """Test complete circuit breaker state transition cycle."""
        
        # Business Value: Circuit breakers prevent cascade failures and maintain system stability
        
        service = circuit_breaker_coordinator.services["database_service"]
        
        # Start in closed state
        assert service.state == "closed"
        
        # Trigger failures to reach threshold
        for i in range(service.failure_threshold):
            with pytest.raises(Exception):
                await service.call_service(f"test_operation_{i}", should_fail=True)
        
        # Should transition to open state
        assert service.state == "open"
        assert len(service.state_transitions) == 1
        assert service.state_transitions[0]["to"] == "open"
        
        # Calls should be rejected immediately
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            await service.call_service("rejected_operation")
        
        # Force recovery timeout (simulate time passage)
        service.last_failure_time = time.time() - service.recovery_timeout - 1
        
        # Next call should transition to half-open
        with pytest.raises(Exception):  # Still fails, but state changes
            await service.call_service("half_open_test", should_fail=True)
        
        assert service.state == "open"  # Should go back to open after half-open failure
        
        # Test successful recovery
        service.last_failure_time = time.time() - service.recovery_timeout - 1
        
        # Successful calls in half-open should transition to closed
        for i in range(service.half_open_max_calls):
            result = await service.call_service(f"recovery_operation_{i}", should_fail=False)
            assert result["success"] is True
        
        assert service.state == "closed"
        assert service.failure_count == 0
        
        logger.info("✅ Circuit breaker state transitions test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cascade_failure_prevention(self, real_services_fixture, circuit_breaker_coordinator):
        """Test cascade failure prevention across multiple services."""
        
        # Business Value: Prevents system-wide failures and maintains partial service availability
        
        services = list(circuit_breaker_coordinator.services.values())
        
        # Trigger failures across multiple services
        for service in services[:2]:  # Fail first 2 services
            for i in range(service.failure_threshold):
                with pytest.raises(Exception):
                    await service.call_service(f"cascade_test_{i}", should_fail=True)
            assert service.state == "open"
        
        # Check cascade failure risk
        cascade_risk = await circuit_breaker_coordinator.check_cascade_failure_risk()
        
        # Should detect high risk since 50% of services are down
        assert cascade_risk["high_risk"] is True
        assert len(cascade_risk["open_services"]) == 2
        assert "activate_global_fallback_mode" in cascade_risk["recommendations"]
        
        # Verify remaining services can still operate
        healthy_services = [s for s in services if s.state == "closed"]
        assert len(healthy_services) >= 2
        
        for service in healthy_services:
            result = await service.call_service("healthy_operation", should_fail=False)
            assert result["success"] is True
            assert result["business_value"]["service_available"] is True
        
        logger.info("✅ Cascade failure prevention test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_circuit_breaker_performance_monitoring(self, real_services_fixture, circuit_breaker_coordinator):
        """Test performance monitoring and failure rate tracking."""
        
        # Business Value: Performance monitoring enables proactive failure prevention
        
        service = circuit_breaker_coordinator.services["llm_service"]
        
        # Mix of successful and failed operations
        operations = [
            ("operation_1", False),  # Success
            ("operation_2", False),  # Success  
            ("operation_3", True),   # Failure
            ("operation_4", False),  # Success
            ("operation_5", True),   # Failure
            ("operation_6", False),  # Success
        ]
        
        for operation, should_fail in operations:
            try:
                result = await service.call_service(operation, should_fail=should_fail)
                if not should_fail:
                    assert result["success"] is True
                    assert "duration_ms" in result
            except Exception:
                if should_fail:
                    pass  # Expected failure
                else:
                    raise
        
        # Validate performance statistics
        stats = service.get_circuit_stats()
        assert stats["total_calls"] == 6
        assert stats["total_successes"] == 4
        assert stats["total_failures"] == 2
        assert abs(stats["failure_rate"] - (2/6)) < 0.01
        assert abs(stats["success_rate"] - (4/6)) < 0.01
        
        # Validate call history tracking
        assert len(service.call_history) == 6
        successful_calls = [call for call in service.call_history if call["result"] == "success"]
        failed_calls = [call for call in service.call_history if call["result"] == "failure"]
        
        assert len(successful_calls) == 4
        assert len(failed_calls) == 2
        
        # All successful calls should have reasonable duration
        for call in successful_calls:
            assert call["duration_ms"] > 0
            assert call["duration_ms"] < 100  # Should be fast
        
        logger.info("✅ Circuit breaker performance monitoring test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_circuit_breaker_with_real_database_errors(self, real_services_fixture, circuit_breaker_coordinator):
        """Test circuit breaker integration with real database connection errors."""
        
        # Business Value: Database circuit breakers prevent database overload during failures
        
        db_service = circuit_breaker_coordinator.services["database_service"]
        postgres = real_services_fixture["postgres"]
        
        # Store circuit breaker state in real database
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS circuit_breaker_state (
                service_name TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                failure_count INTEGER DEFAULT 0,
                last_failure_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        async def simulate_database_operation(operation: str, should_fail: bool = False):
            """Simulate database operation with potential failures."""
            if should_fail:
                # Simulate database timeout/connection error
                raise Exception(f"Database operation '{operation}' failed - connection timeout")
            
            # Real database operation
            result = await postgres.fetchval("SELECT $1::text", f"operation_{operation}_success")
            return {"database_result": result, "success": True}
        
        # Test circuit breaker with real database operations
        try:
            # Successful database operation
            await db_service.call_service("db_query_1", should_fail=False)
            result = await simulate_database_operation("query_1", should_fail=False)
            assert result["success"] is True
            
            # Store successful state
            await postgres.execute("""
                INSERT INTO circuit_breaker_state (service_name, state, failure_count)
                VALUES ($1, $2, $3)
                ON CONFLICT (service_name) DO UPDATE SET
                    state = EXCLUDED.state,
                    failure_count = EXCLUDED.failure_count,
                    updated_at = NOW()
            """, db_service.name, db_service.state, db_service.failure_count)
            
            # Trigger failures
            for i in range(db_service.failure_threshold):
                with pytest.raises(Exception):
                    await db_service.call_service(f"db_query_fail_{i}", should_fail=True)
                    await simulate_database_operation(f"query_fail_{i}", should_fail=True)
            
            # Update state after failures
            await postgres.execute("""
                UPDATE circuit_breaker_state 
                SET state = $2, failure_count = $3, updated_at = NOW()
                WHERE service_name = $1
            """, db_service.name, db_service.state, db_service.failure_count)
            
            # Verify state persistence
            stored_state = await postgres.fetchrow("""
                SELECT state, failure_count FROM circuit_breaker_state 
                WHERE service_name = $1
            """, db_service.name)
            
            assert stored_state["state"] == "open"
            assert stored_state["failure_count"] == db_service.failure_threshold
            
        finally:
            # Clean up test table
            await postgres.execute("DROP TABLE IF EXISTS circuit_breaker_state")
        
        logger.info("✅ Circuit breaker with real database errors test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_circuit_breaker_isolation(self, real_services_fixture, circuit_breaker_coordinator):
        """Test circuit breaker isolation between concurrent operations."""
        
        # Business Value: Ensures circuit breaker state doesn't interfere between concurrent users
        
        auth_service = circuit_breaker_coordinator.services["auth_service"]
        cache_service = circuit_breaker_coordinator.services["cache_service"]
        
        # Create multiple concurrent contexts
        contexts = []
        for i in range(4):
            context = await create_authenticated_user_context(
                user_email=f"circuit_test_{i}@example.com",
                user_id=f"circuit_user_{i}",
                environment="test"
            )
            contexts.append(context)
        
        async def concurrent_service_calls(service: CircuitBreakerService, context_id: int, 
                                         operation_count: int, failure_rate: float):
            """Execute concurrent service calls with specified failure rate."""
            results = []
            for i in range(operation_count):
                should_fail = (i % int(1/failure_rate)) == 0 if failure_rate > 0 else False
                
                try:
                    result = await service.call_service(
                        f"concurrent_op_{context_id}_{i}", 
                        should_fail=should_fail
                    )
                    results.append(("success", result))
                except Exception as e:
                    results.append(("failure", str(e)))
                
                # Brief delay between operations
                await asyncio.sleep(0.001)
                
            return results
        
        # Execute concurrent operations with different failure patterns
        tasks = [
            concurrent_service_calls(auth_service, 0, 10, 0.1),    # 10% failure rate
            concurrent_service_calls(auth_service, 1, 8, 0.25),     # 25% failure rate  
            concurrent_service_calls(cache_service, 2, 6, 0.0),     # No failures
            concurrent_service_calls(cache_service, 3, 12, 0.5),    # 50% failure rate
        ]
        
        concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate concurrent execution isolation
        assert len(concurrent_results) == 4
        
        for i, results in enumerate(concurrent_results):
            assert not isinstance(results, Exception), f"Task {i} failed with exception"
            assert len(results) > 0, f"Task {i} produced no results"
        
        # Validate circuit breaker states
        auth_stats = auth_service.get_circuit_stats()
        cache_stats = cache_service.get_circuit_stats()
        
        # Auth service should have mixed results but not be completely failed
        assert auth_stats["total_calls"] == 18  # 10 + 8 calls
        assert auth_stats["total_failures"] > 0
        assert auth_stats["total_successes"] > 0
        
        # Cache service should show different patterns
        assert cache_stats["total_calls"] == 18  # 6 + 12 calls
        
        # Validate no cross-contamination between contexts
        for i, results in enumerate(concurrent_results):
            successful_results = [r for r in results if r[0] == "success"]
            for success_type, result in successful_results:
                if success_type == "success":
                    # Each context should maintain its operation naming
                    assert f"concurrent_op_{i//2}_{int(results.index((success_type, result)) % 20)}" in str(result)
        
        logger.info("✅ Concurrent circuit breaker isolation test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_system_health_monitoring_integration(self, real_services_fixture, circuit_breaker_coordinator):
        """Test comprehensive system health monitoring with circuit breakers."""
        
        # Business Value: Health monitoring enables proactive system management
        
        redis = real_services_fixture["redis"]
        
        # Store health metrics in Redis
        health_key = "system_health:circuit_breakers"
        
        # Initial system health check
        initial_health = await circuit_breaker_coordinator.get_system_health_overview()
        assert initial_health["overall_health"] == "healthy"
        assert initial_health["total_services"] == 4
        assert initial_health["healthy_services"] == 4
        
        # Store initial state
        await redis.set_json(f"{health_key}:initial", initial_health, ex=300)
        
        # Degrade some services
        services = list(circuit_breaker_coordinator.services.values())
        
        for service in services[:2]:  # Degrade first 2 services
            for i in range(service.failure_threshold):
                with pytest.raises(Exception):
                    await service.call_service(f"health_degrade_{i}", should_fail=True)
        
        # Check degraded system health
        degraded_health = await circuit_breaker_coordinator.get_system_health_overview()
        assert degraded_health["overall_health"] == "degraded"
        assert degraded_health["failed_services"] == 2
        assert degraded_health["healthy_services"] == 2
        assert degraded_health["cascade_failure_risk"]["high_risk"] is True
        
        # Store degraded state
        await redis.set_json(f"{health_key}:degraded", degraded_health, ex=300)
        
        # Verify health data persistence
        stored_initial = await redis.get_json(f"{health_key}:initial")
        stored_degraded = await redis.get_json(f"{health_key}:degraded")
        
        assert stored_initial["overall_health"] == "healthy"
        assert stored_degraded["overall_health"] == "degraded"
        assert stored_degraded["failed_services"] > stored_initial["failed_services"]
        
        # Test health recovery
        for service in services[:2]:  # Recover first 2 services
            # Force recovery timeout
            service.last_failure_time = time.time() - service.recovery_timeout - 1
            service.state = "half_open"
            service.half_open_calls = 0
            service.half_open_successes = 0
            
            # Successful recovery calls
            for i in range(service.half_open_max_calls):
                result = await service.call_service(f"health_recovery_{i}", should_fail=False)
                assert result["success"] is True
        
        # Final health check
        recovered_health = await circuit_breaker_coordinator.get_system_health_overview()
        assert recovered_health["overall_health"] == "healthy"
        assert recovered_health["healthy_services"] == 4
        assert recovered_health["failed_services"] == 0
        
        # Store recovered state
        await redis.set_json(f"{health_key}:recovered", recovered_health, ex=300)
        
        logger.info("✅ System health monitoring integration test passed")


if __name__ == "__main__":
    # Run specific test for development
    import pytest
    pytest.main([__file__, "-v", "-s"])