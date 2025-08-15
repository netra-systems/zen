"""Delegation methods for DataSubAgent - maintaining 300-line limit compliance."""

from typing import Dict, Any, List
from datetime import datetime, timezone

class AgentDelegation:
    """Delegation methods for DataSubAgent test compatibility."""
    
    def __init__(self, agent_instance, extended_ops) -> None:
        """Initialize with agent and extended operations references."""
        self.agent = agent_instance
        self.extended_ops = extended_ops
    
    async def _process_internal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to extended operations."""
        return await self.extended_ops._process_internal(data)
    
    async def process_with_retry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to extended operations."""
        return await self.extended_ops.process_with_retry(data)
    
    async def process_with_cache(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to extended operations."""
        return await self.extended_ops.process_with_cache(data)
    
    async def process_batch_safe(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Delegate to extended operations."""
        return await self.extended_ops.process_batch_safe(batch)
    
    async def process_concurrent(self, items: List[Dict[str, Any]], max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """Delegate to extended operations."""
        return await self.extended_ops.process_concurrent(items, max_concurrent)
    
    async def process_stream(self, dataset, chunk_size: int = 100):
        """Delegate to extended operations."""
        return self.extended_ops.process_stream(dataset, chunk_size)
    
    async def process_and_persist(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to extended operations."""
        return await self.extended_ops.process_and_persist(data)
    
    async def handle_supervisor_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to extended operations."""
        return await self.extended_ops.handle_supervisor_request(request)
    
    async def enrich_data_external(self, data: Dict[str, Any], external: bool = False) -> Dict[str, Any]:
        """Enhanced data enrichment with external source support."""
        if external:
            return await self.extended_ops.enrich_data_extended(data, external)
        enriched = data.copy()
        enriched["metadata"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": data.get("source", "unknown"),
            "enriched": True
        }
        return enriched
    
    async def _transform_with_pipeline(self, data: Dict[str, Any], pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Delegate to extended operations."""
        return await self.extended_ops._transform_with_pipeline(data, pipeline)
    
    async def _apply_operation(self, data: Dict[str, Any], operation: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to extended operations."""
        return await self.extended_ops._apply_operation(data, operation)
    
    async def save_state(self) -> None:
        """Delegate to extended operations."""
        await self.extended_ops.save_state()
    
    async def load_state(self) -> None:
        """Delegate to extended operations."""
        await self.extended_ops.load_state()
    
    async def recover(self) -> None:
        """Delegate to extended operations."""
        await self.extended_ops.recover()