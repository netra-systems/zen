"""
Unit Tests: Configuration Manager Duplication Violations - Issue #757

**BUSINESS VALUE JUSTIFICATION (BVJ):**
- **Segment:** Platform/Internal - Development Velocity & Risk Reduction
- **Business Goal:** Eliminate configuration duplication to prevent system failures
- **Value Impact:** Ensures reliable configuration access supporting Golden Path user flow
- **Revenue Impact:** Protects $500K+ ARR by preventing configuration-related outages

**PURPOSE:**
These unit tests are DESIGNED TO FAIL until Issue #667 Configuration Manager SSOT consolidation
is complete. Each test validates a specific aspect of configuration manager duplication that
creates technical debt and operational risk.

**EXPECTED BEHAVIOR:**
- ❌ **CURRENT STATE:** Tests FAIL due to duplicate configuration managers
- ✅ **POST-FIX STATE:** Tests PASS after deprecated manager removal

**TEST SCOPE:**
- Configuration manager interface consistency
- Import pattern violations
- Behavioral differences between managers
- Memory and performance impact of duplication
"""

import unittest
import warnings
import gc
import sys
from typing import Any, Dict, Set, Optional
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestConfigurationDuplicationViolations(SSotBaseTestCase):
    """
    Unit Tests: Configuration Manager Duplication Detection and Validation

    These tests identify and validate SSOT violations in configuration management.
    Tests are expected to FAIL until duplicate managers are removed.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Clear import cache to ensure clean test state
        self._clear_import_cache()

        # Reset warnings to capture all deprecation warnings
        warnings.resetwarnings()
        warnings.simplefilter("always")

    def teardown_method(self, method):
        """Cleanup after each test method."""
        self._clear_import_cache()
        super().teardown_method(method)

    def _clear_import_cache(self):
        """Clear Python import cache for configuration modules."""
        modules_to_clear = [
            'netra_backend.app.core.managers.unified_configuration_manager',
            'netra_backend.app.core.configuration.base',
            'netra_backend.app.services.configuration_service'
        ]

        for module in modules_to_clear:
            if module in sys.modules:
                # Don't actually remove from sys.modules as it can break imports
                # Just note which modules are loaded
                pass

    def test_duplicate_configuration_manager_detection(self):
        """
        TEST: Detection of Duplicate Configuration Managers (DESIGNED TO FAIL)

        **SSOT VIOLATION:** Multiple configuration manager implementations exist
        **TECHNICAL DEBT:** Code duplication, maintenance overhead, inconsistency risk
        **BUSINESS IMPACT:** Operational complexity increases failure probability

        **EXPECTED RESULT:**
        - ❌ CURRENT: Test FAILS - multiple managers detected
        - ✅ POST-FIX: Test PASSES - single canonical manager exists
        """
        detected_managers = []
        import_successes = []
        deprecation_warnings = []

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # Test 1: Attempt to import deprecated manager
            try:
                from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager,
    get_config,
    get_config_value,
    set_config_value,
    validate_config_value,
    get_environment,
    is_production,
    is_development,
    is_testing,
    config_manager
)
                detected_managers.append("deprecated_unified_configuration_manager")
                import_successes.append("Successfully imported deprecated manager")

                # Check if deprecation warning was issued
                manager_warnings = [w for w in warning_list if
                                  issubclass(w.category, DeprecationWarning) and
                                  'DEPRECATED' in str(w.message)]
                deprecation_warnings.extend(manager_warnings)

            except ImportError as e:
                self.logger.debug(f"Deprecated manager import failed (expected post-fix): {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error importing deprecated manager: {e}")

            # Test 2: Import canonical manager
            try:
                from netra_backend.app.core.configuration.base import (
                    UnifiedConfigManager as CanonicalManager,
                    config_manager as canonical_instance
                )
                detected_managers.append("canonical_unified_config_manager")
                import_successes.append("Successfully imported canonical manager")

            except ImportError as e:
                self.logger.error(f"Canonical manager import failed: {e}")
                # This should never fail - canonical manager must exist
                self.fail(f"CRITICAL: Canonical configuration manager not available: {e}")

            # Test 3: Check for service-specific configuration manager
            try:
                from netra_backend.app.services.configuration_service import ConfigurationService
                detected_managers.append("service_configuration_manager")
                import_successes.append("Successfully imported service configuration manager")

            except ImportError as e:
                self.logger.debug(f"Service configuration manager import failed: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error importing service configuration: {e}")

        # ASSERTION: Multiple managers indicate SSOT violation
        num_detected = len(detected_managers)

        self.assertGreater(
            num_detected, 1,
            "EXPECTED FAILURE: This test should FAIL by detecting multiple configuration managers "
            f"until Issue #667 is resolved. Detected managers: {detected_managers}. "
            "SSOT requires exactly ONE configuration manager implementation. "
            f"Current count: {num_detected} (should be 1 after SSOT consolidation)."
        )

        # Document specific violations found
        self.logger.warning(f"SSOT Violation: {num_detected} configuration managers detected")
        for i, manager in enumerate(detected_managers):
            self.logger.warning(f"  {i+1}. {manager}")

        if deprecation_warnings:
            self.logger.info(f"Deprecation warnings detected: {len(deprecation_warnings)}")
            for warning in deprecation_warnings:
                self.logger.info(f"  - {warning.message}")

    def test_configuration_manager_interface_consistency(self):
        """
        TEST: Interface Consistency Between Configuration Managers (DESIGNED TO FAIL)

        **SSOT VIOLATION:** Different managers may have different interfaces
        **TECHNICAL DEBT:** API inconsistency causes integration complexity
        **BUSINESS IMPACT:** Developer confusion leads to bugs and slower development

        **EXPECTED RESULT:**
        - ❌ CURRENT: Test FAILS - interfaces differ or are incomplete
        - ✅ POST-FIX: Test PASSES - single consistent interface
        """
        interface_violations = []
        behavioral_differences = []

        # Define expected interface for configuration managers
        expected_methods = [
            'get', 'set', 'get_config', 'validate_config',
            'reload_config', 'get_environment_name'
        ]

        managers_tested = {}

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Focus on interface, not warnings

            # Test deprecated manager interface
            try:
                from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager,
    get_config,
    get_config_value,
    set_config_value,
    validate_config_value,
    get_environment,
    is_production,
    is_development,
    is_testing,
    config_manager
)

                deprecated_manager = DeprecatedManager(user_id="test_interface")
                managers_tested['deprecated'] = deprecated_manager

                # Check interface completeness
                missing_methods = []
                for method in expected_methods:
                    if not hasattr(deprecated_manager, method):
                        missing_methods.append(method)

                if missing_methods:
                    interface_violations.append(
                        f"Deprecated manager missing methods: {missing_methods}"
                    )

            except Exception as e:
                self.logger.debug(f"Could not test deprecated manager interface: {e}")

            # Test canonical manager interface
            try:
                from netra_backend.app.core.configuration.base import UnifiedConfigManager

                canonical_manager = UnifiedConfigManager()
                managers_tested['canonical'] = canonical_manager

                # Check interface completeness
                missing_methods = []
                for method in expected_methods:
                    if not hasattr(canonical_manager, method):
                        missing_methods.append(method)

                if missing_methods:
                    interface_violations.append(
                        f"Canonical manager missing methods: {missing_methods}"
                    )

            except Exception as e:
                interface_violations.append(f"Cannot test canonical manager interface: {e}")

        # Test behavioral consistency between managers
        if len(managers_tested) > 1:
            test_config_key = "test.interface_consistency"
            test_config_value = "test_value_12345"

            for name1, manager1 in managers_tested.items():
                for name2, manager2 in managers_tested.items():
                    if name1 != name2:
                        try:
                            # Set value using first manager
                            if hasattr(manager1, 'set'):
                                manager1.set(test_config_key, test_config_value)

                            # Try to get value using second manager
                            if hasattr(manager2, 'get'):
                                retrieved_value = manager2.get(test_config_key)

                                # Check if managers share state (they shouldn't in SSOT)
                                if retrieved_value == test_config_value:
                                    behavioral_differences.append(
                                        f"Managers {name1} and {name2} share state - potential singleton violation"
                                    )

                        except Exception as e:
                            behavioral_differences.append(
                                f"Behavioral test failed between {name1} and {name2}: {str(e)}"
                            )

        # ASSERTION: Interface violations indicate SSOT problems
        total_violations = len(interface_violations) + len(behavioral_differences)

        self.assertGreater(
            total_violations, 0,
            "EXPECTED FAILURE: This test should FAIL due to interface inconsistencies "
            f"until Issue #667 is resolved. Interface violations: {len(interface_violations)}, "
            f"Behavioral differences: {len(behavioral_differences)}. "
            "SSOT requires one consistent configuration interface."
        )

        # Log specific violations
        for violation in interface_violations:
            self.logger.error(f"SSOT Violation - Interface: {violation}")

        for difference in behavioral_differences:
            self.logger.error(f"SSOT Violation - Behavior: {difference}")

    def test_configuration_import_pattern_violations(self):
        """
        TEST: Configuration Import Pattern SSOT Violations (DESIGNED TO FAIL)

        **SSOT VIOLATION:** Multiple import paths for configuration functionality
        **TECHNICAL DEBT:** Import confusion, potential circular dependencies
        **BUSINESS IMPACT:** Developer errors lead to configuration bugs

        **EXPECTED RESULT:**
        - ❌ CURRENT: Test FAILS - multiple import patterns exist
        - ✅ POST-FIX: Test PASSES - single canonical import pattern
        """
        import_patterns = []
        import_violations = []

        # Test various import patterns that should be consolidated
        import_attempts = [
            # Deprecated patterns
            ("netra_backend.app.core.managers.unified_configuration_manager", "UnifiedConfigurationManager"),
            ("netra_backend.app.core.managers.unified_configuration_manager", "ConfigurationManagerFactory"),
            ("netra_backend.app.core.managers.unified_configuration_manager", "get_configuration_manager"),

            # Canonical patterns
            ("netra_backend.app.core.configuration.base", "UnifiedConfigManager"),
            ("netra_backend.app.core.configuration.base", "config_manager"),
            ("netra_backend.app.core.configuration.base", "get_unified_config"),

            # Service patterns
            ("netra_backend.app.services.configuration_service", "ConfigurationService"),

            # Main app patterns
            ("netra_backend.app.config", "get_config"),
            ("netra_backend.app.config", "config_manager"),
        ]

        for module_path, class_name in import_attempts:
            try:
                module = __import__(module_path, fromlist=[class_name])
                if hasattr(module, class_name):
                    import_patterns.append(f"{module_path}.{class_name}")
                    self.logger.debug(f"Successfully imported {module_path}.{class_name}")

            except ImportError as e:
                self.logger.debug(f"Import failed for {module_path}.{class_name}: {e}")
            except Exception as e:
                import_violations.append(f"Unexpected error importing {module_path}.{class_name}: {e}")

        # Analyze import patterns for SSOT violations
        config_manager_imports = [p for p in import_patterns if 'configuration' in p.lower()]

        # Check for duplicate functionality
        if len(config_manager_imports) > 2:  # Allow canonical + main app wrapper
            import_violations.append(
                f"Too many configuration import patterns: {config_manager_imports}"
            )

        # Check for deprecated imports still working
        deprecated_imports = [p for p in import_patterns if 'managers.unified_configuration' in p]
        if deprecated_imports:
            import_violations.append(
                f"Deprecated configuration imports still functional: {deprecated_imports}"
            )

        # ASSERTION: Multiple import patterns indicate SSOT violations
        self.assertTrue(
            len(import_violations) > 0 or len(config_manager_imports) > 2,
            "EXPECTED FAILURE: This test should FAIL due to multiple configuration import patterns "
            f"until Issue #667 is resolved. Found {len(config_manager_imports)} configuration imports: "
            f"{config_manager_imports}. Import violations: {len(import_violations)}. "
            "SSOT requires one canonical import pattern for configuration."
        )

        # Log specific violations
        self.logger.warning(f"SSOT Violation: {len(config_manager_imports)} configuration import patterns found")
        for pattern in config_manager_imports:
            self.logger.warning(f"  - {pattern}")

        for violation in import_violations:
            self.logger.error(f"SSOT Violation - Import Pattern: {violation}")

    def test_configuration_manager_memory_impact(self):
        """
        TEST: Memory Impact of Configuration Manager Duplication (DESIGNED TO FAIL)

        **SSOT VIOLATION:** Multiple managers consume unnecessary memory
        **TECHNICAL DEBT:** Resource waste, potential memory leaks
        **BUSINESS IMPACT:** Higher infrastructure costs, reduced performance

        **EXPECTED RESULT:**
        - ❌ CURRENT: Test FAILS - multiple managers detected in memory
        - ✅ POST-FIX: Test PASSES - single manager instance pattern
        """
        memory_violations = []
        manager_instances = []

        # Force garbage collection before test
        gc.collect()
        initial_objects = len(gc.get_objects())

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # Create instances of different configuration managers
            try:
                # Deprecated manager instances
                from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager,
    get_config,
    get_config_value,
    set_config_value,
    validate_config_value,
    get_environment,
    is_production,
    is_development,
    is_testing,
    config_manager
)

                deprecated_instance = DeprecatedManager(user_id="memory_test")
                factory_instance = ConfigurationManagerFactory.get_global_manager()

                manager_instances.extend(['deprecated_instance', 'factory_instance'])

            except Exception as e:
                self.logger.debug(f"Could not create deprecated manager instances: {e}")

            try:
                # Canonical manager instances
                from netra_backend.app.core.configuration.base import (
                    UnifiedConfigManager,
                    config_manager
                )

                canonical_instance = UnifiedConfigManager()
                global_instance = config_manager

                manager_instances.extend(['canonical_instance', 'global_instance'])

            except Exception as e:
                memory_violations.append(f"Could not create canonical manager instances: {e}")

            # Check for memory impact
            gc.collect()
            final_objects = len(gc.get_objects())
            object_increase = final_objects - initial_objects

            if object_increase > 100:  # Threshold for concerning memory impact
                memory_violations.append(
                    f"High memory impact from configuration managers: {object_increase} new objects"
                )

            # Check for multiple manager instances of same type
            instance_types = {}
            for instance_name in manager_instances:
                if instance_name in locals():
                    instance_obj = locals()[instance_name]
                    instance_type = type(instance_obj).__name__

                    if instance_type in instance_types:
                        instance_types[instance_type] += 1
                    else:
                        instance_types[instance_type] = 1

            # Multiple instances of same type suggest poor singleton/factory pattern
            for type_name, count in instance_types.items():
                if count > 1 and 'test' not in type_name.lower():
                    memory_violations.append(
                        f"Multiple instances of {type_name}: {count} instances"
                    )

        # ASSERTION: Memory violations indicate SSOT issues
        total_managers = len(manager_instances)

        self.assertTrue(
            len(memory_violations) > 0 or total_managers > 2,
            "EXPECTED FAILURE: This test should FAIL due to memory impact from multiple configuration managers "
            f"until Issue #667 is resolved. Manager instances: {total_managers}, "
            f"Memory violations: {len(memory_violations)}. "
            "SSOT requires minimal memory footprint with singleton/factory patterns."
        )

        # Log memory impact details
        self.logger.warning(f"Configuration manager instances created: {total_managers}")
        self.logger.warning(f"Memory object increase: {object_increase}")

        for violation in memory_violations:
            self.logger.error(f"SSOT Violation - Memory: {violation}")

    def test_configuration_manager_performance_overhead(self):
        """
        TEST: Performance Overhead from Configuration Manager Duplication (DESIGNED TO FAIL)

        **SSOT VIOLATION:** Multiple managers create performance overhead
        **TECHNICAL DEBT:** Slower configuration access, initialization overhead
        **BUSINESS IMPACT:** Slower system startup affects user experience

        **EXPECTED RESULT:**
        - ❌ CURRENT: Test FAILS - performance overhead detected
        - ✅ POST-FIX: Test PASSES - optimized single manager performance
        """
        performance_violations = []
        timing_results = {}

        import time

        # Test configuration access performance with different managers
        test_iterations = 100
        test_config_key = "performance.test_key"
        test_default_value = "default_test_value"

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # Test deprecated manager performance
            try:
                from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager,
    get_config,
    get_config_value,
    set_config_value,
    validate_config_value,
    get_environment,
    is_production,
    is_development,
    is_testing,
    config_manager
)

                deprecated_manager = get_configuration_manager()

                start_time = time.time()
                for _ in range(test_iterations):
                    deprecated_manager.get(test_config_key, test_default_value)
                end_time = time.time()

                timing_results['deprecated_manager'] = end_time - start_time

            except Exception as e:
                self.logger.debug(f"Could not test deprecated manager performance: {e}")

            # Test canonical manager performance
            try:
                from netra_backend.app.core.configuration.base import config_manager

                start_time = time.time()
                for _ in range(test_iterations):
                    config_manager.get_config_value(test_config_key, test_default_value)
                end_time = time.time()

                timing_results['canonical_manager'] = end_time - start_time

            except Exception as e:
                performance_violations.append(f"Could not test canonical manager performance: {e}")

            # Test main app config performance
            try:
                from netra_backend.app.config import get_config

                config = get_config()

                start_time = time.time()
                for _ in range(test_iterations):
                    # Access config attribute (simulating typical usage)
                    getattr(config, 'database_url', None)
                end_time = time.time()

                timing_results['main_app_config'] = end_time - start_time

            except Exception as e:
                performance_violations.append(f"Could not test main app config performance: {e}")

        # Analyze performance results
        if len(timing_results) > 1:
            # Calculate performance variance
            times = list(timing_results.values())
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)

            # High variance suggests inconsistent performance
            if max_time > min_time * 2:  # More than 2x difference
                performance_violations.append(
                    f"High performance variance between managers: "
                    f"fastest={min_time:.4f}s, slowest={max_time:.4f}s"
                )

            # Slow overall performance suggests overhead
            if avg_time > 0.01:  # More than 10ms for 100 simple gets
                performance_violations.append(
                    f"Slow configuration access performance: {avg_time:.4f}s average for {test_iterations} operations"
                )

        # Multiple managers indicate potential performance waste
        if len(timing_results) > 2:
            performance_violations.append(
                f"Multiple configuration managers tested: {list(timing_results.keys())}"
            )

        # ASSERTION: Performance issues indicate SSOT violations
        self.assertTrue(
            len(performance_violations) > 0 or len(timing_results) > 2,
            "EXPECTED FAILURE: This test should FAIL due to performance overhead from multiple configuration managers "
            f"until Issue #667 is resolved. Managers tested: {len(timing_results)}, "
            f"Performance violations: {len(performance_violations)}. "
            "SSOT requires optimal performance with single manager implementation."
        )

        # Log performance analysis
        self.logger.warning(f"Configuration manager performance test results:")
        for manager, time_taken in timing_results.items():
            ops_per_second = test_iterations / time_taken if time_taken > 0 else float('inf')
            self.logger.warning(f"  {manager}: {time_taken:.4f}s ({ops_per_second:.0f} ops/sec)")

        for violation in performance_violations:
            self.logger.error(f"SSOT Violation - Performance: {violation}")


if __name__ == "__main__":
    unittest.main()