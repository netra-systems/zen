"""Request batching for LLM operations.

Batches multiple requests for efficient processing,
reducing overhead and improving throughput.
"""

import asyncio
from typing import Dict, List


class RequestBatcher:
    """Batches multiple requests for efficient processing."""
    
    def __init__(self, batch_size: int = 5, 
                 batch_timeout: float = 0.1):
        """Initialize request batcher with limits."""
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._pending_requests: List[Dict] = []
        self._lock = asyncio.Lock()
        self._batch_event = asyncio.Event()
    
    async def add_request(self, request: Dict) -> asyncio.Future:
        """Add request to batch and return future."""
        future = asyncio.Future()
        async with self._lock:
            self._add_pending_request(request, future)
            self._check_batch_ready()
        return future
    
    def _add_pending_request(self, request: Dict, future: asyncio.Future) -> None:
        """Add request to pending list."""
        self._pending_requests.append({
            'request': request,
            'future': future
        })
    
    def _check_batch_ready(self) -> None:
        """Check if batch is ready and trigger event."""
        if len(self._pending_requests) >= self.batch_size:
            self._batch_event.set()
    
    async def process_batches(self, processor) -> None:
        """Process batches continuously."""
        while True:
            await self._wait_for_batch()
            batch = await self._get_batch()
            if batch:
                await self._process_batch(batch, processor)
    
    async def _wait_for_batch(self) -> None:
        """Wait for batch to be ready."""
        try:
            await asyncio.wait_for(
                self._batch_event.wait(), 
                timeout=self.batch_timeout
            )
        except asyncio.TimeoutError:
            pass
        self._batch_event.clear()
    
    async def _get_batch(self) -> List[Dict]:
        """Get current batch of requests."""
        async with self._lock:
            batch = self._pending_requests[:self.batch_size]
            self._pending_requests = self._pending_requests[self.batch_size:]
            return batch
    
    async def _process_batch(self, batch: List[Dict], processor) -> None:
        """Process batch of requests."""
        try:
            results = await processor(batch)
            self._set_results(batch, results)
        except Exception as e:
            self._set_errors(batch, e)
    
    def _set_results(self, batch: List[Dict], results: List) -> None:
        """Set results for batch futures."""
        for item, result in zip(batch, results):
            if not item['future'].done():
                item['future'].set_result(result)
    
    def _set_errors(self, batch: List[Dict], error: Exception) -> None:
        """Set error for batch futures."""
        for item in batch:
            if not item['future'].done():
                item['future'].set_exception(error)