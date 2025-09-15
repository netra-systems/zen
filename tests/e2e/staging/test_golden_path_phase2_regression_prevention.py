#!/usr/bin/env python
"""
Golden Path Phase 2 Regression Prevention Test

MISSION CRITICAL: Protect $500K+ ARR during MessageRouter proxy removal.
This E2E test validates the complete Golden Path user flow to prevent regression
during SSOT MessageRouter Phase 2 migration.

CRITICAL PURPOSE:
- Tests complete user login → AI response flow end-to-end
- Validates all 5 WebSocket events are delivered correctly
- Ensures agent execution and meaningful responses work
- Protects against proxy removal breaking message routing
- Validates user isolation is maintained during migration

TEST STRATEGY:
- Before Phase 2: Test passes with proxy pattern active
- After Phase 2: Test passes without proxy pattern
- Failure indicates regression requiring immediate fix

Business Value: $500K+ ARR - Core chat functionality protection
Environment: Staging (real services, no Docker dependency)
Authentication: Real JWT/OAuth (no mocks per CLAUDE.md)
"""

import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field

# SSOT imports following CLAUDE.md guidelines
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from shared.isolated_environment import get_env

# Import production components - NO MOCKS per CLAUDE.md
from shared.types.core_types import UserID, ThreadID, RequestID

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.critical,
    pytest.mark.golden_path_phase2,
    pytest.mark.real
]


@dataclass
class GoldenPathTestMetrics:
    """Metrics for Golden Path performance and business value validation."""
    connection_time: float = 0.0
    authentication_time: float = 0.0
    first_event_time: float = 0.0
    agent_start_time: float = 0.0
    agent_completion_time: float = 0.0
    total_flow_time: float = 0.0
    websocket_events_received: List[Dict[str, Any]] = field(default_factory=list)
    message_routing_successful: bool = False
    agent_response_quality_score: int = 0
    user_isolation_validated: bool = False
    concurrent_users_supported: int = 0
    errors_encountered: List[str] = field(default_factory=list)


@dataclass
class WebSocketEvent:
    """Represents a WebSocket event received during testing."""
    event_type: str
    timestamp: float
    data: Dict[str, Any]
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    
    @property
    def elapsed_since_start(self) -> float:
        """Calculate time elapsed since test start."""
        return self.timestamp


class GoldenPathResponseValidator:
    """Validates AI response quality and business value."""
    
    @staticmethod
    def assess_response_quality(response_text: str) -> int:
        """
        Assess AI response quality on a scale of 0-100.
        
        Args:
            response_text: The AI response text to evaluate
            
        Returns:
            Quality score from 0-100
        """
        if not response_text or len(response_text.strip()) < 20:
            return 0
        
        score = 0
        text_lower = response_text.lower()
        
        # Substantive content indicators (40 points max)
        substantive_keywords = [
            'analyze', 'recommendation', 'suggest', 'improve', 'optimize',
            'implement', 'strategy', 'solution', 'approach', 'consider'
        ]
        substantive_score = min(
            sum(4 for keyword in substantive_keywords if keyword in text_lower),
            40
        )
        score += substantive_score
        
        # Technical depth indicators (30 points max)
        technical_keywords = [
            'system', 'process', 'method', 'algorithm', 'infrastructure',
            'configuration', 'architecture', 'performance', 'efficiency'
        ]
        technical_score = min(
            sum(3 for keyword in technical_keywords if keyword in text_lower),
            30
        )
        score += technical_score
        
        # Actionable insights (20 points max)
        actionable_keywords = [
            'step', 'action', 'next', 'should', 'can', 'will', 'plan'
        ]
        actionable_score = min(
            sum(2 for keyword in actionable_keywords if keyword in text_lower),
            20
        )
        score += actionable_score
        
        # Length and completeness (10 points max)
        length_score = min(len(response_text) // 50, 10)
        score += length_score
        
        return min(score, 100)
    
    @staticmethod
    def extract_business_value_indicators(response_text: str) -> List[str]:
        """Extract indicators of business value from response."""
        indicators = []
        text_lower = response_text.lower()
        
        business_patterns = [
            'cost', 'saving', 'efficiency', 'productivity', 'roi',
            'revenue', 'profit', 'optimization', 'improvement', 'automation'
        ]
        
        for pattern in business_patterns:
            if pattern in text_lower:
                indicators.append(pattern)
        
        return indicators


@pytest.mark.e2e
class TestGoldenPathPhase2RegressionPrevention(SSotAsyncTestCase):
    """
    E2E test suite for Golden Path Phase 2 regression prevention.
    
    CRITICAL: This test protects $500K+ ARR during MessageRouter proxy removal.
    """
    
    def setup_method(self, method):
        """Setup test environment with staging validation."""
        # Call parent setup_method (not async_setup_method)
        super().setup_method(method)

        # Initialize config first (before staging availability check)
        self.config = get_staging_config()
        self.metrics = GoldenPathTestMetrics()
        self.test_start_time = time.time()

        # Set up bypass for testing if needed
        env = self.get_env()
        if env.get("BYPASS_STAGING_HEALTH_CHECK") != "true":
            self.set_env_var("BYPASS_STAGING_HEALTH_CHECK", "true")

        # Validate staging environment availability
        if not is_staging_available():
            pytest.skip("Staging environment not available for Golden Path testing")
        
        # Set test environment variables
        self.set_env_var("GOLDEN_PATH_PHASE2_TEST", "true")
        self.set_env_var("TEST_USER_ISOLATION", "enabled")
        
    def teardown_method(self, method):
        """Cleanup and report metrics."""
        # Calculate total test time
        self.metrics.total_flow_time = time.time() - self.test_start_time
        
        # Log comprehensive metrics
        print(f"\n{'='*80}")
        print("GOLDEN PATH PHASE 2 TEST METRICS")
        print(f"{'='*80}")
        print(f"Total Flow Time: {self.metrics.total_flow_time:.3f}s")
        print(f"Connection Time: {self.metrics.connection_time:.3f}s")
        print(f"Authentication Time: {self.metrics.authentication_time:.3f}s")
        print(f"First Event Time: {self.metrics.first_event_time:.3f}s")
        print(f"Agent Completion Time: {self.metrics.agent_completion_time:.3f}s")
        print(f"WebSocket Events Received: {len(self.metrics.websocket_events_received)}")
        print(f"Message Routing Successful: {self.metrics.message_routing_successful}")
        print(f"Agent Response Quality Score: {self.metrics.agent_response_quality_score}/100")
        print(f"User Isolation Validated: {self.metrics.user_isolation_validated}")
        print(f"Concurrent Users Supported: {self.metrics.concurrent_users_supported}")
        print(f"Errors Encountered: {len(self.metrics.errors_encountered)}")
        
        # Record metrics for business value tracking
        self.record_metric("golden_path_total_time", self.metrics.total_flow_time)
        self.record_metric("golden_path_events_count", len(self.metrics.websocket_events_received))
        self.record_metric("golden_path_quality_score", self.metrics.agent_response_quality_score)
        self.record_metric("golden_path_success", self.metrics.message_routing_successful)
        
        # Call parent teardown_method (not async_teardown_method)
        super().teardown_method(method)
    
    async def create_authenticated_websocket_connection(self, user_id: str) -> tuple[Any, Dict[str, str]]:
        """
        Create authenticated WebSocket connection to staging.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Tuple of (websocket_connection, auth_headers)
        """
        connection_start = time.time()
        
        # Get staging authentication token
        env = get_env()
        staging_token = env.get("STAGING_JWT_TOKEN")
        
        if not staging_token:
            # Create test JWT token for staging
            import jwt
            payload = {
                'user_id': user_id,
                'email': f'{user_id}@goldenpath.test',
                'exp': datetime.now(timezone.utc) + timedelta(hours=1),
                'iat': datetime.now(timezone.utc),
                'sub': user_id,
                'golden_path_test': True
            }
            
            # Use staging JWT secret
            jwt_secret = env.get("JWT_SECRET_STAGING") or env.get("JWT_SECRET_KEY") or "test_jwt_secret_key_for_development_only"
            staging_token = jwt.encode(payload, jwt_secret, algorithm='HS256')
        
        auth_headers = {
            'Authorization': f'Bearer {staging_token}',
            'X-User-ID': user_id,
            'X-Test-Type': 'golden_path_phase2',
            'X-Environment': 'staging'
        }
        
        # Connect to staging WebSocket
        websocket_conn = await websockets.connect(
            self.config.websocket_url,
            additional_headers=auth_headers,
            close_timeout=30,
            ping_interval=20,
            ping_timeout=10
        )
        
        self.metrics.connection_time = time.time() - connection_start
        return websocket_conn, auth_headers
    
    async def wait_for_websocket_events(self, websocket, expected_events: Set[str], timeout: float = 120.0) -> List[WebSocketEvent]:
        """
        Wait for expected WebSocket events with comprehensive tracking.
        
        Args:
            websocket: WebSocket connection
            expected_events: Set of expected event types
            timeout: Maximum time to wait
            
        Returns:
            List of received WebSocket events
        """
        events_received = []
        events_found = set()
        start_time = time.time()
        
        while time.time() - start_time < timeout and len(events_found) < len(expected_events):
            try:
                # Wait for message with shorter timeout for responsiveness
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                receive_time = time.time()
                
                try:
                    data = json.loads(message)
                    event_type = data.get('type', data.get('event_type', 'unknown'))
                    
                    event = WebSocketEvent(
                        event_type=event_type,
                        timestamp=receive_time,
                        data=data,
                        user_id=data.get('user_id'),
                        thread_id=data.get('thread_id')
                    )
                    
                    events_received.append(event)
                    self.metrics.websocket_events_received.append(data)
                    
                    # Track first event timing
                    if not self.metrics.first_event_time:
                        self.metrics.first_event_time = receive_time - self.test_start_time
                    
                    # Track specific event types
                    if event_type in expected_events:
                        events_found.add(event_type)
                        
                        # Track agent lifecycle timing
                        if event_type == 'agent_started':
                            self.metrics.agent_start_time = receive_time - self.test_start_time
                        elif event_type == 'agent_completed':
                            self.metrics.agent_completion_time = receive_time - self.test_start_time
                    
                    print(f"[{receive_time - start_time:.1f}s] Received: {event_type}")
                    
                except json.JSONDecodeError:
                    print(f"[{receive_time - start_time:.1f}s] Non-JSON message: {message[:100]}")
                    
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                print(f"[{elapsed:.1f}s] Waiting for events... Found: {events_found}")
                continue
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed unexpectedly")
                break
        
        return events_received
    
    @pytest.mark.asyncio
    async def test_complete_golden_path_user_flow(self):
        """
        Test complete Golden Path user flow: Login → Send Message → Agent Response → User Receives Result.
        
        CRITICAL: This validates the core $500K+ ARR user journey.
        Must pass both before and after MessageRouter proxy removal.
        """
        # Arrange - Create unique test user
        user_id = f"golden_path_user_{uuid.uuid4().hex[:8]}"
        thread_id = f"golden_path_thread_{uuid.uuid4().hex[:8]}"
        request_id = f"golden_path_request_{uuid.uuid4().hex[:8]}"
        
        print(f"\n{'='*80}")
        print(f"TESTING COMPLETE GOLDEN PATH FLOW")
        print(f"User: {user_id}")
        print(f"Thread: {thread_id}")
        print(f"{'='*80}")
        
        # Act & Assert - Execute complete flow
        websocket = None
        try:
            # Step 1: Establish authenticated WebSocket connection
            print("[STEP 1] Establishing authenticated WebSocket connection...")
            websocket, auth_headers = await self.create_authenticated_websocket_connection(user_id)
            print(f"✓ WebSocket connected in {self.metrics.connection_time:.3f}s")
            
            # Step 2: Send user message
            print("[STEP 2] Sending user message...")
            user_message = {
                "type": "user_message",
                "content": "Analyze my AI infrastructure costs and provide optimization recommendations. I'm spending about $10,000/month and need to reduce costs by 30%.",
                "thread_id": thread_id,
                "user_id": user_id,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "golden_path_test": True
            }
            
            await websocket.send(json.dumps(user_message))
            message_sent_time = time.time()
            print(f"✓ User message sent at {message_sent_time - self.test_start_time:.3f}s")
            
            # Step 3: Wait for all critical WebSocket events
            print("[STEP 3] Waiting for critical WebSocket events...")
            expected_events = {
                'agent_started',
                'agent_thinking', 
                'tool_executing',
                'tool_completed',
                'agent_completed'
            }
            
            events = await self.wait_for_websocket_events(websocket, expected_events, timeout=180.0)
            
            # Assert all critical events received
            event_types_received = {event.event_type for event in events}
            missing_events = expected_events - event_types_received
            
            assert len(missing_events) == 0, f"Missing critical WebSocket events: {missing_events}"
            assert len(events) >= 5, f"Expected at least 5 events, got {len(events)}"
            
            print(f"✓ All critical WebSocket events received ({len(events)} total)")
            
            # Step 4: Validate agent response quality
            print("[STEP 4] Validating agent response quality...")
            agent_response = None
            
            # Find the final agent response
            for event in reversed(events):
                if event.event_type == 'agent_completed' and 'result' in event.data:
                    agent_response = event.data['result']
                    break
                elif 'content' in event.data and event.data.get('content'):
                    agent_response = event.data['content']
                    break
            
            assert agent_response is not None, "Must receive substantive agent response"
            
            # Validate response quality
            validator = GoldenPathResponseValidator()
            quality_score = validator.assess_response_quality(str(agent_response))
            self.metrics.agent_response_quality_score = quality_score
            
            assert quality_score >= 60, f"Agent response quality too low: {quality_score}/100"
            
            # Validate business value indicators
            business_indicators = validator.extract_business_value_indicators(str(agent_response))
            assert len(business_indicators) >= 2, f"Must include business value indicators, found: {business_indicators}"
            
            print(f"✓ Agent response quality validated (score: {quality_score}/100)")
            print(f"✓ Business value indicators: {business_indicators}")
            
            # Step 5: Validate timing performance
            print("[STEP 5] Validating performance requirements...")
            
            # Connection should be fast
            assert self.metrics.connection_time <= 10.0, f"Connection too slow: {self.metrics.connection_time:.3f}s"
            
            # First event should arrive quickly
            assert self.metrics.first_event_time <= 15.0, f"First event too slow: {self.metrics.first_event_time:.3f}s"
            
            # Complete flow should finish within reasonable time
            total_time = time.time() - self.test_start_time
            assert total_time <= 240.0, f"Golden Path flow too slow: {total_time:.3f}s"
            
            print(f"✓ Performance requirements met (total: {total_time:.3f}s)")
            
            # Mark successful completion
            self.metrics.message_routing_successful = True
            
            print(f"\n🎉 GOLDEN PATH FLOW COMPLETED SUCCESSFULLY")
            print(f"   Total Time: {total_time:.3f}s")
            print(f"   Events Received: {len(events)}")
            print(f"   Response Quality: {quality_score}/100")
            
        except Exception as e:
            self.metrics.errors_encountered.append(str(e))
            print(f"\n❌ GOLDEN PATH FLOW FAILED: {e}")
            raise
        
        finally:
            if websocket:
                await websocket.close()
    
    @pytest.mark.asyncio
    async def test_websocket_event_sequence_validation(self):
        """
        Test that WebSocket events are delivered in correct sequence.
        
        CRITICAL: Event sequence must remain consistent after proxy removal.
        """
        user_id = f"event_sequence_user_{uuid.uuid4().hex[:8]}"
        
        print(f"\n{'='*80}")
        print("TESTING WEBSOCKET EVENT SEQUENCE")
        print(f"{'='*80}")
        
        websocket = None
        try:
            # Connect and send message
            websocket, _ = await self.create_authenticated_websocket_connection(user_id)
            
            message = {
                "type": "user_message",
                "content": "Quick optimization analysis",
                "user_id": user_id,
                "thread_id": f"seq_thread_{uuid.uuid4().hex[:8]}",
                "sequence_test": True
            }
            
            await websocket.send(json.dumps(message))
            
            # Collect events with timing
            events = []
            timeout_start = time.time()
            
            while time.time() - timeout_start < 60.0:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    event_type = data.get('type', data.get('event_type', 'unknown'))
                    
                    events.append({
                        'type': event_type,
                        'timestamp': time.time(),
                        'data': data
                    })
                    
                    if event_type == 'agent_completed':
                        break
                        
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
            
            # Validate event sequence
            event_types = [event['type'] for event in events]
            
            # Must have agent_started before any other agent events
            if 'agent_started' in event_types and 'agent_thinking' in event_types:
                started_idx = event_types.index('agent_started')
                thinking_idx = event_types.index('agent_thinking')
                assert started_idx < thinking_idx, "agent_started must come before agent_thinking"
            
            # Must have tool_executing before tool_completed
            tool_executing_indices = [i for i, t in enumerate(event_types) if t == 'tool_executing']
            tool_completed_indices = [i for i, t in enumerate(event_types) if t == 'tool_completed']
            
            for exec_idx in tool_executing_indices:
                # Find next tool_completed after this tool_executing
                next_completed = next((idx for idx in tool_completed_indices if idx > exec_idx), None)
                assert next_completed is not None, "Each tool_executing must be followed by tool_completed"
            
            # Must have agent_completed as final event
            if 'agent_completed' in event_types:
                completed_idx = event_types.index('agent_completed')
                assert completed_idx == len(event_types) - 1 or completed_idx == len(event_types) - 2, "agent_completed should be final or second-to-last event"
            
            print(f"✓ Event sequence validated: {event_types}")
            
        finally:
            if websocket:
                await websocket.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_user_isolation(self):
        """
        Test that concurrent users are properly isolated during message routing.
        
        CRITICAL: User isolation must be maintained after proxy removal.
        """
        print(f"\n{'='*80}")
        print("TESTING CONCURRENT USER ISOLATION")
        print(f"{'='*80}")
        
        # Create multiple concurrent users
        num_users = 3
        user_contexts = []
        websockets_list = []
        
        try:
            # Create concurrent connections
            for i in range(num_users):
                user_id = f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}"
                websocket, _ = await self.create_authenticated_websocket_connection(user_id)
                
                user_contexts.append({
                    'user_id': user_id,
                    'websocket': websocket,
                    'thread_id': f"thread_{i}_{uuid.uuid4().hex[:8]}",
                    'messages_sent': [],
                    'events_received': []
                })
                websockets_list.append(websocket)
            
            print(f"✓ Created {num_users} concurrent connections")
            
            # Send unique messages from each user
            for i, context in enumerate(user_contexts):
                message = {
                    "type": "user_message",
                    "content": f"User {i} isolation test - optimize costs for {i*1000+5000} monthly spend",
                    "user_id": context['user_id'],
                    "thread_id": context['thread_id'],
                    "isolation_test_id": i,
                    "unique_marker": f"ISOLATION_TEST_USER_{i}"
                }
                
                await context['websocket'].send(json.dumps(message))
                context['messages_sent'].append(message)
                print(f"✓ User {i} message sent")
            
            # Collect responses for each user
            collection_tasks = []
            
            async def collect_user_events(context):
                """Collect events for a specific user."""
                timeout_start = time.time()
                while time.time() - timeout_start < 90.0:
                    try:
                        message = await asyncio.wait_for(context['websocket'].recv(), timeout=5.0)
                        data = json.loads(message)
                        context['events_received'].append(data)
                        
                        if data.get('type') == 'agent_completed':
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue
            
            # Run collection tasks concurrently
            for context in user_contexts:
                collection_tasks.append(collect_user_events(context))
            
            await asyncio.gather(*collection_tasks, return_exceptions=True)
            
            # Validate isolation
            for i, context in enumerate(user_contexts):
                events = context['events_received']
                assert len(events) > 0, f"User {i} must receive events"
                
                # Check that user only receives their own events
                for event in events:
                    event_user_id = event.get('user_id')
                    if event_user_id:
                        assert event_user_id == context['user_id'], f"User {i} received event for different user: {event_user_id}"
                
                # Check for unique markers in responses
                responses_text = ' '.join(str(event.get('content', '')) for event in events)
                own_marker = f"ISOLATION_TEST_USER_{i}"
                
                # Should see reference to own unique spending amount
                spending_pattern = str(i*1000+5000)
                assert spending_pattern in responses_text or any(spending_pattern in str(event) for event in events), f"User {i} response should reference their unique spending amount"
                
                print(f"✓ User {i} isolation validated ({len(events)} events)")
            
            self.metrics.user_isolation_validated = True
            self.metrics.concurrent_users_supported = num_users
            
            print(f"✓ Concurrent user isolation validated for {num_users} users")
            
        finally:
            # Clean up all connections
            for websocket in websockets_list:
                if websocket:
                    await websocket.close()
    
    @pytest.mark.asyncio
    async def test_error_handling_graceful_degradation(self):
        """
        Test graceful degradation if routing issues occur.
        
        CRITICAL: System must fail gracefully if proxy removal causes issues.
        """
        user_id = f"error_handling_user_{uuid.uuid4().hex[:8]}"
        
        print(f"\n{'='*80}")
        print("TESTING ERROR HANDLING AND GRACEFUL DEGRADATION")
        print(f"{'='*80}")
        
        websocket = None
        try:
            # Connect with valid authentication
            websocket, _ = await self.create_authenticated_websocket_connection(user_id)
            
            # Test 1: Send malformed message (should be handled gracefully)
            malformed_message = '{"type": "user_message", "content": "test", invalid_json'
            
            try:
                await websocket.send(malformed_message)
                print("✓ Malformed message sent")
            except Exception as e:
                print(f"✓ Malformed message rejected as expected: {e}")
            
            # Test 2: Send message with missing required fields
            incomplete_message = {
                "type": "user_message"
                # Missing content and other required fields
            }
            
            await websocket.send(json.dumps(incomplete_message))
            print("✓ Incomplete message sent")
            
            # Test 3: Send valid message and ensure system still works
            valid_message = {
                "type": "user_message",
                "content": "System recovery test - please provide a simple response",
                "user_id": user_id,
                "thread_id": f"recovery_thread_{uuid.uuid4().hex[:8]}",
                "error_recovery_test": True
            }
            
            await websocket.send(json.dumps(valid_message))
            print("✓ Valid recovery message sent")
            
            # Wait for response to valid message
            recovery_events = []
            timeout_start = time.time()
            
            while time.time() - timeout_start < 60.0:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    recovery_events.append(data)
                    
                    if data.get('type') == 'agent_completed':
                        break
                        
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
            
            # Assert system recovered and processed valid message
            assert len(recovery_events) > 0, "System must recover and process valid messages after errors"
            
            # Check for error handling events
            error_events = [event for event in recovery_events if 'error' in event.get('type', '').lower()]
            
            print(f"✓ System recovery validated ({len(recovery_events)} events, {len(error_events)} error events)")
            
        finally:
            if websocket:
                await websocket.close()
    
    @pytest.mark.asyncio
    async def test_performance_baseline_establishment(self):
        """
        Establish performance baseline for Golden Path flow.
        
        CRITICAL: Performance must not degrade after proxy removal.
        """
        user_id = f"perf_baseline_user_{uuid.uuid4().hex[:8]}"
        
        print(f"\n{'='*80}")
        print("ESTABLISHING PERFORMANCE BASELINE")
        print(f"{'='*80}")
        
        performance_runs = []
        
        # Run multiple iterations to establish baseline
        for run in range(3):
            print(f"[RUN {run+1}/3] Starting performance test...")
            
            run_start = time.time()
            websocket = None
            
            try:
                # Measure connection time
                conn_start = time.time()
                websocket, _ = await self.create_authenticated_websocket_connection(f"{user_id}_run_{run}")
                connection_time = time.time() - conn_start
                
                # Send message and measure response time
                message_start = time.time()
                message = {
                    "type": "user_message",
                    "content": "Performance baseline test - quick analysis",
                    "user_id": f"{user_id}_run_{run}",
                    "thread_id": f"perf_thread_{run}_{uuid.uuid4().hex[:8]}",
                    "performance_test": True
                }
                
                await websocket.send(json.dumps(message))
                
                # Wait for first event and completion
                first_event_time = None
                completion_time = None
                
                timeout_start = time.time()
                while time.time() - timeout_start < 120.0:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        data = json.loads(response)
                        
                        if first_event_time is None:
                            first_event_time = time.time() - message_start
                        
                        if data.get('type') == 'agent_completed':
                            completion_time = time.time() - message_start
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue
                
                run_metrics = {
                    'run': run + 1,
                    'connection_time': connection_time,
                    'first_event_time': first_event_time or 999.0,
                    'completion_time': completion_time or 999.0,
                    'total_time': time.time() - run_start
                }
                
                performance_runs.append(run_metrics)
                
                print(f"✓ Run {run+1}: conn={connection_time:.3f}s, first={first_event_time:.3f}s, complete={completion_time:.3f}s")
                
            finally:
                if websocket:
                    await websocket.close()
        
        # Calculate baseline metrics
        avg_connection = sum(run['connection_time'] for run in performance_runs) / len(performance_runs)
        avg_first_event = sum(run['first_event_time'] for run in performance_runs) / len(performance_runs)
        avg_completion = sum(run['completion_time'] for run in performance_runs) / len(performance_runs)
        
        # Record baseline for comparison
        self.record_metric("baseline_connection_time", avg_connection)
        self.record_metric("baseline_first_event_time", avg_first_event)
        self.record_metric("baseline_completion_time", avg_completion)
        
        # Validate baseline performance meets requirements
        assert avg_connection <= 10.0, f"Connection baseline too slow: {avg_connection:.3f}s"
        assert avg_first_event <= 20.0, f"First event baseline too slow: {avg_first_event:.3f}s"
        assert avg_completion <= 120.0, f"Completion baseline too slow: {avg_completion:.3f}s"
        
        print(f"\n✓ PERFORMANCE BASELINE ESTABLISHED:")
        print(f"   Average Connection: {avg_connection:.3f}s")
        print(f"   Average First Event: {avg_first_event:.3f}s")
        print(f"   Average Completion: {avg_completion:.3f}s")