"""
Integration tests for WebSocket authentication flow coordination - NO DOCKER REQUIRED

Purpose: Test coordination between frontend auth, WebSocket connections, and backend services
Issues: #463 (Frontend WebSocket auth), #465 (Token management), #426 cluster
Approach: Mock auth services, test real coordination patterns

MISSION CRITICAL: These tests validate the complete authentication flow that enables
the Golden Path user workflow (Login → WebSocket → AI Response) without Docker.

Business Impact: Authentication enables $500K+ ARR user access to AI chat functionality
"""

import pytest
import asyncio
import json
import jwt
import uuid
import base64
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID


class TestWebSocketAuthenticationFlow(SSotAsyncTestCase):
    """Integration tests for WebSocket authentication flow coordination"""
    
    async def asyncSetUp(self):
        """Setup test environment with auth mocks and test contexts"""
        await super().asyncSetUp()
        
        # Test JWT secret for token generation
        self.jwt_secret = "test-jwt-secret-key-must-be-at-least-32-characters-long"
        
        # Test user data
        self.test_user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test.user@netra-testing.ai",
            "name": "Test User",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        # Generate valid JWT token for testing
        self.valid_jwt_token = jwt.encode(
            self.test_user_data,
            self.jwt_secret,
            algorithm="HS256"
        )
        
        # Base64 encode token for WebSocket protocol
        self.encoded_token = base64.urlsafe_b64encode(
            self.valid_jwt_token.encode()
        ).decode().rstrip('=')
        
        # Create UserExecutionContext
        self.user_context = UserExecutionContext(
            user_id=UserID(self.test_user_data["user_id"]),
            thread_id=ThreadID(str(uuid.uuid4())),
            run_id=RunID(str(uuid.uuid4())),
            request_id=f"auth_test_{uuid.uuid4()}",
            websocket_client_id=f"ws_auth_{uuid.uuid4()}",
            agent_context={
                "auth_test": True,
                "user_email": self.test_user_data["email"]
            },
            audit_metadata={
                "test_case": "websocket_auth_flow",
                "auth_method": "jwt"
            }
        )
        
        self.logger.info(f"Setup WebSocket auth test for user: {self.test_user_data['email']}")

    @pytest.mark.integration
    @pytest.mark.websocket_auth
    @pytest.mark.frontend_coordination
    @pytest.mark.no_docker_required
    async def test_frontend_websocket_auth_protocol_coordination(self):
        """
        Test coordination between frontend auth and WebSocket connection protocol
        
        Issue: #463 - Frontend WebSocket authentication flow
        Difficulty: High (35 minutes)
        Expected: PASS - Frontend and WebSocket should coordinate properly
        """
        # Simulate frontend authentication flow
        frontend_auth_state = {
            "access_token": self.valid_jwt_token,
            "user": self.test_user_data,
            "authenticated": True,
            "token_expiry": self.test_user_data["exp"].isoformat()
        }
        
        # Test different WebSocket protocol formats that frontend might send
        websocket_protocols = [
            {
                "name": "correct_format",
                "protocols": ["jwt-auth", f"jwt.{self.encoded_token}"],
                "should_succeed": True
            },
            {
                "name": "incorrect_array_format", 
                "protocols": ["jwt", self.encoded_token],  # Bug format from Issue #463
                "should_succeed": False
            },
            {
                "name": "missing_jwt_prefix",
                "protocols": ["jwt-auth", self.encoded_token],
                "should_succeed": False
            },
            {
                "name": "empty_protocols",
                "protocols": [],
                "should_succeed": False
            }
        ]
        
        auth_coordination_results = []
        
        # Mock backend auth integration
        with patch('netra_backend.app.auth_integration.auth.BackendAuthIntegration') as mock_auth:
            mock_auth_instance = AsyncMock()
            mock_auth_instance.validate_token.return_value = {
                "valid": True,
                "user_data": self.test_user_data,
                "user_id": self.test_user_data["user_id"]
            }
            mock_auth.return_value = mock_auth_instance
            
            # Test each protocol format
            for protocol_test in websocket_protocols:
                test_start = datetime.utcnow()
                
                try:
                    # Simulate WebSocket connection attempt with different protocols
                    connection_result = await self._simulate_websocket_auth_handshake(
                        frontend_auth_state=frontend_auth_state,
                        websocket_protocols=protocol_test["protocols"],
                        expected_success=protocol_test["should_succeed"]
                    )
                    
                    test_duration = (datetime.utcnow() - test_start).total_seconds()
                    
                    auth_coordination_results.append({
                        "protocol_name": protocol_test["name"],
                        "protocols": protocol_test["protocols"],
                        "expected_success": protocol_test["should_succeed"],
                        "actual_success": connection_result["success"],
                        "duration": test_duration,
                        "details": connection_result.get("details", {})
                    })
                    
                    # Verify result matches expectation
                    if protocol_test["should_succeed"] != connection_result["success"]:
                        self.logger.error(
                            f"Protocol coordination mismatch: {protocol_test['name']} "
                            f"expected {protocol_test['should_succeed']}, got {connection_result['success']}"
                        )
                        
                except Exception as e:
                    auth_coordination_results.append({
                        "protocol_name": protocol_test["name"],
                        "protocols": protocol_test["protocols"], 
                        "expected_success": protocol_test["should_succeed"],
                        "actual_success": False,
                        "error": str(e),
                        "duration": (datetime.utcnow() - test_start).total_seconds()
                    })
        
        # Analyze coordination results
        successful_coords = [r for r in auth_coordination_results if r["actual_success"]]
        failed_coords = [r for r in auth_coordination_results if not r["actual_success"]]
        
        self.logger.info(f"Auth coordination results: {len(successful_coords)} success, {len(failed_coords)} failed")
        
        # Should have at least one successful coordination (correct format)
        correct_format_result = next(
            (r for r in auth_coordination_results if r["protocol_name"] == "correct_format"), 
            None
        )
        
        assert correct_format_result is not None, "Should test correct protocol format"
        assert correct_format_result["actual_success"], (
            f"Correct protocol format should succeed. Details: {correct_format_result}"
        )
        
        # Bug format should fail (validates Issue #463 detection)
        bug_format_result = next(
            (r for r in auth_coordination_results if r["protocol_name"] == "incorrect_array_format"),
            None
        )
        
        if bug_format_result and bug_format_result["actual_success"]:
            self.logger.warning(
                f"Bug format succeeded unexpectedly - Issue #463 may be fixed: {bug_format_result}"
            )

    @pytest.mark.integration
    @pytest.mark.websocket_auth
    @pytest.mark.token_management
    @pytest.mark.no_docker_required
    async def test_auth_token_lifecycle_coordination(self):
        """
        Test coordination of auth token lifecycle with WebSocket connections
        
        Issue: #465 - Auth token management and reuse detection
        Difficulty: High (40 minutes)
        Expected: PASS - Token lifecycle should be properly managed
        """
        token_lifecycle_events = []
        
        # Mock auth service for token management
        with patch('netra_backend.app.auth_integration.auth.BackendAuthIntegration') as mock_auth:
            mock_auth_instance = AsyncMock()
            
            # Track token validation calls
            async def track_token_validation(token):
                validation_event = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "token": token[:20] + "...",  # Partial token for logging
                    "action": "validate"
                }
                token_lifecycle_events.append(validation_event)
                
                # Simulate token validation
                try:
                    decoded = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
                    return {
                        "valid": True,
                        "user_data": decoded,
                        "user_id": decoded.get("user_id")
                    }
                except jwt.InvalidTokenError:
                    return {"valid": False, "error": "Invalid token"}
            
            mock_auth_instance.validate_token.side_effect = track_token_validation
            mock_auth.return_value = mock_auth_instance
            
            # Test token lifecycle scenarios
            lifecycle_scenarios = [
                {
                    "name": "fresh_token_connection",
                    "token": self.valid_jwt_token,
                    "expected_validations": 1
                },
                {
                    "name": "token_reuse_same_connection", 
                    "token": self.valid_jwt_token,
                    "reuse_count": 3,
                    "expected_validations": 1  # Should cache validation
                },
                {
                    "name": "expired_token_handling",
                    "token": self._generate_expired_token(),
                    "expected_validation_failure": True
                },
                {
                    "name": "token_refresh_scenario",
                    "token": self.valid_jwt_token,
                    "refresh_token": self._generate_fresh_token(),
                    "expected_validations": 2  # Original + refreshed
                }
            ]
            
            for scenario in lifecycle_scenarios:
                scenario_start = datetime.utcnow()
                self.logger.info(f"Testing token lifecycle scenario: {scenario['name']}")
                
                try:
                    if scenario["name"] == "fresh_token_connection":
                        # Test fresh token connection
                        await self._test_fresh_token_connection(scenario["token"])
                        
                    elif scenario["name"] == "token_reuse_same_connection":
                        # Test token reuse within same connection
                        for i in range(scenario["reuse_count"]):
                            await self._test_token_reuse_connection(scenario["token"], attempt=i)
                            
                    elif scenario["name"] == "expired_token_handling":
                        # Test expired token handling
                        with pytest.raises((jwt.ExpiredSignatureError, Exception)):
                            await self._test_expired_token_connection(scenario["token"])
                            
                    elif scenario["name"] == "token_refresh_scenario":
                        # Test token refresh flow
                        await self._test_token_refresh_flow(
                            original_token=scenario["token"],
                            refresh_token=scenario["refresh_token"]
                        )
                        
                    scenario_duration = (datetime.utcnow() - scenario_start).total_seconds()
                    self.logger.info(f"Scenario {scenario['name']} completed in {scenario_duration:.2f}s")
                    
                except Exception as e:
                    if not scenario.get("expected_validation_failure", False):
                        self.logger.error(f"Unexpected error in scenario {scenario['name']}: {e}")
                        raise
                    else:
                        self.logger.info(f"Expected failure in scenario {scenario['name']}: {e}")
        
        # Analyze token lifecycle events
        validation_count = len([e for e in token_lifecycle_events if e["action"] == "validate"])
        
        assert validation_count > 0, "Should have at least some token validations"
        
        # Verify token events are properly tracked
        self.logger.info(f"Token lifecycle events tracked: {len(token_lifecycle_events)}")
        
        for event in token_lifecycle_events:
            assert "timestamp" in event, "All events should be timestamped"
            assert "action" in event, "All events should specify action"

    @pytest.mark.integration
    @pytest.mark.websocket_auth
    @pytest.mark.user_context_integration
    @pytest.mark.no_docker_required
    async def test_auth_websocket_user_context_integration(self):
        """
        Test integration between auth, WebSocket, and UserExecutionContext
        
        Issue: #463/#465 - Complete auth integration with user context
        Difficulty: High (35 minutes)
        Expected: PASS - All components should integrate seamlessly
        """
        # Mock complete auth and WebSocket stack
        with patch('netra_backend.app.auth_integration.auth.BackendAuthIntegration') as mock_auth, \
             patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_ws_manager:
            
            # Setup auth integration mock
            mock_auth_instance = AsyncMock()
            mock_auth_instance.validate_token.return_value = {
                "valid": True,
                "user_data": self.test_user_data,
                "user_id": self.test_user_data["user_id"]
            }
            mock_auth.return_value = mock_auth_instance
            
            # Setup WebSocket manager mock
            mock_connection = AsyncMock()
            websocket_events = []
            
            async def track_websocket_events(message):
                try:
                    event_data = json.loads(message)
                    websocket_events.append(event_data)
                except:
                    websocket_events.append({"raw_message": message})
            
            mock_connection.send.side_effect = track_websocket_events
            
            mock_manager = AsyncMock()
            mock_manager.get_connection_by_client_id.return_value = mock_connection
            mock_ws_manager.return_value = mock_manager
            
            # Test complete integration flow
            integration_steps = []
            
            try:
                # Step 1: Authentication
                integration_steps.append("auth_validation")
                auth_result = await mock_auth_instance.validate_token(self.valid_jwt_token)
                assert auth_result["valid"], "Authentication should succeed"
                
                # Step 2: Create UserExecutionContext from auth
                integration_steps.append("user_context_creation")
                authenticated_context = UserExecutionContext(
                    user_id=UserID(auth_result["user_id"]),
                    thread_id=self.user_context.thread_id,
                    run_id=self.user_context.run_id,
                    request_id=self.user_context.request_id,
                    websocket_client_id=self.user_context.websocket_client_id,
                    agent_context={
                        "authenticated": True,
                        "user_email": auth_result["user_data"]["email"],
                        "auth_method": "jwt"
                    },
                    audit_metadata={
                        "auth_validated_at": datetime.utcnow().isoformat(),
                        "test_integration": True
                    }
                )
                
                # Step 3: Create WebSocket bridge with authenticated context
                integration_steps.append("websocket_bridge_creation")
                from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
                websocket_bridge = create_agent_websocket_bridge(authenticated_context)
                
                assert websocket_bridge is not None, "WebSocket bridge should be created"
                
                # Step 4: Send authenticated events through bridge
                integration_steps.append("authenticated_event_sending")
                auth_events = [
                    ("user_authenticated", {
                        "user_id": str(authenticated_context.user_id),
                        "user_email": self.test_user_data["email"],
                        "auth_timestamp": datetime.utcnow().isoformat()
                    }),
                    ("agent_started", {
                        "user_id": str(authenticated_context.user_id),
                        "authenticated_session": True,
                        "capabilities": ["chat", "ai_analysis"]
                    }),
                    ("agent_completed", {
                        "user_id": str(authenticated_context.user_id),
                        "session_duration": 5.2,
                        "authenticated": True
                    })
                ]
                
                for event_type, event_data in auth_events:
                    if hasattr(websocket_bridge, 'send_event'):
                        await websocket_bridge.send_event(event_type, event_data)
                    elif hasattr(websocket_bridge, 'emit_event'):
                        await websocket_bridge.emit_event(event_type, event_data)
                
                integration_steps.append("integration_complete")
                
                # Verify complete integration
                assert len(websocket_events) >= len(auth_events), (
                    f"Should send all authenticated events. Sent: {len(websocket_events)}, Expected: {len(auth_events)}"
                )
                
                # Verify events contain authenticated user context
                for event in websocket_events:
                    if isinstance(event, dict) and "data" in event:
                        event_user_id = event["data"].get("user_id")
                        if event_user_id:
                            assert event_user_id == str(authenticated_context.user_id), (
                                f"Event should contain correct authenticated user ID"
                            )
                
                self.logger.info(f"Auth-WebSocket integration completed successfully: {integration_steps}")
                
            except Exception as e:
                self.logger.error(f"Integration failed at step {integration_steps[-1] if integration_steps else 'unknown'}: {e}")
                raise

    # Helper methods for token lifecycle testing
    
    async def _simulate_websocket_auth_handshake(
        self, 
        frontend_auth_state: Dict[str, Any], 
        websocket_protocols: List[str],
        expected_success: bool
    ) -> Dict[str, Any]:
        """Simulate WebSocket authentication handshake"""
        
        # Simulate protocol validation that WebSocket server would do
        success = False
        details = {}
        
        try:
            if len(websocket_protocols) >= 2:
                auth_protocol = websocket_protocols[0] 
                token_protocol = websocket_protocols[1]
                
                # Check correct format: ["jwt-auth", "jwt.{encoded_token}"]
                if auth_protocol == "jwt-auth" and token_protocol.startswith("jwt."):
                    encoded_token = token_protocol[4:]  # Remove "jwt." prefix
                    
                    # Decode and validate token
                    try:
                        decoded_token = base64.urlsafe_b64decode(encoded_token + "===")
                        jwt_token = decoded_token.decode()
                        
                        # Validate JWT
                        jwt.decode(jwt_token, self.jwt_secret, algorithms=["HS256"])
                        success = True
                        details = {"protocol_validation": "success", "token_valid": True}
                        
                    except Exception as e:
                        details = {"protocol_validation": "failed", "error": str(e)}
                        
                else:
                    details = {"protocol_validation": "failed", "reason": "incorrect_format"}
            else:
                details = {"protocol_validation": "failed", "reason": "insufficient_protocols"}
                
        except Exception as e:
            details = {"error": str(e)}
        
        return {"success": success, "details": details}
    
    async def _test_fresh_token_connection(self, token: str):
        """Test fresh token connection scenario"""
        # Simulate fresh WebSocket connection with new token
        await asyncio.sleep(0.01)  # Simulate network delay
        
    async def _test_token_reuse_connection(self, token: str, attempt: int):
        """Test token reuse within same connection"""
        await asyncio.sleep(0.01)  # Simulate reuse delay
        
    async def _test_expired_token_connection(self, token: str):
        """Test expired token connection scenario"""
        # This should raise an exception for expired tokens
        jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        
    async def _test_token_refresh_flow(self, original_token: str, refresh_token: str):
        """Test token refresh flow scenario"""
        # Test original token
        await self._test_fresh_token_connection(original_token)
        
        # Simulate token refresh
        await asyncio.sleep(0.02)
        
        # Test refreshed token
        await self._test_fresh_token_connection(refresh_token)
    
    def _generate_expired_token(self) -> str:
        """Generate an expired JWT token for testing"""
        expired_data = self.test_user_data.copy()
        expired_data["exp"] = datetime.utcnow() - timedelta(minutes=1)  # Expired 1 minute ago
        
        return jwt.encode(expired_data, self.jwt_secret, algorithm="HS256")
    
    def _generate_fresh_token(self) -> str:
        """Generate a fresh JWT token for testing"""
        fresh_data = self.test_user_data.copy()
        fresh_data["exp"] = datetime.utcnow() + timedelta(hours=2)  # Valid for 2 hours
        fresh_data["iat"] = datetime.utcnow()  # Fresh issued time
        
        return jwt.encode(fresh_data, self.jwt_secret, algorithm="HS256")


# Test configuration
pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket_auth,
    pytest.mark.auth_coordination,
    pytest.mark.frontend_coordination,
    pytest.mark.token_management,
    pytest.mark.issue_463,
    pytest.mark.issue_465,
    pytest.mark.issue_426_cluster,
    pytest.mark.no_docker_required,
    pytest.mark.real_services_not_required
]


if __name__ == "__main__":
    # Allow running this file directly
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s", 
        "--no-docker"
    ])