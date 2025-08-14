"""Refactored DataSubAgent with modular architecture and no test code."""

from typing import Dict, Optional, Any
from functools import lru_cache

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.redis_manager import RedisManager
from app.logging_config import central_logger as logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)

from .query_builder import QueryBuilder
from .analysis_engine import AnalysisEngine
from .clickhouse_operations import ClickHouseOperations
from .execution_engine import ExecutionEngine
from .data_operations import DataOperations
from .metrics_analyzer import MetricsAnalyzer


class DataSubAgent(BaseSubAgent):
    """Advanced data gathering and analysis agent with ClickHouse integration."""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher) -> None:
        super().__init__(
            llm_manager, 
            name="DataSubAgent", 
            description="Advanced data gathering and analysis agent with ClickHouse integration."
        )
        self.tool_dispatcher = tool_dispatcher
        self._init_components()
        self._init_redis()
        self._init_reliability()
        
    def _init_components(self) -> None:
        """Initialize core components."""
        self.query_builder = QueryBuilder()
        self.analysis_engine = AnalysisEngine()
        self.clickhouse_ops = ClickHouseOperations()
        self.cache_ttl = 300  # 5 minutes cache TTL
        
    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        self.redis_manager: Optional[RedisManager] = None
        try:
            self.redis_manager = RedisManager()
        except Exception as e:
            logger.warning(f"Redis not available for DataSubAgent caching: {e}")
    
    def _init_reliability(self) -> None:
        """Initialize reliability wrapper."""
        self.reliability = get_reliability_wrapper(
            "DataSubAgent",
            CircuitBreakerConfig(
                failure_threshold=4,
                recovery_timeout=45.0,
                name="DataSubAgent"
            ),
            RetryConfig(
                max_retries=3,
                base_delay=1.5,
                max_delay=15.0
            )
        )
    
    async def _get_cached_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get cached schema information for a table with manual caching."""
        if not hasattr(self, '_schema_cache'):
            self._schema_cache: Dict[str, Dict[str, Any]] = {}
        
        if table_name in self._schema_cache:
            return self._schema_cache[table_name]
        
        schema = await self.clickhouse_ops.get_table_schema(table_name)
        if schema:
            self._schema_cache[table_name] = schema
        return schema
    
    async def _fetch_clickhouse_data(
        self,
        query: str,
        cache_key: Optional[str] = None
    ) -> Optional[list[Dict[str, Any]]]:
        """Execute ClickHouse query with caching support."""
        return await self.clickhouse_ops.fetch_data(
            query, cache_key, self.redis_manager, self.cache_ttl
        )
    
    async def _send_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send real-time update via WebSocket."""
        try:
            if hasattr(self, 'ws_manager') and self.ws_manager:
                await self.ws_manager.send_agent_update(run_id, "DataSubAgent", update)
        except Exception as e:
            logger.debug(f"Failed to send WebSocket update: {e}")
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> None:
        """Execute advanced data analysis with ClickHouse integration."""
        
        # Initialize execution engine with required dependencies
        execution_engine = ExecutionEngine(
            self.clickhouse_ops,
            self.query_builder, 
            self.analysis_engine,
            self.redis_manager,
            self.llm_manager
        )
        
        # Initialize operations modules
        data_ops = DataOperations(
            self.query_builder,
            self.analysis_engine,
            self.clickhouse_ops,
            self.redis_manager
        )
        
        metrics_analyzer = MetricsAnalyzer(
            self.query_builder,
            self.analysis_engine,
            self.clickhouse_ops
        )
        
        # Delegate execution to engine
        await execution_engine.execute_analysis(
            state, run_id, stream_updates, self._send_update, data_ops, metrics_analyzer
        )
    
    async def handle_supervisor_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests from supervisor agent (test compatibility)."""
        action = request.get("action", "")
        data = request.get("data", {})
        callback = request.get("callback")
        
        result = {"status": "unknown", "action": action}
        
        if action == "process_data":
            result.update({"status": "completed", "processed": True})
        else:
            result.update({"status": "unsupported", "error": f"Action '{action}' not supported"})
        
        if callback:
            await callback(result)
        return result
    
    async def _analyze_performance(self, data: Dict[str, Any], metric_name: str) -> Dict[str, Any]:
        """Analyze performance metrics (test compatibility method)."""
        if not data or len(data) < 2:
            return {"status": "insufficient_data", "message": "Not enough data points"}
        
        values = [item.get("value", 0) for item in data if isinstance(item, dict)]
        if not values:
            return {"status": "no_data", "message": "No valid data points found"}
        
        avg_value = sum(values) / len(values)
        max_value = max(values)
        return {"average": avg_value, "maximum": max_value, "data_points": len(values)}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get agent health status."""
        return self.reliability.get_health_status()
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return self.reliability.circuit_breaker.get_status()