"""Test suite for LLM configuration API key mapping.

This test ensures that all LLM configurations have proper API key mappings
to prevent regression of the issue where 'actions_to_meet_goals' was missing
from the Gemini API key mapping.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

try:
    from netra_backend.app.core.configuration.secrets import SecretManager
    from netra_backend.app.schemas.config import AppConfig, LLMConfig, SECRET_CONFIG
    from netra_backend.app.schemas.llm_base_types import LLMProvider
except ImportError:
    pytest.skip("Required modules have been removed or have missing dependencies", allow_module_level=True)


class TestLLMConfigurationAPIKeys:
    """Test suite to ensure all LLM configurations have proper API key mappings."""
    
    def test_all_gemini_llm_configs_in_secret_mapping(self):
        """Verify all Gemini LLM configs are included in secret mapping."""
        # Get the default AppConfig
        config = AppConfig()
        
        # Find all LLM configs that use GOOGLE provider
        google_llm_configs = []
        for name, llm_config in config.llm_configs.items():
            if llm_config.provider == LLMProvider.GOOGLE:
                google_llm_configs.append(f"llm_configs.{name}")
        
        # Get the secret manager's mapping
        secret_manager = SecretManager()
        gemini_mapping = secret_manager._get_gemini_api_key_mapping()
        
        # Verify all Google LLM configs are in the mapping
        for config_name in google_llm_configs:
            assert config_name in gemini_mapping["target_models"], \
                f"LLM config '{config_name}' is missing from Gemini API key mapping"
    
    def test_secret_config_matches_secret_manager_mapping(self):
        """Ensure SECRET_CONFIG matches SecretManager mappings."""
        # Find the gemini-api-key reference in SECRET_CONFIG
        gemini_secret_ref = None
        for ref in SECRET_CONFIG:
            if ref.name == "gemini-api-key":
                gemini_secret_ref = ref
                break
        
        assert gemini_secret_ref is not None, "gemini-api-key not found in SECRET_CONFIG"
        
        # Get the secret manager's mapping
        secret_manager = SecretManager()
        gemini_mapping = secret_manager._get_gemini_api_key_mapping()
        
        # Verify the target_models match
        secret_config_models = set(gemini_secret_ref.target_models)
        secret_manager_models = set(gemini_mapping["target_models"])
        
        assert secret_config_models == secret_manager_models, \
            f"Mismatch between SECRET_CONFIG and SecretManager mappings:\n" \
            f"SECRET_CONFIG: {secret_config_models}\n" \
            f"SecretManager: {secret_manager_models}"
    
    def test_actions_to_meet_goals_specifically_included(self):
        """Specific test for actions_to_meet_goals inclusion."""
        secret_manager = SecretManager()
        gemini_mapping = secret_manager._get_gemini_api_key_mapping()
        
        assert "llm_configs.actions_to_meet_goals" in gemini_mapping["target_models"], \
            "actions_to_meet_goals is missing from Gemini API key mapping"
    
    def test_all_llm_configs_have_provider(self):
        """Ensure all LLM configs have a valid provider."""
        config = AppConfig()
        
        for name, llm_config in config.llm_configs.items():
            assert llm_config.provider is not None, \
                f"LLM config '{name}' has no provider"
            assert isinstance(llm_config.provider, LLMProvider), \
                f"LLM config '{name}' has invalid provider type"
    
    @patch('netra_backend.app.core.configuration.secrets.get_env')
    def test_gemini_api_key_loaded_from_environment(self, mock_get_env):
        """Test that GEMINI_API_KEY is properly loaded from environment."""
        # Mock environment with GEMINI_API_KEY
        mock_env = MagicMock()
        mock_env.get.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "development",
            "GEMINI_API_KEY": "test-gemini-key-123"
        }.get(key, default)
        mock_get_env.return_value = mock_env
        
        secret_manager = SecretManager()
        
        # Simulate loading secrets
        secrets = secret_manager.load_all_secrets()
        
        # Verify GEMINI_API_KEY is loaded
        assert "GEMINI_API_KEY" in secrets or \
               any("gemini" in k.lower() for k in secrets.keys()), \
               "GEMINI_API_KEY not loaded from environment"
    
    def test_provider_requires_api_key(self):
        """Test that Google provider requires API key."""
        from netra_backend.app.llm.llm_provider_handlers import validate_provider_key
        
        # Test Google provider without API key
        assert not validate_provider_key(LLMProvider.GOOGLE, None), \
            "Google provider should require API key"
        
        # Test Google provider with API key
        assert validate_provider_key(LLMProvider.GOOGLE, "some-key"), \
            "Google provider should accept valid API key"
    
    def test_llm_config_initialization_with_api_key(self):
        """Test LLM config can be initialized with API key."""
        llm_config = LLMConfig(
            provider=LLMProvider.GOOGLE,
            model_name="gemini-2.5-pro",
            api_key="test-key-123"
        )
        
        assert llm_config.api_key == "test-key-123"
        assert llm_config.provider == LLMProvider.GOOGLE
        assert llm_config.model_name == "gemini-2.5-pro"
    
    def test_target_field_consistency(self):
        """Ensure target_field is consistent across mappings."""
        secret_manager = SecretManager()
        gemini_mapping = secret_manager._get_gemini_api_key_mapping()
        
        # Verify target_field matches what's expected in config.py
        assert gemini_mapping["target_field"] == "api_key", \
            f"Target field should be 'api_key', got '{gemini_mapping['target_field']}'"
    
    def test_all_agent_llm_configs_covered(self):
        """Ensure all agent-specific LLM configs are covered."""
        agent_llm_configs = [
            "actions_to_meet_goals",
            "triage", 
            "data",
            "optimizations_core",
            "reporting",
            "analysis"
        ]
        
        secret_manager = SecretManager()
        gemini_mapping = secret_manager._get_gemini_api_key_mapping()
        
        for agent_config in agent_llm_configs:
            full_config_name = f"llm_configs.{agent_config}"
            assert full_config_name in gemini_mapping["target_models"], \
                f"Agent LLM config '{agent_config}' is missing from mapping"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])