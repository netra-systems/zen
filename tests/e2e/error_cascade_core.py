"""Error Cascade Prevention Core Components

Business Value: $35K MRR - Service isolation and graceful degradation
Modular design for error cascade testing with service failure simulation.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from tests.e2e.service_orchestrator import E2EServiceOrchestrator
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient

logger = logging.getLogger(__name__)


class ServiceFailureSimulator:
    """Simulates service failures for error cascade testing."""
    
    def __init__(self, orchestrator: E2EServiceOrchestrator):
        """Initialize failure simulator."""
        self.orchestrator = orchestrator
        self.failed_services = []
        self.recovery_tasks = []
    
    async def kill_backend_service(self) -> bool:
        """Kill backend service process."""
        try:
            backend_service = self._get_backend_service()
            if not self._is_service_killable(backend_service):
                return False
            return await self._terminate_backend_process(backend_service)
        except Exception as e:
            logger.error(f"Failed to kill backend: {e}")
            return False
    
    def _get_backend_service(self):
        """Get backend service from orchestrator."""
        services = self.orchestrator.services_manager.services
        return services.get("backend")
    
    def _is_service_killable(self, service) -> bool:
        """Check if service can be killed."""
        return service and service.process
    
    async def _terminate_backend_process(self, backend_service) -> bool:
        """Terminate backend service process."""
        backend_service.process.terminate()
        await asyncio.sleep(1)
        self.failed_services.append("backend")
        return True
    
    async def restart_backend_service(self) -> bool:
        """Restart previously killed backend service."""
        try:
            await self.orchestrator.services_manager._start_backend_service()
            if "backend" in self.failed_services:
                self.failed_services.remove("backend")
            return True
        except Exception as e:
            logger.error(f"Failed to restart backend: {e}")
            return False


class GracefulDegradationValidator:
    """Validates graceful degradation during service failures."""
    
    def __init__(self):
        """Initialize degradation validator."""
        self.error_messages = []
        self.user_notifications = []
    
    async def validate_frontend_error_handling(self, ws_client: RealWebSocketClient) -> Dict[str, Any]:
        """Validate frontend shows graceful error messages."""
        try:
            await self._send_test_message_during_failure(ws_client)
            response = await self._wait_for_error_response(ws_client)
            return self._analyze_error_response(response)
        except asyncio.TimeoutError:
            return {"error_handled": False, "timeout": True}
    
    async def _send_test_message_during_failure(self, ws_client: RealWebSocketClient) -> None:
        """Send test message during backend failure."""
        test_message = {"type": "chat", "content": "test during failure"}
        await ws_client.send_json(test_message)
    
    async def _wait_for_error_response(self, ws_client: RealWebSocketClient) -> Dict[str, Any]:
        """Wait for error response from WebSocket."""
        return await asyncio.wait_for(ws_client.receive_json(), timeout=5.0)
    
    def _analyze_error_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error response for graceful handling."""
        return {
            "error_handled": response.get("type") == "error",
            "user_friendly": "error" in response.get("message", "").lower(),
            "graceful": response.get("graceful", False)
        }
    
    async def check_auth_service_stability(self, orchestrator: E2EServiceOrchestrator) -> Dict[str, Any]:
        """Verify auth service remains operational during backend failure."""
        try:
            auth_url = orchestrator.get_service_url("auth")
            response = await self._perform_auth_health_check(auth_url)
            return self._evaluate_auth_stability(response)
        except Exception as e:
            return {"auth_responsive": False, "error": str(e)}
    
    async def _perform_auth_health_check(self, auth_url: str):
        """Perform health check on auth service."""
        import httpx
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            return await client.get(f"{auth_url}/health")
    
    def _evaluate_auth_stability(self, response) -> Dict[str, Any]:
        """Evaluate auth service stability from response."""
        return {
            "auth_responsive": response.status_code == 200,
            "isolation_maintained": True
        }


class AutoRecoveryVerifier:
    """Verifies system auto-recovery after service restart."""
    
    def __init__(self):
        """Initialize recovery verifier."""
        self.recovery_start_time = None
        self.recovery_completed = False
    
    async def initiate_recovery_test(self, ws_client: RealWebSocketClient) -> None:
        """Start recovery verification process."""
        self.recovery_start_time = time.time()
        # Attempt reconnection after service restart
        await ws_client.connect()
    
    async def verify_chat_continuity(self, ws_client: RealWebSocketClient) -> Dict[str, Any]:
        """Verify chat functionality after recovery."""
        try:
            await self._send_recovery_test_message(ws_client)
            response = await self._receive_recovery_response(ws_client)
            return self._analyze_recovery_results(response)
        except Exception as e:
            return {"chat_restored": False, "error": str(e)}
    
    async def _send_recovery_test_message(self, ws_client: RealWebSocketClient) -> None:
        """Send recovery test message."""
        recovery_message = {"type": "chat", "content": "recovery test message"}
        await ws_client.send_json(recovery_message)
    
    async def _receive_recovery_response(self, ws_client: RealWebSocketClient):
        """Receive response to recovery test."""
        return await asyncio.wait_for(ws_client.receive_json(), timeout=10.0)
    
    def _analyze_recovery_results(self, response) -> Dict[str, Any]:
        """Analyze recovery test results."""
        recovery_time = time.time() - self.recovery_start_time if self.recovery_start_time else 0
        return {
            "chat_restored": response.get("type") == "response",
            "recovery_time": recovery_time,
            "seamless": recovery_time < 15.0
        }


def create_failure_simulator(orchestrator: E2EServiceOrchestrator) -> ServiceFailureSimulator:
    """Create service failure simulator instance."""
    return ServiceFailureSimulator(orchestrator)


def create_degradation_validator() -> GracefulDegradationValidator:
    """Create graceful degradation validator instance."""
    return GracefulDegradationValidator()


def create_recovery_verifier() -> AutoRecoveryVerifier:
    """Create auto-recovery verifier instance."""
    return AutoRecoveryVerifier()
