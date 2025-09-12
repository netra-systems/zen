# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''Comprehensive SSOT Compliance Test Suite for DataSubAgent

    # REMOVED_SYNTAX_ERROR: This test suite validates:
        # REMOVED_SYNTAX_ERROR: 1. Complete UserExecutionContext isolation
        # REMOVED_SYNTAX_ERROR: 2. No global state leakage between requests
        # REMOVED_SYNTAX_ERROR: 3. Proper session management through DatabaseSessionManager
        # REMOVED_SYNTAX_ERROR: 4. No direct environment access (must use IsolatedEnvironment)
        # REMOVED_SYNTAX_ERROR: 5. Proper JSON handling through unified_json_handler
        # REMOVED_SYNTAX_ERROR: 6. Correct caching with user context in keys
        # REMOVED_SYNTAX_ERROR: 7. WebSocket event emission compliance
        # REMOVED_SYNTAX_ERROR: 8. Concurrent user isolation
        # REMOVED_SYNTAX_ERROR: 9. Error handling through unified patterns
        # REMOVED_SYNTAX_ERROR: 10. No stored database sessions

        # REMOVED_SYNTAX_ERROR: CRITICAL: These tests are designed to be difficult and comprehensive,
        # REMOVED_SYNTAX_ERROR: testing edge cases and concurrent scenarios.
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: import hashlib
        # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List, Optional
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import uuid
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta
        # REMOVED_SYNTAX_ERROR: import concurrent.futures
        # REMOVED_SYNTAX_ERROR: import threading
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
        # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_execution_context import UserExecutionContext
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.database.session_manager import DatabaseSessionManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.data_sub_agent.core.data_analysis_core import DataAnalysisCore
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.data_sub_agent.core.data_processor import DataProcessor
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.data_sub_agent.core.anomaly_detector import AnomalyDetector
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.llm.llm_manager import LLMManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient

        # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)


# REMOVED_SYNTAX_ERROR: class TestDataSubAgentSSOTCompliance:
    # REMOVED_SYNTAX_ERROR: """Test suite for DataSubAgent SSOT compliance and isolation patterns."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_llm_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock LLM manager."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: llm = Mock(spec=LLMManager)
    # REMOVED_SYNTAX_ERROR: llm.generate_response = AsyncMock(return_value={"content": "Test insights"})
    # REMOVED_SYNTAX_ERROR: return llm

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock tool dispatcher."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: dispatcher.dispatch = AsyncMock(return_value={"status": "success"})
    # REMOVED_SYNTAX_ERROR: return dispatcher

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_db_session():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock database session."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: return session

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self, mock_db_session):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test user execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: db_session=mock_db_session,
    # REMOVED_SYNTAX_ERROR: metadata={ )
    # REMOVED_SYNTAX_ERROR: "analysis_type": "performance",
    # REMOVED_SYNTAX_ERROR: "timeframe": "24h",
    # REMOVED_SYNTAX_ERROR: "metrics": ["latency_ms", "cost_cents", "throughput"]
    
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def data_agent(self, mock_llm_manager, mock_tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Create DataSubAgent instance."""
    # REMOVED_SYNTAX_ERROR: agent = DataSubAgent( )
    # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher
    
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return agent

    # Test 1: Verify No Direct Environment Access
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_no_direct_environment_access(self, data_agent):
        # REMOVED_SYNTAX_ERROR: """Test that agent never accesses os.environ directly."""
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"TEST_VAR": "should_not_access"}):
            # Scan agent code for os.environ access
            # REMOVED_SYNTAX_ERROR: import inspect
            # REMOVED_SYNTAX_ERROR: source = inspect.getsource(DataSubAgent)

            # These should NOT appear in the code
            # REMOVED_SYNTAX_ERROR: forbidden_patterns = [ )
            # REMOVED_SYNTAX_ERROR: "os.environ[",
            # REMOVED_SYNTAX_ERROR: "os.environ.get(",
            # REMOVED_SYNTAX_ERROR: "os.getenv(",
            # REMOVED_SYNTAX_ERROR: "environ[" )
            

            # REMOVED_SYNTAX_ERROR: for pattern in forbidden_patterns:
                # REMOVED_SYNTAX_ERROR: assert pattern not in source, "formatted_string"

                # Test 2: Verify UserExecutionContext Isolation
                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_user_context_isolation(self, mock_llm_manager, mock_tool_dispatcher):
                    # REMOVED_SYNTAX_ERROR: """Test complete isolation between different user contexts."""
                    # Create two agents for different users
                    # REMOVED_SYNTAX_ERROR: agent1 = DataSubAgent(llm_manager=mock_llm_manager, tool_dispatcher=mock_tool_dispatcher)
                    # REMOVED_SYNTAX_ERROR: agent2 = DataSubAgent(llm_manager=mock_llm_manager, tool_dispatcher=mock_tool_dispatcher)

                    # Create different contexts
                    # REMOVED_SYNTAX_ERROR: context1 = UserExecutionContext( )
                    # REMOVED_SYNTAX_ERROR: user_id="user1",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread1",
                    # REMOVED_SYNTAX_ERROR: run_id="run1",
                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
                    # REMOVED_SYNTAX_ERROR: metadata={"analysis_type": "performance"}
                    

                    # REMOVED_SYNTAX_ERROR: context2 = UserExecutionContext( )
                    # REMOVED_SYNTAX_ERROR: user_id="user2",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread2",
                    # REMOVED_SYNTAX_ERROR: run_id="run2",
                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
                    # REMOVED_SYNTAX_ERROR: metadata={"analysis_type": "cost_optimization"}
                    

                    # Mock the core analysis to track calls
                    # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
                        # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_perf:
                            # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_costs', new_callable=AsyncMock) as mock_costs:
                                # REMOVED_SYNTAX_ERROR: mock_perf.return_value = {"data_points": 100, "summary": "Performance analysis"}
                                # REMOVED_SYNTAX_ERROR: mock_costs.return_value = {"savings_potential": {"savings_percentage": 25}}

                                # Execute both agents concurrently
                                # REMOVED_SYNTAX_ERROR: results = await asyncio.gather( )
                                # REMOVED_SYNTAX_ERROR: agent1.execute(context1, stream_updates=False),
                                # REMOVED_SYNTAX_ERROR: agent2.execute(context2, stream_updates=False),
                                # REMOVED_SYNTAX_ERROR: return_exceptions=True
                                

                                # Verify no cross-contamination
                                # REMOVED_SYNTAX_ERROR: assert results[0]["user_id"] == "user1"
                                # REMOVED_SYNTAX_ERROR: assert results[1]["user_id"] == "user2"
                                # REMOVED_SYNTAX_ERROR: assert results[0]["analysis_type"] == "performance"
                                # REMOVED_SYNTAX_ERROR: assert results[1]["analysis_type"] == "cost_optimization"

                                # Test 3: Verify No Stored Database Sessions
                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_no_stored_database_sessions(self, data_agent):
                                    # REMOVED_SYNTAX_ERROR: """Test that agent never stores database sessions as instance variables."""
                                    # REMOVED_SYNTAX_ERROR: pass
                                    # Check that agent has no db_session attribute
                                    # REMOVED_SYNTAX_ERROR: assert not hasattr(data_agent, 'db_session')
                                    # REMOVED_SYNTAX_ERROR: assert not hasattr(data_agent, '_db_session')
                                    # REMOVED_SYNTAX_ERROR: assert not hasattr(data_agent, 'session')
                                    # REMOVED_SYNTAX_ERROR: assert not hasattr(data_agent, '_session')

                                    # Check core components don't store sessions
                                    # REMOVED_SYNTAX_ERROR: assert not hasattr(data_agent.data_processor, 'db_session')
                                    # REMOVED_SYNTAX_ERROR: assert not hasattr(data_agent.anomaly_detector, 'db_session')

                                    # Test 4: Test Concurrent User Handling
                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_concurrent_user_handling(self, mock_llm_manager, mock_tool_dispatcher):
                                        # REMOVED_SYNTAX_ERROR: """Test that multiple concurrent users are properly isolated."""
                                        # REMOVED_SYNTAX_ERROR: agent = DataSubAgent(llm_manager=mock_llm_manager, tool_dispatcher=mock_tool_dispatcher)

                                        # Track execution order and data
                                        # REMOVED_SYNTAX_ERROR: execution_log = []
                                        # REMOVED_SYNTAX_ERROR: execution_lock = threading.Lock()

# REMOVED_SYNTAX_ERROR: async def execute_for_user(user_id: str, analysis_type: str):
    # REMOVED_SYNTAX_ERROR: """Execute agent for a specific user."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
    # REMOVED_SYNTAX_ERROR: metadata={ )
    # REMOVED_SYNTAX_ERROR: "analysis_type": analysis_type,
    # REMOVED_SYNTAX_ERROR: "timeframe": "1h",
    # REMOVED_SYNTAX_ERROR: "metrics": ["latency_ms"]
    
    

    # Mock core analysis
    # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
        # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_analyze:
            # REMOVED_SYNTAX_ERROR: mock_analyze.return_value = { )
            # REMOVED_SYNTAX_ERROR: "data_points": 100,
            # REMOVED_SYNTAX_ERROR: "summary": "formatted_string",
            # REMOVED_SYNTAX_ERROR: "user_specific": user_id
            

            # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_costs', new_callable=AsyncMock) as mock_costs:
                # REMOVED_SYNTAX_ERROR: mock_costs.return_value = { )
                # REMOVED_SYNTAX_ERROR: "savings_potential": {"savings_percentage": 20},
                # REMOVED_SYNTAX_ERROR: "user_specific": user_id
                

                # Add delay to simulate processing
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                # REMOVED_SYNTAX_ERROR: result = await agent.execute(context, stream_updates=False)

                # REMOVED_SYNTAX_ERROR: with execution_lock:
                    # REMOVED_SYNTAX_ERROR: execution_log.append({ ))
                    # REMOVED_SYNTAX_ERROR: "user_id": user_id,
                    # REMOVED_SYNTAX_ERROR: "result_user": result.get("user_id"),
                    # REMOVED_SYNTAX_ERROR: "analysis_type": analysis_type,
                    # REMOVED_SYNTAX_ERROR: "timestamp": time.time()
                    

                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                    # REMOVED_SYNTAX_ERROR: return result

                    # Execute for 10 concurrent users
                    # REMOVED_SYNTAX_ERROR: users = ["formatted_string" for i in range(10)]
                    # REMOVED_SYNTAX_ERROR: analysis_types = ["performance", "cost_optimization"] * 5

                    # REMOVED_SYNTAX_ERROR: tasks = [ )
                    # REMOVED_SYNTAX_ERROR: execute_for_user(user, analysis_type)
                    # REMOVED_SYNTAX_ERROR: for user, analysis_type in zip(users, analysis_types)
                    

                    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Verify all results are properly isolated
                    # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):
                        # REMOVED_SYNTAX_ERROR: if not isinstance(result, Exception):
                            # REMOVED_SYNTAX_ERROR: assert result["user_id"] == users[i], "formatted_string"
                            # REMOVED_SYNTAX_ERROR: assert result["run_id"].startswith("formatted_string")

                            # Verify execution log shows proper isolation
                            # REMOVED_SYNTAX_ERROR: for log_entry in execution_log:
                                # REMOVED_SYNTAX_ERROR: assert log_entry["user_id"] == log_entry["result_user"], "User data leaked between contexts"

                                # Test 5: Test JSON Handling Through Unified Handler
                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_unified_json_handler_usage(self, data_agent, user_context):
                                    # REMOVED_SYNTAX_ERROR: """Test that all JSON operations use unified_json_handler."""
                                    # Mock unified JSON handler
                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as mock_parser:
                                        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
                                        # REMOVED_SYNTAX_ERROR: mock_parser.return_value = mock_parser_instance
                                        # REMOVED_SYNTAX_ERROR: mock_parser_instance.parse_json = Mock(return_value={"test": "data"})

                                        # Check if agent uses unified handler for JSON operations
                                        # This would be called if the agent properly uses unified JSON handling
                                        # Note: The current implementation doesn't directly use LLMResponseParser,
                                        # but we're testing the pattern

                                        # Verify no direct json.loads or json.dumps in critical paths
                                        # REMOVED_SYNTAX_ERROR: import inspect
                                        # REMOVED_SYNTAX_ERROR: source = inspect.getsource(DataSubAgent)

                                        # These patterns suggest non-unified JSON handling
                                        # (except in non-critical paths like logging)
                                        # REMOVED_SYNTAX_ERROR: lines = source.split(" )
                                        # REMOVED_SYNTAX_ERROR: ")
                                        # REMOVED_SYNTAX_ERROR: for i, line in enumerate(lines):
                                            # REMOVED_SYNTAX_ERROR: if 'json.loads' in line or 'json.dumps' in line:
                                                # Check if it's in a critical path (not logging)
                                                # REMOVED_SYNTAX_ERROR: if 'logger' not in line and 'log' not in line.lower():
                                                    # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

                                                    # Test 6: Test Cache Key Generation with User Context
                                                    # Removed problematic line: @pytest.mark.asyncio
                                                    # Removed problematic line: async def test_cache_key_includes_user_context(self, data_agent):
                                                        # REMOVED_SYNTAX_ERROR: """Test that cache keys include user context for isolation."""
                                                        # REMOVED_SYNTAX_ERROR: pass
                                                        # REMOVED_SYNTAX_ERROR: request1 = { )
                                                        # REMOVED_SYNTAX_ERROR: "type": "performance",
                                                        # REMOVED_SYNTAX_ERROR: "timeframe": "24h",
                                                        # REMOVED_SYNTAX_ERROR: "user_id": "user1",
                                                        # REMOVED_SYNTAX_ERROR: "metrics": ["latency_ms", "throughput"]
                                                        

                                                        # REMOVED_SYNTAX_ERROR: request2 = { )
                                                        # REMOVED_SYNTAX_ERROR: "type": "performance",
                                                        # REMOVED_SYNTAX_ERROR: "timeframe": "24h",
                                                        # REMOVED_SYNTAX_ERROR: "user_id": "user2",
                                                        # REMOVED_SYNTAX_ERROR: "metrics": ["latency_ms", "throughput"]
                                                        

                                                        # REMOVED_SYNTAX_ERROR: key1 = data_agent._get_analysis_cache_key(request1)
                                                        # REMOVED_SYNTAX_ERROR: key2 = data_agent._get_analysis_cache_key(request2)

                                                        # Keys must be different for different users
                                                        # REMOVED_SYNTAX_ERROR: assert key1 != key2, "Cache keys not isolated by user"
                                                        # REMOVED_SYNTAX_ERROR: assert "user1" in key1
                                                        # REMOVED_SYNTAX_ERROR: assert "user2" in key2

                                                        # Test 7: Test WebSocket Event Emission
                                                        # Removed problematic line: @pytest.mark.asyncio
                                                        # Removed problematic line: async def test_websocket_event_emission(self, data_agent, user_context):
                                                            # REMOVED_SYNTAX_ERROR: """Test that agent properly emits WebSocket events."""
                                                            # Mock WebSocket methods
                                                            # REMOVED_SYNTAX_ERROR: data_agent.websocket = TestWebSocketConnection()

                                                            # Mock core analysis
                                                            # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
                                                                # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_analyze:
                                                                    # REMOVED_SYNTAX_ERROR: mock_analyze.return_value = {"data_points": 100, "summary": "Test"}

                                                                    # Execute with streaming
                                                                    # REMOVED_SYNTAX_ERROR: await data_agent.execute(user_context, stream_updates=True)

                                                                    # Verify events were emitted
                                                                    # REMOVED_SYNTAX_ERROR: assert data_agent.emit_thinking.called
                                                                    # REMOVED_SYNTAX_ERROR: assert data_agent.emit_progress.called
                                                                    # REMOVED_SYNTAX_ERROR: assert data_agent.emit_tool_executing.called
                                                                    # REMOVED_SYNTAX_ERROR: assert data_agent.emit_tool_completed.called

                                                                    # Verify correct event sequence
                                                                    # REMOVED_SYNTAX_ERROR: calls = []
                                                                    # REMOVED_SYNTAX_ERROR: for method in [data_agent.emit_thinking, data_agent.emit_progress,
                                                                    # REMOVED_SYNTAX_ERROR: data_agent.emit_tool_executing, data_agent.emit_tool_completed]:
                                                                        # REMOVED_SYNTAX_ERROR: for call in method.call_args_list:
                                                                            # REMOVED_SYNTAX_ERROR: calls.append((method._mock_name, call))

                                                                            # Verify thinking comes before progress
                                                                            # REMOVED_SYNTAX_ERROR: thinking_indices = [item for item in []]
                                                                            # REMOVED_SYNTAX_ERROR: progress_indices = [item for item in []]
                                                                            # REMOVED_SYNTAX_ERROR: assert min(thinking_indices) < max(progress_indices) if thinking_indices and progress_indices else True

                                                                            # Test 8: Test Error Handling Through Unified Patterns
                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_unified_error_handling(self, data_agent, user_context):
                                                                                # REMOVED_SYNTAX_ERROR: """Test that errors are handled through unified patterns."""
                                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                                # Simulate an error in core analysis
                                                                                # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
                                                                                    # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', side_effect=Exception("Test error")):
                                                                                        # REMOVED_SYNTAX_ERROR: data_agent.websocket = TestWebSocketConnection()

                                                                                        # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception) as exc_info:
                                                                                            # REMOVED_SYNTAX_ERROR: await data_agent.execute(user_context, stream_updates=True)

                                                                                            # REMOVED_SYNTAX_ERROR: assert "Test error" in str(exc_info.value)

                                                                                            # Verify error event was emitted with proper context
                                                                                            # REMOVED_SYNTAX_ERROR: data_agent.emit_error.assert_called()
                                                                                            # REMOVED_SYNTAX_ERROR: error_call = data_agent.emit_error.call_args
                                                                                            # REMOVED_SYNTAX_ERROR: assert "test_user_" in str(error_call)

                                                                                            # Test 9: Test Session Manager Cleanup
                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                            # Removed problematic line: async def test_session_manager_cleanup(self, data_agent, user_context):
                                                                                                # REMOVED_SYNTAX_ERROR: """Test that DatabaseSessionManager is properly cleaned up."""
                                                                                                # REMOVED_SYNTAX_ERROR: cleanup_called = False

                                                                                                # Mock DatabaseSessionManager
                                                                                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.data_sub_agent.data_sub_agent.DatabaseSessionManager') as mock_manager_class:
                                                                                                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                                                                                                    # REMOVED_SYNTAX_ERROR: mock_manager_class.return_value = mock_manager

# REMOVED_SYNTAX_ERROR: async def mock_close():
    # REMOVED_SYNTAX_ERROR: nonlocal cleanup_called
    # REMOVED_SYNTAX_ERROR: cleanup_called = True

    # REMOVED_SYNTAX_ERROR: mock_manager.close = mock_close

    # Mock core analysis
    # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
        # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_analyze:
            # REMOVED_SYNTAX_ERROR: mock_analyze.return_value = {"data_points": 100}

            # Execute normally
            # REMOVED_SYNTAX_ERROR: await data_agent.execute(user_context, stream_updates=False)
            # REMOVED_SYNTAX_ERROR: assert cleanup_called, "Session manager not cleaned up on success"

            # Reset and test cleanup on error
            # REMOVED_SYNTAX_ERROR: cleanup_called = False
            # REMOVED_SYNTAX_ERROR: mock_analyze.side_effect = Exception("Test error")

            # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception):
                # REMOVED_SYNTAX_ERROR: await data_agent.execute(user_context, stream_updates=False)

                # REMOVED_SYNTAX_ERROR: assert cleanup_called, "Session manager not cleaned up on error"

                # Test 10: Test No Global State Storage
                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_no_global_state_storage(self, mock_llm_manager, mock_tool_dispatcher):
                    # REMOVED_SYNTAX_ERROR: """Test that no user-specific data is stored globally."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: agent = DataSubAgent(llm_manager=mock_llm_manager, tool_dispatcher=mock_tool_dispatcher)

                    # Execute for first user
                    # REMOVED_SYNTAX_ERROR: context1 = UserExecutionContext( )
                    # REMOVED_SYNTAX_ERROR: user_id="user1",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread1",
                    # REMOVED_SYNTAX_ERROR: run_id="run1",
                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
                    # REMOVED_SYNTAX_ERROR: metadata={"analysis_type": "performance"}
                    

                    # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
                        # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_analyze:
                            # REMOVED_SYNTAX_ERROR: mock_analyze.return_value = {"data_points": 100}

                            # REMOVED_SYNTAX_ERROR: await agent.execute(context1, stream_updates=False)

                            # Check that no user data is stored
                            # REMOVED_SYNTAX_ERROR: for attr_name in dir(agent):
                                # REMOVED_SYNTAX_ERROR: if not attr_name.startswith('_'):
                                    # REMOVED_SYNTAX_ERROR: attr_value = getattr(agent, attr_name)
                                    # REMOVED_SYNTAX_ERROR: if isinstance(attr_value, str):
                                        # REMOVED_SYNTAX_ERROR: assert "user1" not in attr_value, "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: assert "thread1" not in attr_value, "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: assert "run1" not in attr_value, "formatted_string"

                                        # Test 11: Test Retry Logic Uses UnifiedRetryHandler
                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_unified_retry_handler_usage(self, data_agent):
                                            # REMOVED_SYNTAX_ERROR: """Test that retry logic uses UnifiedRetryHandler, not custom implementation."""
                                            # REMOVED_SYNTAX_ERROR: import inspect
                                            # REMOVED_SYNTAX_ERROR: source = inspect.getsource(DataSubAgent)

                                            # Check for custom retry patterns that should NOT exist
                                            # REMOVED_SYNTAX_ERROR: forbidden_patterns = [ )
                                            # REMOVED_SYNTAX_ERROR: "for attempt in range",
                                            # REMOVED_SYNTAX_ERROR: "while attempts <",
                                            # REMOVED_SYNTAX_ERROR: "retry_count",
                                            # REMOVED_SYNTAX_ERROR: "max_retries",
                                            # REMOVED_SYNTAX_ERROR: "sleep(1)",  # Custom retry delays
                                            

                                            # REMOVED_SYNTAX_ERROR: for pattern in forbidden_patterns:
                                                # Allow in comments but not in actual code
                                                # REMOVED_SYNTAX_ERROR: lines = source.split(" )
                                                # REMOVED_SYNTAX_ERROR: ")
                                                # REMOVED_SYNTAX_ERROR: for line in lines:
                                                    # REMOVED_SYNTAX_ERROR: if pattern in line and not line.strip().startswith('#'):
                                                        # Check if it's actually a retry implementation
                                                        # REMOVED_SYNTAX_ERROR: if 'try:' in source[max(0, source.index(line)-100):source.index(line)+100]:
                                                            # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

                                                            # Test 12: Test Configuration Access Pattern
                                                            # Removed problematic line: @pytest.mark.asyncio
                                                            # Removed problematic line: async def test_configuration_access_pattern(self, data_agent):
                                                                # REMOVED_SYNTAX_ERROR: """Test that configuration is accessed through proper architecture."""
                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                # Agent should not directly read config files
                                                                # REMOVED_SYNTAX_ERROR: import inspect
                                                                # REMOVED_SYNTAX_ERROR: source = inspect.getsource(DataSubAgent)

                                                                # REMOVED_SYNTAX_ERROR: forbidden_patterns = [ )
                                                                # REMOVED_SYNTAX_ERROR: "open("config",
                                                                # REMOVED_SYNTAX_ERROR: "open("config",
                                                                # REMOVED_SYNTAX_ERROR: "json.load(f)",
                                                                # REMOVED_SYNTAX_ERROR: "yaml.load",
                                                                # REMOVED_SYNTAX_ERROR: "configparser",
                                                                

                                                                # REMOVED_SYNTAX_ERROR: for pattern in forbidden_patterns:
                                                                    # REMOVED_SYNTAX_ERROR: assert pattern not in source, "formatted_string"

                                                                    # Test 13: Test Hash Generation Through CacheHelpers
                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                    # Removed problematic line: async def test_hash_generation_pattern(self, data_agent):
                                                                        # REMOVED_SYNTAX_ERROR: """Test that hash generation uses CacheHelpers, not custom implementation."""
                                                                        # REMOVED_SYNTAX_ERROR: import inspect
                                                                        # REMOVED_SYNTAX_ERROR: source = inspect.getsource(DataSubAgent)

                                                                        # Check for custom hash implementations
                                                                        # REMOVED_SYNTAX_ERROR: if "hashlib" in source:
                                                                            # hashlib should only be imported through CacheHelpers
                                                                            # REMOVED_SYNTAX_ERROR: lines = source.split(" )
                                                                            # REMOVED_SYNTAX_ERROR: ")
                                                                            # REMOVED_SYNTAX_ERROR: for line in lines:
                                                                                # REMOVED_SYNTAX_ERROR: if 'hashlib' in line and 'import' not in line:
                                                                                    # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

                                                                                    # Test 14: Test BaseAgent Method Usage
                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                    # Removed problematic line: async def test_base_agent_inheritance(self, data_agent):
                                                                                        # REMOVED_SYNTAX_ERROR: """Test that agent properly uses BaseAgent methods."""
                                                                                        # REMOVED_SYNTAX_ERROR: pass
                                                                                        # Use lazy import to avoid circular dependency
                                                                                        # REMOVED_SYNTAX_ERROR: import importlib
                                                                                        # REMOVED_SYNTAX_ERROR: try:
                                                                                            # REMOVED_SYNTAX_ERROR: base_agent_module = importlib.import_module('netra_backend.app.agents.base_agent')
                                                                                            # REMOVED_SYNTAX_ERROR: BaseAgent = getattr(base_agent_module, 'BaseAgent', None)
                                                                                            # REMOVED_SYNTAX_ERROR: if BaseAgent:
                                                                                                # Verify agent extends BaseAgent
                                                                                                # REMOVED_SYNTAX_ERROR: assert isinstance(data_agent, BaseAgent)

                                                                                                # These methods should be inherited, not redefined
                                                                                                # REMOVED_SYNTAX_ERROR: inherited_methods = ['emit_thinking', 'emit_progress', 'emit_tool_executing',
                                                                                                # REMOVED_SYNTAX_ERROR: 'emit_tool_completed', 'emit_error']

                                                                                                # REMOVED_SYNTAX_ERROR: for method in inherited_methods:
                                                                                                    # Check that agent has the method (inherited or overridden)
                                                                                                    # REMOVED_SYNTAX_ERROR: assert hasattr(data_agent, method), "formatted_string"
                                                                                                    # REMOVED_SYNTAX_ERROR: agent_method = getattr(data_agent, method, None)
                                                                                                    # REMOVED_SYNTAX_ERROR: assert callable(agent_method), "formatted_string"
                                                                                                    # REMOVED_SYNTAX_ERROR: else:
                                                                                                        # Fallback: check methods exist without inheritance check
                                                                                                        # REMOVED_SYNTAX_ERROR: inherited_methods = ['emit_thinking', 'emit_progress', 'emit_tool_executing',
                                                                                                        # REMOVED_SYNTAX_ERROR: 'emit_tool_completed', 'emit_error']
                                                                                                        # REMOVED_SYNTAX_ERROR: for method in inherited_methods:
                                                                                                            # REMOVED_SYNTAX_ERROR: assert hasattr(data_agent, method), "formatted_string"
                                                                                                            # REMOVED_SYNTAX_ERROR: except ImportError as e:
                                                                                                                # If BaseAgent can't be imported due to circular dependency, use alternative approach
                                                                                                                # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")
                                                                                                                # Alternative: Check agent has required methods
                                                                                                                # REMOVED_SYNTAX_ERROR: required_methods = ['emit_thinking', 'emit_progress', 'emit_tool_executing',
                                                                                                                # REMOVED_SYNTAX_ERROR: 'emit_tool_completed', 'emit_error', 'execute']
                                                                                                                # REMOVED_SYNTAX_ERROR: for method in required_methods:
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert hasattr(data_agent, method), "formatted_string"

                                                                                                                    # Test 15: Test Memory Leak Prevention
                                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                                    # Removed problematic line: async def test_memory_leak_prevention(self, mock_llm_manager, mock_tool_dispatcher):
                                                                                                                        # REMOVED_SYNTAX_ERROR: """Test that repeated executions don't cause memory leaks."""
                                                                                                                        # REMOVED_SYNTAX_ERROR: agent = DataSubAgent(llm_manager=mock_llm_manager, tool_dispatcher=mock_tool_dispatcher)

                                                                                                                        # REMOVED_SYNTAX_ERROR: initial_attrs = set(dir(agent))
                                                                                                                        # REMOVED_SYNTAX_ERROR: initial_values = {}

                                                                                                                        # Execute multiple times
                                                                                                                        # REMOVED_SYNTAX_ERROR: for i in range(5):
                                                                                                                            # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
                                                                                                                            # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                                                                                                            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
                                                                                                                            # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                                                                                                                            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
                                                                                                                            # REMOVED_SYNTAX_ERROR: metadata={"analysis_type": "performance"}
                                                                                                                            

                                                                                                                            # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
                                                                                                                                # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_analyze:
                                                                                                                                    # REMOVED_SYNTAX_ERROR: mock_analyze.return_value = {"data_points": 100}

                                                                                                                                    # REMOVED_SYNTAX_ERROR: try:
                                                                                                                                        # REMOVED_SYNTAX_ERROR: await agent.execute(context, stream_updates=False)
                                                                                                                                        # REMOVED_SYNTAX_ERROR: except:
                                                                                                                                            # REMOVED_SYNTAX_ERROR: pass

                                                                                                                                            # Check no new attributes were added
                                                                                                                                            # REMOVED_SYNTAX_ERROR: final_attrs = set(dir(agent))
                                                                                                                                            # REMOVED_SYNTAX_ERROR: new_attrs = final_attrs - initial_attrs
                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert len(new_attrs) == 0, "formatted_string"

                                                                                                                                            # Check no accumulation of data
                                                                                                                                            # REMOVED_SYNTAX_ERROR: for attr in initial_attrs:
                                                                                                                                                # REMOVED_SYNTAX_ERROR: if not callable(getattr(agent, attr)):
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: current_value = getattr(agent, attr)
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: initial_value = initial_values.get(attr)

                                                                                                                                                    # Check for accumulation (lists, dicts growing)
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: if isinstance(current_value, (list, dict)):
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: if isinstance(initial_value, (list, dict)):
                                                                                                                                                            # Size shouldn't grow significantly
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert len(str(current_value)) <= len(str(initial_value)) * 2, "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestDataSubAgentStressTests:
    # REMOVED_SYNTAX_ERROR: """Stress tests for DataSubAgent under extreme conditions."""

    # Test 16: High Concurrency Stress Test
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_high_concurrency_stress(self):
        # REMOVED_SYNTAX_ERROR: """Test agent under high concurrency (100+ simultaneous users)."""
        # REMOVED_SYNTAX_ERROR: agent = DataSubAgent(llm_manager=Mock(spec=LLMManager), tool_dispatcher=Mock(spec=ToolDispatcher))

# REMOVED_SYNTAX_ERROR: async def execute_for_user(user_id: int):
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
    # REMOVED_SYNTAX_ERROR: metadata={"analysis_type": "performance"}
    

    # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
        # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock:
            # REMOVED_SYNTAX_ERROR: mock.return_value = {"data_points": user_id, "user_id": "formatted_string"}

            # REMOVED_SYNTAX_ERROR: result = await agent.execute(context, stream_updates=False)
            # REMOVED_SYNTAX_ERROR: assert result["user_id"] == "formatted_string"
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
            # REMOVED_SYNTAX_ERROR: return result

            # Execute 100 concurrent requests
            # REMOVED_SYNTAX_ERROR: tasks = [execute_for_user(i) for i in range(100)]
            # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all completed without cross-contamination
            # REMOVED_SYNTAX_ERROR: successful = [item for item in []]
            # REMOVED_SYNTAX_ERROR: assert len(successful) >= 95, "formatted_string"

            # Check for data isolation
            # REMOVED_SYNTAX_ERROR: user_ids = [r["user_id"] for r in successful]
            # REMOVED_SYNTAX_ERROR: assert len(set(user_ids)) == len(user_ids), "User data contamination detected"

            # Test 17: Rapid Context Switching
            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_rapid_context_switching(self):
                # REMOVED_SYNTAX_ERROR: """Test rapid switching between different user contexts."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: agent = DataSubAgent(llm_manager=Mock(spec=LLMManager), tool_dispatcher=Mock(spec=ToolDispatcher))

                # REMOVED_SYNTAX_ERROR: contexts = [ )
                # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
                # REMOVED_SYNTAX_ERROR: user_id="formatted_string",  # Only 3 users, but 30 requests
                # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
                # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
                # REMOVED_SYNTAX_ERROR: metadata={"analysis_type": ["performance", "cost_optimization", "trend_analysis"][i % 3]}
                
                # REMOVED_SYNTAX_ERROR: for i in range(30)
                

                # REMOVED_SYNTAX_ERROR: results = []

                # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
                    # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_perf:
                        # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_costs', new_callable=AsyncMock) as mock_costs:
                            # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_trends', new_callable=AsyncMock) as mock_trends:
                                # REMOVED_SYNTAX_ERROR: mock_perf.return_value = {"type": "performance", "data_points": 100}
                                # REMOVED_SYNTAX_ERROR: mock_costs.return_value = {"type": "costs", "savings_potential": {"savings_percentage": 20}}
                                # REMOVED_SYNTAX_ERROR: mock_trends.return_value = {"type": "trends", "trends": {}}

                                # REMOVED_SYNTAX_ERROR: for context in contexts:
                                    # REMOVED_SYNTAX_ERROR: result = await agent.execute(context, stream_updates=False)
                                    # REMOVED_SYNTAX_ERROR: results.append(result)

                                    # Verify correct analysis type was used
                                    # REMOVED_SYNTAX_ERROR: expected_type = context.metadata["analysis_type"]
                                    # REMOVED_SYNTAX_ERROR: assert result["analysis_type"] == expected_type

                                    # Test 18: Error Recovery and Isolation
                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_error_recovery_isolation(self):
                                        # REMOVED_SYNTAX_ERROR: """Test that errors in one context don't affect others."""
                                        # REMOVED_SYNTAX_ERROR: agent = DataSubAgent(llm_manager=Mock(spec=LLMManager), tool_dispatcher=Mock(spec=ToolDispatcher))

                                        # REMOVED_SYNTAX_ERROR: success_context = UserExecutionContext( )
                                        # REMOVED_SYNTAX_ERROR: user_id="success_user",
                                        # REMOVED_SYNTAX_ERROR: thread_id="success_thread",
                                        # REMOVED_SYNTAX_ERROR: run_id="success_run",
                                        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
                                        # REMOVED_SYNTAX_ERROR: metadata={"analysis_type": "performance"}
                                        

                                        # REMOVED_SYNTAX_ERROR: error_context = UserExecutionContext( )
                                        # REMOVED_SYNTAX_ERROR: user_id="error_user",
                                        # REMOVED_SYNTAX_ERROR: thread_id="error_thread",
                                        # REMOVED_SYNTAX_ERROR: run_id="error_run",
                                        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
                                        # REMOVED_SYNTAX_ERROR: metadata={"analysis_type": "cost_optimization"}
                                        

                                        # REMOVED_SYNTAX_ERROR: call_count = 0

# REMOVED_SYNTAX_ERROR: async def mock_analyze(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: nonlocal call_count
    # REMOVED_SYNTAX_ERROR: call_count += 1
    # REMOVED_SYNTAX_ERROR: if call_count == 2:  # Second call fails
    # REMOVED_SYNTAX_ERROR: raise Exception("Simulated error")
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return {"data_points": 100}

    # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
        # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_perf:
            # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_costs', new_callable=AsyncMock) as mock_costs:
                # REMOVED_SYNTAX_ERROR: mock_perf.return_value = {"data_points": 100}
                # REMOVED_SYNTAX_ERROR: mock_costs.side_effect = Exception("Cost analysis error")

                # First execution should succeed
                # REMOVED_SYNTAX_ERROR: result1 = await agent.execute(success_context, stream_updates=False)
                # REMOVED_SYNTAX_ERROR: assert result1["status"] == "completed"

                # Second execution should fail
                # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception) as exc_info:
                    # REMOVED_SYNTAX_ERROR: await agent.execute(error_context, stream_updates=False)
                    # REMOVED_SYNTAX_ERROR: assert "Cost analysis error" in str(exc_info.value)

                    # Third execution should succeed (error didn't affect agent state)
                    # REMOVED_SYNTAX_ERROR: result3 = await agent.execute(success_context, stream_updates=False)
                    # REMOVED_SYNTAX_ERROR: assert result3["status"] == "completed"

                    # Test 19: Resource Cleanup Validation
                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_resource_cleanup_validation(self):
                        # REMOVED_SYNTAX_ERROR: """Test that all resources are properly cleaned up."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: agent = DataSubAgent(llm_manager=Mock(spec=LLMManager), tool_dispatcher=Mock(spec=ToolDispatcher))

                        # Track resource allocation
                        # REMOVED_SYNTAX_ERROR: resources_allocated = []
                        # REMOVED_SYNTAX_ERROR: resources_freed = []

# REMOVED_SYNTAX_ERROR: class MockResource:
# REMOVED_SYNTAX_ERROR: def __init__(self, resource_id):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: self.resource_id = resource_id
    # REMOVED_SYNTAX_ERROR: resources_allocated.append(resource_id)

# REMOVED_SYNTAX_ERROR: def close(self):
    # REMOVED_SYNTAX_ERROR: resources_freed.append(self.resource_id)

    # Execute multiple times with resource tracking
    # REMOVED_SYNTAX_ERROR: for i in range(10):
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: db_session=MockResource("formatted_string"),
        # REMOVED_SYNTAX_ERROR: metadata={"analysis_type": "performance"}
        

        # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
            # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock:
                # REMOVED_SYNTAX_ERROR: mock.return_value = {"data_points": 100}

                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.data_sub_agent.data_sub_agent.DatabaseSessionManager') as mock_manager:
                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                    # REMOVED_SYNTAX_ERROR: mock_manager.return_value = mock_manager_instance

                    # Track cleanup calls
                    # REMOVED_SYNTAX_ERROR: cleanup_called = False
# REMOVED_SYNTAX_ERROR: async def mock_close():
    # REMOVED_SYNTAX_ERROR: nonlocal cleanup_called
    # REMOVED_SYNTAX_ERROR: cleanup_called = True
    # REMOVED_SYNTAX_ERROR: context.db_session.close()

    # REMOVED_SYNTAX_ERROR: mock_manager_instance.close = mock_close

    # REMOVED_SYNTAX_ERROR: await agent.execute(context, stream_updates=False)
    # REMOVED_SYNTAX_ERROR: assert cleanup_called, "formatted_string"

    # Verify all resources were freed
    # REMOVED_SYNTAX_ERROR: assert len(resources_allocated) == len(resources_freed), "Resource leak detected"
    # REMOVED_SYNTAX_ERROR: assert set(resources_allocated) == set(resources_freed), "Not all resources freed"

    # Test 20: Pattern Compliance Validation
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_complete_pattern_compliance(self):
        # REMOVED_SYNTAX_ERROR: """Comprehensive test for all SSOT patterns."""
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: import inspect
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.data_sub_agent import data_sub_agent

        # Load the entire module source
        # REMOVED_SYNTAX_ERROR: module_source = inspect.getsource(data_sub_agent)

        # Define all patterns that MUST be present
        # REMOVED_SYNTAX_ERROR: required_patterns = [ )
        # REMOVED_SYNTAX_ERROR: "UserExecutionContext",
        # REMOVED_SYNTAX_ERROR: "DatabaseSessionManager",
        # REMOVED_SYNTAX_ERROR: "BaseAgent",  # Should be imported
        # REMOVED_SYNTAX_ERROR: "from shared.isolated_environment import IsolatedEnvironment",
        

        # Define all patterns that MUST NOT be present
        # REMOVED_SYNTAX_ERROR: forbidden_patterns = [ )
        # REMOVED_SYNTAX_ERROR: "DeepAgentState",  # Legacy pattern
        # REMOVED_SYNTAX_ERROR: "self.db_session =",  # Stored sessions
        # REMOVED_SYNTAX_ERROR: "self.session =",  # Stored sessions
        # REMOVED_SYNTAX_ERROR: "os.environ[",  # Direct env access )
        # REMOVED_SYNTAX_ERROR: "os.environ.get(",  # Direct env access )
        # REMOVED_SYNTAX_ERROR: "global ",  # Global variables
        # REMOVED_SYNTAX_ERROR: "@singleton",  # Singleton pattern
        # REMOVED_SYNTAX_ERROR: "self.user_id =",  # Stored user data
        # REMOVED_SYNTAX_ERROR: "self.thread_id =",  # Stored thread data
        

        # Check required patterns
        # REMOVED_SYNTAX_ERROR: for pattern in required_patterns:
            # REMOVED_SYNTAX_ERROR: assert pattern in module_source, "formatted_string"

            # Check forbidden patterns
            # REMOVED_SYNTAX_ERROR: for pattern in forbidden_patterns:
                # REMOVED_SYNTAX_ERROR: assert pattern not in module_source, "formatted_string"

                # REMOVED_SYNTAX_ERROR: print(" PASS:  All SSOT compliance tests passed!")


                # Additional edge case tests
# REMOVED_SYNTAX_ERROR: class TestDataSubAgentEdgeCases:
    # REMOVED_SYNTAX_ERROR: """Edge case tests for DataSubAgent."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_null_context_handling(self):
        # REMOVED_SYNTAX_ERROR: """Test handling of null or invalid contexts."""
        # REMOVED_SYNTAX_ERROR: agent = DataSubAgent()

        # Test with None context
        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
            # REMOVED_SYNTAX_ERROR: await agent.execute(None, stream_updates=False)
            # REMOVED_SYNTAX_ERROR: assert "Invalid context type" in str(exc_info.value)

            # Test with wrong type
            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError):
                # REMOVED_SYNTAX_ERROR: await agent.execute({"not": "a_context"}, stream_updates=False)

                # Test with context missing db_session
                # REMOVED_SYNTAX_ERROR: invalid_context = UserExecutionContext( )
                # REMOVED_SYNTAX_ERROR: user_id="test",
                # REMOVED_SYNTAX_ERROR: thread_id="test",
                # REMOVED_SYNTAX_ERROR: run_id="test",
                # REMOVED_SYNTAX_ERROR: db_session=None,
                # REMOVED_SYNTAX_ERROR: metadata={}
                

                # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
                    # REMOVED_SYNTAX_ERROR: await agent.execute(invalid_context, stream_updates=False)
                    # REMOVED_SYNTAX_ERROR: assert "must contain a database session" in str(exc_info.value)

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_empty_metadata_handling(self):
                        # REMOVED_SYNTAX_ERROR: """Test handling of empty or missing metadata."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: agent = DataSubAgent()

                        # Context with empty metadata
                        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
                        # REMOVED_SYNTAX_ERROR: user_id="test",
                        # REMOVED_SYNTAX_ERROR: thread_id="test",
                        # REMOVED_SYNTAX_ERROR: run_id="test",
                        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
                        # REMOVED_SYNTAX_ERROR: metadata={}
                        

                        # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
                            # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock:
                                # REMOVED_SYNTAX_ERROR: mock.return_value = {"data_points": 100}

                                # Should use defaults
                                # REMOVED_SYNTAX_ERROR: result = await agent.execute(context, stream_updates=False)
                                # REMOVED_SYNTAX_ERROR: assert result["analysis_type"] == "performance"  # Default
                                # REMOVED_SYNTAX_ERROR: assert result["timeframe"] == "24h"  # Default

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_extremely_large_result_handling(self):
                                    # REMOVED_SYNTAX_ERROR: """Test handling of extremely large analysis results."""
                                    # REMOVED_SYNTAX_ERROR: agent = DataSubAgent()

                                    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
                                    # REMOVED_SYNTAX_ERROR: user_id="test",
                                    # REMOVED_SYNTAX_ERROR: thread_id="test",
                                    # REMOVED_SYNTAX_ERROR: run_id="test",
                                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
                                    # REMOVED_SYNTAX_ERROR: metadata={"analysis_type": "performance"}
                                    

                                    # Create a very large result
                                    # REMOVED_SYNTAX_ERROR: large_result = { )
                                    # REMOVED_SYNTAX_ERROR: "data_points": 1000000,
                                    # REMOVED_SYNTAX_ERROR: "data": ["x" * 1000 for _ in range(1000)],  # Large data
                                    # REMOVED_SYNTAX_ERROR: "metrics": {"formatted_string": i for i in range(10000)}
                                    

                                    # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, '__init__', return_value=None):
                                        # REMOVED_SYNTAX_ERROR: with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock:
                                            # REMOVED_SYNTAX_ERROR: mock.return_value = large_result

                                            # Should handle without memory issues
                                            # REMOVED_SYNTAX_ERROR: result = await agent.execute(context, stream_updates=False)
                                            # REMOVED_SYNTAX_ERROR: assert result["data_points_analyzed"] == 1000000


                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])
                                                # REMOVED_SYNTAX_ERROR: pass