"""
L3-8: Metrics Pipeline with Real Prometheus Scraping Integration Test

BVJ: Critical for observability and SLA monitoring. Ensures metrics are properly
exposed and scraped by Prometheus for alerting and performance monitoring.

Tests metrics pipeline with real Prometheus container scraping metrics.
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
import time
from typing import Any, Dict, List

import aiohttp
import docker
import pytest
from netra_backend.app.monitoring.metrics_collector import MetricsCollector
from netra_backend.app.monitoring.prometheus_exporter import PrometheusExporter
from prometheus_client import Counter, Gauge, Histogram, start_http_server

@pytest.mark.L3
class TestMetricsPipelinePrometheusL3:
    """Test metrics pipeline with real Prometheus scraping."""
    
    @pytest.fixture(scope="class")
    async def docker_client(self):
        """Docker client for container management."""
        client = docker.from_env()
        yield client
        client.close()
    
    @pytest.fixture(scope="class")
    async def prometheus_container(self, docker_client):
        """Start Prometheus container with test configuration."""
        # Create Prometheus config
        prometheus_config = """
global:
  scrape_interval: 1s
  evaluation_interval: 1s

scrape_configs:
  - job_name: 'netra-test'
    static_configs:
      - targets: ['host.docker.internal:8001']
    scrape_interval: 1s
    metrics_path: /metrics
"""
        
        # Write config to temp file
        with open("prometheus_test.yml", "w") as f:
            f.write(prometheus_config)
        
        try:
            container = docker_client.containers.run(
                "prom/prometheus:latest",
                command=[
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--storage.tsdb.path=/prometheus",
                    "--web.console.libraries=/etc/prometheus/console_libraries",
                    "--web.console.templates=/etc/prometheus/consoles",
                    "--storage.tsdb.retention.time=1h",
                    "--web.enable-lifecycle"
                ],
                ports={'9090/tcp': None},
                volumes={
                    "C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\prometheus_test.yml": 
                    {"bind": "/etc/prometheus/prometheus.yml", "mode": "ro"}
                },
                detach=True,
                name="prometheus_test_container"
            )
            
            # Get assigned port
            container.reload()
            port = container.attrs['NetworkSettings']['Ports']['9090/tcp'][0]['HostPort']
            
            # Wait for Prometheus to be ready
            await self._wait_for_prometheus(f"http://localhost:{port}")
            
            yield f"http://localhost:{port}"
            
        finally:
            try:
                container.stop()
                container.remove()
            except:
                pass
            
            # Cleanup config file
            try:
                import os
                os.remove("prometheus_test.yml")
            except:
                pass
    
    @pytest.fixture(scope="class")
    async def metrics_server(self):
        """Start metrics HTTP server."""
        server_port = 8001
        
        # Start Prometheus metrics server
        start_http_server(server_port)
        
        yield f"http://localhost:{server_port}"
        
        # Server cleanup handled by test framework
    
    async def _wait_for_prometheus(self, url: str, timeout: int = 60):
        """Wait for Prometheus to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/-/ready", timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(1)
        raise TimeoutError(f"Prometheus at {url} not ready within {timeout}s")
    
    @pytest.mark.asyncio
    async def test_metrics_collection_and_exposure(self, metrics_server):
        """Test that metrics are properly collected and exposed."""
        collector = MetricsCollector()
        exporter = PrometheusExporter()
        
        # Register test metrics
        request_counter = Counter('netra_test_requests_total', 'Test requests')
        response_time = Histogram('netra_test_response_seconds', 'Test response time')
        active_connections = Gauge('netra_test_active_connections', 'Test active connections')
        
        # Generate test data
        request_counter.inc(10)
        response_time.observe(0.5)
        response_time.observe(1.2)
        response_time.observe(0.8)
        active_connections.set(25)
        
        # Verify metrics are exposed
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{metrics_server}/metrics") as response:
                assert response.status == 200
                metrics_text = await response.text()
                
                assert "netra_test_requests_total 10" in metrics_text
                assert "netra_test_active_connections 25" in metrics_text
                assert "netra_test_response_seconds_count 3" in metrics_text
    
    @pytest.mark.asyncio
    async def test_prometheus_scraping_metrics(
        self, 
        prometheus_container, 
        metrics_server
    ):
        """Test that Prometheus successfully scrapes metrics."""
        # Generate metrics data
        test_counter = Counter('netra_scrape_test_total', 'Scrape test counter')
        test_gauge = Gauge('netra_scrape_test_value', 'Scrape test gauge')
        
        test_counter.inc(5)
        test_gauge.set(42)
        
        # Wait for scraping
        await asyncio.sleep(5)
        
        # Query Prometheus for scraped metrics
        async with aiohttp.ClientSession() as session:
            # Query counter metric
            counter_url = f"{prometheus_container}/api/v1/query"
            counter_params = {"query": "netra_scrape_test_total"}
            
            async with session.get(counter_url, params=counter_params) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                results = data["data"]["result"]
                assert len(results) > 0
                assert float(results[0]["value"][1]) == 5.0
            
            # Query gauge metric  
            gauge_params = {"query": "netra_scrape_test_value"}
            
            async with session.get(counter_url, params=gauge_params) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                results = data["data"]["result"]
                assert len(results) > 0
                assert float(results[0]["value"][1]) == 42.0
    
    @pytest.mark.asyncio
    async def test_metrics_pipeline_performance(self, metrics_server):
        """Test metrics pipeline performance under load."""
        collector = MetricsCollector()
        
        # Create high-frequency metrics
        high_freq_counter = Counter('netra_perf_test_total', 'Performance test')
        latency_hist = Histogram(
            'netra_perf_latency_seconds', 
            'Performance latency',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        start_time = time.time()
        
        # Generate high volume of metrics
        for i in range(1000):
            high_freq_counter.inc()
            latency_hist.observe(0.1 + (i % 10) * 0.1)
        
        collection_time = time.time() - start_time
        
        # Verify metrics are still accessible
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{metrics_server}/metrics") as response:
                assert response.status == 200
                metrics_text = await response.text()
                
                assert "netra_perf_test_total 1000" in metrics_text
                assert "netra_perf_latency_seconds_count 1000" in metrics_text
        
        # Performance assertion
        assert collection_time < 1.0  # Should complete within 1 second
    
    @pytest.mark.asyncio
    async def test_custom_metrics_with_labels(self, prometheus_container, metrics_server):
        """Test custom metrics with labels are properly scraped."""
        # Create labeled metrics
        labeled_counter = Counter(
            'netra_labeled_requests_total',
            'Labeled requests',
            ['method', 'status']
        )
        
        labeled_gauge = Gauge(
            'netra_labeled_active_users',
            'Active users by tenant',
            ['tenant_id']
        )
        
        # Generate labeled data
        labeled_counter.labels(method='GET', status='200').inc(10)
        labeled_counter.labels(method='POST', status='201').inc(5)
        labeled_counter.labels(method='GET', status='404').inc(2)
        
        labeled_gauge.labels(tenant_id='tenant_1').set(25)
        labeled_gauge.labels(tenant_id='tenant_2').set(15)
        
        # Wait for scraping
        await asyncio.sleep(3)
        
        # Verify labeled metrics in Prometheus
        async with aiohttp.ClientSession() as session:
            query_url = f"{prometheus_container}/api/v1/query"
            
            # Test counter with labels
            params = {"query": 'netra_labeled_requests_total{method="GET",status="200"}'}
            async with session.get(query_url, params=params) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                results = data["data"]["result"]
                assert len(results) > 0
                assert float(results[0]["value"][1]) == 10.0
            
            # Test gauge with labels
            params = {"query": 'netra_labeled_active_users{tenant_id="tenant_1"}'}
            async with session.get(query_url, params=params) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                results = data["data"]["result"]
                assert len(results) > 0
                assert float(results[0]["value"][1]) == 25.0
    
    @pytest.mark.asyncio
    async def test_metrics_aggregation_queries(self, prometheus_container, metrics_server):
        """Test Prometheus aggregation queries on collected metrics."""
        # Create metrics for aggregation testing
        request_duration = Histogram(
            'netra_request_duration_seconds',
            'Request duration',
            ['endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        
        # Generate sample data
        endpoints = ['/api/threads', '/api/agents', '/api/teams']
        for endpoint in endpoints:
            for i in range(20):
                duration = 0.1 + (i % 5) * 0.2  # 0.1 to 1.0 seconds
                request_duration.labels(endpoint=endpoint).observe(duration)
        
        # Wait for scraping
        await asyncio.sleep(4)
        
        # Test aggregation queries
        async with aiohttp.ClientSession() as session:
            query_url = f"{prometheus_container}/api/v1/query"
            
            # Test rate calculation
            rate_params = {"query": "rate(netra_request_duration_seconds_count[1m])"}
            async with session.get(query_url, params=rate_params) as response:
                assert response.status == 200
                data = await response.json()
                assert data["status"] == "success"
                assert len(data["data"]["result"]) > 0
            
            # Test quantile calculation
            quantile_params = {"query": "histogram_quantile(0.95, netra_request_duration_seconds_bucket)"}
            async with session.get(query_url, params=quantile_params) as response:
                assert response.status == 200
                data = await response.json()
                assert data["status"] == "success"
                assert len(data["data"]["result"]) > 0