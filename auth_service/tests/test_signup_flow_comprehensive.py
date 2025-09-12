"""
Comprehensive tests for user signup flow with edge cases
Tests database persistence, password hashing, validation, and error handling
"""
import pytest
# Using repository pattern per SSOT requirements
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from test_framework.database.test_database_manager import DatabaseTestManager as DatabaseTestManager
# Removed non-existent AuthManager import
from shared.isolated_environment import IsolatedEnvironment

from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.database.models import AuthUser
from auth_service.auth_core.database.repository import AuthUserRepository

# Import test framework for isolated environment and repository factory
from test_framework.environment_isolation import isolated_test_env
from auth_service.tests.helpers.test_repository_factory import (
    RepositoryFactory,
    mock_user_repository,
    real_user_repository
)


@pytest.fixture
def auth_service():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create auth service instance"""
    service = AuthService()
    return service


@pytest.fixture
async def real_repository_factory(isolated_test_env):
    """Create real repository factory with test environment"""
    factory = RepositoryFactory(use_real_db=True)
    await factory.initialize()
    yield factory
    await factory.cleanup()


@pytest.fixture
async def mock_repository_factory():
    """Create mock repository factory"""
    factory = RepositoryFactory(use_real_db=False)
    await factory.initialize()
    yield factory
    await factory.cleanup()


@pytest.fixture
def password_hasher():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create password hasher instance"""
    return PasswordHasher()


class TestEmailValidation:
    """Test email validation edge cases"""
    
    @pytest.mark.parametrize("email,expected", [
        ("valid@example.com", True),
        ("user.name@domain.co.uk", True),
        ("user+tag@example.org", True),
        ("user_123@test-domain.com", True),
        ("invalid", False),
        ("@example.com", False),
        ("user@", False),
        ("user @example.com", False),
        ("user@.com", False),
        ("user@domain", False),
        ("", False),
        (None, False),
    ])
    def test_email_validation(self, auth_service, email, expected):
        """Test various email formats"""
        if email is None:
            assert auth_service.validate_email("") == False
        else:
            assert auth_service.validate_email(email) == expected


class TestPasswordValidation:
    """Test password validation edge cases"""
    
    @pytest.mark.parametrize("password,should_pass,error_message", [
        ("ValidPass123!", True, "Password is valid"),
        ("short", False, "Password must be at least 8 characters long"),
        ("nouppercase123!", False, "Password must contain at least one uppercase letter"),
        ("NOLOWERCASE123!", False, "Password must contain at least one lowercase letter"),
        ("NoNumbers!", False, "Password must contain at least one number"),
        ("NoSpecial123", False, "Password must contain at least one special character"),
        ("", False, "Password must be at least 8 characters long"),
        ("        ", False, "Password must contain at least one uppercase letter"),  # 8 spaces
        ("Password123", False, "Password must contain at least one special character"),
        ("P@ssw0rd", True, "Password is valid"),  # Minimum valid
        ("Super$ecure123Password!", True, "Password is valid"),  # Strong password
    ])
    def test_password_validation(self, auth_service, password, should_pass, error_message):
        """Test various password formats"""
        is_valid, message = auth_service.validate_password(password)
        assert is_valid == should_pass
        assert message == error_message


class TestUserRegistration:
    """Test user registration with database persistence"""
    
    @pytest.mark.asyncio
    async def test_successful_registration(self, auth_service, mock_repository_factory):
        """Test successful user registration"""
        # Setup
        user_repo = await mock_repository_factory.get_user_repository()
        session = await mock_repository_factory.get_session()
        auth_service.db_session = session
        
        mock_user = MagicMock(spec=AuthUser)
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        mock_user.is_verified = False
        
        # Mock repository methods
        user_repo.get_by_email = AsyncMock(return_value=None)
        user_repo.create_local_user = AsyncMock(return_value=mock_user)
        
        with patch('auth_service.auth_core.services.auth_service.AuthUserRepository', return_value=user_repo):
            # Execute
            result = await auth_service.register_user(
                email="test@example.com",
                password="ValidPass123!",
                full_name="Test User"
            )
            
            # Verify
            assert result["user_id"] == "test-user-id"
            assert result["email"] == "test@example.com"
            assert result["message"] == "User registered successfully"
            assert result["requires_verification"] == True
            session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_duplicate_email_registration(self, auth_service, mock_repository_factory):
        """Test registration with existing email"""
        # Setup
        user_repo = await mock_repository_factory.get_user_repository()
        session = await mock_repository_factory.get_session()
        auth_service.db_session = session
        
        existing_user = MagicMock(spec=AuthUser)
        existing_user.email = "existing@example.com"
        
        # Mock repository methods
        user_repo.get_by_email = AsyncMock(return_value=existing_user)
        
        with patch('auth_service.auth_core.services.auth_service.AuthUserRepository', return_value=user_repo):
            # Execute and verify
            with pytest.raises(ValueError, match="User with this email already exists"):
                await auth_service.register_user(
                    email="existing@example.com",
                    password="ValidPass123!",
                    full_name="Test User"
                )
            
            session.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_invalid_email_registration(self, auth_service, mock_repository_factory):
        """Test registration with invalid email"""
        session = await mock_repository_factory.get_session()
        auth_service.db_session = session
        
        with pytest.raises(ValueError, match="Invalid email format"):
            await auth_service.register_user(
                email="invalid-email",
                password="ValidPass123!",
                full_name="Test User"
            )
    
    @pytest.mark.asyncio
    async def test_weak_password_registration(self, auth_service, mock_repository_factory):
        """Test registration with weak password"""
        session = await mock_repository_factory.get_session()
        auth_service.db_session = session
        
        with pytest.raises(ValueError, match="Password must"):
            await auth_service.register_user(
                email="test@example.com",
                password="weak",
                full_name="Test User"
            )
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, auth_service, mock_repository_factory):
        """Test handling of database errors during registration"""
        # Setup
        user_repo = await mock_repository_factory.get_user_repository()
        session = await mock_repository_factory.get_session()
        auth_service.db_session = session
        
        # Mock repository methods
        user_repo.get_by_email = AsyncMock(side_effect=Exception("Database error"))
        
        with patch('auth_service.auth_core.services.auth_service.AuthUserRepository', return_value=user_repo):
            with pytest.raises(RuntimeError, match="Registration failed"):
                await auth_service.register_user(
                    email="test@example.com",
                    password="ValidPass123!",
                    full_name="Test User"
                )
            
            session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fallback_to_test_registration(self, auth_service):
        """Test fallback to in-memory registration when no database"""
        # No database session
        auth_service.db_session = None
        
        result = await auth_service.register_user(
            email="test@example.com",
            password="ValidPass123!",
            full_name="Test User"
        )
        
        assert "user_id" in result
        assert result["email"] == "test@example.com"
        assert result["message"] == "User registered successfully"
        
        # Verify user is in test users store
        assert "test@example.com" in auth_service._test_users


class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_password_hashing(self, password_hasher):
        """Test that passwords are properly hashed"""
        password = "TestPassword123!"
        hashed = password_hasher.hash(password)
        
        # Verify hash is different from original
        assert hashed != password
        
        # Verify hash can be verified
        password_hasher.verify(hashed, password)
    
    def test_password_verification_mismatch(self, password_hasher):
        """Test that wrong passwords don't verify"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = password_hasher.hash(password)
        
        with pytest.raises(VerifyMismatchError):
            password_hasher.verify(hashed, wrong_password)
    
    def test_same_password_different_hashes(self, password_hasher):
        """Test that same password creates different hashes (salt)"""
        password = "TestPassword123!"
        hash1 = password_hasher.hash(password)
        hash2 = password_hasher.hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify
        password_hasher.verify(hash1, password)
        password_hasher.verify(hash2, password)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_empty_fields(self, auth_service, mock_repository_factory):
        """Test registration with empty fields"""
        session = await mock_repository_factory.get_session()
        auth_service.db_session = session
        
        # Empty email
        with pytest.raises(ValueError, match="Invalid email format"):
            await auth_service.register_user(
                email="",
                password="ValidPass123!",
                full_name="Test User"
            )
        
        # Empty password
        with pytest.raises(ValueError, match="Password must be at least"):
            await auth_service.register_user(
                email="test@example.com",
                password="",
                full_name="Test User"
            )
    
    @pytest.mark.asyncio
    async def test_sql_injection_attempts(self, auth_service, mock_repository_factory):
        """Test that SQL injection attempts are handled safely"""
        session = await mock_repository_factory.get_session()
        auth_service.db_session = session
        
        # SQL injection in email
        with pytest.raises(ValueError, match="Invalid email format"):
            await auth_service.register_user(
                email="test'; DROP TABLE users; --",
                password="ValidPass123!",
                full_name="Test User"
            )
    
    @pytest.mark.asyncio
    async def test_extremely_long_inputs(self, auth_service, mock_repository_factory):
        """Test handling of extremely long inputs"""
        session = await mock_repository_factory.get_session()
        auth_service.db_session = session
        
        # Very long email (should fail validation)
        long_email = "a" * 1000 + "@example.com"
        with pytest.raises(ValueError):
            await auth_service.register_user(
                email=long_email,
                password="ValidPass123!",
                full_name="Test User"
            )
    
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, auth_service, mock_repository_factory):
        """Test handling of unicode and special characters"""
        # Setup
        user_repo = await mock_repository_factory.get_user_repository()
        session = await mock_repository_factory.get_session()
        auth_service.db_session = session
        
        # Unicode in name is fine
        mock_user = MagicMock(spec=AuthUser)
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        mock_user.is_verified = False
        
        # Mock repository methods
        user_repo.get_by_email = AsyncMock(return_value=None)
        user_repo.create_local_user = AsyncMock(return_value=mock_user)
        
        with patch('auth_service.auth_core.services.auth_service.AuthUserRepository', return_value=user_repo):
            result = await auth_service.register_user(
                email="test@example.com",
                password="ValidPass123!",
                full_name="[U+7528][U+6237][U+540D] [U+1F680]"
            )
            
            assert result["user_id"] == "test-user-id"
    
    @pytest.mark.asyncio
    async def test_concurrent_registration_same_email(self, auth_service, mock_repository_factory):
        """Test race condition protection for concurrent registrations"""
        # Setup
        user_repo = await mock_repository_factory.get_user_repository()
        session = await mock_repository_factory.get_session()
        auth_service.db_session = session
        
        # Simulate race condition where user is created between check and create
        async def side_effect(email):
            # First call returns None (user doesn't exist)
            # Second call returns existing user (race condition)
            if not hasattr(side_effect, 'call_count'):
                side_effect.call_count = 0
            side_effect.call_count += 1
            
            if side_effect.call_count == 1:
                return None
            else:
                existing_user = MagicMock(spec=AuthUser)
                existing_user.email = email
                return existing_user
        
        # Mock repository methods
        user_repo.get_by_email = AsyncMock(side_effect=side_effect)
        user_repo.create_local_user = AsyncMock(
            side_effect=ValueError("User with email test@example.com already exists"))
        
        with patch('auth_service.auth_core.services.auth_service.AuthUserRepository', return_value=user_repo):
            with pytest.raises(RuntimeError, match="Registration failed"):
                await auth_service.register_user(
                    email="test@example.com",
                    password="ValidPass123!",
                    full_name="Test User"
                )