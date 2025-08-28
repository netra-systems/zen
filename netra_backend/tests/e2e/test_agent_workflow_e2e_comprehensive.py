"""
End-to-End Agent Workflow Tests (Iterations 26-30).

Tests complete agent workflows from request initiation through 
task completion, including multi-agent collaboration and WebSocket communication.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List
import json
import time

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.websocket.connection_manager import ConnectionManager as WebSocketManager


@pytest.mark.e2e
class TestCompleteAgentWorkflow:
    """Test complete agent workflow end-to-end."""
    
    @pytest.mark.asyncio
    async def test_full_data_analysis_workflow(self):
        """Test complete data analysis workflow from request to response."""
        # Mock WebSocket manager for real-time updates
        mock_websocket_manager = Mock(spec=WebSocketManager)
        mock_websocket_manager.broadcast_to_thread = AsyncMock()
        mock_websocket_manager.get_active_connections.return_value = ["conn_1", "conn_2"]
        
        # Mock database operations
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        # Mock ClickHouse for analytics
        mock_clickhouse_result = [
            {"timestamp": "2024-01-01T00:00:00Z", "metric": "latency", "value": 150},
            {"timestamp": "2024-01-01T01:00:00Z", "metric": "latency", "value": 200},
            {"timestamp": "2024-01-01T02:00:00Z", "metric": "latency", "value": 120}
        ]
        
        with patch('netra_backend.app.websocket_core.utils.get_connection_monitor', return_value=mock_websocket_manager):
            with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
                with patch('netra_backend.app.db.clickhouse.ClickHouseService') as mock_clickhouse:
                    
                    mock_clickhouse_instance = Mock()
                    mock_clickhouse_instance.execute_query = AsyncMock(return_value=mock_clickhouse_result)
                    mock_clickhouse.return_value = mock_clickhouse_instance
                    
                    # Initialize workflow
                    workflow_request = {
                        "user_id": "user123",
                        "thread_id": "thread456",
                        "session_id": "session789", 
                        "task_type": "data_analysis",
                        "parameters": {
                            "analysis_type": "latency_trends",
                            "time_range": "24h",
                            "metrics": ["latency", "throughput"],
                            "filters": {"service": "api_gateway"}
                        }
                    }
                    
                    # Create supervisor agent
                    agent_state = DeepAgentState(
                        agent_id="workflow_supervisor",
                        session_id=workflow_request["session_id"],
                        thread_id=workflow_request["thread_id"],
                        context={
                            "user_id": workflow_request["user_id"],
                            "task_type": workflow_request["task_type"],
                            "parameters": workflow_request["parameters"]
                        }
                    )
                    
                    agent = SupervisorAgent(
                        agent_id="e2e_workflow_test",
                        initial_state=agent_state
                    )
                    
                    # Execute complete workflow
                    start_time = time.time()
                    workflow_result = await agent._execute_complete_workflow(workflow_request)
                    end_time = time.time()
                    
                    # Verify workflow completion
                    assert workflow_result["status"] == "completed"
                    assert workflow_result["task_type"] == "data_analysis"
                    assert "analysis_results" in workflow_result
                    assert "insights" in workflow_result
                    assert workflow_result["execution_time_ms"] > 0
                    
                    # Verify data was fetched and processed
                    assert len(workflow_result["analysis_results"]["data_points"]) == 3
                    assert workflow_result["analysis_results"]["trend"] in ["increasing", "decreasing", "stable"]
                    
                    # Verify WebSocket notifications were sent
                    expected_calls = 4  # Started, progress updates, completed
                    assert mock_websocket_manager.broadcast_to_thread.call_count >= expected_calls
                    
                    # Verify database state was persisted
                    mock_session.execute.assert_called()
                    
                    # Verify workflow metadata
                    assert workflow_result["workflow_id"] is not None
                    assert workflow_result["user_id"] == "user123"
                    assert workflow_result["thread_id"] == "thread456"
                    assert end_time - start_time < 30  # Should complete within 30 seconds
    
    @pytest.mark.asyncio
    async def test_multi_agent_collaboration_workflow(self):
        """Test workflow involving multiple specialized agents."""
        # Mock different agent types
        mock_data_agent = Mock()
        mock_data_agent.execute_task = AsyncMock(return_value={
            "status": "completed",
            "data": {"processed_records": 1000, "analysis_results": {"avg_latency": 150}}
        })
        
        mock_llm_agent = Mock()
        mock_llm_agent.execute_task = AsyncMock(return_value={
            "status": "completed", 
            "insights": ["Latency increased by 15% compared to yesterday", "Peak usage at 2-3 PM"],
            "recommendations": ["Scale up during peak hours", "Optimize slow queries"]
        })
        
        mock_websocket_manager = Mock(spec=WebSocketManager)
        mock_websocket_manager.broadcast_to_thread = AsyncMock()
        
        with patch('netra_backend.app.websocket_core.utils.get_connection_monitor', return_value=mock_websocket_manager):
            with patch('netra_backend.app.agents.data_sub_agent.data_agent.DataAgent', return_value=mock_data_agent):
                with patch('netra_backend.app.agents.llm_sub_agent.llm_agent.LLMAgent', return_value=mock_llm_agent):
                    
                    workflow_request = {
                        "user_id": "user456",
                        "thread_id": "thread789",
                        "session_id": "session012",
                        "task_type": "comprehensive_analysis",
                        "parameters": {
                            "data_sources": ["clickhouse", "prometheus"],
                            "analysis_depth": "comprehensive",
                            "include_recommendations": True,
                            "collaboration_mode": True
                        }
                    }
                    
                    agent_state = DeepAgentState(
                        agent_id="multi_agent_supervisor",
                        session_id=workflow_request["session_id"],
                        thread_id=workflow_request["thread_id"],
                        context=workflow_request["parameters"]
                    )
                    
                    agent = SupervisorAgent(
                        agent_id="multi_agent_test", 
                        initial_state=agent_state
                    )
                    
                    # Execute multi-agent workflow
                    result = await agent._execute_collaborative_workflow(workflow_request)
                    
                    # Verify coordination between agents
                    assert result["status"] == "completed"
                    assert result["agents_involved"] == ["data_agent", "llm_agent"]
                    assert result["collaboration_successful"] is True
                    
                    # Verify data agent was called first
                    mock_data_agent.execute_task.assert_called_once()
                    data_call_args = mock_data_agent.execute_task.call_args[1]
                    assert data_call_args["task_type"] == "data_processing"
                    
                    # Verify LLM agent received data agent results
                    mock_llm_agent.execute_task.assert_called_once() 
                    llm_call_args = mock_llm_agent.execute_task.call_args[1]
                    assert "data_results" in llm_call_args["context"]
                    assert llm_call_args["task_type"] == "insight_generation"
                    
                    # Verify final results combine both agents' outputs
                    assert "data_analysis" in result
                    assert "insights" in result
                    assert "recommendations" in result
                    assert len(result["recommendations"]) == 2
    
    @pytest.mark.asyncio
    async def test_error_recovery_in_workflow(self):
        """Test workflow error recovery and graceful degradation."""
        mock_websocket_manager = Mock(spec=WebSocketManager)
        mock_websocket_manager.broadcast_to_thread = AsyncMock()
        
        # Simulate partial failures in workflow steps
        step_results = [
            {"status": "completed", "step": "initialization"},
            {"status": "failed", "step": "data_fetch", "error": "ClickHouse timeout"},
            {"status": "completed", "step": "fallback_data_fetch", "source": "postgres"},
            {"status": "completed", "step": "analysis"}
        ]
        step_iter = iter(step_results)
        
        with patch('netra_backend.app.websocket_core.utils.get_connection_monitor', return_value=mock_websocket_manager):
            
            agent_state = DeepAgentState(
                agent_id="error_recovery_agent",
                session_id="recovery_session",
                thread_id="recovery_thread", 
                context={"error_recovery_enabled": True, "fallback_strategies": ["postgres_fallback"]}
            )
            
            agent = SupervisorAgent(
                agent_id="error_recovery_test",
                initial_state=agent_state
            )
            
            # Mock step execution with failures
            async def mock_execute_step(step_config):
                result = next(step_iter)
                if result["status"] == "failed":
                    # Simulate retry with fallback
                    fallback_result = next(step_iter) 
                    return fallback_result
                return result
            
            agent._execute_workflow_step = mock_execute_step
            
            workflow_request = {
                "user_id": "user_recovery",
                "thread_id": "recovery_thread",
                "session_id": "recovery_session",
                "task_type": "resilient_analysis",
                "parameters": {"enable_fallbacks": True, "max_retries": 2}
            }
            
            result = await agent._execute_resilient_workflow(workflow_request)
            
            # Verify workflow completed despite failures
            assert result["status"] == "completed_with_degradation"
            assert result["errors_encountered"] == 1
            assert result["fallbacks_used"] == 1
            assert result["final_data_source"] == "postgres"
            
            # Verify error notifications were sent
            error_notifications = [
                call for call in mock_websocket_manager.broadcast_to_thread.call_args_list
                if "error" in str(call)
            ]
            assert len(error_notifications) >= 1
            
            # Verify recovery steps were logged
            assert "recovery_actions" in result
            assert len(result["recovery_actions"]) >= 1


@pytest.mark.e2e
class TestAgentWebSocketIntegration:
    """Test agent integration with WebSocket real-time communication."""
    
    @pytest.mark.asyncio
    async def test_real_time_progress_updates(self):
        """Test agent sends real-time progress updates via WebSocket."""
        mock_websocket_manager = Mock(spec=WebSocketManager)
        mock_websocket_manager.broadcast_to_thread = AsyncMock()
        mock_websocket_manager.get_thread_connections.return_value = ["conn1", "conn2"]
        
        with patch('netra_backend.app.websocket_core.utils.get_connection_monitor', return_value=mock_websocket_manager):
            
            agent_state = DeepAgentState(
                agent_id="progress_agent",
                session_id="progress_session", 
                thread_id="progress_thread",
                context={"real_time_updates": True, "progress_interval": 0.1}
            )
            
            agent = SupervisorAgent(
                agent_id="progress_test",
                initial_state=agent_state
            )
            
            # Execute long-running task with progress updates
            task_config = {
                "task_type": "batch_processing",
                "total_items": 100,
                "batch_size": 10,
                "progress_updates": True
            }
            
            result = await agent._execute_with_progress_updates(task_config)
            
            # Verify task completed
            assert result["status"] == "completed"
            assert result["items_processed"] == 100
            
            # Verify progress updates were sent
            progress_calls = [
                call for call in mock_websocket_manager.broadcast_to_thread.call_args_list
                if "progress" in str(call[0][1])  # Check message content
            ]
            
            assert len(progress_calls) >= 10  # Should have multiple progress updates
            
            # Verify progress message format
            sample_call = mock_websocket_manager.broadcast_to_thread.call_args_list[0]
            thread_id, message = sample_call[0]
            assert thread_id == "progress_thread"
            
            message_data = json.loads(message)
            assert message_data["type"] in ["progress", "agent_started", "agent_completed"]
            assert "agent_id" in message_data
            assert "timestamp" in message_data
    
    @pytest.mark.asyncio
    async def test_websocket_error_notifications(self):
        """Test agent sends error notifications via WebSocket."""
        mock_websocket_manager = Mock(spec=WebSocketManager)
        mock_websocket_manager.broadcast_to_thread = AsyncMock()
        mock_websocket_manager.send_error_notification = AsyncMock()
        
        with patch('netra_backend.app.websocket_core.utils.get_connection_monitor', return_value=mock_websocket_manager):
            
            agent_state = DeepAgentState(
                agent_id="error_agent",
                session_id="error_session",
                thread_id="error_thread", 
                context={"error_notifications": True}
            )
            
            agent = SupervisorAgent(
                agent_id="error_notification_test",
                initial_state=agent_state
            )
            
            # Execute task that will encounter errors
            task_config = {
                "task_type": "failing_operation",
                "simulate_errors": ["connection_error", "timeout_error", "validation_error"],
                "max_error_retries": 2
            }
            
            result = await agent._execute_with_error_notifications(task_config)
            
            # Verify errors were handled and notifications sent
            assert result["status"] == "failed"
            assert result["errors_encountered"] == 3
            
            # Verify error notifications were sent via WebSocket
            error_calls = [
                call for call in mock_websocket_manager.broadcast_to_thread.call_args_list
                if "error" in str(call[0][1])
            ]
            
            assert len(error_calls) >= 3  # One for each error type
            
            # Verify error message format
            error_call = error_calls[0]
            thread_id, error_message = error_call[0]
            assert thread_id == "error_thread"
            
            error_data = json.loads(error_message)
            assert error_data["type"] == "agent_error"
            assert error_data["error_type"] in ["connection_error", "timeout_error", "validation_error"]
            assert "error_details" in error_data
    
    @pytest.mark.asyncio
    async def test_websocket_bidirectional_communication(self):
        """Test bidirectional communication between client and agent via WebSocket."""
        mock_websocket_manager = Mock(spec=WebSocketManager)
        mock_websocket_manager.broadcast_to_thread = AsyncMock()
        mock_websocket_manager.send_to_connection = AsyncMock()
        
        # Simulate incoming messages from client
        incoming_messages = [
            {"type": "pause_request", "reason": "user_initiated"},
            {"type": "resume_request"},
            {"type": "cancel_request", "reason": "user_cancelled"}
        ]
        message_iter = iter(incoming_messages)
        
        async def mock_receive_message():
            return next(message_iter, None)
        
        with patch('netra_backend.app.websocket_core.utils.get_connection_monitor', return_value=mock_websocket_manager):
            
            agent_state = DeepAgentState(
                agent_id="interactive_agent",
                session_id="interactive_session",
                thread_id="interactive_thread",
                context={"interactive_mode": True}
            )
            
            agent = SupervisorAgent(
                agent_id="interactive_test",
                initial_state=agent_state
            )
            
            # Mock message receiving
            agent._receive_websocket_message = mock_receive_message
            
            # Execute interactive task
            task_config = {
                "task_type": "interactive_analysis", 
                "allow_interruptions": True,
                "response_to_commands": True
            }
            
            result = await agent._execute_interactive_task(task_config)
            
            # Verify agent responded to user commands
            assert result["status"] == "cancelled"  # Last command was cancel
            assert result["interactions"] == 3
            assert result["pause_count"] == 1
            assert result["resume_count"] == 1
            assert result["cancellation_reason"] == "user_cancelled"
            
            # Verify acknowledgments were sent
            ack_calls = [
                call for call in mock_websocket_manager.broadcast_to_thread.call_args_list
                if "acknowledgment" in str(call[0][1])
            ]
            assert len(ack_calls) >= 3  # One for each command received


@pytest.mark.e2e
class TestAgentSystemIntegration:
    """Test agent integration with broader system components."""
    
    @pytest.mark.asyncio
    async def test_agent_authentication_authorization_workflow(self):
        """Test agent respects authentication and authorization throughout workflow."""
        # Mock auth service responses
        mock_auth_service = Mock()
        mock_auth_service.validate_token = AsyncMock(return_value={
            "valid": True,
            "user_id": "authenticated_user",
            "permissions": ["read:analytics", "write:reports"],
            "expires_at": "2024-12-31T23:59:59Z"
        })
        mock_auth_service.check_permission = AsyncMock(return_value=True)
        
        # Mock database with user context
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.auth.auth_service_client.auth_service', mock_auth_service):
            with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
                
                workflow_request = {
                    "user_id": "authenticated_user",
                    "auth_token": "valid_jwt_token",
                    "thread_id": "secure_thread", 
                    "session_id": "secure_session",
                    "task_type": "sensitive_analysis",
                    "parameters": {
                        "data_access_level": "restricted",
                        "required_permissions": ["read:analytics"]
                    }
                }
                
                agent_state = DeepAgentState(
                    agent_id="secure_agent",
                    session_id=workflow_request["session_id"],
                    thread_id=workflow_request["thread_id"],
                    context={
                        "user_id": workflow_request["user_id"],
                        "auth_token": workflow_request["auth_token"],
                        "security_context": "authenticated"
                    }
                )
                
                agent = SupervisorAgent(
                    agent_id="auth_test",
                    initial_state=agent_state
                )
                
                # Execute workflow with auth checks
                result = await agent._execute_secure_workflow(workflow_request)
                
                # Verify authentication was validated
                mock_auth_service.validate_token.assert_called_with("valid_jwt_token")
                
                # Verify permission checks occurred
                mock_auth_service.check_permission.assert_called_with(
                    "authenticated_user", "read:analytics"
                )
                
                # Verify workflow completed successfully
                assert result["status"] == "completed"
                assert result["user_id"] == "authenticated_user"
                assert result["security_validated"] is True
                
                # Verify audit trail was created
                audit_calls = [
                    call for call in mock_session.execute.call_args_list 
                    if "audit" in str(call[0][0]).lower()
                ]
                assert len(audit_calls) >= 1
    
    @pytest.mark.asyncio
    async def test_agent_configuration_management_integration(self):
        """Test agent integrates with configuration management system."""
        # Mock configuration manager
        mock_config_manager = Mock()
        mock_config_manager.get_agent_config.return_value = {
            "max_execution_time": 300,
            "retry_attempts": 3,
            "batch_size": 50,
            "memory_limit_mb": 512,
            "features": ["real_time_updates", "error_recovery", "performance_monitoring"]
        }
        mock_config_manager.get_feature_flags.return_value = {
            "enable_llm_integration": True,
            "enable_advanced_analytics": True,
            "enable_experimental_features": False
        }
        
        with patch('netra_backend.app.config.unified_config_manager.unified_config_manager', mock_config_manager):
            
            agent_state = DeepAgentState(
                agent_id="config_agent",
                session_id="config_session",
                thread_id="config_thread",
                context={"config_driven": True}
            )
            
            agent = SupervisorAgent(
                agent_id="config_test",
                initial_state=agent_state
            )
            
            # Execute workflow that uses configuration
            workflow_request = {
                "task_type": "configurable_analysis",
                "parameters": {"use_system_config": True}
            }
            
            result = await agent._execute_configurable_workflow(workflow_request)
            
            # Verify configuration was applied
            assert result["status"] == "completed"
            assert result["config_applied"] is True
            assert result["execution_time_ms"] <= 300000  # Respected time limit
            
            # Verify feature flags were respected
            assert result["llm_integration_used"] is True  # Flag was enabled
            assert result["experimental_features_used"] is False  # Flag was disabled
            
            # Verify agent configuration was loaded
            mock_config_manager.get_agent_config.assert_called_with("config_agent")
            mock_config_manager.get_feature_flags.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_end_to_end_system_health_integration(self):
        """Test agent workflow integrates with system health monitoring."""
        # Mock health checker
        mock_health_checker = Mock()
        mock_health_checker.check_all = AsyncMock(return_value={
            "postgres": Mock(status="healthy", response_time_ms=50),
            "redis": Mock(status="degraded", response_time_ms=200),
            "clickhouse": Mock(status="healthy", response_time_ms=100),
            "websocket": Mock(status="healthy", response_time_ms=25)
        })
        mock_health_checker.get_overall_health = AsyncMock(return_value={
            "status": "degraded",
            "health_score": 0.75,
            "degraded_services": ["redis"]
        })
        
        with patch('netra_backend.app.core.health_checkers.HealthChecker', return_value=mock_health_checker):
            
            agent_state = DeepAgentState(
                agent_id="health_aware_agent",
                session_id="health_session",
                thread_id="health_thread",
                context={"health_monitoring": True}
            )
            
            agent = SupervisorAgent(
                agent_id="health_integration_test",
                initial_state=agent_state
            )
            
            workflow_request = {
                "task_type": "health_aware_processing",
                "parameters": {
                    "health_checks_enabled": True,
                    "adapt_to_system_health": True
                }
            }
            
            result = await agent._execute_health_aware_workflow(workflow_request)
            
            # Verify health checks were performed
            mock_health_checker.check_all.assert_called_once()
            mock_health_checker.get_overall_health.assert_called_once()
            
            # Verify agent adapted to degraded Redis
            assert result["status"] == "completed"
            assert result["health_adaptations"] == 1
            assert result["redis_fallback_used"] is True
            assert result["performance_adjustments_made"] is True
            
            # Verify health status was included in response
            assert result["system_health_score"] == 0.75
            assert "redis" in result["degraded_services"]