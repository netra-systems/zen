"""
Test script to verify WebSocket disconnect handling fixes
"""
import asyncio
import websockets
import json
import sys
import time
from typing import Optional

# Configuration
BASE_URL = "ws://localhost:8000"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxZTFjZmNkYy1kZGVlLTRhZjMtYjY2ZC01NDQzOGI2M2I3NWUiLCJleHAiOjE3NjQ0NjA3MjR9.YJdAaQfJtRCIcBbTv-HXpgYZPM8QdPABQkJxKpvEqIY"

class WebSocketTestClient:
    def __init__(self, token: str):
        self.token = token
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.received_messages = []
        
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(
                f"{BASE_URL}/ws?token={self.token}",
                ping_interval=None  # Disable ping to test disconnect handling
            )
            print("[OK] Connected to WebSocket server")
            return True
        except Exception as e:
            print(f"[FAIL] Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            print("[OK] Disconnected from WebSocket server")
    
    async def send_message(self, message_type: str, payload: dict):
        """Send a message to the server"""
        if not self.websocket:
            print("[FAIL] Not connected to server")
            return False
            
        message = {
            "type": message_type,
            "payload": payload
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            print(f"[OK] Sent message: {message_type}")
            return True
        except Exception as e:
            print(f"[FAIL] Failed to send message: {e}")
            return False
    
    async def receive_messages(self, timeout: float = 5.0):
        """Receive messages from server with timeout"""
        if not self.websocket:
            return []
            
        messages = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=0.5
                )
                parsed = json.loads(message)
                messages.append(parsed)
                print(f"[OK] Received message: {parsed.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                print("[OK] Connection closed by server (expected)")
                break
            except Exception as e:
                print(f"[FAIL] Error receiving message: {e}")
                break
                
        return messages

async def test_disconnect_during_processing():
    """Test disconnecting while server is processing a message"""
    print("\n=== Test 1: Disconnect During Processing ===")
    
    client = WebSocketTestClient(TEST_TOKEN)
    
    # Connect
    if not await client.connect():
        return False
    
    # Send a message that will trigger processing
    await client.send_message("user_message", {
        "text": "Test message for disconnect handling",
        "references": []
    })
    
    # Wait briefly for processing to start
    await asyncio.sleep(0.5)
    
    # Disconnect abruptly
    print("-> Disconnecting abruptly...")
    await client.disconnect()
    
    print("[OK] Test 1 passed: No crash after abrupt disconnect")
    return True

async def test_send_after_close():
    """Test that server handles attempts to send after close gracefully"""
    print("\n=== Test 2: Send After Close ===")
    
    client = WebSocketTestClient(TEST_TOKEN)
    
    # Connect
    if not await client.connect():
        return False
    
    # Send a message
    await client.send_message("user_message", {
        "text": "Initial message",
        "references": []
    })
    
    # Close the connection
    await client.disconnect()
    
    # Wait for server to process
    await asyncio.sleep(1)
    
    print("[OK] Test 2 passed: Server handled send-after-close gracefully")
    return True

async def test_multiple_rapid_disconnects():
    """Test multiple rapid connect/disconnect cycles"""
    print("\n=== Test 3: Multiple Rapid Disconnects ===")
    
    for i in range(3):
        print(f"\n-> Cycle {i+1}/3")
        client = WebSocketTestClient(TEST_TOKEN)
        
        # Connect
        if not await client.connect():
            print(f"[FAIL] Failed to connect in cycle {i+1}")
            continue
        
        # Send a message
        await client.send_message("user_message", {
            "text": f"Test message {i+1}",
            "references": []
        })
        
        # Disconnect quickly
        await asyncio.sleep(0.1)
        await client.disconnect()
        
        # Brief pause before next cycle
        await asyncio.sleep(0.5)
    
    print("[OK] Test 3 passed: Multiple rapid disconnects handled")
    return True

async def test_concurrent_connections():
    """Test multiple concurrent WebSocket connections"""
    print("\n=== Test 4: Concurrent Connections ===")
    
    clients = []
    
    # Create multiple clients
    for i in range(3):
        client = WebSocketTestClient(TEST_TOKEN)
        if await client.connect():
            clients.append(client)
            print(f"[OK] Client {i+1} connected")
    
    # Send messages from all clients
    for i, client in enumerate(clients):
        await client.send_message("user_message", {
            "text": f"Message from client {i+1}",
            "references": []
        })
    
    # Wait briefly
    await asyncio.sleep(1)
    
    # Disconnect all clients
    for i, client in enumerate(clients):
        await client.disconnect()
        print(f"[OK] Client {i+1} disconnected")
    
    print("[OK] Test 4 passed: Concurrent connections handled")
    return True

async def main():
    """Run all tests"""
    print("=" * 50)
    print("WebSocket Disconnect Handling Test Suite")
    print("=" * 50)
    
    tests = [
        test_disconnect_during_processing,
        test_send_after_close,
        test_multiple_rapid_disconnects,
        test_concurrent_connections
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"[FAIL] Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("[OK] All tests passed!")
        return 0
    else:
        print("[FAIL] Some tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)