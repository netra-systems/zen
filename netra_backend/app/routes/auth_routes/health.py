"""
Auth service health check endpoint.
"""
from fastapi import APIRouter

from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.logging_config import central_logger

router = APIRouter()
logger = central_logger.get_logger(__name__)


def _create_base_health_status(oauth_config, environment) -> dict:
    """Create base health status indicators."""
    return {
        "status": "healthy", "environment": environment.value,
        "oauth_configured": bool(oauth_config.client_id), "auth_service_enabled": auth_client.enabled,
        "auth_service_url": auth_client.base_url
    }

async def _make_health_request() -> tuple[bool, str | None]:
    """Make health check request to auth service."""
    try:
        client = await auth_client._get_client()
        response = await client.get("/health", timeout=5.0)
        return response.status_code == 200, None
    except Exception as e:
        logger.warning(f"Auth service not reachable: {e}")
        return False, str(e)

async def _perform_auth_service_check() -> tuple[bool, str | None]:
    """Perform auth service reachability check."""
    if not auth_client.enabled:
        return True, None
    return await _make_health_request()

async def _check_auth_service_reachability(health_status: dict) -> None:
    """Check if auth service is reachable and update health status."""
    reachable, error = await _perform_auth_service_check()
    health_status["auth_service_reachable"] = reachable
    if error:
        health_status["auth_service_error"] = error

async def _build_health_status() -> dict:
    """Build complete health status."""
    oauth_config = auth_client.get_oauth_config()
    environment = auth_client.detect_environment()
    health_status = _create_base_health_status(oauth_config, environment)
    await _check_auth_service_reachability(health_status)
    return health_status

@router.get("/health")
@router.head("/health")
@router.options("/health")
async def auth_health():
    """Check auth service health and configuration."""
    try:
        return await _build_health_status()
    except Exception as e:
        logger.error(f"Auth health check failed: {e}", exc_info=True)
        return {"status": "unhealthy", "error": str(e)}


def _build_validation_dict(oauth_config, environment) -> dict:
    """Build validation results dictionary."""
    return {
        "environment": environment.value, "client_id_configured": bool(oauth_config.client_id),
        "client_secret_configured": bool(oauth_config.client_secret),
        "redirect_uris_configured": len(oauth_config.redirect_uris) > 0,
        "javascript_origins_configured": len(oauth_config.javascript_origins) > 0,
        "dev_login_allowed": oauth_config.allow_dev_login, "mock_auth_allowed": oauth_config.allow_mock_auth
    }

def _create_validation_results(oauth_config, environment) -> dict:
    """Create validation results for OAuth configuration."""
    return _build_validation_dict(oauth_config, environment)

def _check_client_config(oauth_config, missing_config: list) -> None:
    """Check client ID and secret configuration."""
    if not oauth_config.client_id:
        missing_config.append("google_client_id")
    if not oauth_config.client_secret:
        missing_config.append("google_client_secret")

def _check_missing_config(oauth_config, environment) -> list:
    """Check for missing critical configuration items."""
    missing_config = []
    _check_client_config(oauth_config, missing_config)
    if not oauth_config.redirect_uris:
        missing_config.append("redirect_uris")
    return missing_config

def _build_validation_response(oauth_config, environment) -> dict:
    """Build complete validation response."""
    validation_results = _create_validation_results(oauth_config, environment)
    missing_config = _check_missing_config(oauth_config, environment)
    validation_results["is_valid"] = len(missing_config) == 0
    validation_results["missing_config"] = missing_config
    return validation_results

def _perform_config_validation() -> dict:
    """Perform OAuth configuration validation."""
    oauth_config = auth_client.get_oauth_config()
    environment = auth_client.detect_environment()
    return _build_validation_response(oauth_config, environment)

@router.get("/config/validate")
async def validate_auth_config():
    """Validate auth configuration completeness."""
    try:
        return _perform_config_validation()
    except Exception as e:
        logger.error(f"Auth config validation failed: {e}", exc_info=True)
        return {"is_valid": False, "error": str(e)}