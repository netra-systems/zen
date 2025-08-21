"""Modern Performance Analyzer with BaseExecutionInterface

Modernized performance metrics analysis with:
- BaseExecutionInterface integration
- Reliability patterns and error handling
- Performance monitoring
- Circuit breaker protection
- Standardized execution patterns

Business Value: Standardizes performance analysis execution.
BVJ: Growth & Enterprise | Increase Reliability | +10% system uptime
"""

import time
from typing import Dict, List, Any, Tuple, Optional, Protocol
from datetime import datetime
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.agents.state import DeepAgentState

# Modern Base Components
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus,
    WebSocketManagerProtocol
)
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.schemas.shared_types import RetryConfig

# Helper Modules
from netra_backend.app.agents.data_sub_agent.performance_analysis_helpers import PerformanceAnalysisHelpers
from netra_backend.app.agents.data_sub_agent.performance_analysis_validation import (
    PerformanceAnalysisValidator, PerformanceQueryBuilder, PerformanceErrorHandlers
)


@dataclass
class PerformanceAnalysisContext:
    """Context for performance analysis operations."""
    user_id: int
    workload_id: Optional[str]
    time_range: Tuple[datetime, datetime]
    aggregation_level: Optional[str] = None
    requires_caching: bool = True
    

class ModernPerformanceAnalyzer(BaseExecutionInterface):
    """Modern performance analyzer with standardized execution patterns.
    
    Provides reliable performance metrics analysis with:
    - Circuit breaker protection for external services
    - Retry logic for transient failures  
    - Comprehensive monitoring and metrics
    - Standardized error handling and recovery
    """
    
    def __init__(self, query_builder: Any, analysis_engine: Any, 
                 clickhouse_ops: Any, redis_manager: Any,
                 websocket_manager: Optional[WebSocketManagerProtocol] = None,
                 reliability_manager: Optional[ReliabilityManager] = None):
        super().__init__("ModernPerformanceAnalyzer", websocket_manager)
        self._set_core_dependencies(query_builder, analysis_engine, clickhouse_ops, redis_manager)
        self._initialize_execution_engine(reliability_manager)
        self._initialize_helper_components()
    
    def _set_core_dependencies(self, query_builder: Any, analysis_engine: Any,
                              clickhouse_ops: Any, redis_manager: Any) -> None:
        """Set core dependencies for the analyzer."""
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager
    
    def _initialize_execution_engine(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize execution engine with reliability patterns."""
        if not reliability_manager:
            reliability_manager = self._create_default_reliability_manager()
        
        monitor = ExecutionMonitor(max_history_size=1000)
        self.execution_engine = BaseExecutionEngine(reliability_manager, monitor)
        self.monitor = monitor
    
    def _create_default_reliability_manager(self) -> ReliabilityManager:
        """Create default reliability manager with performance analysis optimized settings."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        return ReliabilityManager(circuit_config, retry_config)
    
    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            name="performance_analysis",
            failure_threshold=3,
            recovery_timeout=30
        )
    
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(max_retries=2, base_delay=1.0, max_delay=10.0)
    
    def _initialize_helper_components(self) -> None:
        """Initialize helper components for modular architecture."""
        self.helpers = PerformanceAnalysisHelpers(self.analysis_engine)
        self.validator = PerformanceAnalysisValidator(self.clickhouse_ops, self.redis_manager)
        self.query_builder_helper = PerformanceQueryBuilder(self.query_builder)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for performance analysis."""
        try:
            return await self._perform_validation_workflow(context)
        except Exception as e:
            return self._handle_validation_error(e)
    
    async def _perform_validation_workflow(self, context: ExecutionContext) -> bool:
        """Perform the validation workflow."""
        analysis_context = self._extract_analysis_context(context)
        validation_checks = await self._run_validation_checks(analysis_context)
        is_valid = all(validation_checks.values())
        await self.validator.log_validation_result(context, is_valid, validation_checks)
        return is_valid
    
    async def _run_validation_checks(self, analysis_context) -> Dict[str, bool]:
        """Run validation checks for analysis context."""
        return await self.validator.run_validation_checks(
            analysis_context.user_id, analysis_context.workload_id, analysis_context.time_range
        )
    
    def _handle_validation_error(self, error: Exception) -> bool:
        """Handle validation error and return False."""
        logger.error(f"Precondition validation failed: {error}", exc_info=True)
        return False
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute performance analysis core logic with modern patterns."""
        analysis_context = self._extract_analysis_context(context)
        await self._track_execution_start(context, analysis_context)
        return await self._execute_with_error_handling(context, analysis_context)
    
    async def _execute_with_error_handling(self, context: ExecutionContext,
                                          analysis_context: PerformanceAnalysisContext) -> Dict[str, Any]:
        """Execute analysis workflow with error handling."""
        try:
            result = await self._execute_analysis_workflow(context, analysis_context)
            return await self._finalize_successful_execution(context, result)
        except Exception as e:
            return await self._handle_execution_error(context, e)
    
    async def analyze_performance_metrics(
        self, user_id: int, workload_id: Optional[str], 
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Legacy interface for backward compatibility."""
        context = self._create_legacy_context(user_id, workload_id, time_range)
        result = await self.execution_engine.execute(self, context)
        return self._process_legacy_result(result)
    
    def _create_legacy_context(self, user_id: int, workload_id: Optional[str],
                              time_range: Tuple[datetime, datetime]) -> ExecutionContext:
        """Create execution context for legacy interface."""
        state = self.validator.create_legacy_state(user_id, workload_id, time_range)
        return self._create_legacy_execution_context(state)
    
    def _create_legacy_execution_context(self, state) -> ExecutionContext:
        """Create execution context for legacy interface."""
        return ExecutionContext(
            run_id=f"legacy_perf_{int(time.time())}",
            agent_name=self.agent_name,
            state=state,
            stream_updates=False
        )
    
    def _process_legacy_result(self, result) -> Dict[str, Any]:
        """Process result from legacy execution."""
        return result.result if result.success else self._create_error_response(result)
    
    async def execute_with_modern_patterns(self, state: DeepAgentState, run_id: str,
                                         stream_updates: bool = False) -> ExecutionResult:
        """Execute using modern execution patterns with full orchestration."""
        context = self._create_modern_context(state, run_id, stream_updates)
        return await self.execution_engine.execute(self, context)
    
    def _create_modern_context(self, state: DeepAgentState, run_id: str,
                              stream_updates: bool) -> ExecutionContext:
        """Create execution context for modern patterns."""
        context_params = self._build_modern_context_params(run_id, state, stream_updates)
        return ExecutionContext(**context_params)
    
    def _build_modern_context_params(self, run_id: str, state: DeepAgentState,
                                    stream_updates: bool) -> Dict[str, Any]:
        """Build parameters for modern execution context."""
        return {
            "run_id": run_id, "agent_name": self.agent_name,
            "state": state, "stream_updates": stream_updates
        }
    
    def _extract_analysis_context(self, context: ExecutionContext) -> PerformanceAnalysisContext:
        """Extract performance analysis context from execution context."""
        state = context.state
        user_id = getattr(state, 'user_id', 0)
        workload_id, time_range = self._extract_metadata_params(context)
        if not time_range:
            time_range = self._create_default_time_range()
        return self._build_analysis_context(user_id, workload_id, time_range)
    
    def _extract_metadata_params(self, context: ExecutionContext) -> Tuple[Optional[str], Optional[Tuple]]:
        """Extract workload_id and time_range from metadata."""
        if not context.metadata:
            return None, None
        workload_id = context.metadata.get('workload_id')
        time_range = context.metadata.get('time_range')
        return workload_id, time_range
    
    def _create_default_time_range(self) -> Tuple[datetime, datetime]:
        """Create default time range for last 24 hours."""
        end_time = datetime.utcnow()
        start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        return (start_time, end_time)
    
    def _build_analysis_context(self, user_id: int, workload_id: Optional[str], 
                               time_range: Tuple[datetime, datetime]) -> PerformanceAnalysisContext:
        """Build PerformanceAnalysisContext from extracted parameters."""
        return PerformanceAnalysisContext(
            user_id=user_id,
            workload_id=workload_id,
            time_range=time_range
        )
    
    async def _track_execution_start(self, context: ExecutionContext,
                                   analysis_context: PerformanceAnalysisContext) -> None:
        """Track execution start with monitoring integration."""
        self.monitor.start_execution(context)
        await self.send_status_update(context, "initializing", "Preparing performance analysis")
        start_time, end_time = analysis_context.time_range
        logger.info(f"Starting performance analysis for user {analysis_context.user_id}, "
                   f"time range: {start_time} to {end_time}")
    
    async def _execute_analysis_workflow(self, context: ExecutionContext,
                                       analysis_context: PerformanceAnalysisContext) -> Dict[str, Any]:
        """Execute analysis workflow with enhanced monitoring."""
        data = await self._fetch_metrics_data_with_monitoring(analysis_context, context)
        return await self._process_fetched_data(context, data, analysis_context)
    
    async def _process_fetched_data(self, context: ExecutionContext, data: Optional[List[Dict]],
                                   analysis_context: PerformanceAnalysisContext) -> Dict[str, Any]:
        """Process fetched data and create analysis result."""
        if not data:
            return PerformanceErrorHandlers.create_no_data_response()
        result = self._analyze_metrics_data_comprehensive(data, analysis_context.time_range)
        self._record_analysis_metrics(context, result, analysis_context)
        return result
    
    async def _finalize_successful_execution(self, context: ExecutionContext,
                                           result: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize successful execution with metrics tracking."""
        await self.send_status_update(context, "completed", "Performance analysis completed")
        logger.info(f"Performance analysis completed successfully for {context.run_id}")
        return result
    
    async def _handle_execution_error(self, context: ExecutionContext, error: Exception) -> Dict[str, Any]:
        """Handle execution errors with comprehensive error tracking."""
        self.monitor.record_error(context, error)
        error_result = PerformanceErrorHandlers.create_error_response_from_exception(error)
        await self.send_status_update(context, "failed", f"Analysis failed: {str(error)}")
        logger.error(f"Performance analysis failed for {context.run_id}: {error}", exc_info=True)
        return error_result
    
    async def _fetch_metrics_data_with_monitoring(self, analysis_context: PerformanceAnalysisContext,
                                                context: ExecutionContext) -> Optional[List[Dict]]:
        """Fetch metrics data with enhanced monitoring and error handling."""
        start_time, end_time = analysis_context.time_range
        query_params = self._build_query_parameters(analysis_context, start_time, end_time)
        return await self._execute_data_fetch(context, query_params)
    
    async def _execute_data_fetch(self, context: ExecutionContext, query_params: Dict[str, str]) -> Optional[List[Dict]]:
        """Execute data fetch with status update."""
        await self.send_status_update(context, "fetching_data", "Fetching performance metrics")
        return await self.clickhouse_ops.fetch_data(
            query_params['query'], query_params['cache_key'], self.redis_manager
        )
    
    def _build_query_parameters(self, analysis_context: PerformanceAnalysisContext,
                               start_time: datetime, end_time: datetime) -> Dict[str, str]:
        """Build query and cache key parameters."""
        aggregation = self.query_builder_helper.determine_aggregation_level(start_time, end_time)
        query = self._build_performance_query(analysis_context, start_time, end_time, aggregation)
        cache_key = self._build_cache_key(analysis_context, start_time, end_time)
        return {'query': query, 'cache_key': cache_key}
    
    def _build_performance_query(self, analysis_context: PerformanceAnalysisContext,
                                start_time: datetime, end_time: datetime, aggregation: str) -> str:
        """Build performance query."""
        return self.query_builder_helper.build_performance_query(
            analysis_context.user_id, analysis_context.workload_id, 
            start_time, end_time, aggregation
        )
    
    def _build_cache_key(self, analysis_context: PerformanceAnalysisContext,
                        start_time: datetime, end_time: datetime) -> str:
        """Build cache key for query."""
        return self.query_builder_helper.build_cache_key(
            analysis_context.user_id, analysis_context.workload_id, 
            start_time, end_time
        )
    
    def _analyze_metrics_data_comprehensive(self, data: List[Dict], time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Analyze metrics data with comprehensive analysis components."""
        metric_values = self.helpers.extract_metric_values(data)
        result = self.helpers.build_base_result(time_range, data, metric_values)
        self._add_all_analysis_components(result, data, metric_values)
        return result
    
    def _add_all_analysis_components(self, result: Dict, data: List[Dict], metric_values: Dict) -> None:
        """Add all analysis components to result."""
        self.helpers.add_trend_analysis(result, data, metric_values)
        self.helpers.add_seasonality_analysis(result, data, metric_values)
        self.helpers.add_outlier_analysis(result, data, metric_values)
    
    def _record_analysis_metrics(self, context: ExecutionContext, result: Dict[str, Any],
                               analysis_context: PerformanceAnalysisContext) -> None:
        """Record analysis-specific metrics for performance tracking."""
        metrics = self._build_analysis_metrics(result, analysis_context)
        context.metadata.update(metrics)
    
    def _build_analysis_metrics(self, result: Dict[str, Any],
                               analysis_context: PerformanceAnalysisContext) -> Dict[str, Any]:
        """Build metrics dictionary for analysis tracking."""
        base_metrics = self._create_base_metrics(analysis_context)
        performance_metrics = self._create_performance_metrics(result, analysis_context)
        return {**base_metrics, **performance_metrics}
    
    def _create_base_metrics(self, analysis_context: PerformanceAnalysisContext) -> Dict[str, Any]:
        """Create base metrics from analysis context."""
        return {
            "user_id": analysis_context.user_id,
            "workload_id": analysis_context.workload_id,
            "analysis_success": True
        }
    
    def _create_performance_metrics(self, result: Dict[str, Any],
                                   analysis_context: PerformanceAnalysisContext) -> Dict[str, Any]:
        """Create performance-related metrics."""
        return {
            "data_points": len(result.get("raw_data", [])),
            "time_range_hours": self.validator.calculate_time_range_hours(analysis_context.time_range)
        }
    
    def _create_error_response(self, result: ExecutionResult) -> Dict[str, Any]:
        """Create error response from execution result."""
        return {
            "status": "error",
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
            "retry_count": result.retry_count
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including all components."""
        base_status = self._get_base_health_status()
        performance_status = PerformanceErrorHandlers.get_performance_components_health()
        return {**base_status, **performance_status}
    
    def _get_base_health_status(self) -> Dict[str, Any]:
        """Get base health status for core components."""
        return {
            "agent_name": self.agent_name,
            "execution_engine": self.execution_engine.get_health_status(),
            "monitor": self.monitor.get_health_status()
        }


# Legacy alias for backward compatibility
PerformanceAnalyzer = ModernPerformanceAnalyzer