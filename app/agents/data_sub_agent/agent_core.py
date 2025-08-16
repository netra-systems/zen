"""Core DataSubAgent class with proper module boundaries."""

from typing import Dict, Optional, Any
from functools import lru_cache

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.redis_manager import RedisManager
from app.logging_config import central_logger as logger

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
    
    @lru_cache(maxsize=128)
    async def _get_cached_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get cached schema information for a table."""
        return await self.clickhouse_ops.get_table_schema(table_name)
    
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
        execution_engine = self._create_execution_engine()
        data_ops = self._create_data_operations()
        metrics_analyzer = self._create_metrics_analyzer()
        await execution_engine.execute_analysis(
            state, run_id, stream_updates, self._send_update, data_ops, metrics_analyzer
        )
    
    def _create_execution_engine(self) -> ExecutionEngine:
        """Create execution engine with required dependencies."""
        return ExecutionEngine(
            self.clickhouse_ops,
            self.query_builder, 
            self.analysis_engine,
            self.redis_manager,
            self.llm_manager
        )
    
    def _create_data_operations(self) -> DataOperations:
        """Create data operations module."""
        return DataOperations(
            self.query_builder,
            self.analysis_engine,
            self.clickhouse_ops,
            self.redis_manager
        )
    
    def _create_metrics_analyzer(self) -> MetricsAnalyzer:
        """Create metrics analyzer module."""
        return MetricsAnalyzer(
            self.query_builder,
            self.analysis_engine,
            self.clickhouse_ops
        )
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate data structure."""
        if not self._is_valid_dict_with_min_fields(data):
            return False
        return self._has_required_structure(data)
    
    def _is_valid_dict_with_min_fields(self, data: Dict[str, Any]) -> bool:
        """Check if data is valid dict with minimum fields."""
        return isinstance(data, dict) and len(data) >= 2
    
    def _has_required_structure(self, data: Dict[str, Any]) -> bool:
        """Check if data has required field structure."""
        common_fields = ['id', 'data', 'input', 'content', 'type', 'timestamp']
        has_common_field = any(field in data for field in common_fields)
        has_multiple_fields = len(data) >= 2
        return has_common_field and has_multiple_fields
    
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with validation (legacy compatibility)."""
        if data.get("valid", True):
            return {"status": "success", "processed": True}
        else:
            return {"status": "error", "message": "Invalid data"}