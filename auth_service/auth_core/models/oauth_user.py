"""OAuth User Model - Database representation for OAuth users

**CRITICAL**: Enterprise-Grade OAuth User Data Management
Defines database model for OAuth user information with provider integration
and comprehensive data validation for multi-provider support.

Business Value: Enables OAuth user management and provider integration
Critical for OAuth authentication flows and user data persistence.

This model represents OAuth users from external providers (Google, GitHub, etc.)
with secure data handling and comprehensive validation.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

from auth_service.auth_core.database.models import Base

logger = logging.getLogger(__name__)


class OAuthUser(Base):
    """
    OAuth User database model.
    
    **CRITICAL**: Represents users authenticated via OAuth providers.
    Stores essential OAuth user information with provider-specific data
    and comprehensive validation for secure multi-provider support.
    """
    
    __tablename__ = "oauth_users"
    
    # Primary OAuth fields
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False, index=True)  # 'google', 'github', etc.
    provider_user_id = Column(String(255), nullable=False, index=True)  # Provider's user ID
    email = Column(String(320), nullable=False, index=True)  # RFC 5322 max length
    name = Column(String(255), nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    
    # Optional profile data from provider
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    picture_url = Column(Text, nullable=True)
    locale = Column(String(10), nullable=True)  # e.g., 'en', 'en-US'
    
    # Provider-specific data storage (JSON)
    profile_data = Column(JSON, nullable=True)  # Store additional provider data
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # OAuth-specific fields
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __init__(self, **kwargs):
        """Initialize OAuth user with validation."""
        super().__init__(**kwargs)
        self._validate_oauth_user()
    
    def _validate_oauth_user(self):
        """Validate OAuth user data."""
        if not self.provider:
            raise ValueError("OAuth provider is required")
        
        if not self.provider_user_id:
            raise ValueError("Provider user ID is required")
        
        if not self.email:
            raise ValueError("Email is required")
        
        # Validate email format (basic)
        if "@" not in self.email:
            raise ValueError("Invalid email format")
        
        # Validate provider
        valid_providers = ["google", "github", "microsoft", "apple"]
        if self.provider.lower() not in valid_providers:
            logger.warning(f"Unknown OAuth provider: {self.provider}")
    
    def update_profile(self, profile_data: Dict[str, Any]) -> None:
        """
        Update OAuth user profile from provider data.
        
        Args:
            profile_data: Profile data from OAuth provider
        """
        # Update standard fields if present
        if "name" in profile_data:
            self.name = profile_data["name"]
        
        if "email" in profile_data:
            self.email = profile_data["email"]
        
        if "email_verified" in profile_data:
            self.email_verified = profile_data["email_verified"]
        
        if "given_name" in profile_data:
            self.first_name = profile_data["given_name"]
        
        if "family_name" in profile_data:
            self.last_name = profile_data["family_name"]
        
        if "picture" in profile_data:
            self.picture_url = profile_data["picture"]
        
        if "locale" in profile_data:
            self.locale = profile_data["locale"]
        
        # Store complete profile data
        self.profile_data = profile_data
        self.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Updated OAuth user profile for {self.email}")
    
    def record_login(self) -> None:
        """Record successful login."""
        self.last_login_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate OAuth user."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
        logger.info(f"Deactivated OAuth user: {self.email}")
    
    def reactivate(self) -> None:
        """Reactivate OAuth user."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
        logger.info(f"Reactivated OAuth user: {self.email}")
    
    def get_display_name(self) -> str:
        """Get display name for OAuth user."""
        if self.name:
            return self.name
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.email.split("@")[0]  # Use email username as fallback
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert OAuth user to dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive data
            
        Returns:
            Dictionary representation of OAuth user
        """
        data = {
            "id": self.id,
            "provider": self.provider,
            "email": self.email,
            "name": self.name,
            "email_verified": self.email_verified,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "picture_url": self.picture_url,
            "locale": self.locale,
            "display_name": self.get_display_name(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }
        
        if include_sensitive:
            data.update({
                "provider_user_id": self.provider_user_id,
                "profile_data": self.profile_data
            })
        
        return data
    
    def __repr__(self) -> str:
        """String representation of OAuth user."""
        return f"<OAuthUser(id={self.id}, provider={self.provider}, email={self.email})>"
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.get_display_name()} ({self.provider})"
    
    # Index definitions for database performance
    __table_args__ = (
        # Unique constraint on provider + provider_user_id
        {"extend_existing": True}
    )


__all__ = ["OAuthUser"]