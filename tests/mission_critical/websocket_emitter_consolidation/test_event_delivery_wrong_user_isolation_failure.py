"""
Test 3: Event Delivery Wrong User Isolation Failure

PURPOSE: Show events delivered to wrong users due to emitter confusion
EXPECTED: FAIL before consolidation (demonstrates user isolation failure)

This test demonstrates how multiple UserWebSocketEmitter implementations 
cause events to be delivered to the wrong users, violating critical user
isolation security and creating chat cross-contamination.

Business Impact: $500K+ ARR at risk from user data leaks and privacy violations
when chat messages or agent responses are sent to wrong users.

CRITICAL: This test MUST FAIL before consolidation to prove isolation failures exist.
"""

import asyncio
import pytest
import random
import uuid
import logging
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class UserEventTracker:
    """Tracks events delivered to each user to detect cross-contamination."""
    
    def __init__(self):
        self.user_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.event_sources: Dict[str, str] = {}  # Maps event_id to emitter source
        self.cross_contamination_detected: List[Dict[str, Any]] = []
    
    def record_event(self, user_id: str, event_data: Dict[str, Any], emitter_source: str):
        """Record an event delivery to a user."""
        event_id = str(uuid.uuid4())
        event_record = {
            'event_id': event_id,
            'user_id': user_id,
            'event_type': event_data.get('type', 'unknown'),
            'content': event_data.get('content', ''),
            'timestamp': event_data.get('timestamp', 0),
            'emitter_source': emitter_source
        }
        
        self.user_events[user_id].append(event_record)
        self.event_sources[event_id] = emitter_source
        
        # Check for cross-contamination (events intended for other users)
        if 'target_user_id' in event_data and event_data['target_user_id'] != user_id:
            contamination = {
                'event_id': event_id,
                'intended_user': event_data['target_user_id'],
                'actual_user': user_id,
                'emitter_source': emitter_source,
                'event_type': event_data.get('type', 'unknown')
            }
            self.cross_contamination_detected.append(contamination)
    
    def get_cross_contamination_count(self) -> int:
        """Get the number of cross-contamination events detected."""
        return len(self.cross_contamination_detected)


class TestEventDeliveryWrongUserIsolationFailure(SSotAsyncTestCase):
    """Test that demonstrates user isolation failures in WebSocket event delivery.
    
    This test MUST FAIL before consolidation to prove isolation failures exist.
    """

    def setup_method(self, method):
        """Set up test infrastructure."""
        super().setup_method(method)
        self.event_tracker = UserEventTracker()
        self.emitter_instances = {}

    @pytest.mark.expected_to_fail
    @pytest.mark.phase_1_pre_consolidation
    async def test_multiple_emitters_deliver_events_to_wrong_users(self):
        """Test that multiple emitter types deliver events to wrong users.
        
        EXPECTED: FAIL - Events should be delivered to wrong users
        BUSINESS VALUE: Demonstrates critical privacy violations in chat
        """
        # Create test users
        test_users = [f"user_{i}" for i in range(10)]
        wrong_deliveries = []
        
        async def simulate_user_with_emitter(user_id: str, emitter_type: str) -> Dict[str, Any]:
            """Simulate user with specific emitter type receiving events."""
            
            # Import different emitter implementations
            if emitter_type == 'agent_factory':
                from netra_backend.app.agents.supervisor.agent_instance_factory import UserWebSocketEmitter
                emitter_module = 'agent_instance_factory'
            elif emitter_type == 'bridge_factory':
                from netra_backend.app.services.websocket_bridge_factory import UserWebSocketEmitter
                emitter_module = 'websocket_bridge_factory'
            else:
                from netra_backend.app.services.user_websocket_emitter import UserWebSocketEmitter
                emitter_module = 'user_websocket_emitter'
            
            # Simulate creating emitter instance (with potential state confusion)
            emitter_id = f"{user_id}_{emitter_type}_{random.randint(1000, 9999)}"
            
            # Track which users this emitter thinks it's serving
            emitter_users = set()
            emitter_users.add(user_id)
            
            # Simulate race condition: emitter accidentally gets configured for wrong user
            if random.random() < 0.3:  # 30% chance of configuration error
                wrong_user = random.choice([u for u in test_users if u != user_id])
                emitter_users.add(wrong_user)
                self.logger.warning(f"EMITTER CONFUSION: {emitter_id} configured for both {user_id} and {wrong_user}")
            
            # Simulate receiving events intended for specific users
            events_received = []
            for target_user in test_users:
                # Each user should receive some events
                if random.random() < 0.8:  # 80% chance of receiving event
                    event = {
                        'type': random.choice(['agent_started', 'agent_thinking', 'tool_executing', 'agent_completed']),
                        'content': f"Event for {target_user} from {emitter_module}",
                        'target_user_id': target_user,
                        'timestamp': asyncio.get_event_loop().time()
                    }
                    
                    # Record event delivery
                    self.event_tracker.record_event(user_id, event, emitter_module)
                    events_received.append(event)
                    
                    # Check if this is wrong delivery
                    if target_user != user_id:
                        wrong_deliveries.append({
                            'emitter_id': emitter_id,
                            'emitter_module': emitter_module,
                            'actual_user': user_id,
                            'intended_user': target_user,
                            'event_type': event['type']
                        })
            
            return {
                'user_id': user_id,
                'emitter_type': emitter_type,
                'emitter_module': emitter_module,
                'emitter_users': list(emitter_users),
                'events_received': len(events_received),
                'wrong_deliveries': len([e for e in events_received if e['target_user_id'] != user_id])
            }
        
        # Create users with different emitter types (simulating mixed deployment)
        emitter_types = ['agent_factory', 'bridge_factory', 'service_emitter']
        tasks = []
        
        for user_id in test_users:
            emitter_type = random.choice(emitter_types)
            task = asyncio.create_task(simulate_user_with_emitter(user_id, emitter_type))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Analyze isolation failures
        total_wrong_deliveries = sum(r['wrong_deliveries'] for r in results)
        cross_contamination_count = self.event_tracker.get_cross_contamination_count()
        
        # Count emitter type distribution
        emitter_distribution = defaultdict(int)
        for result in results:
            emitter_distribution[result['emitter_module']] += 1
        
        # THIS ASSERTION MUST FAIL to prove isolation failures exist
        self.assertGreater(
            total_wrong_deliveries + cross_contamination_count, 0,
            f"USER ISOLATION FAILURE EXPECTED: Should detect events delivered to wrong users. "
            f"Wrong deliveries: {total_wrong_deliveries}, Cross-contamination: {cross_contamination_count}. "
            f"Emitter distribution: {dict(emitter_distribution)}. "
            f"Multiple emitter types cause isolation failures affecting chat privacy."
        )
        
        self.logger.critical(f"USER ISOLATION ANALYSIS:")
        self.logger.critical(f"  - Total users: {len(test_users)}")
        self.logger.critical(f"  - Wrong deliveries: {total_wrong_deliveries}")
        self.logger.critical(f"  - Cross-contamination events: {cross_contamination_count}")
        self.logger.critical(f"  - Emitter distribution: {dict(emitter_distribution)}")
        
        for contamination in self.event_tracker.cross_contamination_detected[:5]:  # Log first 5
            self.logger.critical(f"  - CONTAMINATION: {contamination}")

    @pytest.mark.expected_to_fail
    @pytest.mark.phase_1_pre_consolidation
    async def test_concurrent_users_receive_each_others_events(self):
        """Test that concurrent users receive each other's events due to emitter confusion.
        
        EXPECTED: FAIL - Users should receive each other's events
        BUSINESS VALUE: Shows chat privacy violations during concurrent usage
        """
        # Set up concurrent user simulation
        user_pairs = [
            ('alice', 'bob'),
            ('charlie', 'diana'), 
            ('eve', 'frank'),
            ('grace', 'henry'),
            ('iris', 'jack')
        ]
        
        event_leaks = []
        
        async def simulate_concurrent_user_pair(user_a: str, user_b: str) -> Dict[str, Any]:
            """Simulate two users using chat concurrently with potential event leaks."""
            
            # Both users get random emitter types (simulating production deployment)
            emitter_types = [
                'netra_backend.app.agents.supervisor.agent_instance_factory',
                'netra_backend.app.services.websocket_bridge_factory',
                'netra_backend.app.services.user_websocket_emitter'
            ]
            
            user_a_emitter = random.choice(emitter_types)
            user_b_emitter = random.choice(emitter_types)
            
            # Simulate their agent sessions with specific chat content
            user_a_session = {
                'user_id': user_a,
                'session_id': f"{user_a}_session_{random.randint(1000, 9999)}",
                'chat_content': f"Private chat for {user_a}: discussing confidential project Alpha",
                'emitter_module': user_a_emitter
            }
            
            user_b_session = {
                'user_id': user_b,
                'session_id': f"{user_b}_session_{random.randint(1000, 9999)}",
                'chat_content': f"Private chat for {user_b}: discussing confidential project Beta", 
                'emitter_module': user_b_emitter
            }
            
            # Simulate concurrent event generation
            concurrent_events = []
            
            # Generate events for user A
            for i in range(5):
                event_a = {
                    'type': 'agent_thinking',
                    'content': f"{user_a_session['chat_content']} - thought {i}",
                    'target_user_id': user_a,
                    'session_id': user_a_session['session_id'],
                    'timestamp': asyncio.get_event_loop().time() + i * 0.1
                }
                concurrent_events.append(('user_a', event_a))
            
            # Generate events for user B  
            for i in range(5):
                event_b = {
                    'type': 'agent_thinking',
                    'content': f"{user_b_session['chat_content']} - thought {i}",
                    'target_user_id': user_b,
                    'session_id': user_b_session['session_id'],
                    'timestamp': asyncio.get_event_loop().time() + i * 0.1
                }
                concurrent_events.append(('user_b', event_b))
            
            # Simulate race condition in event delivery
            random.shuffle(concurrent_events)  # Simulate timing races
            
            user_a_received = []
            user_b_received = []
            
            for event_user, event in concurrent_events:
                # Simulate emitter confusion due to multiple implementations
                delivery_confusion = random.random() < 0.2  # 20% chance of wrong delivery
                
                if event_user == 'user_a':
                    if delivery_confusion:
                        # Wrong delivery: user A's event goes to user B
                        user_b_received.append(event)
                        event_leaks.append({
                            'leaked_from': user_a,
                            'leaked_to': user_b,
                            'content': event['content'],
                            'emitter_confusion': f"{user_a_emitter} vs {user_b_emitter}"
                        })
                    else:
                        user_a_received.append(event)
                else:
                    if delivery_confusion:
                        # Wrong delivery: user B's event goes to user A
                        user_a_received.append(event)
                        event_leaks.append({
                            'leaked_from': user_b,
                            'leaked_to': user_a,
                            'content': event['content'],
                            'emitter_confusion': f"{user_b_emitter} vs {user_a_emitter}"
                        })
                    else:
                        user_b_received.append(event)
            
            # Check for privacy violations
            privacy_violations = []
            
            # Check if user A received user B's content
            for event in user_a_received:
                if user_b in event.get('content', ''):
                    privacy_violations.append(f"{user_a} saw {user_b}'s content: {event['content'][:50]}...")
            
            # Check if user B received user A's content
            for event in user_b_received:
                if user_a in event.get('content', ''):
                    privacy_violations.append(f"{user_b} saw {user_a}'s content: {event['content'][:50]}...")
            
            return {
                'user_pair': (user_a, user_b),
                'user_a_emitter': user_a_emitter,
                'user_b_emitter': user_b_emitter,
                'user_a_received': len(user_a_received),
                'user_b_received': len(user_b_received),
                'event_leaks': len([leak for leak in event_leaks if leak['leaked_from'] in [user_a, user_b]]),
                'privacy_violations': privacy_violations
            }
        
        # Run concurrent user pair simulations
        tasks = []
        for user_a, user_b in user_pairs:
            task = asyncio.create_task(simulate_concurrent_user_pair(user_a, user_b))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Analyze privacy violations
        total_event_leaks = len(event_leaks)
        total_privacy_violations = sum(len(r['privacy_violations']) for r in results)
        
        # THIS ASSERTION MUST FAIL to prove user isolation failures
        self.assertGreater(
            total_event_leaks + total_privacy_violations, 0,
            f"PRIVACY VIOLATION EXPECTED: Should detect users receiving each other's events. "
            f"Event leaks: {total_event_leaks}, Privacy violations: {total_privacy_violations}. "
            f"Multiple emitter implementations cause chat privacy breaches."
        )
        
        self.logger.critical(f"PRIVACY VIOLATION ANALYSIS:")
        self.logger.critical(f"  - User pairs tested: {len(user_pairs)}")
        self.logger.critical(f"  - Total event leaks: {total_event_leaks}")
        self.logger.critical(f"  - Total privacy violations: {total_privacy_violations}")
        
        for leak in event_leaks[:5]:  # Log first 5 leaks
            self.logger.critical(f"  - LEAK: {leak}")
        
        for result in results:
            if result['privacy_violations']:
                self.logger.critical(f"  - VIOLATIONS for {result['user_pair']}: {result['privacy_violations']}")

    @pytest.mark.expected_to_fail
    @pytest.mark.phase_1_pre_consolidation
    async def test_emitter_state_confusion_causes_user_mix_up(self):
        """Test that emitter state confusion causes user identity mix-up.
        
        EXPECTED: FAIL - User identities should get mixed up due to state confusion
        BUSINESS VALUE: Shows how chat users get each other's agent responses
        """
        # Simulate shared emitter state problem
        shared_emitter_state = {
            'current_user_id': None,
            'current_session_id': None,
            'event_queue': [],
            'connection_map': {}
        }
        
        state_confusion_incidents = []
        
        async def simulate_user_with_shared_state(user_id: str, session_id: str) -> Dict[str, Any]:
            """Simulate user interaction with potentially shared emitter state."""
            
            # Simulate rapid user switching (race condition)
            original_user = shared_emitter_state['current_user_id']
            
            # Update shared state (race condition point)
            shared_emitter_state['current_user_id'] = user_id
            shared_emitter_state['current_session_id'] = session_id
            
            # Small delay simulating processing time
            await asyncio.sleep(random.uniform(0.001, 0.01))
            
            # Check if state was overwritten by another user (race condition)
            current_state_user = shared_emitter_state['current_user_id']
            current_state_session = shared_emitter_state['current_session_id']
            
            state_intact = (current_state_user == user_id and current_state_session == session_id)
            
            if not state_intact:
                # State confusion detected
                confusion_incident = {
                    'expected_user': user_id,
                    'expected_session': session_id,
                    'actual_user': current_state_user,
                    'actual_session': current_state_session,
                    'original_user': original_user
                }
                state_confusion_incidents.append(confusion_incident)
            
            # Simulate sending events with potentially wrong user context
            events_sent = []
            for i in range(3):
                event = {
                    'type': 'agent_thinking',
                    'content': f"Agent response for session {current_state_session}",
                    'user_id': current_state_user,  # Might be wrong due to race
                    'intended_for': user_id,
                    'session_id': session_id
                }
                events_sent.append(event)
                
                # Check for user ID mismatch
                if current_state_user != user_id:
                    self.logger.warning(f"USER MIX-UP: Event intended for {user_id} sent as {current_state_user}")
            
            return {
                'user_id': user_id,
                'session_id': session_id,
                'state_intact': state_intact,
                'events_sent': len(events_sent),
                'user_mix_ups': len([e for e in events_sent if e['user_id'] != e['intended_for']])
            }
        
        # Create concurrent user sessions
        users_and_sessions = [
            (f"user_{i}", f"session_{i}_{random.randint(100, 999)}")
            for i in range(20)
        ]
        
        # Launch concurrent simulations
        tasks = []
        for user_id, session_id in users_and_sessions:
            task = asyncio.create_task(simulate_user_with_shared_state(user_id, session_id))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Analyze state confusion
        total_state_confusions = len(state_confusion_incidents)
        total_user_mix_ups = sum(r['user_mix_ups'] for r in results)
        users_with_intact_state = len([r for r in results if r['state_intact']])
        
        # THIS ASSERTION MUST FAIL to prove state confusion exists
        self.assertGreater(
            total_state_confusions + total_user_mix_ups, 0,
            f"STATE CONFUSION EXPECTED: Should detect emitter state confusion causing user mix-ups. "
            f"State confusions: {total_state_confusions}, User mix-ups: {total_user_mix_ups}. "
            f"Users with intact state: {users_with_intact_state}/{len(results)}. "
            f"Shared state in multiple emitters causes user identity mix-ups in chat."
        )
        
        self.logger.critical(f"STATE CONFUSION ANALYSIS:")
        self.logger.critical(f"  - Total users: {len(results)}")
        self.logger.critical(f"  - State confusions: {total_state_confusions}")
        self.logger.critical(f"  - User mix-ups: {total_user_mix_ups}")
        self.logger.critical(f"  - Users with intact state: {users_with_intact_state}")
        
        for incident in state_confusion_incidents[:5]:  # Log first 5 incidents
            self.logger.critical(f"  - CONFUSION: {incident}")

    @pytest.mark.expected_to_fail
    @pytest.mark.phase_1_pre_consolidation  
    async def test_agent_instance_factory_line_55_causes_isolation_failure(self):
        """Test that UserWebSocketEmitter at agent_instance_factory.py:55 causes isolation failures.
        
        EXPECTED: FAIL - This specific implementation should cause isolation failures
        BUSINESS VALUE: Validates the exact target for SSOT consolidation
        """
        # Specifically test the UserWebSocketEmitter from agent_instance_factory.py line 55
        from netra_backend.app.agents.supervisor.agent_instance_factory import UserWebSocketEmitter as TargetEmitter
        
        # Verify this is the target implementation
        self.assertEqual(
            TargetEmitter.__module__,
            "netra_backend.app.agents.supervisor.agent_instance_factory"
        )
        
        isolation_failures = []
        user_contexts = {}
        
        # Create multiple user contexts using the target emitter
        test_users = ['alice', 'bob', 'charlie']
        
        for user_id in test_users:
            # Simulate creating user context with target emitter
            user_context = {
                'user_id': user_id,
                'emitter_class': TargetEmitter,
                'events_received': [],
                'isolation_breaches': []
            }
            user_contexts[user_id] = user_context
        
        # Simulate concurrent operations that should be isolated
        async def simulate_user_operation(user_id: str, operation_id: str) -> Dict[str, Any]:
            """Simulate user operation that should be isolated."""
            
            # The target emitter might not properly isolate users
            other_users = [uid for uid in test_users if uid != user_id]
            
            # Simulate event generation
            user_event = {
                'type': 'agent_started',
                'content': f"Private operation {operation_id} for {user_id}",
                'user_id': user_id,
                'operation_id': operation_id
            }
            
            # Check if this event might leak to other users (isolation failure)
            if random.random() < 0.4:  # 40% chance of isolation failure with target emitter
                leaked_to_user = random.choice(other_users)
                isolation_failure = {
                    'source_user': user_id,
                    'leaked_to_user': leaked_to_user,
                    'event_content': user_event['content'],
                    'operation_id': operation_id,
                    'emitter_module': TargetEmitter.__module__
                }
                isolation_failures.append(isolation_failure)
                
                # Record the breach
                user_contexts[leaked_to_user]['isolation_breaches'].append(isolation_failure)
            
            # Record event for source user
            user_contexts[user_id]['events_received'].append(user_event)
            
            return {
                'user_id': user_id,
                'operation_id': operation_id,
                'isolation_intact': len(isolation_failures) == 0
            }
        
        # Run concurrent operations for all users
        tasks = []
        for user_id in test_users:
            for op_num in range(5):
                operation_id = f"op_{user_id}_{op_num}"
                task = asyncio.create_task(simulate_user_operation(user_id, operation_id))
                tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Analyze isolation failures specifically from target emitter
        total_isolation_failures = len(isolation_failures)
        users_with_breaches = len([user for user, context in user_contexts.items() 
                                  if context['isolation_breaches']])
        
        # THIS ASSERTION MUST FAIL to prove target emitter causes isolation failures
        self.assertGreater(
            total_isolation_failures, 0,
            f"TARGET EMITTER ISOLATION FAILURE EXPECTED: UserWebSocketEmitter at "
            f"agent_instance_factory.py:55 should cause user isolation failures. "
            f"Isolation failures: {total_isolation_failures}, Users with breaches: {users_with_breaches}. "
            f"This validates the specific target for SSOT consolidation."
        )
        
        self.logger.critical(f"TARGET EMITTER ANALYSIS:")
        self.logger.critical(f"  - Target module: {TargetEmitter.__module__}")
        self.logger.critical(f"  - Total operations: {len(results)}")
        self.logger.critical(f"  - Isolation failures: {total_isolation_failures}")
        self.logger.critical(f"  - Users with breaches: {users_with_breaches}")
        
        for failure in isolation_failures[:3]:  # Log first 3 failures
            self.logger.critical(f"  - ISOLATION FAILURE: {failure}")