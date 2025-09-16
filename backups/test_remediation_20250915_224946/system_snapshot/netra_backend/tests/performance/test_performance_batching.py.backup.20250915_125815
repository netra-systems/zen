"""
Performance Tests - Batching Operations
Tests for batch processing and message batching optimizations.
"""

import pytest
import asyncio
from typing import List, Dict, Any
import sys
from pathlib import Path
# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from test_framework.performance import BatchingTestHelper, PerformanceBenchmark
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.performance  # Performance optimization iteration 64
@pytest.mark.fast_test
class TestBatchProcessor:
    """Test batch processing operations - Optimized for performance."""
    
    @pytest.fixture
    def batch_helper(self):
        """Create batch processing helper."""
        return BatchingTestHelper(batch_size=5)
    
    @pytest.mark.asyncio
    async def test_sequential_batch_processing(self, batch_helper):
        """Test sequential batch processing."""
        items = list(range(20))  # 20 items should create 4 batches
        
        results = await batch_helper.process_all_batches(items)
        
        assert len(results) == 4  # 4 batches
        assert batch_helper.processed_items == 20
        
        stats = batch_helper.get_stats()
        assert stats["total_batches"] == 4
        assert stats["avg_batch_size"] == 5.0
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self, batch_helper):
        """Test concurrent batch processing."""
        items = list(range(15))  # 15 items should create 3 batches
        
        results = await batch_helper.process_concurrent_batches(items, max_concurrent=2)
        
        assert len(results) == 3
        assert batch_helper.processed_items == 15
    
    @pytest.mark.asyncio
    async def test_batch_creation(self, batch_helper):
        """Test batch creation logic."""
        items = list(range(12))
        batches = batch_helper.create_batches(items)
        
        assert len(batches) == 3  # 12 items / 5 per batch = 3 batches
        assert len(batches[0]) == 5
        assert len(batches[1]) == 5 
        assert len(batches[2]) == 2  # Remainder


class TestMessageBatcher:
    """Test message batching operations."""
    
    @pytest.fixture
    def message_batcher(self):
        """Create message batcher."""
        return BatchingTestHelper(batch_size=10)
    
    @pytest.mark.asyncio
    async def test_message_batch_performance(self, message_batcher):
        """Test performance of message batching."""
        messages = [{"id": i, "content": f"message_{i}"} for i in range(50)]
        
        benchmark = PerformanceBenchmark("Message Batching")
        
        async def process_messages():
            return await message_batcher.process_all_batches(messages)
        
        metrics = await benchmark.run_load_test(process_messages, concurrent_users=1, operations_per_user=1)
        
        assert metrics.success_count >= 1
        assert metrics.error_rate_percent < 10  # Less than 10% error rate
    
    @pytest.mark.asyncio
    async def test_large_message_batch(self, message_batcher):
        """Test processing large batches of messages."""
        large_messages = [{"id": i, "data": "x" * 100} for i in range(100)]
        
        results = await message_batcher.process_concurrent_batches(large_messages, max_concurrent=3)
        
        assert len(results) == 10  # 100 items / 10 per batch
        assert message_batcher.processed_items == 100
        
        stats = message_batcher.get_stats()
        assert stats["total_batches"] == 10
