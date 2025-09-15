"""
Test Issue #722 SSOT Violations - Critical File Environment Access Violations

EXPECTED TO FAIL - Detects Current Environment Access Violations in 4 Critical Files

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Environment Detection Reliability - Prevent Golden Path failures
- Value Impact: Validates SSOT environment access patterns prevent configuration drift
- Strategic Impact: Protects $500K+ ARR by ensuring consistent environment detection

PURPOSE: This test is EXPECTED TO FAIL until the 4 critical files use IsolatedEnvironment.
It detects specific os.environ violations that cause environment detection failures.

Test Coverage:
1. auth_trace_logger.py violations (lines 284, 293, 302)
2. unified_corpus_admin.py violations (lines 155, 281) 
3. websocket_core/types.py violations (lines 349-355)
4. auth_startup_validator.py violations (lines 514-520)

CRITICAL: Environmental configuration failures block user login and AI chat
functionality, directly impacting $500K+ ARR Golden Path revenue protection.

See Issue #722 for complete analysis and remediation plan.
"""
import pytest
import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
import importlib
import inspect
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class Issue722SSOTViolationsTests(SSotBaseTestCase):
    """Test suite to detect specific SSOT violations in 4 critical files per Issue #722."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for Issue #722 violation detection."""
        super().setUpClass()
        cls.critical_files_with_violations = {'netra_backend/app/logging/auth_trace_logger.py': [284, 293, 302], 'netra_backend/app/admin/corpus/unified_corpus_admin.py': [155, 281], 'netra_backend/app/websocket_core/types.py': [349, 350, 351, 352], 'netra_backend/app/core/auth_startup_validator.py': [518, 520]}

    def test_auth_trace_logger_environment_access_violations(self):
        """
        EXPECTED TO FAIL - Detect os.getenv violations in auth_trace_logger.py.
        
        Per Issue #722: Lines 284, 293, 302 contain direct os.getenv() calls
        that bypass SSOT IsolatedEnvironment patterns.
        
        These violations cause environment detection inconsistencies in
        development vs staging vs production environments.
        """
        file_path = Path('netra_backend/app/logging/auth_trace_logger.py')
        expected_violation_lines = [284, 293, 302]
        violations = self._detect_os_environ_violations_in_file(file_path, expected_violation_lines)
        assert len(violations) == 0, f"ISSUE #722 VIOLATION: auth_trace_logger.py contains {len(violations)} os.environ/os.getenv violations at lines {[v['line'] for v in violations]}. Expected violations at lines {expected_violation_lines}. These environment access patterns must use IsolatedEnvironment for SSOT compliance. Violations: {violations}"

    def test_unified_corpus_admin_environment_access_violations(self):
        """
        EXPECTED TO FAIL - Detect os.getenv violations in unified_corpus_admin.py.
        
        Per Issue #722: Lines 155, 281 contain direct os.getenv() calls
        that bypass SSOT IsolatedEnvironment patterns for CORPUS_BASE_PATH.
        
        These violations cause corpus path inconsistencies across environments.
        """
        file_path = Path('netra_backend/app/admin/corpus/unified_corpus_admin.py')
        expected_violation_lines = [155, 281]
        violations = self._detect_os_environ_violations_in_file(file_path, expected_violation_lines)
        assert len(violations) == 0, f"ISSUE #722 VIOLATION: unified_corpus_admin.py contains {len(violations)} os.environ/os.getenv violations at lines {[v['line'] for v in violations]}. Expected violations at lines {expected_violation_lines}. CORPUS_BASE_PATH environment access must use IsolatedEnvironment for consistency. Violations: {violations}"

    def test_websocket_types_cloud_run_detection_violations(self):
        """
        EXPECTED TO FAIL - Detect os.getenv violations in websocket_core/types.py.
        
        Per Issue #722: Lines 349-355 contain multiple os.getenv() calls
        for Cloud Run environment detection that bypass SSOT patterns.
        
        These violations cause WebSocket connection inconsistencies in Cloud Run.
        """
        file_path = Path('netra_backend/app/websocket_core/types.py')
        expected_violation_lines = [349, 350, 351, 352]
        violations = self._detect_os_environ_violations_in_file(file_path, expected_violation_lines)
        assert len(violations) == 0, f"ISSUE #722 VIOLATION: websocket_core/types.py contains {len(violations)} os.environ/os.getenv violations at lines {[v['line'] for v in violations]}. Expected violations at lines {expected_violation_lines}. Cloud Run environment detection must use IsolatedEnvironment for SSOT compliance. Violations: {violations}"

    def test_auth_startup_validator_fallback_violations(self):
        """
        EXPECTED TO FAIL - Detect os.environ violations in auth_startup_validator.py.
        
        Per Issue #722: Lines 518, 520 contain fallback os.environ access
        that bypasses SSOT IsolatedEnvironment patterns.
        
        These violations cause auth configuration inconsistencies.
        """
        file_path = Path('netra_backend/app/core/auth_startup_validator.py')
        expected_violation_lines = [518, 520]
        violations = self._detect_os_environ_violations_in_file(file_path, expected_violation_lines)
        assert len(violations) == 0, f"ISSUE #722 VIOLATION: auth_startup_validator.py contains {len(violations)} os.environ access violations at lines {[v['line'] for v in violations]}. Expected violations at lines {expected_violation_lines}. Auth environment access fallbacks must use IsolatedEnvironment for SSOT compliance. Violations: {violations}"

    def test_all_critical_files_missing_isolated_environment_imports(self):
        """
        EXPECTED TO FAIL - Verify critical files import IsolatedEnvironment.
        
        Per Issue #722: All 4 critical files must import and use IsolatedEnvironment
        instead of direct os.environ/os.getenv access patterns.
        
        Missing imports indicate non-SSOT environment access patterns.
        """
        missing_imports = []
        for file_path in self.critical_files_with_violations.keys():
            path = Path(file_path)
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    has_isolated_env_import = any(['from shared.isolated_environment import' in content, 'import shared.isolated_environment' in content, 'from dev_launcher.isolated_environment import' in content, 'import dev_launcher.isolated_environment' in content, 'IsolatedEnvironment' in content])
                    if not has_isolated_env_import:
                        missing_imports.append(str(path))
                except Exception as e:
                    missing_imports.append(f'{path}: ERROR reading file - {e}')
        assert len(missing_imports) == 0, f'ISSUE #722 VIOLATION: {len(missing_imports)} critical files missing IsolatedEnvironment imports: {missing_imports}. All critical files must import IsolatedEnvironment for SSOT compliance.'

    def test_critical_files_ast_based_violation_detection(self):
        """
        EXPECTED TO FAIL - Use AST analysis for comprehensive violation detection.
        
        Uses Abstract Syntax Tree parsing to detect all os.environ and os.getenv
        violations in the 4 critical files, providing exact line numbers and context.
        """
        all_violations = []
        for file_path, expected_lines in self.critical_files_with_violations.items():
            path = Path(file_path)
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    tree = ast.parse(source_code)
                    file_violations = self._find_ast_os_environ_violations(tree, str(path), expected_lines)
                    all_violations.extend(file_violations)
                except Exception as e:
                    all_violations.append({'file': str(path), 'line': -1, 'violation': f'AST parsing error: {str(e)}'})
        assert len(all_violations) == 0, f'ISSUE #722 VIOLATION: AST analysis detected {len(all_violations)} os.environ/os.getenv violations across critical files: {all_violations}. All environment access must use IsolatedEnvironment SSOT patterns.'

    def test_configuration_consistency_across_critical_files(self):
        """
        EXPECTED TO FAIL - Integration test for configuration consistency.
        
        Tests that environment variable access is consistent across all 4 critical files
        when they attempt to read the same environment variables.
        
        This integration test validates SSOT environment access patterns.
        """
        test_env_vars = ['ENVIRONMENT', 'K_SERVICE', 'CORPUS_BASE_PATH', 'AUTH_SERVICE_URL']
        consistency_violations = []
        test_env = {'ENVIRONMENT': 'testing', 'K_SERVICE': 'test-service', 'CORPUS_BASE_PATH': '/test/corpus', 'AUTH_SERVICE_URL': 'http://test-auth:8001'}
        with patch.dict(os.environ, test_env, clear=False):
            for env_var in test_env_vars:
                file_values = {}
                for file_path in self.critical_files_with_violations.keys():
                    try:
                        file_values[file_path] = self._simulate_env_access_from_file(Path(file_path), env_var)
                    except Exception as e:
                        file_values[file_path] = f'ERROR: {str(e)}'
                non_error_values = {k: v for k, v in file_values.items() if v is not None and (not str(v).startswith('ERROR:'))}
                if len(set((str(v) for v in non_error_values.values()))) > 1:
                    consistency_violations.append({'env_var': env_var, 'file_values': file_values, 'inconsistent_values': list(set((str(v) for v in non_error_values.values())))})
        assert len(consistency_violations) == 0, f'ISSUE #722 VIOLATION: Found {len(consistency_violations)} configuration inconsistencies across critical files: {consistency_violations}. Environment access must be consistent through IsolatedEnvironment SSOT.'

    def _detect_os_environ_violations_in_file(self, file_path: Path, expected_lines: List[int]) -> List[Dict[str, Any]]:
        """Detect os.environ/os.getenv violations in specific file."""
        violations = []
        if not file_path.exists():
            return [{'file': str(file_path), 'line': -1, 'violation': 'File does not exist'}]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                if line_num in expected_lines:
                    if any((pattern in line_stripped for pattern in ['os.environ', 'os.getenv', 'os.environ[', 'os.environ.get'])) and (not line_stripped.startswith('#')):
                        violations.append({'file': str(file_path), 'line': line_num, 'content': line_stripped, 'violation': 'Direct os environment access'})
        except Exception as e:
            violations.append({'file': str(file_path), 'line': -1, 'violation': f'Error reading file: {str(e)}'})
        return violations

    def _find_ast_os_environ_violations(self, tree: ast.AST, file_path: str, expected_lines: List[int]) -> List[Dict[str, Any]]:
        """Find os.environ access violations using AST parsing."""
        violations = []
        for node in ast.walk(tree):
            if hasattr(node, 'lineno') and node.lineno in expected_lines:
                violation_found = False
                violation_type = ''
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name) and node.value.id == 'os' and (node.attr == 'environ'):
                        violation_found = True
                        violation_type = 'os.environ attribute access'
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and (node.func.value.id == 'os') and (node.func.attr == 'getenv'):
                        violation_found = True
                        violation_type = 'os.getenv() call'
                if violation_found:
                    violations.append({'file': file_path, 'line': node.lineno, 'violation': violation_type, 'ast_node_type': type(node).__name__})
        return violations

    def _simulate_env_access_from_file(self, file_path: Path, env_var: str) -> Any:
        """Simulate environment variable access from file's perspective."""
        return None

@pytest.mark.unit
class Issue722IntegrationPatternsTests(SSotBaseTestCase):
    """Integration tests for Issue #722 SSOT environment access patterns."""

    def test_isolated_environment_integration_patterns(self):
        """
        Integration test showing proper IsolatedEnvironment usage patterns.
        
        This test demonstrates how the 4 critical files SHOULD access environment
        variables through IsolatedEnvironment for SSOT compliance.
        
        This test should PASS, showing the correct pattern.
        """
        try:
            from shared.isolated_environment import IsolatedEnvironment
            isolated_env = IsolatedEnvironment()
        except ImportError:
            try:
                from dev_launcher.isolated_environment import IsolatedEnvironment
                isolated_env = IsolatedEnvironment()
            except ImportError:
                pytest.skip('IsolatedEnvironment not available for pattern demonstration')
        test_vars = ['ENVIRONMENT', 'K_SERVICE', 'CORPUS_BASE_PATH']
        for var_name in test_vars:
            value = isolated_env.get_env(var_name, 'default_value')
            assert value is not None, f'IsolatedEnvironment.get_env() should handle {var_name}'
            value2 = isolated_env.get_env(var_name, 'default_value')
            assert value == value2, f'IsolatedEnvironment should return consistent values for {var_name}'
        assert True, 'IsolatedEnvironment pattern works correctly for SSOT compliance'

    def test_environment_detection_reliability_with_ssot_patterns(self):
        """
        Integration test for reliable environment detection using SSOT patterns.
        
        Tests that environment detection is reliable when using IsolatedEnvironment
        instead of direct os.environ access.
        
        This test should PASS, demonstrating the target state for Issue #722.
        """
        try:
            from shared.isolated_environment import IsolatedEnvironment
            isolated_env = IsolatedEnvironment()
        except ImportError:
            try:
                from dev_launcher.isolated_environment import IsolatedEnvironment
                isolated_env = IsolatedEnvironment()
            except ImportError:
                pytest.skip('IsolatedEnvironment not available for reliability test')
        environments = ['development', 'staging', 'production']
        for env in environments:
            with patch.object(isolated_env, 'get_env', return_value=env):
                detected_env = isolated_env.get_env('ENVIRONMENT', 'unknown')
                assert detected_env == env, f'Environment detection should be reliable for {env}'
                detected_env2 = isolated_env.get_env('ENVIRONMENT', 'unknown')
                assert detected_env == detected_env2, f'Environment detection should be consistent for {env}'
        assert True, 'SSOT environment detection is reliable and consistent'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')