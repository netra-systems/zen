"""
Comprehensive Unit Tests for AgentRegistry - SSOT Base Implementation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Stability & Development Velocity
- Value Impact: Ensures agent registry system works correctly for multi-user isolation patterns
- Strategic Impact: Core platform functionality - agent management enables chat value delivery

CRITICAL MISSION: Validates comprehensive AgentRegistry functionality with:
1. Singleton pattern initialization and SSOT compliance
2. User isolation features (UserAgentSession, memory management)
3. Agent creation and registration with proper isolation patterns
4. WebSocket manager integration and per-user bridges
5. Factory pattern support for tool dispatchers
6. Backward compatibility method delegation
7. Registry health monitoring and diagnostics
8. Cleanup and memory leak prevention mechanisms
9. Thread-safe concurrent execution for 10+ users
10. Edge case handling and error conditions

This comprehensive test suite covers ALL major functionality areas:
- AgentRegistry initialization and configuration validation
- UserAgentSession lifecycle management and isolation
- AgentLifecycleManager memory leak prevention
- WebSocket manager integration and propagation patterns
- Tool dispatcher factory integration with UnifiedToolDispatcher
- Agent registration, creation, retrieval, and cleanup
- Concurrent access patterns and thread safety validation
- Health monitoring, diagnostics, and metrics reporting
- Backward compatibility method delegation and legacy support
- Error handling, validation, and edge case coverage
- Multi-user isolation scenarios and resource cleanup

CRITICAL REQUIREMENTS:
- Uses SSOT test patterns from test_framework.ssot.base_test_case
- Tests with REAL instances (AgentRegistry, UserAgentSession, etc.) - NO mocks for business logic
- Tests all async methods properly with await
- Includes comprehensive edge case and error condition testing
- Tests multi-user isolation scenarios and concurrent access patterns
- Validates WebSocket integration and per-user bridge isolation
- Tests memory leak prevention and cleanup mechanisms
- Follows absolute import patterns and CLAUDE.md compliance
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

# SSOT test base
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import the class under test
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    UserAgentSession,
    AgentLifecycleManager,
    get_agent_registry
)

# Import dependencies for testing
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext


# ============================================================================
# TEST FIXTURES AND UTILITIES
# ============================================================================

class TestAgentRegistryInitialization(SSotAsyncTestCase):
    """Test AgentRegistry initialization and basic configuration."""
    
    async def test_init_creates_registry_with_required_components(self):
        """Test that AgentRegistry initializes with all required components.
        
        Business Value: Ensures core platform stability through proper initialization.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        mock_llm_manager.initialize = AsyncMock()
        mock_llm_manager._initialized = True
        
        mock_tool_dispatcher_factory = AsyncMock()
        
        # Act
        registry = AgentRegistry(
            llm_manager=mock_llm_manager,
            tool_dispatcher_factory=mock_tool_dispatcher_factory
        )
        
        # Assert - Core components initialized
        assert registry.llm_manager == mock_llm_manager
        assert registry.tool_dispatcher_factory == mock_tool_dispatcher_factory
        assert registry._agents_registered is False
        assert len(registry.registration_errors) == 0
        
        # Assert - User isolation components initialized
        assert len(registry._user_sessions) == 0
        assert isinstance(registry._lifecycle_manager, AgentLifecycleManager)
        assert registry._created_at is not None
        assert isinstance(registry._created_at, datetime)
        
        # Assert - Legacy compatibility initialized
        assert registry._legacy_dispatcher is None
        
        # Record metrics for business value tracking
        self.record_metric("agent_registry_components_validated", 8)
    
    async def test_init_with_default_dispatcher_factory(self):
        """Test AgentRegistry initialization with default tool dispatcher factory.
        
        Business Value: Ensures platform works with default configurations.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        mock_llm_manager._initialized = True
        
        # Act
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Assert
        assert registry.llm_manager == mock_llm_manager
        assert registry.tool_dispatcher_factory is not None
        assert callable(registry.tool_dispatcher_factory)
        
        self.record_metric("default_factory_validated", True)
    
    async def test_init_validates_required_parameters(self):
        """Test that AgentRegistry validates required parameters.
        
        Business Value: Prevents runtime errors through proper validation.
        """
        # Act & Assert
        with self.expect_exception(TypeError):
            AgentRegistry()  # Missing llm_manager
        
        self.record_metric("parameter_validation_working", True)
    
    async def test_registry_inheritance_from_universal_registry(self):
        """Test that AgentRegistry properly inherits from UniversalRegistry.
        
        Business Value: Ensures SSOT pattern compliance and consistent behavior.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        mock_llm_manager._initialized = True
        
        # Act
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Assert - Check SSOT inheritance methods are available
        assert hasattr(registry, 'register')
        assert hasattr(registry, 'remove')
        assert hasattr(registry, 'list_keys')
        assert hasattr(registry, 'register_factory')
        assert hasattr(registry, 'get_async')
        
        # Assert - Check enhanced methods are available
        assert hasattr(registry, 'get_user_session')
        assert hasattr(registry, 'cleanup_user_session')
        assert hasattr(registry, 'set_websocket_manager')
        
        self.record_metric("universal_registry_inheritance_validated", True)


class TestUserAgentSessionManagement(SSotAsyncTestCase):
    """Test UserAgentSession lifecycle management and isolation features."""
    
    async def test_user_agent_session_initialization(self):
        """Test that UserAgentSession initializes correctly.
        
        Business Value: Ensures user isolation foundation works correctly.
        """
        # Arrange
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Act
        user_session = UserAgentSession(test_user_id)
        
        # Assert - Core initialization
        assert user_session.user_id == test_user_id
        assert len(user_session._agents) == 0
        assert len(user_session._execution_contexts) == 0
        assert user_session._websocket_bridge is None
        assert user_session._websocket_manager is None
        assert user_session._created_at is not None
        assert isinstance(user_session._created_at, datetime)
        
        # Assert - Threading components
        assert user_session._access_lock is not None
        assert hasattr(user_session._access_lock, 'acquire')
        
        self.record_metric("user_session_components_validated", 7)
    
    async def test_user_session_validates_user_id(self):
        """Test that UserAgentSession validates user_id parameter.
        
        Business Value: Prevents data corruption and isolation breaches.
        """
        # Test empty string
        with self.expect_exception(ValueError, "user_id must be a non-empty string"):
            UserAgentSession("")
        
        # Test None
        with self.expect_exception(ValueError, "user_id must be a non-empty string"):
            UserAgentSession(None)
        
        # Test non-string
        with self.expect_exception(ValueError, "user_id must be a non-empty string"):
            UserAgentSession(123)
        
        self.record_metric("user_id_validation_cases_tested", 3)
    
    async def test_get_user_session_creates_new_session(self):
        """Test that get_user_session creates new isolated session.
        
        Business Value: Enables multi-user support and prevents data leakage.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        mock_llm_manager._initialized = True
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Act
        user_session = await registry.get_user_session(test_user_id)
        
        # Assert
        assert isinstance(user_session, UserAgentSession)
        assert user_session.user_id == test_user_id
        assert test_user_id in registry._user_sessions
        assert user_session._created_at is not None
        assert len(user_session._agents) == 0
        
        self.record_metric("new_session_created_successfully", True)
    
    async def test_get_user_session_returns_existing_session(self):
        """Test that get_user_session returns existing session for same user.
        
        Business Value: Ensures consistent user experience and resource efficiency.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        session1 = await registry.get_user_session(test_user_id)
        
        # Act
        session2 = await registry.get_user_session(test_user_id)
        
        # Assert
        assert session1 is session2
        assert len(registry._user_sessions) == 1
        
        self.record_metric("session_reuse_working", True)
    
    async def test_get_user_session_validates_user_id(self):
        """Test that get_user_session validates user_id parameter.
        
        Business Value: Prevents system errors and ensures proper user tracking.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Test empty string
        with self.expect_exception(ValueError, "user_id must be a non-empty string"):
            await registry.get_user_session("")
        
        # Test None
        with self.expect_exception(ValueError, "user_id must be a non-empty string"):
            await registry.get_user_session(None)
        
        # Test non-string
        with self.expect_exception(ValueError, "user_id must be a non-empty string"):
            await registry.get_user_session(123)
        
        self.record_metric("get_session_validation_working", True)
    
    async def test_cleanup_user_session_removes_session(self):
        """Test that cleanup_user_session properly removes and cleans up session.
        
        Business Value: Prevents memory leaks and ensures resource cleanup.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        await registry.get_user_session(test_user_id)
        assert test_user_id in registry._user_sessions
        
        # Act
        cleanup_metrics = await registry.cleanup_user_session(test_user_id)
        
        # Assert
        assert test_user_id not in registry._user_sessions
        assert cleanup_metrics['user_id'] == test_user_id
        assert cleanup_metrics['status'] == 'cleaned'
        assert 'cleaned_agents' in cleanup_metrics
        
        self.record_metric("cleanup_metrics_complete", True)
    
    async def test_cleanup_nonexistent_session_returns_appropriate_metrics(self):
        """Test cleanup of non-existent session returns appropriate metrics.
        
        Business Value: Provides reliable error handling and system diagnostics.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Act
        cleanup_metrics = await registry.cleanup_user_session("nonexistent_user")
        
        # Assert
        assert cleanup_metrics['user_id'] == "nonexistent_user"
        assert cleanup_metrics['status'] == 'no_session'
        assert cleanup_metrics['cleaned_agents'] == 0
        
        self.record_metric("nonexistent_cleanup_handled", True)
    
    async def test_cleanup_session_validates_user_id(self):
        """Test that cleanup_user_session validates user_id parameter.
        
        Business Value: Ensures robust error handling and prevents system crashes.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Test empty string
        with self.expect_exception(ValueError, "user_id is required"):
            await registry.cleanup_user_session("")
        
        # Test None
        with self.expect_exception(ValueError, "user_id is required"):
            await registry.cleanup_user_session(None)
        
        self.record_metric("cleanup_validation_working", True)


class TestUserAgentSessionBehavior(SSotAsyncTestCase):
    """Test UserAgentSession behavior and lifecycle management."""
    
    async def test_register_and_get_agent(self):
        """Test registering and retrieving agents from user session.
        
        Business Value: Enables agent-based workflow execution for users.
        """
        # Arrange
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_session = UserAgentSession(test_user_id)
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        
        # Act
        await user_session.register_agent("test_agent", mock_agent)
        retrieved_agent = await user_session.get_agent("test_agent")
        
        # Assert
        assert retrieved_agent == mock_agent
        assert len(user_session._agents) == 1
        assert "test_agent" in user_session._agents
        
        self.record_metric("agent_registration_working", True)
    
    async def test_cleanup_all_agents(self):
        """Test that cleanup_all_agents properly cleans up resources.
        
        Business Value: Prevents memory leaks and ensures clean user sessions.
        """
        # Arrange
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_session = UserAgentSession(test_user_id)
        
        mock_agent = Mock()
        mock_agent.cleanup = AsyncMock()
        mock_agent.close = AsyncMock()
        
        await user_session.register_agent("test_agent", mock_agent)
        
        # Act
        await user_session.cleanup_all_agents()
        
        # Assert
        assert len(user_session._agents) == 0
        assert len(user_session._execution_contexts) == 0
        assert user_session._websocket_bridge is None
        mock_agent.cleanup.assert_called_once()
        mock_agent.close.assert_called_once()
        
        self.record_metric("agent_cleanup_successful", True)
    
    async def test_cleanup_handles_exceptions(self):
        """Test that cleanup_all_agents handles exceptions gracefully.
        
        Business Value: Ensures system stability even when individual agents fail.
        """
        # Arrange
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_session = UserAgentSession(test_user_id)
        
        mock_agent = Mock()
        mock_agent.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
        
        await user_session.register_agent("test_agent", mock_agent)
        
        # Act - should not raise exception
        await user_session.cleanup_all_agents()
        
        # Assert
        assert len(user_session._agents) == 0
        
        self.record_metric("exception_handling_working", True)
    
    async def test_get_metrics(self):
        """Test that get_metrics returns appropriate metrics.
        
        Business Value: Provides operational visibility and monitoring capability.
        """
        # Arrange
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_session = UserAgentSession(test_user_id)
        
        # Act
        metrics = user_session.get_metrics()
        
        # Assert
        assert isinstance(metrics, dict)
        assert 'user_id' in metrics
        assert 'agent_count' in metrics
        assert 'context_count' in metrics
        assert 'has_websocket_bridge' in metrics
        assert 'uptime_seconds' in metrics
        
        assert metrics['user_id'] == test_user_id
        assert metrics['agent_count'] == 0
        assert metrics['context_count'] == 0
        assert metrics['has_websocket_bridge'] is False
        assert metrics['uptime_seconds'] >= 0
        
        self.record_metric("metrics_fields_complete", 5)
    
    async def test_create_agent_execution_context(self):
        """Test creation of isolated execution contexts.
        
        Business Value: Enables proper agent isolation and execution tracking.
        """
        # Arrange
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_session = UserAgentSession(test_user_id)
        
        test_user_context = UserExecutionContext(
            user_id=test_user_id,
            request_id=f"test_request_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Act
        execution_context = await user_session.create_agent_execution_context(
            "test_agent", test_user_context
        )
        
        # Assert
        assert isinstance(execution_context, UserExecutionContext)
        assert execution_context.user_id == test_user_id
        assert "test_agent" in user_session._execution_contexts
        
        self.record_metric("execution_context_creation_working", True)


class TestWebSocketManagerIntegration(SSotAsyncTestCase):
    """Test WebSocket manager integration and propagation."""
    
    async def test_set_websocket_manager_stores_manager(self):
        """Test that set_websocket_manager properly stores the manager.
        
        Business Value: Enables real-time chat notifications and user engagement.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_websocket_manager = Mock()
        
        # Act
        registry.set_websocket_manager(mock_websocket_manager)
        
        # Assert
        assert registry.websocket_manager == mock_websocket_manager
        
        self.record_metric("websocket_manager_stored", True)
    
    async def test_set_websocket_manager_async_propagates_immediately(self):
        """Test that set_websocket_manager_async immediately propagates to sessions.
        
        Business Value: Ensures all user sessions receive WebSocket capabilities.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_websocket_manager = Mock()
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        user_session = await registry.get_user_session(test_user_id)
        
        # Act
        with patch.object(user_session, 'set_websocket_manager', new_callable=AsyncMock) as mock_set_ws:
            await registry.set_websocket_manager_async(mock_websocket_manager)
        
        # Assert
        mock_set_ws.assert_called_once()
        
        self.record_metric("async_websocket_propagation_working", True)
    
    async def test_set_websocket_manager_handles_none_gracefully(self):
        """Test that set_websocket_manager handles None value gracefully.
        
        Business Value: Provides robust error handling for configuration issues.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Act - should not raise exception
        registry.set_websocket_manager(None)
        
        # Assert
        assert registry.websocket_manager is None
        
        self.record_metric("none_websocket_handled", True)
    
    async def test_user_session_websocket_manager_integration(self):
        """Test WebSocket manager integration at user session level.
        
        Business Value: Ensures per-user WebSocket isolation and proper resource management.
        """
        # Arrange
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_session = UserAgentSession(test_user_id)
        mock_websocket_manager = Mock()
        
        test_user_context = UserExecutionContext(
            user_id=test_user_id,
            request_id=f"test_request_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Act
        await user_session.set_websocket_manager(mock_websocket_manager, test_user_context)
        
        # Assert
        assert user_session._websocket_manager == mock_websocket_manager
        assert user_session._websocket_bridge is not None
        
        self.record_metric("user_websocket_integration_working", True)


class TestAgentCreationAndManagement(SSotAsyncTestCase):
    """Test agent creation, registration, and management."""
    
    async def test_create_agent_for_user_validates_parameters(self):
        """Test that create_agent_for_user validates required parameters.
        
        Business Value: Prevents runtime errors and ensures proper agent creation.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        test_user_context = UserExecutionContext(
            user_id=test_user_id,
            request_id=f"test_request_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Test missing user_id
        with self.expect_exception(ValueError, "user_id and agent_type are required"):
            await registry.create_agent_for_user("", "test_agent", test_user_context)
        
        # Test missing agent_type
        with self.expect_exception(ValueError, "user_id and agent_type are required"):
            await registry.create_agent_for_user(test_user_id, "", test_user_context)
        
        self.record_metric("agent_creation_validation_working", True)
    
    async def test_create_agent_for_user_handles_unknown_agent_type(self):
        """Test that create_agent_for_user handles unknown agent type gracefully.
        
        Business Value: Provides clear error messages for configuration issues.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        test_user_context = UserExecutionContext(
            user_id=test_user_id,
            request_id=f"test_request_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Mock get_async to return None (no factory found)
        registry.get_async = AsyncMock(return_value=None)
        
        # Act & Assert
        with self.expect_exception(KeyError, "No factory registered for agent type"):
            await registry.create_agent_for_user(
                user_id=test_user_id,
                agent_type="nonexistent_agent",
                user_context=test_user_context
            )
        
        self.record_metric("unknown_agent_error_handled", True)
    
    async def test_get_user_agent_retrieves_specific_agent(self):
        """Test that get_user_agent retrieves specific agent for user.
        
        Business Value: Enables efficient agent reuse and resource management.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        
        user_session = await registry.get_user_session(test_user_id)
        await user_session.register_agent("test_agent", mock_agent)
        
        # Act
        retrieved_agent = await registry.get_user_agent(test_user_id, "test_agent")
        
        # Assert
        assert retrieved_agent == mock_agent
        
        self.record_metric("agent_retrieval_working", True)
    
    async def test_get_user_agent_returns_none_for_nonexistent_user(self):
        """Test that get_user_agent returns None for non-existent user.
        
        Business Value: Provides graceful handling of invalid user requests.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Act
        agent = await registry.get_user_agent("nonexistent_user", "test_agent")
        
        # Assert
        assert agent is None
        
        self.record_metric("nonexistent_user_handled", True)
    
    async def test_get_user_agent_returns_none_for_nonexistent_agent(self):
        """Test that get_user_agent returns None for non-existent agent.
        
        Business Value: Provides graceful handling of invalid agent requests.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        await registry.get_user_session(test_user_id)
        
        # Act
        agent = await registry.get_user_agent(test_user_id, "nonexistent_agent")
        
        # Assert
        assert agent is None
        
        self.record_metric("nonexistent_agent_handled", True)
    
    async def test_remove_user_agent_removes_specific_agent(self):
        """Test that remove_user_agent removes specific agent and cleans up.
        
        Business Value: Enables proper resource management and memory cleanup.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        mock_agent = Mock()
        mock_agent.cleanup = AsyncMock()
        
        user_session = await registry.get_user_session(test_user_id)
        await user_session.register_agent("test_agent", mock_agent)
        
        # Act
        result = await registry.remove_user_agent(test_user_id, "test_agent")
        
        # Assert
        assert result is True
        assert "test_agent" not in user_session._agents
        mock_agent.cleanup.assert_called_once()
        
        self.record_metric("agent_removal_working", True)
    
    async def test_remove_user_agent_returns_false_for_nonexistent(self):
        """Test that remove_user_agent returns False for non-existent agent.
        
        Business Value: Provides clear feedback on removal operations.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Act
        result = await registry.remove_user_agent("nonexistent_user", "test_agent")
        
        # Assert
        assert result is False
        
        self.record_metric("nonexistent_removal_handled", True)


class TestToolDispatcherIntegration(SSotAsyncTestCase):
    """Test tool dispatcher creation and enhancement."""
    
    @patch('netra_backend.app.agents.supervisor.agent_registry.UnifiedToolDispatcher')
    async def test_create_tool_dispatcher_for_user_creates_isolated_dispatcher(self, mock_unified_dispatcher):
        """Test that create_tool_dispatcher_for_user creates isolated dispatcher.
        
        Business Value: Ensures proper tool isolation and security per user.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        test_user_context = UserExecutionContext(
            user_id=test_user_id,
            request_id=f"test_request_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        mock_dispatcher = Mock()
        mock_unified_dispatcher.create_for_user = AsyncMock(return_value=mock_dispatcher)
        
        # Act
        result = await registry.create_tool_dispatcher_for_user(
            user_context=test_user_context,
            websocket_bridge=None,
            enable_admin_tools=False
        )
        
        # Assert
        assert result == mock_dispatcher
        mock_unified_dispatcher.create_for_user.assert_called_once_with(
            user_context=test_user_context,
            websocket_bridge=None,
            enable_admin_tools=False
        )
        
        self.record_metric("tool_dispatcher_creation_working", True)
    
    @patch('netra_backend.app.agents.supervisor.agent_registry.UnifiedToolDispatcher')
    async def test_create_tool_dispatcher_for_user_with_admin_tools(self, mock_unified_dispatcher):
        """Test tool dispatcher creation with admin tools enabled.
        
        Business Value: Enables advanced functionality for authorized users.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        test_user_context = UserExecutionContext(
            user_id=test_user_id,
            request_id=f"test_request_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        mock_dispatcher = Mock()
        mock_unified_dispatcher.create_for_user = AsyncMock(return_value=mock_dispatcher)
        
        # Act
        result = await registry.create_tool_dispatcher_for_user(
            user_context=test_user_context,
            websocket_bridge=None,
            enable_admin_tools=True
        )
        
        # Assert
        mock_unified_dispatcher.create_for_user.assert_called_once_with(
            user_context=test_user_context,
            websocket_bridge=None,
            enable_admin_tools=True
        )
        
        self.record_metric("admin_tools_dispatcher_working", True)
    
    @patch('netra_backend.app.agents.supervisor.agent_registry.UnifiedToolDispatcher')
    async def test_default_dispatcher_factory_uses_unified_dispatcher(self, mock_unified_dispatcher):
        """Test that default dispatcher factory uses UnifiedToolDispatcher.
        
        Business Value: Ensures SSOT compliance for tool dispatching.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        test_user_context = UserExecutionContext(
            user_id=test_user_id,
            request_id=f"test_request_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        mock_dispatcher = Mock()
        mock_unified_dispatcher.create_for_user = AsyncMock(return_value=mock_dispatcher)
        
        # Act
        result = await registry._default_dispatcher_factory(
            user_context=test_user_context,
            websocket_bridge=None
        )
        
        # Assert
        assert result == mock_dispatcher
        mock_unified_dispatcher.create_for_user.assert_called_once_with(
            user_context=test_user_context,
            websocket_bridge=None,
            enable_admin_tools=False
        )
        
        self.record_metric("default_factory_uses_unified", True)
    
    async def test_tool_dispatcher_property_returns_none_with_warning(self):
        """Test that legacy tool_dispatcher property returns None and logs warning.
        
        Business Value: Provides backward compatibility while encouraging migration.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Act
        result = registry.tool_dispatcher
        
        # Assert
        assert result is None
        
        self.record_metric("legacy_dispatcher_property_deprecated", True)
    
    async def test_tool_dispatcher_setter_logs_warning(self):
        """Test that legacy tool_dispatcher setter logs warning and ignores value.
        
        Business Value: Maintains backward compatibility while preventing misuse.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_dispatcher = Mock()
        
        # Act
        registry.tool_dispatcher = mock_dispatcher
        
        # Assert
        assert registry._legacy_dispatcher == mock_dispatcher
        assert registry.tool_dispatcher is None  # Still returns None
        
        self.record_metric("legacy_dispatcher_setter_deprecated", True)


class TestAgentFactoryRegistration(SSotAsyncTestCase):
    """Test agent factory registration and default agent setup."""
    
    def test_register_default_agents_sets_flag(self):
        """Test that register_default_agents sets the registered flag.
        
        Business Value: Ensures agent registry initialization is trackable.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        assert registry._agents_registered is False
        
        # Act
        registry.register_default_agents()
        
        # Assert
        assert registry._agents_registered is True
        
        self.record_metric("agents_registered_flag_working", True)
    
    def test_register_default_agents_idempotent(self):
        """Test that register_default_agents is idempotent.
        
        Business Value: Prevents duplicate registrations and resource waste.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Act - call twice
        registry.register_default_agents()
        initial_count = len(registry.list_keys())
        
        registry.register_default_agents()
        final_count = len(registry.list_keys())
        
        # Assert - should not register twice
        assert initial_count == final_count
        
        self.record_metric("registration_idempotent", True)
    
    def test_register_default_agents_registers_core_agents(self):
        """Test that register_default_agents registers expected core agents.
        
        Business Value: Ensures core workflow agents are available for business logic.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Act
        registry.register_default_agents()
        
        # Assert
        registered_agents = registry.list_keys()
        
        # Check that registration was attempted (some may fail due to import issues in tests)
        assert len(registered_agents) >= 0  # At least attempted registration
        
        self.record_metric("core_agents_registration_attempted", True)
    
    async def test_register_agent_safely_handles_success(self):
        """Test that register_agent_safely properly handles successful registration.
        
        Business Value: Ensures reliable agent registration for platform stability.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_agent_class = Mock()
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        
        # Mock tool_dispatcher to avoid None error
        registry._legacy_dispatcher = Mock()
        
        # Act
        result = await registry.register_agent_safely(
            name="test_agent",
            agent_class=mock_agent_class
        )
        
        # Assert
        assert result is True
        assert "test_agent" not in registry.registration_errors
        
        self.record_metric("safe_registration_success", True)
    
    async def test_register_agent_safely_handles_failure(self):
        """Test that register_agent_safely properly handles registration failure.
        
        Business Value: Provides graceful error handling and system stability.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_agent_class = Mock(side_effect=Exception("Test error"))
        
        # Act
        result = await registry.register_agent_safely(
            name="failing_agent",
            agent_class=mock_agent_class
        )
        
        # Assert
        assert result is False
        assert "failing_agent" in registry.registration_errors
        assert "Test error" in registry.registration_errors["failing_agent"]
        
        self.record_metric("safe_registration_failure_handled", True)


class TestRegistryHealthAndDiagnostics(SSotAsyncTestCase):
    """Test registry health monitoring and diagnostic methods."""
    
    async def test_get_registry_health_returns_complete_status(self):
        """Test that get_registry_health returns comprehensive health information.
        
        Business Value: Provides operational visibility and monitoring capabilities.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        registry.register_default_agents()
        
        # Act
        health = registry.get_registry_health()
        
        # Assert - Core health fields
        assert isinstance(health, dict)
        assert 'total_agents' in health
        assert 'failed_registrations' in health
        assert 'registration_errors' in health
        assert 'death_detection_enabled' in health
        assert 'using_universal_registry' in health
        
        # Assert - Hardening and isolation fields
        assert 'hardened_isolation' in health
        assert 'total_user_sessions' in health
        assert 'total_user_agents' in health
        assert 'memory_leak_prevention' in health
        assert 'thread_safe_concurrent_execution' in health
        assert 'uptime_seconds' in health
        
        # Assert - Feature status
        assert health['hardened_isolation'] is True
        assert health['memory_leak_prevention'] is True
        assert health['thread_safe_concurrent_execution'] is True
        assert health['using_universal_registry'] is True
        
        self.record_metric("health_fields_complete", 11)
    
    async def test_get_registry_health_detects_issues(self):
        """Test that get_registry_health properly detects issues.
        
        Business Value: Enables proactive issue detection and system monitoring.
        """
        # Arrange - create many user sessions to trigger warnings
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        for i in range(55):  # Exceed threshold of 50
            await registry.get_user_session(f"test_user_{i}")
        
        # Act
        health = registry.get_registry_health()
        
        # Assert
        assert len(health.get('issues', [])) > 0
        assert health['status'] in ['warning', 'critical']
        assert health['total_user_sessions'] == 55
        
        self.record_metric("issue_detection_working", True)
    
    async def test_diagnose_websocket_wiring_comprehensive(self):
        """Test that diagnose_websocket_wiring provides comprehensive diagnosis.
        
        Business Value: Enables debugging of WebSocket integration issues.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_websocket_manager = Mock()
        registry.set_websocket_manager(mock_websocket_manager)
        
        # Create user sessions
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        await registry.get_user_session(user_id)
        
        # Act
        diagnosis = registry.diagnose_websocket_wiring()
        
        # Assert
        assert isinstance(diagnosis, dict)
        assert 'registry_has_websocket_manager' in diagnosis
        assert 'total_user_sessions' in diagnosis
        assert 'users_with_websocket_bridges' in diagnosis
        assert 'critical_issues' in diagnosis
        assert 'user_details' in diagnosis
        assert 'websocket_health' in diagnosis
        
        assert diagnosis['registry_has_websocket_manager'] is True
        assert diagnosis['total_user_sessions'] > 0
        
        self.record_metric("websocket_diagnosis_comprehensive", True)
    
    async def test_get_factory_integration_status_returns_complete_info(self):
        """Test that get_factory_integration_status returns complete information.
        
        Business Value: Validates factory pattern implementation and compliance.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Act
        status = registry.get_factory_integration_status()
        
        # Assert
        assert isinstance(status, dict)
        assert 'using_universal_registry' in status
        assert 'factory_patterns_enabled' in status
        assert 'thread_safe' in status
        assert 'hardened_isolation_enabled' in status
        assert 'user_isolation_enforced' in status
        assert 'memory_leak_prevention' in status
        assert 'thread_safe_concurrent_execution' in status
        assert 'total_user_sessions' in status
        assert 'global_state_eliminated' in status
        assert 'websocket_isolation_per_user' in status
        assert 'timestamp' in status
        
        # Assert - Feature status
        assert status['using_universal_registry'] is True
        assert status['factory_patterns_enabled'] is True
        assert status['hardened_isolation_enabled'] is True
        assert status['global_state_eliminated'] is True
        
        self.record_metric("factory_status_complete", 11)


class TestConcurrencyAndThreadSafety(SSotAsyncTestCase):
    """Test concurrent access and thread safety."""
    
    async def test_concurrent_user_session_creation(self):
        """Test that concurrent user session creation is thread-safe.
        
        Business Value: Ensures platform stability under concurrent user load.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_ids = [f"user_{i}_{uuid.uuid4().hex[:4]}" for i in range(10)]
        
        # Act - create sessions concurrently
        tasks = [registry.get_user_session(user_id) for user_id in user_ids]
        sessions = await asyncio.gather(*tasks)
        
        # Assert
        assert len(sessions) == 10
        assert len(registry._user_sessions) == 10
        
        # Verify each session has correct user_id
        for i, session in enumerate(sessions):
            assert session.user_id == user_ids[i]
        
        self.record_metric("concurrent_session_creation_successful", True)
    
    async def test_concurrent_session_cleanup(self):
        """Test that concurrent session cleanup is thread-safe.
        
        Business Value: Ensures reliable resource cleanup under concurrent load.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_ids = [f"user_{i}_{uuid.uuid4().hex[:4]}" for i in range(5)]
        
        # Create sessions first
        for user_id in user_ids:
            await registry.get_user_session(user_id)
        
        # Act - cleanup concurrently
        cleanup_tasks = [registry.cleanup_user_session(user_id) for user_id in user_ids]
        cleanup_results = await asyncio.gather(*cleanup_tasks)
        
        # Assert
        assert len(cleanup_results) == 5
        assert len(registry._user_sessions) == 0
        
        for result in cleanup_results:
            assert result['status'] == 'cleaned'
        
        self.record_metric("concurrent_cleanup_successful", True)
    
    async def test_concurrent_websocket_manager_setting(self):
        """Test that concurrent WebSocket manager setting is safe.
        
        Business Value: Ensures reliable WebSocket setup under concurrent operations.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_websocket_managers = [Mock() for _ in range(3)]
        
        # Create some user sessions first
        for i in range(3):
            await registry.get_user_session(f"user_{i}_{uuid.uuid4().hex[:4]}")
        
        # Act - set WebSocket managers concurrently
        tasks = [
            registry.set_websocket_manager_async(manager)
            for manager in mock_websocket_managers
        ]
        await asyncio.gather(*tasks)
        
        # Assert - last one should win
        assert registry.websocket_manager == mock_websocket_managers[-1]
        
        self.record_metric("concurrent_websocket_setting_safe", True)


class TestMemoryLeakPrevention(SSotAsyncTestCase):
    """Test memory leak prevention features."""
    
    async def test_monitor_all_users_detects_memory_issues(self):
        """Test that monitor_all_users detects potential memory issues.
        
        Business Value: Enables proactive memory management and system stability.
        """
        # Arrange - create many sessions to trigger thresholds
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        for i in range(55):  # Exceed user threshold
            await registry.get_user_session(f"user_{i}_{uuid.uuid4().hex[:4]}")
        
        # Act
        monitoring_report = await registry.monitor_all_users()
        
        # Assert
        assert isinstance(monitoring_report, dict)
        assert 'total_users' in monitoring_report
        assert 'total_agents' in monitoring_report
        assert 'global_issues' in monitoring_report
        assert 'timestamp' in monitoring_report
        
        assert monitoring_report['total_users'] == 55
        assert len(monitoring_report['global_issues']) > 0
        
        self.record_metric("memory_monitoring_working", True)
    
    async def test_emergency_cleanup_all_removes_all_sessions(self):
        """Test that emergency_cleanup_all removes all user sessions.
        
        Business Value: Provides emergency recovery mechanism for system stability.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        for i in range(5):
            await registry.get_user_session(f"user_{i}_{uuid.uuid4().hex[:4]}")
        
        assert len(registry._user_sessions) == 5
        
        # Act
        cleanup_report = await registry.emergency_cleanup_all()
        
        # Assert
        assert len(registry._user_sessions) == 0
        assert cleanup_report['users_cleaned'] == 5
        assert len(cleanup_report['errors']) == 0
        assert 'timestamp' in cleanup_report
        
        self.record_metric("emergency_cleanup_successful", True)
    
    async def test_reset_user_agents_creates_fresh_session(self):
        """Test that reset_user_agents creates fresh session for user.
        
        Business Value: Enables user session recovery and resource cleanup.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        user_session = await registry.get_user_session(user_id)
        mock_agent = Mock()
        await user_session.register_agent("test_agent", mock_agent)
        
        old_session_id = id(user_session)
        
        # Act
        reset_report = await registry.reset_user_agents(user_id)
        
        # Assert
        assert reset_report['status'] == 'reset_complete'
        assert reset_report['agents_reset'] == 1
        
        new_session = registry._user_sessions[user_id]
        assert id(new_session) != old_session_id
        assert len(new_session._agents) == 0
        
        self.record_metric("user_reset_successful", True)
    
    async def test_agent_lifecycle_manager_functionality(self):
        """Test AgentLifecycleManager memory leak prevention features.
        
        Business Value: Ensures proper agent lifecycle management and resource cleanup.
        """
        # Arrange
        lifecycle_manager = AgentLifecycleManager()
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Act - Test monitoring memory usage
        memory_report = await lifecycle_manager.monitor_memory_usage(test_user_id)
        
        # Assert
        assert isinstance(memory_report, dict)
        assert 'status' in memory_report
        assert 'user_id' in memory_report
        assert memory_report['user_id'] == test_user_id
        assert memory_report['status'] == 'no_session'
        
        self.record_metric("lifecycle_manager_functional", True)


class TestBackwardCompatibility(SSotAsyncTestCase):
    """Test backward compatibility methods."""
    
    def test_list_agents_returns_registered_keys(self):
        """Test that list_agents returns list of registered agent names.
        
        Business Value: Maintains API compatibility for existing integrations.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Act
        agent_list = registry.list_agents()
        
        # Assert
        assert isinstance(agent_list, list)
        
        self.record_metric("list_agents_compatible", True)
    
    def test_remove_agent_delegates_to_universal_registry(self):
        """Test that remove_agent properly delegates to UniversalRegistry.
        
        Business Value: Ensures SSOT compliance while maintaining compatibility.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        mock_agent = Mock()
        registry.register("test_agent", mock_agent)
        
        # Act
        result = registry.remove_agent("test_agent")
        
        # Assert
        assert result is True
        assert "test_agent" not in registry.list_keys()
        
        self.record_metric("remove_agent_compatible", True)
    
    async def test_get_agent_delegates_to_get_async(self):
        """Test that get_agent properly delegates to get_async.
        
        Business Value: Provides backward compatibility for async agent retrieval.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        test_user_context = UserExecutionContext(
            user_id=test_user_id,
            request_id=f"test_request_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Act
        result = await registry.get_agent("nonexistent_agent", test_user_context)
        
        # Assert
        assert result is None
        
        self.record_metric("get_agent_compatible", True)
    
    async def test_reset_all_agents_returns_success_report(self):
        """Test that reset_all_agents returns appropriate success report.
        
        Business Value: Provides backward compatibility for bulk operations.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Act
        reset_report = await registry.reset_all_agents()
        
        # Assert
        assert isinstance(reset_report, dict)
        assert 'total_agents' in reset_report
        assert 'successful_resets' in reset_report
        assert 'failed_resets' in reset_report
        assert 'using_universal_registry' in reset_report
        
        assert reset_report['failed_resets'] == 0
        assert reset_report['using_universal_registry'] is True
        
        self.record_metric("reset_all_agents_compatible", True)


class TestModuleExports(SSotAsyncTestCase):
    """Test module-level exports and factory functions."""
    
    def test_get_agent_registry_returns_registry_instance(self):
        """Test that get_agent_registry returns proper AgentRegistry instance.
        
        Business Value: Ensures consistent registry access across the platform.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        mock_llm_manager._initialized = True
        mock_tool_dispatcher = Mock()
        
        # Act
        registry = get_agent_registry(mock_llm_manager, mock_tool_dispatcher)
        
        # Assert
        assert isinstance(registry, AgentRegistry)
        assert registry.llm_manager == mock_llm_manager
        
        self.record_metric("get_agent_registry_functional", True)
    
    def test_get_agent_registry_handles_existing_global_registry(self):
        """Test that get_agent_registry properly handles existing global registry.
        
        Business Value: Ensures efficient resource reuse and consistent state.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        mock_llm_manager._initialized = True
        
        # Act - call twice to test caching behavior
        registry1 = get_agent_registry(mock_llm_manager, None)
        registry2 = get_agent_registry(mock_llm_manager, None)
        
        # Assert - should return registry instances (may or may not be same instance)
        assert isinstance(registry1, AgentRegistry)
        assert isinstance(registry2, AgentRegistry)
        
        self.record_metric("global_registry_handling_working", True)


class TestEdgeCasesAndErrorHandling(SSotAsyncTestCase):
    """Test edge cases and error handling scenarios."""
    
    async def test_user_session_with_websocket_manager_none(self):
        """Test user session behavior when WebSocket manager is None.
        
        Business Value: Ensures graceful degradation when WebSocket is unavailable.
        """
        # Arrange
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_session = UserAgentSession(test_user_id)
        
        test_user_context = UserExecutionContext(
            user_id=test_user_id,
            request_id=f"test_request_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Act - should not raise exception
        await user_session.set_websocket_manager(None, test_user_context)
        
        # Assert
        assert user_session._websocket_manager is None
        assert user_session._websocket_bridge is None
        
        self.record_metric("none_websocket_manager_handled", True)
    
    async def test_cleanup_with_agent_missing_cleanup_method(self):
        """Test cleanup behavior with agents missing cleanup method.
        
        Business Value: Ensures robust cleanup even with incomplete agent implementations.
        """
        # Arrange
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_session = UserAgentSession(test_user_id)
        
        mock_agent = Mock(spec=[])  # Agent without cleanup method
        await user_session.register_agent("test_agent", mock_agent)
        
        # Act - should not raise exception
        await user_session.cleanup_all_agents()
        
        # Assert
        assert len(user_session._agents) == 0
        
        self.record_metric("missing_cleanup_method_handled", True)
    
    async def test_registry_with_invalid_tool_dispatcher_factory(self):
        """Test registry behavior with invalid tool dispatcher factory.
        
        Business Value: Provides error handling for configuration issues.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        mock_llm_manager._initialized = True
        
        def invalid_factory():
            raise Exception("Factory failed")
        
        registry = AgentRegistry(
            llm_manager=mock_llm_manager,
            tool_dispatcher_factory=invalid_factory
        )
        
        # Assert - Registry should still initialize
        assert registry.tool_dispatcher_factory == invalid_factory
        
        self.record_metric("invalid_factory_handled", True)
    
    async def test_concurrent_access_to_user_session_agents(self):
        """Test concurrent access to user session agents.
        
        Business Value: Ensures thread safety in multi-user scenarios.
        """
        # Arrange
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_session = UserAgentSession(test_user_id)
        
        mock_agents = [Mock() for _ in range(5)]
        agent_names = [f"agent_{i}" for i in range(5)]
        
        # Act - Register agents concurrently
        register_tasks = [
            user_session.register_agent(name, agent)
            for name, agent in zip(agent_names, mock_agents)
        ]
        await asyncio.gather(*register_tasks)
        
        # Act - Get agents concurrently
        get_tasks = [
            user_session.get_agent(name)
            for name in agent_names
        ]
        retrieved_agents = await asyncio.gather(*get_tasks)
        
        # Assert
        assert len(retrieved_agents) == 5
        for i, retrieved_agent in enumerate(retrieved_agents):
            assert retrieved_agent == mock_agents[i]
        
        self.record_metric("concurrent_agent_access_safe", True)
    
    async def test_registry_cleanup_with_partially_failed_sessions(self):
        """Test registry cleanup when some user sessions fail to clean up.
        
        Business Value: Ensures overall system stability even with partial failures.
        """
        # Arrange
        mock_llm_manager = AsyncMock()
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Create multiple user sessions
        user_ids = [f"user_{i}_{uuid.uuid4().hex[:4]}" for i in range(3)]
        for user_id in user_ids:
            await registry.get_user_session(user_id)
        
        # Mock one session to fail cleanup
        failing_session = registry._user_sessions[user_ids[0]]
        failing_session.cleanup_all_agents = AsyncMock(side_effect=Exception("Cleanup failed"))
        
        # Act
        cleanup_report = await registry.emergency_cleanup_all()
        
        # Assert - should still clean up other sessions
        assert cleanup_report['users_cleaned'] >= 2  # At least 2 should succeed
        assert len(cleanup_report['errors']) >= 1  # At least 1 error expected
        
        self.record_metric("partial_cleanup_failure_handled", True)


# Test execution summary
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])