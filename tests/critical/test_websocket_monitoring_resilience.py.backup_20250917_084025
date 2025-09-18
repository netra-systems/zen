"""CRITICAL RESILIENCE TEST: WebSocket Manager Background Monitoring

This test suite validates the CRITICAL resilience fixes for WebSocket Manager
background monitoring system to prevent permanent monitoring disable.

FIXES TESTED:
1. restart_background_monitoring() method prevents permanent disable
2. Monitoring task recovery from failures with exponential backoff
3. Health check endpoint verifies monitoring status
4. Comprehensive logging for monitoring state changes
5. Automatic monitoring restart after critical failures

BUSINESS VALUE: $100K+ ARR - Prevents system health monitoring failures
"""
import asyncio
import os
import sys
import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager

class WebSocketMonitoringResilienceTests:
    """Test suite for WebSocket Manager monitoring resilience fixes."""

    @pytest.fixture
    async def websocket_manager(self):
        """Create WebSocket manager for testing."""
        manager = UnifiedWebSocketManager()
        yield manager
        await manager.shutdown_background_monitoring()

    @pytest.fixture
    def mock_task_function(self):
        """Mock function for background tasks."""

        async def mock_task():
            await asyncio.sleep(0.1)
            return 'task_completed'
        return mock_task

    @pytest.fixture
    def failing_task_function(self):
        """Mock function that always fails."""

        async def failing_task():
            raise Exception('Simulated task failure')
        return failing_task

    async def test_restart_background_monitoring_basic_functionality(self, websocket_manager):
        """Test basic restart_background_monitoring functionality."""
        assert websocket_manager._monitoring_enabled is True
        websocket_manager._monitoring_enabled = False
        websocket_manager._shutdown_requested = True
        restart_result = await websocket_manager.restart_background_monitoring()
        assert restart_result['monitoring_restarted'] is True
        assert websocket_manager._monitoring_enabled is True
        assert websocket_manager._shutdown_requested is False
        assert restart_result['health_check_passed'] is True

    async def test_restart_background_monitoring_force_restart(self, websocket_manager, mock_task_function):
        """Test force restart functionality."""
        task_name = 'test_task'
        await websocket_manager.start_monitored_background_task(task_name, mock_task_function)
        await asyncio.sleep(0.2)
        restart_result = await websocket_manager.restart_background_monitoring(force_restart=True)
        assert restart_result['monitoring_restarted'] is True
        assert 'existing_tasks_cleaned' in restart_result['recovery_actions_taken']
        assert 'state_reset' in restart_result['recovery_actions_taken']

    async def test_monitoring_health_verification(self, websocket_manager):
        """Test monitoring health verification functionality."""
        health_ok = await websocket_manager._verify_monitoring_health()
        assert health_ok is True
        websocket_manager._monitoring_enabled = False
        health_ok = await websocket_manager._verify_monitoring_health()
        assert health_ok is False
        websocket_manager._monitoring_enabled = True
        websocket_manager._shutdown_requested = True
        health_ok = await websocket_manager._verify_monitoring_health()
        assert health_ok is False

    async def test_get_monitoring_health_status_comprehensive(self, websocket_manager, mock_task_function):
        """Test comprehensive health status reporting."""
        task_name = 'health_test_task'
        await websocket_manager.start_monitored_background_task(task_name, mock_task_function)
        health_status = await websocket_manager.get_monitoring_health_status()
        assert 'monitoring_enabled' in health_status
        assert 'shutdown_requested' in health_status
        assert 'task_health' in health_status
        assert 'overall_health' in health_status
        assert 'alerts' in health_status
        task_health = health_status['task_health']
        assert task_health['total_tasks'] >= 1
        assert 'healthy_tasks' in task_health
        overall_health = health_status['overall_health']
        assert 'score' in overall_health
        assert 'status' in overall_health
        assert overall_health['status'] in ['healthy', 'warning', 'degraded', 'critical']

    async def test_health_alerts_generation(self, websocket_manager):
        """Test health alert generation for different scenarios."""
        websocket_manager._monitoring_enabled = False
        health_status = await websocket_manager.get_monitoring_health_status()
        alerts = health_status['alerts']
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        assert len(critical_alerts) > 0
        assert any(('monitoring is disabled' in alert['message'].lower() for alert in critical_alerts))

    async def test_task_recovery_with_exponential_backoff(self, websocket_manager):
        """Test enhanced task recovery with exponential backoff and jitter."""
        failure_count = 0
        max_failures = 3

        async def intermittent_failing_task():
            nonlocal failure_count
            failure_count += 1
            if failure_count < max_failures:
                raise Exception(f'Simulated failure {failure_count}')
            return 'success_after_failures'
        task_name = 'recovery_test_task'
        await websocket_manager.start_monitored_background_task(task_name, intermittent_failing_task)
        await asyncio.sleep(5.0)
        assert failure_count == max_failures

    async def test_automatic_monitoring_restart_on_critical_failure(self, websocket_manager):
        """Test automatic monitoring restart when tasks hit failure threshold."""
        restart_attempts = []
        original_restart = websocket_manager.restart_background_monitoring

        async def mock_restart(force_restart=False):
            restart_attempts.append({'force_restart': force_restart, 'time': time.time()})
            return {'monitoring_restarted': True, 'health_check_passed': True, 'tasks_recovered': 0, 'tasks_failed_recovery': 0}
        websocket_manager.restart_background_monitoring = mock_restart

        async def always_failing_task():
            raise Exception('Always fails')
        task_name = 'critical_failure_task'
        await websocket_manager.start_monitored_background_task(task_name, always_failing_task)
        await asyncio.sleep(8.0)
        assert len(restart_attempts) > 0
        assert restart_attempts[0]['force_restart'] is True

    async def test_task_registry_preservation_across_restarts(self, websocket_manager, mock_task_function):
        """Test that task registry is preserved across monitoring restarts."""
        task_names = ['task1', 'task2', 'task3']
        for task_name in task_names:
            await websocket_manager.start_monitored_background_task(task_name, mock_task_function)
        assert len(websocket_manager._task_registry) >= len(task_names)
        restart_result = await websocket_manager.restart_background_monitoring()
        assert len(websocket_manager._task_registry) >= len(task_names)
        assert restart_result['tasks_recovered'] >= 0

    async def test_monitoring_state_logging_comprehensive(self, websocket_manager, mock_task_function, caplog):
        """Test comprehensive logging for monitoring state changes."""
        import logging
        caplog.set_level(logging.DEBUG)
        task_name = 'logging_test_task'
        await websocket_manager.start_monitored_background_task(task_name, mock_task_function)
        await websocket_manager.restart_background_monitoring(force_restart=True)
        log_messages = [record.message for record in caplog.records]
        assert any(('MONITORING RESTART INITIATED' in msg for msg in log_messages))
        assert any(('MONITORING RESTART COMPLETED' in msg for msg in log_messages))
        assert any(('MONITORING TASK STARTED' in msg for msg in log_messages))

    async def test_health_check_endpoint_responses(self, websocket_manager):
        """Test health check endpoint provides proper status responses."""
        health_status = await websocket_manager.get_monitoring_health_status()
        assert health_status['overall_health']['status'] == 'healthy'
        assert health_status['overall_health']['score'] >= 90
        websocket_manager._health_check_failures = 2
        health_status = await websocket_manager.get_monitoring_health_status()
        assert health_status['overall_health']['score'] <= 75
        websocket_manager._monitoring_enabled = False
        health_status = await websocket_manager.get_monitoring_health_status()
        assert health_status['overall_health']['status'] == 'critical'
        assert health_status['overall_health']['score'] == 0

    async def test_background_monitoring_disable_recovery(self, websocket_manager, mock_task_function):
        """Test recovery from the original permanent disable issue."""
        task_name = 'disable_recovery_test'
        await websocket_manager.start_monitored_background_task(task_name, mock_task_function)
        websocket_manager._monitoring_enabled = False
        websocket_manager._shutdown_requested = True
        assert websocket_manager._monitoring_enabled is False
        restart_result = await websocket_manager.restart_background_monitoring()
        assert restart_result['monitoring_restarted'] is True
        assert websocket_manager._monitoring_enabled is True
        assert websocket_manager._shutdown_requested is False
        assert restart_result['health_check_passed'] is True

    async def test_concurrent_monitoring_operations(self, websocket_manager, mock_task_function):
        """Test concurrent monitoring operations don't cause race conditions."""
        restart_tasks = []
        for i in range(5):
            restart_tasks.append(asyncio.create_task(websocket_manager.restart_background_monitoring()))
        restart_results = await asyncio.gather(*restart_tasks, return_exceptions=True)
        for result in restart_results:
            assert not isinstance(result, Exception), f'Restart failed with: {result}'
        health_status = await websocket_manager.get_monitoring_health_status()
        assert health_status['monitoring_enabled'] is True

    async def test_task_failure_threshold_and_abandonment(self, websocket_manager):
        """Test task abandonment after hitting failure threshold."""
        admin_notifications = []

        async def mock_notify_admin(task_name, error, failure_count):
            admin_notifications.append({'task_name': task_name, 'error': str(error), 'failure_count': failure_count})
        websocket_manager._notify_admin_of_task_failure = mock_notify_admin

        async def always_failing_task():
            raise Exception('Persistent failure')
        task_name = 'abandonment_test_task'
        await websocket_manager.start_monitored_background_task(task_name, always_failing_task)
        await asyncio.sleep(10.0)
        assert len(admin_notifications) >= 1
        assert admin_notifications[0]['task_name'] == task_name
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')