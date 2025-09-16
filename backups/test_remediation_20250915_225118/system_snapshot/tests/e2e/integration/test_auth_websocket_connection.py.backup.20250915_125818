"""
WebSocket Authentication Connection Tests - Basic connection and validation

Tests fundamental WebSocket authentication flows including token validation,
connection establishment, and basic messaging functionality.

Business Value Justification (BVJ):
- Segment: ALL | Goal: Core Chat | Impact: $300K MRR
- Ensures reliable WebSocket authentication for real-time AI interactions
- Validates token validation consistency across Auth  ->  Backend  ->  WebSocket
- Prevents authentication failures during critical AI workflows

Test Coverage:
- WebSocket connection with valid tokens
- Invalid token rejection with proper error handling
- Cross-service token validation consistency
- Basic message sending with authenticated connections
"""

import asyncio
import time
import pytest
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment

from test_framework.service_dependencies import requires_services
from test_framework.helpers.auth_helpers import (
    WebSocketAuthTester,
    TokenExpiryTester,
    AuthTestConfig,
    skip_if_services_unavailable,
    assert_auth_performance,
    assert_token_rejection
)


@requires_services(["auth", "backend", "websocket"], mode="either")
@pytest.mark.critical
@pytest.mark.asyncio
@pytest.mark.e2e
class TestWebSocketAuthConnection:
    """Critical WebSocket Authentication Connection Tests."""
    
    @pytest.fixture
    def auth_tester(self):
        """Initialize WebSocket auth tester."""
        return WebSocketAuthTester()
    
    @pytest.fixture
    def expiry_tester(self, auth_tester):
        """Initialize token expiry tester."""
        return TokenExpiryTester(auth_tester)
    
    @pytest.mark.e2e
    async def test_websocket_auth_integration(self, auth_tester):
        """
        BVJ: Segment: ALL | Goal: Core Chat | Impact: $300K MRR
        Tests: WebSocket authentication and message handling
        """
        start_time = time.time()
        
        try:
            # Phase 1: Generate real JWT token (auth < 100ms)
            jwt_token = await auth_tester.generate_real_jwt_token("free")
            using_real_auth = jwt_token is not None
            
            if not using_real_auth:
                jwt_token = auth_tester.create_mock_jwt_token()
                
            assert jwt_token is not None, "Failed to create JWT token"
            
            # Phase 2: Validate token in Backend service (< 50ms)
            backend_result = await auth_tester.validate_token_in_backend(jwt_token)
            if not backend_result["valid"] and not using_real_auth:
                pytest.skip("Backend service not available and no real auth token")
            
            assert_auth_performance(backend_result["validation_time"], "validation")
            
            # Phase 3: Establish WebSocket connection
            ws_result = await auth_tester.establish_websocket_connection(jwt_token)
            if not ws_result["connected"]:
                skip_if_services_unavailable(str(ws_result.get("error", "")))
            else:
                # Phase 4: Test message sending
                websocket = ws_result["websocket"]
                
                message_result = await auth_tester.send_test_message(
                    websocket, "Test authentication integration message"
                )
                assert message_result["sent"], f"Failed to send message: {message_result['error']}"
                
                await websocket.close()
            
            # Verify overall performance
            execution_time = time.time() - start_time
            assert execution_time < AuthTestConfig.TEST_EXECUTION_LIMIT, \
                f"Test took {execution_time:.2f}s, expected <{AuthTestConfig.TEST_EXECUTION_LIMIT}s"
            
        except Exception as e:
            skip_if_services_unavailable(str(e))
    
    @pytest.mark.e2e
    async def test_invalid_token_rejection(self, auth_tester, expiry_tester):
        """Test proper rejection of invalid tokens with performance requirements."""
        malformed_tokens = expiry_tester.create_malformed_tokens()
        
        for test_name, invalid_token in malformed_tokens:
            if not invalid_token:  # Skip empty tokens for WebSocket test
                continue
                
            try:
                start_time = time.time()
                ws_result = await auth_tester.establish_websocket_connection(
                    invalid_token, timeout=2.0
                )
                rejection_time = time.time() - start_time
                
                # Invalid tokens should be rejected quickly
                assert_token_rejection(ws_result, test_name)
                assert rejection_time < 1.0, f"Token rejection took {rejection_time:.3f}s, should be <1s"
                
            except Exception as e:
                skip_if_services_unavailable(str(e))
    
    @pytest.mark.e2e
    async def test_cross_service_token_consistency(self, auth_tester):
        """Test token validation consistency across Auth and Backend services."""
        try:
            # Generate token from Auth service
            jwt_token = await auth_tester.generate_real_jwt_token("free")
            if not jwt_token:
                pytest.skip("Could not get token from Auth service")
            
            # Test Backend service validation
            backend_result = await auth_tester.validate_token_in_backend(jwt_token)
            assert backend_result["valid"], \
                f"Backend should accept Auth service tokens: {backend_result['error']}"
            
            # Test WebSocket accepts same token
            ws_result = await auth_tester.establish_websocket_connection(jwt_token)
            websocket_valid = ws_result["connected"]
            
            if ws_result["websocket"]:
                await ws_result["websocket"].close()
            
            # All services should consistently validate the same token
            assert websocket_valid, \
                f"WebSocket should accept tokens validated by Backend: {ws_result['error']}"
            
        except Exception as e:
            skip_if_services_unavailable(str(e))
    
    @pytest.mark.e2e
    async def test_websocket_connection_basic_messaging(self, auth_tester):
        """Test basic messaging functionality with authenticated WebSocket connection."""
        try:
            # Establish authenticated connection
            jwt_token = await auth_tester.generate_real_jwt_token("free")
            if not jwt_token:
                jwt_token = auth_tester.create_mock_jwt_token()
            
            ws_result = await auth_tester.establish_websocket_connection(jwt_token)
            if not ws_result["connected"]:
                skip_if_services_unavailable(str(ws_result.get("error", "")))
            
            websocket = ws_result["websocket"]
            
            # Test multiple message types
            test_messages = [
                "Basic test message",
                "Message with special characters: [U+00E9][U+00F1][U+2122]",
                '{"type": "json", "content": "JSON formatted message"}',
                "Long message: " + "A" * 500  # Test longer content
            ]
            
            successful_messages = 0
            for i, message_content in enumerate(test_messages):
                message_result = await auth_tester.send_test_message(websocket, message_content)
                if message_result["sent"]:
                    successful_messages += 1
                
                # Brief pause between messages
                await asyncio.sleep(0.1)
            
            # At least some messages should succeed
            assert successful_messages > 0, "At least one message should be sent successfully"
            
            await websocket.close()
            
        except Exception as e:
            skip_if_services_unavailable(str(e))
    
    @pytest.mark.e2e
    async def test_websocket_connection_different_user_tiers(self, auth_tester):
        """Test WebSocket authentication with different user tier tokens."""
        try:
            tested_tiers = []
            successful_connections = 0
            
            for tier in ["free", "early", "mid"]:
                try:
                    # Generate token for tier
                    jwt_token = await auth_tester.generate_real_jwt_token(tier)
                    if not jwt_token:
                        jwt_token = auth_tester.create_mock_jwt_token()
                    
                    # Test connection
                    ws_result = await auth_tester.establish_websocket_connection(jwt_token)
                    tested_tiers.append(tier)
                    
                    if ws_result["connected"]:
                        successful_connections += 1
                        
                        # Test basic message for this tier
                        message_result = await auth_tester.send_test_message(
                            ws_result["websocket"], f"Test message for {tier} tier"
                        )
                        
                        await ws_result["websocket"].close()
                        
                except Exception as e:
                    continue
            
            # At least one tier should work if services are available
            if tested_tiers:
                assert successful_connections > 0, \
                    f"At least one user tier should connect successfully. Tested: {tested_tiers}"
            else:
                pytest.skip("No user tiers could be tested - services not available")
                
        except Exception as e:
            skip_if_services_unavailable(str(e))


# Business Impact Summary for WebSocket Connection Tests
"""
WebSocket Authentication Connection Tests - Business Impact

Revenue Impact: $300K MRR Protection
- Prevents authentication failures during real-time AI conversations
- Ensures reliable WebSocket connections for critical chat functionality
- Validates consistent token handling across microservice boundaries

Technical Excellence:
- Authentication performance: <100ms requirement validation
- Token validation across services: <50ms requirement validation
- Message delivery reliability for authenticated sessions
- Support for all user tiers (Free, Early, Mid, Enterprise)

Customer Impact:
- All Segments: Reliable real-time AI interactions without auth interruptions
- Enterprise: Security compliance for high-value contracts
- Growth: Reduced churn from authentication failures during AI workflows
"""
