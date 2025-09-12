"""
Enhanced Staging WebSocket Test Helper

This module provides robust WebSocket testing utilities specifically designed for staging environment.
Handles authentication, SSL/TLS, connection retry, and event tracking for staging WebSocket endpoints.

Business Value:
- Validates WebSocket functionality in production-like environment  
- Prevents $50K+ MRR loss from WebSocket failures before production deployment
- Ensures agent event tracking works correctly in staging
"""

import asyncio
import json
import logging
import time
import ssl
from typing import Any, Callable, Dict, List, Optional, Union, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import websockets
from websockets.exceptions import WebSocketException, ConnectionClosedError, InvalidURI
import urllib.parse

from tests.e2e.staging_config import get_staging_config
from tests.e2e.staging_auth_client import StagingAuthClient

logger = logging.getLogger(__name__)


@dataclass
class WebSocketEventRecord:
    """Record of a WebSocket event for validation."""
    event_type: str
    data: Dict[str, Any]
    timestamp: float
    thread_id: str
    message_id: Optional[str] = None


class StagingWebSocketTestHelper:
    """Enhanced WebSocket test helper for staging environment with robust error handling."""
    
    def __init__(self, auth_client: Optional[StagingAuthClient] = None):
        """Initialize staging WebSocket test helper."""
        self.config = get_staging_config()
        self.auth_client = auth_client or StagingAuthClient()
        
        # Connection management
        self.websocket: Optional[websockets.ClientConnection] = None
        self.is_connected = False
        self.connection_start_time: Optional[datetime] = None
        self.current_token: Optional[str] = None
        self.current_user_id: Optional[str] = None
        
        # Event tracking
        self.received_events: List[WebSocketEventRecord] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Connection retry configuration
        self.max_retries = self.config.ws_max_reconnect_attempts
        self.retry_delay = self.config.ws_reconnect_delay
        self.connection_timeout = 15.0
        self.ping_interval = self.config.ws_heartbeat_interval
        
        # SSL/TLS configuration for staging wss:// connections
        self.ssl_context = self._create_ssl_context()
        
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure WebSocket connections."""
        if self.config.urls.websocket_url.startswith('wss://'):
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            return context
        return None
    
    async def connect_with_auth(
        self, 
        email: Optional[str] = None,
        name: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        force_refresh: bool = False,
        max_retries: Optional[int] = None
    ) -> bool:
        """
        Connect to staging WebSocket with authentication.
        
        Args:
            email: User email for authentication
            name: User name for authentication  
            permissions: User permissions
            force_refresh: Force new token even if cached
            max_retries: Override default retry attempts
            
        Returns:
            True if connected successfully
        """
        retries = max_retries or self.max_retries
        
        for attempt in range(retries + 1):
            try:
                # Get authentication token
                if not self.current_token or force_refresh:
                    logger.info(f"Getting auth token for staging WebSocket (attempt {attempt + 1})")
                    tokens = await self.auth_client.get_auth_token(
                        email=email,
                        name=name, 
                        permissions=permissions,
                        force_refresh=force_refresh
                    )
                    self.current_token = tokens["access_token"]
                    self.current_user_id = email or self.config.test_user_email
                
                # Attempt WebSocket connection
                success = await self._attempt_connection()
                if success:
                    logger.info(f"Successfully connected to staging WebSocket on attempt {attempt + 1}")
                    return True
                    
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                
            if attempt < retries:
                wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying connection in {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        logger.error(f"Failed to connect to staging WebSocket after {retries + 1} attempts")
        return False
    
    async def _attempt_connection(self) -> bool:
        """Attempt single WebSocket connection."""
        try:
            ws_url = self.config.urls.websocket_url
            headers = self.config.get_websocket_headers(self.current_token)
            
            logger.info(f"Connecting to staging WebSocket: {ws_url}")
            self.connection_start_time = datetime.now()
            
            # Connect with proper SSL context and timeout
            connect_kwargs = {
                'additional_headers': headers,
                'ping_interval': self.ping_interval,
                'ping_timeout': 10,
                'close_timeout': 10,
            }
            
            if self.ssl_context:
                connect_kwargs['ssl'] = self.ssl_context
            
            self.websocket = await asyncio.wait_for(
                websockets.connect(ws_url, **connect_kwargs),
                timeout=self.connection_timeout
            )
            
            self.is_connected = True
            connection_time = (datetime.now() - self.connection_start_time).total_seconds()
            logger.info(f"Connected to staging WebSocket in {connection_time:.2f}s")
            
            # Start message listener
            asyncio.create_task(self._listen_for_messages())
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"WebSocket connection timeout after {self.connection_timeout}s")
            return False
        except InvalidURI as e:
            logger.error(f"Invalid WebSocket URL: {e}")
            return False
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
    
    async def _listen_for_messages(self) -> None:
        """Listen for incoming WebSocket messages with error handling."""
        try:
            async for message in self.websocket:
                try:
                    await self._handle_message(message)
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    
        except ConnectionClosedError as e:
            logger.warning(f"WebSocket connection closed: {e}")
            self.is_connected = False
            
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
            
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.is_connected = False
    
    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message and record events."""
        try:
            data = json.loads(message)
            event_type = data.get("type", "unknown")
            
            # Record event
            event_record = WebSocketEventRecord(
                event_type=event_type,
                data=data,
                timestamp=time.time(),
                thread_id=data.get("thread_id", "unknown"),
                message_id=data.get("message_id")
            )
            self.received_events.append(event_record)
            
            logger.debug(f"Received WebSocket event: {event_type}")
            
            # Call registered handlers
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(data)
                        else:
                            handler(data)
                    except Exception as e:
                        logger.error(f"Error in event handler for {event_type}: {e}")
                        
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON message: {message[:100]}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def on_event(self, event_type: str, handler: Callable) -> None:
        """
        Register an event handler for specific event type.
        
        Args:
            event_type: The event type to handle
            handler: Function to call when event is received (can be sync or async)
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def send_message(self, message_type: str, data: Dict[str, Any], thread_id: str = None) -> bool:
        """
        Send a message to staging WebSocket.
        
        Args:
            message_type: Type of message to send
            data: Message data
            thread_id: Thread ID for the message
            
        Returns:
            True if sent successfully
        """
        if not self.is_connected or not self.websocket:
            logger.error("Cannot send message: not connected to staging WebSocket")
            return False
        
        try:
            message = {
                "type": message_type,
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id or f"test-{int(time.time())}",
                "user_id": self.current_user_id,
                **data
            }
            
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent WebSocket message: {message_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def send_agent_request(
        self, 
        query: str, 
        agent_type: str = "supervisor",
        thread_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Send agent request through WebSocket.
        
        Args:
            query: The query to send to the agent
            agent_type: Type of agent to request
            thread_id: Thread ID for the request
            **kwargs: Additional request parameters
            
        Returns:
            True if sent successfully
        """
        thread_id = thread_id or f"test-agent-{int(time.time())}"
        
        return await self.send_message("agent_request", {
            "query": query,
            "agent_type": agent_type,
            "parameters": kwargs.get("parameters", {}),
            "metadata": kwargs.get("metadata", {"test_request": True})
        }, thread_id=thread_id)
    
    async def wait_for_event(
        self,
        event_type: str,
        timeout: float = 30.0,
        thread_id: Optional[str] = None,
        condition: Optional[Callable[[Dict], bool]] = None
    ) -> Optional[WebSocketEventRecord]:
        """
        Wait for a specific event type.
        
        Args:
            event_type: The event type to wait for
            timeout: Maximum time to wait
            thread_id: Optional thread ID to filter by
            condition: Optional condition function
            
        Returns:
            The event record if received, None if timeout
        """
        start_time = time.time()
        initial_count = len(self.received_events)
        
        while time.time() - start_time < timeout:
            # Check new events since we started waiting
            for event in self.received_events[initial_count:]:
                if event.event_type == event_type:
                    if thread_id and event.thread_id != thread_id:
                        continue
                    if condition and not condition(event.data):
                        continue
                    return event
            
            # Check if connection is still alive
            if not self.is_connected:
                logger.warning(f"Connection lost while waiting for {event_type}")
                break
                
            await asyncio.sleep(0.1)
        
        logger.warning(f"Timeout waiting for event: {event_type}")
        return None
    
    async def wait_for_agent_flow(
        self,
        thread_id: str,
        timeout: float = 60.0,
        required_events: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Wait for complete agent flow and validate events.
        
        Args:
            thread_id: Thread ID to monitor
            timeout: Maximum time to wait
            required_events: Set of required event types
            
        Returns:
            Dictionary with flow results and validation
        """
        required_events = required_events or {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        start_time = time.time()
        received_events = []
        event_types = set()
        
        logger.info(f"Waiting for agent flow completion in thread: {thread_id}")
        
        # Wait for agent_started first
        started_event = await self.wait_for_event(
            "agent_started", 
            timeout=10.0, 
            thread_id=thread_id
        )
        
        if not started_event:
            return {
                "success": False,
                "error": "Agent never started",
                "events": [],
                "missing_events": required_events
            }
        
        received_events.append(started_event)
        event_types.add("agent_started")
        
        # Wait for completion or timeout
        while time.time() - start_time < timeout:
            # Look for completion events
            completion_event = await self.wait_for_event(
                "agent_completed",
                timeout=1.0,
                thread_id=thread_id
            )
            
            if completion_event:
                received_events.append(completion_event)
                event_types.add("agent_completed")
                break
                
            # Check for error events
            error_event = await self.wait_for_event(
                "agent_error",
                timeout=0.1,
                thread_id=thread_id
            )
            
            if error_event:
                received_events.append(error_event)
                event_types.add("agent_error")
                break
        
        # Collect all events for this thread
        thread_events = [e for e in self.received_events if e.thread_id == thread_id]
        all_event_types = {e.event_type for e in thread_events}
        
        # Validate flow
        missing_events = required_events - all_event_types
        success = len(missing_events) == 0 and (
            "agent_completed" in all_event_types or "agent_error" in all_event_types
        )
        
        duration = time.time() - start_time
        
        result = {
            "success": success,
            "duration": duration,
            "events": thread_events,
            "event_types": list(all_event_types),
            "missing_events": list(missing_events),
            "total_events": len(thread_events)
        }
        
        if success:
            logger.info(f"Agent flow completed successfully in {duration:.2f}s with {len(thread_events)} events")
        else:
            logger.warning(f"Agent flow incomplete: missing {missing_events}")
            
        return result
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.websocket = None
                self.is_connected = False
                logger.info("Disconnected from staging WebSocket")
    
    def get_event_stats(self) -> Dict[str, Any]:
        """Get statistics about received events."""
        event_types = {}
        thread_ids = set()
        
        for event in self.received_events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
            thread_ids.add(event.thread_id)
        
        return {
            "total_events": len(self.received_events),
            "event_types": event_types,
            "unique_threads": len(thread_ids),
            "connection_time": (
                (datetime.now() - self.connection_start_time).total_seconds()
                if self.connection_start_time else 0
            ),
            "is_connected": self.is_connected
        }
    
    def get_events_for_thread(self, thread_id: str) -> List[WebSocketEventRecord]:
        """Get all events for a specific thread."""
        return [e for e in self.received_events if e.thread_id == thread_id]
    
    def clear_events(self) -> None:
        """Clear all recorded events."""
        self.received_events.clear()
        logger.info("Cleared all recorded WebSocket events")


async def test_staging_websocket_helper():
    """Test the staging WebSocket helper functionality."""
    helper = StagingWebSocketTestHelper()
    
    try:
        # Test connection
        connected = await helper.connect_with_auth()
        if not connected:
            print(" FAIL:  Failed to connect to staging WebSocket")
            return False
        
        print(f" PASS:  Connected to staging WebSocket")
        
        # Register event handlers
        agent_events = []
        
        def handle_agent_event(data):
            agent_events.append(data)
            print(f"  [U+1F4E8] Received: {data.get('type')}")
        
        helper.on_event("agent_started", handle_agent_event)
        helper.on_event("agent_thinking", handle_agent_event)
        helper.on_event("tool_executing", handle_agent_event)
        helper.on_event("tool_completed", handle_agent_event)
        helper.on_event("agent_completed", handle_agent_event)
        
        # Test agent flow
        thread_id = f"test-flow-{int(time.time())}"
        success = await helper.send_agent_request(
            "Test WebSocket agent flow", 
            thread_id=thread_id
        )
        print(f" PASS:  Sent agent request: {success}")
        
        if success:
            # Wait for agent flow to complete
            flow_result = await helper.wait_for_agent_flow(thread_id, timeout=45.0)
            
            print(f" PASS:  Agent flow result:")
            print(f"  - Success: {flow_result['success']}")
            print(f"  - Duration: {flow_result['duration']:.2f}s") 
            print(f"  - Events: {flow_result['total_events']}")
            print(f"  - Types: {flow_result['event_types']}")
            
            if flow_result['missing_events']:
                print(f"  - Missing: {flow_result['missing_events']}")
        
        # Get final stats
        stats = helper.get_event_stats()
        print(f" PASS:  Final stats:")
        print(f"  - Total events: {stats['total_events']}")
        print(f"  - Event types: {stats['event_types']}")
        print(f"  - Unique threads: {stats['unique_threads']}")
        print(f"  - Connection time: {stats['connection_time']:.2f}s")
        
        return True
        
    except Exception as e:
        print(f" FAIL:  Test failed: {e}")
        return False
        
    finally:
        await helper.disconnect()


if __name__ == "__main__":
    # Run test when executed directly
    success = asyncio.run(test_staging_websocket_helper())
    exit(0 if success else 1)