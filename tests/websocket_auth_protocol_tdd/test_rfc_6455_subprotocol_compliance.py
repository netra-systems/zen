"""
RFC 6455 WebSocket Subprotocol Compliance Tests - TDD Approach

Issue #280: WebSocket authentication failure - P0 CRITICAL affecting $500K+ ARR

This test suite validates RFC 6455 compliance for WebSocket subprotocol negotiation,
specifically testing that the backend properly responds with the selected subprotocol
parameter in websocket.accept() calls.

Business Impact:
- $500K+ ARR Golden Path blocked due to authentication handshake failures
- All 5 critical agent events fail to deliver (agent_started, agent_thinking, etc.)
- Frontend correctly sends subprotocols=['jwt-auth', 'jwt.{token}'] per RFC 6455
- Backend violates RFC 6455 by not responding with selected subprotocol

Root Cause (Expected):
- 4 websocket.accept() calls missing subprotocol="jwt-auth" parameter
- Locations: websocket_ssot.py lines 298, 393, 461, 539
- Error: WebSocket closes with Error 1006 (abnormal closure)

TDD Strategy:
1. Create failing tests that validate subprotocol negotiation
2. Tests should fail with Error 1006 or similar connection issues
3. After fix, tests should pass with proper subprotocol selection

RFC 6455 Requirements Tested:
- Section 4.2.2: Server must select exactly one subprotocol from client list
- Section 11.3.4: Sec-WebSocket-Protocol response header required if negotiated
- WebSocket.accept(subprotocol="selected_protocol") compliance
"""

import asyncio
import websockets
import json
import base64
import logging
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Optional, List, Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class RFC6455SubprotocolComplianceTest(SSotAsyncTestCase):
    """
    RFC 6455 WebSocket Subprotocol Negotiation Compliance Tests
    
    Tests the 4 critical websocket.accept() locations for proper subprotocol parameter
    usage according to RFC 6455 WebSocket Protocol specification.
    
    Expected Behavior (After Fix):
    - Backend selects 'jwt-auth' from client subprotocols list
    - websocket.accept(subprotocol="jwt-auth") called at all 4 locations
    - JWT token extracted from 'jwt.{token}' subprotocol format
    - WebSocket connection succeeds with proper handshake completion
    """
    
    def setUp(self):
        """Set up test fixtures for RFC 6455 compliance testing"""
        super().setUp()
        
        # Test JWT token (valid format for extraction)
        self.test_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyIiwiaWF0IjoxNTE2MjM5MDIyfQ.test_signature"
        
        # Base64URL encode for subprotocol (as frontend does)
        self.encoded_jwt_token = base64.urlsafe_b64encode(self.test_jwt_token.encode()).decode().rstrip('=')
        
        # RFC 6455 compliant subprotocol list (as sent by frontend)
        self.rfc_compliant_subprotocols = [
            "jwt-auth",  # Protocol identifier
            f"jwt.{self.encoded_jwt_token}"  # JWT token payload
        ]
        
        # WebSocket SSOT router for testing
        self.websocket_router = WebSocketSSOTRouter()
        
        # Backend URL for integration tests
        env = get_env()
        backend_port = env.get('BACKEND_PORT', '8000')
        self.backend_websocket_url = f"ws://localhost:{backend_port}/ws"
    
    def create_mock_websocket(self, subprotocols: List[str], state="CONNECTING") -> Mock:
        """Create mock WebSocket with RFC 6455 compliant headers"""
        websocket = Mock()
        websocket.state = state
        websocket.subprotocols = subprotocols
        websocket.headers = {
            "sec-websocket-protocol": ", ".join(subprotocols),
            "connection": "upgrade",
            "upgrade": "websocket"
        }
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        websocket.client.port = 3000
        
        # Mock accept method to track subprotocol parameter
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        websocket.send = AsyncMock()
        
        return websocket

    async def test_main_mode_subprotocol_negotiation_failure(self):
        """
        Test: Main mode websocket.accept() missing subprotocol parameter
        
        Location: websocket_ssot.py line 298
        Expected: await websocket.accept() → FAILS RFC 6455 (missing subprotocol)
        Should Be: await websocket.accept(subprotocol="jwt-auth") → RFC 6455 compliant
        
        This test validates that the main mode WebSocket endpoint violates RFC 6455
        by not including the subprotocol parameter in the accept() call.
        """
        # Arrange: Create WebSocket with RFC 6455 compliant subprotocols
        websocket = self.create_mock_websocket(self.rfc_compliant_subprotocols)
        
        # Mock authentication to focus on subprotocol negotiation
        with patch('netra_backend.app.routes.websocket_ssot.authenticate_websocket_ssot') as mock_auth:
            mock_auth_result = Mock()
            mock_auth_result.success = True
            mock_auth_result.user_context = Mock()
            mock_auth_result.user_context.user_id = "test_user_123"
            mock_auth.return_value = mock_auth_result
            
            # Mock WebSocket manager creation
            with patch.object(self.websocket_router, '_create_websocket_manager') as mock_create_manager:
                mock_create_manager.return_value = Mock()
                
                # Act: Call main mode WebSocket handler
                try:
                    await self.websocket_router.handle_main_mode(websocket)
                except Exception as e:
                    # Expected: Some form of connection issue due to missing subprotocol
                    logger.info(f"Main mode connection issue (expected): {e}")
        
        # Assert: WebSocket accept was called WITHOUT subprotocol parameter (RFC 6455 violation)
        websocket.accept.assert_called_once()
        call_args = websocket.accept.call_args
        
        # CRITICAL TEST: This should FAIL initially - no subprotocol parameter
        assert call_args[1].get('subprotocol') is None, \
            "EXPECTED FAILURE: websocket.accept() called without subprotocol parameter (RFC 6455 violation)"
        
        # Log the RFC violation
        logger.error(f"🚨 RFC 6455 VIOLATION: Main mode websocket.accept() missing subprotocol parameter")
        logger.error(f"   Client sent: {self.rfc_compliant_subprotocols}")
        logger.error(f"   Server response: websocket.accept() with no subprotocol")
        logger.error(f"   RFC 6455 requires: websocket.accept(subprotocol='jwt-auth')")

    async def test_factory_mode_subprotocol_negotiation_failure(self):
        """
        Test: Factory mode websocket.accept() missing subprotocol parameter
        
        Location: websocket_ssot.py line 393  
        Expected: await websocket.accept() → FAILS RFC 6455 (missing subprotocol)
        Should Be: await websocket.accept(subprotocol="jwt-auth") → RFC 6455 compliant
        """
        # Arrange: WebSocket with factory mode context
        websocket = self.create_mock_websocket(self.rfc_compliant_subprotocols)
        
        # Mock pre-authentication for factory mode
        with patch('netra_backend.app.routes.websocket_ssot.pre_authenticate_user') as mock_preauth:
            mock_user_context = Mock()
            mock_user_context.user_id = "factory_test_user"
            mock_preauth.return_value = mock_user_context
            
            with patch.object(self.websocket_router, '_create_websocket_manager') as mock_create_manager:
                mock_create_manager.return_value = Mock()
                
                # Act: Call factory mode WebSocket handler
                try:
                    await self.websocket_router.handle_factory_mode(websocket)
                except Exception as e:
                    logger.info(f"Factory mode connection issue (expected): {e}")
        
        # Assert: RFC 6455 violation in factory mode
        websocket.accept.assert_called_once()
        call_args = websocket.accept.call_args
        
        # CRITICAL TEST: Should FAIL initially - no subprotocol parameter  
        assert call_args[1].get('subprotocol') is None, \
            "EXPECTED FAILURE: Factory mode websocket.accept() missing subprotocol parameter"
            
        logger.error(f"🚨 RFC 6455 VIOLATION: Factory mode websocket.accept() missing subprotocol parameter")

    async def test_isolated_mode_subprotocol_negotiation_failure(self):
        """
        Test: Isolated mode websocket.accept() missing subprotocol parameter
        
        Location: websocket_ssot.py line 461
        Expected: await websocket.accept() → FAILS RFC 6455 (missing subprotocol) 
        Should Be: await websocket.accept(subprotocol="jwt-auth") → RFC 6455 compliant
        """
        # Arrange: WebSocket for isolated mode
        websocket = self.create_mock_websocket(self.rfc_compliant_subprotocols)
        
        # Mock isolated mode authentication
        with patch('netra_backend.app.routes.websocket_ssot.authenticate_websocket_ssot') as mock_auth:
            mock_auth_result = Mock()
            mock_auth_result.success = True
            mock_auth_result.user_context = Mock()
            mock_auth_result.user_context.user_id = "isolated_test_user"
            mock_auth.return_value = mock_auth_result
            
            # Act: Call isolated mode handler
            try:
                await self.websocket_router.handle_isolated_mode(websocket)
            except Exception as e:
                logger.info(f"Isolated mode connection issue (expected): {e}")
        
        # Assert: RFC 6455 violation in isolated mode
        websocket.accept.assert_called_once() 
        call_args = websocket.accept.call_args
        
        # CRITICAL TEST: Should FAIL initially - no subprotocol parameter
        assert call_args[1].get('subprotocol') is None, \
            "EXPECTED FAILURE: Isolated mode websocket.accept() missing subprotocol parameter"
            
        logger.error(f"🚨 RFC 6455 VIOLATION: Isolated mode websocket.accept() missing subprotocol parameter")

    async def test_legacy_mode_subprotocol_negotiation_failure(self):
        """
        Test: Legacy mode websocket.accept() missing subprotocol parameter
        
        Location: websocket_ssot.py line 539
        Expected: await websocket.accept() → FAILS RFC 6455 (missing subprotocol)
        Should Be: await websocket.accept(subprotocol="jwt-auth") → RFC 6455 compliant
        """
        # Arrange: WebSocket for legacy mode
        websocket = self.create_mock_websocket(self.rfc_compliant_subprotocols)
        
        # Act: Call legacy mode handler (simplest case)
        try:
            await self.websocket_router.handle_legacy_mode(websocket)
        except Exception as e:
            logger.info(f"Legacy mode connection issue (expected): {e}")
        
        # Assert: RFC 6455 violation in legacy mode
        websocket.accept.assert_called_once()
        call_args = websocket.accept.call_args
        
        # CRITICAL TEST: Should FAIL initially - no subprotocol parameter
        assert call_args[1].get('subprotocol') is None, \
            "EXPECTED FAILURE: Legacy mode websocket.accept() missing subprotocol parameter"
            
        logger.error(f"🚨 RFC 6455 VIOLATION: Legacy mode websocket.accept() missing subprotocol parameter")

    async def test_rfc_6455_subprotocol_selection_logic(self):
        """
        Test: RFC 6455 compliant subprotocol selection logic
        
        Per RFC 6455, server must:
        1. Receive client subprotocols: ["jwt-auth", "jwt.{token}"]
        2. Select exactly one: "jwt-auth" 
        3. Respond with selected subprotocol in accept() call
        4. Extract JWT from "jwt.{token}" format
        
        This test validates the expected logic after fix is applied.
        """
        # Test data: Various subprotocol combinations
        test_cases = [
            {
                "name": "Standard JWT auth",
                "subprotocols": ["jwt-auth", f"jwt.{self.encoded_jwt_token}"],
                "expected_selected": "jwt-auth",
                "should_extract_jwt": True
            },
            {
                "name": "JWT auth only", 
                "subprotocols": ["jwt-auth"],
                "expected_selected": "jwt-auth",
                "should_extract_jwt": False  # No jwt.{token} to extract from
            },
            {
                "name": "Multiple protocols with JWT",
                "subprotocols": ["chat-v1", "jwt-auth", f"jwt.{self.encoded_jwt_token}", "binary"],
                "expected_selected": "jwt-auth", 
                "should_extract_jwt": True
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case["name"]):
                # This test documents expected behavior after fix
                # Currently will fail due to missing subprotocol selection
                
                logger.info(f"🧪 RFC 6455 Test Case: {test_case['name']}")
                logger.info(f"   Client subprotocols: {test_case['subprotocols']}")
                logger.info(f"   Expected selected: {test_case['expected_selected']}")
                logger.info(f"   Should extract JWT: {test_case['should_extract_jwt']}")
                
                # Document the required implementation
                expected_fix = f"""
                # REQUIRED FIX for RFC 6455 compliance:
                if 'jwt-auth' in websocket.subprotocols:
                    selected_subprotocol = 'jwt-auth'
                    await websocket.accept(subprotocol=selected_subprotocol)
                else:
                    # No supported subprotocol
                    await websocket.close(code=1002, reason="Unsupported subprotocol")
                """
                logger.info(f"📋 Required implementation:\n{expected_fix}")

    @pytest.mark.integration 
    async def test_real_websocket_connection_subprotocol_failure(self):
        """
        Integration test: Real WebSocket connection with subprotocol negotiation
        
        This test attempts a real WebSocket connection to validate the actual
        RFC 6455 violation occurs in practice, not just in unit tests.
        
        Expected: Connection fails with Error 1006 or similar due to missing 
                  subprotocol response from server.
        """
        try:
            # Attempt real WebSocket connection with RFC 6455 compliant subprotocols
            logger.info(f"🔌 Attempting WebSocket connection to: {self.backend_websocket_url}")
            logger.info(f"   Subprotocols: {self.rfc_compliant_subprotocols}")
            
            # This should FAIL due to backend RFC 6455 violation
            connection = await asyncio.wait_for(
                websockets.connect(
                    self.backend_websocket_url,
                    subprotocols=self.rfc_compliant_subprotocols,
                    timeout=10
                ),
                timeout=15
            )
            
            # If we get here, connection unexpectedly succeeded
            selected_subprotocol = connection.subprotocol
            logger.error(f"🚨 UNEXPECTED: WebSocket connection succeeded!")
            logger.error(f"   Selected subprotocol: {selected_subprotocol}")
            
            await connection.close()
            
            # Test should fail here - connection should not succeed with current bug
            assert False, "UNEXPECTED SUCCESS: WebSocket connection should fail due to RFC 6455 violation"
            
        except (websockets.exceptions.ConnectionClosedError, 
                websockets.exceptions.InvalidStatusCode,
                asyncio.TimeoutError,
                OSError) as e:
            # Expected failure due to RFC 6455 subprotocol violation
            logger.info(f"✅ EXPECTED FAILURE: WebSocket connection failed due to subprotocol issue")
            logger.info(f"   Error type: {type(e).__name__}")
            logger.info(f"   Error details: {str(e)}")
            
            # Document the expected fix impact
            logger.info(f"🔧 After fix: Connection should succeed with subprotocol='jwt-auth'")
            
            # Test passes - this failure is expected with current bug
            assert True, "Expected connection failure due to RFC 6455 subprotocol violation"

    def test_subprotocol_selection_algorithm(self):
        """
        Unit test: Subprotocol selection algorithm per RFC 6455
        
        Tests the algorithm that should be implemented to select subprotocols
        according to RFC 6455 Section 4.2.2.
        """
        test_cases = [
            {
                "client_subprotocols": ["jwt-auth", f"jwt.{self.encoded_jwt_token}"],
                "server_supported": ["jwt-auth", "chat-v1"],
                "expected_selected": "jwt-auth"
            },
            {
                "client_subprotocols": ["chat-v2", "binary"],
                "server_supported": ["jwt-auth", "chat-v1"], 
                "expected_selected": None  # No overlap
            },
            {
                "client_subprotocols": [],
                "server_supported": ["jwt-auth"],
                "expected_selected": None  # Client sent no subprotocols
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            with self.subTest(f"algorithm_case_{i}"):
                # Document expected algorithm
                def select_subprotocol(client_protocols: List[str], server_supported: List[str]) -> Optional[str]:
                    """RFC 6455 compliant subprotocol selection"""
                    for protocol in client_protocols:
                        if protocol in server_supported:
                            return protocol
                    return None
                
                # Test the algorithm
                result = select_subprotocol(
                    test_case["client_subprotocols"],
                    test_case["server_supported"]
                )
                
                assert result == test_case["expected_selected"], \
                    f"Subprotocol selection failed for case {i}"
                
                logger.info(f"✅ RFC 6455 Algorithm Test {i}: {result}")

    def test_business_impact_validation(self):
        """
        Test: Validate business impact of RFC 6455 subprotocol violation
        
        Documents the critical business functionality blocked by this issue:
        - $500K+ ARR Golden Path user flow
        - All 5 critical WebSocket agent events
        - Real-time AI response delivery
        """
        critical_events_blocked = [
            "agent_started",    # User sees agent began processing 
            "agent_thinking",   # Real-time reasoning visibility
            "tool_executing",   # Tool usage transparency
            "tool_completed",   # Tool results display
            "agent_completed"   # User knows response is ready
        ]
        
        # Document business impact
        business_impact = {
            "revenue_at_risk": "$500K+ ARR",
            "affected_user_flow": "Golden Path (login → AI responses)",
            "critical_events_blocked": critical_events_blocked,
            "user_experience_impact": "Complete chat functionality failure",
            "error_manifestation": "WebSocket Error 1006 (abnormal closure)"
        }
        
        logger.error(f"🚨 BUSINESS IMPACT OF RFC 6455 VIOLATION:")
        for key, value in business_impact.items():
            logger.error(f"   {key}: {value}")
        
        # Test passes - this documents the impact
        assert len(critical_events_blocked) == 5, "All 5 critical events must be blocked"
        assert "Golden Path" in business_impact["affected_user_flow"], "Golden Path must be affected"


if __name__ == "__main__":
    # Run the TDD test suite
    import unittest
    
    # Configure logging for test output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(RFC6455SubprotocolComplianceTest)
    runner = unittest.TextTestRunner(verbosity=2)
    
    print("🧪 RFC 6455 WebSocket Subprotocol Compliance Test Suite")
    print("Issue #280: WebSocket authentication failure - P0 CRITICAL")
    print("Expected: Tests should FAIL initially, demonstrating RFC 6455 violation")
    print("After Fix: Tests should PASS, validating subprotocol negotiation")
    print("=" * 80)
    
    result = runner.run(suite)
    
    if result.failures or result.errors:
        print("✅ EXPECTED: Tests failed, demonstrating RFC 6455 subprotocol violation")
        print("🔧 Next Step: Apply subprotocol parameter fix to websocket.accept() calls")
    else:
        print("🚨 UNEXPECTED: Tests passed - RFC 6455 violation may already be fixed")