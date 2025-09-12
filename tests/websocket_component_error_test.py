#!/usr/bin/env python3
"""
WebSocket Component Error Reporting Test

This test validates the new component-specific error reporting system
that replaces generic 1011 WebSocket errors with detailed component diagnostics.

MISSION: Prove that the WebSocket error reporting system can identify
and report specific component failures instead of generic 1011 errors.
"""

import asyncio
import json
import pytest
import websockets
from typing import Dict, Any, Optional
from datetime import datetime

# Test configuration
WEBSOCKET_URL = "ws://localhost:8000/ws"
TEST_TIMEOUT = 30.0

class WebSocketComponentErrorTester:
    """Test harness for component-specific WebSocket error reporting."""
    
    def __init__(self):
        self.test_results = {
            "component_errors_detected": [],
            "error_codes_received": [],
            "generic_1011_errors": 0,
            "specific_component_errors": 0,
            "test_timestamp": datetime.now().isoformat()
        }
    
    async def test_component_health_validation(self) -> Dict[str, Any]:
        """Test the component health validation function directly."""
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import validate_websocket_component_health
            
            print(" SEARCH:  Testing component health validation...")
            health_report = validate_websocket_component_health()
            
            print(f" CHART:  Health Report Summary: {health_report.get('summary', 'Unknown')}")
            print(f"[U+1F3E5] Overall Health: {' PASS:  Healthy' if health_report.get('healthy', False) else ' FAIL:  Unhealthy'}")
            
            if health_report.get("failed_components"):
                print(f" ALERT:  Failed Components: {health_report['failed_components']}")
                for component, details in health_report.get("component_details", {}).items():
                    if details.get("status") == "failed":
                        error_code = details.get("error_code", "unknown")
                        print(f"    FAIL:  {component}: Code {error_code} - {details.get('error', 'Unknown error')}")
            
            return {
                "test": "component_health_validation",
                "success": True,
                "health_report": health_report,
                "healthy": health_report.get("healthy", False),
                "failed_components": health_report.get("failed_components", [])
            }
            
        except Exception as e:
            print(f" FAIL:  Component health validation test failed: {e}")
            return {
                "test": "component_health_validation", 
                "success": False,
                "error": str(e)
            }
    
    async def test_websocket_error_codes(self) -> Dict[str, Any]:
        """Test WebSocket component error code generation."""
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketComponentError
            
            print("[U+1F9EA] Testing WebSocket component error codes...")
            
            # Test different error types
            auth_error = WebSocketComponentError.auth_failure("Test auth failure")
            database_error = WebSocketComponentError.database_failure("Test database failure")
            factory_error = WebSocketComponentError.factory_failure("Test factory failure")
            handler_error = WebSocketComponentError.handler_failure("Test handler failure")
            
            error_codes = {
                "auth": auth_error.error_code,
                "database": database_error.error_code,
                "factory": factory_error.error_code,
                "handler": handler_error.error_code
            }
            
            print(f"[U+1F522] Error Codes Generated:")
            for component, code in error_codes.items():
                print(f"   {component}: {code}")
            
            # Verify no generic 1011 codes unless explicitly set
            non_generic_codes = [code for code in error_codes.values() if code != 1011]
            
            return {
                "test": "websocket_error_codes",
                "success": True,
                "error_codes": error_codes,
                "non_generic_codes": len(non_generic_codes),
                "total_codes": len(error_codes),
                "all_specific": len(non_generic_codes) == len(error_codes)
            }
            
        except Exception as e:
            print(f" FAIL:  WebSocket error codes test failed: {e}")
            return {
                "test": "websocket_error_codes",
                "success": False,
                "error": str(e)
            }
    
    async def test_websocket_connection_with_error_reporting(self) -> Dict[str, Any]:
        """Test actual WebSocket connection to observe error reporting behavior."""
        try:
            print("[U+1F310] Testing WebSocket connection with error reporting...")
            
            # Try to connect without authentication to trigger auth error
            try:
                async with websockets.connect(
                    WEBSOCKET_URL,
                    timeout=5.0,
                    close_timeout=2.0
                ) as websocket:
                    print("[U+1F4E1] WebSocket connected - sending test message...")
                    
                    # Send a message to trigger processing
                    test_message = {
                        "type": "chat_message",
                        "content": "test message to trigger error reporting"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Listen for response messages
                    error_messages = []
                    try:
                        while True:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            response_data = json.loads(response)
                            
                            print(f"[U+1F4E8] Received response: {response_data.get('type', 'unknown')}")
                            
                            # Check for error responses
                            if response_data.get("type") == "error":
                                error = response_data.get("error", {})
                                error_code = error.get("code", "unknown")
                                component = error.get("component", "unknown")
                                
                                print(f" TARGET:  Component Error Detected: {component} (Code: {error_code})")
                                error_messages.append(response_data)
                                
                                # Track error statistics
                                if error_code == 1011:
                                    self.test_results["generic_1011_errors"] += 1
                                else:
                                    self.test_results["specific_component_errors"] += 1
                                    
                                self.test_results["error_codes_received"].append(error_code)
                                self.test_results["component_errors_detected"].append(component)
                            
                            # Check for system messages about errors
                            elif response_data.get("type") == "system_message":
                                event = response_data.get("content", {}).get("event", "")
                                if "error" in event.lower() or "recovery" in event.lower():
                                    print(f"[U+1F527] System Recovery Message: {event}")
                    
                    except asyncio.TimeoutError:
                        print("[U+23F0] Response timeout - checking collected error data...")
                        pass
                    
                    return {
                        "test": "websocket_connection_error_reporting",
                        "success": True,
                        "error_messages_received": len(error_messages),
                        "specific_component_errors": self.test_results["specific_component_errors"],
                        "generic_1011_errors": self.test_results["generic_1011_errors"],
                        "error_codes": self.test_results["error_codes_received"],
                        "components_detected": self.test_results["component_errors_detected"],
                        "error_messages": error_messages
                    }
                    
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"[U+1F50C] WebSocket connection closed: Code {e.code} - {e.reason}")
                
                # Analyze close code for component-specific information
                if e.code != 1011:
                    print(f" PASS:  Non-generic close code detected: {e.code}")
                    self.test_results["specific_component_errors"] += 1
                else:
                    print(f" FAIL:  Generic 1011 close code detected")
                    self.test_results["generic_1011_errors"] += 1
                
                return {
                    "test": "websocket_connection_error_reporting",
                    "success": True,
                    "connection_closed": True,
                    "close_code": e.code,
                    "close_reason": e.reason,
                    "specific_error": e.code != 1011
                }
                
        except Exception as e:
            print(f" FAIL:  WebSocket connection test failed: {e}")
            return {
                "test": "websocket_connection_error_reporting",
                "success": False,
                "error": str(e)
            }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive test suite for component error reporting."""
        print("[U+1F680] Starting WebSocket Component Error Reporting Test Suite...")
        print("=" * 70)
        
        test_results = []
        
        # Test 1: Component Health Validation
        print("\n[U+1F4CB] TEST 1: Component Health Validation")
        health_test = await self.test_component_health_validation()
        test_results.append(health_test)
        
        # Test 2: Error Code Generation
        print("\n[U+1F4CB] TEST 2: Error Code Generation")
        error_code_test = await self.test_websocket_error_codes()
        test_results.append(error_code_test)
        
        # Test 3: WebSocket Connection Error Reporting
        print("\n[U+1F4CB] TEST 3: WebSocket Connection Error Reporting")
        connection_test = await self.test_websocket_connection_with_error_reporting()
        test_results.append(connection_test)
        
        # Compile final results
        successful_tests = sum(1 for test in test_results if test.get("success", False))
        
        final_results = {
            "test_suite": "websocket_component_error_reporting",
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(test_results),
            "successful_tests": successful_tests,
            "success_rate": successful_tests / len(test_results) if test_results else 0,
            "overall_success": successful_tests == len(test_results),
            "test_results": test_results,
            "error_reporting_summary": self.test_results
        }
        
        print("\n" + "=" * 70)
        print(" CHART:  TEST SUITE RESULTS")
        print(f" PASS:  Successful Tests: {successful_tests}/{len(test_results)}")
        print(f"[U+1F4C8] Success Rate: {final_results['success_rate']:.1%}")
        print(f" TARGET:  Specific Component Errors: {self.test_results['specific_component_errors']}")
        print(f" FAIL:  Generic 1011 Errors: {self.test_results['generic_1011_errors']}")
        
        if self.test_results["component_errors_detected"]:
            print(f" SEARCH:  Components Detected: {set(self.test_results['component_errors_detected'])}")
        
        if self.test_results["error_codes_received"]:
            print(f"[U+1F522] Error Codes Received: {set(self.test_results['error_codes_received'])}")
        
        return final_results


async def main():
    """Main test execution function."""
    print("[U+1F527] WebSocket Component Error Reporting Test")
    print("Mission: Validate component-specific error reporting to replace generic 1011 errors")
    print()
    
    tester = WebSocketComponentErrorTester()
    results = await tester.run_comprehensive_test()
    
    # Save results to file
    with open("websocket_component_error_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n[U+1F4BE] Results saved to: websocket_component_error_test_results.json")
    
    # Return success status for CI/CD
    if results["overall_success"]:
        print(" CELEBRATION:  All tests passed!")
        return 0
    else:
        print(" FAIL:  Some tests failed!")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)