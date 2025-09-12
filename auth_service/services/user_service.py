"""
User Service - Single Source of Truth for User Management

This service provides a unified interface for user management operations,
following SSOT principles and maintaining service independence.

Business Value: Provides consistent user management across the auth service,
enabling reliable user registration, authentication, and profile management.
"""

import bcrypt
import logging
import uuid
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List

from auth_service.auth_core.models.auth_models import User
from auth_service.auth_core.database import AuthUserRepository
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.connection import auth_db
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

logger = logging.getLogger(__name__)


class UserService:
    """
    Single Source of Truth for user management operations.
    
    This service provides a unified interface for all user-related operations
    including registration, authentication, profile management, and deletion.
    """
    
    def __init__(self, auth_config: AuthConfig, database=None):
        """
        Initialize UserService with configuration and database.
        
        Args:
            auth_config: Authentication configuration
            database: Database interface (optional, uses default if not provided)
        """
        self.auth_config = auth_config
        self.database = database
        self._user_repository = None
        
    async def _get_repository_session(self):
        """Get a database session for repository operations."""
        if self.database:
            return self.database.get_session()
        else:
            return auth_db.get_session()
    
    async def create_user(self, email: str, password: str, name: str = None, **kwargs) -> User:
        """
        Create a new user.
        
        Args:
            email: User email
            password: User password (will be hashed)
            name: User name
            **kwargs: Additional user data
            
        Returns:
            Created User instance
            
        Raises:
            ValueError: If user already exists or validation fails
        """
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_email(email)
            if existing_user:
                raise ValueError(f"User with email {email} already exists")
                
            # Hash password
            password_hash = bcrypt.hashpw(
                password.encode('utf-8'), 
                bcrypt.gensalt(rounds=self.auth_config.get_bcrypt_rounds())
            ).decode('utf-8')
            
            # Create user in database using session context
            async with await self._get_repository_session() as session:
                repository = AuthUserRepository(session)
                
                # Create user data
                from auth_service.auth_core.database.models import AuthUser
                
                # Generate secure unique user ID using UnifiedIDManager
                id_manager = UnifiedIDManager()
                user_id = id_manager.generate_id(IDType.USER)
                
                user_data = AuthUser(
                    id=user_id,
                    email=email,
                    full_name=name or email.split('@')[0],
                    hashed_password=password_hash,
                    is_active=True,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                session.add(user_data)
                await session.commit()
                await session.refresh(user_data)
                
                # Convert to User model
                return User(
                    id=user_data.id,
                    email=user_data.email,
                    name=user_data.full_name,
                    is_active=user_data.is_active,
                    created_at=user_data.created_at,
                    updated_at=user_data.updated_at
                )
            
        except Exception as e:
            logger.error(f"Failed to create user {email}: {e}")
            raise
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email
            
        Returns:
            User instance or None if not found
        """
        try:
            async with await self._get_repository_session() as session:
                repository = AuthUserRepository(session)
                db_user = await repository.get_by_email(email)
                
                if not db_user:
                    return None
                    
                return User(
                    id=db_user.id,
                    email=db_user.email,
                    name=db_user.full_name,
                    is_active=db_user.is_active,
                    created_at=db_user.created_at,
                    updated_at=db_user.updated_at
                )
            
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User instance or None if not found
        """
        try:
            db_user = await self.user_repository.get_by_id(user_id)
            if not db_user:
                return None
                
            return User(
                id=db_user.id,
                email=db_user.email,
                name=db_user.name,
                is_active=db_user.is_active,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to get user by id {user_id}: {e}")
            raise
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Authentication result with user data or None if failed
        """
        try:
            async with await self._get_repository_session() as session:
                repository = AuthUserRepository(session)
                db_user = await repository.get_by_email(email)
                
                if not db_user or not db_user.is_active:
                    raise Exception("User not found")
                    
                if not db_user.hashed_password:
                    raise Exception("Invalid credentials")
                
                # Verify password
                if not bcrypt.checkpw(password.encode('utf-8'), db_user.hashed_password.encode('utf-8')):
                    raise Exception("Invalid credentials")
                
                # Create JWT token (simplified for now)
                from auth_service.services.jwt_service import JWTService
                jwt_service = JWTService(self.auth_config)
                access_token = await jwt_service.create_access_token(
                    user_id=str(db_user.id),
                    email=db_user.email,
                    permissions=["read", "write"]
                )
                
                return {
                    "user": User(
                        id=db_user.id,
                        email=db_user.email,
                        name=db_user.full_name,
                        is_active=db_user.is_active,
                        created_at=db_user.created_at,
                        updated_at=db_user.updated_at
                    ),
                    "access_token": access_token
                }
            
        except Exception as e:
            logger.error(f"Failed to authenticate user {email}: {e}")
            raise
    
    async def verify_password(self, user_id: str, password: str) -> bool:
        """
        Verify password for a user.
        
        Args:
            user_id: User ID
            password: Password to verify
            
        Returns:
            True if password is correct, False otherwise
        """
        try:
            async with await self._get_repository_session() as session:
                repository = AuthUserRepository(session)
                db_user = await repository.get_by_id(user_id)
                
                if not db_user:
                    return False
                
                if not db_user.hashed_password:
                    return False
                    
                return bcrypt.checkpw(password.encode('utf-8'), db_user.hashed_password.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Failed to verify password for user {user_id}: {e}")
            return False
    
    async def update_user_profile(self, user_id: str, **update_data) -> Optional[User]:
        """
        Update user profile.
        
        Args:
            user_id: User ID
            **update_data: Data to update
            
        Returns:
            Updated User instance or None if not found
        """
        try:
            update_data['updated_at'] = datetime.now(UTC)
            updated_user = await self.user_repository.update(user_id, update_data)
            
            if not updated_user:
                return None
                
            return User(
                id=updated_user.id,
                email=updated_user.email,
                name=updated_user.name,
                is_active=updated_user.is_active,
                created_at=updated_user.created_at,
                updated_at=updated_user.updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to update user profile {user_id}: {e}")
            raise
    
    async def update_password(self, user_id: str, new_password: str) -> bool:
        """
        Update user password.
        
        Args:
            user_id: User ID
            new_password: New password
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Hash new password
            password_hash = bcrypt.hashpw(
                new_password.encode('utf-8'), 
                bcrypt.gensalt(rounds=self.auth_config.get_bcrypt_rounds())
            ).decode('utf-8')
            
            update_data = {
                'password_hash': password_hash,
                'updated_at': datetime.now(UTC)
            }
            
            updated_user = await self.user_repository.update(user_id, update_data)
            return updated_user is not None
            
        except Exception as e:
            logger.error(f"Failed to update password for user {user_id}: {e}")
            return False
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with await self._get_repository_session() as session:
                repository = AuthUserRepository(session)
                db_user = await repository.get_by_id(user_id)
                
                if not db_user:
                    return False
                
                await session.delete(db_user)
                await session.commit()
                return True
            
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False
    
    async def logout_user(self, user_id: str) -> bool:
        """
        Logout user (placeholder for session management).
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        try:
            # This is a placeholder - in a full implementation, this would
            # invalidate user sessions, clear tokens, etc.
            logger.info(f"User {user_id} logged out")
            return True
            
        except Exception as e:
            logger.error(f"Failed to logout user {user_id}: {e}")
            return False


__all__ = ["UserService"]