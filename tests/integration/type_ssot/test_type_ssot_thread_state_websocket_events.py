"""
Test Thread State WebSocket Event Type Consistency

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket thread state events deliver real-time chat value
- Value Impact: Thread state events inform users of conversation progress
- Strategic Impact: Real-time updates are core to chat UX and $120K+ MRR retention

CRITICAL: WebSocket thread state events must use strongly typed ThreadState
definitions to prevent event delivery failures and maintain user experience.
Event type mismatches cause silent failures and broken real-time updates.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.types.core_types import ThreadID, UserID, WebSocketID, ConnectionID


@dataclass
class ThreadStateEvent:
    """Strongly typed thread state event for testing."""
    event_type: str
    thread_id: ThreadID
    user_id: UserID
    old_state: Optional[str]
    new_state: str
    timestamp: float
    connection_id: Optional[ConnectionID] = None


class TestThreadStateWebSocketEventConsistency(BaseIntegrationTest):
    """Integration tests for thread state WebSocket event type consistency."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_thread_state_event_structure_validation(self, real_services_fixture):
        """
        Test that WebSocket thread state events have consistent, strongly typed structure.
        
        MISSION CRITICAL: Event structure consistency ensures reliable real-time updates.
        Malformed events break user chat experience and conversation flow.
        """
        # Setup real Redis for event publishing/subscribing
        redis_client = real_services_fixture['redis']
        
        # Mock WebSocket event publisher
        class WebSocketEventPublisher:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.published_events = []
            
            async def publish_thread_state_change(self, event: ThreadStateEvent):
                # Validate event structure before publishing
                assert isinstance(event.thread_id, ThreadID), (
                    f"thread_id must be ThreadID, got {type(event.thread_id)}"
                )
                assert isinstance(event.user_id, UserID), (
                    f"user_id must be UserID, got {type(event.user_id)}"
                )
                assert isinstance(event.new_state, str), (
                    f"new_state must be string, got {type(event.new_state)}"
                )
                assert event.new_state in ['active', 'processing', 'waiting', 'completed', 'error'], (
                    f"new_state must be valid state, got '{event.new_state}'"
                )
                
                # Serialize event for Redis publishing
                event_data = {
                    'event_type': event.event_type,
                    'thread_id': str(event.thread_id),
                    'user_id': str(event.user_id),
                    'old_state': event.old_state,
                    'new_state': event.new_state,
                    'timestamp': event.timestamp
                }
                
                if event.connection_id:
                    event_data['connection_id'] = str(event.connection_id)
                
                # Publish to Redis channel
                channel = f"websocket:thread_events:{event.user_id}"
                await self.redis.publish(channel, json.dumps(event_data))
                
                self.published_events.append(event)
        
        publisher = WebSocketEventPublisher(redis_client)
        
        # Test event creation and validation
        test_events = [
            ThreadStateEvent(
                event_type="thread_state_change",
                thread_id=ThreadID("ws-thread-001"),
                user_id=UserID("ws-user-001"),
                old_state="active",
                new_state="processing",
                timestamp=asyncio.get_event_loop().time(),
                connection_id=ConnectionID("conn-001")
            ),
            ThreadStateEvent(
                event_type="thread_state_change",
                thread_id=ThreadID("ws-thread-002"),
                user_id=UserID("ws-user-002"),
                old_state=None,  # Initial state
                new_state="active",
                timestamp=asyncio.get_event_loop().time()
            )
        ]
        
        # Publish events and validate structure
        for event in test_events:
            await publisher.publish_thread_state_change(event)
        
        # Validate all events were published successfully
        assert len(publisher.published_events) == len(test_events), (
            f"Expected {len(test_events)} events published, got {len(publisher.published_events)}"
        )
        
        # Validate event type consistency
        for i, published_event in enumerate(publisher.published_events):
            original_event = test_events[i]
            
            assert published_event.thread_id == original_event.thread_id, (
                f"Event {i}: thread_id mismatch"
            )
            assert published_event.user_id == original_event.user_id, (
                f"Event {i}: user_id mismatch"
            )
            assert published_event.new_state == original_event.new_state, (
                f"Event {i}: new_state mismatch"
            )


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_state_event_user_isolation(self, real_services_fixture):
        """
        Test that thread state events maintain proper user isolation.
        
        SECURITY CRITICAL: Events must only reach intended users to prevent
        information leakage and maintain multi-user security.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock WebSocket event subscriber
        class WebSocketEventSubscriber:
            def __init__(self, redis_client, user_id: UserID):
                self.redis = redis_client
                self.user_id = user_id
                self.received_events = []
                self.channel = f"websocket:thread_events:{user_id}"
            
            async def subscribe_and_listen(self, duration_seconds: float = 1.0):
                pubsub = self.redis.pubsub()
                await pubsub.subscribe(self.channel)
                
                try:
                    # Listen for events
                    end_time = asyncio.get_event_loop().time() + duration_seconds
                    while asyncio.get_event_loop().time() < end_time:
                        message = await pubsub.get_message(timeout=0.1)
                        if message and message['type'] == 'message':
                            event_data = json.loads(message['data'].decode())
                            self.received_events.append(event_data)
                        await asyncio.sleep(0.05)  # Small delay to prevent tight loop
                finally:
                    await pubsub.unsubscribe(self.channel)
                    await pubsub.close()
        
        # Create subscribers for different users
        user1_id = UserID("isolation-user-001")
        user2_id = UserID("isolation-user-002")
        user3_id = UserID("isolation-user-003")
        
        subscriber1 = WebSocketEventSubscriber(redis_client, user1_id)
        subscriber2 = WebSocketEventSubscriber(redis_client, user2_id)
        subscriber3 = WebSocketEventSubscriber(redis_client, user3_id)
        
        # Start listening concurrently
        listen_tasks = [
            subscriber1.subscribe_and_listen(2.0),
            subscriber2.subscribe_and_listen(2.0),
            subscriber3.subscribe_and_listen(2.0)
        ]
        
        # Start listeners
        listen_futures = [asyncio.create_task(task) for task in listen_tasks]
        await asyncio.sleep(0.2)  # Allow subscribers to start
        
        # Publish events for different users
        test_events = [
            # User 1 events
            {
                'event_type': 'thread_state_change',
                'thread_id': str(ThreadID("iso-thread-001")),
                'user_id': str(user1_id),
                'old_state': 'active',
                'new_state': 'processing',
                'timestamp': asyncio.get_event_loop().time()
            },
            # User 2 events
            {
                'event_type': 'thread_state_change',
                'thread_id': str(ThreadID("iso-thread-002")),
                'user_id': str(user2_id),
                'old_state': 'waiting',
                'new_state': 'active',
                'timestamp': asyncio.get_event_loop().time()
            },
            # User 3 events
            {
                'event_type': 'thread_state_change',
                'thread_id': str(ThreadID("iso-thread-003")),
                'user_id': str(user3_id),
                'old_state': None,
                'new_state': 'active',
                'timestamp': asyncio.get_event_loop().time()
            }
        ]
        
        # Publish events to user-specific channels
        for event in test_events:
            user_id = event['user_id']
            channel = f"websocket:thread_events:{user_id}"
            await redis_client.publish(channel, json.dumps(event))
            await asyncio.sleep(0.1)  # Small delay between publishes
        
        # Wait for all listeners to complete
        await asyncio.gather(*listen_futures)
        
        # Validate user isolation
        assert len(subscriber1.received_events) == 1, (
            f"User 1 should receive exactly 1 event, got {len(subscriber1.received_events)}"
        )
        assert len(subscriber2.received_events) == 1, (
            f"User 2 should receive exactly 1 event, got {len(subscriber2.received_events)}"
        )
        assert len(subscriber3.received_events) == 1, (
            f"User 3 should receive exactly 1 event, got {len(subscriber3.received_events)}"
        )
        
        # Validate each user received only their own events
        user1_event = subscriber1.received_events[0]
        user2_event = subscriber2.received_events[0]
        user3_event = subscriber3.received_events[0]
        
        assert user1_event['user_id'] == str(user1_id), "User 1 must only receive their own events"
        assert user1_event['thread_id'] == str(ThreadID("iso-thread-001")), "User 1 must receive correct thread event"
        
        assert user2_event['user_id'] == str(user2_id), "User 2 must only receive their own events"
        assert user2_event['thread_id'] == str(ThreadID("iso-thread-002")), "User 2 must receive correct thread event"
        
        assert user3_event['user_id'] == str(user3_id), "User 3 must only receive their own events"
        assert user3_event['thread_id'] == str(ThreadID("iso-thread-003")), "User 3 must receive correct thread event"


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_state_event_ordering_consistency(self, real_services_fixture):
        """
        Test that thread state events maintain chronological ordering.
        
        BUSINESS CRITICAL: Event ordering ensures users see coherent conversation flow.
        Out-of-order events confuse users and break chat experience.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock event tracker with ordering validation
        class OrderedEventTracker:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.event_sequence = []
                self.event_timestamps = []
            
            async def track_thread_state_sequence(self, thread_id: ThreadID, user_id: UserID, state_sequence: List[str]):
                for i, state in enumerate(state_sequence):
                    event = {
                        'event_type': 'thread_state_change',
                        'thread_id': str(thread_id),
                        'user_id': str(user_id),
                        'old_state': state_sequence[i-1] if i > 0 else None,
                        'new_state': state,
                        'sequence_number': i,
                        'timestamp': asyncio.get_event_loop().time()
                    }
                    
                    # Store event with ordering metadata
                    await self.redis.zadd(
                        f"thread_events:{thread_id}:ordered",
                        {json.dumps(event): event['timestamp']}
                    )
                    
                    self.event_sequence.append(event)
                    self.event_timestamps.append(event['timestamp'])
                    
                    # Small delay to ensure timestamp ordering
                    await asyncio.sleep(0.01)
            
            async def get_ordered_events(self, thread_id: ThreadID) -> List[Dict[str, Any]]:
                # Retrieve events in chronological order
                ordered_events_raw = await self.redis.zrange(
                    f"thread_events:{thread_id}:ordered", 
                    0, -1, withscores=True
                )
                
                ordered_events = []
                for event_data, score in ordered_events_raw:
                    event = json.loads(event_data.decode())
                    event['retrieved_timestamp'] = score
                    ordered_events.append(event)
                
                return ordered_events
        
        event_tracker = OrderedEventTracker(redis_client)
        
        # Test thread state progression
        test_thread_id = ThreadID("order-thread-001")
        test_user_id = UserID("order-user-001")
        
        # Define expected state sequence
        expected_sequence = [
            'active',
            'processing',
            'waiting_for_input',
            'processing',
            'completed'
        ]
        
        # Track state sequence
        await event_tracker.track_thread_state_sequence(
            test_thread_id, test_user_id, expected_sequence
        )
        
        # Retrieve ordered events
        ordered_events = await event_tracker.get_ordered_events(test_thread_id)
        
        # Validate event count
        assert len(ordered_events) == len(expected_sequence), (
            f"Expected {len(expected_sequence)} ordered events, got {len(ordered_events)}"
        )
        
        # Validate chronological ordering
        for i in range(1, len(ordered_events)):
            prev_timestamp = ordered_events[i-1]['retrieved_timestamp']
            curr_timestamp = ordered_events[i]['retrieved_timestamp']
            
            assert curr_timestamp >= prev_timestamp, (
                f"Event {i} timestamp {curr_timestamp} must be >= previous timestamp {prev_timestamp}"
            )
        
        # Validate state sequence correctness
        for i, event in enumerate(ordered_events):
            expected_state = expected_sequence[i]
            actual_state = event['new_state']
            
            assert actual_state == expected_state, (
                f"Event {i}: Expected state '{expected_state}', got '{actual_state}'"
            )
            
            # Validate old_state consistency
            if i > 0:
                expected_old_state = expected_sequence[i-1]
                actual_old_state = event['old_state']
                
                assert actual_old_state == expected_old_state, (
                    f"Event {i}: Expected old_state '{expected_old_state}', got '{actual_old_state}'"
                )
            else:
                assert event['old_state'] is None, "First event must have null old_state"
        
        # Validate sequence numbers
        for i, event in enumerate(ordered_events):
            assert event['sequence_number'] == i, (
                f"Event {i}: Expected sequence_number {i}, got {event['sequence_number']}"
            )
        
        # Cleanup
        await redis_client.delete(f"thread_events:{test_thread_id}:ordered")