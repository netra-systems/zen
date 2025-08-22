"""LLM configuration management module.

Handles LLM configuration, validation, and logger setup.
Each function must be ≤8 lines as per architecture requirements.
"""

from typing import Any, Dict

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.core.exceptions_service import ServiceUnavailableError
from netra_backend.app.llm.observability import get_data_logger, get_heartbeat_logger
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Config import AppConfig

logger = central_logger.get_logger(__name__)


class LLMConfigManager:
    """Manages LLM configuration and validation.
    
    **CRITICAL**: Now integrated with unified configuration system.
    Uses get_unified_config() as single source of truth for all LLM configuration.
    """
    
    def __init__(self, settings: AppConfig = None):
        """Initialize config manager.
        
        Args:
            settings: Legacy parameter for backward compatibility.
                     If None, uses unified configuration system.
        """
        # Use unified config as primary source, fallback to parameter for compatibility
        self.settings = settings or get_unified_config()
        self.enabled = self._check_if_enabled()
        self._configure_loggers()
    
    def _configure_loggers(self) -> None:
        """Configure both heartbeat and data loggers."""
        self._configure_heartbeat_logger()
        self._configure_data_logger()
    
    def _configure_heartbeat_logger(self) -> None:
        """Configure the heartbeat logger with unified config settings."""
        heartbeat_logger = get_heartbeat_logger()
        # Map unified config fields to logger configuration
        heartbeat_logger.interval_seconds = self.settings.llm_heartbeat_interval_seconds
        heartbeat_logger.log_as_json = self.settings.llm_heartbeat_log_json
    
    def _configure_data_logger(self) -> None:
        """Configure the data logger with unified config settings."""
        data_logger = get_data_logger()
        # Map unified config fields to data logger configuration
        data_logger.truncate_length = self.settings.llm_data_truncate_length
        data_logger.json_depth = self.settings.llm_data_json_depth
        data_logger.log_format = self.settings.llm_data_log_format
    
    def _check_if_enabled(self) -> bool:
        """Check if LLMs should be enabled based on unified config service mode."""
        # Use unified config LLM mode setting
        llm_mode = self.settings.llm_mode.lower()
        if llm_mode in ["disabled", "mock"]:
            logger.info(f"LLMs are disabled (mode: {llm_mode})")
            return False
        return self._check_environment_enabled()
    
    def _check_environment_enabled(self) -> bool:
        """Check environment-specific LLM enablement from unified config."""
        # Use unified config environment detection
        if self.settings.environment == "development":
            return self._check_dev_enabled()
        return True
    
    def _check_dev_enabled(self) -> bool:
        """Check if LLMs are enabled in development via unified config."""
        # Use unified config development LLM setting
        enabled = self.settings.dev_mode_llm_enabled
        if not enabled:
            logger.info("LLMs are disabled in development configuration")
        return enabled
    
    def _raise_llm_unavailable_error(self, name: str) -> None:
        """Raise service unavailable error for disabled LLM."""
        error_msg = f"LLM '{name}' is not available - LLM service is disabled"
        logger.error(error_msg)
        raise ServiceUnavailableError(error_msg)
    
    def _handle_disabled_llm(self, name: str) -> Any:
        """Handle disabled LLM based on environment - dev gets mock, production gets error."""
        if self._should_use_mock_llm():
            return self._create_mock_llm()
        self._raise_llm_unavailable_error(name)
    
    def _should_use_mock_llm(self) -> bool:
        """Check if mock LLM should be used in development via unified config."""
        # Use unified config environment setting
        return self.settings.environment == "development"
    
    def _create_mock_llm(self) -> Any:
        """Create mock LLM for development environment."""
        try:
            from netra_backend.tests.helpers.llm_mocks import MockLLM
            return MockLLM("mock-dev-model")
        except ImportError:
            logger.warning("MockLLM not available - using None")
            return None
    
    def get_llm_config(self, name: str) -> Any:
        """Get LLM configuration for specified name from unified config.
        
        Args:
            name: Name of the LLM configuration (e.g., 'default', 'triage', 'data')
            
        Returns:
            LLM configuration object from unified config
            
        Raises:
            ValueError: If configuration not found
        """
        if not self.settings.llm_configs or name not in self.settings.llm_configs:
            available = list(self.settings.llm_configs.keys()) if self.settings.llm_configs else []
            raise ValueError(f"LLM configuration '{name}' not found. Available: {available}")
        return self.settings.llm_configs[name]
    
    def get_available_configurations(self) -> list:
        """Get list of available LLM configuration names from unified config."""
        return list(self.settings.llm_configs.keys()) if self.settings.llm_configs else []
    
    def is_caching_enabled(self) -> bool:
        """Check if LLM caching is enabled via unified config."""
        return getattr(self.settings, 'llm_cache_enabled', True)
    
    def get_cache_ttl(self) -> int:
        """Get LLM cache TTL from unified config."""
        return getattr(self.settings, 'llm_cache_ttl', 3600)
    
    def reload_configuration(self) -> None:
        """Reload configuration from unified config system.
        
        Useful for hot-reload scenarios in development.
        """
        from netra_backend.app.core.configuration.base import reload_unified_config
        reload_unified_config(force=True)
        
        # Refresh our settings reference
        self.settings = get_unified_config()
        
        # Recalculate enabled status and reconfigure loggers
        self.enabled = self._check_if_enabled()
        self._configure_loggers()
        
        logger.info("LLMConfigManager configuration reloaded from unified config")