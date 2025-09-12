"""
Staging WebSocket Client for E2E Tests

This module provides a WebSocket client for testing real-time features
against the deployed staging environment.

Business Value:
- Validates WebSocket connectivity in production-like environment
- Tests real-time agent updates and chat functionality
- Prevents $50K+ MRR loss from WebSocket failures
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import websockets
from websockets.exceptions import WebSocketException

from tests.e2e.staging_config import get_staging_config
from tests.e2e.staging_auth_client import StagingAuthClient

logger = logging.getLogger(__name__)


class StagingWebSocketClient:
    """WebSocket client for staging environment tests."""
    
    def __init__(self, auth_client: Optional[StagingAuthClient] = None):
        """Initialize WebSocket client."""
        self.config = get_staging_config()
        self.auth_client = auth_client or StagingAuthClient()
        self.websocket: Optional[websockets.ClientConnection] = None
        self.is_connected = False
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.received_messages: List[Dict] = []
        self.connection_start_time: Optional[datetime] = None
        self.current_token: Optional[str] = None
        
    async def connect(self, token: Optional[str] = None, **auth_kwargs) -> bool:
        """
        Connect to staging WebSocket server.
        
        Args:
            token: Access token (will get one if not provided)
            **auth_kwargs: Arguments for get_auth_token if token not provided
            
        Returns:
            True if connected successfully
        """
        try:
            # Get auth token if not provided
            if not token:
                tokens = await self.auth_client.get_auth_token(**auth_kwargs)
                token = tokens["access_token"]
            
            self.current_token = token
            
            # Build WebSocket URL with auth
            ws_url = self.config.urls.websocket_url
            headers = self.config.get_websocket_headers(token)
            
            logger.info(f"Connecting to staging WebSocket: {ws_url}")
            self.connection_start_time = datetime.now()
            
            # Connect with auth headers
            self.websocket = await websockets.connect(
                ws_url,
                additional_headers=headers,
                ping_interval=self.config.ws_heartbeat_interval,
                ping_timeout=10
            )
            
            self.is_connected = True
            connection_time = (datetime.now() - self.connection_start_time).total_seconds()
            logger.info(f"Connected to staging WebSocket in {connection_time:.2f}s")
            
            # Start message listener
            asyncio.create_task(self._listen_for_messages())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to staging WebSocket: {e}")
            self.is_connected = False
            return False
    
    async def _listen_for_messages(self) -> None:
        """Listen for incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                await self._handle_message(message)
                
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
            
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.is_connected = False
    
    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            self.received_messages.append(data)
            
            event_type = data.get("type", "unknown")
            logger.debug(f"Received WebSocket message: {event_type}")
            
            # Call registered handlers
            if event_type in self.message_handlers:
                for handler in self.message_handlers[event_type]:
                    try:
                        await handler(data)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
                        
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON message: {message}")
    
    def on_message(self, event_type: str, handler: Callable) -> None:
        """
        Register a message handler for a specific event type.
        
        Args:
            event_type: The event type to handle
            handler: Async function to call when event is received
        """
        if event_type not in self.message_handlers:
            self.message_handlers[event_type] = []
        self.message_handlers[event_type].append(handler)
    
    async def send_message(self, message_type: str, data: Dict[str, Any]) -> bool:
        """
        Send a message to the staging WebSocket server.
        
        Args:
            message_type: Type of message to send
            data: Message data
            
        Returns:
            True if sent successfully
        """
        if not self.is_connected or not self.websocket:
            logger.error("Cannot send message: not connected")
            return False
        
        try:
            message = {
                "type": message_type,
                "timestamp": datetime.now().isoformat(),
                **data
            }
            
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent WebSocket message: {message_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def send_chat_message(self, content: str, conversation_id: Optional[str] = None) -> bool:
        """
        Send a chat message through WebSocket.
        
        Args:
            content: Message content
            conversation_id: Optional conversation ID
            
        Returns:
            True if sent successfully
        """
        return await self.send_message("chat_message", {
            "content": content,
            "conversation_id": conversation_id or "test_conversation",
            "user_id": "test_user"
        })
    
    async def wait_for_message(
        self,
        event_type: str,
        timeout: float = 10.0,
        condition: Optional[Callable[[Dict], bool]] = None
    ) -> Optional[Dict]:
        """
        Wait for a specific message type.
        
        Args:
            event_type: The event type to wait for
            timeout: Maximum time to wait
            condition: Optional condition function
            
        Returns:
            The message if received, None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check existing messages
            for msg in self.received_messages:
                if msg.get("type") == event_type:
                    if condition is None or condition(msg):
                        return msg
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
        
        logger.warning(f"Timeout waiting for message type: {event_type}")
        return None
    
    async def test_agent_flow(self, query: str) -> bool:
        """
        Test a complete agent interaction flow.
        
        Args:
            query: The query to send to the agent
            
        Returns:
            True if flow completed successfully
        """
        logger.info(f"Testing agent flow with query: {query}")
        
        # Send agent request
        success = await self.send_message("agent_request", {
            "query": query,
            "agent_type": "supervisor"
        })
        
        if not success:
            return False
        
        # Wait for agent_started event
        started = await self.wait_for_message("agent_started", timeout=5.0)
        if not started:
            logger.error("Did not receive agent_started event")
            return False
        
        logger.info(f"Agent started: {started.get('agent_id')}")
        
        # Wait for agent_completed or agent_error
        completed = await self.wait_for_message(
            "agent_completed",
            timeout=30.0,
            condition=lambda m: m.get("agent_id") == started.get("agent_id")
        )
        
        if completed:
            logger.info(f"Agent completed successfully: {completed.get('result')}")
            return True
        
        # Check for error
        error = await self.wait_for_message(
            "agent_error",
            timeout=1.0,
            condition=lambda m: m.get("agent_id") == started.get("agent_id")
        )
        
        if error:
            logger.error(f"Agent failed: {error.get('error')}")
        
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.is_connected = False
            logger.info("Disconnected from staging WebSocket")
    
    def get_message_stats(self) -> Dict[str, Any]:
        """Get statistics about received messages."""
        event_types = {}
        for msg in self.received_messages:
            event_type = msg.get("type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        return {
            "total_messages": len(self.received_messages),
            "event_types": event_types,
            "connection_time": (
                (datetime.now() - self.connection_start_time).total_seconds()
                if self.connection_start_time else 0
            )
        }


async def test_staging_websocket():
    """Test staging WebSocket connectivity and messaging."""
    client = StagingWebSocketClient()
    
    try:
        # Connect to WebSocket
        connected = await client.connect()
        if not connected:
            print("[U+2717] Failed to connect to staging WebSocket")
            return False
        
        print(f"[U+2713] Connected to staging WebSocket")
        
        # Register message handler
        agent_events = []
        
        async def handle_agent_event(msg):
            agent_events.append(msg)
            print(f"  Received: {msg.get('type')}")
        
        client.on_message("agent_started", handle_agent_event)
        client.on_message("agent_thinking", handle_agent_event)
        client.on_message("agent_completed", handle_agent_event)
        
        # Send a test message
        success = await client.send_chat_message("Hello from staging E2E test")
        print(f"[U+2713] Sent test message: {success}")
        
        # Test agent flow
        success = await client.test_agent_flow("What is 2+2?")
        print(f"[U+2713] Agent flow test: {'passed' if success else 'failed'}")
        
        # Wait a bit for any remaining messages
        await asyncio.sleep(2)
        
        # Get stats
        stats = client.get_message_stats()
        print(f"[U+2713] Message stats:")
        print(f"  - Total messages: {stats['total_messages']}")
        print(f"  - Event types: {stats['event_types']}")
        print(f"  - Connection time: {stats['connection_time']:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"[U+2717] Test failed: {e}")
        return False
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    # Run test when executed directly
    success = asyncio.run(test_staging_websocket())
    exit(0 if success else 1)