#!/usr/bin/env python3
"""
Validation script for Issue #1176 Phase 1 implementation.

This script validates that the standardized WebSocket Manager factory interface
has been properly implemented and prevents coordination gaps.
"""

import sys
import traceback
from datetime import datetime


def validate_standardized_factory_import():
    """Validate that standardized factory can be imported."""
    try:
        from netra_backend.app.websocket_core.standardized_factory_interface import (
            StandardizedWebSocketManagerFactory,
            WebSocketManagerFactoryValidator,
            get_standardized_websocket_manager_factory
        )
        print("✅ Standardized factory interface imports successful")
        return True
    except Exception as e:
        print(f"❌ Standardized factory import failed: {e}")
        return False


def validate_factory_creation():
    """Validate that standardized factory can be created."""
    try:
        from netra_backend.app.websocket_core.standardized_factory_interface import (
            get_standardized_websocket_manager_factory
        )

        factory = get_standardized_websocket_manager_factory(require_user_context=True)

        # Check factory has required methods
        required_methods = ['create_manager', 'validate_manager_instance', 'supports_user_isolation']
        for method in required_methods:
            if not hasattr(factory, method):
                print(f"❌ Factory missing required method: {method}")
                return False
            if not callable(getattr(factory, method)):
                print(f"❌ Factory method not callable: {method}")
                return False

        print("✅ Standardized factory creation and interface validation successful")
        return True
    except Exception as e:
        print(f"❌ Factory creation failed: {e}")
        traceback.print_exc()
        return False


def validate_factory_compliance_checking():
    """Validate that factory compliance checking works."""
    try:
        from netra_backend.app.websocket_core.standardized_factory_interface import (
            get_standardized_websocket_manager_factory,
            WebSocketManagerFactoryValidator
        )

        factory = get_standardized_websocket_manager_factory(require_user_context=True)

        # Validate compliance
        validation_result = WebSocketManagerFactoryValidator.validate_factory_compliance(factory)

        if not validation_result.get('compliant', False):
            print(f"❌ Factory compliance validation failed: {validation_result}")
            return False

        print("✅ Factory compliance validation successful")
        return True
    except Exception as e:
        print(f"❌ Factory compliance checking failed: {e}")
        traceback.print_exc()
        return False


def validate_agent_bridge_integration():
    """Validate that AgentWebSocketBridge integrates with standardized factory."""
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

        # Create bridge
        bridge = AgentWebSocketBridge()

        # Check if _initialize_websocket_manager exists and is callable
        if not hasattr(bridge, '_initialize_websocket_manager'):
            print("❌ AgentWebSocketBridge missing _initialize_websocket_manager method")
            return False

        if not callable(getattr(bridge, '_initialize_websocket_manager')):
            print("❌ AgentWebSocketBridge _initialize_websocket_manager not callable")
            return False

        print("✅ AgentWebSocketBridge integration validation successful")
        return True
    except Exception as e:
        print(f"❌ AgentWebSocketBridge integration validation failed: {e}")
        traceback.print_exc()
        return False


def validate_protocols_integration():
    """Validate that WebSocket protocols work with standardized interface."""
    try:
        from netra_backend.app.websocket_core.protocols import WebSocketProtocol
        from netra_backend.app.websocket_core.standardized_factory_interface import (
            WebSocketManagerFactoryProtocol
        )

        # Check protocols exist
        if WebSocketProtocol is None:
            print("❌ WebSocketProtocol not available")
            return False

        if WebSocketManagerFactoryProtocol is None:
            print("❌ WebSocketManagerFactoryProtocol not available")
            return False

        print("✅ Protocol integration validation successful")
        return True
    except Exception as e:
        print(f"❌ Protocol integration validation failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all validation tests for Issue #1176 Phase 1."""
    print("🚀 Starting Issue #1176 Phase 1 validation...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    validations = [
        ("Standardized Factory Import", validate_standardized_factory_import),
        ("Factory Creation", validate_factory_creation),
        ("Factory Compliance Checking", validate_factory_compliance_checking),
        ("AgentWebSocketBridge Integration", validate_agent_bridge_integration),
        ("Protocol Integration", validate_protocols_integration),
    ]

    results = []
    for name, validation_func in validations:
        print(f"\n📋 Testing: {name}")
        try:
            success = validation_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ {name} failed with exception: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("📊 VALIDATION RESULTS:")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
        if success:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"📈 Summary: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All Issue #1176 Phase 1 validations PASSED!")
        print("✅ Standardized WebSocket Manager factory interface successfully implemented")
        print("✅ Coordination gaps prevented through interface validation")
        return True
    else:
        print("⚠️  Some Issue #1176 Phase 1 validations FAILED")
        print("❌ Review failed validations and fix implementation issues")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)