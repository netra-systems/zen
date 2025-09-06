from shared.isolated_environment import IsolatedEnvironment
from test_framework.database.test_database_manager import TestDatabaseManager
from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Test to reproduce and fix the database health checker sslmode issue.

This test recreates the exact issue seen in GCP staging where the health checker
fails with "connect() got an unexpected keyword argument 'sslmode'" error.

Business Value Justification (BVJ):
    - Segment: Platform/Internal
- Business Goal: Database reliability and zero-downtime deployments
- Value Impact: Prevents production outages from SSL parameter misconfigurations
- Strategic Impact: Ensures consistent database connectivity across all environments
""""

import asyncio
import os
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from netra_backend.app.services.database.health_checker import ConnectionHealthChecker
from netra_backend.app.services.database.pool_metrics import ConnectionPoolMetrics
from netra_backend.app.db import postgres_core
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.db.postgres_core import get_converted_async_db_url


class TestDatabaseHealthCheckerSSLMode:
    """Test suite to reproduce and fix the sslmode parameter issue."""
    
    @pytest.mark.asyncio
    async def test_health_checker_fails_with_sslmode_in_url(self):
        """Reproduce the exact error from GCP staging: asyncpg doesn't understand sslmode."""
        # Simulate GCP staging environment URL with sslmode parameter
        staging_url_with_sslmode = "postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=require"
        
        # Create an engine with the problematic URL (simulating what happens in staging)
        with pytest.raises(Exception) as exc_info:
            # This should fail because asyncpg doesn't understand 'sslmode'
            test_engine = create_async_engine(
                staging_url_with_sslmode,
                pool_size=1,
                max_overflow=0
            )
            
            # Try to connect (this is where the error occurs)
            async with test_engine.connect() as conn:
                await conn.execute("SELECT 1")
        
        # Verify we get the expected error
        assert "sslmode" in str(exc_info.value).lower() or "unexpected keyword argument" in str(exc_info.value)
    
    @pytest.mark.asyncio 
    async def test_health_checker_with_unconverted_url_fails(self):
        """Test that health checker fails when engine has unconverted URL."""
        # Mock the engine with an unconverted URL
        # Mock: Generic component isolation for controlled unit testing
        mock_engine = AsyncMock()  # TODO: Use real service instance
        mock_engine.url = "postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=require"
        
        # Create a mock that simulates the exact error we see in staging
        # Mock: Generic component isolation for controlled unit testing
        mock_conn_context = AsyncMock()  # TODO: Use real service instance
        mock_conn_context.__aenter__.side_effect = TypeError("connect() got an unexpected keyword argument 'sslmode'")
        mock_conn_context.__aexit__.return_value = None
        mock_engine.connect.return_value = mock_conn_context
        
        # Patch postgres_core.async_engine to return our mock
        with patch.object(postgres_core, 'async_engine', mock_engine):
            metrics = ConnectionPoolMetrics()
            health_checker = ConnectionHealthChecker(metrics)
            
            # This should fail with the sslmode error
            result = await health_checker.perform_health_check()
            
            # Verify the health check detected the failure
            assert result["connectivity_test"]["status"] == "failed"
            assert "sslmode" in result["connectivity_test"]["error"]
    
    @pytest.mark.asyncio
    async def test_database_manager_converts_sslmode_to_ssl(self):
        """Test that DatabaseManager properly converts sslmode to ssl for asyncpg."""
        # Test with a URL containing sslmode (like from GCP)
        test_url = "postgresql://user:pass@host:5432/dbname?sslmode=require"
        
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            # Get the converted async URL
            async_url = get_converted_async_db_url()
            
            # Verify conversion happened
            assert "postgresql+asyncpg://" in async_url
            assert "sslmode=" not in async_url
            assert "ssl=" in async_url or "/cloudsql/" in async_url
    
    @pytest.mark.asyncio
    async def test_get_converted_async_db_url_prevents_sslmode(self):
        """Test that get_converted_async_db_url properly handles URL conversion."""
        # Mock a staging environment URL with sslmode
        staging_url = "postgresql://user:pass@host:5432/dbname?sslmode=require"
        
        with patch.dict(os.environ, {"DATABASE_URL": staging_url}):
            # Get the converted URL using the function that should be used
            converted_url = postgres_core.get_converted_async_db_url()
            
            # Verify it's properly converted
            assert "postgresql+asyncpg://" in converted_url
            assert "sslmode=" not in converted_url
            # Should have ssl= instead (unless it's Cloud SQL)
            if "/cloudsql/" not in converted_url:
                assert "ssl=" in converted_url
    
    @pytest.mark.asyncio
    async def test_health_checker_works_with_converted_url(self):
        """Test that health checker works when using properly converted URL."""
        # Mock a properly converted URL (ssl instead of sslmode)
        converted_url = "postgresql+asyncpg://user:pass@host:5432/dbname?ssl=require"
        
        # Create a mock engine that simulates successful connection
        # Mock: Generic component isolation for controlled unit testing
        mock_engine = AsyncMock()  # TODO: Use real service instance
        mock_engine.url = converted_url
        
        # Mock successful connection and query
        # Mock: Generic component isolation for controlled unit testing
        mock_conn = AsyncMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_result = AsyncMock()  # TODO: Use real service instance
        mock_result.fetchone.return_value = (1,)
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_engine.connect.return_value.__aexit__.return_value = None
        
        # Patch the engine
        with patch.object(postgres_core, 'async_engine', mock_engine):
            metrics = ConnectionPoolMetrics()
            health_checker = ConnectionHealthChecker(metrics)
            
            # This should succeed
            result = await health_checker.perform_health_check()
            
            # Verify success
            assert result["connectivity_test"]["status"] == "healthy"
            assert result["connectivity_test"]["error"] is None
    
    @pytest.mark.asyncio
    async def test_cloud_sql_url_has_no_ssl_params(self):
        """Test that Cloud SQL URLs have SSL parameters completely removed."""
        # Test with a Cloud SQL URL
        cloud_sql_url = "postgresql://user:pass@/dbname?host=/cloudsql/project:region:instance&sslmode=require"
        
        with patch.dict(os.environ, {"DATABASE_URL": cloud_sql_url}):
            # Get the converted async URL
            async_url = get_converted_async_db_url()
            
            # Verify SSL params are completely removed for Cloud SQL
            assert "sslmode=" not in async_url
            assert "ssl=" not in async_url
            assert "/cloudsql/" in async_url
    
    @pytest.mark.asyncio
    async def test_init_async_db_validates_url_conversion(self):
        """Test that init_async_db properly validates URL conversion."""
        # Mock a URL with sslmode that should fail validation
        bad_url = "postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=require"
        
        with patch.dict(os.environ, {"DATABASE_URL": bad_url}):
            with patch('netra_backend.app.db.postgres_core.get_converted_async_db_url', return_value=bad_url):
                # The validation should catch this
                with pytest.raises(RuntimeError) as exc_info:
                    # Mock the create_async_engine to not actually create engine
                    # Mock: Component isolation for testing without external dependencies
                    with patch('netra_backend.app.db.postgres_core.create_async_engine'):
                        postgres_core._create_and_setup_engine(bad_url, {})
                
                assert "CRITICAL" in str(exc_info.value)
                assert "validation failed" in str(exc_info.value)
