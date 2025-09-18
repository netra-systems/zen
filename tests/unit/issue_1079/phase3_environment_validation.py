#!/usr/bin/env python3
"""
Issue #1079 Phase 3: Environment Validation Test

This test validates the test environment and import paths:
- Python path configuration
- Module discovery mechanisms
- Environment variables affecting imports
- Test framework integration issues
"""

import sys
import os
import unittest
import importlib
import site
from pathlib import Path
import json
import subprocess

class EnvironmentValidationTest(unittest.TestCase):
    """Phase 3: Validate test environment and import configuration"""

    def setUp(self):
        """Set up environment validation"""
        self.python_path_issues = []
        self.missing_paths = []
        self.environment_issues = []
        self.module_discovery_issues = []

    def test_python_path_configuration(self):
        """Test Python path configuration for netra_backend imports"""
        print("\n=== Phase 3.1: Testing Python path configuration ===")

        print("Current sys.path:")
        for i, path in enumerate(sys.path):
            print(f"  {i}: {path}")

        # Check if current directory is in Python path
        current_dir = os.getcwd()
        print(f"\nCurrent working directory: {current_dir}")

        if current_dir not in sys.path:
            print("WARNING️  Current directory not in sys.path")
            self.python_path_issues.append("current_directory_missing")

        # Check for netra_backend accessibility
        netra_backend_path = Path(current_dir) / "netra_backend"
        print(f"\nChecking netra_backend path: {netra_backend_path}")

        if netra_backend_path.exists():
            print("CHECK netra_backend directory exists")

            # Check if we can import netra_backend
            try:
                import netra_backend
                print("CHECK netra_backend package imports successfully")
                print(f"  Location: {netra_backend.__file__}")
            except ImportError as e:
                print(f"✗ netra_backend import failed: {e}")
                self.python_path_issues.append("netra_backend_import_failed")

        else:
            print("✗ netra_backend directory not found")
            self.missing_paths.append(str(netra_backend_path))

    def test_module_discovery_mechanism(self):
        """Test module discovery for problematic imports"""
        print("\n=== Phase 3.2: Testing module discovery mechanism ===")

        test_modules = [
            "netra_backend",
            "netra_backend.app",
            "netra_backend.app.db",
            "netra_backend.app.agents",
            "netra_backend.app.db.supply_database_manager",
            "netra_backend.app.agents.base_agent"
        ]

        for module_name in test_modules:
            print(f"\nTesting discovery: {module_name}")

            try:
                # Use find_spec to test module discovery
                spec = importlib.util.find_spec(module_name)

                if spec is None:
                    print(f"  ✗ Module spec not found")
                    self.module_discovery_issues.append(module_name)
                    continue

                print(f"  CHECK Module spec found")
                print(f"    Name: {spec.name}")
                print(f"    Origin: {spec.origin}")
                print(f"    Loader: {type(spec.loader).__name__ if spec.loader else 'None'}")

                # Check if origin file exists
                if spec.origin:
                    origin_path = Path(spec.origin)
                    if origin_path.exists():
                        print(f"    CHECK Origin file exists: {origin_path}")
                        stat = origin_path.stat()
                        print(f"      Size: {stat.st_size} bytes")
                        print(f"      Modified: {stat.st_mtime}")
                    else:
                        print(f"    ✗ Origin file missing: {origin_path}")
                        self.missing_paths.append(str(origin_path))

                # Test if we can create module from spec
                try:
                    module = importlib.util.module_from_spec(spec)
                    print(f"    CHECK Module object created successfully")
                except Exception as e:
                    print(f"    ✗ Module creation failed: {e}")

            except Exception as e:
                print(f"  ✗ Discovery failed: {type(e).__name__}: {e}")
                self.module_discovery_issues.append(module_name)

    def test_environment_variables(self):
        """Test environment variables affecting imports"""
        print("\n=== Phase 3.3: Testing environment variables ===")

        important_env_vars = [
            'PYTHONPATH',
            'PYTHONDONTWRITEBYTECODE',
            'PYTHONHASHSEED',
            'PYTHONUNBUFFERED',
            'PATH',
            'VIRTUAL_ENV'
        ]

        print("Environment variables:")
        for var in important_env_vars:
            value = os.environ.get(var)
            if value:
                print(f"  {var}: {value}")
            else:
                print(f"  {var}: (not set)")

        # Check if PYTHONPATH contains current directory
        pythonpath = os.environ.get('PYTHONPATH', '')
        current_dir = os.getcwd()

        if pythonpath:
            pythonpath_dirs = pythonpath.split(os.pathsep)
            if current_dir not in pythonpath_dirs:
                print(f"WARNING️  Current directory not in PYTHONPATH")
                self.environment_issues.append("current_dir_not_in_pythonpath")
        else:
            print("WARNING️  PYTHONPATH not set")
            self.environment_issues.append("pythonpath_not_set")

        # Check virtual environment
        virtual_env = os.environ.get('VIRTUAL_ENV')
        if virtual_env:
            print(f"CHECK Virtual environment: {virtual_env}")
            venv_path = Path(virtual_env)
            if not venv_path.exists():
                print(f"✗ Virtual environment path does not exist: {venv_path}")
                self.environment_issues.append("venv_path_missing")
        else:
            print("WARNING️  No virtual environment detected")

    def test_site_packages_configuration(self):
        """Test site-packages configuration"""
        print("\n=== Phase 3.4: Testing site-packages configuration ===")

        print("Site packages directories:")
        for path in site.getsitepackages():
            print(f"  {path}")

        print(f"\nUser site directory: {site.getusersitepackages()}")

        # Check for .pth files that might affect imports
        for site_dir in site.getsitepackages():
            site_path = Path(site_dir)
            if site_path.exists():
                pth_files = list(site_path.glob("*.pth"))
                if pth_files:
                    print(f"\n.pth files in {site_dir}:")
                    for pth_file in pth_files:
                        print(f"  {pth_file.name}")

    def test_test_framework_integration(self):
        """Test integration with test framework"""
        print("\n=== Phase 3.5: Testing test framework integration ===")

        # Check if we're running under pytest or unittest
        if 'pytest' in sys.modules:
            print("CHECK Running under pytest")
            pytest_version = sys.modules['pytest'].__version__
            print(f"  Version: {pytest_version}")
        else:
            print("CHECK Running under unittest")

        # Check for test-specific environment modifications
        print("\nTest-specific sys.path modifications:")
        for i, path in enumerate(sys.path):
            path_obj = Path(path)
            if path_obj.name in ['tests', 'test', 'test_framework']:
                print(f"  {i}: {path} (test-related)")

        # Check current working directory context
        cwd = os.getcwd()
        cwd_path = Path(cwd)
        print(f"\nTest execution context:")
        print(f"  Working directory: {cwd}")
        print(f"  Directory name: {cwd_path.name}")
        print(f"  Parent directory: {cwd_path.parent}")

        # Verify test can access main codebase
        try:
            from netra_backend.app.core.configuration.base import get_config
            print("CHECK Test can access main codebase (configuration)")
        except ImportError as e:
            print(f"✗ Test cannot access main codebase: {e}")
            self.environment_issues.append("codebase_access_failed")

    def test_import_performance_in_test_context(self):
        """Test import performance specifically in test context"""
        print("\n=== Phase 3.6: Testing import performance in test context ===")

        import time

        # Test imports that are known to be problematic
        test_imports = [
            "netra_backend.app.core.configuration.base",
            "netra_backend.app.db.database_manager",
            "netra_backend.app.agents.registry"
        ]

        for module_name in test_imports:
            print(f"\nTesting: {module_name}")

            # Clear from cache if present
            if module_name in sys.modules:
                del sys.modules[module_name]

            start_time = time.time()

            try:
                __import__(module_name)
                duration = time.time() - start_time
                print(f"  CHECK Import successful: {duration:.3f}s")

                if duration > 10.0:
                    print(f"  WARNING️  SLOW IMPORT: {duration:.3f}s")
                    self.environment_issues.append(f"slow_import_{module_name}")

            except Exception as e:
                duration = time.time() - start_time
                print(f"  ✗ Import failed after {duration:.3f}s: {e}")

    def test_subprocess_import_behavior(self):
        """Test how imports behave in subprocess (simulating test runner)"""
        print("\n=== Phase 3.7: Testing subprocess import behavior ===")

        # Test script to run in subprocess
        test_script = '''
import sys
import time
import os

print(f"Subprocess Python path entries: {len(sys.path)}")
print(f"Current directory: {os.getcwd()}")

start_time = time.time()
try:
    from netra_backend.app.agents.base_agent import BaseAgent
    duration = time.time() - start_time
    print(f"SUCCESS: BaseAgent import took {duration:.3f}s")
except Exception as e:
    duration = time.time() - start_time
    print(f"FAILED: BaseAgent import failed after {duration:.3f}s: {e}")

try:
    from netra_backend.app.db.supply_database_manager import SupplyDatabaseManager
    print("SUCCESS: SupplyDatabaseManager import successful")
except Exception as e:
    print(f"FAILED: SupplyDatabaseManager import failed: {e}")
'''

        try:
            result = subprocess.run(
                [sys.executable, '-c', test_script],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )

            print("Subprocess output:")
            print(result.stdout)

            if result.stderr:
                print("Subprocess errors:")
                print(result.stderr)

            if result.returncode != 0:
                print(f"✗ Subprocess failed with return code: {result.returncode}")
                self.environment_issues.append("subprocess_import_failed")
            else:
                print("CHECK Subprocess completed successfully")

        except subprocess.TimeoutExpired:
            print("✗ Subprocess timed out (import hang detected)")
            self.environment_issues.append("subprocess_timeout")
        except Exception as e:
            print(f"✗ Subprocess test failed: {e}")

    def tearDown(self):
        """Report environment validation results"""
        print("\n" + "="*60)
        print("PHASE 3 ENVIRONMENT VALIDATION SUMMARY")
        print("="*60)

        print(f"Python path issues: {len(self.python_path_issues)}")
        for issue in self.python_path_issues:
            print(f"  - {issue}")

        print(f"\nMissing paths: {len(self.missing_paths)}")
        for path in self.missing_paths:
            print(f"  - {path}")

        print(f"\nModule discovery issues: {len(self.module_discovery_issues)}")
        for module in self.module_discovery_issues:
            print(f"  - {module}")

        print(f"\nEnvironment issues: {len(self.environment_issues)}")
        for issue in self.environment_issues:
            print(f"  - {issue}")

        # Overall assessment
        total_issues = (len(self.python_path_issues) + len(self.missing_paths) +
                       len(self.module_discovery_issues) + len(self.environment_issues))

        if total_issues == 0:
            print("\nCHECK Environment validation passed - no issues detected")
        else:
            print(f"\n✗ Environment validation found {total_issues} issues")

if __name__ == "__main__":
    print("="*60)
    print("ISSUE #1079 PHASE 3: ENVIRONMENT VALIDATION")
    print("="*60)
    print("This test validates the test environment and import configuration:")
    print("- Python path configuration")
    print("- Module discovery mechanisms")
    print("- Environment variables")
    print("- Test framework integration")
    print("="*60)

    unittest.main(verbosity=2)