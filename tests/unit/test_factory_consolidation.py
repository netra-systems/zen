"""
Comprehensive test suite for factory consolidation with performance optimizations.

Business Value Justification:
- Segment: Platform Quality Assurance
- Business Goal: Stability and Reliability
- Value Impact: Ensures consolidated factory maintains all functionality
- Strategic Impact: Validates performance improvements without regressions
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import Mock, MagicMock, AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    UserWebSocketEmitter,
    get_agent_instance_factory,
    configure_agent_instance_factory
)
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.factory_performance_config import (
    FactoryPerformanceConfig,
    set_factory_performance_config
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    def __init__(self):
        super().__init__()
        self.executed = False
    
    async def execute(self, state: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        self.executed = True
        return {"result": "success"}


@pytest.fixture
async def mock_websocket_bridge():
    """Mock WebSocket bridge for testing."""
    bridge = AsyncMock(spec=AgentWebSocketBridge)
    bridge.notify_agent_started = AsyncMock(return_value=True)
    bridge.notify_agent_thinking = AsyncMock(return_value=True)
    bridge.notify_tool_executing = AsyncMock(return_value=True)
    bridge.notify_tool_completed = AsyncMock(return_value=True)
    bridge.notify_agent_completed = AsyncMock(return_value=True)
    return bridge


@pytest.fixture
async def mock_websocket_manager():
    """Mock WebSocket manager for testing."""
    return MagicMock(spec=WebSocketManager)


@pytest.fixture
async def mock_agent_class_registry():
    """Mock agent class registry for testing."""
    registry = MagicMock(spec=AgentClassRegistry)
    registry.get_agent_class = Mock(return_value=MockAgent)
    return registry


@pytest.fixture
async def mock_db_session():
    """Mock database session for testing."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def minimal_performance_config():
    """Minimal performance configuration for testing."""
    config = FactoryPerformanceConfig.minimal()
    set_factory_performance_config(config)
    return config


@pytest.fixture
def balanced_performance_config():
    """Balanced performance configuration for testing."""
    config = FactoryPerformanceConfig.balanced()
    set_factory_performance_config(config)
    return config


@pytest.fixture
def maximum_performance_config():
    """Maximum performance configuration for testing."""
    config = FactoryPerformanceConfig.maximum_performance()
    set_factory_performance_config(config)
    return config


class TestFactoryConsolidation:
    """Test suite for factory consolidation."""
    
    @pytest.mark.asyncio
    async def test_factory_initialization_with_minimal_config(self, minimal_performance_config):
        """Test factory initialization with minimal configuration."""
        factory = AgentInstanceFactory()
        
        assert factory._performance_config == minimal_performance_config
        assert factory._emitter_pool is None
        assert not hasattr(factory, '_agent_class_cache')
        assert not hasattr(factory, '_perf_stats')
    
    @pytest.mark.asyncio
    async def test_factory_initialization_with_balanced_config(self, balanced_performance_config, mock_websocket_bridge, mock_db_session):
        """Test factory initialization with balanced configuration."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        assert factory._performance_config == balanced_performance_config
        
        # Pool is lazily initialized, so create a context to trigger it
        if balanced_performance_config.enable_emitter_pooling:
            context = await factory.create_user_execution_context(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4()),
                db_session=mock_db_session
            )
            assert factory._emitter_pool is not None
            await factory.cleanup_user_context(context)
        
        assert hasattr(factory, '_agent_class_cache')
        assert hasattr(factory, '_perf_stats')
    
    @pytest.mark.asyncio
    async def test_factory_configuration(self, mock_websocket_bridge, mock_agent_class_registry):
        """Test factory configuration with required components."""
        factory = AgentInstanceFactory()
        
        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge
        )
        
        assert factory._websocket_bridge == mock_websocket_bridge
        assert factory._agent_class_registry == mock_agent_class_registry
    
    @pytest.mark.asyncio
    async def test_user_context_creation(self, mock_websocket_bridge, mock_db_session, balanced_performance_config):
        """Test user execution context creation with pooling."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        user_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        
        context = await factory.create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=mock_db_session
        )
        
        assert context.user_id == user_id
        assert context.thread_id == thread_id
        assert context.run_id == run_id
        assert context.db_session == mock_db_session
        
        # Check if emitter was created
        context_id = f"{user_id}_{thread_id}_{run_id}"
        assert context_id in factory._active_contexts
    
    @pytest.mark.asyncio
    async def test_agent_instance_creation(self, mock_websocket_bridge, mock_agent_class_registry, mock_db_session):
        """Test agent instance creation with caching."""
        factory = AgentInstanceFactory()
        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge
        )
        
        # Create context
        context = await factory.create_user_execution_context(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            db_session=mock_db_session
        )
        
        # Create agent instance
        agent = await factory.create_agent_instance("test_agent", context)
        
        assert isinstance(agent, MockAgent)
        assert not agent.executed
        
        # Verify caching behavior
        mock_agent_class_registry.get_agent_class.assert_called_once_with("test_agent")
    
    @pytest.mark.asyncio
    async def test_context_cleanup(self, mock_websocket_bridge, mock_db_session, balanced_performance_config):
        """Test user context cleanup with emitter pooling."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        user_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        
        context = await factory.create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=mock_db_session
        )
        
        context_id = f"{user_id}_{thread_id}_{run_id}"
        assert context_id in factory._active_contexts
        
        # Cleanup context
        await factory.cleanup_user_context(context)
        
        # Verify cleanup
        assert context_id not in factory._active_contexts
        assert factory._factory_metrics['total_contexts_cleaned'] == 1
    
    @pytest.mark.asyncio
    async def test_user_execution_scope(self, mock_websocket_bridge, mock_db_session):
        """Test user execution scope context manager."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        user_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        
        async with factory.user_execution_scope(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=mock_db_session
        ) as context:
            assert context.user_id == user_id
            assert context.thread_id == thread_id
            assert context.run_id == run_id
            
            context_id = f"{user_id}_{thread_id}_{run_id}"
            assert context_id in factory._active_contexts
        
        # Context should be cleaned up after exiting scope
        assert context_id not in factory._active_contexts
    
    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, mock_websocket_bridge, mock_db_session, balanced_performance_config):
        """Test performance metrics tracking."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create multiple contexts to generate metrics
        for i in range(5):
            context = await factory.create_user_execution_context(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4()),
                db_session=mock_db_session
            )
            await factory.cleanup_user_context(context)
        
        # Check metrics
        metrics = factory.get_factory_metrics()
        assert metrics['total_instances_created'] == 5
        assert metrics['total_contexts_cleaned'] == 5
        assert 'performance_config' in metrics
        
        # Check performance stats if enabled
        if balanced_performance_config.enable_metrics:
            assert len(factory._perf_stats['context_creation_ms']) > 0
            assert len(factory._perf_stats['cleanup_ms']) > 0
    
    @pytest.mark.asyncio
    async def test_pool_statistics(self, mock_websocket_bridge, balanced_performance_config):
        """Test emitter pool statistics."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        pool_stats = factory.get_pool_stats()
        
        if balanced_performance_config.enable_emitter_pooling:
            assert 'total_created' in pool_stats
            assert 'pool_size' in pool_stats
            assert 'active_count' in pool_stats
        else:
            assert pool_stats == {}
    
    @pytest.mark.asyncio
    async def test_backward_compatibility(self, mock_websocket_bridge, mock_agent_class_registry, mock_db_session):
        """Test backward compatibility with existing code."""
        factory = AgentInstanceFactory()
        
        # Old style configuration should still work
        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge,
            websocket_manager=None
        )
        
        # Old style context creation should still work
        context = await factory.create_user_execution_context(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            db_session=mock_db_session
        )
        
        assert context is not None
        assert isinstance(context._websocket_emitter, UserWebSocketEmitter)
    
    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self, mock_websocket_bridge, mock_db_session):
        """Test concurrent operations for multiple users."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create contexts for multiple users concurrently
        async def create_and_cleanup_context(user_num):
            context = await factory.create_user_execution_context(
                user_id=f"user_{user_num}",
                thread_id=f"thread_{user_num}",
                run_id=f"run_{user_num}",
                db_session=mock_db_session
            )
            await asyncio.sleep(0.01)  # Simulate some work
            await factory.cleanup_user_context(context)
            return user_num
        
        # Run 10 concurrent operations
        tasks = [create_and_cleanup_context(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert factory._factory_metrics['total_instances_created'] == 10
        assert factory._factory_metrics['total_contexts_cleaned'] == 10
        assert factory._factory_metrics['active_contexts'] == 0
    
    @pytest.mark.asyncio
    async def test_performance_targets(self, mock_websocket_bridge, mock_db_session, maximum_performance_config):
        """Test that performance targets are met."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Measure context creation time
        start_time = time.perf_counter()
        context = await factory.create_user_execution_context(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            db_session=mock_db_session
        )
        creation_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Measure cleanup time
        start_time = time.perf_counter()
        await factory.cleanup_user_context(context)
        cleanup_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Check against performance targets
        assert creation_time_ms < maximum_performance_config.target_context_creation_ms * 2
        assert cleanup_time_ms < maximum_performance_config.target_cleanup_ms * 2
    
    @pytest.mark.asyncio
    async def test_factory_singleton(self):
        """Test factory singleton behavior."""
        factory1 = get_agent_instance_factory()
        factory2 = get_agent_instance_factory()
        
        assert factory1 is factory2
    
    @pytest.mark.asyncio
    async def test_configure_singleton_factory(self, mock_websocket_bridge):
        """Test configuring the singleton factory."""
        factory = await configure_agent_instance_factory(
            websocket_bridge=mock_websocket_bridge
        )
        
        assert factory._websocket_bridge == mock_websocket_bridge
        
        # Verify same instance returned by getter
        assert factory is get_agent_instance_factory()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_context_creation(self):
        """Test error handling when factory not configured."""
        factory = AgentInstanceFactory()
        
        with pytest.raises(ValueError, match="Factory not configured"):
            await factory.create_user_execution_context(
                user_id="test",
                thread_id="test",
                run_id="test"
            )
    
    @pytest.mark.asyncio
    async def test_websocket_emitter_notifications(self, mock_websocket_bridge):
        """Test WebSocket emitter sends all required notifications."""
        emitter = UserWebSocketEmitter(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            websocket_bridge=mock_websocket_bridge
        )
        
        # Test all 5 critical WebSocket events
        assert await emitter.notify_agent_started("test_agent") == True
        assert await emitter.notify_agent_thinking("test_agent", "reasoning") == True
        assert await emitter.notify_tool_executing("test_agent", "test_tool") == True
        assert await emitter.notify_tool_completed("test_agent", "test_tool", True) == True
        assert await emitter.notify_agent_completed("test_agent", {"result": "done"}) == True
        
        # Verify bridge was called
        mock_websocket_bridge.notify_agent_started.assert_called_once()
        mock_websocket_bridge.notify_agent_thinking.assert_called_once()
        mock_websocket_bridge.notify_tool_executing.assert_called_once()
        mock_websocket_bridge.notify_tool_completed.assert_called_once()
        mock_websocket_bridge.notify_agent_completed.assert_called_once()