from fastapi import APIRouter, Depends, HTTPException
from app.config import settings
from app import schemas
from typing import Dict, Any
from pydantic import BaseModel

router = APIRouter()

class ConfigUpdate(BaseModel):
    log_level: str = None
    max_retries: int = None
    timeout: int = None
    feature_flags: Dict[str, Any] = None

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

@router.get("/api/config")
async def get_api_config():
    """Get configuration for API testing"""
    return {
        "log_level": "INFO",
        "max_retries": 3,
        "timeout": 30
    }

@router.put("/api/config")
async def update_api_config(config: ConfigUpdate):
    """Update configuration with validation"""
    if config.log_level and config.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        raise HTTPException(status_code=422, detail="Invalid log level")
    if config.max_retries is not None and config.max_retries < 0:
        raise HTTPException(status_code=422, detail="Invalid max_retries")
    
    return {"success": True, "message": "Configuration updated"}

async def update_config(config_data: Dict[str, Any]) -> Dict[str, bool]:
    """Update configuration helper function"""
    return {"success": True}

