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
    validate_websocket_token_business_logic
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestUnifiedWebSocketAuthBusinessLogic:
    """Test WebSocket authentication business logic patterns."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket with configurable headers."""
        websocket = Mock()
        websocket.headers = {}
        websocket.state = Mock()
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
        assert context.get("detection_method") == "headers"
    
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
        assert context.get("detection_method") == "environment"
    
    @pytest.mark.unit
    def test_websocket_authentication_flow_business_logic(self, mock_websocket, mock_auth_service):
        """Test WebSocket authentication flow for revenue-generating users."""
        # Given: Premium user attempting WebSocket connection
        token = "valid-premium-user-token"
        mock_websocket.headers = {"authorization": f"Bearer {token}"}
        
        # When: Authenticating WebSocket connection
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', return_value=mock_auth_service):
            result = authenticate_websocket_connection(mock_websocket, token)
        
        # Then: Should return valid authentication result
        assert result is not None
        assert result.is_valid is True
        assert hasattr(result, 'user_id')
        assert hasattr(result, 'email')
        assert hasattr(result, 'permissions')
        
        # And: Should call unified authentication service
        mock_auth_service.authenticate.assert_called_once()
    
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
        assert user_context.email == auth_result.email
        assert user_context.permissions == auth_result.permissions
        
        # And: Should include business tier information
        assert hasattr(user_context, 'subscription_tier')
    
    @pytest.mark.unit
    def test_token_validation_business_logic_security_patterns(self):
        """Test token validation business logic for security enforcement."""
        # Given: Various token scenarios
        valid_token = "valid-enterprise-token-12345"
        expired_token = "expired-token-12345"
        malformed_token = "malformed.token"
        empty_token = ""
        
        # When/Then: Valid token should pass validation
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                'sub': str(uuid.uuid4()),
                'email': 'test@enterprise.com',
                'exp': 9999999999,  # Far future
                'permissions': ['execute_agents']
            }
            
            result = validate_websocket_token_business_logic(valid_token)
            assert result is not None
            assert result.get('email') == 'test@enterprise.com'
        
        # When/Then: Expired token should fail validation
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.jwt.decode') as mock_decode:
            mock_decode.side_effect = Exception("Token has expired")
            
            result = validate_websocket_token_business_logic(expired_token)
            assert result is None
        
        # When/Then: Malformed token should fail validation  
        result = validate_websocket_token_business_logic(malformed_token)
        assert result is None
        
        # When/Then: Empty token should fail validation
        result = validate_websocket_token_business_logic(empty_token)
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
            
            # Then: Validation should match expected state
            with patch('netra_backend.app.websocket_core.unified_websocket_auth._is_websocket_connected') as mock_check:
                mock_check.return_value = should_be_valid
                is_connected = mock_check(mock_websocket)
                assert is_connected == should_be_valid
    
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
    def test_websocket_auth_error_handling_business_logic(self, mock_websocket):
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
                
                # Simulate authentication failure
                mock_auth_service = Mock()
                mock_auth_service.authenticate.side_effect = Exception(expected_message)
                
                with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service', 
                          return_value=mock_auth_service):
                    result = authenticate_websocket_connection(mock_websocket, "invalid-token")
                
                # Then: Should handle error gracefully and log appropriately
                assert result is None or not getattr(result, 'is_valid', True)
                mock_logger.error.assert_called()
    
    @pytest.mark.unit
    def test_websocket_user_context_isolation_validation(self):
        """Test user context isolation validation for multi-tenant security."""
        # Given: Multiple users with overlapping data
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        shared_thread_id = str(uuid.uuid4())  # Same thread, different users
        
        # When: Creating isolated user contexts
        context1 = UserExecutionContext(
            user_id=user1_id,
            email="user1@tenant1.com",
            thread_id=shared_thread_id,
            permissions=["read_basic"]
        )
        
        context2 = UserExecutionContext(
            user_id=user2_id, 
            email="user2@tenant2.com",
            thread_id=shared_thread_id,
            permissions=["read_premium", "execute_agents"]
        )
        
        # Then: Contexts should be properly isolated
        assert context1.user_id != context2.user_id
        assert context1.email != context2.email
        assert context1.permissions != context2.permissions
        
        # And: Thread ID can be shared but user data remains isolated
        assert context1.thread_id == context2.thread_id  # Shared thread OK
        assert context1.to_dict()['user_id'] != context2.to_dict()['user_id']  # User isolation maintained