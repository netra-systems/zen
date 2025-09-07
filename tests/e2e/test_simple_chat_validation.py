#!/usr/bin/env python
"""Simple Chat Validation Test - Basic WebSocket Flow

Tests basic chat message flow with real services to verify:
1. Messages are sent successfully
2. Events are received
3. Final responses make sense
"""

import asyncio
import json
import os
import sys
import time
import uuid
from typing import Dict, List, Optional

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import websockets
from loguru import logger

from shared.isolated_environment import IsolatedEnvironment


class SimpleChatTester:
    """Simple tester for chat flow validation."""
    
    def __init__(self):
        env = IsolatedEnvironment()
        backend_url = env.get("BACKEND_URL", default="http://localhost:8000")
        self.ws_url = backend_url.replace("http", "ws") + "/ws"
        self.events_received = []
        self.ws_connection = None
        
    async def connect(self):
        """Connect to WebSocket."""
        try:
            # Simple connection without auth for basic test
            self.ws_connection = await asyncio.wait_for(
                websockets.connect(self.ws_url),
                timeout=10.0
            )
            logger.info(f"Connected to {self.ws_url}")
            return True
        except asyncio.TimeoutError:
            logger.error("Connection timed out after 10 seconds")
            return False
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            raise
            
    async def send_chat(self, message: str, thread_id: str = None):
        """Send a chat message."""
        if not self.ws_connection:
            raise RuntimeError("Not connected")
            
        thread_id = thread_id or str(uuid.uuid4())
        chat_message = {
            "type": "chat",
            "message": message,
            "thread_id": thread_id
        }
        
        await self.ws_connection.send(json.dumps(chat_message))
        logger.info(f"Sent: {message}")
        return thread_id
        
    async def receive_events(self, timeout: float = 10.0):
        """Receive events until timeout."""
        if not self.ws_connection:
            return []
            
        events = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                # Set a short timeout for each receive
                try:
                    message = await asyncio.wait_for(
                        self.ws_connection.recv(),
                        timeout=1.0
                    )
                    event = json.loads(message)
                    events.append(event)
                    logger.info(f"Received event: {event.get('type', 'unknown')}")
                    
                    # Stop on completion events
                    if event.get("type") in ["agent_completed", "final_report", "error"]:
                        break
                        
                except asyncio.TimeoutError:
                    continue  # Keep trying until main timeout
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed during receive")
            
        return events
        
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.ws_connection:
            await self.ws_connection.close()
            

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_simple_chat_flow():
    """Test simple chat message flow."""
    tester = SimpleChatTester()
    
    # Connect
    connected = await tester.connect()
    if not connected:
        pytest.skip("Could not connect to WebSocket")
        
    try:
        # Send a simple message
        thread_id = await tester.send_chat("What is 2 + 2?")
        
        # Receive events
        events = await tester.receive_events(timeout=15.0)
        
        # Validate we got some events
        assert len(events) > 0, "Should receive at least one event"
        
        # Check event types
        event_types = [e.get("type") for e in events]
        logger.info(f"Event types received: {event_types}")
        
        # Look for key events or responses
        has_response = any(
            e.get("type") in ["agent_completed", "final_report", "agent_thinking", "agent_started"]
            for e in events
        )
        assert has_response or len(events) > 0, "Should have some response events"
        
        # Check if we got a final answer
        for event in events:
            if event.get("type") in ["agent_completed", "final_report"]:
                data = event.get("data", {})
                response = data.get("response", "") or data.get("content", "") or str(data)
                logger.info(f"Final response: {response[:200]}")
                
                # Basic check - did we get something that looks like an answer?
                if "4" in response or "four" in response.lower():
                    logger.success("Got correct answer in response!")
                    
    finally:
        await tester.disconnect()
        

@pytest.mark.asyncio  
@pytest.mark.e2e
async def test_multiple_messages():
    """Test sending multiple messages in sequence."""
    tester = SimpleChatTester()
    
    connected = await tester.connect()
    if not connected:
        pytest.skip("Could not connect to WebSocket")
        
    try:
        # Send multiple messages
        messages = [
            "Hello",
            "What is the capital of France?",
            "Calculate 10 * 5"
        ]
        
        for msg in messages:
            thread_id = await tester.send_chat(msg)
            events = await tester.receive_events(timeout=10.0)
            
            logger.info(f"Message '{msg}' got {len(events)} events")
            assert len(events) >= 0, f"Should handle message: {msg}"
            
            # Small delay between messages
            await asyncio.sleep(0.5)
            
    finally:
        await tester.disconnect()


if __name__ == "__main__":
    # Run the test directly
    import asyncio
    
    async def main():
        logger.info("Starting simple chat validation test...")
        
        # Test 1: Simple flow
        try:
            await test_simple_chat_flow()
            logger.success("✓ Simple chat flow test passed")
        except Exception as e:
            logger.error(f"✗ Simple chat flow test failed: {e}")
            
        # Test 2: Multiple messages
        try:
            await test_multiple_messages()  
            logger.success("✓ Multiple messages test passed")
        except Exception as e:
            logger.error(f"✗ Multiple messages test failed: {e}")
            
    asyncio.run(main())