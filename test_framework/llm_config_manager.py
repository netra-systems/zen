"""LLM configuration manager for testing.

This module provides configuration management for LLM testing modes,
allowing tests to use real or mock LLM services as needed.
"""

from enum import Enum
from typing import Dict, Optional
from shared.isolated_environment import get_env


class LLMTestMode(Enum):
    """LLM testing mode enumeration."""
    REAL = "real"
    MOCK = "mock" 
    FAST = "fast"


class LLMConfigManager:
    """Manages LLM configuration for testing."""
    
    def __init__(self):
        """Initialize LLM config manager."""
        self.env = get_env()
        self.mode = self._detect_mode()
        self.config = self._get_default_config()
    
    def _detect_mode(self) -> LLMTestMode:
        """Detect LLM testing mode from environment.
        
        Returns:
            Detected LLM test mode
        """
        if self.env.get("TEST_REAL_LLM", "false").lower() == "true":
            return LLMTestMode.REAL
        elif self.env.get("TEST_FAST", "false").lower() == "true":
            return LLMTestMode.FAST
        else:
            return LLMTestMode.MOCK
    
    def _get_default_config(self) -> Dict:
        """Get default LLM configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "model": self.env.get("TEST_LLM_MODEL", "gemini-2.5-flash"),
            "api_key": self.env.get("TEST_LLM_API_KEY"),
            "timeout": int(self.env.get("TEST_LLM_TIMEOUT", "30")),
            "max_tokens": int(self.env.get("TEST_LLM_MAX_TOKENS", "1000")),
            "temperature": float(self.env.get("TEST_LLM_TEMPERATURE", "0.0"))
        }
    
    def configure(self, mode: Optional[LLMTestMode] = None, **kwargs):
        """Configure LLM testing settings.
        
        Args:
            mode: Optional LLM test mode override
            **kwargs: Additional configuration parameters
        """
        if mode:
            self.mode = mode
        
        self.config.update(kwargs)
    
    def get_config(self) -> Dict:
        """Get current LLM configuration.
        
        Returns:
            Current configuration dictionary
        """
        return self.config.copy()
    
    def is_real_llm(self) -> bool:
        """Check if using real LLM services.
        
        Returns:
            True if using real LLM, False otherwise
        """
        return self.mode == LLMTestMode.REAL
    
    def should_use_mock(self) -> bool:
        """Check if should use mock LLM.
        
        Returns:
            True if should use mock, False otherwise
        """
        return self.mode in [LLMTestMode.MOCK, LLMTestMode.FAST]


# Global config manager instance
_global_config_manager: Optional[LLMConfigManager] = None


def get_llm_config_manager() -> LLMConfigManager:
    """Get the global LLM config manager instance.
    
    Returns:
        Global LLMConfigManager instance
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = LLMConfigManager()
    return _global_config_manager


def configure_llm_testing(mode: Optional[LLMTestMode] = None, **config) -> Dict:
    """Configure LLM testing settings.
    
    Args:
        mode: Optional LLM test mode
        **config: Additional configuration parameters
        
    Returns:
        Updated configuration dictionary
    """
    manager = get_llm_config_manager()
    manager.configure(mode, **config)
    return manager.get_config()


def is_real_llm_enabled() -> bool:
    """Check if real LLM is enabled for testing.
    
    Returns:
        True if real LLM is enabled, False otherwise
    """
    manager = get_llm_config_manager()
    return manager.is_real_llm()


def should_skip_llm_test() -> bool:
    """Check if LLM tests should be skipped.
    
    Returns:
        True if LLM tests should be skipped, False otherwise
    """
    manager = get_llm_config_manager()
    # Skip if not using real LLM and no API key available
    if manager.should_use_mock() and not manager.config.get("api_key"):
        return True
    return False


def get_llm_test_config() -> Dict:
    """Get LLM test configuration.
    
    Returns:
        Current LLM test configuration
    """
    manager = get_llm_config_manager()
    return manager.get_config()


def configure_fast_llm_testing() -> Dict:
    """Configure fast LLM testing with minimal settings.
    
    Returns:
        Fast test configuration
    """
    return configure_llm_testing(
        mode=LLMTestMode.FAST,
        timeout=5,
        max_tokens=100
    )


def configure_real_llm_testing(model: str = "gemini-2.5-flash") -> Dict:
    """Configure real LLM testing.
    
    Args:
        model: LLM model to use
        
    Returns:
        Real LLM test configuration
    """
    return configure_llm_testing(
        mode=LLMTestMode.REAL,
        model=model
    )


def reset_llm_config():
    """Reset LLM configuration to defaults."""
    global _global_config_manager
    _global_config_manager = None