"""UVS Resilience Tests for ReportingSubAgent.

Business Value: Ensures ReportingSubAgent NEVER crashes and ALWAYS delivers value.
Test Coverage: All failure scenarios, partial data, and emergency fallbacks.
"""

import pytest
import uuid
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext


class TestReportingResilience:
    """Test suite for UVS resilience requirements."""
    
    @pytest.mark.asyncio
    async def test_no_data_still_delivers_value(self):
        """Test that agent delivers value even with absolutely no data."""
        # Arrange - Empty context with required IDs
        context = UserExecutionContext(
            user_id="test_user_1",
            thread_id="test_thread_1",
            run_id=str(uuid.uuid4())
        )
        agent = ReportingSubAgent(context=context)
        
        # Act
        report = await agent.execute(context, stream_updates=False)
        
        # Assert - Must return valid report
        assert report is not None
        assert report['report_type'] == 'guidance'
        assert 'next_steps' in report
        assert len(report['next_steps']) >= 3
        assert 'data_collection_guide' in report
        assert 'quick_assessment' in report
        assert report['status'] == 'awaiting_data'
    
    @pytest.mark.asyncio
    async def test_corrupted_context_recovery(self):
        """Test recovery from malformed context."""
        # Arrange - Create a mock context with broken metadata
        agent = ReportingSubAgent()
        
        # Create a mock context with broken metadata
        mock_context = mock_context_instance  # Initialize appropriate service
        mock_context.metadata = "NOT_A_DICT"  # Intentionally broken
        mock_context.user_id = "test_user"
        mock_context.thread_id = "test_thread"
        mock_context.run_id = "test_run"
        
        # Act
        report = await agent.execute(mock_context, stream_updates=False)
        
        # Assert - Must still return valid report
        assert report is not None
        assert report['report_type'] in ['guidance', 'fallback']
        assert 'next_steps' in report
        assert report.get('status') in ['awaiting_data', 'ready_to_help']
    
    @pytest.mark.asyncio
    async def test_none_context_handling(self):
        """Test handling of None context."""
        # Arrange
        agent = ReportingSubAgent(context=None)
        
        # Act - Pass None context
        report = await agent.execute(None, stream_updates=False)
        
        # Assert - Must handle gracefully
        assert report is not None
        assert 'next_steps' in report
        assert report['report_type'] in ['guidance', 'fallback']
    
    @pytest.mark.asyncio
    async def test_partial_data_report(self):
        """Test report generation with partial data."""
        # Arrange - Context with only some data
        context = UserExecutionContext(
            user_id="test_user_3",
            thread_id="test_thread_3",
            run_id=str(uuid.uuid4()),
            metadata={
                'data_result': {'usage': [1, 2, 3], 'total_cost': 100},
                # Missing optimizations and action plan
            }
        )
        agent = ReportingSubAgent(context=context)
        
        # Act
        report = await agent.execute(context, stream_updates=False)
        
        # Assert
        assert report['report_type'] == 'partial_analysis'
        assert 'data_insights' in report
        assert 'missing_data_guidance' in report
        assert 'next_steps' in report
        assert report['status'] == 'partial_complete'
    
    @pytest.mark.asyncio
    async def test_exception_during_full_report_generation(self):
        """Test fallback when full report generation fails."""
        # Arrange
        context = UserExecutionContext(
            user_id="test_user_4",
            thread_id="test_thread_4",
            run_id=str(uuid.uuid4()),
            metadata={
                'triage_result': {'status': 'complete'},
                'data_result': {'data': 'present'},
                'optimizations_result': {'optimizations': 'found'},
                'action_plan_result': {'plan': 'created'}
            }
        )
        agent = ReportingSubAgent(context=context)
        
        # Mock LLM to fail
        with patch.object(agent, '_execute_reporting_llm_with_observability', 
                         side_effect=Exception("Catastrophic LLM failure")):
            # Act
            report = await agent.execute(context, stream_updates=False)
        
        # Assert - Should fallback gracefully
        assert report is not None
        assert 'next_steps' in report
        # Should attempt partial report since we have data
        assert report['report_type'] in ['partial_analysis', 'guidance', 'fallback']
    
    @pytest.mark.asyncio
    async def test_websocket_failure_doesnt_crash(self):
        """Test that WebSocket failures don't crash report generation."""
        # Arrange
        context = UserExecutionContext(
            user_id="test_user_5",
            thread_id="test_thread_5",
            run_id=str(uuid.uuid4())
        )
        agent = ReportingSubAgent(context=context)
        
        # Mock WebSocket methods to fail
        agent.emit_agent_started = AsyncMock(side_effect=Exception("WebSocket failed"))
        agent.emit_thinking = AsyncMock(side_effect=Exception("WebSocket failed"))
        agent.emit_agent_completed = AsyncMock(side_effect=Exception("WebSocket failed"))
        
        # Act
        report = await agent.execute(context, stream_updates=True)
        
        # Assert - Must still generate report
        assert report is not None
        assert 'next_steps' in report
        assert report['report_type'] in ['guidance', 'fallback']
    
    @pytest.mark.asyncio
    async def test_cache_failure_doesnt_crash(self):
        """Test that cache failures don't crash report generation."""
        # Arrange
        context = UserExecutionContext(
            user_id="test_user_6",
            thread_id="test_thread_6",
            run_id=str(uuid.uuid4()),
            metadata={
                'data_result': {'test': 'data'}
            }
        )
        agent = ReportingSubAgent(context=context)
        
        # Mock cache to fail
        with patch.object(agent, '_get_cached_report', 
                         side_effect=Exception("Redis connection failed")):
            with patch.object(agent, '_cache_report_result',
                            side_effect=Exception("Cache write failed")):
                # Act
                report = await agent.execute(context, stream_updates=False)
        
        # Assert - Must still work without cache
        assert report is not None
        assert 'next_steps' in report
    
    @pytest.mark.asyncio
    async def test_emergency_fallback_always_works(self):
        """Test that emergency fallback NEVER fails."""
        # Arrange
        agent = ReportingSubAgent()
        
        # Test with various broken contexts
        test_cases = [
            None,
            "broken",
            123,
            {"broken": object()},
            Mock(spec=None),
        ]
        
        for test_context in test_cases:
            # Act
            report = agent._get_emergency_fallback_report(
                test_context, 
                Exception("Test error")
            )
            
            # Assert
            assert report is not None
            assert report['report_type'] == 'fallback'
            assert 'next_steps' in report
            assert report['status'] == 'ready_to_help'
    
    @pytest.mark.asyncio
    async def test_template_enhancement_failure_handled(self):
        """Test that template enhancement failures are handled."""
        # Arrange
        context = UserExecutionContext(
            user_id="test_user_7",
            thread_id="test_thread_7",
            run_id=str(uuid.uuid4())
        )
        agent = ReportingSubAgent(context=context)
        
        # Mock template enhancement to fail
        with patch.object(agent._templates, 'enhance_with_context',
                         side_effect=Exception("Enhancement failed")):
            # Act
            report = agent._get_emergency_fallback_report(context, Exception("Test"))
        
        # Assert - Should still return valid template
        assert report is not None
        assert 'next_steps' in report
    
    @pytest.mark.asyncio
    async def test_all_tiers_have_next_steps(self):
        """Test that all report tiers include actionable next_steps."""
        context = UserExecutionContext(
            user_id="test_user_8",
            thread_id="test_thread_8",
            run_id=str(uuid.uuid4())
        )
        agent = ReportingSubAgent(context=context)
        
        # Test guidance report (no data)
        report = await agent._generate_guidance_report(context, {}, False)
        assert 'next_steps' in report
        assert len(report['next_steps']) >= 3
        
        # Test partial report
        assessment = {
            'has_partial_data': True,
            'available_sections': ['data insights'],
            'has_data': True
        }
        # Create new context with metadata
        context = UserExecutionContext(
            user_id="test_user_8b",
            thread_id="test_thread_8b",
            run_id=str(uuid.uuid4()),
            metadata={'data_result': {'test': 'data'}}
        )
        report = await agent._generate_partial_report(context, assessment, False)
        assert 'next_steps' in report
        assert len(report['next_steps']) >= 3
    
    @pytest.mark.asyncio
    async def test_data_assessment_with_pydantic_models(self):
        """Test data assessment handles Pydantic models correctly."""
        # Arrange
        from netra_backend.app.agents.state import OptimizationsResult, ActionPlanResult
        
        context = UserExecutionContext(
            user_id="test_user_9",
            thread_id="test_thread_9",
            run_id=str(uuid.uuid4()),
            metadata={
                'optimizations_result': OptimizationsResult(
                    optimization_type='cost',
                    recommendations=['Test rec 1', 'Test rec 2']
                ),
                'action_plan_result': ActionPlanResult(
                    action_plan_summary='Test plan'
                )
            }
        )
        agent = ReportingSubAgent(context=context)
        
        # Act
        assessment = agent._assess_available_data(context)
        
        # Assert
        assert assessment['has_optimizations'] is True
        assert assessment['has_action_plan'] is True
        assert assessment['has_partial_data'] is True
        assert 'optimization recommendations' in assessment['available_sections']
    
    @pytest.mark.asyncio
    async def test_format_methods_handle_all_types(self):
        """Test that format methods handle various input types."""
        agent = ReportingSubAgent()
        
        # Test with dict
        result = agent._format_data_insights({'key': 'value'})
        assert 'summary' in result
        
        # Test with string
        result = agent._format_data_insights("string data")
        assert 'summary' in result
        
        # Test with None
        result = agent._format_data_insights(None)
        assert 'summary' in result
        
        # Test with Pydantic model mock
        mock_model = mock_model_instance  # Initialize appropriate service
        mock_model.model_dump = Mock(return_value={'test': 'data'})
        result = agent._format_optimization_insights(mock_model)
        assert 'summary' in result
    
    @pytest.mark.asyncio
    async def test_extreme_stress_conditions(self):
        """Test under extreme failure conditions."""
        # Arrange - Everything is broken
        agent = ReportingSubAgent()
        
        # Break everything we can
        agent.logger = Mock(side_effect=Exception("Logger broken"))
        agent._templates = None
        agent.llm_manager = None
        agent.redis_manager = None
        
        # Act - Should still not crash
        report = await agent.execute(None, stream_updates=False)
        
        # Assert
        assert report is not None
        assert 'next_steps' in report
        assert report['report_type'] == 'fallback'
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_isolation(self):
        """Test that concurrent executions don't interfere."""
        import asyncio
        
        async def run_report(user_id: str) -> Dict[str, Any]:
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{user_id}",
                run_id=str(uuid.uuid4()),
                metadata={'user_request': f'Request from {user_id}'}
            )
            agent = ReportingSubAgent(context=context)
            return await agent.execute(context, stream_updates=False)
        
        # Act - Run multiple reports concurrently
        reports = await asyncio.gather(
            run_report("user1"),
            run_report("user2"),
            run_report("user3"),
            return_exceptions=True
        )
        
        # Assert - All should succeed independently
        for report in reports:
            assert not isinstance(report, Exception)
            assert report is not None
            assert 'next_steps' in report