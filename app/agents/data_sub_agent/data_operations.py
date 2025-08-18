"""Data processing operations coordinator with proper type safety."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.logging_config import central_logger as logger
from .performance_analysis import PerformanceAnalysisOperations
from .anomaly_detection import AnomalyDetectionOperations
from .correlation_analysis import CorrelationAnalysisOperations
from .usage_analysis import UsageAnalysisOperations


class DataOperations:
    """Coordinates data processing operations with strong typing."""
    
    def __init__(
        self,
        query_builder: Any,
        analysis_engine: Any,
        clickhouse_ops: Any,
        redis_manager: Any
    ) -> None:
        self._assign_dependencies(query_builder, analysis_engine, clickhouse_ops, redis_manager)
        self._initialize_operation_modules()
    
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