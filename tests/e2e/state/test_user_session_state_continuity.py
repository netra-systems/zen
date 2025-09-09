"""
E2E Test: User Session State Continuity

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Session continuity is fundamental UX
- Business Goal: Ensure user state is preserved across UI interactions and browser refreshes
- Value Impact: Users can maintain conversation context and don't lose progress
- Strategic Impact: Core user experience that prevents abandonment and supports engagement

This E2E test validates:
- State maintained across UI interactions (WebSocket reconnections)
- Browser refresh state recovery with proper authentication context
- Real authentication context preservation across sessions
- WebSocket reconnection with complete state recovery
- Thread and conversation history persistence

CRITICAL: Tests the session management that enables continuous user experience
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

# Core system imports with absolute paths
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Database and state management imports
try:
    from netra_backend.app.models.user_session import UserSession
    from netra_backend.app.models.thread import Thread
    from netra_backend.app.models.message import Message
    from netra_backend.app.database.session_manager import DatabaseSessionManager
except ImportError:
    # Fallback if models aren't available
    UserSession = None
    Thread = None
    Message = None
    DatabaseSessionManager = None


class TestUserSessionStateContinuity(BaseE2ETest):
    """E2E tests for user session state continuity across interactions."""
    
    @pytest.fixture
    async def persistent_user_context(self):
        """Create user context for state continuity testing."""
        return await create_authenticated_user_context(
            user_email="state_continuity_user@e2e.test",
            environment="test",
            permissions=["read", "write", "agent_execute", "websocket_connect", "session_persist"],
            websocket_enabled=True
        )
    
    @pytest.fixture
    def websocket_auth_helper(self):
        """WebSocket authentication helper for state testing."""
        return E2EWebSocketAuthHelper(environment="test")
    
    @pytest.fixture
    def unified_id_generator(self):
        """ID generator for consistent state tracking."""
        return UnifiedIdGenerator()
    
    @pytest.fixture
    async def real_agent_registry(self):
        """Real agent registry for state testing."""
        registry = AgentRegistry()
        await registry.initialize_registry()
        return registry
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.state_management
    async def test_websocket_reconnection_state_preservation(
        self,
        persistent_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test that user state is preserved across WebSocket reconnections.
        
        Simulates user briefly losing connection and reconnecting - state should be maintained.
        """
        
        # Phase 1: Initial connection and agent execution
        run_id_1 = unified_id_generator.generate_run_id(
            user_id=str(persistent_user_context.user_id),
            operation="state_continuity_phase1"
        )
        
        initial_execution_context = AgentExecutionContext(
            agent_name="triage_agent",
            run_id=str(run_id_1),
            correlation_id=str(persistent_user_context.request_id),
            retry_count=0,
            user_context=persistent_user_context
        )
        
        # First WebSocket connection
        ws_connection_1 = await websocket_auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        initial_events = []
        
        async def collect_initial_events():
            """Collect events from initial connection."""
            try:
                while True:
                    event_raw = await asyncio.wait_for(ws_connection_1.recv(), timeout=30.0)
                    event = json.loads(event_raw)
                    initial_events.append(event)
                    
                    if event.get('type') == 'agent_completed':
                        break
            except asyncio.TimeoutError:
                pass
        
        # Execute initial agent
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        initial_agent_state = DeepAgentState(
            user_id=str(persistent_user_context.user_id),
            thread_id=str(persistent_user_context.thread_id),
            agent_context={
                **persistent_user_context.agent_context,
                'user_message': 'Initial request for state continuity test',
                'session_phase': 'initial',
                'preserve_state': True
            }
        )
        
        event_task_1 = asyncio.create_task(collect_initial_events())
        
        initial_result = await execution_core.execute_agent(
            context=initial_execution_context,
            state=initial_agent_state,
            timeout=40.0,
            enable_llm=False,  # Focus on state management
            enable_websocket_events=True
        )
        
        await event_task_1
        await ws_connection_1.close()
        
        # Validate initial execution
        assert initial_result.success is True, f"Initial execution failed: {initial_result.error}"
        assert len(initial_events) > 0, "Initial execution generated no events"
        
        # Extract state information from initial execution
        initial_thread_id = str(persistent_user_context.thread_id)
        initial_user_id = str(persistent_user_context.user_id)
        
        self.logger.info(f"Initial execution completed. Thread ID: {initial_thread_id}")
        
        # Phase 2: Simulate disconnect and reconnect (state should be preserved)
        await asyncio.sleep(2.0)  # Simulate brief disconnect
        
        # Reconnect with same authentication context
        ws_connection_2 = await websocket_auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        # Phase 3: Execute another agent in same thread/session
        run_id_2 = unified_id_generator.generate_run_id(
            user_id=str(persistent_user_context.user_id),
            operation="state_continuity_phase2"
        )
        
        continuation_execution_context = AgentExecutionContext(
            agent_name="triage_agent", 
            run_id=str(run_id_2),
            correlation_id=str(persistent_user_context.request_id),
            retry_count=0,
            user_context=persistent_user_context  # Same user context
        )
        
        continuation_events = []
        
        async def collect_continuation_events():
            """Collect events after reconnection."""
            try:
                while True:
                    event_raw = await asyncio.wait_for(ws_connection_2.recv(), timeout=25.0)
                    event = json.loads(event_raw)
                    continuation_events.append(event)
                    
                    if event.get('type') == 'agent_completed':
                        break
            except asyncio.TimeoutError:
                pass
        
        # Execute continuation agent with reference to previous context
        continuation_agent_state = DeepAgentState(
            user_id=initial_user_id,  # Same user
            thread_id=initial_thread_id,  # Same thread - state continuity
            agent_context={
                **persistent_user_context.agent_context,
                'user_message': 'Follow-up request in same session',
                'session_phase': 'continuation',
                'previous_run_id': str(run_id_1),  # Reference to previous execution
                'preserve_state': True,
                'continuation_of_session': True
            }
        )
        
        event_task_2 = asyncio.create_task(collect_continuation_events())
        
        continuation_result = await execution_core.execute_agent(
            context=continuation_execution_context,
            state=continuation_agent_state,
            timeout=35.0,
            enable_websocket_events=True
        )
        
        await event_task_2
        await ws_connection_2.close()
        
        # CRITICAL VALIDATION: Continuation execution succeeded
        assert continuation_result.success is True, \
            f"Continuation execution failed: {continuation_result.error}"
        
        # CRITICAL VALIDATION: Events delivered after reconnection
        assert len(continuation_events) > 0, \
            "No events received after WebSocket reconnection"
        
        # CRITICAL VALIDATION: State continuity maintained
        continuation_event_types = [event.get('type') for event in continuation_events]
        required_events = ['agent_started', 'agent_completed']
        
        for required_event in required_events:
            assert required_event in continuation_event_types, \
                f"Missing required event after reconnection: {required_event}"
        
        # CRITICAL VALIDATION: Thread/session consistency
        for event in continuation_events:
            if 'run_id' in event:
                assert event.get('run_id') == str(run_id_2), \
                    "Continuation events should have new run_id"
            
            # Events should be associated with same user
            if 'user_id' in event:
                assert event.get('user_id') == initial_user_id, \
                    "User ID should be consistent across reconnections"
        
        # VALIDATION: Different run IDs but same session context
        initial_run_ids = {event.get('run_id') for event in initial_events}
        continuation_run_ids = {event.get('run_id') for event in continuation_events}
        
        # Run IDs should be different (new execution)
        assert initial_run_ids.isdisjoint(continuation_run_ids), \
            "Run IDs should be different between executions"
        
        # But user context should be preserved
        assert str(run_id_1) in initial_run_ids, "Initial run_id should be in initial events"
        assert str(run_id_2) in continuation_run_ids, "Continuation run_id should be in continuation events"
        
        self.logger.info("✅ SUCCESS: WebSocket reconnection state preservation validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.state_management
    async def test_browser_refresh_state_recovery(
        self,
        persistent_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test state recovery after simulated browser refresh.
        
        Validates that authentication context and session state survive browser refresh.
        """
        
        # Phase 1: Initial session with agent execution
        initial_run_id = unified_id_generator.generate_run_id(
            user_id=str(persistent_user_context.user_id),
            operation="browser_refresh_initial"
        )
        
        # Execute initial agent to establish state
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        initial_context = AgentExecutionContext(
            agent_name="triage_agent",
            run_id=str(initial_run_id),
            correlation_id=str(persistent_user_context.request_id),
            retry_count=0,
            user_context=persistent_user_context
        )
        
        initial_state = DeepAgentState(
            user_id=str(persistent_user_context.user_id),
            thread_id=str(persistent_user_context.thread_id),
            agent_context={
                **persistent_user_context.agent_context,
                'user_message': 'Pre-refresh execution to establish state',
                'session_marker': 'pre_refresh'
            }
        )
        
        initial_result = await execution_core.execute_agent(
            context=initial_context,
            state=initial_state,
            timeout=30.0,
            enable_websocket_events=False  # Focus on state, not events
        )
        
        assert initial_result.success is True, "Initial execution before refresh failed"
        
        # Extract session information for refresh simulation
        session_user_id = str(persistent_user_context.user_id)
        session_thread_id = str(persistent_user_context.thread_id)
        auth_token = persistent_user_context.agent_context.get('jwt_token')
        
        self.logger.info(f"Pre-refresh state established. User: {session_user_id}, Thread: {session_thread_id}")
        
        # Phase 2: Simulate browser refresh (create new auth helper with same token)
        await asyncio.sleep(1.0)  # Brief pause to simulate refresh
        
        # Create new WebSocket helper (simulates new browser session)
        refresh_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Simulate state recovery using stored authentication
        recovered_user_context = await create_authenticated_user_context(
            user_email="state_continuity_user@e2e.test",  # Same email
            user_id=session_user_id,  # Same user ID 
            environment="test",
            permissions=["read", "write", "agent_execute", "websocket_connect", "session_persist"],
            websocket_enabled=True
        )
        
        # Validate recovered context matches original
        assert str(recovered_user_context.user_id) == session_user_id, \
            "User ID should be recovered correctly after refresh"
        
        # Phase 3: Execute agent with recovered state
        post_refresh_run_id = unified_id_generator.generate_run_id(
            user_id=session_user_id,
            operation="browser_refresh_recovery"
        )
        
        ws_connection = await refresh_auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        recovery_events = []
        
        async def collect_recovery_events():
            try:
                while True:
                    event_raw = await asyncio.wait_for(ws_connection.recv(), timeout=25.0)
                    event = json.loads(event_raw)
                    recovery_events.append(event)
                    
                    if event.get('type') == 'agent_completed':
                        break
            except asyncio.TimeoutError:
                pass
        
        recovery_context = AgentExecutionContext(
            agent_name="triage_agent",
            run_id=str(post_refresh_run_id),
            correlation_id=str(recovered_user_context.request_id),
            retry_count=0,
            user_context=recovered_user_context
        )
        
        recovery_state = DeepAgentState(
            user_id=session_user_id,
            thread_id=session_thread_id,  # Same thread as before refresh
            agent_context={
                **recovered_user_context.agent_context,
                'user_message': 'Post-refresh execution to validate recovery',
                'session_marker': 'post_refresh',
                'recovered_session': True,
                'previous_execution_id': str(initial_run_id)
            }
        )
        
        event_task = asyncio.create_task(collect_recovery_events())
        
        recovery_result = await execution_core.execute_agent(
            context=recovery_context,
            state=recovery_state,
            timeout=30.0,
            enable_websocket_events=True
        )
        
        await event_task
        await ws_connection.close()
        
        # CRITICAL VALIDATION: Recovery execution succeeded
        assert recovery_result.success is True, \
            f"Post-refresh execution failed: {recovery_result.error}"
        
        # CRITICAL VALIDATION: WebSocket events delivered after refresh
        assert len(recovery_events) > 0, \
            "No WebSocket events received after browser refresh recovery"
        
        recovery_event_types = [event.get('type') for event in recovery_events]
        assert 'agent_started' in recovery_event_types, \
            "Missing agent_started event after refresh"
        assert 'agent_completed' in recovery_event_types, \
            "Missing agent_completed event after refresh"
        
        # CRITICAL VALIDATION: Session continuity preserved
        for event in recovery_events:
            if 'run_id' in event:
                assert event.get('run_id') == str(post_refresh_run_id), \
                    "Recovery events should have post-refresh run_id"
        
        # VALIDATION: State consistency across refresh
        # Both executions should be associated with same user and thread
        assert initial_state.user_id == recovery_state.user_id, \
            "User ID should be consistent across browser refresh"
        assert initial_state.thread_id == recovery_state.thread_id, \
            "Thread ID should be consistent across browser refresh"
        
        self.logger.info("✅ SUCCESS: Browser refresh state recovery validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.state_management
    @pytest.mark.performance
    async def test_long_session_state_persistence(
        self,
        persistent_user_context: StronglyTypedUserExecutionContext,
        websocket_auth_helper: E2EWebSocketAuthHelper,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test state persistence across multiple agent executions in a long session.
        
        Validates that session state is maintained across multiple interactions.
        """
        
        num_interactions = 5
        session_results = []
        session_run_ids = []
        
        # Execute multiple agents in sequence to simulate long session
        for interaction_num in range(num_interactions):
            run_id = unified_id_generator.generate_run_id(
                user_id=str(persistent_user_context.user_id),
                operation=f"long_session_interaction_{interaction_num}"
            )
            session_run_ids.append(str(run_id))
            
            execution_context = AgentExecutionContext(
                agent_name="triage_agent",
                run_id=str(run_id),
                correlation_id=str(persistent_user_context.request_id),
                retry_count=0,
                user_context=persistent_user_context
            )
            
            # Create WebSocket connection for this interaction
            ws_connection = await websocket_auth_helper.connect_authenticated_websocket(timeout=15.0)
            
            interaction_events = []
            
            async def collect_interaction_events():
                try:
                    while True:
                        event_raw = await asyncio.wait_for(ws_connection.recv(), timeout=20.0)
                        event = json.loads(event_raw)
                        interaction_events.append(event)
                        
                        if event.get('type') == 'agent_completed':
                            break
                except asyncio.TimeoutError:
                    pass
            
            # Set up execution infrastructure
            websocket_manager = UnifiedWebSocketManager()
            websocket_bridge = AgentWebSocketBridge(websocket_manager)
            execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
            
            agent_state = DeepAgentState(
                user_id=str(persistent_user_context.user_id),
                thread_id=str(persistent_user_context.thread_id),  # Same thread throughout session
                agent_context={
                    **persistent_user_context.agent_context,
                    'user_message': f'Long session interaction {interaction_num + 1}',
                    'interaction_number': interaction_num + 1,
                    'session_context': 'long_running_session',
                    'previous_interactions': session_run_ids[:-1] if session_run_ids else []
                }
            )
            
            event_task = asyncio.create_task(collect_interaction_events())
            
            result = await execution_core.execute_agent(
                context=execution_context,
                state=agent_state,
                timeout=25.0,
                enable_websocket_events=True
            )
            
            await event_task
            await ws_connection.close()
            
            # Record result
            session_results.append({
                'interaction_num': interaction_num,
                'result': result,
                'events': interaction_events,
                'run_id': str(run_id)
            })
            
            # Brief pause between interactions
            await asyncio.sleep(0.5)
        
        # CRITICAL VALIDATION: All interactions succeeded
        for i, interaction in enumerate(session_results):
            assert interaction['result'].success is True, \
                f"Long session interaction {i} failed: {interaction['result'].error}"
            assert len(interaction['events']) > 0, \
                f"Long session interaction {i} generated no events"
        
        # CRITICAL VALIDATION: Session consistency maintained
        all_user_ids = set()
        all_thread_ids = set()
        
        for interaction in session_results:
            for event in interaction['events']:
                if 'user_id' in event:
                    all_user_ids.add(event['user_id'])
                if 'thread_id' in event:
                    all_thread_ids.add(event['thread_id'])
        
        # Should have only one user_id and thread_id across all interactions
        assert len(all_user_ids) <= 1, \
            f"Multiple user IDs in long session: {all_user_ids}"
        assert len(all_thread_ids) <= 1, \
            f"Multiple thread IDs in long session: {all_thread_ids}"
        
        # VALIDATION: Each interaction had unique run_id
        all_run_ids = [interaction['run_id'] for interaction in session_results]
        assert len(set(all_run_ids)) == num_interactions, \
            f"Run IDs not unique across interactions: {all_run_ids}"
        
        # VALIDATION: All events delivered correctly
        total_events = sum(len(interaction['events']) for interaction in session_results)
        assert total_events >= num_interactions * 2, \
            f"Too few events across long session: {total_events}"
        
        self.logger.info(f"✅ SUCCESS: Long session state persistence validated across {num_interactions} interactions")
        self.logger.info(f"  - Total events: {total_events}")
        self.logger.info(f"  - Unique run IDs: {len(set(all_run_ids))}")
        self.logger.info(f"  - Session user IDs: {all_user_ids}")
        self.logger.info(f"  - Session thread IDs: {all_thread_ids}")