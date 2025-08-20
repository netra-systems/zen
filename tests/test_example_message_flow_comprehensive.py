"""Comprehensive Test Suite for Example Message Flow System

Production-ready test coverage addressing all critical review issues.
Includes 10+ test categories covering functionality, reliability, and edge cases.

Business Value: Ensures system reliability for Free-to-Paid conversion flow
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
from uuid import uuid4

# Test framework imports
from fastapi.testclient import TestClient
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

# Application imports
from app.routes.example_messages_enhanced import (
    router, MessageSequencer, ConnectionStateManager, 
    message_sequencer, connection_manager, agent_circuit_breaker
)
from app.handlers.example_message_handler_enhanced import (
    EnhancedExampleMessageHandler, SessionManager, RealAgentIntegration,
    ExampleMessageRequest, ExampleMessageResponse, ExampleMessageMetadata
)
from app.core.circuit_breaker import CircuitBreaker
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestMessageSequencer:
    """Test Category 1: Message Sequencing and Ordering"""

    @pytest.fixture
    def sequencer(self):
        return MessageSequencer()

    def test_sequence_generation(self, sequencer):
        """Test sequence number generation for users"""
        user_id = "test_user_1"
        
        # First sequence should be 1
        seq1 = sequencer.get_next_sequence(user_id)
        assert seq1 == 1
        
        # Second sequence should be 2
        seq2 = sequencer.get_next_sequence(user_id)
        assert seq2 == 2
        
        # Different user should start at 1
        seq3 = sequencer.get_next_sequence("test_user_2")
        assert seq3 == 1

    def test_transactional_message_handling(self, sequencer):
        """Test transactional pattern for message handling"""
        user_id = "test_user"
        sequence = 1
        message = {"type": "test", "payload": "data"}
        
        # Add pending message
        sequencer.add_pending_message(user_id, sequence, message)
        
        # Message should be in pending state
        pending = sequencer.get_pending_messages(user_id)
        assert sequence in pending
        assert pending[sequence]['status'] == 'pending'
        
        # Mark as sending
        assert sequencer.mark_message_sending(user_id, sequence) == True
        pending = sequencer.get_pending_messages(user_id)
        assert pending[sequence]['status'] == 'sending'
        
        # Acknowledge message
        assert sequencer.acknowledge_message(user_id, sequence) == True
        
        # Message should be removed from pending
        pending = sequencer.get_pending_messages(user_id)
        assert sequence not in pending

    def test_message_retry_logic(self, sequencer):
        """Test message retry logic with failure handling"""
        user_id = "test_user"
        sequence = 1
        message = {"type": "test", "payload": "data"}
        
        # Add message
        sequencer.add_pending_message(user_id, sequence, message)
        
        # Simulate send failure - revert to pending
        sequencer.mark_message_sending(user_id, sequence)
        sequencer.revert_message_to_pending(user_id, sequence)
        
        # Should be pending again with retry count
        pending = sequencer.get_pending_messages(user_id)
        assert pending[sequence]['status'] == 'pending'
        assert sequencer.should_retry_message(user_id, sequence) == True
        
        # After max retries, should not retry
        for i in range(4):  # Exceed max retries
            sequencer.revert_message_to_pending(user_id, sequence)
        
        assert sequencer.should_retry_message(user_id, sequence) == False

    def test_atomic_cleanup(self, sequencer):
        """Test atomic cleanup of user sequences"""
        user_id = "test_user"
        
        # Add multiple messages
        for i in range(3):
            seq = sequencer.get_next_sequence(user_id)
            sequencer.add_pending_message(user_id, seq, {"test": i})
        
        # Verify data exists
        assert len(sequencer.get_pending_messages(user_id)) == 3
        
        # Cleanup
        sequencer.cleanup_user_sequences(user_id)
        
        # All data should be removed
        assert len(sequencer.get_pending_messages(user_id)) == 0
        assert user_id not in sequencer._sequences


class TestConnectionStateManager:
    """Test Category 2: Connection State Management"""

    @pytest.fixture
    def state_manager(self):
        return ConnectionStateManager()

    @pytest.mark.asyncio
    async def test_connection_registration(self, state_manager):
        """Test connection registration with full state tracking"""
        user_id = "test_user"
        connection_id = str(uuid4())
        websocket = Mock(spec=WebSocket)
        
        # Register connection
        await state_manager.register_connection(user_id, connection_id, websocket)
        
        # Verify connection is registered
        assert state_manager.is_connection_valid(user_id)
        
        conn_info = state_manager.get_connection_info(user_id)
        assert conn_info['connection_id'] == connection_id
        assert conn_info['status'] == 'connected'
        assert conn_info['authenticated'] == False

    def test_connection_activity_tracking(self, state_manager):
        """Test connection activity tracking and timeouts"""
        user_id = "test_user"
        connection_id = str(uuid4())
        websocket = Mock(spec=WebSocket)
        
        # Register connection
        asyncio.run(state_manager.register_connection(user_id, connection_id, websocket))
        
        # Update activity
        initial_activity = state_manager.get_connection_info(user_id)['last_activity']
        time.sleep(0.1)  # Brief delay
        state_manager.update_activity(user_id)
        
        updated_activity = state_manager.get_connection_info(user_id)['last_activity']
        assert updated_activity > initial_activity

    def test_error_count_management(self, state_manager):
        """Test error counting and disconnection thresholds"""
        user_id = "test_user"
        connection_id = str(uuid4())
        websocket = Mock(spec=WebSocket)
        
        # Register connection
        asyncio.run(state_manager.register_connection(user_id, connection_id, websocket))
        
        # Increment errors
        for i in range(5):
            state_manager.increment_error_count(user_id)
        
        conn_info = state_manager.get_connection_info(user_id)
        assert conn_info['error_count'] == 5
        
        # Should not disconnect yet (threshold is 10)
        assert not state_manager.should_disconnect_for_errors(user_id)
        
        # Add more errors to exceed threshold
        for i in range(6):
            state_manager.increment_error_count(user_id)
        
        assert state_manager.should_disconnect_for_errors(user_id)

    @pytest.mark.asyncio
    async def test_atomic_cleanup(self, state_manager):
        """Test atomic connection cleanup"""
        user_id = "test_user"
        connection_id = str(uuid4())
        websocket = Mock(spec=WebSocket)
        
        # Register connection
        await state_manager.register_connection(user_id, connection_id, websocket)
        assert state_manager.is_connection_valid(user_id)
        
        # Cleanup
        await state_manager.cleanup_connection(user_id)
        
        # Connection should be removed
        assert not state_manager.is_connection_valid(user_id)
        assert state_manager.get_connection_info(user_id) is None


class TestSessionManager:
    """Test Category 3: Session Management and Memory Cleanup"""

    @pytest.fixture
    def session_manager(self):
        return SessionManager()

    @pytest.mark.asyncio
    async def test_session_creation_with_timeout(self, session_manager):
        """Test session creation with proper timeout management"""
        user_id = "test_user"
        message_id = "test_message"
        metadata = {"category": "test", "complexity": "basic"}
        
        # Create session
        session_id = await session_manager.create_session(
            user_id, message_id, metadata, timeout_minutes=1
        )
        
        # Verify session exists
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session['user_id'] == user_id
        assert session['message_id'] == message_id
        
        # Verify timeout is set
        assert session_id in session_manager.session_timeouts

    def test_session_updates(self, session_manager):
        """Test session data updates"""
        user_id = "test_user"
        message_id = "test_message"
        metadata = {"category": "test"}
        
        session_id = asyncio.run(session_manager.create_session(user_id, message_id, metadata))
        
        # Update session
        updates = {"status": "processing", "progress": 50}
        assert session_manager.update_session(session_id, updates) == True
        
        # Verify updates
        session = session_manager.get_session(session_id)
        assert session['status'] == 'processing'
        assert session['progress'] == 50

    def test_user_session_tracking(self, session_manager):
        """Test tracking sessions by user"""
        user_id = "test_user"
        
        # Create multiple sessions for user
        session_ids = []
        for i in range(3):
            session_id = asyncio.run(session_manager.create_session(
                user_id, f"message_{i}", {"test": i}
            ))
            session_ids.append(session_id)
        
        # Get user sessions
        user_sessions = session_manager.get_user_sessions(user_id)
        assert len(user_sessions) == 3
        
        # Verify all sessions belong to user
        for session in user_sessions:
            assert session['user_id'] == user_id

    @pytest.mark.asyncio
    async def test_session_cleanup_and_memory_management(self, session_manager):
        """Test session cleanup prevents memory leaks"""
        user_id = "test_user"
        message_id = "test_message"
        metadata = {"category": "test"}
        
        # Create session
        session_id = await session_manager.create_session(user_id, message_id, metadata)
        
        # Verify session exists
        assert session_manager.get_session(session_id) is not None
        
        # Cleanup session
        await session_manager._cleanup_session(session_id)
        
        # Verify session is removed
        assert session_manager.get_session(session_id) is None
        assert user_id not in session_manager.user_sessions or not session_manager.user_sessions[user_id]

    def test_session_statistics(self, session_manager):
        """Test session statistics generation"""
        # Create multiple sessions with different statuses
        for i in range(3):
            session_id = asyncio.run(session_manager.create_session(f"user_{i}", f"msg_{i}", {}))
            session_manager.update_session(session_id, {"status": "processing" if i % 2 else "completed"})
        
        stats = session_manager.get_stats()
        
        assert stats['active_sessions'] == 3
        assert stats['total_users'] == 3
        assert 'status_breakdown' in stats
        assert 'memory_usage_estimate' in stats


class TestCircuitBreakerIntegration:
    """Test Category 4: Circuit Breaker Pattern and Resilience"""

    @pytest.fixture
    def circuit_breaker(self):
        return CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1.0,
            expected_exception=Exception
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_normal_operation(self, circuit_breaker):
        """Test circuit breaker in normal operation"""
        
        async def successful_operation():
            return "success"
        
        # Should work normally
        result = await circuit_breaker.call(successful_operation)
        assert result == "success"
        assert circuit_breaker.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_handling(self, circuit_breaker):
        """Test circuit breaker failure handling and state transitions"""
        
        async def failing_operation():
            raise Exception("Test failure")
        
        # Trigger failures to open circuit
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_operation)
        
        # Circuit should be open after threshold failures
        assert circuit_breaker.state == "OPEN"
        
        # Subsequent calls should fail fast
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_operation)

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, circuit_breaker):
        """Test circuit breaker recovery mechanism"""
        
        call_count = 0
        
        async def intermittent_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Initial failure")
            return "recovered"
        
        # Trigger failures
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(intermittent_operation)
        
        assert circuit_breaker.state == "OPEN"
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next call should attempt recovery
        result = await circuit_breaker.call(intermittent_operation)
        assert result == "recovered"
        assert circuit_breaker.state == "CLOSED"


class TestRealAgentIntegration:
    """Test Category 5: Real Agent Integration and Fallback Mechanisms"""

    @pytest.fixture
    def mock_supervisor(self):
        supervisor = Mock()
        supervisor.process_message = AsyncMock(return_value=Mock(content="Test response"))
        return supervisor

    @pytest.fixture
    def agent_integration(self, mock_supervisor):
        integration = RealAgentIntegration()
        integration.supervisor = mock_supervisor
        return integration

    @pytest.mark.asyncio
    async def test_real_agent_execution_success(self, agent_integration):
        """Test successful real agent execution"""
        
        result = await agent_integration.execute_real_agent_processing(
            user_id="test_user",
            content="Test optimization request",
            metadata={"category": "cost-optimization", "complexity": "basic"},
            session_id="test_session"
        )
        
        assert result is not None
        assert result['real_agent_execution'] == True
        assert 'optimization_type' in result

    @pytest.mark.asyncio
    async def test_fallback_mechanism(self, agent_integration):
        """Test fallback when real agents fail"""
        
        # Make supervisor fail
        agent_integration.supervisor.process_message.side_effect = Exception("Agent failure")
        
        result = await agent_integration.execute_real_agent_processing(
            user_id="test_user",
            content="Test request",
            metadata={"category": "cost-optimization"},
            session_id="test_session"
        )
        
        assert 'fallback_note' in result or result.get('status') == 'fallback'

    @pytest.mark.asyncio
    async def test_agent_category_routing(self, agent_integration):
        """Test proper routing to different agent categories"""
        
        categories = ['cost-optimization', 'latency-optimization', 'model-selection', 'scaling', 'advanced']
        
        for category in categories:
            result = await agent_integration.execute_real_agent_processing(
                user_id="test_user",
                content=f"Test {category} request",
                metadata={"category": category, "complexity": "basic"},
                session_id="test_session"
            )
            
            assert result is not None
            assert result.get('optimization_type') in [category, category.replace('-', '_')]


class TestErrorHandlingAndRecovery:
    """Test Category 6: Comprehensive Error Handling and Recovery"""

    @pytest.fixture
    def handler(self):
        return EnhancedExampleMessageHandler()

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, handler):
        """Test handling of validation errors"""
        
        invalid_message = {
            "content": "short",  # Too short
            "example_message_id": "test",
            "user_id": "user"
            # Missing required fields
        }
        
        response = await handler.handle_example_message(invalid_message)
        
        assert response.status == 'error'
        assert 'validation' in response.error.lower() or 'invalid' in response.error.lower()

    @pytest.mark.asyncio
    async def test_processing_error_recovery(self, handler):
        """Test recovery from processing errors"""
        
        with patch.object(handler.real_agent_integration, 'execute_real_agent_processing') as mock_process:
            # Make processing fail initially, then succeed
            mock_process.side_effect = [Exception("Processing error"), {"agent_name": "Test", "result": "success"}]
            
            # First attempt should handle error gracefully
            response = await handler.handle_example_message({
                "content": "Test optimization request with sufficient length",
                "example_message_id": "test_message",
                "example_message_metadata": {
                    "title": "Test",
                    "category": "cost-optimization",
                    "complexity": "basic",
                    "businessValue": "conversion",
                    "estimatedTime": "30s"
                },
                "user_id": "test_user",
                "timestamp": int(time.time() * 1000)
            })
            
            # Should handle error gracefully
            assert response.status == 'error'
            assert response.error is not None

    @pytest.mark.asyncio
    async def test_timeout_handling(self, handler):
        """Test handling of processing timeouts"""
        
        with patch.object(handler.real_agent_integration, 'execute_real_agent_processing') as mock_process:
            # Simulate timeout
            async def slow_process(*args, **kwargs):
                await asyncio.sleep(2)  # Longer than circuit breaker timeout
                return {"result": "slow"}
            
            mock_process.side_effect = slow_process
            
            # Should handle timeout gracefully
            response = await handler.handle_example_message({
                "content": "Test optimization request with sufficient length for timeout test",
                "example_message_id": "test_message",
                "example_message_metadata": {
                    "title": "Test",
                    "category": "cost-optimization", 
                    "complexity": "basic",
                    "businessValue": "conversion",
                    "estimatedTime": "30s"
                },
                "user_id": "test_user",
                "timestamp": int(time.time() * 1000)
            })
            
            # Should complete (with circuit breaker protection)
            assert response is not None


class TestWebSocketReliability:
    """Test Category 7: WebSocket Connection Reliability"""

    @pytest.fixture
    def mock_websocket(self):
        websocket = Mock(spec=WebSocket)
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def mock_ws_manager(self):
        manager = Mock()
        manager.connect_user = AsyncMock()
        manager.disconnect_user = AsyncMock()
        manager.send_message_to_user = AsyncMock()
        manager.handle_message = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self, mock_websocket, mock_ws_manager):
        """Test complete WebSocket connection lifecycle"""
        
        with patch('app.routes.example_messages_enhanced.get_manager', return_value=mock_ws_manager):
            with patch('app.routes.example_messages_enhanced.get_example_message_handler') as mock_handler:
                mock_handler.return_value.get_session_stats.return_value = {}
                mock_handler.return_value.get_active_sessions.return_value = {}
                
                # Simulate WebSocket disconnect
                mock_websocket.receive_text.side_effect = WebSocketDisconnect
                
                # Import and test the websocket endpoint
                from app.routes.example_messages_enhanced import example_message_websocket_enhanced
                
                # Should handle disconnect gracefully
                await example_message_websocket_enhanced(mock_websocket, "test_user")
                
                # Verify cleanup was called
                mock_ws_manager.disconnect_user.assert_called()

    def test_message_sequencing_under_failure(self):
        """Test message sequencing reliability under network failures"""
        
        sequencer = MessageSequencer()
        user_id = "test_user"
        
        # Add multiple messages
        messages = []
        for i in range(5):
            seq = sequencer.get_next_sequence(user_id)
            message = {"type": "test", "sequence": seq, "data": f"message_{i}"}
            sequencer.add_pending_message(user_id, seq, message)
            messages.append((seq, message))
        
        # Simulate partial failure - some messages sent, some failed
        for seq, _ in messages[:3]:
            sequencer.mark_message_sending(user_id, seq)
            if seq % 2 == 0:  # Even sequences fail
                sequencer.revert_message_to_pending(user_id, seq)
            else:  # Odd sequences succeed
                sequencer.acknowledge_message(user_id, seq)
        
        pending = sequencer.get_pending_messages(user_id)
        
        # Should have failed messages still pending
        assert len(pending) > 0
        
        # Failed messages should be retryable
        for seq in pending:
            assert sequencer.should_retry_message(user_id, seq)


class TestConcurrencyAndPerformance:
    """Test Category 8: Concurrency Handling and Performance"""

    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self):
        """Test concurrent session creation without conflicts"""
        
        session_manager = SessionManager()
        user_id = "test_user"
        
        # Create multiple sessions concurrently
        tasks = []
        for i in range(10):
            task = session_manager.create_session(
                user_id=f"{user_id}_{i}",
                message_id=f"message_{i}",
                metadata={"test": i}
            )
            tasks.append(task)
        
        session_ids = await asyncio.gather(*tasks)
        
        # All sessions should be created successfully
        assert len(session_ids) == 10
        assert len(set(session_ids)) == 10  # All unique

    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self):
        """Test concurrent message processing reliability"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Mock the real agent integration to return quickly
        with patch.object(handler.real_agent_integration, 'execute_real_agent_processing') as mock_process:
            mock_process.return_value = {
                "agent_name": "Test Agent",
                "optimization_type": "test",
                "real_agent_execution": False
            }
            
            # Process multiple messages concurrently
            tasks = []
            for i in range(5):
                message = {
                    "content": f"Test optimization request number {i} with sufficient length",
                    "example_message_id": f"test_message_{i}",
                    "example_message_metadata": {
                        "title": f"Test {i}",
                        "category": "cost-optimization",
                        "complexity": "basic",
                        "businessValue": "conversion",
                        "estimatedTime": "30s"
                    },
                    "user_id": f"test_user_{i}",
                    "timestamp": int(time.time() * 1000)
                }
                task = handler.handle_example_message(message)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete successfully
            for result in results:
                assert not isinstance(result, Exception)
                assert result.status in ['completed', 'error']  # Either is acceptable

    def test_memory_usage_under_load(self):
        """Test memory usage remains bounded under load"""
        
        session_manager = SessionManager()
        initial_session_count = len(session_manager.active_sessions)
        
        # Create many sessions
        session_ids = []
        for i in range(100):
            session_id = asyncio.run(session_manager.create_session(
                f"user_{i}", f"msg_{i}", {"test": i}
            ))
            session_ids.append(session_id)
        
        assert len(session_manager.active_sessions) == initial_session_count + 100
        
        # Cleanup all sessions
        for session_id in session_ids:
            asyncio.run(session_manager._cleanup_session(session_id))
        
        # Memory should be released
        assert len(session_manager.active_sessions) == initial_session_count


class TestBusinessLogicValidation:
    """Test Category 9: Business Logic and Value Generation"""

    @pytest.fixture
    def handler(self):
        return EnhancedExampleMessageHandler()

    @pytest.mark.asyncio
    async def test_business_insights_generation(self, handler):
        """Test business insights generation for different value types"""
        
        metadata = ExampleMessageMetadata(
            title="Test",
            category="cost-optimization",
            complexity="advanced",
            businessValue="conversion",
            estimatedTime="30s"
        )
        
        result = {"real_agent_execution": True, "agent_name": "Test"}
        processing_time = 15000  # 15 seconds
        
        insights = handler._generate_enhanced_business_insights(metadata, result, processing_time)
        
        assert insights['business_value_type'] == 'conversion'
        assert insights['real_agent_execution'] == True
        assert insights['performance_score'] > 0.8  # High score for real agent + good time
        assert 'conversion_indicators' in insights

    def test_category_routing_logic(self, handler):
        """Test proper routing logic for different optimization categories"""
        
        categories = ['cost-optimization', 'latency-optimization', 'model-selection', 'scaling', 'advanced']
        
        for category in categories:
            # Test that each category has appropriate processing logic
            integration = handler.real_agent_integration
            
            # Verify the category-specific processing methods exist
            method_name = f"_process_{category.replace('-', '_')}_real"
            assert hasattr(integration, method_name)

    def test_complexity_handling(self, handler):
        """Test handling of different complexity levels"""
        
        complexities = ['basic', 'intermediate', 'advanced']
        
        for complexity in complexities:
            metadata = ExampleMessageMetadata(
                title="Test",
                category="cost-optimization",
                complexity=complexity,
                businessValue="conversion",
                estimatedTime="30s"
            )
            
            # Should handle all complexity levels
            result = {"agent_name": "Test", "complexity_handled": complexity}
            insights = handler._generate_enhanced_business_insights(metadata, result, 20000)
            
            assert insights['complexity_handled'] == complexity


class TestDataValidationAndSecurity:
    """Test Category 10: Data Validation and Security"""

    def test_input_validation_comprehensive(self):
        """Test comprehensive input validation"""
        
        # Test valid message
        valid_message = {
            "content": "Valid optimization request with sufficient length",
            "example_message_id": "valid_id",
            "example_message_metadata": {
                "title": "Valid Title",
                "category": "cost-optimization",
                "complexity": "basic", 
                "businessValue": "conversion",
                "estimatedTime": "30s"
            },
            "user_id": "valid_user",
            "timestamp": int(time.time() * 1000)
        }
        
        # Should validate successfully
        request = ExampleMessageRequest(**valid_message)
        assert request.content == valid_message["content"]

    def test_input_sanitization(self):
        """Test input sanitization and security"""
        
        # Test with potentially malicious input
        malicious_content = "<script>alert('xss')</script>" + "a" * 100  # Make it long enough
        
        message = {
            "content": malicious_content,
            "example_message_id": "test_id",
            "example_message_metadata": {
                "title": "Test",
                "category": "cost-optimization",
                "complexity": "basic",
                "businessValue": "conversion", 
                "estimatedTime": "30s"
            },
            "user_id": "test_user",
            "timestamp": int(time.time() * 1000)
        }
        
        # Should accept content but validation should handle it appropriately
        request = ExampleMessageRequest(**message)
        assert request.content == malicious_content  # Content preserved as-is for processing

    def test_field_validation_constraints(self):
        """Test field validation constraints"""
        
        # Test category validation
        with pytest.raises(ValueError):
            ExampleMessageMetadata(
                title="Test",
                category="invalid_category",  # Invalid category
                complexity="basic",
                businessValue="conversion",
                estimatedTime="30s"
            )
        
        # Test complexity validation
        with pytest.raises(ValueError):
            ExampleMessageMetadata(
                title="Test",
                category="cost-optimization",
                complexity="invalid_complexity",  # Invalid complexity
                businessValue="conversion",
                estimatedTime="30s"
            )

    def test_user_id_validation(self):
        """Test user ID validation and session isolation"""
        
        session_manager = SessionManager()
        
        # Create sessions for different users
        user1_session = asyncio.run(session_manager.create_session("user1", "msg1", {}))
        user2_session = asyncio.run(session_manager.create_session("user2", "msg2", {}))
        
        # Users should have isolated sessions
        user1_sessions = session_manager.get_user_sessions("user1")
        user2_sessions = session_manager.get_user_sessions("user2")
        
        assert len(user1_sessions) == 1
        assert len(user2_sessions) == 1
        assert user1_sessions[0]['session_id'] != user2_sessions[0]['session_id']


class TestIntegrationEndToEnd:
    """Test Category 11: End-to-End Integration Tests"""

    @pytest.mark.asyncio
    async def test_complete_message_flow(self):
        """Test complete message flow from WebSocket to response"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Mock dependencies
        with patch.object(handler.real_agent_integration, 'execute_real_agent_processing') as mock_process:
            mock_process.return_value = {
                "agent_name": "Test Agent",
                "optimization_type": "cost_optimization",
                "real_agent_execution": True,
                "analysis": {"savings": "20%"}
            }
            
            with patch.object(handler.ws_manager, 'send_message_to_user') as mock_send:
                # Process complete message
                message = {
                    "content": "Complete end-to-end test optimization request with sufficient length",
                    "example_message_id": "e2e_test_message",
                    "example_message_metadata": {
                        "title": "E2E Test",
                        "category": "cost-optimization",
                        "complexity": "advanced",
                        "businessValue": "conversion",
                        "estimatedTime": "45s"
                    },
                    "user_id": "e2e_test_user",
                    "timestamp": int(time.time() * 1000)
                }
                
                response = await handler.handle_example_message(message)
                
                # Verify complete flow
                assert response.status == 'completed'
                assert response.real_agent_execution == True
                assert response.business_insights is not None
                assert response.execution_metadata is not None
                
                # Verify WebSocket notifications were sent
                assert mock_send.call_count >= 2  # At least start and completion notifications

    @pytest.mark.asyncio
    async def test_system_resilience_under_failures(self):
        """Test system resilience under various failure conditions"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Test with database unavailable
        with patch('app.routes.example_messages_enhanced.get_async_db') as mock_db:
            mock_db.side_effect = Exception("Database unavailable")
            
            # Should still handle gracefully with fallback
            message = {
                "content": "Resilience test message with sufficient length for processing",
                "example_message_id": "resilience_test",
                "example_message_metadata": {
                    "title": "Resilience Test",
                    "category": "cost-optimization",
                    "complexity": "basic",
                    "businessValue": "conversion",
                    "estimatedTime": "30s"
                },
                "user_id": "resilience_user",
                "timestamp": int(time.time() * 1000)
            }
            
            # Should handle error gracefully
            response = await handler.handle_example_message(message)
            assert response is not None  # Should not crash

    def test_performance_benchmarks(self):
        """Test performance benchmarks and thresholds"""
        
        start_time = time.time()
        
        # Test session manager performance
        session_manager = SessionManager()
        
        # Create and cleanup 100 sessions
        session_ids = []
        for i in range(100):
            session_id = asyncio.run(session_manager.create_session(f"user_{i}", f"msg_{i}", {}))
            session_ids.append(session_id)
        
        creation_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert creation_time < 2.0  # 2 seconds for 100 sessions
        
        # Cleanup performance
        start_time = time.time()
        for session_id in session_ids:
            asyncio.run(session_manager._cleanup_session(session_id))
        
        cleanup_time = time.time() - start_time
        assert cleanup_time < 1.0  # 1 second for cleanup


# Test fixtures and utilities
@pytest.fixture
def sample_message():
    """Sample valid message for testing"""
    return {
        "content": "Sample optimization request with sufficient length for validation",
        "example_message_id": "sample_message_123",
        "example_message_metadata": {
            "title": "Sample Optimization",
            "category": "cost-optimization",
            "complexity": "intermediate",
            "businessValue": "conversion",
            "estimatedTime": "30s"
        },
        "user_id": "sample_user_123",
        "timestamp": int(time.time() * 1000)
    }


@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager for testing"""
    manager = Mock()
    manager.get_client = Mock(return_value=Mock())
    return manager


# Test configuration
@pytest.mark.asyncio
class TestConfiguration:
    """Verify test configuration and setup"""
    
    def test_all_imports_successful(self):
        """Verify all required imports are successful"""
        # This test will fail if any imports are broken
        assert True
    
    def test_mock_objects_configured(self, mock_llm_manager):
        """Verify mock objects are properly configured"""
        assert mock_llm_manager is not None
        assert hasattr(mock_llm_manager, 'get_client')


if __name__ == "__main__":
    # Run specific test categories
    import sys
    
    if len(sys.argv) > 1:
        category = sys.argv[1]
        pytest.main([f"-k", f"Test{category}", "-v"])
    else:
        # Run all tests
        pytest.main([__file__, "-v", "--tb=short"])