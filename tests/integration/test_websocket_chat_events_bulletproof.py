#!/usr/bin/env python
"""MISSION CRITICAL INTEGRATION TEST: WebSocket Chat Event Flow

Business Value: $500K+ ARR - Real-time chat interaction and agent visibility
CHAT IS KING - THIS TEST MUST PASS.

Tests the complete WebSocket event flow for chat interactions:
1. All required agent events per spec
2. Event ordering and timing
3. Message correlation and deduplication
4. Error recovery and resilience
5. Performance under load

NO MOCKS - Uses real WebSocket connections and services.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import threading
import pytest
from loguru import logger
import websockets
from websockets.exceptions import WebSocketException
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import production components
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)


# ============================================================================
# WEBSOCKET EVENT VALIDATOR
# ============================================================================

class WebSocketEventValidator:
    """Validates WebSocket events against specification requirements."""
    
    # Required events from SPEC/learnings/websocket_agent_integration_critical.xml
    REQUIRED_EVENTS = {
        'agent_started': {'critical': True, 'description': 'User must know agent is processing'},
        'agent_thinking': {'critical': True, 'description': 'Real-time reasoning visibility'},
        'tool_executing': {'critical': True, 'description': 'Tool usage transparency'},
        'tool_completed': {'critical': True, 'description': 'Tool results display'},
        'agent_completed': {'critical': True, 'description': 'User must know when done'},
        'partial_result': {'critical': False, 'description': 'Streaming response UX'},
        'final_report': {'critical': False, 'description': 'Comprehensive summary'}
    }
    
    # Event ordering rules
    EVENT_SEQUENCES = [
        ['agent_started', 'agent_thinking'],
        ['tool_executing', 'tool_completed'],
        ['agent_started', 'agent_completed']
    ]
    
    # Timing constraints (milliseconds)
    MAX_EVENT_DELAYS = {
        'agent_started': 500,  # Must start within 500ms
        'agent_thinking': 1000,  # Thinking events within 1s
        'tool_executing': 2000,  # Tool execution within 2s
        'agent_completed': 30000  # Complete within 30s
    }
    
    def __init__(self):
        self.events: List[Dict] = []
        self.event_times: Dict[str, float] = {}
        self.validation_errors: List[str] = []
        
    def add_event(self, event: Dict) -> None:
        """Add an event for validation."""
        event_type = event.get('type')
        timestamp = time.time()
        
        self.events.append({
            'event': event,
            'timestamp': timestamp,
            'type': event_type
        })
        
        if event_type not in self.event_times:
            self.event_times[event_type] = []
        self.event_times[event_type].append(timestamp)
        
        logger.debug(f"Event received: {event_type} at {timestamp}")
    
    def validate_required_events(self) -> bool:
        """Validate all critical required events are present."""
        received_types = {e['type'] for e in self.events}
        
        for event_type, config in self.REQUIRED_EVENTS.items():
            if config['critical'] and event_type not in received_types:
                self.validation_errors.append(
                    f"Missing critical event: {event_type} - {config['description']}"
                )
                
        return len(self.validation_errors) == 0
    
    def validate_event_ordering(self) -> bool:
        """Validate events follow correct ordering."""
        event_sequence = [e['type'] for e in self.events]
        
        for required_seq in self.EVENT_SEQUENCES:
            # Check if required sequence exists in order
            seq_indices = []
            for event in required_seq:
                try:
                    idx = event_sequence.index(event)
                    seq_indices.append(idx)
                except ValueError:
                    # Event not found, might be optional
                    continue
            
            # Validate ordering if all events present
            if len(seq_indices) == len(required_seq):
                if seq_indices != sorted(seq_indices):
                    self.validation_errors.append(
                        f"Invalid event ordering: {required_seq} not in correct order"
                    )
                    
        return len(self.validation_errors) == 0
    
    def validate_event_timing(self, start_time: float) -> bool:
        """Validate events occur within timing constraints."""
        for event_type, max_delay in self.MAX_EVENT_DELAYS.items():
            if event_type in self.event_times:
                first_occurrence = min(self.event_times[event_type])
                delay = (first_occurrence - start_time) * 1000  # Convert to ms
                
                if delay > max_delay:
                    self.validation_errors.append(
                        f"Event {event_type} delayed by {delay:.0f}ms (max: {max_delay}ms)"
                    )
                    
        return len(self.validation_errors) == 0
    
    def validate_event_pairing(self) -> bool:
        """Validate paired events (e.g., tool_executing/tool_completed)."""
        event_counts = {}
        for event in self.events:
            event_type = event['type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # Check tool events are paired
        executing_count = event_counts.get('tool_executing', 0)
        completed_count = event_counts.get('tool_completed', 0)
        
        if executing_count != completed_count:
            self.validation_errors.append(
                f"Unpaired tool events: {executing_count} executing, {completed_count} completed"
            )
            
        return len(self.validation_errors) == 0
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get comprehensive validation report."""
        received_types = {e['type'] for e in self.events}
        critical_events = {k for k, v in self.REQUIRED_EVENTS.items() if v['critical']}
        
        return {
            'total_events': len(self.events),
            'unique_event_types': len(received_types),
            'received_types': list(received_types),
            'critical_events_received': list(critical_events & received_types),
            'critical_events_missing': list(critical_events - received_types),
            'validation_errors': self.validation_errors,
            'is_valid': len(self.validation_errors) == 0
        }


# ============================================================================
# WEBSOCKET CLIENT SIMULATOR
# ============================================================================

class WebSocketChatClient:
    """Simulates a frontend WebSocket client for chat interactions."""
    
    def __init__(self, client_id: str = None):
        self.client_id = client_id or f"test_client_{uuid.uuid4().hex[:8]}"
        self.websocket = None
        self.connected = False
        self.validator = WebSocketEventValidator()
        self.messages_sent = []
        self.messages_received = []
        self.errors = []
        
    async def connect(self, url: str, token: str) -> bool:
        """Connect to WebSocket server with authentication."""
        try:
            # Add token to URL or headers based on server config
            ws_url = f"{url}?jwt={token}"
            
            # Connect with subprotocol for auth
            self.websocket = await websockets.connect(
                ws_url,
                subprotocols=[f"jwt.{token}"],
                ping_interval=10,
                ping_timeout=5
            )
            
            self.connected = True
            logger.info(f"Client {self.client_id} connected to WebSocket")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.errors.append({'phase': 'connection', 'error': str(e)})
            return False
    
    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.messages_received.append(data)
                    self.validator.add_event(data)
                    
                    # Log important events
                    event_type = data.get('type')
                    if event_type in WebSocketEventValidator.REQUIRED_EVENTS:
                        logger.info(f"Client {self.client_id} received: {event_type}")
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message[:100]}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {self.client_id} connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error in message listener: {e}")
            self.errors.append({'phase': 'listening', 'error': str(e)})
    
    async def send_chat_message(self, content: str, thread_id: str = None) -> Dict[str, Any]:
        """Send a chat message and track response events."""
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        thread_id = thread_id or f"thread_{uuid.uuid4().hex[:8]}"
        
        message = {
            "type": "user_message",
            "payload": {
                "content": content,
                "thread_id": thread_id,
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat(),
                "client_id": self.client_id
            }
        }
        
        try:
            start_time = time.time()
            await self.websocket.send(json.dumps(message))
            self.messages_sent.append(message)
            
            logger.info(f"Client {self.client_id} sent message: {message_id}")
            
            # Wait for agent_completed event or timeout
            timeout = 30  # 30 seconds max
            while time.time() - start_time < timeout:
                # Check if we received agent_completed
                completed_events = [
                    e for e in self.validator.events 
                    if e['type'] == 'agent_completed'
                ]
                
                if completed_events:
                    elapsed = time.time() - start_time
                    logger.info(f"Message processing completed in {elapsed:.2f}s")
                    
                    # Validate all events
                    self.validator.validate_required_events()
                    self.validator.validate_event_ordering()
                    self.validator.validate_event_timing(start_time)
                    self.validator.validate_event_pairing()
                    
                    return {
                        'success': True,
                        'message_id': message_id,
                        'processing_time': elapsed,
                        'validation_report': self.validator.get_validation_report()
                    }
                
                await asyncio.sleep(0.1)
            
            # Timeout reached
            return {
                'success': False,
                'error': 'Timeout waiting for agent_completed',
                'message_id': message_id,
                'validation_report': self.validator.get_validation_report()
            }
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {'success': False, 'error': str(e)}
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info(f"Client {self.client_id} disconnected")


# ============================================================================
# INTEGRATION TEST SUITE
# ============================================================================

class WebSocketChatIntegrationTest:
    """Comprehensive WebSocket chat integration tests."""
    
    def __init__(self):
        self.ws_manager = WebSocketManager()
        self.agent_registry = AgentRegistry()
        self.clients: List[WebSocketChatClient] = []
        
    async def setup(self):
        """Set up test environment."""
        # Ensure WebSocket manager is enhanced
        self.agent_registry.set_websocket_manager(self.ws_manager)
        
        # Verify enhancement
        if hasattr(self.agent_registry.tool_dispatcher, '_websocket_enhanced'):
            logger.info("Tool dispatcher properly enhanced with WebSocket notifications")
        else:
            logger.error("CRITICAL: Tool dispatcher not enhanced!")
            
    async def test_single_message_flow(self, token: str) -> Dict[str, Any]:
        """Test single message flow with all required events."""
        client = WebSocketChatClient()
        self.clients.append(client)
        
        # Connect client
        ws_url = "ws://localhost:8080/ws"
        connected = await client.connect(ws_url, token)
        if not connected:
            return {'success': False, 'error': 'Connection failed'}
        
        # Send test message
        result = await client.send_chat_message(
            "Test message for WebSocket event validation"
        )
        
        # Disconnect
        await client.disconnect()
        
        return result
    
    async def test_concurrent_messages(self, token: str, num_messages: int = 5) -> Dict[str, Any]:
        """Test multiple concurrent messages from single client."""
        client = WebSocketChatClient()
        self.clients.append(client)
        
        # Connect
        ws_url = "ws://localhost:8080/ws"
        connected = await client.connect(ws_url, token)
        if not connected:
            return {'success': False, 'error': 'Connection failed'}
        
        # Send multiple messages concurrently
        tasks = []
        for i in range(num_messages):
            task = client.send_chat_message(f"Concurrent message {i}")
            tasks.append(task)
            await asyncio.sleep(0.1)  # Small delay between messages
        
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful = sum(1 for r in results if r.get('success'))
        
        await client.disconnect()
        
        return {
            'success': successful == num_messages,
            'total': num_messages,
            'successful': successful,
            'results': results
        }
    
    async def test_message_deduplication(self, token: str) -> Dict[str, Any]:
        """Test that duplicate messages are properly handled."""
        client = WebSocketChatClient()
        self.clients.append(client)
        
        # Connect
        ws_url = "ws://localhost:8080/ws"
        await client.connect(ws_url, token)
        
        # Send same message twice with same ID
        message_id = f"dup_test_{uuid.uuid4().hex[:8]}"
        
        message = {
            "type": "user_message",
            "payload": {
                "content": "Test deduplication",
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Send twice
        await client.websocket.send(json.dumps(message))
        await asyncio.sleep(0.5)
        await client.websocket.send(json.dumps(message))
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Check for duplicate handling
        agent_started_events = [
            e for e in client.validator.events 
            if e['type'] == 'agent_started'
        ]
        
        await client.disconnect()
        
        # Should only process once
        return {
            'success': len(agent_started_events) == 1,
            'agent_started_count': len(agent_started_events),
            'total_events': len(client.validator.events)
        }
    
    async def test_websocket_reconnection(self, token: str) -> Dict[str, Any]:
        """Test WebSocket reconnection and message continuity."""
        client = WebSocketChatClient()
        self.clients.append(client)
        
        # Initial connection
        ws_url = "ws://localhost:8080/ws"
        await client.connect(ws_url, token)
        
        # Send first message
        result1 = await client.send_chat_message("Message before disconnect")
        
        # Simulate disconnect
        await client.websocket.close()
        await asyncio.sleep(1)
        
        # Reconnect
        await client.connect(ws_url, token)
        
        # Send second message
        result2 = await client.send_chat_message("Message after reconnect")
        
        await client.disconnect()
        
        return {
            'success': result1.get('success') and result2.get('success'),
            'before_disconnect': result1,
            'after_reconnect': result2
        }
    
    async def test_error_recovery(self, token: str) -> Dict[str, Any]:
        """Test error recovery and resilience."""
        client = WebSocketChatClient()
        self.clients.append(client)
        
        ws_url = "ws://localhost:8080/ws"
        await client.connect(ws_url, token)
        
        # Send malformed message
        try:
            await client.websocket.send("INVALID JSON {[}")
        except:
            pass
        
        # Connection should still work
        await asyncio.sleep(0.5)
        
        # Send valid message
        result = await client.send_chat_message("Valid message after error")
        
        await client.disconnect()
        
        return {
            'success': result.get('success'),
            'recovered': client.connected,
            'result': result
        }


# ============================================================================
# STRESS TEST: HIGH VOLUME EVENTS
# ============================================================================

class WebSocketEventStressTest:
    """Stress test for high volume WebSocket events."""
    
    async def test_event_storm(self, token: str, num_clients: int = 10, messages_per_client: int = 5):
        """Test system under high event load."""
        clients = []
        
        # Create and connect multiple clients
        for i in range(num_clients):
            client = WebSocketChatClient(f"stress_client_{i}")
            connected = await client.connect("ws://localhost:8080/ws", token)
            if connected:
                clients.append(client)
            await asyncio.sleep(0.05)  # Stagger connections
        
        logger.info(f"Connected {len(clients)} clients for stress test")
        
        # Send messages from all clients concurrently
        all_tasks = []
        for client in clients:
            for j in range(messages_per_client):
                task = client.send_chat_message(f"Stress test message {j}")
                all_tasks.append(task)
                await asyncio.sleep(0.01)  # Small delay
        
        # Wait for all messages to process
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Disconnect all clients
        for client in clients:
            await client.disconnect()
        
        # Analyze results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        failed = len(results) - successful
        
        # Check validation reports
        validation_errors = []
        for r in results:
            if isinstance(r, dict) and 'validation_report' in r:
                report = r['validation_report']
                if not report['is_valid']:
                    validation_errors.extend(report['validation_errors'])
        
        return {
            'total_messages': len(results),
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / len(results)) * 100 if results else 0,
            'validation_errors': validation_errors[:10]  # First 10 errors
        }


# ============================================================================
# TEST CASES
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.mission_critical
async def test_websocket_chat_events_complete_flow():
    """Test complete WebSocket chat event flow."""
    test = WebSocketChatIntegrationTest()
    await test.setup()
    
    # Get test token using SSOT E2E auth helper
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    auth_helper = E2EAuthHelper()
    token = auth_helper.create_test_jwt_token(
        user_id="test_user",
        email="test@netra.ai"
    )
    
    result = await test.test_single_message_flow(token)
    
    assert result['success'], f"Chat flow failed: {result.get('error')}"
    
    # Validate all required events received
    report = result['validation_report']
    assert report['is_valid'], f"Validation errors: {report['validation_errors']}"
    assert len(report['critical_events_missing']) == 0, \
        f"Missing critical events: {report['critical_events_missing']}"


@pytest.mark.asyncio
@pytest.mark.mission_critical
async def test_websocket_concurrent_messages():
    """Test concurrent message handling."""
    test = WebSocketChatIntegrationTest()
    await test.setup()
    
    # Get test token using SSOT E2E auth helper
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    auth_helper = E2EAuthHelper()
    token = auth_helper.create_test_jwt_token(
        user_id="test_user",
        email="test@netra.ai"
    )
    
    result = await test.test_concurrent_messages(token, num_messages=5)
    
    assert result['success'], f"Concurrent messages failed: {result['successful']}/{result['total']}"


@pytest.mark.asyncio
@pytest.mark.mission_critical
async def test_websocket_deduplication():
    """Test message deduplication."""
    test = WebSocketChatIntegrationTest()
    await test.setup()
    
    # Get test token using SSOT E2E auth helper
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    auth_helper = E2EAuthHelper()
    token = auth_helper.create_test_jwt_token(
        user_id="test_user",
        email="test@netra.ai"
    )
    
    result = await test.test_message_deduplication(token)
    
    assert result['success'], f"Deduplication failed: {result['agent_started_count']} agent_started events"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_websocket_event_storm():
    """Stress test with high volume of events."""
    stress_test = WebSocketEventStressTest()
    
    # Get test token using SSOT E2E auth helper
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    auth_helper = E2EAuthHelper()
    token = auth_helper.create_test_jwt_token(
        user_id="test_user",
        email="test@netra.ai"
    )
    
    result = await stress_test.test_event_storm(
        token,
        num_clients=5,
        messages_per_client=3
    )
    
    logger.info(f"Stress test results: {json.dumps(result, indent=2)}")
    
    # At least 80% success rate
    assert result['success_rate'] >= 80, \
        f"Too many failures: {result['failed']}/{result['total_messages']}"


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    # Run with detailed logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="DEBUG"
    )
    
    # Run tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "mission_critical",
        "--asyncio-mode=auto"
    ])