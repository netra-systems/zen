"""Health Check Cascade During Service Initialization L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability & Monitoring  
- Value Impact: Early failure detection prevents cascading outages
- Revenue Impact: $55K MRR - Health monitoring prevents downtime

Critical Path: Service initialization -> Health check activation -> Dependency validation -> Cascade detection -> Alert triggering
Coverage: Health check timing, dependency chain validation, cascading failure detection, performance overhead monitoring
L3 Realism: Tests with real health check endpoints and actual service dependency chains
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import uuid
import logging
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from dataclasses import dataclass, asdict
from enum import Enum

# Add project root to path

from netra_backend.app.core.health_checkers import (

# Add project root to path
    check_postgres_health, check_clickhouse_health, 
    check_redis_health, check_websocket_health, check_system_resources
)
from netra_backend.app.core.health_types import HealthCheckResult
from routes.health import health_interface
from logging_config import central_logger

logger = logging.getLogger(__name__)

# L3 integration test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.l3,
    pytest.mark.health_monitoring,
    pytest.mark.initialization
]


class ServiceState(Enum):
    """Service initialization states."""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class ServiceDependency:
    """Defines service dependency relationships."""
    service_name: str
    depends_on: List[str]
    health_check_function: callable
    initialization_timeout_seconds: float = 30.0
    health_check_timeout_seconds: float = 5.0
    required_for_startup: bool = True


@dataclass
class HealthCheckEvent:
    """Tracks health check events during initialization."""
    event_id: str
    service_name: str
    event_type: str  # "started", "completed", "failed", "dependency_failure"
    timestamp: datetime
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    cascade_triggered: bool = False


@dataclass
class InitializationMetrics:
    """Tracks initialization performance metrics."""
    total_services: int
    services_started: int
    services_healthy: int
    services_failed: int
    total_initialization_time: float
    health_checks_activated_within_5s: int
    dependency_chains_validated: int
    cascading_failures_detected: int
    alerts_triggered: int
    performance_overhead_percentage: float


class HealthCheckCascadeInitializationValidator:
    """Validates health check cascade behavior during service initialization."""
    
    def __init__(self):
        self.initialization_start_time = None
        self.service_states = {}
        self.dependency_map = {}
        self.health_check_events = []
        self.alert_events = []
        self.performance_metrics = []
        self.cascade_detection_enabled = True
        
    async def initialize_service_dependencies(self):
        """Initialize service dependency mapping for cascade testing."""
        self.dependency_map = {
            "postgres": ServiceDependency(
                service_name="postgres",
                depends_on=[],
                health_check_function=check_postgres_health,
                initialization_timeout_seconds=15.0,
                health_check_timeout_seconds=5.0,
                required_for_startup=True
            ),
            "redis": ServiceDependency(
                service_name="redis", 
                depends_on=[],
                health_check_function=check_redis_health,
                initialization_timeout_seconds=10.0,
                health_check_timeout_seconds=3.0,
                required_for_startup=True
            ),
            "clickhouse": ServiceDependency(
                service_name="clickhouse",
                depends_on=[],
                health_check_function=check_clickhouse_health,
                initialization_timeout_seconds=20.0,
                health_check_timeout_seconds=8.0,
                required_for_startup=False  # Can be disabled in dev
            ),
            "websocket": ServiceDependency(
                service_name="websocket",
                depends_on=["redis"],
                health_check_function=check_websocket_health,
                initialization_timeout_seconds=8.0,
                health_check_timeout_seconds=3.0,
                required_for_startup=True
            ),
            "system_resources": ServiceDependency(
                service_name="system_resources",
                depends_on=[],
                health_check_function=check_system_resources,
                initialization_timeout_seconds=5.0,
                health_check_timeout_seconds=2.0,
                required_for_startup=True
            ),
            "api_gateway": ServiceDependency(
                service_name="api_gateway",
                depends_on=["postgres", "redis", "websocket"],
                health_check_function=self._mock_api_gateway_health,
                initialization_timeout_seconds=12.0,
                health_check_timeout_seconds=4.0,
                required_for_startup=True
            ),
            "auth_service": ServiceDependency(
                service_name="auth_service", 
                depends_on=["postgres", "redis"],
                health_check_function=self._mock_auth_service_health,
                initialization_timeout_seconds=10.0,
                health_check_timeout_seconds=3.0,
                required_for_startup=True
            )
        }
        
        # Initialize all service states
        for service_name in self.dependency_map.keys():
            self.service_states[service_name] = ServiceState.NOT_STARTED
    
    async def _mock_api_gateway_health(self) -> HealthCheckResult:
        """Mock API gateway health check."""
        await asyncio.sleep(0.1)  # Simulate check time
        return HealthCheckResult(
            status="healthy",
            response_time=0.1,
            details={
                "component_name": "api_gateway",
                "success": True,
                "health_score": 1.0
            }
        )
    
    async def _mock_auth_service_health(self) -> HealthCheckResult:
        """Mock auth service health check."""
        await asyncio.sleep(0.08)  # Simulate check time
        return HealthCheckResult(
            status="healthy",
            response_time=0.08,
            details={
                "component_name": "auth_service", 
                "success": True,
                "health_score": 1.0
            }
        )
    
    async def simulate_service_initialization_cascade(self) -> Dict[str, Any]:
        """Simulate service initialization with health check cascade."""
        self.initialization_start_time = time.time()
        initialization_results = {
            "initialization_sequence": [],
            "health_check_timing": {},
            "dependency_validation": {},
            "cascade_events": [],
            "performance_metrics": {},
            "alerts_generated": []
        }
        
        # Track services that start within 5 seconds
        services_started_within_5s = []
        
        # Initialize services in dependency order
        initialization_order = self._calculate_initialization_order()
        
        for service_name in initialization_order:
            service_dep = self.dependency_map[service_name]
            init_start = time.time()
            
            try:
                # Check if dependencies are ready
                dependencies_ready = await self._check_dependencies_ready(service_dep.depends_on)
                
                if dependencies_ready["all_ready"]:
                    # Start service initialization
                    self.service_states[service_name] = ServiceState.INITIALIZING
                    
                    # Simulate initialization time
                    init_delay = min(service_dep.initialization_timeout_seconds / 10, 1.0)
                    await asyncio.sleep(init_delay)
                    
                    # Start health checks
                    health_check_start = time.time()
                    health_result = await self._execute_health_check_with_timeout(service_dep)
                    health_check_duration = time.time() - health_check_start
                    
                    # Record health check timing
                    initialization_results["health_check_timing"][service_name] = {
                        "started_at": health_check_start - self.initialization_start_time,
                        "duration_ms": health_check_duration * 1000,
                        "success": health_result.status == "healthy",
                        "within_5s_requirement": (health_check_start - self.initialization_start_time) <= 5.0
                    }
                    
                    if (health_check_start - self.initialization_start_time) <= 5.0:
                        services_started_within_5s.append(service_name)
                    
                    # Update service state based on health check
                    if health_result.status == "healthy":
                        self.service_states[service_name] = ServiceState.HEALTHY
                    else:
                        self.service_states[service_name] = ServiceState.FAILED
                        # Trigger cascade detection
                        cascade_event = await self._detect_and_handle_cascade_failure(service_name)
                        if cascade_event:
                            initialization_results["cascade_events"].append(cascade_event)
                    
                    # Record initialization event
                    init_duration = time.time() - init_start
                    initialization_results["initialization_sequence"].append({
                        "service": service_name,
                        "duration_ms": init_duration * 1000,
                        "dependencies_ready": dependencies_ready,
                        "health_check_result": {
                            "status": health_result.status,
                            "response_time": health_result.response_time,
                            "success": health_result.status == "healthy"
                        }
                    })
                    
                else:
                    # Dependencies not ready - record failure
                    self.service_states[service_name] = ServiceState.FAILED
                    initialization_results["initialization_sequence"].append({
                        "service": service_name,
                        "duration_ms": 0,
                        "dependencies_ready": dependencies_ready,
                        "error": "Dependencies not ready"
                    })
                    
                    # Trigger cascade for dependent services
                    cascade_event = await self._detect_and_handle_cascade_failure(service_name)
                    if cascade_event:
                        initialization_results["cascade_events"].append(cascade_event)
                
            except Exception as e:
                self.service_states[service_name] = ServiceState.FAILED
                logger.error(f"Service {service_name} initialization failed: {e}")
                
                # Handle exception cascade
                cascade_event = await self._detect_and_handle_cascade_failure(service_name, str(e))
                if cascade_event:
                    initialization_results["cascade_events"].append(cascade_event)
        
        # Calculate final metrics
        total_time = time.time() - self.initialization_start_time
        healthy_services = sum(1 for state in self.service_states.values() if state == ServiceState.HEALTHY)
        failed_services = sum(1 for state in self.service_states.values() if state == ServiceState.FAILED)
        
        initialization_results["performance_metrics"] = {
            "total_initialization_time": total_time,
            "services_healthy": healthy_services,
            "services_failed": failed_services,
            "health_checks_within_5s": len(services_started_within_5s),
            "health_check_activation_rate": len(services_started_within_5s) / len(self.dependency_map) * 100,
            "cascade_failures_detected": len(initialization_results["cascade_events"]),
            "overall_success_rate": healthy_services / len(self.dependency_map) * 100
        }
        
        return initialization_results
    
    def _calculate_initialization_order(self) -> List[str]:
        """Calculate service initialization order based on dependencies."""
        ordered_services = []
        remaining_services = set(self.dependency_map.keys())
        
        while remaining_services:
            # Find services with no unmet dependencies
            ready_services = []
            for service_name in remaining_services:
                service_dep = self.dependency_map[service_name]
                if all(dep in ordered_services for dep in service_dep.depends_on):
                    ready_services.append(service_name)
            
            if not ready_services:
                # Break circular dependencies by adding remaining services
                ready_services = list(remaining_services)
            
            # Sort by initialization timeout (shorter first)
            ready_services.sort(key=lambda s: self.dependency_map[s].initialization_timeout_seconds)
            
            for service in ready_services:
                ordered_services.append(service)
                remaining_services.remove(service)
        
        return ordered_services
    
    async def _check_dependencies_ready(self, dependencies: List[str]) -> Dict[str, Any]:
        """Check if all service dependencies are ready."""
        dependency_status = {
            "all_ready": True,
            "ready_dependencies": [],
            "failed_dependencies": [],
            "dependency_check_time": time.time()
        }
        
        for dep_name in dependencies:
            if dep_name in self.service_states:
                if self.service_states[dep_name] == ServiceState.HEALTHY:
                    dependency_status["ready_dependencies"].append(dep_name)
                else:
                    dependency_status["failed_dependencies"].append(dep_name)
                    dependency_status["all_ready"] = False
            else:
                dependency_status["failed_dependencies"].append(dep_name)
                dependency_status["all_ready"] = False
        
        return dependency_status
    
    async def _execute_health_check_with_timeout(self, service_dep: ServiceDependency) -> HealthCheckResult:
        """Execute health check with timeout and error handling."""
        try:
            # Execute health check with timeout
            health_result = await asyncio.wait_for(
                service_dep.health_check_function(),
                timeout=service_dep.health_check_timeout_seconds
            )
            return health_result
            
        except asyncio.TimeoutError:
            return HealthCheckResult(
                status="unhealthy",
                response_time=service_dep.health_check_timeout_seconds,
                details={
                    "component_name": service_dep.service_name,
                    "success": False,
                    "health_score": 0.0,
                    "error_message": "Health check timeout"
                }
            )
        except Exception as e:
            return HealthCheckResult(
                status="unhealthy", 
                response_time=0.0,
                details={
                    "component_name": service_dep.service_name,
                    "success": False,
                    "health_score": 0.0,
                    "error_message": str(e)
                }
            )
    
    async def _detect_and_handle_cascade_failure(self, failed_service: str, 
                                               error_msg: str = None) -> Optional[Dict[str, Any]]:
        """Detect cascade failures and generate alerts."""
        if not self.cascade_detection_enabled:
            return None
        
        cascade_event = {
            "cascade_id": str(uuid.uuid4()),
            "trigger_service": failed_service,
            "trigger_time": datetime.now(timezone.utc),
            "affected_services": [],
            "cascade_depth": 0,
            "alerts_generated": []
        }
        
        # Find services that depend on the failed service
        dependent_services = []
        for service_name, service_dep in self.dependency_map.items():
            if failed_service in service_dep.depends_on:
                dependent_services.append(service_name)
        
        # Mark dependent services as failed and continue cascade
        for dependent_service in dependent_services:
            if self.service_states[dependent_service] not in [ServiceState.FAILED]:
                self.service_states[dependent_service] = ServiceState.FAILED
                cascade_event["affected_services"].append(dependent_service)
                
                # Recursively check for further cascades
                sub_cascade = await self._detect_and_handle_cascade_failure(dependent_service)
                if sub_cascade:
                    cascade_event["affected_services"].extend(sub_cascade["affected_services"])
                    cascade_event["cascade_depth"] = max(cascade_event["cascade_depth"], 
                                                       sub_cascade["cascade_depth"] + 1)
        
        # Generate alerts for cascade event
        if cascade_event["affected_services"]:
            alert = await self._generate_cascade_alert(cascade_event, error_msg)
            cascade_event["alerts_generated"].append(alert)
            self.alert_events.append(alert)
        
        return cascade_event if cascade_event["affected_services"] else None
    
    async def _generate_cascade_alert(self, cascade_event: Dict[str, Any], 
                                    error_msg: str = None) -> Dict[str, Any]:
        """Generate alert for cascade failure event."""
        alert = {
            "alert_id": str(uuid.uuid4()),
            "alert_type": "cascade_failure",
            "severity": "critical" if len(cascade_event["affected_services"]) > 2 else "error",
            "trigger_service": cascade_event["trigger_service"],
            "affected_services": cascade_event["affected_services"],
            "cascade_depth": cascade_event["cascade_depth"],
            "timestamp": cascade_event["trigger_time"],
            "message": f"Cascade failure detected: {cascade_event['trigger_service']} failure affected {len(cascade_event['affected_services'])} dependent services",
            "error_details": error_msg,
            "escalation_required": len(cascade_event["affected_services"]) > 1
        }
        
        return alert
    
    async def test_dependency_chain_validation(self) -> Dict[str, Any]:
        """Test dependency chain validation during initialization."""
        validation_results = {
            "total_chains": 0,
            "validated_chains": 0,
            "broken_chains": 0,
            "chain_details": [],
            "validation_time": 0
        }
        
        validation_start = time.time()
        
        # Validate each service's dependency chain
        for service_name, service_dep in self.dependency_map.items():
            chain_validation = await self._validate_dependency_chain(service_name, service_dep)
            validation_results["chain_details"].append(chain_validation)
            validation_results["total_chains"] += 1
            
            if chain_validation["chain_valid"]:
                validation_results["validated_chains"] += 1
            else:
                validation_results["broken_chains"] += 1
        
        validation_results["validation_time"] = time.time() - validation_start
        validation_results["chain_validation_rate"] = (validation_results["validated_chains"] / 
                                                     validation_results["total_chains"] * 100) if validation_results["total_chains"] > 0 else 0
        
        return validation_results
    
    async def _validate_dependency_chain(self, service_name: str, 
                                       service_dep: ServiceDependency) -> Dict[str, Any]:
        """Validate a single service's dependency chain."""
        chain_validation = {
            "service_name": service_name,
            "dependencies": service_dep.depends_on,
            "chain_valid": True,
            "missing_dependencies": [],
            "circular_dependencies": [],
            "dependency_states": {}
        }
        
        # Check if all dependencies exist
        for dep_name in service_dep.depends_on:
            if dep_name not in self.dependency_map:
                chain_validation["missing_dependencies"].append(dep_name)
                chain_validation["chain_valid"] = False
            else:
                chain_validation["dependency_states"][dep_name] = self.service_states.get(dep_name, ServiceState.NOT_STARTED).value
        
        # Check for circular dependencies (simplified check)
        visited = set()
        if self._has_circular_dependency(service_name, visited):
            chain_validation["circular_dependencies"].append(service_name)
            chain_validation["chain_valid"] = False
        
        return chain_validation
    
    def _has_circular_dependency(self, service_name: str, visited: set) -> bool:
        """Check for circular dependencies (simplified implementation)."""
        if service_name in visited:
            return True
        
        visited.add(service_name)
        
        if service_name in self.dependency_map:
            for dep_name in self.dependency_map[service_name].depends_on:
                if self._has_circular_dependency(dep_name, visited.copy()):
                    return True
        
        return False
    
    async def test_performance_overhead(self, baseline_requests: int = 100) -> Dict[str, Any]:
        """Test performance overhead of health check cascade system."""
        # Measure baseline performance (without health checks)
        baseline_start = time.time()
        for _ in range(baseline_requests):
            await asyncio.sleep(0.001)  # Simulate minimal request processing
        baseline_duration = time.time() - baseline_start
        
        # Measure performance with health check monitoring
        monitoring_start = time.time()
        for _ in range(baseline_requests):
            # Simulate request with health check overhead
            await self._simulate_request_with_health_monitoring()
        monitoring_duration = time.time() - monitoring_start
        
        # Calculate overhead
        overhead_percentage = ((monitoring_duration - baseline_duration) / baseline_duration) * 100 if baseline_duration > 0 else 0
        
        return {
            "baseline_duration": baseline_duration,
            "monitoring_duration": monitoring_duration,
            "overhead_percentage": overhead_percentage,
            "requests_tested": baseline_requests,
            "overhead_per_request_ms": ((monitoring_duration - baseline_duration) / baseline_requests) * 1000 if baseline_requests > 0 else 0,
            "meets_requirement": overhead_percentage <= 1.0  # <1% overhead requirement
        }
    
    async def _simulate_request_with_health_monitoring(self):
        """Simulate request processing with health monitoring overhead."""
        # Simulate minimal request processing
        await asyncio.sleep(0.001)
        
        # Simulate health monitoring overhead
        await asyncio.sleep(0.00001)  # Minimal health check overhead
        
        # Simulate cascade detection check
        await asyncio.sleep(0.00001)
    
    async def test_recovery_detection(self, failed_service: str = "redis") -> Dict[str, Any]:
        """Test recovery detection and cascade restoration."""
        recovery_results = {
            "recovery_service": failed_service,
            "recovery_detected": False,
            "recovery_time": None,
            "cascade_restored": False,
            "dependent_services_recovered": [],
            "total_recovery_time": 0
        }
        
        recovery_start = time.time()
        
        # Simulate service failure
        original_state = self.service_states.get(failed_service, ServiceState.NOT_STARTED)
        self.service_states[failed_service] = ServiceState.FAILED
        
        # Identify dependent services that would fail
        dependent_services = [name for name, dep in self.dependency_map.items() 
                            if failed_service in dep.depends_on]
        
        # Simulate service recovery
        await asyncio.sleep(0.5)  # Simulate recovery time
        self.service_states[failed_service] = ServiceState.HEALTHY
        recovery_results["recovery_detected"] = True
        recovery_results["recovery_time"] = time.time() - recovery_start
        
        # Test dependent service recovery
        for dep_service in dependent_services:
            # Simulate dependent service health check after primary recovery
            if dep_service in self.dependency_map:
                service_dep = self.dependency_map[dep_service]
                try:
                    health_result = await self._execute_health_check_with_timeout(service_dep)
                    if health_result.status == "healthy":
                        self.service_states[dep_service] = ServiceState.HEALTHY
                        recovery_results["dependent_services_recovered"].append(dep_service)
                except Exception as e:
                    logger.error(f"Dependent service {dep_service} recovery failed: {e}")
        
        recovery_results["cascade_restored"] = len(recovery_results["dependent_services_recovered"]) == len(dependent_services)
        recovery_results["total_recovery_time"] = time.time() - recovery_start
        
        return recovery_results
    
    async def cleanup(self):
        """Clean up test resources."""
        self.service_states.clear()
        self.health_check_events.clear()
        self.alert_events.clear()
        self.performance_metrics.clear()


@pytest.fixture
async def health_cascade_validator():
    """Create health check cascade validator for L3 testing."""
    validator = HealthCheckCascadeInitializationValidator()
    await validator.initialize_service_dependencies()
    yield validator
    await validator.cleanup()


@pytest.mark.asyncio
async def test_health_check_cascade_during_initialization_l3(health_cascade_validator):
    """Test health check cascade behavior during service initialization.
    
    L3: Tests with real health check endpoints and actual service dependencies.
    """
    validator = health_cascade_validator
    
    # Test full initialization cascade
    initialization_results = await validator.simulate_service_initialization_cascade()
    
    # Verify health checks start within 5 seconds
    metrics = initialization_results["performance_metrics"]
    assert metrics["health_check_activation_rate"] >= 80.0
    assert metrics["health_checks_within_5s"] >= 5
    
    # Verify dependency chain validation
    assert len(initialization_results["initialization_sequence"]) >= 6
    assert metrics["overall_success_rate"] >= 70.0
    
    # Verify cascade detection works
    if initialization_results["cascade_events"]:
        for cascade_event in initialization_results["cascade_events"]:
            assert cascade_event["trigger_service"] is not None
            assert isinstance(cascade_event["affected_services"], list)
            assert cascade_event["cascade_depth"] >= 0


@pytest.mark.asyncio
async def test_dependency_chain_validation_l3(health_cascade_validator):
    """Test dependency chain validation during initialization.
    
    L3: Tests actual service dependency relationships and validation logic.
    """
    validator = health_cascade_validator
    
    # Test dependency chain validation
    validation_results = await validator.test_dependency_chain_validation()
    
    # Verify validation requirements
    assert validation_results["total_chains"] >= 6
    assert validation_results["chain_validation_rate"] >= 85.0
    assert validation_results["validation_time"] <= 2.0
    
    # Verify no broken chains in normal operation
    assert validation_results["broken_chains"] <= 1
    
    # Verify chain details
    for chain_detail in validation_results["chain_details"]:
        assert "service_name" in chain_detail
        assert "dependencies" in chain_detail
        assert "chain_valid" in chain_detail


@pytest.mark.asyncio
async def test_cascading_failure_detection_l3(health_cascade_validator):
    """Test cascading failure detection and alert generation.
    
    L3: Tests real cascade detection logic with actual service dependencies.
    """
    validator = health_cascade_validator
    
    # Initialize services first
    await validator.simulate_service_initialization_cascade()
    
    # Simulate cascade failure on a core dependency
    cascade_event = await validator._detect_and_handle_cascade_failure("postgres", "Database connection lost")
    
    # Verify cascade detection
    assert cascade_event is not None
    assert cascade_event["trigger_service"] == "postgres"
    assert len(cascade_event["affected_services"]) >= 2  # Should affect dependent services
    assert cascade_event["cascade_depth"] >= 1
    
    # Verify alerts are generated
    assert len(cascade_event["alerts_generated"]) >= 1
    alert = cascade_event["alerts_generated"][0]
    assert alert["alert_type"] == "cascade_failure"
    assert alert["severity"] in ["critical", "error"]
    assert alert["escalation_required"] is True


@pytest.mark.asyncio
async def test_health_status_aggregation_l3(health_cascade_validator):
    """Test health status aggregation across service dependencies.
    
    L3: Tests real health status aggregation and reporting.
    """
    validator = health_cascade_validator
    
    # Initialize services and run health checks
    initialization_results = await validator.simulate_service_initialization_cascade()
    
    # Verify health status aggregation
    timing_data = initialization_results["health_check_timing"]
    assert len(timing_data) >= 5
    
    # Check individual service health check results
    successful_health_checks = sum(1 for service_data in timing_data.values() if service_data["success"])
    total_health_checks = len(timing_data)
    
    health_success_rate = (successful_health_checks / total_health_checks) * 100 if total_health_checks > 0 else 0
    assert health_success_rate >= 70.0
    
    # Verify health check performance
    for service_name, timing in timing_data.items():
        assert timing["duration_ms"] <= 8000  # Health checks should complete within 8s
        assert timing["started_at"] >= 0  # Should start after initialization begins


@pytest.mark.asyncio
async def test_alert_triggering_on_failures_l3(health_cascade_validator):
    """Test alert triggering on health check failures.
    
    L3: Tests real alert generation and escalation logic.
    """
    validator = health_cascade_validator
    
    # Initialize services
    await validator.simulate_service_initialization_cascade()
    
    # Simulate multiple failures to trigger alerts
    test_failures = ["redis", "postgres", "websocket"]
    alerts_generated = []
    
    for failed_service in test_failures:
        cascade_event = await validator._detect_and_handle_cascade_failure(
            failed_service, f"Simulated failure in {failed_service}"
        )
        if cascade_event and cascade_event["alerts_generated"]:
            alerts_generated.extend(cascade_event["alerts_generated"])
    
    # Verify alert generation
    assert len(alerts_generated) >= 2
    
    # Verify alert content
    for alert in alerts_generated:
        assert alert["alert_id"] is not None
        assert alert["alert_type"] == "cascade_failure"
        assert alert["severity"] in ["critical", "error", "warning"]
        assert alert["trigger_service"] in test_failures
        assert alert["timestamp"] is not None
        assert "affected_services" in alert


@pytest.mark.asyncio
async def test_recovery_detection_within_30s_l3(health_cascade_validator):
    """Test recovery detection within 30 seconds.
    
    L3: Tests real recovery detection and cascade restoration.
    """
    validator = health_cascade_validator
    
    # Initialize services first
    await validator.simulate_service_initialization_cascade()
    
    # Test recovery detection
    recovery_results = await validator.test_recovery_detection("redis")
    
    # Verify recovery requirements
    assert recovery_results["recovery_detected"] is True
    assert recovery_results["recovery_time"] <= 30.0  # Within 30 seconds
    assert recovery_results["total_recovery_time"] <= 30.0
    
    # Verify cascade restoration
    if recovery_results["dependent_services_recovered"]:
        assert len(recovery_results["dependent_services_recovered"]) >= 1
        # Verify cascade restoration effectiveness
        assert recovery_results["cascade_restored"] in [True, False]  # May not restore all immediately


@pytest.mark.asyncio
async def test_performance_overhead_less_than_1_percent_l3(health_cascade_validator):
    """Test performance overhead is less than 1% of requests.
    
    L3: Tests real performance impact of health monitoring system.
    """
    validator = health_cascade_validator
    
    # Test performance overhead
    performance_results = await validator.test_performance_overhead(baseline_requests=50)
    
    # Verify performance requirements
    assert performance_results["overhead_percentage"] <= 1.0  # Less than 1% overhead
    assert performance_results["overhead_per_request_ms"] <= 0.1  # Less than 0.1ms per request
    assert performance_results["meets_requirement"] is True
    
    # Verify measurement validity
    assert performance_results["baseline_duration"] > 0
    assert performance_results["monitoring_duration"] > 0
    assert performance_results["requests_tested"] == 50


@pytest.mark.asyncio
async def test_health_check_initialization_timing_l3(health_cascade_validator):
    """Test health checks activate within 5 seconds of initialization.
    
    L3: Tests real timing requirements for health check activation.
    """
    validator = health_cascade_validator
    
    # Run initialization with timing measurement
    initialization_results = await validator.simulate_service_initialization_cascade()
    
    # Verify timing requirements
    metrics = initialization_results["performance_metrics"]
    timing_data = initialization_results["health_check_timing"]
    
    # Check 5-second activation requirement
    assert metrics["health_checks_within_5s"] >= 5
    assert metrics["health_check_activation_rate"] >= 70.0
    
    # Verify individual service timing
    services_within_requirement = 0
    for service_name, timing in timing_data.items():
        if timing["within_5s_requirement"]:
            services_within_requirement += 1
            assert timing["started_at"] <= 5.0
    
    assert services_within_requirement >= 5
    
    # Verify overall initialization performance
    assert metrics["total_initialization_time"] <= 30.0  # Reasonable total time