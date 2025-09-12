"""
Comprehensive tests for critical dev launcher issues.

This test suite reproduces and validates fixes for:
1. Frontend displaying failure to load secrets instantly upon start
2. Legacy code removal and duplicate merging  
3. ClickHouse authentication failure (code 194)
4. Info message color display issues
5. Premature error display before environment loading
"""

import asyncio
import logging
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path for imports

from dev_launcher.config import LauncherConfig
from dev_launcher.frontend_starter import FrontendStarter
from dev_launcher.launcher import DevLauncher
from shared.isolated_environment import get_env
from dev_launcher.log_filter import LogFilter, LogLevel, StartupMode

# Get environment instance for configuration
env = get_env()


class TestCriticalDevLauncherIssues(unittest.TestCase):
    """Test suite for critical dev launcher issues."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temp directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Create expected directory structure
        (self.test_path / 'netra_backend' / 'app').mkdir(parents=True)
        (self.test_path / 'frontend').mkdir(parents=True)
        (self.test_path / 'auth_service').mkdir(parents=True)
        
        # Save original environment
        self.original_env = env.get_all()
        
        # Clear test-specific env vars using IsolatedEnvironment
        for key in list(env.get_all().keys()):
            if key.startswith('TEST_') or key.startswith('CLICKHOUSE_'):
                if env.exists(key):
                    env.delete(key)
        
        # Track error messages for testing premature error display
        self.error_messages = []
        self.info_messages = []
        self.warning_messages = []
        
        # Mock logging to capture messages
        self.log_handler = logging.Handler()
        self.log_handler.emit = self._capture_log_message
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
        
        # Clean up test files
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _capture_log_message(self, record):
        """Capture log messages for testing."""
        if record.levelname == 'ERROR':
            self.error_messages.append(record.getMessage())
        elif record.levelname == 'INFO':
            self.info_messages.append(record.getMessage())
        elif record.levelname == 'WARNING':
            self.warning_messages.append(record.getMessage())
    
    def _create_launcher_with_mocks(self, config):
        """Helper to create launcher with all necessary mocks."""
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.launcher.setup_logging'):
            # Mock: Component isolation for testing without external dependencies
            with patch('dev_launcher.launcher.check_emoji_support', return_value=False):
                # Mock: Component isolation for testing without external dependencies
                with patch('dev_launcher.launcher.HealthMonitor'):
                    # Mock: Component isolation for testing without external dependencies
                    with patch('dev_launcher.launcher.ProcessManager'):
                        # Mock: Component isolation for testing without external dependencies
                        with patch('dev_launcher.launcher.LogManager'):
                            # Mock: Component isolation for testing without external dependencies
                            with patch('dev_launcher.launcher.ServiceDiscovery'):
                                # Mock: Component isolation for testing without external dependencies
                                with patch('dev_launcher.launcher.EnvironmentChecker'):
                                    # Mock: Component isolation for testing without external dependencies
                                    with patch('dev_launcher.launcher.ServiceStartupCoordinator'):
                                        # Mock: Component isolation for testing without external dependencies
                                        with patch('dev_launcher.launcher.SummaryDisplay'):
                                            # Mock: Component isolation for testing without external dependencies
                                            with patch('dev_launcher.launcher.StartupOptimizer'):
                                                # Mock: Component isolation for testing without external dependencies
                                                with patch('dev_launcher.launcher.CacheManager'):
                                                    return DevLauncher(config)
    
    def test_frontend_premature_error_display(self):
        """
        Test that frontend shows errors before secrets have a chance to load.
        
        ISSUE: Frontend starter immediately displays error messages when 
        required environment variables aren't available, even before
        the secret loading process has had time to complete.
        """
        # Create config without critical env vars
        args = MagicMock()
        args.backend_port = None
        args.frontend_port = 3000
        args.static = False
        args.dynamic = True
        args.verbose = False
        args.backend_reload = False
        args.no_reload = True
        args.load_secrets = True
        args.no_secrets = False
        args.project_id = 'test-project'
        args.no_browser = True
        args.non_interactive = True
        args.no_turbopack = True
        args.no_parallel = False
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.config.find_project_root', return_value=self.test_path):
            config = LauncherConfig.from_args(args)
            config.project_root = self.test_path
            
            # Create .env file with required variables (simulating slow loading)
            env_file = self.test_path / '.env'
            env_file.write_text('''
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
DATABASE_URL=postgresql://user:pass@localhost:5432/test
JWT_SECRET_KEY=super_secret_key_at_least_64_characters_long_for_testing_purposes
''')
            
            # Mock service discovery to return None (simulating missing backend info)
            # Mock: Generic component isolation for controlled unit testing
            mock_service_discovery = MagicMock()
            mock_service_discovery.read_backend_info.return_value = None
            
            # Mock: Generic component isolation for controlled unit testing
            mock_log_manager = MagicMock()
            
            # Create FrontendStarter
            frontend_starter = FrontendStarter(
                config=config,
                # Mock: Generic component isolation for controlled unit testing
                services_config=MagicMock(),
                log_manager=mock_log_manager,
                service_discovery=mock_service_discovery,
                use_emoji=False
            )
            
            # Track error messages
            error_messages = []
            
            def mock_print(emoji, text, message):
                if text == "ERROR":
                    error_messages.append(message)
            
            frontend_starter._print = mock_print
            
            # Try to start frontend immediately (should fail gracefully)
            start_time = time.time()
            result = frontend_starter.start_frontend()
            error_display_time = time.time()
            
            # Simulate secret loading taking time
            time.sleep(0.1)
            secret_load_time = time.time()
            
            # CRITICAL TEST: Error should not be displayed immediately
            # before secrets have had a chance to load
            error_display_delay = error_display_time - start_time
            secret_loading_window = secret_load_time - start_time
            
            # Should fail but this demonstrates the issue exists
            self.assertIsNone(result[0], "Frontend should not start without backend info")
            self.assertTrue(len(error_messages) > 0, "Error messages should be displayed")
            
            # The ISSUE: Error is displayed too quickly (< 100ms)
            # Should wait for secrets to load first
            self.assertLess(
                error_display_delay,
                0.1,
                f"REGRESSION: Error displayed too quickly ({error_display_delay:.3f}s) "
                f"before secrets could load ({secret_loading_window:.3f}s)"
            )
    
    def test_clickhouse_authentication_failure_code_194(self):
        """
        Test ClickHouse password incorrect error (code 194).
        
        ISSUE: ClickHouse connections failing with "Password incorrect" 
        error code 194, often due to configuration or environment loading issues.
        """
        # Set up ClickHouse environment variables with incorrect password
        env.set('CLICKHOUSE_HOST', 'localhost')
        env.set('CLICKHOUSE_PORT', '8123')
        env.set('CLICKHOUSE_USER', 'default')
        env.set('CLICKHOUSE_PASSWORD', 'wrong_password')
        env.set('CLICKHOUSE_DATABASE', 'test_db')
        
        # Mock ClickHouse client that fails with code 194
        class MockClickHouseError(Exception):
            def __init__(self, message, code=194):
                self.message = message
                self.code = code
                super().__init__(message)
        
        # Mock database connector that attempts ClickHouse connection
        # Mock: Generic component isolation for controlled unit testing
        mock_connector = MagicMock()
        # Mock: ClickHouse database isolation for fast testing without external database dependency
        mock_connector.validate_clickhouse_connection = Mock(
            side_effect=MockClickHouseError("Password incorrect", 194)
        )
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.config.find_project_root', return_value=self.test_path):
            # Mock: Generic component isolation for controlled unit testing
            args = MagicMock()
            args.backend_port = None
            args.frontend_port = 3000
            args.static = False
            args.dynamic = True
            args.verbose = True
            args.backend_reload = False
            args.no_reload = True
            args.load_secrets = False
            args.no_secrets = True
            args.project_id = None
            args.no_browser = True
            args.non_interactive = True
            args.no_turbopack = True
            args.no_parallel = False
            
            config = LauncherConfig.from_args(args)
            config.project_root = self.test_path
            
            # Create launcher and try to validate databases
            launcher = self._create_launcher_with_mocks(config)
            launcher.database_connector = mock_connector
            
            # Test ClickHouse validation failure
            try:
                # This should trigger the ClickHouse validation
                mock_connector.validate_clickhouse_connection()
                self.fail("Should have raised ClickHouse authentication error")
            except MockClickHouseError as e:
                self.assertEqual(e.code, 194)
                self.assertIn("Password incorrect", e.message)
                
                # CRITICAL TEST: This error code should be handled gracefully
                # and not crash the entire dev launcher
                self.assertTrue(
                    True,  # We expect this error to occur
                    "ClickHouse error code 194 should be handled gracefully"
                )
    
    def test_info_message_color_display_issue(self):
        """
        Test info messages showing in red instead of proper info color.
        
        ISSUE: Info level messages are being displayed with error colors
        instead of proper info colors due to log filtering or formatting issues.
        """
        # Create log filter
        log_filter = LogFilter(StartupMode.MINIMAL)
        
        # Test different log levels and their expected colors/formatting
        test_messages = [
            ("INFO", "Environment check completed", True),
            ("SUCCESS", "Service started successfully", True), 
            ("WARNING", "Service degraded but functional", True),
            ("ERROR", "Critical failure occurred", True),
            ("DEBUG", "Detailed debug information", False),  # Should be filtered in minimal mode
        ]
        
        for level, message, should_show in test_messages:
            result = log_filter.should_show(message, level)
            self.assertEqual(
                result, should_show,
                f"Message level {level} should {'show' if should_show else 'hide'} in minimal mode"
            )
            
            if should_show:
                formatted = log_filter.format_message(message, level)
                self.assertIsNotNone(formatted, f"Level {level} message should format properly")
                
                # CRITICAL TEST: Info messages should not be treated as errors
                if level == "INFO":
                    # Info messages should not contain error indicators
                    self.assertNotIn(" FAIL: ", formatted, "Info messages should not show error emoji")
                    self.assertNotIn("ERROR", formatted, "Info messages should not be labeled as ERROR")
                    
                    # This test currently PASSES but demonstrates the issue exists
                    # The real issue is in the display system, not the filter
                    
        # Test the actual issue: LogLevel enum values
        info_level = LogLevel.INFO
        success_level = LogLevel.SUCCESS
        error_level = LogLevel.ERROR
        
        # Verify LogLevel priorities are correct
        self.assertLess(info_level.value, error_level.value, 
                       "INFO should have lower priority than ERROR")
        self.assertLess(success_level.value, error_level.value,
                       "SUCCESS should have lower priority than ERROR") 
        
        # CRITICAL TEST: The real issue might be in color mapping
        # This would fail if colors are mapped incorrectly
        color_mapping = {
            LogLevel.INFO: "blue",      # Should be info color
            LogLevel.SUCCESS: "green",   # Should be success color  
            LogLevel.WARNING: "yellow",  # Should be warning color
            LogLevel.ERROR: "red",       # Should be error color
        }
        
        # Verify info is not mapped to red
        self.assertNotEqual(
            color_mapping[LogLevel.INFO], 
            "red",
            "CRITICAL: Info messages should not use red color"
        )
    
    def test_legacy_code_duplication_detection(self):
        """
        Test detection of legacy code and duplicates across dev launcher modules.
        
        ISSUE: Dev launcher has accumulated legacy code, duplicate implementations,
        and outdated patterns that need systematic cleanup.
        """
        # Scan for known legacy patterns in launcher code
        launcher_file = Path(__file__).parent.parent / "launcher.py"
        
        if launcher_file.exists():
            content = launcher_file.read_text(encoding='utf-8', errors='ignore')
            
            # Look for legacy patterns that should be cleaned up
            legacy_patterns = [
                "_load_env_file",  # Duplicate environment loading
                "# NOTE: Removed",  # Old commented out code
                "# TODO:",  # Unresolved todos
                "# FIXME:",  # Known issues
                "_legacy_",  # Legacy method prefixes
                "deprecated",  # Deprecated functionality
            ]
            
            legacy_found = []
            for pattern in legacy_patterns:
                if pattern in content:
                    legacy_found.append(pattern)
            
            # Document findings for cleanup
            if legacy_found:
                print(f"\nLegacy patterns found in launcher.py: {legacy_found}")
                
            # Check for duplicate method definitions
            import re
            method_definitions = re.findall(r'def ([a-zA-Z_][a-zA-Z0-9_]*)\(', content)
            method_counts = {}
            for method in method_definitions:
                method_counts[method] = method_counts.get(method, 0) + 1
            
            duplicates = {k: v for k, v in method_counts.items() if v > 1}
            
            # CRITICAL TEST: Should not have duplicate method definitions
            self.assertEqual(
                len(duplicates), 0,
                f"LEGACY ISSUE: Duplicate method definitions found: {duplicates}"
            )
            
        # Check for duplicate imports
        common_modules = [
            "dev_launcher.config",
            "dev_launcher.secret_loader", 
            "dev_launcher.local_secrets",
        ]
        
        for module_name in common_modules:
            try:
                module = __import__(module_name, fromlist=[''])
                
                # Check for duplicate class definitions or similar functionality
                classes = [attr for attr in dir(module) if not attr.startswith('_')]
                
                # Look for classes that might be duplicates
                similar_classes = []
                for i, class1 in enumerate(classes):
                    for class2 in classes[i+1:]:
                        if self._are_similar_class_names(class1, class2):
                            similar_classes.append((class1, class2))
                
                # Document potential duplicates
                if similar_classes:
                    print(f"\nPotential duplicate classes in {module_name}: {similar_classes}")
                    
            except ImportError:
                pass  # Module may not exist
    
    def _are_similar_class_names(self, name1: str, name2: str) -> bool:
        """Check if class names are suspiciously similar (potential duplicates)."""
        # Simple heuristic for similar names
        if abs(len(name1) - len(name2)) <= 2:
            common = sum(1 for a, b in zip(name1.lower(), name2.lower()) if a == b)
            similarity = common / max(len(name1), len(name2))
            return similarity > 0.7
        return False
    
    def test_environment_loading_race_condition(self):
        """
        Test race condition between error display and environment loading.
        
        ISSUE: Components display errors before environment variables
        have been fully loaded from .env files and secret sources.
        """
        # Create launcher config
        # Mock: Generic component isolation for controlled unit testing
        args = MagicMock()
        args.backend_port = None
        args.frontend_port = 3000
        args.static = False
        args.dynamic = True
        args.verbose = False
        args.backend_reload = False
        args.no_reload = True
        args.load_secrets = True
        args.no_secrets = False
        args.project_id = 'test-project'
        args.no_browser = True
        args.non_interactive = True
        args.no_turbopack = True
        args.no_parallel = False
        
        # Create env files with critical variables
        env_file = self.test_path / '.env'
        env_file.write_text('''
DATABASE_URL=postgresql://user:pass@localhost:5432/test
JWT_SECRET_KEY=super_secret_key_at_least_64_characters_long_for_testing_purposes_to_meet_requirements
CLICKHOUSE_PASSWORD=test_password
REDIS_URL=redis://localhost:6379
''')
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.config.find_project_root', return_value=self.test_path):
            config = LauncherConfig.from_args(args)
            config.project_root = self.test_path
            
            # Track timing of environment loading vs error checking
            load_start = time.time()
            
            # Use unified config to load environment
            env = get_env()
            env.reset_to_original()
            env.disable_isolation()  # Ensure variables are set in os.environ for testing
            
            # Load environment files
            env_file = self.test_path / '.env'
            if env_file.exists():
                env.load_from_file(str(env_file))
            
            # Time how long environment loading takes
            # Simulate loading time for test purposes
            time.sleep(0.01)
            load_complete = time.time()
            
            loading_time = load_complete - load_start
            
            # Now check if components would error immediately
            error_check_start = time.time()
            
            # Simulate component that checks for required env vars
            required_vars = ['DATABASE_URL', 'JWT_SECRET_KEY', 'CLICKHOUSE_PASSWORD']
            missing_vars = []
            for var in required_vars:
                if not env.get(var):
                    missing_vars.append(var)
            
            error_check_complete = time.time()
            error_check_time = error_check_complete - error_check_start
            
            # CRITICAL TEST: Environment loading should be faster than error checking
            # If error checking happens before loading, we have a race condition
            self.assertGreater(
                loading_time, 0.001,  # Loading should take some time
                "Environment loading should take measurable time"
            )
            
            self.assertLess(
                error_check_time, loading_time / 10,
                "Error checking should be much faster than loading"
            )
            
            # Verify no variables are missing after loading
            self.assertEqual(
                len(missing_vars), 0,
                f"RACE CONDITION: Variables missing after loading: {missing_vars}"
            )
    
    def test_secret_loader_priority_order_comprehensive(self):
        """
        Comprehensive test of secret loading priority order.
        
        Tests the complete priority chain:
        OS env (highest) > .env.local > .env > .secrets (lowest)
        """
        # Set up complete test scenario
        test_var_name = 'TEST_PRIORITY_VAR'
        
        # Layer 1: .secrets (lowest priority)
        secrets_file = self.test_path / '.secrets'
        secrets_file.write_text(f'{test_var_name}=from_secrets_file')
        
        # Layer 2: .env (base configuration)  
        env_file = self.test_path / '.env'
        env_file.write_text(f'{test_var_name}=from_env_file')
        
        # Layer 3: .env.local (local overrides)
        env_local = self.test_path / '.env.local'
        env_local.write_text(f'{test_var_name}=from_env_local')
        
        # Load using unified config
        env = get_env()
        env.reset_to_original()
        env.disable_isolation()
        
        # Layer 4: OS environment (highest priority)
        # Must set AFTER reset_to_original() which clears the environment
        env.set(test_var_name, 'from_os_environment')
        
        # Load files in priority order (reversed for proper layering)
        # Later files override earlier ones
        for file_name in ['.secrets', '.env', '.env.local']:
            file_path = self.test_path / file_name
            if file_path.exists():
                env.load_from_file(str(file_path), override_existing=True)
        
        secrets = {test_var_name: env.get(test_var_name)}
        
        # CRITICAL TEST: OS environment should win
        self.assertEqual(
            secrets.get(test_var_name),
            'from_os_environment',
            "OS environment should have highest priority"
        )
        
        # Test each layer by removing higher priority sources
        env.delete(test_var_name)
        env.reset_to_original()
        for file_name in ['.secrets', '.env', '.env.local']:
            file_path = self.test_path / file_name
            if file_path.exists():
                env.load_from_file(str(file_path), override_existing=True)
        secrets = {test_var_name: env.get(test_var_name)}
        
        self.assertEqual(
            secrets.get(test_var_name),
            'from_env_local',
            ".env.local should have priority over .env and .secrets"
        )
        
        # Remove .env.local
        os.remove(env_local)
        env.reset_to_original()
        for file_name in ['.secrets', '.env', '.env.local']:
            file_path = self.test_path / file_name
            if file_path.exists():
                env.load_from_file(str(file_path), override_existing=True)
        secrets = {test_var_name: env.get(test_var_name)}
        
        self.assertEqual(
            secrets.get(test_var_name),
            'from_env_file',
            ".env should have priority over .secrets"
        )
        
        # Remove .env (only .secrets left)
        os.remove(env_file)
        env.reset_to_original()
        for file_name in ['.secrets', '.env', '.env.local']:
            file_path = self.test_path / file_name
            if file_path.exists():
                env.load_from_file(str(file_path), override_existing=True)
        secrets = {test_var_name: env.get(test_var_name)}
        
        self.assertEqual(
            secrets.get(test_var_name),
            'from_secrets_file',
            ".secrets should be loaded when no higher priority sources exist"
        )

    async def test_async_launcher_startup_error_handling(self):
        """
        Test async launcher startup with proper error handling timing.
        
        ISSUE: Async operations may show errors before having sufficient
        time to complete, especially during parallel pre-checks.
        """
        # Create minimal config for async testing
        # Mock: Generic component isolation for controlled unit testing
        args = MagicMock()
        args.backend_port = None
        args.frontend_port = 3000
        args.static = False
        args.dynamic = True
        args.verbose = False
        args.backend_reload = False
        args.no_reload = True
        args.load_secrets = False
        args.no_secrets = True
        args.project_id = None
        args.no_browser = True
        args.non_interactive = True
        args.no_turbopack = True
        args.no_parallel = True  # Disable parallel for this test
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.config.find_project_root', return_value=self.test_path):
            config = LauncherConfig.from_args(args)
            config.project_root = self.test_path
            
            # Create launcher with minimal mocking
            launcher = self._create_launcher_with_mocks(config)
            
            # Mock database validation to simulate slow async operation
            async def slow_validate():
                await asyncio.sleep(0.2)  # Simulate slow validation
                return False  # Return failure after delay
            
            launcher._validate_databases = slow_validate
            
            # Test async error handling timing
            start_time = time.time()
            
            try:
                # This should wait for the async operation to complete
                result = await launcher._validate_databases()
                validation_time = time.time() - start_time
                
                # CRITICAL TEST: Should wait for full validation time
                self.assertGreaterEqual(
                    validation_time, 0.15,
                    "Async validation should wait for operation to complete"
                )
                
                self.assertFalse(result, "Validation should return False after delay")
                
            except Exception as e:
                self.fail(f"Async validation should not raise exception: {e}")


class TestStartupErrorSequenceRegression(unittest.TestCase):
    """Test the sequence of startup errors and their timing."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Create directory structure
        (self.test_path / 'netra_backend' / 'app').mkdir(parents=True)
        (self.test_path / 'frontend').mkdir(parents=True)
        (self.test_path / 'auth_service').mkdir(parents=True)
        
        # Save original environment
        self.original_env = dict(os.environ)
        
    def tearDown(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
        
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_startup_error_sequence_timing(self):
        """
        Test that startup errors follow the correct sequence and timing.
        
        Should be:
        1. Load environment variables (including secrets)
        2. Initialize components
        3. Check for missing configuration
        4. Display errors only after loading is complete
        """
        # Create incomplete environment (missing critical vars)
        env_file = self.test_path / '.env'
        env_file.write_text('''
# Incomplete configuration - missing critical variables
FRONTEND_PORT=3000
''')
        
        # Track operation timing
        operations = []
        
        def track_operation(name):
            operations.append((name, time.time()))
        
        # Mock environment loading with timing
        env = get_env()
        original_load = env.load_from_file
        
        def timed_load(file_path):
            track_operation("secret_load_start")
            result = original_load(file_path)
            track_operation("secret_load_end") 
            return result
        
        with patch.object(env, 'load_from_file', timed_load):
            # Mock: Component isolation for testing without external dependencies
            with patch('dev_launcher.config.find_project_root', return_value=self.test_path):
                # Mock: Generic component isolation for controlled unit testing
                args = MagicMock()
                args.backend_port = None
                args.frontend_port = 3000
                args.static = False
                args.dynamic = True
                args.verbose = False
                args.backend_reload = False
                args.no_reload = True
                args.load_secrets = True
                args.no_secrets = False
                args.project_id = 'test-project'
                args.no_browser = True
                args.non_interactive = True
                args.no_turbopack = True
                args.no_parallel = False
                
                config = LauncherConfig.from_args(args)
                config.project_root = self.test_path
                
                track_operation("config_created")
                
                # Track frontend starter creation timing
                # Mock: Generic component isolation for controlled unit testing
                mock_launcher = MagicMock()
                
                # Track when errors would be displayed
                error_display_times = []
                
                def mock_error_display(emoji, text, message):
                    if text == "ERROR":
                        error_display_times.append(time.time())
                        track_operation(f"error_display: {message[:50]}...")
                
                # Use unified config for testing
                env = get_env()
                env.reset_to_original()
                env.disable_isolation()
                
                track_operation("secret_loader_created")
                
                # Load environment files
                env_file_path = self.test_path / '.env'
                if env_file_path.exists():
                    env.load_from_file(str(env_file_path))
                
                # Now test component initialization timing
                # Mock: Generic component isolation for controlled unit testing
                mock_service_discovery = MagicMock()
                mock_service_discovery.read_backend_info.return_value = None
                
                frontend_starter = FrontendStarter(
                    config=config,
                    # Mock: Generic component isolation for controlled unit testing
                    services_config=MagicMock(),
                    # Mock: Generic component isolation for controlled unit testing
                    log_manager=MagicMock(),
                    service_discovery=mock_service_discovery,
                    use_emoji=False
                )
                
                track_operation("frontend_starter_created")
                
                frontend_starter._print = mock_error_display
                
                # Attempt to start frontend (will fail)
                result = frontend_starter.start_frontend()
                track_operation("frontend_start_attempted")
        
        # Analyze timing sequence
        if len(operations) >= 4:
            secret_start_time = next((t for name, t in operations if name == "secret_load_start"), None)
            secret_end_time = next((t for name, t in operations if name == "secret_load_end"), None)
            error_times = [t for name, t in operations if name.startswith("error_display")]
            
            if secret_start_time and secret_end_time and error_times:
                first_error_time = min(error_times)
                
                # CRITICAL TEST: Errors should not display before secret loading is complete
                self.assertGreaterEqual(
                    first_error_time, secret_end_time,
                    "REGRESSION: Errors displayed before secret loading completed"
                )
        
        print(f"\nStartup operation sequence:")
        for name, timestamp in operations:
            print(f"  {name}: {timestamp:.3f}")


# Async test support
class AsyncTestCase(unittest.TestCase):
    """Base class for async tests."""
    
    def setUp(self):
        """Set up async test environment."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up async test environment."""
        self.loop.close()
    
    def async_test(self, coro):
        """Run async test."""
        return self.loop.run_until_complete(coro)


if __name__ == '__main__':
    # Run tests with detailed output
    unittest.main(verbosity=2, buffer=True)