from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment
"""Tests for project_utils module.

This module tests the SSOT project utility functions for path resolution
and test environment detection.

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects ALL customer tiers through system reliability)
- Business Goal: System Reliability, Development Velocity
- Value Impact: Ensures correct path resolution and test environment detection across services
- Strategic Impact: Prevents production issues from incorrect path handling and improves development efficiency
"""

import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, Mock

from netra_backend.app.core.project_utils import (
    get_project_root,
    get_app_root,
    is_test_environment
)

env = get_env()

class TestProjectPathResolution:
    """Test project path resolution functions."""
    
    def test_get_project_root_returns_correct_path(self):
        """Test that get_project_root returns the correct project root path."""
        root = get_project_root()
        
        # Should be a Path object
        assert isinstance(root, Path)
        
        # Should be absolute
        assert root.is_absolute()
        
        # Should contain expected project structure markers
        expected_markers = [
            'netra_backend',
            'frontend',
            'shared',
            'requirements.txt'
        ]
        
        for marker in expected_markers:
            marker_path = root / marker
            assert marker_path.exists(), f"Expected project marker '{marker}' not found in {root}"
    
    def test_get_app_root_returns_correct_path(self):
        """Test that get_app_root returns the correct app root path."""
        app_root = get_app_root()
        
        # Should be a Path object
        assert isinstance(app_root, Path)
        
        # Should be absolute
        assert app_root.is_absolute()
        
        # Should contain expected app structure
        expected_items = [
            'core',
            'main.py',
            'db',
            'services'
        ]
        
        for item in expected_items:
            item_path = app_root / item
            assert item_path.exists(), f"Expected app item '{item}' not found in {app_root}"
    
    def test_project_and_app_root_relationship(self):
        """Test the relationship between project root and app root."""
        project_root = get_project_root()
        app_root = get_app_root()
        
        # App root should be inside project root
        assert str(app_root).startswith(str(project_root))
        
        # App root should be project_root/netra_backend/app
        expected_app_root = project_root / 'netra_backend' / 'app'
        assert app_root == expected_app_root
    
    def test_paths_are_consistent_across_calls(self):
        """Test that path functions return consistent results across multiple calls."""
        # Call multiple times
        roots1 = [get_project_root(), get_app_root()]
        roots2 = [get_project_root(), get_app_root()]
        roots3 = [get_project_root(), get_app_root()]
        
        # All calls should return identical paths
        assert roots1 == roots2 == roots3


class TestEnvironmentDetection:
    """Test test environment detection functionality."""
    
    def setup_method(self):
        """Setup method to store original environment."""
        self.original_env = env.get_all()
    
    def teardown_method(self):
        """Teardown method to restore original environment."""
        env.clear()
        env.update(self.original_env, "test")
    
    def test_pytest_current_test_detection(self):
        """Test detection via PYTEST_CURRENT_TEST variable."""
        # Clear all test-related env vars first
        test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', '_', 'ENVIRONMENT', 'NETRA_ENV']
        for var in test_vars:
            os.environ.pop(var, None)
        
        # Set PYTEST_CURRENT_TEST
        env.set('PYTEST_CURRENT_TEST', 'test_something.py::test_function', "test")
        
        assert is_test_environment() is True
    
    def test_testing_flag_detection(self):
        """Test detection via TESTING=1 flag."""
        # Clear all test-related env vars first
        test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', '_', 'ENVIRONMENT', 'NETRA_ENV']
        for var in test_vars:
            os.environ.pop(var, None)
        
        # Set TESTING flag
        env.set('TESTING', '1', "test")
        
        assert is_test_environment() is True
    
    def test_pytest_in_command_line_detection(self):
        """Test detection via pytest in command line."""
        # Clear all test-related env vars first
        test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', '_', 'ENVIRONMENT', 'NETRA_ENV']
        for var in test_vars:
            os.environ.pop(var, None)
        
        # Set _ variable with pytest
        env.set('_', '/usr/bin/pytest', "test")
        
        assert is_test_environment() is True
    
    def test_environment_name_test_detection(self):
        """Test detection via ENVIRONMENT=test."""
        # Clear all test-related env vars first
        test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', '_', 'ENVIRONMENT', 'NETRA_ENV']
        for var in test_vars:
            os.environ.pop(var, None)
        
        # Set ENVIRONMENT to test
        env.set('ENVIRONMENT', 'test', "test")
        
        assert is_test_environment() is True
    
    def test_environment_name_testing_detection(self):
        """Test detection via ENVIRONMENT=testing."""
        # Clear all test-related env vars first
        test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', '_', 'ENVIRONMENT', 'NETRA_ENV']
        for var in test_vars:
            os.environ.pop(var, None)
        
        # Set ENVIRONMENT to testing
        env.set('ENVIRONMENT', 'testing', "test")
        
        assert is_test_environment() is True
    
    def test_netra_env_test_detection(self):
        """Test detection via NETRA_ENV=test."""
        # Clear all test-related env vars first
        test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', '_', 'ENVIRONMENT', 'NETRA_ENV']
        for var in test_vars:
            os.environ.pop(var, None)
        
        # Set NETRA_ENV to test
        env.set('NETRA_ENV', 'test', "test")
        
        assert is_test_environment() is True
    
    def test_netra_env_testing_detection(self):
        """Test detection via NETRA_ENV=testing."""
        # Clear all test-related env vars first
        test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', '_', 'ENVIRONMENT', 'NETRA_ENV']
        for var in test_vars:
            os.environ.pop(var, None)
        
        # Set NETRA_ENV to testing
        env.set('NETRA_ENV', 'testing', "test")
        
        assert is_test_environment() is True
    
    def test_non_test_environment_detection(self):
        """Test that non-test environments return False."""
        # Mock IsolatedEnvironment to return production values
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = Mock()  # Initialize appropriate service
            mock_env.get.side_effect = lambda key, default='': {
                'PYTEST_CURRENT_TEST': None,
                'TESTING': None,
                '_': '',
                'ENVIRONMENT': 'production',
                'NETRA_ENV': 'production'
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            assert is_test_environment() is False
    
    def test_case_insensitive_detection(self):
        """Test that environment detection is case-insensitive."""
        # Clear all test-related env vars first
        test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', '_', 'ENVIRONMENT', 'NETRA_ENV']
        for var in test_vars:
            os.environ.pop(var, None)
        
        # Test various cases
        test_cases = [
            ('ENVIRONMENT', 'TEST'),
            ('ENVIRONMENT', 'Test'),
            ('ENVIRONMENT', 'TESTING'),
            ('ENVIRONMENT', 'Testing'),
            ('NETRA_ENV', 'TEST'),
            ('NETRA_ENV', 'TESTING'),
        ]
        
        for env_var, value in test_cases:
            # Clear and set specific variable
            for var in test_vars:
                os.environ.pop(var, None)
            
            os.environ[env_var] = value
            assert is_test_environment() is True, f"Failed for {env_var}={value}"
    
    def test_multiple_detection_methods_priority(self):
        """Test that multiple detection methods work together."""
        # Clear all first
        test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', '_', 'ENVIRONMENT', 'NETRA_ENV']
        for var in test_vars:
            os.environ.pop(var, None)
        
        # Set production environment but also test flags
        env.set('ENVIRONMENT', 'production', "test")
        env.set('PYTEST_CURRENT_TEST', 'test_file.py::test_func', "test")
        
        # Should still detect as test environment due to pytest flag
        assert is_test_environment() is True
    
    def test_empty_environment_variables(self):
        """Test behavior with empty environment variables."""
        # Mock IsolatedEnvironment to return empty values
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = Mock()  # Initialize appropriate service
            mock_env.get.side_effect = lambda key, default='': {
                'PYTEST_CURRENT_TEST': None,
                'TESTING': None,
                '_': '',
                'ENVIRONMENT': '',
                'NETRA_ENV': ''
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            assert is_test_environment() is False


class TestPathResolutionEdgeCases:
    """Test edge cases for path resolution."""
    
    def test_path_resolution_with_symlinks(self):
        """Test that path resolution works correctly with symbolic links."""
        # Get paths normally
        project_root = get_project_root()
        app_root = get_app_root()
        
        # Verify they're resolved (not symbolic)
        assert project_root.resolve() == project_root
        assert app_root.resolve() == app_root
    
    def test_path_resolution_is_stable(self):
        """Test that path resolution is stable across different working directories."""
        import os
        
        original_cwd = os.getcwd()
        
        try:
            # Get paths from original directory
            original_project_root = get_project_root()
            original_app_root = get_app_root()
            
            # Change to parent directory (safe directory that exists)
            parent_dir = Path(original_cwd).parent
            if parent_dir.exists():
                os.chdir(str(parent_dir))
                
                # Get paths from different directory
                new_project_root = get_project_root()
                new_app_root = get_app_root()
                
                # Paths should be identical regardless of working directory
                assert original_project_root == new_project_root
                assert original_app_root == new_app_root
                
        finally:
            os.chdir(original_cwd)


class TestSSotCompliance:
    """Test Single Source of Truth compliance."""
    
    def test_functions_are_ssot(self):
        """Test that project utilities serve as single source of truth."""
        # These functions should be the canonical way to get these paths
        # Any other method of getting project paths should use these functions
        
        # Verify functions exist and are callable
        assert callable(get_project_root)
        assert callable(get_app_root)
        assert callable(is_test_environment)
        
        # Verify they return consistent types
        assert isinstance(get_project_root(), Path)
        assert isinstance(get_app_root(), Path)
        assert isinstance(is_test_environment(), bool)
    
    def test_functions_have_docstrings(self):
        """Test that all functions have proper documentation."""
        functions = [get_project_root, get_app_root, is_test_environment]
        
        for func in functions:
            assert func.__doc__ is not None, f"Function {func.__name__} missing docstring"
            assert len(func.__doc__.strip()) > 0, f"Function {func.__name__} has empty docstring"
            
            # Should mention SSOT for critical functions
            if func.__name__ in ['get_project_root', 'is_test_environment']:
                assert 'SINGLE SOURCE OF TRUTH' in func.__doc__.upper(), \
                    f"Function {func.__name__} should document SSOT compliance"


class TestIntegrationWithActualEnvironment:
    """Integration tests with the actual development environment."""
    
    def test_project_structure_validation(self):
        """Test that detected project structure matches expected layout."""
        project_root = get_project_root()
        
        # Critical project structure validation
        critical_paths = [
            'netra_backend/app/main.py',
            'frontend/package.json', 
            'shared',
            'requirements.txt',
            'CLAUDE.md'
        ]
        
        for critical_path in critical_paths:
            full_path = project_root / critical_path
            assert full_path.exists(), \
                f"Critical project file/directory '{critical_path}' not found. " \
                f"Project root detected as: {project_root}"
    
    def test_app_structure_validation(self):
        """Test that detected app structure matches expected layout."""
        app_root = get_app_root()
        
        # Critical app structure validation
        critical_paths = [
            'core/project_utils.py',  # This very file should be findable
            'main.py',
            'db',
            'services'
        ]
        
        for critical_path in critical_paths:
            full_path = app_root / critical_path
            assert full_path.exists(), \
                f"Critical app file/directory '{critical_path}' not found. " \
                f"App root detected as: {app_root}"
    
    def test_current_test_is_actually_in_test_environment(self):
        """Meta-test: Verify this test is running in test environment."""
        # This test itself should be detected as running in test environment
        assert is_test_environment() is True, \
            "This test should be running in test environment but is_test_environment() returned False"


# Integration test for SSOT compliance
class TestRealWorldUsage:
    """Test real-world usage scenarios."""
    
    def test_can_import_sibling_modules_using_project_root(self):
        """Test that we can use project_root to import sibling modules."""
        project_root = get_project_root()
        
        # Should be able to construct paths to other modules
        shared_path = project_root / 'shared'
        assert shared_path.exists()
        assert shared_path.is_dir()
        
        # Should contain expected shared modules  
        expected_shared_files = ['secret_manager_builder.py']
        for file_name in expected_shared_files:
            shared_file = shared_path / file_name
            assert shared_file.exists(), f"Expected shared file '{file_name}' not found"
    
    def test_can_find_config_files_using_project_root(self):
        """Test that we can find configuration files using project_root."""
        project_root = get_project_root()
        
        # Should find common config files
        config_files = [
            'requirements.txt',
            'CLAUDE.md',
            '.gitignore'
        ]
        
        for config_file in config_files:
            config_path = project_root / config_file
            assert config_path.exists(), f"Expected config file '{config_file}' not found"
    
    def test_environment_detection_works_in_ci(self):
        """Test environment detection for CI environments."""
        # In CI environments, we might have different combinations of variables
        # This test ensures our detection is robust
        
        # Save current environment
        original_env = env.get_all()
        
        try:
            # Simulate CI test environment
            env.clear()
            env.update(original_env, "test")  # Restore base environment
            
            # CI environments often set specific test-related variables
            ci_test_scenarios = [
                {'PYTEST_CURRENT_TEST': 'test_file.py::test_function'},
                {'TESTING': '1'},
                {'ENVIRONMENT': 'test'},
                {'NODE_ENV': 'test', 'PYTEST_CURRENT_TEST': 'something'},  # Mixed frontend/backend
            ]
            
            for scenario in ci_test_scenarios:
                # Clear test variables
                test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', 'ENVIRONMENT', 'NETRA_ENV', '_']
                for var in test_vars:
                    os.environ.pop(var, None)
                
                # Apply scenario
                env.update(scenario, "test")
                
                assert is_test_environment() is True, \
                    f"Failed to detect test environment for CI scenario: {scenario}"
                    
        finally:
            # Restore original environment
            env.clear()
            env.update(original_env, "test")