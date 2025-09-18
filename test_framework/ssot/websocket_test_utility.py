"""
WebSocket Test Utility - SSOT for WebSocket Testing Infrastructure

This module provides the canonical WebSocket testing utilities for the platform.
Consolidates all WebSocket test functionality into a single source of truth.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Testing Infrastructure
- Business Goal: Enable reliable WebSocket golden path testing
- Value Impact: Provides SSOT WebSocket testing capabilities for agent workflows
- Strategic Impact: Supports validation of 90% platform value (chat functionality)
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Callable
from unittest.mock import AsyncMock, MagicMock, Mock
from dataclasses import dataclass, field
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from test_framework.fixtures.websocket_fixtures import MockWebSocket, MockWebSocketState
from tests.helpers.auth_test_utils import TestAuthHelper


class WebSocketTestHelper:
    """
    SSOT WebSocket Test Helper for golden path validation.

    Provides comprehensive WebSocket testing utilities for agent workflows,
    focusing on business-critical chat functionality testing.
    """

    def __init__(self):
        """Initialize WebSocket test helper."""
        self.connections: Dict[str, Any] = {}
        self.message_history: List[Dict[str, Any]] = []
        self.auth_helper = TestAuthHelper()

    async def create_test_connection(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Any:
        """
        Create a test WebSocket connection with auth and timeout handling.

        Args:
            url: WebSocket endpoint URL
            headers: Optional authentication headers
            timeout: Connection timeout in seconds

        Returns:
            WebSocket connection object
        """
        try:
            # Add default test headers if none provided
            if headers is None:
                headers = await self._get_test_auth_headers()

            # Create connection with timeout
            connection = await asyncio.wait_for(
                websockets.connect(url, extra_headers=headers),
                timeout=timeout
            )

            connection_id = f"test_{int(time.time() * 1000)}"
            self.connections[connection_id] = connection

            return connection

        except asyncio.TimeoutError:
            raise TimeoutError(f"WebSocket connection to {url} timed out after {timeout}s")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to WebSocket {url}: {e}")

    async def send_agent_message(
        self,
        connection: Any,
        message: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an agent message through WebSocket and track for testing.

        Args:
            connection: WebSocket connection
            message: Message to send to agent
            user_id: Optional user ID for tracking

        Returns:
            Message metadata for validation
        """
        try:
            # Prepare agent message payload
            payload = {
                "type": "agent_message",
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id or "test_user"
            }

            # Send message
            await connection.send(json.dumps(payload))

            # Track message history
            message_record = {
                "sent_at": time.time(),
                "payload": payload,
                "user_id": user_id
            }
            self.message_history.append(message_record)

            return message_record

        except ConnectionClosed:
            raise ConnectionError("WebSocket connection was closed")
        except Exception as e:
            raise RuntimeError(f"Failed to send agent message: {e}")

    async def wait_for_agent_events(
        self,
        connection: Any,
        expected_events: List[str],
        timeout: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Wait for specific agent events in WebSocket stream.

        Args:
            connection: WebSocket connection
            expected_events: List of event types to wait for
            timeout: Timeout in seconds

        Returns:
            List of received events matching expected types
        """
        received_events = []
        start_time = time.time()

        try:
            while time.time() - start_time < timeout:
                # Wait for message with shorter timeout to allow checking
                try:
                    message = await asyncio.wait_for(connection.recv(), timeout=5)
                    event_data = json.loads(message)

                    # Check if this is an expected event
                    if event_data.get("type") in expected_events:
                        received_events.append(event_data)

                        # Remove from expected list
                        if event_data["type"] in expected_events:
                            expected_events.remove(event_data["type"])

                    # Break if all expected events received
                    if not expected_events:
                        break

                except asyncio.TimeoutError:
                    # Continue waiting if we haven't hit the overall timeout
                    continue

        except ConnectionClosed:
            raise ConnectionError("WebSocket connection closed while waiting for events")

        if expected_events:
            raise TimeoutError(f"Timeout waiting for events: {expected_events}")

        return received_events

    async def validate_agent_workflow(
        self,
        connection: Any,
        message: str,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Validate complete agent workflow from message to completion.

        Tests the golden path: message -> agent_started -> agent_thinking ->
        tool_executing -> tool_completed -> agent_completed

        Args:
            connection: WebSocket connection
            message: Message to send
            timeout: Total timeout for workflow

        Returns:
            Validation results with events and timing
        """
        # Expected agent workflow events
        expected_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

        start_time = time.time()

        # Send message to trigger workflow
        await self.send_agent_message(connection, message)

        # Wait for all expected events
        events = await self.wait_for_agent_events(
            connection,
            expected_events.copy(),  # Copy to avoid modifying original
            timeout
        )

        workflow_time = time.time() - start_time

        # Validate workflow
        validation_result = {
            "success": len(events) >= 4,  # At least 4 critical events
            "events_received": len(events),
            "events_expected": len(expected_events),
            "workflow_time": workflow_time,
            "events": events,
            "message": message
        }

        return validation_result

    async def _get_test_auth_headers(self) -> Dict[str, str]:
        """Get test authentication headers."""
        try:
            # Try to get JWT token for testing
            jwt_token = await self.auth_helper.get_test_jwt_async()
            if jwt_token:
                return {
                    "Authorization": f"Bearer {jwt_token}",
                    "X-Test-Mode": "agent-golden-path"
                }
        except Exception:
            pass

        # Fallback to basic test headers
        return {
            "X-Test-Mode": "agent-golden-path",
            "X-Test-Auth": "test-token"
        }

    async def cleanup_connections(self):
        """Clean up all test connections."""
        for connection_id, connection in self.connections.items():
            try:
                if not connection.closed:
                    await connection.close()
            except Exception:
                pass  # Ignore cleanup errors

        self.connections.clear()

    def get_message_history(self) -> List[Dict[str, Any]]:
        """Get history of all messages sent during testing."""
        return self.message_history.copy()

    def reset_test_state(self):
        """Reset test state for new test run."""
        self.message_history.clear()
        # Don't clear connections as they may be actively used


# Convenience function for backward compatibility
def get_websocket_test_helper() -> WebSocketTestHelper:
    """Get WebSocket test helper instance."""
    return WebSocketTestHelper()