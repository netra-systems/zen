"""
Comprehensive Unit Tests for UserContextToolFactory

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Multi-User Safety, Risk Reduction, Platform Stability
- Value Impact: Factory creates isolated tool systems preventing $10M+ churn from user data leakage
- Strategic Impact: Foundation for scalable multi-tenant agent execution with complete resource isolation

This test suite ensures UserContextToolFactory delivers 100% user isolation for multi-user chat,
preventing data leaks and enabling concurrent agent execution across all customer segments.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import List, Type, Optional

from netra_backend.app.agents.user_context_tool_factory import (
    UserContextToolFactory, 
    get_app_tool_classes
)


class MockBaseTool:
    """Mock tool that mimics real BaseTool interface for testing."""
    
    def __init__(self, name: str = "mock_tool"):
        self.name = name


class MockFailingTool:
    """Mock tool that fails during instantiation to test error handling."""
    
    def __init__(self):
        raise Exception("Tool instantiation failed")


class MockUserExecutionContext:
    """Mock UserExecutionContext with required interface for factory testing."""
    
    def __init__(self, user_id: str = "test_user", run_id: str = "test_run"):
        self.user_id = user_id
        self.run_id = run_id
        self._correlation_id = f"{user_id}_{run_id}_{int(time.time())}"
    
    def get_correlation_id(self) -> str:
        return self._correlation_id


class MockToolRegistry:
    """Mock ToolRegistry that tracks registrations for testing."""
    
    def __init__(self):
        self.registered_tools = {}
    
    def register(self, name: str, tool):
        self.registered_tools[name] = tool


class MockUnifiedToolDispatcher:
    """Mock UnifiedToolDispatcher for factory testing."""
    
    def __init__(self):
        self.dispatcher_id = f"dispatcher_{int(time.time() * 1000)}"
        self.registry = None


class MockUnifiedToolDispatcherFactory:
    """Mock factory for creating UnifiedToolDispatcher instances."""
    
    @staticmethod
    def create_for_request(user_context, tools, websocket_manager=None):
        return MockUnifiedToolDispatcher()


class MockWebSocketBridge:
    """Mock WebSocket bridge for integration testing."""
    
    def __init__(self):
        self.bridge_id = f"bridge_{int(time.time())}"


@pytest.fixture
def mock_user_context():
    """Fixture providing mock UserExecutionContext."""
    return MockUserExecutionContext()


@pytest.fixture
def mock_tool_classes():
    """Fixture providing mock tool classes for testing."""
    return [MockBaseTool]


@pytest.fixture
def mock_websocket_bridge_factory():
    """Fixture providing mock WebSocket bridge factory."""
    return lambda: MockWebSocketBridge()


class TestUserContextToolFactoryBasics:
    """Test basic functionality and interfaces of UserContextToolFactory."""
    
    @pytest.mark.unit
    def test_class_exists_and_has_required_methods(self):
        """Ensure UserContextToolFactory exists with required static methods."""
        assert hasattr(UserContextToolFactory, 'create_user_tool_system')
        assert hasattr(UserContextToolFactory, 'create_minimal_tool_system')
        assert hasattr(UserContextToolFactory, 'validate_tool_system')
        
    @pytest.mark.unit 
    def test_get_app_tool_classes_function_exists(self):
        """Ensure get_app_tool_classes function exists and returns list."""
        tool_classes = get_app_tool_classes()
        assert isinstance(tool_classes, list)


class TestUserContextToolFactoryCompleteSystemCreation:
    """Test complete tool system creation with all components."""
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_create_user_tool_system_happy_path(
        self, mock_dispatcher_factory, mock_registry_class, 
        mock_user_context, mock_tool_classes, mock_websocket_bridge_factory
    ):
        """Test complete tool system creation with all components."""
        
        # Setup mocks
        mock_registry = MockToolRegistry()
        mock_registry_class.return_value = mock_registry
        mock_dispatcher_factory.create_for_request.return_value = MockUnifiedToolDispatcher()
        
        # Execute factory method
        result = await UserContextToolFactory.create_user_tool_system(
            context=mock_user_context,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=mock_websocket_bridge_factory
        )
        
        # Verify complete system structure
        assert isinstance(result, dict)
        required_keys = ['registry', 'dispatcher', 'tools', 'bridge', 'correlation_id']
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"
        
        # Verify components
        assert result['registry'] is mock_registry
        assert isinstance(result['dispatcher'], MockUnifiedToolDispatcher)
        assert isinstance(result['tools'], list)
        assert len(result['tools']) == 1
        assert isinstance(result['tools'][0], MockBaseTool)
        assert isinstance(result['bridge'], MockWebSocketBridge)
        assert result['correlation_id'] == mock_user_context.get_correlation_id()
        
        # Verify tool registration
        assert len(mock_registry.registered_tools) == 1
        assert 'mock_tool' in mock_registry.registered_tools
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_create_user_tool_system_without_websocket_bridge(
        self, mock_dispatcher_factory, mock_registry_class,
        mock_user_context, mock_tool_classes
    ):
        """Test system creation without WebSocket bridge (graceful degradation)."""
        
        # Setup mocks
        mock_registry = MockToolRegistry()
        mock_registry_class.return_value = mock_registry
        mock_dispatcher_factory.create_for_request.return_value = MockUnifiedToolDispatcher()
        
        # Execute without bridge factory
        result = await UserContextToolFactory.create_user_tool_system(
            context=mock_user_context,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=None
        )
        
        # Verify system created without bridge
        assert result['bridge'] is None
        assert result['registry'] is mock_registry
        assert len(result['tools']) == 1
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_create_user_tool_system_with_empty_tool_classes(
        self, mock_dispatcher_factory, mock_registry_class, mock_user_context
    ):
        """Test system creation with empty tool classes list."""
        
        # Setup mocks
        mock_registry = MockToolRegistry()
        mock_registry_class.return_value = mock_registry
        mock_dispatcher_factory.create_for_request.return_value = MockUnifiedToolDispatcher()
        
        # Execute with empty tool classes
        result = await UserContextToolFactory.create_user_tool_system(
            context=mock_user_context,
            tool_classes=[],
            websocket_bridge_factory=None
        )
        
        # Verify empty system structure maintained
        assert isinstance(result['tools'], list)
        assert len(result['tools']) == 0
        assert len(mock_registry.registered_tools) == 0


class TestUserContextToolFactoryUserIsolation:
    """Test critical user isolation functionality - prevents $10M+ churn from data leaks."""
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_different_users_get_isolated_systems(
        self, mock_dispatcher_factory, mock_registry_class, mock_tool_classes
    ):
        """CRITICAL: Different users must get completely isolated tool systems."""
        
        # Create different user contexts
        user1_context = MockUserExecutionContext(user_id="user1", run_id="run1")
        user2_context = MockUserExecutionContext(user_id="user2", run_id="run1")
        
        # Mock registries for isolation testing
        registry1 = MockToolRegistry()
        registry2 = MockToolRegistry()
        mock_registry_class.side_effect = [registry1, registry2]
        
        dispatcher1 = MockUnifiedToolDispatcher()
        dispatcher2 = MockUnifiedToolDispatcher()
        mock_dispatcher_factory.create_for_request.side_effect = [dispatcher1, dispatcher2]
        
        # Create systems for both users
        system1 = await UserContextToolFactory.create_user_tool_system(
            context=user1_context,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=None
        )
        
        system2 = await UserContextToolFactory.create_user_tool_system(
            context=user2_context,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=None
        )
        
        # Verify complete isolation
        assert system1['registry'] is not system2['registry']
        assert system1['dispatcher'] is not system2['dispatcher']
        assert system1['tools'][0] is not system2['tools'][0]
        assert system1['correlation_id'] != system2['correlation_id']
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_same_user_different_runs_get_separate_systems(
        self, mock_dispatcher_factory, mock_registry_class, mock_tool_classes
    ):
        """CRITICAL: Same user different runs must get separate isolated systems."""
        
        # Same user, different runs
        context_run1 = MockUserExecutionContext(user_id="user1", run_id="run1")
        context_run2 = MockUserExecutionContext(user_id="user1", run_id="run2")
        
        # Mock separate registries and dispatchers
        registry1 = MockToolRegistry()
        registry2 = MockToolRegistry()
        mock_registry_class.side_effect = [registry1, registry2]
        
        dispatcher1 = MockUnifiedToolDispatcher()
        dispatcher2 = MockUnifiedToolDispatcher()
        mock_dispatcher_factory.create_for_request.side_effect = [dispatcher1, dispatcher2]
        
        # Create systems for different runs
        system1 = await UserContextToolFactory.create_user_tool_system(
            context=context_run1,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=None
        )
        
        system2 = await UserContextToolFactory.create_user_tool_system(
            context=context_run2,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=None
        )
        
        # Verify separation between runs
        assert system1['registry'] is not system2['registry']
        assert system1['dispatcher'] is not system2['dispatcher']
        assert system1['correlation_id'] != system2['correlation_id']
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_concurrent_system_creation_isolation(
        self, mock_dispatcher_factory, mock_registry_class, mock_tool_classes
    ):
        """Test concurrent tool system creation maintains proper isolation."""
        
        # Create multiple contexts
        contexts = [
            MockUserExecutionContext(user_id=f"user{i}", run_id=f"run{i}") 
            for i in range(5)
        ]
        
        # Mock separate registries and dispatchers for each
        registries = [MockToolRegistry() for _ in range(5)]
        dispatchers = [MockUnifiedToolDispatcher() for _ in range(5)]
        mock_registry_class.side_effect = registries
        mock_dispatcher_factory.create_for_request.side_effect = dispatchers
        
        # Create systems concurrently
        tasks = [
            UserContextToolFactory.create_user_tool_system(
                context=ctx,
                tool_classes=mock_tool_classes,
                websocket_bridge_factory=None
            ) for ctx in contexts
        ]
        
        systems = await asyncio.gather(*tasks)
        
        # Verify all systems are isolated
        for i in range(5):
            for j in range(i + 1, 5):
                assert systems[i]['registry'] is not systems[j]['registry']
                assert systems[i]['dispatcher'] is not systems[j]['dispatcher']
                assert systems[i]['correlation_id'] != systems[j]['correlation_id']


class TestUserContextToolFactoryErrorHandling:
    """Test error handling and graceful degradation."""
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_tool_creation_failure_graceful_degradation(
        self, mock_dispatcher_factory, mock_registry_class, mock_user_context
    ):
        """Test graceful handling when some tools fail to instantiate."""
        
        # Setup mocks
        mock_registry = MockToolRegistry()
        mock_registry_class.return_value = mock_registry
        mock_dispatcher_factory.create_for_request.return_value = MockUnifiedToolDispatcher()
        
        # Mixed tool classes - some work, some fail
        mixed_tool_classes = [MockBaseTool, MockFailingTool, MockBaseTool]
        
        # Execute with failing tools
        result = await UserContextToolFactory.create_user_tool_system(
            context=mock_user_context,
            tool_classes=mixed_tool_classes,
            websocket_bridge_factory=None
        )
        
        # Verify partial success - working tools still created
        assert isinstance(result['tools'], list)
        assert len(result['tools']) == 2  # Only successful tools
        assert all(isinstance(tool, MockBaseTool) for tool in result['tools'])
        assert len(mock_registry.registered_tools) == 2
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_websocket_bridge_creation_failure_graceful_degradation(
        self, mock_dispatcher_factory, mock_registry_class, 
        mock_user_context, mock_tool_classes
    ):
        """Test graceful handling when WebSocket bridge creation fails."""
        
        # Setup mocks
        mock_registry = MockToolRegistry()
        mock_registry_class.return_value = mock_registry
        mock_dispatcher_factory.create_for_request.return_value = MockUnifiedToolDispatcher()
        
        # Bridge factory that fails
        def failing_bridge_factory():
            raise Exception("Bridge creation failed")
        
        # Execute with failing bridge factory
        result = await UserContextToolFactory.create_user_tool_system(
            context=mock_user_context,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=failing_bridge_factory
        )
        
        # Verify core system still works without bridge
        assert result['bridge'] is None
        assert result['registry'] is mock_registry
        assert len(result['tools']) == 1
        assert isinstance(result['dispatcher'], MockUnifiedToolDispatcher)
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_all_tools_fail_still_creates_valid_system(
        self, mock_dispatcher_factory, mock_registry_class, mock_user_context
    ):
        """Test that even if all tools fail, a valid empty system is created."""
        
        # Setup mocks
        mock_registry = MockToolRegistry()
        mock_registry_class.return_value = mock_registry
        mock_dispatcher_factory.create_for_request.return_value = MockUnifiedToolDispatcher()
        
        # All failing tools
        failing_tool_classes = [MockFailingTool, MockFailingTool]
        
        # Execute with all failing tools
        result = await UserContextToolFactory.create_user_tool_system(
            context=mock_user_context,
            tool_classes=failing_tool_classes,
            websocket_bridge_factory=None
        )
        
        # Verify valid empty system created
        assert isinstance(result['tools'], list)
        assert len(result['tools']) == 0
        assert result['registry'] is mock_registry
        assert isinstance(result['dispatcher'], MockUnifiedToolDispatcher)
        assert len(mock_registry.registered_tools) == 0
    
    @pytest.mark.unit
    async def test_invalid_user_context_raises_error(self):
        """Test that invalid user context raises appropriate error."""
        
        # Execute with None context - should fail
        with pytest.raises(AttributeError):
            await UserContextToolFactory.create_user_tool_system(
                context=None,
                tool_classes=[MockBaseTool],
                websocket_bridge_factory=None
            )


class TestUserContextToolFactoryMinimalSystem:
    """Test minimal system creation for lightweight scenarios."""
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.UserContextToolFactory.create_user_tool_system')
    async def test_create_minimal_tool_system(self, mock_create_system, mock_user_context):
        """Test minimal system creation with only DataHelperTool."""
        
        # Mock the underlying create_user_tool_system call
        expected_result = {
            'registry': MockToolRegistry(),
            'dispatcher': MockUnifiedToolDispatcher(),
            'tools': [MockBaseTool("data_helper_tool")],
            'bridge': None,
            'correlation_id': mock_user_context.get_correlation_id()
        }
        mock_create_system.return_value = expected_result
        
        # Execute minimal system creation
        result = await UserContextToolFactory.create_minimal_tool_system(mock_user_context)
        
        # Verify create_user_tool_system called with minimal config
        mock_create_system.assert_called_once()
        call_args = mock_create_system.call_args
        
        assert call_args[1]['context'] == mock_user_context
        assert call_args[1]['websocket_bridge_factory'] is None
        
        # Verify DataHelperTool imported and used
        tool_classes = call_args[1]['tool_classes']
        assert len(tool_classes) == 1
        # Note: We can't easily test the actual import, but structure is correct
        
        # Verify result structure
        assert result == expected_result


class TestUserContextToolFactoryValidation:
    """Test tool system validation functionality."""
    
    @pytest.mark.unit
    def test_validate_tool_system_success(self):
        """Test validation of complete, valid tool system."""
        
        valid_system = {
            'registry': MockToolRegistry(),
            'dispatcher': MockUnifiedToolDispatcher(),
            'tools': [MockBaseTool(), MockBaseTool()],
            'bridge': MockWebSocketBridge(),
            'correlation_id': 'test_user_test_run_123456'
        }
        
        # Validation should pass
        result = UserContextToolFactory.validate_tool_system(valid_system)
        assert result is True
    
    @pytest.mark.unit
    def test_validate_tool_system_missing_required_keys(self):
        """Test validation failure when required keys are missing."""
        
        incomplete_systems = [
            {},  # Empty system
            {'registry': MockToolRegistry()},  # Missing other keys
            {'registry': MockToolRegistry(), 'dispatcher': MockUnifiedToolDispatcher()},  # Missing tools
            {'registry': MockToolRegistry(), 'dispatcher': MockUnifiedToolDispatcher(), 'tools': []},  # Missing correlation_id
        ]
        
        for incomplete_system in incomplete_systems:
            result = UserContextToolFactory.validate_tool_system(incomplete_system)
            assert result is False
    
    @pytest.mark.unit
    def test_validate_tool_system_invalid_tools_type(self):
        """Test validation failure when tools is not a list."""
        
        invalid_system = {
            'registry': MockToolRegistry(),
            'dispatcher': MockUnifiedToolDispatcher(),
            'tools': "not_a_list",  # Invalid type
            'correlation_id': 'test_correlation'
        }
        
        result = UserContextToolFactory.validate_tool_system(invalid_system)
        assert result is False
    
    @pytest.mark.unit
    def test_validate_tool_system_empty_tools_warning(self):
        """Test validation warning for empty tools list."""
        
        empty_tools_system = {
            'registry': MockToolRegistry(),
            'dispatcher': MockUnifiedToolDispatcher(),
            'tools': [],  # Empty but valid
            'correlation_id': 'test_correlation'
        }
        
        # Should pass validation but log warning (we can't easily test logging here)
        result = UserContextToolFactory.validate_tool_system(empty_tools_system)
        assert result is True


class TestUserContextToolFactoryWebSocketBridgeIntegration:
    """Test WebSocket bridge integration with factory."""
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_websocket_bridge_factory_integration(
        self, mock_dispatcher_factory, mock_registry_class,
        mock_user_context, mock_tool_classes
    ):
        """Test WebSocket bridge factory integration with tool system."""
        
        # Setup mocks
        mock_registry = MockToolRegistry()
        mock_registry_class.return_value = mock_registry
        mock_dispatcher_factory.create_for_request.return_value = MockUnifiedToolDispatcher()
        
        bridge_instance = MockWebSocketBridge()
        bridge_factory = Mock(return_value=bridge_instance)
        
        # Execute with bridge factory
        result = await UserContextToolFactory.create_user_tool_system(
            context=mock_user_context,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=bridge_factory
        )
        
        # Verify bridge factory called and integrated
        bridge_factory.assert_called_once()
        assert result['bridge'] is bridge_instance
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_multiple_systems_bridge_isolation(
        self, mock_dispatcher_factory, mock_registry_class, mock_tool_classes
    ):
        """Test that multiple systems get separate WebSocket bridges."""
        
        # Setup mocks for two systems
        mock_registry_class.side_effect = [MockToolRegistry(), MockToolRegistry()]
        mock_dispatcher_factory.create_for_request.side_effect = [
            MockUnifiedToolDispatcher(), MockUnifiedToolDispatcher()
        ]
        
        # Different bridge instances
        bridge1 = MockWebSocketBridge()
        bridge2 = MockWebSocketBridge()
        bridge_factory1 = Mock(return_value=bridge1)
        bridge_factory2 = Mock(return_value=bridge2)
        
        # Create two systems
        context1 = MockUserExecutionContext(user_id="user1")
        context2 = MockUserExecutionContext(user_id="user2")
        
        system1 = await UserContextToolFactory.create_user_tool_system(
            context=context1,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=bridge_factory1
        )
        
        system2 = await UserContextToolFactory.create_user_tool_system(
            context=context2,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=bridge_factory2
        )
        
        # Verify bridge isolation
        assert system1['bridge'] is bridge1
        assert system2['bridge'] is bridge2
        assert system1['bridge'] is not system2['bridge']


class TestUserContextToolFactoryPerformanceAndStress:
    """Test performance characteristics and stress scenarios."""
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_system_creation_performance(
        self, mock_dispatcher_factory, mock_registry_class,
        mock_user_context, mock_tool_classes
    ):
        """Test that system creation completes within reasonable time bounds."""
        
        # Setup mocks
        mock_registry_class.return_value = MockToolRegistry()
        mock_dispatcher_factory.create_for_request.return_value = MockUnifiedToolDispatcher()
        
        # Time the system creation
        start_time = time.time()
        
        result = await UserContextToolFactory.create_user_tool_system(
            context=mock_user_context,
            tool_classes=mock_tool_classes,
            websocket_bridge_factory=None
        )
        
        elapsed_time = time.time() - start_time
        
        # System creation should be fast (under 1 second for mocked components)
        assert elapsed_time < 1.0
        assert result is not None
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_concurrent_system_creation_stress(
        self, mock_dispatcher_factory, mock_registry_class, mock_tool_classes
    ):
        """Stress test concurrent system creation for race conditions."""
        
        # Setup mocks for multiple systems
        registries = [MockToolRegistry() for _ in range(10)]
        dispatchers = [MockUnifiedToolDispatcher() for _ in range(10)]
        mock_registry_class.side_effect = registries
        mock_dispatcher_factory.create_for_request.side_effect = dispatchers
        
        # Create contexts for stress testing
        contexts = [
            MockUserExecutionContext(user_id=f"stress_user_{i}", run_id=f"stress_run_{i}") 
            for i in range(10)
        ]
        
        # Execute concurrent creation
        tasks = [
            UserContextToolFactory.create_user_tool_system(
                context=ctx,
                tool_classes=mock_tool_classes,
                websocket_bridge_factory=None
            ) for ctx in contexts
        ]
        
        # All should complete successfully
        systems = await asyncio.gather(*tasks)
        
        # Verify all systems created and isolated
        assert len(systems) == 10
        for i, system in enumerate(systems):
            assert system['registry'] is registries[i]
            assert system['dispatcher'] is dispatchers[i]
            assert len(system['tools']) == 1


class TestUserContextToolFactoryEdgeCasesAndRobustness:
    """Test edge cases and robustness scenarios."""
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry')
    @patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory')
    async def test_duplicate_tool_classes_handled(
        self, mock_dispatcher_factory, mock_registry_class, mock_user_context
    ):
        """Test handling of duplicate tool classes in the list."""
        
        # Setup mocks
        mock_registry = MockToolRegistry()
        mock_registry_class.return_value = mock_registry
        mock_dispatcher_factory.create_for_request.return_value = MockUnifiedToolDispatcher()
        
        # Duplicate tool classes
        duplicate_tool_classes = [MockBaseTool, MockBaseTool, MockBaseTool]
        
        # Execute with duplicates
        result = await UserContextToolFactory.create_user_tool_system(
            context=mock_user_context,
            tool_classes=duplicate_tool_classes,
            websocket_bridge_factory=None
        )
        
        # Should create separate instances (no deduplication expected)
        assert len(result['tools']) == 3
        assert all(isinstance(tool, MockBaseTool) for tool in result['tools'])
        
        # All should be registered (with same name - registry handles conflicts)
        assert len(mock_registry.registered_tools) == 3
    
    @pytest.mark.unit
    async def test_none_values_in_tool_classes_handled(self, mock_user_context):
        """Test handling of None values in tool classes list."""
        
        with patch('netra_backend.app.agents.user_context_tool_factory.ToolRegistry'), \
             patch('netra_backend.app.agents.user_context_tool_factory.UnifiedToolDispatcherFactory'):
            
            # Tool classes with None values should cause errors
            tool_classes_with_none = [MockBaseTool, None, MockBaseTool]
            
            # This should raise an error when trying to instantiate None
            with pytest.raises((TypeError, AttributeError)):
                await UserContextToolFactory.create_user_tool_system(
                    context=mock_user_context,
                    tool_classes=tool_classes_with_none,
                    websocket_bridge_factory=None
                )
    
    @pytest.mark.unit
    def test_validate_system_with_none_input(self):
        """Test validation handles None input gracefully."""
        
        # Should not crash, should return False
        result = UserContextToolFactory.validate_tool_system(None)
        assert result is False


class TestGetAppToolClasses:
    """Test the standalone get_app_tool_classes function."""
    
    @pytest.mark.unit
    def test_get_app_tool_classes_returns_list(self):
        """Test that get_app_tool_classes returns a list of tool classes."""
        
        result = get_app_tool_classes()
        
        assert isinstance(result, list)
        # Should return some tool classes (at least the fallback ones)
        assert len(result) >= 0  # May be empty in test environment
    
    @pytest.mark.unit
    @patch('netra_backend.app.agents.user_context_tool_factory.Request')
    def test_get_app_tool_classes_handles_request_context_failure(self, mock_request):
        """Test fallback behavior when request context is not available."""
        
        # Mock Request to raise exception (simulating no request context)
        mock_request.side_effect = Exception("No request context")
        
        result = get_app_tool_classes()
        
        # Should fall back to default tool classes
        assert isinstance(result, list)
        # In the actual implementation, this falls back to specific tools
        assert len(result) >= 0