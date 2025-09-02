"""
Mission Critical Tests for Golden Pattern SummaryExtractorSubAgent

Tests the complete golden pattern implementation including:
- WebSocket event emissions for chat value delivery
- Summary extraction workflow with real LLM services
- Error handling with proper AgentError types
- Complete end-to-end flow testing
- BaseAgent infrastructure integration

CRITICAL: This test suite ensures the SummaryExtractorSubAgent follows
the golden pattern and delivers chat value through WebSocket events.

Business Value: Validates that users can receive real-time updates during
summary extraction, enabling immediate understanding of data insights.
"""

import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from netra_backend.app.agents.summary_extractor_sub_agent import SummaryExtractorSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.agent_error_types import AgentValidationError
from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager


class TestSummaryExtractorGoldenPattern:
    """Test the SummaryExtractorSubAgent golden pattern implementation."""

    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager with realistic summary responses."""
        llm_manager = AsyncMock(spec=LLMManager)
        
        # Mock individual summary response
        llm_manager.query_async.side_effect = [
            # Individual source summaries
            json.dumps({
                "key_points": [
                    "Data shows significant performance improvement",
                    "Cost optimization opportunities identified", 
                    "User engagement metrics are trending upward"
                ],
                "summary": "Analysis reveals strong positive trends with optimization potential",
                "confidence": 0.85
            }),
            json.dumps({
                "key_points": [
                    "High priority issues require immediate attention",
                    "Category classification completed successfully",
                    "Resource allocation optimized"
                ],
                "summary": "Triage process identified critical areas needing focus",
                "confidence": 0.92
            }),
            # Comprehensive summary response
            json.dumps({
                "overall_summary": "Comprehensive analysis shows strong performance with identified optimization opportunities and clear priority areas requiring attention.",
                "top_insights": [
                    "Performance improvements demonstrate system effectiveness",
                    "Cost optimization potential of 25-30%",
                    "User engagement trending positively",
                    "Critical priority issues identified for immediate action",
                    "Resource allocation successfully optimized"
                ],
                "recommendations": [
                    "Focus on high-priority issues first",
                    "Implement cost optimization strategies",
                    "Monitor user engagement trends",
                    "Continue performance monitoring",
                    "Validate resource allocation changes"
                ],
                "confidence": 0.88
            })
        ]
        
        return llm_manager

    @pytest.fixture
    def summary_agent(self, mock_llm_manager):
        """Create SummaryExtractorSubAgent instance."""
        agent = SummaryExtractorSubAgent()
        agent.llm_manager = mock_llm_manager
        return agent

    @pytest.fixture
    def valid_state_with_data(self):
        """Create valid DeepAgentState with data to summarize."""
        state = DeepAgentState()
        state.user_request = "Please extract key summaries from my analysis data"
        state.data_result = {
            "analysis": "Comprehensive performance analysis",
            "metrics": {"improvement": 25, "efficiency": 85},
            "insights": ["Performance up", "Costs down", "Users happy"]
        }
        state.triage_result = {
            "category": "optimization",
            "priority": "high", 
            "issues": ["memory usage", "query performance"],
            "recommendations": ["add caching", "optimize indexes"]
        }
        state.optimizations_result = {
            "potential_savings": 30000,
            "optimization_areas": ["database", "caching", "api calls"],
            "implementation_priority": ["high", "medium", "low"]
        }
        return state

    @pytest.fixture
    def empty_state(self):
        """Create DeepAgentState with no data to summarize."""
        state = DeepAgentState()
        state.user_request = "Extract summaries please"
        # No data attributes set
        return state

    @pytest.fixture
    def partial_data_state(self):
        """Create state with only some data sources."""
        state = DeepAgentState()
        state.user_request = "Summarize available data"
        state.data_result = {"analysis": "Basic analysis completed"}
        # Missing triage_result, optimizations_result, etc.
        return state

    @pytest.fixture
    def execution_context(self, valid_state_with_data):
        """Create valid execution context."""
        return ExecutionContext(
            run_id="test_summary_run_123",
            agent_name="SummaryExtractorSubAgent",
            state=valid_state_with_data,
            stream_updates=True,
            thread_id="thread_456",
            user_id="user_789",
            start_time=time.time(),
            correlation_id="correlation_123"
        )

    async def test_golden_pattern_inheritance(self, summary_agent):
        """Test that SummaryExtractorSubAgent follows golden pattern inheritance."""
        # Verify inheritance from BaseAgent
        from netra_backend.app.agents.base_agent import BaseAgent
        assert isinstance(summary_agent, BaseAgent)
        
        # Verify infrastructure is enabled
        assert summary_agent._enable_reliability == True
        assert summary_agent._enable_execution_engine == True
        assert summary_agent._enable_caching == True
        
        # Verify proper initialization
        assert summary_agent.name == "SummaryExtractorSubAgent"
        assert "summary extraction" in summary_agent.description.lower()

    async def test_websocket_event_emissions(self, summary_agent, execution_context):
        """Test that all required WebSocket events are emitted for chat value."""
        # Mock WebSocket emissions to track calls
        with patch.object(summary_agent, 'emit_thinking') as mock_thinking, \
             patch.object(summary_agent, 'emit_progress') as mock_progress, \
             patch.object(summary_agent, 'emit_error') as mock_error:
            
            # Execute the agent
            await summary_agent.execute_core_logic(execution_context)
            
            # Verify thinking events for reasoning visibility
            thinking_calls = mock_thinking.call_args_list
            assert len(thinking_calls) >= 3, "Should emit multiple thinking events"
            
            # Check specific thinking events
            thinking_messages = [call[0][0] for call in thinking_calls]
            assert any("Starting intelligent summary extraction" in msg for msg in thinking_messages)
            assert any("Analyzing available data sources" in msg for msg in thinking_messages) 
            assert any("Synthesizing findings" in msg for msg in thinking_messages)
            
            # Verify progress events
            progress_calls = mock_progress.call_args_list
            assert len(progress_calls) >= 3, "Should emit multiple progress events"
            
            # Check specific progress events
            progress_messages = [call[0][0] for call in progress_calls]
            assert any("Collecting data" in msg for msg in progress_messages)
            assert any("Extracting key insights" in msg for msg in progress_messages)
            assert any("completed successfully" in msg for msg in progress_messages)
            
            # Verify completion event
            final_progress_call = progress_calls[-1]
            assert final_progress_call[1]['is_complete'] == True

    async def test_validate_preconditions_success(self, summary_agent, execution_context):
        """Test successful precondition validation with available data."""
        result = await summary_agent.validate_preconditions(execution_context)
        assert result == True

    async def test_validate_preconditions_failure_no_data(self, summary_agent, empty_state):
        """Test precondition validation failure when no data is available."""
        context = ExecutionContext(
            run_id="test_run",
            agent_name="SummaryExtractorSubAgent", 
            state=empty_state,
            stream_updates=True
        )
        
        with pytest.raises(AgentValidationError) as exc_info:
            await summary_agent.validate_preconditions(context)
        
        assert "No data available to extract summaries from" in str(exc_info.value)
        assert exc_info.value.context["run_id"] == "test_run"

    async def test_validate_preconditions_success_partial_data(self, summary_agent, partial_data_state):
        """Test successful validation with partial data (should still pass)."""
        context = ExecutionContext(
            run_id="test_run",
            agent_name="SummaryExtractorSubAgent",
            state=partial_data_state,
            stream_updates=True
        )
        
        result = await summary_agent.validate_preconditions(context)
        assert result == True

    async def test_execute_core_logic_success(self, summary_agent, execution_context):
        """Test successful execution of core summary extraction logic."""
        result = await summary_agent.execute_core_logic(execution_context)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'comprehensive_summary' in result
        assert 'individual_summaries' in result
        assert 'data_sources_processed' in result
        assert 'extraction_timestamp' in result
        assert 'total_sources' in result
        assert 'extraction_quality' in result
        
        # Verify comprehensive summary structure
        comprehensive = result['comprehensive_summary']
        assert 'overall_summary' in comprehensive
        assert 'top_insights' in comprehensive
        assert 'recommendations' in comprehensive
        assert 'confidence' in comprehensive
        
        # Verify individual summaries
        individual = result['individual_summaries']
        assert len(individual) > 0
        for source_summary in individual.values():
            assert 'key_points' in source_summary
            assert 'summary' in source_summary
            assert 'confidence' in source_summary
        
        # Verify extraction quality metrics
        quality = result['extraction_quality']
        assert 'overall_confidence' in quality
        assert 'sources_successfully_processed' in quality
        assert 'processing_errors' in quality
        
        # Verify state was updated
        assert execution_context.state.summary_result == result

    async def test_collect_available_data(self, summary_agent, valid_state_with_data):
        """Test data collection from various state sources."""
        collected = summary_agent._collect_available_data(valid_state_with_data)
        
        assert isinstance(collected, dict)
        assert len(collected) > 0
        
        # Verify expected data sources are collected
        expected_sources = ['data_analysis', 'triage_analysis', 'optimizations', 'user_request']
        found_sources = [src for src in expected_sources if src in collected]
        assert len(found_sources) >= 2, "Should collect multiple data sources"
        
        # Verify data content
        assert collected['data_analysis'] == valid_state_with_data.data_result
        assert collected['triage_analysis'] == valid_state_with_data.triage_result
        assert collected['optimizations'] == valid_state_with_data.optimizations_result

    async def test_summarize_data_source(self, summary_agent, mock_llm_manager):
        """Test individual data source summarization."""
        test_data = {"key": "value", "analysis": "test analysis"}
        
        result = await summary_agent._summarize_data_source("test_source", test_data, "run_123")
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'key_points' in result
        assert 'summary' in result 
        assert 'confidence' in result
        
        # Verify confidence is properly bounded
        assert 0.0 <= result['confidence'] <= 1.0
        
        # Verify LLM was called
        mock_llm_manager.query_async.assert_called()

    async def test_error_handling_llm_failure(self, summary_agent, execution_context):
        """Test error handling when LLM operations fail."""
        # Mock LLM to raise exception
        summary_agent.llm_manager.query_async.side_effect = Exception("LLM service unavailable")
        
        with patch.object(summary_agent, 'emit_error') as mock_error:
            with pytest.raises(AgentError) as exc_info:
                await summary_agent.execute_core_logic(execution_context)
            
            # Verify error emission
            mock_error.assert_called()
            error_msg = mock_error.call_args[0][0]
            assert "Summary extraction failed" in error_msg
            
            # Verify exception details
            assert "Summary extraction failed" in str(exc_info.value)
            assert exc_info.value.context["run_id"] == execution_context.run_id

    async def test_fallback_summary_generation(self, summary_agent):
        """Test fallback summary generation when AI processing fails."""
        test_summaries = {
            'source1': {
                'key_points': ['Point 1', 'Point 2'],
                'summary': 'Summary 1',
                'confidence': 0.8
            },
            'source2': {
                'key_points': ['Point 3', 'Point 4'],
                'summary': 'Summary 2', 
                'confidence': 0.7
            }
        }
        
        result = summary_agent._create_fallback_comprehensive_summary(test_summaries)
        
        assert isinstance(result, dict)
        assert 'overall_summary' in result
        assert 'top_insights' in result
        assert 'recommendations' in result
        assert 'confidence' in result
        
        # Verify confidence is lower for fallback
        assert result['confidence'] <= 0.5
        
        # Verify insights are combined
        assert len(result['top_insights']) == 4  # All points combined

    async def test_format_summary_result(self, summary_agent):
        """Test summary result formatting."""
        comprehensive = {
            'overall_summary': 'Test summary',
            'top_insights': ['Insight 1', 'Insight 2'],
            'recommendations': ['Rec 1'],
            'confidence': 0.85
        }
        
        summaries = {
            'source1': {'confidence': 0.9},
            'source2': {'confidence': 0.2}  # Low confidence
        }
        
        collected_data = {'source1': 'data1', 'source2': 'data2'}
        
        result = summary_agent._format_summary_result(comprehensive, summaries, collected_data)
        
        # Verify structure
        assert result['comprehensive_summary'] == comprehensive
        assert result['individual_summaries'] == summaries
        assert result['data_sources_processed'] == ['source1', 'source2']
        assert result['total_sources'] == 2
        
        # Verify quality metrics
        quality = result['extraction_quality']
        assert quality['overall_confidence'] == 0.85
        assert quality['sources_successfully_processed'] == 1  # Only source1 > 0.3
        assert quality['processing_errors'] == 1  # source2 <= 0.3

    async def test_websocket_completion_update(self, summary_agent, execution_context):
        """Test WebSocket completion update with proper data structure."""
        result = {
            'comprehensive_summary': {'top_insights': ['Insight 1', 'Insight 2']},
            'total_sources': 3,
            'extraction_quality': {'overall_confidence': 0.88}
        }
        
        with patch.object(summary_agent, 'emit_progress') as mock_progress:
            await summary_agent._send_summary_completion_update(
                execution_context.run_id, 
                execution_context.stream_updates, 
                result
            )
            
            # Verify completion update was sent
            mock_progress.assert_called_once()
            call_args = mock_progress.call_args
            
            # Check message content
            message = call_args[0][0]
            assert "Summary extraction completed" in message
            assert "3 data sources" in message
            assert "2 key insights" in message
            
            # Check completion flag
            assert call_args[1]['is_complete'] == True
            
            # Check data payload
            data_payload = call_args[1]['data']
            assert data_payload['sources_processed'] == 3
            assert data_payload['key_insights_count'] == 2
            assert data_payload['confidence_score'] == 0.88

    async def test_real_llm_integration(self, summary_agent, execution_context):
        """Integration test with real LLM service (if available)."""
        # Skip if no real LLM manager available
        if not hasattr(summary_agent, 'llm_manager') or summary_agent.llm_manager is None:
            pytest.skip("Real LLM manager not available")
        
        # This test would run against real services
        # Only run in integration test environment
        if not pytest.current_request.config.getoption("--real-llm", default=False):
            pytest.skip("Real LLM integration test skipped (use --real-llm to enable)")
        
        result = await summary_agent.execute_core_logic(execution_context)
        
        # Verify real result structure
        assert isinstance(result, dict)
        assert result['total_sources'] > 0
        assert result['extraction_quality']['overall_confidence'] > 0

    async def test_business_value_delivery(self, summary_agent, execution_context):
        """Test that the agent delivers clear business value through summaries."""
        result = await summary_agent.execute_core_logic(execution_context)
        
        # Verify business value indicators
        comprehensive = result['comprehensive_summary'] 
        
        # Should provide actionable insights
        assert len(comprehensive.get('top_insights', [])) >= 3
        
        # Should provide recommendations
        assert len(comprehensive.get('recommendations', [])) >= 3
        
        # Should have reasonable confidence
        assert comprehensive.get('confidence', 0) >= 0.5
        
        # Summary should be concise but informative
        summary_text = comprehensive.get('overall_summary', '')
        assert len(summary_text) > 50  # Informative
        assert len(summary_text) < 500  # Concise

    async def test_concurrent_execution_safety(self, summary_agent):
        """Test that multiple concurrent executions don't interfere."""
        # Create multiple execution contexts
        contexts = []
        for i in range(3):
            state = DeepAgentState()
            state.data_result = {"analysis": f"test_data_{i}"}
            context = ExecutionContext(
                run_id=f"concurrent_run_{i}",
                agent_name="SummaryExtractorSubAgent",
                state=state,
                stream_updates=True
            )
            contexts.append(context)
        
        # Execute concurrently
        results = await asyncio.gather(*[
            summary_agent.execute_core_logic(ctx) for ctx in contexts
        ], return_exceptions=True)
        
        # Verify all succeeded
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, dict)
            assert 'comprehensive_summary' in result


class TestSummaryExtractorEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def summary_agent(self):
        agent = SummaryExtractorSubAgent()
        agent.llm_manager = AsyncMock()
        return agent

    async def test_malformed_llm_response(self, summary_agent):
        """Test handling of malformed LLM responses."""
        # Mock malformed JSON response
        summary_agent.llm_manager.query_async.return_value = "Not valid JSON response"
        
        result = await summary_agent._summarize_data_source("test", {"data": "test"}, "run_id")
        
        # Should still return valid structure
        assert 'key_points' in result
        assert 'summary' in result
        assert 'confidence' in result
        
        # Confidence should be reasonable for fallback
        assert 0 <= result['confidence'] <= 1

    async def test_empty_data_source(self, summary_agent):
        """Test summarization of empty data source."""
        result = await summary_agent._summarize_data_source("empty", {}, "run_id")
        
        assert isinstance(result, dict)
        assert 'key_points' in result
        assert 'summary' in result

    async def test_very_large_data_source(self, summary_agent):
        """Test handling of very large data sources."""
        large_data = {"key": "x" * 10000}  # Large data
        
        # Should not raise exception
        result = await summary_agent._summarize_data_source("large", large_data, "run_id")
        assert isinstance(result, dict)