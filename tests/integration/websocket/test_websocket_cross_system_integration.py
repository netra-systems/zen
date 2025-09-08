"""
Integration tests for WebSocket serialization across multiple systems.

This test suite verifies that the WebSocket JSON serialization fix works correctly
in real cross-system integration scenarios with actual service interactions.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: End-to-end System Reliability  
- Value Impact: Ensures WebSocket serialization works in real multi-service scenarios
- Strategic Impact: Prevents production failures in complex system interactions
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from enum import Enum, IntEnum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import time

# Import all the WebSocket-related systems for integration testing
from netra_backend.app.websocket_core.unified_manager import (
    _serialize_message_safely,
    UnifiedWebSocketManager,
    WebSocketConnection
)
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager,
    create_websocket_manager,
    create_defensive_user_execution_context
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


# Integration test data models
class SystemWebSocketState(Enum):
    """WebSocket state for integration testing."""
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 3


class IntegrationAgentStatus(Enum):
    """Agent status for integration testing.""" 
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETING = "completing"
    COMPLETED = "completed"
    ERROR = "error"


class IntegrationToolStatus(IntEnum):
    """Tool execution status for integration testing."""
    QUEUED = 0
    STARTING = 1
    EXECUTING = 2
    SUCCESS = 3
    FAILED = 4


@dataclass
class IntegrationMessage:
    """Integration test message with complex serialization needs."""
    message_id: str
    timestamp: datetime
    source_system: str
    target_system: str
    message_type: str
    payload: Dict[str, Any]
    websocket_state: SystemWebSocketState
    routing_metadata: Dict[str, Any] = None


class MockIntegrationService:
    """Mock service for integration testing."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.websocket_manager = None
        self.message_history = []
        self.error_count = 0
    
    def set_websocket_manager(self, manager):
        """Set the WebSocket manager for this service."""
        self.websocket_manager = manager
    
    async def send_message(self, message: IntegrationMessage) -> bool:
        """Send a message through WebSocket with serialization."""
        try:
            if not self.websocket_manager:
                raise RuntimeError(f"No WebSocket manager configured for {self.service_name}")
            
            # Serialize the message safely
            safe_message = _serialize_message_safely({
                "service": self.service_name,
                "message": message,
                "timestamp": datetime.now(timezone.utc)
            })
            
            # Send through WebSocket manager
            await self.websocket_manager.send_to_user("integration_user", safe_message)
            self.message_history.append(safe_message)
            return True
            
        except Exception as e:
            self.error_count += 1
            raise e
    
    async def process_received_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a received message with serialization verification."""
        # Verify the message is properly serialized
        json.dumps(message_data)  # Should not raise
        
        # Process and return response
        response = {
            "type": "service_response",
            "responding_service": self.service_name,
            "original_message": message_data,
            "response_time": datetime.now(timezone.utc),
            "processing_status": IntegrationAgentStatus.COMPLETED,
            "websocket_state": SystemWebSocketState.CONNECTED
        }
        
        return _serialize_message_safely(response)


class TestIntegrationScenario1_AgentToWebSocketFlow:
    """Integration test: Agent execution -> WebSocket manager -> Client delivery."""
    
    @pytest.fixture
    async def integration_setup(self):
        """Set up integration test environment."""
        # Create WebSocket manager
        manager = UnifiedWebSocketManager()
        
        # Create mock WebSocket connection
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.client_state = SystemWebSocketState.CONNECTED
        
        connection = WebSocketConnection(
            connection_id="integration_conn_001",
            user_id="integration_user",
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await manager.add_connection(connection)
        
        # Create mock agent service
        agent_service = MockIntegrationService("agent_service")
        agent_service.set_websocket_manager(manager)
        
        return {
            "manager": manager,
            "connection": connection,
            "agent_service": agent_service,
            "mock_websocket": mock_websocket
        }
    
    async def test_agent_execution_complete_flow(self, integration_setup):
        """Test complete agent execution flow with WebSocket notifications."""
        setup = integration_setup
        agent_service = setup["agent_service"]
        mock_websocket = setup["mock_websocket"]
        
        # Simulate agent execution lifecycle with complex data
        execution_stages = [
            {
                "stage": "agent_started",
                "data": {
                    "agent_id": "integration_agent_001",
                    "status": IntegrationAgentStatus.INITIALIZING,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "start_time": datetime.now(timezone.utc),
                    "tools": [IntegrationToolStatus.QUEUED, IntegrationToolStatus.QUEUED]
                }
            },
            {
                "stage": "tool_executing",
                "data": {
                    "agent_id": "integration_agent_001", 
                    "status": IntegrationAgentStatus.RUNNING,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "current_tool": {
                        "name": "data_analyzer",
                        "status": IntegrationToolStatus.EXECUTING,
                        "progress": 0.3,
                        "started_at": datetime.now(timezone.utc)
                    },
                    "queue_status": [IntegrationToolStatus.EXECUTING, IntegrationToolStatus.QUEUED]
                }
            },
            {
                "stage": "tool_completed",
                "data": {
                    "agent_id": "integration_agent_001",
                    "status": IntegrationAgentStatus.RUNNING,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "completed_tool": {
                        "name": "data_analyzer",
                        "status": IntegrationToolStatus.SUCCESS,
                        "duration": 2.5,
                        "completed_at": datetime.now(timezone.utc),
                        "results": {
                            "records_processed": 1500,
                            "success_rate": 0.98,
                            "tool_chain_state": SystemWebSocketState.CONNECTED
                        }
                    },
                    "queue_status": [IntegrationToolStatus.SUCCESS, IntegrationToolStatus.EXECUTING]
                }
            },
            {
                "stage": "agent_completed",
                "data": {
                    "agent_id": "integration_agent_001",
                    "status": IntegrationAgentStatus.COMPLETED,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "completion_time": datetime.now(timezone.utc),
                    "final_results": {
                        "success": True,
                        "total_duration": 5.2,
                        "tools_executed": [
                            {
                                "name": "data_analyzer",
                                "status": IntegrationToolStatus.SUCCESS,
                                "duration": 2.5
                            },
                            {
                                "name": "report_generator",
                                "status": IntegrationToolStatus.SUCCESS, 
                                "duration": 2.7
                            }
                        ],
                        "final_state": SystemWebSocketState.CONNECTED
                    }
                }
            }
        ]
        
        # Execute each stage and verify serialization
        for i, stage_info in enumerate(execution_stages):
            message = IntegrationMessage(
                message_id=f"exec_msg_{i:03d}",
                timestamp=datetime.now(timezone.utc),
                source_system="agent_execution_core",
                target_system="websocket_manager", 
                message_type=stage_info["stage"],
                payload=stage_info["data"],
                websocket_state=SystemWebSocketState.CONNECTED,
                routing_metadata={
                    "priority": "high",
                    "user_id": "integration_user",
                    "session_state": SystemWebSocketState.CONNECTED
                }
            )
            
            # Send message through agent service
            success = await agent_service.send_message(message)
            assert success, f"Failed to send message for stage: {stage_info['stage']}"
        
        # Verify all messages were sent
        assert mock_websocket.send_json.call_count == len(execution_stages)
        
        # Verify serialization of each sent message
        for call_index, call in enumerate(mock_websocket.send_json.call_args_list):
            sent_message = call[0][0]
            
            # Verify JSON serializability
            json.dumps(sent_message)
            
            # Verify enum serialization
            message_data = sent_message["message"]
            payload = message_data["payload"]
            
            # Check WebSocket state serialization
            assert message_data["websocket_state"] == 1  # CONNECTED
            
            # Check payload enum serialization
            if "status" in payload:
                assert isinstance(payload["status"], str)  # Agent status enum -> string
            if "websocket_state" in payload:
                assert payload["websocket_state"] == 1  # CONNECTED
            
            # Check nested serialization in tools and results
            if "tools" in payload:
                assert all(isinstance(tool_status, int) for tool_status in payload["tools"])
            if "current_tool" in payload:
                assert isinstance(payload["current_tool"]["status"], int)  # Tool status enum -> int
            if "completed_tool" in payload:
                tool_data = payload["completed_tool"]
                assert isinstance(tool_data["status"], int)
                if "results" in tool_data:
                    assert tool_data["results"]["tool_chain_state"] == 1  # CONNECTED
        
        print(f"✅ Executed {len(execution_stages)} agent lifecycle stages with complex serialization")


class TestIntegrationScenario2_MultiServiceCommunication:
    """Integration test: Multi-service communication through WebSocket bridge."""
    
    @pytest.fixture
    async def multi_service_setup(self):
        """Set up multi-service integration test environment.""" 
        # Create WebSocket manager factory
        factory = WebSocketManagerFactory(max_managers_per_user=10)
        
        # Create user context
        user_context = create_defensive_user_execution_context(
            user_id="multi_service_user",
            websocket_client_id="multi_client_001"
        )
        
        # Create isolated manager
        manager = factory.create_manager(user_context)
        
        # Create mock WebSocket
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.client_state = SystemWebSocketState.CONNECTED
        
        connection = WebSocketConnection(
            connection_id="multi_conn_001",
            user_id="multi_service_user",
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await manager.add_connection(connection)
        
        # Create multiple mock services
        services = {
            "agent_service": MockIntegrationService("agent_service"),
            "data_service": MockIntegrationService("data_service"),
            "auth_service": MockIntegrationService("auth_service"),
            "notification_service": MockIntegrationService("notification_service")
        }
        
        for service in services.values():
            service.set_websocket_manager(manager)
        
        return {
            "factory": factory,
            "manager": manager,
            "user_context": user_context,
            "connection": connection,
            "services": services,
            "mock_websocket": mock_websocket
        }
    
    async def test_cross_service_message_flow(self, multi_service_setup):
        """Test message flow between multiple services with complex serialization.""" 
        setup = multi_service_setup
        services = setup["services"]
        mock_websocket = setup["mock_websocket"]
        
        # Define service interaction flow
        service_flow = [
            {
                "from_service": "agent_service",
                "to_service": "data_service",
                "message_type": "data_request",
                "payload": {
                    "request_id": "data_req_001",
                    "agent_status": IntegrationAgentStatus.RUNNING,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "data_requirements": {
                        "tables": ["users", "transactions"],
                        "filters": {
                            "status": IntegrationAgentStatus.RUNNING,
                            "connection_state": SystemWebSocketState.CONNECTED
                        },
                        "requested_at": datetime.now(timezone.utc)
                    }
                }
            },
            {
                "from_service": "data_service", 
                "to_service": "agent_service",
                "message_type": "data_response",
                "payload": {
                    "request_id": "data_req_001",
                    "status": IntegrationAgentStatus.COMPLETED,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "data_result": {
                        "records_count": 2500,
                        "processing_time": 1.8,
                        "query_status": IntegrationToolStatus.SUCCESS,
                        "connection_state": SystemWebSocketState.CONNECTED,
                        "completed_at": datetime.now(timezone.utc)
                    }
                }
            },
            {
                "from_service": "agent_service",
                "to_service": "auth_service", 
                "message_type": "permission_check",
                "payload": {
                    "user_id": "multi_service_user",
                    "operation": "data_analysis",
                    "agent_status": IntegrationAgentStatus.RUNNING,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "auth_context": {
                        "session_active": True,
                        "connection_state": SystemWebSocketState.CONNECTED,
                        "permissions": ["read", "analyze"],
                        "check_time": datetime.now(timezone.utc)
                    }
                }
            },
            {
                "from_service": "auth_service",
                "to_service": "notification_service",
                "message_type": "security_alert",
                "payload": {
                    "alert_type": "high_privilege_operation",
                    "user_id": "multi_service_user",
                    "operation_status": IntegrationAgentStatus.RUNNING,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "alert_data": {
                        "severity": "medium",
                        "connection_state": SystemWebSocketState.CONNECTED,
                        "alert_time": datetime.now(timezone.utc),
                        "notification_status": IntegrationToolStatus.QUEUED
                    }
                }
            }
        ]
        
        # Execute service flow
        for flow_step in service_flow:
            from_service = services[flow_step["from_service"]]
            
            message = IntegrationMessage(
                message_id=f"flow_{flow_step['from_service']}_{flow_step['to_service']}",
                timestamp=datetime.now(timezone.utc),
                source_system=flow_step["from_service"],
                target_system=flow_step["to_service"],
                message_type=flow_step["message_type"],
                payload=flow_step["payload"],
                websocket_state=SystemWebSocketState.CONNECTED,
                routing_metadata={
                    "flow_id": "multi_service_flow_001",
                    "step_number": len(services),
                    "connection_state": SystemWebSocketState.CONNECTED
                }
            )
            
            # Send message
            success = await from_service.send_message(message)
            assert success, f"Failed to send message from {flow_step['from_service']} to {flow_step['to_service']}"
        
        # Verify all messages sent successfully
        assert mock_websocket.send_json.call_count == len(service_flow)
        
        # Verify serialization of cross-service messages
        for call_index, call in enumerate(mock_websocket.send_json.call_args_list):
            sent_message = call[0][0]
            flow_step = service_flow[call_index]
            
            # Verify JSON serializability
            json.dumps(sent_message)
            
            # Verify service-specific serialization
            message_data = sent_message["message"]
            payload = message_data["payload"]
            
            # Check enum serialization in payload
            for key, value in payload.items():
                if isinstance(value, IntegrationAgentStatus):
                    assert isinstance(payload[key], str)
                elif isinstance(value, SystemWebSocketState):
                    assert isinstance(payload[key], int)
                elif isinstance(value, IntegrationToolStatus):
                    assert isinstance(payload[key], int)
                elif isinstance(value, dict):
                    # Check nested enum serialization
                    for nested_key, nested_value in value.items():
                        if "status" in nested_key and isinstance(nested_value, Enum):
                            assert not isinstance(value[nested_key], Enum), "Nested enum should be serialized"
                        elif "state" in nested_key and isinstance(nested_value, Enum):
                            assert not isinstance(value[nested_key], Enum), "Nested state should be serialized"
        
        print(f"✅ Executed {len(service_flow)} cross-service communications with complex serialization")
    
    async def test_concurrent_service_operations(self, multi_service_setup):
        """Test concurrent operations across services with WebSocket serialization."""
        setup = multi_service_setup
        services = setup["services"]
        mock_websocket = setup["mock_websocket"]
        
        # Create concurrent operations
        async def service_operation(service_name: str, operation_id: int):
            """Simulate a service operation with complex data."""
            service = services[service_name]
            
            message = IntegrationMessage(
                message_id=f"concurrent_{service_name}_{operation_id:03d}",
                timestamp=datetime.now(timezone.utc),
                source_system=service_name,
                target_system="websocket_manager",
                message_type="concurrent_operation",
                payload={
                    "operation_id": operation_id,
                    "service": service_name,
                    "status": IntegrationAgentStatus.RUNNING,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "operation_data": {
                        "start_time": datetime.now(timezone.utc),
                        "tool_status": IntegrationToolStatus.EXECUTING,
                        "connection_state": SystemWebSocketState.CONNECTED,
                        "nested_enums": [
                            IntegrationAgentStatus.INITIALIZING,
                            IntegrationAgentStatus.RUNNING,
                            IntegrationAgentStatus.COMPLETING
                        ],
                        "state_transitions": [
                            SystemWebSocketState.CONNECTING,
                            SystemWebSocketState.CONNECTED
                        ]
                    }
                },
                websocket_state=SystemWebSocketState.CONNECTED,
                routing_metadata={
                    "concurrent_batch": "batch_001",
                    "operation_index": operation_id,
                    "connection_state": SystemWebSocketState.CONNECTED
                }
            )
            
            await service.send_message(message)
            return f"{service_name}_{operation_id}"
        
        # Create concurrent tasks
        tasks = []
        operations_per_service = 5
        
        for service_name in services.keys():
            for operation_id in range(operations_per_service):
                task = service_operation(service_name, operation_id)
                tasks.append(task)
        
        # Execute concurrent operations
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Verify all operations completed
        successful_operations = [r for r in results if not isinstance(r, Exception)]
        failed_operations = [r for r in results if isinstance(r, Exception)]
        
        assert len(failed_operations) == 0, f"Some operations failed: {failed_operations}"
        assert len(successful_operations) == len(services) * operations_per_service
        
        # Verify all messages were sent
        expected_message_count = len(services) * operations_per_service
        assert mock_websocket.send_json.call_count == expected_message_count
        
        # Verify serialization integrity under concurrent load
        for call in mock_websocket.send_json.call_args_list:
            sent_message = call[0][0]
            
            # Each message should be JSON serializable
            json.dumps(sent_message)
            
            # Verify enum serialization in concurrent messages
            message_data = sent_message["message"]
            payload = message_data["payload"]
            operation_data = payload["operation_data"]
            
            # Check enum array serialization
            nested_enums = operation_data["nested_enums"]
            assert all(isinstance(status, str) for status in nested_enums)
            
            # Check state transitions serialization
            state_transitions = operation_data["state_transitions"]
            assert all(isinstance(state, int) for state in state_transitions)
            assert state_transitions == [0, 1]  # CONNECTING, CONNECTED
        
        print(f"✅ Executed {len(successful_operations)} concurrent operations in {execution_time:.3f}s")


class TestIntegrationScenario3_ErrorHandlingAndRecovery:
    """Integration test: Error handling and recovery with WebSocket serialization."""
    
    @pytest.fixture
    async def error_recovery_setup(self):
        """Set up error recovery integration test environment."""
        manager = UnifiedWebSocketManager()
        
        # Create connections with different states for testing
        connections = {}
        mock_websockets = {}
        
        for i, state in enumerate([SystemWebSocketState.CONNECTED, SystemWebSocketState.CONNECTING]):
            mock_ws = Mock()
            mock_ws.send_json = AsyncMock()
            mock_ws.client_state = state
            
            # Simulate connection failures for some connections
            if i == 1:  # Second connection fails
                mock_ws.send_json.side_effect = Exception("Connection lost")
            
            conn_id = f"error_conn_{i:03d}"
            connection = WebSocketConnection(
                connection_id=conn_id,
                user_id="error_test_user", 
                websocket=mock_ws,
                connected_at=datetime.now(timezone.utc) - timedelta(minutes=i)
            )
            
            await manager.add_connection(connection)
            connections[conn_id] = connection
            mock_websockets[conn_id] = mock_ws
        
        return {
            "manager": manager,
            "connections": connections,
            "mock_websockets": mock_websockets
        }
    
    async def test_error_handling_with_complex_serialization(self, error_recovery_setup):
        """Test error handling maintains serialization integrity."""
        setup = error_recovery_setup
        manager = setup["manager"]
        mock_websockets = setup["mock_websockets"]
        
        # Create error scenarios with complex data
        error_scenarios = [
            {
                "scenario": "serialization_error_recovery",
                "message": {
                    "type": "error_test",
                    "error_data": {
                        "error_type": "serialization_failure",
                        "failed_objects": [
                            {
                                "object_type": "agent_state",
                                "status": IntegrationAgentStatus.ERROR,
                                "websocket_state": SystemWebSocketState.DISCONNECTED,
                                "error_time": datetime.now(timezone.utc)
                            }
                        ],
                        "recovery_attempts": [
                            {
                                "attempt": 1,
                                "status": IntegrationToolStatus.FAILED,
                                "connection_state": SystemWebSocketState.DISCONNECTED
                            },
                            {
                                "attempt": 2,
                                "status": IntegrationToolStatus.SUCCESS,
                                "connection_state": SystemWebSocketState.CONNECTED
                            }
                        ]
                    }
                }
            },
            {
                "scenario": "connection_failure_recovery",
                "message": {
                    "type": "connection_recovery",
                    "recovery_data": {
                        "failed_connections": ["error_conn_001"],
                        "recovery_state": SystemWebSocketState.CONNECTING,
                        "recovery_time": datetime.now(timezone.utc),
                        "fallback_data": {
                            "agent_status": IntegrationAgentStatus.RUNNING,
                            "tool_states": [
                                IntegrationToolStatus.SUCCESS,
                                IntegrationToolStatus.EXECUTING,
                                IntegrationToolStatus.QUEUED
                            ],
                            "websocket_state": SystemWebSocketState.CONNECTED
                        }
                    }
                }
            }
        ]
        
        for scenario in error_scenarios:
            scenario_name = scenario["scenario"]
            message = scenario["message"]
            
            # Attempt to send message through manager
            try:
                await manager.send_to_user("error_test_user", message)
            except Exception as e:
                # Some connections may fail, but serialization should not be the cause
                assert "JSON serializable" not in str(e), f"Serialization error in {scenario_name}: {e}"
                assert "not JSON serializable" not in str(e), f"Serialization error in {scenario_name}: {e}"
        
        # Verify successful connections received serialized messages
        successful_websockets = [ws for ws in mock_websockets.values() if not ws.send_json.side_effect]
        
        for ws in successful_websockets:
            if ws.send_json.called:
                for call in ws.send_json.call_args_list:
                    sent_message = call[0][0]
                    
                    # Verify message is JSON serializable
                    json.dumps(sent_message)
                    
                    # Verify enum serialization in error/recovery data
                    if "error_data" in sent_message:
                        error_data = sent_message["error_data"]
                        if "failed_objects" in error_data:
                            for failed_obj in error_data["failed_objects"]:
                                assert isinstance(failed_obj["status"], str)  # Agent status
                                assert isinstance(failed_obj["websocket_state"], int)  # WebSocket state
                        if "recovery_attempts" in error_data:
                            for attempt in error_data["recovery_attempts"]:
                                assert isinstance(attempt["status"], int)  # Tool status
                                assert isinstance(attempt["connection_state"], int)  # WebSocket state
                    
                    if "recovery_data" in sent_message:
                        recovery_data = sent_message["recovery_data"]
                        if "fallback_data" in recovery_data:
                            fallback = recovery_data["fallback_data"]
                            assert isinstance(fallback["agent_status"], str)
                            assert isinstance(fallback["websocket_state"], int)
                            assert all(isinstance(tool_state, int) for tool_state in fallback["tool_states"])
        
        print("✅ Error handling maintained serialization integrity across failure scenarios")


class TestIntegrationScenario4_PerformanceUnderLoad:
    """Integration test: Performance testing with high message volume and complex serialization."""
    
    async def test_high_volume_serialization_performance(self):
        """Test WebSocket serialization performance under high message volume."""
        # Create WebSocket manager
        manager = UnifiedWebSocketManager()
        
        # Create multiple connections
        connections = []
        mock_websockets = []
        
        connection_count = 10
        for i in range(connection_count):
            mock_ws = Mock()
            mock_ws.send_json = AsyncMock()
            mock_ws.client_state = SystemWebSocketState.CONNECTED
            mock_websockets.append(mock_ws)
            
            connection = WebSocketConnection(
                connection_id=f"perf_conn_{i:03d}",
                user_id=f"perf_user_{i:03d}",
                websocket=mock_ws,
                connected_at=datetime.now(timezone.utc)
            )
            
            await manager.add_connection(connection)
            connections.append(connection)
        
        # Generate high-volume messages with complex serialization
        messages_per_user = 100
        total_messages = connection_count * messages_per_user
        
        async def send_user_messages(user_id: str, user_index: int):
            """Send messages to a specific user."""
            user_messages = []
            
            for msg_index in range(messages_per_user):
                complex_message = {
                    "type": "performance_test",
                    "message_id": f"perf_{user_index:03d}_{msg_index:04d}",
                    "timestamp": datetime.now(timezone.utc),
                    "user_data": {
                        "user_id": user_id,
                        "status": IntegrationAgentStatus.RUNNING,
                        "websocket_state": SystemWebSocketState.CONNECTED,
                        "agent_data": [
                            {
                                "agent_id": f"perf_agent_{j:03d}",
                                "status": IntegrationAgentStatus.RUNNING if j % 2 == 0 else IntegrationAgentStatus.PENDING,
                                "tools": [
                                    IntegrationToolStatus.SUCCESS,
                                    IntegrationToolStatus.EXECUTING,
                                    IntegrationToolStatus.QUEUED
                                ],
                                "websocket_state": SystemWebSocketState.CONNECTED,
                                "created_at": datetime.now(timezone.utc)
                            } for j in range(5)  # 5 agents per message
                        ],
                        "state_history": [SystemWebSocketState.CONNECTING, SystemWebSocketState.CONNECTED] * 10,  # 20 states
                        "performance_metadata": {
                            "batch_id": f"batch_{user_index:03d}",
                            "message_index": msg_index,
                            "enum_count": 25,  # Approximate enum objects in message
                            "connection_state": SystemWebSocketState.CONNECTED
                        }
                    }
                }
                
                user_messages.append(complex_message)
            
            # Send all messages for this user
            for message in user_messages:
                await manager.send_to_user(user_id, message)
        
        # Execute performance test
        start_time = time.time()
        
        tasks = []
        for i, connection in enumerate(connections):
            task = send_user_messages(connection.user_id, i)
            tasks.append(task)
        
        # Execute all message sending concurrently
        await asyncio.gather(*tasks)
        
        execution_time = time.time() - start_time
        
        # Verify performance metrics
        messages_per_second = total_messages / execution_time
        
        # Verify all messages were sent and properly serialized
        total_sent_messages = sum(ws.send_json.call_count for ws in mock_websockets)
        assert total_sent_messages == total_messages, f"Expected {total_messages}, got {total_sent_messages}"
        
        # Verify serialization quality by checking sample messages
        sample_checks = 0
        max_sample_checks = 50  # Don't check every message for performance
        
        for ws in mock_websockets[:5]:  # Check first 5 websockets
            for call in ws.send_json.call_args_list[:10]:  # Check first 10 messages per websocket
                sent_message = call[0][0]
                
                # Verify JSON serializability
                json.dumps(sent_message)
                
                # Verify complex enum serialization
                user_data = sent_message["user_data"]
                assert isinstance(user_data["status"], str)  # Agent status
                assert isinstance(user_data["websocket_state"], int)  # WebSocket state
                
                # Check agent data array serialization
                for agent_data in user_data["agent_data"]:
                    assert isinstance(agent_data["status"], str)
                    assert isinstance(agent_data["websocket_state"], int)
                    assert all(isinstance(tool_status, int) for tool_status in agent_data["tools"])
                
                # Check state history serialization
                assert all(isinstance(state, int) for state in user_data["state_history"])
                
                sample_checks += 1
                if sample_checks >= max_sample_checks:
                    break
            
            if sample_checks >= max_sample_checks:
                break
        
        # Performance assertions
        assert execution_time < 10.0, f"Performance test took {execution_time:.3f}s, expected < 10.0s"
        assert messages_per_second > 100, f"Message rate {messages_per_second:.1f}/sec, expected > 100/sec"
        
        print(f"✅ Performance test: {total_messages} messages in {execution_time:.3f}s ({messages_per_second:.1f} msg/sec)")
        print(f"✅ Verified serialization integrity for {sample_checks} complex messages")


class TestIntegrationScenario5_RealWorldComplexity:
    """Integration test: Real-world complexity scenarios with full system integration."""
    
    async def test_complete_user_session_flow(self):
        """Test complete user session with realistic complexity and serialization needs."""
        # Set up complete integration environment
        factory = WebSocketManagerFactory(max_managers_per_user=5)
        
        # Create user context for realistic session
        user_context = create_defensive_user_execution_context(
            user_id="session_user_001",
            websocket_client_id="session_client_001"
        )
        
        manager = factory.create_manager(user_context)
        
        # Create WebSocket connection
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.client_state = SystemWebSocketState.CONNECTED
        
        connection = WebSocketConnection(
            connection_id="session_conn_001",
            user_id="session_user_001",
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await manager.add_connection(connection)
        
        # Simulate realistic user session flow
        session_events = [
            {
                "event": "user_login",
                "data": {
                    "user_id": "session_user_001",
                    "login_time": datetime.now(timezone.utc),
                    "auth_status": IntegrationAgentStatus.COMPLETED,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "session_data": {
                        "session_id": "session_001",
                        "auth_method": "oauth",
                        "permissions": ["read", "write", "execute"],
                        "connection_quality": SystemWebSocketState.CONNECTED
                    }
                }
            },
            {
                "event": "agent_request",
                "data": {
                    "request_id": "req_001",
                    "request_type": "data_analysis",
                    "user_query": "Analyze customer behavior patterns",
                    "agent_status": IntegrationAgentStatus.INITIALIZING,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "request_metadata": {
                        "priority": "high",
                        "estimated_duration": 300,  # 5 minutes
                        "required_tools": [
                            {
                                "tool": "data_fetcher",
                                "status": IntegrationToolStatus.QUEUED
                            },
                            {
                                "tool": "pattern_analyzer",
                                "status": IntegrationToolStatus.QUEUED
                            },
                            {
                                "tool": "report_generator",
                                "status": IntegrationToolStatus.QUEUED
                            }
                        ],
                        "connection_state": SystemWebSocketState.CONNECTED
                    }
                }
            },
            {
                "event": "agent_processing",
                "data": {
                    "request_id": "req_001",
                    "agent_status": IntegrationAgentStatus.RUNNING,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "processing_details": {
                        "current_step": "data_fetching",
                        "progress": 0.25,
                        "active_tools": [
                            {
                                "tool": "data_fetcher",
                                "status": IntegrationToolStatus.EXECUTING,
                                "progress": 0.8,
                                "estimated_completion": datetime.now(timezone.utc) + timedelta(seconds=30)
                            }
                        ],
                        "queued_tools": [
                            {
                                "tool": "pattern_analyzer", 
                                "status": IntegrationToolStatus.QUEUED,
                                "estimated_start": datetime.now(timezone.utc) + timedelta(seconds=45)
                            },
                            {
                                "tool": "report_generator",
                                "status": IntegrationToolStatus.QUEUED,
                                "estimated_start": datetime.now(timezone.utc) + timedelta(seconds=200)
                            }
                        ],
                        "connection_state": SystemWebSocketState.CONNECTED,
                        "real_time_metrics": {
                            "cpu_usage": 0.65,
                            "memory_usage": 0.42,
                            "websocket_latency": 0.023,
                            "connection_stability": SystemWebSocketState.CONNECTED
                        }
                    }
                }
            },
            {
                "event": "intermediate_results",
                "data": {
                    "request_id": "req_001",
                    "agent_status": IntegrationAgentStatus.RUNNING,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "partial_results": {
                        "data_fetched": {
                            "records_count": 15000,
                            "fetch_duration": 28.5,
                            "status": IntegrationToolStatus.SUCCESS,
                            "connection_state": SystemWebSocketState.CONNECTED
                        },
                        "analysis_preview": {
                            "patterns_detected": 7,
                            "confidence_scores": [0.92, 0.87, 0.93, 0.78, 0.95, 0.82, 0.89],
                            "analysis_status": IntegrationToolStatus.EXECUTING,
                            "websocket_state": SystemWebSocketState.CONNECTED,
                            "intermediate_timestamp": datetime.now(timezone.utc)
                        }
                    }
                }
            },
            {
                "event": "agent_completion",
                "data": {
                    "request_id": "req_001",
                    "agent_status": IntegrationAgentStatus.COMPLETED,
                    "websocket_state": SystemWebSocketState.CONNECTED,
                    "completion_time": datetime.now(timezone.utc),
                    "final_results": {
                        "success": True,
                        "total_duration": 287.3,
                        "results_summary": {
                            "patterns_found": 7,
                            "customer_segments": 4,
                            "key_insights": [
                                "High-value customers prefer weekend purchases",
                                "Mobile app usage correlates with loyalty",
                                "Seasonal patterns in product preferences"
                            ],
                            "data_quality": {
                                "completeness": 0.96,
                                "accuracy": 0.94,
                                "freshness": "current"
                            }
                        },
                        "tool_execution_summary": [
                            {
                                "tool": "data_fetcher",
                                "status": IntegrationToolStatus.SUCCESS,
                                "duration": 28.5,
                                "records_processed": 15000
                            },
                            {
                                "tool": "pattern_analyzer", 
                                "status": IntegrationToolStatus.SUCCESS,
                                "duration": 156.8,
                                "patterns_analyzed": 7
                            },
                            {
                                "tool": "report_generator",
                                "status": IntegrationToolStatus.SUCCESS,
                                "duration": 102.0,
                                "report_pages": 12
                            }
                        ],
                        "final_state": {
                            "agent_status": IntegrationAgentStatus.COMPLETED,
                            "websocket_state": SystemWebSocketState.CONNECTED,
                            "session_active": True
                        }
                    }
                }
            },
            {
                "event": "user_logout",
                "data": {
                    "user_id": "session_user_001",
                    "logout_time": datetime.now(timezone.utc),
                    "session_duration": 420.7,  # 7 minutes
                    "logout_status": IntegrationAgentStatus.COMPLETED,
                    "websocket_state": SystemWebSocketState.DISCONNECTED,
                    "session_summary": {
                        "requests_completed": 1,
                        "total_processing_time": 287.3,
                        "connection_quality": "stable",
                        "final_connection_state": SystemWebSocketState.DISCONNECTED
                    }
                }
            }
        ]
        
        # Execute complete session flow
        for event_info in session_events:
            await manager.emit_critical_event(event_info["event"], event_info["data"])
        
        # Verify all session events were sent
        assert mock_websocket.send_json.call_count == len(session_events)
        
        # Verify complex serialization for each event
        for i, call in enumerate(mock_websocket.send_json.call_args_list):
            sent_message = call[0][0]
            event_info = session_events[i]
            
            # Verify JSON serializability
            json.dumps(sent_message)
            
            # Verify critical event structure
            assert sent_message["type"] == event_info["event"]
            assert "data" in sent_message
            assert "timestamp" in sent_message
            assert sent_message["critical"] is True
            
            event_data = sent_message["data"]
            
            # Verify enum serialization based on event type
            if "auth_status" in event_data:
                assert isinstance(event_data["auth_status"], str)
            if "agent_status" in event_data:
                assert isinstance(event_data["agent_status"], str)
            if "websocket_state" in event_data:
                assert isinstance(event_data["websocket_state"], int)
            
            # Verify nested complex serialization
            if "processing_details" in event_data:
                details = event_data["processing_details"]
                if "active_tools" in details:
                    for tool in details["active_tools"]:
                        assert isinstance(tool["status"], int)  # Tool status enum
                if "queued_tools" in details:
                    for tool in details["queued_tools"]:
                        assert isinstance(tool["status"], int)
                if "real_time_metrics" in details:
                    metrics = details["real_time_metrics"]
                    assert isinstance(metrics["connection_stability"], int)
            
            # Verify tool execution summary serialization
            if "tool_execution_summary" in event_data.get("final_results", {}):
                tools_summary = event_data["final_results"]["tool_execution_summary"]
                for tool_info in tools_summary:
                    assert isinstance(tool_info["status"], int)  # Tool status enum
        
        print(f"✅ Complete user session flow: {len(session_events)} events with complex real-world serialization")


# Run integration tests
if __name__ == "__main__":
    async def run_integration_tests():
        """Run all integration tests."""
        print("Running WebSocket Cross-System Integration Tests...")
        
        # Quick smoke test
        test_data = {
            "websocket_state": SystemWebSocketState.CONNECTED,
            "agent_status": IntegrationAgentStatus.RUNNING,
            "tool_status": IntegrationToolStatus.EXECUTING,
            "timestamp": datetime.now(timezone.utc),
            "complex_nested": {
                "states": [SystemWebSocketState.CONNECTING, SystemWebSocketState.CONNECTED],
                "statuses": [IntegrationAgentStatus.PENDING, IntegrationAgentStatus.RUNNING]
            }
        }
        
        safe_data = _serialize_message_safely(test_data)
        json_output = json.dumps(safe_data)
        
        print(f"✅ Integration smoke test passed: {len(json_output)} characters")
        print("✅ All cross-system WebSocket serialization integration tests ready!")
    
    asyncio.run(run_integration_tests())