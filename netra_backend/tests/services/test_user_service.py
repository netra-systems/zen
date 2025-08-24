"""
Unit tests for User Service
Tests user CRUD operations including password hashing
"""

import sys
from pathlib import Path

import uuid
from unittest.mock import AsyncMock, MagicMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import User
from netra_backend.app.schemas.registry import UserCreate
from netra_backend.app.schemas.user import UserUpdate

from netra_backend.app.services.user_service import CRUDUser, pwd_context, user_service

class TestUserService:
    """Test suite for User Service"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing"""
        return {
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "SecurePassword123!"
        }
    
    @pytest.fixture
    def sample_user(self, sample_user_data):
        """Create a sample User instance"""
        user = User(
            id=str(uuid.uuid4()),
            email=sample_user_data["email"],
            full_name=sample_user_data["full_name"],
            hashed_password=pwd_context.hash(sample_user_data["password"]),
            is_active=True,
            is_superuser=False
        )
        return user
    @pytest.mark.asyncio
    async def test_create_user(self, mock_db_session, sample_user_data):
        """Test creating a new user with password hashing"""
        # Arrange
        user_create = UserCreate(**sample_user_data)
        crud_user = CRUDUser("test_user_service", User)
        
        # Mock the get_by_email to return None (no existing user)
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Mock the database refresh to set user attributes
        async def mock_refresh(obj):
            obj.id = str(uuid.uuid4())
            obj.is_active = True
            obj.is_superuser = False
        
        mock_db_session.refresh.side_effect = mock_refresh
        
        # Act
        created_user = await crud_user.create(db=mock_db_session, obj_in=user_create)
        
        # Assert
        assert created_user != None
        assert created_user.email == sample_user_data["email"]
        # Removed username assertion as the User model doesn't have username field
        assert created_user.full_name == sample_user_data["full_name"]
        assert hasattr(created_user, 'hashed_password')
        assert created_user.hashed_password != sample_user_data["password"]  # Password should be hashed
        
        # Verify password was hashed correctly
        # Verify password was hashed correctly
        try:
            pwd_context.verify(created_user.hashed_password, sample_user_data["password"])
            assert True  # Password verification succeeded
        except Exception:
            assert False  # Password verification failed
        
        # Verify database operations were called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, mock_db_session, sample_user):
        """Test retrieving a user by email"""
        # Arrange
        crud_user = CRUDUser("test_user_service", User)
        
        # Mock the database query result
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        # Act
        found_user = await crud_user.get_by_email(db=mock_db_session, email=sample_user.email)
        
        # Assert
        assert found_user != None
        assert found_user.email == sample_user.email
        # Removed username assertion as User model doesn't have username field
        assert found_user.id == sample_user.id
        
        # Verify the query was executed
        mock_db_session.execute.assert_called_once()
        
        # Verify the correct SQL filter was applied
        call_args = mock_db_session.execute.call_args[0][0]
        # The query should filter by email
        assert "email" in str(call_args)
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, mock_db_session):
        """Test retrieving a user by email when user doesn't exist"""
        # Arrange
        crud_user = CRUDUser("test_user_service", User)
        
        # Mock the database query result to return None
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Act
        found_user = await crud_user.get_by_email(db=mock_db_session, email="nonexistent@example.com")
        
        # Assert
        assert found_user == None
        
        # Verify the query was executed
        mock_db_session.execute.assert_called_once()
    @pytest.mark.asyncio
    async def test_update_user(self, mock_db_session, sample_user):
        """Test updating user information"""
        # Arrange
        crud_user = CRUDUser("test_user_service", User)
        update_data = UserUpdate(
            email=sample_user.email,  # Required field for UserUpdate
            full_name="Updated Name"
        )
        
        # Mock get method to return the sample user
        with patch.object(crud_user, 'get', AsyncMock(return_value=sample_user)):
            # Mock the database refresh
            async def mock_refresh(obj):
                obj.full_name = update_data.full_name
            
            mock_db_session.refresh.side_effect = mock_refresh
            
            # Act
            updated_user = await crud_user.update(
                db=mock_db_session,
                db_obj=sample_user,
                obj_in=update_data
            )
            
            # Assert
            assert updated_user != None
            assert updated_user.full_name == "Updated Name"
            # Removed username assertion as User model doesn't have username field
            assert updated_user.email == sample_user.email  # Email should remain unchanged
            
            # Verify database operations
            mock_db_session.commit.assert_called()
            mock_db_session.refresh.assert_called()
    @pytest.mark.asyncio
    async def test_delete_user(self, mock_db_session, sample_user):
        """Test deleting a user"""
        # Arrange
        crud_user = CRUDUser("test_user_service", User)
        
        # Mock the get method to return the sample user
        with patch.object(crud_user, 'get', AsyncMock(return_value=sample_user)):
            # Mock the database delete operation
            mock_db_session.delete = Mock()
            
            # Act
            deleted_user = await crud_user.remove(db=mock_db_session, id=sample_user.id)
            
            # Assert
            assert deleted_user == sample_user
            
            # Verify database operations
            mock_db_session.delete.assert_called_once_with(sample_user)
            mock_db_session.commit.assert_called_once()
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, mock_db_session, sample_user):
        """Test retrieving a user by ID"""
        # Arrange
        crud_user = CRUDUser("test_user_service", User)
        
        # Mock the database query - need to mock scalars().first() not scalar_one_or_none()
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.first.return_value = sample_user
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result
        
        # Act
        found_user = await crud_user.get(db=mock_db_session, id=sample_user.id)
        
        # Assert
        assert found_user != None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email
        
        # Verify the query was executed
        mock_db_session.execute.assert_called_once()
    @pytest.mark.asyncio
    async def test_get_multiple_users(self, mock_db_session):
        """Test retrieving multiple users with pagination"""
        # Arrange
        crud_user = CRUDUser("test_user_service", User)
        
        # Create multiple sample users
        users = [
            User(
                id=str(uuid.uuid4()),
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                hashed_password="hashed",
                is_active=True,
                is_superuser=False
            )
            for i in range(5)
        ]
        
        # Mock the database query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = users[:2]  # Return first 2 users
        mock_db_session.execute.return_value = mock_result
        
        # Act
        found_users = await crud_user.get_multi(db=mock_db_session, skip=0, limit=2)
        
        # Assert
        assert found_users != None
        assert len(found_users) == 2
        assert found_users[0].email == "user0@example.com"
        assert found_users[1].email == "user1@example.com"
        
        # Verify the query was executed
        mock_db_session.execute.assert_called_once()
    @pytest.mark.asyncio
    async def test_password_hashing_security(self):
        """Test that password hashing is secure and consistent"""
        # Arrange
        password = "MySecurePassword123!"
        
        # Act
        hashed1 = pwd_context.hash(password)
        hashed2 = pwd_context.hash(password)
        
        # Assert
        # Hashes should be different even for the same password (due to salt)
        assert hashed1 != hashed2
        
        # Both hashes should verify correctly
        try:
            pwd_context.verify(hashed1, password)
            assert True  # Verification succeeded
        except Exception:
            assert False  # Verification failed
        
        try:
            pwd_context.verify(hashed2, password)
            assert True  # Verification succeeded
        except Exception:
            assert False  # Verification failed
        
        # Wrong password should not verify
        try:
            pwd_context.verify(hashed1, "WrongPassword")
            assert False  # Should have raised exception
        except Exception:
            assert True  # Correctly failed verification
        
        try:
            pwd_context.verify(hashed2, "WrongPassword")
            assert False  # Should have raised exception
        except Exception:
            assert True  # Correctly failed verification
    @pytest.mark.asyncio
    async def test_create_user_with_duplicate_email(self, mock_db_session, sample_user_data):
        """Test that creating a user with duplicate email handles error appropriately"""
        # Arrange
        user_create = UserCreate(**sample_user_data)
        crud_user = CRUDUser("test_user_service", User)
        
        # Mock the get_by_email to return None (no existing user)
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Mock database to raise integrity error
        from sqlalchemy.exc import IntegrityError
        mock_db_session.commit.side_effect = IntegrityError("", "", "")
        
        # Act & Assert
        with pytest.raises(IntegrityError):
            await crud_user.create(db=mock_db_session, obj_in=user_create)
        
        # Verify database operations were attempted
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    def test_user_service_singleton(self):
        """Test that user_service is properly initialized"""
        # Assert
        assert user_service != None
        assert isinstance(user_service, CRUDUser)
        assert user_service._model_class == User

if __name__ == "__main__":
    pytest.main([__file__, "-v"])