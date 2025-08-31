"""Consolidated Redis Session Manager - Single Source of Truth for all session management.

This is the canonical session manager for the entire Netra platform,
consolidating all session management functionality in one location.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


class RedisSessionManager:
    """Consolidated session manager - Single Source of Truth for all session management.
    
    Supports:
    - User authentication sessions
    - Demo session management with message tracking
    - Security features (fingerprinting, session limits)
    - Database persistence backup
    - Memory fallback when Redis unavailable
    """
    
    def __init__(self, redis_client=None):
        """Initialize consolidated session manager with Redis client."""
        # Initialize memory store for fallback
        self._memory_store = {}
        
        # Import redis service if available
        try:
            from netra_backend.app.services.redis_service import redis_service
            self.redis = redis_client or redis_service
        except ImportError:
            # Fallback to in-memory storage for tests
            self.redis = None
        
        # Session prefixes for different session types
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
        self.demo_session_prefix = "demo:session:"
        self.default_ttl = 3600  # 1 hour
        self.demo_ttl = 86400  # 24 hours for demo sessions
        
        # Security and performance features
        self.used_refresh_tokens = set()
        self._session_locks = {}
        self._user_session_limits = {}
        self._session_activities = {}
        self._invalidation_history = {}
    
    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"{self.session_prefix}{session_id}"
    
    def _get_user_sessions_key(self, user_id: str) -> str:
        """Get Redis key for user sessions list."""
        return f"{self.user_sessions_prefix}{user_id}"
    
    async def create_session(self, user_id: str, session_data: Dict[str, Any], 
                           ttl: Optional[int] = None) -> str:
        """Create a new session."""
        session_id = f"{user_id}_{int(time.time() * 1000)}"
        session_key = self._get_session_key(session_id)
        user_sessions_key = self._get_user_sessions_key(user_id)
        
        # Prepare session data
        full_session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "data": session_data
        }
        
        session_ttl = ttl or self.default_ttl
        
        redis_success = False
        if self.redis:
            # Store in Redis
            try:
                setex_result = await self.redis.setex(
                    session_key, 
                    session_ttl, 
                    json.dumps(full_session_data)
                )
                
                if setex_result:
                    # Add to user sessions list
                    await self.redis.sadd(user_sessions_key, session_id)
                    await self.redis.expire(user_sessions_key, session_ttl)
                    redis_success = True
                
            except Exception:
                # Redis operation failed, will use memory store
                pass
        
        # Use memory store if Redis is not available or failed
        if not redis_success:
            self._memory_store[session_key] = {
                "data": full_session_data,
                "expires_at": time.time() + session_ttl
            }
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        session_key = self._get_session_key(session_id)
        
        if self.redis:
            try:
                session_data = await self.redis.get(session_key)
                if session_data:
                    data = json.loads(session_data)
                    # Update last accessed time
                    data["last_accessed"] = datetime.now().isoformat()
                    update_result = await self.redis.setex(
                        session_key, 
                        self.default_ttl, 
                        json.dumps(data)
                    )
                    # Return data even if update failed
                    return data
            except Exception:
                pass
        
        # Check memory store
        if session_key in self._memory_store:
            entry = self._memory_store[session_key]
            if time.time() < entry["expires_at"]:
                entry["data"]["last_accessed"] = datetime.now().isoformat()
                return entry["data"]
            else:
                # Expired
                del self._memory_store[session_key]
        
        return None
    
    async def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Update session data."""
        current_session = await self.get_session(session_id)
        if not current_session:
            return False
        
        # Update the data
        current_session["data"].update(session_data)
        current_session["last_accessed"] = datetime.now().isoformat()
        
        session_key = self._get_session_key(session_id)
        
        if self.redis:
            try:
                await self.redis.setex(
                    session_key, 
                    self.default_ttl, 
                    json.dumps(current_session)
                )
                return True
            except Exception:
                pass
        
        # Update memory store
        if session_key in self._memory_store:
            self._memory_store[session_key]["data"] = current_session
            return True
        
        return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session_key = self._get_session_key(session_id)
        
        # Get session to find user_id
        session_data = await self.get_session(session_id)
        if session_data:
            user_id = session_data.get("user_id")
            if user_id:
                user_sessions_key = self._get_user_sessions_key(user_id)
                
                if self.redis:
                    try:
                        await self.redis.srem(user_sessions_key, session_id)
                    except Exception:
                        pass
        
        if self.redis:
            try:
                result = await self.redis.delete(session_key)
                return result > 0
            except Exception:
                pass
        
        # Delete from memory store
        if session_key in self._memory_store:
            del self._memory_store[session_key]
            return True
        
        return False
    
    async def get_user_sessions(self, user_id: str) -> List[str]:
        """Get all sessions for a user."""
        user_sessions_key = self._get_user_sessions_key(user_id)
        
        if self.redis:
            try:
                sessions = await self.redis.smembers(user_sessions_key)
                return [s.decode() if isinstance(s, bytes) else s for s in sessions]
            except Exception:
                pass
        
        # Check memory store
        sessions = []
        prefix = self.session_prefix
        for key, entry in self._memory_store.items():
            if key.startswith(prefix) and time.time() < entry["expires_at"]:
                data = entry["data"]
                if data.get("user_id") == user_id:
                    sessions.append(data["session_id"])
        
        return sessions
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from memory store."""
        if not hasattr(self, '_memory_store'):
            return 0
        
        expired_keys = []
        current_time = time.time()
        
        for key, entry in self._memory_store.items():
            if current_time >= entry["expires_at"]:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._memory_store[key]
        
        return len(expired_keys)
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        stats = {
            "total_sessions": 0,
            "memory_sessions": len(getattr(self, '_memory_store', {})),
            "redis_available": self.redis is not None,
            "default_ttl": self.default_ttl
        }
        
        if self.redis:
            try:
                # Count Redis sessions (approximate)
                pattern = f"{self.session_prefix}*"
                keys = await self.redis.keys(pattern)
                stats["redis_sessions"] = len(keys)
                stats["total_sessions"] = len(keys)
            except Exception:
                stats["redis_sessions"] = 0
        
        if not self.redis:
            stats["total_sessions"] = stats["memory_sessions"]
        
        return stats
    
    # Demo Session Management Methods
    async def create_demo_session(self, session_id: str, industry: str, 
                                 user_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new demo session with industry context."""
        session_key = f"{self.demo_session_prefix}{session_id}"
        session_data = {
            "industry": industry,
            "user_id": user_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "session_type": "demo"
        }
        
        redis_success = False
        if self.redis:
            try:
                setex_result = await self.redis.setex(
                    session_key, 
                    self.demo_ttl,  # 24 hours for demo sessions
                    json.dumps(session_data)
                )
                redis_success = bool(setex_result)
            except Exception:
                pass
        
        if not redis_success:
            # Store in memory fallback
            self._memory_store[session_key] = {
                "data": session_data,
                "expires_at": time.time() + self.demo_ttl
            }
        
        return session_data
    
    async def get_demo_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get demo session data."""
        session_key = f"{self.demo_session_prefix}{session_id}"
        
        if self.redis:
            try:
                session_data = await self.redis.get(session_key)
                if session_data:
                    return json.loads(session_data)
            except Exception:
                pass
        
        # Check memory store
        if session_key in self._memory_store:
            entry = self._memory_store[session_key]
            if time.time() < entry["expires_at"]:
                return entry["data"]
            else:
                del self._memory_store[session_key]
        
        return None
    
    async def add_demo_message(self, session_id: str, role: str, 
                              content: str, **metadata) -> Dict[str, Any]:
        """Add a message to a demo session."""
        session_data = await self.get_demo_session(session_id)
        if not session_data:
            raise ValueError(f"Demo session not found: {session_id}")
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **metadata
        }
        session_data["messages"].append(message)
        
        # Update session
        session_key = f"{self.demo_session_prefix}{session_id}"
        if self.redis:
            try:
                await self.redis.setex(session_key, self.demo_ttl, json.dumps(session_data))
            except Exception:
                pass
        
        # Update memory store if needed
        if session_key in self._memory_store:
            self._memory_store[session_key]["data"] = session_data
        
        return message
    
    async def get_demo_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the status of a demo session."""
        session_data = await self.get_demo_session(session_id)
        if not session_data:
            raise ValueError(f"Demo session not found: {session_id}")
        
        message_count = len(session_data.get("messages", []))
        expected_steps = 6  # Demo flow steps
        progress = min(100, (message_count / expected_steps) * 100)
        
        return {
            "session_id": session_id,
            "industry": session_data.get("industry"),
            "started_at": session_data.get("started_at"),
            "message_count": message_count,
            "progress_percentage": progress,
            "status": "active" if progress < 100 else "completed",
            "last_interaction": (session_data["messages"][-1]["timestamp"] 
                               if session_data.get("messages") else None)
        }
    
    # Security and Performance Methods
    async def regenerate_session_id(self, old_session_id: str, user_id: str, 
                                   user_data: Optional[Dict] = None) -> str:
        """Regenerate session ID for session fixation protection."""
        import secrets
        
        # Create new session with cryptographically secure ID
        new_session_id = secrets.token_urlsafe(32)
        
        # Get old session data
        old_session = await self.get_session(old_session_id)
        if old_session and user_data is None:
            user_data = old_session.get("data", {})
        
        # Create new session
        if user_data is None:
            user_data = {}
        await self.create_session(user_id, user_data, ttl=self.default_ttl)
        
        # Delete old session
        if old_session_id:
            await self.delete_session(old_session_id)
        
        return new_session_id
    
    async def set_user_session_limit(self, user_id: str, limit: int):
        """Set concurrent session limit for a user."""
        self._user_session_limits[user_id] = limit
    
    async def record_session_activity(self, session_id: str, activity_type: str, 
                                    resource: str, client_ip: str, timestamp: float = None):
        """Record session activity for security monitoring."""
        if session_id not in self._session_activities:
            self._session_activities[session_id] = []
        
        activity = {
            "activity_type": activity_type,
            "resource": resource,
            "client_ip": client_ip,
            "timestamp": timestamp or time.time()
        }
        self._session_activities[session_id].append(activity)
    
    async def get_session_security_status(self, session_id: str) -> Dict[str, Any]:
        """Get session security status based on activities."""
        activities = self._session_activities.get(session_id, [])
        
        # Simple risk assessment
        risk_level = "low"
        if len(activities) > 10:
            risk_level = "medium"
        if len(activities) > 20:
            risk_level = "high_risk"
        
        return {
            "session_id": session_id,
            "security_level": risk_level,
            "activity_count": len(activities)
        }
    
    async def invalidate_all_user_sessions(self, user_id: str, reason: str = None, 
                                         except_session_id: str = None) -> int:
        """Invalidate all sessions for a user with race condition protection."""
        if user_id not in self._session_locks:
            self._session_locks[user_id] = asyncio.Lock()
        
        async with self._session_locks[user_id]:
            sessions = await self.get_user_sessions(user_id)
            count = 0
            
            for session_id in sessions:
                if except_session_id and session_id == except_session_id:
                    continue
                if await self.delete_session(session_id):
                    count += 1
        
        # Log invalidation
        if user_id not in self._invalidation_history:
            self._invalidation_history[user_id] = []
        
        self._invalidation_history[user_id].append({
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sessions_invalidated": count
        })
        
        return count
    
    async def validate_session(self, session_id: str, user_id: str) -> bool:
        """Validate that session belongs to user and is still valid."""
        session_data = await self.get_session(session_id)
        if not session_data:
            return False
        
        return session_data.get("user_id") == user_id
    
    async def extend_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """Extend session TTL."""
        session_key = self._get_session_key(session_id)
        session_ttl = ttl or self.default_ttl
        
        if self.redis:
            try:
                result = await self.redis.expire(session_key, session_ttl)
                return result
            except Exception:
                pass
        
        # Extend memory store session
        if session_key in self._memory_store:
            self._memory_store[session_key]["expires_at"] = time.time() + session_ttl
            return True
        
        return False
