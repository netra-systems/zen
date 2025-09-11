"""
Integration Tests: Cascade Failure Prevention

Business Value Justification (BVJ):
- Segment: Enterprise (mission-critical system resilience)
- Business Goal: System Stability + Business Continuity + Risk Mitigation
- Value Impact: Prevents single component failures from bringing down entire system,
  isolates failures to minimize business impact, maintains core functionality during
  partial system outages, enables rapid identification and containment of failure
  propagation, protects customer data and transactions during system stress
- Revenue Impact: Prevents catastrophic system outages worth $1M+ in lost revenue,
  reduces cascade failure recovery time from hours to minutes, enables Enterprise
  SLA guarantees for system availability, protects customer confidence and retention
  during infrastructure incidents, minimizes business disruption costs

Test Focus: Failure isolation mechanisms, dependency circuit breakers, bulkhead
patterns, service mesh resilience, timeout propagation, and system-wide failure recovery.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import random
from enum import Enum
from dataclasses import dataclass, field
from collections import deque, defaultdict
import threading

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.agents.supervisor.execution_engine import UserExecutionContext
from netra_backend.app.core.config import get_config


class FailureType(Enum):
    SERVICE_DOWN = "service_down"
    SLOW_RESPONSE = "slow_response"
    HIGH_ERROR_RATE = "high_error_rate"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    DATABASE_LOCK = "database_lock"


class IsolationMechanism(Enum):
    CIRCUIT_BREAKER = "circuit_breaker"
    BULKHEAD = "bulkhead"
    TIMEOUT = "timeout"
    RATE_LIMITER = "rate_limiter"
    FALLBACK = "fallback"


@dataclass
class ServiceNode:
    name: str
    tier: int  # Tier level (0=frontend, 1=api, 2=data, etc.)
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    failure_active: bool = False
    failure_type: Optional[FailureType] = None
    isolation_mechanisms: Set[IsolationMechanism] = field(default_factory=set)
    health_status: str = "healthy"
    
    
@dataclass
class CascadeEvent:
    timestamp: float
    source_service: str
    affected_service: str
    failure_type: FailureType
    isolation_triggered: bool
    isolation_mechanism: Optional[IsolationMechanism]
    propagation_prevented: bool


class SimulatedServiceMesh:
    """Simulated service mesh for testing cascade failure prevention."""
    
    def __init__(self):
        self.services: Dict[str, ServiceNode] = {}
        self.cascade_events: List[CascadeEvent] = []
        self.active_failures: Dict[str, Dict[str, Any]] = {}
        self.isolation_states: Dict[str, Dict[str, Any]] = {}
        
        # Cascade prevention mechanisms
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.bulkheads: Dict[str, Dict[str, Any]] = {}
        self.timeouts: Dict[str, float] = {}
        self.rate_limiters: Dict[str, Dict[str, Any]] = {}
        
        # Monitoring
        self.failure_propagation_log: List[Dict[str, Any]] = []
        self.isolation_effectiveness_log: List[Dict[str, Any]] = []
        
    def register_service(self, service_name: str, tier: int, 
                        dependencies: Set[str] = None,
                        isolation_mechanisms: Set[IsolationMechanism] = None):
        """Register a service in the mesh with its dependencies and isolation."""
        service = ServiceNode(
            name=service_name,
            tier=tier,
            dependencies=dependencies or set(),
            isolation_mechanisms=isolation_mechanisms or set()
        )
        
        self.services[service_name] = service
        
        # Update dependents for referenced services
        for dep_name in service.dependencies:
            if dep_name in self.services:
                self.services[dep_name].dependents.add(service_name)
        
        # Initialize isolation mechanisms
        self._initialize_service_isolation(service_name, isolation_mechanisms or set())
    
    def _initialize_service_isolation(self, service_name: str, 
                                    mechanisms: Set[IsolationMechanism]):
        """Initialize isolation mechanisms for a service."""
        if IsolationMechanism.CIRCUIT_BREAKER in mechanisms:
            self.circuit_breakers[service_name] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure_time": None,
                "failure_threshold": 3,
                "recovery_timeout": 30.0
            }
        
        if IsolationMechanism.BULKHEAD in mechanisms:
            self.bulkheads[service_name] = {
                "max_concurrent_requests": 10,
                "current_requests": 0,
                "request_pool": "dedicated"
            }
        
        if IsolationMechanism.TIMEOUT in mechanisms:
            self.timeouts[service_name] = 5.0  # 5 second timeout
        
        if IsolationMechanism.RATE_LIMITER in mechanisms:
            self.rate_limiters[service_name] = {
                "max_requests_per_minute": 100,
                "current_minute_requests": 0,
                "minute_start": time.time()
            }
        
        # Initialize isolation state
        self.isolation_states[service_name] = {
            "mechanisms": mechanisms,
            "isolation_active": False,
            "last_isolation_trigger": None
        }
    
    async def inject_failure(self, service_name: str, failure_type: FailureType,
                           duration: float = 60.0) -> bool:
        """Inject a failure into a specific service."""
        if service_name not in self.services:
            return False
        
        # Record failure injection
        self.active_failures[service_name] = {
            "failure_type": failure_type,
            "start_time": time.time(),
            "duration": duration,
            "propagation_attempts": []
        }
        
        service = self.services[service_name]
        service.failure_active = True
        service.failure_type = failure_type
        service.health_status = "failing"
        
        # Start failure propagation monitoring
        asyncio.create_task(self._monitor_failure_propagation(service_name))
        
        return True
    
    async def _monitor_failure_propagation(self, failed_service: str):
        """Monitor and potentially prevent failure propagation."""
        service = self.services[failed_service]
        failure_info = self.active_failures[failed_service]
        
        # Check each dependent service for potential cascade
        for dependent_service in service.dependents:
            cascade_risk = await self._assess_cascade_risk(
                failed_service, dependent_service, failure_info["failure_type"]
            )
            
            if cascade_risk["high_risk"]:
                # Attempt to prevent cascade
                prevention_success = await self._prevent_cascade(
                    failed_service, dependent_service, failure_info["failure_type"]
                )
                
                # Record cascade event
                cascade_event = CascadeEvent(
                    timestamp=time.time(),
                    source_service=failed_service,
                    affected_service=dependent_service,
                    failure_type=failure_info["failure_type"],
                    isolation_triggered=prevention_success["isolation_triggered"],
                    isolation_mechanism=prevention_success.get("mechanism"),
                    propagation_prevented=prevention_success["prevented"]
                )
                
                self.cascade_events.append(cascade_event)
                
                # Log propagation attempt
                failure_info["propagation_attempts"].append({
                    "target_service": dependent_service,
                    "prevention_attempted": True,
                    "prevention_success": prevention_success["prevented"],
                    "mechanism_used": prevention_success.get("mechanism"),
                    "timestamp": time.time()
                })
    
    async def _assess_cascade_risk(self, failed_service: str, dependent_service: str,
                                 failure_type: FailureType) -> Dict[str, Any]:
        """Assess the risk of cascade failure to a dependent service."""
        dependent = self.services[dependent_service]
        
        # Risk factors
        risk_factors = {
            "direct_dependency": failed_service in dependent.dependencies,
            "tier_adjacency": abs(self.services[failed_service].tier - dependent.tier) <= 1,
            "isolation_available": len(dependent.isolation_mechanisms) > 0,
            "failure_type_critical": failure_type in [FailureType.SERVICE_DOWN, FailureType.RESOURCE_EXHAUSTION]
        }
        
        # Calculate risk score
        risk_score = 0.0
        if risk_factors["direct_dependency"]:
            risk_score += 0.4
        if risk_factors["tier_adjacency"]:
            risk_score += 0.2
        if not risk_factors["isolation_available"]:
            risk_score += 0.3
        if risk_factors["failure_type_critical"]:
            risk_score += 0.3
        
        return {
            "high_risk": risk_score >= 0.6,
            "risk_score": risk_score,
            "risk_factors": risk_factors
        }
    
    async def _prevent_cascade(self, failed_service: str, dependent_service: str,
                             failure_type: FailureType) -> Dict[str, Any]:
        """Attempt to prevent cascade failure using available isolation mechanisms."""
        dependent = self.services[dependent_service]
        isolation_mechanisms = dependent.isolation_mechanisms
        
        prevention_result = {
            "isolation_triggered": False,
            "prevented": False,
            "mechanism": None
        }
        
        # Try isolation mechanisms in priority order
        for mechanism in [IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.BULKHEAD,
                         IsolationMechanism.TIMEOUT, IsolationMechanism.RATE_LIMITER]:
            
            if mechanism in isolation_mechanisms:
                isolation_success = await self._activate_isolation_mechanism(
                    dependent_service, mechanism, failed_service, failure_type
                )
                
                if isolation_success:
                    prevention_result["isolation_triggered"] = True
                    prevention_result["mechanism"] = mechanism
                    prevention_result["prevented"] = True
                    
                    # Update isolation state
                    self.isolation_states[dependent_service]["isolation_active"] = True
                    self.isolation_states[dependent_service]["last_isolation_trigger"] = time.time()
                    
                    break
        
        return prevention_result
    
    async def _activate_isolation_mechanism(self, service_name: str, 
                                          mechanism: IsolationMechanism,
                                          failed_dependency: str,
                                          failure_type: FailureType) -> bool:
        """Activate a specific isolation mechanism."""
        current_time = time.time()
        
        if mechanism == IsolationMechanism.CIRCUIT_BREAKER:
            # Open circuit breaker for failed dependency
            if service_name in self.circuit_breakers:
                cb = self.circuit_breakers[service_name]
                cb["state"] = "open"
                cb["last_failure_time"] = current_time
                
                self.isolation_effectiveness_log.append({
                    "service": service_name,
                    "mechanism": "circuit_breaker",
                    "action": "opened",
                    "target": failed_dependency,
                    "timestamp": current_time
                })
                
                return True
        
        elif mechanism == IsolationMechanism.BULKHEAD:
            # Isolate resource pool
            if service_name in self.bulkheads:
                bulkhead = self.bulkheads[service_name]
                bulkhead["request_pool"] = "isolated"
                
                self.isolation_effectiveness_log.append({
                    "service": service_name,
                    "mechanism": "bulkhead",
                    "action": "isolated_pool",
                    "timestamp": current_time
                })
                
                return True
        
        elif mechanism == IsolationMechanism.TIMEOUT:
            # Reduce timeout for failing dependency
            if service_name in self.timeouts:
                original_timeout = self.timeouts[service_name]
                self.timeouts[service_name] = min(2.0, original_timeout * 0.5)
                
                self.isolation_effectiveness_log.append({
                    "service": service_name,
                    "mechanism": "timeout_reduction",
                    "action": f"reduced_from_{original_timeout}s_to_{self.timeouts[service_name]}s",
                    "timestamp": current_time
                })
                
                return True
        
        elif mechanism == IsolationMechanism.RATE_LIMITER:
            # Activate aggressive rate limiting
            if service_name in self.rate_limiters:
                limiter = self.rate_limiters[service_name]
                limiter["max_requests_per_minute"] = int(limiter["max_requests_per_minute"] * 0.3)
                
                self.isolation_effectiveness_log.append({
                    "service": service_name,
                    "mechanism": "rate_limiter",
                    "action": "aggressive_limiting",
                    "timestamp": current_time
                })
                
                return True
        
        return False
    
    async def simulate_service_call(self, from_service: str, to_service: str,
                                  timeout: float = 5.0) -> Dict[str, Any]:
        """Simulate a service call with failure and isolation logic."""
        call_start = time.time()
        
        # Check if target service is failing
        if to_service in self.active_failures:
            failure_info = self.active_failures[to_service]
            failure_type = failure_info["failure_type"]
            
            # Check isolation mechanisms
            isolation_applied = await self._check_call_isolation(from_service, to_service)
            
            if isolation_applied["blocked"]:
                return {
                    "success": False,
                    "error": f"Call blocked by {isolation_applied['mechanism']}",
                    "isolation_protected": True,
                    "response_time": time.time() - call_start
                }
            
            # Simulate failure behavior
            if failure_type == FailureType.SERVICE_DOWN:
                # Service completely unavailable
                await asyncio.sleep(timeout)  # Wait for full timeout
                return {
                    "success": False,
                    "error": "Service unavailable",
                    "response_time": time.time() - call_start,
                    "timeout_occurred": True
                }
            
            elif failure_type == FailureType.SLOW_RESPONSE:
                # Very slow response
                slow_delay = random.uniform(8.0, 15.0)
                if slow_delay < timeout:
                    await asyncio.sleep(slow_delay)
                    return {
                        "success": True,
                        "result": "Slow response data",
                        "response_time": time.time() - call_start,
                        "performance_degraded": True
                    }
                else:
                    await asyncio.sleep(timeout)
                    return {
                        "success": False,
                        "error": "Timeout on slow service",
                        "response_time": time.time() - call_start,
                        "timeout_occurred": True
                    }
            
            elif failure_type == FailureType.HIGH_ERROR_RATE:
                # High probability of error
                processing_time = random.uniform(0.1, 0.5)
                await asyncio.sleep(processing_time)
                
                if random.random() < 0.7:  # 70% error rate
                    return {
                        "success": False,
                        "error": "Service error during processing",
                        "response_time": time.time() - call_start
                    }
                else:
                    return {
                        "success": True,
                        "result": "Lucky success despite high error rate",
                        "response_time": time.time() - call_start
                    }
            
            elif failure_type == FailureType.RESOURCE_EXHAUSTION:
                # Resource constraints
                if to_service in self.bulkheads:
                    bulkhead = self.bulkheads[to_service]
                    if bulkhead["current_requests"] >= bulkhead["max_concurrent_requests"]:
                        return {
                            "success": False,
                            "error": "Service at capacity",
                            "response_time": time.time() - call_start,
                            "resource_exhausted": True
                        }
        
        # Normal service call
        processing_time = random.uniform(0.05, 0.3)
        await asyncio.sleep(processing_time)
        
        return {
            "success": True,
            "result": f"Normal response from {to_service}",
            "response_time": time.time() - call_start
        }
    
    async def _check_call_isolation(self, from_service: str, to_service: str) -> Dict[str, Any]:
        """Check if call should be blocked by isolation mechanisms."""
        
        # Check circuit breaker
        if from_service in self.circuit_breakers:
            cb = self.circuit_breakers[from_service]
            if cb["state"] == "open":
                # Check if recovery timeout has passed
                if (cb["last_failure_time"] and 
                    time.time() - cb["last_failure_time"] < cb["recovery_timeout"]):
                    return {"blocked": True, "mechanism": "circuit_breaker"}
        
        # Check bulkhead capacity
        if to_service in self.bulkheads:
            bulkhead = self.bulkheads[to_service]
            if bulkhead["current_requests"] >= bulkhead["max_concurrent_requests"]:
                return {"blocked": True, "mechanism": "bulkhead"}
        
        # Check rate limiter
        if from_service in self.rate_limiters:
            limiter = self.rate_limiters[from_service]
            current_minute = int(time.time() / 60)
            limiter_minute = int(limiter["minute_start"] / 60)
            
            if current_minute > limiter_minute:
                # Reset for new minute
                limiter["current_minute_requests"] = 0
                limiter["minute_start"] = time.time()
            
            if limiter["current_minute_requests"] >= limiter["max_requests_per_minute"]:
                return {"blocked": True, "mechanism": "rate_limiter"}
            
            limiter["current_minute_requests"] += 1
        
        return {"blocked": False, "mechanism": None}
    
    def get_cascade_analysis(self) -> Dict[str, Any]:
        """Get analysis of cascade events and prevention effectiveness."""
        total_cascade_attempts = len(self.cascade_events)
        prevented_cascades = len([e for e in self.cascade_events if e.propagation_prevented])
        
        # Analyze by failure type
        cascade_by_failure_type = defaultdict(int)
        prevented_by_failure_type = defaultdict(int)
        
        for event in self.cascade_events:
            cascade_by_failure_type[event.failure_type.value] += 1
            if event.propagation_prevented:
                prevented_by_failure_type[event.failure_type.value] += 1
        
        # Analyze by isolation mechanism
        mechanism_effectiveness = defaultdict(lambda: {"used": 0, "successful": 0})
        
        for event in self.cascade_events:
            if event.isolation_mechanism:
                mechanism_effectiveness[event.isolation_mechanism.value]["used"] += 1
                if event.propagation_prevented:
                    mechanism_effectiveness[event.isolation_mechanism.value]["successful"] += 1
        
        return {
            "total_cascade_attempts": total_cascade_attempts,
            "cascades_prevented": prevented_cascades,
            "prevention_rate": prevented_cascades / max(1, total_cascade_attempts),
            "cascade_by_failure_type": dict(cascade_by_failure_type),
            "prevented_by_failure_type": dict(prevented_by_failure_type),
            "mechanism_effectiveness": dict(mechanism_effectiveness),
            "isolation_log": self.isolation_effectiveness_log
        }


class TestCascadeFailurePrevention(BaseIntegrationTest):
    """
    Test cascade failure prevention mechanisms across distributed service architecture.
    
    Business Value: Prevents single points of failure from bringing down entire system,
    protecting business continuity and minimizing revenue impact during outages.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_cascade_prevention_test(self, real_services_fixture):
        """Setup cascade failure prevention test environment."""
        self.config = get_config()
        
        # Cascade prevention test state
        self.service_meshes: Dict[str, SimulatedServiceMesh] = {}
        self.failure_injection_tasks: List[asyncio.Task] = []
        
        # Test contexts
        self.test_contexts: List[UserExecutionContext] = []
        
        # Create service mesh topologies for testing
        mesh_topologies = {
            "simple_tier": self._create_simple_tier_mesh,
            "complex_dependency": self._create_complex_dependency_mesh,
            "hub_spoke": self._create_hub_spoke_mesh
        }
        
        for topology_name, topology_creator in mesh_topologies.items():
            mesh = SimulatedServiceMesh()
            topology_creator(mesh)
            self.service_meshes[topology_name] = mesh
        
        yield
        
        # Cancel failure injection tasks
        for task in self.failure_injection_tasks:
            if not task.done():
                task.cancel()
        
        # Cleanup contexts
        for context in self.test_contexts:
            try:
                await context.cleanup()
            except Exception:
                pass
    
    def _create_simple_tier_mesh(self, mesh: SimulatedServiceMesh):
        """Create simple tiered service topology."""
        # Tier 0: Frontend
        mesh.register_service("web_frontend", tier=0, dependencies={"api_gateway"})
        
        # Tier 1: API Gateway
        mesh.register_service("api_gateway", tier=1, 
                            dependencies={"user_service", "order_service"},
                            isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.TIMEOUT})
        
        # Tier 2: Business Services
        mesh.register_service("user_service", tier=2, dependencies={"user_db"},
                            isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.BULKHEAD})
        mesh.register_service("order_service", tier=2, dependencies={"order_db", "payment_service"},
                            isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.RATE_LIMITER})
        mesh.register_service("payment_service", tier=2, dependencies={"payment_db"},
                            isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.TIMEOUT})
        
        # Tier 3: Data Layer
        mesh.register_service("user_db", tier=3)
        mesh.register_service("order_db", tier=3)
        mesh.register_service("payment_db", tier=3)
    
    def _create_complex_dependency_mesh(self, mesh: SimulatedServiceMesh):
        """Create complex dependency topology with cross-tier dependencies."""
        # Frontend services
        mesh.register_service("web_app", tier=0, dependencies={"api_service", "cdn_service"})
        mesh.register_service("mobile_api", tier=0, dependencies={"api_service", "push_service"})
        
        # API and orchestration
        mesh.register_service("api_service", tier=1, 
                            dependencies={"user_service", "product_service", "analytics_service"},
                            isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.BULKHEAD})
        mesh.register_service("orchestrator", tier=1, 
                            dependencies={"user_service", "order_service", "inventory_service"},
                            isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.TIMEOUT})
        
        # Business services with cross dependencies
        mesh.register_service("user_service", tier=2, dependencies={"user_db", "cache_service"},
                            isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.RATE_LIMITER})
        mesh.register_service("product_service", tier=2, dependencies={"product_db", "search_service"},
                            isolation_mechanisms={IsolationMechanism.BULKHEAD, IsolationMechanism.TIMEOUT})
        mesh.register_service("order_service", tier=2, dependencies={"order_db", "inventory_service", "payment_service"},
                            isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.BULKHEAD})
        
        # Support services
        mesh.register_service("analytics_service", tier=2, dependencies={"analytics_db", "cache_service"})
        mesh.register_service("inventory_service", tier=2, dependencies={"inventory_db", "cache_service"},
                            isolation_mechanisms={IsolationMechanism.RATE_LIMITER, IsolationMechanism.TIMEOUT})
        mesh.register_service("payment_service", tier=2, dependencies={"payment_db", "external_payment_api"},
                            isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.TIMEOUT})
        
        # Infrastructure services
        mesh.register_service("cache_service", tier=3, dependencies={"cache_cluster"},
                            isolation_mechanisms={IsolationMechanism.BULKHEAD})
        mesh.register_service("search_service", tier=3, dependencies={"search_index"})
        mesh.register_service("cdn_service", tier=3)
        mesh.register_service("push_service", tier=3, dependencies={"push_gateway"})
        
        # Data and external services
        mesh.register_service("user_db", tier=4)
        mesh.register_service("product_db", tier=4)
        mesh.register_service("order_db", tier=4)
        mesh.register_service("inventory_db", tier=4)
        mesh.register_service("payment_db", tier=4)
        mesh.register_service("analytics_db", tier=4)
        mesh.register_service("cache_cluster", tier=4)
        mesh.register_service("search_index", tier=4)
        mesh.register_service("push_gateway", tier=4)
        mesh.register_service("external_payment_api", tier=4)
    
    def _create_hub_spoke_mesh(self, mesh: SimulatedServiceMesh):
        """Create hub-spoke topology with central services."""
        # Central hub services
        mesh.register_service("central_hub", tier=1, 
                            dependencies={"config_service", "logging_service", "monitoring_service"},
                            isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.BULKHEAD, IsolationMechanism.RATE_LIMITER})
        mesh.register_service("message_bus", tier=1,
                            isolation_mechanisms={IsolationMechanism.BULKHEAD, IsolationMechanism.RATE_LIMITER})
        
        # Spoke services all dependent on hub
        spoke_services = [
            "service_a", "service_b", "service_c", "service_d", "service_e"
        ]
        
        for i, service_name in enumerate(spoke_services):
            mesh.register_service(service_name, tier=2,
                                dependencies={"central_hub", "message_bus", f"db_{service_name}"},
                                isolation_mechanisms={IsolationMechanism.CIRCUIT_BREAKER, IsolationMechanism.TIMEOUT})
            
            # Each spoke has its own database
            mesh.register_service(f"db_{service_name}", tier=3)
        
        # Infrastructure services
        mesh.register_service("config_service", tier=3)
        mesh.register_service("logging_service", tier=3)
        mesh.register_service("monitoring_service", tier=3)
    
    @pytest.mark.asyncio
    async def test_single_service_failure_isolation(self):
        """
        Test isolation of single service failure to prevent cascade.
        
        BVJ: Validates that individual service failures don't bring down
        entire system, protecting business continuity and user experience.
        """
        mesh = self.service_meshes["simple_tier"]
        
        isolation_test_results = {
            "failure_scenarios": [],
            "cascade_prevention_rate": 0.0,
            "services_protected": [],
            "isolation_mechanisms_tested": set()
        }
        
        # Test different single-point failure scenarios
        failure_scenarios = [
            {"service": "user_service", "failure_type": FailureType.SERVICE_DOWN},
            {"service": "payment_service", "failure_type": FailureType.SLOW_RESPONSE},
            {"service": "user_db", "failure_type": FailureType.RESOURCE_EXHAUSTION},
            {"service": "order_service", "failure_type": FailureType.HIGH_ERROR_RATE}
        ]
        
        for scenario in failure_scenarios:
            failed_service = scenario["service"]
            failure_type = scenario["failure_type"]
            
            # Inject failure
            injection_success = await mesh.inject_failure(failed_service, failure_type, duration=30.0)
            assert injection_success, f"Failed to inject failure into {failed_service}"
            
            # Allow time for cascade detection and prevention
            await asyncio.sleep(5.0)
            
            # Test dependent services to see if they're isolated
            dependent_services = mesh.services[failed_service].dependents
            protection_results = {}
            
            for dependent_service in dependent_services:
                # Simulate calls to dependent service
                call_results = []
                
                for call_num in range(5):
                    try:
                        result = await mesh.simulate_service_call("test_caller", dependent_service, timeout=3.0)
                        call_results.append(result)
                    except Exception as e:
                        call_results.append({"success": False, "error": str(e)})
                    
                    await asyncio.sleep(0.5)
                
                # Analyze protection effectiveness
                successful_calls = [r for r in call_results if r.get("success")]
                isolated_calls = [r for r in call_results if r.get("isolation_protected")]
                
                protection_results[dependent_service] = {
                    "total_calls": len(call_results),
                    "successful_calls": len(successful_calls),
                    "isolation_protected_calls": len(isolated_calls),
                    "protection_effective": len(isolated_calls) > 0 or len(successful_calls) > 0
                }
            
            scenario_result = {
                "failed_service": failed_service,
                "failure_type": failure_type.value,
                "dependent_services_tested": list(dependent_services),
                "protection_results": protection_results,
                "cascade_events": [e for e in mesh.cascade_events if e.source_service == failed_service]
            }
            
            isolation_test_results["failure_scenarios"].append(scenario_result)
            
            # Reset for next scenario
            if failed_service in mesh.active_failures:
                del mesh.active_failures[failed_service]
            mesh.services[failed_service].failure_active = False
            mesh.services[failed_service].health_status = "healthy"
            
            await asyncio.sleep(2.0)  # Brief pause between scenarios
        
        # Analyze overall isolation effectiveness
        cascade_analysis = mesh.get_cascade_analysis()
        isolation_test_results["cascade_prevention_rate"] = cascade_analysis["prevention_rate"]
        
        # Collect services that were protected
        for scenario_result in isolation_test_results["failure_scenarios"]:
            for service, protection in scenario_result["protection_results"].items():
                if protection["protection_effective"]:
                    isolation_test_results["services_protected"].append(service)
        
        # Collect isolation mechanisms that were tested
        for event in mesh.cascade_events:
            if event.isolation_mechanism:
                isolation_test_results["isolation_mechanisms_tested"].add(event.isolation_mechanism.value)
        
        # Verify isolation effectiveness
        assert cascade_analysis["total_cascade_attempts"] > 0, \
            "No cascade attempts detected - test may not be working correctly"
        
        assert cascade_analysis["prevention_rate"] >= 0.7, \
            f"Cascade prevention rate too low: {cascade_analysis['prevention_rate']:.1%}"
        
        # Verify multiple isolation mechanisms were used
        assert len(isolation_test_results["isolation_mechanisms_tested"]) >= 2, \
            f"Too few isolation mechanisms tested: {isolation_test_results['isolation_mechanisms_tested']}"
        
        # Verify services were actually protected
        assert len(isolation_test_results["services_protected"]) > 0, \
            "No services were effectively protected from cascade failures"
        
        self.logger.info(f"Single service failure isolation test completed: "
                        f"{cascade_analysis['prevention_rate']:.1%} prevention rate, "
                        f"{len(isolation_test_results['services_protected'])} services protected")
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_failure_isolation(self):
        """
        Test isolation during multiple concurrent service failures.
        
        BVJ: Ensures system can handle multiple simultaneous failures without
        complete system collapse, protecting business during infrastructure incidents.
        """
        mesh = self.service_meshes["complex_dependency"]
        
        concurrent_failure_results = {
            "failure_combinations_tested": [],
            "system_stability_maintained": False,
            "critical_paths_preserved": [],
            "isolation_overload_detected": False
        }
        
        # Define critical business paths that should remain functional
        critical_paths = [
            {"name": "user_authentication", "services": ["web_app", "api_service", "user_service"]},
            {"name": "product_browsing", "services": ["web_app", "api_service", "product_service"]},
            {"name": "order_placement", "services": ["mobile_api", "orchestrator", "order_service"]}
        ]
        
        # Test multiple concurrent failure scenarios
        concurrent_failure_scenarios = [
            {
                "name": "infrastructure_failure",
                "failures": [
                    ("cache_service", FailureType.SERVICE_DOWN),
                    ("analytics_service", FailureType.RESOURCE_EXHAUSTION)
                ]
            },
            {
                "name": "data_layer_stress", 
                "failures": [
                    ("user_db", FailureType.SLOW_RESPONSE),
                    ("product_db", FailureType.HIGH_ERROR_RATE),
                    ("analytics_db", FailureType.RESOURCE_EXHAUSTION)
                ]
            },
            {
                "name": "service_layer_cascade",
                "failures": [
                    ("payment_service", FailureType.SERVICE_DOWN),
                    ("inventory_service", FailureType.HIGH_ERROR_RATE),
                    ("search_service", FailureType.SLOW_RESPONSE)
                ]
            }
        ]
        
        for scenario in concurrent_failure_scenarios:
            scenario_name = scenario["name"]
            failures = scenario["failures"]
            
            # Inject all failures simultaneously
            failure_tasks = []
            for service_name, failure_type in failures:
                task = asyncio.create_task(
                    mesh.inject_failure(service_name, failure_type, duration=40.0)
                )
                failure_tasks.append(task)
                self.failure_injection_tasks.append(task)
            
            # Wait for all failures to be injected
            await asyncio.gather(*failure_tasks)
            
            # Allow time for cascade detection and prevention
            await asyncio.sleep(8.0)
            
            # Test critical business paths
            critical_path_results = {}
            
            for path in critical_paths:
                path_name = path["name"]
                path_services = path["services"]
                
                # Simulate end-to-end flow through critical path
                path_success = await self._test_critical_path_flow(mesh, path_services)
                critical_path_results[path_name] = path_success
                
                if path_success["flow_completed"]:
                    concurrent_failure_results["critical_paths_preserved"].append(path_name)
            
            # Analyze system stability
            cascade_analysis = mesh.get_cascade_analysis()
            
            scenario_result = {
                "scenario_name": scenario_name,
                "concurrent_failures": [(service, ftype.value) for service, ftype in failures],
                "critical_path_results": critical_path_results,
                "cascade_events_count": len(mesh.cascade_events),
                "cascade_prevention_rate": cascade_analysis["prevention_rate"],
                "isolation_mechanisms_active": len([log for log in cascade_analysis["isolation_log"] 
                                                  if log["action"] != "restored"])
            }
            
            concurrent_failure_results["failure_combinations_tested"].append(scenario_result)
            
            # Check for isolation mechanism overload
            if scenario_result["isolation_mechanisms_active"] > 10:
                concurrent_failure_results["isolation_overload_detected"] = True
            
            # Reset failures for next scenario
            for service_name, _ in failures:
                if service_name in mesh.active_failures:
                    del mesh.active_failures[service_name]
                mesh.services[service_name].failure_active = False
                mesh.services[service_name].health_status = "healthy"
            
            # Clear cascade events for next test
            mesh.cascade_events.clear()
            mesh.isolation_effectiveness_log.clear()
            
            await asyncio.sleep(5.0)  # Recovery pause between scenarios
        
        # Determine overall system stability
        total_critical_paths = len(critical_paths) * len(concurrent_failure_scenarios)
        preserved_critical_paths = len(concurrent_failure_results["critical_paths_preserved"])
        
        concurrent_failure_results["system_stability_maintained"] = (
            preserved_critical_paths / total_critical_paths >= 0.6
        )
        
        # Verify concurrent failure handling
        assert len(concurrent_failure_results["failure_combinations_tested"]) > 0, \
            "No concurrent failure scenarios were tested"
        
        # Verify system stability under concurrent failures
        assert concurrent_failure_results["system_stability_maintained"], \
            f"System stability not maintained: only {preserved_critical_paths}/{total_critical_paths} critical paths preserved"
        
        # Verify isolation mechanisms didn't become overloaded
        if concurrent_failure_results["isolation_overload_detected"]:
            self.logger.warning("Isolation mechanism overload detected during concurrent failures")
        
        # At least some critical paths should remain functional
        assert len(concurrent_failure_results["critical_paths_preserved"]) > 0, \
            "No critical business paths remained functional during concurrent failures"
        
        self.logger.info(f"Multiple concurrent failure isolation test completed: "
                        f"{preserved_critical_paths}/{total_critical_paths} critical paths preserved")
    
    async def _test_critical_path_flow(self, mesh: SimulatedServiceMesh, 
                                     path_services: List[str]) -> Dict[str, Any]:
        """Test end-to-end flow through a critical business path."""
        flow_results = []
        
        # Simulate calls through the path
        for i in range(len(path_services) - 1):
            from_service = path_services[i]
            to_service = path_services[i + 1]
            
            try:
                result = await mesh.simulate_service_call(from_service, to_service, timeout=5.0)
                flow_results.append({
                    "from": from_service,
                    "to": to_service,
                    "success": result.get("success", False),
                    "isolated": result.get("isolation_protected", False),
                    "response_time": result.get("response_time", 0)
                })
            except Exception as e:
                flow_results.append({
                    "from": from_service,
                    "to": to_service,
                    "success": False,
                    "error": str(e)
                })
        
        # Determine if overall flow completed successfully
        successful_hops = [r for r in flow_results if r.get("success")]
        flow_completed = len(successful_hops) == len(flow_results)
        
        # Calculate performance impact
        total_response_time = sum(r.get("response_time", 0) for r in flow_results)
        isolated_hops = len([r for r in flow_results if r.get("isolated")])
        
        return {
            "flow_completed": flow_completed,
            "successful_hops": len(successful_hops),
            "total_hops": len(flow_results),
            "total_response_time": total_response_time,
            "isolation_protected_hops": isolated_hops,
            "hop_details": flow_results
        }
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_cascade_prevention(self):
        """
        Test circuit breaker effectiveness in preventing cascading failures.
        
        BVJ: Validates circuit breakers prevent retry storms and resource exhaustion
        cascades, protecting system resources during dependency failures.
        """
        mesh = self.service_meshes["hub_spoke"]
        
        circuit_breaker_results = {
            "circuit_breaker_activations": [],
            "retry_storm_prevention": 0,
            "resource_protection_effectiveness": 0.0,
            "recovery_behavior": []
        }
        
        # Inject failure in central hub to test circuit breaker behavior
        central_failure_task = asyncio.create_task(
            mesh.inject_failure("central_hub", FailureType.SERVICE_DOWN, duration=45.0)
        )
        self.failure_injection_tasks.append(central_failure_task)
        
        # Wait for failure to be active
        await asyncio.sleep(3.0)
        
        # Simulate high load from spoke services trying to reach hub
        spoke_services = ["service_a", "service_b", "service_c", "service_d", "service_e"]
        
        # Phase 1: Generate initial load that should trigger circuit breakers
        initial_load_tasks = []
        for spoke_service in spoke_services:
            # Each spoke makes multiple rapid calls to the failing hub
            async def generate_spoke_load(spoke):
                call_results = []
                for call_num in range(20):  # 20 rapid calls
                    try:
                        result = await mesh.simulate_service_call(spoke, "central_hub", timeout=2.0)
                        call_results.append(result)
                    except Exception as e:
                        call_results.append({"success": False, "error": str(e)})
                    
                    await asyncio.sleep(0.1)  # Very rapid calls
                
                return {"spoke": spoke, "results": call_results}
            
            task = asyncio.create_task(generate_spoke_load(spoke_service))
            initial_load_tasks.append(task)
        
        initial_load_results = await asyncio.gather(*initial_load_tasks)
        
        # Analyze initial load results for circuit breaker activation
        for spoke_result in initial_load_results:
            spoke_service = spoke_result["spoke"]
            call_results = spoke_result["results"]
            
            # Look for circuit breaker activation
            circuit_breaker_calls = [r for r in call_results if "circuit_breaker" in r.get("error", "")]
            
            if circuit_breaker_calls:
                circuit_breaker_results["circuit_breaker_activations"].append({
                    "spoke_service": spoke_service,
                    "activation_after_calls": len(call_results) - len(circuit_breaker_calls),
                    "protected_calls": len(circuit_breaker_calls)
                })
        
        # Phase 2: Test retry storm prevention
        await asyncio.sleep(5.0)  # Allow circuit breakers to fully activate
        
        # Generate continued load that should be blocked by circuit breakers
        retry_storm_tasks = []
        for spoke_service in spoke_services:
            async def test_retry_storm_protection(spoke):
                blocked_calls = 0
                total_calls = 10
                
                for call_num in range(total_calls):
                    try:
                        result = await mesh.simulate_service_call(spoke, "central_hub", timeout=1.0)
                        if result.get("isolation_protected"):
                            blocked_calls += 1
                    except Exception:
                        pass
                    
                    await asyncio.sleep(0.2)
                
                return {"spoke": spoke, "blocked_calls": blocked_calls, "total_calls": total_calls}
            
            task = asyncio.create_task(test_retry_storm_protection(spoke_service))
            retry_storm_tasks.append(task)
        
        retry_storm_results = await asyncio.gather(*retry_storm_tasks)
        
        # Calculate retry storm prevention effectiveness
        total_retry_calls = sum(r["total_calls"] for r in retry_storm_results)
        total_blocked_calls = sum(r["blocked_calls"] for r in retry_storm_results)
        circuit_breaker_results["retry_storm_prevention"] = total_blocked_calls / max(1, total_retry_calls)
        
        # Phase 3: Test recovery behavior
        # Stop the failure and test circuit breaker recovery
        central_failure_task.cancel()
        
        # Clear failure state
        if "central_hub" in mesh.active_failures:
            del mesh.active_failures["central_hub"]
        mesh.services["central_hub"].failure_active = False
        mesh.services["central_hub"].health_status = "healthy"
        
        # Wait for circuit breaker recovery timeout
        await asyncio.sleep(35.0)  # Allow recovery timeout to pass
        
        # Test recovery behavior
        recovery_tasks = []
        for spoke_service in spoke_services:
            async def test_recovery_behavior(spoke):
                recovery_attempts = []
                
                for attempt_num in range(5):
                    try:
                        result = await mesh.simulate_service_call(spoke, "central_hub", timeout=3.0)
                        recovery_attempts.append({
                            "attempt": attempt_num,
                            "success": result.get("success", False),
                            "response_time": result.get("response_time", 0)
                        })
                    except Exception as e:
                        recovery_attempts.append({
                            "attempt": attempt_num,
                            "success": False,
                            "error": str(e)
                        })
                    
                    await asyncio.sleep(1.0)
                
                return {"spoke": spoke, "recovery_attempts": recovery_attempts}
            
            task = asyncio.create_task(test_recovery_behavior(spoke_service))
            recovery_tasks.append(task)
        
        recovery_results = await asyncio.gather(*recovery_tasks)
        circuit_breaker_results["recovery_behavior"] = recovery_results
        
        # Calculate resource protection effectiveness
        cascade_analysis = mesh.get_cascade_analysis()
        circuit_breaker_results["resource_protection_effectiveness"] = cascade_analysis["prevention_rate"]
        
        # Verify circuit breaker effectiveness
        assert len(circuit_breaker_results["circuit_breaker_activations"]) > 0, \
            "No circuit breaker activations detected despite service failure"
        
        # Verify retry storm prevention
        assert circuit_breaker_results["retry_storm_prevention"] >= 0.5, \
            f"Retry storm prevention too low: {circuit_breaker_results['retry_storm_prevention']:.1%}"
        
        # Verify resource protection
        assert circuit_breaker_results["resource_protection_effectiveness"] >= 0.7, \
            f"Resource protection effectiveness too low: {circuit_breaker_results['resource_protection_effectiveness']:.1%}"
        
        # Verify recovery behavior
        recovery_successful_spokes = 0
        for recovery_result in recovery_results:
            recovery_attempts = recovery_result["recovery_attempts"]
            successful_attempts = [a for a in recovery_attempts if a.get("success")]
            
            if len(successful_attempts) > 0:
                recovery_successful_spokes += 1
        
        recovery_rate = recovery_successful_spokes / len(spoke_services)
        assert recovery_rate >= 0.6, \
            f"Circuit breaker recovery rate too low: {recovery_rate:.1%}"
        
        self.logger.info(f"Circuit breaker cascade prevention test completed: "
                        f"{circuit_breaker_results['retry_storm_prevention']:.1%} retry storm prevention, "
                        f"{recovery_rate:.1%} recovery rate")
    
    @pytest.mark.asyncio
    async def test_bulkhead_isolation_effectiveness(self):
        """
        Test bulkhead pattern effectiveness in isolating resource pools.
        
        BVJ: Validates resource pool isolation prevents one failing component
        from consuming all system resources, maintaining service for other components.
        """
        mesh = self.service_meshes["complex_dependency"]
        
        bulkhead_test_results = {
            "resource_pools_tested": [],
            "isolation_effectiveness": {},
            "resource_starvation_prevented": False,
            "concurrent_pool_performance": {}
        }
        
        # Services with bulkhead isolation
        bulkhead_services = [service for service, node in mesh.services.items() 
                           if IsolationMechanism.BULKHEAD in node.isolation_mechanisms]
        
        assert len(bulkhead_services) > 0, "No services with bulkhead isolation found for testing"
        
        # Test resource pool isolation
        for service_name in bulkhead_services[:2]:  # Test first 2 bulkhead services
            # Phase 1: Saturate one resource pool
            resource_saturation_task = asyncio.create_task(
                self._saturate_service_resource_pool(mesh, service_name)
            )
            self.failure_injection_tasks.append(resource_saturation_task)
            
            # Wait for saturation
            await asyncio.sleep(5.0)
            
            # Phase 2: Test other resource pools remain unaffected
            other_services = [s for s in bulkhead_services if s != service_name][:3]
            
            concurrent_performance_results = {}
            
            for other_service in other_services:
                # Test performance of isolated resource pool
                performance_result = await self._test_resource_pool_performance(
                    mesh, other_service, concurrent_requests=5
                )
                concurrent_performance_results[other_service] = performance_result
            
            # Analyze isolation effectiveness
            isolation_effectiveness = 0.0
            for other_service, performance in concurrent_performance_results.items():
                if performance["success_rate"] >= 0.8:  # 80% success rate indicates good isolation
                    isolation_effectiveness += 1.0
            
            if len(concurrent_performance_results) > 0:
                isolation_effectiveness /= len(concurrent_performance_results)
            
            bulkhead_test_results["resource_pools_tested"].append({
                "saturated_service": service_name,
                "tested_other_pools": list(other_services),
                "isolation_effectiveness": isolation_effectiveness
            })
            
            bulkhead_test_results["concurrent_pool_performance"][service_name] = concurrent_performance_results
            
            # Stop saturation for next test
            resource_saturation_task.cancel()
            await asyncio.sleep(2.0)
        
        # Calculate overall isolation effectiveness
        if bulkhead_test_results["resource_pools_tested"]:
            avg_isolation_effectiveness = sum(
                result["isolation_effectiveness"] 
                for result in bulkhead_test_results["resource_pools_tested"]
            ) / len(bulkhead_test_results["resource_pools_tested"])
            
            bulkhead_test_results["isolation_effectiveness"]["average"] = avg_isolation_effectiveness
            bulkhead_test_results["resource_starvation_prevented"] = avg_isolation_effectiveness >= 0.7
        
        # Verify bulkhead isolation effectiveness
        assert len(bulkhead_test_results["resource_pools_tested"]) > 0, \
            "No resource pool isolation tests were completed"
        
        assert bulkhead_test_results["resource_starvation_prevented"], \
            f"Resource starvation not adequately prevented: {avg_isolation_effectiveness:.1%} effectiveness"
        
        # Verify individual pool performance under concurrent saturation
        for service_name, concurrent_performance in bulkhead_test_results["concurrent_pool_performance"].items():
            for other_service, performance in concurrent_performance.items():
                assert performance["success_rate"] >= 0.6, \
                    f"Resource pool {other_service} performance too degraded during {service_name} saturation: {performance['success_rate']:.1%}"
        
        self.logger.info(f"Bulkhead isolation effectiveness test completed: "
                        f"{avg_isolation_effectiveness:.1%} average isolation effectiveness, "
                        f"{len(bulkhead_test_results['resource_pools_tested'])} pools tested")
    
    async def _saturate_service_resource_pool(self, mesh: SimulatedServiceMesh, service_name: str):
        """Saturate a service's resource pool to test bulkhead isolation."""
        # Get bulkhead configuration
        if service_name not in mesh.bulkheads:
            return
        
        bulkhead = mesh.bulkheads[service_name]
        max_concurrent = bulkhead["max_concurrent_requests"]
        
        # Generate requests to saturate the pool
        saturation_tasks = []
        
        for request_num in range(max_concurrent + 5):  # Exceed capacity
            async def long_running_request(req_id):
                try:
                    # Simulate long-running request that holds resources
                    result = await mesh.simulate_service_call("saturation_caller", service_name, timeout=30.0)
                    await asyncio.sleep(20.0)  # Hold resource for extended time
                    return result
                except Exception:
                    pass
            
            task = asyncio.create_task(long_running_request(request_num))
            saturation_tasks.append(task)
            await asyncio.sleep(0.1)  # Brief delay between requests
        
        # Let saturation persist
        try:
            await asyncio.gather(*saturation_tasks, return_exceptions=True)
        except asyncio.CancelledError:
            # Cancel all saturation tasks
            for task in saturation_tasks:
                if not task.done():
                    task.cancel()
    
    async def _test_resource_pool_performance(self, mesh: SimulatedServiceMesh, 
                                            service_name: str, concurrent_requests: int = 5) -> Dict[str, Any]:
        """Test performance of a resource pool under concurrent load."""
        performance_tasks = []
        
        for request_num in range(concurrent_requests):
            async def performance_test_request(req_id):
                start_time = time.time()
                try:
                    result = await mesh.simulate_service_call("performance_tester", service_name, timeout=5.0)
                    return {
                        "success": result.get("success", False),
                        "response_time": time.time() - start_time,
                        "isolated": result.get("isolation_protected", False)
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "response_time": time.time() - start_time,
                        "error": str(e)
                    }
            
            task = asyncio.create_task(performance_test_request(request_num))
            performance_tasks.append(task)
        
        # Execute performance tests
        performance_results = await asyncio.gather(*performance_tasks, return_exceptions=True)
        
        # Analyze performance
        successful_requests = [r for r in performance_results if isinstance(r, dict) and r.get("success")]
        total_requests = len(performance_results)
        
        if total_requests > 0:
            success_rate = len(successful_requests) / total_requests
            
            if successful_requests:
                avg_response_time = sum(r["response_time"] for r in successful_requests) / len(successful_requests)
            else:
                avg_response_time = 0.0
        else:
            success_rate = 0.0
            avg_response_time = 0.0
        
        return {
            "service_name": service_name,
            "total_requests": total_requests,
            "successful_requests": len(successful_requests),
            "success_rate": success_rate,
            "average_response_time": avg_response_time
        }