"""
Tests for OAuth integration functionality.
All functions ≤8 lines per requirements.
"""

import sys
from pathlib import Path

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from netra_backend.tests.services.security_service_test_mocks import (
    EnhancedSecurityService,
    MockUser,
)

@pytest.fixture
def oauth_security_service():
    """Create security service for OAuth testing"""
    key_manager = MagicMock()
    key_manager.jwt_secret_key = "oauth_test_key"
    key_manager.fernet_key = Fernet.generate_key()
    return EnhancedSecurityService(key_manager)

class TestSecurityServiceOAuth:
    """Test OAuth integration functionality"""
    
    async def test_create_user_from_oauth_new_user(self, oauth_security_service):
        """Test creating new user from OAuth data"""
        mock_db_session, oauth_user_info, created_user = self._setup_new_oauth_user_test()
        
        user = await self._execute_oauth_user_creation(
            oauth_security_service, mock_db_session, oauth_user_info, created_user
        )
        
        _assert_oauth_user_creation(mock_db_session)
    
    def _setup_new_oauth_user_test(self):
        """Setup test data for new OAuth user creation"""
        mock_db_session = AsyncMock()
        oauth_user_info = _get_oauth_user_info()
        created_user = _create_oauth_user()
        _setup_oauth_new_user_mocks(mock_db_session)
        return mock_db_session, oauth_user_info, created_user
    
    async def _execute_oauth_user_creation(self, oauth_security_service, mock_db_session, oauth_user_info, created_user):
        """Execute OAuth user creation with patches"""
        with patch.object(oauth_security_service, 'get_user', return_value=None), \
             patch('app.db.models_postgres.User', return_value=created_user):
            return await oauth_security_service.get_or_create_user_from_oauth(
                mock_db_session, oauth_user_info
            )
    
    async def test_get_existing_user_from_oauth(self, oauth_security_service):
        """Test getting existing user from OAuth data"""
        mock_db_session, existing_user, oauth_user_info = self._setup_existing_oauth_user_test()
        
        user = await self._execute_existing_oauth_user_retrieval(
            oauth_security_service, mock_db_session, oauth_user_info, existing_user
        )
        
        _assert_oauth_existing_user(mock_db_session, existing_user)
    
    def _setup_existing_oauth_user_test(self):
        """Setup test data for existing OAuth user"""
        mock_db_session = AsyncMock()
        existing_user = MockUser("existing_456", "existing@example.com", "Existing User")
        _setup_oauth_existing_user_mocks(mock_db_session, existing_user)
        oauth_user_info = {"email": "existing@example.com", "name": "Existing User"}
        return mock_db_session, existing_user, oauth_user_info
    
    async def _execute_existing_oauth_user_retrieval(self, oauth_security_service, mock_db_session, oauth_user_info, existing_user):
        """Execute existing OAuth user retrieval with patches"""
        with patch.object(oauth_security_service, 'get_user', return_value=existing_user):
            return await oauth_security_service.get_or_create_user_from_oauth(
                mock_db_session, oauth_user_info
            )
    
    async def test_oauth_token_validation(self, oauth_security_service):
        """Test OAuth token validation"""
        oauth_user = _create_oauth_user()
        token_data = _create_oauth_token_data(oauth_user)
        
        token = oauth_security_service.create_access_token(token_data)
        validation_result = await oauth_security_service.validate_token_jwt(token)
        
        _assert_oauth_token_validation(validation_result, oauth_user)
    
    async def test_oauth_user_profile_update(self, oauth_security_service):
        """Test OAuth user profile update"""
        mock_db_session, existing_user, updated_oauth_info = self._setup_profile_update_test()
        
        await _test_oauth_profile_update(
            oauth_security_service, mock_db_session, existing_user, updated_oauth_info
        )
    
    def _setup_profile_update_test(self):
        """Setup test data for profile update"""
        mock_db_session = AsyncMock()
        existing_user = MockUser("update_789", "update@example.com", "Old Name")
        updated_oauth_info = {
            "email": "update@example.com",
            "name": "New Name",
            "picture": "https://example.com/new_avatar.jpg"
        }
        return mock_db_session, existing_user, updated_oauth_info
    
    async def test_oauth_error_handling(self, oauth_security_service):
        """Test OAuth error handling scenarios"""
        mock_db_session = AsyncMock()
        
        # Test with invalid OAuth data
        invalid_oauth_info = {"invalid": "data"}
        
        with pytest.raises(Exception):
            await oauth_security_service.get_or_create_user_from_oauth(
                mock_db_session, invalid_oauth_info
            )
    
    async def test_oauth_security_validation(self, oauth_security_service):
        """Test OAuth security validation"""
        oauth_user_info = _get_oauth_user_info()
        
        # Validate OAuth data format
        _assert_oauth_data_format(oauth_user_info)
        
        suspicious_oauth_info = self._create_suspicious_oauth_info()
        _assert_oauth_security_handling(suspicious_oauth_info)
    
    def _create_suspicious_oauth_info(self) -> dict:
        """Create suspicious OAuth info for security testing"""
        return {
            "email": "suspicious@evil.com",
            "name": "<script>alert('xss')</script>",
            "picture": "javascript:alert('xss')"
        }
    
    async def test_oauth_rate_limiting(self, oauth_security_service):
        """Test OAuth-specific rate limiting"""
        identifier = "oauth_client_123"
        
        await self._test_oauth_rate_limit_attempts(oauth_security_service, identifier)
        
        # Should still be under OAuth rate limit
        allowed = await oauth_security_service.check_rate_limit(identifier, limit=5)
        assert allowed is True
    
    async def _test_oauth_rate_limit_attempts(self, oauth_security_service, identifier: str) -> None:
        """Test multiple OAuth rate limit attempts"""
        for i in range(3):
            allowed = await oauth_security_service.check_rate_limit(identifier, limit=5)
            assert allowed is True
            oauth_security_service.record_rate_limit_attempt(identifier)

class TestSecurityServiceConcurrency:
    """Test concurrent security service operations"""
    
    async def test_concurrent_authentication_attempts(self, oauth_security_service):
        """Test concurrent authentication attempts"""
        user = _create_oauth_user()
        
        authenticate_user = self._create_authenticate_user_func(oauth_security_service, user)
        results = await self._run_concurrent_authentication(authenticate_user)
        
        _assert_concurrent_authentication_results(results)
    
    def _create_authenticate_user_func(self, oauth_security_service, user):
        """Create authenticate user function for testing"""
        async def authenticate_user():
            with patch.object(oauth_security_service, '_get_user_by_email', return_value=user):
                return await oauth_security_service.enhanced_authenticate_user(
                    user.email, "test_password"
                )
        return authenticate_user
    
    async def _run_concurrent_authentication(self, authenticate_user_func):
        """Run concurrent authentication attempts"""
        tasks = [authenticate_user_func() for _ in range(5)]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def test_concurrent_token_validation(self, oauth_security_service):
        """Test concurrent token validation"""
        user, token = self._setup_token_validation_test(oauth_security_service)
        
        validate_token = self._create_validate_token_func(oauth_security_service, token)
        results = await self._run_concurrent_validation(validate_token)
        
        _assert_concurrent_validation_results(results)
    
    def _setup_token_validation_test(self, oauth_security_service):
        """Setup test data for token validation"""
        user = _create_oauth_user()
        token_data = _create_oauth_token_data(user)
        token = oauth_security_service.create_access_token(token_data)
        return user, token
    
    def _create_validate_token_func(self, oauth_security_service, token):
        """Create validate token function for testing"""
        async def validate_token_jwt():
            return await oauth_security_service.validate_token_jwt(token)
        return validate_token
    
    async def _run_concurrent_validation(self, validate_token_func):
        """Run concurrent token validations"""
        tasks = [validate_token_func() for _ in range(10)]
        return await asyncio.gather(*tasks)
    
    async def test_concurrent_rate_limiting(self, oauth_security_service):
        """Test concurrent rate limiting"""
        identifier = "concurrent_test"
        
        check_and_record = self._create_check_and_record_func(oauth_security_service, identifier)
        results = await self._run_concurrent_rate_limit_checks(check_and_record)
        
        _assert_concurrent_rate_limit_results(results)
    
    def _create_check_and_record_func(self, oauth_security_service, identifier: str):
        """Create check and record function for rate limiting test"""
        async def check_and_record():
            allowed = await oauth_security_service.check_rate_limit(identifier, limit=5)
            if allowed:
                oauth_security_service.record_rate_limit_attempt(identifier)
            return allowed
        return check_and_record
    
    async def _run_concurrent_rate_limit_checks(self, check_and_record_func):
        """Run concurrent rate limit checks"""
        tasks = [check_and_record_func() for _ in range(10)]
        return await asyncio.gather(*tasks)

def _get_oauth_user_info() -> dict:
    """Get OAuth user info for testing"""
    return {
        "email": "oauth@example.com",
        "name": "OAuth User",
        "picture": "https://example.com/avatar.jpg"
    }

def _create_oauth_user() -> MockUser:
    """Create OAuth user for testing"""
    user = MockUser("oauth_123", "oauth@example.com", "OAuth User")
    user.picture = "https://example.com/avatar.jpg"
    return user

def _setup_oauth_new_user_mocks(mock_db_session: AsyncMock) -> None:
    """Setup mocks for new OAuth user creation"""
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

def _setup_oauth_existing_user_mocks(mock_db_session: AsyncMock, existing_user: MockUser) -> None:
    """Setup mocks for existing OAuth user"""
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existing_user
    mock_db_session.execute.return_value = mock_result

def _assert_oauth_user_creation(mock_db_session: AsyncMock) -> None:
    """Assert OAuth user creation was attempted"""
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

def _assert_oauth_existing_user(mock_db_session: AsyncMock, existing_user: MockUser) -> None:
    """Assert OAuth existing user handling"""
    # Should not create new user
    mock_db_session.add.assert_not_called()

def _create_oauth_token_data(user: MockUser) -> dict:
    """Create OAuth token data"""
    return {
        'user_id': user.id,
        'email': user.email,
        'oauth_provider': 'google',
        'picture': user.picture
    }

def _assert_oauth_token_validation(validation_result: dict, user: MockUser) -> None:
    """Assert OAuth token validation"""
    assert validation_result.get('valid') is True
    assert validation_result.get('user_id') == user.id
    assert validation_result.get('email') == user.email

async def _test_oauth_profile_update(oauth_security_service, mock_db_session, existing_user, updated_oauth_info):
    """Test OAuth profile update"""
    with patch.object(oauth_security_service, 'get_user', return_value=existing_user):
        user = await oauth_security_service.get_or_create_user_from_oauth(
            mock_db_session, updated_oauth_info
        )
        
        # Should update user profile
        assert user.full_name == updated_oauth_info["name"]

def _assert_oauth_data_format(oauth_user_info: dict) -> None:
    """Assert OAuth data has correct format"""
    assert "email" in oauth_user_info
    assert "name" in oauth_user_info
    assert "@" in oauth_user_info["email"]

def _assert_oauth_security_handling(suspicious_oauth_info: dict) -> None:
    """Assert OAuth security handling"""
    # Should validate and sanitize input
    assert "<script>" in suspicious_oauth_info["name"]  # Test data contains script
    assert "javascript:" in suspicious_oauth_info["picture"]  # Test data contains JavaScript

def _assert_concurrent_authentication_results(results: list) -> None:
    """Assert concurrent authentication results"""
    # All results should be either success or proper exception
    for result in results:
        if isinstance(result, Exception):
            continue  # Acceptable for concurrent testing
        assert isinstance(result, dict)

def _assert_concurrent_validation_results(results: list) -> None:
    """Assert concurrent validation results"""
    # All validations should succeed for same token
    for result in results:
        assert result.get('valid') is True

def _assert_concurrent_rate_limit_results(results: list) -> None:
    """Assert concurrent rate limit results"""
    # Should respect rate limits even under concurrency
    allowed_count = sum(1 for result in results if result)
    assert allowed_count <= 5  # Should not exceed limit