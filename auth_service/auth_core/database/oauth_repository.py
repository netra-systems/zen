"""OAuth Repository - Database operations for OAuth users and tokens

**CRITICAL**: Enterprise-Grade OAuth Database Operations
Provides secure database operations for OAuth users and tokens with
comprehensive validation, error handling, and transaction management.

Business Value: Enables reliable OAuth data persistence and retrieval
Critical for OAuth authentication flows and user management operations.

This repository handles all database operations for OAuth entities with
proper error handling, validation, and security measures.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_, or_, desc

from auth_service.auth_core.models.oauth_user import OAuthUser
from auth_service.auth_core.models.oauth_token import OAuthToken

logger = logging.getLogger(__name__)


class OAuthRepositoryError(Exception):
    """Raised when OAuth repository operations fail."""
    pass


class OAuthRepository:
    """
    Single Source of Truth for OAuth database operations.
    
    **CRITICAL**: All OAuth database access MUST use this repository.
    Provides comprehensive CRUD operations for OAuth users and tokens
    with proper error handling, validation, and transaction management.
    """
    
    def __init__(self, session: Session):
        """
        Initialize OAuth repository with database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    # OAuth User Operations
    
    async def create_oauth_user(self, provider: str, provider_user_id: str, 
                               email: str, name: Optional[str] = None,
                               email_verified: bool = False,
                               profile_data: Optional[Dict[str, Any]] = None) -> OAuthUser:
        """
        Create new OAuth user.
        
        Args:
            provider: OAuth provider name
            provider_user_id: Provider's user ID
            email: User email address
            name: User display name
            email_verified: Whether email is verified by provider
            profile_data: Additional profile data from provider
            
        Returns:
            Created OAuthUser instance
            
        Raises:
            OAuthRepositoryError: If user creation fails
        """
        try:
            # Check if user already exists
            existing_user = await self.get_oauth_user_by_provider_id(provider, provider_user_id)
            if existing_user:
                raise OAuthRepositoryError(f"OAuth user already exists for {provider}:{provider_user_id}")
            
            # Create new OAuth user
            oauth_user = OAuthUser(
                provider=provider,
                provider_user_id=provider_user_id,
                email=email,
                name=name,
                email_verified=email_verified,
                profile_data=profile_data or {}
            )
            
            # Parse profile data for additional fields
            if profile_data:
                if "given_name" in profile_data:
                    oauth_user.first_name = profile_data["given_name"]
                if "family_name" in profile_data:
                    oauth_user.last_name = profile_data["family_name"]
                if "picture" in profile_data:
                    oauth_user.picture_url = profile_data["picture"]
                if "locale" in profile_data:
                    oauth_user.locale = profile_data["locale"]
            
            self.session.add(oauth_user)
            self.session.commit()
            
            logger.info(f"Created OAuth user for {provider}:{email}")
            return oauth_user
            
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Integrity error creating OAuth user: {e}")
            raise OAuthRepositoryError(f"Database constraint violation: {str(e)}")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create OAuth user: {e}")
            raise OAuthRepositoryError(f"User creation failed: {str(e)}")
    
    async def get_oauth_user_by_id(self, user_id: int) -> Optional[OAuthUser]:
        """
        Get OAuth user by ID.
        
        Args:
            user_id: OAuth user ID
            
        Returns:
            OAuthUser if found, None otherwise
        """
        try:
            return self.session.query(OAuthUser).filter(OAuthUser.id == user_id).first()
        except Exception as e:
            logger.error(f"Failed to get OAuth user by ID {user_id}: {e}")
            return None
    
    async def get_oauth_user_by_provider_id(self, provider: str, provider_user_id: str) -> Optional[OAuthUser]:
        """
        Get OAuth user by provider and provider user ID.
        
        Args:
            provider: OAuth provider name
            provider_user_id: Provider's user ID
            
        Returns:
            OAuthUser if found, None otherwise
        """
        try:
            return self.session.query(OAuthUser).filter(
                and_(
                    OAuthUser.provider == provider,
                    OAuthUser.provider_user_id == provider_user_id
                )
            ).first()
        except Exception as e:
            logger.error(f"Failed to get OAuth user by provider ID {provider}:{provider_user_id}: {e}")
            return None
    
    async def get_oauth_user_by_email(self, email: str, provider: Optional[str] = None) -> Optional[OAuthUser]:
        """
        Get OAuth user by email address.
        
        Args:
            email: User email address
            provider: Optional provider filter
            
        Returns:
            OAuthUser if found, None otherwise
        """
        try:
            query = self.session.query(OAuthUser).filter(OAuthUser.email == email)
            
            if provider:
                query = query.filter(OAuthUser.provider == provider)
            
            return query.first()
        except Exception as e:
            logger.error(f"Failed to get OAuth user by email {email}: {e}")
            return None
    
    async def update_oauth_user(self, user_id: int, **kwargs) -> Optional[OAuthUser]:
        """
        Update OAuth user.
        
        Args:
            user_id: OAuth user ID
            **kwargs: Fields to update
            
        Returns:
            Updated OAuthUser if found, None otherwise
        """
        try:
            oauth_user = await self.get_oauth_user_by_id(user_id)
            if not oauth_user:
                return None
            
            # Update provided fields
            for field, value in kwargs.items():
                if hasattr(oauth_user, field):
                    setattr(oauth_user, field, value)
            
            oauth_user.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            
            logger.info(f"Updated OAuth user {user_id}")
            return oauth_user
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update OAuth user {user_id}: {e}")
            raise OAuthRepositoryError(f"User update failed: {str(e)}")
    
    # OAuth Token Operations
    
    async def create_oauth_token(self, oauth_user_id: int, access_token: str,
                                refresh_token: Optional[str] = None,
                                token_type: str = "Bearer",
                                expires_at: Optional[datetime] = None,
                                expires_in: Optional[int] = None,
                                scope: Optional[str] = None,
                                id_token: Optional[str] = None) -> OAuthToken:
        """
        Create new OAuth token.
        
        Args:
            oauth_user_id: OAuth user ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            token_type: Token type (usually "Bearer")
            expires_at: Token expiration datetime
            expires_in: Token lifetime in seconds
            scope: OAuth scopes
            id_token: OpenID Connect ID token
            
        Returns:
            Created OAuthToken instance
            
        Raises:
            OAuthRepositoryError: If token creation fails
        """
        try:
            # Get OAuth user to validate and get provider
            oauth_user = await self.get_oauth_user_by_id(oauth_user_id)
            if not oauth_user:
                raise OAuthRepositoryError(f"OAuth user {oauth_user_id} not found")
            
            # Calculate expiration if not provided
            if not expires_at and expires_in:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            elif not expires_at:
                # Default to 1 hour if no expiration provided
                expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
                expires_in = 3600
            
            # Deactivate existing tokens for this user/provider
            await self._deactivate_user_tokens(oauth_user_id, oauth_user.provider)
            
            # Create new token
            oauth_token = OAuthToken(
                oauth_user_id=oauth_user_id,
                provider=oauth_user.provider,
                access_token=access_token,
                refresh_token=refresh_token,
                id_token=id_token,
                token_type=token_type,
                expires_at=expires_at,
                expires_in=expires_in,
                scope=scope
            )
            
            self.session.add(oauth_token)
            self.session.commit()
            
            logger.info(f"Created OAuth token for user {oauth_user_id}")
            return oauth_token
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create OAuth token: {e}")
            raise OAuthRepositoryError(f"Token creation failed: {str(e)}")
    
    async def get_active_oauth_token(self, oauth_user_id: int) -> Optional[OAuthToken]:
        """
        Get active OAuth token for user.
        
        Args:
            oauth_user_id: OAuth user ID
            
        Returns:
            Active OAuthToken if found, None otherwise
        """
        try:
            return self.session.query(OAuthToken).filter(
                and_(
                    OAuthToken.oauth_user_id == oauth_user_id,
                    OAuthToken.is_active == True,
                    OAuthToken.is_revoked == False,
                    OAuthToken.expires_at > datetime.now(timezone.utc)
                )
            ).order_by(desc(OAuthToken.created_at)).first()
        except Exception as e:
            logger.error(f"Failed to get active OAuth token for user {oauth_user_id}: {e}")
            return None
    
    async def get_oauth_token_by_id(self, token_id: int) -> Optional[OAuthToken]:
        """
        Get OAuth token by ID.
        
        Args:
            token_id: OAuth token ID
            
        Returns:
            OAuthToken if found, None otherwise
        """
        try:
            return self.session.query(OAuthToken).filter(OAuthToken.id == token_id).first()
        except Exception as e:
            logger.error(f"Failed to get OAuth token by ID {token_id}: {e}")
            return None
    
    async def update_oauth_token(self, token_id: int, **kwargs) -> Optional[OAuthToken]:
        """
        Update OAuth token.
        
        Args:
            token_id: OAuth token ID
            **kwargs: Fields to update
            
        Returns:
            Updated OAuthToken if found, None otherwise
        """
        try:
            oauth_token = await self.get_oauth_token_by_id(token_id)
            if not oauth_token:
                return None
            
            # Update provided fields
            for field, value in kwargs.items():
                if hasattr(oauth_token, field):
                    setattr(oauth_token, field, value)
            
            oauth_token.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            
            logger.info(f"Updated OAuth token {token_id}")
            return oauth_token
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update OAuth token {token_id}: {e}")
            raise OAuthRepositoryError(f"Token update failed: {str(e)}")
    
    async def refresh_oauth_token(self, token_id: int, new_access_token: str,
                                 new_refresh_token: Optional[str] = None,
                                 expires_in: Optional[int] = None) -> Optional[OAuthToken]:
        """
        Refresh OAuth token with new values.
        
        Args:
            token_id: OAuth token ID
            new_access_token: New access token
            new_refresh_token: New refresh token (optional)
            expires_in: New token lifetime in seconds
            
        Returns:
            Refreshed OAuthToken if successful, None otherwise
        """
        try:
            oauth_token = await self.get_oauth_token_by_id(token_id)
            if not oauth_token:
                return None
            
            # Update token values
            oauth_token.update_tokens(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_in=expires_in
            )
            
            self.session.commit()
            
            logger.info(f"Refreshed OAuth token {token_id}")
            return oauth_token
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to refresh OAuth token {token_id}: {e}")
            raise OAuthRepositoryError(f"Token refresh failed: {str(e)}")
    
    async def revoke_oauth_token(self, token_id: int) -> bool:
        """
        Revoke OAuth token.
        
        Args:
            token_id: OAuth token ID
            
        Returns:
            True if token was revoked, False if not found
        """
        try:
            oauth_token = await self.get_oauth_token_by_id(token_id)
            if not oauth_token:
                return False
            
            oauth_token.revoke()
            self.session.commit()
            
            logger.info(f"Revoked OAuth token {token_id}")
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to revoke OAuth token {token_id}: {e}")
            return False
    
    async def _deactivate_user_tokens(self, oauth_user_id: int, provider: str) -> int:
        """
        Deactivate all existing tokens for a user/provider.
        
        Args:
            oauth_user_id: OAuth user ID
            provider: OAuth provider
            
        Returns:
            Number of tokens deactivated
        """
        try:
            tokens = self.session.query(OAuthToken).filter(
                and_(
                    OAuthToken.oauth_user_id == oauth_user_id,
                    OAuthToken.provider == provider,
                    OAuthToken.is_active == True
                )
            ).all()
            
            for token in tokens:
                token.deactivate()
            
            self.session.commit()
            
            logger.info(f"Deactivated {len(tokens)} tokens for user {oauth_user_id}")
            return len(tokens)
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to deactivate user tokens: {e}")
            return 0
    
    # Cleanup Operations
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired OAuth tokens.
        
        Returns:
            Number of tokens cleaned up
        """
        try:
            expired_tokens = self.session.query(OAuthToken).filter(
                and_(
                    OAuthToken.expires_at < datetime.now(timezone.utc),
                    OAuthToken.is_active == True
                )
            ).all()
            
            for token in expired_tokens:
                token.deactivate()
            
            self.session.commit()
            
            logger.info(f"Cleaned up {len(expired_tokens)} expired OAuth tokens")
            return len(expired_tokens)
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to cleanup expired tokens: {e}")
            return 0
    
    # Statistics and Monitoring
    
    async def get_oauth_statistics(self) -> Dict[str, Any]:
        """
        Get OAuth repository statistics.
        
        Returns:
            Dictionary with OAuth statistics
        """
        try:
            stats = {
                "total_oauth_users": self.session.query(OAuthUser).count(),
                "active_oauth_users": self.session.query(OAuthUser).filter(OAuthUser.is_active == True).count(),
                "total_oauth_tokens": self.session.query(OAuthToken).count(),
                "active_oauth_tokens": self.session.query(OAuthToken).filter(
                    and_(
                        OAuthToken.is_active == True,
                        OAuthToken.is_revoked == False,
                        OAuthToken.expires_at > datetime.now(timezone.utc)
                    )
                ).count(),
                "expired_tokens": self.session.query(OAuthToken).filter(
                    OAuthToken.expires_at <= datetime.now(timezone.utc)
                ).count()
            }
            
            # Provider breakdown
            provider_stats = {}
            providers = self.session.query(OAuthUser.provider).distinct().all()
            for (provider,) in providers:
                provider_stats[provider] = {
                    "users": self.session.query(OAuthUser).filter(OAuthUser.provider == provider).count(),
                    "active_tokens": self.session.query(OAuthToken).filter(
                        and_(
                            OAuthToken.provider == provider,
                            OAuthToken.is_active == True,
                            OAuthToken.is_revoked == False,
                            OAuthToken.expires_at > datetime.now(timezone.utc)
                        )
                    ).count()
                }
            
            stats["providers"] = provider_stats
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get OAuth statistics: {e}")
            return {}


__all__ = ["OAuthRepository", "OAuthRepositoryError"]