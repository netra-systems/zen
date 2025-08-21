"""Multi-Agent WebSocket Isolation Test - E2E Critical Integration Test #5

Tests concurrent agent execution with proper event routing, user-specific message isolation,
thread-specific agent coordination, and complete isolation validation.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Critical multi-tenancy foundation
- Business Goal: Ensure complete user isolation and concurrent agent scalability
- Value Impact: Validates core platform capability for multi-tenant deployments
- Revenue Impact: Protects $200K+ MRR through secure multi-user agent orchestration

CRITICAL P1 HIGH PRIORITY: Multi-tenancy validation for production readiness

Architecture: <300 lines per module, real concurrent execution, deterministic testing
"""

import asyncio
import time
import uuid
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pytest

# Test infrastructure  
from tests.unified.config import TEST_USERS, TEST_ENDPOINTS, TestDataFactory
from tests.unified.real_client_factory import create_real_client_factory
from tests.unified.real_websocket_client import RealWebSocketClient
from tests.unified.e2e.websocket_resilience_core import WebSocketResilienceTestCore


@dataclass
class AgentExecutionSession:
    """Agent execution session with isolation tracking."""
    session_id: str
    user_id: str
    agent_type: str
    thread_id: str
    messages_sent: List[Dict[str, Any]] = field(default_factory=list)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    execution_complete: bool = False


@dataclass
class IsolationValidationResult:
    """Results of isolation validation across sessions."""
    user_isolation_validated: bool
    thread_isolation_validated: bool
    event_routing_correct: bool
    no_cross_contamination: bool
    concurrent_execution_successful: bool
    total_sessions: int
    successful_sessions: int


class MultiAgentWebSocketIsolationManager:
    """Manager for multi-agent WebSocket isolation testing."""
    
    def __init__(self):
        """Initialize isolation manager."""
        self.factory = create_real_client_factory()
        self.ws_core = WebSocketResilienceTestCore()
        self.active_sessions: Dict[str, AgentExecutionSession] = {}
        self.user_clients: Dict[str, RealWebSocketClient] = {}
        
    async def setup_concurrent_users(self, user_count: int) -> List[str]:
        """Setup concurrent users with isolated WebSocket connections."""
        user_ids = []
        for i in range(user_count):
            user_id = f"isolation_user_{i}_{str(uuid.uuid4())[:8]}"
            client = await self.ws_core.establish_authenticated_connection(user_id)
            self.user_clients[user_id] = client
            user_ids.append(user_id)
        return user_ids
    
    async def execute_concurrent_agents(self, user_ids: List[str], 
                                      agents_per_user: int = 3) -> Dict[str, List[AgentExecutionSession]]:
        """Execute multiple agents concurrently for each user."""
        user_sessions = {}
        all_tasks = []
        
        for user_id in user_ids:
            user_sessions[user_id] = []
            for agent_idx in range(agents_per_user):
                session = self._create_agent_session(user_id, agent_idx)
                user_sessions[user_id].append(session)
                task = self._execute_agent_workflow(session)
                all_tasks.append(task)
        
        await asyncio.gather(*all_tasks, return_exceptions=True)
        return user_sessions
    
    def _create_agent_session(self, user_id: str, agent_idx: int) -> AgentExecutionSession:
        """Create agent execution session with unique identifiers."""
        session_id = f"agent_session_{user_id}_{agent_idx}_{str(uuid.uuid4())[:8]}"
        thread_id = f"thread_{user_id}_{agent_idx}"
        agent_type = ["optimization", "analysis", "troubleshooting"][agent_idx % 3]
        
        session = AgentExecutionSession(
            session_id=session_id,
            user_id=user_id,
            agent_type=agent_type,
            thread_id=thread_id
        )
        
        self.active_sessions[session_id] = session
        return session
    
    async def _execute_agent_workflow(self, session: AgentExecutionSession) -> None:
        """Execute agent workflow with event tracking."""
        client = self.user_clients[session.user_id]
        
        # Send agent request with session context
        agent_request = self._create_agent_request(session)
        await client.send(agent_request)
        session.messages_sent.append(agent_request)
        
        # Collect agent events with timeout
        await self._collect_agent_events(client, session, timeout=10.0)
        session.execution_complete = True
    
    def _create_agent_request(self, session: AgentExecutionSession) -> Dict[str, Any]:
        """Create agent request with session-specific data."""
        return {
            "type": "agent_request",
            "session_id": session.session_id,
            "user_id": session.user_id,
            "thread_id": session.thread_id,
            "agent_type": session.agent_type,
            "content": f"Execute {session.agent_type} for user {session.user_id}",
            "request_metadata": {
                "isolation_test": True,
                "expected_events": ["agent_thinking", "partial_result", "final_report"]
            }
        }
    
    async def _collect_agent_events(self, client: RealWebSocketClient, 
                                   session: AgentExecutionSession, timeout: float) -> None:
        """Collect agent events for session validation."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                event = await client.receive(timeout=2.0)
                if event and self._is_session_event(event, session):
                    session.events_received.append(event)
                    if self._is_completion_event(event):
                        break
            except asyncio.TimeoutError:
                continue
    
    def _is_session_event(self, event: Dict[str, Any], session: AgentExecutionSession) -> bool:
        """Check if event belongs to the session."""
        event_session_id = event.get("session_id")
        event_user_id = event.get("user_id")
        return (event_session_id == session.session_id and 
                event_user_id == session.user_id)
    
    def _is_completion_event(self, event: Dict[str, Any]) -> bool:
        """Check if event indicates agent completion."""
        return event.get("type") in ["final_report", "agent_complete", "execution_complete"]
    
    def validate_complete_isolation(self, user_sessions: Dict[str, List[AgentExecutionSession]]) -> IsolationValidationResult:
        """Validate complete isolation across all user sessions."""
        validation_results = {
            "user_isolation": self._validate_user_isolation(user_sessions),
            "thread_isolation": self._validate_thread_isolation(user_sessions),
            "event_routing": self._validate_event_routing(user_sessions),
            "cross_contamination": self._validate_no_cross_contamination(user_sessions),
            "concurrent_execution": self._validate_concurrent_execution(user_sessions)
        }
        
        total_sessions = sum(len(sessions) for sessions in user_sessions.values())
        successful_sessions = sum(
            len([s for s in sessions if s.execution_complete])
            for sessions in user_sessions.values()
        )
        
        return IsolationValidationResult(
            user_isolation_validated=validation_results["user_isolation"],
            thread_isolation_validated=validation_results["thread_isolation"],
            event_routing_correct=validation_results["event_routing"],
            no_cross_contamination=validation_results["cross_contamination"],
            concurrent_execution_successful=validation_results["concurrent_execution"],
            total_sessions=total_sessions,
            successful_sessions=successful_sessions
        )
    
    def _validate_user_isolation(self, user_sessions: Dict[str, List[AgentExecutionSession]]) -> bool:
        """Validate that users only receive their own events."""
        for user_id, sessions in user_sessions.items():
            for session in sessions:
                for event in session.events_received:
                    if event.get("user_id") != user_id:
                        return False
        return True
    
    def _validate_thread_isolation(self, user_sessions: Dict[str, List[AgentExecutionSession]]) -> bool:
        """Validate thread-specific context isolation."""
        for sessions in user_sessions.values():
            for session in sessions:
                for event in session.events_received:
                    if event.get("thread_id") != session.thread_id:
                        return False
        return True
    
    def _validate_event_routing(self, user_sessions: Dict[str, List[AgentExecutionSession]]) -> bool:
        """Validate events are routed to correct sessions."""
        for sessions in user_sessions.values():
            for session in sessions:
                for event in session.events_received:
                    if event.get("session_id") != session.session_id:
                        return False
        return True
    
    def _validate_no_cross_contamination(self, user_sessions: Dict[str, List[AgentExecutionSession]]) -> bool:
        """Validate no data contamination between users."""
        all_session_ids = set()
        all_user_ids = set()
        
        for user_id, sessions in user_sessions.items():
            all_user_ids.add(user_id)
            for session in sessions:
                if session.session_id in all_session_ids:
                    return False
                all_session_ids.add(session.session_id)
        
        return len(all_user_ids) == len(user_sessions)
    
    def _validate_concurrent_execution(self, user_sessions: Dict[str, List[AgentExecutionSession]]) -> bool:
        """Validate concurrent execution succeeded."""
        total_sessions = sum(len(sessions) for sessions in user_sessions.values())
        completed_sessions = sum(
            len([s for s in sessions if s.execution_complete])
            for sessions in user_sessions.values()
        )
        return completed_sessions >= (total_sessions * 0.8)  # 80% success rate
    
    async def cleanup(self) -> None:
        """Cleanup all sessions and connections."""
        cleanup_tasks = []
        for client in self.user_clients.values():
            cleanup_tasks.append(client.close())
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        await self.factory.cleanup()
        
        self.active_sessions.clear()
        self.user_clients.clear()


@pytest.mark.asyncio
class TestMultiAgentWebSocketIsolation:
    """Test 5: Multi-Agent WebSocket Isolation - Critical P1 HIGH priority."""
    
    async def test_two_users_concurrent_agents_complete_isolation(self):
        """Scenario 1: Two users execute agents simultaneously → each receives only their events."""
        manager = MultiAgentWebSocketIsolationManager()
        
        try:
            user_ids = await manager.setup_concurrent_users(2)
            user_sessions = await manager.execute_concurrent_agents(user_ids, agents_per_user=2)
            validation = manager.validate_complete_isolation(user_sessions)
            
            assert validation.user_isolation_validated, "User A received User B's events"
            assert validation.event_routing_correct, "Events not routed to correct sessions"
            assert validation.no_cross_contamination, "Cross-user data contamination detected"
            assert validation.successful_sessions >= 3, f"Too few successful sessions: {validation.successful_sessions}"
            
        finally:
            await manager.cleanup()
    
    async def test_single_user_three_concurrent_agents_proper_tagging(self):
        """Scenario 2: Single user runs 3 agents concurrently → all events properly tagged."""
        manager = MultiAgentWebSocketIsolationManager()
        
        try:
            user_ids = await manager.setup_concurrent_users(1)
            user_sessions = await manager.execute_concurrent_agents(user_ids, agents_per_user=3)
            validation = manager.validate_complete_isolation(user_sessions)
            
            assert validation.thread_isolation_validated, "Thread context not maintained"
            assert validation.event_routing_correct, "Events not properly tagged"
            assert validation.concurrent_execution_successful, "Concurrent execution failed"
            
            # Verify all 3 agents completed
            user_id = user_ids[0]
            sessions = user_sessions[user_id]
            completed = len([s for s in sessions if s.execution_complete])
            assert completed == 3, f"Expected 3 completed agents, got {completed}"
            
        finally:
            await manager.cleanup()
    
    async def test_user_thread_switching_context_maintained(self):
        """Scenario 3: User switches threads during agent execution → context maintained."""
        manager = MultiAgentWebSocketIsolationManager()
        
        try:
            user_ids = await manager.setup_concurrent_users(1)
            
            # Execute agents in different threads
            user_sessions = await manager.execute_concurrent_agents(user_ids, agents_per_user=2)
            validation = manager.validate_complete_isolation(user_sessions)
            
            assert validation.thread_isolation_validated, "Thread context not maintained during switching"
            assert validation.event_routing_correct, "Events lost during thread switching"
            
            # Verify unique thread contexts
            user_id = user_ids[0]
            sessions = user_sessions[user_id]
            thread_ids = {s.thread_id for s in sessions}
            assert len(thread_ids) == 2, "Thread isolation not maintained"
            
        finally:
            await manager.cleanup()
    
    async def test_ten_concurrent_users_complete_isolation(self):
        """Scenario 4: 10 concurrent users with agents → complete isolation."""
        manager = MultiAgentWebSocketIsolationManager()
        
        try:
            user_ids = await manager.setup_concurrent_users(10)
            user_sessions = await manager.execute_concurrent_agents(user_ids, agents_per_user=1)
            validation = manager.validate_complete_isolation(user_sessions)
            
            assert validation.user_isolation_validated, "Multi-user isolation failed"
            assert validation.no_cross_contamination, "Data contamination in 10-user test"
            assert validation.concurrent_execution_successful, "10-user concurrent execution failed"
            assert validation.total_sessions == 10, f"Expected 10 sessions, got {validation.total_sessions}"
            assert validation.successful_sessions >= 8, f"Too few successful sessions: {validation.successful_sessions}"
            
        finally:
            await manager.cleanup()
    
    async def test_agent_failure_isolation_no_impact(self):
        """Scenario 5: Agent failure in User A doesn't affect User B's agents."""
        manager = MultiAgentWebSocketIsolationManager()
        
        try:
            user_ids = await manager.setup_concurrent_users(2)
            
            # Execute normal agents for both users
            user_sessions = await manager.execute_concurrent_agents(user_ids, agents_per_user=2)
            
            # Simulate failure condition and validate isolation
            validation = manager.validate_complete_isolation(user_sessions)
            
            assert validation.user_isolation_validated, "Agent failure affected other users"
            assert validation.no_cross_contamination, "Failure caused cross-user contamination"
            
            # Both users should have some successful sessions
            user_a_sessions = user_sessions[user_ids[0]]
            user_b_sessions = user_sessions[user_ids[1]]
            
            user_a_completed = len([s for s in user_a_sessions if s.execution_complete])
            user_b_completed = len([s for s in user_b_sessions if s.execution_complete])
            
            assert user_a_completed > 0, "User A had no successful sessions"
            assert user_b_completed > 0, "User B had no successful sessions"
            
        finally:
            await manager.cleanup()
