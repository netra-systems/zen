#!/usr/bin/env python
"""
Simple runner for the comprehensive WebSocket validation test suite.
This bypasses pytest issues and runs the tests directly.
"""

import asyncio
import sys
import os
import time
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Import our comprehensive test suite
from tests.mission_critical.test_websocket_comprehensive_validation import (
    TestUltraComprehensiveWebSocketValidation,
    TestComprehensiveRegressionPrevention,
    WebSocketTestHarness,
    ComprehensiveEventValidator,
    UltraReliableMockWebSocketManager
)

async def run_comprehensive_tests():
    """Run the comprehensive WebSocket validation tests."""
    print("=" * 80)
    print("ULTRA-COMPREHENSIVE WEBSOCKET VALIDATION TEST SUITE")
    print("=" * 80)
    print("This test suite validates ALL critical WebSocket events are sent during agent execution.")
    print("Business Value: $500K+ ARR - Core chat functionality")
    print("")
    
    # Test results tracking
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    test_results = []
    
    # Create test instance
    test_instance = TestUltraComprehensiveWebSocketValidation()
    regression_test_instance = TestComprehensiveRegressionPrevention()
    
    # List of tests to run
    test_methods = [
        ("Component Isolation", test_instance.test_ultra_comprehensive_component_isolation),
        ("Single Agent Flow", test_instance.test_ultra_comprehensive_single_agent_flow),
        ("Tool Dispatcher Integration", test_instance.test_ultra_comprehensive_tool_dispatcher_integration),
        ("Error Recovery", test_instance.test_ultra_comprehensive_error_recovery),
        ("Event Ordering", test_instance.test_ultra_comprehensive_event_ordering_validation),
        ("Regression Prevention", test_instance.test_ultra_comprehensive_regression_prevention),
        ("Function Existence", regression_test_instance.test_enhance_tool_dispatcher_function_exists_and_works),
        ("Bridge Integration", regression_test_instance.test_websocket_bridge_integration_never_breaks),
        ("Critical Events", regression_test_instance.test_all_critical_events_always_sent)
    ]
    
    print(f"Running {len(test_methods)} comprehensive tests...")
    print("")
    
    for test_name, test_method in test_methods:
        total_tests += 1
        print(f"Running: {test_name}")
        
        try:
            # Manually setup test environment (without pytest fixtures)
            test_instance.test_harness = WebSocketTestHarness()
            test_instance.mock_ws_manager = test_instance.test_harness.mock_ws_manager
            test_instance.validator = test_instance.test_harness.validator
            test_instance._monitoring_active = True
            test_instance._test_start_time = time.time()
            
            # Setup regression testing
            regression_test_instance.mock_ws_manager = UltraReliableMockWebSocketManager()
            
            # Run the test
            await test_method()
            
            # Test passed
            passed_tests += 1
            result = "PASSED"
            test_results.append((test_name, True, None))
            print(f"   {result}")
            
        except Exception as e:
            # Test failed
            failed_tests += 1
            result = f"FAILED: {str(e)[:100]}..."
            test_results.append((test_name, False, e))
            print(f"   {result}")
            if "--verbose" in sys.argv:
                traceback.print_exc()
        
        print("")
    
    # Final results
    print("=" * 80)
    print("COMPREHENSIVE TEST RESULTS")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print("")
    
    # Detailed results
    print("DETAILED RESULTS:")
    for test_name, passed, error in test_results:
        status = "PASS" if passed else "FAIL"
        print(f"  {status} {test_name}")
        if not passed and error and "--verbose" in sys.argv:
            print(f"     Error: {str(error)}")
    
    print("")
    
    # Validate business requirements
    critical_tests = [
        "Component Isolation",
        "Single Agent Flow", 
        "Tool Dispatcher Integration",
        "Critical Events"
    ]
    
    critical_passed = sum(1 for name, passed, _ in test_results 
                         if name in critical_tests and passed)
    
    print("BUSINESS VALIDATION:")
    if critical_passed == len(critical_tests):
        print("ALL CRITICAL BUSINESS REQUIREMENTS VALIDATED")
        print("   - WebSocket events enable substantive chat interactions")
        print("   - Real-time reasoning visibility working")
        print("   - Tool usage transparency operational") 
        print("   - User completion notifications functional")
        print("   - Chat value delivery system: OPERATIONAL")
    else:
        print("CRITICAL BUSINESS REQUIREMENTS FAILED")
        print(f"   Only {critical_passed}/{len(critical_tests)} critical tests passed")
        print("   CHAT FUNCTIONALITY AT RISK")
        return False
    
    print("")
    print("=" * 80)
    
    return failed_tests == 0

def run_basic_validation():
    """Run basic validation to ensure the test framework works."""
    print("Running basic validation...")
    
    try:
        # Test mock WebSocket manager
        from tests.mission_critical.test_websocket_comprehensive_validation import UltraReliableMockWebSocketManager
        mock_ws = UltraReliableMockWebSocketManager()
        print("Mock WebSocket Manager: OK")
        
        # Test event validator
        validator = ComprehensiveEventValidator()
        validator.record_event({'type': 'agent_started'}, 'test')
        print("Event Validator: OK")
        
        # Test harness
        harness = WebSocketTestHarness()
        print("Test Harness: OK")
        
        print("Basic validation passed - framework operational")
        return True
        
    except Exception as e:
        print(f"Basic validation failed: {e}")
        traceback.print_exc()
        return False

async def main():
    """Main entry point."""
    print("Starting Comprehensive WebSocket Validation")
    print("")
    
    # Run basic validation first
    if not run_basic_validation():
        print("Basic validation failed - cannot proceed")
        return False
    
    print("")
    
    # Run comprehensive tests
    success = await run_comprehensive_tests()
    
    if success:
        print("ALL TESTS PASSED - WebSocket notifications fully validated")
        print("Business Value: Chat functionality preserved and operational")
    else:
        print("TESTS FAILED - WebSocket notification issues detected")
        print("Business Impact: Chat functionality may be compromised")
    
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest suite crashed: {e}")
        traceback.print_exc()
        sys.exit(1)