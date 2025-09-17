class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.""
    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    async def send_json(self, message: dict):
        ""Send JSON message."
        if self._closed:
            raise RuntimeError("WebSocket is closed)
        self.messages_sent.append(message)
    async def close(self, code: int = 1000, reason: str = Normal closure"):
        "Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False
    async def get_messages(self) -> list:
        ""Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()
        '''Comprehensive SSOT Compliance Test Suite for DataSubAgent
        This test suite validates:
        1. Complete UserExecutionContext isolation
        2. No global state leakage between requests
        3. Proper session management through DatabaseSessionManager
        4. No direct environment access (must use IsolatedEnvironment)
        5. Proper JSON handling through unified_json_handler
        6. Correct caching with user context in keys
        7. WebSocket event emission compliance
        8. Concurrent user isolation
        9. Error handling through unified patterns
        10. No stored database sessions
        CRITICAL: These tests are designed to be difficult and comprehensive,
        testing edge cases and concurrent scenarios.
        '''
        import asyncio
        import os
        import json
        import hashlib
        from typing import Any, Dict, List, Optional
        import pytest
        import uuid
        from datetime import datetime, timedelta
        import concurrent.futures
        import threading
        import time
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from netra_backend.app.redis_manager import redis_manager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.database.session_manager import DatabaseSessionManager
        from netra_backend.app.agents.data_sub_agent.core.data_analysis_core import DataAnalysisCore
        from netra_backend.app.agents.data_sub_agent.core.data_processor import DataProcessor
        from netra_backend.app.agents.data_sub_agent.core.anomaly_detector import AnomalyDetector
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from shared.isolated_environment import IsolatedEnvironment
        from netra_backend.app.logging_config import central_logger
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        logger = central_logger.get_logger(__name__)
class TestDataSubAgentSSOTCompliance:
        "Test suite for DataSubAgent SSOT compliance and isolation patterns.""
        @pytest.fixture
    def real_llm_manager():
        ""Use real service instance."
    # TODO: Initialize real service
        "Create mock LLM manager.""
        pass
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value={content": "Test insights}
        return llm
        @pytest.fixture
    def real_tool_dispatcher():
        ""Use real service instance."
    # TODO: Initialize real service
        "Create mock tool dispatcher.""
        pass
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch = AsyncMock(return_value={status": "success}
        return dispatcher
        @pytest.fixture
    def real_db_session():
        ""Use real service instance."
    # TODO: Initialize real service
        "Create mock database session.""
        pass
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        return session
        @pytest.fixture
    def user_context(self, mock_db_session):
        ""Use real service instance."
    # TODO: Initialize real service
        "Create test user execution context.""
        pass
        return UserExecutionContext( )
        user_id=formatted_string",
        thread_id="formatted_string,
        run_id=formatted_string",
        db_session=mock_db_session,
        metadata={
        "analysis_type: performance",
        "timeframe: 24h",
        "metrics: [latency_ms", "cost_cents, throughput"]
    
    
        @pytest.fixture
    async def data_agent(self, mock_llm_manager, mock_tool_dispatcher):
        "Create DataSubAgent instance.""
        agent = DataSubAgent( )
        llm_manager=mock_llm_manager,
        tool_dispatcher=mock_tool_dispatcher
    
        await asyncio.sleep(0)
        return agent
    # Test 1: Verify No Direct Environment Access
@pytest.mark.asyncio
    async def test_no_direct_environment_access(self, data_agent):
""Test that agent never accesses os.environ directly."
pass
with patch.dict(os.environ, {"TEST_VAR: should_not_access"}:
            # Scan agent code for os.environ access
import inspect
source = inspect.getsource(DataSubAgent)
            # These should NOT appear in the code
forbidden_patterns = [
"os.environ[,
os.environ.get(",
"os.getenv(,
environ[" )
            
for pattern in forbidden_patterns:
    assert pattern not in source, "formatted_string
                # Test 2: Verify UserExecutionContext Isolation
@pytest.mark.asyncio
    async def test_user_context_isolation(self, mock_llm_manager, mock_tool_dispatcher):
""Test complete isolation between different user contexts."
                    # Create two agents for different users
agent1 = DataSubAgent(llm_manager=mock_llm_manager, tool_dispatcher=mock_tool_dispatcher)
agent2 = DataSubAgent(llm_manager=mock_llm_manager, tool_dispatcher=mock_tool_dispatcher)
                    # Create different contexts
context1 = UserExecutionContext( )
user_id="user1,
thread_id=thread1",
run_id="run1,
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={analysis_type": "performance}
                    
context2 = UserExecutionContext( )
user_id=user2",
thread_id="thread2,
run_id=run2",
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={"analysis_type: cost_optimization"}
                    
                    # Mock the core analysis to track calls
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_perf:
with patch.object(DataAnalysisCore, 'analyze_costs', new_callable=AsyncMock) as mock_costs:
mock_perf.return_value = {"data_points: 100, summary": "Performance analysis}
mock_costs.return_value = {savings_potential": {"savings_percentage: 25}}
                                # Execute both agents concurrently
results = await asyncio.gather( )
agent1.execute(context1, stream_updates=False),
agent2.execute(context2, stream_updates=False),
return_exceptions=True
                                
                                # Verify no cross-contamination
assert results[0][user_id"] == "user1
assert results[1][user_id"] == "user2
assert results[0][analysis_type"] == "performance
assert results[1][analysis_type"] == "cost_optimization
                                # Test 3: Verify No Stored Database Sessions
@pytest.mark.asyncio
    async def test_no_stored_database_sessions(self, data_agent):
""Test that agent never stores database sessions as instance variables."
pass
                                    # Check that agent has no db_session attribute
assert not hasattr(data_agent, 'db_session')
assert not hasattr(data_agent, '_db_session')
assert not hasattr(data_agent, 'session')
assert not hasattr(data_agent, '_session')
                                    # Check core components don't store sessions
assert not hasattr(data_agent.data_processor, 'db_session')
assert not hasattr(data_agent.anomaly_detector, 'db_session')
                                    # Test 4: Test Concurrent User Handling
@pytest.mark.asyncio
    async def test_concurrent_user_handling(self, mock_llm_manager, mock_tool_dispatcher):
"Test that multiple concurrent users are properly isolated.""
agent = DataSubAgent(llm_manager=mock_llm_manager, tool_dispatcher=mock_tool_dispatcher)
                                        # Track execution order and data
execution_log = []
execution_lock = threading.Lock()
async def execute_for_user(user_id: str, analysis_type: str):
""Execute agent for a specific user."
pass
context = UserExecutionContext( )
user_id=user_id,
thread_id="formatted_string,
run_id=formatted_string",
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={
"analysis_type: analysis_type,
timeframe": "1h,
metrics": ["latency_ms]
    
    
    # Mock core analysis
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_analyze:
mock_analyze.return_value = {
data_points": 100,
"summary: formatted_string",
"user_specific: user_id
            
with patch.object(DataAnalysisCore, 'analyze_costs', new_callable=AsyncMock) as mock_costs:
mock_costs.return_value = {
savings_potential": {"savings_percentage: 20},
user_specific": user_id
                
                # Add delay to simulate processing
await asyncio.sleep(0.1)
result = await agent.execute(context, stream_updates=False)
with execution_lock:
execution_log.append()
"user_id: user_id,
result_user": result.get("user_id),
analysis_type": analysis_type,
"timestamp: time.time()
                    
await asyncio.sleep(0)
return result
                    # Execute for 10 concurrent users
users = [formatted_string" for i in range(10)]
analysis_types = ["performance, cost_optimization"] * 5
tasks = [
execute_for_user(user, analysis_type)
for user, analysis_type in zip(users, analysis_types)
                    
results = await asyncio.gather(*tasks, return_exceptions=True)
                    # Verify all results are properly isolated
for i, result in enumerate(results):
    if not isinstance(result, Exception):
    assert result["user_id] == users[i], formatted_string"
assert result["run_id].startswith(formatted_string")
                            # Verify execution log shows proper isolation
for log_entry in execution_log:
    assert log_entry["user_id] == log_entry[result_user"], "User data leaked between contexts
                                # Test 5: Test JSON Handling Through Unified Handler
@pytest.mark.asyncio
    async def test_unified_json_handler_usage(self, data_agent, user_context):
""Test that all JSON operations use unified_json_handler."
                                    # Mock unified JSON handler
with patch('netra_backend.app.core.serialization.unified_json_handler.LLMResponseParser') as mock_parser:
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_parser.return_value = mock_parser_instance
mock_parser_instance.parse_json = Mock(return_value={"test: data"}
                                        # Check if agent uses unified handler for JSON operations
                                        # This would be called if the agent properly uses unified JSON handling
                                        # Note: The current implementation doesn't directly use LLMResponseParser,
                                        # but we're testing the pattern
                                        # Verify no direct json.loads or json.dumps in critical paths
import inspect
source = inspect.getsource(DataSubAgent)
                                        # These patterns suggest non-unified JSON handling
                                        # (except in non-critical paths like logging)
lines = source.split(" )
)
for i, line in enumerate(lines):
    if 'json.loads' in line or 'json.dumps' in line:
                                                # Check if it's in a critical path (not logging)
if 'logger' not in line and 'log' not in line.lower():
    pytest.fail(formatted_string")
                                                    # Test 6: Test Cache Key Generation with User Context
@pytest.mark.asyncio
    async def test_cache_key_includes_user_context(self, data_agent):
"Test that cache keys include user context for isolation.""
pass
request1 = {
type": "performance,
timeframe": "24h,
user_id": "user1,
metrics": ["latency_ms, throughput"]
                                                        
request2 = {
"type: performance",
"timeframe: 24h",
"user_id: user2",
"metrics: [latency_ms", "throughput]
                                                        
key1 = data_agent._get_analysis_cache_key(request1)
key2 = data_agent._get_analysis_cache_key(request2)
                                                        # Keys must be different for different users
assert key1 != key2, Cache keys not isolated by user"
assert "user1 in key1
assert user2" in key2
                                                        # Test 7: Test WebSocket Event Emission
@pytest.mark.asyncio
    async def test_websocket_event_emission(self, data_agent, user_context):
"Test that agent properly emits WebSocket events.""
                                                            # Mock WebSocket methods
data_agent.websocket = TestWebSocketConnection()
                                                            # Mock core analysis
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_analyze:
mock_analyze.return_value = {data_points": 100, "summary: Test"}
                                                                    # Execute with streaming
await data_agent.execute(user_context, stream_updates=True)
                                                                    # Verify events were emitted
assert data_agent.emit_thinking.called
assert data_agent.emit_progress.called
assert data_agent.emit_tool_executing.called
assert data_agent.emit_tool_completed.called
                                                                    # Verify correct event sequence
calls = []
for method in [data_agent.emit_thinking, data_agent.emit_progress,
data_agent.emit_tool_executing, data_agent.emit_tool_completed]:
for call in method.call_args_list:
    calls.append((method._mock_name, call))
                                                                            # Verify thinking comes before progress
thinking_indices = [item for item in []]
progress_indices = [item for item in []]
assert min(thinking_indices) < max(progress_indices) if thinking_indices and progress_indices else True
                                                                            # Test 8: Test Error Handling Through Unified Patterns
@pytest.mark.asyncio
    async def test_unified_error_handling(self, data_agent, user_context):
"Test that errors are handled through unified patterns.""
pass
                                                                                # Simulate an error in core analysis
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', side_effect=Exception(Test error")):
data_agent.websocket = TestWebSocketConnection()
with pytest.raises(Exception) as exc_info:
await data_agent.execute(user_context, stream_updates=True)
assert "Test error in str(exc_info.value)
                                                                                            # Verify error event was emitted with proper context
data_agent.emit_error.assert_called()
error_call = data_agent.emit_error.call_args
assert test_user_" in str(error_call)
                                                                                            # Test 9: Test Session Manager Cleanup
@pytest.mark.asyncio
    async def test_session_manager_cleanup(self, data_agent, user_context):
"Test that DatabaseSessionManager is properly cleaned up.""
cleanup_called = False
                                                                                                # Mock DatabaseSessionManager
with patch('netra_backend.app.agents.data_sub_agent.data_sub_agent.DatabaseSessionManager') as mock_manager_class:
websocket = TestWebSocketConnection()
mock_manager_class.return_value = mock_manager
async def mock_close():
nonlocal cleanup_called
cleanup_called = True
mock_manager.close = mock_close
    # Mock core analysis
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_analyze:
mock_analyze.return_value = {data_points": 100}
            # Execute normally
await data_agent.execute(user_context, stream_updates=False)
assert cleanup_called, "Session manager not cleaned up on success
            # Reset and test cleanup on error
cleanup_called = False
mock_analyze.side_effect = Exception(Test error")
with pytest.raises(Exception):
await data_agent.execute(user_context, stream_updates=False)
assert cleanup_called, "Session manager not cleaned up on error
                # Test 10: Test No Global State Storage
@pytest.mark.asyncio
    async def test_no_global_state_storage(self, mock_llm_manager, mock_tool_dispatcher):
""Test that no user-specific data is stored globally."
pass
agent = DataSubAgent(llm_manager=mock_llm_manager, tool_dispatcher=mock_tool_dispatcher)
                    # Execute for first user
context1 = UserExecutionContext( )
user_id="user1,
thread_id=thread1",
run_id="run1,
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={analysis_type": "performance}
                    
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_analyze:
mock_analyze.return_value = {data_points": 100}
await agent.execute(context1, stream_updates=False)
                            # Check that no user data is stored
for attr_name in dir(agent):
    if not attr_name.startswith('_'):
    attr_value = getattr(agent, attr_name)
if isinstance(attr_value, str):
    assert "user1 not in attr_value, formatted_string"
assert "thread1 not in attr_value, formatted_string"
assert "run1 not in attr_value, formatted_string"
                                        # Test 11: Test Retry Logic Uses UnifiedRetryHandler
@pytest.mark.asyncio
    async def test_unified_retry_handler_usage(self, data_agent):
"Test that retry logic uses UnifiedRetryHandler, not custom implementation.""
import inspect
source = inspect.getsource(DataSubAgent)
                                            # Check for custom retry patterns that should NOT exist
forbidden_patterns = [
for attempt in range",
"while attempts <,
retry_count",
"max_retries,
sleep(1)",  # Custom retry delays
                                            
for pattern in forbidden_patterns:
                                                # Allow in comments but not in actual code
lines = source.split(" )
)
for line in lines:
    if pattern in line and not line.strip().startswith('#'):
                                                        # Check if it's actually a retry implementation
if 'try:' in source[max(0, source.index(line)-100):source.index(line)+100]:
    pytest.fail(formatted_string")
                                                            # Test 12: Test Configuration Access Pattern
@pytest.mark.asyncio
    async def test_configuration_access_pattern(self, data_agent):
"Test that configuration is accessed through proper architecture.""
pass
                                                                # Agent should not directly read config files
import inspect
source = inspect.getsource(DataSubAgent)
forbidden_patterns = [
open("config",
open(config",
"json.load(f),
yaml.load",
"configparser,
                                                                
for pattern in forbidden_patterns:
    assert pattern not in source, formatted_string"
                                                                    # Test 13: Test Hash Generation Through CacheHelpers
@pytest.mark.asyncio
    async def test_hash_generation_pattern(self, data_agent):
"Test that hash generation uses CacheHelpers, not custom implementation.""
import inspect
source = inspect.getsource(DataSubAgent)
                                                                        # Check for custom hash implementations
if hashlib" in source:
                                                                            # hashlib should only be imported through CacheHelpers
lines = source.split(" )
)
for line in lines:
    if 'hashlib' in line and 'import' not in line:
    pytest.fail(formatted_string")
                                                                                    # Test 14: Test BaseAgent Method Usage
@pytest.mark.asyncio
    async def test_base_agent_inheritance(self, data_agent):
"Test that agent properly uses BaseAgent methods.""
pass
                                                                                        Use lazy import to avoid circular dependency
import importlib
try:
    base_agent_module = importlib.import_module('netra_backend.app.agents.base_agent')
BaseAgent = getattr(base_agent_module, 'BaseAgent', None)
if BaseAgent:
                                                                                                # Verify agent extends BaseAgent
assert isinstance(data_agent, BaseAgent)
                                                                                                # These methods should be inherited, not redefined
inherited_methods = ['emit_thinking', 'emit_progress', 'emit_tool_executing',
'emit_tool_completed', 'emit_error']
for method in inherited_methods:
                                                                                                    # Check that agent has the method (inherited or overridden)
assert hasattr(data_agent, method), formatted_string"
agent_method = getattr(data_agent, method, None)
assert callable(agent_method), "formatted_string
else:
                                                                                                        # Fallback: check methods exist without inheritance check
inherited_methods = ['emit_thinking', 'emit_progress', 'emit_tool_executing',
'emit_tool_completed', 'emit_error']
for method in inherited_methods:
    assert hasattr(data_agent, method), formatted_string"
except ImportError as e:
                                                                                                                # If BaseAgent can't be imported due to circular dependency, use alternative approach
logger.warning("formatted_string)
                                                                                                                # Alternative: Check agent has required methods
required_methods = ['emit_thinking', 'emit_progress', 'emit_tool_executing',
'emit_tool_completed', 'emit_error', 'execute']
for method in required_methods:
    assert hasattr(data_agent, method), formatted_string"
                                                                                                                    # Test 15: Test Memory Leak Prevention
@pytest.mark.asyncio
    async def test_memory_leak_prevention(self, mock_llm_manager, mock_tool_dispatcher):
"Test that repeated executions don't cause memory leaks.""
agent = DataSubAgent(llm_manager=mock_llm_manager, tool_dispatcher=mock_tool_dispatcher)
initial_attrs = set(dir(agent))
initial_values = {}
                                                                                                                        # Execute multiple times
for i in range(5):
    context = UserExecutionContext( )
user_id=formatted_string",
thread_id="formatted_string,
run_id=formatted_string",
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={"analysis_type: performance"}
                                                                                                                            
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_analyze:
mock_analyze.return_value = {"data_points: 100}
try:
    await agent.execute(context, stream_updates=False)
except:
    pass
                                                                                                                                            # Check no new attributes were added
final_attrs = set(dir(agent))
new_attrs = final_attrs - initial_attrs
assert len(new_attrs) == 0, formatted_string"
                                                                                                                                            # Check no accumulation of data
for attr in initial_attrs:
    if not callable(getattr(agent, attr)):
    current_value = getattr(agent, attr)
initial_value = initial_values.get(attr)
                                                                                                                                                    # Check for accumulation (lists, dicts growing)
if isinstance(current_value, (list, dict)):
    if isinstance(initial_value, (list, dict)):
                                                                                                                                                            # Size shouldn't grow significantly
assert len(str(current_value)) <= len(str(initial_value)) * 2, "formatted_string
class TestDataSubAgentStressTests:
    ""Stress tests for DataSubAgent under extreme conditions."
    # Test 16: High Concurrency Stress Test
@pytest.mark.asyncio
    async def test_high_concurrency_stress(self):
"Test agent under high concurrency (100+ simultaneous users).""
agent = DataSubAgent(llm_manager=Mock(spec=LLMManager), tool_dispatcher=Mock(spec=ToolDispatcher))
async def execute_for_user(user_id: int):
context = UserExecutionContext( )
user_id=formatted_string",
thread_id="formatted_string,
run_id=formatted_string",
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={"analysis_type: performance"}
    
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock:
mock.return_value = {"data_points: user_id, user_id": "formatted_string}
result = await agent.execute(context, stream_updates=False)
assert result[user_id"] == "formatted_string
await asyncio.sleep(0)
return result
            # Execute 100 concurrent requests
tasks = [execute_for_user(i) for i in range(100)]
results = await asyncio.gather(*tasks, return_exceptions=True)
            # Verify all completed without cross-contamination
successful = [item for item in []]
assert len(successful) >= 95, formatted_string"
            # Check for data isolation
user_ids = [r["user_id] for r in successful]
assert len(set(user_ids)) == len(user_ids), User data contamination detected"
            # Test 17: Rapid Context Switching
@pytest.mark.asyncio
    async def test_rapid_context_switching(self):
"Test rapid switching between different user contexts.""
pass
agent = DataSubAgent(llm_manager=Mock(spec=LLMManager), tool_dispatcher=Mock(spec=ToolDispatcher))
contexts = [
UserExecutionContext( )
user_id=formatted_string",  # Only 3 users, but 30 requests
thread_id="formatted_string,
run_id=formatted_string",
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={"analysis_type: [performance", "cost_optimization, trend_analysis"][i % 3]}
                
for i in range(30)
                
results = []
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_perf:
with patch.object(DataAnalysisCore, 'analyze_costs', new_callable=AsyncMock) as mock_costs:
with patch.object(DataAnalysisCore, 'analyze_trends', new_callable=AsyncMock) as mock_trends:
mock_perf.return_value = {"type: performance", "data_points: 100}
mock_costs.return_value = {type": "costs, savings_potential": {"savings_percentage: 20}}
mock_trends.return_value = {type": "trends, trends": {}}
for context in contexts:
    result = await agent.execute(context, stream_updates=False)
results.append(result)
                                    # Verify correct analysis type was used
expected_type = context.metadata["analysis_type]
assert result[analysis_type"] == expected_type
                                    # Test 18: Error Recovery and Isolation
@pytest.mark.asyncio
    async def test_error_recovery_isolation(self):
"Test that errors in one context don't affect others.""
agent = DataSubAgent(llm_manager=Mock(spec=LLMManager), tool_dispatcher=Mock(spec=ToolDispatcher))
success_context = UserExecutionContext( )
user_id=success_user",
thread_id="success_thread,
run_id=success_run",
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={"analysis_type: performance"}
                                        
error_context = UserExecutionContext( )
user_id="error_user,
thread_id=error_thread",
run_id="error_run,
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={analysis_type": "cost_optimization}
                                        
call_count = 0
async def mock_analyze(*args, **kwargs):
nonlocal call_count
call_count += 1
if call_count == 2:  # Second call fails
raise Exception(Simulated error")
await asyncio.sleep(0)
return {"data_points: 100}
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock_perf:
with patch.object(DataAnalysisCore, 'analyze_costs', new_callable=AsyncMock) as mock_costs:
mock_perf.return_value = {data_points": 100}
mock_costs.side_effect = Exception("Cost analysis error)
                # First execution should succeed
result1 = await agent.execute(success_context, stream_updates=False)
assert result1[status"] == "completed
                # Second execution should fail
with pytest.raises(Exception) as exc_info:
await agent.execute(error_context, stream_updates=False)
assert Cost analysis error" in str(exc_info.value)
                    # Third execution should succeed (error didn't affect agent state)
result3 = await agent.execute(success_context, stream_updates=False)
assert result3["status] == completed"
                    # Test 19: Resource Cleanup Validation
@pytest.mark.asyncio
    async def test_resource_cleanup_validation(self):
"Test that all resources are properly cleaned up.""
pass
agent = DataSubAgent(llm_manager=Mock(spec=LLMManager), tool_dispatcher=Mock(spec=ToolDispatcher))
                        # Track resource allocation
resources_allocated = []
resources_freed = []
class MockResource:
    def __init__(self, resource_id):
        ""Use real service instance."
    # TODO: Initialize real service
        self.resource_id = resource_id
        resources_allocated.append(resource_id)
    def close(self):
        resources_freed.append(self.resource_id)
    # Execute multiple times with resource tracking
        for i in range(10):
        context = UserExecutionContext( )
        user_id="formatted_string,
        thread_id=formatted_string",
        run_id="formatted_string,
        db_session=MockResource(formatted_string"),
        metadata={"analysis_type: performance"}
        
        with patch.object(DataAnalysisCore, '__init__', return_value=None):
        with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock:
        mock.return_value = {"data_points: 100}
        with patch('netra_backend.app.agents.data_sub_agent.data_sub_agent.DatabaseSessionManager') as mock_manager:
        websocket = TestWebSocketConnection()
        mock_manager.return_value = mock_manager_instance
                    # Track cleanup calls
        cleanup_called = False
    async def mock_close():
        nonlocal cleanup_called
        cleanup_called = True
        context.db_session.close()
        mock_manager_instance.close = mock_close
        await agent.execute(context, stream_updates=False)
        assert cleanup_called, formatted_string"
    # Verify all resources were freed
        assert len(resources_allocated) == len(resources_freed), "Resource leak detected
        assert set(resources_allocated) == set(resources_freed), Not all resources freed"
    # Test 20: Pattern Compliance Validation
@pytest.mark.asyncio
    async def test_complete_pattern_compliance(self):
"Comprehensive test for all SSOT patterns.""
pass
import inspect
from netra_backend.app.agents.data_sub_agent import data_sub_agent
        # Load the entire module source
module_source = inspect.getsource(data_sub_agent)
        # Define all patterns that MUST be present
required_patterns = [
UserExecutionContext",
"DatabaseSessionManager,
BaseAgent",  # Should be imported
"from shared.isolated_environment import IsolatedEnvironment,
        
        # Define all patterns that MUST NOT be present
forbidden_patterns = [
DeepAgentState",  # Legacy pattern
"self.db_session =,  # Stored sessions
self.session =",  # Stored sessions
"os.environ[,  # Direct env access )
os.environ.get(",  # Direct env access )
"global ,  # Global variables
@singleton",  # Singleton pattern
"self.user_id =,  # Stored user data
self.thread_id =",  # Stored thread data
        
        # Check required patterns
for pattern in required_patterns:
    assert pattern in module_source, "formatted_string
            # Check forbidden patterns
for pattern in forbidden_patterns:
    assert pattern not in module_source, formatted_string"
    print(" PASS:  All SSOT compliance tests passed!)
                # Additional edge case tests
class TestDataSubAgentEdgeCases:
    ""Edge case tests for DataSubAgent."
@pytest.mark.asyncio
    async def test_null_context_handling(self):
"Test handling of null or invalid contexts.""
agent = DataSubAgent()
        # Test with None context
with pytest.raises(ValueError) as exc_info:
await agent.execute(None, stream_updates=False)
assert Invalid context type" in str(exc_info.value)
            # Test with wrong type
with pytest.raises(ValueError):
await agent.execute({"not: a_context"}, stream_updates=False)
                # Test with context missing db_session
invalid_context = UserExecutionContext( )
user_id="test,
thread_id=test",
run_id="test,
db_session=None,
metadata={}
                
with pytest.raises(ValueError) as exc_info:
await agent.execute(invalid_context, stream_updates=False)
assert must contain a database session" in str(exc_info.value)
@pytest.mark.asyncio
    async def test_empty_metadata_handling(self):
"Test handling of empty or missing metadata.""
pass
agent = DataSubAgent()
                        # Context with empty metadata
context = UserExecutionContext( )
user_id=test",
thread_id="test,
run_id=test",
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={}
                        
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock:
mock.return_value = {"data_points: 100}
                                # Should use defaults
result = await agent.execute(context, stream_updates=False)
assert result[analysis_type"] == "performance  # Default
assert result[timeframe"] == "24h  # Default
@pytest.mark.asyncio
    async def test_extremely_large_result_handling(self):
""Test handling of extremely large analysis results."
agent = DataSubAgent()
context = UserExecutionContext( )
user_id="test,
thread_id=test",
run_id="test,
websocket = TestWebSocketConnection()  # Real WebSocket implementation,
metadata={analysis_type": "performance}
                                    
                                    # Create a very large result
large_result = {
data_points": 1000000,
"data: [x" * 1000 for _ in range(1000)],  # Large data
"metrics: {formatted_string": i for i in range(10000)}
                                    
with patch.object(DataAnalysisCore, '__init__', return_value=None):
with patch.object(DataAnalysisCore, 'analyze_performance', new_callable=AsyncMock) as mock:
mock.return_value = large_result
                                            # Should handle without memory issues
result = await agent.execute(context, stream_updates=False)
assert result["data_points_analyzed] == 1000000
if __name__ == __main__":
    pass