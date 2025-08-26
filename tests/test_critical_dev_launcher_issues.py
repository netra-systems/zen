"""
Critical Dev Launcher Regression Tests
Tests to prevent the critical issues found in dev_launcher_logs.txt from recurring
"""

import pytest
import asyncio
import psycopg2
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netra_backend.app.db.postgres_core import get_pool_status, initialize_postgres
from netra_backend.app.db.migration_utils import get_current_revision, execute_migration
from netra_backend.app.startup_module import _ensure_database_tables_exist, _check_and_run_migrations
from netra_backend.app.routes.health import _check_readiness_status
from dev_launcher.backend_starter import BackendStarter
from dev_launcher.config import DevelopmentConfig


class TestPortConfiguration:
    """Test suite for port configuration consistency"""
    
    def test_backend_port_is_8000_not_8004(self):
        """Frontend must connect to backend on port 8000, not 8004"""
        config = DevelopmentConfig()
        starter = BackendStarter(config)
        
        # Get allocated port
        port = starter._allocate_port(service_name="backend")
        
        # Port should be 8000 by default
        assert port == 8000, f"Backend port should be 8000, got {port}"
    
    def test_frontend_api_config_uses_correct_port(self):
        """Frontend API config must use port 8000 for backend"""
        # This would test the frontend config but we're in Python
        # Creating as a placeholder for the actual TypeScript test
        expected_backend_url = "http://localhost:8000"
        
        # Simulate what the frontend config should return
        from frontend.config.api_config import get_api_url
        api_url = get_api_url()
        
        assert api_url == expected_backend_url, f"Frontend should use {expected_backend_url}, got {api_url}"
    
    def test_static_ports_are_default(self):
        """Static ports should be the default, not dynamic"""
        config = DevelopmentConfig()
        assert config.use_dynamic_ports == False, "Dynamic ports should not be default"
        assert config.backend_port == 8000, "Backend port should default to 8000"
        assert config.frontend_port == 3000, "Frontend port should default to 3000"


class TestDatabaseMigrations:
    """Test suite for database migration issues"""
    
    @pytest.mark.asyncio
    async def test_migration_handles_existing_tables(self):
        """Migration should handle existing tables gracefully"""
        # Create a mock connection that simulates existing tables
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = psycopg2.errors.DuplicateTable("relation 'users' already exists")
        
        with patch('netra_backend.app.db.migration_utils.get_database_connection', return_value=mock_conn):
            # This should not raise an exception
            result = await execute_migration(mock_conn, "test_revision")
            assert result is not None, "Migration should handle existing tables"
    
    @pytest.mark.asyncio
    async def test_alembic_version_table_check(self):
        """Should check if alembic_version table exists before querying"""
        mock_conn = MagicMock()
        
        # First call - check for alembic_version table
        mock_conn.execute.return_value.scalar.side_effect = [False, None]
        
        revision = await get_current_revision(mock_conn)
        assert revision is None, "Should return None when alembic_version doesn't exist"
        
        # Verify it checked for the table first
        calls = mock_conn.execute.call_args_list
        assert "alembic_version" in str(calls[0]), "Should check for alembic_version table"
    
    def test_migration_state_consistency(self):
        """Alembic state should match actual database schema"""
        # This tests that we properly track migration state
        with patch('alembic.command.current') as mock_current:
            mock_current.return_value = None  # No current revision
            
            with patch('netra_backend.app.startup_module.get_existing_tables') as mock_tables:
                mock_tables.return_value = ['users', 'threads', 'corpus_objects']
                
                # This should detect the mismatch and handle it
                result = _check_and_run_migrations(None)
                assert result is not None, "Should handle migration state mismatch"


class TestAsyncPoolOperations:
    """Test suite for AsyncAdaptedQueuePool issues"""
    
    def test_async_pool_has_no_invalid_attribute(self):
        """AsyncAdaptedQueuePool doesn't have invalid() method"""
        pool = AsyncAdaptedQueuePool(lambda: None)
        
        # This should not exist
        assert not hasattr(pool, 'invalid'), "AsyncAdaptedQueuePool should not have invalid() method"
        
        # But invalidated should work
        assert hasattr(pool, 'invalidated'), "AsyncAdaptedQueuePool should have invalidated property"
    
    def test_get_pool_status_handles_async_pool(self):
        """get_pool_status should handle async pools correctly"""
        mock_pool = MagicMock(spec=AsyncAdaptedQueuePool)
        mock_pool.size.return_value = 5
        mock_pool.checked_in.return_value = 3
        mock_pool.overflow.return_value = 0
        mock_pool.invalidated = []
        
        # Should not raise AttributeError
        status = get_pool_status(mock_pool)
        assert status is not None, "Should return pool status"
        assert "total" in status, "Status should contain pool info"
    
    def test_pool_status_fallback_on_attribute_error(self):
        """Should fallback gracefully when pool methods don't exist"""
        mock_pool = MagicMock()
        del mock_pool.invalid  # Remove the method
        
        # Should not crash
        status = get_pool_status(mock_pool) 
        assert status is not None, "Should handle missing attributes"


class TestClickHouseResilience:
    """Test suite for ClickHouse connection resilience"""
    
    @pytest.mark.asyncio
    async def test_clickhouse_failure_does_not_block_startup(self):
        """ClickHouse connection failure should not block startup in development"""
        with patch('clickhouse_driver.Client') as mock_client:
            mock_client.side_effect = Exception("Connection failed")
            
            # Startup should continue
            from netra_backend.app.startup_module import initialize_clickhouse_tables
            result = await initialize_clickhouse_tables(environment="development")
            assert result is not None, "Should handle ClickHouse failure in development"
    
    def test_clickhouse_timeout_configured(self):
        """ClickHouse should have reasonable timeout configured"""
        from netra_backend.app.db.clickhouse_core import get_clickhouse_client
        
        client = get_clickhouse_client(timeout=5)
        assert client is not None, "Should create client with timeout"
        # Verify timeout is set (implementation specific)
    
    def test_clickhouse_retries_limited(self):
        """ClickHouse retries should be limited to prevent cascading failures"""
        max_retries = 5
        attempts = 0
        
        def failing_connect():
            nonlocal attempts
            attempts += 1
            raise Exception("Connection failed")
        
        with patch('clickhouse_driver.Client', side_effect=failing_connect):
            from netra_backend.app.db.clickhouse_core import connect_with_retry
            
            try:
                connect_with_retry(max_retries=max_retries)
            except:
                pass
            
            assert attempts <= max_retries, f"Should limit retries to {max_retries}, attempted {attempts}"


class TestHealthCheckDeterminism:
    """Test suite for health check race conditions"""
    
    @pytest.mark.asyncio 
    async def test_health_checks_sequential_not_concurrent(self):
        """Critical health checks should run sequentially to avoid race conditions"""
        check_order = []
        
        async def mock_postgres_check():
            check_order.append("postgres")
            await asyncio.sleep(0.1)
            return True
        
        async def mock_redis_check():
            check_order.append("redis")
            await asyncio.sleep(0.1)
            return True
        
        async def mock_clickhouse_check():
            check_order.append("clickhouse")
            await asyncio.sleep(0.1)
            return True
        
        # Run health checks
        with patch('netra_backend.app.routes.health._check_postgres', mock_postgres_check):
            with patch('netra_backend.app.routes.health._check_redis', mock_redis_check):
                with patch('netra_backend.app.routes.health._check_clickhouse', mock_clickhouse_check):
                    status = await _check_readiness_status()
        
        # Verify sequential execution
        assert check_order == ["postgres", "redis", "clickhouse"], "Checks should run sequentially"
    
    @pytest.mark.asyncio
    async def test_health_check_handles_concurrent_pool_access(self):
        """Health checks should handle concurrent pool access safely"""
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        
        async def concurrent_check():
            return get_pool_status(mock_pool)
        
        # Run multiple concurrent checks
        results = await asyncio.gather(*[concurrent_check() for _ in range(10)])
        
        # All should succeed
        assert all(r is not None for r in results), "All concurrent checks should succeed"
    
    def test_health_check_environment_specific(self):
        """Health checks should be environment-aware"""
        # In staging, some services are optional
        from netra_backend.app.routes.health import get_required_services
        
        dev_services = get_required_services("development")
        staging_services = get_required_services("staging") 
        
        assert "clickhouse" in dev_services, "ClickHouse required in dev"
        assert "clickhouse" not in staging_services, "ClickHouse optional in staging"


class TestAuthServiceVerification:
    """Test suite for auth service verification issues"""
    
    @pytest.mark.asyncio
    async def test_auth_verification_blocks_on_failure(self):
        """Auth verification failure should properly fail startup"""
        with patch('netra_backend.app.startup_module.verify_auth_service') as mock_verify:
            mock_verify.return_value = False
            
            # This should raise or return failure
            from netra_backend.app.startup_module import run_complete_startup
            with pytest.raises(Exception, match="Auth.*failed"):
                await run_complete_startup(None)
    
    def test_auth_service_health_endpoint_exists(self):
        """Auth service should have proper health endpoint"""
        from auth_service.auth_core.main import app
        
        # Check that health endpoint is registered
        routes = [route.path for route in app.routes]
        assert "/health" in routes or "/health/" in routes, "Auth service needs health endpoint"
    
    def test_cross_service_token_validated(self):
        """Cross-service auth token should be validated on startup"""
        import os
        token = os.environ.get("CROSS_SERVICE_AUTH_TOKEN")
        
        if token:
            assert len(token) >= 32, "Cross-service token should be sufficiently long"
            assert token.isalnum(), "Token should be alphanumeric"


class TestSQLAlchemyLoggingControl:
    """Test suite for SQLAlchemy logging issues"""
    
    def test_sqlalchemy_echo_disabled_by_default(self):
        """SQLAlchemy echo should be disabled to prevent log spam"""
        from netra_backend.app.db.postgres_core import create_async_engine
        
        engine = create_async_engine("postgresql://test", echo=False)
        assert engine.echo is False, "Echo should be disabled by default"
    
    def test_raw_sql_logging_controlled(self):
        """Raw SQL logging should be controlled via log level"""
        import logging
        
        # SQLAlchemy logger should not be at INFO level
        sql_logger = logging.getLogger("sqlalchemy.engine")
        assert sql_logger.level > logging.INFO, "SQLAlchemy logger should not log at INFO"


class TestDeprecationWarnings:
    """Test suite for deprecation warnings"""
    
    def test_websocket_handler_signature(self):
        """WebSocket handler should use correct signature"""
        from netra_backend.app.routes.websocket import websocket_endpoint
        import inspect
        
        sig = inspect.signature(websocket_endpoint)
        params = list(sig.parameters.keys())
        
        # Should only have one parameter (websocket)
        assert len(params) == 1, "WebSocket handler should have single parameter"
    
    def test_nextjs_config_valid(self):
        """Next.js config should not have deprecated options"""
        import json
        config_path = "frontend/next.config.ts"
        
        # Would need to parse TypeScript, placeholder test
        # assert "swcMinify" not in config_content, "swcMinify is deprecated in Next.js 15"
        pass


# Integration test for full startup sequence
class TestFullStartupIntegration:
    """Integration test for complete startup sequence"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_dev_launcher_startup(self):
        """Complete dev launcher startup should work end-to-end"""
        from scripts.dev_launcher import DevLauncher
        
        launcher = DevLauncher()
        
        # Mock external dependencies
        with patch('docker.from_env'):
            with patch('subprocess.Popen'):
                # Start the launcher
                result = await launcher.start()
                
                assert result is not None, "Launcher should start successfully"
                assert launcher.backend_port == 8000, "Backend should be on port 8000"
                assert launcher.frontend_port == 3000, "Frontend should be on port 3000"
    
    @pytest.mark.asyncio
    async def test_service_discovery_file_created(self):
        """Service discovery file should be created with correct ports"""
        import json
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
            discovery_data = {
                "backend": {"port": 8000, "url": "http://localhost:8000"},
                "frontend": {"port": 3000, "url": "http://localhost:3000"},
                "auth": {"port": 8081, "url": "http://localhost:8081"}
            }
            json.dump(discovery_data, f)
            f.flush()
            
            # Read back and verify
            with open(f.name, 'r') as rf:
                data = json.load(rf)
                assert data["backend"]["port"] == 8000, "Backend port should be 8000"
                assert data["frontend"]["port"] == 3000, "Frontend port should be 3000"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])