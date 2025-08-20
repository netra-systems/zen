"""Final Integration Tests for Example Message Flow System

End-to-end integration tests that verify the complete system works together
with all production-ready enhancements and reliability features.

Business Value: Ensures complete Free-to-Paid conversion flow works flawlessly
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

# Import all enhanced components
from app.routes.example_messages_enhanced import (
    router, MessageSequencer, ConnectionStateManager,
    message_sequencer, connection_manager
)
from app.handlers.example_message_handler_enhanced import (
    EnhancedExampleMessageHandler, handle_example_message,
    get_example_message_handler
)
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestCompleteIntegrationFlow:
    """Complete end-to-end integration testing"""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with enhanced routes"""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        mocks = {}
        
        # Mock WebSocket manager
        mocks['ws_manager'] = Mock()
        mocks['ws_manager'].connect_user = AsyncMock(return_value={'connection_id': 'test'})
        mocks['ws_manager'].disconnect_user = AsyncMock()
        mocks['ws_manager'].send_message_to_user = AsyncMock()
        mocks['ws_manager'].handle_message = AsyncMock()
        
        # Mock database
        mocks['db_session'] = AsyncMock()
        mocks['db_session'].execute = AsyncMock()
        mocks['db_session'].__aenter__ = AsyncMock(return_value=mocks['db_session'])
        mocks['db_session'].__aexit__ = AsyncMock()
        
        # Mock LLM manager
        mocks['llm_manager'] = Mock()
        
        # Mock supervisor
        mocks['supervisor'] = Mock()
        mocks['supervisor'].process_message = AsyncMock(
            return_value=Mock(content="Test optimization response")
        )
        
        return mocks

    @pytest.mark.asyncio
    async def test_complete_message_processing_flow(self, mock_dependencies):
        """Test complete message processing from start to finish"""
        
        with patch('app.routes.example_messages_enhanced.get_manager', return_value=mock_dependencies['ws_manager']):
            with patch('app.routes.example_messages_enhanced.get_async_db', return_value=mock_dependencies['db_session']):
                with patch('app.handlers.example_message_handler_enhanced.get_manager', return_value=mock_dependencies['ws_manager']):
                    
                    # Create handler instance
                    handler = EnhancedExampleMessageHandler()
                    
                    # Mock the real agent integration
                    handler.real_agent_integration.supervisor = mock_dependencies['supervisor']
                    
                    # Test message
                    message = {
                        "content": "Complete integration test optimization request with sufficient length",
                        "example_message_id": "integration_test_001",
                        "example_message_metadata": {
                            "title": "Integration Test",
                            "category": "cost-optimization",
                            "complexity": "advanced",
                            "businessValue": "conversion",
                            "estimatedTime": "30s"
                        },
                        "user_id": "integration_user_001",
                        "timestamp": int(time.time() * 1000)
                    }
                    
                    # Process message
                    response = await handler.handle_example_message(message)
                    
                    # Verify complete processing
                    assert response is not None
                    assert response.status == 'completed'
                    assert response.message_id == "integration_test_001"
                    assert response.real_agent_execution == True
                    assert response.business_insights is not None
                    assert response.execution_metadata is not None
                    
                    # Verify WebSocket notifications were sent
                    assert mock_dependencies['ws_manager'].send_message_to_user.call_count >= 2
                    
                    # Verify notifications have correct structure
                    calls = mock_dependencies['ws_manager'].send_message_to_user.call_args_list
                    
                    # Check processing started notification
                    start_call = calls[0][0]  # First positional argument
                    start_user_id = start_call[0]
                    start_message = start_call[1]
                    
                    assert start_user_id == "integration_user_001"
                    assert start_message['type'] == 'processing_started'
                    assert 'session_id' in start_message['payload']
                    
                    # Check completion notification
                    completion_call = calls[1][0]
                    completion_user_id = completion_call[0]
                    completion_message = completion_call[1]
                    
                    assert completion_user_id == "integration_user_001"
                    assert completion_message['type'] == 'agent_completed'
                    assert completion_message['payload']['real_agent_execution'] == True

    def test_enhanced_api_endpoints(self, client, mock_dependencies):
        """Test all enhanced API endpoints"""
        
        with patch('app.routes.example_messages_enhanced.get_example_message_handler') as mock_handler_getter:
            mock_handler = Mock()
            mock_handler.get_session_stats.return_value = {
                'active_sessions': 5,
                'processing_sessions': 2,
                'avg_processing_time': 15.5
            }
            mock_handler.get_active_sessions.return_value = {
                'session_1': {'status': 'processing', 'metadata': {'category': 'cost-optimization'}},
                'session_2': {'status': 'completed', 'metadata': {'category': 'latency-optimization'}}
            }
            mock_handler_getter.return_value = mock_handler
            
            with patch('app.routes.example_messages_enhanced.get_async_db', return_value=mock_dependencies['db_session']):
                
                # Test enhanced stats endpoint
                response = client.get("/api/v1/example-messages/stats")
                assert response.status_code == 200
                
                data = response.json()
                assert data['status'] == 'success'
                assert 'circuit_breaker_stats' in data
                assert 'message_sequencing_stats' in data
                assert 'connection_stats' in data
                
                # Test enhanced health endpoint
                response = client.get("/api/v1/example-messages/health")
                assert response.status_code in [200, 503]  # Could be degraded
                
                health_data = response.json()
                assert 'handler_active' in health_data
                assert 'database_healthy' in health_data
                assert 'circuit_breaker_healthy' in health_data
                assert 'system_metrics' in health_data
                
                # Test circuit breaker reset endpoint
                response = client.get("/api/v1/example-messages/circuit-breaker/reset")
                assert response.status_code == 200
                
                # Test pending messages endpoint
                response = client.get("/api/v1/example-messages/pending-messages/test_user")
                assert response.status_code == 200
                
                pending_data = response.json()
                assert 'pending_count' in pending_data
                assert 'pending_messages' in pending_data

    @pytest.mark.asyncio
    async def test_websocket_enhanced_functionality(self, mock_dependencies):
        """Test enhanced WebSocket functionality with all features"""
        
        # Mock WebSocket
        websocket = Mock(spec=WebSocket)
        websocket.receive_text = AsyncMock()
        websocket.close = AsyncMock()
        websocket.send_text = AsyncMock()
        
        # Mock handler
        mock_handler = Mock()
        mock_handler.get_session_stats.return_value = {}
        mock_handler.get_active_sessions.return_value = {}
        mock_handler.cleanup_user_sessions = Mock()
        
        with patch('app.routes.example_messages_enhanced.get_manager', return_value=mock_dependencies['ws_manager']):
            with patch('app.routes.example_messages_enhanced.get_example_message_handler', return_value=mock_handler):
                with patch('app.routes.example_messages_enhanced.get_async_db', return_value=mock_dependencies['db_session']):
                    
                    # Import the enhanced websocket function
                    from app.routes.example_messages_enhanced import example_message_websocket_enhanced
                    
                    # Test connection establishment
                    websocket.receive_text.side_effect = WebSocketDisconnect
                    
                    # Should handle connection and disconnection gracefully
                    await example_message_websocket_enhanced(websocket, "test_user_ws")
                    
                    # Verify connection manager was used
                    mock_dependencies['ws_manager'].connect_user.assert_called_once_with("test_user_ws", websocket)
                    mock_dependencies['ws_manager'].disconnect_user.assert_called_once_with("test_user_ws", websocket)
                    
                    # Verify cleanup was called
                    mock_handler.cleanup_user_sessions.assert_called_once_with("test_user_ws")

    @pytest.mark.asyncio
    async def test_message_sequencing_integration(self):
        """Test message sequencing works correctly in integration"""
        
        sequencer = MessageSequencer()
        user_id = "sequencing_test_user"
        
        # Simulate complete message flow with sequencing
        messages = []
        for i in range(5):
            sequence = sequencer.get_next_sequence(user_id)
            message = {
                "type": "integration_test",
                "sequence": sequence,
                "payload": {"test_data": f"message_{i}"}
            }
            
            # Add to pending (transactional start)
            sequencer.add_pending_message(user_id, sequence, message)
            messages.append((sequence, message))
        
        # Verify all messages are pending
        pending = sequencer.get_pending_messages(user_id)
        assert len(pending) == 5
        
        # Simulate sending with some failures
        for i, (sequence, message) in enumerate(messages):
            # Mark as sending
            assert sequencer.mark_message_sending(user_id, sequence) == True
            
            if i % 2 == 0:  # Simulate success for even messages
                assert sequencer.acknowledge_message(user_id, sequence) == True
            else:  # Simulate failure for odd messages
                sequencer.revert_message_to_pending(user_id, sequence)
        
        # Check final state
        pending = sequencer.get_pending_messages(user_id)
        assert len(pending) == 2  # Only failed messages should remain
        
        # Verify failed messages can be retried
        for sequence in pending:
            assert sequencer.should_retry_message(user_id, sequence) == True

    @pytest.mark.asyncio
    async def test_session_lifecycle_integration(self):
        """Test complete session lifecycle integration"""
        
        handler = EnhancedExampleMessageHandler()
        session_manager = handler.session_manager
        
        # Create session
        user_id = "lifecycle_user"
        message_id = "lifecycle_message"
        metadata = {"category": "cost-optimization", "complexity": "basic"}
        
        session_id = await session_manager.create_session(user_id, message_id, metadata)
        
        # Verify session exists
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session['user_id'] == user_id
        assert session['status'] == 'created'
        
        # Simulate session updates during processing
        updates = [
            {'status': 'processing', 'agent_name': 'Test Agent'},
            {'status': 'agent_thinking', 'progress': 50},
            {'status': 'generating_result', 'progress': 80},
            {'status': 'completed', 'progress': 100, 'result': {'success': True}}
        ]
        
        for update in updates:
            assert session_manager.update_session(session_id, update) == True
            updated_session = session_manager.get_session(session_id)
            for key, value in update.items():
                assert updated_session[key] == value
        
        # Test session cleanup
        await session_manager._cleanup_session(session_id)
        
        # Verify session is removed
        assert session_manager.get_session(session_id) is None

    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration across components"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Test circuit breaker is properly configured
        assert handler.processing_circuit_breaker is not None
        assert handler.real_agent_integration.circuit_breaker is not None
        
        # Test circuit breaker state
        assert handler.processing_circuit_breaker.state in ["CLOSED", "HALF_OPEN", "OPEN"]
        assert handler.real_agent_integration.circuit_breaker.state in ["CLOSED", "HALF_OPEN", "OPEN"]
        
        # Test circuit breaker reset functionality
        handler.processing_circuit_breaker.reset()
        assert handler.processing_circuit_breaker.state == "CLOSED"

    def test_error_handling_integration(self):
        """Test integrated error handling across all components"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Test validation error handling
        invalid_message = {
            "content": "short",  # Too short
            "user_id": "test"
            # Missing required fields
        }
        
        response = asyncio.run(handler.handle_example_message(invalid_message))
        assert response.status == 'error'
        assert response.error is not None
        assert 'validation' in response.execution_metadata.get('error_stage', '')

    @pytest.mark.asyncio
    async def test_memory_management_integration(self):
        """Test memory management across integrated components"""
        
        handler = EnhancedExampleMessageHandler()
        session_manager = handler.session_manager
        
        # Create multiple sessions
        session_ids = []
        for i in range(10):
            session_id = await session_manager.create_session(
                user_id=f"memory_user_{i}",
                message_id=f"memory_msg_{i}",
                metadata={"test": i}
            )
            session_ids.append(session_id)
        
        # Verify sessions exist
        stats_before = session_manager.get_stats()
        assert stats_before['active_sessions'] >= 10
        
        # Cleanup all sessions
        for session_id in session_ids:
            await session_manager._cleanup_session(session_id)
        
        # Verify cleanup
        stats_after = session_manager.get_stats()
        assert stats_after['active_sessions'] < stats_before['active_sessions']

    @pytest.mark.asyncio
    async def test_concurrent_integration_operations(self):
        """Test concurrent operations across integrated components"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Mock real agent integration for fast processing
        with patch.object(handler.real_agent_integration, 'execute_real_agent_processing') as mock_process:
            mock_process.return_value = {
                "agent_name": "Concurrent Test Agent",
                "optimization_type": "test",
                "real_agent_execution": True
            }
            
            # Create concurrent operations
            tasks = []
            for i in range(10):
                message = {
                    "content": f"Concurrent integration test {i} with sufficient length for processing",
                    "example_message_id": f"concurrent_integration_{i:03d}",
                    "example_message_metadata": {
                        "title": f"Concurrent Integration {i}",
                        "category": "cost-optimization",
                        "complexity": "basic",
                        "businessValue": "conversion",
                        "estimatedTime": "30s"
                    },
                    "user_id": f"concurrent_user_{i:03d}",
                    "timestamp": int(time.time() * 1000)
                }
                task = handler.handle_example_message(message)
                tasks.append(task)
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all completed successfully
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == 10, f"Only {len(successful_results)}/10 concurrent operations succeeded"
            
            # Verify all have correct status
            for result in successful_results:
                assert result.status == 'completed'
                assert result.real_agent_execution == True

    def test_business_value_integration(self):
        """Test business value features work end-to-end"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Test different business value scenarios
        business_values = ['conversion', 'retention', 'expansion']
        categories = ['cost-optimization', 'latency-optimization', 'model-selection']
        
        for bv in business_values:
            for category in categories:
                metadata_dict = {
                    "title": f"{category} for {bv}",
                    "category": category,
                    "complexity": "intermediate",
                    "businessValue": bv,
                    "estimatedTime": "30s"
                }
                
                from app.handlers.example_message_handler_enhanced import ExampleMessageMetadata
                metadata = ExampleMessageMetadata(**metadata_dict)
                
                result = {"real_agent_execution": True, "agent_name": "Test"}
                processing_time = 20000  # 20 seconds
                
                insights = handler._generate_enhanced_business_insights(metadata, result, processing_time)
                
                assert insights['business_value_type'] == bv
                assert insights['revenue_impact_category'] == category
                assert insights['real_agent_execution'] == True
                assert 'conversion_indicators' in insights


class TestProductionReadinessValidation:
    """Validate system is truly production-ready"""

    def test_all_components_initialized(self):
        """Test all components can be initialized without errors"""
        
        # Test handler initialization
        handler = EnhancedExampleMessageHandler()
        assert handler is not None
        assert handler.session_manager is not None
        assert handler.real_agent_integration is not None
        assert handler.processing_circuit_breaker is not None
        
        # Test session manager
        session_manager = handler.session_manager
        assert session_manager.active_sessions is not None
        assert session_manager.user_sessions is not None
        assert session_manager.session_timeouts is not None
        
        # Test real agent integration
        integration = handler.real_agent_integration
        assert integration.circuit_breaker is not None
        assert integration.llm_manager is not None

    def test_error_boundaries_complete(self):
        """Test all error boundaries are properly implemented"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Test each major operation has error handling
        test_message = {
            "content": "Error boundary test with sufficient length",
            "example_message_id": "error_test",
            "example_message_metadata": {
                "title": "Error Test",
                "category": "cost-optimization",
                "complexity": "basic",
                "businessValue": "conversion",
                "estimatedTime": "30s"
            },
            "user_id": "error_user",
            "timestamp": int(time.time() * 1000)
        }
        
        # Should handle processing gracefully even with mocked failures
        with patch.object(handler.real_agent_integration, 'execute_real_agent_processing') as mock_process:
            mock_process.side_effect = Exception("Simulated failure")
            
            response = asyncio.run(handler.handle_example_message(test_message))
            
            # Should not crash, should return error response
            assert response is not None
            assert response.status == 'error'
            assert response.error is not None

    def test_resource_cleanup_comprehensive(self):
        """Test comprehensive resource cleanup"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Create resources
        session_ids = []
        for i in range(5):
            session_id = asyncio.run(handler.session_manager.create_session(
                f"cleanup_user_{i}", f"cleanup_msg_{i}", {}
            ))
            session_ids.append(session_id)
        
        # Verify resources exist
        stats_before = handler.session_manager.get_stats()
        assert stats_before['active_sessions'] >= 5
        
        # Test user-level cleanup
        handler.cleanup_user_sessions("cleanup_user_0")
        
        # Test individual session cleanup
        for session_id in session_ids[1:]:
            asyncio.run(handler.session_manager._cleanup_session(session_id))
        
        # Verify cleanup
        stats_after = handler.session_manager.get_stats()
        assert stats_after['active_sessions'] < stats_before['active_sessions']

    def test_monitoring_and_observability(self):
        """Test monitoring and observability features"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Test statistics generation
        stats = handler.get_session_stats()
        assert isinstance(stats, dict)
        assert 'handler_type' in stats
        assert stats['handler_type'] == 'enhanced_with_real_agents'
        
        # Test session tracking
        active_sessions = handler.get_active_sessions()
        assert isinstance(active_sessions, dict)
        
        # Test circuit breaker stats
        assert 'circuit_breaker_state' in stats
        assert 'real_agent_availability' in stats

    def test_scalability_preparations(self):
        """Test system is prepared for scale"""
        
        # Test message sequencer can handle many users
        sequencer = MessageSequencer()
        
        for i in range(100):
            user_id = f"scale_user_{i:03d}"
            for j in range(10):
                seq = sequencer.get_next_sequence(user_id)
                sequencer.add_pending_message(user_id, seq, {"test": j})
        
        # Should handle 1000 total messages across 100 users
        total_pending = sum(
            len(sequencer.get_pending_messages(f"scale_user_{i:03d}"))
            for i in range(100)
        )
        assert total_pending == 1000
        
        # Test connection state manager
        connection_manager = ConnectionStateManager()
        
        for i in range(50):
            user_id = f"scale_conn_{i:03d}"
            conn_id = f"conn_{i:03d}"
            websocket = Mock()
            
            asyncio.run(connection_manager.register_connection(user_id, conn_id, websocket))
        
        # Should handle 50 concurrent connections
        valid_connections = sum(
            1 for i in range(50)
            if connection_manager.is_connection_valid(f"scale_conn_{i:03d}")
        )
        assert valid_connections == 50


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])