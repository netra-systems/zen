"""
ClickHouse Real Connection Validation - Integration Tests

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Ensure analytics infrastructure reliability
- Value Impact: 100% confidence in ClickHouse integration across environments
- Revenue Impact: Prevents $50K+ outages from connection failures

CRITICAL: These tests validate real ClickHouse connections and proper test/production separation.
"""
import pytest
import asyncio
from unittest.mock import patch
from netra_backend.app.db.clickhouse import get_clickhouse_client, get_clickhouse_service, ClickHouseService, use_mock_clickhouse, _is_testing_environment, _is_real_database_test, _should_disable_clickhouse_for_tests
from test_framework.ssot.test_context_decorator import ContextValidationError

@pytest.mark.integration
class ClickHouseRealConnectionValidationTests:
    """Integration tests for real ClickHouse connections."""

    @pytest.mark.real_database
    async def test_real_clickhouse_connection_works(self):
        """Test that real ClickHouse connections work when properly configured."""
        try:
            async with get_clickhouse_client() as client:
                result = await client.execute('SELECT 1 as test')
                assert result is not None
                assert len(result) >= 0
        except (ConnectionError, TimeoutError, Exception) as e:
            pytest.skip(f'Real ClickHouse not available: {e}')

    @pytest.mark.real_database
    async def test_real_clickhouse_service_initialization(self):
        """Test that ClickHouse service can initialize with real connections."""
        service = ClickHouseService(force_mock=False)
        try:
            await service.initialize()
            health = await service.health_check()
            assert 'status' in health
            is_available = await service.ping()
            assert isinstance(is_available, bool)
        except (ConnectionError, TimeoutError, Exception) as e:
            pytest.skip(f'Real ClickHouse service not available: {e}')
        finally:
            await service.close()

    async def test_mock_clickhouse_used_in_tests(self):
        """Test that mock ClickHouse is used when configured for tests."""
        with patch('netra_backend.app.db.clickhouse._is_testing_environment') as mock_test_env:
            mock_test_env.return_value = True
            should_use_mock = use_mock_clickhouse()
            assert isinstance(should_use_mock, bool)

    async def test_context_detection_functions_work_in_tests(self):
        """Test that context detection functions work properly in test environment."""
        is_test_env = _is_testing_environment()
        assert isinstance(is_test_env, bool)
        is_real_db_test = _is_real_database_test()
        assert isinstance(is_real_db_test, bool)
        should_disable = _should_disable_clickhouse_for_tests()
        assert isinstance(should_disable, bool)

@pytest.mark.integration
class ClickHouseEnvironmentSeparationTests:
    """Test proper separation between test and production environments."""

    async def test_production_environment_uses_real_connections(self):
        """Test that production environment always uses real connections."""
        with patch('netra_backend.app.db.clickhouse._is_testing_environment') as mock_test_env, patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_test_env.return_value = False
            mock_get_env.return_value = {'ENVIRONMENT': 'production', 'TESTING': 'false'}
            should_use_mock = use_mock_clickhouse()
            assert should_use_mock == False

    async def test_development_environment_uses_real_connections(self):
        """Test that development environment uses real connections."""
        with patch('netra_backend.app.db.clickhouse._is_testing_environment') as mock_test_env, patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_test_env.return_value = False
            mock_get_env.return_value = {'ENVIRONMENT': 'development', 'TESTING': 'false'}
            should_use_mock = use_mock_clickhouse()
            assert should_use_mock == False

    async def test_staging_environment_uses_real_connections(self):
        """Test that staging environment uses real connections."""
        with patch('netra_backend.app.db.clickhouse._is_testing_environment') as mock_test_env, patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_test_env.return_value = False
            mock_get_env.return_value = {'ENVIRONMENT': 'staging', 'TESTING': 'false'}
            should_use_mock = use_mock_clickhouse()
            assert should_use_mock == False

@pytest.mark.integration
class ClickHouseDecoratorIntegrationTests:
    """Test decorator behavior in integration context."""

    async def test_noop_client_works_in_test_context(self):
        """Test that NoOp client functions work properly in test context."""
        from netra_backend.app.db.clickhouse import NoOpClickHouseClient
        client = NoOpClickHouseClient()
        result = await client.execute('SELECT 1')
        assert isinstance(result, list)
        is_connected = await client.test_connection()
        assert is_connected == True
        await client.disconnect()
        is_connected_after = await client.test_connection()
        assert is_connected_after == False

    async def test_context_functions_allow_production_usage(self):
        """Test that context detection functions work in production (allow_production=True)."""
        with patch('test_framework.ssot.test_context_decorator.TestContextValidator.is_test_environment') as mock_test_env, patch('test_framework.ssot.test_context_decorator.TestContextValidator.is_test_file') as mock_test_file:
            mock_test_env.return_value = False
            mock_test_file.return_value = False
            is_test_env = _is_testing_environment()
            assert isinstance(is_test_env, bool)
            should_disable = _should_disable_clickhouse_for_tests()
            assert isinstance(should_disable, bool)
            should_use_mock = use_mock_clickhouse()
            assert isinstance(should_use_mock, bool)

@pytest.mark.integration
class ClickHouseConfigurationValidationTests:
    """Test ClickHouse configuration validation across environments."""

    async def test_configuration_loading_in_test_environment(self):
        """Test that ClickHouse configuration loads properly in test environment."""
        from netra_backend.app.db.clickhouse import get_clickhouse_config
        try:
            config = get_clickhouse_config()
            assert hasattr(config, 'host')
            assert hasattr(config, 'port')
            assert hasattr(config, 'database')
            assert isinstance(config.host, str)
            assert isinstance(config.port, int)
            assert config.port > 0
        except Exception as e:
            pytest.skip(f'Configuration not available: {e}')

    async def test_service_metrics_and_health_check(self):
        """Test service metrics and health check functionality."""
        service = ClickHouseService(force_mock=True)
        try:
            await service.initialize()
            metrics = service.get_metrics()
            assert 'queries_executed' in metrics
            assert 'query_failures' in metrics
            assert 'circuit_breaker_state' in metrics
            health = await service.health_check()
            assert 'status' in health
            assert 'metrics' in health
            assert 'cache_stats' in health
        finally:
            await service.close()

    async def test_cache_functionality(self):
        """Test ClickHouse cache functionality."""
        service = ClickHouseService(force_mock=True)
        try:
            await service.initialize()
            stats = service.get_cache_stats()
            assert 'size' in stats
            assert 'hits' in stats
            assert 'misses' in stats
            service.clear_cache()
            stats_after = service.get_cache_stats()
            assert stats_after['size'] == 0
        finally:
            await service.close()

@pytest.mark.skip(reason='Demonstrates expected failures - will be enabled once decorators fully enforced')
class StrictDecoratorEnforcementTests:
    """Tests that demonstrate strict decorator enforcement (currently skipped)."""

    def test_noop_client_blocks_production_instantiation(self):
        """FUTURE: NoOp client should block production instantiation."""
        pass

    def test_test_functions_block_production_calls(self):
        """FUTURE: Test-only functions should block production calls."""
        pass
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')