"""Test WebSocket Event Delivery Fragmentation Failures - Phase 1 Reproduction Test

This test validates Issue #564: WebSocket event delivery failures due to manager fragmentation.

CRITICAL BUSINESS CONTEXT:
- Issue: Fragmented WebSocket managers cause inconsistent event delivery 
- Business Impact: $500K+ ARR at risk due to unreliable chat functionality
- SSOT Violation: Multiple event delivery systems cause events to be lost or duplicated
- Golden Path Impact: Agent WebSocket events (90% of platform value) fail to reach users

TEST PURPOSE:
This test MUST FAIL initially to prove event delivery issues exist, then PASS after SSOT consolidation.
It demonstrates that fragmented managers create inconsistent event delivery patterns.

Expected Behavior:
- BEFORE SSOT Fix: FAIL (missing events, delivery inconsistencies, event duplication)
- AFTER SSOT Fix: PASS (reliable event delivery with consolidated SSOT manager)

Business Value Justification:
- Segment: ALL (Free -> Enterprise) - event delivery is core to all users
- Business Goal: Ensure reliable WebSocket event delivery for Golden Path chat functionality
- Value Impact: Protects real-time chat experience (90% of platform value)
- Revenue Impact: Prevents event delivery failures affecting $500K+ ARR from unreliable chat
"""

import pytest
import asyncio
import uuid
import time
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketEventDeliveryFragmentationFailures(SSotAsyncTestCase):
    """Phase 1 Reproduction Test: Prove event delivery fails with fragmented managers."""
    
    def setup_method(self, method):
        """Set up test environment for event delivery testing."""
        super().setup_method(method)
        logger.info(f"Setting up event delivery fragmentation test: {method.__name__}")
        
        # Create user context for testing
        self.test_user_context = type('TestUserContext', (), {
            'user_id': f'event_test_user_{uuid.uuid4().hex[:8]}',
            'thread_id': f'event_test_thread_{uuid.uuid4().hex[:8]}',
            'request_id': f'event_test_request_{uuid.uuid4().hex[:8]}',
            'is_test': True
        })()
        
        # Track events for validation
        self.received_events = []
        self.event_timestamps = {}
        
        logger.info(f"Created test context for event delivery: {self.test_user_context.user_id}")
    
    async def test_fragmented_managers_cause_event_delivery_inconsistencies(self):
        """
        CRITICAL REPRODUCTION TEST: Prove fragmented managers cause inconsistent event delivery.
        
        SSOT VIOLATION: All managers should deliver events reliably and consistently.
        Fragmentation causes events to be lost, duplicated, or delivered to wrong contexts.
        
        Expected Results:
        - BEFORE SSOT Fix: This test FAILS (inconsistent event delivery patterns)
        - AFTER SSOT Fix: This test PASSES (consistent event delivery from all managers)
        """
        logger.info("Testing event delivery consistency across fragmented managers")
        
        # Import different WebSocket manager implementations
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager as factory1
        from netra_backend.app.websocket_core.manager import WebSocketManager as DirectManager
        from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
        
        try:
            # Create managers via different import paths
            manager1 = await factory1(user_context=self.test_user_context, mode=WebSocketManagerMode.UNIFIED)
            manager2 = DirectManager(mode=WebSocketManagerMode.UNIFIED, user_context=self.test_user_context)
            
            logger.info(f"Created managers: {type(manager1)} and {type(manager2)}")
            
            # Create mock WebSocket connections for event testing
            mock_connection = await self._create_mock_websocket_connection()
            
            # Add connection to both managers to test event delivery
            await manager1.add_connection(mock_connection)
            await manager2.add_connection(mock_connection)
            
            # Test critical WebSocket events that support Golden Path chat functionality
            critical_events = [
                {'event': 'agent_started', 'data': {'agent_type': 'supervisor', 'user_id': self.test_user_context.user_id}},
                {'event': 'agent_thinking', 'data': {'thought': 'Processing user request', 'progress': 25}},
                {'event': 'tool_executing', 'data': {'tool': 'data_analysis', 'parameters': {'query': 'test'}}},
                {'event': 'tool_completed', 'data': {'tool': 'data_analysis', 'result': 'analysis_complete'}},
                {'event': 'agent_completed', 'data': {'result': 'Task completed successfully', 'final': True}}
            ]
            
            # Send events through Manager1 and track delivery
            manager1_delivered_events = []
            for event in critical_events:
                try:
                    await self._send_event_and_track(manager1, event, manager1_delivered_events)
                except Exception as e:
                    logger.error(f"Manager1 event delivery failed for {event['event']}: {e}")
            
            # Send same events through Manager2 and track delivery
            manager2_delivered_events = []
            for event in critical_events:
                try:
                    await self._send_event_and_track(manager2, event, manager2_delivered_events)
                except Exception as e:
                    logger.error(f"Manager2 event delivery failed for {event['event']}: {e}")
            
            logger.info(f"Manager1 delivered {len(manager1_delivered_events)} events")
            logger.info(f"Manager2 delivered {len(manager2_delivered_events)} events")
            
            # CRITICAL SSOT TEST: Both managers should deliver all events consistently
            expected_event_count = len(critical_events)
            
            # Test Manager1 event delivery completeness
            if len(manager1_delivered_events) != expected_event_count:
                logger.error(f"❌ EVENT DELIVERY FAILURE: Manager1 delivered {len(manager1_delivered_events)}/{expected_event_count} events")
                missing_events = [e['event'] for e in critical_events if e['event'] not in [d['event'] for d in manager1_delivered_events]]
                logger.error(f"Missing events from Manager1: {missing_events}")
                
                pytest.fail(
                    f"MANAGER1 EVENT DELIVERY FAILURE: Delivered {len(manager1_delivered_events)}/{expected_event_count} events. "
                    f"Missing critical events: {missing_events}. "
                    f"SSOT Violation: Fragmented manager failed to deliver all Golden Path events. "
                    f"Business Impact: Users miss critical chat progress updates, degrading experience "
                    f"and affecting $500K+ ARR from unreliable event delivery."
                )
            
            # Test Manager2 event delivery completeness
            if len(manager2_delivered_events) != expected_event_count:
                logger.error(f"❌ EVENT DELIVERY FAILURE: Manager2 delivered {len(manager2_delivered_events)}/{expected_event_count} events")
                missing_events = [e['event'] for e in critical_events if e['event'] not in [d['event'] for d in manager2_delivered_events]]
                logger.error(f"Missing events from Manager2: {missing_events}")
                
                pytest.fail(
                    f"MANAGER2 EVENT DELIVERY FAILURE: Delivered {len(manager2_delivered_events)}/{expected_event_count} events. "
                    f"Missing critical events: {missing_events}. "
                    f"SSOT Violation: Fragmented manager inconsistent with primary manager. "
                    f"Business Impact: Event delivery varies by import path, creating unreliable user experience."
                )
            
            # Test event delivery consistency between managers
            await self._validate_event_delivery_consistency(manager1_delivered_events, manager2_delivered_events)
            
            logger.info("✅ Event delivery consistency test PASSED - all managers delivered events reliably")
            
        except Exception as e:
            logger.error(f"❌ EVENT DELIVERY FRAGMENTATION TEST FAILED: {e}")
            raise
    
    async def _create_mock_websocket_connection(self):
        """Create a mock WebSocket connection for event testing."""
        connection = type('MockWebSocketConnection', (), {
            'connection_id': f'event_test_conn_{uuid.uuid4().hex[:8]}',
            'user_id': self.test_user_context.user_id,
            'thread_id': self.test_user_context.thread_id,
            'websocket': type('MockWebSocket', (), {
                'send_text': self._mock_websocket_send,
                'send_json': self._mock_websocket_send_json,
                'is_closed': False
            })(),
            'is_active': True,
            'events_received': []  # Track events for this connection
        })()
        
        logger.info(f"Created mock WebSocket connection: {connection.connection_id}")
        return connection
    
    async def _mock_websocket_send(self, message):
        """Mock WebSocket send_text method."""
        timestamp = time.time()
        self.received_events.append({
            'type': 'text',
            'message': message,
            'timestamp': timestamp,
            'connection_id': 'mock_connection'
        })
        logger.debug(f"Mock WebSocket received text: {message}")
    
    async def _mock_websocket_send_json(self, data):
        """Mock WebSocket send_json method."""
        timestamp = time.time()
        event_name = data.get('event', 'unknown')
        self.event_timestamps[event_name] = timestamp
        
        self.received_events.append({
            'type': 'json',
            'data': data,
            'timestamp': timestamp,
            'connection_id': 'mock_connection'
        })
        logger.debug(f"Mock WebSocket received JSON: {data}")
    
    async def _send_event_and_track(self, manager, event, delivered_events):
        """Send an event through a manager and track delivery."""
        event_name = event['event']
        event_data = event['data']
        
        try:
            # Try different event sending methods based on manager interface
            if hasattr(manager, 'send_event'):
                await manager.send_event(event_name, event_data, user_id=self.test_user_context.user_id)
            elif hasattr(manager, 'broadcast_event'):
                await manager.broadcast_event(event_name, event_data, user_id=self.test_user_context.user_id)
            elif hasattr(manager, 'emit_event'):
                await manager.emit_event(event_name, event_data, user_id=self.test_user_context.user_id)
            elif hasattr(manager, 'broadcast_message'):
                # Fallback to broadcast_message if specific event methods not available
                message = {'event': event_name, 'data': event_data}
                await manager.broadcast_message(message, user_id=self.test_user_context.user_id)
            else:
                logger.warning(f"Manager {type(manager)} has no known event sending interface")
                return
            
            # Allow time for event to be processed
            await asyncio.sleep(0.1)
            
            # Check if event was delivered
            event_delivered = any(
                e.get('data', {}).get('event') == event_name or 
                e.get('type') == 'json' and e.get('data', {}).get('event') == event_name
                for e in self.received_events
            )
            
            if event_delivered:
                delivered_events.append({
                    'event': event_name,
                    'data': event_data,
                    'timestamp': time.time(),
                    'manager_type': type(manager).__name__
                })
                logger.debug(f"✅ Event {event_name} delivered successfully via {type(manager).__name__}")
            else:
                logger.error(f"❌ Event {event_name} NOT delivered via {type(manager).__name__}")
                
        except Exception as e:
            logger.error(f"Failed to send event {event_name} via {type(manager)}: {e}")
            raise
    
    async def _validate_event_delivery_consistency(self, manager1_events, manager2_events):
        """Validate that both managers deliver events consistently."""
        logger.info("Validating event delivery consistency between managers")
        
        # Check that both managers delivered the same events
        manager1_event_names = {e['event'] for e in manager1_events}
        manager2_event_names = {e['event'] for e in manager2_events}
        
        if manager1_event_names != manager2_event_names:
            logger.error("❌ EVENT CONSISTENCY FAILURE: Managers delivered different event sets")
            manager1_only = manager1_event_names - manager2_event_names
            manager2_only = manager2_event_names - manager1_event_names
            
            logger.error(f"Events only from Manager1: {manager1_only}")
            logger.error(f"Events only from Manager2: {manager2_only}")
            
            pytest.fail(
                f"EVENT SET INCONSISTENCY: Manager1 events {manager1_event_names} != "
                f"Manager2 events {manager2_event_names}. "
                f"SSOT Violation: Fragmented managers deliver different event sets. "
                f"Business Impact: Users get inconsistent chat updates depending on which "
                f"manager handles their connection, creating unpredictable experience."
            )
        
        # Check event timing consistency (should be similar if both managers work properly)
        for event_name in manager1_event_names:
            manager1_event = next((e for e in manager1_events if e['event'] == event_name), None)
            manager2_event = next((e for e in manager2_events if e['event'] == event_name), None)
            
            if manager1_event and manager2_event:
                time_diff = abs(manager1_event['timestamp'] - manager2_event['timestamp'])
                # Allow for reasonable timing differences (up to 1 second)
                if time_diff > 1.0:
                    logger.warning(
                        f"⚠️ TIMING INCONSISTENCY: Event {event_name} timing differs by {time_diff:.2f}s "
                        f"between managers. This may indicate delivery path differences."
                    )
        
        logger.info("✅ Event delivery consistency validated between managers")
    
    async def test_event_deduplication_with_fragmented_managers(self):
        """
        REPRODUCTION TEST: Verify fragmented managers don't cause event duplication.
        
        SSOT VIOLATION: Multiple managers handling the same user should not cause
        duplicate events. Fragmentation may lead to events being sent multiple times.
        """
        logger.info("Testing event deduplication with fragmented managers")
        
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
        
        try:
            # Create multiple managers for the same user (potential duplication scenario)
            manager1 = await get_websocket_manager(user_context=self.test_user_context)
            manager2 = await get_websocket_manager(user_context=self.test_user_context)
            
            # Create connection and add to both managers
            mock_connection = await self._create_mock_websocket_connection()
            await manager1.add_connection(mock_connection)
            await manager2.add_connection(mock_connection)
            
            # Clear previous events
            self.received_events.clear()
            
            # Send a test event through both managers
            test_event = {
                'event': 'agent_thinking',
                'data': {'thought': 'Testing deduplication', 'unique_id': str(uuid.uuid4())}
            }
            
            # Send same event through both managers
            await self._send_event_and_track(manager1, test_event, [])
            await self._send_event_and_track(manager2, test_event, [])
            
            # Allow time for all events to be processed
            await asyncio.sleep(0.2)
            
            # Count how many times the event was received
            agent_thinking_events = [
                e for e in self.received_events 
                if e.get('data', {}).get('event') == 'agent_thinking' or
                   (e.get('type') == 'json' and e.get('data', {}).get('event') == 'agent_thinking')
            ]
            
            logger.info(f"Received {len(agent_thinking_events)} agent_thinking events")
            
            # CRITICAL DEDUPLICATION TEST: Should receive event only once despite two managers
            if len(agent_thinking_events) > 1:
                logger.error("❌ EVENT DUPLICATION DETECTED: Same event delivered multiple times!")
                for i, event in enumerate(agent_thinking_events):
                    logger.error(f"Duplicate #{i+1}: {event}")
                
                pytest.fail(
                    f"EVENT DUPLICATION FAILURE: Received {len(agent_thinking_events)} copies of the same event. "
                    f"SSOT Violation: Fragmented managers cause duplicate event delivery. "
                    f"Business Impact: Users receive duplicate chat notifications, creating poor UX "
                    f"and potential confusion in $500K+ ARR chat interactions."
                )
            elif len(agent_thinking_events) == 0:
                logger.error("❌ EVENT DELIVERY FAILURE: No events received despite sending through both managers!")
                pytest.fail(
                    f"EVENT DELIVERY FAILURE: No events delivered despite sending through two managers. "
                    f"SSOT Violation: Fragmented managers failed to deliver events. "
                    f"Business Impact: Users miss critical chat updates, breaking Golden Path experience."
                )
            
            logger.info("✅ Event deduplication working properly - no duplicate events detected")
            
        except Exception as e:
            logger.error(f"❌ EVENT DEDUPLICATION TEST FAILED: {e}")
            raise
    
    async def test_event_ordering_consistency_across_managers(self):
        """
        REPRODUCTION TEST: Verify event ordering remains consistent across fragmented managers.
        
        SSOT VIOLATION: Events should maintain chronological order regardless of which
        manager delivers them. Fragmentation may cause order inconsistencies.
        """
        logger.info("Testing event ordering consistency across managers")
        
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        try:
            # Create managers for ordering test
            manager1 = await get_websocket_manager(user_context=self.test_user_context)
            manager2 = await get_websocket_manager(user_context=self.test_user_context)
            
            # Create connection
            mock_connection = await self._create_mock_websocket_connection()
            await manager1.add_connection(mock_connection)
            await manager2.add_connection(mock_connection)
            
            # Clear previous events
            self.received_events.clear()
            
            # Send events in sequence through alternating managers to test ordering
            ordered_events = [
                {'event': 'agent_started', 'data': {'sequence': 1, 'agent': 'supervisor'}},
                {'event': 'agent_thinking', 'data': {'sequence': 2, 'thought': 'First thought'}},
                {'event': 'tool_executing', 'data': {'sequence': 3, 'tool': 'analyzer'}},
                {'event': 'agent_thinking', 'data': {'sequence': 4, 'thought': 'Second thought'}},
                {'event': 'agent_completed', 'data': {'sequence': 5, 'result': 'Complete'}}
            ]
            
            # Send events alternating between managers with small delays
            for i, event in enumerate(ordered_events):
                manager = manager1 if i % 2 == 0 else manager2
                await self._send_event_and_track(manager, event, [])
                await asyncio.sleep(0.05)  # Small delay to establish order
            
            # Allow time for all events to be processed
            await asyncio.sleep(0.2)
            
            # Extract received events and check ordering
            received_json_events = [
                e for e in self.received_events 
                if e.get('type') == 'json' and 'sequence' in e.get('data', {}).get('data', {})
            ]
            
            logger.info(f"Received {len(received_json_events)} ordered events")
            
            # Sort received events by timestamp to check if they arrived in order
            received_json_events.sort(key=lambda x: x['timestamp'])
            
            # Check if sequence numbers are in order
            sequences = [
                e['data']['data']['sequence'] 
                for e in received_json_events 
                if 'sequence' in e.get('data', {}).get('data', {})
            ]
            
            expected_sequence = list(range(1, len(ordered_events) + 1))
            
            if sequences != expected_sequence:
                logger.error("❌ EVENT ORDERING FAILURE: Events received out of order!")
                logger.error(f"Expected sequence: {expected_sequence}")
                logger.error(f"Received sequence: {sequences}")
                
                pytest.fail(
                    f"EVENT ORDERING INCONSISTENCY: Expected sequence {expected_sequence}, "
                    f"received {sequences}. "
                    f"SSOT Violation: Fragmented managers cause event ordering inconsistencies. "
                    f"Business Impact: Chat messages and agent updates arrive out of order, "
                    f"confusing users and degrading $500K+ ARR chat experience quality."
                )
            
            logger.info("✅ Event ordering maintained consistently across managers")
            
        except Exception as e:
            logger.error(f"❌ EVENT ORDERING TEST FAILED: {e}")
            raise

    def teardown_method(self, method):
        """Clean up test environment."""
        logger.info(f"Tearing down event delivery fragmentation test: {method.__name__}")
        # Clear tracked events
        self.received_events.clear()
        self.event_timestamps.clear()
        super().teardown_method(method)