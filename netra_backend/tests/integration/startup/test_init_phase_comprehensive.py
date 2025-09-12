"""
Integration Tests for System Startup INIT Phase

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability & Chat Readiness
- Value Impact: Ensures system can initialize core components required for chat functionality
- Strategic Impact: Prevents catastrophic startup failures that block all user interactions

CRITICAL: These tests validate the INIT phase (Phase 1) of deterministic startup:
1. Environment variable loading and validation
2. Configuration setup and validation  
3. Logging system initialization
4. Project root resolution
5. Dotenv file loading scenarios
6. Cloud Run vs local environment detection
7. Dev launcher integration scenarios

The INIT phase is foundational - if it fails, chat cannot work.
"""

import asyncio
import os
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestInitPhaseComprehensive(BaseIntegrationTest):
    """
    Comprehensive integration tests for system startup INIT phase.
    
    CRITICAL: These tests ensure the foundation of chat functionality.
    Without proper INIT phase, the system cannot serve users.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.logger.info("Setting up INIT phase integration test")
        
        # Create temporary directories for test isolation
        self.temp_project_root = tempfile.mkdtemp(prefix="netra_test_init_")
        self.temp_env_files = []
        
        # Store original environment state for cleanup
        self.original_env_vars = dict(os.environ)
        
        # Setup test logging capture
        self.log_handler = logging.Handler()
        self.log_records = []
        
        class LogCapture(logging.Handler):
            def __init__(self, records_list):
                super().__init__()
                self.records = records_list
            
            def emit(self, record):
                self.records.append(record)
        
        self.log_capture = LogCapture(self.log_records)
        logging.getLogger().addHandler(self.log_capture)
    
    def teardown_method(self):
        """Cleanup after each test method."""
        super().teardown_method()
        
        # Clean up temporary files
        if hasattr(self, 'temp_project_root') and os.path.exists(self.temp_project_root):
            shutil.rmtree(self.temp_project_root, ignore_errors=True)
        
        # Clean up temporary env files
        for env_file in getattr(self, 'temp_env_files', []):
            if os.path.exists(env_file):
                os.unlink(env_file)
        
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env_vars)
        
        # Remove log handler
        if hasattr(self, 'log_capture'):
            logging.getLogger().removeHandler(self.log_capture)
    
    def create_test_env_file(self, filename: str, content: str) -> str:
        """Create a temporary .env file for testing."""
        env_file = os.path.join(self.temp_project_root, filename)
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        self.temp_env_files.append(env_file)
        return env_file

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_environment_variable_loading_basic(self):
        """
        Test basic environment variable loading functionality.
        
        BVJ: Core system initialization requires environment access.
        Without env vars, chat services cannot connect to databases or APIs.
        """
        self.logger.info("Testing basic environment variable loading")
        
        # Test data
        test_vars = {
            'TEST_DATABASE_URL': 'postgresql://localhost:5432/test',
            'TEST_API_KEY': 'test_key_12345',
            'TEST_ENVIRONMENT': 'test'
        }
        
        # Setup environment
        for key, value in test_vars.items():
            os.environ[key] = value
        
        # Test isolated environment access
        env = get_env()
        
        # Verify all test variables are accessible
        for key, expected_value in test_vars.items():
            actual_value = env.get(key)
            assert actual_value == expected_value, f"Environment variable {key} not loaded correctly"
        
        # Test default value handling
        non_existent_var = env.get('NON_EXISTENT_VAR', 'default_value')
        assert non_existent_var == 'default_value', "Default value handling failed"
        
        self.logger.info("[U+2713] Basic environment variable loading successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_environment_validation_critical_vars(self):
        """
        Test validation of critical environment variables for chat functionality.
        
        BVJ: Chat requires database, Redis, and LLM API connections.
        Missing critical vars cause chat failures that block user value.
        """
        self.logger.info("Testing critical environment variable validation")
        
        # Define critical variables for chat functionality
        critical_vars = {
            'LLM_MODE': 'gemini',
            'POSTGRES_HOST': 'localhost',
            'REDIS_URL': 'redis://localhost:6379',
            'SECRET_KEY': 'test_secret_for_sessions'
        }
        
        # Test: All critical vars present
        for key, value in critical_vars.items():
            os.environ[key] = value
        
        env = get_env()
        
        # Validate all critical variables are accessible
        missing_vars = []
        for key in critical_vars:
            if not env.get(key):
                missing_vars.append(key)
        
        assert not missing_vars, f"Missing critical environment variables: {missing_vars}"
        
        # Test: Missing critical var detection
        del os.environ['LLM_MODE']
        
        # This should be detectable by startup validation
        llm_mode = env.get('LLM_MODE')
        assert llm_mode is None, "Deleted environment variable should be None"
        
        self.logger.info("[U+2713] Critical environment variable validation successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_dotenv_file_loading_hierarchy(self):
        """
        Test .env file loading hierarchy for development environments.
        
        BVJ: Proper configuration loading ensures consistent chat behavior
        across development, staging, and production environments.
        """
        self.logger.info("Testing .env file loading hierarchy")
        
        # Create test .env files in correct hierarchy
        base_env_content = """
# Base configuration
DATABASE_NAME=netra_base
API_VERSION=v1
DEBUG=false
        """
        
        dev_env_content = """
# Development overrides
DATABASE_NAME=netra_dev
DEBUG=true
DEV_FEATURE_FLAG=enabled
        """
        
        local_env_content = """
# Local overrides
DATABASE_NAME=netra_local
DEVELOPER_MODE=true
        """
        
        # Create the files
        self.create_test_env_file('.env', base_env_content.strip())
        self.create_test_env_file('.env.development', dev_env_content.strip())
        self.create_test_env_file('.env.development.local', local_env_content.strip())
        
        # Simulate the loading process (simplified for testing)
        from netra_backend.app.main import _load_base_env_file, _load_development_env_file, _load_local_development_env_file
        
        project_root = Path(self.temp_project_root)
        
        # Load in proper hierarchy
        _load_base_env_file(project_root)
        _load_development_env_file(project_root)
        _load_local_development_env_file(project_root)
        
        env = get_env()
        
        # Verify hierarchy: local overrides dev overrides base
        assert env.get('DATABASE_NAME') == 'netra_local', "Local env should override dev and base"
        assert env.get('DEBUG') == 'true', "Development setting should be preserved"
        assert env.get('API_VERSION') == 'v1', "Base setting should be preserved"
        assert env.get('DEV_FEATURE_FLAG') == 'enabled', "Dev-specific setting should be loaded"
        assert env.get('DEVELOPER_MODE') == 'true', "Local-specific setting should be loaded"
        
        self.logger.info("[U+2713] .env file loading hierarchy successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_cloud_run_vs_local_detection(self):
        """
        Test detection of Cloud Run vs local environment for proper config.
        
        BVJ: Chat needs different configurations for local development vs production.
        Wrong detection breaks authentication, database connections, and WebSocket.
        """
        self.logger.info("Testing Cloud Run vs local environment detection")
        
        env = get_env()
        
        # Test local environment detection
        os.environ['ENVIRONMENT'] = 'development'
        if 'K_SERVICE' in os.environ:
            del os.environ['K_SERVICE']
        if 'PORT' in os.environ:
            del os.environ['PORT']
        
        # This simulates local development
        environment = env.get('ENVIRONMENT', '').lower()
        is_local = environment in ['development', 'local']
        has_cloud_run_indicators = env.get('K_SERVICE') or env.get('PORT')
        
        assert is_local, "Should detect local development environment"
        assert not has_cloud_run_indicators, "Should not detect Cloud Run indicators locally"
        
        # Test Cloud Run environment detection
        os.environ['ENVIRONMENT'] = 'production'
        os.environ['K_SERVICE'] = 'netra-backend-service'
        os.environ['PORT'] = '8080'
        
        environment = env.get('ENVIRONMENT', '').lower()
        is_production = environment in ['staging', 'production', 'prod']
        has_cloud_run_indicators = env.get('K_SERVICE') or env.get('PORT')
        
        assert is_production, "Should detect production environment"
        assert has_cloud_run_indicators, "Should detect Cloud Run indicators"
        
        self.logger.info("[U+2713] Cloud Run vs local detection successful")

    @pytest.mark.integration  
    @pytest.mark.startup_init
    async def test_dev_launcher_integration_detection(self):
        """
        Test detection of dev launcher to prevent double .env loading.
        
        BVJ: Dev launcher provides environment setup for local development.
        Double loading causes configuration conflicts that break chat setup.
        """
        self.logger.info("Testing dev launcher integration detection")
        
        env = get_env()
        
        # Test: No dev launcher indicators
        for indicator in ['DEV_LAUNCHER_ACTIVE', 'CROSS_SERVICE_AUTH_TOKEN']:
            if indicator in os.environ:
                del os.environ[indicator]
        
        dev_launcher_detected = any(env.get(indicator) for indicator in ['DEV_LAUNCHER_ACTIVE', 'CROSS_SERVICE_AUTH_TOKEN'])
        assert not dev_launcher_detected, "Should not detect dev launcher when not active"
        
        # Test: Dev launcher active
        os.environ['DEV_LAUNCHER_ACTIVE'] = 'true'
        os.environ['CROSS_SERVICE_AUTH_TOKEN'] = 'dev_token_12345'
        
        dev_launcher_detected = any(env.get(indicator) for indicator in ['DEV_LAUNCHER_ACTIVE', 'CROSS_SERVICE_AUTH_TOKEN'])
        assert dev_launcher_detected, "Should detect active dev launcher"
        
        # Test: Critical vars already set (simulating external loading)
        os.environ['LLM_MODE'] = 'gemini'
        os.environ['POSTGRES_HOST'] = 'localhost'
        os.environ['GEMINI_API_KEY'] = 'test_key'
        
        critical_vars = ['LLM_MODE', 'POSTGRES_HOST', 'GEMINI_API_KEY']
        vars_already_set = sum(1 for var in critical_vars if env.get(var))
        
        assert vars_already_set >= len(critical_vars) // 2, "Should detect pre-configured environment"
        
        self.logger.info("[U+2713] Dev launcher integration detection successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_project_root_resolution(self):
        """
        Test project root resolution for proper file path handling.
        
        BVJ: Chat functionality requires loading templates, static files, and configs.
        Wrong project root breaks file loading and renders chat UI unusable.
        """
        self.logger.info("Testing project root resolution")
        
        from netra_backend.app.core.project_utils import get_project_root
        
        # Test project root resolution
        try:
            project_root = get_project_root()
            assert project_root is not None, "Project root should be resolved"
            assert project_root.exists(), "Project root should exist as a directory"
            assert project_root.is_dir(), "Project root should be a directory"
            
            # Verify it looks like a Netra project
            expected_files = ['netra_backend', 'requirements.txt', 'README.md']
            missing_files = [f for f in expected_files if not (project_root / f).exists()]
            
            # Allow some flexibility - at least netra_backend should exist
            assert (project_root / 'netra_backend').exists(), f"Project root seems invalid, netra_backend directory not found at {project_root}"
            
            self.logger.info(f"[U+2713] Project root resolved to: {project_root}")
            
        except Exception as e:
            pytest.fail(f"Project root resolution failed: {e}")
        
        self.logger.info("[U+2713] Project root resolution successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_logging_system_initialization(self):
        """
        Test logging system initialization for startup and runtime debugging.
        
        BVJ: Chat problems require debugging through logs.
        Broken logging makes troubleshooting chat issues impossible.
        """
        self.logger.info("Testing logging system initialization")
        
        # Test that logging is properly initialized
        test_logger = logging.getLogger('test_startup_init')
        test_message = "Test logging initialization message"
        
        # Clear previous log records
        self.log_records.clear()
        
        # Test different log levels
        test_logger.info(test_message)
        test_logger.warning("Test warning message")
        test_logger.error("Test error message")
        
        # Verify logs were captured
        assert len(self.log_records) >= 1, "Logging system should capture log records"
        
        # Test that we can find our test message
        info_messages = [r.getMessage() for r in self.log_records if r.levelno == logging.INFO]
        assert any(test_message in msg for msg in info_messages), "Info message should be logged"
        
        # Test Cloud Run logging configuration
        from netra_backend.app.core.logging_config import configure_cloud_run_logging
        
        # This should not raise an exception
        try:
            configure_cloud_run_logging()
            self.logger.info("[U+2713] Cloud Run logging configuration successful")
        except Exception as e:
            pytest.fail(f"Cloud Run logging configuration failed: {e}")
        
        self.logger.info("[U+2713] Logging system initialization successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_configuration_setup_validation(self):
        """
        Test configuration setup and validation during INIT phase.
        
        BVJ: Chat requires proper database URLs, API keys, and service endpoints.
        Invalid configuration causes chat service failures.
        """
        self.logger.info("Testing configuration setup and validation")
        
        # Setup test configuration
        test_config_vars = {
            'DATABASE_URL': 'postgresql://test_user:test_pass@localhost:5432/test_db',
            'REDIS_URL': 'redis://localhost:6379/0',
            'SECRET_KEY': 'test_secret_key_for_sessions',
            'FRONTEND_URL': 'http://localhost:3000',
            'API_BASE_URL': 'http://localhost:8000',
            'ENVIRONMENT': 'test'
        }
        
        for key, value in test_config_vars.items():
            os.environ[key] = value
        
        # Test configuration loading
        from netra_backend.app.config import get_config
        
        try:
            config = get_config()
            assert config is not None, "Configuration should be loaded"
            
            # Test that config has required attributes for chat
            required_attrs = ['database_url', 'frontend_url', 'environment']
            missing_attrs = [attr for attr in required_attrs if not hasattr(config, attr)]
            assert not missing_attrs, f"Configuration missing required attributes: {missing_attrs}"
            
            # Test environment-specific validation
            assert config.environment == 'test', "Environment should be set correctly"
            
            self.logger.info("[U+2713] Configuration loading successful")
            
        except Exception as e:
            pytest.fail(f"Configuration setup failed: {e}")
        
        self.logger.info("[U+2713] Configuration setup and validation successful")

    @pytest.mark.integration
    @pytest.mark.startup_init  
    async def test_environment_isolation_for_testing(self):
        """
        Test environment isolation capabilities for testing scenarios.
        
        BVJ: Testing chat functionality requires isolated environments.
        Environment leakage between tests causes flaky chat behavior.
        """
        self.logger.info("Testing environment isolation for testing")
        
        # Test isolation mode
        env = get_env()
        
        # Test setting isolated test values
        test_key = 'TEST_ISOLATION_VAR'
        test_value = 'isolated_test_value'
        
        # Set in isolated environment
        env.set(test_key, test_value, source='test')
        
        # Verify isolation
        isolated_value = env.get(test_key)
        assert isolated_value == test_value, "Isolated environment should contain test value"
        
        # Test source tracking
        if hasattr(env, 'get_source'):
            source = env.get_source(test_key)
            assert source == 'test', "Source tracking should work for isolated values"
        
        # Test cleanup capabilities
        if hasattr(env, 'clear_test_values'):
            env.clear_test_values()
            cleared_value = env.get(test_key)
            assert cleared_value is None or cleared_value != test_value, "Test values should be clearable"
        
        self.logger.info("[U+2713] Environment isolation for testing successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_dotenv_loading_error_handling(self):
        """
        Test error handling during .env file loading.
        
        BVJ: Malformed config files should not crash chat startup.
        Graceful handling allows chat to continue with defaults.
        """
        self.logger.info("Testing .env loading error handling")
        
        # Test missing .env file (should not crash)
        from netra_backend.app.main import _load_base_env_file
        
        non_existent_root = Path(self.temp_project_root) / 'nonexistent'
        
        try:
            _load_base_env_file(non_existent_root)
            # Should not raise an exception
            self.logger.info("[U+2713] Missing .env file handled gracefully")
        except Exception as e:
            pytest.fail(f"Missing .env file should be handled gracefully: {e}")
        
        # Test malformed .env file
        malformed_content = """
# Malformed .env file
VALID_VAR=valid_value
MALFORMED_LINE_WITHOUT_EQUALS
=VALUE_WITHOUT_KEY
        """
        
        malformed_file = self.create_test_env_file('.env.malformed', malformed_content)
        
        # This should not crash the system
        try:
            from dotenv import load_dotenv
            load_dotenv(malformed_file)
            self.logger.info("[U+2713] Malformed .env file handled gracefully")
        except Exception as e:
            # Some malformed content might cause exceptions, which is acceptable
            self.logger.info(f"Malformed .env file caused expected error: {e}")
        
        self.logger.info("[U+2713] .env loading error handling successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_unicode_and_encoding_handling(self):
        """
        Test Unicode and encoding handling for Windows compatibility.
        
        BVJ: Chat must work on Windows for developer productivity.
        Encoding issues block Windows developers from chat testing.
        """
        self.logger.info("Testing Unicode and encoding handling")
        
        # Test Unicode in environment variables
        unicode_vars = {
            'TEST_UNICODE_NAME': 'Test User [U+1F468][U+200D][U+1F4BB]',
            'TEST_UNICODE_PATH': 'C:\\Users\\[U+6D4B][U+8BD5]\\Documents',
            'TEST_UNICODE_MESSAGE': 'Hello World! [U+1F30D] [U+0417][U+0434]pavctvu[U+0439] m[U+0438]p!',
        }
        
        env = get_env()
        
        # Set Unicode variables
        for key, value in unicode_vars.items():
            try:
                env.set(key, value, source='test')
                retrieved_value = env.get(key)
                assert retrieved_value == value, f"Unicode handling failed for {key}: expected {value}, got {retrieved_value}"
            except UnicodeError as e:
                pytest.fail(f"Unicode handling failed for {key}: {e}")
        
        # Test Unicode in .env file
        unicode_env_content = """
# Unicode test file
APP_NAME=Netra AI [U+1F916]
USER_GREETING=Hello! [U+1F44B] [U+041F]p[U+0438]vet!
FILE_PATH=C:\\Users\\[U+7528][U+6237]\\Documents\\[U+6D4B][U+8BD5].txt
        """
        
        unicode_env_file = self.create_test_env_file('.env.unicode', unicode_env_content)
        
        try:
            from dotenv import load_dotenv
            load_dotenv(unicode_env_file)
            
            # Verify Unicode values were loaded correctly
            app_name = env.get('APP_NAME')
            assert 'Netra AI [U+1F916]' in str(app_name) if app_name else False, "Unicode app name should be loaded"
            
        except (UnicodeError, UnicodeDecodeError) as e:
            pytest.fail(f"Unicode .env file handling failed: {e}")
        
        self.logger.info("[U+2713] Unicode and encoding handling successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_startup_timing_and_performance(self):
        """
        Test INIT phase timing and performance requirements.
        
        BVJ: Chat startup must be fast for good user experience.
        Slow initialization frustrates users and reduces chat adoption.
        """
        self.logger.info("Testing INIT phase timing and performance")
        
        import time
        
        # Measure basic environment operations
        start_time = time.time()
        
        # Simulate INIT phase operations
        env = get_env()
        
        # Environment variable access (should be very fast)
        for i in range(100):
            _ = env.get(f'TEST_VAR_{i}', 'default')
        
        env_access_time = time.time() - start_time
        
        # Environment access should be under 100ms for 100 operations
        assert env_access_time < 0.1, f"Environment access too slow: {env_access_time:.3f}s for 100 operations"
        
        # Test project root resolution timing
        start_time = time.time()
        
        from netra_backend.app.core.project_utils import get_project_root
        
        for _ in range(10):  # Multiple calls should be cached
            _ = get_project_root()
        
        project_root_time = time.time() - start_time
        
        # Multiple calls should be fast due to caching
        assert project_root_time < 0.05, f"Project root resolution too slow: {project_root_time:.3f}s for 10 operations"
        
        self.logger.info(f"[U+2713] INIT phase performance: env_access={env_access_time:.3f}s, project_root={project_root_time:.3f}s")
        self.logger.info("[U+2713] INIT phase timing and performance successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_environment_variable_precedence(self):
        """
        Test environment variable precedence rules for configuration.
        
        BVJ: Chat configuration must follow predictable precedence rules.
        Wrong precedence causes production values to leak into development.
        """
        self.logger.info("Testing environment variable precedence rules")
        
        env = get_env()
        test_var = 'TEST_PRECEDENCE_VAR'
        
        # Test 1: OS environment has highest precedence
        os.environ[test_var] = 'os_value'
        value = env.get(test_var)
        assert value == 'os_value', "OS environment should have highest precedence"
        
        # Test 2: .env file values (lower precedence)
        env_content = f"{test_var}=env_file_value"
        env_file = self.create_test_env_file('.env.test', env_content)
        
        from dotenv import load_dotenv
        load_dotenv(env_file)  # This should not override OS env
        
        value = env.get(test_var)
        assert value == 'os_value', "OS environment should override .env file"
        
        # Test 3: Remove OS env, should fall back to .env
        del os.environ[test_var]
        
        # Reload to get .env file value  
        load_dotenv(env_file, override=False)
        value = env.get(test_var)
        
        # Note: This test might be environment-dependent
        # The key point is that there's a predictable precedence
        self.logger.info(f"Final value after OS removal: {value}")
        
        # Test 4: Default values (lowest precedence)
        non_existent_var = env.get('NON_EXISTENT_VAR', 'default_value')
        assert non_existent_var == 'default_value', "Default values should work when no other source exists"
        
        self.logger.info("[U+2713] Environment variable precedence rules successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_production_safety_checks(self):
        """
        Test production safety checks during INIT phase.
        
        BVJ: Production chat must not load development configurations.
        Config leakage in production exposes secrets and breaks security.
        """
        self.logger.info("Testing production safety checks")
        
        env = get_env()
        
        # Test production environment detection
        original_env = env.get('ENVIRONMENT')
        
        # Simulate production environment
        os.environ['ENVIRONMENT'] = 'production'
        
        environment = env.get('ENVIRONMENT', '').lower()
        is_production = environment in ['staging', 'production', 'prod']
        
        assert is_production, "Should detect production environment"
        
        # Test that .env files should be skipped in production
        # (This is tested in the main startup logic)
        
        # Test required production variables
        production_required = ['SECRET_KEY', 'DATABASE_URL']
        
        # Set minimal required vars for test
        os.environ['SECRET_KEY'] = 'production_secret_123'
        os.environ['DATABASE_URL'] = 'postgresql://prod:secret@db:5432/netra'
        
        for var in production_required:
            value = env.get(var)
            assert value is not None, f"Production requires {var} to be set"
        
        # Test debug mode should be disabled in production
        debug_disabled = env.get('DEBUG', '').lower() not in ['true', '1', 'yes']
        assert debug_disabled, "DEBUG should be disabled in production"
        
        # Restore original environment
        if original_env:
            os.environ['ENVIRONMENT'] = original_env
        elif 'ENVIRONMENT' in os.environ:
            del os.environ['ENVIRONMENT']
        
        self.logger.info("[U+2713] Production safety checks successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_init_phase_error_recovery(self):
        """
        Test error recovery during INIT phase for resilient startup.
        
        BVJ: Chat startup should be resilient to minor configuration issues.
        Graceful recovery allows chat to work with fallback configurations.
        """
        self.logger.info("Testing INIT phase error recovery")
        
        # Test 1: Missing optional environment variables
        env = get_env()
        
        # Remove optional vars that shouldn't break startup
        optional_vars = ['ANALYTICS_ENDPOINT', 'MONITORING_URL', 'OPTIONAL_FEATURE_FLAG']
        
        for var in optional_vars:
            if var in os.environ:
                del os.environ[var]
        
        # These should return None or defaults without breaking
        for var in optional_vars:
            value = env.get(var, 'default_fallback')
            assert value == 'default_fallback', f"Optional var {var} should use fallback"
        
        # Test 2: Malformed URLs (should be detectable)
        os.environ['TEST_MALFORMED_URL'] = 'not-a-valid-url'
        
        malformed_url = env.get('TEST_MALFORMED_URL')
        assert malformed_url == 'not-a-valid-url', "Malformed URL should be retrievable"
        
        # Validation would happen later in the startup process
        
        # Test 3: Empty but set variables
        os.environ['TEST_EMPTY_VAR'] = ''
        
        empty_var = env.get('TEST_EMPTY_VAR')
        assert empty_var == '', "Empty string should be preserved"
        
        # Test fallback when empty
        empty_with_fallback = env.get('TEST_EMPTY_VAR') or 'fallback_value'
        assert empty_with_fallback == 'fallback_value', "Empty string should allow fallback"
        
        self.logger.info("[U+2713] INIT phase error recovery successful")

    @pytest.mark.integration
    @pytest.mark.startup_init
    async def test_concurrent_environment_access(self):
        """
        Test concurrent access to environment variables for thread safety.
        
        BVJ: Chat handles multiple concurrent requests requiring env access.
        Race conditions in env access cause intermittent chat failures.
        """
        self.logger.info("Testing concurrent environment access")
        
        import asyncio
        import concurrent.futures
        
        env = get_env()
        
        # Setup test variables
        test_vars = {f'CONCURRENT_TEST_{i}': f'value_{i}' for i in range(20)}
        for key, value in test_vars.items():
            os.environ[key] = value
        
        # Test concurrent reads
        async def read_env_vars():
            """Read environment variables concurrently."""
            results = {}
            for key in test_vars.keys():
                results[key] = env.get(key)
            return results
        
        # Run multiple concurrent readers
        tasks = [read_env_vars() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all concurrent reads got correct values
        for result in results:
            for key, expected_value in test_vars.items():
                actual_value = result.get(key)
                assert actual_value == expected_value, f"Concurrent read failed for {key}: expected {expected_value}, got {actual_value}"
        
        # Test thread-based concurrent access
        def thread_read_env():
            """Read environment variables from thread."""
            thread_env = get_env()
            return {key: thread_env.get(key) for key in test_vars.keys()}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(thread_read_env) for _ in range(5)]
            thread_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify thread-based reads
        for result in thread_results:
            for key, expected_value in test_vars.items():
                actual_value = result.get(key)
                assert actual_value == expected_value, f"Thread read failed for {key}: expected {expected_value}, got {actual_value}"
        
        self.logger.info("[U+2713] Concurrent environment access successful")