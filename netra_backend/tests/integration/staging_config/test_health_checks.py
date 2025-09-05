"""
Test Health Checks

Validates health check endpoints and monitoring
in the staging environment.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest
# Test framework import - using pytest fixtures instead

import asyncio
from typing import Dict, List

import httpx

from netra_backend.tests.integration.staging_config.base import StagingConfigTestBase

class TestHealthChecks(StagingConfigTestBase):
    """Test health checks in staging."""
    
    @pytest.mark.asyncio
    async def test_main_health_endpoint(self):
        """Test main health check endpoint."""
        self.skip_if_not_staging()
        
        health_data = await self.assert_service_healthy(
            self.staging_url,
            '/health'
        )
        
        # Verify health response structure
        self.assertIn('status', health_data)
        self.assertIn('checks', health_data)
        self.assertIn('version', health_data)
        self.assertIn('timestamp', health_data)
        
        # Verify component checks
        expected_checks = ['database', 'redis', 'websocket']
        for check in expected_checks:
            self.assertIn(check, health_data['checks'],
                         f"Missing health check for {check}")
                         
    @pytest.mark.asyncio
    async def test_readiness_probe(self):
        """Test Kubernetes readiness probe."""
        self.skip_if_not_staging()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.staging_url}/ready",
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                self.assertTrue(data.get('ready'),
                              "Service reports not ready")
            else:
                self.assertEqual(response.status_code, 503,
                               "Readiness probe should return 503 when not ready")
                               
    @pytest.mark.asyncio
    async def test_liveness_probe(self):
        """Test Kubernetes liveness probe."""
        self.skip_if_not_staging()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.staging_url}/alive",
                timeout=5.0
            )
            
            self.assertEqual(response.status_code, 200,
                           "Liveness probe failed")
                           
    @pytest.mark.asyncio
    async def test_component_health_checks(self):
        """Test individual component health checks."""
        self.skip_if_not_staging()
        
        components = [
            '/health/database',
            '/health/redis',
            '/health/websocket',
            '/health/llm'
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in components:
                with self.subTest(component=endpoint):
                    try:
                        response = await client.get(
                            f"{self.staging_url}{endpoint}",
                            timeout=10.0
                        )
                        
                        self.assertIn(response.status_code, [200, 503],
                                    f"Unexpected status for {endpoint}")
                                    
                        if response.status_code == 200:
                            data = response.json()
                            self.assertIn('healthy', data)
                            self.assertIn('latency_ms', data)
                            
                    except httpx.TimeoutException:
                        self.fail(f"Health check timeout for {endpoint}")
                        
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint."""
        self.skip_if_not_staging()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.staging_url}/metrics",
                timeout=10.0
            )
            
            self.assertEqual(response.status_code, 200,
                           "Metrics endpoint failed")
                           
            # Verify Prometheus format
            content = response.text
            self.assertIn('# HELP', content)
            self.assertIn('# TYPE', content)
            
            # Check for critical metrics
            critical_metrics = [
                'http_requests_total',
                'http_request_duration_seconds',
                'websocket_connections',
                'database_pool_size'
            ]
            
            for metric in critical_metrics:
                self.assertIn(metric, content,
                            f"Missing critical metric: {metric}")
                            
    @pytest.mark.asyncio
    async def test_health_check_degradation(self):
        """Test health check degradation handling."""
        self.skip_if_not_staging()
        
        # Get initial health
        initial_health = await self.assert_service_healthy(
            self.staging_url,
            '/health'
        )
        
        # Check if any components are degraded
        degraded_components = []
        for component, status in initial_health['checks'].items():
            if isinstance(status, dict) and status.get('status') == 'degraded':
                degraded_components.append(component)
                
        # Service should still be healthy with degraded components
        if degraded_components:
            self.assertEqual(initial_health['status'], 'degraded',
                           f"Overall status should be degraded with degraded components: {degraded_components}")
                           
    @pytest.mark.asyncio
    async def test_health_check_circuit_breaker(self):
        """Test health check circuit breaker behavior."""
        self.skip_if_not_staging()
        
        async with httpx.AsyncClient() as client:
            # Make multiple rapid health check requests
            responses = []
            for _ in range(10):
                response = await client.get(
                    f"{self.staging_url}/health",
                    timeout=5.0
                )
                responses.append(response.status_code)
                
            # All should succeed (circuit breaker shouldn't trip for health checks)
            for status in responses:
                self.assertEqual(status, 200,
                               "Health check circuit breaker tripped incorrectly")
                               
    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        """Test health check timeout handling."""
        self.skip_if_not_staging()
        
        async with httpx.AsyncClient() as client:
            # Health checks should respond quickly
            import time
            start = time.time()
            
            response = await client.get(
                f"{self.staging_url}/health",
                timeout=5.0
            )
            
            elapsed = time.time() - start
            
            self.assertEqual(response.status_code, 200)
            self.assertLess(elapsed, 2.0,
                          f"Health check took {elapsed:.2f}s, exceeds 2s limit")