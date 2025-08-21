"""Analysis operations orchestrator for DataSubAgent."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.performance_analyzer import PerformanceAnalyzer
from netra_backend.app.anomaly_detector import AnomalyDetector
from netra_backend.app.correlation_analyzer import CorrelationAnalyzer
from netra_backend.app.usage_pattern_analyzer import UsagePatternAnalyzer


class AnalysisOperations:
    """Orchestrate analysis operations through specialized analyzers."""
    
    def __init__(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any, redis_manager: Any) -> None:
        self.performance_analyzer = PerformanceAnalyzer(query_builder, analysis_engine, clickhouse_ops, redis_manager)
        self.anomaly_detector = AnomalyDetector(query_builder, clickhouse_ops, redis_manager)
        self.correlation_analyzer = CorrelationAnalyzer(query_builder, clickhouse_ops, redis_manager)
        self.usage_pattern_analyzer = UsagePatternAnalyzer(query_builder, clickhouse_ops, redis_manager)
    
    async def analyze_performance_metrics(
        self,
        user_id: int,
        workload_id: Optional[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Delegate performance metrics analysis to specialized analyzer."""
        return await self.performance_analyzer.analyze_performance_metrics(user_id, workload_id, time_range)
    
    async def detect_anomalies(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        z_score_threshold: float = 2.0
    ) -> Dict[str, Any]:
        """Delegate anomaly detection to specialized detector."""
        result = await self.anomaly_detector.detect_anomalies(
            user_id, metric_name, time_range, z_score_threshold
        )
        # Convert AnomalyDetectionResponse to dict for backward compatibility
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        return result
    
    async def analyze_correlations(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Delegate correlation analysis to specialized analyzer."""
        return await self.correlation_analyzer.analyze_correlations(user_id, metrics, time_range)
    
    async def analyze_usage_patterns(
        self,
        user_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Delegate usage pattern analysis to specialized analyzer."""
        return await self.usage_pattern_analyzer.analyze_usage_patterns(user_id, days_back)

