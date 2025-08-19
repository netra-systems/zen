"""
Session Manager - Centralized session handling with Redis
Maintains 300-line limit with focused session management
"""
import os
import json
import uuid
import redis
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """Single Source of Truth for session management"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.session_ttl = int(os.getenv("SESSION_TTL_HOURS", "24"))
        self.redis_client = None
        self.redis_enabled = self._should_enable_redis()
        if self.redis_enabled:
            self._connect_redis()
        else:
            logger.info("Redis disabled for current environment")
            
    def _should_enable_redis(self) -> bool:
        """Determine if Redis should be enabled based on environment"""
        env = os.getenv("ENVIRONMENT", "development").lower()
        redis_disabled = os.getenv("REDIS_DISABLED", "false").lower() == "true"
        
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
    
    def create_session(self, user_id: str, user_data: Dict) -> str:
        """Create new session and return session ID"""
        session_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            **user_data
        }
        
        if not self.redis_enabled:
            # Return session ID but don't store when Redis is disabled
            logger.debug(f"Created session {session_id} (Redis disabled - not stored)")
            return session_id
        
        if self._store_session(session_id, session_data):
            return session_id
        return None
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve session data"""
        if not self.redis_enabled or not self.redis_client:
            # Return None when Redis is disabled - sessions won't be stored/retrieved
            logger.debug(f"Session retrieval skipped for {session_id} (Redis disabled)")
            return None
            
        try:
            key = self._get_session_key(session_id)
            data = self.redis_client.get(key)
            
            if data:
                session = json.loads(data)
                # Update last activity
                await self._update_activity_async(session_id)
                return session
                
        except Exception as e:
            logger.error(f"Session retrieval failed: {e}")
            
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
        session["last_activity"] = datetime.utcnow().isoformat()
        
        return self._store_session(session_id, session)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session (logout)"""
        if not self.redis_enabled or not self.redis_client:
            # Return True to indicate operation "succeeded" when Redis is disabled
            logger.debug(f"Session deletion skipped for {session_id} (Redis disabled)")
            return True
            
        try:
            key = self._get_session_key(session_id)
            result = self.redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Session deletion failed: {e}")
            return False
    
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
        
        if datetime.utcnow() > expiry:
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
        """Invalidate all sessions for a user"""
        sessions = await self.get_user_sessions(user_id)
        count = 0
        
        for session in sessions:
            if self.delete_session(session["session_id"]):
                count += 1
                
        return count
    
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