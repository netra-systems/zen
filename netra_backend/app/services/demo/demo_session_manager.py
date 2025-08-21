"""Session management for demo service."""

import json
import uuid
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.services.demo.demo_constants import DEMO_SESSION_TTL, MAX_DEMO_SESSIONS

logger = central_logger.get_logger(__name__)

class DemoSessionManager:
    """Manages demo sessions and their lifecycle."""
    
    def __init__(self):
        self.redis = redis_manager
        self.session_prefix = "demo:session:"
        self.active_sessions_key = "demo:active_sessions"
    
    async def create_session(self, user_id: str, config: Dict[str, Any]) -> str:
        """Create a new demo session."""
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(UTC).isoformat(),
            "config": config,
            "status": "active"
        }
        
        # Store session with TTL
        session_key = f"{self.session_prefix}{session_id}"
        await self.redis.setex(
            session_key,
            DEMO_SESSION_TTL,
            json.dumps(session_data)
        )
        
        # Track active sessions
        await self.redis.sadd(self.active_sessions_key, session_id)
        
        # Enforce max sessions limit
        await self._enforce_session_limit()
        
        logger.info(f"Created demo session {session_id} for user {user_id}")
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data."""
        session_key = f"{self.session_prefix}{session_id}"
        data = await self.redis.get(session_key)
        
        if data:
            return json.loads(data)
        return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data."""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session.update(updates)
        session["updated_at"] = datetime.now(UTC).isoformat()
        
        session_key = f"{self.session_prefix}{session_id}"
        await self.redis.setex(
            session_key,
            DEMO_SESSION_TTL,
            json.dumps(session)
        )
        
        return True
    
    async def end_session(self, session_id: str) -> bool:
        """End a demo session."""
        session_key = f"{self.session_prefix}{session_id}"
        
        # Update status before deletion
        session = await self.get_session(session_id)
        if session:
            session["status"] = "completed"
            session["ended_at"] = datetime.now(UTC).isoformat()
            await self.redis.setex(
                session_key,
                300,  # Keep for 5 minutes for final data retrieval
                json.dumps(session)
            )
        
        # Remove from active sessions
        await self.redis.srem(self.active_sessions_key, session_id)
        
        logger.info(f"Ended demo session {session_id}")
        return True
    
    async def _enforce_session_limit(self) -> None:
        """Enforce maximum number of active sessions."""
        active_sessions = await self.redis.smembers(self.active_sessions_key)
        
        if len(active_sessions) > MAX_DEMO_SESSIONS:
            # Get session details to find oldest
            sessions_with_time = []
            for session_id in active_sessions:
                session = await self.get_session(session_id)
                if session:
                    created_at = datetime.fromisoformat(session["created_at"])
                    sessions_with_time.append((session_id, created_at))
            
            # Sort by creation time and remove oldest
            sessions_with_time.sort(key=lambda x: x[1])
            sessions_to_remove = len(sessions_with_time) - MAX_DEMO_SESSIONS
            
            for i in range(sessions_to_remove):
                await self.end_session(sessions_with_time[i][0])
                logger.warning(f"Removed old session {sessions_with_time[i][0]} due to limit")
    
    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return await self.redis.scard(self.active_sessions_key)
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from active set."""
        active_sessions = await self.redis.smembers(self.active_sessions_key)
        removed_count = 0
        
        for session_id in active_sessions:
            if not await self.get_session(session_id):
                await self.redis.srem(self.active_sessions_key, session_id)
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired sessions")
        
        return removed_count