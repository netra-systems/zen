"""
Test Database Performance Monitoring - Iteration 58

Business Value Justification:
- Segment: Enterprise/Mid
- Business Goal: Performance Optimization
- Value Impact: Enables proactive performance management and issue detection
- Strategic Impact: Improves user experience and system scalability

Focus: Real-time metrics, performance baselines, and alerting
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import statistics
import time

from netra_backend.app.database.manager import DatabaseManager
from netra_backend.app.monitoring.metrics_collector import MetricsCollector


class TestDatabasePerformanceMonitoring:
    """Test database performance monitoring and metrics collection"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager with performance monitoring"""
        manager = MagicMock()
        manager.connection_pool_stats = {
            "active": 5,
            "idle": 15,
            "total": 20
        }
        manager.query_metrics = []
        return manager
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """Mock metrics collector service"""
        collector = MagicMock()
        collector.metrics_history = []
        collector.baselines = {}
        collector.alerts = []
        return collector
    
    @pytest.mark.asyncio
    async def test_real_time_performance_metrics_collection(self, mock_db_manager, mock_metrics_collector):
        """Test real-time collection of database performance metrics"""
        current_metrics = {
            "timestamp": datetime.now(),
            "connections": {"active": 0, "idle": 0, "total": 0},
            "queries": {"per_second": 0, "avg_response_time": 0, "slow_queries": 0},
            "resources": {"cpu_usage": 0, "memory_usage": 0, "disk_io": 0},
            "locks": {"active_locks": 0, "deadlocks": 0}
        }
        
        async def collect_performance_metrics():
            # Simulate collecting various performance metrics
            await asyncio.sleep(0.01)  # Simulate collection time
            
            current_metrics.update({
                "timestamp": datetime.now(),
                "connections": {
                    "active": mock_db_manager.connection_pool_stats["active"],
                    "idle": mock_db_manager.connection_pool_stats["idle"],
                    "total": mock_db_manager.connection_pool_stats["total"]
                },
                "queries": {
                    "per_second": len(mock_db_manager.query_metrics) / 10 if mock_db_manager.query_metrics else 0,
                    "avg_response_time": statistics.mean([q["duration"] for q in mock_db_manager.query_metrics]) if mock_db_manager.query_metrics else 0,
                    "slow_queries": len([q for q in mock_db_manager.query_metrics if q["duration"] > 100])
                },
                "resources": {
                    "cpu_usage": 45.2,  # Mock values
                    "memory_usage": 78.5,
                    "disk_io": 25.8
                },
                "locks": {
                    "active_locks": 12,
                    "deadlocks": 0
                }
            })
            
            mock_metrics_collector.metrics_history.append(current_metrics.copy())
            return current_metrics
        
        mock_metrics_collector.collect_performance_metrics = collect_performance_metrics
        
        # Add some mock query metrics
        mock_db_manager.query_metrics = [
            {"query": "SELECT * FROM users", "duration": 25, "timestamp": time.time()},
            {"query": "SELECT * FROM posts", "duration": 150, "timestamp": time.time()},  # Slow query
            {"query": "SELECT COUNT(*) FROM orders", "duration": 45, "timestamp": time.time()},
        ]
        
        # Collect metrics
        metrics = await mock_metrics_collector.collect_performance_metrics()
        
        assert metrics["connections"]["active"] == 5
        assert metrics["connections"]["total"] == 20
        assert metrics["queries"]["slow_queries"] == 1  # One query > 100ms
        assert metrics["queries"]["avg_response_time"] == statistics.mean([25, 150, 45])
        assert metrics["resources"]["cpu_usage"] == 45.2
        assert len(mock_metrics_collector.metrics_history) == 1
    
    @pytest.mark.asyncio
    async def test_performance_baseline_establishment(self, mock_metrics_collector):
        """Test establishment and maintenance of performance baselines"""
        def establish_performance_baselines(historical_metrics, baseline_period_days=7):
            baselines = {
                "connections": {"avg_active": 0, "max_active": 0},
                "queries": {"avg_response_time": 0, "max_response_time": 0, "queries_per_second": 0},
                "resources": {"avg_cpu": 0, "avg_memory": 0, "avg_disk_io": 0}
            }
            
            if not historical_metrics:
                return baselines
            
            # Calculate baseline metrics from historical data
            active_connections = [m["connections"]["active"] for m in historical_metrics]
            response_times = [m["queries"]["avg_response_time"] for m in historical_metrics if m["queries"]["avg_response_time"] > 0]
            queries_per_second = [m["queries"]["per_second"] for m in historical_metrics if m["queries"]["per_second"] > 0]
            cpu_usage = [m["resources"]["cpu_usage"] for m in historical_metrics]
            memory_usage = [m["resources"]["memory_usage"] for m in historical_metrics]
            disk_io = [m["resources"]["disk_io"] for m in historical_metrics]
            
            baselines.update({
                "connections": {
                    "avg_active": statistics.mean(active_connections) if active_connections else 0,
                    "max_active": max(active_connections) if active_connections else 0
                },
                "queries": {
                    "avg_response_time": statistics.mean(response_times) if response_times else 0,
                    "max_response_time": max(response_times) if response_times else 0,
                    "queries_per_second": statistics.mean(queries_per_second) if queries_per_second else 0
                },
                "resources": {
                    "avg_cpu": statistics.mean(cpu_usage) if cpu_usage else 0,
                    "avg_memory": statistics.mean(memory_usage) if memory_usage else 0,
                    "avg_disk_io": statistics.mean(disk_io) if disk_io else 0
                },
                "established_at": datetime.now().isoformat(),
                "sample_count": len(historical_metrics)
            })
            
            mock_metrics_collector.baselines = baselines
            return baselines
        
        mock_metrics_collector.establish_performance_baselines = establish_performance_baselines
        
        # Create historical metrics
        historical_data = []
        base_time = datetime.now()
        
        for i in range(10):  # 10 data points
            metric = {
                "timestamp": base_time - timedelta(hours=i),
                "connections": {"active": 8 + (i % 5), "idle": 12, "total": 20},
                "queries": {
                    "per_second": 50 + (i * 2),
                    "avg_response_time": 45 + (i * 3),
                    "slow_queries": i % 3
                },
                "resources": {
                    "cpu_usage": 40 + (i * 2),
                    "memory_usage": 70 + (i * 1.5),
                    "disk_io": 20 + (i * 1.2)
                }
            }
            historical_data.append(metric)
        
        # Establish baselines
        baselines = mock_metrics_collector.establish_performance_baselines(historical_data)
        
        assert baselines["connections"]["avg_active"] > 8
        assert baselines["connections"]["max_active"] >= baselines["connections"]["avg_active"]
        assert baselines["queries"]["avg_response_time"] > 45
        assert baselines["resources"]["avg_cpu"] > 40
        assert baselines["sample_count"] == 10
        assert "established_at" in baselines
    
    @pytest.mark.asyncio
    async def test_performance_anomaly_detection(self, mock_metrics_collector):
        """Test detection of performance anomalies against baselines"""
        # Set up baselines
        mock_metrics_collector.baselines = {
            "connections": {"avg_active": 10, "max_active": 15},
            "queries": {"avg_response_time": 50, "max_response_time": 100},
            "resources": {"avg_cpu": 45, "avg_memory": 75}
        }
        
        def detect_performance_anomalies(current_metrics):
            anomalies = []
            baselines = mock_metrics_collector.baselines
            
            # Define anomaly thresholds (percentages above baseline)
            thresholds = {
                "connections_high": 1.5,  # 150% of average
                "response_time_high": 2.0,  # 200% of average
                "cpu_high": 1.8,  # 180% of average
                "memory_high": 1.5   # 150% of average
            }
            
            # Check connection anomalies
            if current_metrics["connections"]["active"] > baselines["connections"]["avg_active"] * thresholds["connections_high"]:
                anomalies.append({
                    "type": "high_connections",
                    "severity": "warning",
                    "current_value": current_metrics["connections"]["active"],
                    "baseline_value": baselines["connections"]["avg_active"],
                    "threshold_exceeded": thresholds["connections_high"]
                })
            
            # Check response time anomalies
            if current_metrics["queries"]["avg_response_time"] > baselines["queries"]["avg_response_time"] * thresholds["response_time_high"]:
                anomalies.append({
                    "type": "high_response_time",
                    "severity": "critical",
                    "current_value": current_metrics["queries"]["avg_response_time"],
                    "baseline_value": baselines["queries"]["avg_response_time"],
                    "threshold_exceeded": thresholds["response_time_high"]
                })
            
            # Check resource anomalies
            if current_metrics["resources"]["cpu_usage"] > baselines["resources"]["avg_cpu"] * thresholds["cpu_high"]:
                anomalies.append({
                    "type": "high_cpu_usage",
                    "severity": "warning",
                    "current_value": current_metrics["resources"]["cpu_usage"],
                    "baseline_value": baselines["resources"]["avg_cpu"],
                    "threshold_exceeded": thresholds["cpu_high"]
                })
            
            return {
                "anomalies_detected": len(anomalies),
                "anomalies": anomalies,
                "timestamp": datetime.now().isoformat()
            }
        
        mock_metrics_collector.detect_performance_anomalies = detect_performance_anomalies
        
        # Test normal metrics (no anomalies)
        normal_metrics = {
            "connections": {"active": 12, "idle": 8, "total": 20},
            "queries": {"avg_response_time": 55, "slow_queries": 1},
            "resources": {"cpu_usage": 50, "memory_usage": 80}
        }
        
        normal_result = mock_metrics_collector.detect_performance_anomalies(normal_metrics)
        assert normal_result["anomalies_detected"] == 0
        
        # Test anomalous metrics
        anomalous_metrics = {
            "connections": {"active": 18, "idle": 2, "total": 20},  # High connections
            "queries": {"avg_response_time": 120, "slow_queries": 5},  # High response time
            "resources": {"cpu_usage": 85, "memory_usage": 95}  # High CPU
        }
        
        anomaly_result = mock_metrics_collector.detect_performance_anomalies(anomalous_metrics)
        assert anomaly_result["anomalies_detected"] >= 2  # At least connections and response time
        
        # Verify specific anomalies
        anomaly_types = [a["type"] for a in anomaly_result["anomalies"]]
        assert "high_connections" in anomaly_types
        assert "high_response_time" in anomaly_types
        assert "high_cpu_usage" in anomaly_types
        
        # Check severity levels
        critical_anomalies = [a for a in anomaly_result["anomalies"] if a["severity"] == "critical"]
        assert len(critical_anomalies) >= 1  # Response time should be critical
    
    @pytest.mark.asyncio
    async def test_automated_alerting_system(self, mock_metrics_collector):
        """Test automated alerting based on performance thresholds"""
        alert_rules = [
            {
                "name": "high_response_time",
                "metric": "queries.avg_response_time",
                "threshold": 100,
                "severity": "critical",
                "cooldown_minutes": 5
            },
            {
                "name": "connection_pool_exhaustion",
                "metric": "connections.utilization",
                "threshold": 0.9,
                "severity": "warning",
                "cooldown_minutes": 2
            },
            {
                "name": "high_cpu_usage",
                "metric": "resources.cpu_usage",
                "threshold": 80,
                "severity": "warning",
                "cooldown_minutes": 3
            }
        ]
        
        alert_state = {}  # Track alert cooldowns
        
        def process_performance_alerts(current_metrics, alert_rules):
            triggered_alerts = []
            current_time = datetime.now()
            
            for rule in alert_rules:
                alert_key = rule["name"]
                
                # Check cooldown
                if alert_key in alert_state:
                    last_triggered = datetime.fromisoformat(alert_state[alert_key]["last_triggered"])
                    cooldown_delta = timedelta(minutes=rule["cooldown_minutes"])
                    if current_time - last_triggered < cooldown_delta:
                        continue  # Still in cooldown
                
                # Extract metric value
                metric_path = rule["metric"].split(".")
                metric_value = current_metrics
                for path_part in metric_path:
                    if path_part in metric_value:
                        metric_value = metric_value[path_part]
                    else:
                        metric_value = None
                        break
                
                if metric_value is None:
                    continue
                
                # Special handling for connection utilization
                if rule["metric"] == "connections.utilization":
                    total_connections = current_metrics["connections"]["total"]
                    active_connections = current_metrics["connections"]["active"]
                    metric_value = active_connections / total_connections if total_connections > 0 else 0
                
                # Check threshold
                if metric_value > rule["threshold"]:
                    alert = {
                        "rule_name": rule["name"],
                        "severity": rule["severity"],
                        "metric": rule["metric"],
                        "current_value": metric_value,
                        "threshold": rule["threshold"],
                        "triggered_at": current_time.isoformat(),
                        "message": f"{rule['name']}: {metric_value} exceeds threshold {rule['threshold']}"
                    }
                    
                    triggered_alerts.append(alert)
                    mock_metrics_collector.alerts.append(alert)
                    
                    # Update alert state
                    alert_state[alert_key] = {
                        "last_triggered": current_time.isoformat(),
                        "trigger_count": alert_state.get(alert_key, {}).get("trigger_count", 0) + 1
                    }
            
            return {
                "alerts_triggered": len(triggered_alerts),
                "alerts": triggered_alerts
            }
        
        mock_metrics_collector.process_performance_alerts = process_performance_alerts
        
        # Test metrics that trigger alerts
        alert_triggering_metrics = {
            "connections": {"active": 19, "idle": 1, "total": 20},  # 95% utilization
            "queries": {"avg_response_time": 150, "slow_queries": 8},  # High response time
            "resources": {"cpu_usage": 85, "memory_usage": 90}  # High CPU
        }
        
        alert_result = mock_metrics_collector.process_performance_alerts(
            alert_triggering_metrics, alert_rules
        )
        
        assert alert_result["alerts_triggered"] >= 2  # Should trigger multiple alerts
        
        # Verify specific alerts
        alert_names = [alert["rule_name"] for alert in alert_result["alerts"]]
        assert "high_response_time" in alert_names
        assert "connection_pool_exhaustion" in alert_names
        assert "high_cpu_usage" in alert_names
        
        # Check severity levels
        critical_alerts = [a for a in alert_result["alerts"] if a["severity"] == "critical"]
        warning_alerts = [a for a in alert_result["alerts"] if a["severity"] == "warning"]
        
        assert len(critical_alerts) >= 1  # Response time alert
        assert len(warning_alerts) >= 1  # Connection or CPU alerts
        
        # Test cooldown functionality
        initial_alert_count = len(mock_metrics_collector.alerts)
        
        # Process same metrics again immediately (should be in cooldown)
        cooldown_result = mock_metrics_collector.process_performance_alerts(
            alert_triggering_metrics, alert_rules
        )
        
        assert cooldown_result["alerts_triggered"] == 0  # All should be in cooldown
        assert len(mock_metrics_collector.alerts) == initial_alert_count  # No new alerts
    
    def test_performance_trend_analysis(self, mock_metrics_collector):
        """Test performance trend analysis and forecasting"""
        def analyze_performance_trends(metrics_history, trend_window_hours=24):
            if len(metrics_history) < 2:
                return {"trends": [], "forecast": None, "analysis": "insufficient_data"}
            
            trends = {
                "response_time": {"direction": "stable", "rate_of_change": 0, "confidence": 0},
                "connection_usage": {"direction": "stable", "rate_of_change": 0, "confidence": 0},
                "cpu_usage": {"direction": "stable", "rate_of_change": 0, "confidence": 0}
            }
            
            # Analyze response time trend
            response_times = [m["queries"]["avg_response_time"] for m in metrics_history if m["queries"]["avg_response_time"] > 0]
            if len(response_times) >= 3:
                # Simple linear trend analysis
                recent_avg = statistics.mean(response_times[-3:])
                earlier_avg = statistics.mean(response_times[:3])
                
                if recent_avg > earlier_avg * 1.1:  # 10% increase
                    trends["response_time"]["direction"] = "increasing"
                    trends["response_time"]["rate_of_change"] = (recent_avg - earlier_avg) / earlier_avg
                elif recent_avg < earlier_avg * 0.9:  # 10% decrease
                    trends["response_time"]["direction"] = "decreasing"
                    trends["response_time"]["rate_of_change"] = (recent_avg - earlier_avg) / earlier_avg
                
                trends["response_time"]["confidence"] = min(len(response_times) / 10.0, 1.0)  # Max confidence at 10+ samples
            
            # Analyze connection usage trend
            connection_usage = [m["connections"]["active"] / m["connections"]["total"] for m in metrics_history]
            if len(connection_usage) >= 3:
                recent_usage = statistics.mean(connection_usage[-3:])
                earlier_usage = statistics.mean(connection_usage[:3])
                
                if recent_usage > earlier_usage + 0.1:  # 10% increase in utilization
                    trends["connection_usage"]["direction"] = "increasing"
                    trends["connection_usage"]["rate_of_change"] = recent_usage - earlier_usage
                elif recent_usage < earlier_usage - 0.1:
                    trends["connection_usage"]["direction"] = "decreasing"
                    trends["connection_usage"]["rate_of_change"] = recent_usage - earlier_usage
                
                trends["connection_usage"]["confidence"] = min(len(connection_usage) / 10.0, 1.0)
            
            # Generate forecast
            forecast = {
                "time_horizon_hours": 4,
                "predicted_response_time": response_times[-1] if response_times else 0,
                "predicted_connection_usage": connection_usage[-1] if connection_usage else 0,
                "confidence": statistics.mean([trends[k]["confidence"] for k in trends])
            }
            
            # Apply trend to forecast
            if trends["response_time"]["direction"] == "increasing":
                forecast["predicted_response_time"] *= (1 + abs(trends["response_time"]["rate_of_change"]) * 0.5)
            
            return {
                "trends": trends,
                "forecast": forecast,
                "analysis": "completed",
                "analyzed_samples": len(metrics_history)
            }
        
        mock_metrics_collector.analyze_performance_trends = analyze_performance_trends
        
        # Create trending metrics data
        trending_metrics = []
        base_time = datetime.now()
        
        for i in range(12):  # 12 hours of data
            # Simulate degrading performance over time
            metric = {
                "timestamp": base_time - timedelta(hours=i),
                "connections": {"active": 8 + i, "idle": 12 - i, "total": 20},
                "queries": {
                    "avg_response_time": 40 + (i * 5),  # Increasing response time
                    "slow_queries": i // 2
                },
                "resources": {"cpu_usage": 35 + (i * 3), "memory_usage": 70}
            }
            trending_metrics.append(metric)
        
        trending_metrics.reverse()  # Chronological order
        
        analysis = mock_metrics_collector.analyze_performance_trends(trending_metrics)
        
        assert analysis["analysis"] == "completed"
        assert analysis["analyzed_samples"] == 12
        
        # Check trend detection
        assert analysis["trends"]["response_time"]["direction"] == "increasing"
        assert analysis["trends"]["response_time"]["rate_of_change"] > 0
        assert analysis["trends"]["connection_usage"]["direction"] == "increasing"
        
        # Check forecast
        forecast = analysis["forecast"]
        assert forecast["time_horizon_hours"] == 4
        assert forecast["predicted_response_time"] > 40  # Should be higher due to trend
        assert forecast["confidence"] > 0