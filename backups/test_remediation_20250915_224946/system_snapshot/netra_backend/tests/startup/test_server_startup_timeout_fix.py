"""Backend Server Startup Timeout Fix Test

Business Value Justification (BVJ):
- Segment: All (Platform Foundation)  
- Business Goal: Ensure backend starts within reasonable time limits
- Value Impact: Prevents infinite startup hangs, enables reliable deployments
- Revenue Impact: Critical - ensures platform can start and serve customers

This test validates the timeout fixes added to prevent database initialization 
and startup checks from hanging the server startup indefinitely.
"""
from test_framework.performance_helpers import fast_test, timeout_override
import asyncio
import time
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment
import pytest
from fastapi import FastAPI
from netra_backend.app.startup_module import setup_database_connections, startup_health_checks, _async_initialize_postgres

class ServerStartupTimeoutsTests:
    """Test timeout protections in server startup."""

    @fast_test
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_database_initialization_timeout_protection(self):
        """Test that database initialization has timeout protection."""
        app = FastAPI()
        with patch('netra_backend.app.startup_module._async_initialize_postgres') as mock_init:

            async def hanging_init(logger):
                await asyncio.sleep(20)
                return None
            mock_init.side_effect = hanging_init
            start_time = time.time()
            await setup_database_connections(app)
            elapsed = time.time() - start_time
            assert elapsed < 17, f'Database setup took too long: {elapsed}s (should timeout at ~15s)'
            assert not getattr(app.state, 'database_available', True)
            assert getattr(app.state, 'database_mock_mode', False) == True
            print(f' PASS:  Database timeout protection working - completed in {elapsed:.1f}s')

    @fast_test
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_startup_health_checks_timeout_protection(self):
        """Test that startup health checks have timeout protection."""
        app = FastAPI()
        with patch('netra_backend.app.startup_checks.run_startup_checks') as mock_checks:

            async def hanging_checks(app):
                await asyncio.sleep(25)
                return {'passed': 5, 'total_checks': 5}
            mock_checks.side_effect = hanging_checks
            mock_logger = MagicNone
            start_time = time.time()
            await startup_health_checks(app, mock_logger)
            elapsed = time.time() - start_time
            assert elapsed < 22, f'Health checks took too long: {elapsed}s (should timeout at ~20s)'
            print(f' PASS:  Health checks timeout protection working - completed in {elapsed:.1f}s')

    @fast_test
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_async_postgres_initialization_wrapper(self):
        """Test the async postgres initialization wrapper."""
        mock_logger = MagicNone
        with patch('netra_backend.app.startup_module.initialize_postgres') as mock_init:
            mock_session_factory = MagicNone
            mock_init.return_value = mock_session_factory
            result = await _async_initialize_postgres(mock_logger)
            assert result == mock_session_factory
            mock_init.assert_called_once()
            print(' PASS:  Async postgres wrapper handles successful initialization')
        with patch('netra_backend.app.startup_module.initialize_postgres') as mock_init:
            mock_init.side_effect = Exception('Database connection failed')
            result = await _async_initialize_postgres(mock_logger)
            assert result is None
            mock_logger.error.assert_called()
            print(' PASS:  Async postgres wrapper handles failed initialization')

    @fast_test
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_database_setup_graceful_degradation(self):
        """Test database setup graceful degradation on timeout."""
        app = FastAPI()
        with patch('netra_backend.app.startup_module.get_config') as mock_config:
            config_mock = MagicNone
            config_mock.database_url = 'postgresql://test:test@localhost/test'
            config_mock.graceful_startup_mode = 'true'
            mock_config.return_value = config_mock
            with patch('netra_backend.app.startup_module._is_postgres_service_mock_mode', return_value=False):
                with patch('netra_backend.app.startup_module._is_mock_database_url', return_value=False):
                    with patch('netra_backend.app.startup_module._async_initialize_postgres') as mock_init:

                        async def timeout_init(logger):
                            await asyncio.sleep(20)
                            return None
                        mock_init.side_effect = timeout_init
                        await setup_database_connections(app)
                        assert not getattr(app.state, 'database_available', True)
                        assert getattr(app.state, 'database_mock_mode', False) == True
                        print(' PASS:  Graceful degradation working on database timeout')

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_database_setup_fast_success(self):
        """Test that database setup works quickly when everything is working."""
        app = FastAPI()
        with patch('netra_backend.app.startup_module.get_config') as mock_config:
            config_mock = MagicNone
            config_mock.database_url = 'postgresql://test:test@localhost/test'
            config_mock.graceful_startup_mode = 'true'
            mock_config.return_value = config_mock
            with patch('netra_backend.app.startup_module._is_postgres_service_mock_mode', return_value=False):
                with patch('netra_backend.app.startup_module._is_mock_database_url', return_value=False):
                    with patch('netra_backend.app.startup_module._async_initialize_postgres') as mock_init:
                        mock_session_factory = MagicNone
                        mock_init.return_value = mock_session_factory
                        with patch('netra_backend.app.startup_module._ensure_database_tables_exist'):
                            start_time = time.time()
                            await setup_database_connections(app)
                            elapsed = time.time() - start_time
                            assert elapsed < 2, f'Fast setup took too long: {elapsed}s'
                            assert getattr(app.state, 'database_available', False)
                            assert app.state.db_session_factory == mock_session_factory
                            print(f' PASS:  Fast database setup working - completed in {elapsed:.1f}s')

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mock_database_mode_fast_path(self):
        """Test that mock database mode bypasses all timeout logic."""
        app = FastAPI()
        with patch('netra_backend.app.startup_module.get_config') as mock_config:
            config_mock = MagicNone
            config_mock.database_url = 'sqlite+aiosqlite:///:memory:'
            config_mock.graceful_startup_mode = 'true'
            mock_config.return_value = config_mock
            start_time = time.time()
            await setup_database_connections(app)
            elapsed = time.time() - start_time
            assert elapsed < 0.1, f'Mock database setup took too long: {elapsed}s'
            assert not getattr(app.state, 'database_available', True)
            assert getattr(app.state, 'database_mock_mode', False)
            print(f' PASS:  Mock database mode fast path working - completed in {elapsed:.3f}s')

@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_startup_with_timeouts():
    """Test complete startup sequence with timeout protections."""
    print('\n=== TESTING COMPLETE STARTUP WITH TIMEOUT PROTECTIONS ===')
    app = FastAPI()
    with patch('netra_backend.app.startup_module.get_config') as mock_config:
        config_mock = MagicNone
        config_mock.graceful_startup_mode = 'true'
        config_mock.disable_startup_checks = 'false'
        config_mock.fast_startup_mode = 'false'
        config_mock.database_url = 'sqlite+aiosqlite:///:memory:'
        mock_config.return_value = config_mock
        from netra_backend.app.startup_module import initialize_logging, initialize_core_services
        start_time = time.time()
        startup_time, logger = initialize_logging()
        await setup_database_connections(app)
        await startup_health_checks(app, logger)
        elapsed = time.time() - start_time
        assert elapsed < 5, f'Complete startup took too long: {elapsed}s'
        print(f' PASS:  Complete startup with timeouts working - completed in {elapsed:.1f}s')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')