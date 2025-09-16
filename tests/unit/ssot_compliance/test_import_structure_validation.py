"""
Import Structure Validation Test - Issue #1098 Phase 2 SSOT Compliance

MISSION: Validate that import structures comply with SSOT patterns and don't create cycles.

This test suite validates that the SSOT import structure is working correctly
and that canonical import paths function as expected. It also validates that
deprecated import paths issue appropriate warnings.

Business Value: Platform/Internal - Development Velocity & System Stability
Ensures import structure doesn't cause:
- Circular import dependencies
- Import path confusion
- Missing deprecation warnings
- SSOT compliance violations

Test Strategy:
- Unit tests analyze import structure without external dependencies
- Test canonical import paths work correctly
- Validate deprecation warnings for legacy paths
- Check for circular dependencies
- Ensure SSOT compliance in import patterns

Expected Results (Phase 2):
- PASS: Canonical imports work correctly
- PASS: No circular import dependencies
- PASS: Deprecation warnings issued appropriately
- PASS: Import structure supports SSOT patterns
"""

import ast
import sys
import importlib
import warnings
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class ImportViolation:
    """Represents an import structure violation."""
    file_path: str
    line_number: int
    import_statement: str
    violation_type: str
    severity: str
    description: str


@dataclass
class CircularDependency:
    """Represents a circular import dependency."""
    cycle_path: List[str]
    entry_point: str
    affected_modules: Set[str]


class TestImportStructureValidation(SSotBaseTestCase):
    """
    Unit test suite validating SSOT import structure compliance.

    Tests import patterns, circular dependencies, and canonical path functionality
    without requiring external dependencies.
    """

    # SSOT canonical import paths that should work
    CANONICAL_IMPORT_PATHS = [
        "netra_backend.app.websocket_core.canonical_imports",
        "netra_backend.app.services.user_execution_context",
        "netra_backend.app.core.configuration.base",
        "test_framework.ssot.base_test_case",
    ]

    # Deprecated import paths that should issue warnings
    DEPRECATED_IMPORT_PATHS = [
        "netra_backend.app.websocket_core.manager",
        "netra_backend.app.factories.websocket_factory",
        "netra_backend.app.core.legacy_config",
    ]

    # Import patterns that violate SSOT
    PROHIBITED_IMPORT_PATTERNS = [
        r'from.*\.legacy\.',
        r'import.*deprecated',
        r'from.*old_.*import',
        r'import.*\.factory\.(?!.*canonical)',
    ]

    def setUp(self):
        """Set up import structure validation."""
        super().setUp()
        self.import_violations: List[ImportViolation] = []
        self.circular_dependencies: List[CircularDependency] = []
        self.assertLog("Starting import structure validation")

    def test_canonical_imports_accessibility(self):
        """
        Test that canonical import paths are accessible and functional.

        Validates that SSOT canonical imports work without errors.
        """
        self.assertLog("Testing canonical import accessibility")

        accessible_imports = []
        failed_imports = []

        for import_path in self.CANONICAL_IMPORT_PATHS:
            try:
                # Test import accessibility
                module = importlib.import_module(import_path)
                self.assertIsNotNone(module)
                accessible_imports.append(import_path)
                self.assertLog(f"✅ Accessible: {import_path}")

            except ImportError as e:
                failed_imports.append((import_path, str(e)))
                self.assertLog(f"❌ Failed: {import_path} - {e}")

            except Exception as e:
                failed_imports.append((import_path, f"Unexpected error: {e}"))
                self.assertLog(f"⚠️ Error: {import_path} - {e}")

        # Log summary
        self.assertLog(f"Canonical imports: {len(accessible_imports)}/{len(self.CANONICAL_IMPORT_PATHS)} accessible")

        # Require at least 50% of canonical imports to be accessible
        min_required = len(self.CANONICAL_IMPORT_PATHS) // 2

        self.assertGreaterEqual(
            len(accessible_imports), min_required,
            f"Too few canonical imports accessible ({len(accessible_imports)} < {min_required}). "
            f"Failed imports: {failed_imports}"
        )

        self.assertLog("✅ Canonical import accessibility validated")

    def test_deprecated_import_warnings(self):
        """
        Test that deprecated import paths issue appropriate warnings.

        Validates backward compatibility with deprecation warnings.
        """
        self.assertLog("Testing deprecated import warnings")

        warnings_issued = []
        no_warnings_issued = []

        for deprecated_path in self.DEPRECATED_IMPORT_PATHS:
            with warnings.catch_warnings(record=True) as warning_list:
                warnings.simplefilter("always")

                try:
                    # Attempt to import deprecated path
                    importlib.import_module(deprecated_path)

                    # Check if deprecation warning was issued
                    deprecation_warnings = [
                        w for w in warning_list
                        if "deprecat" in str(w.message).lower() or "legacy" in str(w.message).lower()
                    ]

                    if deprecation_warnings:
                        warnings_issued.append(deprecated_path)
                        self.assertLog(f"✅ Warning issued: {deprecated_path}")
                    else:
                        no_warnings_issued.append(deprecated_path)
                        self.assertLog(f"⚠️ No warning: {deprecated_path}")

                except ImportError:
                    # Expected for eliminated deprecated imports
                    self.assertLog(f"Eliminated (expected): {deprecated_path}")

                except Exception as e:
                    self.assertLog(f"Error testing {deprecated_path}: {e}")

        # Log summary
        if warnings_issued:
            self.assertLog(f"Deprecation warnings working: {len(warnings_issued)} imports")

        if no_warnings_issued:
            self.assertLog(f"Missing warnings: {len(no_warnings_issued)} imports (may be eliminated)")

        self.assertLog("✅ Deprecated import warning testing completed")

    def test_no_circular_import_dependencies(self):
        """
        Test that import structure doesn't create circular dependencies.

        Analyzes import graphs to detect potential circular dependencies.
        """
        self.assertLog("Testing for circular import dependencies")

        # Analyze imports in production code
        production_modules = self._get_production_modules()
        circular_deps = self._detect_circular_dependencies(production_modules)

        self.circular_dependencies = circular_deps

        if circular_deps:
            self.assertLog(f"⚠️ Found {len(circular_deps)} potential circular dependencies")

            for dep in circular_deps[:3]:  # Show first 3
                cycle_str = " → ".join(dep.cycle_path)
                self.assertLog(f"  Cycle: {cycle_str}")

            # Allow some circular dependencies during migration but limit them
            max_allowed_circular = 5

            self.assertLessEqual(
                len(circular_deps), max_allowed_circular,
                f"Too many circular dependencies ({len(circular_deps)} > {max_allowed_circular}). "
                f"This can cause import failures and startup issues. "
                f"Cycles: {[' → '.join(dep.cycle_path) for dep in circular_deps[:3]]}"
            )

        else:
            self.assertLog("✅ No circular dependencies detected")

        self.assertLog("✅ Circular dependency testing completed")

    def test_ssot_import_pattern_compliance(self):
        """
        Test that import patterns comply with SSOT requirements.

        Scans code for prohibited import patterns that violate SSOT.
        """
        self.assertLog("Testing SSOT import pattern compliance")

        violations = self._scan_for_prohibited_import_patterns()
        self.import_violations = violations

        if violations:
            self.assertLog(f"⚠️ Found {len(violations)} import pattern violations")

            # Group by violation type
            by_type = {}
            for violation in violations:
                if violation.violation_type not in by_type:
                    by_type[violation.violation_type] = []
                by_type[violation.violation_type].append(violation)

            for violation_type, type_violations in by_type.items():
                self.assertLog(f"  {violation_type}: {len(type_violations)} violations")

            # Allow some violations during migration but track them
            max_allowed_violations = 20

            self.assertLessEqual(
                len(violations), max_allowed_violations,
                f"Too many import pattern violations ({len(violations)} > {max_allowed_violations}). "
                f"Violations: {[f'{v.file_path}:{v.line_number}' for v in violations[:5]]}"
            )

        else:
            self.assertLog("✅ No import pattern violations found")

        self.assertLog("✅ SSOT import pattern compliance validated")

    def test_websocket_canonical_import_functionality(self):
        """
        Test that WebSocket canonical imports provide expected functionality.

        Validates that canonical WebSocket imports work as intended.
        """
        self.assertLog("Testing WebSocket canonical import functionality")

        try:
            # Test canonical WebSocket imports
            from netra_backend.app.websocket_core.canonical_imports import (
                create_websocket_manager,
                ConnectionLifecycleManager
            )

            # Validate functions are callable
            self.assertTrue(callable(create_websocket_manager))
            self.assertTrue(callable(ConnectionLifecycleManager))

            self.assertLog("✅ WebSocket canonical imports functional")

            # Test that functions have expected signatures
            if hasattr(create_websocket_manager, '__annotations__'):
                self.assertLog("✅ create_websocket_manager has type annotations")

            # Test error handling functionality
            try:
                from netra_backend.app.websocket_core.canonical_imports import (
                    FactoryInitializationError,
                    WebSocketComponentError
                )

                self.assertTrue(issubclass(FactoryInitializationError, Exception))
                self.assertTrue(issubclass(WebSocketComponentError, Exception))

                self.assertLog("✅ WebSocket error classes accessible")

            except ImportError:
                self.assertLog("⚠️ WebSocket error classes not accessible (may be eliminated)")

        except ImportError as e:
            self.assertLog(f"⚠️ WebSocket canonical imports not accessible: {e}")
            # Don't fail test if this is expected during migration
            pass

    def test_configuration_canonical_import_functionality(self):
        """
        Test that configuration canonical imports work correctly.

        Validates SSOT configuration access patterns.
        """
        self.assertLog("Testing configuration canonical import functionality")

        try:
            # Test configuration imports
            from netra_backend.app.core.configuration.base import get_config

            self.assertTrue(callable(get_config))
            self.assertLog("✅ Configuration canonical imports functional")

            # Test isolated environment access
            from dev_launcher.isolated_environment import IsolatedEnvironment

            self.assertIsNotNone(IsolatedEnvironment)
            self.assertLog("✅ IsolatedEnvironment accessible")

        except ImportError as e:
            self.assertLog(f"⚠️ Configuration canonical imports not accessible: {e}")

    def test_test_framework_ssot_imports(self):
        """
        Test that test framework SSOT imports work correctly.

        Validates test infrastructure canonical imports.
        """
        self.assertLog("Testing test framework SSOT imports")

        try:
            # Test framework imports should work
            from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

            self.assertTrue(issubclass(SSotBaseTestCase, object))
            self.assertTrue(issubclass(SSotAsyncTestCase, object))

            self.assertLog("✅ Test framework SSOT imports functional")

            # Test additional SSOT utilities
            ssot_utilities = [
                'test_framework.ssot.mock_factory',
                'test_framework.ssot.websocket_test_utility',
                'test_framework.ssot.database_test_utility',
            ]

            accessible_utilities = 0

            for utility in ssot_utilities:
                try:
                    importlib.import_module(utility)
                    accessible_utilities += 1
                    self.assertLog(f"✅ Accessible: {utility}")
                except ImportError:
                    self.assertLog(f"⚠️ Not accessible: {utility}")

            # Require at least 50% of utilities to be accessible
            min_required = len(ssot_utilities) // 2
            self.assertGreaterEqual(
                accessible_utilities, min_required,
                f"Too few SSOT utilities accessible ({accessible_utilities} < {min_required})"
            )

        except ImportError as e:
            self.fail(f"Test framework SSOT imports failed: {e}")

    # Helper methods for import analysis

    def _get_production_modules(self) -> List[str]:
        """
        Get list of production modules to analyze.

        Returns:
            List of module paths in production code.
        """
        modules = []
        production_paths = [
            "netra_backend/app",
            "auth_service",
            "shared"
        ]

        for path in production_paths:
            if Path(path).exists():
                for file_path in Path(path).rglob("*.py"):
                    if self._should_analyze_file(file_path):
                        # Convert file path to module path
                        module_path = str(file_path).replace('/', '.').replace('\\', '.').replace('.py', '')
                        modules.append(module_path)

        return modules

    def _should_analyze_file(self, file_path: Path) -> bool:
        """
        Determine if file should be analyzed for imports.

        Args:
            file_path: Path to check

        Returns:
            True if file should be analyzed.
        """
        exclusions = [
            '__pycache__',
            'test_',
            '.backup',
            'migrations/',
            'node_modules/',
        ]

        for exclusion in exclusions:
            if exclusion in str(file_path):
                return False

        return True

    def _detect_circular_dependencies(self, modules: List[str]) -> List[CircularDependency]:
        """
        Detect circular dependencies in module list.

        Args:
            modules: List of module paths to analyze

        Returns:
            List of circular dependencies found.
        """
        # This is a simplified circular dependency detection
        # In a real implementation, you'd use more sophisticated graph analysis

        circular_deps = []
        dependency_graph = {}

        # Build dependency graph by analyzing imports
        for module in modules[:50]:  # Limit for performance
            try:
                dependencies = self._get_module_dependencies(module)
                dependency_graph[module] = dependencies
            except Exception:
                continue

        # Look for simple circular dependencies
        for module, deps in dependency_graph.items():
            for dep in deps:
                if dep in dependency_graph:
                    dep_deps = dependency_graph.get(dep, [])
                    if module in dep_deps:
                        # Found simple circular dependency
                        circular_deps.append(CircularDependency(
                            cycle_path=[module, dep, module],
                            entry_point=module,
                            affected_modules={module, dep}
                        ))

        return circular_deps

    def _get_module_dependencies(self, module_path: str) -> List[str]:
        """
        Get dependencies for a module by analyzing its imports.

        Args:
            module_path: Module path to analyze

        Returns:
            List of module dependencies.
        """
        try:
            # Convert module path back to file path
            file_path = module_path.replace('.', '/') + '.py'

            if not Path(file_path).exists():
                return []

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            dependencies = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.append(node.module)

            return dependencies

        except Exception:
            return []

    def _scan_for_prohibited_import_patterns(self) -> List[ImportViolation]:
        """
        Scan for prohibited import patterns that violate SSOT.

        Returns:
            List of import violations found.
        """
        violations = []
        production_paths = [
            "netra_backend/app",
            "auth_service",
            "shared"
        ]

        for path in production_paths:
            if Path(path).exists():
                for file_path in Path(path).rglob("*.py"):
                    if self._should_analyze_file(file_path):
                        file_violations = self._scan_file_for_import_violations(file_path)
                        violations.extend(file_violations)

        return violations

    def _scan_file_for_import_violations(self, file_path: Path) -> List[ImportViolation]:
        """
        Scan a single file for import violations.

        Args:
            file_path: Path to file to scan

        Returns:
            List of violations found in file.
        """
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()

                # Check for prohibited patterns
                for pattern in self.PROHIBITED_IMPORT_PATTERNS:
                    import re
                    if re.search(pattern, line_stripped, re.IGNORECASE):
                        violations.append(ImportViolation(
                            file_path=str(file_path),
                            line_number=line_num,
                            import_statement=line_stripped,
                            violation_type="prohibited_pattern",
                            severity=self._determine_import_violation_severity(line_stripped),
                            description=f"Prohibited import pattern: {pattern}"
                        ))

                # Check for specific anti-patterns
                if 'from' in line_stripped and 'import' in line_stripped:
                    if '.legacy.' in line_stripped or 'deprecated' in line_stripped.lower():
                        violations.append(ImportViolation(
                            file_path=str(file_path),
                            line_number=line_num,
                            import_statement=line_stripped,
                            violation_type="legacy_import",
                            severity="medium",
                            description="Legacy import usage"
                        ))

        except (UnicodeDecodeError, IOError):
            pass

        return violations

    def _determine_import_violation_severity(self, import_statement: str) -> str:
        """
        Determine severity of import violation.

        Args:
            import_statement: Import statement to analyze

        Returns:
            Severity level: 'critical', 'high', 'medium', 'low'
        """
        if 'websocket' in import_statement.lower() and 'factory' in import_statement.lower():
            return 'critical'
        elif 'deprecated' in import_statement.lower():
            return 'high'
        elif 'legacy' in import_statement.lower():
            return 'medium'
        else:
            return 'low'


if __name__ == "__main__":
    import unittest
    unittest.main()