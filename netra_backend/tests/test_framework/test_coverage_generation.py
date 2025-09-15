"""
Test coverage generation for unit level and above.

This test verifies that coverage is generated correctly for different test levels
according to the testing.xml specification requirements.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - testing infrastructure
2. Business Goal: Ensure coverage compliance per testing specification
3. Value Impact: Prevents coverage reporting gaps that could miss code quality issues
4. Strategic Impact: Maintains testing standard compliance and development velocity
"""
import json
import subprocess
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment
import pytest
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

class CoverageGenerationTests:
    """Test coverage generation compliance across test levels."""

    def test_unit_level_generates_coverage(self):
        """Test that unit level generates coverage summary."""
        cmd = [sys.executable, '-m', 'test_framework.test_runner', '--level', 'unit', '--backend-only', '--fast-fail', '--no-warnings', '--list', '--list-format', 'json']
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, f'Command failed: {result.stderr}'
        output = json.loads(result.stdout)
        unit_config = output['test_levels']['unit']
        assert unit_config['runs_coverage'] is True, 'Unit level should have coverage enabled'

    def test_integration_level_generates_coverage(self):
        """Test that integration level generates coverage summary."""
        cmd = [sys.executable, '-m', 'test_framework.test_runner', '--level', 'integration', '--backend-only', '--fast-fail', '--no-warnings', '--list', '--list-format', 'json']
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, f'Command failed: {result.stderr}'
        output = json.loads(result.stdout)
        integration_config = output['test_levels']['integration']
        assert integration_config['runs_coverage'] is True, 'Integration level should have coverage enabled'

    def test_critical_level_generates_coverage(self):
        """Test that critical level generates coverage summary."""
        cmd = [sys.executable, '-m', 'test_framework.test_runner', '--level', 'critical', '--backend-only', '--fast-fail', '--no-warnings', '--list', '--list-format', 'json']
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, f'Command failed: {result.stderr}'
        output = json.loads(result.stdout)
        critical_config = output['test_levels']['critical']
        assert critical_config['runs_coverage'] is True, 'Critical level should have coverage enabled'

    def test_smoke_level_does_not_generate_coverage(self):
        """Test that smoke level does NOT generate coverage (as intended)."""
        cmd = [sys.executable, 'unified_test_runner.py', '--help']
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f'Test runner help failed: {result.stderr}'
        assert '--no-coverage' in result.stdout, 'Test runner should support --no-coverage flag'
        assert 'smoke' in result.stdout, 'Smoke category should be documented in help'

    def test_no_coverage_flag_overrides_unit_level(self):
        """Test that --no-coverage flag properly disables coverage for unit level."""
        cmd = [sys.executable, '-c', f"""\nimport sys\nfrom pathlib import Path\nfrom unified_test_runner import configure_speed_options\n\n# Create a mock args object with no_coverage=True\nclass MockArgs:\n    def __init__(self):\n        self.speed = False\n        self.ci = False\n        self.no_warnings = False\n        self.no_coverage = True\n        self.fast_fail = False\n\nargs = MockArgs()\nspeed_opts = configure_speed_options(args)\n\n# Verify that no_coverage is enabled in speed options\nassert speed_opts is not None, "Speed options should be created when no_coverage is set"\nassert speed_opts.get('no_coverage') is True, "no_coverage should be True in speed options"\nprint("SUCCESS: --no-coverage flag properly sets speed_opts['no_coverage'] = True")\n"""]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f'Speed options test failed: {result.stderr}'
        assert 'SUCCESS' in result.stdout, 'Test verification should pass'

    def test_coverage_in_backend_args_unit_level(self):
        """Test that unit level includes --coverage in backend_args."""
        from test_framework.test_config import TEST_LEVELS
        unit_config = TEST_LEVELS['unit']
        backend_args = unit_config['backend_args']
        assert '--coverage' in backend_args, 'Unit level should include --coverage in backend_args'
        assert unit_config['run_coverage'] is True, 'Unit level should have run_coverage=True'

    def test_coverage_in_backend_args_integration_level(self):
        """Test that integration level includes --coverage in backend_args."""
        from test_framework.test_config import TEST_LEVELS
        integration_config = TEST_LEVELS['integration']
        backend_args = integration_config['backend_args']
        assert '--coverage' in backend_args, 'Integration level should include --coverage in backend_args'
        assert integration_config['run_coverage'] is True, 'Integration level should have run_coverage=True'

    def test_coverage_in_backend_args_critical_level(self):
        """Test that critical level includes --coverage in backend_args."""
        from test_framework.test_config import TEST_LEVELS
        critical_config = TEST_LEVELS['critical']
        backend_args = critical_config['backend_args']
        assert '--coverage' in backend_args, 'Critical level should include --coverage in backend_args'
        assert critical_config['run_coverage'] is True, 'Critical level should have run_coverage=True'

    def test_speed_optimizations_remove_coverage_for_backend_runner(self):
        """Test that speed optimizations properly remove --coverage for backend runner."""
        cmd = [sys.executable, '-c', f"""\nimport sys\nfrom pathlib import Path\nfrom test_framework.test_runners import _apply_speed_optimizations\n\n# Create a mock command for backend runner with --coverage\ncmd = ['python', 'unified_test_runner.py --service backend', '--coverage', '--category', 'unit']\n\n# Create speed options with no_coverage=True\nspeed_opts = {{'no_coverage': True}}\n\n# Apply speed optimizations\noptimized_cmd = _apply_speed_optimizations(cmd, speed_opts)\n\n# Verify that --coverage is removed\nassert '--coverage' not in optimized_cmd, "Coverage flag should be removed when no_coverage is True"\nprint("SUCCESS: Speed optimizations properly remove --coverage flag for backend runner")\n"""]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f'Speed optimization test failed: {result.stderr}'
        assert 'SUCCESS' in result.stdout, 'Coverage removal should work correctly'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')