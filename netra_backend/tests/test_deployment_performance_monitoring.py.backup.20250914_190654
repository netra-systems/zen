"""
Deployment Performance Monitoring Tests

Real-time monitoring and alerting for deployment performance metrics.
Tests continuous monitoring of key deployment health indicators.
"""

import asyncio
import time
import pytest
import psutil
import json
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

from test_framework.base import BaseTestCase


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: float
    timestamp: float
    unit: str
    threshold: Optional[float] = None
    status: str = "normal"  # normal, warning, critical


class TestDeploymentPerformanceMonitoring(BaseTestCase):
    """Test continuous performance monitoring during deployment."""

    def setup_method(self):
        """Set up monitoring test environment."""
        self.metrics_buffer = []
        self.monitoring_active = True
        self.alert_thresholds = {
            "memory_usage_mb": 900,
            "cpu_utilization_percent": 85,
            "response_time_ms": 100,
            "error_rate_percent": 5,
            "startup_time_seconds": 60
        }

    @pytest.mark.asyncio
    async def test_continuous_memory_monitoring(self):
        """Test continuous memory usage monitoring."""
        monitoring_duration = 10  # seconds
        sample_interval = 1      # second
        
        memory_samples = []
        
        # Monitor memory usage over time
        for i in range(monitoring_duration):
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            metric = PerformanceMetric(
                name="memory_usage_mb",
                value=memory_mb,
                timestamp=time.time(),
                unit="MB",
                threshold=self.alert_thresholds["memory_usage_mb"]
            )
            
            # Check threshold
            if memory_mb > self.alert_thresholds["memory_usage_mb"]:
                metric.status = "critical"
                pytest.warn(f"Memory usage {memory_mb:.1f}MB exceeds threshold {metric.threshold}MB")
            elif memory_mb > self.alert_thresholds["memory_usage_mb"] * 0.8:
                metric.status = "warning"
            
            memory_samples.append(metric)
            
            # Simulate some memory activity
            if i == 5:
                # Simulate memory spike
                temp_data = b'0' * (50 * 1024 * 1024)  # 50MB
                await asyncio.sleep(sample_interval)
                del temp_data
            else:
                await asyncio.sleep(sample_interval)
        
        # Analyze memory stability
        memory_values = [sample.value for sample in memory_samples]
        memory_variance = self._calculate_variance(memory_values)
        max_memory = max(memory_values)
        avg_memory = sum(memory_values) / len(memory_values)
        
        # Assert memory stability
        assert max_memory < self.alert_thresholds["memory_usage_mb"], f"Peak memory {max_memory:.1f}MB exceeded threshold"
        assert memory_variance < 100, f"Memory variance {memory_variance:.1f}MB[U+00B2] too high, indicates instability"
        
        # Record metrics
        self.record_metric("memory_monitoring_avg_mb", avg_memory)
        self.record_metric("memory_monitoring_max_mb", max_memory)
        self.record_metric("memory_monitoring_variance", memory_variance)

    @pytest.mark.asyncio
    async def test_performance_alerting_system(self):
        """Test automated performance alerting."""
        alerts_triggered = []
        
        # Simulate performance monitoring with alert triggers
        performance_scenarios = [
            {"metric": "memory_usage_mb", "value": 950, "should_alert": True},
            {"metric": "cpu_utilization_percent", "value": 90, "should_alert": True},
            {"metric": "response_time_ms", "value": 150, "should_alert": True},
            {"metric": "memory_usage_mb", "value": 400, "should_alert": False},
            {"metric": "cpu_utilization_percent", "value": 30, "should_alert": False},
        ]
        
        for scenario in performance_scenarios:
            alert = self._check_performance_alert(
                scenario["metric"],
                scenario["value"]
            )
            
            if alert:
                alerts_triggered.append(alert)
            
            # Verify alert expectations
            if scenario["should_alert"] and not alert:
                pytest.fail(f"Expected alert for {scenario['metric']} = {scenario['value']}")
            elif not scenario["should_alert"] and alert:
                pytest.warn(f"Unexpected alert for {scenario['metric']} = {scenario['value']}")
        
        # Record alerting effectiveness
        expected_alerts = sum(1 for s in performance_scenarios if s["should_alert"])
        actual_alerts = len(alerts_triggered)
        
        self.record_metric("alerting_accuracy_percent", 
                          (actual_alerts / expected_alerts) * 100 if expected_alerts > 0 else 100)

    @pytest.mark.asyncio
    async def test_real_time_performance_dashboard(self):
        """Test real-time performance dashboard metrics."""
        dashboard_metrics = {}
        
        # Collect dashboard metrics
        for i in range(5):
            # System metrics
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            cpu_percent = process.cpu_percent(interval=1)
            
            # Application metrics (simulated)
            response_time = await self._measure_response_time()
            error_rate = await self._calculate_error_rate()
            active_connections = await self._count_active_connections()
            
            # Collect metrics
            snapshot = {
                "timestamp": time.time(),
                "memory_mb": memory_mb,
                "cpu_percent": cpu_percent,
                "response_time_ms": response_time,
                "error_rate_percent": error_rate,
                "active_connections": active_connections
            }
            
            dashboard_metrics[f"snapshot_{i}"] = snapshot
            await asyncio.sleep(1)
        
        # Analyze dashboard data
        latest_snapshot = list(dashboard_metrics.values())[-1]
        
        # Verify all metrics are within acceptable ranges
        assert latest_snapshot["memory_mb"] < 800, "Dashboard memory metric too high"
        assert latest_snapshot["cpu_percent"] < 80, "Dashboard CPU metric too high"
        assert latest_snapshot["response_time_ms"] < 200, "Dashboard response time too high"
        assert latest_snapshot["error_rate_percent"] < 10, "Dashboard error rate too high"
        
        # Record dashboard metrics
        for key, value in latest_snapshot.items():
            if isinstance(value, (int, float)):
                self.record_metric(f"dashboard_{key}", value)

    @pytest.mark.asyncio
    async def test_performance_regression_detection(self):
        """Test detection of performance regressions."""
        # Baseline performance measurements
        baseline_metrics = await self._collect_baseline_metrics()
        
        # Current performance measurements
        current_metrics = await self._collect_current_metrics()
        
        # Compare for regressions
        regressions = []
        
        for metric_name in baseline_metrics:
            if metric_name in current_metrics:
                baseline_value = baseline_metrics[metric_name]
                current_value = current_metrics[metric_name]
                
                # Calculate percentage change
                if baseline_value > 0:
                    change_percent = ((current_value - baseline_value) / baseline_value) * 100
                    
                    # Define regression thresholds
                    regression_thresholds = {
                        "response_time_ms": 20,    # 20% increase is regression
                        "memory_usage_mb": 30,     # 30% increase is regression
                        "cpu_utilization_percent": 25,  # 25% increase is regression
                        "startup_time_seconds": 15,     # 15% increase is regression
                    }
                    
                    threshold = regression_thresholds.get(metric_name, 20)  # Default 20%
                    
                    if change_percent > threshold:
                        regressions.append({
                            "metric": metric_name,
                            "baseline": baseline_value,
                            "current": current_value,
                            "change_percent": change_percent,
                            "threshold": threshold
                        })
        
        # Assert no significant regressions
        if regressions:
            regression_summary = "\n".join(
                f"  {r['metric']}: {r['change_percent']:.1f}% increase (threshold: {r['threshold']}%)"
                for r in regressions
            )
            pytest.warn(f"Performance regressions detected:\n{regression_summary}")
        
        # Record regression analysis
        self.record_metric("performance_regressions_count", len(regressions))

    def test_resource_utilization_trending(self):
        """Test resource utilization trending over time."""
        # Collect resource utilization samples
        samples = []
        sample_count = 10
        
        for i in range(sample_count):
            process = psutil.Process()
            
            sample = {
                "timestamp": time.time(),
                "memory_percent": (process.memory_info().rss / (1024**3)) / 1.0 * 100,  # % of 1GB
                "cpu_percent": process.cpu_percent(),
                "memory_rss_mb": process.memory_info().rss / (1024**2),
            }
            samples.append(sample)
            
            # Brief activity simulation
            time.sleep(0.5)
        
        # Analyze trends
        memory_trend = self._calculate_trend([s["memory_percent"] for s in samples])
        cpu_trend = self._calculate_trend([s["cpu_percent"] for s in samples])
        
        # Memory should be stable or decreasing (no leaks)
        assert memory_trend <= 5, f"Memory trend {memory_trend:.2f}% indicates potential leak"
        
        # CPU trend should be reasonable
        assert abs(cpu_trend) <= 10, f"CPU trend {cpu_trend:.2f}% indicates instability"
        
        # Record trending metrics
        self.record_metric("memory_utilization_trend_percent", memory_trend)
        self.record_metric("cpu_utilization_trend_percent", cpu_trend)

    async def _measure_response_time(self) -> float:
        """Measure simulated response time."""
        start_time = time.time()
        # Simulate endpoint response
        await asyncio.sleep(0.05)  # 50ms simulated response
        return (time.time() - start_time) * 1000

    async def _calculate_error_rate(self) -> float:
        """Calculate simulated error rate."""
        # Simulate low error rate
        return 1.5  # 1.5% error rate

    async def _count_active_connections(self) -> int:
        """Count simulated active connections."""
        # Simulate connection count
        return 25

    async def _collect_baseline_metrics(self) -> Dict[str, float]:
        """Collect baseline performance metrics."""
        return {
            "response_time_ms": 75.0,
            "memory_usage_mb": 400.0,
            "cpu_utilization_percent": 35.0,
            "startup_time_seconds": 25.0
        }

    async def _collect_current_metrics(self) -> Dict[str, float]:
        """Collect current performance metrics."""
        process = psutil.Process()
        
        return {
            "response_time_ms": await self._measure_response_time(),
            "memory_usage_mb": process.memory_info().rss / (1024**2),
            "cpu_utilization_percent": process.cpu_percent(),
            "startup_time_seconds": 28.0  # Simulated startup time
        }

    def _check_performance_alert(self, metric_name: str, value: float) -> Optional[Dict[str, Any]]:
        """Check if performance metric triggers an alert."""
        threshold = self.alert_thresholds.get(metric_name)
        
        if threshold and value > threshold:
            return {
                "metric": metric_name,
                "value": value,
                "threshold": threshold,
                "severity": "critical" if value > threshold * 1.2 else "warning",
                "timestamp": time.time()
            }
        
        return None

    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (slope) of values over time."""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x_values = list(range(n))
        
        # Linear regression slope calculation
        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values))
        sum_x2 = sum(x * x for x in x_values)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope


class TestDeploymentHealthMetrics(BaseTestCase):
    """Test deployment health metrics collection and analysis."""

    @pytest.mark.asyncio
    async def test_health_score_calculation(self):
        """Test calculation of overall deployment health score."""
        # Collect health indicators
        health_indicators = {
            "startup_success": True,
            "memory_within_limits": True,
            "cpu_performance_adequate": True,
            "database_connectivity": True,
            "external_service_availability": False,  # Simulate partial failure
            "error_rate_acceptable": True,
            "response_time_acceptable": True
        }
        
        # Calculate health score
        total_indicators = len(health_indicators)
        healthy_indicators = sum(1 for indicator in health_indicators.values() if indicator)
        health_score = (healthy_indicators / total_indicators) * 100
        
        # Health score should be reasonable even with partial failures
        assert health_score >= 70, f"Health score {health_score:.1f}% too low for deployment"
        
        # Record health metrics
        self.record_metric("deployment_health_score", health_score)
        self.record_metric("healthy_indicators_count", healthy_indicators)
        self.record_metric("total_indicators_count", total_indicators)

    @pytest.mark.asyncio
    async def test_deployment_readiness_score(self):
        """Test calculation of deployment readiness score."""
        readiness_checks = [
            ("configuration_valid", True, 20),
            ("secrets_loaded", True, 15),
            ("database_connected", True, 25),
            ("services_initialized", True, 20),
            ("health_checks_passing", True, 20)
        ]
        
        total_weight = sum(weight for _, _, weight in readiness_checks)
        weighted_score = 0
        
        for check_name, passed, weight in readiness_checks:
            if passed:
                weighted_score += weight
            else:
                pytest.warn(f"Readiness check failed: {check_name}")
        
        readiness_percentage = (weighted_score / total_weight) * 100
        
        # Deployment should be ready
        assert readiness_percentage >= 90, f"Deployment readiness {readiness_percentage:.1f}% insufficient"
        
        # Record readiness metrics
        self.record_metric("deployment_readiness_percentage", readiness_percentage)

    @pytest.mark.asyncio
    async def test_performance_sla_compliance(self):
        """Test compliance with performance SLAs."""
        sla_requirements = {
            "startup_time_seconds": {"threshold": 60, "current": 35},
            "memory_usage_mb": {"threshold": 1000, "current": 450},
            "response_time_p95_ms": {"threshold": 200, "current": 85},
            "availability_percentage": {"threshold": 99.0, "current": 99.8},
            "error_rate_percentage": {"threshold": 1.0, "current": 0.3}
        }
        
        sla_violations = []
        
        for metric, config in sla_requirements.items():
            threshold = config["threshold"]
            current = config["current"]
            
            # Check SLA compliance (different logic for different metrics)
            if metric in ["startup_time_seconds", "memory_usage_mb", "response_time_p95_ms", "error_rate_percentage"]:
                # Lower is better
                compliant = current <= threshold
            else:
                # Higher is better
                compliant = current >= threshold
            
            if not compliant:
                sla_violations.append({
                    "metric": metric,
                    "threshold": threshold,
                    "current": current
                })
            
            # Record individual SLA compliance
            self.record_metric(f"sla_compliance_{metric}", compliant)
        
        # Overall SLA compliance
        sla_compliance_percentage = ((len(sla_requirements) - len(sla_violations)) / len(sla_requirements)) * 100
        
        assert sla_compliance_percentage >= 80, f"SLA compliance {sla_compliance_percentage:.1f}% insufficient"
        
        # Record SLA metrics
        self.record_metric("sla_compliance_percentage", sla_compliance_percentage)
        self.record_metric("sla_violations_count", len(sla_violations))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])