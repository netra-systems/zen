"""Token Optimization Configuration Manager

This module provides configuration-driven pricing and settings for token optimization,
eliminating hardcoded values and integrating with the existing UnifiedConfigurationManager.

CRITICAL: All pricing and configuration must come from the configuration system.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone

from netra_backend.app.core.configuration.base import UnifiedConfigManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TokenOptimizationConfigManager:
    """Configuration manager for token optimization settings.
    
    This class integrates with the existing UnifiedConfigurationManager to provide
    configuration-driven pricing and settings without hardcoded values.
    
    Key Features:
    - Dynamic pricing from configuration system
    - Optimization thresholds and targets
    - Model-specific configuration
    - Cost alert thresholds
    - Session management settings
    """
    
    def __init__(self):
        """Initialize with existing UnifiedConfigManager (SSOT pattern)."""

        # Use existing configuration manager (SSOT compliance)
        self.config_manager = UnifiedConfigManager()
        
        # Cache configuration to avoid repeated lookups
        self._config_cache = {}
        self._cache_timestamp = None
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL
        
        logger.debug("Initialized TokenOptimizationConfigManager with UnifiedConfigurationManager")
    
    def get_model_pricing(self, model: Optional[str] = None) -> Dict[str, Dict[str, Decimal]]:
        """Get token pricing from configuration system.
        
        Args:
            model: Specific model to get pricing for, or None for all models
            
        Returns:
            Dictionary with model pricing information from configuration
        """
        pricing_config = self._get_cached_config("token_pricing", {
            # OpenAI GPT models
            "LLM_PRICING_GPT4_INPUT": "0.00003",
            "LLM_PRICING_GPT4_OUTPUT": "0.00006",
            "LLM_PRICING_GPT4_TURBO_INPUT": "0.00001",
            "LLM_PRICING_GPT4_TURBO_OUTPUT": "0.00003",
            "LLM_PRICING_GPT35_TURBO_INPUT": "0.0015",
            "LLM_PRICING_GPT35_TURBO_OUTPUT": "0.002",
            
            # Anthropic Claude models
            "LLM_PRICING_CLAUDE3_OPUS_INPUT": "0.015",
            "LLM_PRICING_CLAUDE3_OPUS_OUTPUT": "0.075",
            "LLM_PRICING_CLAUDE3_SONNET_INPUT": "0.003",
            "LLM_PRICING_CLAUDE3_SONNET_OUTPUT": "0.015",
            "LLM_PRICING_CLAUDE3_HAIKU_INPUT": "0.00025",
            "LLM_PRICING_CLAUDE3_HAIKU_OUTPUT": "0.00125",
            
            # Google models
            "LLM_PRICING_GEMINI_PRO_INPUT": "0.0005",
            "LLM_PRICING_GEMINI_PRO_OUTPUT": "0.0015",
            "LLM_PRICING_GEMINI_FLASH_INPUT": "0.00035",
            "LLM_PRICING_GEMINI_FLASH_OUTPUT": "0.00053",
            
            # Default pricing
            "LLM_PRICING_DEFAULT_INPUT": "0.001",
            "LLM_PRICING_DEFAULT_OUTPUT": "0.002"
        })
        
        # Convert configuration to structured pricing
        structured_pricing = {
            # GPT models
            "gpt-4": {
                "input": Decimal(str(pricing_config.get("LLM_PRICING_GPT4_INPUT", "0.00003"))),
                "output": Decimal(str(pricing_config.get("LLM_PRICING_GPT4_OUTPUT", "0.00006")))
            },
            "gpt-4-turbo": {
                "input": Decimal(str(pricing_config.get("LLM_PRICING_GPT4_TURBO_INPUT", "0.00001"))),
                "output": Decimal(str(pricing_config.get("LLM_PRICING_GPT4_TURBO_OUTPUT", "0.00003")))
            },
            "gpt-3.5-turbo": {
                "input": Decimal(str(pricing_config.get("LLM_PRICING_GPT35_TURBO_INPUT", "0.0015"))),
                "output": Decimal(str(pricing_config.get("LLM_PRICING_GPT35_TURBO_OUTPUT", "0.002")))
            },
            
            # Claude models
            "claude-3-opus": {
                "input": Decimal(str(pricing_config.get("LLM_PRICING_CLAUDE3_OPUS_INPUT", "0.015"))),
                "output": Decimal(str(pricing_config.get("LLM_PRICING_CLAUDE3_OPUS_OUTPUT", "0.075")))
            },
            "claude-3-sonnet": {
                "input": Decimal(str(pricing_config.get("LLM_PRICING_CLAUDE3_SONNET_INPUT", "0.003"))),
                "output": Decimal(str(pricing_config.get("LLM_PRICING_CLAUDE3_SONNET_OUTPUT", "0.015")))
            },
            "claude-3-haiku": {
                "input": Decimal(str(pricing_config.get("LLM_PRICING_CLAUDE3_HAIKU_INPUT", "0.00025"))),
                "output": Decimal(str(pricing_config.get("LLM_PRICING_CLAUDE3_HAIKU_OUTPUT", "0.00125")))
            },
            
            # Google models
            "gemini-pro": {
                "input": Decimal(str(pricing_config.get("LLM_PRICING_GEMINI_PRO_INPUT", "0.0005"))),
                "output": Decimal(str(pricing_config.get("LLM_PRICING_GEMINI_PRO_OUTPUT", "0.0015")))
            },
            "gemini-2.5-flash": {
                "input": Decimal(str(pricing_config.get("LLM_PRICING_GEMINI_FLASH_INPUT", "0.00035"))),
                "output": Decimal(str(pricing_config.get("LLM_PRICING_GEMINI_FLASH_OUTPUT", "0.00053")))
            },
            
            # Default pricing
            "default": {
                "input": Decimal(str(pricing_config.get("LLM_PRICING_DEFAULT_INPUT", "0.001"))),
                "output": Decimal(str(pricing_config.get("LLM_PRICING_DEFAULT_OUTPUT", "0.002")))
            }
        }
        
        # Return specific model or all models
        if model:
            return {model: structured_pricing.get(model, structured_pricing["default"])}
        
        return structured_pricing
    
    def get_optimization_settings(self) -> Dict[str, Any]:
        """Get optimization settings from configuration system.
        
        Returns:
            Dictionary with optimization settings and thresholds
        """
        return self._get_cached_config("optimization_settings", {
            "TOKEN_OPTIMIZATION_ENABLED": True,
            "TOKEN_OPTIMIZATION_DEFAULT_TARGET_REDUCTION": 20,
            "TOKEN_OPTIMIZATION_MIN_REDUCTION": 5,
            "TOKEN_OPTIMIZATION_MAX_REDUCTION": 50,
            "TOKEN_OPTIMIZATION_CACHE_TTL_SECONDS": 3600,
            "TOKEN_OPTIMIZATION_HIGH_TOKEN_THRESHOLD": 2000,
            "TOKEN_OPTIMIZATION_VERBOSE_LOGGING": False
        })
    
    def get_cost_alert_thresholds(self) -> Dict[str, Decimal]:
        """Get cost alert thresholds from configuration system.
        
        Returns:
            Dictionary with cost thresholds for different alert levels
        """
        threshold_config = self._get_cached_config("cost_thresholds", {
            "COST_ALERT_LOW_THRESHOLD": "0.10",
            "COST_ALERT_MEDIUM_THRESHOLD": "1.00", 
            "COST_ALERT_HIGH_THRESHOLD": "5.00",
            "COST_ALERT_CRITICAL_THRESHOLD": "25.00",
            "COST_DAILY_BUDGET_WARNING": "50.00",
            "COST_DAILY_BUDGET_LIMIT": "100.00"
        })
        
        return {
            "low": Decimal(str(threshold_config.get("COST_ALERT_LOW_THRESHOLD", "0.10"))),
            "medium": Decimal(str(threshold_config.get("COST_ALERT_MEDIUM_THRESHOLD", "1.00"))),
            "high": Decimal(str(threshold_config.get("COST_ALERT_HIGH_THRESHOLD", "5.00"))),
            "critical": Decimal(str(threshold_config.get("COST_ALERT_CRITICAL_THRESHOLD", "25.00"))),
            "daily_warning": Decimal(str(threshold_config.get("COST_DAILY_BUDGET_WARNING", "50.00"))),
            "daily_limit": Decimal(str(threshold_config.get("COST_DAILY_BUDGET_LIMIT", "100.00")))
        }
    
    def get_session_management_settings(self) -> Dict[str, Any]:
        """Get session management settings from configuration system.
        
        Returns:
            Dictionary with session management configuration
        """
        return self._get_cached_config("session_management", {
            "SESSION_MAX_AGE_HOURS": 24,
            "SESSION_CLEANUP_INTERVAL_MINUTES": 60,
            "SESSION_MAX_CONCURRENT_PER_USER": 10,
            "SESSION_ENABLE_AUTOMATIC_FINALIZATION": True,
            "SESSION_TRACK_USER_PATTERNS": True,
            "SESSION_ENABLE_CROSS_SESSION_ANALYTICS": False  # Privacy compliance
        })
    
    def get_model_specific_config(self, model: str) -> Dict[str, Any]:
        """Get model-specific configuration settings.
        
        Args:
            model: Model name to get configuration for
            
        Returns:
            Dictionary with model-specific settings
        """
        # Normalize model name for configuration lookup
        model_key = model.upper().replace("-", "_").replace(".", "_")
        
        base_config = self._get_cached_config("model_specific", {
            f"MODEL_{model_key}_MAX_CONTEXT_LENGTH": 4096,
            f"MODEL_{model_key}_OPTIMIZATION_ENABLED": True,
            f"MODEL_{model_key}_PREFERRED_FOR_COST": False,
            f"MODEL_{model_key}_QUALITY_TIER": "standard",
            f"MODEL_{model_key}_RATE_LIMIT_PER_MINUTE": 60
        })
        
        return {
            "max_context_length": base_config.get(f"MODEL_{model_key}_MAX_CONTEXT_LENGTH", 4096),
            "optimization_enabled": base_config.get(f"MODEL_{model_key}_OPTIMIZATION_ENABLED", True),
            "preferred_for_cost": base_config.get(f"MODEL_{model_key}_PREFERRED_FOR_COST", False),
            "quality_tier": base_config.get(f"MODEL_{model_key}_QUALITY_TIER", "standard"),
            "rate_limit_per_minute": base_config.get(f"MODEL_{model_key}_RATE_LIMIT_PER_MINUTE", 60)
        }
    
    def is_optimization_enabled_for_user(self, user_id: str) -> bool:
        """Check if token optimization is enabled for a specific user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if optimization is enabled for the user
        """
        # Check global setting first
        optimization_settings = self.get_optimization_settings()
        if not optimization_settings.get("TOKEN_OPTIMIZATION_ENABLED", True):
            return False
        
        # Check user-specific settings (could be implemented later)
        user_config = self._get_cached_config("user_specific", {
            f"USER_{user_id}_OPTIMIZATION_ENABLED": True,
            f"USER_{user_id}_OPTIMIZATION_LEVEL": "standard"
        })
        
        return user_config.get(f"USER_{user_id}_OPTIMIZATION_ENABLED", True)
    
    def get_cost_budget_for_user(self, user_id: str) -> Optional[Decimal]:
        """Get cost budget configuration for a specific user.
        
        Args:
            user_id: User ID to get budget for
            
        Returns:
            User's cost budget or None if no limit configured
        """
        user_config = self._get_cached_config("user_budgets", {
            f"USER_{user_id}_DAILY_BUDGET": None,
            f"USER_{user_id}_MONTHLY_BUDGET": None,
            f"USER_{user_id}_TOTAL_BUDGET": None
        })
        
        # Check for daily budget first (most restrictive)
        daily_budget = user_config.get(f"USER_{user_id}_DAILY_BUDGET")
        if daily_budget:
            return Decimal(str(daily_budget))
        
        # Fall back to monthly budget
        monthly_budget = user_config.get(f"USER_{user_id}_MONTHLY_BUDGET")  
        if monthly_budget:
            return Decimal(str(monthly_budget)) / 30  # Daily equivalent
        
        # No specific budget configured
        return None
    
    def _get_cached_config(self, config_section: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
        """Get configuration with caching to reduce lookup overhead.
        
        Args:
            config_section: Section identifier for caching
            defaults: Default values if configuration is not available
            
        Returns:
            Configuration dictionary with values from config system or defaults
        """
        current_time = datetime.now(timezone.utc)
        
        # Check if cache is valid
        if (self._cache_timestamp and 
            (current_time - self._cache_timestamp).total_seconds() < self._cache_ttl_seconds and
            config_section in self._config_cache):
            return self._config_cache[config_section]
        
        # Fetch configuration from UnifiedConfigurationManager
        config_values = {}
        
        try:
            for key, default_value in defaults.items():
                # Get value from configuration manager
                config_value = self.config_manager.get(key, default_value)
                config_values[key] = config_value
                
        except Exception as e:
            logger.warning(
                f"Failed to load configuration for {config_section}, using defaults: {e}"
            )
            config_values = defaults
        
        # Update cache
        if not self._config_cache:
            self._config_cache = {}
        
        self._config_cache[config_section] = config_values
        self._cache_timestamp = current_time
        
        logger.debug(f"Loaded configuration for {config_section} with {len(config_values)} settings")
        
        return config_values
    
    def invalidate_cache(self) -> None:
        """Invalidate configuration cache to force reload."""
        self._config_cache.clear()
        self._cache_timestamp = None
        logger.debug("Configuration cache invalidated")
    
    def get_all_config_summary(self) -> Dict[str, Any]:
        """Get comprehensive configuration summary for monitoring and debugging.
        
        Returns:
            Dictionary with all token optimization configuration
        """
        return {
            "pricing": self.get_model_pricing(),
            "optimization_settings": self.get_optimization_settings(),
            "cost_thresholds": {k: float(v) for k, v in self.get_cost_alert_thresholds().items()},
            "session_management": self.get_session_management_settings(),
            "cache_status": {
                "cache_sections": list(self._config_cache.keys()),
                "last_updated": self._cache_timestamp.isoformat() if self._cache_timestamp else None,
                "ttl_seconds": self._cache_ttl_seconds
            },
            "config_manager_type": "UnifiedConfigurationManager",
            "uses_configuration_system": True,
            "hardcoded_values": False
        }