"""OAuth session management for secure state handling.

Manages OAuth sessions and state for security with Redis storage.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

import json
import time
import secrets
from typing import Dict, Any, Optional, TypedDict
from fastapi import HTTPException

from app.logging_config import central_logger
from app.redis_manager import RedisManager

logger = central_logger.get_logger(__name__)
redis_service = RedisManager()


class StateData(TypedDict):
    """OAuth state data structure."""
    csrf_token: str
    return_url: str
    timestamp: int
    pr_number: Optional[str]


class OAuthSessionManager:
    """OAuth-specific session manager for auth service."""
    
    def __init__(self):
        """Initialize OAuth session manager."""
        self.session_ttl = 300  # 5 minutes
        
    async def create_oauth_state(self, pr_number: Optional[str], return_url: str) -> str:
        """Create secure OAuth state parameter."""
        csrf_token = secrets.token_urlsafe(32)
        state_data = self._build_state_data(pr_number, return_url, csrf_token)
        state_id = await self._store_state_data(state_data)
        return state_id
    
    def _build_state_data(self, pr_number: Optional[str], return_url: str, csrf_token: str) -> StateData:
        """Build OAuth state data."""
        state_data = {
            "csrf_token": csrf_token, "return_url": return_url,
            "timestamp": int(time.time())
        }
        if pr_number is not None:
            state_data["pr_number"] = pr_number
        return state_data
    
    async def _store_state_data(self, state_data: StateData) -> str:
        """Store state data in Redis and return state ID."""
        state_id = secrets.token_urlsafe(16)
        key = f"oauth_state:{state_id}"
        await redis_service.setex(key, self.session_ttl, json.dumps(state_data))
        return state_id
    
    async def validate_and_consume_state(self, state_id: str) -> StateData:
        """Validate OAuth state and consume it."""
        state_json = await redis_service.get(f"oauth_state:{state_id}")
        if not state_json:
            raise HTTPException(status_code=400, detail="Invalid or expired state")
        await redis_service.delete(f"oauth_state:{state_id}")
        return self._validate_state_data(json.loads(state_json))
    
    def _validate_state_data(self, state_data: StateData) -> StateData:
        """Validate state data timestamp and structure."""
        current_time = int(time.time())
        if current_time - state_data.get("timestamp", 0) > self.session_ttl:
            raise HTTPException(status_code=400, detail="OAuth state expired")
        return state_data