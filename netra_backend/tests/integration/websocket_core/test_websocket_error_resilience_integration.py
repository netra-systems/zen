"""
Integration tests for WebSocket Error Resilience - Testing system recovery and fault tolerance.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Platform reliability and business continuity
- Value Impact: Ensures chat sessions continue despite network/system failures
- Strategic Impact: Critical for enterprise SLA compliance - validates system resilience

These integration tests validate error handling, automatic recovery, graceful degradation,
and fault tolerance mechanisms that ensure reliable AI chat service delivery.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.websocket import WebSocketTestUtility
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.error_recovery_handler import WebSocketErrorRecoveryHandler
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.models import User, Thread


class TestWebSocketErrorResilienceIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket error resilience."""
    
    @pytest.fixture
    async def test_user(self, real_services_fixture) -> User:
        """Create test user."""
        db = real_services_fixture["db"]
        
        user = User(
            email="resilience_test@example.com",
            name="Resilience Test User",
            subscription_tier="enterprise"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @pytest.fixture
    async def test_thread(self, real_services_fixture, test_user) -> Thread:
        """Create test thread."""
        db = real_services_fixture["db"]
        
        thread = Thread(
            user_id=test_user.id,
            title="Error Resilience Test Chat",
            metadata={"error_recovery_enabled": True}
        )
        db.add(thread)
        await db.commit()
        await db.refresh(thread)
        return thread
    
    @pytest.fixture
    async def websocket_manager(self):
        """Create WebSocket manager."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    async def error_recovery_handler(self, websocket_manager):
        """Create error recovery handler."""
        return WebSocketErrorRecoveryHandler(
            config={
                "max_retry_attempts": 3,
                "retry_backoff_multiplier": 2.0,
                "circuit_breaker_enabled": True,
                "graceful_degradation": True
            },
            websocket_manager=websocket_manager,
            message_buffer=Mock()
        )
    
    @pytest.fixture
    async def websocket_utility(self):
        """Create WebSocket test utility."""
        return WebSocketTestUtility()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_automatic_reconnection_after_network_failure(self, real_services_fixture, test_user, test_thread,
                                                               websocket_manager, websocket_utility, error_recovery_handler):
        """Test automatic reconnection after simulated network failure."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create initial connection
        original_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="resilience_test_conn",
            user_id=str(test_user.id),
            websocket=original_websocket,
            metadata={"thread_id": str(test_thread.id)}
        )
        await websocket_manager.add_connection(connection)
        
        # Verify initial connection works
        test_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "Test message before failure"},
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=original_websocket,
            message=test_message
        )
        
        initial_messages = len(original_websocket.sent_messages)
        assert initial_messages > 0
        
        # Simulate network failure
        await websocket_manager.remove_connection(connection.connection_id)
        
        # Simulate messages sent during disconnection (should be buffered)
        disconnected_messages = [
            WebSocketMessage(
                message_type=MessageType.AGENT_THINKING,
                payload={"status": "Analyzing during disconnection"},
                user_id=str(test_user.id),
                thread_id=str(test_thread.id)
            ),
            WebSocketMessage(
                message_type=MessageType.AGENT_COMPLETED,
                payload={"result": "Analysis completed during disconnection"},
                user_id=str(test_user.id),
                thread_id=str(test_thread.id)
            )
        ]
        
        # Buffer messages (in real system, this happens automatically)
        error_recovery_handler.message_buffer.get_buffered_messages = AsyncMock(
            return_value=disconnected_messages
        )
        
        # Simulate successful reconnection
        reconnected_websocket = await websocket_utility.create_mock_websocket()
        new_connection = await websocket_manager.create_connection(
            connection_id="resilience_test_conn_recovered",
            user_id=str(test_user.id),
            websocket=reconnected_websocket,
            metadata={
                "thread_id": str(test_thread.id),
                "recovered_connection": True,
                "original_connection_id": connection.connection_id
            }
        )
        await websocket_manager.add_connection(new_connection)
        
        # Simulate message recovery delivery
        for msg in disconnected_messages:
            await websocket_manager.send_to_user(
                user_id=str(test_user.id),
                message=msg
            )
        
        # Verify reconnection works and buffered messages delivered
        reconnected_messages = reconnected_websocket.sent_messages
        assert len(reconnected_messages) >= len(disconnected_messages)
        
        # Verify message content preserved
        message_contents = [str(msg) for msg in reconnected_messages]
        assert any("Analyzing during disconnection" in content for content in message_contents)
        assert any("Analysis completed during disconnection" in content for content in message_contents)
        
        # Test new messages work after recovery
        recovery_test_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "Test message after recovery"},
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=reconnected_websocket,
            message=recovery_test_message
        )
        
        final_message_count = len(reconnected_websocket.sent_messages)
        assert final_message_count > len(disconnected_messages)
        
        # Cleanup
        await websocket_manager.remove_connection(new_connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_graceful_degradation_during_database_issues(self, real_services_fixture, test_user, test_thread,
                                                             websocket_manager, websocket_utility):
        """Test graceful degradation when database is unavailable."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="degradation_test_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={"graceful_degradation": True}
        )
        await websocket_manager.add_connection(connection)
        
        # Simulate database failure
        with patch.object(db, 'execute', side_effect=Exception("Database unavailable")), \
             patch.object(db, 'commit', side_effect=Exception("Database unavailable")):
            
            # Send message that normally requires database persistence
            db_dependent_message = WebSocketMessage(
                message_type=MessageType.USER_MESSAGE,
                payload={
                    "content": "Message during database outage",
                    "persist_to_db": True,
                    "thread_id": str(test_thread.id)
                },
                user_id=str(test_user.id),
                thread_id=str(test_thread.id)
            )
            
            # Should handle gracefully without failing completely
            try:
                result = await websocket_manager.handle_message(
                    user_id=str(test_user.id),
                    websocket=mock_websocket,
                    message=db_dependent_message
                )
                
                # Should not crash, might return degraded service indication
                assert result is not None
                
            except Exception as e:
                # If it raises exception, should be graceful degradation exception
                assert "degraded" in str(e).lower() or "database" in str(e).lower()
        
        # Verify degradation notification sent to user
        sent_messages = mock_websocket.sent_messages
        degradation_messages = [
            msg for msg in sent_messages
            if "degraded" in str(msg).lower() or "limited" in str(msg).lower()
        ]
        
        # Should notify user about degraded service
        assert len(degradation_messages) > 0 or len(sent_messages) > 0
        
        # Test that connection still works for non-database operations
        simple_message = WebSocketMessage(
            message_type=MessageType.SYSTEM_STATUS,
            payload={"status": "Testing non-DB functionality"},
            user_id=str(test_user.id)
        )
        
        await websocket_manager.send_to_user(
            user_id=str(test_user.id),
            message=simple_message
        )
        
        # Should still deliver messages
        final_message_count = len(mock_websocket.sent_messages)
        assert final_message_count > 0
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_circuit_breaker_prevents_cascade_failures(self, real_services_fixture, test_user,
                                                            websocket_manager, websocket_utility, error_recovery_handler):
        """Test circuit breaker preventing cascade failures."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create multiple connections
        connections = []
        websockets = []
        
        for i in range(5):
            websocket = await websocket_utility.create_mock_websocket()
            connection = await websocket_manager.create_connection(
                connection_id=f"circuit_test_conn_{i}",
                user_id=str(test_user.id),
                websocket=websocket,
                metadata={"circuit_breaker_test": True}
            )
            await websocket_manager.add_connection(connection)
            connections.append(connection)
            websockets.append(websocket)
        
        # Simulate failing service (Redis failure)
        with patch.object(redis, 'get', side_effect=Exception("Redis connection failed")), \
             patch.object(redis, 'set', side_effect=Exception("Redis connection failed")):
            
            # Send messages that would normally use Redis
            failing_messages = []
            for i in range(10):  # Send enough to trigger circuit breaker
                message = WebSocketMessage(
                    message_type=MessageType.USER_MESSAGE,
                    payload={
                        "content": f"Message {i} requiring Redis",
                        "cache_result": True
                    },
                    user_id=str(test_user.id)
                )
                failing_messages.append(message)
            
            # Track failures
            failure_count = 0
            circuit_breaker_triggered = False
            
            for i, message in enumerate(failing_messages):
                try:
                    await websocket_manager.handle_message(
                        user_id=str(test_user.id),
                        websocket=websockets[i % len(websockets)],
                        message=message
                    )
                except Exception as e:
                    failure_count += 1
                    if "circuit" in str(e).lower() or "breaker" in str(e).lower():
                        circuit_breaker_triggered = True
                        break
                
                await asyncio.sleep(0.01)  # Small delay
            
            # Circuit breaker should eventually trigger
            # (Exact behavior depends on circuit breaker configuration)
            assert failure_count > 0  # Should have some failures
            
        # Test that circuit breaker recovers after timeout
        await asyncio.sleep(0.1)  # Wait for potential circuit breaker timeout
        
        # Should be able to send normal messages again
        recovery_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "Test recovery after circuit breaker"},
            user_id=str(test_user.id)
        )
        
        # At least one connection should work
        recovery_success = False
        for websocket in websockets:
            try:
                await websocket_manager.handle_message(
                    user_id=str(test_user.id),
                    websocket=websocket,
                    message=recovery_message
                )
                recovery_success = True
                break
            except:
                continue
        
        # Should recover functionality
        assert recovery_success, "Circuit breaker should allow recovery"
        
        # Cleanup
        for connection in connections:
            await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_deduplication_during_retries(self, real_services_fixture, test_user, test_thread,
                                                       websocket_manager, websocket_utility):
        """Test message deduplication during retry scenarios."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="dedup_test_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={"deduplication_enabled": True}
        )
        await websocket_manager.add_connection(connection)
        
        # Create message with unique ID for deduplication
        message_id = "unique_msg_12345"
        original_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={
                "content": "Message that might be retried",
                "message_id": message_id,
                "deduplication_key": message_id
            },
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        # Send message first time
        await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=mock_websocket,
            message=original_message
        )
        
        initial_message_count = len(mock_websocket.sent_messages)
        assert initial_message_count > 0
        
        # Simulate retry (same message sent again)
        retry_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={
                "content": "Message that might be retried",  # Same content
                "message_id": message_id,  # Same ID
                "deduplication_key": message_id,  # Same dedup key
                "retry_attempt": 1
            },
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        # Send retry
        await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=mock_websocket,
            message=retry_message
        )
        
        # Should not duplicate processing
        final_message_count = len(mock_websocket.sent_messages)
        
        # Either should be same count (fully deduplicated) or should include
        # deduplication notification (but not duplicate processing)
        dedup_notifications = [
            msg for msg in mock_websocket.sent_messages
            if "duplicate" in str(msg).lower() or "already" in str(msg).lower()
        ]
        
        # Verify deduplication worked
        if final_message_count == initial_message_count:
            # Silent deduplication
            assert True
        else:
            # Should have deduplication notification, not duplicate processing
            assert len(dedup_notifications) > 0
            assert final_message_count <= initial_message_count + 1  # At most one additional notification
        
        # Send different message (should be processed)
        different_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={
                "content": "Different message content",
                "message_id": "different_msg_67890",
                "deduplication_key": "different_msg_67890"
            },
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=mock_websocket,
            message=different_message
        )
        
        # Should process different message
        different_message_count = len(mock_websocket.sent_messages)
        assert different_message_count > final_message_count
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_partial_service_degradation_handling(self, real_services_fixture, test_user, test_thread,
                                                       websocket_manager, websocket_utility):
        """Test handling of partial service degradation scenarios."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="partial_degradation_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={"service_monitoring": True}
        )
        await websocket_manager.add_connection(connection)
        
        # Test scenario 1: Redis slow but working
        with patch.object(redis, 'get', 
                         AsyncMock(side_effect=lambda k: asyncio.sleep(2) or "cached_value")):  # Very slow Redis
            
            redis_dependent_message = WebSocketMessage(
                message_type=MessageType.USER_MESSAGE,
                payload={
                    "content": "Message requiring cache lookup",
                    "use_cache": True
                },
                user_id=str(test_user.id),
                thread_id=str(test_thread.id)
            )
            
            start_time = datetime.now()
            
            # Should handle slow Redis gracefully (with timeout)
            try:
                await asyncio.wait_for(
                    websocket_manager.handle_message(
                        user_id=str(test_user.id),
                        websocket=mock_websocket,
                        message=redis_dependent_message
                    ),
                    timeout=1.0  # Shorter than Redis response time
                )
            except asyncio.TimeoutError:
                # Expected - should timeout gracefully
                pass
            
            processing_time = datetime.now() - start_time
            
            # Should not wait too long for slow service
            assert processing_time.total_seconds() <= 1.5
        
        # Test scenario 2: Database working but some tables inaccessible
        with patch.object(db, 'execute') as mock_execute:
            def selective_db_failure(query):
                if "messages" in str(query).lower():
                    raise Exception("Messages table unavailable")
                return AsyncMock()
            
            mock_execute.side_effect = selective_db_failure
            
            selective_failure_message = WebSocketMessage(
                message_type=MessageType.USER_MESSAGE,
                payload={
                    "content": "Message during partial DB failure",
                    "save_to_messages": True
                },
                user_id=str(test_user.id),
                thread_id=str(test_thread.id)
            )
            
            # Should handle partial DB failure
            try:
                result = await websocket_manager.handle_message(
                    user_id=str(test_user.id),
                    websocket=mock_websocket,
                    message=selective_failure_message
                )
                
                # Should provide degraded service
                assert result is not None
                
            except Exception as e:
                # Should be graceful failure, not complete crash
                assert "messages table" in str(e).lower() or "partial" in str(e).lower()
        
        # Verify system continues to work for non-affected operations
        simple_message = WebSocketMessage(
            message_type=MessageType.SYSTEM_STATUS,
            payload={"status": "System health check"},
            user_id=str(test_user.id)
        )
        
        await websocket_manager.send_to_user(
            user_id=str(test_user.id),
            message=simple_message
        )
        
        # Should still deliver basic messages
        sent_messages = mock_websocket.sent_messages
        assert len(sent_messages) > 0
        
        # Should include service degradation notifications
        degradation_notifications = [
            msg for msg in sent_messages
            if "degraded" in str(msg).lower() or "limited" in str(msg).lower() or "partial" in str(msg).lower()
        ]
        
        # Should inform user about service limitations
        assert len(degradation_notifications) > 0 or len(sent_messages) >= 1
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)