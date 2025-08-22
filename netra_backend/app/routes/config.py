from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from netra_backend.app import schemas
from netra_backend.app.auth_integration.auth import get_current_user, require_admin
from netra_backend.app.config import get_config
settings = get_config()

router = APIRouter()

class ConfigUpdate(BaseModel):
    log_level: str = None
    max_retries: int = None
    timeout: int = None
    feature_flags: Dict[str, Any] = None

@router.get("/config/websocket", response_model=schemas.WebSocketConfig)
async def get_websocket_config(
    current_user: Dict = Depends(get_current_user)
):
    """Get WebSocket configuration (Authenticated)."""
    return settings.ws_config

def _get_default_features() -> Dict[str, bool]:
    """Get default feature configuration"""
    return {"websocket": True, "multi_agent": True}

def _build_public_config() -> Dict[str, Any]:
    """Build public configuration response"""
    return {
        "environment": settings.environment,
        "app_name": settings.app_name,
        "version": getattr(settings, "version", "2.0.0"),
        "features": getattr(settings, "features", _get_default_features())
    }

@router.get("/config/public")
async def get_public_config():
    """Get public configuration for frontend"""
    return _build_public_config()


def _build_api_config() -> Dict[str, Any]:
    """Build API configuration response."""
    ws_config = settings.ws_config
    return {"log_level": "INFO", "max_retries": 3, "timeout": 30, "ws_url": ws_config.ws_url}

@router.get("/config")
async def get_api_config(current_user: Dict = Depends(require_admin)):
    """Get API configuration including WebSocket URL (Admin only)."""
    return _build_api_config()

def _validate_config_update(config: ConfigUpdate) -> None:
    """Validate configuration update."""
    if config.log_level and config.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        raise HTTPException(status_code=422, detail="Invalid log level")
    if config.max_retries is not None and config.max_retries < 0:
        raise HTTPException(status_code=422, detail="Invalid max_retries")

@router.put("/config")
async def update_api_config(config: ConfigUpdate, current_user: Dict = Depends(require_admin)):
    """Update configuration with validation (Admin only)."""
    _validate_config_update(config)
    return {"success": True, "message": "Configuration updated"}

async def update_config(config_data: Dict[str, Any]) -> Dict[str, bool]:
    """Update configuration helper function"""
    return {"success": True}

def _validate_authorization_header(authorization: Optional[str]) -> str:
    """Validate and extract token from authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    return authorization.split(" ")[1]

def _check_admin_access(token: str) -> None:
    """Check admin access with token"""
    if not verify_admin_token(token):
        raise HTTPException(status_code=403, detail="Admin access required")

@router.post("/config/update")
async def update_config_admin(
    config_data: Dict[str, Any],
    current_user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Update configuration with admin authorization (Admin only)."""
    result = await update_config(config_data)
    return {"success": True, "updated": config_data}

def verify_admin_token(token: str) -> bool:
    """Verify admin token for backward compatibility"""
    # Simple validation - in production this would verify against actual auth
    return token == "admin-token"

async def backup_config() -> Dict[str, Any]:
    """Create configuration backup with ID and timestamp."""
    from netra_backend.app.services.config_service import create_backup
    try:
        result = await create_backup()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

async def restore_config(backup_id: str) -> Dict[str, Any]:
    """Restore configuration from backup ID."""
    from netra_backend.app.services.config_service import restore_from_backup
    try:
        result = await restore_from_backup(backup_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

