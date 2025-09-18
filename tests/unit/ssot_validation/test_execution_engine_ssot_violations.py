"""
Unit Tests for Execution Engine SSOT Violations Detection

Issue #909: Critical P0 SSOT violations in agent execution infrastructure
These tests detect multiple competing execution engine implementations causing race conditions.

Business Impact: $500K+ ARR at risk due to Golden Path success rate at ~60% (needs 99.9%)
"""

import pytest
import sys
import importlib
import inspect
import ast
from typing import Set, List, Dict, Any, Tuple
from pathlib import Path

# SSOT test framework imports
try:
    from test_framework.ssot.base_test_case import SSotBaseTestCase
except ImportError:
    # Fallback if SSOT framework not available
    import unittest
    SSotBaseTestCase = unittest.TestCase


class TestExecutionEngineSSotViolations(SSotBaseTestCase):
    """Test suite to detect Execution Engine SSOT violations."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.discovered_engines = []
        self.import_violations = []
        self.execution_engine_patterns = [
            'ExecutionEngine',
            'UserExecutionEngine',
            'RequestScopedExecutionEngine',
            'MCPExecutionEngine',
            'ToolExecutionEngine',
        ]

    def test_detect_multiple_execution_engines(self):
        """Test that detects multiple ExecutionEngine implementations.

        EXPECTED RESULT: This test should FAIL initially to prove it detects violations.
        """
        engine_classes = []
        engine_locations = []

        # Initialize import_violations for this test
        self.import_violations = []

        # Known execution engine locations to check
        engine_paths = [
            'netra_backend.app.agents.supervisor.user_execution_engine',
            'netra_backend.app.agents.supervisor.execution_engine_factory',
            'netra_backend.app.agents.supervisor.mcp_execution_engine',
            'netra_backend.app.agents.execution_engine_consolidated',
            'netra_backend.app.agents.execution_engine_interface',
            'netra_backend.app.agents.execution_engine_legacy_adapter',
            'netra_backend.app.agents.tool_dispatcher_execution',
            'netra_backend.app.agents.unified_tool_execution',
            'netra_backend.app.agents.base.executor',
        ]

        for path in engine_paths:
            try:
                module = importlib.import_module(path)
                # Look for execution engine classes
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if any(pattern in name for pattern in self.execution_engine_patterns):
                        engine_classes.append((name, obj, path))
                        engine_locations.append(f"{path}.{name}")
            except ImportError as e:
                self.import_violations.append(f"Failed to import {path}: {e}")

        # Store findings for analysis
        self.discovered_engines = engine_classes

        # Count actual ExecutionEngine implementations (not interfaces)
        concrete_engines = [
            (name, obj, path) for name, obj, path in engine_classes
            if not getattr(obj, '__abstractmethods__', None) and 'Interface' not in name
        ]

        print(f"\n=== EXECUTION ENGINE VIOLATION ANALYSIS ===")
        print(f"Found {len(engine_classes)} execution engine classes:")
        for name, obj, path in engine_classes:
            is_abstract = bool(getattr(obj, '__abstractmethods__', None))
            print(f"  - {name} in {path} {'(abstract)' if is_abstract else '(concrete)'}")

        print(f"\nConcrete implementations: {len(concrete_engines)}")
        for name, obj, path in concrete_engines:
            print(f"  - {name} in {path}")

        print(f"Import violations: {len(self.import_violations)}")
        for violation in self.import_violations:
            print(f"  - {violation}")

        # CRITICAL: This should fail initially - indicating we have multiple concrete engines
        self.assertLessEqual(len(concrete_engines), 3,
                           f"SSOT VIOLATION: Found {len(concrete_engines)} concrete ExecutionEngine classes, "
                           f"should be 3 or fewer (User, Tool, and optionally MCP). "
                           f"Locations: {[f'{path}.{name}' for name, obj, path in concrete_engines]}")

    def test_detect_execution_engine_import_multiplicity(self):
        """Test that detects multiple import paths for execution engines.

        EXPECTED RESULT: This test should FAIL initially to prove it detects violations.
        """
        import_paths_tested = []
        successful_imports = []

        # Test different import paths that might resolve to execution engines
        execution_engine_import_paths = [
            'netra_backend.app.agents.supervisor.execution_engine.ExecutionEngine',
            'netra_backend.app.agents.execution_engine_consolidated.ExecutionEngine',
            'netra_backend.app.agents.supervisor.user_execution_engine.UserExecutionEngine',
            'netra_backend.app.agents.canonical_imports.UserExecutionEngine',
        ]

        for import_path in execution_engine_import_paths:
            try:
                parts = import_path.split('.')
                module_path = '.'.join(parts[:-1])
                class_name = parts[-1]

                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    successful_imports.append((import_path, cls, id(cls)))
                    import_paths_tested.append(import_path)

            except (ImportError, AttributeError) as e:
                # Record but don't fail on import errors
                import_paths_tested.append(f"{import_path} (FAILED: {e})")

        # Group by class name to check for multiple implementations
        class_groups = {}
        for path, cls, cls_id in successful_imports:
            class_name = cls.__name__
            if class_name not in class_groups:
                class_groups[class_name] = []
            class_groups[class_name].append((path, cls, cls_id))

        print(f"\n=== EXECUTION ENGINE IMPORT PATH ANALYSIS ===")
        print(f"Tested import paths: {len(import_paths_tested)}")
        for path in import_paths_tested:
            print(f"  - {path}")

        print(f"\nSuccessful imports by class name:")
        violation_count = 0
        for class_name, imports in class_groups.items():
            print(f"  {class_name}:")
            unique_ids = set(cls_id for _, _, cls_id in imports)
            if len(unique_ids) > 1:
                violation_count += 1
                print(f"    ❌ VIOLATION: {len(unique_ids)} different class objects")
            else:
                print(f"    ✅ OK: Single class object")

            for path, cls, cls_id in imports:
                print(f"    - {path} (id: {cls_id})")

        # CRITICAL: This should fail if we have multiple different class objects
        # for the same class name
        self.assertEqual(violation_count, 0,
                        f"SSOT VIOLATION: Found {violation_count} classes with multiple implementations. "
                        f"Each class name should resolve to the same object.")

    def test_detect_execution_engine_factory_violations(self):
        """Test that detects factory pattern violations in execution engines.

        EXPECTED RESULT: This test should FAIL initially if singleton patterns are used.
        """
        factory_violations = []
        singleton_patterns = []

        # Check execution engine factory implementation
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory

            # Inspect the factory for singleton patterns
            factory_source = inspect.getsource(ExecutionEngineFactory)

            # Look for singleton indicators
            singleton_indicators = [
                '_instance',
                'global ',
                'singleton',
                '@classmethod',
                'if not hasattr(',
                'if cls._instance is None',
            ]

            for line_num, line in enumerate(factory_source.split('\n'), 1):
                line_lower = line.lower().strip()
                for indicator in singleton_indicators:
                    if indicator.lower() in line_lower:
                        singleton_patterns.append(f"Line {line_num}: {line.strip()}")

            # Check for proper user-scoped factory methods
            has_user_scoped = 'user_context' in factory_source or 'user_id' in factory_source
            has_create_method = 'def create(' in factory_source or 'def get(' in factory_source

            print(f"\n=== EXECUTION ENGINE FACTORY ANALYSIS ===")
            print(f"Singleton patterns found: {len(singleton_patterns)}")
            for pattern in singleton_patterns:
                print(f"  - {pattern}")

            print(f"Has user-scoped methods: {has_user_scoped}")
            print(f"Has factory create methods: {has_create_method}")

            # Check for factory violations
            if singleton_patterns and not has_user_scoped:
                factory_violations.append("Factory uses singleton pattern without user scoping")

            if not has_create_method:
                factory_violations.append("Factory missing proper create/get methods")

        except ImportError as e:
            factory_violations.append(f"Could not import ExecutionEngineFactory: {e}")

        print(f"Factory violations: {len(factory_violations)}")
        for violation in factory_violations:
            print(f"  - {violation}")

        # CRITICAL: This should fail if factory pattern violations are detected
        self.assertEqual(len(factory_violations), 0,
                        f"FACTORY PATTERN VIOLATIONS: Found {len(factory_violations)} violations. "
                        f"Details: {factory_violations}")

    def test_validate_execution_engine_ssot_redirections(self):
        """Test that validates SSOT redirection patterns are working correctly.

        This test checks if redirection files properly point to SSOT implementations.
        """
        redirection_status = {}

        # Check key redirection files
        redirection_files = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.execution_engine_consolidated',
        ]

        for module_path in redirection_files:
            try:
                module = importlib.import_module(module_path)
                module_source = inspect.getsource(module)

                # Check for proper SSOT redirection patterns
                has_ssot_comment = 'SSOT' in module_source
                has_import_redirect = 'from ' in module_source and 'import' in module_source
                has_deprecation = 'DEPRECATED' in module_source or 'deprecated' in module_source

                redirection_status[module_path] = {
                    'has_ssot_comment': has_ssot_comment,
                    'has_import_redirect': has_import_redirect,
                    'has_deprecation': has_deprecation,
                    'source_lines': len(module_source.split('\n'))
                }

            except ImportError as e:
                redirection_status[module_path] = {'error': str(e)}

        print(f"\n=== SSOT REDIRECTION ANALYSIS ===")
        for module_path, status in redirection_status.items():
            print(f"{module_path}:")
            if 'error' in status:
                print(f"  ❌ Import error: {status['error']}")
            else:
                print(f"  - SSOT comment: {status['has_ssot_comment']}")
                print(f"  - Import redirect: {status['has_import_redirect']}")
                print(f"  - Deprecation notice: {status['has_deprecation']}")
                print(f"  - Source lines: {status['source_lines']}")

        # Validate that redirection files are properly implemented
        for module_path, status in redirection_status.items():
            if 'error' not in status:
                self.assertTrue(status['has_ssot_comment'],
                              f"SSOT VIOLATION: {module_path} missing SSOT documentation")
                self.assertTrue(status['has_import_redirect'],
                              f"SSOT VIOLATION: {module_path} missing proper import redirection")

    def tearDown(self):
        """Clean up test environment and report findings."""
        super().tearDown()

        # Generate summary report
        print(f"\n=== EXECUTION ENGINE SSOT VIOLATION SUMMARY ===")
        print(f"Execution engines discovered: {len(self.discovered_engines)}")
        print(f"Import violations: {len(self.import_violations)}")

        if hasattr(self, '_outcome') and self._outcome.errors:
            print("❌ Test detected SSOT violations - THIS IS EXPECTED initially")
        else:
            print("✅ No SSOT violations detected")


if __name__ == '__main__':
    # Run this test file directly for development
    pytest.main([__file__, '-v', '-s'])