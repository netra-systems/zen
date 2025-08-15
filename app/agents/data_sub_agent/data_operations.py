"""Data processing operations coordinator with proper type safety."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.logging_config import central_logger as logger


class DataOperations:
    """Coordinates data processing operations with strong typing."""
    
    def __init__(
        self,
        query_builder: Any,
        analysis_engine: Any,
        clickhouse_ops: Any,
        redis_manager: Any
    ) -> None:
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager
    
    async def analyze_performance_metrics(
        self,
        user_id: int,
        workload_id: Optional[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze performance metrics from ClickHouse."""
        start_time, end_time = time_range
        aggregation = self._determine_aggregation_level(start_time, end_time)
        
        query = self._build_performance_query(user_id, workload_id, start_time, end_time, aggregation)
        cache_key = self._create_cache_key("perf_metrics", user_id, workload_id, start_time, end_time)
        data = await self._fetch_cached_data(query, cache_key)
        
        if not data:
            return self._create_no_data_response("No performance metrics found")
        
        return self._process_performance_data(data, time_range, aggregation)
    
    async def detect_anomalies(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        z_score_threshold: float = 2.0
    ) -> Dict[str, Any]:
        """Detect anomalies in metric data."""
        start_time, end_time = time_range
        
        query = self._build_anomaly_query(user_id, metric_name, start_time, end_time, z_score_threshold)
        cache_key = self._create_anomaly_cache_key(user_id, metric_name, start_time, z_score_threshold)
        data = await self._fetch_cached_data(query, cache_key)
        
        if not data:
            return self._create_no_anomalies_response(metric_name, z_score_threshold)
        
        return self._process_anomaly_data(data, metric_name, z_score_threshold)
    
    async def analyze_correlations(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze correlations between multiple metrics."""
        if len(metrics) < 2:
            return {"error": "At least 2 metrics required for correlation analysis"}
        
        start_time, end_time = time_range
        correlations = {}
        
        for i in range(len(metrics)):
            for j in range(i + 1, len(metrics)):
                metric1, metric2 = metrics[i], metrics[j]
                correlation = await self._calculate_pairwise_correlation(
                    user_id, metric1, metric2, start_time, end_time
                )
                if correlation:
                    correlations[f"{metric1}_vs_{metric2}"] = correlation
        
        return self._format_correlation_results(correlations, metrics, time_range)
    
    async def analyze_usage_patterns(
        self,
        user_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Analyze usage patterns over time."""
        query = self._build_usage_patterns_query(user_id, days_back)
        cache_key = f"usage_patterns:{user_id}:{days_back}"
        data = await self._fetch_cached_data(query, cache_key)
        
        if not data:
            return {"status": "no_data", "message": "No usage data available"}
        
        return self._process_usage_patterns(data, days_back)
    
    def _determine_aggregation_level(self, start_time: datetime, end_time: datetime) -> str:
        """Determine appropriate aggregation level based on time range."""
        time_diff = (end_time - start_time).total_seconds()
        if time_diff <= 3600:  # 1 hour
            return "minute"
        elif time_diff <= 86400:  # 1 day
            return "hour"
        else:
            return "day"
    
    def _build_performance_query(
        self,
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        aggregation: str
    ) -> str:
        """Build performance metrics query."""
        return self.query_builder.build_performance_metrics_query(
            user_id, workload_id, start_time, end_time, aggregation
        )
    
    def _build_anomaly_query(
        self,
        user_id: int,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        z_score_threshold: float
    ) -> str:
        """Build anomaly detection query."""
        return self.query_builder.build_anomaly_detection_query(
            user_id, metric_name, start_time, end_time, z_score_threshold
        )
    
    def _build_usage_patterns_query(self, user_id: int, days_back: int) -> str:
        """Build usage patterns query."""
        return self.query_builder.build_usage_patterns_query(user_id, days_back)
    
    def _create_cache_key(
        self,
        prefix: str,
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """Create cache key for query results."""
        return f"{prefix}:{user_id}:{workload_id}:{start_time.isoformat()}:{end_time.isoformat()}"
    
    def _create_anomaly_cache_key(
        self,
        user_id: int,
        metric_name: str,
        start_time: datetime,
        z_score_threshold: float
    ) -> str:
        """Create cache key for anomaly detection."""
        return f"anomalies:{user_id}:{metric_name}:{start_time.isoformat()}:{z_score_threshold}"
    
    async def _fetch_cached_data(self, query: str, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch data with caching support."""
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
    def _create_no_data_response(self, message: str) -> Dict[str, Any]:
        """Create standardized no data response."""
        return {"status": "no_data", "message": message}
    
    def _create_no_anomalies_response(self, metric_name: str, threshold: float) -> Dict[str, Any]:
        """Create no anomalies response."""
        return {
            "status": "no_anomalies",
            "message": f"No anomalies detected for {metric_name}",
            "threshold": threshold
        }
    
    def _process_performance_data(
        self,
        data: List[Dict[str, Any]],
        time_range: Tuple[datetime, datetime],
        aggregation: str
    ) -> Dict[str, Any]:
        """Process performance metrics data."""
        from .performance_data_processor import PerformanceDataProcessor
        processor = PerformanceDataProcessor(self.analysis_engine)
        return processor.process_performance_data(data, time_range, aggregation)
    
    def _process_anomaly_data(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        z_score_threshold: float
    ) -> Dict[str, Any]:
        """Process anomaly detection data."""
        return {
            "status": "anomalies_found",
            "metric": metric_name,
            "threshold": z_score_threshold,
            "anomaly_count": len(data),
            "anomalies": [
                {
                    "timestamp": row['timestamp'],
                    "value": row['metric_value'],
                    "z_score": row['z_score'],
                    "severity": "high" if abs(row['z_score']) > 3 else "medium"
                }
                for row in data[:50]  # Limit to top 50 anomalies
            ]
        }
    
    async def _calculate_pairwise_correlation(
        self,
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Calculate correlation between two metrics."""
        query = self.query_builder.build_correlation_analysis_query(
            user_id, metric1, metric2, start_time, end_time
        )
        
        data = await self._fetch_cached_data(query, None)
        if not data or data[0]['sample_size'] <= 10:
            return None
        
        corr_data = data[0]
        corr_coef = corr_data['correlation_coefficient']
        
        return self._format_correlation_result(corr_data, corr_coef)
    
    def _format_correlation_result(self, corr_data: Dict[str, Any], corr_coef: float) -> Dict[str, Any]:
        """Format correlation analysis result."""
        strength = self._interpret_correlation_strength(corr_coef)
        
        return {
            "coefficient": corr_coef,
            "strength": strength,
            "direction": "positive" if corr_coef > 0 else "negative",
            "sample_size": corr_data['sample_size'],
            "metric1_stats": {
                "mean": corr_data['metric1_avg'],
                "std": corr_data['metric1_std']
            },
            "metric2_stats": {
                "mean": corr_data['metric2_avg'],
                "std": corr_data['metric2_std']
            }
        }
    
    def _interpret_correlation_strength(self, coefficient: float) -> str:
        """Interpret correlation coefficient strength."""
        abs_coef = abs(coefficient)
        if abs_coef > 0.7:
            return "strong"
        elif abs_coef > 0.4:
            return "moderate"
        else:
            return "weak"
    
    def _format_correlation_results(
        self,
        correlations: Dict[str, Any],
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Format final correlation analysis results."""
        start_time, end_time = time_range
        
        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "metrics_analyzed": metrics,
            "correlations": correlations,
            "strongest_correlation": max(
                correlations.items(),
                key=lambda x: abs(x[1]['coefficient'])
            ) if correlations else None
        }
    
    def _process_usage_patterns(self, data: List[Dict[str, Any]], days_back: int) -> Dict[str, Any]:
        """Process usage patterns data."""
        from .usage_pattern_processor import UsagePatternProcessor
        processor = UsagePatternProcessor()
        return processor.process_patterns(data, days_back)