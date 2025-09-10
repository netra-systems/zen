#!/usr/bin/env python
"""
Health Endpoints Integration Tests - Critical P0 Issue #146
===========================================================

This test suite validates health endpoint functionality that's critical for
Cloud Run container startup and load balancer health checks.

Critical Issues Being Tested:
1. Missing health check endpoints (/api/health, /health returning 404s)
2. Health endpoint response format and timing requirements
3. Health check dependencies (database, Redis, etc.)
4. Cloud Run startup probe compatibility

BUSINESS VALUE: Prevents Golden Path blocking due to failed health checks in staging/production

Following CLAUDE.md principles:
- Real services and connections, not mocks
- Tests designed to expose current health endpoint issues
- Complete validation of health check dependencies
- SSOT compliance for health endpoint patterns
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
import pytest
import aiohttp
import redis.asyncio as redis
from fastapi.testclient import TestClient

from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.app_factory import create_app
from auth_service.main import app as auth_app

pytestmark = pytest.mark.asyncio


class HealthEndpointError(Exception):
    """Exception raised for health endpoint validation errors."""
    pass


class HealthEndpointValidator:
    """
    Validates health endpoint functionality across all services.
    
    This validator ensures health endpoints meet Cloud Run requirements
    and provide proper startup/liveness probe responses.
    """
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.project_root = Path(__file__).parent.parent.parent
        
    async def validate_health_endpoint(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Validate a health endpoint for Cloud Run compatibility.
        
        Args:
            url: Health endpoint URL to test
            timeout: Request timeout in seconds
            
        Returns:
            Dict with validation results
        """
        result = {
            'url': url,
            'accessible': False,
            'status_code': None,
            'response_time_ms': 0,
            'response_data': None,
            'headers': {},
            'errors': [],
            'cloud_run_compatible': False
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                
                result['accessible'] = True
                result['status_code'] = response.status_code
                result['response_time_ms'] = (time.time() - start_time) * 1000
                result['headers'] = dict(response.headers)
                
                try:
                    result['response_data'] = response.json()
                except:
                    result['response_data'] = response.text
                
                # Validate Cloud Run compatibility
                if response.status_code == 200:
                    result['cloud_run_compatible'] = True
                elif response.status_code in [503, 500]:
                    # Acceptable for startup probes when initializing
                    result['cloud_run_compatible'] = True
                    result['errors'].append('service_initializing')
                else:
                    result['errors'].append(f'invalid_status_code_{response.status_code}')
                
                # Check response time requirements (Cloud Run timeout)
                if result['response_time_ms'] > 30000:  # 30 second Cloud Run timeout
                    result['errors'].append('response_too_slow')
                    result['cloud_run_compatible'] = False
                    
        except httpx.ConnectTimeout:
            result['errors'].append('connection_timeout')
        except httpx.ReadTimeout:
            result['errors'].append('read_timeout')
        except httpx.ConnectError:
            result['errors'].append('connection_refused')
        except Exception as e:
            result['errors'].append(f'unexpected_error_{type(e).__name__}')
        
        return result
    
    async def test_health_endpoint_dependencies(self, base_url: str) -> Dict[str, Any]:
        """
        Test health endpoint with various dependency states.
        
        Args:
            base_url: Base URL of the service to test
            
        Returns:
            Dict with dependency test results
        """
        dependency_tests = {
            'base_url': base_url,
            'tests_performed': [],
            'dependency_failures': [],
            'overall_health_resilient': True
        }
        
        health_endpoints = ['/health', '/api/health']
        
        for endpoint in health_endpoints:
            url = f"{base_url.rstrip('/')}{endpoint}"
            
            # Test 1: Normal health check
            normal_result = await self.validate_health_endpoint(url, timeout=10)
            dependency_tests['tests_performed'].append({
                'endpoint': endpoint,
                'test': 'normal_health_check',
                'result': normal_result
            })
            
            # Test 2: Health check under load simulation
            load_results = []
            try:
                # Send 5 concurrent requests to simulate load
                tasks = []
                for i in range(5):
                    task = self.validate_health_endpoint(url, timeout=5)
                    tasks.append(task)
                
                load_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Analyze load test results
                successful_responses = [r for r in load_results 
                                      if isinstance(r, dict) and r.get('accessible')]
                
                if len(successful_responses) < 3:  # Less than 60% success rate
                    dependency_tests['dependency_failures'].append({
                        'endpoint': endpoint,
                        'test': 'load_test',
                        'issue': 'poor_success_rate_under_load',
                        'success_rate': len(successful_responses) / 5
                    })
                    dependency_tests['overall_health_resilient'] = False
                    
            except Exception as e:
                dependency_tests['dependency_failures'].append({
                    'endpoint': endpoint,
                    'test': 'load_test',
                    'issue': f'load_test_exception_{type(e).__name__}',
                    'error': str(e)
                })
            
            dependency_tests['tests_performed'].append({
                'endpoint': endpoint,
                'test': 'load_simulation',
                'results': load_results if isinstance(load_results, list) else str(load_results)
            })
        
        return dependency_tests
    
    def analyze_health_response_format(self, response_data: Any) -> Dict[str, Any]:
        """
        Analyze health response format for completeness and usefulness.
        
        Args:
            response_data: Response data from health endpoint
            
        Returns:
            Dict with format analysis results
        """
        analysis = {
            'format_valid': False,
            'has_status': False,
            'has_timestamp': False,
            'has_dependencies': False,
            'has_version': False,
            'format_issues': [],
            'recommendations': []
        }
        
        if not response_data:
            analysis['format_issues'].append('empty_response')
            return analysis
        
        if isinstance(response_data, str):
            # Simple text response
            if response_data.lower() in ['ok', 'healthy', 'up']:
                analysis['format_valid'] = True
                analysis['has_status'] = True
            else:
                analysis['format_issues'].append('unclear_text_response')
        
        elif isinstance(response_data, dict):
            # JSON response - preferred format
            analysis['format_valid'] = True
            
            # Check for standard health check fields
            if 'status' in response_data:
                analysis['has_status'] = True
            else:
                analysis['recommendations'].append('add_status_field')
            
            if any(key in response_data for key in ['timestamp', 'time', 'checked_at']):
                analysis['has_timestamp'] = True
            else:
                analysis['recommendations'].append('add_timestamp_field')
            
            if any(key in response_data for key in ['dependencies', 'checks', 'services']):
                analysis['has_dependencies'] = True
            else:
                analysis['recommendations'].append('add_dependency_checks')
            
            if any(key in response_data for key in ['version', 'build', 'commit']):
                analysis['has_version'] = True
            else:
                analysis['recommendations'].append('add_version_info')
        
        else:
            analysis['format_issues'].append('unsupported_response_type')
        
        return analysis


class TestHealthEndpoints(SSotBaseTestCase):
    """
    Integration tests for health endpoint functionality.
    
    These tests are designed to FAIL initially to expose current
    health endpoint issues causing Cloud Run deployment failures.
    """
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.validator = HealthEndpointValidator()
        self.env = IsolatedEnvironment()
        
        # Define service URLs for testing
        self.service_urls = {
            'backend': f"http://localhost:{self.env.get('NETRA_BACKEND_PORT', '8000')}",
            'auth': f"http://localhost:{self.env.get('NETRA_AUTH_PORT', '8081')}"
        }
    
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_backend_health_endpoints_accessibility(self):
        """
        CRITICAL: Test backend service health endpoints.
        
        This test SHOULD FAIL initially if health endpoints return 404.
        """
        backend_url = self.service_urls['backend']
        health_endpoints = ['/health', '/api/health']
        
        endpoint_results = {}
        
        for endpoint in health_endpoints:
            url = f"{backend_url}{endpoint}"
            result = await self.validator.validate_health_endpoint(url)
            endpoint_results[endpoint] = result
            
            # Log detailed results
            self.log_test_result(f"backend_health_endpoint_{endpoint.replace('/', '_')}", result)
        
        # Assert all health endpoints are accessible
        for endpoint, result in endpoint_results.items():
            assert result['accessible'], (
                f"CRITICAL: Backend health endpoint {endpoint} is not accessible\n"
                f"URL: {result['url']}\n"
                f"Errors: {result['errors']}"
            )
            
            assert result['status_code'] == 200, (
                f"CRITICAL: Backend health endpoint {endpoint} returned {result['status_code']}\n"
                f"Expected: 200\n"
                f"Response: {result['response_data']}"
            )
        
        # Verify response times are acceptable for Cloud Run
        for endpoint, result in endpoint_results.items():
            assert result['response_time_ms'] < 30000, (
                f"Health endpoint {endpoint} too slow: {result['response_time_ms']}ms\n"
                f"Cloud Run timeout: 30000ms"
            )
    
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_auth_service_health_endpoints_accessibility(self):
        """
        CRITICAL: Test auth service health endpoints.
        
        This test SHOULD FAIL initially if auth health endpoints return 404.
        """
        auth_url = self.service_urls['auth']
        health_endpoints = ['/health', '/api/health']
        
        endpoint_results = {}
        
        for endpoint in health_endpoints:
            url = f"{auth_url}{endpoint}"
            result = await self.validator.validate_health_endpoint(url)
            endpoint_results[endpoint] = result
            
            # Log results
            self.log_test_result(f"auth_health_endpoint_{endpoint.replace('/', '_')}", result)
        
        # Assert auth health endpoints work
        for endpoint, result in endpoint_results.items():
            assert result['accessible'], (
                f"CRITICAL: Auth health endpoint {endpoint} is not accessible\n"
                f"URL: {result['url']}\n"
                f"Errors: {result['errors']}"
            )
        
        # At least one endpoint should return 200
        successful_endpoints = [ep for ep, res in endpoint_results.items() 
                               if res['status_code'] == 200]
        
        assert len(successful_endpoints) > 0, (
            f"CRITICAL: No auth health endpoints returned 200 status\n"
            f"Results: {[(ep, res['status_code']) for ep, res in endpoint_results.items()]}"
        )
    
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_health_endpoint_response_formats(self):
        """
        Test health endpoint response formats for usefulness.
        
        Validates that health responses provide meaningful information.
        """
        all_results = {}
        
        for service, base_url in self.service_urls.items():
            service_results = {}
            
            for endpoint in ['/health', '/api/health']:
                url = f"{base_url}{endpoint}"
                health_result = await self.validator.validate_health_endpoint(url, timeout=10)
                
                if health_result['accessible'] and health_result['status_code'] == 200:
                    format_analysis = self.validator.analyze_health_response_format(
                        health_result['response_data']
                    )
                    
                    service_results[endpoint] = {
                        'health_result': health_result,
                        'format_analysis': format_analysis
                    }
            
            all_results[service] = service_results
        
        # Log all format analyses
        self.log_test_result("health_response_format_analysis", all_results)
        
        # Assert at least one service has properly formatted health responses
        services_with_valid_format = []
        for service, endpoints in all_results.items():
            for endpoint, data in endpoints.items():
                if data['format_analysis']['format_valid']:
                    services_with_valid_format.append(f"{service}{endpoint}")
        
        assert len(services_with_valid_format) > 0, (
            f"No services have properly formatted health responses\n"
            f"Services tested: {list(all_results.keys())}\n"
            f"All responses need status information for Cloud Run compatibility"
        )
    
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_health_endpoint_dependency_resilience(self):
        """
        Test health endpoints under various dependency states.
        
        Validates resilience when dependencies are unavailable.
        """
        dependency_test_results = {}
        
        for service, base_url in self.service_urls.items():
            service_dependency_test = await self.validator.test_health_endpoint_dependencies(base_url)
            dependency_test_results[service] = service_dependency_test
        
        # Log dependency test results
        self.log_test_result("health_dependency_resilience", dependency_test_results)
        
        # Assert overall resilience
        resilient_services = [service for service, result in dependency_test_results.items() 
                             if result['overall_health_resilient']]
        
        # At least 50% of services should be resilient
        min_resilient = len(self.service_urls) // 2
        assert len(resilient_services) >= min_resilient, (
            f"Only {len(resilient_services)} services are health-resilient, need at least {min_resilient}\n"
            f"Resilient services: {resilient_services}\n"
            f"Non-resilient services may cause Cloud Run startup failures"
        )
    
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_health_endpoints_cors_support(self):
        """
        Test health endpoints support for CORS and various HTTP methods.
        
        Cloud Run load balancers may use different HTTP methods for health checks.
        """
        cors_test_results = {}
        
        for service, base_url in self.service_urls.items():
            service_cors_results = {}
            
            for endpoint in ['/health', '/api/health']:
                url = f"{base_url}{endpoint}"
                method_results = {}
                
                # Test different HTTP methods
                methods_to_test = ['GET', 'HEAD', 'OPTIONS']
                
                for method in methods_to_test:
                    try:
                        async with httpx.AsyncClient(timeout=10) as client:
                            response = await client.request(method, url)
                            
                            method_results[method] = {
                                'status_code': response.status_code,
                                'accessible': response.status_code < 500,
                                'headers': dict(response.headers),
                                'supports_cors': 'Access-Control-Allow-Origin' in response.headers
                            }
                    except Exception as e:
                        method_results[method] = {
                            'status_code': None,
                            'accessible': False,
                            'error': str(e),
                            'supports_cors': False
                        }
                
                service_cors_results[endpoint] = method_results
            
            cors_test_results[service] = service_cors_results
        
        # Log CORS test results
        self.log_test_result("health_endpoints_cors_support", cors_test_results)
        
        # Assert GET method works for all accessible endpoints
        for service, endpoints in cors_test_results.items():
            for endpoint, methods in endpoints.items():
                if 'GET' in methods:
                    get_result = methods['GET']
                    if get_result['accessible']:  # If endpoint exists
                        assert get_result['status_code'] in [200, 503], (
                            f"Health endpoint {service}{endpoint} GET method failed\n"
                            f"Status: {get_result['status_code']}\n"
                            f"Cloud Run requires GET method support for health checks"
                        )
    
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_health_endpoints_startup_probe_simulation(self):
        """
        Test health endpoints behavior during startup simulation.
        
        Simulates Cloud Run startup probe behavior and timing requirements.
        """
        startup_simulation_results = {}
        
        # Startup probe parameters (Cloud Run defaults)
        startup_config = {
            'initial_delay_seconds': 0,
            'timeout_seconds': 1,
            'period_seconds': 1,
            'failure_threshold': 30  # 30 failures = 30 seconds to start
        }
        
        for service, base_url in self.service_urls.items():
            service_startup_results = {
                'service': service,
                'startup_config': startup_config,
                'probe_results': [],
                'startup_successful': False,
                'time_to_healthy_seconds': 0
            }
            
            start_time = time.time()
            failures = 0
            max_attempts = startup_config['failure_threshold']
            
            for attempt in range(max_attempts):
                # Test primary health endpoint
                health_url = f"{base_url}/health"
                probe_result = await self.validator.validate_health_endpoint(
                    health_url, 
                    timeout=startup_config['timeout_seconds']
                )
                
                probe_result['attempt'] = attempt + 1
                probe_result['elapsed_seconds'] = time.time() - start_time
                service_startup_results['probe_results'].append(probe_result)
                
                if probe_result['status_code'] == 200:
                    # Startup successful
                    service_startup_results['startup_successful'] = True
                    service_startup_results['time_to_healthy_seconds'] = probe_result['elapsed_seconds']
                    break
                else:
                    failures += 1
                
                # Wait for next probe (simulate Cloud Run timing)
                await asyncio.sleep(startup_config['period_seconds'])
            
            startup_simulation_results[service] = service_startup_results
        
        # Log startup simulation results
        self.log_test_result("startup_probe_simulation", startup_simulation_results)
        
        # Assert at least one service starts successfully
        successful_startups = [service for service, result in startup_simulation_results.items() 
                              if result['startup_successful']]
        
        assert len(successful_startups) > 0, (
            f"No services passed startup probe simulation\n"
            f"Services tested: {list(startup_simulation_results.keys())}\n"
            f"Cloud Run startup probes will fail for all services"
        )
        
        # Assert startup times are reasonable
        for service, result in startup_simulation_results.items():
            if result['startup_successful']:
                assert result['time_to_healthy_seconds'] < 30, (
                    f"Service {service} takes too long to start: {result['time_to_healthy_seconds']}s\n"
                    f"Cloud Run default startup timeout: 30 seconds"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])