"""Environment detection and configuration creation.

Focused module for environment detection logic only.
Separated from the main configuration for clarity.

**DEPRECATION NOTICE**: This module should be migrated to use the
unified configuration system instead of direct os.environ access.
For new code, use: from netra_backend.app.core.configuration import unified_config_manager
"""

import os
from typing import Dict, Type
from netra_backend.app.schemas.config import AppConfig, DevelopmentConfig, ProductionConfig, StagingConfig, NetraTestingConfig
from netra_backend.app.logging_config import central_logger as logger

# MIGRATION NOTE: For new code, use the unified configuration system:
# from netra_backend.app.core.configuration import unified_config_manager
# config = unified_config_manager.get_config()
# This provides centralized, validated configuration access.


def detect_cloud_run_environment() -> str:
    """Detect if running in Cloud Run and determine environment."""
    env = _check_k_service_for_staging()
    if env:
        return env
    return _check_pr_number_for_staging()


def _check_k_service_for_staging() -> str:
    """Check K_SERVICE environment variable for staging.
    
    DEPRECATION: Consider using unified configuration system instead.
    """
    # LEGACY: Direct env access - should migrate to unified config
    k_service = os.environ.get("K_SERVICE")
    if k_service and "staging" in k_service.lower():
        logger.debug(f"Staging from K_SERVICE: {k_service}")
        return "staging"
    return ""


def _check_pr_number_for_staging() -> str:
    """Check PR_NUMBER environment variable for staging.
    
    DEPRECATION: Consider using unified configuration system instead.
    """
    # LEGACY: Direct env access - should migrate to unified config
    if os.environ.get("PR_NUMBER"):
        logger.debug(f"Staging from PR_NUMBER")
        return "staging"
    return ""


def get_environment() -> str:
    """Determine the current environment.
    
    DEPRECATION: Consider using unified configuration system instead.
    """
    # LEGACY: Direct env access - should migrate to unified config
    if os.environ.get("TESTING"):
        return "testing"
    cloud_env = detect_cloud_run_environment()
    if cloud_env:
        return cloud_env
    return _get_default_environment()


def _get_default_environment() -> str:
    """Get default environment from env vars.
    
    DEPRECATION: Consider using unified configuration system instead.
    """
    # LEGACY: Direct env access - should migrate to unified config
    env = os.environ.get("ENVIRONMENT", "development").lower()
    logger.debug(f"Environment determined as: {env}")
    return env


def create_base_config(environment: str) -> AppConfig:
    """Create the base configuration object for the environment."""
    config_classes = _get_config_classes()
    return _init_config(config_classes, environment)


def _get_config_classes() -> Dict[str, Type]:
    """Get configuration classes mapping."""
    return {
        "production": ProductionConfig,
        "staging": StagingConfig,
        "testing": NetraTestingConfig,
        "development": DevelopmentConfig
    }


def _init_config(config_classes: dict, env: str) -> AppConfig:
    """Initialize config with appropriate class."""
    config_class = config_classes.get(env, DevelopmentConfig)
    config = config_class()
    _update_websocket_url(config)
    return config


def _update_websocket_url(config: AppConfig) -> None:
    """Update WebSocket URL if server port is set.
    
    DEPRECATION: Consider using unified configuration system instead.
    """
    # LEGACY: Direct env access - should migrate to unified config
    server_port = os.environ.get('SERVER_PORT')
    if server_port:
        config.ws_config.ws_url = f"ws://localhost:{server_port}/ws"
        logger.info(f"Updated WebSocket URL to port {server_port}")