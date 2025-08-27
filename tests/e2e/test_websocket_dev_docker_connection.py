"""
E2E test to expose WebSocket connection failures in dev docker environment.

This test specifically targets the WebSocket connection issue occurring at:
- ws://localhost:8000/ws
- Environment: dev docker

Expected Error Pattern:
- WebSocketService.ts:988 WebSocket connection to 'ws://localhost:8000/ws' failed
- WebSocket error occurred [WebSocketService] (websocket_error)
- WebSocket connection error [WebSocketProvider] (connection_error)
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, Optional

import httpx
import pytest
import websocket
from websocket import WebSocketApp

# Add path for test framework imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Mark test for dev environment only
pytestmark = pytest.mark.dev


class WebSocketConnectionTest:
    """Test harness for WebSocket connection issues."""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws"
        self.connection_errors = []
        self.error_logs = []
        self.ws_app = None
        
    def on_message(self, ws, message):
        """Handle WebSocket messages."""
        print(f"WebSocket message received: {message}")
        
    def on_error(self, ws, error):
        """Capture WebSocket errors."""
        error_msg = str(error)
        print(f"WebSocket error: {error_msg}")
        self.connection_errors.append(error_msg)
        self.error_logs.append({
            "type": "websocket_error",
            "message": error_msg,
            "timestamp": time.time()
        })
        
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        print(f"WebSocket closed - Code: {close_status_code}, Message: {close_msg}")
        if close_status_code:
            self.error_logs.append({
                "type": "websocket_close",
                "code": close_status_code,
                "message": close_msg,
                "timestamp": time.time()
            })
            
    def on_open(self, ws):
        """Handle WebSocket open."""
        print("WebSocket connection opened")
        
    def test_basic_connection(self) -> Dict[str, Any]:
        """Test basic WebSocket connection without authentication."""
        print(f"\nTesting WebSocket connection to: {self.ws_url}")
        
        try:
            # Test raw WebSocket connection
            self.ws_app = WebSocketApp(
                self.ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Run with timeout
            import threading
            def run_ws():
                self.ws_app.run_forever(ping_interval=30, ping_timeout=10)
            
            ws_thread = threading.Thread(target=run_ws)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection attempt
            time.sleep(5)
            
            # Force close if still running
            if self.ws_app:
                self.ws_app.close()
                
            ws_thread.join(timeout=2)
            
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            print(f"Exception during connection: {error_msg}")
            self.connection_errors.append(error_msg)
            self.error_logs.append({
                "type": "connection_exception",
                "message": error_msg,
                "timestamp": time.time()
            })
            
        return {
            "connection_errors": self.connection_errors,
            "error_logs": self.error_logs,
            "ws_url": self.ws_url
        }
        
    def test_cors_headers(self) -> Dict[str, Any]:
        """Test WebSocket CORS configuration."""
        print("\nTesting WebSocket CORS headers...")
        
        cors_issues = []
        
        try:
            # Test with various connection methods
            # Note: We avoid setting explicit Origin headers to prevent conflicts with
            # the websocket-client library's automatic Origin header generation
            test_cases = [
                ("Default connection", {}),  # Let client set origin automatically
                ("Test endpoint", {"endpoint": "/ws/test"}),  # Try test endpoint
            ]
            
            for description, options in test_cases:
                endpoint = options.get("endpoint", self.ws_url)
                # If endpoint is relative, make it absolute
                if endpoint.startswith("/"):
                    endpoint = f"ws://localhost:8000{endpoint}"
                    
                try:
                    # Create WebSocket connection without explicit origin to avoid duplicates
                    ws = websocket.create_connection(
                        endpoint,
                        timeout=5
                    )
                    ws.close()
                    print(f"[SUCCESS] Connection successful: {description}")
                    
                except Exception as e:
                    error_msg = f"Failed {description}: {str(e)}"
                    print(f"[FAILED] {error_msg}")
                    cors_issues.append({
                        "test": description,
                        "endpoint": endpoint,
                        "error": str(e),
                        "timestamp": time.time()
                    })
                    
        except Exception as e:
            cors_issues.append({
                "type": "cors_test_failure",
                "error": str(e),
                "timestamp": time.time()
            })
            
        return {
            "cors_issues": cors_issues,
            "tested_cases": [desc for desc, _ in test_cases] if 'test_cases' in locals() else []
        }
        
    def test_backend_availability(self) -> Dict[str, Any]:
        """Check if backend services are running."""
        print("\nChecking backend service availability...")
        
        service_status = {}
        
        # Check main backend HTTP endpoint
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=5)
            service_status["backend_http"] = {
                "available": response.status_code == 200,
                "status_code": response.status_code
            }
        except Exception as e:
            service_status["backend_http"] = {
                "available": False,
                "error": str(e)
            }
            
        # Check WebSocket endpoint availability via HTTP upgrade
        try:
            response = httpx.get(
                f"{self.base_url}/ws",
                headers={
                    "Upgrade": "websocket",
                    "Connection": "Upgrade",
                    "Sec-WebSocket-Key": "x3JJHMbDL1EzLkh9GBhXDw==",
                    "Sec-WebSocket-Version": "13"
                },
                timeout=5
            )
            # Expected 426 Upgrade Required or 101 Switching Protocols via httpx limitations
            service_status["websocket_endpoint"] = {
                "reachable": True,
                "status_code": response.status_code
            }
        except Exception as e:
            service_status["websocket_endpoint"] = {
                "reachable": False,
                "error": str(e)
            }
            
        return service_status


@pytest.mark.e2e
@pytest.mark.websocket
class TestWebSocketDevDockerConnection:
    """E2E test suite for WebSocket connection issues in dev docker."""
    
    def test_websocket_connection_failure(self):
        """
        Test that reproduces the WebSocket connection failure in dev docker.
        
        This test is expected to FAIL with the following errors:
        - Connection refused or failed
        - CORS origin validation errors
        - WebSocket handshake failures
        """
        test_harness = WebSocketConnectionTest()
        
        # Check backend availability first
        backend_status = test_harness.test_backend_availability()
        print(f"\nBackend Status: {json.dumps(backend_status, indent=2)}")
        
        # Test basic connection (expected to fail)
        connection_result = test_harness.test_basic_connection()
        print(f"\nConnection Test Result: {json.dumps(connection_result, indent=2)}")
        
        # Test CORS configuration
        cors_result = test_harness.test_cors_headers()
        print(f"\nCORS Test Result: {json.dumps(cors_result, indent=2)}")
        
        # Compile all errors
        all_errors = {
            "backend_status": backend_status,
            "connection_errors": connection_result["connection_errors"],
            "error_logs": connection_result["error_logs"],
            "cors_issues": cors_result["cors_issues"]
        }
        
        # Print summary
        print("\n" + "="*60)
        print("WebSocket Connection Test Summary")
        print("="*60)
        
        if connection_result["connection_errors"]:
            print(f"\n❌ Connection Errors Found ({len(connection_result['connection_errors'])} total):")
            for error in connection_result["connection_errors"]:
                print(f"  - {error}")
                
        if cors_result["cors_issues"]:
            print(f"\n❌ CORS Issues Found ({len(cors_result['cors_issues'])} total):")
            for issue in cors_result["cors_issues"]:
                print(f"  - Origin: {issue.get('origin', 'N/A')}, Error: {issue.get('error', 'Unknown')}")
                
        if not backend_status.get("backend_http", {}).get("available"):
            print(f"\n❌ Backend HTTP not available")
            
        if not backend_status.get("websocket_endpoint", {}).get("reachable"):
            print(f"\n❌ WebSocket endpoint not reachable")
            
        # This assertion is expected to FAIL, demonstrating the issue
        assert len(connection_result["connection_errors"]) == 0, (
            f"WebSocket connection failed with errors: {connection_result['connection_errors']}"
        )
        
        # Additional assertions to expose specific issues
        assert len(cors_result["cors_issues"]) == 0, (
            f"CORS configuration issues found: {cors_result['cors_issues']}"
        )
        
        assert backend_status.get("backend_http", {}).get("available"), (
            "Backend HTTP service is not available"
        )
        
        assert backend_status.get("websocket_endpoint", {}).get("reachable"), (
            "WebSocket endpoint is not reachable"
        )


@pytest.mark.e2e
@pytest.mark.websocket
class TestWebSocketCORSValidation:
    """Specific tests for WebSocket CORS validation issues."""
    
    def test_localhost_origin_validation(self):
        """Test that localhost origins are properly validated in dev environment."""
        
        # Test basic WebSocket connectivity without explicit Origin headers
        # This avoids the duplicate Origin header issue with websocket-client library
        test_cases = [
            ("Basic connection", "ws://localhost:8000/ws", True, "Main WebSocket endpoint"),
            ("Test endpoint", "ws://localhost:8000/ws/test", True, "Test WebSocket endpoint (no auth)"),
        ]
        
        errors = []
        for description, ws_url, should_work, details in test_cases:
            print(f"\nTesting: {description} - {details}")
            print(f"URL: {ws_url}")
                
            try:
                # Don't set explicit Origin headers to avoid duplicates
                ws = websocket.create_connection(
                    ws_url,
                    timeout=5
                )
                ws.close()
                
                if should_work:
                    print(f"[SUCCESS] Connection successful (as expected)")
                else:
                    error_msg = f"Connection succeeded but should have failed for: {ws_url}"
                    print(f"[FAILED] {error_msg}")
                    errors.append(error_msg)
                    
            except Exception as e:
                if not should_work:
                    print(f"[SUCCESS] Connection failed as expected: {str(e)}")
                else:
                    error_msg = f"Connection failed but should have succeeded for '{ws_url}': {str(e)}"
                    print(f"[FAILED] {error_msg}")
                    errors.append(error_msg)
                    
        # This assertion is expected to FAIL if WebSocket connections don't work
        assert len(errors) == 0, f"WebSocket connection errors:\n" + "\n".join(errors)


@pytest.mark.e2e  
@pytest.mark.websocket
async def test_websocket_connection_with_retry():
    """Test WebSocket connection with retry logic to expose intermittent failures."""
    
    max_retries = 3
    retry_delay = 2
    connection_attempts = []
    
    for attempt in range(max_retries):
        print(f"\nConnection attempt {attempt + 1}/{max_retries}")
        
        try:
            # Don't set explicit Origin header to avoid duplicates with websocket-client library
            ws = websocket.create_connection(
                "ws://localhost:8000/ws/test",  # Use test endpoint to avoid auth issues
                timeout=10
            )
            
            # Try to send a test message
            import json
            test_msg = json.dumps({"type": "ping"})
            ws.send(test_msg)
            response = ws.recv()
            
            ws.close()
            
            connection_attempts.append({
                "attempt": attempt + 1,
                "success": True,
                "message": "Connected successfully"
            })
            print("[SUCCESS] Connection successful")
            break
            
        except Exception as e:
            error_msg = str(e)
            connection_attempts.append({
                "attempt": attempt + 1,
                "success": False,
                "error": error_msg
            })
            print(f"✗ Connection failed: {error_msg}")
            
            if attempt < max_retries - 1:
                print(f"Waiting {retry_delay} seconds before retry...")
                await asyncio.sleep(retry_delay)
                
    # Check if all attempts failed
    all_failed = all(not attempt["success"] for attempt in connection_attempts)
    
    # This assertion is expected to FAIL if WebSocket is not working
    assert not all_failed, (
        f"All {max_retries} WebSocket connection attempts failed:\n" +
        "\n".join([f"  Attempt {a['attempt']}: {a.get('error', 'Unknown error')}" 
                  for a in connection_attempts if not a["success"]])
    )


if __name__ == "__main__":
    """Allow running this test directly for debugging."""
    print("Running WebSocket connection tests for dev docker environment...")
    print("="*60)
    
    test = WebSocketConnectionTest()
    
    # Run all tests
    backend_status = test.test_backend_availability()
    print(f"\nBackend Status:\n{json.dumps(backend_status, indent=2)}")
    
    connection_result = test.test_basic_connection()
    print(f"\nConnection Result:\n{json.dumps(connection_result, indent=2)}")
    
    cors_result = test.test_cors_headers()
    print(f"\nCORS Result:\n{json.dumps(cors_result, indent=2)}")
    
    # Run async test
    import asyncio
    asyncio.run(test_websocket_connection_with_retry())