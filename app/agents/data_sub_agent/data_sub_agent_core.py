"""Data Sub Agent Core Components

Core functionality for data analysis operations with modern execution patterns.
Handles reliability management, component initialization, and core analysis logic.

Business Value: Core data analysis engine for customer insights generation.
BVJ: Growth & Enterprise | Data Intelligence Core | +20% performance capture
"""

from typing import Dict, Any, Optional
from datetime import datetime

from app.llm.llm_manager import LLMManager
from app.logging_config import central_logger as logger
from app.agents.base.interface import ExecutionContext
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.schemas.shared_types import RetryConfig
from app.redis_manager import RedisManager
from app.agents.config import agent_config

# Core analysis components
from .query_builder import QueryBuilder
from .analysis_engine import AnalysisEngine
from .clickhouse_operations import DataSubAgentClickHouseOperations
from .extended_operations import ExtendedOperations
from .delegation import AgentDelegation


class DataSubAgentCore:
    """Core components and logic for data analysis operations.
    
    Centralizes initialization and management of core analysis components.
    """
    
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager
        self._init_core_components()
        self._init_redis_connection()
        
    def _init_core_components(self) -> None:
        """Initialize core analysis components."""
        self.query_builder = QueryBuilder()
        self.analysis_engine = AnalysisEngine()
        self.clickhouse_ops = DataSubAgentClickHouseOperations()
        self.cache_ttl = agent_config.cache.default_ttl
        
    def _init_redis_connection(self) -> None:
        """Initialize Redis connection with fallback handling."""
        self.redis_manager: Optional[RedisManager] = None
        try:
            self.redis_manager = RedisManager()
        except Exception as e:
            logger.warning(f"Redis not available for DataSubAgent caching: {e}")
    
    def create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager with default configurations."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        return ReliabilityManager(circuit_config, retry_config)
        
    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration for data operations."""
        return CircuitBreakerConfig(
            name="DataSubAgent",
            failure_threshold=3,
            recovery_timeout=30
        )
        
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration for data operations."""
        return RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )
    
    async def validate_data_analysis_preconditions(self, context: ExecutionContext) -> bool:
        """Validate preconditions for data analysis execution."""
        return self._check_core_dependencies() and self._check_data_access()
        
    def _check_core_dependencies(self) -> bool:
        """Check if core dependencies are available."""
        return all([
            self.query_builder is not None,
            self.analysis_engine is not None,
            self.clickhouse_ops is not None
        ])
        
    def _check_data_access(self) -> bool:
        """Check if data access is available."""
        # Basic data access validation
        return True  # Can be enhanced with actual connectivity checks
    
    async def execute_data_analysis(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core data analysis logic."""
        state = context.state
        analysis_params = self._extract_analysis_params(state)
        
        await context.state.add_message("system", "Starting data analysis...")
        result = await self._perform_analysis(analysis_params, context)
        
        return self._format_analysis_result(result)
        
    def _extract_analysis_params(self, state) -> Dict[str, Any]:
        """Extract analysis parameters from agent state."""
        # Extract key parameters from state for analysis
        params = {
            "user_query": getattr(state, 'user_input', ''),
            "data_source": getattr(state, 'data_source', 'default'),
            "analysis_type": getattr(state, 'analysis_type', 'comprehensive'),
            "time_range": getattr(state, 'time_range', None)
        }
        return params
        
    async def _perform_analysis(self, params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Perform the actual data analysis."""
        try:
            # Build query based on parameters
            query = await self._build_analysis_query(params)
            
            # Execute query and get data
            data = await self._fetch_analysis_data(query)
            
            # Analyze data using analysis engine
            analysis_result = await self._analyze_data(data, params)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Data analysis failed: {e}", exc_info=True)
            return {"error": str(e), "status": "failed"}
    
    async def _build_analysis_query(self, params: Dict[str, Any]) -> str:
        """Build analysis query based on parameters."""
        user_query = params.get("user_query", "")
        analysis_type = params.get("analysis_type", "comprehensive")
        
        # Use query builder to construct appropriate query
        return self.query_builder.build_query(user_query, analysis_type)
    
    async def _fetch_analysis_data(self, query: str) -> Dict[str, Any]:
        """Fetch data using the constructed query."""
        return await self.clickhouse_ops.fetch_data(
            query, None, self.redis_manager, self.cache_ttl
        )
    
    async def _analyze_data(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze fetched data using analysis engine."""
        if not data:
            return {"analysis": "No data available for analysis", "status": "completed"}
            
        # Use analysis engine for data processing
        return await self.analysis_engine.analyze_data(data, params)
    
    def _format_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format analysis result for standardized output."""
        if isinstance(result, dict) and "error" not in result:
            result["timestamp"] = datetime.utcnow().isoformat()
            result["status"] = result.get("status", "completed")
            
        return result
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of core components."""
        return {
            "query_builder": "healthy" if self.query_builder else "unavailable",
            "analysis_engine": "healthy" if self.analysis_engine else "unavailable", 
            "clickhouse_ops": "healthy" if self.clickhouse_ops else "unavailable",
            "redis_manager": "healthy" if self.redis_manager else "unavailable",
            "overall_status": "healthy" if self._check_core_dependencies() else "degraded"
        }