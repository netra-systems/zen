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
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {
                'anthropic-claude-3-sonnet': {}, 'gpt-4': {}
            }
            mock_settings.environment = "development"
            
            await checker.check_llm_providers()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == True
            assert "2 LLM providers configured" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_partial_failure(self, mock_app, checker):
        """Test LLM providers check with some providers failing."""
        llm_manager = mock_app.state.llm_manager
        
        def get_llm_side_effect(name):
            if name == 'gpt-4':
                raise Exception("API key missing")
            return Mock()
        
        llm_manager.get_llm = Mock(side_effect=get_llm_side_effect)
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {
                'anthropic-claude-3-sonnet': {}, 'gpt-4': {}
            }
            mock_settings.environment = "development"
            
            await checker.check_llm_providers()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == True
            assert "1 available, 1 failed" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_all_failed(self, mock_app, checker):
        """Test LLM providers check with all providers failing."""
        llm_manager = mock_app.state.llm_manager
        llm_manager.get_llm = Mock(side_effect=Exception("No providers available"))
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {'anthropic-claude-3-sonnet': {}}
            mock_settings.environment = "development"
            
            await checker.check_llm_providers()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == False
            assert "No LLM providers available" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_critical_provider_not_initialized(self, mock_app, checker):
        """Test LLM providers check with critical provider returning None."""
        llm_manager = mock_app.state.llm_manager
        llm_manager.get_llm = Mock(return_value=None)
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {'anthropic-claude-3-opus': {}}
            mock_settings.environment = "development"
            
            await checker.check_llm_providers()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == False
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_exception(self, mock_app, checker):
        """Test LLM providers check with unexpected exception."""
        mock_app.state.llm_manager = None
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "production"
            
            await checker.check_llm_providers()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == False
            assert checker.results[0].critical == True