"""
Basic Auth Routes for Auth Service
Minimal implementation to get the service running
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
from datetime import datetime, UTC

# Create router instances
router = APIRouter()
oauth_router = APIRouter()

# Mock auth service for now
class MockAuthService:
    """Mock auth service implementation"""
    
    class SessionManager:
        def __init__(self):
            self.redis_enabled = False
    
    def __init__(self):
        self.session_manager = self.SessionManager()

# Global auth service instance
auth_service = MockAuthService()

@router.get("/auth/status")
async def auth_status() -> Dict[str, Any]:
    """Basic auth service status endpoint"""
    return {
        "service": "auth-service",
        "status": "running",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0"
    }

@oauth_router.get("/oauth/providers")
async def oauth_providers() -> Dict[str, Any]:
    """Basic OAuth providers endpoint"""
    return {
        "providers": ["google"],
        "status": "configured",
        "timestamp": datetime.now(UTC).isoformat()
    }