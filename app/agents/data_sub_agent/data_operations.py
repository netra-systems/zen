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
        self._assign_dependencies(query_builder, analysis_engine, clickhouse_ops, redis_manager)
    
    def _assign_dependencies(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any, redis_manager: Any) -> None:
        """Assign injected dependencies to instance variables."""
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
        return await self._execute_performance_analysis(user_id, workload_id, time_range)

    async def _execute_performance_analysis(
        self,
        user_id: int,
        workload_id: Optional[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Execute the performance analysis workflow."""
        params = self._build_query_params(time_range, user_id, workload_id)
        data = await self._fetch_performance_data(params)
        return self._handle_performance_result(data, time_range, params['aggregation'])
    
    def _build_query_params(self, time_range: Tuple[datetime, datetime], user_id: int, workload_id: Optional[str]) -> Dict[str, Any]:
        """Build query parameters for performance analysis."""
        start_time, end_time = time_range
        aggregation = self._determine_aggregation_level(start_time, end_time)
        return {
            'start_time': start_time, 'end_time': end_time, 'aggregation': aggregation,
            'user_id': user_id, 'workload_id': workload_id
        }
    
    async def _fetch_performance_data(self, params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Fetch performance data using query parameters."""
        query = self._build_performance_query(
            params['user_id'], params['workload_id'], params['start_time'], params['end_time'], params['aggregation']
        )
        cache_key = self._create_cache_key("perf_metrics", params['user_id'], params['workload_id'], params['start_time'], params['end_time'])
        return await self._fetch_cached_data(query, cache_key)
    
    def _handle_performance_result(self, data: Optional[List[Dict[str, Any]]], time_range: Tuple[datetime, datetime], aggregation: str) -> Dict[str, Any]:
        """Handle performance analysis result."""
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
        return await self._execute_anomaly_detection(user_id, metric_name, time_range, z_score_threshold)

    async def _execute_anomaly_detection(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        z_score_threshold: float
    ) -> Dict[str, Any]:
        """Execute anomaly detection workflow."""
        data = await self._fetch_anomaly_data(user_id, metric_name, time_range, z_score_threshold)
        return self._handle_anomaly_result(data, metric_name, z_score_threshold)

    async def _fetch_anomaly_data(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        z_score_threshold: float
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch anomaly data from database."""
        start_time, end_time = time_range
        query = self._build_anomaly_query(user_id, metric_name, start_time, end_time, z_score_threshold)
        cache_key = self._create_anomaly_cache_key(user_id, metric_name, start_time, z_score_threshold)
        return await self._fetch_cached_data(query, cache_key)

    def _handle_anomaly_result(
        self,
        data: Optional[List[Dict[str, Any]]],
        metric_name: str,
        z_score_threshold: float
    ) -> Dict[str, Any]:
        """Handle anomaly detection result."""
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
        return await self._execute_correlation_analysis(user_id, metrics, time_range)

    async def _execute_correlation_analysis(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Execute correlation analysis workflow."""
        validation_error = self._validate_metrics_for_correlation(metrics)
        if validation_error:
            return validation_error
        correlations = await self._compute_all_correlations(user_id, metrics, time_range)
        return self._format_correlation_results(correlations, metrics, time_range)

    def _validate_metrics_for_correlation(self, metrics: List[str]) -> Optional[Dict[str, str]]:
        """Validate metrics list for correlation analysis."""
        if len(metrics) < 2:
            return {"error": "At least 2 metrics required for correlation analysis"}
        return None
    
    async def _compute_all_correlations(
        self, user_id: int, metrics: List[str], time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Compute correlations for all metric pairs."""
        return await self._iterate_metric_correlations(user_id, metrics, time_range)

    async def _iterate_metric_correlations(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Iterate through metrics and compute correlations."""
        start_time, end_time = time_range
        correlations = {}
        return await self._compute_all_metric_pairs(metrics, user_id, start_time, end_time, correlations)

    async def _compute_all_metric_pairs(
        self,
        metrics: List[str],
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        correlations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute correlations for all metric pairs."""
        for i in range(len(metrics)):
            correlations.update(
                await self._compute_metric_correlations(i, metrics, user_id, start_time, end_time)
            )
        return correlations
    
    async def _compute_metric_correlations(
        self, i: int, metrics: List[str], user_id: int, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Compute correlations for a specific metric against later metrics."""
        return await self._process_metric_pairs(i, metrics, user_id, start_time, end_time)

    async def _process_metric_pairs(
        self,
        i: int,
        metrics: List[str],
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Process correlation pairs for a specific metric index."""
        return await self._calculate_index_correlations(i, metrics, user_id, start_time, end_time)

    async def _calculate_index_correlations(
        self,
        i: int,
        metrics: List[str],
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate correlations for specific metric index."""
        correlations = {}
        for j in range(i + 1, len(metrics)):
            pair_correlation = await self._compute_single_pair_correlation(i, j, metrics, user_id, start_time, end_time)
            correlations.update(pair_correlation)
        return correlations

    async def _compute_single_pair_correlation(
        self,
        i: int,
        j: int,
        metrics: List[str],
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Compute correlation for a single metric pair."""
        return await self._calculate_metric_pair_correlation(i, j, metrics, user_id, start_time, end_time)

    async def _calculate_metric_pair_correlation(
        self,
        i: int,
        j: int,
        metrics: List[str],
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate correlation for metric pair at indices i, j."""
        metric1, metric2 = metrics[i], metrics[j]
        correlation = await self._calculate_pairwise_correlation(user_id, metric1, metric2, start_time, end_time)
        return self._format_pair_correlation_result(metric1, metric2, correlation)

    def _format_pair_correlation_result(self, metric1: str, metric2: str, correlation: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Format correlation result for metric pair."""
        if correlation:
            return {f"{metric1}_vs_{metric2}": correlation}
        return {}
    
    async def analyze_usage_patterns(
        self,
        user_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Analyze usage patterns over time."""
        return await self._execute_usage_analysis(user_id, days_back)

    async def _execute_usage_analysis(self, user_id: int, days_back: int) -> Dict[str, Any]:
        """Execute usage pattern analysis workflow."""
        data = await self._fetch_usage_data(user_id, days_back)
        return self._handle_usage_result(data, days_back)

    async def _fetch_usage_data(self, user_id: int, days_back: int) -> Optional[List[Dict[str, Any]]]:
        """Fetch usage pattern data from database."""
        query = self._build_usage_patterns_query(user_id, days_back)
        cache_key = f"usage_patterns:{user_id}:{days_back}"
        return await self._fetch_cached_data(query, cache_key)

    def _handle_usage_result(
        self,
        data: Optional[List[Dict[str, Any]]],
        days_back: int
    ) -> Dict[str, Any]:
        """Handle usage pattern analysis result."""
        if not data:
            return {"status": "no_data", "message": "No usage data available"}
        return self._process_usage_patterns(data, days_back)
    
    def _determine_aggregation_level(self, start_time: datetime, end_time: datetime) -> str:
        """Determine appropriate aggregation level based on time range."""
        time_diff = self._calculate_time_difference(start_time, end_time)
        return self._select_aggregation_by_duration(time_diff)

    def _calculate_time_difference(self, start_time: datetime, end_time: datetime) -> float:
        """Calculate time difference in seconds."""
        return (end_time - start_time).total_seconds()

    def _select_aggregation_by_duration(self, time_diff: float) -> str:
        """Select aggregation level based on duration."""
        return self._get_aggregation_by_time_threshold(time_diff)

    def _get_aggregation_by_time_threshold(self, time_diff: float) -> str:
        """Get aggregation based on time thresholds."""
        if time_diff <= 3600:  # 1 hour
            return "minute"
        elif time_diff <= 86400:  # 1 day
            return "hour"
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
        return self._delegate_performance_query_build(
            user_id, workload_id, start_time, end_time, aggregation
        )

    def _delegate_performance_query_build(
        self,
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        aggregation: str
    ) -> str:
        """Delegate performance query building to query builder."""
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
        return self._delegate_anomaly_query_build(
            user_id, metric_name, start_time, end_time, z_score_threshold
        )

    def _delegate_anomaly_query_build(
        self,
        user_id: int,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        z_score_threshold: float
    ) -> str:
        """Delegate anomaly query building to query builder."""
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
        return self._build_cache_key_string(prefix, user_id, workload_id, start_time, end_time)

    def _build_cache_key_string(
        self,
        prefix: str,
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """Build cache key string from components."""
        return f"{prefix}:{user_id}:{workload_id}:{start_time.isoformat()}:{end_time.isoformat()}"
    
    def _create_anomaly_cache_key(
        self,
        user_id: int,
        metric_name: str,
        start_time: datetime,
        z_score_threshold: float
    ) -> str:
        """Create cache key for anomaly detection."""
        return self._build_anomaly_cache_string(user_id, metric_name, start_time, z_score_threshold)

    def _build_anomaly_cache_string(
        self,
        user_id: int,
        metric_name: str,
        start_time: datetime,
        z_score_threshold: float
    ) -> str:
        """Build anomaly cache key string."""
        return f"anomalies:{user_id}:{metric_name}:{start_time.isoformat()}:{z_score_threshold}"
    
    async def _fetch_cached_data(self, query: str, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch data with caching support."""
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
    def _create_no_data_response(self, message: str) -> Dict[str, Any]:
        """Create standardized no data response."""
        return {"status": "no_data", "message": message}
    
    def _create_no_anomalies_response(self, metric_name: str, threshold: float) -> Dict[str, Any]:
        """Create no anomalies response."""
        return self._build_no_anomalies_dict(metric_name, threshold)

    def _build_no_anomalies_dict(self, metric_name: str, threshold: float) -> Dict[str, Any]:
        """Build no anomalies response dictionary."""
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
        processor = self._create_performance_processor()
        return self._delegate_performance_processing(processor, data, time_range, aggregation)

    def _create_performance_processor(self):
        """Create performance data processor instance."""
        from .performance_data_processor import PerformanceDataProcessor
        return PerformanceDataProcessor(self.analysis_engine)

    def _delegate_performance_processing(
        self,
        processor,
        data: List[Dict[str, Any]],
        time_range: Tuple[datetime, datetime],
        aggregation: str
    ) -> Dict[str, Any]:
        """Delegate processing to performance processor."""
        return processor.process_performance_data(data, time_range, aggregation)
    
    def _process_anomaly_data(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        z_score_threshold: float
    ) -> Dict[str, Any]:
        """Process anomaly detection data."""
        return self._build_anomaly_response(data, metric_name, z_score_threshold)

    def _build_anomaly_response(
        self,
        data: List[Dict[str, Any]],
        metric_name: str,
        z_score_threshold: float
    ) -> Dict[str, Any]:
        """Build complete anomaly response."""
        base_info = self._build_anomaly_base_info(metric_name, z_score_threshold, len(data))
        anomalies = self._format_anomaly_entries(data)
        return self._merge_anomaly_info(base_info, anomalies)

    def _merge_anomaly_info(self, base_info: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge base info with anomalies list."""
        return {**base_info, "anomalies": anomalies}
    
    def _build_anomaly_base_info(self, metric_name: str, threshold: float, count: int) -> Dict[str, Any]:
        """Build base anomaly information."""
        return self._create_anomaly_base_dict(metric_name, threshold, count)

    def _create_anomaly_base_dict(self, metric_name: str, threshold: float, count: int) -> Dict[str, Any]:
        """Create anomaly base information dictionary."""
        return {
            "status": "anomalies_found",
            "metric": metric_name,
            "threshold": threshold,
            "anomaly_count": count
        }
    
    def _format_anomaly_entries(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format anomaly entries for response."""
        limited_data = data[:50]  # Limit to top 50 anomalies
        return [self._format_single_anomaly(row) for row in limited_data]
    
    def _format_single_anomaly(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Format single anomaly entry."""
        return self._build_anomaly_entry(row)

    def _build_anomaly_entry(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Build formatted anomaly entry."""
        z_score = row['z_score']
        return self._create_anomaly_entry_dict(row, z_score)

    def _create_anomaly_entry_dict(self, row: Dict[str, Any], z_score: float) -> Dict[str, Any]:
        """Create anomaly entry dictionary."""
        return {
            "timestamp": row['timestamp'],
            "value": row['metric_value'],
            "z_score": z_score,
            "severity": self._determine_anomaly_severity(z_score)
        }

    def _determine_anomaly_severity(self, z_score: float) -> str:
        """Determine anomaly severity based on z-score."""
        return "high" if abs(z_score) > 3 else "medium"
    
    async def _calculate_pairwise_correlation(
        self,
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Calculate correlation between two metrics."""
        return await self._execute_pairwise_calculation(user_id, metric1, metric2, start_time, end_time)

    async def _execute_pairwise_calculation(
        self,
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Execute pairwise correlation calculation."""
        data = await self._fetch_correlation_data(user_id, metric1, metric2, start_time, end_time)
        return self._process_correlation_data(data)

    async def _fetch_correlation_data(
        self,
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch correlation data from database."""
        query = self._build_correlation_query(user_id, metric1, metric2, start_time, end_time)
        return await self._fetch_cached_data(query, None)

    def _build_correlation_query(
        self,
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """Build correlation query using query builder."""
        return self.query_builder.build_correlation_analysis_query(
            user_id, metric1, metric2, start_time, end_time
        )

    def _process_correlation_data(self, data: Optional[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        """Process correlation data and format result."""
        if not data or data[0]['sample_size'] <= 10:
            return None
        corr_data = data[0]
        return self._extract_and_format_correlation(corr_data)

    def _extract_and_format_correlation(self, corr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract correlation coefficient and format result."""
        corr_coef = corr_data['correlation_coefficient']
        return self._format_correlation_result(corr_data, corr_coef)
    
    def _format_correlation_result(self, corr_data: Dict[str, Any], corr_coef: float) -> Dict[str, Any]:
        """Format correlation analysis result."""
        base_info = self._build_correlation_base_info(corr_coef, corr_data)
        stats_info = self._build_correlation_stats(corr_data)
        return self._merge_correlation_info(base_info, stats_info)

    def _merge_correlation_info(self, base_info: Dict[str, Any], stats_info: Dict[str, Any]) -> Dict[str, Any]:
        """Merge correlation base and stats info."""
        return {**base_info, **stats_info}
    
    def _build_correlation_base_info(self, corr_coef: float, corr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build base correlation information."""
        return self._create_correlation_base_dict(corr_coef, corr_data)

    def _create_correlation_base_dict(self, corr_coef: float, corr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create correlation base information dictionary."""
        return {
            "coefficient": corr_coef,
            "strength": self._interpret_correlation_strength(corr_coef),
            "direction": "positive" if corr_coef > 0 else "negative",
            "sample_size": corr_data['sample_size']
        }
    
    def _build_correlation_stats(self, corr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build correlation statistics."""
        metric1_stats = self._build_metric_stats(corr_data, 'metric1')
        metric2_stats = self._build_metric_stats(corr_data, 'metric2')
        return self._create_correlation_stats_dict(metric1_stats, metric2_stats)

    def _create_correlation_stats_dict(self, metric1_stats: Dict[str, Any], metric2_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Create correlation statistics dictionary."""
        return {"metric1_stats": metric1_stats, "metric2_stats": metric2_stats}
    
    def _build_metric_stats(self, corr_data: Dict[str, Any], metric_prefix: str) -> Dict[str, Any]:
        """Build stats for a single metric."""
        return self._create_metric_stats_dict(corr_data, metric_prefix)

    def _create_metric_stats_dict(self, corr_data: Dict[str, Any], metric_prefix: str) -> Dict[str, Any]:
        """Create metric statistics dictionary."""
        return {
            "mean": corr_data[f'{metric_prefix}_avg'],
            "std": corr_data[f'{metric_prefix}_std']
        }
    
    def _interpret_correlation_strength(self, coefficient: float) -> str:
        """Interpret correlation coefficient strength."""
        return self._classify_correlation_strength(abs(coefficient))

    def _classify_correlation_strength(self, abs_coefficient: float) -> str:
        """Classify correlation strength by absolute coefficient."""
        return self._get_strength_classification(abs_coefficient)

    def _get_strength_classification(self, abs_coefficient: float) -> str:
        """Get strength classification for coefficient."""
        if abs_coefficient > 0.7:
            return "strong"
        elif abs_coefficient > 0.4:
            return "moderate"
        return "weak"
    
    def _format_correlation_results(
        self,
        correlations: Dict[str, Any],
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Format final correlation analysis results."""
        return self._build_correlation_summary(correlations, metrics, time_range)

    def _build_correlation_summary(
        self,
        correlations: Dict[str, Any],
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Build correlation analysis summary."""
        time_info = self._build_time_range_info(time_range)
        strongest = self._find_strongest_correlation(correlations)
        return self._create_correlation_summary_dict(time_info, metrics, correlations, strongest)

    def _create_correlation_summary_dict(
        self,
        time_info: Dict[str, Any],
        metrics: List[str],
        correlations: Dict[str, Any],
        strongest: Optional[Tuple[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Create correlation summary dictionary."""
        return {
            **time_info,
            "metrics_analyzed": metrics,
            "correlations": correlations,
            "strongest_correlation": strongest
        }
    
    def _build_time_range_info(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Build time range information."""
        return self._create_time_range_dict(time_range)

    def _create_time_range_dict(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Create time range dictionary."""
        start_time, end_time = time_range
        return self._format_time_range_dict(start_time, end_time)

    def _format_time_range_dict(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Format time range into dictionary."""
        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
    
    def _find_strongest_correlation(self, correlations: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Find strongest correlation from results."""
        if not correlations:
            return None
        return self._get_max_correlation(correlations)

    def _get_max_correlation(self, correlations: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Get correlation with maximum coefficient."""
        return max(
            correlations.items(),
            key=lambda x: abs(x[1]['coefficient'])
        )
    
    def _process_usage_patterns(self, data: List[Dict[str, Any]], days_back: int) -> Dict[str, Any]:
        """Process usage patterns data."""
        from .usage_pattern_processor import UsagePatternProcessor
        processor = UsagePatternProcessor()
        return processor.process_patterns(data, days_back)