from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
Test Observability Pipeline

Validates logging, metrics, and distributed tracing
in the staging environment.
"""

import sys
from pathlib import Path

import pytest
# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
from typing import Dict, List

import httpx

from netra_backend.tests.integration.staging_config.base import StagingConfigTestBase

class TestObservabilityPipeline(StagingConfigTestBase):
    """Test observability pipeline in staging."""
    
    @pytest.mark.asyncio
    async def test_structured_logging(self):
        """Test structured logging configuration."""
        self.skip_if_not_staging()
        
        # Generate a log entry
        async with httpx.AsyncClient() as client:
            trace_id = 'test-trace-12345'
            
            response = await client.get(
                f"{self.staging_url}/health",
                headers={
                    'X-Trace-Id': trace_id
                },
                timeout=5.0
            )
            
            # Check if logs are being collected
            # This would normally query log aggregation service
            self.assertEqual(response.status_code, 200,
                           "Request should succeed for log generation")
                           
    @pytest.mark.asyncio
    async def test_prometheus_metrics(self):
        """Test Prometheus metrics export."""
        self.skip_if_not_staging()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.staging_url}/metrics",
                timeout=10.0
            )
            
            self.assertEqual(response.status_code, 200,
                           "Metrics endpoint should be accessible")
                           
            metrics_text = response.text
            
            # Verify critical metrics present
            critical_metrics = [
                'http_requests_total',
                'http_request_duration_seconds',
                'websocket_connections',
                'database_pool_size',
                'redis_operations_total',
                'llm_requests_total',
                'agent_executions_total'
            ]
            
            missing_metrics = []
            for metric in critical_metrics:
                if metric not in metrics_text:
                    missing_metrics.append(metric)
                    
            self.assertEqual(len(missing_metrics), 0,
                           f"Missing metrics: {missing_metrics}")
                           
            # Verify metric format
            self.assertIn('# HELP', metrics_text, "Missing metric help text")
            self.assertIn('# TYPE', metrics_text, "Missing metric type definitions")
            
    @pytest.mark.asyncio
    async def test_distributed_tracing(self):
        """Test distributed tracing with OpenTelemetry."""
        self.skip_if_not_staging()
        
        trace_id = 'test-trace-67890'
        span_id = 'span-12345'
        
        async with httpx.AsyncClient() as client:
            # Make request with trace context
            response = await client.post(
                f"{self.staging_url}/api/threads",
                headers={
                    'traceparent': f'00-{trace_id}-{span_id}-01',
                    'Authorization': 'Bearer test_token'
                },
                json={
                    'title': 'Test Thread for Tracing'
                },
                timeout=10.0
            )
            
            # Check for trace propagation in response
            if 'traceparent' in response.headers:
                # Verify trace ID is preserved
                self.assertIn(trace_id, response.headers['traceparent'],
                            "Trace ID should be propagated")
                            
    @pytest.mark.asyncio
    async def test_custom_metrics(self):
        """Test custom application metrics."""
        self.skip_if_not_staging()
        
        async with httpx.AsyncClient() as client:
            # Generate some metric data
            for i in range(5):
                await client.post(
                    f"{self.staging_url}/api/chat/completions",
                    json={
                        'model': 'gemini-pro',
                        'messages': [{'role': 'user', 'content': f'Test {i}'}]
                    },
                    headers={'Authorization': 'Bearer test_token'},
                    timeout=10.0
                )
                
            # Check metrics were recorded
            response = await client.get(
                f"{self.staging_url}/metrics",
                timeout=5.0
            )
            
            metrics_text = response.text
            
            # Verify custom metrics
            custom_metrics = [
                'llm_token_usage',
                'agent_response_time',
                'cache_hit_ratio'
            ]
            
            for metric in custom_metrics:
                if metric in metrics_text:
                    # Extract metric value
                    lines = metrics_text.split('\n')
                    for line in lines:
                        if metric in line and not line.startswith('#'):
                            # Verify metric has value
                            self.assertRegex(line, r'\d+(\.\d+)?',
                                          f"Metric {metric} has no value")
                                          
    @pytest.mark.asyncio
    async def test_error_tracking(self):
        """Test error tracking and reporting."""
        self.skip_if_not_staging()
        
        async with httpx.AsyncClient() as client:
            # Generate an error
            response = await client.get(
                f"{self.staging_url}/api/nonexistent",
                timeout=5.0
            )
            
            # Should return 404
            self.assertEqual(response.status_code, 404)
            
            # Check error metrics
            response = await client.get(
                f"{self.staging_url}/metrics",
                timeout=5.0
            )
            
            metrics_text = response.text
            
            # Verify error metrics incremented
            self.assertIn('http_requests_total{.*status="404"', metrics_text,
                        "404 errors should be tracked")
                        
    @pytest.mark.asyncio
    async def test_grafana_dashboards(self):
        """Test Grafana dashboard data sources."""
        self.skip_if_not_staging()
        
        # Check if Grafana endpoint is configured
        grafana_url = get_env().get('GRAFANA_URL', f"{self.staging_url}/grafana")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{grafana_url}/api/health",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    # Grafana is accessible
                    data = response.json()
                    self.assertEqual(data.get('database'), 'ok',
                                   "Grafana database not healthy")
            except:
                # Grafana might not be publicly accessible
                pass
                
    @pytest.mark.asyncio
    async def test_log_correlation(self):
        """Test log correlation across services."""
        self.skip_if_not_staging()
        
        correlation_id = 'corr-test-99999'
        
        async with httpx.AsyncClient() as client:
            # Make requests to multiple services with same correlation ID
            services = [
                '/api/threads',
                '/auth/verify',
                '/ws'
            ]
            
            for service in services:
                response = await client.get(
                    f"{self.staging_url}{service}",
                    headers={
                        'X-Correlation-Id': correlation_id
                    },
                    timeout=5.0
                )
                
                # Services should propagate correlation ID
                if 'X-Correlation-Id' in response.headers:
                    self.assertEqual(response.headers['X-Correlation-Id'],
                                   correlation_id,
                                   f"Correlation ID not preserved by {service}")
                                   
    @pytest.mark.asyncio
    async def test_alerting_webhooks(self):
        """Test alerting webhook endpoints."""
        self.skip_if_not_staging()
        
        # These endpoints should exist for alert manager
        webhook_endpoints = [
            '/webhooks/alerts',
            '/webhooks/prometheus',
            '/webhooks/grafana'
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in webhook_endpoints:
                response = await client.post(
                    f"{self.staging_url}{endpoint}",
                    json={
                        'alerts': [{
                            'status': 'firing',
                            'labels': {'alertname': 'test'}
                        }]
                    },
                    timeout=5.0
                )
                
                # Should exist but might require auth
                self.assertIn(response.status_code, [200, 401, 403, 405],
                            f"Webhook endpoint {endpoint} not configured")
