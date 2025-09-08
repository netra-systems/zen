"""
Session Service - Single Source of Truth for Session Management

This service provides a unified interface for session management operations,
following SSOT principles and maintaining service independence.

Business Value: Enables persistent user sessions that improve UX by reducing
re-authentication friction and supporting multi-device login scenarios.
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, UTC

from auth_service.auth_core.config import AuthConfig
from auth_service.services.redis_service import RedisService
from auth_service.services.jwt_service import JWTService

logger = logging.getLogger(__name__)


class SessionService:
    """
    Single Source of Truth for session management operations.
    
    This service provides a unified interface for creating, validating,
    and managing user sessions using Redis for persistence.
    """
    
    def __init__(self, auth_config: AuthConfig, redis_service: Optional[RedisService] = None, jwt_service: Optional[JWTService] = None):
        """
        Initialize SessionService with configuration and dependencies.
        
        Args:
            auth_config: Authentication configuration
            redis_service: Optional Redis service instance
            jwt_service: Optional JWT service instance
        """
        self.auth_config = auth_config
        self.redis_service = redis_service or RedisService(auth_config)
        self.jwt_service = jwt_service or JWTService(auth_config)
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
        
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.session_prefix}{session_id}"
    
    def _get_user_sessions_key(self, user_id: str) -> str:
        """Generate Redis key for user sessions list."""
        return f"{self.user_sessions_prefix}{user_id}"
    
    async def create_session(
        self, 
        user_id: str, 
        email: str = None,
        access_token: str = None,
        session_data: Dict[str, Any] = None,
        user_data: Dict[str, Any] = None,
        expires_in: Optional[int] = None
    ) -> str:
        """
        Create a new user session.
        
        Args:
            user_id: User ID
            user_data: User information to store in session
            expires_in: Session expiration time in seconds (default from config)
            
        Returns:
            Session information including session ID and expiration
        """
        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Set expiration time
            if expires_in is None:
                # Convert hours to seconds
                expires_in = self.auth_config.get_session_ttl_hours() * 3600
            
            # Prepare session data
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "user_data": user_data,
                "created_at": datetime.now(UTC).isoformat(),
                "expires_at": (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat(),
                "last_accessed": datetime.now(UTC).isoformat()
            }
            
            # Store session in Redis
            session_key = self._get_session_key(session_id)
            await self.redis_service.set(
                session_key, 
                json.dumps(session_data), 
                ex=expires_in
            )
            
            # Add session to user's session list
            await self._add_to_user_sessions(user_id, session_id, expires_in)
            
            logger.info(f"Created session {session_id} for user {user_id}")
            
            return {
                "session_id": session_id,
                "user_id": user_id,
                "expires_in": expires_in,
                "created_at": session_data["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None if not found/expired
        """
        try:
            session_key = self._get_session_key(session_id)
            session_data_json = await self.redis_service.get(session_key)
            
            if not session_data_json:
                return None
            
            session_data = json.loads(session_data_json)
            
            # Check if session is expired
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            if datetime.now(UTC) > expires_at:
                # Session expired, clean it up
                await self.delete_session(session_id)
                return None
            
            # Update last accessed time
            session_data["last_accessed"] = datetime.now(UTC).isoformat()
            await self.redis_service.set(
                session_key,
                json.dumps(session_data),
                ex=int((expires_at - datetime.now(UTC)).total_seconds())
            )
            
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate session and return user data if valid.
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            User data if session is valid, None otherwise
        """
        try:
            session_data = await self.get_session(session_id)
            if not session_data:
                return None
            
            return {
                "user_id": session_data["user_id"],
                "user_data": session_data["user_data"],
                "session_id": session_id,
                "valid": True
            }
            
        except Exception as e:
            logger.error(f"Failed to validate session {session_id}: {e}")
            return None
    
    async def refresh_session(self, session_id: str, expires_in: Optional[int] = None) -> bool:
        """
        Refresh session expiration time.
        
        Args:
            session_id: Session ID to refresh
            expires_in: New expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session_data = await self.get_session(session_id)
            if not session_data:
                return False
            
            # Set new expiration
            if expires_in is None:
                # Convert hours to seconds
                expires_in = self.auth_config.get_session_ttl_hours() * 3600
            
            new_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
            session_data["expires_at"] = new_expires_at.isoformat()
            session_data["last_accessed"] = datetime.now(UTC).isoformat()
            
            # Update session in Redis
            session_key = self._get_session_key(session_id)
            await self.redis_service.set(
                session_key,
                json.dumps(session_data),
                ex=expires_in
            )
            
            logger.info(f"Refreshed session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get session to find user ID
            session_data = await self.get_session(session_id)
            if session_data:
                user_id = session_data["user_id"]
                # Remove from user's session list
                await self._remove_from_user_sessions(user_id, session_id)
            
            # Delete session from Redis
            session_key = self._get_session_key(session_id)
            deleted_count = await self.redis_service.delete(session_key)
            
            logger.info(f"Deleted session {session_id}")
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def delete_user_sessions(self, user_id: str) -> int:
        """
        Delete all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions deleted
        """
        try:
            # Get user's sessions
            user_sessions = await self.get_user_sessions(user_id)
            deleted_count = 0
            
            for session_id in user_sessions:
                if await self.delete_session(session_id):
                    deleted_count += 1
            
            # Clear user sessions list
            user_sessions_key = self._get_user_sessions_key(user_id)
            await self.redis_service.delete(user_sessions_key)
            
            logger.info(f"Deleted {deleted_count} sessions for user {user_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete sessions for user {user_id}: {e}")
            return 0
    
    async def get_user_sessions(self, user_id: str) -> List[str]:
        """
        Get all session IDs for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of session IDs
        """
        try:
            user_sessions_key = self._get_user_sessions_key(user_id)
            sessions_data = await self.redis_service.get(user_sessions_key)
            
            if not sessions_data:
                return []
            
            return json.loads(sessions_data)
            
        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {e}")
            return []
    
    async def _add_to_user_sessions(self, user_id: str, session_id: str, expires_in: int):
        """Add session to user's session list."""
        try:
            sessions = await self.get_user_sessions(user_id)
            if session_id not in sessions:
                sessions.append(session_id)
            
            user_sessions_key = self._get_user_sessions_key(user_id)
            await self.redis_service.set(
                user_sessions_key,
                json.dumps(sessions),
                ex=expires_in
            )
            
        except Exception as e:
            logger.error(f"Failed to add session {session_id} to user {user_id} sessions: {e}")
    
    async def _remove_from_user_sessions(self, user_id: str, session_id: str):
        """Remove session from user's session list."""
        try:
            sessions = await self.get_user_sessions(user_id)
            if session_id in sessions:
                sessions.remove(session_id)
                
                user_sessions_key = self._get_user_sessions_key(user_id)
                if sessions:
                    await self.redis_service.set(
                        user_sessions_key,
                        json.dumps(sessions)
                    )
                else:
                    await self.redis_service.delete(user_sessions_key)
                    
        except Exception as e:
            logger.error(f"Failed to remove session {session_id} from user {user_id} sessions: {e}")


__all__ = ["SessionService"]