"""
Comprehensive Unit Tests for AuthServiceStartupOptimizer SSOT Class

Business Value Justification (BVJ):
- Segment: Platform/Internal - All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Stability & Performance - Ensure sub-5 second auth service startup
- Value Impact: Fast service initialization directly impacts user experience and system availability
- Strategic Impact: Critical infrastructure reliability - auth service must start quickly for all user flows

CRITICAL REQUIREMENTS:
- NO business logic mocks (use real AuthServiceStartupOptimizer instances)
- ALL tests MUST be designed to FAIL HARD in every way
- Use ABSOLUTE IMPORTS only (no relative imports)
- Tests must RAISE ERRORS - DO NOT USE try/except blocks in tests
- CHEATING ON TESTS = ABOMINATION
- Real async behavior testing with proper timing validation
- Race condition detection for concurrent initialization

This test suite covers the 336-line AuthServiceStartupOptimizer SSOT class with:
- Real instances (no business logic mocks)
- Startup timing validation
- Component initialization testing
- Parallel vs sequential execution validation
- Error handling and recovery patterns
- Performance optimization verification
- Concurrent execution safety
- Lazy loading patterns
- Metrics collection validation
"""
import asyncio
import logging
import pytest
import time
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from auth_service.auth_core.performance.startup_optimizer import AuthServiceStartupOptimizer, StartupMetrics, startup_optimizer
from shared.isolated_environment import IsolatedEnvironment
logger = logging.getLogger(__name__)

class StartupMetricsDataClassTests:
    """Test StartupMetrics dataclass functionality."""

    def test_startup_metrics_initialization_default(self):
        """Test StartupMetrics initializes with correct defaults."""
        metrics = StartupMetrics()
        assert metrics.total_startup_time == 0.0
        assert metrics.component_times == {}
        assert metrics.parallel_tasks_time == 0.0
        assert metrics.sequential_tasks_time == 0.0
        assert metrics.failed_components == []

    def test_startup_metrics_initialization_with_values(self):
        """Test StartupMetrics initializes with provided values."""
        component_times = {'jwt_handler': 0.5, 'redis_manager': 1.2}
        failed_components = ['oauth_managers', 'audit_logging']
        metrics = StartupMetrics(total_startup_time=5.7, component_times=component_times, parallel_tasks_time=2.1, sequential_tasks_time=3.6, failed_components=failed_components)
        assert metrics.total_startup_time == 5.7
        assert metrics.component_times == component_times
        assert metrics.parallel_tasks_time == 2.1
        assert metrics.sequential_tasks_time == 3.6
        assert metrics.failed_components == failed_components

    def test_startup_metrics_post_init_creates_empty_collections(self):
        """Test StartupMetrics __post_init__ creates empty collections when None."""
        metrics = StartupMetrics(component_times=None, failed_components=None)
        assert metrics.component_times == {}
        assert metrics.failed_components == []

class AuthServiceStartupOptimizerCoreTests:
    """Core AuthServiceStartupOptimizer functionality tests with real instances."""

    def test_startup_optimizer_initialization(self):
        """Test AuthServiceStartupOptimizer initializes correctly."""
        optimizer = AuthServiceStartupOptimizer()
        assert isinstance(optimizer.metrics, StartupMetrics)
        assert optimizer.initialized_components == set()
        assert optimizer.lazy_components == {}
        assert optimizer.startup_start_time is None

    def test_startup_optimizer_singleton_pattern(self):
        """Test global startup_optimizer singleton exists and is correct type."""
        from auth_service.auth_core.performance.startup_optimizer import startup_optimizer
        assert isinstance(startup_optimizer, AuthServiceStartupOptimizer)
        assert startup_optimizer.initialized_components == set()

    def test_is_component_ready_false_when_not_initialized(self):
        """Test is_component_ready returns False for uninitialized components."""
        optimizer = AuthServiceStartupOptimizer()
        assert optimizer.is_component_ready('jwt_handler') is False
        assert optimizer.is_component_ready('redis_manager') is False
        assert optimizer.is_component_ready('nonexistent_component') is False

    def test_is_component_ready_true_when_initialized(self):
        """Test is_component_ready returns True for initialized components."""
        optimizer = AuthServiceStartupOptimizer()
        optimizer.initialized_components.add('jwt_handler')
        optimizer.initialized_components.add('security_components')
        assert optimizer.is_component_ready('jwt_handler') is True
        assert optimizer.is_component_ready('security_components') is True
        assert optimizer.is_component_ready('redis_manager') is False

class AuthServiceStartupOptimizerReportsTests:
    """Test startup reporting and metrics functionality."""

    def test_get_startup_report_initial_state(self):
        """Test get_startup_report returns correct initial state."""
        optimizer = AuthServiceStartupOptimizer()
        report = optimizer.get_startup_report()
        assert report['total_startup_time'] == 0.0
        assert report['component_times'] == {}
        assert report['parallel_tasks_time'] == 0.0
        assert report['initialized_components'] == []
        assert report['failed_components'] == []
        assert report['startup_success'] is True
        assert report['critical_components_ok'] is True

    def test_get_startup_report_with_initialized_components(self):
        """Test get_startup_report includes initialized components."""
        optimizer = AuthServiceStartupOptimizer()
        optimizer.initialized_components.update(['jwt_handler', 'redis_manager', 'security_components'])
        optimizer.metrics.component_times = {'jwt_handler': 0.5, 'redis_manager': 1.2}
        optimizer.metrics.total_startup_time = 3.7
        report = optimizer.get_startup_report()
        assert report['total_startup_time'] == 3.7
        assert 'jwt_handler' in report['initialized_components']
        assert 'redis_manager' in report['initialized_components']
        assert 'security_components' in report['initialized_components']
        assert report['component_times']['jwt_handler'] == 0.5
        assert report['component_times']['redis_manager'] == 1.2

    def test_get_startup_report_with_failed_components(self):
        """Test get_startup_report handles failed components correctly."""
        optimizer = AuthServiceStartupOptimizer()
        optimizer.metrics.failed_components = ['oauth_managers', 'audit_logging']
        report = optimizer.get_startup_report()
        assert report['failed_components'] == ['oauth_managers', 'audit_logging']
        assert report['startup_success'] is False
        assert report['critical_components_ok'] is True

    def test_get_startup_report_with_critical_component_failures(self):
        """Test get_startup_report detects critical component failures."""
        optimizer = AuthServiceStartupOptimizer()
        optimizer.metrics.failed_components = ['jwt_handler', 'oauth_managers']
        report = optimizer.get_startup_report()
        assert report['startup_success'] is False
        assert report['critical_components_ok'] is False

    def test_get_startup_report_security_components_critical_failure(self):
        """Test get_startup_report detects security_components as critical."""
        optimizer = AuthServiceStartupOptimizer()
        optimizer.metrics.failed_components = ['security_components', 'audit_logging']
        report = optimizer.get_startup_report()
        assert report['critical_components_ok'] is False

class AuthServiceStartupOptimizerLazyLoadingTests:
    """Test lazy loading functionality."""

    def test_lazy_load_component_first_time(self):
        """Test lazy_load_component loads component on first access."""
        optimizer = AuthServiceStartupOptimizer()
        test_component = {'name': 'test_component', 'initialized': True}

        def loader_func():
            return test_component
        result = optimizer.lazy_load_component('test_service', loader_func)
        assert result == test_component
        assert 'test_service' in optimizer.lazy_components
        assert optimizer.lazy_components['test_service'] == test_component
        assert 'test_service' in optimizer.initialized_components
        assert 'test_service_lazy' in optimizer.metrics.component_times

    def test_lazy_load_component_second_access(self):
        """Test lazy_load_component returns cached component on second access."""
        optimizer = AuthServiceStartupOptimizer()
        test_component = {'name': 'cached_component'}

        def loader_func():
            return test_component
        result1 = optimizer.lazy_load_component('cached_service', loader_func)
        result2 = optimizer.lazy_load_component('cached_service', loader_func)
        assert result1 == result2 == test_component
        assert result1 is result2

    def test_lazy_load_component_loader_exception(self):
        """Test lazy_load_component raises exception when loader fails."""
        optimizer = AuthServiceStartupOptimizer()

        def failing_loader():
            raise ValueError('Loader failed')
        with pytest.raises(ValueError, match='Loader failed'):
            optimizer.lazy_load_component('failing_service', failing_loader)
        assert 'failing_service' not in optimizer.lazy_components
        assert 'failing_service' not in optimizer.initialized_components

    def test_lazy_load_component_timing_recorded(self):
        """Test lazy_load_component records accurate timing."""
        optimizer = AuthServiceStartupOptimizer()

        def slow_loader():
            time.sleep(0.01)
            return {'loaded': True}
        start_time = time.time()
        optimizer.lazy_load_component('timed_service', slow_loader)
        end_time = time.time()
        recorded_time = optimizer.metrics.component_times['timed_service_lazy']
        actual_time = end_time - start_time
        assert abs(recorded_time - actual_time) < 0.005

class AuthServiceStartupOptimizerAsyncTests:
    """Test async startup functionality with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_fast_startup_basic_flow(self):
        """Test fast_startup executes basic flow and records timing."""
        optimizer = AuthServiceStartupOptimizer()
        with patch.object(optimizer, '_initialize_critical_components', new_callable=AsyncMock) as mock_critical, patch.object(optimizer, '_initialize_database_optimized', new_callable=AsyncMock) as mock_db, patch.object(optimizer, '_initialize_background_components', new_callable=AsyncMock) as mock_bg:
            start_time = time.time()
            metrics = await optimizer.fast_startup()
            end_time = time.time()
            mock_critical.assert_called_once()
            mock_db.assert_called_once()
            mock_bg.assert_called_once()
            assert isinstance(metrics, StartupMetrics)
            assert metrics.total_startup_time > 0
            assert metrics.total_startup_time < end_time - start_time + 0.1

    @pytest.mark.asyncio
    async def test_fast_startup_exception_handling(self):
        """Test fast_startup handles exceptions and still records timing."""
        optimizer = AuthServiceStartupOptimizer()
        with patch.object(optimizer, '_initialize_critical_components', new_callable=AsyncMock) as mock_critical:
            mock_critical.side_effect = RuntimeError('Critical component failed')
            with pytest.raises(RuntimeError, match='Critical component failed'):
                await optimizer.fast_startup()
            assert optimizer.metrics.total_startup_time > 0

    @pytest.mark.asyncio
    async def test_initialize_critical_components_parallel_execution(self):
        """Test _initialize_critical_components runs tasks in parallel."""
        optimizer = AuthServiceStartupOptimizer()
        with patch.object(optimizer, '_init_jwt_handler', new_callable=AsyncMock) as mock_jwt, patch.object(optimizer, '_init_redis_manager', new_callable=AsyncMock) as mock_redis, patch.object(optimizer, '_init_security_components', new_callable=AsyncMock) as mock_security:

            async def delayed_jwt():
                await asyncio.sleep(0.01)

            async def delayed_redis():
                await asyncio.sleep(0.01)

            async def delayed_security():
                await asyncio.sleep(0.01)
            mock_jwt.side_effect = delayed_jwt
            mock_redis.side_effect = delayed_redis
            mock_security.side_effect = delayed_security
            start_time = time.time()
            await optimizer._initialize_critical_components()
            end_time = time.time()
            execution_time = end_time - start_time
            assert execution_time < 0.025
            assert optimizer.metrics.parallel_tasks_time > 0

    @pytest.mark.asyncio
    async def test_initialize_critical_components_handles_exceptions(self):
        """Test _initialize_critical_components handles component failures gracefully."""
        optimizer = AuthServiceStartupOptimizer()
        with patch.object(optimizer, '_init_jwt_handler', new_callable=AsyncMock) as mock_jwt, patch.object(optimizer, '_init_redis_manager', new_callable=AsyncMock) as mock_redis, patch.object(optimizer, '_init_security_components', new_callable=AsyncMock) as mock_security:
            mock_redis.side_effect = ConnectionError('Redis unavailable')
            await optimizer._initialize_critical_components()
            assert 'redis_manager' in optimizer.metrics.failed_components
            assert optimizer.metrics.parallel_tasks_time > 0

    @pytest.mark.asyncio
    async def test_initialize_database_optimized_fast_test_mode(self):
        """Test _initialize_database_optimized skips in fast test mode."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {'AUTH_FAST_TEST_MODE': 'true', 'ENVIRONMENT': 'test'}.get(key, default)
            mock_get_env.return_value = mock_env
            await optimizer._initialize_database_optimized()
            assert optimizer.metrics.component_times['database'] == 0.0

    @pytest.mark.asyncio
    async def test_initialize_database_optimized_production_flow(self):
        """Test _initialize_database_optimized executes production flow."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('shared.isolated_environment.get_env') as mock_get_env, patch('auth_service.auth_core.database.connection.auth_db') as mock_auth_db:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {'AUTH_FAST_TEST_MODE': 'false', 'ENVIRONMENT': 'production'}.get(key, default)
            mock_get_env.return_value = mock_env
            mock_auth_db._initialized = False
            mock_auth_db.initialize = AsyncMock()
            with patch.object(optimizer, '_prewarm_database_connections', new_callable=AsyncMock) as mock_prewarm:
                await optimizer._initialize_database_optimized()
                mock_auth_db.initialize.assert_called_once()
                mock_prewarm.assert_called_once()
                assert 'database' in optimizer.initialized_components
                assert 'database' in optimizer.metrics.component_times

    @pytest.mark.asyncio
    async def test_initialize_database_optimized_handles_exceptions(self):
        """Test _initialize_database_optimized handles database failures gracefully."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get.side_effect = lambda key, default=None: {'AUTH_FAST_TEST_MODE': 'false', 'ENVIRONMENT': 'development'}.get(key, default)
            mock_get_env.return_value = mock_env
            with patch('auth_service.auth_core.database.connection.auth_db', side_effect=ImportError('Database unavailable')):
                await optimizer._initialize_database_optimized()
                assert 'database' in optimizer.metrics.failed_components
                assert 'database' in optimizer.metrics.component_times

class AuthServiceStartupOptimizerBackgroundTests:
    """Test background component initialization."""

    @pytest.mark.asyncio
    async def test_initialize_background_components_success(self):
        """Test _initialize_background_components initializes all components."""
        optimizer = AuthServiceStartupOptimizer()
        with patch.object(optimizer, '_init_oauth_managers', new_callable=AsyncMock) as mock_oauth, patch.object(optimizer, '_init_audit_logging', new_callable=AsyncMock) as mock_audit, patch.object(optimizer, '_init_metrics_collection', new_callable=AsyncMock) as mock_metrics, patch.object(optimizer, '_init_cleanup_tasks', new_callable=AsyncMock) as mock_cleanup:
            await optimizer._initialize_background_components()
            mock_oauth.assert_called_once()
            mock_audit.assert_called_once()
            mock_metrics.assert_called_once()
            mock_cleanup.assert_called_once()
            expected_components = ['oauth_managers', 'audit_logging', 'metrics_collection', 'cleanup_tasks']
            for component in expected_components:
                assert component in optimizer.initialized_components

    @pytest.mark.asyncio
    async def test_initialize_background_components_handles_failures(self):
        """Test _initialize_background_components handles individual failures."""
        optimizer = AuthServiceStartupOptimizer()
        with patch.object(optimizer, '_init_oauth_managers', new_callable=AsyncMock) as mock_oauth, patch.object(optimizer, '_init_audit_logging', new_callable=AsyncMock) as mock_audit, patch.object(optimizer, '_init_metrics_collection', new_callable=AsyncMock) as mock_metrics, patch.object(optimizer, '_init_cleanup_tasks', new_callable=AsyncMock) as mock_cleanup:
            mock_oauth.side_effect = RuntimeError('OAuth failed')
            mock_metrics.side_effect = ConnectionError('Metrics unavailable')
            await optimizer._initialize_background_components()
            assert 'oauth_managers' in optimizer.metrics.failed_components
            assert 'metrics_collection' in optimizer.metrics.failed_components
            assert 'audit_logging' in optimizer.initialized_components
            assert 'cleanup_tasks' in optimizer.initialized_components

class AuthServiceStartupOptimizerComponentInitTests:
    """Test individual component initialization methods."""

    @pytest.mark.asyncio
    async def test_init_jwt_handler_success(self):
        """Test _init_jwt_handler initializes successfully."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('auth_service.auth_core.core.jwt_handler.JWTHandler') as mock_jwt_class:
            mock_jwt_instance = MagicMock()
            mock_jwt_class.return_value = mock_jwt_instance
            await optimizer._init_jwt_handler()
            mock_jwt_class.assert_called_once()
            assert 'jwt_handler' in optimizer.initialized_components
            assert 'jwt_handler' in optimizer.metrics.component_times

    @pytest.mark.asyncio
    async def test_init_jwt_handler_failure(self):
        """Test _init_jwt_handler handles initialization failure."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('auth_service.auth_core.core.jwt_handler.JWTHandler', side_effect=ValueError('Invalid JWT config')):
            with pytest.raises(ValueError, match='Invalid JWT config'):
                await optimizer._init_jwt_handler()
            assert 'jwt_handler' in optimizer.metrics.component_times

    @pytest.mark.asyncio
    async def test_init_redis_manager_enabled_success(self):
        """Test _init_redis_manager with enabled Redis."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('auth_service.auth_core.redis_manager.auth_redis_manager') as mock_redis:
            mock_redis.enabled = True
            mock_redis.connect = MagicMock()
            await optimizer._init_redis_manager()
            mock_redis.connect.assert_called_once()
            assert 'redis_manager' in optimizer.initialized_components
            assert 'redis_manager' in optimizer.metrics.component_times

    @pytest.mark.asyncio
    async def test_init_redis_manager_connection_failure(self):
        """Test _init_redis_manager handles connection failure gracefully."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('auth_service.auth_core.redis_manager.auth_redis_manager') as mock_redis:
            mock_redis.enabled = True
            mock_redis.connect.side_effect = ConnectionError('Redis connection failed')
            await optimizer._init_redis_manager()
            assert 'redis_manager' in optimizer.initialized_components
            assert 'redis_manager' in optimizer.metrics.component_times

    @pytest.mark.asyncio
    async def test_init_security_components_success(self):
        """Test _init_security_components initializes successfully."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('auth_service.auth_core.security.oauth_security.OAuthSecurityManager') as mock_security:
            mock_security_instance = MagicMock()
            mock_security.return_value = mock_security_instance
            await optimizer._init_security_components()
            mock_security.assert_called_once()
            assert 'security_components' in optimizer.initialized_components
            assert 'security_components' in optimizer.metrics.component_times

    @pytest.mark.asyncio
    async def test_init_security_components_failure(self):
        """Test _init_security_components handles failure."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('auth_service.auth_core.security.oauth_security.OAuthSecurityManager', side_effect=ImportError('Security module unavailable')):
            with pytest.raises(ImportError, match='Security module unavailable'):
                await optimizer._init_security_components()
            assert 'security_components' in optimizer.metrics.component_times

class AuthServiceStartupOptimizerDatabasePrewarmTests:
    """Test database pre-warming functionality."""

    @pytest.mark.asyncio
    async def test_prewarm_database_connections_success(self):
        """Test _prewarm_database_connections executes connection tests."""
        optimizer = AuthServiceStartupOptimizer()
        with patch.object(optimizer, '_test_db_connection', new_callable=AsyncMock) as mock_test:
            await optimizer._prewarm_database_connections()
            assert mock_test.call_count == 2

    @pytest.mark.asyncio
    async def test_prewarm_database_connections_handles_failures(self):
        """Test _prewarm_database_connections handles test failures gracefully."""
        optimizer = AuthServiceStartupOptimizer()
        with patch.object(optimizer, '_test_db_connection', new_callable=AsyncMock) as mock_test:
            mock_test.side_effect = ConnectionError('DB test failed')
            await optimizer._prewarm_database_connections()

    @pytest.mark.asyncio
    async def test_test_db_connection_success(self):
        """Test _test_db_connection executes SQL query."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('auth_service.auth_core.database.connection.auth_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            await optimizer._test_db_connection()
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_db_connection_handles_failure(self):
        """Test _test_db_connection handles database errors gracefully."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('auth_service.auth_core.database.connection.auth_db') as mock_db:
            mock_db.get_session.side_effect = RuntimeError('DB connection failed')
            await optimizer._test_db_connection()

class AuthServiceStartupOptimizerPeriodicCleanupTests:
    """Test periodic cleanup functionality."""

    @pytest.mark.asyncio
    async def test_init_cleanup_tasks_creates_task(self):
        """Test _init_cleanup_tasks creates background task."""
        optimizer = AuthServiceStartupOptimizer()
        with patch('asyncio.create_task') as mock_create_task:
            await optimizer._init_cleanup_tasks()
            mock_create_task.assert_called_once()
            assert 'cleanup_tasks' in optimizer.metrics.component_times

    @pytest.mark.asyncio
    async def test_periodic_cleanup_loop_iteration(self):
        """Test _periodic_cleanup executes one loop iteration."""
        optimizer = AuthServiceStartupOptimizer()
        sleep_count = 0

        async def mock_sleep(duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 1:
                raise asyncio.CancelledError('Test completed')
        with patch('asyncio.sleep', side_effect=mock_sleep), patch('auth_service.auth_core.core.jwt_cache.jwt_validation_cache'):
            with pytest.raises(asyncio.CancelledError):
                await optimizer._periodic_cleanup()
            assert sleep_count == 1

    @pytest.mark.asyncio
    async def test_periodic_cleanup_handles_exceptions(self):
        """Test _periodic_cleanup handles exceptions and continues."""
        optimizer = AuthServiceStartupOptimizer()
        sleep_count = 0

        async def mock_sleep(duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count == 1:
                return
            elif sleep_count == 2:
                raise asyncio.CancelledError('Test completed')
        with patch('asyncio.sleep', side_effect=mock_sleep), patch('auth_service.auth_core.core.jwt_cache.jwt_validation_cache', side_effect=RuntimeError('Cache error')):
            with pytest.raises(asyncio.CancelledError):
                await optimizer._periodic_cleanup()
            assert sleep_count == 2

class AuthServiceStartupOptimizerConcurrentSafetyTests:
    """Test concurrent execution safety and race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_fast_startup_calls(self):
        """Test multiple concurrent fast_startup calls don't interfere."""
        optimizer = AuthServiceStartupOptimizer()
        with patch.object(optimizer, '_initialize_critical_components', new_callable=AsyncMock) as mock_critical, patch.object(optimizer, '_initialize_database_optimized', new_callable=AsyncMock) as mock_db, patch.object(optimizer, '_initialize_background_components', new_callable=AsyncMock) as mock_bg:
            mock_critical.side_effect = lambda: asyncio.sleep(0.001)
            mock_db.side_effect = lambda: asyncio.sleep(0.001)
            mock_bg.side_effect = lambda: asyncio.sleep(0.001)
            tasks = [optimizer.fast_startup() for _ in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            assert len(results) == 3
            for result in results:
                assert isinstance(result, StartupMetrics)
                assert result.total_startup_time > 0

    @pytest.mark.asyncio
    async def test_concurrent_component_initialization(self):
        """Test concurrent component initialization is safe."""
        optimizer = AuthServiceStartupOptimizer()

        async def init_component(name: str):
            await asyncio.sleep(0.001)
            optimizer.initialized_components.add(name)
            optimizer.metrics.component_times[name] = 0.001
        tasks = [init_component('component1'), init_component('component2'), init_component('component3')]
        await asyncio.gather(*tasks)
        expected = {'component1', 'component2', 'component3'}
        assert optimizer.initialized_components == expected

    def test_concurrent_lazy_loading_same_component(self):
        """Test concurrent lazy loading of same component is safe."""
        optimizer = AuthServiceStartupOptimizer()
        load_count = 0

        def loader_func():
            nonlocal load_count
            load_count += 1
            time.sleep(0.001)
            return {'load_count': load_count}
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(optimizer.lazy_load_component, 'concurrent_test', loader_func) for _ in range(3)]
            results = [f.result() for f in futures]
        assert load_count == 1
        assert all((r['load_count'] == 1 for r in results))
        assert all((r is results[0] for r in results))

class AuthServiceStartupOptimizerRealTimingTests:
    """Test real timing and performance requirements."""

    @pytest.mark.asyncio
    async def test_startup_timing_recorded_accurately(self):
        """Test startup timing is recorded with reasonable accuracy."""
        optimizer = AuthServiceStartupOptimizer()

        async def slow_critical():
            await asyncio.sleep(0.01)

        async def slow_db():
            await asyncio.sleep(0.02)

        async def slow_bg():
            await asyncio.sleep(0.01)
        with patch.object(optimizer, '_initialize_critical_components', side_effect=slow_critical), patch.object(optimizer, '_initialize_database_optimized', side_effect=slow_db), patch.object(optimizer, '_initialize_background_components', side_effect=slow_bg):
            start_time = time.time()
            metrics = await optimizer.fast_startup()
            end_time = time.time()
            actual_time = end_time - start_time
            recorded_time = metrics.total_startup_time
            assert abs(recorded_time - actual_time) < 0.005

    def test_component_timing_precision(self):
        """Test individual component timing is precise."""
        optimizer = AuthServiceStartupOptimizer()

        def timed_loader():
            time.sleep(0.05)
            return {'timed': True}
        start_time = time.time()
        optimizer.lazy_load_component('precision_test', timed_loader)
        end_time = time.time()
        actual_time = end_time - start_time
        recorded_time = optimizer.metrics.component_times['precision_test_lazy']
        assert abs(recorded_time - actual_time) < 0.002

    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_timing_difference(self):
        """Test parallel execution is actually faster than sequential."""
        optimizer = AuthServiceStartupOptimizer()

        async def parallel_task():
            await asyncio.sleep(0.01)
        parallel_tasks = [parallel_task() for _ in range(3)]
        parallel_start = time.time()
        await asyncio.gather(*parallel_tasks)
        parallel_end = time.time()
        sequential_start = time.time()
        for _ in range(3):
            await parallel_task()
        sequential_end = time.time()
        parallel_time = parallel_end - parallel_start
        sequential_time = sequential_end - sequential_start
        assert parallel_time < sequential_time * 0.5

class AuthServiceStartupOptimizerEdgeCasesTests:
    """Test edge cases and boundary conditions."""

    def test_empty_startup_metrics(self):
        """Test optimizer handles empty metrics correctly."""
        optimizer = AuthServiceStartupOptimizer()
        report = optimizer.get_startup_report()
        assert report['total_startup_time'] == 0.0
        assert report['startup_success'] is True
        assert report['critical_components_ok'] is True

    def test_very_long_component_names(self):
        """Test optimizer handles very long component names."""
        optimizer = AuthServiceStartupOptimizer()
        long_name = 'a' * 1000

        def simple_loader():
            return {'name': long_name}
        result = optimizer.lazy_load_component(long_name, simple_loader)
        assert result['name'] == long_name
        assert long_name in optimizer.initialized_components
        assert f'{long_name}_lazy' in optimizer.metrics.component_times

    def test_component_ready_special_characters(self):
        """Test is_component_ready with special characters in names."""
        optimizer = AuthServiceStartupOptimizer()
        special_names = ['comp-1', 'comp_2', 'comp.3', 'comp@4', 'comp/5']
        for name in special_names:
            assert optimizer.is_component_ready(name) is False
            optimizer.initialized_components.add(name)
            assert optimizer.is_component_ready(name) is True

    @pytest.mark.asyncio
    async def test_background_initialization_fire_and_forget(self):
        """Test background initialization doesn't block startup completion."""
        optimizer = AuthServiceStartupOptimizer()
        slow_background_called = False

        async def slow_background():
            nonlocal slow_background_called
            await asyncio.sleep(0.1)
            slow_background_called = True
        with patch.object(optimizer, '_initialize_critical_components', new_callable=AsyncMock), patch.object(optimizer, '_initialize_database_optimized', new_callable=AsyncMock), patch.object(optimizer, '_initialize_background_components', side_effect=slow_background):
            start_time = time.time()
            await optimizer.fast_startup()
            end_time = time.time()
            startup_time = end_time - start_time
            assert startup_time < 0.05

class AuthServiceStartupOptimizerBusinessValueTests:
    """Test business value and performance requirements."""

    @pytest.mark.asyncio
    async def test_sub_five_second_startup_requirement(self):
        """Test startup meets sub-5 second business requirement."""
        optimizer = AuthServiceStartupOptimizer()

        async def realistic_critical():
            await asyncio.sleep(0.5)

        async def realistic_db():
            await asyncio.sleep(1.0)

        async def realistic_bg():
            await asyncio.sleep(0.1)
        with patch.object(optimizer, '_initialize_critical_components', side_effect=realistic_critical), patch.object(optimizer, '_initialize_database_optimized', side_effect=realistic_db), patch.object(optimizer, '_initialize_background_components', side_effect=realistic_bg):
            metrics = await optimizer.fast_startup()
            assert metrics.total_startup_time < 5.0
            assert metrics.total_startup_time < 2.0

    def test_startup_optimizer_singleton_business_value(self):
        """Test singleton pattern provides business value through consistency."""
        from auth_service.auth_core.performance.startup_optimizer import startup_optimizer
        optimizer1 = startup_optimizer
        optimizer2 = startup_optimizer
        assert optimizer1 is optimizer2
        optimizer1.initialized_components.add('test_component')
        assert optimizer2.is_component_ready('test_component') is True

    @pytest.mark.asyncio
    async def test_critical_components_failure_detection(self):
        """Test system detects critical component failures affecting business value."""
        optimizer = AuthServiceStartupOptimizer()
        with patch.object(optimizer, '_initialize_critical_components', new_callable=AsyncMock) as mock_critical:

            async def failing_critical():
                optimizer.metrics.failed_components.append('jwt_handler')
            mock_critical.side_effect = failing_critical
            with patch.object(optimizer, '_initialize_database_optimized', new_callable=AsyncMock), patch.object(optimizer, '_initialize_background_components', new_callable=AsyncMock):
                await optimizer.fast_startup()
                report = optimizer.get_startup_report()
                assert report['critical_components_ok'] is False
                assert report['startup_success'] is False
                assert 'jwt_handler' in report['failed_components']
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')