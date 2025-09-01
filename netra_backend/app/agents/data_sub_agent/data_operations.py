"""Data processing operations coordinator with BaseExecutionInterface modernization.

Modernized with:
- BaseExecutionInterface implementation
- ReliabilityManager integration
- ExecutionMonitor support
- Structured error handling
- Zero breaking changes

Business Value: Enhanced reliability and monitoring for data operations.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.interface import (
    
    ExecutionContext,
    ExecutionResult)
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.data_sub_agent.anomaly_detection import (
    AnomalyDetectionOperations,
)
from netra_backend.app.agents.data_sub_agent.correlation_analysis import (
    CorrelationAnalysisOperations,
)
from netra_backend.app.agents.data_sub_agent.performance_analysis import (
    PerformanceAnalysisOperations,
)
from netra_backend.app.agents.data_sub_agent.usage_analysis import (
    UsageAnalysisOperations,
)
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.shared_types import RetryConfig


class DataOperations:
    """Coordinates data processing operations with modern execution patterns.
    
    Enhanced with:
    - BaseExecutionInterface compliance
    - ReliabilityManager for fault tolerance
    - ExecutionMonitor for performance tracking
    - Structured error handling
    """
    
    def __init__(
        self,
        query_builder: Any,
        analysis_engine: Any,
        clickhouse_ops: Any,
        redis_manager: Any
    ) -> None:
        super().__init__("DataOperations")
        self._assign_dependencies(query_builder, analysis_engine, clickhouse_ops, redis_manager)
        self._initialize_all_components()
    
    def _assign_dependencies(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any, redis_manager: Any) -> None:
        """Assign injected dependencies to instance variables."""
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager

    def _initialize_all_components(self) -> None:
        """Initialize all components including operation modules and modern components."""
        self._initialize_operation_modules()
        self._initialize_modern_components()
        
    def _initialize_operation_modules(self) -> None:
        """Initialize specialized operation modules."""
        self.performance_ops = PerformanceAnalysisOperations(self.query_builder, self.clickhouse_ops, self.redis_manager)
        self.anomaly_ops = AnomalyDetectionOperations(self.query_builder, self.clickhouse_ops, self.redis_manager)
        self.correlation_ops = CorrelationAnalysisOperations(self.query_builder, self.clickhouse_ops, self.redis_manager)
        self.usage_ops = UsageAnalysisOperations(self.query_builder, self.clickhouse_ops, self.redis_manager)
    
    async def analyze_performance_metrics(
        self,
        user_id: int,
        workload_id: Optional[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze performance metrics from ClickHouse."""
        return await self.performance_ops.analyze_performance_metrics(user_id, workload_id, time_range)

    async def detect_anomalies(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        z_score_threshold: float = 2.0
    ) -> Dict[str, Any]:
        """Detect anomalies in metric data."""
        return await self.anomaly_ops.detect_anomalies(user_id, metric_name, time_range, z_score_threshold)

    async def analyze_correlations(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze correlations between multiple metrics."""
        return await self.correlation_ops.analyze_correlations(user_id, metrics, time_range)

    async def analyze_usage_patterns(
        self,
        user_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Analyze usage patterns over time."""
        return await self.usage_ops.analyze_usage_patterns(user_id, days_back)
    
    def _initialize_modern_components(self) -> None:
        """Initialize modern execution components."""
        circuit_config = self._create_circuit_config()
        retry_config = self._create_retry_config()
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        self.execution_monitor = ExecutionMonitor()
    
    def _create_circuit_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            name="DataOperations",
            failure_threshold=5,
            recovery_timeout=60
        )
    
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for data operations."""
        try:
            return await self._check_dependencies_available(context)
        except Exception as e:
            logger.error(f"Precondition validation failed: {e}")
            return False
    
    async def _check_dependencies_available(self, context: ExecutionContext) -> bool:
        """Check if all required dependencies are available."""
        if not self.clickhouse_ops:
            return False
        if not self.query_builder:
            return False
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute data operations core logic with modern patterns."""
        operation_type = self._extract_operation_type(context)
        operation_params = self._extract_operation_params(context)
        
        return await self._execute_operation_by_type(operation_type, operation_params)
    
    def _extract_operation_type(self, context: ExecutionContext) -> str:
        """Extract operation type from execution context."""
        return context.metadata.get("operation_type", "performance_analysis")
    
    def _extract_operation_params(self, context: ExecutionContext) -> Dict[str, Any]:
        """Extract operation parameters from context."""
        return context.metadata.get("operation_params", {})
    
    async def _execute_operation_by_type(self, operation_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific operation based on type."""
        operation_map = self._get_operation_mapping()
        operation_func = operation_map.get(operation_type)
        
        if not operation_func:
            return self._create_unsupported_operation_result(operation_type)
        
        return await operation_func(params)
    
    def _get_operation_mapping(self) -> Dict[str, Any]:
        """Get mapping of operation types to functions."""
        return {
            "performance_analysis": self._execute_performance_analysis,
            "anomaly_detection": self._execute_anomaly_detection,
            "correlation_analysis": self._execute_correlation_analysis,
            "usage_analysis": self._execute_usage_analysis
        }
    
    def _create_unsupported_operation_result(self, operation_type: str) -> Dict[str, Any]:
        """Create result for unsupported operation type."""
        return {
            "status": "error",
            "error": f"Unsupported operation type: {operation_type}"
        }
    
    async def _execute_performance_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute performance analysis operation."""
        user_id = params.get("user_id")
        workload_id = params.get("workload_id")
        time_range = params.get("time_range")
        
        return await self.performance_ops.analyze_performance_metrics(
            user_id, workload_id, time_range
        )
    
    async def _execute_anomaly_detection(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute anomaly detection operation."""
        user_id = params.get("user_id")
        metric_name = params.get("metric_name")
        time_range = params.get("time_range")
        threshold = params.get("z_score_threshold", 2.0)
        
        return await self.anomaly_ops.detect_anomalies(
            user_id, metric_name, time_range, threshold
        )
    
    async def _execute_correlation_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute correlation analysis operation."""
        user_id = params.get("user_id")
        metrics = params.get("metrics", [])
        time_range = params.get("time_range")
        
        return await self.correlation_ops.analyze_correlations(
            user_id, metrics, time_range
        )
    
    async def _execute_usage_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute usage analysis operation."""
        user_id = params.get("user_id")
        days_back = params.get("days_back", 30)
        
        return await self.usage_ops.analyze_usage_patterns(user_id, days_back)
    
    async def execute_with_modern_patterns(self, context: ExecutionContext) -> ExecutionResult:
        """Execute with modern reliability and monitoring patterns."""
        self.execution_monitor.start_execution(context)
        
        async def execute_func() -> ExecutionResult:
            return await self._execute_with_timing(context)
        
        result = await self.reliability_manager.execute_with_reliability(context, execute_func)
        self.execution_monitor.complete_execution(context, result)
        return result
    
    async def _execute_with_timing(self, context: ExecutionContext) -> ExecutionResult:
        """Execute with execution timing tracking."""
        start_time = time.time()
        try:
            result = await self.execute_core_logic(context)
            execution_time = (time.time() - start_time) * 1000
            return self._create_success_execution_result(result, execution_time)
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return self._create_error_execution_result(str(e), execution_time)
    
    def _create_success_execution_result(self, result: Dict[str, Any], execution_time: float) -> ExecutionResult:
        """Create successful execution result."""
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED,
            result=result,
            execution_time_ms=execution_time
        )
    
    def _create_error_execution_result(self, error: str, execution_time: float) -> ExecutionResult:
        """Create error execution result."""
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=error,
            execution_time_ms=execution_time
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        reliability_health = self.reliability_manager.get_health_status()
        monitor_health = self.execution_monitor.get_health_status()
        return self._build_health_status_response(reliability_health, monitor_health)
        
    def _build_health_status_response(self, reliability_health: Dict[str, Any], 
                                    monitor_health: Dict[str, Any]) -> Dict[str, Any]:
        """Build health status response dictionary."""
        return {
            "component": "DataOperations",
            "status": self._determine_overall_health(reliability_health, monitor_health),
            "reliability": reliability_health,
            "monitoring": monitor_health
        }
    
    def _determine_overall_health(self, reliability_health: Dict[str, Any], 
                                monitor_health: Dict[str, Any]) -> str:
        """Determine overall health status."""
        reliability_status = reliability_health.get("overall_health", "degraded")
        monitor_status = monitor_health.get("status", "degraded")
        
        return "healthy" if reliability_status == "healthy" and monitor_status == "healthy" else "degraded"