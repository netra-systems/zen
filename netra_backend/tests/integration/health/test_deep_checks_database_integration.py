"""
Integration Test: Deep Checks Database Integration Failure

Purpose: Test deep_checks.py database manager integration with real import paths
Issue #572: Database manager unavailable for health checks

This test MUST FAIL initially to prove the import issue affects integration.
"""
import pytest
import asyncio
import sys
from unittest.mock import patch, AsyncMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class TestDeepChecksDatabaseIntegration(SSotAsyncTestCase):
    """Integration test for deep health checks database manager integration."""

    def setUp(self):
        """Set up integration test."""
        super().setUp()
        modules_to_clear = ['netra_backend.app.services.health.deep_checks', 'shared.database.core_database_manager']
        for module_name in modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]

    async def test_deep_checks_initialization_integration_failure(self):
        """
        CRITICAL: This test MUST FAIL to prove Issue #572 affects integration.
        
        This test verifies that deep_checks.py fails to initialize its database manager
        due to the broken import path in line 44.
        """
        from netra_backend.app.services.health.deep_checks import DeepHealthChecks, get_deep_health_checks
        deep_checks = DeepHealthChecks()
        await deep_checks.initialize()
        assert deep_checks._initialized is False, 'Deep checks should fail to initialize due to broken database manager import. If this passes, the issue may be resolved or the test is incorrect.'
        assert deep_checks.db_manager is None, 'Database manager should be None due to import failure. If this passes, the broken import may have been fixed.'

    async def test_database_health_check_with_broken_integration(self):
        """
        CRITICAL: This test MUST show degraded functionality due to import issue.
        
        Test that database health checks fail gracefully when database manager
        cannot be imported.
        """
        from netra_backend.app.services.health.deep_checks import DeepHealthChecks
        deep_checks = DeepHealthChecks()
        await deep_checks.initialize()
        result = await deep_checks.check_database_depth()
        assert result.component_name == 'database_deep'
        assert result.status == 'unhealthy', 'Database health check should be unhealthy due to missing database manager. If this passes, the import issue may be resolved.'
        assert 'not initialized' in result.message.lower() or 'unavailable' in result.message.lower(), f'Should indicate database manager unavailable, got: {result.message}'
        assert 'availability' in result.details
        assert result.details['availability'] == 'unavailable'

    async def test_deep_checks_with_correct_db_manager_injection(self):
        """
        This test should PASS - shows that deep checks work when db_manager is injected correctly.
        
        This proves that the issue is with the import, not with the deep checks logic itself.
        """
        from netra_backend.app.services.health.deep_checks import DeepHealthChecks
        mock_db_manager = AsyncMock()
        mock_connection = AsyncMock()
        mock_connection.fetchone = AsyncMock()
        mock_connection.execute = AsyncMock()
        mock_connection.fetchone.side_effect = [(1, '2024-01-01 12:00:00'), (3,)]
        mock_db_manager.get_connection.return_value.__aenter__.return_value = mock_connection
        mock_db_manager.get_connection.return_value.__aexit__.return_value = None
        deep_checks = DeepHealthChecks()
        await deep_checks.initialize(db_manager=mock_db_manager)
        assert deep_checks._initialized is True, 'Should initialize successfully with injected db_manager'
        assert deep_checks.db_manager is not None, 'Should have db_manager when injected'
        result = await deep_checks.check_database_depth()
        assert result.component_name == 'database_deep'
        assert result.status in ['healthy', 'degraded'], f'Should be healthy/degraded with proper db_manager, got: {result.status}'
        assert 'unavailable' not in result.message.lower(), f'Should not be unavailable with proper db_manager, got: {result.message}'

    async def test_import_path_resolution_integration(self):
        """
        Integration test to verify the import path issue in the actual module loading.
        
        This test MUST FAIL to prove the integration issue exists.
        """
        with pytest.raises(ImportError, match="No module named 'shared.database.core_database_manager'"):
            from shared.database.core_database_manager import get_database_manager
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            assert DatabaseManager is not None, 'Correct import should work'
        except ImportError as e:
            pytest.fail(f'Correct database manager import should work: {e}')
        try:
            from netra_backend.app.services.health.deep_checks import DeepHealthChecks
            assert DeepHealthChecks is not None, 'Deep checks module should load despite broken import'
        except Exception as e:
            pytest.fail(f'Deep checks module should load despite import issue: {e}')

    async def test_singleton_instance_behavior_with_import_failure(self):
        """
        Test the global singleton instance behavior when import fails.
        
        This should demonstrate that the global instance also has the import issue.
        """
        from netra_backend.app.services.health.deep_checks import get_deep_health_checks, initialize_deep_health_checks
        global_instance = get_deep_health_checks()
        initialized_instance = await initialize_deep_health_checks()
        assert global_instance is initialized_instance, 'Should return same singleton instance'
        assert not initialized_instance._initialized, 'Global instance should fail to initialize due to import issue'
        assert initialized_instance.db_manager is None, 'Global instance should have no db_manager due to import failure'

    async def test_graceful_degradation_integration(self):
        """
        Test that the system gracefully handles the import failure in integration scenarios.
        
        This tests the real-world behavior when health checks are called despite the import issue.
        """
        from netra_backend.app.services.health.deep_checks import get_deep_health_checks
        deep_checks = get_deep_health_checks()
        await deep_checks.initialize()
        database_result = await deep_checks.check_database_depth()
        assert database_result.status == 'unhealthy', 'Should be unhealthy due to unavailable database manager'
        assert 'unavailable' in database_result.message.lower(), 'Should indicate unavailable'
        redis_result = await deep_checks.check_redis_depth()
        assert 'unavailable' in redis_result.message.lower(), 'Redis should also be unavailable without injection'
        websocket_result = await deep_checks.check_websocket_server_depth()
        assert websocket_result.component_name == 'websocket_deep'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')