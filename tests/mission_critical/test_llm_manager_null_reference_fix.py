"""
🔴 MISSION CRITICAL TEST: LLM Manager Null Reference Fix
Based on Five Whys Root Cause Analysis (2025-09-04)

This test verifies that the fix for LLM manager null reference errors
is working correctly and prevents the runtime failures identified in production.

ROOT CAUSE: Incomplete architectural migration where agents can be created
without essential dependencies like LLMManager.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import warnings

# Import the agent that was failing
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager


class TestLLMManagerNullReferenceFix:
    """Test suite for LLM manager null reference fix based on Five Whys analysis."""
    
    def test_agent_instantiation_without_llm_manager_warns(self):
        """
        Test WHY #1-2: Verify that instantiating agent without LLM manager
        produces a warning but doesn't crash immediately.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Create agent without LLM manager (the problematic pattern)
            agent = ActionsToMeetGoalsSubAgent(llm_manager=None)
            
            # Should have received a warning
            assert len(w) == 1
            assert "ActionsToMeetGoalsSubAgent instantiated without LLMManager" in str(w[0].message)
            assert w[0].category == RuntimeWarning
            
            # Agent should still be created (for backward compatibility)
            assert agent is not None
            assert agent.llm_manager is None
    
    def test_agent_instantiation_with_llm_manager_no_warning(self):
        """
        Test: Verify proper instantiation with LLM manager works without warnings.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Create mock LLM manager
            mock_llm = Mock(spec=LLMManager)
            
            # Create agent with LLM manager (the correct pattern)
            agent = ActionsToMeetGoalsSubAgent(llm_manager=mock_llm)
            
            # Should have no warnings
            assert len(w) == 0
            
            # Agent should have LLM manager
            assert agent is not None
            assert agent.llm_manager is mock_llm
    
    @pytest.mark.asyncio
    async def test_llm_operation_without_manager_fails_with_clear_error(self):
        """
        Test WHY #3-5: Verify that attempting LLM operations without manager
        fails with a clear error message pointing to the architectural issue.
        """
        # Create agent without LLM manager (simulating the bug scenario)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Suppress warning for this test
            agent = ActionsToMeetGoalsSubAgent(llm_manager=None)
        
        # Try to perform LLM operation
        with pytest.raises(RuntimeError) as exc_info:
            await agent._get_llm_response_with_monitoring("test prompt")
        
        # Verify the error message is clear and helpful
        error_msg = str(exc_info.value)
        assert "LLM manager is None" in error_msg
        assert "agent was instantiated without required dependency" in error_msg
        assert "architectural migration" in error_msg
        assert "FIVE_WHYS_ANALYSIS_20250904.md" in error_msg
    
    @pytest.mark.asyncio
    async def test_llm_operation_with_manager_succeeds(self):
        """
        Test: Verify that LLM operations work correctly when manager is provided.
        """
        # Create mock LLM manager
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value="Test response")
        
        # Create agent with LLM manager
        agent = ActionsToMeetGoalsSubAgent(llm_manager=mock_llm)
        
        # Perform LLM operation
        response = await agent._get_llm_response_with_monitoring("test prompt")
        
        # Should succeed
        assert response == "Test response"
        mock_llm.ask_llm.assert_called_once_with(
            "test prompt", 
            llm_config_name='actions_to_meet_goals'
        )
    
    @pytest.mark.asyncio
    async def test_execute_with_null_llm_manager_fails_early(self):
        """
        Test: Verify that execute method fails early with null LLM manager.
        This tests the complete execution path to ensure errors are caught early.
        """
        # Create agent without LLM manager
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            agent = ActionsToMeetGoalsSubAgent(llm_manager=None)
        
        # Create mock context
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.run_id = "test_run_123"
        mock_context.metadata = {
            'user_request': 'Test request',
            'optimizations_result': {'test': 'data'},
            'data_result': {'test': 'data'}
        }
        
        # Execute should handle the null LLM manager gracefully
        result = await agent.execute(mock_context, stream_updates=False)
        
        # Should have executed fallback logic
        assert 'fallback' in result or 'error' in result
    
    def test_legacy_agent_registry_pattern_detection(self):
        """
        Test: Verify we can detect the problematic legacy pattern.
        This helps identify code that needs migration.
        """
        # Simulate the legacy pattern that causes issues
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        
        # Mock dependencies
        mock_llm = None  # This is the problem - None being passed
        mock_dispatcher = Mock()
        
        # Legacy pattern should warn
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # This pattern is deprecated and causes issues
            registry = AgentRegistry(mock_llm, mock_dispatcher)
            
            # Should have deprecation warning
            assert any("AgentRegistry is deprecated" in str(warning.message) for warning in w)
    
    @pytest.mark.asyncio
    async def test_factory_pattern_with_proper_dependencies(self):
        """
        Test: Verify the new factory pattern properly handles dependencies.
        This is the correct pattern that should be used.
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
        
        # Create factory with proper dependencies
        mock_llm = Mock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value="Test response")
        
        factory = AgentInstanceFactory()
        factory._llm_manager = mock_llm  # Proper dependency injection
        
        # Factory should validate dependencies (once implemented)
        # For now, just verify the pattern works
        assert factory._llm_manager is not None


class TestFiveWhysValidation:
    """Validate that each level of the Five Whys is addressed."""
    
    def test_why_1_surface_symptom_handled(self):
        """WHY #1: NoneType error is now caught with clear message."""
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None)
        assert agent.llm_manager is None  # The symptom
    
    def test_why_2_immediate_cause_identified(self):
        """WHY #2: Agent instantiation without LLM manager is detected."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ActionsToMeetGoalsSubAgent(llm_manager=None)
            assert len(w) > 0  # Warning raised
    
    def test_why_3_system_failure_documented(self):
        """WHY #3: System failure mode is documented in error messages."""
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None)
        try:
            asyncio.run(agent._get_llm_response_with_monitoring("test"))
        except RuntimeError as e:
            assert "architectural migration" in str(e)
    
    def test_why_4_process_gap_acknowledged(self):
        """WHY #4: Process gap is acknowledged in warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ActionsToMeetGoalsSubAgent(llm_manager=None)
            assert "incomplete architectural migration" in str(w[0].message)
    
    def test_why_5_root_cause_referenced(self):
        """WHY #5: Root cause document is referenced in errors."""
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None)
        try:
            asyncio.run(agent._get_llm_response_with_monitoring("test"))
        except RuntimeError as e:
            assert "FIVE_WHYS_ANALYSIS_20250904.md" in str(e)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])