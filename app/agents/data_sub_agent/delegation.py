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
    
    def process_stream(self, dataset, chunk_size: int = 100):
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
    
    async def _analyze_performance_metrics(self, user_id: int, workload_id: str, time_range) -> Dict[str, Any]:
        """Delegate to analysis operations."""
        from .analysis_operations import AnalysisOperations
        ops = AnalysisOperations(
            self.agent.query_builder, self.agent.analysis_engine,
            self.agent.clickhouse_ops, self.agent.redis_manager
        )
        return await ops.analyze_performance_metrics(user_id, workload_id, time_range)
    
    async def _detect_anomalies(self, user_id: int, metric_name: str, time_range, threshold: float = 2.5) -> Dict[str, Any]:
        """Delegate to analysis operations."""
        from .analysis_operations import AnalysisOperations
        ops = AnalysisOperations(
            self.agent.query_builder, self.agent.analysis_engine,
            self.agent.clickhouse_ops, self.agent.redis_manager
        )
        return await ops.detect_anomalies(user_id, metric_name, time_range, threshold)
    
    async def _analyze_usage_patterns(self, user_id: int, days_back: int = 7) -> Dict[str, Any]:
        """Delegate to analysis operations with days_back parameter."""
        from .analysis_operations import AnalysisOperations
        from datetime import datetime, timedelta
        
        # Convert days_back to time_range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        time_range = (start_time, end_time)
        
        ops = AnalysisOperations(
            self.agent.query_builder, self.agent.analysis_engine,
            self.agent.clickhouse_ops, self.agent.redis_manager
        )
        return await ops.analyze_usage_patterns(user_id, time_range)
    
    async def _analyze_correlations(self, user_id: int, metric1: str, metric2: str, time_range) -> Dict[str, Any]:
        """Delegate to analysis operations with individual metric parameters."""
        from .analysis_operations import AnalysisOperations
        
        # Convert individual metrics to list
        metrics = [metric1, metric2]
        
        ops = AnalysisOperations(
            self.agent.query_builder, self.agent.analysis_engine,
            self.agent.clickhouse_ops, self.agent.redis_manager
        )
        return await ops.analyze_correlations(user_id, metrics, time_range)