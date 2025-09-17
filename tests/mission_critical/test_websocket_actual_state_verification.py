"""
WebSocket SSOT Actual State Verification for Issue #885

This test verifies the actual current state of WebSocket SSOT compliance
to determine if Issue #885 claims of 0.0% compliance are accurate.
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketActualState(SSotBaseTestCase):
    """Verify actual current state of WebSocket SSOT compliance."""

    def setUp(self):
        """Setup for tests."""
        super().setUp()
        self.findings = []

    def test_websocket_manager_current_state(self):
        """
        Verify current state of WebSocket manager implementations.
        """
        implementations = []
        import_successes = []
        import_failures = []

        # Test all known WebSocket manager import paths
        test_imports = [
            ("netra_backend.app.websocket_core.manager", "WebSocketManager"),
            ("netra_backend.app.websocket_core.unified_manager", "_UnifiedWebSocketManagerImplementation"),
            ("netra_backend.app.websocket_core.canonical_import_patterns", "UnifiedWebSocketManager"),
            ("netra_backend.app.websocket_core.websocket_manager_factory", "WebSocketManagerFactory"),
            ("netra_backend.app.websocket_core.websocket_manager", "WebSocketManager")
        ]

        for module_path, class_name in test_imports:
            try:
                module = __import__(module_path, fromlist=[class_name])
                if hasattr(module, class_name):
                    impl_class = getattr(module, class_name)
                    implementations.append({
                        'path': f"{module_path}.{class_name}",
                        'class': impl_class,
                        'type': type(impl_class).__name__
                    })
                    import_successes.append(f"{module_path}.{class_name}")
                    self.findings.append(f"FOUND: {module_path}.{class_name}")
                else:
                    import_failures.append(f"{module_path}.{class_name} - attribute not found")
            except ImportError as e:
                import_failures.append(f"{module_path}.{class_name} - {e}")

        print(f"\n=== WEBSOCKET MANAGER IMPLEMENTATIONS FOUND ===")
        print(f"Total implementations: {len(implementations)}")
        for impl in implementations:
            print(f"  ✓ {impl['path']} ({impl['type']})")

        print(f"\n=== IMPORT FAILURES ===")
        for failure in import_failures:
            print(f"  ✗ {failure}")

        # Determine SSOT compliance
        if len(implementations) == 1:
            print(f"\n✅ SSOT COMPLIANT: Only 1 implementation found")
            ssot_compliant = True
        elif len(implementations) > 1:
            print(f"\n❌ SSOT VIOLATION: {len(implementations)} implementations found")
            ssot_compliant = False
        else:
            print(f"\n⚠️  NO IMPLEMENTATIONS: This suggests import issues")
            ssot_compliant = False

        return {
            'implementations': implementations,
            'import_successes': import_successes,
            'import_failures': import_failures,
            'ssot_compliant': ssot_compliant,
            'compliance_percentage': 100.0 if ssot_compliant else 0.0
        }

    def test_factory_pattern_current_state(self):
        """
        Verify current state of factory patterns.
        """
        factories = []

        factory_tests = [
            ("netra_backend.app.websocket_core.websocket_manager_factory", "WebSocketManagerFactory"),
            ("netra_backend.app.websocket_core.canonical_import_patterns", "get_websocket_manager"),
            ("netra_backend.app.websocket_core.supervisor_factory", "SupervisorFactory"),
        ]

        for module_path, factory_name in factory_tests:
            try:
                module = __import__(module_path, fromlist=[factory_name])
                if hasattr(module, factory_name):
                    factory = getattr(module, factory_name)
                    factories.append({
                        'path': f"{module_path}.{factory_name}",
                        'factory': factory,
                        'callable': callable(factory)
                    })
                    self.findings.append(f"FACTORY FOUND: {module_path}.{factory_name}")
            except (ImportError, AttributeError):
                pass

        print(f"\n=== FACTORY PATTERNS FOUND ===")
        print(f"Total factories: {len(factories)}")
        for factory in factories:
            print(f"  ✓ {factory['path']} (callable: {factory['callable']})")

        return {
            'factories': factories,
            'factory_count': len(factories)
        }

    def test_user_isolation_current_state(self):
        """
        Verify current state of user isolation.
        """
        isolation_test_results = []

        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

            # Test user isolation
            user1_context = {"user_id": "test_user_1", "session_id": "session_1"}
            user2_context = {"user_id": "test_user_2", "session_id": "session_2"}

            manager1 = get_websocket_manager(user_context=user1_context)
            manager2 = get_websocket_manager(user_context=user2_context)

            # Test results
            same_instance = manager1 is manager2
            same_class = manager1.__class__ is manager2.__class__

            isolation_test_results.append({
                'test': 'same_instance',
                'result': same_instance,
                'violation': same_instance
            })

            isolation_test_results.append({
                'test': 'same_class',
                'result': same_class,
                'violation': False  # Same class is OK, same instance is not
            })

            # Check internal state sharing
            shared_connections = False
            shared_registries = False

            if hasattr(manager1, '_connections') and hasattr(manager2, '_connections'):
                shared_connections = manager1._connections is manager2._connections

            if hasattr(manager1, 'registry') and hasattr(manager2, 'registry'):
                shared_registries = manager1.registry is manager2.registry

            isolation_test_results.append({
                'test': 'shared_connections',
                'result': shared_connections,
                'violation': shared_connections
            })

            isolation_test_results.append({
                'test': 'shared_registries',
                'result': shared_registries,
                'violation': shared_registries
            })

            print(f"\n=== USER ISOLATION TEST RESULTS ===")
            violations = 0
            for result in isolation_test_results:
                status = "❌ VIOLATION" if result['violation'] else "✅ OK"
                print(f"  {result['test']}: {result['result']} - {status}")
                if result['violation']:
                    violations += 1
                    self.findings.append(f"ISOLATION VIOLATION: {result['test']}")

            isolation_compliant = violations == 0
            print(f"\nUser Isolation: {'✅ COMPLIANT' if isolation_compliant else f'❌ {violations} VIOLATIONS'}")

            return {
                'isolation_results': isolation_test_results,
                'violations': violations,
                'isolation_compliant': isolation_compliant
            }

        except Exception as e:
            print(f"\n❌ USER ISOLATION TEST FAILED: {e}")
            self.findings.append(f"ISOLATION TEST ERROR: {e}")
            return {
                'isolation_results': [],
                'violations': 1,  # Failure to test is a violation
                'isolation_compliant': False
            }

    def test_overall_ssot_compliance_assessment(self):
        """
        Generate overall SSOT compliance assessment.
        """
        print(f"\n{'='*80}")
        print("WEBSOCKET SSOT COMPLIANCE ASSESSMENT - ISSUE #885")
        print(f"{'='*80}")

        # Run all tests
        manager_state = self.test_websocket_manager_current_state()
        factory_state = self.test_factory_pattern_current_state()
        isolation_state = self.test_user_isolation_current_state()

        # Calculate overall compliance
        compliance_factors = []

        # Manager implementation compliance
        if manager_state['ssot_compliant']:
            compliance_factors.append(('Manager SSOT', 100.0))
        else:
            compliance_factors.append(('Manager SSOT', 0.0))

        # Factory pattern compliance (multiple factories allowed, but should be minimal)
        factory_compliance = 100.0 if factory_state['factory_count'] <= 2 else max(0, 100 - (factory_state['factory_count'] - 2) * 25)
        compliance_factors.append(('Factory Patterns', factory_compliance))

        # User isolation compliance
        isolation_compliance = 100.0 if isolation_state['isolation_compliant'] else 0.0
        compliance_factors.append(('User Isolation', isolation_compliance))

        # Calculate weighted average
        overall_compliance = sum(score for _, score in compliance_factors) / len(compliance_factors)

        print(f"\n=== COMPLIANCE BREAKDOWN ===")
        for factor, score in compliance_factors:
            print(f"  {factor}: {score:.1f}%")

        print(f"\n=== OVERALL ASSESSMENT ===")
        print(f"Overall SSOT Compliance: {overall_compliance:.1f}%")

        if overall_compliance >= 90:
            assessment = "✅ EXCELLENT - High SSOT compliance"
        elif overall_compliance >= 70:
            assessment = "⚠️  GOOD - Some SSOT violations need attention"
        elif overall_compliance >= 50:
            assessment = "❌ POOR - Significant SSOT violations"
        else:
            assessment = "❌ CRITICAL - Major SSOT violations"

        print(f"Assessment: {assessment}")

        # Issue #885 validation
        issue_885_claim = "0.0% SSOT compliance"
        actual_compliance = overall_compliance

        print(f"\n=== ISSUE #885 VALIDATION ===")
        print(f"Issue #885 Claim: {issue_885_claim}")
        print(f"Actual Compliance: {actual_compliance:.1f}%")

        if actual_compliance <= 10:
            print("✅ ISSUE #885 CLAIM VALIDATED - Compliance is indeed near 0%")
            issue_validated = True
        else:
            print("❌ ISSUE #885 CLAIM DISPUTED - Compliance is higher than claimed")
            issue_validated = False

        print(f"{'='*80}")

        return {
            'overall_compliance': overall_compliance,
            'compliance_factors': compliance_factors,
            'assessment': assessment,
            'issue_885_validated': issue_validated,
            'manager_state': manager_state,
            'factory_state': factory_state,
            'isolation_state': isolation_state
        }

    def tearDown(self):
        """Report all findings."""
        if self.findings:
            print(f"\n=== DETAILED FINDINGS ===")
            for i, finding in enumerate(self.findings, 1):
                print(f"{i:2d}. {finding}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])