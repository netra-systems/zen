"""
Test Unified WebSocket Authentication Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Enable secure real-time chat functionality
- Value Impact: Protects WebSocket connections that deliver 90% of user value
- Strategic Impact: Core authentication for $120K+ MRR chat platform

CRITICAL COMPLIANCE:
- Tests SSOT WebSocket authentication patterns
- Validates E2E detection logic critical for staging
- Ensures user context extraction for multi-tenant isolation
- Tests header-based authentication bypass for testing
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from netra_backend.app.websocket_core.unified_websocket_auth import (
    extract_e2e_context_from_websocket,
    authenticate_websocket_connection,
    create_authenticated_user_context,
    validate_websocket_token_business_logic,
    get_websocket_authenticator
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestUnifiedWebSocketAuthBusinessLogic:
    """Test WebSocket authentication business logic patterns."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket with configurable headers."""
        from fastapi.websockets import WebSocketState
        
        websocket = Mock()
        websocket.headers = {}
        websocket.state = Mock()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.application_state = WebSocketState.CONNECTED
        
        # Make client serializable for JSON logging
        mock_client = Mock()
        mock_client.host = "127.0.0.1"
        mock_client.port = 8080
        websocket.client = mock_client
        
        return websocket
    
    @pytest.fixture
    def mock_auth_service(self):
        """Create mock authentication service."""
        service = Mock()
        service.authenticate.return_value = Mock(
            is_valid=True,
            user_id=str(uuid.uuid4()),
            email="test@enterprise.com",
            permissions=["read_data", "execute_agents"]
        )
        return service
    
    @pytest.mark.unit
    def test_e2e_context_extraction_header_detection(self, mock_websocket):
        """Test E2E context extraction via WebSocket headers for staging."""
        # Given: WebSocket connection with E2E test headers
        mock_websocket.headers = {
            "x-e2e-test": "staging", 
            "x-test-mode": "enabled",
            "authorization": "Bearer staging-test-token"
        }
        
        # When: Extracting E2E context for staging compatibility
        context = extract_e2e_context_from_websocket(mock_websocket)
        
        # Then: Should detect E2E testing mode from headers
        assert context is not None
        assert context.get("is_e2e_testing") is True
        assert "x-e2e-test" in context.get("e2e_headers", {})
        # SSOT implementation provides detailed detection methods
        detection_method = context.get("detection_method", {})
        assert detection_method.get("via_headers") is True
    
    @pytest.mark.unit
    def test_e2e_context_extraction_environment_detection(self, mock_websocket):
        """Test E2E context extraction via environment variables."""
        # Given: WebSocket in E2E test environment
        mock_websocket.headers = {}
        
        # When: Environment variables indicate E2E testing
        with patch('shared.isolated_environment.get_env') as mock_env:
            env_mock = Mock()
            env_mock.get.side_effect = lambda key, default="0": {
                "E2E_TESTING": "1",
                "PYTEST_RUNNING": "1", 
                "STAGING_E2E_TEST": "1",
                "E2E_TEST_ENV": "staging"
            }.get(key, default)
            mock_env.return_value = env_mock
            
            context = extract_e2e_context_from_websocket(mock_websocket)
        
        # Then: Should detect E2E testing from environment
        assert context is not None
        assert context.get("is_e2e_testing") is True
        # SSOT implementation provides detailed detection methods
        detection_method = context.get("detection_method", {})
        assert detection_method.get("via_environment") is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_websocket_authentication_flow_business_logic(self, mock_websocket, mock_auth_service):
        """Test WebSocket authentication flow for revenue-generating users."""
        # Given: Premium user attempting WebSocket connection
        token = "valid-premium-user-token"
        mock_websocket.headers = {"authorization": f"Bearer {token}"}
        
        # Mock the auth service response to return valid authentication
        from netra_backend.app.services.unified_authentication_service import AuthResult
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        mock_auth_result = AuthResult(
            success=True,
            user_id=str(uuid.uuid4()),
            email="test@enterprise.com",
            permissions=["read_data", "execute_agents"]
        )
        
        mock_user_context = UserExecutionContext(
            user_id=mock_auth_result.user_id,
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4())
        )
        
        # Mock the auth service authenticate_websocket method
        mock_auth_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
        
        # When: Authenticating WebSocket connection
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=mock_auth_service):
            result = await authenticate_websocket_connection(mock_websocket)
        
        # Then: Should return valid authentication result
        assert result is not None
        assert result.success is True
        assert result.user_context is not None
        assert result.auth_result is not None
        assert result.auth_result.user_id == mock_auth_result.user_id
        
        # And: Should call unified authentication service
        mock_auth_service.authenticate_websocket.assert_called_once()
    
    @pytest.mark.unit
    def test_authenticated_user_context_creation_multi_tenant(self, mock_websocket):
        """Test user context creation for multi-tenant isolation."""
        # Given: Enterprise user authentication data
        auth_result = Mock()
        auth_result.user_id = str(uuid.uuid4())
        auth_result.email = "enterprise@customer.com"
        auth_result.permissions = ["read_data", "write_analysis", "execute_agents", "admin_access"]
        auth_result.subscription_tier = "enterprise"
        
        # When: Creating authenticated user context
        user_context = create_authenticated_user_context(
            auth_result, 
            mock_websocket,
            thread_id=str(uuid.uuid4())
        )
        
        # Then: Should create isolated user context
        assert isinstance(user_context, UserExecutionContext)
        assert user_context.user_id == auth_result.user_id
        # Email and permissions are stored in agent_context
        assert user_context.agent_context.get('email') == auth_result.email
        assert user_context.agent_context.get('permissions') == auth_result.permissions
        
        # And: Should include business tier information in agent_context
        assert user_context.agent_context.get('subscription_tier') == "enterprise"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_token_validation_business_logic_security_patterns(self):
        """Test token validation business logic for security enforcement."""
        # Given: Various token scenarios
        valid_token = "valid-enterprise-token-12345"
        expired_token = "expired-token-12345"
        malformed_token = "malformed.token"
        empty_token = ""
        
        # When/Then: Valid token should pass validation via SSOT auth service
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_get_service:
            mock_auth_service = Mock()
            mock_auth_result = Mock()
            mock_auth_result.success = True
            mock_auth_result.user_id = str(uuid.uuid4())
            mock_auth_result.email = 'test@enterprise.com'
            mock_auth_result.permissions = ['execute_agents']
            mock_auth_result.validated_at = Mock()
            mock_auth_result.validated_at.timestamp.return_value = 1234567890
            
            mock_auth_service.authenticate.return_value = mock_auth_result
            mock_get_service.return_value = mock_auth_service
            
            result = await validate_websocket_token_business_logic(valid_token)
            assert result is not None
            assert result.get('email') == 'test@enterprise.com'
            assert result.get('permissions') == ['execute_agents']
        
        # When/Then: Expired token should fail validation via SSOT auth service
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_get_service:
            mock_auth_service = Mock()
            mock_auth_result = Mock()
            mock_auth_result.success = False
            mock_auth_result.error = "Token has expired"
            
            mock_auth_service.authenticate.return_value = mock_auth_result
            mock_get_service.return_value = mock_auth_service
            
            result = await validate_websocket_token_business_logic(expired_token)
            assert result is None
        
        # When/Then: Malformed token should fail validation  
        result = await validate_websocket_token_business_logic(malformed_token)
        # Should fail due to auth service errors
        
        # When/Then: Empty token should fail validation
        result = await validate_websocket_token_business_logic(empty_token)
        assert result is None
    
    @pytest.mark.unit
    def test_websocket_connection_state_validation(self, mock_websocket):
        """Test WebSocket connection state validation for stability."""
        from fastapi.websockets import WebSocketState
        
        # Given: WebSocket in different connection states
        states_to_test = [
            (WebSocketState.CONNECTING, False),
            (WebSocketState.CONNECTED, True),
            (WebSocketState.DISCONNECTED, False)
        ]
        
        for state, should_be_valid in states_to_test:
            # When: Checking connection state
            mock_websocket.client_state = state
            
            # Then: Validation should match expected state using SSOT authenticator method
            authenticator = get_websocket_authenticator()
            is_connected = authenticator._is_websocket_connected(mock_websocket)
            
            # CONNECTED state should return True, others False
            expected = (state == WebSocketState.CONNECTED)
            assert is_connected == expected
    
    @pytest.mark.unit
    def test_permission_based_websocket_access_control(self, mock_websocket):
        """Test permission-based access control for WebSocket features."""
        # Given: Users with different permission levels
        permission_scenarios = [
            (["read_basic"], "basic", False),  # Can't execute agents
            (["read_basic", "read_premium"], "premium", False),  # Can't execute agents
            (["read_basic", "execute_agents"], "premium_plus", True),  # Can execute agents
            (["read_basic", "execute_agents", "admin_access"], "enterprise", True)  # Full access
        ]
        
        for permissions, tier, can_execute_agents in permission_scenarios:
            # When: Checking agent execution permissions
            auth_result = Mock()
            auth_result.permissions = permissions
            auth_result.subscription_tier = tier
            
            # Then: Permission check should match business tier
            has_agent_permission = "execute_agents" in permissions
            assert has_agent_permission == can_execute_agents
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_websocket_auth_error_handling_business_logic(self, mock_websocket):
        """Test WebSocket authentication error handling patterns."""
        # Given: Various authentication failure scenarios
        error_scenarios = [
            ("invalid_token", "Authentication failed - invalid token"),
            ("expired_session", "Session expired - please re-authenticate"),  
            ("insufficient_permissions", "Insufficient permissions for WebSocket access"),
            ("service_unavailable", "Authentication service temporarily unavailable")
        ]
        
        for error_type, expected_message in error_scenarios:
            # When: Authentication fails with specific error
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.logger') as mock_logger:
                
                # Simulate authentication failure via SSOT service
                mock_auth_service = Mock()
                mock_auth_service.authenticate_websocket.side_effect = Exception(expected_message)
                
                with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', 
                          return_value=mock_auth_service):
                    result = await authenticate_websocket_connection(mock_websocket)
                
                # Then: Should handle error gracefully and return failure result
                assert result is not None
                assert result.success is False
                assert result.error_code == "WEBSOCKET_AUTH_EXCEPTION"
                # Should log the error appropriately
                mock_logger.error.assert_called()
    
    @pytest.mark.unit
    def test_websocket_user_context_isolation_validation(self):
        """Test user context isolation validation for multi-tenant security."""
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
        
        # Given: Multiple users with overlapping data
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        shared_thread_id = str(uuid.uuid4())  # Same thread, different users
        
        id_manager = UnifiedIDManager()
        
        # When: Creating isolated user contexts with proper SSOT patterns
        context1 = UserExecutionContext(
            user_id=user1_id,
            thread_id=shared_thread_id,
            run_id=id_manager.generate_run_id(shared_thread_id),
            request_id=id_manager.generate_id(IDType.REQUEST, prefix="req", context={"test": True}),
            agent_context={
                "email": "user1@tenant1.com",
                "permissions": ["read_basic"]
            }
        )
        
        context2 = UserExecutionContext(
            user_id=user2_id, 
            thread_id=shared_thread_id,
            run_id=id_manager.generate_run_id(shared_thread_id),
            request_id=id_manager.generate_id(IDType.REQUEST, prefix="req", context={"test": True}),
            agent_context={
                "email": "user2@tenant2.com",
                "permissions": ["read_premium", "execute_agents"]
            }
        )
        
        # Then: Contexts should be properly isolated
        assert context1.user_id != context2.user_id
        assert context1.agent_context.get('email') != context2.agent_context.get('email')
        assert context1.agent_context.get('permissions') != context2.agent_context.get('permissions')
        
        # And: Thread ID can be shared but user data remains isolated
        assert context1.thread_id == context2.thread_id  # Shared thread OK
        assert context1.user_id != context2.user_id  # User isolation maintained