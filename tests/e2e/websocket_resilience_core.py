"""WebSocket Resilience Test Core Module

This module provides core WebSocket testing functionality for E2E tests.
It was missing and causing import errors in conversation flow tests.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import websockets
from websockets.exceptions import WebSocketException

logger = logging.getLogger(__name__)


class WebSocketResilienceTestCore:
    """Core WebSocket test utilities for resilience testing."""
    
    def __init__(self):
        """Initialize WebSocket test core."""
        self.connection = None
        self.messages_received = []
        self.messages_sent = []
        self.is_connected = False
        self.websocket_url = "wss://api.staging.netrasystems.ai/ws"
        
    async def connect(self, url: Optional[str] = None, auth_token: Optional[str] = None) -> bool:
        """Establish WebSocket connection."""
        try:
            ws_url = url or self.websocket_url
            headers = {}
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
                
            self.connection = await websockets.connect(ws_url, extra_headers=headers)
            self.is_connected = True
            logger.info(f"Connected to WebSocket: {ws_url}")
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.is_connected = False
            return False
            
    async def disconnect(self):
        """Close WebSocket connection."""
        if self.connection:
            await self.connection.close()
            self.is_connected = False
            self.connection = None
            logger.info("WebSocket disconnected")
            
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message through WebSocket."""
        if not self.is_connected or not self.connection:
            logger.error("Cannot send message: Not connected")
            return False
            
        try:
            msg_str = json.dumps(message)
            await self.connection.send(msg_str)
            self.messages_sent.append(message)
            logger.debug(f"Sent message: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
            
    async def receive_message(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Receive message from WebSocket."""
        if not self.is_connected or not self.connection:
            logger.error("Cannot receive message: Not connected")
            return None
            
        try:
            msg_str = await asyncio.wait_for(self.connection.recv(), timeout=timeout)
            message = json.loads(msg_str)
            self.messages_received.append(message)
            logger.debug(f"Received message: {message}")
            return message
        except asyncio.TimeoutError:
            logger.warning("Receive message timeout")
            return None
        except Exception as e:
            logger.error(f"Failed to receive message: {e}")
            return None
            
    async def wait_for_event(self, event_type: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Wait for specific event type."""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            message = await self.receive_message(timeout=1.0)
            if message and message.get('type') == event_type:
                return message
                
        logger.warning(f"Timeout waiting for event: {event_type}")
        return None
        
    async def simulate_disconnect(self):
        """Simulate network disconnection."""
        if self.connection:
            await self.connection.close()
            self.is_connected = False
            logger.info("Simulated disconnect")
            
    async def simulate_reconnect(self, auth_token: Optional[str] = None) -> bool:
        """Simulate reconnection."""
        await self.disconnect()
        await asyncio.sleep(0.5)  # Brief pause before reconnect
        return await self.connect(auth_token=auth_token)
        
    def clear_messages(self):
        """Clear message history."""
        self.messages_received.clear()
        self.messages_sent.clear()
        
    def get_conversation_context(self) -> Dict[str, Any]:
        """Get current conversation context."""
        return {
            "messages_sent": len(self.messages_sent),
            "messages_received": len(self.messages_received),
            "is_connected": self.is_connected,
            "last_sent": self.messages_sent[-1] if self.messages_sent else None,
            "last_received": self.messages_received[-1] if self.messages_received else None
        }
        
    async def test_multi_turn_conversation(self, turns: int = 3) -> bool:
        """Test multi-turn conversation flow."""
        success = True
        
        for turn in range(turns):
            # Send a message
            message = {
                "type": "message",
                "content": f"Test message turn {turn + 1}",
                "turn": turn + 1
            }
            
            if not await self.send_message(message):
                logger.error(f"Failed to send message on turn {turn + 1}")
                success = False
                break
                
            # Wait for response
            response = await self.receive_message(timeout=10.0)
            if not response:
                logger.error(f"No response received on turn {turn + 1}")
                success = False
                break
                
            logger.info(f"Completed turn {turn + 1}")
            
        return success
        
    async def verify_context_preservation(self) -> bool:
        """Verify that context is preserved across messages."""
        # Send initial context-setting message
        context_msg = {
            "type": "set_context",
            "context": {"user": "test_user", "session": "test_session"}
        }
        
        if not await self.send_message(context_msg):
            return False
            
        # Send follow-up message
        followup_msg = {
            "type": "message",
            "content": "Follow-up message requiring context"
        }
        
        if not await self.send_message(followup_msg):
            return False
            
        # Check if context was preserved in response
        response = await self.receive_message(timeout=10.0)
        if response and "context" in response:
            return response["context"].get("session") == "test_session"
            
        return False


# Additional helper functions for compatibility
async def create_websocket_connection(url: str, auth_token: Optional[str] = None) -> WebSocketResilienceTestCore:
    """Create and connect a WebSocket test instance."""
    core = WebSocketResilienceTestCore()
    await core.connect(url, auth_token)
    return core


async def test_websocket_resilience(url: str) -> Dict[str, Any]:
    """Run basic WebSocket resilience test."""
    core = WebSocketResilienceTestCore()
    results = {
        "connection": False,
        "message_send": False,
        "message_receive": False,
        "reconnection": False
    }
    
    # Test connection
    results["connection"] = await core.connect(url)
    
    if results["connection"]:
        # Test message send
        results["message_send"] = await core.send_message({"type": "test"})
        
        # Test message receive
        response = await core.receive_message(timeout=5.0)
        results["message_receive"] = response is not None
        
        # Test reconnection
        await core.simulate_disconnect()
        results["reconnection"] = await core.simulate_reconnect()
        
        await core.disconnect()
        
    return results