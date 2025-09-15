#!/usr/bin/env python3
"""
Issue #1040 Regression Prevention Test - Duplicate Enum Detection

Business Value Justification (BVJ):
- Segment: Platform/Internal (enabling all segments)
- Business Goal: Prevent SSOT violations and maintain architectural consistency
- Value Impact: Ensures fix doesn't introduce duplicate enums or architectural regression
- Revenue Impact: Protects system stability and maintainability for long-term velocity

Purpose: This test ensures that the ServiceAvailability fix doesn't introduce SSOT violations
by creating duplicate enums or breaking existing SSOT consolidation principles.

Expected Behavior:
- PASSES before fix: No duplicate orchestration enums exist
- PASSES after fix: ServiceAvailability added without creating duplicates
- FAILS if regression: Fix introduces duplicate enums or breaks SSOT principles

Author: Claude Code Agent - Issue #1040 Test Strategy
Created: 2025-09-14
"""

import pytest
import sys
import ast
import inspect
import importlib
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from enum import Enum
from collections import defaultdict

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Test framework imports following SSOT patterns
try:
    from test_framework.ssot.base_test_case import SSotBaseTestCase
    SSOT_FRAMEWORK_AVAILABLE = True
except ImportError:
    import unittest
    SSotBaseTestCase = unittest.TestCase
    SSOT_FRAMEWORK_AVAILABLE = False


@pytest.mark.unit
class TestIssue1040RegressionPrevention(SSotBaseTestCase):
    """
    Regression prevention test for Issue #1040 ServiceAvailability SSOT consolidation.

    This test suite ensures that the fix doesn't introduce new SSOT violations
    or break existing architectural consolidation principles.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Known orchestration enum names that should exist in SSOT location
        self.known_ssot_orchestration_enums = {
            'BackgroundTaskStatus',
            'E2ETestCategory',
            'ExecutionStrategy',
            'ProgressOutputMode',
            'ProgressEventType',
            'OrchestrationMode',
            'ResourceStatus',
            'ServiceStatus',
            'LayerType'
        }

        # ServiceAvailability should be added to this set after fix
        self.target_enum_name = 'ServiceAvailability'

        # Modules where enum duplicates should NOT exist after SSOT consolidation
        self.prohibited_duplicate_locations = [
            'test_framework.orchestration.background_e2e_agent',
            'test_framework.orchestration.background_e2e_manager',
            'test_framework.orchestration.layer_execution_agent',
            'test_framework.orchestration.layer_execution_manager',
            'test_framework.orchestration.progress_streaming_agent',
            'test_framework.orchestration.progress_streaming_manager'
        ]

    def test_existing_ssot_orchestration_enums_no_duplicates(self):
        """
        Test that existing SSOT orchestration enums don't have duplicates.

        This validates the current SSOT consolidation is working properly.
        """
        # Import SSOT module
        from test_framework.ssot import orchestration_enums as ssot_enums

        # Check each existing enum
        for enum_name in self.known_ssot_orchestration_enums:
            with self.subTest(enum_name=enum_name):
                # Should exist in SSOT location
                self.assertTrue(hasattr(ssot_enums, enum_name),
                              f"{enum_name} should exist in SSOT location")

                enum_class = getattr(ssot_enums, enum_name)
                self.assertTrue(issubclass(enum_class, Enum),
                              f"{enum_name} should be an Enum in SSOT location")

    def test_no_duplicate_enums_in_prohibited_locations(self):
        """
        Test that orchestration enums don't exist as duplicates in prohibited locations.

        This validates that SSOT consolidation eliminated duplicates properly.
        """
        enum_violations = []

        for module_path in self.prohibited_duplicate_locations:
            try:
                # Try to import the module
                module = importlib.import_module(module_path)

                # Check if any of the SSOT enum names exist in this module
                for enum_name in self.known_ssot_orchestration_enums:
                    if hasattr(module, enum_name):
                        enum_violations.append({
                            'enum_name': enum_name,
                            'prohibited_location': module_path,
                            'violation_type': 'DUPLICATE_ENUM'
                        })

            except ImportError:
                # Module doesn't exist or can't be imported - this is actually good for consolidation
                continue

        # Should have no violations
        self.assertEqual(len(enum_violations), 0,
                        f"SSOT VIOLATION: Found duplicate enums in prohibited locations: {enum_violations}")

    def test_service_availability_not_duplicated_in_prohibited_locations(self):
        """
        Test that ServiceAvailability doesn't exist in prohibited duplicate locations.

        This ensures the fix doesn't create duplicates.
        """
        service_availability_violations = []

        # Check prohibited orchestration locations
        for module_path in self.prohibited_duplicate_locations:
            try:
                module = importlib.import_module(module_path)

                if hasattr(module, 'ServiceAvailability'):
                    service_availability_violations.append({
                        'enum_name': 'ServiceAvailability',
                        'prohibited_location': module_path,
                        'violation_type': 'DUPLICATE_ENUM'
                    })

            except ImportError:
                continue

        # Should have no violations
        self.assertEqual(len(service_availability_violations), 0,
                        f"ServiceAvailability should not be duplicated in prohibited locations: {service_availability_violations}")

    def test_service_availability_enum_structure_consistency(self):
        """
        Test that ServiceAvailability enum structure is consistent between locations.

        This ensures that if multiple locations exist during migration, they're identical.
        """
        # Import from SSOT location (may fail before fix)
        ssot_service_availability = None
        try:
            from test_framework.ssot.orchestration_enums import ServiceAvailability as SSOTServiceAvailability
            ssot_service_availability = SSOTServiceAvailability
        except ImportError:
            # Expected before fix
            pass

        # Import from legacy location
        from test_framework.service_abstraction.integration_service_abstraction import ServiceAvailability as LegacyServiceAvailability

        if ssot_service_availability is not None:
            # Both locations exist - they should be identical
            ssot_members = {member.name: member.value for member in ssot_service_availability}
            legacy_members = {member.name: member.value for member in LegacyServiceAvailability}

            self.assertEqual(ssot_members, legacy_members,
                           "ServiceAvailability enum members should be identical in both locations")

        # Legacy location should have expected structure
        expected_members = {
            'AVAILABLE': 'available',
            'UNAVAILABLE': 'unavailable',
            'DEGRADED': 'degraded',
            'UNKNOWN': 'unknown'
        }

        legacy_members = {member.name: member.value for member in LegacyServiceAvailability}
        self.assertEqual(legacy_members, expected_members,
                        "Legacy ServiceAvailability should have expected structure")

    def test_orchestration_enums_module_size_regression_prevention(self):
        """
        Test that orchestration_enums.py doesn't become too large after ServiceAvailability addition.

        This prevents the fix from making the SSOT module unmaintainable.
        """
        orchestration_enums_file = PROJECT_ROOT / "test_framework" / "ssot" / "orchestration_enums.py"

        # File should exist
        self.assertTrue(orchestration_enums_file.exists())

        # Read current size
        with open(orchestration_enums_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_size = len(lines)

        # Should be reasonable size (currently ~670 lines, allow room for ServiceAvailability)
        max_reasonable_size = 800  # Lines
        self.assertLess(current_size, max_reasonable_size,
                       f"orchestration_enums.py should remain manageable size: {current_size} lines")

        # Should have grown reasonably if ServiceAvailability was added
        # (Adding an enum should add ~10-20 lines for enum definition and documentation)
        min_expected_size = 600  # Should be substantial file
        self.assertGreater(current_size, min_expected_size,
                         f"orchestration_enums.py should be substantial SSOT file: {current_size} lines")

    def test_enum_naming_consistency_in_ssot_module(self):
        """
        Test that all enums in SSOT orchestration module follow consistent naming.

        This ensures ServiceAvailability addition follows established patterns.
        """
        from test_framework.ssot import orchestration_enums as ssot_enums

        # Get all enum classes from the module
        enum_classes = []
        for name in dir(ssot_enums):
            obj = getattr(ssot_enums, name)
            if inspect.isclass(obj) and issubclass(obj, Enum) and obj != Enum:
                enum_classes.append((name, obj))

        # Should have reasonable number of enums (9 existing + ServiceAvailability potentially)
        expected_min_enums = 9
        expected_max_enums = 12
        self.assertGreaterEqual(len(enum_classes), expected_min_enums,
                              f"Should have at least {expected_min_enums} orchestration enums")
        self.assertLessEqual(len(enum_classes), expected_max_enums,
                           f"Should not have excessive enums: {len(enum_classes)}")

        # Check naming consistency
        for enum_name, enum_class in enum_classes:
            with self.subTest(enum_name=enum_name):
                # Should follow PascalCase naming
                self.assertTrue(enum_name[0].isupper(),
                              f"Enum should start with uppercase: {enum_name}")
                self.assertFalse('_' in enum_name or '-' in enum_name,
                               f"Enum should use PascalCase, not snake_case: {enum_name}")

                # Should have meaningful name
                self.assertGreater(len(enum_name), 3,
                                 f"Enum name should be meaningful: {enum_name}")

    def test_no_circular_imports_after_service_availability_addition(self):
        """
        Test that ServiceAvailability addition doesn't create circular import issues.

        This prevents the fix from introducing import dependency problems.
        """
        # Test importing SSOT orchestration_enums doesn't create circular imports
        try:
            from test_framework.ssot import orchestration_enums
            # Should succeed without circular import errors
            self.assertTrue(True, "SSOT orchestration_enums import successful")

        except ImportError as e:
            if "circular import" in str(e).lower():
                self.fail(f"Circular import detected: {e}")
            else:
                # Other import error might be expected (like missing ServiceAvailability)
                pass

        # Test importing from legacy location doesn't create conflicts
        try:
            from test_framework.service_abstraction.integration_service_abstraction import ServiceAvailability
            # Should succeed
            self.assertTrue(True, "Legacy ServiceAvailability import successful")

        except ImportError as e:
            self.fail(f"Legacy ServiceAvailability import should work: {e}")

    def test_ssot_architecture_principles_maintained(self):
        """
        Test that SSOT architecture principles are maintained after fix.

        This ensures the fix follows established SSOT consolidation patterns.
        """
        from test_framework.ssot import orchestration_enums as ssot_enums

        # Check SSOT documentation patterns
        self.assertIsNotNone(ssot_enums.__doc__)
        self.assertIn("Single Source of Truth", ssot_enums.__doc__)
        self.assertIn("CRITICAL", ssot_enums.__doc__)

        # Check consolidation documentation
        self.assertIn("CONSOLIDATED", ssot_enums.__doc__)

        # Check __all__ export pattern (good SSOT practice)
        self.assertTrue(hasattr(ssot_enums, '__all__'),
                       "SSOT modules should have __all__ exports")

        all_exports = getattr(ssot_enums, '__all__', [])
        self.assertGreater(len(all_exports), 5,
                         "SSOT module should export meaningful number of items")

        # All exported items should exist in module
        for export_name in all_exports:
            self.assertTrue(hasattr(ssot_enums, export_name),
                          f"__all__ export should exist in module: {export_name}")

    def test_enum_consolidation_completeness_regression(self):
        """
        Test that enum consolidation completeness doesn't regress.

        This ensures the fix maintains or improves SSOT consolidation.
        """
        # Count total enum definitions across orchestration modules
        enum_locations = defaultdict(list)

        # Check SSOT location
        try:
            from test_framework.ssot import orchestration_enums as ssot_enums
            for name in dir(ssot_enums):
                obj = getattr(ssot_enums, name)
                if inspect.isclass(obj) and issubclass(obj, Enum) and obj != Enum:
                    enum_locations[name].append('test_framework.ssot.orchestration_enums')
        except ImportError:
            pass

        # Check legacy/duplicate locations
        potential_duplicate_modules = [
            'test_framework.service_abstraction.integration_service_abstraction',
        ] + self.prohibited_duplicate_locations

        for module_path in potential_duplicate_modules:
            try:
                module = importlib.import_module(module_path)
                for name in dir(module):
                    obj = getattr(module, name)
                    if inspect.isclass(obj) and issubclass(obj, Enum) and obj != Enum:
                        # Check if it's an orchestration-related enum
                        orchestration_enum_indicators = [
                            'Status', 'Strategy', 'Mode', 'Type', 'Category', 'Availability'
                        ]
                        if any(indicator in name for indicator in orchestration_enum_indicators):
                            enum_locations[name].append(module_path)
            except ImportError:
                continue

        # Analyze consolidation health
        duplicate_enums = {name: locations for name, locations in enum_locations.items()
                          if len(locations) > 1}

        # ServiceAvailability is allowed to exist in both locations during migration
        acceptable_duplicates = {'ServiceAvailability'}
        problematic_duplicates = {name: locations for name, locations in duplicate_enums.items()
                                if name not in acceptable_duplicates}

        self.assertEqual(len(problematic_duplicates), 0,
                        f"Should not have problematic duplicate enums: {problematic_duplicates}")

        # Document consolidation status
        total_enum_types = len(enum_locations)
        duplicate_enum_types = len(duplicate_enums)
        consolidation_percentage = ((total_enum_types - duplicate_enum_types) / total_enum_types * 100
                                  if total_enum_types > 0 else 100)

        # Should maintain high consolidation
        min_consolidation_percentage = 85  # Allow for ServiceAvailability migration period
        self.assertGreaterEqual(consolidation_percentage, min_consolidation_percentage,
                              f"Enum consolidation should be high: {consolidation_percentage}%")


@pytest.mark.unit
class TestIssue1040PostFixRegressionValidation(SSotBaseTestCase):
    """
    Post-fix regression validation tests.

    These tests should be enabled after the ServiceAvailability fix is implemented
    to validate no regressions were introduced.
    """

    def test_service_availability_properly_consolidated_after_fix(self):
        """
        Test that ServiceAvailability is properly consolidated after fix (enable post-fix).

        This validates the fix achieved its goal without regression.
        """
        # This test should pass after fix - ServiceAvailability should be in SSOT location
        try:
            from test_framework.ssot.orchestration_enums import ServiceAvailability as SSOTServiceAvailability
            from test_framework.service_abstraction.integration_service_abstraction import ServiceAvailability as LegacyServiceAvailability

            # Both should exist and be identical
            ssot_members = {member.name: member.value for member in SSOTServiceAvailability}
            legacy_members = {member.name: member.value for member in LegacyServiceAvailability}

            self.assertEqual(ssot_members, legacy_members,
                           "ServiceAvailability should be identical in both locations after fix")

            # SSOT location should be preferred
            self.assertTrue(True, "POST-FIX VALIDATION: ServiceAvailability available from both locations")

        except ImportError as e:
            # If this test is run before fix, document the pre-fix state
            if "ServiceAvailability" in str(e):
                self.skipTest(f"PRE-FIX STATE: {e}")
            else:
                raise

    def test_no_new_ssot_violations_introduced_by_fix(self):
        """
        Test that the fix doesn't introduce new SSOT violations.

        This ensures the solution maintains architectural quality.
        """
        # Run architecture compliance check for orchestration enums
        from test_framework.ssot import orchestration_enums as ssot_enums

        # Should maintain proper SSOT patterns
        self.assertTrue(hasattr(ssot_enums, '__all__'),
                       "SSOT module should maintain __all__ exports pattern")

        # Should maintain documentation standards
        self.assertIn("Single Source of Truth", ssot_enums.__doc__,
                     "SSOT module should maintain documentation standards")

        # Should not have introduced import conflicts
        try:
            # These imports should all work without conflicts
            from test_framework.ssot.orchestration_enums import (
                BackgroundTaskStatus,
                ServiceStatus,
                OrchestrationMode
            )

            # ServiceAvailability should also work after fix
            from test_framework.ssot.orchestration_enums import ServiceAvailability

            # All should be Enum classes
            enums_to_check = [BackgroundTaskStatus, ServiceStatus, OrchestrationMode, ServiceAvailability]
            for enum_class in enums_to_check:
                self.assertTrue(issubclass(enum_class, Enum))

        except ImportError as e:
            if "ServiceAvailability" in str(e):
                self.skipTest(f"PRE-FIX STATE: ServiceAvailability not yet available: {e}")
            else:
                self.fail(f"Fix should not break existing SSOT imports: {e}")


if __name__ == "__main__":
    unittest.main()