"""Agent Startup Reconnection E2E Tests
 
Tests 5-6 from AGENT_STARTUP_E2E_TEST_PLAN.md:
- test_websocket_reconnection_preserves_agent_state
- test_concurrent_user_agent_startup_isolation

Uses REAL WebSocket connections and agent state management for true integration validation.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - Critical reliability foundation
- Business Goal: Protect agent session continuity and user isolation 
- Value Impact: Prevents lost sessions and data contamination issues
- Revenue Impact: Protects $200K+ MRR through reliable agent state management

Architecture: 450-line compliance through focused reconnection and isolation testing
"""

# Test infrastructure

import asyncio
import time
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.agent_reconnection_state_manager import AgentStateReconnectionManager
from tests.e2e.concurrent_user_isolation_manager import ConcurrentUserIsolationManager
from tests.e2e.real_client_factory import create_real_client_factory


@pytest.mark.asyncio

@pytest.mark.e2e
class TestWebSocketReconnectionPreservesAgentState:

    """Test 5: WebSocket reconnection preserves agent state - BVJ: Session continuity"""
    

    @pytest.mark.e2e
    async def test_websocket_reconnection_preserves_agent_state(self):

        """Test agent state preservation across WebSocket reconnections."""

        factory = create_real_client_factory()

        manager = AgentStateReconnectionManager(factory)
        

        try:

            preserved_state = await self._execute_reconnection_test(manager)

            self._validate_state_preservation(preserved_state)

        finally:

            await factory.cleanup()
    

    async def _execute_reconnection_test(self, manager: AgentStateReconnectionManager) -> dict:

        """Execute reconnection test workflow."""

        user_id = f"reconnect_test_{int(time.time())}"

        await manager.establish_initial_connection(user_id)

        await manager.simulate_connection_loss()

        await asyncio.sleep(1)  # Allow for cleanup

        return await manager.reconnect_and_verify_state()
    

    def _validate_state_preservation(self, preserved_state: dict) -> None:

        """Validate state preservation results."""

        assert preserved_state["state_preserved"], "Agent state was not preserved"

        assert preserved_state["session_continuity"], "Session continuity broken"

        assert preserved_state["reconnection_successful"], "Reconnection failed"


@pytest.mark.asyncio 

@pytest.mark.e2e
class TestConcurrentUserAgentStartupIsolation:

    """Test 6: Concurrent user agent startup isolation - BVJ: Multi-tenant security"""
    

    @pytest.mark.e2e
    async def test_concurrent_user_agent_startup_isolation(self):

        """Test 10 concurrent users with complete isolation."""

        factory = create_real_client_factory()

        manager = ConcurrentUserIsolationManager(factory)
        

        try:

            isolation_validation = await self._execute_concurrent_test(manager)

            self._validate_user_isolation(isolation_validation)

        finally:

            await manager.cleanup_concurrent_sessions()

            await factory.cleanup()
    

    async def _execute_concurrent_test(self, manager: ConcurrentUserIsolationManager) -> dict:

        """Execute concurrent user isolation test."""

        users = await manager.setup_concurrent_users(10)

        assert len(users) == 10, "Failed to setup all concurrent users"

        session_results = await manager.start_concurrent_sessions(users)

        return manager.validate_complete_isolation(session_results)
    

    def _validate_user_isolation(self, isolation_validation: dict) -> None:

        """Validate user isolation requirements."""

        assert isolation_validation["unique_users"], "User ID collision detected"

        assert isolation_validation["unique_sessions"], "Session ID collision detected" 

        assert isolation_validation["no_cross_contamination"], "Data contamination detected"

        min_sessions = isolation_validation["successful_sessions"]

        assert min_sessions >= 8, f"Too few successful sessions: {min_sessions}"