from fastapi import APIRouter, Depends
from app.config import settings
from app import schemas
from typing import Dict, Any

router = APIRouter()

@router.get("/config", response_model=schemas.WebSocketConfig)
async def get_config():
    return settings.ws_config

@router.get("/config/public")
async def get_public_config():
    """Get public configuration for frontend"""
    return {
        "environment": settings.environment,
        "app_name": settings.app_name,
        "version": getattr(settings, "version", "2.0.0"),
        "features": getattr(settings, "features", {
            "websocket": True,
            "multi_agent": True
        })
    }

async def update_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
    """Update configuration for testing."""
    from app.services import config_service
    success = await config_service.save_config(new_config)
    return {"success": success, "config": new_config}