"""Session Invalidation Across Services L4 Critical Path Test

Business Value Justification (BVJ):
- Segment: Security/Compliance - Business Goal: Complete session termination
- Value Impact: $18K MRR - Logout must invalidate sessions everywhere
- Strategic Impact: Ensures security compliance by preventing lingering sessions

L4 Test: Real staging environment validation of complete session invalidation.
Tests logout propagation across all services with real auth, Redis, PostgreSQL, and WebSocket.

Critical scenarios: Single logout invalidates all sessions, WebSocket termination, 
Redis sessions removed, JWT tokens blacklisted, API calls rejected, multi-device invalidation.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import pytest
import websockets
from netra_backend.tests.integration.critical_paths.l4_staging_critical_base import L4StagingCriticalPathTestBase

@dataclass
class SessionData:
    """Container for session information."""
    session_id: str
    user_id: str
    access_token: str
    device_id: str = ""

class SessionInvalidationL4TestSuite(L4StagingCriticalPathTestBase):
    """L4 test suite for session invalidation across services in staging."""
    
    def __init__(self):
        super().__init__("session_invalidation_across_services_l4")
        self.active_sessions: Dict[str, SessionData] = {}
        self._test_users: List[Dict[str, Any]] = []
        
    async def setup_test_specific_environment(self) -> None:
        """Setup session invalidation test environment."""
        await self._validate_session_endpoints()
        
    async def _validate_session_endpoints(self) -> None:
        """Validate session management endpoints in staging."""
        endpoints = [
            f"{self.service_endpoints.auth}/oauth/logout",
            f"{self.service_endpoints.backend}/api/auth/validate_session"
        ]
        
        for endpoint in endpoints:
            try:
                response = await self.test_client.options(endpoint, timeout=5.0)
                if response.status_code not in [200, 204, 405]:
                    raise RuntimeError(f"Endpoint unavailable: {endpoint}")
            except Exception:
                raise RuntimeError(f"Session endpoints unavailable: {endpoint}")
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute session invalidation critical path test."""
        test_results = {"service_calls": 0, "test_scenarios": {}}
        
        try:
            # Core test scenarios
            single_result = await self._test_single_session_invalidation()
            test_results["test_scenarios"]["single_session"] = single_result
            test_results["service_calls"] += single_result.get("service_calls", 0)
            
            multi_result = await self._test_multi_device_invalidation()
            test_results["test_scenarios"]["multi_device"] = multi_result
            test_results["service_calls"] += multi_result.get("service_calls", 0)
            
            ws_result = await self._test_websocket_invalidation()
            test_results["test_scenarios"]["websocket_termination"] = ws_result
            test_results["service_calls"] += ws_result.get("service_calls", 0)
            
            # Calculate overall success
            successful_scenarios = sum(
                1 for result in test_results["test_scenarios"].values()
                if result.get("success", False)
            )
            test_results["overall_success"] = successful_scenarios >= 2
            
        except Exception as e:
            test_results["error"] = str(e)
            test_results["overall_success"] = False
            
        return test_results
    
    async def _test_single_session_invalidation(self) -> Dict[str, Any]:
        """Test single session logout invalidates everywhere."""
        try:
            session = await self._create_test_session("enterprise")
            if not session:
                raise Exception("Session creation failed")
            
            # Verify session active before logout
            verification_before = await self._verify_session_active(session)
            if not verification_before["success"]:
                raise Exception("Session not properly established")
            
            # Perform logout
            logout_result = await self._perform_logout(session)
            if not logout_result["success"]:
                raise Exception("Logout failed")
            
            # Verify complete invalidation
            verification_after = await self._verify_session_invalidated(session)
            
            return {
                "success": verification_after["success"],
                "session_id": session.session_id,
                "service_calls": 6
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _test_multi_device_invalidation(self) -> Dict[str, Any]:
        """Test logout invalidates sessions across multiple devices."""
        try:
            sessions = []
            for device in ["web", "mobile", "api"]:
                session = await self._create_test_session("mid", device_id=device)
                if session:
                    sessions.append(session)
                    
            if len(sessions) < 2:
                raise Exception("Failed to create multi-device sessions")
            
            # Logout from first device
            logout_result = await self._perform_logout(sessions[0])
            if not logout_result["success"]:
                raise Exception("Multi-device logout failed")
                
            # Verify all sessions invalidated
            invalidation_results = []
            for session in sessions:
                verification = await self._verify_session_invalidated(session)
                invalidation_results.append(verification["success"])
            
            successful_invalidations = sum(invalidation_results)
            
            return {
                "success": successful_invalidations == len(sessions),
                "devices_tested": len(sessions),
                "successful_invalidations": successful_invalidations,
                "service_calls": len(sessions) * 4
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _test_websocket_invalidation(self) -> Dict[str, Any]:
        """Test WebSocket connections are terminated during logout."""
        try:
            session = await self._create_test_session("enterprise")
            if not session:
                raise Exception("Session creation failed")
            
            # Establish WebSocket
            websocket = await self._establish_websocket(session)
            if not websocket:
                raise Exception("WebSocket connection failed")
            
            # Test WebSocket active
            await websocket.send(json.dumps({"type": "ping"}))
            try:
                await asyncio.wait_for(websocket.recv(), timeout=3.0)
                ws_active_before = True
            except:
                ws_active_before = False
            
            # Perform logout
            logout_result = await self._perform_logout(session)
            
            # Test WebSocket disconnected
            try:
                await websocket.send(json.dumps({"type": "test"}))
                await asyncio.wait_for(websocket.recv(), timeout=2.0)
                ws_disconnected = False
            except:
                ws_disconnected = True
            
            try:
                await websocket.close()
            except:
                pass
            
            return {
                "success": ws_active_before and ws_disconnected and logout_result["success"],
                "websocket_active_before": ws_active_before,
                "websocket_disconnected_after": ws_disconnected,
                "service_calls": 4
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _create_test_session(self, tier: str = "free", device_id: str = None) -> Optional[SessionData]:
        """Create authenticated session with staging services."""
        try:
            user_data = await self.create_test_user_with_billing(tier)
            if not user_data["success"]:
                return None
            
            self._test_users.append(user_data)
            
            session = SessionData(
                session_id=f"session_l4_{tier}_{uuid.uuid4().hex[:8]}",
                user_id=user_data["user_id"],
                access_token=user_data["access_token"],
                device_id=device_id or f"device_{uuid.uuid4().hex[:8]}"
            )
            
            # Create session in backend
            response = await self.test_client.post(
                f"{self.service_endpoints.backend}/api/auth/create_session",
                json={
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "device_id": session.device_id
                },
                headers={"Authorization": f"Bearer {session.access_token}"}
            )
            
            if response.status_code not in [200, 201]:
                return None
            
            self.active_sessions[session.session_id] = session
            return session
            
        except Exception:
            return None
    
    async def _establish_websocket(self, session: SessionData):
        """Establish WebSocket connection with authentication."""
        try:
            websocket = await websockets.connect(
                self.service_endpoints.websocket,
                extra_headers={"Authorization": f"Bearer {session.access_token}"}
            )
            
            await websocket.send(json.dumps({
                "type": "authenticate",
                "session_id": session.session_id,
                "access_token": session.access_token
            }))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            auth_response = json.loads(response)
            
            if auth_response.get("type") != "auth_success":
                return None
            
            return websocket
            
        except Exception:
            return None
    
    async def _perform_logout(self, session: SessionData) -> Dict[str, Any]:
        """Perform logout invalidation across all services."""
        try:
            # Call logout endpoint
            response = await self.test_client.post(
                f"{self.service_endpoints.auth}/oauth/logout",
                json={
                    "session_id": session.session_id,
                    "user_id": session.user_id
                },
                headers={"Authorization": f"Bearer {session.access_token}"}
            )
            
            logout_success = response.status_code == 200
            
            # Call backend invalidation
            response = await self.test_client.post(
                f"{self.service_endpoints.backend}/api/auth/invalidate_session",
                json={"session_id": session.session_id},
                headers={"Authorization": f"Bearer {session.access_token}"}
            )
            
            backend_success = response.status_code == 200
            
            if session.session_id in self.active_sessions:
                del self.active_sessions[session.session_id]
            
            return {"success": logout_success and backend_success}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _verify_session_active(self, session: SessionData) -> Dict[str, Any]:
        """Verify session is active across services."""
        try:
            response = await self.test_client.get(
                f"{self.service_endpoints.backend}/api/user/profile",
                headers={"Authorization": f"Bearer {session.access_token}"}
            )
            api_success = response.status_code == 200
            
            response = await self.test_client.post(
                f"{self.service_endpoints.backend}/api/auth/validate_session",
                json={"session_id": session.session_id},
                headers={"Authorization": f"Bearer {session.access_token}"}
            )
            validation_success = response.status_code == 200
            
            return {"success": api_success and validation_success}
            
        except Exception:
            return {"success": False}
    
    async def _verify_session_invalidated(self, session: SessionData) -> Dict[str, Any]:
        """Verify session is completely invalidated."""
        try:
            response = await self.test_client.get(
                f"{self.service_endpoints.backend}/api/user/profile",
                headers={"Authorization": f"Bearer {session.access_token}"}
            )
            api_rejected = response.status_code == 401
            
            response = await self.test_client.post(
                f"{self.service_endpoints.backend}/api/auth/validate_session",
                json={"session_id": session.session_id},
                headers={"Authorization": f"Bearer {session.access_token}"}
            )
            session_invalid = response.status_code in [401, 404]
            
            return {"success": api_rejected and session_invalid}
            
        except Exception:
            return {"success": False}
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate critical path test results meet business requirements."""
        if not results.get("overall_success", False):
            return False
        
        expected_metrics = {
            "max_response_time_seconds": 10.0,
            "min_success_rate_percent": 80.0,
            "max_error_count": 2
        }
        
        business_validation = await self.validate_business_metrics(expected_metrics)
        
        scenarios = results.get("test_scenarios", {})
        critical_scenarios = ["single_session", "multi_device", "websocket_termination"]
        
        critical_success = sum(
            1 for scenario in critical_scenarios
            if scenarios.get(scenario, {}).get("success", False)
        )
        
        scenario_validation = critical_success >= 2
        
        return business_validation and scenario_validation
    
    async def cleanup_test_specific_resources(self) -> None:
        """Clean up session invalidation test resources."""
        for session_id, session in list(self.active_sessions.items()):
            try:
                await self._perform_logout(session)
            except Exception:
                pass
                
        for user_data in self._test_users:
            try:
                await self.test_client.delete(
                    f"{self.service_endpoints.auth}/api/users/{user_data['user_id']}/cleanup",
                    timeout=5.0
                )
            except Exception:
                pass

# Test fixtures and cases

@pytest.fixture
async def session_invalidation_l4_suite():
    """Create L4 session invalidation test suite."""
    suite = SessionInvalidationL4TestSuite()
    await suite.initialize_l4_environment()
    yield suite
    await suite.cleanup_l4_resources()

@pytest.mark.asyncio
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.critical
async def test_single_session_logout_invalidation_l4(session_invalidation_l4_suite):
    """Test single session logout invalidates everywhere in staging."""
    test_results = await session_invalidation_l4_suite.run_complete_critical_path_test()
    assert test_results.success is True, f"Critical path test failed: {test_results.errors}"
    test_scenarios = test_results.details.get("test_scenarios", {})
    single_session = test_scenarios.get("single_session", {})
    assert single_session.get("success", False) is True, "Single session invalidation failed"

@pytest.mark.asyncio
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.critical
async def test_multi_device_session_invalidation_l4(session_invalidation_l4_suite):
    """Test logout invalidates sessions across multiple devices in staging."""
    test_results = await session_invalidation_l4_suite.run_complete_critical_path_test()
    test_scenarios = test_results.details.get("test_scenarios", {})
    multi_device = test_scenarios.get("multi_device", {})
    assert multi_device.get("success", False) is True, "Multi-device invalidation failed"
    devices_tested = multi_device.get("devices_tested", 0)
    successful_invalidations = multi_device.get("successful_invalidations", 0)
    assert devices_tested >= 2, f"Insufficient devices tested: {devices_tested}"
    assert successful_invalidations == devices_tested, f"Not all devices invalidated"

@pytest.mark.asyncio
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.critical
async def test_websocket_termination_on_logout_l4(session_invalidation_l4_suite):
    """Test WebSocket connections are terminated during logout in staging."""
    test_results = await session_invalidation_l4_suite.run_complete_critical_path_test()
    test_scenarios = test_results.details.get("test_scenarios", {})
    websocket_result = test_scenarios.get("websocket_termination", {})
    assert websocket_result.get("success", False) is True, "WebSocket termination failed"
    assert websocket_result.get("websocket_active_before", False) is True, "WebSocket not active before"
    assert websocket_result.get("websocket_disconnected_after", False) is True, "WebSocket not disconnected"

@pytest.mark.asyncio
@pytest.mark.L4
@pytest.mark.staging
async def test_session_invalidation_performance_l4(session_invalidation_l4_suite):
    """Test session invalidation performance meets business requirements in staging."""
    test_results = await session_invalidation_l4_suite.run_complete_critical_path_test()
    assert test_results.average_response_time < 5.0, f"Response time too high: {test_results.average_response_time}s"
    assert test_results.success_rate >= 80.0, f"Success rate too low: {test_results.success_rate}%"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])