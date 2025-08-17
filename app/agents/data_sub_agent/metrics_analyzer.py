"""Metrics analysis orchestrator with modular specialized analyzers."""

from typing import Dict, List, Any, Tuple
from datetime import datetime

from app.logging_config import central_logger as logger
from .metric_distribution_analyzer import MetricDistributionAnalyzer
from .metric_trend_analyzer import MetricTrendAnalyzer
from .metric_percentile_analyzer import MetricPercentileAnalyzer
from .metric_comparison_analyzer import MetricComparisonAnalyzer
from .metric_seasonality_analyzer import MetricSeasonalityAnalyzer


class MetricsAnalyzer:
    """Orchestrator for specialized metric analysis operations."""
    
    def __init__(
        self,
        query_builder: Any,
        analysis_engine: Any,
        clickhouse_ops: Any
    ) -> None:
        self._initialize_specialized_analyzers(query_builder, analysis_engine, clickhouse_ops)
    
    def _initialize_specialized_analyzers(
        self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any
    ) -> None:
        """Initialize specialized analyzer modules."""
        self.distribution_analyzer = MetricDistributionAnalyzer(query_builder, analysis_engine, clickhouse_ops)
        self.trend_analyzer = MetricTrendAnalyzer(query_builder, analysis_engine, clickhouse_ops)
        self.percentile_analyzer = MetricPercentileAnalyzer(query_builder, clickhouse_ops)
        self.comparison_analyzer = MetricComparisonAnalyzer(query_builder, clickhouse_ops)
        self.seasonality_analyzer = MetricSeasonalityAnalyzer(query_builder, analysis_engine, clickhouse_ops)
    
    async def analyze_metric_distribution(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Delegate distribution analysis to specialized analyzer."""
        return await self.distribution_analyzer.analyze_metric_distribution(user_id, metric_name, time_range)
    
    async def detect_metric_trends(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Delegate trend detection to specialized analyzer."""
        return await self.trend_analyzer.detect_metric_trends(user_id, metric_name, time_range)
    
    async def calculate_metric_percentiles(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        percentiles: List[float] = [50.0, 75.0, 90.0, 95.0, 99.0]
    ) -> Dict[str, Any]:
        """Delegate percentile calculation to specialized analyzer."""
        return await self.percentile_analyzer.calculate_metric_percentiles(user_id, metric_name, time_range, percentiles)
    
    async def compare_metrics_performance(
        self,
        user_id: int,
        metric_names: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Delegate metrics comparison to specialized analyzer."""
        return await self.comparison_analyzer.compare_metrics_performance(user_id, metric_names, time_range)
    
    async def detect_metric_seasonality(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Delegate seasonality detection to specialized analyzer."""
        return await self.seasonality_analyzer.detect_metric_seasonality(user_id, metric_name, time_range)
