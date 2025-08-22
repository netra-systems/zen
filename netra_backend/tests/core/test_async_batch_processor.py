"""
Tests for AsyncBatchProcessor - batch processing functionality
Split from test_async_utils.py for architectural compliance (≤300 lines, ≤8 lines per function)
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio

import pytest

# Add project root to path
from netra_backend.app.core.async_batch_processor import AsyncBatchProcessor
from netra_backend.tests.helpers.async_utils_helpers import (
    assert_batch_results,
    assert_progress_tracking,
    # Add project root to path
    create_dummy_processor,
    create_progress_tracker,
    create_sum_processor,
)


class TestAsyncBatchProcessor:
    """Test AsyncBatchProcessor for batch processing"""
    
    @pytest.fixture
    def batch_processor(self):
        return AsyncBatchProcessor(batch_size=3, max_concurrent_batches=2)
    async def test_process_items_empty_list(self, batch_processor):
        """Test processing empty list"""
        processor = create_dummy_processor()
        results = await batch_processor.process_items([], processor)
        assert results == []
    async def test_process_items_single_batch(self, batch_processor):
        """Test processing single batch"""
        items = [1, 2, 3]
        processor = create_sum_processor()
        results = await batch_processor.process_items(items, processor)
        assert len(results) == 1
        assert results[0] == 6
    async def test_process_items_multiple_batches(self, batch_processor):
        """Test processing multiple batches"""
        items = list(range(1, 8))
        processor = create_sum_processor()
        results = await batch_processor.process_items(items, processor)
        assert_batch_results(results, [6, 15, 7])
    async def test_process_items_with_progress_callback(self, batch_processor):
        """Test processing with progress callback"""
        items = list(range(1, 7))
        progress_calls, progress_callback = create_progress_tracker()
        processor = self._create_length_processor()
        results = await batch_processor.process_items(items, processor, progress_callback)
        assert len(results) == 2
        assert_progress_tracking(progress_calls, [(1, 2), (2, 2)])
    
    def _create_length_processor(self):
        """Create processor that returns batch length"""
        async def processor(batch):
            await asyncio.sleep(0.01)
            return len(batch)
        return processor
    async def test_process_items_handles_exceptions(self, batch_processor):
        """Test that processor exceptions are propagated"""
        items = [1, 2, 3]
        async def failing_processor(batch):
            raise ValueError("Processing failed")
        with pytest.raises(ValueError, match="Processing failed"):
            await batch_processor.process_items(items, failing_processor)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])