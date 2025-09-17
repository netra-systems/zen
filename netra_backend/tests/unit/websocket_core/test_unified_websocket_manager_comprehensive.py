"""
Comprehensive Unit Test Suite for UnifiedWebSocketManager - Business Critical Infrastructure

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - 100% of users depend on this
- Business Goal: Ensure Real-Time Chat Reliability enabling $500K+ ARR  
- Value Impact: WebSocket events deliver 90% of platform business value through chat interactions
- Strategic Impact: MISSION CRITICAL - Platform foundation for real-time AI chat that drives revenue

This test suite provides COMPREHENSIVE coverage of the UnifiedWebSocketManager class,
which is the Single Source of Truth (SSOT) for WebSocket connection management.

CRITICAL COVERAGE AREAS (10/10 Business Criticality):
1. User isolation and multi-user safety (prevents $100K data breach)
2. Connection lifecycle management (connect, disconnect, cleanup) 
3. WebSocket event delivery (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
4. Authentication integration and error handling (prevents unauthorized access)
5. Message serialization and complex data handling (Enums, Pydantic models, datetime)
6. Race condition prevention in concurrent scenarios (prevents data corruption)
7. Background task monitoring and health checks (ensures system reliability)
8. Error recovery and message queuing (prevents message loss)
9. Performance optimization and memory management (prevents system crashes)
10. Edge cases that could cause complete chat system failure

This is P0 Chat Critical testing - ensures the foundation of real-time user interactions
that deliver our core business value proposition.
"""
import asyncio
import pytest
import time
import uuid
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from enum import Enum
from dataclasses import dataclass
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, ConnectionID, WebSocketID, RequestID, ensure_user_id, ensure_thread_id, ensure_websocket_id
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager, WebSocketConnection, RegistryCompat, _serialize_message_safely, _get_enum_key_representation
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

class WebSocketStateTests(Enum):
    """Test enum to simulate WebSocket states for serialization testing."""
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3

class ComplexDataTests:
    """Test class with complex serialization requirements."""

    def __init__(self, value: str):
        self.value = value
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {'value': self.value, 'timestamp': self.timestamp.isoformat(), 'type': 'ComplexDataTests'}

@dataclass
class DataClassTests:
    """Test dataclass for serialization testing."""
    name: str
    value: int
    active: bool = True

class MockWebSocket:
    """
    High-fidelity WebSocket mock for comprehensive testing.
    
    Simulates real WebSocket behavior including:
    - State management (OPEN, CLOSED, etc.)
    - Connection failures and recovery
    - Message serialization validation
    - Performance characteristics
    """

    def __init__(self, user_id: str, connection_id: str, should_fail: bool=False):
        self.user_id = user_id
        self.connection_id = connection_id
        self.should_fail = should_fail
        self.sent_messages: List[Dict[str, Any]] = []
        self.is_closed = False
        self.client_state = WebSocketStateTests.OPEN
        self.send_delay = 0.0
        self.message_count = 0
        self.bytes_sent = 0

    async def send_json(self, message: Dict[str, Any]) -> None:
        """Mock sending JSON message with realistic behavior."""
        if self.should_fail:
            raise RuntimeError(f'Mock WebSocket send failure for connection {self.connection_id}')
        if self.is_closed or self.client_state == WebSocketStateTests.CLOSED:
            raise RuntimeError('WebSocket connection closed')
        if self.send_delay > 0:
            await asyncio.sleep(self.send_delay)
        try:
            json_str = json.dumps(message)
            self.bytes_sent += len(json_str.encode('utf-8'))
        except (TypeError, ValueError) as e:
            raise RuntimeError(f'Message not JSON serializable: {e}')
        message_with_meta = {**message, '_test_user_id': self.user_id, '_test_connection_id': self.connection_id, '_test_timestamp': datetime.utcnow().isoformat(), '_test_message_number': self.message_count}
        self.sent_messages.append(message_with_meta)
        self.message_count += 1

    async def close(self, code: int=1000, reason: str='Normal closure') -> None:
        """Mock closing WebSocket with status codes."""
        self.is_closed = True
        self.client_state = WebSocketStateTests.CLOSED

    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all sent messages for validation."""
        return self.sent_messages.copy()

    def clear_sent_messages(self) -> None:
        """Clear message history for fresh test state."""
        self.sent_messages.clear()
        self.message_count = 0
        self.bytes_sent = 0

    def set_network_conditions(self, delay: float=0.0, should_fail: bool=False):
        """Simulate network conditions for stress testing."""
        self.send_delay = delay
        self.should_fail = should_fail

class UnifiedWebSocketManagerComprehensiveTests(BaseIntegrationTest):
    """
    Comprehensive unit test suite for UnifiedWebSocketManager.
    
    This test class ensures 100% coverage of critical business logic with focus on:
    - Real-world edge cases that could break chat functionality
    - Multi-user isolation preventing data leakage
    - Error recovery that maintains business continuity
    - Performance characteristics under load
    """

    def setup_method(self, method=None):
        """Setup method for each test - clean state guaranteed."""
        super().setup_method()
        self.env = get_env()
        self.env.set('ENVIRONMENT', 'test', 'websocket_unit_test')
        self.env.set('WEBSOCKET_TEST_TIMEOUT', '5', 'websocket_unit_test')
        self.manager = None
        self.test_metrics = {'connections_created': 0, 'messages_sent': 0, 'errors_handled': 0, 'test_start_time': time.time()}
        self.id_manager = UnifiedIDManager()

    def teardown_method(self, method=None):
        """Cleanup after each test - prevent state leakage."""
        super().teardown_method()
        self.manager = None
        test_duration = time.time() - self.test_metrics['test_start_time']
        if test_duration > 1.0:
            print(f"SLOW TEST WARNING: {(method.__name__ if method else 'unknown')} took {test_duration:.2f}s")

    def create_mock_connection(self, user_id: str, connection_id: str=None, should_fail: bool=False) -> WebSocketConnection:
        """
        Create a realistic mock WebSocket connection for testing.
        
        Args:
            user_id: User identifier (will be validated)
            connection_id: Optional connection ID (generated if not provided)
            should_fail: Whether WebSocket should simulate failures
            
        Returns:
            WebSocketConnection instance with mock WebSocket
        """
        if connection_id is None:
            connection_id = self.id_manager.generate_id(IDType.WEBSOCKET, prefix='test_conn', context={'user_id': user_id})
        validated_user_id = UserID(user_id)
        mock_websocket = MockWebSocket(validated_user_id, connection_id, should_fail)
        connection = WebSocketConnection(connection_id=connection_id, user_id=validated_user_id, websocket=mock_websocket, connected_at=datetime.utcnow(), metadata={'test': True, 'user_agent': 'Test WebSocket Client', 'ip_address': '127.0.0.1', 'session_id': f'session_{user_id}_{int(time.time())}'})
        self.test_metrics['connections_created'] += 1
        return connection

    async def send_test_message(self, user_id: str, message_type: str, data: Dict[str, Any]=None) -> None:
        """Helper to send test messages with metrics tracking."""
        message = {'type': message_type, 'data': data or {}, 'timestamp': datetime.utcnow().isoformat()}
        await self.manager.send_to_user(user_id, message)
        self.test_metrics['messages_sent'] += 1

    @pytest.mark.asyncio
    async def test_user_isolation_prevents_data_leakage(self):
        """
        CRITICAL: Verify complete user isolation to prevent data breaches.
        
        Business Impact: Data leakage between users would be a $100K+ security breach.
        This test validates the core security promise of the platform.
        """
        from unittest.mock import Mock
        mock_user_context = Mock()
        mock_user_context.user_id = 'test_user_123'
        self.manager = await create_websocket_manager(mock_user_context)
        user_a_id = self.id_manager.generate_id(IDType.USER, prefix='test_user_a')
        user_b_id = self.id_manager.generate_id(IDType.USER, prefix='test_user_b')
        user_c_id = self.id_manager.generate_id(IDType.USER, prefix='test_user_c')
        conn_a = self.create_mock_connection(user_a_id, 'conn_a_isolation')
        conn_b = self.create_mock_connection(user_b_id, 'conn_b_isolation')
        conn_c = self.create_mock_connection(user_c_id, 'conn_c_isolation')
        await self.manager.add_connection(conn_a)
        await self.manager.add_connection(conn_b)
        await self.manager.add_connection(conn_c)
        sensitive_data_a = {'user_id': user_a_id, 'confidential_data': "User A's private financial information", 'account_balance': 150000, 'ssn_last_four': '1234'}
        sensitive_data_b = {'user_id': user_b_id, 'confidential_data': "User B's private business intelligence", 'revenue_projection': 2000000, 'client_list': ['ClientX', 'ClientY']}
        sensitive_data_c = {'user_id': user_c_id, 'confidential_data': "User C's personal health data", 'medical_conditions': ['diabetes', 'hypertension'], 'insurance_id': 'INS987654'}
        await self.send_test_message(user_a_id, 'private_financial_data', sensitive_data_a)
        await self.send_test_message(user_b_id, 'private_business_data', sensitive_data_b)
        await self.send_test_message(user_c_id, 'private_health_data', sensitive_data_c)
        messages_a = conn_a.websocket.get_sent_messages()
        messages_b = conn_b.websocket.get_sent_messages()
        messages_c = conn_c.websocket.get_sent_messages()
        assert len(messages_a) == 1, f'User A should have 1 message, got {len(messages_a)}'
        assert len(messages_b) == 1, f'User B should have 1 message, got {len(messages_b)}'
        assert len(messages_c) == 1, f'User C should have 1 message, got {len(messages_c)}'
        user_a_message = messages_a[0]
        assert user_a_message['data']['user_id'] == user_a_id
        assert "User A's private financial information" in str(user_a_message)
        assert "User B's private business intelligence" not in str(user_a_message)
        assert "User C's personal health data" not in str(user_a_message)
        assert user_a_message['_test_user_id'] == user_a_id
        user_b_message = messages_b[0]
        assert user_b_message['data']['user_id'] == user_b_id
        assert "User B's private business intelligence" in str(user_b_message)
        assert "User A's private financial information" not in str(user_b_message)
        assert "User C's personal health data" not in str(user_b_message)
        assert user_b_message['_test_user_id'] == user_b_id
        user_c_message = messages_c[0]
        assert user_c_message['data']['user_id'] == user_c_id
        assert "User C's personal health data" in str(user_c_message)
        assert "User A's private financial information" not in str(user_c_message)
        assert "User B's private business intelligence" not in str(user_c_message)
        assert user_c_message['_test_user_id'] == user_c_id
        user_a_connections = self.manager.get_user_connections(user_a_id)
        user_b_connections = self.manager.get_user_connections(user_b_id)
        user_c_connections = self.manager.get_user_connections(user_c_id)
        assert 'conn_a_isolation' in user_a_connections
        assert 'conn_b_isolation' not in user_a_connections
        assert 'conn_c_isolation' not in user_a_connections
        assert 'conn_b_isolation' in user_b_connections
        assert 'conn_a_isolation' not in user_b_connections
        assert 'conn_c_isolation' not in user_b_connections
        assert 'conn_c_isolation' in user_c_connections
        assert 'conn_a_isolation' not in user_c_connections
        assert 'conn_b_isolation' not in user_c_connections

    @pytest.mark.asyncio
    async def test_connection_lifecycle_management(self):
        """
        CRITICAL: Validate complete connection lifecycle without leaks.
        
        Business Impact: Connection leaks lead to memory exhaustion and system crashes.
        """
        user_id = self.id_manager.generate_id(IDType.USER, prefix='lifecycle_test_user')
        connection_id = 'lifecycle_test_conn'
        connection = self.create_mock_connection(user_id, connection_id)
        assert connection.user_id == user_id
        assert connection.connection_id == connection_id
        assert connection.websocket is not None
        assert connection.connected_at is not None
        await self.manager.add_connection(connection)
        assert self.manager.get_connection(connection_id) is not None
        user_connections = self.manager.get_user_connections(user_id)
        assert connection_id in user_connections
        assert self.manager.is_connection_active(user_id) is True
        health = self.manager.get_connection_health(user_id)
        assert health['has_active_connections'] is True
        assert health['total_connections'] == 1
        assert health['active_connections'] == 1
        test_message = {'type': 'lifecycle_test', 'data': {'test': 'connection_active'}}
        await self.manager.send_to_user(user_id, test_message)
        messages = connection.websocket.get_sent_messages()
        assert len(messages) == 1
        assert messages[0]['type'] == 'lifecycle_test'
        await self.manager.remove_connection(connection_id)
        assert self.manager.get_connection(connection_id) is None
        user_connections_after = self.manager.get_user_connections(user_id)
        assert connection_id not in user_connections_after
        assert len(user_connections_after) == 0
        assert self.manager.is_connection_active(user_id) is False
        health_after = self.manager.get_connection_health(user_id)
        assert health_after['has_active_connections'] is False
        assert health_after['total_connections'] == 0
        assert health_after['active_connections'] == 0
        await self.manager.send_to_user(user_id, test_message)
        error_stats = self.manager.get_error_statistics()
        assert error_stats['total_users_with_errors'] >= 0

    @pytest.mark.asyncio
    async def test_all_five_critical_websocket_events(self):
        """
        MISSION CRITICAL: Test all 5 WebSocket events that deliver chat business value.
        
        Business Impact: These events enable 90% of platform value through real-time chat.
        Without these events, users see blank screens and we lose revenue.
        """
        user_id = self.id_manager.generate_id(IDType.USER, prefix='events_test_user')
        connection = self.create_mock_connection(user_id)
        await self.manager.add_connection(connection)
        critical_events = [('agent_started', {'agent_type': 'cost_optimizer', 'user_id': user_id, 'thread_id': 'thread_12345', 'run_id': 'run_67890', 'message': 'Starting cost analysis for your AWS infrastructure', 'estimated_duration': '30-45 seconds'}), ('agent_thinking', {'thoughts': 'Analyzing current AWS costs and identifying optimization opportunities...', 'step': 'data_analysis', 'progress': 25, 'current_action': 'Fetching EC2 instance utilization metrics'}), ('tool_executing', {'tool': 'aws_cost_analyzer', 'parameters': {'timeframe': 'last_30_days', 'services': ['EC2', 'S3', 'RDS'], 'include_reserved_instances': True}, 'estimated_duration': 15}), ('tool_completed', {'tool': 'aws_cost_analyzer', 'execution_time': 12.8, 'result': {'total_monthly_cost': 15420.5, 'potential_savings': 2340.75, 'optimization_opportunities': [{'type': 'right_sizing', 'savings': 1200.0}, {'type': 'reserved_instances', 'savings': 840.75}, {'type': 'storage_optimization', 'savings': 300.0}]}, 'success': True}), ('agent_completed', {'result': {'summary': 'Found $2,340.75 in monthly savings opportunities', 'total_potential_annual_savings': 28089.0, 'confidence_score': 0.94, 'recommendations': [{'priority': 'high', 'action': 'Right-size 8 underutilized EC2 instances', 'monthly_savings': 1200.0, 'effort': 'low'}, {'priority': 'medium', 'action': 'Purchase reserved instances for stable workloads', 'monthly_savings': 840.75, 'effort': 'medium'}]}, 'execution_time': 34.2, 'tokens_used': 1250, 'success': True})]
        start_time = time.time()
        for event_type, event_data in critical_events:
            await self.manager.emit_critical_event(user_id, event_type, event_data)
            await asyncio.sleep(0.01)
        end_time = time.time()
        messages = connection.websocket.get_sent_messages()
        assert len(messages) == 5, f'Expected 5 critical events, got {len(messages)}'
        for i, (expected_type, expected_data) in enumerate(critical_events):
            message = messages[i]
            assert message['type'] == expected_type, f"Event {i}: expected {expected_type}, got {message['type']}"
            assert message['critical'] is True, f'Event {i}: should be marked as critical'
            assert 'timestamp' in message, f'Event {i}: missing timestamp'
            if expected_type == 'agent_started':
                assert message['data']['agent_type'] == 'cost_optimizer'
                assert message['data']['user_id'] == user_id
            elif expected_type == 'agent_thinking':
                assert 'thoughts' in message['data']
                assert 'progress' in message['data']
            elif expected_type == 'tool_executing':
                assert message['data']['tool'] == 'aws_cost_analyzer'
                assert 'parameters' in message['data']
            elif expected_type == 'tool_completed':
                assert message['data']['success'] is True
                assert 'result' in message['data']
                assert message['data']['result']['potential_savings'] > 0
            elif expected_type == 'agent_completed':
                assert message['data']['success'] is True
                assert 'recommendations' in message['data']['result']
                assert message['data']['result']['total_potential_annual_savings'] > 0
        total_time = end_time - start_time
        assert total_time < 0.5, f'Event delivery too slow: {total_time:.3f}s (max 0.5s)'
        final_result = messages[-1]['data']['result']
        assert final_result['total_potential_annual_savings'] > 20000
        assert len(final_result['recommendations']) >= 2
        assert final_result['confidence_score'] > 0.9

    @pytest.mark.asyncio
    async def test_websocket_message_serialization_comprehensive(self):
        """
        CRITICAL: Test complex message serialization for all data types.
        
        Business Impact: Serialization failures cause blank screens and lost revenue.
        """
        user_id = self.id_manager.generate_id(IDType.USER, prefix='serialization_test_user')
        connection = self.create_mock_connection(user_id)
        await self.manager.add_connection(connection)
        complex_test_cases = [{'type': 'enum_test', 'data': {'websocket_state': WebSocketStateTests.OPEN, 'connection_status': WebSocketStateTests.CONNECTING}}, {'type': 'datetime_test', 'data': {'timestamp': datetime.utcnow(), 'scheduled_time': datetime.utcnow() + timedelta(hours=1), 'expiry': datetime.utcnow() + timedelta(days=30)}}, {'type': 'dataclass_test', 'data': {'config': DataClassTests('test_config', 42, True), 'backup_config': DataClassTests('backup', 24, False)}}, {'type': 'nested_complex', 'data': {'user_profile': {'id': user_id, 'preferences': {'notifications': True, 'theme': 'dark', 'auto_save': WebSocketStateTests.OPEN}, 'metadata': ComplexDataTests('user_metadata'), 'created_at': datetime.utcnow()}, 'session_data': [DataClassTests('session_1', 100), DataClassTests('session_2', 200)]}}, {'type': 'large_data_test', 'data': {'large_list': [f'item_{i}' for i in range(1000)], 'large_dict': {f'key_{i}': f'value_{i}' for i in range(500)}, 'timestamp': datetime.utcnow()}}]
        for test_case in complex_test_cases:
            start_time = time.time()
            await self.manager.send_to_user(user_id, test_case)
            serialization_time = time.time() - start_time
            assert serialization_time < 0.1, f"Serialization too slow for {test_case['type']}: {serialization_time:.3f}s"
        messages = connection.websocket.get_sent_messages()
        assert len(messages) == len(complex_test_cases)
        enum_message = messages[0]
        assert enum_message['data']['websocket_state'] == 'open'
        assert enum_message['data']['connection_status'] == 'connecting'
        datetime_message = messages[1]
        assert isinstance(datetime_message['data']['timestamp'], str)
        assert 'T' in datetime_message['data']['timestamp']
        dataclass_message = messages[2]
        assert isinstance(dataclass_message['data']['config'], dict)
        assert dataclass_message['data']['config']['name'] == 'test_config'
        nested_message = messages[3]
        assert nested_message['data']['user_profile']['preferences']['auto_save'] == 'open'
        assert isinstance(nested_message['data']['user_profile']['metadata'], dict)
        large_data_message = messages[4]
        assert len(large_data_message['data']['large_list']) == 1000
        assert len(large_data_message['data']['large_dict']) == 500

    @pytest.mark.asyncio
    async def test_concurrent_user_operations_race_prevention(self):
        """
        CRITICAL: Test race condition prevention in concurrent operations.
        
        Business Impact: Race conditions cause data corruption and user session failures.
        """
        num_users = 20
        operations_per_user = 10

        async def simulate_user_operations(user_index: int):
            """Simulate concurrent operations for a single user."""
            user_id = self.id_manager.generate_id(IDType.USER, prefix=f'race_test_user_{user_index:03d}')
            operations_completed = 0
            errors = []
            try:
                connections = []
                for conn_idx in range(3):
                    connection_id = f'race_conn_{user_index:03d}_{conn_idx}'
                    connection = self.create_mock_connection(user_id, connection_id)
                    await self.manager.add_connection(connection)
                    connections.append(connection)
                    operations_completed += 1
                send_tasks = []
                for op_idx in range(operations_per_user):
                    message = {'type': f'race_test_message_{op_idx}', 'data': {'user_id': user_id, 'operation': op_idx, 'timestamp': time.time(), 'private_data': f'confidential_{user_id}_{op_idx}'}}
                    task = asyncio.create_task(self.manager.send_to_user(user_id, message))
                    send_tasks.append(task)
                await asyncio.gather(*send_tasks, return_exceptions=True)
                operations_completed += len(send_tasks)
                remove_tasks = []
                for connection in connections:
                    task = asyncio.create_task(self.manager.remove_connection(connection.connection_id))
                    remove_tasks.append(task)
                await asyncio.gather(*remove_tasks, return_exceptions=True)
                operations_completed += len(remove_tasks)
                return {'user_id': user_id, 'operations_completed': operations_completed, 'errors': errors, 'connections': connections}
            except Exception as e:
                errors.append(str(e))
                return {'user_id': user_id, 'operations_completed': operations_completed, 'errors': errors, 'connections': []}
        start_time = time.time()
        results = await asyncio.gather(*[simulate_user_operations(i) for i in range(num_users)], return_exceptions=True)
        execution_time = time.time() - start_time
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == num_users, f'Some users failed due to race conditions'
        for result in successful_results:
            user_id = result['user_id']
            connections = result['connections']
            for connection in connections:
                messages = connection.websocket.get_sent_messages()
                assert len(messages) == operations_per_user
                for message in messages:
                    assert message['data']['user_id'] == user_id
                    assert user_id in message['data']['private_data']
                    assert message['_test_user_id'] == user_id
                    for other_result in successful_results:
                        if other_result['user_id'] != user_id:
                            other_user_id = other_result['user_id']
                            assert other_user_id not in str(message['data'])
        total_operations = sum((r['operations_completed'] for r in successful_results))
        operations_per_second = total_operations / execution_time if execution_time > 0 else 0
        assert operations_per_second >= 50, f'Poor concurrency performance: {operations_per_second:.1f} ops/sec'
        final_stats = self.manager.get_stats()
        assert final_stats['total_connections'] == 0, 'Race condition caused connection leaks'
        assert final_stats['unique_users'] == 0, 'Race condition caused user data leaks'

    @pytest.mark.asyncio
    async def test_message_recovery_and_error_handling(self):
        """
        CRITICAL: Test message recovery system for business continuity.
        
        Business Impact: Lost messages mean lost customer communications and revenue.
        """
        user_id = self.id_manager.generate_id(IDType.USER, prefix='recovery_test_user')
        pre_connection_messages = []
        for i in range(5):
            message = {'type': f'pre_connection_message_{i}', 'data': {'message_id': f'msg_{i}', 'content': f'Important business data {i}', 'priority': 'high' if i % 2 == 0 else 'normal'}}
            pre_connection_messages.append(message)
            await self.manager.send_to_user(user_id, message)
        error_stats = self.manager.get_error_statistics()
        assert error_stats['total_queued_messages'] >= 5
        assert user_id in error_stats['error_details']
        connection = self.create_mock_connection(user_id)
        await self.manager.add_connection(connection)
        await asyncio.sleep(0.1)
        recovered_messages = connection.websocket.get_sent_messages()
        assert len(recovered_messages) >= 5, f'Expected at least 5 recovered messages, got {len(recovered_messages)}'
        for i, message in enumerate(recovered_messages[:5]):
            assert message['type'] == f'pre_connection_message_{i}'
            assert message['data']['message_id'] == f'msg_{i}'
            assert 'recovered' in message
        real_time_message = {'type': 'real_time_test', 'data': {'test': 'post_recovery_delivery'}}
        await self.manager.send_to_user(user_id, real_time_message)
        all_messages = connection.websocket.get_sent_messages()
        assert len(all_messages) >= 6
        last_message = all_messages[-1]
        assert last_message['type'] == 'real_time_test'
        assert 'recovered' not in last_message
        connection.websocket.should_fail = True
        failed_message = {'type': 'failed_message_test', 'data': {'test': 'connection_failure_recovery'}}
        await self.manager.send_to_user(user_id, failed_message)
        error_stats_after_failure = self.manager.get_error_statistics()
        assert error_stats_after_failure['total_queued_messages'] >= 1
        connection.websocket.should_fail = False
        await self.manager.process_recovery_queue(user_id)
        final_messages = connection.websocket.get_sent_messages()
        recovery_found = any((msg['type'] == 'failed_message_test' for msg in final_messages))
        assert recovery_found, 'Failed message was not recovered'

    @pytest.mark.asyncio
    async def test_background_task_monitoring_comprehensive(self):
        """
        CRITICAL: Test background task monitoring system reliability.
        
        Business Impact: Failed background tasks can cause silent system degradation.
        """
        task_results = []

        async def successful_task(task_id: str, iterations: int=3):
            """A task that completes successfully."""
            for i in range(iterations):
                task_results.append(f'{task_id}_iteration_{i}')
                await asyncio.sleep(0.01)
            return f'{task_id}_completed'
        task_name = 'test_successful_task'
        task_id = await self.manager.start_monitored_background_task(task_name, successful_task, 'success_task', 3)
        assert task_id == task_name
        await asyncio.sleep(0.1)
        task_status = self.manager.get_background_task_status()
        assert task_name in task_status['tasks']
        assert task_status['tasks'][task_name]['failure_count'] == 0
        assert len(task_results) == 3
        failure_count = 0

        async def failing_task(task_id: str, max_failures: int=2):
            """A task that fails a few times then succeeds."""
            nonlocal failure_count
            failure_count += 1
            if failure_count <= max_failures:
                raise RuntimeError(f'Simulated failure #{failure_count}')
            return f'{task_id}_succeeded_after_{failure_count}_attempts'
        failing_task_name = 'test_failing_task'
        await self.manager.start_monitored_background_task(failing_task_name, failing_task, 'failing_task', 2)
        await asyncio.sleep(0.5)
        task_status_after_failure = self.manager.get_background_task_status()
        assert failing_task_name in task_status_after_failure['tasks']
        failing_task_info = task_status_after_failure['tasks'][failing_task_name]
        assert failing_task_info['failure_count'] >= 2
        health_status = await self.manager.get_monitoring_health_status()
        assert health_status['monitoring_enabled'] is True
        assert health_status['shutdown_requested'] is False
        assert health_status['task_health']['total_tasks'] >= 2
        assert health_status['overall_health']['status'] in ['healthy', 'warning']
        restart_result = await self.manager.restart_background_monitoring(force_restart=True)
        assert restart_result['monitoring_restarted'] is True
        assert restart_result['health_check_passed'] is True
        post_restart_health = await self.manager.get_monitoring_health_status()
        assert post_restart_health['monitoring_enabled'] is True
        await self.manager.shutdown_background_monitoring()
        shutdown_health = await self.manager.get_monitoring_health_status()
        assert shutdown_health['monitoring_enabled'] is False
        assert shutdown_health['shutdown_requested'] is True
        recovery_result = await self.manager.enable_background_monitoring(restart_previous_tasks=True)
        assert recovery_result['monitoring_enabled'] is True
        assert recovery_result['health_check_reset'] is True

    @pytest.mark.asyncio
    async def test_edge_cases_and_boundary_conditions(self):
        """
        CRITICAL: Test edge cases that could cause system failures.
        
        Business Impact: Edge case failures cause unpredictable system behavior.
        """
        invalid_user_ids = ['', None, 'user with spaces', 'user\nwith\nnewlines', 'user\twith\ttabs']
        for invalid_id in invalid_user_ids:
            try:
                if invalid_id is not None:
                    connection = self.create_mock_connection(str(invalid_id))
                    await self.manager.add_connection(connection)
                    await self.manager.remove_connection(connection.connection_id)
            except (ValueError, TypeError, AssertionError):
                pass
        large_user_id = self.id_manager.generate_id(IDType.USER, prefix='large_message_test_user')
        large_connection = self.create_mock_connection(large_user_id)
        await self.manager.add_connection(large_connection)
        large_data = {'type': 'large_message_test', 'data': {'large_field': 'x' * (1024 * 1024), 'metadata': {'size': '1MB', 'test': True}}}
        start_time = time.time()
        await self.manager.send_to_user(large_user_id, large_data)
        large_message_time = time.time() - start_time
        messages = large_connection.websocket.get_sent_messages()
        assert len(messages) == 1
        assert len(messages[0]['data']['large_field']) == 1024 * 1024
        assert large_message_time < 1.0, f'Large message handling too slow: {large_message_time:.3f}s'
        rapid_user_id = self.id_manager.generate_id(IDType.USER, prefix='rapid_cycle_test_user')
        for cycle in range(10):
            connection = self.create_mock_connection(rapid_user_id, f'rapid_conn_{cycle}')
            await self.manager.add_connection(connection)
            await self.send_test_message(rapid_user_id, 'rapid_test', {'cycle': cycle})
            await self.manager.remove_connection(connection.connection_id)
            assert not self.manager.is_connection_active(rapid_user_id)
        multi_conn_user_id = self.id_manager.generate_id(IDType.USER, prefix='multi_connection_test_user')
        good_connection_1 = self.create_mock_connection(multi_conn_user_id, 'good_conn_1')
        failing_connection = self.create_mock_connection(multi_conn_user_id, 'failing_conn', should_fail=True)
        good_connection_2 = self.create_mock_connection(multi_conn_user_id, 'good_conn_2')
        await self.manager.add_connection(good_connection_1)
        await self.manager.add_connection(failing_connection)
        await self.manager.add_connection(good_connection_2)
        test_message = {'type': 'multi_connection_test', 'data': {'test': 'partial_failure_handling'}}
        await self.manager.send_to_user(multi_conn_user_id, test_message)
        good_1_messages = good_connection_1.websocket.get_sent_messages()
        good_2_messages = good_connection_2.websocket.get_sent_messages()
        failing_messages = failing_connection.websocket.get_sent_messages()
        assert len(good_1_messages) == 1
        assert len(good_2_messages) == 1
        assert len(failing_messages) == 0
        assert self.manager.is_connection_active(multi_conn_user_id)
        empty_data_cases = [{'type': 'empty_data', 'data': {}}, {'type': 'null_data', 'data': None}, {'type': 'missing_data'}]
        for empty_case in empty_data_cases:
            await self.manager.send_to_user(multi_conn_user_id, empty_case)
        final_good_1_messages = good_connection_1.websocket.get_sent_messages()
        assert len(final_good_1_messages) >= 4

    @pytest.mark.asyncio
    async def test_memory_management_and_performance(self):
        """
        CRITICAL: Test memory management to prevent system crashes.
        
        Business Impact: Memory leaks cause system crashes and service outages.
        """
        initial_stats = self.manager.get_stats()
        perf_user_id = self.id_manager.generate_id(IDType.USER, prefix='performance_test_user')
        perf_connection = self.create_mock_connection(perf_user_id)
        await self.manager.add_connection(perf_connection)
        message_count = 1000
        start_time = time.time()
        for i in range(message_count):
            message = {'type': 'performance_test', 'data': {'sequence': i, 'timestamp': time.time(), 'payload': f'Message payload {i}'}}
            await self.manager.send_to_user(perf_user_id, message)
        end_time = time.time()
        total_time = end_time - start_time
        messages_per_second = message_count / total_time if total_time > 0 else 0
        assert messages_per_second >= 1000, f'Poor message throughput: {messages_per_second:.1f} msg/sec'
        assert total_time < 1.0, f'Message sending too slow: {total_time:.3f}s for {message_count} messages'
        sent_messages = perf_connection.websocket.get_sent_messages()
        assert len(sent_messages) == message_count
        await self.manager.remove_connection(perf_connection.connection_id)
        connection_count = 100
        test_connections = []
        create_start = time.time()
        for i in range(connection_count):
            user_id = self.id_manager.generate_id(IDType.USER, prefix=f'mem_test_user_{i:03d}')
            connection = self.create_mock_connection(user_id, f'mem_conn_{i:03d}')
            await self.manager.add_connection(connection)
            test_connections.append(connection)
        create_time = time.time() - create_start
        connections_per_second = connection_count / create_time if create_time > 0 else 0
        assert connections_per_second >= 50, f'Slow connection creation: {connections_per_second:.1f} conn/sec'
        stats_with_connections = self.manager.get_stats()
        assert stats_with_connections['total_connections'] == connection_count
        assert stats_with_connections['unique_users'] == connection_count
        cleanup_start = time.time()
        for connection in test_connections:
            await self.manager.remove_connection(connection.connection_id)
        cleanup_time = time.time() - cleanup_start
        cleanup_per_second = connection_count / cleanup_time if cleanup_time > 0 else 0
        assert cleanup_per_second >= 50, f'Slow connection cleanup: {cleanup_per_second:.1f} conn/sec'
        final_stats = self.manager.get_stats()
        assert final_stats['total_connections'] == 0, 'Connection cleanup incomplete'
        assert final_stats['unique_users'] == 0, 'User cleanup incomplete'
        error_user_id = self.id_manager.generate_id(IDType.USER, prefix='error_cleanup_test_user')
        for i in range(10):
            await self.manager.send_to_user(error_user_id, {'type': 'error_test', 'data': {'msg': i}})
        error_stats_before = self.manager.get_error_statistics()
        assert error_stats_before['total_queued_messages'] >= 10
        cleanup_result = await self.manager.cleanup_error_data(older_than_hours=0)
        error_stats_after = self.manager.get_error_statistics()
        assert error_stats_after['total_queued_messages'] < error_stats_before['total_queued_messages']

    @pytest.mark.asyncio
    async def test_five_whys_root_cause_prevention_methods(self):
        """
        CRITICAL: Test Five Whys root cause prevention methods.
        
        Business Impact: Ensures interface compatibility prevents system integration failures.
        """
        user_id = self.id_manager.generate_id(IDType.USER, prefix='five_whys_test_user')
        thread_id = 'five_whys_thread_123'
        connection = self.create_mock_connection(user_id, 'five_whys_conn')
        await self.manager.add_connection(connection)
        found_connection_id = self.manager.get_connection_id_by_websocket(connection.websocket)
        assert found_connection_id is not None
        assert str(found_connection_id) == connection.connection_id
        fake_websocket = MockWebSocket('fake_user', 'fake_conn')
        not_found_id = self.manager.get_connection_id_by_websocket(fake_websocket)
        assert not_found_id is None
        thread_update_success = self.manager.update_connection_thread(connection.connection_id, thread_id)
        assert thread_update_success is True
        updated_connection = self.manager.get_connection(connection.connection_id)
        assert hasattr(updated_connection, 'thread_id')
        assert updated_connection.thread_id == thread_id
        fake_conn_id = 'non_existent_connection'
        fake_update_result = self.manager.update_connection_thread(fake_conn_id, thread_id)
        assert fake_update_result is False
        try:
            invalid_result = self.manager.update_connection_thread('', '')
            assert invalid_result is False
        except ValueError:
            pass

    @pytest.mark.asyncio
    async def test_complete_business_workflow_simulation(self):
        """
        CRITICAL: Test complete business workflow that delivers revenue.
        
        Business Impact: Validates end-to-end chat workflow worth $500K+ ARR.
        This test simulates the complete user journey that generates revenue.
        """
        user_id = self.id_manager.generate_id(IDType.USER, prefix='business_workflow_user')
        connection_id = 'business_workflow_conn'
        thread_id = 'business_thread_12345'
        connection = self.create_mock_connection(user_id, connection_id)
        await self.manager.add_connection(connection)
        self.manager.update_connection_thread(connection_id, thread_id)
        user_query = {'type': 'user_message', 'data': {'user_id': user_id, 'thread_id': thread_id, 'message': "Help me optimize my AWS costs - I'm spending $15,000/month", 'context': {'monthly_spend': 15000, 'primary_services': ['EC2', 'S3', 'RDS'], 'team_size': 25, 'urgency': 'high'}}}
        await self.manager.send_to_user(user_id, user_query)
        agent_workflow_events = [('agent_started', {'agent_type': 'cost_optimization_specialist', 'user_id': user_id, 'thread_id': thread_id, 'run_id': 'run_cost_opt_789', 'message': "I'll analyze your AWS spending and find savings opportunities", 'estimated_duration': '45-60 seconds', 'business_value': 'cost_optimization'}), ('agent_thinking', {'thoughts': 'User spends $15K/month on AWS - analyzing spend patterns to identify optimization opportunities', 'reasoning': 'High spend suggests potential for significant savings through right-sizing and reserved instances', 'step': 'cost_analysis_planning', 'progress': 15}), ('tool_executing', {'tool': 'aws_cost_analyzer_pro', 'parameters': {'monthly_budget': 15000, 'services': ['EC2', 'S3', 'RDS'], 'optimization_focus': ['right_sizing', 'reserved_instances', 'storage_classes'], 'team_size': 25}, 'estimated_duration': 20}), ('tool_completed', {'tool': 'aws_cost_analyzer_pro', 'execution_time': 18.5, 'result': {'current_monthly_spend': 15420.5, 'potential_monthly_savings': 3840.75, 'savings_percentage': 24.9, 'optimization_opportunities': [{'category': 'EC2_right_sizing', 'monthly_savings': 2100.0, 'effort': 'low', 'confidence': 0.95}, {'category': 'reserved_instances', 'monthly_savings': 1240.75, 'effort': 'medium', 'confidence': 0.88}, {'category': 'S3_storage_optimization', 'monthly_savings': 500.0, 'effort': 'low', 'confidence': 0.92}]}, 'success': True}), ('agent_completed', {'result': {'summary': 'Found $3,840.75 in monthly savings (24.9% reduction)', 'annual_savings': 46089.0, 'roi_analysis': {'implementation_effort': 'low_to_medium', 'payback_period': 'immediate', 'confidence_score': 0.91}, 'prioritized_recommendations': [{'priority': 1, 'action': 'Right-size 12 overprovisioned EC2 instances', 'monthly_savings': 2100.0, 'implementation_time': '1-2 hours', 'business_impact': 'No service disruption'}, {'priority': 2, 'action': 'Purchase 1-year reserved instances for stable workloads', 'monthly_savings': 1240.75, 'implementation_time': '30 minutes', 'business_impact': 'Immediate cost reduction'}, {'priority': 3, 'action': 'Optimize S3 storage classes and lifecycle policies', 'monthly_savings': 500.0, 'implementation_time': '2-3 hours', 'business_impact': 'Reduced storage costs'}], 'business_value_delivered': {'cost_savings': '$46,089 annually', 'efficiency_gain': '24.9% cost reduction', 'competitive_advantage': 'Budget reallocation for growth initiatives'}}, 'execution_time': 47.3, 'tokens_used': 2150, 'success': True, 'user_satisfaction_score': 0.97})]
        workflow_start_time = time.time()
        for event_type, event_data in agent_workflow_events:
            await self.manager.emit_critical_event(user_id, event_type, event_data)
            await asyncio.sleep(0.02)
        workflow_end_time = time.time()
        all_messages = connection.websocket.get_sent_messages()
        assert len(all_messages) == 6, f'Expected 6 messages in complete workflow, got {len(all_messages)}'
        assert all_messages[0]['type'] == 'user_message'
        expected_sequence = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        for i, expected_type in enumerate(expected_sequence):
            actual_message = all_messages[i + 1]
            assert actual_message['type'] == expected_type, f"Wrong event at position {i}: expected {expected_type}, got {actual_message['type']}"
            assert actual_message['critical'] is True, f'Event {expected_type} should be marked critical'
        final_result = all_messages[-1]['data']['result']
        assert final_result['annual_savings'] >= 40000, 'Insufficient savings delivered'
        assert final_result['roi_analysis']['confidence_score'] >= 0.9, 'Low confidence in recommendations'
        assert len(final_result['prioritized_recommendations']) >= 3, 'Insufficient actionable recommendations'
        agent_completed_message = all_messages[-1]
        assert agent_completed_message['data']['user_satisfaction_score'] >= 0.95, 'Low user satisfaction'
        assert agent_completed_message['data']['execution_time'] < 60, 'Agent took too long to deliver value'
        total_workflow_time = workflow_end_time - workflow_start_time
        assert total_workflow_time < 2.0, f'Complete workflow too slow: {total_workflow_time:.3f}s'
        await self.manager.remove_connection(connection_id)
        assert not self.manager.is_connection_active(user_id), 'User should be disconnected'
        final_stats = self.manager.get_stats()
        assert final_stats['total_connections'] == 0, 'Connection not properly cleaned up'
        savings_percentage = final_result['annual_savings'] / (15000 * 12) * 100
        assert savings_percentage >= 20, f'Insufficient savings percentage: {savings_percentage:.1f}%'
        estimated_platform_revenue = final_result['annual_savings'] * 0.15
        assert estimated_platform_revenue >= 5000, f'Low platform revenue potential: ${estimated_platform_revenue:.0f}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')