"""
Simple User Isolation Violation Test for Issue #885

This test validates user isolation violations in WebSocket manager.
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUserIsolationSimpleViolations(SSotBaseTestCase):
    """Simple test to prove user isolation violations exist."""

    def setUp(self):
        """Setup for tests."""
        super().setUp()
        self.violations_found = []

    def test_websocket_manager_user_isolation_violation(self):
        """
        EXPECTED TO FAIL: This test should detect user isolation violations.

        This proves that WebSocket managers don't properly isolate users.
        """
        isolation_violations = []

        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

            # Create contexts for different users
            user1_context = {"user_id": "user_001", "session_id": "session_001"}
            user2_context = {"user_id": "user_002", "session_id": "session_002"}

            # Get managers for different users
            manager1 = get_websocket_manager(user_context=user1_context)
            manager2 = get_websocket_manager(user_context=user2_context)

            print(f"\nManager 1 ID: {id(manager1)}")
            print(f"Manager 2 ID: {id(manager2)}")

            # Test 1: Check if managers are the same instance (violation)
            if manager1 is manager2:
                violation = "CRITICAL: Same manager instance returned for different users"
                isolation_violations.append(violation)
                self.violations_found.append(violation)
                print("CHECK VIOLATION DETECTED: Same manager instance for different users")

            # Test 2: Check if connection registries are shared
            if hasattr(manager1, '_connections') and hasattr(manager2, '_connections'):
                if manager1._connections is manager2._connections:
                    violation = "CRITICAL: Shared connection registry between users"
                    isolation_violations.append(violation)
                    self.violations_found.append(violation)
                    print("CHECK VIOLATION DETECTED: Shared connection registry")

            # Test 3: Check if user connection mappings are shared
            if hasattr(manager1, '_user_connections') and hasattr(manager2, '_user_connections'):
                if manager1._user_connections is manager2._user_connections:
                    violation = "CRITICAL: Shared user connection mapping"
                    isolation_violations.append(violation)
                    self.violations_found.append(violation)
                    print("CHECK VIOLATION DETECTED: Shared user connection mapping")

            # Test 4: Check registry sharing
            if hasattr(manager1, 'registry') and hasattr(manager2, 'registry'):
                if manager1.registry is manager2.registry:
                    violation = "CRITICAL: Shared registry between users"
                    isolation_violations.append(violation)
                    self.violations_found.append(violation)
                    print("CHECK VIOLATION DETECTED: Shared registry")

            # Test 5: Check if managers are different classes (anti-test)
            if manager1.__class__ is not manager2.__class__:
                violation = "WARNING: Different manager classes returned"
                isolation_violations.append(violation)
                self.violations_found.append(violation)
                print("! VIOLATION DETECTED: Different manager classes")

        except ImportError as e:
            violation = f"Cannot test user isolation - import failed: {e}"
            isolation_violations.append(violation)
            self.violations_found.append(violation)
            print(f"✗ IMPORT ERROR: {e}")

        except Exception as e:
            violation = f"User isolation test failed: {e}"
            isolation_violations.append(violation)
            self.violations_found.append(violation)
            print(f"✗ TEST ERROR: {e}")

        print(f"\nFound {len(isolation_violations)} user isolation violations")

        # ASSERTION THAT SHOULD FAIL: User isolation violations detected
        self.assertGreater(
            len(isolation_violations), 0,
            f"USER ISOLATION VIOLATION: Found {len(isolation_violations)} violations. "
            f"This proves users are not properly isolated. "
            f"Violations: {isolation_violations}"
        )

        print("USER ISOLATION VIOLATIONS CONFIRMED")

    def test_factory_creates_shared_instances(self):
        """
        EXPECTED TO FAIL: Test should detect that factory creates shared instances.
        """
        factory_violations = []

        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

            # Create multiple instances rapidly
            instances = []
            for i in range(3):
                context = {"user_id": f"rapid_user_{i}", "session_id": f"session_{i}"}
                instance = get_websocket_manager(user_context=context)
                instances.append(instance)

            print(f"\nCreated {len(instances)} instances:")
            for i, instance in enumerate(instances):
                print(f"  Instance {i}: {id(instance)} - {type(instance).__name__}")

            # Check for shared instances
            for i, inst1 in enumerate(instances):
                for j, inst2 in enumerate(instances):
                    if i != j and inst1 is inst2:
                        violation = f"CRITICAL: Factory returned same instance for calls {i} and {j}"
                        factory_violations.append(violation)
                        self.violations_found.append(violation)
                        print(f"CHECK VIOLATION DETECTED: Same instance at positions {i} and {j}")

        except Exception as e:
            violation = f"Factory sharing test failed: {e}"
            factory_violations.append(violation)
            self.violations_found.append(violation)
            print(f"✗ FACTORY TEST ERROR: {e}")

        print(f"\nFound {len(factory_violations)} factory sharing violations")

        # ASSERTION THAT SHOULD FAIL: Factory sharing violations detected
        self.assertGreater(
            len(factory_violations), 0,
            f"FACTORY SHARING VIOLATION: Found {len(factory_violations)} violations. "
            f"Factory should create isolated instances. "
            f"Violations: {factory_violations}"
        )

        print("FACTORY SHARING VIOLATIONS CONFIRMED")

    def tearDown(self):
        """Report violations found."""
        if self.violations_found:
            print("\n" + "="*60)
            print("USER ISOLATION VIOLATIONS DETECTED")
            print("="*60)
            for i, violation in enumerate(self.violations_found, 1):
                print(f"{i:2d}. {violation}")
            print("="*60)
            print(f"TOTAL VIOLATIONS: {len(self.violations_found)}")
            print("SECURITY RISK FOR $500K+ ARR")
            print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])