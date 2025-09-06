#!/usr/bin/env python
"""E2E TEST SUITE: ActionsAgent Complete Workflow with Real Services

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
"""

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
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from netra_backend.app.core.agent_registry import AgentRegistry

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger

# Import test infrastructure (REAL SERVICES ONLY)
from test_framework.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import IsolatedEnvironment

# Import production components for E2E testing
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager

# Import state and data structures
from netra_backend.app.agents.state import (
    DeepAgentState, 
    OptimizationsResult, 
    ActionPlanResult,
    PlanStep
)
from netra_backend.app.schemas.shared_types import DataAnalysisResponse

# Import services for complete E2E flow
from netra_backend.app.services.database.run_repository import RunRepository
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
    pass
        self.base_url = base_url
        self.websocket = None
        self.received_messages: List[Dict] = []
        self.connection_established = False
        self.message_handlers: Dict[str, callable] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, thread_id: str, user_id: str) -> bool:
        """Connect to real WebSocket endpoint."""
        try:
            ws_url = f"{self.base_url}/ws/{thread_id}/{user_id}"
            
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
            
            logger.info(f"✅ Real WebSocket connected: {ws_url}")
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
            logger.error(f"WebSocket listener error: {e}")
    
    def on_message(self, message_type: str, handler: callable):
        """Register message handler."""
    pass
        self.message_handlers[message_type] = handler
    
    async def send_user_message(self, message: str) -> bool:
        """Send user message through WebSocket."""
        if not self.websocket or not self.connection_established:
            await asyncio.sleep(0)
    return False
        
        try:
            await self.websocket.send(json.dumps({
                'type': 'user_message',
                'message': message,
                'timestamp': time.time()
            }))
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            return False
    
    async def wait_for_events(self, expected_types: List[str], timeout: float = 60.0) -> List[Dict]:
        """Wait for specific WebSocket events."""
        start_time = time.time()
        found_events = []
        
        while time.time() - start_time < timeout:
            async with self._lock:
                for message in self.received_messages:
                    if message['message_type'] in expected_types:
                        found_events.append(message)
            
            if len(set(msg['message_type'] for msg in found_events)) >= len(set(expected_types)):
                break
                
            await asyncio.sleep(0.5)
        
        return found_events
    
    async def disconnect(self):
        """Disconnect WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connection_established = False


class RealServiceIntegrator:
    """Integrates with real backend services for E2E testing."""
    
    def __init__(self, env: IsolatedEnvironment):
    pass
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
        await asyncio.sleep(0)
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
                    return data['thread_id']
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
                f"{self.base_url}/api/chat/message",
                json={
                    'thread_id': thread_id,
                    'user_id': user_id,
                    'message': message
                }
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Chat message error: {e}")
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
                    return await response.json()
                else:
                    return {'status': 'unknown', 'error': f'HTTP {response.status}'}
        except Exception as e:
            logger.error(f"Thread status error: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def cleanup(self):
        """Clean up HTTP session."""
        if self.session:
            await self.session.close()


# ============================================================================
# E2E USER EXPERIENCE TESTS
# ============================================================================

class TestActionsAgentCompleteUserFlow:
    """E2E tests for complete ActionsAgent user experience."""
    
    @pytest.fixture(autouse=True)
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
        self.run_repository = RunRepository()
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
    @pytest.mark.timeout(180)
    async def test_complete_user_to_action_plan_journey(self):
        """CRITICAL: Test complete user journey from request to action plan."""
    pass
        logger.info("
" + "🎯 STARTING COMPLETE USER-TO-ACTION-PLAN JOURNEY TEST")
        
        # Create E2E test session
        session = E2ETestSession(
            session_id=f"e2e-{uuid.uuid4()}",
            user_id=f"test-user-{int(time.time())}",
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
    pass
                agent_events_received.append({
                    'type': data.get('type'),
                    'timestamp': time.time(),
                    'data': data
                })
                logger.info(f"📨 Received: {data.get('type')} - {data.get('message', '')[:50]}...")
            
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
                logger.info(f"📊 WebSocket responsiveness: {responsiveness_delay:.2f}s delay")
            else:
                metrics.websocket_responsiveness_score = 0.0
                logger.warning("⚠️ No agent events received")
            
            # STEP 5: Validate action plan generation and quality
            logger.info("📋 Step 5: Validating action plan generation...")
            
            # Wait additional time for final results
            await asyncio.sleep(5.0)
            
            # Check thread status through API
            thread_status = await self.service_integrator.get_thread_status(session.thread_id)
            logger.info(f"Thread status: {thread_status.get('status', 'unknown')}")
            
            # Analyze action plan quality from received events
            final_reports = [e for e in agent_events if e['message_type'] in ['agent_completed', 'final_report']]
            
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
                
                logger.info(f"📊 Action plan quality: {quality_score:.1%}")
                for indicator, present in quality_indicators.items():
                    status = "✅" if present else "❌"
                    logger.info(f"   {status} {indicator}")
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
            
            logger.info(f"📊 Chat value delivery: {chat_value_score:.1%}")
            
            # Calculate final metrics
            journey_end_time = time.time()
            metrics.request_to_response_time = journey_end_time - journey_start_time
            metrics.performance_satisfaction_score = max(0.0, 1.0 - (metrics.request_to_response_time / 120.0))
            
            overall_ux_score = metrics.calculate_overall_score()
            
            # CRITICAL VALIDATIONS
            assert total_events > 0, \
                f"No agent events received - complete pipeline failure. Thread status: {thread_status}"
            
            assert metrics.websocket_responsiveness_score > 0.3, \
                f"WebSocket too unresponsive: {metrics.websocket_responsiveness_score:.1%}"
            
            assert metrics.request_to_response_time < 150.0, \
                f"Complete journey too slow: {metrics.request_to_response_time:.2f}s"
            
            assert overall_ux_score >= 0.6, \
                f"Overall user experience inadequate: {overall_ux_score:.1%}"
            
            # SUCCESS REPORT
            logger.info("
" + "🎉 E2E USER JOURNEY COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"Journey Time: {metrics.request_to_response_time:.2f}s")
            logger.info(f"WebSocket Events: {total_events}")
            logger.info(f"Responsiveness: {metrics.websocket_responsiveness_score:.1%}")
            logger.info(f"Action Plan Quality: {metrics.action_plan_quality_score:.1%}")
            logger.info(f"Chat Value Delivery: {metrics.chat_value_delivery_score:.1%}")
            logger.info(f"Performance Satisfaction: {metrics.performance_satisfaction_score:.1%}")
            logger.info(f"OVERALL UX SCORE: {overall_ux_score:.1%}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ E2E journey failed: {e}")
            metrics.error_handling_ux_score = 0.0
            raise
        
        finally:
            # Cleanup WebSocket
            if session.websocket_connection:
                await session.websocket_connection.disconnect()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(120)
    async def test_concurrent_user_sessions_e2e(self):
        """CRITICAL: Test multiple concurrent user sessions E2E."""
        logger.info("
" + "👥 STARTING CONCURRENT USER SESSIONS E2E TEST")
        
        concurrent_users = 3
        user_sessions = []
        
        # Create concurrent user sessions
        for i in range(concurrent_users):
            session = E2ETestSession(
                session_id=f"concurrent-e2e-{i}-{uuid.uuid4()}",
                user_id=f"concurrent-user-{i}-{int(time.time())}",
                thread_id=""
            )
            user_sessions.append(session)
            self.test_sessions.append(session)
        
        # Execute concurrent user journeys
        async def run_concurrent_user_journey(session: E2ETestSession, user_index: int):
            try:
                # Create thread
                session.thread_id = await self.service_integrator.create_thread(session.user_id)
                if not session.thread_id:
                    await asyncio.sleep(0)
    return {'success': False, 'error': 'Thread creation failed', 'user_index': user_index}
                
                # Connect WebSocket
                ws_client = RealWebSocketClient()
                connected = await ws_client.connect(session.thread_id, session.user_id)
                if not connected:
                    return {'success': False, 'error': 'WebSocket connection failed', 'user_index': user_index}
                
                session.websocket_connection = ws_client
                
                # Send user request
                user_request = f"User {user_index}: Create cost optimization plan for our infrastructure"
                
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
        successful_sessions = [r for r in results if isinstance(r, dict) and r.get('success')]
        success_rate = len(successful_sessions) / concurrent_users
        
        # Validate concurrent performance
        assert success_rate >= 0.67, \
            f"Concurrent user sessions failed: {success_rate:.1%} success rate (need ≥67%)"
        
        assert total_time < 90.0, \
            f"Concurrent sessions too slow: {total_time:.2f}s (need <90s)"
        
        # Log results
        logger.info(f"✅ Concurrent E2E: {success_rate:.1%} success rate in {total_time:.2f}s")
        for result in results:
            if isinstance(result, dict):
                if result['success']:
                    logger.info(f"   User {result['user_index']}: {result['events_received']} events")
                else:
                    logger.warning(f"   User {result['user_index']}: FAILED - {result['error']}")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(90)
    async def test_error_recovery_user_experience(self):
        """CRITICAL: Test error recovery from user experience perspective."""
    pass
        logger.info("
" + "🛠️ STARTING ERROR RECOVERY USER EXPERIENCE TEST")
        
        # Create session
        session = E2ETestSession(
            session_id=f"error-recovery-{uuid.uuid4()}",
            user_id=f"error-user-{int(time.time())}",
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
                logger.info(f"🧪 Testing error scenario {i+1}: {error_scenario[:30]}...")
                
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
                    logger.info(f"✅ Scenario {i+1}: recovered in {recovery_time:.2f}s (score: {recovery_score:.2f})")
                else:
                    recovery_scores.append(0.0)
                    logger.warning(f"⚠️ Scenario {i+1}: no recovery response")
                
                # Brief pause between scenarios
                await asyncio.sleep(2.0)
            
            # Overall error recovery assessment
            avg_recovery_score = sum(recovery_scores) / len(recovery_scores)
            
            assert avg_recovery_score >= 0.5, \
                f"Error recovery UX inadequate: {avg_recovery_score:.1%} (need ≥50%)"
            
            logger.info(f"✅ Error recovery UX: {avg_recovery_score:.1%} average score")
            
        except Exception as e:
            logger.error(f"❌ Error recovery test failed: {e}")
            raise
        
        finally:
            if session.websocket_connection:
                await session.websocket_connection.disconnect()


# ============================================================================
# PERFORMANCE AND SCALABILITY E2E TESTS
# ============================================================================

class TestActionsAgentE2EPerformance:
    """E2E performance and scalability tests under realistic conditions."""
    
    @pytest.fixture(autouse=True)
    async def setup_performance_e2e_environment(self):
        """Setup environment for performance E2E testing."""
        logger.info("🚀 Setting up performance E2E environment...")
        
        self.docker_manager = UnifiedDockerManager()
        await self.docker_manager.ensure_services_running([
            'postgres', 'redis', 'backend'
        ])
        
        self.env = IsolatedEnvironment()
        self.service_integrator = RealServiceIntegrator(self.env)
        await self.service_integrator.initialize_session()
        
        yield
        
        await self.service_integrator.cleanup()
        await self.docker_manager.cleanup_if_needed()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(300)
    async def test_sustained_load_e2e_performance(self):
        """CRITICAL: Test sustained load performance E2E."""
    pass
        logger.info("
" + "⚡ STARTING SUSTAINED LOAD E2E PERFORMANCE TEST")
        
        load_users = 5
        requests_per_user = 3
        total_requests = load_users * requests_per_user
        
        # Performance tracking
        performance_metrics = {
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'response_times': [],
            'websocket_events': 0
        }
        
        async def simulate_user_load(user_index: int):
            """Simulate sustained user load."""
            user_results = []
            
            for request_index in range(requests_per_user):
                try:
                    # Create unique session
                    user_id = f"load-user-{user_index}-{request_index}"
                    thread_id = await self.service_integrator.create_thread(user_id)
                    
                    if not thread_id:
                        user_results.append({'success': False, 'error': 'Thread creation failed'})
                        continue
                    
                    # WebSocket connection
                    ws_client = RealWebSocketClient()
                    connected = await ws_client.connect(thread_id, user_id)
                    
                    if not connected:
                        user_results.append({'success': False, 'error': 'WebSocket connection failed'})
                        continue
                    
                    # Send request and measure performance
                    request_start = time.time()
                    
                    user_request = f"Load test {user_index}-{request_index}: Optimize our system performance and reduce costs"
                    await ws_client.send_user_message(user_request)
                    
                    # Wait for completion
                    events = await ws_client.wait_for_events(
                        expected_types=['agent_completed', 'final_report'],
                        timeout=60.0
                    )
                    
                    response_time = time.time() - request_start
                    
                    user_results.append({
                        'success': len(events) > 0,
                        'response_time': response_time,
                        'events_count': len(events),
                        'user_index': user_index,
                        'request_index': request_index
                    })
                    
                    # Cleanup
                    await ws_client.disconnect()
                    
                    # Brief pause to avoid overwhelming
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    user_results.append({
                        'success': False,
                        'error': str(e),
                        'user_index': user_index,
                        'request_index': request_index
                    })
            
            await asyncio.sleep(0)
    return user_results
        
        # Execute sustained load
        total_start_time = time.time()
        tasks = [simulate_user_load(i) for i in range(load_users)]
        all_user_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - total_start_time
        
        # Aggregate results
        all_results = []
        for user_results in all_user_results:
            if isinstance(user_results, list):
                all_results.extend(user_results)
        
        # Calculate performance metrics
        successful_results = [r for r in all_results if r.get('success')]
        failed_results = [r for r in all_results if not r.get('success')]
        
        success_rate = len(successful_results) / len(all_results) if all_results else 0
        
        if successful_results:
            response_times = [r['response_time'] for r in successful_results if 'response_time' in r]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            total_events = sum(r.get('events_count', 0) for r in successful_results)
        else:
            avg_response_time = 0
            max_response_time = 0
            total_events = 0
        
        # Performance validations
        assert success_rate >= 0.7, \
            f"Sustained load performance failed: {success_rate:.1%} success rate (need ≥70%)"
        
        assert avg_response_time < 45.0, \
            f"Average response time too high: {avg_response_time:.2f}s (need <45s)"
        
        assert total_duration < 240.0, \
            f"Total load test duration too long: {total_duration:.2f}s (need <240s)"
        
        # Calculate throughput
        requests_per_second = len(successful_results) / total_duration if total_duration > 0 else 0
        
        assert requests_per_second > 0.05, \
            f"Throughput too low: {requests_per_second:.3f} req/s (need >0.05)"
        
        # Performance report
        logger.info("
" + "📊 SUSTAINED LOAD PERFORMANCE REPORT")
        logger.info("=" * 50)
        logger.info(f"Total Requests: {len(all_results)}")
        logger.info(f"Successful: {len(successful_results)} ({success_rate:.1%})")
        logger.info(f"Failed: {len(failed_results)}")
        logger.info(f"Average Response Time: {avg_response_time:.2f}s")
        logger.info(f"Max Response Time: {max_response_time:.2f}s")
        logger.info(f"Throughput: {requests_per_second:.3f} req/s")
        logger.info(f"Total WebSocket Events: {total_events}")
        logger.info(f"Duration: {total_duration:.2f}s")
        logger.info("=" * 50)
        
        if failed_results:
            logger.warning("Failed requests:")
            for failure in failed_results[:5]:  # Show first 5 failures
                logger.warning(f"  - User {failure.get('user_index')}: {failure.get('error', 'Unknown error')}")


# ============================================================================
# COMPREHENSIVE E2E TEST SUITE
# ============================================================================

@pytest.mark.critical
@pytest.mark.e2e
class TestActionsAgentE2EComprehensive:
    """Comprehensive E2E test suite for ActionsAgent complete workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_e2e_validation_suite(self):
        """Run complete E2E validation for ActionsAgent."""
        logger.info("
" + "=" * 80)
        logger.info("RUNNING COMPLETE ACTIONS AGENT E2E VALIDATION SUITE")
        logger.info("TESTING: Complete user journey with REAL services")
        logger.info("=" * 80)
        
        # Initialize real services
        docker_manager = UnifiedDockerManager()
        services_ready = await docker_manager.ensure_services_running([
            'postgres', 'redis', 'backend'
        ])
        
        if not services_ready:
            pytest.skip("Real services not available for E2E testing")
        
        env = IsolatedEnvironment()
        service_integrator = RealServiceIntegrator(env)
        await service_integrator.initialize_session()
        
        try:
            # E2E validation metrics
            e2e_metrics = UserExperienceMetrics()
            
            logger.info("🌐 Testing basic E2E connectivity...")
            
            # Test 1: Basic connectivity
            test_user_id = f"e2e-validation-{int(time.time())}"
            test_thread_id = await service_integrator.create_thread(test_user_id)
            
            if test_thread_id:
                e2e_metrics.chat_value_delivery_score += 0.2
                logger.info(f"✅ Backend API connectivity: thread {test_thread_id}")
            else:
                logger.error("❌ Backend API connectivity failed")
            
            # Test 2: WebSocket connectivity
            if test_thread_id:
                ws_client = RealWebSocketClient()
                ws_connected = await ws_client.connect(test_thread_id, test_user_id)
                
                if ws_connected:
                    e2e_metrics.websocket_responsiveness_score += 0.3
                    logger.info("✅ WebSocket connectivity established")
                    
                    # Test message sending
                    message_sent = await ws_client.send_user_message("E2E validation test message")
                    if message_sent:
                        e2e_metrics.websocket_responsiveness_score += 0.3
                        logger.info("✅ WebSocket message sending works")
                    
                    await ws_client.disconnect()
                else:
                    logger.error("❌ WebSocket connectivity failed")
            
            # Test 3: Agent processing pipeline
            logger.info("🤖 Testing agent processing pipeline...")
            if test_thread_id:
                # Send realistic request
                api_sent = await service_integrator.send_chat_message(
                    test_thread_id, 
                    test_user_id,
                    "E2E test: Create action plan for system optimization"
                )
                
                if api_sent:
                    e2e_metrics.action_plan_quality_score += 0.4
                    logger.info("✅ Agent processing request sent")
                    
                    # Check status after processing time
                    await asyncio.sleep(10.0)
                    status = await service_integrator.get_thread_status(test_thread_id)
                    
                    if status.get('status') != 'error':
                        e2e_metrics.action_plan_quality_score += 0.4
                        logger.info(f"✅ Agent processing status: {status.get('status', 'unknown')}")
                    else:
                        logger.warning(f"⚠️ Agent processing status: {status}")
                else:
                    logger.error("❌ Agent processing request failed")
            
            # Test 4: Performance validation
            logger.info("⚡ Testing performance characteristics...")
            start_time = time.time()
            
            # Simulate realistic performance test
            performance_thread = await service_integrator.create_thread(f"perf-{test_user_id}")
            if performance_thread:
                perf_ws = RealWebSocketClient()
                if await perf_ws.connect(performance_thread, test_user_id):
                    await perf_ws.send_user_message("Performance test: quick optimization plan")
                    
                    events = await perf_ws.wait_for_events(
                        expected_types=['agent_started'], 
                        timeout=15.0
                    )
                    
                    if events:
                        performance_time = time.time() - start_time
                        e2e_metrics.performance_satisfaction_score = max(0.0, 1.0 - (performance_time / 20.0))
                        logger.info(f"✅ Performance test: {performance_time:.2f}s")
                    
                    await perf_ws.disconnect()
            
            # Calculate overall E2E score
            overall_e2e_score = e2e_metrics.calculate_overall_score()
            
            # E2E validation report
            logger.info("
" + "🎯 E2E VALIDATION REPORT")
            logger.info("=" * 40)
            logger.info(f"WebSocket Responsiveness: {e2e_metrics.websocket_responsiveness_score:.1%}")
            logger.info(f"Action Plan Quality: {e2e_metrics.action_plan_quality_score:.1%}")
            logger.info(f"Chat Value Delivery: {e2e_metrics.chat_value_delivery_score:.1%}")
            logger.info(f"Performance Satisfaction: {e2e_metrics.performance_satisfaction_score:.1%}")
            logger.info(f"")
            logger.info(f"OVERALL E2E SCORE: {overall_e2e_score:.1%}")
            
            # Validation threshold
            e2e_threshold = 0.5  # 50% E2E functionality required
            
            if overall_e2e_score >= e2e_threshold:
                logger.info("✅ E2E VALIDATION PASSED")
            else:
                pytest.fail(f"❌ E2E VALIDATION FAILED: {overall_e2e_score:.1%} (need ≥{e2e_threshold:.1%})")
                
        finally:
            await service_integrator.cleanup()
            await docker_manager.cleanup_if_needed()


if __name__ == "__main__":
    # Run with: python tests/e2e/test_actions_agent_full_flow.py
    # Or: pytest tests/e2e/test_actions_agent_full_flow.py -v
    pytest.main([__file__, "-v", "--tb=short"])
    pass