"""Mission Critical: SupervisorAgent Golden Pattern Compliance Tests

Tests the migrated SupervisorAgent for golden pattern compliance:
1. Clean inheritance from BaseAgent
2. SSOT infrastructure usage
3. WebSocket event emission
4. Backward compatibility
5. Business logic only architecture

Business Value: Ensures supervisor orchestration reliability
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager


class TestSupervisorAgentGoldenPattern:
    """Test SupervisorAgent golden pattern compliance."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        return Mock(spec=LLMManager)
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher."""
        return Mock(spec=ToolDispatcher)
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return Mock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_websocket_bridge(self):
        """Create mock websocket bridge."""
        bridge = Mock()
        bridge.notify_agent_started = AsyncMock()
        bridge.notify_agent_thinking = AsyncMock() 
        bridge.notify_agent_completed = AsyncMock()
        bridge.notify_progress = AsyncMock()
        return bridge
    
    @pytest.fixture
    def supervisor_agent(self, mock_db_session, mock_llm_manager, 
                        mock_websocket_bridge, mock_tool_dispatcher):
        """Create SupervisorAgent instance."""
        with patch('netra_backend.app.agents.supervisor.agent_registry.AgentRegistry') as mock_registry_class:
            # Mock the registry
            mock_registry = Mock()
            mock_registry.agents = {}
            mock_registry.get_all_agents.return_value = []
            mock_registry.register_default_agents = Mock()
            mock_registry.set_websocket_bridge = Mock()
            mock_registry_class.return_value = mock_registry
            
            # Mock execution helpers
            with patch('netra_backend.app.agents.supervisor.modern_execution_helpers.SupervisorExecutionHelpers') as mock_helpers_class:
                mock_helpers = Mock()
                mock_helpers.run_supervisor_workflow = AsyncMock(return_value=DeepAgentState())
                mock_helpers_class.return_value = mock_helpers
                
                with patch('netra_backend.app.agents.supervisor.workflow_execution.SupervisorWorkflowExecutor'):
                    agent = SupervisorAgent(
                        db_session=mock_db_session,
                        llm_manager=mock_llm_manager,
                        websocket_bridge=mock_websocket_bridge,
                        tool_dispatcher=mock_tool_dispatcher
                    )
                    # Ensure registry mock is accessible
                    agent.registry = mock_registry
                    return agent

    def test_golden_pattern_inheritance(self, supervisor_agent):
        """Test 1: Verify clean BaseAgent inheritance."""
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # Must inherit from BaseAgent
        assert isinstance(supervisor_agent, BaseAgent)
        
        # Must have infrastructure enabled
        assert supervisor_agent._enable_reliability is True
        assert supervisor_agent._enable_execution_engine is True
        assert supervisor_agent._enable_caching is True
        
        # Must have BaseAgent infrastructure
        assert hasattr(supervisor_agent, 'unified_reliability_handler')
        assert hasattr(supervisor_agent, 'execution_engine')
        assert hasattr(supervisor_agent, 'execution_monitor')

    def test_ssot_infrastructure_compliance(self, supervisor_agent):
        """Test 2: Verify SSOT infrastructure usage."""
        # Should NOT have custom infrastructure
        assert not hasattr(supervisor_agent, 'monitor')  # Should use BaseAgent's
        assert not hasattr(supervisor_agent, 'reliability_manager')  # Should use BaseAgent's
        
        # Should have business logic components only
        assert hasattr(supervisor_agent, 'registry')
        assert hasattr(supervisor_agent, 'execution_helpers')
        assert hasattr(supervisor_agent, 'workflow_executor')
        
        # Legacy compatibility components
        assert hasattr(supervisor_agent, 'hooks')
        assert hasattr(supervisor_agent, 'completion_helpers')

    def test_abstract_methods_implemented(self, supervisor_agent):
        """Test 3: Verify abstract methods are implemented."""
        # Must have validate_preconditions
        assert hasattr(supervisor_agent, 'validate_preconditions')
        assert callable(supervisor_agent.validate_preconditions)
        
        # Must have execute_core_logic
        assert hasattr(supervisor_agent, 'execute_core_logic')
        assert callable(supervisor_agent.execute_core_logic)

    @pytest.mark.asyncio
    async def test_validate_preconditions(self, supervisor_agent):
        """Test 4: Validate preconditions implementation."""
        # Test with valid context
        state = DeepAgentState()
        state.user_request = "Test request"
        context = ExecutionContext(
            run_id="test_run",
            agent_name="Supervisor",
            state=state
        )
        
        # Mock registry to have agents
        supervisor_agent.registry.agents = {"test_agent": Mock()}
        
        result = await supervisor_agent.validate_preconditions(context)
        assert result is True
        
        # Test with missing user_request
        state.user_request = None
        result = await supervisor_agent.validate_preconditions(context)
        assert result is False
        
        # Test with no agents
        state.user_request = "Test request"
        supervisor_agent.registry.agents = {}
        result = await supervisor_agent.validate_preconditions(context)
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_core_logic_websocket_events(self, supervisor_agent):
        """Test 5: Verify WebSocket events are emitted during execution."""
        state = DeepAgentState()
        state.user_request = "Test orchestration request"
        
        context = ExecutionContext(
            run_id="test_run",
            agent_name="Supervisor", 
            state=state
        )
        
        # Mock WebSocket methods
        supervisor_agent.emit_thinking = AsyncMock()
        supervisor_agent.emit_progress = AsyncMock()
        
        # Execute core logic
        result = await supervisor_agent.execute_core_logic(context)
        
        # Verify WebSocket events were emitted
        supervisor_agent.emit_thinking.assert_any_call("Starting supervisor orchestration...")
        supervisor_agent.emit_thinking.assert_any_call("Coordinating with registered agents for optimal workflow")
        supervisor_agent.emit_progress.assert_any_call("Analyzing request and planning agent workflow...")
        supervisor_agent.emit_progress.assert_any_call("Orchestration completed successfully", is_complete=True)
        
        # Verify result structure
        assert result["supervisor_result"] == "completed"
        assert "updated_state" in result
        assert result["orchestration_successful"] is True

    @pytest.mark.asyncio
    async def test_backward_compatibility_execute(self, supervisor_agent):
        """Test 6: Verify backward compatible execute() method."""
        state = DeepAgentState()
        state.user_request = "Test request"
        run_id = "test_run"
        
        # Mock execute_modern method
        supervisor_agent.execute_modern = AsyncMock()
        
        # Call legacy execute method
        await supervisor_agent.execute(state, run_id, stream_updates=True)
        
        # Should delegate to execute_modern
        supervisor_agent.execute_modern.assert_called_once_with(state, run_id, True)

    @pytest.mark.asyncio
    async def test_backward_compatibility_run(self, supervisor_agent):
        """Test 7: Verify backward compatible run() method."""
        user_prompt = "Test user request"
        thread_id = "test_thread"
        user_id = "test_user"
        run_id = "test_run"
        
        # Mock validate_preconditions and execute_core_logic
        supervisor_agent.validate_preconditions = AsyncMock(return_value=True)
        supervisor_agent.execute_core_logic = AsyncMock(return_value={"status": "completed"})
        
        # Call legacy run method
        result = await supervisor_agent.run(user_prompt, thread_id, user_id, run_id)
        
        # Should return DeepAgentState
        assert isinstance(result, DeepAgentState)
        assert result.user_request == user_prompt
        assert result.thread_id == thread_id
        assert result.user_id == user_id
        
        # Should call modern methods
        supervisor_agent.validate_preconditions.assert_called_once()
        supervisor_agent.execute_core_logic.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_fallback_mechanism(self, supervisor_agent):
        """Test 8: Verify fallback to legacy execution helpers."""
        user_prompt = "Test user request"
        thread_id = "test_thread"
        user_id = "test_user"
        run_id = "test_run"
        
        # Mock validation to fail first, succeed in fallback
        supervisor_agent.validate_preconditions = AsyncMock(side_effect=Exception("Validation error"))
        
        # Mock execution helpers fallback
        fallback_state = DeepAgentState()
        fallback_state.user_request = user_prompt
        supervisor_agent.execution_helpers.run_supervisor_workflow = AsyncMock(return_value=fallback_state)
        
        # Call run method - should fallback gracefully
        result = await supervisor_agent.run(user_prompt, thread_id, user_id, run_id)
        
        # Should return fallback result
        assert isinstance(result, DeepAgentState)
        supervisor_agent.execution_helpers.run_supervisor_workflow.assert_called_once()

    def test_business_logic_only_architecture(self, supervisor_agent):
        """Test 9: Verify only business logic components exist."""
        # Should have ONLY business logic components
        business_components = [
            'registry', 'agent_registry',  # Agent orchestration
            'execution_helpers', 'workflow_executor',  # Business logic execution
            'hooks', 'completion_helpers',  # Legacy compatibility
            'db_session', 'state_persistence',  # Data persistence
            '_execution_lock'  # Coordination
        ]
        
        # Should NOT have infrastructure components
        infrastructure_violations = [
            'monitor', 'execution_engine', 'reliability_manager',  # Should use BaseAgent's
            'pipeline_executor', 'pipeline_builder',  # Complex infrastructure
            'flow_logger', 'utilities',  # Observability infrastructure
            'lifecycle_manager', 'workflow_orchestrator',  # Complex orchestration
            'error_handler'  # Should use BaseAgent's
        ]
        
        for component in business_components:
            assert hasattr(supervisor_agent, component), f"Missing business component: {component}"
        
        for violation in infrastructure_violations:
            assert not hasattr(supervisor_agent, violation), f"Infrastructure violation: {violation}"

    def test_websocket_inheritance(self, supervisor_agent):
        """Test 10: Verify WebSocket methods are inherited from BaseAgent."""
        # Should have WebSocket methods from BaseAgent
        websocket_methods = [
            'emit_thinking', 'emit_progress', 'emit_agent_started',
            'emit_agent_completed', 'emit_tool_executing', 'emit_tool_completed',
            'emit_error'
        ]
        
        for method in websocket_methods:
            assert hasattr(supervisor_agent, method), f"Missing WebSocket method: {method}"
            assert callable(getattr(supervisor_agent, method))

    def test_agent_registration_compatibility(self, supervisor_agent):
        """Test 11: Verify agent registration works."""
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # Mock agent
        mock_agent = Mock(spec=BaseAgent)
        
        # Register agent
        supervisor_agent.register_agent("test_agent", mock_agent)
        
        # Should call registry.register
        supervisor_agent.registry.register.assert_called_with("test_agent", mock_agent)

    def test_hook_registration_compatibility(self, supervisor_agent):
        """Test 12: Verify hook registration works."""
        def test_hook(state, **kwargs):
            pass
        
        # Register hook
        supervisor_agent.register_hook("before_agent", test_hook)
        
        # Should be in hooks
        assert test_hook in supervisor_agent.hooks["before_agent"]

    def test_stats_and_health_methods(self, supervisor_agent):
        """Test 13: Verify stats and health methods work."""
        # Should have stats methods
        assert callable(supervisor_agent.get_stats)
        assert callable(supervisor_agent.get_performance_metrics)
        
        # Should use completion helpers
        stats = supervisor_agent.get_stats()
        assert isinstance(stats, dict)
        
        metrics = supervisor_agent.get_performance_metrics()
        assert isinstance(metrics, dict)

    def test_line_count_compliance(self, supervisor_agent):
        """Test 14: Verify golden pattern line count (<300 lines)."""
        import inspect
        
        # Get source file
        source_file = inspect.getfile(supervisor_agent.__class__)
        
        with open(source_file, 'r') as f:
            lines = f.readlines()
        
        # Count non-empty, non-comment lines
        code_lines = [line for line in lines 
                     if line.strip() and not line.strip().startswith('#') 
                     and not line.strip().startswith('"""') 
                     and not line.strip().startswith("'''")]
        
        # Should be under golden pattern limit (<300 lines)
        assert len(code_lines) < 300, f"SupervisorAgent has {len(code_lines)} lines, exceeds golden pattern limit"

    @pytest.mark.asyncio
    async def test_hook_execution(self, supervisor_agent):
        """Test 15: Verify hook execution works correctly."""
        hook_called = False
        
        async def test_hook(state, **kwargs):
            nonlocal hook_called
            hook_called = True
        
        # Register hook
        supervisor_agent.hooks["before_agent"] = [test_hook]
        
        # Run hooks
        test_state = DeepAgentState()
        await supervisor_agent._run_hooks("before_agent", test_state)
        
        # Verify hook was called
        assert hook_called is True

    def test_properties_backward_compatibility(self, supervisor_agent):
        """Test 16: Verify properties for backward compatibility."""
        # Should have agents property
        agents = supervisor_agent.agents
        assert agents == supervisor_agent.registry.agents
        
        # Should have sub_agents property
        sub_agents = supervisor_agent.sub_agents
        assert hasattr(supervisor_agent, 'sub_agents')


class TestSupervisorAgentIntegration:
    """Integration tests for SupervisorAgent golden pattern."""
    
    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test complete execution flow with mocked dependencies."""
        # This test would require more complex setup with actual dependencies
        # For now, it's a placeholder for future integration tests
        pass

    @pytest.mark.asyncio 
    async def test_websocket_event_sequence(self):
        """Test that WebSocket events are emitted in correct sequence."""
        # This test would verify the complete WebSocket event flow
        # For now, it's a placeholder for future WebSocket integration tests
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])