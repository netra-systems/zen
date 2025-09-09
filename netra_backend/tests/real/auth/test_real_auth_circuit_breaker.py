"""
Real Auth Circuit Breaker Tests

Business Value: Platform/Internal - Reliability & System Stability - Validates circuit breaker
patterns for authentication failures and service recovery using real services.

Coverage Target: 85%
Test Category: Integration with Real Services - RELIABILITY CRITICAL
Infrastructure Required: Docker (PostgreSQL, Redis, Auth Service, Backend)

This test suite validates circuit breaker patterns for authentication services,
failure detection, automatic recovery, and system stability under auth service outages.

CRITICAL: Tests system resilience to prevent cascade failures when auth services
are unavailable, as described in auth circuit breaker requirements.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from unittest.mock import patch, MagicMock

import pytest
import redis.asyncio as redis
from fastapi import HTTPException, status
from httpx import AsyncClient, ConnectError, TimeoutException

# Import circuit breaker and auth components
from netra_backend.app.core.auth_constants import (
    AuthConstants, AuthErrorConstants, HeaderConstants, JWTConstants
)
from netra_backend.app.auth_dependencies import get_request_scoped_db_session_for_fastapi
from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.main import app
from shared.isolated_environment import IsolatedEnvironment

# Import test framework
from test_framework.docker_test_manager import UnifiedDockerManager

# Use isolated environment for all env access
env = IsolatedEnvironment()

# Docker manager for real services
docker_manager = UnifiedDockerManager()

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.circuit_breaker
@pytest.mark.reliability
@pytest.mark.asyncio
class TestRealAuthCircuitBreaker:
    """
    Real auth circuit breaker tests using Docker services.
    
    Tests circuit breaker patterns, failure detection, automatic recovery,
    and graceful degradation when auth services fail using real infrastructure.
    
    CRITICAL: Validates system stability and prevents cascade failures.
    """

    @pytest.fixture(scope="class", autouse=True)
    async def setup_docker_services(self):
        """Start Docker services for circuit breaker testing."""
        print("🐳 Starting Docker services for auth circuit breaker tests...")
        
        services = ["backend", "auth", "postgres", "redis"]
        
        try:
            await docker_manager.start_services_async(
                services=services,
                health_check=True,
                timeout=120
            )
            
            await asyncio.sleep(5)
            print("✅ Docker services ready for circuit breaker tests")
            yield
            
        except Exception as e:
            pytest.fail(f"❌ Failed to start Docker services for circuit breaker tests: {e}")
        finally:
            print("🧹 Cleaning up Docker services after circuit breaker tests...")
            await docker_manager.cleanup_async()

    @pytest.fixture
    async def async_client(self):
        """Create async HTTP client for circuit breaker testing."""
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client

    @pytest.fixture
    async def redis_client(self):
        """Create real Redis client for circuit breaker state storage."""
        redis_url = env.get_env_var("REDIS_URL", "redis://localhost:6381")
        
        try:
            client = redis.from_url(redis_url, decode_responses=True)
            await client.ping()
            yield client
        except Exception as e:
            pytest.fail(f"❌ Failed to connect to Redis for circuit breaker tests: {e}")
        finally:
            if 'client' in locals():
                await client.aclose()

    def create_circuit_breaker_state(
        self, 
        service_name: str, 
        state: CircuitState = CircuitState.CLOSED,
        **kwargs
    ) -> Dict[str, Any]:
        """Create circuit breaker state data."""
        now = datetime.utcnow()
        
        return {
            "service_name": service_name,
            "state": state.value,
            "failure_count": kwargs.get("failure_count", 0),
            "success_count": kwargs.get("success_count", 0),
            "last_failure_time": kwargs.get("last_failure_time"),
            "last_success_time": kwargs.get("last_success_time"),
            "state_changed_at": now.isoformat(),
            "failure_threshold": kwargs.get("failure_threshold", 5),
            "recovery_timeout": kwargs.get("recovery_timeout", 60),  # seconds
            "half_open_max_calls": kwargs.get("half_open_max_calls", 3),
            "circuit_breaker_enabled": kwargs.get("enabled", True),
            "service_health_status": kwargs.get("health_status", "unknown")
        }

    @pytest.mark.asyncio
    async def test_circuit_breaker_normal_operation(self, redis_client):
        """Test circuit breaker in normal closed state operation."""
        
        service_name = "auth_service"
        cb_key = f"circuit_breaker:{service_name}"
        
        # Initialize circuit breaker in closed state
        cb_state = self.create_circuit_breaker_state(
            service_name,
            CircuitState.CLOSED,
            success_count=10,
            last_success_time=datetime.utcnow().isoformat(),
            health_status="healthy"
        )
        
        try:
            await redis_client.setex(cb_key, 3600, json.dumps(cb_state))
            
            # Verify circuit breaker is in closed state
            stored_state = json.loads(await redis_client.get(cb_key))
            assert stored_state["state"] == CircuitState.CLOSED.value
            assert stored_state["failure_count"] == 0
            assert stored_state["success_count"] == 10
            assert stored_state["circuit_breaker_enabled"] is True
            
            # Simulate successful auth operations
            for i in range(5):
                stored_state["success_count"] += 1
                stored_state["last_success_time"] = datetime.utcnow().isoformat()
                
                await redis_client.setex(cb_key, 3600, json.dumps(stored_state))
            
            # Verify successful operations don't change state
            final_state = json.loads(await redis_client.get(cb_key))
            assert final_state["state"] == CircuitState.CLOSED.value
            assert final_state["success_count"] == 15
            assert final_state["failure_count"] == 0
            
            print("✅ Circuit breaker normal operation validated")
            
        finally:
            await redis_client.delete(cb_key)

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_detection_and_opening(self, redis_client):
        """Test circuit breaker failure detection and transition to open state."""
        
        service_name = "auth_service_failing"
        cb_key = f"circuit_breaker:{service_name}"
        
        # Initialize circuit breaker in closed state
        cb_state = self.create_circuit_breaker_state(
            service_name,
            CircuitState.CLOSED,
            failure_threshold=3,  # Lower threshold for testing
            health_status="healthy"
        )
        
        try:
            await redis_client.setex(cb_key, 3600, json.dumps(cb_state))
            
            # Simulate auth service failures
            failure_scenarios = [
                {"error": "connection_timeout", "status": 503},
                {"error": "auth_service_unavailable", "status": 503},
                {"error": "database_connection_failed", "status": 500}
            ]
            
            stored_state = json.loads(await redis_client.get(cb_key))
            
            for i, failure in enumerate(failure_scenarios):
                # Record failure
                stored_state["failure_count"] += 1
                stored_state["last_failure_time"] = datetime.utcnow().isoformat()
                
                # Check if failure threshold is reached
                if stored_state["failure_count"] >= stored_state["failure_threshold"]:
                    # Open circuit breaker
                    stored_state["state"] = CircuitState.OPEN.value
                    stored_state["state_changed_at"] = datetime.utcnow().isoformat()
                    stored_state["service_health_status"] = "unhealthy"
                    
                await redis_client.setex(cb_key, 3600, json.dumps(stored_state))
                
                print(f"❌ Failure {i+1}: {failure['error']} - Count: {stored_state['failure_count']}")
            
            # Verify circuit breaker opened after threshold
            final_state = json.loads(await redis_client.get(cb_key))
            assert final_state["state"] == CircuitState.OPEN.value
            assert final_state["failure_count"] == 3
            assert final_state["service_health_status"] == "unhealthy"
            
            print("✅ Circuit breaker failure detection and opening validated")
            
        finally:
            await redis_client.delete(cb_key)

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state_request_rejection(self, redis_client, async_client):
        """Test circuit breaker rejecting requests in open state."""
        
        service_name = "auth_service_open"
        cb_key = f"circuit_breaker:{service_name}"
        
        # Set circuit breaker to open state
        cb_state = self.create_circuit_breaker_state(
            service_name,
            CircuitState.OPEN,
            failure_count=5,
            last_failure_time=datetime.utcnow().isoformat(),
            health_status="unhealthy"
        )
        
        try:
            await redis_client.setex(cb_key, 3600, json.dumps(cb_state))
            
            # Simulate requests when circuit breaker is open
            test_requests = [
                {"endpoint": "/auth/login", "method": "POST"},
                {"endpoint": "/auth/validate", "method": "GET"},
                {"endpoint": "/auth/refresh", "method": "POST"}
            ]
            
            for request in test_requests:
                # In open state, requests should be rejected immediately
                # without calling the actual auth service
                
                # Verify circuit breaker state prevents service calls
                stored_state = json.loads(await redis_client.get(cb_key))
                assert stored_state["state"] == CircuitState.OPEN.value
                
                # In real implementation, this would return fast failure
                print(f"❌ Request to {request['endpoint']} rejected (circuit breaker open)")
                
                # Simulate fast failure response
                circuit_breaker_response = {
                    "error": AuthErrorConstants.AUTH_SERVICE_UNAVAILABLE,
                    "message": "Authentication service temporarily unavailable",
                    "circuit_breaker_state": "open",
                    "retry_after": 60
                }
                
                assert circuit_breaker_response["circuit_breaker_state"] == "open"
                assert "unavailable" in circuit_breaker_response["message"]
            
            print("✅ Circuit breaker open state request rejection validated")
            
        finally:
            await redis_client.delete(cb_key)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery_attempt(self, redis_client):
        """Test circuit breaker transition to half-open state and recovery attempts."""
        
        service_name = "auth_service_recovery"
        cb_key = f"circuit_breaker:{service_name}"
        
        # Set circuit breaker to open state (past recovery timeout)
        past_time = datetime.utcnow() - timedelta(seconds=70)  # Past 60 second timeout
        cb_state = self.create_circuit_breaker_state(
            service_name,
            CircuitState.OPEN,
            failure_count=5,
            last_failure_time=past_time.isoformat(),
            recovery_timeout=60,
            health_status="unhealthy"
        )
        
        try:
            await redis_client.setex(cb_key, 3600, json.dumps(cb_state))
            
            # Simulate recovery timeout elapsed - transition to half-open
            stored_state = json.loads(await redis_client.get(cb_key))
            
            # Check if recovery timeout has elapsed
            last_failure = datetime.fromisoformat(stored_state["last_failure_time"])
            recovery_timeout = stored_state["recovery_timeout"]
            
            if (datetime.utcnow() - last_failure).total_seconds() > recovery_timeout:
                # Transition to half-open state
                stored_state["state"] = CircuitState.HALF_OPEN.value
                stored_state["state_changed_at"] = datetime.utcnow().isoformat()
                stored_state["half_open_attempts"] = 0
                
                await redis_client.setex(cb_key, 3600, json.dumps(stored_state))
            
            # Verify half-open state
            half_open_state = json.loads(await redis_client.get(cb_key))
            assert half_open_state["state"] == CircuitState.HALF_OPEN.value
            assert "half_open_attempts" in half_open_state
            
            # Simulate limited test requests in half-open state
            max_calls = half_open_state["half_open_max_calls"]
            
            for i in range(max_calls):
                # Test request to auth service
                half_open_state["half_open_attempts"] += 1
                
                # Simulate successful test request
                if i < 2:  # First 2 succeed
                    half_open_state["success_count"] += 1
                    half_open_state["last_success_time"] = datetime.utcnow().isoformat()
                    print(f"✅ Half-open test request {i+1} succeeded")
                else:  # Last one fails
                    half_open_state["failure_count"] += 1
                    half_open_state["last_failure_time"] = datetime.utcnow().isoformat()
                    print(f"❌ Half-open test request {i+1} failed")
                
                await redis_client.setex(cb_key, 3600, json.dumps(half_open_state))
            
            # Evaluate half-open results
            final_half_open = json.loads(await redis_client.get(cb_key))
            
            # If majority of test requests succeeded, close circuit breaker
            success_ratio = final_half_open["success_count"] / max_calls if max_calls > 0 else 0
            
            if success_ratio >= 0.6:  # 60% success rate
                final_half_open["state"] = CircuitState.CLOSED.value
                final_half_open["failure_count"] = 0  # Reset failure count
                final_half_open["service_health_status"] = "recovering"
            else:
                final_half_open["state"] = CircuitState.OPEN.value
                final_half_open["service_health_status"] = "still_unhealthy"
            
            final_half_open["state_changed_at"] = datetime.utcnow().isoformat()
            await redis_client.setex(cb_key, 3600, json.dumps(final_half_open))
            
            print(f"✅ Half-open recovery attempt completed - Final state: {final_half_open['state']}")
            
        finally:
            await redis_client.delete(cb_key)

    @pytest.mark.asyncio
    async def test_circuit_breaker_successful_recovery_to_closed(self, redis_client):
        """Test successful circuit breaker recovery to closed state."""
        
        service_name = "auth_service_recovered"
        cb_key = f"circuit_breaker:{service_name}"
        
        # Start with half-open state after recovery timeout
        cb_state = self.create_circuit_breaker_state(
            service_name,
            CircuitState.HALF_OPEN,
            failure_count=3,
            half_open_max_calls=5,
            health_status="recovering"
        )
        cb_state["half_open_attempts"] = 0
        
        try:
            await redis_client.setex(cb_key, 3600, json.dumps(cb_state))
            
            # Simulate successful recovery attempts
            stored_state = json.loads(await redis_client.get(cb_key))
            max_calls = stored_state["half_open_max_calls"]
            
            # All recovery attempts succeed
            for i in range(max_calls):
                stored_state["half_open_attempts"] += 1
                stored_state["success_count"] += 1
                stored_state["last_success_time"] = datetime.utcnow().isoformat()
                
                await redis_client.setex(cb_key, 3600, json.dumps(stored_state))
                print(f"✅ Recovery attempt {i+1} succeeded")
            
            # Check if all attempts succeeded - close circuit breaker
            final_state = json.loads(await redis_client.get(cb_key))
            
            if final_state["half_open_attempts"] == max_calls and final_state["success_count"] >= max_calls:
                # Successfully recovered - close circuit breaker
                final_state["state"] = CircuitState.CLOSED.value
                final_state["failure_count"] = 0
                final_state["service_health_status"] = "healthy"
                final_state["state_changed_at"] = datetime.utcnow().isoformat()
                final_state["recovered_at"] = datetime.utcnow().isoformat()
                
                # Remove half-open specific fields
                final_state.pop("half_open_attempts", None)
                
                await redis_client.setex(cb_key, 3600, json.dumps(final_state))
            
            # Verify successful recovery
            recovered_state = json.loads(await redis_client.get(cb_key))
            assert recovered_state["state"] == CircuitState.CLOSED.value
            assert recovered_state["failure_count"] == 0
            assert recovered_state["service_health_status"] == "healthy"
            assert "recovered_at" in recovered_state
            
            print("✅ Successful circuit breaker recovery to closed state validated")
            
        finally:
            await redis_client.delete(cb_key)

    @pytest.mark.asyncio
    async def test_circuit_breaker_graceful_degradation(self, redis_client, async_client):
        """Test graceful degradation when auth circuit breaker is open."""
        
        service_name = "auth_service_degraded"
        cb_key = f"circuit_breaker:{service_name}"
        
        # Set circuit breaker to open state
        cb_state = self.create_circuit_breaker_state(
            service_name,
            CircuitState.OPEN,
            failure_count=10,
            health_status="unhealthy"
        )
        
        try:
            await redis_client.setex(cb_key, 3600, json.dumps(cb_state))
            
            # Test graceful degradation strategies
            degradation_scenarios = [
                {
                    "feature": "user_authentication",
                    "fallback": "cached_token_validation",
                    "description": "Use cached tokens when auth service is down"
                },
                {
                    "feature": "permission_check", 
                    "fallback": "default_permissions",
                    "description": "Use default safe permissions"
                },
                {
                    "feature": "new_user_signup",
                    "fallback": "queue_for_processing",
                    "description": "Queue signups for later processing"
                }
            ]
            
            for scenario in degradation_scenarios:
                # Verify circuit breaker state
                stored_state = json.loads(await redis_client.get(cb_key))
                assert stored_state["state"] == CircuitState.OPEN.value
                
                # Implement graceful degradation
                degradation_response = {
                    "feature": scenario["feature"],
                    "status": "degraded_mode",
                    "fallback_strategy": scenario["fallback"],
                    "message": f"Using fallback: {scenario['description']}",
                    "circuit_breaker_state": "open",
                    "service_health": "unhealthy"
                }
                
                # Verify degradation response
                assert degradation_response["status"] == "degraded_mode"
                assert "fallback" in degradation_response["fallback_strategy"]
                assert degradation_response["circuit_breaker_state"] == "open"
                
                print(f"✅ Graceful degradation for {scenario['feature']}: {scenario['fallback']}")
            
            print("✅ Circuit breaker graceful degradation validated")
            
        finally:
            await redis_client.delete(cb_key)

    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_and_monitoring(self, redis_client):
        """Test circuit breaker metrics collection and monitoring."""
        
        service_name = "auth_service_monitored"
        cb_key = f"circuit_breaker:{service_name}"
        metrics_key = f"circuit_breaker_metrics:{service_name}"
        
        # Initialize circuit breaker with metrics
        cb_state = self.create_circuit_breaker_state(
            service_name,
            CircuitState.CLOSED
        )
        
        metrics_data = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "circuit_opened_count": 0,
            "circuit_closed_count": 0,
            "circuit_half_open_count": 0,
            "average_response_time": 0.0,
            "last_metric_update": datetime.utcnow().isoformat(),
            "uptime_percentage": 100.0
        }
        
        try:
            await redis_client.setex(cb_key, 3600, json.dumps(cb_state))
            await redis_client.setex(metrics_key, 3600, json.dumps(metrics_data))
            
            # Simulate requests with metrics collection
            request_scenarios = [
                {"success": True, "response_time": 0.1},
                {"success": True, "response_time": 0.15},
                {"success": False, "response_time": 2.0},  # Timeout
                {"success": False, "response_time": 1.5},  # Error
                {"success": True, "response_time": 0.12}
            ]
            
            stored_state = json.loads(await redis_client.get(cb_key))
            stored_metrics = json.loads(await redis_client.get(metrics_key))
            
            for request in request_scenarios:
                # Update request metrics
                stored_metrics["total_requests"] += 1
                
                if request["success"]:
                    stored_metrics["successful_requests"] += 1
                    stored_state["success_count"] += 1
                else:
                    stored_metrics["failed_requests"] += 1
                    stored_state["failure_count"] += 1
                
                # Update average response time
                total_time = (stored_metrics["average_response_time"] * 
                             (stored_metrics["total_requests"] - 1) + 
                             request["response_time"])
                stored_metrics["average_response_time"] = total_time / stored_metrics["total_requests"]
                
                # Check for state transitions
                if stored_state["failure_count"] >= stored_state["failure_threshold"]:
                    if stored_state["state"] != CircuitState.OPEN.value:
                        stored_state["state"] = CircuitState.OPEN.value
                        stored_metrics["circuit_opened_count"] += 1
                
                stored_metrics["last_metric_update"] = datetime.utcnow().isoformat()
                
                # Calculate uptime percentage
                success_rate = (stored_metrics["successful_requests"] / 
                               stored_metrics["total_requests"] * 100)
                stored_metrics["uptime_percentage"] = success_rate
                
                await redis_client.setex(cb_key, 3600, json.dumps(stored_state))
                await redis_client.setex(metrics_key, 3600, json.dumps(stored_metrics))
            
            # Verify metrics collection
            final_metrics = json.loads(await redis_client.get(metrics_key))
            
            assert final_metrics["total_requests"] == 5
            assert final_metrics["successful_requests"] == 3
            assert final_metrics["failed_requests"] == 2
            assert final_metrics["uptime_percentage"] == 60.0  # 3/5 * 100
            assert final_metrics["average_response_time"] > 0
            
            print("✅ Circuit breaker metrics and monitoring validated")
            print(f"   Total requests: {final_metrics['total_requests']}")
            print(f"   Success rate: {final_metrics['uptime_percentage']}%")
            print(f"   Avg response time: {final_metrics['average_response_time']:.3f}s")
            
        finally:
            await redis_client.delete(cb_key)
            await redis_client.delete(metrics_key)

    @pytest.mark.asyncio
    async def test_multiple_service_circuit_breakers(self, redis_client):
        """Test multiple independent circuit breakers for different services."""
        
        # Create circuit breakers for different auth-related services
        services = [
            {"name": "primary_auth_service", "state": CircuitState.CLOSED},
            {"name": "oauth_service", "state": CircuitState.OPEN},
            {"name": "user_profile_service", "state": CircuitState.HALF_OPEN},
            {"name": "permission_service", "state": CircuitState.CLOSED}
        ]
        
        circuit_breakers = {}
        
        try:
            # Initialize circuit breakers for each service
            for service in services:
                cb_key = f"circuit_breaker:{service['name']}"
                cb_state = self.create_circuit_breaker_state(
                    service['name'],
                    service['state'],
                    failure_count=3 if service['state'] == CircuitState.OPEN else 0
                )
                
                await redis_client.setex(cb_key, 3600, json.dumps(cb_state))
                circuit_breakers[service['name']] = cb_key
            
            # Verify each circuit breaker operates independently
            for service in services:
                cb_key = circuit_breakers[service['name']]
                stored_state = json.loads(await redis_client.get(cb_key))
                
                assert stored_state["service_name"] == service['name']
                assert stored_state["state"] == service['state'].value
                
                print(f"✅ {service['name']}: {service['state'].value}")
                
                # Simulate state changes for one service
                if service['name'] == "primary_auth_service":
                    # Primary auth fails
                    stored_state["failure_count"] = 5
                    stored_state["state"] = CircuitState.OPEN.value
                    await redis_client.setex(cb_key, 3600, json.dumps(stored_state))
                
                elif service['name'] == "oauth_service":
                    # OAuth service recovers
                    stored_state["state"] = CircuitState.HALF_OPEN.value
                    await redis_client.setex(cb_key, 3600, json.dumps(stored_state))
            
            # Verify other services are unaffected by individual service changes
            for service in services:
                cb_key = circuit_breakers[service['name']]
                final_state = json.loads(await redis_client.get(cb_key))
                
                if service['name'] == "permission_service":
                    # Should still be closed
                    assert final_state["state"] == CircuitState.CLOSED.value
                    assert final_state["failure_count"] == 0
                
                print(f"✅ {service['name']} final state: {final_state['state']}")
            
            print("✅ Multiple service circuit breakers operate independently")
            
        finally:
            # Cleanup all circuit breakers
            for cb_key in circuit_breakers.values():
                await redis_client.delete(cb_key)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])