"""
Regression tests for user registration functionality
Ensures database persistence is working correctly and not using test/in-memory stores
"""
import pytest
from datetime import datetime, UTC
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from test_framework.database.test_database_manager import DatabaseTestManager as DatabaseManager
from shared.isolated_environment import IsolatedEnvironment

from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.database.models import AuthUser


@pytest.mark.asyncio
class TestRegistrationRegression:
    """Regression tests to prevent auth service from reverting to in-memory storage"""
    
    async def test_create_user_uses_database_not_memory(self):
        """Ensure create_user uses database when available, not in-memory storage"""
        # Create service instance
        service = AuthService()
        
        # Mock database connection
        mock_db_connection = DatabaseManager().get_session()
        mock_session = AsyncNone  # TODO: Use real service instance
        mock_repo = AsyncNone  # TODO: Use real service instance
        
        # Configure mocks
        mock_db_connection.get_session = AsyncNone  # TODO: Use real service instance
        mock_db_connection.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_connection.get_session.return_value.__aexit__ = AsyncNone  # TODO: Use real service instance
        
        # Mock repository methods
        mock_repo.get_by_email = AsyncMock(return_value=None)  # User doesn't exist
        
        # Set up the service with mocked database
        service._db_connection = mock_db_connection
        
        with patch('auth_service.auth_core.services.auth_service.AuthUserRepository', return_value=mock_repo):
            # Create a user
            user_id = await service.create_user(
                email="test@example.com",
                password="SecurePass123!",
                name="Test User"
            )
            
            # Verify database was used
            mock_repo.get_by_email.assert_called_once_with("test@example.com")
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            
            # Ensure in-memory store was NOT used
            assert "test@example.com" not in service._test_users
    
    async def test_authenticate_user_uses_database_not_memory(self):
        """Ensure authenticate_user uses database when available"""
        # Create service instance
        service = AuthService()
        
        # Mock database connection
        mock_db_connection = DatabaseManager().get_session()
        mock_session = AsyncNone  # TODO: Use real service instance
        mock_repo = AsyncNone  # TODO: Use real service instance
        
        # Create mock user
        mock_user = Mock(spec=AuthUser)
        mock_user.id = "user-123"
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"
        mock_user.hashed_password = PasswordHasher().hash("SecurePass123!")
        mock_user.is_verified = True
        mock_user.is_active = True
        mock_user.last_login_at = None
        
        # Configure mocks
        mock_db_connection.get_session = AsyncNone  # TODO: Use real service instance
        mock_db_connection.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_connection.get_session.return_value.__aexit__ = AsyncNone  # TODO: Use real service instance
        
        # Mock repository methods
        mock_repo.get_by_email = AsyncMock(return_value=mock_user)
        
        # Set up the service
        service._db_connection = mock_db_connection
        
        with patch('auth_service.auth_core.services.auth_service.AuthUserRepository', return_value=mock_repo):
            # Authenticate user
            result = await service.authenticate_user(
                email="test@example.com",
                password="SecurePass123!"
            )
            
            # Verify authentication succeeded
            assert result is not None
            user_id, user_data = result
            assert user_id == "user-123"
            assert user_data["email"] == "test@example.com"
            
            # Verify database was used
            mock_repo.get_by_email.assert_called_once_with("test@example.com")
            mock_session.commit.assert_called_once()  # For last_login_at update
    
    async def test_registration_with_real_database(self, auth_db_session):
        """Test registration flow with actual database connection"""
        # Create service with real database
        service = AuthService()
        
        # Ensure service has database connection
        assert service._db_connection is not None
        
        # Create a new user
        user_id = await service.create_user(
            email="realtest@example.com",
            password="RealSecurePass123!",
            name="Real Test User"
        )
        
        # Verify user was created
        assert user_id is not None
        
        # Try to authenticate the user
        result = await service.authenticate_user(
            email="realtest@example.com",
            password="RealSecurePass123!"
        )
        
        assert result is not None
        auth_user_id, user_data = result
        assert auth_user_id == user_id
        assert user_data["email"] == "realtest@example.com"
        assert user_data["name"] == "Real Test User"
        
        # Verify duplicate registration fails
        duplicate_id = await service.create_user(
            email="realtest@example.com",
            password="AnotherPass123!",
            name="Duplicate User"
        )
        assert duplicate_id is None
    
    async def test_invalid_email_format_rejected(self):
        """Test that invalid email formats are rejected"""
        service = AuthService()
        
        # Test various invalid email formats
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
            "user@domain",
            "user name@example.com",
            "",
            None
        ]
        
        for email in invalid_emails:
            if email is not None:
                user_id = await service.create_user(
                    email=email,
                    password="ValidPass123!",
                    name="Test User"
                )
                assert user_id is None, f"Invalid email '{email}' should have been rejected"
    
    async def test_password_hashing_security(self):
        """Ensure passwords are properly hashed and never stored in plaintext"""
        service = AuthService()
        
        # Mock database to inspect what gets stored
        mock_db_connection = DatabaseManager().get_session()
        mock_session = AsyncNone  # TODO: Use real service instance
        stored_user = None
        
        def capture_user(user):
            nonlocal stored_user
            stored_user = user
        
        mock_session.add.side_effect = capture_user
        
        mock_db_connection.get_session = AsyncNone  # TODO: Use real service instance
        mock_db_connection.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_connection.get_session.return_value.__aexit__ = AsyncNone  # TODO: Use real service instance
        
        service._db_connection = mock_db_connection
        
        with patch('auth_service.auth_core.services.auth_service.AuthUserRepository') as mock_repo_class:
            mock_repo = AsyncNone  # TODO: Use real service instance
            mock_repo.get_by_email = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo
            
            # Create user
            password = "MySecretPassword123!"
            await service.create_user(
                email="hashtest@example.com",
                password=password,
                name="Hash Test"
            )
            
            # Verify password was hashed
            assert stored_user is not None
            assert stored_user.hashed_password is not None
            assert stored_user.hashed_password != password
            assert password not in stored_user.hashed_password
            
            # Verify the hash is valid Argon2 format
            assert stored_user.hashed_password.startswith("$argon2")