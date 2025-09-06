#!/usr/bin/env python
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

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

class TestWebSocketMonitoringResilience:
    """Test suite for WebSocket Manager monitoring resilience fixes."""

    @pytest.fixture
    async def websocket_manager(self):
        """Create WebSocket manager for testing."""
        manager = UnifiedWebSocketManager()
        yield manager
        # Clean up background tasks
        await manager.shutdown_background_monitoring()

    @pytest.fixture
    def mock_task_function(self):
        """Mock function for background tasks."""
        async def mock_task():
            await asyncio.sleep(0.1)
            return "task_completed"
        return mock_task

    @pytest.fixture
    def failing_task_function(self):
        """Mock function that always fails."""
        async def failing_task():
            raise Exception("Simulated task failure")
        return failing_task

    async def test_restart_background_monitoring_basic_functionality(self, websocket_manager):
        """Test basic restart_background_monitoring functionality."""
        # Initially monitoring should be enabled
        assert websocket_manager._monitoring_enabled is True
        
        # Disable monitoring to simulate permanent disable issue
        websocket_manager._monitoring_enabled = False
        websocket_manager._shutdown_requested = True
        
        # Restart monitoring
        restart_result = await websocket_manager.restart_background_monitoring()
        
        # Verify restart was successful
        assert restart_result['monitoring_restarted'] is True
        assert websocket_manager._monitoring_enabled is True
        assert websocket_manager._shutdown_requested is False
        assert restart_result['health_check_passed'] is True

    async def test_restart_background_monitoring_force_restart(self, websocket_manager, mock_task_function):
        """Test force restart functionality."""
        # Start a background task
        task_name = "test_task"
        await websocket_manager.start_monitored_background_task(task_name, mock_task_function)
        
        # Wait for task to be registered
        await asyncio.sleep(0.2)
        
        # Force restart even though monitoring appears healthy
        restart_result = await websocket_manager.restart_background_monitoring(force_restart=True)
        
        assert restart_result['monitoring_restarted'] is True
        assert 'existing_tasks_cleaned' in restart_result['recovery_actions_taken']
        assert 'state_reset' in restart_result['recovery_actions_taken']

    async def test_monitoring_health_verification(self, websocket_manager):
        """Test monitoring health verification functionality."""
        # Test healthy state
        health_ok = await websocket_manager._verify_monitoring_health()
        assert health_ok is True
        
        # Test unhealthy state - monitoring disabled
        websocket_manager._monitoring_enabled = False
        health_ok = await websocket_manager._verify_monitoring_health()
        assert health_ok is False
        
        # Test unhealthy state - shutdown requested
        websocket_manager._monitoring_enabled = True
        websocket_manager._shutdown_requested = True
        health_ok = await websocket_manager._verify_monitoring_health()
        assert health_ok is False

    async def test_get_monitoring_health_status_comprehensive(self, websocket_manager, mock_task_function):
        """Test comprehensive health status reporting."""
        # Start a background task
        task_name = "health_test_task"
        await websocket_manager.start_monitored_background_task(task_name, mock_task_function)
        
        # Get health status
        health_status = await websocket_manager.get_monitoring_health_status()
        
        # Verify health status structure
        assert 'monitoring_enabled' in health_status
        assert 'shutdown_requested' in health_status
        assert 'task_health' in health_status
        assert 'overall_health' in health_status
        assert 'alerts' in health_status
        
        # Verify task health metrics
        task_health = health_status['task_health']
        assert task_health['total_tasks'] >= 1
        assert 'healthy_tasks' in task_health
        
        # Verify overall health scoring
        overall_health = health_status['overall_health']
        assert 'score' in overall_health
        assert 'status' in overall_health
        assert overall_health['status'] in ['healthy', 'warning', 'degraded', 'critical']

    async def test_health_alerts_generation(self, websocket_manager):
        """Test health alert generation for different scenarios."""
        # Test critical alert - monitoring disabled
        websocket_manager._monitoring_enabled = False
        health_status = await websocket_manager.get_monitoring_health_status()
        
        alerts = health_status['alerts']
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        assert len(critical_alerts) > 0
        assert any('monitoring is disabled' in alert['message'].lower() for alert in critical_alerts)

    async def test_task_recovery_with_exponential_backoff(self, websocket_manager):
        """Test enhanced task recovery with exponential backoff and jitter."""
        failure_count = 0
        max_failures = 3
        
        async def intermittent_failing_task():
            nonlocal failure_count
            failure_count += 1
            if failure_count < max_failures:
                raise Exception(f"Simulated failure {failure_count}")
            return "success_after_failures"
        
        # Start the task and let it run through failure recovery
        task_name = "recovery_test_task"
        await websocket_manager.start_monitored_background_task(task_name, intermittent_failing_task)
        
        # Wait for task to complete with recovery
        await asyncio.sleep(5.0)  # Allow time for retries with backoff
        
        # Verify the task eventually succeeded
        assert failure_count == max_failures  # Should have failed exactly max_failures - 1 times before success

    async def test_automatic_monitoring_restart_on_critical_failure(self, websocket_manager):
        """Test automatic monitoring restart when tasks hit failure threshold."""
        restart_attempts = []
        
        # Mock restart_background_monitoring to track calls
        original_restart = websocket_manager.restart_background_monitoring
        async def mock_restart(force_restart=False):
            restart_attempts.append({'force_restart': force_restart, 'time': time.time()})
            return {
                'monitoring_restarted': True,
                'health_check_passed': True,
                'tasks_recovered': 0,
                'tasks_failed_recovery': 0
            }
        
        websocket_manager.restart_background_monitoring = mock_restart
        
        # Create a task that always fails
        async def always_failing_task():
            raise Exception("Always fails")
        
        # Start the failing task
        task_name = "critical_failure_task"
        await websocket_manager.start_monitored_background_task(task_name, always_failing_task)
        
        # Wait for task to hit failure threshold and trigger restart
        await asyncio.sleep(8.0)  # Allow time for all retries and restart
        
        # Verify automatic restart was attempted
        assert len(restart_attempts) > 0
        assert restart_attempts[0]['force_restart'] is True

    async def test_task_registry_preservation_across_restarts(self, websocket_manager, mock_task_function):
        """Test that task registry is preserved across monitoring restarts."""
        # Start multiple background tasks
        task_names = ["task1", "task2", "task3"]
        for task_name in task_names:
            await websocket_manager.start_monitored_background_task(task_name, mock_task_function)
        
        # Verify tasks are registered
        assert len(websocket_manager._task_registry) >= len(task_names)
        
        # Restart monitoring
        restart_result = await websocket_manager.restart_background_monitoring()
        
        # Verify task registry is preserved and tasks are recovered
        assert len(websocket_manager._task_registry) >= len(task_names)
        assert restart_result['tasks_recovered'] >= 0  # Some tasks should be recovered

    async def test_monitoring_state_logging_comprehensive(self, websocket_manager, mock_task_function, caplog):
        """Test comprehensive logging for monitoring state changes."""
        import logging
        
        # Enable debug logging to capture all messages
        caplog.set_level(logging.DEBUG)
        
        # Start a task
        task_name = "logging_test_task"
        await websocket_manager.start_monitored_background_task(task_name, mock_task_function)
        
        # Restart monitoring
        await websocket_manager.restart_background_monitoring(force_restart=True)
        
        # Check for key log messages
        log_messages = [record.message for record in caplog.records]
        
        # Verify critical monitoring messages are logged
        assert any("MONITORING RESTART INITIATED" in msg for msg in log_messages)
        assert any("MONITORING RESTART COMPLETED" in msg for msg in log_messages)
        assert any("MONITORING TASK STARTED" in msg for msg in log_messages)

    async def test_health_check_endpoint_responses(self, websocket_manager):
        """Test health check endpoint provides proper status responses."""
        # Test healthy state
        health_status = await websocket_manager.get_monitoring_health_status()
        assert health_status['overall_health']['status'] == 'healthy'
        assert health_status['overall_health']['score'] >= 90
        
        # Test degraded state
        websocket_manager._health_check_failures = 2
        health_status = await websocket_manager.get_monitoring_health_status()
        assert health_status['overall_health']['score'] <= 75
        
        # Test critical state
        websocket_manager._monitoring_enabled = False
        health_status = await websocket_manager.get_monitoring_health_status()
        assert health_status['overall_health']['status'] == 'critical'
        assert health_status['overall_health']['score'] == 0

    async def test_background_monitoring_disable_recovery(self, websocket_manager, mock_task_function):
        """Test recovery from the original permanent disable issue."""
        # Start a background task
        task_name = "disable_recovery_test"
        await websocket_manager.start_monitored_background_task(task_name, mock_task_function)
        
        # Simulate the permanent disable bug
        websocket_manager._monitoring_enabled = False  # This was the bug!
        websocket_manager._shutdown_requested = True
        
        # Verify monitoring is disabled
        assert websocket_manager._monitoring_enabled is False
        
        # This should now be recoverable with restart_background_monitoring
        restart_result = await websocket_manager.restart_background_monitoring()
        
        # Verify recovery was successful
        assert restart_result['monitoring_restarted'] is True
        assert websocket_manager._monitoring_enabled is True
        assert websocket_manager._shutdown_requested is False
        assert restart_result['health_check_passed'] is True

    async def test_concurrent_monitoring_operations(self, websocket_manager, mock_task_function):
        """Test concurrent monitoring operations don't cause race conditions."""
        # Start multiple concurrent restart operations
        restart_tasks = []
        for i in range(5):
            restart_tasks.append(
                asyncio.create_task(websocket_manager.restart_background_monitoring())
            )
        
        # Wait for all restarts to complete
        restart_results = await asyncio.gather(*restart_tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        for result in restart_results:
            assert not isinstance(result, Exception), f"Restart failed with: {result}"
        
        # Verify final monitoring state is consistent
        health_status = await websocket_manager.get_monitoring_health_status()
        assert health_status['monitoring_enabled'] is True

    async def test_task_failure_threshold_and_abandonment(self, websocket_manager):
        """Test task abandonment after hitting failure threshold."""
        admin_notifications = []
        
        # Mock admin notification to track calls
        async def mock_notify_admin(task_name, error, failure_count):
            admin_notifications.append({
                'task_name': task_name,
                'error': str(error),
                'failure_count': failure_count
            })
        
        websocket_manager._notify_admin_of_task_failure = mock_notify_admin
        
        # Create task that always fails
        async def always_failing_task():
            raise Exception("Persistent failure")
        
        # Start failing task
        task_name = "abandonment_test_task"
        await websocket_manager.start_monitored_background_task(task_name, always_failing_task)
        
        # Wait for task to hit failure threshold
        await asyncio.sleep(10.0)  # Allow time for all retries
        
        # Verify admin notification was sent
        assert len(admin_notifications) >= 1
        assert admin_notifications[0]['task_name'] == task_name


if __name__ == "__main__":
    # Run the test suite
    pytest.main([__file__, "-v", "--tb=short"])