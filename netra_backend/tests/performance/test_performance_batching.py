"""
Performance Tests - Batching and Message Processing
Tests for batch processing and WebSocket message batching functionality.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.performance_optimization_manager import BatchProcessor
from netra_backend.app.websocket_core.batch_message_handler import (
    BatchConfig,
    BatchingStrategy,
    LoadMonitor,
    MessageBatcher,
)

class TestBatchProcessor:
    """Test batch processing functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create batch processor for testing."""
        return BatchProcessor(max_batch_size=5, flush_interval=0.1)
        
    @pytest.mark.asyncio
    async def test_batch_size_flushing(self, processor):
        """Test batch flushing when size limit is reached."""
        processed_batches = []
        
        async def batch_processor(batch):
            processed_batches.append(batch.copy())
        
        # Add items to trigger size-based flush
        for i in range(5):
            await processor.add_to_batch("test_batch", f"item_{i}", batch_processor)
        
        # Wait a moment for processing
        await asyncio.sleep(0.01)
        
        # Should have processed one batch of 5 items
        assert len(processed_batches) == 1
        assert len(processed_batches[0]) == 5
        
    @pytest.mark.asyncio
    async def test_time_based_flushing(self, processor):
        """Test batch flushing based on time interval."""
        processed_batches = []
        
        async def batch_processor(batch):
            processed_batches.append(batch.copy())
        
        # Add fewer items than batch size
        for i in range(3):
            await processor.add_to_batch("test_batch", f"item_{i}", batch_processor)
        
        # Wait for time-based flush
        await asyncio.sleep(0.15)
        
        # Should have processed one batch of 3 items
        assert len(processed_batches) == 1
        assert len(processed_batches[0]) == 3
        
    @pytest.mark.asyncio
    async def test_multiple_batch_keys(self, processor):
        """Test handling multiple batch keys."""
        processed_batches = {"batch1": [], "batch2": []}
        
        async def batch_processor_1(batch):
            processed_batches["batch1"].append(batch.copy())
        
        async def batch_processor_2(batch):
            processed_batches["batch2"].append(batch.copy())
        
        # Add items to different batches
        await processor.add_to_batch("batch1", "item1", batch_processor_1)
        await processor.add_to_batch("batch2", "item2", batch_processor_2)
        await processor.add_to_batch("batch1", "item3", batch_processor_1)
        
        # Flush all batches
        await processor.flush_all()
        
        # Each batch should have been processed separately
        assert len(processed_batches["batch1"]) == 1
        assert len(processed_batches["batch2"]) == 1
        assert len(processed_batches["batch1"][0]) == 2  # item1, item3
        assert len(processed_batches["batch2"][0]) == 1  # item2

class TestMessageBatcher:
    """Test WebSocket message batching."""
    
    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock connection manager."""
        manager = Mock()
        manager.get_user_connections.return_value = [
            Mock(connection_id="conn_1", websocket=AsyncMock()),
            Mock(connection_id="conn_2", websocket=AsyncMock())
        ]
        manager.get_connection_by_id.return_value = Mock(
            websocket=AsyncMock(),
            message_count=0
        )
        return manager
    
    @pytest.fixture
    def batcher(self, mock_connection_manager):
        """Create message batcher for testing."""
        config = BatchConfig(max_batch_size=3, max_wait_time=0.1)
        return MessageBatcher(config, mock_connection_manager)
        
    @pytest.mark.asyncio
    async def test_message_batching_size_trigger(self, batcher, mock_connection_manager):
        """Test message batching triggered by size."""
        # Queue messages
        for i in range(3):
            await batcher.queue_message("user123", {"message": f"test_{i}"})
        
        # Wait for batch processing
        await asyncio.sleep(0.01)
        
        # Should have sent a batch
        conn_mock = mock_connection_manager.get_connection_by_id.return_value
        assert conn_mock.websocket.send_text.called
        
    @pytest.mark.asyncio
    async def test_priority_message_handling(self, batcher, mock_connection_manager):
        """Test high-priority message handling."""
        # Queue high-priority message
        await batcher.queue_message("user123", {"urgent": "data"}, priority=5)
        
        # Wait for processing
        await asyncio.sleep(0.01)
        
        # High-priority messages should be processed quickly
        conn_mock = mock_connection_manager.get_connection_by_id.return_value
        assert conn_mock.websocket.send_text.called
        
    @pytest.mark.asyncio
    async def test_adaptive_batching(self, batcher, mock_connection_manager):
        """Test adaptive batching strategy."""
        batcher.config.strategy = BatchingStrategy.ADAPTIVE
        
        # Simulate high load
        batcher._load_monitor._load_history = [(time.time(), 0.9)]
        
        # Add messages
        for i in range(2):  # Less than max but should trigger due to high load
            await batcher.queue_message("user123", {"message": f"test_{i}"})
        
        await asyncio.sleep(0.01)
        
        # Should have batched due to adaptive strategy
        conn_mock = mock_connection_manager.get_connection_by_id.return_value
        assert conn_mock.websocket.send_text.called

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
