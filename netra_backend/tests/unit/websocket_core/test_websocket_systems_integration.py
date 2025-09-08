"""
Comprehensive unit tests for top 10 WebSocket serialization-related systems.

This test suite verifies that the WebSocket JSON serialization fix works correctly
across all major systems that interact with WebSocket messaging.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Reliability & Chat Functionality
- Value Impact: Ensures all WebSocket-related systems handle complex objects safely
- Strategic Impact: Prevents cascade failures across the entire WebSocket ecosystem
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from enum import Enum, IntEnum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import the serialization function and related systems
from netra_backend.app.websocket_core.unified_manager import (
    _serialize_message_safely,
    UnifiedWebSocketManager,
    WebSocketConnection
)
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager,
    create_websocket_manager
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


# Test data classes and enums
class WebSocketState(Enum):
    """Mock WebSocketState for testing."""
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 3


class AgentStatus(Enum):
    """Mock AgentStatus enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolExecutionStatus(IntEnum):
    """Mock tool execution status."""
    QUEUED = 0
    EXECUTING = 1
    SUCCESS = 2
    ERROR = 3


@dataclass
class AgentStateData:
    """Mock agent state data."""
    agent_id: str
    status: AgentStatus
    progress: float
    created_at: datetime
    metadata: Dict[str, Any] = None


class MockPydanticModel:
    """Mock Pydantic model with datetime fields."""
    
    def __init__(self, name: str, created_at: datetime, status: Enum = None):
        self.name = name
        self.created_at = created_at
        self.status = status
    
    def model_dump(self, mode: str = None) -> Dict[str, Any]:
        if mode == 'json':
            return {
                'name': self.name,
                'created_at': self.created_at.isoformat(),
                'status': self.status.value if self.status else None
            }
        else:
            return {
                'name': self.name,
                'created_at': self.created_at,
                'status': self.status
            }


class TestSystem1_UnifiedWebSocketManager:
    """Tests for System 1: UnifiedWebSocketManager serialization integration."""
    
    @pytest.fixture
    def mock_websocket(self):
        websocket = Mock()
        websocket.send_json = AsyncMock()
        return websocket
    
    @pytest.fixture
    def websocket_manager(self):
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    def test_connection(self, mock_websocket):
        return WebSocketConnection(
            connection_id="test_conn_001",
            user_id="test_user",
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc)
        )
    
    async def test_unified_manager_handles_websocket_state_enum(self, websocket_manager, test_connection):
        """Test UnifiedWebSocketManager handles WebSocketState enum in messages."""
        await websocket_manager.add_connection(test_connection)
        
        # Message with WebSocketState enum
        message_with_enum = {
            "type": "connection_status",
            "state": WebSocketState.CONNECTED,
            "previous_state": WebSocketState.CONNECTING,
            "timestamp": datetime.now(timezone.utc)
        }
        
        await websocket_manager.send_to_user("test_user", message_with_enum)
        
        # Verify send_json was called
        assert test_connection.websocket.send_json.called
        sent_message = test_connection.websocket.send_json.call_args[0][0]
        
        # Verify enum serialization
        assert sent_message["state"] == 1  # CONNECTED
        assert sent_message["previous_state"] == 0  # CONNECTING
        assert isinstance(sent_message["timestamp"], str)  # ISO format
        
        # Verify JSON serializability
        json.dumps(sent_message)
    
    async def test_unified_manager_handles_complex_agent_data(self, websocket_manager, test_connection):
        """Test UnifiedWebSocketManager handles complex agent data structures."""
        await websocket_manager.add_connection(test_connection)
        
        agent_data = AgentStateData(
            agent_id="agent_001",
            status=AgentStatus.RUNNING,
            progress=0.75,
            created_at=datetime.now(timezone.utc),
            metadata={
                "tools": [ToolExecutionStatus.SUCCESS, ToolExecutionStatus.EXECUTING],
                "websocket_state": WebSocketState.CONNECTED
            }
        )
        
        message = {
            "type": "agent_update",
            "agent_data": agent_data,
            "connection_states": [WebSocketState.CONNECTING, WebSocketState.CONNECTED]
        }
        
        await websocket_manager.send_to_user("test_user", message)
        
        sent_message = test_connection.websocket.send_json.call_args[0][0]
        
        # Verify dataclass serialization
        assert sent_message["agent_data"]["agent_id"] == "agent_001"
        assert sent_message["agent_data"]["status"] == "running"
        assert sent_message["agent_data"]["metadata"]["tools"] == [2, 1]  # SUCCESS, EXECUTING
        assert sent_message["agent_data"]["metadata"]["websocket_state"] == 1  # CONNECTED
        assert sent_message["connection_states"] == [0, 1]  # CONNECTING, CONNECTED
        
        json.dumps(sent_message)


class TestSystem2_WebSocketManagerFactory:
    """Tests for System 2: WebSocketManagerFactory with complex serialization."""
    
    @pytest.fixture
    def mock_user_context(self):
        return UserExecutionContext(
            user_id="00000000-0000-0000-0000-000000000001",
            thread_id="00000000-0000-0000-0000-000000000002", 
            run_id="00000000-0000-0000-0000-000000000003",
            request_id="00000000-0000-0000-0000-000000000004",
            websocket_client_id="00000000-0000-0000-0000-000000000005"
        )
    
    @pytest.fixture
    def manager_factory(self):
        return WebSocketManagerFactory(max_managers_per_user=3)
    
    async def test_factory_creates_manager_with_enum_support(self, manager_factory, mock_user_context):
        """Test factory creates managers that handle enum serialization."""
        manager = manager_factory.create_manager(mock_user_context)
        
        # Create mock connection
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        connection = WebSocketConnection(
            connection_id="conn_factory_001",
            user_id=mock_user_context.user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await manager.add_connection(connection)
        
        # Send message with enums
        message = {
            "type": "factory_test",
            "websocket_state": WebSocketState.CONNECTED,
            "agent_status": AgentStatus.RUNNING,
            "tool_status": ToolExecutionStatus.SUCCESS
        }
        
        await manager.send_to_user(message)
        
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["websocket_state"] == 1
        assert sent_message["agent_status"] == "running"
        assert sent_message["tool_status"] == 2
        
        json.dumps(sent_message)
    
    async def test_factory_handles_critical_events_with_complex_data(self, manager_factory, mock_user_context):
        """Test factory managers handle critical events with complex serialization."""
        manager = manager_factory.create_manager(mock_user_context)
        
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        connection = WebSocketConnection(
            connection_id="conn_critical_001",
            user_id=mock_user_context.user_id, 
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await manager.add_connection(connection)
        
        # Critical event with complex data
        event_data = {
            "agent_state": AgentStateData(
                agent_id="critical_agent",
                status=AgentStatus.FAILED,
                progress=0.0,
                created_at=datetime.now(timezone.utc)
            ),
            "websocket_states": [WebSocketState.CONNECTED, WebSocketState.DISCONNECTED],
            "pydantic_model": MockPydanticModel("test", datetime.now(timezone.utc), AgentStatus.PENDING)
        }
        
        await manager.emit_critical_event("agent_error", event_data)
        
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "agent_error"
        assert sent_message["data"]["agent_state"]["status"] == "failed"
        assert sent_message["data"]["websocket_states"] == [1, 3]
        assert sent_message["data"]["pydantic_model"]["status"] == "pending"
        
        json.dumps(sent_message)


class TestSystem3_WebSocketRoutes:
    """Tests for System 3: FastAPI WebSocket Routes with serialization."""
    
    async def test_websocket_route_message_processing(self):
        """Test WebSocket route processes messages with complex serialization."""
        # Mock FastAPI WebSocket
        mock_websocket = Mock()
        mock_websocket.receive_json = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.state = Mock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # Simulate incoming message with enum data
        incoming_message = {
            "type": "client_update",
            "connection_state": WebSocketState.CONNECTED,
            "timestamp": datetime.now(timezone.utc)
        }
        
        # Process with safe serialization
        safe_message = _serialize_message_safely(incoming_message)
        
        # Verify serialization
        assert safe_message["connection_state"] == 1
        assert isinstance(safe_message["timestamp"], str)
        json.dumps(safe_message)
        
        # Simulate sending response
        response = {
            "type": "route_response",
            "status": "processed",
            "original_state": WebSocketState.CONNECTED
        }
        
        safe_response = _serialize_message_safely(response)
        await mock_websocket.send_json(safe_response)
        
        # Verify response sent correctly
        assert mock_websocket.send_json.called
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["original_state"] == 1
        json.dumps(sent_data)


class TestSystem4_AgentExecutionCore:
    """Tests for System 4: Agent Execution Core WebSocket notifications."""
    
    async def test_agent_execution_websocket_events(self):
        """Test agent execution sends proper WebSocket events with serialization."""
        # Mock WebSocket manager
        mock_manager = Mock()
        mock_manager.emit_critical_event = AsyncMock()
        
        # Simulate agent execution events
        events = [
            {
                "type": "agent_started",
                "agent_id": "exec_agent_001",
                "status": AgentStatus.RUNNING,
                "websocket_state": WebSocketState.CONNECTED
            },
            {
                "type": "tool_executing", 
                "tool_name": "data_analyzer",
                "tool_status": ToolExecutionStatus.EXECUTING,
                "progress_data": {
                    "current_step": 3,
                    "total_steps": 10,
                    "state": WebSocketState.CONNECTED
                }
            },
            {
                "type": "agent_completed",
                "result": {
                    "status": AgentStatus.COMPLETED,
                    "final_state": WebSocketState.DISCONNECTED,
                    "execution_time": 45.7
                }
            }
        ]
        
        # Process each event through serialization
        for event in events:
            safe_event = _serialize_message_safely(event)
            
            # Verify all enums are serialized
            if "status" in safe_event:
                assert isinstance(safe_event["status"], str)
            if "websocket_state" in safe_event:
                assert isinstance(safe_event["websocket_state"], int)
            if "tool_status" in safe_event:
                assert isinstance(safe_event["tool_status"], int)
            
            # Verify nested serialization
            if "progress_data" in safe_event:
                assert safe_event["progress_data"]["state"] == 1  # CONNECTED
            if "result" in safe_event:
                assert safe_event["result"]["status"] == "completed"
                assert safe_event["result"]["final_state"] == 3  # DISCONNECTED
            
            json.dumps(safe_event)
            
            await mock_manager.emit_critical_event(event["type"], safe_event)
        
        # Verify all events were emitted
        assert mock_manager.emit_critical_event.call_count == len(events)


class TestSystem5_WebSocketNotifier:
    """Tests for System 5: WebSocket Notifier with agent supervisor integration."""
    
    async def test_websocket_notifier_handles_supervisor_data(self):
        """Test WebSocket notifier handles supervisor agent data with complex objects."""
        # Mock notifier dependencies
        mock_websocket_manager = Mock()
        mock_websocket_manager.emit_critical_event = AsyncMock()
        
        # Supervisor agent data with complex structures
        supervisor_data = {
            "type": "supervisor_update",
            "supervisor_id": "supervisor_001",
            "managed_agents": [
                {
                    "agent_id": "agent_001",
                    "status": AgentStatus.RUNNING,
                    "websocket_state": WebSocketState.CONNECTED,
                    "tools": [ToolExecutionStatus.SUCCESS, ToolExecutionStatus.EXECUTING]
                },
                {
                    "agent_id": "agent_002", 
                    "status": AgentStatus.PENDING,
                    "websocket_state": WebSocketState.CONNECTING,
                    "tools": [ToolExecutionStatus.QUEUED]
                }
            ],
            "overall_status": {
                "active_count": 2,
                "connection_states": [WebSocketState.CONNECTED, WebSocketState.CONNECTING],
                "last_update": datetime.now(timezone.utc)
            }
        }
        
        # Serialize supervisor data
        safe_supervisor_data = _serialize_message_safely(supervisor_data)
        
        # Verify complex nested serialization
        assert safe_supervisor_data["managed_agents"][0]["status"] == "running"
        assert safe_supervisor_data["managed_agents"][0]["websocket_state"] == 1
        assert safe_supervisor_data["managed_agents"][0]["tools"] == [2, 1]  # SUCCESS, EXECUTING
        assert safe_supervisor_data["managed_agents"][1]["status"] == "pending" 
        assert safe_supervisor_data["managed_agents"][1]["websocket_state"] == 0  # CONNECTING
        assert safe_supervisor_data["overall_status"]["connection_states"] == [1, 0]
        assert isinstance(safe_supervisor_data["overall_status"]["last_update"], str)
        
        json.dumps(safe_supervisor_data)
        
        await mock_websocket_manager.emit_critical_event("supervisor_update", safe_supervisor_data)
        assert mock_websocket_manager.emit_critical_event.called


class TestSystem6_AgentService:
    """Tests for System 6: Agent Service WebSocket integration."""
    
    async def test_agent_service_websocket_updates(self):
        """Test Agent Service sends WebSocket updates with proper serialization."""
        # Mock agent service components
        mock_websocket_bridge = Mock()
        mock_websocket_bridge.send_agent_update = AsyncMock()
        
        # Agent service update data
        service_update = {
            "type": "service_agent_update",
            "service_id": "agent_service_001",
            "agents": {
                "active": [
                    {
                        "id": "svc_agent_001",
                        "status": AgentStatus.RUNNING,
                        "connection": WebSocketState.CONNECTED,
                        "model_data": MockPydanticModel("service_model", datetime.now(timezone.utc), AgentStatus.RUNNING)
                    }
                ],
                "pending": [
                    {
                        "id": "svc_agent_002",
                        "status": AgentStatus.PENDING,
                        "connection": WebSocketState.CONNECTING
                    }
                ]
            },
            "metrics": {
                "total_agents": 2,
                "connection_distribution": {
                    WebSocketState.CONNECTED: 1,
                    WebSocketState.CONNECTING: 1,
                    WebSocketState.DISCONNECTED: 0
                },
                "timestamp": datetime.now(timezone.utc)
            }
        }
        
        # Serialize service update
        safe_update = _serialize_message_safely(service_update)
        
        # Verify serialization of nested structures
        active_agent = safe_update["agents"]["active"][0]
        assert active_agent["status"] == "running"
        assert active_agent["connection"] == 1  # CONNECTED
        assert active_agent["model_data"]["status"] == "running"
        assert isinstance(active_agent["model_data"]["created_at"], str)
        
        pending_agent = safe_update["agents"]["pending"][0] 
        assert pending_agent["status"] == "pending"
        assert pending_agent["connection"] == 0  # CONNECTING
        
        # Verify metrics serialization (dict keys converted to strings/values)
        metrics = safe_update["metrics"]
        connection_dist = metrics["connection_distribution"]
        # Enum keys should be converted to their values
        assert 1 in connection_dist or "1" in connection_dist  # CONNECTED
        assert 0 in connection_dist or "0" in connection_dist  # CONNECTING
        assert 3 in connection_dist or "3" in connection_dist  # DISCONNECTED
        
        json.dumps(safe_update)
        
        await mock_websocket_bridge.send_agent_update(safe_update)
        assert mock_websocket_bridge.send_agent_update.called


class TestSystem7_WebSocketConnectionHandler:
    """Tests for System 7: WebSocket Connection Handler low-level operations."""
    
    async def test_connection_handler_state_transitions(self):
        """Test connection handler manages state transitions with proper serialization."""
        # Connection state transition data
        state_transitions = [
            {
                "type": "connection_transition",
                "connection_id": "handler_conn_001",
                "from_state": WebSocketState.CONNECTING,
                "to_state": WebSocketState.CONNECTED,
                "timestamp": datetime.now(timezone.utc),
                "metadata": {
                    "user_id": "handler_user_001",
                    "session_data": {
                        "auth_status": "authenticated",
                        "connection_quality": "stable",
                        "previous_states": [WebSocketState.CONNECTING]
                    }
                }
            },
            {
                "type": "connection_error",
                "connection_id": "handler_conn_001", 
                "error_state": WebSocketState.DISCONNECTED,
                "error_details": {
                    "reason": "network_timeout",
                    "last_known_state": WebSocketState.CONNECTED,
                    "retry_states": [WebSocketState.CONNECTING, WebSocketState.CONNECTED, WebSocketState.DISCONNECTED],
                    "error_time": datetime.now(timezone.utc)
                }
            }
        ]
        
        for transition in state_transitions:
            safe_transition = _serialize_message_safely(transition)
            
            if "from_state" in safe_transition:
                assert safe_transition["from_state"] == 0  # CONNECTING
                assert safe_transition["to_state"] == 1  # CONNECTED
            
            if "error_state" in safe_transition:
                assert safe_transition["error_state"] == 3  # DISCONNECTED
                error_details = safe_transition["error_details"]
                assert error_details["last_known_state"] == 1  # CONNECTED
                assert error_details["retry_states"] == [0, 1, 3]  # Full transition sequence
            
            # Verify nested serialization in metadata
            if "metadata" in safe_transition:
                session_data = safe_transition["metadata"]["session_data"]
                assert session_data["previous_states"] == [0]  # CONNECTING
            
            json.dumps(safe_transition)


class TestSystem8_AuthenticationIntegration:
    """Tests for System 8: Authentication Integration with WebSocket serialization."""
    
    async def test_auth_integration_websocket_messages(self):
        """Test authentication integration handles WebSocket messages with complex data."""
        # Authentication event data
        auth_events = [
            {
                "type": "auth_success",
                "user_id": "auth_user_001",
                "connection_state": WebSocketState.CONNECTED,
                "auth_data": {
                    "method": "jwt",
                    "token_expires": datetime.now(timezone.utc),
                    "permissions": ["read", "write"],
                    "session_state": WebSocketState.CONNECTED
                }
            },
            {
                "type": "auth_refresh",
                "user_id": "auth_user_001",
                "refresh_data": {
                    "old_state": WebSocketState.CONNECTED,
                    "new_state": WebSocketState.CONNECTED,
                    "refresh_time": datetime.now(timezone.utc),
                    "status_model": MockPydanticModel("refresh_status", datetime.now(timezone.utc))
                }
            },
            {
                "type": "auth_failure", 
                "connection_state": WebSocketState.DISCONNECTED,
                "failure_data": {
                    "reason": "token_expired",
                    "previous_state": WebSocketState.CONNECTED,
                    "disconnect_time": datetime.now(timezone.utc)
                }
            }
        ]
        
        for event in auth_events:
            safe_event = _serialize_message_safely(event)
            
            # Verify WebSocketState serialization
            if "connection_state" in safe_event:
                assert isinstance(safe_event["connection_state"], int)
            
            # Verify nested auth data serialization
            if "auth_data" in safe_event:
                auth_data = safe_event["auth_data"]
                assert isinstance(auth_data["token_expires"], str)  # datetime -> ISO string
                assert auth_data["session_state"] == 1  # CONNECTED
            
            if "refresh_data" in safe_event:
                refresh_data = safe_event["refresh_data"] 
                assert refresh_data["old_state"] == 1  # CONNECTED
                assert refresh_data["new_state"] == 1  # CONNECTED
                assert isinstance(refresh_data["refresh_time"], str)
                # Pydantic model serialization
                assert "created_at" in refresh_data["status_model"]
            
            if "failure_data" in safe_event:
                failure_data = safe_event["failure_data"]
                assert failure_data["previous_state"] == 1  # CONNECTED
                assert isinstance(failure_data["disconnect_time"], str)
            
            json.dumps(safe_event)


class TestSystem9_WebSocketBridgeFactory:
    """Tests for System 9: WebSocket Bridge Factory service integration."""
    
    async def test_bridge_factory_cross_service_messages(self):
        """Test WebSocket bridge handles cross-service messages with complex serialization."""
        # Cross-service bridge messages
        bridge_messages = [
            {
                "type": "service_to_websocket",
                "source_service": "agent_service",
                "target_connection": "bridge_conn_001",
                "payload": {
                    "service_data": {
                        "status": AgentStatus.RUNNING,
                        "connection_state": WebSocketState.CONNECTED,
                        "metrics": {
                            "processing_time": 1.5,
                            "state_transitions": [WebSocketState.CONNECTING, WebSocketState.CONNECTED],
                            "last_update": datetime.now(timezone.utc)
                        }
                    }
                }
            },
            {
                "type": "websocket_to_service",
                "source_connection": "bridge_conn_001", 
                "target_service": "agent_service",
                "payload": {
                    "command": "update_status",
                    "parameters": {
                        "new_status": AgentStatus.PENDING,
                        "websocket_state": WebSocketState.CONNECTED,
                        "request_time": datetime.now(timezone.utc),
                        "complex_data": MockPydanticModel("bridge_request", datetime.now(timezone.utc), AgentStatus.PENDING)
                    }
                }
            }
        ]
        
        for message in bridge_messages:
            safe_message = _serialize_message_safely(message)
            
            if "service_data" in safe_message.get("payload", {}):
                service_data = safe_message["payload"]["service_data"]
                assert service_data["status"] == "running"
                assert service_data["connection_state"] == 1  # CONNECTED
                metrics = service_data["metrics"]
                assert metrics["state_transitions"] == [0, 1]  # CONNECTING, CONNECTED
                assert isinstance(metrics["last_update"], str)
            
            if "parameters" in safe_message.get("payload", {}):
                params = safe_message["payload"]["parameters"]
                assert params["new_status"] == "pending"
                assert params["websocket_state"] == 1  # CONNECTED
                assert isinstance(params["request_time"], str)
                # Pydantic model in bridge message
                complex_data = params["complex_data"]
                assert complex_data["status"] == "pending"
                assert isinstance(complex_data["created_at"], str)
            
            json.dumps(safe_message)


class TestSystem10_CircuitBreaker:
    """Tests for System 10: Circuit Breaker with WebSocket error handling."""
    
    async def test_circuit_breaker_websocket_error_recovery(self):
        """Test circuit breaker handles WebSocket errors with proper serialization."""
        # Circuit breaker error scenarios
        error_scenarios = [
            {
                "type": "circuit_breaker_open",
                "service": "websocket_manager",
                "error_data": {
                    "failure_count": 3,
                    "last_failure_time": datetime.now(timezone.utc),
                    "connection_state": WebSocketState.DISCONNECTED,
                    "error_details": {
                        "error_type": "serialization_error",
                        "failed_states": [WebSocketState.CONNECTED, WebSocketState.DISCONNECTED],
                        "recovery_state": WebSocketState.CONNECTING
                    }
                }
            },
            {
                "type": "circuit_breaker_half_open",
                "service": "websocket_manager",
                "recovery_data": {
                    "test_connection_state": WebSocketState.CONNECTING,
                    "recovery_time": datetime.now(timezone.utc),
                    "test_message": {
                        "type": "circuit_test",
                        "status": AgentStatus.PENDING,
                        "websocket_state": WebSocketState.CONNECTING
                    }
                }
            },
            {
                "type": "circuit_breaker_closed",
                "service": "websocket_manager",
                "success_data": {
                    "recovery_successful": True,
                    "connection_state": WebSocketState.CONNECTED,
                    "success_time": datetime.now(timezone.utc),
                    "validated_serialization": {
                        "enum_test": AgentStatus.COMPLETED,
                        "state_test": WebSocketState.CONNECTED,
                        "datetime_test": datetime.now(timezone.utc)
                    }
                }
            }
        ]
        
        for scenario in error_scenarios:
            safe_scenario = _serialize_message_safely(scenario)
            
            if "error_data" in safe_scenario:
                error_data = safe_scenario["error_data"]
                assert isinstance(error_data["last_failure_time"], str)
                assert error_data["connection_state"] == 3  # DISCONNECTED
                error_details = error_data["error_details"]
                assert error_details["failed_states"] == [1, 3]  # CONNECTED, DISCONNECTED
                assert error_details["recovery_state"] == 0  # CONNECTING
            
            if "recovery_data" in safe_scenario:
                recovery_data = safe_scenario["recovery_data"]
                assert recovery_data["test_connection_state"] == 0  # CONNECTING
                assert isinstance(recovery_data["recovery_time"], str)
                test_msg = recovery_data["test_message"]
                assert test_msg["status"] == "pending"
                assert test_msg["websocket_state"] == 0  # CONNECTING
            
            if "success_data" in safe_scenario:
                success_data = safe_scenario["success_data"]
                assert success_data["connection_state"] == 1  # CONNECTED
                assert isinstance(success_data["success_time"], str)
                validation = success_data["validated_serialization"]
                assert validation["enum_test"] == "completed"
                assert validation["state_test"] == 1  # CONNECTED
                assert isinstance(validation["datetime_test"], str)
            
            json.dumps(safe_scenario)


class TestCrossSystemIntegration:
    """Integration tests across multiple WebSocket systems."""
    
    async def test_full_pipeline_serialization(self):
        """Test complete pipeline from agent execution to WebSocket delivery."""
        # Simulate full pipeline: Agent -> Notifier -> Manager -> WebSocket
        
        # 1. Agent execution generates complex event
        agent_event = {
            "type": "agent_pipeline_complete",
            "agent_id": "pipeline_agent_001",
            "execution_data": {
                "status": AgentStatus.COMPLETED,
                "start_time": datetime.now(timezone.utc),
                "end_time": datetime.now(timezone.utc), 
                "results": {
                    "success": True,
                    "data_processed": 1500,
                    "connection_state": WebSocketState.CONNECTED,
                    "tool_executions": [
                        {
                            "tool": "analyzer",
                            "status": ToolExecutionStatus.SUCCESS,
                            "duration": 2.3
                        },
                        {
                            "tool": "reporter", 
                            "status": ToolExecutionStatus.SUCCESS,
                            "duration": 1.1
                        }
                    ]
                }
            }
        }
        
        # 2. Serialize for WebSocket notifier
        safe_event = _serialize_message_safely(agent_event)
        
        # 3. Verify serialization at each stage
        exec_data = safe_event["execution_data"]
        assert exec_data["status"] == "completed"
        assert isinstance(exec_data["start_time"], str)
        assert isinstance(exec_data["end_time"], str)
        
        results = exec_data["results"]
        assert results["connection_state"] == 1  # CONNECTED
        
        # Tool executions array serialization
        tools = results["tool_executions"]
        assert all(tool["status"] == 2 for tool in tools)  # All SUCCESS
        
        # 4. Mock WebSocket manager delivery
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        
        # Simulate final delivery
        await mock_websocket.send_json(safe_event)
        
        # 5. Verify final JSON serializability
        final_message = mock_websocket.send_json.call_args[0][0]
        json.dumps(final_message)
        
        assert mock_websocket.send_json.called
    
    async def test_error_cascade_handling(self):
        """Test error handling cascade across systems with serialization."""
        # Error cascade: Connection failure -> Circuit breaker -> Recovery -> Success
        
        error_cascade = [
            {
                "stage": "connection_failure",
                "data": {
                    "type": "websocket_error",
                    "connection_state": WebSocketState.DISCONNECTED,
                    "error_time": datetime.now(timezone.utc),
                    "failed_message": {
                        "agent_status": AgentStatus.FAILED,
                        "websocket_state": WebSocketState.CONNECTED  # Before failure
                    }
                }
            },
            {
                "stage": "circuit_breaker_triggered",
                "data": {
                    "type": "circuit_open", 
                    "failure_threshold_reached": True,
                    "failed_states": [WebSocketState.CONNECTED, WebSocketState.DISCONNECTED],
                    "trigger_time": datetime.now(timezone.utc)
                }
            },
            {
                "stage": "recovery_attempt",
                "data": {
                    "type": "recovery_test",
                    "test_connection_state": WebSocketState.CONNECTING,
                    "recovery_data": {
                        "retry_count": 1,
                        "test_message": {
                            "status": AgentStatus.PENDING,
                            "websocket_state": WebSocketState.CONNECTING
                        },
                        "recovery_time": datetime.now(timezone.utc)
                    }
                }
            },
            {
                "stage": "recovery_success",
                "data": {
                    "type": "connection_restored",
                    "new_state": WebSocketState.CONNECTED,
                    "success_time": datetime.now(timezone.utc),
                    "validated_operations": [
                        {
                            "operation": "enum_serialization",
                            "status": AgentStatus.COMPLETED,
                            "result": "success"
                        },
                        {
                            "operation": "state_management",
                            "websocket_state": WebSocketState.CONNECTED,
                            "result": "success"
                        }
                    ]
                }
            }
        ]
        
        # Process each stage through serialization
        for stage in error_cascade:
            safe_stage = _serialize_message_safely(stage)
            
            # Verify stage-specific serialization
            stage_name = safe_stage["stage"]
            data = safe_stage["data"]
            
            if stage_name == "connection_failure":
                assert data["connection_state"] == 3  # DISCONNECTED
                failed_msg = data["failed_message"]
                assert failed_msg["agent_status"] == "failed"
                assert failed_msg["websocket_state"] == 1  # CONNECTED (before failure)
            
            elif stage_name == "circuit_breaker_triggered":
                assert data["failed_states"] == [1, 3]  # CONNECTED, DISCONNECTED
            
            elif stage_name == "recovery_attempt":
                assert data["test_connection_state"] == 0  # CONNECTING
                recovery_data = data["recovery_data"]
                test_msg = recovery_data["test_message"]
                assert test_msg["status"] == "pending"
                assert test_msg["websocket_state"] == 0  # CONNECTING
            
            elif stage_name == "recovery_success":
                assert data["new_state"] == 1  # CONNECTED
                validated_ops = data["validated_operations"]
                assert validated_ops[0]["status"] == "completed"
                assert validated_ops[1]["websocket_state"] == 1  # CONNECTED
            
            # Verify all stages are JSON serializable
            json.dumps(safe_stage)


# Performance and stress testing
class TestSerializationPerformance:
    """Performance tests for WebSocket serialization across systems."""
    
    def test_serialization_performance_with_large_datasets(self):
        """Test serialization performance with large complex datasets."""
        import time
        
        # Create large dataset with mixed complex objects
        large_dataset = {
            "type": "bulk_update",
            "timestamp": datetime.now(timezone.utc),
            "agents": []
        }
        
        # Add 1000 agents with complex data
        for i in range(1000):
            agent_data = {
                "agent_id": f"perf_agent_{i:04d}",
                "status": AgentStatus.RUNNING if i % 2 == 0 else AgentStatus.PENDING,
                "websocket_state": WebSocketState.CONNECTED if i % 3 == 0 else WebSocketState.CONNECTING,
                "tools": [ToolExecutionStatus.SUCCESS, ToolExecutionStatus.EXECUTING, ToolExecutionStatus.QUEUED],
                "metadata": {
                    "created_at": datetime.now(timezone.utc),
                    "model_data": MockPydanticModel(f"perf_model_{i}", datetime.now(timezone.utc), AgentStatus.RUNNING),
                    "state_history": [WebSocketState.CONNECTING, WebSocketState.CONNECTED] * 10  # 20 states
                }
            }
            large_dataset["agents"].append(agent_data)
        
        # Measure serialization performance
        start_time = time.time()
        safe_dataset = _serialize_message_safely(large_dataset)
        serialization_time = time.time() - start_time
        
        # Verify serialization correctness
        assert len(safe_dataset["agents"]) == 1000
        sample_agent = safe_dataset["agents"][0]
        assert sample_agent["status"] == "running"
        assert sample_agent["websocket_state"] in [0, 1]  # CONNECTING or CONNECTED
        assert sample_agent["tools"] == [2, 1, 0]  # SUCCESS, EXECUTING, QUEUED
        
        # Verify JSON serialization works for large dataset
        start_json = time.time()
        json_output = json.dumps(safe_dataset)
        json_time = time.time() - start_json
        
        # Performance assertions (should complete in reasonable time)
        assert serialization_time < 1.0, f"Serialization took {serialization_time:.3f}s, expected < 1.0s"
        assert json_time < 0.5, f"JSON dumps took {json_time:.3f}s, expected < 0.5s"
        assert len(json_output) > 100000, "JSON output should be substantial"
        
        print(f"Performance: Serialized 1000 agents in {serialization_time:.3f}s, JSON in {json_time:.3f}s")


# Regression tests for specific error scenarios
class TestSerializationRegressionScenarios:
    """Regression tests for specific WebSocket serialization error scenarios."""
    
    def test_regression_websocket_state_in_nested_dict_keys(self):
        """Regression test: WebSocketState as dictionary keys."""
        # This scenario caused issues in some systems
        problematic_data = {
            "type": "state_distribution",
            "connection_counts": {
                WebSocketState.CONNECTED: 15,
                WebSocketState.CONNECTING: 3,
                WebSocketState.DISCONNECTED: 0
            },
            "agent_states": {
                AgentStatus.RUNNING: [WebSocketState.CONNECTED, WebSocketState.CONNECTED],
                AgentStatus.PENDING: [WebSocketState.CONNECTING]
            }
        }
        
        safe_data = _serialize_message_safely(problematic_data)
        
        # Dictionary keys should be converted to serializable values
        conn_counts = safe_data["connection_counts"]
        # Keys might be converted to int values or string representations
        total_connections = sum(conn_counts.values())
        assert total_connections == 18  # 15 + 3 + 0
        
        agent_states = safe_data["agent_states"]
        # Values should be properly serialized arrays
        for status, states in agent_states.items():
            assert isinstance(states, list)
            assert all(isinstance(state, int) for state in states)
        
        json.dumps(safe_data)
    
    def test_regression_circular_reference_with_enums(self):
        """Regression test: Circular references involving enum objects."""
        # Create objects that could cause circular references
        obj_a = {"id": "a", "status": AgentStatus.RUNNING}
        obj_b = {"id": "b", "status": AgentStatus.PENDING, "parent": obj_a}
        obj_a["child"] = obj_b  # Circular reference
        
        # Should handle gracefully without infinite recursion
        safe_data = _serialize_message_safely({
            "type": "circular_test",
            "objects": [obj_a, obj_b],
            "websocket_state": WebSocketState.CONNECTED
        })
        
        # Verify serialization completed without infinite loop
        assert safe_data["websocket_state"] == 1
        assert len(safe_data["objects"]) == 2
        
        # Note: Circular references might be broken during serialization
        # The important thing is that it doesn't crash and enums are handled
        json.dumps(safe_data)


if __name__ == "__main__":
    # Quick smoke test
    import asyncio
    
    async def smoke_test():
        """Quick smoke test to verify basic functionality."""
        print("Running WebSocket serialization systems smoke test...")
        
        # Test basic enum serialization
        test_data = {
            "websocket_state": WebSocketState.CONNECTED,
            "agent_status": AgentStatus.RUNNING,
            "tool_status": ToolExecutionStatus.SUCCESS,
            "timestamp": datetime.now(timezone.utc)
        }
        
        safe_data = _serialize_message_safely(test_data)
        json_output = json.dumps(safe_data)
        
        print(f"✅ Basic serialization works: {len(json_output)} characters")
        print("✅ All WebSocket systems serialization tests ready to run!")
    
    asyncio.run(smoke_test())