"""

End-to-end tests for WebSocket immediate disconnect regression prevention.



These tests verify the complete WebSocket connection lifecycle works correctly,

preventing the "Loading chat..." issue where connections immediately disconnect

with ABNORMAL_CLOSURE (1006).



To verify these tests catch the regression:

1. Break either the state checking or subprotocol negotiation

2. These tests should fail with connection closing immediately

3. Restore both fixes

4. Tests should pass with stable connections

"""



import pytest

import asyncio

import json

import time

import websockets

from websockets.exceptions import ConnectionClosed, WebSocketException

import httpx

from typing import Optional, Dict, Any

import logging

from shared.isolated_environment import IsolatedEnvironment



# Setup logging to capture connection issues

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)





class TestWebSocketImmediateDisconnectRegression:

    """E2E tests to prevent regression of immediate disconnect bug."""

    

    @pytest.fixture

    def backend_url(self):

        """Get backend WebSocket URL."""

        return "ws://localhost:8000/ws"

    

    @pytest.fixture

    @pytest.mark.websocket

    @pytest.mark.e2e

    def test_token(self):

        """Get a test JWT token."""

        # This is a dev token that should work in development mode

        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdGVtcC10ZXN0IiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzU2NDE5MzY5LCJpYXQiOjE3MjQ3OTczNjkifQ.test"

    

    @pytest.mark.asyncio

    @pytest.mark.timeout(30)

    async def test_websocket_must_not_immediately_disconnect(self, backend_url, test_token):

        """

        REGRESSION TEST: WebSocket must stay connected, not immediately disconnect.

        This is the primary symptom users experienced - immediate ABNORMAL_CLOSURE.

        """

        connection_start = time.time()

        connection_duration = 0

        disconnect_code = None

        messages_received = []

        

        try:

            # Connect with subprotocols (like the frontend does)

            async with websockets.connect(

                backend_url,

                subprotocols=["jwt-auth", f"jwt.{test_token}"],

                additional_headers={

                    "Authorization": f"Bearer {test_token}"

                }

            ) as websocket:

                logger.info("WebSocket connected successfully")

                

                # Connection established - should stay open

                connection_duration = time.time() - connection_start

                assert connection_duration < 1.0, \

                    "Connection took too long to establish"

                

                # Should receive welcome message

                try:

                    welcome = await asyncio.wait_for(websocket.recv(), timeout=2.0)

                    messages_received.append(welcome)

                    logger.info(f"Received welcome message: {welcome[:100]}")

                except asyncio.TimeoutError:

                    logger.warning("No welcome message received")

                

                # Send a test message

                test_message = json.dumps({

                    "type": "ping",

                    "id": "test-1",

                    "timestamp": time.time()

                })

                await websocket.send(test_message)

                logger.info("Sent test message")

                

                # Should be able to receive response or stay connected

                try:

                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)

                    messages_received.append(response)

                    logger.info(f"Received response: {response[:100]}")

                except asyncio.TimeoutError:

                    # Timeout is OK - connection is still open

                    pass

                

                # Connection should still be open

                assert websocket.open, "WebSocket closed prematurely"

                

                # Measure how long connection stays open

                await asyncio.sleep(1.0)

                connection_duration = time.time() - connection_start

                

                # Should stay connected for at least 1 second

                assert connection_duration >= 1.0, \

                    f"Connection closed too quickly: {connection_duration}s"

                

        except ConnectionClosed as e:

            disconnect_code = e.code

            connection_duration = time.time() - connection_start

            logger.error(f"Connection closed with code {e.code}: {e.reason}")

            

            # CRITICAL: Should NOT close with ABNORMAL_CLOSURE (1006) immediately

            assert e.code != 1006 or connection_duration > 0.5, \

                f"REGRESSION: Immediate ABNORMAL_CLOSURE (1006) after {connection_duration}s - the exact bug!"

            

            # Also should not close with policy violation (1008) from missing subprotocol

            assert e.code != 1008, \

                "Connection closed with policy violation - subprotocol negotiation failed"

        

        # Verify connection was stable

        assert connection_duration >= 1.0, \

            f"Connection only lasted {connection_duration}s - should stay open longer"

        assert disconnect_code != 1006, \

            f"Connection closed with ABNORMAL_CLOSURE - indicates state/subprotocol issue"

    

    @pytest.mark.asyncio

    @pytest.mark.timeout(30)

    async def test_websocket_with_frontend_like_subprotocols(self, backend_url, test_token):

        """

        REGRESSION TEST: Test with exact subprotocols the frontend sends.

        Frontend sends: jwt-auth, jwt.<token>, sometimes compression protocols.

        """

        # Simulate exact frontend behavior

        encoded_token = test_token.replace('+', '-').replace('/', '_').replace('=', '')

        subprotocols = ["jwt-auth", f"jwt.{encoded_token}"]

        

        connection_stable = False

        selected_subprotocol = None

        

        try:

            async with websockets.connect(

                backend_url,

                subprotocols=subprotocols,

                additional_headers={

                    "Authorization": f"Bearer {test_token}",

                    "Origin": "http://localhost:3000"  # Frontend origin

                }

            ) as websocket:

                # Check which subprotocol was selected

                selected_subprotocol = websocket.subprotocol

                logger.info(f"Server selected subprotocol: {selected_subprotocol}")

                

                # CRITICAL: Server must select one of our subprotocols

                assert selected_subprotocol in ["jwt-auth", None], \

                    f"Server selected unexpected subprotocol: {selected_subprotocol}"

                

                # If we sent subprotocols, server should select one

                if subprotocols:

                    assert selected_subprotocol == "jwt-auth", \

                        "Server didn't select jwt-auth subprotocol when client requested it"

                

                # Stay connected for a bit

                await asyncio.sleep(0.5)

                connection_stable = websocket.open

                

        except ConnectionClosed as e:

            if e.code == 1006 and time.time() - start_time < 0.1:

                pytest.fail(f"REGRESSION: Immediate disconnect with 1006 - subprotocol issue")

        

        assert connection_stable, "Connection was not stable"

        assert selected_subprotocol == "jwt-auth", \

            "Subprotocol negotiation failed - would cause frontend disconnect"

    

    @pytest.mark.asyncio

    @pytest.mark.timeout(30)

    async def test_websocket_message_exchange(self, backend_url, test_token):

        """

        REGRESSION TEST: Full message exchange must work.

        Tests that connection stays open long enough for bidirectional communication.

        """

        messages_sent = 0

        messages_received = 0

        

        try:

            async with websockets.connect(

                backend_url,

                subprotocols=["jwt-auth"],

                additional_headers={"Authorization": f"Bearer {test_token}"}

            ) as websocket:

                # Send multiple messages

                for i in range(3):

                    message = json.dumps({

                        "type": "test",

                        "id": f"msg-{i}",

                        "content": f"Test message {i}"

                    })

                    await websocket.send(message)

                    messages_sent += 1

                    logger.info(f"Sent message {i}")

                    

                    # Try to receive response

                    try:

                        response = await asyncio.wait_for(websocket.recv(), timeout=1.0)

                        messages_received += 1

                        logger.info(f"Received response: {response[:100]}")

                    except asyncio.TimeoutError:

                        # OK if no response, as long as connection stays open

                        pass

                    

                    await asyncio.sleep(0.1)

                

                # Connection should still be open after message exchange

                assert websocket.open, "Connection closed during message exchange"

                

        except ConnectionClosed as e:

            if e.code == 1006 and messages_sent == 0:

                pytest.fail("REGRESSION: Connection closed before any messages could be sent")

        

        assert messages_sent >= 3, f"Could only send {messages_sent} messages before disconnect"

        logger.info(f"Successfully exchanged messages: sent={messages_sent}, received={messages_received}")

    

    @pytest.mark.asyncio

    @pytest.mark.timeout(30)

    async def test_websocket_without_subprotocols(self, backend_url, test_token):

        """

        REGRESSION TEST: Connection should work even without subprotocols.

        Some clients might not send subprotocols.

        """

        try:

            # Connect without subprotocols

            async with websockets.connect(

                backend_url,

                additional_headers={"Authorization": f"Bearer {test_token}"}

            ) as websocket:

                # Should connect successfully

                assert websocket.open, "Failed to connect without subprotocols"

                

                # Should stay connected

                await asyncio.sleep(0.5)

                assert websocket.open, "Connection closed when no subprotocols sent"

                

                # No subprotocol should be selected

                assert websocket.subprotocol is None, \

                    f"Unexpected subprotocol selected: {websocket.subprotocol}"

                

        except ConnectionClosed as e:

            if e.code == 1006:

                pytest.fail("Connection rejected when no subprotocols sent")

    

    @pytest.mark.asyncio

    @pytest.mark.timeout(30)

    async def test_multiple_concurrent_websocket_connections(self, backend_url, test_token):

        """

        REGRESSION TEST: Multiple connections should work simultaneously.

        Tests that the fix works under concurrent connection load.

        """

        num_connections = 5

        connections = []

        connection_results = []

        

        async def create_connection(conn_id):

            try:

                websocket = await websockets.connect(

                    backend_url,

                    subprotocols=["jwt-auth"],

                    additional_headers={

                        "Authorization": f"Bearer {test_token}",

                        "X-Connection-ID": str(conn_id)

                    }

                )

                connections.append(websocket)

                

                # Test connection stability

                await asyncio.sleep(0.5)

                is_open = websocket.open

                

                # Close gracefully

                await websocket.close()

                

                return {"id": conn_id, "success": is_open}

                

            except ConnectionClosed as e:

                return {"id": conn_id, "success": False, "error": f"Code {e.code}"}

            except Exception as e:

                return {"id": conn_id, "success": False, "error": str(e)}

        

        # Create multiple connections concurrently

        tasks = [create_connection(i) for i in range(num_connections)]

        connection_results = await asyncio.gather(*tasks)

        

        # Check results

        successful = [r for r in connection_results if r.get("success")]

        failed = [r for r in connection_results if not r.get("success")]

        

        logger.info(f"Connections: {len(successful)} successful, {len(failed)} failed")

        for failure in failed:

            logger.error(f"Connection {failure['id']} failed: {failure.get('error')}")

        

        # Most connections should succeed

        assert len(successful) >= num_connections * 0.8, \

            f"Too many connections failed: {len(failed)}/{num_connections}"

        

        # No connection should fail with immediate 1006

        immediate_1006 = [f for f in failed if "Code 1006" in f.get("error", "")]

        assert len(immediate_1006) == 0, \

            f"REGRESSION: {len(immediate_1006)} connections had immediate ABNORMAL_CLOSURE"

    

    @pytest.mark.asyncio

    @pytest.mark.timeout(30)

    async def test_websocket_reconnection_after_disconnect(self, backend_url, test_token):

        """

        REGRESSION TEST: Reconnection should work after disconnect.

        Tests that the bug doesn't affect reconnection scenarios.

        """

        first_connection_ok = False

        second_connection_ok = False

        

        # First connection

        try:

            async with websockets.connect(

                backend_url,

                subprotocols=["jwt-auth"],

                additional_headers={"Authorization": f"Bearer {test_token}"}

            ) as websocket:

                await asyncio.sleep(0.5)

                first_connection_ok = websocket.open

                # Close gracefully

                await websocket.close()

        except ConnectionClosed as e:

            if e.code == 1006:

                pytest.fail("First connection failed with ABNORMAL_CLOSURE")

        

        # Wait a bit before reconnecting

        await asyncio.sleep(0.5)

        

        # Second connection (reconnect)

        try:

            async with websockets.connect(

                backend_url,

                subprotocols=["jwt-auth"],

                additional_headers={"Authorization": f"Bearer {test_token}"}

            ) as websocket:

                await asyncio.sleep(0.5)

                second_connection_ok = websocket.open

        except ConnectionClosed as e:

            if e.code == 1006:

                pytest.fail("Reconnection failed with ABNORMAL_CLOSURE")

        

        assert first_connection_ok, "First connection failed"

        assert second_connection_ok, "Reconnection failed"

        logger.info("Both initial connection and reconnection successful")





class TestWebSocketChatUIIntegration:

    """Test that the fix resolves the actual "Loading chat..." issue."""

    

    @pytest.mark.asyncio

    @pytest.mark.timeout(30)

    async def test_chat_ui_websocket_connection(self):

        """

        REGRESSION TEST: Simulate the exact chat UI connection flow.

        This should resolve the "Loading chat..." issue.

        """

        # This simulates what the chat UI does

        backend_url = "ws://localhost:8000/ws"

        

        # Frontend auth token (from AuthContext)

        auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdGVtcC11aSIsImVtYWlsIjoidWlAZXhhbXBsZS5jb20ifQ.test"

        

        chat_ready = False

        error_message = None

        

        try:

            # Frontend WebSocket connection with all the bells and whistles

            async with websockets.connect(

                backend_url,

                subprotocols=["jwt-auth", f"jwt.{auth_token}"],

                additional_headers={

                    "Authorization": f"Bearer {auth_token}",

                    "Origin": "http://localhost:3000",

                    "User-Agent": "Mozilla/5.0 (Chat UI Test)"

                },

                # Frontend connection parameters

                ping_interval=20,

                ping_timeout=10,

                close_timeout=10

            ) as websocket:

                logger.info("Chat UI WebSocket connected")

                

                # Wait for welcome message (chat UI expects this)

                try:

                    welcome = await asyncio.wait_for(websocket.recv(), timeout=3.0)

                    welcome_data = json.loads(welcome)

                    

                    # Chat UI checks for welcome message

                    if welcome_data.get("type") in ["welcome", "connected", "ready"]:

                        chat_ready = True

                        logger.info("Chat UI received welcome message - ready!")

                except asyncio.TimeoutError:

                    error_message = "No welcome message - chat stuck on loading"

                except json.JSONDecodeError:

                    error_message = "Invalid welcome message format"

                

                # If we got here, connection is stable

                if not error_message:

                    # Send initial chat message

                    await websocket.send(json.dumps({

                        "type": "chat.message",

                        "content": "Hello, assistant!",

                        "thread_id": "test-thread"

                    }))

                    

                    # Chat should now be interactive

                    chat_ready = True

                    

        except ConnectionClosed as e:

            if e.code == 1006:

                error_message = f"REGRESSION: Chat UI connection failed with ABNORMAL_CLOSURE - 'Loading chat...' bug!"

            else:

                error_message = f"Chat UI connection failed with code {e.code}"

        except Exception as e:

            error_message = f"Chat UI connection error: {str(e)}"

        

        # Verify chat UI would work

        assert chat_ready, f"Chat UI not ready: {error_message or 'Unknown error'}"

        assert not error_message, error_message

        logger.info("Chat UI WebSocket connection successful - no more 'Loading chat...'!")





if __name__ == "__main__":

    # Can run directly for quick testing

    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))

