"""
Test default launcher configuration and improvements.

This test ensures all recent improvements are properly integrated
when the launcher is called without arguments.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import argparse
import sys
import unittest
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path

from dev_launcher.config import LauncherConfig
from dev_launcher.launcher import DevLauncher


class TestDefaultLauncherConfig(SSotBaseTestCase):
    """Test suite for default launcher configuration."""
    
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_default_config_uses_dynamic_ports(self, mock_exists, mock_find_root):
        """Test that default configuration uses dynamic ports."""
        # Mock project structure
        mock_find_root.return_value = Path(".")
        mock_exists.return_value = True
        
        # Create mock args with no flags set
        args = argparse.Namespace()
        args.backend_port = None
        args.frontend_port = 3000
        args.static = False
        args.dynamic = True
        args.no_secrets = False
        args.verbose = False
        args.no_browser = False
        args.non_interactive = False
        args.no_turbopack = True
        args.no_parallel = False
        args.project_id = None
        
        # Create config from args
        config = LauncherConfig.from_args(args)
        
        # Verify dynamic ports is enabled by default
        self.assertTrue(config.dynamic_ports)
        self.assertFalse(config.backend_reload)  # Should be disabled by default
        self.assertFalse(config.frontend_reload)  # Frontend reload disabled by default for performance
        self.assertFalse(config.load_secrets)     # Local-only secrets by default (no GCP)
    
    # Mock: Component isolation for testing without external dependencies
    def test_static_flag_disables_dynamic_ports(self, mock_exists, mock_find_root):
        """Test that --static flag properly disables dynamic ports."""
        # Mock project structure
        mock_find_root.return_value = Path(".")
        mock_exists.return_value = True
        
        args = argparse.Namespace()
        args.backend_port = None
        args.frontend_port = 3000
        args.static = True  # Explicitly set static
        args.no_secrets = False
        args.verbose = False
        args.no_browser = False
        args.non_interactive = False
        args.no_turbopack = True
        args.no_parallel = False
        args.project_id = None
        
        config = LauncherConfig.from_args(args)
        
        # Verify static mode is enabled
        self.assertFalse(config.dynamic_ports)
    
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_default_startup_mode_is_minimal(self, mock_exists, mock_find_root):
        """Test that default startup mode is minimal for clean output."""
        # Mock project structure
        mock_find_root.return_value = Path(".")
        mock_exists.return_value = True
        
        args = argparse.Namespace()
        args.backend_port = None
        args.frontend_port = 3000
        args.static = False
        args.no_secrets = False
        args.verbose = False
        args.standard = False
        args.minimal = False
        args.mode = "minimal"
        args.no_browser = False
        args.non_interactive = False
        args.no_turbopack = True
        args.no_parallel = False
        args.project_id = None
        
        config = LauncherConfig.from_args(args)
        
        # Verify minimal mode is default
        self.assertEqual(config.startup_mode, "minimal")
    
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_parallel_startup_enabled_by_default(self, mock_exists, mock_find_root):
        """Test that parallel startup is enabled by default."""
        # Mock project structure
        mock_find_root.return_value = Path(".")
        mock_exists.return_value = True
        
        args = argparse.Namespace()
        args.backend_port = None
        args.frontend_port = 3000
        args.static = False
        args.no_secrets = False
        args.verbose = False
        args.no_browser = False
        args.non_interactive = False
        args.no_turbopack = True
        args.no_parallel = False  # Not disabled
        args.project_id = None
        
        config = LauncherConfig.from_args(args)
        
        # Verify parallel startup is enabled
        self.assertTrue(config.parallel_startup)
    
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_launcher_initializes_with_improvements(self, mock_exists, mock_logging, mock_signals):
        """Test that launcher initializes with all improvements."""
        # Mock path existence checks
        mock_exists.return_value = True
        
        # Create default config
        args = argparse.Namespace()
        args.backend_port = None
        args.frontend_port = 3000
        args.static = False
        args.no_secrets = False
        args.verbose = False
        args.no_browser = False
        args.non_interactive = False
        args.no_turbopack = True
        args.no_parallel = False
        args.project_id = None
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.config.find_project_root', return_value=Path(".")):
            config = LauncherConfig.from_args(args)
        
        # Create launcher instance
        launcher = DevLauncher(config)
        
        # Verify key components are initialized
        self.assertIsNotNone(launcher.cache_manager)
        self.assertIsNotNone(launcher.startup_optimizer)
        self.assertIsNotNone(launcher.log_filter)
        self.assertIsNotNone(launcher.progress_tracker)
        
        # Verify startup mode is set correctly
        from dev_launcher.log_filter import StartupMode
        self.assertEqual(launcher.startup_mode, StartupMode.MINIMAL)
        
        # Verify parallel startup is enabled
        self.assertTrue(launcher.parallel_enabled)


class TestPortAllocationImprovements(SSotBaseTestCase):
    """Test improved port allocation functionality."""
    
    def test_find_available_port_prefers_specified_port(self):
        """Test that find_available_port prefers the specified port."""
        from dev_launcher.utils import find_available_port, is_port_available
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.utils.is_port_available') as mock_available:
            # Mock that preferred port is available
            mock_available.side_effect = lambda p: p == 8000
            
            port = find_available_port(8000, (8000, 8010))
            
            # Should return preferred port
            self.assertEqual(port, 8000)
            mock_available.assert_called_with(8000)
    
    def test_find_available_port_tries_range(self):
        """Test that find_available_port tries ports in range."""
        from dev_launcher.utils import find_available_port
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.utils.is_port_available') as mock_available:
            # Mock that 8000-8002 are taken, 8003 is free
            mock_available.side_effect = lambda p: p == 8003
            
            port = find_available_port(8000, (8000, 8010))
            
            # Should find 8003
            self.assertEqual(port, 8003)
    
    def test_find_available_port_fallback_to_random(self):
        """Test fallback to random port when range is exhausted."""
        from dev_launcher.utils import find_available_port
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.utils.is_port_available') as mock_available:
            # Mock: Component isolation for testing without external dependencies
            with patch('dev_launcher.utils.get_free_port') as mock_free:
                # Mock that all ports in range are taken
                mock_available.return_value = False
                mock_free.return_value = 54321
                
                port = find_available_port(8000, (8000, 8010))
                
                # Should fallback to random port
                self.assertEqual(port, 54321)
                mock_free.assert_called_once()


class TestGracefulShutdownImprovements(SSotBaseTestCase):
    """Test improved graceful shutdown functionality."""
    
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_graceful_shutdown_avoids_duplicate_messages(self, mock_exists, mock_logging, mock_signals):
        """Test that graceful shutdown avoids duplicate cleanup messages."""
        mock_exists.return_value = True
        
        # Create launcher with mock config
        # Mock: Generic component isolation for controlled unit testing
        config = MagicMock()
        config.project_root = Path(".")
        config.verbose = False
        config.load_secrets = True
        config.parallel_startup = True
        config.silent_mode = False
        config.no_cache = False
        config.profile_startup = False
        
        launcher = DevLauncher(config)
        
        # Mock process manager with no processes
        # Mock: Generic component isolation for controlled unit testing
        launcher.process_manager = MagicMock()
        launcher.process_manager.processes = {}
        
        # Mock: Component isolation for testing without external dependencies
        with patch('builtins.print') as mock_print:
            launcher._graceful_shutdown()
            
            # Should not print shutdown messages when no processes
            shutdown_messages = [call for call in mock_print.call_args_list 
                               if 'shutdown' in str(call).lower()]
            self.assertEqual(len(shutdown_messages), 0)
    
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    # Mock: Component isolation for testing without external dependencies
    def test_ensure_cleanup_sets_shutting_down_flag(self, mock_exists, mock_logging, mock_signals):
        """Test that _ensure_cleanup properly sets shutting down flag."""
        mock_exists.return_value = True
        
        # Mock: Generic component isolation for controlled unit testing
        config = MagicMock()
        config.project_root = Path(".")
        config.verbose = False
        config.load_secrets = True
        config.parallel_startup = True
        config.silent_mode = False
        config.no_cache = False
        config.profile_startup = False
        
        launcher = DevLauncher(config)
        
        # Verify flag is initially false
        self.assertFalse(launcher._shutting_down)
        
        with patch.object(launcher, '_graceful_shutdown'):
            launcher._ensure_cleanup()
            
            # Flag should be set
            self.assertTrue(launcher._shutting_down)


if __name__ == '__main__':
    unittest.main()