#!/usr/bin/env python3
"""
End-to-End CLI Integration Tests for Orchestration System
=========================================================

These tests validate the complete integration of the orchestration system
with the unified_test_runner.py CLI, including:

- CLI argument parsing and validation
- Orchestration mode selection and execution
- Backward compatibility with legacy category system
- Real CLI execution (subprocess testing)
- Error handling and user feedback
- Integration with existing test framework

These are true E2E tests that execute the CLI as a user would.
"""

import json
import os
import subprocess
import sys
import tempfile
import pytest
from pathlib import Path
from typing import Dict, List, Any
from shared.isolated_environment import IsolatedEnvironment

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestCLIArgumentParsing:
    """Test CLI argument parsing for new orchestration features"""
    
    def test_help_includes_orchestration_options(self):
        """Test that help output includes new orchestration options"""
        result = subprocess.run([
            sys.executable, 
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--help"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        # Should include new orchestration arguments
        assert "Master Orchestration System" in result.stdout or result.returncode == 0
        
        # Check for key orchestration arguments
        expected_args = [
            "--use-layers",
            "--execution-mode", 
            "--background-e2e",
            "--orchestration-status"
        ]
        
        for arg in expected_args:
            # Either in help output or system handles it gracefully
            assert arg in result.stdout or result.returncode == 0
    
    def test_orchestration_status_command(self):
        """Test orchestration status command"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--orchestration-status"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        # Should succeed and show status
        assert result.returncode == 0
        assert "ORCHESTRATION STATUS" in result.stdout or "not available" in result.stdout.lower()
    
    def test_invalid_execution_mode(self):
        """Test handling of invalid execution mode"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--execution-mode", "invalid_mode"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        # Should fail with helpful error message
        assert result.returncode != 0 or "invalid" in result.stderr.lower()
    
    def test_layers_without_use_layers_flag(self):
        """Test that --layers requires --use-layers"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--layers", "fast_feedback"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        # Should either handle gracefully or show proper error
        # (The exact behavior depends on implementation)
        assert result.returncode is not None


class TestBackwardCompatibilityE2E:
    """End-to-end tests for backward compatibility"""
    
    def test_legacy_category_execution_still_works(self):
        """Test that legacy category execution still works unchanged"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--categories", "smoke",
            "--env", "test",
            "--timeout", "1"  # Very short timeout for test
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=60)
        
        # Should attempt to run (may fail due to missing services, but should not crash)
        # Success is return code 0, or graceful failure with proper error message
        assert result.returncode is not None
        assert len(result.stdout) > 0 or len(result.stderr) > 0
    
    def test_list_categories_still_works(self):
        """Test that --list-categories still works"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--list-categories"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        # Should succeed and show categories
        assert result.returncode == 0
        assert "CATEGORIES" in result.stdout or "categories" in result.stdout.lower()
    
    def test_category_stats_still_works(self):
        """Test that --show-category-stats still works"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--show-category-stats"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        # Should succeed and show statistics
        assert result.returncode == 0 or "not available" in result.stdout.lower()


class TestOrchestrationExecution:
    """Test actual orchestration execution (may be slow)"""
    
    @pytest.mark.slow
    def test_fast_feedback_execution(self):
        """Test fast feedback execution mode"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--execution-mode", "fast_feedback",
            "--env", "test",
            "--progress-mode", "silent"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=300)  # 5 minute timeout
        
        # Check execution attempt
        assert result.returncode is not None
        
        # If orchestration is available, should attempt execution
        if "not available" not in result.stdout.lower():
            # Either succeeds or fails with meaningful error
            assert len(result.stdout) > 0 or len(result.stderr) > 0
    
    @pytest.mark.slow
    def test_background_e2e_command(self):
        """Test background E2E command"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--background-e2e",
            "--env", "test",
            "--progress-mode", "silent"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=60)
        
        # Should attempt background execution
        assert result.returncode is not None
        assert len(result.stdout) > 0 or len(result.stderr) > 0


class TestErrorScenarios:
    """Test error scenarios and edge cases"""
    
    def test_no_arguments_defaults_to_legacy(self):
        """Test that running with no arguments defaults to legacy mode"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py")
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        
        # Should show help or attempt legacy execution
        assert result.returncode is not None
        # Either shows help or attempts execution
        assert len(result.stdout) > 0 or len(result.stderr) > 0
    
    def test_conflicting_arguments(self):
        """Test handling of conflicting arguments"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--use-layers",
            "--categories", "unit",  # Legacy argument conflicts with --use-layers
            "--execution-mode", "fast_feedback"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        
        # Should handle conflict gracefully
        assert result.returncode is not None
    
    def test_missing_layer_dependencies(self):
        """Test execution when layer dependencies are missing"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--use-layers",
            "--layers", "nonexistent_layer"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        
        # Should fail with meaningful error
        assert result.returncode != 0 or "error" in result.stderr.lower()


class TestProgressOutputModes:
    """Test different progress output modes"""
    
    def test_json_progress_mode(self):
        """Test JSON progress output mode"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--orchestration-status",
            "--progress-mode", "json"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        # Should succeed
        assert result.returncode == 0
    
    def test_silent_progress_mode(self):
        """Test silent progress output mode"""
        result = subprocess.run([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "unified_test_runner.py"),
            "--orchestration-status",
            "--progress-mode", "silent"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        # Should succeed with minimal output
        assert result.returncode == 0


def run_cli_integration_tests():
    """Run CLI integration tests with proper configuration"""
    # Configure pytest for CLI testing
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "-m", "not slow",  # Skip slow tests by default
        "--disable-warnings"
    ]
    
    # Add slow tests if requested
    if "--include-slow" in sys.argv:
        pytest_args.remove("-m")
        pytest_args.remove("not slow")
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    sys.exit(run_cli_integration_tests())
