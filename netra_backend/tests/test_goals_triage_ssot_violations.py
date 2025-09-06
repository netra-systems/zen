# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive SSOT Violation Test Suite for GoalsTriageSubAgent

# REMOVED_SYNTAX_ERROR: This test suite is designed to FAIL with the current implementation
# REMOVED_SYNTAX_ERROR: and will PASS only when proper SSOT patterns are implemented.

# REMOVED_SYNTAX_ERROR: SSOT Violations being tested:
    # REMOVED_SYNTAX_ERROR: 1. JSON Handling - Must use LLMResponseParser from unified_json_handler.py
    # REMOVED_SYNTAX_ERROR: 2. Error Handling - Must use unified error handler patterns

    # REMOVED_SYNTAX_ERROR: Business Value: Ensures consistent patterns across all agents for maintainability
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.database.session_manager import DatabaseSessionManager


# REMOVED_SYNTAX_ERROR: class TestGoalsTriageSubAgentSSOTViolations:
    # REMOVED_SYNTAX_ERROR: """Test suite for SSOT violations in GoalsTriageSubAgent."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock UserExecutionContext for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: context = MagicMock(spec=UserExecutionContext)
    # REMOVED_SYNTAX_ERROR: context.user_id = "test_user_123"
    # REMOVED_SYNTAX_ERROR: context.run_id = "test_run_456"
    # REMOVED_SYNTAX_ERROR: context.thread_id = "test_thread_789"
    # REMOVED_SYNTAX_ERROR: context.metadata = {"user_request": "Optimize costs and improve user experience"}
    # REMOVED_SYNTAX_ERROR: context.db_session = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return context

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def agent(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create GoalsTriageSubAgent instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return GoalsTriageSubAgent()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_session_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock DatabaseSessionManager."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: session_manager = MagicMock(spec=DatabaseSessionManager)
    # REMOVED_SYNTAX_ERROR: session_manager.close = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return session_manager

    # ========================================================================
    # JSON HANDLING VIOLATION TESTS
    # These tests verify that unified_json_handler is used instead of json.loads
    # ========================================================================

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_json_parsing_uses_llm_response_parser(self, agent, mock_context):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: CRITICAL TEST: Verify that LLMResponseParser is used for JSON parsing.

        # REMOVED_SYNTAX_ERROR: Current violation: Lines 338-344 use json.loads() directly
        # REMOVED_SYNTAX_ERROR: Expected: Should use LLMResponseParser.safe_json_parse()
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # Patch the LLMResponseParser to track its usage
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as MockParser:
            # REMOVED_SYNTAX_ERROR: mock_parser = MockParser.return_value
            # REMOVED_SYNTAX_ERROR: mock_parser.safe_json_parse = MagicMock(return_value=["goal1", "goal2"])

            # Create malformed JSON that json.loads would fail on
            # REMOVED_SYNTAX_ERROR: malformed_json = '["goal1", "goal2",]'  # Trailing comma - invalid JSON

            # This should use LLMResponseParser, not json.loads
            # REMOVED_SYNTAX_ERROR: result = agent._parse_goals_from_llm_response(malformed_json)

            # ASSERTION: LLMResponseParser.safe_json_parse should be called
            # REMOVED_SYNTAX_ERROR: mock_parser.safe_json_parse.assert_called_once_with(malformed_json, fallback=None)
            # REMOVED_SYNTAX_ERROR: assert result == ["goal1", "goal2"]

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_goal_analysis_parsing_uses_llm_response_parser(self, agent, mock_context):
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: CRITICAL TEST: Verify goal analysis uses LLMResponseParser.

                # REMOVED_SYNTAX_ERROR: Current violation: Line 365 uses json.loads() directly
                # REMOVED_SYNTAX_ERROR: Expected: Should use LLMResponseParser.ensure_agent_response_is_json()
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as MockParser:
                    # REMOVED_SYNTAX_ERROR: mock_parser = MockParser.return_value
                    # REMOVED_SYNTAX_ERROR: expected_data = { )
                    # REMOVED_SYNTAX_ERROR: "priority": "high",
                    # REMOVED_SYNTAX_ERROR: "category": "revenue",
                    # REMOVED_SYNTAX_ERROR: "confidence_score": 0.8
                    
                    # REMOVED_SYNTAX_ERROR: mock_parser.ensure_agent_response_is_json = MagicMock(return_value=expected_data)

                    # Create response with JSON fragment (should be handled by LLMResponseParser)
                    # REMOVED_SYNTAX_ERROR: json_fragment = '"priority": "high", "category": "revenue"'

                    # REMOVED_SYNTAX_ERROR: result = agent._parse_goal_analysis_response(json_fragment)

                    # ASSERTION: Should use LLMResponseParser
                    # REMOVED_SYNTAX_ERROR: mock_parser.ensure_agent_response_is_json.assert_called_once_with(json_fragment)
                    # REMOVED_SYNTAX_ERROR: assert result == expected_data

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_handles_malformed_json_with_error_fixer(self, agent, mock_context):
                        # REMOVED_SYNTAX_ERROR: '''
                        # REMOVED_SYNTAX_ERROR: TEST: Verify JSONErrorFixer is used for malformed JSON recovery.

                        # REMOVED_SYNTAX_ERROR: Expected: Should use JSONErrorFixer.fix_common_json_errors()
                        # REMOVED_SYNTAX_ERROR: '''
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.serialization.unified_json_handler.JSONErrorFixer') as MockFixer:
                            # REMOVED_SYNTAX_ERROR: mock_fixer = MockFixer.return_value
                            # REMOVED_SYNTAX_ERROR: mock_fixer.fix_common_json_errors = MagicMock(return_value='["fixed_goal"]')

                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as MockParser:
                                # REMOVED_SYNTAX_ERROR: mock_parser = MockParser.return_value
                                # REMOVED_SYNTAX_ERROR: mock_parser.safe_json_parse = MagicMock(side_effect=[ ))
                                # REMOVED_SYNTAX_ERROR: None,  # First attempt fails
                                # REMOVED_SYNTAX_ERROR: ["fixed_goal"]  # After fixing, succeeds
                                

                                # Malformed JSON with multiple issues
                                # REMOVED_SYNTAX_ERROR: malformed = '["goal1", "goal2",,]'  # Double comma and trailing comma

                                # REMOVED_SYNTAX_ERROR: result = agent._parse_goals_from_llm_response(malformed)

                                # ASSERTION: JSONErrorFixer should be invoked
                                # REMOVED_SYNTAX_ERROR: mock_fixer.fix_common_json_errors.assert_called()

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_json_serialization_uses_unified_handler(self, agent, mock_context):
                                    # REMOVED_SYNTAX_ERROR: '''
                                    # REMOVED_SYNTAX_ERROR: TEST: Verify UnifiedJSONHandler is used for JSON serialization.

                                    # REMOVED_SYNTAX_ERROR: Expected: Should use UnifiedJSONHandler.dumps() for serialization
                                    # REMOVED_SYNTAX_ERROR: '''
                                    # REMOVED_SYNTAX_ERROR: pass
                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.serialization.unified_json_handler.UnifiedJSONHandler') as MockHandler:
                                        # REMOVED_SYNTAX_ERROR: mock_handler = MockHandler.return_value
                                        # REMOVED_SYNTAX_ERROR: mock_handler.dumps = MagicMock(return_value='{"serialized": true}')

                                        # When converting goal results to dict, should use unified handler
                                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.goals_triage_sub_agent import GoalTriageResult, GoalPriority, GoalCategory

                                        # REMOVED_SYNTAX_ERROR: goal_result = GoalTriageResult( )
                                        # REMOVED_SYNTAX_ERROR: goal_id="test_1",
                                        # REMOVED_SYNTAX_ERROR: original_goal="Test goal",
                                        # REMOVED_SYNTAX_ERROR: priority=GoalPriority.HIGH,
                                        # REMOVED_SYNTAX_ERROR: category=GoalCategory.REVENUE,
                                        # REMOVED_SYNTAX_ERROR: confidence_score=0.9,
                                        # REMOVED_SYNTAX_ERROR: rationale="Test rationale",
                                        # REMOVED_SYNTAX_ERROR: estimated_impact="High",
                                        # REMOVED_SYNTAX_ERROR: resource_requirements={},
                                        # REMOVED_SYNTAX_ERROR: timeline_estimate="1 month",
                                        # REMOVED_SYNTAX_ERROR: dependencies=[],
                                        # REMOVED_SYNTAX_ERROR: risk_assessment={}
                                        

                                        # Convert to dict (this should eventually use UnifiedJSONHandler for any JSON operations)
                                        # REMOVED_SYNTAX_ERROR: result_dict = agent._goal_to_dict(goal_result)

                                        # Verify the structure is correct
                                        # REMOVED_SYNTAX_ERROR: assert result_dict["priority"] == "high"
                                        # REMOVED_SYNTAX_ERROR: assert result_dict["category"] == "revenue"

                                        # ========================================================================
                                        # ERROR HANDLING VIOLATION TESTS
                                        # These tests verify that unified error handling patterns are used
                                        # ========================================================================

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_uses_unified_error_handler_for_llm_failures(self, agent, mock_context, mock_session_manager):
                                            # REMOVED_SYNTAX_ERROR: '''
                                            # REMOVED_SYNTAX_ERROR: TEST: Verify unified error handler is used for LLM failures.

                                            # REMOVED_SYNTAX_ERROR: Current violation: Lines 183-188 use basic try/except
                                            # REMOVED_SYNTAX_ERROR: Expected: Should use agent_error_handler decorator or unified patterns
                                            # REMOVED_SYNTAX_ERROR: '''
                                            # REMOVED_SYNTAX_ERROR: pass
                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.unified_error_handler.agent_error_handler') as mock_error_handler:
                                                # Mock the error handler decorator
                                                # REMOVED_SYNTAX_ERROR: mock_error_handler.return_value = lambda x: None func

                                                # Force an LLM error
                                                # REMOVED_SYNTAX_ERROR: agent.llm_manager = MagicNone  # TODO: Use real service instance
                                                # REMOVED_SYNTAX_ERROR: agent.llm_manager.ask_llm = AsyncMock(side_effect=Exception("LLM API Error"))

                                                # This should be wrapped with agent_error_handler
                                                # REMOVED_SYNTAX_ERROR: result = await agent._extract_goals_from_request(mock_context, "test request")

                                                # ASSERTION: Error should be handled through unified handler
                                                # The method should gracefully fallback, not raise
                                                # REMOVED_SYNTAX_ERROR: assert isinstance(result, list)  # Should await asyncio.sleep(0)
                                                # REMOVED_SYNTAX_ERROR: return fallback list

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_uses_circuit_breaker_for_repeated_failures(self, agent, mock_context):
                                                    # REMOVED_SYNTAX_ERROR: '''
                                                    # REMOVED_SYNTAX_ERROR: TEST: Verify circuit breaker pattern is used for repeated failures.

                                                    # REMOVED_SYNTAX_ERROR: Expected: Should integrate with circuit breaker from BaseAgent
                                                    # REMOVED_SYNTAX_ERROR: '''
                                                    # REMOVED_SYNTAX_ERROR: pass
                                                    # Since agent inherits from BaseAgent with enable_reliability=True,
                                                    # it should have circuit breaker functionality

                                                    # Mock multiple failures
                                                    # REMOVED_SYNTAX_ERROR: agent.llm_manager = MagicNone  # TODO: Use real service instance
                                                    # REMOVED_SYNTAX_ERROR: agent.llm_manager.ask_llm = AsyncMock(side_effect=Exception("Persistent failure"))

                                                    # Try multiple times - circuit breaker should engage
                                                    # REMOVED_SYNTAX_ERROR: for _ in range(5):
                                                        # REMOVED_SYNTAX_ERROR: try:
                                                            # REMOVED_SYNTAX_ERROR: await agent._analyze_single_goal(mock_context, "test goal", 0)
                                                            # REMOVED_SYNTAX_ERROR: except:
                                                                # REMOVED_SYNTAX_ERROR: pass

                                                                # After multiple failures, circuit breaker should be open
                                                                # This is inherited from BaseAgent, so we just verify the agent has the capability
                                                                # REMOVED_SYNTAX_ERROR: assert hasattr(agent, 'reliability_manager') or hasattr(agent, 'circuit_breaker')

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_error_context_includes_user_execution_context(self, agent, mock_context):
                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                    # REMOVED_SYNTAX_ERROR: TEST: Verify errors include UserExecutionContext for debugging.

                                                                    # REMOVED_SYNTAX_ERROR: Expected: Error logs should include user_id, run_id, thread_id
                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                    # REMOVED_SYNTAX_ERROR: with patch.object(agent.logger, 'error') as mock_logger:
                                                                        # Force an error
                                                                        # REMOVED_SYNTAX_ERROR: agent.llm_manager = MagicNone  # TODO: Use real service instance
                                                                        # REMOVED_SYNTAX_ERROR: agent.llm_manager.ask_llm = AsyncMock(side_effect=ValueError("Test error"))

                                                                        # REMOVED_SYNTAX_ERROR: await agent._extract_goals_from_request(mock_context, "test")

                                                                        # ASSERTION: Error log should include context information
                                                                        # REMOVED_SYNTAX_ERROR: mock_logger.assert_called()
                                                                        # REMOVED_SYNTAX_ERROR: error_call = mock_logger.call_args[0][0]
                                                                        # Error message should reference context (though current implementation may not)
                                                                        # This test documents the expected behavior

                                                                        # ========================================================================
                                                                        # INTEGRATION TESTS
                                                                        # These tests verify overall SSOT compliance in real scenarios
                                                                        # ========================================================================

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_full_execution_with_ssot_compliance(self, agent, mock_context):
                                                                            # REMOVED_SYNTAX_ERROR: '''
                                                                            # REMOVED_SYNTAX_ERROR: INTEGRATION TEST: Full execution should use all SSOT patterns.
                                                                            # REMOVED_SYNTAX_ERROR: '''
                                                                            # REMOVED_SYNTAX_ERROR: pass
                                                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as MockParser, \
                                                                            # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.core.serialization.unified_json_handler.UnifiedJSONHandler') as MockHandler, \
                                                                            # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.core.unified_error_handler.agent_error_handler') as mock_error_handler, \
                                                                            # REMOVED_SYNTAX_ERROR: patch.object(DatabaseSessionManager, '__init__', return_value=None), \
                                                                            # REMOVED_SYNTAX_ERROR: patch.object(DatabaseSessionManager, 'close', new_callable=AsyncMock):

                                                                                # Setup mocks
                                                                                # REMOVED_SYNTAX_ERROR: mock_parser = MockParser.return_value
                                                                                # REMOVED_SYNTAX_ERROR: mock_handler = MockHandler.return_value
                                                                                # REMOVED_SYNTAX_ERROR: mock_error_handler.return_value = lambda x: None func

                                                                                # Mock LLM responses
                                                                                # REMOVED_SYNTAX_ERROR: agent.llm_manager = MagicNone  # TODO: Use real service instance
                                                                                # REMOVED_SYNTAX_ERROR: agent.llm_manager.ask_llm = AsyncMock(return_value='["goal1", "goal2"]')

                                                                                # Mock WebSocket methods
                                                                                # REMOVED_SYNTAX_ERROR: agent.emit_agent_started = AsyncNone  # TODO: Use real service instance
                                                                                # REMOVED_SYNTAX_ERROR: agent.emit_thinking = AsyncNone  # TODO: Use real service instance
                                                                                # REMOVED_SYNTAX_ERROR: agent.emit_progress = AsyncNone  # TODO: Use real service instance
                                                                                # REMOVED_SYNTAX_ERROR: agent.emit_tool_executing = AsyncNone  # TODO: Use real service instance
                                                                                # REMOVED_SYNTAX_ERROR: agent.emit_tool_completed = AsyncNone  # TODO: Use real service instance
                                                                                # REMOVED_SYNTAX_ERROR: agent.emit_agent_completed = AsyncNone  # TODO: Use real service instance

                                                                                # Execute
                                                                                # REMOVED_SYNTAX_ERROR: result = await agent.execute(mock_context)

                                                                                # ASSERTIONS: Verify SSOT patterns were used
                                                                                # REMOVED_SYNTAX_ERROR: assert result is not None

                                                                                # Verify WebSocket events were emitted (critical for chat value)
                                                                                # REMOVED_SYNTAX_ERROR: agent.emit_agent_started.assert_called()
                                                                                # REMOVED_SYNTAX_ERROR: agent.emit_agent_completed.assert_called()

                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                # Removed problematic line: async def test_concurrent_execution_with_user_isolation(self, agent):
                                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                                    # REMOVED_SYNTAX_ERROR: TEST: Verify concurrent executions maintain user isolation.
                                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                                    # Create multiple contexts for different users
                                                                                    # REMOVED_SYNTAX_ERROR: contexts = []
                                                                                    # REMOVED_SYNTAX_ERROR: for i in range(3):
                                                                                        # REMOVED_SYNTAX_ERROR: context = MagicMock(spec=UserExecutionContext)
                                                                                        # REMOVED_SYNTAX_ERROR: context.user_id = "formatted_string"
                                                                                        # REMOVED_SYNTAX_ERROR: context.run_id = "formatted_string"
                                                                                        # REMOVED_SYNTAX_ERROR: context.thread_id = "formatted_string"
                                                                                        # REMOVED_SYNTAX_ERROR: context.metadata = {"user_request": "formatted_string"}
                                                                                        # REMOVED_SYNTAX_ERROR: context.db_session = MagicNone  # TODO: Use real service instance
                                                                                        # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                                                                        # Mock dependencies
                                                                                        # REMOVED_SYNTAX_ERROR: agent.llm_manager = MagicNone  # TODO: Use real service instance
                                                                                        # REMOVED_SYNTAX_ERROR: agent.llm_manager.ask_llm = AsyncMock(return_value='["user_specific_goal"]')

                                                                                        # Mock WebSocket methods
                                                                                        # REMOVED_SYNTAX_ERROR: for method in ['emit_agent_started', 'emit_thinking', 'emit_progress',
                                                                                        # REMOVED_SYNTAX_ERROR: 'emit_tool_executing', 'emit_tool_completed', 'emit_agent_completed']:
                                                                                            # REMOVED_SYNTAX_ERROR: setattr(agent, method, AsyncNone  # TODO: Use real service instance)

                                                                                            # Mock DatabaseSessionManager
                                                                                            # REMOVED_SYNTAX_ERROR: with patch.object(DatabaseSessionManager, '__init__', return_value=None), \
                                                                                            # REMOVED_SYNTAX_ERROR: patch.object(DatabaseSessionManager, 'close', new_callable=AsyncMock):

                                                                                                # Execute concurrently
                                                                                                # REMOVED_SYNTAX_ERROR: tasks = [agent.execute(ctx) for ctx in contexts]
                                                                                                # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                                                                                                # ASSERTIONS: Each execution should be isolated
                                                                                                # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):
                                                                                                    # REMOVED_SYNTAX_ERROR: if not isinstance(result, Exception):
                                                                                                        # Each result should contain the correct user context
                                                                                                        # REMOVED_SYNTAX_ERROR: assert "goal_triage_result" in result
                                                                                                        # REMOVED_SYNTAX_ERROR: metadata = result["goal_triage_result"]["metadata"]
                                                                                                        # REMOVED_SYNTAX_ERROR: assert metadata["user_id"] == "formatted_string"
                                                                                                        # REMOVED_SYNTAX_ERROR: assert metadata["run_id"] == "formatted_string"
                                                                                                        # REMOVED_SYNTAX_ERROR: assert metadata["thread_id"] == "formatted_string"

                                                                                                        # ========================================================================
                                                                                                        # PERFORMANCE AND EDGE CASE TESTS
                                                                                                        # ========================================================================

                                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                                        # Removed problematic line: async def test_handles_extremely_malformed_json(self, agent):
                                                                                                            # REMOVED_SYNTAX_ERROR: '''
                                                                                                            # REMOVED_SYNTAX_ERROR: TEST: Should gracefully handle extremely malformed JSON.
                                                                                                            # REMOVED_SYNTAX_ERROR: '''
                                                                                                            # REMOVED_SYNTAX_ERROR: pass
                                                                                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as MockParser:
                                                                                                                # REMOVED_SYNTAX_ERROR: mock_parser = MockParser.return_value
                                                                                                                # REMOVED_SYNTAX_ERROR: mock_parser.safe_json_parse = MagicMock(return_value=["fallback_goal"])

                                                                                                                # Various malformed JSON scenarios
                                                                                                                # REMOVED_SYNTAX_ERROR: malformed_inputs = [ )
                                                                                                                # REMOVED_SYNTAX_ERROR: '{"incomplete": ',  # Incomplete JSON )
                                                                                                                # REMOVED_SYNTAX_ERROR: 'null',  # Null value
                                                                                                                # REMOVED_SYNTAX_ERROR: 'undefined',  # JavaScript undefined
                                                                                                                # REMOVED_SYNTAX_ERROR: '{"key": undefined}',  # Contains undefined
                                                                                                                # REMOVED_SYNTAX_ERROR: '{key: "value"}',  # Unquoted keys
                                                                                                                # REMOVED_SYNTAX_ERROR: "{'key': 'value'}",  # Single quotes
                                                                                                                # REMOVED_SYNTAX_ERROR: '{"key": "value",,,}',  # Multiple commas
                                                                                                                # REMOVED_SYNTAX_ERROR: '["item1" "item2"]',  # Missing comma
                                                                                                                # REMOVED_SYNTAX_ERROR: '{"nested": {"deep": {"incomplete":',  # Deeply nested incomplete )))
                                                                                                                

                                                                                                                # REMOVED_SYNTAX_ERROR: for malformed in malformed_inputs:
                                                                                                                    # REMOVED_SYNTAX_ERROR: result = agent._parse_goals_from_llm_response(malformed)
                                                                                                                    # Should not raise exception, should await asyncio.sleep(0)
                                                                                                                    # REMOVED_SYNTAX_ERROR: return something usable
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert isinstance(result, list)
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert len(result) > 0  # Should have fallback

                                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                                    # Removed problematic line: async def test_handles_circular_references(self, agent):
                                                                                                                        # REMOVED_SYNTAX_ERROR: '''
                                                                                                                        # REMOVED_SYNTAX_ERROR: TEST: Should handle circular references in data structures.
                                                                                                                        # REMOVED_SYNTAX_ERROR: '''
                                                                                                                        # REMOVED_SYNTAX_ERROR: pass
                                                                                                                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.serialization.unified_json_handler.CircularReferenceHandler') as MockCircHandler:
                                                                                                                            # REMOVED_SYNTAX_ERROR: mock_handler = MockCircHandler.return_value
                                                                                                                            # REMOVED_SYNTAX_ERROR: mock_handler.serialize_safe = MagicMock(return_value='{"safe": "data"}')

                                                                                                                            # Create circular reference
                                                                                                                            # REMOVED_SYNTAX_ERROR: circular_data = {"key": "value"}
                                                                                                                            # REMOVED_SYNTAX_ERROR: circular_data["sel"formatted_string"test")

                                                                                                                                # ASSERTIONS: WebSocket events should still be emitted
                                                                                                                                # REMOVED_SYNTAX_ERROR: agent.emit_tool_executing.assert_called()
                                                                                                                                # REMOVED_SYNTAX_ERROR: agent.emit_tool_completed.assert_called()

                                                                                                                                # Should have error info in completion
                                                                                                                                # REMOVED_SYNTAX_ERROR: completion_call = agent.emit_tool_completed.call_args
                                                                                                                                # REMOVED_SYNTAX_ERROR: assert "error" in completion_call[0][1] or "fallback_used" in completion_call[0][1]


# REMOVED_SYNTAX_ERROR: class TestGoalsTriageSubAgentCompliance:
    # REMOVED_SYNTAX_ERROR: """Test suite for verifying SSOT compliance after fixes."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_no_direct_json_imports(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: COMPLIANCE TEST: Verify no direct json module usage.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: import ast
        # REMOVED_SYNTAX_ERROR: import inspect
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents import goals_triage_sub_agent

        # Get source code
        # REMOVED_SYNTAX_ERROR: source = inspect.getsource(goals_triage_sub_agent)

        # Parse AST
        # REMOVED_SYNTAX_ERROR: tree = ast.parse(source)

        # Check for json.loads or json.dumps calls
        # REMOVED_SYNTAX_ERROR: json_calls = []
        # REMOVED_SYNTAX_ERROR: for node in ast.walk(tree):
            # REMOVED_SYNTAX_ERROR: if isinstance(node, ast.Call):
                # REMOVED_SYNTAX_ERROR: if isinstance(node.func, ast.Attribute):
                    # REMOVED_SYNTAX_ERROR: if (isinstance(node.func.value, ast.Name) and )
                    # REMOVED_SYNTAX_ERROR: node.func.value.id == 'json' and
                    # REMOVED_SYNTAX_ERROR: node.func.attr in ['loads', 'dumps', 'load', 'dump']):
                        # REMOVED_SYNTAX_ERROR: json_calls.append((node.lineno, node.func.attr))

                        # ASSERTION: Should not use json directly (except in imports)
                        # Current implementation will FAIL this test
                        # REMOVED_SYNTAX_ERROR: assert len(json_calls) == 0, "formatted_string"

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_uses_canonical_implementations(self):
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: COMPLIANCE TEST: Verify usage of canonical SSOT implementations.
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: pass
                            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents import goals_triage_sub_agent
                            # REMOVED_SYNTAX_ERROR: source = inspect.getsource(goals_triage_sub_agent)

                            # Check for required imports
                            # REMOVED_SYNTAX_ERROR: required_imports = [ )
                            # REMOVED_SYNTAX_ERROR: 'LLMResponseParser',
                            # REMOVED_SYNTAX_ERROR: 'UnifiedJSONHandler',
                            # REMOVED_SYNTAX_ERROR: 'JSONErrorFixer'
                            

                            # REMOVED_SYNTAX_ERROR: for required in required_imports:
                                # REMOVED_SYNTAX_ERROR: assert required in source, "formatted_string"

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_maintains_backward_compatibility(self, agent, mock_context):
                                    # REMOVED_SYNTAX_ERROR: '''
                                    # REMOVED_SYNTAX_ERROR: TEST: Ensure fixes maintain backward compatibility.
                                    # REMOVED_SYNTAX_ERROR: '''
                                    # REMOVED_SYNTAX_ERROR: pass
                                    # Old-style JSON response (what existing code might return)
                                    # REMOVED_SYNTAX_ERROR: old_style_response = '["goal1", "goal2", "goal3"]'

                                    # Should still parse correctly after fixes
                                    # REMOVED_SYNTAX_ERROR: result = agent._parse_goals_from_llm_response(old_style_response)
                                    # REMOVED_SYNTAX_ERROR: assert result == ["goal1", "goal2", "goal3"]

                                    # New-style with proper error handling should also work
                                    # REMOVED_SYNTAX_ERROR: new_style_response = '{"goals": ["goal1", "goal2"], "metadata": {}}'
                                    # REMOVED_SYNTAX_ERROR: result = agent._parse_goals_from_llm_response(new_style_response)
                                    # REMOVED_SYNTAX_ERROR: assert isinstance(result, (list, dict))


                                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                        # Run tests with verbose output
                                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "-s", "--tb=short"])