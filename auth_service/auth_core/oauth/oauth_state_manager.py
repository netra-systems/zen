"""OAuth State Manager - CSRF Protection and State Management

**CRITICAL**: Enterprise-Grade OAuth State Management
Provides secure OAuth state generation, validation, and persistence
for CSRF protection during OAuth authorization flows.

Business Value: Prevents OAuth CSRF attacks that could compromise user accounts
Critical for secure OAuth authentication and user protection.

This module handles OAuth state lifecycle including generation, validation,
persistence, and cleanup with comprehensive security measures.
"""

import logging
import secrets
import json
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict

from auth_service.auth_core.oauth.oauth_config import OAuthConfig
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class OAuthStateData:
    """OAuth state data structure."""
    state_token: str
    provider: str
    redirect_uri: Optional[str]
    user_context: Dict[str, Any]
    additional_params: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    is_expired: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data["created_at"] = self.created_at.isoformat()
        data["expires_at"] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthStateData":
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return cls(**data)


@dataclass
class OAuthStateValidation:
    """OAuth state validation result."""
    is_valid: bool
    error_message: Optional[str] = None
    state_data: Optional[OAuthStateData] = None


class OAuthStateError(Exception):
    """Raised when OAuth state operations fail."""
    pass


class OAuthStateManager:
    """
    Single Source of Truth for OAuth state management.
    
    **CRITICAL**: All OAuth flows MUST use this state manager for CSRF protection.
    Provides secure state generation, validation, and persistence with automatic cleanup.
    """
    
    def __init__(self, config: Optional[OAuthConfig] = None):
        """
        Initialize OAuth state manager.
        
        Args:
            config: Optional OAuthConfig instance for dependency injection
        """
        self.config = config or OAuthConfig()
        self.env = get_env().get("ENVIRONMENT", "development").lower()
        self._in_memory_states: Dict[str, OAuthStateData] = {}
        
        # State configuration
        self.state_expiry_minutes = 10  # OAuth states expire after 10 minutes
        self.cleanup_interval_minutes = 30  # Clean up expired states every 30 minutes
        self.last_cleanup = datetime.now(timezone.utc)
    
    def create_oauth_state(self, state_data: Dict[str, Any]) -> OAuthStateData:
        """
        Create secure OAuth state for authorization flow.
        
        Args:
            state_data: Dictionary containing provider, redirect_uri, user_context, etc.
            
        Returns:
            OAuthStateData with generated state token
            
        Raises:
            OAuthStateError: If state creation fails
        """
        try:
            # Generate secure state token
            state_token = self._generate_state_token(state_data)
            
            # Create state data object
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(minutes=self.state_expiry_minutes)
            
            oauth_state = OAuthStateData(
                state_token=state_token,
                provider=state_data.get("provider", ""),
                redirect_uri=state_data.get("redirect_uri"),
                user_context=state_data.get("user_context", {}),
                additional_params=state_data.get("additional_params", {}),
                created_at=now,
                expires_at=expires_at
            )
            
            # Store state (in-memory for now, could be Redis in production)
            self._store_state(oauth_state)
            
            logger.info(f"Created OAuth state for provider {oauth_state.provider}")
            return oauth_state
            
        except Exception as e:
            logger.error(f"Failed to create OAuth state: {e}")
            raise OAuthStateError(f"State creation failed: {str(e)}")
    
    def validate_oauth_state(self, state_token: str) -> OAuthStateValidation:
        """
        Validate OAuth state token and retrieve associated data.
        
        Args:
            state_token: State token to validate
            
        Returns:
            OAuthStateValidation with validation result and data
        """
        try:
            # Clean up expired states periodically
            self._cleanup_expired_states()
            
            # Retrieve state data
            state_data = self._retrieve_state(state_token)
            if not state_data:
                return OAuthStateValidation(
                    is_valid=False,
                    error_message="OAuth state not found or invalid"
                )
            
            # Check expiration
            now = datetime.now(timezone.utc)
            if now > state_data.expires_at:
                state_data.is_expired = True
                self._remove_state(state_token)
                return OAuthStateValidation(
                    is_valid=False,
                    error_message="OAuth state has expired"
                )
            
            # Validate state token signature
            if not self._verify_state_token(state_token, state_data):
                return OAuthStateValidation(
                    is_valid=False,
                    error_message="OAuth state signature invalid"
                )
            
            return OAuthStateValidation(
                is_valid=True,
                state_data=state_data
            )
            
        except Exception as e:
            logger.error(f"OAuth state validation failed: {e}")
            return OAuthStateValidation(
                is_valid=False,
                error_message=f"State validation error: {str(e)}"
            )
    
    async def get_persisted_state(self, state_token: str) -> Optional[OAuthStateData]:
        """
        Get persisted OAuth state data (async for future Redis integration).
        
        Args:
            state_token: State token to retrieve
            
        Returns:
            OAuthStateData if found, None otherwise
        """
        return self._retrieve_state(state_token)
    
    async def expire_state(self, state_token: str) -> OAuthStateData:
        """
        Mark OAuth state as expired (async for future Redis integration).
        
        Args:
            state_token: State token to expire
            
        Returns:
            Updated OAuthStateData with is_expired=True
        """
        state_data = self._retrieve_state(state_token)
        if state_data:
            state_data.is_expired = True
            # Update in storage
            self._store_state(state_data)
        return state_data
    
    def cleanup_state(self, state_token: str) -> bool:
        """
        Clean up OAuth state after successful use.
        
        Args:
            state_token: State token to clean up
            
        Returns:
            True if state was cleaned up, False if not found
        """
        try:
            removed = self._remove_state(state_token)
            if removed:
                logger.info(f"Cleaned up OAuth state: {state_token[:16]}...")
            return removed
        except Exception as e:
            logger.error(f"Failed to cleanup OAuth state: {e}")
            return False
    
    def _generate_state_token(self, state_data: Dict[str, Any]) -> str:
        """
        Generate secure state token with HMAC signature.
        
        Args:
            state_data: State data to include in token generation
            
        Returns:
            Secure state token
        """
        # Generate random component
        random_part = secrets.token_urlsafe(24)
        
        # Create deterministic component from state data
        state_json = json.dumps(state_data, sort_keys=True)
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        
        # Combine components
        token_data = f"{random_part}.{timestamp}.{state_json}"
        
        # Sign with HMAC
        secret = self.config.oauth_state_secret.encode()
        signature = hmac.new(secret, token_data.encode(), hashlib.sha256).hexdigest()
        
        return f"{random_part}.{timestamp}.{signature}"
    
    def _verify_state_token(self, state_token: str, state_data: OAuthStateData) -> bool:
        """
        Verify state token signature.
        
        Args:
            state_token: State token to verify
            state_data: Associated state data
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            parts = state_token.split('.')
            if len(parts) != 3:
                return False
            
            random_part, timestamp, signature = parts
            
            # Recreate token data for verification
            original_data = {
                "provider": state_data.provider,
                "redirect_uri": state_data.redirect_uri,
                "user_context": state_data.user_context,
                "additional_params": state_data.additional_params
            }
            state_json = json.dumps(original_data, sort_keys=True)
            token_data = f"{random_part}.{timestamp}.{state_json}"
            
            # Verify signature
            secret = self.config.oauth_state_secret.encode()
            expected_signature = hmac.new(secret, token_data.encode(), hashlib.sha256).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"State token verification failed: {e}")
            return False
    
    def _store_state(self, state_data: OAuthStateData) -> None:
        """Store OAuth state data."""
        self._in_memory_states[state_data.state_token] = state_data
    
    def _retrieve_state(self, state_token: str) -> Optional[OAuthStateData]:
        """Retrieve OAuth state data."""
        return self._in_memory_states.get(state_token)
    
    def _remove_state(self, state_token: str) -> bool:
        """Remove OAuth state data."""
        if state_token in self._in_memory_states:
            del self._in_memory_states[state_token]
            return True
        return False
    
    def _cleanup_expired_states(self) -> None:
        """Clean up expired OAuth states."""
        now = datetime.now(timezone.utc)
        
        # Only cleanup if enough time has passed
        if (now - self.last_cleanup) < timedelta(minutes=self.cleanup_interval_minutes):
            return
        
        expired_tokens = []
        for token, state_data in self._in_memory_states.items():
            if now > state_data.expires_at:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            self._remove_state(token)
            
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired OAuth states")
        
        self.last_cleanup = now
    
    def get_active_states_count(self) -> int:
        """Get count of active OAuth states."""
        self._cleanup_expired_states()
        return len(self._in_memory_states)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of OAuth state manager.
        
        Returns:
            Dictionary with health check results
        """
        try:
            active_states = self.get_active_states_count()
            
            return {
                "service": "oauth_state_manager",
                "status": "healthy",
                "environment": self.env,
                "active_states": active_states,
                "state_expiry_minutes": self.state_expiry_minutes,
                "last_cleanup": self.last_cleanup.isoformat(),
                "oauth_state_secret_configured": bool(self.config.oauth_state_secret)
            }
            
        except Exception as e:
            logger.error(f"OAuth state manager health check failed: {e}")
            return {
                "service": "oauth_state_manager",
                "status": "unhealthy",
                "error": str(e),
                "environment": self.env
            }


__all__ = ["OAuthStateManager", "OAuthStateData", "OAuthStateValidation", "OAuthStateError"]