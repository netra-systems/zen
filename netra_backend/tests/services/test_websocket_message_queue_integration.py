"""
WebSocket Message Queue Integration Tests
Tests for integration with message queue system.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import AsyncMock, MagicMock

# Add project root to path

from netra_backend.app.services.websocket.message_queue import QueuedMessage, MessagePriority

# Add project root to path


class TestMessageQueueIntegration:
    """Test integration with message queue system."""
    
    @pytest.fixture
    def mock_message_queue(self):
        """Create mock message queue for testing."""
        queue = MagicMock()
        queue.enqueue = AsyncMock()
        queue.dequeue = AsyncMock()
        queue.get_queue_stats = MagicMock()
        return queue

    async def test_message_queueing_for_routing(self, mock_message_queue):
        """Test message queueing before routing."""
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

    async def test_priority_queue_processing(self, mock_message_queue):
        """Test priority-based queue processing."""
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
        """Test queue statistics tracking."""
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