"""
OAuth Validation Logic
"""
import urllib.parse
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.core.configuration import unified_config_manager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.routes.auth_routes.utils import get_frontend_url_for_environment

logger = central_logger.get_logger(__name__)


def validate_oauth_credentials(oauth_config) -> Optional[RedirectResponse]:
    """
    DEPRECATED: Validate OAuth credentials are configured.
    
    This function now delegates to SSOT OAuth validation.
    Use shared.configuration.central_config_validator.validate_oauth_credentials_endpoint() instead.
    """
    try:
        # SSOT OAuth validation - this replaces duplicate implementation
        from shared.configuration.central_config_validator import validate_oauth_credentials_endpoint
        
        # Convert oauth_config to dict format for SSOT validation
        credentials = {
            "client_id": getattr(oauth_config, 'client_id', None),
            "client_secret": getattr(oauth_config, 'client_secret', None)
        }
        
        # Use SSOT OAuth credential validation
        validation_result = validate_oauth_credentials_endpoint(credentials)
        
        if not validation_result["valid"]:
            logger.error(f"SSOT OAuth validation failed: {'; '.join(validation_result['errors'])}")
            frontend_url = get_frontend_url_for_environment()
            error_msg = "OAuth not configured. Check server logs."
            return RedirectResponse(url=f"{frontend_url}/auth/error?message={error_msg}")
        
        return None
        
    except ImportError:
        # Fallback if SSOT not available
        logger.warning("SSOT OAuth validation not available - using deprecated implementation")
        if not oauth_config.client_id or not oauth_config.client_secret:
            logger.error("OAuth credentials not configured!")
            frontend_url = get_frontend_url_for_environment()
            error_msg = "OAuth not configured. Check server logs."
            return RedirectResponse(url=f"{frontend_url}/auth/error?message={error_msg}")
        return None


def build_proxy_url(oauth_config, request: Request) -> str:
    """Build proxy URL for PR environment OAuth."""
    config = unified_config_manager.get_config()
    pr_number = getattr(config, 'pr_number', None)
    return_url = str(request.base_url).rstrip('/')
    proxy_url = f"{oauth_config.proxy_url}/initiate?pr_number={pr_number}&return_url={urllib.parse.quote(return_url)}"
    logger.info(f"PR #{pr_number} OAuth login via proxy: {proxy_url}")
    return proxy_url


def handle_pr_proxy_redirect(oauth_config, request: Request) -> Optional[RedirectResponse]:
    """Handle PR environment proxy redirects."""
    if oauth_config.use_proxy and oauth_config.proxy_url:
        proxy_url = build_proxy_url(oauth_config, request)
        return RedirectResponse(url=proxy_url)
    return None


def build_redirect_uri(request: Request) -> str:
    """Build redirect URI based on request and environment."""
    base_url = str(request.base_url).rstrip('/')
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return f"{base_url}/auth/callback"
    base_url = ensure_https_for_production(base_url)
    return f"{base_url}/auth/callback"


def ensure_https_for_production(base_url: str) -> str:
    """Ensure HTTPS for production environments."""
    if auth_client.detect_environment().value in ["staging", "production"]:
        base_url = base_url.replace("http://", "https://")
    return base_url


def validate_redirect_uri(redirect_uri: str, oauth_config) -> Optional[RedirectResponse]:
    """Validate redirect URI against allowed list."""
    if redirect_uri not in oauth_config.redirect_uris:
        logger.error(f"Redirect URI not in allowed list: {redirect_uri}")
        logger.error(f"Allowed URIs: {oauth_config.redirect_uris}")
        frontend_url = get_frontend_url_for_environment()
        return RedirectResponse(url=f"{frontend_url}/auth/error?message=redirect_uri_mismatch")
    return None


def log_oauth_initiation(oauth_config, redirect_uri: str) -> None:
    """Log OAuth login initiation for security auditing."""
    logger.info(f"OAuth login initiated")
    logger.info(f"Environment: {auth_client.detect_environment().value}")
    logger.info(f"Redirect URI: {redirect_uri}")
    logger.info(f"Client ID: {oauth_config.client_id[:20]}...")
    logger.info(f"Session configured: same_site=lax for localhost")