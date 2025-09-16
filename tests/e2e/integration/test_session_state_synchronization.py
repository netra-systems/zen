"""Session State Synchronization Integration Test

Business Value Justification (BVJ):
- Segment: All tiers (Free, Early, Mid, Enterprise) 
- Business Goal: Protect $7K MRR by maintaining seamless user context across platform components
- Value Impact: Ensures consistent user experience across WebSocket connections, server restarts, and concurrent sessions
- Revenue Impact: Prevents user frustration and churn from lost context, protecting monthly recurring revenue
- Strategic Value: Enables reliable multi-tab/multi-device user experiences essential for modern web applications

Refactored for <300 lines using helpers.
"""

import asyncio
import pytest
import time
import json
from typing import Dict, Any, List
import pytest_asyncio
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.config import TEST_USERS, TEST_ENDPOINTS
from tests.e2e.jwt_token_helpers import JWTTestHelper
from tests.e2e.helpers.auth.session_test_helpers import (
    SessionPersistenceManager, CrossServiceSessionValidator, MultiTabSessionManager, create_test_session_data, validate_session_timeout_behavior, create_session_test_scenarios,
    SessionPersistenceManager,
    CrossServiceSessionValidator,
    MultiTabSessionManager,
    create_test_session_data,
    validate_session_timeout_behavior,
    create_session_test_scenarios
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest_asyncio.fixture
async def session_manager():
    """Create session persistence manager fixture."""
    manager = SessionPersistenceManager()
    try:
        yield manager
    finally:
        # Cleanup sessions
        pass


@pytest_asyncio.fixture
async def cross_service_validator():
    """Create cross-service session validator fixture."""
    validator = CrossServiceSessionValidator()
    try:
        yield validator
    finally:
        validator.clear_errors()


@pytest_asyncio.fixture
async def multi_tab_manager():
    """Create multi-tab session manager fixture."""
    manager = MultiTabSessionManager()
    try:
        yield manager
    finally:
        # Cleanup tab sessions
        pass


@pytest_asyncio.fixture
async def jwt_helper():
    """Create JWT test helper fixture."""
    helper = JWTTestHelper()
    try:
        yield helper
    finally:
        # Cleanup tokens
        pass


@pytest.mark.e2e
class SessionStateSynchronizationTests:
    """Test session state synchronization across services."""
    
    @pytest.mark.e2e
    async def test_cross_service_session_sync(self, session_manager, cross_service_validator):
        """Test session synchronization across all services."""
        manager = session_manager
        validator = cross_service_validator
        user_data = TEST_USERS["free"]
        
        # Create session with complex state
        session_state = create_test_session_data(user_data.id, "complex")
        session = await manager.create_test_session(user_data.id, session_state)
        
        # Validate cross-service synchronization
        sync_result = await validator.validate_cross_service_sync(
            session.session_id, 
            ["frontend", "backend", "auth_service"]
        )
        
        # Validate synchronization success
        assert sync_result["consistent"], f"Services not synchronized: {sync_result['inconsistencies']}"
        assert len(sync_result["services_checked"]) == 3
        
        # All services should report session exists
        for service, state in sync_result["sync_results"].items():
            assert state["exists"], f"Session not found in {service}"
            assert state["session_id"] == session.session_id
        
        logger.info(f"Cross-service sync validated for session {session.session_id}")
    
    @pytest.mark.e2e
    async def test_session_persistence_across_restart(self, session_manager):
        """Test session persists across service restart."""
        manager = session_manager
        user_data = TEST_USERS["early"]
        
        # Create session with state
        initial_state = create_test_session_data(user_data.id, "simple")
        session = await manager.create_test_session(user_data.id, initial_state)
        
        # Update session state
        state_updates = {"new_data": "test_value", "timestamp": time.time()}
        update_success = await manager.update_session_state(session.session_id, state_updates)
        assert update_success
        
        # Simulate restart
        restart_result = await manager.simulate_session_restart(session.session_id)
        
        # Validate restart success
        assert restart_result["success"]
        assert restart_result["state_preserved"]
        
        # Validate persistence
        persistence_result = await manager.validate_session_persistence(session.session_id)
        assert persistence_result["valid"]
        assert persistence_result["persistent"]
        
        logger.info(f"Session persistence validated across restart for {session.session_id}")
    
    @pytest.mark.e2e
    async def test_concurrent_session_updates(self, session_manager):
        """Test concurrent session updates from multiple sources."""
        manager = session_manager
        user_data = TEST_USERS["mid"]
        
        # Create session
        session = await manager.create_test_session(user_data.id)
        
        # Perform concurrent updates
        update_tasks = []
        
        for i in range(5):
            update_data = {f"concurrent_update_{i}": f"value_{i}", "update_time": time.time()}
            task = asyncio.create_task(
                manager.update_session_state(session.session_id, update_data)
            )
            update_tasks.append(task)
        
        # Wait for all updates to complete
        update_results = await asyncio.gather(*update_tasks)
        
        # Validate all updates succeeded
        for result in update_results:
            assert result, "Concurrent update failed"
        
        # Validate final session state
        persistence_result = await manager.validate_session_persistence(session.session_id)
        assert persistence_result["valid"]
        
        # Check session contains all updates
        final_session = manager.active_sessions[session.session_id]
        assert len(final_session.state_data) >= 5  # At least 5 concurrent updates
        
        logger.info(f"Concurrent updates validated for session {session.session_id}")
    
    @pytest.mark.e2e
    async def test_multi_tab_session_isolation(self, multi_tab_manager):
        """Test multi-tab session isolation and synchronization."""
        manager = multi_tab_manager
        user_data = TEST_USERS["enterprise"]
        
        # Create multiple tabs for same user
        tab_1 = await manager.create_tab_session(user_data.id, "tab_1")
        tab_2 = await manager.create_tab_session(user_data.id, "tab_2")
        
        # Connect WebSockets for both tabs
        await manager.connect_tab_websocket("tab_1")
        await manager.connect_tab_websocket("tab_2")
        
        # Validate tabs are properly isolated for security
        isolation_valid = manager.validate_tab_isolation("tab_1", "tab_2")
        assert isolation_valid
        
        # Test state synchronization between tabs
        sync_result = await manager.sync_tab_states(user_data.id)
        assert sync_result["success"]
        assert sync_result["tabs_synced"] == 2
        
        # Validate synchronized state
        assert "tab_1" in sync_result["tab_ids"]
        assert "tab_2" in sync_result["tab_ids"]
        
        # Check both tabs have synchronized state
        tab_1_session = manager.tab_sessions["tab_1"]
        tab_2_session = manager.tab_sessions["tab_2"]
        
        assert "shared_data" in tab_1_session["state"]
        assert "shared_data" in tab_2_session["state"]
        assert tab_1_session["state"]["shared_data"] == tab_2_session["state"]["shared_data"]
        
        logger.info(f"Multi-tab isolation and sync validated for user {user_data.id}")
    
    @pytest.mark.e2e
    async def test_session_timeout_handling(self, session_manager):
        """Test session timeout behavior."""
        manager = session_manager
        user_data = TEST_USERS["free"]
        
        # Create session
        session = await manager.create_test_session(user_data.id)
        
        # Test session timeout behavior
        timeout_valid = await validate_session_timeout_behavior(
            manager, 
            session.session_id, 
            timeout_seconds=2.0
        )
        
        assert timeout_valid, "Session timeout handling failed"
        
        # Validate session still accessible after timeout test
        persistence_result = await manager.validate_session_persistence(session.session_id)
        assert persistence_result["valid"]
        
        logger.info(f"Session timeout handling validated for {session.session_id}")
    
    @pytest.mark.e2e
    async def test_session_migration_between_servers(self, session_manager, cross_service_validator):
        """Test session migration during server changes."""
        session_mgr = session_manager
        validator = cross_service_validator
        user_data = TEST_USERS["mid"]
        
        # Create session with complex state
        complex_state = create_test_session_data(user_data.id, "complex")
        session = await session_mgr.create_test_session(user_data.id, complex_state)
        
        # Validate initial cross-service presence
        initial_sync = await validator.validate_cross_service_sync(session.session_id)
        assert initial_sync["consistent"]
        
        # Simulate server migration (restart simulation)
        migration_result = await session_mgr.simulate_session_restart(session.session_id)
        assert migration_result["success"]
        assert migration_result["state_preserved"]
        
        # Validate session available after migration
        post_migration_sync = await validator.validate_cross_service_sync(session.session_id)
        assert post_migration_sync["consistent"]
        
        # Validate complex state preserved
        final_session = session_mgr.active_sessions[session.session_id]
        assert "ui_state" in final_session.state_data
        assert "cache" in final_session.state_data
        
        logger.info(f"Session migration validated for {session.session_id}")
    
    @pytest.mark.e2e
    async def test_different_user_session_isolation(self, session_manager, cross_service_validator):
        """Test sessions between different users are properly isolated."""
        manager = session_manager
        validator = cross_service_validator
        
        # Create sessions for different users
        user_1 = TEST_USERS["free"]
        user_2 = TEST_USERS["early"]
        
        session_1 = await manager.create_test_session(user_1.id, {"user_specific": "data_1"})
        session_2 = await manager.create_test_session(user_2.id, {"user_specific": "data_2"})
        
        # Validate both sessions exist
        sync_1 = await validator.validate_cross_service_sync(session_1.session_id)
        sync_2 = await validator.validate_cross_service_sync(session_2.session_id)
        
        assert sync_1["consistent"]
        assert sync_2["consistent"]
        
        # Validate sessions are isolated
        assert session_1.session_id != session_2.session_id
        assert session_1.user_id != session_2.user_id
        assert session_1.state_data != session_2.state_data
        
        logger.info(f"User session isolation validated between {user_1.id} and {user_2.id}")
    
    @pytest.mark.performance
    @pytest.mark.e2e
    async def test_session_sync_performance(self, session_manager, cross_service_validator):
        """Test session synchronization performance."""
        manager = session_manager
        validator = cross_service_validator
        user_data = TEST_USERS["enterprise"]
        
        # Measure session creation time
        create_start = time.time()
        session = await manager.create_test_session(user_data.id)
        create_time = time.time() - create_start
        
        assert create_time < 1.0, f"Session creation too slow: {create_time:.3f}s"
        
        # Measure cross-service sync time
        sync_start = time.time()
        sync_result = await validator.validate_cross_service_sync(session.session_id)
        sync_time = time.time() - sync_start
        
        assert sync_time < 2.0, f"Cross-service sync too slow: {sync_time:.3f}s"
        assert sync_result["consistent"]
        
        # Measure state update time
        update_start = time.time()
        update_success = await manager.update_session_state(
            session.session_id, 
            {"performance_test": True}
        )
        update_time = time.time() - update_start
        
        assert update_time < 0.5, f"State update too slow: {update_time:.3f}s"
        assert update_success
        
        logger.info(f"Session sync performance validated - "
                   f"Create: {create_time:.3f}s, "
                   f"Sync: {sync_time:.3f}s, "
                   f"Update: {update_time:.3f}s")
    
    @pytest.mark.e2e
    async def test_session_state_scenarios(self, session_manager):
        """Test various session state scenarios."""
        manager = session_manager
        user_data = TEST_USERS["mid"]
        
        # Test different session scenarios
        scenarios = create_session_test_scenarios()
        
        for scenario in scenarios[:3]:  # Test first 3 scenarios
            scenario_start = time.time()
            
            # Create session based on scenario complexity
            if scenario["complexity"] == "simple":
                state_data = create_test_session_data(user_data.id, "simple")
            elif scenario["complexity"] == "complex":
                state_data = create_test_session_data(user_data.id, "complex")
            else:
                state_data = create_test_session_data(user_data.id, "simple")
            
            session = await manager.create_test_session(user_data.id, state_data)
            
            # Validate session persistence
            persistence_result = await manager.validate_session_persistence(session.session_id)
            assert persistence_result["valid"]
            
            scenario_time = time.time() - scenario_start
            expected_duration = scenario["expected_duration"]
            
            # Should complete within expected time
            assert scenario_time < expected_duration, \
                f"Scenario '{scenario['name']}' took {scenario_time:.3f}s > {expected_duration}s"
            
            logger.info(f"Scenario '{scenario['name']}' completed in {scenario_time:.3f}s")
        
        # Validate all scenarios created sessions
        stats = manager.get_session_statistics()
        assert stats["active_sessions"] >= 3
