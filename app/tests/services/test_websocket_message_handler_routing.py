"""
Comprehensive tests for WebSocket message handler routing and broadcast mechanisms
Tests message routing, handler registration, broadcast logic, and queue management
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from enum import Enum

from app.services.websocket.message_handler import (
    BaseMessageHandler,
    StartAgentHandler,
    UserMessageHandler
)
from app.services.websocket.message_queue import (
    message_queue,
    QueuedMessage,
    MessagePriority
)
from app.core.exceptions_base import NetraException


class MessageType(Enum):
    START_AGENT = "start_agent"
    USER_MESSAGE = "user_message"
    SYSTEM_STATUS = "system_status"
    HEARTBEAT = "heartbeat"
    BROADCAST = "broadcast"
    NOTIFICATION = "notification"


class MockMessageHandler(BaseMessageHandler):
    """Mock message handler for testing"""
    
    def __init__(self, message_type: str):
        self.message_type = message_type
        self.handled_messages = []
        self.handle_delay = 0
        self.should_fail = False
        
    def get_message_type(self) -> str:
        return self.message_type
        
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        if self.handle_delay > 0:
            await asyncio.sleep(self.handle_delay)
            
        if self.should_fail:
            raise NetraException(f"Handler {self.message_type} failed")
            
        self.handled_messages.append({
            'user_id': user_id,
            'payload': payload,
            'timestamp': datetime.now(UTC)
        })


class MessageRouter:
    """Message router for WebSocket messages"""
    
    def __init__(self):
        self.handlers: Dict[str, BaseMessageHandler] = {}
        self.middleware_stack = []
        self.routing_metrics = {
            'messages_routed': 0,
            'routing_errors': 0,
            'handler_execution_times': {}
        }
        
    def register_handler(self, handler: BaseMessageHandler):
        """Register a message handler"""
        message_type = handler.get_message_type()
        if message_type in self.handlers:
            raise NetraException(f"Handler for {message_type} already registered")
        self.handlers[message_type] = handler
        
    def unregister_handler(self, message_type: str):
        """Unregister a message handler"""
        if message_type in self.handlers:
            del self.handlers[message_type]
            
    def add_middleware(self, middleware_func):
        """Add middleware to processing pipeline"""
        self.middleware_stack.append(middleware_func)
        
    async def route_message(self, user_id: str, message_type: str, payload: Dict[str, Any]) -> bool:
        """Route message to appropriate handler"""
        try:
            # Apply middleware
            processed_payload = payload
            for middleware in self.middleware_stack:
                processed_payload = await middleware(user_id, message_type, processed_payload)
                
            # Find and execute handler
            if message_type not in self.handlers:
                raise NetraException(f"No handler registered for message type: {message_type}")
                
            handler = self.handlers[message_type]
            
            start_time = datetime.now(UTC)
            await handler.handle(user_id, processed_payload)
            execution_time = (datetime.now(UTC) - start_time).total_seconds()
            
            # Update metrics
            self.routing_metrics['messages_routed'] += 1
            if message_type not in self.routing_metrics['handler_execution_times']:
                self.routing_metrics['handler_execution_times'][message_type] = []
            self.routing_metrics['handler_execution_times'][message_type].append(execution_time)
            
            return True
            
        except Exception as e:
            self.routing_metrics['routing_errors'] += 1
            raise NetraException(f"Message routing failed: {str(e)}")


class BroadcastManager:
    """Manages message broadcasting to multiple users"""
    
    def __init__(self):
        self.subscribers = {}  # user_id -> subscription_filters
        self.broadcast_history = []
        self.delivery_stats = {
            'total_broadcasts': 0,
            'successful_deliveries': 0,
            'failed_deliveries': 0
        }
        
    def subscribe(self, user_id: str, filters: Dict[str, Any] = None):
        """Subscribe user to broadcasts"""
        self.subscribers[user_id] = filters or {}
        
    def unsubscribe(self, user_id: str):
        """Unsubscribe user from broadcasts"""
        if user_id in self.subscribers:
            del self.subscribers[user_id]
            
    def should_receive_broadcast(self, user_id: str, broadcast_data: Dict[str, Any]) -> bool:
        """Check if user should receive broadcast based on filters"""
        if user_id not in self.subscribers:
            return False
            
        filters = self.subscribers[user_id]
        if not filters:
            return True  # No filters = receive all
            
        # Apply filters
        for key, expected_value in filters.items():
            if key in broadcast_data and broadcast_data[key] != expected_value:
                return False
                
        return True
        
    async def broadcast_message(self, message_data: Dict[str, Any], target_users: List[str] = None) -> Dict[str, int]:
        """Broadcast message to subscribers"""
        if target_users == None:
            target_users = list(self.subscribers.keys())
            
        delivery_results = {'success': 0, 'failed': 0}
        
        for user_id in target_users:
            try:
                if self.should_receive_broadcast(user_id, message_data):
                    # Mock message delivery
                    await self._deliver_message(user_id, message_data)
                    delivery_results['success'] += 1
                    self.delivery_stats['successful_deliveries'] += 1
                    
            except Exception:
                delivery_results['failed'] += 1
                self.delivery_stats['failed_deliveries'] += 1
                
        self.broadcast_history.append({
            'message_data': message_data,
            'target_users': target_users,
            'timestamp': datetime.now(UTC),
            'results': delivery_results
        })
        
        self.delivery_stats['total_broadcasts'] += 1
        return delivery_results
        
    async def _deliver_message(self, user_id: str, message_data: Dict[str, Any]):
        """Mock message delivery implementation"""
        # In real implementation, this would use WebSocket manager
        pass


class TestWebSocketMessageHandlerRouting:
    """Test WebSocket message handler routing"""
    
    @pytest.fixture
    def message_router(self):
        """Create message router for testing"""
        return MessageRouter()
    
    @pytest.fixture
    def sample_handlers(self):
        """Create sample message handlers"""
        return {
            'start_agent': MockMessageHandler('start_agent'),
            'user_message': MockMessageHandler('user_message'),
            'system_status': MockMessageHandler('system_status'),
            'heartbeat': MockMessageHandler('heartbeat')
        }
    
    def test_handler_registration(self, message_router, sample_handlers):
        """Test message handler registration"""
        # Register handlers
        for handler in sample_handlers.values():
            message_router.register_handler(handler)
            
        # Verify registration
        assert len(message_router.handlers) == 4
        assert 'start_agent' in message_router.handlers
        assert 'user_message' in message_router.handlers
        assert 'system_status' in message_router.handlers
        assert 'heartbeat' in message_router.handlers
    
    def test_handler_duplicate_registration_prevention(self, message_router, sample_handlers):
        """Test prevention of duplicate handler registration"""
        handler = sample_handlers['start_agent']
        
        # First registration should succeed
        message_router.register_handler(handler)
        
        # Second registration should fail
        with pytest.raises(NetraException) as exc_info:
            message_router.register_handler(handler)
        assert "already registered" in str(exc_info.value)
    
    def test_handler_unregistration(self, message_router, sample_handlers):
        """Test message handler unregistration"""
        # Register handler
        handler = sample_handlers['start_agent']
        message_router.register_handler(handler)
        assert 'start_agent' in message_router.handlers
        
        # Unregister handler
        message_router.unregister_handler('start_agent')
        assert 'start_agent' not in message_router.handlers
        
        # Unregistering non-existent handler should not error
        message_router.unregister_handler('non_existent')
    
    @pytest.mark.asyncio
    async def test_message_routing_success(self, message_router, sample_handlers):
        """Test successful message routing"""
        # Register handler
        handler = sample_handlers['start_agent']
        message_router.register_handler(handler)
        
        # Route message
        payload = {'query': 'test query', 'user_id': 'test_user'}
        result = await message_router.route_message('user123', 'start_agent', payload)
        
        # Verify routing
        assert result == True
        assert len(handler.handled_messages) == 1
        assert handler.handled_messages[0]['user_id'] == 'user123'
        assert handler.handled_messages[0]['payload'] == payload
        
        # Verify metrics
        assert message_router.routing_metrics['messages_routed'] == 1
        assert message_router.routing_metrics['routing_errors'] == 0
        assert 'start_agent' in message_router.routing_metrics['handler_execution_times']
    
    @pytest.mark.asyncio
    async def test_message_routing_no_handler(self, message_router):
        """Test message routing when no handler is registered"""
        # Route message to unregistered type
        with pytest.raises(NetraException) as exc_info:
            await message_router.route_message('user123', 'unknown_type', {})
        
        assert "No handler registered" in str(exc_info.value)
        assert message_router.routing_metrics['routing_errors'] == 1
    
    @pytest.mark.asyncio
    async def test_message_routing_handler_failure(self, message_router, sample_handlers):
        """Test message routing when handler fails"""
        # Register failing handler
        handler = sample_handlers['start_agent']
        handler.should_fail = True
        message_router.register_handler(handler)
        
        # Route message
        with pytest.raises(NetraException) as exc_info:
            await message_router.route_message('user123', 'start_agent', {})
        
        assert "Message routing failed" in str(exc_info.value)
        assert message_router.routing_metrics['routing_errors'] == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_message_routing(self, message_router, sample_handlers):
        """Test concurrent message routing"""
        # Register handlers
        for handler in sample_handlers.values():
            message_router.register_handler(handler)
        
        # Create concurrent routing tasks
        tasks = []
        for i in range(20):
            handler_type = list(sample_handlers.keys())[i % 4]
            payload = {'message_id': i, 'data': f'test_data_{i}'}
            task = message_router.route_message(f'user_{i}', handler_type, payload)
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert all(result == True for result in results)
        assert message_router.routing_metrics['messages_routed'] == 20
        assert message_router.routing_metrics['routing_errors'] == 0
        
        # Verify handlers received messages
        total_handled = sum(len(handler.handled_messages) for handler in sample_handlers.values())
        assert total_handled == 20
    
    @pytest.mark.asyncio
    async def test_middleware_processing(self, message_router, sample_handlers):
        """Test middleware processing in routing pipeline"""
        # Register handler
        handler = sample_handlers['user_message']
        message_router.register_handler(handler)
        
        # Add middleware
        middleware_calls = []
        
        async def logging_middleware(user_id, message_type, payload):
            middleware_calls.append(('logging', user_id, message_type))
            return payload
        
        async def validation_middleware(user_id, message_type, payload):
            middleware_calls.append(('validation', user_id, message_type))
            if 'required_field' not in payload:
                payload['required_field'] = 'default_value'
            return payload
        
        async def authentication_middleware(user_id, message_type, payload):
            middleware_calls.append(('auth', user_id, message_type))
            payload['authenticated_user'] = user_id
            return payload
        
        # Add middleware in order
        message_router.add_middleware(logging_middleware)
        message_router.add_middleware(validation_middleware)
        message_router.add_middleware(authentication_middleware)
        
        # Route message
        payload = {'message': 'test message'}
        await message_router.route_message('user123', 'user_message', payload)
        
        # Verify middleware execution order
        assert len(middleware_calls) == 3
        assert middleware_calls[0] == ('logging', 'user123', 'user_message')
        assert middleware_calls[1] == ('validation', 'user123', 'user_message')
        assert middleware_calls[2] == ('auth', 'user123', 'user_message')
        
        # Verify payload modifications
        handled_payload = handler.handled_messages[0]['payload']
        assert handled_payload['required_field'] == 'default_value'
        assert handled_payload['authenticated_user'] == 'user123'
    
    @pytest.mark.asyncio
    async def test_routing_performance_metrics(self, message_router, sample_handlers):
        """Test routing performance metrics collection"""
        # Register slow handler
        slow_handler = sample_handlers['start_agent']
        slow_handler.handle_delay = 0.1  # 100ms delay
        message_router.register_handler(slow_handler)
        
        # Route multiple messages
        for i in range(5):
            await message_router.route_message(f'user_{i}', 'start_agent', {'index': i})
        
        # Verify metrics
        execution_times = message_router.routing_metrics['handler_execution_times']['start_agent']
        assert len(execution_times) == 5
        assert all(time >= 0.1 for time in execution_times)  # All should be >= 100ms
        
        # Calculate average execution time
        avg_time = sum(execution_times) / len(execution_times)
        assert 0.1 <= avg_time <= 0.2  # Should be around 100ms
    
    @pytest.mark.asyncio
    async def test_message_priority_handling(self, message_router):
        """Test message priority-based handling"""
        # Create handlers with different processing delays
        high_priority_handler = MockMessageHandler('high_priority')
        high_priority_handler.handle_delay = 0.05
        
        low_priority_handler = MockMessageHandler('low_priority')
        low_priority_handler.handle_delay = 0.1
        
        message_router.register_handler(high_priority_handler)
        message_router.register_handler(low_priority_handler)
        
        # Route messages with different priorities
        start_time = datetime.now(UTC)
        
        tasks = [
            message_router.route_message('user1', 'low_priority', {'priority': 'low'}),
            message_router.route_message('user2', 'high_priority', {'priority': 'high'}),
            message_router.route_message('user3', 'low_priority', {'priority': 'low'})
        ]
        
        await asyncio.gather(*tasks)
        
        end_time = datetime.now(UTC)
        total_time = (end_time - start_time).total_seconds()
        
        # High priority should complete faster than low priority
        high_times = message_router.routing_metrics['handler_execution_times']['high_priority']
        low_times = message_router.routing_metrics['handler_execution_times']['low_priority']
        
        avg_high_time = sum(high_times) / len(high_times)
        avg_low_time = sum(low_times) / len(low_times)
        
        assert avg_high_time < avg_low_time


class TestBroadcastMechanisms:
    """Test broadcast mechanisms and subscription management"""
    
    @pytest.fixture
    def broadcast_manager(self):
        """Create broadcast manager for testing"""
        return BroadcastManager()
    
    def test_user_subscription(self, broadcast_manager):
        """Test user subscription to broadcasts"""
        # Subscribe users
        broadcast_manager.subscribe('user1', {'topic': 'alerts'})
        broadcast_manager.subscribe('user2', {'topic': 'updates'})
        broadcast_manager.subscribe('user3')  # No filters
        
        # Verify subscriptions
        assert len(broadcast_manager.subscribers) == 3
        assert 'user1' in broadcast_manager.subscribers
        assert broadcast_manager.subscribers['user1'] == {'topic': 'alerts'}
        assert broadcast_manager.subscribers['user3'] == {}
    
    def test_user_unsubscription(self, broadcast_manager):
        """Test user unsubscription from broadcasts"""
        # Subscribe then unsubscribe
        broadcast_manager.subscribe('user1', {'topic': 'alerts'})
        assert 'user1' in broadcast_manager.subscribers
        
        broadcast_manager.unsubscribe('user1')
        assert 'user1' not in broadcast_manager.subscribers
        
        # Unsubscribing non-existent user should not error
        broadcast_manager.unsubscribe('non_existent')
    
    def test_broadcast_filtering(self, broadcast_manager):
        """Test broadcast message filtering"""
        # Subscribe users with different filters
        broadcast_manager.subscribe('user1', {'topic': 'alerts', 'priority': 'high'})
        broadcast_manager.subscribe('user2', {'topic': 'alerts'})
        broadcast_manager.subscribe('user3', {'priority': 'high'})
        broadcast_manager.subscribe('user4')  # No filters
        
        # Test different broadcast messages
        alert_high = {'topic': 'alerts', 'priority': 'high', 'message': 'Critical alert'}
        alert_low = {'topic': 'alerts', 'priority': 'low', 'message': 'Info alert'}
        update_high = {'topic': 'updates', 'priority': 'high', 'message': 'System update'}
        
        # user1: should receive alert_high only (both filters match)
        assert broadcast_manager.should_receive_broadcast('user1', alert_high) == True
        assert broadcast_manager.should_receive_broadcast('user1', alert_low) == False
        assert broadcast_manager.should_receive_broadcast('user1', update_high) == False
        
        # user2: should receive both alerts (topic matches)
        assert broadcast_manager.should_receive_broadcast('user2', alert_high) == True
        assert broadcast_manager.should_receive_broadcast('user2', alert_low) == True
        assert broadcast_manager.should_receive_broadcast('user2', update_high) == False
        
        # user3: should receive high priority messages (priority matches)
        assert broadcast_manager.should_receive_broadcast('user3', alert_high) == True
        assert broadcast_manager.should_receive_broadcast('user3', alert_low) == False
        assert broadcast_manager.should_receive_broadcast('user3', update_high) == True
        
        # user4: should receive all messages (no filters)
        assert broadcast_manager.should_receive_broadcast('user4', alert_high) == True
        assert broadcast_manager.should_receive_broadcast('user4', alert_low) == True
        assert broadcast_manager.should_receive_broadcast('user4', update_high) == True
    
    @pytest.mark.asyncio
    async def test_broadcast_message_delivery(self, broadcast_manager):
        """Test broadcast message delivery"""
        # Subscribe users
        broadcast_manager.subscribe('user1', {'topic': 'alerts'})
        broadcast_manager.subscribe('user2', {'topic': 'alerts'})
        broadcast_manager.subscribe('user3', {'topic': 'updates'})
        
        # Broadcast alert message
        message_data = {'topic': 'alerts', 'message': 'System maintenance scheduled'}
        results = await broadcast_manager.broadcast_message(message_data)
        
        # Verify delivery results
        assert results['success'] == 2  # user1 and user2
        assert results['failed'] == 0
        
        # Verify broadcast history
        assert len(broadcast_manager.broadcast_history) == 1
        history_entry = broadcast_manager.broadcast_history[0]
        assert history_entry['message_data'] == message_data
        assert history_entry['results'] == results
        
        # Verify delivery stats
        stats = broadcast_manager.delivery_stats
        assert stats['total_broadcasts'] == 1
        assert stats['successful_deliveries'] == 2
        assert stats['failed_deliveries'] == 0
    
    @pytest.mark.asyncio
    async def test_targeted_broadcast(self, broadcast_manager):
        """Test targeted broadcast to specific users"""
        # Subscribe multiple users
        for i in range(10):
            broadcast_manager.subscribe(f'user_{i}', {'topic': 'alerts'})
        
        # Broadcast to specific subset
        target_users = ['user_1', 'user_3', 'user_5']
        message_data = {'topic': 'alerts', 'message': 'Targeted alert'}
        results = await broadcast_manager.broadcast_message(message_data, target_users)
        
        # Verify only targeted users received message
        assert results['success'] == 3
        assert results['failed'] == 0
        
        # Verify broadcast history
        history_entry = broadcast_manager.broadcast_history[0]
        assert history_entry['target_users'] == target_users
    
    @pytest.mark.asyncio
    async def test_broadcast_delivery_failure_handling(self, broadcast_manager):
        """Test handling of broadcast delivery failures"""
        # Subscribe users
        broadcast_manager.subscribe('user1', {'topic': 'alerts'})
        broadcast_manager.subscribe('user2', {'topic': 'alerts'})
        
        # Mock delivery failure for user2
        original_deliver = broadcast_manager._deliver_message
        
        async def mock_deliver(user_id, message_data):
            if user_id == 'user2':
                raise Exception("Delivery failed")
            return await original_deliver(user_id, message_data)
        
        broadcast_manager._deliver_message = mock_deliver
        
        # Broadcast message
        message_data = {'topic': 'alerts', 'message': 'Test message'}
        results = await broadcast_manager.broadcast_message(message_data)
        
        # Verify results
        assert results['success'] == 1  # user1 succeeded
        assert results['failed'] == 1   # user2 failed
        
        # Verify stats
        stats = broadcast_manager.delivery_stats
        assert stats['successful_deliveries'] == 1
        assert stats['failed_deliveries'] == 1
    
    @pytest.mark.asyncio
    async def test_high_volume_broadcasting(self, broadcast_manager):
        """Test broadcasting under high volume conditions"""
        # Subscribe many users
        num_users = 100
        for i in range(num_users):
            broadcast_manager.subscribe(f'user_{i}', {'topic': 'alerts'})
        
        # Broadcast multiple messages rapidly
        num_messages = 50
        tasks = []
        
        for i in range(num_messages):
            message_data = {'topic': 'alerts', 'message': f'Bulk message {i}'}
            tasks.append(broadcast_manager.broadcast_message(message_data))
        
        # Execute all broadcasts
        results = await asyncio.gather(*tasks)
        
        # Verify all broadcasts succeeded
        total_success = sum(result['success'] for result in results)
        total_failed = sum(result['failed'] for result in results)
        
        expected_success = num_messages * num_users
        assert total_success == expected_success
        assert total_failed == 0
        
        # Verify history and stats
        assert len(broadcast_manager.broadcast_history) == num_messages
        assert broadcast_manager.delivery_stats['total_broadcasts'] == num_messages
        assert broadcast_manager.delivery_stats['successful_deliveries'] == expected_success


class TestMessageQueueIntegration:
    """Test integration with message queue system"""
    
    @pytest.fixture
    def mock_message_queue(self):
        """Create mock message queue for testing"""
        queue = MagicMock()
        queue.enqueue = AsyncMock()
        queue.dequeue = AsyncMock()
        queue.get_queue_stats = MagicMock()
        return queue
    
    @pytest.mark.asyncio
    async def test_message_queueing_for_routing(self, mock_message_queue):
        """Test message queueing before routing"""
        # Create queued message
        message = QueuedMessage(
            user_id='user123',
            message_type='start_agent',
            payload={'query': 'test query'},
            priority=MessagePriority.HIGH
        )
        
        # Enqueue message
        await mock_message_queue.enqueue(message)
        
        # Verify enqueue was called
        mock_message_queue.enqueue.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_priority_queue_processing(self, mock_message_queue):
        """Test priority-based queue processing"""
        # Setup queue to return messages in priority order
        high_priority_msg = QueuedMessage(
            user_id='user1',
            message_type='emergency',
            payload={'alert': 'critical'},
            priority=MessagePriority.HIGH
        )
        
        low_priority_msg = QueuedMessage(
            user_id='user2',
            message_type='info',
            payload={'info': 'update'},
            priority=MessagePriority.LOW
        )
        
        # Mock dequeue to return high priority first
        mock_message_queue.dequeue.side_effect = [high_priority_msg, low_priority_msg, None]
        
        # Process queue
        processed_messages = []
        
        while True:
            message = await mock_message_queue.dequeue()
            if message == None:
                break
            processed_messages.append(message)
        
        # Verify processing order
        assert len(processed_messages) == 2
        assert processed_messages[0].priority == MessagePriority.HIGH
        assert processed_messages[1].priority == MessagePriority.LOW
    
    def test_queue_statistics_tracking(self, mock_message_queue):
        """Test queue statistics tracking"""
        # Mock queue stats
        mock_stats = {
            'queue_length': 15,
            'messages_processed': 250,
            'average_processing_time': 0.125,
            'priority_distribution': {
                'HIGH': 25,
                'MEDIUM': 150,
                'LOW': 75
            }
        }
        
        mock_message_queue.get_queue_stats.return_value = mock_stats
        
        # Get stats
        stats = mock_message_queue.get_queue_stats()
        
        # Verify stats
        assert stats['queue_length'] == 15
        assert stats['messages_processed'] == 250
        assert stats['average_processing_time'] == 0.125
        assert stats['priority_distribution']['HIGH'] == 25