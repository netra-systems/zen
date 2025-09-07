"""Direct SSOT Validation Tests for SupervisorAgent and Related Components.

This test file validates that all SSOT violations have been fixed in:
- SupervisorAgent
- Observability components
- GoalsTriageSubAgent
- ActionsToMeetGoalsSubAgent
"""

import pytest
import asyncio
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

# Import the components we've fixed
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.observability_flow import get_supervisor_flow_logger
from netra_backend.app.agents.supervisor.flow_logger import SupervisorPipelineLogger
from netra_backend.app.agents.supervisor.comprehensive_observability import ComprehensiveObservabilityManager
from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext

# Import canonical SSOT implementations to verify usage
from netra_backend.app.core.serialization.unified_json_handler import backend_json_handler
from netra_backend.app.core.unified_error_handler import agent_error_handler
from shared.isolated_environment import IsolatedEnvironment


class TestSSOTCompliance:
    """Test SSOT compliance for all fixed components."""
    
    def test_json_handling_in_observability(self):
        """Verify observability components use backend_json_handler."""
        # Test SupervisorPipelineLogger
        flow_logger = SupervisorPipelineLogger()
        
        # Verify backend_json_handler is imported (not json)
        import inspect
        source = inspect.getsource(flow_logger.__class__)
        assert "backend_json_handler" in source, "SupervisorPipelineLogger should use backend_json_handler"
        assert "import json" not in source, "SupervisorPipelineLogger should not import json directly"
        
        # Test ComprehensiveObservabilityManager
        obs_manager = ComprehensiveObservabilityManager("test_agent")
        source = inspect.getsource(obs_manager.__class__)
        assert "backend_json_handler" in source, "ComprehensiveObservabilityManager should use backend_json_handler"
        assert "import json" not in source, "ComprehensiveObservabilityManager should not import json directly"
    
    def test_supervisor_agent_ssot_compliance(self):
        """Verify SupervisorAgent follows SSOT patterns."""
        # Create mocked dependencies
        llm_manager = MagicNone  # TODO: Use real service instance
        websocket_bridge = MagicNone  # TODO: Use real service instance
        tool_dispatcher = MagicNone  # TODO: Use real service instance
        
        # Create supervisor
        supervisor = SupervisorAgent(llm_manager, websocket_bridge, tool_dispatcher)
        
        # Verify UserExecutionContext pattern
        assert hasattr(supervisor, 'execute'), "SupervisorAgent should have execute method"
        
        # Verify no session storage in instance
        assert not hasattr(supervisor, 'db_session'), "SupervisorAgent should not store db_session"
        assert not hasattr(supervisor, 'session'), "SupervisorAgent should not store session"
        
        # Verify imports in source
        import inspect
        source = inspect.getsource(supervisor.__class__)
        assert "UserExecutionContext" in source, "Should use UserExecutionContext"
        assert "DatabaseSessionManager" in source, "Should use DatabaseSessionManager"
        assert "IsolatedEnvironment" not in source or "os.environ" not in source, "Should not use os.environ directly"
    
    def test_goals_triage_ssot_compliance(self):
        """Verify GoalsTriageSubAgent follows SSOT patterns."""
        agent = GoalsTriageSubAgent()
        
        # Check source for SSOT compliance
        import inspect
        source = inspect.getsource(agent.__class__)
        
        # Verify JSON handling
        assert "LLMResponseParser" in source, "Should use LLMResponseParser for JSON"
        assert "JSONErrorFixer" in source, "Should use JSONErrorFixer for JSON recovery"
        
        # Verify error handling
        assert "agent_error_handler" in source, "Should use agent_error_handler"
        assert "ErrorContext" in source, "Should use ErrorContext for errors"
        
        # Verify no direct json usage
        json_imports = source.count("import json")
        assert json_imports == 0 or "# For type checking" in source, "Should not import json directly for runtime"
    
    def test_actions_agent_ssot_compliance(self):
        """Verify ActionsToMeetGoalsSubAgent follows SSOT patterns."""
        llm_manager = MagicNone  # TODO: Use real service instance
        tool_dispatcher = MagicNone  # TODO: Use real service instance
        agent = ActionsToMeetGoalsSubAgent(llm_manager, tool_dispatcher)
        
        # Check source for SSOT compliance
        import inspect
        source = inspect.getsource(agent.__class__)
        
        # Verify JSON handling
        assert "backend_json_handler" in source, "Should use backend_json_handler"
        
        # Verify error handling
        assert "ErrorContext" in source, "Should use ErrorContext"
        
        # Verify UserExecutionContext usage
        assert "UserExecutionContext" in source, "Should use UserExecutionContext"
    
    @pytest.mark.asyncio
    async def test_supervisor_user_isolation(self):
        """Test that SupervisorAgent properly isolates users."""
        # Create supervisor with mocked dependencies
        llm_manager = MagicNone  # TODO: Use real service instance
        websocket_bridge = MagicNone  # TODO: Use real service instance
        tool_dispatcher = MagicNone  # TODO: Use real service instance
        
        supervisor = SupervisorAgent(llm_manager, websocket_bridge, tool_dispatcher)
        
        # Create two different user contexts
        context1 = UserExecutionContext(
            user_id="user1",
            thread_id="thread1",
            run_id="run1",
            metadata={"user_request": "Test 1"},
            db_session=MagicNone  # TODO: Use real service instance
        )
        
        context2 = UserExecutionContext(
            user_id="user2",
            thread_id="thread2", 
            run_id="run2",
            metadata={"user_request": "Test 2"},
            db_session=MagicNone  # TODO: Use real service instance
        )
        
        # Mock the internal methods to avoid actual execution
        supervisor._orchestrate_agents = AsyncMock(return_value={"test": "result"})
        
        # Execute with both contexts
        result1 = await supervisor.execute(context1)
        result2 = await supervisor.execute(context2)
        
        # Verify isolation
        assert result1["user_id"] == "user1"
        assert result2["user_id"] == "user2"
        assert result1["run_id"] == "run1"
        assert result2["run_id"] == "run2"
    
    def test_no_global_state_in_supervisor(self):
        """Verify SupervisorAgent has no global state that could leak between users."""
        llm_manager = MagicNone  # TODO: Use real service instance
        websocket_bridge = MagicNone  # TODO: Use real service instance
        tool_dispatcher = MagicNone  # TODO: Use real service instance
        
        supervisor = SupervisorAgent(llm_manager, websocket_bridge, tool_dispatcher)
        
        # Check for problematic attributes
        problematic_attrs = ['user_id', 'thread_id', 'run_id', 'db_session', 'session']
        
        for attr in problematic_attrs:
            assert not hasattr(supervisor, attr), f"SupervisorAgent should not have {attr} attribute"
    
    def test_websocket_event_isolation(self):
        """Test that WebSocket events are properly isolated per user."""
        llm_manager = MagicNone  # TODO: Use real service instance
        websocket_bridge = MagicNone  # TODO: Use real service instance
        tool_dispatcher = MagicNone  # TODO: Use real service instance
        
        supervisor = SupervisorAgent(llm_manager, websocket_bridge, tool_dispatcher)
        
        # Check that supervisor uses websocket_bridge correctly
        assert supervisor.websocket_bridge is websocket_bridge
        
        # Verify emit_thinking method exists and uses context
        assert hasattr(supervisor, '_emit_thinking')
        
        # Check method signature includes context
        import inspect
        sig = inspect.signature(supervisor._emit_thinking)
        params = list(sig.parameters.keys())
        assert 'context' in params, "_emit_thinking should accept context parameter"


class TestIntegrationPatterns:
    """Test integration patterns between components."""
    
    @pytest.mark.asyncio
    async def test_supervisor_to_subagent_context_flow(self):
        """Test that context flows correctly from supervisor to sub-agents."""
        # Create supervisor
        llm_manager = MagicNone  # TODO: Use real service instance
        websocket_bridge = MagicNone  # TODO: Use real service instance
        tool_dispatcher = MagicNone  # TODO: Use real service instance
        
        supervisor = SupervisorAgent(llm_manager, websocket_bridge, tool_dispatcher)
        
        # Create context
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            metadata={"test": "data"},
            db_session=MagicNone  # TODO: Use real service instance
        )
        
        # Mock agent instance creation
        mock_agent = MagicNone  # TODO: Use real service instance
        mock_agent.execute = AsyncMock(return_value={"result": "success"})
        
        with patch.object(supervisor, '_create_isolated_agent_instances', 
                         return_value={"test_agent": mock_agent}):
            with patch.object(supervisor, '_execute_workflow_with_isolated_agents',
                            new=AsyncMock(return_value={"workflow": "completed"})):
                
                result = await supervisor.execute(context)
                
                # Verify result structure
                assert result["user_id"] == "test_user"
                assert result["run_id"] == "test_run"
                assert result["user_isolation_verified"] == True
    
    def test_error_context_usage_in_agents(self):
        """Verify agents use ErrorContext for error handling."""
        # Check GoalsTriageSubAgent
        goals_agent = GoalsTriageSubAgent()
        source = inspect.getsource(goals_agent.__class__)
        
        # Look for ErrorContext usage pattern
        assert "ErrorContext(" in source, "GoalsTriageSubAgent should create ErrorContext"
        assert "component=" in source, "ErrorContext should specify component"
        assert "operation=" in source, "ErrorContext should specify operation"
        
        # Check ActionsToMeetGoalsSubAgent
        llm_manager = MagicNone  # TODO: Use real service instance
        tool_dispatcher = MagicNone  # TODO: Use real service instance
        actions_agent = ActionsToMeetGoalsSubAgent(llm_manager, tool_dispatcher)
        source = inspect.getsource(actions_agent.__class__)
        
        assert "ErrorContext(" in source, "ActionsToMeetGoalsSubAgent should create ErrorContext"


class TestBackwardCompatibility:
    """Test that backward compatibility is maintained where needed."""
    
    def test_agents_still_function_without_context(self):
        """Test that agents can still be instantiated without context."""
        # GoalsTriageSubAgent
        goals_agent = GoalsTriageSubAgent()
        assert goals_agent is not None
        
        # ActionsToMeetGoalsSubAgent
        llm_manager = MagicNone  # TODO: Use real service instance
        tool_dispatcher = MagicNone  # TODO: Use real service instance
        actions_agent = ActionsToMeetGoalsSubAgent(llm_manager, tool_dispatcher)
        assert actions_agent is not None
        
        # SupervisorAgent
        websocket_bridge = MagicNone  # TODO: Use real service instance
        supervisor = SupervisorAgent(llm_manager, websocket_bridge, tool_dispatcher)
        assert supervisor is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])