"""Configuration Environment Detection Module

Handles environment detection, config creation, and basic setup.

DEPRECATED: This module is deprecated. Use app.core.configuration instead.
Will be removed in v2.0. Migration guide: /docs/configuration-migration.md
"""

import os
from typing import Dict, Type
from app.schemas.Config import AppConfig, DevelopmentConfig, ProductionConfig, StagingConfig, NetraTestingConfig
from app.config_loader import detect_cloud_run_environment
from app.logging_config import central_logger as logger
from app.core.environment_constants import (
    Environment, EnvironmentVariables, get_current_environment
)


class ConfigEnvironment:
    """Handles environment detection and config creation"""
    
    def __init__(self):
        self._logger = logger
    
    def get_environment(self) -> str:
        """Determine the current environment."""
        if os.environ.get(EnvironmentVariables.TESTING):
            return Environment.TESTING.value
        cloud_env = detect_cloud_run_environment()
        if cloud_env:
            return cloud_env
        return self._get_default_environment()
        
    def _get_default_environment(self) -> str:
        """Get default environment from env vars."""
        env = get_current_environment()
        self._logger.debug(f"Environment determined as: {env}")
        return env
    
    def create_base_config(self, environment: str) -> AppConfig:
        """Create the base configuration object for the environment."""
        config_classes = self._get_config_classes()
        return self._init_config(config_classes, environment)
        
    def _get_config_classes(self) -> Dict[str, Type]:
        """Get configuration classes mapping."""
        return {
            Environment.PRODUCTION.value: ProductionConfig,
            Environment.STAGING.value: StagingConfig,
            Environment.TESTING.value: NetraTestingConfig,
            Environment.DEVELOPMENT.value: DevelopmentConfig
        }
    
    def _init_config(self, config_classes: dict, env: str) -> AppConfig:
        """Initialize config with appropriate class."""
        config_class = config_classes.get(env, DevelopmentConfig)
        config = config_class()
        self._update_websocket_url(config)
        return config
    
    def _update_websocket_url(self, config: AppConfig) -> None:
        """Update WebSocket URL if server port is set."""
        server_port = os.environ.get('SERVER_PORT')
        if server_port:
            config.ws_config.ws_url = f"ws://localhost:{server_port}/ws"
            self._logger.info(f"Updated WebSocket URL to port {server_port}")