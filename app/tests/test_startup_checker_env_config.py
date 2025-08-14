"""Tests for StartupChecker environment and configuration checks."""

import pytest
from unittest.mock import patch

from app.startup_checks import StartupChecker
from app.tests.helpers.startup_check_helpers import (
    create_mock_app, setup_env_vars_production, setup_env_vars_development,
    clear_required_env_vars, clear_optional_env_vars
)


class TestStartupCheckerEnvConfig:
    """Test StartupChecker environment and configuration checks."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state."""
        return create_mock_app()
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance."""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_dev_mode(self, checker, monkeypatch):
        """Test environment variable check in development mode."""
        setup_env_vars_development(monkeypatch)
        clear_required_env_vars(monkeypatch)
        
        await checker.check_environment_variables()
        
        assert len(checker.results) == 1
        assert checker.results[0].success == True
        assert "Development mode" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_production_missing(self, checker, monkeypatch):
        """Test environment variable check in production with missing required vars."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        clear_required_env_vars(monkeypatch)
        
        await checker.check_environment_variables()
        
        assert len(checker.results) == 1
        assert checker.results[0].success == False
        assert "Missing required" in checker.results[0].message
        assert checker.results[0].critical == True
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_with_optional(self, checker, monkeypatch):
        """Test environment variable check with optional variables missing."""
        setup_env_vars_production(monkeypatch)
        clear_optional_env_vars(monkeypatch)
        
        await checker.check_environment_variables()
        
        assert len(checker.results) == 1
        assert checker.results[0].success == True
        assert "Optional missing" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_configuration_success(self, checker):
        """Test configuration validation success."""
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.database_url = "postgresql://localhost/test"
            mock_settings.secret_key = "a" * 32
            mock_settings.environment = "development"
            
            await checker.check_configuration()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == True
    
    @pytest.mark.asyncio
    async def test_check_configuration_missing_database(self, checker):
        """Test configuration validation with missing database URL."""
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.database_url = None
            
            await checker.check_configuration()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == False
            assert "DATABASE_URL" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_configuration_short_secret_production(self, checker):
        """Test configuration validation with short secret key in production."""
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.database_url = "postgresql://localhost/test"
            mock_settings.secret_key = "short"
            mock_settings.environment = "production"
            
            await checker.check_configuration()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == False
            assert "SECRET_KEY" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_configuration_invalid_environment(self, checker):
        """Test configuration validation with invalid environment."""
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.database_url = "postgresql://localhost/test"
            mock_settings.secret_key = "a" * 32
            mock_settings.environment = "invalid"
            
            await checker.check_configuration()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == False
            assert "Invalid environment" in checker.results[0].message