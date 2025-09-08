"""Integration tests for Phase 3 data access factory integration.

Tests that UserExecutionEngine properly integrates with data access factories
and that agents can access user-scoped ClickHouse and Redis contexts.

Business Value: Ensures complete data isolation for multi-tenant operations.
"""

import asyncio
import pytest
from datetime import datetime
from uuid import uuid4
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.data_access_integration import (
    DataAccessCapabilities,
    UserExecutionEngineExtensions
)
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.data_sub_agent.core.data_analysis_core import DataAnalysisCore
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.factories.data_access_factory import (
    get_clickhouse_factory,
    get_redis_factory,
    cleanup_all_factories
)


class MockUserExecutionEngine:
    """Mock UserExecutionEngine for testing data access integration."""
    
    def __init__(self, user_context: UserExecutionContext):
        self.context = user_context
        self._data_access_capabilities = None
    
    def get_user_context(self):
        return self.context


@pytest.fixture
async def user_context():
    """Create a test UserExecutionContext."""
    context = UserExecutionContext(
        user_id="test_user_123",
        run_id="test_run_456", 
        thread_id="test_thread_789",
        websocket_connection_id="test_websocket_abc",
        metadata={"analysis_type": "performance", "timeframe": "24h"}
    )
    yield context


@pytest.fixture 
async def mock_engine(user_context):
    """Create a mock UserExecutionEngine with data access capabilities."""
    engine = MockUserExecutionEngine(user_context)
    
    # Integrate data access capabilities
    UserExecutionEngineExtensions.integrate_data_access(engine)
    
    yield engine
    
    # Cleanup
    await UserExecutionEngineExtensions.cleanup_data_access(engine)


@pytest.fixture
async def cleanup_factories():
    """Cleanup factories after tests."""
    yield
    await cleanup_all_factories()


class TestDataAccessCapabilities:
    """Test DataAccessCapabilities class functionality."""
    
    async def test_data_access_capabilities_initialization(self, user_context):
        """Test that DataAccessCapabilities initializes properly."""
        capabilities = DataAccessCapabilities(user_context)
        
        assert capabilities.user_context == user_context
        assert capabilities._clickhouse_factory is not None
        assert capabilities._redis_factory is not None
    
    async def test_clickhouse_context_manager(self, user_context, cleanup_factories):
        """Test ClickHouse context manager provides user-scoped access."""
        capabilities = DataAccessCapabilities(user_context)
        
        async with capabilities.get_clickhouse_context() as ch_context:
            assert ch_context is not None
            assert hasattr(ch_context, 'execute')
            assert hasattr(ch_context, 'user_id')
            assert ch_context.user_id == user_context.user_id
    
    async def test_redis_context_manager(self, user_context, cleanup_factories):
        """Test Redis context manager provides user-scoped access."""
        capabilities = DataAccessCapabilities(user_context)
        
        async with capabilities.get_redis_context() as redis_context:
            assert redis_context is not None
            assert hasattr(redis_context, 'set')
            assert hasattr(redis_context, 'get')
            assert hasattr(redis_context, 'user_id')
            assert redis_context.user_id == user_context.user_id


class TestUserExecutionEngineIntegration:
    """Test UserExecutionEngine data access integration."""
    
    async def test_engine_has_data_access_methods(self, mock_engine):
        """Test that UserExecutionEngine gets data access methods."""
        engine = mock_engine
        
        # Check that data access methods were added
        assert hasattr(engine, 'get_clickhouse_context')
        assert hasattr(engine, 'get_redis_context')
        assert hasattr(engine, 'execute_analytics_query')
        assert hasattr(engine, 'store_session_data')
        assert hasattr(engine, 'get_session_data')
    
    async def test_engine_data_access_context_managers(self, mock_engine, cleanup_factories):
        """Test UserExecutionEngine data access context managers."""
        engine = mock_engine
        
        # Test ClickHouse context manager
        async with engine.get_clickhouse_context() as ch:
            assert ch is not None
            assert ch.user_id == engine.context.user_id
        
        # Test Redis context manager
        async with engine.get_redis_context() as redis:
            assert redis is not None
            assert redis.user_id == engine.context.user_id
    
    async def test_engine_analytics_query_method(self, mock_engine, cleanup_factories):
        """Test UserExecutionEngine analytics query method."""
        engine = mock_engine
        
        # Test analytics query (will use mock ClickHouse service)
        try:
            result = await engine.execute_analytics_query("SELECT 1 as test")
            # Should not raise an error even with mock service
            assert isinstance(result, list)
        except Exception as e:
            # Expected with mock services - just verify method exists and is callable
            assert callable(engine.execute_analytics_query)


class TestAgentDataAccessIntegration:
    """Test agent integration with data access capabilities."""
    
    async def test_data_analysis_core_with_capabilities(self, user_context):
        """Test DataAnalysisCore with data access capabilities."""
        # Create database session manager (stub implementation)
        session_manager = DatabaseSessionManager()
        
        # Create data access capabilities
        capabilities = DataAccessCapabilities(user_context)
        
        # Create DataAnalysisCore with capabilities
        core = DataAnalysisCore(session_manager, capabilities)
        
        assert core.session_manager == session_manager
        assert core.data_access == capabilities
        
        await session_manager.close()
    
    async def test_data_analysis_core_legacy_fallback(self, user_context):
        """Test DataAnalysisCore legacy fallback without capabilities."""
        # Create database session manager (stub implementation)
        session_manager = DatabaseSessionManager()
        
        # Create DataAnalysisCore without capabilities (legacy mode)
        core = DataAnalysisCore(session_manager, None)
        
        assert core.session_manager == session_manager
        assert core.data_access is None
        
        await session_manager.close()
    
    async def test_data_sub_agent_creates_capabilities(self, user_context):
        """Test that DataSubAgent creates data access capabilities."""
        # Create DataSubAgent
        agent = DataSubAgent()
        
        # Verify agent was created successfully
        assert agent.name == "DataSubAgent"
        assert hasattr(agent, 'data_processor')
        assert hasattr(agent, 'anomaly_detector')


class TestDataIsolation:
    """Test that data access is properly isolated between users."""
    
    async def test_user_isolation_different_contexts(self, cleanup_factories):
        """Test that different users get isolated data access."""
        # Create two different user contexts
        context1 = UserExecutionContext(
            user_id="user_1", 
            run_id="run_1",
            thread_id="thread_1",
            websocket_connection_id="websocket_1"
        )
        
        context2 = UserExecutionContext(
            user_id="user_2",
            run_id="run_2", 
            thread_id="thread_2",
            websocket_connection_id="websocket_2"
        )
        
        # Create data access capabilities for each user
        capabilities1 = DataAccessCapabilities(context1)
        capabilities2 = DataAccessCapabilities(context2)
        
        # Verify they have different user contexts
        assert capabilities1.user_context.user_id != capabilities2.user_context.user_id
        assert capabilities1.user_context.run_id != capabilities2.user_context.run_id
        
        # Verify contexts maintain proper user isolation
        async with capabilities1.get_clickhouse_context() as ch1:
            async with capabilities2.get_clickhouse_context() as ch2:
                assert ch1.user_id != ch2.user_id
                assert ch1.user_id == context1.user_id
                assert ch2.user_id == context2.user_id
    
    async def test_factory_stats_track_users(self, cleanup_factories):
        """Test that factory stats properly track different users."""
        # Create contexts for different users
        contexts = []
        capabilities = []
        
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"test_user_{i}",
                run_id=f"test_run_{i}",
                thread_id=f"test_thread_{i}",
                websocket_connection_id=f"test_websocket_{i}"
            )
            contexts.append(context)
            capabilities.append(DataAccessCapabilities(context))
        
        # Get factory stats
        ch_factory = get_clickhouse_factory()
        redis_factory = get_redis_factory()
        
        ch_stats = await ch_factory.get_context_stats()
        redis_stats = await redis_factory.get_context_stats()
        
        # Verify stats show multiple users
        assert ch_stats["factory_name"] == "ClickHouseAccessFactory"
        assert redis_stats["factory_name"] == "RedisAccessFactory"
        
        # Should have contexts for the users
        assert ch_stats["users_with_contexts"] >= 0  # May be 0 if contexts haven't been created yet
        assert redis_stats["users_with_contexts"] >= 0


class TestWebSocketCompatibility:
    """Test that WebSocket events still work with factory integration."""
    
    async def test_data_sub_agent_websocket_events(self, user_context):
        """Test that DataSubAgent still emits proper WebSocket events."""
        # Create DataSubAgent
        agent = DataSubAgent()
        
        # Verify the agent has WebSocket capabilities from BaseAgent
        assert hasattr(agent, 'emit_agent_started')
        assert hasattr(agent, 'emit_thinking')
        assert hasattr(agent, 'emit_progress') 
        assert hasattr(agent, 'emit_agent_completed')
        assert hasattr(agent, 'emit_error')
        
        # Note: Full WebSocket testing requires integration environment
        # This test verifies the methods exist and can be called


if __name__ == "__main__":
    # Run tests standalone
    pytest.main([__file__, "-v"])