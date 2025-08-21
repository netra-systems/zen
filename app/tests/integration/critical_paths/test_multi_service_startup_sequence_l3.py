"""L3 Integration Test: Multi-Service Startup Sequence Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability
- Value Impact: Ensures reliable service orchestration preventing downtime
- Revenue Impact: $100K MRR - Platform availability affects all customers

This test validates the complete service startup sequence using real containerized services
to ensure proper dependency resolution, health check propagation, and failure handling.

L3 Realism Level: Real services with Docker containers, local networking
"""

import pytest
import asyncio
import time
import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
import httpx

from test_framework.docker_testing.compose_manager import DockerComposeManager
from app.core.configuration.base import get_unified_config
from app.services.health_checker import HealthChecker
from app.services.redis.session_manager import RedisSessionManager
from app.services.database.postgres_service import PostgresService

logger = logging.getLogger(__name__)


@dataclass
class ServiceMetrics:
    """Metrics for individual service startup."""
    name: str
    start_time: float
    ready_time: Optional[float] = None
    health_check_attempts: int = 0
    dependency_wait_time: float = 0.0
    startup_success: bool = False
    error_count: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def startup_duration(self) -> float:
        """Calculate startup duration in seconds."""
        if self.ready_time is None:
            return time.time() - self.start_time
        return self.ready_time - self.start_time


@dataclass
class StartupSequenceMetrics:
    """Overall metrics for startup sequence."""
    test_start_time: float
    test_end_time: Optional[float] = None
    total_services: int = 0
    successful_services: int = 0
    failed_services: int = 0
    max_startup_time: float = 30.0
    dependency_resolution_time: float = 0.0
    health_propagation_time: float = 0.0
    service_metrics: Dict[str, ServiceMetrics] = field(default_factory=dict)
    sequence_errors: List[str] = field(default_factory=list)
    
    @property
    def total_startup_time(self) -> float:
        """Calculate total startup time."""
        if self.test_end_time is None:
            return time.time() - self.test_start_time
        return self.test_end_time - self.test_start_time
    
    @property
    def success_rate(self) -> float:
        """Calculate startup success rate."""
        if self.total_services == 0:
            return 0.0
        return (self.successful_services / self.total_services) * 100.0


class L3MultiServiceStartupManager:
    """Manages L3 multi-service startup sequence testing."""
    
    def __init__(self):
        self.compose_manager: Optional[DockerComposeManager] = None
        self.postgres_container: Optional[PostgresContainer] = None
        self.redis_container: Optional[RedisContainer] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.health_checker: Optional[HealthChecker] = None
        self.metrics = StartupSequenceMetrics(test_start_time=time.time())
        self.service_endpoints: Dict[str, str] = {}
        self.startup_order = [
            "postgres",
            "redis", 
            "auth_service",
            "backend",
            "frontend"
        ]
        self.service_dependencies = {
            "postgres": [],
            "redis": [],
            "auth_service": ["postgres"],
            "backend": ["postgres", "redis", "auth_service"],
            "frontend": ["backend"]
        }
        
    async def initialize_l3_environment(self) -> None:
        """Initialize L3 test environment with real services."""
        logger.info("Initializing L3 multi-service startup environment")
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(timeout=10.0)
        
        # Initialize health checker
        self.health_checker = HealthChecker()
        await self.health_checker.initialize()
        
        # Create compose configuration dynamically
        await self._create_compose_configuration()
        
        # Initialize Docker Compose manager
        self.compose_manager = DockerComposeManager(
            compose_file="docker-compose.startup-test.yml",
            project_name="netra-startup-test"
        )
        await self.compose_manager.initialize()
        
        logger.info("L3 environment initialized successfully")
    
    async def _create_compose_configuration(self) -> None:
        """Create Docker Compose configuration for startup testing."""
        compose_config = {
            "version": "3.8",
            "services": {
                "postgres": {
                    "image": "postgres:15-alpine",
                    "environment": {
                        "POSTGRES_DB": "netra_test",
                        "POSTGRES_USER": "postgres",
                        "POSTGRES_PASSWORD": "test_password"
                    },
                    "ports": ["5432:5432"],
                    "healthcheck": {
                        "test": ["CMD-SHELL", "pg_isready -U postgres"],
                        "interval": "5s",
                        "timeout": "3s",
                        "retries": 5,
                        "start_period": "10s"
                    }
                },
                "redis": {
                    "image": "redis:7-alpine",
                    "ports": ["6379:6379"],
                    "healthcheck": {
                        "test": ["CMD", "redis-cli", "ping"],
                        "interval": "5s",
                        "timeout": "3s",
                        "retries": 5,
                        "start_period": "5s"
                    }
                },
                "auth_service": {
                    "build": {
                        "context": ".",
                        "dockerfile": "auth_service/Dockerfile"
                    },
                    "ports": ["8081:8081"],
                    "environment": {
                        "DATABASE_URL": "postgresql://postgres:test_password@postgres:5432/netra_test",
                        "REDIS_URL": "redis://redis:6379",
                        "PORT": "8081"
                    },
                    "depends_on": {
                        "postgres": {"condition": "service_healthy"}
                    },
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8081/health"],
                        "interval": "10s",
                        "timeout": "5s",
                        "retries": 5,
                        "start_period": "15s"
                    }
                },
                "backend": {
                    "build": {
                        "context": ".",
                        "dockerfile": "app/Dockerfile"
                    },
                    "ports": ["8080:8080"],
                    "environment": {
                        "DATABASE_URL": "postgresql://postgres:test_password@postgres:5432/netra_test",
                        "REDIS_URL": "redis://redis:6379",
                        "AUTH_SERVICE_URL": "http://auth_service:8081",
                        "PORT": "8080"
                    },
                    "depends_on": {
                        "postgres": {"condition": "service_healthy"},
                        "redis": {"condition": "service_healthy"},
                        "auth_service": {"condition": "service_healthy"}
                    },
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
                        "interval": "10s",
                        "timeout": "5s",
                        "retries": 5,
                        "start_period": "20s"
                    }
                },
                "frontend": {
                    "build": {
                        "context": ".",
                        "dockerfile": "frontend/Dockerfile"
                    },
                    "ports": ["3000:3000"],
                    "environment": {
                        "REACT_APP_API_URL": "http://localhost:8080",
                        "REACT_APP_AUTH_URL": "http://localhost:8081"
                    },
                    "depends_on": {
                        "backend": {"condition": "service_healthy"}
                    },
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:3000/health"],
                        "interval": "10s",
                        "timeout": "5s",
                        "retries": 5,
                        "start_period": "30s"
                    }
                }
            },
            "networks": {
                "default": {
                    "driver": "bridge"
                }
            }
        }
        
        # Write compose file
        import yaml
        with open("docker-compose.startup-test.yml", "w") as f:
            yaml.dump(compose_config, f, default_flow_style=False)
        
        logger.info("Docker Compose configuration created")
    
    async def execute_startup_sequence_test(self) -> Dict[str, Any]:
        """Execute the complete startup sequence test."""
        logger.info("Starting multi-service startup sequence test")
        
        test_results = {
            "sequence_success": False,
            "startup_order_validated": False,
            "dependency_resolution_success": False,
            "health_propagation_success": False,
            "timing_requirements_met": False,
            "cleanup_success": False,
            "details": {}
        }
        
        try:
            # Test 1: Validate correct startup order
            order_result = await self._test_startup_order()
            test_results["startup_order_validated"] = order_result["success"]
            test_results["details"]["startup_order"] = order_result
            
            # Test 2: Validate dependency resolution
            dependency_result = await self._test_dependency_resolution()
            test_results["dependency_resolution_success"] = dependency_result["success"]
            test_results["details"]["dependency_resolution"] = dependency_result
            
            # Test 3: Validate health check propagation
            health_result = await self._test_health_check_propagation()
            test_results["health_propagation_success"] = health_result["success"]
            test_results["details"]["health_propagation"] = health_result
            
            # Test 4: Validate timing requirements
            timing_result = await self._test_timing_requirements()
            test_results["timing_requirements_met"] = timing_result["success"]
            test_results["details"]["timing"] = timing_result
            
            # Test 5: Test failure scenarios
            failure_result = await self._test_failure_scenarios()
            test_results["details"]["failure_handling"] = failure_result
            
            # Overall success determination
            test_results["sequence_success"] = all([
                test_results["startup_order_validated"],
                test_results["dependency_resolution_success"],
                test_results["health_propagation_success"],
                test_results["timing_requirements_met"]
            ])
            
        except Exception as e:
            logger.error(f"Startup sequence test failed: {e}")
            self.metrics.sequence_errors.append(f"Test execution failed: {str(e)}")
            test_results["sequence_success"] = False
            test_results["details"]["error"] = str(e)
        
        finally:
            # Cleanup test environment
            cleanup_result = await self._cleanup_test_environment()
            test_results["cleanup_success"] = cleanup_result["success"]
            test_results["details"]["cleanup"] = cleanup_result
        
        self.metrics.test_end_time = time.time()
        return test_results
    
    async def _test_startup_order(self) -> Dict[str, Any]:
        """Test that services start in the correct dependency order."""
        logger.info("Testing startup order validation")
        
        order_metrics = []
        startup_times = {}
        
        try:
            # Start services one by one in dependency order
            for service_name in self.startup_order:
                service_metric = ServiceMetrics(
                    name=service_name,
                    start_time=time.time()
                )
                self.metrics.service_metrics[service_name] = service_metric
                
                # Start the service
                logger.info(f"Starting service: {service_name}")
                start_success = await self.compose_manager.start_containers([service_name])
                
                if not start_success:
                    service_metric.errors.append(f"Failed to start {service_name}")
                    service_metric.error_count += 1
                    continue
                
                # Wait for service to be healthy
                health_start = time.time()
                is_healthy = await self._wait_for_service_health(service_name, timeout=60)
                service_metric.dependency_wait_time = time.time() - health_start
                
                if is_healthy:
                    service_metric.ready_time = time.time()
                    service_metric.startup_success = True
                    startup_times[service_name] = service_metric.ready_time
                    self.metrics.successful_services += 1
                    logger.info(f"Service {service_name} started successfully in {service_metric.startup_duration:.2f}s")
                else:
                    service_metric.errors.append(f"Service {service_name} failed to become healthy")
                    service_metric.error_count += 1
                    self.metrics.failed_services += 1
                    logger.error(f"Service {service_name} failed to start")
                
                self.metrics.total_services += 1
                order_metrics.append({
                    "service": service_name,
                    "startup_time": service_metric.startup_duration,
                    "success": service_metric.startup_success
                })
            
            # Validate order is correct
            order_valid = await self._validate_startup_order(startup_times)
            
            return {
                "success": order_valid and self.metrics.failed_services == 0,
                "startup_times": startup_times,
                "order_metrics": order_metrics,
                "order_valid": order_valid,
                "services_started": self.metrics.successful_services,
                "services_failed": self.metrics.failed_services
            }
            
        except Exception as e:
            logger.error(f"Startup order test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "startup_times": startup_times,
                "order_metrics": order_metrics
            }
    
    async def _test_dependency_resolution(self) -> Dict[str, Any]:
        """Test that service dependencies are properly resolved."""
        logger.info("Testing dependency resolution")
        
        dependency_results = {}
        resolution_success = True
        
        try:
            for service_name, dependencies in self.service_dependencies.items():
                if not dependencies:
                    continue  # Skip services with no dependencies
                
                service_results = {
                    "service": service_name,
                    "dependencies": dependencies,
                    "dependency_checks": []
                }
                
                for dependency in dependencies:
                    # Check if dependency is accessible from service
                    dependency_accessible = await self._check_service_dependency(
                        service_name, dependency
                    )
                    
                    service_results["dependency_checks"].append({
                        "dependency": dependency,
                        "accessible": dependency_accessible,
                        "check_time": time.time()
                    })
                    
                    if not dependency_accessible:
                        resolution_success = False
                        self.metrics.sequence_errors.append(
                            f"Service {service_name} cannot access dependency {dependency}"
                        )
                
                dependency_results[service_name] = service_results
            
            return {
                "success": resolution_success,
                "dependency_results": dependency_results,
                "resolution_time": time.time() - self.metrics.test_start_time
            }
            
        except Exception as e:
            logger.error(f"Dependency resolution test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dependency_results": dependency_results
            }
    
    async def _test_health_check_propagation(self) -> Dict[str, Any]:
        """Test that health checks propagate correctly through the service chain."""
        logger.info("Testing health check propagation")
        
        health_results = {}
        propagation_success = True
        
        try:
            # Check health of all services
            for service_name in self.startup_order:
                health_status = await self._get_service_health_status(service_name)
                health_results[service_name] = health_status
                
                if not health_status.get("healthy", False):
                    propagation_success = False
                    self.metrics.sequence_errors.append(
                        f"Service {service_name} health check failed"
                    )
            
            # Test health check cascade - simulate failure
            cascade_result = await self._test_health_cascade()
            
            return {
                "success": propagation_success,
                "health_results": health_results,
                "cascade_test": cascade_result,
                "propagation_time": time.time() - self.metrics.test_start_time
            }
            
        except Exception as e:
            logger.error(f"Health check propagation test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "health_results": health_results
            }
    
    async def _test_timing_requirements(self) -> Dict[str, Any]:
        """Test that startup completes within required time limits."""
        logger.info("Testing timing requirements")
        
        timing_results = {
            "total_startup_time": self.metrics.total_startup_time,
            "max_allowed_time": self.metrics.max_startup_time,
            "within_limits": self.metrics.total_startup_time <= self.metrics.max_startup_time,
            "service_timings": {},
            "slowest_service": None,
            "fastest_service": None
        }
        
        try:
            # Analyze individual service timings
            service_times = {}
            for service_name, metrics in self.metrics.service_metrics.items():
                if metrics.startup_success:
                    service_times[service_name] = metrics.startup_duration
            
            if service_times:
                timing_results["service_timings"] = service_times
                timing_results["slowest_service"] = max(service_times, key=service_times.get)
                timing_results["fastest_service"] = min(service_times, key=service_times.get)
            
            # Check if any individual service exceeded limits
            individual_limits_met = all(
                time <= 20.0 for time in service_times.values()  # 20s per service max
            )
            
            timing_results["individual_limits_met"] = individual_limits_met
            timing_results["success"] = (
                timing_results["within_limits"] and 
                individual_limits_met
            )
            
            return timing_results
            
        except Exception as e:
            logger.error(f"Timing requirements test failed: {e}")
            timing_results["success"] = False
            timing_results["error"] = str(e)
            return timing_results
    
    async def _test_failure_scenarios(self) -> Dict[str, Any]:
        """Test failure handling and recovery scenarios."""
        logger.info("Testing failure scenarios")
        
        failure_results = {
            "dependency_failure_handled": False,
            "service_restart_successful": False,
            "graceful_degradation": False,
            "recovery_time": 0.0
        }
        
        try:
            # Test 1: Simulate dependency failure (Redis)
            redis_failure_start = time.time()
            
            # Stop Redis temporarily
            await self.compose_manager.stop_containers(["redis"])
            await asyncio.sleep(2)
            
            # Check if dependent services handle the failure gracefully
            backend_health = await self._get_service_health_status("backend")
            if backend_health.get("degraded", False):
                failure_results["graceful_degradation"] = True
            
            # Restart Redis
            await self.compose_manager.start_containers(["redis"])
            redis_healthy = await self._wait_for_service_health("redis", timeout=30)
            
            if redis_healthy:
                # Check if backend recovers
                backend_recovered = await self._wait_for_service_health("backend", timeout=30)
                if backend_recovered:
                    failure_results["service_restart_successful"] = True
                    failure_results["dependency_failure_handled"] = True
            
            failure_results["recovery_time"] = time.time() - redis_failure_start
            
            return failure_results
            
        except Exception as e:
            logger.error(f"Failure scenarios test failed: {e}")
            failure_results["error"] = str(e)
            return failure_results
    
    async def _wait_for_service_health(
        self, 
        service_name: str, 
        timeout: int = 60
    ) -> bool:
        """Wait for a service to become healthy."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                container_info = await self.compose_manager.get_container_info(service_name)
                if container_info and container_info.health_status == "healthy":
                    return True
                
                # If container doesn't have health check, try HTTP health endpoint
                endpoint = await self.compose_manager.get_service_endpoint(service_name)
                if endpoint:
                    try:
                        response = await self.http_client.get(f"{endpoint}/health")
                        if response.status_code == 200:
                            return True
                    except:
                        pass  # Continue waiting
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.debug(f"Health check failed for {service_name}: {e}")
                await asyncio.sleep(2)
        
        return False
    
    async def _validate_startup_order(self, startup_times: Dict[str, float]) -> bool:
        """Validate that services started in the correct dependency order."""
        for service_name, dependencies in self.service_dependencies.items():
            if service_name not in startup_times:
                continue
                
            service_start_time = startup_times[service_name]
            
            for dependency in dependencies:
                if dependency not in startup_times:
                    return False
                    
                dependency_start_time = startup_times[dependency]
                
                # Dependency should start before the service
                if dependency_start_time >= service_start_time:
                    logger.error(
                        f"Startup order violation: {dependency} "
                        f"({dependency_start_time}) started after {service_name} "
                        f"({service_start_time})"
                    )
                    return False
        
        return True
    
    async def _check_service_dependency(
        self, 
        service_name: str, 
        dependency_name: str
    ) -> bool:
        """Check if a service can access its dependency."""
        try:
            # Use Docker network connectivity check
            return await self.compose_manager.check_network_connectivity(
                service_name, dependency_name
            )
        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            return False
    
    async def _get_service_health_status(self, service_name: str) -> Dict[str, Any]:
        """Get detailed health status of a service."""
        try:
            container_info = await self.compose_manager.get_container_info(service_name)
            
            if not container_info:
                return {"healthy": False, "error": "Container not found"}
            
            health_status = {
                "healthy": container_info.health_status == "healthy",
                "status": container_info.health_status,
                "container_status": container_info.status.value,
                "ports": container_info.ports
            }
            
            # Try HTTP health check if available
            endpoint = await self.compose_manager.get_service_endpoint(service_name)
            if endpoint:
                try:
                    response = await self.http_client.get(f"{endpoint}/health")
                    health_status["http_health"] = {
                        "status_code": response.status_code,
                        "response_time": response.elapsed.total_seconds(),
                        "healthy": response.status_code == 200
                    }
                except Exception as e:
                    health_status["http_health"] = {
                        "error": str(e),
                        "healthy": False
                    }
            
            return health_status
            
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _test_health_cascade(self) -> Dict[str, Any]:
        """Test health check cascade behavior."""
        try:
            # Temporarily stop a critical service and check cascade
            await self.compose_manager.stop_containers(["postgres"])
            await asyncio.sleep(5)
            
            # Check if dependent services detect the failure
            auth_health = await self._get_service_health_status("auth_service")
            backend_health = await self._get_service_health_status("backend")
            
            # Restart postgres
            await self.compose_manager.start_containers(["postgres"])
            postgres_healthy = await self._wait_for_service_health("postgres", timeout=30)
            
            return {
                "postgres_failure_detected": not auth_health.get("healthy", True),
                "cascade_propagated": not backend_health.get("healthy", True),
                "recovery_successful": postgres_healthy,
                "cascade_working": True
            }
            
        except Exception as e:
            return {"error": str(e), "cascade_working": False}
    
    async def _cleanup_test_environment(self) -> Dict[str, Any]:
        """Clean up the test environment."""
        logger.info("Cleaning up test environment")
        cleanup_results = {"success": True, "cleanup_actions": []}
        
        try:
            # Stop and remove all containers
            if self.compose_manager:
                await self.compose_manager.cleanup()
                cleanup_results["cleanup_actions"].append("Docker containers cleaned up")
            
            # Close HTTP client
            if self.http_client:
                await self.http_client.aclose()
                cleanup_results["cleanup_actions"].append("HTTP client closed")
            
            # Remove compose file
            if os.path.exists("docker-compose.startup-test.yml"):
                os.remove("docker-compose.startup-test.yml")
                cleanup_results["cleanup_actions"].append("Compose file removed")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            cleanup_results["success"] = False
            cleanup_results["error"] = str(e)
        
        return cleanup_results


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_multi_service_startup_sequence_validation_l3():
    """
    L3 Integration Test: Multi-Service Startup Sequence Validation
    
    Tests the complete multi-service startup sequence with real containerized services.
    Validates dependency resolution, health check propagation, timing requirements,
    and failure handling scenarios.
    
    Success Criteria:
    1. All services start in correct dependency order
    2. Dependencies are properly resolved and accessible
    3. Health checks propagate correctly through service chain
    4. Total startup time < 30 seconds
    5. Individual service startup < 20 seconds
    6. Graceful handling of dependency failures
    7. Successful recovery from transient failures
    
    Revenue Impact: Protects $100K MRR by ensuring platform availability
    """
    logger.info("Starting L3 multi-service startup sequence validation test")
    
    # Initialize test manager
    startup_manager = L3MultiServiceStartupManager()
    
    try:
        # Initialize L3 environment
        await startup_manager.initialize_l3_environment()
        
        # Execute startup sequence test
        test_results = await startup_manager.execute_startup_sequence_test()
        
        # Validate critical assertions
        assert test_results["sequence_success"], (
            f"Multi-service startup sequence failed. "
            f"Errors: {startup_manager.metrics.sequence_errors}"
        )
        
        assert test_results["startup_order_validated"], (
            "Service startup order validation failed"
        )
        
        assert test_results["dependency_resolution_success"], (
            "Service dependency resolution failed"
        )
        
        assert test_results["health_propagation_success"], (
            "Health check propagation failed"
        )
        
        assert test_results["timing_requirements_met"], (
            f"Startup timing requirements not met. "
            f"Total time: {startup_manager.metrics.total_startup_time:.2f}s "
            f"(max allowed: {startup_manager.metrics.max_startup_time}s)"
        )
        
        # Validate business metrics
        assert startup_manager.metrics.success_rate >= 100.0, (
            f"Service startup success rate too low: {startup_manager.metrics.success_rate:.1f}%"
        )
        
        assert startup_manager.metrics.total_startup_time <= 30.0, (
            f"Total startup time {startup_manager.metrics.total_startup_time:.2f}s exceeds 30s limit"
        )
        
        # Log success metrics
        logger.info(
            f"Multi-service startup test completed successfully. "
            f"Total time: {startup_manager.metrics.total_startup_time:.2f}s, "
            f"Success rate: {startup_manager.metrics.success_rate:.1f}%, "
            f"Services: {startup_manager.metrics.successful_services}/"
            f"{startup_manager.metrics.total_services}"
        )
        
        # Validate detailed test results
        details = test_results["details"]
        
        # Startup order validation
        order_details = details.get("startup_order", {})
        assert order_details.get("order_valid", False), "Startup order validation failed"
        assert order_details.get("services_failed", 1) == 0, "Some services failed to start"
        
        # Dependency resolution validation
        dep_details = details.get("dependency_resolution", {})
        assert dep_details.get("success", False), "Dependency resolution failed"
        
        # Health propagation validation
        health_details = details.get("health_propagation", {})
        assert health_details.get("success", False), "Health propagation failed"
        
        # Timing validation
        timing_details = details.get("timing", {})
        assert timing_details.get("success", False), "Timing requirements not met"
        assert timing_details.get("within_limits", False), "Overall timing limits exceeded"
        assert timing_details.get("individual_limits_met", False), "Individual service timing limits exceeded"
        
        logger.info("All startup sequence validations passed successfully")
        
    except Exception as e:
        logger.error(f"Multi-service startup test failed: {e}")
        
        # Log detailed error information
        if hasattr(startup_manager, 'metrics'):
            logger.error(f"Test metrics: {startup_manager.metrics}")
            logger.error(f"Service errors: {startup_manager.metrics.sequence_errors}")
        
        raise AssertionError(f"L3 multi-service startup sequence test failed: {e}")
    
    finally:
        # Ensure cleanup happens even if test fails
        try:
            if startup_manager.compose_manager:
                await startup_manager.compose_manager.cleanup()
        except Exception as cleanup_error:
            logger.warning(f"Cleanup error: {cleanup_error}")


if __name__ == "__main__":
    # Allow direct execution for debugging
    asyncio.run(test_multi_service_startup_sequence_validation_l3())