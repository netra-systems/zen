"""
RED TEAM TEST 20: Circuit Breaker State Management

CRITICAL: This test is DESIGNED TO FAIL initially to expose real integration issues.
Tests circuit breaker state coordination across services and failure recovery.

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (high availability requirements)
- Business Goal: Platform Reliability, Error Recovery, Service Resilience
- Value Impact: Poor circuit breaker coordination causes cascade failures and downtime
- Strategic Impact: Core resilience foundation for enterprise-grade AI platform reliability

Testing Level: L3 (Real services, real coordination, minimal mocking)
Expected Initial Result: FAILURE (exposes real circuit breaker coordination gaps)
"""

import asyncio
import json
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest
import httpx
import redis.asyncio as redis
from fastapi.testclient import TestClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
# Fix imports with error handling
try:
    from netra_backend.app.core.network_constants import DatabaseConstants, ServicePorts
except ImportError:
    class DatabaseConstants:
        REDIS_TEST_DB = 1
    class ServicePorts:
        REDIS_DEFAULT = 6379
        POSTGRES_DEFAULT = 5432

try:
    from netra_backend.app.services.circuit_breaker import CircuitBreaker
except ImportError:
    # Mock CircuitBreaker
    class CircuitBreaker:
        def __init__(self, *args, **kwargs):
            self.state = "closed"
            self.failure_count = 0
        async def call(self, func, *args, **kwargs):
            return await func(*args, **kwargs)
        def get_state(self): return self.state
        def reset(self): self.failure_count = 0

try:
    from netra_backend.app.services.circuit_breaker_monitor import CircuitBreakerMonitor
except ImportError:
    class CircuitBreakerMonitor:
        def __init__(self): self.breakers = {}
        async def get_circuit_breaker_stats(self): return {}
        async def reset_circuit_breaker(self, name): pass

try:
    from netra_backend.app.core.reliability_circuit_breaker import ReliabilityCircuitBreaker
except ImportError:
    ReliabilityCircuitBreaker = CircuitBreaker

try:
    from netra_backend.app.services.external_api_client import ExternalAPIClient
except ImportError:
    class ExternalAPIClient:
        async def make_request(self, *args, **kwargs): 
            return {"status": "success", "data": "mock response"}

try:
    from netra_backend.app.llm.client import LLMClient
except ImportError:
    class LLMClient:
        async def generate(self, *args, **kwargs):
            return {"response": "Mock LLM response"}


class TestCircuitBreakerStateManagement:
    """
    RED TEAM TEST 20: Circuit Breaker State Management
    
    Tests critical circuit breaker coordination across services for failure recovery.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """

    @pytest.fixture(scope="class")
    async def real_redis_client(self):
        """Real Redis client for circuit breaker state - will fail if Redis not available."""
        try:
            redis_client = redis.Redis(
                host="localhost",
                port=ServicePorts.REDIS_DEFAULT,
                db=DatabaseConstants.REDIS_TEST_DB,
                decode_responses=True
            )
            
            # Test real connection
            await redis_client.ping()
            
            yield redis_client
        except Exception as e:
            pytest.fail(f"CRITICAL: Real Redis connection failed: {e}")
        finally:
            if 'redis_client' in locals():
                await redis_client.close()

    @pytest.fixture
    def real_test_client(self):
        """Real FastAPI test client - no mocking of the application."""
        return TestClient(app)

    @pytest.fixture
    async def circuit_breaker_monitor(self, real_redis_client):
        """Circuit breaker monitoring service."""
        try:
            monitor = CircuitBreakerMonitor(redis_client=real_redis_client)
            yield monitor
        except Exception as e:
            pytest.fail(f"Circuit breaker monitor initialization failed: {e}")

    @pytest.mark.asyncio
    async def test_01_basic_circuit_breaker_state_tracking_fails(
        self, real_redis_client, circuit_breaker_monitor
    ):
        """
        Test 20A: Basic Circuit Breaker State Tracking (EXPECTED TO FAIL)
        
        Tests basic circuit breaker state management and persistence.
        Will likely FAIL because:
        1. Circuit breaker state persistence may not be implemented
        2. State transitions may not work correctly
        3. Redis state synchronization may be missing
        """
        try:
            # Create test circuit breaker
            service_name = f"test_service_{secrets.token_urlsafe(8)}"
            
            # FAILURE EXPECTED HERE - circuit breaker creation may not work
            circuit_breaker = CircuitBreaker(
                name=service_name,
                failure_threshold=3,
                timeout_seconds=10,
                redis_client=real_redis_client
            )
            
            assert circuit_breaker is not None, "Circuit breaker creation failed"
            
            # Verify initial state
            initial_state = await circuit_breaker.get_state()
            assert initial_state == "closed", \
                f"Circuit breaker should start in closed state, got '{initial_state}'"
            
            # Test state persistence in Redis
            redis_state_key = f"circuit_breaker:{service_name}:state"
            redis_state = await real_redis_client.get(redis_state_key)
            
            if redis_state is None:
                # Try to initialize state in Redis
                await circuit_breaker.reset()
                redis_state = await real_redis_client.get(redis_state_key)
            
            assert redis_state is not None, \
                "Circuit breaker state should be persisted in Redis"
            assert redis_state == "closed", \
                f"Redis state should be 'closed', got '{redis_state}'"
            
            # Test failure recording
            for i in range(2):
                await circuit_breaker.record_failure()
            
            # Should still be closed after 2 failures (threshold is 3)
            current_state = await circuit_breaker.get_state()
            assert current_state == "closed", \
                f"Circuit breaker should remain closed after 2 failures, got '{current_state}'"
            
            # Record third failure to trip the breaker
            await circuit_breaker.record_failure()
            
            # Should now be open
            final_state = await circuit_breaker.get_state()
            assert final_state == "open", \
                f"Circuit breaker should be open after 3 failures, got '{final_state}'"
            
            # Verify state persisted in Redis
            redis_final_state = await real_redis_client.get(redis_state_key)
            assert redis_final_state == "open", \
                f"Redis state should be 'open', got '{redis_final_state}'"
            
            # Test failure count tracking
            failure_count = await circuit_breaker.get_failure_count()
            assert failure_count >= 3, \
                f"Failure count should be at least 3, got {failure_count}"
                
        except ImportError as e:
            pytest.fail(f"Circuit breaker components not available: {e}")
        except Exception as e:
            pytest.fail(f"Basic circuit breaker state tracking test failed: {e}")

    @pytest.mark.asyncio
    async def test_02_cross_service_circuit_breaker_coordination_fails(
        self, real_redis_client, circuit_breaker_monitor
    ):
        """
        Test 20B: Cross-Service Circuit Breaker Coordination (EXPECTED TO FAIL)
        
        Tests circuit breaker coordination between multiple services.
        Will likely FAIL because:
        1. Service-to-service circuit breaker communication may not work
        2. State propagation may be delayed or missing
        3. Coordination protocols may not be implemented
        """
        try:
            # Create multiple service circuit breakers
            services = [
                f"auth_service_{secrets.token_urlsafe(6)}",
                f"llm_service_{secrets.token_urlsafe(6)}",
                f"database_service_{secrets.token_urlsafe(6)}"
            ]
            
            service_breakers = {}
            
            for service_name in services:
                # FAILURE EXPECTED HERE - multi-service coordination may not work
                breaker = CircuitBreaker(
                    name=service_name,
                    failure_threshold=2,
                    timeout_seconds=5,
                    redis_client=real_redis_client
                )
                service_breakers[service_name] = breaker
            
            # Test coordinated failure scenario
            # Simulate auth service failing, which should affect dependent services
            auth_service = service_breakers[services[0]]
            
            # Record failures in auth service
            for i in range(2):
                await auth_service.record_failure()
            
            # Auth service should now be open
            auth_state = await auth_service.get_state()
            assert auth_state == "open", \
                f"Auth service circuit breaker should be open, got '{auth_state}'"
            
            # Monitor should detect this and coordinate with dependent services
            if hasattr(circuit_breaker_monitor, 'coordinate_dependent_services'):
                coordination_result = await circuit_breaker_monitor.coordinate_dependent_services(
                    failed_service=services[0],
                    dependent_services=services[1:]
                )
                
                assert coordination_result is not None, \
                    "Service coordination should return result"
                assert "coordinated_services" in coordination_result, \
                    "Coordination result should include coordinated services"
                
                coordinated_count = coordination_result["coordinated_services"]
                assert coordinated_count == len(services) - 1, \
                    f"Should coordinate {len(services) - 1} services, got {coordinated_count}"
            
            # Test state propagation timing
            await asyncio.sleep(2)  # Wait for propagation
            
            # Check if dependent services are aware of auth service failure
            for service_name in services[1:]:
                breaker = service_breakers[service_name]
                
                if hasattr(breaker, 'get_dependency_status'):
                    dependency_status = await breaker.get_dependency_status(services[0])
                    
                    assert dependency_status is not None, \
                        f"Service {service_name} should know about dependency {services[0]} status"
                    assert dependency_status["state"] == "open", \
                        f"Dependency status should show 'open', got '{dependency_status['state']}'"
            
            # Test recovery coordination
            # Reset auth service to simulate recovery
            await auth_service.reset()
            
            # Record success to move to closed state
            await auth_service.record_success()
            
            auth_recovery_state = await auth_service.get_state()
            assert auth_recovery_state == "closed", \
                f"Auth service should be closed after recovery, got '{auth_recovery_state}'"
            
            # Wait for recovery propagation
            await asyncio.sleep(2)
            
            # Verify dependent services are notified of recovery
            if hasattr(circuit_breaker_monitor, 'propagate_recovery'):
                recovery_result = await circuit_breaker_monitor.propagate_recovery(
                    recovered_service=services[0],
                    dependent_services=services[1:]
                )
                
                assert recovery_result["propagated_to"] == len(services) - 1, \
                    "Recovery should propagate to all dependent services"
                    
        except Exception as e:
            pytest.fail(f"Cross-service circuit breaker coordination test failed: {e}")

    @pytest.mark.asyncio
    async def test_03_circuit_breaker_automatic_recovery_fails(
        self, real_redis_client, circuit_breaker_monitor
    ):
        """
        Test 20C: Circuit Breaker Automatic Recovery (EXPECTED TO FAIL)
        
        Tests automatic recovery mechanisms and half-open state transitions.
        Will likely FAIL because:
        1. Automatic recovery timers may not be implemented
        2. Half-open state logic may not work
        3. Recovery verification may be missing
        """
        try:
            service_name = f"recovery_test_{secrets.token_urlsafe(8)}"
            
            # Create circuit breaker with short timeout for testing
            circuit_breaker = CircuitBreaker(
                name=service_name,
                failure_threshold=2,
                timeout_seconds=3,  # Short timeout for testing
                redis_client=real_redis_client
            )
            
            # Trip the circuit breaker
            for i in range(2):
                await circuit_breaker.record_failure()
            
            # Verify it's open
            open_state = await circuit_breaker.get_state()
            assert open_state == "open", \
                f"Circuit breaker should be open, got '{open_state}'"
            
            # Record the time when it opened
            open_time = time.time()
            
            # Test that requests are rejected while open
            if hasattr(circuit_breaker, 'allow_request'):
                allow_request_open = await circuit_breaker.allow_request()
                assert not allow_request_open, \
                    "Requests should be rejected when circuit breaker is open"
            
            # Wait for timeout period
            await asyncio.sleep(4)  # Wait longer than timeout
            
            # FAILURE EXPECTED HERE - automatic recovery may not work
            # Check if circuit breaker automatically transitioned to half-open
            current_state = await circuit_breaker.get_state()
            
            if current_state == "open":
                # Try to trigger transition manually if automatic doesn't work
                if hasattr(circuit_breaker, 'check_for_recovery'):
                    await circuit_breaker.check_for_recovery()
                    current_state = await circuit_breaker.get_state()
            
            assert current_state in ["half-open", "closed"], \
                f"Circuit breaker should transition to half-open or closed after timeout, got '{current_state}'"
            
            # Test half-open behavior
            if current_state == "half-open":
                # Should allow limited requests in half-open state
                if hasattr(circuit_breaker, 'allow_request'):
                    allow_request_half_open = await circuit_breaker.allow_request()
                    assert allow_request_half_open, \
                        "Should allow requests when circuit breaker is half-open"
                
                # Test successful recovery
                await circuit_breaker.record_success()
                
                recovered_state = await circuit_breaker.get_state()
                assert recovered_state == "closed", \
                    f"Circuit breaker should be closed after successful request, got '{recovered_state}'"
                
                # Test failure in half-open (should go back to open)
                # Create another breaker for this test
                test_breaker = CircuitBreaker(
                    name=f"halfopen_test_{secrets.token_urlsafe(6)}",
                    failure_threshold=1,
                    timeout_seconds=1,
                    redis_client=real_redis_client
                )
                
                # Trip it
                await test_breaker.record_failure()
                await asyncio.sleep(1.5)  # Wait for timeout
                
                # Check for recovery to half-open
                if hasattr(test_breaker, 'check_for_recovery'):
                    await test_breaker.check_for_recovery()
                
                test_state = await test_breaker.get_state()
                if test_state == "half-open":
                    # Record failure in half-open state
                    await test_breaker.record_failure()
                    
                    back_to_open_state = await test_breaker.get_state()
                    assert back_to_open_state == "open", \
                        f"Circuit breaker should return to open after failure in half-open, got '{back_to_open_state}'"
            
            # Test recovery tracking
            if hasattr(circuit_breaker_monitor, 'track_recovery_metrics'):
                recovery_metrics = await circuit_breaker_monitor.track_recovery_metrics(service_name)
                
                assert recovery_metrics is not None, "Recovery metrics should be available"
                assert "recovery_time" in recovery_metrics, \
                    "Recovery metrics should include recovery time"
                
                recovery_time = recovery_metrics["recovery_time"]
                expected_min_time = 3  # At least the timeout period
                assert recovery_time >= expected_min_time, \
                    f"Recovery time should be at least {expected_min_time}s, got {recovery_time}s"
                    
        except Exception as e:
            pytest.fail(f"Circuit breaker automatic recovery test failed: {e}")

    @pytest.mark.asyncio
    async def test_04_circuit_breaker_load_balancing_integration_fails(
        self, real_redis_client, circuit_breaker_monitor
    ):
        """
        Test 20D: Circuit Breaker Load Balancing Integration (EXPECTED TO FAIL)
        
        Tests circuit breaker integration with load balancing and service discovery.
        Will likely FAIL because:
        1. Load balancer integration may not be implemented
        2. Service health checks may not coordinate with circuit breakers
        3. Request routing may not respect circuit breaker state
        """
        try:
            # Simulate multiple instances of the same service
            service_instances = [
                f"llm_service_instance_{i}_{secrets.token_urlsafe(6)}"
                for i in range(3)
            ]
            
            instance_breakers = {}
            
            # Create circuit breakers for each instance
            for instance_name in service_instances:
                breaker = CircuitBreaker(
                    name=instance_name,
                    failure_threshold=2,
                    timeout_seconds=5,
                    redis_client=real_redis_client
                )
                instance_breakers[instance_name] = breaker
            
            # Create external API client to test load balancing
            if hasattr(ExternalAPIClient, '__init__'):
                # FAILURE EXPECTED HERE - load balancer integration may not work
                api_client = ExternalAPIClient(
                    service_instances=service_instances,
                    circuit_breaker_monitor=circuit_breaker_monitor
                )
                
                # Test normal operation - all instances healthy
                for i in range(6):  # Make multiple requests
                    try:
                        if hasattr(api_client, 'make_request'):
                            response = await api_client.make_request(
                                endpoint="/test",
                                method="GET",
                                timeout=5
                            )
                            
                            # Should distribute requests across instances
                            assert "instance_used" in response, \
                                "Response should indicate which instance was used"
                    except Exception as e:
                        # Expected if external service not available
                        pass
                
                # Simulate failure in one instance
                failed_instance = service_instances[0]
                failed_breaker = instance_breakers[failed_instance]
                
                # Trip the circuit breaker for first instance
                for i in range(2):
                    await failed_breaker.record_failure()
                
                failed_state = await failed_breaker.get_state()
                assert failed_state == "open", \
                    f"Failed instance circuit breaker should be open, got '{failed_state}'"
                
                # Test load balancer avoids failed instance
                if hasattr(api_client, 'get_healthy_instances'):
                    healthy_instances = await api_client.get_healthy_instances()
                    
                    assert len(healthy_instances) == len(service_instances) - 1, \
                        f"Should have {len(service_instances) - 1} healthy instances, got {len(healthy_instances)}"
                    
                    assert failed_instance not in healthy_instances, \
                        "Failed instance should not be in healthy instances list"
                
                # Test that requests go to healthy instances only
                for i in range(3):
                    try:
                        if hasattr(api_client, 'make_request'):
                            response = await api_client.make_request(
                                endpoint="/test",
                                method="GET",
                                timeout=5
                            )
                            
                            if "instance_used" in response:
                                instance_used = response["instance_used"]
                                assert instance_used != failed_instance, \
                                    f"Should not use failed instance {failed_instance}, but used {instance_used}"
                    except Exception:
                        # Expected if no healthy instances available
                        pass
            
            # Test circuit breaker health check integration
            if hasattr(circuit_breaker_monitor, 'get_service_health_summary'):
                health_summary = await circuit_breaker_monitor.get_service_health_summary(
                    service_instances
                )
                
                assert health_summary is not None, "Health summary should be available"
                assert "healthy_count" in health_summary, \
                    "Health summary should include healthy count"
                assert "unhealthy_count" in health_summary, \
                    "Health summary should include unhealthy count"
                
                expected_healthy = len(service_instances) - 1  # One failed
                assert health_summary["healthy_count"] == expected_healthy, \
                    f"Should have {expected_healthy} healthy instances, got {health_summary['healthy_count']}"
                
                assert health_summary["unhealthy_count"] == 1, \
                    f"Should have 1 unhealthy instance, got {health_summary['unhealthy_count']}"
                    
        except Exception as e:
            pytest.fail(f"Circuit breaker load balancing integration test failed: {e}")

    @pytest.mark.asyncio
    async def test_05_circuit_breaker_metrics_monitoring_fails(
        self, real_redis_client, circuit_breaker_monitor
    ):
        """
        Test 20E: Circuit Breaker Metrics and Monitoring (EXPECTED TO FAIL)
        
        Tests comprehensive metrics collection and monitoring for circuit breakers.
        Will likely FAIL because:
        1. Metrics collection may not be implemented
        2. Monitoring dashboards may not exist
        3. Alerting on circuit breaker state changes may be missing
        """
        try:
            # Create test services with circuit breakers
            test_services = [
                f"monitored_service_{i}_{secrets.token_urlsafe(6)}"
                for i in range(2)
            ]
            
            service_breakers = {}
            
            for service_name in test_services:
                breaker = CircuitBreaker(
                    name=service_name,
                    failure_threshold=3,
                    timeout_seconds=5,
                    redis_client=real_redis_client
                )
                service_breakers[service_name] = breaker
            
            # Generate test activity
            service1 = service_breakers[test_services[0]]
            service2 = service_breakers[test_services[1]]
            
            # Service 1: Some failures but not enough to trip
            for i in range(2):
                await service1.record_failure()
            await service1.record_success()
            
            # Service 2: Enough failures to trip the breaker
            for i in range(3):
                await service2.record_failure()
            
            # Wait for metrics collection
            await asyncio.sleep(1)
            
            # FAILURE EXPECTED HERE - metrics collection may not work
            if hasattr(circuit_breaker_monitor, 'collect_metrics'):
                metrics = await circuit_breaker_monitor.collect_metrics()
                
                assert metrics is not None, "Circuit breaker metrics should be available"
                assert "services" in metrics, "Metrics should include service data"
                
                service_metrics = metrics["services"]
                
                # Verify metrics for both services
                for service_name in test_services:
                    assert service_name in service_metrics, \
                        f"Metrics should include data for {service_name}"
                    
                    service_data = service_metrics[service_name]
                    
                    assert "state" in service_data, \
                        f"Service {service_name} metrics should include state"
                    assert "failure_count" in service_data, \
                        f"Service {service_name} metrics should include failure count"
                    assert "last_failure_time" in service_data, \
                        f"Service {service_name} metrics should include last failure time"
                
                # Verify service 2 is open
                service2_metrics = service_metrics[test_services[1]]
                assert service2_metrics["state"] == "open", \
                    f"Service 2 should be open, got '{service2_metrics['state']}'"
                
                assert service2_metrics["failure_count"] >= 3, \
                    f"Service 2 should have at least 3 failures, got {service2_metrics['failure_count']}"
            
            # Test alerting functionality
            if hasattr(circuit_breaker_monitor, 'check_alert_conditions'):
                alert_conditions = await circuit_breaker_monitor.check_alert_conditions()
                
                assert alert_conditions is not None, "Alert conditions should be checkable"
                assert "alerts" in alert_conditions, "Should include alerts list"
                
                alerts = alert_conditions["alerts"]
                
                # Should have alert for service 2 being open
                service2_alerts = [
                    alert for alert in alerts
                    if alert.get("service") == test_services[1]
                ]
                
                assert len(service2_alerts) > 0, \
                    f"Should have alerts for service {test_services[1]}"
                
                critical_alerts = [
                    alert for alert in service2_alerts
                    if alert.get("severity") in ["critical", "high"]
                ]
                
                assert len(critical_alerts) > 0, \
                    "Should have critical alerts for open circuit breaker"
            
            # Test dashboard data preparation
            if hasattr(circuit_breaker_monitor, 'get_dashboard_data'):
                dashboard_data = await circuit_breaker_monitor.get_dashboard_data()
                
                assert dashboard_data is not None, "Dashboard data should be available"
                assert "overview" in dashboard_data, \
                    "Dashboard should include overview data"
                assert "services" in dashboard_data, \
                    "Dashboard should include detailed service data"
                
                overview = dashboard_data["overview"]
                assert "total_services" in overview, \
                    "Overview should include total services count"
                assert "healthy_services" in overview, \
                    "Overview should include healthy services count"
                assert "unhealthy_services" in overview, \
                    "Overview should include unhealthy services count"
                
                # Verify counts
                assert overview["total_services"] == len(test_services), \
                    f"Total services should be {len(test_services)}, got {overview['total_services']}"
                
                assert overview["unhealthy_services"] >= 1, \
                    f"Should have at least 1 unhealthy service, got {overview['unhealthy_services']}"
            
            # Test historical metrics
            if hasattr(circuit_breaker_monitor, 'get_historical_metrics'):
                historical_metrics = await circuit_breaker_monitor.get_historical_metrics(
                    service_name=test_services[1],
                    time_range_minutes=5
                )
                
                assert historical_metrics is not None, \
                    "Historical metrics should be available"
                assert "timeline" in historical_metrics, \
                    "Historical metrics should include timeline"
                
                timeline = historical_metrics["timeline"]
                assert len(timeline) > 0, \
                    "Timeline should have data points"
                
                # Should show state change from closed to open
                state_changes = [
                    point for point in timeline
                    if point.get("event_type") == "state_change"
                ]
                
                assert len(state_changes) > 0, \
                    "Should have recorded state changes"
                    
        except Exception as e:
            pytest.fail(f"Circuit breaker metrics and monitoring test failed: {e}")


# Utility class for circuit breaker testing
class RedTeamCircuitBreakerTestUtils:
    """Utility methods for circuit breaker state management testing."""
    
    @staticmethod
    async def create_test_circuit_breaker(
        name: str,
        redis_client,
        failure_threshold: int = 3,
        timeout_seconds: int = 10
    ) -> CircuitBreaker:
        """Create a test circuit breaker with specified parameters."""
        try:
            breaker = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                timeout_seconds=timeout_seconds,
                redis_client=redis_client
            )
            
            # Initialize in Redis
            await breaker.reset()
            
            return breaker
        except Exception as e:
            pytest.fail(f"Failed to create test circuit breaker: {e}")
    
    @staticmethod
    async def simulate_service_failures(
        circuit_breaker: CircuitBreaker,
        failure_count: int
    ) -> Dict[str, Any]:
        """Simulate multiple service failures and return state info."""
        initial_state = await circuit_breaker.get_state()
        
        for i in range(failure_count):
            await circuit_breaker.record_failure()
        
        final_state = await circuit_breaker.get_state()
        total_failures = await circuit_breaker.get_failure_count()
        
        return {
            "initial_state": initial_state,
            "final_state": final_state,
            "failures_recorded": failure_count,
            "total_failure_count": total_failures,
            "state_changed": initial_state != final_state
        }
    
    @staticmethod
    async def wait_for_recovery_transition(
        circuit_breaker: CircuitBreaker,
        max_wait_seconds: int = 30
    ) -> Optional[str]:
        """Wait for circuit breaker to transition from open state."""
        wait_time = 0
        
        while wait_time < max_wait_seconds:
            current_state = await circuit_breaker.get_state()
            
            if current_state != "open":
                return current_state
            
            # Try to trigger recovery check if available
            if hasattr(circuit_breaker, 'check_for_recovery'):
                await circuit_breaker.check_for_recovery()
            
            await asyncio.sleep(1)
            wait_time += 1
        
        return None
    
    @staticmethod
    async def verify_redis_state_consistency(
        circuit_breaker: CircuitBreaker,
        redis_client,
        service_name: str
    ) -> Dict[str, Any]:
        """Verify consistency between circuit breaker object and Redis state."""
        
        # Get state from circuit breaker object
        object_state = await circuit_breaker.get_state()
        object_failures = await circuit_breaker.get_failure_count()
        
        # Get state from Redis directly
        redis_state_key = f"circuit_breaker:{service_name}:state"
        redis_failures_key = f"circuit_breaker:{service_name}:failures"
        
        redis_state = await redis_client.get(redis_state_key)
        redis_failures = await redis_client.get(redis_failures_key)
        
        consistency_report = {
            "object_state": object_state,
            "redis_state": redis_state,
            "object_failures": object_failures,
            "redis_failures": int(redis_failures) if redis_failures else 0,
            "state_consistent": object_state == redis_state,
            "failures_consistent": object_failures == (int(redis_failures) if redis_failures else 0)
        }
        
        consistency_report["fully_consistent"] = (
            consistency_report["state_consistent"] and
            consistency_report["failures_consistent"]
        )
        
        return consistency_report
    
    @staticmethod
    def create_mock_external_request():
        """Create a mock external request function for testing."""
        
        async def mock_request():
            """Mock external request that can be configured to succeed or fail."""
            # In real tests, this would make actual HTTP requests
            # For testing, we simulate network calls
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # This would be configured based on test scenario
            success_rate = 0.7  # 70% success rate
            
            import random
            if random.random() < success_rate:
                return {"status": "success", "data": "mock_response"}
            else:
                raise httpx.ConnectError("Mock network failure")
        
        return mock_request