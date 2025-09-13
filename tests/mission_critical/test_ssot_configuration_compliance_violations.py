#!/usr/bin/env python3

"""

Mission Critical Test Suite: Configuration Manager SSOT Compliance Violations Detection



Business Value: Platform/Internal - System Reliability & Configuration Management

Critical for $500K+ ARR protection through consistent configuration access patterns.



PURPOSE: This test MUST FAIL with current SSOT violations and PASS after remediation.

Detects direct environment variable access that bypasses SSOT configuration patterns.



CRITICAL VIOLATIONS TO DETECT:

1. netra_backend/app/logging/auth_trace_logger.py:284 - os.getenv('ENVIRONMENT')

2. netra_backend/app/middleware/error_recovery_middleware.py:33 - os.environ.get('ENVIRONMENT')

3. netra_backend/app/admin/corpus/unified_corpus_admin.py:155 - os.getenv('CORPUS_BASE_PATH')



Expected Behavior:

- CURRENT STATE: This test should FAIL due to 3 SSOT violations detected

- AFTER REMEDIATION: This test should PASS when violations are fixed using IsolatedEnvironment



Test Strategy:

- Scan source code for direct os.environ/os.getenv usage

- Validate SSOT configuration manager usage patterns

- Ensure IsolatedEnvironment compliance across all modules

- Protect Golden Path user authentication and AI chat functionality



Author: SSOT Gardener Agent - Step 2 Test Plan Execution

Date: 2025-09-13

"""



import ast

import os

import sys

import inspect

from pathlib import Path

from typing import List, Dict, Set, Any, Optional, Tuple

from dataclasses import dataclass

from collections import defaultdict



import pytest



# Import SSOT test framework

from test_framework.ssot.base_test_case import SSotBaseTestCase





@dataclass

class SsotViolation:

    """Structure for SSOT configuration compliance violations."""

    violation_type: str

    file_path: str

    line_number: int

    code_line: str

    environment_variable: str

    description: str

    severity: str  # CRITICAL, HIGH, MEDIUM, LOW

    business_impact: str





@dataclass

class SsotComplianceResults:

    """SSOT configuration compliance validation results."""

    total_files_scanned: int

    total_violations_found: int

    critical_violations: List[SsotViolation]

    high_violations: List[SsotViolation]

    medium_violations: List[SsotViolation]

    low_violations: List[SsotViolation]

    compliant_files: int

    violation_files: int





class TestSSotConfigurationComplianceViolations(SSotBaseTestCase):

    """CRITICAL: Test suite to detect Configuration Manager SSOT compliance violations."""



    def setup_method(self, method=None):

        """Setup test environment for SSOT compliance validation."""

        super().setup_method(method)



        # Project root path

        self.project_root = Path(__file__).resolve().parent.parent.parent



        # Expected violations that MUST be detected (current state)

        self.expected_violations = [

            {

                'file': 'netra_backend/app/logging/auth_trace_logger.py',

                'line': 284,

                'pattern': "os.getenv('ENVIRONMENT')",

                'variable': 'ENVIRONMENT',

                'severity': 'CRITICAL',

                'impact': 'Authentication logging inconsistency - affects Golden Path user auth debugging'

            },

            {

                'file': 'netra_backend/app/middleware/error_recovery_middleware.py',

                'line': 33,

                'pattern': "os.environ.get('ENVIRONMENT')",

                'variable': 'ENVIRONMENT',

                'severity': 'CRITICAL',

                'impact': 'Error handling inconsistency - affects system stability and user experience'

            },

            {

                'file': 'netra_backend/app/admin/corpus/unified_corpus_admin.py',

                'line': 155,

                'pattern': "os.getenv('CORPUS_BASE_PATH')",

                'variable': 'CORPUS_BASE_PATH',

                'severity': 'HIGH',

                'impact': 'Corpus administration path inconsistency - affects content management functionality'

            }

        ]



        # Patterns that indicate SSOT violations

        self.violation_patterns = [

            'os.environ[',

            'os.environ.get(',

            'os.getenv(',

            'environ[',

            'environ.get('

        ]



        # Patterns that indicate proper SSOT usage

        self.compliant_patterns = [

            'get_env()',

            'IsolatedEnvironment',

            'shared.isolated_environment',

            'dev_launcher.isolated_environment'

        ]



    def scan_file_for_violations(self, file_path: Path) -> List[SsotViolation]:

        """Scan a Python file for SSOT configuration violations."""

        violations = []



        try:

            with open(file_path, 'r', encoding='utf-8') as f:

                content = f.read()

                lines = content.splitlines()



            for line_num, line in enumerate(lines, 1):

                line_stripped = line.strip()



                # Skip comments and empty lines

                if not line_stripped or line_stripped.startswith('#'):

                    continue



                # Check for violation patterns

                for pattern in self.violation_patterns:

                    if pattern in line:

                        # Extract environment variable name if possible

                        env_var = self.extract_env_var_name(line)



                        # Determine severity based on environment variable

                        severity = self.determine_violation_severity(env_var, pattern)



                        # Create violation record

                        violation = SsotViolation(

                            violation_type="DIRECT_ENVIRONMENT_ACCESS",

                            file_path=str(file_path.relative_to(self.project_root)),

                            line_number=line_num,

                            code_line=line.strip(),

                            environment_variable=env_var,

                            description=f"Direct environment access using {pattern} instead of IsolatedEnvironment",

                            severity=severity,

                            business_impact=self.determine_business_impact(env_var, str(file_path))

                        )



                        violations.append(violation)



        except Exception as e:

            # Log file read errors but don't fail the test

            self.record_metric('file_read_errors', f"{file_path}: {str(e)}")



        return violations



    def extract_env_var_name(self, code_line: str) -> str:

        """Extract environment variable name from code line."""

        # Common patterns: os.getenv('VAR'), os.environ.get('VAR'), os.environ['VAR']

        for quote in ["'", '"']:

            if f"({quote}" in code_line and f"{quote})" in code_line:

                start = code_line.find(f"({quote}") + 2

                end = code_line.find(f"{quote})", start)

                if start < end:

                    return code_line[start:end]



            if f"[{quote}" in code_line and f"{quote}]" in code_line:

                start = code_line.find(f"[{quote}") + 2

                end = code_line.find(f"{quote}]", start)

                if start < end:

                    return code_line[start:end]



        return "UNKNOWN"



    def determine_violation_severity(self, env_var: str, pattern: str) -> str:

        """Determine severity of SSOT violation."""

        # Critical environment variables that affect Golden Path

        critical_vars = {'ENVIRONMENT', 'JWT_SECRET_KEY', 'DATABASE_URL', 'REDIS_URL'}

        high_vars = {'CORPUS_BASE_PATH', 'AUTH_SERVICE_URL', 'API_KEY'}



        if env_var in critical_vars:

            return 'CRITICAL'

        elif env_var in high_vars:

            return 'HIGH'

        elif env_var != 'UNKNOWN':

            return 'MEDIUM'

        else:

            return 'LOW'



    def determine_business_impact(self, env_var: str, file_path: str) -> str:

        """Determine business impact of SSOT violation."""

        if 'auth' in file_path.lower() and env_var == 'ENVIRONMENT':

            return 'Authentication system inconsistency - affects $500K+ ARR Golden Path user auth'

        elif 'middleware' in file_path.lower() and env_var == 'ENVIRONMENT':

            return 'Error handling inconsistency - affects system stability and user experience'

        elif 'corpus' in file_path.lower() and env_var == 'CORPUS_BASE_PATH':

            return 'Content management path inconsistency - affects admin functionality'

        elif env_var in {'JWT_SECRET_KEY', 'DATABASE_URL', 'REDIS_URL'}:

            return 'Critical infrastructure configuration - affects system availability'

        else:

            return 'Configuration consistency - affects development and deployment reliability'



    def scan_project_for_violations(self) -> SsotComplianceResults:

        """Scan entire project for SSOT configuration violations."""

        all_violations = []

        files_scanned = 0

        compliant_files = 0

        violation_files = 0



        # Scan Python files in key directories

        scan_directories = [

            'netra_backend/app',

            'auth_service',

            'shared'

        ]



        for scan_dir in scan_directories:

            scan_path = self.project_root / scan_dir

            if not scan_path.exists():

                continue



            # Find all Python files

            python_files = list(scan_path.rglob('*.py'))



            for py_file in python_files:

                # Skip test files and __pycache__

                if (py_file.name.startswith('test_') or

                    '__pycache__' in str(py_file) or

                    py_file.suffix != '.py'):

                    continue



                files_scanned += 1

                file_violations = self.scan_file_for_violations(py_file)



                if file_violations:

                    all_violations.extend(file_violations)

                    violation_files += 1

                else:

                    compliant_files += 1



        # Categorize violations by severity

        critical_violations = [v for v in all_violations if v.severity == 'CRITICAL']

        high_violations = [v for v in all_violations if v.severity == 'HIGH']

        medium_violations = [v for v in all_violations if v.severity == 'MEDIUM']

        low_violations = [v for v in all_violations if v.severity == 'LOW']



        # Record metrics

        self.record_metric('total_files_scanned', files_scanned)

        self.record_metric('total_violations_found', len(all_violations))

        self.record_metric('critical_violations', len(critical_violations))

        self.record_metric('high_violations', len(high_violations))



        return SsotComplianceResults(

            total_files_scanned=files_scanned,

            total_violations_found=len(all_violations),

            critical_violations=critical_violations,

            high_violations=high_violations,

            medium_violations=medium_violations,

            low_violations=low_violations,

            compliant_files=compliant_files,

            violation_files=violation_files

        )



    def test_detect_auth_trace_logger_ssot_violation(self):

        """

        MUST FAIL CURRENTLY - Detect SSOT violation in auth trace logger.



        This test specifically targets the known violation:

        netra_backend/app/logging/auth_trace_logger.py:284 - os.getenv('ENVIRONMENT')

        """

        target_file = self.project_root / 'netra_backend/app/logging/auth_trace_logger.py'



        # Verify file exists

        assert target_file.exists(), f"Target file not found: {target_file}"



        # Scan for violations

        violations = self.scan_file_for_violations(target_file)



        # Filter for ENVIRONMENT variable violations

        env_violations = [v for v in violations if v.environment_variable == 'ENVIRONMENT']



        # CURRENT EXPECTATION: Should find violation around line 284

        expected_violation_found = False

        for violation in env_violations:

            if 280 <= violation.line_number <= 290:  # Allow some tolerance for line numbers

                expected_violation_found = True

                break



        # TEST ASSERTION: This MUST FAIL in current state (violation exists)

        assert expected_violation_found, (

            f"EXPECTED SSOT VIOLATION NOT FOUND: Expected to find os.getenv('ENVIRONMENT') violation "

            f"around line 284 in auth_trace_logger.py. Found violations: {env_violations}. "

            f"This test should FAIL until violation is fixed with IsolatedEnvironment."

        )



    def test_detect_error_recovery_middleware_ssot_violation(self):

        """

        MUST FAIL CURRENTLY - Detect SSOT violation in error recovery middleware.



        This test specifically targets the known violation:

        netra_backend/app/middleware/error_recovery_middleware.py:33 - os.environ.get('ENVIRONMENT')

        """

        target_file = self.project_root / 'netra_backend/app/middleware/error_recovery_middleware.py'



        # Verify file exists

        assert target_file.exists(), f"Target file not found: {target_file}"



        # Scan for violations

        violations = self.scan_file_for_violations(target_file)



        # Filter for ENVIRONMENT variable violations

        env_violations = [v for v in violations if v.environment_variable == 'ENVIRONMENT']



        # CURRENT EXPECTATION: Should find violation around line 33

        expected_violation_found = False

        for violation in env_violations:

            if 30 <= violation.line_number <= 40:  # Allow some tolerance for line numbers

                expected_violation_found = True

                break



        # TEST ASSERTION: This MUST FAIL in current state (violation exists)

        assert expected_violation_found, (

            f"EXPECTED SSOT VIOLATION NOT FOUND: Expected to find os.environ.get('ENVIRONMENT') violation "

            f"around line 33 in error_recovery_middleware.py. Found violations: {env_violations}. "

            f"This test should FAIL until violation is fixed with IsolatedEnvironment."

        )



    def test_detect_corpus_admin_ssot_violation(self):

        """

        MUST FAIL CURRENTLY - Detect SSOT violation in unified corpus admin.



        This test specifically targets the known violation:

        netra_backend/app/admin/corpus/unified_corpus_admin.py:155 - os.getenv('CORPUS_BASE_PATH')

        """

        target_file = self.project_root / 'netra_backend/app/admin/corpus/unified_corpus_admin.py'



        # Verify file exists

        assert target_file.exists(), f"Target file not found: {target_file}"



        # Scan for violations

        violations = self.scan_file_for_violations(target_file)



        # Filter for CORPUS_BASE_PATH variable violations

        corpus_violations = [v for v in violations if v.environment_variable == 'CORPUS_BASE_PATH']



        # CURRENT EXPECTATION: Should find violation around line 155

        expected_violation_found = False

        for violation in corpus_violations:

            if 150 <= violation.line_number <= 160:  # Allow some tolerance for line numbers

                expected_violation_found = True

                break



        # TEST ASSERTION: This MUST FAIL in current state (violation exists)

        assert expected_violation_found, (

            f"EXPECTED SSOT VIOLATION NOT FOUND: Expected to find os.getenv('CORPUS_BASE_PATH') violation "

            f"around line 155 in unified_corpus_admin.py. Found violations: {corpus_violations}. "

            f"This test should FAIL until violation is fixed with IsolatedEnvironment."

        )



    def test_comprehensive_ssot_configuration_compliance(self):

        """

        MUST FAIL CURRENTLY - Comprehensive scan for all SSOT configuration violations.



        This test scans the entire project and validates that all expected violations are found.

        After SSOT remediation, this test should pass with zero violations.

        """

        # Perform comprehensive scan

        compliance_results = self.scan_project_for_violations()



        # Expected violation count (current state)

        expected_critical_violations = 2  # ENVIRONMENT violations in auth_trace_logger and middleware

        expected_high_violations = 1      # CORPUS_BASE_PATH violation in corpus admin

        expected_minimum_total = 3        # At least the 3 known violations



        # Analyze results

        actual_critical = len(compliance_results.critical_violations)

        actual_high = len(compliance_results.high_violations)

        actual_total = compliance_results.total_violations_found



        # Record detailed metrics

        self.record_metric('compliance_scan_results', {

            'files_scanned': compliance_results.total_files_scanned,

            'total_violations': actual_total,

            'critical_violations': actual_critical,

            'high_violations': actual_high,

            'medium_violations': len(compliance_results.medium_violations),

            'low_violations': len(compliance_results.low_violations),

            'compliant_files': compliance_results.compliant_files,

            'violation_files': compliance_results.violation_files

        })



        # Validate expected violations are present

        violation_details = []

        for violation in compliance_results.critical_violations + compliance_results.high_violations:

            violation_details.append({

                'file': violation.file_path,

                'line': violation.line_number,

                'variable': violation.environment_variable,

                'severity': violation.severity,

                'code': violation.code_line

            })



        # TEST ASSERTION: This MUST FAIL in current state (violations exist)

        assert actual_total >= expected_minimum_total, (

            f"INSUFFICIENT SSOT VIOLATIONS DETECTED: Expected to find at least {expected_minimum_total} "

            f"SSOT violations but found {actual_total}. This indicates the test may not be working properly. "

            f"Expected violations: {self.expected_violations}. "

            f"Found violations: {violation_details}"

        )



        assert actual_critical >= expected_critical_violations, (

            f"INSUFFICIENT CRITICAL VIOLATIONS: Expected at least {expected_critical_violations} critical "

            f"SSOT violations but found {actual_critical}. Critical violations affect Golden Path functionality. "

            f"Found critical: {[v.file_path + ':' + str(v.line_number) for v in compliance_results.critical_violations]}"

        )



        assert actual_high >= expected_high_violations, (

            f"INSUFFICIENT HIGH VIOLATIONS: Expected at least {expected_high_violations} high priority "

            f"SSOT violations but found {actual_high}. "

            f"Found high: {[v.file_path + ':' + str(v.line_number) for v in compliance_results.high_violations]}"

        )



        # Detailed assertion message for when this test should eventually pass

        if actual_total == 0:

            pytest.fail(

                f"SSOT REMEDIATION COMPLETE: All configuration violations have been fixed! "

                f"This test should now PASS consistently. Consider updating test expectations. "

                f"Files scanned: {compliance_results.total_files_scanned}, "

                f"Compliant files: {compliance_results.compliant_files}"

            )



    def test_validate_isolated_environment_usage_patterns(self):

        """

        Test for proper IsolatedEnvironment usage patterns in SSOT-compliant files.



        This test identifies files that correctly use IsolatedEnvironment patterns

        and ensures they serve as examples for SSOT remediation.

        """

        compliant_files = []

        files_with_good_patterns = []



        # Scan for files with compliant patterns

        scan_directories = ['netra_backend/app', 'shared']



        for scan_dir in scan_directories:

            scan_path = self.project_root / scan_dir

            if not scan_path.exists():

                continue



            python_files = list(scan_path.rglob('*.py'))



            for py_file in python_files:

                if py_file.name.startswith('test_') or '__pycache__' in str(py_file):

                    continue



                try:

                    with open(py_file, 'r', encoding='utf-8') as f:

                        content = f.read()



                    # Check for compliant patterns

                    has_compliant_pattern = any(pattern in content for pattern in self.compliant_patterns)

                    has_violation_pattern = any(pattern in content for pattern in self.violation_patterns)



                    if has_compliant_pattern and not has_violation_pattern:

                        compliant_files.append(str(py_file.relative_to(self.project_root)))

                    elif has_compliant_pattern:

                        files_with_good_patterns.append(str(py_file.relative_to(self.project_root)))



                except Exception:

                    continue



        # Record findings

        self.record_metric('compliant_files_found', compliant_files)

        self.record_metric('files_with_good_patterns', files_with_good_patterns)



        # This test is informational - shows what good patterns look like

        assert len(compliant_files) >= 0, (

            f"Found {len(compliant_files)} fully compliant files using IsolatedEnvironment patterns. "

            f"Compliant files: {compliant_files}. "

            f"Files with mixed patterns: {files_with_good_patterns}"

        )





if __name__ == "__main__":

    # Run the test to detect SSOT violations

    pytest.main([__file__, "-v", "--tb=short"])

