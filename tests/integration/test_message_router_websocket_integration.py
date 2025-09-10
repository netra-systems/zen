"""
Integration Tests for MessageRouter WebSocket Integration - GitHub Issue #217

Business Value Justification:
- Segment: Platform/Chat (90% of business value)
- Business Goal: Chat reliability and user experience
- Value Impact: Ensure stable message routing for real-time chat
- Strategic Impact: Protect $500K+ ARR chat functionality

These tests are designed to FAIL initially to reproduce WebSocket routing issues.
They test with REAL WebSocket connections (no mocks) as per SSOT testing standards.
"""

import asyncio
import json
import uuid
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock
import websockets
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient
from netra_backend.app.websocket_core.handlers import MessageRouter
from netra_backend.app.websocket_core.types import MessageType, create_standard_message
from netra_backend.app.websocket_core import create_websocket_manager


class TestMessageRouterWebSocketIntegration(SSotAsyncTestCase):
    """Integration tests for MessageRouter with real WebSocket connections."""
    
    async def asyncSetUp(self):
        """Set up test environment with real WebSocket infrastructure."""
        await super().asyncSetUp()
        
        # Initialize real WebSocket components (no mocks in integration tests)
        self.websocket_client = RealWebSocketTestClient()
        self.websocket_manager = create_websocket_manager()
        self.message_router = MessageRouter()
        
        # Track messages for verification
        self.received_messages = []
        self.routing_failures = []
        self.connection_states = {}
        
    async def asyncTearDown(self):
        """Clean up WebSocket connections."""
        await self.websocket_client.cleanup()
        await super().asyncTearDown()
        
    async def test_websocket_message_routing_with_real_connections(self):
        """
        Test MessageRouter with real WebSocket connections.
        This should FAIL initially, revealing routing inconsistencies.
        """
        # Create real WebSocket connection
        user_id = f"test_user_{uuid.uuid4()}"
        connection_id = f"conn_{uuid.uuid4()}"
        
        try:
            # Attempt to create WebSocket connection through router
            websocket = await self.websocket_client.create_test_connection(
                user_id=user_id,
                connection_id=connection_id
            )
            
            # Test message routing through the router
            test_message = create_standard_message(
                message_type=MessageType.USER_MESSAGE,
                content={"text": "test routing message", "user_id": user_id},
                user_id=user_id
            )
            
            # Route message through MessageRouter
            routing_success = await self.message_router.route_message(
                websocket=websocket,
                user_id=user_id,
                message=test_message
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Check for routing failures
            if hasattr(self.message_router, 'get_routing_errors'):
                routing_errors = self.message_router.get_routing_errors()
                self.routing_failures.extend(routing_errors)
            
            # This assertion should FAIL, revealing routing issues
            self.assertTrue(
                routing_success,
                f"MESSAGE ROUTING FAILURE: MessageRouter failed to route message. "
                f"Routing failures: {self.routing_failures}"
            )
            
        except Exception as e:
            # Capture routing exceptions
            self.routing_failures.append({
                'error': str(e),
                'context': 'WebSocket message routing',
                'user_id': user_id
            })
            
            # This should FAIL, revealing the integration issue
            self.fail(
                f"WEBSOCKET ROUTING EXCEPTION: {e}. "
                f"All failures: {self.routing_failures}"
            )
            
    async def test_agent_router_communication_consistency(self):
        """
        Test that agent communication through MessageRouter is consistent.
        This should FAIL initially, revealing agent-router communication issues.
        """
        agent_messages = []
        routing_inconsistencies = []
        
        # Simulate agent communication scenarios
        agents = ['supervisor', 'triage', 'data_helper', 'apex_optimizer']
        user_id = f"agent_test_user_{uuid.uuid4()}"
        
        try:
            # Create WebSocket for agent communication
            websocket = await self.websocket_utility.create_test_connection(
                user_id=user_id,
                connection_id=f"agent_conn_{uuid.uuid4()}"
            )
            
            # Test agent message routing consistency
            for agent_name in agents:
                agent_message = create_standard_message(
                    message_type=MessageType.AGENT_RESPONSE,
                    content={
                        "agent": agent_name,
                        "response": f"Response from {agent_name}",
                        "user_id": user_id
                    },
                    user_id=user_id
                )
                
                # Route through MessageRouter
                try:
                    routing_result = await self.message_router.route_message(
                        websocket=websocket,
                        user_id=user_id,
                        message=agent_message
                    )
                    
                    agent_messages.append({
                        'agent': agent_name,
                        'success': routing_result,
                        'message_id': getattr(agent_message, 'id', None)
                    })
                    
                except Exception as e:
                    routing_inconsistencies.append({
                        'agent': agent_name,
                        'error': str(e),
                        'message_type': MessageType.AGENT_RESPONSE
                    })
            
            # Check for routing inconsistencies
            failed_routings = [msg for msg in agent_messages if not msg['success']]
            
            # This assertion should FAIL, revealing agent routing issues
            self.assertEqual(
                len(failed_routings), 0,
                f"AGENT ROUTING INCONSISTENCY: {len(failed_routings)} agents failed routing. "
                f"Failed: {failed_routings}. Inconsistencies: {routing_inconsistencies}"
            )
            
        except Exception as e:
            # This should FAIL, revealing the communication issue
            self.fail(
                f"AGENT COMMUNICATION FAILURE: {e}. "
                f"Inconsistencies: {routing_inconsistencies}"
            )
            
    async def test_golden_path_message_flow_validation(self):
        """
        Test the complete golden path message flow through MessageRouter.
        This should FAIL initially, revealing breaks in the golden path.
        """
        golden_path_events = []
        golden_path_failures = []
        
        # Golden path: User message -> Agent processing -> Response
        user_id = f"golden_path_user_{uuid.uuid4()}"
        
        try:
            # Step 1: Create WebSocket connection
            websocket = await self.websocket_utility.create_test_connection(
                user_id=user_id,
                connection_id=f"golden_conn_{uuid.uuid4()}"
            )
            
            # Step 2: User sends message
            user_message = create_standard_message(
                message_type=MessageType.USER_MESSAGE,
                content={"text": "Help me optimize my AI workflow", "user_id": user_id},
                user_id=user_id
            )
            
            user_routing_success = await self.message_router.route_message(
                websocket=websocket,
                user_id=user_id,
                message=user_message
            )
            
            golden_path_events.append({
                'step': 'user_message',
                'success': user_routing_success,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            # Step 3: Simulate agent events that should be routed
            agent_events = [
                MessageType.AGENT_STARTED,
                MessageType.AGENT_THINKING,
                MessageType.TOOL_EXECUTING,
                MessageType.TOOL_COMPLETED,
                MessageType.AGENT_COMPLETED
            ]
            
            for event_type in agent_events:
                event_message = create_standard_message(
                    message_type=event_type,
                    content={"event": event_type.value, "user_id": user_id},
                    user_id=user_id
                )
                
                try:
                    event_routing_success = await self.message_router.route_message(
                        websocket=websocket,
                        user_id=user_id,
                        message=event_message
                    )
                    
                    golden_path_events.append({
                        'step': event_type.value,
                        'success': event_routing_success,
                        'timestamp': asyncio.get_event_loop().time()
                    })
                    
                except Exception as e:
                    golden_path_failures.append({
                        'step': event_type.value,
                        'error': str(e),
                        'critical': True
                    })
            
            # Step 4: Final agent response
            final_response = create_standard_message(
                message_type=MessageType.AGENT_RESPONSE,
                content={
                    "response": "Here's your AI optimization plan...",
                    "user_id": user_id
                },
                user_id=user_id
            )
            
            response_routing_success = await self.message_router.route_message(
                websocket=websocket,
                user_id=user_id,
                message=final_response
            )
            
            golden_path_events.append({
                'step': 'agent_response',
                'success': response_routing_success,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            # Validate golden path completion
            failed_steps = [event for event in golden_path_events if not event['success']]
            
            # This assertion should FAIL, revealing golden path breaks
            self.assertEqual(
                len(failed_steps), 0,
                f"GOLDEN PATH FAILURE: {len(failed_steps)} steps failed. "
                f"Failed steps: {failed_steps}. Critical failures: {golden_path_failures}"
            )
            
        except Exception as e:
            # This should FAIL, revealing the golden path issue
            self.fail(
                f"GOLDEN PATH EXCEPTION: {e}. "
                f"Events: {golden_path_events}. Failures: {golden_path_failures}"
            )
            
    async def test_concurrent_user_message_routing_isolation(self):
        """
        Test that concurrent users have isolated message routing.
        This should FAIL initially, revealing user isolation issues.
        """
        concurrent_users = []
        isolation_violations = []
        
        # Create multiple concurrent users
        num_users = 3
        user_ids = [f"concurrent_user_{i}_{uuid.uuid4()}" for i in range(num_users)]
        
        try:
            # Create WebSocket connections for all users
            user_connections = {}
            for user_id in user_ids:
                connection = await self.websocket_utility.create_test_connection(
                    user_id=user_id,
                    connection_id=f"concurrent_conn_{user_id}"
                )
                user_connections[user_id] = connection
            
            # Send concurrent messages from all users
            async def send_user_message(user_id: str, websocket):
                """Send message from a specific user."""
                message = create_standard_message(
                    message_type=MessageType.USER_MESSAGE,
                    content={
                        "text": f"Message from {user_id}",
                        "user_id": user_id,
                        "timestamp": asyncio.get_event_loop().time()
                    },
                    user_id=user_id
                )
                
                try:
                    routing_success = await self.message_router.route_message(
                        websocket=websocket,
                        user_id=user_id,
                        message=message
                    )
                    
                    return {
                        'user_id': user_id,
                        'success': routing_success,
                        'message_id': getattr(message, 'id', None)
                    }
                    
                except Exception as e:
                    isolation_violations.append({
                        'user_id': user_id,
                        'error': str(e),
                        'context': 'concurrent message routing'
                    })
                    return {'user_id': user_id, 'success': False, 'error': str(e)}
            
            # Execute concurrent message sending
            tasks = [
                send_user_message(user_id, user_connections[user_id])
                for user_id in user_ids
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            concurrent_users.extend([r for r in results if isinstance(r, dict)])
            
            # Check for isolation violations
            failed_users = [user for user in concurrent_users if not user.get('success', False)]
            
            # This assertion should FAIL, revealing isolation issues
            self.assertEqual(
                len(failed_users), 0,
                f"USER ISOLATION VIOLATION: {len(failed_users)} users failed routing. "
                f"Failed users: {failed_users}. Violations: {isolation_violations}"
            )
            
        except Exception as e:
            # This should FAIL, revealing the isolation issue
            self.fail(
                f"CONCURRENT USER ISOLATION FAILURE: {e}. "
                f"Users: {concurrent_users}. Violations: {isolation_violations}"
            )


if __name__ == "__main__":
    # Run async tests
    import unittest
    unittest.main(verbosity=2)