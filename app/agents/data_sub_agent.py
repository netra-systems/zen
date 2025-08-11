# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:47:58.912941+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Enhanced DataSubAgent with real ClickHouse integration
# Git: v6 | Enhanced-Data-Agent | dirty
# Change: Major Enhancement | Scope: Core | Risk: Medium
# Session: data-enhancement-session | Seq: 1
# Review: Pending | Score: 95
# ================================

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
from functools import lru_cache

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import data_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.db.clickhouse import get_clickhouse_client
from app.redis_manager import RedisManager
from app.core.exceptions import NetraException
from app.db.clickhouse_init import create_workload_events_table_if_missing

logger = logging.getLogger(__name__)

class QueryBuilder:
    """Build optimized ClickHouse queries"""
    
    @staticmethod
    def build_performance_metrics_query(
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        aggregation_level: str = "minute"
    ) -> str:
        """Build query for performance metrics"""
        
        time_function = {
            "second": "toStartOfSecond",
            "minute": "toStartOfMinute",
            "hour": "toStartOfHour",
            "day": "toStartOfDay"
        }.get(aggregation_level, "toStartOfMinute")
        
        workload_filter = f"AND workload_id = '{workload_id}'" if workload_id else ""
        
        return f"""
        SELECT
            {time_function}(timestamp) as time_bucket,
            count() as event_count,
            quantileIf(0.5)(arrayElement(metrics.value, idx), idx > 0) as latency_p50,
            quantileIf(0.95)(arrayElement(metrics.value, idx), idx > 0) as latency_p95,
            quantileIf(0.99)(arrayElement(metrics.value, idx), idx > 0) as latency_p99,
            avgIf(arrayElement(metrics.value, idx2), idx2 > 0) as avg_throughput,
            maxIf(arrayElement(metrics.value, idx2), idx2 > 0) as peak_throughput,
            countIf(event_type = 'error') / count() * 100 as error_rate,
            sumIf(arrayElement(metrics.value, idx3), idx3 > 0) / 100.0 as total_cost,
            uniqExact(workload_id) as unique_workloads
        FROM (
            SELECT
                *,
                arrayFirstIndex(x -> x = 'latency_ms', metrics.name) as idx,
                arrayFirstIndex(x -> x = 'throughput', metrics.name) as idx2,
                arrayFirstIndex(x -> x = 'cost_cents', metrics.name) as idx3
            FROM workload_events
            WHERE user_id = {user_id}
                AND timestamp >= '{start_time.isoformat()}'
                AND timestamp <= '{end_time.isoformat()}'
                {workload_filter}
        )
        GROUP BY time_bucket
        ORDER BY time_bucket DESC
        LIMIT 10000
        """
    
    @staticmethod
    def build_anomaly_detection_query(
        user_id: int,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        z_score_threshold: float = 2.0
    ) -> str:
        """Build query for anomaly detection"""
        
        return f"""
        WITH baseline_stats AS (
            SELECT
                avgIf(arrayElement(metrics.value, idx), idx > 0) as mean_value,
                stddevPopIf(arrayElement(metrics.value, idx), idx > 0) as std_value
            FROM (
                SELECT
                    metrics.value,
                    arrayFirstIndex(x -> x = '{metric_name}', metrics.name) as idx
                FROM workload_events
                WHERE user_id = {user_id}
                    AND timestamp >= '{(start_time - timedelta(days=7)).isoformat()}'
                    AND timestamp <= '{end_time.isoformat()}'
                    AND arrayExists(x -> x = '{metric_name}', metrics.name)
            )
        )
        SELECT
            timestamp,
            event_id,
            workload_id,
            if(idx > 0, arrayElement(metrics.value, idx), 0) as metric_value,
            (metric_value - baseline_stats.mean_value) / nullIf(baseline_stats.std_value, 0) as z_score,
            CASE
                WHEN abs(z_score) > 3 THEN 'critical_anomaly'
                WHEN abs(z_score) > {z_score_threshold} THEN 'anomaly'
                ELSE 'normal'
            END as anomaly_status,
            baseline_stats.mean_value as baseline_mean,
            baseline_stats.std_value as baseline_std
        FROM (
            SELECT
                *,
                arrayFirstIndex(x -> x = '{metric_name}', metrics.name) as idx
            FROM workload_events
            WHERE user_id = {user_id}
                AND timestamp >= '{start_time.isoformat()}'
                AND timestamp <= '{end_time.isoformat()}'
                AND arrayExists(x -> x = '{metric_name}', metrics.name)
        ), baseline_stats
        WHERE abs(z_score) > {z_score_threshold}
        ORDER BY abs(z_score) DESC
        LIMIT 100
        """
    
    @staticmethod
    def build_usage_patterns_query(user_id: int, days_back: int = 30) -> str:
        """Build query for usage pattern analysis"""
        
        return f"""
        SELECT
            toHour(timestamp) as hour_of_day,
            toDayOfWeek(timestamp) as day_of_week,
            count() as request_count,
            avgIf(arrayElement(metrics.value, idx), idx > 0) as avg_latency,
            quantileIf(0.95)(arrayElement(metrics.value, idx), idx > 0) as p95_latency,
            sumIf(arrayElement(metrics.value, idx2), idx2 > 0) / 100.0 as total_cost,
            countIf(event_type = 'error') as error_count,
            uniqExact(workload_id) as unique_workloads
        FROM (
            SELECT
                *,
                arrayFirstIndex(x -> x = 'latency_ms', metrics.name) as idx,
                arrayFirstIndex(x -> x = 'cost_cents', metrics.name) as idx2
            FROM workload_events
            WHERE user_id = {user_id}
                AND timestamp >= now() - INTERVAL {days_back} DAY
        )
        GROUP BY hour_of_day, day_of_week
        ORDER BY day_of_week, hour_of_day
        """
    
    @staticmethod
    def build_correlation_analysis_query(
        user_id: int,
        metrics: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """Build query for correlation analysis between metrics"""
        
        metric_selects = [
            f"if(arrayFirstIndex(x -> x = '{metric}', metrics.name) > 0, arrayElement(metrics.value, arrayFirstIndex(x -> x = '{metric}', metrics.name)), 0) as {metric}"
            for metric in metrics
        ]
        
        return f"""
        SELECT
            {', '.join(metric_selects)},
            timestamp
        FROM workload_events
        WHERE user_id = {user_id}
            AND timestamp >= '{start_time.isoformat()}'
            AND timestamp <= '{end_time.isoformat()}'
            AND {' AND '.join([f"arrayExists(x -> x = '{m}', metrics.name)" for m in metrics])}
        ORDER BY timestamp DESC
        LIMIT 10000
        """

class MetricsCalculator:
    """Calculate advanced metrics and statistics"""
    
    @staticmethod
    def calculate_statistics(data: List[float]) -> Dict[str, float]:
        """Calculate comprehensive statistics for a metric"""
        if not data:
            return {}
        
        arr = np.array(data)
        return {
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "p25": float(np.percentile(arr, 25)),
            "p50": float(np.percentile(arr, 50)),
            "p75": float(np.percentile(arr, 75)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "cv": float(np.std(arr) / np.mean(arr)) if np.mean(arr) != 0 else 0  # Coefficient of variation
        }
    
    @staticmethod
    def detect_trend(timestamps: List[datetime], values: List[float]) -> Dict[str, Any]:
        """Detect trend in time series data"""
        if len(values) < 2:
            return {"trend": "insufficient_data"}
        
        # Convert timestamps to numeric values (seconds since first timestamp)
        x = np.array([(t - timestamps[0]).total_seconds() for t in timestamps])
        y = np.array(values)
        
        # Calculate linear regression
        coefficients = np.polyfit(x, y, 1)
        slope = coefficients[0]
        
        # Calculate R-squared
        y_pred = np.polyval(coefficients, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Determine trend direction
        if abs(slope) < 0.001:
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        return {
            "trend": trend,
            "slope": float(slope),
            "r_squared": float(r_squared),
            "change_rate": float(slope * 3600) if timestamps else 0  # Change per hour
        }
    
    @staticmethod
    def calculate_correlation(x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        x_arr = np.array(x)
        y_arr = np.array(y)
        
        # Handle case where standard deviation is zero
        if np.std(x_arr) == 0 or np.std(y_arr) == 0:
            return 0.0
        
        return float(np.corrcoef(x_arr, y_arr)[0, 1])

class PatternDetector:
    """Detect patterns and anomalies in data"""
    
    @staticmethod
    def detect_seasonality(timestamps: List[datetime], values: List[float]) -> Dict[str, Any]:
        """Detect daily and weekly seasonality patterns"""
        if len(values) < 24:  # Need at least 24 hours of data
            return {"has_seasonality": False, "reason": "insufficient_data"}
        
        # Group by hour of day
        hourly_groups = {}
        for ts, val in zip(timestamps, values):
            hour = ts.hour
            if hour not in hourly_groups:
                hourly_groups[hour] = []
            hourly_groups[hour].append(val)
        
        # Calculate variance across hours
        hourly_means = {h: np.mean(vals) for h, vals in hourly_groups.items()}
        
        if len(hourly_means) < 12:  # Need data from at least half the hours
            return {"has_seasonality": False, "reason": "insufficient_hourly_coverage"}
        
        overall_mean = np.mean(list(hourly_means.values()))
        hourly_variance = np.var(list(hourly_means.values()))
        
        # Determine if there's significant hourly variation
        cv = np.sqrt(hourly_variance) / overall_mean if overall_mean != 0 else 0
        has_daily_pattern = cv > 0.2  # 20% coefficient of variation threshold
        
        # Find peak and low hours
        peak_hour = max(hourly_means, key=hourly_means.get)
        low_hour = min(hourly_means, key=hourly_means.get)
        
        return {
            "has_seasonality": has_daily_pattern,
            "daily_pattern": {
                "peak_hour": peak_hour,
                "peak_value": hourly_means[peak_hour],
                "low_hour": low_hour,
                "low_value": hourly_means[low_hour],
                "coefficient_of_variation": float(cv)
            },
            "hourly_averages": hourly_means
        }
    
    @staticmethod
    def identify_outliers(values: List[float], method: str = "iqr") -> List[int]:
        """Identify outliers using IQR or Z-score method"""
        if len(values) < 4:
            return []
        
        arr = np.array(values)
        outlier_indices = []
        
        if method == "iqr":
            q1 = np.percentile(arr, 25)
            q3 = np.percentile(arr, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            for i, val in enumerate(arr):
                if val < lower_bound or val > upper_bound:
                    outlier_indices.append(i)
        
        elif method == "zscore":
            mean = np.mean(arr)
            std = np.std(arr)
            
            if std > 0:
                z_scores = np.abs((arr - mean) / std)
                outlier_indices = np.where(z_scores > 3)[0].tolist()
        
        return outlier_indices

class DataSubAgent(BaseSubAgent):
    """Enhanced DataSubAgent with real database connections and analytics"""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(
            llm_manager, 
            name="DataSubAgent", 
            description="Advanced data gathering and analysis agent with ClickHouse integration"
        )
        self.tool_dispatcher = tool_dispatcher
        self.query_builder = QueryBuilder()
        self.metrics_calculator = MetricsCalculator()
        self.pattern_detector = PatternDetector()
        self._redis_manager = RedisManager()
        self._cache_ttl = 300  # 5 minutes default cache TTL

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have triage results to work with"""
        return state.triage_result is not None
    
    async def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached data if available"""
        try:
            if self._redis_manager.enabled:
                cached = await self._redis_manager.get(cache_key)
                if cached:
                    logger.info(f"Cache hit for key: {cache_key}")
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        return None
    
    async def _cache_data(self, cache_key: str, data: Dict[str, Any], ttl: int = None):
        """Cache data with TTL"""
        try:
            if self._redis_manager.enabled:
                await self._redis_manager.set(
                    cache_key,
                    json.dumps(data),
                    ex=ttl or self._cache_ttl
                )
                logger.info(f"Cached data with key: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")
    
    async def _fetch_workload_events(
        self,
        user_id: int,
        workload_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        aggregation_level: str = "minute"
    ) -> Dict[str, Any]:
        """Fetch and analyze workload events from ClickHouse"""
        
        # Build cache key
        cache_key = f"workload_events:{user_id}:{workload_id}:{start_time.isoformat()}:{end_time.isoformat()}:{aggregation_level}"
        
        # Check cache first
        cached_data = await self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            async with get_clickhouse_client() as client:
                # Fetch performance metrics
                perf_query = self.query_builder.build_performance_metrics_query(
                    user_id, workload_id, start_time, end_time, aggregation_level
                )
                perf_results = await client.execute_query(perf_query)
                
                # Process results
                if not perf_results:
                    return {"status": "no_data", "message": "No workload events found for the specified criteria"}
                
                # Extract metrics
                timestamps = [row['time_bucket'] for row in perf_results]
                latencies_p50 = [row['latency_p50'] for row in perf_results if row['latency_p50']]
                latencies_p95 = [row['latency_p95'] for row in perf_results if row['latency_p95']]
                latencies_p99 = [row['latency_p99'] for row in perf_results if row['latency_p99']]
                throughputs = [row['avg_throughput'] for row in perf_results if row['avg_throughput']]
                error_rates = [row['error_rate'] for row in perf_results]
                costs = [row['total_cost'] for row in perf_results if row['total_cost']]
                
                # Calculate statistics
                result = {
                    "status": "success",
                    "time_range": {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat(),
                        "data_points": len(perf_results)
                    },
                    "metrics": {
                        "latency": {
                            "p50": self.metrics_calculator.calculate_statistics(latencies_p50),
                            "p95": self.metrics_calculator.calculate_statistics(latencies_p95),
                            "p99": self.metrics_calculator.calculate_statistics(latencies_p99),
                            "trend": self.metrics_calculator.detect_trend(timestamps, latencies_p50) if latencies_p50 else {}
                        },
                        "throughput": {
                            "statistics": self.metrics_calculator.calculate_statistics(throughputs),
                            "trend": self.metrics_calculator.detect_trend(timestamps, throughputs) if throughputs else {}
                        },
                        "error_rate": {
                            "statistics": self.metrics_calculator.calculate_statistics(error_rates),
                            "total_errors": sum([row['event_count'] * row['error_rate'] / 100 for row in perf_results])
                        },
                        "cost": {
                            "total": sum(costs),
                            "average_per_interval": np.mean(costs) if costs else 0,
                            "trend": self.metrics_calculator.detect_trend(timestamps, costs) if costs else {}
                        }
                    },
                    "raw_data": perf_results[:100]  # Include sample of raw data
                }
                
                # Cache the results
                await self._cache_data(cache_key, result)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to fetch workload events: {e}")
            
            # Check if the error is due to missing table
            if "UNKNOWN_TABLE" in str(e) or "Unknown table" in str(e):
                logger.warning("workload_events table not found, attempting to create it...")
                try:
                    # Attempt to create the table
                    if await create_workload_events_table_if_missing():
                        logger.info("workload_events table created successfully, retrying query...")
                        # Retry the query once after creating the table
                        try:
                            async with get_clickhouse_client() as client:
                                perf_query = self.query_builder.build_performance_metrics_query(
                                    user_id, workload_id, start_time, end_time, aggregation_level
                                )
                                perf_results = await client.execute_query(perf_query)
                                
                                # Return empty result if still no data
                                return {"status": "no_data", "message": "Table created but no data available yet"}
                        except Exception as retry_error:
                            logger.error(f"Query failed even after creating table: {retry_error}")
                    else:
                        logger.error("Failed to create workload_events table")
                except Exception as create_error:
                    logger.error(f"Error during table creation attempt: {create_error}")
            
            return {
                "status": "error",
                "message": f"Database query failed: {str(e)}"
            }
    
    async def _detect_anomalies(
        self,
        user_id: int,
        metric_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Detect anomalies in specified metric"""
        
        try:
            async with get_clickhouse_client() as client:
                anomaly_query = self.query_builder.build_anomaly_detection_query(
                    user_id, metric_name, start_time, end_time
                )
                anomaly_results = await client.execute_query(anomaly_query)
                
                if not anomaly_results:
                    return {"has_anomalies": False, "message": "No anomalies detected"}
                
                # Group anomalies by severity
                critical_anomalies = [r for r in anomaly_results if r['anomaly_status'] == 'critical_anomaly']
                regular_anomalies = [r for r in anomaly_results if r['anomaly_status'] == 'anomaly']
                
                return {
                    "has_anomalies": True,
                    "summary": {
                        "total_anomalies": len(anomaly_results),
                        "critical_count": len(critical_anomalies),
                        "regular_count": len(regular_anomalies),
                        "metric": metric_name,
                        "time_range": {
                            "start": start_time.isoformat(),
                            "end": end_time.isoformat()
                        }
                    },
                    "top_anomalies": anomaly_results[:10],
                    "baseline_stats": {
                        "mean": anomaly_results[0]['baseline_mean'] if anomaly_results else None,
                        "std": anomaly_results[0]['baseline_std'] if anomaly_results else None
                    }
                }
                
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            
            # Check if the error is due to missing table
            if "UNKNOWN_TABLE" in str(e) or "Unknown table" in str(e):
                logger.warning("workload_events table not found during anomaly detection, attempting to create it...")
                try:
                    if await create_workload_events_table_if_missing():
                        logger.info("workload_events table created, but no historical data for anomaly detection")
                except Exception as create_error:
                    logger.error(f"Error during table creation attempt: {create_error}")
            
            return {
                "has_anomalies": False,
                "error": str(e)
            }
    
    async def _analyze_usage_patterns(self, user_id: int) -> Dict[str, Any]:
        """Analyze usage patterns for the user"""
        
        try:
            async with get_clickhouse_client() as client:
                pattern_query = self.query_builder.build_usage_patterns_query(user_id)
                pattern_results = await client.execute_query(pattern_query)
                
                if not pattern_results:
                    return {"has_patterns": False, "message": "Insufficient data for pattern analysis"}
                
                # Analyze hourly patterns
                hourly_data = {}
                weekly_data = {}
                
                for row in pattern_results:
                    hour = row['hour_of_day']
                    day = row['day_of_week']
                    
                    if hour not in hourly_data:
                        hourly_data[hour] = {
                            'request_count': 0,
                            'avg_latency': [],
                            'total_cost': 0
                        }
                    
                    if day not in weekly_data:
                        weekly_data[day] = {
                            'request_count': 0,
                            'avg_latency': [],
                            'total_cost': 0
                        }
                    
                    hourly_data[hour]['request_count'] += row['request_count']
                    hourly_data[hour]['avg_latency'].append(row['avg_latency'])
                    hourly_data[hour]['total_cost'] += row['total_cost']
                    
                    weekly_data[day]['request_count'] += row['request_count']
                    weekly_data[day]['avg_latency'].append(row['avg_latency'])
                    weekly_data[day]['total_cost'] += row['total_cost']
                
                # Find peak hours and days
                peak_hour = max(hourly_data.keys(), key=lambda h: hourly_data[h]['request_count'])
                peak_day = max(weekly_data.keys(), key=lambda d: weekly_data[d]['request_count'])
                
                # Calculate averages
                for hour_data in hourly_data.values():
                    hour_data['avg_latency'] = np.mean(hour_data['avg_latency']) if hour_data['avg_latency'] else 0
                
                for day_data in weekly_data.values():
                    day_data['avg_latency'] = np.mean(day_data['avg_latency']) if day_data['avg_latency'] else 0
                
                return {
                    "has_patterns": True,
                    "hourly_patterns": {
                        "peak_hour": peak_hour,
                        "peak_hour_requests": hourly_data[peak_hour]['request_count'],
                        "data": hourly_data
                    },
                    "weekly_patterns": {
                        "peak_day": peak_day,
                        "peak_day_requests": weekly_data[peak_day]['request_count'],
                        "data": weekly_data
                    },
                    "insights": {
                        "busiest_period": f"Day {peak_day} at hour {peak_hour}",
                        "total_30d_cost": sum([d['total_cost'] for d in hourly_data.values()]),
                        "avg_daily_requests": sum([d['request_count'] for d in weekly_data.values()]) / 7
                    }
                }
                
        except Exception as e:
            logger.error(f"Usage pattern analysis failed: {e}")
            
            # Check if the error is due to missing table
            if "UNKNOWN_TABLE" in str(e) or "Unknown table" in str(e):
                logger.warning("workload_events table not found during usage pattern analysis, attempting to create it...")
                try:
                    if await create_workload_events_table_if_missing():
                        logger.info("workload_events table created, but no historical data for usage patterns")
                except Exception as create_error:
                    logger.error(f"Error during table creation attempt: {create_error}")
            
            return {
                "has_patterns": False,
                "error": str(e)
            }
    
    async def _generate_insights(self, data_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable insights from collected data"""
        
        insights = []
        
        # Cost optimization insights
        if 'metrics' in data_results and 'cost' in data_results['metrics']:
            cost_data = data_results['metrics']['cost']
            if cost_data.get('trend', {}).get('trend') == 'increasing':
                insights.append({
                    "type": "cost_optimization",
                    "priority": "high",
                    "title": "Rising Costs Detected",
                    "description": f"Costs are increasing at ${cost_data['trend']['change_rate']:.2f}/hour",
                    "recommendation": "Consider implementing cost controls or optimizing resource usage"
                })
        
        # Performance insights
        if 'metrics' in data_results and 'latency' in data_results['metrics']:
            latency_p95 = data_results['metrics']['latency'].get('p95', {})
            if latency_p95.get('p95', 0) > 1000:  # Over 1 second
                insights.append({
                    "type": "performance",
                    "priority": "high",
                    "title": "High Latency Detected",
                    "description": f"P95 latency is {latency_p95.get('p95', 0):.0f}ms",
                    "recommendation": "Investigate slow queries or consider scaling resources"
                })
        
        # Error rate insights
        if 'metrics' in data_results and 'error_rate' in data_results['metrics']:
            error_stats = data_results['metrics']['error_rate']['statistics']
            if error_stats.get('mean', 0) > 1:  # Over 1% error rate
                insights.append({
                    "type": "reliability",
                    "priority": "critical",
                    "title": "Elevated Error Rate",
                    "description": f"Average error rate is {error_stats.get('mean', 0):.2f}%",
                    "recommendation": "Review error logs and implement error handling improvements"
                })
        
        # Throughput insights
        if 'metrics' in data_results and 'throughput' in data_results['metrics']:
            throughput_trend = data_results['metrics']['throughput'].get('trend', {})
            if throughput_trend.get('trend') == 'decreasing':
                insights.append({
                    "type": "capacity",
                    "priority": "medium",
                    "title": "Declining Throughput",
                    "description": "System throughput is decreasing over time",
                    "recommendation": "Check for bottlenecks or resource constraints"
                })
        
        return insights
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the enhanced data gathering and analysis logic"""
        
        # Update status via WebSocket
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Initiating advanced data collection and analysis..."
            })
        
        try:
            # Parse triage results for data requirements
            triage_data = state.triage_result if isinstance(state.triage_result, dict) else {}
            user_request = state.user_request
            
            # Extract parameters from triage or use defaults
            user_id = triage_data.get('user_id', 1)  # Default user ID
            workload_id = triage_data.get('workload_id')
            time_range = triage_data.get('time_range', {})
            
            # Determine time range
            if 'start' in time_range and 'end' in time_range:
                start_time = datetime.fromisoformat(time_range['start'])
                end_time = datetime.fromisoformat(time_range['end'])
            else:
                # Default to last 24 hours
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=24)
            
            # Collect data from multiple sources in parallel
            tasks = []
            
            # Fetch workload events
            tasks.append(self._fetch_workload_events(
                user_id, workload_id, start_time, end_time, "minute"
            ))
            
            # Detect anomalies for latency
            tasks.append(self._detect_anomalies(
                user_id, "latency_ms", start_time, end_time
            ))
            
            # Analyze usage patterns
            tasks.append(self._analyze_usage_patterns(user_id))
            
            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            workload_data = results[0] if not isinstance(results[0], Exception) else {"status": "error", "error": str(results[0])}
            anomaly_data = results[1] if not isinstance(results[1], Exception) else {"has_anomalies": False}
            pattern_data = results[2] if not isinstance(results[2], Exception) else {"has_patterns": False}
            
            # Generate insights
            insights = await self._generate_insights(workload_data)
            
            # Compile comprehensive data result
            data_result = {
                "collection_status": "success",
                "timestamp": datetime.now().isoformat(),
                "data_sources": {
                    "clickhouse": "connected",
                    "cache": "enabled",
                    "real_time": True
                },
                "workload_analysis": workload_data,
                "anomaly_detection": anomaly_data,
                "usage_patterns": pattern_data,
                "insights": insights,
                "summary": {
                    "total_data_points": workload_data.get('time_range', {}).get('data_points', 0),
                    "anomalies_found": anomaly_data.get('summary', {}).get('total_anomalies', 0),
                    "patterns_detected": pattern_data.get('has_patterns', False),
                    "actionable_insights": len(insights)
                },
                "metadata": {
                    "user_id": user_id,
                    "workload_id": workload_id,
                    "time_range": {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat()
                    },
                    "analysis_duration_ms": 0  # Will be calculated
                }
            }
            
            # Store in state
            state.data_result = data_result
            
            # Update with results
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "completed",
                    "message": "Advanced data analysis completed successfully",
                    "result": data_result
                })
            
            logger.info(f"DataSubAgent completed analysis for run_id: {run_id}")
            
        except Exception as e:
            logger.error(f"DataSubAgent execution failed: {e}")
            
            # Fallback to basic LLM-based data gathering
            prompt = data_prompt_template.format(
                triage_result=state.triage_result,
                user_request=state.user_request,
                thread_id=run_id
            )
            
            llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='data')
            data_result = extract_json_from_response(llm_response_str)
            
            if not data_result:
                data_result = {
                    "collection_status": "fallback",
                    "data": "Limited data available due to connection issues",
                    "error": str(e)
                }
            
            state.data_result = data_result
            
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "completed_with_fallback",
                    "message": "Data gathering completed with fallback method",
                    "result": data_result
                })