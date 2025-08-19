"""Data Processing Operations Module - Analysis operations (<300 lines)

Business Value: Data processing operations for customer insights
BVJ: Growth & Enterprise | Data Analytics | +15% operational efficiency
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from app.logging_config import central_logger as logger


class DataProcessingOperations:
    """Handles complex data processing and analysis operations."""
    
    def __init__(self, agent):
        """Initialize with agent reference."""
        self.agent = agent
        
    async def analyze_performance_metrics(self, user_id: int, workload_id: str, time_range) -> Dict[str, Any]:
        """Analyze performance metrics with enhanced processing."""
        try:
            data = await self._fetch_performance_data(user_id, workload_id)
            if not data:
                return self._create_no_data_response()
            return await self._process_performance_analysis(data, time_range)
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _fetch_performance_data(self, user_id: int, workload_id: str) -> List[Dict]:
        """Fetch performance data with caching."""
        cache_key = f"perf_metrics_{user_id}_{workload_id}"
        query = f"SELECT * FROM performance_metrics WHERE user_id = {user_id} AND workload_id = '{workload_id}'"
        return await self.agent._fetch_clickhouse_data(query, cache_key)
        
    def _create_no_data_response(self) -> Dict[str, Any]:
        """Create response for no data scenarios."""
        return {"status": "no_data", "message": "No performance data found"}
        
    async def _process_performance_analysis(self, data: List[Dict], time_range) -> Dict[str, Any]:
        """Process performance data with comprehensive analysis."""
        base_metrics = self._calculate_base_metrics(data)
        result = self._create_base_result(base_metrics, time_range)
        
        # Add advanced analysis for sufficient data
        if len(data) >= 10:
            result["trends"] = self._calculate_trends(data)
        if len(data) >= 24:
            result["seasonality"] = self._calculate_seasonality(data)
        if len(data) >= 5:
            result["outliers"] = self._detect_outliers(data)
            
        return result
        
    def _calculate_base_metrics(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate basic performance metrics."""
        total_events = sum(item.get('event_count', 0) for item in data)
        avg_latency = sum(item.get('latency_p50', 0) for item in data) / len(data) if data else 0
        avg_throughput = sum(item.get('avg_throughput', 0) for item in data) / len(data) if data else 0
        return {"total_events": total_events, "avg_latency": avg_latency, "avg_throughput": avg_throughput}
        
    def _create_base_result(self, metrics: Dict, time_range) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            "status": "success",
            "time_range": self._format_time_range(time_range),
            "summary": {"total_events": metrics["total_events"], "data_points": len([])},
            "latency": {"avg_p50": metrics["avg_latency"], "unit": "ms"},
            "throughput": {"average": metrics["avg_throughput"], "unit": "requests/s"}
        }
        
    def _format_time_range(self, time_range) -> Dict[str, Any]:
        """Format time range information."""
        aggregation_level = self._determine_aggregation_level(time_range)
        return {
            "aggregation_level": aggregation_level,
            "start": time_range[0].isoformat() if hasattr(time_range, '__len__') and len(time_range) > 0 else None,
            "end": time_range[1].isoformat() if hasattr(time_range, '__len__') and len(time_range) > 1 else None
        }
    
    def _determine_aggregation_level(self, time_range) -> str:
        """Determine aggregation level based on duration."""
        try:
            if hasattr(time_range, '__len__') and len(time_range) >= 2:
                duration = time_range[1] - time_range[0]
                return self._get_level_by_duration(duration.total_seconds())
            return "hour"
        except:
            return "hour"
    
    def _get_level_by_duration(self, seconds: float) -> str:
        """Get aggregation level by duration in seconds."""
        if seconds < 3600:
            return "minute"
        elif seconds < 86400:
            return "hour"
        else:
            return "day"
    
    def _calculate_trends(self, data: list) -> Dict[str, Any]:
        """Calculate trend analysis for performance data."""
        if len(data) < 2:
            return {"status": "insufficient_data"}
        
        event_counts = [item.get('event_count', 0) for item in data]
        trend_direction = self._analyze_trend_direction(event_counts)
        
        return {
            "overall_trend": trend_direction,
            "data_points_analyzed": len(data),
            "confidence": "medium"
        }
    
    def _analyze_trend_direction(self, values: List[float]) -> str:
        """Analyze trend direction from values."""
        if len(values) < 2:
            return "stable"
            
        first_half = sum(values[:len(values)//2])
        second_half = sum(values[len(values)//2:])
        
        if second_half > first_half:
            return "increasing"
        elif second_half < first_half:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_seasonality(self, data: list) -> Dict[str, Any]:
        """Calculate seasonality patterns."""
        if len(data) < 24:
            return {"status": "insufficient_data"}
        
        hourly_data = self._group_by_hour(data)
        avg_by_hour = {hour: sum(counts)/len(counts) for hour, counts in hourly_data.items()}
        peak_hour, low_hour = self._find_peak_and_low_hours(avg_by_hour)
        
        return {
            "detected": True,
            "peak_hour": peak_hour,
            "low_hour": low_hour,
            "peak_value": avg_by_hour.get(peak_hour, 0),
            "low_value": avg_by_hour.get(low_hour, 0),
            "confidence": "medium"
        }
    
    def _group_by_hour(self, data: List[Dict]) -> Dict[int, List[int]]:
        """Group data by hour pattern."""
        hourly_data = {}
        for i, item in enumerate(data):
            hour = i % 24
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(item.get('event_count', 0))
        return hourly_data
        
    def _find_peak_and_low_hours(self, avg_by_hour: Dict[int, float]) -> tuple:
        """Find peak and low hours from averages."""
        if not avg_by_hour:
            return 0, 0
        peak_hour = max(avg_by_hour, key=avg_by_hour.get)
        low_hour = min(avg_by_hour, key=avg_by_hour.get)
        return peak_hour, low_hour
    
    def _detect_outliers(self, data: list) -> Dict[str, Any]:
        """Detect outliers using statistical methods."""
        if len(data) < 5:
            return {"detected": False, "reason": "insufficient_data"}
        
        latency_values = [item.get('latency_p50', 0) for item in data if item.get('latency_p50') is not None]
        if len(latency_values) < 5:
            return {"detected": False, "reason": "insufficient_latency_data"}
        
        statistics = self._calculate_statistics(latency_values)
        outliers = self._find_outliers(latency_values, statistics)
        
        return {
            "detected": len(outliers) > 0,
            "count": len(outliers),
            "latency_outliers": outliers,
            "threshold": 2.0,
            "mean_latency": statistics['mean'],
            "std_dev": statistics['std_dev']
        }
    
    def _calculate_statistics(self, values: List[float]) -> Dict[str, float]:
        """Calculate basic statistics for outlier detection."""
        mean_value = sum(values) / len(values)
        variance = sum((x - mean_value) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        return {'mean': mean_value, 'std_dev': std_dev}
        
    def _find_outliers(self, values: List[float], stats: Dict[str, float]) -> List[Dict]:
        """Find outliers based on z-score threshold."""
        outliers = []
        threshold = 2.0
        
        for i, value in enumerate(values):
            z_score = abs((value - stats['mean']) / stats['std_dev']) if stats['std_dev'] > 0 else 0
            if z_score > threshold:
                outliers.append({
                    "index": i,
                    "value": value,
                    "z_score": z_score,
                    "metric": "latency_p50"
                })
        return outliers
    
    async def detect_anomalies(self, user_id: int, metric_name: str, time_range, z_score_threshold: float = 3.0) -> Dict[str, Any]:
        """Detect anomalies in metrics data."""
        try:
            data = await self._fetch_anomaly_data(user_id, metric_name)
            if not data:
                return {"status": "no_data", "message": "No data found for anomaly detection"}
            return await self._process_anomaly_detection(data, z_score_threshold)
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _fetch_anomaly_data(self, user_id: int, metric_name: str) -> List[Dict]:
        """Fetch data for anomaly detection."""
        cache_key = f"anomalies_{user_id}_{metric_name}"
        query = f"SELECT * FROM metrics WHERE user_id = {user_id} AND metric_name = '{metric_name}'"
        return await self.agent._fetch_clickhouse_data(query, cache_key)
        
    async def _process_anomaly_detection(self, data: List[Dict], threshold: float) -> Dict[str, Any]:
        """Process anomaly detection on data."""
        values = [item.get('value', 0) for item in data if item.get('value') is not None]
        if len(values) < 2:
            return {"status": "insufficient_data", "message": "Need at least 2 data points"}
        
        anomalies = self._identify_anomalies(data, values, threshold)
        
        return {
            "status": "success",
            "anomalies_detected": len(anomalies),
            "anomaly_percentage": (len(anomalies) / len(data)) * 100 if data else 0,
            "anomalies": anomalies,
            "threshold": threshold,
            "total_data_points": len(data)
        }
    
    def _identify_anomalies(self, data: List[Dict], values: List[float], threshold: float) -> List[Dict]:
        """Identify anomalies using z-score method."""
        anomalies = []
        mean_value = sum(values) / len(values)
        variance = sum((x - mean_value) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        for i, item in enumerate(data):
            z_score = self._calculate_z_score(item, mean_value, std_dev, values)
            if z_score > threshold:
                anomalies.append({
                    "index": i,
                    "timestamp": item.get('timestamp'),
                    "value": item.get('value', 0),
                    "z_score": z_score
                })
        return anomalies
    
    def _calculate_z_score(self, item: Dict, mean_value: float, std_dev: float, values: List[float]) -> float:
        """Calculate z-score for anomaly detection."""
        if 'z_score' in item and item['z_score'] is not None:
            return abs(item['z_score'])
        
        value = item.get('value', 0)
        if std_dev > 0:
            return abs((value - mean_value) / std_dev)
        return 0
    
    async def analyze_usage_patterns(self, user_id: int, days_back: int = 7) -> Dict[str, Any]:
        """Analyze usage patterns for optimization insights."""
        try:
            data = await self._fetch_usage_data(user_id, days_back)
            if not data:
                return {"status": "no_data", "message": "No usage pattern data found"}
            return self._process_usage_analysis(data, days_back)
        except Exception as e:
            logger.error(f"Usage pattern analysis failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _fetch_usage_data(self, user_id: int, days_back: int) -> List[Dict]:
        """Fetch usage pattern data."""
        cache_key = f"usage_patterns_{user_id}_{days_back}"
        query = f"SELECT * FROM usage_patterns WHERE user_id = {user_id} AND date_added >= NOW() - INTERVAL {days_back} DAY"
        return await self.agent._fetch_clickhouse_data(query, cache_key)
        
    def _process_usage_analysis(self, data: List[Dict], days_back: int) -> Dict[str, Any]:
        """Process usage pattern analysis."""
        hourly_totals = self._calculate_hourly_usage_totals(data)
        hourly_averages = {hour: sum(events)/len(events) for hour, events in hourly_totals.items()}
        peak_hour, low_hour = self._find_peak_and_low_hours(hourly_averages)
        
        return {
            "status": "success",
            "hourly_patterns": hourly_averages,
            "peak_hour": peak_hour,
            "low_hour": low_hour,
            "peak_value": hourly_averages.get(peak_hour, 0),
            "low_value": hourly_averages.get(low_hour, 0),
            "days_analyzed": days_back
        }
    
    def _calculate_hourly_usage_totals(self, data: List[Dict]) -> Dict[int, List[int]]:
        """Calculate hourly usage totals from data."""
        hourly_totals = {}
        for item in data:
            hour = item.get('hour', 0)
            total_events = item.get('total_events', 0)
            if hour not in hourly_totals:
                hourly_totals[hour] = []
            hourly_totals[hour].append(total_events)
        return hourly_totals
    
    async def analyze_correlations(self, user_id: int, metric1: str, metric2: str, time_range) -> Dict[str, Any]:
        """Analyze correlations between metrics."""
        try:
            data = await self._fetch_correlation_data(user_id, metric1, metric2)
            if not data or len(data) < 2:
                return {"status": "insufficient_data", "message": "Need at least 2 data points"}
            return self._calculate_correlation_analysis(data, metric1, metric2)
        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _fetch_correlation_data(self, user_id: int, metric1: str, metric2: str) -> List[Dict]:
        """Fetch data for correlation analysis."""
        cache_key = f"correlations_{user_id}_{metric1}_{metric2}"
        query = f"SELECT metric1, metric2 FROM correlations WHERE user_id = {user_id}"
        return await self.agent._fetch_clickhouse_data(query, cache_key)
        
    def _calculate_correlation_analysis(self, data: List[Dict], metric1: str, metric2: str) -> Dict[str, Any]:
        """Calculate Pearson correlation coefficient."""
        values1 = [item.get('metric1', 0) for item in data if item.get('metric1') is not None]
        values2 = [item.get('metric2', 0) for item in data if item.get('metric2') is not None]
        
        if len(values1) != len(values2) or len(values1) < 2:
            return {"status": "insufficient_data", "message": "Mismatched data"}
        
        correlation = self._compute_pearson_correlation(values1, values2)
        strength = self._determine_correlation_strength(correlation)
        
        return {
            "status": "success",
            "correlation_coefficient": correlation,
            "correlation_strength": strength,
            "data_points": len(values1),
            "metric1": metric1,
            "metric2": metric2
        }
    
    def _compute_pearson_correlation(self, values1: List[float], values2: List[float]) -> float:
        """Compute Pearson correlation coefficient."""
        n = len(values1)
        sum1, sum2 = sum(values1), sum(values2)
        sum1_sq = sum(x * x for x in values1)
        sum2_sq = sum(x * x for x in values2)
        sum_products = sum(x * y for x, y in zip(values1, values2))
        
        numerator = n * sum_products - sum1 * sum2
        denominator = ((n * sum1_sq - sum1 * sum1) * (n * sum2_sq - sum2 * sum2)) ** 0.5
        
        return numerator / denominator if denominator != 0 else 0
    
    def _determine_correlation_strength(self, correlation: float) -> str:
        """Determine correlation strength category."""
        abs_corr = abs(correlation)
        if abs_corr >= 0.7:
            return "strong"
        elif abs_corr >= 0.3:
            return "moderate"
        else:
            return "weak"