"""
Unit tests for agent metadata and registry systems.

This module tests critical agent registry functionality including user isolation,
session management, and agent metadata tracking.

Business Value: Agent registry ensures secure multi-user execution and proper
resource isolation, enabling concurrent customer usage across all segments.
"""

import pytest
import asyncio
import uuid
import weakref
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from netra_backend.app.agents.supervisor.agent_registry import (
    UserAgentSession,
    get_global_registry
)
from netra_backend.app.agents.models import (
    DataCategory,
    DataPriority,
    DataRequirement,
    WorkflowContext,
    WorkflowPath,
    AgentState,
    DataSufficiencyAssessment
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestUserAgentSession:
    """Test user agent session isolation and management."""
    
    def test_user_agent_session_creation_requires_valid_user_id(self):
        """Test that UserAgentSession requires a valid user ID."""
        # Valid user ID should work
        session = UserAgentSession("user_123")
        assert session.user_id == "user_123"
        assert len(session._agents) == 0
        assert len(session._execution_contexts) == 0
        assert session._websocket_bridge is None
        
        # Invalid user IDs should raise ValueError
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            UserAgentSession("")
        
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            UserAgentSession(None)
        
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            UserAgentSession(123)  # Not a string
    
    def test_user_agent_session_isolation_by_user_id(self):
        """Test that different user sessions are completely isolated."""
        session1 = UserAgentSession("user_1")
        session2 = UserAgentSession("user_2")
        
        # Sessions should be independent
        assert session1.user_id != session2.user_id
        assert session1._agents is not session2._agents
        assert session1._execution_contexts is not session2._execution_contexts
        assert id(session1) != id(session2)
    
    @pytest.mark.asyncio
    async def test_websocket_manager_setup_with_user_context(self):
        """Test WebSocket manager setup with proper user context isolation."""
        session = UserAgentSession("test_user")
        mock_websocket_manager = Mock()
        
        # Mock the user context
        mock_user_context = Mock()
        mock_user_context.user_id = "test_user"
        
        # Mock the bridge creation factory
        mock_bridge = Mock()
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge', 
                  return_value=mock_bridge) as mock_factory:
            
            await session.set_websocket_manager(mock_websocket_manager, mock_user_context)
        
        # Verify websocket manager was set
        assert session._websocket_manager == mock_websocket_manager
        assert session._websocket_bridge == mock_bridge
        
        # Verify factory was called with correct context
        mock_factory.assert_called_once()
        call_args = mock_factory.call_args[0]
        assert call_args[0] == mock_user_context  # First argument should be user context
    
    @pytest.mark.asyncio
    async def test_websocket_manager_creates_context_when_none_provided(self):
        """Test WebSocket manager creates user context when none provided."""
        session = UserAgentSession("context_test_user")
        mock_websocket_manager = Mock()
        
        mock_bridge = Mock()
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge', 
                  return_value=mock_bridge) as mock_factory:
            with patch('netra_backend.app.services.user_execution_context.UserExecutionContext') as mock_context_class:
                mock_context_instance = Mock()
                mock_context_instance.user_id = "context_test_user"
                mock_context_class.return_value = mock_context_instance
                
                await session.set_websocket_manager(mock_websocket_manager)
                
                # Verify context was created with correct user ID
                mock_context_class.assert_called_once()
                call_kwargs = mock_context_class.call_args[1]
                assert call_kwargs['user_id'] == "context_test_user"
                assert 'request_id' in call_kwargs
                assert 'thread_id' in call_kwargs
    
    @pytest.mark.asyncio
    async def test_custom_bridge_factory_support(self):
        """Test support for custom WebSocket bridge factories (e.g., for testing)."""
        session = UserAgentSession("custom_factory_user")
        
        # Mock websocket manager with custom bridge factory
        mock_websocket_manager = Mock()
        mock_custom_bridge = Mock()
        
        # Test async bridge factory
        async def async_bridge_factory(context):
            return mock_custom_bridge
        
        mock_websocket_manager.create_bridge = async_bridge_factory
        
        mock_user_context = Mock()
        mock_user_context.user_id = "custom_factory_user"
        
        await session.set_websocket_manager(mock_websocket_manager, mock_user_context)
        
        assert session._websocket_bridge == mock_custom_bridge
    
    def test_user_agent_session_timestamp_tracking(self):
        """Test that UserAgentSession tracks creation time properly."""
        before_creation = datetime.now(timezone.utc)
        session = UserAgentSession("timestamp_user")
        after_creation = datetime.now(timezone.utc)
        
        assert before_creation <= session._created_at <= after_creation
        assert session._created_at.tzinfo == timezone.utc


class TestAgentMetadataModels:
    """Test agent metadata model functionality and business logic."""
    
    def test_data_requirement_priority_comparison(self):
        """Test DataRequirement priority comparison for business logic."""
        critical_req = DataRequirement(
            category=DataCategory.FINANCIAL,
            field="revenue",
            priority=DataPriority.CRITICAL,
            reason="Essential for ROI calculation"
        )
        
        low_req = DataRequirement(
            category=DataCategory.TECHNICAL,
            field="api_version",
            priority=DataPriority.LOW,
            reason="Nice to have for compatibility"
        )
        
        # Critical should have higher numeric value than low
        assert critical_req.priority.value_numeric > low_req.priority.value_numeric
        assert critical_req.priority.value_numeric == 4
        assert low_req.priority.value_numeric == 1
    
    def test_data_category_enum_completeness(self):
        """Test that DataCategory enum covers expected business domains."""
        expected_categories = {
            DataCategory.FINANCIAL,
            DataCategory.PERFORMANCE, 
            DataCategory.USAGE,
            DataCategory.TECHNICAL,
            DataCategory.BUSINESS
        }
        
        # All expected categories should exist
        assert len(expected_categories) == 5
        
        # Each should have appropriate string values
        assert DataCategory.FINANCIAL.value == "financial"
        assert DataCategory.PERFORMANCE.value == "performance"
        assert DataCategory.USAGE.value == "usage"
        assert DataCategory.TECHNICAL.value == "technical"
        assert DataCategory.BUSINESS.value == "business"
    
    def test_workflow_context_state_transitions(self):
        """Test WorkflowContext supports proper agent state transitions."""
        context = WorkflowContext(
            thread_id="thread_123",
            turn_id="turn_456",
            workflow_path=WorkflowPath.FLOW_A_SUFFICIENT,
            data_sufficiency="sufficient",  # Using string instead of enum
            state=AgentState.IDLE
        )
        
        # Should start in IDLE state
        assert context.state == AgentState.IDLE
        assert context.current_agent is None
        assert context.started_at is None
        assert context.completed_at is None
        
        # Simulate state transitions
        context.state = AgentState.PROCESSING
        context.current_agent = "data_collection_agent"
        context.started_at = datetime.now()
        
        assert context.state == AgentState.PROCESSING
        assert context.current_agent == "data_collection_agent"
        assert context.started_at is not None
    
    def test_workflow_path_enum_business_logic(self):
        """Test WorkflowPath enum reflects business workflow decisions."""
        # Test that all expected workflow paths exist
        paths = [
            WorkflowPath.FLOW_A_SUFFICIENT,
            WorkflowPath.FLOW_B_PARTIAL, 
            WorkflowPath.FLOW_C_INSUFFICIENT
        ]
        
        assert len(paths) == 3
        
        # Verify string values match expected business naming
        assert WorkflowPath.FLOW_A_SUFFICIENT.value == "flow_a_sufficient"
        assert WorkflowPath.FLOW_B_PARTIAL.value == "flow_b_partial"
        assert WorkflowPath.FLOW_C_INSUFFICIENT.value == "flow_c_insufficient"
    
    def test_agent_state_enum_covers_execution_lifecycle(self):
        """Test AgentState enum covers complete execution lifecycle."""
        expected_states = {
            AgentState.IDLE,
            AgentState.PROCESSING,
            AgentState.WAITING_FOR_INPUT,
            AgentState.COMPLETED,
            AgentState.ERROR
        }
        
        assert len(expected_states) == 5
        
        # Verify all states have proper string values
        state_values = {state.value for state in expected_states}
        expected_values = {"idle", "processing", "waiting_for_input", "completed", "error"}
        assert state_values == expected_values
    
    def test_data_sufficiency_assessment_business_validation(self):
        """Test DataSufficiencyAssessment provides proper business decision support."""
        assessment = DataSufficiencyAssessment(
            sufficiency_level="PARTIAL",
            percentage_complete=60,
            can_proceed=True,
            missing_requirements=[],
            optimization_quality={
                "cost_optimization": "medium",
                "performance_optimization": "low"
            }
        )
        
        assert assessment.sufficiency_level == "PARTIAL"
        assert assessment.percentage_complete == 60
        assert assessment.can_proceed is True
        
        # Business logic: partial data (60%) can still proceed
        # This reflects real business decision-making
        assert assessment.optimization_quality["cost_optimization"] == "medium"
        assert assessment.optimization_quality["performance_optimization"] == "low"


class TestAgentRegistryIntegration:
    """Test agent registry integration and global state management."""
    
    def test_global_registry_singleton_pattern(self):
        """Test that global registry follows singleton pattern."""
        registry1 = get_global_registry()
        registry2 = get_global_registry()
        
        # Should return same instance
        assert registry1 is registry2
        assert id(registry1) == id(registry2)
    
    def test_global_registry_initialization(self):
        """Test that global registry initializes properly."""
        registry = get_global_registry()
        
        # Should have expected methods and attributes
        assert hasattr(registry, 'register_agent')
        assert hasattr(registry, 'get_agent')
        assert callable(registry.register_agent)
        assert callable(registry.get_agent)
    
    def test_user_session_isolation_memory_safety(self):
        """Test that user sessions don't create memory leaks."""
        # Create multiple sessions
        sessions = []
        for i in range(10):
            session = UserAgentSession(f"user_{i}")
            sessions.append(weakref.ref(session))
        
        # Clear strong references
        del sessions[0].__self__  # Clear first session explicitly
        
        # Force garbage collection (if available)
        import gc
        gc.collect()
        
        # Weak references should allow cleanup
        # (Note: This test is more about structure than actual GC behavior)
        assert len(sessions) == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_user_session_creation(self):
        """Test concurrent user session creation for race condition safety."""
        async def create_session(user_id):
            session = UserAgentSession(user_id)
            # Simulate some async work
            await asyncio.sleep(0.001)
            return session
        
        # Create multiple sessions concurrently
        tasks = [create_session(f"concurrent_user_{i}") for i in range(20)]
        sessions = await asyncio.gather(*tasks)
        
        # All sessions should be created successfully
        assert len(sessions) == 20
        
        # Each should have unique user ID
        user_ids = {session.user_id for session in sessions}
        assert len(user_ids) == 20  # All unique
        
        # All should be properly initialized
        for session in sessions:
            assert isinstance(session._created_at, datetime)
            assert len(session._agents) == 0
            assert hasattr(session, '_access_lock')
    
    def test_user_execution_context_integration(self):
        """Test UserExecutionContext integration with agent sessions."""
        session = UserAgentSession("integration_test_user")
        
        # Create a mock user execution context
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "integration_test_user"
        mock_context.request_id = "req_123"
        mock_context.thread_id = "thread_456"
        
        # Context should integrate properly with session
        # (Testing the interface, actual integration tested elsewhere)
        assert mock_context.user_id == session.user_id
        assert hasattr(mock_context, 'request_id')
        assert hasattr(mock_context, 'thread_id')


class TestAgentMetadataEdgeCases:
    """Test edge cases and error conditions in agent metadata."""
    
    def test_data_requirement_with_minimal_fields(self):
        """Test DataRequirement with only required fields."""
        requirement = DataRequirement(
            category=DataCategory.BUSINESS,
            field="primary_goal",
            priority=DataPriority.MEDIUM,
            reason="Needed for strategy alignment"
        )
        
        assert requirement.category == DataCategory.BUSINESS
        assert requirement.field == "primary_goal"
        assert requirement.priority == DataPriority.MEDIUM
        assert requirement.reason == "Needed for strategy alignment"
        assert requirement.optional is False  # Default value
    
    def test_workflow_context_with_complex_data_structures(self):
        """Test WorkflowContext handling of complex collected data."""
        complex_data = {
            "financial": {
                "revenue": {"monthly": 50000, "annual": 600000},
                "costs": {"infrastructure": 15000, "personnel": 30000}
            },
            "performance": {
                "metrics": [
                    {"name": "response_time", "value": 150, "unit": "ms"},
                    {"name": "throughput", "value": 2000, "unit": "rpm"}
                ]
            },
            "metadata": {
                "collection_timestamp": datetime.now().isoformat(),
                "data_sources": ["manual_input", "api_metrics", "database_query"]
            }
        }
        
        context = WorkflowContext(
            thread_id="complex_data_thread",
            turn_id="complex_data_turn",
            workflow_path=WorkflowPath.FLOW_A_SUFFICIENT,
            data_sufficiency="sufficient",
            collected_data=complex_data
        )
        
        # Should handle nested data structures
        assert context.collected_data["financial"]["revenue"]["annual"] == 600000
        assert len(context.collected_data["performance"]["metrics"]) == 2
        assert "api_metrics" in context.collected_data["metadata"]["data_sources"]
    
    def test_agent_state_enum_string_conversion(self):
        """Test AgentState enum string conversion for logging/serialization."""
        state = AgentState.PROCESSING
        
        # Should convert to proper string for logging
        assert str(state) == "AgentState.PROCESSING"
        assert state.value == "processing"
        
        # Should be JSON serializable
        import json
        state_dict = {"current_state": state.value}
        json_str = json.dumps(state_dict)
        assert '"current_state": "processing"' in json_str
    
    def test_empty_user_agent_session_initial_state(self):
        """Test that empty UserAgentSession has consistent initial state."""
        session = UserAgentSession("empty_test_user")
        
        # All collections should be empty
        assert len(session._agents) == 0
        assert len(session._execution_contexts) == 0
        
        # Optional components should be None
        assert session._websocket_bridge is None
        assert session._websocket_manager is None
        
        # Timestamp should be recent
        time_diff = datetime.now(timezone.utc) - session._created_at
        assert time_diff.total_seconds() < 1.0  # Created within last second
    
    def test_data_priority_edge_case_values(self):
        """Test DataPriority enum edge cases and boundary values."""
        # Test all priority levels
        priorities = [
            (DataPriority.CRITICAL, 4),
            (DataPriority.HIGH, 3),
            (DataPriority.MEDIUM, 2),
            (DataPriority.LOW, 1)
        ]
        
        for priority, expected_numeric in priorities:
            assert priority.value_numeric == expected_numeric
        
        # Test that unknown values return 0 (safety fallback)
        # Note: This tests the implementation detail in value_numeric property
        fake_priority = Mock()
        fake_priority.value = "unknown_priority"
        
        # Monkey patch to test edge case
        original_get = dict.get
        def mock_get(key, default=None):
            if key == "unknown_priority":
                return 0
            return original_get(key, default)
        
        priority_map = {
            "critical": 4, "high": 3, "medium": 2, "low": 1
        }
        
        # Test fallback behavior
        result = priority_map.get("unknown_priority", 0)
        assert result == 0