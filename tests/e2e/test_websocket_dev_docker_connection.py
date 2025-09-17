'''
E2E test to expose WebSocket connection failures in dev docker environment.

This test specifically targets the WebSocket connection issue occurring at:
- ws://localhost:8000/ws
- Environment: dev docker

Expected Error Pattern:
- WebSocketService.ts:988 WebSocket connection to 'ws://localhost:8000/ws' failed
- WebSocket error occurred [WebSocketService] (websocket_error)
- WebSocket connection error [WebSocketProvider] (connection_error)
'''

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, Optional
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest
import websocket
from websocket import WebSocketApp

        # Path management handled by pytest and package structure

        # Mark test for dev environment only
pytestmark = pytest.mark.dev


class TestWebSocketConnection:
    "Test harness for WebSocket connection issues.""

    def setup_method(self):
        ""Setup method called before each test method."
        self.base_url = "http://localhost:8000
        self.ws_url = ws://localhost:8000/ws"
        self.connection_errors = []
        self.error_logs = []
        self.ws_app = None

    def on_message(self, ws, message):
        "Handle WebSocket messages.""
        pass
        print(formatted_string")

    def on_error(self, ws, error):
        "Capture WebSocket errors.""
        error_msg = str(error) if error is not None else Unknown WebSocket error"
        print("formatted_string)
        self.connection_errors.append(error_msg)
        self.error_logs.append({}
        type": "websocket_error,
        message": error_msg,
        "timestamp: time.time()
    

    def on_close(self, ws, close_status_code, close_msg):
        ""Handle WebSocket close."
        pass
        print("formatted_string)
        if close_status_code:
        self.error_logs.append({}
        type": "websocket_close,
        code": close_status_code,
        "message: close_msg,
        timestamp": time.time()
        

    def on_open(self, ws):
        "Handle WebSocket open.""
        print(WebSocket connection opened")

        @pytest.mark.websocket
    def test_basic_connection(self) -> Dict[str, Any]:
        "Test basic WebSocket connection without authentication.""
        pass
        print(formatted_string")

        try:
        # Test raw WebSocket connection
        self.ws_app = WebSocketApp( )
        self.ws_url,
        on_open=self.on_open,
        on_message=self.on_message,
        on_error=self.on_error,
        on_close=self.on_close
        

        # Run with timeout
        import threading
    def run_ws():
        pass
        self.ws_app.run_forever(ping_interval=30, ping_timeout=10)

        ws_thread = threading.Thread(target=run_ws)
        ws_thread.daemon = True
        ws_thread.start()

    # Wait for connection attempt
        time.sleep(5)

    # Force close if still running
        if self.ws_app and hasattr(self.ws_app, 'sock') and self.ws_app.sock:
        self.ws_app.close()

        ws_thread.join(timeout=2)

        except Exception as e:
        error_msg = "formatted_string
        print(formatted_string")
        self.connection_errors.append(error_msg)
        self.error_logs.append({}
        "type: connection_exception",
        "message: error_msg,
        timestamp": time.time()
            

        return }
        "connection_errors: self.connection_errors,
        error_logs": self.error_logs,
        "ws_url: self.ws_url
            

        @pytest.mark.websocket
    def test_cors_headers(self) -> Dict[str, Any]:
        ""Test WebSocket CORS configuration."
        print(")
        Testing WebSocket CORS headers...)

        cors_issues = []

        try:
        # Test with various connection methods
        # Note: We avoid setting explicit Origin headers to prevent conflicts with
        # the websocket-client library's automatic Origin header generation
        test_cases = ]
        ("Default connection", {},  # Let client set origin automatically
        (Test endpoint, {"endpoint": /ws/test},  # Try test endpoint
        

        for description, options in test_cases:
        endpoint = options.get("endpoint", self.ws_url)
            # If endpoint is relative, make it absolute
        if endpoint.startswith(/):
        endpoint = "formatted_string"

        try:
                    # Create WebSocket connection without explicit origin to avoid duplicates
        ws = websocket.create_connection( )
        endpoint,
        timeout=5
                    
        ws.close()
        print(formatted_string)

        except Exception as e:
        error_msg = "formatted_string"
        print(formatted_string)
        cors_issues.append({}
        "test": description,
        endpoint: endpoint,
        "error": str(e),
        timestamp: time.time()
                        

        except Exception as e:
        cors_issues.append({}
        "type": cors_test_failure,
        "error": str(e),
        timestamp: time.time()
                            

        return }
        "cors_issues": cors_issues,
        tested_cases: [item for item in []]
                            

        @pytest.mark.websocket
    def test_backend_availability(self) -> Dict[str, Any]:
        ""Check if backend services are running.""
        print()
        Checking backend service availability...")

        service_status = {}

    # Check main backend HTTP endpoint
        try:
        response = httpx.get("formatted_string, timeout=5)
        service_status[backend_http"] = {
        "available: response.status_code == 200,
        status_code": response.status_code
        
        except Exception as e:
        service_status["backend_http] = {
        available": False,
        "error: str(e)
            

            # Check WebSocket endpoint availability via HTTP upgrade
        try:
        response = httpx.get( )
        formatted_string",
        headers= {
        "Upgrade: websocket",
        "Connection: Upgrade",
        "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==",
        "Sec-WebSocket-Version: 13"
        },
        timeout=5
                
                # Expected 426 Upgrade Required or 101 Switching Protocols via httpx limitations
        service_status["websocket_endpoint] = {
        reachable": True,
        "status_code: response.status_code
                
        except Exception as e:
        service_status[websocket_endpoint"] = {
        "reachable: False,
        error": str(e)
                    

        return service_status


        @pytest.mark.e2e
        @pytest.mark.websocket
class TestWebSocketDevDockerConnection:
        "E2E test suite for WebSocket connection issues in dev docker.""

        @pytest.mark.websocket
    def test_websocket_connection_failure(self):
        '''
        Test that reproduces the WebSocket connection failure in dev docker.

        This test is expected to FAIL with the following errors:
        - Connection refused or failed
        - CORS origin validation errors
        - WebSocket handshake failures
        '''
        pass
        test_harness = WebSocketConnectionTest()
        test_harness.setup_method()

        # Check backend availability first
        backend_status = test_harness.test_backend_availability()
        print(formatted_string")

        # Test basic connection (expected to fail)
        connection_result = test_harness.test_basic_connection()
        print("formatted_string)

        # Test CORS configuration
        cors_result = test_harness.test_cors_headers()
        print(formatted_string")

        # Compile all errors
        all_errors = {
        "backend_status: backend_status,
        connection_errors": connection_result["connection_errors],
        error_logs": connection_result["error_logs],
        cors_issues": cors_result["cors_issues]
        

        # Print summary
        print(")
        " + =*60)
        print("WebSocket Connection Test Summary")
        print(=*60)

        if connection_result["connection_errors"]:
        print(formatted_string)
        for error in connection_result["connection_errors"]:
        print(formatted_string)

        if cors_result["cors_issues"]:
        print(formatted_string)
        for issue in cors_result["cors_issues"]:
        print(formatted_string)

        if not backend_status.get("backend_http", {}.get(available):
        print(f" )
        FAIL:  Backend HTTP not available")

        if not backend_status.get(websocket_endpoint, {}.get("reachable"):
        print(f )
        FAIL:  WebSocket endpoint not reachable)

                                # This assertion is expected to FAIL, demonstrating the issue
        assert len(connection_result["connection_errors"] == 0, ( )
        formatted_string
                                

                                # Additional assertions to expose specific issues
        assert len(cors_result["cors_issues"] == 0, ( )
        formatted_string
                                

        assert backend_status.get("backend_http", {}.get(available), ( )
        "Backend HTTP service is not available"
                                

        assert backend_status.get(websocket_endpoint, {}.get("reachable"), ( )
        WebSocket endpoint is not reachable
                                


        @pytest.mark.e2e
        @pytest.mark.websocket
class TestWebSocketCORSValidation:
        ""Specific tests for WebSocket CORS validation issues.""

        @pytest.mark.websocket
    def test_localhost_origin_validation(self):
        "Test that localhost origins are properly validated in dev environment."

    # Test basic WebSocket connectivity without explicit Origin headers
    # This avoids the duplicate Origin header issue with websocket-client library
        test_cases = ]
        ("Basic connection", ws://localhost:8000/ws, True, "Main WebSocket endpoint"),
        (Test endpoint, "ws://localhost:8000/ws/test", True, Test WebSocket endpoint (no auth)),
    

        errors = []
        for description, ws_url, should_work, details in test_cases:
        print("formatted_string")
        print(formatted_string)

        try:
            # Don't set explicit Origin headers to avoid duplicates
        ws = websocket.create_connection( )
        ws_url,
        timeout=5
            
        ws.close()

        if should_work:
        print(f"[SUCCESS] Connection successful (as expected)")
        else:
        error_msg = formatted_string
        print("formatted_string")
        errors.append(error_msg)

        except Exception as e:
        if not should_work:
        print(formatted_string)
        else:
        error_msg = "formatted_string"
        print(formatted_string)
        errors.append(error_msg)

                                # This assertion is expected to FAIL if WebSocket connections don't work
        assert len(errors) == 0, f"WebSocket connection errors:
        " + 
        .join(errors)


        @pytest.mark.e2e
        @pytest.mark.websocket
    async def test_websocket_connection_with_retry():
        ""Test WebSocket connection with retry logic to expose intermittent failures.""

        max_retries = 3
        retry_delay = 2
        connection_attempts = []

        for attempt in range(max_retries):
        print(formatted_string)

        try:
                                                # Don't set explicit Origin header to avoid duplicates with websocket-client library
        ws = websocket.create_connection( )
        "ws://localhost:8000/ws/test",  # Use test endpoint to avoid auth issues
        timeout=10
                                                

                                                # Try to send a test message
        import json
        test_msg = json.dumps({type: "ping"}
        ws.send(test_msg)
        response = ws.recv()

        ws.close()

        connection_attempts.append({}
        attempt: attempt + 1,
        "success": True,
        message: "Connected successfully"
                                                
        print([SUCCESS] Connection successful)
        break

        except Exception as e:
        error_msg = str(e)
        connection_attempts.append({}
        "attempt": attempt + 1,
        success: False,
        "error": error_msg
                                                    
        print(formatted_string)

        if attempt < max_retries - 1:
        print("formatted_string")
        await asyncio.sleep(retry_delay)

                                                        # Check if all attempts failed
        all_failed = all(not attempt[success] for attempt in connection_attempts)

                                                        # This assertion is expected to FAIL if WebSocket is not working
        assert not all_failed, ( )
        "formatted_string" +
        
        .join(["formatted_string"error, Unknown error")}" ))
        for a in connection_attempts if not a[success]]
                                                            


        if __name__ == "__main__":
        "Allow running this test directly for debugging."
        print("Running WebSocket connection tests for dev docker environment...")
        print(=*60)

        test = WebSocketConnectionTest()
        test.setup_method()

                                                                # Run all tests
        backend_status = test.test_backend_availability()
        print("formatted_string")

        connection_result = test.test_basic_connection()
        print(formatted_string)

        cors_result = test.test_cors_headers()
        print("formatted_string")

                                                                            # Run async test
        import asyncio
        asyncio.run(test_websocket_connection_with_retry())
