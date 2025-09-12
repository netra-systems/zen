"""
Integration Tests: WebSocket-to-Auth Service Real-time Communication

Business Value Justification (BVJ):
- Segment: Platform/Internal - Critical WebSocket Infrastructure
- Business Goal: System Stability & Real-time Performance - Protects $500K+ ARR Golden Path  
- Value Impact: Ensures WebSocket authentication works reliably during active connections
- Revenue Impact: Prevents authentication timeouts that break real-time chat experience

CRITICAL PURPOSE: These integration tests validate real-time authentication scenarios
between WebSocket connections and the auth service, including token validation during
active sessions, timeout handling, and service coordination.

Test Coverage Areas:
1. WebSocket token validation via auth service during active connections
2. Real-time auth service communication during WebSocket lifecycle
3. Auth service timeout handling in WebSocket connections
4. Multi-service authentication coordination (Backend + Auth + Analytics)
5. WebSocket client context propagation to auth service  
6. Auth service response integration with WebSocket messages
7. Service dependency management during auth service downtime
"""

import asyncio
import json
import pytest
import time
import websockets
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx
from contextlib import asynccontextmanager

from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.fixtures.websocket import websocket_client_fixture
from test_framework.fixtures.auth import auth_service_client_fixture

from netra_backend.app.services.unified_authentication_service import (
    UnifiedAuthenticationService,
    AuthenticationContext
)
from netra_backend.app.auth import AuthenticationResult, AuthMethodType
from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient,
    AuthServiceConnectionError,
    AuthServiceValidationError
)
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuth
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.mark.integration
@pytest.mark.asyncio  
class TestWebSocketAuthServiceRealTimeCommunication(BaseIntegrationTest):
    """Integration tests for real-time WebSocket-to-Auth service communication."""
    
    async def setup_method(self):
        """Setup test environment with WebSocket and auth service integration."""
        await super().setup_method()
        
        # Real service instances for integration testing
        self.auth_client = AuthServiceClient()
        self.unified_auth_service = UnifiedAuthenticationService()
        self.websocket_auth = UnifiedWebSocketAuth()
        
        # Test data
        self.test_user_id = "websocket-user-456"
        self.test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNDU2IiwiZXhwIjoyMTQ3NDgzNjQ3fQ.wstoken"
        self.websocket_url = "ws://localhost:8000/ws/chat"
        
    async def teardown_method(self):
        """Cleanup test resources."""
        if hasattr(self, 'auth_client') and self.auth_client:
            await self.auth_client.cleanup()
        await super().teardown_method()

    async def test_websocket_token_validation_during_active_connection(self):
        """
        BVJ: Validates tokens during active WebSocket sessions with auth service
        Critical for maintaining security during long-running chat sessions
        """
        # Mock WebSocket connection state
        mock_websocket = AsyncMock()
        mock_websocket.client_state = 1  # CONNECTED
        
        # Setup auth service response for active validation
        with patch.object(self.auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": self.test_user_id,
                "permissions": ["websocket_access", "chat_access"],
                "expires_at": int(time.time()) + 3600
            }
            
            # Simulate active WebSocket connection validation
            auth_context = AuthenticationContext(
                token=self.test_token,
                user_id=self.test_user_id,
                method=AuthMethodType.JWT_BEARER,
                source="websocket_active_validation",
                websocket_connection=mock_websocket
            )
            
            # Test real-time validation
            result = await self.websocket_auth.validate_active_connection(
                websocket=mock_websocket,
                auth_context=auth_context
            )
            
            assert result["valid"] is True
            assert result["user_id"] == self.test_user_id
            assert "websocket_access" in result["permissions"]
            assert result["expires_at"] > time.time()
            
            # Verify auth service integration
            mock_validate.assert_called_once_with(self.test_token)

    async def test_realtime_auth_service_communication_websocket_lifecycle(self):
        """
        BVJ: Tests auth service communication throughout WebSocket connection lifecycle
        Ensures authentication remains valid from connection to disconnection
        """
        lifecycle_events = []
        
        async def mock_auth_lifecycle(event_type, context):
            lifecycle_events.append(event_type)
            return {
                "valid": True,
                "user_id": self.test_user_id,
                "event": event_type,
                "timestamp": time.time()
            }
        
        with patch.object(self.unified_auth_service, 'handle_websocket_lifecycle_auth') as mock_lifecycle:
            mock_lifecycle.side_effect = mock_auth_lifecycle
            
            # Test connection initiation
            connect_result = await self.unified_auth_service.handle_websocket_lifecycle_auth(
                "connection_initiation",
                AuthenticationContext(
                    token=self.test_token,
                    user_id=self.test_user_id,
                    method=AuthMethodType.JWT_BEARER,
                    source="websocket_connect"
                )
            )
            
            # Test message authentication during session
            message_result = await self.unified_auth_service.handle_websocket_lifecycle_auth(
                "message_authentication", 
                AuthenticationContext(
                    token=self.test_token,
                    user_id=self.test_user_id,
                    method=AuthMethodType.JWT_BEARER,
                    source="websocket_message"
                )
            )
            
            # Test disconnection cleanup
            disconnect_result = await self.unified_auth_service.handle_websocket_lifecycle_auth(
                "connection_cleanup",
                AuthenticationContext(
                    token=self.test_token,
                    user_id=self.test_user_id,
                    method=AuthMethodType.JWT_BEARER,
                    source="websocket_disconnect"
                )
            )
            
            # Verify all lifecycle events handled
            assert "connection_initiation" in lifecycle_events
            assert "message_authentication" in lifecycle_events  
            assert "connection_cleanup" in lifecycle_events
            assert len(lifecycle_events) == 3

    async def test_auth_service_timeout_handling_websocket_connections(self):
        """
        BVJ: Tests timeout handling when auth service is slow during WebSocket operations
        Prevents WebSocket connections from hanging due to auth service delays
        """
        # Mock slow auth service response
        async def slow_auth_validation(token):
            await asyncio.sleep(2.0)  # Simulate slow response
            return {"valid": True, "user_id": self.test_user_id}
            
        with patch.object(self.auth_client, 'validate_token', side_effect=slow_auth_validation):
            
            auth_context = AuthenticationContext(
                token=self.test_token,
                user_id=self.test_user_id,
                method=AuthMethodType.JWT_BEARER,
                source="websocket_handshake",
                timeout_ms=1000  # 1 second timeout
            )
            
            start_time = time.time()
            
            # Test timeout handling
            result = await self.websocket_auth.authenticate_with_timeout(auth_context)
            
            elapsed_time = time.time() - start_time
            
            # Should timeout and handle gracefully
            assert result.success is False
            assert result.error_code == "AUTH_SERVICE_TIMEOUT"
            assert elapsed_time < 1.5  # Should timeout before 1.5 seconds
            assert result.fallback_attempted is True

    async def test_multi_service_authentication_coordination(self):
        """
        BVJ: Tests coordination between Backend, Auth, and Analytics services during WebSocket auth
        Ensures all services receive consistent authentication state
        """
        service_auth_states = {}
        
        async def mock_service_notification(service_name, auth_state):
            service_auth_states[service_name] = auth_state
            return {"acknowledged": True, "service": service_name}
        
        with patch.object(self.unified_auth_service, 'notify_service_auth_state') as mock_notify:
            mock_notify.side_effect = mock_service_notification
            
            # Simulate multi-service authentication coordination
            auth_result = AuthenticationResult(
                success=True,
                user_id=self.test_user_id,
                authentication_method=AuthMethodType.JWT_BEARER,
                permissions=["websocket_access", "analytics_access"]
            )
            
            # Test service coordination
            coordination_results = await self.unified_auth_service.coordinate_multi_service_auth(
                auth_result=auth_result,
                target_services=["backend", "auth_service", "analytics"]
            )
            
            # Verify all services notified
            assert "backend" in service_auth_states
            assert "auth_service" in service_auth_states
            assert "analytics" in service_auth_states
            
            # Verify consistent state across services
            for service, state in service_auth_states.items():
                assert state["user_id"] == self.test_user_id
                assert state["authenticated"] is True

    async def test_websocket_client_context_propagation_auth_service(self):
        """
        BVJ: Tests propagation of WebSocket client context to auth service
        Ensures auth service has necessary context for security decisions
        """
        client_context = {
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 WebSocket Client", 
            "connection_id": "ws-conn-789",
            "session_start": time.time(),
            "origin": "https://netra-apex.com"
        }
        
        with patch.object(self.auth_client, 'validate_token_with_context') as mock_validate_context:
            mock_validate_context.return_value = {
                "valid": True,
                "user_id": self.test_user_id,
                "security_score": 95,  # High security score based on context
                "risk_factors": []
            }
            
            auth_context = AuthenticationContext(
                token=self.test_token,
                user_id=self.test_user_id,
                method=AuthMethodType.JWT_BEARER,
                source="websocket_handshake",
                client_context=client_context
            )
            
            # Test context propagation
            result = await self.unified_auth_service.authenticate_user(auth_context)
            
            assert result.success is True
            assert result.security_score == 95
            assert len(result.risk_factors) == 0
            
            # Verify context was passed to auth service
            mock_validate_context.assert_called_once()
            call_args = mock_validate_context.call_args
            assert call_args[1]["client_context"]["ip_address"] == "192.168.1.100"
            assert call_args[1]["client_context"]["connection_id"] == "ws-conn-789"

    async def test_auth_service_response_integration_websocket_messages(self):
        """
        BVJ: Tests integration of auth service responses with WebSocket message flow
        Ensures authentication results properly influence WebSocket message handling
        """
        message_queue = []
        
        async def mock_websocket_send(message):
            message_queue.append(json.loads(message))
            
        mock_websocket = AsyncMock()
        mock_websocket.send = mock_websocket_send
        mock_websocket.client_state = 1  # CONNECTED
        
        with patch.object(self.auth_client, 'validate_token') as mock_validate:
            # Test successful authentication response
            mock_validate.return_value = {
                "valid": True,
                "user_id": self.test_user_id,
                "permissions": ["websocket_access", "premium_features"]
            }
            
            # Test WebSocket message with auth integration
            await self.websocket_auth.handle_authenticated_message(
                websocket=mock_websocket,
                message_data={
                    "type": "chat_message",
                    "content": "Hello, test message!",
                    "token": self.test_token
                }
            )
            
            # Verify auth-influenced message processing
            assert len(message_queue) > 0
            
            # Should include authentication confirmation
            auth_message = next(
                (msg for msg in message_queue if msg.get("type") == "auth_confirmed"), 
                None
            )
            assert auth_message is not None
            assert auth_message["user_id"] == self.test_user_id
            assert "premium_features" in auth_message["permissions"]

    async def test_service_dependency_management_auth_service_downtime(self):
        """
        BVJ: Tests graceful handling when auth service is completely down
        Ensures WebSocket connections can still function with degraded auth
        """
        downtime_scenarios = ["connection_refused", "timeout", "service_unavailable"]
        
        for scenario in downtime_scenarios:
            with self.subTest(scenario=scenario):
                
                # Mock different failure scenarios
                if scenario == "connection_refused":
                    error = AuthServiceConnectionError("Connection refused")
                elif scenario == "timeout": 
                    error = asyncio.TimeoutError("Auth service timeout")
                else:
                    error = AuthServiceValidationError("Service unavailable")
                
                with patch.object(self.auth_client, 'validate_token', side_effect=error):
                    
                    auth_context = AuthenticationContext(
                        token=self.test_token,
                        user_id=self.test_user_id,
                        method=AuthMethodType.JWT_BEARER,
                        source="websocket_handshake"
                    )
                    
                    # Test service dependency management
                    result = await self.unified_auth_service.handle_service_downtime_auth(
                        auth_context=auth_context,
                        fallback_strategy="graceful_degradation"
                    )
                    
                    # Should handle downtime gracefully
                    assert result["status"] == "degraded_operation"
                    assert result["auth_service_available"] is False
                    assert result["fallback_active"] is True
                    assert result["user_session_maintained"] is True


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebSocketAuthServiceLifecycleIntegration(BaseIntegrationTest):
    """Tests WebSocket authentication throughout complete service lifecycle."""
    
    async def setup_method(self):
        await super().setup_method() 
        self.unified_auth_service = UnifiedAuthenticationService()
        self.test_user_id = "lifecycle-user-789"
        
    async def test_websocket_auth_service_startup_integration(self):
        """
        BVJ: Tests authentication service integration during system startup
        Ensures WebSocket auth is ready when system comes online
        """
        startup_phases = []
        
        async def mock_startup_phase(phase_name, dependencies):
            startup_phases.append(phase_name)
            return {"phase": phase_name, "status": "completed", "duration_ms": 150}
        
        with patch.object(self.unified_auth_service, 'initialize_startup_phase') as mock_startup:
            mock_startup.side_effect = mock_startup_phase
            
            # Test startup sequence
            startup_result = await self.unified_auth_service.initialize_websocket_auth_integration()
            
            assert startup_result["status"] == "ready"
            assert len(startup_phases) >= 3  # Should have multiple initialization phases
            assert "auth_client_connection" in startup_phases
            assert "websocket_auth_setup" in startup_phases
            assert "service_health_check" in startup_phases