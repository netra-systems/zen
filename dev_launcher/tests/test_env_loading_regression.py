"""
Tests for dev launcher environment loading regression.

CRITICAL BUG: Dev launcher has regression in loading environment variables with wrong priority order.
This test suite reproduces the issues and verifies fixes.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dev_launcher.config import LauncherConfig
from dev_launcher.launcher import DevLauncher
from dev_launcher.local_secrets import LocalSecretManager
from dev_launcher.secret_loader import SecretLoader


class TestEnvironmentLoadingRegression(unittest.TestCase):
    """Test suite for environment loading regression in dev launcher."""
    
    def _create_launcher_with_mocks(self, config):
        """Helper to create launcher with all necessary mocks."""
        with patch('dev_launcher.launcher.setup_logging'):
            with patch('dev_launcher.launcher.check_emoji_support', return_value=False):
                with patch('dev_launcher.launcher.HealthMonitor'):
                    with patch('dev_launcher.launcher.ProcessManager'):
                        with patch('dev_launcher.launcher.LogManager'):
                            with patch('dev_launcher.launcher.ServiceDiscovery'):
                                with patch('dev_launcher.launcher.EnvironmentChecker'):
                                    with patch('dev_launcher.launcher.ServiceStartupCoordinator'):
                                        with patch('dev_launcher.launcher.SummaryDisplay'):
                                            with patch('dev_launcher.launcher.StartupOptimizer'):
                                                with patch('dev_launcher.launcher.CacheManager'):
                                                    return DevLauncher(config)
    
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
        self.original_env = dict(os.environ)
        
        # Clear test-specific env vars
        for key in list(os.environ.keys()):
            if key.startswith('TEST_'):
                del os.environ[key]
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
        
        # Clean up test files
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_env_loading_priority_order_regression(self):
        """
        Test that demonstrates the wrong priority order in env loading.
        
        EXPECTED: System env > .env.local > .env > .secrets
        ACTUAL BUG: .env overrides system env due to wrong loading order
        """
        # Set system environment variable (should have highest priority)
        os.environ['TEST_VAR'] = 'system_value'
        os.environ['TEST_ONLY_SYSTEM'] = 'only_in_system'
        
        # Create .env file (should have lower priority)
        env_file = self.test_path / '.env'
        env_file.write_text('''
TEST_VAR=env_file_value
TEST_ONLY_ENV=only_in_env
''')
        
        # Create .env.local file (should have medium priority)
        env_local = self.test_path / '.env.local'
        env_local.write_text('''
TEST_VAR=env_local_value
TEST_ONLY_LOCAL=only_in_local
''')
        
        # Create .secrets file (should have lowest priority)
        secrets_file = self.test_path / '.secrets'
        secrets_file.write_text('''
TEST_VAR=secrets_value
TEST_ONLY_SECRETS=only_in_secrets
''')
        
        # Mock the project structure
        with patch('dev_launcher.config.find_project_root', return_value=self.test_path):
            # Create launcher config
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
            args.no_parallel = False
            
            config = LauncherConfig.from_args(args)
            config.project_root = self.test_path
            
            # Create launcher (this will call _load_env_file)
            launcher = self._create_launcher_with_mocks(config)
            
            # CRITICAL TEST: System env should have priority over .env file
            self.assertEqual(
                os.environ.get('TEST_VAR'), 
                'system_value',  # Should be system value
                "REGRESSION: .env file overrides system environment variable!"
            )
            
            # Test that each source's unique variables are loaded
            self.assertEqual(
                os.environ.get('TEST_ONLY_SYSTEM'),
                'only_in_system',
                "System-only variable not preserved"
            )
            
            # Since .env is loaded but doesn't override system, its unique vars should exist
            self.assertEqual(
                os.environ.get('TEST_ONLY_ENV'),
                'only_in_env',
                ".env unique variable not loaded"
            )
    
    def test_duplicate_loading_issue(self):
        """
        Test that demonstrates duplicate loading of env files.
        
        ISSUE: Both _load_env_file and SecretLoader load the same files,
        causing confusion and potential overrides.
        """
        # Create test env file with counter variable
        env_file = self.test_path / '.env'
        env_file.write_text('TEST_LOAD_COUNT=loaded_once')
        
        load_count = []
        
        # Patch file reading to track how many times files are loaded
        original_open = open
        def tracked_open(file, *args, **kwargs):
            file_path = Path(file) if not isinstance(file, Path) else file
            if file_path.name in ['.env', '.env.local', '.secrets']:
                load_count.append(file_path.name)
            return original_open(file, *args, **kwargs)
        
        with patch('builtins.open', tracked_open):
            with patch('dev_launcher.config.find_project_root', return_value=self.test_path):
                # Create launcher config
                args = MagicMock()
                args.backend_port = None
                args.frontend_port = 3000
                args.static = False
                args.dynamic = True
                args.verbose = False
                args.backend_reload = False
                args.no_reload = True
                args.load_secrets = True  # Enable secret loading
                args.no_secrets = False
                args.project_id = 'test-project'
                args.no_browser = True
                args.non_interactive = True
                args.no_turbopack = True
                args.no_parallel = False
                
                config = LauncherConfig.from_args(args)
                config.project_root = self.test_path
                
                # Create launcher and load secrets
                launcher = self._create_launcher_with_mocks(config)
                
                # Now trigger secret loading
                launcher.secret_loader.load_all_secrets()
        
        # Check how many times .env was loaded
        env_load_count = load_count.count('.env')
        self.assertGreaterEqual(
            env_load_count,
            2,
            f"DUPLICATE LOADING: .env file loaded {env_load_count} times (once by launcher, once by SecretLoader)"
        )
    
    def test_env_local_priority_over_env(self):
        """
        Test that .env.local has priority over .env file.
        
        This is the correct behavior per SecretLoader, but may conflict
        with launcher's _load_env_file which doesn't handle .env.local.
        """
        # Create .env file
        env_file = self.test_path / '.env'
        env_file.write_text('TEST_PRIORITY=from_env')
        
        # Create .env.local file (should override .env)
        env_local = self.test_path / '.env.local'
        env_local.write_text('TEST_PRIORITY=from_env_local')
        
        # Test with SecretLoader directly
        secret_loader = SecretLoader(
            project_root=self.test_path,
            verbose=True,
            load_secrets=False
        )
        
        # Load secrets
        secret_loader.load_all_secrets()
        
        # .env.local should have priority over .env
        self.assertEqual(
            os.environ.get('TEST_PRIORITY'),
            'from_env_local',
            ".env.local should have priority over .env"
        )
    
    def test_secrets_file_lowest_priority(self):
        """
        Test that .secrets file has the lowest priority.
        
        The launcher's _load_env_file loads .secrets, but it should
        have the lowest priority of all sources.
        """
        # Set all sources with the same variable
        os.environ['TEST_PRECEDENCE'] = 'from_system'
        
        env_file = self.test_path / '.env'
        env_file.write_text('TEST_PRECEDENCE=from_env')
        
        secrets_file = self.test_path / '.secrets'
        secrets_file.write_text('TEST_PRECEDENCE=from_secrets')
        
        # Load through LocalSecretManager (correct implementation)
        local_manager = LocalSecretManager(self.test_path, verbose=True)
        secrets, _ = local_manager.load_secrets_with_fallback(set(['TEST_PRECEDENCE']))
        
        # System should win
        self.assertEqual(
            secrets.get('TEST_PRECEDENCE'),
            'from_system',
            "System environment should have highest priority"
        )
        
        # Now test with only .env and .secrets (no system env)
        del os.environ['TEST_PRECEDENCE']
        secrets, _ = local_manager.load_secrets_with_fallback(set(['TEST_PRECEDENCE']))
        
        self.assertEqual(
            secrets.get('TEST_PRECEDENCE'),
            'from_env',
            ".env should have priority over .secrets"
        )
    
    def test_loading_order_affects_interpolation(self):
        """
        Test that wrong loading order affects variable interpolation.
        
        If files are loaded in wrong order, ${VAR} references may not
        resolve correctly.
        """
        # Create .env with base URL
        env_file = self.test_path / '.env'
        env_file.write_text('''
BASE_URL=http://localhost:8000
API_URL=${BASE_URL}/api
''')
        
        # Create .env.local that overrides base URL
        env_local = self.test_path / '.env.local'
        env_local.write_text('BASE_URL=http://localhost:9000')
        
        # Load with correct implementation
        local_manager = LocalSecretManager(self.test_path, verbose=True)
        secrets, _ = local_manager.load_secrets_with_fallback(set(['BASE_URL', 'API_URL']))
        
        # API_URL should use the overridden BASE_URL from .env.local
        self.assertEqual(
            secrets.get('BASE_URL'),
            'http://localhost:9000',
            "BASE_URL should be from .env.local"
        )
        
        self.assertEqual(
            secrets.get('API_URL'),
            'http://localhost:9000/api',
            "API_URL interpolation should use .env.local's BASE_URL"
        )
    
    def test_system_env_not_overwritten(self):
        """
        Test that system environment variables are never overwritten.
        
        This is a critical security feature - system env should always
        have the highest priority.
        """
        # Set critical system variables
        os.environ['JWT_SECRET_KEY'] = 'system_secret'
        os.environ['DATABASE_URL'] = 'system_database'
        
        # Try to override in files (should fail)
        env_file = self.test_path / '.env'
        env_file.write_text('''
JWT_SECRET_KEY=file_secret_should_not_load
DATABASE_URL=file_database_should_not_load
''')
        
        secrets_file = self.test_path / '.secrets'
        secrets_file.write_text('''
JWT_SECRET_KEY=secrets_secret_should_not_load
DATABASE_URL=secrets_database_should_not_load
''')
        
        # Load through launcher
        with patch('dev_launcher.config.find_project_root', return_value=self.test_path):
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
            args.no_parallel = False
            
            config = LauncherConfig.from_args(args)
            config.project_root = self.test_path
            
            launcher = self._create_launcher_with_mocks(config)
        
        # System values should be preserved
        self.assertEqual(
            os.environ.get('JWT_SECRET_KEY'),
            'system_secret',
            "CRITICAL: System JWT_SECRET_KEY was overwritten!"
        )
        
        self.assertEqual(
            os.environ.get('DATABASE_URL'),
            'system_database',
            "CRITICAL: System DATABASE_URL was overwritten!"
        )


if __name__ == '__main__':
    # Run with verbose output to see all issues
    unittest.main(verbosity=2)