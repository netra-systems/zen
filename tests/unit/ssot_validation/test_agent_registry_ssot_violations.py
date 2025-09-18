"""
Unit Tests for Agent Registry SSOT Violations Detection

Issue #909: Critical P0 SSOT violations in agent execution infrastructure
These tests detect multiple competing SSOT implementations causing race conditions.

Business Impact: $500K+ ARR at risk due to Golden Path success rate at ~60% (needs 99.9%)
"""

import pytest
import sys
import importlib
import inspect
from typing import Set, List, Dict, Any
from unittest.mock import patch, MagicMock

# SSOT test framework imports
try:
    from test_framework.ssot.base_test_case import SSotBaseTestCase
except ImportError:
    # Fallback if SSOT framework not available
    import unittest
    SSotBaseTestCase = unittest.TestCase


class TestAgentRegistrySSotViolations(SSotBaseTestCase):
    """Test suite to detect Agent Registry SSOT violations."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.discovered_registries = []
        self.import_violations = []

    def test_detect_multiple_agent_registries(self):
        """Test that detects multiple AgentRegistry implementations.

        EXPECTED RESULT: This test should FAIL initially to prove it detects violations.
        """
        registry_classes = []
        registry_locations = []

        # Initialize import_violations for this test
        self.import_violations = []

        # Known registry locations to check
        registry_paths = [
            'netra_backend.app.agents.registry',
            'netra_backend.app.agents.supervisor.agent_registry',
            'netra_backend.app.agents.supervisor.agent_class_registry',
            'netra_backend.app.agents.execution_tracking.registry',
        ]

        for path in registry_paths:
            try:
                module = importlib.import_module(path)
                # Look for registry classes
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if 'Registry' in name and name not in ['BaseAgentRegistry']:
                        registry_classes.append((name, obj, path))
                        registry_locations.append(f"{path}.{name}")
            except ImportError as e:
                self.import_violations.append(f"Failed to import {path}: {e}")

        # Store findings for analysis
        self.discovered_registries = registry_classes

        # CRITICAL: This assertion should FAIL to prove we detect violations
        violation_count = len([r for r in registry_classes if 'AgentRegistry' in r[0]])

        # Document findings
        print(f"\n=== SSOT VIOLATION ANALYSIS ===")
        print(f"Found {len(registry_classes)} registry classes:")
        for name, obj, path in registry_classes:
            print(f"  - {name} in {path}")
        print(f"Import violations: {len(self.import_violations)}")
        for violation in self.import_violations:
            print(f"  - {violation}")

        # This should fail initially - indicating we have multiple registries
        self.assertLessEqual(violation_count, 1,
                           f"SSOT VIOLATION: Found {violation_count} AgentRegistry classes, should be 1. "
                           f"Locations: {registry_locations}")

    def test_detect_import_path_multiplicity(self):
        """Test that detects multiple import paths for the same functionality.

        EXPECTED RESULT: This test should FAIL initially to prove it detects violations.
        """
        import_paths_tested = []
        successful_imports = []

        # Test different import paths that should resolve to the same class
        registry_import_paths = [
            'netra_backend.app.agents.registry.AgentRegistry',
            'netra_backend.app.agents.supervisor.agent_registry.AgentRegistry',
            'netra_backend.app.agents.registry.agent_registry',  # module-level
        ]

        for import_path in registry_import_paths:
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

        # Check if we have multiple classes with same name but different IDs
        class_ids = {cls_id for _, _, cls_id in successful_imports}

        print(f"\n=== IMPORT PATH ANALYSIS ===")
        print(f"Tested import paths: {len(import_paths_tested)}")
        for path in import_paths_tested:
            print(f"  - {path}")
        print(f"Successful imports: {len(successful_imports)}")
        for path, cls, cls_id in successful_imports:
            print(f"  - {path} -> {cls} (id: {cls_id})")
        print(f"Unique class IDs: {len(class_ids)}")

        # CRITICAL: This should fail if we have multiple different class objects
        # for what should be the same functionality
        if len(successful_imports) > 1:
            self.assertEqual(len(class_ids), 1,
                           f"SSOT VIOLATION: Multiple class IDs found for AgentRegistry imports. "
                           f"Should be same class object. Found IDs: {class_ids}")

    def test_detect_circular_import_dependencies(self):
        """Test that detects circular import dependencies in agent infrastructure.

        EXPECTED RESULT: This test should FAIL initially to prove it detects violations.
        """
        # Track import attempts to detect circular dependencies
        circular_imports = []

        with patch('importlib.import_module') as mock_import:
            original_import = importlib.import_module

            def tracking_import(name, package=None):
                # Detect if we're trying to import something that's already importing us
                frame = inspect.currentframe()
                import_stack = []

                while frame:
                    if 'importlib' in str(frame.f_code.co_filename):
                        frame = frame.f_back
                        continue
                    if frame.f_locals.get('__name__'):
                        import_stack.append(frame.f_locals['__name__'])
                    frame = frame.f_back

                # Check for circular patterns
                if name in import_stack:
                    circular_imports.append(f"{' -> '.join(import_stack)} -> {name}")

                return original_import(name, package)

            mock_import.side_effect = tracking_import

            # Test importing key agent modules that might have circular dependencies
            test_modules = [
                'netra_backend.app.agents.registry',
                'netra_backend.app.agents.supervisor.agent_registry',
                'netra_backend.app.agents.supervisor.execution_engine_factory',
            ]

            for module_name in test_modules:
                try:
                    importlib.import_module(module_name)
                except Exception as e:
                    circular_imports.append(f"Import error in {module_name}: {e}")

        print(f"\n=== CIRCULAR IMPORT ANALYSIS ===")
        print(f"Detected circular imports: {len(circular_imports)}")
        for circular in circular_imports:
            print(f"  - {circular}")

        # This should pass if no circular dependencies are detected
        self.assertEqual(len(circular_imports), 0,
                        f"CIRCULAR IMPORT VIOLATIONS: Found {len(circular_imports)} circular dependencies. "
                        f"Details: {circular_imports}")

    def test_validate_ssot_compliance_indicators(self):
        """Test that validates SSOT compliance indicators in the codebase.

        This test checks for specific SSOT compliance markers that should be present.
        """
        compliance_indicators = {}

        # Check main registry file for SSOT compliance markers
        try:
            import netra_backend.app.agents.registry as registry_module

            # Look for SSOT compliance indicators
            compliance_indicators['registry_ssot_success'] = getattr(
                registry_module, 'SSOT_CONSOLIDATION_SUCCESS', False
            )

            # Check if the registry has proper re-export
            compliance_indicators['has_agent_registry'] = hasattr(registry_module, 'AgentRegistry')

            # Check for deprecation warnings (good SSOT practice)
            compliance_indicators['has_deprecation_warning'] = any(
                'deprecation' in line.lower() or 'migration' in line.lower()
                for line in inspect.getsource(registry_module).lower().split('\n')
            )

        except ImportError as e:
            compliance_indicators['registry_import_error'] = str(e)

        print(f"\n=== SSOT COMPLIANCE ANALYSIS ===")
        for indicator, value in compliance_indicators.items():
            print(f"  - {indicator}: {value}")

        # Check critical compliance indicators
        if 'registry_ssot_success' in compliance_indicators:
            self.assertTrue(compliance_indicators['registry_ssot_success'],
                           "SSOT VIOLATION: Registry module reports SSOT_CONSOLIDATION_SUCCESS=False")

        self.assertTrue(compliance_indicators.get('has_agent_registry', False),
                       "SSOT VIOLATION: Registry module missing AgentRegistry export")

    def tearDown(self):
        """Clean up test environment and report findings."""
        super().tearDown()

        # Generate summary report
        print(f"\n=== SSOT VIOLATION SUMMARY ===")
        print(f"Registries discovered: {len(self.discovered_registries)}")
        print(f"Import violations: {len(self.import_violations)}")

        if hasattr(self, '_outcome') and self._outcome.errors:
            print("❌ Test detected SSOT violations - THIS IS EXPECTED initially")
        else:
            print("✅ No SSOT violations detected")


if __name__ == '__main__':
    # Run this test file directly for development
    pytest.main([__file__, '-v', '-s'])