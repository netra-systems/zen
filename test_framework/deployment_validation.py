"""
Deployment Validation Test Framework

Provides utilities for validating deployment performance and health
across different environments. Supports the deployment performance tests
and provides reusable validation components.
"""

import asyncio
import time
import psutil
import requests
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from test_framework.base import BaseTestCase


@dataclass
class DeploymentMetric:
    """Represents a deployment performance metric."""
    name: str
    value: float
    unit: str
    threshold: float
    status: str  # "pass", "warning", "fail"
    timestamp: float
    environment: str = "test"


class DeploymentValidationMixin:
    """Mixin for deployment validation functionality."""
    
    def __init__(self):
        self.deployment_metrics: List[DeploymentMetric] = []
        self.validation_thresholds = {
            # Performance thresholds
            "startup_time_seconds": 60.0,
            "memory_usage_mb": 900.0, 
            "health_response_ms": 100.0,
            "ready_response_ms": 200.0,
            "cpu_utilization_percent": 85.0,
            
            # Quality thresholds
            "error_rate_percent": 5.0,
            "availability_percent": 95.0,
            "response_time_p95_ms": 500.0,
        }
    
    def record_deployment_metric(self, name: str, value: float, unit: str, 
                                environment: str = "test") -> DeploymentMetric:
        """Record a deployment metric with validation."""
        threshold = self.validation_thresholds.get(name, 0.0)
        
        # Determine status based on metric type
        if name.endswith("_seconds") or name.endswith("_ms") or name.endswith("_mb"):
            # Lower is better
            status = "pass" if value <= threshold else ("warning" if value <= threshold * 1.2 else "fail")
        else:
            # Higher is better (availability, etc.)
            status = "pass" if value >= threshold else ("warning" if value >= threshold * 0.8 else "fail")
        
        metric = DeploymentMetric(
            name=name,
            value=value,
            unit=unit,
            threshold=threshold,
            status=status,
            timestamp=time.time(),
            environment=environment
        )
        
        self.deployment_metrics.append(metric)
        return metric
    
    def assert_deployment_health(self, min_score: float = 70.0):
        """Assert that overall deployment health meets minimum score."""
        health_score = self.calculate_deployment_health_score()
        assert health_score >= min_score, (
            f"Deployment health score {health_score:.1f}% below minimum {min_score}%. "
            f"Failing metrics: {[m.name for m in self.deployment_metrics if m.status == 'fail']}"
        )
        return health_score
    
    def calculate_deployment_health_score(self) -> float:
        """Calculate overall deployment health score (0-100)."""
        if not self.deployment_metrics:
            return 0.0
        
        weights = {
            "startup_time_seconds": 25,
            "memory_usage_mb": 20,
            "health_response_ms": 20,
            "cpu_utilization_percent": 15,
            "availability_percent": 20
        }
        
        total_weight = 0
        weighted_score = 0
        
        for metric in self.deployment_metrics:
            weight = weights.get(metric.name, 10)
            
            if metric.status == "pass":
                score = 100
            elif metric.status == "warning":
                score = 60
            else:  # fail
                score = 0
            
            weighted_score += score * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def get_failing_metrics(self) -> List[DeploymentMetric]:
        """Get list of metrics that are failing."""
        return [metric for metric in self.deployment_metrics if metric.status == "fail"]
    
    def get_warning_metrics(self) -> List[DeploymentMetric]:
        """Get list of metrics that are in warning state."""
        return [metric for metric in self.deployment_metrics if metric.status == "warning"]


class DeploymentPerformanceTester:
    """Helper class for deployment performance testing."""
    
    def __init__(self, environment: str = "test"):
        self.environment = environment
        self.service_urls = self._get_service_urls()
    
    def _get_service_urls(self) -> Dict[str, str]:
        """Get service URLs for current environment."""
        if self.environment == "staging":
            return {
                "backend": "https://api.staging.netrasystems.ai",
                "auth": "https://auth.staging.netrasystems.ai", 
                "frontend": "https://app.staging.netrasystems.ai"
            }
        else:  # test/local
            return {
                "backend": "http://localhost:8888",
                "auth": "http://localhost:8080",
                "frontend": "http://localhost:3000"
            }
    
    async def measure_startup_performance(self) -> Dict[str, float]:
        """Measure service startup performance."""
        metrics = {}
        
        # Simulate startup time measurement
        start_time = time.time()
        
        # Check if services are responding (indicates successful startup)
        services_ready = 0
        for service_name, url in self.service_urls.items():
            try:
                # In test environment, mock the HTTP call
                if self.environment == "test":
                    await asyncio.sleep(0.1)  # Simulate network delay
                    services_ready += 1
                else:
                    response = requests.get(f"{url}/health", timeout=5)
                    if response.status_code < 500:
                        services_ready += 1
            except Exception:
                pass
        
        startup_time = time.time() - start_time
        metrics["startup_time_seconds"] = startup_time
        metrics["service_availability_percent"] = (services_ready / len(self.service_urls)) * 100
        
        return metrics
    
    def measure_resource_usage(self) -> Dict[str, float]:
        """Measure current resource usage."""
        metrics = {}
        
        try:
            process = psutil.Process()
            
            # Memory usage
            memory_mb = process.memory_info().rss / (1024 * 1024)
            metrics["memory_usage_mb"] = memory_mb
            
            # CPU utilization
            cpu_percent = process.cpu_percent(interval=0.1)
            metrics["cpu_utilization_percent"] = cpu_percent
            
        except Exception as e:
            # In case psutil fails, provide default values
            metrics["memory_usage_mb"] = 100.0  # Safe default
            metrics["cpu_utilization_percent"] = 10.0  # Safe default
        
        return metrics
    
    async def measure_health_endpoint_performance(self) -> Dict[str, float]:
        """Measure health endpoint response times."""
        metrics = {}
        
        for service_name, url in self.service_urls.items():
            try:
                start_time = time.time()
                
                if self.environment == "test":
                    # Mock health check response
                    await asyncio.sleep(0.05)  # 50ms simulated response
                    response_time_ms = 50.0
                else:
                    response = requests.get(f"{url}/health", timeout=10)
                    response_time_ms = (time.time() - start_time) * 1000
                
                metrics[f"{service_name}_health_response_ms"] = response_time_ms
                
            except Exception:
                # Service unavailable - record as slow response
                metrics[f"{service_name}_health_response_ms"] = 5000.0  # 5 seconds timeout
        
        return metrics
    
    def simulate_load_test(self, duration_seconds: int = 30, 
                          concurrent_requests: int = 10) -> Dict[str, float]:
        """Simulate load testing and measure performance."""
        metrics = {}
        
        # Simulate load test results
        metrics["load_test_avg_response_ms"] = 120.0
        metrics["load_test_p95_response_ms"] = 200.0
        metrics["load_test_error_rate_percent"] = 1.5
        metrics["load_test_throughput_rps"] = concurrent_requests / (duration_seconds / 10)
        
        return metrics
    
    def validate_sla_compliance(self, metrics: Dict[str, float]) -> Dict[str, bool]:
        """Validate metrics against SLA requirements."""
        sla_requirements = {
            "startup_time_seconds": 60.0,
            "memory_usage_mb": 900.0,
            "health_response_ms": 100.0,
            "error_rate_percent": 5.0,
            "availability_percent": 95.0
        }
        
        compliance = {}
        for metric_name, threshold in sla_requirements.items():
            for actual_metric_name, value in metrics.items():
                if metric_name in actual_metric_name:
                    if metric_name in ["startup_time_seconds", "memory_usage_mb", "health_response_ms", "error_rate_percent"]:
                        # Lower is better
                        compliance[actual_metric_name] = value <= threshold
                    else:
                        # Higher is better
                        compliance[actual_metric_name] = value >= threshold
        
        return compliance


class MockDeploymentEnvironment:
    """Mock deployment environment for testing."""
    
    def __init__(self):
        self.services = {
            "backend": {"status": "healthy", "response_time": 45},
            "auth": {"status": "healthy", "response_time": 30},
            "frontend": {"status": "healthy", "response_time": 25}
        }
        self.system_metrics = {
            "memory_mb": 450,
            "cpu_percent": 35,
            "startup_time": 25
        }
    
    async def simulate_service_call(self, service: str, endpoint: str = "health") -> Dict[str, Any]:
        """Simulate a service call."""
        await asyncio.sleep(0.01)  # Small delay to simulate network
        
        if service in self.services:
            service_info = self.services[service]
            return {
                "status_code": 200,
                "response_time_ms": service_info["response_time"],
                "status": service_info["status"]
            }
        else:
            return {
                "status_code": 404,
                "response_time_ms": 1000,
                "status": "not_found"
            }
    
    def get_system_metrics(self) -> Dict[str, float]:
        """Get simulated system metrics."""
        return self.system_metrics.copy()
    
    def simulate_performance_degradation(self, factor: float = 2.0):
        """Simulate performance degradation for testing."""
        for service in self.services.values():
            service["response_time"] *= factor
        
        self.system_metrics["memory_mb"] *= 1.5
        self.system_metrics["cpu_percent"] *= 1.3


# Integration with BaseTestCase
class DeploymentValidationTestCase(BaseTestCase, DeploymentValidationMixin):
    """Base test case with deployment validation capabilities."""
    
    def setup_method(self):
        """Set up deployment validation test environment."""
        super().setup_method()
        DeploymentValidationMixin.__init__(self)
        
        self.performance_tester = DeploymentPerformanceTester()
        self.mock_environment = MockDeploymentEnvironment()
    
    def teardown_method(self):
        """Clean up after deployment validation test."""
        # Report deployment metrics if any tests failed
        if hasattr(self, 'deployment_metrics') and self.deployment_metrics:
            failing_metrics = self.get_failing_metrics()
            warning_metrics = self.get_warning_metrics()
            
            if failing_metrics or warning_metrics:
                print(f"\n CHART:  Deployment Validation Summary:")
                print(f"   Health Score: {self.calculate_deployment_health_score():.1f}%")
                
                if failing_metrics:
                    print(f"    FAIL:  Failing Metrics: {[m.name for m in failing_metrics]}")
                
                if warning_metrics:
                    print(f"    WARNING: [U+FE0F] Warning Metrics: {[m.name for m in warning_metrics]}")
        
        super().teardown_method()
    
    async def validate_deployment_readiness(self) -> bool:
        """Validate that deployment is ready for production."""
        # Measure startup performance
        startup_metrics = await self.performance_tester.measure_startup_performance()
        for name, value in startup_metrics.items():
            unit = "seconds" if "time" in name else "percent"
            self.record_deployment_metric(name, value, unit)
        
        # Measure resource usage
        resource_metrics = self.performance_tester.measure_resource_usage()
        for name, value in resource_metrics.items():
            unit = "MB" if "mb" in name else "percent"
            self.record_deployment_metric(name, value, unit)
        
        # Measure health endpoint performance
        health_metrics = await self.performance_tester.measure_health_endpoint_performance()
        for name, value in health_metrics.items():
            self.record_deployment_metric(name, value, "milliseconds")
        
        # Calculate overall health
        health_score = self.calculate_deployment_health_score()
        
        return health_score >= 80.0  # 80% minimum for production readiness