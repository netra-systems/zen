#!/usr/bin/env python3
"""
Phase 1 Test Framework Import Resolution Tests for Issue #1098

This test file validates the core test framework infrastructure to ensure:
1. SSOT BaseTestCase imports work correctly
2. test_framework module accessibility is functional
3. Critical SSOT modules exist and are importable
4. Unified test runner infrastructure functions properly

These tests expose the import path issues blocking Issue #1098 validation.
"""

import sys
import os
from pathlib import Path
import importlib
import traceback
import pytest

# Add project root to path for absolute imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestFrameworkImportResolution:
    """Validates that test framework imports work correctly."""

    def test_project_root_accessible(self):
        """Verify project root is accessible and contains expected structure."""
        project_root = Path(__file__).parent.parent.parent
        assert project_root.exists(), f"Project root not found: {project_root}"

        # Check for key directories
        expected_dirs = [
            "test_framework",
            "tests",
            "netra_backend",
            "shared"
        ]

        for dir_name in expected_dirs:
            dir_path = project_root / dir_name
            assert dir_path.exists(), f"Expected directory not found: {dir_path}"

    def test_test_framework_module_import(self):
        """Verify test_framework module can be imported."""
        try:
            import test_framework
            assert test_framework is not None, "test_framework module import returned None"
        except ImportError as e:
            pytest.fail(f"Failed to import test_framework module: {e}")

    def test_ssot_base_test_case_import(self):
        """Verify SSOT BaseTestCase can be imported."""
        try:
            from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
            assert SSotBaseTestCase is not None, "SSotBaseTestCase import returned None"
            assert SSotAsyncTestCase is not None, "SSotAsyncTestCase import returned None"
        except ImportError as e:
            pytest.fail(f"Failed to import SSOT BaseTestCase: {e}")

    def test_ssot_mock_factory_import(self):
        """Verify SSOT Mock Factory can be imported."""
        try:
            from test_framework.ssot.mock_factory import SSotMockFactory
            assert SSotMockFactory is not None, "SSotMockFactory import returned None"
        except ImportError as e:
            pytest.fail(f"Failed to import SSOT MockFactory: {e}")

    def test_ssot_orchestration_import(self):
        """Verify SSOT orchestration modules can be imported."""
        try:
            from test_framework.ssot.orchestration import OrchestrationConfig
            assert OrchestrationConfig is not None, "OrchestrationConfig import returned None"
        except ImportError as e:
            pytest.fail(f"Failed to import SSOT orchestration: {e}")

    def test_ssot_orchestration_enums_import(self):
        """Verify SSOT orchestration enums can be imported."""
        try:
            from test_framework.ssot.orchestration_enums import (
                OrchestrationMode,
                DockerOrchestrationMode,
                ServiceAvailability
            )
            assert OrchestrationMode is not None, "OrchestrationMode import returned None"
            assert DockerOrchestrationMode is not None, "DockerOrchestrationMode import returned None"
            assert ServiceAvailability is not None, "ServiceAvailability import returned None"
        except ImportError as e:
            pytest.fail(f"Failed to import SSOT orchestration enums: {e}")

    def test_unified_test_runner_import(self):
        """Verify unified test runner can be imported."""
        try:
            sys.path.insert(0, str(project_root / "tests"))
            import unified_test_runner
            assert unified_test_runner is not None, "unified_test_runner import returned None"
        except ImportError as e:
            pytest.fail(f"Failed to import unified_test_runner: {e}")

    def test_isolated_environment_import(self):
        """Verify IsolatedEnvironment can be imported."""
        try:
            from shared.isolated_environment import IsolatedEnvironment
            assert IsolatedEnvironment is not None, "IsolatedEnvironment import returned None"
        except ImportError as e:
            pytest.fail(f"Failed to import IsolatedEnvironment: {e}")

    def test_critical_test_utilities_import(self):
        """Verify critical test utilities can be imported."""
        test_utilities = [
            ("test_framework.ssot.database", "DatabaseTestUtility"),
            ("test_framework.ssot.websocket", "WebSocketTestUtility"),
            ("test_framework.unified_docker_manager", "UnifiedDockerManager"),
        ]

        for module_path, class_name in test_utilities:
            try:
                module = importlib.import_module(module_path)
                test_class = getattr(module, class_name, None)
                assert test_class is not None, f"Class {class_name} not found in {module_path}"
            except ImportError as e:
                pytest.fail(f"Failed to import {module_path}: {e}")

    def test_python_path_configuration(self):
        """Verify Python path includes required directories."""
        project_root = Path(__file__).parent.parent.parent
        required_paths = [
            str(project_root),
            # Note: test_framework is accessible via project_root, not separately
            # str(project_root / "test_framework"),
            # str(project_root / "shared"),
        ]

        current_paths = [str(Path(p).resolve()) for p in sys.path]

        for required_path in required_paths:
            resolved_required = str(Path(required_path).resolve())
            assert any(resolved_required in current_path for current_path in current_paths), \
                f"Required path not in sys.path: {resolved_required}\nCurrent sys.path: {current_paths}"

        # Verify test_framework is accessible even if not directly in path
        try:
            import test_framework
            assert test_framework is not None, "test_framework should be accessible"
        except ImportError as e:
            pytest.fail(f"test_framework not accessible despite path configuration: {e}")

    def test_test_framework_ssot_init_accessible(self):
        """Verify test_framework.ssot __init__.py is accessible and contains expected exports."""
        try:
            from test_framework.ssot import (
                BaseTestCase,
                AsyncBaseTestCase,
                MockFactory,
                DatabaseTestUtility
            )

            # Verify all expected classes are available
            assert BaseTestCase is not None, "BaseTestCase not exported from test_framework.ssot"
            assert AsyncBaseTestCase is not None, "AsyncBaseTestCase not exported from test_framework.ssot"
            assert MockFactory is not None, "MockFactory not exported from test_framework.ssot"
            assert DatabaseTestUtility is not None, "DatabaseTestUtility not exported from test_framework.ssot"

        except ImportError as e:
            pytest.fail(f"Failed to import from test_framework.ssot: {e}")

    def test_mission_critical_test_imports(self):
        """Verify mission critical test modules can be imported."""
        try:
            # Test that we can import a known mission critical test
            sys.path.insert(0, str(project_root / "tests"))

            # Check if mission_critical directory exists and has tests
            mission_critical_dir = project_root / "tests" / "mission_critical"
            if mission_critical_dir.exists():
                # Try to import a specific mission critical test if it exists
                test_files = list(mission_critical_dir.glob("test_*.py"))
                if test_files:
                    # Try importing the first test file found
                    test_file = test_files[0]
                    test_module_name = f"mission_critical.{test_file.stem}"

                    try:
                        importlib.import_module(test_module_name)
                    except ImportError as e:
                        pytest.fail(f"Failed to import mission critical test {test_module_name}: {e}")

        except Exception as e:
            pytest.fail(f"Error testing mission critical imports: {e}")


class TestSSotComplianceBasics:
    """Validates basic SSOT compliance infrastructure."""

    def test_ssot_base_test_case_inheritance(self):
        """Verify SSOT BaseTestCase can be inherited from properly."""
        try:
            from test_framework.ssot.base_test_case import SSotBaseTestCase

            class TestSSotInheritance(SSotBaseTestCase):
                def test_inheritance_works(self):
                    pass

            # Verify the class was created successfully
            assert TestSSotInheritance is not None, "Failed to create SSOT test case subclass"
            assert issubclass(TestSSotInheritance, SSotBaseTestCase), "Class is not a proper subclass"

        except Exception as e:
            pytest.fail(f"Failed to inherit from SSotBaseTestCase: {e}")

    def test_ssot_mock_factory_instantiation(self):
        """Verify SSOT MockFactory can be instantiated."""
        try:
            from test_framework.ssot.mock_factory import SSotMockFactory

            factory = SSotMockFactory()
            assert factory is not None, "Failed to instantiate SSotMockFactory"

        except Exception as e:
            pytest.fail(f"Failed to instantiate SSotMockFactory: {e}")

    def test_orchestration_config_instantiation(self):
        """Verify OrchestrationConfig can be instantiated."""
        try:
            from test_framework.ssot.orchestration import OrchestrationConfig

            config = OrchestrationConfig()
            assert config is not None, "Failed to instantiate OrchestrationConfig"

        except Exception as e:
            pytest.fail(f"Failed to instantiate OrchestrationConfig: {e}")


if __name__ == "__main__":
    # Run tests directly when script is executed
    print("Running Phase 1 Test Framework Import Resolution Tests...")

    # Import pytest and run
    try:
        import pytest
        exit_code = pytest.main([__file__, "-v", "--tb=short"])
        sys.exit(exit_code)
    except ImportError:
        print("pytest not available, running tests manually...")

        # Manual test execution
        test_instance = TestFrameworkImportResolution()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]

        passed = 0
        failed = 0

        for test_method in test_methods:
            try:
                print(f"Running {test_method}...")
                getattr(test_instance, test_method)()
                print(f"✓ {test_method} PASSED")
                passed += 1
            except Exception as e:
                print(f"✗ {test_method} FAILED: {e}")
                failed += 1

        print(f"\nResults: {passed} passed, {failed} failed")
        sys.exit(0 if failed == 0 else 1)