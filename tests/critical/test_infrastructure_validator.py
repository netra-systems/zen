"""
Test Infrastructure Validator for Issue #1176 Phase 3
====================================================

Week 1 Foundation Tasks: Core infrastructure validation that ensures
the test infrastructure itself is functioning correctly and reports
accurate results.

This validator specifically tests:
1. Test runner accuracy and truthfulness
2. Infrastructure component availability  
3. Basic import and startup functionality
4. Configuration accessibility

CRITICAL: These tests validate the test infrastructure BEFORE using it
to validate the application code.
"""

import subprocess
import sys
import os
import importlib.util
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestInfrastructureValidator(SSotBaseTestCase):
    """
    Foundation validator for test infrastructure components.
    
    These tests must pass before any application testing can be trusted.
    """

    def setUp(self):
        """Set up test infrastructure validation."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        
    def test_unified_test_runner_exists_and_importable(self):
        """
        FOUNDATION: Verify unified test runner exists and can be imported.
        """
        test_runner_path = self.project_root / "tests" / "unified_test_runner.py"
        
        self.assertTrue(
            test_runner_path.exists(),
            f"Unified test runner must exist at {test_runner_path}"
        )
        
        # Test that it can be imported
        spec = importlib.util.spec_from_file_location(
            "unified_test_runner", 
            test_runner_path
        )
        
        self.assertIsNotNone(
            spec,
            "Unified test runner must be importable"
        )
        
        # Test that module can be loaded
        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check for key classes
            self.assertTrue(
                hasattr(module, 'UnifiedTestRunner'),
                "UnifiedTestRunner class must be available"
            )
            
        except Exception as e:
            self.fail(f"Failed to load unified test runner: {e}")

    def test_test_framework_ssot_availability(self):
        """
        FOUNDATION: Verify SSOT test framework components are available.
        """
        required_ssot_modules = [
            "test_framework.ssot.base_test_case",
            "test_framework.ssot.mock_factory", 
            "test_framework.ssot.database_test_utility",
            "test_framework.ssot.websocket_test_utility"
        ]
        
        for module_name in required_ssot_modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                self.fail(f"Required SSOT module '{module_name}' not available: {e}")
                
    def test_critical_application_imports(self):
        """
        FOUNDATION: Verify critical application imports work.
        """
        critical_imports = [
            "netra_backend.app.config",
            "netra_backend.app.db.database_manager",
            "shared.cors_config"
        ]
        
        import_failures = []
        
        for module_name in critical_imports:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                import_failures.append(f"{module_name}: {e}")
                
        if import_failures:
            self.fail(
                f"Critical application imports failed:\n" + 
                "\n".join(import_failures)
            )

    def test_test_runner_basic_execution(self):
        """
        FOUNDATION: Verify test runner can execute basic operations.
        """
        # Test help command works
        cmd = [
            sys.executable,
            "tests/unified_test_runner.py", 
            "--help"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        self.assertEqual(
            result.returncode, 0,
            f"Test runner help command failed: {result.stderr}"
        )
        
        # Check for basic help content
        self.assertIn(
            "usage:",
            result.stdout.lower(),
            "Help output must contain usage information"
        )

    def test_environment_variables_accessibility(self):
        """
        FOUNDATION: Verify environment variables can be accessed.
        """
        # Test basic environment access
        test_env_script = '''
import os
import sys
sys.path.insert(0, ".")

try:
    from dev_launcher.isolated_environment import IsolatedEnvironment
    env = IsolatedEnvironment()
    
    # Test basic environment access
    env.get("HOME", "default")
    env.get("PATH", "default")
    
    print("Environment access successful")
    sys.exit(0)
    
except Exception as e:
    print(f"Environment access failed: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_env_script],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        self.assertEqual(
            result.returncode, 0,
            f"Environment variable access failed: {result.stderr}"
        )

    def test_project_structure_integrity(self):
        """
        FOUNDATION: Verify basic project structure is intact.
        """
        required_directories = [
            "tests",
            "test_framework",
            "netra_backend",
            "shared",
            "scripts"
        ]
        
        missing_dirs = []
        
        for dir_name in required_directories:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
                
        if missing_dirs:
            self.fail(
                f"Required project directories missing: {missing_dirs}"
            )

    def test_python_path_configuration(self):
        """
        FOUNDATION: Verify Python path is configured correctly.
        """
        # Test that project modules can be found
        path_test_script = '''
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    # These imports should work if path is configured correctly
    import netra_backend
    import test_framework
    import shared
    
    print("Python path configuration successful")
    sys.exit(0)
    
except ImportError as e:
    print(f"Python path configuration failed: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", path_test_script],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        self.assertEqual(
            result.returncode, 0,
            f"Python path configuration failed: {result.stderr}"
        )

    def test_test_collection_mechanism(self):
        """
        FOUNDATION: Verify test collection mechanism works.
        """
        # Test that pytest can collect tests from our structure
        cmd = [
            sys.executable, 
            "-m", "pytest",
            "--collect-only",
            "--quiet",
            "tests/critical/test_issue_1176_anti_recursive_validation.py"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        self.assertEqual(
            result.returncode, 0,
            f"Test collection failed: {result.stderr}"
        )
        
        # Should find test methods
        self.assertIn(
            "test",
            result.stdout,
            "Test collection should find test methods"
        )

    def test_subprocess_execution_environment(self):
        """
        FOUNDATION: Verify subprocess execution works correctly.
        """
        # Test basic subprocess execution
        result = subprocess.run(
            [sys.executable, "-c", "print('subprocess test')"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        self.assertEqual(
            result.returncode, 0,
            "Basic subprocess execution must work"
        )
        
        self.assertIn(
            "subprocess test",
            result.stdout,
            "Subprocess output must be captured correctly"
        )

    def test_critical_file_permissions(self):
        """
        FOUNDATION: Verify critical files have correct permissions.
        """
        critical_files = [
            "tests/unified_test_runner.py",
            "test_framework/ssot/base_test_case.py"
        ]
        
        permission_issues = []
        
        for file_path in critical_files:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                permission_issues.append(f"{file_path}: Does not exist")
                continue
                
            if not os.access(full_path, os.R_OK):
                permission_issues.append(f"{file_path}: Not readable")
                
        if permission_issues:
            self.fail(
                f"File permission issues:\n" + 
                "\n".join(permission_issues)
            )


if __name__ == "__main__":
    # Run infrastructure validation independently
    import unittest
    unittest.main()