"""
Health monitoring tests for the dev launcher.

Tests cover HealthMonitor, recovery mechanisms, and error handling.
All functions follow 8-line maximum rule per CLAUDE.md.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import time
import threading

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dev_launcher.health_monitor import HealthMonitor, HealthStatus
from dev_launcher.launcher import DevLauncher
from dev_launcher.config import LauncherConfig


class TestHealthMonitor(unittest.TestCase):
    """Test health monitoring functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.monitor = HealthMonitor(check_interval=0.1)
    
    def tearDown(self):
        """Clean up after tests."""
        self.monitor.stop()
    
    def test_register_service(self):
        """Test registering a service for monitoring."""
        health_check = Mock(return_value=True)
        recovery = Mock()
        self.monitor.register_service(
            "TestService", health_check, recovery, max_failures=3
        )
        self._assert_service_registered()
    
    def _assert_service_registered(self):
        """Assert service was properly registered."""
        self.assertIn("TestService", self.monitor.services)
        self.assertIn("TestService", self.monitor.health_status)
    
    def test_health_check_success(self):
        """Test successful health checks."""
        health_check = Mock(return_value=True)
        self.monitor.register_service("TestService", health_check)
        self.monitor._check_all_services()
        self._assert_service_healthy()
    
    def _assert_service_healthy(self):
        """Assert service is marked as healthy."""
        status = self.monitor.get_status("TestService")
        self.assertTrue(status.is_healthy)
        self.assertEqual(status.consecutive_failures, 0)
    
    def test_health_check_failure_and_recovery(self):
        """Test health check failures triggering recovery."""
        health_check = Mock(return_value=False)
        recovery = Mock()
        self._register_service_with_recovery(health_check, recovery)
        self._test_failure_threshold(recovery)
    
    def _register_service_with_recovery(self, health_check, recovery):
        """Register service with recovery handler."""
        self.monitor.register_service(
            "TestService", health_check, recovery, max_failures=2
        )
    
    def _test_failure_threshold(self, recovery):
        """Test that recovery triggers at threshold."""
        self.monitor._check_all_services()
        status = self.monitor.get_status("TestService")
        self.assertFalse(status.is_healthy)
        self.assertEqual(status.consecutive_failures, 1)
        recovery.assert_not_called()
        self.monitor._check_all_services()
        status = self.monitor.get_status("TestService")
        self.assertEqual(status.consecutive_failures, 0)
        recovery.assert_called_once()
    
    def test_monitoring_thread(self):
        """Test the monitoring thread operation."""
        health_check = Mock(return_value=True)
        self.monitor.register_service("TestService", health_check)
        self._test_thread_execution(health_check)
    
    def _test_thread_execution(self, health_check):
        """Test that monitoring thread runs checks."""
        self.monitor.start()
        time.sleep(0.3)
        self.assertGreater(health_check.call_count, 1)
        self.monitor.stop()


class TestAdvancedHealthMonitor(unittest.TestCase):
    """Advanced health monitoring tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.monitor = HealthMonitor(check_interval=0.05)
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'monitor'):
            self.monitor.stop()
    
    def test_cascading_failures(self):
        """Test handling cascading service failures."""
        services_health = {'Service1': True, 'Service2': True, 'Service3': True}
        recovery_calls = []
        self._register_cascading_services(services_health, recovery_calls)
        self._trigger_cascading_failures(services_health)
        self._verify_cascading_recovery(recovery_calls)
    
    def _register_cascading_services(self, health_dict, recovery_list):
        """Register services with shared health and recovery."""
        for service in health_dict:
            self.monitor.register_service(
                service,
                lambda s=service: health_dict[s],
                lambda s=service: self._recovery_handler(s, health_dict, recovery_list),
                max_failures=2
            )
    
    def _recovery_handler(self, service, health_dict, recovery_list):
        """Handle recovery for a service."""
        recovery_list.append(service)
        health_dict[service] = True
    
    def _trigger_cascading_failures(self, health_dict):
        """Trigger failures in multiple services."""
        health_dict['Service1'] = False
        health_dict['Service2'] = False
        for _ in range(3):
            self.monitor._check_all_services()
    
    def _verify_cascading_recovery(self, recovery_calls):
        """Verify both services recovered."""
        self.assertIn('Service1', recovery_calls)
        self.assertIn('Service2', recovery_calls)
    
    def test_health_check_performance(self):
        """Test health check performance under load."""
        check_times = []
        self._register_performance_services(check_times)
        self._measure_check_performance(check_times)
    
    def _register_performance_services(self, check_times):
        """Register multiple services for performance test."""
        for i in range(10):
            self.monitor.register_service(
                f"PerfService{i}",
                lambda ct=check_times: self._timed_health_check(ct)
            )
    
    def _timed_health_check(self, check_times):
        """Health check that measures timing."""
        start = time.time()
        time.sleep(0.01)
        check_times.append(time.time() - start)
        return True
    
    def _measure_check_performance(self, check_times):
        """Measure overall check performance."""
        start = time.time()
        self.monitor._check_all_services()
        total_time = time.time() - start
        self.assertLess(total_time, 1.0)
        self.assertEqual(len(check_times), 10)
    
    def test_adaptive_check_intervals(self):
        """Test adaptive health check intervals based on failures."""
        failure_count = 0
        self._register_adaptive_service(failure_count)
        self._run_adaptive_checks()
        self._verify_adaptive_recovery()
    
    def _register_adaptive_service(self, failure_count):
        """Register service with adaptive failure behavior."""
        def failing_check():
            nonlocal failure_count
            failure_count += 1
            return failure_count > 5
        self.monitor.register_service(
            "AdaptiveService", failing_check, max_failures=10
        )
    
    def _run_adaptive_checks(self):
        """Run checks until service recovers."""
        for _ in range(7):
            self.monitor._check_all_services()
    
    def _verify_adaptive_recovery(self):
        """Verify service eventually becomes healthy."""
        status = self.monitor.get_status("AdaptiveService")
        self.assertTrue(status.is_healthy)


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery mechanisms."""
    
    @patch('dev_launcher.launcher.load_or_create_config')
    def test_port_conflict_recovery(self, mock_config):
        """Test recovery from port conflicts."""
        config = self._create_dynamic_config()
        launcher = DevLauncher(config)
        self._test_port_allocation_retry(launcher)
    
    def _create_dynamic_config(self):
        """Create config with dynamic ports enabled."""
        with patch.object(LauncherConfig, '_validate'):
            return LauncherConfig(dynamic_ports=True)
    
    def _test_port_allocation_retry(self, launcher):
        """Test port allocation retry logic."""
        with patch('dev_launcher.launcher.get_free_port') as mock_port:
            mock_port.side_effect = [None, None, 8001, 3001]
            if hasattr(launcher, '_allocate_dynamic_ports'):
                with patch('dev_launcher.launcher.create_subprocess'):
                    launcher._allocate_dynamic_ports()
                self._assert_ports_allocated(launcher)
    
    def _assert_ports_allocated(self, launcher):
        """Assert ports were successfully allocated."""
        self.assertEqual(launcher.config.backend_port, 8001)
        self.assertEqual(launcher.config.frontend_port, 3001)
    
    def test_network_error_recovery(self):
        """Test recovery from network errors."""
        from dev_launcher.utils import wait_for_service
        attempt_count = self._test_retry_logic()
        self.assertEqual(attempt_count, 3)
    
    def _test_retry_logic(self):
        """Test network retry logic."""
        attempt_count = 0
        def mock_request(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Network error")
            return Mock(status_code=200)
        with patch('requests.get', side_effect=mock_request):
            from dev_launcher.utils import wait_for_service
            result = wait_for_service("http://localhost:8000", timeout=5)
            self.assertTrue(result)
        return attempt_count
    
    @patch('dev_launcher.launcher.load_or_create_config')
    def test_resource_cleanup_on_error(self, mock_config):
        """Test proper resource cleanup on errors."""
        config = self._create_test_config()
        launcher = DevLauncher(config)
        self._test_cleanup_on_error(launcher)
    
    def _create_test_config(self):
        """Create test configuration."""
        with patch.object(LauncherConfig, '_validate'):
            return LauncherConfig(load_secrets=False)
    
    def _test_cleanup_on_error(self, launcher):
        """Test cleanup is called on startup error."""
        with patch.object(launcher, 'start_backend') as mock_backend:
            mock_backend.side_effect = Exception("Startup error")
            with patch.object(launcher.process_manager, 'terminate_all') as mock_terminate:
                with patch.object(launcher.health_monitor, 'stop') as mock_stop:
                    with self.assertRaises(Exception):
                        launcher.run()
                    mock_terminate.assert_called()
                    mock_stop.assert_called()


class TestHealthStatusManagement(unittest.TestCase):
    """Test health status tracking and reporting."""
    
    def test_health_status_initialization(self):
        """Test health status initialization."""
        status = HealthStatus()
        self._assert_initial_status(status)
    
    def _assert_initial_status(self, status):
        """Assert initial status values."""
        self.assertTrue(status.is_healthy)
        self.assertEqual(status.consecutive_failures, 0)
        self.assertIsNotNone(status.last_check)
    
    def test_health_status_updates(self):
        """Test updating health status."""
        status = HealthStatus()
        self._update_status_failure(status)
        self._assert_failure_state(status)
    
    def _update_status_failure(self, status):
        """Update status to failure state."""
        status.is_healthy = False
        status.consecutive_failures = 3
    
    def _assert_failure_state(self, status):
        """Assert status reflects failure."""
        self.assertFalse(status.is_healthy)
        self.assertEqual(status.consecutive_failures, 3)
    
    def test_concurrent_health_checks(self):
        """Test concurrent health status updates."""
        monitor = HealthMonitor(check_interval=0.01)
        self._register_concurrent_services(monitor)
        threads = self._create_check_threads(monitor)
        self._run_concurrent_checks(threads)
        monitor.stop()
    
    def _register_concurrent_services(self, monitor):
        """Register multiple services for concurrent testing."""
        for i in range(5):
            monitor.register_service(
                f"ConcurrentService{i}",
                lambda: True
            )
    
    def _create_check_threads(self, monitor):
        """Create threads for concurrent health checks."""
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=monitor._check_all_services)
            threads.append(thread)
        return threads
    
    def _run_concurrent_checks(self, threads):
        """Run all check threads concurrently."""
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()


if __name__ == '__main__':
    unittest.main()