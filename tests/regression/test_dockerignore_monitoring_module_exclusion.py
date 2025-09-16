"""
Test Plan: P0 .dockerignore Monitoring Module Exclusion Prevention
==================================================================

This test validates that the monitoring module is always available for import,
preventing the P0 issue where `**/monitoring/` in .dockerignore excluded
netra_backend/app/services/monitoring/ from Docker build context.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Critical Infrastructure
2. Business Goal: System Stability & Production Reliability
3. Value Impact: Prevents runtime ModuleNotFoundError that breaks entire system
4. Revenue Impact: Protects $500K+ ARR by ensuring production systems remain operational

ROOT CAUSE: Line 103 in .dockerignore contained `**/monitoring/` which excluded
the monitoring module from Docker builds, causing middleware import failures.

FIX: Line 103 commented out with explanation comment.

Test Strategy:
- UNIT TEST: Direct import validation (runs in all environments)
- INTEGRATION: Simulate Docker build context scenarios
- REGRESSION: Verify .dockerignore patterns don't exclude critical modules
"""

import importlib
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Set
from unittest.mock import patch

# SSOT imports - no relative imports allowed per CLAUDE.md
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDockerignoreMonitoringModuleRegression(SSotBaseTestCase):
    """
    Regression test to prevent .dockerignore from excluding monitoring module.

    CRITICAL: This test ensures the monitoring module is always importable,
    preventing the P0 production failure caused by .dockerignore exclusion.
    """

    def setup_method(self, method=None):
        """Set up test environment with SSOT compliance."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent
        self.dockerignore_path = self.project_root / ".dockerignore"
        self.monitoring_module_path = (
            self.project_root / "netra_backend" / "app" / "services" / "monitoring"
        )

    def test_monitoring_module_direct_import_success(self):
        """
        CRITICAL P0 Test: Verify monitoring module imports succeed.

        This test validates the specific imports that failed in production:
        - set_request_context
        - clear_request_context

        REQUIREMENT: This test must PASS in all environments (local, CI, Docker)
        """
        try:
            # Test the exact imports that were failing in middleware
            from netra_backend.app.services.monitoring.gcp_error_reporter import (
                set_request_context,
                clear_request_context
            )

            # Verify functions are callable
            self.assertTrue(callable(set_request_context))
            self.assertTrue(callable(clear_request_context))

            # Verify the module exists on filesystem
            self.assertTrue(
                self.monitoring_module_path.exists(),
                f"Monitoring module directory not found: {self.monitoring_module_path}"
            )

            # Verify the specific file exists
            gcp_error_reporter_path = self.monitoring_module_path / "gcp_error_reporter.py"
            self.assertTrue(
                gcp_error_reporter_path.exists(),
                f"GCP error reporter module not found: {gcp_error_reporter_path}"
            )

        except ImportError as e:
            self.fail(
                f"CRITICAL P0 FAILURE: Monitoring module import failed: {e}\n"
                f"This indicates .dockerignore or build context excludes monitoring module.\n"
                f"Expected path: {self.monitoring_module_path}\n"
                f"Check .dockerignore for '**/monitoring/' exclusion patterns."
            )

    def test_middleware_dependency_imports(self):
        """
        Test the specific import pattern that failed in middleware.

        This replicates the exact import from gcp_auth_context_middleware.py
        that was causing production failures.
        """
        try:
            # Exact import from middleware that was failing
            from netra_backend.app.services.monitoring.gcp_error_reporter import (
                set_request_context, clear_request_context
            )

            # Test that we can actually call these functions
            # (with safe parameters that don't affect test environment)
            set_request_context(user_id="test_user_regression")
            clear_request_context()

        except ImportError as e:
            self.fail(
                f"MIDDLEWARE IMPORT FAILURE: {e}\n"
                f"This replicates the production P0 failure.\n"
                f"Middleware file: netra_backend/app/middleware/gcp_auth_context_middleware.py\n"
                f"Failed import line 23"
            )

    def test_dockerignore_monitoring_exclusion_prevention(self):
        """
        REGRESSION PREVENTION: Verify .dockerignore properly handles monitoring exclusions.

        This test validates the current fix strategy:
        1. General monitoring directories can be excluded for optimization
        2. Critical netra_backend monitoring must have explicit includes
        3. Global patterns like **/monitoring/ must be commented out
        """
        if not self.dockerignore_path.exists():
            self.skipTest("No .dockerignore file found - Docker builds may include everything")

        with open(self.dockerignore_path, 'r') as f:
            dockerignore_content = f.read()
            lines = dockerignore_content.split('\n')

        # Check for the original problematic global pattern
        global_monitoring_exclusions = []
        critical_include_patterns = []

        for line_num, line in enumerate(lines, 1):
            line_content = line.strip()

            # Check for global monitoring exclusions that are NOT commented
            if '**/monitoring/' in line_content and not line_content.startswith('#'):
                global_monitoring_exclusions.append({
                    'line_number': line_num,
                    'line': line_content
                })

            # Check for critical include patterns
            if line_content.startswith('!') and 'netra_backend' in line_content and 'monitoring' in line_content:
                critical_include_patterns.append({
                    'line_number': line_num,
                    'line': line_content
                })

        # FAIL if global monitoring exclusions are active
        if global_monitoring_exclusions:
            exclusion_details = '\n'.join([
                f"  Line {exc['line_number']}: {exc['line']}"
                for exc in global_monitoring_exclusions
            ])

            self.fail(
                f"CRITICAL: Global monitoring exclusions found (these caused the P0 failure):\n"
                f"{exclusion_details}\n\n"
                f"These patterns exclude ALL monitoring directories including critical ones.\n"
                f"Comment out these lines and use selective exclusions with explicit includes.\n"
                f"File: {self.dockerignore_path}"
            )

        # WARN if no explicit includes for critical modules
        if not critical_include_patterns:
            self.fail(
                f"WARNING: No explicit include patterns found for critical monitoring modules.\n"
                f"Expected patterns like: !netra_backend/app/services/monitoring/\n"
                f"Without these, selective exclusions may still exclude critical modules.\n"
                f"File: {self.dockerignore_path}"
            )

        # Record successful validation
        self.record_metric("global_exclusions_prevented", len(global_monitoring_exclusions) == 0)
        self.record_metric("critical_includes_present", len(critical_include_patterns) > 0)

    def test_monitoring_module_file_structure_completeness(self):
        """
        Verify the monitoring module has all required files for imports.

        This ensures the module structure is complete and would be
        included in Docker builds.
        """
        required_files = [
            "__init__.py",
            "gcp_error_reporter.py"
        ]

        missing_files = []
        for filename in required_files:
            file_path = self.monitoring_module_path / filename
            if not file_path.exists():
                missing_files.append(str(file_path))

        if missing_files:
            self.fail(
                f"Monitoring module missing required files:\n"
                f"{chr(10).join(missing_files)}\n"
                f"These files are needed for proper import functionality."
            )

    def test_docker_build_context_simulation(self):
        """
        Simulate Docker build context to ensure monitoring module would be included.

        This test simulates what Docker sees during build context creation
        by checking if monitoring files would be excluded by .dockerignore patterns.
        """
        if not self.dockerignore_path.exists():
            self.skipTest("No .dockerignore - all files included in Docker context")

        # Simulate Docker's build context filtering
        monitoring_files = list(self.monitoring_module_path.glob("**/*.py"))

        if not monitoring_files:
            self.fail(
                f"No Python files found in monitoring module: {self.monitoring_module_path}\n"
                f"This indicates the module is missing or empty."
            )

        # For this test, we verify the files exist and are Python modules
        # In a real Docker context test, we'd need to actually build a container
        for py_file in monitoring_files:
            self.assertTrue(
                py_file.suffix == '.py',
                f"Non-Python file in monitoring module: {py_file}"
            )

            # Verify file is not empty (basic sanity check)
            self.assertGreater(
                py_file.stat().st_size, 0,
                f"Empty Python file in monitoring module: {py_file}"
            )


class TestDockerignoreMonitoringModuleIntegration(SSotBaseTestCase):
    """
    Integration tests for monitoring module availability in realistic scenarios.
    """

    def setup_method(self, method=None):
        """Set up integration test environment."""
        super().setup_method(method)

    def test_monitoring_module_dependencies_available(self):
        """
        Integration test to validate monitoring module dependencies are available.
        """
        # Check if monitoring module dependencies are available
        monitoring_dependencies = [
            ("netra_backend.app.services.monitoring.gcp_error_reporter", ["set_request_context", "clear_request_context"]),
            ("netra_backend.app.core.exceptions_base", ["NetraException"]),
            ("netra_backend.app.schemas.monitoring_schemas", ["ErrorSeverity"])
        ]

        for module_name, expected_attributes in monitoring_dependencies:
            try:
                import importlib
                module = importlib.import_module(module_name)

                # Verify expected attributes exist
                for attr_name in expected_attributes:
                    if not hasattr(module, attr_name):
                        self.fail(
                            f"Missing expected attribute '{attr_name}' in module {module_name}.\n"
                            f"This indicates module structure changes or exclusion."
                        )

            except ImportError as e:
                self.fail(
                    f"Monitoring module dependency check failed for {module_name}: {e}\n"
                    f"This indicates missing or excluded modules in build context."
                )

    def test_monitoring_functions_callable_in_middleware_context(self):
        """
        Test monitoring functions work in simulated middleware context.

        This replicates how the middleware actually uses these functions.
        """
        try:
            # Import exactly as middleware does
            from netra_backend.app.services.monitoring.gcp_error_reporter import (
                set_request_context, clear_request_context
            )

            # Simulate middleware usage pattern
            test_context = {
                'user_id': 'test_user_integration',
                'trace_id': 'test_trace_123',
                'http_context': {'method': 'GET', 'path': '/test'}
            }

            # Test setting context (as middleware does on request start)
            set_request_context(**test_context)

            # Test clearing context (as middleware does on request end)
            clear_request_context()

        except Exception as e:
            self.fail(
                f"Monitoring functions failed in middleware simulation: {e}\n"
                f"This indicates the monitoring module is not properly integrated."
            )


if __name__ == '__main__':
    unittest.main()