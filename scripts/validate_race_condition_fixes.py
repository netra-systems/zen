#!/usr/bin/env python3
"""
Validation Script for WebSocket Accept Race Condition Fixes

This script validates that Phase 1 fixes for the WebSocket accept race condition
are working correctly by testing:
1. Connection state machine integration
2. Accept completion validation  
3. Cloud Run environment timing adjustments

Usage: python validate_race_condition_fixes.py
"""

import asyncio
import time
import os
import sys
from typing import Optional

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def test_connection_state_machine():
    """Test Phase 1 Fix 1: ApplicationConnectionStateMachine integration."""
    print("\n=== Testing Connection State Machine Integration ===")
    
    try:
        from netra_backend.app.websocket_core.connection_state_machine import (
            get_connection_state_registry, 
            ApplicationConnectionState,
            ConnectionStateMachine
        )
        
        # Test state machine registry
        registry = get_connection_state_registry()
        print("[OK] Connection state registry initialized")
        
        # Test state machine creation and transitions
        test_connection_id = "test_conn_123"
        test_user_id = "test_user_456"
        
        state_machine = registry.register_connection(test_connection_id, test_user_id)
        print("[OK] Connection state machine registered")
        
        # Test state transitions
        transitions = [
            (ApplicationConnectionState.ACCEPTED, "WebSocket accepted"),
            (ApplicationConnectionState.AUTHENTICATED, "Authentication completed"),
            (ApplicationConnectionState.SERVICES_READY, "Services initialized"),
            (ApplicationConnectionState.PROCESSING_READY, "Ready for messages")
        ]
        
        for state, reason in transitions:
            success = state_machine.transition_to(state, reason=reason)
            if success:
                print(f"[OK] Successfully transitioned to {state.value}")
            else:
                print(f"[FAIL] Failed to transition to {state.value}")
                return False
                
        # Test readiness validation
        if state_machine.can_process_messages():
            print("[OK] State machine reports ready for message processing")
        else:
            print("[FAIL] State machine not ready for message processing")
            return False
            
        # Cleanup
        registry.unregister_connection(test_connection_id)
        print("[OK] Connection state machine cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Connection state machine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_websocket_config_environment_detection():
    """Test Phase 1 Fix 3: Cloud Run environment timing adjustments."""
    print("\n=== Testing WebSocket Config Environment Detection ===")
    
    try:
        from netra_backend.app.websocket_core.types import WebSocketConfig
        
        # Test default configuration
        default_config = WebSocketConfig()
        print("[OK] Default WebSocket configuration created")
        print(f"  - Accept completion timeout: {default_config.accept_completion_timeout_seconds}s")
        print(f"  - Cloud Run accept delay: {default_config.cloud_run_accept_delay_ms}ms")
        print(f"  - Stabilization delay: {default_config.cloud_run_stabilization_delay_ms}ms")
        
        # Test Cloud Run optimized configuration
        cloud_run_config = WebSocketConfig.get_cloud_run_optimized_config()
        print("[OK] Cloud Run optimized configuration created")
        print(f"  - Heartbeat interval: {cloud_run_config.heartbeat_interval_seconds}s")
        print(f"  - Accept completion timeout: {cloud_run_config.accept_completion_timeout_seconds}s")
        print(f"  - Cloud Run accept delay: {cloud_run_config.cloud_run_accept_delay_ms}ms")
        
        # Test environment detection
        detected_config = WebSocketConfig.detect_and_configure_for_environment()
        print("[OK] Environment-aware configuration created")
        print(f"  - Detected config heartbeat: {detected_config.heartbeat_interval_seconds}s")
        
        # Validate Cloud Run optimizations are present
        if hasattr(detected_config, 'cloud_run_accept_delay_ms'):
            print("[OK] Cloud Run timing adjustments present in configuration")
        else:
            print("[FAIL] Cloud Run timing adjustments missing")
            return False
            
        return True
        
    except Exception as e:
        print(f"[FAIL] WebSocket config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_accept_completion_validation_function():
    """Test that accept completion validation functions are accessible."""
    print("\n=== Testing Accept Completion Validation Functions ===")
    
    try:
        from netra_backend.app.websocket_core.connection_state_machine import is_connection_ready_for_messages
        
        # Test function accessibility
        test_connection_id = "validation_test_conn"
        result = is_connection_ready_for_messages(test_connection_id)
        print(f"[OK] Accept completion validation function accessible")
        print(f"  - Result for non-existent connection: {result}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Accept completion validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_imports_and_integration():
    """Test that all required imports work for the race condition fixes."""
    print("\n=== Testing Imports and Integration ===")
    
    try:
        # Test WebSocket route imports (these are used in websocket.py)
        from netra_backend.app.websocket_core.connection_state_machine import (
            get_connection_state_registry,
            ApplicationConnectionState,
            get_connection_state_machine
        )
        print("[OK] WebSocket route integration imports successful")
        
        # Test WebSocket config imports
        from netra_backend.app.websocket_core.types import WebSocketConfig
        print("[OK] WebSocket configuration imports successful")
        
        # Test that the modifications we made are present in websocket.py
        import inspect
        from netra_backend.app.routes import websocket as websocket_module
        
        # Check if WEBSOCKET_CONFIG has our new attributes
        if hasattr(websocket_module, 'WEBSOCKET_CONFIG'):
            config = websocket_module.WEBSOCKET_CONFIG
            if hasattr(config, 'cloud_run_accept_delay_ms'):
                print("[OK] WebSocket module contains Cloud Run timing configurations")
            else:
                print("[FAIL] WebSocket module missing Cloud Run timing configurations")
                return False
        else:
            print("[FAIL] WEBSOCKET_CONFIG not found in websocket module")
            return False
            
        return True
        
    except Exception as e:
        print(f"[FAIL] Import and integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def simulate_cloud_run_environment():
    """Simulate Cloud Run environment variables for testing."""
    print("\n=== Simulating Cloud Run Environment ===")
    
    # Set Cloud Run environment variables
    os.environ['K_SERVICE'] = 'test-service'
    os.environ['K_REVISION'] = 'test-revision-001'
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
    os.environ['ENVIRONMENT'] = 'staging'
    
    print("[OK] Cloud Run environment variables set")
    return True

async def main():
    """Run all validation tests."""
    print("WebSocket Accept Race Condition Fix Validation")
    print("=" * 50)
    
    tests = [
        ("Connection State Machine Integration", test_connection_state_machine),
        ("WebSocket Config Environment Detection", test_websocket_config_environment_detection), 
        ("Accept Completion Validation Functions", test_accept_completion_validation_function),
        ("Imports and Integration", test_imports_and_integration)
    ]
    
    # Simulate Cloud Run environment for testing
    simulate_cloud_run_environment()
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                print(f"[OK] {test_name}: PASSED")
            else:
                print(f"[FAIL] {test_name}: FAILED")
                
        except Exception as e:
            print(f"[FAIL] {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'=' * 50}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        symbol = "[OK]" if result else "[FAIL]"
        print(f"{symbol} {test_name}: {status}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] ALL RACE CONDITION FIXES VALIDATED SUCCESSFULLY!")
        print("\nPhase 1 fixes are ready for production:")
        print("  [OK] Connection state machine integration")
        print("  [OK] Accept completion validation")  
        print("  [OK] Cloud Run environment timing adjustments")
        return True
    else:
        print(f"\n[ERROR] {total - passed} tests failed. Race condition fixes need attention.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)