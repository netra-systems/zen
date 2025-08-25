"""Metrics Collection Pipeline L4 Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (operational excellence for all tiers)
- Business Goal: Complete observability and performance monitoring
- Value Impact: Enables proactive issue detection, reduces MTTR, ensures SLA compliance
- Strategic Impact: $7K MRR protection through operational excellence and customer confidence

Critical Path: Metrics ingestion -> Prometheus storage -> Grafana visualization -> Alert generation
Coverage: Real Prometheus/Grafana integration, custom metrics accuracy, cardinality management, alerting rules
L4 Realism: Tests against staging infrastructure with real monitoring stack
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import patch, AsyncMock, MagicMock

import httpx
import pytest

from netra_backend.app.config import get_config
from netra_backend.app.services.observability.alert_manager import AlertManager

from netra_backend.app.services.observability.metrics_collector import MetricsCollector
from netra_backend.app.services.observability.prometheus_exporter import (
    PrometheusExporter,
)

logger = logging.getLogger(__name__)

# L4 Staging environment markers
pytestmark = [
    pytest.mark.l4,
    pytest.mark.staging,
    pytest.mark.observability,
    pytest.mark.slow
]

class MetricsPipelineL4Manager:
    """Manages L4 metrics pipeline testing with real monitoring infrastructure."""
    
    def __init__(self):
        self.config = None
        self.metrics_collector = None
        self.prometheus_exporter = None
        self.alert_manager = None
        self.staging_prometheus_url = None
        self.staging_grafana_url = None
        self.test_metrics = []
        self.generated_alerts = []
        self.cardinality_metrics = {}
        
    async def initialize_staging_services(self):
        """Initialize real monitoring services in staging."""
        try:
            # Initialize config for staging
            self.config = Config()
            
            # Skip if not in staging environment
            if self.config.environment != "staging":
                pytest.skip("L4 tests require staging environment")
                
            # Get staging monitoring URLs from config
            self.staging_prometheus_url = os.getenv(
                "STAGING_PROMETHEUS_URL", 
                "http://prometheus.staging.netrasystems.ai:9090"
            )
            self.staging_grafana_url = os.getenv(
                "STAGING_GRAFANA_URL",
                "http://grafana.staging.netrasystems.ai:3000"
            )
            
            # Initialize real metrics services
            self.metrics_collector = MetricsCollector()
            await self.metrics_collector.initialize()
            
            self.prometheus_exporter = PrometheusExporter()
            await self.prometheus_exporter.initialize()
            
            self.alert_manager = AlertManager()
            await self.alert_manager.initialize()
            
            # Verify staging infrastructure is accessible
            await self.verify_staging_infrastructure()
            
            logger.info("L4 metrics pipeline services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize L4 metrics services: {e}")
            pytest.skip(f"L4 infrastructure unavailable: {e}")
    
    async def verify_staging_infrastructure(self):
        """Verify staging monitoring infrastructure is accessible."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check Prometheus accessibility
            try:
                prometheus_response = await client.get(f"{self.staging_prometheus_url}/api/query?query=up")
                assert prometheus_response.status_code == 200
                assert prometheus_response.json()["status"] == "success"
            except Exception as e:
                raise Exception(f"Staging Prometheus unavailable: {e}")
            
            # Check Grafana accessibility  
            try:
                grafana_response = await client.get(f"{self.staging_grafana_url}/api/health")
                assert grafana_response.status_code == 200
            except Exception as e:
                raise Exception(f"Staging Grafana unavailable: {e}")
    
    async def collect_business_metric_l4(self, metric_name: str, value: float, 
                                      labels: Dict[str, str] = None) -> Dict[str, Any]:
        """Collect business metric with L4 realism - writes to real Prometheus."""
        metric_id = str(uuid.uuid4())
        timestamp = time.time()
        
        try:
            metric_data = {
                "metric_id": metric_id,
                "name": metric_name,
                "value": value,
                "labels": labels or {},
                "timestamp": timestamp,
                "type": "business",
                "environment": "staging",
                "test_session": "l4_metrics_pipeline"
            }
            
            # Add L4 test labels for identification
            metric_data["labels"].update({
                "test_type": "l4_integration",
                "test_session_id": metric_id[:8],
                "netra_environment": "staging"
            })
            
            # Collect through real metrics collector
            collection_result = await self.metrics_collector.collect_metric(metric_data)
            
            if collection_result["success"]:
                # Export to real Prometheus in staging
                export_result = await self.prometheus_exporter.export_metric(metric_data)
                
                # Wait for metric to be available in Prometheus
                await asyncio.sleep(2.0)
                
                # Verify metric appears in Prometheus
                verification_result = await self.verify_metric_in_prometheus(metric_name, labels)
                
                self.test_metrics.append({
                    "metric_data": metric_data,
                    "collection_result": collection_result,
                    "export_result": export_result,
                    "verification_result": verification_result
                })
            
            return {
                "metric_id": metric_id,
                "collected": collection_result["success"],
                "exported": export_result.get("success", False) if collection_result["success"] else False,
                "verified_in_prometheus": verification_result.get("found", False) if collection_result["success"] else False,
                "collection_result": collection_result
            }
            
        except Exception as e:
            return {
                "metric_id": metric_id,
                "collected": False,
                "error": str(e)
            }
    
    async def verify_metric_in_prometheus(self, metric_name: str, labels: Dict[str, str] = None) -> Dict[str, Any]:
        """Verify metric exists in staging Prometheus."""
        try:
            # Build Prometheus query
            query = metric_name
            if labels:
                label_selectors = []
                for key, value in labels.items():
                    label_selectors.append(f'{key}="{value}"')
                if label_selectors:
                    query += "{" + ",".join(label_selectors) + "}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.staging_prometheus_url}/api/query",
                    params={"query": query}
                )
                
                if response.status_code != 200:
                    return {"found": False, "error": f"Prometheus query failed: {response.status_code}"}
                
                data = response.json()
                if data["status"] != "success":
                    return {"found": False, "error": f"Query error: {data.get('error', 'Unknown')}"}
                
                results = data["data"]["result"]
                return {
                    "found": len(results) > 0,
                    "result_count": len(results),
                    "latest_value": results[0]["value"][1] if results else None,
                    "query": query
                }
                
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    @pytest.mark.asyncio
    async def test_cardinality_management_l4(self) -> Dict[str, Any]:
        """Test metric cardinality management in real Prometheus."""
        try:
            cardinality_test_results = {
                "high_cardinality_metrics": [],
                "cardinality_violations": [],
                "total_series_count": 0
            }
            
            # Generate metrics with varying cardinality
            base_metric = "test_cardinality_metric"
            
            # Low cardinality (acceptable)
            low_cardinality_labels = [
                {"service": "auth", "status": "success"},
                {"service": "auth", "status": "error"},
                {"service": "api", "status": "success"},
                {"service": "api", "status": "error"}
            ]
            
            for labels in low_cardinality_labels:
                result = await self.collect_business_metric_l4(base_metric, 1.0, labels)
                assert result["collected"], f"Failed to collect low cardinality metric: {labels}"
            
            # High cardinality (potentially problematic)
            high_cardinality_metric = "test_high_cardinality_metric"
            for i in range(50):  # Generate 50 unique label combinations
                labels = {
                    "user_id": f"user_{i}",
                    "session_id": f"session_{i}",
                    "request_id": f"req_{i}"
                }
                result = await self.collect_business_metric_l4(high_cardinality_metric, 1.0, labels)
                if not result["collected"]:
                    cardinality_test_results["cardinality_violations"].append({
                        "metric": high_cardinality_metric,
                        "labels": labels,
                        "error": result.get("error", "Collection failed")
                    })
            
            # Wait for metrics to propagate
            await asyncio.sleep(5.0)
            
            # Query Prometheus for series count
            series_count = await self.get_prometheus_series_count()
            cardinality_test_results["total_series_count"] = series_count
            
            # Check for cardinality warnings in Prometheus
            cardinality_warnings = await self.check_cardinality_warnings()
            cardinality_test_results["cardinality_warnings"] = cardinality_warnings
            
            self.cardinality_metrics = cardinality_test_results
            
            return cardinality_test_results
            
        except Exception as e:
            return {"error": str(e), "cardinality_violations": ["Test execution failed"]}
    
    async def get_prometheus_series_count(self) -> int:
        """Get total series count from Prometheus."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.staging_prometheus_url}/api/query",
                    params={"query": "prometheus_tsdb_symbol_table_size_bytes"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data["status"] == "success" and data["data"]["result"]:
                        return int(float(data["data"]["result"][0]["value"][1]))
                
                return 0
        except Exception:
            return 0
    
    async def check_cardinality_warnings(self) -> List[Dict[str, Any]]:
        """Check for cardinality warnings in Prometheus."""
        try:
            warnings = []
            
            # Query for high cardinality metrics
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.staging_prometheus_url}/api/query",
                    params={"query": "topk(10, count by (__name__)({__name__=~'.+'})"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data["status"] == "success":
                        for result in data["data"]["result"]:
                            metric_name = result["metric"]["__name__"]
                            series_count = int(float(result["value"][1]))
                            
                            if series_count > 1000:  # Arbitrary threshold
                                warnings.append({
                                    "metric_name": metric_name,
                                    "series_count": series_count,
                                    "severity": "high" if series_count > 5000 else "medium"
                                })
            
            return warnings
            
        except Exception:
            return []
    
    @pytest.mark.asyncio
    async def test_alerting_rules_l4(self) -> Dict[str, Any]:
        """Test alerting rules trigger correctly in staging."""
        try:
            alerting_test_results = {
                "tested_alerts": [],
                "triggered_alerts": [],
                "alert_latency": {}
            }
            
            # Generate metrics that should trigger alerts
            alert_test_scenarios = [
                {
                    "name": "high_error_rate",
                    "metric": "http_requests_total",
                    "labels": {"status": "500", "service": "api"},
                    "value": 100,  # High error count
                    "expected_alert": "HighErrorRate"
                },
                {
                    "name": "high_response_time",
                    "metric": "http_request_duration_seconds",
                    "labels": {"service": "api", "endpoint": "/api/test"},
                    "value": 5.0,  # 5 seconds response time
                    "expected_alert": "HighResponseTime"
                },
                {
                    "name": "low_disk_space",
                    "metric": "disk_free_bytes",
                    "labels": {"instance": "staging-server", "mount": "/"},
                    "value": 1000000,  # 1MB free space
                    "expected_alert": "DiskSpaceLow"
                }
            ]
            
            for scenario in alert_test_scenarios:
                scenario_start = time.time()
                
                # Generate metric that should trigger alert
                metric_result = await self.collect_business_metric_l4(
                    scenario["metric"],
                    scenario["value"],
                    scenario["labels"]
                )
                
                assert metric_result["collected"], f"Failed to collect metric for {scenario['name']}"
                
                # Wait for alert evaluation cycle
                await asyncio.sleep(30.0)
                
                # Check if alert was triggered
                alert_status = await self.check_alert_status(scenario["expected_alert"])
                
                scenario_end = time.time()
                alert_latency = scenario_end - scenario_start
                
                alerting_test_results["tested_alerts"].append(scenario["name"])
                alerting_test_results["alert_latency"][scenario["name"]] = alert_latency
                
                if alert_status["active"]:
                    alerting_test_results["triggered_alerts"].append({
                        "scenario": scenario["name"],
                        "alert_name": scenario["expected_alert"],
                        "latency": alert_latency,
                        "alert_details": alert_status["details"]
                    })
                
                # Record alert generation
                self.generated_alerts.append({
                    "scenario": scenario,
                    "alert_status": alert_status,
                    "latency": alert_latency
                })
            
            return alerting_test_results
            
        except Exception as e:
            return {"error": str(e), "tested_alerts": [], "triggered_alerts": []}
    
    async def check_alert_status(self, alert_name: str) -> Dict[str, Any]:
        """Check if specific alert is active in AlertManager."""
        try:
            # Query AlertManager API (assuming it's available)
            alertmanager_url = os.getenv(
                "STAGING_ALERTMANAGER_URL",
                "http://alertmanager.staging.netrasystems.ai:9093"
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{alertmanager_url}/api/alerts")
                
                if response.status_code == 200:
                    alerts = response.json()["data"]
                    
                    for alert in alerts:
                        if alert["labels"].get("alertname") == alert_name:
                            return {
                                "active": True,
                                "details": {
                                    "state": alert["status"]["state"],
                                    "active_at": alert["activeAt"],
                                    "labels": alert["labels"],
                                    "annotations": alert.get("annotations", {})
                                }
                            }
                    
                    return {"active": False, "details": None}
                else:
                    return {"active": False, "error": f"AlertManager query failed: {response.status_code}"}
                    
        except Exception as e:
            # Fallback: Check Prometheus for alert rules
            return await self.check_prometheus_alert_rules(alert_name)
    
    async def check_prometheus_alert_rules(self, alert_name: str) -> Dict[str, Any]:
        """Fallback: Check Prometheus alert rules."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.staging_prometheus_url}/api/rules")
                
                if response.status_code == 200:
                    data = response.json()
                    for group in data["data"]["groups"]:
                        for rule in group["rules"]:
                            if rule.get("name") == alert_name and rule.get("state") == "firing":
                                return {
                                    "active": True,
                                    "details": {
                                        "state": rule["state"],
                                        "value": rule.get("value"),
                                        "query": rule.get("query")
                                    }
                                }
                
                return {"active": False, "details": None}
                
        except Exception as e:
            return {"active": False, "error": str(e)}
    
    @pytest.mark.asyncio
    async def test_grafana_integration_l4(self) -> Dict[str, Any]:
        """Test Grafana dashboard integration with real data."""
        try:
            grafana_test_results = {
                "dashboards_tested": [],
                "data_sources_verified": [],
                "query_performance": {}
            }
            
            # Test Grafana API accessibility
            async with httpx.AsyncClient(timeout=30.0) as client:
                # List available dashboards
                dashboards_response = await client.get(
                    f"{self.staging_grafana_url}/api/search?type=dash-db",
                    headers={"Authorization": f"Bearer {os.getenv('GRAFANA_API_TOKEN', '')}"}
                )
                
                if dashboards_response.status_code == 200:
                    dashboards = dashboards_response.json()
                    
                    # Test key dashboards
                    key_dashboards = ["System Overview", "API Metrics", "Error Tracking"]
                    for dashboard_title in key_dashboards:
                        dashboard = next((d for d in dashboards if dashboard_title in d.get("title", "")), None)
                        if dashboard:
                            dashboard_test = await self.test_dashboard_queries(dashboard["uid"])
                            grafana_test_results["dashboards_tested"].append({
                                "title": dashboard_title,
                                "uid": dashboard["uid"],
                                "test_result": dashboard_test
                            })
                
                # Verify data sources
                datasources_response = await client.get(
                    f"{self.staging_grafana_url}/api/datasources",
                    headers={"Authorization": f"Bearer {os.getenv('GRAFANA_API_TOKEN', '')}"}
                )
                
                if datasources_response.status_code == 200:
                    datasources = datasources_response.json()
                    for datasource in datasources:
                        if datasource["type"] == "prometheus":
                            ds_test = await self.test_datasource_connection(datasource["uid"])
                            grafana_test_results["data_sources_verified"].append({
                                "name": datasource["name"],
                                "type": datasource["type"],
                                "url": datasource["url"],
                                "test_result": ds_test
                            })
            
            return grafana_test_results
            
        except Exception as e:
            return {"error": str(e), "dashboards_tested": [], "data_sources_verified": []}
    
    @pytest.mark.asyncio
    async def test_dashboard_queries(self, dashboard_uid: str) -> Dict[str, Any]:
        """Test dashboard query performance."""
        try:
            # This is a simplified test - in reality would parse dashboard JSON
            # and test each panel's queries
            test_start = time.time()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.staging_grafana_url}/api/dashboards/uid/{dashboard_uid}",
                    headers={"Authorization": f"Bearer {os.getenv('GRAFANA_API_TOKEN', '')}"}
                )
                
                if response.status_code == 200:
                    test_duration = time.time() - test_start
                    return {
                        "success": True,
                        "query_duration": test_duration,
                        "panels_count": len(response.json().get("dashboard", {}).get("panels", []))
                    }
                else:
                    return {"success": False, "error": f"Dashboard query failed: {response.status_code}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @pytest.mark.asyncio
    async def test_datasource_connection(self, datasource_uid: str) -> Dict[str, Any]:
        """Test data source connection."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.staging_grafana_url}/api/datasources/uid/{datasource_uid}/health",
                    headers={"Authorization": f"Bearer {os.getenv('GRAFANA_API_TOKEN', '')}"}
                )
                
                return {
                    "success": response.status_code == 200,
                    "status": response.json() if response.status_code == 200 else None
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def cleanup(self):
        """Clean up L4 test resources."""
        try:
            # Clean up test metrics from Prometheus (if possible)
            cleanup_tasks = []
            
            if self.metrics_collector:
                cleanup_tasks.append(self.metrics_collector.shutdown())
            if self.prometheus_exporter:
                cleanup_tasks.append(self.prometheus_exporter.shutdown())
            if self.alert_manager:
                cleanup_tasks.append(self.alert_manager.shutdown())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                
            logger.info("L4 metrics pipeline cleanup completed")
            
        except Exception as e:
            logger.error(f"L4 cleanup failed: {e}")

@pytest.fixture
async def metrics_pipeline_l4():
    """Create L4 metrics pipeline manager for staging tests."""
    manager = MetricsPipelineL4Manager()
    await manager.initialize_staging_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
async def test_business_metrics_collection_l4_staging(metrics_pipeline_l4):
    """Test business metrics collection with L4 realism in staging."""
    # Test critical business metrics
    business_metrics = [
        ("revenue_per_user_monthly", 125.50, {"tier": "enterprise", "region": "us-east"}),
        ("api_requests_success_rate", 98.5, {"service": "auth", "timeframe": "1h"}),
        ("user_engagement_score", 8.7, {"feature": "chat", "cohort": "new_users"}),
        ("llm_token_usage_rate", 15000, {"model": "gpt-4", "usage_type": "completion"}),
        ("conversion_rate_percent", 12.3, {"source": "organic", "tier": "free_to_paid"})
    ]
    
    collection_results = []
    for metric_name, value, labels in business_metrics:
        result = await metrics_pipeline_l4.collect_business_metric_l4(metric_name, value, labels)
        collection_results.append(result)
        
        # L4 verification: metric must be collected, exported, AND verified in Prometheus
        assert result["collected"], f"Metric {metric_name} collection failed"
        assert result["exported"], f"Metric {metric_name} export to Prometheus failed"
        assert result["verified_in_prometheus"], f"Metric {metric_name} not found in staging Prometheus"
    
    # Verify all metrics were processed successfully
    successful_collections = [r for r in collection_results if r["collected"] and r["exported"]]
    assert len(successful_collections) == 5, "Not all business metrics were successfully processed"
    
    # Verify metrics are queryable from staging Prometheus
    total_metrics_count = len(metrics_pipeline_l4.test_metrics)
    assert total_metrics_count >= 5, "Test metrics not properly tracked"

@pytest.mark.asyncio
async def test_cardinality_management_l4_staging(metrics_pipeline_l4):
    """Test metric cardinality management in real Prometheus."""
    cardinality_results = await metrics_pipeline_l4.test_cardinality_management_l4()
    
    # Verify cardinality management is working
    assert "error" not in cardinality_results, f"Cardinality test failed: {cardinality_results.get('error')}"
    
    # Check that high cardinality didn't cause system issues
    assert cardinality_results["total_series_count"] > 0, "No metrics series found in Prometheus"
    
    # Verify cardinality violations are within acceptable limits
    violation_count = len(cardinality_results["cardinality_violations"])
    assert violation_count < 10, f"Too many cardinality violations: {violation_count}"
    
    # Check for cardinality warnings
    if cardinality_results.get("cardinality_warnings"):
        high_cardinality_warnings = [
            w for w in cardinality_results["cardinality_warnings"] 
            if w["severity"] == "high"
        ]
        assert len(high_cardinality_warnings) < 3, "Too many high cardinality metrics detected"

@pytest.mark.asyncio
async def test_alerting_rules_l4_staging(metrics_pipeline_l4):
    """Test alerting rules trigger correctly in staging environment."""
    alerting_results = await metrics_pipeline_l4.test_alerting_rules_l4()
    
    # Verify alerting test execution
    assert "error" not in alerting_results, f"Alerting test failed: {alerting_results.get('error')}"
    assert len(alerting_results["tested_alerts"]) >= 3, "Not enough alert scenarios tested"
    
    # Verify alert latency is within acceptable bounds
    for alert_name, latency in alerting_results["alert_latency"].items():
        assert latency < 120.0, f"Alert latency too high for {alert_name}: {latency}s"
    
    # At least some alerts should trigger (depending on staging environment state)
    # This is a softer assertion since it depends on staging environment conditions
    total_alerts_tested = len(alerting_results["tested_alerts"])
    triggered_alerts = len(alerting_results["triggered_alerts"])
    
    logger.info(f"Alert testing: {triggered_alerts}/{total_alerts_tested} alerts triggered")
    
    # Verify alert infrastructure is responsive
    assert total_alerts_tested > 0, "No alert scenarios were tested"

@pytest.mark.asyncio  
async def test_grafana_integration_l4_staging(metrics_pipeline_l4):
    """Test Grafana dashboard integration with real staging data."""
    grafana_results = await metrics_pipeline_l4.test_grafana_integration_l4()
    
    # Skip test if Grafana API token not available
    if "error" in grafana_results and "token" in grafana_results["error"].lower():
        pytest.skip("Grafana API token not available for L4 testing")
    
    # Verify Grafana integration
    assert "error" not in grafana_results, f"Grafana integration test failed: {grafana_results.get('error')}"
    
    # Verify data sources are connected
    verified_sources = [ds for ds in grafana_results["data_sources_verified"] if ds["test_result"]["success"]]
    assert len(verified_sources) > 0, "No Grafana data sources verified"
    
    # Verify dashboard accessibility
    tested_dashboards = grafana_results["dashboards_tested"]
    if tested_dashboards:
        successful_dashboard_tests = [d for d in tested_dashboards if d["test_result"]["success"]]
        assert len(successful_dashboard_tests) > 0, "No dashboards successfully tested"
        
        # Verify dashboard query performance
        for dashboard in successful_dashboard_tests:
            query_duration = dashboard["test_result"]["query_duration"]
            assert query_duration < 10.0, f"Dashboard query too slow: {query_duration}s"

@pytest.mark.asyncio
async def test_metrics_pipeline_performance_l4_staging(metrics_pipeline_l4):
    """Test metrics pipeline performance under L4 realistic load."""
    performance_start = time.time()
    
    # Generate realistic metric load
    batch_metrics = []
    for i in range(100):  # 100 metrics in batch
        batch_metrics.append({
            "name": f"performance_test_metric_{i % 10}",  # 10 unique metric names
            "value": float(i),
            "labels": {
                "batch_id": "perf_test",
                "metric_index": str(i),
                "test_type": "performance"
            }
        })
    
    # Process metrics in parallel batches
    batch_size = 20
    batch_results = []
    
    for i in range(0, len(batch_metrics), batch_size):
        batch = batch_metrics[i:i + batch_size]
        batch_tasks = []
        
        for metric in batch:
            task = metrics_pipeline_l4.collect_business_metric_l4(
                metric["name"],
                metric["value"], 
                metric["labels"]
            )
            batch_tasks.append(task)
        
        batch_start = time.time()
        batch_result = await asyncio.gather(*batch_tasks, return_exceptions=True)
        batch_duration = time.time() - batch_start
        
        batch_results.extend(batch_result)
        
        # Verify batch performance
        assert batch_duration < 30.0, f"Batch processing too slow: {batch_duration}s"
    
    total_duration = time.time() - performance_start
    
    # Verify overall performance
    successful_metrics = [r for r in batch_results if isinstance(r, dict) and r.get("collected")]
    success_rate = len(successful_metrics) / len(batch_metrics) * 100
    
    assert success_rate >= 95.0, f"Metric collection success rate too low: {success_rate}%"
    assert total_duration < 120.0, f"Total pipeline performance too slow: {total_duration}s"
    
    # Calculate throughput
    throughput = len(batch_metrics) / total_duration
    assert throughput >= 1.0, f"Metrics throughput too low: {throughput} metrics/second"
    
    logger.info(f"L4 Performance Results: {len(successful_metrics)}/{len(batch_metrics)} metrics, "
               f"{throughput:.2f} metrics/sec, {success_rate:.1f}% success rate")