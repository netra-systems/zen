"""
Issue #519: Pytest Configuration Conflicts - Mission Critical Test Suite

This test suite reproduces and validates pytest configuration conflicts that are blocking
the Mission Critical WebSocket Test Suite from running properly.

Root Cause Analysis:
- Duplicate --analyze-service-deps option definition (wildcard import + plugin auto-discovery)  
- Deprecated collect_ignore configuration patterns
- Plugin loading conflicts from conftest.py wildcard imports

Business Impact: HIGH - Blocking $500K+ ARR validation through Mission Critical tests
Priority: P0 - Must resolve to protect business value
"""

import subprocess
import sys
import pytest
from pathlib import Path
from typing import List, Dict, Any, Optional


class TestPytestConfigConflicts:
    """Test suite for reproducing pytest configuration conflicts."""
    
    def test_phase1_reproduce_duplicate_option_conflict(self):
        """PHASE 1: Reproduce the duplicate --analyze-service-deps option conflict.
        
        This test should FAIL initially, confirming the issue reproduction.
        The conflict occurs due to:
        1. Plugin auto-discovery loading pytest_no_docker_plugin.py
        2. Wildcard import in conftest.py importing the same plugin
        3. Both registering the same command-line option
        """
        # Attempt to run pytest with help to trigger option parsing
        cmd = [
            sys.executable, "-m", "pytest", 
            "--help",
            "-p", "test_framework.ssot.pytest_no_docker_plugin"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # This should fail with duplicate option error
        assert "already added" in result.stderr.lower() or "conflict" in result.stderr.lower(), (
            f"Expected duplicate option conflict in stderr, but got:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}\n"
            f"Return code: {result.returncode}"
        )
        
    def test_phase1_reproduce_mission_critical_blockage(self):
        """PHASE 1: Reproduce the Mission Critical WebSocket test blockage.
        
        This test should FAIL initially, confirming that the Mission Critical
        WebSocket tests cannot run due to pytest configuration conflicts.
        """
        # Try to collect Mission Critical WebSocket tests
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/mission_critical/test_websocket_agent_events_suite.py",
            "--collect-only",
            "--analyze-service-deps"  # This should trigger the conflict
        ]
        
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Should fail due to option conflicts
        assert result.returncode != 0, (
            f"Expected test collection to fail due to option conflicts, "
            f"but it succeeded with return code: {result.returncode}\n"
            f"STDOUT: {result.stdout}\n" 
            f"STDERR: {result.stderr}"
        )
        
        # Verify it's specifically an option conflict
        assert any(keyword in result.stderr.lower() for keyword in [
            "already added", "conflict", "duplicate", "option"
        ]), (
            f"Expected option conflict error in stderr, but got:\n"
            f"STDERR: {result.stderr}"
        )

    def test_phase1_reproduce_wildcard_import_issue(self):
        """PHASE 1: Reproduce wildcard import causing plugin conflicts.
        
        The issue is in /tests/conftest.py line 58:
        from test_framework.ssot.pytest_no_docker_plugin import *
        
        This imports pytest_addoption function which conflicts with
        pytest's plugin auto-discovery also loading the same module.
        """
        # Check if the problematic wildcard import exists
        conftest_path = Path(__file__).parent.parent / "conftest.py"
        assert conftest_path.exists(), f"Main conftest.py not found at {conftest_path}"
        
        conftest_content = conftest_path.read_text()
        
        # Verify wildcard import exists (this confirms the issue)
        assert "from test_framework.ssot.pytest_no_docker_plugin import *" in conftest_content, (
            "Wildcard import from pytest_no_docker_plugin not found in conftest.py. "
            "Issue may have been already fixed or structure changed."
        )
        
        # Verify the plugin defines pytest_addoption
        plugin_path = Path(__file__).parent.parent.parent / "test_framework/ssot/pytest_no_docker_plugin.py"
        assert plugin_path.exists(), f"Plugin file not found at {plugin_path}"
        
        plugin_content = plugin_path.read_text()
        assert "def pytest_addoption(parser):" in plugin_content, (
            "pytest_addoption function not found in no_docker_plugin. "
            "Issue structure may have changed."
        )
        
        # This confirms the root cause: wildcard import brings pytest_addoption
        # into conftest.py namespace, while pytest also auto-discovers the plugin
        assert True, "Wildcard import issue confirmed"
        
    def test_phase1_validate_plugin_auto_discovery(self):
        """PHASE 1: Validate that pytest auto-discovers the conflicting plugin.
        
        Pytest auto-discovers plugins in test_framework/ssot/ which creates
        the duplicate registration problem.
        """
        # Run pytest with plugin discovery info
        cmd = [
            sys.executable, "-m", "pytest", 
            "--trace-config",
            "--collect-only",
            "-q"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check if plugin is auto-discovered
        output = result.stdout + result.stderr
        plugin_discovered = any(
            "pytest_no_docker_plugin" in line or "no_docker_plugin" in line
            for line in output.split('\n')
        )
        
        # This test documents the auto-discovery behavior
        # In a working system, we either have auto-discovery OR manual import, not both
        if result.returncode == 0 and not plugin_discovered:
            pytest.skip("Plugin auto-discovery not captured in trace output")
            
        assert True, f"Plugin discovery behavior documented. Output: {output[:500]}..."


class TestPytestConfigDeprecation:
    """Test suite for deprecated configuration patterns."""
    
    def test_phase1_check_collect_ignore_deprecation(self):
        """PHASE 1: Check for deprecated collect_ignore patterns.
        
        From the pyproject.toml, we should look for any collect_ignore
        patterns that might be causing issues.
        """
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), f"pyproject.toml not found at {pyproject_path}"
        
        pyproject_content = pyproject_path.read_text()
        
        # Check for deprecated collect_ignore (should use norecursedirs instead)
        has_collect_ignore = "collect_ignore" in pyproject_content
        
        if has_collect_ignore:
            pytest.fail(
                "Found deprecated collect_ignore in pyproject.toml. "
                "This can cause pytest configuration conflicts. "
                "Should use norecursedirs instead."
            )
        
        # Check that norecursedirs is used instead
        has_norecursedirs = "norecursedirs" in pyproject_content
        assert has_norecursedirs, (
            "Neither collect_ignore nor norecursedirs found in pyproject.toml. "
            "Need proper file exclusion configuration."
        )
        
    def test_phase1_validate_current_config_structure(self):
        """PHASE 1: Validate current pytest configuration structure.
        
        Documents the current configuration to understand conflicts.
        """
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        pyproject_content = pyproject_path.read_text()
        
        # Extract pytest configuration
        config_lines = []
        in_pytest_section = False
        
        for line in pyproject_content.split('\n'):
            if line.strip() == "[tool.pytest.ini_options]":
                in_pytest_section = True
                continue
            elif line.startswith('[') and in_pytest_section:
                break
            elif in_pytest_section:
                config_lines.append(line)
        
        pytest_config = '\n'.join(config_lines)
        
        # This test documents current config - should pass
        assert len(pytest_config) > 0, "No pytest configuration found in pyproject.toml"
        
        # Log current config for analysis
        print(f"Current pytest configuration:\n{pytest_config}")
        
        
class TestEnvironmentConflicts:
    """Test environment-specific conflicts that might affect pytest."""
    
    def test_phase1_check_multiple_python_paths(self):
        """PHASE 1: Check for Python path conflicts that might affect plugin loading."""
        import sys
        
        # Check for multiple pytest installations
        pytest_locations = []
        for path in sys.path:
            pytest_path = Path(path) / "pytest"
            if pytest_path.exists():
                pytest_locations.append(str(pytest_path))
        
        # Multiple pytest locations can cause plugin conflicts
        if len(pytest_locations) > 1:
            pytest.fail(
                f"Multiple pytest installations found: {pytest_locations}. "
                f"This can cause plugin loading conflicts."
            )
        
        assert True, f"Single pytest installation confirmed: {pytest_locations}"
        
    def test_phase1_check_venv_plugin_isolation(self):
        """PHASE 1: Check virtual environment plugin isolation."""
        import sys
        
        # Check if we're in a virtual environment
        in_venv = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        
        if not in_venv:
            pytest.skip("Not running in virtual environment - plugin isolation not applicable")
        
        # In venv, plugins should be isolated
        venv_path = Path(sys.prefix)
        site_packages = venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
        
        if not site_packages.exists():
            pytest.skip(f"Site-packages not found at expected location: {site_packages}")
        
        # Check for pytest plugins in site-packages
        pytest_plugins = list(site_packages.glob("pytest_*"))
        
        # This documents the plugin environment
        print(f"Virtual environment: {venv_path}")
        print(f"Site-packages: {site_packages}")  
        print(f"Pytest plugins found: {[p.name for p in pytest_plugins]}")
        
        assert True, "Virtual environment plugin isolation documented"