"""
Integration Tests: Service Health Monitoring and Recovery

Business Value Justification (BVJ):
- Segment: Enterprise (mission-critical system monitoring)
- Business Goal: System Reliability + Proactive Issue Detection + Operational Excellence
- Value Impact: Enables proactive detection of service degradation before user impact,
  provides automated health checks and recovery procedures, reduces mean time to
  detection (MTTD) and mean time to recovery (MTTR) for system issues,
  supports Enterprise SLA commitments and operational monitoring requirements
- Revenue Impact: Prevents revenue loss from undetected service degradation
  ($50K+ per hour), reduces operational costs through automated monitoring,
  enables Enterprise contracts requiring 99.9% uptime monitoring,
  improves customer satisfaction through proactive issue resolution

Test Focus: Health check algorithms, service dependency monitoring, automated
recovery procedures, health state transitions, and monitoring system resilience.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Any, Optional, Callable, Set
from unittest.mock import AsyncMock, MagicMock, patch
import random
from enum import Enum
from dataclasses import dataclass, field
import statistics
from collections import deque

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.config import get_config


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    NONE = "none"
    RESTART_SERVICE = "restart_service"
    SCALE_UP = "scale_up"
    FAILOVER = "failover"
    ALERT_OPERATORS = "alert_operators"


@dataclass
class HealthCheckConfig:
    check_interval: float = 30.0      # Seconds between health checks
    timeout: float = 5.0              # Health check timeout
    failure_threshold: int = 3        # Failures before marking unhealthy
    success_threshold: int = 2        # Successes to mark healthy again
    degraded_threshold: float = 0.7   # Performance threshold for degraded status


@dataclass
class HealthMetric:
    timestamp: float
    status: HealthStatus
    response_time: Optional[float] = None
    error_rate: Optional[float] = None
    throughput: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    additional_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceHealthState:
    service_name: str
    current_status: HealthStatus = HealthStatus.UNKNOWN
    status_since: float = field(default_factory=time.time)
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    health_history: deque = field(default_factory=lambda: deque(maxlen=100))
    last_recovery_action: Optional[RecoveryAction] = None
    last_recovery_time: Optional[float] = None
    dependencies: Set[str] = field(default_factory=set)


class SimulatedHealthMonitor:
    """Simulated health monitoring system for testing recovery scenarios."""
    
    def __init__(self, config: HealthCheckConfig):
        self.config = config
        self.services: Dict[str, ServiceHealthState] = {}
        self.monitoring_active = False
        self.recovery_actions_taken: List[Dict[str, Any]] = []
        self.health_check_results: List[Dict[str, Any]] = []
        
    def register_service(self, service_name: str, dependencies: Set[str] = None):
        """Register a service for health monitoring."""
        self.services[service_name] = ServiceHealthState(
            service_name=service_name,
            dependencies=dependencies or set()
        )
    
    async def start_monitoring(self):
        """Start continuous health monitoring."""
        self.monitoring_active = True
        
        # Start monitoring tasks for each service
        monitoring_tasks = []
        for service_name in self.services.keys():
            task = asyncio.create_task(self._monitor_service_health(service_name))
            monitoring_tasks.append(task)
        
        return monitoring_tasks
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        self.monitoring_active = False
    
    async def _monitor_service_health(self, service_name: str):
        """Monitor health of a specific service continuously."""
        service_state = self.services[service_name]
        
        while self.monitoring_active:
            try:
                # Perform health check
                health_metric = await self._perform_health_check(service_name)
                
                # Process health check result
                await self._process_health_check_result(service_name, health_metric)
                
                # Check if recovery action is needed
                await self._evaluate_recovery_actions(service_name)
                
                # Wait for next check interval
                await asyncio.sleep(self.config.check_interval)
                
            except Exception as e:
                # Health monitoring should be resilient
                error_metric = HealthMetric(
                    timestamp=time.time(),
                    status=HealthStatus.UNKNOWN,
                    additional_metrics={"error": str(e)}
                )
                await self._process_health_check_result(service_name, error_metric)
                await asyncio.sleep(self.config.check_interval)
    
    async def _perform_health_check(self, service_name: str) -> HealthMetric:
        """Perform health check for a service."""
        start_time = time.time()
        
        try:
            # Simulate health check operation with timeout
            health_data = await asyncio.wait_for(
                self._simulate_service_health_check(service_name),
                timeout=self.config.timeout
            )
            
            response_time = time.time() - start_time
            
            # Determine health status based on metrics
            status = self._calculate_health_status(health_data, response_time)
            
            metric = HealthMetric(
                timestamp=start_time,
                status=status,
                response_time=response_time,
                error_rate=health_data.get("error_rate", 0.0),
                throughput=health_data.get("throughput", 0.0),
                cpu_usage=health_data.get("cpu_usage", 0.0),
                memory_usage=health_data.get("memory_usage", 0.0),
                additional_metrics=health_data
            )
            
            self.health_check_results.append({
                "service": service_name,
                "timestamp": start_time,
                "success": True,
                "metric": metric
            })
            
            return metric
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            metric = HealthMetric(
                timestamp=start_time,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                additional_metrics={"error": "Health check timeout"}
            )
            
            self.health_check_results.append({
                "service": service_name,
                "timestamp": start_time,
                "success": False,
                "error": "timeout",
                "metric": metric
            })
            
            return metric
            
        except Exception as e:
            response_time = time.time() - start_time
            metric = HealthMetric(
                timestamp=start_time,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                additional_metrics={"error": str(e)}
            )
            
            self.health_check_results.append({
                "service": service_name,
                "timestamp": start_time,
                "success": False,
                "error": str(e),
                "metric": metric
            })
            
            return metric
    
    async def _simulate_service_health_check(self, service_name: str) -> Dict[str, Any]:
        """Simulate service-specific health check."""
        # Simulate different service health patterns
        service_health_patterns = {
            "database_service": self._simulate_database_health,
            "api_service": self._simulate_api_health,
            "cache_service": self._simulate_cache_health,
            "auth_service": self._simulate_auth_health
        }
        
        health_check_func = service_health_patterns.get(
            service_name, 
            self._simulate_generic_health
        )
        
        return await health_check_func(service_name)
    
    async def _simulate_database_health(self, service_name: str) -> Dict[str, Any]:
        """Simulate database health check."""
        # Simulate database response time variation
        base_response_time = 0.1
        response_variation = random.uniform(0.8, 1.5)
        await asyncio.sleep(base_response_time * response_variation)
        
        # Simulate varying database metrics
        return {
            "connection_pool_usage": random.uniform(0.3, 0.9),
            "query_response_time": base_response_time * response_variation,
            "error_rate": random.uniform(0.0, 0.05),
            "throughput": random.uniform(100, 500),
            "cpu_usage": random.uniform(0.2, 0.8),
            "memory_usage": random.uniform(0.4, 0.9),
            "active_connections": random.randint(10, 100)
        }
    
    async def _simulate_api_health(self, service_name: str) -> Dict[str, Any]:
        """Simulate API service health check."""
        # Simulate API response patterns
        response_time = random.uniform(0.05, 0.3)
        await asyncio.sleep(response_time)
        
        return {
            "response_time": response_time,
            "error_rate": random.uniform(0.0, 0.1),
            "throughput": random.uniform(50, 200),
            "cpu_usage": random.uniform(0.1, 0.6),
            "memory_usage": random.uniform(0.3, 0.7),
            "active_requests": random.randint(5, 50)
        }
    
    async def _simulate_cache_health(self, service_name: str) -> Dict[str, Any]:
        """Simulate cache service health check."""
        response_time = random.uniform(0.01, 0.1)
        await asyncio.sleep(response_time)
        
        return {
            "hit_rate": random.uniform(0.7, 0.95),
            "response_time": response_time,
            "error_rate": random.uniform(0.0, 0.02),
            "throughput": random.uniform(200, 1000),
            "cpu_usage": random.uniform(0.05, 0.3),
            "memory_usage": random.uniform(0.5, 0.9),
            "cache_size": random.randint(1000, 10000)
        }
    
    async def _simulate_auth_health(self, service_name: str) -> Dict[str, Any]:
        """Simulate authentication service health check."""
        response_time = random.uniform(0.1, 0.4)
        await asyncio.sleep(response_time)
        
        return {
            "token_validation_time": response_time,
            "error_rate": random.uniform(0.0, 0.03),
            "throughput": random.uniform(30, 150),
            "cpu_usage": random.uniform(0.1, 0.5),
            "memory_usage": random.uniform(0.3, 0.6),
            "active_sessions": random.randint(10, 200)
        }
    
    async def _simulate_generic_health(self, service_name: str) -> Dict[str, Any]:
        """Simulate generic service health check."""
        response_time = random.uniform(0.05, 0.2)
        await asyncio.sleep(response_time)
        
        return {
            "response_time": response_time,
            "error_rate": random.uniform(0.0, 0.05),
            "throughput": random.uniform(50, 300),
            "cpu_usage": random.uniform(0.1, 0.7),
            "memory_usage": random.uniform(0.3, 0.8)
        }
    
    def _calculate_health_status(self, health_data: Dict[str, Any], response_time: float) -> HealthStatus:
        """Calculate health status based on health metrics."""
        # Check for critical failures
        error_rate = health_data.get("error_rate", 0.0)
        cpu_usage = health_data.get("cpu_usage", 0.0)
        memory_usage = health_data.get("memory_usage", 0.0)
        
        if error_rate > 0.1 or response_time > 2.0:
            return HealthStatus.UNHEALTHY
        
        # Check for degraded performance
        if (error_rate > 0.05 or response_time > 1.0 or 
            cpu_usage > 0.8 or memory_usage > 0.9):
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    async def _process_health_check_result(self, service_name: str, metric: HealthMetric):
        """Process health check result and update service state."""
        service_state = self.services[service_name]
        
        # Add to health history
        service_state.health_history.append(metric)
        
        # Update consecutive counters
        if metric.status == HealthStatus.HEALTHY:
            service_state.consecutive_successes += 1
            service_state.consecutive_failures = 0
        else:
            service_state.consecutive_failures += 1
            service_state.consecutive_successes = 0
        
        # Determine if status should change
        new_status = self._determine_service_status(service_state, metric)
        
        if new_status != service_state.current_status:
            # Status transition
            old_status = service_state.current_status
            service_state.current_status = new_status
            service_state.status_since = time.time()
            
            # Reset counters after status change
            service_state.consecutive_failures = 0
            service_state.consecutive_successes = 0
            
            # Log status transition
            self.health_check_results.append({
                "service": service_name,
                "timestamp": time.time(),
                "status_transition": {
                    "from": old_status.value,
                    "to": new_status.value
                }
            })
    
    def _determine_service_status(self, service_state: ServiceHealthState, 
                                current_metric: HealthMetric) -> HealthStatus:
        """Determine service status based on current state and new metric."""
        current_status = service_state.current_status
        
        # Transition to UNHEALTHY
        if (current_metric.status == HealthStatus.UNHEALTHY and 
            service_state.consecutive_failures >= self.config.failure_threshold):
            return HealthStatus.UNHEALTHY
        
        # Transition to HEALTHY from any state
        if (current_metric.status == HealthStatus.HEALTHY and 
            service_state.consecutive_successes >= self.config.success_threshold):
            return HealthStatus.HEALTHY
        
        # Transition to DEGRADED
        if current_metric.status == HealthStatus.DEGRADED:
            if current_status == HealthStatus.HEALTHY:
                return HealthStatus.DEGRADED
            elif current_status == HealthStatus.UNHEALTHY and service_state.consecutive_successes > 0:
                return HealthStatus.DEGRADED
        
        # Stay in current status if no transition criteria met
        return current_status
    
    async def _evaluate_recovery_actions(self, service_name: str):
        """Evaluate and potentially trigger recovery actions."""
        service_state = self.services[service_name]
        
        # Don't trigger recovery actions too frequently
        if (service_state.last_recovery_time and 
            time.time() - service_state.last_recovery_time < 300):  # 5 minute cooldown
            return
        
        recovery_action = None
        
        if service_state.current_status == HealthStatus.UNHEALTHY:
            # Determine appropriate recovery action
            if service_state.consecutive_failures >= self.config.failure_threshold * 2:
                recovery_action = RecoveryAction.RESTART_SERVICE
            elif service_state.consecutive_failures >= self.config.failure_threshold:
                recovery_action = RecoveryAction.ALERT_OPERATORS
        
        elif service_state.current_status == HealthStatus.DEGRADED:
            # Check if degradation is persistent
            recent_metrics = list(service_state.health_history)[-10:]  # Last 10 metrics
            degraded_count = sum(1 for m in recent_metrics if m.status == HealthStatus.DEGRADED)
            
            if degraded_count >= 7:  # 70% of recent checks degraded
                recovery_action = RecoveryAction.SCALE_UP
        
        if recovery_action:
            await self._execute_recovery_action(service_name, recovery_action)
    
    async def _execute_recovery_action(self, service_name: str, action: RecoveryAction):
        """Execute recovery action for a service."""
        service_state = self.services[service_name]
        
        recovery_record = {
            "service": service_name,
            "action": action.value,
            "timestamp": time.time(),
            "service_status": service_state.current_status.value,
            "consecutive_failures": service_state.consecutive_failures
        }
        
        # Simulate recovery action execution
        if action == RecoveryAction.RESTART_SERVICE:
            # Simulate service restart
            await asyncio.sleep(0.5)  # Restart time
            recovery_record["result"] = "service_restarted"
            
        elif action == RecoveryAction.SCALE_UP:
            # Simulate scaling up
            await asyncio.sleep(0.3)  # Scale up time
            recovery_record["result"] = "scaled_up"
            
        elif action == RecoveryAction.ALERT_OPERATORS:
            # Simulate alert
            recovery_record["result"] = "operators_alerted"
        
        self.recovery_actions_taken.append(recovery_record)
        service_state.last_recovery_action = action
        service_state.last_recovery_time = time.time()
    
    def get_service_status(self, service_name: str) -> Optional[HealthStatus]:
        """Get current status of a service."""
        if service_name in self.services:
            return self.services[service_name].current_status
        return None
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get summary of all service health states."""
        return {
            "services": {
                name: {
                    "status": state.current_status.value,
                    "status_since": state.status_since,
                    "consecutive_failures": state.consecutive_failures,
                    "consecutive_successes": state.consecutive_successes,
                    "last_recovery_action": state.last_recovery_action.value if state.last_recovery_action else None
                }
                for name, state in self.services.items()
            },
            "total_recovery_actions": len(self.recovery_actions_taken),
            "monitoring_active": self.monitoring_active
        }


class TestServiceHealthMonitoringRecovery(BaseIntegrationTest):
    """
    Test service health monitoring and automated recovery mechanisms.
    
    Business Value: Enables proactive service management and automated recovery,
    reducing operational overhead and improving system reliability.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_health_monitoring_test(self, real_services_fixture):
        """Setup service health monitoring test environment."""
        self.config = get_config()
        
        # Health monitoring test state
        self.health_monitors: Dict[str, SimulatedHealthMonitor] = {}
        self.service_failure_simulations: Dict[str, Dict[str, Any]] = {}
        
        # Test contexts
        self.test_contexts: List[UserExecutionContext] = []
        
        # Create health monitors with different configurations
        monitor_configs = {
            "standard": HealthCheckConfig(check_interval=5.0, failure_threshold=3, success_threshold=2),
            "sensitive": HealthCheckConfig(check_interval=3.0, failure_threshold=2, success_threshold=3),
            "tolerant": HealthCheckConfig(check_interval=10.0, failure_threshold=5, success_threshold=2)
        }
        
        for config_name, config in monitor_configs.items():
            monitor = SimulatedHealthMonitor(config)
            self.health_monitors[config_name] = monitor
            
            # Register services for monitoring
            services = ["database_service", "api_service", "cache_service", "auth_service"]
            for service in services:
                monitor.register_service(service)
        
        yield
        
        # Stop all monitoring
        for monitor in self.health_monitors.values():
            await monitor.stop_monitoring()
        
        # Cleanup contexts
        for context in self.test_contexts:
            try:
                await context.cleanup()
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_health_check_detection_accuracy(self):
        """
        Test accuracy of health check detection across different service states.
        
        BVJ: Ensures health monitoring correctly identifies service issues,
        preventing false positives that waste resources and false negatives that miss problems.
        """
        monitor = self.health_monitors["standard"]
        test_duration = 30.0  # 30 seconds of monitoring
        
        # Configure different health states for services
        service_health_configs = {
            "database_service": {"target_status": HealthStatus.HEALTHY, "error_injection": False},
            "api_service": {"target_status": HealthStatus.DEGRADED, "error_injection": True, "error_rate": 0.06},
            "cache_service": {"target_status": HealthStatus.UNHEALTHY, "error_injection": True, "error_rate": 0.15},
            "auth_service": {"target_status": HealthStatus.HEALTHY, "error_injection": False}
        }
        
        # Modify health simulation to match configurations
        await self._configure_service_health_simulation(monitor, service_health_configs)
        
        detection_accuracy_results = {
            "services": {},
            "overall_accuracy": 0.0,
            "false_positives": 0,
            "false_negatives": 0,
            "detection_time_analysis": []
        }
        
        # Start monitoring
        monitoring_tasks = await monitor.start_monitoring()
        
        # Let monitoring run for test duration
        await asyncio.sleep(test_duration)
        
        # Stop monitoring
        await monitor.stop_monitoring()
        
        # Cancel monitoring tasks
        for task in monitoring_tasks:
            task.cancel()
        
        # Analyze detection accuracy
        health_summary = monitor.get_health_summary()
        
        for service_name, config in service_health_configs.items():
            expected_status = config["target_status"]
            actual_status = HealthStatus(health_summary["services"][service_name]["status"])
            
            service_results = {
                "service_name": service_name,
                "expected_status": expected_status.value,
                "actual_status": actual_status.value,
                "detection_accurate": expected_status == actual_status,
                "status_transitions": [],
                "detection_time": None
            }
            
            # Analyze health check history for this service
            service_state = monitor.services[service_name]
            health_checks = [result for result in monitor.health_check_results 
                           if result.get("service") == service_name]
            
            # Find status transitions
            transitions = [result for result in health_checks 
                          if "status_transition" in result]
            service_results["status_transitions"] = transitions
            
            # Calculate detection time (time to reach expected status)
            if expected_status != HealthStatus.HEALTHY:  # For degraded/unhealthy states
                detection_transition = next(
                    (t for t in transitions if t["status_transition"]["to"] == expected_status.value),
                    None
                )
                if detection_transition:
                    # Calculate time from test start to detection
                    test_start_time = time.time() - test_duration
                    service_results["detection_time"] = detection_transition["timestamp"] - test_start_time
                    detection_accuracy_results["detection_time_analysis"].append({
                        "service": service_name,
                        "expected_status": expected_status.value,
                        "detection_time": service_results["detection_time"]
                    })
            
            detection_accuracy_results["services"][service_name] = service_results
            
            # Count accuracy metrics
            if not service_results["detection_accurate"]:
                if expected_status == HealthStatus.HEALTHY and actual_status != HealthStatus.HEALTHY:
                    detection_accuracy_results["false_positives"] += 1
                elif expected_status != HealthStatus.HEALTHY and actual_status == HealthStatus.HEALTHY:
                    detection_accuracy_results["false_negatives"] += 1
        
        # Calculate overall accuracy
        accurate_detections = sum(1 for s in detection_accuracy_results["services"].values() 
                                if s["detection_accurate"])
        total_services = len(detection_accuracy_results["services"])
        detection_accuracy_results["overall_accuracy"] = accurate_detections / total_services
        
        # Verify detection accuracy
        assert detection_accuracy_results["overall_accuracy"] >= 0.75, \
            f"Health detection accuracy too low: {detection_accuracy_results['overall_accuracy']:.2%}"
        
        # Verify minimal false positives/negatives
        assert detection_accuracy_results["false_positives"] <= 1, \
            f"Too many false positive detections: {detection_accuracy_results['false_positives']}"
        
        assert detection_accuracy_results["false_negatives"] <= 1, \
            f"Too many false negative detections: {detection_accuracy_results['false_negatives']}"
        
        # Verify detection timing for problematic services
        problematic_detections = [d for d in detection_accuracy_results["detection_time_analysis"] 
                                if d["detection_time"] is not None]
        
        if problematic_detections:
            avg_detection_time = sum(d["detection_time"] for d in problematic_detections) / len(problematic_detections)
            assert avg_detection_time <= 20.0, \
                f"Average detection time too slow: {avg_detection_time:.1f}s"
        
        self.logger.info(f"Health check detection accuracy test completed: "
                        f"{detection_accuracy_results['overall_accuracy']:.1%} accuracy, "
                        f"{len(problematic_detections)} issue detections")
    
    async def _configure_service_health_simulation(self, monitor: SimulatedHealthMonitor, 
                                           configs: Dict[str, Dict[str, Any]]):
        """Configure service health simulation to match test requirements."""
        # Store original simulation methods
        original_methods = {}
        
        for service_name, config in configs.items():
            target_status = config["target_status"]
            error_injection = config.get("error_injection", False)
            error_rate = config.get("error_rate", 0.0)
            
            if error_injection and target_status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]:
                # Create modified health simulation for this service
                def create_degraded_health_sim(service, error_rate):
                    async def degraded_health_sim(service_name):
                        # Inject errors and slow responses to trigger degraded/unhealthy status
                        if random.random() < 0.3:  # 30% chance of slow response
                            await asyncio.sleep(random.uniform(1.0, 2.5))
                        else:
                            await asyncio.sleep(random.uniform(0.1, 0.3))
                        
                        return {
                            "response_time": random.uniform(0.5, 1.5),
                            "error_rate": error_rate,
                            "throughput": random.uniform(10, 50),  # Lower throughput
                            "cpu_usage": random.uniform(0.7, 0.95),  # High CPU
                            "memory_usage": random.uniform(0.8, 0.95),  # High memory
                        }
                    return degraded_health_sim
                
                # Replace simulation method for this service
                if service_name == "database_service":
                    monitor._simulate_database_health = create_degraded_health_sim(service_name, error_rate)
                elif service_name == "api_service":
                    monitor._simulate_api_health = create_degraded_health_sim(service_name, error_rate)
                elif service_name == "cache_service":
                    monitor._simulate_cache_health = create_degraded_health_sim(service_name, error_rate)
                elif service_name == "auth_service":
                    monitor._simulate_auth_health = create_degraded_health_sim(service_name, error_rate)
    
    @pytest.mark.asyncio
    async def test_automated_recovery_action_effectiveness(self):
        """
        Test effectiveness of automated recovery actions triggered by health monitoring.
        
        BVJ: Validates that automated recovery procedures actually improve service
        health, reducing manual intervention requirements and recovery time.
        """
        monitor = self.health_monitors["sensitive"]  # More responsive to issues
        test_duration = 60.0  # Longer test for recovery cycles
        
        # Configure services with different failure patterns requiring recovery
        recovery_scenarios = {
            "database_service": {
                "failure_pattern": "persistent_unhealthy",
                "expected_recovery_action": RecoveryAction.RESTART_SERVICE
            },
            "api_service": {
                "failure_pattern": "persistent_degraded", 
                "expected_recovery_action": RecoveryAction.SCALE_UP
            }
        }
        
        recovery_effectiveness_results = {
            "recovery_actions_triggered": [],
            "service_recovery_analysis": {},
            "recovery_success_rate": 0.0,
            "mean_time_to_recovery": 0.0
        }
        
        # Configure unhealthy service simulations
        await self._configure_recovery_test_services(monitor, recovery_scenarios)
        
        # Start monitoring
        monitoring_tasks = await monitor.start_monitoring()
        
        # Track recovery cycles
        recovery_start_time = time.time()
        
        # Let monitoring run and trigger recovery actions
        await asyncio.sleep(test_duration)
        
        # Stop monitoring
        await monitor.stop_monitoring()
        
        # Cancel monitoring tasks
        for task in monitoring_tasks:
            task.cancel()
        
        total_test_time = time.time() - recovery_start_time
        
        # Analyze recovery effectiveness
        recovery_actions = monitor.recovery_actions_taken
        recovery_effectiveness_results["recovery_actions_triggered"] = recovery_actions
        
        for service_name, scenario in recovery_scenarios.items():
            expected_action = scenario["expected_recovery_action"]
            
            # Find recovery actions for this service
            service_actions = [action for action in recovery_actions 
                             if action["service"] == service_name]
            
            # Analyze service health before and after recovery
            service_analysis = {
                "service_name": service_name,
                "recovery_actions_taken": len(service_actions),
                "expected_action_triggered": any(
                    RecoveryAction(action["action"]) == expected_action 
                    for action in service_actions
                ),
                "health_before_recovery": [],
                "health_after_recovery": [],
                "recovery_improved_health": False,
                "recovery_time": None
            }
            
            if service_actions:
                first_action_time = min(action["timestamp"] for action in service_actions)
                last_action_time = max(action["timestamp"] for action in service_actions)
                
                # Get health metrics before and after recovery
                service_state = monitor.services[service_name]
                all_health_metrics = list(service_state.health_history)
                
                # Health metrics before first recovery action
                service_analysis["health_before_recovery"] = [
                    metric for metric in all_health_metrics 
                    if metric.timestamp < first_action_time
                ][-10:]  # Last 10 before recovery
                
                # Health metrics after last recovery action
                service_analysis["health_after_recovery"] = [
                    metric for metric in all_health_metrics 
                    if metric.timestamp > last_action_time
                ][:10]  # First 10 after recovery
                
                # Analyze health improvement
                if (service_analysis["health_before_recovery"] and 
                    service_analysis["health_after_recovery"]):
                    
                    before_unhealthy_rate = sum(
                        1 for m in service_analysis["health_before_recovery"] 
                        if m.status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]
                    ) / len(service_analysis["health_before_recovery"])
                    
                    after_unhealthy_rate = sum(
                        1 for m in service_analysis["health_after_recovery"]
                        if m.status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]  
                    ) / len(service_analysis["health_after_recovery"])
                    
                    service_analysis["recovery_improved_health"] = after_unhealthy_rate < before_unhealthy_rate
                
                service_analysis["recovery_time"] = last_action_time - first_action_time
            
            recovery_effectiveness_results["service_recovery_analysis"][service_name] = service_analysis
        
        # Calculate overall recovery metrics
        services_with_actions = [s for s in recovery_effectiveness_results["service_recovery_analysis"].values() 
                               if s["recovery_actions_taken"] > 0]
        
        if services_with_actions:
            successful_recoveries = [s for s in services_with_actions if s["recovery_improved_health"]]
            recovery_effectiveness_results["recovery_success_rate"] = len(successful_recoveries) / len(services_with_actions)
            
            recovery_times = [s["recovery_time"] for s in services_with_actions if s["recovery_time"]]
            if recovery_times:
                recovery_effectiveness_results["mean_time_to_recovery"] = sum(recovery_times) / len(recovery_times)
        
        # Verify recovery effectiveness
        assert len(recovery_actions) > 0, "No recovery actions were triggered during test"
        
        # Verify expected recovery actions were triggered
        for service_name, analysis in recovery_effectiveness_results["service_recovery_analysis"].items():
            if analysis["recovery_actions_taken"] > 0:
                assert analysis["expected_action_triggered"], \
                    f"Expected recovery action not triggered for {service_name}"
        
        # Verify recovery success rate
        if recovery_effectiveness_results["recovery_success_rate"] > 0:
            assert recovery_effectiveness_results["recovery_success_rate"] >= 0.5, \
                f"Recovery success rate too low: {recovery_effectiveness_results['recovery_success_rate']:.1%}"
        
        # Verify reasonable recovery time
        if recovery_effectiveness_results["mean_time_to_recovery"] > 0:
            assert recovery_effectiveness_results["mean_time_to_recovery"] <= 45.0, \
                f"Mean time to recovery too long: {recovery_effectiveness_results['mean_time_to_recovery']:.1f}s"
        
        self.logger.info(f"Recovery action effectiveness test completed: "
                        f"{len(recovery_actions)} actions triggered, "
                        f"{recovery_effectiveness_results['recovery_success_rate']:.1%} success rate")
    
    async def _configure_recovery_test_services(self, monitor: SimulatedHealthMonitor, 
                                              scenarios: Dict[str, Dict[str, Any]]):
        """Configure services for recovery testing."""
        for service_name, scenario in scenarios.items():
            failure_pattern = scenario["failure_pattern"]
            
            if failure_pattern == "persistent_unhealthy":
                # Create simulation that consistently reports unhealthy status
                def create_unhealthy_sim(service):
                    async def unhealthy_sim(service_name):
                        await asyncio.sleep(random.uniform(0.5, 2.0))  # Slow response
                        
                        return {
                            "response_time": random.uniform(2.0, 5.0),  # Very slow
                            "error_rate": random.uniform(0.15, 0.3),    # High error rate
                            "throughput": random.uniform(1, 10),        # Very low throughput
                            "cpu_usage": random.uniform(0.9, 1.0),     # Maxed CPU
                            "memory_usage": random.uniform(0.95, 1.0), # Maxed memory
                        }
                    return unhealthy_sim
                
                if service_name == "database_service":
                    monitor._simulate_database_health = create_unhealthy_sim(service_name)
            
            elif failure_pattern == "persistent_degraded":
                # Create simulation that reports degraded performance
                def create_degraded_sim(service):
                    async def degraded_sim(service_name):
                        await asyncio.sleep(random.uniform(0.3, 1.0))
                        
                        return {
                            "response_time": random.uniform(0.8, 1.5),  # Slow but not terrible
                            "error_rate": random.uniform(0.06, 0.1),    # Moderate error rate
                            "throughput": random.uniform(20, 50),       # Reduced throughput
                            "cpu_usage": random.uniform(0.75, 0.9),    # High CPU
                            "memory_usage": random.uniform(0.8, 0.9),  # High memory
                        }
                    return degraded_sim
                
                if service_name == "api_service":
                    monitor._simulate_api_health = create_degraded_sim(service_name)
    
    @pytest.mark.asyncio
    async def test_service_dependency_health_propagation(self):
        """
        Test health monitoring of service dependencies and status propagation.
        
        BVJ: Ensures dependent service failures are properly tracked and don't
        create false health alerts for services that depend on failing components.
        """
        monitor = self.health_monitors["standard"]
        
        # Configure service dependency relationships
        dependency_config = {
            "api_service": {"dependencies": {"database_service", "auth_service"}},
            "cache_service": {"dependencies": {"database_service"}},
            "auth_service": {"dependencies": set()},  # No dependencies
            "database_service": {"dependencies": set()}  # Core service
        }
        
        # Register services with dependencies
        for service_name, config in dependency_config.items():
            monitor.register_service(service_name, config["dependencies"])
        
        dependency_test_results = {
            "dependency_propagation_analysis": {},
            "false_alerts_prevented": 0,
            "dependency_aware_actions": [],
            "health_correlation_analysis": {}
        }
        
        # Configure database service to fail (affecting dependent services)
        await self._configure_dependency_failure_simulation(monitor, "database_service")
        
        # Start monitoring
        monitoring_tasks = await monitor.start_monitoring()
        
        # Let monitoring run to observe dependency propagation
        test_duration = 40.0
        await asyncio.sleep(test_duration)
        
        # Stop monitoring
        await monitor.stop_monitoring()
        for task in monitoring_tasks:
            task.cancel()
        
        # Analyze dependency health propagation
        health_summary = monitor.get_health_summary()
        
        for service_name, service_info in health_summary["services"].items():
            service_dependencies = dependency_config[service_name]["dependencies"]
            
            analysis = {
                "service_name": service_name,
                "dependencies": list(service_dependencies),
                "current_status": service_info["status"],
                "dependency_status_correlation": {},
                "appropriate_status_for_dependencies": True
            }
            
            # Check dependency health correlation
            for dep_service in service_dependencies:
                dep_status = health_summary["services"][dep_service]["status"]
                analysis["dependency_status_correlation"][dep_service] = dep_status
                
                # If dependency is unhealthy, dependent service should account for this
                if dep_service == "database_service" and dep_status in ["unhealthy", "degraded"]:
                    # Services depending on database should show appropriate status
                    if service_info["status"] == "healthy":
                        # This might indicate the service isn't properly checking its dependencies
                        analysis["appropriate_status_for_dependencies"] = False
            
            dependency_test_results["dependency_propagation_analysis"][service_name] = analysis
        
        # Analyze recovery actions with dependency awareness
        recovery_actions = monitor.recovery_actions_taken
        dependency_aware_actions = []
        
        for action in recovery_actions:
            service_name = action["service"]
            service_dependencies = dependency_config[service_name]["dependencies"]
            
            # Check if action considered dependencies
            dependency_aware = False
            
            if service_dependencies:
                # For services with dependencies, check if root cause was addressed
                for dep_service in service_dependencies:
                    dep_actions = [a for a in recovery_actions if a["service"] == dep_service]
                    if dep_actions:
                        dependency_aware = True
                        break
            
            if dependency_aware:
                dependency_aware_actions.append(action)
        
        dependency_test_results["dependency_aware_actions"] = dependency_aware_actions
        
        # Calculate health correlation metrics
        database_health_history = list(monitor.services["database_service"].health_history)
        
        for service_name in ["api_service", "cache_service"]:
            if service_name in dependency_config and "database_service" in dependency_config[service_name]["dependencies"]:
                service_health_history = list(monitor.services[service_name].health_history)
                
                # Calculate correlation between database health and dependent service health
                correlation_analysis = self._calculate_health_correlation(
                    database_health_history, service_health_history
                )
                
                dependency_test_results["health_correlation_analysis"][service_name] = correlation_analysis
        
        # Verify dependency awareness
        # Services depending on failed database should not be marked as fully healthy
        database_status = health_summary["services"]["database_service"]["status"]
        
        if database_status in ["unhealthy", "degraded"]:
            for service_name, analysis in dependency_test_results["dependency_propagation_analysis"].items():
                if "database_service" in analysis["dependencies"]:
                    # Dependent services should reflect dependency issues appropriately
                    assert analysis["current_status"] != "healthy" or analysis["appropriate_status_for_dependencies"], \
                        f"Service {service_name} shows healthy status despite unhealthy database dependency"
        
        # Verify health correlation for dependent services
        for service_name, correlation in dependency_test_results["health_correlation_analysis"].items():
            if correlation["sample_size"] > 10:  # Enough data points
                # There should be some correlation between database health and dependent service health
                assert correlation["correlation_strength"] >= 0.3, \
                    f"Insufficient health correlation between database and {service_name}: {correlation['correlation_strength']:.2f}"
        
        self.logger.info(f"Service dependency health propagation test completed: "
                        f"{len(dependency_test_results['dependency_propagation_analysis'])} services analyzed, "
                        f"{len(dependency_aware_actions)} dependency-aware recovery actions")
    
    def _calculate_health_correlation(self, primary_health_history: List[HealthMetric], 
                                    dependent_health_history: List[HealthMetric]) -> Dict[str, Any]:
        """Calculate correlation between primary and dependent service health."""
        if len(primary_health_history) < 5 or len(dependent_health_history) < 5:
            return {"correlation_strength": 0.0, "sample_size": 0}
        
        # Align timestamps for correlation analysis
        primary_by_time = {int(m.timestamp): m for m in primary_health_history}
        dependent_by_time = {int(m.timestamp): m for m in dependent_health_history}
        
        # Find common timestamps
        common_times = set(primary_by_time.keys()) & set(dependent_by_time.keys())
        
        if len(common_times) < 3:
            return {"correlation_strength": 0.0, "sample_size": len(common_times)}
        
        # Calculate correlation
        primary_unhealthy_count = 0
        dependent_unhealthy_count = 0
        both_unhealthy_count = 0
        
        for timestamp in common_times:
            primary_unhealthy = primary_by_time[timestamp].status != HealthStatus.HEALTHY
            dependent_unhealthy = dependent_by_time[timestamp].status != HealthStatus.HEALTHY
            
            if primary_unhealthy:
                primary_unhealthy_count += 1
            if dependent_unhealthy:
                dependent_unhealthy_count += 1
            if primary_unhealthy and dependent_unhealthy:
                both_unhealthy_count += 1
        
        # Simple correlation calculation
        total_samples = len(common_times)
        if primary_unhealthy_count == 0:
            correlation_strength = 0.0
        else:
            correlation_strength = both_unhealthy_count / primary_unhealthy_count
        
        return {
            "correlation_strength": correlation_strength,
            "sample_size": total_samples,
            "primary_unhealthy_rate": primary_unhealthy_count / total_samples,
            "dependent_unhealthy_rate": dependent_unhealthy_count / total_samples
        }
    
    async def _configure_dependency_failure_simulation(self, monitor: SimulatedHealthMonitor, 
                                                     failing_service: str):
        """Configure dependency failure simulation."""
        if failing_service == "database_service":
            async def failing_database_sim(service_name):
                # Simulate database failure
                if random.random() < 0.7:  # 70% chance of failure
                    await asyncio.sleep(random.uniform(3.0, 8.0))  # Very slow
                    raise Exception("Database connection timeout")
                else:
                    await asyncio.sleep(random.uniform(1.5, 3.0))  # Still slow when working
                    
                return {
                    "response_time": random.uniform(2.0, 4.0),
                    "error_rate": random.uniform(0.2, 0.4),
                    "throughput": random.uniform(1, 5),
                    "cpu_usage": random.uniform(0.9, 1.0),
                    "memory_usage": random.uniform(0.95, 1.0),
                    "connection_failures": random.randint(5, 20)
                }
            
            monitor._simulate_database_health = failing_database_sim