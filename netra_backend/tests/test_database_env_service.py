"""Tests for Database Environment Service"""

import sys
from pathlib import Path

from test_framework import setup_test_path

from unittest.mock import MagicMock, patch

import pytest

from netra_backend.app.services.database_env_service import (
    DatabaseEnvironmentValidator,
    validate_database_environment,
)

class TestDatabaseEnvironmentValidator:
    
    def test_keyword_constants(self):
        """Test that environment keywords are properly defined"""
        assert "prod" in DatabaseEnvironmentValidator.PROD_KEYWORDS
        assert "production" in DatabaseEnvironmentValidator.PROD_KEYWORDS
        assert "test" in DatabaseEnvironmentValidator.TEST_KEYWORDS
        assert "dev" in DatabaseEnvironmentValidator.DEV_KEYWORDS
    
    def test_validate_production_database_success(self):
        """Test production database validation passes with valid URL"""
        mock_settings = MagicMock()
        mock_settings.environment = "production"
        mock_settings.database_url = "postgresql://user:pass@prod-server/app_prod"
        
        with patch('app.services.database_env_service.settings', mock_settings):
            # Should not raise any exception
            DatabaseEnvironmentValidator.validate_database_environment()
    
    def test_validate_production_database_failure_with_test_keyword(self):
        """Test production database validation fails with test keyword"""
        mock_settings = MagicMock()
        mock_settings.environment = "production"
        mock_settings.database_url = "postgresql://user:pass@server/app_test"
        
        with patch('app.services.database_env_service.settings', mock_settings):
            with pytest.raises(ValueError, match="Production environment cannot use database with 'test'"):
                DatabaseEnvironmentValidator.validate_database_environment()
    
    def test_validate_production_database_failure_with_dev_keyword(self):
        """Test production database validation fails with dev keyword"""
        mock_settings = MagicMock()
        mock_settings.environment = "production"  
        mock_settings.database_url = "postgresql://user:pass@server/app_dev"
        
        with patch('app.services.database_env_service.settings', mock_settings):
            with pytest.raises(ValueError, match="Production environment cannot use database with 'dev'"):
                DatabaseEnvironmentValidator.validate_database_environment()
    
    def test_validate_testing_database_success(self):
        """Test testing database validation passes with valid URL"""
        mock_settings = MagicMock()
        mock_settings.environment = "testing"
        mock_settings.database_url = "postgresql://user:pass@localhost/app_test"
        
        with patch('app.services.database_env_service.settings', mock_settings):
            # Should not raise any exception
            DatabaseEnvironmentValidator.validate_database_environment()
    
    def test_validate_testing_database_failure_with_prod_keyword(self):
        """Test testing database validation fails with production keyword"""
        mock_settings = MagicMock()
        mock_settings.environment = "testing"
        mock_settings.database_url = "postgresql://user:pass@server/app_prod"
        
        with patch('app.services.database_env_service.settings', mock_settings):
            with pytest.raises(ValueError, match="Testing environment cannot use production database"):
                DatabaseEnvironmentValidator.validate_database_environment()
    
    def test_validate_development_database_success(self):
        """Test development database validation passes with valid URL"""
        mock_settings = MagicMock()
        mock_settings.environment = "development"
        mock_settings.database_url = "postgresql://user:pass@localhost/app_dev"
        
        with patch('app.services.database_env_service.settings', mock_settings):
            # Should not raise any exception
            DatabaseEnvironmentValidator.validate_database_environment()
    
    def test_validate_development_database_warning_with_prod_keyword(self):
        """Test development database validation warns with production keyword"""
        mock_settings = MagicMock()
        mock_settings.environment = "development"
        mock_settings.database_url = "postgresql://user:pass@server/app_prod"
        
        with patch('app.services.database_env_service.settings', mock_settings):
            with patch('app.services.database_env_service.logger') as mock_logger:
                DatabaseEnvironmentValidator.validate_database_environment()
                mock_logger.warning.assert_called_once()
                assert "prod" in mock_logger.warning.call_args[0][0]
    
    def test_validate_database_environment_no_url(self):
        """Test validation when no database URL is configured"""
        mock_settings = MagicMock()
        mock_settings.environment = "development"
        mock_settings.database_url = None
        
        with patch('app.services.database_env_service.settings', mock_settings):
            with patch('app.services.database_env_service.logger') as mock_logger:
                DatabaseEnvironmentValidator.validate_database_environment()
                mock_logger.warning.assert_called_with("No database URL configured")
    
    def test_validate_database_environment_convenience_function(self):
        """Test the convenience function calls the validator"""
        with patch.object(DatabaseEnvironmentValidator, 'validate_database_environment') as mock_validate:
            validate_database_environment()
            mock_validate.assert_called_once()