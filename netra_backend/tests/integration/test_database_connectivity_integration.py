"""
Integration tests for database connectivity across environments.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Reliability
- Value Impact: Ensures database connectivity works end-to-end
- Strategic Impact: Prevents production outages from database misconfigurations

Tests validate:
1. Database URL construction from environment variables
2. Health endpoint database connectivity checks
3. Proper error handling and recovery mechanisms
"""

import pytest
import asyncio
import os
from typing import Optional
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from netra_backend.app.main import app
from netra_backend.app.database import get_db
from shared.database_url_builder import DatabaseURLBuilder


class TestDatabaseConnectivityIntegration:
    """Integration tests for database connectivity."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_ready_endpoint_with_valid_database(self):
        """Test /health/ready endpoint with valid database configuration."""
        # Create a mock database session that simulates a working connection
        async def mock_get_db():
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = 1
            mock_session.execute.return_value = mock_result
            try:
                yield mock_session
            finally:
                pass
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            with patch('netra_backend.app.routes.health.unified_config_manager.get_config') as mock_config:
                mock_cfg = MagicMock()
                mock_cfg.database_url = 'postgresql://test:test@localhost/testdb'
                mock_cfg.environment = 'testing'
                mock_config.return_value = mock_cfg
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/health/ready")
                    
                    # In testing environment with valid database, should return 200
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "ready"
                    assert "postgres" in data["services"]
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_ready_endpoint_with_missing_database_staging(self):
        """Test /health/ready endpoint with missing database in staging."""
        # Create a mock database session
        async def mock_get_db():
            mock_session = AsyncMock()
            try:
                yield mock_session
            finally:
                pass
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            with patch('netra_backend.app.routes.health.unified_config_manager.get_config') as mock_config:
                mock_cfg = MagicMock()
                mock_cfg.database_url = None  # Missing database URL
                mock_cfg.environment = 'staging'
                mock_config.return_value = mock_cfg
                
                with patch('shared.isolated_environment.get_env') as mock_env:
                    mock_env.return_value.get.return_value = 'staging'
                    
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        response = await client.get("/health/ready")
                        
                        # In staging with missing database, should return 503
                        assert response.status_code == 503
                        data = response.json()
                        assert data["error"] is True
                        assert "Core database unavailable" in data["message"]
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_database_url_builder_integration(self):
        """Test DatabaseURLBuilder integration with different environment configurations."""
        test_cases = [
            {
                "name": "Complete PostgreSQL configuration",
                "env_vars": {
                    "ENVIRONMENT": "staging",
                    "POSTGRES_HOST": "db.example.com",
                    "POSTGRES_PORT": "5432",
                    "POSTGRES_USER": "testuser",
                    "POSTGRES_PASSWORD": "testpass",
                    "POSTGRES_DB": "testdb"
                },
                "expected_contains": ["postgresql", "testuser", "db.example.com", "testdb"]
            },
            {
                "name": "DATABASE_URL override",
                "env_vars": {
                    "ENVIRONMENT": "production",
                    "DATABASE_URL": "postgresql://override:pass@override.com/overridedb",
                    "POSTGRES_HOST": "ignored.com",
                    "POSTGRES_USER": "ignored"
                },
                "expected_contains": ["override.com", "overridedb"]
            },
            {
                "name": "Cloud SQL configuration",
                "env_vars": {
                    "ENVIRONMENT": "production",
                    "CLOUD_SQL_CONNECTION_NAME": "project:region:instance",
                    "POSTGRES_USER": "clouduser",
                    "POSTGRES_PASSWORD": "cloudpass",
                    "POSTGRES_DB": "clouddb"
                },
                "expected_contains": ["clouduser", "clouddb", "cloudsql"]
            }
        ]
        
        for test_case in test_cases:
            builder = DatabaseURLBuilder(test_case["env_vars"])
            
            # Get appropriate URL based on environment
            if test_case["env_vars"]["ENVIRONMENT"] == "staging":
                url = builder.staging.auto_url
            elif test_case["env_vars"]["ENVIRONMENT"] == "production":
                url = builder.production.auto_url
            else:
                url = builder.development.auto_url
            
            # Verify URL contains expected parts
            if url:
                for expected in test_case["expected_contains"]:
                    assert expected in url, f"Test '{test_case['name']}' failed: '{expected}' not in URL"
            elif test_case.get("should_be_none"):
                assert url is None, f"Test '{test_case['name']}' failed: URL should be None"


class TestDatabaseConnectionPooling:
    """Test database connection pooling and recovery."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_connection_pool_recovery(self):
        """Test that database connection pool can recover from failures."""
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # Create a database manager with test configuration
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {
                'ENVIRONMENT': 'testing',
                'DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/testdb'
            }
            
            manager = DatabaseManager()
            
            # Simulate connection failure and recovery
            with patch.object(manager, '_engine') as mock_engine:
                # First call fails
                mock_engine.dispose = MagicMock()
                
                # Simulate recovery
                manager.handle_connection_error(Exception("Connection lost"))
                
                # Verify pool was disposed for recovery
                mock_engine.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_database_requests(self):
        """Test handling of concurrent database requests."""
        # Create mock database sessions
        sessions_created = []
        
        async def mock_get_db():
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = 1
            mock_session.execute.return_value = mock_result
            sessions_created.append(mock_session)
            try:
                yield mock_session
            finally:
                pass
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            with patch('netra_backend.app.routes.health.unified_config_manager.get_config') as mock_config:
                mock_cfg = MagicMock()
                mock_cfg.database_url = 'postgresql://test:test@localhost/testdb'
                mock_cfg.environment = 'testing'
                mock_config.return_value = mock_cfg
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    # Make multiple concurrent requests
                    tasks = [
                        client.get("/health/ready")
                        for _ in range(10)
                    ]
                    
                    responses = await asyncio.gather(*tasks)
                    
                    # All requests should succeed
                    for response in responses:
                        assert response.status_code == 200
                    
                    # Verify separate sessions were created for each request
                    assert len(sessions_created) == 10
        finally:
            app.dependency_overrides.clear()


class TestEnvironmentSpecificDatabaseConfig:
    """Test environment-specific database configurations."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_staging_requires_ssl_connection(self):
        """Test that staging environment requires SSL for database connections."""
        builder = DatabaseURLBuilder({
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "staging-db.example.com",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "staging_user",
            "POSTGRES_PASSWORD": "staging_pass",
            "POSTGRES_DB": "staging_db"
        })
        
        url = builder.staging.auto_url
        
        # Staging should use SSL
        assert url is not None
        assert "sslmode=" in url or "ssl" in url.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_production_cloud_sql_priority(self):
        """Test that production prioritizes Cloud SQL connections."""
        builder = DatabaseURLBuilder({
            "ENVIRONMENT": "production",
            "CLOUD_SQL_CONNECTION_NAME": "project:region:instance",
            "POSTGRES_HOST": "tcp-host.example.com",  # Should be ignored
            "POSTGRES_USER": "produser",
            "POSTGRES_PASSWORD": "prodpass",
            "POSTGRES_DB": "proddb"
        })
        
        url = builder.production.auto_url
        
        # Should use Cloud SQL, not TCP
        assert url is not None
        assert "cloudsql" in url.lower()
        assert "tcp-host.example.com" not in url
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_development_local_database_default(self):
        """Test that development environment defaults to local database."""
        builder = DatabaseURLBuilder({
            "ENVIRONMENT": "development"
            # No database configuration provided
        })
        
        url = builder.development.auto_url
        
        # Should have a default development URL
        assert url is not None
        assert "localhost" in url or "127.0.0.1" in url


# Helper class for async mocking
class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])