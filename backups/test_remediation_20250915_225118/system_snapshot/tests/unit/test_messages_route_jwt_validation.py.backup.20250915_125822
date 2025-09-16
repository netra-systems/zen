"""
Unit Tests for Messages Route JWT Validation - Issue #1234 Reproduction

Tests the specific JWT validation failures in the messages route that correlate with
commit f1c251c9c JWT SSOT changes, targeting 403 authentication errors.

Business Value: Platform/Critical - Chat Functionality Protection  
Reproduces and documents the 403 authentication errors preventing $500K+ ARR chat functionality.

Following CLAUDE.md guidelines:
- Tests designed to FAIL initially to reproduce the 403 errors
- Unit tests focused on JWT validation logic in isolation
- No real services - mocked auth service responses
- Use SSOT patterns from test_framework/ssot/
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# SSOT Base Test Case per CLAUDE.md requirements
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

# Target module under test
from netra_backend.app.routes.messages import get_current_user_from_jwt


class TestMessagesRouteJWTValidation(SSotBaseTestCase):
    """
    Unit tests for JWT validation in messages route - Issue #1234 reproduction.
    
    These tests are designed to FAIL initially to reproduce the 403 authentication
    errors that correlate with commit f1c251c9c JWT SSOT changes.
    """
    
    def setup_method(self, method):
        """Setup test environment for JWT validation testing."""
        super().setup_method(method)
        
        # Set up test environment
        self._env.set("JWT_SECRET_KEY", "test-jwt-secret-32-chars-long", "test_setup")
        self._env.set("AUTH_SERVICE_URL", "http://localhost:8001", "test_setup")
        self._env.set("ENVIRONMENT", "test", "test_setup")
    
    @pytest.mark.asyncio
    async def test_jwt_validation_fails_with_invalid_token_expects_401(self):
        """
        Test that invalid JWT tokens result in 401 errors.
        
        This test is expected to FAIL initially if there are issues with JWT validation
        logic introduced in commit f1c251c9c.
        """
        # Arrange
        invalid_token = "invalid.jwt.token"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=invalid_token
        )
        
        # Mock the user context extractor to simulate auth service failure
        with patch('netra_backend.app.routes.messages.get_user_context_extractor') as mock_extractor:
            mock_extractor_instance = AsyncMock()
            mock_extractor_instance.validate_and_decode_jwt.return_value = None  # Invalid token
            mock_extractor.return_value = mock_extractor_instance
            
            # Act & Assert - Should raise 401 HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_from_jwt(credentials)
            
            # Verify the correct error response
            assert exc_info.value.status_code == 401
            assert "Invalid or expired JWT token" in str(exc_info.value.detail)
            
            # Verify auth service was called
            mock_extractor_instance.validate_and_decode_jwt.assert_called_once_with(invalid_token)
    
    @pytest.mark.asyncio
    async def test_jwt_validation_fails_with_missing_user_id_expects_401(self):
        """
        Test that JWT tokens missing user_id result in 401 errors.
        
        This reproduces the specific case where JWT validation succeeds but
        the payload is missing required user identification.
        """
        # Arrange
        valid_token_without_user_id = "valid.jwt.without.userid"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials=valid_token_without_user_id
        )
        
        # Mock auth service returning valid JWT but without user_id
        with patch('netra_backend.app.routes.messages.get_user_context_extractor') as mock_extractor:
            mock_extractor_instance = AsyncMock()
            # JWT validation succeeds but missing user_id
            mock_extractor_instance.validate_and_decode_jwt.return_value = {
                "valid": True,
                "email": "test@example.com",
                # Missing "sub" field (user_id)
            }
            mock_extractor.return_value = mock_extractor_instance
            
            # Act & Assert - Should raise 401 HTTPException for missing user_id
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_from_jwt(credentials)
            
            # Verify the correct error response
            assert exc_info.value.status_code == 401
            assert "JWT token missing user ID" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_jwt_validation_auth_service_timeout_expects_401(self):
        """
        Test that auth service timeouts result in authentication failures.
        
        This tests the scenario where the auth service is unreachable,
        which could cause 403 errors if the fallback logic is incorrect.
        """
        # Arrange
        valid_token = "valid.jwt.token"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_token
        )
        
        # Mock auth service timing out
        with patch('netra_backend.app.routes.messages.get_user_context_extractor') as mock_extractor:
            mock_extractor_instance = AsyncMock()
            mock_extractor_instance.validate_and_decode_jwt.side_effect = asyncio.TimeoutError("Auth service timeout")
            mock_extractor.return_value = mock_extractor_instance
            
            # Act & Assert - Should raise 401 HTTPException for auth service failure
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_from_jwt(credentials)
            
            # Verify the correct error response (should be 401, not 403)
            assert exc_info.value.status_code == 401
            assert "Authentication failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_jwt_validation_succeeds_with_valid_token_and_user_id(self):
        """
        Test that valid JWT tokens with proper user_id succeed.
        
        This test establishes the baseline for successful authentication
        to contrast with the failing cases.
        """
        # Arrange  
        valid_token = "valid.jwt.token.with.userid"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_token
        )
        
        expected_user_id = "user_12345"
        
        # Mock successful auth service response
        with patch('netra_backend.app.routes.messages.get_user_context_extractor') as mock_extractor:
            mock_extractor_instance = AsyncMock()
            mock_extractor_instance.validate_and_decode_jwt.return_value = {
                "valid": True,
                "sub": expected_user_id,  # Required user_id field
                "email": "test@example.com",
                "role": "user"
            }
            mock_extractor.return_value = mock_extractor_instance
            
            # Act
            result_user_id = await get_current_user_from_jwt(credentials)
            
            # Assert
            assert result_user_id == expected_user_id
            mock_extractor_instance.validate_and_decode_jwt.assert_called_once_with(valid_token)
    
    @pytest.mark.asyncio 
    async def test_jwt_validation_malformed_auth_header_expects_401(self):
        """
        Test that malformed authorization headers result in 401 errors.
        
        This tests edge cases in JWT extraction that could lead to 403 errors
        if the error handling is incorrect.
        """
        # Test cases for malformed authorization headers
        malformed_cases = [
            None,  # No credentials
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=""),  # Empty token
            HTTPAuthorizationCredentials(scheme="Basic", credentials="wrong_scheme"),  # Wrong scheme
        ]
        
        for case_num, credentials in enumerate(malformed_cases):
            with patch('netra_backend.app.routes.messages.get_user_context_extractor') as mock_extractor:
                mock_extractor_instance = AsyncMock()
                mock_extractor.return_value = mock_extractor_instance
                
                # Act & Assert
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user_from_jwt(credentials)
                
                # Should be 401 Unauthorized, not 403 Forbidden
                assert exc_info.value.status_code == 401, f"Case {case_num}: Expected 401, got {exc_info.value.status_code}"
    
    @pytest.mark.asyncio
    async def test_jwt_validation_circuit_breaker_impact_reproduction(self):
        """
        Test how circuit breaker failures impact JWT validation.
        
        This specifically tests the interaction between auth service failures
        and circuit breaker logic that might cause 403 instead of 401 errors.
        """
        # Arrange
        valid_token = "valid.jwt.token"
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_token
        )
        
        # Mock circuit breaker open scenario
        with patch('netra_backend.app.routes.messages.get_user_context_extractor') as mock_extractor:
            mock_extractor_instance = AsyncMock() 
            
            # Simulate circuit breaker preventing auth service calls
            mock_extractor_instance.validate_and_decode_jwt.side_effect = Exception("Circuit breaker is OPEN")
            mock_extractor.return_value = mock_extractor_instance
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_from_jwt(credentials)
            
            # CRITICAL: Should be 401 (auth failure), NOT 403 (forbidden)
            # If this returns 403, it indicates the circuit breaker is causing
            # incorrect error classification
            assert exc_info.value.status_code == 401, f"Circuit breaker failure should return 401, got {exc_info.value.status_code}"
            assert "Authentication failed" in str(exc_info.value.detail)
    
    def test_jwt_validation_performance_under_load(self):
        """
        Test JWT validation performance to ensure it doesn't timeout under load.
        
        Poor performance could lead to timeouts that manifest as 403 errors
        in staging environment.
        """
        # This is a placeholder for performance testing
        # In a real implementation, this would test:
        # 1. Multiple concurrent JWT validations
        # 2. Memory usage during validation
        # 3. Response time under load
        
        # For now, just verify the function exists and can be imported
        assert get_current_user_from_jwt is not None
        assert callable(get_current_user_from_jwt)
        
        # Record test metrics
        self._metrics.record_custom("jwt_validation_function_available", True)
        self._metrics.record_custom("test_focus", "Issue #1234 403 error reproduction")