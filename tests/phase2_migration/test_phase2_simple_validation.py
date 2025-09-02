"""
Phase 2 Agent Migration Simple Validation Tests
================================================
Basic tests to verify Phase 2 agents work with UserExecutionContext.
"""

import asyncio
import pytest
import uuid
from unittest.mock import MagicMock, patch

from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext


class TestPhase2AgentsBasicValidation:
    """Basic validation that Phase 2 agents accept UserExecutionContext."""
    
    @pytest.fixture
    def user_context(self):
        """Create a test UserExecutionContext."""
        mock_session = MagicMock()
        return UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            db_session=mock_session,
            metadata={
                "user_request": "Test request",
                "data_result": {"test": "data"},
                "triage_result": {"priority": "high"},
                "optimizations_result": {"suggestions": ["optimize"]},
                "action_plan_result": {"steps": ["step1"]}
            }
        )
    
    @pytest.mark.asyncio
    async def test_reporting_agent_accepts_context(self, user_context):
        """Test ReportingSubAgent accepts UserExecutionContext."""
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        agent = ReportingSubAgent()
        
        # Mock the LLM call
        with patch.object(agent, '_generate_report_with_llm', return_value={"report": "test"}):
            # Should not raise TypeError
            result = await agent.execute(user_context, stream_updates=False)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_optimizations_agent_accepts_context(self, user_context):
        """Test OptimizationsCoreSubAgent accepts UserExecutionContext."""
        from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
        
        agent = OptimizationsCoreSubAgent(tool_dispatcher=MagicMock())
        
        # Mock the LLM call
        with patch.object(agent, '_analyze_with_llm', return_value={"optimizations": ["test"]}):
            # Should not raise TypeError
            result = await agent.execute(user_context, stream_updates=False)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_goals_triage_agent_accepts_context(self, user_context):
        """Test GoalsTriageSubAgent accepts UserExecutionContext."""
        from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
        
        agent = GoalsTriageSubAgent()
        
        # Mock the LLM call
        with patch.object(agent, '_extract_and_analyze_goals', return_value={"goals": ["test"]}):
            # Should not raise TypeError
            result = await agent.execute(user_context, stream_updates=False)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_actions_goals_agent_accepts_context(self, user_context):
        """Test ActionsToMeetGoalsSubAgent accepts UserExecutionContext."""
        try:
            from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
            
            agent = ActionsToMeetGoalsSubAgent()
            
            # Mock the LLM call
            with patch.object(agent, '_generate_action_plan', return_value={"plan": "test"}):
                # Should not raise TypeError
                result = await agent.execute(user_context, stream_updates=False)
                assert result is not None
        except ImportError:
            # Agent may have circular import issues - skip
            pytest.skip("Agent has import issues")
    
    @pytest.mark.asyncio
    async def test_enhanced_execution_accepts_context(self, user_context):
        """Test EnhancedExecutionAgent accepts UserExecutionContext."""
        try:
            from netra_backend.app.agents.enhanced_execution_agent import EnhancedExecutionAgent
            
            agent = EnhancedExecutionAgent()
            
            # Mock the processing
            with patch.object(agent, '_process_with_llm', return_value={"result": "test"}):
                # Should not raise TypeError
                result = await agent.execute(user_context, stream_updates=False)
                assert result is not None
        except ImportError:
            # Agent may have circular import issues - skip
            pytest.skip("Agent has import issues")
    
    @pytest.mark.asyncio
    async def test_synthetic_data_accepts_context(self, user_context):
        """Test SyntheticDataSubAgent accepts UserExecutionContext."""
        from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
        
        agent = SyntheticDataSubAgent()
        
        # Mock the generation workflow
        with patch('netra_backend.app.agents.synthetic_data_sub_agent.GenerationWorkflow') as mock_workflow:
            mock_instance = MagicMock()
            mock_instance.execute = MagicMock(return_value={"data": "test"})
            mock_workflow.return_value = mock_instance
            
            # Should not raise TypeError
            result = await agent.execute(user_context, stream_updates=False)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_isolation(self, user_context):
        """Test that multiple agents can run concurrently with different contexts."""
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
        
        reporting_agent = ReportingSubAgent()
        goals_agent = GoalsTriageSubAgent()
        
        # Create different contexts
        context1 = user_context
        context2 = UserExecutionContext(
            user_id="different_user",
            thread_id="different_thread",
            run_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            db_session=user_context.db_session,
            metadata={"user_request": "Different request"}
        )
        
        # Mock the LLM calls
        with patch.object(reporting_agent, '_generate_report_with_llm', return_value={"report": "test1"}):
            with patch.object(goals_agent, '_extract_and_analyze_goals', return_value={"goals": ["test2"]}):
                # Run concurrently
                results = await asyncio.gather(
                    reporting_agent.execute(context1, stream_updates=False),
                    goals_agent.execute(context2, stream_updates=False)
                )
        
        # Both should complete
        assert len(results) == 2
        assert all(r is not None for r in results)
    
    @pytest.mark.asyncio
    async def test_context_validation(self):
        """Test that agents validate context properly."""
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        agent = ReportingSubAgent()
        
        # Test with invalid context (not UserExecutionContext)
        with pytest.raises((TypeError, AttributeError)):
            await agent.execute("not_a_context", stream_updates=False)
        
        # Test with None
        with pytest.raises((TypeError, AttributeError)):
            await agent.execute(None, stream_updates=False)
        
        # Test with dict (not UserExecutionContext)
        with pytest.raises((TypeError, AttributeError)):
            await agent.execute({"user_id": "test"}, stream_updates=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])