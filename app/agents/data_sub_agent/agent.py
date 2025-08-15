"""Refactored DataSubAgent with modular architecture and no test code."""

from typing import Dict, Optional, List, AsyncGenerator, Union, Any
from functools import lru_cache
import json
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.schemas.strict_types import TypedAgentResult
from app.core.type_validators import agent_type_safe
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.config import agent_config
from app.redis_manager import RedisManager
from app.logging_config import central_logger as logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)
from app.agents.input_validation import validate_agent_input

from .query_builder import QueryBuilder
from .analysis_engine import AnalysisEngine
from .clickhouse_operations import ClickHouseOperations
from .execution_engine import ExecutionEngine
from .data_operations import DataOperations
from .metrics_analyzer import MetricsAnalyzer
from .models import DataAnalysisResponse, AnomalyDetectionResponse
from .extended_operations import ExtendedOperations
from .delegation import AgentDelegation


class DataSubAgent(BaseSubAgent):
    """Advanced data gathering and analysis agent with ClickHouse integration."""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher) -> None:
        self._init_base_agent(llm_manager)
        self.tool_dispatcher = tool_dispatcher
        self._init_components()
        self._init_redis()
        self._init_reliability()
        
    def _init_base_agent(self, llm_manager: LLMManager) -> None:
        """Initialize base agent with core parameters."""
        super().__init__(
            llm_manager, 
            name="DataSubAgent", 
            description="Advanced data gathering and analysis agent with ClickHouse integration."
        )
        
    def _init_components(self) -> None:
        """Initialize core components."""
        self.query_builder = QueryBuilder()
        self.analysis_engine = AnalysisEngine()
        self.clickhouse_ops = ClickHouseOperations()
        self.cache_ttl = agent_config.cache.default_ttl
        self.extended_ops = ExtendedOperations(self)
        self.delegation = AgentDelegation(self, self.extended_ops)
        
    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        self.redis_manager: Optional[RedisManager] = None
        try:
            self.redis_manager = RedisManager()
        except Exception as e:
            logger.warning(f"Redis not available for DataSubAgent caching: {e}")
    
    def _init_reliability(self) -> None:
        """Initialize reliability wrapper."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        self.reliability = get_reliability_wrapper("DataSubAgent", circuit_config, retry_config)
        
    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=agent_config.failure_threshold,
            recovery_timeout=agent_config.timeout.recovery_timeout,
            name="DataSubAgent"
        )
        
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(
            max_retries=agent_config.retry.max_retries,
            base_delay=agent_config.retry.base_delay,
            max_delay=agent_config.retry.max_delay
        )
    
    async def _get_cached_schema(self, table_name: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get cached schema information with TTL and cache invalidation."""
        self._ensure_cache_initialized()
        current_time = time.time()
        
        if not force_refresh and self._is_cache_valid(table_name, current_time):
            return self._schema_cache[table_name]
        
        return await self._fetch_and_cache_schema(table_name, current_time)
    
    def _ensure_cache_initialized(self) -> None:
        """Initialize cache dictionaries if they don't exist."""
        if not hasattr(self, '_schema_cache'):
            self._schema_cache: Dict[str, Dict[str, Any]] = {}
            self._schema_cache_timestamps: Dict[str, float] = {}
    
    def _is_cache_valid(self, table_name: str, current_time: float) -> bool:
        """Check if cache entry exists and is still valid."""
        if table_name not in self._schema_cache:
            return False
        
        cache_time = self._schema_cache_timestamps.get(table_name, 0)
        cache_age = current_time - cache_time
        return cache_age < 300  # 5 minutes TTL
    
    async def _fetch_and_cache_schema(self, table_name: str, current_time: float) -> Optional[Dict[str, Any]]:
        """Fetch fresh schema and update cache."""
        schema = await self.clickhouse_ops.get_table_schema(table_name)
        if schema:
            self._update_schema_cache(table_name, schema, current_time)
            await self._cleanup_old_cache_entries(current_time)
        return schema
    
    def _update_schema_cache(self, table_name: str, schema: Dict[str, Any], current_time: float) -> None:
        """Update schema cache with new data."""
        self._schema_cache[table_name] = schema
        self._schema_cache_timestamps[table_name] = current_time
    
    async def _cleanup_old_cache_entries(self, current_time: float) -> None:
        """Clean up old cache entries to prevent memory leaks."""
        max_cache_age = 3600  # 1 hour
        tables_to_remove = self._identify_expired_cache_entries(current_time, max_cache_age)
        self._remove_expired_cache_entries(tables_to_remove)
    
    def _identify_expired_cache_entries(self, current_time: float, max_cache_age: float) -> List[str]:
        """Identify cache entries that have expired."""
        return [
            table_name for table_name, timestamp in self._schema_cache_timestamps.items()
            if current_time - timestamp > max_cache_age
        ]
    
    def _remove_expired_cache_entries(self, tables_to_remove: List[str]) -> None:
        """Remove expired entries from cache."""
        for table_name in tables_to_remove:
            self._schema_cache.pop(table_name, None)
            self._schema_cache_timestamps.pop(table_name, None)
    
    async def invalidate_schema_cache(self, table_name: Optional[str] = None) -> None:
        """Invalidate schema cache for specific table or all tables."""
        if not hasattr(self, '_schema_cache'):
            return
            
        if table_name:
            self._invalidate_single_table_cache(table_name)
        else:
            self._invalidate_all_cache_entries()
    
    def _invalidate_single_table_cache(self, table_name: str) -> None:
        """Invalidate cache for a specific table."""
        self._schema_cache.pop(table_name, None)
        self._schema_cache_timestamps.pop(table_name, None)
    
    def _invalidate_all_cache_entries(self) -> None:
        """Clear entire schema cache."""
        self._schema_cache.clear()
        self._schema_cache_timestamps.clear()
    
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
    
    @validate_agent_input('DataSubAgent')
    @agent_type_safe
    async def execute(self, state: DeepAgentState, run_id: str, 
                     stream_updates: bool = False) -> TypedAgentResult:
        """Execute advanced data analysis with ClickHouse integration."""
        start_time = time.time()
        
        try:
            return await self._execute_with_error_handling(state, run_id, stream_updates, start_time)
        except Exception as e:
            logger.error(f"Data analysis execution failed for run_id {run_id}: {e}")
            return self._create_failure_result(f"Data analysis failed: {e}", start_time)
    
    async def _execute_with_error_handling(
        self, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> TypedAgentResult:
        """Execute data analysis with comprehensive error handling."""
        execution_engine = self._create_execution_engine()
        data_ops, metrics_analyzer = self._create_operation_modules()
        
        await execution_engine.execute_analysis(
            state, run_id, stream_updates, self._send_update, data_ops, metrics_analyzer
        )
        
        data_result = self._ensure_data_result(state.data_result)
        state.data_result = data_result
        return self._create_success_result(start_time, data_result)
    
    def _create_execution_engine(self) -> ExecutionEngine:
        """Create and configure execution engine."""
        return ExecutionEngine(
            self.clickhouse_ops, self.query_builder, self.analysis_engine,
            self.redis_manager, self.llm_manager
        )
    
    def _create_operation_modules(self) -> tuple:
        """Create data operations and metrics analyzer modules."""
        data_ops = DataOperations(
            self.query_builder, self.analysis_engine, self.clickhouse_ops, self.redis_manager
        )
        metrics_analyzer = MetricsAnalyzer(
            self.query_builder, self.analysis_engine, self.clickhouse_ops
        )
        return data_ops, metrics_analyzer
    
    def _ensure_data_result(self, result) -> Union[DataAnalysisResponse, AnomalyDetectionResponse]:
        """Ensure result is a proper data analysis result object."""
        if isinstance(result, (DataAnalysisResponse, AnomalyDetectionResponse)):
            return result
        elif isinstance(result, dict):
            return self._convert_dict_to_result(result)
        else:
            return self._create_fallback_result("Invalid result type")
    
    def _convert_dict_to_result(self, result_dict: dict) -> Union[DataAnalysisResponse, AnomalyDetectionResponse]:
        """Convert dictionary to typed result."""
        try:
            return DataAnalysisResponse(**result_dict)
        except Exception:
            return self._try_anomaly_detection_conversion(result_dict)
    
    def _try_anomaly_detection_conversion(
        self, result_dict: dict
    ) -> Union[AnomalyDetectionResponse, DataAnalysisResponse]:
        """Try converting to AnomalyDetectionResponse, fallback to DataAnalysisResponse."""
        try:
            return AnomalyDetectionResponse(**result_dict)
        except Exception as e:
            logger.warning(f"Failed to convert dict to typed result: {e}")
            return self._create_fallback_result(str(e))
    
    def _create_fallback_result(self, error_message: str) -> DataAnalysisResponse:
        """Create fallback DataAnalysisResponse."""
        return DataAnalysisResponse(
            query="unknown",
            error=error_message
        )
    
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get agent health status."""
        return self.reliability.get_health_status()
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return self.reliability.circuit_breaker.get_status()
    
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Enhanced cleanup with cache management."""
        await super().cleanup(state, run_id)
        
        # Clean up old cache entries during cleanup
        if hasattr(self, '_schema_cache_timestamps'):
            await self._cleanup_old_cache_entries(time.time())

    async def process_and_stream(self, data: Dict[str, Any], websocket) -> None:
        """Process data and stream results via WebSocket for real-time updates."""
        try:
            result = await self.analysis_engine.process_data(data)
            await websocket.send(json.dumps({"type": "data_result", "data": result}))
        except Exception as e:
            await websocket.send(json.dumps({"type": "error", "message": str(e)}))

    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate data has required fields."""
        required_fields = ["input", "type"]
        return all(field in data for field in required_fields)

    async def _transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data and preserve type."""
        result = self._create_base_transform_result(data)
        
        if self._should_parse_json_content(data):
            result["parsed"] = self._safe_json_parse(data["content"])
        
        return result
    
    def _create_base_transform_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create base transformation result structure."""
        return {
            "transformed": True,
            "type": data.get("type", "unknown"),
            "content": data.get("content", ""),
            "original": data
        }
    
    def _should_parse_json_content(self, data: Dict[str, Any]) -> bool:
        """Check if data should be parsed as JSON."""
        return data.get("type") == "json" and "content" in data
    
    def _safe_json_parse(self, content: str) -> Dict[str, Any]:
        """Safely parse JSON content with error handling."""
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {}


    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual data item."""
        return {"status": "processed", "data": data}

    async def process_batch(self, batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch of data items."""
        results = []
        for item in batch_data:
            result = await self.process_data(item)
            results.append(result)
        return results
    
    def __getattr__(self, name: str):
        """Dynamic delegation to extended operations and delegation modules."""
        delegation_methods = self._get_delegation_methods()
        
        if name in delegation_methods and hasattr(self, 'delegation'):
            return self._resolve_delegation_method(name)
        
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
    
    def _get_delegation_methods(self) -> List[str]:
        """Get list of methods that can be delegated."""
        return [
            "_process_internal", "process_with_retry", "process_with_cache",
            "process_batch_safe", "process_concurrent", "process_stream",
            "process_and_persist", "handle_supervisor_request", "enrich_data",
            "_transform_with_pipeline", "_apply_operation", "save_state",
            "load_state", "recover"
        ]
    
    def _resolve_delegation_method(self, name: str):
        """Resolve delegation method from delegation module."""
        if name == "enrich_data":
            return self.delegation.enrich_data_external
        return getattr(self.delegation, name)