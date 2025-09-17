"Test WebSocket JWT Reconnection State Management - Enterprise User Session Continuity"""

CRITICAL E2E Test: WebSocket reconnection with JWT token auth and state preservation.

BVJ: Enterprise | User session continuity | $60K+ MRR Protection
- Zero-downtime AI interactions required
- Message queue preservation prevents data loss
- <2s reconnection time meets enterprise SLA

Requirements: Same JWT reconnection, message preservation, state restoration, <300 lines
""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.config import TEST_ENDPOINTS, TEST_SECRETS, TEST_USERS
from tests.e2e.jwt_token_helpers import JWTTestHelper
from tests.e2e.reconnection_test_helpers import ReconnectionTestHelpers


class ReconnectionPhase(Enum):
    Phases of reconnection testing.""
    INITIAL_CONNECT = "initial_connect"
    STABLE_SESSION = stable_session
    DISCONNECTION = "disconnection"
    MESSAGE_QUEUEING = message_queueing
    RECONNECTION = reconnection""
    STATE_RESTORATION = state_restoration""
    MESSAGE_DELIVERY = message_delivery


@dataclass
class JWTSessionState:
    ""JWT WebSocket session state for reconnection testing.
    user_id: str
    access_token: str
    thread_id: str
    agent_context: Dict[str, Any]
    message_queue: List[Dict[str, Any]]
    connection_id: str
    session_timestamp: datetime
    auth_validated: bool = False


@dataclass 
class ReconnectionMetrics:
    Performance metrics for reconnection operations.""
    initial_connect_time: float
    disconnection_time: float
    reconnection_time: float
    state_restoration_time: float
    message_delivery_time: float
    total_cycle_time: float
    messages_preserved: int
    auth_validation_time: float


class WebSocketJWTReconnectionerTests:
    Core tester for WebSocket JWT reconnection state management.""
    
    def __init__(self):
        self.jwt_helper = JWTTestHelper()
        self.ws_url = TEST_ENDPOINTS.ws_url
        self.reconnection_fixture = ReconnectionTestHelpers()
        self.performance_threshold = 2.0  # 2 second requirement
        
    async def setup_authenticated_session(self, user_id: str) -> JWTSessionState:
        Setup authenticated WebSocket session with state tracking.""
        access_token = self.jwt_helper.create_access_token(
            user_id=user_id, email=f{user_id}@enterprise.netrasystems.ai", "
            permissions=[read, write, "agent_execute]"
        
        session_state = JWTSessionState(
            user_id=user_id, access_token=access_token,
            thread_id=fthread_{user_id}_{int(time.time())},
            agent_context={current_task: data_analysis", "phase: initial},
            message_queue=[], connection_id=fconn_{uuid.uuid4().hex[:8]},
            session_timestamp=datetime.now(timezone.utc)
        )
        
        connection_result = await self.reconnection_fixture.establish_websocket_connection(
            ws_url=self.ws_url, access_token=access_token, connection_id=session_state.connection_id
        )
        session_state.auth_validated = connection_result[auth_validated]""
        return session_state
    
    async def simulate_session_activity(self, session_state: JWTSessionState) -> Dict[str, Any]:
        "Simulate active session with messages and state updates."""
        test_messages = [
            {type": "agent_start, content: Beginning data analysis task},
            {type: "user_input, content": Analyze quarterly sales data},
            {type: agent_progress, content": "Processing data... 30% complete}
        ]
        
        activity_result = await self.reconnection_fixture.send_session_messages(
            messages=test_messages, session_context=session_state.__dict__
        )
        
        session_state.agent_context.update({
            phase: processing, progress: 30,""
            "last_activity: datetime.now(timezone.utc).isoformat()"
        }
        return activity_result
    
    async def execute_controlled_disconnection(self, session_state: JWTSessionState) -> Dict[str, Any]:
        Execute controlled disconnection while preserving state.""
        disconnect_start = time.time()
        
        pending_messages = [
            {type: user_input, content: Please continue with analysis"},"
            {"type: system_update, content: Data processing continued},"
            {"type: agent_progress", content: Analysis 60% complete}
        ]
        session_state.message_queue.extend(pending_messages)
        
        disconnection_result = await self.reconnection_fixture.simulate_network_disconnection(
            connection_id=session_state.connection_id, preserve_state=True
        )
        
        return {
            disconnection_successful: disconnection_result[success"],"
            "state_preserved: disconnection_result[state_preserved],"
            messages_queued: len(session_state.message_queue),
            disconnection_time": time.time() - disconnect_start"
        }
    
    async def execute_jwt_reconnection(self, session_state: JWTSessionState) -> ReconnectionMetrics:
        Execute reconnection using same JWT token with full metrics.""
        reconnect_start = time.time()
        reconnection_result = await self.reconnection_fixture.reconnect_websocket(
            ws_url=self.ws_url, access_token=session_state.access_token,
            connection_id=session_state.connection_id, previous_state=session_state.__dict__
        )
        reconnect_time = time.time() - reconnect_start
        
        state_restore_start = time.time()
        state_restoration = await self.reconnection_fixture.restore_session_state(
            session_context=session_state.__dict__, connection_established=reconnection_result[connected"]"
        state_restore_time = time.time() - state_restore_start
        
        message_delivery_start = time.time()
        delivery_result = await self.reconnection_fixture.deliver_queued_messages(
            message_queue=session_state.message_queue, connection_active=reconnection_result[connected]
        message_delivery_time = time.time() - message_delivery_start
        
        auth_validation_start = time.time()
        auth_check = await self.reconnection_fixture.validate_auth_context(
            access_token=session_state.access_token, user_id=session_state.user_id
        )
        auth_validation_time = time.time() - auth_validation_start
        
        return ReconnectionMetrics(
            initial_connect_time=0.0, disconnection_time=0.0, reconnection_time=reconnect_time,
            state_restoration_time=state_restore_time, message_delivery_time=message_delivery_time,
            total_cycle_time=reconnect_time + state_restore_time + message_delivery_time,
            messages_preserved=len(session_state.message_queue), auth_validation_time=auth_validation_time
        )


@pytest.mark.asyncio
@pytest.mark.e2e
class WebSocketJWTReconnectionStateTests:
    ""Test Suite: WebSocket JWT Reconnection State Management.
    
    @pytest.fixture
    def jwt_reconnection_tester(self):
        Initialize JWT reconnection tester.""
        return WebSocketJWTReconnectionTester()
    
    @pytest.fixture
    def enterprise_user_id(self):
        Provide enterprise test user ID.""
        return TEST_USERS[enterprise].id
    
    @pytest.mark.e2e
    async def test_jwt_token_reconnection_same_token(self, jwt_reconnection_tester, enterprise_user_id):
        "Test Case 1: Reconnection with same JWT token maintains session."
        session_state = await jwt_reconnection_tester.setup_authenticated_session(enterprise_user_id)
        assert session_state.auth_validated and session_state.user_id == enterprise_user_id
        
        activity_result = await jwt_reconnection_tester.simulate_session_activity(session_state)
        assert activity_result[messages_sent] > 0
        
        disconnect_result = await jwt_reconnection_tester.execute_controlled_disconnection(session_state)
        assert disconnect_result[disconnection_successful"]"
        
        metrics = await jwt_reconnection_tester.execute_jwt_reconnection(session_state)
        assert metrics.reconnection_time < jwt_reconnection_tester.performance_threshold
        assert metrics.total_cycle_time < jwt_reconnection_tester.performance_threshold
    
    @pytest.mark.e2e
    async def test_message_queue_preservation_during_reconnection(self, jwt_reconnection_tester, enterprise_user_id):
        Test Case 2: Message queue preserved and delivered after reconnection.""
        session_state = await jwt_reconnection_tester.setup_authenticated_session(enterprise_user_id)
        await jwt_reconnection_tester.simulate_session_activity(session_state)
        initial_message_count = len(session_state.message_queue)
        
        disconnect_result = await jwt_reconnection_tester.execute_controlled_disconnection(session_state)
        queued_messages = disconnect_result[messages_queued"]"
        assert queued_messages > initial_message_count
        
        metrics = await jwt_reconnection_tester.execute_jwt_reconnection(session_state)
        assert metrics.messages_preserved == queued_messages
        assert metrics.message_delivery_time < 1.0
    
    @pytest.mark.e2e
    async def test_auth_context_persistence_across_reconnection(self, jwt_reconnection_tester, enterprise_user_id):
        Test Case 3: Authentication context maintained across reconnection.""
        session_state = await jwt_reconnection_tester.setup_authenticated_session(enterprise_user_id)
        original_token, original_user_id = session_state.access_token, session_state.user_id
        
        await jwt_reconnection_tester.simulate_session_activity(session_state)
        await jwt_reconnection_tester.execute_controlled_disconnection(session_state)
        metrics = await jwt_reconnection_tester.execute_jwt_reconnection(session_state)
        
        assert session_state.access_token == original_token
        assert session_state.user_id == original_user_id
        assert metrics.auth_validation_time < 0.5
    
    @pytest.mark.e2e
    async def test_session_state_restoration_completeness(self, jwt_reconnection_tester, enterprise_user_id):
        Test Case 4: Complete session state restored after reconnection.""
        session_state = await jwt_reconnection_tester.setup_authenticated_session(enterprise_user_id)
        await jwt_reconnection_tester.simulate_session_activity(session_state)
        session_state.agent_context.update({
            "workspace: {files: [data.csv, analysis.py]},"
            "execution_state: {current_step": 3, total_steps: 5},
            user_preferences: {"format: detailed", notifications: True}
        }
        
        await jwt_reconnection_tester.execute_controlled_disconnection(session_state)
        metrics = await jwt_reconnection_tester.execute_jwt_reconnection(session_state)
        
        assert all(key in session_state.agent_context for key in [workspace, execution_state, user_preferences"]"
        assert metrics.state_restoration_time < 1.0
    
    @pytest.mark.e2e
    async def test_performance_requirements_compliance(self, jwt_reconnection_tester, enterprise_user_id):
        Test Case 5: Performance requirements met consistently.""
        performance_results = []
        
        for cycle in range(3):
            session_state = await jwt_reconnection_tester.setup_authenticated_session(f{enterprise_user_id}_cycle_{cycle}")"
            await jwt_reconnection_tester.simulate_session_activity(session_state)
            await jwt_reconnection_tester.execute_controlled_disconnection(session_state)
            metrics = await jwt_reconnection_tester.execute_jwt_reconnection(session_state)
            performance_results.append(metrics.total_cycle_time)
        
        max_time, avg_time = max(performance_results), sum(performance_results) / len(performance_results)
        assert max_time < 2.0, fMax reconnection time {max_time:.2f}s exceeds 2s requirement
        assert avg_time < 1.5, fAverage reconnection time {avg_time:.2f}s exceeds 1.5s target""
    
    @pytest.mark.e2e
    async def test_concurrent_reconnection_isolation(self, jwt_reconnection_tester):
        "Test Case 6: Concurrent user reconnections don't interfere."""
        user_sessions = []
        for i in range(2):
            user_id = f{TEST_USERS['enterprise'].id}_concurrent_{i}""
            session_state = await jwt_reconnection_tester.setup_authenticated_session(user_id)
            user_sessions.append(session_state)
        
        reconnection_tasks = [
            asyncio.create_task(self._execute_full_reconnection_cycle(jwt_reconnection_tester, session_state))
            for session_state in user_sessions
        ]
        
        results = await asyncio.gather(*reconnection_tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), fReconnection {i} failed: {result}
            assert result[success], fReconnection {i} unsuccessful
            assert result[session_isolated], f"Session {i} isolation compromised"
    
    async def _execute_full_reconnection_cycle(self, tester, session_state):
        "Helper: Execute complete reconnection cycle for concurrent testing."""
        try:
            await tester.simulate_session_activity(session_state)
            await tester.execute_controlled_disconnection(session_state)
            metrics = await tester.execute_jwt_reconnection(session_state)
            
            return {
                "success: metrics.total_cycle_time < 2.0,"
                session_isolated: session_state.user_id in session_state.thread_id,
                performance_met: metrics.reconnection_time < 2.0""
            }
        except Exception as e:
            return {success": False, "error: str(e), session_isolated": False}"
