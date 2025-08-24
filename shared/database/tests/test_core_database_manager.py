"""
Tests for CoreDatabaseManager shared utility

This test suite validates the shared database URL handling functionality
to ensure consistent behavior across all services.
"""

import os
import pytest
from unittest.mock import patch

from shared.database.core_database_manager import CoreDatabaseManager


class TestCoreDatabaseManager:
    """Test cases for CoreDatabaseManager"""
    
    def test_normalize_postgres_url_converts_postgres_scheme(self):
        """Test postgres:// to postgresql:// conversion"""
        url = "postgres://user:pass@host:5432/db"
        result = CoreDatabaseManager.normalize_postgres_url(url)
        assert result == "postgresql://user:pass@host:5432/db"
    
    def test_normalize_postgres_url_strips_async_driver(self):
        """Test async driver prefix removal"""
        url = "postgresql+asyncpg://user:pass@host:5432/db"
        result = CoreDatabaseManager.normalize_postgres_url(url)
        assert result == "postgresql://user:pass@host:5432/db"
    
    def test_normalize_postgres_url_handles_empty_string(self):
        """Test handling of empty URL"""
        result = CoreDatabaseManager.normalize_postgres_url("")
        assert result == ""
    
    def test_normalize_postgres_url_handles_none(self):
        """Test handling of None URL"""
        result = CoreDatabaseManager.normalize_postgres_url(None)
        assert result is None
    
    def test_is_cloud_sql_connection_detects_cloudsql(self):
        """Test Cloud SQL connection detection"""
        url = "postgresql://user:pass@host/cloudsql/project:region:instance/db"
        assert CoreDatabaseManager.is_cloud_sql_connection(url) is True
    
    def test_is_cloud_sql_connection_rejects_normal_url(self):
        """Test normal connection rejection"""
        url = "postgresql://user:pass@host:5432/db"
        assert CoreDatabaseManager.is_cloud_sql_connection(url) is False
    
    def test_is_cloud_sql_connection_handles_empty_url(self):
        """Test empty URL handling"""
        assert CoreDatabaseManager.is_cloud_sql_connection("") is False
        assert CoreDatabaseManager.is_cloud_sql_connection(None) is False
    
    def test_convert_ssl_params_for_asyncpg_cloud_sql(self):
        """Test SSL parameter removal for Cloud SQL"""
        url = "postgresql://user:pass@host/cloudsql/project:region:instance/db?sslmode=require&ssl=disable"
        result = CoreDatabaseManager.convert_ssl_params_for_asyncpg(url)
        assert "sslmode=" not in result
        assert "ssl=" not in result
        assert result == "postgresql://user:pass@host/cloudsql/project:region:instance/db"
    
    def test_convert_ssl_params_for_asyncpg_normal_connection(self):
        """Test SSL parameter conversion for normal connections"""
        url = "postgresql://user:pass@host:5432/db?sslmode=require"
        result = CoreDatabaseManager.convert_ssl_params_for_asyncpg(url)
        assert result == "postgresql://user:pass@host:5432/db?ssl=require"
    
    def test_convert_ssl_params_for_asyncpg_removes_unknown_sslmode(self):
        """Test removal of unknown sslmode parameters"""
        url = "postgresql://user:pass@host:5432/db?sslmode=prefer"
        result = CoreDatabaseManager.convert_ssl_params_for_asyncpg(url)
        assert "sslmode=" not in result
        assert result == "postgresql://user:pass@host:5432/db"
    
    def test_convert_ssl_params_for_psycopg2_cloud_sql(self):
        """Test SSL parameter removal for Cloud SQL psycopg2"""
        url = "postgresql://user:pass@host/cloudsql/project:region:instance/db?ssl=require"
        result = CoreDatabaseManager.convert_ssl_params_for_psycopg2(url)
        assert "ssl=" not in result
        assert "sslmode=" not in result
        assert result == "postgresql://user:pass@host/cloudsql/project:region:instance/db"
    
    def test_convert_ssl_params_for_psycopg2_normal_connection(self):
        """Test SSL parameter conversion for psycopg2"""
        url = "postgresql://user:pass@host:5432/db?ssl=require"
        result = CoreDatabaseManager.convert_ssl_params_for_psycopg2(url)
        assert result == "postgresql://user:pass@host:5432/db?sslmode=require"
    
    def test_format_url_for_async_driver(self):
        """Test async driver formatting"""
        url = "postgresql://user:pass@host:5432/db?sslmode=require"
        result = CoreDatabaseManager.format_url_for_async_driver(url)
        assert result.startswith("postgresql+asyncpg://")
        assert "ssl=require" in result
        assert "sslmode=" not in result
    
    def test_format_url_for_sync_driver(self):
        """Test sync driver formatting"""
        url = "postgresql+asyncpg://user:pass@host:5432/db?ssl=require"
        result = CoreDatabaseManager.format_url_for_sync_driver(url)
        assert result.startswith("postgresql://")
        assert "postgresql+asyncpg://" not in result
        assert "sslmode=require" in result
        assert "ssl=" not in result
    
    def test_get_database_url_from_env_success(self):
        """Test successful environment variable retrieval"""
        test_url = "postgresql://test:test@localhost:5432/test"
        with patch.dict(os.environ, {"TEST_DATABASE_URL": test_url}):
            result = CoreDatabaseManager.get_database_url_from_env("TEST_DATABASE_URL")
            assert result == test_url
    
    def test_get_database_url_from_env_missing(self):
        """Test missing environment variable handling"""
        with pytest.raises(ValueError, match="TEST_MISSING_URL environment variable not set"):
            CoreDatabaseManager.get_database_url_from_env("TEST_MISSING_URL")
    
    def test_validate_database_url_valid_postgresql(self):
        """Test validation of valid PostgreSQL URLs"""
        valid_urls = [
            "postgresql://user:pass@host:5432/db",
            "postgres://user:pass@host:5432/db",
            "postgresql+asyncpg://user:pass@host:5432/db"
        ]
        for url in valid_urls:
            assert CoreDatabaseManager.validate_database_url(url) is True
    
    def test_validate_database_url_invalid_schemes(self):
        """Test validation rejection of invalid schemes"""
        invalid_urls = [
            "mysql://user:pass@host:3306/db",
            "sqlite:///test.db",
            "http://example.com"
        ]
        for url in invalid_urls:
            assert CoreDatabaseManager.validate_database_url(url) is False
    
    def test_validate_database_url_empty_or_none(self):
        """Test validation of empty or None URLs"""
        assert CoreDatabaseManager.validate_database_url("") is False
        assert CoreDatabaseManager.validate_database_url(None) is False
    
    def test_get_environment_type_from_environment_var(self):
        """Test environment type detection from ENVIRONMENT variable"""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            result = CoreDatabaseManager.get_environment_type()
            assert result == "staging"
    
    def test_get_environment_type_from_testing_flag(self):
        """Test environment type detection from TESTING flag"""
        with patch.dict(os.environ, {"TESTING": "true"}, clear=True):
            result = CoreDatabaseManager.get_environment_type()
            assert result == "test"
    
    def test_get_environment_type_defaults_to_development(self):
        """Test default environment type"""
        with patch.dict(os.environ, {}, clear=True):
            result = CoreDatabaseManager.get_environment_type()
            assert result == "development"
    
    def test_get_default_url_for_environment_development(self):
        """Test default URL for development environment"""
        result = CoreDatabaseManager.get_default_url_for_environment("development")
        assert "localhost:5432" in result
        assert "netra" in result
    
    def test_get_default_url_for_environment_test(self):
        """Test default URL for test environment"""
        result = CoreDatabaseManager.get_default_url_for_environment("test")
        assert result == "sqlite:///:memory:"
    
    def test_get_default_url_for_environment_staging(self):
        """Test default URL for staging environment"""
        result = CoreDatabaseManager.get_default_url_for_environment("staging")
        assert "netra_staging" in result
    
    def test_strip_driver_prefixes(self):
        """Test driver prefix stripping"""
        test_cases = [
            ("postgresql+asyncpg://host/db", "postgresql://host/db"),
            ("postgres+asyncpg://host/db", "postgresql://host/db"),
            ("postgres://host/db", "postgresql://host/db"),
            ("postgresql://host/db", "postgresql://host/db")
        ]
        for input_url, expected in test_cases:
            result = CoreDatabaseManager.strip_driver_prefixes(input_url)
            assert result == expected
    
    def test_has_mixed_ssl_params_detects_mixed(self):
        """Test detection of mixed SSL parameters"""
        url = "postgresql://host/db?ssl=require&sslmode=disable"
        assert CoreDatabaseManager.has_mixed_ssl_params(url) is True
    
    def test_has_mixed_ssl_params_rejects_single_param(self):
        """Test rejection of single SSL parameter"""
        test_cases = [
            "postgresql://host/db?ssl=require",
            "postgresql://host/db?sslmode=require",
            "postgresql://host/db"
        ]
        for url in test_cases:
            assert CoreDatabaseManager.has_mixed_ssl_params(url) is False
    
    def test_has_mixed_ssl_params_handles_empty_url(self):
        """Test empty URL handling for mixed SSL params"""
        assert CoreDatabaseManager.has_mixed_ssl_params("") is False
        assert CoreDatabaseManager.has_mixed_ssl_params(None) is False