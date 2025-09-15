"""
Performance Data & Analytics Integration Tests

These tests validate real-time performance metrics collection, KPI calculations,
user engagement analysis, system performance monitoring, and revenue analytics.

Focus Areas:
- Real-time performance metrics collection and aggregation
- Business KPI calculation and tracking
- User engagement data analysis and patterns
- System performance data aggregation and monitoring
- Revenue and usage analytics processing
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import statistics
from collections import defaultdict, deque
import time

from netra_backend.app.services.billing.cost_calculator import CostCalculator, CostType
from netra_backend.app.services.billing.usage_tracker import UsageTracker, UsageType, UsageEvent
from netra_backend.app.services.quality.quality_score_calculators import QualityScoreCalculators


class PerformanceMetric:
    """Represents a performance metric data point."""
    
    def __init__(self, metric_name: str, value: float, timestamp: datetime, 
                 metadata: Dict[str, Any] = None):
        self.metric_name = metric_name
        self.value = value
        self.timestamp = timestamp
        self.metadata = metadata or {}


class RealTimeMetricsCollector:
    """Collects and aggregates real-time performance metrics."""
    
    def __init__(self, window_size: int = 100):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.aggregated_metrics: Dict[str, Dict[str, float]] = {}
        self.collection_start = datetime.now(timezone.utc)
        
    def record_metric(self, metric_name: str, value: float, 
                     metadata: Dict[str, Any] = None) -> None:
        """Record a performance metric."""
        timestamp = datetime.now(timezone.utc)
        metric = PerformanceMetric(metric_name, value, timestamp, metadata)
        self.metrics[metric_name].append(metric)
        self._update_aggregations(metric_name)
    
    def _update_aggregations(self, metric_name: str) -> None:
        """Update real-time aggregations for a metric."""
        metric_values = [m.value for m in self.metrics[metric_name]]
        
        if metric_values:
            self.aggregated_metrics[metric_name] = {
                "count": len(metric_values),
                "sum": sum(metric_values),
                "avg": statistics.mean(metric_values),
                "min": min(metric_values),
                "max": max(metric_values),
                "latest": metric_values[-1],
                "stddev": statistics.stdev(metric_values) if len(metric_values) > 1 else 0.0
            }
    
    def get_metric_summary(self, metric_name: str) -> Dict[str, Any]:
        """Get summary statistics for a specific metric."""
        return self.aggregated_metrics.get(metric_name, {})
    
    def get_all_metrics_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary for all collected metrics."""
        return self.aggregated_metrics.copy()
    
    def calculate_percentiles(self, metric_name: str, 
                            percentiles: List[float] = [50.0, 95.0, 99.0]) -> Dict[str, float]:
        """Calculate percentiles for a metric."""
        if metric_name not in self.metrics:
            return {}
        
        values = [m.value for m in self.metrics[metric_name]]
        if not values:
            return {}
        
        sorted_values = sorted(values)
        percentile_results = {}
        
        for p in percentiles:
            if p <= 0 or p >= 100:
                continue
            
            index = (len(sorted_values) - 1) * p / 100.0
            lower_index = int(index)
            upper_index = min(lower_index + 1, len(sorted_values) - 1)
            
            if lower_index == upper_index:
                percentile_value = sorted_values[lower_index]
            else:
                weight = index - lower_index
                percentile_value = (sorted_values[lower_index] * (1 - weight) + 
                                  sorted_values[upper_index] * weight)
            
            percentile_results[f"p{p}"] = percentile_value
        
        return percentile_results


class KPICalculator:
    """Calculates business Key Performance Indicators."""
    
    def __init__(self):
        self.cost_calculator = CostCalculator()
        self.usage_tracker = UsageTracker()
    
    async def calculate_customer_kpis(self, user_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate customer-related KPIs."""
        if not user_data:
            return {"error": "No user data provided"}
        
        total_users = len(user_data)
        active_users = len([u for u in user_data if u.get("last_activity_days", 999) <= 30])
        paying_users = len([u for u in user_data if u.get("monthly_cost", 0) > 0])
        
        # Calculate revenue metrics
        total_monthly_revenue = sum(u.get("monthly_cost", 0) for u in user_data)
        average_revenue_per_user = total_monthly_revenue / total_users if total_users > 0 else 0
        average_revenue_per_paying_user = (total_monthly_revenue / paying_users 
                                         if paying_users > 0 else 0)
        
        # Calculate engagement metrics
        total_usage_events = sum(u.get("usage_events", 0) for u in user_data)
        average_events_per_user = total_usage_events / active_users if active_users > 0 else 0
        
        # Calculate tier distribution
        tier_distribution = defaultdict(int)
        tier_revenue = defaultdict(float)
        
        for user in user_data:
            tier = user.get("tier", "unknown")
            tier_distribution[tier] += 1
            tier_revenue[tier] += user.get("monthly_cost", 0)
        
        return {
            "customer_metrics": {
                "total_users": total_users,
                "active_users": active_users,
                "paying_users": paying_users,
                "activation_rate": (active_users / total_users) if total_users > 0 else 0,
                "conversion_rate": (paying_users / total_users) if total_users > 0 else 0
            },
            "revenue_metrics": {
                "total_monthly_revenue": total_monthly_revenue,
                "average_revenue_per_user": average_revenue_per_user,
                "average_revenue_per_paying_user": average_revenue_per_paying_user
            },
            "engagement_metrics": {
                "total_usage_events": total_usage_events,
                "average_events_per_user": average_events_per_user
            },
            "tier_distribution": dict(tier_distribution),
            "tier_revenue": dict(tier_revenue)
        }
    
    async def calculate_operational_kpis(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate operational KPIs from performance data."""
        api_metrics = performance_data.get("api_metrics", {})
        system_metrics = performance_data.get("system_metrics", {})
        error_metrics = performance_data.get("error_metrics", {})
        
        # API Performance KPIs
        avg_response_time = api_metrics.get("avg_response_time", 0)
        request_rate = api_metrics.get("requests_per_second", 0)
        throughput_score = min(100, (request_rate / 1000) * 100) if request_rate > 0 else 0
        
        # System Health KPIs
        cpu_utilization = system_metrics.get("cpu_percent", 0)
        memory_utilization = system_metrics.get("memory_percent", 0)
        storage_utilization = system_metrics.get("storage_percent", 0)
        
        system_health_score = 100 - max(cpu_utilization, memory_utilization, storage_utilization)
        
        # Error Rate KPIs
        error_rate = error_metrics.get("error_rate", 0)
        availability = (1 - error_rate) * 100 if error_rate < 1 else 0
        
        # Overall Performance Score (composite)
        performance_score = (
            (100 - min(avg_response_time / 10, 100)) * 0.3 +  # Response time (lower is better)
            throughput_score * 0.2 +                          # Throughput
            system_health_score * 0.3 +                       # System health
            availability * 0.2                                # Availability
        )
        
        return {
            "api_performance": {
                "avg_response_time_ms": avg_response_time,
                "requests_per_second": request_rate,
                "throughput_score": throughput_score
            },
            "system_health": {
                "cpu_utilization_percent": cpu_utilization,
                "memory_utilization_percent": memory_utilization,
                "storage_utilization_percent": storage_utilization,
                "system_health_score": system_health_score
            },
            "reliability": {
                "error_rate": error_rate,
                "availability_percent": availability
            },
            "overall_performance_score": performance_score
        }


class UserEngagementAnalyzer:
    """Analyzes user engagement patterns and behavior."""
    
    def __init__(self):
        self.session_data: List[Dict[str, Any]] = []
        self.usage_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def record_user_session(self, user_id: str, session_duration: int, 
                          actions_count: int, session_type: str = "web") -> None:
        """Record a user session for engagement analysis."""
        session = {
            "user_id": user_id,
            "session_duration": session_duration,
            "actions_count": actions_count,
            "session_type": session_type,
            "timestamp": datetime.now(timezone.utc),
            "actions_per_minute": actions_count / max(session_duration / 60.0, 0.1)
        }
        
        self.session_data.append(session)
        self.usage_patterns[user_id].append(session)
    
    def analyze_engagement_patterns(self) -> Dict[str, Any]:
        """Analyze overall user engagement patterns."""
        if not self.session_data:
            return {"error": "No session data available"}
        
        # Basic engagement metrics
        total_sessions = len(self.session_data)
        unique_users = len(set(s["user_id"] for s in self.session_data))
        
        # Session duration analysis
        durations = [s["session_duration"] for s in self.session_data]
        avg_session_duration = statistics.mean(durations)
        median_session_duration = statistics.median(durations)
        
        # Actions analysis
        actions = [s["actions_count"] for s in self.session_data]
        avg_actions_per_session = statistics.mean(actions)
        
        # Session type distribution
        session_types = defaultdict(int)
        for session in self.session_data:
            session_types[session["session_type"]] += 1
        
        # Engagement intensity classification
        engagement_levels = {
            "high_engagement": 0,  # >10 actions/min and >15 min duration
            "medium_engagement": 0,  # 3-10 actions/min and 5-15 min duration
            "low_engagement": 0     # <3 actions/min or <5 min duration
        }
        
        for session in self.session_data:
            actions_per_min = session["actions_per_minute"]
            duration_min = session["session_duration"] / 60.0
            
            if actions_per_min > 10 and duration_min > 15:
                engagement_levels["high_engagement"] += 1
            elif actions_per_min >= 3 and duration_min >= 5:
                engagement_levels["medium_engagement"] += 1
            else:
                engagement_levels["low_engagement"] += 1
        
        return {
            "session_metrics": {
                "total_sessions": total_sessions,
                "unique_users": unique_users,
                "avg_sessions_per_user": total_sessions / unique_users if unique_users > 0 else 0
            },
            "duration_metrics": {
                "avg_session_duration_seconds": avg_session_duration,
                "median_session_duration_seconds": median_session_duration
            },
            "activity_metrics": {
                "avg_actions_per_session": avg_actions_per_session,
                "avg_actions_per_minute": statistics.mean([s["actions_per_minute"] 
                                                         for s in self.session_data])
            },
            "session_type_distribution": dict(session_types),
            "engagement_levels": engagement_levels
        }
    
    def identify_power_users(self, threshold_percentile: float = 80.0) -> List[Dict[str, Any]]:
        """Identify power users based on engagement metrics."""
        if not self.usage_patterns:
            return []
        
        user_metrics = []
        
        for user_id, sessions in self.usage_patterns.items():
            total_sessions = len(sessions)
            total_duration = sum(s["session_duration"] for s in sessions)
            total_actions = sum(s["actions_count"] for s in sessions)
            avg_actions_per_minute = statistics.mean([s["actions_per_minute"] for s in sessions])
            
            # Calculate engagement score
            engagement_score = (
                (total_sessions / 30) * 0.3 +  # Session frequency (normalize to monthly)
                (total_duration / 3600) * 0.3 +  # Total time spent (hours)
                (avg_actions_per_minute / 10) * 0.4  # Activity intensity
            )
            
            user_metrics.append({
                "user_id": user_id,
                "total_sessions": total_sessions,
                "total_duration_seconds": total_duration,
                "total_actions": total_actions,
                "avg_actions_per_minute": avg_actions_per_minute,
                "engagement_score": engagement_score
            })
        
        # Sort by engagement score and find threshold
        user_metrics.sort(key=lambda x: x["engagement_score"], reverse=True)
        threshold_index = int(len(user_metrics) * (100 - threshold_percentile) / 100)
        
        power_users = user_metrics[:max(threshold_index, 1)]
        
        return power_users


class TestPerformanceDataAnalytics:
    """Test suite for performance data collection and analytics processing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics_collector = RealTimeMetricsCollector(window_size=200)
        self.kpi_calculator = KPICalculator()
        self.engagement_analyzer = UserEngagementAnalyzer()
        self.cost_calculator = CostCalculator()
        self.usage_tracker = UsageTracker()
    
    def test_real_time_performance_metrics_collection(self):
        """Test real-time collection and aggregation of performance metrics."""
        # Simulate collecting various performance metrics
        test_metrics = [
            ("api_response_time", [120, 140, 95, 180, 110, 200, 85, 160]),
            ("cpu_usage", [45.5, 52.3, 38.1, 67.8, 44.2, 59.0, 41.7, 55.4]),
            ("memory_usage", [78.2, 82.5, 75.9, 88.1, 80.0, 85.3, 77.6, 83.9]),
            ("request_rate", [450, 523, 389, 678, 442, 590, 417, 554]),
            ("error_count", [2, 5, 1, 8, 3, 6, 1, 4])
        ]
        
        # Record metrics over time
        for metric_name, values in test_metrics:
            for i, value in enumerate(values):
                self.metrics_collector.record_metric(
                    metric_name, 
                    value,
                    metadata={"sequence": i, "batch": "test_batch_1"}
                )
        
        # Validate metric collection and aggregation
        all_summaries = self.metrics_collector.get_all_metrics_summary()
        
        # Should have collected all metric types
        assert len(all_summaries) == len(test_metrics)
        
        for metric_name, expected_values in test_metrics:
            summary = self.metrics_collector.get_metric_summary(metric_name)
            
            # Validate basic statistics
            assert summary["count"] == len(expected_values)
            assert abs(summary["sum"] - sum(expected_values)) < 0.01
            assert abs(summary["avg"] - statistics.mean(expected_values)) < 0.01
            assert summary["min"] == min(expected_values)
            assert summary["max"] == max(expected_values)
            assert summary["latest"] == expected_values[-1]
            
            # Validate standard deviation calculation
            expected_stddev = statistics.stdev(expected_values) if len(expected_values) > 1 else 0.0
            assert abs(summary["stddev"] - expected_stddev) < 0.01
        
        # Test percentile calculations
        api_percentiles = self.metrics_collector.calculate_percentiles("api_response_time")
        assert "p50" in api_percentiles
        assert "p95" in api_percentiles
        assert "p99" in api_percentiles
        
        # Percentiles should be in ascending order
        assert api_percentiles["p50"] <= api_percentiles["p95"] <= api_percentiles["p99"]
        
        # Validate percentile values are within expected range
        api_values = [120, 140, 95, 180, 110, 200, 85, 160]
        assert min(api_values) <= api_percentiles["p50"] <= max(api_values)
        assert min(api_values) <= api_percentiles["p95"] <= max(api_values)
    
    @pytest.mark.asyncio
    async def test_business_kpi_calculation_and_tracking(self):
        """Test calculation of business KPIs from user and revenue data."""
        # Create comprehensive user data for KPI calculation
        test_user_data = [
            # High-value enterprise users
            {"user_id": "ent_001", "tier": "enterprise", "monthly_cost": 500.0, 
             "usage_events": 15000, "last_activity_days": 1},
            {"user_id": "ent_002", "tier": "enterprise", "monthly_cost": 750.0, 
             "usage_events": 22000, "last_activity_days": 2},
            {"user_id": "ent_003", "tier": "enterprise", "monthly_cost": 650.0, 
             "usage_events": 18000, "last_activity_days": 5},
            
            # Professional users
            {"user_id": "pro_001", "tier": "professional", "monthly_cost": 150.0, 
             "usage_events": 8000, "last_activity_days": 3},
            {"user_id": "pro_002", "tier": "professional", "monthly_cost": 200.0, 
             "usage_events": 12000, "last_activity_days": 1},
            {"user_id": "pro_003", "tier": "professional", "monthly_cost": 125.0, 
             "usage_events": 6000, "last_activity_days": 15},
            {"user_id": "pro_004", "tier": "professional", "monthly_cost": 175.0, 
             "usage_events": 9500, "last_activity_days": 7},
            
            # Starter users
            {"user_id": "start_001", "tier": "starter", "monthly_cost": 25.0, 
             "usage_events": 2000, "last_activity_days": 10},
            {"user_id": "start_002", "tier": "starter", "monthly_cost": 35.0, 
             "usage_events": 3000, "last_activity_days": 5},
            {"user_id": "start_003", "tier": "starter", "monthly_cost": 15.0, 
             "usage_events": 1500, "last_activity_days": 25},
            
            # Free users
            {"user_id": "free_001", "tier": "free", "monthly_cost": 0.0, 
             "usage_events": 800, "last_activity_days": 8},
            {"user_id": "free_002", "tier": "free", "monthly_cost": 0.0, 
             "usage_events": 600, "last_activity_days": 45},
            {"user_id": "free_003", "tier": "free", "monthly_cost": 0.0, 
             "usage_events": 1200, "last_activity_days": 12}
        ]
        
        # Calculate customer KPIs
        kpis = await self.kpi_calculator.calculate_customer_kpis(test_user_data)
        
        # Validate customer metrics
        customer_metrics = kpis["customer_metrics"]
        assert customer_metrics["total_users"] == 13
        assert customer_metrics["active_users"] == 10  # last_activity_days <= 30
        assert customer_metrics["paying_users"] == 10   # monthly_cost > 0
        
        # Validate calculated rates
        expected_activation_rate = 10 / 13  # 10 active out of 13 total
        expected_conversion_rate = 10 / 13  # 10 paying out of 13 total
        assert abs(customer_metrics["activation_rate"] - expected_activation_rate) < 0.01
        assert abs(customer_metrics["conversion_rate"] - expected_conversion_rate) < 0.01
        
        # Validate revenue metrics
        revenue_metrics = kpis["revenue_metrics"]
        expected_total_revenue = sum(u["monthly_cost"] for u in test_user_data)
        expected_arpu = expected_total_revenue / 13
        expected_arppu = expected_total_revenue / 10  # Paying users only
        
        assert abs(revenue_metrics["total_monthly_revenue"] - expected_total_revenue) < 0.01
        assert abs(revenue_metrics["average_revenue_per_user"] - expected_arpu) < 0.01
        assert abs(revenue_metrics["average_revenue_per_paying_user"] - expected_arppu) < 0.01
        
        # Validate engagement metrics
        engagement_metrics = kpis["engagement_metrics"]
        expected_total_events = sum(u["usage_events"] for u in test_user_data)
        expected_avg_events = expected_total_events / 10  # Active users only
        
        assert engagement_metrics["total_usage_events"] == expected_total_events
        assert abs(engagement_metrics["average_events_per_user"] - expected_avg_events) < 0.01
        
        # Validate tier distribution
        tier_distribution = kpis["tier_distribution"]
        assert tier_distribution["enterprise"] == 3
        assert tier_distribution["professional"] == 4
        assert tier_distribution["starter"] == 3
        assert tier_distribution["free"] == 3
        
        # Validate tier revenue
        tier_revenue = kpis["tier_revenue"]
        assert tier_revenue["enterprise"] == 1900.0  # 500 + 750 + 650
        assert tier_revenue["professional"] == 650.0  # 150 + 200 + 125 + 175
        assert tier_revenue["starter"] == 75.0       # 25 + 35 + 15
        assert tier_revenue["free"] == 0.0
    
    @pytest.mark.asyncio
    async def test_operational_kpis_system_performance_monitoring(self):
        """Test operational KPI calculation from system performance data."""
        # Create realistic system performance data
        performance_data = {
            "api_metrics": {
                "avg_response_time": 145.0,  # milliseconds
                "requests_per_second": 850.0,
                "total_requests": 3060000,   # Monthly total
                "successful_requests": 3045180
            },
            "system_metrics": {
                "cpu_percent": 65.5,
                "memory_percent": 78.2,
                "storage_percent": 42.1,
                "network_io_mbps": 125.8
            },
            "error_metrics": {
                "total_errors": 14820,
                "error_rate": 0.0048,  # 0.48% error rate
                "timeout_errors": 8520,
                "server_errors": 6300
            }
        }
        
        # Calculate operational KPIs
        operational_kpis = await self.kpi_calculator.calculate_operational_kpis(performance_data)
        
        # Validate API performance KPIs
        api_performance = operational_kpis["api_performance"]
        assert api_performance["avg_response_time_ms"] == 145.0
        assert api_performance["requests_per_second"] == 850.0
        
        # Throughput score should be calculated correctly
        expected_throughput_score = min(100, (850.0 / 1000) * 100)  # 85.0
        assert abs(api_performance["throughput_score"] - expected_throughput_score) < 0.1
        
        # Validate system health KPIs
        system_health = operational_kpis["system_health"]
        assert system_health["cpu_utilization_percent"] == 65.5
        assert system_health["memory_utilization_percent"] == 78.2
        assert system_health["storage_utilization_percent"] == 42.1
        
        # System health score should be 100 - max utilization
        expected_health_score = 100 - max(65.5, 78.2, 42.1)  # 100 - 78.2 = 21.8
        assert abs(system_health["system_health_score"] - expected_health_score) < 0.1
        
        # Validate reliability KPIs
        reliability = operational_kpis["reliability"]
        assert reliability["error_rate"] == 0.0048
        expected_availability = (1 - 0.0048) * 100  # 99.52%
        assert abs(reliability["availability_percent"] - expected_availability) < 0.01
        
        # Validate overall performance score calculation
        overall_score = operational_kpis["overall_performance_score"]
        
        # Calculate expected score components
        response_time_score = 100 - min(145.0 / 10, 100)  # 100 - 14.5 = 85.5
        throughput_score = 85.0  # Calculated above
        health_score = 21.8      # Calculated above
        availability_score = 99.52  # Calculated above
        
        expected_overall = (
            response_time_score * 0.3 +
            throughput_score * 0.2 +
            health_score * 0.3 +
            availability_score * 0.2
        )
        
        assert abs(overall_score - expected_overall) < 1.0, f"Expected {expected_overall}, got {overall_score}"
    
    def test_user_engagement_data_analysis_and_patterns(self):
        """Test user engagement analysis and pattern detection."""
        # Simulate diverse user engagement patterns
        engagement_patterns = [
            # Power users - high engagement
            ("power_user_001", [(1800, 45), (2400, 60), (3000, 75), (2700, 55)]),  # Long sessions, many actions
            ("power_user_002", [(2100, 50), (2850, 70), (1950, 40), (3300, 80)]),
            
            # Regular users - moderate engagement  
            ("regular_user_001", [(900, 15), (1200, 25), (600, 10), (1500, 30)]),
            ("regular_user_002", [(750, 12), (1050, 20), (1350, 28), (900, 18)]),
            ("regular_user_003", [(1100, 22), (800, 16), (1400, 26), (950, 19)]),
            
            # Casual users - low engagement
            ("casual_user_001", [(300, 5), (450, 8), (200, 3), (600, 10)]),
            ("casual_user_002", [(250, 4), (350, 6), (180, 2), (400, 7)]),
            
            # Mobile users - different pattern (shorter sessions, fewer actions)
            ("mobile_user_001", [(600, 8), (480, 6), (720, 10), (540, 7)]),
            ("mobile_user_002", [(420, 5), (660, 9), (360, 4), (780, 11)])
        ]
        
        # Record user sessions with different types
        for user_id, sessions in engagement_patterns:
            session_type = "mobile" if "mobile" in user_id else "web"
            
            for duration, actions in sessions:
                self.engagement_analyzer.record_user_session(
                    user_id, duration, actions, session_type
                )
        
        # Analyze engagement patterns
        engagement_analysis = self.engagement_analyzer.analyze_engagement_patterns()
        
        # Validate session metrics
        session_metrics = engagement_analysis["session_metrics"]
        expected_total_sessions = sum(len(sessions) for _, sessions in engagement_patterns)
        expected_unique_users = len(engagement_patterns)
        
        assert session_metrics["total_sessions"] == expected_total_sessions
        assert session_metrics["unique_users"] == expected_unique_users
        assert abs(session_metrics["avg_sessions_per_user"] - 
                  (expected_total_sessions / expected_unique_users)) < 0.01
        
        # Validate duration metrics
        duration_metrics = engagement_analysis["duration_metrics"]
        all_durations = []
        for _, sessions in engagement_patterns:
            all_durations.extend([duration for duration, _ in sessions])
        
        expected_avg_duration = statistics.mean(all_durations)
        expected_median_duration = statistics.median(all_durations)
        
        assert abs(duration_metrics["avg_session_duration_seconds"] - expected_avg_duration) < 1.0
        assert abs(duration_metrics["median_session_duration_seconds"] - expected_median_duration) < 1.0
        
        # Validate activity metrics  
        activity_metrics = engagement_analysis["activity_metrics"]
        all_actions = []
        for _, sessions in engagement_patterns:
            all_actions.extend([actions for _, actions in sessions])
        
        expected_avg_actions = statistics.mean(all_actions)
        assert abs(activity_metrics["avg_actions_per_session"] - expected_avg_actions) < 0.1
        
        # Validate session type distribution
        session_type_dist = engagement_analysis["session_type_distribution"]
        mobile_sessions = sum(len(sessions) for user_id, sessions in engagement_patterns 
                            if "mobile" in user_id)
        web_sessions = expected_total_sessions - mobile_sessions
        
        assert session_type_dist.get("mobile", 0) == mobile_sessions
        assert session_type_dist.get("web", 0) == web_sessions
        
        # Validate engagement level classification
        engagement_levels = engagement_analysis["engagement_levels"]
        total_classified = sum(engagement_levels.values())
        assert total_classified == expected_total_sessions
        
        # Should have users in all engagement categories
        assert engagement_levels["high_engagement"] > 0, "Should identify some high-engagement sessions"
        assert engagement_levels["medium_engagement"] > 0, "Should identify some medium-engagement sessions"
        assert engagement_levels["low_engagement"] > 0, "Should identify some low-engagement sessions"
    
    def test_power_user_identification_and_segmentation(self):
        """Test identification and segmentation of power users based on engagement."""
        # Create detailed engagement data with clear power users
        user_engagement_data = [
            # Clear power users - high activity across all metrics
            ("power_user_alpha", [(3600, 120), (4200, 150), (3800, 130), (4500, 180), (3200, 110)]),
            ("power_user_beta", [(3000, 100), (3900, 140), (4100, 160), (3500, 125), (4000, 145)]),
            
            # High-frequency but shorter sessions
            ("frequent_user_001", [(1200, 40), (1500, 50), (1100, 35), (1400, 45), (1300, 42), 
                                 (1600, 55), (1000, 30), (1800, 60)]),  # 8 sessions
            
            # Long sessions but infrequent
            ("intensive_user_001", [(7200, 180), (6800, 200)]),  # 2 very long sessions
            
            # Regular users - balanced but moderate
            ("regular_user_001", [(1800, 30), (2100, 40), (1500, 25)]),
            ("regular_user_002", [(1600, 28), (1900, 35), (1400, 22), (2200, 45)]),
            
            # Low-engagement users
            ("casual_user_001", [(600, 8), (800, 12)]),
            ("casual_user_002", [(500, 6), (450, 5), (700, 10)])
        ]
        
        # Record all engagement data
        for user_id, sessions in user_engagement_data:
            for duration, actions in sessions:
                self.engagement_analyzer.record_user_session(user_id, duration, actions)
        
        # Identify power users (top 20% by engagement)
        power_users = self.engagement_analyzer.identify_power_users(threshold_percentile=80.0)
        
        # Should identify approximately 20% of users as power users
        total_users = len(user_engagement_data)
        expected_power_user_count = max(1, int(total_users * 0.2))
        
        assert len(power_users) >= expected_power_user_count, f"Expected at least {expected_power_user_count} power users"
        
        # Validate power users have high engagement scores
        if power_users:
            # Top power user should be among the clear power users
            top_power_user = power_users[0]
            assert "power_user" in top_power_user["user_id"] or "frequent_user" in top_power_user["user_id"]
            
            # Power users should have high session counts and/or high activity
            for user in power_users:
                engagement_score = user["engagement_score"]
                assert engagement_score > 0, "Power users should have positive engagement scores"
                
                # Should have meaningful activity levels
                assert (user["total_sessions"] >= 3 or 
                       user["total_duration_seconds"] >= 3600 or 
                       user["avg_actions_per_minute"] >= 5), "Power users should show high activity in at least one dimension"
        
        # Validate engagement score ranking
        engagement_scores = [user["engagement_score"] for user in power_users]
        assert engagement_scores == sorted(engagement_scores, reverse=True), "Power users should be ranked by engagement score"
        
        # Test different threshold percentiles
        top_10_percent = self.engagement_analyzer.identify_power_users(threshold_percentile=90.0)
        top_50_percent = self.engagement_analyzer.identify_power_users(threshold_percentile=50.0)
        
        assert len(top_10_percent) <= len(power_users) <= len(top_50_percent), "Different thresholds should yield different sized groups"
    
    @pytest.mark.asyncio
    async def test_revenue_and_usage_analytics_processing(self):
        """Test comprehensive revenue and usage analytics processing."""
        # Create comprehensive usage and revenue data
        test_users = [
            {"user_id": "enterprise_001", "tier": "enterprise", "region": "us-east"},
            {"user_id": "enterprise_002", "tier": "enterprise", "region": "eu-west"},
            {"user_id": "professional_001", "tier": "professional", "region": "us-west"},
            {"user_id": "professional_002", "tier": "professional", "region": "us-east"},
            {"user_id": "starter_001", "tier": "starter", "region": "us-east"},
            {"user_id": "starter_002", "tier": "starter", "region": "asia-pacific"}
        ]
        
        # Generate usage events for analytics
        usage_analytics_data = []
        total_revenue_by_user = {}
        
        for user_data in test_users:
            user_id = user_data["user_id"]
            tier = user_data["tier"]
            region = user_data["region"]
            
            # Create tier-appropriate usage patterns
            if tier == "enterprise":
                usage_patterns = [
                    (UsageType.API_CALL, 50000, 50.0),
                    (UsageType.LLM_TOKENS, 2500000, 50.0),
                    (UsageType.STORAGE, 200, 10.0),
                    (UsageType.AGENT_EXECUTION, 2000, 10.0)
                ]
            elif tier == "professional":
                usage_patterns = [
                    (UsageType.API_CALL, 20000, 20.0),
                    (UsageType.LLM_TOKENS, 800000, 16.0),
                    (UsageType.STORAGE, 50, 4.0),
                    (UsageType.AGENT_EXECUTION, 500, 2.5)
                ]
            else:  # starter
                usage_patterns = [
                    (UsageType.API_CALL, 5000, 5.0),
                    (UsageType.LLM_TOKENS, 150000, 3.0),
                    (UsageType.STORAGE, 10, 1.0),
                ]
            
            user_total_cost = 0.0
            
            # Track usage and calculate costs
            for usage_type, quantity, cost in usage_patterns:
                event = await self.usage_tracker.track_usage(
                    user_id=user_id,
                    usage_type=usage_type,
                    quantity=quantity,
                    unit="units",
                    metadata={
                        "tier": tier,
                        "region": region,
                        "analytics_test": True,
                        "cost_center": f"{tier}_operations"
                    }
                )
                
                user_total_cost += cost
            
            total_revenue_by_user[user_id] = user_total_cost
            
            # Add to analytics data
            usage_analytics_data.append({
                "user_id": user_id,
                "tier": tier,
                "region": region,
                "total_cost": user_total_cost,
                "usage_events": len(usage_patterns)
            })
        
        # Process revenue analytics
        revenue_analytics = self._process_revenue_analytics(usage_analytics_data)
        
        # Validate revenue analytics structure
        assert "total_revenue" in revenue_analytics
        assert "revenue_by_tier" in revenue_analytics
        assert "revenue_by_region" in revenue_analytics
        assert "average_revenue_per_user" in revenue_analytics
        assert "tier_performance" in revenue_analytics
        
        # Validate total revenue calculation
        expected_total_revenue = sum(total_revenue_by_user.values())
        assert abs(revenue_analytics["total_revenue"] - expected_total_revenue) < 0.01
        
        # Validate revenue by tier
        revenue_by_tier = revenue_analytics["revenue_by_tier"]
        expected_enterprise_revenue = sum(cost for user_id, cost in total_revenue_by_user.items() 
                                        if "enterprise" in user_id)
        expected_professional_revenue = sum(cost for user_id, cost in total_revenue_by_user.items() 
                                          if "professional" in user_id)
        expected_starter_revenue = sum(cost for user_id, cost in total_revenue_by_user.items() 
                                     if "starter" in user_id)
        
        assert abs(revenue_by_tier["enterprise"] - expected_enterprise_revenue) < 0.01
        assert abs(revenue_by_tier["professional"] - expected_professional_revenue) < 0.01
        assert abs(revenue_by_tier["starter"] - expected_starter_revenue) < 0.01
        
        # Validate ARPU calculation
        expected_arpu = expected_total_revenue / len(test_users)
        assert abs(revenue_analytics["average_revenue_per_user"] - expected_arpu) < 0.01
        
        # Validate tier performance analysis
        tier_performance = revenue_analytics["tier_performance"]
        for tier in ["enterprise", "professional", "starter"]:
            assert tier in tier_performance
            tier_data = tier_performance[tier]
            assert "user_count" in tier_data
            assert "total_revenue" in tier_data
            assert "average_revenue_per_user" in tier_data
            assert tier_data["user_count"] > 0
        
        # Enterprise should have highest ARPU
        enterprise_arpu = tier_performance["enterprise"]["average_revenue_per_user"]
        professional_arpu = tier_performance["professional"]["average_revenue_per_user"]
        starter_arpu = tier_performance["starter"]["average_revenue_per_user"]
        
        assert enterprise_arpu > professional_arpu > starter_arpu, "Tier ARPU should be in descending order"
    
    def _process_revenue_analytics(self, usage_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Helper method to process revenue analytics from usage data."""
        total_revenue = sum(user["total_cost"] for user in usage_data)
        total_users = len(usage_data)
        
        # Revenue by tier
        revenue_by_tier = defaultdict(float)
        users_by_tier = defaultdict(int)
        
        for user in usage_data:
            tier = user["tier"]
            cost = user["total_cost"]
            revenue_by_tier[tier] += cost
            users_by_tier[tier] += 1
        
        # Revenue by region
        revenue_by_region = defaultdict(float)
        for user in usage_data:
            region = user["region"]
            cost = user["total_cost"]
            revenue_by_region[region] += cost
        
        # Tier performance analysis
        tier_performance = {}
        for tier, total_tier_revenue in revenue_by_tier.items():
            user_count = users_by_tier[tier]
            tier_performance[tier] = {
                "user_count": user_count,
                "total_revenue": total_tier_revenue,
                "average_revenue_per_user": total_tier_revenue / user_count if user_count > 0 else 0,
                "revenue_share": (total_tier_revenue / total_revenue) * 100 if total_revenue > 0 else 0
            }
        
        return {
            "total_revenue": total_revenue,
            "revenue_by_tier": dict(revenue_by_tier),
            "revenue_by_region": dict(revenue_by_region),
            "average_revenue_per_user": total_revenue / total_users if total_users > 0 else 0,
            "tier_performance": tier_performance,
            "analytics_timestamp": datetime.now(timezone.utc).isoformat()
        }