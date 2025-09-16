"""Test Issue #1186: Singleton Violation Elimination Validation

This test suite validates the elimination of remaining singleton violations
identified in Issue #1186 Phase 4 status update for SSOT consolidation.

Expected Behavior: These tests SHOULD FAIL to demonstrate:
1. 8 remaining singleton violations requiring remediation
2. Singleton patterns in UserExecutionEngine usage
3. Shared state between user execution contexts
4. Global instance patterns preventing user isolation

Business Impact: Singleton violations prevent enterprise-grade multi-user isolation
and create security vulnerabilities affecting $500K+ ARR production deployment.

Business Value Justification (BVJ):
- Segment: Enterprise/Platform
- Business Goal: Eliminate singleton violations for enterprise security
- Value Impact: Enables secure multi-tenant production deployment
- Strategic Impact: Critical security foundation for enterprise customers
"""

import ast
import gc
import os
import re
import sys
import unittest
import pytest
import weakref
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from unittest.mock import Mock, patch


# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    # Create mock classes for testing when imports fail
    class UserExecutionEngine:
        def __init__(self, *args, **kwargs):
            pass

    class UserExecutionContext:
        pass

    class AgentInstanceFactory:
        pass


@pytest.mark.unit
class TestSingletonViolationElimination(unittest.TestCase):
    """Test class to validate singleton violation elimination"""

    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent

    def test_1_no_singleton_patterns_detected(self):
        """
        Test 1: Detect remaining singleton patterns in codebase

        EXPECTED TO FAIL: Should reveal the 8 remaining singleton violations from Issue #1186
        """
        print("\n🔍 SINGLETON TEST 1: Detecting singleton patterns...")

        singleton_patterns = self._scan_for_singleton_patterns()

        # This test should FAIL to demonstrate remaining singleton violations
        self.assertEqual(
            len(singleton_patterns),
            0,
            f"❌ EXPECTED FAILURE: Found {len(singleton_patterns)} singleton patterns. "
            f"Issue #1186 Phase 4 identified 8 remaining singleton violations requiring elimination:\n"
            + '\n'.join([f"  - {path}: {pattern}" for path, pattern in singleton_patterns[:8]])
            + (f"\n  ... and {len(singleton_patterns) - 8} more" if len(singleton_patterns) > 8 else "")
        )

    def test_2_multi_instance_isolation(self):
        """
        Test 2: Validate multiple UserExecutionEngine instances are isolated

        EXPECTED BEHAVIOR: Multiple instances should be completely isolated
        """
        print("\n🔍 SINGLETON TEST 2: Validating multi-instance isolation...")

        isolation_violations = self._test_multi_instance_isolation()

        # This test validates proper instance isolation
        self.assertEqual(
            len(isolation_violations),
            0,
            f"❌ INSTANCE ISOLATION FAILURE: Found {len(isolation_violations)} isolation violations. "
            f"These prevent proper user isolation required for enterprise deployment:\n"
            + '\n'.join([f"  - {violation}" for violation in isolation_violations])
        )

    def test_3_user_execution_engine_factory_compliance(self):
        """
        Test 3: Validate UserExecutionEngine uses factory patterns exclusively

        EXPECTED BEHAVIOR: Should validate factory-only instantiation
        """
        print("\n🔍 SINGLETON TEST 3: Validating factory pattern compliance...")

        factory_violations = self._validate_factory_compliance()

        # This test validates factory pattern usage
        self.assertEqual(
            len(factory_violations),
            0,
            f"❌ FACTORY COMPLIANCE FAILURE: Found {len(factory_violations)} factory pattern violations. "
            f"These indicate direct instantiation bypassing factory patterns:\n"
            + '\n'.join([f"  - {violation}" for violation in factory_violations])
        )

    def test_4_global_instance_detection(self):
        """
        Test 4: Detect global UserExecutionEngine instances

        EXPECTED TO FAIL: Should reveal global instances preventing user isolation
        """
        print("\n🔍 SINGLETON TEST 4: Detecting global instances...")

        global_instances = self._scan_for_global_instances()

        # This test should FAIL to demonstrate global instance violations
        self.assertEqual(
            len(global_instances),
            0,
            f"❌ EXPECTED FAILURE: Found {len(global_instances)} global UserExecutionEngine instances. "
            f"These create singleton-like behavior and prevent user isolation:\n"
            + '\n'.join([f"  - {path}: {instance}" for path, instance in global_instances])
        )

    def test_5_shared_state_elimination(self):
        """
        Test 5: Validate elimination of shared state in UserExecutionEngine

        EXPECTED BEHAVIOR: No shared state should exist between instances
        """
        print("\n🔍 SINGLETON TEST 5: Validating shared state elimination...")

        shared_state_violations = self._detect_shared_state()

        # This test validates shared state elimination
        self.assertEqual(
            len(shared_state_violations),
            0,
            f"❌ SHARED STATE FAILURE: Found {len(shared_state_violations)} shared state violations. "
            f"These create cross-user contamination risks:\n"
            + '\n'.join([f"  - {violation}" for violation in shared_state_violations])
        )

    def _scan_for_singleton_patterns(self) -> List[Tuple[str, str]]:
        """Scan codebase for singleton patterns"""
        singleton_patterns = []

        # Patterns that indicate singleton violations
        singleton_detection_patterns = [
            r'_instance\s*=\s*None',  # Instance storage
            r'__new__.*_instance',  # Singleton __new__ pattern
            r'@.*singleton',  # Singleton decorator
            r'global.*_instance',  # Global instance variables
            r'class.*Singleton',  # Singleton base classes
            r'if not hasattr.*_instance',  # Instance checking
            r'cls\._instance',  # Class instance attribute
            r'_instances\s*=\s*{}',  # Instance registry
        ]

        for py_file in self._get_execution_engine_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in singleton_detection_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        singleton_patterns.append((str(py_file), match))

            except (UnicodeDecodeError, PermissionError):
                continue

        return singleton_patterns

    def _test_multi_instance_isolation(self) -> List[str]:
        """Test that multiple UserExecutionEngine instances are isolated"""
        isolation_violations = []

        try:
            # Create mock dependencies
            mock_context1 = Mock(spec=UserExecutionContext)
            mock_context1.user_id = "user_1"

            mock_context2 = Mock(spec=UserExecutionContext)
            mock_context2.user_id = "user_2"

            mock_factory = Mock(spec=AgentInstanceFactory)
            mock_emitter = Mock()

            # Create multiple instances
            instance1 = UserExecutionEngine(mock_context1, mock_factory, mock_emitter)
            instance2 = UserExecutionEngine(mock_context2, mock_factory, mock_emitter)

            # Test instance isolation
            if instance1 is instance2:
                isolation_violations.append("Instances are identical (singleton behavior)")

            if id(instance1) == id(instance2):
                isolation_violations.append("Instances have same memory address")

            # Test for shared class attributes
            if hasattr(UserExecutionEngine, '_instance'):
                isolation_violations.append("Class has shared _instance attribute")

            if hasattr(UserExecutionEngine, '_instances'):
                isolation_violations.append("Class has shared _instances registry")

            # Test for shared state through class variables
            class_vars = [attr for attr in dir(UserExecutionEngine)
                         if not attr.startswith('__') and not callable(getattr(UserExecutionEngine, attr))]

            for var in class_vars:
                try:
                    value = getattr(UserExecutionEngine, var)
                    if isinstance(value, (dict, list, set)) and value:
                        isolation_violations.append(f"Class has shared mutable state: {var} = {value}")
                except Exception:
                    continue

        except Exception as e:
            isolation_violations.append(f"Error testing instance isolation: {e}")

        return isolation_violations

    def _validate_factory_compliance(self) -> List[str]:
        """Validate factory pattern compliance"""
        factory_violations = []

        try:
            # Check if direct instantiation is prevented
            try:
                # This should fail if proper dependency injection is enforced
                direct_instance = UserExecutionEngine()
                factory_violations.append("Direct instantiation without factory dependencies is allowed")
            except TypeError:
                # Expected behavior - constructor requires dependencies
                pass
            except Exception as e:
                factory_violations.append(f"Unexpected error during direct instantiation test: {e}")

            # Check for factory method usage in codebase
            factory_usage = self._scan_for_factory_usage()
            if not factory_usage:
                factory_violations.append("No factory pattern usage detected in codebase")

            # Check for direct instantiation patterns in code
            direct_instantiation_patterns = self._scan_for_direct_instantiation()
            if direct_instantiation_patterns:
                factory_violations.extend([
                    f"Direct instantiation found: {path}"
                    for path, _ in direct_instantiation_patterns
                ])

        except Exception as e:
            factory_violations.append(f"Error validating factory compliance: {e}")

        return factory_violations

    def _scan_for_global_instances(self) -> List[Tuple[str, str]]:
        """Scan for global UserExecutionEngine instances"""
        global_instances = []

        # Patterns that indicate global instances
        global_patterns = [
            r'global.*execution.*engine',  # Global execution engine
            r'_global_engine\s*=',  # Global engine variable
            r'ENGINE_INSTANCE\s*=',  # Constant instance
            r'DEFAULT_ENGINE\s*=',  # Default engine instance
            r'SHARED_ENGINE\s*=',  # Shared engine instance
        ]

        for py_file in self._get_execution_engine_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in global_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        global_instances.append((str(py_file), match))

            except (UnicodeDecodeError, PermissionError):
                continue

        return global_instances

    def _detect_shared_state(self) -> List[str]:
        """Detect shared state in UserExecutionEngine"""
        shared_state_violations = []

        try:
            # Check class attributes for mutable shared state
            class_attributes = [attr for attr in dir(UserExecutionEngine)
                              if not attr.startswith('__')]

            for attr_name in class_attributes:
                try:
                    attr_value = getattr(UserExecutionEngine, attr_name)

                    # Check for mutable shared state
                    if isinstance(attr_value, (dict, list, set)):
                        if attr_value:  # Non-empty mutable objects
                            shared_state_violations.append(
                                f"Mutable shared state in class attribute: {attr_name} = {attr_value}"
                            )
                    elif hasattr(attr_value, '__dict__') and not callable(attr_value):
                        # Object with potential state
                        shared_state_violations.append(
                            f"Shared object state in class attribute: {attr_name}"
                        )

                except Exception:
                    continue

            # Test for shared state between instances
            try:
                mock_deps = (Mock(), Mock(), Mock())
                instance1 = UserExecutionEngine(*mock_deps)
                instance2 = UserExecutionEngine(*mock_deps)

                # Look for shared attributes
                for attr in dir(instance1):
                    if not attr.startswith('__') and hasattr(instance2, attr):
                        try:
                            val1 = getattr(instance1, attr)
                            val2 = getattr(instance2, attr)

                            # Check if they share the same mutable object
                            if isinstance(val1, (dict, list, set)) and val1 is val2:
                                shared_state_violations.append(
                                    f"Instances share mutable state: {attr}"
                                )

                        except Exception:
                            continue

            except Exception as e:
                shared_state_violations.append(f"Error testing shared state between instances: {e}")

        except Exception as e:
            shared_state_violations.append(f"Error detecting shared state: {e}")

        return shared_state_violations

    def _scan_for_factory_usage(self) -> List[Tuple[str, str]]:
        """Scan for factory pattern usage"""
        factory_usage = []

        # Patterns that indicate factory usage
        factory_patterns = [
            r'get_execution_engine_factory',
            r'create_user_execution_engine',
            r'ExecutionEngineFactory.*create',
            r'agent_factory.*create',
        ]

        for py_file in self._get_execution_engine_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in factory_patterns:
                    if re.search(pattern, content, re.MULTILINE):
                        factory_usage.append((str(py_file), pattern))

            except (UnicodeDecodeError, PermissionError):
                continue

        return factory_usage

    def _scan_for_direct_instantiation(self) -> List[Tuple[str, str]]:
        """Scan for direct UserExecutionEngine instantiation"""
        direct_instantiation = []

        # Pattern for direct instantiation
        direct_pattern = r'UserExecutionEngine\(\s*\)'

        for py_file in self._get_execution_engine_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                matches = re.findall(direct_pattern, content, re.MULTILINE)
                if matches:
                    direct_instantiation.append((str(py_file), f"Found {len(matches)} direct instantiations"))

            except (UnicodeDecodeError, PermissionError):
                continue

        return direct_instantiation

    def _get_execution_engine_files(self) -> List[Path]:
        """Get files related to UserExecutionEngine"""
        execution_engine_files = []

        # Focus on execution engine related directories
        search_paths = [
            self.project_root / 'netra_backend' / 'app' / 'agents' / 'supervisor',
            self.project_root / 'netra_backend' / 'app' / 'services',
            self.project_root / 'netra_backend' / 'app' / 'core',
        ]

        # File patterns related to execution engines
        file_patterns = [
            '*execution*engine*.py',
            '*user_execution*.py',
            '*agent_factory*.py',
            '*singleton*.py',
        ]

        for search_path in search_paths:
            if search_path.exists():
                for pattern in file_patterns:
                    try:
                        execution_engine_files.extend(list(search_path.rglob(pattern)))
                    except (OSError, PermissionError):
                        continue

        # Remove duplicates and sort
        unique_files = list(set(execution_engine_files))
        return sorted(unique_files)


@pytest.mark.unit
class TestSingletonViolationMetrics(unittest.TestCase):
    """Test class to measure singleton violation elimination metrics"""

    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent

    def test_6_singleton_violation_count_measurement(self):
        """
        Test 6: Measure current singleton violation count

        EXPECTED TO FAIL: Should measure the 8 remaining violations from Issue #1186
        """
        print("\n📊 SINGLETON METRICS TEST 6: Measuring singleton violation count...")

        violation_count = self._count_singleton_violations()
        target_violations = 0  # Target is zero violations

        # This test should FAIL to measure current violations
        self.assertEqual(
            violation_count,
            target_violations,
            f"❌ EXPECTED FAILURE: Found {violation_count} singleton violations. "
            f"Issue #1186 Phase 4 identified 8 remaining singleton violations requiring elimination. "
            f"Target: {target_violations} violations (complete singleton elimination)."
        )

    def test_7_user_isolation_compliance_validation(self):
        """
        Test 7: Validate user isolation compliance metrics

        EXPECTED BEHAVIOR: Should validate complete user isolation
        """
        print("\n📊 SINGLETON METRICS TEST 7: Validating user isolation compliance...")

        isolation_metrics = self._measure_user_isolation_compliance()

        # Expected metrics for complete user isolation
        expected_metrics = {
            'instance_isolation': True,  # Instances should be isolated
            'no_shared_state': True,  # No shared state between instances
            'factory_compliance': True,  # Factory patterns enforced
            'no_global_instances': True,  # No global instances
        }

        for metric, expected_value in expected_metrics.items():
            actual_value = isolation_metrics.get(metric, False)
            self.assertEqual(
                actual_value,
                expected_value,
                f"❌ USER ISOLATION FAILURE: {metric} = {actual_value}, expected {expected_value}. "
                f"Issue #1186 Phase 4 requires complete user isolation for enterprise security."
            )

    def _count_singleton_violations(self) -> int:
        """Count current singleton violations"""
        violation_count = 0

        # Create test instance to access methods
        test_instance = TestSingletonViolationElimination()
        test_instance.setUp()

        try:
            # Count singleton patterns
            singleton_patterns = test_instance._scan_for_singleton_patterns()
            violation_count += len(singleton_patterns)

            # Count global instances
            global_instances = test_instance._scan_for_global_instances()
            violation_count += len(global_instances)

            # Count direct instantiation patterns
            direct_instantiation = test_instance._scan_for_direct_instantiation()
            violation_count += len(direct_instantiation)

            # Count shared state violations
            shared_state_violations = test_instance._detect_shared_state()
            violation_count += len(shared_state_violations)

        except Exception as e:
            print(f"Warning: Error counting singleton violations: {e}")
            violation_count = -1  # Indicate measurement error

        return violation_count

    def _measure_user_isolation_compliance(self) -> Dict[str, bool]:
        """Measure user isolation compliance"""
        compliance_metrics = {}

        test_instance = TestSingletonViolationElimination()
        test_instance.setUp()

        try:
            # Test instance isolation
            isolation_violations = test_instance._test_multi_instance_isolation()
            compliance_metrics['instance_isolation'] = len(isolation_violations) == 0

            # Test shared state elimination
            shared_state_violations = test_instance._detect_shared_state()
            compliance_metrics['no_shared_state'] = len(shared_state_violations) == 0

            # Test factory compliance
            factory_violations = test_instance._validate_factory_compliance()
            compliance_metrics['factory_compliance'] = len(factory_violations) == 0

            # Test global instance elimination
            global_instances = test_instance._scan_for_global_instances()
            compliance_metrics['no_global_instances'] = len(global_instances) == 0

        except Exception as e:
            print(f"Warning: Error measuring user isolation compliance: {e}")
            compliance_metrics = {key: False for key in [
                'instance_isolation', 'no_shared_state', 'factory_compliance', 'no_global_instances'
            ]}

        return compliance_metrics


if __name__ == '__main__':
    print("🚨 Issue #1186 Singleton Violation Elimination - Validation Tests")
    print("=" * 80)
    print("⚠️  WARNING: Some tests are DESIGNED TO FAIL to demonstrate remaining violations")
    print("📊 Expected: Test failures exposing 8 remaining singleton violations from Issue #1186")
    print("🎯 Goal: Complete elimination of singleton patterns for enterprise user isolation")
    print("🔒 Impact: Enables secure multi-tenant production deployment")
    print("=" * 80)

    unittest.main(verbosity=2)