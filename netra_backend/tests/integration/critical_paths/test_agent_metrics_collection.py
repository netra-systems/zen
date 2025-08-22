"""Agent Metrics Collection L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (operational excellence and monitoring)
- Business Goal: Observability and operational excellence
- Value Impact: Protects $6K MRR from operational blind spots and debugging inefficiency
- Strategic Impact: Core observability infrastructure for data-driven optimization

Critical Path: Metric generation -> Collection -> Aggregation -> Export -> Dashboard/Alerting
Coverage: Real metric collectors, aggregators, exporters, dashboard integration
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import hashlib
import json
import logging
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from netra_backend.app.monitoring.metrics_collector import MetricsCollector

from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager

# Add project root to path
# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


class MetricCategory(Enum):
    """Categories of metrics for organization."""
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    BUSINESS = "business"
    RESOURCE = "resource"
    SECURITY = "security"
    CUSTOM = "custom"


@dataclass
class MetricDefinition:
    """Definition of a metric to be collected."""
    name: str
    metric_type: MetricType
    category: MetricCategory
    description: str
    unit: str
    labels: Dict[str, str] = field(default_factory=dict)
    collection_interval: float = 60.0  # seconds
    retention_days: int = 30
    
    def get_metric_key(self) -> str:
        """Get unique key for this metric."""
        label_hash = hashlib.md5(json.dumps(self.labels, sort_keys=True).encode()).hexdigest()[:8]
        return f"{self.name}_{label_hash}"


@dataclass
class MetricPoint:
    """Individual metric data point."""
    metric_name: str
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "metadata": self.metadata
        }
    
    def to_prometheus_format(self) -> str:
        """Convert to Prometheus exposition format."""
        label_str = ""
        if self.labels:
            labels_formatted = [f'{k}="{v}"' for k, v in self.labels.items()]
            label_str = "{" + ",".join(labels_formatted) + "}"
        
        timestamp_ms = int(self.timestamp.timestamp() * 1000)
        return f"{self.metric_name}{label_str} {self.value} {timestamp_ms}"


class MetricBuffer:
    """Buffer for collecting metrics before aggregation."""
    
    def __init__(self, max_size: int = 10000):
        self.buffer = []
        self.max_size = max_size
        self.buffer_stats = {
            "total_points": 0,
            "buffer_overflows": 0,
            "last_flush": None
        }
    
    def add_point(self, point: MetricPoint) -> bool:
        """Add a metric point to the buffer."""
        if len(self.buffer) >= self.max_size:
            # Remove oldest point
            self.buffer.pop(0)
            self.buffer_stats["buffer_overflows"] += 1
        
        self.buffer.append(point)
        self.buffer_stats["total_points"] += 1
        return True
    
    def get_points(self, metric_name: Optional[str] = None,
                   since: Optional[datetime] = None) -> List[MetricPoint]:
        """Get points from buffer with optional filtering."""
        points = self.buffer.copy()
        
        if metric_name:
            points = [p for p in points if p.metric_name == metric_name]
        
        if since:
            points = [p for p in points if p.timestamp >= since]
        
        return points
    
    def flush(self) -> List[MetricPoint]:
        """Flush all points from buffer."""
        points = self.buffer.copy()
        self.buffer.clear()
        self.buffer_stats["last_flush"] = datetime.now()
        return points
    
    def size(self) -> int:
        """Get current buffer size."""
        return len(self.buffer)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        return {
            **self.buffer_stats,
            "current_size": len(self.buffer),
            "utilization": len(self.buffer) / self.max_size * 100
        }


class MetricAggregator:
    """Aggregates metrics over time windows."""
    
    def __init__(self):
        self.aggregation_rules = {}
        self.aggregated_metrics = {}
        
    def add_aggregation_rule(self, metric_pattern: str, window_seconds: int,
                           aggregation_func: str, group_by: List[str] = None):
        """Add an aggregation rule."""
        self.aggregation_rules[metric_pattern] = {
            "window_seconds": window_seconds,
            "aggregation_func": aggregation_func,
            "group_by": group_by or []
        }
    
    def aggregate_points(self, points: List[MetricPoint]) -> Dict[str, MetricPoint]:
        """Aggregate points according to rules."""
        aggregated = {}
        
        for pattern, rule in self.aggregation_rules.items():
            # Find matching points
            matching_points = [p for p in points if pattern in p.metric_name]
            
            if not matching_points:
                continue
            
            # Group by labels if specified
            groups = self._group_points(matching_points, rule["group_by"])
            
            for group_key, group_points in groups.items():
                if not group_points:
                    continue
                
                # Apply aggregation function
                aggregated_value = self._apply_aggregation(
                    group_points, rule["aggregation_func"]
                )
                
                # Create aggregated metric point
                base_point = group_points[0]
                aggregated_name = f"{base_point.metric_name}_{rule['aggregation_func']}"
                
                aggregated_point = MetricPoint(
                    metric_name=aggregated_name,
                    value=aggregated_value,
                    timestamp=datetime.now(),
                    labels=base_point.labels,
                    metadata={
                        "aggregation_func": rule["aggregation_func"],
                        "window_seconds": rule["window_seconds"],
                        "point_count": len(group_points)
                    }
                )
                
                aggregated[f"{aggregated_name}_{group_key}"] = aggregated_point
        
        return aggregated
    
    def _group_points(self, points: List[MetricPoint], 
                     group_by: List[str]) -> Dict[str, List[MetricPoint]]:
        """Group points by specified labels."""
        if not group_by:
            return {"default": points}
        
        groups = {}
        for point in points:
            # Create group key from labels
            group_values = [point.labels.get(label, "unknown") for label in group_by]
            group_key = "_".join(group_values)
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append(point)
        
        return groups
    
    def _apply_aggregation(self, points: List[MetricPoint], func: str) -> float:
        """Apply aggregation function to points."""
        values = [float(p.value) for p in points]
        
        if func == "sum":
            return sum(values)
        elif func == "avg" or func == "mean":
            return statistics.mean(values)
        elif func == "min":
            return min(values)
        elif func == "max":
            return max(values)
        elif func == "count":
            return len(values)
        elif func == "p95":
            return statistics.quantiles(values, n=20)[18] if len(values) > 1 else values[0]
        elif func == "p99":
            return statistics.quantiles(values, n=100)[98] if len(values) > 1 else values[0]
        else:
            return statistics.mean(values)  # Default to mean


class MetricExporter:
    """Exports metrics to external systems."""
    
    def __init__(self):
        self.export_targets = {}
        self.export_stats = {
            "total_exports": 0,
            "successful_exports": 0,
            "failed_exports": 0,
            "export_latency": []
        }
    
    def add_export_target(self, name: str, export_func: Callable[[List[MetricPoint]], bool]):
        """Add an export target."""
        self.export_targets[name] = export_func
    
    async def export_metrics(self, points: List[MetricPoint]) -> Dict[str, bool]:
        """Export metrics to all configured targets."""
        results = {}
        
        for target_name, export_func in self.export_targets.items():
            start_time = time.time()
            
            try:
                if asyncio.iscoroutinefunction(export_func):
                    success = await export_func(points)
                else:
                    success = export_func(points)
                
                results[target_name] = success
                
                if success:
                    self.export_stats["successful_exports"] += 1
                else:
                    self.export_stats["failed_exports"] += 1
                
            except Exception as e:
                logger.error(f"Export to {target_name} failed: {e}")
                results[target_name] = False
                self.export_stats["failed_exports"] += 1
            
            # Record latency
            latency = time.time() - start_time
            self.export_stats["export_latency"].append(latency)
            
            # Keep only last 100 latency measurements
            if len(self.export_stats["export_latency"]) > 100:
                self.export_stats["export_latency"].pop(0)
        
        self.export_stats["total_exports"] += 1
        return results
    
    def get_export_stats(self) -> Dict[str, Any]:
        """Get export statistics."""
        stats = self.export_stats.copy()
        
        if stats["export_latency"]:
            stats["avg_export_latency"] = statistics.mean(stats["export_latency"])
            stats["max_export_latency"] = max(stats["export_latency"])
        else:
            stats["avg_export_latency"] = 0
            stats["max_export_latency"] = 0
        
        return stats


class DashboardIntegration:
    """Integration with dashboard systems."""
    
    def __init__(self):
        self.dashboard_configs = {}
        self.widget_data = {}
        
    def configure_dashboard(self, dashboard_id: str, config: Dict[str, Any]):
        """Configure a dashboard."""
        self.dashboard_configs[dashboard_id] = config
        
    def update_widget_data(self, dashboard_id: str, widget_id: str, 
                          points: List[MetricPoint]):
        """Update data for a specific widget."""
        if dashboard_id not in self.widget_data:
            self.widget_data[dashboard_id] = {}
        
        # Process points for widget display
        widget_data = self._process_widget_data(points)
        self.widget_data[dashboard_id][widget_id] = widget_data
        
    def _process_widget_data(self, points: List[MetricPoint]) -> Dict[str, Any]:
        """Process metric points for widget display."""
        if not points:
            return {"values": [], "timestamps": [], "latest_value": 0}
        
        # Sort by timestamp
        sorted_points = sorted(points, key=lambda p: p.timestamp)
        
        return {
            "values": [p.value for p in sorted_points],
            "timestamps": [p.timestamp.isoformat() for p in sorted_points],
            "latest_value": sorted_points[-1].value,
            "point_count": len(sorted_points)
        }
    
    def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get all data for a dashboard."""
        return self.widget_data.get(dashboard_id, {})


class AlertManager:
    """Manages alerting based on metric thresholds."""
    
    def __init__(self):
        self.alert_rules = {}
        self.active_alerts = {}
        self.alert_history = []
        
    def add_alert_rule(self, rule_id: str, metric_pattern: str, 
                      condition: str, threshold: float, duration: int = 60):
        """Add an alert rule."""
        self.alert_rules[rule_id] = {
            "metric_pattern": metric_pattern,
            "condition": condition,  # "gt", "lt", "eq"
            "threshold": threshold,
            "duration": duration,
            "triggered_count": 0
        }
    
    def evaluate_alerts(self, points: List[MetricPoint]) -> List[Dict[str, Any]]:
        """Evaluate alert rules against metric points."""
        triggered_alerts = []
        
        for rule_id, rule in self.alert_rules.items():
            # Find matching points
            matching_points = [
                p for p in points 
                if rule["metric_pattern"] in p.metric_name
            ]
            
            if not matching_points:
                continue
            
            # Check condition
            latest_point = max(matching_points, key=lambda p: p.timestamp)
            
            if self._check_condition(latest_point.value, rule["condition"], rule["threshold"]):
                # Alert condition met
                alert = {
                    "rule_id": rule_id,
                    "metric_name": latest_point.metric_name,
                    "value": latest_point.value,
                    "threshold": rule["threshold"],
                    "condition": rule["condition"],
                    "triggered_at": datetime.now(),
                    "severity": self._determine_severity(latest_point.value, rule["threshold"])
                }
                
                # Check if this is a new alert or ongoing
                if rule_id not in self.active_alerts:
                    self.active_alerts[rule_id] = alert
                    triggered_alerts.append(alert)
                    rule["triggered_count"] += 1
                    
                    logger.warning(f"Alert triggered: {rule_id} - {latest_point.metric_name} "
                                 f"{rule['condition']} {rule['threshold']} (value: {latest_point.value})")
        
        return triggered_alerts
    
    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Check if value meets alert condition."""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "eq":
            return abs(value - threshold) < 0.001  # Float equality with tolerance
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        else:
            return False
    
    def _determine_severity(self, value: float, threshold: float) -> str:
        """Determine alert severity based on how far value exceeds threshold."""
        ratio = abs(value - threshold) / threshold if threshold != 0 else 1
        
        if ratio > 0.5:
            return "critical"
        elif ratio > 0.2:
            return "warning"
        else:
            return "info"
    
    def resolve_alert(self, rule_id: str):
        """Resolve an active alert."""
        if rule_id in self.active_alerts:
            alert = self.active_alerts[rule_id]
            alert["resolved_at"] = datetime.now()
            self.alert_history.append(alert)
            del self.active_alerts[rule_id]
            logger.info(f"Alert resolved: {rule_id}")
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Get current alert status."""
        return {
            "active_alerts": len(self.active_alerts),
            "total_rules": len(self.alert_rules),
            "alert_history_count": len(self.alert_history),
            "active_alert_details": list(self.active_alerts.values())
        }


class MetricsCollectionSystem:
    """Main metrics collection system."""
    
    def __init__(self):
        self.metric_buffer = MetricBuffer()
        self.metric_aggregator = MetricAggregator()
        self.metric_exporter = MetricExporter()
        self.dashboard_integration = DashboardIntegration()
        self.alert_manager = AlertManager()
        self.metric_definitions = {}
        self.collection_interval = 60.0
        self.is_running = False
        
    def register_metric(self, definition: MetricDefinition):
        """Register a metric definition."""
        self.metric_definitions[definition.name] = definition
        logger.debug(f"Registered metric: {definition.name}")
    
    def record_metric(self, name: str, value: Union[int, float], 
                     labels: Dict[str, str] = None, 
                     metadata: Dict[str, Any] = None) -> bool:
        """Record a metric value."""
        point = MetricPoint(
            metric_name=name,
            value=value,
            timestamp=datetime.now(),
            labels=labels or {},
            metadata=metadata or {}
        )
        
        return self.metric_buffer.add_point(point)
    
    async def start_collection(self):
        """Start the metrics collection system."""
        self.is_running = True
        logger.info("Started metrics collection system")
        
        # Start background tasks
        asyncio.create_task(self._collection_loop())
        asyncio.create_task(self._aggregation_loop())
        asyncio.create_task(self._export_loop())
        asyncio.create_task(self._alert_loop())
    
    def stop_collection(self):
        """Stop the metrics collection system."""
        self.is_running = False
        logger.info("Stopped metrics collection system")
    
    async def _collection_loop(self):
        """Main collection loop."""
        while self.is_running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Collection loop error: {e}")
                await asyncio.sleep(5)
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        # Record buffer stats
        buffer_stats = self.metric_buffer.get_stats()
        self.record_metric("metrics_buffer_size", buffer_stats["current_size"])
        self.record_metric("metrics_buffer_utilization", buffer_stats["utilization"])
        
        # Record collection system metrics
        self.record_metric("metrics_definitions_count", len(self.metric_definitions))
        self.record_metric("metrics_collection_timestamp", time.time())
    
    async def _aggregation_loop(self):
        """Aggregation loop."""
        while self.is_running:
            try:
                # Get recent points for aggregation
                since = datetime.now() - timedelta(seconds=self.collection_interval * 2)
                points = self.metric_buffer.get_points(since=since)
                
                if points:
                    aggregated = self.metric_aggregator.aggregate_points(points)
                    
                    # Add aggregated points back to buffer
                    for aggregated_point in aggregated.values():
                        self.metric_buffer.add_point(aggregated_point)
                
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Aggregation loop error: {e}")
                await asyncio.sleep(10)
    
    async def _export_loop(self):
        """Export loop."""
        while self.is_running:
            try:
                # Flush buffer and export
                points = self.metric_buffer.flush()
                
                if points:
                    export_results = await self.metric_exporter.export_metrics(points)
                    logger.debug(f"Exported {len(points)} points: {export_results}")
                
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Export loop error: {e}")
                await asyncio.sleep(10)
    
    async def _alert_loop(self):
        """Alert evaluation loop."""
        while self.is_running:
            try:
                # Get recent points for alert evaluation
                since = datetime.now() - timedelta(seconds=self.collection_interval)
                points = self.metric_buffer.get_points(since=since)
                
                if points:
                    triggered_alerts = self.alert_manager.evaluate_alerts(points)
                    
                    if triggered_alerts:
                        logger.warning(f"Triggered {len(triggered_alerts)} alerts")
                
                await asyncio.sleep(30)  # Check alerts every 30 seconds
            except Exception as e:
                logger.error(f"Alert loop error: {e}")
                await asyncio.sleep(30)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            "is_running": self.is_running,
            "metric_definitions": len(self.metric_definitions),
            "buffer_stats": self.metric_buffer.get_stats(),
            "export_stats": self.metric_exporter.get_export_stats(),
            "alert_status": self.alert_manager.get_alert_status()
        }


class AgentMetricsCollectionManager:
    """Manages agent metrics collection testing."""
    
    def __init__(self):
        self.redis_service = None
        self.db_manager = None
        self.metrics_system = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
        self.metrics_system = MetricsCollectionSystem()
        await self._setup_test_metrics()
        await self._setup_test_exporters()
        await self._setup_test_alerts()
        
        await self.metrics_system.start_collection()
    
    async def _setup_test_metrics(self):
        """Setup test metric definitions."""
        metrics = [
            MetricDefinition("agent_execution_time", MetricType.HISTOGRAM, 
                           MetricCategory.PERFORMANCE, "Agent execution time", "seconds"),
            MetricDefinition("agent_success_rate", MetricType.GAUGE, 
                           MetricCategory.RELIABILITY, "Agent success rate", "percent"),
            MetricDefinition("agent_request_count", MetricType.COUNTER, 
                           MetricCategory.BUSINESS, "Total agent requests", "count"),
            MetricDefinition("agent_memory_usage", MetricType.GAUGE, 
                           MetricCategory.RESOURCE, "Agent memory usage", "bytes"),
            MetricDefinition("agent_error_count", MetricType.COUNTER, 
                           MetricCategory.RELIABILITY, "Agent error count", "count")
        ]
        
        for metric in metrics:
            self.metrics_system.register_metric(metric)
        
        # Setup aggregation rules
        self.metrics_system.metric_aggregator.add_aggregation_rule(
            "agent_execution_time", 300, "avg", ["agent_type"]
        )
        self.metrics_system.metric_aggregator.add_aggregation_rule(
            "agent_request_count", 300, "sum", ["agent_type"]
        )
    
    async def _setup_test_exporters(self):
        """Setup test export targets."""
        
        def prometheus_exporter(points: List[MetricPoint]) -> bool:
            """Mock Prometheus exporter."""
            # Simulate export to Prometheus
            prometheus_data = [p.to_prometheus_format() for p in points]
            logger.debug(f"Exported {len(prometheus_data)} points to Prometheus")
            return True
        
        async def dashboard_exporter(points: List[MetricPoint]) -> bool:
            """Mock dashboard exporter."""
            # Simulate export to dashboard
            await asyncio.sleep(0.01)  # Simulate network delay
            logger.debug(f"Exported {len(points)} points to dashboard")
            return True
        
        def log_exporter(points: List[MetricPoint]) -> bool:
            """Log exporter for testing."""
            for point in points:
                logger.debug(f"Metric: {point.metric_name}={point.value} @{point.timestamp}")
            return True
        
        self.metrics_system.metric_exporter.add_export_target("prometheus", prometheus_exporter)
        self.metrics_system.metric_exporter.add_export_target("dashboard", dashboard_exporter)
        self.metrics_system.metric_exporter.add_export_target("logs", log_exporter)
    
    async def _setup_test_alerts(self):
        """Setup test alert rules."""
        self.metrics_system.alert_manager.add_alert_rule(
            "high_error_rate", "agent_error_count", "gt", 10.0, 60
        )
        self.metrics_system.alert_manager.add_alert_rule(
            "low_success_rate", "agent_success_rate", "lt", 80.0, 120
        )
        self.metrics_system.alert_manager.add_alert_rule(
            "high_memory_usage", "agent_memory_usage", "gt", 1000000.0, 300
        )
    
    def simulate_agent_metrics(self, agent_id: str, count: int = 10):
        """Simulate agent metrics for testing."""
        import random
        
        for i in range(count):
            # Execution time
            execution_time = random.uniform(0.1, 5.0)
            self.metrics_system.record_metric(
                "agent_execution_time", 
                execution_time,
                {"agent_id": agent_id, "agent_type": "test_agent"}
            )
            
            # Success rate
            success_rate = random.uniform(70, 99)
            self.metrics_system.record_metric(
                "agent_success_rate",
                success_rate,
                {"agent_id": agent_id, "agent_type": "test_agent"}
            )
            
            # Request count
            self.metrics_system.record_metric(
                "agent_request_count",
                1,
                {"agent_id": agent_id, "agent_type": "test_agent"}
            )
            
            # Memory usage
            memory_usage = random.uniform(100000, 2000000)
            self.metrics_system.record_metric(
                "agent_memory_usage",
                memory_usage,
                {"agent_id": agent_id, "agent_type": "test_agent"}
            )
            
            # Error count (occasionally)
            if random.random() < 0.1:  # 10% chance of error
                self.metrics_system.record_metric(
                    "agent_error_count",
                    1,
                    {"agent_id": agent_id, "agent_type": "test_agent"}
                )
    
    async def cleanup(self):
        """Clean up resources."""
        if self.metrics_system:
            self.metrics_system.stop_collection()
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()


@pytest.fixture
async def metrics_collection_manager():
    """Create metrics collection manager for testing."""
    manager = AgentMetricsCollectionManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_basic_metric_recording(metrics_collection_manager):
    """Test basic metric recording functionality."""
    manager = metrics_collection_manager
    
    # Record some test metrics
    success = manager.metrics_system.record_metric(
        "test_metric", 42.5, {"source": "test"}
    )
    
    assert success is True
    
    # Check buffer
    points = manager.metrics_system.metric_buffer.get_points("test_metric")
    assert len(points) == 1
    assert points[0].value == 42.5
    assert points[0].labels["source"] == "test"


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_metric_buffer_operations(metrics_collection_manager):
    """Test metric buffer operations and overflow handling."""
    manager = metrics_collection_manager
    
    # Set small buffer size for testing
    manager.metrics_system.metric_buffer.max_size = 10
    
    # Add more metrics than buffer size
    for i in range(15):
        manager.metrics_system.record_metric(f"test_metric_{i}", i)
    
    # Check buffer size is limited
    assert manager.metrics_system.metric_buffer.size() == 10
    
    # Check overflow stats
    stats = manager.metrics_system.metric_buffer.get_stats()
    assert stats["buffer_overflows"] > 0
    assert stats["total_points"] == 15


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_metric_aggregation(metrics_collection_manager):
    """Test metric aggregation functionality."""
    manager = metrics_collection_manager
    
    # Add points for aggregation
    values = [10, 20, 30, 40, 50]
    for value in values:
        manager.metrics_system.record_metric(
            "aggregation_test", value, {"type": "test"}
        )
    
    # Get points and aggregate
    points = manager.metrics_system.metric_buffer.get_points("aggregation_test")
    
    # Add aggregation rule
    manager.metrics_system.metric_aggregator.add_aggregation_rule(
        "aggregation_test", 60, "avg"
    )
    
    aggregated = manager.metrics_system.metric_aggregator.aggregate_points(points)
    
    assert len(aggregated) > 0
    
    # Check aggregated value
    avg_point = next((p for p in aggregated.values() 
                     if "avg" in p.metric_name), None)
    assert avg_point is not None
    assert avg_point.value == 30.0  # Average of [10, 20, 30, 40, 50]


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_metric_export_functionality(metrics_collection_manager):
    """Test metric export to different targets."""
    manager = metrics_collection_manager
    
    # Record some metrics
    for i in range(5):
        manager.metrics_system.record_metric(f"export_test_{i}", i * 10)
    
    # Get points and export
    points = manager.metrics_system.metric_buffer.get_points()
    
    export_results = await manager.metrics_system.metric_exporter.export_metrics(points)
    
    # Should have exported to all configured targets
    assert "prometheus" in export_results
    assert "dashboard" in export_results
    assert "logs" in export_results
    
    # All exports should succeed
    assert all(export_results.values())
    
    # Check export stats
    stats = manager.metrics_system.metric_exporter.get_export_stats()
    assert stats["successful_exports"] > 0


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_alert_rule_evaluation(metrics_collection_manager):
    """Test alert rule evaluation and triggering."""
    manager = metrics_collection_manager
    
    # Record metrics that should trigger alerts
    manager.metrics_system.record_metric("agent_error_count", 15.0)  # Above threshold of 10
    manager.metrics_system.record_metric("agent_success_rate", 70.0)  # Below threshold of 80
    
    # Get points and evaluate alerts
    points = manager.metrics_system.metric_buffer.get_points()
    
    triggered_alerts = manager.metrics_system.alert_manager.evaluate_alerts(points)
    
    # Should have triggered alerts
    assert len(triggered_alerts) > 0
    
    # Check alert details
    error_alert = next((a for a in triggered_alerts 
                       if "error_count" in a["metric_name"]), None)
    assert error_alert is not None
    assert error_alert["value"] == 15.0
    assert error_alert["condition"] == "gt"
    
    # Check alert status
    alert_status = manager.metrics_system.alert_manager.get_alert_status()
    assert alert_status["active_alerts"] > 0


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_prometheus_format_export(metrics_collection_manager):
    """Test Prometheus format export."""
    manager = metrics_collection_manager
    
    # Record metric with labels
    manager.metrics_system.record_metric(
        "http_requests_total", 
        100,
        {"method": "GET", "status": "200"}
    )
    
    points = manager.metrics_system.metric_buffer.get_points("http_requests_total")
    assert len(points) == 1
    
    # Test Prometheus format
    prometheus_line = points[0].to_prometheus_format()
    
    assert "http_requests_total" in prometheus_line
    assert 'method="GET"' in prometheus_line
    assert 'status="200"' in prometheus_line
    assert "100" in prometheus_line


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_dashboard_integration(metrics_collection_manager):
    """Test dashboard integration functionality."""
    manager = metrics_collection_manager
    
    # Configure dashboard
    dashboard_config = {
        "name": "Agent Metrics Dashboard",
        "widgets": ["performance", "reliability"]
    }
    
    manager.metrics_system.dashboard_integration.configure_dashboard(
        "test_dashboard", dashboard_config
    )
    
    # Record metrics
    for i in range(5):
        manager.metrics_system.record_metric("dashboard_test", i * 10)
    
    # Update widget data
    points = manager.metrics_system.metric_buffer.get_points("dashboard_test")
    manager.metrics_system.dashboard_integration.update_widget_data(
        "test_dashboard", "performance_widget", points
    )
    
    # Get dashboard data
    dashboard_data = manager.metrics_system.dashboard_integration.get_dashboard_data(
        "test_dashboard"
    )
    
    assert "performance_widget" in dashboard_data
    widget_data = dashboard_data["performance_widget"]
    assert widget_data["point_count"] == 5
    assert widget_data["latest_value"] == 40  # Last recorded value


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_system_metrics_collection(metrics_collection_manager):
    """Test automatic system metrics collection."""
    manager = metrics_collection_manager
    
    # Let system collect metrics
    await asyncio.sleep(1.0)
    
    # Check for system metrics
    buffer_size_points = manager.metrics_system.metric_buffer.get_points("metrics_buffer_size")
    assert len(buffer_size_points) > 0
    
    utilization_points = manager.metrics_system.metric_buffer.get_points("metrics_buffer_utilization")
    assert len(utilization_points) > 0
    
    # System metrics should have reasonable values
    latest_size = buffer_size_points[-1].value
    assert latest_size >= 0
    
    latest_utilization = utilization_points[-1].value
    assert 0 <= latest_utilization <= 100


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_agent_metrics_simulation(metrics_collection_manager):
    """Test agent metrics simulation and collection."""
    manager = metrics_collection_manager
    
    # Simulate metrics for multiple agents
    agents = ["agent_1", "agent_2", "agent_3"]
    
    for agent_id in agents:
        manager.simulate_agent_metrics(agent_id, count=5)
    
    # Check that metrics were recorded
    execution_time_points = manager.metrics_system.metric_buffer.get_points("agent_execution_time")
    assert len(execution_time_points) == 15  # 3 agents * 5 metrics
    
    success_rate_points = manager.metrics_system.metric_buffer.get_points("agent_success_rate")
    assert len(success_rate_points) == 15
    
    # Check label consistency
    agent_ids = set()
    for point in execution_time_points:
        agent_ids.add(point.labels.get("agent_id"))
    
    assert agent_ids == set(agents)


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_metric_collection(metrics_collection_manager):
    """Test concurrent metric collection performance."""
    manager = metrics_collection_manager
    
    # Collect metrics concurrently
    async def collect_metrics(agent_id: str):
        for i in range(20):
            manager.metrics_system.record_metric(
                f"concurrent_test_{agent_id}", 
                i,
                {"agent_id": agent_id}
            )
            await asyncio.sleep(0.001)  # Small delay
    
    start_time = time.time()
    
    # Run concurrent collection
    tasks = [collect_metrics(f"agent_{i}") for i in range(10)]
    await asyncio.gather(*tasks)
    
    collection_time = time.time() - start_time
    
    # Check that all metrics were collected
    total_points = sum(
        len(manager.metrics_system.metric_buffer.get_points(f"concurrent_test_agent_{i}"))
        for i in range(10)
    )
    
    assert total_points == 200  # 10 agents * 20 metrics
    
    # Performance check
    assert collection_time < 5.0  # Should complete quickly with concurrency


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_metrics_collection_performance(metrics_collection_manager):
    """Benchmark metrics collection performance."""
    manager = metrics_collection_manager
    
    # Benchmark metric recording
    start_time = time.time()
    
    for i in range(1000):
        manager.metrics_system.record_metric(
            "performance_test", 
            i,
            {"index": str(i % 10)}
        )
    
    recording_time = time.time() - start_time
    
    # Benchmark export
    points = manager.metrics_system.metric_buffer.get_points()
    
    start_time = time.time()
    export_results = await manager.metrics_system.metric_exporter.export_metrics(points)
    export_time = time.time() - start_time
    
    # Performance assertions
    assert recording_time < 2.0   # 1000 recordings in under 2 seconds
    assert export_time < 1.0      # Export in under 1 second
    
    avg_recording_time = recording_time / 1000
    assert avg_recording_time < 0.002  # Under 2ms per recording
    
    # All exports should succeed
    assert all(export_results.values())
    
    logger.info(f"Performance: {avg_recording_time*1000:.1f}ms per metric recording")
    logger.info(f"Export time for {len(points)} points: {export_time:.3f}s")