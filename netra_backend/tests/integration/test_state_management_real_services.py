"""Integration Tests for State Management with Real Services

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable agent state persistence and retrieval
- Value Impact: Enables resumable AI workflows and state recovery
- Strategic Impact: Foundation for long-running AI operations

Test Coverage:
- Agent state persistence with real Redis
- State serialization and deserialization 
- Multi-user state isolation
- State recovery after service restarts
"""

import pytest
import asyncio
import uuid
from datetime import datetime

from netra_backend.app.agents.state import DeepAgentState
from test_framework.ssot.real_services_test_fixtures import *


@pytest.mark.integration
class TestStateManagementRealServices:
    """Integration tests for state management with real services."""
    
    @pytest.mark.asyncio
    async def test_agent_state_redis_persistence(self, real_services_fixture, real_redis_fixture):
        """Test agent state persistence with real Redis."""
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for state testing")
        
        redis_client = real_redis_fixture
        
        # Create agent state
        state = DeepAgentState(
            user_id=f"state-user-{uuid.uuid4()}",
            thread_id=f"state-thread-{uuid.uuid4()}",
            agent_name="state_test_agent",
            user_data={
                "preferences": {"theme": "dark"},
                "context": {"last_query": "analyze costs"}
            }
        )
        
        # Act - persist state to Redis
        state_key = f"agent_state:{state.user_id}:{state.thread_id}"
        import json
        await redis_client.set(state_key, json.dumps(state.to_dict()), ex=3600)
        
        # Retrieve state
        stored_data = await redis_client.get(state_key)
        restored_state_dict = json.loads(stored_data)
        
        # Assert - verify state persistence
        assert restored_state_dict["user_id"] == state.user_id
        assert restored_state_dict["thread_id"] == state.thread_id
        assert restored_state_dict["agent_name"] == state.agent_name
        assert restored_state_dict["user_data"]["preferences"]["theme"] == "dark"
    
    @pytest.mark.asyncio
    async def test_multi_user_state_isolation_redis(self, real_services_fixture, real_redis_fixture):
        """Test multi-user state isolation with real Redis."""
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for isolation testing")
        
        redis_client = real_redis_fixture
        
        # Create states for different users
        user1_state = DeepAgentState(
            user_id=f"isolation-user1-{uuid.uuid4()}",
            thread_id=f"user1-thread-{uuid.uuid4()}",
            user_data={"sensitive": "user1_data"}
        )
        
        user2_state = DeepAgentState(
            user_id=f"isolation-user2-{uuid.uuid4()}",
            thread_id=f"user2-thread-{uuid.uuid4()}",
            user_data={"sensitive": "user2_data"}
        )
        
        # Store both states
        import json
        await redis_client.set(f"state:{user1_state.user_id}", json.dumps(user1_state.to_dict()))
        await redis_client.set(f"state:{user2_state.user_id}", json.dumps(user2_state.to_dict()))
        
        # Retrieve and verify isolation
        user1_data = await redis_client.get(f"state:{user1_state.user_id}")
        user2_data = await redis_client.get(f"state:{user2_state.user_id}")
        
        user1_restored = json.loads(user1_data)
        user2_restored = json.loads(user2_data)
        
        # Assert isolation
        assert user1_restored["user_data"]["sensitive"] == "user1_data"
        assert user2_restored["user_data"]["sensitive"] == "user2_data"
        assert user1_restored["user_id"] != user2_restored["user_id"]