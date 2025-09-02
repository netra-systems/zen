#!/usr/bin/env python3
"""
Simple Infrastructure Test Validation

Quick test to validate that infrastructure fixes are working without complex dependencies.
"""

import sys
import time
import traceback
from pathlib import Path

def test_imports():
    """Test that all infrastructure modules can be imported."""
    print("Testing infrastructure imports...")
    
    try:
        # Test TestContext imports
        from test_framework.test_context import (
            TestContext,
            TestUserContext, 
            WebSocketEventCapture,
            create_test_context
        )
        print("[OK] TestContext imports successful")
        
        # Test conftest imports  
        from test_framework.conftest_real_services import (
            real_services_function,
            real_services_session,
            real_services
        )
        print("[OK] Real services fixture imports successful")
        
        # Test environment isolation
        from test_framework.environment_isolation import (
            get_test_env_manager,
            ensure_test_isolation
        )
        print("[OK] Environment isolation imports successful")
        
        # Test shared environment
        from shared.isolated_environment import get_env
        print("[OK] Shared environment imports successful")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Import error: {e}")
        traceback.print_exc()
        return False


def test_test_context_creation():
    """Test TestContext creation and basic functionality."""
    print("\nTesting TestContext creation...")
    
    try:
        from test_framework.test_context import create_test_context
        
        # Create test context
        context = create_test_context()
        print("[OK] TestContext created successfully")
        
        # Test user context
        assert context.user_context is not None
        assert context.user_context.user_id is not None
        print("[OK] TestUserContext validated")
        
        # Test event capture
        test_event = {
            "type": "test_event",
            "data": "test_data"
        }
        context.event_capture.capture_event(test_event)
        
        assert len(context.event_capture.events) == 1
        assert "test_event" in context.event_capture.event_types
        print("[OK] Event capture working")
        
        # Test performance metrics
        metrics = context.get_performance_metrics()
        assert "duration_seconds" in metrics
        assert "total_events_captured" in metrics
        print("[OK] Performance metrics working")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] TestContext error: {e}")
        traceback.print_exc()
        return False


def test_user_context_isolation():
    """Test user context isolation."""
    print("\nTesting user context isolation...")
    
    try:
        from test_framework.test_context import create_isolated_test_contexts
        
        # Create multiple contexts
        contexts = create_isolated_test_contexts(count=3)
        print("[OK] Multiple contexts created")
        
        # Test isolation
        user_ids = [ctx.user_context.user_id for ctx in contexts]
        assert len(set(user_ids)) == 3, "User IDs should be unique"
        print("[OK] User context isolation validated")
        
        # Test event isolation
        for i, context in enumerate(contexts):
            context.event_capture.capture_event({
                "type": f"isolated_event_{i}",
                "user_id": context.user_context.user_id
            })
        
        # Verify each context has only its events
        for i, context in enumerate(contexts):
            assert len(context.event_capture.events) == 1
            assert f"isolated_event_{i}" in context.event_capture.event_types
        
        print("[OK] Event isolation validated")
        return True
        
    except Exception as e:
        print(f"[ERROR] Isolation error: {e}")
        traceback.print_exc()
        return False


def test_websocket_event_validation():
    """Test WebSocket event validation."""
    print("\nTesting WebSocket event validation...")
    
    try:
        from test_framework.test_context import create_test_context
        
        context = create_test_context()
        
        # Required WebSocket events
        required_events = {
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        # Capture all required events
        for event_type in required_events:
            context.event_capture.capture_event({
                "type": event_type,
                "timestamp": time.time()
            })
        
        # Validate events
        validation = context.validate_agent_events(required_events)
        assert validation["valid"] == True
        assert len(validation["missing_events"]) == 0
        print("[OK] WebSocket event validation working")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] WebSocket validation error: {e}")
        traceback.print_exc()
        return False


def test_environment_access():
    """Test environment access."""
    print("\nTesting environment access...")
    
    try:
        from shared.isolated_environment import get_env
        from test_framework.environment_isolation import get_test_env_manager
        
        # Test environment manager
        env_manager = get_test_env_manager()
        assert env_manager is not None
        print("[OK] Environment manager accessible")
        
        # Test environment access
        env = get_env()
        assert env is not None
        print("[OK] Environment access working")
        
        # Test setting and getting values
        env.set("TEST_KEY", "test_value", source="infrastructure_test")
        value = env.get("TEST_KEY")
        assert value == "test_value"
        print("[OK] Environment value storage working")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Environment error: {e}")
        traceback.print_exc()
        return False


def test_fixture_scope_simulation():
    """Test fixture scope compatibility simulation."""
    print("\nTesting fixture scope compatibility...")
    
    try:
        from test_framework.test_context import create_test_context
        
        # Test that we can create multiple test contexts 
        # (simulating multiple function-scoped fixtures)
        contexts = []
        for i in range(3):
            context = create_test_context(user_id=f"fixture_test_user_{i}")
            contexts.append(context)
        
        print("[OK] Multiple fixture-scoped contexts created")
        
        # Test they don't interfere with each other
        for i, context in enumerate(contexts):
            context.event_capture.capture_event({
                "type": f"fixture_scope_test_{i}",
                "user_id": context.user_context.user_id
            })
        
        # Verify isolation (like fixtures should be)
        for i, context in enumerate(contexts):
            assert len(context.event_capture.events) == 1
            assert f"fixture_scope_test_{i}" in context.event_capture.event_types
        
        print("[OK] Fixture scope simulation successful")
        return True
        
    except Exception as e:
        print(f"[ERROR] Fixture scope error: {e}")
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all infrastructure validation tests."""
    print("=" * 60)
    print("INFRASTRUCTURE FIXES VALIDATION")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_test_context_creation,
        test_user_context_isolation,
        test_websocket_event_validation,
        test_environment_access,
        test_fixture_scope_simulation
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[ERROR] Test {test_func.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("[OK] ALL INFRASTRUCTURE FIXES VALIDATED SUCCESSFULLY!")
        return True
    else:
        print("[ERROR] Some infrastructure issues detected")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)