"""Data Analysis Core - Consolidated Business Logic

Core data analysis functionality extracted from 66+ fragmented files.
Contains ONLY business logic - no infrastructure concerns.

Consolidates functionality from:
- analysis_engine.py
- performance_analyzer.py
- query_builder.py
- clickhouse_operations.py
- data_operations.py
- metrics_analyzer.py
- And many more fragmented components
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.logging_config import central_logger
from netra_backend.app.database.session_manager import DatabaseSessionManager

logger = central_logger.get_logger(__name__)


class DataAnalysisCore:
    """Core data analysis engine consolidating all business logic.
    
    Updated to use user-scoped data access patterns from UserExecutionEngine.
    Instead of direct ClickHouse service access, uses data access capabilities
    provided by UserExecutionEngine for complete user isolation.
    """
    
    def __init__(self, session_manager: DatabaseSessionManager, data_access_capabilities=None):
        """Initialize with DatabaseSessionManager and data access capabilities.
        
        Args:
            session_manager: DatabaseSessionManager for proper session isolation
            data_access_capabilities: DataAccessCapabilities from UserExecutionEngine
                                    providing user-scoped ClickHouse and Redis access
        """
        self.session_manager = session_manager
        self.data_access = data_access_capabilities
        self.cache_ttl = 300  # 5 minutes default cache
        
        # Log initialization mode
        if data_access_capabilities:
            logger.debug("DataAnalysisCore initialized with user-scoped data access capabilities")
        else:
            logger.warning("DataAnalysisCore initialized without data access capabilities - falling back to legacy mode")
        
    async def analyze_performance(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance metrics with comprehensive analysis."""
        analysis_type = request.get("type", "performance")
        timeframe = request.get("timeframe", "24h")
        metrics = request.get("metrics", ["latency_ms", "cost_cents", "throughput"])
        filters = request.get("filters", {})
        
        # Build query for performance analysis
        query = self._build_performance_query(timeframe, metrics, filters)
        
        # Fetch data with caching
        data = await self._fetch_data_with_cache(query, f"perf_{analysis_type}_{timeframe}")
        
        if not data:
            return {
                "status": "no_data",
                "message": "No performance data found for analysis",
                "data_points": 0
            }
        
        # Perform comprehensive analysis
        analysis_result = await self._perform_performance_analysis(data, request)
        
        return {
            "status": "completed",
            "analysis_type": analysis_type,
            "timeframe": timeframe,
            "data_points": len(data),
            "summary": f"Analyzed {len(data)} performance data points over {timeframe}",
            **analysis_result
        }
    
    async def analyze_trends(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends in data over time."""
        timeframe = request.get("timeframe", "7d")
        metrics = request.get("metrics", ["throughput", "latency_ms"])
        
        # Build trend analysis query
        query = self._build_trend_query(timeframe, metrics)
        data = await self._fetch_data_with_cache(query, f"trends_{timeframe}")
        
        if not data or len(data) < 3:
            return {
                "status": "insufficient_data",
                "message": "Need at least 3 data points for trend analysis",
                "trends": {}
            }
        
        # Calculate trends
        trends = self._calculate_trends(data, metrics)
        
        return {
            "status": "completed",
            "trends": trends,
            "data_points": len(data),
            "confidence": "medium" if len(data) > 10 else "low"
        }
    
    async def detect_anomalies(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies in performance data."""
        user_id = request.get("user_id")
        metric_name = request.get("metric_name", "latency_ms")
        threshold = request.get("threshold", 2.0)  # z-score threshold
        
        # Build anomaly detection query
        query = self._build_anomaly_query(user_id, metric_name)
        data = await self._fetch_data_with_cache(query, f"anomalies_{user_id}_{metric_name}")
        
        if not data or len(data) < 5:
            return {
                "status": "insufficient_data",
                "message": "Need at least 5 data points for anomaly detection",
                "anomalies": []
            }
        
        # Detect anomalies using statistical methods
        anomalies = self._detect_statistical_anomalies(data, metric_name, threshold)
        
        return {
            "status": "completed",
            "anomalies_count": len(anomalies),
            "anomaly_percentage": (len(anomalies) / len(data)) * 100,
            "anomalies": anomalies,
            "threshold": threshold
        }
    
    async def analyze_costs(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze costs and identify optimization opportunities."""
        timeframe = request.get("timeframe", "30d")
        user_id = request.get("user_id")
        
        # Build cost analysis query
        query = self._build_cost_query(user_id, timeframe)
        data = await self._fetch_data_with_cache(query, f"costs_{user_id}_{timeframe}")
        
        if not data:
            return {
                "status": "no_data", 
                "message": "No cost data found",
                "savings_potential": {}
            }
        
        # Analyze costs and calculate savings potential
        cost_analysis = self._analyze_cost_data(data)
        savings_potential = self._calculate_savings_potential(cost_analysis)
        
        return {
            "status": "completed",
            "total_cost_cents": cost_analysis.get("total_cost_cents", 0),
            "avg_daily_cost_cents": cost_analysis.get("avg_daily_cost_cents", 0),
            "savings_potential": savings_potential,
            "recommendations": self._generate_cost_recommendations(cost_analysis)
        }
    
    def _build_performance_query(self, timeframe: str, metrics: List[str], filters: Dict[str, Any]) -> str:
        """Build performance analysis query."""
        # Convert timeframe to SQL interval
        interval_map = {"1h": "1 HOUR", "24h": "1 DAY", "7d": "7 DAY", "30d": "30 DAY"}
        interval = interval_map.get(timeframe, "1 DAY")
        
        # Build SELECT clause with requested metrics
        select_fields = ["timestamp", "user_id", "workload_id"]
        for metric in metrics:
            if metric in ["latency_ms", "latency_p50", "latency_p95", "latency_p99"]:
                select_fields.extend(["latency_p50", "latency_p95", "latency_p99"])
            elif metric == "cost_cents":
                select_fields.append("cost_cents")
            elif metric == "throughput":
                select_fields.extend(["throughput", "requests_per_second"])
        
        # Remove duplicates and build query
        unique_fields = list(set(select_fields))
        fields_str = ", ".join(unique_fields)
        
        base_query = f"""
        SELECT {fields_str}
        FROM performance_metrics 
        WHERE timestamp >= NOW() - INTERVAL {interval}
        """
        
        # Add filters
        if filters.get("user_id"):
            base_query += f" AND user_id = {filters['user_id']}"
        if filters.get("workload_id"):
            base_query += f" AND workload_id = '{filters['workload_id']}'"
        
        base_query += " ORDER BY timestamp DESC LIMIT 10000"
        
        return base_query
    
    def _build_trend_query(self, timeframe: str, metrics: List[str]) -> str:
        """Build trend analysis query."""
        interval_map = {"7d": "7 DAY", "30d": "30 DAY", "90d": "90 DAY"}
        interval = interval_map.get(timeframe, "7 DAY")
        
        return f"""
        SELECT 
            timestamp,
            AVG(latency_p50) as avg_latency,
            AVG(throughput) as avg_throughput,
            AVG(cost_cents) as avg_cost,
            COUNT(*) as event_count
        FROM performance_metrics 
        WHERE timestamp >= NOW() - INTERVAL {interval}
        GROUP BY DATE(timestamp)
        ORDER BY timestamp ASC
        """
    
    def _build_anomaly_query(self, user_id: Optional[int], metric_name: str) -> str:
        """Build anomaly detection query."""
        base_query = """
        SELECT timestamp, latency_p50 as value, user_id
        FROM performance_metrics 
        WHERE timestamp >= NOW() - INTERVAL 7 DAY
        """
        
        if user_id:
            base_query += f" AND user_id = {user_id}"
        
        base_query += " ORDER BY timestamp DESC LIMIT 1000"
        return base_query
    
    def _build_cost_query(self, user_id: Optional[int], timeframe: str) -> str:
        """Build cost analysis query."""
        interval_map = {"7d": "7 DAY", "30d": "30 DAY", "90d": "90 DAY"}
        interval = interval_map.get(timeframe, "30 DAY")
        
        base_query = f"""
        SELECT 
            DATE(timestamp) as date,
            SUM(cost_cents) as daily_cost_cents,
            COUNT(*) as daily_requests,
            AVG(latency_p50) as avg_latency
        FROM performance_metrics 
        WHERE timestamp >= NOW() - INTERVAL {interval}
        """
        
        if user_id:
            base_query += f" AND user_id = {user_id}"
        
        base_query += " GROUP BY DATE(timestamp) ORDER BY date DESC"
        return base_query
    
    async def _fetch_data_with_cache(self, query: str, cache_key: str) -> List[Dict[str, Any]]:
        """Fetch data from ClickHouse using user-scoped data access capabilities."""
        try:
            if self.data_access:
                # Use user-scoped data access capabilities for complete isolation
                data = await self.data_access.execute_analytics_query(query)
                logger.debug(f"Fetched {len(data or [])} rows via user-scoped data access for cache key: {cache_key}")
                return data or []
            else:
                # Legacy fallback mode (not recommended for production)
                logger.warning(f"Using legacy ClickHouse access for {cache_key} - consider upgrading to UserExecutionEngine pattern")
                from netra_backend.app.db.clickhouse import get_clickhouse_service
                clickhouse_client = get_clickhouse_service()
                data = await clickhouse_client.execute_query(query)
                logger.debug(f"Fetched {len(data or [])} rows via legacy access for cache key: {cache_key}")
                return data or []
        except Exception as e:
            logger.error(f"ClickHouse query failed for {cache_key}: {e}")
            return []
    
    async def _perform_performance_analysis(self, data: List[Dict[str, Any]], request: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive performance analysis."""
        if not data:
            return {}
        
        # Calculate basic metrics
        latency_values = [item.get("latency_p50", 0) for item in data if item.get("latency_p50")]
        throughput_values = [item.get("throughput", 0) for item in data if item.get("throughput")]
        cost_values = [item.get("cost_cents", 0) for item in data if item.get("cost_cents")]
        
        metrics = {}
        
        if latency_values:
            metrics["latency"] = {
                "avg_latency_ms": sum(latency_values) / len(latency_values),
                "min_latency_ms": min(latency_values),
                "max_latency_ms": max(latency_values),
                "p95_latency_ms": self._calculate_percentile(latency_values, 95)
            }
        
        if throughput_values:
            metrics["throughput"] = {
                "avg_throughput": sum(throughput_values) / len(throughput_values),
                "peak_throughput": max(throughput_values) if throughput_values else 0
            }
        
        if cost_values:
            metrics["costs"] = {
                "total_cost_cents": sum(cost_values),
                "avg_cost_per_request_cents": sum(cost_values) / len(cost_values) if cost_values else 0
            }
        
        # Generate findings and recommendations
        findings = self._generate_performance_findings(metrics)
        recommendations = self._generate_performance_recommendations(metrics)
        
        return {
            "metrics": metrics,
            "findings": findings,
            "recommendations": recommendations
        }
    
    def _calculate_trends(self, data: List[Dict[str, Any]], metrics: List[str]) -> Dict[str, Any]:
        """Calculate trends for specified metrics."""
        trends = {}
        
        if len(data) < 2:
            return trends
        
        # Calculate trend for throughput
        if "throughput" in metrics:
            throughput_values = [item.get("avg_throughput", 0) for item in data]
            trends["throughput"] = self._calculate_trend_direction(throughput_values)
        
        # Calculate trend for latency
        if "latency_ms" in metrics:
            latency_values = [item.get("avg_latency", 0) for item in data]
            trends["latency"] = self._calculate_trend_direction(latency_values)
        
        return trends
    
    def _calculate_trend_direction(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend direction for a series of values."""
        if len(values) < 2:
            return {"direction": "stable", "confidence": "low"}
        
        # Simple linear trend calculation
        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
        
        change_percent = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
        
        if change_percent > 10:
            direction = "increasing"
        elif change_percent < -10:
            direction = "decreasing"
        else:
            direction = "stable"
        
        confidence = "high" if abs(change_percent) > 20 else "medium"
        
        return {
            "direction": direction,
            "change_percent": round(change_percent, 2),
            "confidence": confidence
        }
    
    def _detect_statistical_anomalies(self, data: List[Dict[str, Any]], metric_name: str, threshold: float) -> List[Dict[str, Any]]:
        """Detect anomalies using statistical methods."""
        values = [item.get("value", 0) for item in data if item.get("value") is not None]
        
        if len(values) < 3:
            return []
        
        # Calculate mean and standard deviation
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        anomalies = []
        for i, item in enumerate(data):
            value = item.get("value", 0)
            if std_dev > 0:
                z_score = abs((value - mean_val) / std_dev)
                if z_score > threshold:
                    anomalies.append({
                        "timestamp": item.get("timestamp"),
                        "value": value,
                        "z_score": round(z_score, 2),
                        "deviation_type": "high" if value > mean_val else "low"
                    })
        
        return anomalies
    
    def _analyze_cost_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cost data and extract insights."""
        if not data:
            return {}
        
        daily_costs = [item.get("daily_cost_cents", 0) for item in data]
        total_cost_cents = sum(daily_costs)
        avg_daily_cost_cents = total_cost_cents / len(daily_costs) if daily_costs else 0
        
        return {
            "total_cost_cents": total_cost_cents,
            "avg_daily_cost_cents": avg_daily_cost_cents,
            "peak_daily_cost_cents": max(daily_costs) if daily_costs else 0,
            "min_daily_cost_cents": min(daily_costs) if daily_costs else 0,
            "days_analyzed": len(data)
        }
    
    def _calculate_savings_potential(self, cost_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate potential cost savings."""
        avg_daily_cost = cost_analysis.get("avg_daily_cost_cents", 0)
        
        # Conservative savings estimates based on optimization opportunities
        optimization_savings_pct = 15  # 15% average savings through optimization
        peak_shaving_savings_pct = 8   # 8% savings through peak usage optimization
        
        total_savings_pct = optimization_savings_pct + peak_shaving_savings_pct
        potential_daily_savings = avg_daily_cost * (total_savings_pct / 100)
        potential_monthly_savings = potential_daily_savings * 30
        
        return {
            "savings_percentage": total_savings_pct,
            "potential_daily_savings_cents": round(potential_daily_savings, 2),
            "potential_monthly_savings_cents": round(potential_monthly_savings, 2),
            "total_savings_cents": potential_monthly_savings,  # For backward compatibility
            "optimization_categories": ["Resource rightsizing", "Peak usage optimization", "Query optimization"]
        }
    
    def _generate_performance_findings(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate performance analysis findings."""
        findings = []
        
        # Latency analysis
        latency_data = metrics.get("latency", {})
        if latency_data:
            avg_latency = latency_data.get("avg_latency_ms", 0)
            p95_latency = latency_data.get("p95_latency_ms", 0)
            
            if avg_latency > 500:
                findings.append(f"High average latency detected: {avg_latency:.1f}ms")
            if p95_latency > 1000:
                findings.append(f"P95 latency exceeds threshold: {p95_latency:.1f}ms")
        
        # Throughput analysis  
        throughput_data = metrics.get("throughput", {})
        if throughput_data:
            avg_throughput = throughput_data.get("avg_throughput", 0)
            if avg_throughput < 10:
                findings.append(f"Low throughput detected: {avg_throughput:.1f} req/s")
        
        # Cost analysis
        cost_data = metrics.get("costs", {})
        if cost_data:
            avg_cost_per_req = cost_data.get("avg_cost_per_request_cents", 0)
            if avg_cost_per_req > 5:
                findings.append(f"High per-request cost: ${avg_cost_per_req/100:.3f}")
        
        return findings or ["Performance metrics within normal ranges"]
    
    def _generate_performance_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Latency recommendations
        latency_data = metrics.get("latency", {})
        if latency_data and latency_data.get("avg_latency_ms", 0) > 300:
            recommendations.extend([
                "Consider query optimization to reduce latency",
                "Evaluate caching strategies for frequently accessed data",
                "Review database indexing and query patterns"
            ])
        
        # Cost recommendations
        cost_data = metrics.get("costs", {})
        if cost_data and cost_data.get("avg_cost_per_request_cents", 0) > 3:
            recommendations.extend([
                "Optimize resource allocation to reduce per-request costs",
                "Consider batch processing for better cost efficiency",
                "Review pricing tier and usage patterns"
            ])
        
        return recommendations or ["Performance appears optimized - continue monitoring"]
    
    def _generate_cost_recommendations(self, cost_analysis: Dict[str, Any]) -> List[str]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        avg_cost = cost_analysis.get("avg_daily_cost_cents", 0)
        peak_cost = cost_analysis.get("peak_daily_cost_cents", 0)
        
        if peak_cost > avg_cost * 1.5:
            recommendations.append("Consider peak usage optimization to reduce cost spikes")
        
        if avg_cost > 10000:  # $100/day
            recommendations.extend([
                "Review resource rightsizing opportunities",
                "Evaluate query optimization for cost reduction",
                "Consider reserved capacity for predictable workloads"
            ])
        
        recommendations.append("Monitor usage patterns for additional optimization opportunities")
        
        return recommendations
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value from a list of numbers."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of data analysis core."""
        return {
            "clickhouse_health": "connected" if self.clickhouse_client else "disconnected",
            "session_manager_health": "active" if self.session_manager and self.session_manager._is_active else "inactive",
            "pattern": "UserExecutionContext",
            "cache_ttl": self.cache_ttl,
            "status": "healthy"
        }