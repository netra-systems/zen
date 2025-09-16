"""Test for LLM Manager method fix.

This test verifies that the get_llm_config method exists and works correctly
as an alias for get_config, fixing the health check warning.
"""

import pytest
import asyncio
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.llm.llm_manager import LLMManager


class TestLLMManagerMethodFix:
    """Test that the LLM manager has all required methods."""
    
    @pytest.mark.asyncio
    async def test_llm_manager_has_required_methods(self):
        """Verify LLM manager has both ask_llm and get_llm_config methods."""
        manager = LLMManager()
        
        # Check that required methods exist
        assert hasattr(manager, 'ask_llm'), "LLM manager missing ask_llm method"
        assert hasattr(manager, 'get_llm_config'), "LLM manager missing get_llm_config method"
        assert hasattr(manager, 'get_config'), "LLM manager missing get_config method"
        
        # Verify methods are callable
        assert callable(getattr(manager, 'ask_llm'))
        assert callable(getattr(manager, 'get_llm_config'))
        assert callable(getattr(manager, 'get_config'))
    
    @pytest.mark.asyncio
    async def test_get_llm_config_is_alias_for_get_config(self):
        """Verify get_llm_config returns the same result as get_config."""
        manager = LLMManager()
        
        # Mock the config
        mock_config = MagicNone  # TODO: Use real service instance
        mock_config.llm_configs = {
            "default": {"model": "test-model", "provider": "test"},
            "custom": {"model": "custom-model", "provider": "custom"}
        }
        manager._config = mock_config
        manager._initialized = True
        
        # Test default config
        config1 = await manager.get_config("default")
        config2 = await manager.get_llm_config("default")
        assert config1 == config2
        assert config1 == {"model": "test-model", "provider": "test"}
        
        # Test custom config
        config3 = await manager.get_config("custom")
        config4 = await manager.get_llm_config("custom")
        assert config3 == config4
        assert config3 == {"model": "custom-model", "provider": "custom"}
        
        # Test non-existent config
        config5 = await manager.get_config("nonexistent")
        config6 = await manager.get_llm_config("nonexistent")
        assert config5 == config6
        assert config5 is None
    
    @pytest.mark.asyncio
    async def test_get_llm_config_default_parameter(self):
        """Verify get_llm_config uses 'default' as default parameter."""
        manager = LLMManager()
        
        # Mock the config
        mock_config = MagicNone  # TODO: Use real service instance
        mock_config.llm_configs = {
            "default": {"model": "default-model", "provider": "default"}
        }
        manager._config = mock_config
        manager._initialized = True
        
        # Call without parameter (should use "default")
        config = await manager.get_llm_config()
        assert config == {"model": "default-model", "provider": "default"}
    
    @pytest.mark.asyncio
    async def test_health_check_validates_methods(self):
        """Simulate the health check validation to ensure it passes."""
        from netra_backend.app.startup_health_checks import StartupHealthChecker, ServiceStatus
        
        # Create a mock app with LLM manager
        mock_app = MagicNone  # TODO: Use real service instance
        mock_app.state.llm_manager = LLMManager()
        mock_app.state.llm_manager._initialized = True
        mock_app.state.llm_manager.llm_configs = {"default": {}}
        
        # Run health check
        checker = StartupHealthChecker(mock_app)
        result = await checker.check_llm_manager()
        
        # Should not be DEGRADED due to missing methods
        assert result.status != ServiceStatus.DEGRADED or "missing methods" not in result.message.lower()
        
        # If it's degraded, it should be for a different reason
        if result.status == ServiceStatus.DEGRADED:
            assert "get_llm_config" not in result.message