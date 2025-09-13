"""
Integration Tests: Graceful Degradation Under Load

Business Value Justification (BVJ):
- Segment: Enterprise (high-availability and load tolerance requirements)
- Business Goal: Service Continuity + User Experience + Resource Optimization
- Value Impact: Maintains partial functionality during high load rather than complete
  failure, provides predictable service degradation that preserves core business
  functions, enables system to serve maximum users possible within resource constraints,
  prevents cascade failures that could bring down entire platform
- Revenue Impact: Protects revenue during traffic spikes by serving partial functionality
  rather than complete outages, enables handling of 10x traffic surges without total
  system failure, reduces customer churn from service unavailability,
  supports Enterprise SLA commitments during unexpected load conditions

Test Focus: Load-based feature toggles, priority-based request handling, resource
throttling mechanisms, service capacity limits, and degraded mode functionality.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import random
from enum import Enum
from dataclasses import dataclass, field
import statistics
from collections import deque
import psutil
import threading

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.config import get_config


class ServiceTier(Enum):
    CRITICAL = "critical"      # Must remain available
    IMPORTANT = "important"    # Should remain available if possible  
    OPTIONAL = "optional"      # Can be disabled under load
    ANALYTICS = "analytics"    # Non-essential, first to disable


class LoadLevel(Enum):
    NORMAL = "normal"          # < 70% capacity
    ELEVATED = "elevated"      # 70-85% capacity
    HIGH = "high"             # 85-95% capacity
    CRITICAL = "critical"      # > 95% capacity


@dataclass
class DegradationConfig:
    cpu_threshold_elevated: float = 0.7
    cpu_threshold_high: float = 0.85
    cpu_threshold_critical: float = 0.95
    memory_threshold_elevated: float = 0.75
    memory_threshold_high: float = 0.9
    memory_threshold_critical: float = 0.95
    request_rate_limit_normal: int = 100
    request_rate_limit_elevated: int = 75
    request_rate_limit_high: int = 50
    request_rate_limit_critical: int = 25


@dataclass
class ServiceCapacity:
    service_name: str
    service_tier: ServiceTier
    max_concurrent_requests: int = 10
    current_load: float = 0.0
    enabled: bool = True
    degraded_mode: bool = False
    priority_only: bool = False


@dataclass
class LoadMetrics:
    timestamp: float
    cpu_usage: float
    memory_usage: float
    active_requests: int
    request_rate: float
    response_time_p95: float
    error_rate: float
    load_level: LoadLevel


class SimulatedLoadBalancer:
    """Simulated load balancer with graceful degradation capabilities."""
    
    def __init__(self, config: DegradationConfig):
        self.config = config
        self.services: Dict[str, ServiceCapacity] = {}
        self.load_metrics_history: deque = deque(maxlen=100)
        self.current_load_level = LoadLevel.NORMAL
        self.degradation_actions_taken: List[Dict[str, Any]] = []
        self.request_counts: Dict[str, int] = {}
        self.active_requests: Dict[str, int] = {}
        self.response_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        
        # Resource monitoring
        self.monitoring_active = False
        self.resource_lock = asyncio.Lock()
        
    def register_service(self, service_name: str, service_tier: ServiceTier, 
                        max_concurrent: int = 10):
        """Register a service for load balancing and degradation."""
        self.services[service_name] = ServiceCapacity(
            service_name=service_name,
            service_tier=service_tier,
            max_concurrent_requests=max_concurrent
        )
        self.request_counts[service_name] = 0
        self.active_requests[service_name] = 0
        self.response_times[service_name] = []
        self.error_counts[service_name] = 0
    
    async def start_load_monitoring(self):
        """Start continuous load monitoring and degradation management."""
        self.monitoring_active = True
        
        # Start background monitoring task
        monitoring_task = asyncio.create_task(self._monitor_system_load())
        return monitoring_task
    
    async def stop_load_monitoring(self):
        """Stop load monitoring."""
        self.monitoring_active = False
    
    async def handle_request(self, service_name: str, request_priority: str = "normal",
                           user_id: str = None) -> Dict[str, Any]:
        """Handle request with graceful degradation logic."""
        request_start_time = time.time()
        
        # Check if service is available
        if service_name not in self.services:
            return {
                "success": False,
                "error": f"Service {service_name} not registered",
                "degraded": False
            }
        
        service = self.services[service_name]
        
        # Apply degradation policies
        degradation_result = await self._apply_degradation_policies(
            service, request_priority, user_id
        )
        
        if not degradation_result["allowed"]:
            return {
                "success": False,
                "error": degradation_result["reason"],
                "degraded": True,
                "load_level": self.current_load_level.value
            }
        
        # Handle request with capacity limits
        try:
            async with self.resource_lock:
                if self.active_requests[service_name] >= service.max_concurrent_requests:
                    # Service at capacity
                    return {
                        "success": False,
                        "error": "Service at capacity",
                        "degraded": True,
                        "load_level": self.current_load_level.value
                    }
                
                self.active_requests[service_name] += 1
            
            # Process request
            result = await self._process_request(service, request_priority, degradation_result)
            
            # Record metrics
            processing_time = time.time() - request_start_time
            self.response_times[service_name].append(processing_time)
            self.request_counts[service_name] += 1
            
            if result["success"]:
                return {
                    **result,
                    "processing_time": processing_time,
                    "degraded": degradation_result["degraded"],
                    "load_level": self.current_load_level.value
                }
            else:
                self.error_counts[service_name] += 1
                return {
                    **result,
                    "processing_time": processing_time,
                    "degraded": True,
                    "load_level": self.current_load_level.value
                }
                
        finally:
            async with self.resource_lock:
                self.active_requests[service_name] = max(0, self.active_requests[service_name] - 1)
    
    async def _monitor_system_load(self):
        """Monitor system load and trigger degradation as needed."""
        while self.monitoring_active:
            try:
                # Collect load metrics
                current_metrics = await self._collect_load_metrics()
                self.load_metrics_history.append(current_metrics)
                
                # Determine load level
                new_load_level = self._determine_load_level(current_metrics)
                
                # Apply degradation if load level changed
                if new_load_level != self.current_load_level:
                    await self._apply_load_level_degradation(self.current_load_level, new_load_level)
                    self.current_load_level = new_load_level
                
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                # Monitoring should be resilient
                print(f"Load monitoring error: {e}")
                await asyncio.sleep(5.0)
    
    async def _collect_load_metrics(self) -> LoadMetrics:
        """Collect current system load metrics."""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            memory_usage = memory_info.percent / 100.0
        except:
            # Fallback if psutil unavailable
            cpu_usage = random.uniform(0.3, 0.9)
            memory_usage = random.uniform(0.4, 0.8)
        
        # Calculate request metrics
        total_active_requests = sum(self.active_requests.values())
        
        # Calculate request rate (requests per second over last minute)
        recent_request_count = sum(self.request_counts.values())
        request_rate = recent_request_count / 60.0  # Approximate
        
        # Calculate 95th percentile response time
        all_response_times = []
        for service_times in self.response_times.values():
            all_response_times.extend(service_times[-50:])  # Recent response times
        
        if all_response_times:
            response_time_p95 = sorted(all_response_times)[int(0.95 * len(all_response_times))]
        else:
            response_time_p95 = 0.0
        
        # Calculate error rate
        total_requests = sum(self.request_counts.values())
        total_errors = sum(self.error_counts.values())
        error_rate = total_errors / max(1, total_requests)
        
        # Determine load level
        load_level = LoadLevel.NORMAL
        if cpu_usage >= self.config.cpu_threshold_critical or memory_usage >= self.config.memory_threshold_critical:
            load_level = LoadLevel.CRITICAL
        elif cpu_usage >= self.config.cpu_threshold_high or memory_usage >= self.config.memory_threshold_high:
            load_level = LoadLevel.HIGH
        elif cpu_usage >= self.config.cpu_threshold_elevated or memory_usage >= self.config.memory_threshold_elevated:
            load_level = LoadLevel.ELEVATED
        
        return LoadMetrics(
            timestamp=time.time(),
            cpu_usage=cpu_usage / 100.0,  # Convert to 0-1 scale
            memory_usage=memory_usage,
            active_requests=total_active_requests,
            request_rate=request_rate,
            response_time_p95=response_time_p95,
            error_rate=error_rate,
            load_level=load_level
        )
    
    def _determine_load_level(self, metrics: LoadMetrics) -> LoadLevel:
        """Determine load level based on current metrics."""
        return metrics.load_level
    
    async def _apply_load_level_degradation(self, old_level: LoadLevel, new_level: LoadLevel):
        """Apply degradation policies based on load level transition."""
        degradation_action = {
            "timestamp": time.time(),
            "from_level": old_level.value,
            "to_level": new_level.value,
            "actions_taken": []
        }
        
        if new_level == LoadLevel.ELEVATED:
            # Start light degradation
            for service_name, service in self.services.items():
                if service.service_tier == ServiceTier.ANALYTICS:
                    service.degraded_mode = True
                    degradation_action["actions_taken"].append(f"Enable degraded mode for {service_name}")
        
        elif new_level == LoadLevel.HIGH:
            # Increase degradation
            for service_name, service in self.services.items():
                if service.service_tier in [ServiceTier.ANALYTICS, ServiceTier.OPTIONAL]:
                    service.degraded_mode = True
                    degradation_action["actions_taken"].append(f"Enable degraded mode for {service_name}")
                elif service.service_tier == ServiceTier.IMPORTANT:
                    service.priority_only = True
                    degradation_action["actions_taken"].append(f"Enable priority-only mode for {service_name}")
        
        elif new_level == LoadLevel.CRITICAL:
            # Maximum degradation
            for service_name, service in self.services.items():
                if service.service_tier == ServiceTier.ANALYTICS:
                    service.enabled = False
                    degradation_action["actions_taken"].append(f"Disable {service_name}")
                elif service.service_tier == ServiceTier.OPTIONAL:
                    service.degraded_mode = True
                    degradation_action["actions_taken"].append(f"Heavily degrade {service_name}")
                elif service.service_tier == ServiceTier.IMPORTANT:
                    service.priority_only = True
                    service.degraded_mode = True
                    degradation_action["actions_taken"].append(f"Priority-only degraded mode for {service_name}")
        
        elif new_level == LoadLevel.NORMAL and old_level != LoadLevel.NORMAL:
            # Restore services
            for service_name, service in self.services.items():
                service.enabled = True
                service.degraded_mode = False
                service.priority_only = False
                degradation_action["actions_taken"].append(f"Restore normal operation for {service_name}")
        
        if degradation_action["actions_taken"]:
            self.degradation_actions_taken.append(degradation_action)
    
    async def _apply_degradation_policies(self, service: ServiceCapacity, 
                                        request_priority: str, user_id: str) -> Dict[str, Any]:
        """Apply degradation policies to determine if request should be processed."""
        if not service.enabled:
            return {
                "allowed": False,
                "reason": f"Service {service.service_name} disabled under load",
                "degraded": True
            }
        
        if service.priority_only and request_priority != "high":
            return {
                "allowed": False,
                "reason": f"Service {service.service_name} in priority-only mode",
                "degraded": True
            }
        
        # Check request rate limits based on load level
        rate_limits = {
            LoadLevel.NORMAL: self.config.request_rate_limit_normal,
            LoadLevel.ELEVATED: self.config.request_rate_limit_elevated,
            LoadLevel.HIGH: self.config.request_rate_limit_high,
            LoadLevel.CRITICAL: self.config.request_rate_limit_critical
        }
        
        current_rate_limit = rate_limits[self.current_load_level]
        recent_requests = len([t for t in self.response_times[service.service_name][-60:] 
                             if time.time() - t < 60])  # Last minute
        
        if recent_requests >= current_rate_limit:
            return {
                "allowed": False,
                "reason": f"Rate limit exceeded for {service.service_name}",
                "degraded": True
            }
        
        return {
            "allowed": True,
            "degraded": service.degraded_mode,
            "reason": None
        }
    
    async def _process_request(self, service: ServiceCapacity, request_priority: str,
                             degradation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process request with appropriate degradation."""
        # Simulate processing time based on degradation level and load
        base_processing_time = 0.1
        
        if degradation_result["degraded"]:
            # Degraded mode - faster processing but reduced functionality
            processing_time = base_processing_time * 0.7
            await asyncio.sleep(processing_time)
            
            return {
                "success": True,
                "result": f"Degraded response from {service.service_name}",
                "features_available": ["core"],
                "degraded": True
            }
        else:
            # Normal processing
            load_multiplier = {
                LoadLevel.NORMAL: 1.0,
                LoadLevel.ELEVATED: 1.2,
                LoadLevel.HIGH: 1.5,
                LoadLevel.CRITICAL: 2.0
            }[self.current_load_level]
            
            processing_time = base_processing_time * load_multiplier
            await asyncio.sleep(processing_time)
            
            # Simulate occasional failures under high load
            failure_rates = {
                LoadLevel.NORMAL: 0.01,
                LoadLevel.ELEVATED: 0.03,
                LoadLevel.HIGH: 0.08,
                LoadLevel.CRITICAL: 0.15
            }
            
            if random.random() < failure_rates[self.current_load_level]:
                return {
                    "success": False,
                    "error": f"Processing failed under load for {service.service_name}"
                }
            
            return {
                "success": True,
                "result": f"Full response from {service.service_name}",
                "features_available": ["core", "enhanced", "analytics"],
                "degraded": False
            }
    
    def get_load_summary(self) -> Dict[str, Any]:
        """Get summary of current load and degradation state."""
        recent_metrics = list(self.load_metrics_history)[-5:]  # Last 5 metrics
        
        if recent_metrics:
            avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
            avg_response_time = sum(m.response_time_p95 for m in recent_metrics) / len(recent_metrics)
            avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        else:
            avg_cpu = avg_memory = avg_response_time = avg_error_rate = 0.0
        
        return {
            "current_load_level": self.current_load_level.value,
            "average_metrics": {
                "cpu_usage": avg_cpu,
                "memory_usage": avg_memory,
                "response_time_p95": avg_response_time,
                "error_rate": avg_error_rate
            },
            "service_states": {
                name: {
                    "enabled": service.enabled,
                    "degraded_mode": service.degraded_mode,
                    "priority_only": service.priority_only,
                    "active_requests": self.active_requests[name],
                    "total_requests": self.request_counts[name],
                    "error_count": self.error_counts[name]
                }
                for name, service in self.services.items()
            },
            "degradation_actions_taken": len(self.degradation_actions_taken)
        }


class TestGracefulDegradationUnderLoad(BaseIntegrationTest):
    """
    Test graceful degradation mechanisms under various load conditions.
    
    Business Value: Ensures system maintains core functionality under load
    rather than complete failure, maximizing revenue during high-traffic periods.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_degradation_test(self, real_services_fixture):
        """Setup graceful degradation test environment."""
        self.config = get_config()
        
        # Degradation test state
        self.load_balancers: Dict[str, SimulatedLoadBalancer] = {}
        self.load_simulation_tasks: List[asyncio.Task] = []
        
        # Test contexts
        self.test_contexts: List[UserExecutionContext] = []
        
        # Create load balancer configurations
        degradation_configs = {
            "standard": DegradationConfig(),
            "aggressive": DegradationConfig(
                cpu_threshold_elevated=0.6,
                cpu_threshold_high=0.75,
                cpu_threshold_critical=0.9
            ),
            "conservative": DegradationConfig(
                cpu_threshold_elevated=0.8,
                cpu_threshold_high=0.9,
                cpu_threshold_critical=0.98
            )
        }
        
        for config_name, config in degradation_configs.items():
            load_balancer = SimulatedLoadBalancer(config)
            self.load_balancers[config_name] = load_balancer
            
            # Register services with different tiers
            services_config = [
                ("user_auth", ServiceTier.CRITICAL, 20),
                ("core_api", ServiceTier.CRITICAL, 15),
                ("data_processing", ServiceTier.IMPORTANT, 10),
                ("recommendations", ServiceTier.OPTIONAL, 8),
                ("analytics", ServiceTier.ANALYTICS, 5)
            ]
            
            for service_name, tier, max_concurrent in services_config:
                load_balancer.register_service(service_name, tier, max_concurrent)
        
        yield
        
        # Stop all load monitoring
        for load_balancer in self.load_balancers.values():
            await load_balancer.stop_load_monitoring()
        
        # Cancel load simulation tasks
        for task in self.load_simulation_tasks:
            if not task.done():
                task.cancel()
        
        # Cleanup contexts
        for context in self.test_contexts:
            try:
                await context.cleanup()
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_service_tier_based_degradation_priority(self):
        """
        Test that services degrade in correct priority order based on tier classification.
        
        BVJ: Ensures critical business functions remain available while optional
        features are disabled, maximizing revenue protection under load.
        """
        load_balancer = self.load_balancers["standard"]
        
        # Start load monitoring
        monitoring_task = await load_balancer.start_load_monitoring()
        
        # Simulate increasing load levels
        load_scenarios = [
            {"name": "normal_load", "duration": 10.0, "request_rate": 20},
            {"name": "elevated_load", "duration": 15.0, "request_rate": 50},
            {"name": "high_load", "duration": 15.0, "request_rate": 80},
            {"name": "critical_load", "duration": 20.0, "request_rate": 120}
        ]
        
        tier_degradation_results = {
            "degradation_progression": [],
            "service_availability_by_tier": {},
            "load_level_transitions": []
        }
        
        for scenario in load_scenarios:
            scenario_name = scenario["name"]
            duration = scenario["duration"]
            request_rate = scenario["request_rate"]
            
            # Generate load for this scenario
            load_task = asyncio.create_task(
                self._generate_sustained_load(load_balancer, request_rate, duration)
            )
            self.load_simulation_tasks.append(load_task)
            
            await asyncio.sleep(duration)
            
            # Analyze service availability by tier
            load_summary = load_balancer.get_load_summary()
            current_load_level = load_summary["current_load_level"]
            
            scenario_analysis = {
                "scenario": scenario_name,
                "load_level": current_load_level,
                "service_states_by_tier": {}
            }
            
            # Group services by tier
            services_by_tier = {
                "critical": [],
                "important": [],
                "optional": [], 
                "analytics": []
            }
            
            for service_name, service_state in load_summary["service_states"].items():
                service = load_balancer.services[service_name]
                tier_name = service.service_tier.value
                
                services_by_tier[tier_name].append({
                    "service": service_name,
                    "enabled": service_state["enabled"],
                    "degraded": service_state["degraded_mode"],
                    "priority_only": service_state["priority_only"]
                })
            
            scenario_analysis["service_states_by_tier"] = services_by_tier
            tier_degradation_results["degradation_progression"].append(scenario_analysis)
            
            # Record load level transition
            if scenario_analysis not in tier_degradation_results["load_level_transitions"]:
                tier_degradation_results["load_level_transitions"].append({
                    "scenario": scenario_name,
                    "load_level": current_load_level
                })
        
        # Stop monitoring
        await load_balancer.stop_load_monitoring()
        monitoring_task.cancel()
        
        # Analyze tier-based degradation correctness
        for scenario_analysis in tier_degradation_results["degradation_progression"]:
            load_level = scenario_analysis["load_level"]
            services_by_tier = scenario_analysis["service_states_by_tier"]
            
            # Verify degradation priority order
            if load_level in ["elevated", "high", "critical"]:
                # Analytics services should degrade first
                analytics_services = services_by_tier["analytics"]
                for service_info in analytics_services:
                    assert service_info["degraded"] or not service_info["enabled"], \
                        f"Analytics service {service_info['service']} should be degraded under {load_level} load"
            
            if load_level in ["high", "critical"]:
                # Optional services should be degraded
                optional_services = services_by_tier["optional"]
                for service_info in optional_services:
                    assert service_info["degraded"] or not service_info["enabled"], \
                        f"Optional service {service_info['service']} should be degraded under {load_level} load"
            
            if load_level == "critical":
                # Important services should have some degradation
                important_services = services_by_tier["important"]
                for service_info in important_services:
                    assert service_info["degraded"] or service_info["priority_only"], \
                        f"Important service {service_info['service']} should have some degradation under critical load"
            
            # Critical services should always remain enabled
            critical_services = services_by_tier["critical"]
            for service_info in critical_services:
                assert service_info["enabled"], \
                    f"Critical service {service_info['service']} should remain enabled under all load levels"
        
        # Verify progression of degradation actions
        degradation_actions = load_balancer.degradation_actions_taken
        assert len(degradation_actions) > 0, "No degradation actions were taken during load test"
        
        # Actions should be taken in response to increasing load
        load_increases = [action for action in degradation_actions 
                         if action["to_level"] != "normal"]
        assert len(load_increases) > 0, "No degradation triggered despite increasing load"
        
        self.logger.info(f"Service tier degradation test completed: "
                        f"{len(degradation_actions)} degradation actions, "
                        f"load levels reached: {set(a['load_level'] for a in tier_degradation_results['degradation_progression'])}")
    
    @pytest.mark.asyncio
    async def test_request_priority_handling_under_load(self):
        """
        Test that high-priority requests are preserved during degradation.
        
        BVJ: Ensures critical user operations (payments, authentication) succeed
        even when system is under load, protecting revenue-critical transactions.
        """
        load_balancer = self.load_balancers["aggressive"]  # More aggressive degradation
        
        # Start monitoring
        monitoring_task = await load_balancer.start_load_monitoring()
        
        priority_test_results = {
            "requests_by_priority": {
                "high": {"attempted": 0, "successful": 0, "degraded": 0},
                "normal": {"attempted": 0, "successful": 0, "degraded": 0},
                "low": {"attempted": 0, "successful": 0, "degraded": 0}
            },
            "load_conditions_tested": [],
            "priority_preservation_rate": {}
        }
        
        # Generate high load to trigger degradation
        high_load_task = asyncio.create_task(
            self._generate_sustained_load(load_balancer, 100, 30.0)
        )
        self.load_simulation_tasks.append(high_load_task)
        
        # Allow load to build up
        await asyncio.sleep(10.0)
        
        # Test different priority requests under load
        test_scenarios = [
            {"priority": "high", "count": 20, "service": "core_api"},
            {"priority": "normal", "count": 30, "service": "core_api"},
            {"priority": "low", "count": 25, "service": "core_api"},
            {"priority": "high", "count": 15, "service": "data_processing"},
            {"priority": "normal", "count": 20, "service": "data_processing"}
        ]
        
        # Execute priority test requests
        for scenario in test_scenarios:
            priority = scenario["priority"]
            count = scenario["count"]
            service = scenario["service"]
            
            priority_test_results["requests_by_priority"][priority]["attempted"] += count
            
            # Send requests concurrently
            request_tasks = []
            for i in range(count):
                user_id = f"priority_test_user_{priority}_{i}"
                task = asyncio.create_task(
                    load_balancer.handle_request(service, priority, user_id)
                )
                request_tasks.append(task)
            
            # Wait for requests to complete
            results = await asyncio.gather(*request_tasks, return_exceptions=True)
            
            # Analyze results
            for result in results:
                if isinstance(result, dict):
                    if result.get("success"):
                        priority_test_results["requests_by_priority"][priority]["successful"] += 1
                    if result.get("degraded"):
                        priority_test_results["requests_by_priority"][priority]["degraded"] += 1
            
            await asyncio.sleep(2.0)  # Brief pause between scenarios
        
        # Record load conditions
        load_summary = load_balancer.get_load_summary()
        priority_test_results["load_conditions_tested"].append({
            "load_level": load_summary["current_load_level"],
            "degradation_actions": len(load_balancer.degradation_actions_taken)
        })
        
        # Stop load generation and monitoring
        high_load_task.cancel()
        await load_balancer.stop_load_monitoring()
        monitoring_task.cancel()
        
        # Calculate priority preservation rates
        for priority, stats in priority_test_results["requests_by_priority"].items():
            if stats["attempted"] > 0:
                success_rate = stats["successful"] / stats["attempted"]
                priority_test_results["priority_preservation_rate"][priority] = success_rate
        
        # Verify priority-based request handling
        high_priority_success = priority_test_results["priority_preservation_rate"].get("high", 0)
        normal_priority_success = priority_test_results["priority_preservation_rate"].get("normal", 0)
        low_priority_success = priority_test_results["priority_preservation_rate"].get("low", 0)
        
        # High priority requests should have highest success rate
        assert high_priority_success >= 0.8, \
            f"High priority request success rate too low: {high_priority_success:.2%}"
        
        # High priority should outperform normal priority under load
        if normal_priority_success > 0:
            assert high_priority_success >= normal_priority_success, \
                f"High priority success rate ({high_priority_success:.2%}) should be >= normal priority ({normal_priority_success:.2%})"
        
        # Normal priority should outperform low priority under load
        if low_priority_success > 0 and normal_priority_success > 0:
            assert normal_priority_success >= low_priority_success, \
                f"Normal priority success rate ({normal_priority_success:.2%}) should be >= low priority ({low_priority_success:.2%})"
        
        # Verify degradation occurred (some requests experienced degraded service)
        total_degraded = sum(stats["degraded"] for stats in priority_test_results["requests_by_priority"].values())
        assert total_degraded > 0, "No requests experienced degradation despite high load"
        
        self.logger.info(f"Request priority handling test completed: "
                        f"High priority success: {high_priority_success:.1%}, "
                        f"Normal priority success: {normal_priority_success:.1%}, "
                        f"Low priority success: {low_priority_success:.1%}")
    
    async def _generate_sustained_load(self, load_balancer: SimulatedLoadBalancer, 
                                     request_rate: int, duration: float):
        """Generate sustained load for testing degradation."""
        end_time = time.time() + duration
        services = list(load_balancer.services.keys())
        priorities = ["high", "normal", "low"]
        
        request_interval = 1.0 / request_rate  # Seconds between requests
        request_counter = 0
        
        while time.time() < end_time:
            try:
                # Send request
                service = random.choice(services)
                priority = random.choice(priorities)
                user_id = f"load_gen_user_{request_counter}"
                
                # Fire and forget to maintain request rate
                asyncio.create_task(
                    load_balancer.handle_request(service, priority, user_id)
                )
                
                request_counter += 1
                await asyncio.sleep(request_interval)
                
            except Exception as e:
                # Continue load generation even if individual requests fail
                await asyncio.sleep(request_interval)
    
    @pytest.mark.asyncio
    async def test_load_level_threshold_accuracy(self):
        """
        Test accuracy of load level detection and threshold-based degradation.
        
        BVJ: Ensures degradation triggers at appropriate load levels, preventing
        premature degradation that reduces capacity and delayed degradation that risks crashes.
        """
        load_balancer = self.load_balancers["standard"]
        
        # Test different load threshold scenarios
        threshold_test_scenarios = [
            {"name": "below_elevated", "target_cpu": 0.65, "target_memory": 0.7, "expected_level": "normal"},
            {"name": "at_elevated", "target_cpu": 0.75, "target_memory": 0.8, "expected_level": "elevated"},
            {"name": "at_high", "target_cpu": 0.88, "target_memory": 0.92, "expected_level": "high"},
            {"name": "at_critical", "target_cpu": 0.97, "target_memory": 0.97, "expected_level": "critical"}
        ]
        
        threshold_accuracy_results = {
            "scenario_results": [],
            "detection_accuracy": 0.0,
            "threshold_response_times": []
        }
        
        # Start monitoring
        monitoring_task = await load_balancer.start_load_monitoring()
        
        for scenario in threshold_test_scenarios:
            scenario_name = scenario["name"]
            target_cpu = scenario["target_cpu"]
            target_memory = scenario["target_memory"]
            expected_level = scenario["expected_level"]
            
            # Simulate system load to reach target thresholds
            load_simulation_start = time.time()
            
            # Generate artificial load metrics (since we can't easily control actual CPU/memory)
            original_collect = load_balancer._collect_load_metrics
            
            async def mock_collect_metrics():
                # Return metrics that match our target
                return LoadMetrics(
                    timestamp=time.time(),
                    cpu_usage=target_cpu,
                    memory_usage=target_memory,
                    active_requests=random.randint(10, 50),
                    request_rate=random.uniform(30, 100),
                    response_time_p95=random.uniform(0.1, 0.5),
                    error_rate=random.uniform(0.01, 0.1),
                    load_level=LoadLevel.NORMAL  # Will be recalculated
                )
            
            # Temporarily replace metrics collection
            load_balancer._collect_load_metrics = mock_collect_metrics
            
            # Wait for load level detection
            detection_start = time.time()
            detected_level = None
            
            for _ in range(12):  # Wait up to 60 seconds (5s intervals)
                await asyncio.sleep(5.0)
                current_level = load_balancer.current_load_level.value
                
                if current_level == expected_level:
                    detected_level = current_level
                    detection_time = time.time() - detection_start
                    threshold_accuracy_results["threshold_response_times"].append({
                        "scenario": scenario_name,
                        "detection_time": detection_time
                    })
                    break
            
            # Restore original metrics collection
            load_balancer._collect_load_metrics = original_collect
            
            scenario_result = {
                "scenario": scenario_name,
                "target_cpu": target_cpu,
                "target_memory": target_memory,
                "expected_level": expected_level,
                "detected_level": detected_level,
                "detection_accurate": detected_level == expected_level,
                "load_balancer_state": load_balancer.get_load_summary()
            }
            
            threshold_accuracy_results["scenario_results"].append(scenario_result)
            
            # Brief pause before next scenario
            await asyncio.sleep(5.0)
        
        # Stop monitoring
        await load_balancer.stop_load_monitoring()
        monitoring_task.cancel()
        
        # Calculate detection accuracy
        accurate_detections = sum(1 for result in threshold_accuracy_results["scenario_results"] 
                                if result["detection_accurate"])
        total_scenarios = len(threshold_accuracy_results["scenario_results"])
        threshold_accuracy_results["detection_accuracy"] = accurate_detections / total_scenarios
        
        # Verify threshold detection accuracy
        assert threshold_accuracy_results["detection_accuracy"] >= 0.75, \
            f"Load level detection accuracy too low: {threshold_accuracy_results['detection_accuracy']:.1%}"
        
        # Verify detection timing
        detection_times = [entry["detection_time"] for entry in threshold_accuracy_results["threshold_response_times"]]
        if detection_times:
            avg_detection_time = sum(detection_times) / len(detection_times)
            max_detection_time = max(detection_times)
            
            # Detection should be reasonably fast
            assert avg_detection_time <= 20.0, \
                f"Average load level detection too slow: {avg_detection_time:.1f}s"
            assert max_detection_time <= 30.0, \
                f"Maximum load level detection too slow: {max_detection_time:.1f}s"
        
        # Verify appropriate degradation actions were triggered
        degradation_actions = load_balancer.degradation_actions_taken
        
        # Should have taken degradation actions for elevated+ load levels
        elevated_plus_scenarios = [s for s in threshold_accuracy_results["scenario_results"] 
                                 if s["expected_level"] in ["elevated", "high", "critical"] 
                                 and s["detection_accurate"]]
        
        if elevated_plus_scenarios:
            assert len(degradation_actions) > 0, \
                "No degradation actions taken despite elevated load levels"
        
        self.logger.info(f"Load level threshold accuracy test completed: "
                        f"{threshold_accuracy_results['detection_accuracy']:.1%} accuracy, "
                        f"avg detection time: {sum(detection_times)/len(detection_times) if detection_times else 0:.1f}s")
    
    @pytest.mark.asyncio
    async def test_recovery_from_degraded_state(self):
        """
        Test system recovery when load decreases after degradation.
        
        BVJ: Ensures system automatically restores full functionality when load
        subsides, maximizing feature availability and user experience recovery.
        """
        load_balancer = self.load_balancers["standard"]
        
        recovery_test_results = {
            "degradation_phase": {},
            "recovery_phase": {},
            "recovery_success": False,
            "recovery_time": 0.0,
            "services_restored": []
        }
        
        # Start monitoring
        monitoring_task = await load_balancer.start_load_monitoring()
        
        # Phase 1: Generate high load to trigger degradation
        high_load_task = asyncio.create_task(
            self._generate_sustained_load(load_balancer, 120, 25.0)
        )
        self.load_simulation_tasks.append(high_load_task)
        
        # Wait for degradation to occur
        await asyncio.sleep(20.0)
        
        # Record degradation state
        degraded_state = load_balancer.get_load_summary()
        recovery_test_results["degradation_phase"] = {
            "load_level": degraded_state["current_load_level"],
            "degraded_services": [
                name for name, state in degraded_state["service_states"].items()
                if state["degraded_mode"] or not state["enabled"]
            ],
            "degradation_actions": len(load_balancer.degradation_actions_taken)
        }
        
        # Verify degradation occurred
        assert degraded_state["current_load_level"] in ["elevated", "high", "critical"], \
            f"Expected degradation, but load level is {degraded_state['current_load_level']}"
        
        degraded_services = recovery_test_results["degradation_phase"]["degraded_services"]
        assert len(degraded_services) > 0, "No services were degraded despite high load"
        
        # Phase 2: Stop load generation and wait for recovery
        high_load_task.cancel()
        
        recovery_start_time = time.time()
        recovery_detected = False
        
        # Wait for system to recover (up to 60 seconds)
        for check_num in range(12):
            await asyncio.sleep(5.0)
            
            current_state = load_balancer.get_load_summary()
            
            # Check if load level returned to normal
            if current_state["current_load_level"] == "normal":
                # Check if services were restored
                restored_services = []
                for service_name in degraded_services:
                    service_state = current_state["service_states"][service_name]
                    if service_state["enabled"] and not service_state["degraded_mode"]:
                        restored_services.append(service_name)
                
                if len(restored_services) == len(degraded_services):
                    # Full recovery detected
                    recovery_detected = True
                    recovery_test_results["recovery_time"] = time.time() - recovery_start_time
                    recovery_test_results["services_restored"] = restored_services
                    recovery_test_results["recovery_phase"] = {
                        "load_level": current_state["current_load_level"],
                        "final_state": current_state
                    }
                    break
        
        # Stop monitoring
        await load_balancer.stop_load_monitoring()
        monitoring_task.cancel()
        
        recovery_test_results["recovery_success"] = recovery_detected
        
        # Verify recovery effectiveness
        assert recovery_detected, \
            f"System did not recover within 60 seconds. Final load level: {current_state['current_load_level']}"
        
        # Verify recovery time is reasonable
        assert recovery_test_results["recovery_time"] <= 45.0, \
            f"Recovery took too long: {recovery_test_results['recovery_time']:.1f}s"
        
        # Verify all degraded services were restored
        assert len(recovery_test_results["services_restored"]) == len(degraded_services), \
            f"Not all services restored: {len(recovery_test_results['services_restored'])}/{len(degraded_services)}"
        
        # Verify degradation actions included recovery actions
        final_actions = load_balancer.degradation_actions_taken
        recovery_actions = [action for action in final_actions if action["to_level"] == "normal"]
        assert len(recovery_actions) > 0, "No recovery actions recorded"
        
        self.logger.info(f"Recovery from degraded state test completed: "
                        f"Recovery time: {recovery_test_results['recovery_time']:.1f}s, "
                        f"Services restored: {len(recovery_test_results['services_restored'])}")
    
    @pytest.mark.asyncio
    async def test_concurrent_user_degradation_fairness(self):
        """
        Test fairness of degradation across concurrent users.
        
        BVJ: Ensures degradation doesn't disproportionately affect specific users,
        maintaining fair service distribution and preventing user satisfaction issues.
        """
        load_balancer = self.load_balancers["standard"]
        
        # Start monitoring  
        monitoring_task = await load_balancer.start_load_monitoring()
        
        # Generate high load to trigger degradation
        high_load_task = asyncio.create_task(
            self._generate_sustained_load(load_balancer, 90, 40.0)
        )
        self.load_simulation_tasks.append(high_load_task)
        
        # Allow load to build up
        await asyncio.sleep(15.0)
        
        fairness_test_results = {
            "user_groups": {},
            "fairness_metrics": {},
            "degradation_distribution": {}
        }
        
        # Test different user groups under degradation
        user_groups = {
            "premium_users": {"count": 15, "priority": "high"},
            "standard_users": {"count": 30, "priority": "normal"},
            "free_users": {"count": 20, "priority": "low"}
        }
        
        # Execute requests for each user group
        for group_name, group_config in user_groups.items():
            user_count = group_config["count"]
            priority = group_config["priority"]
            
            group_results = {
                "requests_attempted": 0,
                "requests_successful": 0,
                "requests_degraded": 0,
                "average_response_time": 0.0,
                "user_results": []
            }
            
            # Create users and send requests
            user_tasks = []
            for user_num in range(user_count):
                user_id = f"{group_name}_user_{user_num}"
                
                # Each user makes multiple requests
                async def user_request_sequence(uid, prio):
                    user_request_results = []
                    
                    for req_num in range(3):  # 3 requests per user
                        try:
                            result = await load_balancer.handle_request("core_api", prio, uid)
                            user_request_results.append(result)
                        except Exception as e:
                            user_request_results.append({"success": False, "error": str(e)})
                        
                        await asyncio.sleep(0.5)  # Brief pause between requests
                    
                    return {"user_id": uid, "requests": user_request_results}
                
                task = asyncio.create_task(user_request_sequence(user_id, priority))
                user_tasks.append(task)
            
            # Wait for all users in this group to complete
            group_user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            # Analyze group results
            for user_result in group_user_results:
                if isinstance(user_result, dict):
                    group_results["user_results"].append(user_result)
                    
                    for request_result in user_result["requests"]:
                        group_results["requests_attempted"] += 1
                        
                        if request_result.get("success"):
                            group_results["requests_successful"] += 1
                        
                        if request_result.get("degraded"):
                            group_results["requests_degraded"] += 1
            
            fairness_test_results["user_groups"][group_name] = group_results
        
        # Stop load generation and monitoring
        high_load_task.cancel()
        await load_balancer.stop_load_monitoring()
        monitoring_task.cancel()
        
        # Calculate fairness metrics
        for group_name, group_results in fairness_test_results["user_groups"].items():
            if group_results["requests_attempted"] > 0:
                success_rate = group_results["requests_successful"] / group_results["requests_attempted"]
                degradation_rate = group_results["requests_degraded"] / group_results["requests_attempted"]
                
                fairness_test_results["fairness_metrics"][group_name] = {
                    "success_rate": success_rate,
                    "degradation_rate": degradation_rate
                }
        
        # Verify fairness across user groups
        success_rates = [metrics["success_rate"] for metrics in fairness_test_results["fairness_metrics"].values()]
        
        if len(success_rates) > 1:
            # Premium users should have better success rates than free users
            premium_success = fairness_test_results["fairness_metrics"]["premium_users"]["success_rate"]
            free_success = fairness_test_results["fairness_metrics"]["free_users"]["success_rate"]
            
            assert premium_success >= free_success, \
                f"Premium users success rate ({premium_success:.1%}) should be >= free users ({free_success:.1%})"
            
            # But the difference shouldn't be extreme (fairness)
            success_rate_range = max(success_rates) - min(success_rates)
            assert success_rate_range <= 0.4, \
                f"Success rate variation too high across user groups: {success_rate_range:.1%}"
        
        # Verify no user group was completely blocked
        for group_name, metrics in fairness_test_results["fairness_metrics"].items():
            assert metrics["success_rate"] > 0.1, \
                f"User group {group_name} completely blocked: {metrics['success_rate']:.1%} success rate"
        
        self.logger.info(f"Concurrent user degradation fairness test completed: "
                        f"User groups tested: {len(user_groups)}, "
                        f"Success rate range: {max(success_rates) - min(success_rates):.1%}")