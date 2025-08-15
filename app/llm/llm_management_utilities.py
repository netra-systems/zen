"""LLM management utilities module.

Provides health checking, statistics, and configuration information utilities.
Each function must be ≤8 lines as per architecture requirements.
"""
from typing import Optional
from datetime import datetime
from app.schemas.llm_base_types import (
    LLMConfigInfo, LLMManagerStats, LLMHealthCheck, LLMProvider
)
from app.schemas.llm_config_types import LLMConfig as GenerationConfig
from app.logging_config import central_logger
import time

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
        
        return LLMConfigInfo(
            name=name,
            provider=LLMProvider(config.provider),
            model_name=config.model_name,
            api_key_configured=bool(config.api_key),
            generation_config=GenerationConfig(**config.generation_config),
            enabled=bool(config.api_key) if config.provider == "google" else True
        )
    
    def get_manager_stats(self) -> LLMManagerStats:
        """Get LLM manager statistics."""
        active_configs = [name for name, config in self.core.settings.llm_configs.items() 
                         if config.api_key or config.provider != "google"]
        
        return LLMManagerStats(
            total_requests=0,  # Would need to implement request tracking
            cached_responses=0,  # Would need to implement cache tracking
            cache_hit_rate=0.0,
            average_response_time_ms=0.0,
            active_configs=active_configs,
            enabled=self.core.enabled
        )
    
    async def health_check(self, config_name: str) -> LLMHealthCheck:
        """Perform health check on an LLM configuration."""
        start_time = time.time()
        try:
            # Simple test prompt
            test_response = await self.core.ask_llm("Hello", config_name, use_cache=False)
            response_time_ms = (time.time() - start_time) * 1000
            
            return LLMHealthCheck(
                config_name=config_name,
                healthy=bool(test_response),
                response_time_ms=response_time_ms,
                last_checked=datetime.utcnow()
            )
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return LLMHealthCheck(
                config_name=config_name,
                healthy=False,
                response_time_ms=response_time_ms,
                error=str(e),
                last_checked=datetime.utcnow()
            )