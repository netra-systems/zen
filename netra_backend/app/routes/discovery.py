"""
Service discovery endpoints for dynamic port configuration.
"""

import json
from shared.logging.unified_logging_ssot import get_logger
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from netra_backend.app.routes.utils.error_handlers import handle_service_error
from netra_backend.app.core.environment_constants import get_current_environment, Environment

logger = get_logger(__name__)

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


class ServiceInfo(BaseModel):
    """Service information model."""
    port: int
    url: str
    api_url: Optional[str] = None
    ws_url: Optional[str] = None
    timestamp: str
    cors_metadata: Optional[Dict[str, Any]] = None


class ServicesResponse(BaseModel):
    """Response model for services discovery."""
    services: Dict[str, ServiceInfo]
    timestamp: str
    available: bool


def get_service_discovery_dir() -> Path:
    """Get the service discovery directory path."""
    # Look for .service_discovery directory in project root
    current_dir = Path.cwd()
    discovery_dir = current_dir / ".service_discovery"
    
    if not discovery_dir.exists():
        # If not found, create it
        discovery_dir.mkdir(exist_ok=True)
        logger.info(f"Created service discovery directory: {discovery_dir}")
    
    return discovery_dir


def read_service_info(service_file: Path) -> Optional[Dict[str, Any]]:
    """Read service information from a JSON file."""
    try:
        if service_file.exists():
            with open(service_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.warning(f"Failed to read service info from {service_file}: {e}")
        return None


def get_fallback_service_info() -> Dict[str, ServiceInfo]:
    """Get fallback service information when discovery files are not available."""
    from datetime import datetime
    
    timestamp = datetime.now().isoformat()
    environment = get_current_environment()
    
    # Return environment-specific URLs
    if environment == Environment.STAGING.value:
        return {
            "backend": ServiceInfo(
                port=443,  # HTTPS port in staging
                url="https://api.staging.netrasystems.ai",
                api_url="https://api.staging.netrasystems.ai",
                ws_url="wss://api.staging.netrasystems.ai/ws",
                timestamp=timestamp
            ),
            "frontend": ServiceInfo(
                port=443,  # HTTPS port in staging
                url="https://app.staging.netrasystems.ai",
                api_url=None,
                ws_url=None,
                timestamp=timestamp
            ),
            "auth": ServiceInfo(
                port=443,  # HTTPS port in staging
                url="https://auth.staging.netrasystems.ai",
                api_url="https://auth.staging.netrasystems.ai",
                ws_url=None,
                timestamp=timestamp
            )
        }
    elif environment == Environment.PRODUCTION.value:
        return {
            "backend": ServiceInfo(
                port=443,  # HTTPS port in production
                url="https://api.netrasystems.ai",
                api_url="https://api.netrasystems.ai",
                ws_url="wss://api.netrasystems.ai/ws",
                timestamp=timestamp
            ),
            "frontend": ServiceInfo(
                port=443,  # HTTPS port in production
                url="https://app.netrasystems.ai",
                api_url=None,
                ws_url=None,
                timestamp=timestamp
            ),
            "auth": ServiceInfo(
                port=443,  # HTTPS port in production
                url="https://auth.netrasystems.ai",
                api_url="https://auth.netrasystems.ai",
                ws_url=None,
                timestamp=timestamp
            )
        }
    else:
        # Development/Testing environment - return localhost
        return {
            "backend": ServiceInfo(
                port=8000,
                url="http://localhost:8000",
                api_url="http://localhost:8000",
                ws_url="ws://localhost:8000/ws",
                timestamp=timestamp
            ),
            "frontend": ServiceInfo(
                port=3000,
                url="http://localhost:3000",
                api_url=None,
                ws_url=None,
                timestamp=timestamp
            ),
            "auth": ServiceInfo(
                port=8081,
                url="http://localhost:8081",
                api_url="http://localhost:8081",
                ws_url=None,
                timestamp=timestamp
            )
        }


@router.get("/services", response_model=ServicesResponse)
async def get_services():
    """
    Get current service port mappings and URLs.
    
    Reads service discovery JSON files from .service_discovery/ directory
    and returns current port mappings for all services.
    """
    try:
        discovery_dir = get_service_discovery_dir()
        services = {}
        found_any = False
        
        # Check for service files
        service_files = {
            "backend": discovery_dir / "backend.json",
            "frontend": discovery_dir / "frontend.json", 
            "auth": discovery_dir / "auth.json"
        }
        
        for service_name, service_file in service_files.items():
            service_data = read_service_info(service_file)
            if service_data:
                found_any = True
                
                # Normalize the service data into ServiceInfo format
                services[service_name] = ServiceInfo(
                    port=service_data.get("port", 8000 if service_name == "backend" else 3000),
                    url=service_data.get("url", service_data.get("api_url", f"http://localhost:{service_data.get('port', 8000)}")),
                    api_url=service_data.get("api_url"),
                    ws_url=service_data.get("ws_url"),
                    timestamp=service_data.get("timestamp", ""),
                    cors_metadata=service_data.get("cors_metadata")
                )
                
                logger.debug(f"Loaded {service_name} service info: port={services[service_name].port}")
        
        # If no services found, return fallback configuration
        if not found_any:
            logger.info("No service discovery files found, returning fallback configuration")
            services = get_fallback_service_info()
        
        from datetime import datetime
        return ServicesResponse(
            services=services,
            timestamp=datetime.now().isoformat(),
            available=found_any
        )
        
    except Exception as e:
        logger.error(f"Failed to get service discovery information: {e}")
        raise handle_service_error(e, "Service discovery failed")


@router.get("/services/{service_name}", response_model=ServiceInfo)
async def get_service_info(service_name: str):
    """
    Get specific service information.
    
    Args:
        service_name: Name of the service (backend, frontend, auth)
    """
    try:
        discovery_dir = get_service_discovery_dir()
        service_file = discovery_dir / f"{service_name.lower()}.json"
        
        service_data = read_service_info(service_file)
        
        if not service_data:
            # Return fallback for known services
            fallback_services = get_fallback_service_info()
            if service_name.lower() in fallback_services:
                logger.info(f"Service {service_name} not found in discovery, returning fallback")
                return fallback_services[service_name.lower()]
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Service '{service_name}' not found in discovery"
                )
        
        return ServiceInfo(
            port=service_data.get("port", 8000),
            url=service_data.get("url", service_data.get("api_url", f"http://localhost:{service_data.get('port', 8000)}")),
            api_url=service_data.get("api_url"),
            ws_url=service_data.get("ws_url"),
            timestamp=service_data.get("timestamp", ""),
            cors_metadata=service_data.get("cors_metadata")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get service info for {service_name}: {e}")
        raise handle_service_error(e, f"Failed to get {service_name} service info")


@router.get("/health")
@router.head("/health")
@router.options("/health")
async def discovery_health():
    """Health check for discovery service."""
    discovery_dir = get_service_discovery_dir()
    
    return {
        "status": "healthy",
        "discovery_dir_exists": discovery_dir.exists(),
        "discovery_dir": str(discovery_dir),
        "available_services": [
            f.stem for f in discovery_dir.glob("*.json")
        ] if discovery_dir.exists() else []
    }