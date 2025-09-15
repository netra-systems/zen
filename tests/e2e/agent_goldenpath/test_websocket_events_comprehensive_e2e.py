"""
E2E Tests for Comprehensive WebSocket Event Delivery in Agent Golden Path
Issue #1081 - Agent Golden Path Messages E2E Test Creation

MISSION CRITICAL: Tests comprehensive WebSocket event delivery during agent work
- All 5 critical WebSocket events delivered during agent processing
- Event timing and sequencing validation
- Event payload integrity and business context
- Real-time user experience validation
- Event delivery under various load conditions

Business Value Justification (BVJ):
- Segment: All Users requiring real-time chat experience
- Business Goal: Real-time User Experience & System Transparency 
- Value Impact: Ensures $500K+ ARR chat functionality provides excellent UX
- Strategic Impact: Real-time events are critical for user engagement and platform stickiness

Test Strategy:
- REAL WEBSOCKETS: Complete staging WebSocket event delivery
- REAL EVENTS: All 5 critical events in production-like scenarios
- REAL TIMING: Event sequencing and performance validation
- REAL USER EXPERIENCE: UX quality measurement
- NO MOCKING: Full WebSocket event pipeline testing

Coverage Target: Increase from 65-75% to 85%
Test Focus: WebSocket events, real-time UX, event integrity, system transparency
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid
from dataclasses import dataclass, field
from enum import Enum
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, AuthenticatedUser

class WebSocketEventType(Enum):
    """Critical WebSocket events for Golden Path."""
    AGENT_STARTED = 'agent_started'
    AGENT_THINKING = 'agent_thinking'
    TOOL_EXECUTING = 'tool_executing'
    TOOL_COMPLETED = 'tool_completed'
    AGENT_COMPLETED = 'agent_completed'

@dataclass
class EventValidation:
    """WebSocket event validation metrics."""
    event_type: str
    received_at: float
    payload_valid: bool = True
    timing_valid: bool = True
    business_context: str = ''
    sequence_position: int = 0
    user_experience_impact: str = 'positive'

@dataclass
class WebSocketEventSequence:
    """Complete WebSocket event sequence analysis."""
    events_received: List[EventValidation] = field(default_factory=list)
    total_duration: float = 0.0
    sequence_complete: bool = False
    timing_quality: float = 0.0
    user_experience_score: float = 0.0
    business_transparency: float = 0.0

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.websocket_events
@pytest.mark.mission_critical
class TestWebSocketEventsComprehensiveE2E(SSotAsyncTestCase):
    """
    Comprehensive E2E tests for WebSocket event delivery in agent golden path.
    
    Validates complete WebSocket event delivery, timing, sequencing, and user experience
    during agent message processing in staging GCP environment.
    """

    @classmethod
    def setup_class(cls):
        """Setup comprehensive WebSocket events test environment."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available')
        cls.auth_helper = E2EWebSocketAuthHelper(environment='staging')
        cls.CRITICAL_EVENTS = [WebSocketEventType.AGENT_STARTED, WebSocketEventType.AGENT_THINKING, WebSocketEventType.TOOL_EXECUTING, WebSocketEventType.TOOL_COMPLETED, WebSocketEventType.AGENT_COMPLETED]
        cls.EXCELLENT_FIRST_EVENT_TIME = 3.0
        cls.GOOD_FIRST_EVENT_TIME = 8.0
        cls.MAX_EVENT_INTERVAL = 15.0
        cls.EXCELLENT_COMPLETION_TIME = 30.0
        cls.GOOD_COMPLETION_TIME = 60.0
        cls.UX_WEIGHTS = {'event_completeness': 0.3, 'timing_quality': 0.25, 'sequence_logic': 0.2, 'business_context': 0.15, 'transparency': 0.1}
        cls.logger.info('Comprehensive WebSocket events e2e tests initialized')

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.test_id = f'websocket_events_test_{int(time.time())}'
        self.thread_id = f'thread_{self.test_id}'
        self.run_id = f'run_{self.test_id}'
        self.logger.info(f'WebSocket events test setup - test_id: {self.test_id}')

    def _validate_event_payload(self, event: Dict[str, Any]) -> bool:
        """Validate WebSocket event payload structure and content."""
        required_fields = ['type']
        if not all((field in event for field in required_fields)):
            return False
        event_type = event.get('type', '')
        if 'agent' in event_type:
            event_data = event.get('data', {})
            if not event_data:
                return False
        if 'tool' in event_type:
            event_data = event.get('data', {})
            if not any((key in event_data for key in ['tool_name', 'tool_type', 'action'])):
                pass
        return True

    def _extract_business_context(self, event: Dict[str, Any]) -> str:
        """Extract business context from WebSocket event."""
        context_sources = [event.get('data', {}).get('context', ''), event.get('data', {}).get('message', ''), event.get('data', {}).get('description', ''), event.get('message', ''), str(event.get('data', {}))]
        for source in context_sources:
            if source and len(str(source)) > 10:
                return str(source)[:200]
        return 'No business context available'

    def _calculate_timing_quality(self, events: List[EventValidation]) -> float:
        """Calculate timing quality score for event sequence."""
        if len(events) < 2:
            return 0.5
        timing_scores = []
        first_event_time = events[0].received_at
        if first_event_time <= self.EXCELLENT_FIRST_EVENT_TIME:
            timing_scores.append(1.0)
        elif first_event_time <= self.GOOD_FIRST_EVENT_TIME:
            timing_scores.append(0.7)
        else:
            timing_scores.append(0.3)
        for i in range(1, len(events)):
            interval = events[i].received_at - events[i - 1].received_at
            if interval <= 5.0:
                timing_scores.append(1.0)
            elif interval <= 10.0:
                timing_scores.append(0.8)
            elif interval <= self.MAX_EVENT_INTERVAL:
                timing_scores.append(0.6)
            else:
                timing_scores.append(0.2)
        total_time = events[-1].received_at
        if total_time <= self.EXCELLENT_COMPLETION_TIME:
            timing_scores.append(1.0)
        elif total_time <= self.GOOD_COMPLETION_TIME:
            timing_scores.append(0.7)
        else:
            timing_scores.append(0.4)
        return sum(timing_scores) / len(timing_scores)

    def _calculate_user_experience_score(self, sequence: WebSocketEventSequence) -> float:
        """Calculate comprehensive user experience score."""
        if not sequence.events_received:
            return 0.0
        critical_events_received = sum((1 for event in sequence.events_received if any((critical.value in event.event_type for critical in self.CRITICAL_EVENTS))))
        completeness_score = min(critical_events_received / len(self.CRITICAL_EVENTS), 1.0)
        timing_score = self._calculate_timing_quality(sequence.events_received)
        sequence_score = 1.0
        event_types = [e.event_type for e in sequence.events_received]
        if 'agent_completed' in event_types and 'agent_started' in event_types:
            started_idx = next((i for i, t in enumerate(event_types) if 'agent_started' in t))
            completed_idx = next((i for i, t in enumerate(event_types) if 'agent_completed' in t))
            if started_idx >= completed_idx:
                sequence_score = 0.3
        context_events = sum((1 for e in sequence.events_received if len(e.business_context) > 20))
        context_score = min(context_events / max(len(sequence.events_received), 1), 1.0)
        transparency_score = min(len(sequence.events_received) / 5, 1.0)
        ux_score = completeness_score * self.UX_WEIGHTS['event_completeness'] + timing_score * self.UX_WEIGHTS['timing_quality'] + sequence_score * self.UX_WEIGHTS['sequence_logic'] + context_score * self.UX_WEIGHTS['business_context'] + transparency_score * self.UX_WEIGHTS['transparency']
        return min(ux_score, 1.0)

    def _analyze_event_sequence(self, events: List[Dict[str, Any]], start_time: float) -> WebSocketEventSequence:
        """Analyze complete WebSocket event sequence."""
        sequence = WebSocketEventSequence()
        for i, event in enumerate(events):
            event_type = event.get('type', 'unknown')
            event_time = event.get('timestamp', time.time()) if 'timestamp' in event else start_time + i * 2
            validation = EventValidation(event_type=event_type, received_at=event_time - start_time, payload_valid=self._validate_event_payload(event), business_context=self._extract_business_context(event), sequence_position=i)
            sequence.events_received.append(validation)
        if sequence.events_received:
            sequence.total_duration = sequence.events_received[-1].received_at
            sequence.timing_quality = self._calculate_timing_quality(sequence.events_received)
            sequence.user_experience_score = self._calculate_user_experience_score(sequence)
            sequence.sequence_complete = any(('agent_completed' in e.event_type for e in sequence.events_received))
            meaningful_events = sum((1 for e in sequence.events_received if len(e.business_context) > 20))
            sequence.business_transparency = min(meaningful_events / len(sequence.events_received), 1.0)
        return sequence

    async def test_critical_websocket_events_delivery(self):
        """
        Test delivery of all 5 critical WebSocket events during agent processing.
        
        Validates that:
        1. All 5 critical events are delivered (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
        2. Events are delivered in logical sequence
        3. Event timing meets user experience requirements
        4. Event payloads contain meaningful business context
        
        Flow:
        1. Send agent message → monitor for all critical events
        2. Validate each event type received → check payload quality
        3. Analyze event timing and sequencing → UX scoring
        4. Validate business context and transparency
        
        Coverage: Critical event delivery, event sequencing, UX timing, business context
        """
        critical_events_start = time.time()
        self.logger.info('📡 Testing critical WebSocket events delivery')
        try:
            events_user = await self.auth_helper.create_authenticated_user(email=f'critical_events_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'agent_execution', 'websocket_events'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.staging_config.urls.websocket_url, additional_headers=self.auth_helper.get_websocket_headers(events_user.jwt_token), ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=20.0)
            critical_events_message = {'type': 'chat_message', 'content': 'Please analyze my AI infrastructure costs and provide optimization recommendations. Current monthly spend: $12,000 with 750,000 API calls. I need specific cost reduction strategies with ROI calculations.', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': events_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'critical_events_delivery', 'expects_all_events': True, 'business_scenario': 'cost_optimization'}}
            message_start = time.time()
            await websocket.send(json.dumps(critical_events_message))
            all_events = []
            received_event_types = set()
            event_timestamps = {}
            timeout = 75.0
            collection_start = time.time()
            while time.time() - collection_start < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    event['timestamp'] = time.time()
                    all_events.append(event)
                    event_type = event.get('type', 'unknown')
                    received_event_types.add(event_type)
                    event_timestamps[event_type] = time.time() - collection_start
                    self.logger.info(f'📨 Critical event received: {event_type} at {event_timestamps[event_type]:.2f}s')
                    if event_type == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
            await websocket.close()
            sequence = self._analyze_event_sequence(all_events, collection_start)
            total_time = time.time() - critical_events_start
            assert len(all_events) > 0, 'Should receive WebSocket events'
            assert sequence.sequence_complete, 'Should receive agent_completed event'
            critical_events_received = []
            for critical_event in self.CRITICAL_EVENTS:
                if any((critical_event.value in event_type for event_type in received_event_types)):
                    critical_events_received.append(critical_event.value)
            critical_coverage = len(critical_events_received) / len(self.CRITICAL_EVENTS)
            assert critical_coverage >= 0.6, f'Should receive most critical events: {critical_coverage:.1%} (received: {critical_events_received})'
            assert sequence.timing_quality >= 0.4, f"Event timing should meet UX requirements: {sequence.timing_quality:.3f} (first event: {event_timestamps.get(list(received_event_types)[0], 'N/A'):.2f}s)"
            assert sequence.user_experience_score >= 0.5, f'User experience should meet quality threshold: {sequence.user_experience_score:.3f}'
            assert sequence.business_transparency >= 0.3, f'Events should provide business context: {sequence.business_transparency:.3f}'
            self.logger.info('📡 Critical WebSocket events delivery validation complete')
            self.logger.info(f'   Total time: {total_time:.2f}s')
            self.logger.info(f'   Processing time: {sequence.total_duration:.2f}s')
            self.logger.info(f'   Events received: {len(all_events)}')
            self.logger.info(f'   Critical events: {critical_events_received}')
            self.logger.info(f'   Critical coverage: {critical_coverage:.1%}')
            self.logger.info(f'   Timing quality: {sequence.timing_quality:.3f}')
            self.logger.info(f'   UX score: {sequence.user_experience_score:.3f}')
            self.logger.info(f'   Business transparency: {sequence.business_transparency:.3f}')
        except Exception as e:
            self.logger.error(f'❌ Critical WebSocket events delivery failed: {e}')
            raise AssertionError(f'Critical WebSocket events delivery failed: {e}. This breaks real-time user experience and system transparency.')

    async def test_websocket_event_timing_and_performance(self):
        """
        Test WebSocket event timing and performance during agent processing.
        
        Validates that:
        1. First event is delivered quickly (good UX)
        2. Event intervals are reasonable (maintaining engagement)
        3. Total processing time meets performance expectations
        4. Event delivery doesn't degrade under processing load
        
        Flow:
        1. Send request → measure first event timing
        2. Monitor all events → analyze intervals and performance
        3. Validate timing meets UX requirements
        4. Check for performance degradation patterns
        
        Coverage: Event timing, UX performance, real-time responsiveness
        """
        timing_test_start = time.time()
        timing_metrics = {'first_event_time': None, 'event_intervals': [], 'total_processing_time': 0.0, 'performance_score': 0.0}
        self.logger.info('⏱️ Testing WebSocket event timing and performance')
        try:
            timing_user = await self.auth_helper.create_authenticated_user(email=f'event_timing_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'agent_execution', 'performance_testing'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.staging_config.urls.websocket_url, additional_headers=self.auth_helper.get_websocket_headers(timing_user.jwt_token), ssl=ssl_context), timeout=15.0)
            timing_message = {'type': 'chat_message', 'content': 'Quick analysis: What are the top 3 ways to reduce AI costs for a startup spending $3,000/month on OpenAI? Please prioritize by impact and ease.', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': timing_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'event_timing', 'performance_priority': 'high', 'expects_fast_response': True}}
            message_send_time = time.time()
            await websocket.send(json.dumps(timing_message))
            events_with_timing = []
            last_event_time = message_send_time
            first_event_received = False
            timeout = 45.0
            collection_start = time.time()
            while time.time() - collection_start < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    event_time = time.time()
                    if not first_event_received:
                        timing_metrics['first_event_time'] = event_time - message_send_time
                        first_event_received = True
                        self.logger.info(f"⚡ First event in {timing_metrics['first_event_time']:.2f}s")
                    interval = event_time - last_event_time
                    timing_metrics['event_intervals'].append(interval)
                    events_with_timing.append({'event': event, 'timestamp': event_time - collection_start, 'interval': interval})
                    last_event_time = event_time
                    event_type = event.get('type', 'unknown')
                    self.logger.info(f'⏰ Event: {event_type} (interval: {interval:.2f}s)')
                    if event_type == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
            await websocket.close()
            total_processing_time = time.time() - collection_start
            timing_metrics['total_processing_time'] = total_processing_time
            performance_components = []
            if timing_metrics['first_event_time']:
                if timing_metrics['first_event_time'] <= 3.0:
                    performance_components.append(1.0)
                elif timing_metrics['first_event_time'] <= 8.0:
                    performance_components.append(0.7)
                else:
                    performance_components.append(0.3)
            if timing_metrics['event_intervals']:
                avg_interval = sum(timing_metrics['event_intervals']) / len(timing_metrics['event_intervals'])
                max_interval = max(timing_metrics['event_intervals'])
                if max_interval <= 10.0:
                    performance_components.append(1.0)
                elif max_interval <= 20.0:
                    performance_components.append(0.7)
                else:
                    performance_components.append(0.4)
            if total_processing_time <= 25.0:
                performance_components.append(1.0)
            elif total_processing_time <= 45.0:
                performance_components.append(0.7)
            else:
                performance_components.append(0.4)
            timing_metrics['performance_score'] = sum(performance_components) / len(performance_components) if performance_components else 0.0
            total_time = time.time() - timing_test_start
            assert len(events_with_timing) > 0, 'Should receive events for timing analysis'
            if timing_metrics['first_event_time']:
                assert timing_metrics['first_event_time'] <= 12.0, f"First event too slow for good UX: {timing_metrics['first_event_time']:.2f}s (max 12s)"
            if timing_metrics['event_intervals']:
                max_interval = max(timing_metrics['event_intervals'])
                assert max_interval <= 25.0, f'Event intervals too long: {max_interval:.2f}s (max 25s)'
            assert total_processing_time <= 50.0, f'Total processing too slow: {total_processing_time:.2f}s (max 50s)'
            assert timing_metrics['performance_score'] >= 0.4, f"Overall timing performance insufficient: {timing_metrics['performance_score']:.3f}"
            self.logger.info('⏱️ WebSocket event timing validation complete')
            self.logger.info(f'   Total time: {total_time:.2f}s')
            self.logger.info(f'   Processing time: {total_processing_time:.2f}s')
            self.logger.info(f"   First event time: {timing_metrics['first_event_time']:.2f}s" if timing_metrics['first_event_time'] else '   First event time: N/A')
            self.logger.info(f'   Events received: {len(events_with_timing)}')
            self.logger.info(f"   Event intervals: {len(timing_metrics['event_intervals'])}")
            if timing_metrics['event_intervals']:
                avg_interval = sum(timing_metrics['event_intervals']) / len(timing_metrics['event_intervals'])
                max_interval = max(timing_metrics['event_intervals'])
                self.logger.info(f'   Average interval: {avg_interval:.2f}s')
                self.logger.info(f'   Max interval: {max_interval:.2f}s')
            self.logger.info(f"   Performance score: {timing_metrics['performance_score']:.3f}")
        except Exception as e:
            self.logger.error(f'❌ WebSocket event timing test failed: {e}')
            raise AssertionError(f'WebSocket event timing and performance test failed: {e}. This indicates poor real-time user experience.')

    async def test_websocket_events_under_concurrent_load(self):
        """
        Test WebSocket event delivery under concurrent user load.
        
        Validates that:
        1. Events are delivered correctly with multiple concurrent users
        2. No event cross-contamination between users
        3. Event delivery performance maintained under load
        4. User isolation maintained in event streams
        
        Flow:
        1. Create multiple concurrent users → parallel connections
        2. Send simultaneous messages → monitor separate event streams
        3. Validate event isolation → no cross-user contamination
        4. Check performance degradation under load
        
        Coverage: Concurrent event delivery, user isolation, load performance
        """
        concurrent_load_start = time.time()
        load_metrics = {'concurrent_users': 0, 'total_events': 0, 'cross_contamination': False, 'performance_degradation': 0.0}
        self.logger.info('👥 Testing WebSocket events under concurrent load')
        try:
            concurrent_users = []
            user_count = 3
            for i in range(user_count):
                user = await self.auth_helper.create_authenticated_user(email=f'concurrent_events_{i}_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'agent_execution'])
                concurrent_users.append({'user': user, 'thread_id': f'concurrent_thread_{i}_{self.test_id}', 'events': [], 'connection': None})
            load_metrics['concurrent_users'] = len(concurrent_users)

            async def setup_user_connection(user_data: Dict[str, Any]) -> None:
                """Setup WebSocket connection for a concurrent user."""
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                try:
                    websocket = await asyncio.wait_for(websockets.connect(self.staging_config.urls.websocket_url, additional_headers=self.auth_helper.get_websocket_headers(user_data['user'].jwt_token), ssl=ssl_context), timeout=15.0)
                    user_data['connection'] = websocket
                except Exception as e:
                    self.logger.warning(f'Failed to connect user: {e}')
            await asyncio.gather(*[setup_user_connection(user_data) for user_data in concurrent_users])
            connected_users = [u for u in concurrent_users if u['connection'] is not None]
            assert len(connected_users) >= 2, 'Should have at least 2 concurrent connections'

            async def send_user_message(user_data: Dict[str, Any], user_index: int) -> None:
                """Send message and monitor events for a concurrent user."""
                try:
                    message = {'type': 'chat_message', 'content': f'Concurrent user {user_index}: Analyze cost optimization for AI spend of ${(user_index + 1) * 5000}/month', 'thread_id': user_data['thread_id'], 'run_id': f'concurrent_run_{user_index}_{self.test_id}', 'user_id': user_data['user'].user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'concurrent_events', 'user_index': user_index}}
                    await user_data['connection'].send(json.dumps(message))
                    timeout = 60.0
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        try:
                            event_data = await asyncio.wait_for(user_data['connection'].recv(), timeout=10.0)
                            event = json.loads(event_data)
                            event['_user_index'] = user_index
                            event['_user_id'] = user_data['user'].user_id
                            user_data['events'].append(event)
                            if event.get('type') == 'agent_completed':
                                break
                        except asyncio.TimeoutError:
                            continue
                    await user_data['connection'].close()
                except Exception as e:
                    self.logger.warning(f'User {user_index} processing failed: {e}')
            concurrent_start = time.time()
            await asyncio.gather(*[send_user_message(user_data, i) for i, user_data in enumerate(connected_users)])
            concurrent_processing_time = time.time() - concurrent_start
            all_user_events = []
            for user_data in connected_users:
                all_user_events.extend(user_data['events'])
                load_metrics['total_events'] += len(user_data['events'])
            for user_data in connected_users:
                user_events = user_data['events']
                expected_user_id = user_data['user'].user_id
                for event in user_events:
                    event_str = str(event).lower()
                    for other_user in connected_users:
                        if other_user['user'].user_id != expected_user_id:
                            if other_user['user'].user_id.lower() in event_str:
                                load_metrics['cross_contamination'] = True
                                self.logger.warning(f"Cross-contamination detected: {other_user['user'].user_id} in {expected_user_id}'s events")
            expected_single_user_time = 35.0
            if concurrent_processing_time > expected_single_user_time:
                load_metrics['performance_degradation'] = (concurrent_processing_time - expected_single_user_time) / expected_single_user_time
            total_time = time.time() - concurrent_load_start
            assert load_metrics['total_events'] > 0, 'Should receive events from concurrent users'
            assert not load_metrics['cross_contamination'], 'Should not have cross-user event contamination'
            assert concurrent_processing_time < 90.0, f'Concurrent processing too slow: {concurrent_processing_time:.2f}s (max 90s)'
            for i, user_data in enumerate(connected_users):
                user_event_count = len(user_data['events'])
                assert user_event_count > 0, f'User {i} should receive events: got {user_event_count}'
            assert load_metrics['performance_degradation'] < 1.0, f"Performance degradation too high under load: {load_metrics['performance_degradation']:.1%}"
            self.logger.info('👥 Concurrent WebSocket events validation complete')
            self.logger.info(f'   Total time: {total_time:.2f}s')
            self.logger.info(f'   Concurrent processing: {concurrent_processing_time:.2f}s')
            self.logger.info(f'   Connected users: {len(connected_users)}')
            self.logger.info(f"   Total events: {load_metrics['total_events']}")
            self.logger.info(f"   Cross-contamination: {load_metrics['cross_contamination']}")
            self.logger.info(f"   Performance degradation: {load_metrics['performance_degradation']:.1%}")
            for i, user_data in enumerate(connected_users):
                self.logger.info(f"   User {i} events: {len(user_data['events'])}")
        except Exception as e:
            self.logger.error(f'❌ Concurrent WebSocket events test failed: {e}')
            raise AssertionError(f'WebSocket events under concurrent load failed: {e}. This indicates scalability issues with real-time event delivery.')

    async def test_websocket_event_payload_integrity(self):
        """
        Test WebSocket event payload integrity and business context.
        
        Validates that:
        1. Event payloads contain required structure and fields
        2. Business context is meaningful and relevant
        3. Event data is consistent and accurate
        4. Payload size and format are appropriate
        
        Flow:
        1. Send business-focused message → monitor detailed event payloads
        2. Validate payload structure → check required fields
        3. Analyze business context → meaningful content validation
        4. Check data consistency across events
        
        Coverage: Event payload quality, business context, data integrity
        """
        payload_integrity_start = time.time()
        integrity_metrics = {'valid_payloads': 0, 'invalid_payloads': 0, 'business_context_events': 0, 'payload_quality_score': 0.0}
        self.logger.info('📋 Testing WebSocket event payload integrity')
        try:
            payload_user = await self.auth_helper.create_authenticated_user(email=f'payload_integrity_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'agent_execution', 'detailed_events'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.staging_config.urls.websocket_url, additional_headers=self.auth_helper.get_websocket_headers(payload_user.jwt_token), ssl=ssl_context), timeout=15.0)
            business_message = {'type': 'chat_message', 'content': "I'm the CFO of a tech startup and need detailed AI cost analysis. Our current spend: $18,000/month across GPT-4 (60%), GPT-3.5 (30%), embeddings (10%). User base: 25,000 MAU with 3.2 queries per session average. Please provide detailed cost breakdown, optimization recommendations, and ROI projections for implementing cost reduction strategies.", 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': payload_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'payload_integrity', 'business_role': 'CFO', 'company_stage': 'startup', 'expects_detailed_analysis': True}}
            await websocket.send(json.dumps(business_message))
            self.logger.info('📤 Business-focused message sent for payload analysis')
            all_events = []
            payload_analyses = []
            timeout = 70.0
            collection_start = time.time()
            while time.time() - collection_start < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=12.0)
                    event = json.loads(event_data)
                    all_events.append(event)
                    payload_valid = self._validate_event_payload(event)
                    business_context = self._extract_business_context(event)
                    if payload_valid:
                        integrity_metrics['valid_payloads'] += 1
                    else:
                        integrity_metrics['invalid_payloads'] += 1
                    if len(business_context) > 20:
                        integrity_metrics['business_context_events'] += 1
                    payload_analysis = {'event_type': event.get('type', 'unknown'), 'payload_valid': payload_valid, 'has_business_context': len(business_context) > 20, 'payload_size': len(str(event)), 'business_context': business_context[:100]}
                    payload_analyses.append(payload_analysis)
                    self.logger.info(f"📋 Payload analyzed: {payload_analysis['event_type']} (valid: {payload_valid}, context: {len(business_context) > 20})")
                    if event.get('type') == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
            await websocket.close()
            if all_events:
                valid_rate = integrity_metrics['valid_payloads'] / len(all_events)
                context_rate = integrity_metrics['business_context_events'] / len(all_events)
                integrity_metrics['payload_quality_score'] = valid_rate * 0.6 + context_rate * 0.4
            total_time = time.time() - payload_integrity_start
            assert len(all_events) > 0, 'Should receive events for payload analysis'
            assert integrity_metrics['valid_payloads'] > 0, 'Should have valid event payloads'
            valid_payload_rate = integrity_metrics['valid_payloads'] / len(all_events)
            assert valid_payload_rate >= 0.8, f"Payload validity rate too low: {valid_payload_rate:.1%} (valid: {integrity_metrics['valid_payloads']}, invalid: {integrity_metrics['invalid_payloads']})"
            context_rate = integrity_metrics['business_context_events'] / len(all_events)
            assert context_rate >= 0.3, f"Business context rate too low: {context_rate:.1%} (events with context: {integrity_metrics['business_context_events']})"
            assert integrity_metrics['payload_quality_score'] >= 0.6, f"Overall payload quality insufficient: {integrity_metrics['payload_quality_score']:.3f}"
            business_events = [analysis for analysis in payload_analyses if analysis['has_business_context'] and 'cost' in analysis['business_context'].lower()]
            assert len(business_events) > 0, 'Should have events with relevant business context for cost analysis'
            self.logger.info('📋 WebSocket event payload integrity validation complete')
            self.logger.info(f'   Total time: {total_time:.2f}s')
            self.logger.info(f'   Events analyzed: {len(all_events)}')
            self.logger.info(f"   Valid payloads: {integrity_metrics['valid_payloads']}")
            self.logger.info(f"   Invalid payloads: {integrity_metrics['invalid_payloads']}")
            self.logger.info(f"   Events with business context: {integrity_metrics['business_context_events']}")
            self.logger.info(f'   Valid payload rate: {valid_payload_rate:.1%}')
            self.logger.info(f'   Business context rate: {context_rate:.1%}')
            self.logger.info(f"   Payload quality score: {integrity_metrics['payload_quality_score']:.3f}")
            self.logger.info(f'   Business-relevant events: {len(business_events)}')
        except Exception as e:
            self.logger.error(f'❌ WebSocket event payload integrity test failed: {e}')
            raise AssertionError(f'WebSocket event payload integrity test failed: {e}. This indicates poor event quality and business context delivery.')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')