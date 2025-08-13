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
        
        start_time, end_time = time_range
        
        # Determine appropriate aggregation level based on time range
        time_diff = (end_time - start_time).total_seconds()
        if time_diff <= 3600:  # 1 hour
            aggregation = "minute"
        elif time_diff <= 86400:  # 1 day
            aggregation = "hour"
        else:
            aggregation = "day"
        
        # Build and execute query
        query = query_builder.build_performance_metrics_query(
            user_id, workload_id, start_time, end_time, aggregation
        )
        
        cache_key = f"perf_metrics:{user_id}:{workload_id}:{start_time.isoformat()}:{end_time.isoformat()}"
        data = await self.data_fetching.fetch_clickhouse_data(query, cache_key)
        
        if not data:
            return {
                "status": "no_data",
                "message": "No performance metrics found for the specified criteria"
            }
        
        # Extract metric values for analysis
        latencies = [row.get('latency_p50', 0) for row in data if row.get('latency_p50')]
        throughputs = [row.get('avg_throughput', 0) for row in data if row.get('avg_throughput')]
        error_rates = [row.get('error_rate', 0) for row in data]
        costs = [row.get('total_cost', 0) for row in data]
        
        # Perform statistical analysis
        result = {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "aggregation_level": aggregation
            },
            "summary": {
                "total_events": sum(row.get('event_count', 0) for row in data),
                "unique_workloads": max(row.get('unique_workloads', 0) for row in data),
                "total_cost": sum(costs)
            },
            "latency": analysis_engine.calculate_statistics(latencies),
            "throughput": analysis_engine.calculate_statistics(throughputs),
            "error_rate": analysis_engine.calculate_statistics(error_rates),
            "raw_data": data[:100]  # Limit raw data size
        }
        
        # Add trend analysis if enough data points
        if len(data) >= 3:
            timestamps = [datetime.fromisoformat(row['time_bucket']) for row in data]
            result["trends"] = {
                "latency": analysis_engine.detect_trend(latencies[:len(timestamps)], timestamps),
                "throughput": analysis_engine.detect_trend(throughputs[:len(timestamps)], timestamps),
                "cost": analysis_engine.detect_trend(costs, timestamps)
            }
        
        # Add seasonality detection if enough data
        if len(data) >= 24:
            timestamps = [datetime.fromisoformat(row['time_bucket']) for row in data]
            result["seasonality"] = analysis_engine.detect_seasonality(latencies[:len(timestamps)], timestamps)
        
        # Identify outliers
        outlier_indices = analysis_engine.identify_outliers(latencies)
        if outlier_indices:
            result["outliers"] = {
                "latency_outliers": [
                    {
                        "timestamp": data[i]['time_bucket'],
                        "value": latencies[i],
                        "percentile_rank": 100 * sum(1 for v in latencies if v < latencies[i]) / len(latencies)
                    }
                    for i in outlier_indices[:10]  # Limit to top 10 outliers
                ]
            }
        
        return result
    
    async def detect_anomalies(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        query_builder,
        z_score_threshold: float = 2.0
    ) -> Dict[str, Any]:
        """Detect anomalies in metric data"""
        
        start_time, end_time = time_range
        
        query = query_builder.build_anomaly_detection_query(
            user_id, metric_name, start_time, end_time, z_score_threshold
        )
        
        cache_key = f"anomalies:{user_id}:{metric_name}:{start_time.isoformat()}:{z_score_threshold}"
        data = await self.data_fetching.fetch_clickhouse_data(query, cache_key)
        
        if not data:
            return {
                "status": "no_anomalies",
                "message": f"No anomalies detected for {metric_name}",
                "threshold": z_score_threshold
            }
        
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
    
    async def analyze_correlations(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime],
        query_builder
    ) -> Dict[str, Any]:
        """Analyze correlations between multiple metrics"""
        
        if len(metrics) < 2:
            return {"error": "At least 2 metrics required for correlation analysis"}
        
        start_time, end_time = time_range
        correlations = {}
        
        # Calculate pairwise correlations
        for i in range(len(metrics)):
            for j in range(i + 1, len(metrics)):
                metric1, metric2 = metrics[i], metrics[j]
                
                query = query_builder.build_correlation_analysis_query(
                    user_id, metric1, metric2, start_time, end_time
                )
                
                data = await self.data_fetching.fetch_clickhouse_data(query)
                if data and data[0]['sample_size'] > 10:
                    corr_data = data[0]
                    correlation_key = f"{metric1}_vs_{metric2}"
                    
                    # Interpret correlation strength
                    corr_coef = corr_data['correlation_coefficient']
                    if abs(corr_coef) > 0.7:
                        strength = "strong"
                    elif abs(corr_coef) > 0.4:
                        strength = "moderate"
                    else:
                        strength = "weak"
                    
                    correlations[correlation_key] = {
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
    
    async def analyze_usage_patterns(
        self,
        user_id: int,
        query_builder,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Analyze usage patterns over time"""
        
        query = query_builder.build_usage_patterns_query(user_id, days_back)
        cache_key = f"usage_patterns:{user_id}:{days_back}"
        data = await self.data_fetching.fetch_clickhouse_data(query, cache_key)
        
        if not data:
            return {
                "status": "no_data",
                "message": "No usage data available"
            }
        
        # Aggregate by day of week and hour
        daily_patterns = {}
        hourly_patterns = {}
        
        for row in data:
            dow = row['day_of_week']
            hour = row['hour_of_day']
            
            if dow not in daily_patterns:
                daily_patterns[dow] = {
                    "total_events": 0,
                    "total_cost": 0,
                    "unique_workloads": set(),
                    "unique_models": set()
                }
            
            if hour not in hourly_patterns:
                hourly_patterns[hour] = {
                    "total_events": 0,
                    "total_cost": 0
                }
            
            daily_patterns[dow]["total_events"] += row['event_count']
            daily_patterns[dow]["total_cost"] += row['total_cost']
            
            hourly_patterns[hour]["total_events"] += row['event_count']
            hourly_patterns[hour]["total_cost"] += row['total_cost']
        
        # Find peak usage times
        peak_day = max(daily_patterns.items(), key=lambda x: x[1]["total_events"])
        peak_hour = max(hourly_patterns.items(), key=lambda x: x[1]["total_events"])
        
        # Calculate average daily cost
        total_cost = sum(d["total_cost"] for d in daily_patterns.values())
        avg_daily_cost = total_cost / days_back if days_back > 0 else 0
        
        return {
            "period": f"Last {days_back} days",
            "summary": {
                "total_cost": total_cost,
                "average_daily_cost": avg_daily_cost,
                "peak_usage_day": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][peak_day[0] - 1],
                "peak_usage_hour": f"{peak_hour[0]:02d}:00",
                "total_events": sum(d["total_events"] for d in daily_patterns.values())
            },
            "daily_patterns": {
                ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][k - 1]: v
                for k, v in daily_patterns.items()
            },
            "hourly_distribution": hourly_patterns
        }
    
