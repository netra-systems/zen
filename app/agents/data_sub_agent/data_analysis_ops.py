"""Data analysis operations module for DataSubAgent - handles complex analysis tasks."""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app.logging_config import central_logger as logger
from .data_fetching import DataFetching


class DataAnalysisOperations:
    """Handles complex data analysis operations"""
    
    def __init__(self, data_fetching: DataFetching):
        self.data_fetching = data_fetching
    
    async def analyze_performance_metrics(
        self,
        user_id: int,
        workload_id: Optional[str],
        time_range: Tuple[datetime, datetime],
        query_builder,
        analysis_engine
    ) -> Dict[str, Any]:
        """Analyze performance metrics from ClickHouse"""
        data = await self._fetch_metrics_data(user_id, workload_id, time_range, query_builder)
        if not data:
            return self._create_no_data_response()
        return self._process_metrics_data(data, time_range, analysis_engine)
    
    def _process_metrics_data(self, data: List[Dict], time_range: Tuple[datetime, datetime], analysis_engine) -> Dict[str, Any]:
        """Process metrics data and build complete result."""
        metric_values = self._extract_metric_values(data)
        result = self._build_base_result(time_range, data, metric_values, analysis_engine)
        self._add_all_analyses(result, data, metric_values, analysis_engine)
        return result
    
    def _add_all_analyses(self, result: Dict, data: List[Dict], metric_values: Dict, analysis_engine) -> None:
        """Add all analysis types to result."""
        self._add_trend_analysis(result, data, metric_values, analysis_engine)
        self._add_seasonality_analysis(result, data, metric_values, analysis_engine)
        self._add_outlier_analysis(result, data, metric_values, analysis_engine)
    
    async def detect_anomalies(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        query_builder,
        z_score_threshold: float = 2.0
    ) -> Dict[str, Any]:
        """Detect anomalies in metric data"""
        data = await self._fetch_anomaly_data(user_id, metric_name, time_range, query_builder, z_score_threshold)
        return self._process_anomaly_data(data, metric_name, z_score_threshold)
    
    def _process_anomaly_data(self, data: Optional[List[Dict]], metric_name: str, z_score_threshold: float) -> Dict[str, Any]:
        """Process anomaly data and build response."""
        if not data:
            return self._create_no_anomalies_response(metric_name, z_score_threshold)
        return self._build_anomalies_response(data, metric_name, z_score_threshold)
    
    async def analyze_correlations(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime],
        query_builder
    ) -> Dict[str, Any]:
        """Analyze correlations between multiple metrics"""
        if len(metrics) < 2:
            return self._create_insufficient_metrics_error()
        return await self._process_correlation_analysis(user_id, metrics, time_range, query_builder)
    
    def _create_insufficient_metrics_error(self) -> Dict[str, str]:
        """Create error response for insufficient metrics."""
        return {"error": "At least 2 metrics required for correlation analysis"}
    
    async def _process_correlation_analysis(self, user_id: int, metrics: List[str], time_range: Tuple[datetime, datetime], query_builder) -> Dict[str, Any]:
        """Process correlation analysis for valid metrics."""
        correlations = await self._calculate_pairwise_correlations(user_id, metrics, time_range, query_builder)
        return self._build_correlation_response(time_range, metrics, correlations)
    
    async def analyze_usage_patterns(
        self,
        user_id: int,
        query_builder,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Analyze usage patterns over time"""
        data = await self._fetch_usage_data(user_id, query_builder, days_back)
        if not data:
            return self._create_no_usage_data_response()
        return self._process_usage_patterns(data, days_back)
    
    def _process_usage_patterns(self, data: List[Dict], days_back: int) -> Dict[str, Any]:
        """Process usage patterns data and build response."""
        patterns = self._aggregate_usage_patterns(data)
        peaks = self._find_peak_usage_times(patterns)
        summary = self._calculate_usage_summary(patterns, days_back, peaks)
        return self._build_usage_response(days_back, summary, patterns)
    
    # Helper methods for analyze_performance_metrics
    async def _fetch_metrics_data(self, user_id: int, workload_id: Optional[str], 
                                 time_range: Tuple[datetime, datetime], query_builder) -> Optional[List[Dict]]:
        """Fetch metrics data from ClickHouse."""
        start_time, end_time = time_range
        aggregation = self._determine_aggregation_level(start_time, end_time)
        query = query_builder.build_performance_metrics_query(user_id, workload_id, start_time, end_time, aggregation)
        cache_key = f"perf_metrics:{user_id}:{workload_id}:{start_time.isoformat()}:{end_time.isoformat()}"
        return await self.data_fetching.fetch_clickhouse_data(query, cache_key)
    
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
    
    def _build_base_result(self, time_range: Tuple[datetime, datetime], data: List[Dict], 
                          metric_values: Dict, analysis_engine) -> Dict[str, Any]:
        """Build base result structure with time range and statistics."""
        start_time, end_time = time_range
        aggregation = self._determine_aggregation_level(start_time, end_time)
        time_range_info = {"start": start_time.isoformat(), "end": end_time.isoformat(), "aggregation_level": aggregation}
        return self._create_result_structure(time_range_info, data, metric_values, analysis_engine)
    
    def _create_result_structure(self, time_range_info: Dict, data: List[Dict], metric_values: Dict, analysis_engine) -> Dict[str, Any]:
        """Create complete result structure."""
        statistics = self._build_metric_statistics(metric_values, analysis_engine)
        return self._combine_result_components(time_range_info, data, metric_values, statistics)
    
    def _build_metric_statistics(self, metric_values: Dict, analysis_engine) -> Dict[str, Any]:
        """Build statistics for all metrics."""
        return {
            "latency": analysis_engine.calculate_statistics(metric_values["latencies"]),
            "throughput": analysis_engine.calculate_statistics(metric_values["throughputs"]),
            "error_rate": analysis_engine.calculate_statistics(metric_values["error_rates"])
        }
    
    def _combine_result_components(self, time_range_info: Dict, data: List[Dict], metric_values: Dict, statistics: Dict) -> Dict[str, Any]:
        """Combine all result components."""
        base_info = {"time_range": time_range_info, "summary": self._build_summary_stats(data, metric_values["costs"])}
        metric_info = {"latency": statistics["latency"], "throughput": statistics["throughput"]}
        error_info = {"error_rate": statistics["error_rate"], "raw_data": data[:100]}
        return {**base_info, **metric_info, **error_info}
    
    def _build_summary_stats(self, data: List[Dict], costs: List) -> Dict[str, Any]:
        """Build summary statistics."""
        return {
            "total_events": sum(row.get('event_count', 0) for row in data),
            "unique_workloads": max(row.get('unique_workloads', 0) for row in data),
            "total_cost": sum(costs)
        }
    
    def _add_trend_analysis(self, result: Dict, data: List[Dict], metric_values: Dict, analysis_engine) -> None:
        """Add trend analysis if enough data points."""
        if len(data) >= 3:
            timestamps = [datetime.fromisoformat(row['time_bucket']) for row in data]
            result["trends"] = self._build_trend_data(metric_values, timestamps, analysis_engine)
    
    def _build_trend_data(self, metric_values: Dict, timestamps: List[datetime], analysis_engine) -> Dict[str, Any]:
        """Build trend analysis data."""
        return {
            "latency": analysis_engine.detect_trend(metric_values["latencies"][:len(timestamps)], timestamps),
            "throughput": analysis_engine.detect_trend(metric_values["throughputs"][:len(timestamps)], timestamps),
            "cost": analysis_engine.detect_trend(metric_values["costs"], timestamps)
        }
    
    def _add_seasonality_analysis(self, result: Dict, data: List[Dict], metric_values: Dict, analysis_engine) -> None:
        """Add seasonality detection if enough data."""
        if len(data) >= 24:
            timestamps = [datetime.fromisoformat(row['time_bucket']) for row in data]
            result["seasonality"] = analysis_engine.detect_seasonality(metric_values["latencies"][:len(timestamps)], timestamps)
    
    def _add_outlier_analysis(self, result: Dict, data: List[Dict], metric_values: Dict, analysis_engine) -> None:
        """Add outlier analysis to results."""
        outlier_indices = analysis_engine.identify_outliers(metric_values["latencies"])
        if outlier_indices:
            result["outliers"] = {"latency_outliers": self._build_outlier_data(data, metric_values["latencies"], outlier_indices)}
    
    def _build_outlier_data(self, data: List[Dict], latencies: List, outlier_indices: List[int]) -> List[Dict]:
        """Build outlier data for response."""
        return [self._create_outlier_entry(data, latencies, i) for i in outlier_indices[:10]]
    
    def _create_outlier_entry(self, data: List[Dict], latencies: List, index: int) -> Dict[str, Any]:
        """Create single outlier data entry."""
        percentile_rank = 100 * sum(1 for v in latencies if v < latencies[index]) / len(latencies)
        return {
            "timestamp": data[index]['time_bucket'],
            "value": latencies[index],
            "percentile_rank": percentile_rank
        }
    
    # Helper methods for detect_anomalies
    async def _fetch_anomaly_data(self, user_id: int, metric_name: str, time_range: Tuple[datetime, datetime], 
                                 query_builder, z_score_threshold: float) -> Optional[List[Dict]]:
        """Fetch anomaly data from ClickHouse."""
        start_time, end_time = time_range
        query = query_builder.build_anomaly_detection_query(user_id, metric_name, start_time, end_time, z_score_threshold)
        cache_key = f"anomalies:{user_id}:{metric_name}:{start_time.isoformat()}:{z_score_threshold}"
        return await self.data_fetching.fetch_clickhouse_data(query, cache_key)
    
    def _create_no_anomalies_response(self, metric_name: str, z_score_threshold: float) -> Dict[str, Any]:
        """Create response for no anomalies found."""
        return {
            "status": "no_anomalies",
            "message": f"No anomalies detected for {metric_name}",
            "threshold": z_score_threshold
        }
    
    def _build_anomalies_response(self, data: List[Dict], metric_name: str, z_score_threshold: float) -> Dict[str, Any]:
        """Build anomalies response."""
        base_response = self._create_anomaly_base_response(metric_name, z_score_threshold)
        base_response.update({"anomaly_count": len(data), "anomalies": self._format_anomaly_list(data)})
        return base_response
    
    def _create_anomaly_base_response(self, metric_name: str, z_score_threshold: float) -> Dict[str, Any]:
        """Create base anomaly response structure."""
        return {
            "status": "anomalies_found",
            "metric": metric_name,
            "threshold": z_score_threshold
        }
    
    def _format_anomaly_list(self, data: List[Dict]) -> List[Dict]:
        """Format anomaly list for response."""
        return [self._format_single_anomaly(row) for row in data[:50]]
    
    def _format_single_anomaly(self, row: Dict) -> Dict[str, Any]:
        """Format single anomaly entry."""
        severity = self._determine_anomaly_severity(row['z_score'])
        return self._build_anomaly_entry(row, severity)
    
    def _determine_anomaly_severity(self, z_score: float) -> str:
        """Determine anomaly severity based on z-score."""
        return "high" if abs(z_score) > 3 else "medium"
    
    def _build_anomaly_entry(self, row: Dict, severity: str) -> Dict[str, Any]:
        """Build complete anomaly entry."""
        return {
            "timestamp": row['timestamp'],
            "value": row['metric_value'],
            "z_score": row['z_score'],
            "severity": severity
        }
    
    # Helper methods for analyze_correlations
    async def _calculate_pairwise_correlations(self, user_id: int, metrics: List[str], 
                                             time_range: Tuple[datetime, datetime], query_builder) -> Dict[str, Any]:
        """Calculate pairwise correlations between metrics."""
        start_time, end_time = time_range
        correlations = {}
        await self._process_metric_pairs(user_id, metrics, start_time, end_time, query_builder, correlations)
        return correlations
    
    async def _process_metric_pairs(self, user_id: int, metrics: List[str], start_time: datetime, 
                                   end_time: datetime, query_builder, correlations: Dict) -> None:
        """Process all metric pairs for correlation calculation."""
        for i in range(len(metrics)):
            for j in range(i + 1, len(metrics)):
                await self._add_correlation_if_valid(user_id, metrics[i], metrics[j], start_time, end_time, query_builder, correlations)
    
    async def _add_correlation_if_valid(self, user_id: int, metric1: str, metric2: str, start_time: datetime, 
                                       end_time: datetime, query_builder, correlations: Dict) -> None:
        """Add correlation to dict if valid."""
        correlation = await self._calculate_single_correlation(user_id, metric1, metric2, start_time, end_time, query_builder)
        if correlation:
            correlations[f"{metric1}_vs_{metric2}"] = correlation
    
    async def _calculate_single_correlation(self, user_id: int, metric1: str, metric2: str, 
                                          start_time: datetime, end_time: datetime, query_builder) -> Optional[Dict]:
        """Calculate correlation between two metrics."""
        query = query_builder.build_correlation_analysis_query(user_id, metric1, metric2, start_time, end_time)
        data = await self.data_fetching.fetch_clickhouse_data(query)
        return self._process_correlation_result(data)
    
    def _process_correlation_result(self, data: Optional[List[Dict]]) -> Optional[Dict]:
        """Process correlation calculation result."""
        if data and data[0]['sample_size'] > 10:
            return self._format_correlation_data(data[0])
        return None
    
    def _format_correlation_data(self, corr_data: Dict) -> Dict[str, Any]:
        """Format correlation data for response."""
        corr_coef = corr_data['correlation_coefficient']
        strength = self._interpret_correlation_strength(corr_coef)
        direction = "positive" if corr_coef > 0 else "negative"
        return self._build_correlation_result(corr_coef, strength, direction, corr_data)
    
    def _build_correlation_result(self, corr_coef: float, strength: str, direction: str, corr_data: Dict) -> Dict[str, Any]:
        """Build complete correlation result."""
        basic_info = {"coefficient": corr_coef, "strength": strength, "direction": direction, "sample_size": corr_data['sample_size']}
        metric_stats = self._build_correlation_metric_stats(corr_data)
        return {**basic_info, **metric_stats}
    
    def _build_correlation_metric_stats(self, corr_data: Dict) -> Dict[str, Any]:
        """Build metric statistics for correlation result."""
        return {
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
        time_range_info = {"start": start_time.isoformat(), "end": end_time.isoformat()}
        return self._create_correlation_response(time_range_info, metrics, correlations)
    
    def _create_correlation_response(self, time_range_info: Dict, metrics: List[str], correlations: Dict) -> Dict[str, Any]:
        """Create complete correlation response."""
        return {
            "time_range": time_range_info,
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
    async def _fetch_usage_data(self, user_id: int, query_builder, days_back: int) -> Optional[List[Dict]]:
        """Fetch usage pattern data from ClickHouse."""
        query = query_builder.build_usage_patterns_query(user_id, days_back)
        cache_key = f"usage_patterns:{user_id}:{days_back}"
        return await self.data_fetching.fetch_clickhouse_data(query, cache_key)
    
    def _create_no_usage_data_response(self) -> Dict[str, Any]:
        """Create response for no usage data."""
        return {"status": "no_data", "message": "No usage data available"}
    
    def _aggregate_usage_patterns(self, data: List[Dict]) -> Dict[str, Dict]:
        """Aggregate usage data by day and hour patterns."""
        daily_patterns, hourly_patterns = {}, {}
        self._process_usage_rows(data, daily_patterns, hourly_patterns)
        return {"daily": daily_patterns, "hourly": hourly_patterns}
    
    def _process_usage_rows(self, data: List[Dict], daily_patterns: Dict, hourly_patterns: Dict) -> None:
        """Process all usage data rows."""
        for row in data:
            self._update_daily_pattern(daily_patterns, row)
            self._update_hourly_pattern(hourly_patterns, row)
    
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
        totals = self._calculate_usage_totals(patterns)
        return self._build_usage_summary_dict(totals, days_back, peaks, day_names)
    
    def _calculate_usage_totals(self, patterns: Dict) -> Dict[str, float]:
        """Calculate total cost and events from patterns."""
        total_cost = sum(d["total_cost"] for d in patterns["daily"].values())
        total_events = sum(d["total_events"] for d in patterns["daily"].values())
        return {"total_cost": total_cost, "total_events": total_events}
    
    def _build_usage_summary_dict(self, totals: Dict, days_back: int, peaks: Dict, day_names: List[str]) -> Dict[str, Any]:
        """Build usage summary dictionary."""
        cost_info = self._build_cost_summary(totals, days_back)
        peak_info = self._build_peak_summary(peaks, day_names)
        return {**cost_info, **peak_info, "total_events": totals["total_events"]}
    
    def _build_cost_summary(self, totals: Dict, days_back: int) -> Dict[str, Any]:
        """Build cost summary information."""
        return {
            "total_cost": totals["total_cost"],
            "average_daily_cost": totals["total_cost"] / days_back if days_back > 0 else 0
        }
    
    def _build_peak_summary(self, peaks: Dict, day_names: List[str]) -> Dict[str, Any]:
        """Build peak usage summary information."""
        return {
            "peak_usage_day": day_names[peaks["day"][0] - 1],
            "peak_usage_hour": f"{peaks['hour'][0]:02d}:00"
        }
    
    def _build_usage_response(self, days_back: int, summary: Dict, patterns: Dict) -> Dict[str, Any]:
        """Build usage patterns response."""
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        daily_patterns = {day_names[k - 1]: v for k, v in patterns["daily"].items()}
        return self._create_usage_response_dict(days_back, summary, daily_patterns, patterns["hourly"])
    
    def _create_usage_response_dict(self, days_back: int, summary: Dict, daily_patterns: Dict, hourly_patterns: Dict) -> Dict[str, Any]:
        """Create complete usage response dictionary."""
        return {
            "period": f"Last {days_back} days",
            "summary": summary,
            "daily_patterns": daily_patterns,
            "hourly_distribution": hourly_patterns
        }
    
