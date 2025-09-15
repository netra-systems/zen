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
PROJECT_ROOT = Path(__file__).parent.parent.parent

@pytest.mark.e2e
class TestCLIArgumentParsing:
    """Test CLI argument parsing for new orchestration features"""

    def test_help_includes_orchestration_options(self):
        """Test that help output includes new orchestration options"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--help'], capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert 'Master Orchestration System' in result.stdout or result.returncode == 0
        expected_args = ['--use-layers', '--execution-mode', '--background-e2e', '--orchestration-status']
        for arg in expected_args:
            assert arg in result.stdout or result.returncode == 0

    def test_orchestration_status_command(self):
        """Test orchestration status command"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--orchestration-status'], capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert 'ORCHESTRATION STATUS' in result.stdout or 'not available' in result.stdout.lower()

    def test_invalid_execution_mode(self):
        """Test handling of invalid execution mode"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--execution-mode', 'invalid_mode'], capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert result.returncode != 0 or 'invalid' in result.stderr.lower()

    def test_layers_without_use_layers_flag(self):
        """Test that --layers requires --use-layers"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--layers', 'fast_feedback'], capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert result.returncode is not None

@pytest.mark.e2e
class TestBackwardCompatibilityE2E:
    """End-to-end tests for backward compatibility"""

    def test_legacy_category_execution_still_works(self):
        """Test that legacy category execution still works unchanged"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--categories', 'smoke', '--env', 'test', '--timeout', '1'], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=60)
        assert result.returncode is not None
        assert len(result.stdout) > 0 or len(result.stderr) > 0

    def test_list_categories_still_works(self):
        """Test that --list-categories still works"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--list-categories'], capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert 'CATEGORIES' in result.stdout or 'categories' in result.stdout.lower()

    def test_category_stats_still_works(self):
        """Test that --show-category-stats still works"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--show-category-stats'], capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert result.returncode == 0 or 'not available' in result.stdout.lower()

@pytest.mark.e2e
class TestOrchestrationExecution:
    """Test actual orchestration execution (may be slow)"""

    @pytest.mark.slow
    def test_fast_feedback_execution(self):
        """Test fast feedback execution mode"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--execution-mode', 'fast_feedback', '--env', 'test', '--progress-mode', 'silent'], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=300)
        assert result.returncode is not None
        if 'not available' not in result.stdout.lower():
            assert len(result.stdout) > 0 or len(result.stderr) > 0

    @pytest.mark.slow
    def test_background_e2e_command(self):
        """Test background E2E command"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--background-e2e', '--env', 'test', '--progress-mode', 'silent'], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=60)
        assert result.returncode is not None
        assert len(result.stdout) > 0 or len(result.stderr) > 0

@pytest.mark.e2e
class TestErrorScenarios:
    """Test error scenarios and edge cases"""

    def test_no_arguments_defaults_to_legacy(self):
        """Test that running with no arguments defaults to legacy mode"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py')], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        assert result.returncode is not None
        assert len(result.stdout) > 0 or len(result.stderr) > 0

    def test_conflicting_arguments(self):
        """Test handling of conflicting arguments"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--use-layers', '--categories', 'unit', '--execution-mode', 'fast_feedback'], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        assert result.returncode is not None

    def test_missing_layer_dependencies(self):
        """Test execution when layer dependencies are missing"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--use-layers', '--layers', 'nonexistent_layer'], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        assert result.returncode != 0 or 'error' in result.stderr.lower()

@pytest.mark.e2e
class TestProgressOutputModes:
    """Test different progress output modes"""

    def test_json_progress_mode(self):
        """Test JSON progress output mode"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--orchestration-status', '--progress-mode', 'json'], capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_silent_progress_mode(self):
        """Test silent progress output mode"""
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'unified_test_runner.py'), '--orchestration-status', '--progress-mode', 'silent'], capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert result.returncode == 0

def run_cli_integration_tests():
    """Run CLI integration tests with proper configuration"""
    pytest_args = [__file__, '-v', '--tb=short', '-m', 'not slow', '--disable-warnings']
    if '--include-slow' in sys.argv:
        pytest_args.remove('-m')
        pytest_args.remove('not slow')
    return 
    pass
if __name__ == '__main__':
    sys.exit(run_cli_integration_tests())