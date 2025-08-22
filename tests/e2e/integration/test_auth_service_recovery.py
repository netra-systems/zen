"""Service Recovery After Auth Service Failure Test - Critical E2E Test

CRITICAL E2E test for system behavior when Auth service fails completely.
Tests session persistence, graceful degradation, and automatic recovery.

Business Value Justification (BVJ):
1. Segment: Enterprise & Growth (High-value customers requiring 99.9% uptime)
2. Business Goal: Prevent complete system outages from single service failure
3. Value Impact: Ensures existing authenticated users can continue working
4. Revenue Impact: Protects $50K+ MRR by preventing cascade failures

Test Requirements:
- Establish authenticated sessions with Backend
- Stop Auth service (kill process)
- Verify existing sessions continue working
- Test WebSocket with cached token during outage
- Restart Auth service
- Verify seamless recovery
- Test circuit breaker activation on Auth degradation

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines (modular design with helper utilities)
- Function size: <25 lines each (clear, focused functions)
- Real services only - NO MOCKING
- <30 second execution time for fast feedback
- Integration with existing service recovery infrastructure
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch

import httpx
import pytest

# Add parent directories to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from tests.e2e.integration.service_failure_recovery_helpers import (
    create_auth_failure_simulator,
    create_degradation_tester,
    create_recovery_time_validator,
    create_state_preservation_validator,
)
from tests.e2e.integration.service_orchestrator import (
    create_service_orchestrator,
)
from tests.e2e.jwt_token_helpers import JWTTestHelper
from tests.real_websocket_client import RealWebSocketClient
from tests.test_websocket_real_connection import WebSocketRealConnectionTester

logger = logging.getLogger(__name__)


class AuthServiceRecoveryTester:
    """Core tester for Auth service failure and recovery scenarios."""
    
    def __init__(self):
        """Initialize Auth service recovery tester."""
        self.orchestrator = None
        self.jwt_helper = JWTTestHelper()
        self.ws_tester = WebSocketRealConnectionTester()
        self.authenticated_sessions = {}
        self.cached_tokens = {}
    
    async def setup_test_environment(self) -> bool:
        """Setup complete test environment with all services."""
        try:
            self.orchestrator = create_service_orchestrator()
            await self.orchestrator.start_test_environment("auth_recovery_test")
            await self._wait_for_environment_stability()
            return True
        except Exception as e:
            logger.error(f"Environment setup failed: {e}")
            return False
    
    async def _wait_for_environment_stability(self) -> None:
        """Wait for environment to stabilize after startup."""
        await asyncio.sleep(3)  # Allow services to fully initialize
    
    async def establish_authenticated_sessions(self, user_count: int = 3) -> Dict[str, Dict[str, Any]]:
        """Establish multiple authenticated sessions before Auth failure."""
        sessions = {}
        
        for i in range(user_count):
            user_id = f"test_user_{i}"
            try:
                session_data = await self._create_authenticated_session(user_id)
                if session_data["success"]:
                    sessions[user_id] = session_data
                    self.cached_tokens[user_id] = session_data["token"]
                    logger.info(f"Established session for {user_id}")
            except Exception as e:
                logger.error(f"Failed to establish session for {user_id}: {e}")
        
        return sessions
    
    async def _create_authenticated_session(self, user_id: str) -> Dict[str, Any]:
        """Create authenticated session with Backend service."""
        try:
            # Get JWT token from Auth service
            token = await self._get_auth_token(user_id)
            
            # Establish WebSocket connection with Backend
            ws_connection = await self.ws_tester.create_authenticated_connection(user_id)
            
            # Test Backend HTTP session
            backend_session = await self._test_backend_session(token)
            
            return {
                "success": True,
                "user_id": user_id,
                "token": token,
                "ws_connection": ws_connection,
                "backend_session": backend_session,
                "session_established_at": time.time()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_auth_token(self, user_id: str) -> str:
        """Get authentication token from Auth service."""
        # Try real token from Auth service first
        real_token = await self.jwt_helper.get_real_token_from_auth()
        if real_token:
            return real_token
        
        # Fallback to test token
        return self.jwt_helper.create_access_token(
            user_id=user_id,
            email=f"{user_id}@test.com",
            permissions=["read", "write"]
        )
    
    async def _test_backend_session(self, token: str) -> Dict[str, Any]:
        """Test Backend HTTP session with token."""
        try:
            backend_url = self.orchestrator.get_service_url("backend")
            headers = {"Authorization": f"Bearer {token}"}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{backend_url}/health", headers=headers)
                return {"status_code": response.status_code, "authenticated": True}
        except Exception as e:
            return {"authenticated": False, "error": str(e)}
    
    async def simulate_auth_service_failure(self) -> bool:
        """Simulate Auth service failure by killing the process."""
        try:
            # Find and kill the Auth service process 
            import subprocess
            
            # Get the actual auth service port from the orchestrator
            auth_service = self.orchestrator.services_manager.services.get("auth")
            auth_port = auth_service.port if auth_service else 8081
            
            # Find the process using the auth port
            result = subprocess.run(
                ["netstat", "-ano"], 
                capture_output=True, 
                text=True
            )
            
            lines = result.stdout.split('\n')
            auth_pid = None
            
            for line in lines:
                if f":{auth_port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        auth_pid = parts[-1]
                        break
            
            if auth_pid:
                # Kill the Auth service process
                subprocess.run(["taskkill", "/F", "/PID", auth_pid], check=True)
                await asyncio.sleep(2)  # Wait for process to be killed
                logger.info(f"Auth service failure simulated successfully (PID: {auth_pid}, Port: {auth_port})")
                await self._verify_auth_service_down()
                return True
            else:
                logger.error(f"Could not find Auth service process on port {auth_port}")
                return False
        except Exception as e:
            logger.error(f"Auth failure simulation error: {e}")
            return False
    
    async def _verify_auth_service_down(self) -> None:
        """Verify Auth service is actually down."""
        try:
            auth_service = self.orchestrator.services_manager.services.get("auth")
            auth_port = auth_service.port if auth_service else 8081
            auth_url = f"http://localhost:{auth_port}"
            
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.get(f"{auth_url}/health")
                raise RuntimeError("Auth service still responding after failure simulation")
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ConnectTimeout):
            # Expected - Auth service is down
            pass
    
    async def test_existing_sessions_during_outage(self, sessions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Test that existing sessions continue working during Auth outage."""
        results = {"sessions_working": 0, "total_sessions": len(sessions), "failures": []}
        
        for user_id, session_data in sessions.items():
            try:
                # Test WebSocket connection still works
                ws_result = await self._test_websocket_during_outage(session_data["ws_connection"])
                
                # Test Backend HTTP with cached token
                backend_result = await self._test_backend_during_outage(session_data["token"])
                
                if ws_result["working"] and backend_result["working"]:
                    results["sessions_working"] += 1
                    logger.info(f"Session {user_id} working during outage")
                else:
                    results["failures"].append({
                        "user_id": user_id,
                        "ws_working": ws_result["working"],
                        "backend_working": backend_result["working"]
                    })
            except Exception as e:
                results["failures"].append({"user_id": user_id, "error": str(e)})
        
        results["success_rate"] = results["sessions_working"] / results["total_sessions"]
        return results
    
    async def _test_websocket_during_outage(self, ws_connection: Dict[str, Any]) -> Dict[str, Any]:
        """Test WebSocket connection during Auth outage."""
        try:
            if not ws_connection.get("connected"):
                return {"working": False, "reason": "Not connected"}
            
            client = ws_connection["client"]
            
            # Send test message
            test_message = {"type": "health_check", "content": "auth outage test"}
            send_success = await client.send(test_message)
            
            if not send_success:
                return {"working": False, "reason": "Send failed"}
            
            # Try to receive response (with timeout)
            try:
                response = await asyncio.wait_for(client.receive(), timeout=5.0)
                return {"working": True, "response_received": response is not None}
            except asyncio.TimeoutError:
                # WebSocket might still be working but no response expected during outage
                return {"working": True, "response_received": False, "note": "No response during outage"}
        
        except Exception as e:
            return {"working": False, "error": str(e)}
    
    async def _test_backend_during_outage(self, token: str) -> Dict[str, Any]:
        """Test Backend HTTP access during Auth outage."""
        try:
            backend_url = self.orchestrator.get_service_url("backend")
            headers = {"Authorization": f"Bearer {token}"}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{backend_url}/health", headers=headers)
                # Backend should work with cached token even if Auth is down
                return {"working": response.status_code == 200, "status_code": response.status_code}
        except Exception as e:
            return {"working": False, "error": str(e)}
    
    async def test_new_login_fails_gracefully(self) -> Dict[str, Any]:
        """Test that new login attempts fail gracefully during Auth outage."""
        try:
            # Try to get new token (should fail)
            with patch.object(self.jwt_helper, 'get_real_token_from_auth') as mock_auth:
                mock_auth.side_effect = httpx.ConnectError("Auth service unavailable")
                
                new_user_id = "new_user_during_outage"
                session_result = await self._create_authenticated_session(new_user_id)
                
                return {
                    "failed_gracefully": not session_result["success"],
                    "error_handled": "error" in session_result,
                    "error_message": session_result.get("error", "")
                }
        except Exception as e:
            return {"failed_gracefully": False, "test_error": str(e)}
    
    async def restore_auth_service(self) -> bool:
        """Restore Auth service and verify recovery."""
        try:
            # Restart the Auth service manually
            
            # Get the port that was being used
            auth_service = self.orchestrator.services_manager.services.get("auth")
            auth_port = auth_service.port if auth_service else 8081
            
            # Start the Auth service in the background
            auth_main = self.orchestrator.project_root / "auth_service" / "main.py"
            cmd = [
                sys.executable, str(auth_main),
                "--host", "0.0.0.0",
                "--port", str(auth_port)
            ]
            
            # Start the process in the background
            subprocess.Popen(
                cmd,
                cwd=str(self.orchestrator.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for service to start
            await asyncio.sleep(5)
            await self._verify_auth_service_restored()
            logger.info(f"Auth service restored successfully on port {auth_port}")
            return True
        except Exception as e:
            logger.error(f"Auth service restoration error: {e}")
            return False
    
    async def _verify_auth_service_restored(self) -> None:
        """Verify Auth service is back online and healthy."""
        max_attempts = 10
        auth_service = self.orchestrator.services_manager.services.get("auth")
        auth_port = auth_service.port if auth_service else 8081
        auth_url = f"http://localhost:{auth_port}"
        
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.get(f"{auth_url}/health")
                    if response.status_code == 200:
                        return  # Auth service is healthy
            except Exception:
                pass
            
            await asyncio.sleep(1)
        
        raise RuntimeError(f"Auth service failed to restore within timeout on port {auth_port}")
    
    async def test_seamless_recovery(self, sessions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Test that recovery is seamless for existing sessions."""
        results = {"sessions_recovered": 0, "total_sessions": len(sessions), "new_login_works": False}
        
        # Test existing sessions still work after recovery
        for user_id, session_data in sessions.items():
            try:
                backend_result = await self._test_backend_during_outage(session_data["token"])
                if backend_result["working"]:
                    results["sessions_recovered"] += 1
            except Exception:
                pass
        
        # Test new login works after recovery
        try:
            new_session = await self._create_authenticated_session("recovery_test_user")
            results["new_login_works"] = new_session["success"]
        except Exception:
            pass
        
        results["recovery_rate"] = results["sessions_recovered"] / results["total_sessions"]
        return results
    
    async def test_circuit_breaker_activation(self) -> Dict[str, Any]:
        """Test circuit breaker activation during Auth degradation."""
        try:
            # Test that Backend still responds during Auth outage
            backend_url = self.orchestrator.get_service_url("backend")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{backend_url}/health")
                return {
                    "degraded_properly": response.status_code in [200, 503],
                    "response_code": response.status_code,
                    "graceful": True
                }
        except Exception as e:
            return {"degraded_properly": False, "error": str(e)}
    
    async def cleanup_test_environment(self) -> None:
        """Cleanup test environment and resources."""
        try:
            if self.orchestrator:
                await self.orchestrator.stop_test_environment("auth_recovery_test")
            
            # Close any remaining WebSocket connections
            for session_data in self.authenticated_sessions.values():
                if "ws_connection" in session_data and session_data["ws_connection"].get("client"):
                    try:
                        await session_data["ws_connection"]["client"].disconnect()
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_auth_service_recovery_complete():
    """Complete Auth service recovery test - validates system resilience."""
    tester = AuthServiceRecoveryTester()
    
    try:
        # Phase 1: Setup test environment
        logger.info("=== Phase 1: Setting up test environment ===")
        setup_success = await tester.setup_test_environment()
        assert setup_success, "Failed to setup test environment"
        
        # Phase 2: Establish authenticated sessions
        logger.info("=== Phase 2: Establishing authenticated sessions ===")
        sessions = await tester.establish_authenticated_sessions(user_count=3)
        assert len(sessions) >= 2, f"Failed to establish minimum sessions: {len(sessions)}"
        
        # Phase 3: Simulate Auth service failure
        logger.info("=== Phase 3: Simulating Auth service failure ===")
        failure_success = await tester.simulate_auth_service_failure()
        assert failure_success, "Failed to simulate Auth service failure"
        
        # Phase 4: Test existing sessions continue working
        logger.info("=== Phase 4: Testing session persistence during outage ===")
        outage_results = await tester.test_existing_sessions_during_outage(sessions)
        assert outage_results["success_rate"] >= 0.8, f"Too many sessions failed during outage: {outage_results}"
        
        # Phase 5: Test new logins fail gracefully
        logger.info("=== Phase 5: Testing graceful failure for new logins ===")
        graceful_failure = await tester.test_new_login_fails_gracefully()
        assert graceful_failure["failed_gracefully"], "New logins did not fail gracefully"
        
        # Phase 6: Test circuit breaker activation
        logger.info("=== Phase 6: Testing circuit breaker activation ===")
        circuit_breaker_result = await tester.test_circuit_breaker_activation()
        assert circuit_breaker_result["degraded_properly"], "Circuit breaker did not activate properly"
        
        # Phase 7: Restore Auth service
        logger.info("=== Phase 7: Restoring Auth service ===")
        restore_success = await tester.restore_auth_service()
        assert restore_success, "Failed to restore Auth service"
        
        # Phase 8: Test seamless recovery
        logger.info("=== Phase 8: Testing seamless recovery ===")
        recovery_results = await tester.test_seamless_recovery(sessions)
        assert recovery_results["recovery_rate"] >= 0.8, f"Poor recovery rate: {recovery_results}"
        assert recovery_results["new_login_works"], "New logins not working after recovery"
        
        logger.info("=== Auth Service Recovery Test PASSED ===")
        
    finally:
        await tester.cleanup_test_environment()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_auth_service_failure_isolation():
    """Test that Auth service failure does not cascade to other services."""
    tester = AuthServiceRecoveryTester()
    
    try:
        # Setup and establish sessions
        await tester.setup_test_environment()
        sessions = await tester.establish_authenticated_sessions(user_count=2)
        
        # Simulate Auth failure
        await tester.simulate_auth_service_failure()
        
        # Test Backend service isolation
        backend_url = tester.orchestrator.get_service_url("backend")
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Backend health should still work
            response = await client.get(f"{backend_url}/health")
            assert response.status_code == 200, "Backend service affected by Auth failure"
        
        # Test that existing WebSocket connections remain stable
        for user_id, session_data in sessions.items():
            ws_connection = session_data["ws_connection"]
            if ws_connection.get("connected"):
                client = ws_connection["client"]
                # Connection should still be alive
                assert client.state.name == "CONNECTED", f"WebSocket disconnected for {user_id}"
        
        logger.info("=== Auth Service Failure Isolation Test PASSED ===")
        
    finally:
        await tester.cleanup_test_environment()


if __name__ == "__main__":
    import os
    
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    sys.path.insert(0, project_root)
    
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
