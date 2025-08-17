"""
Auth service health check endpoint.
"""
from fastapi import APIRouter
from app.clients.auth_client import auth_client
from app.logging_config import central_logger

router = APIRouter()
logger = central_logger.get_logger(__name__)


@router.get("/health")
async def auth_health():
    """Check auth service health and configuration."""
    try:
        # Check OAuth configuration
        oauth_config = auth_client.get_oauth_config()
        
        # Check environment detection
        environment = auth_client.detect_environment()
        
        # Basic health indicators
        health_status = {
            "status": "healthy",
            "environment": environment.value,
            "oauth_configured": bool(oauth_config.client_id),
            "auth_service_enabled": auth_client.enabled,
            "auth_service_url": auth_client.base_url
        }
        
        # Check if auth service is reachable (if enabled)
        if auth_client.enabled:
            try:
                client = await auth_client._get_client()
                # Try a simple connectivity test
                response = await client.get("/health", timeout=5.0)
                health_status["auth_service_reachable"] = response.status_code == 200
            except Exception as e:
                logger.warning(f"Auth service not reachable: {e}")
                health_status["auth_service_reachable"] = False
                health_status["auth_service_error"] = str(e)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Auth health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/config/validate")
async def validate_auth_config():
    """Validate auth configuration completeness."""
    try:
        oauth_config = auth_client.get_oauth_config()
        environment = auth_client.detect_environment()
        
        validation_results = {
            "environment": environment.value,
            "client_id_configured": bool(oauth_config.client_id),
            "client_secret_configured": bool(oauth_config.client_secret),
            "redirect_uris_configured": len(oauth_config.redirect_uris) > 0,
            "javascript_origins_configured": len(oauth_config.javascript_origins) > 0,
            "dev_login_allowed": oauth_config.allow_dev_login,
            "mock_auth_allowed": oauth_config.allow_mock_auth
        }
        
        # Check for missing critical configuration
        missing_config = []
        if not oauth_config.client_id:
            missing_config.append("google_client_id")
        if not oauth_config.client_secret and environment in ["staging", "production"]:
            missing_config.append("google_client_secret")
        if not oauth_config.redirect_uris:
            missing_config.append("redirect_uris")
        
        validation_results["is_valid"] = len(missing_config) == 0
        validation_results["missing_config"] = missing_config
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Auth config validation failed: {e}", exc_info=True)
        return {
            "is_valid": False,
            "error": str(e)
        }