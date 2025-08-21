"""
Test that launcher stays running and doesn't shutdown prematurely.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import threading
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dev_launcher.launcher import DevLauncher


class TestLauncherMainLoop(unittest.TestCase):
    """Test suite for verifying launcher stays running properly."""
    
    @patch('dev_launcher.launcher.DevLauncher._setup_signal_handlers')
    @patch('dev_launcher.launcher.setup_logging')
    @patch('pathlib.Path.exists')
    def test_optimized_startup_enters_main_loop(self, mock_exists, mock_logging, mock_signals):
        """Test that optimized startup properly enters the main loop."""
        mock_exists.return_value = True
        
        # Create mock config
        config = MagicMock()
        config.project_root = Path(".")
        config.verbose = False
        config.load_secrets = True
        config.parallel_startup = True
        config.silent_mode = False
        config.no_cache = False
        config.profile_startup = False
        config.legacy_mode = False
        
        launcher = DevLauncher(config)
        
        # Mock the process manager with running processes
        launcher.process_manager = MagicMock()
        launcher.process_manager.processes = {"Backend": MagicMock(), "Frontend": MagicMock()}
        launcher.process_manager.wait_for_all = MagicMock()
        
        # Mock the optimized startup
        launcher.optimized_startup = MagicMock()
        
        # Create actual optimized startup orchestrator
        orchestrator = OptimizedStartupOrchestrator(launcher)
        
        # Mock successful sequence execution
        orchestrator.sequencer = MagicMock()
        orchestrator.sequencer.execute_sequence = MagicMock(return_value={})
        orchestrator.sequencer.get_sequence_summary = MagicMock(return_value={})
        orchestrator.progress = MagicMock()
        
        # Mock _show_startup_summary to prevent actual output
        orchestrator._show_startup_summary = MagicMock()
        
        # Mock launcher's _run_main_loop to verify it's called
        launcher._run_main_loop = MagicMock()
        launcher._handle_cleanup = MagicMock(return_value=0)
        
        # Run the complete startup success
        result = orchestrator._complete_startup_success()
        
        # Verify main loop was called
        launcher._run_main_loop.assert_called_once()
        
        # Verify cleanup was called after main loop
        launcher._handle_cleanup.assert_called_once()
        
        self.assertEqual(result, 0)
    
    @patch('dev_launcher.launcher.DevLauncher._setup_signal_handlers')
    @patch('dev_launcher.launcher.setup_logging')
    @patch('pathlib.Path.exists')
    def test_legacy_runner_enters_main_loop(self, mock_exists, mock_logging, mock_signals):
        """Test that legacy runner properly enters the main loop."""
        mock_exists.return_value = True
        
        # Create mock config
        config = MagicMock()
        config.project_root = Path(".")
        config.verbose = False
        config.load_secrets = True
        config.parallel_startup = True
        config.silent_mode = False
        config.no_cache = False
        config.profile_startup = False
        config.legacy_mode = True
        
        launcher = DevLauncher(config)
        
        # Create legacy runner
        legacy_runner = LegacyServiceRunner(launcher)
        
        # Mock service startup methods
        legacy_runner._start_and_verify_auth = MagicMock(return_value=0)
        legacy_runner._start_and_verify_backend = MagicMock(return_value=0)
        legacy_runner._start_and_verify_frontend = MagicMock(return_value=0)
        
        # Mock launcher methods
        launcher._run_main_loop = MagicMock()
        launcher._handle_cleanup = MagicMock(return_value=0)
        launcher.process_manager = MagicMock()
        launcher.process_manager.add_process = MagicMock()
        launcher.service_startup = MagicMock()
        launcher.service_startup.start_frontend = MagicMock(return_value=(MagicMock(), None))
        
        # Run sequential services
        result = legacy_runner.run_services_sequential()
        
        # Verify main loop was called
        launcher._run_main_loop.assert_called_once()
        
        # Verify cleanup was called
        launcher._handle_cleanup.assert_called_once()
        
        self.assertEqual(result, 0)
    
    @patch('dev_launcher.launcher.DevLauncher._setup_signal_handlers')
    @patch('dev_launcher.launcher.setup_logging')
    @patch('pathlib.Path.exists')
    def test_main_loop_waits_for_processes(self, mock_exists, mock_logging, mock_signals):
        """Test that main loop properly waits for all processes."""
        mock_exists.return_value = True
        
        config = MagicMock()
        config.project_root = Path(".")
        config.verbose = False
        config.load_secrets = True
        config.parallel_startup = True
        config.silent_mode = False
        config.no_cache = False
        config.profile_startup = False
        config.legacy_mode = False
        
        launcher = DevLauncher(config)
        
        # Mock process manager
        launcher.process_manager = MagicMock()
        launcher.process_manager.wait_for_all = MagicMock()
        
        # Call _run_main_loop
        launcher._run_main_loop()
        
        # Verify wait_for_all was called
        launcher.process_manager.wait_for_all.assert_called_once()
    
    @patch('dev_launcher.launcher.DevLauncher._setup_signal_handlers')
    @patch('dev_launcher.launcher.setup_logging')
    @patch('pathlib.Path.exists')
    def test_process_manager_keeps_running_with_active_processes(self, mock_exists, mock_logging, mock_signals):
        """Test that process manager keeps running while processes are active."""
        mock_exists.return_value = True
        
        from dev_launcher.process_manager import ProcessManager
        
        # Create real process manager
        pm = ProcessManager(health_monitor=None)
        
        # Create mock processes that stay "running"
        mock_backend = MagicMock()
        mock_backend.poll.return_value = None  # None means still running
        
        mock_frontend = MagicMock()
        mock_frontend.poll.return_value = None  # None means still running
        
        # Add processes
        pm.add_process("Backend", mock_backend)
        pm.add_process("Frontend", mock_frontend)
        
        # Verify processes are considered running
        self.assertTrue(pm.is_running("Backend"))
        self.assertTrue(pm.is_running("Frontend"))
        self.assertEqual(pm.get_running_count(), 2)
        
        # Create a thread that will simulate wait_for_all behavior
        # It should keep checking while processes are running
        check_count = [0]
        
        def simulate_wait():
            while pm.processes and check_count[0] < 5:
                for name, proc in list(pm.processes.items()):
                    if proc.poll() is not None:
                        pm._remove_from_processes(name)
                check_count[0] += 1
                time.sleep(0.1)
        
        # Run simulation in thread with timeout
        thread = threading.Thread(target=simulate_wait)
        thread.start()
        thread.join(timeout=1.0)
        
        # Verify the loop ran multiple times (processes stayed running)
        self.assertGreater(check_count[0], 1)
        
        # Processes should still be in the manager
        self.assertEqual(len(pm.processes), 2)


if __name__ == '__main__':
    unittest.main()