"""
CI/CD Integration Test: .dockerignore Validation
================================================

This test suite validates .dockerignore patterns during CI/CD to prevent
future P0 production failures from Docker build context exclusions.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - DevOps & CI/CD Pipeline
2. Business Goal: Prevent Production Deployment Failures
3. Value Impact: Catches .dockerignore issues before deployment
4. Revenue Impact: Protects $500K+ ARR by preventing container build failures

INTEGRATION POINTS:
- Pre-deployment validation
- Docker build context simulation
- Critical module availability verification
- Automated regression detection

This test can be integrated into CI/CD pipelines to catch .dockerignore
issues before they reach production environments.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple
import shutil

# SSOT imports - no relative imports allowed per CLAUDE.md
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDockerignoreCICDValidation(SSotBaseTestCase):
    """
    CI/CD validation tests for .dockerignore critical module inclusion.

    These tests can be run in CI/CD pipelines to prevent deployment
    of .dockerignore configurations that would break production.
    """

    def setUp(self):
        """Set up CI/CD validation test environment."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.dockerignore_path = self.project_root / ".dockerignore"

        # Critical paths that MUST be available in Docker builds
        self.critical_paths = [
            "netra_backend/app/services/monitoring/gcp_error_reporter.py",
            "netra_backend/app/services/monitoring/__init__.py",
            "netra_backend/app/middleware/gcp_auth_context_middleware.py",
            "shared/isolated_environment.py",
            "shared/types.py"
        ]

        # Paths that SHOULD be excluded (for optimization)
        self.should_exclude_paths = [
            "monitoring/test_data/",
            "deployment/monitoring/logs/",
            "tests/monitoring/fixtures/",
            "docs/monitoring/",
            ".git/monitoring/"
        ]

    def test_critical_modules_in_simulated_docker_context(self):
        """
        CRITICAL CI/CD TEST: Simulate Docker build context creation.

        This test simulates what Docker sees during build context creation
        and validates that critical modules would be included.
        """
        if not self.dockerignore_path.exists():
            self.skipTest("No .dockerignore file - all files would be included")

        # Create temporary directory to simulate Docker build context
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Copy project structure to temp directory (simulating Docker context)
            excluded_files, included_files = self._simulate_docker_context_copy(
                source_dir=self.project_root,
                dest_dir=temp_path
            )

            # Validate critical modules are included
            missing_critical_files = []
            for critical_path in self.critical_paths:
                expected_path = temp_path / critical_path
                if not expected_path.exists():
                    missing_critical_files.append(critical_path)

            if missing_critical_files:
                self.fail(
                    f"CRITICAL CI/CD FAILURE: Missing critical files in Docker context:\n"
                    f"{chr(10).join(f'  - {path}' for path in missing_critical_files)}\n\n"
                    f"These files are required for production container startup.\n"
                    f"Update .dockerignore to include these paths.\n"
                    f"Total files excluded: {len(excluded_files)}\n"
                    f"Total files included: {len(included_files)}"
                )

            # Verify optimization is working (some files should be excluded)
            if len(excluded_files) == 0:
                self.fail(
                    "WARNING: No files excluded by .dockerignore.\n"
                    "This may indicate inefficient Docker build context.\n"
                    "Consider adding exclusion patterns for test files, docs, etc."
                )

            # Record CI/CD metrics
            self.record_metric("docker_context_files_included", len(included_files))
            self.record_metric("docker_context_files_excluded", len(excluded_files))
            self.record_metric("critical_modules_validation_passed", True)

    def test_monitoring_module_import_in_simulated_container(self):
        """
        CI/CD TEST: Validate monitoring imports work in simulated container.

        This simulates the container environment to ensure imports work.
        """
        # Create minimal Python environment simulation
        import sys
        import importlib.util

        # Test direct import of critical monitoring module
        monitoring_module_path = (
            self.project_root / "netra_backend" / "app" / "services" /
            "monitoring" / "gcp_error_reporter.py"
        )

        if not monitoring_module_path.exists():
            self.fail(
                f"CRITICAL: Monitoring module not found at {monitoring_module_path}\n"
                f"This indicates the module structure has changed or is missing."
            )

        # Load module directly (simulating container import)
        try:
            spec = importlib.util.spec_from_file_location(
                "gcp_error_reporter",
                monitoring_module_path
            )
            module = importlib.util.module_from_spec(spec)

            # This would fail if dependencies are missing
            spec.loader.exec_module(module)

            # Verify critical functions exist
            required_functions = ['set_request_context', 'clear_request_context']
            for func_name in required_functions:
                if not hasattr(module, func_name):
                    self.fail(
                        f"CRITICAL: Required function '{func_name}' not found in monitoring module.\n"
                        f"This indicates module structure changes."
                    )

            self.record_metric("container_import_simulation_passed", True)

        except Exception as e:
            self.fail(
                f"CRITICAL CI/CD FAILURE: Container import simulation failed: {e}\n"
                f"This indicates the monitoring module would fail in container environment.\n"
                f"Check dependencies and module structure."
            )

    def test_dockerignore_syntax_validation(self):
        """
        CI/CD TEST: Validate .dockerignore syntax and patterns.

        This catches syntax errors that could cause unexpected behavior.
        """
        with open(self.dockerignore_path, 'r') as f:
            lines = f.read().split('\n')

        syntax_errors = []
        pattern_warnings = []

        for line_num, line in enumerate(lines, 1):
            line_content = line.strip()

            # Skip empty lines and comments
            if not line_content or line_content.startswith('#'):
                continue

            # Check for common syntax issues
            if line_content.startswith('/'):
                pattern_warnings.append(
                    f"Line {line_num}: Pattern starts with '/' - may not work as expected: {line_content}"
                )

            if ' ' in line_content and not line_content.startswith('#'):
                syntax_errors.append(
                    f"Line {line_num}: Pattern contains spaces: {line_content}"
                )

            # Check for dangerous glob patterns
            if '**/**' in line_content:
                pattern_warnings.append(
                    f"Line {line_num}: Redundant '**/**' pattern: {line_content}"
                )

        # Report syntax errors (fail build)
        if syntax_errors:
            self.fail(
                f"CRITICAL CI/CD FAILURE: .dockerignore syntax errors:\n"
                f"{chr(10).join(syntax_errors)}\n\n"
                f"Fix these syntax errors before deployment."
            )

        # Report warnings (don't fail build but log)
        if pattern_warnings:
            for warning in pattern_warnings:
                self.logger.warning(f"dockerignore pattern warning: {warning}")

        self.record_metric("dockerignore_syntax_valid", True)

    def test_build_context_size_optimization(self):
        """
        CI/CD TEST: Validate Docker build context size optimization.

        This ensures .dockerignore is effectively reducing build context size.
        """
        # Calculate total project size
        total_size = self._calculate_directory_size(self.project_root)

        # Simulate Docker context filtering
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            excluded_files, included_files = self._simulate_docker_context_copy(
                source_dir=self.project_root,
                dest_dir=temp_path
            )

            # Calculate filtered size
            filtered_size = self._calculate_directory_size(temp_path)

            # Calculate optimization percentage
            if total_size > 0:
                size_reduction = ((total_size - filtered_size) / total_size) * 100
            else:
                size_reduction = 0

            # Expect significant size reduction (at least 20% for efficient builds)
            min_expected_reduction = 20.0

            if size_reduction < min_expected_reduction:
                self.fail(
                    f"BUILD CONTEXT OPTIMIZATION WARNING:\n"
                    f"Size reduction: {size_reduction:.1f}% (expected: >{min_expected_reduction}%)\n"
                    f"Total size: {total_size:,} bytes\n"
                    f"Filtered size: {filtered_size:,} bytes\n"
                    f"Consider adding more exclusion patterns to .dockerignore"
                )

            # Record optimization metrics
            self.record_metric("build_context_size_reduction_percent", size_reduction)
            self.record_metric("total_project_size_bytes", total_size)
            self.record_metric("filtered_context_size_bytes", filtered_size)

    def test_deployment_pipeline_validation(self):
        """
        CI/CD TEST: Complete deployment pipeline validation.

        This test runs all validations that should pass before deployment.
        """
        validation_results = {}

        # Test 1: Critical modules accessible
        try:
            from netra_backend.app.services.monitoring.gcp_error_reporter import (
                set_request_context, clear_request_context
            )
            validation_results['monitoring_import'] = True
        except ImportError:
            validation_results['monitoring_import'] = False

        # Test 2: .dockerignore exists and is valid
        validation_results['dockerignore_exists'] = self.dockerignore_path.exists()

        # Test 3: Emergency fix documentation present
        if validation_results['dockerignore_exists']:
            with open(self.dockerignore_path, 'r') as f:
                content = f.read().lower()
            validation_results['emergency_fix_documented'] = (
                'emergency' in content or 'monitoring module required' in content
            )
        else:
            validation_results['emergency_fix_documented'] = False

        # Test 4: No active global monitoring exclusions
        validation_results['no_global_monitoring_exclusion'] = (
            self._check_no_global_monitoring_exclusion()
        )

        # Evaluate overall pipeline readiness
        failed_validations = [
            test_name for test_name, passed in validation_results.items()
            if not passed
        ]

        if failed_validations:
            self.fail(
                f"DEPLOYMENT PIPELINE VALIDATION FAILED:\n"
                f"Failed tests: {', '.join(failed_validations)}\n"
                f"All validations: {validation_results}\n\n"
                f"Fix these issues before deploying to production."
            )

        # Record pipeline validation success
        self.record_metric("deployment_pipeline_validation_passed", True)
        self.record_metric("validation_results", validation_results)

    def _simulate_docker_context_copy(self, source_dir: Path, dest_dir: Path) -> Tuple[List[str], List[str]]:
        """
        Simulate Docker build context creation with .dockerignore filtering.

        Args:
            source_dir: Source project directory
            dest_dir: Destination directory (simulated container context)

        Returns:
            Tuple of (excluded_files, included_files)
        """
        import fnmatch
        import pathspec

        # Read .dockerignore patterns
        dockerignore_patterns = []
        if self.dockerignore_path.exists():
            with open(self.dockerignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        dockerignore_patterns.append(line)

        # Create pathspec for Docker-style gitignore patterns
        spec = pathspec.PathSpec.from_lines('gitwildmatch', dockerignore_patterns)

        excluded_files = []
        included_files = []

        # Walk through source directory
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(source_dir)
                relative_str = str(relative_path).replace('\\', '/')

                # Check if file should be excluded
                if spec.match_file(relative_str):
                    excluded_files.append(relative_str)
                else:
                    # Copy file to destination
                    dest_file_path = dest_dir / relative_path
                    dest_file_path.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        shutil.copy2(file_path, dest_file_path)
                        included_files.append(relative_str)
                    except Exception as e:
                        self.logger.warning(f"Failed to copy {file_path}: {e}")

        return excluded_files, included_files

    def _calculate_directory_size(self, directory: Path) -> int:
        """
        Calculate total size of directory in bytes.

        Args:
            directory: Directory to calculate size for

        Returns:
            Total size in bytes
        """
        total_size = 0
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.exists():
                        total_size += file_path.stat().st_size
        except Exception as e:
            self.logger.warning(f"Error calculating directory size: {e}")

        return total_size

    def _check_no_global_monitoring_exclusion(self) -> bool:
        """
        Check that no global monitoring exclusion patterns are active.

        Returns:
            True if no dangerous global patterns found
        """
        if not self.dockerignore_path.exists():
            return True

        with open(self.dockerignore_path, 'r') as f:
            lines = f.read().split('\n')

        dangerous_patterns = ['**/monitoring/', '**/monitoring']

        for line in lines:
            line_content = line.strip()
            # Skip comments
            if line_content.startswith('#'):
                continue

            for pattern in dangerous_patterns:
                if pattern in line_content:
                    return False

        return True


class TestDockerignorePreDeploymentValidation(SSotBaseTestCase):
    """
    Pre-deployment validation tests specifically for production deployments.

    These tests should be run as the final gate before production deployment.
    """

    def setUp(self):
        """Set up pre-deployment validation environment."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent

    def test_production_readiness_checklist(self):
        """
        FINAL CI/CD GATE: Production readiness checklist.

        This test validates all critical requirements are met for production.
        """
        checklist = {
            'monitoring_module_importable': False,
            'dockerignore_optimized': False,
            'critical_paths_included': False,
            'emergency_fix_documented': False,
            'no_syntax_errors': False
        }

        # Check 1: Monitoring module importable
        try:
            from netra_backend.app.services.monitoring.gcp_error_reporter import (
                set_request_context, clear_request_context
            )
            # Test actual function calls
            set_request_context(user_id="production_readiness_test")
            clear_request_context()
            checklist['monitoring_module_importable'] = True
        except Exception:
            pass

        # Check 2: .dockerignore optimized (some exclusions present)
        dockerignore_path = self.project_root / ".dockerignore"
        if dockerignore_path.exists():
            with open(dockerignore_path, 'r') as f:
                content = f.read()
                active_patterns = [
                    line.strip() for line in content.split('\n')
                    if line.strip() and not line.strip().startswith('#')
                ]
                checklist['dockerignore_optimized'] = len(active_patterns) > 5

        # Check 3: Critical paths exist
        critical_paths = [
            "netra_backend/app/services/monitoring/gcp_error_reporter.py",
            "netra_backend/app/middleware/gcp_auth_context_middleware.py"
        ]

        all_critical_exist = all(
            (self.project_root / path).exists() for path in critical_paths
        )
        checklist['critical_paths_included'] = all_critical_exist

        # Check 4: Emergency fix documented
        if dockerignore_path.exists():
            with open(dockerignore_path, 'r') as f:
                content = f.read().lower()
                checklist['emergency_fix_documented'] = (
                    'emergency' in content and 'monitoring' in content
                )

        # Check 5: No syntax errors in .dockerignore
        if dockerignore_path.exists():
            with open(dockerignore_path, 'r') as f:
                lines = f.read().split('\n')
                has_syntax_errors = any(
                    ' ' in line.strip() and not line.strip().startswith('#')
                    for line in lines
                    if line.strip()
                )
                checklist['no_syntax_errors'] = not has_syntax_errors

        # Evaluate production readiness
        failed_checks = [check for check, passed in checklist.items() if not passed]

        if failed_checks:
            self.fail(
                f"PRODUCTION DEPLOYMENT BLOCKED:\n"
                f"Failed readiness checks: {failed_checks}\n"
                f"Full checklist: {checklist}\n\n"
                f"All checks must pass before production deployment.\n"
                f"Fix these issues and re-run validation."
            )

        # Record successful production readiness
        self.record_metric("production_readiness_validated", True)
        self.record_metric("production_readiness_checklist", checklist)


if __name__ == '__main__':
    unittest.main()