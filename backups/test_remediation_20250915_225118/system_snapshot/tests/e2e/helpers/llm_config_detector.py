from shared.isolated_environment import get_env
"""LLM Configuration Detection Helper

from shared.isolated_environment import get_env
Detects whether tests should use real LLM services or mock configurations.
Provides utilities for E2E tests to adapt to different environments.

Business Value: Enables flexible test execution across dev/staging/prod environments.
"""

import os
from typing import Dict, Any, Optional
from netra_backend.app.config import get_config


env = get_env()
class LLMConfigDetector:
    """Detects LLM configuration for test execution."""
    
    def __init__(self):
        self.config = get_config()
        self._real_llm_detected = None
        
    def should_use_real_llm(self) -> bool:
        """Determine if tests should use real LLM services."""
        if self._real_llm_detected is not None:
            return self._real_llm_detected
            
        # Check environment variables
        use_real_llm = get_env().get("USE_REAL_LLM", "false").lower()
        if use_real_llm in ["true", "1", "yes"]:
            self._real_llm_detected = True
            return True
            
        # Check pytest markers/flags
        if get_env().get("PYTEST_REAL_LLM", "false").lower() in ["true", "1"]:
            self._real_llm_detected = True
            return True
            
        # Check if running in staging/production environment
        env_name = get_env().get("ENVIRONMENT", "dev").lower()
        if env_name in ["staging", "prod", "production"]:
            self._real_llm_detected = True
            return True
            
        # Check for specific real LLM keys
        if self._has_real_llm_keys():
            self._real_llm_detected = True
            return True
            
        # Default to mock
        self._real_llm_detected = False
        return False
        
    def get_llm_test_config(self) -> Dict[str, Any]:
        """Get LLM configuration for testing."""
        if self.should_use_real_llm():
            return {
                "use_real_llm": True,
                "timeout_multiplier": 3.0,  # Real LLM calls take longer
                "max_retries": 2,
                "test_mode": "real_llm"
            }
        else:
            return {
                "use_real_llm": False,
                "timeout_multiplier": 1.0,
                "max_retries": 0,
                "test_mode": "mock_llm"
            }
    
    def _has_real_llm_keys(self) -> bool:
        """Check if real LLM API keys are available."""
        # Check for OpenAI API key
        if get_env().get("GOOGLE_API_KEY"):
            return True
            
        # Check for Anthropic API key
        if get_env().get("ANTHROPIC_API_KEY"):
            return True
            
        # Check for other LLM provider keys
        llm_keys = [
            "GOOGLE_API_KEY",
            "AZURE_OPENAI_KEY",
            "COHERE_API_KEY",
            "MISTRAL_API_KEY"
        ]
        
        return any(get_env().get(key) for key in llm_keys)
    
    def get_test_timeout(self, base_timeout: float) -> float:
        """Get adjusted timeout based on LLM configuration."""
        config = self.get_llm_test_config()
        return base_timeout * config["timeout_multiplier"]
        
    def skip_if_no_real_llm(self) -> Optional[str]:
        """Return skip reason if real LLM required but not available."""
        if self.should_use_real_llm():
            return None
        return "Real LLM configuration not detected - set USE_REAL_LLM=true to enable"


# Global instance for easy access
llm_detector = LLMConfigDetector()


def pytest_configure_real_llm():
    """Configure pytest for real LLM testing."""
    import pytest
    
    # Add custom markers
    pytest.mark.real_llm = pytest.mark.skipif(
        not llm_detector.should_use_real_llm(),
        reason="Real LLM not available - use --real-llm flag or set USE_REAL_LLM=true"
    )
    
    pytest.mark.mock_llm_only = pytest.mark.skipif(
        llm_detector.should_use_real_llm(),
        reason="Test designed for mock LLM only"
    )


def get_llm_config_for_test() -> Dict[str, Any]:
    """Get LLM configuration for current test context."""
    return llm_detector.get_llm_test_config()
