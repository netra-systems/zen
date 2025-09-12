#!/usr/bin/env python3

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
WebSocket Message Routing Golden Path Test Runner

This script provides a simple way to run the WebSocket message routing golden path test
to validate the current system state.

Expected Result: The test should INITIALLY FAIL to prove current system issues exist.

Usage:
    python tests/e2e/websocket_message_routing/run_golden_path_test.py
    
    Or use pytest directly:
    pytest tests/e2e/websocket_message_routing/test_websocket_message_to_agent_golden_path.py -v
"""

import asyncio
import logging
import sys
import traceback
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from test_websocket_message_to_agent_golden_path import TestWebSocketMessageToAgentGoldenPath
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_golden_path_test():
    """Run the WebSocket message routing golden path test."""
    print("[U+1F680] Starting WebSocket Message Routing Golden Path Test")
    print("=" * 80)
    print("Expected Result: Test should FAIL initially to prove system issues")
    print("=" * 80)
    
    test_instance = TestWebSocketMessageToAgentGoldenPath()
    
    try:
        # Setup test
        print("[U+1F527] Setting up test instance...")
        test_instance.setup_method()
        
        # Run the main golden path test
        print(" TARGET:  Running golden path test...")
        await test_instance.test_websocket_message_to_agent_complete_golden_path()
        
        # If we get here, the test passed unexpectedly
        print("=" * 80)
        print(" PASS:  UNEXPECTED: Golden Path Test PASSED")
        print("This suggests the WebSocket message routing system is working correctly!")
        print("The system may have been fixed since this test was created.")
        print("=" * 80)
        return True
        
    except AssertionError as e:
        print("=" * 80)
        print(" FAIL:  EXPECTED: Golden Path Test FAILED")
        print(f"Failure Details: {e}")
        print("")
        print("This failure PROVES the current system issues exist:")
        print("- Missing WebSocket events during agent execution")
        print("- Incomplete message routing to agent pipeline") 
        print("- Problems with agent execution or event notification")
        print("")
        print("Next Steps:")
        print("1. Review the specific missing events in the failure message")
        print("2. Check WebSocket event integration in agent execution")
        print("3. Validate AgentRegistry.set_websocket_manager() usage")
        print("4. Ensure EnhancedToolExecutionEngine wraps tool execution")
        print("=" * 80)
        return False
        
    except Exception as e:
        print("=" * 80)
        print("[U+1F4A5] UNEXPECTED ERROR in Golden Path Test")
        print(f"Error: {e}")
        print("")
        print("Stack Trace:")
        traceback.print_exc()
        print("")
        print("This error suggests infrastructure issues:")
        print("- WebSocket connection failures")
        print("- Authentication problems")
        print("- Service availability issues")
        print("=" * 80)
        return False
        
    finally:
        # Always cleanup
        try:
            print("[U+1F9F9] Cleaning up test resources...")
            await test_instance.cleanup_method()
            print(" PASS:  Cleanup completed")
        except Exception as cleanup_error:
            print(f" WARNING: [U+FE0F]  Cleanup warning: {cleanup_error}")


async def run_failure_modes_test():
    """Run the WebSocket failure modes test."""
    print("[U+1F527] Running WebSocket Message Routing Failure Modes Test...")
    
    test_instance = TestWebSocketMessageToAgentGoldenPath()
    
    try:
        test_instance.setup_method()
        await test_instance.test_websocket_message_routing_failure_modes()
        print(" PASS:  Failure modes test completed successfully")
        return True
        
    except Exception as e:
        print(f" FAIL:  Failure modes test failed: {e}")
        return False
        
    finally:
        await test_instance.cleanup_method()


async def run_concurrent_test():
    """Run the concurrent message handling test."""
    print("[U+1F527] Running WebSocket Concurrent Message Handling Test...")
    
    test_instance = TestWebSocketMessageToAgentGoldenPath()
    
    try:
        test_instance.setup_method()
        await test_instance.test_websocket_concurrent_message_handling()
        print(" PASS:  Concurrent handling test completed successfully")
        return True
        
    except Exception as e:
        print(f" FAIL:  Concurrent handling test failed: {e}")
        return False
        
    finally:
        await test_instance.cleanup_method()


async def main():
    """Main test runner entry point."""
    print("WebSocket Message Routing Test Suite")
    print("===================================")
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        test_type = "golden"  # Default to golden path test
    
    results = []
    
    if test_type == "golden":
        result = await run_golden_path_test()
        results.append(("Golden Path", result))
        
    elif test_type == "failure":
        result = await run_failure_modes_test()
        results.append(("Failure Modes", result))
        
    elif test_type == "concurrent":
        result = await run_concurrent_test()
        results.append(("Concurrent Handling", result))
        
    elif test_type == "all":
        print("Running all WebSocket message routing tests...")
        
        golden_result = await run_golden_path_test()
        results.append(("Golden Path", golden_result))
        
        failure_result = await run_failure_modes_test()
        results.append(("Failure Modes", failure_result))
        
        concurrent_result = await run_concurrent_test()
        results.append(("Concurrent Handling", concurrent_result))
        
    else:
        print(f"Unknown test type: {test_type}")
        print("Available options: golden, failure, concurrent, all")
        return 1
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = " PASS:  PASSED" if passed else " FAIL:  FAILED"
        print(f"{test_name:30} {status}")
    
    # Determine exit code
    failed_tests = [name for name, passed in results if not passed]
    
    if not failed_tests:
        print("\n CELEBRATION:  All tests completed successfully!")
        return 0
    else:
        print(f"\n WARNING: [U+FE0F]  {len(failed_tests)} test(s) failed: {', '.join(failed_tests)}")
        print("Note: Golden Path test failure is EXPECTED initially.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[U+1F6D1] Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[U+1F4A5] Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)