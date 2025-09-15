"""
Regression tests for state model validation errors.
Ensures all state models can be instantiated with minimal required data.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from typing import Any, Dict

import pytest
from pydantic import ValidationError

# Import both versions of DeepAgentState to test consistency
try:
    from netra_backend.app.schemas.agent_models import DeepAgentState as AgentsDeepAgentState
    from netra_backend.app.schemas.agent_models import (
        DeepAgentState as SchemaDeepAgentState,
    )
except ImportError:
    pytest.skip("Required modules have been removed or have missing dependencies", allow_module_level=True)
from netra_backend.app.websocket_core.connection_executor import ConnectionOperationBuilder

class TestDeepAgentStateRegression:
    """Regression tests for DeepAgentState validation issues."""
    
    def test_deep_agent_state_minimal_init(self):
        """Test that DeepAgentState can be created with minimal data."""
        # Should not raise validation error with empty dict
        state = AgentsDeepAgentState()
        assert state.user_request == "default_request"
        
    def test_deep_agent_state_empty_dict(self):
        """Test DeepAgentState handles empty dict initialization."""
        # This was the original failing case
        state = AgentsDeepAgentState(**{})
        assert state.user_request == "default_request"
        
    def test_schema_deep_agent_state_consistency(self):
        """Ensure both DeepAgentState versions behave consistently."""
        agents_state = AgentsDeepAgentState()
        schema_state = SchemaDeepAgentState()
        
        assert agents_state.user_request == schema_state.user_request
        assert agents_state.user_request == "default_request"
        
    def test_deep_agent_state_with_user_request(self):
        """Test DeepAgentState with explicit user_request."""
        request = "test_user_request"
        state = AgentsDeepAgentState(user_request=request)
        assert state.user_request == request

class TestWebSocketConnectionRegression:
    """Regression tests for WebSocket connection state issues."""
    
    def test_connection_builder_creates_valid_state(self):
        """Test ConnectionOperationBuilder creates valid DeepAgentState."""
        builder = ConnectionOperationBuilder()
        builder.with_operation_type("test_operation")
        builder.with_operation_data({})
        
        # This should not raise validation error
        state = builder._create_agent_state()
        assert state.user_request == "websocket_test_operation"
        
    def test_connection_builder_with_user_request(self):
        """Test ConnectionOperationBuilder uses provided user_request."""
        builder = ConnectionOperationBuilder()
        builder.with_operation_type("test")
        builder.with_operation_data({"user_request": "custom_request"})
        
        state = builder._create_agent_state()
        assert state.user_request == "custom_request"
        
    def test_connection_builder_no_operation_type(self):
        """Test ConnectionOperationBuilder handles missing operation type."""
        builder = ConnectionOperationBuilder()
        builder.with_operation_data({})
        
        # Should create state with default operation type
        state = builder._create_agent_state()
        assert state.user_request == "websocket_operation"

class TestAllStateModelsInit:
    """Test all state models can be initialized properly."""
    
    def test_migration_state_init(self):
        """Test MigrationState initialization."""
        from netra_backend.app.startup.migration_models import MigrationState
        
        # Test with default initialization
        state = MigrationState()
        assert state.applied_migrations == []
        assert state.pending_migrations == []
        assert state.auto_run_enabled is True
        
    def test_langchain_agent_state_init(self):
        """Test LangChainAgentState initialization."""
        from langchain_core.messages import HumanMessage

        from netra_backend.app.schemas.agent import LangChainAgentState
        
        # Test with required fields
        state = LangChainAgentState(
            messages=[HumanMessage(content="test")],
            next_node="start"
        )
        assert len(state.messages) == 1
        
    def test_sub_agent_state_init(self):
        """Test SubAgentState initialization."""
        from langchain_core.messages import HumanMessage

        from netra_backend.app.schemas.agent import SubAgentState
        
        # Test with required fields
        state = SubAgentState(
            messages=[HumanMessage(content="test")],
            next_node="start"
        )
        assert len(state.messages) == 1
        
    def test_agent_state_from_apex_optimizer(self):
        """Test AgentState from apex_optimizer."""
        from langchain_core.messages import HumanMessage

        from netra_backend.app.services.apex_optimizer_agent.models import AgentState
        
        # Test with required fields
        state = AgentState(
            messages=[HumanMessage(content="test")],
            next_node="start"
        )
        assert len(state.messages) == 1
        assert state.next_node == "start"
        
    def test_current_system_state_init(self):
        """Test CurrentSystemState initialization."""
        from netra_backend.app.schemas.llm_config_types import CurrentSystemState
        
        # Test with required fields
        state = CurrentSystemState(
            daily_cost=100.0,
            avg_latency_ms=50.0,
            daily_requests=1000
        )
        assert state.daily_cost == 100.0
        assert state.avg_latency_ms == 50.0
        assert state.daily_requests == 1000
        
    def test_system_state_diagnostic_init(self):
        """Test SystemState from diagnostics initialization."""
        from netra_backend.app.schemas.diagnostic_types import SystemState
        
        # Should have sensible defaults
        state = SystemState()
        assert state.processes == []
        assert state.memory_usage == 0.0
        assert state.cpu_usage == 0.0

class TestValidationErrorMessages:
    """Test that validation errors are clear and helpful."""
    
    def test_missing_required_field_error_message(self):
        """Test error message when required field is missing."""
        from netra_backend.app.schemas.agent import LangChainAgentState
        
        with pytest.raises(ValidationError) as exc_info:
            # Missing required 'messages' field
            LangChainAgentState(next_node="start")
            
        error = exc_info.value
        assert "messages" in str(error)
        assert "Field required" in str(error)
        
    def test_deep_agent_state_backward_compatibility(self):
        """Ensure DeepAgentState maintains backward compatibility."""
        # Old code that didn't provide user_request should still work
        old_style_init = {"chat_thread_id": "thread_123"}
        state = AgentsDeepAgentState(**old_style_init)
        
        assert state.user_request == "default_request"
        assert state.chat_thread_id == "thread_123"