"""
WebSocket Message Handler Routing Tests
Tests for WebSocket message handler registration, routing, and middleware processing.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from datetime import UTC, datetime
from typing import Any, Dict

import pytest

from app.core.exceptions_base import NetraException

# Add project root to path
from app.services.websocket.message_handler import MessageRouter
from .websocket_test_utilities import MockMessageHandler

# Add project root to path


class TestWebSocketMessageHandlerRouting:
    """Test WebSocket message handler routing."""
    
    @pytest.fixture
    def message_router(self):
        """Create message router for testing."""
        return MessageRouter()
    
    @pytest.fixture
    def sample_handlers(self):
        """Create sample message handlers."""
        return {
            'start_agent': MockMessageHandler('start_agent'),
            'user_message': MockMessageHandler('user_message'),
            'system_status': MockMessageHandler('system_status'),
            'heartbeat': MockMessageHandler('heartbeat')
        }
    
    def test_handler_registration(self, message_router, sample_handlers):
        """Test message handler registration."""
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
        """Test prevention of duplicate handler registration."""
        handler = sample_handlers['start_agent']
        
        # First registration should succeed
        message_router.register_handler(handler)
        
        # Second registration should fail
        with pytest.raises(NetraException) as exc_info:
            message_router.register_handler(handler)
        assert "already registered" in str(exc_info.value)
    
    def test_handler_unregistration(self, message_router, sample_handlers):
        """Test message handler unregistration."""
        # Register handler
        handler = sample_handlers['start_agent']
        message_router.register_handler(handler)
        assert 'start_agent' in message_router.handlers
        
        # Unregister handler
        message_router.unregister_handler('start_agent')
        assert 'start_agent' not in message_router.handlers
        
        # Unregistering non-existent handler should not error
        message_router.unregister_handler('non_existent')

    async def test_message_routing_success(self, message_router, sample_handlers):
        """Test successful message routing."""
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

    async def test_message_routing_no_handler(self, message_router):
        """Test message routing when no handler is registered."""
        # Route message to unregistered type
        with pytest.raises(NetraException) as exc_info:
            await message_router.route_message('user123', 'unknown_type', {})
        
        assert "No handler registered" in str(exc_info.value)
        assert message_router.routing_metrics['routing_errors'] == 1

    async def test_message_routing_handler_failure(self, message_router, sample_handlers):
        """Test message routing when handler fails."""
        # Register failing handler
        handler = sample_handlers['start_agent']
        handler.should_fail = True
        message_router.register_handler(handler)
        
        # Route message
        with pytest.raises(NetraException) as exc_info:
            await message_router.route_message('user123', 'start_agent', {})
        
        assert "Message routing failed" in str(exc_info.value)
        assert message_router.routing_metrics['routing_errors'] == 1

    async def test_concurrent_message_routing(self, message_router, sample_handlers):
        """Test concurrent message routing."""
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

    async def test_middleware_processing(self, message_router, sample_handlers):
        """Test middleware processing in routing pipeline."""
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

    async def test_routing_performance_metrics(self, message_router, sample_handlers):
        """Test routing performance metrics collection."""
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

    async def test_message_priority_handling(self, message_router):
        """Test message priority-based handling."""
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