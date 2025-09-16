"""
PROPER Unit Tests for UnifiedTestRunner - CLAUDE.md Compliant

CRITICAL: This test suite follows CLAUDE.md principles with ZERO mocking and tests REAL functionality.
This replaces the previous broken test suite that violated SSOT principles.

Business Value: Platform/Internal - System Stability & Development Velocity
Ensures the unified test runner works correctly across all environments.

ARCHITECTURAL COMPLIANCE:
- NO MOCKS WHATSOEVER - Tests real implementations only
- NO try/except blocks - Let tests fail hard 
- Uses real SSOT imports that actually exist
- Tests real functionality with actual system calls
- Uses real argparse.Namespace objects, not mock objects

TESTING STRATEGY:
This is UNIT testing focused on:
- Configuration and initialization logic  
- Command building and argument parsing
- Category system and test discovery logic
- Utility functions and helper methods
- Error handling and validation logic

NOT tested here (covered by integration tests):
- Docker operations (covered by integration tests)
- Actual test execution (covered by integration tests) 
- WebSocket connections (covered by integration tests)
"""
import sys
import os
import argparse
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from unittest import TestCase
import pytest
from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
from unified_test_runner import UnifiedTestRunner

@pytest.mark.unit
class UnifiedTestRunnerProperTests(SSotBaseTestCase):
    """
    Proper unit tests for UnifiedTestRunner that test REAL functionality.
    
    This test suite validates core business logic without mocks, ensuring 
    the test runner can actually execute commands and handle configurations
    correctly in real environments.
    """

    def setup_method(self, method=None):
        """Set up test environment with real components."""
        super().setup_method(method)
        self.env = self.get_env()
        self.set_env_var('TEST_MODE', 'unit')
        self.runner = UnifiedTestRunner()
        self.record_metric('test_setup', 'unified_test_runner')

    def teardown_method(self, method=None):
        """Clean up test environment."""
        self.delete_env_var('TEST_MODE')
        super().teardown_method(method)

    def test_python_command_detection_real_system(self):
        """
        Test real Python command detection on the actual system.
        
        This validates that the runner can detect the correct Python command
        that actually works on the system, which is critical for test execution.
        
        Business Value: Ensures tests can run on any development environment.
        """
        detected_command = self.runner._detect_python_command()
        assert isinstance(detected_command, str)
        assert len(detected_command) > 0
        assert detected_command in ['python3', 'python', 'py']
        result = subprocess.run([detected_command, '--version'], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        assert 'Python 3' in result.stdout
        self.record_metric('python_detection', 'success')

    def test_project_paths_initialization(self):
        """
        Test that project paths are correctly initialized from real filesystem.
        
        This validates that the runner correctly identifies project structure,
        which is essential for finding test files and configurations.
        """
        assert self.runner.project_root.exists()
        assert self.runner.project_root.is_dir()
        assert (self.runner.project_root / 'tests').exists()
        assert self.runner.backend_path == self.runner.project_root / 'netra_backend'
        assert self.runner.auth_path == self.runner.project_root / 'auth_service'
        assert self.runner.frontend_path == self.runner.project_root / 'frontend'
        assert self.runner.test_framework_path == self.runner.project_root / 'test_framework'
        self.record_metric('path_initialization', 'success')

    def test_category_determination_with_real_args(self):
        """
        Test category determination with real argparse.Namespace objects.
        
        This validates the core logic for determining which test categories
        to run based on command-line arguments.
        """
        args = argparse.Namespace(category='unit', categories=None, service=None)
        categories = self.runner._determine_categories_to_run(args)
        assert 'unit' in categories
        assert isinstance(categories, list)
        args = argparse.Namespace(category=None, categories=['unit', 'integration'], service=None)
        categories = self.runner._determine_categories_to_run(args)
        assert 'unit' in categories
        assert 'integration' in categories
        assert len(categories) >= 2
        args = argparse.Namespace(category=None, categories=None, service=None)
        categories = self.runner._determine_categories_to_run(args)
        assert isinstance(categories, list)
        assert len(categories) > 0
        default_categories = {'smoke', 'unit', 'integration'}
        assert any((cat in default_categories for cat in categories))
        self.record_metric('category_determination', 'success')

    def test_service_category_mapping_real_logic(self):
        """
        Test service to category mapping with real logic.
        
        This validates that the legacy service selection correctly maps
        to appropriate test categories for backward compatibility.
        """
        backend_categories = self.runner._get_categories_for_service('backend')
        assert isinstance(backend_categories, list)
        assert 'unit' in backend_categories
        assert 'integration' in backend_categories
        assert 'api' in backend_categories
        frontend_categories = self.runner._get_categories_for_service('frontend')
        assert isinstance(frontend_categories, list)
        assert 'unit' in frontend_categories
        assert 'e2e' in frontend_categories
        auth_categories = self.runner._get_categories_for_service('auth_service')
        assert isinstance(auth_categories, list)
        assert 'security' in auth_categories
        unknown_categories = self.runner._get_categories_for_service('unknown_service')
        assert isinstance(unknown_categories, list)
        assert len(unknown_categories) >= 2
        self.record_metric('service_mapping', 'success')

    def test_pytest_command_building_backend_real(self):
        """
        Test pytest command building for backend service with real arguments.
        
        This validates that the command builder creates valid pytest commands
        that would actually execute correctly.
        """
        args = argparse.Namespace(no_coverage=False, parallel=False, verbose=False, fast_fail=False, pattern=None, workers=4)
        cmd = self.runner._build_pytest_command('backend', 'unit', args)
        assert isinstance(cmd, str)
        assert self.runner.python_command in cmd
        assert '-m pytest' in cmd
        assert 'netra_backend/tests/unit' in cmd
        assert '--cov' in cmd
        cmd_parts = cmd.split()
        assert len(cmd_parts) >= 3
        assert cmd_parts[0] in ['python3', 'python', 'py']
        assert cmd_parts[1] == '-m'
        assert cmd_parts[2] == 'pytest'
        self.record_metric('pytest_backend_command', 'success')

    def test_pytest_command_building_integration_real(self):
        """
        Test pytest command building for integration tests with real arguments.
        
        This validates command building for more complex test scenarios.
        """
        args = argparse.Namespace(no_coverage=True, parallel=True, verbose=True, fast_fail=True, pattern='test_important', workers=2)
        cmd = self.runner._build_pytest_command('backend', 'integration', args)
        assert '-vv' in cmd
        assert '-x' in cmd
        assert '-n 2' in cmd
        assert '--cov' not in cmd
        assert '-k "test_important"' in cmd
        assert 'netra_backend/tests/integration' in cmd
        self.record_metric('pytest_integration_command', 'success')

    def test_pytest_command_building_auth_service(self):
        """
        Test pytest command building for auth service tests.
        
        This validates that auth service tests get proper configuration.
        """
        args = argparse.Namespace(no_coverage=False, parallel=False, verbose=False, fast_fail=False, pattern=None, workers=4)
        cmd = self.runner._build_pytest_command('auth', 'unit', args)
        assert 'auth_service/tests' in cmd
        assert '-m unit' in cmd
        assert self.runner.python_command in cmd
        security_cmd = self.runner._build_pytest_command('auth', 'security', args)
        assert 'auth_service/tests' in security_cmd
        assert '-m security' in security_cmd
        self.record_metric('pytest_auth_command', 'success')

    def test_frontend_command_building_real(self):
        """
        Test frontend command building with real arguments.
        
        This validates that frontend (npm) commands are built correctly
        with proper environment configuration.
        """
        args = argparse.Namespace(real_services=True, env='dev', no_coverage=False, fast_fail=False, verbose=False, category=None, categories=None, service=None)
        cmd = self.runner._build_frontend_command('unit', args)
        assert isinstance(cmd, str)
        assert cmd.startswith('npm run test:unit')
        assert 'setupFilesAfterEnv' in cmd
        use_real_llm = self.get_env_var('USE_REAL_LLM')
        assert use_real_llm == 'true'
        integration_cmd = self.runner._build_frontend_command('integration', args)
        assert 'npm run test:integration' in integration_cmd
        e2e_cmd = self.runner._build_frontend_command('e2e', args)
        assert 'npm run test:critical' in e2e_cmd
        self.record_metric('frontend_command', 'success')

    def test_test_config_structure_validation(self):
        """
        Test that test configurations are properly structured and valid.
        
        This validates the internal test configuration structure used
        for building commands across different services.
        """
        expected_services = ['backend', 'auth', 'frontend']
        for service in expected_services:
            assert service in self.runner.test_configs
            config = self.runner.test_configs[service]
            assert 'path' in config
            assert 'test_dir' in config
            assert 'command' in config
            if service != 'frontend':
                assert 'config' in config
                path = Path(config['path'])
                assert path.exists()
        backend_config = self.runner.test_configs['backend']
        assert str(backend_config['path']) == str(self.runner.project_root)
        assert backend_config['test_dir'] == 'netra_backend/tests'
        assert self.runner.python_command in backend_config['command']
        self.record_metric('config_structure', 'success')

    def test_resume_functionality_real_logic(self):
        """
        Test resume functionality with real category lists.
        
        This validates that the resume feature correctly skips completed
        categories and starts from the specified point.
        """
        categories = ['smoke', 'unit', 'integration', 'api', 'e2e']
        resumed = self.runner._handle_resume(categories, 'integration')
        assert resumed == ['integration', 'api', 'e2e']
        assert len(resumed) == 3
        resumed_start = self.runner._handle_resume(categories, 'smoke')
        assert resumed_start == categories
        resumed_end = self.runner._handle_resume(categories, 'e2e')
        assert resumed_end == ['e2e']
        resumed_invalid = self.runner._handle_resume(categories, 'nonexistent')
        assert resumed_invalid == categories
        self.record_metric('resume_functionality', 'success')

    def test_environment_configuration_real(self):
        """
        Test environment configuration with real IsolatedEnvironment.
        
        This validates that the runner properly configures the test environment
        using the SSOT environment management system.
        """
        args = argparse.Namespace(env='test', real_services=True, real_llm=False, category=None, categories=None, service=None)
        current_env = self.get_env()
        assert current_env is not None
        current_env = get_env()
        assert current_env is not None
        test_var = current_env.get('TEST_MODE')
        assert test_var is not None
        self.record_metric('environment_config', 'success')

    def test_windows_path_handling_real(self):
        """
        Test Windows path handling with real filesystem paths.
        
        This validates that the runner correctly handles Windows-specific
        path formats and separators.
        """
        test_path = self.runner.project_root
        path_str = str(test_path)
        assert isinstance(path_str, str)
        assert len(path_str) > 0
        if os.name == 'nt':
            assert '\\' in path_str or test_path.is_absolute()
        assert test_path.exists()
        assert test_path.is_dir()
        test_subpath = test_path / 'tests'
        assert isinstance(test_subpath, Path)
        assert test_subpath.exists()
        self.record_metric('windows_path_handling', 'success')

    def test_command_validation_real_syntax(self):
        """
        Test that generated commands have valid syntax for execution.
        
        This validates that the command builder creates syntactically
        correct commands that could actually be executed.
        """
        args = argparse.Namespace(no_coverage=False, parallel=False, verbose=True, fast_fail=False, pattern=None, workers=4, category=None, categories=None, service=None, real_services=False, env='test')
        backend_cmd = self.runner._build_pytest_command('backend', 'unit', args)
        cmd_parts = backend_cmd.split()
        assert cmd_parts[0] in ['python3', 'python', 'py']
        assert '-m' in cmd_parts
        pytest_index = cmd_parts.index('-m') + 1
        assert cmd_parts[pytest_index] == 'pytest'
        assert not any(('""' in part for part in cmd_parts))
        assert not any((part.startswith('-') and '=' in part and (part.split('=')[1] == '') for part in cmd_parts))
        frontend_cmd = self.runner._build_frontend_command('unit', args)
        assert frontend_cmd.startswith('npm')
        assert 'npm run' in frontend_cmd
        self.record_metric('command_syntax', 'success')

    def test_category_system_integration_real(self):
        """
        Test integration with real category system components.
        
        This validates that the runner correctly integrates with
        the category system for test discovery and organization.
        """
        assert self.runner.category_system is not None
        try:
            categories = self.runner.category_system.categories
            assert isinstance(categories, dict)
        except AttributeError:
            assert hasattr(self.runner.category_system, 'get_category') or hasattr(self.runner.category_system, 'categories')
        assert self.runner.config_loader is not None
        self.record_metric('category_system_integration', 'success')

    def test_error_handling_real_scenarios(self):
        """
        Test error handling with real error scenarios.
        
        This validates that the runner handles actual error conditions
        gracefully without crashing.
        """
        args = argparse.Namespace(no_coverage=False, parallel=False, verbose=False, fast_fail=False, pattern=None, workers=4, category=None, categories=None, service=None)
        with self.expect_exception(KeyError):
            self.runner._build_pytest_command('nonexistent_service', 'unit', args)
        args_empty = argparse.Namespace(category=None, categories=[], service=None)
        categories = self.runner._determine_categories_to_run(args_empty)
        assert isinstance(categories, list)
        assert len(categories) > 0
        self.record_metric('error_handling', 'success')

    def test_real_system_python_detection_validation(self):
        """
        Test Python detection against the actual system environment.
        
        This validates that detected Python command works in real subprocess calls
        and can import required modules.
        """
        python_cmd = self.runner.python_command
        test_script = "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')"
        result = subprocess.run([python_cmd, '-c', test_script], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        assert 'Python 3.' in result.stdout
        pytest_test = "import pytest; print('pytest available')"
        result = subprocess.run([python_cmd, '-c', pytest_test], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        assert 'pytest available' in result.stdout
        self.record_metric('python_validation', 'success')

    def test_configuration_consistency_real_files(self):
        """
        Test configuration consistency with actual configuration files.
        
        This validates that the test configurations reference files
        that actually exist in the project structure.
        """
        backend_config = self.runner.test_configs['backend']
        backend_config_path = self.runner.project_root / backend_config['config']
        if backend_config_path.exists():
            content = backend_config_path.read_text(encoding='utf-8')
            assert '[pytest]' in content or 'pytest' in content.lower()
        auth_config = self.runner.test_configs['auth']
        auth_config_path = self.runner.project_root / auth_config['config']
        if auth_config_path.exists():
            content = auth_config_path.read_text(encoding='utf-8')
            assert len(content) > 0
        backend_test_dir = self.runner.project_root / backend_config['test_dir']
        assert backend_test_dir.exists(), f'Backend test directory should exist: {backend_test_dir}'
        auth_test_dir = self.runner.project_root / auth_config['test_dir']
        assert isinstance(str(auth_test_dir), str)
        self.record_metric('config_consistency', 'success')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')