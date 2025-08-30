"""Unified LLM Configuration Manager for Netra Test Framework.

This is the SINGLE SOURCE OF TRUTH for all LLM test configuration.
All other LLM configuration systems have been consolidated into this module.

Business Value Justification (BVJ):
1. Segment: Platform/Internal
2. Business Goal: Development Velocity, Testing Infrastructure Reliability
3. Value Impact: Eliminates configuration inconsistencies that cause test failures
4. Strategic Impact: Reduces debugging time, improves developer experience

ARCHITECTURAL COMPLIANCE:
- Single Source of Truth (SSOT): ONE canonical LLM configuration system
- File size: <750 lines (focused module)
- Single responsibility: LLM test configuration and mode management
- Type safety with Pydantic models and enums
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


# Configure logging for LLM testing
logger = logging.getLogger(__name__)


class LLMTestMode(Enum):
    """Test modes for LLM configuration."""
    MOCK = "mock"           # Use mock responses only
    REAL = "real"           # Use real LLM APIs
    MIXED = "mixed"         # Allow both real and mock based on availability


class LLMProvider(Enum):
    """Supported LLM providers for testing."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MOCK = "mock"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    provider: LLMProvider
    max_tokens: int = 2000
    temperature: float = 0.0  # Deterministic for testing
    timeout_seconds: int = 30
    cost_per_1k_tokens: float = 0.01
    
    def __post_init__(self):
        """Validate model configuration."""
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")


@dataclass
class LLMTestConfig:
    """Unified configuration for all LLM testing."""
    mode: LLMTestMode = LLMTestMode.MOCK
    timeout_seconds: int = 30
    max_retries: int = 3
    cost_budget_per_run: float = 50.0
    rate_limit_per_minute: int = 60
    
    # Environment configuration
    use_dedicated_env: bool = True
    
    # Test execution settings
    parallel_execution: int = 3  # Conservative for LLM rate limits
    
    # Model configurations
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default models if none provided."""
        if not self.models:
            self.models = self._get_default_models()
    
    def _get_default_models(self) -> Dict[str, ModelConfig]:
        """Get default model configurations optimized for testing."""
        return {
            "gemini-2.5-pro": ModelConfig(
                name="gemini-2.5-pro",
                provider=LLMProvider.GOOGLE,
                max_tokens=2000,
                timeout_seconds=25,
                cost_per_1k_tokens=0.002
            ),
            "gemini-2.5-flash": ModelConfig(
                name="gemini-2.5-flash",
                provider=LLMProvider.GOOGLE,
                max_tokens=2000,
                timeout_seconds=25,
                cost_per_1k_tokens=0.001
            ),
            "gpt-4": ModelConfig(
                name="gpt-4-turbo-preview",
                provider=LLMProvider.OPENAI,
                max_tokens=2000,
                timeout_seconds=30,
                cost_per_1k_tokens=0.03
            ),
            "claude-3": ModelConfig(
                name="claude-3-opus-20240229",
                provider=LLMProvider.ANTHROPIC,
                max_tokens=2000,
                timeout_seconds=30,
                cost_per_1k_tokens=0.075
            ),
            "mock": ModelConfig(
                name="mock-model",
                provider=LLMProvider.MOCK,
                max_tokens=2000,
                timeout_seconds=1,
                cost_per_1k_tokens=0.0
            )
        }


class LLMConfigManager:
    """Unified manager for all LLM test configuration."""
    
    # CANONICAL environment variable names (SSOT)
    ENABLE_REAL_LLM_VAR = "ENABLE_REAL_LLM_TESTING"
    TEST_LLM_MODE_VAR = "TEST_LLM_MODE"
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._api_keys = self._load_api_keys()
        self.config = self._load_configuration()
        self._original_env = {}  # For restoration
        
    def _load_configuration(self) -> LLMTestConfig:
        """Load configuration from environment variables."""
        # Determine mode from environment
        mode = self._determine_mode()
        
        config = LLMTestConfig(
            mode=mode,
            timeout_seconds=int(os.getenv("TEST_LLM_TIMEOUT", "30")),
            max_retries=int(os.getenv("TEST_LLM_RETRIES", "3")),
            cost_budget_per_run=float(os.getenv("TEST_LLM_BUDGET", "50.0")),
            rate_limit_per_minute=int(os.getenv("TEST_LLM_RATE_LIMIT", "60")),
            parallel_execution=int(os.getenv("TEST_LLM_PARALLEL", "3")),
            use_dedicated_env=os.getenv("TEST_USE_DEDICATED_ENV", "true").lower() == "true"
        )
        
        # Validate configuration if real LLM is enabled
        if mode == LLMTestMode.REAL:
            self._validate_real_llm_setup()
        
        return config
    
    def _determine_mode(self) -> LLMTestMode:
        """Determine LLM test mode from environment variables."""
        # Check explicit mode setting first
        explicit_mode = os.getenv(self.TEST_LLM_MODE_VAR)
        if explicit_mode:
            try:
                return LLMTestMode(explicit_mode.lower())
            except ValueError:
                logger.warning(f"Invalid LLM test mode: {explicit_mode}, defaulting to mock")
        
        # Check legacy environment variables for backward compatibility
        if (os.getenv(self.ENABLE_REAL_LLM_VAR, "false").lower() == "true" or 
            os.getenv("USE_REAL_LLM", "false").lower() == "true" or
            os.getenv("TEST_USE_REAL_LLM", "false").lower() == "true"):  # Legacy support
            return LLMTestMode.REAL
        
        return LLMTestMode.MOCK
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys, preferring TEST_* variants."""
        api_keys = {}
        
        # Define key mappings (TEST_* preferred over production keys)
        key_mappings = {
            'openai': ['TEST_OPENAI_API_KEY', 'OPENAI_API_KEY'],
            'anthropic': ['TEST_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'],
            'google': ['TEST_GOOGLE_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_API_KEY']
        }
        
        for provider, key_options in key_mappings.items():
            for key in key_options:
                value = os.getenv(key)
                if value:
                    api_keys[provider] = value
                    if not key.startswith('TEST_'):
                        logger.warning(f"Using production {provider.upper()} API key - consider using TEST_{key}")
                    break
        
        return api_keys
    
    def _validate_real_llm_setup(self):
        """Validate that real LLM testing can be performed."""
        if not self._api_keys:
            raise ValueError(
                "Real LLM testing enabled but no API keys found. "
                "Set at least one of: TEST_OPENAI_API_KEY, TEST_ANTHROPIC_API_KEY, TEST_GOOGLE_API_KEY"
            )
        
        available_providers = list(self._api_keys.keys())
        logger.info(f"Real LLM testing enabled with providers: {available_providers}")
    
    def configure_environment(self, 
                            mode: Optional[LLMTestMode] = None,
                            model: str = "gemini-2.5-pro",
                            timeout: int = 60,
                            parallel: Union[str, int] = "auto",
                            use_dedicated_env: bool = True) -> Dict[str, Any]:
        """Configure environment for LLM testing with the specified mode.
        
        This is the CANONICAL function for configuring LLM testing environment.
        Replaces all other configure_real_llm functions.
        
        Args:
            mode: LLM test mode (mock, real, mixed)
            model: Default model to use
            timeout: Timeout in seconds
            parallel: Parallelism level ("auto", "max", or integer)
            use_dedicated_env: Whether to use dedicated test environment
            
        Returns:
            Configuration dictionary
        """
        # Save original environment for restoration
        self._save_original_environment()
        
        # Use provided mode or current config mode
        actual_mode = mode or self.config.mode
        
        # Handle parallel execution
        if parallel == "max":
            parallel_value = 8  # Maximum safe parallelism
        elif parallel == "auto":
            # For real LLM tests, limit parallelism to avoid rate limits
            parallel_value = 3 if actual_mode == LLMTestMode.REAL else 8
        else:
            parallel_value = int(parallel)
        
        # Set canonical environment variables
        os.environ[self.ENABLE_REAL_LLM_VAR] = str(actual_mode == LLMTestMode.REAL).lower()
        os.environ[self.TEST_LLM_MODE_VAR] = actual_mode.value
        os.environ["TEST_LLM_MODEL"] = model
        os.environ["TEST_LLM_TIMEOUT"] = str(timeout)
        os.environ["TEST_LLM_PARALLEL"] = str(parallel_value)
        
        # Set environment variables
        if actual_mode == LLMTestMode.REAL:
            os.environ["USE_REAL_LLM"] = "true"
            os.environ["TEST_USE_REAL_LLM"] = "true"  # Legacy compatibility
        else:
            os.environ["USE_REAL_LLM"] = "false"
            os.environ["TEST_USE_REAL_LLM"] = "false"  # Legacy compatibility
        
        # Configure dedicated test environment if requested
        if use_dedicated_env:
            self._configure_dedicated_test_environment()
        
        # Build configuration response
        config_response = {
            "mode": actual_mode.value,
            "model": model,
            "timeout": timeout,
            "parallel": parallel_value,
            "use_dedicated_env": use_dedicated_env,
            "rate_limit_delay": 1 if parallel_value > 2 and actual_mode == LLMTestMode.REAL else 0
        }
        
        logger.info(f"LLM testing configured: mode={actual_mode.value}, model={model}, parallel={parallel_value}")
        return config_response
    
    def _configure_dedicated_test_environment(self):
        """Configure dedicated test environment with isolated resources."""
        # Database configuration for test environment
        test_db_url = os.getenv("TEST_DATABASE_URL")
        if not test_db_url:
            # Fallback to main database with test schema
            main_db_url = os.getenv("DATABASE_URL", "postgresql://localhost/netra_main")
            test_db_url = main_db_url.replace("/netra_main", "/netra_test")
            os.environ["TEST_DATABASE_URL"] = test_db_url
        
        # Redis configuration with test namespace
        test_redis_url = os.getenv("TEST_REDIS_URL")
        if not test_redis_url:
            main_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            # Use database index 1 for tests
            test_redis_url = main_redis_url.replace("/0", "/1")
            os.environ["TEST_REDIS_URL"] = test_redis_url
        
        # Set Redis namespace prefix for test isolation
        os.environ["TEST_REDIS_NAMESPACE"] = "test:"
        
        # ClickHouse configuration with test database
        test_clickhouse_url = os.getenv("TEST_CLICKHOUSE_URL")
        if not test_clickhouse_url:
            main_clickhouse_url = os.getenv("CLICKHOUSE_URL", "clickhouse://localhost:8123/netra_main")
            test_clickhouse_url = main_clickhouse_url.replace("/netra_main", "/netra_test")
            os.environ["TEST_CLICKHOUSE_URL"] = test_clickhouse_url
        
        # Set ClickHouse table prefix for test isolation
        os.environ["TEST_CLICKHOUSE_TABLES_PREFIX"] = "test_"
        
        # Set test environment flag
        os.environ["TEST_ENVIRONMENT"] = "test_dedicated"
        os.environ["USE_TEST_ISOLATION"] = "true"
    
    def _save_original_environment(self):
        """Save original environment variables for restoration."""
        env_vars = [
            self.ENABLE_REAL_LLM_VAR,
            self.TEST_LLM_MODE_VAR,
            "USE_REAL_LLM",
            "TEST_USE_REAL_LLM",  # Legacy compatibility
            "TEST_LLM_MODEL",
            "TEST_LLM_TIMEOUT",
            "TEST_LLM_PARALLEL"
        ]
        
        for var in env_vars:
            if var in os.environ:
                self._original_env[var] = os.environ[var]
            else:
                self._original_env[var] = None
    
    def restore_environment(self):
        """Restore original environment variables."""
        for var, original_value in self._original_env.items():
            if original_value is None:
                # Variable didn't exist originally
                if var in os.environ:
                    del os.environ[var]
            else:
                os.environ[var] = original_value
        
        self._original_env.clear()
    
    def is_real_llm_enabled(self) -> bool:
        """Check if real LLM testing is currently enabled."""
        return self.config.mode == LLMTestMode.REAL
    
    def get_current_mode(self) -> LLMTestMode:
        """Get current LLM test mode."""
        return self.config.mode
    
    def has_api_key(self, provider: str) -> bool:
        """Check if API key is available for provider."""
        return provider.lower() in self._api_keys
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for specific provider."""
        return self._api_keys.get(provider.lower())
    
    def get_model_config(self, model_key: str) -> ModelConfig:
        """Get configuration for a specific model."""
        if model_key not in self.config.models:
            logger.warning(f"Model {model_key} not found, using gemini-2.5-pro default")
            model_key = "gemini-2.5-pro"
        
        return self.config.models[model_key]
    
    def get_available_providers(self) -> List[str]:
        """Get list of available LLM providers."""
        if self.config.mode == LLMTestMode.MOCK:
            return ["mock"]
        elif self.config.mode == LLMTestMode.REAL:
            return list(self._api_keys.keys())
        else:  # MIXED
            return ["mock"] + list(self._api_keys.keys())


# Global singleton instance
_llm_config_manager: Optional[LLMConfigManager] = None


def get_llm_config_manager() -> LLMConfigManager:
    """Get the global LLM configuration manager instance."""
    global _llm_config_manager
    if _llm_config_manager is None:
        _llm_config_manager = LLMConfigManager()
    return _llm_config_manager


def configure_llm_testing(mode: Optional[LLMTestMode] = None,
                         model: str = "gemini-2.5-pro",
                         timeout: int = 60,
                         parallel: Union[str, int] = "auto",
                         use_dedicated_env: bool = True) -> Dict[str, Any]:
    """Configure LLM testing environment.
    
    This is the CANONICAL function for configuring LLM testing.
    Replaces all other configure_real_llm functions throughout the codebase.
    
    Args:
        mode: LLM test mode (None for auto-detection)
        model: Default model to use
        timeout: Timeout in seconds  
        parallel: Parallelism level
        use_dedicated_env: Whether to use dedicated test environment
        
    Returns:
        Configuration dictionary
    """
    manager = get_llm_config_manager()
    return manager.configure_environment(
        mode=mode,
        model=model,
        timeout=timeout,
        parallel=parallel,
        use_dedicated_env=use_dedicated_env
    )


def is_real_llm_enabled() -> bool:
    """Check if real LLM testing is currently enabled."""
    manager = get_llm_config_manager()
    return manager.is_real_llm_enabled()


def get_llm_test_mode() -> LLMTestMode:
    """Get current LLM test mode."""
    manager = get_llm_config_manager()
    return manager.get_current_mode()


def restore_llm_environment():
    """Restore original LLM environment variables."""
    manager = get_llm_config_manager()
    manager.restore_environment()


# Backward compatibility functions (DEPRECATED - use configure_llm_testing instead)
def configure_real_llm(model: str = "gemini-2.5-pro", 
                       timeout: int = 60, 
                       parallel: Union[str, int] = "auto", 
                       test_level: Optional[str] = None, 
                       use_dedicated_env: bool = True) -> Dict[str, Any]:
    """DEPRECATED: Use configure_llm_testing instead.
    
    Maintained for backward compatibility only.
    """
    logger.warning(
        "configure_real_llm is deprecated. Use configure_llm_testing(mode=LLMTestMode.REAL, ...) instead"
    )
    return configure_llm_testing(
        mode=LLMTestMode.REAL,
        model=model,
        timeout=timeout,
        parallel=parallel,
        use_dedicated_env=use_dedicated_env
    )