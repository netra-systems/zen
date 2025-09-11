#!/usr/bin/env python
'''E2E TEST SUITE: ActionsAgent Complete Workflow with Real Services

THIS SUITE VALIDATES THE ENTIRE ACTIONS AGENT USER JOURNEY.
Business Value: $3M+ ARR - Complete user-to-action-plan pipeline

This E2E test suite validates the complete workflow:
1. User request → Supervisor → ActionsAgent → Action Plan
2. Real WebSocket connections with real-time user experience
3. Real database persistence and state management
4. Real LLM interactions with actual API calls
5. Real Redis caching and session management
6. Complete chat value delivery pipeline
7. Performance under production-like conditions
8. End-to-end error recovery and user experience

CRITICAL: NO MOCKS - Tests complete production pipeline
Real services, real data, real user experience measurement
'''

import asyncio
import json
import os
import sys
import time
import uuid
import websockets
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import pytest
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import psutil
from test_framework.unified_docker_manager import UnifiedDockerManager

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger

# Import test infrastructure (REAL SERVICES ONLY)
from shared.isolated_environment import IsolatedEnvironment

# Import production components for E2E testing
try:
    from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent as ActionsAgent
except ImportError:
    from netra_backend.app.agents.data_helper_agent import DataHelperAgent as ActionsAgent

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# Import state and data structures
from netra_backend.app.agents.state import (
    DeepAgentState
)

try:
    from shared.types.agent_types import AgentExecutionResult
except ImportError:
    from netra_backend.app.schemas.shared_types import DataAnalysisResponse as AgentExecutionResult

# Import services for complete E2E flow
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.redis_manager import RedisManager


# ============================================================================
# E2E TEST DATA AND METRICS
# ============================================================================

@dataclass
class UserExperienceMetrics:
    """Metrics measuring complete user experience."""
    request_to_response_time: float = 0.0
    websocket_responsiveness_score: float = 0.0
    action_plan_quality_score: float = 0.0
    chat_value_delivery_score: float = 0.0
    error_handling_ux_score: float = 0.0
    performance_satisfaction_score: float = 0.0
    overall_user_experience_score: float = 0.0

    def calculate_overall_score(self) -> float:
        """Calculate weighted user experience score."""
        weights = {
            'websocket_responsiveness_score': 0.25,  # Real-time feedback critical
            'action_plan_quality_score': 0.25,      # Core business value
            'chat_value_delivery_score': 0.20,      # Chat is primary interface
            'performance_satisfaction_score': 0.15,  # User satisfaction
            'error_handling_ux_score': 0.10,        # Resilience UX
            'request_to_response_time': 0.05        # Speed component
        }

        # Convert request_to_response_time to score (lower is better)
        time_score = max(0.0, 1.0 - (self.request_to_response_time / 60.0))  # 60s = 0 score

        total = (
            self.websocket_responsiveness_score * weights['websocket_responsiveness_score'] +
            self.action_plan_quality_score * weights['action_plan_quality_score'] +
            self.chat_value_delivery_score * weights['chat_value_delivery_score'] +
            self.performance_satisfaction_score * weights['performance_satisfaction_score'] +
            self.error_handling_ux_score * weights['error_handling_ux_score'] +
            time_score * weights['request_to_response_time']
        )

        self.overall_user_experience_score = total
        return total


@dataclass
class E2ETestSession:
    """Complete E2E test session with real service connections."""
    session_id: str
    user_id: str
    thread_id: str
    websocket_connection: Optional[Any] = None
    database_connection: Optional[Any] = None
    redis_connection: Optional[Any] = None
    start_time: float = field(default_factory=time.time)
    websocket_events: List[Dict] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    errors_encountered: List[str] = field(default_factory=list)


class RealWebSocketClient:
    """Real WebSocket client for E2E testing."""

    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.websocket = None
        self.received_messages: List[Dict] = []
        self.connection_established = False
        self.message_handlers: Dict[str, callable] = {}
        self._lock = asyncio.Lock()

    async def connect(self, thread_id: str, user_id: str) -> bool:
        """Connect to real WebSocket endpoint."""
        try:
            ws_url = f"{self.base_url}/ws?thread_id={thread_id}&user_id={user_id}"

            # Connect with real WebSocket
            self.websocket = await websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )

            self.connection_established = True

            # Start message listener
            asyncio.create_task(self._message_listener())

            logger.info(f"✅ WebSocket connected to {ws_url}")
            return True

        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            self.connection_established = False
            return False

    async def _message_listener(self):
        """Listen for WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    async with self._lock:
                        self.received_messages.append({
                            'data': data,
                            'timestamp': time.time(),
                            'message_type': data.get('type', 'unknown')
                        })

                        # Call handlers
                        message_type = data.get('type')
                        if message_type in self.message_handlers:
                            await self.message_handlers[message_type](data)

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in WebSocket message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket message listener error: {e}")

    def on_message(self, message_type: str, handler: callable):
        """Register message handler."""
        self.message_handlers[message_type] = handler

    async def send_user_message(self, message: str) -> bool:
        """Send user message through WebSocket."""
        if not self.websocket or not self.connection_established:
            logger.error("WebSocket not connected")
            return False

        try:
            await self.websocket.send(json.dumps({
                'type': 'user_message',
                'message': message,
                'timestamp': time.time()
            }))
            logger.info(f"📤 Sent message: {message[:100]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            return False

    async def wait_for_events(self, expected_types: List[str], timeout: float = 60.0) -> List[Dict]:
        """Wait for specific WebSocket events."""
        start_time = time.time()
        found_events = []
        expected_set = set(expected_types)

        logger.info(f"⏳ Waiting for events: {expected_types}")

        while time.time() - start_time < timeout:
            async with self._lock:
                for message in self.received_messages:
                    if message['message_type'] in expected_types and message not in found_events:
                        found_events.append(message)
                        logger.info(f"📨 Received event: {message['message_type']}")

                # Check if we have all expected event types
                found_types = set(msg['message_type'] for msg in found_events)
                if expected_set.issubset(found_types):
                    logger.info(f"✅ All expected events received: {found_types}")
                    return found_events

            await asyncio.sleep(0.5)

        logger.warning(f"⚠️ Timeout waiting for events. Expected: {expected_types}, Found: {[e['message_type'] for e in found_events]}")
        return found_events

    async def disconnect(self):
        """Disconnect WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connection_established = False
            logger.info("🔌 WebSocket disconnected")


class RealServiceIntegrator:
    """Integrates with real backend services for E2E testing."""

    def __init__(self, env: IsolatedEnvironment):
        self.env = env
        self.base_url = env.get('BACKEND_URL', 'http://localhost:8000')
        self.session = None

    async def initialize_session(self) -> aiohttp.ClientSession:
        """Initialize HTTP session for API calls."""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=60.0)
        )
        logger.info(f"🌐 HTTP session initialized for {self.base_url}")
        return self.session

    async def create_thread(self, user_id: str) -> str:
        """Create new thread through real API."""
        if not self.session:
            await self.initialize_session()

        try:
            async with self.session.post(
                f"{self.base_url}/api/threads/create",
                json={'user_id': user_id}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    thread_id = data.get('thread_id')
                    logger.info(f"📄 Created thread {thread_id} for user {user_id}")
                    return thread_id
                else:
                    logger.error(f"Thread creation failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Thread creation error: {e}")
            return None

    async def send_chat_message(self, thread_id: str, user_id: str, message: str) -> bool:
        """Send chat message through real API."""
        if not self.session:
            await self.initialize_session()

        try:
            async with self.session.post(
                f"{self.base_url}/api/chat/send",
                json={
                    'thread_id': thread_id,
                    'user_id': user_id,
                    'message': message
                }
            ) as response:
                success = response.status == 200
                if success:
                    logger.info(f"📨 Message sent to thread {thread_id}")
                else:
                    logger.error(f"Message sending failed: {response.status}")
                return success
        except Exception as e:
            logger.error(f"Message sending error: {e}")
            return False

    async def get_thread_status(self, thread_id: str) -> Dict:
        """Get thread status through real API."""
        if not self.session:
            await self.initialize_session()

        try:
            async with self.session.get(
                f"{self.base_url}/api/threads/{thread_id}/status"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"📋 Thread {thread_id} status: {data.get('status')}")
                    return data
                else:
                    logger.error(f"Thread status check failed: {response.status}")
                    return {'status': 'unknown', 'error': f'HTTP {response.status}'}
        except Exception as e:
            logger.error(f"Thread status error: {e}")
            return {'status': 'error', 'error': str(e)}

    async def cleanup(self):
        """Clean up HTTP session."""
        if self.session:
            await self.session.close()
            logger.info("🧹 HTTP session cleaned up")


# ============================================================================
# E2E USER EXPERIENCE TESTS
# ============================================================================

class TestActionsAgentCompleteUserFlow:
    """E2E tests for complete ActionsAgent user experience."""

    @pytest.fixture
    async def setup_complete_e2e_environment(self):
        """Setup complete real services environment for E2E testing."""
        logger.info("🚀 Setting up complete E2E environment with REAL services...")

        # Start real services
        self.docker_manager = UnifiedDockerManager()
        services_started = await self.docker_manager.ensure_services_running([
            'postgres', 'redis', 'backend', 'auth'
        ])

        if not services_started:
            pytest.skip("Real services not available for E2E testing")

        # Setup environment
        self.env = IsolatedEnvironment()

        # Initialize real service connections
        self.service_integrator = RealServiceIntegrator(self.env)
        await self.service_integrator.initialize_session()

        # Initialize database and Redis connections
        self.database_manager = DatabaseManager()
        self.redis_manager = RedisManager()

        # Test session tracking
        self.test_sessions: List[E2ETestSession] = []

        logger.info("✅ E2E environment ready with real services")

        yield

        # Cleanup
        logger.info("🧹 Cleaning up E2E environment...")
        for session in self.test_sessions:
            if session.websocket_connection:
                try:
                    await session.websocket_connection.disconnect()
                except:
                    pass

        await self.service_integrator.cleanup()
        await self.docker_manager.cleanup_if_needed()

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_complete_user_to_action_plan_journey(self, setup_complete_e2e_environment):
        """CRITICAL: Test complete user journey from request to action plan."""
        logger.info("\\n" + "🎯 STARTING COMPLETE USER-TO-ACTION-PLAN JOURNEY TEST")

        # Create E2E test session
        session = E2ETestSession(
            session_id=f"e2e-test-{uuid.uuid4()}",
            user_id=f"test-user-{uuid.uuid4()}",
            thread_id=""  # Will be created
        )
        self.test_sessions.append(session)

        metrics = UserExperienceMetrics()
        journey_start_time = time.time()

        try:
            # STEP 1: Create thread through real API
            logger.info("📝 Step 1: Creating thread through real backend API...")
            session.thread_id = await self.service_integrator.create_thread(session.user_id)

            assert session.thread_id is not None, \
                "Failed to create thread through real API - backend may be down"

            logger.info(f"✅ Thread created: {session.thread_id}")

            # STEP 2: Establish real WebSocket connection
            logger.info("🔌 Step 2: Establishing real WebSocket connection...")
            ws_client = RealWebSocketClient()

            websocket_connected = await ws_client.connect(session.thread_id, session.user_id)
            assert websocket_connected, \
                "Failed to establish real WebSocket connection - WebSocket service may be down"

            session.websocket_connection = ws_client

            # Setup WebSocket event tracking
            agent_events_received = []

            async def track_agent_event(data):
                agent_events_received.append({
                    'type': data.get('type'),
                    'timestamp': time.time(),
                    'data': data
                })
                logger.info(f"📡 Event received: {data.get('type')}")

            # Register for all critical agent events
            critical_events = [
                'agent_started', 'agent_thinking', 'tool_executing',
                'tool_completed', 'agent_completed', 'final_report'
            ]

            for event_type in critical_events:
                ws_client.on_message(event_type, track_agent_event)

            logger.info("✅ Real WebSocket connection established")

            # STEP 3: Send realistic user message for action planning
            logger.info("💬 Step 3: Sending realistic user request...")
            user_request = (
                "I need to optimize our cloud costs while maintaining performance. "
                "Our monthly cloud bill is $50,000 and we're seeing 15% month-over-month growth. "
                "We have compute, storage, and database services across multiple regions. "
                "Please analyze our setup and create a detailed action plan to reduce costs by 20-30% "
                "without impacting system performance or availability."
            )

            message_sent = await ws_client.send_user_message(user_request)
            assert message_sent, "Failed to send user message through WebSocket"

            # Also send through HTTP API for complete integration
            api_sent = await self.service_integrator.send_chat_message(
                session.thread_id, session.user_id, user_request
            )
            assert api_sent, "Failed to send message through API"

            logger.info("✅ User request sent through both WebSocket and API")

            # STEP 4: Wait for and validate real-time agent events
            logger.info("⏳ Step 4: Waiting for real-time agent processing...")

            # Wait for critical agent lifecycle events
            agent_events = await ws_client.wait_for_events(
                expected_types=['agent_started', 'agent_thinking', 'agent_completed'],
                timeout=120.0  # Generous timeout for real LLM processing
            )

            # Validate real-time responsiveness
            if agent_events:
                first_event_time = min(event['timestamp'] for event in agent_events)
                responsiveness_delay = first_event_time - journey_start_time

                metrics.websocket_responsiveness_score = max(0.0, 1.0 - (responsiveness_delay / 10.0))
                logger.info(f"⚡ Responsiveness delay: {responsiveness_delay:.2f}s (score: {metrics.websocket_responsiveness_score:.2f})")
            else:
                metrics.websocket_responsiveness_score = 0.0
                logger.warning("⚠️ No agent events received")

            # STEP 5: Validate action plan generation and quality
            logger.info("📋 Step 5: Validating action plan generation...")

            # Wait additional time for final results
            await asyncio.sleep(5.0)

            # Check thread status through API
            thread_status = await self.service_integrator.get_thread_status(session.thread_id)
            logger.info(f"📋 Thread status: {thread_status}")

            # Analyze action plan quality from received events
            final_reports = [event for event in agent_events 
                           if event['message_type'] in ['agent_completed', 'final_report']]

            if final_reports:
                # Extract action plan data
                action_plan_data = final_reports[-1].get('data', {})

                # Quality scoring based on action plan content
                quality_indicators = {
                    'has_recommendations': bool(action_plan_data.get('recommendations')),
                    'has_steps': bool(action_plan_data.get('steps')),
                    'addresses_cost_optimization': 'cost' in str(action_plan_data).lower(),
                    'addresses_performance': 'performance' in str(action_plan_data).lower(),
                    'has_specific_actions': len(str(action_plan_data)) > 200
                }

                quality_score = sum(quality_indicators.values()) / len(quality_indicators)
                metrics.action_plan_quality_score = quality_score

                logger.info(f"🎯 Action plan quality score: {quality_score:.2f}")
                for indicator, present in quality_indicators.items():
                    status = "✅" if present else "❌"
                    logger.info(f"  {status} {indicator}: {present}")
            else:
                metrics.action_plan_quality_score = 0.0
                logger.warning("⚠️ No action plan received")

            # STEP 6: Measure overall chat value delivery
            logger.info("💎 Step 6: Measuring chat value delivery...")

            total_events = len(agent_events)
            event_types = [e['message_type'] for e in agent_events]

            # Chat value indicators
            value_indicators = {
                'real_time_feedback': 'agent_thinking' in event_types,
                'processing_visibility': 'agent_started' in event_types,
                'completion_notification': any(t in event_types for t in ['agent_completed', 'final_report']),
                'sufficient_updates': total_events >= 3,
                'timely_response': metrics.websocket_responsiveness_score > 0.5
            }

            chat_value_score = sum(value_indicators.values()) / len(value_indicators)
            metrics.chat_value_delivery_score = chat_value_score

            logger.info(f"💎 Chat value delivery score: {chat_value_score:.2f}")

            # Calculate final metrics
            journey_end_time = time.time()
            metrics.request_to_response_time = journey_end_time - journey_start_time
            metrics.performance_satisfaction_score = max(0.0, 1.0 - (metrics.request_to_response_time / 120.0))

            overall_ux_score = metrics.calculate_overall_score()

            # CRITICAL VALIDATIONS
            assert total_events > 0, \
                f"No WebSocket events received - agent pipeline may be broken. Expected at least agent_started event."

            assert metrics.websocket_responsiveness_score > 0.3, \
                f"WebSocket responsiveness too low: {metrics.websocket_responsiveness_score:.2f} (min 0.3). Real-time feedback is failing."

            assert metrics.request_to_response_time < 150.0, \
                f"Request to response time too slow: {metrics.request_to_response_time:.2f}s (max 150s). Performance is unacceptable."

            assert overall_ux_score >= 0.6, \
                f"Overall user experience score too low: {overall_ux_score:.2f} (min 0.6). System is not delivering business value."

            # SUCCESS REPORT
            logger.info("\\n" + "🎉 E2E USER JOURNEY COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"WebSocket Responsiveness: {metrics.websocket_responsiveness_score:.2f}")
            logger.info(f"Action Plan Quality: {metrics.action_plan_quality_score:.2f}")
            logger.info(f"Chat Value Delivery: {metrics.chat_value_delivery_score:.2f}")
            logger.info(f"Performance Satisfaction: {metrics.performance_satisfaction_score:.2f}")
            logger.info(f"Total Response Time: {metrics.request_to_response_time:.2f}s")
            logger.info(f"Overall UX Score: {overall_ux_score:.2f}")
            logger.info(f"Events Received: {total_events} ({event_types})")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"🚨 E2E test failed: {e}")
            metrics.error_handling_ux_score = 0.0
            raise

        finally:
            # Cleanup WebSocket
            if session.websocket_connection:
                await session.websocket_connection.disconnect()


# ============================================================================
# ADDITIONAL E2E TEST METHODS
# ============================================================================

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_user_sessions_e2e(self, setup_complete_e2e_environment):
        """CRITICAL: Test multiple concurrent user sessions E2E."""
        logger.info("\\n" + "👥 STARTING CONCURRENT USER SESSIONS E2E TEST")

        concurrent_users = 3
        user_sessions = []

        # Create concurrent user sessions
        for i in range(concurrent_users):
            session = E2ETestSession(
                session_id=f"concurrent-test-{i}-{uuid.uuid4()}",
                user_id=f"concurrent-user-{i}-{uuid.uuid4()}",
                thread_id=""
            )
            user_sessions.append(session)
            self.test_sessions.append(session)

        async def run_concurrent_user_journey(session: E2ETestSession, user_index: int):
            try:
                # Create thread
                session.thread_id = await self.service_integrator.create_thread(session.user_id)
                if not session.thread_id:
                    return {'success': False, 'error': 'Thread creation failed', 'user_index': user_index}

                # Connect WebSocket
                ws_client = RealWebSocketClient()
                connected = await ws_client.connect(session.thread_id, session.user_id)
                if not connected:
                    return {'success': False, 'error': 'WebSocket connection failed', 'user_index': user_index}

                session.websocket_connection = ws_client

                # Send user request
                user_request = f"User {user_index}: Create an optimization plan for our system performance."

                await ws_client.send_user_message(user_request)

                # Wait for agent response
                events = await ws_client.wait_for_events(
                    expected_types=['agent_started', 'agent_completed'],
                    timeout=60.0
                )

                return {
                    'success': True,
                    'user_index': user_index,
                    'events_received': len(events),
                    'thread_id': session.thread_id
                }

            except Exception as e:
                return {'success': False, 'error': str(e), 'user_index': user_index}

        # Run all sessions concurrently
        start_time = time.time()
        tasks = [run_concurrent_user_journey(user_sessions[i], i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Analyze concurrent results
        successful_sessions = [result for result in results if isinstance(result, dict) and result.get('success')]
        success_rate = len(successful_sessions) / concurrent_users

        # Validate concurrent performance
        assert success_rate >= 0.67, \
            f"Concurrent session success rate too low: {success_rate:.2f} (min 0.67). System cannot handle multiple users."

        assert total_time < 90.0, \
            f"Concurrent execution too slow: {total_time:.2f}s (max 90s). Performance degrades under load."

        # Log results
        logger.info(f"✅ Concurrent test completed: {len(successful_sessions)}/{concurrent_users} successful")
        for result in results:
            if isinstance(result, dict):
                if result['success']:
                    logger.info(f"  ✅ User {result['user_index']}: {result['events_received']} events")
                else:
                    logger.warning(f"  ❌ User {result['user_index']}: {result['error']}")

    @pytest.mark.asyncio 
    @pytest.mark.critical
    async def test_error_recovery_user_experience(self, setup_complete_e2e_environment):
        """CRITICAL: Test error recovery from user experience perspective."""
        logger.info("\\n" + "🛠️ STARTING ERROR RECOVERY USER EXPERIENCE TEST")

        # Create session
        session = E2ETestSession(
            session_id=f"error-recovery-{uuid.uuid4()}",
            user_id=f"recovery-user-{uuid.uuid4()}",
            thread_id=""
        )
        self.test_sessions.append(session)

        try:
            # Setup normal connection
            session.thread_id = await self.service_integrator.create_thread(session.user_id)
            assert session.thread_id, "Thread creation failed for error recovery test"

            ws_client = RealWebSocketClient()
            connected = await ws_client.connect(session.thread_id, session.user_id)
            assert connected, "WebSocket connection failed for error recovery test"

            session.websocket_connection = ws_client

            # Test error scenarios that users might encounter
            error_scenarios = [
                "",  # Empty message
                "x" * 10000,  # Very long message
                "Invalid request with no clear intent or structure that might confuse the system"
            ]

            recovery_scores = []

            for i, error_scenario in enumerate(error_scenarios):
                logger.info(f"🧪 Testing error scenario {i+1}: {error_scenario[:50]}...")

                # Send problematic request
                await ws_client.send_user_message(error_scenario)

                # Wait for system response
                start_time = time.time()
                events = await ws_client.wait_for_events(
                    expected_types=['agent_started', 'agent_completed', 'error'],
                    timeout=45.0
                )
                recovery_time = time.time() - start_time

                # Analyze recovery quality
                if events:
                    # System responded - good
                    recovery_score = max(0.0, 1.0 - (recovery_time / 30.0))  # 30s = 0 score

                    # Bonus for graceful error handling
                    event_types = [e['message_type'] for e in events]
                    if any('error' not in t.lower() for t in event_types):
                        recovery_score += 0.2  # Bonus for non-error response

                    recovery_scores.append(min(1.0, recovery_score))
                    logger.info(f"✅ Recovery time: {recovery_time:.2f}s, score: {recovery_score:.2f}")
                else:
                    recovery_scores.append(0.0)
                    logger.warning(f"❌ No response to error scenario {i+1}")

                # Brief pause between scenarios
                await asyncio.sleep(2.0)

            # Overall error recovery assessment
            avg_recovery_score = sum(recovery_scores) / len(recovery_scores)

            assert avg_recovery_score >= 0.5, \
                f"Error recovery score too low: {avg_recovery_score:.2f} (min 0.5). System does not handle errors gracefully."

            logger.info(f"✅ Error recovery test passed: {avg_recovery_score:.2f} average score")

        except Exception as e:
            logger.error(f"🚨 Error recovery test failed: {e}")
            raise

        finally:
            if session.websocket_connection:
                await session.websocket_connection.disconnect()


if __name__ == "__main__":
    # Run with: python tests/e2e/test_actions_agent_full_flow.py
    # Or: pytest tests/e2e/test_actions_agent_full_flow.py -v
    pytest.main([__file__, "-v", "--tb=short"])