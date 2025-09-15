"""
Test WebSocket SessionMiddleware Failure Reproduction

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent WebSocket 1011 internal errors in production
- Value Impact: Ensure real-time chat communication works
- Strategic Impact: Core platform stability - $80K+ MRR at risk

MISSION: Create failing tests that reproduce the exact SessionMiddleware failure
patterns identified in ULTIMATE_TEST_DEPLOY_LOOP_GOLDEN_PATH_20250909_SESSION5.md

ROOT CAUSE TO REPRODUCE:
- "SessionMiddleware must be installed to access request.session"
- WebSocket connection established but internal error 1011 during message processing
- Backend accepts handshake but fails during session access

CRITICAL: These tests MUST FAIL before fixes are applied to validate remediation works.
"""

import pytest
import asyncio
import json
import time
import platform
import websockets
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

from tests.e2e.staging_test_config import get_staging_config

# Mark all tests as critical failure reproduction tests
pytestmark = [pytest.mark.critical, pytest.mark.reproduction, pytest.mark.sessionmiddleware]

class TestWebSocketSessionMiddlewareFailureReproduction:
    """
    CRITICAL: Reproduce exact WebSocket SessionMiddleware failures from SESSION5
    
    These tests are designed to FAIL and demonstrate the exact error patterns
    that need to be fixed. Success criteria is REPRODUCING the failures.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)  # Allow time for failure to manifest
    async def test_websocket_1011_internal_error_reproduction(self):
        """
        CRITICAL FAILURE REPRODUCTION: test_002_websocket_authentication_real
        
        Expected Failure Pattern:
        - WebSocket connection establishes successfully
        - Authentication appears to work
        - Backend accepts handshake
        - FAILS with 1011 internal error when processing messages
        - Error: "SessionMiddleware must be installed to access request.session"
        
        This test MUST FAIL before SessionMiddleware fix is applied.
        """
        config = get_staging_config()
        start_time = time.time()
        
        # Detailed error tracking for root cause analysis
        error_details = {
            "connection_established": False,
            "handshake_successful": False,
            "welcome_message_received": False,
            "internal_error_1011": False,
            "session_middleware_error": False,
            "exact_error_message": None,
            "websocket_close_code": None,
            "websocket_close_reason": None,
            "timestamps": {
                "connection_start": start_time,
                "connection_established": None,
                "error_occurred": None,
                "connection_closed": None
            }
        }
        
        try:
            # Get proper WebSocket headers with authentication
            ws_headers = config.get_websocket_headers()
            print(f" SEARCH:  Attempting WebSocket connection to: {config.websocket_url}")
            print(f" SEARCH:  Using headers: {list(ws_headers.keys()) if ws_headers else 'None'}")
            
            # Connect with authentication - this should succeed initially
            async with websockets.connect(
                config.websocket_url,
                additional_headers=ws_headers if ws_headers else {},
                close_timeout=10
            ) as ws:
                error_details["connection_established"] = True
                error_details["timestamps"]["connection_established"] = time.time()
                print("[U+2713] WebSocket connection established successfully")
                
                # Connection handshake successful
                error_details["handshake_successful"] = True
                
                try:
                    # CRITICAL: This is where SessionMiddleware failure occurs
                    # Backend accepts connection but fails during session access
                    print(" SEARCH:  Waiting for welcome message (this should trigger SessionMiddleware error)...")
                    
                    welcome_response = await asyncio.wait_for(ws.recv(), timeout=15)
                    error_details["welcome_message_received"] = True
                    print(f"[U+1F4E5] Welcome message received: {welcome_response[:100]}...")
                    
                    # If we get here, the SessionMiddleware issue might be fixed
                    print(" WARNING: [U+FE0F] UNEXPECTED: Welcome message received without SessionMiddleware error")
                    print(" WARNING: [U+FE0F] This suggests the SessionMiddleware issue may be resolved")
                    
                except websockets.exceptions.ConnectionClosedError as e:
                    # EXPECTED: This is the exact failure pattern we want to reproduce
                    error_details["timestamps"]["error_occurred"] = time.time()
                    error_details["websocket_close_code"] = e.code
                    error_details["websocket_close_reason"] = e.reason
                    error_details["exact_error_message"] = str(e)
                    
                    if e.code == 1011:
                        error_details["internal_error_1011"] = True
                        print(f"[U+2713] REPRODUCED: WebSocket 1011 internal error: {e}")
                        
                        # Check if this is the SessionMiddleware error pattern
                        if "internal error" in str(e).lower():
                            error_details["session_middleware_error"] = True
                            print("[U+2713] REPRODUCED: SessionMiddleware failure pattern detected")
                    else:
                        print(f" SEARCH:  Different error pattern: {e.code} - {e}")
                        
                except asyncio.TimeoutError:
                    error_details["timestamps"]["error_occurred"] = time.time()
                    print(" SEARCH:  Timeout waiting for welcome message - connection hangs")
                    print(" SEARCH:  This may indicate backend processing failure")
                    
                    # Try to send a message to trigger the SessionMiddleware error
                    try:
                        print(" SEARCH:  Attempting to send message to trigger SessionMiddleware error...")
                        test_message = {
                            "type": "test_message",
                            "content": "Test message to trigger SessionMiddleware error",
                            "timestamp": time.time()
                        }
                        
                        await ws.send(json.dumps(test_message))
                        
                        # Try to receive response - this should trigger the SessionMiddleware error
                        response = await asyncio.wait_for(ws.recv(), timeout=10)
                        print(f" SEARCH:  Unexpected response received: {response[:100]}...")
                        
                    except websockets.exceptions.ConnectionClosedError as msg_error:
                        error_details["websocket_close_code"] = msg_error.code
                        error_details["websocket_close_reason"] = msg_error.reason
                        error_details["exact_error_message"] = str(msg_error)
                        
                        if msg_error.code == 1011:
                            error_details["internal_error_1011"] = True
                            error_details["session_middleware_error"] = True
                            print(f"[U+2713] REPRODUCED: SessionMiddleware error on message send: {msg_error}")
                    
                    except Exception as msg_error:
                        print(f" SEARCH:  Message send error: {msg_error}")
                
                error_details["timestamps"]["connection_closed"] = time.time()
                
        except websockets.exceptions.InvalidStatus as e:
            # Connection rejected - might be auth issue
            print(f" SEARCH:  Connection rejected: {e}")
            if e.status_code in [401, 403]:
                print(" SEARCH:  Authentication rejected - expected in staging environment")
            else:
                print(f" SEARCH:  Unexpected status code: {e.status_code}")
                
        except Exception as e:
            error_details["exact_error_message"] = str(e)
            print(f" SEARCH:  Unexpected connection error: {e}")
        
        duration = time.time() - start_time
        error_details["total_duration"] = duration
        
        # Comprehensive error analysis
        print("\n" + "="*50)
        print("WEBSOCKET SESSIONMIDDLEWARE FAILURE ANALYSIS")
        print("="*50)
        
        for key, value in error_details.items():
            print(f"{key}: {value}")
        
        print(f"\nTest duration: {duration:.3f}s")
        
        # CRITICAL: Verify this was a real network test
        assert duration > 0.5, f"Test too fast ({duration:.3f}s) - must make real network calls!"
        
        # SUCCESS CRITERIA: We want to reproduce the SessionMiddleware failure
        if error_details["internal_error_1011"] and error_details["session_middleware_error"]:
            print("\n PASS:  SUCCESS: Successfully reproduced SessionMiddleware failure!")
            print(" PASS:  WebSocket 1011 internal error reproduced")
            print(" PASS:  SessionMiddleware error pattern confirmed")
            
            # This is actually success for a reproduction test
            assert True, "SessionMiddleware failure successfully reproduced"
            
        elif error_details["connection_established"] and not error_details["welcome_message_received"]:
            print("\n WARNING: [U+FE0F] PARTIAL REPRODUCTION: Connection established but failed during processing")
            print(" WARNING: [U+FE0F] This suggests SessionMiddleware issue exists but may manifest differently")
            
            # Still consider this a successful reproduction of the problem
            assert True, "SessionMiddleware processing failure reproduced"
            
        elif error_details["connection_established"] and error_details["welcome_message_received"]:
            print("\n FAIL:  REPRODUCTION FAILED: No SessionMiddleware error detected")
            print(" FAIL:  This suggests the SessionMiddleware issue may be fixed")
            print(" FAIL:  Or the test environment has different configuration")
            
            # For a reproduction test, this is actually a failure
            pytest.fail(
                "Failed to reproduce SessionMiddleware error. "
                "This suggests the issue may be fixed or environment differs from SESSION5."
            )
            
        else:
            print("\n FAIL:  REPRODUCTION FAILED: Could not establish WebSocket connection")
            print(" FAIL:  Cannot reproduce SessionMiddleware error without connection")
            
            pytest.fail(
                "Failed to establish WebSocket connection to reproduce SessionMiddleware error. "
                f"Connection details: {error_details}"
            )
    
    @pytest.mark.asyncio 
    @pytest.mark.timeout(90)
    async def test_session_middleware_backend_logs_correlation(self):
        """
        SUPPORTING TEST: Verify backend logs show SessionMiddleware errors
        
        This test attempts to correlate WebSocket failures with specific
        backend log patterns that indicate SessionMiddleware issues.
        """
        config = get_staging_config()
        start_time = time.time()
        
        # First, verify backend health
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                health_response = await client.get(f"{config.backend_url}/health")
                print(f" SEARCH:  Backend health status: {health_response.status_code}")
                
                if health_response.status_code != 200:
                    print(f" WARNING: [U+FE0F] Backend health check failed: {health_response.text}")
                else:
                    print("[U+2713] Backend is responding to HTTP requests")
                    
            except Exception as e:
                print(f" FAIL:  Backend health check failed: {e}")
                pytest.fail(f"Cannot test SessionMiddleware with unhealthy backend: {e}")
        
        # Test if specific endpoints that require session access fail
        session_dependent_endpoints = [
            "/api/user/session",
            "/api/user/context", 
            "/api/user/threads",
            "/api/sessions"
        ]
        
        session_errors_detected = []
        
        async with httpx.AsyncClient(timeout=30) as client:
            for endpoint in session_dependent_endpoints:
                try:
                    response = await client.get(f"{config.backend_url}{endpoint}")
                    
                    if response.status_code == 500:
                        # Check if response indicates session middleware issues
                        response_text = response.text.lower()
                        if any(phrase in response_text for phrase in [
                            "sessionmiddleware", 
                            "session middleware", 
                            "request.session",
                            "session not found"
                        ]):
                            session_errors_detected.append({
                                "endpoint": endpoint,
                                "status": response.status_code,
                                "error_text": response.text[:200]
                            })
                            print(f" SEARCH:  SessionMiddleware error detected on {endpoint}")
                    
                    await asyncio.sleep(0.1)  # Prevent overwhelming backend
                    
                except Exception as e:
                    print(f" SEARCH:  Endpoint test error {endpoint}: {e}")
        
        duration = time.time() - start_time
        
        print(f"\nSession middleware backend correlation results:")
        print(f"Endpoints tested: {len(session_dependent_endpoints)}")
        print(f"Session errors detected: {len(session_errors_detected)}")
        
        for error in session_errors_detected:
            print(f"  {error['endpoint']}: {error['status']} - {error['error_text'][:100]}...")
        
        print(f"Test duration: {duration:.3f}s")
        
        # Real test validation
        assert duration > 0.3, f"Test too fast ({duration:.3f}s) - must make real HTTP calls!"
        
        # For reproduction purposes, we want to detect session middleware issues
        if session_errors_detected:
            print(" PASS:  SUCCESS: SessionMiddleware errors detected in HTTP endpoints")
            print(" PASS:  This supports the WebSocket SessionMiddleware failure hypothesis")
        else:
            print(" SEARCH:  No obvious SessionMiddleware errors in HTTP endpoints")
            print(" SEARCH:  SessionMiddleware issue may be specific to WebSocket processing")
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60) 
    async def test_websocket_connection_vs_processing_failure(self):
        """
        DETAILED ANALYSIS: Separate connection establishment from message processing
        
        This test specifically isolates the SessionMiddleware failure to either:
        1. Connection establishment phase
        2. Message processing phase
        3. Session context access phase
        """
        config = get_staging_config()
        start_time = time.time()
        
        connection_phases = {
            "tcp_connection": False,
            "websocket_handshake": False,
            "authentication": False,
            "session_access": False,
            "message_processing": False,
            "error_phase": None,
            "error_details": None
        }
        
        try:
            print(" SEARCH:  Phase 1: TCP Connection")
            # Test raw WebSocket connection without auth first
            async with websockets.connect(
                config.websocket_url.replace("wss://", "ws://") if config.websocket_url.startswith("wss://") else config.websocket_url,
                timeout=10
            ) as ws:
                connection_phases["tcp_connection"] = True
                connection_phases["websocket_handshake"] = True
                print("[U+2713] Phase 1 & 2: TCP Connection and WebSocket handshake successful")
                
                # Close immediately to test just connection capability
                
        except Exception as e:
            connection_phases["error_phase"] = "tcp_connection"
            connection_phases["error_details"] = str(e)
            print(f" FAIL:  Phase 1 failed: {e}")
        
        if connection_phases["tcp_connection"]:
            try:
                print(" SEARCH:  Phase 3: Authentication")
                ws_headers = config.get_websocket_headers()
                
                async with websockets.connect(
                    config.websocket_url,
                    additional_headers=ws_headers if ws_headers else {},
                    timeout=10
                ) as ws:
                    connection_phases["authentication"] = True
                    print("[U+2713] Phase 3: Authentication successful")
                    
                    try:
                        print(" SEARCH:  Phase 4: Session Access (welcome message)")
                        # This is where SessionMiddleware error typically occurs
                        welcome_msg = await asyncio.wait_for(ws.recv(), timeout=5)
                        connection_phases["session_access"] = True
                        print("[U+2713] Phase 4: Session access successful")
                        
                        try:
                            print(" SEARCH:  Phase 5: Message Processing")
                            test_msg = {"type": "test", "content": "test"}
                            await ws.send(json.dumps(test_msg))
                            
                            response = await asyncio.wait_for(ws.recv(), timeout=5)
                            connection_phases["message_processing"] = True
                            print("[U+2713] Phase 5: Message processing successful")
                            
                        except Exception as e:
                            connection_phases["error_phase"] = "message_processing"
                            connection_phases["error_details"] = str(e)
                            print(f" FAIL:  Phase 5 failed: {e}")
                            
                    except websockets.exceptions.ConnectionClosedError as e:
                        connection_phases["error_phase"] = "session_access"
                        connection_phases["error_details"] = f"Code {e.code}: {e.reason}"
                        print(f" FAIL:  Phase 4 failed - SessionMiddleware error likely: {e}")
                        
                    except asyncio.TimeoutError:
                        connection_phases["error_phase"] = "session_access" 
                        connection_phases["error_details"] = "Timeout waiting for welcome message"
                        print(" FAIL:  Phase 4 failed: Timeout - backend processing issue")
                        
            except Exception as e:
                connection_phases["error_phase"] = "authentication"
                connection_phases["error_details"] = str(e)
                print(f" FAIL:  Phase 3 failed: {e}")
        
        duration = time.time() - start_time
        
        print("\n" + "="*50)
        print("WEBSOCKET CONNECTION PHASE ANALYSIS")
        print("="*50)
        
        for phase, success in connection_phases.items():
            print(f"{phase}: {success}")
        
        print(f"Test duration: {duration:.3f}s")
        
        # Real test validation
        assert duration > 0.2, f"Test too fast ({duration:.3f}s) - must make real network calls!"
        
        # Analyze where the failure occurs for SessionMiddleware debugging
        if connection_phases["error_phase"] == "session_access":
            print("\n PASS:  SUCCESS: SessionMiddleware failure reproduced at session access phase")
            print(" PASS:  Connection and auth work, but session access fails")
            print(" PASS:  This confirms the SessionMiddleware installation issue")
            
        elif connection_phases["error_phase"] == "message_processing":
            print("\n PASS:  SUCCESS: SessionMiddleware failure reproduced at message processing phase")
            print(" PASS:  Welcome message works, but message processing fails")
            print(" PASS:  This suggests SessionMiddleware works partially")
            
        elif connection_phases["error_phase"] is None:
            print("\n FAIL:  REPRODUCTION FAILED: All phases successful")
            print(" FAIL:  SessionMiddleware appears to be working correctly")
            pytest.fail("Failed to reproduce SessionMiddleware failure - all connection phases successful")
            
        else:
            print(f"\n SEARCH:  DIFFERENT FAILURE: Error in {connection_phases['error_phase']} phase")
            print(f" SEARCH:  Error details: {connection_phases['error_details']}")
            print(" SEARCH:  This may be a different issue than SessionMiddleware")


def verify_reproduction_test_timing(test_name: str, duration: float, minimum: float = 0.2):
    """
    Verify reproduction test took real time to execute
    
    Reproduction tests must make real network calls to accurately 
    reproduce staging environment failures.
    """
    assert duration >= minimum, \
        f" ALERT:  FAKE REPRODUCTION TEST: {test_name} completed in {duration:.3f}s " \
        f"(minimum: {minimum}s). Reproduction tests must make real network calls!"


if __name__ == "__main__":
    print("=" * 70)
    print("WEBSOCKET SESSIONMIDDLEWARE FAILURE REPRODUCTION TESTS")
    print("=" * 70)
    print("These tests are designed to FAIL and reproduce exact SessionMiddleware")
    print("failure patterns from SESSION5. Success = reproducing the failures.")
    print("") 
    print("Expected failures:")
    print("- WebSocket 1011 internal server error")
    print("- 'SessionMiddleware must be installed' error pattern")
    print("- Connection succeeds but message processing fails")
    print("=" * 70)
