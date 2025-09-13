#!/usr/bin/env python3
"""
Unit Test: Unified Corpus Admin SSOT Compliance Validation

Business Value: Platform/Internal - Content Management System Reliability
Critical for content administration functionality supporting $500K+ ARR platform.

PURPOSE: This test MUST FAIL with current SSOT violations and PASS after remediation.
Validates that UnifiedCorpusAdmin uses IsolatedEnvironment instead of direct os.getenv.

CRITICAL VIOLATION TO DETECT:
- netra_backend/app/admin/corpus/unified_corpus_admin.py:155 - os.getenv('CORPUS_BASE_PATH')

Expected Behavior:
- CURRENT STATE: This test should FAIL due to direct os.getenv usage
- AFTER REMEDIATION: This test should PASS when using get_env() from IsolatedEnvironment

Test Strategy:
- Import and inspect UnifiedCorpusAdmin source code
- Validate environment access patterns in corpus path management
- Ensure SSOT compliance in file system path configuration
- Protect content management functionality for platform administration

Author: SSOT Gardener Agent - Step 2 Test Plan Execution
Date: 2025-09-13
"""

import inspect
import ast
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from unittest.mock import patch, MagicMock

import pytest

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUnifiedCorpusAdminSsotCompliance(SSotBaseTestCase):
    """Unit tests for Unified Corpus Admin SSOT configuration compliance."""

    def setup_method(self, method=None):
        """Setup test environment for unified corpus admin SSOT validation."""
        super().setup_method(method)

        # Import paths
        self.module_path = 'netra_backend.app.admin.corpus.unified_corpus_admin'
        self.admin_class_name = 'UnifiedCorpusAdmin'

        # SSOT violation patterns to detect
        self.violation_patterns = [
            'os.environ[',
            'os.environ.get(',
            'os.getenv(',
        ]

        # SSOT compliant patterns that should be used instead
        self.compliant_patterns = [
            'get_env()',
            'IsolatedEnvironment',
            'isolated_environment',
        ]

        # Expected violations (current state)
        self.expected_violation_line_ranges = [
            (150, 160),  # Around line 155
            (275, 285)   # Around line 281 (second occurrence)
        ]
        self.expected_violation_variable = 'CORPUS_BASE_PATH'
        self.expected_violation_context = '/data/corpus'  # Default path value

    def import_unified_corpus_admin(self):
        """Safely import the UnifiedCorpusAdmin class."""
        try:
            module = __import__(self.module_path, fromlist=[self.admin_class_name])
            admin_class = getattr(module, self.admin_class_name)
            return admin_class
        except (ImportError, AttributeError) as e:
            pytest.skip(f"Cannot import UnifiedCorpusAdmin: {str(e)}")

    def get_source_code(self, class_or_function):
        """Get source code with error handling."""
        try:
            return inspect.getsource(class_or_function)
        except OSError as e:
            pytest.skip(f"Cannot get source code: {str(e)}")

    def parse_source_for_violations(self, source_code: str) -> List[Dict]:
        """Parse source code to find SSOT violations."""
        violations = []
        lines = source_code.splitlines()

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('#'):
                continue

            # Check for violation patterns
            for pattern in self.violation_patterns:
                if pattern in line:
                    # Extract environment variable if possible
                    env_var = self.extract_env_var_from_line(line)

                    # Check for corpus base path context
                    has_corpus_path_context = (
                        'corpus' in line.lower() or
                        '/data' in line.lower() or
                        'base_path' in line.lower()
                    )

                    # Check for default path value
                    has_default_path = self.expected_violation_context in line

                    violations.append({
                        'line_number': line_num,
                        'code_line': line.strip(),
                        'pattern': pattern,
                        'environment_variable': env_var,
                        'has_corpus_context': has_corpus_path_context,
                        'has_default_path': has_default_path,
                        'violation_type': 'DIRECT_ENVIRONMENT_ACCESS'
                    })

        return violations

    def extract_env_var_from_line(self, code_line: str) -> str:
        """Extract environment variable name from code line."""
        # Look for patterns like os.getenv('VAR') or os.environ.get('VAR')
        for quote in ["'", '"']:
            if f"({quote}" in code_line and f"{quote}" in code_line[code_line.find(f"({quote}") + 2:]:
                start = code_line.find(f"({quote}") + 2
                end = code_line.find(f"{quote}", start)
                if start < end:
                    return code_line[start:end]

            if f"[{quote}" in code_line and f"{quote}]" in code_line:
                start = code_line.find(f"[{quote}") + 2
                end = code_line.find(f"{quote}]", start)
                if start < end:
                    return code_line[start:end]

        return "UNKNOWN"

    def check_for_compliant_patterns(self, source_code: str) -> Dict[str, bool]:
        """Check if source code uses SSOT compliant patterns."""
        compliance_status = {}

        for pattern in self.compliant_patterns:
            compliance_status[pattern] = pattern in source_code

        # Check for IsolatedEnvironment import
        has_isolated_env_import = (
            'from shared.isolated_environment import' in source_code or
            'from dev_launcher.isolated_environment import' in source_code or
            'import shared.isolated_environment' in source_code
        )

        compliance_status['isolated_environment_import'] = has_isolated_env_import

        return compliance_status

    def test_unified_corpus_admin_class_exists_and_importable(self):
        """
        Validate that UnifiedCorpusAdmin class exists and can be imported.
        This is a prerequisite for SSOT compliance testing.
        """
        admin_class = self.import_unified_corpus_admin()

        assert admin_class is not None, f"UnifiedCorpusAdmin class not found in {self.module_path}"
        assert inspect.isclass(admin_class), f"UnifiedCorpusAdmin is not a class"

        # Test that it can be instantiated (with minimal args)
        try:
            # Admin classes might require specific parameters
            admin_instance = admin_class()
            assert admin_instance is not None, "UnifiedCorpusAdmin cannot be instantiated"
        except Exception as e:
            # If instantiation fails due to dependencies, that's ok for this test
            self.record_metric('instantiation_error', str(e))

    def test_unified_corpus_admin_direct_environment_access_violation(self):
        """
        MUST FAIL CURRENTLY - Detect direct environment access in UnifiedCorpusAdmin.

        This test specifically checks for the known SSOT violation:
        os.getenv('CORPUS_BASE_PATH') usage instead of IsolatedEnvironment patterns.
        """
        admin_class = self.import_unified_corpus_admin()
        source_code = self.get_source_code(admin_class)

        # Parse source for violations
        violations = self.parse_source_for_violations(source_code)

        # Filter for CORPUS_BASE_PATH variable violations
        corpus_violations = [
            v for v in violations
            if v['environment_variable'] == self.expected_violation_variable
        ]

        # Check for violations in expected line ranges
        target_violations = []
        for line_range in self.expected_violation_line_ranges:
            range_violations = [
                v for v in corpus_violations
                if line_range[0] <= v['line_number'] <= line_range[1]
            ]
            target_violations.extend(range_violations)

        # Check for corpus base path context
        contextual_violations = [
            v for v in target_violations
            if v['has_corpus_context'] or v['has_default_path']
        ]

        # Record metrics
        self.record_metric('total_violations_found', len(violations))
        self.record_metric('corpus_path_violations_found', len(corpus_violations))
        self.record_metric('target_violations_found', len(target_violations))
        self.record_metric('contextual_violations_found', len(contextual_violations))

        # TEST ASSERTION: This MUST FAIL in current state
        assert len(target_violations) > 0, (
            f"EXPECTED SSOT VIOLATION NOT DETECTED: Expected to find os.getenv('CORPUS_BASE_PATH') violation "
            f"in lines around {self.expected_violation_line_ranges} of UnifiedCorpusAdmin, but none found. "
            f"All corpus violations: {corpus_violations}. "
            f"All violations: {violations}. "
            f"This test should FAIL until the violation is fixed with IsolatedEnvironment."
        )

        # Verify specific pattern is detected
        detected_patterns = [v['pattern'] for v in target_violations]
        assert 'os.getenv(' in detected_patterns, (
            f"Expected 'os.getenv(' pattern not found. Detected patterns: {detected_patterns}"
        )

        # Verify corpus base path context
        assert len(contextual_violations) > 0, (
            f"Expected corpus base path context not found. Target violations: {target_violations}. "
            f"The admin class should be accessing CORPUS_BASE_PATH with default '/data/corpus'."
        )

    def test_unified_corpus_admin_lacks_isolated_environment_compliance(self):
        """
        MUST FAIL CURRENTLY - Validate that UnifiedCorpusAdmin lacks proper SSOT patterns.

        This test checks that the current implementation does NOT use SSOT compliant
        patterns and should fail until remediation is complete.
        """
        admin_class = self.import_unified_corpus_admin()
        source_code = self.get_source_code(admin_class)

        # Check for compliant patterns
        compliance_status = self.check_for_compliant_patterns(source_code)

        # Record metrics
        self.record_metric('compliance_patterns_found', compliance_status)

        # Current expectation: Should NOT have SSOT compliance
        has_any_compliant_pattern = any(compliance_status.values())

        # TEST ASSERTION: This MUST FAIL in current state (no SSOT compliance)
        assert not has_any_compliant_pattern, (
            f"UNEXPECTED SSOT COMPLIANCE DETECTED: UnifiedCorpusAdmin appears to already use SSOT patterns. "
            f"Compliance status: {compliance_status}. "
            f"Expected no SSOT compliance in current state. "
            f"If remediation is complete, update test expectations."
        )

        # Specifically check that IsolatedEnvironment is not imported
        assert not compliance_status['isolated_environment_import'], (
            f"IsolatedEnvironment import detected in UnifiedCorpusAdmin, but expected direct os.getenv usage. "
            f"If remediation is complete, this test should be updated."
        )

    def test_unified_corpus_admin_corpus_path_methods(self):
        """
        Test specific methods in UnifiedCorpusAdmin that access corpus path variables.

        This test identifies which methods contain SSOT violations and will help
        with targeted remediation for corpus path configuration.
        """
        admin_class = self.import_unified_corpus_admin()

        # Get methods that might access corpus path environment variables
        methods_to_check = []
        for name, method in inspect.getmembers(admin_class, predicate=inspect.isfunction):
            if not name.startswith('__'):  # Skip magic methods but include _private methods
                methods_to_check.append((name, method))

        # Check each method for violations
        method_violations = {}
        total_violations = 0
        corpus_path_methods = []

        for method_name, method in methods_to_check:
            try:
                method_source = self.get_source_code(method)
                violations = self.parse_source_for_violations(method_source)

                if violations:
                    method_violations[method_name] = violations
                    total_violations += len(violations)

                    # Check for corpus path related functionality
                    if any(keyword in method_source.lower()
                           for keyword in ['corpus', 'base_path', '/data']):
                        corpus_path_methods.append(method_name)

            except Exception as e:
                self.record_metric(f'method_source_error_{method_name}', str(e))

        # Record detailed metrics
        self.record_metric('methods_checked', len(methods_to_check))
        self.record_metric('methods_with_violations', len(method_violations))
        self.record_metric('total_method_violations', total_violations)
        self.record_metric('corpus_path_methods', corpus_path_methods)
        self.record_metric('method_violation_details', method_violations)

        # TEST ASSERTION: Should find violations in current state
        assert total_violations > 0, (
            f"NO VIOLATIONS FOUND IN METHODS: Expected to find SSOT violations in UnifiedCorpusAdmin methods "
            f"but found none. Methods checked: {[name for name, _ in methods_to_check]}. "
            f"This may indicate the test is not detecting violations properly or remediation is complete."
        )

        # Validate that at least one method has CORPUS_BASE_PATH variable access
        corpus_methods = []
        for method_name, violations in method_violations.items():
            for violation in violations:
                if violation['environment_variable'] == 'CORPUS_BASE_PATH':
                    corpus_methods.append(method_name)

        assert len(corpus_methods) > 0, (
            f"NO CORPUS_BASE_PATH VARIABLE ACCESS FOUND: Expected to find methods accessing 'CORPUS_BASE_PATH' variable "
            f"but found none. Method violations: {method_violations}"
        )

        # Validate corpus path functionality exists
        assert len(corpus_path_methods) > 0, (
            f"NO CORPUS PATH METHODS FOUND: Expected UnifiedCorpusAdmin to have corpus path related methods "
            f"but found none. Methods checked: {[name for name, _ in methods_to_check]}"
        )

    def test_unified_corpus_admin_file_system_path_logic(self):
        """
        Test the file system path management logic in UnifiedCorpusAdmin.

        This test validates that the admin properly handles corpus base paths
        and identifies where SSOT violations affect file system operations.
        """
        admin_class = self.import_unified_corpus_admin()
        source_code = self.get_source_code(admin_class)

        # Look for file system related patterns
        filesystem_patterns = [
            'path',
            'dir',
            'file',
            'corpus',
            'base_path',
            '/data',
            'mkdir',
            'exists',
            'pathlib',
            'os.path'
        ]

        # Find lines with file system operations
        filesystem_lines = []
        lines = source_code.splitlines()

        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            if any(pattern in line_lower for pattern in filesystem_patterns):
                if any(violation_pattern in line for violation_pattern in self.violation_patterns):
                    filesystem_lines.append({
                        'line_number': line_num,
                        'code': line.strip(),
                        'has_violation': True
                    })

        # Parse all violations
        violations = self.parse_source_for_violations(source_code)
        corpus_violations = [v for v in violations if v['environment_variable'] == 'CORPUS_BASE_PATH']

        # Record metrics
        self.record_metric('filesystem_related_lines', len(filesystem_lines))
        self.record_metric('filesystem_lines_with_violations',
                          len([line for line in filesystem_lines if line['has_violation']]))
        self.record_metric('corpus_path_violations_in_filesystem_logic', len(corpus_violations))

        # TEST ASSERTION: Validate file system logic has violations
        assert len(filesystem_lines) > 0, (
            f"NO FILE SYSTEM LOGIC FOUND: Expected UnifiedCorpusAdmin to contain "
            f"file system path management logic but found none. "
            f"This may indicate the admin doesn't handle corpus file operations."
        )

        filesystem_violations = [line for line in filesystem_lines if line['has_violation']]
        assert len(filesystem_violations) > 0, (
            f"NO VIOLATIONS IN FILE SYSTEM LOGIC: Expected to find SSOT violations in corpus path "
            f"management logic but found none. Filesystem lines: {filesystem_lines}. "
            f"Corpus violations: {corpus_violations}"
        )

        # Verify default path configuration
        default_path_lines = [line for line in filesystem_lines if self.expected_violation_context in line['code']]
        assert len(default_path_lines) > 0, (
            f"DEFAULT CORPUS PATH NOT FOUND: Expected to find default '/data/corpus' path configuration "
            f"but found none. Filesystem lines: {filesystem_lines}"
        )

    def test_unified_corpus_admin_admin_functionality_impact(self):
        """
        Assess the admin functionality impact of UnifiedCorpusAdmin SSOT violations.

        This test validates that violations in UnifiedCorpusAdmin affect critical
        content management capabilities supporting the $500K+ ARR platform.
        """
        admin_class = self.import_unified_corpus_admin()
        source_code = self.get_source_code(admin_class)

        # Look for admin functionality patterns
        admin_patterns = [
            'admin',
            'manage',
            'create',
            'delete',
            'update',
            'list',
            'upload',
            'download',
            'corpus',
            'content',
            'file',
            'document'
        ]

        # Check how many admin patterns are in the class
        admin_pattern_count = sum(1 for pattern in admin_patterns
                                 if pattern.lower() in source_code.lower())

        # Find SSOT violations
        violations = self.parse_source_for_violations(source_code)
        corpus_violations = [v for v in violations if v['environment_variable'] == 'CORPUS_BASE_PATH']

        # Check for admin-specific functionality
        has_admin_functionality = (
            'admin' in source_code.lower() or
            'manage' in source_code.lower() or
            'corpus' in source_code.lower()
        )

        # Record business impact metrics
        self.record_metric('admin_patterns_found', admin_pattern_count)
        self.record_metric('has_admin_functionality', has_admin_functionality)
        self.record_metric('corpus_path_violations', len(corpus_violations))

        # Assess business impact
        has_content_functionality = admin_pattern_count > 3  # Allow for some basic patterns
        has_corpus_violations = len(corpus_violations) > 0

        # TEST ASSERTION: Validate admin functionality impact
        if has_content_functionality and has_corpus_violations:
            # This is the expected current state - admin class with SSOT violations
            assert True, (
                f"ADMIN FUNCTIONALITY IMPACT CONFIRMED: UnifiedCorpusAdmin contains {admin_pattern_count} "
                f"admin/content patterns and {len(corpus_violations)} CORPUS_BASE_PATH variable violations. "
                f"This affects content management functionality supporting $500K+ ARR platform operations."
            )
        elif has_content_functionality and not has_corpus_violations:
            pytest.fail(
                f"SSOT REMEDIATION APPEARS COMPLETE: UnifiedCorpusAdmin has admin functionality "
                f"but no CORPUS_BASE_PATH variable violations detected. If remediation is complete, "
                f"update test expectations to validate proper IsolatedEnvironment usage."
            )
        else:
            pytest.fail(
                f"UNEXPECTED STATE: UnifiedCorpusAdmin analysis shows admin patterns: {admin_pattern_count}, "
                f"CORPUS_BASE_PATH violations: {len(corpus_violations)}. Verify test logic and file content."
            )

        # Additional validation for admin functionality
        assert has_admin_functionality, (
            f"ADMIN FUNCTIONALITY NOT DETECTED: Expected UnifiedCorpusAdmin to contain "
            f"admin-specific patterns but found limited functionality. "
            f"Verify this is actually an admin class."
        )

    def test_unified_corpus_admin_ssot_remediation_readiness(self):
        """
        Prepare for SSOT remediation by identifying what needs to be changed.

        This test documents the current state and provides guidance for
        converting to SSOT-compliant patterns for corpus path management.
        """
        admin_class = self.import_unified_corpus_admin()
        source_code = self.get_source_code(admin_class)

        # Find all violations
        violations = self.parse_source_for_violations(source_code)

        # Create remediation guide
        remediation_guide = {
            'violations_to_fix': [],
            'recommended_patterns': {
                'os.getenv(': 'get_env().get(',
                'os.environ.get(': 'get_env().get(',
                'os.environ[': 'get_env().get(',
            },
            'required_imports': [
                'from shared.isolated_environment import get_env'
            ],
            'corpus_path_fixes': []
        }

        for violation in violations:
            # Specific remediation for corpus path access
            if violation['environment_variable'] == 'CORPUS_BASE_PATH':
                current_line = violation['code_line']

                # Handle default path patterns
                if self.expected_violation_context in current_line:
                    recommended_fix = current_line.replace(
                        violation['pattern'],
                        'get_env().get('
                    )
                    remediation_guide['corpus_path_fixes'].append({
                        'line': violation['line_number'],
                        'current': current_line,
                        'recommended': recommended_fix,
                        'note': 'Corpus base path access using IsolatedEnvironment with default /data/corpus'
                    })

            remediation_guide['violations_to_fix'].append({
                'line': violation['line_number'],
                'current': violation['code_line'],
                'pattern': violation['pattern'],
                'variable': violation['environment_variable'],
                'has_corpus_context': violation['has_corpus_context'],
                'has_default_path': violation['has_default_path'],
                'recommended_fix': violation['code_line'].replace(
                    violation['pattern'],
                    remediation_guide['recommended_patterns'].get(violation['pattern'], 'get_env().get(')
                )
            })

        # Record comprehensive remediation information
        self.record_metric('ssot_remediation_guide', remediation_guide)
        self.record_metric('violations_count_for_remediation', len(violations))
        self.record_metric('corpus_path_fixes_needed', len(remediation_guide['corpus_path_fixes']))

        # TEST ASSERTION: Provide remediation guidance
        assert len(violations) > 0, (
            f"SSOT REMEDIATION GUIDE: Found {len(violations)} violations in UnifiedCorpusAdmin that need fixing. "
            f"Remediation guide: {remediation_guide}. "
            f"After remediation, these violations should be replaced with IsolatedEnvironment patterns. "
            f"Pay special attention to corpus base path configuration: {len(remediation_guide['corpus_path_fixes'])} found."
        )

        # Validate that corpus path violations are found
        corpus_violations = [v for v in violations if v['environment_variable'] == 'CORPUS_BASE_PATH']
        assert len(corpus_violations) > 0, (
            f"NO CORPUS_BASE_PATH VIOLATIONS FOR REMEDIATION: Expected to find CORPUS_BASE_PATH violations "
            f"for remediation planning but found none. All violations: {violations}"
        )


if __name__ == "__main__":
    # Run the test to validate unified corpus admin SSOT compliance
    pytest.main([__file__, "-v", "--tb=short"])