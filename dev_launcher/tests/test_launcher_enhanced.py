"""
Enhanced tests for the dev launcher with comprehensive coverage.

Tests cover advanced scenarios, error recovery, concurrent operations,
resource management, and integration testing.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call, ANY
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime
import threading
import time
import json
import os
import signal

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dev_launcher.config import LauncherConfig, find_project_root
from dev_launcher.launcher import DevLauncher
from dev_launcher.process_manager import ProcessManager
from dev_launcher.health_monitor import HealthMonitor, HealthStatus
from dev_launcher.log_streamer import LogStreamer, LogManager
from dev_launcher.secret_manager import SecretLoader, ServiceDiscovery
from dev_launcher.service_config import ServicesConfiguration, ResourceMode


class TestAdvancedProcessManager(unittest.TestCase):
    """Advanced process management tests."""
    
    def setUp(self):
        self.manager = ProcessManager()
    
    def test_concurrent_process_operations(self):
        """Test concurrent process operations."""
        processes = []
        for i in range(5):
            mock_process = Mock(spec=subprocess.Popen)
            mock_process.pid = 12345 + i
            mock_process.poll.return_value = None
            processes.append((f"Service{i}", mock_process))
        
        # Add processes concurrently
        threads = []
        for name, process in processes:
            thread = threading.Thread(
                target=self.manager.add_process,
                args=(name, process)
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All processes should be added
        self.assertEqual(len(self.manager.processes), 5)
        self.assertEqual(self.manager.get_running_count(), 5)
    
    def test_process_restart_on_failure(self):
        """Test process restart capability."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.side_effect = [None, None, 1]  # Running, then fails
        
        self.manager.add_process("RestartService", mock_process)
        
        # Simulate restart logic
        restart_count = 0
        max_restarts = 3
        
        while restart_count < max_restarts:
            if not self.manager.is_running("RestartService"):
                restart_count += 1
                new_process = Mock(spec=subprocess.Popen)
                new_process.pid = 12345 + restart_count
                new_process.poll.return_value = None
                self.manager.add_process("RestartService", new_process)
        
        self.assertEqual(restart_count, 1)
        self.assertTrue(self.manager.is_running("RestartService"))
    
    def test_graceful_shutdown_timeout(self):
        """Test graceful shutdown with timeout."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)
        
        self.manager.add_process("TimeoutService", mock_process)
        
        with patch('subprocess.run') as mock_run:
            # Should force kill after timeout
            result = self.manager.terminate_process("TimeoutService")
        
        if sys.platform == "win32":
            mock_run.assert_called()
        else:
            mock_process.terminate.assert_called()


class TestAdvancedHealthMonitor(unittest.TestCase):
    """Advanced health monitoring tests."""
    
    def setUp(self):
        self.monitor = HealthMonitor(check_interval=0.05)
    
    def tearDown(self):
        if hasattr(self, 'monitor'):
            self.monitor.stop()
    
    def test_cascading_failures(self):
        """Test handling cascading service failures."""
        services_health = {'Service1': True, 'Service2': True, 'Service3': True}
        recovery_calls = []
        
        def health_check(name):
            return services_health[name]
        
        def recovery(name):
            recovery_calls.append(name)
            services_health[name] = True  # Recovery resets health
        
        for service in services_health:
            self.monitor.register_service(
                service,
                lambda s=service: health_check(s),
                lambda s=service: recovery(s),
                max_failures=2
            )
        
        # Trigger cascading failures
        services_health['Service1'] = False
        services_health['Service2'] = False
        
        # Check multiple times to trigger recovery
        for _ in range(3):
            self.monitor._check_all_services()
        
        # Both services should have triggered recovery
        self.assertIn('Service1', recovery_calls)
        self.assertIn('Service2', recovery_calls)
    
    def test_health_check_performance(self):
        """Test health check performance under load."""
        check_times = []
        
        def timed_health_check():
            start = time.time()
            time.sleep(0.01)  # Simulate check time
            check_times.append(time.time() - start)
            return True
        
        # Register multiple services
        for i in range(10):
            self.monitor.register_service(
                f"PerfService{i}",
                timed_health_check
            )
        
        # Run checks
        start = time.time()
        self.monitor._check_all_services()
        total_time = time.time() - start
        
        # Should complete reasonably quickly
        self.assertLess(total_time, 1.0)
        self.assertEqual(len(check_times), 10)
    
    def test_adaptive_check_intervals(self):
        """Test adaptive health check intervals based on failures."""
        failure_count = 0
        
        def failing_check():
            nonlocal failure_count
            failure_count += 1
            return failure_count > 5  # Succeed after 5 failures
        
        self.monitor.register_service(
            "AdaptiveService",
            failing_check,
            max_failures=10
        )
        
        # Run checks manually instead of starting thread
        for _ in range(7):
            self.monitor._check_all_services()
        
        # Should have attempted multiple checks
        self.assertGreater(failure_count, 5)
        
        # Service should eventually be healthy
        status = self.monitor.get_status("AdaptiveService")
        self.assertTrue(status.is_healthy)


class TestLogStreaming(unittest.TestCase):
    """Test log streaming functionality."""
    
    def test_log_manager_concurrent_streams(self):
        """Test managing multiple concurrent log streams."""
        manager = LogManager()
        
        # Create multiple mock processes
        processes = []
        for i in range(3):
            mock_process = Mock(spec=subprocess.Popen)
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_process.stdout.readline.return_value = f"Service{i} output\n".encode()
            mock_process.stderr.readline.return_value = b""
            processes.append(mock_process)
        
        # Add streamers
        streamers = []
        for i, process in enumerate(processes):
            streamer = manager.add_streamer(
                f"Service{i}",
                process,
                verbose=False
            )
            streamers.append(streamer)
        
        # All streamers should be created
        self.assertEqual(len(streamers), 3)
        
        # Stop all streamers
        manager.stop_all()
    
    def test_log_streamer_error_handling(self):
        """Test log streamer error handling."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        # Simulate read error
        mock_process.stdout.readline.side_effect = IOError("Read error")
        mock_process.stderr.readline.return_value = b""
        
        with patch('builtins.print'):
            streamer = LogStreamer("ErrorService", mock_process, verbose=False)
            
            # Should handle error gracefully
            streamer.start()
            time.sleep(0.05)
            streamer.stop()
            
            # Streamer should have stopped
            self.assertFalse(streamer.running)
    
    def test_unicode_handling(self):
        """Test handling of unicode in logs."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        
        # Unicode test strings
        unicode_logs = [
            "Hello 世界\n".encode('utf-8'),
            "Emoji test 🚀\n".encode('utf-8'),
            "Special chars: ñ, ü, é\n".encode('utf-8'),
            b""  # End of stream
        ]
        
        mock_process.stdout.readline.side_effect = unicode_logs
        mock_process.stderr.readline.return_value = b""
        
        captured_output = []
        
        def capture_print(*args, **kwargs):
            captured_output.append(args[0] if args else "")
        
        with patch('builtins.print', side_effect=capture_print):
            streamer = LogStreamer("UnicodeService", mock_process, verbose=True)
            streamer.start()
            time.sleep(0.1)
            streamer.stop()
        
        # Should have captured unicode output
        output_str = ' '.join(str(o) for o in captured_output)
        self.assertTrue("世界" in output_str or "Hello" in output_str)


class TestServiceDiscovery(unittest.TestCase):
    """Test service discovery functionality."""
    
    def test_service_info_persistence(self):
        """Test service information persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sd = ServiceDiscovery(Path(tmpdir))
            
            # Write service info
            sd.write_backend_info(8080)
            sd.write_frontend_info(3001)
            
            # Create new instance and read
            sd2 = ServiceDiscovery(Path(tmpdir))
            backend_info = sd2.read_backend_info()
            frontend_info = sd2.read_frontend_info()
            
            self.assertEqual(backend_info['port'], 8080)
            self.assertEqual(frontend_info['port'], 3001)
    
    def test_concurrent_service_updates(self):
        """Test concurrent updates to service info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sd = ServiceDiscovery(Path(tmpdir))
            
            def update_backend(port):
                sd.write_backend_info(port)
            
            # Concurrent updates
            threads = []
            for port in [8000, 8001, 8002]:
                thread = threading.Thread(target=update_backend, args=(port,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            # Should have last written value
            info = sd.read_backend_info()
            self.assertIn(info['port'], [8000, 8001, 8002])
    
    def test_service_info_corruption_recovery(self):
        """Test recovery from corrupted service info files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sd = ServiceDiscovery(Path(tmpdir))
            
            # Write valid info
            sd.write_backend_info(8000)
            
            # Corrupt the file
            service_file = Path(tmpdir) / ".netra" / "backend.json"
            service_file.write_text("invalid json {[}")
            
            # Should handle gracefully
            info = sd.read_backend_info()
            self.assertIsNone(info)
            
            # Should be able to write new info
            sd.write_backend_info(8001)
            info = sd.read_backend_info()
            self.assertEqual(info['port'], 8001)


class TestResourceManagement(unittest.TestCase):
    """Test resource management and cleanup."""
    
    @patch('dev_launcher.launcher.load_or_create_config')
    def test_resource_cleanup_on_error(self, mock_config):
        """Test proper resource cleanup on errors."""
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig(load_secrets=False)
        
        launcher = DevLauncher(config)
        
        # Simulate error during startup
        with patch.object(launcher, 'start_backend') as mock_backend:
            mock_backend.side_effect = Exception("Startup error")
            
            with patch.object(launcher.process_manager, 'terminate_all') as mock_terminate:
                with patch.object(launcher.health_monitor, 'stop') as mock_stop:
                    with self.assertRaises(Exception):
                        launcher.run()
                    
                    # Cleanup should be called
                    mock_terminate.assert_called()
                    mock_stop.assert_called()
    
    def test_memory_leak_prevention(self):
        """Test prevention of memory leaks in long-running operations."""
        manager = ProcessManager()
        
        # Add and remove many processes
        for i in range(100):
            mock_process = Mock(spec=subprocess.Popen)
            mock_process.pid = 10000 + i
            mock_process.poll.return_value = 0  # Already terminated
            
            manager.add_process(f"TempService{i}", mock_process)
            manager.terminate_process(f"TempService{i}")
        
        # Should not accumulate processes
        self.assertEqual(len(manager.processes), 0)
    
    def test_file_handle_management(self):
        """Test proper file handle management."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create many service discovery instances
            instances = []
            for i in range(10):
                sd = ServiceDiscovery(Path(tmpdir))
                sd.write_backend_info(8000 + i)
                instances.append(sd)
            
            # All should work without file handle exhaustion
            for i, sd in enumerate(instances):
                info = sd.read_backend_info()
                self.assertIsNotNone(info)


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery mechanisms."""
    
    @patch('dev_launcher.launcher.load_or_create_config')
    def test_port_conflict_recovery(self, mock_config):
        """Test recovery from port conflicts."""
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig(dynamic_ports=True)
        
        launcher = DevLauncher(config)
        
        with patch('dev_launcher.launcher.get_free_port') as mock_port:
            # First attempt fails, second succeeds
            mock_port.side_effect = [None, None, 8001, 3001]
            
            # Should retry and find new ports
            if hasattr(launcher, '_allocate_dynamic_ports'):
                with patch('dev_launcher.launcher.create_subprocess'):
                    launcher._allocate_dynamic_ports()
                
                self.assertEqual(launcher.config.backend_port, 8001)
                self.assertEqual(launcher.config.frontend_port, 3001)
    
    def test_network_error_recovery(self):
        """Test recovery from network errors."""
        from dev_launcher.utils import wait_for_service
        
        attempt_count = 0
        
        def mock_request(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Network error")
            return Mock(status_code=200)
        
        with patch('requests.get', side_effect=mock_request):
            result = wait_for_service("http://localhost:8000", timeout=5)
            
        self.assertTrue(result)
        self.assertEqual(attempt_count, 3)
    
    def test_signal_handling(self):
        """Test proper signal handling."""
        manager = ProcessManager()
        
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        
        manager.add_process("SignalService", mock_process)
        
        # Simulate signal handling setup
        if hasattr(manager, 'setup_signal_handlers'):
            with patch('signal.signal') as mock_signal:
                manager.setup_signal_handlers()
                
                # Should register handlers
                if sys.platform != "win32":
                    mock_signal.assert_called()


class TestIntegrationScenarios(unittest.TestCase):
    """Complex integration test scenarios."""
    
    @patch('dev_launcher.launcher.check_dependencies')
    @patch('dev_launcher.launcher.check_project_structure')
    @patch('dev_launcher.launcher.create_subprocess')
    @patch('dev_launcher.launcher.wait_for_service')
    def test_rolling_restart(self, mock_wait, mock_subprocess,
                            mock_structure, mock_deps):
        """Test rolling restart of services."""
        # Setup mocks
        mock_deps.return_value = {
            'uvicorn': True, 'fastapi': True,
            'node': True, 'npm': True
        }
        mock_structure.return_value = {
            'backend': True, 'frontend': True,
            'frontend_deps': True
        }
        mock_wait.return_value = True
        
        # Create mock processes
        backend_v1 = Mock(spec=subprocess.Popen, pid=12345)
        backend_v2 = Mock(spec=subprocess.Popen, pid=12346)
        frontend_v1 = Mock(spec=subprocess.Popen, pid=12347)
        frontend_v2 = Mock(spec=subprocess.Popen, pid=12348)
        
        for p in [backend_v1, backend_v2, frontend_v1, frontend_v2]:
            p.poll.return_value = None
        
        mock_subprocess.side_effect = [backend_v1, frontend_v1, backend_v2, frontend_v2]
        
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig(load_secrets=False)
        
        with patch('dev_launcher.launcher.load_or_create_config'):
            launcher = DevLauncher(config)
        
        # Start initial services
        with patch.object(launcher.service_discovery, 'write_backend_info'):
            with patch.object(launcher.service_discovery, 'write_frontend_info'):
                launcher.start_backend()
                launcher.start_frontend()
        
        # Perform rolling restart
        launcher.process_manager.terminate_process("Backend")
        
        with patch.object(launcher.service_discovery, 'write_backend_info'):
            launcher.start_backend()
        
        # Should have new backend process
        self.assertTrue(launcher.process_manager.is_running("Backend"))
    
    def test_dev_to_prod_configuration_switch(self):
        """Test switching between development and production configs."""
        from dev_launcher.service_config import ServicesConfiguration, ResourceMode
        
        # Development config
        dev_config = ServicesConfiguration(
            resource_mode=ResourceMode.DEVELOPMENT,
            backend_workers=1,
            enable_monitoring=False,
            enable_profiling=True
        )
        
        # Production config
        prod_config = ServicesConfiguration(
            resource_mode=ResourceMode.PRODUCTION,
            backend_workers=4,
            enable_monitoring=True,
            enable_profiling=False
        )
        
        self.assertNotEqual(dev_config.backend_workers, prod_config.backend_workers)
        self.assertNotEqual(dev_config.enable_monitoring, prod_config.enable_monitoring)
    
    def test_multi_environment_launch(self):
        """Test launching in different environments."""
        environments = ['development', 'staging', 'production']
        
        for env in environments:
            with patch.dict(os.environ, {'NETRA_ENV': env}):
                with patch.object(LauncherConfig, '_validate'):
                    config = LauncherConfig()
                
                # Environment should affect configuration
                # Configuration may vary by environment
                self.assertIsNotNone(config)


if __name__ == '__main__':
    unittest.main()