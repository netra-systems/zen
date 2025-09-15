"""
Standalone Auth Service Unit Tests - Phase 1 Issue #925
Docker-independent unit tests focusing on core auth functionality

These tests validate JWT operations, token validation, and basic auth logic
without requiring Docker services or external backend dependencies.

MISSION: Enable auth unit testing without Docker infrastructure dependency
"""

import os
import sys
import pytest
import unittest.mock
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import json
import jwt

# Ensure auth_service path is available
sys.path.insert(0, os.path.dirname(__file__))

# Core auth service imports - direct module imports to avoid cross-service dependencies
try:
    from auth_core.core.jwt_handler import JWTHandler
    from auth_core.config import AuthConfig
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Auth service imports not available: {e}")
    IMPORTS_AVAILABLE = False


class TestJWTHandlerStandalone(unittest.TestCase):
    """
    Standalone JWT Handler unit tests
    Test core JWT functionality without external service dependencies
    """
    
    def setUp(self):
        """Set up test environment"""
        if not IMPORTS_AVAILABLE:
            self.skipTest("Auth service imports not available")
            
        # Mock shared.isolated_environment to avoid backend dependency
        self.env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.env_patcher.start()
        self.mock_env.return_value = {
            'ENVIRONMENT': 'test',
            'JWT_SECRET_KEY': 'test-secret-key-for-unit-testing-32chars-long',
            'AUTH_SERVICE_ID': 'test-auth-service'
        }
        
        # Mock AuthConfig to return test values
        self.config_patcher = patch.object(AuthConfig, 'get_jwt_secret')
        self.mock_config = self.config_patcher.start()
        self.mock_config.return_value = 'test-secret-key-for-unit-testing-32chars-long'
        
        # Mock other AuthConfig methods
        with patch.object(AuthConfig, 'get_service_secret', return_value='service-secret'):
            with patch.object(AuthConfig, 'get_service_id', return_value='test-service'):
                with patch.object(AuthConfig, 'get_jwt_algorithm', return_value='HS256'):
                    with patch.object(AuthConfig, 'get_jwt_access_expiry_minutes', return_value=60):
                        with patch.object(AuthConfig, 'get_jwt_refresh_expiry_days', return_value=7):
                            with patch.object(AuthConfig, 'get_jwt_service_expiry_minutes', return_value=120):
                                with patch.object(AuthConfig, 'get_environment', return_value='test'):
                                    self.jwt_handler = JWTHandler()
    
    def tearDown(self):
        """Clean up test environment"""
        if IMPORTS_AVAILABLE:
            self.env_patcher.stop()
            self.config_patcher.stop()

    @pytest.mark.unit
    def test_jwt_handler_initialization(self):
        """Test JWT handler initializes correctly"""
        self.assertIsNotNone(self.jwt_handler)
        self.assertEqual(self.jwt_handler.algorithm, 'HS256')
        self.assertIsNotNone(self.jwt_handler.secret)

    @pytest.mark.unit
    def test_create_access_token(self):
        """Test creating access tokens"""
        user_id = "test-user-123"
        email = "test@example.com"
        permissions = ["read", "write"]
        
        token = self.jwt_handler.create_access_token(user_id, email, permissions)
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split('.')), 3)  # Valid JWT format

    @pytest.mark.unit
    def test_create_refresh_token(self):
        """Test creating refresh tokens"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = self.jwt_handler.create_refresh_token(user_id, email)
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split('.')), 3)  # Valid JWT format

    @pytest.mark.unit
    def test_validate_access_token(self):
        """Test validating access tokens"""
        user_id = "test-user-123"
        email = "test@example.com"
        permissions = ["read", "write"]
        
        # Create token
        token = self.jwt_handler.create_access_token(user_id, email, permissions)
        
        # Validate token
        payload = self.jwt_handler.validate_token(token, "access")
        
        self.assertIsNotNone(payload)
        self.assertEqual(payload['sub'], user_id)
        self.assertEqual(payload['email'], email)
        self.assertEqual(payload['permissions'], permissions)
        self.assertEqual(payload['token_type'], 'access')

    @pytest.mark.unit
    def test_validate_refresh_token(self):
        """Test validating refresh tokens"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        # Create refresh token
        token = self.jwt_handler.create_refresh_token(user_id, email)
        
        # Validate token
        payload = self.jwt_handler.validate_token(token, "refresh")
        
        self.assertIsNotNone(payload)
        self.assertEqual(payload['sub'], user_id)
        self.assertEqual(payload['token_type'], 'refresh')

    @pytest.mark.unit
    def test_token_expiration(self):
        """Test token expiration behavior"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        # Create token with short expiry for testing
        with patch.object(self.jwt_handler, '_get_token_expiry', return_value=0):  # Immediate expiry
            token = self.jwt_handler.create_access_token(user_id, email)
            
            # Token should be expired immediately
            payload = self.jwt_handler.validate_token(token, "access")
            self.assertIsNone(payload)  # Should fail validation due to expiry

    @pytest.mark.unit
    def test_invalid_token_format(self):
        """Test handling of invalid token formats"""
        invalid_tokens = [
            "",  # Empty string
            "not.a.token",  # Wrong format
            "invalid",  # Not JWT format
            None,  # None value
            "too.few",  # Only 2 segments
            "too.many.segments.here",  # Too many segments
        ]
        
        for invalid_token in invalid_tokens:
            payload = self.jwt_handler.validate_token(invalid_token, "access")
            self.assertIsNone(payload, f"Expected None for invalid token: {invalid_token}")

    @pytest.mark.unit
    def test_token_type_mismatch(self):
        """Test token type validation"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        # Create access token
        access_token = self.jwt_handler.create_access_token(user_id, email)
        
        # Try to validate as refresh token (should fail)
        payload = self.jwt_handler.validate_token(access_token, "refresh")
        self.assertIsNone(payload)

    @pytest.mark.unit
    def test_token_blacklisting(self):
        """Test token blacklisting functionality"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        # Create and validate token
        token = self.jwt_handler.create_access_token(user_id, email)
        payload = self.jwt_handler.validate_token(token, "access")
        self.assertIsNotNone(payload)
        
        # Blacklist token
        success = self.jwt_handler.blacklist_token(token)
        self.assertTrue(success)
        
        # Token should now fail validation
        payload = self.jwt_handler.validate_token(token, "access")
        self.assertIsNone(payload)

    @pytest.mark.unit
    def test_user_blacklisting(self):
        """Test user blacklisting functionality"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        # Create and validate token
        token = self.jwt_handler.create_access_token(user_id, email)
        payload = self.jwt_handler.validate_token(token, "access")
        self.assertIsNotNone(payload)
        
        # Blacklist user
        success = self.jwt_handler.blacklist_user(user_id)
        self.assertTrue(success)
        
        # All tokens for this user should now fail validation
        payload = self.jwt_handler.validate_token(token, "access")
        self.assertIsNone(payload)

    @pytest.mark.unit
    def test_extract_user_id(self):
        """Test extracting user ID from token without full validation"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        token = self.jwt_handler.create_access_token(user_id, email)
        
        extracted_user_id = self.jwt_handler.extract_user_id(token)
        self.assertEqual(extracted_user_id, user_id)

    @pytest.mark.unit
    def test_refresh_access_token(self):
        """Test refreshing access tokens using refresh token"""
        user_id = "test-user-123"
        email = "test@example.com"
        permissions = ["read", "write"]
        
        # Create refresh token
        refresh_token = self.jwt_handler.create_refresh_token(user_id, email, permissions)
        
        # Refresh to get new access token
        result = self.jwt_handler.refresh_access_token(refresh_token)
        
        self.assertIsNotNone(result)
        new_access_token, new_refresh_token = result
        
        # Validate new tokens
        access_payload = self.jwt_handler.validate_token(new_access_token, "access")
        self.assertIsNotNone(access_payload)
        self.assertEqual(access_payload['sub'], user_id)
        
        refresh_payload = self.jwt_handler.validate_token(new_refresh_token, "refresh")
        self.assertIsNotNone(refresh_payload)
        self.assertEqual(refresh_payload['sub'], user_id)

    @pytest.mark.unit
    def test_create_service_token(self):
        """Test creating service-to-service tokens"""
        service_id = "test-service-123"
        service_name = "test-service"
        
        token = self.jwt_handler.create_service_token(service_id, service_name)
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split('.')), 3)  # Valid JWT format
        
        # Validate service token
        payload = self.jwt_handler.validate_token(token, "service")
        self.assertIsNotNone(payload)
        self.assertEqual(payload['sub'], service_id)
        self.assertEqual(payload['service'], service_name)

    @pytest.mark.unit
    def test_jwt_security_validation(self):
        """Test JWT security validation"""
        user_id = "test-user-123"
        email = "test@example.com"
        
        # Create valid token
        valid_token = self.jwt_handler.create_access_token(user_id, email)
        
        # Test security validation
        is_secure = self.jwt_handler._validate_token_security_consolidated(valid_token)
        self.assertTrue(is_secure)
        
        # Test with obviously invalid token
        invalid_token = "invalid.token.format"
        is_secure = self.jwt_handler._validate_token_security_consolidated(invalid_token)
        self.assertFalse(is_secure)

    @pytest.mark.unit
    def test_get_performance_stats(self):
        """Test performance statistics retrieval"""
        stats = self.jwt_handler.get_performance_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('cache_stats', stats)
        self.assertIn('blacklist_stats', stats)
        self.assertIn('performance_optimizations', stats)

    @pytest.mark.unit
    def test_mock_token_rejection(self):
        """Test that mock tokens are properly rejected"""
        mock_tokens = [
            "mock_token_123",
            "mock_access_token",
            "mock_refresh_token"
        ]
        
        for mock_token in mock_tokens:
            payload = self.jwt_handler.validate_token(mock_token, "access")
            self.assertIsNone(payload, f"Mock token should be rejected: {mock_token}")


class TestAuthConfigStandalone(unittest.TestCase):
    """
    Standalone AuthConfig unit tests
    Test configuration handling without external dependencies
    """
    
    def setUp(self):
        """Set up test environment"""
        if not IMPORTS_AVAILABLE:
            self.skipTest("Auth service imports not available")
    
    @pytest.mark.unit
    def test_auth_config_import(self):
        """Test that AuthConfig can be imported and used"""
        # This test validates that the import structure works
        self.assertTrue(hasattr(AuthConfig, 'get_jwt_secret'))
        self.assertTrue(hasattr(AuthConfig, 'get_environment'))


if __name__ == "__main__":
    # Run tests directly if called as script
    if IMPORTS_AVAILABLE:
        # Set up environment for direct execution using IsolatedEnvironment
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from shared.isolated_environment import get_env
        env = get_env()
        env.set('ENVIRONMENT', 'test')
        env.set('JWT_SECRET_KEY', 'test-secret-key-for-unit-testing-32chars-long')
        
        unittest.main(argv=[''], exit=False, verbosity=2)
    else:
        print("ERROR: Auth service imports not available. Cannot run standalone tests.")
        print("Make sure you're running from the auth_service directory and dependencies are installed.")