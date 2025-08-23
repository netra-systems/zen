"""Service Failure Recovery Core Components

Business Value Justification (BVJ):
1. Segment: Enterprise & Growth
2. Business Goal: System resilience and availability 
3. Value Impact: Prevents revenue loss from service failures
4. Revenue Impact: Protects $50K+ MRR through reliable recovery

Modular design for service failure recovery testing with state preservation.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from tests.e2e.service_orchestrator import E2EServiceOrchestrator
from test_framework.http_client import ClientConfig
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient

logger = logging.getLogger(__name__)


class AuthServiceFailureSimulator:
    """Simulates Auth service failures for recovery testing."""
    
    def __init__(self, orchestrator: E2EServiceOrchestrator):
        """Initialize Auth failure simulator."""
        self.orchestrator = orchestrator
        self.failed_services = []
        self.original_states = {}
    
    async def simulate_auth_failure(self) -> bool:
        """Simulate Auth service failure."""
        try:
            auth_service = await self._get_auth_service()
            if not self._can_terminate_service(auth_service):
                return False
            return await self._terminate_auth_service(auth_service)
        except Exception as e:
            logger.error(f"Auth failure simulation error: {e}")
            return False
    
    async def _get_auth_service(self):
        """Get Auth service from orchestrator."""
        services = self.orchestrator.services_manager.services
        return services.get("auth")
    
    def _can_terminate_service(self, service) -> bool:
        """Check if service can be terminated."""
        return service and hasattr(service, 'process') and service.process
    
    async def _terminate_auth_service(self, auth_service) -> bool:
        """Terminate Auth service process."""
        auth_service.process.terminate()
        await asyncio.sleep(1)
        self.failed_services.append("auth")
        return True
    
    async def restore_auth_service(self) -> bool:
        """Restore Auth service after failure."""
        try:
            await self.orchestrator.services_manager._start_auth_service()
            if "auth" in self.failed_services:
                self.failed_services.remove("auth")
            await self._wait_for_auth_stabilization()
            return True
        except Exception as e:
            logger.error(f"Auth restoration error: {e}")
            return False
    
    async def _wait_for_auth_stabilization(self) -> None:
        """Wait for Auth service to stabilize."""
        await asyncio.sleep(3)  # Allow service startup


class GracefulDegradationTester:
    """Tests system graceful degradation during service failures."""
    
    def __init__(self):
        """Initialize degradation tester."""
        self.degradation_results = {}
        self.user_state_cache = {}
    
    async def test_backend_degradation(self, orchestrator: E2EServiceOrchestrator) -> Dict[str, Any]:
        """Test backend degrades gracefully without Auth."""
        try:
            backend_url = orchestrator.get_service_url("backend")
            response = await self._check_backend_health_degraded(backend_url)
            return self._analyze_backend_degradation(response)
        except Exception as e:
            return {"degraded_properly": False, "error": str(e)}
    
    async def _check_backend_health_degraded(self, backend_url: str):
        """Check backend health during Auth failure."""
        import httpx
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            return await client.get(f"{backend_url}/health")
    
    def _analyze_backend_degradation(self, response) -> Dict[str, Any]:
        """Analyze backend degradation response."""
        return {
            "degraded_properly": response.status_code in [200, 503],
            "response_code": response.status_code,
            "graceful": True
        }
    
    async def test_frontend_error_handling(self, ws_client: RealWebSocketClient) -> Dict[str, Any]:
        """Test frontend handles Auth failure gracefully."""
        try:
            await self._send_auth_required_request(ws_client)
            error_response = await self._wait_for_auth_error(ws_client)
            return self._evaluate_frontend_handling(error_response)
        except asyncio.TimeoutError:
            return {"handled_gracefully": False, "timeout": True}
    
    async def _send_auth_required_request(self, ws_client: RealWebSocketClient) -> None:
        """Send request requiring authentication."""
        auth_request = {"type": "auth_required", "content": "test request"}
        await ws_client.send_json(auth_request)
    
    async def _wait_for_auth_error(self, ws_client: RealWebSocketClient) -> Dict[str, Any]:
        """Wait for authentication error response."""
        return await asyncio.wait_for(ws_client.receive_json(), timeout=5.0)
    
    def _evaluate_frontend_handling(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate frontend error handling quality."""
        return {
            "handled_gracefully": response.get("type") == "auth_error",
            "user_friendly": "authentication" in response.get("message", "").lower(),
            "retry_available": response.get("retry_available", False)
        }


class StatePreservationValidator:
    """Validates state preservation during and after recovery."""
    
    def __init__(self):
        """Initialize state preservation validator."""
        self.pre_failure_state = {}
        self.post_recovery_state = {}
        self.state_keys = ["user_session", "conversation_history", "preferences"]
    
    async def capture_pre_failure_state(self, ws_client: RealWebSocketClient) -> bool:
        """Capture system state before failure."""
        try:
            for state_key in self.state_keys:
                state_value = await self._query_state(ws_client, state_key)
                self.pre_failure_state[state_key] = state_value
            return True
        except Exception as e:
            logger.error(f"State capture error: {e}")
            return False
    
    async def _query_state(self, ws_client: RealWebSocketClient, state_key: str) -> Any:
        """Query specific state from system."""
        query = {"type": "state_query", "key": state_key}
        await ws_client.send_json(query)
        response = await asyncio.wait_for(ws_client.receive_json(), timeout=5.0)
        return response.get("value")
    
    async def validate_post_recovery_state(self, ws_client: RealWebSocketClient) -> Dict[str, Any]:
        """Validate state after recovery."""
        try:
            await self._capture_post_recovery_state(ws_client)
            return self._compare_states()
        except Exception as e:
            return {"state_preserved": False, "error": str(e)}
    
    async def _capture_post_recovery_state(self, ws_client: RealWebSocketClient) -> None:
        """Capture system state after recovery."""
        for state_key in self.state_keys:
            state_value = await self._query_state(ws_client, state_key)
            self.post_recovery_state[state_key] = state_value
    
    def _compare_states(self) -> Dict[str, Any]:
        """Compare pre-failure and post-recovery states."""
        preserved_count = 0
        total_count = len(self.state_keys)
        
        for key in self.state_keys:
            pre_val = self.pre_failure_state.get(key)
            post_val = self.post_recovery_state.get(key)
            if pre_val == post_val:
                preserved_count += 1
        
        preservation_rate = preserved_count / total_count if total_count > 0 else 0
        return {
            "state_preserved": preservation_rate >= 0.8,
            "preservation_rate": preservation_rate,
            "preserved_states": preserved_count,
            "total_states": total_count
        }


class RecoveryTimeValidator:
    """Validates recovery completes within time limits."""
    
    def __init__(self, max_recovery_time: float = 30.0):
        """Initialize recovery time validator."""
        self.max_recovery_time = max_recovery_time
        self.failure_start_time = None
        self.recovery_complete_time = None
    
    def start_failure_timer(self) -> None:
        """Start timing the failure recovery process."""
        self.failure_start_time = time.time()
    
    async def validate_recovery_complete(self, ws_client: RealWebSocketClient) -> Dict[str, Any]:
        """Validate recovery is complete and within time limit."""
        try:
            recovery_successful = await self._test_system_responsiveness(ws_client)
            self.recovery_complete_time = time.time()
            return self._analyze_recovery_timing(recovery_successful)
        except Exception as e:
            return {"recovery_within_limit": False, "error": str(e)}
    
    async def _test_system_responsiveness(self, ws_client: RealWebSocketClient) -> bool:
        """Test if system is responsive after recovery."""
        test_message = {"type": "health_check", "content": "recovery test"}
        await ws_client.send_json(test_message)
        response = await asyncio.wait_for(ws_client.receive_json(), timeout=10.0)
        return response.get("type") == "health_ok"
    
    def _analyze_recovery_timing(self, recovery_successful: bool) -> Dict[str, Any]:
        """Analyze recovery timing results."""
        if not self.failure_start_time:
            return {"recovery_within_limit": False, "error": "Timer not started"}
        
        recovery_time = self.recovery_complete_time - self.failure_start_time
        return {
            "recovery_within_limit": recovery_time <= self.max_recovery_time,
            "recovery_time": recovery_time,
            "recovery_successful": recovery_successful,
            "max_allowed_time": self.max_recovery_time
        }


def create_auth_failure_simulator(orchestrator: E2EServiceOrchestrator) -> AuthServiceFailureSimulator:
    """Create Auth service failure simulator instance."""
    return AuthServiceFailureSimulator(orchestrator)


def create_degradation_tester() -> GracefulDegradationTester:
    """Create graceful degradation tester instance."""
    return GracefulDegradationTester()


def create_state_preservation_validator() -> StatePreservationValidator:
    """Create state preservation validator instance."""
    return StatePreservationValidator()


def create_recovery_time_validator(max_time: float = 30.0) -> RecoveryTimeValidator:
    """Create recovery time validator instance."""
    return RecoveryTimeValidator(max_time)
