"""Test Suite 9: Error Isolation Basic

Business Value: $45K+ MRR protection through service isolation
Tests basic error isolation between microservices with <5s recovery.
Ensures graceful degradation and automatic recovery.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.clients.factory import TestClientFactory
from tests.e2e.error_cascade_core import (
    AutoRecoveryVerifier,
    GracefulDegradationValidator,
    ServiceFailureSimulator,
)
from tests.e2e.service_orchestrator import E2EServiceOrchestrator
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient

logger = logging.getLogger(__name__)


class ErrorIsolationerTests:
    """Core error isolation testing functionality."""
    
    def __init__(self):
        """Initialize error isolation tester."""
        self.orchestrator = None
        self.client_factory = None
        self.failure_simulator = None
        self.degradation_validator = None
        self.recovery_verifier = None
    
    async def setup_test_environment(self) -> None:
        """Setup test environment for error isolation."""
        self.orchestrator = E2EServiceOrchestrator()
        await self.orchestrator.start_test_environment("error_isolation_test")
        
        self.client_factory = TestClientFactory()
        self.failure_simulator = ServiceFailureSimulator(self.orchestrator)
        self.degradation_validator = GracefulDegradationValidator()
        self.recovery_verifier = AutoRecoveryVerifier()
    
    @pytest.mark.e2e
    async def test_cleanup_test_environment(self) -> None:
        """Cleanup test environment."""
        if self.client_factory:
            await self.client_factory.cleanup()
        if self.orchestrator:
            await self.orchestrator.shutdown()


@pytest.fixture
async def error_tester():
    """Fixture providing error isolation tester."""
    tester = ErrorIsolationTester()
    await tester.setup_test_environment()
    yield tester
    await tester.cleanup_test_environment()


@pytest.mark.e2e
async def test_auth_service_failure_isolation(error_tester):
    """Test 1: Backend continues when Auth service fails."""
    # Get backend client without auth dependency
    backend_client = await error_tester.client_factory.create_backend_client()
    
    # Kill auth service
    auth_service = error_tester.orchestrator.get_service("auth")
    if auth_service and auth_service.process:
        auth_service.process.terminate()
        await asyncio.sleep(1)
    
    # Verify backend health check still works
    health_response = await backend_client.get("/health")
    assert health_response.status_code == 200
    
    # Restart auth service for cleanup
    await error_tester.orchestrator.services_manager._start_auth_service()


@pytest.mark.e2e
async def test_backend_service_failure_isolation(error_tester):
    """Test 2: Auth/Frontend continue when Backend fails."""
    # Get auth client
    auth_client = await error_tester.client_factory.create_auth_client()
    
    # Kill backend service
    killed = await error_tester.failure_simulator.kill_backend_service()
    assert killed, "Backend service should be killable"
    
    # Verify auth service remains responsive
    health_response = await auth_client.get("/health")
    assert health_response.status_code == 200
    
    # Restart backend for cleanup
    await error_tester.failure_simulator.restart_backend_service()


@pytest.mark.e2e
async def test_websocket_failure_isolation(error_tester):
    """Test 3: Other services continue when WebSocket fails."""
    # Create auth and backend clients
    auth_client = await error_tester.client_factory.create_auth_client()
    backend_client = await error_tester.client_factory.create_backend_client()
    
    # Create WebSocket client and force disconnect
    ws_client = await error_tester.client_factory.create_websocket_client("test_token")
    try:
        await ws_client.connect()
        await ws_client.close()  # Simulate WebSocket failure
    except Exception:
        pass  # Expected - WebSocket failure
    
    # Verify other services remain operational
    auth_health = await auth_client.get("/health")
    backend_health = await backend_client.get("/health")
    
    assert auth_health.status_code == 200
    assert backend_health.status_code == 200


@pytest.mark.e2e
async def test_error_message_propagation(error_tester):
    """Test 4: Appropriate errors shown to users."""
    # Create authenticated WebSocket client
    ws_client = await error_tester.client_factory.create_authenticated_websocket_client()
    
    # Kill backend service
    await error_tester.failure_simulator.kill_backend_service()
    
    # Validate frontend error handling
    error_result = await error_tester.degradation_validator.validate_frontend_error_handling(ws_client)
    
    # Should show graceful error message
    assert error_result.get("error_handled", False), "Error should be handled gracefully"
    
    # Cleanup
    await error_tester.failure_simulator.restart_backend_service()
    await ws_client.close()


@pytest.mark.e2e
async def test_automatic_recovery(error_tester):
    """Test 5: Services reconnect when dependencies recover."""
    # Create WebSocket client
    ws_client = await error_tester.client_factory.create_authenticated_websocket_client()
    
    # Kill and restart backend service
    await error_tester.failure_simulator.kill_backend_service()
    await asyncio.sleep(2)  # Wait for failure recognition
    await error_tester.failure_simulator.restart_backend_service()
    
    # Test recovery
    await error_tester.recovery_verifier.initiate_recovery_test(ws_client)
    recovery_result = await error_tester.recovery_verifier.verify_chat_continuity(ws_client)
    
    # Should recover within 5 seconds
    assert recovery_result.get("recovery_time", 10) < 5.0, "Recovery should be under 5 seconds"
    assert recovery_result.get("chat_restored", False), "Chat should be restored"
    
    await ws_client.close()


@pytest.mark.e2e
async def test_circuit_breaker_behavior(error_tester):
    """Test 6: Prevent cascade failures."""
    # Create clients for all services
    auth_client = await error_tester.client_factory.create_auth_client()
    backend_client = await error_tester.client_factory.create_backend_client()
    
    # Kill backend service
    await error_tester.failure_simulator.kill_backend_service()
    
    # Verify auth service isolation
    auth_stability = await error_tester.degradation_validator.check_auth_service_stability(
        error_tester.orchestrator
    )
    
    assert auth_stability.get("auth_responsive", False), "Auth should remain responsive"
    assert auth_stability.get("isolation_maintained", False), "Isolation should be maintained"
    
    # Cleanup
    await error_tester.failure_simulator.restart_backend_service()


@pytest.mark.e2e
async def test_performance_during_failure(error_tester):
    """Test 7: Degraded but functional performance."""
    # Measure baseline performance
    auth_client = await error_tester.client_factory.create_auth_client()
    
    start_time = time.time()
    health_response = await auth_client.get("/health")
    baseline_time = time.time() - start_time
    
    # Kill backend service
    await error_tester.failure_simulator.kill_backend_service()
    
    # Measure degraded performance
    start_time = time.time()
    degraded_response = await auth_client.get("/health")
    degraded_time = time.time() - start_time
    
    # Should still be responsive (< 5 seconds)
    assert degraded_response.status_code == 200
    assert degraded_time < 5.0, "Degraded performance should be under 5 seconds"
    
    # Cleanup
    await error_tester.failure_simulator.restart_backend_service()


# Additional helper functions for service health verification

async def verify_service_health(client, service_name: str) -> Dict[str, Any]:
    """Verify service health and return metrics."""
    try:
        start_time = time.time()
        response = await client.get("/health")
        response_time = time.time() - start_time
        
        return {
            "responsive": response.status_code == 200,
            "response_time": response_time,
            "service": service_name
        }
    except Exception as e:
        return {
            "responsive": False,
            "error": str(e),
            "service": service_name
        }


async def simulate_user_interaction(ws_client: RealWebSocketClient, message: str) -> Optional[Dict[str, Any]]:
    """Simulate user interaction during service failure."""
    try:
        await ws_client.send_json({"type": "chat", "content": message})
        response = await asyncio.wait_for(ws_client.receive_json(), timeout=3.0)
        return response
    except asyncio.TimeoutError:
        return {"type": "timeout", "message": "Service unavailable"}
    except Exception as e:
        return {"type": "error", "message": str(e)}


def assert_recovery_metrics(recovery_result: Dict[str, Any]) -> None:
    """Assert recovery meets performance requirements."""
    recovery_time = recovery_result.get("recovery_time", float('inf'))
    assert recovery_time < 5.0, f"Recovery time {recovery_time}s exceeds 5s target"
    
    chat_restored = recovery_result.get("chat_restored", False)
    assert chat_restored, "Chat functionality should be restored after recovery"


def assert_isolation_maintained(auth_result: Dict[str, Any], backend_killed: bool) -> None:
    """Assert service isolation is maintained during failures."""
    if backend_killed:
        assert auth_result.get("auth_responsive", False), "Auth should remain responsive when backend fails"
        assert auth_result.get("isolation_maintained", False), "Service isolation should be maintained"
