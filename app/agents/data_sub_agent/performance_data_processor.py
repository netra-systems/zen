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
        start_time, end_time = time_range
        
        # Extract metric values for analysis
        latencies = [row.get('latency_p50', 0) for row in data if row.get('latency_p50')]
        throughputs = [row.get('avg_throughput', 0) for row in data if row.get('avg_throughput')]
        error_rates = [row.get('error_rate', 0) for row in data]
        costs = [row.get('total_cost', 0) for row in data]
        
        result = self._build_performance_result(data, time_range, aggregation, latencies, throughputs, error_rates, costs)
        
        # Add advanced analytics if sufficient data
        if len(data) >= 3:
            result["trends"] = self._calculate_trends(data, latencies, throughputs, costs)
        
        if len(data) >= 24:
            result["seasonality"] = self._detect_seasonality(data, latencies)
        
        if len(data) >= 10:
            result["outliers"] = self._identify_outliers(data, latencies)
        
        return result
    
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
        start_time, end_time = time_range
        
        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "aggregation_level": aggregation
            },
            "summary": {
                "total_events": sum(item.get('event_count', 0) for item in data),
                "data_points": len(data),
                "total_cost": sum(costs)
            },
            "latency": self.analysis_engine.calculate_statistics(latencies),
            "throughput": self.analysis_engine.calculate_statistics(throughputs),
            "error_rate": self.analysis_engine.calculate_statistics(error_rates),
            "raw_data": data[:100]  # Limit raw data size
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
        
        return {
            "detected": True,
            "count": len(outlier_indices),
            "threshold": 2.5,
            "outlier_indices": outlier_indices[:10],  # Limit to top 10
            "latency_outliers": [
                {
                    "index": i,
                    "timestamp": data[i]['time_bucket'],
                    "value": latencies[i],
                    "percentile_rank": 100 * sum(1 for v in latencies if v < latencies[i]) / len(latencies)
                }
                for i in outlier_indices[:10]
            ]
        }