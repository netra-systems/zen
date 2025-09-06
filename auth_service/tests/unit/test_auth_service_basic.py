"""
Basic unit tests for AuthService
Tests core authentication functionality with real services
"""
import uuid
import pytest
import pytest_asyncio
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.models.auth_models import LoginRequest, User
from shared.isolated_environment import IsolatedEnvironment


class TestAuthServiceCore:
    """Test core AuthService functionality"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.service = AuthService()
        self.email = f"test_{uuid.uuid4()}@example.com"
        self.password = "TestPassword123!"
        self.name = f"Test User {uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test user creation"""
        user_id = await self.service.create_user(self.email, self.password, self.name)
        assert user_id is not None
        assert len(user_id) > 0
    
    @pytest.mark.asyncio
    async def test_authenticate_user(self):
        """Test user authentication"""
        # Create user first
        await self.service.create_user(self.email, self.password, self.name)
        
        # Authenticate
        result = await self.service.authenticate_user(self.email, self.password)
        assert result is not None
        assert len(result) == 2  # Returns (user_id, user_data)
        user_id, user_data = result
        assert user_id is not None
        assert user_data["email"] == self.email
    
    @pytest.mark.asyncio
    async def test_authenticate_with_wrong_password_fails(self):
        """Test authentication fails with wrong password"""
        await self.service.create_user(self.email, self.password, self.name)
        result = await self.service.authenticate_user(self.email, "WrongPassword!")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_create_access_token(self):
        """Test access token creation"""
        user_id = await self.service.create_user(self.email, self.password, self.name)
        token = await self.service.create_access_token(user_id, self.email, ["read"])
        assert token is not None
        assert len(token.split('.')) == 3  # JWT format
    
    @pytest.mark.asyncio
    async def test_create_refresh_token(self):
        """Test refresh token creation"""
        user_id = await self.service.create_user(self.email, self.password, self.name)
        token = await self.service.create_refresh_token(user_id, self.email, ["read"])
        assert token is not None
        assert len(token.split('.')) == 3
    
    @pytest.mark.asyncio
    async def test_validate_token(self):
        """Test token validation"""
        user_id = await self.service.create_user(self.email, self.password, self.name)
        access_token = await self.service.create_access_token(user_id, self.email, ["read"])
        
        response = await self.service.validate_token(access_token, "access")
        assert response is not None
        assert response.valid is True
        assert response.user_id == user_id
    
    @pytest.mark.asyncio
    async def test_refresh_tokens(self):
        """Test token refresh"""
        user_id = await self.service.create_user(self.email, self.password, self.name)
        refresh_token = await self.service.create_refresh_token(user_id, self.email, ["read"])
        
        result = await self.service.refresh_tokens(refresh_token)
        assert result is not None
        assert len(result) == 2
        new_access, new_refresh = result
        assert new_access != refresh_token
        assert new_refresh != refresh_token
    
    @pytest.mark.asyncio
    async def test_blacklist_token(self):
        """Test token blacklisting"""
        user_id = await self.service.create_user(self.email, self.password, self.name)
        token = await self.service.create_access_token(user_id, self.email)
        
        # Blacklist the token
        await self.service.blacklist_token(token)
        
        # Validation should fail
        response = await self.service.validate_token(token, "access")
        assert response is None or response.valid is False
    
    @pytest.mark.asyncio
    async def test_hash_and_verify_password(self):
        """Test password hashing and verification"""
        hashed = await self.service.hash_password(self.password)
        assert hashed != self.password
        assert len(hashed) > len(self.password)
        
        is_valid = await self.service.verify_password(self.password, hashed)
        assert is_valid is True
        
        is_invalid = await self.service.verify_password("WrongPassword", hashed)
        assert is_invalid is False
    
    @pytest.mark.asyncio
    async def test_register_user(self):
        """Test user registration"""
        user_data = await self.service.register_user(self.email, self.password, "Test User")
        assert user_data is not None
        assert "user_id" in user_data
        assert user_data.get("email") == self.email
    
    @pytest.mark.asyncio
    async def test_duplicate_registration_fails(self):
        """Test duplicate email registration fails"""
        await self.service.register_user(self.email, self.password, "User 1")
        
        # Try to register with same email
        with pytest.raises(Exception):
            await self.service.register_user(self.email, "Different123!", "User 2")
    
    @pytest.mark.asyncio
    async def test_invalidate_user_sessions(self):
        """Test invalidating all user sessions"""
        user_id = await self.service.create_user(self.email, self.password, self.name)
        
        # This should not raise an error
        await self.service.invalidate_user_sessions(user_id)
        assert True  # If we get here, it worked
    
    @pytest.mark.asyncio
    async def test_create_service_token(self):
        """Test service token creation"""
        service_id = f"service_{uuid.uuid4()}"
        token = await self.service.create_service_token(service_id)
        assert token is not None
        assert len(token.split('.')) == 3