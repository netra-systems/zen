"""LLM configuration management module.

Handles LLM configuration, validation, and logger setup.
Each function must be ≤8 lines as per architecture requirements.
"""

from typing import Any, Dict

from netra_backend.app.core.exceptions_service import ServiceUnavailableError
from netra_backend.app.llm.observability import get_data_logger, get_heartbeat_logger
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Config import AppConfig

logger = central_logger.get_logger(__name__)


class LLMConfigManager:
    """Manages LLM configuration and validation."""
    
    def __init__(self, settings: AppConfig):
        """Initialize config manager with settings."""
        self.settings = settings
        self.enabled = self._check_if_enabled()
        self._configure_loggers()
    
    def _configure_loggers(self) -> None:
        """Configure both heartbeat and data loggers."""
        self._configure_heartbeat_logger()
        self._configure_data_logger()
    
    def _configure_heartbeat_logger(self) -> None:
        """Configure the heartbeat logger with settings."""
        heartbeat_logger = get_heartbeat_logger()
        heartbeat_logger.interval_seconds = self.settings.llm_heartbeat_interval_seconds
        heartbeat_logger.log_as_json = self.settings.llm_heartbeat_log_json
    
    def _configure_data_logger(self) -> None:
        """Configure the data logger with settings."""
        data_logger = get_data_logger()
        data_logger.truncate_length = self.settings.llm_data_truncate_length
        data_logger.json_depth = self.settings.llm_data_json_depth
        data_logger.log_format = self.settings.llm_data_log_format
    
    def _check_if_enabled(self) -> bool:
        """Check if LLMs should be enabled based on service mode configuration."""
        llm_mode = self.settings.llm_mode.lower()
        if llm_mode in ["disabled", "mock"]:
            logger.info(f"LLMs are disabled (mode: {llm_mode})")
            return False
        return self._check_environment_enabled()
    
    def _check_environment_enabled(self) -> bool:
        """Check environment-specific LLM enablement."""
        if self.settings.environment == "development":
            return self._check_dev_enabled()
        return True
    
    def _check_dev_enabled(self) -> bool:
        """Check if LLMs are enabled in development."""
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
        """Check if mock LLM should be used in development."""
        return self.settings.environment == "development"
    
    def _create_mock_llm(self) -> Any:
        """Create mock LLM for development environment."""
        try:
            from netra_backend.tests.helpers.llm_mocks import MockLLM
            return MockLLM("mock-dev-model")
        except ImportError:
            logger.warning("MockLLM not available - using None")
            return None