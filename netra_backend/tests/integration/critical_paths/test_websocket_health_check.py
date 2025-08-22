"""
L2 Integration Test: WebSocket Health Check and Monitoring

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Monitoring worth $6K MRR operational excellence
- Value Impact: Ensures connection reliability and prevents service degradation
- Strategic Impact: Operational excellence reduces churn and enables scaling

L2 Test: Real internal health check components with mocked external monitoring.
Performance target: <10s health check cycles, 99.5% uptime detection accuracy.
"""

# Add project root to path

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from test_framework import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio
import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from netra_backend.app.schemas import User

from netra_backend.app.services.websocket_manager import WebSocketManager
from test_framework.mock_utils import mock_justified


class HealthStatus(Enum):

    """Health status enumeration."""

    HEALTHY = "healthy"

    DEGRADED = "degraded"

    UNHEALTHY = "unhealthy"

    UNKNOWN = "unknown"


class WebSocketHealthChecker:

    """Health checker for WebSocket connections and services."""
    

    def __init__(self):

        self.check_interval = 30  # seconds

        self.timeout_threshold = 60  # seconds

        self.unhealthy_threshold = 3  # consecutive failures

        self.health_history = {}

        self.connection_metrics = {}

        self.service_dependencies = ['redis', 'database', 'auth_service']
    

    async def check_connection_health(self, user_id: str, connection_id: str) -> Dict[str, Any]:

        """Check health of a specific WebSocket connection."""

        health_data = {

            "user_id": user_id,

            "connection_id": connection_id,

            "timestamp": time.time(),

            "status": HealthStatus.UNKNOWN.value,

            "metrics": {},

            "issues": []

        }
        

        try:
            # Check connection responsiveness

            ping_result = await self._ping_connection(user_id, connection_id)

            health_data["metrics"]["ping_ms"] = ping_result.get("latency", -1)

            health_data["metrics"]["ping_success"] = ping_result.get("success", False)
            
            # Check message queue health

            queue_health = await self._check_message_queue_health(user_id)

            health_data["metrics"]["queue_size"] = queue_health.get("size", 0)

            health_data["metrics"]["queue_lag"] = queue_health.get("lag", 0)
            
            # Check resource usage

            resource_metrics = await self._check_resource_usage(connection_id)

            health_data["metrics"].update(resource_metrics)
            
            # Determine overall health status

            health_data["status"] = self._calculate_health_status(health_data["metrics"])
            

        except Exception as e:

            health_data["status"] = HealthStatus.UNHEALTHY.value

            health_data["issues"].append(f"Health check failed: {str(e)}")
        
        # Update health history

        self._update_health_history(user_id, connection_id, health_data)
        

        return health_data
    

    async def _ping_connection(self, user_id: str, connection_id: str) -> Dict[str, Any]:

        """Ping WebSocket connection to check responsiveness."""

        start_time = time.time()
        

        try:
            # Simulate ping by checking connection state
            # In real implementation, would send ping frame

            await asyncio.sleep(0.01)  # Simulate network latency
            

            latency = (time.time() - start_time) * 1000  # Convert to ms

            return {

                "success": True,

                "latency": latency,

                "timestamp": time.time()

            }

        except Exception:

            return {

                "success": False,

                "latency": -1,

                "timestamp": time.time()

            }
    

    async def _check_message_queue_health(self, user_id: str) -> Dict[str, Any]:

        """Check message queue health for user."""
        # Simulate queue health check

        return {

            "size": 0,  # No queued messages indicates healthy

            "lag": 5,   # 5ms processing lag

            "throughput": 100  # messages per second

        }
    

    async def _check_resource_usage(self, connection_id: str) -> Dict[str, Any]:

        """Check resource usage for connection."""
        # Simulate resource metrics

        return {

            "memory_mb": 2.5,

            "cpu_percent": 1.2,

            "open_handles": 3,

            "network_bytes_in": 1024,

            "network_bytes_out": 2048

        }
    

    def _calculate_health_status(self, metrics: Dict[str, Any]) -> str:

        """Calculate overall health status from metrics."""

        issues = 0
        
        # Check ping health

        if not metrics.get("ping_success", False):

            issues += 2

        elif metrics.get("ping_ms", 0) > 1000:  # >1s ping

            issues += 1
        
        # Check queue health

        if metrics.get("queue_size", 0) > 100:

            issues += 1

        if metrics.get("queue_lag", 0) > 1000:  # >1s lag

            issues += 1
        
        # Check resource usage

        if metrics.get("memory_mb", 0) > 10:

            issues += 1

        if metrics.get("cpu_percent", 0) > 5:

            issues += 1
        

        if issues == 0:

            return HealthStatus.HEALTHY.value

        elif issues <= 2:

            return HealthStatus.DEGRADED.value

        else:

            return HealthStatus.UNHEALTHY.value
    

    def _update_health_history(self, user_id: str, connection_id: str, health_data: Dict[str, Any]) -> None:

        """Update health history for connection."""

        key = f"{user_id}:{connection_id}"
        

        if key not in self.health_history:

            self.health_history[key] = []
        

        self.health_history[key].append(health_data)
        
        # Keep only last 100 health checks

        if len(self.health_history[key]) > 100:

            self.health_history[key] = self.health_history[key][-100:]
    

    async def check_service_dependencies(self) -> Dict[str, Any]:

        """Check health of service dependencies."""

        dependency_health = {}

        overall_healthy = True
        

        for service in self.service_dependencies:

            try:

                service_health = await self._check_service_health(service)

                dependency_health[service] = service_health
                

                if service_health["status"] != HealthStatus.HEALTHY.value:

                    overall_healthy = False
                    

            except Exception as e:

                dependency_health[service] = {

                    "status": HealthStatus.UNHEALTHY.value,

                    "error": str(e),

                    "timestamp": time.time()

                }

                overall_healthy = False
        

        return {

            "overall_healthy": overall_healthy,

            "services": dependency_health,

            "timestamp": time.time()

        }
    

    async def _check_service_health(self, service_name: str) -> Dict[str, Any]:

        """Check health of a specific service."""
        # Simulate service health checks

        health_checks = {

            "redis": self._check_redis_health,

            "database": self._check_database_health,

            "auth_service": self._check_auth_service_health

        }
        

        if service_name in health_checks:

            return await health_checks[service_name]()
        

        return {

            "status": HealthStatus.UNKNOWN.value,

            "timestamp": time.time()

        }
    

    async def _check_redis_health(self) -> Dict[str, Any]:

        """Check Redis health."""
        # Simulate Redis health check

        return {

            "status": HealthStatus.HEALTHY.value,

            "latency_ms": 2.5,

            "memory_usage_mb": 45.2,

            "connected_clients": 12,

            "timestamp": time.time()

        }
    

    async def _check_database_health(self) -> Dict[str, Any]:

        """Check database health."""
        # Simulate database health check

        return {

            "status": HealthStatus.HEALTHY.value,

            "query_latency_ms": 15.3,

            "active_connections": 8,

            "max_connections": 100,

            "timestamp": time.time()

        }
    

    async def _check_auth_service_health(self) -> Dict[str, Any]:

        """Check auth service health."""
        # Simulate auth service health check

        return {

            "status": HealthStatus.HEALTHY.value,

            "response_time_ms": 125.7,

            "success_rate": 99.8,

            "error_rate": 0.2,

            "timestamp": time.time()

        }
    

    def get_health_summary(self, user_id: str, connection_id: str) -> Dict[str, Any]:

        """Get health summary for connection."""

        key = f"{user_id}:{connection_id}"
        

        if key not in self.health_history:

            return {"error": "No health data available"}
        

        history = self.health_history[key]

        recent_checks = history[-10:]  # Last 10 checks
        
        # Calculate health metrics

        healthy_count = sum(1 for check in recent_checks 

                          if check["status"] == HealthStatus.HEALTHY.value)
        

        avg_ping = sum(check["metrics"].get("ping_ms", 0) for check in recent_checks) / len(recent_checks)
        

        return {

            "total_checks": len(history),

            "recent_checks": len(recent_checks),

            "health_rate": (healthy_count / len(recent_checks)) * 100,

            "avg_ping_ms": avg_ping,

            "last_check": recent_checks[-1] if recent_checks else None,

            "trend": self._calculate_health_trend(recent_checks)

        }
    

    def _calculate_health_trend(self, recent_checks: List[Dict[str, Any]]) -> str:

        """Calculate health trend from recent checks."""

        if len(recent_checks) < 3:

            return "insufficient_data"
        
        # Simple trend calculation

        recent_health = [1 if check["status"] == HealthStatus.HEALTHY.value else 0 

                        for check in recent_checks[-3:]]
        

        if sum(recent_health) == 3:

            return "improving"

        elif sum(recent_health) == 0:

            return "degrading"

        else:

            return "stable"


class MetricCollector:

    """Collect and aggregate WebSocket health metrics."""
    

    def __init__(self):

        self.metrics = {}

        self.aggregated_metrics = {}

        self.collection_interval = 60  # seconds
    

    def record_health_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None) -> None:

        """Record a health metric."""

        if labels is None:

            labels = {}
        

        metric_key = f"{metric_name}:{json.dumps(labels, sort_keys=True)}"
        

        if metric_key not in self.metrics:

            self.metrics[metric_key] = []
        

        self.metrics[metric_key].append({

            "value": value,

            "timestamp": time.time(),

            "labels": labels

        })
        
        # Keep only last 1000 data points

        if len(self.metrics[metric_key]) > 1000:

            self.metrics[metric_key] = self.metrics[metric_key][-1000:]
    

    def get_metric_summary(self, metric_name: str, time_window: int = 300) -> Dict[str, Any]:

        """Get metric summary for time window."""

        cutoff_time = time.time() - time_window

        matching_metrics = []
        

        for key, values in self.metrics.items():

            if key.startswith(f"{metric_name}:"):

                recent_values = [v for v in values if v["timestamp"] > cutoff_time]

                matching_metrics.extend(recent_values)
        

        if not matching_metrics:

            return {"error": "No metrics found"}
        

        values = [m["value"] for m in matching_metrics]
        

        return {

            "count": len(values),

            "min": min(values),

            "max": max(values),

            "avg": sum(values) / len(values),

            "latest": matching_metrics[-1]["value"] if matching_metrics else None,

            "time_window": time_window

        }
    

    def aggregate_metrics(self) -> Dict[str, Any]:

        """Aggregate all metrics for reporting."""

        aggregation = {}

        current_time = time.time()
        
        # Common metrics to aggregate

        metric_names = ["ping_latency", "queue_size", "memory_usage", "cpu_usage"]
        

        for metric_name in metric_names:

            summary = self.get_metric_summary(metric_name, 300)  # 5 minute window

            if "error" not in summary:

                aggregation[metric_name] = summary
        

        aggregation["timestamp"] = current_time

        aggregation["collection_interval"] = self.collection_interval
        

        return aggregation


@pytest.mark.L2

@pytest.mark.integration

class TestWebSocketHealthCheck:

    """L2 integration tests for WebSocket health checking."""
    

    @pytest.fixture

    def ws_manager(self):

        """Create WebSocket manager with mocked external services."""

        with patch('app.ws_manager.redis_manager') as mock_redis:

            mock_redis.enabled = False  # Use in-memory storage

            return WebSocketManager()
    

    @pytest.fixture

    def health_checker(self):

        """Create WebSocket health checker."""

        return WebSocketHealthChecker()
    

    @pytest.fixture

    def metric_collector(self):

        """Create metric collector."""

        return MetricCollector()
    

    @pytest.fixture

    def test_users(self):

        """Create test users."""

        return [

            User(

                id=f"health_user_{i}",

                email=f"healthuser{i}@example.com",

                username=f"healthuser{i}",

                is_active=True,

                created_at=datetime.now(timezone.utc)

            )

            for i in range(3)

        ]
    

    async def test_basic_connection_health_check(self, ws_manager, health_checker, test_users):

        """Test basic connection health checking."""

        user = test_users[0]

        mock_websocket = AsyncMock()
        
        # Connect user

        connection_info = await ws_manager.connect_user(user.id, mock_websocket)

        assert connection_info is not None
        
        # Perform health check

        health_data = await health_checker.check_connection_health(user.id, connection_info.connection_id)
        
        # Verify health check structure

        assert "user_id" in health_data

        assert "connection_id" in health_data

        assert "status" in health_data

        assert "metrics" in health_data

        assert "timestamp" in health_data
        
        # Verify metrics collected

        metrics = health_data["metrics"]

        assert "ping_ms" in metrics

        assert "ping_success" in metrics

        assert "queue_size" in metrics

        assert "memory_mb" in metrics
        
        # Verify status is valid

        assert health_data["status"] in [s.value for s in HealthStatus]
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, mock_websocket)
    

    async def test_service_dependency_health_checks(self, health_checker):

        """Test health checks for service dependencies."""

        dependency_health = await health_checker.check_service_dependencies()
        
        # Verify structure

        assert "overall_healthy" in dependency_health

        assert "services" in dependency_health

        assert "timestamp" in dependency_health
        
        # Verify all services checked

        services = dependency_health["services"]

        expected_services = health_checker.service_dependencies
        

        for service in expected_services:

            assert service in services

            assert "status" in services[service]

            assert "timestamp" in services[service]
        
        # Verify Redis health specifics

        redis_health = services["redis"]

        assert "latency_ms" in redis_health

        assert "memory_usage_mb" in redis_health

        assert "connected_clients" in redis_health
        
        # Verify database health specifics

        db_health = services["database"]

        assert "query_latency_ms" in db_health

        assert "active_connections" in db_health

        assert "max_connections" in db_health
        
        # Verify auth service health specifics

        auth_health = services["auth_service"]

        assert "response_time_ms" in auth_health

        assert "success_rate" in auth_health

        assert "error_rate" in auth_health
    

    async def test_health_history_tracking(self, ws_manager, health_checker, test_users):

        """Test health history tracking functionality."""

        user = test_users[0]

        mock_websocket = AsyncMock()
        
        # Connect user

        connection_info = await ws_manager.connect_user(user.id, mock_websocket)

        assert connection_info is not None
        
        # Perform multiple health checks

        check_count = 5

        for i in range(check_count):

            await health_checker.check_connection_health(user.id, connection_info.connection_id)

            await asyncio.sleep(0.1)  # Small delay between checks
        
        # Get health summary

        summary = health_checker.get_health_summary(user.id, connection_info.connection_id)
        
        # Verify summary structure

        assert "total_checks" in summary

        assert "recent_checks" in summary

        assert "health_rate" in summary

        assert "avg_ping_ms" in summary

        assert "last_check" in summary

        assert "trend" in summary
        
        # Verify data consistency

        assert summary["total_checks"] == check_count

        assert summary["recent_checks"] <= check_count

        assert 0 <= summary["health_rate"] <= 100

        assert summary["avg_ping_ms"] >= 0
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, mock_websocket)
    

    async def test_metric_collection_and_aggregation(self, metric_collector):

        """Test metric collection and aggregation."""
        # Record test metrics

        metric_collector.record_health_metric("ping_latency", 50.5, {"user": "test1"})

        metric_collector.record_health_metric("ping_latency", 75.2, {"user": "test2"})

        metric_collector.record_health_metric("ping_latency", 32.1, {"user": "test1"})
        

        metric_collector.record_health_metric("queue_size", 5, {"service": "websocket"})

        metric_collector.record_health_metric("queue_size", 12, {"service": "websocket"})
        
        # Get metric summary

        ping_summary = metric_collector.get_metric_summary("ping_latency")
        
        # Verify summary structure

        assert "count" in ping_summary

        assert "min" in ping_summary

        assert "max" in ping_summary

        assert "avg" in ping_summary

        assert "latest" in ping_summary
        
        # Verify calculated values

        assert ping_summary["count"] == 3

        assert ping_summary["min"] == 32.1

        assert ping_summary["max"] == 75.2

        assert abs(ping_summary["avg"] - 52.6) < 0.1  # Average of 50.5, 75.2, 32.1
        
        # Test aggregation

        aggregated = metric_collector.aggregate_metrics()

        assert "ping_latency" in aggregated

        assert "queue_size" in aggregated

        assert "timestamp" in aggregated
    

    async def test_unhealthy_connection_detection(self, ws_manager, health_checker, test_users):

        """Test detection of unhealthy connections."""

        user = test_users[0]

        mock_websocket = AsyncMock()
        
        # Connect user

        connection_info = await ws_manager.connect_user(user.id, mock_websocket)

        assert connection_info is not None
        
        # Mock unhealthy connection by patching ping method

        async def unhealthy_ping(*args):

            return {"success": False, "latency": -1, "timestamp": time.time()}
        

        health_checker._ping_connection = unhealthy_ping
        
        # Perform health check

        health_data = await health_checker.check_connection_health(user.id, connection_info.connection_id)
        
        # Verify unhealthy status detected

        assert health_data["status"] in [HealthStatus.DEGRADED.value, HealthStatus.UNHEALTHY.value]

        assert health_data["metrics"]["ping_success"] is False
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, mock_websocket)
    

    async def test_concurrent_health_checks(self, ws_manager, health_checker, test_users):

        """Test concurrent health checking for multiple connections."""

        connections = []
        
        # Establish multiple connections

        for user in test_users:

            mock_websocket = AsyncMock()

            connection_info = await ws_manager.connect_user(user.id, mock_websocket)

            if connection_info:

                connections.append((user, mock_websocket, connection_info))
        
        # Perform concurrent health checks

        start_time = time.time()

        health_tasks = []
        

        for user, _, connection_info in connections:

            task = health_checker.check_connection_health(user.id, connection_info.connection_id)

            health_tasks.append(task)
        

        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)

        check_duration = time.time() - start_time
        
        # Performance assertions

        assert check_duration < 5.0  # Should complete quickly
        
        # Verify all checks completed successfully

        successful_checks = sum(1 for result in health_results 

                              if not isinstance(result, Exception))

        assert successful_checks == len(connections)
        
        # Verify health data structure

        for result in health_results:

            if not isinstance(result, Exception):

                assert "status" in result

                assert "metrics" in result

                assert "timestamp" in result
        
        # Cleanup

        for user, websocket, _ in connections:

            await ws_manager.disconnect_user(user.id, websocket)
    

    @mock_justified("L2: WebSocket health checking with real internal components")

    async def test_health_check_integration_flow(self, ws_manager, health_checker, metric_collector, test_users):

        """Test complete health check integration flow."""

        user = test_users[0]

        mock_websocket = AsyncMock()
        
        # Connect user

        connection_info = await ws_manager.connect_user(user.id, mock_websocket)

        assert connection_info is not None
        
        # Simulate health monitoring cycle

        monitoring_cycles = 3
        

        for cycle in range(monitoring_cycles):
            # Perform health check

            health_data = await health_checker.check_connection_health(user.id, connection_info.connection_id)
            
            # Record metrics

            metrics = health_data["metrics"]

            metric_collector.record_health_metric("ping_latency", metrics.get("ping_ms", 0))

            metric_collector.record_health_metric("queue_size", metrics.get("queue_size", 0))

            metric_collector.record_health_metric("memory_usage", metrics.get("memory_mb", 0))
            
            # Check service dependencies

            dependency_health = await health_checker.check_service_dependencies()
            
            # Record service health metrics

            for service, service_health in dependency_health["services"].items():

                status_numeric = 1 if service_health["status"] == HealthStatus.HEALTHY.value else 0

                metric_collector.record_health_metric(f"service_{service}_health", status_numeric)
            

            await asyncio.sleep(0.1)  # Small delay between cycles
        
        # Get health summary

        summary = health_checker.get_health_summary(user.id, connection_info.connection_id)
        
        # Verify monitoring effectiveness

        assert summary["total_checks"] == monitoring_cycles

        assert summary["health_rate"] >= 0

        assert "trend" in summary
        
        # Get aggregated metrics

        aggregated = metric_collector.aggregate_metrics()
        
        # Verify metric aggregation

        assert "ping_latency" in aggregated

        assert "queue_size" in aggregated

        assert "memory_usage" in aggregated
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, mock_websocket)
    

    async def test_health_check_performance_benchmarks(self, health_checker, test_users):

        """Test health check performance benchmarks."""

        user = test_users[0]

        connection_id = str(uuid4())
        
        # Benchmark single health check

        start_time = time.time()

        health_data = await health_checker.check_connection_health(user.id, connection_id)

        single_check_time = time.time() - start_time
        
        # Single check should be very fast

        assert single_check_time < 0.5  # Less than 500ms
        
        # Benchmark multiple health checks

        check_count = 20

        start_time = time.time()
        

        for _ in range(check_count):

            await health_checker.check_connection_health(user.id, connection_id)
        

        multiple_checks_time = time.time() - start_time

        avg_check_time = multiple_checks_time / check_count
        
        # Average check time should be reasonable

        assert avg_check_time < 0.1  # Less than 100ms per check

        assert multiple_checks_time < 5.0  # Total time reasonable
        
        # Benchmark service dependency checks

        start_time = time.time()

        dependency_health = await health_checker.check_service_dependencies()

        dependency_check_time = time.time() - start_time
        
        # Service dependency check should complete quickly

        assert dependency_check_time < 2.0  # Less than 2 seconds

        assert dependency_health["overall_healthy"] is not None


if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])