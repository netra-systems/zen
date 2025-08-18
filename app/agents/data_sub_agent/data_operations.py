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
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.logging_config import central_logger as logger
from app.agents.base.interface import BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.schemas.shared_types import RetryConfig
from .performance_analysis import PerformanceAnalysisOperations
from .anomaly_detection import AnomalyDetectionOperations
from .correlation_analysis import CorrelationAnalysisOperations
from .usage_analysis import UsageAnalysisOperations


class DataOperations(BaseExecutionInterface):
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
        self._initialize_operation_modules()
        self._initialize_modern_components()
    
    def _assign_dependencies(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any, redis_manager: Any) -> None:
        """Assign injected dependencies to instance variables."""
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager

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