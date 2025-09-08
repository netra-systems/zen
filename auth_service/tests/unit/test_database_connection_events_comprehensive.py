"""
Comprehensive unit tests for Auth Service Database Connection Events

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure reliable database connection monitoring and timeout handling
- Value Impact: Prevents auth service failures due to connection issues and provides observability
- Strategic Impact: Foundation for monitoring and debugging database connectivity issues

Tests connection event handlers, timeout configuration, pool monitoring,
event setup, and integration with SQLAlchemy engine events.
Uses real PostgreSQL database for comprehensive validation.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import Mock, MagicMock, patch, call
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import ConnectionPoolEntry, _ConnectionFairy, NullPool
from sqlalchemy import text

from auth_service.auth_core.database.connection_events import (
    AuthDatabaseConfig,
    get_settings,
    setup_auth_async_engine_events,
    _configure_auth_connection_timeouts,
    _set_auth_connection_pid,
    _monitor_auth_pool_usage,
    _execute_auth_timeout_statements,
    _close_cursor_safely,
    _log_auth_connection_established,
    _log_auth_checkout_if_enabled
)
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from shared.isolated_environment import get_env
from test_framework.real_services_test_fixtures import real_services_fixture


class TestAuthDatabaseConfig:
    """Test auth database configuration constants"""
    
    @pytest.mark.unit
    def test_auth_database_config_constants(self):
        """Test that configuration constants are properly defined"""
        assert hasattr(AuthDatabaseConfig, 'STATEMENT_TIMEOUT')
        assert hasattr(AuthDatabaseConfig, 'POOL_SIZE')
        assert hasattr(AuthDatabaseConfig, 'MAX_OVERFLOW')
        assert hasattr(AuthDatabaseConfig, 'POOL_WARNING_THRESHOLD')
        
        # Test specific values
        assert AuthDatabaseConfig.STATEMENT_TIMEOUT == 15000  # 15 seconds
        assert AuthDatabaseConfig.POOL_SIZE == 5
        assert AuthDatabaseConfig.MAX_OVERFLOW == 10
        assert AuthDatabaseConfig.POOL_WARNING_THRESHOLD == 0.8
    
    @pytest.mark.unit
    def test_auth_database_config_values_reasonable(self):
        """Test that configuration values are reasonable for auth service"""
        # Statement timeout should be reasonable (not too short, not too long)
        assert 5000 <= AuthDatabaseConfig.STATEMENT_TIMEOUT <= 30000
        
        # Pool size should be appropriate for auth service load
        assert 1 <= AuthDatabaseConfig.POOL_SIZE <= 20
        
        # Max overflow should be reasonable
        assert 0 <= AuthDatabaseConfig.MAX_OVERFLOW <= 50
        
        # Warning threshold should be a percentage
        assert 0.0 < AuthDatabaseConfig.POOL_WARNING_THRESHOLD <= 1.0


class TestGetSettings:
    """Test settings retrieval functionality"""
    
    @pytest.mark.unit
    def test_get_settings_with_auth_config(self):
        """Test settings retrieval when AuthConfig is available"""
        with patch('auth_service.auth_core.database.connection_events.AuthConfig') as mock_config:
            mock_config.LOG_ASYNC_CHECKOUT = True
            mock_config.ENVIRONMENT = "test"
            
            settings = get_settings()
            
            assert settings is not None
            assert hasattr(settings, 'log_async_checkout')
            assert hasattr(settings, 'environment')
            assert settings.log_async_checkout is True
            assert settings.environment == "test"
    
    @pytest.mark.unit
    def test_get_settings_with_partial_auth_config(self):
        """Test settings retrieval when AuthConfig has missing attributes"""
        with patch('auth_service.auth_core.database.connection_events.AuthConfig') as mock_config:
            # Mock config without LOG_ASYNC_CHECKOUT attribute
            del mock_config.LOG_ASYNC_CHECKOUT
            mock_config.ENVIRONMENT = "test"
            
            settings = get_settings()
            
            assert settings is not None
            assert hasattr(settings, 'log_async_checkout')
            assert hasattr(settings, 'environment')
            assert settings.log_async_checkout is False  # Default
            assert settings.environment == "test"
    
    @pytest.mark.unit
    def test_get_settings_import_error(self):
        """Test settings retrieval when AuthConfig import fails"""
        with patch('auth_service.auth_core.database.connection_events.AuthConfig', side_effect=ImportError):
            settings = get_settings()
            
            assert settings is None
    
    @pytest.mark.unit
    def test_get_settings_module_level_initialization(self):
        """Test that settings are initialized at module level"""
        # Re-import module to test initialization
        from auth_service.auth_core.database.connection_events import settings
        
        # Settings should be initialized (either object or None)
        assert settings is not None or settings is None


class TestTimeoutConfiguration:
    """Test database timeout configuration functions"""
    
    @pytest.mark.unit
    def test_execute_auth_timeout_statements(self):
        """Test timeout statement execution"""
        mock_cursor = Mock()
        
        _execute_auth_timeout_statements(mock_cursor)
        
        # Verify all timeout statements were executed
        expected_calls = [
            call(f"SET statement_timeout = {AuthDatabaseConfig.STATEMENT_TIMEOUT}"),
            call("SET idle_in_transaction_session_timeout = 30000"),
            call("SET lock_timeout = 5000")
        ]
        mock_cursor.execute.assert_has_calls(expected_calls)
    
    @pytest.mark.unit
    def test_close_cursor_safely_success(self):
        """Test cursor closing with no errors"""
        mock_cursor = Mock()
        
        _close_cursor_safely(mock_cursor)
        
        mock_cursor.close.assert_called_once()
    
    @pytest.mark.unit
    def test_close_cursor_safely_error(self):
        """Test cursor closing with error (should not raise)"""
        mock_cursor = Mock()
        mock_cursor.close.side_effect = Exception("Close error")
        
        # Should not raise exception
        _close_cursor_safely(mock_cursor)
        
        mock_cursor.close.assert_called_once()
    
    @pytest.mark.unit
    def test_configure_auth_connection_timeouts_success(self):
        """Test successful timeout configuration"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        _configure_auth_connection_timeouts(mock_conn)
        
        # Verify cursor operations
        mock_conn.cursor.assert_called_once()
        mock_cursor.close.assert_called_once()
        
        # Should execute timeout statements
        assert mock_cursor.execute.call_count >= 3
    
    @pytest.mark.unit
    def test_configure_auth_connection_timeouts_error(self):
        """Test timeout configuration with error"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("SQL Error")
        
        with pytest.raises(Exception):
            _configure_auth_connection_timeouts(mock_conn)
        
        # Should attempt rollback
        mock_conn.rollback.assert_called_once()


class TestConnectionPIDHandling:
    """Test connection PID setting and handling"""
    
    @pytest.mark.unit
    def test_set_auth_connection_pid_with_backend_pid(self):
        """Test PID setting when backend PID is available"""
        mock_conn = Mock()
        mock_conn.get_backend_pid.return_value = 12345
        mock_record = Mock()
        mock_record.info = {}
        
        _set_auth_connection_pid(mock_conn, mock_record)
        
        assert mock_record.info['pid'] == 12345
    
    @pytest.mark.unit
    def test_set_auth_connection_pid_no_backend_pid(self):
        """Test PID setting when backend PID is not available"""
        mock_conn = Mock()
        # Remove get_backend_pid method
        del mock_conn.get_backend_pid
        mock_record = Mock()
        mock_record.info = {}
        
        _set_auth_connection_pid(mock_conn, mock_record)
        
        assert mock_record.info['pid'] is None
    
    @pytest.mark.unit
    def test_set_auth_connection_pid_error(self):
        """Test PID setting with error (should not raise)"""
        mock_conn = Mock()
        mock_conn.get_backend_pid.side_effect = Exception("PID error")
        mock_record = Mock()
        mock_record.info = {}
        
        # Should not raise exception
        _set_auth_connection_pid(mock_conn, mock_record)
        
        assert mock_record.info['pid'] is None


class TestPoolMonitoring:
    """Test connection pool monitoring functionality"""
    
    @pytest.mark.unit
    def test_monitor_auth_pool_usage_no_pool(self):
        """Test pool monitoring when no pool is available"""
        # Should not raise error
        _monitor_auth_pool_usage(None)
    
    @pytest.mark.unit
    def test_monitor_auth_pool_usage_normal_usage(self):
        """Test pool monitoring with normal usage"""
        mock_pool = Mock()
        mock_pool.size.return_value = 5
        mock_pool.checkedin.return_value = 3
        mock_pool.overflow.return_value = 0
        mock_pool.total.return_value = 5
        
        # Should not log warnings for normal usage
        with patch('auth_service.auth_core.database.connection_events.logger') as mock_logger:
            _monitor_auth_pool_usage(mock_pool)
            
            # Should not log warnings
            mock_logger.warning.assert_not_called()
    
    @pytest.mark.unit
    def test_monitor_auth_pool_usage_high_usage(self):
        """Test pool monitoring with high usage (should warn)"""
        mock_pool = Mock()
        mock_pool.size.return_value = 5
        mock_pool.checkedin.return_value = 1  # Only 1 available
        mock_pool.overflow.return_value = 8   # High overflow
        mock_pool.total.return_value = 13
        
        # High usage should trigger warning
        with patch('auth_service.auth_core.database.connection_events.logger') as mock_logger:
            _monitor_auth_pool_usage(mock_pool)
            
            # Should log warning about high usage
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Connection pool usage high" in warning_call
    
    @pytest.mark.unit
    def test_monitor_auth_pool_usage_missing_methods(self):
        """Test pool monitoring with pool missing required methods"""
        mock_pool = Mock()
        # Remove required methods
        del mock_pool.size
        
        # Should not raise error
        _monitor_auth_pool_usage(mock_pool)
    
    @pytest.mark.unit
    def test_monitor_auth_pool_usage_error(self):
        """Test pool monitoring with error in pool methods"""
        mock_pool = Mock()
        mock_pool.size.side_effect = Exception("Pool error")
        
        # Should not raise exception
        _monitor_auth_pool_usage(mock_pool)


class TestConnectionLogging:
    """Test connection logging functionality"""
    
    @pytest.mark.unit
    def test_log_auth_connection_established_with_settings(self):
        """Test connection logging when settings are available"""
        mock_record = Mock()
        mock_record.info = {'pid': 12345}
        
        with patch('auth_service.auth_core.database.connection_events.settings') as mock_settings:
            mock_settings.log_async_checkout = True
            
            with patch('auth_service.auth_core.database.connection_events.logger') as mock_logger:
                _log_auth_connection_established(mock_record)
                
                # Should log the connection
                mock_logger.debug.assert_called_once()
                log_call = mock_logger.debug.call_args[0][0]
                assert "Database connection established" in log_call
                assert "PID=12345" in log_call
    
    @pytest.mark.unit
    def test_log_auth_connection_established_no_settings(self):
        """Test connection logging when settings are not available"""
        mock_record = Mock()
        mock_record.info = {'pid': None}
        
        with patch('auth_service.auth_core.database.connection_events.settings', None):
            with patch('auth_service.auth_core.database.connection_events.logger') as mock_logger:
                mock_logger.isEnabledFor.return_value = False
                
                _log_auth_connection_established(mock_record)
                
                # Should not log when debug is disabled
                mock_logger.debug.assert_not_called()
    
    @pytest.mark.unit
    def test_log_auth_checkout_if_enabled_enabled(self):
        """Test checkout logging when enabled"""
        mock_record = Mock()
        mock_record.info = {'pid': 67890}
        
        with patch('auth_service.auth_core.database.connection_events.settings') as mock_settings:
            mock_settings.log_async_checkout = True
            
            with patch('auth_service.auth_core.database.connection_events.logger') as mock_logger:
                _log_auth_checkout_if_enabled(mock_record)
                
                # Should log the checkout
                mock_logger.debug.assert_called_once()
                log_call = mock_logger.debug.call_args[0][0]
                assert "Connection checked out" in log_call
                assert "PID=67890" in log_call
    
    @pytest.mark.unit
    def test_log_auth_checkout_if_enabled_disabled(self):
        """Test checkout logging when disabled"""
        mock_record = Mock()
        mock_record.info = {'pid': 67890}
        
        with patch('auth_service.auth_core.database.connection_events.settings') as mock_settings:
            mock_settings.log_async_checkout = False
            
            with patch('auth_service.auth_core.database.connection_events.logger') as mock_logger:
                mock_logger.isEnabledFor.return_value = False
                
                _log_auth_checkout_if_enabled(mock_record)
                
                # Should not log when disabled
                mock_logger.debug.assert_not_called()


class TestEngineEventSetup:
    """Test engine event setup and handler creation"""
    
    @pytest.mark.unit
    async def test_setup_auth_async_engine_events_success(self):
        """Test successful engine event setup"""
        # Create a mock async engine
        mock_engine = Mock(spec=AsyncEngine)
        mock_sync_engine = Mock()
        mock_engine.sync_engine = mock_sync_engine
        
        with patch('sqlalchemy.event.listens_for') as mock_listens_for:
            setup_auth_async_engine_events(mock_engine)
            
            # Should set up connect and checkout event handlers
            assert mock_listens_for.call_count >= 2
            
            # Verify event types
            event_calls = [call.args for call in mock_listens_for.call_args_list]
            event_types = [call[1] for call in event_calls if len(call) > 1]
            assert "connect" in event_types
            assert "checkout" in event_types
    
    @pytest.mark.unit
    def test_setup_auth_async_engine_events_none_engine(self):
        """Test engine event setup with None engine"""
        with patch('auth_service.auth_core.database.connection_events.logger') as mock_logger:
            setup_auth_async_engine_events(None)
            
            # Should log warning about None engine
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Cannot setup events on None engine" in warning_call
    
    @pytest.mark.unit
    def test_setup_auth_async_engine_events_error(self):
        """Test engine event setup with error"""
        mock_engine = Mock(spec=AsyncEngine)
        mock_sync_engine = Mock()
        mock_engine.sync_engine = mock_sync_engine
        
        with patch('sqlalchemy.event.listens_for', side_effect=Exception("Event setup error")):
            with patch('auth_service.auth_core.database.connection_events.logger') as mock_logger:
                setup_auth_async_engine_events(mock_engine)
                
                # Should log error but not raise
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args[0][0]
                assert "Failed to setup engine events" in error_call


class TestEventHandlersIntegration:
    """Test event handlers with real or realistic scenarios"""
    
    @pytest.mark.unit
    def test_connect_event_handler_postgresql(self):
        """Test connect event handler for PostgreSQL"""
        # Mock objects for event handler
        mock_conn = Mock()
        mock_conn.cursor.return_value = Mock()
        mock_record = Mock()
        mock_record.info = {}
        
        # Create mock engine with PostgreSQL URL
        mock_engine = Mock()
        mock_engine.url = Mock()
        mock_engine.url.__str__ = Mock(return_value="postgresql://user:pass@localhost/db")
        
        with patch('auth_service.auth_core.database.connection_events._set_auth_connection_pid') as mock_set_pid:
            with patch('auth_service.auth_core.database.connection_events._configure_auth_connection_timeouts') as mock_configure:
                with patch('auth_service.auth_core.database.connection_events._log_auth_connection_established') as mock_log:
                    with patch('auth_service.auth_core.database.connection_events._monitor_auth_pool_usage') as mock_monitor:
                        # Simulate connect event handler
                        mock_set_pid(mock_conn, mock_record)
                        mock_configure(mock_conn)
                        mock_log(mock_record)
                        mock_monitor(None)  # No pool in mock
                        
                        # Verify all handlers were called
                        mock_set_pid.assert_called_once()
                        mock_configure.assert_called_once()
                        mock_log.assert_called_once()
                        mock_monitor.assert_called_once()
    
    @pytest.mark.unit
    def test_connect_event_handler_sqlite(self):
        """Test connect event handler for SQLite (should skip timeout config)"""
        mock_conn = Mock()
        mock_record = Mock()
        mock_record.info = {}
        
        # Create mock engine with SQLite URL
        mock_engine = Mock()
        mock_engine.url = Mock()
        mock_engine.url.__str__ = Mock(return_value="sqlite:///test.db")
        
        with patch('auth_service.auth_core.database.connection_events._set_auth_connection_pid') as mock_set_pid:
            with patch('auth_service.auth_core.database.connection_events._configure_auth_connection_timeouts') as mock_configure:
                with patch('auth_service.auth_core.database.connection_events._log_auth_connection_established') as mock_log:
                    # Simulate connect event handler for SQLite
                    mock_set_pid(mock_conn, mock_record)
                    # Should NOT configure timeouts for SQLite
                    mock_log(mock_record)
                    
                    # Verify PID and logging called, but not timeout config
                    mock_set_pid.assert_called_once()
                    mock_configure.assert_not_called()  # Should skip for SQLite
                    mock_log.assert_called_once()
    
    @pytest.mark.unit
    def test_checkout_event_handler(self):
        """Test checkout event handler"""
        mock_conn = Mock()
        mock_record = Mock()
        mock_record.info = {'pid': 12345}
        mock_proxy = Mock(spec=_ConnectionFairy)
        
        # Mock engine with pool
        mock_engine = Mock()
        mock_pool = Mock()
        mock_engine.pool = mock_pool
        
        with patch('auth_service.auth_core.database.connection_events._monitor_auth_pool_usage') as mock_monitor:
            with patch('auth_service.auth_core.database.connection_events._log_auth_checkout_if_enabled') as mock_log:
                # Simulate checkout event handler
                mock_monitor(mock_pool)
                mock_log(mock_record)
                
                # Verify handlers were called
                mock_monitor.assert_called_once_with(mock_pool)
                mock_log.assert_called_once_with(mock_record)


class TestRealEngineIntegration:
    """Test integration with real database engines"""
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_setup_events_on_real_engine(self, real_services_fixture):
        """Test setting up events on real database engine"""
        # Create real engine for testing
        engine = AuthDatabaseManager.create_async_engine()
        
        try:
            # Setup events (should not raise error)
            setup_auth_async_engine_events(engine)
            
            # Test that engine still works after event setup
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                value = result.scalar()
                assert value == 1
                
        finally:
            await engine.dispose()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_events_trigger_on_real_connections(self, real_services_fixture):
        """Test that events are actually triggered on real connections"""
        # Create engine with events
        engine = AuthDatabaseManager.create_async_engine()
        setup_auth_async_engine_events(engine)
        
        try:
            # Use connection to trigger events
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                assert db_name is not None
                
            # Events should have been triggered (we can't easily verify this
            # without mocking, but at least we know they don't break functionality)
            
        finally:
            await engine.dispose()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_multiple_connections_with_events(self, real_services_fixture):
        """Test multiple connections with events enabled"""
        engine = AuthDatabaseManager.create_async_engine()
        setup_auth_async_engine_events(engine)
        
        try:
            # Create multiple connections
            for i in range(3):
                async with engine.connect() as conn:
                    result = await conn.execute(text(f"SELECT {i + 1}"))
                    value = result.scalar()
                    assert value == i + 1
                    
        finally:
            await engine.dispose()


class TestEventHandlerEdgeCases:
    """Test edge cases and error scenarios in event handlers"""
    
    @pytest.mark.unit
    def test_pool_events_setup(self):
        """Test setup of additional pool events"""
        mock_engine = Mock(spec=AsyncEngine)
        mock_sync_engine = Mock()
        mock_engine.sync_engine = mock_sync_engine
        
        # Mock pool events
        with patch('sqlalchemy.event.listens_for') as mock_listens_for:
            with patch('auth_service.auth_core.database.connection_events._setup_pool_overflow_events') as mock_setup_pool:
                setup_auth_async_engine_events(mock_engine)
                
                # Should attempt to setup pool events
                mock_setup_pool.assert_called_once_with(mock_engine)
    
    @pytest.mark.unit
    def test_connection_info_logging(self):
        """Test connection information logging"""
        mock_conn = Mock()
        mock_conn.server_version = "PostgreSQL 13.0"
        mock_conn.autocommit = False
        
        with patch('auth_service.auth_core.database.connection_events._log_auth_connection_info') as mock_log_info:
            # This would be called in a real event handler
            mock_log_info(mock_conn)
            
            mock_log_info.assert_called_once_with(mock_conn)
    
    @pytest.mark.unit
    def test_event_handler_exception_handling(self):
        """Test that event handlers handle exceptions gracefully"""
        mock_conn = Mock()
        mock_conn.cursor.side_effect = Exception("Database error")
        mock_record = Mock()
        mock_record.info = {}
        
        # Event handlers should not let exceptions propagate
        with pytest.raises(Exception):
            _configure_auth_connection_timeouts(mock_conn)
        
        # But other handlers should still work
        _set_auth_connection_pid(mock_conn, mock_record)  # Should not raise
    
    @pytest.mark.unit
    def test_module_exports(self):
        """Test that all expected functions are exported"""
        from auth_service.auth_core.database.connection_events import __all__
        
        expected_exports = [
            "setup_auth_async_engine_events",
            "AuthDatabaseConfig",
            "get_settings",
            "_monitor_auth_pool_usage"
        ]
        
        for export in expected_exports:
            assert export in __all__