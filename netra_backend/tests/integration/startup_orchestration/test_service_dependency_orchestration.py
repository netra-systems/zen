"""
Startup Sequence & Service Dependency Orchestration Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal + All Customer Segments
- Business Goal: Platform Reliability & Availability
- Value Impact: Ensures system starts reliably, preventing customer-facing outages
- Strategic Impact: Startup reliability directly impacts customer trust and platform uptime SLA

These tests validate service startup sequences, dependency orchestration,
and graceful degradation scenarios critical for platform reliability.
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class ServiceState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class TestStartupServiceDependencyOrchestration(BaseIntegrationTest):
    """Test startup sequences and service dependency orchestration."""

    @pytest.mark.integration
    async def test_startup_sequence_various_service_availability(self):
        """
        Test startup sequence with various service availability combinations.
        
        BVJ: Ensures platform can start even when some services are temporarily
        unavailable, maintaining customer access to core functionality.
        """
        startup_events = []
        service_states = {}
        
        class ServiceOrchestrator:
            def __init__(self):
                self.services = {
                    "database": {"priority": 1, "required": True, "state": ServiceState.STOPPED},
                    "redis": {"priority": 1, "required": True, "state": ServiceState.STOPPED},
                    "auth_service": {"priority": 2, "required": True, "state": ServiceState.STOPPED},
                    "backend": {"priority": 3, "required": True, "state": ServiceState.STOPPED},
                    "analytics": {"priority": 4, "required": False, "state": ServiceState.STOPPED},
                    "frontend": {"priority": 5, "required": False, "state": ServiceState.STOPPED}
                }
                self.startup_timeout = 30.0
                self.health_check_interval = 1.0
            
            async def start_service(self, service_name: str, availability: bool = True):
                service = self.services[service_name]
                service["state"] = ServiceState.STARTING
                startup_events.append(f"starting_{service_name}")
                
                # Simulate startup time
                startup_delay = 0.1 + (service["priority"] * 0.05)
                await asyncio.sleep(startup_delay)
                
                if availability:
                    service["state"] = ServiceState.HEALTHY
                    startup_events.append(f"healthy_{service_name}")
                    service_states[service_name] = "healthy"
                else:
                    service["state"] = ServiceState.FAILED
                    startup_events.append(f"failed_{service_name}")
                    service_states[service_name] = "failed"
                
                return service["state"]
            
            async def orchestrated_startup(self, service_availability: Dict[str, bool]):
                startup_result = {
                    "success": True,
                    "started_services": [],
                    "failed_services": [],
                    "degraded_mode": False
                }
                
                # Start services by priority
                for priority in sorted(set(s["priority"] for s in self.services.values())):
                    priority_services = [
                        name for name, config in self.services.items()
                        if config["priority"] == priority
                    ]
                    
                    # Start services in same priority group concurrently
                    startup_tasks = []
                    for service_name in priority_services:
                        available = service_availability.get(service_name, True)
                        task = self.start_service(service_name, available)
                        startup_tasks.append((service_name, task))
                    
                    # Wait for priority group to complete
                    for service_name, task in startup_tasks:
                        try:
                            state = await asyncio.wait_for(task, timeout=10.0)
                            if state == ServiceState.HEALTHY:
                                startup_result["started_services"].append(service_name)
                            else:
                                startup_result["failed_services"].append(service_name)
                                
                                # Check if failure is critical
                                if self.services[service_name]["required"]:
                                    if priority <= 2:  # Critical infrastructure
                                        startup_result["success"] = False
                                        startup_events.append(f"critical_failure_{service_name}")
                                        return startup_result
                                    else:
                                        startup_result["degraded_mode"] = True
                                        startup_events.append(f"degraded_mode_enabled")
                        
                        except asyncio.TimeoutError:
                            startup_result["failed_services"].append(service_name)
                            startup_events.append(f"timeout_{service_name}")
                
                return startup_result
        
        orchestrator = ServiceOrchestrator()
        
        # Test normal startup (all services available)
        availability_scenario_1 = {
            "database": True,
            "redis": True,
            "auth_service": True,
            "backend": True,
            "analytics": True,
            "frontend": True
        }
        
        result_1 = await orchestrator.orchestrated_startup(availability_scenario_1)
        
        assert result_1["success"] is True
        assert len(result_1["started_services"]) == 6
        assert len(result_1["failed_services"]) == 0
        assert result_1["degraded_mode"] is False
        
        # Verify startup order
        database_start = next(i for i, event in enumerate(startup_events) if event == "starting_database")
        auth_start = next(i for i, event in enumerate(startup_events) if event == "starting_auth_service")
        backend_start = next(i for i, event in enumerate(startup_events) if event == "starting_backend")
        
        assert database_start < auth_start < backend_start
        
        # Reset for next test
        startup_events.clear()
        service_states.clear()
        
        # Test startup with non-critical service failure
        availability_scenario_2 = {
            "database": True,
            "redis": True,
            "auth_service": True,
            "backend": True,
            "analytics": False,  # Non-critical service fails
            "frontend": True
        }
        
        result_2 = await orchestrator.orchestrated_startup(availability_scenario_2)
        
        assert result_2["success"] is True  # Should still succeed
        assert "analytics" in result_2["failed_services"]
        assert "analytics" not in result_2["started_services"]
        assert len(result_2["started_services"]) == 5
        
        # Test startup with critical service failure
        availability_scenario_3 = {
            "database": False,  # Critical service fails
            "redis": True,
            "auth_service": True,
            "backend": True,
            "analytics": True,
            "frontend": True
        }
        
        startup_events.clear()
        service_states.clear()
        
        result_3 = await orchestrator.orchestrated_startup(availability_scenario_3)
        
        assert result_3["success"] is False  # Should fail due to critical service
        assert "database" in result_3["failed_services"]
        assert "critical_failure_database" in startup_events

    @pytest.mark.integration
    async def test_health_check_cascade_failures_and_recovery(self):
        """
        Test health check cascade failures and recovery mechanisms.
        
        BVJ: Ensures platform can detect and recover from cascade failures,
        maintaining service availability for customers.
        """
        health_events = []
        cascade_recovery = []
        
        class HealthCheckSystem:
            def __init__(self):
                self.services = {
                    "database": {"healthy": True, "dependencies": []},
                    "redis": {"healthy": True, "dependencies": []},
                    "auth_service": {"healthy": True, "dependencies": ["database", "redis"]},
                    "backend": {"healthy": True, "dependencies": ["database", "redis", "auth_service"]},
                    "frontend": {"healthy": True, "dependencies": ["backend", "auth_service"]}
                }
                self.health_check_interval = 0.1
                self.cascade_detection_window = 0.5
                self.recovery_attempts = {}
            
            async def check_service_health(self, service_name: str):
                service = self.services[service_name]
                
                # Check dependencies first
                for dependency in service["dependencies"]:
                    if not self.services[dependency]["healthy"]:
                        health_events.append(f"dependency_unhealthy_{service_name}_{dependency}")
                        return False
                
                # Simulate health check
                health_events.append(f"health_check_{service_name}")
                return service["healthy"]
            
            async def perform_health_checks(self):
                health_results = {}
                
                for service_name in self.services:
                    is_healthy = await self.check_service_health(service_name)
                    health_results[service_name] = is_healthy
                    
                    if not is_healthy and service_name not in self.recovery_attempts:
                        self.recovery_attempts[service_name] = 0
                
                return health_results
            
            async def detect_cascade_failure(self, health_results: Dict[str, bool]):
                unhealthy_services = [name for name, healthy in health_results.items() if not healthy]
                
                if len(unhealthy_services) >= 3:  # Threshold for cascade
                    health_events.append(f"cascade_detected_{len(unhealthy_services)}_services")
                    return True
                
                return False
            
            async def attempt_recovery(self, failed_services: List[str]):
                recovery_results = []
                
                # Sort by dependency order (infrastructure first)
                service_priority = {"database": 1, "redis": 1, "auth_service": 2, "backend": 3, "frontend": 4}
                sorted_services = sorted(failed_services, key=lambda s: service_priority.get(s, 5))
                
                for service_name in sorted_services:
                    attempt_count = self.recovery_attempts.get(service_name, 0)
                    if attempt_count < 3:  # Max 3 recovery attempts
                        self.recovery_attempts[service_name] = attempt_count + 1
                        
                        cascade_recovery.append(f"recovery_attempt_{service_name}_{attempt_count + 1}")
                        
                        # Simulate recovery (50% success rate)
                        import random
                        recovery_success = random.random() > 0.5
                        
                        if recovery_success:
                            self.services[service_name]["healthy"] = True
                            cascade_recovery.append(f"recovery_success_{service_name}")
                            recovery_results.append(f"recovered_{service_name}")
                        else:
                            cascade_recovery.append(f"recovery_failed_{service_name}")
                
                return recovery_results
            
            def simulate_service_failure(self, service_name: str):
                self.services[service_name]["healthy"] = False
                health_events.append(f"service_failed_{service_name}")
        
        health_system = HealthCheckSystem()
        
        # Test normal health checks
        health_results = await health_system.perform_health_checks()
        
        assert all(health_results.values())  # All services should be healthy initially
        assert len([e for e in health_events if e.startswith("health_check")]) == 5
        
        # Simulate cascade failure (database fails, affecting dependent services)
        health_system.simulate_service_failure("database")
        
        health_results = await health_system.perform_health_checks()
        
        # Verify cascade detection
        cascade_detected = await health_system.detect_cascade_failure(health_results)
        assert cascade_detected is True
        
        # Verify dependent services are affected
        assert health_results["database"] is False
        assert health_results["auth_service"] is False  # Depends on database
        assert health_results["backend"] is False       # Depends on database and auth
        assert health_results["frontend"] is False      # Depends on backend
        
        # Test recovery
        failed_services = [name for name, healthy in health_results.items() if not healthy]
        recovery_results = await health_system.attempt_recovery(failed_services)
        
        # Verify recovery attempts were made
        assert len(cascade_recovery) > 0
        database_recovery = [e for e in cascade_recovery if "database" in e]
        assert len(database_recovery) > 0  # Database recovery should be attempted first
        
        # Test multiple recovery cycles
        for cycle in range(3):
            health_results = await health_system.perform_health_checks()
            failed_services = [name for name, healthy in health_results.items() if not healthy]
            
            if failed_services:
                recovery_results = await health_system.attempt_recovery(failed_services)
                await asyncio.sleep(0.1)  # Wait between recovery cycles
        
        # Verify recovery attempt limits
        for service_name in ["database", "auth_service", "backend", "frontend"]:
            if service_name in health_system.recovery_attempts:
                assert health_system.recovery_attempts[service_name] <= 3

    @pytest.mark.integration
    async def test_configuration_validation_during_startup(self):
        """
        Test configuration validation during startup process.
        
        BVJ: Ensures services start with valid configurations, preventing runtime
        failures that could impact customer experience.
        """
        config_validation_events = []
        startup_blockers = []
        
        class StartupConfigValidator:
            def __init__(self):
                self.required_configs = {
                    "database": ["DATABASE_URL", "DB_POOL_SIZE", "DB_TIMEOUT"],
                    "redis": ["REDIS_URL", "REDIS_MAX_CONNECTIONS"],
                    "auth_service": ["JWT_SECRET", "OAUTH_CLIENT_ID", "OAUTH_CLIENT_SECRET"],
                    "backend": ["PORT", "LOG_LEVEL", "API_RATE_LIMIT"],
                    "frontend": ["BACKEND_URL", "AUTH_URL"]
                }
                
                self.config_validators = {
                    "DATABASE_URL": self._validate_database_url,
                    "REDIS_URL": self._validate_redis_url,
                    "JWT_SECRET": self._validate_jwt_secret,
                    "PORT": self._validate_port,
                    "DB_POOL_SIZE": self._validate_positive_integer,
                    "API_RATE_LIMIT": self._validate_positive_integer
                }
            
            async def validate_service_config(self, service_name: str, config: Dict[str, Any]):
                validation_result = {
                    "service": service_name,
                    "valid": True,
                    "errors": [],
                    "warnings": []
                }
                
                required_keys = self.required_configs.get(service_name, [])
                
                # Check required configurations
                for config_key in required_keys:
                    if config_key not in config:
                        validation_result["valid"] = False
                        validation_result["errors"].append(f"missing_{config_key}")
                        config_validation_events.append(f"config_missing_{service_name}_{config_key}")
                    else:
                        # Validate config value
                        value = config[config_key]
                        validator = self.config_validators.get(config_key, self._validate_generic)
                        
                        is_valid, error_message = await validator(config_key, value)
                        if not is_valid:
                            validation_result["valid"] = False
                            validation_result["errors"].append(f"invalid_{config_key}_{error_message}")
                            config_validation_events.append(f"config_invalid_{service_name}_{config_key}")
                        else:
                            config_validation_events.append(f"config_valid_{service_name}_{config_key}")
                
                return validation_result
            
            async def _validate_database_url(self, key: str, value: str):
                if not value.startswith(("postgresql://", "postgres://")):
                    return False, "invalid_protocol"
                if "localhost" in value or "127.0.0.1" in value:
                    return True, None  # Local URLs are valid for tests
                # More validation logic would go here
                return True, None
            
            async def _validate_redis_url(self, key: str, value: str):
                if not value.startswith("redis://"):
                    return False, "invalid_protocol"
                return True, None
            
            async def _validate_jwt_secret(self, key: str, value: str):
                if len(value) < 32:
                    return False, "too_short"
                return True, None
            
            async def _validate_port(self, key: str, value: str):
                try:
                    port = int(value)
                    if port < 1 or port > 65535:
                        return False, "out_of_range"
                    return True, None
                except ValueError:
                    return False, "not_integer"
            
            async def _validate_positive_integer(self, key: str, value: str):
                try:
                    num = int(value)
                    if num <= 0:
                        return False, "not_positive"
                    return True, None
                except ValueError:
                    return False, "not_integer"
            
            async def _validate_generic(self, key: str, value: str):
                if not value or value.strip() == "":
                    return False, "empty_value"
                return True, None
            
            async def validate_all_services(self, service_configs: Dict[str, Dict[str, Any]]):
                validation_results = {}
                
                for service_name, config in service_configs.items():
                    validation_result = await self.validate_service_config(service_name, config)
                    validation_results[service_name] = validation_result
                    
                    if not validation_result["valid"]:
                        startup_blockers.append(f"config_validation_failed_{service_name}")
                
                return validation_results
        
        validator = StartupConfigValidator()
        
        # Test with valid configurations
        valid_configs = {
            "database": {
                "DATABASE_URL": "postgresql://user:pass@localhost:5432/test_db",
                "DB_POOL_SIZE": "10",
                "DB_TIMEOUT": "30"
            },
            "redis": {
                "REDIS_URL": "redis://localhost:6379",
                "REDIS_MAX_CONNECTIONS": "100"
            },
            "auth_service": {
                "JWT_SECRET": "super_secret_jwt_key_32_chars_long_123",
                "OAUTH_CLIENT_ID": "client_123",
                "OAUTH_CLIENT_SECRET": "secret_456"
            },
            "backend": {
                "PORT": "8000",
                "LOG_LEVEL": "INFO",
                "API_RATE_LIMIT": "1000"
            },
            "frontend": {
                "BACKEND_URL": "http://localhost:8000",
                "AUTH_URL": "http://localhost:8081"
            }
        }
        
        validation_results = await validator.validate_all_services(valid_configs)
        
        # Verify all services have valid configurations
        for service_name, result in validation_results.items():
            assert result["valid"] is True, f"Service {service_name} config validation failed: {result['errors']}"
            assert len(result["errors"]) == 0
        
        # Verify no startup blockers
        assert len(startup_blockers) == 0
        
        # Test with invalid configurations
        invalid_configs = {
            "database": {
                "DATABASE_URL": "invalid://not_a_valid_url",  # Invalid protocol
                "DB_POOL_SIZE": "not_a_number",               # Invalid type
                # Missing DB_TIMEOUT
            },
            "redis": {
                "REDIS_URL": "redis://localhost:6379",
                "REDIS_MAX_CONNECTIONS": "-5"  # Invalid value
            },
            "auth_service": {
                "JWT_SECRET": "short",  # Too short
                "OAUTH_CLIENT_ID": "client_123",
                "OAUTH_CLIENT_SECRET": ""  # Empty value
            },
            "backend": {
                "PORT": "99999",  # Out of range
                "LOG_LEVEL": "INFO",
                "API_RATE_LIMIT": "1000"
            }
        }
        
        config_validation_events.clear()
        startup_blockers.clear()
        
        validation_results_invalid = await validator.validate_all_services(invalid_configs)
        
        # Verify configuration validation caught errors
        assert validation_results_invalid["database"]["valid"] is False
        assert "missing_DB_TIMEOUT" in validation_results_invalid["database"]["errors"]
        assert "invalid_DATABASE_URL_invalid_protocol" in validation_results_invalid["database"]["errors"]
        
        assert validation_results_invalid["auth_service"]["valid"] is False
        assert "invalid_JWT_SECRET_too_short" in validation_results_invalid["auth_service"]["errors"]
        
        # Verify startup blockers recorded
        assert len(startup_blockers) >= 3  # At least database, auth_service, backend should fail

    @pytest.mark.integration
    async def test_service_dependency_ordering_and_timing(self):
        """
        Test service dependency ordering and timing requirements.
        
        BVJ: Ensures services start in correct order with proper timing,
        preventing startup race conditions that could cause platform instability.
        """
        startup_timeline = []
        dependency_violations = []
        
        class DependencyOrchestrator:
            def __init__(self):
                self.services = {
                    "infrastructure": {
                        "database": {"startup_time": 2.0, "dependencies": []},
                        "redis": {"startup_time": 1.0, "dependencies": []},
                        "message_queue": {"startup_time": 1.5, "dependencies": []}
                    },
                    "core_services": {
                        "auth_service": {"startup_time": 3.0, "dependencies": ["database", "redis"]},
                        "user_service": {"startup_time": 2.5, "dependencies": ["database", "auth_service"]}
                    },
                    "application_services": {
                        "backend": {"startup_time": 4.0, "dependencies": ["database", "redis", "auth_service"]},
                        "websocket_service": {"startup_time": 2.0, "dependencies": ["backend", "auth_service"]},
                        "analytics": {"startup_time": 3.5, "dependencies": ["database", "message_queue"]}
                    },
                    "frontend_services": {
                        "frontend": {"startup_time": 1.5, "dependencies": ["backend", "websocket_service"]}
                    }
                }
                
                self.service_states = {}
                self.startup_times = {}
            
            async def start_service(self, service_name: str, service_config: Dict[str, Any]):
                # Check dependencies
                for dependency in service_config["dependencies"]:
                    if dependency not in self.service_states or self.service_states[dependency] != "running":
                        dependency_violations.append(f"dependency_not_ready_{service_name}_{dependency}")
                        startup_timeline.append({
                            "event": "dependency_violation",
                            "service": service_name,
                            "missing_dependency": dependency,
                            "timestamp": time.time()
                        })
                        raise RuntimeError(f"Dependency {dependency} not ready for {service_name}")
                
                # Start service
                startup_timeline.append({
                    "event": "service_starting",
                    "service": service_name,
                    "timestamp": time.time()
                })
                
                self.service_states[service_name] = "starting"
                
                # Simulate startup time (scaled down for testing)
                scaled_startup_time = service_config["startup_time"] * 0.1
                await asyncio.sleep(scaled_startup_time)
                
                self.service_states[service_name] = "running"
                self.startup_times[service_name] = time.time()
                
                startup_timeline.append({
                    "event": "service_ready",
                    "service": service_name, 
                    "timestamp": time.time(),
                    "startup_duration": scaled_startup_time
                })
                
                return "running"
            
            async def orchestrated_startup_sequence(self):
                startup_order = []
                
                # Start services tier by tier
                for tier_name, tier_services in self.services.items():
                    startup_timeline.append({
                        "event": "tier_starting",
                        "tier": tier_name,
                        "timestamp": time.time()
                    })
                    
                    # Start services in tier concurrently (they should have same dependencies satisfied)
                    tier_tasks = []
                    for service_name, service_config in tier_services.items():
                        task = self.start_service(service_name, service_config)
                        tier_tasks.append((service_name, task))
                    
                    # Wait for all services in tier to start
                    tier_results = []
                    for service_name, task in tier_tasks:
                        try:
                            result = await task
                            tier_results.append((service_name, result))
                            startup_order.append(service_name)
                        except RuntimeError as e:
                            startup_timeline.append({
                                "event": "service_failed",
                                "service": service_name,
                                "error": str(e),
                                "timestamp": time.time()
                            })
                            raise
                    
                    startup_timeline.append({
                        "event": "tier_complete",
                        "tier": tier_name,
                        "timestamp": time.time(),
                        "services": [name for name, _ in tier_results]
                    })
                
                return {
                    "startup_order": startup_order,
                    "final_states": self.service_states,
                    "startup_times": self.startup_times
                }
        
        orchestrator = DependencyOrchestrator()
        
        # Test proper startup sequence
        startup_result = await orchestrator.orchestrated_startup_sequence()
        
        # Verify no dependency violations
        assert len(dependency_violations) == 0, f"Dependency violations: {dependency_violations}"
        
        # Verify all services started
        assert len(startup_result["startup_order"]) == 9  # All services
        assert all(state == "running" for state in startup_result["final_states"].values())
        
        # Verify startup order respects dependencies
        startup_order = startup_result["startup_order"]
        
        # Infrastructure should start first
        infra_services = ["database", "redis", "message_queue"]
        infra_positions = [startup_order.index(s) for s in infra_services]
        
        # Core services should start after infrastructure
        core_services = ["auth_service", "user_service"]
        core_positions = [startup_order.index(s) for s in core_services]
        
        # Application services should start after core services
        app_services = ["backend", "websocket_service", "analytics"]
        app_positions = [startup_order.index(s) for s in app_services]
        
        # Frontend should start last
        frontend_position = startup_order.index("frontend")
        
        # Verify ordering
        assert max(infra_positions) < min(core_positions), "Core services started before infrastructure"
        assert max(core_positions) < min(app_positions), "Application services started before core services"
        assert frontend_position > max(app_positions), "Frontend started before application services"
        
        # Verify specific dependency relationships
        database_pos = startup_order.index("database")
        auth_pos = startup_order.index("auth_service")
        backend_pos = startup_order.index("backend")
        frontend_pos = startup_order.index("frontend")
        
        assert database_pos < auth_pos, "Auth service started before database"
        assert auth_pos < backend_pos, "Backend started before auth service"
        assert backend_pos < frontend_pos, "Frontend started before backend"

    @pytest.mark.integration
    async def test_startup_performance_under_resource_constraints(self):
        """
        Test startup performance under various resource constraints.
        
        BVJ: Ensures platform can start efficiently even with limited resources,
        important for cost-effective deployment and customer environments.
        """
        performance_metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "startup_times": {},
            "resource_warnings": []
        }
        
        class ResourceConstrainedStartup:
            def __init__(self, cpu_limit: float = 1.0, memory_limit_mb: int = 512):
                self.cpu_limit = cpu_limit  # CPU cores
                self.memory_limit_mb = memory_limit_mb
                self.current_cpu_usage = 0.0
                self.current_memory_mb = 0
                self.services = {
                    "database": {"cpu_req": 0.3, "memory_req": 128},
                    "redis": {"cpu_req": 0.1, "memory_req": 64},
                    "auth_service": {"cpu_req": 0.2, "memory_req": 96},
                    "backend": {"cpu_req": 0.4, "memory_req": 192},
                    "frontend": {"cpu_req": 0.1, "memory_req": 48}
                }
            
            async def check_resource_availability(self, service_name: str):
                service = self.services[service_name]
                cpu_needed = service["cpu_req"]
                memory_needed = service["memory_req"]
                
                # Check if resources are available
                if self.current_cpu_usage + cpu_needed > self.cpu_limit:
                    performance_metrics["resource_warnings"].append(f"cpu_constraint_{service_name}")
                    return False, "cpu_limit"
                
                if self.current_memory_mb + memory_needed > self.memory_limit_mb:
                    performance_metrics["resource_warnings"].append(f"memory_constraint_{service_name}")
                    return False, "memory_limit"
                
                return True, None
            
            async def start_service_with_resources(self, service_name: str):
                service = self.services[service_name]
                start_time = time.time()
                
                # Check resource availability
                available, constraint = await self.check_resource_availability(service_name)
                
                if not available:
                    performance_metrics["resource_warnings"].append(f"delayed_start_{service_name}_{constraint}")
                    # Simulate waiting for resources
                    await asyncio.sleep(0.5)
                    
                    # Try again (simulate resource becoming available)
                    available, constraint = await self.check_resource_availability(service_name)
                    if not available:
                        raise ResourceError(f"Insufficient {constraint} for {service_name}")
                
                # Allocate resources
                self.current_cpu_usage += service["cpu_req"]
                self.current_memory_mb += service["memory_req"]
                
                # Record resource usage
                performance_metrics["cpu_usage"].append(self.current_cpu_usage)
                performance_metrics["memory_usage"].append(self.current_memory_mb)
                
                # Simulate startup with resource constraints
                # More constrained resources = longer startup time
                resource_pressure = (self.current_cpu_usage / self.cpu_limit + 
                                   self.current_memory_mb / self.memory_limit_mb) / 2
                
                base_startup_time = 0.1
                constrained_startup_time = base_startup_time * (1 + resource_pressure)
                
                await asyncio.sleep(constrained_startup_time)
                
                startup_duration = time.time() - start_time
                performance_metrics["startup_times"][service_name] = startup_duration
                
                return {
                    "service": service_name,
                    "startup_time": startup_duration,
                    "cpu_used": service["cpu_req"],
                    "memory_used": service["memory_req"],
                    "resource_pressure": resource_pressure
                }
            
            async def optimized_startup_sequence(self):
                # Sort services by resource efficiency (startup_time / resources_used)
                def resource_efficiency(service_name):
                    service = self.services[service_name]
                    resource_score = service["cpu_req"] + (service["memory_req"] / 100)
                    return resource_score  # Lower is more efficient
                
                sorted_services = sorted(self.services.keys(), key=resource_efficiency)
                
                startup_results = []
                for service_name in sorted_services:
                    try:
                        result = await self.start_service_with_resources(service_name)
                        startup_results.append(result)
                    except ResourceError as e:
                        startup_results.append({
                            "service": service_name,
                            "error": str(e),
                            "resource_constrained": True
                        })
                
                return {
                    "startup_results": startup_results,
                    "final_cpu_usage": self.current_cpu_usage,
                    "final_memory_usage": self.current_memory_mb,
                    "total_services": len(startup_results)
                }
        
        class ResourceError(Exception):
            pass
        
        # Test startup under normal resource constraints
        normal_startup = ResourceConstrainedStartup(cpu_limit=2.0, memory_limit_mb=1024)
        normal_result = await normal_startup.optimized_startup_sequence()
        
        # Verify all services started successfully
        successful_starts = [r for r in normal_result["startup_results"] if "error" not in r]
        assert len(successful_starts) == 5  # All services
        
        # Verify resource usage within limits
        assert normal_result["final_cpu_usage"] <= 2.0
        assert normal_result["final_memory_usage"] <= 1024
        
        # Test startup under severe resource constraints
        performance_metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "startup_times": {},
            "resource_warnings": []
        }
        
        constrained_startup = ResourceConstrainedStartup(cpu_limit=0.8, memory_limit_mb=300)
        constrained_result = await constrained_startup.optimized_startup_sequence()
        
        # Some services may fail to start due to resource constraints
        failed_starts = [r for r in constrained_result["startup_results"] if "error" in r]
        successful_constrained = [r for r in constrained_result["startup_results"] if "error" not in r]
        
        # At least lightweight services should start
        assert len(successful_constrained) >= 2  # Redis and frontend should fit
        
        # Verify resource warnings were generated
        assert len(performance_metrics["resource_warnings"]) > 0
        
        # Verify performance metrics collected
        assert len(performance_metrics["cpu_usage"]) > 0
        assert len(performance_metrics["memory_usage"]) > 0
        assert len(performance_metrics["startup_times"]) > 0
        
        # Test resource-aware startup ordering
        lightweight_services = ["redis", "frontend"]  # Should start first under constraints
        heavyweight_services = ["backend", "database"]  # May be delayed or fail
        
        for result in successful_constrained:
            service_name = result["service"]
            if service_name in lightweight_services:
                # Lightweight services should start relatively quickly even under constraints
                assert result["startup_time"] < 1.0
            
            # All started services should have reasonable resource pressure
            assert result.get("resource_pressure", 0) < 2.0  # Shouldn't be extremely constrained

    @pytest.mark.integration
    async def test_graceful_degradation_mode_functionality(self):
        """
        Test graceful degradation mode when critical services are unavailable.
        
        BVJ: Ensures customers can still access core platform features even when
        some services are down, maintaining business continuity.
        """
        degradation_events = []
        feature_availability = {}
        
        class GracefulDegradationManager:
            def __init__(self):
                self.service_status = {
                    "database": "healthy",
                    "redis": "healthy",
                    "auth_service": "healthy",
                    "backend": "healthy",
                    "analytics": "healthy",
                    "frontend": "healthy"
                }
                
                self.feature_requirements = {
                    "user_authentication": ["auth_service", "database"],
                    "chat_interface": ["backend", "frontend", "database"],
                    "agent_execution": ["backend", "database", "redis"],
                    "cost_optimization": ["backend", "database", "analytics"],
                    "reporting": ["backend", "database", "analytics"],
                    "user_profile": ["backend", "database", "auth_service"],
                    "real_time_updates": ["backend", "redis"]
                }
                
                self.degradation_alternatives = {
                    "cost_optimization": "basic_cost_optimization",  # Fallback without analytics
                    "reporting": "cached_reports",                  # Use cached data
                    "real_time_updates": "polling_updates"          # Fallback to polling
                }
            
            async def assess_service_health(self):
                health_assessment = {}
                
                for service_name, status in self.service_status.items():
                    health_assessment[service_name] = status
                    if status != "healthy":
                        degradation_events.append(f"service_degraded_{service_name}")
                
                return health_assessment
            
            async def determine_feature_availability(self):
                service_health = await self.assess_service_health()
                
                for feature_name, required_services in self.feature_requirements.items():
                    # Check if all required services are healthy
                    all_healthy = all(
                        service_health.get(service, "unknown") == "healthy" 
                        for service in required_services
                    )
                    
                    if all_healthy:
                        feature_availability[feature_name] = "available"
                        degradation_events.append(f"feature_available_{feature_name}")
                    else:
                        # Check if degraded alternative exists
                        alternative = self.degradation_alternatives.get(feature_name)
                        if alternative:
                            feature_availability[feature_name] = f"degraded_{alternative}"
                            degradation_events.append(f"feature_degraded_{feature_name}_{alternative}")
                        else:
                            feature_availability[feature_name] = "unavailable"
                            degradation_events.append(f"feature_unavailable_{feature_name}")
                
                return feature_availability
            
            async def enable_degradation_mode(self, failed_services: List[str]):
                degradation_config = {
                    "mode": "degraded",
                    "failed_services": failed_services,
                    "available_features": [],
                    "degraded_features": [],
                    "unavailable_features": []
                }
                
                # Update service status
                for service in failed_services:
                    self.service_status[service] = "failed"
                
                # Reassess feature availability
                features = await self.determine_feature_availability()
                
                for feature, status in features.items():
                    if status == "available":
                        degradation_config["available_features"].append(feature)
                    elif status.startswith("degraded_"):
                        degradation_config["degraded_features"].append({
                            "feature": feature,
                            "alternative": status.split("degraded_")[1]
                        })
                    else:
                        degradation_config["unavailable_features"].append(feature)
                
                degradation_events.append(f"degradation_mode_enabled_{len(failed_services)}_services")
                
                return degradation_config
        
        degradation_manager = GracefulDegradationManager()
        
        # Test normal operation (all services healthy)
        features = await degradation_manager.determine_feature_availability()
        
        # All features should be available initially
        assert all(status == "available" for status in features.values())
        assert len([e for e in degradation_events if e.startswith("feature_available")]) == 7
        
        # Test degradation when analytics service fails
        degradation_events.clear()
        feature_availability.clear()
        
        degradation_config_1 = await degradation_manager.enable_degradation_mode(["analytics"])
        
        # Verify degradation mode configuration
        assert degradation_config_1["mode"] == "degraded"
        assert "analytics" in degradation_config_1["failed_services"]
        
        # Features not requiring analytics should remain available
        available_features = degradation_config_1["available_features"]
        assert "user_authentication" in available_features
        assert "chat_interface" in available_features
        assert "agent_execution" in available_features
        
        # Features requiring analytics should be degraded or unavailable
        degraded_features = degradation_config_1["degraded_features"]
        degraded_feature_names = [f["feature"] for f in degraded_features]
        
        assert "cost_optimization" in degraded_feature_names
        assert "reporting" in degraded_feature_names
        
        # Test severe degradation (multiple critical services fail)
        degradation_events.clear()
        feature_availability.clear()
        
        degradation_config_2 = await degradation_manager.enable_degradation_mode(["database", "redis"])
        
        # With database down, most features should be unavailable
        unavailable_features = degradation_config_2["unavailable_features"]
        
        # Database is required for most features
        assert "user_authentication" in unavailable_features
        assert "chat_interface" in unavailable_features
        assert "agent_execution" in unavailable_features
        
        # Only frontend might still be available in very limited capacity
        available_features = degradation_config_2["available_features"]
        assert len(available_features) <= 1  # Very limited functionality
        
        # Verify degradation events were properly logged
        database_events = [e for e in degradation_events if "database" in e]
        redis_events = [e for e in degradation_events if "redis" in e]
        
        assert len(database_events) > 0
        assert len(redis_events) > 0
        assert "degradation_mode_enabled_2_services" in degradation_events
        
        # Test partial recovery scenario
        degradation_manager.service_status["database"] = "healthy"  # Database recovers
        
        degradation_events.clear()
        feature_availability.clear()
        
        recovery_features = await degradation_manager.determine_feature_availability()
        
        # With database recovered, most features should be available again
        recovered_features = [name for name, status in recovery_features.items() if status == "available"]
        
        assert "user_authentication" in recovered_features
        assert "chat_interface" in recovered_features
        assert "user_profile" in recovered_features
        
        # Redis-dependent features might still be degraded
        assert "real_time_updates" in feature_availability
        redis_dependent_status = feature_availability["real_time_updates"]
        assert "degraded" in redis_dependent_status or redis_dependent_status == "unavailable"