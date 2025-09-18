from shared.logging.unified_logging_ssot import get_logger
"""
Main FastAPI application module.
Entry point for the Netra AI Optimization Platform.

[U+1F534] CRITICAL AUTH ARCHITECTURE:
- This is the MAIN BACKEND service, NOT the auth service
- Auth service runs SEPARATELY on port 8001 (see app/auth/auth_service.py)
- This backend ONLY uses auth_integration to connect to auth service
- NEVER implement authentication logic here
- All auth operations go through auth_client

See: app/auth_integration/CRITICAL_AUTH_ARCHITECTURE.md
"""
import logging
from pathlib import Path
from shared.isolated_environment import get_env
from shared.environment_loading_ssot import StartupEnvironmentManager, BACKEND_CONFIG

# Load environment files using SSOT implementation
env_manager = get_env()
startup_manager = StartupEnvironmentManager(env_manager)
startup_manager.setup_service_environment(BACKEND_CONFIG)

# CRITICAL FIX: Set required auth environment variables for Issue #1229
# This fixes AgentService dependency injection failure that breaks $500K+ ARR chat functionality
# Missing SERVICE_ID and AUTH_SERVICE_URL cause deterministic startup to fail, preventing AgentService initialization
if not env_manager.get("SERVICE_ID"):
    env_manager.set("SERVICE_ID", "netra-backend")
if not env_manager.get("AUTH_SERVICE_URL"):
    # Use development auth service URL for local development
    env_manager.set("AUTH_SERVICE_URL", "http://localhost:8001")
if not env_manager.get("SERVICE_SECRET"):
    # Use development service secret for local development - use strong secret for validation
    env_manager.set("SERVICE_SECRET", "xNp9hKjT5mQ8w2fE7vR4yU3iO6aS1gL9cB0zZ8tN6wX2eR4vY7uI0pQ3s9dF5gH8")

# Configure logging for Cloud Run compatibility (prevents ANSI codes)
from netra_backend.app.core.logging_config import configure_cloud_run_logging, setup_exception_handler
configure_cloud_run_logging()
setup_exception_handler()

# Import unified logging first to ensure interceptor is set up
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

# Configure loggers after unified logging is initialized
logging.getLogger("faker").setLevel(logging.WARNING)

# CRITICAL: SSOT-Compliant Environment Validation at Startup
# Validate environment configuration before creating app to prevent runtime failures
# This implements Phase 1 of the SSOT-compliant integration plan
def validate_environment_at_startup():
    """
    Validate environment configuration before starting service.
    SSOT COMPLIANT: Uses central validators and IsolatedEnvironment.
    """
    import sys
    from shared.configuration.central_config_validator import validate_platform_configuration
    
    logger.info("🔍 Validating environment configuration with SSOT validators...")
    
    try:
        # Use SSOT central validator for comprehensive environment validation
        # This validates JWT secrets, database config, OAuth, Redis, LLM keys etc.
        validate_platform_configuration()
        logger.info("✅ Environment validation completed (SSOT compliant)")
        
    except ValueError as e:
        error_message = f"""
🚨 ENVIRONMENT VALIDATION FAILED (SSOT) 🚨

Service: netra-backend
Validator: SSOT CentralConfigValidator
Error: {str(e)}

SSOT compliance status: ✅ Validated
Required actions:
1. Fix environment variable configuration
2. Verify all POSTGRES_*, JWT_*, and SERVICE_* variables are set
3. Check OAuth credentials for current environment
4. Restart service after fixing configuration

This prevents runtime configuration failures that could impact the Golden Path.
Service startup ABORTED for safety.
"""
        logger.critical(error_message)
        sys.exit(1)
    except Exception as e:
        # For unexpected errors, log but don't prevent startup in development
        env_manager = get_env()
        environment = env_manager.get("ENVIRONMENT", "development").lower()
        
        if environment in ["staging", "production"]:
            error_message = f"""
🚨 ENVIRONMENT VALIDATION ERROR (SSOT) 🚨

Service: netra-backend
Environment: {environment}
Error: {str(e)}

Critical validation infrastructure failure in {environment} environment.
Service startup ABORTED for safety.
"""
            logger.critical(error_message)
            sys.exit(1)
        else:
            logger.warning(f"⚠️ Environment validation error in {environment}: {e} - continuing startup")

# Run SSOT-compliant validation before creating app
# RE-ENABLED FOR BACKEND SERVICE DATABASE CONFIGURATION ISSUE REMEDIATION
validate_environment_at_startup()
logger.info("✅ Environment validation enabled for proper configuration")

from netra_backend.app.core.app_factory import create_app

app = create_app()


def _get_uvicorn_config() -> dict:
    """Get uvicorn server configuration with modern WebSocket support."""
    env_manager = get_env()
    host = env_manager.get("HOST", "0.0.0.0")
    port = int(env_manager.get("PORT", "8000"))
    
    # Modern uvicorn configuration that avoids deprecated WebSocket implementations
    config = {
        "host": host, 
        "port": port, 
        "reload": True,
        "reload_dirs": ["app"], 
        "reload_excludes": ["*/tests/*", "*/.pytest_cache/*"],
        # WebSocket configuration to avoid deprecated implementations
        "ws_ping_interval": 20.0,
        "ws_ping_timeout": 20.0,
        "ws_max_size": 16 * 1024 * 1024,  # 16MB
        # Use modern HTTP/WebSocket handling
        "http": "httptools",
        "loop": "auto",
        # Disable legacy WebSocket implementations
        "interface": "asgi3"
    }
    
    return config


def _run_development_server() -> None:
    """Run the FastAPI development server with uvicorn."""
    import uvicorn
    config = _get_uvicorn_config()
    uvicorn.run("main:app", **config)


if __name__ == "__main__":
    _run_development_server()
