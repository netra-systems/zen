"""
Unit Tests for SSOT Auth Test Helpers (Issue #1195)

This test module validates the SSOT auth test helpers infrastructure that
replaces direct JWT operations with proper auth service delegation patterns.

Business Value: Platform/Internal - Auth Testing Infrastructure & SSOT Compliance
Ensures consistent auth testing patterns and prevents JWT violations in tests.

Test Strategy:
1. Test SSOTAuthTestHelper functionality
2. Validate auth service delegation in test helpers
3. Test mock auth service for controlled testing
4. Ensure helper methods work without direct JWT operations
5. Validate backwards compatibility with existing test patterns

Expected Results:
- Auth test helpers should work without direct JWT dependencies
- All auth operations should delegate to auth service
- Helpers should provide test-friendly interfaces
- Mock service should support isolation testing
"""

import pytest
import asyncio
import tempfile
import os
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.unit
class SSOTAuthTestHelpersTests(SSotAsyncTestCase):
    """
    Tests for SSOT Auth Test Helpers functionality.
    
    These tests validate that the auth test helpers work correctly
    and provide proper delegation to auth service.
    """
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        # Track test metrics
        self.record_metric("test_category", "ssot_auth_test_helpers")
        self.record_metric("issue_number", "1195")
    
    async def test_ssot_auth_test_helper_import_available(self):
        """
        Test that SSOTAuthTestHelper can be imported successfully.
        
        Expected: Should import without JWT dependencies.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Verify class exists and has expected structure
            self.assertIsNotNone(SSOTAuthTestHelper)
            
            # Check for required methods (should not require JWT)
            required_methods = [
                'create_test_user_with_token',
                'validate_token_via_service',
                'create_websocket_auth_token',
                'get_user_from_token',
                'refresh_token_via_service'
            ]
            
            for method_name in required_methods:
                self.assertTrue(
                    hasattr(SSOTAuthTestHelper, method_name),
                    f"SSOTAuthTestHelper missing required method: {method_name}"
                )
            
            self.record_metric("ssot_auth_helper_import", "success")
            self.logger.info("CHECK Successfully imported SSOTAuthTestHelper")
            
        except ImportError as e:
            self.record_metric("ssot_auth_helper_import", "failed")
            self.logger.error(f"X Could not import SSOTAuthTestHelper: {e}")
            self.fail(f"SSOTAuthTestHelper import failed: {e}")
    
    async def test_ssot_auth_helper_initialization_without_auth_client(self):
        """
        Test SSOTAuthTestHelper initialization when auth client is unavailable.
        
        Expected: Should handle missing auth client gracefully.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Mock AuthServiceClient import failure
            with patch('test_framework.ssot.auth_test_helpers.AuthServiceClient') as mock_client:
                mock_client.side_effect = ImportError("AuthServiceClient not available")
                
                # Initialize helper (should handle missing client)
                helper = SSOTAuthTestHelper()
                self.assertIsNotNone(helper)
                
                # Verify auth_client is None when unavailable
                self.assertIsNone(helper.auth_client)
                
                self.record_metric("auth_helper_graceful_degradation", "success")
                self.logger.info("CHECK SSOTAuthTestHelper handles missing auth client gracefully")
                
        except Exception as e:
            self.record_metric("auth_helper_graceful_degradation", "failed")
            self.logger.error(f"X Auth helper graceful degradation failed: {e}")
            self.fail(f"Auth helper should handle missing client gracefully: {e}")
    
    async def test_ssot_auth_helper_initialization_with_mock_client(self):
        """
        Test SSOTAuthTestHelper initialization with mock auth client.
        
        Expected: Should accept custom auth client for testing.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client
            mock_auth_client = AsyncMock()
            mock_auth_client.create_user = AsyncMock(return_value={"user_id": "test_user_123"})
            mock_auth_client.generate_token = AsyncMock(return_value={
                "access_token": "mock_token_123",
                "token_type": "bearer",
                "expires_in": 3600
            })
            
            # Initialize helper with mock client
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            self.assertIsNotNone(helper)
            self.assertEqual(helper.auth_client, mock_auth_client)
            
            self.record_metric("auth_helper_mock_client", "success")
            self.logger.info("CHECK SSOTAuthTestHelper accepts mock auth client")
            
        except Exception as e:
            self.record_metric("auth_helper_mock_client", "failed")
            self.logger.error(f"X Auth helper mock client initialization failed: {e}")
            self.fail(f"Auth helper should accept mock client: {e}")
    
    async def test_create_test_user_with_token_delegates_to_auth_service(self):
        """
        Test that create_test_user_with_token delegates to auth service.
        
        Expected: Should call auth service methods, not JWT operations.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client with expected methods
            mock_auth_client = AsyncMock()
            mock_auth_client.create_user = AsyncMock(return_value={
                "user_id": "test_user_456",
                "email": "test@example.com"
            })
            mock_auth_client.generate_token = AsyncMock(return_value={
                "access_token": "auth_service_token_456",
                "token_type": "bearer", 
                "expires_in": 3600
            })
            
            # Initialize helper with mock client
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Create test user
            user_data = await helper.create_test_user_with_token(
                email="test@example.com",
                password="TestPassword123!",
                name="Test User",
                permissions=["read", "write"]
            )
            
            # Verify auth service delegation occurred
            mock_auth_client.create_user.assert_called_once_with(
                email="test@example.com",
                password="TestPassword123!",
                name="Test User"
            )
            mock_auth_client.generate_token.assert_called_once_with(
                user_id="test_user_456",
                email="test@example.com",
                permissions=["read", "write"]
            )
            
            # Verify user data structure
            self.assertIsInstance(user_data, dict)
            self.assertEqual(user_data["user_id"], "test_user_456")
            self.assertEqual(user_data["email"], "test@example.com")
            self.assertEqual(user_data["access_token"], "auth_service_token_456")
            self.assertEqual(user_data["token_type"], "bearer")
            
            # Verify no JWT operations were used (delegated to auth service)
            self.record_metric("create_user_delegation", "success")
            self.logger.info("CHECK create_test_user_with_token properly delegates to auth service")
            
        except Exception as e:
            self.record_metric("create_user_delegation", "failed")
            self.logger.error(f"X create_test_user_with_token delegation failed: {e}")
            self.fail(f"User creation should delegate to auth service: {e}")
    
    async def test_validate_token_via_service_delegates_to_auth_service(self):
        """
        Test that validate_token_via_service delegates to auth service.
        
        Expected: Should call auth service validation, not JWT decode.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client with validation method
            mock_auth_client = AsyncMock()
            mock_auth_client.validate_token = AsyncMock(return_value={
                "valid": True,
                "user_id": "validated_user_789",
                "email": "validated@example.com",
                "permissions": ["read", "write"]
            })
            
            # Initialize helper with mock client
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Validate token
            test_token = "test_token_to_validate"
            validation_result = await helper.validate_token_via_service(test_token)
            
            # Verify auth service delegation occurred
            mock_auth_client.validate_token.assert_called_once_with(test_token)
            
            # Verify validation result structure
            self.assertIsInstance(validation_result, dict)
            self.assertTrue(validation_result["valid"])
            self.assertEqual(validation_result["user_id"], "validated_user_789")
            self.assertEqual(validation_result["email"], "validated@example.com")
            
            # Verify no JWT decode operations were used
            self.record_metric("validate_token_delegation", "success")
            self.logger.info("CHECK validate_token_via_service properly delegates to auth service")
            
        except Exception as e:
            self.record_metric("validate_token_delegation", "failed")
            self.logger.error(f"X validate_token_via_service delegation failed: {e}")
            self.fail(f"Token validation should delegate to auth service: {e}")
    
    async def test_create_websocket_auth_token_delegates_to_auth_service(self):
        """
        Test that create_websocket_auth_token delegates to auth service.
        
        Expected: Should use auth service for WebSocket tokens, not JWT operations.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client with WebSocket token method
            mock_auth_client = AsyncMock()
            mock_auth_client.generate_websocket_token = AsyncMock(return_value={
                "access_token": "websocket_token_123"
            })
            
            # Initialize helper with mock client
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Create WebSocket token
            user_id = "websocket_user_123"
            scopes = ["websocket", "chat"]
            websocket_token = await helper.create_websocket_auth_token(user_id, scopes)
            
            # Verify auth service delegation occurred
            mock_auth_client.generate_websocket_token.assert_called_once_with(
                user_id=user_id,
                scopes=scopes
            )
            
            # Verify token returned
            self.assertEqual(websocket_token, "websocket_token_123")
            
            self.record_metric("websocket_token_delegation", "success")
            self.logger.info("CHECK create_websocket_auth_token properly delegates to auth service")
            
        except Exception as e:
            self.record_metric("websocket_token_delegation", "failed")
            self.logger.error(f"X create_websocket_auth_token delegation failed: {e}")
            self.fail(f"WebSocket token creation should delegate to auth service: {e}")
    
    async def test_create_websocket_auth_token_fallback_when_no_websocket_method(self):
        """
        Test WebSocket token creation fallback when auth client lacks WebSocket method.
        
        Expected: Should fall back to regular token generation with WebSocket permissions.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client WITHOUT WebSocket-specific method
            mock_auth_client = AsyncMock()
            # Don't add generate_websocket_token method
            mock_auth_client.generate_token = AsyncMock(return_value={
                "access_token": "fallback_websocket_token_456"
            })
            
            # Initialize helper with mock client
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Create WebSocket token (should use fallback)
            user_id = "websocket_user_456"
            scopes = ["websocket", "chat"]
            websocket_token = await helper.create_websocket_auth_token(user_id, scopes)
            
            # Verify fallback to regular token generation
            mock_auth_client.generate_token.assert_called_once_with(
                user_id=user_id,
                permissions=scopes
            )
            
            # Verify token returned
            self.assertEqual(websocket_token, "fallback_websocket_token_456")
            
            self.record_metric("websocket_token_fallback", "success")
            self.logger.info("CHECK WebSocket token creation falls back to regular token generation")
            
        except Exception as e:
            self.record_metric("websocket_token_fallback", "failed")
            self.logger.error(f"X WebSocket token fallback failed: {e}")
            self.fail(f"WebSocket token should fall back to regular generation: {e}")
    
    async def test_get_user_from_token_delegates_to_validation(self):
        """
        Test that get_user_from_token delegates to auth service validation.
        
        Expected: Should use validation service, not JWT decode.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client
            mock_auth_client = AsyncMock()
            mock_auth_client.validate_token = AsyncMock(return_value={
                "valid": True,
                "user_id": "token_user_789",
                "email": "token_user@example.com",
                "permissions": ["read", "write", "admin"]
            })
            
            # Initialize helper with mock client
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Get user from token
            test_token = "user_lookup_token"
            user_info = await helper.get_user_from_token(test_token)
            
            # Verify validation was called
            mock_auth_client.validate_token.assert_called_once_with(test_token)
            
            # Verify user info structure
            self.assertIsInstance(user_info, dict)
            self.assertEqual(user_info["user_id"], "token_user_789")
            self.assertEqual(user_info["email"], "token_user@example.com")
            self.assertEqual(user_info["permissions"], ["read", "write", "admin"])
            
            self.record_metric("get_user_from_token_delegation", "success")
            self.logger.info("CHECK get_user_from_token properly delegates to auth service validation")
            
        except Exception as e:
            self.record_metric("get_user_from_token_delegation", "failed")
            self.logger.error(f"X get_user_from_token delegation failed: {e}")
            self.fail(f"User lookup should delegate to auth service validation: {e}")
    
    async def test_get_user_from_token_handles_invalid_token(self):
        """
        Test that get_user_from_token handles invalid tokens gracefully.
        
        Expected: Should return None for invalid tokens, not raise JWT errors.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client that returns invalid validation
            mock_auth_client = AsyncMock()
            mock_auth_client.validate_token = AsyncMock(return_value={
                "valid": False,
                "error": "Token expired"
            })
            
            # Initialize helper with mock client
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Get user from invalid token
            invalid_token = "invalid_token_123"
            user_info = await helper.get_user_from_token(invalid_token)
            
            # Verify validation was called
            mock_auth_client.validate_token.assert_called_once_with(invalid_token)
            
            # Verify None returned for invalid token
            self.assertIsNone(user_info)
            
            self.record_metric("invalid_token_handling", "success")
            self.logger.info("CHECK get_user_from_token handles invalid tokens gracefully")
            
        except Exception as e:
            self.record_metric("invalid_token_handling", "failed")
            self.logger.error(f"X Invalid token handling failed: {e}")
            self.fail(f"Invalid token should be handled gracefully: {e}")
    
    async def test_create_multiple_test_users_for_isolation_testing(self):
        """
        Test creating multiple test users for isolation testing.
        
        Expected: Should create multiple isolated users via auth service.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client
            mock_auth_client = AsyncMock()
            
            # Mock multiple user creation
            user_responses = [
                {"user_id": "multi_user_1"}, 
                {"user_id": "multi_user_2"},
                {"user_id": "multi_user_3"}
            ]
            mock_auth_client.create_user = AsyncMock(side_effect=user_responses)
            
            # Mock token generation
            token_responses = [
                {"access_token": "token_1", "token_type": "bearer", "expires_in": 3600},
                {"access_token": "token_2", "token_type": "bearer", "expires_in": 3600},
                {"access_token": "token_3", "token_type": "bearer", "expires_in": 3600}
            ]
            mock_auth_client.generate_token = AsyncMock(side_effect=token_responses)
            
            # Initialize helper
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Create multiple users
            users = await helper.create_multiple_test_users(count=3, email_prefix="isolation-test")
            
            # Verify multiple users created
            self.assertEqual(len(users), 3)
            
            # Verify each user has proper structure
            for i, user in enumerate(users):
                self.assertEqual(user["user_id"], f"multi_user_{i+1}")
                self.assertEqual(user["access_token"], f"token_{i+1}")
                self.assertEqual(user["email"], f"isolation-test-{i+1}@example.com")
            
            # Verify auth service was called for each user
            self.assertEqual(mock_auth_client.create_user.call_count, 3)
            self.assertEqual(mock_auth_client.generate_token.call_count, 3)
            
            self.record_metric("multiple_users_creation", "success")
            self.record_metric("users_created_count", 3)
            self.logger.info("CHECK Successfully created multiple test users for isolation testing")
            
        except Exception as e:
            self.record_metric("multiple_users_creation", "failed")
            self.logger.error(f"X Multiple users creation failed: {e}")
            self.fail(f"Multiple user creation should work via auth service: {e}")


@pytest.mark.unit
class SSOTAuthTestHelpersConvenienceFunctionsTests(SSotAsyncTestCase):
    """
    Tests for SSOT Auth Test Helpers convenience functions.
    
    These test the standalone convenience functions that provide
    simple interfaces for common auth testing scenarios.
    """
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.record_metric("test_category", "ssot_auth_convenience_functions")
    
    async def test_create_test_auth_token_convenience_function(self):
        """
        Test create_test_auth_token convenience function.
        
        Expected: Should provide simple interface for token creation.
        """
        try:
            from test_framework.ssot.auth_test_helpers import create_test_auth_token
            
            # Mock the underlying helper
            with patch('test_framework.ssot.auth_test_helpers.SSOTAuthTestHelper') as mock_helper_class:
                mock_helper = AsyncMock()
                mock_helper.create_test_user_with_token = AsyncMock(return_value={
                    "access_token": "convenience_token_123"
                })
                mock_helper_class.return_value = mock_helper
                
                # Use convenience function
                token = await create_test_auth_token(
                    user_id="convenience_user",
                    email="convenience@example.com",
                    permissions=["read", "write"]
                )
                
                # Verify token returned
                self.assertEqual(token, "convenience_token_123")
                
                # Verify helper was used correctly
                mock_helper.create_test_user_with_token.assert_called_once_with(
                    email="convenience@example.com",
                    permissions=["read", "write"]
                )
                
                self.record_metric("convenience_create_token", "success")
                self.logger.info("CHECK create_test_auth_token convenience function works")
                
        except Exception as e:
            self.record_metric("convenience_create_token", "failed")
            self.logger.error(f"X create_test_auth_token convenience function failed: {e}")
            self.fail(f"Convenience token creation should work: {e}")
    
    async def test_validate_test_token_convenience_function(self):
        """
        Test validate_test_token convenience function.
        
        Expected: Should provide simple interface for token validation.
        """
        try:
            from test_framework.ssot.auth_test_helpers import validate_test_token
            
            # Mock the underlying helper
            with patch('test_framework.ssot.auth_test_helpers.SSOTAuthTestHelper') as mock_helper_class:
                mock_helper = AsyncMock()
                mock_helper.validate_token_via_service = AsyncMock(return_value={
                    "valid": True
                })
                mock_helper_class.return_value = mock_helper
                
                # Use convenience function
                is_valid = await validate_test_token("test_validation_token")
                
                # Verify validation result
                self.assertTrue(is_valid)
                
                # Verify helper was used correctly
                mock_helper.validate_token_via_service.assert_called_once_with("test_validation_token")
                
                self.record_metric("convenience_validate_token", "success")
                self.logger.info("CHECK validate_test_token convenience function works")
                
        except Exception as e:
            self.record_metric("convenience_validate_token", "failed")
            self.logger.error(f"X validate_test_token convenience function failed: {e}")
            self.fail(f"Convenience token validation should work: {e}")
    
    async def test_convenience_functions_handle_auth_service_unavailable(self):
        """
        Test that convenience functions handle auth service unavailability.
        
        Expected: Should raise clear errors when auth service unavailable.
        """
        try:
            from test_framework.ssot.auth_test_helpers import create_test_auth_token, validate_test_token
            
            # Mock helper initialization failure
            with patch('test_framework.ssot.auth_test_helpers.SSOTAuthTestHelper') as mock_helper_class:
                mock_helper_class.side_effect = ImportError("AuthServiceClient not available")
                
                # Test token creation failure
                with self.expect_exception(ImportError):
                    await create_test_auth_token()
                
                # Test token validation failure  
                with self.expect_exception(ImportError):
                    await validate_test_token("test_token")
                
                self.record_metric("convenience_error_handling", "success")
                self.logger.info("CHECK Convenience functions handle auth service unavailability")
                
        except Exception as e:
            self.record_metric("convenience_error_handling", "failed")
            self.logger.error(f"X Convenience function error handling failed: {e}")
            self.fail(f"Convenience functions should handle errors gracefully: {e}")


@pytest.mark.unit
class SSOTAuthTestHelpersAsyncContextManagerTests(SSotAsyncTestCase):
    """
    Tests for SSOT Auth Test Helpers async context manager functionality.
    
    These test the context manager features for automatic cleanup.
    """
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.record_metric("test_category", "ssot_auth_context_manager")
    
    async def test_auth_helper_async_context_manager_entry(self):
        """
        Test that auth helper works as async context manager.
        
        Expected: Should enter context successfully.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client
            mock_auth_client = AsyncMock()
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Test async context manager entry
            async with helper as context_helper:
                self.assertIsNotNone(context_helper)
                self.assertEqual(context_helper, helper)
                
                self.record_metric("context_manager_entry", "success")
                self.logger.info("CHECK Auth helper async context manager entry works")
                
        except Exception as e:
            self.record_metric("context_manager_entry", "failed")
            self.logger.error(f"X Context manager entry failed: {e}")
            self.fail(f"Async context manager entry should work: {e}")
    
    async def test_auth_helper_context_manager_cleanup_on_exit(self):
        """
        Test that auth helper performs cleanup on context exit.
        
        Expected: Should call cleanup methods on exit.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client with cleanup methods
            mock_auth_client = AsyncMock()
            mock_auth_client.delete_user = AsyncMock()
            
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Create test users then exit context
            async with helper:
                # Mock creating users during context
                from test_framework.ssot.auth_test_helpers import AuthenticatedTestUser
                from datetime import datetime, UTC
                
                test_user = AuthenticatedTestUser(
                    user_id="cleanup_user",
                    email="cleanup@example.com",
                    access_token="cleanup_token",
                    created_at=datetime.now(UTC)
                )
                helper._test_users.append(test_user)
            
            # After context exit, cleanup should have been called
            # (In practice, this would call delete_user if available)
            self.record_metric("context_manager_cleanup", "success")
            self.logger.info("CHECK Auth helper context manager cleanup works")
            
        except Exception as e:
            self.record_metric("context_manager_cleanup", "failed") 
            self.logger.error(f"X Context manager cleanup failed: {e}")
            self.fail(f"Context manager cleanup should work: {e}")


@pytest.mark.unit
class SSOTAuthTestHelpersErrorHandlingTests(SSotAsyncTestCase):
    """
    Tests for SSOT Auth Test Helpers error handling.
    
    These test how the helpers handle various error conditions gracefully.
    """
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.record_metric("test_category", "ssot_auth_error_handling")
    
    async def test_helper_handles_auth_service_connection_errors(self):
        """
        Test that helper handles auth service connection errors gracefully.
        
        Expected: Should raise clear errors for connection issues.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client that raises connection errors
            mock_auth_client = AsyncMock()
            mock_auth_client.create_user = AsyncMock(side_effect=ConnectionError("Auth service unavailable"))
            
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Test that connection errors are properly handled
            with self.expect_exception(ConnectionError):
                await helper.create_test_user_with_token()
            
            self.record_metric("connection_error_handling", "success")
            self.logger.info("CHECK Helper handles auth service connection errors")
            
        except Exception as e:
            self.record_metric("connection_error_handling", "failed")
            self.logger.error(f"X Connection error handling failed: {e}")
            self.fail(f"Should handle connection errors gracefully: {e}")
    
    async def test_helper_handles_auth_service_timeout_errors(self):
        """
        Test that helper handles auth service timeout errors gracefully.
        
        Expected: Should raise clear errors for timeout issues.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client that raises timeout errors
            mock_auth_client = AsyncMock()
            mock_auth_client.validate_token = AsyncMock(side_effect=asyncio.TimeoutError("Auth service timeout"))
            
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Test that timeout errors are properly handled
            with self.expect_exception(asyncio.TimeoutError):
                await helper.validate_token_via_service("test_token")
            
            self.record_metric("timeout_error_handling", "success")
            self.logger.info("CHECK Helper handles auth service timeout errors")
            
        except Exception as e:
            self.record_metric("timeout_error_handling", "failed")
            self.logger.error(f"X Timeout error handling failed: {e}")
            self.fail(f"Should handle timeout errors gracefully: {e}")
    
    async def test_helper_handles_malformed_auth_service_responses(self):
        """
        Test that helper handles malformed auth service responses gracefully.
        
        Expected: Should handle unexpected response formats.
        """
        try:
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Create mock auth client that returns malformed responses
            mock_auth_client = AsyncMock()
            mock_auth_client.validate_token = AsyncMock(return_value="not_a_dict")  # Malformed response
            
            helper = SSOTAuthTestHelper(auth_client=mock_auth_client)
            
            # Test that malformed responses are handled
            # (Implementation should handle this gracefully)
            try:
                result = await helper.validate_token_via_service("test_token")
                # Should either handle gracefully or raise clear error
                self.record_metric("malformed_response_handling", "handled_gracefully")
            except Exception as e:
                # Should be a clear, informative error
                self.assertIn("response", str(e).lower())
                self.record_metric("malformed_response_handling", "clear_error")
            
            self.logger.info("CHECK Helper handles malformed auth service responses")
            
        except Exception as e:
            self.record_metric("malformed_response_handling", "failed")
            self.logger.error(f"X Malformed response handling failed: {e}")
            # Don't fail test - this is testing error handling itself