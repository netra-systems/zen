"""
Issue #1069: Execution Engine Import Paths Critical Infrastructure Gap Testing

Business Value Justification (BVJ):
- Segment: Platform/Enterprise - Core execution infrastructure critical for $500K+ ARR
- Business Goal: System Stability - Prevent execution engine import failures affecting agent workflows
- Value Impact: Ensures execution engine components are properly accessible via SSOT import paths
- Strategic Impact: Foundation for reliable agent execution and customer value delivery

CRITICAL: These tests should FAIL initially to expose execution engine import path issues.
They validate that deprecated execution_engine imports break SSOT compliance and system stability.

Test Coverage:
1. Deprecated execution_engine import path scanning and detection
2. SSOT import path validation for execution engine components
3. Specific test_execution_engine_migration_validation.py import issue reproduction
4. Execution engine component accessibility via canonical imports
5. Cross-service execution engine import fragmentation detection
6. Legacy import path deprecation validation
7. SSOT compliance verification for execution engine imports
8. Production execution engine import path stability testing

ARCHITECTURE ALIGNMENT:
- Tests validate SSOT_IMPORT_REGISTRY.md compliance for execution engine
- Demonstrates execution engine import fragmentation issues
- Shows $500K+ ARR agent execution reliability dependency on proper imports
- Validates production execution engine import path stability requirements
"""

import ast
import importlib
import os
import pytest
import sys
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestExecutionEngineImportPaths(SSotAsyncTestCase):
    """Test suite for execution engine import paths critical infrastructure gaps."""

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.test_run_id = f"execution_engine_test_{uuid.uuid4().hex[:8]}"
        self.import_failures = []
        self.deprecated_imports = []
        self.ssot_violations = []

    def test_deprecated_execution_engine_import_scanning(self):
        """
        Test scanning for deprecated execution_engine import patterns.

        CRITICAL: This should FAIL if deprecated import patterns are found,
        exposing SSOT compliance violations.
        """
        # Scan for deprecated execution engine imports
        deprecated_patterns = [
            "from netra_backend.app.agents.supervisor.execution_engine import",
            "import netra_backend.app.agents.supervisor.execution_engine",
            "from netra_backend.app.agents.execution_engine import",
            "import netra_backend.app.agents.execution_engine"
        ]

        project_root = Path("/c/GitHub/netra-apex")
        deprecated_found = []

        # Scan relevant directories for deprecated imports
        scan_dirs = [
            project_root / "tests",
            project_root / "netra_backend" / "app",
            project_root / "test_framework"
        ]

        for scan_dir in scan_dirs:
            if scan_dir.exists():
                for py_file in scan_dir.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            for pattern in deprecated_patterns:
                                if pattern in content:
                                    deprecated_found.append(f"{py_file}: {pattern}")
                    except Exception as e:
                        self.import_failures.append(f"Failed to scan {py_file}: {e}")

        if deprecated_found:
            self.deprecated_imports.extend(deprecated_found)
            pytest.fail(f"CRITICAL: Deprecated execution engine imports found:\n" +
                     "\n".join(deprecated_found[:10]))  # Limit output

    def test_ssot_execution_engine_import_validation(self):
        """
        Test SSOT import path validation for execution engine components.

        CRITICAL: This should FAIL if SSOT execution engine imports are broken.
        """
        # Test canonical SSOT execution engine imports
        ssot_imports = [
            "netra_backend.app.agents.supervisor.execution_engine",
            "netra_backend.app.agents.supervisor.workflow_orchestrator",
            "netra_backend.app.agents.supervisor.pipeline_executor"
        ]

        import_failures = []

        for import_path in ssot_imports:
            try:
                module = importlib.import_module(import_path)
                self.assertIsNotNone(module, f"SSOT import {import_path} should be available")
            except ImportError as e:
                import_failures.append(f"{import_path}: {e}")
            except Exception as e:
                import_failures.append(f"{import_path}: Unexpected error: {e}")

        if import_failures:
            self.ssot_violations.extend(import_failures)
            pytest.fail(f"CRITICAL: SSOT execution engine import failures:\n" +
                     "\n".join(import_failures))

    def test_execution_engine_migration_validation_issue(self):
        """
        Test specific test_execution_engine_migration_validation.py import issue.

        CRITICAL: This should FAIL if the specific import issue exists,
        reproducing the exact problem mentioned in Issue #1069.
        """
        try:
            # Test the specific import that was mentioned as problematic
            from netra_backend.app.agents.supervisor import execution_engine
            self.assertIsNotNone(execution_engine, "execution_engine module should be importable")

            # Test that we can access key components
            self.assertTrue(hasattr(execution_engine, 'ExecutionEngine') or
                          hasattr(execution_engine, 'ModernExecutionEngine'),
                          "ExecutionEngine class should be accessible")

        except ImportError as e:
            pytest.fail(f"CRITICAL: test_execution_engine_migration_validation import issue reproduced: {e}")
        except AttributeError as e:
            pytest.fail(f"CRITICAL: ExecutionEngine class not accessible: {e}")

    def test_execution_engine_component_accessibility(self):
        """
        Test execution engine component accessibility via canonical imports.

        CRITICAL: This should FAIL if execution engine components cannot be accessed.
        """
        try:
            # Test accessing execution engine components
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            self.assertIsNotNone(ExecutionEngine, "ExecutionEngine should be accessible")

        except ImportError as e:
            try:
                # Try alternative import path
                from netra_backend.app.agents.supervisor.execution_engine import ModernExecutionEngine
                self.assertIsNotNone(ModernExecutionEngine, "ModernExecutionEngine should be accessible")
            except ImportError as e2:
                pytest.fail(f"CRITICAL: No execution engine components accessible: {e}, {e2}")

    def test_cross_service_execution_engine_import_fragmentation(self):
        """
        Test cross-service execution engine import fragmentation detection.

        CRITICAL: This should FAIL if import fragmentation is detected across services.
        """
        # Check for execution engine imports across different services
        service_dirs = [
            Path("/c/GitHub/netra-apex/netra_backend"),
            Path("/c/GitHub/netra-apex/auth_service"),
            Path("/c/GitHub/netra-apex/frontend"),
            Path("/c/GitHub/netra-apex/shared")
        ]

        fragmentation_issues = []

        for service_dir in service_dirs:
            if service_dir.exists():
                for py_file in service_dir.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Look for multiple different execution engine import patterns
                            if "execution_engine" in content.lower():
                                # Parse AST to get actual import statements
                                try:
                                    tree = ast.parse(content)
                                    for node in ast.walk(tree):
                                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                                            if hasattr(node, 'module') and node.module and 'execution_engine' in node.module:
                                                fragmentation_issues.append(f"{py_file}: {ast.unparse(node)}")
                                except SyntaxError:
                                    pass  # Skip files with syntax errors
                    except Exception as e:
                        self.import_failures.append(f"Failed to scan {py_file}: {e}")

        if len(set(fragmentation_issues)) > 3:  # More than 3 unique import patterns indicates fragmentation
            pytest.fail(f"CRITICAL: Execution engine import fragmentation detected:\n" +
                     "\n".join(set(fragmentation_issues)[:10]))

    def test_legacy_import_path_deprecation_validation(self):
        """
        Test legacy import path deprecation validation.

        CRITICAL: This should FAIL if legacy import paths are still being used.
        """
        legacy_import_patterns = [
            "from netra_backend.app.agents.execution_engine",
            "import netra_backend.app.agents.execution_engine",
            "from netra_backend.execution_engine",
            "import netra_backend.execution_engine"
        ]

        project_root = Path("/c/GitHub/netra-apex")
        legacy_found = []

        # Focus on test files that might have legacy imports
        test_dirs = [
            project_root / "tests" / "unit" / "agents",
            project_root / "tests" / "integration",
            project_root / "netra_backend" / "tests"
        ]

        for test_dir in test_dirs:
            if test_dir.exists():
                for py_file in test_dir.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            for pattern in legacy_import_patterns:
                                if pattern in content:
                                    legacy_found.append(f"{py_file}: {pattern}")
                    except Exception as e:
                        self.import_failures.append(f"Failed to scan {py_file}: {e}")

        if legacy_found:
            pytest.fail(f"CRITICAL: Legacy execution engine import paths found:\n" +
                     "\n".join(legacy_found[:10]))

    def test_ssot_compliance_verification_execution_engine(self):
        """
        Test SSOT compliance verification for execution engine imports.

        CRITICAL: This should FAIL if SSOT compliance violations are found.
        """
        # Check SSOT_IMPORT_REGISTRY for execution engine entries
        try:
            ssot_registry_path = Path("/c/GitHub/netra-apex/docs/SSOT_IMPORT_REGISTRY.md")
            if ssot_registry_path.exists():
                with open(ssot_registry_path, 'r', encoding='utf-8') as f:
                    registry_content = f.read()

                    # Check if execution engine imports are documented
                    if "execution_engine" not in registry_content.lower():
                        pytest.fail("CRITICAL: Execution engine imports not documented in SSOT_IMPORT_REGISTRY.md")

                    # Check for specific canonical imports
                    canonical_imports = [
                        "netra_backend.app.agents.supervisor.execution_engine",
                        "netra_backend.app.agents.supervisor.workflow_orchestrator"
                    ]

                    missing_imports = []
                    for canonical_import in canonical_imports:
                        if canonical_import not in registry_content:
                            missing_imports.append(canonical_import)

                    if missing_imports:
                        pytest.fail(f"CRITICAL: Canonical execution engine imports missing from SSOT registry: {missing_imports}")
            else:
                pytest.fail("CRITICAL: SSOT_IMPORT_REGISTRY.md not found")

        except Exception as e:
            pytest.fail(f"CRITICAL: SSOT compliance verification failed: {e}")

    def test_production_execution_engine_import_stability(self):
        """
        Test production execution engine import path stability.

        CRITICAL: This should FAIL if production import paths are unstable.
        """
        # Test that production execution engine imports work consistently
        production_imports = [
            "netra_backend.app.agents.supervisor.execution_engine.ExecutionEngine",
            "netra_backend.app.agents.supervisor.workflow_orchestrator.WorkflowOrchestrator",
            "netra_backend.app.agents.supervisor.pipeline_executor.PipelineExecutor"
        ]

        stability_failures = []

        for import_path in production_imports:
            try:
                # Split module and class
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)

                if hasattr(module, class_name):
                    class_obj = getattr(module, class_name)
                    self.assertIsNotNone(class_obj, f"{class_name} should be accessible from {module_path}")
                else:
                    stability_failures.append(f"{class_name} not found in {module_path}")

            except ImportError as e:
                stability_failures.append(f"{import_path}: Import failed: {e}")
            except Exception as e:
                stability_failures.append(f"{import_path}: Unexpected error: {e}")

        if stability_failures:
            pytest.fail(f"CRITICAL: Production execution engine import stability issues:\n" +
                     "\n".join(stability_failures))

    def teardown_method(self, method):
        """Cleanup after each test method."""
        super().teardown_method(method)

        # Log any import issues for analysis
        if self.import_failures:
            self.logger.warning(f"Execution engine import failures: {self.import_failures}")

        if self.deprecated_imports:
            self.logger.warning(f"Deprecated execution engine imports: {self.deprecated_imports}")

        if self.ssot_violations:
            self.logger.warning(f"SSOT execution engine violations: {self.ssot_violations}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])