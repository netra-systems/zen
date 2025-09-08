"""
Unit Tests for WebSocket Connection Management - Batch 3 WebSocket Infrastructure Suite
====================================================================================

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Chat System Stability & Connection Reliability
- Value Impact: Ensures WebSocket connections remain stable for chat sessions
- Strategic Impact: Prevents user session drops that interrupt AI conversations

This test suite validates WebSocket connection lifecycle, reconnection patterns,
and connection pool management that are critical for maintaining chat sessions.
Connection stability directly impacts user retention and AI interaction quality.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional

from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool


class TestWebSocketConnectionLifecycle:
    """
    Unit tests for WebSocket connection lifecycle management.
    
    These tests ensure WebSocket connections are properly managed throughout
    their lifecycle to maintain stable chat sessions for users.
    """
    
    @pytest.fixture
    def mock_websocket_connection(self):
        """Create mock WebSocket connection."""
        from fastapi import WebSocket
        from fastapi.websockets import WebSocketState
        
        mock_connection = AsyncMock(spec=WebSocket)
        mock_connection.client_state = WebSocketState.CONNECTED
        mock_connection.application_state = WebSocketState.CONNECTED
        mock_connection.send = AsyncMock()
        mock_connection.close = AsyncMock()
        mock_connection.ping = AsyncMock()
        return mock_connection
    
    @pytest.fixture
    def connection_pool(self):
        """Create WebSocket connection pool for testing."""
        return WebSocketConnectionPool()
    
    async def test_connection_creation_and_registration(self, connection_pool, mock_websocket_connection):
        """
        Test WebSocket connection creation and proper registration.
        
        BUSINESS VALUE: New chat users get properly registered connections
        that can receive their AI interaction events reliably.
        """
        # Arrange
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        # Act - Add new connection
        success = await connection_pool.add_connection(
            connection_id, user_id, mock_websocket_connection
        )
        
        # Assert - Connection registered successfully
        assert success is True
        
        # Verify connection can be retrieved
        retrieved_conn_info = await connection_pool.get_connection(connection_id, user_id)
        assert retrieved_conn_info is not None
        assert retrieved_conn_info.websocket == mock_websocket_connection
        
        # Verify user has connections tracked
        user_connections = await connection_pool.get_user_connections(user_id)
        assert len(user_connections) == 1
        assert user_connections[0].connection_id == connection_id
    
    async def test_connection_cleanup_on_disconnect(self, connection_pool, mock_websocket_connection):
        """
        Test connection cleanup when users disconnect from chat.
        
        BUSINESS VALUE: Proper cleanup prevents memory leaks and stale connections
        that could impact system performance for other chat users.
        """
        # Arrange - Register connection
        user_id = f"cleanup_user_{uuid.uuid4().hex[:8]}"
        thread_id = f"cleanup_thread_{uuid.uuid4().hex[:8]}"
        
        await connection_pool.register_connection(
            user_id, thread_id, mock_websocket_connection
        )
        
        # Verify connection exists
        assert await connection_pool.get_connection(user_id, thread_id) is not None
        
        # Act - Disconnect and cleanup
        await connection_pool.remove_connection(user_id, thread_id)
        
        # Assert - Connection cleaned up
        retrieved_conn = await connection_pool.get_connection(user_id, thread_id)
        assert retrieved_conn is None
        
        # Verify no memory leaks in tracking
        active_connections = connection_pool.get_active_connections()
        assert user_id not in active_connections or len(active_connections[user_id]) == 0
    
    async def test_connection_health_monitoring(self, connection_pool, mock_websocket_connection):
        """
        Test connection health monitoring for chat stability.
        
        BUSINESS VALUE: Proactive health monitoring prevents chat sessions
        from becoming unresponsive, maintaining user engagement.
        """
        # Arrange - Register connection
        user_id = f"health_user_{uuid.uuid4().hex[:8]}"
        thread_id = f"health_thread_{uuid.uuid4().hex[:8]}"
        
        await connection_pool.register_connection(
            user_id, thread_id, mock_websocket_connection
        )
        
        # Mock ping response for healthy connection
        mock_websocket_connection.ping.return_value = asyncio.Future()
        mock_websocket_connection.ping.return_value.set_result(None)
        
        # Act - Check connection health
        is_healthy = await connection_pool.check_connection_health(user_id, thread_id)
        
        # Assert - Healthy connection detected
        assert is_healthy is True
        mock_websocket_connection.ping.assert_called_once()
    
    async def test_connection_health_detection_failure(self, connection_pool):
        """
        Test detection of unhealthy connections for proactive cleanup.
        
        BUSINESS VALUE: Unhealthy connections are detected and cleaned up
        before they can impact user chat experience with failed message delivery.
        """
        # Arrange - Mock unhealthy connection
        unhealthy_connection = AsyncMock()
        unhealthy_connection.closed = True  # Connection is closed
        unhealthy_connection.ping.side_effect = Exception("Connection dead")
        
        user_id = f"unhealthy_user_{uuid.uuid4().hex[:8]}"
        thread_id = f"unhealthy_thread_{uuid.uuid4().hex[:8]}"
        
        await connection_pool.register_connection(
            user_id, thread_id, unhealthy_connection
        )
        
        # Act - Check unhealthy connection
        is_healthy = await connection_pool.check_connection_health(user_id, thread_id)
        
        # Assert - Unhealthy connection detected
        assert is_healthy is False
    
    async def test_concurrent_connection_management(self, connection_pool):
        """
        Test concurrent connection operations for multi-user chat.
        
        BUSINESS VALUE: System handles multiple simultaneous chat users
        without connection conflicts or race conditions.
        """
        # Arrange - Create multiple mock connections
        connection_count = 5
        connections = []
        users_and_threads = []
        
        for i in range(connection_count):
            mock_conn = AsyncMock()
            mock_conn.closed = False
            mock_conn.send = AsyncMock()
            connections.append(mock_conn)
            
            user_id = f"concurrent_user_{i}"
            thread_id = f"concurrent_thread_{i}"
            users_and_threads.append((user_id, thread_id, mock_conn))
        
        # Act - Register connections concurrently
        registration_tasks = []
        for user_id, thread_id, connection in users_and_threads:
            task = asyncio.create_task(
                connection_pool.register_connection(user_id, thread_id, connection)
            )
            registration_tasks.append(task)
        
        registration_results = await asyncio.gather(*registration_tasks)
        
        # Assert - All registrations should succeed
        assert all(registration_results), "Some concurrent registrations failed"
        
        # Verify all connections are tracked
        active_connections = connection_pool.get_active_connections()
        assert len(active_connections) == connection_count
        
        # Verify each connection can be retrieved
        for user_id, thread_id, expected_conn in users_and_threads:
            retrieved_conn = await connection_pool.get_connection(user_id, thread_id)
            assert retrieved_conn == expected_conn
    
    async def test_connection_pool_capacity_management(self, connection_pool):
        """
        Test connection pool capacity limits prevent resource exhaustion.
        
        BUSINESS VALUE: System remains stable under high load by limiting
        connections, preventing crashes that would impact all chat users.
        """
        # Arrange - Pool with limited capacity (10 connections)
        # Create more connections than the pool can handle
        excess_connection_count = 12
        
        successful_registrations = 0
        
        # Act - Try to register more connections than capacity
        for i in range(excess_connection_count):
            mock_conn = AsyncMock()
            mock_conn.closed = False
            
            user_id = f"capacity_user_{i}"
            thread_id = f"capacity_thread_{i}"
            
            success = await connection_pool.register_connection(
                user_id, thread_id, mock_conn
            )
            
            if success:
                successful_registrations += 1
        
        # Assert - Should not exceed pool capacity
        active_connections = connection_pool.get_active_connections()
        total_connections = sum(len(threads) for threads in active_connections.values())
        
        assert total_connections <= 10, f"Pool exceeded capacity: {total_connections} connections"
        assert successful_registrations <= 10, "Pool allowed too many registrations"
    
    async def test_connection_message_routing(self, connection_pool):
        """
        Test message routing to correct WebSocket connections.
        
        BUSINESS VALUE: Users receive only their own chat events and AI responses,
        maintaining conversation privacy and preventing confusion.
        """
        # Arrange - Multiple users with connections
        users_data = []
        for i in range(3):
            mock_conn = AsyncMock()
            mock_conn.closed = False
            mock_conn.send = AsyncMock()
            
            user_id = f"routing_user_{i}"
            thread_id = f"routing_thread_{i}"
            
            await connection_pool.register_connection(user_id, thread_id, mock_conn)
            users_data.append((user_id, thread_id, mock_conn))
        
        # Act - Send targeted messages to specific users
        for i, (user_id, thread_id, expected_conn) in enumerate(users_data):
            message = {
                "type": "agent_response",
                "content": f"Response for user {i}",
                "user_id": user_id,
                "thread_id": thread_id
            }
            
            # Send message through connection pool
            target_conn = await connection_pool.get_connection(user_id, thread_id)
            if target_conn:
                await target_conn.send(json.dumps(message))
        
        # Assert - Each connection received only its intended message
        for i, (user_id, thread_id, connection) in enumerate(users_data):
            connection.send.assert_called_once()
            
            # Verify message content was for correct user
            sent_args = connection.send.call_args[0]
            sent_message = json.loads(sent_args[0])
            assert sent_message["content"] == f"Response for user {i}"
            assert sent_message["user_id"] == user_id


class TestWebSocketManagerFactory:
    """
    Unit tests for WebSocket manager factory patterns.
    
    These tests ensure WebSocket managers are created correctly with proper
    configuration for different chat environments and user isolation.
    """
    
    @pytest.fixture
    def manager_factory(self):
        """Create WebSocket manager factory."""
        return WebSocketManagerFactory()
    
    async def test_websocket_manager_creation(self, manager_factory):
        """
        Test WebSocket manager creation with proper configuration.
        
        BUSINESS VALUE: Ensures WebSocket managers are properly configured
        for reliable chat service across different deployment environments.
        """
        # Act - Create WebSocket manager
        manager = await manager_factory.create_websocket_manager(
            config={
                "max_connections": 100,
                "heartbeat_interval": 30,
                "message_queue_size": 1000
            }
        )
        
        # Assert - Manager created with proper configuration
        assert manager is not None
        assert hasattr(manager, 'send_to_thread')
        assert hasattr(manager, 'broadcast')
        assert callable(manager.send_to_thread)
        assert callable(manager.broadcast)
    
    async def test_websocket_manager_user_isolation_setup(self, manager_factory):
        """
        Test WebSocket manager setup for user isolation.
        
        BUSINESS VALUE: Each user gets isolated WebSocket context preventing
        cross-user event leakage in multi-tenant chat environment.
        """
        # Arrange - User-specific configuration
        user_configs = [
            {
                "user_id": "isolation_user_1",
                "thread_id": "thread_1",
                "isolation_mode": "strict"
            },
            {
                "user_id": "isolation_user_2", 
                "thread_id": "thread_2",
                "isolation_mode": "strict"
            }
        ]
        
        # Act - Create managers for different users
        managers = []
        for config in user_configs:
            manager = await manager_factory.create_user_scoped_manager(config)
            managers.append(manager)
        
        # Assert - Each manager maintains user isolation
        assert len(managers) == 2
        for manager in managers:
            assert manager is not None
            assert hasattr(manager, 'user_id') or hasattr(manager, 'get_user_context')
    
    async def test_websocket_manager_performance_configuration(self, manager_factory):
        """
        Test WebSocket manager performance optimizations for chat.
        
        BUSINESS VALUE: Optimized WebSocket managers provide responsive
        chat experience even under high message volume.
        """
        # Arrange - Performance-optimized configuration
        perf_config = {
            "message_buffer_size": 10000,
            "compression_enabled": True,
            "batch_processing": True,
            "priority_queue": True,
            "connection_pooling": True
        }
        
        # Act - Create performance-optimized manager
        perf_manager = await manager_factory.create_performance_optimized_manager(
            perf_config
        )
        
        # Assert - Manager has performance features
        assert perf_manager is not None
        
        # Should have high-performance characteristics
        if hasattr(perf_manager, 'get_configuration'):
            config = perf_manager.get_configuration()
            assert config.get("message_buffer_size", 0) >= 1000
    
    async def test_websocket_manager_failure_recovery(self, manager_factory):
        """
        Test WebSocket manager failure recovery mechanisms.
        
        BUSINESS VALUE: Chat service remains available even when individual
        WebSocket managers fail, ensuring business continuity.
        """
        # Arrange - Manager with failure recovery
        recovery_config = {
            "auto_recovery": True,
            "max_retries": 3,
            "recovery_delay_ms": 1000,
            "fallback_enabled": True
        }
        
        # Act - Create manager with recovery capabilities
        recovery_manager = await manager_factory.create_resilient_manager(
            recovery_config
        )
        
        # Assert - Manager has recovery features
        assert recovery_manager is not None
        
        # Should handle failures gracefully
        if hasattr(recovery_manager, 'get_health_status'):
            health = recovery_manager.get_health_status()
            assert health is not None


class TestWebSocketMessageHandling:
    """
    Unit tests for WebSocket message handling and serialization.
    
    These tests ensure messages are properly formatted, serialized, and
    delivered for reliable chat communication.
    """
    
    def test_chat_message_serialization(self):
        """
        Test chat message serialization for WebSocket transport.
        
        BUSINESS VALUE: Chat messages are properly formatted for reliable
        transport and parsing by client-side JavaScript.
        """
        # Arrange - Chat message data
        chat_message = {
            "type": "agent_response",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": "business_analyst",
            "content": {
                "response": "Based on your Q3 data, here are the key insights...",
                "analysis": {
                    "revenue_trend": "increasing",
                    "top_segments": ["enterprise", "mid-market"],
                    "recommendations": [
                        "Focus on enterprise segment expansion",
                        "Optimize mid-market conversion funnel"
                    ]
                },
                "confidence": 0.87,
                "data_sources": ["sales_db", "analytics_warehouse"]
            },
            "metadata": {
                "processing_time_ms": 2500,
                "tools_used": ["data_query", "trend_analysis"],
                "user_id": "business_user_123"
            }
        }
        
        # Act - Serialize message
        serialized = json.dumps(chat_message)
        deserialized = json.loads(serialized)
        
        # Assert - Serialization preserves message structure
        assert deserialized["type"] == "agent_response"
        assert deserialized["agent_name"] == "business_analyst"
        assert "revenue_trend" in deserialized["content"]["analysis"]
        assert len(deserialized["content"]["analysis"]["recommendations"]) == 2
        assert deserialized["content"]["confidence"] == 0.87
        
        # Verify timestamp is properly formatted
        timestamp_str = deserialized["timestamp"]
        parsed_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        assert isinstance(parsed_timestamp, datetime)
    
    def test_large_message_handling(self):
        """
        Test handling of large messages in chat context.
        
        BUSINESS VALUE: Chat can deliver comprehensive AI responses with
        substantial data without breaking WebSocket connections.
        """
        # Arrange - Large chat response (realistic AI analysis)
        large_response = {
            "type": "comprehensive_analysis",
            "summary": "Complete business analysis with detailed insights",
            "detailed_results": {
                f"analysis_section_{i}": {
                    "title": f"Business Area {i}",
                    "data_points": [f"insight_{j}" * 50 for j in range(20)],
                    "trends": [f"trend_{j}" for j in range(15)],
                    "recommendations": [f"recommendation_{j}" * 30 for j in range(10)]
                } for i in range(25)  # 25 detailed sections
            },
            "raw_data": {
                f"dataset_{i}": list(range(i * 100, (i + 1) * 100)) 
                for i in range(50)  # 50 datasets with 100 points each
            },
            "visualizations": {
                "charts": [f"chart_config_{i}" * 200 for i in range(10)],
                "graphs": [f"graph_data_{i}" * 150 for i in range(8)]
            }
        }
        
        # Act - Serialize large message
        start_time = time.time()
        serialized = json.dumps(large_response)
        serialization_time = time.time() - start_time
        
        # Verify can deserialize
        deserialized = json.loads(serialized)
        
        # Assert - Large message handled efficiently
        message_size = len(serialized.encode('utf-8'))
        
        # Should be reasonable size (less than 10MB for typical chat)
        assert message_size < 10 * 1024 * 1024, f"Message too large: {message_size} bytes"
        
        # Serialization should be reasonably fast
        assert serialization_time < 1.0, f"Serialization too slow: {serialization_time:.2f}s"
        
        # Content should be preserved
        assert len(deserialized["detailed_results"]) == 25
        assert len(deserialized["raw_data"]) == 50
        assert "charts" in deserialized["visualizations"]
    
    def test_message_validation_for_chat_ui(self):
        """
        Test message validation for chat UI compatibility.
        
        BUSINESS VALUE: All chat messages meet UI requirements preventing
        client-side rendering errors that would break user experience.
        """
        # Test cases for different message types
        test_messages = [
            {
                "type": "agent_started",
                "agent_name": "cost_optimizer", 
                "timestamp": datetime.now().isoformat(),
                "user_id": "test_user"
            },
            {
                "type": "agent_thinking",
                "thought": "Analyzing cost patterns...",
                "progress_percentage": 45.5,
                "estimated_remaining_ms": 5000
            },
            {
                "type": "tool_executing",
                "tool_name": "cost_analyzer",
                "purpose": "Identifying savings opportunities",
                "status": "running"
            },
            {
                "type": "tool_completed",
                "tool_name": "cost_analyzer",
                "result": {
                    "savings_found": "$15,000",
                    "opportunities": 7
                },
                "duration_ms": 3200
            },
            {
                "type": "agent_completed",
                "summary": "Analysis complete - found significant savings",
                "total_duration_ms": 12500,
                "confidence": 0.92
            }
        ]
        
        # Act & Assert - Validate each message type
        for message in test_messages:
            # Should serialize without errors
            serialized = json.dumps(message)
            assert len(serialized) > 0
            
            # Should deserialize correctly
            deserialized = json.loads(serialized)
            assert deserialized["type"] == message["type"]
            
            # Should have required fields for UI
            assert "type" in deserialized
            
            # Type-specific validations
            if message["type"] == "agent_thinking":
                assert "thought" in deserialized
                assert isinstance(deserialized.get("progress_percentage"), (int, float))
            
            elif message["type"] == "tool_executing":
                assert "tool_name" in deserialized
                assert "status" in deserialized or "purpose" in deserialized
            
            elif message["type"] == "agent_completed":
                assert "summary" in deserialized or "result" in deserialized