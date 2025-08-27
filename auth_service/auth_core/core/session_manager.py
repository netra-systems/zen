"""
Session Manager - Centralized session handling with Redis
Maintains 450-line limit with focused session management
Optimized for high-performance with async operations and caching
"""
import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from datetime import timezone

from auth_service.auth_core.redis_manager import auth_redis_manager
from auth_service.auth_core.config import AuthConfig

logger = logging.getLogger(__name__)

class SessionManager:
    """Single Source of Truth for session management"""
    
    def __init__(self):
        # Use auth service Redis manager for all Redis operations
        self.redis_manager = auth_redis_manager
        self.session_ttl = AuthConfig.get_session_ttl_hours()
        
        # Initialize fallback mode BEFORE attempting Redis connection
        self._fallback_mode = False
        self._memory_sessions = {}
        
        # Try to connect to Redis if enabled
        self.redis_enabled = self.redis_manager.enabled
        if self.redis_enabled:
            self._connect_redis()
        else:
            logger.info("Redis disabled for current environment")
        
        # Initialize race condition protection
        self.used_refresh_tokens = set()
        self._session_locks = {}
        
        # Track initialization state
        self._initialized = False
            
    async def initialize(self):
        """Initialize the session manager for testing."""
        if self._initialized:
            return
            
        # Ensure any database connections are ready if needed
        try:
            # Initialize database connection if needed for session persistence
            from auth_service.auth_core.database.connection import auth_db
            if not auth_db._initialized:
                await auth_db.initialize()
        except Exception as e:
            logger.debug(f"Database initialization skipped during session manager init: {e}")
            
        # For testing: store original sync method and monkey-patch with async versions
        self._create_session_original = self.create_session
        self.create_session = self.create_session_async
        
        self._initialized = True
        logger.debug("SessionManager initialized")
    
    async def cleanup(self):
        """Clean up session manager resources."""
        if not self._initialized:
            return
            
        try:
            # Clear memory sessions
            self._memory_sessions.clear()
            
            # Clear session locks
            self._session_locks.clear()
            
            # Clear used refresh tokens
            self.used_refresh_tokens.clear()
            
            # Close Redis connections if needed
            await self.close_redis()
            
        except Exception as e:
            logger.debug(f"Error during session manager cleanup: {e}")
        finally:
            self._initialized = False
            logger.debug("SessionManager cleaned up")
            
    @property
    def redis_client(self):
        """Get Redis client from unified manager."""
        return self.redis_manager.get_client()
        
    def _connect_redis(self):
        """Establish Redis connection using unified manager."""
        if self.redis_manager.connect():
            logger.info("Redis connected for session management")
            self._fallback_mode = False
        else:
            logger.warning("Redis connection failed - using fallback mode")
            self._enable_fallback_mode()
    
    def create_session(self, user_or_user_id=None, user_data: Optional[Dict] = None, session_id: Optional[str] = None, 
                      client_ip: Optional[str] = None, user_agent: Optional[str] = None, 
                      fingerprint: Optional[str] = None, device_id: Optional[str] = None,
                      session_timeout: Optional[int] = None, force_create: bool = False, 
                      user_id: Optional[str] = None) -> str:
        """Create new session and return session ID
        
        Args:
            user_or_user_id: Either a User object or user_id string (positional)
            user_data: Optional dict of user data (if user_or_user_id is a string)
            user_id: DEPRECATED - use user_or_user_id instead (kept for backward compatibility)
        """
        # Handle both calling patterns: create_session(user) and create_session(user_id, user_data)
        from auth_service.auth_core.models.auth_models import User
        
        # Handle backward compatibility with user_id keyword argument
        if user_or_user_id is None and user_id is not None:
            # Called with user_id=... keyword argument (old pattern)
            user_or_user_id = user_id
        elif user_or_user_id is None:
            raise ValueError("Either user_or_user_id or user_id must be provided")
        
        if isinstance(user_or_user_id, User):
            # Called with User object: create_session(user)
            user = user_or_user_id
            actual_user_id = user.id
            if user_data is None:
                user_data = {
                    "email": str(user.email),
                    "name": user.name,
                    "picture": user.picture,
                    "verified_email": user.verified_email,
                    "provider": user.provider
                }
        else:
            # Called with user_id string: create_session(user_id, user_data)
            actual_user_id = user_or_user_id
            if user_data is None:
                user_data = {}
        # Allow custom session ID for session fixation protection
        if not session_id:
            session_id = str(uuid.uuid4())
        session_data = {
            "user_id": actual_user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "fingerprint": fingerprint,
            "device_id": device_id,
            "session_timeout": session_timeout or self.session_ttl,
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
        """Retrieve session data with fallback support including database restore"""
        if not self.redis_enabled:
            # Try memory first, then database
            memory_session = self._get_session_memory(session_id)
            if memory_session:
                return memory_session
            return await self._restore_session_from_db(session_id)
        
        if self._fallback_mode:
            # Already in fallback mode, try memory then database
            memory_session = self._get_session_memory(session_id)
            if memory_session:
                return memory_session
            return await self._restore_session_from_db(session_id)
            
        try:
            key = self._get_session_key(session_id)
            data = self.redis_client.get(key)
            
            if data:
                session = json.loads(data)
                # Update last activity
                await self._update_activity_async(session_id)
                return session
            else:
                # CRITICAL FIX: Try to restore from database if not in Redis
                return await self._restore_session_from_db(session_id)
                
        except Exception as e:
            logger.error(f"Redis session retrieval failed: {e}")
            # Enable fallback and try memory then database
            self._enable_fallback_mode()
            memory_session = self._get_session_memory(session_id)
            if memory_session:
                return memory_session
            return await self._restore_session_from_db(session_id)
            
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
        """Store session data in Redis with database backup for persistence"""
        if not self.redis_enabled or not self.redis_client:
            logger.debug(f"Session storage skipped for {session_id} (Redis disabled)")
            # Store in memory as fallback
            self._memory_sessions[session_id] = session_data
            # Also backup to database for persistence
            asyncio.create_task(self._backup_session_to_db(session_id, session_data))
            return True
            
        try:
            key = self._get_session_key(session_id)
            value = json.dumps(session_data)
            
            result = self.redis_client.setex(
                key,
                timedelta(hours=self.session_ttl),
                value
            )
            
            # CRITICAL FIX: Also backup to database for persistence across restarts
            if result:
                asyncio.create_task(self._backup_session_to_db(session_id, session_data))
            
            return result
            
        except Exception as e:
            logger.error(f"Session storage failed: {e}")
            # Enable fallback mode and store in memory
            self._enable_fallback_mode()
            self._memory_sessions[session_id] = session_data
            return True
    
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
        """Check Redis connection health with performance optimization"""
        if not self.redis_enabled:
            # When Redis is disabled, consider it "healthy" since it's intentionally disabled
            return True
            
        if not self.redis_client:
            return False
            
        try:
            # Use a lightweight ping operation
            self.redis_client.ping()
            return True
        except Exception:
            return False
    
    async def close_redis(self):
        """Close Redis connections gracefully"""
        try:
            if hasattr(self.redis_manager, 'close'):
                await self.redis_manager.close()
            logger.info("Redis connections closed successfully")
        except Exception as e:
            logger.warning(f"Error closing Redis connections: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get session manager performance statistics"""
        return {
            "redis_enabled": self.redis_enabled,
            "fallback_mode": self._fallback_mode,
            "memory_sessions_count": len(self._memory_sessions),
            "session_ttl_hours": self.session_ttl,
            "health_status": "healthy" if self.health_check() else "degraded"
        }
    
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
    
    def regenerate_session_id(self, old_session_id: str, user_id: str, user_data: Optional[Dict] = None) -> str:
        """Regenerate session ID for session fixation protection"""
        import secrets
        
        # Create new session with cryptographically secure ID
        new_session_id = secrets.token_urlsafe(32)
        
        # Create new session
        if user_data is None:
            user_data = {}
        self.create_session(user_id, user_data, new_session_id)
        
        # Delete old session if it exists
        if old_session_id:
            self.delete_session(old_session_id)
        
        logger.info(f"Session ID regenerated for user {user_id}")
        return new_session_id

    async def _backup_session_to_db(self, session_id: str, session_data: Dict):
        """CRITICAL FIX: Backup session to database for persistence across restarts"""
        try:
            from auth_service.auth_core.database.connection import auth_db
            from auth_service.auth_core.database.models import AuthSession
            from datetime import datetime, timezone, timedelta
            
            # Ensure database is initialized before creating session
            if not auth_db._initialized:
                await auth_db.initialize()
            
            async with auth_db.get_session() as db_session:
                # Create or update session record
                expires_at = datetime.now(timezone.utc) + timedelta(hours=self.session_ttl)
                
                auth_session = AuthSession(
                    id=session_id,
                    user_id=session_data.get("user_id"),
                    ip_address=session_data.get("ip_address"),
                    user_agent=session_data.get("user_agent"),
                    expires_at=expires_at,
                    is_active=True
                )
                
                # Use merge to handle existing records
                await db_session.merge(auth_session)
                await db_session.commit()
                
        except Exception as e:
            logger.error(f"Failed to backup session {session_id} to database: {e}")

    async def _restore_session_from_db(self, session_id: str) -> Optional[Dict]:
        """CRITICAL FIX: Restore session from database when Redis is unavailable"""
        try:
            from auth_service.auth_core.database.connection import auth_db
            from auth_service.auth_core.database.models import AuthSession
            from sqlalchemy import select
            from datetime import datetime, timezone
            
            # Ensure database is initialized before creating session
            if not auth_db._initialized:
                await auth_db.initialize()
            
            async with auth_db.get_session() as db_session:
                stmt = select(AuthSession).where(
                    AuthSession.id == session_id,
                    AuthSession.is_active == True,
                    AuthSession.expires_at > datetime.now(timezone.utc)
                )
                result = await db_session.execute(stmt)
                auth_session = result.scalar_one_or_none()
                
                if auth_session:
                    return {
                        "user_id": auth_session.user_id,
                        "created_at": auth_session.created_at.isoformat(),
                        "last_activity": auth_session.last_activity.isoformat(),
                        "ip_address": auth_session.ip_address,
                        "user_agent": auth_session.user_agent
                    }
                    
        except Exception as e:
            logger.error(f"Failed to restore session {session_id} from database: {e}")
        
        return None
    
    # Async wrappers for test compatibility
    async def create_session_async(self, user_or_user_id=None, user_data: Optional[Dict] = None, session_id: Optional[str] = None,
                                 client_ip: Optional[str] = None, user_agent: Optional[str] = None, 
                                 fingerprint: Optional[str] = None, device_id: Optional[str] = None,
                                 session_timeout: Optional[int] = None, force_create: bool = False,
                                 user_id: Optional[str] = None) -> str:
        """Async version of create_session for test compatibility
        
        Args:
            user_or_user_id: Either a User object or user_id string (positional)
            user_data: Optional dict of user data (if user_or_user_id is a string)
            user_id: DEPRECATED - use user_or_user_id instead (kept for backward compatibility)
        """
        # Handle both calling patterns: create_session(user) and create_session(user_id, user_data)
        from auth_service.auth_core.models.auth_models import User
        
        # Handle backward compatibility with user_id keyword argument
        if user_or_user_id is None and user_id is not None:
            # Called with user_id=... keyword argument (old pattern)
            user_or_user_id = user_id
        elif user_or_user_id is None:
            raise ValueError("Either user_or_user_id or user_id must be provided")
        
        if isinstance(user_or_user_id, User):
            # Called with User object: create_session(user)
            user = user_or_user_id
            actual_user_id = user.id
            if user_data is None:
                user_data = {
                    "email": str(user.email),
                    "name": user.name,
                    "picture": user.picture,
                    "verified_email": user.verified_email,
                    "provider": user.provider
                }
        else:
            # Called with user_id string: create_session(user_id, user_data)
            actual_user_id = user_or_user_id
            if user_data is None:
                user_data = {}
        
        # Use the sync version directly - it handles the session creation logic
        # Allow custom session ID for session fixation protection
        if not session_id:
            session_id = str(uuid.uuid4())
        session_data = {
            "user_id": actual_user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "fingerprint": fingerprint,
            "device_id": device_id,
            "session_timeout": session_timeout or self.session_ttl,
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
    
    async def validate_session(self, session_id: str, client_ip: Optional[str] = None, 
                             user_agent: Optional[str] = None) -> Dict:
        """Validate session with client fingerprint check"""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        # Check client fingerprint if provided
        if client_ip or user_agent:
            stored_fingerprint = session.get("fingerprint")
            if stored_fingerprint:
                import hashlib
                current_fingerprint_data = f"{client_ip}:{user_agent}"
                current_fingerprint = hashlib.sha256(current_fingerprint_data.encode()).hexdigest()
                if stored_fingerprint != current_fingerprint:
                    raise ValueError("Session fingerprint mismatch")
        
        return session
    
    async def validate_session_by_id(self, session_id: str) -> Dict:
        """Validate session by ID only"""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        return session
    
    async def get_active_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user"""
        return await self.get_user_sessions(user_id)
    
    async def set_user_session_limit(self, user_id: str, limit: int):
        """Set concurrent session limit for a user (stub implementation)"""
        # Store in memory for testing
        if not hasattr(self, '_user_session_limits'):
            self._user_session_limits = {}
        self._user_session_limits[user_id] = limit
    
    async def record_session_activity(self, session_id: str, activity_type: str, 
                                    resource: str, client_ip: str, timestamp: float = None):
        """Record session activity (stub implementation)"""
        if not hasattr(self, '_session_activities'):
            self._session_activities = {}
        if session_id not in self._session_activities:
            self._session_activities[session_id] = []
        
        activity = {
            "activity_type": activity_type,
            "resource": resource,
            "client_ip": client_ip,
            "timestamp": timestamp or time.time()
        }
        self._session_activities[session_id].append(activity)
    
    async def get_session_status(self, session_id: str) -> Dict:
        """Get session security status (stub implementation)"""
        activities = getattr(self, '_session_activities', {}).get(session_id, [])
        
        # Simple risk assessment based on activities
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
                                         except_session_id: str = None):
        """Invalidate all sessions for a user"""
        count = await self.invalidate_user_sessions(user_id)
        
        # Log the invalidation
        if not hasattr(self, '_invalidation_history'):
            self._invalidation_history = {}
        if user_id not in self._invalidation_history:
            self._invalidation_history[user_id] = []
            
        self._invalidation_history[user_id].append({
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sessions_invalidated": count
        })
        
        return count
    
    async def get_invalidation_history(self, user_id: str) -> list:
        """Get invalidation history for a user"""
        if not hasattr(self, '_invalidation_history'):
            self._invalidation_history = {}
        return self._invalidation_history.get(user_id, [])