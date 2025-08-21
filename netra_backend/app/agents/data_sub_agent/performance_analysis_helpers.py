"""Performance Analysis Helper Functions

Helper functions for performance metrics analysis operations.
Extracted to maintain 450-line module limit.

Business Value: Modular performance analysis utilities.
"""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from netra_backend.app.logging_config import central_logger as logger


class PerformanceAnalysisHelpers:
    """Helper functions for performance analysis operations."""
    
    def __init__(self, analysis_engine: Any):
        self.analysis_engine = analysis_engine
    
    def extract_metric_values(self, data: List[Dict]) -> Dict[str, List]:
        """Extract metric values from data for analysis."""
        return {
            "latencies": self._extract_latency_values(data),
            "throughputs": self._extract_throughput_values(data),
            "error_rates": self._extract_error_rate_values(data),
            "costs": self._extract_cost_values(data)
        }
    
    def _extract_latency_values(self, data: List[Dict]) -> List[float]:
        """Extract latency values from data."""
        return [row.get('latency_p50', 0) for row in data if row.get('latency_p50')]
    
    def _extract_throughput_values(self, data: List[Dict]) -> List[float]:
        """Extract throughput values from data."""
        return [row.get('avg_throughput', 0) for row in data if row.get('avg_throughput')]
    
    def _extract_error_rate_values(self, data: List[Dict]) -> List[float]:
        """Extract error rate values from data."""
        return [row.get('error_rate', 0) for row in data]
    
    def _extract_cost_values(self, data: List[Dict]) -> List[float]:
        """Extract cost values from data."""
        return [row.get('total_cost', 0) for row in data]
    
    def build_base_result(self, time_range: Tuple[datetime, datetime], 
                         data: List[Dict], metric_values: Dict) -> Dict[str, Any]:
        """Build base result structure with time range and statistics."""
        start_time, end_time = time_range
        aggregation = self._determine_aggregation_level(start_time, end_time)
        time_range_info = self._create_time_range_info(start_time, end_time, aggregation)
        statistics = self._compute_metric_statistics(data, metric_values)
        raw_data = self._limit_raw_data(data)
        return {**time_range_info, **statistics, "raw_data": raw_data}
    
    def _create_time_range_info(self, start_time: datetime, end_time: datetime, 
                               aggregation: str) -> Dict[str, Any]:
        """Create time range information structure."""
        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "aggregation_level": aggregation
            }
        }
    
    def _limit_raw_data(self, data: List[Dict]) -> List[Dict]:
        """Limit raw data to first 100 entries."""
        return data[:100]
    
    def _compute_metric_statistics(self, data: List[Dict], metric_values: Dict) -> Dict[str, Any]:
        """Compute statistics for all metrics."""
        return {
            "summary": self._build_summary_stats(data, metric_values["costs"]),
            "latency": self._compute_latency_stats(metric_values["latencies"]),
            "throughput": self._compute_throughput_stats(metric_values["throughputs"]),
            "error_rate": self._compute_error_rate_stats(metric_values["error_rates"])
        }
    
    def _compute_latency_stats(self, latencies: List[float]) -> Dict[str, Any]:
        """Compute latency statistics."""
        return self.analysis_engine.calculate_statistics(latencies)
    
    def _compute_throughput_stats(self, throughputs: List[float]) -> Dict[str, Any]:
        """Compute throughput statistics."""
        return self.analysis_engine.calculate_statistics(throughputs)
    
    def _compute_error_rate_stats(self, error_rates: List[float]) -> Dict[str, Any]:
        """Compute error rate statistics."""
        return self.analysis_engine.calculate_statistics(error_rates)
    
    def _build_summary_stats(self, data: List[Dict], costs: List) -> Dict[str, Any]:
        """Build summary statistics."""
        return {
            "total_events": self._sum_total_events(data),
            "unique_workloads": self._get_max_unique_workloads(data),
            "total_cost": sum(costs)
        }
    
    def _sum_total_events(self, data: List[Dict]) -> int:
        """Sum total events from data."""
        return sum(row.get('event_count', 0) for row in data)
    
    def _get_max_unique_workloads(self, data: List[Dict]) -> int:
        """Get maximum unique workloads from data."""
        return max(row.get('unique_workloads', 0) for row in data) if data else 0
    
    def _determine_aggregation_level(self, start_time: datetime, end_time: datetime) -> str:
        """Determine appropriate aggregation level based on time range."""
        time_diff = (end_time - start_time).total_seconds()
        if time_diff <= 3600:
            return "minute"
        elif time_diff <= 86400:
            return "hour"
        return "day"
    
    def add_trend_analysis(self, result: Dict, data: List[Dict], metric_values: Dict) -> None:
        """Add trend analysis if enough data points."""
        if len(data) >= 3:
            timestamps = self._extract_timestamps(data)
            result["trends"] = self._build_trend_data(metric_values, timestamps)
    
    def _extract_timestamps(self, data: List[Dict]) -> List[datetime]:
        """Extract timestamps from data."""
        return [datetime.fromisoformat(row['time_bucket']) for row in data]
    
    def _build_trend_data(self, metric_values: Dict, timestamps: List[datetime]) -> Dict[str, Any]:
        """Build trend analysis data."""
        return {
            "latency": self._detect_latency_trend(metric_values["latencies"], timestamps),
            "throughput": self._detect_throughput_trend(metric_values["throughputs"], timestamps),
            "cost": self._detect_cost_trend(metric_values["costs"], timestamps)
        }
    
    def _detect_latency_trend(self, latencies: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect latency trend."""
        return self.analysis_engine.detect_trend(latencies[:len(timestamps)], timestamps)
    
    def _detect_throughput_trend(self, throughputs: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect throughput trend."""
        return self.analysis_engine.detect_trend(throughputs[:len(timestamps)], timestamps)
    
    def _detect_cost_trend(self, costs: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect cost trend."""
        return self.analysis_engine.detect_trend(costs, timestamps)
    
    def add_seasonality_analysis(self, result: Dict, data: List[Dict], metric_values: Dict) -> None:
        """Add seasonality detection if enough data."""
        if len(data) >= 24:
            timestamps = self._extract_timestamps(data)
            seasonality = self._detect_seasonality(metric_values["latencies"], timestamps)
            result["seasonality"] = seasonality
    
    def _detect_seasonality(self, latencies: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect seasonality in latency data."""
        return self.analysis_engine.detect_seasonality(latencies[:len(timestamps)], timestamps)
    
    def add_outlier_analysis(self, result: Dict, data: List[Dict], metric_values: Dict) -> None:
        """Add outlier analysis to results."""
        outlier_indices = self._identify_outliers(metric_values["latencies"])
        if outlier_indices:
            outlier_data = self._build_outlier_data(data, metric_values["latencies"], outlier_indices)
            result["outliers"] = {"latency_outliers": outlier_data}
    
    def _identify_outliers(self, latencies: List[float]) -> List[int]:
        """Identify outliers in latency data."""
        return self.analysis_engine.identify_outliers(latencies)
    
    def _build_outlier_data(self, data: List[Dict], latencies: List, outlier_indices: List[int]) -> List[Dict]:
        """Build outlier data for response."""
        return [
            self._create_outlier_entry(data, latencies, i)
            for i in outlier_indices[:10]
        ]
    
    def _create_outlier_entry(self, data: List[Dict], latencies: List, index: int) -> Dict[str, Any]:
        """Create single outlier entry."""
        percentile_rank = self._calculate_percentile_rank(latencies, index)
        return {
            "timestamp": data[index]['time_bucket'],
            "value": latencies[index],
            "percentile_rank": percentile_rank
        }
    
    def _calculate_percentile_rank(self, latencies: List, index: int) -> float:
        """Calculate percentile rank for outlier."""
        return 100 * sum(1 for v in latencies if v < latencies[index]) / len(latencies)