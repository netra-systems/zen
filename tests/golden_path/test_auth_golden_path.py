"""
Emergency Golden Path Test: Authentication Flow Core
Critical test for validating user login and token management for Golden Path.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Use absolute imports as required by SSOT
from netra_backend.app.auth_integration.auth import AuthIntegrationClient
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestAuthGoldenPath(SSotAsyncTestCase):
    """Emergency test for core authentication flow that enables Golden Path user access."""
    
    async def asyncSetUp(self):
        """Set up test environment with isolated auth configuration."""
        self.env = IsolatedEnvironment()
        self.env.set("ENVIRONMENT", "test")
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8081")
        self.env.set("JWT_SECRET", "test-secret-key")
        
        # Mock auth service responses
        self.mock_auth_response = {
            "access_token": "test-access-token-123",
            "refresh_token": "test-refresh-token-456", 
            "user": {
                "id": "user-123",
                "email": "test@example.com",
                "name": "Test User"
            },
            "expires_in": 3600
        }
        
    async def test_user_login_success(self):
        """Test successful user login returns proper tokens."""
        # Arrange
        with patch('netra_backend.app.auth_integration.auth.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = self.mock_auth_response
            mock_post.return_value = mock_response
            
            auth_client = AuthIntegrationClient()
            
            # Act
            result = await auth_client.authenticate_user(
                email="test@example.com",
                password="password123"
            )
            
            # Assert
            self.assertEqual(result["access_token"], "test-access-token-123")
            self.assertEqual(result["user"]["email"], "test@example.com")
            self.assertEqual(result["user"]["id"], "user-123")
            
            # Verify auth service was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            self.assertEqual(call_args[0][0], "http://localhost:8081/auth/login")
            
    async def test_user_login_invalid_credentials(self):
        """Test user login with invalid credentials returns proper error."""
        # Arrange
        with patch('netra_backend.app.auth_integration.auth.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "detail": "Invalid credentials"
            }
            mock_post.return_value = mock_response
            
            auth_client = AuthIntegrationClient()
            
            # Act & Assert
            with self.assertRaises(Exception) as context:
                await auth_client.authenticate_user(
                    email="test@example.com",
                    password="wrong-password"
                )
            
            self.assertIn("Invalid credentials", str(context.exception))
            
    async def test_token_refresh_success(self):
        """Test successful token refresh returns new tokens."""
        # Arrange
        refresh_response = {
            "access_token": "new-access-token-789",
            "refresh_token": "new-refresh-token-012",
            "expires_in": 3600
        }
        
        with patch('netra_backend.app.auth_integration.auth.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = refresh_response
            mock_post.return_value = mock_response
            
            auth_client = AuthIntegrationClient()
            
            # Act
            result = await auth_client.refresh_token(
                refresh_token="test-refresh-token-456"
            )
            
            # Assert
            self.assertEqual(result["access_token"], "new-access-token-789")
            self.assertEqual(result["refresh_token"], "new-refresh-token-012")
            
            # Verify refresh endpoint was called
            call_args = mock_post.call_args
            self.assertEqual(call_args[0][0], "http://localhost:8081/auth/refresh")
            
    async def test_token_validation_success(self):
        """Test successful token validation returns user info."""
        # Arrange
        validation_response = {
            "valid": True,
            "user": {
                "id": "user-123",
                "email": "test@example.com",
                "name": "Test User"
            }
        }
        
        with patch('netra_backend.app.auth_integration.auth.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = validation_response
            mock_get.return_value = mock_response
            
            auth_client = AuthIntegrationClient()
            
            # Act
            result = await auth_client.validate_token(
                token="test-access-token-123"
            )
            
            # Assert
            self.assertTrue(result["valid"])
            self.assertEqual(result["user"]["id"], "user-123")
            self.assertEqual(result["user"]["email"], "test@example.com")
            
    async def test_token_validation_invalid_token(self):
        """Test token validation with invalid token returns proper error."""
        # Arrange
        with patch('netra_backend.app.auth_integration.auth.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "valid": False,
                "detail": "Invalid token"
            }
            mock_get.return_value = mock_response
            
            auth_client = AuthIntegrationClient()
            
            # Act
            result = await auth_client.validate_token(
                token="invalid-token"
            )
            
            # Assert
            self.assertFalse(result["valid"])
            self.assertIn("Invalid token", result["detail"])
            
    async def test_user_logout_success(self):
        """Test successful user logout invalidates token."""
        # Arrange
        with patch('netra_backend.app.auth_integration.auth.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "message": "Successfully logged out"
            }
            mock_post.return_value = mock_response
            
            auth_client = AuthIntegrationClient()
            
            # Act
            result = await auth_client.logout_user(
                token="test-access-token-123"
            )
            
            # Assert
            self.assertEqual(result["status"], "success")
            
            # Verify logout endpoint was called with auth header
            call_args = mock_post.call_args
            self.assertEqual(call_args[0][0], "http://localhost:8081/auth/logout")
            self.assertIn("Authorization", call_args[1]["headers"])
            
    async def test_complete_golden_path_auth_flow(self):
        """Test complete authentication flow: login -> validate -> refresh -> logout."""
        auth_client = AuthIntegrationClient()
        
        # Step 1: Login
        with patch('netra_backend.app.auth_integration.auth.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = self.mock_auth_response
            mock_post.return_value = mock_response
            
            login_result = await auth_client.authenticate_user(
                email="test@example.com",
                password="password123"
            )
            
            access_token = login_result["access_token"]
            refresh_token = login_result["refresh_token"]
            
        # Step 2: Validate token
        with patch('netra_backend.app.auth_integration.auth.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "valid": True,
                "user": self.mock_auth_response["user"]
            }
            mock_get.return_value = mock_response
            
            validation_result = await auth_client.validate_token(token=access_token)
            
        # Step 3: Refresh token
        with patch('netra_backend.app.auth_integration.auth.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600
            }
            mock_post.return_value = mock_response
            
            refresh_result = await auth_client.refresh_token(refresh_token=refresh_token)
            new_access_token = refresh_result["access_token"]
            
        # Step 4: Logout
        with patch('netra_backend.app.auth_integration.auth.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_post.return_value = mock_response
            
            logout_result = await auth_client.logout_user(token=new_access_token)
            
        # Assert complete flow worked
        self.assertEqual(login_result["user"]["email"], "test@example.com")
        self.assertTrue(validation_result["valid"])
        self.assertIsNotNone(refresh_result["access_token"])
        self.assertEqual(logout_result["status"], "success")
        
    async def test_auth_client_configuration_validation(self):
        """Test that auth client properly validates its configuration."""
        # Test missing auth service URL
        with patch.object(self.env, 'get', return_value=None):
            with self.assertRaises(Exception) as context:
                auth_client = AuthIntegrationClient()
                await auth_client.authenticate_user("test@example.com", "password")
                
            self.assertIn("AUTH_SERVICE_URL", str(context.exception))
            
    async def test_auth_service_connection_failure(self):
        """Test handling of auth service connection failures."""
        # Arrange
        with patch('netra_backend.app.auth_integration.auth.requests.post') as mock_post:
            mock_post.side_effect = Exception("Connection refused")
            
            auth_client = AuthIntegrationClient()
            
            # Act & Assert
            with self.assertRaises(Exception) as context:
                await auth_client.authenticate_user(
                    email="test@example.com",
                    password="password123"
                )
            
            self.assertIn("Connection refused", str(context.exception))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])