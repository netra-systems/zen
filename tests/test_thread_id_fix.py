#!/usr/bin/env python3
"""
Test to verify the CLI correctly uses the backend's thread_id from handshake_response.

This test simulates the scenario where:
1. Backend sends connection_established (should be ignored for handshake)
2. Backend sends handshake_response with thread_id
3. CLI should acknowledge ONLY the handshake_response with the backend's thread_id
"""

import asyncio
import json
import websockets
from datetime import datetime, timezone


class MockBackend:
    """Mock backend server to test handshake behavior"""

    def __init__(self):
        self.received_messages = []
        self.client_acknowledged = False
        self.acknowledged_thread_id = None

    async def handler(self, websocket, path):
        """Handle WebSocket connections"""
        print("[Backend] Client connected")

        # Step 1: Send connection_established with a connection_id
        # CLI should NOT acknowledge this!
        connection_msg = {
            "type": "connection_established",
            "data": {
                "connection_id": "ws_conn_100bdd8f3a44fc72_1760038639328_20_4c253ab0",
                "user_id": "test_user"
            }
        }
        await websocket.send(json.dumps(connection_msg))
        print(f"[Backend] Sent connection_established with connection_id: {connection_msg['data']['connection_id']}")

        # Give client time to process (incorrectly if buggy)
        await asyncio.sleep(0.5)

        # Step 2: Wait for handshake_request from client
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(message)
            self.received_messages.append(data)

            if data.get("type") == "handshake_request":
                print("[Backend] Received handshake_request from client")

                # Step 3: Send handshake_response with the correct thread_id
                handshake_response = {
                    "type": "handshake_response",
                    "thread_id": "thread_cli_25_e1cf9405",  # The correct thread ID
                    "run_id": "run_abc123",
                    "message": "Handshake complete",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await websocket.send(json.dumps(handshake_response))
                print(f"[Backend] Sent handshake_response with thread_id: {handshake_response['thread_id']}")

                # Step 4: Wait for session_acknowledged
                ack_message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                ack_data = json.loads(ack_message)
                self.received_messages.append(ack_data)

                if ack_data.get("type") == "session_acknowledged":
                    self.client_acknowledged = True
                    self.acknowledged_thread_id = ack_data.get("thread_id")
                    print(f"[Backend] Received session_acknowledged with thread_id: {self.acknowledged_thread_id}")

                    # Check if it's the correct thread_id
                    if self.acknowledged_thread_id == "thread_cli_25_e1cf9405":
                        print("✅ SUCCESS: CLI acknowledged with CORRECT thread_id!")
                    elif self.acknowledged_thread_id == "ws_conn_100bdd8f3a44fc72_1760038639328_20_4c253ab0":
                        print("❌ FAILURE: CLI acknowledged with connection_id instead of thread_id!")
                    else:
                        print(f"❌ FAILURE: CLI acknowledged with unexpected ID: {self.acknowledged_thread_id}")

        except asyncio.TimeoutError:
            print("❌ FAILURE: Timeout waiting for client messages")
        except Exception as e:
            print(f"❌ FAILURE: Error in backend handler: {e}")

        # Keep connection open briefly for any additional messages
        await asyncio.sleep(1)


async def run_test():
    """Run the test"""
    backend = MockBackend()

    # Start mock backend server
    print("\n" + "="*60)
    print("Thread ID Fix Verification Test")
    print("="*60 + "\n")

    async with websockets.serve(backend.handler, "localhost", 8765):
        print("[Test] Mock backend server started on ws://localhost:8765")
        print("[Test] Waiting for CLI to connect...")
        print("[Test] Run the CLI with: python scripts/agent_cli.py --ws-url ws://localhost:8765")
        print()

        # Wait for test to complete
        await asyncio.sleep(10)

    # Print results
    print("\n" + "="*60)
    print("Test Results")
    print("="*60)

    if backend.client_acknowledged:
        if backend.acknowledged_thread_id == "thread_cli_25_e1cf9405":
            print("✅ TEST PASSED: CLI correctly used backend's thread_id")
        else:
            print(f"❌ TEST FAILED: CLI used wrong thread_id: {backend.acknowledged_thread_id}")
    else:
        print("❌ TEST FAILED: CLI did not send session_acknowledged")

    print("\nReceived messages:")
    for msg in backend.received_messages:
        print(f"  - {msg.get('type')}: {msg.get('thread_id', 'N/A')}")

    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_test())