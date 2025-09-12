"""
Issue #519: Pytest Environment Validation Tests - Phase 3

This test suite validates the pytest execution environment to ensure
it's properly configured for Mission Critical test execution without conflicts.

Focus Areas:
- Python environment consistency
- Virtual environment isolation
- Module import path validation  
- Plugin discovery environment
- System-level pytest configuration

Business Impact: HIGH - Ensures reliable test environment for $500K+ ARR protection
Priority: P0 - Critical infrastructure validation
"""

import subprocess
import sys
import os
import pytest
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple


class TestPythonEnvironmentConsistency:
    """Test Python environment setup for consistent pytest execution."""
    
    def test_phase3_python_version_consistency(self):
        """PHASE 3: Validate Python version consistency across execution contexts.
        
        Different Python versions can have different plugin loading behaviors.
        This test should PASS but documents environment state.
        """
        import sys
        
        # Get current Python version
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # Run pytest in subprocess to see if version is consistent
        cmd = [sys.executable, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        subprocess_version = result.stdout.strip()
        
        assert current_version == subprocess_version, (
            f"Python version inconsistency detected:\n"
            f"  Current process: {current_version}\n" 
            f"  Subprocess: {subprocess_version}\n"
            f"This can cause pytest plugin loading issues."
        )
        
        # Also validate that pytest is using the same Python
        cmd = [sys.executable, "-m", "pytest", "--version"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            pytest.fail(f"pytest --version failed: {result.stderr}")
        
        print(f"Python version: {current_version}")
        print(f"Pytest version info: {result.stdout.strip()}")
        
    def test_phase3_virtual_environment_isolation(self):
        """PHASE 3: Validate virtual environment provides proper isolation.
        
        Should FAIL if venv isolation is broken, allowing system packages to interfere.
        """
        import sys
        
        # Check if we're in a virtual environment
        in_venv = (
            hasattr(sys, 'real_prefix') or  # virtualenv
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)  # venv
        )
        
        if not in_venv:
            pytest.skip("Not running in virtual environment - isolation test not applicable")
        
        # Get venv paths
        venv_path = Path(sys.prefix)
        site_packages_paths = [Path(p) for p in sys.path if 'site-packages' in p and str(venv_path) in p]
        
        if not site_packages_paths:
            pytest.fail(
                f"Virtual environment site-packages not found in sys.path.\n"
                f"venv path: {venv_path}\n"
                f"sys.path: {sys.path[:5]}..."  # First 5 entries
            )
        
        # Check for system pytest contamination
        system_site_packages = [p for p in sys.path if 'site-packages' in p and str(venv_path) not in p]
        
        pytest_conflicts = []
        for sys_path in system_site_packages:
            sys_pytest_path = Path(sys_path) / "pytest"
            if sys_pytest_path.exists():
                pytest_conflicts.append(str(sys_pytest_path))
        
        if pytest_conflicts:
            pytest.fail(
                f"System pytest installations found in PATH, may cause plugin conflicts:\n" +
                "\n".join(f"  - {path}" for path in pytest_conflicts) +
                f"\nVirtual environment should isolate from system packages."
            )
        
        assert True, f"Virtual environment isolation confirmed. Site-packages: {site_packages_paths[0]}"
    
    def test_phase3_module_import_path_validation(self):
        """PHASE 3: Validate module import paths for consistent plugin discovery.
        
        Should FAIL if import paths are inconsistent, causing plugin loading issues.
        """
        import sys
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        
        # Check if project root is in sys.path (it should be for tests)
        project_root_in_path = any(
            Path(p).resolve() == project_root.resolve() 
            for p in sys.path
        )
        
        if not project_root_in_path:
            # Try to find where project modules would be imported from
            test_module_paths = []
            for path in sys.path:
                potential_path = Path(path) / "test_framework"
                if potential_path.exists():
                    test_module_paths.append(str(potential_path))
            
            if not test_module_paths:
                pytest.fail(
                    f"Project root not in sys.path and test_framework not found elsewhere.\n"
                    f"Project root: {project_root}\n"
                    f"This will cause module import failures for plugins.\n"
                    f"First 5 sys.path entries: {sys.path[:5]}"
                )
            else:
                pytest.fail(
                    f"Project root not in sys.path, but test_framework found at:\n" +
                    "\n".join(f"  - {path}" for path in test_module_paths) +
                    f"\nThis may cause inconsistent plugin imports."
                )
        
        # Validate that test_framework can be imported
        try:
            import test_framework
            test_framework_path = Path(test_framework.__file__).parent
        except ImportError as e:
            pytest.fail(f"Cannot import test_framework module: {e}")
        
        # Check if the imported test_framework is from the expected location
        expected_path = project_root / "test_framework"
        if test_framework_path.resolve() != expected_path.resolve():
            pytest.fail(
                f"test_framework imported from unexpected location:\n"
                f"  Expected: {expected_path}\n"
                f"  Actual: {test_framework_path}\n"
                f"This can cause plugin version conflicts."
            )
        
        assert True, f"Module import paths validated. test_framework: {test_framework_path}"


class TestPytestEnvironmentConfiguration:
    """Test pytest-specific environment configuration."""
    
    def test_phase3_pytest_plugin_discovery_environment(self):
        """PHASE 3: Test environment setup for pytest plugin discovery.
        
        Should FAIL if plugin discovery environment is misconfigured.
        """
        import sys
        from pathlib import Path
        
        # Check PYTHONPATH environment variable
        python_path = os.environ.get('PYTHONPATH', '')
        project_root = Path(__file__).parent.parent.parent
        
        # For plugin discovery to work correctly, project should be in PYTHONPATH or sys.path
        paths_to_check = []
        if python_path:
            paths_to_check.extend(python_path.split(os.pathsep))
        paths_to_check.extend(sys.path)
        
        project_accessible = any(
            Path(p).resolve() == project_root.resolve()
            for p in paths_to_check
            if p  # Skip empty strings
        )
        
        if not project_accessible:
            pytest.fail(
                f"Project root not accessible for plugin discovery:\n"
                f"  Project root: {project_root}\n"
                f"  PYTHONPATH: {python_path}\n"
                f"  sys.path (first 5): {sys.path[:5]}\n"
                f"This will prevent pytest from discovering project plugins."
            )
        
        # Check for pytest-specific environment variables that might affect behavior
        pytest_env_vars = {
            key: value for key, value in os.environ.items()
            if 'PYTEST' in key.upper() or 'TEST' in key.upper()
        }
        
        print(f"Pytest-related environment variables: {pytest_env_vars}")
        
        # Check if any problematic test environment variables are set
        problematic_vars = []
        for key, value in pytest_env_vars.items():
            if 'DISABLE' in key.upper() and value.lower() in ['true', '1', 'yes']:
                problematic_vars.append(f"{key}={value}")
        
        if problematic_vars:
            pytest.fail(
                f"Problematic test environment variables found:\n" +
                "\n".join(f"  - {var}" for var in problematic_vars) +
                f"\nThese may interfere with pytest plugin discovery."
            )
        
        assert True, "Pytest plugin discovery environment validated"
    
    def test_phase3_conftest_loading_environment(self):
        """PHASE 3: Test environment for proper conftest.py loading.
        
        Should FAIL if conftest loading environment has issues.
        """
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        
        # Find all conftest.py files in the project
        conftest_files = list(project_root.rglob("conftest.py"))
        
        # Filter out venv and system files
        project_conftest_files = [
            f for f in conftest_files 
            if 'venv' not in str(f) and 'site-packages' not in str(f)
        ]
        
        if not project_conftest_files:
            pytest.fail("No conftest.py files found in project")
        
        print(f"Found {len(project_conftest_files)} conftest.py files")
        
        # Check if conftest files have any syntax errors
        syntax_errors = []
        for conftest_file in project_conftest_files:
            try:
                with open(conftest_file, 'r') as f:
                    content = f.read()
                compile(content, str(conftest_file), 'exec')
            except SyntaxError as e:
                syntax_errors.append(f"{conftest_file}: {e}")
            except Exception as e:
                syntax_errors.append(f"{conftest_file}: {type(e).__name__}: {e}")
        
        if syntax_errors:
            pytest.fail(
                f"Syntax errors in conftest.py files:\n" +
                "\n".join(f"  - {error}" for error in syntax_errors)
            )
        
        # Check for import errors in conftest files
        import_errors = []
        for conftest_file in project_conftest_files:
            # Try to import the modules that conftest files depend on
            try:
                with open(conftest_file, 'r') as f:
                    content = f.read()
                
                # Look for import statements
                import re
                imports = re.findall(r'^(?:from\s+(\S+)\s+)?import\s+(\S+)', content, re.MULTILINE)
                
                for from_module, import_name in imports:
                    if from_module and not from_module.startswith('.'):
                        try:
                            importlib.import_module(from_module)
                        except ImportError as e:
                            import_errors.append(f"{conftest_file}: Cannot import {from_module}: {e}")
                        
            except Exception as e:
                import_errors.append(f"{conftest_file}: Error analyzing imports: {e}")
        
        if import_errors:
            # Only fail if these are critical imports, not optional ones
            critical_errors = [
                error for error in import_errors 
                if not any(optional in error.lower() for optional in ['optional', 'try', 'except'])
            ]
            
            if critical_errors:
                pytest.fail(
                    f"Import errors in conftest.py files:\n" +
                    "\n".join(f"  - {error}" for error in critical_errors[:5])  # Limit to first 5
                )
        
        assert True, f"Conftest loading environment validated for {len(project_conftest_files)} files"


class TestSystemLevelConfiguration:
    """Test system-level configuration that might affect pytest."""
    
    def test_phase3_system_pytest_configuration(self):
        """PHASE 3: Check for system-level pytest configuration conflicts.
        
        Should FAIL if system config interferes with project config.
        """
        import os
        from pathlib import Path
        
        # Check for system-wide pytest configuration
        system_config_locations = [
            Path.home() / '.pytest.ini',
            Path.home() / 'pytest.ini',
            Path('/etc/pytest.ini'),
            Path('/usr/local/etc/pytest.ini')
        ]
        
        system_configs_found = [
            str(config_path) for config_path in system_config_locations
            if config_path.exists()
        ]
        
        if system_configs_found:
            pytest.fail(
                f"System-wide pytest configuration files found:\n" +
                "\n".join(f"  - {config}" for config in system_configs_found) +
                f"\nThese may override project-specific pytest configuration."
            )
        
        # Check for environment variables that affect pytest behavior
        pytest_env_overrides = {}
        for key, value in os.environ.items():
            if key.startswith('PYTEST_') and key != 'PYTEST_CURRENT_TEST':
                pytest_env_overrides[key] = value
        
        if pytest_env_overrides:
            pytest.fail(
                f"Pytest environment variable overrides found:\n" +
                "\n".join(f"  - {key}={value}" for key, value in pytest_env_overrides.items()) +
                f"\nThese may interfere with project pytest configuration."
            )
        
        assert True, "No system-level pytest configuration conflicts found"
    
    def test_phase3_plugin_installation_environment(self):
        """PHASE 3: Validate plugin installation environment.
        
        Should FAIL if plugin installation environment has conflicts.
        """
        import sys
        import pkg_resources
        from pathlib import Path
        
        # Get all installed packages
        try:
            installed_packages = {pkg.project_name.lower(): pkg for pkg in pkg_resources.working_set}
        except Exception as e:
            pytest.skip(f"Could not enumerate installed packages: {e}")
        
        # Look for pytest plugins
        pytest_plugins = {
            name: pkg for name, pkg in installed_packages.items()
            if 'pytest' in name or name.startswith('py.test')
        }
        
        print(f"Installed pytest-related packages: {list(pytest_plugins.keys())}")
        
        # Check for version conflicts
        version_conflicts = []
        
        # Check if pytest is installed
        if 'pytest' not in installed_packages:
            pytest.fail("pytest not found in installed packages")
        
        pytest_version = installed_packages['pytest'].version
        print(f"Pytest version: {pytest_version}")
        
        # Check for plugin compatibility issues
        incompatible_plugins = []
        
        for plugin_name, plugin_pkg in pytest_plugins.items():
            if plugin_name == 'pytest':
                continue
            
            # Check if plugin has version requirements
            try:
                requirements = list(plugin_pkg.requires())
                pytest_reqs = [req for req in requirements if req.project_name.lower() == 'pytest']
                
                for req in pytest_reqs:
                    if not req.specifier.contains(pytest_version):
                        incompatible_plugins.append(
                            f"{plugin_name} {plugin_pkg.version} requires pytest{req.specifier}, "
                            f"but {pytest_version} is installed"
                        )
            except Exception:
                # Skip plugins we can't analyze
                continue
        
        if incompatible_plugins:
            pytest.fail(
                f"Incompatible pytest plugins found:\n" +
                "\n".join(f"  - {issue}" for issue in incompatible_plugins)
            )
        
        # Check for duplicate plugin installations (different locations)
        plugin_locations = {}
        for plugin_name, plugin_pkg in pytest_plugins.items():
            location = Path(plugin_pkg.location)
            if plugin_name not in plugin_locations:
                plugin_locations[plugin_name] = []
            plugin_locations[plugin_name].append(str(location))
        
        duplicate_installations = {
            name: locations for name, locations in plugin_locations.items()
            if len(set(locations)) > 1  # Different locations
        }
        
        if duplicate_installations:
            pytest.fail(
                f"Duplicate plugin installations found:\n" +
                "\n".join(
                    f"  - {name}: {locations}" 
                    for name, locations in duplicate_installations.items()
                )
            )
        
        assert True, f"Plugin installation environment validated. {len(pytest_plugins)} plugins found."


class TestConcurrencyAndIsolation:
    """Test concurrent execution and test isolation environment."""
    
    def test_phase3_concurrent_pytest_execution_safety(self):
        """PHASE 3: Test that pytest environment supports safe concurrent execution.
        
        Should FAIL if concurrent execution environment has issues.
        """
        import tempfile
        import threading
        import queue
        from pathlib import Path
        
        # Create temporary test files for concurrent execution
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create simple test files
            for i in range(3):
                test_content = f'''
def test_concurrent_{i}():
    """Concurrent test {i}."""
    import time
    time.sleep(0.1)  # Small delay to test concurrency
    assert True
'''
                (tmpdir_path / f"test_concurrent_{i}.py").write_text(test_content)
            
            # Create conftest.py for the temp tests
            conftest_content = '''
import pytest

@pytest.fixture
def shared_resource():
    """Test shared resource fixture."""
    return "shared_value"
'''
            (tmpdir_path / "conftest.py").write_text(conftest_content)
            
            # Run multiple pytest instances concurrently
            results_queue = queue.Queue()
            
            def run_pytest_worker(worker_id):
                """Worker function to run pytest."""
                cmd = [
                    sys.executable, "-m", "pytest",
                    str(tmpdir_path / f"test_concurrent_{worker_id}.py"),
                    "-v"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                results_queue.put({
                    'worker_id': worker_id,
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                })
            
            # Start concurrent workers
            threads = []
            for i in range(3):
                thread = threading.Thread(target=run_pytest_worker, args=(i,))
                thread.start()
                threads.append(thread)
            
            # Wait for all workers to complete
            for thread in threads:
                thread.join(timeout=60)
                if thread.is_alive():
                    pytest.fail(f"Worker thread did not complete within timeout")
            
            # Collect results
            results = []
            while not results_queue.empty():
                results.append(results_queue.get())
            
            if len(results) != 3:
                pytest.fail(f"Expected 3 results, got {len(results)}")
            
            # Check for failures
            failures = [r for r in results if r['returncode'] != 0]
            
            if failures:
                failure_details = []
                for failure in failures:
                    failure_details.append(
                        f"Worker {failure['worker_id']}: exit {failure['returncode']}\n"
                        f"STDERR: {failure['stderr']}"
                    )
                
                pytest.fail(
                    f"Concurrent pytest execution failures:\n" +
                    "\n".join(failure_details)
                )
            
            assert True, f"Concurrent pytest execution successful for {len(results)} workers"
    
    def test_phase3_test_isolation_environment_validation(self):
        """PHASE 3: Validate test isolation environment.
        
        Should FAIL if test isolation is broken.
        """
        import sys
        import os
        
        # Check for global state that might leak between tests
        problematic_globals = []
        
        # Check environment variables that might persist
        test_env_vars = {
            key: value for key, value in os.environ.items()
            if any(prefix in key.upper() for prefix in ['TEST_', 'PYTEST_', 'MOCK_'])
        }
        
        # Some test environment variables are expected
        expected_test_vars = {
            'PYTEST_CURRENT_TEST',  # Set by pytest itself
            'TEST_COLLECTION_MODE',  # Our own test mode indicator
            'TESTING'  # Common test mode indicator
        }
        
        unexpected_vars = {
            key: value for key, value in test_env_vars.items()
            if key not in expected_test_vars and not key.startswith('TEST_DISABLE')
        }
        
        if len(unexpected_vars) > 10:  # Allow some test vars but not too many
            problematic_globals.append(
                f"Many test environment variables set ({len(unexpected_vars)}), "
                f"may indicate poor test isolation"
            )
        
        # Check for module-level global state
        import gc
        
        # Get all objects in memory
        all_objects = gc.get_objects()
        
        # Look for large global caches or state objects
        large_objects = [
            obj for obj in all_objects 
            if hasattr(obj, '__dict__') and len(obj.__dict__) > 50
        ]
        
        # This is informational - too many large objects might indicate memory leaks
        if len(large_objects) > 100:
            print(f"Warning: {len(large_objects)} large objects in memory, may indicate leaks")
        
        if problematic_globals:
            pytest.fail(
                f"Test isolation environment issues:\n" +
                "\n".join(f"  - {issue}" for issue in problematic_globals)
            )
        
        assert True, f"Test isolation environment validated. {len(unexpected_vars)} unexpected env vars."