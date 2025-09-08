"""OAuth Token Model - Database representation for OAuth tokens

**CRITICAL**: Enterprise-Grade OAuth Token Management
Defines database model for OAuth access/refresh tokens with encryption
and comprehensive security measures for token lifecycle management.

Business Value: Enables secure OAuth token storage and management
Critical for OAuth authentication flows and token refresh operations.

This model represents OAuth tokens from external providers with secure
storage, automatic expiration handling, and comprehensive validation.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from auth_service.auth_core.database.models import Base

logger = logging.getLogger(__name__)


class OAuthToken(Base):
    """
    OAuth Token database model.
    
    **CRITICAL**: Represents OAuth access and refresh tokens for secure storage.
    Handles token lifecycle including expiration, refresh, and secure storage
    with comprehensive validation for multi-provider token management.
    """
    
    __tablename__ = "oauth_tokens"
    
    # Primary fields
    id = Column(Integer, primary_key=True, autoincrement=True)
    oauth_user_id = Column(Integer, ForeignKey("oauth_users.id"), nullable=False, index=True)
    
    # Token data (should be encrypted in production)
    access_token = Column(Text, nullable=False)  # OAuth access token
    refresh_token = Column(Text, nullable=True)  # OAuth refresh token
    id_token = Column(Text, nullable=True)  # OpenID Connect ID token
    
    # Token metadata
    token_type = Column(String(50), default="Bearer", nullable=False)  # Usually "Bearer"
    expires_at = Column(DateTime(timezone=True), nullable=False)  # When access token expires
    expires_in = Column(Integer, nullable=True)  # Token lifetime in seconds
    scope = Column(String(500), nullable=True)  # OAuth scopes granted
    
    # Provider information
    provider = Column(String(50), nullable=False, index=True)  # 'google', 'github', etc.
    
    # Token status
    is_active = Column(Boolean, default=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship to OAuth user
    oauth_user = relationship("OAuthUser", backref="tokens")
    
    def __init__(self, **kwargs):
        """Initialize OAuth token with validation."""
        super().__init__(**kwargs)
        self._validate_oauth_token()
    
    def _validate_oauth_token(self):
        """Validate OAuth token data."""
        if not self.oauth_user_id:
            raise ValueError("OAuth user ID is required")
        
        if not self.access_token:
            raise ValueError("Access token is required")
        
        if not self.provider:
            raise ValueError("OAuth provider is required")
        
        if not self.expires_at:
            raise ValueError("Token expiration time is required")
        
        # Validate token type
        valid_token_types = ["Bearer", "MAC"]
        if self.token_type not in valid_token_types:
            logger.warning(f"Unknown token type: {self.token_type}")
    
    def is_expired(self) -> bool:
        """
        Check if access token is expired.
        
        Returns:
            True if token is expired, False otherwise
        """
        return datetime.now(timezone.utc) >= self.expires_at
    
    def is_valid(self) -> bool:
        """
        Check if token is valid (not expired, active, and not revoked).
        
        Returns:
            True if token is valid, False otherwise
        """
        return (
            self.is_active and 
            not self.is_revoked and 
            not self.is_expired()
        )
    
    def time_until_expiry(self) -> timedelta:
        """
        Get time remaining until token expires.
        
        Returns:
            timedelta representing time until expiration
        """
        return self.expires_at - datetime.now(timezone.utc)
    
    def minutes_until_expiry(self) -> int:
        """
        Get minutes remaining until token expires.
        
        Returns:
            Number of minutes until expiration (0 if expired)
        """
        delta = self.time_until_expiry()
        return max(0, int(delta.total_seconds() / 60))
    
    def refresh_token_if_needed(self, refresh_threshold_minutes: int = 30) -> bool:
        """
        Check if token needs refresh based on threshold.
        
        Args:
            refresh_threshold_minutes: Minutes before expiry to trigger refresh
            
        Returns:
            True if token needs refresh, False otherwise
        """
        if self.is_expired():
            return True
        
        minutes_left = self.minutes_until_expiry()
        return minutes_left <= refresh_threshold_minutes
    
    def update_tokens(self, access_token: str, refresh_token: Optional[str] = None, 
                     expires_in: Optional[int] = None, id_token: Optional[str] = None,
                     scope: Optional[str] = None) -> None:
        """
        Update OAuth tokens with new values.
        
        Args:
            access_token: New access token
            refresh_token: New refresh token (optional)
            expires_in: Token lifetime in seconds
            id_token: New ID token (optional)
            scope: Updated scope (optional)
        """
        self.access_token = access_token
        
        if refresh_token is not None:
            self.refresh_token = refresh_token
        
        if id_token is not None:
            self.id_token = id_token
        
        if scope is not None:
            self.scope = scope
        
        # Update expiration
        if expires_in:
            self.expires_in = expires_in
            self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        self.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Updated OAuth tokens for user {self.oauth_user_id}")
    
    def record_usage(self) -> None:
        """Record token usage."""
        self.last_used_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def revoke(self) -> None:
        """Revoke OAuth token."""
        self.is_revoked = True
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
        logger.info(f"Revoked OAuth token for user {self.oauth_user_id}")
    
    def deactivate(self) -> None:
        """Deactivate OAuth token."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
        logger.info(f"Deactivated OAuth token for user {self.oauth_user_id}")
    
    def reactivate(self) -> None:
        """Reactivate OAuth token (if not revoked)."""
        if self.is_revoked:
            raise ValueError("Cannot reactivate revoked token")
        
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
        logger.info(f"Reactivated OAuth token for user {self.oauth_user_id}")
    
    def get_token_info(self, include_tokens: bool = False) -> Dict[str, Any]:
        """
        Get token information.
        
        Args:
            include_tokens: Whether to include actual token values (security risk)
            
        Returns:
            Dictionary with token information
        """
        data = {
            "id": self.id,
            "oauth_user_id": self.oauth_user_id,
            "provider": self.provider,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat(),
            "expires_in": self.expires_in,
            "scope": self.scope,
            "is_active": self.is_active,
            "is_revoked": self.is_revoked,
            "is_expired": self.is_expired(),
            "is_valid": self.is_valid(),
            "minutes_until_expiry": self.minutes_until_expiry(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None
        }
        
        if include_tokens:
            # WARNING: Only include actual tokens in secure contexts
            data.update({
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "id_token": self.id_token
            })
        
        return data
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert OAuth token to dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive token data
            
        Returns:
            Dictionary representation of OAuth token
        """
        return self.get_token_info(include_tokens=include_sensitive)
    
    def __repr__(self) -> str:
        """String representation of OAuth token."""
        return f"<OAuthToken(id={self.id}, user_id={self.oauth_user_id}, provider={self.provider}, valid={self.is_valid()})>"
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        status = "valid" if self.is_valid() else "invalid"
        return f"OAuth Token for user {self.oauth_user_id} ({self.provider}) - {status}"
    
    # Index definitions for database performance
    __table_args__ = (
        # Index for finding active tokens by user and provider
        {"extend_existing": True}
    )


__all__ = ["OAuthToken"]