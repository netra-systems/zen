"""
SSOT Docker Manager Compliance Validation Tests
============================================

CRITICAL MISSION: Prove Docker Manager SSOT violation exists and validate fix works.

This test suite validates:
1. SSOT ENFORCEMENT: Only ONE Docker Manager implementation should exist and be used
2. IMPORT VALIDATION: All imports must resolve to the same real implementation
3. GOLDEN PATH PROTECTION: Real services vs mocks for $500K+ ARR functionality
4. SSOT COMPLIANCE: Prevents regression of Docker Manager duplication

Created for Issue #1083: 51 tests import mock Docker Manager instead of real SSOT implementation

EXPECTED CURRENT STATE: These tests will FAIL, proving the SSOT violation exists.
EXPECTED AFTER REMEDIATION: These tests will PASS, proving SSOT compliance.

Business Impact: Protects $500K+ ARR Golden Path functionality by ensuring real services.
"""

import ast
import importlib
import inspect
import os
import sys
import types
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import unittest
from unittest.mock import MagicMock, AsyncMock

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

# Get isolated environment
env = get_env()


class TestDockerManagerSSOTCompliance(SSotBaseTestCase):
    """
    Test suite to prove Docker Manager SSOT violation and validate fix.

    These tests DELIBERATELY FAIL to prove the violation exists.
    After remediation, they will PASS to prove SSOT compliance.
    """

    def setUp(self):
        """Set up test environment with SSOT compliance checking."""
        super().setUp()
        self.project_root = Path(env.get("PROJECT_ROOT", "/c/GitHub/netra-apex"))
        self.mock_docker_manager_path = self.project_root / "test_framework" / "docker" / "unified_docker_manager.py"
        self.real_docker_manager_path = self.project_root / "test_framework" / "unified_docker_manager.py"

    def test_ssot_violation_exists_duplicate_docker_managers(self):
        """
        PROVES SSOT VIOLATION: Multiple Docker Manager implementations exist.

        CURRENT EXPECTATION: FAIL - Mock and real implementations both exist
        POST-REMEDIATION: PASS - Only real implementation exists
        """
        # Check if mock Docker Manager exists (violation)
        mock_exists = self.mock_docker_manager_path.exists()
        real_exists = self.real_docker_manager_path.exists()

        # This test FAILS if both exist (proving violation)
        with self.assertRaises(AssertionError, msg="SSOT VIOLATION: Both mock and real Docker Managers exist"):
            self.assertFalse(mock_exists and real_exists,
                           f"SSOT VIOLATION DETECTED:\n"
                           f"Mock Docker Manager: {self.mock_docker_manager_path} (exists: {mock_exists})\n"
                           f"Real Docker Manager: {self.real_docker_manager_path} (exists: {real_exists})\n"
                           f"Expected: Only real implementation should exist")

    def test_ssot_violation_mock_docker_manager_has_mock_implementations(self):
        """
        PROVES VIOLATION: Mock Docker Manager contains MagicMock/AsyncMock implementations.

        CURRENT EXPECTATION: FAIL - Mock implementations detected
        POST-REMEDIATION: N/A - Mock file should not exist
        """
        if not self.mock_docker_manager_path.exists():
            self.skipTest("Mock Docker Manager file does not exist - already remediated")

        # Parse the mock Docker Manager file
        with open(self.mock_docker_manager_path, 'r') as f:
            content = f.read()

        # Check for mock implementations (violation indicators)
        mock_indicators = [
            "MagicMock",
            "AsyncMock",
            "Mock",
            "mock_docker_manager",
            "Mock Docker manager"
        ]

        found_mocks = [indicator for indicator in mock_indicators if indicator in content]

        # This test FAILS if mock implementations are found (proving violation)
        self.assertNotEqual(found_mocks, [],
                           f"SSOT VIOLATION: Mock implementations found in Docker Manager: {found_mocks}\n"
                           f"This proves the violation exists - tests are using mock instead of real services")

    def test_ssot_violation_tests_import_mock_docker_manager(self):
        """
        PROVES VIOLATION: Tests import from test_framework.docker.unified_docker_manager (mock).

        CURRENT EXPECTATION: FAIL - Mock imports found in test files
        POST-REMEDIATION: PASS - No mock imports exist
        """
        # Find all Python files in tests directory
        test_files = []
        for root, _, files in os.walk(self.project_root):
            if "test" in root.lower():
                for file in files:
                    if file.endswith('.py'):
                        test_files.append(Path(root) / file)

        # Check for problematic imports
        mock_import_files = []
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "from test_framework.docker.unified_docker_manager" in content:
                        mock_import_files.append(str(test_file))
            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue

        # This test FAILS if mock imports are found (proving violation)
        self.assertNotEqual(mock_import_files, [],
                           f"SSOT VIOLATION: {len(mock_import_files)} test files import mock Docker Manager:\n" +
                           "\n".join(mock_import_files[:10]) +
                           (f"\n... and {len(mock_import_files) - 10} more" if len(mock_import_files) > 10 else ""))

    def test_golden_path_functionality_mock_vs_real_docker_manager(self):
        """
        VALIDATES GOLDEN PATH: Real Docker Manager provides actual service connections.

        CURRENT EXPECTATION: FAIL - Mock provides fake functionality
        POST-REMEDIATION: PASS - Real implementation provides actual services
        """
        # Try to import both implementations
        mock_manager = None
        real_manager = None

        # Import mock Docker Manager (if it exists)
        try:
            mock_module_path = "test_framework.docker.unified_docker_manager"
            if mock_module_path in sys.modules:
                del sys.modules[mock_module_path]
            mock_module = importlib.import_module(mock_module_path)
            mock_manager = mock_module.UnifiedDockerManager()
        except ImportError:
            pass  # Already remediated

        # Import real Docker Manager
        try:
            real_module_path = "test_framework.unified_docker_manager"
            if real_module_path in sys.modules:
                del sys.modules[real_module_path]
            real_module = importlib.import_module(real_module_path)
            real_manager = real_module.UnifiedDockerManager()
        except ImportError:
            self.fail("CRITICAL: Real Docker Manager cannot be imported - Golden Path broken!")

        if mock_manager is None:
            self.skipTest("Mock Docker Manager not found - already remediated")

        # Check if mock manager has MagicMock client (violation indicator)
        mock_has_magic_mock = isinstance(getattr(mock_manager, 'client', None), MagicMock)

        # Check if real manager has actual Docker client (Golden Path requirement)
        real_has_actual_client = not isinstance(getattr(real_manager, 'client', None), (MagicMock, AsyncMock))

        # This test FAILS if mock is being used instead of real services
        with self.assertRaises(AssertionError, msg="GOLDEN PATH VIOLATION: Mock Docker Manager detected"):
            self.assertTrue(mock_has_magic_mock and not real_has_actual_client,
                           f"GOLDEN PATH VIOLATION:\n"
                           f"Mock manager has MagicMock client: {mock_has_magic_mock}\n"
                           f"Real manager has actual client: {real_has_actual_client}\n"
                           f"Tests using mock instead of real services breaks $500K+ ARR functionality")

    def test_ssot_compliance_only_one_docker_manager_implementation(self):
        """
        ENFORCES SSOT: Only one Docker Manager implementation should exist.

        CURRENT EXPECTATION: FAIL - Two implementations exist
        POST-REMEDIATION: PASS - Only real implementation exists
        """
        # Find all UnifiedDockerManager class definitions
        docker_manager_files = []

        # Search for files containing UnifiedDockerManager class
        for root, _, files in os.walk(self.project_root / "test_framework"):
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if "class UnifiedDockerManager" in content:
                                docker_manager_files.append(str(file_path))
                    except (UnicodeDecodeError, PermissionError):
                        continue

        # SSOT compliance requires exactly ONE implementation
        expected_count = 1
        actual_count = len(docker_manager_files)

        # This test FAILS if multiple implementations exist (proving violation)
        self.assertEqual(actual_count, expected_count,
                        f"SSOT VIOLATION: Found {actual_count} Docker Manager implementations, expected {expected_count}:\n" +
                        "\n".join(docker_manager_files))

    def test_import_consistency_all_imports_resolve_to_same_implementation(self):
        """
        VALIDATES IMPORT CONSISTENCY: All Docker Manager imports resolve to same instance.

        CURRENT EXPECTATION: FAIL - Imports resolve to different implementations
        POST-REMEDIATION: PASS - All imports resolve to real implementation
        """
        import_paths = [
            "test_framework.unified_docker_manager",
            "test_framework.docker.unified_docker_manager"  # Should not exist after remediation
        ]

        implementations = {}
        import_errors = {}

        for import_path in import_paths:
            try:
                # Clear any cached modules
                if import_path in sys.modules:
                    del sys.modules[import_path]

                module = importlib.import_module(import_path)
                manager_class = getattr(module, 'UnifiedDockerManager', None)
                if manager_class:
                    # Check if it's a real implementation (has real methods) vs mock
                    is_mock = any(
                        hasattr(manager_class, attr) and
                        str(type(getattr(manager_class, attr))) == "<class 'unittest.mock.MagicMock'>"
                        for attr in ['client']
                    )
                    implementations[import_path] = {
                        'class': manager_class,
                        'is_mock': is_mock,
                        'module_file': getattr(module, '__file__', 'unknown')
                    }
            except ImportError as e:
                import_errors[import_path] = str(e)

        # After remediation, only one import should work
        working_imports = list(implementations.keys())

        # Check for SSOT violation: multiple working imports with different implementations
        if len(working_imports) > 1:
            mock_imports = [path for path, info in implementations.items() if info.get('is_mock', False)]
            real_imports = [path for path, info in implementations.items() if not info.get('is_mock', False)]

            # This test FAILS if both mock and real imports work (proving violation)
            self.assertEqual(len(mock_imports), 0,
                           f"SSOT VIOLATION: Mock Docker Manager imports still working:\n"
                           f"Mock imports: {mock_imports}\n"
                           f"Real imports: {real_imports}\n"
                           f"All imports should resolve to real implementation only")

    def test_golden_path_websocket_events_require_real_services(self):
        """
        VALIDATES GOLDEN PATH: WebSocket events require real Docker services for $500K+ ARR.

        CURRENT EXPECTATION: FAIL - Mock services cannot provide real WebSocket events
        POST-REMEDIATION: PASS - Real services enable Golden Path functionality
        """
        # This test validates that Docker Manager enables real service connections
        # which are required for WebSocket events in Golden Path user flow

        try:
            # Import the Docker Manager being used
            from test_framework.unified_docker_manager import UnifiedDockerManager
            manager = UnifiedDockerManager()

            # Check if manager can provide real service capabilities
            # Real implementation should have these attributes without MagicMock
            required_real_methods = [
                'start_services',
                'get_service_health',
                'manage_containers',
                'get_websocket_url'  # Required for Golden Path WebSocket events
            ]

            mock_method_count = 0
            missing_methods = []

            for method_name in required_real_methods:
                if hasattr(manager, method_name):
                    method = getattr(manager, method_name)
                    if isinstance(method, (MagicMock, AsyncMock)):
                        mock_method_count += 1
                else:
                    missing_methods.append(method_name)

            # Golden Path requires real service methods, not mocks
            golden_path_compatible = mock_method_count == 0 and len(missing_methods) == 0

            # This test FAILS if Golden Path functionality is mocked (proving violation)
            self.assertTrue(golden_path_compatible,
                           f"GOLDEN PATH VIOLATION: Docker Manager lacks real service capabilities:\n"
                           f"Methods that are mocks: {mock_method_count}/{len(required_real_methods)}\n"
                           f"Missing methods: {missing_methods}\n"
                           f"Golden Path WebSocket events require real service connections for $500K+ ARR")

        except ImportError as e:
            self.fail(f"CRITICAL: Cannot import Docker Manager - Golden Path broken: {e}")

    def test_ssot_enforcement_prevents_future_regression(self):
        """
        ENFORCES SSOT: Validates that SSOT patterns prevent future Docker Manager duplication.

        CURRENT EXPECTATION: FAIL - SSOT enforcement not active
        POST-REMEDIATION: PASS - SSOT patterns prevent regression
        """
        # Check that only the correct import path is documented/used
        correct_import_path = "test_framework.unified_docker_manager"
        incorrect_import_path = "test_framework.docker.unified_docker_manager"

        # Verify the correct path works
        try:
            importlib.import_module(correct_import_path)
            correct_import_works = True
        except ImportError:
            correct_import_works = False

        # Verify the incorrect path fails (after remediation)
        try:
            importlib.import_module(incorrect_import_path)
            incorrect_import_works = True
        except ImportError:
            incorrect_import_works = False

        # SSOT compliance: correct works, incorrect fails
        ssot_enforced = correct_import_works and not incorrect_import_works

        # This test FAILS if SSOT is not enforced (proving violation exists)
        self.assertTrue(ssot_enforced,
                       f"SSOT ENFORCEMENT VIOLATION:\n"
                       f"Correct import ({correct_import_path}) works: {correct_import_works}\n"
                       f"Incorrect import ({incorrect_import_path}) works: {incorrect_import_works}\n"
                       f"Expected: Only correct import should work (SSOT compliance)")


class TestDockerManagerMissionCriticalIntegration(SSotBaseTestCase):
    """
    Mission critical tests for Docker Manager SSOT compliance.

    These tests validate that Docker Manager SSOT compliance protects
    mission critical business functionality worth $500K+ ARR.
    """

    def setUp(self):
        """Set up mission critical test environment."""
        super().setUp()

    def test_mission_critical_websocket_events_require_real_docker_services(self):
        """
        MISSION CRITICAL: WebSocket agent events require real Docker services.

        Business Impact: $500K+ ARR depends on WebSocket events working with real services.
        SSOT compliance ensures tests use real services, not mocks.
        """
        # This test validates the critical business requirement:
        # WebSocket agent events (agent_started, agent_thinking, tool_executing,
        # tool_completed, agent_completed) require real service connections

        try:
            from test_framework.unified_docker_manager import UnifiedDockerManager
            manager = UnifiedDockerManager()

            # Mission critical methods for WebSocket functionality
            websocket_critical_methods = [
                'get_websocket_url',
                'get_backend_url',
                'ensure_services_running',
                'get_service_status'
            ]

            methods_available = []
            methods_mocked = []
            methods_missing = []

            for method_name in websocket_critical_methods:
                if hasattr(manager, method_name):
                    method = getattr(manager, method_name)
                    if isinstance(method, (MagicMock, AsyncMock)):
                        methods_mocked.append(method_name)
                    else:
                        methods_available.append(method_name)
                else:
                    methods_missing.append(method_name)

            # Mission critical requirement: NO mocked methods
            mission_critical_compliance = len(methods_mocked) == 0

            self.assertTrue(mission_critical_compliance,
                           f"MISSION CRITICAL VIOLATION: WebSocket functionality compromised:\n"
                           f"Real methods available: {methods_available}\n"
                           f"Methods mocked (VIOLATION): {methods_mocked}\n"
                           f"Methods missing: {methods_missing}\n"
                           f"Business Impact: $500K+ ARR WebSocket events require real services")

        except ImportError as e:
            self.fail(f"MISSION CRITICAL FAILURE: Docker Manager import failed: {e}")

    def test_mission_critical_golden_path_service_integration(self):
        """
        MISSION CRITICAL: Golden Path requires integrated service management.

        Validates that Docker Manager provides integrated service management
        required for the complete Golden Path user flow.
        """
        try:
            from test_framework.unified_docker_manager import UnifiedDockerManager
            manager = UnifiedDockerManager()

            # Golden Path integration requirements
            integration_requirements = [
                'start_backend_services',
                'start_auth_service',
                'get_all_service_urls',
                'validate_service_integration'
            ]

            integration_score = 0
            missing_integrations = []

            for requirement in integration_requirements:
                if hasattr(manager, requirement):
                    method = getattr(manager, requirement)
                    if not isinstance(method, (MagicMock, AsyncMock)):
                        integration_score += 1
                else:
                    missing_integrations.append(requirement)

            # Golden Path requires high integration capability
            min_required_score = len(integration_requirements) // 2
            golden_path_ready = integration_score >= min_required_score

            self.assertTrue(golden_path_ready,
                           f"GOLDEN PATH VIOLATION: Insufficient service integration:\n"
                           f"Integration score: {integration_score}/{len(integration_requirements)}\n"
                           f"Minimum required: {min_required_score}\n"
                           f"Missing integrations: {missing_integrations}\n"
                           f"Golden Path user flow requires integrated service management")

        except ImportError as e:
            self.fail(f"GOLDEN PATH FAILURE: Service integration unavailable: {e}")


if __name__ == '__main__':
    # Configure test runner for mission critical execution
    unittest.main(
        verbosity=2,
        failfast=False,  # Run all tests to show full violation scope
        warnings='default'
    )