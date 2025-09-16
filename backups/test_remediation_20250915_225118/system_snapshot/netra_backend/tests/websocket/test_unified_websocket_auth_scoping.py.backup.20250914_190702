"""
Unit Tests for WebSocket Authentication Variable Scoping Bug

This test suite validates the critical variable scoping bug in unified_websocket_auth.py
where `is_production` is used on line 119 but declared on line 151.

Business Value Justification:
- Segment: Platform/Internal - Critical Bug Fix
- Business Goal: Ensure WebSocket authentication works in staging environment
- Value Impact: Prevents GOLDEN PATH failures in staging that block user chat
- Revenue Impact: Enables reliable staging testing which prevents production issues

CRITICAL: These tests MUST FAIL before the fix and PASS after the fix.
"""

import pytest
import json
import unittest.mock
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from netra_backend.app.websocket_core.unified_websocket_auth import (
    extract_e2e_context_from_websocket,
    UnifiedWebSocketAuthenticator,
    authenticate_websocket_connection,
    WebSocketAuthResult
)


class TestVariableScopingBug:
    """Test suite specifically for the variable scoping bug on lines 119/151."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = Mock(spec=WebSocket)
        websocket.headers = {}
        websocket.client = Mock()
        websocket.client.host = "localhost"
        websocket.client.port = 8000
        websocket.client_state = WebSocketState.CONNECTED
        return websocket
    
    @pytest.fixture
    def staging_environment_vars(self):
        """Environment variables that trigger staging E2E detection."""
        return {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging-project",
            "K_SERVICE": "netra-staging-backend",
            "E2E_TESTING": "0",  # Not explicitly enabled
            "STAGING_E2E_TEST": "0",  # Not explicitly enabled
            "PYTEST_RUNNING": "1"
        }
    
    def test_production_environment_detection(self, mock_websocket):
        """Test that production environment is correctly detected."""
        production_vars = {
            "ENVIRONMENT": "production",
            "GOOGLE_CLOUD_PROJECT": "netra-production-project",
            "K_SERVICE": "netra-prod-backend"
        }
        
        with patch('shared.isolated_environment.get_env', return_value=production_vars):
            e2e_context = extract_e2e_context_from_websocket(mock_websocket)
            
            # Production should never allow E2E bypass
            assert e2e_context is None, "Production environment should never allow E2E bypass"
    
    def test_staging_environment_detection(self, mock_websocket):
        """Test that staging environment is correctly detected."""
        staging_vars = {
            "ENVIRONMENT": "staging", 
            "GOOGLE_CLOUD_PROJECT": "netra-staging-project",
            "K_SERVICE": "netra-staging-backend"
        }
        
        with patch('shared.isolated_environment.get_env', return_value=staging_vars):
            e2e_context = extract_e2e_context_from_websocket(mock_websocket)
            
            # This test documents current expected behavior
            # When bug is fixed, staging should allow E2E bypass with proper headers
            if e2e_context:
                assert e2e_context["is_e2e_testing"] is True
                assert e2e_context["environment"] == "staging"
    
    def test_local_environment_detection(self, mock_websocket):
        """Test that local development environment is correctly detected."""
        local_vars = {
            "ENVIRONMENT": "local",
            "GOOGLE_CLOUD_PROJECT": "",
            "K_SERVICE": "",
            "E2E_TESTING": "1"  # Explicitly enabled for local
        }
        
        with patch('shared.isolated_environment.get_env', return_value=local_vars):
            e2e_context = extract_e2e_context_from_websocket(mock_websocket)
            
            assert e2e_context is not None
            assert e2e_context["is_e2e_testing"] is True
            assert e2e_context["environment"] == "local"
    
    @pytest.mark.critical
    def test_e2e_context_with_staging_triggers_bug(self, mock_websocket):
        """
        CRITICAL TEST: This test MUST FAIL before the fix due to UnboundLocalError.
        
        This reproduces the exact conditions that cause the variable scoping bug:
        - Staging environment with "staging" in project name
        - E2E headers present to trigger is_e2e_via_headers = True
        - This causes is_staging_env_for_e2e evaluation on line 119
        - Which uses is_production before it's declared on line 151
        """
        # Set up exact staging environment that triggers the scoping bug
        staging_vars = {
            "ENVIRONMENT": "staging", 
            "GOOGLE_CLOUD_PROJECT": "netra-staging-test-project",  # Contains "staging"
            "K_SERVICE": "netra-backend-staging",  # Contains "staging"
            "E2E_TESTING": "0",  # Not explicitly set
            "STAGING_E2E_TEST": "0"  # Not explicitly set
        }
        
        # Add E2E headers that trigger is_e2e_via_headers = True
        mock_websocket.headers = {
            "x-e2e-test": "true",  # Contains "e2e"
            "test-environment": "staging"  # Contains "test"
        }
        
        with patch('shared.isolated_environment.get_env', return_value=staging_vars):
            # This should raise UnboundLocalError on line 119 before the fix
            try:
                e2e_context = extract_e2e_context_from_websocket(mock_websocket)
                
                # If we get here without UnboundLocalError, check if bug is already fixed
                if e2e_context is not None:
                    print(" PASS:  BUG APPEARS TO BE FIXED: E2E context created successfully")
                    assert e2e_context.get("is_e2e_testing") is True
                    assert e2e_context.get("environment") == "staging"
                else:
                    # If no E2E context but no error, document the behavior
                    print("[U+2139][U+FE0F] NO E2E CONTEXT: Staging environment did not create E2E context")
                
            except UnboundLocalError as e:
                # This is the expected error before the fix
                assert "is_production" in str(e), f"Expected UnboundLocalError for is_production, got: {e}"
                pytest.fail(f" ALERT:  CRITICAL BUG REPRODUCED: {e} - is_production used before declaration on line 119")
            except NameError as e:
                # Also catch NameError which is another form of the same bug
                if "is_production" in str(e):
                    pytest.fail(f" ALERT:  CRITICAL BUG REPRODUCED: {e} - is_production variable scoping error")
                else:
                    raise
    
    def test_variable_declaration_order_validation(self, mock_websocket):
        """Test that validates the specific variable declaration order issue."""
        # Environment that triggers staging auto-detection branch
        problematic_vars = {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging-project", 
            "K_SERVICE": "netra-staging-service",
            "E2E_TESTING": "0"
        }
        
        # Headers that cause E2E detection
        mock_websocket.headers = {"x-test-mode": "e2e"}
        
        with patch('shared.isolated_environment.get_env', return_value=problematic_vars):
            # This validates the specific code path where is_production is used before declaration
            try:
                e2e_context = extract_e2e_context_from_websocket(mock_websocket)
                
                # If successful, verify the context contains expected staging E2E data
                if e2e_context:
                    assert e2e_context["environment"] == "staging"
                    assert "detection_method" in e2e_context
                    
            except NameError as e:
                # Catch the specific variable scoping error
                if "is_production" in str(e):
                    pytest.fail(f"Variable scoping bug detected: {e}")
                else:
                    raise
    
    def test_k_service_naming_variations(self, mock_websocket):
        """Test different K_SERVICE naming patterns that could trigger the bug."""
        k_service_variations = [
            "netra-staging-backend",
            "staging-netra-api", 
            "netra-backend-staging",
            "staging-service",
            "netra-staging"
        ]
        
        for k_service in k_service_variations:
            staging_vars = {
                "ENVIRONMENT": "staging",
                "GOOGLE_CLOUD_PROJECT": "netra-staging",
                "K_SERVICE": k_service
            }
            
            mock_websocket.headers = {"test-header": "staging"}
            
            with patch('shared.isolated_environment.get_env', return_value=staging_vars):
                try:
                    e2e_context = extract_e2e_context_from_websocket(mock_websocket)
                    
                    # Document which K_SERVICE patterns work
                    if e2e_context:
                        assert e2e_context["k_service"] == k_service
                        assert "staging" in k_service.lower()
                        
                except UnboundLocalError as e:
                    if "is_production" in str(e):
                        pytest.fail(f"Variable scoping bug with K_SERVICE={k_service}: {e}")

    def test_concurrent_environment_detection(self, mock_websocket):
        """Test concurrent test markers that could interact with the scoping bug."""
        concurrent_vars = {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging",
            "K_SERVICE": "staging-backend",
            "PYTEST_XDIST_WORKER": "gw0",  # pytest-xdist marker
            "PYTEST_CURRENT_TEST": "test_websocket_auth_scoping.py::test_staging",
            "RACE_CONDITION_TEST_MODE": "1"
        }
        
        with patch('shared.isolated_environment.get_env', return_value=concurrent_vars):
            try:
                e2e_context = extract_e2e_context_from_websocket(mock_websocket)
                
                if e2e_context:
                    # Verify concurrent test detection
                    assert e2e_context["is_e2e_testing"] is True
                    assert e2e_context["enhanced_detection"] is True
                    
            except UnboundLocalError as e:
                if "is_production" in str(e):
                    pytest.fail(f"Concurrent testing triggers scoping bug: {e}")


class TestWebSocketAuthenticatorScoping:
    """Test the main authenticator class with scoping conditions."""
    
    @pytest.fixture
    def authenticator(self):
        """Create authenticator instance for testing."""
        return UnifiedWebSocketAuthenticator()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for authenticator tests."""
        websocket = Mock(spec=WebSocket)
        websocket.headers = {}
        websocket.client = Mock()
        websocket.client.host = "test.local"
        websocket.client.port = 8000
        websocket.client_state = WebSocketState.CONNECTED
        return websocket
    
    @pytest.mark.asyncio
    async def test_authenticate_with_scoping_bug_conditions(self, authenticator, mock_websocket):
        """Test authentication under conditions that trigger the scoping bug."""
        # Set up environment that triggers the bug
        bug_trigger_vars = {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging-test",
            "K_SERVICE": "backend-staging",
            "E2E_TESTING": "0"
        }
        
        # Mock the auth service to avoid external dependencies
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
            mock_auth_instance = AsyncMock()
            mock_auth_service.return_value = mock_auth_instance
            
            # Mock successful auth to focus on scoping bug
            from netra_backend.app.services.unified_authentication_service import AuthResult
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            mock_auth_result = Mock(spec=AuthResult)
            mock_auth_result.success = True
            mock_auth_result.user_id = "test_user_123"
            mock_auth_result.email = "test@staging.com"
            mock_auth_result.permissions = ["execute_agents"]
            mock_auth_result.error = None
            mock_auth_result.error_code = None
            mock_auth_result.metadata = {}
            
            mock_user_context = Mock(spec=UserExecutionContext)
            mock_user_context.user_id = "test_user_123"
            mock_user_context.websocket_client_id = "ws_client_123"
            
            mock_auth_instance.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
            
            # Patch environment to trigger scoping bug
            with patch('shared.isolated_environment.get_env', return_value=bug_trigger_vars):
                try:
                    # This should trigger the scoping bug during E2E context extraction
                    result = await authenticator.authenticate_websocket_connection(mock_websocket)
                    
                    # If we get here, the bug might be fixed or not triggered
                    assert isinstance(result, WebSocketAuthResult)
                    
                except UnboundLocalError as e:
                    if "is_production" in str(e):
                        pytest.fail(f"Authentication failed due to variable scoping bug: {e}")
                    else:
                        raise

    @pytest.mark.asyncio 
    async def test_error_handling_with_scoping_conditions(self, authenticator, mock_websocket):
        """Test error handling when scoping bug conditions are present."""
        error_trigger_vars = {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging",
            "K_SERVICE": "staging-backend"
        }
        
        # Add headers that trigger E2E detection
        mock_websocket.headers = {"x-e2e-test": "true"}
        
        with patch('shared.isolated_environment.get_env', return_value=error_trigger_vars):
            # Mock auth service to raise an error
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
                mock_auth_instance = AsyncMock()
                mock_auth_service.return_value = mock_auth_instance
                mock_auth_instance.authenticate_websocket.side_effect = Exception("Auth service error")
                
                try:
                    result = await authenticator.authenticate_websocket_connection(mock_websocket)
                    
                    # Should get an error result, not an exception
                    assert not result.success
                    assert result.error_code == "WEBSOCKET_AUTH_EXCEPTION"
                    
                except UnboundLocalError as e:
                    if "is_production" in str(e):
                        pytest.fail(f"Error handling failed due to scoping bug: {e}")
                    else:
                        raise


class TestBackwardCompatibilityWithScoping:
    """Test backward compatibility functions under scoping bug conditions."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket for compatibility tests.""" 
        websocket = Mock(spec=WebSocket)
        websocket.headers = {"test-header": "staging"}
        websocket.client = Mock()
        websocket.client.host = "staging.test.com"
        websocket.client.port = 443
        websocket.client_state = WebSocketState.CONNECTED
        return websocket
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket_connection_with_scoping_bug(self, mock_websocket):
        """Test the backward compatibility function under scoping bug conditions."""
        scoping_bug_vars = {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging-project",
            "K_SERVICE": "netra-staging-backend",
            "E2E_TESTING": "0",
            "STAGING_E2E_TEST": "0"
        }
        
        with patch('shared.isolated_environment.get_env', return_value=scoping_bug_vars):
            # Mock the unified auth service
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth_service:
                mock_auth_instance = AsyncMock()
                mock_auth_service.return_value = mock_auth_instance
                
                # Mock successful authentication
                from netra_backend.app.services.unified_authentication_service import AuthResult
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                
                mock_auth_result = Mock(spec=AuthResult)
                mock_auth_result.success = True
                mock_auth_result.user_id = "scoping_test_user"
                mock_auth_result.email = "test@staging.com"
                mock_auth_result.permissions = ["execute_agents"]
                mock_auth_result.error = None
                mock_auth_result.error_code = None
                mock_auth_result.metadata = {}
                
                mock_user_context = Mock(spec=UserExecutionContext)
                mock_user_context.user_id = "scoping_test_user"
                mock_user_context.websocket_client_id = "ws_scoping_test"
                
                mock_auth_instance.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
                
                try:
                    # Test the backward compatibility function
                    result = await authenticate_websocket_connection(
                        websocket=mock_websocket,
                        token="test_token_staging",
                        e2e_context=None
                    )
                    
                    assert isinstance(result, WebSocketAuthResult)
                    if result.success:
                        assert result.user_context.user_id == "scoping_test_user"
                    
                except UnboundLocalError as e:
                    if "is_production" in str(e):
                        pytest.fail(f"Backward compatibility function failed due to scoping bug: {e}")
                    else:
                        raise


if __name__ == "__main__":
    # Run the critical scoping bug test
    pytest.main([__file__, "-v", "-k", "test_e2e_context_with_staging_triggers_bug"])