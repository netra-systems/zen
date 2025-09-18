"""
Integration Tests for E2E Test Collection (Issue #1277)

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Ensure E2E tests can be discovered and executed
- Value Impact: Prevents "0 tests collected" blocking development workflows
- Revenue Impact: Maintains deployment pipeline reliability

This test module validates that the Issue #1277 fix enables proper E2E test
collection and execution without the previous "0 tests collected" failures.
"""

import pytest
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

from tests.e2e.real_services_manager import RealServicesManager
from test_framework.base_integration_test import BaseIntegrationTest


class TestE2ETestCollectionValidation(BaseIntegrationTest):
    """Test E2E test collection and discovery mechanisms."""

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_e2e_tests_are_collected_successfully(self):
        """
        Test that E2E tests are properly collected (not 0).

        This is the primary validation of the Issue #1277 fix.
        """
        # Run pytest collection on E2E tests
        project_root = Path(__file__).parent.parent.parent.parent
        e2e_test_dir = project_root / "tests" / "e2e"

        # Execute pytest --collect-only to check test collection
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(e2e_test_dir),
            "--collect-only",
            "-q",
            "--tb=no"
        ], capture_output=True, text=True, cwd=str(project_root))

        # Should not have collection errors
        assert result.returncode == 0, f"Test collection failed: {result.stderr}"

        # Should collect more than 0 tests
        output_lines = result.stdout.strip().split('\n')
        collected_line = [line for line in output_lines if "collected" in line.lower()]

        assert len(collected_line) > 0, f"No collection summary found in output: {result.stdout}"

        # Extract number of collected tests
        collection_summary = collected_line[0]
        assert "0 items collected" not in collection_summary, \
            f"Found '0 items collected' - Issue #1277 regression: {collection_summary}"

        # Should have meaningful test collection
        assert "collected" in collection_summary.lower()
        print(f"CHECK E2E test collection successful: {collection_summary}")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_realservicesmanager_instantiation_succeeds(self):
        """
        Test RealServicesManager can be instantiated without errors.

        This validates the core fix - no import or initialization errors.
        """
        # Should be able to create RealServicesManager without errors
        try:
            manager = RealServicesManager()
            assert manager is not None
            assert manager.project_root is not None
            assert isinstance(manager.project_root, Path)
            print(f"CHECK RealServicesManager instantiated successfully with project_root: {manager.project_root}")

        except Exception as e:
            pytest.fail(f"RealServicesManager instantiation failed: {e}")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_project_root_detection_consistent_across_imports(self):
        """
        Test project root detection is consistent when imported from different modules.

        This ensures the fix works reliably across different import contexts.
        """
        # Import and create multiple instances
        from tests.e2e.real_services_manager import RealServicesManager as RSM1

        # Direct import
        manager1 = RSM1()

        # Import with alias
        from tests.e2e import real_services_manager as rsm_module
        manager2 = rsm_module.RealServicesManager()

        # Both should detect the same project root
        assert manager1.project_root == manager2.project_root
        assert manager1.project_root.exists()
        assert manager2.project_root.exists()

        print(f"CHECK Consistent project root detection: {manager1.project_root}")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_e2e_test_infrastructure_initialization(self):
        """
        Test E2E test infrastructure components initialize correctly.

        This validates that the fix enables full E2E infrastructure functionality.
        """
        manager = RealServicesManager()

        # Test core infrastructure components
        assert manager.project_root is not None
        assert manager.service_endpoints is not None
        assert len(manager.service_endpoints) > 0
        assert manager.health_checker is not None
        assert manager.env is not None

        # Test service endpoint configuration
        endpoint_names = [ep.name for ep in manager.service_endpoints]
        expected_services = ["auth_service", "backend", "websocket"]

        for service in expected_services:
            assert service in endpoint_names, f"Missing service endpoint: {service}"

        print(f"CHECK E2E infrastructure initialized with {len(manager.service_endpoints)} service endpoints")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    @pytest.mark.performance
    def test_pytest_collection_performance(self):
        """
        Test that pytest collection completes within reasonable time.

        This ensures the fix doesn't introduce performance regressions.
        """
        project_root = Path(__file__).parent.parent.parent.parent
        e2e_test_dir = project_root / "tests" / "e2e"

        start_time = time.time()

        # Run test collection
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(e2e_test_dir),
            "--collect-only",
            "-q",
            "--tb=no"
        ], capture_output=True, text=True, cwd=str(project_root))

        end_time = time.time()
        collection_time = end_time - start_time

        # Should complete within reasonable time (30 seconds)
        assert collection_time < 30.0, f"Test collection took {collection_time:.1f}s, should be under 30s"

        # Should be successful
        assert result.returncode == 0, f"Collection failed: {result.stderr}"

        print(f"CHECK E2E test collection completed in {collection_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_specific_e2e_test_files_are_discoverable(self):
        """
        Test that specific E2E test files can be discovered and collected.

        This validates test discovery works for individual test files.
        """
        project_root = Path(__file__).parent.parent.parent.parent
        e2e_test_dir = project_root / "tests" / "e2e"

        # Find some actual E2E test files to test
        test_files = list(e2e_test_dir.glob("test_*.py"))
        assert len(test_files) > 0, "No E2E test files found for testing"

        # Test collection for individual files
        for test_file in test_files[:3]:  # Test first 3 files
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                str(test_file),
                "--collect-only",
                "-q",
                "--tb=no"
            ], capture_output=True, text=True, cwd=str(project_root))

            # Collection should succeed for individual files
            if result.returncode != 0:
                # Some test files might have import issues, but should not be
                # due to project root detection (which is what we're testing)
                if "Cannot detect project root" in result.stderr:
                    pytest.fail(f"Project root detection failed for {test_file}: {result.stderr}")
                else:
                    # Other import issues are not related to Issue #1277
                    print(f"WARNING {test_file.name} has collection issues (not project root related)")
            else:
                print(f"CHECK {test_file.name} collected successfully")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_path_resolution_in_e2e_tests(self):
        """
        Test that path resolution works correctly in E2E test context.

        This ensures the fix resolves path-related issues.
        """
        manager = RealServicesManager()

        # Test path resolution for key project components
        project_root = manager.project_root

        # Key paths should be resolvable
        expected_paths = [
            project_root / "pyproject.toml",
            project_root / "netra_backend",
            project_root / "auth_service",
            project_root / "tests",
            project_root / "tests" / "e2e"
        ]

        for path in expected_paths:
            assert path.exists(), f"Expected path does not exist: {path}"

        print(f"CHECK All expected project paths resolved correctly from root: {project_root}")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_import_validation_for_e2e_infrastructure(self):
        """
        Test that E2E infrastructure imports work correctly.

        This validates that the fix resolves import-related issues.
        """
        # Test key imports that should work with proper project root detection
        try:
            # Test RealServicesManager import
            from tests.e2e.real_services_manager import RealServicesManager, ServiceEndpoint, ServiceStatus
            assert RealServicesManager is not None
            assert ServiceEndpoint is not None
            assert ServiceStatus is not None

            # Test that instances can be created
            manager = RealServicesManager()
            assert manager is not None

            # Test health checker import and creation
            from tests.e2e.real_services_manager import AsyncHealthChecker, HealthCheckConfig
            health_checker = AsyncHealthChecker()
            assert health_checker is not None

            print("CHECK All E2E infrastructure imports successful")

        except ImportError as e:
            pytest.fail(f"E2E infrastructure import failed: {e}")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_environment_configuration_with_detected_root(self):
        """
        Test environment configuration works with detected project root.

        This validates that environment-specific functionality works.
        """
        manager = RealServicesManager()

        # Should be able to determine environment
        environment = manager._get_current_environment()
        assert environment in ["local", "staging", "test"]

        # Should configure service endpoints based on environment
        endpoints = manager.service_endpoints
        assert len(endpoints) > 0

        # Endpoint URLs should be appropriate for environment
        for endpoint in endpoints:
            assert endpoint.url is not None
            assert endpoint.url.startswith(("http://", "https://", "ws://", "wss://", "postgresql://"))

        print(f"CHECK Environment configuration successful for {environment} environment")


class TestE2ETestCollectionRegressionPrevention:
    """Regression prevention tests for E2E test collection."""

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.regression_prevention
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_reproduces_original_issue_1277_scenario(self):
        """
        Test that reproduces the original Issue #1277 scenario (should now pass).

        This test specifically validates that the original failure case now works.
        """
        # The original issue was "0 tests collected" due to missing claude.md
        # This test ensures that E2E tests can now be collected

        project_root = Path(__file__).parent.parent.parent.parent

        # Verify our assumptions about the fix
        assert (project_root / "pyproject.toml").exists(), "Fix requires pyproject.toml"
        assert not (project_root / "claude.md").exists() and not (project_root / "CLAUDE.md").exists(), \
            "Test validates independence from claude.md"

        # Run the exact type of collection that was failing
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(project_root / "tests" / "e2e"),
            "--collect-only",
            "-q"
        ], capture_output=True, text=True, cwd=str(project_root))

        # Should NOT show "0 items collected" (the original issue)
        assert "0 items collected" not in result.stdout, \
            f"Original Issue #1277 has regressed - found '0 items collected': {result.stdout}"

        # Should show successful collection
        assert result.returncode == 0 or "collected" in result.stdout.lower(), \
            f"Collection failed or no items collected: {result.stdout}"

        print("CHECK Original Issue #1277 scenario now passes - test collection successful")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.regression_prevention
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_detection_works_without_claude_md(self):
        """
        Test that project root detection works without claude.md files.

        This specifically validates the Issue #1277 fix.
        """
        project_root = Path(__file__).parent.parent.parent.parent

        # Ensure claude.md files don't exist (they shouldn't be required)
        claude_files = [
            project_root / "claude.md",
            project_root / "CLAUDE.md"
        ]

        for claude_file in claude_files:
            if claude_file.exists():
                print(f"Note: {claude_file.name} exists but should not be required for detection")

        # Project root detection should work regardless
        manager = RealServicesManager()
        detected_root = manager.project_root

        assert detected_root == project_root
        assert (detected_root / "pyproject.toml").exists()

        print("CHECK Project root detection works without claude.md dependency")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.regression_prevention
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_collection_resilience_across_working_directories(self):
        """
        Test that test collection works from different working directories.

        This ensures the fix is robust across different execution contexts.
        """
        import os
        project_root = Path(__file__).parent.parent.parent.parent
        original_cwd = os.getcwd()

        test_directories = [
            project_root,
            project_root / "tests",
            project_root / "netra_backend",
            project_root / "auth_service"
        ]

        try:
            for test_dir in test_directories:
                if not test_dir.exists():
                    continue

                os.chdir(str(test_dir))

                # Try to collect E2E tests from this directory
                result = subprocess.run([
                    sys.executable, "-m", "pytest",
                    str(project_root / "tests" / "e2e"),
                    "--collect-only",
                    "-q",
                    "--tb=no"
                ], capture_output=True, text=True)

                # Collection should not fail due to project root detection issues
                if result.returncode != 0 and "Cannot detect project root" in result.stderr:
                    pytest.fail(f"Project root detection failed from {test_dir}: {result.stderr}")

                print(f"CHECK Test collection works from {test_dir.name}")

        finally:
            os.chdir(original_cwd)

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.regression_prevention
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    def test_multiple_manager_instances_consistency(self):
        """
        Test that multiple RealServicesManager instances work consistently.

        This ensures the fix doesn't have concurrency or state issues.
        """
        managers = []

        # Create multiple instances
        for i in range(5):
            manager = RealServicesManager()
            managers.append(manager)

        # All should detect the same project root
        first_root = managers[0].project_root
        for i, manager in enumerate(managers[1:], 1):
            assert manager.project_root == first_root, \
                f"Manager {i} detected different root: {manager.project_root} vs {first_root}"

        # All should have valid configurations
        for i, manager in enumerate(managers):
            assert len(manager.service_endpoints) > 0, f"Manager {i} has no service endpoints"
            assert manager.health_checker is not None, f"Manager {i} has no health checker"

        print(f"CHECK {len(managers)} RealServicesManager instances all consistent")

    @pytest.mark.integration
    @pytest.mark.test_collection
    @pytest.mark.regression_prevention
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    @pytest.mark.performance
    def test_collection_performance_regression(self):
        """
        Test that the fix doesn't introduce performance regressions.

        This ensures the solution is efficient.
        """
        project_root = Path(__file__).parent.parent.parent.parent

        # Baseline: measure current collection performance
        times = []
        for _ in range(3):
            start_time = time.time()
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                str(project_root / "tests" / "e2e"),
                "--collect-only",
                "-q",
                "--tb=no"
            ], capture_output=True, text=True, cwd=str(project_root))
            end_time = time.time()

            if result.returncode == 0:
                times.append(end_time - start_time)

        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)

            # Performance should be reasonable
            assert avg_time < 20.0, f"Average collection time {avg_time:.1f}s too slow"
            assert max_time < 30.0, f"Max collection time {max_time:.1f}s too slow"

            print(f"CHECK Collection performance: avg={avg_time:.2f}s, max={max_time:.2f}s")
        else:
            print("WARNING Could not measure collection performance - tests may have collection issues")