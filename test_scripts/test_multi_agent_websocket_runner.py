#!/usr/bin/env python3
"""
Simple runner for multi-agent WebSocket integration tests.
Runs the comprehensive test suite with proper error handling.
"""

import sys
import asyncio
import unittest
from io import StringIO
from shared.isolated_environment import IsolatedEnvironment

def run_multi_agent_tests():
    """Run the multi-agent WebSocket integration tests."""
    
    print("Starting Multi-Agent WebSocket Integration Tests...")
    print("=" * 60)
    
    try:
        # Import the test class
        from tests.mission_critical.test_websocket_multi_agent_integration_20250902 import TestMultiAgentWebSocketIntegration
        
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestMultiAgentWebSocketIntegration)
        
        # Run tests with custom runner
        runner = unittest.TextTestRunner(
            verbosity=2,
            stream=sys.stdout,
            buffer=True
        )
        
        result = runner.run(suite)
        
        print("\n" + "=" * 60)
        print("MULTI-AGENT WEBSOCKET TEST RESULTS")
        print("=" * 60)
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%" if result.testsRun > 0 else "N/A")
        
        if result.failures:
            print("\nFAILURES:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback[:200]}...")
        
        if result.errors:
            print("\nERRORS:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback[:200]}...")
        
        # Overall status
        if len(result.failures) == 0 and len(result.errors) == 0:
            print("\nOVERALL STATUS: ALL TESTS PASSED")
            print("Multi-agent WebSocket bridge integration is working correctly!")
        else:
            print(f"\nOVERALL STATUS: {len(result.failures + result.errors)} TESTS FAILED")
            print("Issues detected in multi-agent WebSocket integration.")
        
        return result.wasSuccessful()
        
    except ImportError as e:
        print(f"ERROR: Cannot import test module: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_multi_agent_tests()
    sys.exit(0 if success else 1)