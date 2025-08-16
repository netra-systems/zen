"""Analysis operations for DataSubAgent."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

from app.logging_config import central_logger as logger


class AnalysisOperations:
    """Encapsulate analysis operations."""
    
    def __init__(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any, redis_manager: Any) -> None:
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
        data = await self._fetch_metrics_data(user_id, workload_id, time_range)
        if not data:
            return self._create_no_data_response()
        
        metric_values = self._extract_metric_values(data)
        result = self._build_base_result(time_range, data, metric_values)
        self._add_trend_analysis(result, data, metric_values)
        self._add_seasonality_analysis(result, data, metric_values)
        self._add_outlier_analysis(result, data, metric_values)
        return result
    
    async def detect_anomalies(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        z_score_threshold: float = 2.0
    ) -> Dict[str, Any]:
        """Detect anomalies in metric data."""
        data = await self._fetch_anomaly_data(user_id, metric_name, time_range, z_score_threshold)
        if not data:
            return self._create_no_anomalies_response(metric_name, z_score_threshold)
        return self._build_anomalies_response(data, metric_name, z_score_threshold)
    
    async def analyze_correlations(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze correlations between multiple metrics."""
        if len(metrics) < 2:
            return {"error": "At least 2 metrics required for correlation analysis"}
        
        correlations = await self._calculate_pairwise_correlations(user_id, metrics, time_range)
        return self._build_correlation_response(time_range, metrics, correlations)
    
    async def analyze_usage_patterns(
        self,
        user_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Analyze usage patterns over time."""
        data = await self._fetch_usage_data(user_id, days_back)
        if not data:
            return self._create_no_usage_data_response()
        
        patterns = self._aggregate_usage_patterns(data)
        peaks = self._find_peak_usage_times(patterns)
        summary = self._calculate_usage_summary(patterns, days_back, peaks)
        return self._build_usage_response(days_back, summary, patterns)
    
    # Helper methods for analyze_performance_metrics
    async def _fetch_metrics_data(self, user_id: int, workload_id: Optional[str], time_range: Tuple[datetime, datetime]) -> Optional[List[Dict]]:
        """Fetch metrics data from ClickHouse."""
        start_time, end_time = time_range
        aggregation = self._determine_aggregation_level(start_time, end_time)
        query = self.query_builder.build_performance_metrics_query(user_id, workload_id, start_time, end_time, aggregation)
        cache_key = f"perf_metrics:{user_id}:{workload_id}:{start_time.isoformat()}:{end_time.isoformat()}"
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
    def _determine_aggregation_level(self, start_time: datetime, end_time: datetime) -> str:
        """Determine appropriate aggregation level based on time range."""
        time_diff = (end_time - start_time).total_seconds()
        if time_diff <= 3600:
            return "minute"
        elif time_diff <= 86400:
            return "hour"
        return "day"
    
    def _create_no_data_response(self) -> Dict[str, Any]:
        """Create response for no data found."""
        return {
            "status": "no_data",
            "message": "No performance metrics found for the specified criteria"
        }
    
    def _extract_metric_values(self, data: List[Dict]) -> Dict[str, List]:
        """Extract metric values from data for analysis."""
        return {
            "latencies": [row.get('latency_p50', 0) for row in data if row.get('latency_p50')],
            "throughputs": [row.get('avg_throughput', 0) for row in data if row.get('avg_throughput')],
            "error_rates": [row.get('error_rate', 0) for row in data],
            "costs": [row.get('total_cost', 0) for row in data]
        }
    
    def _build_base_result(self, time_range: Tuple[datetime, datetime], data: List[Dict], metric_values: Dict) -> Dict[str, Any]:
        """Build base result structure with time range and statistics."""
        start_time, end_time = time_range
        aggregation = self._determine_aggregation_level(start_time, end_time)
        return {
            "time_range": {"start": start_time.isoformat(), "end": end_time.isoformat(), "aggregation_level": aggregation},
            "summary": self._build_summary_stats(data, metric_values["costs"]),
            "latency": self.analysis_engine.calculate_statistics(metric_values["latencies"]),
            "throughput": self.analysis_engine.calculate_statistics(metric_values["throughputs"]),
            "error_rate": self.analysis_engine.calculate_statistics(metric_values["error_rates"]),
            "raw_data": data[:100]
        }
    
    def _build_summary_stats(self, data: List[Dict], costs: List) -> Dict[str, Any]:
        """Build summary statistics."""
        return {
            "total_events": sum(row.get('event_count', 0) for row in data),
            "unique_workloads": max(row.get('unique_workloads', 0) for row in data),
            "total_cost": sum(costs)
        }
    
    def _add_trend_analysis(self, result: Dict, data: List[Dict], metric_values: Dict) -> None:
        """Add trend analysis if enough data points."""
        if len(data) >= 3:
            timestamps = [datetime.fromisoformat(row['time_bucket']) for row in data]
            result["trends"] = self._build_trend_data(metric_values, timestamps)
    
    def _build_trend_data(self, metric_values: Dict, timestamps: List[datetime]) -> Dict[str, Any]:
        """Build trend analysis data."""
        return {
            "latency": self.analysis_engine.detect_trend(metric_values["latencies"][:len(timestamps)], timestamps),
            "throughput": self.analysis_engine.detect_trend(metric_values["throughputs"][:len(timestamps)], timestamps),
            "cost": self.analysis_engine.detect_trend(metric_values["costs"], timestamps)
        }
    
    def _add_seasonality_analysis(self, result: Dict, data: List[Dict], metric_values: Dict) -> None:
        """Add seasonality detection if enough data."""
        if len(data) >= 24:
            timestamps = [datetime.fromisoformat(row['time_bucket']) for row in data]
            result["seasonality"] = self.analysis_engine.detect_seasonality(metric_values["latencies"][:len(timestamps)], timestamps)
    
    def _add_outlier_analysis(self, result: Dict, data: List[Dict], metric_values: Dict) -> None:
        """Add outlier analysis to results."""
        outlier_indices = self.analysis_engine.identify_outliers(metric_values["latencies"])
        if outlier_indices:
            result["outliers"] = {"latency_outliers": self._build_outlier_data(data, metric_values["latencies"], outlier_indices)}
    
    def _build_outlier_data(self, data: List[Dict], latencies: List, outlier_indices: List[int]) -> List[Dict]:
        """Build outlier data for response."""
        return [
            {
                "timestamp": data[i]['time_bucket'],
                "value": latencies[i],
                "percentile_rank": 100 * sum(1 for v in latencies if v < latencies[i]) / len(latencies)
            }
            for i in outlier_indices[:10]
        ]
    
    # Helper methods for detect_anomalies
    async def _fetch_anomaly_data(self, user_id: int, metric_name: str, time_range: Tuple[datetime, datetime], 
                                 z_score_threshold: float) -> Optional[List[Dict]]:
        """Fetch anomaly data from ClickHouse."""
        start_time, end_time = time_range
        query = self.query_builder.build_anomaly_detection_query(user_id, metric_name, start_time, end_time, z_score_threshold)
        cache_key = f"anomalies:{user_id}:{metric_name}:{start_time.isoformat()}:{z_score_threshold}"
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
    def _create_no_anomalies_response(self, metric_name: str, z_score_threshold: float) -> Dict[str, Any]:
        """Create response for no anomalies found."""
        return {
            "status": "no_anomalies",
            "message": f"No anomalies detected for {metric_name}",
            "threshold": z_score_threshold
        }
    
    def _build_anomalies_response(self, data: List[Dict], metric_name: str, z_score_threshold: float) -> Dict[str, Any]:
        """Build anomalies response."""
        return {
            "status": "anomalies_found",
            "metric": metric_name,
            "threshold": z_score_threshold,
            "anomaly_count": len(data),
            "anomalies": self._format_anomaly_list(data)
        }
    
    def _format_anomaly_list(self, data: List[Dict]) -> List[Dict]:
        """Format anomaly list for response."""
        return [
            {
                "timestamp": row['timestamp'],
                "value": row['metric_value'],
                "z_score": row['z_score'],
                "severity": "high" if abs(row['z_score']) > 3 else "medium"
            }
            for row in data[:50]
        ]
    
    # Helper methods for analyze_correlations
    async def _calculate_pairwise_correlations(self, user_id: int, metrics: List[str], 
                                             time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Calculate pairwise correlations between metrics."""
        start_time, end_time = time_range
        correlations = {}
        
        for i in range(len(metrics)):
            for j in range(i + 1, len(metrics)):
                correlation = await self._calculate_single_correlation(user_id, metrics[i], metrics[j], start_time, end_time)
                if correlation:
                    correlations[f"{metrics[i]}_vs_{metrics[j]}"] = correlation
        return correlations
    
    async def _calculate_single_correlation(self, user_id: int, metric1: str, metric2: str, 
                                          start_time: datetime, end_time: datetime) -> Optional[Dict]:
        """Calculate correlation between two metrics."""
        query = self.query_builder.build_correlation_analysis_query(user_id, metric1, metric2, start_time, end_time)
        data = await self.clickhouse_ops.fetch_data(query, redis_manager=self.redis_manager)
        
        if data and data[0]['sample_size'] > 10:
            return self._format_correlation_data(data[0])
        return None
    
    def _format_correlation_data(self, corr_data: Dict) -> Dict[str, Any]:
        """Format correlation data for response."""
        corr_coef = corr_data['correlation_coefficient']
        strength = self._interpret_correlation_strength(corr_coef)
        
        return {
            "coefficient": corr_coef,
            "strength": strength,
            "direction": "positive" if corr_coef > 0 else "negative",
            "sample_size": corr_data['sample_size'],
            "metric1_stats": {"mean": corr_data['metric1_avg'], "std": corr_data['metric1_std']},
            "metric2_stats": {"mean": corr_data['metric2_avg'], "std": corr_data['metric2_std']}
        }
    
    def _interpret_correlation_strength(self, corr_coef: float) -> str:
        """Interpret correlation coefficient strength."""
        abs_coef = abs(corr_coef)
        if abs_coef > 0.7:
            return "strong"
        elif abs_coef > 0.4:
            return "moderate"
        return "weak"
    
    def _build_correlation_response(self, time_range: Tuple[datetime, datetime], metrics: List[str], 
                                   correlations: Dict) -> Dict[str, Any]:
        """Build correlation analysis response."""
        start_time, end_time = time_range
        return {
            "time_range": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            "metrics_analyzed": metrics,
            "correlations": correlations,
            "strongest_correlation": self._find_strongest_correlation(correlations)
        }
    
    def _find_strongest_correlation(self, correlations: Dict) -> Optional[Tuple]:
        """Find the strongest correlation in the data."""
        if not correlations:
            return None
        return max(correlations.items(), key=lambda x: abs(x[1]['coefficient']))
    
    # Helper methods for analyze_usage_patterns  
    async def _fetch_usage_data(self, user_id: int, days_back: int) -> Optional[List[Dict]]:
        """Fetch usage pattern data from ClickHouse."""
        query = self.query_builder.build_usage_patterns_query(user_id, days_back)
        cache_key = f"usage_patterns:{user_id}:{days_back}"
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
    def _create_no_usage_data_response(self) -> Dict[str, Any]:
        """Create response for no usage data."""
        return {"status": "no_data", "message": "No usage data available"}
    
    def _aggregate_usage_patterns(self, data: List[Dict]) -> Dict[str, Dict]:
        """Aggregate usage data by day and hour patterns."""
        daily_patterns, hourly_patterns = {}, {}
        
        for row in data:
            self._update_daily_pattern(daily_patterns, row)
            self._update_hourly_pattern(hourly_patterns, row)
        
        return {"daily": daily_patterns, "hourly": hourly_patterns}
    
    def _update_daily_pattern(self, daily_patterns: Dict, row: Dict) -> None:
        """Update daily usage pattern with row data."""
        dow = row['day_of_week']
        if dow not in daily_patterns:
            daily_patterns[dow] = {"total_events": 0, "total_cost": 0, "unique_workloads": set(), "unique_models": set()}
        daily_patterns[dow]["total_events"] += row['event_count']
        daily_patterns[dow]["total_cost"] += row['total_cost']
    
    def _update_hourly_pattern(self, hourly_patterns: Dict, row: Dict) -> None:
        """Update hourly usage pattern with row data."""
        hour = row['hour_of_day']
        if hour not in hourly_patterns:
            hourly_patterns[hour] = {"total_events": 0, "total_cost": 0}
        hourly_patterns[hour]["total_events"] += row['event_count']
        hourly_patterns[hour]["total_cost"] += row['total_cost']
    
    def _find_peak_usage_times(self, patterns: Dict) -> Dict[str, Any]:
        """Find peak usage times from patterns."""
        peak_day = max(patterns["daily"].items(), key=lambda x: x[1]["total_events"])
        peak_hour = max(patterns["hourly"].items(), key=lambda x: x[1]["total_events"])
        return {"day": peak_day, "hour": peak_hour}
    
    def _calculate_usage_summary(self, patterns: Dict, days_back: int, peaks: Dict) -> Dict[str, Any]:
        """Calculate usage summary statistics."""
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        total_cost = sum(d["total_cost"] for d in patterns["daily"].values())
        total_events = sum(d["total_events"] for d in patterns["daily"].values())
        
        return {
            "total_cost": total_cost,
            "average_daily_cost": total_cost / days_back if days_back > 0 else 0,
            "peak_usage_day": day_names[peaks["day"][0] - 1],
            "peak_usage_hour": f"{peaks['hour'][0]:02d}:00",
            "total_events": total_events
        }
    
    def _build_usage_response(self, days_back: int, summary: Dict, patterns: Dict) -> Dict[str, Any]:
        """Build usage patterns response."""
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        return {
            "period": f"Last {days_back} days",
            "summary": summary,
            "daily_patterns": {day_names[k - 1]: v for k, v in patterns["daily"].items()},
            "hourly_distribution": patterns["hourly"]
        }

