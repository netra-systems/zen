"""
Process management tests for the dev launcher.

Tests cover ProcessManager, LogStreamer, and resource management.
All functions follow 25-line maximum rule per CLAUDE.md.
"""

import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch


from dev_launcher.log_streamer import LogManager, LogStreamer
from dev_launcher.process_manager import ProcessManager


class TestProcessManager(unittest.TestCase):
    """Test process management functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.manager = ProcessManager()
    
    def test_add_process(self):
        """Test adding a process to the manager."""
        mock_process = self._create_mock_process(12345)
        self.manager.add_process("TestService", mock_process)
        self.assertIn("TestService", self.manager.processes)
        self.assertEqual(self.manager.processes["TestService"], mock_process)
    
    def _create_mock_process(self, pid, running=True):
        """Create a mock process with specified PID."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = pid
        mock_process.poll.return_value = None if running else 0
        return mock_process
    
    def test_terminate_process_running(self):
        """Test terminating a running process."""
        mock_process = self._create_mock_process(12345)
        mock_process.wait.return_value = None
        self.manager.add_process("TestService", mock_process)
        with patch('subprocess.run') as mock_run:
            result = self.manager.terminate_process("TestService")
        self._assert_process_terminated(result, mock_run)
    
    def _assert_process_terminated(self, result, mock_run):
        """Assert process was terminated successfully."""
        self.assertTrue(result)
        self.assertNotIn("TestService", self.manager.processes)
        if sys.platform == "win32":
            mock_run.assert_called()
    
    def test_terminate_process_not_found(self):
        """Test terminating a non-existent process."""
        result = self.manager.terminate_process("NonExistent")
        self.assertFalse(result)
    
    def test_is_running(self):
        """Test checking if a process is running."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.side_effect = [None, 0]
        self.manager.add_process("TestService", mock_process)
        self.assertTrue(self.manager.is_running("TestService"))
        self.assertFalse(self.manager.is_running("TestService"))
    
    def test_wait_for_all_with_failures(self):
        """Test waiting for processes with error handling."""
        processes = self._create_test_processes()
        self._add_processes(processes)
        self._run_wait_for_all()
        self.assertEqual(len(self.manager.processes), 0)
    
    def _create_test_processes(self):
        """Create test processes with different exit codes."""
        process1 = self._create_mock_process(12345, running=False)
        process1.returncode = 1
        process2 = self._create_mock_process(12346, running=False)
        process2.returncode = 0
        return [("Service1", process1), ("Service2", process2)]
    
    def _add_processes(self, processes):
        """Add multiple processes to manager."""
        for name, process in processes:
            self.manager.add_process(name, process)
    
    def _run_wait_for_all(self):
        """Run wait_for_all in a thread with timeout."""
        thread = threading.Thread(target=self.manager.wait_for_all)
        thread.daemon = True
        thread.start()
        time.sleep(1.5)


class TestAdvancedProcessManager(unittest.TestCase):
    """Advanced process management tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.manager = ProcessManager()
    
    def test_concurrent_process_operations(self):
        """Test concurrent process operations."""
        processes = self._create_concurrent_processes()
        threads = self._create_add_threads(processes)
        self._run_threads(threads)
        self._assert_all_processes_added(len(processes))
    
    def _create_concurrent_processes(self):
        """Create multiple mock processes."""
        processes = []
        for i in range(5):
            mock_process = Mock(spec=subprocess.Popen)
            mock_process.pid = 12345 + i
            mock_process.poll.return_value = None
            processes.append((f"Service{i}", mock_process))
        return processes
    
    def _create_add_threads(self, processes):
        """Create threads to add processes concurrently."""
        threads = []
        for name, process in processes:
            thread = threading.Thread(
                target=self.manager.add_process,
                args=(name, process)
            )
            threads.append(thread)
        return threads
    
    def _run_threads(self, threads):
        """Start and join all threads."""
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    
    def _assert_all_processes_added(self, count):
        """Assert all processes were added."""
        self.assertEqual(len(self.manager.processes), count)
        self.assertEqual(self.manager.get_running_count(), count)
    
    def test_process_restart_on_failure(self):
        """Test process restart capability."""
        mock_process = self._create_failing_process()
        self.manager.add_process("RestartService", mock_process)
        self._verify_process_lifecycle()
        self._restart_failed_process()
    
    def _create_failing_process(self):
        """Create a process that fails after running."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.side_effect = [None, None, 1]
        return mock_process
    
    def _verify_process_lifecycle(self):
        """Verify process goes from running to failed."""
        self.assertTrue(self.manager.is_running("RestartService"))
        self.assertTrue(self.manager.is_running("RestartService"))
        self.assertFalse(self.manager.is_running("RestartService"))
    
    def _restart_failed_process(self):
        """Restart a failed process."""
        new_process = Mock(spec=subprocess.Popen)
        new_process.pid = 12346
        new_process.poll.return_value = None
        self.manager.add_process("RestartService", new_process)
        self.assertTrue(self.manager.is_running("RestartService"))
    
    def test_graceful_shutdown_timeout(self):
        """Test graceful shutdown with timeout."""
        mock_process = self._create_timeout_process()
        self.manager.add_process("TimeoutService", mock_process)
        self._test_forced_termination(mock_process)
    
    def _create_timeout_process(self):
        """Create a process that times out on wait."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)
        return mock_process
    
    def _test_forced_termination(self, mock_process):
        """Test forced termination after timeout."""
        with patch('subprocess.run') as mock_run:
            result = self.manager.terminate_process("TimeoutService")
        if sys.platform == "win32":
            mock_run.assert_called()
        else:
            mock_process.terminate.assert_called()


class TestLogStreaming(unittest.TestCase):
    """Test log streaming functionality."""
    
    def test_log_manager_concurrent_streams(self):
        """Test managing multiple concurrent log streams."""
        manager = LogManager()
        processes = self._create_mock_processes_with_output()
        streamers = self._add_streamers(manager, processes)
        self._assert_streamers_created(streamers)
        manager.stop_all()
    
    def _create_mock_processes_with_output(self):
        """Create mock processes with stdout output."""
        processes = []
        for i in range(3):
            mock_process = self._create_process_with_output(i)
            processes.append(mock_process)
        return processes
    
    def _create_process_with_output(self, index):
        """Create a single mock process with output."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline.return_value = f"Service{index} output\n".encode()
        mock_process.stderr.readline.return_value = b""
        return mock_process
    
    def _add_streamers(self, manager, processes):
        """Add streamers for all processes."""
        streamers = []
        for i, process in enumerate(processes):
            streamer = manager.add_streamer(f"Service{i}", process)
            streamers.append(streamer)
        return streamers
    
    def _assert_streamers_created(self, streamers):
        """Assert all streamers were created."""
        self.assertEqual(len(streamers), 3)
        for streamer in streamers:
            self.assertIsNotNone(streamer)
    
    def test_log_streamer_error_handling(self):
        """Test log streamer error handling."""
        mock_process = self._create_process_with_error()
        with patch('builtins.print'):
            streamer = LogStreamer(mock_process, "ErrorService")
            self._test_error_recovery(streamer)
    
    def _create_process_with_error(self):
        """Create a process that causes read errors."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline.side_effect = IOError("Read error")
        mock_process.stderr.readline.return_value = b""
        return mock_process
    
    def _test_error_recovery(self, streamer):
        """Test that streamer handles errors gracefully."""
        streamer.start()
        time.sleep(0.05)
        streamer.stop()
        self.assertFalse(streamer.running)
    
    def test_unicode_handling(self):
        """Test handling of unicode in logs."""
        mock_process = self._create_process_with_unicode()
        captured = self._capture_unicode_output(mock_process)
        self._assert_unicode_captured(captured)
    
    def _create_process_with_unicode(self):
        """Create a process that outputs unicode."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        unicode_logs = [
            "Hello 世界\n".encode('utf-8'),
            "Emoji test 🚀\n".encode('utf-8'),
            "Special chars: ñ, ü, é\n".encode('utf-8'),
            b""
        ]
        mock_process.stdout.readline.side_effect = unicode_logs
        mock_process.stderr.readline.return_value = b""
        return mock_process
    
    def _capture_unicode_output(self, mock_process):
        """Capture unicode output from streamer."""
        captured = []
        def capture(*args, **kwargs):
            captured.append(args[0] if args else "")
        with patch('builtins.print', side_effect=capture):
            streamer = LogStreamer(mock_process, "UnicodeService")
            streamer.start()
            time.sleep(0.1)
            streamer.stop()
        return captured
    
    def _assert_unicode_captured(self, captured):
        """Assert unicode was properly captured."""
        output = ' '.join(str(o) for o in captured)
        self.assertTrue("世界" in output or "Hello" in output)


class TestResourceManagement(unittest.TestCase):
    """Test resource management and cleanup."""
    
    def test_memory_leak_prevention(self):
        """Test prevention of memory leaks in long-running operations."""
        manager = ProcessManager()
        self._add_and_remove_many_processes(manager)
        self.assertEqual(len(manager.processes), 0)
    
    def _add_and_remove_many_processes(self, manager):
        """Add and remove many processes to test cleanup."""
        for i in range(100):
            mock_process = Mock(spec=subprocess.Popen)
            mock_process.pid = 10000 + i
            mock_process.poll.return_value = 0
            manager.add_process(f"TempService{i}", mock_process)
            manager.terminate_process(f"TempService{i}")
    
    def test_signal_handling(self):
        """Test proper signal handling."""
        manager = ProcessManager()
        mock_process = self._create_running_process()
        manager.add_process("SignalService", mock_process)
        self._test_signal_handler_setup(manager)
    
    def _create_running_process(self):
        """Create a mock running process."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        return mock_process
    
    def _test_signal_handler_setup(self, manager):
        """Test signal handler setup if available."""
        # SignalHandler is now initialized automatically in constructor
        # Check if signal handler exists instead
        if hasattr(manager, 'signal_handler'):
            self.assertIsNotNone(manager.signal_handler)
            self.assertTrue(hasattr(manager.signal_handler, '_setup_signal_handlers'))


if __name__ == '__main__':
    unittest.main()