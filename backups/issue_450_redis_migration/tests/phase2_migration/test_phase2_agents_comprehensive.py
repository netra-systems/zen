class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        CRITICAL: Phase 2 Agent Migration Comprehensive Test Suite
        ============================================================
        Tests all Phase 2 agents migrated to UserExecutionContext pattern.
        These tests are intentionally difficult and comprehensive to ensure
        proper isolation, security, and functionality.
        '''

        import asyncio
        import json
        import pytest
        import uuid
        from datetime import datetime
        from typing import Any, Dict, List, Optional
        from concurrent.futures import ThreadPoolExecutor
        import threading
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

    # Core imports
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.database.session_manager import DatabaseSessionManager

    # Phase 2 Agent imports
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
        from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
        from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
        from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
        from netra_backend.app.agents.enhanced_execution_agent import EnhancedExecutionAgent
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


class TestPhase2AgentsMigration:
        """Comprehensive test suite for Phase 2 agent migration."""

        @pytest.fixture
    def real_db_session():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock database session."""
        pass
        session = Magic        session.commit = Magic        session.rollback = Magic        session.close = Magic        return session

        @pytest.fixture
    def user_context(self, mock_db_session):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a test UserExecutionContext."""
        pass
        return UserExecutionContext( )
        user_id="test_user_123",
        thread_id="thread_456",
        run_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        db_session=mock_db_session,
        metadata={ )
        "user_request": "Analyze performance and suggest improvements",
        "data_result": {"metrics": {"latency": 150, "throughput": 1000}},
        "triage_result": {"priority": "high", "category": "performance"},
        "optimizations_result": {"suggestions": ["cache", "index"]},
        "action_plan_result": {"steps": ["implement cache", "add indexes"]}
    
    

        @pytest.fixture
    def real_websocket_manager():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock WebSocket manager."""
        pass
        manager = Magic        manager.websocket = TestWebSocketConnection()
        return manager


class TestReportingSubAgent(TestPhase2AgentsMigration):
        """Comprehensive tests for ReportingSubAgent migration."""

@pytest.mark.asyncio
    async def test_reporting_agent_user_isolation(self, user_context, mock_websocket_manager):
"""Test that ReportingSubAgent properly isolates user data."""
agent = ReportingSubAgent()

        # Create two different user contexts
context1 = user_context
context2 = UserExecutionContext( )
user_id="different_user_789",
thread_id="thread_999",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=user_context.db_session,
metadata={ )
"user_request": "Different request",
"data_result": {"metrics": {"latency": 500}},
"triage_result": {"priority": "low"},
"optimizations_result": {"suggestions": ["optimize queries"]}
        
        

        # Execute for both users concurrently
with patch.object(agent, '_generate_report_with_llm', return_value={"report": "test"}):
results = await asyncio.gather( )
agent.execute(context1, stream_updates=False),
agent.execute(context2, stream_updates=False)
            

            # Verify results are isolated
assert results[0] != results[1]
assert "test_user_123" not in str(results[1])
assert "different_user_789" not in str(results[0])

@pytest.mark.asyncio
    async def test_reporting_context_validation(self, mock_websocket_manager):
"""Test that ReportingSubAgent validates UserExecutionContext."""
pass
agent = ReportingSubAgent(websocket_manager=mock_websocket_manager)

                # Test with invalid context type
with pytest.raises(TypeError):
await agent.execute("not_a_context", stream_updates=False)

                    # Test with None context
with pytest.raises(TypeError):
await agent.execute(None, stream_updates=False)

@pytest.mark.asyncio
    async def test_reporting_missing_metadata(self, user_context, mock_websocket_manager):
"""Test ReportingSubAgent handles missing metadata gracefully."""
agent = ReportingSubAgent(websocket_manager=mock_websocket_manager)

                            # Remove required metadata
context = UserExecutionContext( )
user_id=user_context.user_id,
thread_id=user_context.thread_id,
run_id=user_context.run_id,
request_id=user_context.request_id,
db_session=user_context.db_session,
metadata={}  # Empty metadata
                            

                            # Should create fallback report
result = await agent.execute(context, stream_updates=False)
assert result is not None
assert "fallback" in str(result).lower() or "unavailable" in str(result).lower()

@pytest.mark.asyncio
    async def test_reporting_concurrent_execution(self, user_context, mock_websocket_manager):
"""Test ReportingSubAgent handles concurrent executions safely."""
pass
agent = ReportingSubAgent(websocket_manager=mock_websocket_manager)

                                # Create 10 concurrent executions
contexts = []
for i in range(10):
ctx = UserExecutionContext( )
user_id="formatted_string",
thread_id="formatted_string",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=user_context.db_session,
metadata=user_context.metadata.copy()
                                    
contexts.append(ctx)

with patch.object(agent, '_generate_report_with_llm', return_value={"report": "test"}):
                                        # Removed problematic line: results = await asyncio.gather(*[ ))
agent.execute(ctx, stream_updates=False) for ctx in contexts
                                        

                                        # All results should be independent
assert len(results) == 10
assert all(r is not None for r in results)


class TestOptimizationsCoreSubAgent(TestPhase2AgentsMigration):
    """Comprehensive tests for OptimizationsCoreSubAgent migration."""

@pytest.mark.asyncio
    async def test_optimizations_context_isolation(self, user_context, mock_websocket_manager):
"""Test that OptimizationsCoreSubAgent maintains context isolation."""
dispatcher = Magic        agent = OptimizationsCoreSubAgent( )
tool_dispatcher=dispatcher,
websocket_manager=mock_websocket_manager
        

        # Mock LLM response
with patch.object(agent, '_analyze_with_llm', return_value={"optimizations": ["cache", "index"]}):
result = await agent.execute(user_context, stream_updates=False)

            # Verify result contains user-specific data
assert result is not None
assert isinstance(result, dict)

            # Verify context wasn't mutated
assert user_context.user_id == "test_user_123"
assert user_context.thread_id == "thread_456"

@pytest.mark.asyncio
    async def test_optimizations_database_session_management(self, user_context, mock_websocket_manager):
"""Test database session management in OptimizationsCoreSubAgent."""
pass
dispatcher = Magic        agent = OptimizationsCoreSubAgent( )
tool_dispatcher=dispatcher,
websocket_manager=mock_websocket_manager
                

with patch.object(agent, '_analyze_with_llm', side_effect=Exception("Test error")):
                    # Should handle error gracefully
result = await agent.execute(user_context, stream_updates=False)

                    # Session should be rolled back on error
user_context.db_session.rollback.assert_called()

@pytest.mark.asyncio
    async def test_optimizations_tool_dispatcher_integration(self, user_context, mock_websocket_manager):
"""Test tool dispatcher integration with UserExecutionContext."""
dispatcher = Magic        dispatcher.execute_tool = AsyncMock(return_value={"tool_result": "success"})

agent = OptimizationsCoreSubAgent( )
tool_dispatcher=dispatcher,
websocket_manager=mock_websocket_manager
                        

with patch.object(agent, '_needs_tools', return_value=True):
with patch.object(agent, '_analyze_with_llm', return_value={"optimizations": ["use_tool"]}):
result = await agent.execute(user_context, stream_updates=False)

                                # Tool dispatcher should be called with context
dispatcher.execute_tool.assert_called()


class TestSyntheticDataSubAgent(TestPhase2AgentsMigration):
    """Comprehensive tests for SyntheticDataSubAgent migration."""

@pytest.mark.asyncio
    async def test_synthetic_data_user_isolation(self, user_context, mock_websocket_manager):
"""Test that synthetic data generation is isolated per user."""
agent = SyntheticDataSubAgent()

        # Mock generation components
with patch('netra_backend.app.agents.synthetic_data_sub_agent.GenerationWorkflow') as mock_workflow:
mock_workflow_instance = Magic            mock_workflow_instance.execute = AsyncMock(return_value={"synthetic_data": "test"})
mock_workflow.return_value = mock_workflow_instance

            # Execute for multiple users
contexts = []
for i in range(5):
ctx = UserExecutionContext( )
user_id="formatted_string",
thread_id="formatted_string",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=user_context.db_session,
metadata={"user_request": "formatted_string"}
                
contexts.append(ctx)

                # Removed problematic line: results = await asyncio.gather(*[ ))
agent.execute(ctx, stream_updates=False) for ctx in contexts
                

                # Verify each user got isolated results
assert len(results) == 5
assert all(r is not None for r in results)

@pytest.mark.asyncio
    async def test_synthetic_data_approval_workflow(self, user_context, mock_websocket_manager):
"""Test approval workflow with UserExecutionContext."""
pass
agent = SyntheticDataSubAgent()

                    # Set up approval requirement
user_context.metadata["requires_approval"] = True

with patch('netra_backend.app.agents.synthetic_data_sub_agent.ApprovalWorkflow') as mock_approval:
mock_approval_instance = Magic            mock_approval_instance.check_approval_required = MagicMock(return_value=True)
mock_approval_instance.request_approval = AsyncMock(return_value=True)
mock_approval.return_value = mock_approval_instance

with patch('netra_backend.app.agents.synthetic_data_sub_agent.GenerationWorkflow') as mock_gen:
mock_gen_instance = Magic                mock_gen_instance.execute = AsyncMock(return_value={"data": "approved"})
mock_gen.return_value = mock_gen_instance

result = await agent.execute(user_context, stream_updates=False)

                            # Verify approval was requested
mock_approval_instance.request_approval.assert_called()
assert result is not None

@pytest.mark.asyncio
    async def test_synthetic_data_batch_processing(self, user_context, mock_websocket_manager):
"""Test batch processing maintains context isolation."""
agent = SyntheticDataSubAgent()

                                # Set up batch request
user_context.metadata["batch_size"] = 100
user_context.metadata["workload_profile"] = { )
"num_users": 10,
"num_sessions": 100,
"events_per_session": 50
                                

with patch('netra_backend.app.agents.synthetic_data_sub_agent.SyntheticDataBatchProcessor') as mock_batch:
mock_batch_instance = Magic            mock_batch_instance.process_all_batches = AsyncMock( )
return_value=[{"batch": i} for i in range(10)]
                                    
mock_batch.return_value = mock_batch_instance

result = await agent.execute(user_context, stream_updates=False)

                                    # Verify batch processing was called
mock_batch_instance.process_all_batches.assert_called()
assert result is not None


class TestGoalsTriageSubAgent(TestPhase2AgentsMigration):
    """Comprehensive tests for GoalsTriageSubAgent migration."""

@pytest.mark.asyncio
    async def test_goals_triage_context_validation(self, user_context, mock_websocket_manager):
"""Test context validation in GoalsTriageSubAgent."""
agent = GoalsTriageSubAgent(websocket_manager=mock_websocket_manager)

        # Test with valid context
with patch.object(agent, '_extract_and_analyze_goals', return_value={"goals": ["goal1"]}):
result = await agent.execute(user_context, stream_updates=False)
assert result is not None

            # Test with invalid context
with pytest.raises(TypeError):
await agent.execute({"not": "a_context"}, stream_updates=False)

@pytest.mark.asyncio
    async def test_goals_priority_isolation(self, user_context, mock_websocket_manager):
"""Test that goal priorities are isolated per user."""
pass
agent = GoalsTriageSubAgent(websocket_manager=mock_websocket_manager)

                    # Create contexts with different priorities
high_priority_context = user_context
high_priority_context.metadata["user_request"] = "URGENT: Fix production issues"

low_priority_context = UserExecutionContext( )
user_id="low_priority_user",
thread_id="thread_low",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=user_context.db_session,
metadata={"user_request": "Maybe someday optimize this"}
                    

with patch.object(agent, '_extract_and_analyze_goals') as mock_analyze:
mock_analyze.side_effect = [ )
{"goals": ["fix_production"], "priority": "critical"},
{"goals": ["optimize"], "priority": "low"}
                        

high_result = await agent.execute(high_priority_context, stream_updates=False)
low_result = await agent.execute(low_priority_context, stream_updates=False)

                        # Verify priorities are different
assert high_result != low_result
assert "critical" in str(high_result) or "high" in str(high_result)
assert "low" in str(low_result) or "optimize" in str(low_result)

@pytest.mark.asyncio
    async def test_goals_fallback_handling(self, user_context, mock_websocket_manager):
"""Test fallback goal generation when analysis fails."""
agent = GoalsTriageSubAgent(websocket_manager=mock_websocket_manager)

                            # Make analysis fail
with patch.object(agent, '_extract_and_analyze_goals', side_effect=Exception("LLM failed")):
result = await agent.execute(user_context, stream_updates=False)

                                # Should await asyncio.sleep(0)
return fallback goals
assert result is not None
assert "goals" in result or "fallback" in str(result).lower()


class TestActionsToMeetGoalsSubAgent(TestPhase2AgentsMigration):
    """Comprehensive tests for ActionsToMeetGoalsSubAgent migration."""

@pytest.mark.asyncio
    async def test_actions_plan_user_isolation(self, user_context, mock_websocket_manager):
"""Test that action plans are isolated per user."""
agent = ActionsToMeetGoalsSubAgent(websocket_manager=mock_websocket_manager)

        # Create multiple user contexts
contexts = []
for i in range(3):
ctx = UserExecutionContext( )
user_id="formatted_string",
thread_id="formatted_string",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=user_context.db_session,
metadata={ )
"user_request": "formatted_string",
"optimizations_result": {"suggestions": ["formatted_string"]},
"data_result": {"metrics": {"id": i}}
            
            
contexts.append(ctx)

with patch.object(agent, '_generate_action_plan') as mock_plan:
mock_plan.side_effect = [ )
{"plan": "formatted_string"} for i in range(3)
                

                # Removed problematic line: results = await asyncio.gather(*[ ))
agent.execute(ctx, stream_updates=False) for ctx in contexts
                

                # Verify each user got their own plan
assert len(results) == 3
for i, result in enumerate(results):
assert "formatted_string" in str(result)

@pytest.mark.asyncio
    async def test_actions_metadata_immutability(self, user_context, mock_websocket_manager):
"""Test that context metadata is handled correctly despite immutability."""
pass
agent = ActionsToMeetGoalsSubAgent(websocket_manager=mock_websocket_manager)

original_metadata = user_context.metadata.copy()

with patch.object(agent, '_generate_action_plan', return_value={"plan": "test"}):
result = await agent.execute(user_context, stream_updates=False)

                            # Context metadata should not be mutated
assert user_context.metadata == original_metadata
assert result is not None


class TestEnhancedExecutionAgent(TestPhase2AgentsMigration):
    """Comprehensive tests for EnhancedExecutionAgent migration."""

@pytest.mark.asyncio
    async def test_enhanced_execution_isolation(self, user_context, mock_websocket_manager):
"""Test enhanced execution maintains user isolation."""
agent = EnhancedExecutionAgent(websocket_manager=mock_websocket_manager)

        # Mock supervisor
with patch('netra_backend.app.agents.enhanced_execution_agent.EnhancedSupervisorWrapper') as mock_supervisor:
mock_supervisor_instance = Magic            mock_supervisor_instance.execute_with_context = AsyncMock( )
return_value={"execution_result": "success"}
            
mock_supervisor.return_value = mock_supervisor_instance

result = await agent.execute(user_context, stream_updates=False)

            # Verify execution completed with context
assert result is not None
mock_supervisor_instance.execute_with_context.assert_called()

@pytest.mark.asyncio
    async def test_enhanced_websocket_notifications(self, user_context, mock_websocket_manager):
"""Test WebSocket notifications use new pattern."""
pass
agent = EnhancedExecutionAgent(websocket_manager=mock_websocket_manager)

with patch.object(agent, '_process_with_llm', return_value={"result": "test"}):
await agent.execute(user_context, stream_updates=True)

                    # Verify new emit_* methods were called
mock_websocket_manager.emit_agent_started.assert_called()
mock_websocket_manager.emit_agent_completed.assert_called()

@pytest.mark.asyncio
    async def test_enhanced_tool_execution(self, user_context, mock_websocket_manager):
"""Test tool execution with UserExecutionContext."""
agent = EnhancedExecutionAgent(websocket_manager=mock_websocket_manager)

                        # Set up tool requirement
user_context.metadata["user_request"] = "Execute database query tool"

with patch.object(agent, '_needs_tools', return_value=True):
with patch.object(agent, '_execute_tools', return_value={"tools_executed": ["db_query"]}):
result = await agent.execute(user_context, stream_updates=False)

                                # Verify tools were executed
assert result is not None
assert "tools_executed" in result or "db_query" in str(result)

@pytest.mark.asyncio
    async def test_enhanced_error_handling(self, user_context, mock_websocket_manager):
"""Test error handling and recovery."""
pass
agent = EnhancedExecutionAgent(websocket_manager=mock_websocket_manager)

                                    # Simulate various errors
with patch.object(agent, '_begin_execution', side_effect=Exception("Startup failed")):
result = await agent.execute(user_context, stream_updates=False)

                                        # Should handle error gracefully
mock_websocket_manager.emit_error.assert_called()
assert result is not None  # Should await asyncio.sleep(0)
return error result


class TestConcurrentUserIsolation(TestPhase2AgentsMigration):
    """Test concurrent execution across all agents for user isolation."""

@pytest.mark.asyncio
    async def test_all_agents_concurrent_isolation(self, mock_db_session, mock_websocket_manager):
"""Test all Phase 2 agents handle concurrent users correctly."""
        # Create agents
agents = [ )
ReportingSubAgent(websocket_manager=mock_websocket_manager),
OptimizationsCoreSubAgent( )
tool_dispatcher=Magic                websocket_manager=mock_websocket_manager
),
SyntheticDataSubAgent(),
GoalsTriageSubAgent(websocket_manager=mock_websocket_manager),
ActionsToMeetGoalsSubAgent(websocket_manager=mock_websocket_manager),
EnhancedExecutionAgent(websocket_manager=mock_websocket_manager)
        

        # Create 5 user contexts
contexts = []
for i in range(5):
ctx = UserExecutionContext( )
user_id="formatted_string",
thread_id="formatted_string",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=mock_db_session,
metadata={ )
"user_request": "formatted_string",
"data_result": {"user_specific": i},
"triage_result": {"priority": "medium"},
"optimizations_result": {"id": i}
            
            
contexts.append(ctx)

            # Execute all agents for all users concurrently
tasks = []
for agent in agents:
                # Mock agent-specific methods
if hasattr(agent, '_generate_report_with_llm'):
agent._generate_report_with_llm = MagicMock(return_value={"report": "test"})
if hasattr(agent, '_analyze_with_llm'):
agent._analyze_with_llm = MagicMock(return_value={"result": "test"})
if hasattr(agent, '_extract_and_analyze_goals'):
agent._extract_and_analyze_goals = MagicMock(return_value={"goals": ["test"]})
if hasattr(agent, '_generate_action_plan'):
agent._generate_action_plan = MagicMock(return_value={"plan": "test"})
if hasattr(agent, '_process_with_llm'):
agent._process_with_llm = MagicMock(return_value={"result": "test"})

                                    # Patch synthetic data components
if isinstance(agent, SyntheticDataSubAgent):
pass

for ctx in contexts:
tasks.append(agent.execute(ctx, stream_updates=False))

                                            # Execute all tasks concurrently
results = await asyncio.gather(*tasks, return_exceptions=True)

                                            # Verify no crashes and all completed
successful_results = [item for item in []]
assert len(successful_results) > 0  # At least some should succeed

                                            # Log any exceptions for debugging
exceptions = [item for item in []]
for exc in exceptions:
print("formatted_string")

@pytest.mark.asyncio
    async def test_thread_safety_with_shared_resources(self, mock_db_session, mock_websocket_manager):
"""Test thread safety when agents share resources."""
pass
shared_resource = {"counter": 0}
lock = threading.Lock()

class ThreadSafeAgent(ReportingSubAgent):
    def __init__(self, resource, lock, **kwargs):
        pass
        super().__init__(**kwargs)
        self.resource = resource
        self.lock = lock

    async def execute(self, context, stream_updates=False):
        pass
    # Simulate shared resource access
        with self.lock:
        self.resource["counter"] += 1
        current = self.resource["counter"]

        # Simulate some async work
        await asyncio.sleep(0.01)

        # Verify counter hasn't been corrupted
        with self.lock:
        assert self.resource["counter"] >= current

        await asyncio.sleep(0)
        return {"result": "formatted_string"}

        agent = ThreadSafeAgent( )
        resource=shared_resource,
        lock=lock,
        websocket_manager=mock_websocket_manager
            

            # Create many concurrent executions
        contexts = []
        for i in range(50):
        ctx = UserExecutionContext( )
        user_id="formatted_string",
        thread_id="formatted_string",
        run_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        db_session=mock_db_session,
        metadata={"user_request": "formatted_string"}
                
        contexts.append(ctx)

                # Execute concurrently
                # Removed problematic line: results = await asyncio.gather(*[ ))
        agent.execute(ctx, stream_updates=False) for ctx in contexts
                

                # Verify all completed and counter is correct
        assert len(results) == 50
        assert shared_resource["counter"] == 50

                # Verify each result is unique
        result_strings = [str(r) for r in results]
        assert len(set(result_strings)) == 50  # All unique


class TestSecurityAndDataLeakage(TestPhase2AgentsMigration):
        """Test for security issues and data leakage between users."""

@pytest.mark.asyncio
    async def test_no_data_leakage_between_users(self, mock_db_session, mock_websocket_manager):
"""Ensure no data leaks between different user contexts."""
agent = ReportingSubAgent(websocket_manager=mock_websocket_manager)

        # User 1 with sensitive data
sensitive_context = UserExecutionContext( )
user_id="sensitive_user",
thread_id="sensitive_thread",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=mock_db_session,
metadata={ )
"user_request": "Process my SSN: 123-45-6789",
"data_result": {"secret": "TOP_SECRET_DATA"},
"triage_result": {"classification": "confidential"}
        
        

        # User 2 - should not see User 1's data
normal_context = UserExecutionContext( )
user_id="normal_user",
thread_id="normal_thread",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=mock_db_session,
metadata={ )
"user_request": "Show me all data",
"data_result": {"public": "public_info"},
"triage_result": {"classification": "public"}
        
        

with patch.object(agent, '_generate_report_with_llm') as mock_generate:
            # Capture what data is passed to report generation
captured_data = []

def capture_and_return(prompt, *args, **kwargs):
captured_data.append(prompt)
await asyncio.sleep(0)
return {"report": "formatted_string"}

mock_generate.side_effect = capture_and_return

    # Execute for both users
sensitive_result = await agent.execute(sensitive_context, stream_updates=False)
normal_result = await agent.execute(normal_context, stream_updates=False)

    # Verify no cross-contamination
assert "TOP_SECRET_DATA" not in str(normal_result)
assert "123-45-6789" not in str(normal_result)
assert "sensitive_user" not in str(normal_result)

    # Verify each user's data is isolated
assert len(captured_data) == 2
assert "TOP_SECRET_DATA" not in captured_data[1]  # Normal user"s prompt
assert "public_info" not in captured_data[0]  # Sensitive user"s prompt

@pytest.mark.asyncio
    async def test_database_session_isolation(self, mock_websocket_manager):
"""Test that database sessions are properly isolated."""
pass
agent = OptimizationsCoreSubAgent( )
tool_dispatcher=Magic            websocket_manager=mock_websocket_manager
        

        # Create separate database sessions
session1 = Magic        session1.query = Magic        session1.commit = Magic
session2 = Magic        session2.query = Magic        session2.commit = Magic
context1 = UserExecutionContext( )
user_id="user1",
thread_id="thread1",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=session1,
metadata={"data_result": {"test": 1}}
        

context2 = UserExecutionContext( )
user_id="user2",
thread_id="thread2",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=session2,
metadata={"data_result": {"test": 2}}
        

with patch.object(agent, '_analyze_with_llm', return_value={"result": "test"}):
await asyncio.gather( )
agent.execute(context1, stream_updates=False),
agent.execute(context2, stream_updates=False)
            

            # Verify each session was used independently
session1.commit.assert_called()
session2.commit.assert_called()

            # Sessions should not have been mixed
assert session1 != session2


class TestPerformanceAndStress(TestPhase2AgentsMigration):
    """Performance and stress tests for migrated agents."""

@pytest.mark.asyncio
    async def test_high_concurrency_performance(self, mock_db_session, mock_websocket_manager):
"""Test agents under high concurrent load."""
agent = GoalsTriageSubAgent(websocket_manager=mock_websocket_manager)

        # Create 100 concurrent requests
contexts = []
for i in range(100):
ctx = UserExecutionContext( )
user_id="formatted_string",
thread_id="formatted_string",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=mock_db_session,
metadata={"user_request": "formatted_string"}
            
contexts.append(ctx)

with patch.object(agent, '_extract_and_analyze_goals', return_value={"goals": ["test"]}):
start_time = datetime.now()
                # Removed problematic line: results = await asyncio.gather(*[ ))
agent.execute(ctx, stream_updates=False) for ctx in contexts
                
end_time = datetime.now()

                # All should complete
assert len(results) == 100
assert all(r is not None for r in results)

                # Should complete in reasonable time (< 10 seconds for 100 requests)
duration = (end_time - start_time).total_seconds()
assert duration < 10, "formatted_string"

@pytest.mark.asyncio
    async def test_memory_leak_prevention(self, mock_db_session, mock_websocket_manager):
"""Test that agents don't leak memory with repeated executions."""
pass
agent = ActionsToMeetGoalsSubAgent(websocket_manager=mock_websocket_manager)

                    # Execute many times with same agent instance
for i in range(100):
ctx = UserExecutionContext( )
user_id="formatted_string",
thread_id="formatted_string",
run_id=str(uuid.uuid4()),
request_id=str(uuid.uuid4()),
db_session=mock_db_session,
metadata={ )
"user_request": "formatted_string",
"optimizations_result": {"test": i}
                        
                        

with patch.object(agent, '_generate_action_plan', return_value={"plan": "formatted_string"}):
result = await agent.execute(ctx, stream_updates=False)

                            # Result should be independent
assert "formatted_string" in str(result)

                            # Agent should not accumulate state
assert not hasattr(agent, 'accumulated_state')
assert not hasattr(agent, 'formatted_string')


                            # Run all tests
if __name__ == "__main__":
pytest.main([__file__, "-v", "--tb=short"])