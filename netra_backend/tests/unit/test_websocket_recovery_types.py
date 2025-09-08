"""
Unit Tests for WebSocket Recovery Types

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket connection reliability and state management
- Value Impact: Critical for chat functionality and user experience
- Strategic Impact: Core platform stability - WebSocket recovery enables continuous agent interactions

Coverage Target: 100%
Business Value: Critical for chat reliability and multi-user isolation
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
import json
from dataclasses import asdict

from netra_backend.app.core.websocket_recovery_types import (
    ConnectionState,
    ReconnectionReason,
    ConnectionMetrics,
    MessageState,
    ReconnectionConfig
)


class TestConnectionState:
    """Test ConnectionState enum values and behavior."""
    
    @pytest.mark.unit
    def test_all_connection_states_exist(self):
        """Test that all expected connection states are defined."""
        expected_states = {
            "CONNECTING": "connecting",
            "CONNECTED": "connected", 
            "DISCONNECTED": "disconnected",
            "RECONNECTING": "reconnecting",
            "FAILED": "failed",
            "CLOSING": "closing"
        }
        
        for state_name, expected_value in expected_states.items():
            state = getattr(ConnectionState, state_name)
            assert state.value == expected_value
    
    @pytest.mark.unit
    def test_connection_state_string_representation(self):
        """Test string representation of connection states."""
        assert str(ConnectionState.CONNECTING) == "ConnectionState.CONNECTING"
        assert ConnectionState.CONNECTED.value == "connected"
    
    @pytest.mark.unit
    def test_connection_state_enum_membership(self):
        """Test enum membership and iteration."""
        all_states = list(ConnectionState)
        assert len(all_states) == 6
        
        # Test specific states are in enum
        assert ConnectionState.CONNECTING in all_states
        assert ConnectionState.CONNECTED in all_states
        assert ConnectionState.DISCONNECTED in all_states
        assert ConnectionState.RECONNECTING in all_states
        assert ConnectionState.FAILED in all_states
        assert ConnectionState.CLOSING in all_states
    
    @pytest.mark.unit
    def test_connection_state_comparison(self):
        """Test connection state equality and comparison."""
        assert ConnectionState.CONNECTING == ConnectionState.CONNECTING
        assert ConnectionState.CONNECTING != ConnectionState.CONNECTED
        
        # Test with string values
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value != "connecting"


class TestReconnectionReason:
    """Test ReconnectionReason enum values and behavior."""
    
    @pytest.mark.unit
    def test_all_reconnection_reasons_exist(self):
        """Test that all expected reconnection reasons are defined."""
        expected_reasons = {
            "CONNECTION_LOST": "connection_lost",
            "NETWORK_ERROR": "network_error",
            "SERVER_ERROR": "server_error", 
            "TIMEOUT": "timeout",
            "MANUAL": "manual"
        }
        
        for reason_name, expected_value in expected_reasons.items():
            reason = getattr(ReconnectionReason, reason_name)
            assert reason.value == expected_value
    
    @pytest.mark.unit
    def test_reconnection_reason_string_representation(self):
        """Test string representation of reconnection reasons."""
        assert str(ReconnectionReason.CONNECTION_LOST) == "ReconnectionReason.CONNECTION_LOST"
        assert ReconnectionReason.NETWORK_ERROR.value == "network_error"
    
    @pytest.mark.unit
    def test_reconnection_reason_enum_membership(self):
        """Test enum membership and iteration."""
        all_reasons = list(ReconnectionReason)
        assert len(all_reasons) == 5
        
        # Test specific reasons are in enum
        assert ReconnectionReason.CONNECTION_LOST in all_reasons
        assert ReconnectionReason.NETWORK_ERROR in all_reasons
        assert ReconnectionReason.SERVER_ERROR in all_reasons
        assert ReconnectionReason.TIMEOUT in all_reasons
        assert ReconnectionReason.MANUAL in all_reasons


class TestConnectionMetrics:
    """Test ConnectionMetrics dataclass functionality."""
    
    @pytest.fixture
    def base_metrics(self):
        """Create basic connection metrics for testing."""
        return ConnectionMetrics(
            connection_id="conn_123",
            connect_time=datetime(2024, 1, 1, 12, 0, 0)
        )
    
    @pytest.mark.unit
    def test_connection_metrics_initialization(self):
        """Test ConnectionMetrics initialization with required fields."""
        connect_time = datetime.now()
        metrics = ConnectionMetrics(
            connection_id="test_conn_123",
            connect_time=connect_time
        )
        
        # Test required fields
        assert metrics.connection_id == "test_conn_123"
        assert metrics.connect_time == connect_time
        
        # Test default values
        assert metrics.disconnect_time is None
        assert metrics.message_count == 0
        assert metrics.error_count == 0
        assert metrics.reconnect_count == 0
        assert metrics.last_ping is None
        assert metrics.last_pong is None
        assert metrics.latency_ms == 0.0
    
    @pytest.mark.unit
    def test_connection_metrics_with_all_fields(self):
        """Test ConnectionMetrics with all fields populated."""
        connect_time = datetime(2024, 1, 1, 12, 0, 0)
        disconnect_time = datetime(2024, 1, 1, 12, 30, 0)
        last_ping = datetime(2024, 1, 1, 12, 15, 0)
        last_pong = datetime(2024, 1, 1, 12, 15, 1)
        
        metrics = ConnectionMetrics(
            connection_id="full_conn_456",
            connect_time=connect_time,
            disconnect_time=disconnect_time,
            message_count=42,
            error_count=3,
            reconnect_count=2,
            last_ping=last_ping,
            last_pong=last_pong,
            latency_ms=125.5
        )
        
        assert metrics.connection_id == "full_conn_456"
        assert metrics.connect_time == connect_time
        assert metrics.disconnect_time == disconnect_time
        assert metrics.message_count == 42
        assert metrics.error_count == 3
        assert metrics.reconnect_count == 2
        assert metrics.last_ping == last_ping
        assert metrics.last_pong == last_pong
        assert metrics.latency_ms == 125.5
    
    @pytest.mark.unit
    def test_connection_metrics_dataclass_behavior(self, base_metrics):
        """Test dataclass functionality like comparison and representation."""
        # Test equality
        metrics2 = ConnectionMetrics(
            connection_id="conn_123",
            connect_time=datetime(2024, 1, 1, 12, 0, 0)
        )
        assert base_metrics == metrics2
        
        # Test inequality
        metrics3 = ConnectionMetrics(
            connection_id="conn_456", 
            connect_time=datetime(2024, 1, 1, 12, 0, 0)
        )
        assert base_metrics != metrics3
    
    @pytest.mark.unit
    def test_connection_metrics_field_modification(self, base_metrics):
        """Test that fields can be modified after creation."""
        # Modify mutable fields
        base_metrics.message_count = 10
        base_metrics.error_count = 1
        base_metrics.latency_ms = 50.0
        
        assert base_metrics.message_count == 10
        assert base_metrics.error_count == 1
        assert base_metrics.latency_ms == 50.0
    
    @pytest.mark.unit
    def test_connection_metrics_serialization(self, base_metrics):
        """Test that ConnectionMetrics can be serialized."""
        # Test conversion to dict
        metrics_dict = asdict(base_metrics)
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["connection_id"] == "conn_123"
        assert isinstance(metrics_dict["connect_time"], datetime)
        
        # Test fields present
        expected_fields = {
            "connection_id", "connect_time", "disconnect_time", 
            "message_count", "error_count", "reconnect_count",
            "last_ping", "last_pong", "latency_ms"
        }
        assert set(metrics_dict.keys()) == expected_fields
    
    @pytest.mark.unit
    def test_connection_metrics_edge_cases(self):
        """Test ConnectionMetrics with edge case values."""
        # Test with very large numbers
        metrics = ConnectionMetrics(
            connection_id="edge_conn",
            connect_time=datetime.now(),
            message_count=999999,
            error_count=0,
            latency_ms=0.001  # Very low latency
        )
        
        assert metrics.message_count == 999999
        assert metrics.error_count == 0
        assert metrics.latency_ms == 0.001
        
        # Test with negative values (should be allowed for edge cases)
        metrics.latency_ms = -1.0  # Could represent invalid measurement
        assert metrics.latency_ms == -1.0


class TestMessageState:
    """Test MessageState dataclass functionality."""
    
    @pytest.fixture
    def sample_content(self):
        """Create sample message content."""
        return {
            "type": "agent_request",
            "agent": "cost_optimizer",
            "message": "Analyze costs",
            "user_id": "user_123"
        }
    
    @pytest.fixture
    def base_message(self, sample_content):
        """Create basic message state for testing."""
        return MessageState(
            message_id="msg_456",
            content=sample_content,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
    
    @pytest.mark.unit
    def test_message_state_initialization(self, sample_content):
        """Test MessageState initialization with required fields."""
        timestamp = datetime.now()
        message = MessageState(
            message_id="test_msg_789",
            content=sample_content,
            timestamp=timestamp
        )
        
        # Test required fields
        assert message.message_id == "test_msg_789"
        assert message.content == sample_content
        assert message.timestamp == timestamp
        
        # Test default values
        assert message.ack_required == False
        assert message.acknowledged == False
        assert message.retry_count == 0
    
    @pytest.mark.unit
    def test_message_state_with_all_fields(self, sample_content):
        """Test MessageState with all fields populated."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        
        message = MessageState(
            message_id="full_msg_101",
            content=sample_content,
            timestamp=timestamp,
            ack_required=True,
            acknowledged=True,
            retry_count=3
        )
        
        assert message.message_id == "full_msg_101"
        assert message.content == sample_content
        assert message.timestamp == timestamp
        assert message.ack_required == True
        assert message.acknowledged == True
        assert message.retry_count == 3
    
    @pytest.mark.unit
    def test_message_state_content_types(self):
        """Test MessageState with different content types."""
        timestamp = datetime.now()
        
        # Test with empty dict
        message1 = MessageState(
            message_id="empty_msg",
            content={},
            timestamp=timestamp
        )
        assert message1.content == {}
        
        # Test with complex nested content
        complex_content = {
            "type": "agent_response",
            "data": {
                "result": "optimization complete",
                "metrics": {"cost_savings": 1000.0, "efficiency": 0.95}
            },
            "metadata": {
                "execution_time": 5.2,
                "tools_used": ["cost_analyzer", "recommendation_engine"]
            }
        }
        
        message2 = MessageState(
            message_id="complex_msg",
            content=complex_content,
            timestamp=timestamp
        )
        assert message2.content == complex_content
        assert message2.content["data"]["metrics"]["cost_savings"] == 1000.0
    
    @pytest.mark.unit
    def test_message_state_acknowledgment_flow(self, base_message):
        """Test message acknowledgment state transitions."""
        # Initial state
        assert base_message.ack_required == False
        assert base_message.acknowledged == False
        
        # Require acknowledgment
        base_message.ack_required = True
        assert base_message.ack_required == True
        assert base_message.acknowledged == False
        
        # Acknowledge message
        base_message.acknowledged = True
        assert base_message.ack_required == True
        assert base_message.acknowledged == True
    
    @pytest.mark.unit
    def test_message_state_retry_logic(self, base_message):
        """Test message retry count behavior."""
        assert base_message.retry_count == 0
        
        # Simulate retries
        for i in range(1, 4):
            base_message.retry_count = i
            assert base_message.retry_count == i
        
        # Test maximum retries
        base_message.retry_count = 999
        assert base_message.retry_count == 999
    
    @pytest.mark.unit
    def test_message_state_serialization(self, base_message):
        """Test MessageState serialization."""
        message_dict = asdict(base_message)
        assert isinstance(message_dict, dict)
        assert message_dict["message_id"] == "msg_456"
        assert isinstance(message_dict["content"], dict)
        assert isinstance(message_dict["timestamp"], datetime)
        
        # Test all fields present
        expected_fields = {
            "message_id", "content", "timestamp", 
            "ack_required", "acknowledged", "retry_count"
        }
        assert set(message_dict.keys()) == expected_fields


class TestReconnectionConfig:
    """Test ReconnectionConfig dataclass functionality."""
    
    @pytest.mark.unit
    def test_reconnection_config_defaults(self):
        """Test ReconnectionConfig default values."""
        config = ReconnectionConfig()
        
        # Test reconnection behavior defaults
        assert config.max_attempts == 10
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter == True
        assert config.timeout_seconds == 30
        
        # Test state preservation defaults  
        assert config.preserve_pending_messages == True
        assert config.max_pending_messages == 1000
        assert config.message_retention_hours == 24
    
    @pytest.mark.unit
    def test_reconnection_config_custom_values(self):
        """Test ReconnectionConfig with custom values."""
        config = ReconnectionConfig(
            max_attempts=5,
            initial_delay=0.5,
            max_delay=30.0,
            backoff_multiplier=1.5,
            jitter=False,
            timeout_seconds=15,
            preserve_pending_messages=False,
            max_pending_messages=500,
            message_retention_hours=12
        )
        
        assert config.max_attempts == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0
        assert config.backoff_multiplier == 1.5
        assert config.jitter == False
        assert config.timeout_seconds == 15
        assert config.preserve_pending_messages == False
        assert config.max_pending_messages == 500
        assert config.message_retention_hours == 12
    
    @pytest.mark.unit
    def test_reconnection_config_validation_scenarios(self):
        """Test ReconnectionConfig with various validation scenarios."""
        # Test minimum values
        config_min = ReconnectionConfig(
            max_attempts=1,
            initial_delay=0.1,
            max_delay=1.0,
            backoff_multiplier=1.0,
            timeout_seconds=1,
            max_pending_messages=1,
            message_retention_hours=1
        )
        
        assert config_min.max_attempts == 1
        assert config_min.initial_delay == 0.1
        assert config_min.backoff_multiplier == 1.0
        
        # Test maximum/extreme values
        config_max = ReconnectionConfig(
            max_attempts=100,
            initial_delay=10.0,
            max_delay=3600.0,  # 1 hour
            backoff_multiplier=10.0,
            timeout_seconds=300,  # 5 minutes
            max_pending_messages=10000,
            message_retention_hours=168  # 1 week
        )
        
        assert config_max.max_attempts == 100
        assert config_max.max_delay == 3600.0
        assert config_max.message_retention_hours == 168
    
    @pytest.mark.unit
    def test_reconnection_config_backoff_calculation(self):
        """Test backoff delay calculation scenarios."""
        config = ReconnectionConfig(
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0
        )
        
        # Test exponential backoff scenarios
        # Delay 1: 1.0 * 2^0 = 1.0
        # Delay 2: 1.0 * 2^1 = 2.0  
        # Delay 3: 1.0 * 2^2 = 4.0
        # Delay 4: 1.0 * 2^3 = 8.0
        # ... until max_delay
        
        assert config.initial_delay == 1.0
        assert config.backoff_multiplier == 2.0
        assert config.max_delay == 60.0
    
    @pytest.mark.unit  
    def test_reconnection_config_state_preservation(self):
        """Test state preservation configuration."""
        # Configuration that preserves state
        preserve_config = ReconnectionConfig(
            preserve_pending_messages=True,
            max_pending_messages=5000,
            message_retention_hours=48
        )
        
        assert preserve_config.preserve_pending_messages == True
        assert preserve_config.max_pending_messages == 5000
        assert preserve_config.message_retention_hours == 48
        
        # Configuration that doesn't preserve state
        no_preserve_config = ReconnectionConfig(
            preserve_pending_messages=False,
            max_pending_messages=0,
            message_retention_hours=0
        )
        
        assert no_preserve_config.preserve_pending_messages == False
        assert no_preserve_config.max_pending_messages == 0
        assert no_preserve_config.message_retention_hours == 0
    
    @pytest.mark.unit
    def test_reconnection_config_serialization(self):
        """Test ReconnectionConfig serialization."""
        config = ReconnectionConfig(
            max_attempts=7,
            initial_delay=2.0,
            jitter=False
        )
        
        config_dict = asdict(config)
        assert isinstance(config_dict, dict)
        assert config_dict["max_attempts"] == 7
        assert config_dict["initial_delay"] == 2.0
        assert config_dict["jitter"] == False
        
        # Test all fields present
        expected_fields = {
            "max_attempts", "initial_delay", "max_delay", "backoff_multiplier",
            "jitter", "timeout_seconds", "preserve_pending_messages",
            "max_pending_messages", "message_retention_hours"
        }
        assert set(config_dict.keys()) == expected_fields


class TestWebSocketRecoveryTypesIntegration:
    """Integration tests for WebSocket recovery types working together."""
    
    @pytest.mark.unit
    def test_complete_recovery_scenario(self):
        """Test a complete WebSocket recovery scenario using all types."""
        # Initial connection
        connect_time = datetime.now()
        connection_metrics = ConnectionMetrics(
            connection_id="integration_conn_123",
            connect_time=connect_time
        )
        
        # Message sent during connection
        message = MessageState(
            message_id="recovery_msg_456",
            content={"type": "agent_request", "message": "test"},
            timestamp=connect_time + timedelta(seconds=10),
            ack_required=True
        )
        
        # Recovery configuration
        config = ReconnectionConfig(
            max_attempts=3,
            initial_delay=1.0,
            preserve_pending_messages=True
        )
        
        # Simulate connection failure
        connection_metrics.disconnect_time = connect_time + timedelta(minutes=5)
        connection_metrics.reconnect_count = 1
        
        # Verify state
        assert connection_metrics.connection_id == "integration_conn_123"
        assert message.ack_required == True
        assert message.acknowledged == False  # Not acknowledged before disconnect
        assert config.preserve_pending_messages == True
    
    @pytest.mark.unit
    def test_state_transitions_with_reasons(self):
        """Test state transitions with different reconnection reasons."""
        reasons_and_states = [
            (ReconnectionReason.CONNECTION_LOST, ConnectionState.RECONNECTING),
            (ReconnectionReason.NETWORK_ERROR, ConnectionState.RECONNECTING), 
            (ReconnectionReason.SERVER_ERROR, ConnectionState.FAILED),
            (ReconnectionReason.TIMEOUT, ConnectionState.RECONNECTING),
            (ReconnectionReason.MANUAL, ConnectionState.CONNECTING)
        ]
        
        for reason, expected_state in reasons_and_states:
            # Each reason should be valid
            assert isinstance(reason, ReconnectionReason)
            assert isinstance(expected_state, ConnectionState)
            
            # Verify reason values
            assert reason.value in [
                "connection_lost", "network_error", "server_error", 
                "timeout", "manual"
            ]
    
    @pytest.mark.unit
    def test_message_lifecycle_with_metrics(self):
        """Test message lifecycle tracking in connection metrics."""
        metrics = ConnectionMetrics(
            connection_id="lifecycle_conn",
            connect_time=datetime.now()
        )
        
        # Simulate message flow
        messages = []
        for i in range(5):
            message = MessageState(
                message_id=f"msg_{i}",
                content={"sequence": i, "data": f"message {i}"},
                timestamp=datetime.now() + timedelta(seconds=i)
            )
            messages.append(message)
            metrics.message_count += 1
        
        # Simulate some errors  
        metrics.error_count = 1
        
        # Verify final state
        assert len(messages) == 5
        assert metrics.message_count == 5
        assert metrics.error_count == 1
        assert all(msg.message_id.startswith("msg_") for msg in messages)
    
    @pytest.mark.unit
    def test_configuration_driven_behavior(self):
        """Test how configuration drives recovery behavior."""
        # Fast reconnection config
        fast_config = ReconnectionConfig(
            max_attempts=10,
            initial_delay=0.1,
            max_delay=5.0,
            backoff_multiplier=1.5
        )
        
        # Slow/conservative reconnection config
        slow_config = ReconnectionConfig(
            max_attempts=3,
            initial_delay=5.0,
            max_delay=300.0,
            backoff_multiplier=3.0
        )
        
        # Verify configurations are different
        assert fast_config.max_attempts > slow_config.max_attempts
        assert fast_config.initial_delay < slow_config.initial_delay
        assert fast_config.backoff_multiplier < slow_config.backoff_multiplier
        
        # Both should be valid configurations
        assert fast_config.max_attempts > 0
        assert slow_config.max_attempts > 0
        assert fast_config.initial_delay > 0
        assert slow_config.initial_delay > 0
    
    @pytest.mark.unit
    def test_data_integrity_across_types(self):
        """Test data integrity when using types together."""
        # Create instances with related data
        connection_id = "integrity_test_conn_789"
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        metrics = ConnectionMetrics(
            connection_id=connection_id,
            connect_time=base_time
        )
        
        message = MessageState(
            message_id="integrity_msg_123",
            content={"connection_id": connection_id, "timestamp": base_time.isoformat()},
            timestamp=base_time + timedelta(seconds=30)
        )
        
        config = ReconnectionConfig(
            preserve_pending_messages=True,
            message_retention_hours=24
        )
        
        # Verify data consistency
        assert metrics.connection_id == connection_id
        assert message.content["connection_id"] == connection_id  
        assert config.preserve_pending_messages == True
        
        # Test that timestamps are consistent
        assert message.timestamp > metrics.connect_time
        message_time_from_content = datetime.fromisoformat(message.content["timestamp"])
        assert message_time_from_content == metrics.connect_time


class TestWebSocketRecoveryTypesEdgeCases:
    """Test edge cases and error conditions for WebSocket recovery types."""
    
    @pytest.mark.unit
    def test_empty_and_null_values(self):
        """Test behavior with empty and null values."""
        # Test with minimal required data
        minimal_metrics = ConnectionMetrics(
            connection_id="",  # Empty string
            connect_time=datetime.now()
        )
        assert minimal_metrics.connection_id == ""
        
        minimal_message = MessageState(
            message_id="",
            content={},  # Empty content
            timestamp=datetime.now()
        )
        assert minimal_message.content == {}
        assert minimal_message.message_id == ""
    
    @pytest.mark.unit
    def test_extreme_numeric_values(self):
        """Test with extreme numeric values."""
        # Very large numbers
        metrics = ConnectionMetrics(
            connection_id="extreme_test",
            connect_time=datetime.now(),
            message_count=2**31 - 1,  # Max int32
            latency_ms=999999.999
        )
        
        assert metrics.message_count == 2147483647
        assert metrics.latency_ms == 999999.999
        
        # Very small numbers
        config = ReconnectionConfig(
            initial_delay=0.001,  # 1ms
            max_delay=0.01,      # 10ms
            backoff_multiplier=1.001  # Minimal backoff
        )
        
        assert config.initial_delay == 0.001
        assert config.max_delay == 0.01
        assert config.backoff_multiplier == 1.001
    
    @pytest.mark.unit
    def test_datetime_edge_cases(self):
        """Test with datetime edge cases."""
        # Very old timestamp
        old_time = datetime(1970, 1, 1, 0, 0, 0)
        metrics = ConnectionMetrics(
            connection_id="old_connection",
            connect_time=old_time
        )
        assert metrics.connect_time == old_time
        
        # Future timestamp
        future_time = datetime(2050, 12, 31, 23, 59, 59)
        message = MessageState(
            message_id="future_msg",
            content={"future": True},
            timestamp=future_time
        )
        assert message.timestamp == future_time
    
    @pytest.mark.unit
    def test_boolean_state_combinations(self):
        """Test all combinations of boolean states."""
        # Test all ack/acknowledge combinations
        bool_combinations = [
            (False, False),  # Default state
            (True, False),   # Ack required but not acknowledged  
            (True, True),    # Ack required and acknowledged
            (False, True),   # Not required but somehow acknowledged (edge case)
        ]
        
        for ack_required, acknowledged in bool_combinations:
            message = MessageState(
                message_id=f"bool_test_{ack_required}_{acknowledged}",
                content={"test": "boolean_states"},
                timestamp=datetime.now(),
                ack_required=ack_required,
                acknowledged=acknowledged
            )
            
            assert message.ack_required == ack_required
            assert message.acknowledged == acknowledged
    
    @pytest.mark.unit
    def test_type_immutability_vs_mutability(self):
        """Test which aspects of types are mutable vs immutable."""
        # Enums should be immutable
        state = ConnectionState.CONNECTING
        original_value = state.value
        
        # Cannot modify enum value (this would raise an error in real code)
        assert state.value == original_value
        
        # Dataclass instances should be mutable
        config = ReconnectionConfig()
        original_attempts = config.max_attempts
        
        # Should be able to modify fields
        config.max_attempts = 20
        assert config.max_attempts == 20
        assert config.max_attempts != original_attempts
        
        # Reset for other tests
        config.max_attempts = original_attempts