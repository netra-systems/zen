"""
Unit tests for database URL validation and configuration.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Reliability
- Value Impact: Prevents database connectivity failures in production
- Strategic Impact: Ensures consistent database configuration across environments

Tests validate:
1. Database URL is properly loaded in all environments
2. None database_url is handled gracefully
3. Health checks handle missing database configuration
4. DatabaseURLBuilder is called correctly
5. Critical configuration errors are raised appropriately
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Optional
import os

from netra_backend.app.schemas.config import (
    AppConfig,
    DevelopmentConfig,
    StagingConfig,
    ProductionConfig,
    NetraTestingConfig
)


class TestDatabaseURLValidation:
    """Test suite for database URL validation and handling."""
    
    def test_appconfig_database_url_none_by_default(self):
        """Test that AppConfig has database_url as None by default."""
        config = AppConfig()
        assert config.database_url is None
    
    def test_development_config_loads_database_url(self):
        """Test that DevelopmentConfig properly loads database URL."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {
                'ENVIRONMENT': 'development',
                'DATABASE_URL': 'postgresql://user:pass@localhost/devdb'
            }
            
            config = DevelopmentConfig()
            assert config.database_url is not None
            assert 'postgresql' in config.database_url
    
    def test_staging_config_loads_database_url_from_parts(self):
        """Test that StagingConfig constructs database URL from individual parts."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {
                'ENVIRONMENT': 'staging',
                'POSTGRES_HOST': 'staging-db.example.com',
                'POSTGRES_PORT': '5432',
                'POSTGRES_USER': 'staging_user',
                'POSTGRES_PASSWORD': 'staging_pass',
                'POSTGRES_DB': 'staging_db'
            }
            
            config = StagingConfig()
            assert config.database_url is not None
            assert 'staging-db.example.com' in config.database_url
            assert 'staging_user' in config.database_url
            assert 'staging_db' in config.database_url
    
    def test_staging_config_raises_without_database_config(self):
        """Test that StagingConfig raises error when database config is missing."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {
                'ENVIRONMENT': 'staging'
                # Missing all database configuration
            }
            
            with pytest.raises(ValueError, match="DatabaseURLBuilder failed to construct URL"):
                StagingConfig()
    
    def test_production_config_loads_database_url(self):
        """Test that ProductionConfig properly loads database URL."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {
                'ENVIRONMENT': 'production',
                'POSTGRES_HOST': 'prod-db.example.com',
                'POSTGRES_PORT': '5432',
                'POSTGRES_USER': 'prod_user',
                'POSTGRES_PASSWORD': 'prod_pass',
                'POSTGRES_DB': 'prod_db'
            }
            
            config = ProductionConfig()
            assert config.database_url is not None
            assert 'prod-db.example.com' in config.database_url


class TestHealthCheckDatabaseValidation:
    """Test suite for health check database validation."""
    
    @pytest.mark.asyncio
    async def test_check_postgres_connection_handles_none_url(self):
        """Test that _check_postgres_connection handles None database_url gracefully."""
        from netra_backend.app.routes.health import _check_postgres_connection
        
        mock_db = AsyncMock()
        mock_config = MagicMock()
        mock_config.database_url = None
        
        with patch('netra_backend.app.routes.health.unified_config_manager.get_config', return_value=mock_config):
            with patch('shared.isolated_environment.get_env') as mock_env:
                # Test in testing environment - should not raise
                mock_env.return_value.get.return_value = 'testing'
                
                # Should not raise in testing environment
                await _check_postgres_connection(mock_db)
                mock_db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_postgres_connection_raises_in_staging_with_none(self):
        """Test that _check_postgres_connection raises in staging with None database_url."""
        from netra_backend.app.routes.health import _check_postgres_connection
        
        mock_db = AsyncMock()
        mock_config = MagicMock()
        mock_config.database_url = None
        
        with patch('netra_backend.app.routes.health.unified_config_manager.get_config', return_value=mock_config):
            with patch('shared.isolated_environment.get_env') as mock_env:
                # Test in staging environment - should raise
                mock_env.return_value.get.return_value = 'staging'
                
                with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
                    await _check_postgres_connection(mock_db)
    
    @pytest.mark.asyncio
    async def test_check_postgres_connection_executes_with_valid_url(self):
        """Test that _check_postgres_connection executes query with valid URL."""
        from netra_backend.app.routes.health import _check_postgres_connection
        from sqlalchemy import text
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_db.execute.return_value = mock_result
        
        mock_config = MagicMock()
        mock_config.database_url = 'postgresql://user:pass@localhost/testdb'
        
        with patch('netra_backend.app.routes.health.unified_config_manager.get_config', return_value=mock_config):
            await _check_postgres_connection(mock_db)
            
            # Verify that SELECT 1 was executed
            mock_db.execute.assert_called_once()
            call_args = mock_db.execute.call_args[0][0]
            assert str(call_args) == 'SELECT 1'
    
    @pytest.mark.asyncio
    async def test_check_postgres_connection_skips_mock_database(self):
        """Test that _check_postgres_connection skips execution for mock database."""
        from netra_backend.app.routes.health import _check_postgres_connection
        
        mock_db = AsyncMock()
        mock_config = MagicMock()
        mock_config.database_url = 'postgresql+mock://mockuser:mockpass@mockhost/mockdb'
        
        with patch('netra_backend.app.routes.health.unified_config_manager.get_config', return_value=mock_config):
            await _check_postgres_connection(mock_db)
            
            # Should not execute query for mock database
            mock_db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_readiness_check_handles_database_errors_gracefully(self):
        """Test that readiness check properly handles database connection errors."""
        from netra_backend.app.routes.health import _check_readiness_status
        from fastapi import HTTPException
        
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Connection failed")
        
        mock_config = MagicMock()
        mock_config.database_url = 'postgresql://user:pass@localhost/testdb'
        mock_config.environment = 'staging'
        
        with patch('netra_backend.app.routes.health.unified_config_manager.get_config', return_value=mock_config):
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env.return_value.get.return_value = 'false'  # CLICKHOUSE_REQUIRED
                
                with pytest.raises(HTTPException) as exc_info:
                    await _check_readiness_status(mock_db)
                
                assert exc_info.value.status_code == 503
                assert "Core database unavailable" in str(exc_info.value.detail)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])