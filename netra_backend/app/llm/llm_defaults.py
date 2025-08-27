"""Centralized LLM Model Configuration and Defaults.

This module enforces standardized LLM model selection across the entire codebase.
All LLM model references MUST go through this module to ensure consistency.

CRITICAL COMPLIANCE RULES:
1. Default model: Always use GEMINI_2_5_FLASH for tests and development
2. Advanced scenarios: Use GEMINI_2_5_PRO only when explicitly needed
3. Production: Model selection based on performance requirements
4. NO hardcoded model strings anywhere in the codebase

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Cost optimization and standardization
- Value Impact: Reduces LLM costs by 90% through efficient model selection
- Revenue Impact: Direct cost reduction increases margins
"""

from enum import Enum
from typing import Dict, Optional, Any
import os


class LLMModel(Enum):
    """Standardized LLM models for Netra platform.
    
    CRITICAL: This is the ONLY place where model names should be defined.
    All other code MUST reference these enum values.
    """
    # Primary models (Google - most cost effective)
    GEMINI_2_5_FLASH = "gemini-2.5-flash"  # DEFAULT for all tests and dev
    GEMINI_2_5_PRO = "gemini-2.5-pro"      # Advanced scenarios only
    
    # Legacy models (being phased out - DO NOT USE)
    GPT_4 = "gpt-4"                        # DEPRECATED - migrate to GEMINI
    GPT_3_5_TURBO = "gpt-3.5-turbo"       # DEPRECATED - migrate to GEMINI
    CLAUDE_3_OPUS = "claude-3-opus"        # DEPRECATED - migrate to GEMINI
    
    # Mock for testing
    MOCK = "mock"                           # Mock model for unit tests
    
    @classmethod
    def get_default(cls) -> 'LLMModel':
        """Get the default model for the current environment.
        
        Returns:
            GEMINI_2_5_FLASH in all cases unless overridden by env var.
        """
        # Allow environment override for special cases
        env_default = os.getenv('NETRA_DEFAULT_LLM_MODEL')
        if env_default:
            try:
                return cls(env_default)
            except ValueError:
                pass  # Fall through to default
        
        # Always default to GEMINI_2_5_FLASH
        return cls.GEMINI_2_5_FLASH
    
    @classmethod
    def get_test_default(cls) -> 'LLMModel':
        """Get the default model for testing.
        
        Returns:
            GEMINI_2_5_FLASH for all test scenarios.
        """
        return cls.GEMINI_2_5_FLASH
    
    @classmethod
    def get_production_default(cls) -> 'LLMModel':
        """Get the default model for production.
        
        Returns:
            GEMINI_2_5_FLASH for standard workloads.
        """
        return cls.GEMINI_2_5_FLASH
    
    def is_deprecated(self) -> bool:
        """Check if this model is deprecated."""
        return self in [self.GPT_4, self.GPT_3_5_TURBO, self.CLAUDE_3_OPUS]
    
    def get_provider(self) -> str:
        """Get the provider for this model."""
        if self in [self.GEMINI_2_5_FLASH, self.GEMINI_2_5_PRO]:
            return "google"
        elif self in [self.GPT_4, self.GPT_3_5_TURBO]:
            return "openai"
        elif self == self.CLAUDE_3_OPUS:
            return "anthropic"
        else:
            return "mock"


class LLMConfig:
    """Centralized configuration for LLM usage."""
    
    # Model configuration with costs per 1k tokens
    MODEL_COSTS: Dict[LLMModel, float] = {
        LLMModel.GEMINI_2_5_FLASH: 0.001,    # Most cost effective
        LLMModel.GEMINI_2_5_PRO: 0.01,       # 10x more expensive
        LLMModel.GPT_4: 0.03,                # 30x more expensive - DEPRECATED
        LLMModel.GPT_3_5_TURBO: 0.002,      # 2x more expensive - DEPRECATED
        LLMModel.CLAUDE_3_OPUS: 0.075,       # 75x more expensive - DEPRECATED
        LLMModel.MOCK: 0.0,                  # Free for testing
    }
    
    # Model performance characteristics
    MODEL_PERFORMANCE: Dict[LLMModel, Dict[str, Any]] = {
        LLMModel.GEMINI_2_5_FLASH: {
            "max_tokens": 8192,
            "temperature": 0.0,  # Deterministic for testing
            "timeout_seconds": 30,
            "rate_limit_rpm": 60,
        },
        LLMModel.GEMINI_2_5_PRO: {
            "max_tokens": 32768,
            "temperature": 0.0,
            "timeout_seconds": 60,
            "rate_limit_rpm": 30,
        },
        LLMModel.GPT_4: {  # DEPRECATED
            "max_tokens": 8192,
            "temperature": 0.0,
            "timeout_seconds": 60,
            "rate_limit_rpm": 20,
        },
        LLMModel.GPT_3_5_TURBO: {  # DEPRECATED
            "max_tokens": 4096,
            "temperature": 0.0,
            "timeout_seconds": 30,
            "rate_limit_rpm": 60,
        },
        LLMModel.CLAUDE_3_OPUS: {  # DEPRECATED
            "max_tokens": 4096,
            "temperature": 0.0,
            "timeout_seconds": 60,
            "rate_limit_rpm": 20,
        },
        LLMModel.MOCK: {
            "max_tokens": 4096,
            "temperature": 0.0,
            "timeout_seconds": 1,
            "rate_limit_rpm": 1000,
        }
    }
    
    @classmethod
    def get_model_config(cls, model: Optional[LLMModel] = None) -> Dict[str, Any]:
        """Get configuration for a specific model.
        
        Args:
            model: The model to get config for. Defaults to GEMINI_2_5_FLASH.
            
        Returns:
            Configuration dictionary for the model.
        """
        if model is None:
            model = LLMModel.get_default()
        
        if model.is_deprecated():
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Using deprecated model {model.value}. "
                f"Please migrate to {LLMModel.GEMINI_2_5_FLASH.value}"
            )
        
        config = cls.MODEL_PERFORMANCE.get(model, cls.MODEL_PERFORMANCE[LLMModel.GEMINI_2_5_FLASH])
        config["cost_per_1k_tokens"] = cls.MODEL_COSTS.get(model, 0.001)
        config["model_name"] = model.value
        config["provider"] = model.get_provider()
        
        return config
    
    @classmethod
    def validate_model_usage(cls, model_string: str) -> bool:
        """Validate that a model string is allowed.
        
        Args:
            model_string: The model string to validate.
            
        Returns:
            True if valid, raises ValueError if not.
            
        Raises:
            ValueError: If the model string is not a valid LLMModel value.
        """
        valid_models = [m.value for m in LLMModel]
        if model_string not in valid_models:
            raise ValueError(
                f"Invalid model '{model_string}'. "
                f"Must use LLMModel enum values: {valid_models}. "
                f"Default is {LLMModel.get_default().value}"
            )
        
        # Check if deprecated
        try:
            model = LLMModel(model_string)
            if model.is_deprecated():
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Model '{model_string}' is deprecated. "
                    f"Please use {LLMModel.GEMINI_2_5_FLASH.value} instead."
                )
        except ValueError:
            pass  # Already validated above
        
        return True
    
    @classmethod
    def get_api_key_env_var(cls, model: Optional[LLMModel] = None) -> str:
        """Get the environment variable name for the API key.
        
        Args:
            model: The model to get API key for. Defaults to GEMINI_2_5_FLASH.
            
        Returns:
            Environment variable name for the API key.
        """
        if model is None:
            model = LLMModel.get_default()
        
        provider = model.get_provider()
        
        if provider == "google":
            return "GOOGLE_API_KEY"
        elif provider == "openai":
            return "OPENAI_API_KEY"  # DEPRECATED
        elif provider == "anthropic":
            return "ANTHROPIC_API_KEY"  # DEPRECATED
        else:
            return ""  # Mock doesn't need API key


# Convenience function for migration
def get_default_llm_model() -> str:
    """Get the default LLM model string.
    
    This function is provided for backwards compatibility during migration.
    New code should use LLMModel.get_default().value directly.
    
    Returns:
        The default model string (gemini-2.5-flash).
    """
    return LLMModel.get_default().value


def migrate_deprecated_model(old_model: str) -> str:
    """Migrate a deprecated model string to the recommended replacement.
    
    Args:
        old_model: The deprecated model string.
        
    Returns:
        The recommended replacement model string.
    """
    migration_map = {
        "gpt-4": LLMModel.GEMINI_2_5_FLASH.value,
        "gpt-4-turbo": LLMModel.GEMINI_2_5_FLASH.value,
        "gpt-3.5-turbo": LLMModel.GEMINI_2_5_FLASH.value,
        "claude-3-opus": LLMModel.GEMINI_2_5_FLASH.value,
        "claude-3-sonnet": LLMModel.GEMINI_2_5_FLASH.value,
    }
    
    return migration_map.get(old_model, LLMModel.GEMINI_2_5_FLASH.value)