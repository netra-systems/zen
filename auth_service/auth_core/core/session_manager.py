"""
Session Manager - Centralized session handling with Redis
Maintains 450-line limit with focused session management
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import redis

from auth_service.auth_core.config import AuthConfig

logger = logging.getLogger(__name__)

class SessionManager:
    """Single Source of Truth for session management"""
    
    def __init__(self):
        # In containerized environments, Redis should connect to a Redis service, not localhost
        # For staging/production, Redis is disabled by environment check
        self.redis_url = AuthConfig.get_redis_url()
        self.session_ttl = AuthConfig.get_session_ttl_hours()
        self.redis_client = None
        self.redis_enabled = self._should_enable_redis()
        if self.redis_enabled:
            self._connect_redis()
        else:
            logger.info("Redis disabled for current environment")
        
        # Initialize race condition protection
        self.used_refresh_tokens = set()
        self._session_locks = {}
        
        # In-memory fallback for when Redis fails
        self._memory_sessions = {}
        self._fallback_mode = False
            
    def _should_enable_redis(self) -> bool:
        """Determine if Redis should be enabled based on environment"""
        env = AuthConfig.get_environment()
        redis_disabled = AuthConfig.is_redis_disabled()
        
        # Disable Redis in staging or if explicitly disabled
        if env == "staging" or redis_disabled:
            return False
        return True
        
    def _connect_redis(self):
        """Establish Redis connection"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis connected for session management")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def create_session(self, user_id: str, user_data: Dict, session_id: Optional[str] = None) -> str:
        """Create new session and return session ID"""
        # Allow custom session ID for session fixation protection
        if not session_id:
            session_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            **user_data
        }
        
        if not self.redis_enabled:
            # Use memory fallback when Redis is disabled
            if self._store_session_memory(session_id, session_data):
                return session_id
            return None
        
        # Try Redis first, fallback to memory if Redis fails
        if self._store_session(session_id, session_data):
            return session_id
        else:
            # Redis failed, try memory fallback
            self._enable_fallback_mode()
            if self._store_session_memory(session_id, session_data):
                return session_id
            return None
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve session data with fallback support"""
        if not self.redis_enabled:
            # Use memory fallback when Redis is disabled
            return self._get_session_memory(session_id)
        
        if self._fallback_mode:
            # Already in fallback mode, use memory
            return self._get_session_memory(session_id)
            
        try:
            key = self._get_session_key(session_id)
            data = self.redis_client.get(key)
            
            if data:
                session = json.loads(data)
                # Update last activity
                await self._update_activity_async(session_id)
                return session
                
        except Exception as e:
            logger.error(f"Redis session retrieval failed: {e}")
            # Enable fallback and try memory
            self._enable_fallback_mode()
            return self._get_session_memory(session_id)
            
        return None
    
    async def update_session(self, session_id: str, 
                      updates: Dict) -> bool:
        """Update existing session data"""
        if not self.redis_enabled:
            # Return True to indicate operation "succeeded" when Redis is disabled
            logger.debug(f"Session update skipped for {session_id} (Redis disabled)")
            return True
            
        session = await self.get_session(session_id)
        if not session:
            return False
            
        session.update(updates)
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        
        return self._store_session(session_id, session)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session (logout) with fallback support"""
        if not self.redis_enabled:
            # Use memory fallback when Redis is disabled
            return self._delete_session_memory(session_id)
        
        if self._fallback_mode:
            # Already in fallback mode, use memory
            return self._delete_session_memory(session_id)
            
        try:
            key = self._get_session_key(session_id)
            result = self.redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Redis session deletion failed: {e}")
            # Enable fallback and try memory
            self._enable_fallback_mode()
            return self._delete_session_memory(session_id)
    
    async def validate_session(self, session_id: str) -> bool:
        """Check if session is valid and active"""
        if not self.redis_enabled:
            # When Redis is disabled, sessions are not validated server-side
            # Rely on JWT token validation instead
            logger.debug(f"Session validation skipped for {session_id} (Redis disabled)")
            return True
            
        session = await self.get_session(session_id)
        if not session:
            return False
            
        # Check expiration
        last_activity = datetime.fromisoformat(session["last_activity"])
        expiry = last_activity + timedelta(hours=self.session_ttl)
        
        if datetime.now(timezone.utc) > expiry:
            self.delete_session(session_id)
            return False
            
        return True
    
    async def get_user_session(self, user_id: str) -> Optional[Dict]:
        """Get most recent active session for a user"""
        sessions = await self.get_user_sessions(user_id)
        if not sessions:
            return None
        return max(sessions, key=lambda s: s.get("last_activity", ""))

    async def get_user_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user"""
        if not self.redis_enabled or not self.redis_client:
            logger.debug(f"User sessions retrieval skipped for {user_id} (Redis disabled)")
            return []
            
        try:
            pattern = f"session:*"
            sessions = []
            
            for key in self.redis_client.scan_iter(pattern):
                data = self.redis_client.get(key)
                if data:
                    session = json.loads(data)
                    if session.get("user_id") == user_id:
                        session_id = key.replace("session:", "")
                        sessions.append({
                            "session_id": session_id,
                            **session
                        })
                        
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []
    
    async def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user with race condition protection"""
        # Use a lock to prevent concurrent invalidation operations for the same user
        if user_id not in self._session_locks:
            self._session_locks[user_id] = asyncio.Lock()
        
        async with self._session_locks[user_id]:
            sessions = await self.get_user_sessions(user_id)
            count = 0
            
            # Process session deletions concurrently but safely
            delete_tasks = []
            for session in sessions:
                delete_tasks.append(self._delete_session_async(session["session_id"]))
            
            if delete_tasks:
                results = await asyncio.gather(*delete_tasks, return_exceptions=True)
                count = sum(1 for result in results if result is True)
                
        return count
    
    async def _delete_session_async(self, session_id: str) -> bool:
        """Async wrapper for session deletion"""
        return self.delete_session(session_id)
    
    def _store_session(self, session_id: str, 
                      session_data: Dict) -> bool:
        """Store session data in Redis"""
        if not self.redis_enabled or not self.redis_client:
            logger.debug(f"Session storage skipped for {session_id} (Redis disabled)")
            return True  # Return True to indicate operation "succeeded"
            
        try:
            key = self._get_session_key(session_id)
            value = json.dumps(session_data)
            
            return self.redis_client.setex(
                key,
                timedelta(hours=self.session_ttl),
                value
            )
            
        except Exception as e:
            logger.error(f"Session storage failed: {e}")
            return False
    
    def _update_activity(self, session_id: str):
        """Update session last activity timestamp"""
        if not self.redis_enabled or not self.redis_client:
            return
            
        try:
            key = self._get_session_key(session_id)
            # Reset TTL
            self.redis_client.expire(
                key, 
                timedelta(hours=self.session_ttl)
            )
        except Exception:
            pass
    
    async def _update_activity_async(self, session_id: str):
        """Update session last activity timestamp (async version)"""
        if not self.redis_enabled or not self.redis_client:
            return
            
        try:
            key = self._get_session_key(session_id)
            # Reset TTL
            self.redis_client.expire(
                key, 
                timedelta(hours=self.session_ttl)
            )
        except Exception:
            pass
    
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"session:{session_id}"
    
    def health_check(self) -> bool:
        """Check Redis connection health"""
        if not self.redis_enabled:
            # When Redis is disabled, consider it "healthy" since it's intentionally disabled
            return True
            
        if not self.redis_client:
            return False
            
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False
    
    def _enable_fallback_mode(self):
        """Enable in-memory fallback when Redis fails"""
        if not self._fallback_mode:
            self._fallback_mode = True
            logger.warning("Redis connection failed, enabling in-memory session fallback")
    
    def _store_session_memory(self, session_id: str, session_data: Dict) -> bool:
        """Store session in memory as fallback"""
        try:
            self._memory_sessions[session_id] = {
                **session_data,
                "_expires_at": datetime.now(timezone.utc) + timedelta(hours=self.session_ttl)
            }
            logger.debug(f"Session {session_id} stored in memory fallback")
            return True
        except Exception as e:
            logger.error(f"Memory session storage failed: {e}")
            return False
    
    def _get_session_memory(self, session_id: str) -> Optional[Dict]:
        """Retrieve session from memory fallback"""
        try:
            session = self._memory_sessions.get(session_id)
            if not session:
                return None
            
            # Check expiration
            if datetime.now(timezone.utc) > session.get("_expires_at", datetime.now(timezone.utc)):
                del self._memory_sessions[session_id]
                return None
            
            # Update last activity
            session["last_activity"] = datetime.now(timezone.utc).isoformat()
            session["_expires_at"] = datetime.now(timezone.utc) + timedelta(hours=self.session_ttl)
            
            # Return session without internal fields
            return {k: v for k, v in session.items() if not k.startswith("_")}
        except Exception as e:
            logger.error(f"Memory session retrieval failed: {e}")
            return None
    
    def _delete_session_memory(self, session_id: str) -> bool:
        """Delete session from memory fallback"""
        try:
            if session_id in self._memory_sessions:
                del self._memory_sessions[session_id]
                return True
            return False
        except Exception as e:
            logger.error(f"Memory session deletion failed: {e}")
            return False
    
    def regenerate_session_id(self, old_session_id: str, user_id: str, user_data: Dict) -> str:
        """Regenerate session ID for session fixation protection"""
        import secrets
        
        # Create new session with cryptographically secure ID
        new_session_id = secrets.token_urlsafe(32)
        
        # Create new session
        self.create_session(user_id, user_data, new_session_id)
        
        # Delete old session if it exists
        if old_session_id:
            self.delete_session(old_session_id)
        
        logger.info(f"Session ID regenerated for user {user_id}")
        return new_session_id