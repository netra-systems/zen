"""
WebSocket Test Integration Framework

This module provides comprehensive integration testing for WebSocket functionality
with embedded server support to eliminate Docker dependencies and connection failures.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Eliminate WebSocket test failures that block development velocity
- Value Impact: Enable reliable WebSocket testing without Docker dependencies
- Strategic Impact: Faster CI/CD cycles and reduced development friction

CRITICAL: Validates all 5 required WebSocket events for chat business value:
1. agent_started - User must see agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - Response ready notification
"""

import asyncio
import json
import logging
import pytest
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from unittest.mock import AsyncMock, MagicMock

from test_framework.embedded_websocket_server import (
    EmbeddedWebSocketServer,
    embedded_websocket_server,
    EmbeddedWebSocketTestHelper
)

logger = logging.getLogger(__name__)


class WebSocketTestClient:
    """
    WebSocket test client for integration testing.
    
    Provides utilities for connecting to WebSocket servers and testing
    chat functionality with proper event validation.
    """
    
    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.websocket = None
        self.received_messages: List[Dict[str, Any]] = []
        self.connection_established = False
        
    async def connect(self, timeout: float = 10.0) -> bool:
        """Connect to WebSocket server."""
        try:
            import websockets
            
            # Try connection with retries
            for attempt in range(3):
                try:
                    self.websocket = await asyncio.wait_for(
                        websockets.connect(self.websocket_url),
                        timeout=timeout
                    )
                    break
                except Exception as e:
                    logger.debug(f"Connection attempt {attempt + 1} failed: {e}")
                    if attempt == 2:  # Last attempt
                        raise
                    await asyncio.sleep(0.5)
            
            # Wait for connection established message
            try:
                welcome_msg = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=3.0
                )
                data = json.loads(welcome_msg)
                self.received_messages.append(data)
                
                if data.get("type") == "connection_established":
                    self.connection_established = True
                    logger.info(f"WebSocket connected successfully: {data.get('connection_id')}")
                    return True
                    
            except asyncio.TimeoutError:
                logger.debug("No welcome message received, but connection seems established")
                self.connection_established = True
                return True
                
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
        
        return self.connection_established
    
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None
            self.connection_established = False
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to WebSocket server."""
        if not self.websocket or not self.connection_established:
            logger.error("WebSocket not connected")
            return False
        
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            return False
    
    async def receive_message(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Receive message from WebSocket server."""
        if not self.websocket or not self.connection_established:
            logger.error("WebSocket not connected")
            return None
        
        try:
            raw_message = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=timeout
            )
            data = json.loads(raw_message)
            self.received_messages.append(data)
            return data
        except asyncio.TimeoutError:
            logger.debug("WebSocket receive timeout")
            return None
        except Exception as e:
            logger.error(f"Failed to receive WebSocket message: {e}")
            return None
    
    async def send_chat_message(self, content: str, expect_events: bool = True) -> Dict[str, bool]:
        """
        Send chat message and validate critical events are received.
        
        Args:
            content: Chat message content
            expect_events: Whether to expect all 5 critical events
            
        Returns:
            Dict mapping event types to whether they were received
        """
        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing', 
            'tool_completed',
            'agent_completed'
        ]
        
        received_events = {event: False for event in critical_events}
        
        # Send chat message
        success = await self.send_message({
            "type": "chat",
            "payload": {
                "content": content
            }
        })
        
        if not success:
            logger.error("Failed to send chat message")
            return received_events
        
        if not expect_events:
            return received_events
        
        # Collect events for up to 5 seconds
        timeout = 5.0
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            message = await self.receive_message(timeout=0.5)
            if message:
                event_type = message.get("type") or message.get("event")
                if event_type in critical_events:
                    received_events[event_type] = True
                    logger.info(f" PASS:  Received critical event: {event_type}")
                
                # Check if all events received
                if all(received_events.values()):
                    logger.info(" PASS:  All critical events received!")
                    break
        
        return received_events
    
    def get_received_messages(self) -> List[Dict[str, Any]]:
        """Get all received messages."""
        return self.received_messages.copy()
    
    def clear_received_messages(self):
        """Clear received messages."""
        self.received_messages.clear()


class WebSocketIntegrationTestSuite:
    """
    Comprehensive WebSocket integration test suite.
    
    Provides standardized tests for WebSocket functionality across
    different environments (embedded, Docker, staging).
    """
    
    def __init__(self, websocket_url: str = None):
        self.websocket_url = websocket_url
        self.embedded_server: Optional[EmbeddedWebSocketServer] = None
        self.test_client: Optional[WebSocketTestClient] = None
    
    async def setup_embedded_server(self, host: str = "127.0.0.1", port: int = None) -> str:
        """Setup embedded WebSocket server for testing."""
        self.embedded_server = EmbeddedWebSocketServer(host=host, port=port)
        self.websocket_url = await self.embedded_server.start()
        return self.websocket_url
    
    async def teardown_embedded_server(self):
        """Teardown embedded WebSocket server."""
        if self.embedded_server:
            await self.embedded_server.stop()
            self.embedded_server = None
        
        if self.test_client:
            await self.test_client.disconnect()
            self.test_client = None
    
    async def test_websocket_connection(self, websocket_url: str = None) -> bool:
        """Test basic WebSocket connection."""
        url = websocket_url or self.websocket_url
        if not url:
            raise ValueError("No WebSocket URL provided")
        
        try:
            client = WebSocketTestClient(url)
            connected = await client.connect()
            
            if connected:
                # Test ping/pong
                success = await client.send_message({
                    "type": "ping",
                    "timestamp": time.time()
                })
                
                if success:
                    response = await client.receive_message(timeout=2.0)
                    if response and response.get("type") == "pong":
                        logger.info(" PASS:  WebSocket connection test passed")
                        await client.disconnect()
                        return True
            
            await client.disconnect()
            return False
            
        except Exception as e:
            logger.error(f"WebSocket connection test failed: {e}")
            return False
    
    async def test_critical_events_emission(self, websocket_url: str = None) -> Dict[str, bool]:
        """Test that all 5 critical WebSocket events are emitted for chat business value."""
        url = websocket_url or self.websocket_url
        if not url:
            raise ValueError("No WebSocket URL provided")
        
        try:
            client = WebSocketTestClient(url)
            connected = await client.connect()
            
            if not connected:
                logger.error("Failed to connect for critical events test")
                return {event: False for event in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']}
            
            # Send chat message and validate events
            received_events = await client.send_chat_message(
                "test message for critical events validation",
                expect_events=True
            )
            
            await client.disconnect()
            
            # Log results
            missing_events = [event for event, received in received_events.items() if not received]
            if missing_events:
                logger.error(f" FAIL:  Missing critical events: {missing_events}")
            else:
                logger.info(" PASS:  All critical events received successfully")
            
            return received_events
            
        except Exception as e:
            logger.error(f"Critical events test failed: {e}")
            return {event: False for event in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']}
    
    async def test_websocket_authentication(self, websocket_url: str = None, jwt_token: str = None) -> bool:
        """Test WebSocket authentication (if required)."""
        url = websocket_url or self.websocket_url
        if not url:
            raise ValueError("No WebSocket URL provided")
        
        try:
            # For embedded server, authentication is not required
            if self.embedded_server:
                logger.info(" PASS:  Authentication test skipped for embedded server")
                return True
            
            # For external servers, test authentication
            headers = {}
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"
            
            import websockets
            async with websockets.connect(url, extra_headers=headers) as websocket:
                # Wait for welcome message or error
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    
                    if data.get("type") == "connection_established":
                        logger.info(" PASS:  WebSocket authentication test passed")
                        return True
                    elif data.get("type") == "error":
                        logger.error(f" FAIL:  WebSocket authentication failed: {data.get('message')}")
                        return False
                        
                except asyncio.TimeoutError:
                    logger.error(" FAIL:  WebSocket authentication timeout")
                    return False
            
        except Exception as e:
            logger.error(f"WebSocket authentication test failed: {e}")
            return False
        
        return False
    
    async def test_message_routing(self, websocket_url: str = None) -> bool:
        """Test WebSocket message routing functionality."""
        url = websocket_url or self.websocket_url
        if not url:
            raise ValueError("No WebSocket URL provided")
        
        try:
            client = WebSocketTestClient(url)
            connected = await client.connect()
            
            if not connected:
                logger.error("Failed to connect for message routing test")
                return False
            
            # Test different message types
            test_messages = [
                {"type": "ping"},
                {"type": "echo", "payload": {"test": "data"}},
                {"type": "user_message", "payload": {"content": "test message"}},
                {"type": "unknown_type", "payload": {"test": True}}
            ]
            
            all_successful = True
            
            for test_msg in test_messages:
                success = await client.send_message(test_msg)
                if success:
                    response = await client.receive_message(timeout=3.0)
                    if response:
                        logger.info(f" PASS:  Message routing test passed for {test_msg['type']}: {response.get('type')}")
                    else:
                        logger.warning(f" WARNING: [U+FE0F] No response for message type: {test_msg['type']}")
                        all_successful = False
                else:
                    logger.error(f" FAIL:  Failed to send message type: {test_msg['type']}")
                    all_successful = False
            
            await client.disconnect()
            return all_successful
            
        except Exception as e:
            logger.error(f"Message routing test failed: {e}")
            return False
    
    async def test_concurrent_connections(self, websocket_url: str = None, connection_count: int = 3) -> bool:
        """Test multiple concurrent WebSocket connections."""
        url = websocket_url or self.websocket_url
        if not url:
            raise ValueError("No WebSocket URL provided")
        
        try:
            clients = []
            
            # Create multiple connections
            for i in range(connection_count):
                client = WebSocketTestClient(url)
                connected = await client.connect()
                
                if connected:
                    clients.append(client)
                    logger.info(f" PASS:  Connection {i+1} established")
                else:
                    logger.error(f" FAIL:  Connection {i+1} failed")
            
            if len(clients) != connection_count:
                logger.error(f"Only {len(clients)}/{connection_count} connections established")
                # Cleanup
                for client in clients:
                    await client.disconnect()
                return False
            
            # Test message sending from all clients
            all_successful = True
            for i, client in enumerate(clients):
                success = await client.send_message({
                    "type": "ping",
                    "client_id": i
                })
                
                if success:
                    response = await client.receive_message(timeout=2.0)
                    if response and response.get("type") == "pong":
                        logger.info(f" PASS:  Client {i} message test passed")
                    else:
                        logger.error(f" FAIL:  Client {i} did not receive pong")
                        all_successful = False
                else:
                    logger.error(f" FAIL:  Client {i} failed to send message")
                    all_successful = False
            
            # Cleanup connections
            for client in clients:
                await client.disconnect()
            
            if all_successful:
                logger.info(f" PASS:  Concurrent connections test passed ({connection_count} clients)")
            else:
                logger.error(f" FAIL:  Concurrent connections test failed")
            
            return all_successful
            
        except Exception as e:
            logger.error(f"Concurrent connections test failed: {e}")
            return False
    
    async def run_comprehensive_test_suite(self, websocket_url: str = None) -> Dict[str, bool]:
        """Run comprehensive WebSocket test suite."""
        url = websocket_url or self.websocket_url
        
        logger.info("[U+1F9EA] Starting comprehensive WebSocket test suite")
        
        test_results = {}
        
        # Test 1: Basic connection
        logger.info("1[U+FE0F][U+20E3] Testing basic WebSocket connection...")
        test_results["connection"] = await self.test_websocket_connection(url)
        
        # Test 2: Critical events (MOST IMPORTANT)
        logger.info("2[U+FE0F][U+20E3] Testing critical events emission...")
        critical_events = await self.test_critical_events_emission(url)
        test_results["critical_events"] = all(critical_events.values())
        test_results["critical_events_detail"] = critical_events
        
        # Test 3: Authentication (if applicable)
        logger.info("3[U+FE0F][U+20E3] Testing WebSocket authentication...")
        test_results["authentication"] = await self.test_websocket_authentication(url)
        
        # Test 4: Message routing
        logger.info("4[U+FE0F][U+20E3] Testing message routing...")
        test_results["message_routing"] = await self.test_message_routing(url)
        
        # Test 5: Concurrent connections
        logger.info("5[U+FE0F][U+20E3] Testing concurrent connections...")
        test_results["concurrent_connections"] = await self.test_concurrent_connections(url, 3)
        
        # Summary
        passed_tests = sum(1 for result in test_results.values() if isinstance(result, bool) and result)
        total_tests = sum(1 for result in test_results.values() if isinstance(result, bool))
        
        logger.info(f"[U+1F3C1] Test suite completed: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info(" PASS:  All WebSocket tests passed!")
        else:
            logger.error(" FAIL:  Some WebSocket tests failed")
            for test_name, result in test_results.items():
                if isinstance(result, bool) and not result:
                    logger.error(f"   Failed: {test_name}")
        
        return test_results


# Pytest fixtures for WebSocket testing
@pytest.fixture
async def embedded_websocket_server_fixture():
    """Pytest fixture for embedded WebSocket server."""
    async with embedded_websocket_server() as websocket_url:
        yield websocket_url


@pytest.fixture
async def websocket_test_suite():
    """Pytest fixture for WebSocket test suite with embedded server."""
    suite = WebSocketIntegrationTestSuite()
    websocket_url = await suite.setup_embedded_server()
    
    try:
        yield suite, websocket_url
    finally:
        await suite.teardown_embedded_server()


@pytest.fixture
async def websocket_test_client(embedded_websocket_server_fixture):
    """Pytest fixture for WebSocket test client."""
    websocket_url = embedded_websocket_server_fixture
    client = WebSocketTestClient(websocket_url)
    
    try:
        yield client
    finally:
        await client.disconnect()


# Utility functions for test integration
async def validate_websocket_events_for_chat(websocket_url: str) -> bool:
    """
    Validate that WebSocket server emits all required events for chat business value.
    
    This is the primary validation function for ensuring chat functionality works.
    
    Returns:
        True if all 5 critical events are emitted, False otherwise
    """
    suite = WebSocketIntegrationTestSuite(websocket_url)
    critical_events = await suite.test_critical_events_emission()
    
    missing_events = [event for event, received in critical_events.items() if not received]
    
    if missing_events:
        logger.error(f" FAIL:  CHAT BUSINESS VALUE FAILURE: Missing events {missing_events}")
        return False
    else:
        logger.info(" PASS:  CHAT BUSINESS VALUE VALIDATED: All critical events working")
        return True


async def quick_websocket_health_check(websocket_url: str) -> bool:
    """
    Quick WebSocket health check for CI/CD pipelines.
    
    Returns:
        True if WebSocket is healthy, False otherwise
    """
    try:
        suite = WebSocketIntegrationTestSuite(websocket_url)
        connected = await suite.test_websocket_connection()
        
        if connected:
            logger.info(" PASS:  WebSocket health check passed")
            return True
        else:
            logger.error(" FAIL:  WebSocket health check failed")
            return False
            
    except Exception as e:
        logger.error(f" FAIL:  WebSocket health check error: {e}")
        return False


# Export main components
__all__ = [
    "WebSocketTestClient",
    "WebSocketIntegrationTestSuite", 
    "embedded_websocket_server_fixture",
    "websocket_test_suite",
    "websocket_test_client",
    "validate_websocket_events_for_chat",
    "quick_websocket_health_check"
]