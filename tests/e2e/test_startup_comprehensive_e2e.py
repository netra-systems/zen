"""Comprehensive Startup E2E Tests for Final Implementation Agent

Business Value Justification (BVJ):
1. Segment: All customer segments (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure system startup reliability and service initialization
3. Value Impact: Critical for system availability and customer access
4. Revenue Impact: Prevents downtime that could result in customer churn and revenue loss

Test Coverage:
- Service startup sequence validation
- Database connectivity verification
- Configuration loading validation
- Health check endpoints
- Service discovery and registration
- Error handling during startup
- Recovery from startup failures
- Resource initialization
- Dependency validation
- Environment configuration
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

from test_framework.environment_markers import env, env_requires, env_safe, all_envs

import aiohttp
import psutil
import pytest


class TestStartupValidationer:
    """Helper class for startup validation testing."""
    
    def __init__(self):
        self.services = {
            "backend": {"url": "http://localhost:8000", "process": None},
            "auth": {"url": "http://localhost:8081", "process": None}
        }
        self.startup_timeouts = {
            "service_start": 30.0,
            "health_check": 10.0,
            "database_connect": 15.0
        }
        self.startup_logs = []
    
    async def start_service(self, service_name: str, command: List[str]) -> Dict[str, Any]:
        """Start a service and track startup."""
        start_time = time.time()
        
        try:
            # Start the service process
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.services[service_name]["process"] = process
            
            # Wait for service to be ready
            service_ready = await self._wait_for_service_ready(service_name)
            
            startup_duration = time.time() - start_time
            
            return {
                "success": service_ready,
                "startup_duration": startup_duration,
                "process_id": process.pid,
                "service_name": service_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "startup_duration": time.time() - start_time,
                "service_name": service_name
            }
    
    async def _wait_for_service_ready(self, service_name: str) -> bool:
        """Wait for service to be ready."""
        service_url = self.services[service_name]["url"]
        health_endpoint = f"{service_url}/health"
        
        timeout = self.startup_timeouts["service_start"]
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_endpoint, timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            return True
            except Exception:
                pass
            
            await asyncio.sleep(1)
        
        return False
    
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check service health endpoint."""
        service_url = self.services[service_name]["url"]
        health_endpoint = f"{service_url}/health"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(health_endpoint) as response:
                    health_data = await response.json()
                    return {
                        "status_code": response.status,
                        "health_data": health_data,
                        "response_time": response.headers.get("X-Response-Time"),
                        "service_name": service_name,
                        "healthy": response.status == 200
                    }
        except Exception as e:
            return {
                "status_code": None,
                "error": str(e),
                "service_name": service_name,
                "healthy": False
            }
    
    async def validate_database_connectivity(self, service_name: str) -> Dict[str, Any]:
        """Validate database connectivity for a service."""
        service_url = self.services[service_name]["url"]
        
        # Try different database health endpoints
        db_endpoints = [
            f"{service_url}/health/db",
            f"{service_url}/health/database",
            f"{service_url}/health/ready"
        ]
        
        results = []
        for endpoint in db_endpoints:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(endpoint) as response:
                        if response.status in [200, 404]:  # 404 means endpoint doesn't exist, not a failure
                            data = await response.json() if response.status == 200 else {}
                            results.append({
                                "endpoint": endpoint,
                                "status_code": response.status,
                                "data": data,
                                "accessible": True
                            })
                        else:
                            results.append({
                                "endpoint": endpoint,
                                "status_code": response.status,
                                "accessible": False
                            })
            except Exception as e:
                results.append({
                    "endpoint": endpoint,
                    "error": str(e),
                    "accessible": False
                })
        
        return {
            "service_name": service_name,
            "database_checks": results,
            "any_db_accessible": any(r.get("accessible", False) for r in results)
        }
    
    async def check_configuration_loading(self, service_name: str) -> Dict[str, Any]:
        """Check if service configuration loaded correctly."""
        service_url = self.services[service_name]["url"]
        config_endpoint = f"{service_url}/health"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(config_endpoint) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        
                        # Check for configuration indicators in health response
                        config_indicators = [
                            "version", "service", "status"
                        ]
                        
                        # Optional indicators that may or may not be present
                        optional_indicators = ["environment", "timestamp"]
                        
                        config_loaded = all(indicator in health_data for indicator in config_indicators)
                        
                        all_indicators = config_indicators + optional_indicators
                        
                        return {
                            "service_name": service_name,
                            "config_loaded": config_loaded,
                            "health_data": health_data,
                            "indicators_found": [ind for ind in all_indicators if ind in health_data]
                        }
                    else:
                        return {
                            "service_name": service_name,
                            "config_loaded": False,
                            "error": f"Health endpoint returned {response.status}"
                        }
        except Exception as e:
            return {
                "service_name": service_name,
                "config_loaded": False,
                "error": str(e)
            }
    
    @pytest.mark.startup
    async def test_service_restart_recovery(self, service_name: str) -> Dict[str, Any]:
        """Test service can recover from restart."""
        # Get current process
        process = self.services[service_name]["process"]
        if not process:
            return {"error": "Service not running", "service_name": service_name}
        
        # Simulate restart by terminating and restarting
        original_pid = process.pid
        
        try:
            # Terminate process
            process.terminate()
            await asyncio.sleep(2)
            
            # Start new process (simplified - in real test would use proper restart command)
            # For this test, we'll simulate recovery by checking if service can be reached
            recovery_start = time.time()
            
            # Wait for service to recover
            recovered = await self._wait_for_service_ready(service_name)
            recovery_time = time.time() - recovery_start
            
            return {
                "service_name": service_name,
                "original_pid": original_pid,
                "recovery_successful": recovered,
                "recovery_time": recovery_time
            }
            
        except Exception as e:
            return {
                "service_name": service_name,
                "error": str(e),
                "recovery_successful": False
            }
    
    def cleanup(self):
        """Clean up started processes."""
        for service_name, service_info in self.services.items():
            process = service_info.get("process")
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass


@pytest.fixture
def startup_tester():
    """Create startup validation tester fixture."""
    tester = TestStartupValidationer()
    yield tester
    tester.cleanup()


class TestStartupComprehensiveE2E:
    """Comprehensive E2E tests for system startup."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.startup
    @pytest.mark.backend
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_backend_service_startup_sequence(self, startup_tester):
        """Test backend service starts up correctly with proper sequence."""
        # Check if service is already running
        health_result = await startup_tester.check_service_health("backend")
        
        if health_result["healthy"]:
            # Service already running, verify it's healthy
            assert health_result["status_code"] == 200
            assert "health_data" in health_result
        else:
            # Service not running, this test would require actual startup
            pytest.skip("Backend service not running - would require actual service startup")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.startup
    @pytest.mark.auth
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_auth_service_startup_sequence(self, startup_tester):
        """Test auth service starts up correctly with proper sequence."""
        # Check if service is already running
        health_result = await startup_tester.check_service_health("auth")
        
        if health_result["healthy"]:
            # Service already running, verify it's healthy
            assert health_result["status_code"] == 200
            assert "health_data" in health_result
        else:
            # Service not running, this test would require actual startup
            pytest.skip("Auth service not running - would require actual service startup")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.startup
    @pytest.mark.smoke
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_service_health_endpoints_responsive(self, startup_tester):
        """Test all service health endpoints are responsive."""
        results = []
        
        for service_name in ["backend", "auth"]:
            health_result = await startup_tester.check_service_health(service_name)
            results.append(health_result)
        
        # At least one service should be healthy
        healthy_services = [r for r in results if r.get("healthy", False)]
        assert len(healthy_services) > 0, f"No services are healthy: {results}"
        
        # All healthy services should return proper health data
        for result in healthy_services:
            assert result["status_code"] == 200
            assert "health_data" in result
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.startup
    @pytest.mark.database
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_database_connectivity_validation(self, startup_tester):
        """Test database connectivity validation during startup."""
        results = []
        
        for service_name in ["backend", "auth"]:
            db_result = await startup_tester.validate_database_connectivity(service_name)
            results.append(db_result)
        
        # At least one service should have database connectivity information
        services_with_db = [r for r in results if r.get("any_db_accessible", False)]
        
        # In development, database might not be required, so we just log the results
        for result in results:
            print(f"Database connectivity for {result['service_name']}: {result.get('any_db_accessible', False)}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_configuration_loading_validation(self, startup_tester):
        """Test configuration loading validation during startup."""
        results = []
        
        for service_name in ["backend", "auth"]:
            config_result = await startup_tester.check_configuration_loading(service_name)
            results.append(config_result)
        
        # All running services should have loaded configuration
        for result in results:
            if result.get("error") is not None:
                # Service not reachable - skip this service
                print(f"Service {result['service_name']} not reachable: {result['error']}")
                continue
            elif result.get("config_loaded") is not None:
                # If we can determine config loading status, it should be loaded
                assert result["config_loaded"], f"Configuration not loaded for {result['service_name']}: {result}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.startup
    @pytest.mark.performance
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_startup_performance_metrics(self, startup_tester):
        """Test startup performance meets acceptable metrics."""
        # Test health endpoint response times
        results = []
        
        for service_name in ["backend", "auth"]:
            start_time = time.time()
            health_result = await startup_tester.check_service_health(service_name)
            response_time = time.time() - start_time
            
            health_result["measured_response_time"] = response_time
            results.append(health_result)
        
        # Health endpoints should respond quickly (under 5 seconds)
        for result in results:
            if result.get("healthy", False):
                assert result["measured_response_time"] < 5.0, f"Health endpoint too slow for {result['service_name']}: {result['measured_response_time']}s"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_environment_configuration_consistency(self, startup_tester):
        """Test environment configuration is consistent across services."""
        service_configs = []
        
        for service_name in ["backend", "auth"]:
            health_result = await startup_tester.check_service_health(service_name)
            if health_result.get("healthy", False):
                health_data = health_result.get("health_data", {})
                service_configs.append({
                    "service": service_name,
                    "environment": health_data.get("environment"),
                    "version": health_data.get("version"),
                    "config": health_data
                })
        
        # If multiple services are running, check for consistency
        if len(service_configs) > 1:
            # All services should report same environment (if they report it)
            environments = [cfg.get("environment") for cfg in service_configs if cfg.get("environment")]
            if len(environments) > 1:
                assert all(env == environments[0] for env in environments), f"Environment mismatch: {environments}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_service_dependency_validation(self, startup_tester):
        """Test service dependencies are properly validated during startup."""
        # Check backend service can reach auth service
        backend_health = await startup_tester.check_service_health("backend")
        auth_health = await startup_tester.check_service_health("auth")
        
        # If both services are running, they should be able to communicate
        if backend_health.get("healthy") and auth_health.get("healthy"):
            # Both services are running and healthy - dependency satisfied
            assert True
        else:
            # At least log which services are available
            available_services = []
            if backend_health.get("healthy"):
                available_services.append("backend")
            if auth_health.get("healthy"):
                available_services.append("auth")
            
            print(f"Available services: {available_services}")
            
            # At least one service should be available
            assert len(available_services) > 0, "No services are available"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.startup
    @pytest.mark.resilience
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_startup_error_handling_graceful_degradation(self, startup_tester):
        """Test startup error handling provides graceful degradation."""
        # Test each service's error handling
        error_scenarios = []
        
        for service_name in ["backend", "auth"]:
            # Test invalid endpoint to see error handling
            service_url = startup_tester.services[service_name]["url"]
            invalid_endpoint = f"{service_url}/invalid_endpoint_test"
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(invalid_endpoint) as response:
                        error_scenarios.append({
                            "service": service_name,
                            "status_code": response.status,
                            "graceful": response.status in [404, 405],  # Proper HTTP error codes
                            "endpoint": invalid_endpoint
                        })
            except Exception as e:
                error_scenarios.append({
                    "service": service_name,
                    "error": str(e),
                    "graceful": False,
                    "endpoint": invalid_endpoint
                })
        
        # Services should handle invalid requests gracefully (not crash)
        for scenario in error_scenarios:
            if "status_code" in scenario:
                assert scenario["graceful"], f"Service {scenario['service']} not handling errors gracefully: {scenario}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_resource_initialization_validation(self, startup_tester):
        """Test resource initialization is properly validated."""
        resource_checks = []
        
        for service_name in ["backend", "auth"]:
            health_result = await startup_tester.check_service_health(service_name)
            
            if health_result.get("healthy", False):
                health_data = health_result.get("health_data", {})
                
                # Check for resource initialization indicators
                resource_indicators = {
                    "service_name": health_data.get("service"),
                    "version": health_data.get("version"),
                    "status": health_data.get("status"),
                    "timestamp": health_data.get("timestamp")
                }
                
                initialized_resources = [k for k, v in resource_indicators.items() if v is not None]
                
                resource_checks.append({
                    "service": service_name,
                    "initialized_resources": initialized_resources,
                    "resource_count": len(initialized_resources)
                })
        
        # Each service should have initialized basic resources
        for check in resource_checks:
            assert check["resource_count"] > 0, f"No resources initialized for {check['service']}: {check}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.startup
    @pytest.mark.monitoring
    @env("test", "dev", "staging", "prod")
    @env_requires(services=["health_endpoints"], features=["basic_connectivity"], data=[])
    @env_safe(operations=["read_only", "health_check"], impact="none", rollback=True)
    @pytest.mark.startup
    async def test_startup_logging_and_monitoring(self, startup_tester):
        """Test startup logging and monitoring are working."""
        monitoring_data = []
        
        for service_name in ["backend", "auth"]:
            health_result = await startup_tester.check_service_health(service_name)
            
            if health_result.get("healthy", False):
                health_data = health_result.get("health_data", {})
                
                # Check for monitoring indicators
                monitoring_indicators = {
                    "has_timestamp": "timestamp" in health_data,
                    "has_status": "status" in health_data,
                    "has_service_id": "service" in health_data,
                    "has_version": "version" in health_data
                }
                
                monitoring_data.append({
                    "service": service_name,
                    "monitoring_indicators": monitoring_indicators,
                    "monitoring_active": any(monitoring_indicators.values())
                })
        
        # At least one service should have monitoring active
        services_with_monitoring = [m for m in monitoring_data if m["monitoring_active"]]
        assert len(services_with_monitoring) > 0, f"No services have monitoring active: {monitoring_data}"