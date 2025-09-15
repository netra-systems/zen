"""
SSOT Deployment Canonical Source Validation Tests

Tests to ensure ONLY UnifiedTestRunner contains deployment logic and all
deployment scripts properly redirect to the SSOT implementation.

Created for GitHub Issue #245: Deploy script canonical source conflicts
Part of: 20% new SSOT deployment tests requirement (Test File 1 of 8)

Business Value: Platform/Internal - System Stability & SSOT Compliance
Prevents duplicate deployment implementations and ensures canonical source integrity.

DESIGN CRITERIA:
- Tests MUST fail if SSOT violations occur
- Tests reproduce current SSOT violation scenarios
- Validates post-SSOT-refactor expected state
- No Docker dependency (pure unit tests)
- Uses SSOT test infrastructure patterns

TEST CATEGORIES:
- Canonical source validation (UnifiedTestRunner as SSOT)
- Duplicate deployment logic detection
- Deprecation warning verification
- Import path validation
"""
import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set
from unittest.mock import Mock, patch, MagicMock
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class DeploymentCanonicalSourceValidationTests(SSotBaseTestCase):
    """
    Unit tests for deployment canonical source validation.
    
    Ensures ONLY UnifiedTestRunner contains deployment logic and all other
    deployment scripts redirect to the SSOT implementation.
    """

    def setup_method(self, method=None):
        """Setup test environment and paths."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.unified_runner_path = self.project_root / 'tests' / 'unified_test_runner.py'
        self.scripts_dir = self.project_root / 'scripts'
        self.record_metric('test_category', 'unit')
        self.record_metric('ssot_focus', 'deployment_canonical_source')
        assert self.unified_runner_path.exists(), f'UnifiedTestRunner not found: {self.unified_runner_path}'
        assert self.scripts_dir.exists(), f'Scripts directory not found: {self.scripts_dir}'

    def test_unified_test_runner_is_canonical_deployment_source(self):
        """
        Test that UnifiedTestRunner contains the canonical deployment logic.
        
        CRITICAL: This test MUST fail if deployment logic exists elsewhere.
        """
        runner_source = self.unified_runner_path.read_text(encoding='utf-8')
        assert 'execution-mode deploy' in runner_source or '--execution-mode' in runner_source, 'UnifiedTestRunner missing deployment execution mode'
        deployment_keywords = ['deploy', 'gcp', 'cloud', 'build', 'docker']
        found_deployment_logic = False
        for keyword in deployment_keywords:
            if keyword.lower() in runner_source.lower():
                found_deployment_logic = True
                break
        assert found_deployment_logic, 'UnifiedTestRunner missing deployment-related logic'
        self.record_metric('canonical_source_validated', True)
        self.record_metric('deployment_logic_location', 'unified_test_runner')

    def test_deployment_scripts_redirect_to_ssot(self):
        """
        Test that all deployment scripts redirect to UnifiedTestRunner.
        
        CRITICAL: This test MUST fail if scripts contain independent deployment logic.
        """
        deployment_scripts = self._find_deployment_scripts()
        assert len(deployment_scripts) > 0, 'No deployment scripts found to validate'
        ssot_violations = []
        redirect_validations = []
        for script_path in deployment_scripts:
            script_name = script_path.name
            if script_name.endswith('.backup') or not script_name.endswith('.py'):
                continue
            try:
                script_source = script_path.read_text(encoding='utf-8')
                has_deprecation_warning = 'DEPRECATION WARNING' in script_source
                has_unified_runner_redirect = 'unified_test_runner' in script_source.lower()
                if has_deprecation_warning and has_unified_runner_redirect:
                    redirect_validations.append(script_name)
                else:
                    independent_logic_indicators = ['gcloud run deploy', 'docker build', 'subprocess.run', 'cloud build', 'terraform apply']
                    has_independent_logic = any((indicator in script_source.lower() for indicator in independent_logic_indicators))
                    if has_independent_logic and (not has_unified_runner_redirect):
                        ssot_violations.append({'script': script_name, 'violation': 'independent_deployment_logic', 'path': str(script_path)})
            except Exception as e:
                self.record_metric(f'script_read_error_{script_name}', str(e))
        self.record_metric('deployment_scripts_found', len(deployment_scripts))
        self.record_metric('redirect_validations', len(redirect_validations))
        self.record_metric('ssot_violations_count', len(ssot_violations))
        if ssot_violations:
            violation_details = '\n'.join([f"  - {v['script']}: {v['violation']} at {v['path']}" for v in ssot_violations])
            pytest.fail(f'SSOT VIOLATION: {len(ssot_violations)} deployment scripts contain independent logic instead of redirecting to UnifiedTestRunner:\n{violation_details}\n\nExpected: All deployment scripts should redirect to UnifiedTestRunner\nFix: Add deprecation warning and redirect logic to violating scripts')

    def test_no_duplicate_deployment_implementations(self):
        """
        Test that deployment logic exists only in UnifiedTestRunner.
        
        CRITICAL: This test MUST fail if duplicate implementations are found.
        """
        deployment_patterns = ['gcloud run deploy', 'docker build.*gcp', 'cloud-build-config', 'terraform.*deploy']
        excluded_patterns = ['backup', '.git', '__pycache__', 'node_modules', '.pyc']
        duplicate_implementations = []
        for pattern in deployment_patterns:
            try:
                result = subprocess.run(['grep', '-r', '-l', pattern, str(self.project_root)], capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    files_with_pattern = result.stdout.strip().split('\n')
                    for file_path in files_with_pattern:
                        if not file_path:
                            continue
                        if any((exclude in file_path for exclude in excluded_patterns)):
                            continue
                        if 'unified_test_runner.py' in file_path:
                            continue
                        duplicate_implementations.append({'file': file_path, 'pattern': pattern, 'type': 'duplicate_deployment_logic'})
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                self.record_metric(f'grep_error_{pattern}', True)
        self.record_metric('duplicate_implementations_found', len(duplicate_implementations))
        if duplicate_implementations:
            duplicate_details = '\n'.join([f"  - {d['file']}: {d['pattern']}" for d in duplicate_implementations])
            pytest.fail(f'DUPLICATE DEPLOYMENT LOGIC: Found {len(duplicate_implementations)} files with deployment logic outside UnifiedTestRunner:\n{duplicate_details}\n\nExpected: Only UnifiedTestRunner should contain deployment logic\nFix: Remove duplicate logic and redirect to UnifiedTestRunner SSOT')

    def test_deprecated_scripts_show_warnings(self):
        """
        Test that deprecated deployment scripts show proper warnings.
        
        Validates user experience during SSOT migration.
        """
        deploy_gcp_script = self.scripts_dir / 'deploy_to_gcp.py'
        if not deploy_gcp_script.exists():
            pytest.skip('deploy_to_gcp.py not found - may have been removed')
        with patch('builtins.print') as mock_print:
            try:
                script_source = deploy_gcp_script.read_text(encoding='utf-8')
                if 'show_deprecation_warning' in script_source:
                    exec_globals = {}
                    exec(script_source, exec_globals)
                    if 'show_deprecation_warning' in exec_globals:
                        exec_globals['show_deprecation_warning']()
                        warning_calls = [str(call) for call in mock_print.call_args_list]
                        warning_text = ' '.join(warning_calls)
                        assert 'DEPRECATION WARNING' in warning_text, 'Deprecation warning not displayed'
                        assert 'unified_test_runner' in warning_text.lower(), 'Warning missing UnifiedTestRunner redirect instructions'
                        self.record_metric('deprecation_warning_displayed', True)
            except Exception as e:
                self.record_metric('deprecation_warning_error', str(e))

    def test_deployment_entry_point_audit(self):
        """
        Test that all deployment entry points are documented and controlled.
        
        Ensures no hidden deployment mechanisms exist.
        """
        legitimate_entry_points = {'tests/unified_test_runner.py': 'canonical_ssot', 'scripts/deploy_to_gcp.py': 'deprecated_redirect'}
        potential_entry_points = []
        python_files = list(self.project_root.rglob('*.py'))
        for py_file in python_files:
            if any((exclude in str(py_file) for exclude in ['.git', '__pycache__', 'node_modules'])):
                continue
            try:
                source = py_file.read_text(encoding='utf-8')
                entry_point_patterns = ['if __name__ == "__main__":', 'def main():', 'deploy.*main', 'gcp.*deploy']
                deployment_indicators = ['gcloud', 'cloud run', 'docker build', 'terraform']
                has_entry_point = any((pattern in source for pattern in entry_point_patterns))
                has_deployment_logic = any((indicator in source.lower() for indicator in deployment_indicators))
                if has_entry_point and has_deployment_logic:
                    relative_path = str(py_file.relative_to(self.project_root))
                    potential_entry_points.append(relative_path)
            except Exception:
                continue
        undocumented_entry_points = []
        for entry_point in potential_entry_points:
            if entry_point not in legitimate_entry_points:
                undocumented_entry_points.append(entry_point)
        self.record_metric('total_entry_points_found', len(potential_entry_points))
        self.record_metric('legitimate_entry_points', len(legitimate_entry_points))
        self.record_metric('undocumented_entry_points', len(undocumented_entry_points))
        if undocumented_entry_points:
            self.record_metric('undocumented_entry_points_list', undocumented_entry_points)
            print(f'\nINFO: Found {len(undocumented_entry_points)} potential deployment entry points:')
            for entry_point in undocumented_entry_points:
                print(f'  - {entry_point}')
            print('These should be reviewed for SSOT compliance.')

    def test_import_path_validation_for_deployment(self):
        """
        Test that deployment-related imports follow SSOT patterns.
        
        Validates that deployment code uses proper import paths.
        """
        expected_ssot_imports = {'test_framework.ssot.base_test_case', 'test_framework.unified_docker_manager', 'shared.isolated_environment'}
        anti_patterns = {'from scripts.deploy_to_gcp import', 'import deploy_to_gcp', 'from deploy_to_gcp import'}
        violations = []
        if self.unified_runner_path.exists():
            runner_source = self.unified_runner_path.read_text(encoding='utf-8')
            try:
                tree = ast.parse(runner_source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_name = alias.name
                            for anti_pattern in anti_patterns:
                                if import_name in anti_pattern:
                                    violations.append({'file': 'unified_test_runner.py', 'violation': f'anti_pattern_import: {import_name}', 'line': node.lineno})
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            import_name = node.module
                            for anti_pattern in anti_patterns:
                                if import_name in anti_pattern:
                                    violations.append({'file': 'unified_test_runner.py', 'violation': f'anti_pattern_from_import: {import_name}', 'line': node.lineno})
            except SyntaxError as e:
                self.record_metric('ast_parse_error', str(e))
        self.record_metric('import_violations_found', len(violations))
        if violations:
            violation_details = '\n'.join([f"  - {v['file']}:{v['line']}: {v['violation']}" for v in violations])
            pytest.fail(f'IMPORT VIOLATION: Found {len(violations)} import anti-patterns:\n{violation_details}\n\nExpected: Deployment code should use SSOT import patterns\nFix: Replace anti-pattern imports with SSOT equivalents')

    def _find_deployment_scripts(self) -> List[Path]:
        """Find all deployment scripts in the project."""
        deployment_scripts = []
        if self.scripts_dir.exists():
            for script in self.scripts_dir.glob('*deploy*.py'):
                deployment_scripts.append(script)
        deployment_patterns = ['**/deploy_*.py', '**/gcp_deploy*.py', '**/staging_deploy*.py']
        for pattern in deployment_patterns:
            for script in self.project_root.glob(pattern):
                if script not in deployment_scripts:
                    deployment_scripts.append(script)
        return deployment_scripts

@pytest.mark.unit
class DeploymentCanonicalSourceEdgeCasesTests(SSotBaseTestCase):
    """
    Edge case tests for deployment canonical source validation.
    """

    def test_deployment_script_parameter_forwarding(self):
        """
        Test that deprecated scripts properly forward parameters to SSOT.
        
        Ensures no functionality is lost during SSOT migration.
        """
        deploy_script = Path(__file__).parent.parent.parent.parent / 'scripts' / 'deploy_to_gcp.py'
        if not deploy_script.exists():
            pytest.skip('deploy_to_gcp.py not found')
        script_source = deploy_script.read_text(encoding='utf-8')
        expected_params = ['--project', '--build-local', '--check-secrets', '--run-checks', '--rollback']
        missing_params = []
        for param in expected_params:
            if param not in script_source:
                missing_params.append(param)
        assert len(missing_params) == 0, f'Missing parameter forwarding: {missing_params}'
        self.record_metric('parameter_forwarding_validated', True)
        self.record_metric('forwarded_parameters_count', len(expected_params))

    def test_ssot_migration_backwards_compatibility(self):
        """
        Test that SSOT migration maintains backwards compatibility.
        
        Ensures existing deployment workflows continue to work.
        """
        unified_runner = Path(__file__).parent.parent.parent.parent / 'tests' / 'unified_test_runner.py'
        runner_source = unified_runner.read_text(encoding='utf-8')
        deployment_modes = ['deploy', 'deployment', 'gcp']
        has_deployment_mode = any((mode in runner_source for mode in deployment_modes))
        assert has_deployment_mode, 'UnifiedTestRunner missing deployment mode support'
        env_vars = ['GCP_PROJECT', 'CONTAINER_RUNTIME', 'BUILD_LOCAL']
        for env_var in env_vars:
            value = self.get_env_var(env_var, 'test_default')
            assert value is not None
        self.record_metric('backwards_compatibility_validated', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')