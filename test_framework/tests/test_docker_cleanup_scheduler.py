"""
Comprehensive test suite for DockerCleanupScheduler

Tests all aspects of the automated Docker cleanup system including:
- Scheduled cleanup operations
- Resource threshold monitoring
- Circuit breaker pattern
- Integration with UnifiedDockerManager
- Cross-platform compatibility

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Quality Assurance
2. Business Goal: Ensure reliable automated cleanup system
3. Value Impact: Prevents regression that could cause Docker crashes
4. Revenue Impact: Protects $2M+ ARR through stable development infrastructure
"""
import pytest
import threading
import time
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import asdict

from shared.isolated_environment import IsolatedEnvironment
from test_framework.base import BaseTestCase
from test_framework.docker_cleanup_scheduler import DockerCleanupScheduler, CleanupType, CleanupResult, SchedulerState, ScheduleConfig, ResourceThresholds, CircuitBreakerConfig, get_cleanup_scheduler, start_cleanup_scheduler, stop_cleanup_scheduler, test_session_context
from test_framework.docker_rate_limiter import DockerRateLimiter, DockerCommandResult

class TestDockerCleanupSchedulerUnit(BaseTestCase):
    """Unit tests for DockerCleanupScheduler core functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        from test_framework.docker_cleanup_scheduler import _global_scheduler
        import test_framework.docker_cleanup_scheduler as scheduler_module
        if scheduler_module._global_scheduler is not None:
            try:
                scheduler_module._global_scheduler.stop()
            except:
                pass
            scheduler_module._global_scheduler = None
        self.mock_rate_limiter = Mock(spec=DockerRateLimiter)
        self.mock_docker_manager = Mock()
        self.mock_rate_limiter.health_check.return_value = True
        self.mock_rate_limiter.execute_docker_command.return_value = DockerCommandResult(returncode=0, stdout='', stderr='', duration=0.1, retry_count=0)
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / 'test_scheduler_state.json'

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.unit
    def test_scheduler_initialization(self):
        """Test scheduler initialization with default configuration."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        scheduler.state_file = self.state_file
        scheduler.state = SchedulerState.STOPPED
        scheduler._consecutive_failures = 0
        scheduler._circuit_open_time = None
        assert scheduler.state == SchedulerState.STOPPED
        assert scheduler.docker_manager == self.mock_docker_manager
        assert scheduler.rate_limiter == self.mock_rate_limiter
        assert isinstance(scheduler.schedule_config, ScheduleConfig)
        assert isinstance(scheduler.resource_thresholds, ResourceThresholds)
        assert isinstance(scheduler.circuit_breaker_config, CircuitBreakerConfig)

    @pytest.mark.unit
    def test_scheduler_initialization_with_custom_config(self):
        """Test scheduler initialization with custom configuration."""
        custom_schedule = ScheduleConfig(business_hours_start=9, business_hours_end=17, cleanup_interval_hours=2)
        custom_thresholds = ResourceThresholds(disk_usage_percent=80.0, container_count=40)
        custom_circuit_breaker = CircuitBreakerConfig(failure_threshold=5, recovery_timeout_minutes=20)
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter, schedule_config=custom_schedule, resource_thresholds=custom_thresholds, circuit_breaker_config=custom_circuit_breaker)
        assert scheduler.schedule_config.business_hours_start == 9
        assert scheduler.schedule_config.business_hours_end == 17
        assert scheduler.schedule_config.cleanup_interval_hours == 2
        assert scheduler.resource_thresholds.disk_usage_percent == 80.0
        assert scheduler.resource_thresholds.container_count == 40
        assert scheduler.circuit_breaker_config.failure_threshold == 5
        assert scheduler.circuit_breaker_config.recovery_timeout_minutes == 20

    @pytest.mark.unit
    def test_scheduler_start_stop(self):
        """Test scheduler start and stop operations."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        assert scheduler.start()
        assert scheduler.state == SchedulerState.RUNNING
        assert scheduler._scheduler_thread is not None
        assert scheduler._scheduler_thread.is_alive()
        assert scheduler.stop()
        assert scheduler.state == SchedulerState.STOPPED
        if scheduler._scheduler_thread is not None:
            assert not scheduler._scheduler_thread.is_alive()
        assert scheduler.start()
        assert scheduler.start()
        assert scheduler.stop()
        assert scheduler.stop()

    @pytest.mark.unit
    def test_scheduler_start_failure_docker_unavailable(self):
        """Test scheduler start failure when Docker is unavailable."""
        self.mock_rate_limiter.health_check.return_value = False
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        assert not scheduler.start()
        assert scheduler.state == SchedulerState.STOPPED
        assert scheduler._scheduler_thread is None

    @pytest.mark.unit
    def test_scheduler_pause_resume(self):
        """Test scheduler pause and resume operations."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        scheduler.start()
        assert scheduler.state == SchedulerState.RUNNING
        scheduler.pause()
        assert scheduler.state == SchedulerState.PAUSED
        scheduler.resume()
        assert scheduler.state == SchedulerState.RUNNING
        scheduler.stop()

    @pytest.mark.unit
    def test_test_session_registration(self):
        """Test test session registration and unregistration."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        scheduler.register_test_session('test1')
        scheduler.register_test_session('test2')
        assert 'test1' in scheduler._active_test_sessions
        assert 'test2' in scheduler._active_test_sessions
        assert len(scheduler._active_test_sessions) == 2
        scheduler.unregister_test_session('test1', trigger_cleanup=False)
        assert 'test1' not in scheduler._active_test_sessions
        assert 'test2' in scheduler._active_test_sessions
        assert len(scheduler._active_test_sessions) == 1

    @pytest.mark.unit
    def test_resource_threshold_checking(self, mock_memory, mock_disk):
        """Test resource threshold checking functionality."""
        mock_disk_usage = Mock()
        mock_disk_usage.total = 1000 * 1024 * 1024 * 1024
        mock_disk_usage.used = 900 * 1024 * 1024 * 1024
        mock_disk.return_value = mock_disk_usage
        mock_memory_usage = Mock()
        mock_memory_usage.percent = 95.0
        mock_memory.return_value = mock_memory_usage

        def mock_docker_command(cmd):
            if 'container' in cmd and 'ls' in cmd:
                return DockerCommandResult(0, 'container1\ncontainer2\ncontainer3', '', 0.1, 0)
            elif 'image' in cmd and 'ls' in cmd:
                return DockerCommandResult(0, 'image1\nimage2', '', 0.1, 0)
            elif 'volume' in cmd and 'ls' in cmd:
                return DockerCommandResult(0, 'volume1', '', 0.1, 0)
            return DockerCommandResult(0, '', '', 0.1, 0)
        self.mock_rate_limiter.execute_docker_command.side_effect = mock_docker_command
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter, resource_thresholds=ResourceThresholds(disk_usage_percent=85.0, memory_usage_percent=90.0, container_count=2, image_count=1, volume_count=1))
        thresholds = scheduler.check_resource_thresholds()
        assert thresholds['disk_usage_percent'] == 90.0
        assert thresholds['disk_threshold_exceeded'] == True
        assert thresholds['memory_usage_percent'] == 95.0
        assert thresholds['memory_threshold_exceeded'] == True
        assert thresholds['container_count'] == 3
        assert thresholds['container_threshold_exceeded'] == True
        assert thresholds['image_count'] == 2
        assert thresholds['image_threshold_exceeded'] == True
        assert thresholds['volume_count'] == 1
        assert thresholds['volume_threshold_exceeded'] == False
        assert thresholds['any_threshold_exceeded'] == True

    @pytest.mark.unit
    def test_cleanup_operation_containers(self):
        """Test container cleanup operation."""

        def mock_docker_command(cmd):
            if 'container' in cmd and 'ls' in cmd and ('exited' in cmd) and ('--format' in cmd):
                return DockerCommandResult(0, 'container1\ncontainer2', '', 0.1, 0)
            elif 'container' in cmd and 'rm' in cmd:
                return DockerCommandResult(0, '', '', 0.1, 0)
            return DockerCommandResult(0, '', '', 0.1, 0)
        self.mock_rate_limiter.execute_docker_command.side_effect = mock_docker_command
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        result = scheduler._perform_single_cleanup(CleanupType.CONTAINERS)
        assert result.success == True
        assert result.items_removed >= 0
        assert result.space_freed_mb >= 0.0
        assert result.cleanup_type == CleanupType.CONTAINERS

    @pytest.mark.unit
    def test_cleanup_operation_failure(self):
        """Test cleanup operation failure handling."""
        self.mock_rate_limiter.execute_docker_command.return_value = DockerCommandResult(1, '', 'Docker command failed', 0.1, 0)
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        result = scheduler._perform_single_cleanup(CleanupType.CONTAINERS)
        assert result.success == False
        assert result.items_removed == 0
        assert result.space_freed_mb == 0.0
        assert 'Failed to list containers' in result.error_message

    @pytest.mark.unit
    def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern functionality."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter, circuit_breaker_config=CircuitBreakerConfig(failure_threshold=2, recovery_timeout_minutes=1))
        scheduler.state = SchedulerState.RUNNING
        with patch.object(scheduler, '_perform_single_cleanup') as mock_cleanup:
            mock_cleanup.return_value = CleanupResult(cleanup_type=CleanupType.CONTAINERS, success=False, items_removed=0, space_freed_mb=0.0, duration_seconds=0.1, error_message='Test failure')
            scheduler._perform_cleanup([CleanupType.CONTAINERS])
            assert scheduler._consecutive_failures == 1
            assert scheduler.state == SchedulerState.RUNNING
            scheduler._perform_cleanup([CleanupType.CONTAINERS])
            assert scheduler._consecutive_failures == 2
            assert scheduler.state == SchedulerState.CIRCUIT_OPEN
            results = scheduler._perform_cleanup([CleanupType.CONTAINERS])
            assert len(results) == 0

    @pytest.mark.unit
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery functionality."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter, circuit_breaker_config=CircuitBreakerConfig(failure_threshold=1, recovery_timeout_minutes=0))
        scheduler._consecutive_failures = 1
        scheduler.state = SchedulerState.CIRCUIT_OPEN
        scheduler._circuit_open_time = datetime.now() - timedelta(minutes=1)
        scheduler._check_circuit_breaker_recovery()
        assert scheduler.state == SchedulerState.RUNNING
        scheduler._reset_circuit_breaker()
        assert scheduler._consecutive_failures == 0
        assert scheduler.state == SchedulerState.RUNNING

    @pytest.mark.unit
    def test_callback_registration(self):
        """Test pre and post cleanup callback registration."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        pre_callback = Mock(return_value=True)
        post_callback = Mock()
        scheduler.add_pre_cleanup_callback(pre_callback)
        scheduler.add_post_cleanup_callback(post_callback)
        with patch.object(scheduler, '_perform_single_cleanup') as mock_cleanup:
            mock_cleanup.return_value = CleanupResult(cleanup_type=CleanupType.CONTAINERS, success=True, items_removed=1, space_freed_mb=10.0, duration_seconds=0.1)
            results = scheduler._perform_cleanup([CleanupType.CONTAINERS])
            pre_callback.assert_called_once()
            post_callback.assert_called_once()
            assert len(results) == 1

    @pytest.mark.unit
    def test_pre_callback_cancellation(self):
        """Test cleanup cancellation by pre-cleanup callback."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        pre_callback = Mock(return_value=False)
        scheduler.add_pre_cleanup_callback(pre_callback)
        results = scheduler._perform_cleanup([CleanupType.CONTAINERS])
        pre_callback.assert_called_once()
        assert len(results) == 0

    @pytest.mark.unit
    def test_state_persistence(self):
        """Test scheduler state persistence to disk."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        scheduler.state_file = self.state_file
        scheduler.state = SchedulerState.RUNNING
        scheduler._total_space_freed_mb = 500.0
        scheduler._total_items_removed = 25
        scheduler._consecutive_failures = 2
        scheduler._last_cleanup_times[CleanupType.CONTAINERS] = datetime.now()
        scheduler._save_state()
        new_scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        new_scheduler.state_file = self.state_file
        new_scheduler._load_state()
        assert new_scheduler.state == SchedulerState.STOPPED
        assert new_scheduler._total_space_freed_mb == 500.0
        assert new_scheduler._total_items_removed == 25
        assert new_scheduler._consecutive_failures == 2
        assert CleanupType.CONTAINERS in new_scheduler._last_cleanup_times

    @pytest.mark.unit
    def test_manual_cleanup_trigger(self):
        """Test manual cleanup triggering."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        scheduler.register_test_session('test1')
        with patch.object(scheduler, '_perform_single_cleanup') as mock_cleanup:
            mock_cleanup.return_value = CleanupResult(cleanup_type=CleanupType.CONTAINERS, success=True, items_removed=1, space_freed_mb=10.0, duration_seconds=0.1)
            results = scheduler.trigger_manual_cleanup([CleanupType.CONTAINERS], force=True)
            assert len(results) == 1
            assert results[0].success == True
            results = scheduler.trigger_manual_cleanup([CleanupType.CONTAINERS], force=False)
            assert len(results) == 0

    @pytest.mark.unit
    def test_get_statistics(self):
        """Test scheduler statistics reporting."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        scheduler._cleanup_history = [CleanupResult(CleanupType.CONTAINERS, True, 2, 20.0, 0.1), CleanupResult(CleanupType.IMAGES, False, 0, 0.0, 0.1, 'Test error')]
        scheduler._total_space_freed_mb = 100.0
        scheduler._total_items_removed = 50
        scheduler.register_test_session('test1')
        stats = scheduler.get_statistics()
        assert stats['scheduler_state'] == SchedulerState.STOPPED.value
        assert stats['active_test_sessions'] == 1
        assert stats['total_operations'] == 2
        assert stats['successful_operations'] == 1
        assert stats['success_rate_percent'] == 50.0
        assert stats['total_space_freed_mb'] == 100.0
        assert stats['total_items_removed'] == 50
        assert 'resource_thresholds' in stats

class TestDockerCleanupSchedulerIntegration(BaseTestCase):
    """Integration tests for DockerCleanupScheduler with real components."""

    def setup_method(self):
        """Set up integration test fixtures."""
        super().setup_method()
        self.real_rate_limiter = Mock(spec=DockerRateLimiter)
        self.real_rate_limiter.health_check.return_value = True
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / 'integration_scheduler_state.json'

    def teardown_method(self):
        """Clean up integration test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.integration
    def test_scheduler_integration_with_docker_manager(self):
        """Test scheduler integration with UnifiedDockerManager."""
        from test_framework.unified_docker_manager import UnifiedDockerManager
        docker_manager = UnifiedDockerManager()
        docker_manager._enable_cleanup_scheduler = True
        result = docker_manager.enable_cleanup_scheduler()
        if not result:
            pytest.skip('Docker not available for integration test')
        status = docker_manager.get_cleanup_scheduler_status()
        assert status is not None
        assert 'scheduler_state' in status
        session_id = docker_manager.register_with_cleanup_scheduler('integration_test')
        assert session_id == 'integration_test'
        docker_manager.unregister_from_cleanup_scheduler('integration_test')
        assert docker_manager.disable_cleanup_scheduler()

    @pytest.mark.integration
    def test_global_scheduler_functions(self):
        """Test global scheduler convenience functions."""
        scheduler = get_cleanup_scheduler()
        assert isinstance(scheduler, DockerCleanupScheduler)
        if scheduler.rate_limiter.health_check():
            assert start_cleanup_scheduler()
            stats = scheduler.get_statistics()
            assert stats['scheduler_state'] == SchedulerState.RUNNING.value
            assert stop_cleanup_scheduler()
            assert scheduler.state == SchedulerState.STOPPED
        else:
            pytest.skip('Docker not available for global scheduler test')

    @pytest.mark.integration
    def test_test_session_context_manager(self):
        """Test test session context manager."""
        scheduler = get_cleanup_scheduler()
        with test_session_context('context_test') as ctx_scheduler:
            assert ctx_scheduler == scheduler
            assert 'context_test' in scheduler._active_test_sessions
        assert 'context_test' not in scheduler._active_test_sessions

    @pytest.mark.integration
    def test_scheduler_thread_behavior(self, mock_sleep):
        """Test scheduler background thread behavior."""
        mock_sleep.return_value = None
        scheduler = DockerCleanupScheduler(rate_limiter=self.real_rate_limiter, schedule_config=ScheduleConfig(cleanup_interval_hours=0.001, enable_threshold_cleanup=False))
        scheduler.state_file = self.state_file
        if not scheduler.rate_limiter.health_check():
            pytest.skip('Docker not available for scheduler thread test')
        try:
            assert scheduler.start()
            time.sleep(0.1)
            assert scheduler.state == SchedulerState.RUNNING
            assert scheduler._scheduler_thread.is_alive()
            assert scheduler.stop()
            assert scheduler.state == SchedulerState.STOPPED
        finally:
            if scheduler.state != SchedulerState.STOPPED:
                scheduler.stop()

class TestDockerCleanupSchedulerErrorConditions(BaseTestCase):
    """Test error conditions and edge cases for DockerCleanupScheduler."""

    def setup_method(self):
        """Set up error condition test fixtures."""
        super().setup_method()
        self.mock_rate_limiter = Mock(spec=DockerRateLimiter)
        self.mock_docker_manager = Mock()

    @pytest.mark.unit
    def test_docker_command_timeout_handling(self):
        """Test handling of Docker command timeouts."""
        import subprocess
        self.mock_rate_limiter.execute_docker_command.side_effect = subprocess.TimeoutExpired(['docker', 'container', 'ls'], 30)
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        result = scheduler._perform_single_cleanup(CleanupType.CONTAINERS)
        assert result.success == False
        assert 'timeout' in result.error_message.lower()

    @pytest.mark.unit
    def test_invalid_json_in_state_file(self):
        """Test handling of corrupted state file."""
        temp_dir = tempfile.mkdtemp()
        state_file = Path(temp_dir) / 'corrupted_state.json'
        try:
            with open(state_file, 'w') as f:
                f.write('{ invalid json content')
            scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
            scheduler.state_file = state_file
            scheduler._load_state()
            assert scheduler.state == SchedulerState.STOPPED
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.unit
    def test_cleanup_with_no_items_to_remove(self):
        """Test cleanup when no items need to be removed."""
        self.mock_rate_limiter.execute_docker_command.return_value = DockerCommandResult(0, '', '', 0.1, 0)
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        result = scheduler._perform_single_cleanup(CleanupType.CONTAINERS)
        assert result.success == True
        assert result.items_removed == 0
        assert result.space_freed_mb == 0.0

    @pytest.mark.unit
    def test_callback_exception_handling(self):
        """Test handling of exceptions in callbacks."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)

        def failing_callback():
            raise RuntimeError('Callback failed')
        scheduler.add_pre_cleanup_callback(failing_callback)
        with patch.object(scheduler, '_perform_single_cleanup') as mock_cleanup:
            mock_cleanup.return_value = CleanupResult(cleanup_type=CleanupType.CONTAINERS, success=True, items_removed=1, space_freed_mb=10.0, duration_seconds=0.1)
            results = scheduler._perform_cleanup([CleanupType.CONTAINERS])
            assert len(results) == 1
            assert results[0].success == True

    @pytest.mark.unit
    def test_scheduler_thread_exception_handling(self):
        """Test scheduler thread exception handling."""
        scheduler = DockerCleanupScheduler(docker_manager=self.mock_docker_manager, rate_limiter=self.mock_rate_limiter)
        original_check = scheduler._check_and_cleanup

        def failing_check():
            raise RuntimeError('Check failed')
        scheduler._check_and_cleanup = failing_check
        if scheduler.rate_limiter.health_check():
            scheduler.start()
            time.sleep(0.1)
            assert scheduler.state == SchedulerState.RUNNING
            scheduler._check_and_cleanup = original_check
            scheduler.stop()
        else:
            pytest.skip('Docker not available for thread exception test')

@pytest.fixture
def cleanup_scheduler():
    """Provide a configured cleanup scheduler for testing."""
    mock_rate_limiter = Mock(spec=DockerRateLimiter)
    mock_rate_limiter.health_check.return_value = True
    mock_docker_manager = Mock()
    scheduler = DockerCleanupScheduler(docker_manager=mock_docker_manager, rate_limiter=mock_rate_limiter)
    yield scheduler
    if scheduler.state != SchedulerState.STOPPED:
        scheduler.stop()

@pytest.fixture
def real_scheduler():
    """Provide a real scheduler for integration testing."""
    from test_framework.docker_rate_limiter import get_docker_rate_limiter
    rate_limiter = get_docker_rate_limiter()
    if not rate_limiter.health_check():
        pytest.skip('Docker not available for real scheduler tests')
    scheduler = DockerCleanupScheduler(rate_limiter=rate_limiter)
    yield scheduler
    if scheduler.state != SchedulerState.STOPPED:
        scheduler.stop()

@pytest.mark.parametrize('cleanup_type', list(CleanupType))
@pytest.mark.unit
def test_all_cleanup_types(cleanup_type, cleanup_scheduler):
    """Test all cleanup types can be executed without errors."""

    def mock_docker_response(cmd):
        if cleanup_type == CleanupType.CONTAINERS and 'container' in cmd:
            if 'ls' in cmd:
                return DockerCommandResult(0, 'container1', '', 0.1, 0)
            elif 'rm' in cmd:
                return DockerCommandResult(0, '', '', 0.1, 0)
        elif cleanup_type == CleanupType.IMAGES and 'image' in cmd:
            return DockerCommandResult(0, 'Total reclaimed space: 100MB', '', 0.1, 0)
        elif cleanup_type == CleanupType.VOLUMES and 'volume' in cmd:
            return DockerCommandResult(0, 'Total reclaimed space: 50MB', '', 0.1, 0)
        elif cleanup_type == CleanupType.NETWORKS and 'network' in cmd:
            return DockerCommandResult(0, 'Deleted Networks:\nnetwork1', '', 0.1, 0)
        elif cleanup_type == CleanupType.BUILD_CACHE and 'builder' in cmd:
            return DockerCommandResult(0, 'Total: 200MB', '', 0.1, 0)
        elif cleanup_type == CleanupType.SYSTEM and 'system' in cmd:
            return DockerCommandResult(0, 'Total reclaimed space: 300MB', '', 0.1, 0)
        return DockerCommandResult(0, '', '', 0.1, 0)
    cleanup_scheduler.rate_limiter.execute_docker_command.side_effect = mock_docker_response
    result = cleanup_scheduler._perform_single_cleanup(cleanup_type)
    assert result.cleanup_type == cleanup_type
    assert result.success == True
    assert result.duration_seconds >= 0
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')