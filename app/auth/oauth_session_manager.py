"""OAuth Session Manager for state and session management.

Handles OAuth state creation, validation, and Redis-based session storage.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Secure OAuth session management
3. Value Impact: Prevents CSRF attacks and manages user sessions
4. Revenue Impact: Critical for secure authentication flows
"""

import json
import time
import uuid
import secrets
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class StateData(BaseModel):
    """OAuth state data model."""
    csrf_token: str
    return_url: str
    timestamp: int
    pr_number: Optional[str] = None

class OAuthSessionManager:
    """Manages OAuth state and session data."""
    
    def __init__(self, session_ttl: int = 300):
        """Initialize session manager."""
        self.session_ttl = session_ttl  # 5 minutes
        
    async def create_oauth_state(
        self, 
        pr_number: Optional[str], 
        return_url: str
    ) -> str:
        """Create OAuth state and store in Redis."""
        csrf_token = self._generate_csrf_token()
        state_data = self._build_state_data(pr_number, return_url, csrf_token)
        state_id = await self._store_state_data(state_data)
        return state_id
        
    def _generate_csrf_token(self) -> str:
        """Generate secure CSRF token."""
        return secrets.token_urlsafe(32)
        
    def _build_state_data(
        self, 
        pr_number: Optional[str], 
        return_url: str, 
        csrf_token: str
    ) -> Dict[str, Any]:
        """Build state data dictionary."""
        data = {
            "csrf_token": csrf_token,
            "return_url": return_url,
            "timestamp": int(time.time())
        }
        if pr_number:
            data["pr_number"] = pr_number
        return data
        
    async def _store_state_data(self, state_data: Dict[str, Any]) -> str:
        """Store state data in Redis."""
        state_id = str(uuid.uuid4())
        key = f"oauth_state:{state_id}"
        data_json = json.dumps(state_data)
        
        from ..services.redis_service import redis_service
        await redis_service.setex(key, self.session_ttl, data_json)
        return state_id
        
    async def validate_and_consume_state(self, state_id: str) -> Dict[str, Any]:
        """Validate and consume OAuth state."""
        key = f"oauth_state:{state_id}"
        
        from ..services.redis_service import redis_service
        stored_data = await redis_service.get(key)
        if not stored_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state"
            )
            
        # Delete the state (consume it)
        await redis_service.delete(key)
        
        # Validate state data
        state_data = json.loads(stored_data)
        return self._validate_state_data(state_data)
        
    def _validate_state_data(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate state data integrity and timing."""
        # Check required fields
        required_fields = ["csrf_token", "return_url", "timestamp"]
        for field in required_fields:
            if field not in state_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
                
        # Check timestamp (prevent replay attacks)
        current_time = int(time.time())
        state_timestamp = state_data["timestamp"]
        if current_time - state_timestamp > self.session_ttl:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State has expired"
            )
            
        return state_data