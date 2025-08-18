"""Batch processing system for efficient bulk operations.

This module provides intelligent batching capabilities for aggregating
operations and processing them efficiently in groups.
"""

import asyncio
from typing import Dict, List, Any, Callable, Optional, Tuple, Union

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class BatchProcessor:
    """Batch processor for efficient bulk operations."""
    
    def __init__(self, max_batch_size: int = 100, flush_interval: float = 1.0):
        self.max_batch_size = max_batch_size
        self.flush_interval = flush_interval
        self._batches: Dict[str, List[Any]] = {}
        self._timers: Dict[str, asyncio.Handle] = {}
        self._processors: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
    
    async def add_to_batch(self, batch_key: str, item: Any, 
                          processor: Callable[[List[Any]], Any]) -> None:
        """Add item to batch for processing."""
        async with self._lock:
            self._initialize_batch_if_needed(batch_key, processor)
            self._batches[batch_key].append(item)
            
            await self._handle_batch_processing(batch_key)
    
    def _initialize_batch_if_needed(self, batch_key: str, processor: Callable) -> None:
        """Initialize batch if it doesn't exist."""
        if batch_key not in self._batches:
            self._batches[batch_key] = []
            self._processors[batch_key] = processor
    
    async def _handle_batch_processing(self, batch_key: str) -> None:
        """Handle batch processing logic."""
        # Cancel existing timer if any
        if batch_key in self._timers:
            self._timers[batch_key].cancel()
        
        # Check if batch is full
        if len(self._batches[batch_key]) >= self.max_batch_size:
            await self._flush_batch(batch_key)
        else:
            self._schedule_timer_flush(batch_key)
    
    def _schedule_timer_flush(self, batch_key: str) -> None:
        """Schedule timer-based batch flush."""
        loop = asyncio.get_event_loop()
        
        def timer_callback():
            if not loop.is_closed():
                asyncio.create_task(self._flush_batch(batch_key))
        
        self._timers[batch_key] = loop.call_later(
            self.flush_interval,
            timer_callback
        )
    
    async def _flush_batch(self, batch_key: str) -> None:
        """Flush a specific batch."""
        batch_data = await self._prepare_batch_for_flush(batch_key)
        if not batch_data:
            return
        
        batch, processor = batch_data
        
        # Process batch outside of lock
        try:
            await processor(batch)
            logger.debug(f"Processed batch {batch_key} with {len(batch)} items")
        except Exception as e:
            logger.error(f"Error processing batch {batch_key}: {e}")
    
    async def _prepare_batch_for_flush(self, batch_key: str) -> Optional[Tuple[List[Any], Callable]]:
        """Prepare batch data for flushing."""
        async with self._lock:
            if batch_key not in self._batches or not self._batches[batch_key]:
                return None
            
            batch = self._batches[batch_key].copy()
            processor = self._processors[batch_key]
            
            # Clear batch and timer
            self._batches[batch_key] = []
            self._cancel_and_remove_timer(batch_key)
            
            return batch, processor
    
    def _cancel_and_remove_timer(self, batch_key: str) -> None:
        """Cancel and remove timer for batch key."""
        if batch_key in self._timers:
            self._timers[batch_key].cancel()
            del self._timers[batch_key]
    
    async def flush_all(self) -> None:
        """Flush all pending batches."""
        batch_keys = list(self._batches.keys())
        for batch_key in batch_keys:
            await self._flush_batch(batch_key)
    
    def get_batch_stats(self) -> Dict[str, Any]:
        """Get batch processing statistics."""
        return {
            "active_batches": len(self._batches),
            "pending_items": sum(len(batch) for batch in self._batches.values()),
            "batch_keys": list(self._batches.keys())
        }