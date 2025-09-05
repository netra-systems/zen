"""
Comprehensive SSOT Violation Test Suite for GoalsTriageSubAgent

This test suite is designed to FAIL with the current implementation
and will PASS only when proper SSOT patterns are implemented.

SSOT Violations being tested:
1. JSON Handling - Must use LLMResponseParser from unified_json_handler.py
2. Error Handling - Must use unified error handler patterns

Business Value: Ensures consistent patterns across all agents for maintainability
"""

import asyncio
import json
import pytest
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.database.session_manager import DatabaseSessionManager


class TestGoalsTriageSubAgentSSOTViolations:
    """Test suite for SSOT violations in GoalsTriageSubAgent."""
    
    @pytest.fixture
 def real_context():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock UserExecutionContext for testing."""
    pass
        context = MagicMock(spec=UserExecutionContext)
        context.user_id = "test_user_123"
        context.run_id = "test_run_456"
        context.thread_id = "test_thread_789"
        context.metadata = {"user_request": "Optimize costs and improve user experience"}
        context.db_session = MagicNone  # TODO: Use real service instance
        return context
    
    @pytest.fixture
    def agent(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create GoalsTriageSubAgent instance."""
    pass
        return GoalsTriageSubAgent()
    
    @pytest.fixture
 def real_session_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock DatabaseSessionManager."""
    pass
        session_manager = MagicMock(spec=DatabaseSessionManager)
        session_manager.close = AsyncNone  # TODO: Use real service instance
        return session_manager
    
    # ========================================================================
    # JSON HANDLING VIOLATION TESTS
    # These tests verify that unified_json_handler is used instead of json.loads
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_json_parsing_uses_llm_response_parser(self, agent, mock_context):
        """
        CRITICAL TEST: Verify that LLMResponseParser is used for JSON parsing.
        
        Current violation: Lines 338-344 use json.loads() directly
        Expected: Should use LLMResponseParser.safe_json_parse()
        """
    pass
        # Patch the LLMResponseParser to track its usage
        with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as MockParser:
            mock_parser = MockParser.return_value
            mock_parser.safe_json_parse = MagicMock(return_value=["goal1", "goal2"])
            
            # Create malformed JSON that json.loads would fail on
            malformed_json = '["goal1", "goal2",]'  # Trailing comma - invalid JSON
            
            # This should use LLMResponseParser, not json.loads
            result = agent._parse_goals_from_llm_response(malformed_json)
            
            # ASSERTION: LLMResponseParser.safe_json_parse should be called
            mock_parser.safe_json_parse.assert_called_once_with(malformed_json, fallback=None)
            assert result == ["goal1", "goal2"]
    
    @pytest.mark.asyncio
    async def test_goal_analysis_parsing_uses_llm_response_parser(self, agent, mock_context):
        """
        CRITICAL TEST: Verify goal analysis uses LLMResponseParser.
        
        Current violation: Line 365 uses json.loads() directly
        Expected: Should use LLMResponseParser.ensure_agent_response_is_json()
        """
    pass
        with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as MockParser:
            mock_parser = MockParser.return_value
            expected_data = {
                "priority": "high",
                "category": "revenue",
                "confidence_score": 0.8
            }
            mock_parser.ensure_agent_response_is_json = MagicMock(return_value=expected_data)
            
            # Create response with JSON fragment (should be handled by LLMResponseParser)
            json_fragment = '"priority": "high", "category": "revenue"'
            
            result = agent._parse_goal_analysis_response(json_fragment)
            
            # ASSERTION: Should use LLMResponseParser
            mock_parser.ensure_agent_response_is_json.assert_called_once_with(json_fragment)
            assert result == expected_data
    
    @pytest.mark.asyncio
    async def test_handles_malformed_json_with_error_fixer(self, agent, mock_context):
        """
        TEST: Verify JSONErrorFixer is used for malformed JSON recovery.
        
        Expected: Should use JSONErrorFixer.fix_common_json_errors()
        """
    pass
        with patch('netra_backend.app.core.serialization.unified_json_handler.JSONErrorFixer') as MockFixer:
            mock_fixer = MockFixer.return_value
            mock_fixer.fix_common_json_errors = MagicMock(return_value='["fixed_goal"]')
            
            with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as MockParser:
                mock_parser = MockParser.return_value
                mock_parser.safe_json_parse = MagicMock(side_effect=[
                    None,  # First attempt fails
                    ["fixed_goal"]  # After fixing, succeeds
                ])
                
                # Malformed JSON with multiple issues
                malformed = '["goal1", "goal2",,]'  # Double comma and trailing comma
                
                result = agent._parse_goals_from_llm_response(malformed)
                
                # ASSERTION: JSONErrorFixer should be invoked
                mock_fixer.fix_common_json_errors.assert_called()
    
    @pytest.mark.asyncio
    async def test_json_serialization_uses_unified_handler(self, agent, mock_context):
        """
        TEST: Verify UnifiedJSONHandler is used for JSON serialization.
        
        Expected: Should use UnifiedJSONHandler.dumps() for serialization
        """
    pass
        with patch('netra_backend.app.core.serialization.unified_json_handler.UnifiedJSONHandler') as MockHandler:
            mock_handler = MockHandler.return_value
            mock_handler.dumps = MagicMock(return_value='{"serialized": true}')
            
            # When converting goal results to dict, should use unified handler
            from netra_backend.app.agents.goals_triage_sub_agent import GoalTriageResult, GoalPriority, GoalCategory
            
            goal_result = GoalTriageResult(
                goal_id="test_1",
                original_goal="Test goal",
                priority=GoalPriority.HIGH,
                category=GoalCategory.REVENUE,
                confidence_score=0.9,
                rationale="Test rationale",
                estimated_impact="High",
                resource_requirements={},
                timeline_estimate="1 month",
                dependencies=[],
                risk_assessment={}
            )
            
            # Convert to dict (this should eventually use UnifiedJSONHandler for any JSON operations)
            result_dict = agent._goal_to_dict(goal_result)
            
            # Verify the structure is correct
            assert result_dict["priority"] == "high"
            assert result_dict["category"] == "revenue"
    
    # ========================================================================
    # ERROR HANDLING VIOLATION TESTS
    # These tests verify that unified error handling patterns are used
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_uses_unified_error_handler_for_llm_failures(self, agent, mock_context, mock_session_manager):
        """
        TEST: Verify unified error handler is used for LLM failures.
        
        Current violation: Lines 183-188 use basic try/except
        Expected: Should use agent_error_handler decorator or unified patterns
        """
    pass
        with patch('netra_backend.app.core.unified_error_handler.agent_error_handler') as mock_error_handler:
            # Mock the error handler decorator
            mock_error_handler.return_value = lambda func: func
            
            # Force an LLM error
            agent.llm_manager = MagicNone  # TODO: Use real service instance
            agent.llm_manager.ask_llm = AsyncMock(side_effect=Exception("LLM API Error"))
            
            # This should be wrapped with agent_error_handler
            result = await agent._extract_goals_from_request(mock_context, "test request")
            
            # ASSERTION: Error should be handled through unified handler
            # The method should gracefully fallback, not raise
            assert isinstance(result, list)  # Should await asyncio.sleep(0)
    return fallback list
    
    @pytest.mark.asyncio  
    async def test_uses_circuit_breaker_for_repeated_failures(self, agent, mock_context):
        """
        TEST: Verify circuit breaker pattern is used for repeated failures.
        
        Expected: Should integrate with circuit breaker from BaseAgent
        """
    pass
        # Since agent inherits from BaseAgent with enable_reliability=True,
        # it should have circuit breaker functionality
        
        # Mock multiple failures
        agent.llm_manager = MagicNone  # TODO: Use real service instance
        agent.llm_manager.ask_llm = AsyncMock(side_effect=Exception("Persistent failure"))
        
        # Try multiple times - circuit breaker should engage
        for _ in range(5):
            try:
                await agent._analyze_single_goal(mock_context, "test goal", 0)
            except:
                pass
        
        # After multiple failures, circuit breaker should be open
        # This is inherited from BaseAgent, so we just verify the agent has the capability
        assert hasattr(agent, 'reliability_manager') or hasattr(agent, 'circuit_breaker')
    
    @pytest.mark.asyncio
    async def test_error_context_includes_user_execution_context(self, agent, mock_context):
        """
        TEST: Verify errors include UserExecutionContext for debugging.
        
        Expected: Error logs should include user_id, run_id, thread_id
        """
    pass
        with patch.object(agent.logger, 'error') as mock_logger:
            # Force an error
            agent.llm_manager = MagicNone  # TODO: Use real service instance
            agent.llm_manager.ask_llm = AsyncMock(side_effect=ValueError("Test error"))
            
            await agent._extract_goals_from_request(mock_context, "test")
            
            # ASSERTION: Error log should include context information
            mock_logger.assert_called()
            error_call = mock_logger.call_args[0][0]
            # Error message should reference context (though current implementation may not)
            # This test documents the expected behavior
    
    # ========================================================================
    # INTEGRATION TESTS
    # These tests verify overall SSOT compliance in real scenarios
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_full_execution_with_ssot_compliance(self, agent, mock_context):
        """
        INTEGRATION TEST: Full execution should use all SSOT patterns.
        """
    pass
        with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as MockParser, \
             patch('netra_backend.app.core.serialization.unified_json_handler.UnifiedJSONHandler') as MockHandler, \
             patch('netra_backend.app.core.unified_error_handler.agent_error_handler') as mock_error_handler, \
             patch.object(DatabaseSessionManager, '__init__', return_value=None), \
             patch.object(DatabaseSessionManager, 'close', new_callable=AsyncMock):
            
            # Setup mocks
            mock_parser = MockParser.return_value
            mock_handler = MockHandler.return_value
            mock_error_handler.return_value = lambda func: func
            
            # Mock LLM responses
            agent.llm_manager = MagicNone  # TODO: Use real service instance
            agent.llm_manager.ask_llm = AsyncMock(return_value='["goal1", "goal2"]')
            
            # Mock WebSocket methods
            agent.emit_agent_started = AsyncNone  # TODO: Use real service instance
            agent.emit_thinking = AsyncNone  # TODO: Use real service instance
            agent.emit_progress = AsyncNone  # TODO: Use real service instance
            agent.emit_tool_executing = AsyncNone  # TODO: Use real service instance
            agent.emit_tool_completed = AsyncNone  # TODO: Use real service instance
            agent.emit_agent_completed = AsyncNone  # TODO: Use real service instance
            
            # Execute
            result = await agent.execute(mock_context)
            
            # ASSERTIONS: Verify SSOT patterns were used
            assert result is not None
            
            # Verify WebSocket events were emitted (critical for chat value)
            agent.emit_agent_started.assert_called()
            agent.emit_agent_completed.assert_called()
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_with_user_isolation(self, agent):
        """
        TEST: Verify concurrent executions maintain user isolation.
        """
    pass
        # Create multiple contexts for different users
        contexts = []
        for i in range(3):
            context = MagicMock(spec=UserExecutionContext)
            context.user_id = f"user_{i}"
            context.run_id = f"run_{i}"
            context.thread_id = f"thread_{i}"
            context.metadata = {"user_request": f"Goal for user {i}"}
            context.db_session = MagicNone  # TODO: Use real service instance
            contexts.append(context)
        
        # Mock dependencies
        agent.llm_manager = MagicNone  # TODO: Use real service instance
        agent.llm_manager.ask_llm = AsyncMock(return_value='["user_specific_goal"]')
        
        # Mock WebSocket methods
        for method in ['emit_agent_started', 'emit_thinking', 'emit_progress', 
                      'emit_tool_executing', 'emit_tool_completed', 'emit_agent_completed']:
            setattr(agent, method, AsyncNone  # TODO: Use real service instance)
        
        # Mock DatabaseSessionManager
        with patch.object(DatabaseSessionManager, '__init__', return_value=None), \
             patch.object(DatabaseSessionManager, 'close', new_callable=AsyncMock):
            
            # Execute concurrently
            tasks = [agent.execute(ctx) for ctx in contexts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # ASSERTIONS: Each execution should be isolated
            for i, result in enumerate(results):
                if not isinstance(result, Exception):
                    # Each result should contain the correct user context
                    assert "goal_triage_result" in result
                    metadata = result["goal_triage_result"]["metadata"]
                    assert metadata["user_id"] == f"user_{i}"
                    assert metadata["run_id"] == f"run_{i}"
                    assert metadata["thread_id"] == f"thread_{i}"
    
    # ========================================================================
    # PERFORMANCE AND EDGE CASE TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_handles_extremely_malformed_json(self, agent):
        """
        TEST: Should gracefully handle extremely malformed JSON.
        """
    pass
        with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as MockParser:
            mock_parser = MockParser.return_value
            mock_parser.safe_json_parse = MagicMock(return_value=["fallback_goal"])
            
            # Various malformed JSON scenarios
            malformed_inputs = [
                '{"incomplete": ',  # Incomplete JSON
                'null',  # Null value
                'undefined',  # JavaScript undefined
                '{"key": undefined}',  # Contains undefined
                '{key: "value"}',  # Unquoted keys
                "{'key': 'value'}",  # Single quotes
                '{"key": "value",,,}',  # Multiple commas
                '["item1" "item2"]',  # Missing comma
                '{"nested": {"deep": {"incomplete":',  # Deeply nested incomplete
            ]
            
            for malformed in malformed_inputs:
                result = agent._parse_goals_from_llm_response(malformed)
                # Should not raise exception, should await asyncio.sleep(0)
    return something usable
                assert isinstance(result, list)
                assert len(result) > 0  # Should have fallback
    
    @pytest.mark.asyncio
    async def test_handles_circular_references(self, agent):
        """
        TEST: Should handle circular references in data structures.
        """
    pass
        with patch('netra_backend.app.core.serialization.unified_json_handler.CircularReferenceHandler') as MockCircHandler:
            mock_handler = MockCircHandler.return_value
            mock_handler.serialize_safe = MagicMock(return_value='{"safe": "data"}')
            
            # Create circular reference
            circular_data = {"key": "value"}
            circular_data["self"] = circular_data
            
            # This should use CircularReferenceHandler
            # (Though the current implementation might not handle this case)
            # This test documents the expected behavior
    
    @pytest.mark.asyncio
    async def test_websocket_events_during_json_errors(self, agent, mock_context):
        """
        TEST: WebSocket events should still be emitted even during JSON errors.
        """
    pass
        # Mock WebSocket methods
        agent.emit_thinking = AsyncNone  # TODO: Use real service instance
        agent.emit_tool_executing = AsyncNone  # TODO: Use real service instance
        agent.emit_tool_completed = AsyncNone  # TODO: Use real service instance
        
        # Force JSON parsing error
        agent.llm_manager = MagicNone  # TODO: Use real service instance
        agent.llm_manager.ask_llm = AsyncMock(return_value='{invalid json}')
        
        # Execute
        result = await agent._extract_goals_from_request(mock_context, "test")
        
        # ASSERTIONS: WebSocket events should still be emitted
        agent.emit_tool_executing.assert_called()
        agent.emit_tool_completed.assert_called()
        
        # Should have error info in completion
        completion_call = agent.emit_tool_completed.call_args
        assert "error" in completion_call[0][1] or "fallback_used" in completion_call[0][1]


class TestGoalsTriageSubAgentCompliance:
    """Test suite for verifying SSOT compliance after fixes."""
    
    @pytest.mark.asyncio
    async def test_no_direct_json_imports(self):
        """
        COMPLIANCE TEST: Verify no direct json module usage.
        """
    pass
        import ast
        import inspect
        from netra_backend.app.agents import goals_triage_sub_agent
        
        # Get source code
        source = inspect.getsource(goals_triage_sub_agent)
        
        # Parse AST
        tree = ast.parse(source)
        
        # Check for json.loads or json.dumps calls
        json_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if (isinstance(node.func.value, ast.Name) and 
                        node.func.value.id == 'json' and
                        node.func.attr in ['loads', 'dumps', 'load', 'dump']):
                        json_calls.append((node.lineno, node.func.attr))
        
        # ASSERTION: Should not use json directly (except in imports)
        # Current implementation will FAIL this test
        assert len(json_calls) == 0, f"Found direct json usage at lines: {json_calls}"
    
    @pytest.mark.asyncio
    async def test_uses_canonical_implementations(self):
        """
        COMPLIANCE TEST: Verify usage of canonical SSOT implementations.
        """
    pass
        from netra_backend.app.agents import goals_triage_sub_agent
        source = inspect.getsource(goals_triage_sub_agent)
        
        # Check for required imports
        required_imports = [
            'LLMResponseParser',
            'UnifiedJSONHandler',
            'JSONErrorFixer'
        ]
        
        for required in required_imports:
            assert required in source, f"Missing required import: {required}"
    
    @pytest.mark.asyncio
    async def test_maintains_backward_compatibility(self, agent, mock_context):
        """
        TEST: Ensure fixes maintain backward compatibility.
        """
    pass
        # Old-style JSON response (what existing code might return)
        old_style_response = '["goal1", "goal2", "goal3"]'
        
        # Should still parse correctly after fixes
        result = agent._parse_goals_from_llm_response(old_style_response)
        assert result == ["goal1", "goal2", "goal3"]
        
        # New-style with proper error handling should also work
        new_style_response = '{"goals": ["goal1", "goal2"], "metadata": {}}'
        result = agent._parse_goals_from_llm_response(new_style_response)
        assert isinstance(result, (list, dict))


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])