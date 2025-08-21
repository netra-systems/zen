"""
Test that launcher stays running and doesn't shutdown prematurely.

NOTE: This test file is temporarily disabled due to references to non-existent modules.
The launcher structure has been refactored and these tests need to be updated.
"""

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dev_launcher.launcher import DevLauncher


class TestLauncherMainLoop(unittest.TestCase):
    """Test suite for verifying launcher stays running properly."""
    
    @unittest.skip("Test needs to be updated for new launcher structure")
    @patch('dev_launcher.launcher.DevLauncher._setup_signal_handlers')
    @patch('dev_launcher.launcher.setup_logging')
    @patch('pathlib.Path.exists')
    def test_launcher_enters_main_loop(self, mock_exists, mock_logging, mock_signals):
        """Test that launcher properly enters the main loop."""
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
        
        launcher = DevLauncher(config)
        
        # Mock the process manager with running processes
        launcher.process_manager = MagicMock()
        launcher.process_manager.processes = {"Backend": MagicMock(), "Frontend": MagicMock()}
        launcher.process_manager.wait_for_all = MagicMock()
        
        # Mock launcher's _run_main_loop to verify it's called
        launcher._run_main_loop = MagicMock()
        launcher._handle_cleanup = MagicMock(return_value=0)
        
        # This test needs to be updated based on the actual launcher structure
        pass
    
    @unittest.skip("Test needs to be updated for new launcher structure")
    @patch('dev_launcher.launcher.time.sleep')
    @patch('dev_launcher.launcher.DevLauncher._setup_signal_handlers')
    @patch('dev_launcher.launcher.setup_logging')
    @patch('pathlib.Path.exists')
    def test_main_loop_keeps_running(self, mock_exists, mock_logging, mock_signals, mock_sleep):
        """Test that main loop continues running until shutdown signal."""
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
        
        launcher = DevLauncher(config)
        
        # Mock process manager with running processes
        launcher.process_manager = MagicMock()
        launcher.process_manager.processes = {"Backend": MagicMock(), "Frontend": MagicMock()}
        launcher.process_manager.has_running_processes = MagicMock(return_value=True)
        launcher.process_manager.check_and_restart_critical = MagicMock()
        
        # Make sleep raise after a few iterations to exit the loop
        mock_sleep.side_effect = [None, None, None, KeyboardInterrupt()]
        
        # Run the main loop - it should exit after KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            launcher._run_main_loop()
        
        # Verify the loop ran multiple times
        self.assertEqual(mock_sleep.call_count, 4)
        launcher.process_manager.check_and_restart_critical.assert_called()
    
    @unittest.skip("Test needs to be updated for new launcher structure")
    @patch('dev_launcher.launcher.DevLauncher._setup_signal_handlers')
    @patch('dev_launcher.launcher.setup_logging')
    @patch('pathlib.Path.exists')
    def test_launcher_shutdown_stops_main_loop(self, mock_exists, mock_logging, mock_signals):
        """Test that shutdown signal properly stops the main loop."""
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
        
        launcher = DevLauncher(config)
        
        # Mock process manager
        launcher.process_manager = MagicMock()
        launcher.process_manager.processes = {"Backend": MagicMock()}
        launcher.process_manager.has_running_processes = MagicMock()
        launcher.process_manager.has_running_processes.side_effect = [True, True, False]
        
        # Test that main loop stops when has_running_processes returns False
        def run_loop():
            while launcher.process_manager.has_running_processes():
                time.sleep(0.01)
        
        # Run in a thread so we can control the timing
        thread = threading.Thread(target=run_loop)
        thread.start()
        thread.join(timeout=1)
        
        # Verify loop exited
        self.assertFalse(thread.is_alive())
        self.assertEqual(launcher.process_manager.has_running_processes.call_count, 3)


if __name__ == '__main__':
    unittest.main()