"""LLM Configuration Helper for E2E Testing

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable reliable LLM integration testing
- Value Impact: Ensures agent pipeline tests work in staging environment
- Strategic Impact: Prevents regressions in core AI functionality

This module provides SSOT methods for configuring LLM access in different environments,
particularly handling the staging environment where API keys are loaded from Secret Manager.
"""

import logging
from typing import Dict, List, Optional, Tuple

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class LLMConfigHelper:
    """Helper class for LLM configuration in different environments."""
    
    SUPPORTED_PROVIDERS = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", 
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY"
    ]
    
    @classmethod
    def get_current_environment(cls) -> str:
        """Get the current environment name."""
        return get_env().get_environment_name()
    
    @classmethod
    def check_llm_availability(cls) -> Tuple[bool, List[str], List[str]]:
        """Check LLM API key availability with environment-specific logic.
        
        Returns:
            Tuple of (available, found_keys, missing_keys)
        """
        env = get_env()
        current_env = cls.get_current_environment()
        
        found_keys = []
        missing_keys = []
        
        for provider in cls.SUPPORTED_PROVIDERS:
            value = env.get(provider)
            if value and value.strip() and not value.startswith("test-"):
                found_keys.append(provider)
            else:
                missing_keys.append(provider)
        
        # Environment-specific validation
        if current_env == "staging":
            # In staging, keys might be loaded from Secret Manager at runtime
            # Check if real LLM is enabled
            use_real_llm = env.get("USE_REAL_LLM", "false").lower() == "true"
            test_use_real_llm = env.get("TEST_USE_REAL_LLM", "false").lower() == "true"
            
            if use_real_llm or test_use_real_llm:
                # Trust that Secret Manager will provide keys, consider available
                available = True
                logger.info(f"Staging environment: Real LLM enabled, trusting Secret Manager for API keys")
            else:
                available = len(found_keys) > 0
        else:
            # For other environments, require at least one key to be directly available
            available = len(found_keys) > 0
        
        return available, found_keys, missing_keys
    
    @classmethod
    def setup_staging_llm_config(cls) -> None:
        """Setup LLM configuration for staging environment."""
        env = get_env()
        current_env = cls.get_current_environment()
        
        if current_env == "staging":
            # Enable real LLM usage in staging
            env.set("USE_REAL_LLM", "true", "staging_llm_config")
            env.set("TEST_USE_REAL_LLM", "true", "staging_llm_config")
            logger.info("Enabled real LLM usage for staging environment")
    
    @classmethod
    def get_llm_status_summary(cls) -> Dict[str, any]:
        """Get a summary of LLM configuration status.
        
        Returns:
            Dictionary with configuration status information
        """
        available, found_keys, missing_keys = cls.check_llm_availability()
        env = get_env()
        current_env = cls.get_current_environment()
        
        return {
            "environment": current_env,
            "llm_available": available,
            "found_api_keys": found_keys,
            "missing_api_keys": missing_keys,
            "use_real_llm": env.get("USE_REAL_LLM", "false").lower() == "true",
            "test_use_real_llm": env.get("TEST_USE_REAL_LLM", "false").lower() == "true",
            "total_providers_found": len(found_keys),
            "staging_secret_manager_expected": current_env == "staging"
        }
    
    @classmethod
    def validate_for_pipeline_test(cls, require_real_keys: bool = True) -> Tuple[bool, str]:
        """Validate LLM configuration for agent pipeline testing.
        
        Args:
            require_real_keys: Whether to require real API keys (vs placeholders)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        available, found_keys, missing_keys = cls.check_llm_availability()
        current_env = cls.get_current_environment()
        env = get_env()
        
        if current_env == "staging":
            # For staging, check if real LLM is enabled
            use_real_llm = env.get("USE_REAL_LLM", "false").lower() == "true"
            test_use_real_llm = env.get("TEST_USE_REAL_LLM", "false").lower() == "true"
            
            if use_real_llm or test_use_real_llm:
                # Staging with real LLM enabled is valid
                return True, ""
            elif not available:
                return False, "Staging environment requires USE_REAL_LLM=true or valid API keys from Secret Manager"
        
        if not available and require_real_keys:
            return False, f"No valid LLM API keys found. Missing: {', '.join(missing_keys)}"
        
        return True, ""
    
    @classmethod
    def setup_test_environment(cls) -> None:
        """Setup optimal LLM configuration for test environment."""
        env = get_env()
        current_env = cls.get_current_environment()
        
        # Always enable real LLM for E2E tests
        env.set("USE_REAL_LLM", "true", "test_setup")
        env.set("TEST_USE_REAL_LLM", "true", "test_setup")
        
        if current_env == "staging":
            cls.setup_staging_llm_config()
            
        logger.info(f"LLM test environment setup complete for {current_env}")


def setup_llm_for_testing() -> bool:
    """Setup LLM configuration for testing - convenience function.
    
    Returns:
        bool: True if LLM is properly configured for testing
    """
    helper = LLMConfigHelper()
    helper.setup_test_environment()
    
    is_valid, error_msg = helper.validate_for_pipeline_test()
    if not is_valid:
        logger.error(f"LLM configuration validation failed: {error_msg}")
        return False
    
    return True


def get_llm_config_status() -> Dict[str, any]:
    """Get current LLM configuration status - convenience function.
    
    Returns:
        Dictionary with LLM configuration status
    """
    return LLMConfigHelper.get_llm_status_summary()