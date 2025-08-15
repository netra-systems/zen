"""
LLM tests for app/startup_checks.py - LLM provider checks

This module tests LLM provider connectivity and configuration.
Part of the refactored test suite to maintain 300-line limit per file.
"""

import os
import sys
from unittest.mock import MagicMock, patch
import pytest

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupChecker


class TestLLMProviderChecks:
    """Test LLM provider connectivity checks"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with LLM manager"""
        app = MagicMock()
        app.state.llm_manager = MagicMock()
        return app
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance"""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_success(self, checker, mock_app):
        """Test LLM providers check success"""
        self._setup_successful_llm_manager(mock_app)
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            self._setup_llm_settings(mock_settings)
            result = await checker.service_checker.check_llm_providers()
        
        self._verify_llm_success(result)
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_partial_failure(self, checker, mock_app):
        """Test LLM providers check with some failures"""
        self._setup_partial_failure_llm_manager(mock_app)
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            self._setup_llm_settings(mock_settings)
            result = await checker.service_checker.check_llm_providers()
        
        self._verify_llm_partial_failure(result)
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_all_failed(self, checker, mock_app):
        """Test LLM providers check with all providers failing"""
        self._setup_failed_llm_manager(mock_app)
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            self._setup_single_llm_settings(mock_settings)
            result = await checker.service_checker.check_llm_providers()
        
        self._verify_llm_all_failed(result)
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_exception(self, checker, mock_app):
        """Test LLM providers check with unexpected exception"""
        del mock_app.state.llm_manager
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.environment = "production"
            result = await checker.service_checker.check_llm_providers()
        
        self._verify_llm_exception(result)
    
    def _setup_successful_llm_manager(self, mock_app):
        """Setup successful LLM manager"""
        mock_llm_manager = mock_app.state.llm_manager
        mock_llm_manager.get_llm.return_value = MagicMock()
    
    def _setup_partial_failure_llm_manager(self, mock_app):
        """Setup LLM manager with partial failures"""
        mock_llm_manager = mock_app.state.llm_manager
        
        def mock_get_llm(name):
            if name == 'anthropic-claude-3-sonnet':
                return MagicMock()
            else:
                raise Exception("API key missing")
        
        mock_llm_manager.get_llm.side_effect = mock_get_llm
    
    def _setup_failed_llm_manager(self, mock_app):
        """Setup failed LLM manager"""
        mock_llm_manager = mock_app.state.llm_manager
        mock_llm_manager.get_llm.side_effect = Exception("API key missing")
    
    def _setup_llm_settings(self, mock_settings):
        """Setup LLM settings with multiple providers"""
        mock_settings.llm_configs = {
            'anthropic-claude-3-sonnet': {},
            'anthropic-claude-3-opus': {}
        }
    
    def _setup_single_llm_settings(self, mock_settings):
        """Setup LLM settings with single provider"""
        mock_settings.llm_configs = {
            'anthropic-claude-3-sonnet': {}
        }
    
    def _verify_llm_success(self, result):
        """Verify successful LLM result"""
        assert result.name == "llm_providers"
        assert result.success is True
        assert "2 LLM providers configured" in result.message
    
    def _verify_llm_partial_failure(self, result):
        """Verify partial LLM failure result"""
        assert result.name == "llm_providers"
        assert result.success is True
        assert "1 available, 1 failed" in result.message
    
    def _verify_llm_all_failed(self, result):
        """Verify all LLM failed result"""
        assert result.name == "llm_providers"
        assert result.success is False
        assert "No LLM providers available" in result.message
        assert result.critical is True
    
    def _verify_llm_exception(self, result):
        """Verify LLM exception result"""
        assert result.name == "llm_providers"
        assert result.success is False
        assert "LLM check failed" in result.message
        assert result.critical is True