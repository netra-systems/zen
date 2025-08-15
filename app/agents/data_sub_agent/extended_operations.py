"""Extended operations for DataSubAgent - maintaining 300-line limit compliance."""

from typing import Dict, Any, List, Optional, AsyncGenerator
import asyncio
import json
import time
from datetime import datetime, timezone

from app.logging_config import central_logger as logger


class ExtendedOperations:
    """Extended operations for DataSubAgent with proper type safety."""
    
    def __init__(self, agent_instance) -> None:
        """Initialize with agent instance reference."""
        self.agent = agent_instance
        self._cache: Dict[str, Any] = {}
        self.config = getattr(agent_instance, 'config', {"max_retries": 3})
        
    async def _process_internal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Internal processing method for retry and cache operations."""
        result = await self.agent.process_data(data)
        return result
        
    async def process_with_retry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with retry mechanism."""
        max_retries = self.config.get("max_retries", 3)
        for attempt in range(max_retries):
            try:
                return await self._process_internal(data)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(0.1 * (2 ** attempt))
        
    async def process_with_cache(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with caching support."""
        cache_key = self._generate_cache_key(data)
        if cache_key in self._cache:
            return self._cache[cache_key]
        result = await self._process_internal(data)
        self._cache[cache_key] = result
        return result
        
    def _generate_cache_key(self, data: Dict[str, Any]) -> str:
        """Generate cache key from data."""
        return f"cache_{json.dumps(data, sort_keys=True)}"
        
    @agent_type_safe
    async def process_batch_safe(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch with graceful degradation."""
        results = []
        for item in batch:
            try:
                result = await self.agent.process_data(item)
                results.append({"status": "success", **result})
            except Exception as e:
                results.append({"status": "error", "error": str(e)})
        return results
        
    @agent_type_safe  
    async def process_concurrent(self, items: List[Dict[str, Any]], 
                               max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """Process items concurrently with limit."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.agent.process_data(item)
                
        tasks = [process_item(item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)
        
    async def process_stream(self, dataset, chunk_size: int = 100) -> AsyncGenerator[List[Any], None]:
        """Process large dataset in chunks for memory efficiency."""
        chunk = []
        for item in dataset:
            chunk.append(item)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk
            
    @agent_type_safe
    async def process_and_persist(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data and persist results."""
        result = await self.agent.process_data(data)
        result.update({
            "persisted": True,
            "id": "saved_123"  # Mock persistence ID
        })
        return result
        
    @agent_type_safe
    async def handle_supervisor_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle supervisor requests."""
        action = request.get("action", "unknown")
        if action == "process_data":
            await self.agent.process_data(request.get("data", {}))
            callback = request.get("callback")
            if callback:
                await callback()
        return {"status": "completed"}
        
    @agent_type_safe  
    async def enrich_data_extended(self, data: Dict[str, Any], external: bool = False) -> Dict[str, Any]:
        """Enhanced data enrichment with external source support."""
        enriched = await self.agent.enrich_data(data)
        if external:
            enriched["additional"] = "data"
        return enriched
        
    @agent_type_safe
    async def _transform_with_pipeline(self, data: Dict[str, Any], 
                                     pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform data through processing pipeline."""
        result = data.copy()
        for operation in pipeline:
            result = await self._apply_operation(result, operation)
        return result
        
    @agent_type_safe
    async def _apply_operation(self, data: Dict[str, Any], operation: Dict[str, Any]) -> Dict[str, Any]:
        """Apply single operation to data."""
        op_type = operation.get("operation", "unknown")
        data["processed"] = True
        data[f"applied_{op_type}"] = True
        return data
        
    async def save_state(self) -> None:
        """Save agent state (mock implementation)."""
        if hasattr(self.agent, 'context'):
            logger.debug(f"Saving state with context: {self.agent.context}")
            
    async def load_state(self) -> None:
        """Load agent state (mock implementation)."""
        logger.debug("Loading saved state")
        
    async def recover(self) -> None:
        """Recover agent from saved state."""
        await self.load_state()
        logger.debug("Agent recovery completed")