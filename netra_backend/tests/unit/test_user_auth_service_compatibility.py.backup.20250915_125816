"""
Comprehensive Unit Tests for user_auth_service.py - Backward Compatibility Shim

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - Maintains legacy API compatibility
- Business Goal: Zero-downtime migration from legacy auth to SSOT auth service
- Value Impact: Prevents breaking changes that could disrupt $50K+ MRR operations
- Strategic Impact: Enables gradual migration while maintaining business continuity

MISSION CRITICAL: user_auth_service.py is a BACKWARD COMPATIBILITY SHIM that
allows existing code to continue working while we migrate to the new SSOT auth
architecture. This prevents cascade failures during the migration and ensures
that all existing authentication integrations continue to work.

Tests validate:
1. UserAuthService class methods work correctly with auth_client backend
2. Legacy function aliases work for backward compatibility
3. Error handling maintains consistent behavior with legacy systems
4. Authentication flows work exactly like the old service
5. Token validation maintains same interface and behavior
6. Exception handling provides graceful degradation
7. SSOT compliance is maintained through auth_client delegation

These tests ensure seamless migration without breaking existing integrations.
"""

import pytest
from typing import Dict, Optional, Any
from unittest.mock import AsyncMock, Mock, patch

from netra_backend.app.services.user_auth_service import (
    UserAuthService,
    authenticate_user,
    validate_token,
    _auth_client
)


class TestUserAuthServiceClass:
    """Test UserAuthService class maintains backward compatibility."""

    @pytest.mark.asyncio
    async def test_authenticate_success_returns_proper_format(self):
        """Test authenticate method returns proper response format on success."""
        mock_result = {
            "access_token": "jwt_token_12345",
            "refresh_token": "refresh_token_67890", 
            "user_id": "user123",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = mock_result
            
            result = await UserAuthService.authenticate("test@example.com", "password123")
            
            assert result is not None
            assert result == mock_result
            assert result["access_token"] == "jwt_token_12345"
            assert result["user_id"] == "user123"
            
            # Verify correct method called on auth_client
            mock_login.assert_called_once_with("test@example.com", "password123")

    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials_returns_none(self):
        """Test authenticate method returns None for invalid credentials."""
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = None  # Auth service returns None for invalid creds
            
            result = await UserAuthService.authenticate("test@example.com", "wrong_password")
            
            assert result is None
            mock_login.assert_called_once_with("test@example.com", "wrong_password")

    @pytest.mark.asyncio
    async def test_authenticate_handles_auth_service_exception(self):
        """Test authenticate method handles auth service exceptions gracefully."""
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.side_effect = Exception("Auth service unavailable")
            
            result = await UserAuthService.authenticate("test@example.com", "password123")
            
            # Should return None instead of raising exception
            assert result is None
            mock_login.assert_called_once_with("test@example.com", "password123")

    @pytest.mark.asyncio
    async def test_validate_token_success_returns_validation_result(self):
        """Test validate_token method returns validation result on success."""
        mock_validation_result = {
            "valid": True,
            "user_id": "user123",
            "email": "test@example.com",
            "permissions": ["read", "write"],
            "role": "standard_user"
        }
        
        with patch.object(_auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = mock_validation_result
            
            result = await UserAuthService.validate_token("valid_jwt_token")
            
            assert result is not None
            assert result == mock_validation_result
            assert result["valid"] is True
            assert result["user_id"] == "user123"
            
            mock_validate.assert_called_once_with("valid_jwt_token")

    @pytest.mark.asyncio
    async def test_validate_token_invalid_token_returns_none(self):
        """Test validate_token method returns None for invalid tokens."""
        with patch.object(_auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = None  # Auth service returns None for invalid token
            
            result = await UserAuthService.validate_token("invalid_jwt_token")
            
            assert result is None
            mock_validate.assert_called_once_with("invalid_jwt_token")

    @pytest.mark.asyncio
    async def test_validate_token_handles_auth_service_exception(self):
        """Test validate_token method handles auth service exceptions gracefully."""
        with patch.object(_auth_client, 'validate_token') as mock_validate:
            mock_validate.side_effect = Exception("Auth service timeout")
            
            result = await UserAuthService.validate_token("some_jwt_token")
            
            # Should return None instead of raising exception
            assert result is None
            mock_validate.assert_called_once_with("some_jwt_token")

    @pytest.mark.asyncio
    async def test_authenticate_maintains_legacy_interface(self):
        """Test authenticate method maintains exact legacy interface."""
        # Legacy interface: (username: str, password: str) -> Optional[Dict[str, Any]]
        mock_result = {"access_token": "token", "user_id": "user123"}
        
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = mock_result
            
            # Should accept positional arguments like legacy service
            result = await UserAuthService.authenticate("user@example.com", "password")
            
            assert result == mock_result
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_validate_token_maintains_legacy_interface(self):
        """Test validate_token method maintains exact legacy interface."""
        # Legacy interface: (token: str) -> Optional[Dict[str, Any]]
        mock_result = {"valid": True, "user_id": "user123"}
        
        with patch.object(_auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = mock_result
            
            # Should accept single token argument like legacy service
            result = await UserAuthService.validate_token("jwt_token")
            
            assert result == mock_result
            assert isinstance(result, dict)


class TestLegacyFunctionAliases:
    """Test legacy function aliases maintain backward compatibility."""

    @pytest.mark.asyncio
    async def test_authenticate_user_function_alias_success(self):
        """Test authenticate_user function alias works correctly."""
        mock_result = {
            "access_token": "legacy_token_123",
            "user_id": "legacy_user_456"
        }
        
        with patch.object(UserAuthService, 'authenticate') as mock_authenticate:
            mock_authenticate.return_value = mock_result
            
            result = await authenticate_user("legacy@example.com", "legacy_pass")
            
            assert result == mock_result
            mock_authenticate.assert_called_once_with("legacy@example.com", "legacy_pass")

    @pytest.mark.asyncio
    async def test_authenticate_user_function_alias_failure(self):
        """Test authenticate_user function alias handles failures."""
        with patch.object(UserAuthService, 'authenticate') as mock_authenticate:
            mock_authenticate.return_value = None
            
            result = await authenticate_user("invalid@example.com", "wrong_pass")
            
            assert result is None
            mock_authenticate.assert_called_once_with("invalid@example.com", "wrong_pass")

    @pytest.mark.asyncio
    async def test_validate_token_function_alias_success(self):
        """Test validate_token function alias works correctly."""
        mock_result = {
            "valid": True,
            "user_id": "legacy_user_789",
            "permissions": ["legacy_read"]
        }
        
        with patch.object(UserAuthService, 'validate_token') as mock_validate:
            mock_validate.return_value = mock_result
            
            result = await validate_token("legacy_jwt_token")
            
            assert result == mock_result
            mock_validate.assert_called_once_with("legacy_jwt_token")

    @pytest.mark.asyncio
    async def test_validate_token_function_alias_failure(self):
        """Test validate_token function alias handles failures."""
        with patch.object(UserAuthService, 'validate_token') as mock_validate:
            mock_validate.return_value = None
            
            result = await validate_token("invalid_legacy_token")
            
            assert result is None
            mock_validate.assert_called_once_with("invalid_legacy_token")

    @pytest.mark.asyncio
    async def test_legacy_function_signatures_match_class_methods(self):
        """Test legacy function signatures exactly match class method signatures."""
        import inspect
        
        # Get signatures
        auth_user_sig = inspect.signature(authenticate_user)
        class_auth_sig = inspect.signature(UserAuthService.authenticate)
        
        validate_token_sig = inspect.signature(validate_token)
        class_validate_sig = inspect.signature(UserAuthService.validate_token)
        
        # Compare parameters (excluding 'self' for class methods)
        auth_params = list(auth_user_sig.parameters.keys())
        class_auth_params = list(class_auth_sig.parameters.keys())
        
        validate_params = list(validate_token_sig.parameters.keys())
        class_validate_params = list(class_validate_sig.parameters.keys())
        
        assert auth_params == class_auth_params
        assert validate_params == class_validate_params


class TestAuthClientIntegration:
    """Test integration with underlying auth_client."""

    def test_auth_client_instance_exists(self):
        """Test _auth_client instance is properly created."""
        assert _auth_client is not None
        # Should be an AuthServiceClient instance
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        assert isinstance(_auth_client, AuthServiceClient)

    @pytest.mark.asyncio
    async def test_user_auth_service_delegates_to_auth_client(self):
        """Test UserAuthService properly delegates calls to auth_client."""
        # Test that methods actually call the auth_client, not some other implementation
        with patch.object(_auth_client, 'login') as mock_login, \
             patch.object(_auth_client, 'validate_token') as mock_validate:
            
            mock_login.return_value = {"test": "result"}
            mock_validate.return_value = {"valid": True}
            
            # Call UserAuthService methods
            await UserAuthService.authenticate("test@example.com", "password")
            await UserAuthService.validate_token("token")
            
            # Verify calls were delegated to auth_client
            mock_login.assert_called_once_with("test@example.com", "password")
            mock_validate.assert_called_once_with("token")

    @pytest.mark.asyncio
    async def test_auth_client_method_name_mapping(self):
        """Test correct mapping from UserAuthService methods to auth_client methods."""
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = {"mapped": "correctly"}
            
            # UserAuthService.authenticate should call auth_client.login
            result = await UserAuthService.authenticate("user@example.com", "pass")
            
            assert result["mapped"] == "correctly"
            # The comment in the code mentions this is a FIX for method name mapping
            mock_login.assert_called_once_with("user@example.com", "pass")


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases in backward compatibility."""

    @pytest.mark.asyncio
    async def test_authenticate_empty_username_handles_gracefully(self):
        """Test authenticate handles empty username gracefully."""
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = None
            
            result = await UserAuthService.authenticate("", "password")
            
            assert result is None
            mock_login.assert_called_once_with("", "password")

    @pytest.mark.asyncio
    async def test_authenticate_empty_password_handles_gracefully(self):
        """Test authenticate handles empty password gracefully."""
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = None
            
            result = await UserAuthService.authenticate("user@example.com", "")
            
            assert result is None
            mock_login.assert_called_once_with("user@example.com", "")

    @pytest.mark.asyncio
    async def test_validate_token_empty_token_handles_gracefully(self):
        """Test validate_token handles empty token gracefully."""
        with patch.object(_auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = None
            
            result = await UserAuthService.validate_token("")
            
            assert result is None
            mock_validate.assert_called_once_with("")

    @pytest.mark.asyncio
    async def test_validate_token_none_token_handles_gracefully(self):
        """Test validate_token handles None token gracefully."""
        with patch.object(_auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = None
            
            result = await UserAuthService.validate_token(None)
            
            assert result is None
            mock_validate.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_authenticate_network_timeout_returns_none(self):
        """Test authenticate returns None on network timeout."""
        import asyncio
        
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.side_effect = asyncio.TimeoutError("Network timeout")
            
            result = await UserAuthService.authenticate("test@example.com", "password")
            
            assert result is None

    @pytest.mark.asyncio 
    async def test_validate_token_connection_error_returns_none(self):
        """Test validate_token returns None on connection error."""
        import httpx
        
        with patch.object(_auth_client, 'validate_token') as mock_validate:
            mock_validate.side_effect = httpx.ConnectError("Connection failed")
            
            result = await UserAuthService.validate_token("jwt_token")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_auth_service_disabled_returns_none(self):
        """Test authenticate returns None when auth service is disabled."""
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = None  # Auth service disabled
            
            result = await UserAuthService.authenticate("test@example.com", "password")
            
            assert result is None
            mock_login.assert_called_once_with("test@example.com", "password")


class TestLegacyResponseFormat:
    """Test that response formats match legacy expectations."""

    @pytest.mark.asyncio
    async def test_authenticate_response_contains_expected_fields(self):
        """Test authenticate response contains fields expected by legacy code."""
        expected_response = {
            "access_token": "jwt_access_token_123",
            "refresh_token": "jwt_refresh_token_456",
            "user_id": "user_789",
            "token_type": "Bearer",
            "expires_in": 3600,
            "role": "standard_user"
        }
        
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = expected_response
            
            result = await UserAuthService.authenticate("test@example.com", "password")
            
            # Verify all expected fields are present
            assert "access_token" in result
            assert "refresh_token" in result
            assert "user_id" in result
            assert "token_type" in result
            assert "expires_in" in result
            
            # Verify field values
            assert result["access_token"] == "jwt_access_token_123"
            assert result["user_id"] == "user_789"

    @pytest.mark.asyncio
    async def test_validate_token_response_contains_expected_fields(self):
        """Test validate_token response contains fields expected by legacy code."""
        expected_response = {
            "valid": True,
            "user_id": "user_123",
            "email": "test@example.com",
            "permissions": ["read", "write", "admin"],
            "role": "admin",
            "is_superuser": True
        }
        
        with patch.object(_auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = expected_response
            
            result = await UserAuthService.validate_token("jwt_token")
            
            # Verify all expected fields are present
            assert "valid" in result
            assert "user_id" in result
            assert "email" in result
            assert "permissions" in result
            
            # Verify field values and types
            assert result["valid"] is True
            assert isinstance(result["permissions"], list)
            assert result["user_id"] == "user_123"

    @pytest.mark.asyncio
    async def test_authenticate_failure_response_format(self):
        """Test authenticate failure response format matches legacy expectations."""
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = None
            
            result = await UserAuthService.authenticate("invalid@example.com", "wrong_pass")
            
            # Legacy code expects None for authentication failure
            assert result is None
            assert result is not False  # Should be None, not False
            assert result != {}  # Should be None, not empty dict

    @pytest.mark.asyncio
    async def test_validate_token_failure_response_format(self):
        """Test validate_token failure response format matches legacy expectations."""
        with patch.object(_auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = None
            
            result = await UserAuthService.validate_token("invalid_token")
            
            # Legacy code expects None for validation failure
            assert result is None
            assert result is not False  # Should be None, not False
            assert result != {"valid": False}  # Should be None, not error dict


class TestBackwardCompatibilityIntegration:
    """Test complete backward compatibility with existing integrations."""

    @pytest.mark.asyncio
    async def test_full_authentication_flow_legacy_compatibility(self):
        """Test complete authentication flow maintains legacy compatibility."""
        # Simulate complete legacy auth flow
        auth_response = {
            "access_token": "complete_flow_token_123",
            "refresh_token": "complete_flow_refresh_456", 
            "user_id": "complete_flow_user_789",
            "expires_in": 3600
        }
        
        validation_response = {
            "valid": True,
            "user_id": "complete_flow_user_789",
            "email": "complete@example.com",
            "permissions": ["read", "write"]
        }
        
        with patch.object(_auth_client, 'login') as mock_login, \
             patch.object(_auth_client, 'validate_token') as mock_validate:
            
            mock_login.return_value = auth_response
            mock_validate.return_value = validation_response
            
            # Step 1: Authenticate (legacy way)
            auth_result = await authenticate_user("complete@example.com", "password123")
            assert auth_result is not None
            assert auth_result["access_token"] == "complete_flow_token_123"
            
            # Step 2: Validate token (legacy way) 
            token_result = await validate_token(auth_result["access_token"])
            assert token_result is not None
            assert token_result["valid"] is True
            assert token_result["user_id"] == "complete_flow_user_789"

    @pytest.mark.asyncio
    async def test_class_method_and_function_alias_consistency(self):
        """Test class methods and function aliases return identical results."""
        test_response = {
            "access_token": "consistency_token_abc",
            "user_id": "consistency_user_def"
        }
        
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = test_response
            
            # Call both class method and function alias
            class_result = await UserAuthService.authenticate("test@example.com", "password")
            function_result = await authenticate_user("test@example.com", "password")
            
            # Results should be identical
            assert class_result == function_result
            assert class_result == test_response
            
            # Both should call the same underlying method
            assert mock_login.call_count == 2

    @pytest.mark.asyncio
    async def test_error_handling_consistency_across_interfaces(self):
        """Test error handling is consistent across class methods and function aliases."""
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.side_effect = Exception("Service unavailable")
            
            # Both interfaces should handle errors the same way
            class_result = await UserAuthService.authenticate("test@example.com", "password")
            function_result = await authenticate_user("test@example.com", "password")
            
            # Both should return None on error
            assert class_result is None
            assert function_result is None


class TestUserAuthServiceBusinessValueDelivery:
    """Test that user_auth_service delivers expected business value."""

    @pytest.mark.asyncio
    async def test_backward_compatibility_prevents_breaking_changes(self):
        """Test backward compatibility prevents breaking changes during migration."""
        # Legacy code calling the old interface should still work
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = {"access_token": "migration_safe_token"}
            
            # Old code using UserAuthService.authenticate
            result1 = await UserAuthService.authenticate("user@example.com", "password")
            
            # Old code using authenticate_user function
            result2 = await authenticate_user("user@example.com", "password")
            
            # Both should work and return expected results
            assert result1 is not None
            assert result2 is not None
            assert result1["access_token"] == "migration_safe_token"
            assert result2["access_token"] == "migration_safe_token"
            
            # This prevents breaking changes that could disrupt business operations

    @pytest.mark.asyncio
    async def test_ssot_compliance_through_delegation(self):
        """Test SSOT compliance is maintained through auth_client delegation."""
        with patch.object(_auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = {"valid": True, "user_id": "ssot_user_123"}
            
            # All calls go through the same SSOT auth_client
            result = await UserAuthService.validate_token("test_token")
            
            assert result["user_id"] == "ssot_user_123"
            mock_validate.assert_called_once_with("test_token")
            
            # This ensures SSOT compliance while maintaining backward compatibility

    @pytest.mark.asyncio
    async def test_enables_gradual_migration_strategy(self):
        """Test enables gradual migration from legacy to new auth architecture."""
        # Service acts as a bridge during migration
        migration_response = {
            "access_token": "migration_token_123",
            "user_id": "migration_user_456",
            "migration_safe": True
        }
        
        with patch.object(_auth_client, 'login') as mock_login:
            mock_login.return_value = migration_response
            
            # Legacy interface works with new backend
            result = await UserAuthService.authenticate("migrate@example.com", "password")
            
            assert result == migration_response
            assert result["migration_safe"] is True
            
            # This allows gradual migration without service disruption

    def test_maintains_service_boundary_independence(self):
        """Test maintains service boundary independence through proper shimming."""
        # The shim should not expose internal auth_client details
        assert hasattr(UserAuthService, 'authenticate')
        assert hasattr(UserAuthService, 'validate_token')
        
        # But should not expose auth_client internals
        assert not hasattr(UserAuthService, 'validate_token_jwt')
        assert not hasattr(UserAuthService, 'circuit_breaker')
        assert not hasattr(UserAuthService, 'token_cache')
        
        # This maintains proper service boundaries during migration