"""
MISSION CRITICAL: Environment Access SSOT Compliance Validation

CRITICAL MISSION: Detect and prevent direct os.environ access that bypasses 
IsolatedEnvironment SSOT patterns and threatens multi-user security isolation.

BUSINESS VALUE: Protects $500K+ ARR Golden Path functionality by ensuring secure
environment variable access patterns that prevent cross-user data contamination.

SECURITY IMPACT: Direct os.environ access can lead to:
- Multi-user session contamination
- Configuration drift between environments  
- Security vulnerabilities in user isolation
- Race conditions in concurrent user execution

SSOT REQUIREMENTS ENFORCED:
- ALL environment access must use IsolatedEnvironment
- NO direct os.environ.get() calls in production code
- NO direct os.getenv() calls in production code
- ALL tests must use SSOT environment access patterns

PURPOSE: These tests MUST FAIL initially to detect current environment access
violations, then pass after remediation to protect ongoing security compliance.
"""
import pytest
import sys
import ast
import re
import os
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))
from test_framework.ssot.base_test_case import SSotBaseTestCase

@dataclass
class EnvironmentViolation:
    """Environment access violation detected in code."""
    file_path: str
    violation_type: str
    description: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    severity: str = 'HIGH'

@pytest.mark.unit
class EnvironmentAccessSSOTComplianceTests(SSotBaseTestCase):
    """
    MISSION CRITICAL: Test SSOT environment access compliance across all code.
    
    This test suite MUST detect violations where code directly accesses os.environ
    instead of using IsolatedEnvironment, protecting multi-user security isolation.
    """

    def setup_method(self, method):
        """Setup for environment access compliance testing."""
        super().setup_method(method)
        self.violations: List[EnvironmentViolation] = []
        self.allowed_direct_access_files = {'dev_launcher/isolated_environment.py', 'shared/isolated_environment.py', 'netra_backend/app/config.py', 'test_framework/ssot/environment_test_utility.py'}
        self.expected_violations = ['test_plans/rollback/test_emergency_rollback_validation.py', 'test_plans/phase5/test_golden_path_protection_validation.py', 'test_plans/phase3/test_critical_configuration_drift_detection.py']

    def test_no_direct_os_environ_access_in_production_code(self):
        """
        CRITICAL: Production code must NOT access os.environ directly.
        
        All environment access must go through IsolatedEnvironment to ensure
        multi-user isolation and prevent security vulnerabilities.
        """
        violations = self._scan_for_direct_environ_access()
        production_violations = [v for v in violations if not any((allowed in v.file_path for allowed in self.allowed_direct_access_files))]
        detected_files = {v.file_path for v in production_violations}
        expected_files = set(self.expected_violations)
        missing_detections = expected_files - detected_files
        if missing_detections:
            self.fail(f'DETECTION FAILURE: Failed to detect known environment access violations: {missing_detections}. The environment compliance detection system is not working correctly.')
        if production_violations:
            violation_details = '\n'.join([f'  - {v.file_path}:{v.line_number} - {v.description}\n    Code: {v.code_snippet}' for v in production_violations])
            self.fail(f"ENVIRONMENT ACCESS VIOLATION: {len(production_violations)} files use direct os.environ access:\n{violation_details}\n\nREMEDIATION REQUIRED:\n1. Import: from dev_launcher.isolated_environment import IsolatedEnvironment\n2. Replace: os.environ.get('VAR') → IsolatedEnvironment.get_env('VAR')\n3. Replace: os.getenv('VAR') → IsolatedEnvironment.get_env('VAR')\n4. Use environment context managers for test isolation\n\nSECURITY IMPACT: Direct environment access threatens multi-user isolation and $500K+ ARR security")

    def test_isolated_environment_usage_in_test_files(self):
        """
        CRITICAL: Test files must use IsolatedEnvironment for all environment access.
        
        Tests that access environment variables directly can cause test contamination
        and false positives/negatives in multi-user scenarios.
        """
        test_violations = self._scan_test_files_for_environment_violations()
        if test_violations:
            violation_details = '\n'.join([f'  - {v.file_path}:{v.line_number} - {v.description}\n    Code: {v.code_snippet}' for v in test_violations])
            self.fail(f'TEST ENVIRONMENT VIOLATION: {len(test_violations)} test files use direct environment access:\n{violation_details}\n\nREMEDIATION REQUIRED:\n1. Use SSOT environment test utilities\n2. Import: from test_framework.ssot.environment_test_utility import EnvironmentTestHelper\n3. Use environment context managers in tests\n4. Ensure test isolation with proper setup/teardown\n\nBUSINESS IMPACT: Test environment contamination can hide bugs affecting $500K+ ARR functionality')

    def test_environment_variable_patterns_are_consistent(self):
        """
        CRITICAL: Environment variable naming and access patterns must be consistent.
        
        Inconsistent environment variable usage can lead to configuration drift
        and environment-specific bugs.
        """
        pattern_violations = self._scan_for_inconsistent_env_patterns()
        if pattern_violations:
            violation_details = '\n'.join([f'  - {v.file_path}:{v.line_number} - {v.description}' for v in pattern_violations])
            self.fail(f'ENVIRONMENT PATTERN VIOLATION: {len(pattern_violations)} files use inconsistent patterns:\n{violation_details}\n\nREMEDIATION REQUIRED:\n1. Standardize environment variable naming (UPPER_CASE_WITH_UNDERSCORES)\n2. Use consistent access patterns through IsolatedEnvironment\n3. Document environment variable requirements\n4. Use environment validation in application startup\n\nBUSINESS IMPACT: Inconsistent environment patterns cause deployment issues')

    def test_environment_security_isolation_compliance(self):
        """
        CRITICAL: Verify environment access maintains security isolation for multi-user system.
        
        The system must prevent user A from accessing environment variables
        that could contain data from user B's session.
        """
        security_violations = self._scan_for_environment_security_violations()
        if security_violations:
            violation_details = '\n'.join([f'  - {v.file_path}:{v.line_number} - {v.description}' for v in security_violations])
            self.fail(f'ENVIRONMENT SECURITY VIOLATION: {len(security_violations)} potential security risks detected:\n{violation_details}\n\nREMEDIATION REQUIRED:\n1. Use user-scoped environment contexts\n2. Implement environment variable validation and sanitization\n3. Ensure session isolation in environment access\n4. Add security auditing for sensitive environment variables\n\nSECURITY IMPACT: Environment security violations could expose sensitive user data')

    def test_detect_specific_environment_access_violations(self):
        """
        CRITICAL: Explicitly test detection of environment access in known violating files.
        
        This ensures our detection system works correctly for actual violations.
        """
        for file_path in self.expected_violations:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                continue
            file_violations = self._analyze_single_file_for_environment_violations(full_path)
            assert file_violations, f'DETECTION FAILURE: No environment access violations detected in known violator: {file_path}\nThis indicates the environment compliance detection system is not working correctly.'

    def _scan_for_direct_environ_access(self) -> List[EnvironmentViolation]:
        """Scan for direct os.environ access in all Python files."""
        violations = []
        environ_patterns = [('os\\.environ\\.get\\s*\\(', 'Direct os.environ.get() access'), ('os\\.environ\\[', 'Direct os.environ[] access'), ('os\\.getenv\\s*\\(', 'Direct os.getenv() access'), ('environ\\.get\\s*\\(', 'Direct environ.get() access (from os import environ)'), ('getenv\\s*\\(', 'Direct getenv() access (from os import getenv)')]
        for py_file in self._find_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    for pattern, description in environ_patterns:
                        if re.search(pattern, line):
                            if line.strip().startswith('#') or '"""' in line or "'''" in line:
                                continue
                            violations.append(EnvironmentViolation(file_path=str(py_file.relative_to(PROJECT_ROOT)), violation_type='DIRECT_ENVIRON_ACCESS', description=description, line_number=line_num, code_snippet=line.strip()[:100], severity='HIGH'))
            except Exception as e:
                print(f'Warning: Could not analyze {py_file}: {e}')
        return violations

    def _scan_test_files_for_environment_violations(self) -> List[EnvironmentViolation]:
        """Scan test files specifically for environment access violations."""
        violations = []
        test_files = self._find_test_files()
        for test_file in test_files:
            violations.extend(self._analyze_single_file_for_environment_violations(test_file))
        return violations

    def _analyze_single_file_for_environment_violations(self, file_path: Path) -> List[EnvironmentViolation]:
        """Analyze a single file for environment access violations."""
        violations = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            environ_patterns = [('os\\.environ', 'Uses os.environ directly'), ('os\\.getenv', 'Uses os.getenv directly'), ('from os import environ', 'Imports environ directly'), ('from os import getenv', 'Imports getenv directly')]
            for line_num, line in enumerate(lines, 1):
                for pattern, description in environ_patterns:
                    if re.search(pattern, line) and (not line.strip().startswith('#')):
                        violations.append(EnvironmentViolation(file_path=str(file_path.relative_to(PROJECT_ROOT)), violation_type='ENVIRONMENT_ACCESS', description=description, line_number=line_num, code_snippet=line.strip()[:100], severity='HIGH'))
        except Exception as e:
            print(f'Warning: Could not analyze {file_path}: {e}')
        return violations

    def _scan_for_inconsistent_env_patterns(self) -> List[EnvironmentViolation]:
        """Scan for inconsistent environment variable patterns."""
        violations = []
        inconsistent_patterns = [('os\\.environ\\["[^"]*"\\]', 'Mixed quote styles in environment access'), ('getenv\\([^)]*,\\s*None\\)', 'Explicit None default (unnecessary)'), ('environ\\.get\\([^)]*,\\s*""', 'Empty string default (should use None)')]
        for py_file in self._find_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    for pattern, description in inconsistent_patterns:
                        if re.search(pattern, line):
                            violations.append(EnvironmentViolation(file_path=str(py_file.relative_to(PROJECT_ROOT)), violation_type='INCONSISTENT_PATTERN', description=description, line_number=line_num, code_snippet=line.strip()[:100], severity='MEDIUM'))
            except Exception as e:
                print(f'Warning: Could not analyze {py_file}: {e}')
        return violations

    def _scan_for_environment_security_violations(self) -> List[EnvironmentViolation]:
        """Scan for potential environment security violations."""
        violations = []
        security_patterns = [('environ.*[Pp]assword', 'Password in environment variable name'), ('environ.*[Ss]ecret', 'Secret in environment variable name'), ('environ.*[Kk]ey.*=', 'Key assignment that might expose secrets'), ('print.*environ', 'Printing environment variables (potential secret exposure)')]
        for py_file in self._find_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    for pattern, description in security_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append(EnvironmentViolation(file_path=str(py_file.relative_to(PROJECT_ROOT)), violation_type='SECURITY_RISK', description=description, line_number=line_num, code_snippet=line.strip()[:100], severity='CRITICAL'))
            except Exception as e:
                print(f'Warning: Could not analyze {py_file}: {e}')
        return violations

    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project (excluding venv, __pycache__, etc.)."""
        python_files = []
        exclude_dirs = {'__pycache__', '.venv', 'venv', 'node_modules', '.git', 'terraform-gcp-staging', 'terraform-gcp-production'}
        for py_file in PROJECT_ROOT.rglob('*.py'):
            if any((excluded in str(py_file) for excluded in exclude_dirs)):
                continue
            python_files.append(py_file)
        return python_files

    def _find_test_files(self) -> List[Path]:
        """Find all test files in the project."""
        test_files = []
        test_dirs = [PROJECT_ROOT / 'tests', PROJECT_ROOT / 'test_plans', PROJECT_ROOT / 'netra_backend' / 'tests', PROJECT_ROOT / 'auth_service' / 'tests', PROJECT_ROOT / 'frontend' / 'tests', PROJECT_ROOT / 'test_framework' / 'tests']
        for test_dir in test_dirs:
            if test_dir.exists():
                test_files.extend(test_dir.rglob('test_*.py'))
                test_files.extend(test_dir.rglob('*_test.py'))
        return test_files
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')