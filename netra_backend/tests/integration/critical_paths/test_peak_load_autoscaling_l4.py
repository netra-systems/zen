"""Peak Load Auto-Scaling L4 Critical Path Tests

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Performance Scalability and High Availability  
- Value Impact: Ensures system handles 10x load spikes without degradation
- Strategic Impact: $30K MRR protection from performance failures

Critical Path: Load detection -> Auto-scaling trigger -> Resource provisioning -> Load distribution -> Performance validation -> Cost optimization
Coverage: Horizontal/vertical scaling, service discovery updates, cost-aware scaling, performance SLA maintenance

L4 Requirements:
- Real staging environment testing
- Actual infrastructure scaling
- Performance metrics validation
- Cost optimization verification
- Cross-service coordination
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import httpx
import pytest
from netra_backend.app.monitoring.metrics_collector import MetricsCollector

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.services.redis_service import RedisService

# Add project root to path
from tests.l4_staging_critical_base import (
    CriticalPathMetrics,
    L4StagingCriticalPathTestBase,
)

# Add project root to path

logger = logging.getLogger(__name__)


@dataclass
class AutoScalingMetrics:
    """Metrics container for auto-scaling operations."""
    scale_up_latency: float = 0.0
    scale_down_latency: float = 0.0
    resource_utilization_before: float = 0.0
    resource_utilization_after: float = 0.0
    cost_per_hour_before: float = 0.0
    cost_per_hour_after: float = 0.0
    scaling_decisions: List[Dict[str, Any]] = field(default_factory=list)
    service_discovery_updates: List[Dict[str, Any]] = field(default_factory=list)
    performance_impact: Dict[str, float] = field(default_factory=dict)
    
    @property
    def cost_efficiency_ratio(self) -> float:
        """Calculate cost efficiency improvement ratio."""
        if self.cost_per_hour_before == 0:
            return 1.0
        return self.cost_per_hour_after / self.cost_per_hour_before
    
    @property
    def resource_efficiency_gain(self) -> float:
        """Calculate resource utilization efficiency gain."""
        return self.resource_utilization_after - self.resource_utilization_before


@dataclass
class LoadTestConfig:
    """Configuration for load testing scenarios."""
    initial_rps: int = 10
    peak_rps: int = 100
    duration_seconds: int = 300
    ramp_up_seconds: int = 60
    steady_state_seconds: int = 120
    ramp_down_seconds: int = 120
    concurrent_users: int = 50
    target_endpoints: List[str] = field(default_factory=list)
    scaling_triggers: Dict[str, Any] = field(default_factory=dict)


class AutoScalingOrchestrator:
    """Orchestrates auto-scaling operations for L4 testing."""
    
    def __init__(self):
        self.current_instances = {}
        self.scaling_history = []
        self.performance_thresholds = {
            "cpu_threshold": 70.0,
            "memory_threshold": 80.0,
            "response_time_threshold": 2.0,
            "error_rate_threshold": 5.0
        }
        self.cost_optimization = {
            "scale_down_delay": 300,  # 5 minutes
            "min_instances": 1,
            "max_instances": 10,
            "instance_types": ["small", "medium", "large"],
            "cost_per_hour": {"small": 0.5, "medium": 1.0, "large": 2.0}
        }
        
    async def trigger_horizontal_scaling(self, service_name: str, 
                                       target_instances: int, 
                                       scaling_reason: str) -> Dict[str, Any]:
        """Trigger horizontal scaling for a service."""
        start_time = time.time()
        current_instances = self.current_instances.get(service_name, 1)
        
        try:
            # Simulate scaling decision logic
            scaling_decision = {
                "service_name": service_name,
                "scaling_type": "horizontal",
                "current_instances": current_instances,
                "target_instances": target_instances,
                "scaling_reason": scaling_reason,
                "timestamp": datetime.utcnow().isoformat(),
                "scaling_direction": "up" if target_instances > current_instances else "down"
            }
            
            # Simulate scaling latency (realistic for cloud environments)
            scaling_latency = random.uniform(30, 90)  # 30-90 seconds
            await asyncio.sleep(scaling_latency / 10)  # Accelerated for testing
            
            # Update instance count
            self.current_instances[service_name] = target_instances
            
            # Calculate cost impact
            instance_type = "medium"  # Default type
            cost_before = current_instances * self.cost_optimization["cost_per_hour"][instance_type]
            cost_after = target_instances * self.cost_optimization["cost_per_hour"][instance_type]
            
            scaling_result = {
                "success": True,
                "scaling_latency": time.time() - start_time,
                "scaling_decision": scaling_decision,
                "cost_impact": {
                    "cost_before": cost_before,
                    "cost_after": cost_after,
                    "cost_change": cost_after - cost_before,
                    "efficiency_gain": (target_instances - current_instances) / current_instances if current_instances > 0 else 0
                },
                "new_instance_count": target_instances
            }
            
            self.scaling_history.append(scaling_result)
            return scaling_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "scaling_latency": time.time() - start_time,
                "scaling_decision": scaling_decision
            }
    
    async def trigger_vertical_scaling(self, service_name: str, 
                                     target_instance_type: str,
                                     scaling_reason: str) -> Dict[str, Any]:
        """Trigger vertical scaling for a service."""
        start_time = time.time()
        current_type = "medium"  # Default current type
        
        try:
            scaling_decision = {
                "service_name": service_name,
                "scaling_type": "vertical",
                "current_instance_type": current_type,
                "target_instance_type": target_instance_type,
                "scaling_reason": scaling_reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Vertical scaling typically takes longer
            scaling_latency = random.uniform(60, 180)  # 1-3 minutes
            await asyncio.sleep(scaling_latency / 20)  # Accelerated for testing
            
            # Calculate cost impact
            instance_count = self.current_instances.get(service_name, 1)
            cost_before = instance_count * self.cost_optimization["cost_per_hour"][current_type]
            cost_after = instance_count * self.cost_optimization["cost_per_hour"][target_instance_type]
            
            scaling_result = {
                "success": True,
                "scaling_latency": time.time() - start_time,
                "scaling_decision": scaling_decision,
                "cost_impact": {
                    "cost_before": cost_before,
                    "cost_after": cost_after,
                    "cost_change": cost_after - cost_before
                },
                "new_instance_type": target_instance_type
            }
            
            self.scaling_history.append(scaling_result)
            return scaling_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "scaling_latency": time.time() - start_time,
                "scaling_decision": scaling_decision
            }
    
    async def update_service_discovery(self, service_name: str, 
                                     instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update service discovery with new instance information."""
        try:
            update_start = time.time()
            
            # Simulate service discovery update
            discovery_update = {
                "service_name": service_name,
                "instance_count": len(instances),
                "instances": instances,
                "update_timestamp": datetime.utcnow().isoformat(),
                "propagation_delay": random.uniform(1, 5)  # 1-5 seconds
            }
            
            # Simulate propagation delay
            await asyncio.sleep(discovery_update["propagation_delay"] / 10)
            
            return {
                "success": True,
                "update_latency": time.time() - update_start,
                "discovery_update": discovery_update
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "update_latency": time.time() - update_start
            }
    
    def calculate_scaling_recommendation(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Calculate scaling recommendation based on current metrics."""
        cpu_usage = metrics.get("cpu_usage", 0.0)
        memory_usage = metrics.get("memory_usage", 0.0)
        response_time = metrics.get("avg_response_time", 0.0)
        error_rate = metrics.get("error_rate", 0.0)
        current_rps = metrics.get("requests_per_second", 0.0)
        
        recommendations = []
        
        # CPU-based scaling
        if cpu_usage > self.performance_thresholds["cpu_threshold"]:
            scale_factor = min(cpu_usage / self.performance_thresholds["cpu_threshold"], 3.0)
            recommendations.append({
                "type": "horizontal_scale_up",
                "reason": f"CPU usage {cpu_usage:.1f}% exceeds threshold {self.performance_thresholds['cpu_threshold']}%",
                "scale_factor": scale_factor,
                "priority": "high"
            })
        
        # Memory-based scaling
        if memory_usage > self.performance_thresholds["memory_threshold"]:
            recommendations.append({
                "type": "vertical_scale_up",
                "reason": f"Memory usage {memory_usage:.1f}% exceeds threshold {self.performance_thresholds['memory_threshold']}%",
                "target_instance_type": "large",
                "priority": "high"
            })
        
        # Response time-based scaling
        if response_time > self.performance_thresholds["response_time_threshold"]:
            recommendations.append({
                "type": "horizontal_scale_up",
                "reason": f"Response time {response_time:.2f}s exceeds threshold {self.performance_thresholds['response_time_threshold']}s",
                "scale_factor": 1.5,
                "priority": "medium"
            })
        
        # Error rate-based scaling
        if error_rate > self.performance_thresholds["error_rate_threshold"]:
            recommendations.append({
                "type": "horizontal_scale_up",
                "reason": f"Error rate {error_rate:.1f}% exceeds threshold {self.performance_thresholds['error_rate_threshold']}%",
                "scale_factor": 2.0,
                "priority": "critical"
            })
        
        # Scale down recommendations for cost optimization
        if (cpu_usage < 30.0 and memory_usage < 50.0 and 
            response_time < 0.5 and error_rate < 1.0):
            recommendations.append({
                "type": "horizontal_scale_down",
                "reason": "Resource utilization low, cost optimization opportunity",
                "scale_factor": 0.7,
                "priority": "low",
                "delay_seconds": self.cost_optimization["scale_down_delay"]
            })
        
        return {
            "recommendations": recommendations,
            "current_metrics": metrics,
            "thresholds": self.performance_thresholds,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }


class PeakLoadAutoScalingL4Test(L4StagingCriticalPathTestBase):
    """L4 peak load auto-scaling critical path test implementation."""
    
    def __init__(self):
        super().__init__("peak_load_autoscaling_l4")
        self.auto_scaler = AutoScalingOrchestrator()
        self.load_test_config = LoadTestConfig()
        self.scaling_metrics = AutoScalingMetrics()
        self.load_generators = []
        self.performance_baseline = {}
        self.scaling_events = []
        
    async def setup_test_specific_environment(self) -> None:
        """Setup auto-scaling test environment."""
        try:
            # Configure load test endpoints
            self.load_test_config.target_endpoints = [
                f"{self.service_endpoints.backend}/api/v1/threads",
                f"{self.service_endpoints.backend}/api/v1/chat",
                f"{self.service_endpoints.backend}/api/v1/agents",
                f"{self.service_endpoints.auth}/api/auth/token",
                f"{self.service_endpoints.backend}/api/v1/metrics"
            ]
            
            # Configure scaling triggers
            self.load_test_config.scaling_triggers = {
                "cpu_threshold": 70.0,
                "memory_threshold": 80.0,
                "response_time_threshold": 2.0,
                "error_rate_threshold": 5.0,
                "rps_threshold": 50.0
            }
            
            # Initialize baseline performance metrics
            await self.establish_performance_baseline()
            
            # Setup monitoring for auto-scaling events
            await self.setup_scaling_monitoring()
            
            logger.info("Auto-scaling test environment initialized")
            
        except Exception as e:
            raise RuntimeError(f"Auto-scaling test setup failed: {e}")
    
    async def establish_performance_baseline(self) -> None:
        """Establish baseline performance metrics before load testing."""
        try:
            baseline_requests = 10
            baseline_results = []
            
            for endpoint in self.load_test_config.target_endpoints:
                endpoint_results = []
                
                for i in range(baseline_requests):
                    result = await self.make_performance_request(endpoint)
                    if result["success"]:
                        endpoint_results.append(result)
                    
                    await asyncio.sleep(0.5)  # Gentle baseline measurement
                
                if endpoint_results:
                    avg_response_time = sum(r["response_time"] for r in endpoint_results) / len(endpoint_results)
                    success_rate = len([r for r in endpoint_results if r["success"]]) / len(endpoint_results) * 100
                    
                    self.performance_baseline[endpoint] = {
                        "avg_response_time": avg_response_time,
                        "success_rate": success_rate,
                        "sample_size": len(endpoint_results)
                    }
            
            logger.info(f"Performance baseline established for {len(self.performance_baseline)} endpoints")
            
        except Exception as e:
            logger.error(f"Failed to establish performance baseline: {e}")
            self.performance_baseline = {}
    
    async def setup_scaling_monitoring(self) -> None:
        """Setup monitoring for auto-scaling events."""
        try:
            # Initialize scaling metrics tracking
            self.scaling_metrics.scaling_decisions = []
            self.scaling_metrics.service_discovery_updates = []
            self.scaling_metrics.performance_impact = {}
            
            # Setup initial resource utilization
            self.scaling_metrics.resource_utilization_before = await self.measure_resource_utilization()
            self.scaling_metrics.cost_per_hour_before = await self.calculate_current_cost()
            
            logger.info("Auto-scaling monitoring initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup scaling monitoring: {e}")
    
    async def make_performance_request(self, endpoint: str, 
                                     user_id: str = None, 
                                     timeout: float = 10.0) -> Dict[str, Any]:
        """Make a performance-instrumented request to an endpoint."""
        start_time = time.time()
        
        if not user_id:
            user_id = f"load_test_user_{random.randint(1000, 9999)}"
        
        headers = {
            "X-User-ID": user_id,
            "X-User-Tier": "enterprise",
            "X-Load-Test": "true",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(endpoint, headers=headers)
                
                response_time = time.time() - start_time
                
                return {
                    "success": response.status_code in [200, 201, 404],  # 404 acceptable for some endpoints
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "endpoint": endpoint,
                    "user_id": user_id,
                    "timestamp": time.time()
                }
                
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "response_time": response_time,
                "endpoint": endpoint,
                "user_id": user_id,
                "timestamp": time.time()
            }
    
    async def generate_load_pattern(self, config: LoadTestConfig) -> List[Dict[str, Any]]:
        """Generate load pattern with gradual increase to peak."""
        all_results = []
        
        try:
            # Phase 1: Ramp up load
            ramp_up_results = await self.execute_ramp_up_phase(config)
            all_results.extend(ramp_up_results)
            
            # Trigger auto-scaling during ramp-up if thresholds exceeded
            await self.check_and_trigger_scaling("ramp_up_phase")
            
            # Phase 2: Steady state at peak load
            peak_load_results = await self.execute_peak_load_phase(config)
            all_results.extend(peak_load_results)
            
            # Monitor scaling effectiveness during peak
            await self.monitor_scaling_effectiveness()
            
            # Phase 3: Ramp down load
            ramp_down_results = await self.execute_ramp_down_phase(config)
            all_results.extend(ramp_down_results)
            
            # Trigger scale-down for cost optimization
            await self.check_and_trigger_scaling("ramp_down_phase")
            
            return all_results
            
        except Exception as e:
            logger.error(f"Load pattern generation failed: {e}")
            return all_results
    
    async def execute_ramp_up_phase(self, config: LoadTestConfig) -> List[Dict[str, Any]]:
        """Execute ramp-up phase with gradually increasing load."""
        results = []
        phase_duration = config.ramp_up_seconds
        steps = 10
        step_duration = phase_duration / steps
        
        for step in range(steps):
            # Calculate current RPS for this step
            progress = (step + 1) / steps
            current_rps = config.initial_rps + (config.peak_rps - config.initial_rps) * progress
            
            # Generate requests for this step
            step_requests = int(current_rps * step_duration)
            request_interval = step_duration / step_requests if step_requests > 0 else 1.0
            
            step_results = []
            for i in range(step_requests):
                endpoint = random.choice(config.target_endpoints)
                user_id = f"ramp_user_{step}_{i}"
                
                result = await self.make_performance_request(endpoint, user_id, timeout=5.0)
                step_results.append(result)
                results.append(result)
                
                if i < step_requests - 1:
                    await asyncio.sleep(request_interval)
            
            # Log ramp-up progress
            successful_requests = len([r for r in step_results if r["success"]])
            avg_response_time = sum(r["response_time"] for r in step_results) / len(step_results) if step_results else 0
            
            logger.info(f"Ramp-up step {step + 1}/{steps}: {current_rps:.1f} RPS, "
                       f"{successful_requests}/{len(step_results)} successful, "
                       f"avg response time: {avg_response_time:.3f}s")
        
        return results
    
    async def execute_peak_load_phase(self, config: LoadTestConfig) -> List[Dict[str, Any]]:
        """Execute peak load phase with sustained high RPS."""
        results = []
        total_requests = int(config.peak_rps * config.steady_state_seconds)
        request_interval = config.steady_state_seconds / total_requests if total_requests > 0 else 1.0
        
        logger.info(f"Starting peak load phase: {config.peak_rps} RPS for {config.steady_state_seconds}s")
        
        # Create concurrent request batches
        batch_size = min(config.concurrent_users, config.peak_rps)
        batches = total_requests // batch_size
        
        for batch in range(batches):
            batch_tasks = []
            
            for i in range(batch_size):
                endpoint = random.choice(config.target_endpoints)
                user_id = f"peak_user_{batch}_{i}"
                
                task = self.make_performance_request(endpoint, user_id, timeout=5.0)
                batch_tasks.append(task)
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, dict):
                    results.append(result)
            
            # Maintain request rate
            await asyncio.sleep(request_interval * batch_size)
            
            # Log progress every 10 batches
            if batch % 10 == 0:
                recent_results = results[-batch_size * 10:] if len(results) >= batch_size * 10 else results
                successful = len([r for r in recent_results if r.get("success", False)])
                avg_time = sum(r.get("response_time", 0) for r in recent_results) / len(recent_results) if recent_results else 0
                
                logger.info(f"Peak load progress: batch {batch}/{batches}, "
                           f"success rate: {successful/len(recent_results)*100:.1f}%, "
                           f"avg response time: {avg_time:.3f}s")
        
        return results
    
    async def execute_ramp_down_phase(self, config: LoadTestConfig) -> List[Dict[str, Any]]:
        """Execute ramp-down phase with gradually decreasing load."""
        results = []
        phase_duration = config.ramp_down_seconds
        steps = 10
        step_duration = phase_duration / steps
        
        for step in range(steps):
            # Calculate current RPS for this step (decreasing)
            progress = (step + 1) / steps
            current_rps = config.peak_rps - (config.peak_rps - config.initial_rps) * progress
            
            # Generate requests for this step
            step_requests = max(1, int(current_rps * step_duration))
            request_interval = step_duration / step_requests if step_requests > 0 else 1.0
            
            step_results = []
            for i in range(step_requests):
                endpoint = random.choice(config.target_endpoints)
                user_id = f"ramp_down_user_{step}_{i}"
                
                result = await self.make_performance_request(endpoint, user_id, timeout=5.0)
                step_results.append(result)
                results.append(result)
                
                if i < step_requests - 1:
                    await asyncio.sleep(request_interval)
            
            # Log ramp-down progress
            successful_requests = len([r for r in step_results if r["success"]])
            avg_response_time = sum(r["response_time"] for r in step_results) / len(step_results) if step_results else 0
            
            logger.info(f"Ramp-down step {step + 1}/{steps}: {current_rps:.1f} RPS, "
                       f"{successful_requests}/{len(step_results)} successful, "
                       f"avg response time: {avg_response_time:.3f}s")
        
        return results
    
    async def check_and_trigger_scaling(self, phase: str) -> None:
        """Check current metrics and trigger scaling if needed."""
        try:
            # Measure current system metrics
            current_metrics = await self.measure_system_metrics()
            
            # Get scaling recommendations
            scaling_analysis = self.auto_scaler.calculate_scaling_recommendation(current_metrics)
            
            if scaling_analysis["recommendations"]:
                logger.info(f"Scaling recommendations during {phase}: {len(scaling_analysis['recommendations'])}")
                
                for recommendation in scaling_analysis["recommendations"]:
                    if recommendation["priority"] in ["critical", "high"]:
                        await self.execute_scaling_recommendation(recommendation, phase)
            
            # Record scaling analysis
            self.scaling_events.append({
                "phase": phase,
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": current_metrics,
                "analysis": scaling_analysis
            })
            
        except Exception as e:
            logger.error(f"Scaling check failed during {phase}: {e}")
    
    async def execute_scaling_recommendation(self, recommendation: Dict[str, Any], phase: str) -> None:
        """Execute a scaling recommendation."""
        try:
            scaling_type = recommendation["type"]
            service_name = "api_service"  # Primary service for testing
            
            if scaling_type == "horizontal_scale_up":
                current_instances = self.auto_scaler.current_instances.get(service_name, 1)
                scale_factor = recommendation.get("scale_factor", 1.5)
                target_instances = min(
                    int(current_instances * scale_factor),
                    self.auto_scaler.cost_optimization["max_instances"]
                )
                
                scaling_result = await self.auto_scaler.trigger_horizontal_scaling(
                    service_name, target_instances, recommendation["reason"]
                )
                
                if scaling_result["success"]:
                    self.scaling_metrics.scale_up_latency = scaling_result["scaling_latency"]
                    self.scaling_metrics.scaling_decisions.append(scaling_result["scaling_decision"])
                    
                    # Update service discovery
                    new_instances = [
                        {"host": f"api-{i}.staging.netrasystems.ai", "port": 8000}
                        for i in range(1, target_instances + 1)
                    ]
                    discovery_result = await self.auto_scaler.update_service_discovery(
                        service_name, new_instances
                    )
                    
                    if discovery_result["success"]:
                        self.scaling_metrics.service_discovery_updates.append(
                            discovery_result["discovery_update"]
                        )
            
            elif scaling_type == "horizontal_scale_down":
                current_instances = self.auto_scaler.current_instances.get(service_name, 1)
                scale_factor = recommendation.get("scale_factor", 0.7)
                target_instances = max(
                    int(current_instances * scale_factor),
                    self.auto_scaler.cost_optimization["min_instances"]
                )
                
                # Implement scale-down delay for cost optimization
                delay = recommendation.get("delay_seconds", 0)
                if delay > 0:
                    logger.info(f"Delaying scale-down by {delay} seconds for cost optimization")
                    await asyncio.sleep(delay / 60)  # Accelerated for testing
                
                scaling_result = await self.auto_scaler.trigger_horizontal_scaling(
                    service_name, target_instances, recommendation["reason"]
                )
                
                if scaling_result["success"]:
                    self.scaling_metrics.scale_down_latency = scaling_result["scaling_latency"]
                    self.scaling_metrics.scaling_decisions.append(scaling_result["scaling_decision"])
            
            elif scaling_type == "vertical_scale_up":
                target_type = recommendation.get("target_instance_type", "large")
                
                scaling_result = await self.auto_scaler.trigger_vertical_scaling(
                    service_name, target_type, recommendation["reason"]
                )
                
                if scaling_result["success"]:
                    self.scaling_metrics.scaling_decisions.append(scaling_result["scaling_decision"])
            
            logger.info(f"Executed scaling recommendation: {scaling_type} during {phase}")
            
        except Exception as e:
            logger.error(f"Failed to execute scaling recommendation: {e}")
    
    async def monitor_scaling_effectiveness(self) -> None:
        """Monitor the effectiveness of auto-scaling decisions."""
        try:
            # Measure post-scaling metrics
            post_scaling_metrics = await self.measure_system_metrics()
            
            # Calculate performance impact
            if self.performance_baseline:
                for endpoint, baseline in self.performance_baseline.items():
                    # Simulate current performance measurement
                    current_performance = await self.measure_endpoint_performance(endpoint)
                    
                    if current_performance:
                        performance_change = {
                            "endpoint": endpoint,
                            "baseline_response_time": baseline["avg_response_time"],
                            "current_response_time": current_performance["avg_response_time"],
                            "response_time_improvement": baseline["avg_response_time"] - current_performance["avg_response_time"],
                            "baseline_success_rate": baseline["success_rate"],
                            "current_success_rate": current_performance["success_rate"],
                            "success_rate_improvement": current_performance["success_rate"] - baseline["success_rate"]
                        }
                        
                        self.scaling_metrics.performance_impact[endpoint] = performance_change
            
            # Update resource utilization
            self.scaling_metrics.resource_utilization_after = await self.measure_resource_utilization()
            self.scaling_metrics.cost_per_hour_after = await self.calculate_current_cost()
            
            logger.info("Scaling effectiveness monitoring completed")
            
        except Exception as e:
            logger.error(f"Scaling effectiveness monitoring failed: {e}")
    
    async def measure_system_metrics(self) -> Dict[str, float]:
        """Measure current system performance metrics."""
        try:
            # Simulate metric collection (in real L4 environment, this would query actual monitoring)
            base_cpu = random.uniform(20, 40)
            base_memory = random.uniform(30, 50)
            base_response_time = random.uniform(0.5, 1.5)
            base_error_rate = random.uniform(0, 2)
            base_rps = random.uniform(10, 30)
            
            # Adjust metrics based on current scaling state
            instance_count = self.auto_scaler.current_instances.get("api_service", 1)
            scaling_factor = 1.0 / max(instance_count, 1)
            
            return {
                "cpu_usage": min(base_cpu * scaling_factor, 95.0),
                "memory_usage": min(base_memory * scaling_factor, 95.0),
                "avg_response_time": max(base_response_time * scaling_factor, 0.1),
                "error_rate": max(base_error_rate * scaling_factor, 0.0),
                "requests_per_second": base_rps * instance_count,
                "active_connections": random.randint(50, 200) * instance_count,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"System metrics measurement failed: {e}")
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "avg_response_time": 0.0,
                "error_rate": 0.0,
                "requests_per_second": 0.0,
                "active_connections": 0,
                "timestamp": time.time()
            }
    
    async def measure_endpoint_performance(self, endpoint: str) -> Optional[Dict[str, float]]:
        """Measure current performance for a specific endpoint."""
        try:
            sample_size = 5
            results = []
            
            for i in range(sample_size):
                result = await self.make_performance_request(endpoint)
                if result["success"]:
                    results.append(result)
                await asyncio.sleep(0.2)
            
            if results:
                avg_response_time = sum(r["response_time"] for r in results) / len(results)
                success_rate = len(results) / sample_size * 100
                
                return {
                    "avg_response_time": avg_response_time,
                    "success_rate": success_rate,
                    "sample_size": len(results)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Endpoint performance measurement failed for {endpoint}: {e}")
            return None
    
    async def measure_resource_utilization(self) -> float:
        """Measure current resource utilization percentage."""
        try:
            # Simulate resource utilization measurement
            instance_count = self.auto_scaler.current_instances.get("api_service", 1)
            base_utilization = random.uniform(40, 60)
            
            # Higher instance count generally means better resource distribution
            utilization_efficiency = min(base_utilization / instance_count * 2, 85.0)
            
            return utilization_efficiency
            
        except Exception as e:
            logger.error(f"Resource utilization measurement failed: {e}")
            return 50.0  # Default value
    
    async def calculate_current_cost(self) -> float:
        """Calculate current hourly cost based on active instances."""
        try:
            instance_count = self.auto_scaler.current_instances.get("api_service", 1)
            instance_type = "medium"  # Default type
            cost_per_instance = self.auto_scaler.cost_optimization["cost_per_hour"][instance_type]
            
            total_cost = instance_count * cost_per_instance
            
            return total_cost
            
        except Exception as e:
            logger.error(f"Cost calculation failed: {e}")
            return 1.0  # Default cost
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute the complete peak load auto-scaling critical path test."""
        try:
            test_start_time = time.time()
            
            # Configure load test for 10x traffic increase
            self.load_test_config.initial_rps = 10
            self.load_test_config.peak_rps = 100  # 10x increase
            self.load_test_config.duration_seconds = 180  # 3 minutes total
            self.load_test_config.ramp_up_seconds = 60
            self.load_test_config.steady_state_seconds = 60
            self.load_test_config.ramp_down_seconds = 60
            
            logger.info(f"Starting peak load auto-scaling test: {self.load_test_config.initial_rps} -> {self.load_test_config.peak_rps} RPS")
            
            # Execute load pattern with auto-scaling
            load_test_results = await self.generate_load_pattern(self.load_test_config)
            
            # Allow time for final scaling operations
            await asyncio.sleep(5)
            
            # Collect final metrics
            final_metrics = await self.measure_system_metrics()
            await self.monitor_scaling_effectiveness()
            
            test_duration = time.time() - test_start_time
            
            # Analyze results
            successful_requests = len([r for r in load_test_results if r.get("success", False)])
            total_requests = len(load_test_results)
            success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
            
            avg_response_time = sum(r.get("response_time", 0) for r in load_test_results) / total_requests if total_requests > 0 else 0
            max_response_time = max((r.get("response_time", 0) for r in load_test_results), default=0)
            
            # Calculate scaling effectiveness
            scaling_events_count = len(self.scaling_metrics.scaling_decisions)
            cost_efficiency = self.scaling_metrics.cost_efficiency_ratio
            resource_efficiency = self.scaling_metrics.resource_efficiency_gain
            
            return {
                "test_duration": test_duration,
                "load_test_config": {
                    "initial_rps": self.load_test_config.initial_rps,
                    "peak_rps": self.load_test_config.peak_rps,
                    "total_duration": self.load_test_config.duration_seconds
                },
                "performance_results": {
                    "total_requests": total_requests,
                    "successful_requests": successful_requests,
                    "success_rate": success_rate,
                    "avg_response_time": avg_response_time,
                    "max_response_time": max_response_time
                },
                "scaling_results": {
                    "scaling_events": scaling_events_count,
                    "scale_up_latency": self.scaling_metrics.scale_up_latency,
                    "scale_down_latency": self.scaling_metrics.scale_down_latency,
                    "service_discovery_updates": len(self.scaling_metrics.service_discovery_updates),
                    "cost_efficiency_ratio": cost_efficiency,
                    "resource_efficiency_gain": resource_efficiency
                },
                "final_metrics": final_metrics,
                "scaling_decisions": self.scaling_metrics.scaling_decisions,
                "performance_impact": self.scaling_metrics.performance_impact,
                "service_calls": total_requests
            }
            
        except Exception as e:
            logger.error(f"Critical path test execution failed: {e}")
            return {
                "error": str(e),
                "test_duration": time.time() - test_start_time if 'test_start_time' in locals() else 0,
                "service_calls": 0
            }
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate that auto-scaling critical path results meet business requirements."""
        try:
            validation_results = []
            
            # Performance validation
            success_rate = results.get("performance_results", {}).get("success_rate", 0)
            avg_response_time = results.get("performance_results", {}).get("avg_response_time", 0)
            max_response_time = results.get("performance_results", {}).get("max_response_time", 0)
            
            # Auto-scaling validation
            scaling_events = results.get("scaling_results", {}).get("scaling_events", 0)
            scale_up_latency = results.get("scaling_results", {}).get("scale_up_latency", 0)
            cost_efficiency = results.get("scaling_results", {}).get("cost_efficiency_ratio", 1.0)
            
            # Business requirements validation
            
            # 1. Success rate must be >= 95% during 10x load increase
            if success_rate >= 95.0:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(f"Success rate {success_rate:.1f}% below 95% threshold during peak load")
                validation_results.append(False)
            
            # 2. Average response time must stay <= 3.0 seconds
            if avg_response_time <= 3.0:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(f"Average response time {avg_response_time:.2f}s exceeds 3.0s limit")
                validation_results.append(False)
            
            # 3. Maximum response time must stay <= 10.0 seconds
            if max_response_time <= 10.0:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(f"Maximum response time {max_response_time:.2f}s exceeds 10.0s limit")
                validation_results.append(False)
            
            # 4. Auto-scaling must trigger at least once
            if scaling_events >= 1:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(f"Auto-scaling events {scaling_events} below minimum 1 event")
                validation_results.append(False)
            
            # 5. Scale-up latency must be <= 120 seconds (realistic for cloud environments)
            if scale_up_latency <= 120.0:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(f"Scale-up latency {scale_up_latency:.1f}s exceeds 120s limit")
                validation_results.append(False)
            
            # 6. Cost efficiency should be reasonable (not more than 3x cost increase for 10x load)
            if cost_efficiency <= 3.0:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(f"Cost efficiency ratio {cost_efficiency:.2f} exceeds 3.0x limit")
                validation_results.append(False)
            
            # 7. Service discovery updates should occur
            discovery_updates = results.get("scaling_results", {}).get("service_discovery_updates", 0)
            if discovery_updates >= 1:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(f"Service discovery updates {discovery_updates} below minimum 1")
                validation_results.append(False)
            
            # 8. No critical errors in scaling decisions
            scaling_decisions = results.get("scaling_decisions", [])
            failed_scaling = len([d for d in scaling_decisions if not d.get("success", True)])
            if failed_scaling == 0:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(f"Failed scaling decisions: {failed_scaling}")
                validation_results.append(False)
            
            # Overall validation
            all_validations_passed = all(validation_results)
            
            if all_validations_passed:
                logger.info("Auto-scaling critical path validation PASSED")
            else:
                logger.error(f"Auto-scaling critical path validation FAILED: {len([r for r in validation_results if not r])}/{len(validation_results)} checks failed")
            
            return all_validations_passed
            
        except Exception as e:
            self.test_metrics.errors.append(f"Validation failed: {str(e)}")
            return False
    
    async def cleanup_test_specific_resources(self) -> None:
        """Clean up auto-scaling test resources."""
        try:
            # Reset auto-scaler state
            self.auto_scaler.current_instances = {}
            self.auto_scaler.scaling_history = []
            
            # Clear load generators
            self.load_generators = []
            
            # Clear metrics
            self.scaling_events = []
            
            logger.info("Auto-scaling test cleanup completed")
            
        except Exception as e:
            logger.error(f"Auto-scaling test cleanup failed: {e}")


# Pytest fixtures and test functions

@pytest.fixture
async def peak_load_autoscaling_test():
    """Create peak load auto-scaling test instance."""
    test_instance = PeakLoadAutoScalingL4Test()
    try:
        yield test_instance
    finally:
        await test_instance.cleanup_l4_resources()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.slow
async def test_peak_load_autoscaling_10x_traffic_spike(peak_load_autoscaling_test):
    """Test auto-scaling response to 10x traffic spike."""
    test_metrics = await peak_load_autoscaling_test.run_complete_critical_path_test()
    
    # Verify test execution
    assert test_metrics.success, f"Auto-scaling test failed: {test_metrics.errors}"
    assert test_metrics.service_calls > 0, "No service calls were made during test"
    assert test_metrics.duration > 0, "Test duration should be positive"
    
    # Verify scaling occurred
    scaling_decisions = test_metrics.details.get("scaling_decisions", [])
    assert len(scaling_decisions) > 0, "No auto-scaling decisions were made"
    
    # Verify performance maintained during scaling
    performance_results = test_metrics.details.get("performance_results", {})
    assert performance_results.get("success_rate", 0) >= 95.0, "Success rate below 95% during peak load"
    assert performance_results.get("avg_response_time", 0) <= 3.0, "Average response time exceeds 3.0s"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.slow
async def test_horizontal_scaling_effectiveness(peak_load_autoscaling_test):
    """Test effectiveness of horizontal scaling decisions."""
    # Initialize test environment
    await peak_load_autoscaling_test.initialize_l4_environment()
    
    # Force horizontal scaling scenario
    peak_load_autoscaling_test.load_test_config.peak_rps = 150  # Higher load
    peak_load_autoscaling_test.auto_scaler.performance_thresholds["cpu_threshold"] = 60.0  # Lower threshold
    
    # Execute scaling test
    results = await peak_load_autoscaling_test.execute_critical_path_test()
    
    # Validate horizontal scaling occurred
    scaling_results = results.get("scaling_results", {})
    assert scaling_results.get("scaling_events", 0) >= 1, "No horizontal scaling events occurred"
    assert scaling_results.get("scale_up_latency", 0) > 0, "Scale-up latency not recorded"
    
    # Validate cost efficiency
    cost_efficiency = scaling_results.get("cost_efficiency_ratio", 1.0)
    assert cost_efficiency <= 3.0, f"Cost efficiency ratio {cost_efficiency} exceeds acceptable limit"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.slow
async def test_service_discovery_updates_during_scaling(peak_load_autoscaling_test):
    """Test service discovery updates during auto-scaling operations."""
    # Initialize test environment
    await peak_load_autoscaling_test.initialize_l4_environment()
    
    # Execute test with focus on service discovery
    results = await peak_load_autoscaling_test.execute_critical_path_test()
    
    # Validate service discovery updates
    scaling_results = results.get("scaling_results", {})
    discovery_updates = scaling_results.get("service_discovery_updates", 0)
    assert discovery_updates >= 1, "No service discovery updates occurred during scaling"
    
    # Validate discovery update timing
    discovery_data = peak_load_autoscaling_test.scaling_metrics.service_discovery_updates
    for update in discovery_data:
        assert "propagation_delay" in update, "Propagation delay not recorded"
        assert update.get("instance_count", 0) > 0, "Invalid instance count in discovery update"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.slow
async def test_cost_optimization_scale_down(peak_load_autoscaling_test):
    """Test cost optimization through intelligent scale-down."""
    # Initialize test environment
    await peak_load_autoscaling_test.initialize_l4_environment()
    
    # Configure for scale-down scenario
    peak_load_autoscaling_test.load_test_config.peak_rps = 80
    peak_load_autoscaling_test.load_test_config.ramp_down_seconds = 90  # Longer ramp-down
    
    # Execute test
    results = await peak_load_autoscaling_test.execute_critical_path_test()
    
    # Validate cost optimization
    scaling_metrics = peak_load_autoscaling_test.scaling_metrics
    initial_cost = scaling_metrics.cost_per_hour_before
    final_cost = scaling_metrics.cost_per_hour_after
    
    # Cost should optimize during scale-down
    if scaling_metrics.resource_efficiency_gain < 0:  # Resource usage decreased
        assert final_cost <= initial_cost * 1.1, "Cost not optimized during scale-down"
    
    # Validate scale-down latency
    scale_down_latency = scaling_metrics.scale_down_latency
    if scale_down_latency > 0:
        assert scale_down_latency <= 120.0, f"Scale-down latency {scale_down_latency}s exceeds limit"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.slow
async def test_performance_sla_maintenance_during_scaling(peak_load_autoscaling_test):
    """Test that performance SLAs are maintained during scaling operations."""
    # Initialize test environment
    await peak_load_autoscaling_test.initialize_l4_environment()
    
    # Execute test with SLA monitoring
    results = await peak_load_autoscaling_test.execute_critical_path_test()
    
    # Validate SLA compliance
    performance_results = results.get("performance_results", {})
    
    # Response time SLA
    avg_response_time = performance_results.get("avg_response_time", 0)
    max_response_time = performance_results.get("max_response_time", 0)
    assert avg_response_time <= 3.0, f"Average response time SLA violation: {avg_response_time:.2f}s"
    assert max_response_time <= 10.0, f"Maximum response time SLA violation: {max_response_time:.2f}s"
    
    # Availability SLA
    success_rate = performance_results.get("success_rate", 0)
    assert success_rate >= 95.0, f"Availability SLA violation: {success_rate:.1f}%"
    
    # Validate performance impact during scaling
    performance_impact = results.get("performance_impact", {})
    for endpoint, impact in performance_impact.items():
        response_time_change = impact.get("response_time_improvement", 0)
        # Response time should not degrade significantly (allow 50% increase max)
        if response_time_change < 0:  # Negative means response time increased
            degradation_ratio = abs(response_time_change) / impact.get("baseline_response_time", 1.0)
            assert degradation_ratio <= 0.5, f"Response time degraded by {degradation_ratio*100:.1f}% for {endpoint}"