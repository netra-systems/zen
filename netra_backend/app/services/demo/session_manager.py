"""Session management for demo service."""

import json
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)

class SessionManager:
    """Manages demo sessions and their lifecycle."""
    
    def __init__(self):
        self.redis_client = None
        
    async def _get_redis(self):
        """Get Redis client lazily."""
        if not self.redis_client:
            self.redis_client = await redis_manager.get_client()
        return self.redis_client
        
    async def create_session(self, session_id: str, industry: str, 
                            user_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new demo session."""
        redis = await self._get_redis()
        session_key = f"demo:session:{session_id}"
        session_data = {
            "industry": industry,
            "user_id": user_id,
            "started_at": datetime.now(UTC).isoformat(),
            "messages": []
        }
        await redis.setex(session_key, 3600 * 24, json.dumps(session_data))
        return session_data
        
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get existing session data."""
        redis = await self._get_redis()
        session_key = f"demo:session:{session_id}"
        existing = await redis.get(session_key)
        return json.loads(existing) if existing else None
        
    async def update_session(self, session_id: str, 
                            session_data: Dict[str, Any]) -> None:
        """Update session data."""
        redis = await self._get_redis()
        session_key = f"demo:session:{session_id}"
        await redis.setex(session_key, 3600 * 24, json.dumps(session_data))
        
    async def add_message(self, session_id: str, role: str, 
                         content: str, **metadata) -> Dict[str, Any]:
        """Add a message to the session."""
        session_data = await self.get_session(session_id)
        if not session_data:
            raise ValueError(f"Session not found: {session_id}")
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
            **metadata
        }
        session_data["messages"].append(message)
        await self.update_session(session_id, session_data)
        return message
        
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the status of a demo session."""
        try:
            session_data = await self.get_session(session_id)
            if not session_data:
                raise ValueError(f"Session not found: {session_id}")
            message_count = len(session_data.get("messages", []))
            expected_steps = 6
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
        except Exception as e:
            logger.error(f"Session status error: {str(e)}")
            raise