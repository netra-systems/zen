"""Async batch processing utilities for handling large datasets efficiently."""

import asyncio
from typing import Any, Awaitable, Callable, List, TypeVar

T = TypeVar('T')


class AsyncBatchProcessor:
    """Process items in batches asynchronously."""
    
    def __init__(self, batch_size: int = 10, max_concurrent_batches: int = 5):
        self._batch_size = batch_size
        self._semaphore = asyncio.Semaphore(max_concurrent_batches)
    
    async def process_items(
        self,
        items: List[T],
        processor: Callable[[List[T]], Awaitable[Any]],
        progress_callback: Callable[[int, int], None] = None
    ) -> List[Any]:
        """Process items in batches."""
        if not items:
            return []
        
        batches = self._create_batches(items)
        tasks = self._create_batch_tasks(batches, processor, progress_callback)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._validate_results(results)
    
    def _create_batches(self, items: List[T]) -> List[List[T]]:
        """Split items into batches."""
        return [
            items[i:i + self._batch_size] 
            for i in range(0, len(items), self._batch_size)
        ]
    
    def _create_batch_tasks(
        self, 
        batches: List[List[T]], 
        processor: Callable[[List[T]], Awaitable[Any]],
        progress_callback: Callable[[int, int], None]
    ) -> List[asyncio.Task]:
        """Create tasks for processing batches."""
        return [
            asyncio.create_task(self._process_batch(batch, i, len(batches), processor, progress_callback))
            for i, batch in enumerate(batches)
        ]
    
    async def _process_batch(
        self,
        batch_items: List[T],
        batch_index: int,
        total_batches: int,
        processor: Callable[[List[T]], Awaitable[Any]],
        progress_callback: Callable[[int, int], None]
    ) -> Any:
        """Process a single batch."""
        async with self._semaphore:
            result = await processor(batch_items)
            self._report_progress(progress_callback, batch_index, total_batches)
            return result
    
    def _report_progress(
        self, 
        progress_callback: Callable[[int, int], None], 
        batch_index: int, 
        total_batches: int
    ):
        """Report progress if callback provided."""
        if progress_callback:
            progress_callback(batch_index + 1, total_batches)
    
    def _validate_results(self, results: List[Any]) -> List[Any]:
        """Validate results and raise exceptions if any."""
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                raise result
            valid_results.append(result)
        return valid_results
    
    @property
    def batch_size(self) -> int:
        """Get batch size."""
        return self._batch_size
    
    @property
    def max_concurrent_batches(self) -> int:
        """Get maximum concurrent batches."""
        return self._semaphore._value