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

from app.logging_config import central_logger as logger
from app.agents.state import DeepAgentState

# Modern Base Components
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus,
    WebSocketManagerProtocol
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.schemas.shared_types import RetryConfig

# Helper Modules
from app.agents.data_sub_agent.performance_analysis_helpers import PerformanceAnalysisHelpers
from app.agents.data_sub_agent.performance_analysis_validation import (
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
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager
        self._initialize_execution_engine(reliability_manager)
        self._initialize_helper_components()
    
    def _initialize_execution_engine(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize execution engine with reliability patterns."""
        if not reliability_manager:
            reliability_manager = self._create_default_reliability_manager()
        
        monitor = ExecutionMonitor(max_history_size=1000)
        self.execution_engine = BaseExecutionEngine(reliability_manager, monitor)
        self.monitor = monitor
    
    def _create_default_reliability_manager(self) -> ReliabilityManager:
        """Create default reliability manager with performance analysis optimized settings."""
        circuit_config = CircuitBreakerConfig(
            name="performance_analysis",
            failure_threshold=3,
            recovery_timeout=30
        )
        retry_config = RetryConfig(max_retries=2, base_delay=1.0, max_delay=10.0)
        return ReliabilityManager(circuit_config, retry_config)
    
    def _initialize_helper_components(self) -> None:
        """Initialize helper components for modular architecture."""
        self.helpers = PerformanceAnalysisHelpers(self.analysis_engine)
        self.validator = PerformanceAnalysisValidator(self.clickhouse_ops, self.redis_manager)
        self.query_builder_helper = PerformanceQueryBuilder(self.query_builder)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for performance analysis."""
        try:
            analysis_context = self._extract_analysis_context(context)
            validation_checks = await self.validator.run_validation_checks(
                analysis_context.user_id, analysis_context.workload_id, analysis_context.time_range
            )
            is_valid = all(validation_checks.values())
            await self.validator.log_validation_result(context, is_valid, validation_checks)
            return is_valid
        except Exception as e:
            logger.error(f"Precondition validation failed: {e}", exc_info=True)
            return False
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute performance analysis core logic with modern patterns."""
        analysis_context = self._extract_analysis_context(context)
        await self._track_execution_start(context, analysis_context)
        
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
        state = self.validator.create_legacy_state(user_id, workload_id, time_range)
        context = ExecutionContext(
            run_id=f"legacy_perf_{int(time.time())}",
            agent_name=self.agent_name,
            state=state,
            stream_updates=False
        )
        
        result = await self.execution_engine.execute(self, context)
        return result.result if result.success else self._create_error_response(result)
    
    async def execute_with_modern_patterns(self, state: DeepAgentState, run_id: str,
                                         stream_updates: bool = False) -> ExecutionResult:
        """Execute using modern execution patterns with full orchestration."""
        context = ExecutionContext(
            run_id=run_id,
            agent_name=self.agent_name,
            state=state,
            stream_updates=stream_updates
        )
        
        return await self.execution_engine.execute(self, context)
    
    def _extract_analysis_context(self, context: ExecutionContext) -> PerformanceAnalysisContext:
        """Extract performance analysis context from execution context."""
        state = context.state
        user_id = getattr(state, 'user_id', 0)
        
        # Extract from metadata or state
        workload_id = context.metadata.get('workload_id') if context.metadata else None
        time_range = context.metadata.get('time_range') if context.metadata else None
        
        if not time_range:
            # Default time range: last 24 hours
            end_time = datetime.utcnow()
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            time_range = (start_time, end_time)
        
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
        aggregation = self.query_builder_helper.determine_aggregation_level(start_time, end_time)
        query = self.query_builder_helper.build_performance_query(
            analysis_context.user_id, analysis_context.workload_id, 
            start_time, end_time, aggregation
        )
        cache_key = self.query_builder_helper.build_cache_key(
            analysis_context.user_id, analysis_context.workload_id, 
            start_time, end_time
        )
        
        await self.send_status_update(context, "fetching_data", "Fetching performance metrics")
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
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
        metrics = {
            "user_id": analysis_context.user_id,
            "workload_id": analysis_context.workload_id,
            "data_points": len(result.get("raw_data", [])),
            "time_range_hours": self.validator.calculate_time_range_hours(analysis_context.time_range),
            "analysis_success": True
        }
        context.metadata.update(metrics)
    
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
        base_status = {
            "agent_name": self.agent_name,
            "execution_engine": self.execution_engine.get_health_status(),
            "monitor": self.monitor.get_health_status()
        }
        
        performance_status = PerformanceErrorHandlers.get_performance_components_health()
        return {**base_status, **performance_status}


# Legacy alias for backward compatibility
PerformanceAnalyzer = ModernPerformanceAnalyzer