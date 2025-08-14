"""
Individual method tests for app/startup_checks.py - Individual check methods

This module tests each individual check method in detail.
Part of the refactored test suite to maintain 300-line limit per file.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupChecker
from app.db.models_postgres import Assistant


class TestEnvironmentVariableChecks:
    """Test environment variable check methods"""
    
    @pytest.fixture
    def checker(self):
        """Create a StartupChecker instance"""
        mock_app = MagicMock()
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_dev_mode(self, checker, monkeypatch):
        """Test environment variable check in development mode"""
        monkeypatch.setenv('ENVIRONMENT', 'development')
        
        await checker.check_environment_variables()
        
        result = self._get_first_result(checker)
        assert result.name == "environment_variables"
        assert result.success is True
        assert "Development mode" in result.message
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_production_missing_required(self, checker, monkeypatch):
        """Test environment variable check in production with missing required vars"""
        self._setup_production_missing_vars(monkeypatch)
        
        await checker.check_environment_variables()
        
        result = self._get_first_result(checker)
        self._verify_missing_required_vars(result)
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_with_optional_missing(self, checker, monkeypatch):
        """Test environment variable check with optional vars missing"""
        self._setup_production_with_optional_missing(monkeypatch)
        
        await checker.check_environment_variables()
        
        result = self._get_first_result(checker)
        self._verify_optional_missing_vars(result)
    
    def _get_first_result(self, checker):
        """Get the first result from checker"""
        assert len(checker.results) == 1
        return checker.results[0]
    
    def _setup_production_missing_vars(self, monkeypatch):
        """Setup production environment with missing required vars"""
        monkeypatch.setenv('ENVIRONMENT', 'production')
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.delenv('SECRET_KEY', raising=False)
    
    def _setup_production_with_optional_missing(self, monkeypatch):
        """Setup production with optional vars missing"""
        monkeypatch.setenv('ENVIRONMENT', 'production')
        monkeypatch.setenv('DATABASE_URL', 'postgres://test')
        monkeypatch.setenv('SECRET_KEY', 'test-secret')
        monkeypatch.delenv('REDIS_URL', raising=False)
        monkeypatch.delenv('CLICKHOUSE_URL', raising=False)
    
    def _verify_missing_required_vars(self, result):
        """Verify result for missing required variables"""
        assert result.name == "environment_variables"
        assert result.success is False
        assert "Missing required" in result.message
        assert result.critical is True
    
    def _verify_optional_missing_vars(self, result):
        """Verify result for missing optional variables"""
        assert result.name == "environment_variables"
        assert result.success is True
        assert "Optional missing" in result.message


class TestConfigurationChecks:
    """Test configuration check methods"""
    
    @pytest.fixture
    def checker(self):
        """Create a StartupChecker instance"""
        mock_app = MagicMock()
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_configuration_success(self, checker):
        """Test configuration check success"""
        mock_settings = self._create_valid_settings()
        
        with patch('app.startup_checks.settings', mock_settings):
            await checker.check_configuration()
        
        result = self._get_first_result(checker)
        self._verify_config_success(result)
    
    @pytest.mark.asyncio
    async def test_check_configuration_missing_database_url(self, checker):
        """Test configuration check with missing database URL"""
        mock_settings = self._create_settings_missing_db()
        
        with patch('app.startup_checks.settings', mock_settings):
            await checker.check_configuration()
        
        result = self._get_first_result(checker)
        self._verify_missing_database_url(result)
    
    @pytest.mark.asyncio
    async def test_check_configuration_short_secret_key_production(self, checker):
        """Test configuration check with short secret key in production"""
        mock_settings = self._create_settings_short_secret()
        
        with patch('app.startup_checks.settings', mock_settings):
            await checker.check_configuration()
        
        result = self._get_first_result(checker)
        self._verify_short_secret_key(result)
    
    @pytest.mark.asyncio
    async def test_check_configuration_invalid_environment(self, checker):
        """Test configuration check with invalid environment"""
        mock_settings = self._create_settings_invalid_env()
        
        with patch('app.startup_checks.settings', mock_settings):
            await checker.check_configuration()
        
        result = self._get_first_result(checker)
        self._verify_invalid_environment(result)
    
    def _get_first_result(self, checker):
        """Get the first result from checker"""
        assert len(checker.results) == 1
        return checker.results[0]
    
    def _create_valid_settings(self):
        """Create valid settings mock"""
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql://test"
        mock_settings.environment = "development"
        mock_settings.secret_key = "test-secret-key"
        return mock_settings
    
    def _create_settings_missing_db(self):
        """Create settings with missing database URL"""
        mock_settings = MagicMock()
        mock_settings.database_url = None
        return mock_settings
    
    def _create_settings_short_secret(self):
        """Create settings with short secret key"""
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql://test"
        mock_settings.environment = "production"
        mock_settings.secret_key = "short"
        return mock_settings
    
    def _create_settings_invalid_env(self):
        """Create settings with invalid environment"""
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql://test"
        mock_settings.environment = "invalid"
        mock_settings.secret_key = "a" * 32
        return mock_settings
    
    def _verify_config_success(self, result):
        """Verify successful configuration result"""
        assert result.name == "configuration"
        assert result.success is True
    
    def _verify_missing_database_url(self, result):
        """Verify missing database URL result"""
        assert result.name == "configuration"
        assert result.success is False
        assert "DATABASE_URL" in result.message
    
    def _verify_short_secret_key(self, result):
        """Verify short secret key result"""
        assert result.name == "configuration"
        assert result.success is False
        assert "SECRET_KEY" in result.message
    
    def _verify_invalid_environment(self, result):
        """Verify invalid environment result"""
        assert result.name == "configuration"
        assert result.success is False
        assert "Invalid environment" in result.message