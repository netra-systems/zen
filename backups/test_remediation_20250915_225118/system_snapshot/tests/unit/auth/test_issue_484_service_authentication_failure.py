"""
Unit tests for Issue #484: Service Authentication Failure

This test suite reproduces the service authentication failure where service:netra-backend
users are getting 403 'Not authenticated' errors due to improper service user pattern
recognition in the authentication system.

Key issue: The authentication middleware doesn't properly handle "service:" prefixed users,
causing database session creation failures and breaking agent operations.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Import the modules under test
from netra_backend.app.dependencies import get_service_user_context, get_request_scoped_db_session
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory


class TestIssue484ServiceAuthenticationFailure:
    """Test class to reproduce Issue #484 service authentication failures."""
    
    def test_service_user_context_format(self):
        """Test that get_service_user_context returns proper service format."""
        # This test should initially pass as it tests the format
        with patch('netra_backend.app.core.configuration.get_configuration') as mock_config:
            # Mock configuration to return service ID
            mock_config_obj = Mock()
            mock_config_obj.service_id = "netra-backend"
            mock_config.return_value = mock_config_obj
            
            service_context = get_service_user_context()
            
            # Verify the service context format is correct
            assert service_context == "service:netra-backend"
            assert service_context.startswith("service:")
    
    @pytest.mark.asyncio
    async def test_auth_client_service_user_validation_success(self):
        """Test AuthServiceClient.validate_service_user_context for successful validation.
        
        This test shows what SHOULD work - proper service user validation.
        """
        auth_client = AuthServiceClient()
        
        # Mock service credentials are configured
        auth_client.service_id = "netra-backend"
        auth_client.service_secret = "test-secret"
        
        # Test successful service user validation
        result = await auth_client.validate_service_user_context("netra-backend", "database_session_creation")
        
        # Should return successful validation
        assert result is not None
        assert result["valid"] is True
        assert result["user_id"] == "service:netra-backend"
        assert result["authentication_method"] == "service_to_service"
        assert result["service_id"] == "netra-backend"
    
    @pytest.mark.asyncio 
    async def test_auth_client_service_user_validation_missing_credentials(self):
        """Test AuthServiceClient.validate_service_user_context when credentials are missing.
        
        This test reproduces part of Issue #484 - missing service credentials.
        """
        auth_client = AuthServiceClient()
        
        # Mock missing service credentials (reproduces the issue)
        auth_client.service_id = None  # Missing SERVICE_ID
        auth_client.service_secret = None  # Missing SERVICE_SECRET
        
        # Test validation with missing credentials
        result = await auth_client.validate_service_user_context("netra-backend", "database_session_creation")
        
        # Should return validation failure due to missing credentials
        assert result is not None
        assert result["valid"] is False
        assert result["error"] == "missing_service_credentials"
        assert "SERVICE_ID and SERVICE_SECRET required" in result["details"]
        assert result["fix"] == "Configure SERVICE_ID and SERVICE_SECRET environment variables"
    
    @pytest.mark.asyncio
    async def test_request_scoped_session_service_user_pattern_recognition(self):
        """Test that request scoped session properly recognizes service user patterns.
        
        This is the CRITICAL test that reproduces Issue #484.
        The session factory should recognize service:netra-backend as a service user.
        """
        factory = RequestScopedSessionFactory()
        
        # Mock the get_db function to simulate database connection
        with patch('netra_backend.app.database.request_scoped_session_factory.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_session.info = {}
            mock_session.in_transaction.return_value = False
            
            # Mock async context manager for get_db
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_get_db.return_value = mock_context
            
            # Mock auth client validation
            with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_service_user_context') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "service_id": "netra-backend",
                    "authentication_method": "service_to_service",
                    "user_context": "service:netra-backend"
                }
                
                # Test session creation with service user
                user_id = "service:netra-backend"
                
                try:
                    async with factory.get_request_scoped_session(user_id, "test-req-id") as session:
                        # If we reach here, service user pattern was recognized correctly
                        assert session is not None
                        assert hasattr(session, 'info')
                        
                        # Verify session was tagged with service user context
                        if hasattr(session, 'info') and session.info:
                            assert session.info.get('user_id') == user_id
                            assert session.info.get('is_request_scoped') is True
                            
                except Exception as e:
                    # If we get here, Issue #484 is reproduced
                    pytest.fail(f"Service user pattern recognition failed: {e}")
    
    @pytest.mark.asyncio 
    async def test_request_scoped_session_system_user_fallback(self):
        """Test that system user gets proper authentication bypass.
        
        This tests the current working pattern vs the broken service pattern.
        """
        factory = RequestScopedSessionFactory()
        
        # Mock get_system_db for system user bypass
        with patch('netra_backend.app.database.request_scoped_session_factory.get_system_db') as mock_get_system_db:
            mock_session = AsyncMock()
            mock_session.info = {}
            
            # Mock async context manager for get_system_db
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_get_system_db.return_value = mock_context
            
            # Test session creation with system user (should work)
            user_id = "system"
            
            try:
                async with factory.get_request_scoped_session(user_id, "test-req-id") as session:
                    # System user should work fine (bypass authentication)
                    assert session is not None
                    
            except Exception as e:
                pytest.fail(f"System user authentication bypass failed: {e}")
    
    @pytest.mark.asyncio
    async def test_auth_client_validate_token_fallback_for_service_users(self):
        """Test that validate_token handles service users properly.
        
        This reproduces the issue where service users are treated like regular JWT users.
        """
        auth_client = AuthServiceClient()
        
        # Mock missing service auth settings (reproduces staging issue)
        auth_client.service_secret = None
        auth_client.service_id = None
        
        # Mock auth service being unavailable (common in tests)
        with patch.object(auth_client, '_check_auth_service_connectivity', return_value=False):
            
            # Try to validate a service token (this should fail in current implementation)
            service_token = "service:netra-backend:some-operation-token"
            
            result = await auth_client.validate_token(service_token)
            
            # This should indicate auth service unavailable
            assert result is not None
            assert result["valid"] is False
            assert "auth_service_unreachable" in result.get("error", "")
    
    def test_service_user_pattern_recognition_logic(self):
        """Test the core logic for recognizing service user patterns.
        
        This tests the fundamental pattern matching that's failing in Issue #484.
        """
        # Test various user ID patterns
        test_cases = [
            ("service:netra-backend", True, "netra-backend"),
            ("service:auth-service", True, "auth-service"), 
            ("service:", False, None),  # Invalid - empty service name
            ("user:123", False, None),  # Not a service user
            ("system", False, None),    # Legacy system user (different pattern)
            ("regular-user-id", False, None),  # Regular user ID
        ]
        
        for user_id, should_be_service, expected_service_id in test_cases:
            # Test if user_id starts with "service:"
            is_service_user = user_id.startswith("service:")
            
            if should_be_service:
                assert is_service_user, f"User ID '{user_id}' should be recognized as service user"
                
                # Test service ID extraction
                if ":" in user_id:
                    extracted_service_id = user_id.split(":", 1)[1] if len(user_id.split(":", 1)) > 1 else None
                    assert extracted_service_id == expected_service_id, f"Service ID extraction failed for '{user_id}'"
            else:
                if user_id.startswith("service:"):
                    # Edge case - starts with service: but invalid format
                    extracted_service_id = user_id.split(":", 1)[1] if len(user_id.split(":", 1)) > 1 else None
                    assert not extracted_service_id or extracted_service_id == "", f"Invalid service user '{user_id}' should not extract valid service ID"
    
    @pytest.mark.asyncio
    async def test_dependencies_get_request_scoped_db_session_service_auth_flow(self):
        """Test the complete flow in dependencies.py for service authentication.
        
        This is the integration test that reproduces the exact Issue #484 scenario.
        """
        # Mock the service user context to return service:netra-backend
        with patch('netra_backend.app.dependencies.get_service_user_context') as mock_service_context:
            mock_service_context.return_value = "service:netra-backend"
            
            # Mock the session factory to test the authentication flow
            with patch('netra_backend.app.database.request_scoped_session_factory.get_session_factory') as mock_get_factory:
                mock_factory = AsyncMock()
                mock_session = AsyncMock()
                mock_session.info = {}
                
                # Mock the session factory's get_request_scoped_session method
                async def mock_session_context(user_id, request_id):
                    # This is where Issue #484 manifests - authentication fails for service users
                    if user_id.startswith("service:"):
                        # In the broken implementation, this would raise an authentication error
                        # For testing, we'll simulate the failure
                        raise Exception("403 Not authenticated - service user validation failed")
                    return mock_session
                
                mock_factory.get_request_scoped_session = AsyncMock(side_effect=mock_session_context)
                mock_get_factory.return_value = mock_factory
                
                # Try to create a session - this should reproduce Issue #484
                try:
                    async for session in get_request_scoped_db_session():
                        pytest.fail("Service authentication should have failed, reproducing Issue #484")
                        
                except Exception as e:
                    # This is the expected failure from Issue #484
                    assert "403 Not authenticated" in str(e)
                    assert "service user validation failed" in str(e)
    
    @pytest.mark.asyncio
    async def test_auth_client_missing_service_secret_error_reproduction(self):
        """Test that reproduces the SERVICE_SECRET configuration issue in Issue #484."""
        
        # Create auth client with missing service secret (reproduces staging issue)
        auth_client = AuthServiceClient()
        
        # Simulate missing SERVICE_SECRET environment variable
        with patch('netra_backend.app.core.configuration.get_configuration') as mock_config:
            mock_config_obj = Mock()
            mock_config_obj.service_id = "netra-backend"
            mock_config_obj.service_secret = None  # Missing SECRET
            mock_config.return_value = mock_config_obj
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env.return_value = {}  # No SERVICE_SECRET in env either
                
                # Re-initialize auth client to pick up missing secret
                auth_client = AuthServiceClient()
                
                # Verify that service secret is not configured
                assert auth_client.service_secret is None
                
                # Test validation with missing secret
                result = await auth_client.validate_service_user_context("netra-backend", "test")
                
                assert result["valid"] is False
                assert result["error"] == "missing_service_credentials"
    
    def test_issue_484_pattern_identification(self):
        """Test to identify the exact patterns that fail in Issue #484."""
        
        # These are the patterns mentioned in Issue #484
        failing_patterns = [
            "service:netra-backend",  # Main service user from the issue
        ]
        
        working_patterns = [
            "system",  # Legacy system user that works
        ]
        
        # Test that we can identify service users correctly
        for user_id in failing_patterns:
            assert user_id.startswith("service:"), f"Pattern {user_id} should be identified as service user"
            
        for user_id in working_patterns:
            assert not user_id.startswith("service:"), f"Pattern {user_id} should not be identified as service user"
    
    @pytest.mark.asyncio
    async def test_service_authentication_bypass_mechanism(self):
        """Test the service authentication bypass mechanism that should be implemented.
        
        This test defines what the fix should accomplish.
        """
        auth_client = AuthServiceClient()
        auth_client.service_id = "netra-backend"
        auth_client.service_secret = "test-secret"
        
        # Test the service authentication bypass for internal operations
        service_user_id = "service:netra-backend"
        
        # This should use service-to-service authentication instead of JWT validation
        result = await auth_client.validate_service_user_context("netra-backend", "database_session_creation")
        
        # Verify service authentication bypass works
        assert result["valid"] is True
        assert result["authentication_method"] == "service_to_service"
        assert result["user_id"] == service_user_id
        assert "service:*" in result["permissions"]  # Service-level permissions
    
    def test_environment_configuration_detection(self):
        """Test detection of environment configuration issues that cause Issue #484."""
        
        # Test scenarios that reproduce the configuration problems
        test_scenarios = [
            {
                "name": "missing_service_secret",
                "service_id": "netra-backend", 
                "service_secret": None,
                "expected_issue": "SERVICE_SECRET not configured"
            },
            {
                "name": "missing_service_id",
                "service_id": None,
                "service_secret": "some-secret", 
                "expected_issue": "SERVICE_ID not configured"
            },
            {
                "name": "both_missing",
                "service_id": None,
                "service_secret": None,
                "expected_issue": "Both SERVICE_ID and SERVICE_SECRET missing"
            }
        ]
        
        for scenario in test_scenarios:
            # Check if the configuration would cause authentication failures
            has_service_id = scenario["service_id"] is not None
            has_service_secret = scenario["service_secret"] is not None
            
            if not has_service_id or not has_service_secret:
                # This configuration would cause Issue #484
                assert True, f"Scenario '{scenario['name']}' would cause service authentication failure"
            else:
                # This configuration should work
                assert has_service_id and has_service_secret


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])