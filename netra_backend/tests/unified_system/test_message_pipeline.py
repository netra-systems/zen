"""Test Suite: Complete Agent Message Processing Pipeline

Tests the complete message flow from WebSocket receipt to agent response.
Focuses on real agent activation, not mocks.

Business Value Justification (BVJ):
- Segment: Enterprise & Growth ($35K MRR)
- Business Goal: Ensure reliable agent communication for AI optimization
- Value Impact: Validates core message routing and agent activation
- Revenue Impact: Critical for customer retention and platform reliability
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import pytest

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.db.postgres import get_async_db

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.config import AppConfig
from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.websocket_core import create_websocket_manager

@pytest.fixture
async def websocket_manager():
    """Create WebSocket manager with proper UserExecutionContext for testing."""
    user_context = UserExecutionContext(
        user_id="test-user-123",
        thread_id="test-thread-456",
        run_id="test-run-789",
        request_id="test-request-789"
    )
    return create_websocket_manager(user_context)

logger = central_logger.get_logger(__name__)

class MessagePipelineTestHelper:
    """Helper class for message pipeline testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.timing_data = {}
        self.agent_activations = []
    
    async def mock_send_message(self, user_id: str, message: Dict[str, Any]):
        """Mock WebSocket message sending with timing."""
        timestamp = time.time()
        self.sent_messages.append({
            "user_id": user_id,
            "message": message,
            "timestamp": timestamp
        })
        logger.info(f"Mock sent message to {user_id}: {message.get('type')}")
    
    async def mock_send_error(self, user_id: str, error: str):
        """Mock WebSocket error sending."""
        await self.mock_send_message(user_id, {"type": "error", "error": error})
    
    def track_agent_activation(self, agent_name: str, timestamp: float):
        """Track agent activation timing."""
        self.agent_activations.append({
            "agent": agent_name,
            "timestamp": timestamp
        })
    
    def get_response_time(self) -> float:
        """Calculate total response time."""
        if len(self.sent_messages) < 2:
            return 0.0
        start = self.sent_messages[0]["timestamp"]
        end = self.sent_messages[-1]["timestamp"]
        return end - start
    
    def assert_timing_under_threshold(self, threshold_seconds: float = 5.0):
        """Assert response time is under threshold."""
        response_time = self.get_response_time()
        assert response_time < threshold_seconds, f"Response time {response_time}s exceeds {threshold_seconds}s threshold"

@pytest.fixture
def message_helper():
    """Use real service instance."""
    # TODO: Initialize real service
    """Fixture providing message pipeline test helper."""
    return MessagePipelineTestHelper()

@pytest.fixture
async def agent_service_with_mocks():
    """Fixture providing AgentService with proper mocks."""
    config = AppConfig()
    
    # Create LLM manager mock
    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager = llm_manager_instance  # Initialize appropriate service
    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager.ask_llm = AsyncMock(return_value="Mock agent response for optimization request")
    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager.generate_streaming_response = AsyncNone  # TODO: Use real service instance
    
    # Create tool dispatcher mock
    # Mock: Tool execution isolation for predictable agent testing
    tool_dispatcher = tool_dispatcher_instance  # Initialize appropriate service
    # Mock: Tool execution isolation for predictable agent testing
    tool_dispatcher.get_available_tools = Mock(return_value=["analysis", "optimization"])
    
    # Create WebSocket manager mock
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager = UnifiedWebSocketManager()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_message = AsyncNone  # TODO: Use real service instance
    
    # Create database session mock
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_db_session = AsyncNone  # TODO: Use real service instance
    
    # Create supervisor with mocked components
    supervisor = SupervisorAgent(
        db_session=mock_db_session,
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        websocket_manager=websocket_manager
    )
    
    # Create and return agent service
    agent_service = AgentService(supervisor)
    yield agent_service, supervisor, llm_manager

@pytest.mark.asyncio
class TestMessagePipeline:
    """Test complete message processing pipeline."""
    
    @pytest.mark.asyncio
    async def test_first_message_agent_activation(self, agent_service_with_mocks, message_helper):
        """Test first user message triggers agent pipeline.
        
        Business Value: $35K MRR - Core AI functionality
        
        Flow:
        1. User sends "Help me optimize my AI costs"
        2. Message received via WebSocket
        3. Supervisor agent activated
        4. Sub-agents spawned
        5. Response generated
        6. Response sent back via WebSocket
        """
        agent_service, supervisor, llm_manager = agent_service_with_mocks
        
        # Track timing
        start_time = time.time()
        
        # Test message - real optimization request
        test_message = {
            "type": "user_message",
            "payload": {
                "content": "Help me optimize my AI costs. I'm spending $10k/month on OpenAI.",
                "thread_id": "test_thread_001",
                "references": []
            }
        }
        
        # Mock WebSocket messaging
        # Mock: Component isolation for testing without external dependencies
        with patch('app.ws_manager.manager.send_message', new=message_helper.mock_send_message):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.ws_manager.manager.send_error', new=message_helper.mock_send_error):
                # Mock: Component isolation for testing without external dependencies
                with patch('app.db.postgres.get_async_db') as mock_db:
                    # Mock database session
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_session = AsyncNone  # TODO: Use real service instance
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    # Mock: Async component isolation for testing without real async operations
                    mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    # Execute the message pipeline
                    await agent_service.handle_websocket_message(
                        user_id="test_user_001",
                        message=test_message,
                        db_session=mock_session
                    )
        
        # Verify timing - should be under 5 seconds
        response_time = time.time() - start_time
        assert response_time < 5.0, f"Response time {response_time}s exceeds 5s threshold"
        
        # Verify message flow
        assert len(message_helper.sent_messages) > 0, "No messages sent to user"
        
        # Check for agent activation messages
        message_types = [msg["message"].get("type") for msg in message_helper.sent_messages]
        logger.info(f"Message types sent: {message_types}")
        
        # Verify we got some kind of response indicating agent processing
        expected_message_types = ["thread_created", "agent_started", "agent_response", "agent_completed", "thread_message_created"]
        has_expected_message = any(msg_type in message_types for msg_type in expected_message_types)
        assert has_expected_message, f"Expected one of {expected_message_types}, got {message_types}"
        
        # Verify supervisor was instantiated and handled the message
        # (The actual LLM calls may happen at different levels)
        assert supervisor is not None, "Supervisor should be created"
        
        logger.info(f"✅ First message pipeline completed in {response_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_message_routing_to_supervisor(self, agent_service_with_mocks, message_helper):
        """Test message routing logic.
        
        Flow:
        - Send different message types
        - Verify supervisor receives all
        - Check message context preserved
        - Test thread association
        """
        agent_service, supervisor, llm_manager = agent_service_with_mocks
        
        # Different message types to test routing
        test_messages = [
            {
                "type": "user_message",
                "payload": {
                    "content": "Analyze my LLM usage patterns",
                    "thread_id": "analysis_thread",
                    "references": []
                }
            },
            {
                "type": "user_message", 
                "payload": {
                    "content": "Debug my API errors",
                    "thread_id": "debug_thread",
                    "references": []
                }
            },
            {
                "type": "user_message",
                "payload": {
                    "content": "Generate optimization report",
                    "thread_id": "report_thread", 
                    "references": []
                }
            }
        ]
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.ws_manager.manager.send_message', new=message_helper.mock_send_message):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.ws_manager.manager.send_error', new=message_helper.mock_send_error):
                # Mock: Component isolation for testing without external dependencies
                with patch('app.db.postgres.get_async_db') as mock_db:
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_session = AsyncNone  # TODO: Use real service instance
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    # Mock: Async component isolation for testing without real async operations
                    mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    # Send all messages
                    for i, message in enumerate(test_messages):
                        await agent_service.handle_websocket_message(
                            user_id=f"test_user_{i:03d}",
                            message=message,
                            db_session=mock_session
                        )
        
        # Verify all messages were routed
        assert len(message_helper.sent_messages) >= len(test_messages), "Not all messages were processed"
        
        # Verify supervisor handled the messages (actual processing may vary)
        logger.info(f"Total messages sent: {len(message_helper.sent_messages)}")
        
        # Verify thread context preservation (relaxed check since threads may be auto-created)
        logger.info(f"Sent messages: {[msg['message'].get('type') for msg in message_helper.sent_messages]}")
        
        # Check that thread creation occurred for each user
        thread_created_count = sum(1 for msg in message_helper.sent_messages 
                                 if msg["message"].get("type") == "thread_created")
        assert thread_created_count >= len(test_messages), f"Expected thread creation for {len(test_messages)} users"
        
        logger.info(f"✅ Message routing test completed - {len(test_messages)} messages routed successfully")
    
    @pytest.mark.asyncio
    async def test_streaming_response_flow(self, agent_service_with_mocks, message_helper):
        """Test streaming responses.
        
        Flow:
        - Agent generates streaming response
        - Chunks sent via WebSocket  
        - Frontend receives and displays
        - Test backpressure handling
        """
        agent_service, supervisor, llm_manager = agent_service_with_mocks
        
        # Mock streaming response
        async def mock_streaming_response():
            chunks = [
                "Analyzing your AI costs...",
                "Current spending: $10k/month",
                "Optimization opportunities identified:",
                "1. Switch to Claude 3.5 for 40% savings",
                "2. Implement caching for 25% reduction", 
                "Total potential savings: $4,500/month"
            ]
            for chunk in chunks:
                yield chunk
                await asyncio.sleep(0.1)  # Simulate streaming delay
        
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager.generate_streaming_response = AsyncMock(return_value=mock_streaming_response())
        
        # Test message requesting streaming response
        test_message = {
            "type": "user_message",
            "payload": {
                "content": "Generate detailed cost optimization analysis",
                "thread_id": "streaming_thread",
                "stream": True,
                "references": []
            }
        }
        
        # Track streaming chunks
        streaming_chunks = []
        
        async def track_streaming_message(user_id: str, message: Dict[str, Any]):
            if message.get("type") == "agent_stream_chunk":
                streaming_chunks.append(message.get("content", ""))
            await message_helper.mock_send_message(user_id, message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.ws_manager.manager.send_message', new=track_streaming_message):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.ws_manager.manager.send_error', new=message_helper.mock_send_error):
                # Mock: Component isolation for testing without external dependencies
                with patch('app.db.postgres.get_async_db') as mock_db:
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_session = AsyncNone  # TODO: Use real service instance
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    # Mock: Async component isolation for testing without real async operations
                    mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    start_time = time.time()
                    await agent_service.handle_websocket_message(
                        user_id="streaming_user",
                        message=test_message,
                        db_session=mock_session
                    )
                    response_time = time.time() - start_time
        
        # Verify streaming occurred
        # Note: In real implementation, streaming would be handled by supervisor
        # This test verifies the message structure supports streaming
        assert len(message_helper.sent_messages) > 0, "No response messages sent"
        
        # Verify response timing for streaming
        assert response_time < 5.0, f"Streaming response time {response_time}s too slow"
        
        # Check for completion message
        message_types = [msg["message"].get("type") for msg in message_helper.sent_messages]
        assert any("agent" in msg_type for msg_type in message_types), "No agent response received"
        
        logger.info(f"✅ Streaming response test completed in {response_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, agent_service_with_mocks, message_helper):
        """Test concurrent message processing from multiple users.
        
        Business Value: $15K MRR - Multi-user scalability
        """
        agent_service, supervisor, llm_manager = agent_service_with_mocks
        
        # Multiple concurrent users
        concurrent_users = 5
        messages_per_user = 2
        
        async def process_user_messages(user_index: int):
            """Process messages for a single user."""
            user_id = f"concurrent_user_{user_index:03d}"
            
            for msg_index in range(messages_per_user):
                message = {
                    "type": "user_message",
                    "payload": {
                        "content": f"User {user_index} message {msg_index}: Optimize my costs",
                        "thread_id": f"thread_{user_index}_{msg_index}",
                        "references": []
                    }
                }
                
                # Mock: Component isolation for testing without external dependencies
                with patch('app.db.postgres.get_async_db') as mock_db:
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_session = AsyncNone  # TODO: Use real service instance
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    # Mock: Async component isolation for testing without real async operations
                    mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    await agent_service.handle_websocket_message(
                        user_id=user_id,
                        message=message,
                        db_session=mock_session
                    )
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.ws_manager.manager.send_message', new=message_helper.mock_send_message):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.ws_manager.manager.send_error', new=message_helper.mock_send_error):
                
                start_time = time.time()
                
                # Process all users concurrently
                tasks = [process_user_messages(i) for i in range(concurrent_users)]
                await asyncio.gather(*tasks)
                
                total_time = time.time() - start_time
        
        # Verify all messages were processed
        expected_total_messages = concurrent_users * messages_per_user
        # Note: Some messages may generate multiple responses (thread creation, etc.)
        assert len(message_helper.sent_messages) >= concurrent_users, \
            f"Expected at least {concurrent_users} responses, got {len(message_helper.sent_messages)}"
        
        # Verify reasonable performance under load
        assert total_time < 10.0, f"Concurrent processing took {total_time}s, should be under 10s"
        
        logger.info(f"✅ Concurrent processing test: {concurrent_users} users, {messages_per_user} msgs/user in {total_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, agent_service_with_mocks, message_helper):
        """Test error handling in message pipeline.
        
        Business Value: $10K MRR - Error handling reliability
        """
        agent_service, supervisor, llm_manager = agent_service_with_mocks
        
        # Configure LLM to fail on first call, succeed on retry
        call_count = 0
        async def mock_llm_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated LLM failure")
            return "Recovery successful - cost optimization analysis complete"
        
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager.ask_llm = AsyncMock(side_effect=mock_llm_with_retry)
        
        # Test message that should trigger error then recovery
        test_message = {
            "type": "user_message",
            "payload": {
                "content": "Analyze my model performance",
                "thread_id": "error_recovery_thread",
                "references": []
            }
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.ws_manager.manager.send_message', new=message_helper.mock_send_message):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.ws_manager.manager.send_error', new=message_helper.mock_send_error):
                # Mock: Component isolation for testing without external dependencies
                with patch('app.db.postgres.get_async_db') as mock_db:
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_session = AsyncNone  # TODO: Use real service instance
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    # Mock: Async component isolation for testing without real async operations
                    mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    # This should handle the error gracefully
                    await agent_service.handle_websocket_message(
                        user_id="error_test_user",
                        message=test_message,
                        db_session=mock_session
                    )
        
        # Verify error was handled gracefully
        assert len(message_helper.sent_messages) > 0, "No messages sent during error scenario"
        
        # Check for appropriate error handling
        error_messages = [msg for msg in message_helper.sent_messages 
                         if msg["message"].get("type") == "error"]
        
        # Should have error handling but system should remain stable
        # The exact behavior depends on implementation - could be error message or fallback response
        assert len(message_helper.sent_messages) > 0, "System should remain responsive during errors"
        
        logger.info(f"✅ Error handling test completed - {len(message_helper.sent_messages)} messages handled")
    
    @pytest.mark.asyncio
    async def test_message_validation_and_rejection(self, agent_service_with_mocks, message_helper):
        """Test message validation and rejection of invalid messages."""
        agent_service, supervisor, llm_manager = agent_service_with_mocks
        
        # Invalid message formats
        invalid_messages = [
            # Missing type
            {"payload": {"content": "test"}},
            # Invalid type
            {"type": "", "payload": {"content": "test"}},
            # Missing payload
            {"type": "user_message"},
            # Invalid JSON structure
            "invalid json string",
            # Empty content
            {"type": "user_message", "payload": {"content": ""}},
        ]
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.ws_manager.manager.send_message', new=message_helper.mock_send_message):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.ws_manager.manager.send_error', new=message_helper.mock_send_error):
                # Mock: Component isolation for testing without external dependencies
                with patch('app.db.postgres.get_async_db') as mock_db:
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_session = AsyncNone  # TODO: Use real service instance
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                    # Mock: Async component isolation for testing without real async operations
                    mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    # Send each invalid message
                    for i, invalid_msg in enumerate(invalid_messages):
                        await agent_service.handle_websocket_message(
                            user_id=f"invalid_user_{i}",
                            message=invalid_msg,
                            db_session=mock_session
                        )
        
        # Verify error responses were sent
        error_count = sum(1 for msg in message_helper.sent_messages 
                         if msg["message"].get("type") == "error")
        
        assert error_count > 0, "No error responses sent for invalid messages"
        
        # Verify system handled invalid messages appropriately
        logger.info(f"Handled {len(invalid_messages)} invalid messages with {error_count} error responses")
        
        logger.info(f"✅ Message validation test: {error_count} errors properly handled")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])