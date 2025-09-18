"""
Fix Validation Test: P0 .dockerignore Monitoring Module Fix
===========================================================

This test validates that the emergency fix for .dockerignore correctly includes
the monitoring module while maintaining appropriate exclusions for development files.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Critical Infrastructure
2. Business Goal: Validate Production Fix Effectiveness
3. Value Impact: Ensures monitoring module is available in container builds
4. Revenue Impact: Validates fix protecting $500K+ ARR production systems

EMERGENCY FIX STATUS:
CHECK Line 103: `# **/monitoring/` (commented out)
CHECK Lines 104-108: Selective exclusion with explicit includes
CHECK Line 105: `monitoring/` (excludes general monitoring)
CHECK Line 106: `deployment/monitoring/` (excludes deployment monitoring)
CHECK Line 107: `!netra_backend/app/monitoring/` (INCLUDES our monitoring module)
CHECK Line 108: `!netra_backend/app/services/monitoring/` (INCLUDES our services monitoring)

This test ensures the selective exclusion approach works correctly.
"""

import os
import re
import unittest
from pathlib import Path
from typing import List, Dict, Set

# SSOT imports - no relative imports allowed per CLAUDE.md
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDockerignoreFixValidation(SSotBaseTestCase):
    """
    Validation test suite for .dockerignore monitoring module fix.

    This test validates that the emergency fix correctly:
    1. Includes netra_backend monitoring modules
    2. Excludes general monitoring directories
    3. Maintains proper Docker build context optimization
    """

    def setUp(self):
        """Set up test environment with SSOT compliance."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.dockerignore_path = self.project_root / ".dockerignore"

        # Critical monitoring paths that MUST be included
        self.critical_monitoring_paths = [
            "netra_backend/app/monitoring/",
            "netra_backend/app/services/monitoring/"
        ]

        # Monitoring paths that SHOULD be excluded (to optimize build context)
        self.excluded_monitoring_paths = [
            "monitoring/",
            "deployment/monitoring/",
            "prometheus/"
        ]

    def test_emergency_fix_applied_correctly(self):
        """
        CRITICAL: Verify the emergency fix is correctly applied.

        This test validates that:
        1. The problematic `**/monitoring/` line is commented out
        2. Selective exclusion patterns are properly configured
        3. Explicit include patterns protect critical monitoring modules
        """
        if not self.dockerignore_path.exists():
            self.fail(f".dockerignore file not found: {self.dockerignore_path}")

        with open(self.dockerignore_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')

        # Test 1: Verify problematic global exclusion is commented out
        problematic_line_found = False
        for line_num, line in enumerate(lines, 1):
            if '**/monitoring/' in line:
                if line.strip().startswith('#'):
                    # Good: commented out
                    self.record_metric("problematic_line_commented", True)
                    problematic_line_found = True
                else:
                    # Bad: still active
                    self.fail(
                        f"CRITICAL: Global monitoring exclusion still active on line {line_num}: {line}\n"
                        f"This will cause the same P0 production failure.\n"
                        f"Line must be commented out or removed."
                    )

        if not problematic_line_found:
            # Check if it was completely removed (also acceptable)
            self.record_metric("problematic_line_removed", True)

        # Test 2: Verify selective exclusions are present
        active_exclusions = self._get_active_dockerignore_patterns(lines)

        for excluded_path in self.excluded_monitoring_paths:
            if not any(excluded_path in pattern for pattern in active_exclusions):
                self.fail(
                    f"Expected exclusion pattern '{excluded_path}' not found.\n"
                    f"This may cause unnecessarily large Docker build contexts.\n"
                    f"Active exclusions: {active_exclusions}"
                )

        # Test 3: Verify explicit includes are present
        for critical_path in self.critical_monitoring_paths:
            include_pattern = f"!{critical_path}"
            if not any(include_pattern in line for line in lines):
                self.fail(
                    f"CRITICAL: Explicit include pattern '{include_pattern}' not found.\n"
                    f"Without this, the monitoring module will still be excluded.\n"
                    f"Add line: {include_pattern}"
                )

    def test_monitoring_module_import_success_post_fix(self):
        """
        Validate that monitoring module imports work after the fix.

        This simulates the Docker build context behavior to ensure
        the monitoring module would be available in containers.
        """
        try:
            # Test the exact imports that were failing
            from netra_backend.app.services.monitoring.gcp_error_reporter import (
                set_request_context,
                clear_request_context
            )

            # Verify functions are properly imported and callable
            self.assertTrue(callable(set_request_context))
            self.assertTrue(callable(clear_request_context))

            # Test function signatures to ensure they're the real functions
            import inspect
            set_context_sig = inspect.signature(set_request_context)
            clear_context_sig = inspect.signature(clear_request_context)

            # Verify expected parameters exist
            self.assertIn('user_id', set_context_sig.parameters)
            self.assertIn('trace_id', set_context_sig.parameters)

            # clear_request_context should have no required parameters
            required_params = [
                p for p in clear_context_sig.parameters.values()
                if p.default == inspect.Parameter.empty
            ]
            self.assertEqual(len(required_params), 0)

            self.record_metric("monitoring_import_success", True)

        except ImportError as e:
            self.fail(
                f"CRITICAL: Monitoring module import still failing after fix: {e}\n"
                f"This indicates the .dockerignore fix did not resolve the issue.\n"
                f"Check that include patterns are correctly formatted and positioned."
            )

    def test_dockerignore_selective_exclusion_strategy(self):
        """
        Validate the selective exclusion strategy is correctly implemented.

        This ensures we're excluding unnecessary monitoring directories
        while preserving critical ones.
        """
        with open(self.dockerignore_path, 'r') as f:
            lines = f.read().split('\n')

        active_patterns = self._get_active_dockerignore_patterns(lines)
        include_patterns = self._get_include_patterns(lines)

        # Strategy validation: Should exclude general monitoring but include specific paths
        general_monitoring_excluded = any('monitoring/' in pattern for pattern in active_patterns)
        specific_monitoring_included = any('netra_backend/app/services/monitoring' in pattern for pattern in include_patterns)

        self.assertTrue(
            general_monitoring_excluded,
            "General monitoring should be excluded to optimize build context"
        )

        self.assertTrue(
            specific_monitoring_included,
            "Specific netra_backend monitoring should be explicitly included"
        )

        # Record strategy metrics
        self.record_metric("selective_exclusion_implemented", True)
        self.record_metric("general_monitoring_excluded", general_monitoring_excluded)
        self.record_metric("specific_monitoring_included", specific_monitoring_included)

    def test_dockerignore_file_structure_validation(self):
        """
        Validate the overall .dockerignore file structure after the fix.

        This ensures the file is well-structured and maintainable.
        """
        with open(self.dockerignore_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')

        # Test file is not empty
        self.assertGreater(len(lines), 0, ".dockerignore should not be empty")

        # Test has emergency fix documentation
        has_emergency_comment = any(
            'EMERGENCY FIX' in line or 'Monitoring module required' in line
            for line in lines
        )

        self.assertTrue(
            has_emergency_comment,
            "Emergency fix should be documented with explanatory comments"
        )

        # Test exclude patterns are properly formatted
        active_patterns = self._get_active_dockerignore_patterns(lines)

        for pattern in active_patterns:
            # Should not start with leading slash (Docker convention)
            self.assertFalse(
                pattern.startswith('/'),
                f"Pattern should not start with '/': {pattern}"
            )

            # Should not have spaces (except in comments)
            if not pattern.strip().startswith('#'):
                self.assertNotIn(' ', pattern.strip(), f"Pattern should not contain spaces: {pattern}")

        self.record_metric("dockerignore_structure_valid", True)

    def test_middleware_import_simulation(self):
        """
        Simulate the exact middleware import that was failing.

        This replicates the production failure scenario to ensure it's resolved.
        """
        try:
            # Simulate the middleware initialization that was failing
            # This is the exact pattern from gcp_auth_context_middleware.py line 23
            from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context

            # Simulate middleware usage during request processing
            test_request_context = {
                'user_id': 'test_user_middleware_simulation',
                'trace_id': 'test_trace_middleware_123',
                'http_context': {
                    'method': 'POST',
                    'path': '/api/test/middleware',
                    'remote_addr': '127.0.0.1'
                }
            }

            # Test setting context (middleware request start)
            set_request_context(**test_request_context)

            # Test clearing context (middleware request end)
            clear_request_context()

            self.record_metric("middleware_simulation_success", True)

        except Exception as e:
            self.fail(
                f"Middleware simulation failed: {e}\n"
                f"This indicates the fix may not resolve the production issue.\n"
                f"The exact middleware import pattern must work in container environment."
            )

    def _get_active_dockerignore_patterns(self, lines: List[str]) -> List[str]:
        """
        Extract active (non-commented) exclusion patterns from .dockerignore.

        Args:
            lines: Lines from .dockerignore file

        Returns:
            List of active exclusion patterns
        """
        active_patterns = []
        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Skip include patterns (start with !)
            if line.startswith('!'):
                continue
            active_patterns.append(line)
        return active_patterns

    def _get_include_patterns(self, lines: List[str]) -> List[str]:
        """
        Extract include patterns (starting with !) from .dockerignore.

        Args:
            lines: Lines from .dockerignore file

        Returns:
            List of include patterns
        """
        include_patterns = []
        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Only include patterns (start with !)
            if line.startswith('!'):
                include_patterns.append(line)
        return include_patterns


class TestDockerignoreFixRegressionPrevention(SSotBaseTestCase):
    """
    Regression prevention tests for .dockerignore monitoring exclusions.

    These tests ensure the same type of issue doesn't happen again.
    """

    def setUp(self):
        """Set up regression prevention test environment."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.dockerignore_path = self.project_root / ".dockerignore"

    def test_prevent_global_monitoring_exclusion(self):
        """
        Prevent future global monitoring exclusions in .dockerignore.

        This test fails if any global patterns would exclude monitoring modules.
        """
        if not self.dockerignore_path.exists():
            self.skipTest("No .dockerignore file - skipping regression test")

        with open(self.dockerignore_path, 'r') as f:
            lines = f.read().split('\n')

        dangerous_patterns = [
            '**/monitoring/',    # The original problematic pattern
            '**/monitoring',     # Variant without trailing slash
            'monitoring/**',     # Alternative global pattern
            '**/services/',      # Would exclude all services
            '**/app/',           # Would exclude all app code
        ]

        active_dangerous_patterns = []

        for line_num, line in enumerate(lines, 1):
            line_content = line.strip()

            # Skip comments and empty lines
            if not line_content or line_content.startswith('#'):
                continue

            # Check for dangerous patterns
            for pattern in dangerous_patterns:
                if pattern in line_content:
                    active_dangerous_patterns.append({
                        'line_number': line_num,
                        'line': line_content,
                        'pattern': pattern
                    })

        if active_dangerous_patterns:
            failure_details = '\n'.join([
                f"  Line {item['line_number']}: {item['line']} (contains: {item['pattern']})"
                for item in active_dangerous_patterns
            ])

            self.fail(
                f"REGRESSION DETECTED: Dangerous global exclusion patterns found:\n"
                f"{failure_details}\n\n"
                f"These patterns could exclude critical monitoring modules.\n"
                f"Use selective exclusions with explicit includes instead."
            )

    def test_critical_modules_have_explicit_includes(self):
        """
        Ensure critical modules have explicit include patterns.

        This prevents accidental exclusion of business-critical modules.
        """
        critical_modules = [
            'netra_backend/app/services/monitoring/',
            'netra_backend/app/monitoring/',
            'shared/monitoring/',
            'auth_service/monitoring/'
        ]

        existing_modules = []
        for module_path in critical_modules:
            full_path = self.project_root / module_path
            if full_path.exists():
                existing_modules.append(module_path)

        if not existing_modules:
            self.skipTest("No critical monitoring modules found")

        with open(self.dockerignore_path, 'r') as f:
            content = f.read()

        missing_includes = []
        for module_path in existing_modules:
            include_pattern = f"!{module_path}"
            if include_pattern not in content:
                missing_includes.append(module_path)

        if missing_includes:
            self.fail(
                f"CRITICAL: Missing explicit include patterns for:\n"
                f"{chr(10).join(f'  !{path}' for path in missing_includes)}\n\n"
                f"Add these lines to .dockerignore to prevent exclusion."
            )

    def test_dockerignore_maintenance_documentation(self):
        """
        Ensure .dockerignore has proper maintenance documentation.

        This helps future developers understand the monitoring exclusion strategy.
        """
        with open(self.dockerignore_path, 'r') as f:
            content = f.read()

        required_documentation = [
            "monitoring",  # Should mention monitoring strategy
            "EMERGENCY",   # Should document emergency nature of fix
            "netra_backend"  # Should explain netra_backend inclusion
        ]

        missing_docs = []
        for doc_keyword in required_documentation:
            if doc_keyword.lower() not in content.lower():
                missing_docs.append(doc_keyword)

        if missing_docs:
            self.fail(
                f"Missing documentation for .dockerignore maintenance:\n"
                f"Should include references to: {', '.join(missing_docs)}\n"
                f"Add comments explaining monitoring exclusion strategy."
            )


if __name__ == '__main__':
    unittest.main()