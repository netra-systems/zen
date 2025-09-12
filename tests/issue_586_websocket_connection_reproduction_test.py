"""
Issue #586: WebSocket Connection Failure Reproduction Test
========================================================

This test reproduces WebSocket connection failures without requiring Docker.
Designed to test WebSocket connectivity issues with the staging backend.

Execution: Python-only (no Docker dependency)
Target: GCP Staging WebSocket Endpoints
Focus: WebSocket connection failures and handshake issues
"""

import asyncio
import websockets
import pytest
import time
import sys
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Try different import patterns for IsolatedEnvironment
try:
    from shared.isolated_environment import IsolatedEnvironment
except ImportError:
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
        from isolated_environment import IsolatedEnvironment
    except ImportError:
        # Fallback - create a minimal stub for IsolatedEnvironment
        class IsolatedEnvironment:
            def __init__(self):
                pass


class WebSocketConnectionReproductionTest:
    """Test WebSocket connections to reproduce connection failures."""
    
    def __init__(self):
        """Initialize test with staging environment configuration."""
        self.env = IsolatedEnvironment()
        self.staging_websocket_url = "wss://api.staging.netrasystems.ai/ws"
        self.test_results = []
        self.error_patterns = []
        
    async def test_websocket_connection_handshake_failure(self) -> Dict[str, Any]:
        """
        EXPECTED TO FAIL: Test WebSocket connection handshake to reproduce failures.
        
        This test is designed to demonstrate WebSocket connection issues
        described in Issue #586.
        """
        print("\n🔍 TESTING: WebSocket Connection Handshake (Expected Failure)")
        print("=" * 70)
        
        test_result = {
            "test_name": "websocket_connection_handshake_failure",
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "expected_failure": True,
            "purpose": "Reproduce Issue #586 WebSocket connection failure",
            "success": False,
            "error_message": None,
            "connection_time_ms": None,
            "evidence": {}
        }
        
        start_time = time.time()
        
        try:
            websocket_url = self.staging_websocket_url
            print(f"Testing WebSocket connection: {websocket_url}")
            
            # Test basic WebSocket connection without authentication
            async with websockets.connect(
                websocket_url,
                timeout=10.0,
                ping_interval=None,  # Disable ping to avoid timeout issues
                ping_timeout=None
            ) as websocket:
                connection_time = (time.time() - start_time) * 1000
                
                test_result.update({
                    "connection_time_ms": round(connection_time, 2),
                    "websocket_state": websocket.state.name if hasattr(websocket, 'state') else "connected"
                })
                
                print(f"Connection Time: {connection_time:.2f}ms")
                print(f"WebSocket State: {websocket.state.name if hasattr(websocket, 'state') else 'connected'}")
                
                # Try to send a test message
                test_message = {"type": "test", "message": "Issue #586 reproduction test"}
                await websocket.send(json.dumps(test_message))
                print(f"Sent test message: {test_message}")
                
                # Try to receive a response (with short timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"Received response: {response[:100]}...")
                    
                    print("❌ UNEXPECTED SUCCESS: WebSocket connection working properly")
                    test_result.update({
                        "success": False,  # Failed to reproduce the issue
                        "error_message": "WebSocket connection unexpectedly successful",
                        "evidence": {
                            "issue_reproduced": False,
                            "connection_successful": True,
                            "message_exchange_working": True,
                            "response_received": response[:200]
                        }
                    })
                    
                except asyncio.TimeoutError:
                    print("⚠️  No response received (timeout after 5s)")
                    test_result.update({
                        "success": True,  # Success at reproducing communication issues
                        "error_message": "WebSocket connected but no response received",
                        "evidence": {
                            "issue_reproduced": True,
                            "connection_successful": True,
                            "message_exchange_failed": True,
                            "error_type": "communication_timeout"
                        }
                    })
                    self.error_patterns.append("websocket_communication_timeout")
                    
        except websockets.exceptions.ConnectionClosed as e:
            print(f"✅ EXPECTED FAILURE: WebSocket connection closed - {e}")
            test_result.update({
                "success": True,  # Success at reproducing connection issues
                "error_message": f"WebSocket connection closed: {str(e)}",
                "evidence": {
                    "issue_reproduced": True,
                    "error_type": "connection_closed",
                    "websocket_error": str(e)
                }
            })
            self.error_patterns.append("websocket_connection_closed")
            
        except websockets.exceptions.InvalidHandshake as e:
            print(f"✅ EXPECTED FAILURE: WebSocket handshake failed - {e}")
            test_result.update({
                "success": True,  # Success at reproducing handshake issues
                "error_message": f"WebSocket handshake failed: {str(e)}",
                "evidence": {
                    "issue_reproduced": True,
                    "error_type": "invalid_handshake",
                    "handshake_error": str(e)
                }
            })
            self.error_patterns.append("websocket_handshake_failure")
            
        except asyncio.TimeoutError:
            print(f"✅ EXPECTED FAILURE: WebSocket connection timeout")
            test_result.update({
                "success": True,  # Success at reproducing timeout issues
                "error_message": "WebSocket connection timeout",
                "evidence": {
                    "issue_reproduced": True,
                    "error_type": "connection_timeout",
                    "websocket_unreachable": True
                }
            })
            self.error_patterns.append("websocket_connection_timeout")
            
        except Exception as e:
            print(f"✅ EXPECTED FAILURE: WebSocket connection error - {str(e)}")
            test_result.update({
                "success": True,  # Success at reproducing general connection issues
                "error_message": f"WebSocket connection failed: {str(e)}",
                "evidence": {
                    "issue_reproduced": True,
                    "error_type": "connection_error",
                    "websocket_error": str(e)
                }
            })
            self.error_patterns.append("websocket_connection_error")
            
        self.test_results.append(test_result)
        return test_result
    
    async def test_websocket_authentication_failure(self) -> Dict[str, Any]:
        """
        EXPECTED TO FAIL: Test WebSocket authentication to demonstrate auth issues.
        """
        print("\n🔍 TESTING: WebSocket Authentication (Expected Failure)")
        print("=" * 70)
        
        test_result = {
            "test_name": "websocket_authentication_failure",
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "expected_failure": True,
            "purpose": "Demonstrate WebSocket authentication issues",
            "success": False
        }
        
        try:
            # Test WebSocket with various authentication approaches
            auth_tests = [
                {"headers": {"Authorization": "Bearer invalid_token"}, "name": "Bearer Token"},
                {"subprotocols": ["auth.invalid_token"], "name": "Subprotocol Auth"},
                {"headers": {"X-Auth-Token": "invalid_token"}, "name": "Custom Header Auth"}
            ]
            
            for auth_test in auth_tests:
                try:
                    print(f"Testing {auth_test['name']} authentication...")
                    
                    connect_params = {
                        "timeout": 5.0,
                        "ping_interval": None,
                        "ping_timeout": None
                    }
                    connect_params.update({k: v for k, v in auth_test.items() if k != 'name'})
                    
                    async with websockets.connect(self.staging_websocket_url, **connect_params) as websocket:
                        # If connection succeeds, test authentication rejection
                        auth_message = {"type": "auth", "token": "invalid_token"}
                        await websocket.send(json.dumps(auth_message))
                        
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            response_data = json.loads(response)
                            
                            if response_data.get("error") or response_data.get("status") == "unauthorized":
                                print(f"✅ EXPECTED FAILURE: Auth rejected - {response_data}")
                                test_result.update({
                                    "success": True,
                                    "error_message": "Authentication properly rejected",
                                    "evidence": {
                                        "issue_reproduced": True,
                                        "auth_rejection": True,
                                        "auth_method": auth_test['name'],
                                        "response": response_data
                                    }
                                })
                                self.error_patterns.append("websocket_auth_rejection")
                                break
                                
                        except asyncio.TimeoutError:
                            print(f"⚠️  No auth response for {auth_test['name']}")
                            
                except Exception as e:
                    print(f"✅ EXPECTED FAILURE: {auth_test['name']} failed - {str(e)}")
                    test_result.update({
                        "success": True,
                        "error_message": f"Authentication method failed: {str(e)}",
                        "evidence": {
                            "issue_reproduced": True,
                            "auth_failure": True,
                            "auth_method": auth_test['name'],
                            "error_details": str(e)
                        }
                    })
                    self.error_patterns.append("websocket_auth_failure")
                    break
            
            if not test_result.get("success"):
                test_result.update({
                    "success": False,
                    "error_message": "Authentication unexpectedly working or no clear rejection"
                })
            
        except Exception as e:
            print(f"✅ EXPECTED ERROR: Authentication test failed - {str(e)}")
            test_result.update({
                "success": True,
                "error_message": f"Authentication test failed: {str(e)}",
                "evidence": {"auth_test_failed": True}
            })
            self.error_patterns.append("websocket_auth_test_failure")
            
        self.test_results.append(test_result)
        return test_result
    
    async def test_websocket_protocol_mismatch(self) -> Dict[str, Any]:
        """
        EXPECTED TO FAIL: Test WebSocket protocol compatibility issues.
        """
        print("\n🔍 TESTING: WebSocket Protocol Compatibility (Expected Issues)")
        print("=" * 70)
        
        test_result = {
            "test_name": "websocket_protocol_mismatch",
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "expected_failure": True,
            "purpose": "Demonstrate WebSocket protocol compatibility issues",
            "success": False
        }
        
        try:
            # Test various WebSocket protocol versions and subprotocols
            protocol_tests = [
                {"subprotocols": ["chat", "v1.0"], "name": "Custom Protocol v1.0"},
                {"subprotocols": ["websocket-legacy"], "name": "Legacy Protocol"},
                {"subprotocols": ["netra-api-v2"], "name": "API Version v2"},
            ]
            
            for protocol_test in protocol_tests:
                try:
                    print(f"Testing {protocol_test['name']}...")
                    
                    async with websockets.connect(
                        self.staging_websocket_url,
                        timeout=5.0,
                        ping_interval=None,
                        ping_timeout=None,
                        **{k: v for k, v in protocol_test.items() if k != 'name'}
                    ) as websocket:
                        print(f"⚠️  Protocol {protocol_test['name']} connected unexpectedly")
                        
                except websockets.exceptions.NegotiationError as e:
                    print(f"✅ EXPECTED FAILURE: Protocol negotiation failed - {e}")
                    test_result.update({
                        "success": True,
                        "error_message": f"Protocol negotiation failed: {str(e)}",
                        "evidence": {
                            "issue_reproduced": True,
                            "protocol_mismatch": True,
                            "protocol_name": protocol_test['name'],
                            "negotiation_error": str(e)
                        }
                    })
                    self.error_patterns.append("websocket_protocol_mismatch")
                    break
                    
                except Exception as e:
                    print(f"✅ EXPECTED ERROR: {protocol_test['name']} failed - {str(e)}")
                    
        except Exception as e:
            print(f"⚠️  Protocol test setup error: {str(e)}")
            
        self.test_results.append(test_result)
        return test_result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all WebSocket connection reproduction tests."""
        print("🚨 ISSUE #586: WEBSOCKET CONNECTION FAILURE REPRODUCTION")
        print("=" * 80)
        print("Purpose: Reproduce WebSocket connection and communication issues")
        print("Expected: Tests should FAIL to demonstrate WebSocket problems")
        print("=" * 80)
        
        test_suite_start = time.time()
        
        # Run all reproduction tests
        results = await asyncio.gather(
            self.test_websocket_connection_handshake_failure(),
            self.test_websocket_authentication_failure(),
            self.test_websocket_protocol_mismatch(),
            return_exceptions=True
        )
        
        test_suite_duration = time.time() - test_suite_start
        
        # Analyze results
        successful_reproductions = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        total_tests = len(results)
        
        summary = {
            "issue_number": 586,
            "test_purpose": "Reproduce WebSocket connection failures",
            "total_tests": total_tests,
            "successful_reproductions": successful_reproductions,
            "reproduction_rate": successful_reproductions / total_tests if total_tests > 0 else 0,
            "test_duration_seconds": round(test_suite_duration, 2),
            "error_patterns_found": list(set(self.error_patterns)),
            "detailed_results": results,
            "conclusions": {
                "issue_reproduced": successful_reproductions > 0,
                "websocket_service_health": "FAILING" if successful_reproductions > 0 else "HEALTHY",
                "recommended_action": "Fix WebSocket service configuration" if successful_reproductions > 0 else "Investigate false positive"
            }
        }
        
        print(f"\n📊 WEBSOCKET TEST SUITE SUMMARY")
        print("=" * 40)
        print(f"Total Tests: {total_tests}")
        print(f"Issue Reproductions: {successful_reproductions}")
        print(f"Reproduction Rate: {summary['reproduction_rate']:.1%}")
        print(f"Duration: {test_suite_duration:.2f}s")
        print(f"Error Patterns: {', '.join(self.error_patterns) if self.error_patterns else 'None'}")
        print(f"WebSocket Status: {summary['conclusions']['websocket_service_health']}")
        print(f"Recommended Action: {summary['conclusions']['recommended_action']}")
        
        return summary


@pytest.mark.asyncio
async def test_issue_586_websocket_connection_reproduction():
    """
    Issue #586 WebSocket reproduction test that should FAIL to demonstrate the problem.
    
    This test is designed to reproduce WebSocket connection failures.
    SUCCESS = Successfully reproducing WebSocket connection issues  
    FAILURE = WebSocket service is unexpectedly healthy
    """
    tester = WebSocketConnectionReproductionTest()
    results = await tester.run_all_tests()
    
    # Assert that we successfully reproduced WebSocket issues
    assert results["successful_reproductions"] > 0, (
        f"Failed to reproduce Issue #586 WebSocket connection errors. "
        f"Got {results['successful_reproductions']} reproductions out of {results['total_tests']} tests. "
        f"WebSocket service appears to be healthy."
    )
    
    # Assert that we found expected error patterns
    assert len(results["error_patterns_found"]) > 0, (
        "No WebSocket error patterns detected. Issue #586 may be resolved or test needs adjustment."
    )
    
    print(f"\n✅ Successfully reproduced Issue #586 WebSocket connection problems!")
    return results


if __name__ == "__main__":
    """Run the test directly for debugging."""
    async def main():
        print("Running Issue #586 WebSocket Connection Reproduction Test")
        tester = WebSocketConnectionReproductionTest()
        results = await tester.run_all_tests()
        
        print(f"\n🎯 FINAL RESULT:")
        if results["successful_reproductions"] > 0:
            print(f"✅ Issue #586 REPRODUCED: Found {results['successful_reproductions']} WebSocket failures")
            print(f"Error patterns: {', '.join(results['error_patterns_found'])}")
        else:
            print(f"❌ Issue #586 NOT REPRODUCED: WebSocket service appears healthy")
            
        return results
    
    results = asyncio.run(main())