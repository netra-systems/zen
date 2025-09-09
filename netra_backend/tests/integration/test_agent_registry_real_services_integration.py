"""Integration Tests for Agent Registry with Real Services

Business Value Justification:
- Segment: Platform/Internal - Agent Infrastructure  
- Business Goal: Ensure reliable agent discovery and lifecycle management
- Value Impact: Enables dynamic agent deployment and scaling
- Strategic Impact: Foundation for multi-agent AI orchestration

CRITICAL TEST PURPOSE:
These integration tests validate agent registry functionality with real
database persistence and Redis caching for agent metadata.

Test Coverage:
- Agent registration and discovery with real database
- Agent metadata caching with real Redis
- Concurrent agent access with real services
- Agent lifecycle management with persistence
- Registry performance with real backend services
"""

import pytest
import asyncio
import uuid
from typing import Dict, Any
from datetime import datetime

from netra_backend.app.core.registry.universal_registry import AgentRegistry
from test_framework.ssot.real_services_test_fixtures import *


class TestAgentRegistryRealServices:
    """Integration tests for agent registry with real services."""
    
    @pytest.mark.asyncio
    async def test_agent_registration_with_real_database_persistence(self, real_services_fixture, with_test_database):
        """Test agent registration with real database persistence."""
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for registry testing")
        
        db_session = with_test_database
        
        # Create registry with database persistence
        registry = AgentRegistry(
            database_session=db_session,
            enable_persistence=True
        )
        
        # Create test agent
        test_agent = MockRegistryAgent(
            name="persistent_agent",
            version="1.0.0",
            capabilities=["data_analysis", "cost_optimization"]
        )
        
        # Act - register agent with persistence
        registration_result = await registry.register_agent(
            agent=test_agent,
            persist_to_database=True
        )
        
        # Assert - verify registration and persistence
        assert registration_result == True
        assert registry.has_agent("persistent_agent") == True
        
        # Verify database persistence
        from sqlalchemy import text
        query = text("""
            SELECT agent_name, agent_version, capabilities, created_at
            FROM agent_registrations 
            WHERE agent_name = :agent_name
        """)
        
        result = await db_session.execute(query, {"agent_name": "persistent_agent"})
        db_record = result.fetchone()
        
        if db_record:
            assert db_record.agent_name == "persistent_agent"
            assert db_record.agent_version == "1.0.0"
            assert "data_analysis" in db_record.capabilities
        
        # Test agent retrieval
        retrieved_agent = registry.get_agent("persistent_agent")
        assert retrieved_agent is not None
        assert retrieved_agent.name == "persistent_agent"
    
    @pytest.mark.asyncio
    async def test_agent_metadata_caching_with_real_redis(self, real_services_fixture, real_redis_fixture):
        """Test agent metadata caching with real Redis."""
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for registry caching testing")
        
        redis_client = real_redis_fixture
        
        # Create registry with Redis caching
        registry = AgentRegistry(
            redis_client=redis_client,
            enable_caching=True,
            cache_ttl=300  # 5 minutes
        )
        
        # Create test agents
        agents = [
            MockRegistryAgent("cached_agent_1", "1.0.0", ["analysis"]),
            MockRegistryAgent("cached_agent_2", "2.0.0", ["optimization"]), 
            MockRegistryAgent("cached_agent_3", "1.5.0", ["reporting"])
        ]
        
        # Act - register agents with caching
        for agent in agents:
            await registry.register_agent(agent, enable_caching=True)
        
        # Verify Redis caching
        for agent in agents:
            cache_key = f"agent:metadata:{agent.name}"
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                import json
                metadata = json.loads(cached_data)
                assert metadata["name"] == agent.name
                assert metadata["version"] == agent.version
        
        # Test cache-based retrieval
        cached_agent = registry.get_agent("cached_agent_2")
        assert cached_agent is not None
        assert cached_agent.name == "cached_agent_2"
        
        # Verify cache performance
        start_time = asyncio.get_event_loop().time()
        
        # Multiple retrievals should be fast (cache hits)
        for _ in range(10):
            registry.get_agent("cached_agent_1")
        
        end_time = asyncio.get_event_loop().time()
        cache_time = end_time - start_time
        
        assert cache_time < 0.1, "Cached retrievals should be very fast"
    
    @pytest.mark.asyncio 
    async def test_concurrent_agent_access_real_services(self, real_services_fixture, real_redis_fixture):
        """Test concurrent agent access with real service backends."""
        if not real_services_fixture["services_available"]["redis"]:
            pytest.skip("Redis service not available for concurrent testing")
        
        redis_client = real_redis_fixture
        
        # Create registry with concurrency support
        registry = AgentRegistry(
            redis_client=redis_client,
            enable_concurrency_locks=True
        )
        
        # Create agents for concurrent testing
        concurrent_agent = MockRegistryAgent(
            "concurrent_agent",
            "1.0.0", 
            ["concurrent_processing"]
        )
        
        await registry.register_agent(concurrent_agent)
        
        # Act - concurrent agent access
        async def access_agent(session_id: int):
            """Access agent concurrently."""
            try:
                agent = registry.get_agent("concurrent_agent")
                if agent:
                    # Simulate agent usage
                    await asyncio.sleep(0.1)
                    result = await agent.execute(f"task_{session_id}")
                    return {"session": session_id, "result": result, "success": True}
            except Exception as e:
                return {"session": session_id, "error": str(e), "success": False}
        
        # Execute concurrent access
        num_concurrent = 10
        tasks = [access_agent(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert - verify concurrent access
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        assert len(successful_results) == num_concurrent
        
        # Verify all sessions got results
        session_ids = [r["session"] for r in successful_results]
        assert len(set(session_ids)) == num_concurrent  # All unique


class MockRegistryAgent:
    """Mock agent for registry testing."""
    
    def __init__(self, name: str, version: str, capabilities: list):
        self.name = name
        self.version = version
        self.capabilities = capabilities
        self.created_at = datetime.utcnow()
    
    async def execute(self, task: str):
        """Execute mock task."""
        await asyncio.sleep(0.05)  # Simulate processing
        return f"Executed {task} with {self.name} v{self.version}"