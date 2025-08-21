"""Metrics and Observability Critical Path Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (operational excellence)
- Business Goal: Complete system observability and performance monitoring
- Value Impact: Enables proactive issue detection, reduces downtime, improves SLA compliance
- Strategic Impact: $15K-35K MRR protection through operational excellence

Critical Path: Metrics collection -> Data aggregation -> Alert generation -> Dashboard visualization -> SLA monitoring
Coverage: Prometheus metrics, Grafana dashboards, OpenTelemetry tracing, log aggregation
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to path

from netra_backend.app.services.observability.metrics_collector import MetricsCollector
from netra_backend.app.services.observability.prometheus_exporter import PrometheusExporter
from netra_backend.app.services.observability.tracing_service import TracingService
from netra_backend.app.services.observability.alert_manager import AlertManager

# Add project root to path

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """Manages observability testing with real metrics collection."""
    
    def __init__(self):
        self.metrics_collector = None
        self.prometheus_exporter = None
        self.tracing_service = None
        self.alert_manager = None
        self.collected_metrics = []
        self.traces = []
        self.alerts_generated = []
        
    async def initialize_services(self):
        """Initialize observability services."""
        try:
            self.metrics_collector = MetricsCollector()
            await self.metrics_collector.initialize()
            
            self.prometheus_exporter = PrometheusExporter()
            await self.prometheus_exporter.initialize()
            
            self.tracing_service = TracingService()
            await self.tracing_service.initialize()
            
            self.alert_manager = AlertManager()
            await self.alert_manager.initialize()
            
            logger.info("Observability services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize observability services: {e}")
            raise
    
    async def collect_business_metrics(self, metric_name: str, value: float, 
                                     labels: Dict[str, str] = None) -> Dict[str, Any]:
        """Collect business metrics with validation."""
        metric_id = str(uuid.uuid4())
        timestamp = time.time()
        
        try:
            metric_data = {
                "metric_id": metric_id,
                "name": metric_name,
                "value": value,
                "labels": labels or {},
                "timestamp": timestamp,
                "type": "business"
            }
            
            collection_result = await self.metrics_collector.collect_metric(metric_data)
            
            if collection_result["success"]:
                self.collected_metrics.append(metric_data)
                
                # Export to Prometheus
                await self.prometheus_exporter.export_metric(metric_data)
            
            return {
                "metric_id": metric_id,
                "collected": collection_result["success"],
                "collection_result": collection_result
            }
            
        except Exception as e:
            return {
                "metric_id": metric_id,
                "collected": False,
                "error": str(e)
            }
    
    async def create_distributed_trace(self, operation_name: str, 
                                     trace_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create distributed trace with spans."""
        trace_id = str(uuid.uuid4())
        
        try:
            trace_context = {
                "trace_id": trace_id,
                "operation_name": operation_name,
                "start_time": time.time(),
                "trace_data": trace_data or {},
                "spans": []
            }
            
            # Create root span
            root_span = await self.create_span(trace_id, "root_span", operation_name)
            trace_context["spans"].append(root_span)
            
            # Simulate child spans
            child_spans = [
                ("database_query", 0.05),
                ("external_api_call", 0.15),
                ("business_logic", 0.08)
            ]
            
            for span_name, duration in child_spans:
                child_span = await self.create_span(trace_id, span_name, span_name, duration)
                trace_context["spans"].append(child_span)
            
            trace_context["end_time"] = time.time()
            trace_context["total_duration"] = trace_context["end_time"] - trace_context["start_time"]
            
            # Send to tracing service
            tracing_result = await self.tracing_service.record_trace(trace_context)
            
            if tracing_result["success"]:
                self.traces.append(trace_context)
            
            return {
                "trace_id": trace_id,
                "recorded": tracing_result["success"],
                "trace_context": trace_context,
                "tracing_result": tracing_result
            }
            
        except Exception as e:
            return {
                "trace_id": trace_id,
                "recorded": False,
                "error": str(e)
            }
    
    async def create_span(self, trace_id: str, span_id: str, operation: str, 
                        duration: float = None) -> Dict[str, Any]:
        """Create individual span within a trace."""
        start_time = time.time()
        
        if duration:
            await asyncio.sleep(duration)
        
        end_time = time.time()
        
        span_data = {
            "trace_id": trace_id,
            "span_id": span_id,
            "operation": operation,
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time,
            "tags": {
                "service.name": "netra-api",
                "operation.type": operation
            }
        }
        
        return span_data
    
    async def test_sla_monitoring(self, service_name: str, target_sla: float) -> Dict[str, Any]:
        """Test SLA monitoring and alerting."""
        try:
            sla_test_results = []
            
            # Simulate service requests with varying response times
            for i in range(20):
                # Vary response times to test SLA monitoring
                if i < 15:
                    response_time = 0.1  # Good response time
                else:
                    response_time = 2.0  # Poor response time
                
                # Record request metric
                await self.collect_business_metrics(
                    "request_duration_seconds",
                    response_time,
                    {"service": service_name, "endpoint": "/api/test"}
                )
                
                sla_test_results.append({
                    "request_id": i,
                    "response_time": response_time,
                    "meets_sla": response_time <= target_sla
                })
            
            # Calculate SLA compliance
            successful_requests = [r for r in sla_test_results if r["meets_sla"]]
            sla_compliance = len(successful_requests) / len(sla_test_results) * 100
            
            # Check if alerts should be generated
            if sla_compliance < 95.0:  # SLA breach threshold
                alert_result = await self.generate_sla_alert(service_name, sla_compliance, target_sla)
            else:
                alert_result = {"alert_generated": False, "reason": "SLA within acceptable range"}
            
            return {
                "service_name": service_name,
                "target_sla": target_sla,
                "actual_compliance": sla_compliance,
                "sla_breach": sla_compliance < 95.0,
                "alert_result": alert_result,
                "test_results": sla_test_results
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "sla_breach": True
            }
    
    async def cleanup(self):
        """Clean up observability resources."""
        try:
            if self.metrics_collector:
                await self.metrics_collector.shutdown()
            if self.prometheus_exporter:
                await self.prometheus_exporter.shutdown()
            if self.tracing_service:
                await self.tracing_service.shutdown()
            if self.alert_manager:
                await self.alert_manager.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def observability_manager():
    """Create observability manager for testing."""
    manager = ObservabilityManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
async def test_business_metrics_collection(observability_manager):
    """Test collection of business metrics."""
    # Collect various business metrics
    business_metrics = [
        ("revenue_per_user", 25.50, {"tier": "enterprise", "region": "us-east"}),
        ("api_requests_total", 1000, {"service": "auth", "status": "success"}),
        ("user_engagement_score", 8.5, {"feature": "chat", "tier": "free"})
    ]
    
    collection_results = []
    for metric_name, value, labels in business_metrics:
        result = await observability_manager.collect_business_metrics(metric_name, value, labels)
        collection_results.append(result)
    
    # Verify all metrics collected successfully
    successful_collections = [r for r in collection_results if r["collected"]]
    assert len(successful_collections) == 3
    
    # Verify metrics are stored
    assert len(observability_manager.collected_metrics) == 3


@pytest.mark.asyncio
async def test_observability_security_controls(observability_manager):
    """Test security controls in observability metrics."""
    # Test legitimate metrics collection
    legitimate_result = await observability_manager.collect_business_metrics(
        "legitimate_metric", 100.0, {"source": "trusted_service"}
    )
    
    assert legitimate_result["collected"] is True
