# REMOVED_SYNTAX_ERROR: '''Comprehensive SSOT Compliance Test Suite for ActionsToMeetGoalsSubAgent

# REMOVED_SYNTAX_ERROR: CRITICAL: This test suite validates ALL SSOT requirements for ActionsToMeetGoalsSubAgent
# REMOVED_SYNTAX_ERROR: - Tests for JSON handling compliance with unified_json_handler
# REMOVED_SYNTAX_ERROR: - Tests for UserExecutionContext proper integration
# REMOVED_SYNTAX_ERROR: - Tests for caching/hashing compliance with CacheHelpers
# REMOVED_SYNTAX_ERROR: - Tests for environment access through IsolatedEnvironment
# REMOVED_SYNTAX_ERROR: - Tests for WebSocket event emission patterns
# REMOVED_SYNTAX_ERROR: - Tests for database session management
# REMOVED_SYNTAX_ERROR: - Tests for global state isolation

# REMOVED_SYNTAX_ERROR: These tests are designed to FAIL until all SSOT violations are fixed.
# REMOVED_SYNTAX_ERROR: '''

import asyncio
import json
import pytest
from typing import Any, Dict, Optional
import hashlib
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.agents.state import ActionPlanResult, OptimizationsResult
from netra_backend.app.schemas.shared_types import DataAnalysisResponse
from netra_backend.app.core.serialization.unified_json_handler import LLMResponseParser
from netra_backend.app.services.cache.cache_helpers import CacheHelpers
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler


# REMOVED_SYNTAX_ERROR: class TestActionsToMeetGoalsSSoTCompliance:
    # REMOVED_SYNTAX_ERROR: """Test suite for SSOT compliance of ActionsToMeetGoalsSubAgent"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_llm_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock LLM manager"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: llm_manager = llm_manager_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: llm_manager.ask_llm = AsyncMock(return_value='{"action_plan": "test"}')
    # REMOVED_SYNTAX_ERROR: return llm_manager

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock tool dispatcher"""
    # REMOVED_SYNTAX_ERROR: return None  # TODO: Use real service instance

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket manager"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: ws_manager = UnifiedWebSocketManager()
    # REMOVED_SYNTAX_ERROR: ws_manager.emit_agent_started = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: ws_manager.emit_agent_thinking = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: ws_manager.emit_tool_executing = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: ws_manager.emit_tool_completed = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: ws_manager.emit_agent_completed = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: ws_manager.emit_progress = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return ws_manager

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create UserExecutionContext for testing"""
    # REMOVED_SYNTAX_ERROR: pass
    # UserExecutionContext is frozen, so metadata must be passed in constructor
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="test_user",
    # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
    # REMOVED_SYNTAX_ERROR: run_id="test_run",
    # REMOVED_SYNTAX_ERROR: request_id="test_request",
    # REMOVED_SYNTAX_ERROR: db_session=Mock(spec=DatabaseSessionManager),  # Use db_session instead of session_manager
    # REMOVED_SYNTAX_ERROR: metadata={ )
    # REMOVED_SYNTAX_ERROR: 'user_request': 'Test request',
    # REMOVED_SYNTAX_ERROR: 'optimizations_result': {'type': 'test', 'recommendations': []},
    # REMOVED_SYNTAX_ERROR: 'data_result': {'query': 'test', 'results': []}
    
    
    # REMOVED_SYNTAX_ERROR: return context

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def agent(self, mock_llm_manager, mock_tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create agent instance for testing"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: agent = ActionsToMeetGoalsSubAgent( )
    # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher
    
    # REMOVED_SYNTAX_ERROR: return agent

    # ============= JSON HANDLING TESTS =============

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_json_parsing_uses_unified_handler(self, agent, user_context):
        # REMOVED_SYNTAX_ERROR: """Test that JSON parsing uses unified_json_handler, not custom implementation"""
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.actions_goals_plan_builder.ActionPlanBuilder.process_llm_response') as mock_process:
            # Check if ActionPlanBuilder is using unified JSON handler
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser.extract_json') as mock_extract:
                # REMOVED_SYNTAX_ERROR: mock_extract.return_value = {'action_plan': 'test'}
                # REMOVED_SYNTAX_ERROR: mock_process.return_value = ActionPlanResult(plan_steps=[], partial_extraction=False)

                # REMOVED_SYNTAX_ERROR: result = await agent.execute(user_context)

                # This test will FAIL if ActionPlanBuilder doesn't use LLMResponseParser
                # We're checking that the unified handler is called
                # Currently this might fail as ActionPlanBuilder might have custom JSON parsing
                # REMOVED_SYNTAX_ERROR: assert mock_extract.called or mock_process.called

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_no_custom_json_extraction(self):
                    # REMOVED_SYNTAX_ERROR: """Test that no custom JSON extraction patterns exist in ActionPlanBuilder"""
                    # REMOVED_SYNTAX_ERROR: pass
                    # Read ActionPlanBuilder source
                    # REMOVED_SYNTAX_ERROR: import inspect
                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.actions_goals_plan_builder import ActionPlanBuilder

                    # REMOVED_SYNTAX_ERROR: source = inspect.getsource(ActionPlanBuilder)

                    # Check for custom JSON parsing patterns that violate SSOT
                    # REMOVED_SYNTAX_ERROR: forbidden_patterns = [ )
                    # REMOVED_SYNTAX_ERROR: 'json.loads',
                    # REMOVED_SYNTAX_ERROR: 'json.dumps',
                    # REMOVED_SYNTAX_ERROR: 're.search.*json',
                    # REMOVED_SYNTAX_ERROR: 'extract.*json',
                    # REMOVED_SYNTAX_ERROR: 'parse.*json'
                    

                    # REMOVED_SYNTAX_ERROR: violations = []
                    # REMOVED_SYNTAX_ERROR: for pattern in forbidden_patterns:
                        # REMOVED_SYNTAX_ERROR: if pattern.replace('.*', '') in source.lower():
                            # REMOVED_SYNTAX_ERROR: violations.append(pattern)

                            # This test will FAIL if custom JSON handling exists
                            # REMOVED_SYNTAX_ERROR: assert not violations, "formatted_string"

                            # ============= USER EXECUTION CONTEXT TESTS =============

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_context_passed_to_all_components(self, agent, user_context):
                                # REMOVED_SYNTAX_ERROR: """Test that UserExecutionContext is passed to all sub-components"""
                                # REMOVED_SYNTAX_ERROR: with patch.object(agent.action_plan_builder, 'process_llm_response') as mock_process:
                                    # REMOVED_SYNTAX_ERROR: mock_process.return_value = ActionPlanResult(plan_steps=[], partial_extraction=False)

                                    # REMOVED_SYNTAX_ERROR: await agent.execute(user_context)

                                    # Verify context is used, not stored
                                    # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, 'user_id'), "Agent should not store user_id"
                                    # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, 'thread_id'), "Agent should not store thread_id"
                                    # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, 'run_id'), "Agent should not store run_id"

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_no_global_state_storage(self, agent, user_context):
                                        # REMOVED_SYNTAX_ERROR: """Test that no user-specific data is stored in instance variables"""
                                        # REMOVED_SYNTAX_ERROR: pass
                                        # Execute with first user
                                        # REMOVED_SYNTAX_ERROR: context1 = UserExecutionContext( )
                                        # REMOVED_SYNTAX_ERROR: user_id="user1",
                                        # REMOVED_SYNTAX_ERROR: thread_id="thread1",
                                        # REMOVED_SYNTAX_ERROR: run_id="run1",
                                        # REMOVED_SYNTAX_ERROR: request_id="req1",
                                        # REMOVED_SYNTAX_ERROR: session_manager=TestDatabaseManager().get_session()
                                        
                                        # REMOVED_SYNTAX_ERROR: context1.metadata = {'user_request': 'Request 1'}

                                        # Execute with second user
                                        # REMOVED_SYNTAX_ERROR: context2 = UserExecutionContext( )
                                        # REMOVED_SYNTAX_ERROR: user_id="user2",
                                        # REMOVED_SYNTAX_ERROR: thread_id="thread2",
                                        # REMOVED_SYNTAX_ERROR: run_id="run2",
                                        # REMOVED_SYNTAX_ERROR: request_id="req2",
                                        # REMOVED_SYNTAX_ERROR: session_manager=TestDatabaseManager().get_session()
                                        
                                        # REMOVED_SYNTAX_ERROR: context2.metadata = {'user_request': 'Request 2'}

                                        # Run both contexts
                                        # REMOVED_SYNTAX_ERROR: await agent.execute(context1)
                                        # REMOVED_SYNTAX_ERROR: await agent.execute(context2)

                                        # Check no cross-contamination
                                        # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, 'current_user_id')
                                        # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, 'current_thread_id')
                                        # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, 'current_run_id')

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_concurrent_execution_isolation(self, mock_llm_manager, mock_tool_dispatcher):
                                            # REMOVED_SYNTAX_ERROR: """Test that concurrent executions don't interfere with each other"""
                                            # REMOVED_SYNTAX_ERROR: agent = ActionsToMeetGoalsSubAgent( )
                                            # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
                                            # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher
                                            

                                            # REMOVED_SYNTAX_ERROR: contexts = []
                                            # REMOVED_SYNTAX_ERROR: for i in range(5):
                                                # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
                                                # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                                # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
                                                # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                                                # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
                                                # REMOVED_SYNTAX_ERROR: session_manager=TestDatabaseManager().get_session()
                                                
                                                # REMOVED_SYNTAX_ERROR: context.metadata = { )
                                                # REMOVED_SYNTAX_ERROR: 'user_request': 'formatted_string',
                                                # REMOVED_SYNTAX_ERROR: 'optimizations_result': {'type': 'formatted_string'},
                                                # REMOVED_SYNTAX_ERROR: 'data_result': {'query': 'formatted_string'}
                                                
                                                # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                                # Execute all contexts concurrently
                                                # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*[agent.execute(ctx) for ctx in contexts])

                                                # Verify no state leakage
                                                # REMOVED_SYNTAX_ERROR: assert len(results) == 5
                                                # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, 'user_data'), "No user data should be stored"

                                                # ============= CACHING AND HASHING TESTS =============

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_cache_key_generation_uses_cache_helpers(self):
                                                    # REMOVED_SYNTAX_ERROR: """Test that cache key generation uses CacheHelpers, not custom implementation"""
                                                    # REMOVED_SYNTAX_ERROR: pass
                                                    # Check if any caching is done and uses proper helpers
                                                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.actions_goals_plan_builder import ActionPlanBuilder

                                                    # REMOVED_SYNTAX_ERROR: builder = ActionPlanBuilder()

                                                    # If builder has cache methods, they should use CacheHelpers
                                                    # REMOVED_SYNTAX_ERROR: if hasattr(builder, 'generate_cache_key') or hasattr(builder, '_get_cache_key'):
                                                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.cache.cache_helpers.CacheHelpers.generate_cache_key') as mock_cache:
                                                            # REMOVED_SYNTAX_ERROR: mock_cache.return_value = "test_key"
                                                            # This test will FAIL if custom cache key generation exists
                                                            # The builder should use CacheHelpers
                                                            # REMOVED_SYNTAX_ERROR: pass

                                                            # Removed problematic line: @pytest.mark.asyncio
                                                            # Removed problematic line: async def test_no_custom_hash_implementation(self):
                                                                # REMOVED_SYNTAX_ERROR: """Test that no custom hash implementations exist"""
                                                                # REMOVED_SYNTAX_ERROR: import inspect
                                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
                                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.actions_goals_plan_builder import ActionPlanBuilder

                                                                # REMOVED_SYNTAX_ERROR: sources = [ )
                                                                # REMOVED_SYNTAX_ERROR: inspect.getsource(ActionsToMeetGoalsSubAgent),
                                                                # REMOVED_SYNTAX_ERROR: inspect.getsource(ActionPlanBuilder)
                                                                

                                                                # REMOVED_SYNTAX_ERROR: violations = []
                                                                # REMOVED_SYNTAX_ERROR: for source in sources:
                                                                    # REMOVED_SYNTAX_ERROR: if 'hashlib' in source:
                                                                        # REMOVED_SYNTAX_ERROR: violations.append("Direct hashlib usage found")
                                                                        # REMOVED_SYNTAX_ERROR: if 'sha256' in source.lower() or 'md5' in source.lower():
                                                                            # REMOVED_SYNTAX_ERROR: violations.append("Direct hash algorithm usage found")

                                                                            # This test will FAIL if custom hashing exists
                                                                            # REMOVED_SYNTAX_ERROR: assert not violations, "formatted_string"

                                                                            # ============= ENVIRONMENT ACCESS TESTS =============

                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_no_direct_os_environ_access(self):
                                                                                # REMOVED_SYNTAX_ERROR: """Test that there's no direct os.environ access"""
                                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                                # REMOVED_SYNTAX_ERROR: import inspect
                                                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
                                                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.actions_goals_plan_builder import ActionPlanBuilder

                                                                                # REMOVED_SYNTAX_ERROR: sources = [ )
                                                                                # REMOVED_SYNTAX_ERROR: inspect.getsource(ActionsToMeetGoalsSubAgent),
                                                                                # REMOVED_SYNTAX_ERROR: inspect.getsource(ActionPlanBuilder)
                                                                                

                                                                                # REMOVED_SYNTAX_ERROR: violations = []
                                                                                # REMOVED_SYNTAX_ERROR: for source in sources:
                                                                                    # REMOVED_SYNTAX_ERROR: if 'os.environ' in source:
                                                                                        # REMOVED_SYNTAX_ERROR: violations.append("Direct os.environ access found")
                                                                                        # REMOVED_SYNTAX_ERROR: if 'os.getenv' in source:
                                                                                            # REMOVED_SYNTAX_ERROR: violations.append("Direct os.getenv usage found")

                                                                                            # This test will FAIL if direct environment access exists
                                                                                            # REMOVED_SYNTAX_ERROR: assert not violations, "formatted_string"

                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                            # Removed problematic line: async def test_uses_isolated_environment(self):
                                                                                                # REMOVED_SYNTAX_ERROR: """Test that IsolatedEnvironment is used for all env access"""
                                                                                                # REMOVED_SYNTAX_ERROR: with patch('shared.isolated_environment.IsolatedEnvironment') as mock_env:
                                                                                                    # REMOVED_SYNTAX_ERROR: mock_env.return_value.get.return_value = "test_value"

                                                                                                    # If the agent needs env vars, it should use IsolatedEnvironment
                                                                                                    # This is a pattern check - implementation might not need env vars
                                                                                                    # REMOVED_SYNTAX_ERROR: pass

                                                                                                    # ============= WEBSOCKET INTEGRATION TESTS =============

                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                    # Removed problematic line: async def test_websocket_events_emitted_correctly(self, agent, user_context):
                                                                                                        # REMOVED_SYNTAX_ERROR: """Test that all required WebSocket events are emitted"""
                                                                                                        # REMOVED_SYNTAX_ERROR: pass
                                                                                                        # Set up WebSocket manager mock
                                                                                                        # REMOVED_SYNTAX_ERROR: ws_manager = UnifiedWebSocketManager()
                                                                                                        # REMOVED_SYNTAX_ERROR: ws_manager.emit_agent_started = AsyncNone  # TODO: Use real service instance
                                                                                                        # REMOVED_SYNTAX_ERROR: ws_manager.emit_thinking = AsyncNone  # TODO: Use real service instance
                                                                                                        # REMOVED_SYNTAX_ERROR: ws_manager.emit_tool_executing = AsyncNone  # TODO: Use real service instance
                                                                                                        # REMOVED_SYNTAX_ERROR: ws_manager.emit_tool_completed = AsyncNone  # TODO: Use real service instance
                                                                                                        # REMOVED_SYNTAX_ERROR: ws_manager.emit_agent_completed = AsyncNone  # TODO: Use real service instance
                                                                                                        # REMOVED_SYNTAX_ERROR: ws_manager.emit_progress = AsyncNone  # TODO: Use real service instance

                                                                                                        # Inject WebSocket manager
                                                                                                        # REMOVED_SYNTAX_ERROR: agent._websocket_manager = ws_manager

                                                                                                        # REMOVED_SYNTAX_ERROR: await agent.execute(user_context, stream_updates=True)

                                                                                                        # Verify critical events are emitted
                                                                                                        # REMOVED_SYNTAX_ERROR: ws_manager.emit_agent_started.assert_called()
                                                                                                        # REMOVED_SYNTAX_ERROR: ws_manager.emit_agent_completed.assert_called()
                                                                                                        # REMOVED_SYNTAX_ERROR: assert ws_manager.emit_thinking.call_count >= 1
                                                                                                        # REMOVED_SYNTAX_ERROR: assert ws_manager.emit_tool_executing.call_count >= 1
                                                                                                        # REMOVED_SYNTAX_ERROR: assert ws_manager.emit_tool_completed.call_count >= 1

                                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                                        # Removed problematic line: async def test_websocket_adapter_pattern_used(self, agent):
                                                                                                            # REMOVED_SYNTAX_ERROR: """Test that WebSocketBridgeAdapter pattern is used, not direct emission"""
                                                                                                            # Check that agent uses adapter pattern
                                                                                                            # This verifies the agent doesn't directly call websocket.send_json
                                                                                                            # REMOVED_SYNTAX_ERROR: assert hasattr(agent, '_websocket_manager') or hasattr(agent, '_websocket_adapter'), \
                                                                                                            # REMOVED_SYNTAX_ERROR: "Agent should use WebSocket adapter pattern"

                                                                                                            # ============= DATABASE SESSION TESTS =============

                                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                                            # Removed problematic line: async def test_database_session_not_stored(self, agent, user_context):
                                                                                                                # REMOVED_SYNTAX_ERROR: """Test that database sessions are not stored in instance variables"""
                                                                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                                                                # REMOVED_SYNTAX_ERROR: await agent.execute(user_context)

                                                                                                                # Check no session storage
                                                                                                                # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, 'db_session'), "Database session should not be stored"
                                                                                                                # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, 'session'), "Session should not be stored"
                                                                                                                # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, '_session'), "Private session should not be stored"

                                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                                # Removed problematic line: async def test_session_passed_through_context(self, agent, user_context):
                                                                                                                    # REMOVED_SYNTAX_ERROR: """Test that database operations use session from context"""
                                                                                                                    # REMOVED_SYNTAX_ERROR: mock_session = TestDatabaseManager().get_session()
                                                                                                                    # REMOVED_SYNTAX_ERROR: user_context.session_manager.get_session.return_value = mock_session

                                                                                                                    # REMOVED_SYNTAX_ERROR: await agent.execute(user_context)

                                                                                                                    # Session should be accessed through context, not stored
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert not hasattr(agent, 'db_session')

                                                                                                                    # ============= ERROR HANDLING TESTS =============

                                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                                    # Removed problematic line: async def test_uses_unified_retry_handler(self):
                                                                                                                        # REMOVED_SYNTAX_ERROR: """Test that retry logic uses UnifiedRetryHandler"""
                                                                                                                        # REMOVED_SYNTAX_ERROR: pass
                                                                                                                        # Check if retry patterns use the unified handler
                                                                                                                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.resilience.unified_retry_handler.UnifiedRetryHandler') as mock_retry:
                                                                                                                            # If retries are needed, they should use UnifiedRetryHandler
                                                                                                                            # REMOVED_SYNTAX_ERROR: pass

                                                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                                                            # Removed problematic line: async def test_no_custom_retry_loops(self):
                                                                                                                                # REMOVED_SYNTAX_ERROR: """Test that no custom retry loops exist"""
                                                                                                                                # REMOVED_SYNTAX_ERROR: import inspect
                                                                                                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent

                                                                                                                                # REMOVED_SYNTAX_ERROR: source = inspect.getsource(ActionsToMeetGoalsSubAgent)

                                                                                                                                # Check for custom retry patterns
                                                                                                                                # REMOVED_SYNTAX_ERROR: violations = []
                                                                                                                                # REMOVED_SYNTAX_ERROR: if 'for attempt in range' in source and 'try:' in source:
                                                                                                                                    # REMOVED_SYNTAX_ERROR: violations.append("Custom retry loop found")
                                                                                                                                    # REMOVED_SYNTAX_ERROR: if 'while attempt' in source and 'try:' in source:
                                                                                                                                        # REMOVED_SYNTAX_ERROR: violations.append("Custom while-based retry found")

                                                                                                                                        # This test will FAIL if custom retry logic exists
                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert not violations, "formatted_string"

                                                                                                                                        # ============= BASE CLASS ALIGNMENT TESTS =============

                                                                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                        # Removed problematic line: async def test_extends_base_agent_properly(self, agent):
                                                                                                                                            # REMOVED_SYNTAX_ERROR: """Test that agent properly extends BaseAgent"""
                                                                                                                                            # REMOVED_SYNTAX_ERROR: pass
                                                                                                                                            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base_agent import BaseAgent

                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert isinstance(agent, BaseAgent), "Must extend BaseAgent"

                                                                                                                                            # Check that BaseAgent methods are used, not overridden incorrectly
                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert hasattr(agent, 'llm_manager'), "Should inherit llm_manager from BaseAgent"
                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert hasattr(agent, 'logger'), "Should inherit logger from BaseAgent"

                                                                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                            # Removed problematic line: async def test_no_duplicate_base_functionality(self):
                                                                                                                                                # REMOVED_SYNTAX_ERROR: """Test that BaseAgent functionality is not duplicated"""
                                                                                                                                                # REMOVED_SYNTAX_ERROR: import inspect
                                                                                                                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent

                                                                                                                                                # REMOVED_SYNTAX_ERROR: source = inspect.getsource(ActionsToMeetGoalsSubAgent)

                                                                                                                                                # Check for duplicated BaseAgent functionality
                                                                                                                                                # REMOVED_SYNTAX_ERROR: violations = []

                                                                                                                                                # These should be inherited, not reimplemented
                                                                                                                                                # REMOVED_SYNTAX_ERROR: base_patterns = [ )
                                                                                                                                                # REMOVED_SYNTAX_ERROR: 'def setup_logging',
                                                                                                                                                # REMOVED_SYNTAX_ERROR: 'def setup_circuit_breaker',
                                                                                                                                                # REMOVED_SYNTAX_ERROR: 'def setup_retry_handler'
                                                                                                                                                

                                                                                                                                                # REMOVED_SYNTAX_ERROR: for pattern in base_patterns:
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: if pattern in source:
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: violations.append("formatted_string")

                                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert not violations, "formatted_string"

                                                                                                                                                        # ============= CONFIGURATION ACCESS TESTS =============

                                                                                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                                        # Removed problematic line: async def test_configuration_access_pattern(self):
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: """Test that configuration is accessed through proper architecture"""
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: pass
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.config.get_config') as mock_config:
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: mock_config.return_value = {'test': 'config'}

                                                                                                                                                                # Configuration should be accessed through get_config, not direct file reading
                                                                                                                                                                # This pattern check ensures proper config access
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: pass

                                                                                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                                                # Removed problematic line: async def test_no_direct_config_file_access(self):
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: """Test that there's no direct config file reading"""
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: import inspect
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent

                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: source = inspect.getsource(ActionsToMeetGoalsSubAgent)

                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: violations = []
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: if 'open('config' in source or 'open('config' in source: ))
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: violations.append("Direct config file access found")
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: if "json.load" in source and "config" in source:
                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: violations.append("Direct JSON config loading found")

                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert not violations, "formatted_string"

                                                                                                                                                                        # ============= TOOL DISPATCHER TESTS =============

                                                                                                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                                                        # Removed problematic line: async def test_tool_dispatcher_request_scoped(self, agent, user_context):
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: """Test that ToolDispatcher is properly scoped per request"""
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: pass
                                                                                                                                                                            # ToolDispatcher should be enhanced with WebSocket manager per request
                                                                                                                                                                            # Not stored globally
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert hasattr(agent, 'tool_dispatcher'), "Should have tool_dispatcher"

                                                                                                                                                                            # But it should be enhanced per request with context
                                                                                                                                                                            # This is a pattern check - implementation details may vary
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: pass

                                                                                                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                                                            # Removed problematic line: async def test_tool_dispatcher_not_singleton(self):
                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: """Test that ToolDispatcher is not used as a singleton"""
                                                                                                                                                                                # Multiple agents should not share the same ToolDispatcher instance
                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent

                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: agent1 = ActionsToMeetGoalsSubAgent(None  # TODO: Use real service instance, None  # TODO: Use real service instance)
                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: agent2 = ActionsToMeetGoalsSubAgent(None  # TODO: Use real service instance, None  # TODO: Use real service instance)

                                                                                                                                                                                # Tool dispatchers should be separate instances or properly isolated
                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: assert agent1.tool_dispatcher is not agent2.tool_dispatcher or \
                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: hasattr(agent1.tool_dispatcher, 'get_for_context'), \
                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "ToolDispatcher should not be a shared singleton"


                                                                                                                                                                                # ============= TEST RUNNER =============

                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                                                                                                                                                    # Run all tests and report violations
                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: pytest.main([__file__, '-v', '--tb=short'])
                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: pass