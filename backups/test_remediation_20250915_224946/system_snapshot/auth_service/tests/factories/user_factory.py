"""
User Test Data Factory
Creates test users with consistent data patterns for auth service testing.
Supports both local and OAuth users with proper password handling.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from auth_service.auth_core.database.models import AuthUser
from auth_service.auth_core.models.auth_models import AuthProvider

# Password hasher instance
ph = PasswordHasher()


class UserFactory:
    """Factory for creating test user data structures"""
    
    @staticmethod
    def create_user_data(
        email: str = None,
        full_name: str = None,
        auth_provider: str = AuthProvider.LOCAL,
        is_active: bool = True,
        is_verified: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Create user data dictionary"""
        user_id = str(uuid.uuid4())
        
        return {
            "id": user_id,
            "email": email or f"user{user_id[:8]}@example.com",
            "full_name": full_name or f"Test User {user_id[:8]}",
            "auth_provider": auth_provider,
            "is_active": is_active,
            "is_verified": is_verified,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            **kwargs
        }
    
    @staticmethod
    def create_local_user_data(
        email: str = None,
        password: str = "TestPassword123!",
        **kwargs
    ) -> Dict[str, Any]:
        """Create local user with hashed password"""
        user_data = UserFactory.create_user_data(
            email=email,
            auth_provider=AuthProvider.LOCAL,
            **kwargs
        )
        
        # Add hashed password for local users
        user_data["hashed_password"] = ph.hash(password)
        
        return user_data
    
    @staticmethod
    def create_oauth_user_data(
        provider: str = AuthProvider.GOOGLE,
        provider_user_id: str = None,
        email: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create OAuth user data"""
        user_data = UserFactory.create_user_data(
            email=email,
            auth_provider=provider,
            **kwargs
        )
        
        # Add OAuth-specific fields
        user_data.update({
            "provider_user_id": provider_user_id or f"{provider}_user_{uuid.uuid4().hex[:10]}",
            "hashed_password": None,  # OAuth users don't have local passwords
            "provider_data": {
                "provider": provider,
                "verified_email": True,
                "picture": f"https://example.com/avatar/{user_data['id']}.jpg"
            }
        })
        
        return user_data
    
    @staticmethod
    def create_google_user_data(email: str = None, **kwargs) -> Dict[str, Any]:
        """Create Google OAuth user data"""
        return UserFactory.create_oauth_user_data(
            provider=AuthProvider.GOOGLE,
            email=email,
            **kwargs
        )
    
    @staticmethod
    def create_github_user_data(email: str = None, **kwargs) -> Dict[str, Any]:
        """Create GitHub OAuth user data"""
        return UserFactory.create_oauth_user_data(
            provider=AuthProvider.GITHUB,
            email=email,
            **kwargs
        )
    
    @staticmethod
    def create_inactive_user_data(**kwargs) -> Dict[str, Any]:
        """Create inactive user data"""
        return UserFactory.create_user_data(
            is_active=False,
            **kwargs
        )
    
    @staticmethod
    def create_unverified_user_data(**kwargs) -> Dict[str, Any]:
        """Create unverified user data"""
        return UserFactory.create_user_data(
            is_verified=False,
            **kwargs
        )


class AuthUserFactory:
    """Factory for creating AuthUser database model instances"""
    
    @staticmethod
    def create_user(session, **kwargs) -> AuthUser:
        """Create and save AuthUser to database"""
        user_data = UserFactory.create_user_data(**kwargs)
        
        user = AuthUser(**user_data)
        session.add(user)
        return user
    
    @staticmethod
    def create_local_user(session, password: str = "TestPassword123!", **kwargs) -> AuthUser:
        """Create local user with password"""
        user_data = UserFactory.create_local_user_data(password=password, **kwargs)
        
        user = AuthUser(**user_data)
        session.add(user)
        return user
    
    @staticmethod
    def create_oauth_user(session, provider: str = AuthProvider.GOOGLE, **kwargs) -> AuthUser:
        """Create OAuth user"""
        user_data = UserFactory.create_oauth_user_data(provider=provider, **kwargs)
        
        user = AuthUser(**user_data)
        session.add(user)
        return user
    
    @staticmethod
    def create_google_user(session, **kwargs) -> AuthUser:
        """Create Google OAuth user"""
        return AuthUserFactory.create_oauth_user(
            session,
            provider=AuthProvider.GOOGLE,
            **kwargs
        )
    
    @staticmethod
    def create_github_user(session, **kwargs) -> AuthUser:
        """Create GitHub OAuth user"""
        return AuthUserFactory.create_oauth_user(
            session,
            provider=AuthProvider.GITHUB,
            **kwargs
        )
    
    @staticmethod
    def verify_password(hashed_password: str, plain_password: str) -> bool:
        """Verify password against hash"""
        try:
            ph.verify(hashed_password, plain_password)
            return True
        except VerifyMismatchError:
            return False