"""Performance data processing module with ≤8 line functions."""

from typing import Dict, List, Any, Tuple
from datetime import datetime


class PerformanceDataProcessor:
    """Process performance metrics data with focused functions."""
    
    def __init__(self, analysis_engine: Any) -> None:
        self.analysis_engine = analysis_engine
    
    def process_performance_data(
        self,
        data: List[Dict[str, Any]],
        time_range: Tuple[datetime, datetime],
        aggregation: str
    ) -> Dict[str, Any]:
        """Process performance metrics data."""
        metrics = self._extract_metric_values(data)
        result = self._build_performance_result(data, time_range, aggregation, *metrics)
        self._add_advanced_analytics(result, data, metrics)
        return result
    
    def _extract_metric_values(self, data: List[Dict[str, Any]]) -> Tuple[List[float], List[float], List[float], List[float]]:
        """Extract metric values for analysis."""
        latencies = [row.get('latency_p50', 0) for row in data if row.get('latency_p50')]
        throughputs = [row.get('avg_throughput', 0) for row in data if row.get('avg_throughput')]
        error_rates = [row.get('error_rate', 0) for row in data]
        costs = [row.get('total_cost', 0) for row in data]
        return latencies, throughputs, error_rates, costs
    
    def _add_advanced_analytics(self, result: Dict[str, Any], data: List[Dict[str, Any]], metrics: Tuple[List[float], List[float], List[float], List[float]]) -> None:
        """Add advanced analytics if sufficient data."""
        latencies, throughputs, _, costs = metrics
        if len(data) >= 3:
            result["trends"] = self._calculate_trends(data, latencies, throughputs, costs)
        if len(data) >= 24:
            result["seasonality"] = self._detect_seasonality(data, latencies)
        if len(data) >= 10:
            result["outliers"] = self._identify_outliers(data, latencies)
    
    def _build_performance_result(
        self,
        data: List[Dict[str, Any]],
        time_range: Tuple[datetime, datetime],
        aggregation: str,
        latencies: List[float],
        throughputs: List[float],
        error_rates: List[float],
        costs: List[float]
    ) -> Dict[str, Any]:
        """Build performance analysis result."""
        return {
            "time_range": self._build_time_range_section(time_range, aggregation),
            "summary": self._build_summary_section(data, costs),
            **self._build_metrics_sections(latencies, throughputs, error_rates),
            "raw_data": data[:100]  # Limit raw data size
        }
    
    def _build_time_range_section(self, time_range: Tuple[datetime, datetime], aggregation: str) -> Dict[str, str]:
        """Build time range section of result."""
        start_time, end_time = time_range
        return {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "aggregation_level": aggregation
        }
    
    def _build_summary_section(self, data: List[Dict[str, Any]], costs: List[float]) -> Dict[str, Any]:
        """Build summary section of result."""
        return {
            "total_events": sum(item.get('event_count', 0) for item in data),
            "data_points": len(data),
            "total_cost": sum(costs)
        }
    
    def _build_metrics_sections(self, latencies: List[float], throughputs: List[float], error_rates: List[float]) -> Dict[str, Any]:
        """Build metrics sections of result."""
        return {
            "latency": self.analysis_engine.calculate_statistics(latencies),
            "throughput": self.analysis_engine.calculate_statistics(throughputs),
            "error_rate": self.analysis_engine.calculate_statistics(error_rates)
        }
    
    def _calculate_trends(
        self,
        data: List[Dict[str, Any]],
        latencies: List[float],
        throughputs: List[float],
        costs: List[float]
    ) -> Dict[str, Any]:
        """Calculate trend analysis."""
        timestamps = [datetime.fromisoformat(row['time_bucket']) for row in data]
        
        return {
            "latency": self.analysis_engine.detect_trend(latencies[:len(timestamps)], timestamps),
            "throughput": self.analysis_engine.detect_trend(throughputs[:len(timestamps)], timestamps),
            "cost": self.analysis_engine.detect_trend(costs, timestamps)
        }
    
    def _detect_seasonality(self, data: List[Dict[str, Any]], latencies: List[float]) -> Dict[str, Any]:
        """Detect seasonality patterns."""
        timestamps = [datetime.fromisoformat(row['time_bucket']) for row in data]
        return self.analysis_engine.detect_seasonality(latencies[:len(timestamps)], timestamps)
    
    def _identify_outliers(self, data: List[Dict[str, Any]], latencies: List[float]) -> Dict[str, Any]:
        """Identify performance outliers."""
        outlier_indices = self.analysis_engine.identify_outliers(latencies)
        if not outlier_indices:
            return {"detected": False}
        return self._build_outliers_result(outlier_indices, data, latencies)
    
    def _build_outliers_result(self, outlier_indices: List[int], data: List[Dict[str, Any]], latencies: List[float]) -> Dict[str, Any]:
        """Build outliers result structure."""
        return {
            "detected": True, "count": len(outlier_indices), "threshold": 2.5,
            "outlier_indices": outlier_indices[:10],
            "latency_outliers": self._build_outlier_details(outlier_indices[:10], data, latencies)
        }
    
    def _build_outlier_details(self, indices: List[int], data: List[Dict[str, Any]], latencies: List[float]) -> List[Dict[str, Any]]:
        """Build detailed outlier information."""
        return [{
            "index": i, "timestamp": data[i]['time_bucket'], "value": latencies[i],
            "percentile_rank": 100 * sum(1 for v in latencies if v < latencies[i]) / len(latencies)
        } for i in indices]