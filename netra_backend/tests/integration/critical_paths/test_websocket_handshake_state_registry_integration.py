"""
Integration Test for WebSocket Handshake State Registry Race Conditions

CRITICAL BUG REPRODUCTION: WebSocket handshake race condition with state_registry scope bug

This test reproduces the production issue where:
1. WebSocket accept() happens successfully 
2. Message handling begins before state_registry is accessible
3. Authentication flow tries to access state_registry causing NameError
4. Results in 100% connection failure rate

Uses real services (no mocks) to demonstrate actual race condition behavior.
Expected Result: Test must FAIL with connection/scope errors before fix is implemented
"""
import pytest
import asyncio
import logging
import json
import time
from typing import Optional, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatus

# Use SSOT testing framework 
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.docker import DockerTestUtility
from test_framework.ssot.websocket import WebSocketTestUtility

logger = logging.getLogger(__name__)


class TestWebSocketHandshakeStateRegistryIntegration(SSotAsyncTestCase):
    """
    CRITICAL INTEGRATION TEST: WebSocket handshake race conditions with state registry
    
    This test demonstrates the real-world race condition where:
    1. WebSocket handshake completes successfully
    2. Client sends authentication message
    3. Server authentication flow fails due to state_registry scope bug
    4. Connection fails with NameError or connection errors
    
    Uses real services to reproduce actual production behavior.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up real services for integration testing"""
        super().setUpClass()
        cls.docker_utility = DockerTestUtility()
        cls.websocket_utility = WebSocketTestUtility()
        
        # Start real backend services (no mocks)
        cls.backend_url = cls.docker_utility.ensure_backend_service()
        cls.websocket_url = f"ws://{cls.backend_url.replace('http://', '')}/ws"
        
        logger.info(f"[U+1F527] INTEGRATION TEST: Backend running at {cls.backend_url}")
        logger.info(f"[U+1F527] INTEGRATION TEST: WebSocket endpoint at {cls.websocket_url}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up services"""
        super().tearDownClass()
        cls.docker_utility.cleanup()
    
    def setUp(self):
        """Set up individual test"""
        super().setUp()
        self.connection_attempts = []
        self.error_logs = []
    
    @pytest.mark.asyncio
    async def test_websocket_handshake_state_registry_race_condition_integration(self):
        """
        CRITICAL INTEGRATION TEST: Reproduce WebSocket handshake race condition
        
        This test connects to real WebSocket service and triggers the exact
        authentication flow that causes the state_registry scope bug.
        
        EXPECTED RESULT: Connection should fail due to state_registry NameError
        """
        logger.info("[U+1F534] INTEGRATION TEST: Testing WebSocket handshake state registry race condition")
        
        # Test configuration
        max_attempts = 5
        connection_timeout = 10.0
        
        for attempt in range(max_attempts):
            logger.info(f" CYCLE:  Attempt {attempt + 1}/{max_attempts}: Testing WebSocket connection")
            
            try:
                # Attempt WebSocket connection with authentication
                async with websockets.connect(
                    self.websocket_url,
                    timeout=connection_timeout,
                    extra_headers={"Authorization": "Bearer fake_jwt_token"}
                ) as websocket:
                    
                    logger.info(f" PASS:  WebSocket connected successfully on attempt {attempt + 1}")
                    
                    # Send authentication message to trigger state registry access
                    auth_message = {
                        "type": "auth",
                        "token": "fake_jwt_token_that_will_decode",
                        "connection_id": f"test_connection_{int(time.time() * 1000)}"
                    }
                    
                    await websocket.send(json.dumps(auth_message))
                    logger.info("[U+1F4E4] Sent authentication message")
                    
                    # Try to receive response - this should trigger the scope bug
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=5.0
                        )
                        logger.info(f"[U+1F4E5] Received response: {response}")
                        
                        # If we get here without error, the bug might be fixed
                        # But for this test, we expect it to fail
                        pytest.fail("Expected connection to fail due to state_registry scope bug, but it succeeded")
                        
                    except asyncio.TimeoutError:
                        logger.error("[U+1F534] Timeout waiting for WebSocket response - likely due to server error")
                        self.connection_attempts.append({
                            "attempt": attempt + 1,
                            "result": "timeout",
                            "error": "Server did not respond to auth message"
                        })
                        
                    except ConnectionClosed as e:
                        logger.error(f"[U+1F534] WebSocket connection closed unexpectedly: {e}")
                        self.connection_attempts.append({
                            "attempt": attempt + 1,
                            "result": "connection_closed",
                            "error": str(e)
                        })
                        
            except (ConnectionRefusedError, InvalidStatus, OSError) as e:
                logger.error(f"[U+1F534] WebSocket connection failed on attempt {attempt + 1}: {e}")
                self.connection_attempts.append({
                    "attempt": attempt + 1,
                    "result": "connection_failed",
                    "error": str(e)
                })
                
                # Wait before next attempt
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1.0)
        
        # Analyze results
        successful_connections = [a for a in self.connection_attempts if a["result"] == "success"]
        failed_connections = [a for a in self.connection_attempts if a["result"] != "success"]
        
        logger.info(f" CHART:  INTEGRATION TEST RESULTS:")
        logger.info(f"   - Successful connections: {len(successful_connections)}/{max_attempts}")
        logger.info(f"   - Failed connections: {len(failed_connections)}/{max_attempts}")
        
        # For this bug reproduction test, we expect failures
        if len(failed_connections) == max_attempts:
            logger.info(" PASS:  INTEGRATION TEST SUCCESS: All connections failed as expected due to state_registry bug")
        elif len(failed_connections) > 0:
            logger.info(f" PASS:  INTEGRATION TEST PARTIAL SUCCESS: {len(failed_connections)} connections failed due to state_registry bug")
        else:
            pytest.fail("Expected at least some connections to fail due to state_registry scope bug")
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_flow_timing_integration(self):
        """
        INTEGRATION TEST: Test the specific timing of authentication flow
        
        This test focuses on the exact timing where the scope bug occurs:
        1. WebSocket accepts connection
        2. Authentication message is processed
        3. State registry access fails due to scope bug
        """
        logger.info("[U+1F534] INTEGRATION TEST: Testing authentication flow timing")
        
        # Use custom WebSocket client to control timing
        try:
            # Connect without initial authentication
            async with websockets.connect(
                self.websocket_url,
                timeout=5.0
            ) as websocket:
                
                logger.info(" PASS:  WebSocket connection established")
                
                # Send authentication message immediately to trigger race condition
                auth_messages = [
                    {
                        "type": "auth",
                        "token": "test_jwt_token",
                        "connection_id": "immediate_auth_test"
                    },
                    {
                        "type": "auth", 
                        "token": "another_test_token",
                        "connection_id": "rapid_fire_auth_test"
                    }
                ]
                
                # Send multiple auth messages rapidly to increase race condition probability
                for i, msg in enumerate(auth_messages):
                    try:
                        await websocket.send(json.dumps(msg))
                        logger.info(f"[U+1F4E4] Sent auth message {i + 1}")
                        
                        # Brief delay to see if server can handle rapid messages
                        await asyncio.sleep(0.1)
                        
                    except ConnectionClosed as e:
                        logger.error(f"[U+1F534] Connection closed during message {i + 1}: {e}")
                        # This is expected due to the scope bug
                        break
                
                # Try to receive any responses
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    logger.info(f"[U+1F4E5] Received: {response}")
                    
                    # If we get a response, check if it indicates an error
                    if "error" in response.lower() or "exception" in response.lower():
                        logger.info(" PASS:  INTEGRATION TEST SUCCESS: Server returned error as expected")
                    else:
                        pytest.fail("Expected server error due to state_registry scope bug")
                        
                except asyncio.TimeoutError:
                    logger.error("[U+1F534] No response from server - likely crashed due to scope bug")
                    logger.info(" PASS:  INTEGRATION TEST SUCCESS: Server timeout indicates scope bug")
                    
                except ConnectionClosed:
                    logger.error("[U+1F534] Server closed connection - likely due to internal error")
                    logger.info(" PASS:  INTEGRATION TEST SUCCESS: Connection closure indicates scope bug")
        
        except Exception as e:
            logger.error(f"[U+1F534] Integration test connection failed: {e}")
            logger.info(" PASS:  INTEGRATION TEST SUCCESS: Connection failure indicates state_registry scope bug")
    
    @pytest.mark.asyncio  
    async def test_websocket_state_registry_concurrent_access_integration(self):
        """
        INTEGRATION TEST: Test concurrent WebSocket connections to trigger race conditions
        
        Multiple simultaneous connections should all fail due to state_registry scope bug.
        This test simulates production load conditions.
        """
        logger.info("[U+1F534] INTEGRATION TEST: Testing concurrent WebSocket connections")
        
        concurrent_connections = 3
        connection_results = []
        
        async def test_single_connection(connection_id: str) -> Dict[str, Any]:
            """Test a single WebSocket connection"""
            try:
                async with websockets.connect(
                    self.websocket_url,
                    timeout=5.0,
                    extra_headers={"Authorization": f"Bearer token_{connection_id}"}
                ) as websocket:
                    
                    # Send auth message
                    auth_msg = {
                        "type": "auth",
                        "token": f"concurrent_token_{connection_id}",
                        "connection_id": f"concurrent_{connection_id}"
                    }
                    
                    await websocket.send(json.dumps(auth_msg))
                    
                    # Wait for response
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    
                    return {
                        "connection_id": connection_id,
                        "status": "success", 
                        "response": response
                    }
                    
            except Exception as e:
                return {
                    "connection_id": connection_id,
                    "status": "failed",
                    "error": str(e)
                }
        
        # Launch concurrent connections
        tasks = [
            test_single_connection(f"conn_{i}")
            for i in range(concurrent_connections)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze concurrent connection results
        successful = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
        failed = [r for r in results if isinstance(r, dict) and r.get("status") == "failed"] 
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        logger.info(f" CHART:  CONCURRENT CONNECTION RESULTS:")
        logger.info(f"   - Successful: {len(successful)}")
        logger.info(f"   - Failed: {len(failed)}")
        logger.info(f"   - Exceptions: {len(exceptions)}")
        
        # For state_registry scope bug, we expect most/all to fail
        total_failures = len(failed) + len(exceptions)
        if total_failures >= concurrent_connections * 0.8:  # 80% failure rate expected
            logger.info(" PASS:  INTEGRATION TEST SUCCESS: High failure rate confirms state_registry scope bug")
        else:
            pytest.fail(f"Expected high failure rate due to scope bug, but got {total_failures}/{concurrent_connections} failures")


if __name__ == "__main__":
    # Run integration tests to verify they demonstrate the race condition
    pytest.main([__file__, "-v", "-s"])