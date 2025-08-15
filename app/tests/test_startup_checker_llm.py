"""Tests for StartupChecker LLM provider checks."""

import pytest
from unittest.mock import patch, Mock

from app.startup_checks import StartupChecker
from app.tests.helpers.startup_check_helpers import create_mock_app


class TestStartupCheckerLLM:
    """Test StartupChecker LLM provider checks."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state."""
        return create_mock_app()
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance."""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_all_success(self, mock_app, checker):
        """Test LLM providers check with all providers available."""
        llm_manager = mock_app.state.llm_manager
        llm_manager.get_llm = Mock(return_value=Mock())
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.llm_configs = {
                'anthropic-claude-3-sonnet': {}, 'gpt-4': {}
            }
            mock_settings.environment = "development"
            
            result = await checker.service_checker.check_llm_providers()
            
            assert result.success == True
            assert "2 LLM providers configured" in result.message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_partial_failure(self, mock_app, checker):
        """Test LLM providers check with some providers failing."""
        from app.schemas.llm_types import LLMProvider
        llm_manager = mock_app.state.llm_manager
        
        def get_llm_side_effect(name):
            if name == 'google-gemini':
                raise Exception("API key missing")
            return Mock()
        
        llm_manager.get_llm = Mock(side_effect=get_llm_side_effect)
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            # Use a GOOGLE provider to trigger failed_providers logic
            mock_configs = Mock()
            mock_configs.__iter__ = Mock(return_value=iter(['anthropic-claude-3-sonnet', 'google-gemini']))
            mock_configs.get = Mock(side_effect=lambda k: 
                Mock(provider=LLMProvider.ANTHROPIC) if k == 'anthropic-claude-3-sonnet' 
                else Mock(provider=LLMProvider.GOOGLE) if k == 'google-gemini' 
                else None)
            mock_settings.llm_configs = mock_configs
            mock_settings.environment = "development"
            
            result = await checker.service_checker.check_llm_providers()
            
            assert result.success == True
            assert "1 available, 1 failed" in result.message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_all_failed(self, mock_app, checker):
        """Test LLM providers check with all providers failing."""
        llm_manager = mock_app.state.llm_manager
        llm_manager.get_llm = Mock(side_effect=Exception("No providers available"))
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.llm_configs = {'anthropic-claude-3-sonnet': {}}
            mock_settings.environment = "development"
            
            result = await checker.service_checker.check_llm_providers()
            
            assert result.success == False
            assert "No LLM providers available" in result.message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_critical_provider_not_initialized(self, mock_app, checker):
        """Test LLM providers check with critical provider returning None."""
        llm_manager = mock_app.state.llm_manager
        llm_manager.get_llm = Mock(return_value=None)
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.llm_configs = {'anthropic-claude-3-opus': {}}
            mock_settings.environment = "development"
            
            result = await checker.service_checker.check_llm_providers()
            
            assert result.success == False
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_exception(self, mock_app, checker):
        """Test LLM providers check with unexpected exception."""
        mock_app.state.llm_manager = None
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.environment = "production"
            
            result = await checker.service_checker.check_llm_providers()
            
            assert result.success == False
            assert result.critical == True