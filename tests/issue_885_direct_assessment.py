"""
Direct Assessment of Issue #885 WebSocket SSOT Compliance

This script directly assesses the current state of WebSocket SSOT compliance
to validate the claims in Issue #885.
"""

def assess_websocket_ssot_compliance():
    """Assess current WebSocket SSOT compliance."""
    print("="*80)
    print("ISSUE #885 WEBSOCKET SSOT COMPLIANCE ASSESSMENT")
    print("="*80)

    findings = []
    implementations = []
    import_successes = []
    import_failures = []

    # Test WebSocket manager implementations
    test_imports = [
        ("netra_backend.app.websocket_core.manager", "WebSocketManager"),
        ("netra_backend.app.websocket_core.unified_manager", "_UnifiedWebSocketManagerImplementation"),
        ("netra_backend.app.websocket_core.canonical_import_patterns", "UnifiedWebSocketManager"),
        ("netra_backend.app.websocket_core.websocket_manager_factory", "WebSocketManagerFactory"),
        ("netra_backend.app.websocket_core.websocket_manager", "WebSocketManager")
    ]

    print("\n1. WEBSOCKET MANAGER IMPLEMENTATIONS")
    print("-" * 40)

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
                print(f"  ✓ FOUND: {module_path}.{class_name}")
                findings.append(f"Implementation found: {module_path}.{class_name}")
            else:
                import_failures.append(f"{module_path}.{class_name} - attribute not found")
                print(f"  ✗ MISSING: {module_path}.{class_name}")
        except ImportError as e:
            import_failures.append(f"{module_path}.{class_name} - {e}")
            print(f"  ✗ IMPORT ERROR: {module_path}.{class_name} - {e}")

    print(f"\nImplementations found: {len(implementations)}")

    # Test factory patterns
    print("\n2. FACTORY PATTERNS")
    print("-" * 40)

    factories = []
    factory_tests = [
        ("netra_backend.app.websocket_core.websocket_manager_factory", "WebSocketManagerFactory"),
        ("netra_backend.app.websocket_core.canonical_import_patterns", "get_websocket_manager"),
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
                print(f"  ✓ FOUND: {module_path}.{factory_name}")
                findings.append(f"Factory found: {module_path}.{factory_name}")
        except (ImportError, AttributeError):
            print(f"  ✗ MISSING: {module_path}.{factory_name}")

    print(f"\nFactory patterns found: {len(factories)}")

    # Test user isolation
    print("\n3. USER ISOLATION TEST")
    print("-" * 40)

    isolation_violations = 0
    try:
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

        user1_context = {"user_id": "test_user_1", "session_id": "session_1"}
        user2_context = {"user_id": "test_user_2", "session_id": "session_2"}

        manager1 = get_websocket_manager(user_context=user1_context)
        manager2 = get_websocket_manager(user_context=user2_context)

        print(f"  Manager 1 ID: {id(manager1)}")
        print(f"  Manager 2 ID: {id(manager2)}")

        # Test same instance
        if manager1 is manager2:
            print("  ❌ VIOLATION: Same instance returned for different users")
            isolation_violations += 1
            findings.append("User isolation violation: Same instance")
        else:
            print("  ✅ OK: Different instances for different users")

        # Test shared state
        if hasattr(manager1, '_connections') and hasattr(manager2, '_connections'):
            if manager1._connections is manager2._connections:
                print("  ❌ VIOLATION: Shared connection registry")
                isolation_violations += 1
                findings.append("User isolation violation: Shared connections")
            else:
                print("  ✅ OK: Separate connection registries")

        if hasattr(manager1, 'registry') and hasattr(manager2, 'registry'):
            if manager1.registry is manager2.registry:
                print("  ❌ VIOLATION: Shared registry")
                isolation_violations += 1
                findings.append("User isolation violation: Shared registry")
            else:
                print("  ✅ OK: Separate registries")

    except Exception as e:
        print(f"  ❌ ERROR: User isolation test failed - {e}")
        isolation_violations += 1
        findings.append(f"User isolation test error: {e}")

    # Calculate compliance
    print("\n4. COMPLIANCE CALCULATION")
    print("-" * 40)

    # Manager SSOT compliance
    if len(implementations) == 1:
        manager_compliance = 100.0
        print(f"  Manager SSOT: 100% (1 implementation)")
    elif len(implementations) > 1:
        manager_compliance = 0.0
        print(f"  Manager SSOT: 0% ({len(implementations)} implementations - VIOLATION)")
    else:
        manager_compliance = 0.0
        print(f"  Manager SSOT: 0% (no implementations found)")

    # Factory compliance (allow up to 2)
    if len(factories) <= 2:
        factory_compliance = 100.0
        print(f"  Factory Pattern: 100% ({len(factories)} factories)")
    else:
        factory_compliance = max(0, 100 - (len(factories) - 2) * 25)
        print(f"  Factory Pattern: {factory_compliance}% ({len(factories)} factories)")

    # User isolation compliance
    if isolation_violations == 0:
        isolation_compliance = 100.0
        print(f"  User Isolation: 100% (no violations)")
    else:
        isolation_compliance = 0.0
        print(f"  User Isolation: 0% ({isolation_violations} violations)")

    # Overall compliance
    overall_compliance = (manager_compliance + factory_compliance + isolation_compliance) / 3

    print("\n5. FINAL ASSESSMENT")
    print("-" * 40)
    print(f"Overall SSOT Compliance: {overall_compliance:.1f}%")

    if overall_compliance >= 90:
        assessment = "✅ EXCELLENT"
    elif overall_compliance >= 70:
        assessment = "⚠️  GOOD"
    elif overall_compliance >= 50:
        assessment = "❌ POOR"
    else:
        assessment = "❌ CRITICAL"

    print(f"Assessment: {assessment}")

    # Issue #885 validation
    print("\n6. ISSUE #885 VALIDATION")
    print("-" * 40)
    print(f"Issue #885 Claim: '0.0% SSOT compliance'")
    print(f"Actual Compliance: {overall_compliance:.1f}%")

    if overall_compliance <= 10:
        print("✅ ISSUE #885 CLAIM VALIDATED")
        issue_validated = True
    else:
        print("❌ ISSUE #885 CLAIM DISPUTED")
        issue_validated = False

    print("\n7. VIOLATIONS DETECTED")
    print("-" * 40)

    violations_detected = []

    if len(implementations) > 1:
        violations_detected.append(f"Multiple WebSocket implementations: {len(implementations)}")

    if len(factories) > 2:
        violations_detected.append(f"Too many factory patterns: {len(factories)}")

    if isolation_violations > 0:
        violations_detected.append(f"User isolation violations: {isolation_violations}")

    if violations_detected:
        print("VIOLATIONS FOUND:")
        for i, violation in enumerate(violations_detected, 1):
            print(f"  {i}. {violation}")
    else:
        print("NO VIOLATIONS FOUND")

    print("\n" + "="*80)

    return {
        'overall_compliance': overall_compliance,
        'manager_compliance': manager_compliance,
        'factory_compliance': factory_compliance,
        'isolation_compliance': isolation_compliance,
        'implementations_count': len(implementations),
        'factories_count': len(factories),
        'isolation_violations': isolation_violations,
        'violations_detected': violations_detected,
        'issue_885_validated': issue_validated,
        'assessment': assessment
    }


if __name__ == "__main__":
    results = assess_websocket_ssot_compliance()

    # Summary for Issue #885
    print(f"\nSUMMARY FOR ISSUE #885:")
    print(f"- Actual SSOT Compliance: {results['overall_compliance']:.1f}%")
    print(f"- Issue #885 Claim Valid: {results['issue_885_validated']}")
    print(f"- Assessment: {results['assessment']}")
    print(f"- Violations: {len(results['violations_detected'])}")