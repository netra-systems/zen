"""
Migration Validation Test Suite: DeepAgentState to UserExecutionContext

This test suite validates the security and functionality of migrating from DeepAgentState
to UserExecutionContext pattern to fix the user isolation vulnerability (Issue #271).

Business Impact: Protects $500K+ ARR by ensuring proper user data isolation.
"""

import asyncio
import pytest
import time
import uuid
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    validate_user_context,
    InvalidContextError,
    ContextIsolationError
)
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcherCore
from netra_backend.app.websocket_core.connection_executor import ConnectionExecutor
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class TestUserIsolationValidation:
    """Test suite to validate user isolation after migration from DeepAgentState."""
    
    @pytest.fixture
    def user1_context(self) -> UserExecutionContext:
        """Create isolated context for user 1."""
        return UserExecutionContext.from_request(
            user_id="test_user_1",
            thread_id="thread_1",
            run_id="run_1",
            agent_context={
                "user_request": "User 1 private request",
                "sensitive_data": "user1_secret_data",
                "user_preferences": {"theme": "dark", "api_key": "user1_api_key"}
            },
            audit_metadata={
                "test_scenario": "user_isolation_validation",
                "user_tier": "enterprise"
            }
        )
    
    @pytest.fixture
    def user2_context(self) -> UserExecutionContext:
        """Create isolated context for user 2."""
        return UserExecutionContext.from_request(
            user_id="test_user_2",
            thread_id="thread_2", 
            run_id="run_2",
            agent_context={
                "user_request": "User 2 confidential request",
                "sensitive_data": "user2_secret_data",
                "user_preferences": {"theme": "light", "api_key": "user2_api_key"}
            },
            audit_metadata={
                "test_scenario": "user_isolation_validation", 
                "user_tier": "free"
            }
        )
    
    @pytest.fixture
    def mock_execution_context(self) -> AgentExecutionContext:
        """Create mock execution context."""
        return AgentExecutionContext(
            run_id="test_run",
            agent_name="test_agent",
            user_id="test_user",
            thread_id="test_thread"
        )
    
    async def test_concurrent_agent_execution_isolation(
        self, 
        user1_context: UserExecutionContext,
        user2_context: UserExecutionContext,
        mock_execution_context: AgentExecutionContext
    ):
        """
        CRITICAL TEST: Verify concurrent agent execution maintains user isolation.
        
        This test directly validates the security fix for Issue #271.
        """
        
        execution_core = AgentExecutionCore()
        
        # Mock agent registry and execution
        with patch.object(execution_core, 'agent_registry') as mock_registry:
            # Create mock agent that logs the context it receives
            received_contexts = []
            
            async def mock_execute(context, exec_context):
                received_contexts.append({
                    'user_id': context.user_id,
                    'agent_context': context.agent_context.copy(),
                    'thread_id': context.thread_id,
                    'request_id': context.request_id
                })
                return MagicMock(success=True)
            
            mock_agent = AsyncMock()
            mock_agent.execute = mock_execute
            mock_registry.get_agent.return_value = mock_agent
            
            # Execute concurrent agent operations
            task1 = asyncio.create_task(
                execution_core.execute_agent_safely(
                    "test_agent", 
                    user1_context, 
                    mock_execution_context
                )
            )
            task2 = asyncio.create_task(
                execution_core.execute_agent_safely(
                    "test_agent",
                    user2_context, 
                    mock_execution_context
                )
            )
            
            # Wait for both executions to complete
            results = await asyncio.gather(task1, task2)
            
            # CRITICAL VALIDATION: No cross-user data contamination
            assert len(received_contexts) == 2
            
            user1_received = next(ctx for ctx in received_contexts if ctx['user_id'] == 'test_user_1')
            user2_received = next(ctx for ctx in received_contexts if ctx['user_id'] == 'test_user_2')
            
            # Verify user 1's sensitive data not in user 2's context
            assert "user1_secret_data" not in str(user2_received['agent_context'])
            assert "user1_api_key" not in str(user2_received['agent_context'])
            
            # Verify user 2's sensitive data not in user 1's context  
            assert "user2_secret_data" not in str(user1_received['agent_context'])
            assert "user2_api_key" not in str(user1_received['agent_context'])
            
            # Verify correct data isolation
            assert user1_received['agent_context']['sensitive_data'] == "user1_secret_data"
            assert user2_received['agent_context']['sensitive_data'] == "user2_secret_data"
            
            # Verify unique request IDs
            assert user1_received['request_id'] != user2_received['request_id']
            
            # Verify results are properly isolated
            assert results[0].success == True
            assert results[1].success == True

    async def test_websocket_execution_isolation(self):
        """Test WebSocket execution maintains user isolation."""
        
        connection_executor = ConnectionExecutor()
        websocket_events = {}  # Track events sent to each connection
        
        # Mock WebSocket bridge to track events
        def mock_send_event(connection_id: str, event_data: Dict[str, Any]):
            if connection_id not in websocket_events:
                websocket_events[connection_id] = []
            websocket_events[connection_id].append(event_data)
        
        with patch.object(connection_executor, 'websocket_bridge') as mock_bridge:
            mock_bridge.send_agent_event = AsyncMock(side_effect=mock_send_event)
            
            # Mock agent execution to return different results per user
            with patch.object(connection_executor, '_process_user_request') as mock_process:
                async def mock_process_request(user_context):
                    # Store user-specific data in mock events
                    if user_context.websocket_client_id:
                        mock_send_event(user_context.websocket_client_id, {
                            'event': 'agent_response',
                            'user_id': user_context.user_id,
                            'data': f"Response for {user_context.user_id}",
                            'sensitive_info': user_context.agent_context.get('sensitive_data')
                        })
                
                mock_process.side_effect = mock_process_request
                
                # Create concurrent WebSocket requests
                user1_request = {
                    "user_id": "ws_user_1",
                    "message": "User 1 private message", 
                    "sensitive_data": "user1_websocket_secret"
                }
                
                user2_request = {
                    "user_id": "ws_user_2",
                    "message": "User 2 private message",
                    "sensitive_data": "user2_websocket_secret" 
                }
                
                # Execute concurrent WebSocket requests
                await asyncio.gather(
                    connection_executor.execute_with_websocket(user1_request, "conn_1"),
                    connection_executor.execute_with_websocket(user2_request, "conn_2")
                )
                
                # CRITICAL VALIDATION: WebSocket events isolated per connection
                assert "conn_1" in websocket_events
                assert "conn_2" in websocket_events
                
                conn1_events = websocket_events["conn_1"]
                conn2_events = websocket_events["conn_2"] 
                
                # Verify no cross-contamination in WebSocket events
                for event in conn1_events:
                    assert "user2_websocket_secret" not in str(event)
                    assert event.get('user_id') != 'ws_user_2'
                
                for event in conn2_events:
                    assert "user1_websocket_secret" not in str(event) 
                    assert event.get('user_id') != 'ws_user_1'

    async def test_tool_dispatcher_isolation(
        self,
        user1_context: UserExecutionContext,
        user2_context: UserExecutionContext
    ):
        """Test tool dispatcher maintains user isolation."""
        
        tool_dispatcher = ToolDispatcherCore()
        tool_results = {}
        
        # Mock tool execution to track context isolation
        async def mock_tool_execution(tool_name: str, params: Dict, context: UserExecutionContext):
            tool_results[context.request_id] = {
                'user_id': context.user_id,
                'tool_name': tool_name,
                'user_data': context.agent_context.copy(),
                'params': params
            }
            return MagicMock(success=True, result=f"Tool result for {context.user_id}")
        
        with patch.object(tool_dispatcher, '_execute_tool_with_context', side_effect=mock_tool_execution):
            # Execute tools concurrently for different users
            tool_params_user1 = {"query": "User 1 private query", "api_key": "user1_tool_key"}
            tool_params_user2 = {"query": "User 2 private query", "api_key": "user2_tool_key"}
            
            await asyncio.gather(
                tool_dispatcher.dispatch_tool("search_tool", tool_params_user1, user1_context),
                tool_dispatcher.dispatch_tool("search_tool", tool_params_user2, user2_context)
            )
            
            # CRITICAL VALIDATION: Tool execution isolated per user
            assert len(tool_results) == 2
            
            user1_result = tool_results[user1_context.request_id]
            user2_result = tool_results[user2_context.request_id]
            
            # Verify no cross-user data in tool results
            assert "user2_tool_key" not in str(user1_result)
            assert "user1_tool_key" not in str(user2_result)
            
            # Verify correct user data isolation
            assert user1_result['user_id'] == 'test_user_1'
            assert user2_result['user_id'] == 'test_user_2'


class TestMigrationFunctionalityValidation:
    """Test suite to validate functionality is preserved after migration."""
    
    @pytest.fixture  
    def sample_context(self) -> UserExecutionContext:
        """Create sample context for functionality testing."""
        return UserExecutionContext.from_request(
            user_id="func_test_user",
            thread_id="func_thread",
            run_id="func_run", 
            agent_context={
                "user_request": "Analyze my usage patterns",
                "user_tier": "enterprise",
                "preferences": {"analysis_depth": "detailed"}
            }
        )
    
    async def test_agent_execution_core_functionality_preserved(
        self,
        sample_context: UserExecutionContext
    ):
        """Test that agent execution core functionality is preserved after migration."""
        
        execution_core = AgentExecutionCore()
        mock_execution_context = AgentExecutionContext(
            run_id="func_test_run",
            agent_name="test_agent", 
            user_id="func_test_user",
            thread_id="func_thread"
        )
        
        with patch.object(execution_core, 'agent_registry') as mock_registry:
            # Mock successful agent execution
            mock_agent = AsyncMock()
            mock_agent.execute.return_value = MagicMock(
                success=True,
                result_data={"analysis": "usage analysis complete"},
                execution_time=1.5
            )
            mock_registry.get_agent.return_value = mock_agent
            
            # Execute agent
            result = await execution_core.execute_agent_safely(
                "analysis_agent",
                sample_context,
                mock_execution_context
            )
            
            # Validate functionality preserved
            assert result.success == True
            assert "analysis" in result.result_data
            
            # Verify agent was called with correct context
            mock_agent.execute.assert_called_once()
            call_args = mock_agent.execute.call_args[0]
            passed_context = call_args[0]
            
            assert isinstance(passed_context, UserExecutionContext)
            assert passed_context.user_id == "func_test_user"
            assert "user_request" in passed_context.agent_context

    async def test_workflow_orchestration_functionality_preserved(
        self,
        sample_context: UserExecutionContext
    ):
        """Test workflow orchestration functionality is preserved after migration."""
        
        orchestrator = WorkflowOrchestrator()
        mock_execution_context = AgentExecutionContext(
            run_id="workflow_test_run",
            agent_name="supervisor",
            user_id="func_test_user", 
            thread_id="func_thread"
        )
        
        with patch.object(orchestrator, '_execute_workflow_steps') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                workflow_result={"steps_completed": 3, "final_result": "workflow success"}
            )
            
            # Execute workflow
            result = await orchestrator.orchestrate_workflow(
                "analysis_workflow",
                sample_context,
                mock_execution_context
            )
            
            # Validate functionality preserved
            assert result.success == True 
            assert result.workflow_result["steps_completed"] == 3
            
            # Verify workflow was called with correct context
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[0]
            workflow_context = call_args[0]
            
            assert isinstance(workflow_context, UserExecutionContext)
            assert workflow_context.user_id == sample_context.user_id


class TestContextValidationAndSecurity:
    """Test suite for context validation and security features."""
    
    def test_invalid_context_detection(self):
        """Test that invalid contexts are properly detected."""
        
        # Test empty user_id
        with pytest.raises(InvalidContextError, match="user_id must be a non-empty string"):
            UserExecutionContext.from_request(
                user_id="",
                thread_id="thread", 
                run_id="run"
            )
        
        # Test placeholder values
        with pytest.raises(InvalidContextError, match="forbidden placeholder value"):
            UserExecutionContext.from_request(
                user_id="placeholder",
                thread_id="thread",
                run_id="run" 
            )
    
    def test_context_isolation_verification(self):
        """Test context isolation verification mechanisms."""
        
        context = UserExecutionContext.from_request(
            user_id="isolation_test_user",
            thread_id="isolation_thread",
            run_id="isolation_run"
        )
        
        # Validation should pass for properly isolated context
        assert validate_user_context(context) == context
        
        # Test context isolation verification
        assert context.verify_isolation() == True
    
    def test_child_context_creation_isolation(self):
        """Test that child contexts maintain proper isolation."""
        
        parent_context = UserExecutionContext.from_request(
            user_id="parent_user",
            thread_id="parent_thread", 
            run_id="parent_run",
            agent_context={"parent_data": "sensitive_parent_info"}
        )
        
        child_context = parent_context.create_child_context(
            "child_operation",
            additional_agent_context={"child_data": "child_specific_info"}
        )
        
        # Verify child context inherits parent data properly
        assert child_context.user_id == parent_context.user_id
        assert child_context.thread_id == parent_context.thread_id
        assert child_context.run_id == parent_context.run_id
        
        # Verify child has its own request ID
        assert child_context.request_id != parent_context.request_id
        
        # Verify data isolation - child should have access to parent data
        assert "parent_data" in child_context.agent_context
        assert "child_data" in child_context.agent_context
        
        # Verify child operation tracking
        assert child_context.operation_depth == parent_context.operation_depth + 1
        assert child_context.parent_request_id == parent_context.request_id


class TestPerformanceAndResourceManagement:
    """Test suite for performance and resource management after migration."""
    
    async def test_concurrent_execution_performance(self):
        """Test performance under concurrent execution."""
        
        contexts = []
        for i in range(10):
            context = UserExecutionContext.from_request(
                user_id=f"perf_user_{i}",
                thread_id=f"perf_thread_{i}",
                run_id=f"perf_run_{i}",
                agent_context={"user_data": f"data_for_user_{i}"}
            )
            contexts.append(context)
        
        execution_core = AgentExecutionCore()
        
        with patch.object(execution_core, 'agent_registry') as mock_registry:
            mock_agent = AsyncMock()
            mock_agent.execute.return_value = MagicMock(success=True)
            mock_registry.get_agent.return_value = mock_agent
            
            mock_execution_context = AgentExecutionContext(
                run_id="perf_test",
                agent_name="test_agent",
                user_id="test_user", 
                thread_id="test_thread"
            )
            
            # Execute all contexts concurrently and measure performance
            start_time = time.time()
            
            tasks = [
                execution_core.execute_agent_safely(
                    "test_agent",
                    context,
                    mock_execution_context
                )
                for context in contexts
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Validate all executions succeeded
            assert all(result.success for result in results)
            
            # Performance should be reasonable (under 5 seconds for 10 concurrent operations)
            assert execution_time < 5.0
            
            # Verify all contexts were processed
            assert len(results) == 10
    
    def test_memory_usage_isolation(self):
        """Test that contexts don't create memory leaks or shared references."""
        
        import gc
        import sys
        
        # Create multiple contexts
        contexts = []
        for i in range(100):
            context = UserExecutionContext.from_request(
                user_id=f"mem_user_{i}",
                thread_id=f"mem_thread_{i}",
                run_id=f"mem_run_{i}",
                agent_context={"large_data": "x" * 1000}  # 1KB per context
            )
            contexts.append(context)
        
        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Clear contexts and force garbage collection
        contexts.clear()
        gc.collect()
        
        final_objects = len(gc.get_objects())
        
        # Verify objects were properly cleaned up (allowing for some variance)
        object_difference = abs(final_objects - initial_objects)
        assert object_difference < 50  # Should be minimal difference


class TestBusinessContinuityValidation:
    """Test suite to validate business continuity after migration."""
    
    async def test_golden_path_user_flow_preserved(self):
        """Test that the Golden Path user flow is preserved after migration."""
        
        # Simulate complete user flow: WebSocket → Agent Execution → Response
        connection_executor = ConnectionExecutor()
        
        user_request = {
            "user_id": "golden_path_user",
            "message": "Help me optimize my AI costs by 30%",
            "type": "chat"
        }
        
        # Mock the complete execution pipeline
        with patch.multiple(
            connection_executor,
            _process_user_request=AsyncMock(),
            _send_success_response=AsyncMock(),
            websocket_bridge=AsyncMock()
        ):
            # Execute Golden Path flow
            await connection_executor.execute_with_websocket(user_request, "golden_conn")
            
            # Verify user request was processed with proper context
            connection_executor._process_user_request.assert_called_once()
            call_args = connection_executor._process_user_request.call_args[0]
            user_context = call_args[0]
            
            # Validate Golden Path context
            assert isinstance(user_context, UserExecutionContext)
            assert user_context.user_id == "golden_path_user"
            assert user_context.websocket_client_id == "golden_conn"
            assert "Help me optimize my AI costs by 30%" in user_context.agent_context.get('user_message', '')
    
    async def test_enterprise_customer_workflow_preserved(self):
        """Test enterprise customer workflows are preserved."""
        
        # Create enterprise customer context
        enterprise_context = UserExecutionContext.from_request(
            user_id="enterprise_customer_001", 
            thread_id="ent_thread_001",
            run_id="ent_run_001",
            agent_context={
                "user_request": "Generate comprehensive cost analysis report",
                "user_tier": "enterprise",
                "customer_features": ["advanced_analytics", "priority_support"],
                "data_retention": "7_years"
            },
            audit_metadata={
                "compliance_level": "SOC2",
                "data_classification": "confidential",
                "customer_id": "CUST_ENT_001"
            }
        )
        
        execution_core = AgentExecutionCore()
        mock_execution_context = AgentExecutionContext(
            run_id="enterprise_run",
            agent_name="enterprise_agent",
            user_id="enterprise_customer_001",
            thread_id="ent_thread_001"
        )
        
        with patch.object(execution_core, 'agent_registry') as mock_registry:
            mock_agent = AsyncMock() 
            mock_agent.execute.return_value = MagicMock(
                success=True,
                result_data={
                    "report_generated": True,
                    "compliance_validated": True,
                    "enterprise_features_used": ["advanced_analytics"]
                }
            )
            mock_registry.get_agent.return_value = mock_agent
            
            # Execute enterprise workflow
            result = await execution_core.execute_agent_safely(
                "enterprise_agent",
                enterprise_context,
                mock_execution_context
            )
            
            # Validate enterprise features preserved
            assert result.success == True
            assert result.result_data["compliance_validated"] == True
            
            # Verify enterprise context was passed correctly  
            mock_agent.execute.assert_called_once()
            call_context = mock_agent.execute.call_args[0][0]
            
            assert call_context.agent_context["user_tier"] == "enterprise"
            assert "SOC2" in call_context.audit_metadata.get("compliance_level", "")


# Run tests with proper test configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])