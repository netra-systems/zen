"""
Issue #519: Pytest Configuration Management Tests - Phase 2

This test suite validates pytest configuration management and plugin loading
to ensure proper resolution of configuration conflicts.

Focus Areas:
- Plugin registration order and conflicts
- Configuration file precedence and validation  
- Hook function conflicts and resolution
- Command-line option management

Business Impact: HIGH - Enables Mission Critical test suite execution
Priority: P0 - Required for $500K+ ARR protection
"""

import subprocess
import sys
import pytest
import tempfile
import textwrap
from pathlib import Path
from typing import List, Dict, Any, Optional, Set


class TestPytestPluginManagement:
    """Test pytest plugin registration and management."""
    
    def test_phase2_plugin_registration_order(self):
        """PHASE 2: Test plugin registration order conflicts.
        
        This test should initially FAIL, demonstrating that plugins
        are being registered in conflicting order.
        """
        # Create a minimal test setup to isolate plugin loading
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create a minimal conftest.py that mimics our issue
            conftest_content = textwrap.dedent("""
                # Simulate our wildcard import issue
                import pytest
                
                def pytest_addoption(parser):
                    parser.addoption(
                        "--test-option-conflict",
                        action="store_true", 
                        default=False,
                        help="Test option for conflict detection"
                    )
            """)
            
            (tmpdir_path / "conftest.py").write_text(conftest_content)
            
            # Create a plugin file that defines the same option
            plugin_content = textwrap.dedent("""
                import pytest
                
                def pytest_addoption(parser):
                    parser.addoption(
                        "--test-option-conflict",
                        action="store_true",
                        default=False, 
                        help="Duplicate test option"
                    )
                
                def pytest_configure(config):
                    pass
            """)
            
            (tmpdir_path / "test_plugin.py").write_text(plugin_content)
            
            # Create a minimal test file
            test_content = textwrap.dedent("""
                def test_dummy():
                    assert True
            """)
            (tmpdir_path / "test_dummy.py").write_text(test_content)
            
            # Try to run pytest with the conflicting plugin
            cmd = [
                sys.executable, "-m", "pytest",
                "--collect-only",
                "-p", f"{tmpdir}/test_plugin",
                str(tmpdir_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Should fail due to duplicate option registration
            assert result.returncode != 0, (
                f"Expected plugin conflict but pytest succeeded:\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )
            
            # Verify it's specifically an option conflict
            error_output = result.stderr.lower()
            assert any(keyword in error_output for keyword in [
                "already added", "conflict", "duplicate", "option"
            ]), f"Expected option conflict error, got: {result.stderr}"
    
    def test_phase2_hook_function_conflicts(self):
        """PHASE 2: Test pytest hook function conflicts.
        
        Multiple conftest.py files or plugins defining the same hook
        can cause unpredictable behavior.
        """
        # Analyze actual project structure for hook conflicts
        project_root = Path(__file__).parent.parent.parent
        
        hook_functions = {}
        conftest_files = list(project_root.rglob("conftest.py"))
        
        # Check for duplicate hook function definitions
        for conftest_file in conftest_files:
            try:
                content = conftest_file.read_text()
                
                # Look for pytest hook functions
                import re
                hook_pattern = r'def (pytest_\w+)\s*\('
                hooks = re.findall(hook_pattern, content)
                
                for hook in hooks:
                    if hook not in hook_functions:
                        hook_functions[hook] = []
                    hook_functions[hook].append(str(conftest_file))
                    
            except Exception as e:
                # Skip files that can't be read
                continue
        
        # Find conflicts (same hook in multiple files)
        conflicts = {
            hook: files for hook, files in hook_functions.items() 
            if len(files) > 1
        }
        
        if conflicts:
            conflict_details = []
            for hook, files in conflicts.items():
                conflict_details.append(f"  {hook}: {len(files)} definitions in {files}")
            
            pytest.fail(
                f"Hook function conflicts found:\n" + 
                "\n".join(conflict_details) +
                "\n\nThese conflicts can cause unpredictable pytest behavior."
            )
        
        assert True, f"No hook function conflicts found in {len(conftest_files)} conftest.py files"
    
    def test_phase2_plugin_import_isolation(self):
        """PHASE 2: Test that plugin imports don't leak into global namespace.
        
        Wildcard imports can bring plugin functions into conftest namespace,
        causing them to be registered multiple times.
        """
        # Check the actual problematic import in our conftest.py
        main_conftest = Path(__file__).parent.parent / "conftest.py"
        
        if not main_conftest.exists():
            pytest.skip("Main conftest.py not found")
        
        content = main_conftest.read_text()
        
        # Check for wildcard imports from plugin modules
        wildcard_imports = []
        for line_num, line in enumerate(content.split('\n'), 1):
            if 'import *' in line and 'plugin' in line.lower():
                wildcard_imports.append(f"Line {line_num}: {line.strip()}")
        
        if wildcard_imports:
            pytest.fail(
                f"Wildcard imports from plugins found in {main_conftest}:\n" +
                "\n".join(wildcard_imports) +
                "\n\nThese can cause function namespace pollution and duplicate registrations."
            )
        
        assert True, "No problematic wildcard imports from plugins found"


class TestConfigurationValidation:
    """Test configuration file validation and precedence."""
    
    def test_phase2_pyproject_toml_validation(self):
        """PHASE 2: Validate pyproject.toml pytest configuration.
        
        Should initially FAIL if configuration has issues.
        """
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        
        if not pyproject_path.exists():
            pytest.skip("pyproject.toml not found")
        
        try:
            import tomli
        except ImportError:
            pytest.skip("tomli not available for TOML parsing")
        
        with open(pyproject_path, 'rb') as f:
            config = tomli.load(f)
        
        pytest_config = config.get('tool', {}).get('pytest', {}).get('ini_options', {})
        
        if not pytest_config:
            pytest.fail("No pytest.ini_options found in pyproject.toml")
        
        # Check for conflicting or problematic settings
        issues = []
        
        # Check for deprecated settings
        deprecated_settings = ['collect_ignore', 'collect_ignore_glob']
        for setting in deprecated_settings:
            if setting in pytest_config:
                issues.append(f"Deprecated setting '{setting}' found")
        
        # Check for conflicting timeout settings
        addopts = pytest_config.get('addopts', [])
        if isinstance(addopts, list):
            timeout_opts = [opt for opt in addopts if '--timeout=' in str(opt)]
            if len(timeout_opts) > 1:
                issues.append(f"Multiple timeout options: {timeout_opts}")
        
        # Check for conflicting import modes
        import_mode = pytest_config.get('import_mode')
        if import_mode and addopts:
            import_opts = [opt for opt in addopts if '--import-mode=' in str(opt)]
            if import_opts and import_mode:
                issues.append(f"Import mode set in both ini_options and addopts")
        
        if issues:
            pytest.fail(
                f"Configuration issues found in pyproject.toml:\n" +
                "\n".join(f"  - {issue}" for issue in issues)
            )
        
        assert True, "pyproject.toml pytest configuration validated"
    
    def test_phase2_config_file_precedence(self):
        """PHASE 2: Test pytest configuration file precedence conflicts."""
        project_root = Path(__file__).parent.parent.parent
        
        # Check for multiple pytest config files that could conflict
        config_files = {
            'pytest.ini': project_root / 'pytest.ini',
            'pyproject.toml': project_root / 'pyproject.toml', 
            'setup.cfg': project_root / 'setup.cfg',
            'tox.ini': project_root / 'tox.ini'
        }
        
        existing_configs = [
            name for name, path in config_files.items() 
            if path.exists() and self._has_pytest_config(path, name)
        ]
        
        if len(existing_configs) > 1:
            pytest.fail(
                f"Multiple pytest configuration files found: {existing_configs}. "
                f"This can cause configuration precedence conflicts. "
                f"Pytest uses the first one it finds in order: pytest.ini, pyproject.toml, tox.ini, setup.cfg"
            )
        
        assert len(existing_configs) == 1, f"Single pytest config file confirmed: {existing_configs}"
    
    def _has_pytest_config(self, path: Path, filename: str) -> bool:
        """Check if file contains pytest configuration."""
        try:
            content = path.read_text()
            
            if filename == 'pytest.ini':
                return '[pytest]' in content or '[tool:pytest]' in content
            elif filename == 'pyproject.toml':
                return '[tool.pytest' in content
            elif filename in ['setup.cfg', 'tox.ini']:
                return '[tool:pytest]' in content or '[pytest]' in content
                
        except Exception:
            return False
        
        return False


class TestCommandLineOptions:
    """Test command-line option management and conflicts."""
    
    def test_phase2_option_registration_analysis(self):
        """PHASE 2: Analyze option registration to find conflicts.
        
        This test should FAIL initially, showing the duplicate option issue.
        """
        # Get all pytest option definitions in the codebase
        project_root = Path(__file__).parent.parent.parent
        
        option_definitions = {}
        
        # Search for pytest_addoption functions
        python_files = list(project_root.rglob("*.py"))
        
        for py_file in python_files:
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            try:
                content = py_file.read_text()
                
                if 'def pytest_addoption' in content:
                    # Extract option names from this file
                    import re
                    
                    # Find addoption calls
                    option_pattern = r'addoption\s*\(\s*["\']([^"\']+)["\']'
                    options = re.findall(option_pattern, content)
                    
                    for option in options:
                        if option not in option_definitions:
                            option_definitions[option] = []
                        option_definitions[option].append(str(py_file))
                        
            except Exception:
                continue
        
        # Find duplicate option definitions
        duplicates = {
            option: files for option, files in option_definitions.items()
            if len(files) > 1
        }
        
        if duplicates:
            duplicate_details = []
            for option, files in duplicates.items():
                duplicate_details.append(f"  {option}: defined in {len(files)} files")
                for file_path in files:
                    duplicate_details.append(f"    - {file_path}")
            
            pytest.fail(
                f"Duplicate pytest option definitions found:\n" +
                "\n".join(duplicate_details) +
                f"\n\nTotal options analyzed: {len(option_definitions)}"
            )
        
        assert True, f"No duplicate options found among {len(option_definitions)} total options"
    
    def test_phase2_specific_analyze_service_deps_conflict(self):
        """PHASE 2: Test the specific --analyze-service-deps option conflict.
        
        This is the exact issue reported in #519.
        """
        project_root = Path(__file__).parent.parent.parent
        
        # Find all files that define --analyze-service-deps
        files_with_option = []
        
        python_files = list(project_root.rglob("*.py"))
        for py_file in python_files:
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            try:
                content = py_file.read_text()
                if '--analyze-service-deps' in content:
                    files_with_option.append(str(py_file))
            except Exception:
                continue
        
        if len(files_with_option) > 1:
            pytest.fail(
                f"Multiple definitions of --analyze-service-deps found:\n" +
                "\n".join(f"  - {file}" for file in files_with_option) +
                f"\n\nThis is the exact conflict causing Issue #519"
            )
        elif len(files_with_option) == 0:
            pytest.fail("No definition of --analyze-service-deps found, but conflict was reported")
        
        # If exactly one file found, check if it's being imported multiple ways
        option_file = Path(files_with_option[0])
        
        # Check if this file is imported via wildcard in conftest.py
        main_conftest = project_root / "tests" / "conftest.py"
        if main_conftest.exists():
            conftest_content = main_conftest.read_text()
            
            # Check for wildcard import of the option-defining module
            module_name = option_file.stem  # filename without extension
            wildcard_pattern = f"from {option_file.parent.name}.{module_name} import *"
            
            if wildcard_pattern in conftest_content.replace('/', '.'):
                pytest.fail(
                    f"Found wildcard import causing duplicate registration:\n"
                    f"  Option defined in: {option_file}\n"
                    f"  Wildcard imported in: {main_conftest}\n"
                    f"  This causes pytest to register the option twice"
                )
        
        assert True, f"Single definition of --analyze-service-deps found in {files_with_option[0]}"


class TestPluginLoadingSequence:
    """Test the plugin loading sequence and conflicts."""
    
    def test_phase2_plugin_discovery_vs_explicit_import(self):
        """PHASE 2: Test plugin auto-discovery vs explicit import conflicts.
        
        When pytest auto-discovers plugins AND they're explicitly imported,
        hooks and options get registered multiple times.
        """
        # Run pytest with detailed plugin information
        cmd = [
            sys.executable, "-m", "pytest", 
            "--trace-config",
            "--collect-only",
            "-v",
            str(Path(__file__).parent.parent.parent / "tests" / "mission_critical")
        ]
        
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout + result.stderr
        
        # Look for plugin loading information
        plugin_loads = []
        for line in output.split('\n'):
            if 'plugin' in line.lower() and ('load' in line.lower() or 'register' in line.lower()):
                plugin_loads.append(line.strip())
        
        # Look for our specific problematic plugin
        no_docker_plugin_loads = [
            line for line in plugin_loads 
            if 'no_docker' in line.lower() or 'pytest_no_docker_plugin' in line
        ]
        
        if len(no_docker_plugin_loads) > 1:
            pytest.fail(
                f"Plugin loaded multiple times:\n" +
                "\n".join(f"  {line}" for line in no_docker_plugin_loads) +
                f"\n\nThis indicates both auto-discovery and explicit import"
            )
        
        # If we can't detect multiple loads, check the error output
        if result.returncode != 0 and any(keyword in output.lower() for keyword in [
            "already added", "conflict", "duplicate"
        ]):
            pytest.fail(
                f"Plugin loading conflict detected in output:\n{output}"
            )
        
        assert True, f"Plugin loading sequence analyzed. Return code: {result.returncode}"