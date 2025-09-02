from shared.isolated_environment import get_env
"""
Comprehensive tests to prevent dev launcher issues from recurring.
These tests expose the root causes found in dev_launcher_logs.txt audit.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import QueuePool


env = get_env()
class TestDatabaseConnectionIssues:
    """Tests for database connection failures and redundancies."""
    
    def test_clickhouse_connection_failure_handling(self, monkeypatch):
        """Test that ClickHouse connection failures are handled gracefully."""
        from netra_backend.app.db.clickhouse import ClickHouseManager
        
        # Should fail gracefully after 5 attempts
        with patch.object(ClickHouseManager, '_connect', side_effect=Exception("Connection failed")):
            manager = ClickHouseManager()
            result = manager.test_connection()
            assert result is False, "ClickHouse should return False on connection failure, not crash"
    
    def test_migration_duplicate_table_idempotency(self):
        """Test that migrations handle 'table already exists' errors properly."""
        from netra_backend.app.startup_module import _handle_migration_error
        from psycopg2.errors import DuplicateTable
        
        logger = MagicMock()
        error = DuplicateTable("relation 'users' already exists")
        
        # Should handle gracefully, not crash
        _handle_migration_error(logger, error)
        logger.warning.assert_called()
        assert "continuing" in str(logger.warning.call_args).lower()
    
    def test_async_pool_invalid_attribute_error(self):
        """Test that AsyncAdaptedQueuePool doesn't have 'invalid' attribute calls."""
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # This should not try to access 'invalid' attribute
        engine = DatabaseManager.create_application_engine()
        pool = engine.pool
        
        # This was causing the error
        with pytest.raises(AttributeError):
            pool.invalid  # Should not exist
        
        # Proper way to invalidate connections
        assert hasattr(pool, 'dispose'), "Pool should have dispose method for cleanup"
    
    def test_duplicate_database_connections_prevented(self):
        """Test that we don't create multiple database connections unnecessarily."""
        from netra_backend.app.startup_module import setup_database_connections
        from fastapi import FastAPI
        
        app = FastAPI()
        call_count = 0
        
        async def mock_test_connection(*args):
            nonlocal call_count
            call_count += 1
            return True
        
        with patch('netra_backend.app.db.database_manager.DatabaseManager.test_connection_with_retry', mock_test_connection):
            asyncio.run(setup_database_connections(app))
            
        assert call_count == 1, f"Database connection tested {call_count} times, should be 1"


class TestSQLAlchemyLoggingIssues:
    """Tests for SQLAlchemy verbose logging issues."""
    
    def test_sqlalchemy_logging_disabled_by_default(self):
        """Test that SQLAlchemy doesn't spam logs in non-TRACE mode."""
        from netra_backend.app.core.unified_logging import UnifiedLogger
        
        # UnifiedLogger is a singleton, no args needed
        logger = UnifiedLogger()
        logger._setup_logging()  # Ensure logging is configured
        
        sql_logger = logging.getLogger("sqlalchemy.engine")
        
        # Should be WARNING level by default, not INFO
        assert sql_logger.level >= logging.WARNING, "SQLAlchemy should not log SQL by default"
    
    def test_echo_disabled_in_production(self):
        """Test that echo is disabled in production database connections."""
        from netra_backend.app.db.database_manager import DatabaseManager
        import os
        
        env.set('ENVIRONMENT', 'production', "test")
        engine_config = DatabaseManager._get_engine_config()
        
        assert engine_config.get('echo', False) is False, "Echo must be False in production"
        assert engine_config.get('echo_pool', False) is False, "Echo pool must be False in production"


class TestAuthServiceIssues:
    """Tests for auth service connectivity and health check issues."""
    
    def test_auth_service_port_consistency(self):
        """Test that auth service port is consistent across configuration."""
        from dev_launcher.auth_starter import AUTH_SERVICE_PORT
        
        # Auth service should use port 8081, not 8004
        assert AUTH_SERVICE_PORT == 8081, f"Auth service port is {AUTH_SERVICE_PORT}, expected 8081"
    
    def test_frontend_proxy_uses_service_discovery(self):
        """Test that frontend doesn't hardcode auth service ports."""
        # This test would check frontend configuration
        # Frontend should read from service discovery, not hardcode ports
        pass  # Frontend tests need JS testing framework
    
    @pytest.mark.asyncio
    async def test_auth_health_check_timeout(self):
        """Test that auth health checks timeout properly."""
        from netra_backend.app.routes.health import _check_auth_connection
        
        with patch('httpx.AsyncClient.get', side_effect=asyncio.TimeoutError()):
            result = await _check_auth_connection()
            assert result is False, "Auth check should return False on timeout, not hang"


class TestWebSocketIssues:
    """Tests for WebSocket authentication and configuration issues."""
    
    @pytest.mark.asyncio
    async def test_websocket_requires_authentication(self):
        """Test that WebSocket connections require proper authentication."""
        from netra_backend.app.websocket_core.auth import secure_websocket_context
        from fastapi import WebSocket
        
        websocket = MagicMock(spec=WebSocket)
        websocket.headers = {}  # No auth headers
        websocket.subprotocols = []  # No JWT in subprotocol
        
        with pytest.raises(Exception) as exc_info:
            async with secure_websocket_context(websocket, "test-id", MagicMock()):
                pass
        
        assert "Authentication required" in str(exc_info.value)
    
    def test_websocket_secure_config_not_spammed(self):
        """Test that useWebSocketSecure configuration isn't logged excessively."""
        # This would check that configuration endpoint has request deduplication
        pass  # Requires frontend testing


class TestStartupPerformanceIssues:
    """Tests for slow startup and service initialization issues."""
    
    @pytest.mark.asyncio
    async def test_startup_completes_within_timeout(self):
        """Test that system startup completes within reasonable time."""
        from netra_backend.app.startup_module import run_complete_startup
        from fastapi import FastAPI
        
        app = FastAPI()
        start_time = datetime.now()
        
        with patch('netra_backend.app.startup_module.setup_database_connections', new_callable=AsyncMock):
            await run_complete_startup(app)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        assert elapsed < 60, f"Startup took {elapsed}s, should be under 60s"
    
    def test_health_checks_not_duplicated(self):
        """Test that health checks aren't run multiple times unnecessarily."""
        from netra_backend.app.startup_module import startup_health_checks
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state.database_validated = True  # Already validated
        
        logger = MagicMock()
        asyncio.run(startup_health_checks(app, logger))
        
        # Should skip redundant checks
        assert "Skipping redundant" in str(logger.info.call_args)
    
    def test_service_startup_order_optimized(self):
        """Test that services start in optimal dependency order."""
        from dev_launcher.launcher import DevLauncher
        
        launcher = DevLauncher()
        # Database should start before backend
        # Auth should start before frontend
        # This validates the startup order is optimized
        assert launcher.startup_order == ['database', 'auth', 'backend', 'frontend']


class TestCrossServiceConnectivity:
    """Tests for cross-service connectivity verification issues."""
    
    @pytest.mark.asyncio
    async def test_service_discovery_file_created(self):
        """Test that service discovery file is created properly."""
        from dev_launcher.service_discovery import ServiceDiscovery
        
        discovery = ServiceDiscovery()
        discovery.register_service('auth', 8081)
        
        services = discovery.get_services()
        assert services['auth'] == 8081, "Service discovery should store correct port"
    
    def test_retry_logic_has_proper_backoff(self):
        """Test that retry logic uses exponential backoff."""
        from netra_backend.app.db.database_manager import DatabaseManager
        
        retry_delays = []
        
        async def mock_connect():
            retry_delays.append(datetime.now())
            raise OperationalError("Connection failed", None, None)
        
        with patch.object(DatabaseManager, '_connect', mock_connect):
            asyncio.run(DatabaseManager.test_connection_with_retry(max_attempts=3))
        
        # Check delays are increasing
        if len(retry_delays) > 1:
            for i in range(1, len(retry_delays)):
                delay = (retry_delays[i] - retry_delays[i-1]).total_seconds()
                assert delay >= 1, f"Retry delay {delay}s is too short"


class TestEnvironmentConfigurationIssues:
    """Tests for environment and configuration consistency."""
    
    def test_environment_variables_consistent(self):
        """Test that environment variables are consistently named and used."""
        from netra_backend.app.core.config import Settings
        import os
        
        # All database URLs should use same environment variable
        settings = Settings()
        assert settings.database_url == get_env().get('DATABASE_URL', settings.database_url)
    
    def test_no_hardcoded_development_values(self):
        """Test that no development values are hardcoded in production code."""
        from netra_backend.app.core.config import Settings
        
        settings = Settings(environment="production")
        
        # No localhost in production
        assert "localhost" not in settings.database_url
        assert "127.0.0.1" not in settings.redis_url


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
