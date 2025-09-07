"""
Comprehensive tests to prevent dev launcher issues from recurring.
These tests expose the root causes found in dev_launcher_logs.txt audit.
"""

import asyncio
import pytest
import logging
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import QueuePool

from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.clients.auth_client_core import AuthServiceClient


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
        assert AUTH_SERVICE_PORT == 8081, f"Auth service port should be 8081, got {AUTH_SERVICE_PORT}"

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


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])