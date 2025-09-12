"""LLM management utilities module.

Provides health checking, statistics, and configuration information utilities.
Each function must be  <= 8 lines as per architecture requirements.
"""
import time
from datetime import UTC, datetime
from typing import Any, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.llm.schemas import (
    LLMConfigInfo,
    LLMHealthCheck,
    LLMManagerStats,
    LLMProvider,
)
from netra_backend.app.schemas.config import LLMConfig as GenerationConfig

logger = central_logger.get_logger(__name__)


class LLMManagementUtilities:
    """Management utilities for LLM operations."""
    
    def __init__(self, core_operations) -> None:
        self.core = core_operations
    
    def get_config_info(self, name: str) -> Optional[LLMConfigInfo]:
        """Get information about an LLM configuration."""
        config = self.core.settings.llm_configs.get(name)
        if not config:
            return None
        return self._build_config_info(name, config)
    
    def _build_config_info(self, name: str, config: Any) -> LLMConfigInfo:
        """Build LLMConfigInfo from configuration."""
        return LLMConfigInfo(
            name=name,
            provider=config.provider,  # Use string directly, not enum
            model_name=config.model_name,
            api_key_configured=bool(config.api_key),
            generation_config=config.generation_config,
            enabled=self._determine_config_enabled(config)
        )
    
    def _determine_config_enabled(self, config: Any) -> bool:
        """Determine if configuration is enabled based on provider requirements."""
        return bool(config.api_key) if config.provider == "google" else True
    
    def _create_stats_object(self, active_configs: list) -> LLMManagerStats:
        """Create LLMManagerStats object with current values."""
        return LLMManagerStats(
            total_requests=0,  # Would need to implement request tracking
            cached_responses=0,  # Would need to implement cache tracking
            cache_hit_rate=0.0,
            average_response_time_ms=0.0,
            active_configs=active_configs,
            enabled=self.core.enabled
        )
    
    def get_manager_stats(self) -> LLMManagerStats:
        """Get LLM manager statistics."""
        active_configs = self._get_active_configs()
        return self._create_stats_object(active_configs)
    
    def _get_active_configs(self) -> list:
        """Get list of active configuration names."""
        return [name for name, config in self.core.settings.llm_configs.items() 
                if config.api_key or config.provider != "google"]
    
    async def health_check(self, config_name: str) -> LLMHealthCheck:
        """Perform health check on an LLM configuration."""
        start_time = time.time()
        try:
            return await self._execute_health_test(config_name, start_time)
        except Exception as e:
            return self._handle_health_check_error(config_name, start_time, e)
    
    async def _execute_health_test(self, config_name: str, start_time: float) -> LLMHealthCheck:
        """Execute health test and create result."""
        test_response = await self.core.ask_llm("Hello", config_name, use_cache=False)
        response_time_ms = (time.time() - start_time) * 1000
        return self._create_healthy_check_result(config_name, test_response, response_time_ms)
    
    def _handle_health_check_error(self, config_name: str, start_time: float, error: Exception) -> LLMHealthCheck:
        """Handle health check error and create result."""
        response_time_ms = (time.time() - start_time) * 1000
        return self._create_unhealthy_check_result(config_name, response_time_ms, str(error))
    
    def _create_healthy_check_result(self, config_name: str, test_response: Any, response_time_ms: float) -> LLMHealthCheck:
        """Create healthy health check result."""
        return LLMHealthCheck(
            config_name=config_name,
            healthy=bool(test_response),
            response_time_ms=response_time_ms,
            last_checked=datetime.now(UTC)
        )
    
    def _create_unhealthy_check_result(self, config_name: str, response_time_ms: float, error: str) -> LLMHealthCheck:
        """Create unhealthy health check result."""
        return LLMHealthCheck(
            config_name=config_name,
            healthy=False,
            response_time_ms=response_time_ms,
            error=error,
            last_checked=datetime.now(UTC)
        )