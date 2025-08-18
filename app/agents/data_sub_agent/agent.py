"""Refactored DataSubAgent with modular architecture - main interface."""

from typing import Dict, Optional, List, Any
import time

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
from .clickhouse_operations import DataSubAgentClickHouseOperations
from .extended_operations import ExtendedOperations
from .delegation import AgentDelegation

# Import modular components
from .agent_cache import CacheManager
from .agent_execution import ExecutionManager
from .agent_data_processing import DataProcessor
from .agent_corpus_operations import CorpusOperations
from .agent_anomaly_processing import AnomalyProcessor


class DataSubAgent(BaseSubAgent):
    """Advanced data gathering and analysis agent with ClickHouse integration."""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher) -> None:
        self._init_base_agent(llm_manager)
        self.tool_dispatcher = tool_dispatcher
        self._init_all_components()
        self._setup_cache_wrapper()
        self._init_modular_components()
    
    def _init_all_components(self) -> None:
        """Initialize all agent components."""
        self._init_components()
        self._init_redis()
        self._init_reliability()
    
    def _setup_cache_wrapper(self) -> None:
        """Setup cache wrapper for test compatibility."""
        logger.debug("Cache wrapper setup skipped - not currently required")
        
    def _init_modular_components(self) -> None:
        """Initialize modular component managers."""
        self.cache_manager = CacheManager(self)
        self.execution_manager = ExecutionManager(self)
        self.data_processor = DataProcessor(self)
        self.corpus_operations = CorpusOperations(self)
        self.anomaly_processor = AnomalyProcessor(self)
        
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
        self.clickhouse_ops = DataSubAgentClickHouseOperations()
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
    
    # Cache management delegation
    async def _get_cached_schema(self, table_name: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get cached schema information with TTL and cache invalidation."""
        return await self.cache_manager.get_cached_schema(table_name, force_refresh)
    
    def cache_clear(self) -> None:
        """Clear the schema cache (for test compatibility)."""
        self.cache_manager.cache_clear()
    
    async def invalidate_schema_cache(self, table_name: Optional[str] = None) -> None:
        """Invalidate schema cache for specific table or all tables."""
        await self.cache_manager.invalidate_schema_cache(table_name)
    
    async def _fetch_clickhouse_data(
        self,
        query: str,
        cache_key: Optional[str] = None
    ) -> Optional[list[Dict[str, Any]]]:
        """Execute ClickHouse query with caching support."""
        return await self._execute_clickhouse_query(query, cache_key)
    
    async def _execute_clickhouse_query(self, query: str, cache_key: Optional[str] = None):
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
    
    # Execution delegation
    @validate_agent_input('DataSubAgent')
    @agent_type_safe
    async def execute(self, state: DeepAgentState, run_id: str, 
                     stream_updates: bool = False) -> TypedAgentResult:
        """Execute advanced data analysis with ClickHouse integration."""
        return await self.execution_manager.execute(state, run_id, stream_updates)
    
    # Anomaly processing delegation (used by execution manager)
    def _ensure_data_result(self, result):
        """Ensure result is a proper data analysis result object."""
        return self.execution_manager._ensure_data_result(result)
    
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get agent health status."""
        return self.reliability.get_health_status()
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return self.reliability.circuit_breaker.get_status()
    
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Enhanced cleanup with cache management."""
        await super().cleanup(state, run_id)
        await self.cache_manager.cleanup_old_cache_entries(time.time())

    # Data processing delegation
    async def process_and_stream(self, data: Dict[str, Any], websocket) -> None:
        """Process data and stream results via WebSocket for real-time updates."""
        await self.data_processor.process_and_stream(data, websocket)

    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate data has required fields."""
        return self.data_processor._validate_data(data)

    async def _transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data and preserve type."""
        return await self.data_processor._transform_data(data)

    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual data item."""
        return await self.data_processor.process_data(data)

    async def process_batch(self, batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch of data items."""
        return await self.data_processor.process_batch(batch_data)
    
    def __getattr__(self, name: str):
        """Dynamic delegation to extended operations and delegation modules."""
        delegation_methods = self._get_delegation_methods()
        
        if name in delegation_methods and hasattr(self, 'delegation'):
            return self._resolve_delegation_method(name)
        
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
    
    def _get_delegation_methods(self) -> List[str]:
        """Get list of methods that can be delegated."""
        process_methods = self._get_process_delegation_methods()
        analysis_methods = self._get_analysis_delegation_methods()
        return process_methods + analysis_methods
    
    def _get_process_delegation_methods(self) -> List[str]:
        """Get process-related delegation methods."""
        core_methods = ["_process_internal", "process_with_retry", "process_with_cache"]
        batch_methods = ["process_batch_safe", "process_concurrent", "process_stream"]
        supervisor_methods = ["process_and_persist", "handle_supervisor_request", "enrich_data"]
        return core_methods + batch_methods + supervisor_methods
    
    def _get_analysis_delegation_methods(self) -> List[str]:
        """Get analysis-related delegation methods."""
        pipeline_methods = ["_transform_with_pipeline", "_apply_operation"]
        state_methods = ["save_state", "load_state", "recover"]
        analysis_methods = ["_analyze_performance_metrics", "_detect_anomalies", "_analyze_usage_patterns", "_analyze_correlations"]
        return pipeline_methods + state_methods + analysis_methods
    
    def _resolve_delegation_method(self, name: str):
        """Resolve delegation method from delegation module."""
        if name == "enrich_data":
            return self.delegation.enrich_data_external
        return getattr(self.delegation, name)

    # Corpus operations delegation
    async def analyze_corpus_data(self, corpus_id: str):
        """Analyze data related to a specific corpus."""
        return await self.corpus_operations.analyze_corpus_data(corpus_id)
    
    async def get_corpus_usage_patterns(self, corpus_id: str):
        """Retrieve usage patterns for a specific corpus."""
        return await self.corpus_operations.get_corpus_usage_patterns(corpus_id)
    
    async def detect_corpus_anomalies(self, corpus_id: str):
        """Detect anomalies in corpus usage and performance."""
        return await self.corpus_operations.detect_corpus_anomalies(corpus_id)
    
    async def generate_corpus_insights(self, corpus_id: str) -> Dict[str, Any]:
        """Generate comprehensive insights for a corpus."""
        return await self.corpus_operations.generate_corpus_insights(corpus_id)
    
    # ClickHouse interface provided by _fetch_clickhouse_data above