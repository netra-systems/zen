from fastapi import APIRouter, Depends
from app.config import settings
from app import schemas
from typing import Dict, Any

router = APIRouter()

@router.get("/config", response_model=schemas.WebSocketConfig)
async def get_config():
    return settings.ws_config

async def update_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
    """Update configuration for testing."""
    from app.services import config_service
    success = await config_service.save_config(new_config)
    return {"success": success, "config": new_config}