"""Integration Tests for Example Message Flow

End-to-end integration tests covering the complete example message flow
from frontend to backend to WebSocket delivery.

Business Value: Validates complete user journey for AI optimization demonstrations
"""

import pytest
import asyncio
import json
import websockets
from unittest.mock import Mock, patch
from datetime import datetime

from app.main import app
from app.ws_manager import get_manager
from app.handlers import get_example_message_handler
from app.agents.example_message_processor import get_example_message_supervisor


@pytest.mark.asyncio
class TestExampleMessageIntegration:
    """End-to-end integration tests"""
    
    @pytest.fixture
    async def app_client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            yield client
            
    @pytest.fixture
    def sample_frontend_message(self):
        """Sample message as it would come from frontend"""
        return {
            "type": "chat_message",
            "payload": {
                "content": "I need to optimize costs while maintaining quality for my AI system",
                "example_message_id": "integration_test_001",
                "example_message_metadata": {
                    "title": "Cost Optimization Integration Test",
                    "category": "cost-optimization",
                    "complexity": "intermediate",
                    "businessValue": "conversion",
                    "estimatedTime": "60-90s"
                },
                "user_id": "integration_test_user",
                "timestamp": int(datetime.now().timestamp())
            }
        }
        
    async def test_complete_message_flow(self, sample_frontend_message):
        """Test complete message flow from frontend to response"""
        
        # Get handler and supervisor
        handler = get_example_message_handler()
        supervisor = get_example_message_supervisor()
        
        # Track WebSocket messages sent
        websocket_messages = []
        
        async def mock_send_message(user_id, message, retry=True):
            websocket_messages.append((user_id, message))
            return True
            
        # Mock WebSocket manager
        ws_manager = get_manager()
        original_send = ws_manager.send_message_to_user
        ws_manager.send_message_to_user = mock_send_message
        
        try:
            # Process the message
            response = await handler.handle_example_message(
                sample_frontend_message["payload"]
            )
            
            # Verify response
            assert response.status == 'completed'
            assert response.message_id == 'integration_test_001'
            assert response.processing_time_ms is not None
            assert response.result is not None
            
            # Verify WebSocket messages were sent
            assert len(websocket_messages) > 0
            
            # Should have sent progress updates and completion
            message_types = []
            for user_id, message in websocket_messages:
                assert user_id == 'integration_test_user'
                message_types.append(message.get('type'))
                
            # Should include agent updates
            assert 'agent_started' in message_types
            assert 'agent_completed' in message_types
            
        finally:
            # Restore original send method
            ws_manager.send_message_to_user = original_send
            
    async def test_websocket_error_handling(self, sample_frontend_message):
        """Test handling when WebSocket connections fail"""
        
        handler = get_example_message_handler()
        
        # Mock WebSocket to fail
        async def mock_failing_send(user_id, message, retry=True):
            raise ConnectionError("WebSocket connection lost")
            
        ws_manager = get_manager()
        original_send = ws_manager.send_message_to_user
        ws_manager.send_message_to_user = mock_failing_send
        
        try:
            # Should still complete processing despite WebSocket errors
            response = await handler.handle_example_message(
                sample_frontend_message["payload"]
            )
            
            # Processing should complete even with WebSocket errors
            assert response.status == 'completed'
            assert response.result is not None
            
        finally:
            ws_manager.send_message_to_user = original_send
            
    async def test_concurrent_user_messages(self):
        """Test handling messages from multiple users concurrently"""
        
        handler = get_example_message_handler()
        
        # Create messages for different users
        messages = []
        for i in range(3):
            messages.append({
                "content": f"Test message from user {i}",
                "example_message_id": f"concurrent_test_{i}",
                "example_message_metadata": {
                    "title": f"Test {i}",
                    "category": "cost-optimization",
                    "complexity": "basic",
                    "businessValue": "conversion", 
                    "estimatedTime": "30s"
                },
                "user_id": f"user_{i}",
                "timestamp": int(datetime.now().timestamp())
            })
            
        # Mock WebSocket manager
        websocket_messages = []
        
        async def mock_send_message(user_id, message, retry=True):
            websocket_messages.append((user_id, message))
            return True
            
        ws_manager = get_manager()
        original_send = ws_manager.send_message_to_user
        ws_manager.send_message_to_user = mock_send_message
        
        try:
            # Process all messages concurrently
            tasks = [handler.handle_example_message(msg) for msg in messages]
            responses = await asyncio.gather(*tasks)
            
            # All should complete successfully
            assert len(responses) == 3
            assert all(resp.status == 'completed' for resp in responses)
            
            # Each user should have received their messages
            users_with_messages = set()
            for user_id, message in websocket_messages:
                users_with_messages.add(user_id)
                
            assert len(users_with_messages) == 3
            assert all(f"user_{i}" in users_with_messages for i in range(3))
            
        finally:
            ws_manager.send_message_to_user = original_send
            
    async def test_message_ordering_per_user(self):
        """Test that messages for same user maintain order"""
        
        handler = get_example_message_handler()
        user_id = "ordering_test_user"
        
        # Track processing order
        processing_order = []
        
        original_process = handler.supervisor.process_example_message
        
        async def mock_process_with_tracking(user_id, content, metadata):
            processing_order.append(metadata['example_message_id'])
            # Add small delay to make ordering issues more likely if present
            await asyncio.sleep(0.01)
            return await original_process(user_id, content, metadata)
            
        handler.supervisor.process_example_message = mock_process_with_tracking
        
        # Mock WebSocket
        async def mock_send_message(user_id, message, retry=True):
            return True
            
        ws_manager = get_manager()
        original_send = ws_manager.send_message_to_user
        ws_manager.send_message_to_user = mock_send_message
        
        try:
            # Send multiple messages for same user in sequence
            message_ids = ['order_1', 'order_2', 'order_3']
            
            for msg_id in message_ids:
                message = {
                    "content": f"Message {msg_id}",
                    "example_message_id": msg_id,
                    "example_message_metadata": {
                        "title": f"Order Test {msg_id}",
                        "category": "cost-optimization",
                        "complexity": "basic",
                        "businessValue": "conversion",
                        "estimatedTime": "30s"
                    },
                    "user_id": user_id,
                    "timestamp": int(datetime.now().timestamp())
                }
                
                # Process sequentially (not concurrently) to test ordering
                await handler.handle_example_message(message)
                
            # Processing should maintain order
            assert processing_order == message_ids
            
        finally:
            # Restore original methods
            handler.supervisor.process_example_message = original_process
            ws_manager.send_message_to_user = original_send
            
    async def test_timeout_handling(self):
        """Test handling of processing timeouts"""
        
        handler = get_example_message_handler()
        
        # Mock supervisor to timeout
        async def mock_timeout_process(user_id, content, metadata):
            await asyncio.sleep(10)  # Long delay to simulate timeout
            return {'result': 'should_not_reach'}
            
        original_process = handler.supervisor.process_example_message
        handler.supervisor.process_example_message = mock_timeout_process
        
        websocket_messages = []
        
        async def mock_send_message(user_id, message, retry=True):
            websocket_messages.append((user_id, message))
            return True
            
        ws_manager = get_manager()
        original_send = ws_manager.send_message_to_user
        ws_manager.send_message_to_user = mock_send_message
        
        try:
            message = {
                "content": "This will timeout",
                "example_message_id": "timeout_test",
                "example_message_metadata": {
                    "title": "Timeout Test",
                    "category": "cost-optimization", 
                    "complexity": "basic",
                    "businessValue": "conversion",
                    "estimatedTime": "30s"
                },
                "user_id": "timeout_user",
                "timestamp": int(datetime.now().timestamp())
            }
            
            # This should timeout and be handled gracefully
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    handler.handle_example_message(message),
                    timeout=2.0  # 2 second timeout
                )
                
        finally:
            # Restore original methods
            handler.supervisor.process_example_message = original_process
            ws_manager.send_message_to_user = original_send
            
    async def test_error_recovery_integration(self):
        """Test error recovery in full integration"""
        
        handler = get_example_message_handler()
        
        # Mock supervisor to fail then succeed
        call_count = 0
        
        async def mock_failing_then_success(user_id, content, metadata):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt fails")
            return {
                'optimization_type': 'cost_optimization',
                'result': 'success_after_retry'
            }
            
        original_process = handler.supervisor.process_example_message
        handler.supervisor.process_example_message = mock_failing_then_success
        
        websocket_messages = []
        
        async def mock_send_message(user_id, message, retry=True):
            websocket_messages.append(message)
            return True
            
        ws_manager = get_manager()
        original_send = ws_manager.send_message_to_user
        ws_manager.send_message_to_user = mock_send_message
        
        try:
            message = {
                "content": "This will fail then succeed",
                "example_message_id": "recovery_test",
                "example_message_metadata": {
                    "title": "Recovery Test",
                    "category": "cost-optimization",
                    "complexity": "basic", 
                    "businessValue": "conversion",
                    "estimatedTime": "30s"
                },
                "user_id": "recovery_user",
                "timestamp": int(datetime.now().timestamp())
            }
            
            # Should handle error and potentially retry
            response = await handler.handle_example_message(message)
            
            # Should indicate error was handled
            assert response.status == 'error'  # First attempt fails
            
            # Check that error notification was sent via WebSocket
            error_messages = [msg for msg in websocket_messages if msg.get('type') == 'error']
            assert len(error_messages) > 0
            
        finally:
            # Restore original methods
            handler.supervisor.process_example_message = original_process
            ws_manager.send_message_to_user = original_send


@pytest.mark.asyncio 
class TestExampleMessageWebSocketIntegration:
    """WebSocket-specific integration tests"""
    
    async def test_websocket_message_flow(self):
        """Test WebSocket message flow end-to-end"""
        
        # This would require a running WebSocket server
        # For now, test the message formatting and routing
        
        from app.routes.example_messages import router
        
        # Test that the route exists
        websocket_routes = [route for route in router.routes if hasattr(route, 'path') and 'ws' in route.path]
        assert len(websocket_routes) > 0
        
    async def test_websocket_error_broadcasting(self):
        """Test that WebSocket errors are properly broadcast"""
        
        ws_manager = get_manager()
        
        # Test error notification
        test_user_id = "websocket_test_user"
        test_error = "Test error message"
        
        # Mock the actual WebSocket sending
        sent_messages = []
        
        async def mock_send(user_id, message, retry=True):
            sent_messages.append((user_id, message))
            return True
            
        original_send = ws_manager.send_message_to_user
        ws_manager.send_message_to_user = mock_send
        
        try:
            # Send error notification
            await ws_manager.send_error_to_user(test_user_id, test_error)
            
            # Should have sent error message
            assert len(sent_messages) == 1
            user_id, message = sent_messages[0]
            assert user_id == test_user_id
            assert message['type'] == 'error' 
            assert test_error in str(message)
            
        finally:
            ws_manager.send_message_to_user = original_send


@pytest.mark.asyncio
class TestExampleMessagePerformance:
    """Performance and load testing"""
    
    async def test_message_processing_performance(self):
        """Test performance of message processing"""
        
        handler = get_example_message_handler()
        
        # Mock WebSocket to avoid network overhead
        async def mock_send_message(user_id, message, retry=True):
            return True
            
        ws_manager = get_manager()
        original_send = ws_manager.send_message_to_user
        ws_manager.send_message_to_user = mock_send_message
        
        try:
            message = {
                "content": "Performance test message",
                "example_message_id": "perf_test",
                "example_message_metadata": {
                    "title": "Performance Test",
                    "category": "cost-optimization",
                    "complexity": "basic",
                    "businessValue": "conversion",
                    "estimatedTime": "30s"
                },
                "user_id": "perf_user",
                "timestamp": int(datetime.now().timestamp())
            }
            
            # Measure processing time
            start_time = datetime.now()
            response = await handler.handle_example_message(message)
            end_time = datetime.now()
            
            processing_duration = (end_time - start_time).total_seconds()
            
            # Should complete within reasonable time (5 seconds for demo)
            assert processing_duration < 5.0
            assert response.status == 'completed'
            assert response.processing_time_ms is not None
            
        finally:
            ws_manager.send_message_to_user = original_send
            
    async def test_concurrent_load(self):
        """Test handling concurrent load"""
        
        handler = get_example_message_handler()
        
        # Mock WebSocket
        message_count = 0
        
        async def mock_send_message(user_id, message, retry=True):
            nonlocal message_count
            message_count += 1
            return True
            
        ws_manager = get_manager()
        original_send = ws_manager.send_message_to_user
        ws_manager.send_message_to_user = mock_send_message
        
        try:
            # Create multiple messages
            messages = []
            for i in range(10):  # 10 concurrent messages
                messages.append({
                    "content": f"Load test message {i}",
                    "example_message_id": f"load_test_{i}",
                    "example_message_metadata": {
                        "title": f"Load Test {i}",
                        "category": "cost-optimization",
                        "complexity": "basic",
                        "businessValue": "conversion",
                        "estimatedTime": "30s"
                    },
                    "user_id": f"load_user_{i}",
                    "timestamp": int(datetime.now().timestamp())
                })
                
            # Process all concurrently
            start_time = datetime.now()
            tasks = [handler.handle_example_message(msg) for msg in messages]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = datetime.now()
            
            # All should complete or have graceful errors
            successful_responses = [r for r in responses if isinstance(r, type(responses[0])) and not isinstance(r, Exception)]
            assert len(successful_responses) >= 8  # At least 80% success rate
            
            # Total time should be reasonable for concurrent processing
            total_time = (end_time - start_time).total_seconds()
            assert total_time < 10.0  # Should not take longer than 10 seconds
            
        finally:
            ws_manager.send_message_to_user = original_send


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])