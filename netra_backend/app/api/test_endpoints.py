"""
Test endpoints for development - bypasses authentication
ONLY enabled in development environment
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import logging

from netra_backend.app.api.thread_routes import create_thread_internal
from netra_backend.app.models.schemas import ThreadCreateRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/test", tags=["test"])

# Only enable in development
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

@router.post("/threads")
async def create_test_thread(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a thread for testing without authentication.
    ONLY available in development environment.
    """
    if ENVIRONMENT != "development":
        raise HTTPException(
            status_code=403,
            detail="Test endpoints are only available in development environment"
        )
    
    # Create thread request
    thread_request = ThreadCreateRequest(
        user_prompt=request.get("user_prompt", ""),
        metadata=request.get("metadata", {})
    )
    
    # Use test user ID
    test_user_id = request.get("user_id", "test-user-001")
    
    logger.info(f"Creating test thread for user {test_user_id}")
    
    # Call the internal thread creation function
    try:
        result = await create_thread_internal(
            thread_request,
            user_id=test_user_id,
            bypass_auth=True  # This flag needs to be handled in the thread creation
        )
        return result
    except Exception as e:
        logger.error(f"Error creating test thread: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def test_health():
    """Test endpoint health check."""
    return {
        "status": "healthy",
        "environment": ENVIRONMENT,
        "test_mode": True
    }