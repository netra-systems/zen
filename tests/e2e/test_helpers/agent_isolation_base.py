"""

Agent Isolation Test Base Utilities



This module provides common utilities for agent resource isolation testing,

extracted from the original test_agent_resource_isolation.py file.



Business Value Justification (BVJ):

- Segment: Enterprise (multi-tenant isolation requirements)

- Business Goal: Provide reusable testing infrastructure for resource isolation

- Value Impact: Enables thorough testing of $500K+ enterprise contracts

- Revenue Impact: Essential for maintaining enterprise trust and SLA compliance

"""



import asyncio

import json

import logging

import os

import time

import uuid

from collections import defaultdict

from dataclasses import dataclass

from typing import Any, Dict, List, Optional, Union



import psutil

import warnings

with warnings.catch_warnings():

    warnings.simplefilter("ignore", DeprecationWarning)

    import websockets

    try:

        from websockets import ServerConnection as WebSocketServerProtocol

    except ImportError:

        # Fallback for older versions

        from websockets import ServerConnection as WebSocketServerProtocol



logger = logging.getLogger(__name__)



@dataclass

class IsolationTestMetrics:

    """Metrics for isolation testing."""

    tenant_id: str

    test_start_time: float

    baseline_cpu: float = 0.0

    baseline_memory_mb: float = 0.0

    peak_cpu: float = 0.0

    peak_memory_mb: float = 0.0

    avg_response_time_ms: float = 0.0

    total_requests: int = 0

    failed_requests: int = 0



@dataclass

class IsolationViolation:

    """Represents an isolation boundary violation."""

    source_tenant: str

    affected_tenant: str

    violation_type: str  # 'performance', 'resource', 'data'

    severity: str       # 'low', 'medium', 'high', 'critical'

    impact_percentage: float

    timestamp: float

    details: Dict[str, Any]



class AgentIsolationBase:

    """Base class for agent isolation testing utilities."""

    

    def __init__(self, monitoring_interval: float = 1.0):

        self.monitoring_interval = monitoring_interval

        self.test_metrics: Dict[str, IsolationTestMetrics] = {}

        self.violations: List[IsolationViolation] = []

        

    def create_test_agent_config(self, tenant_id: str, resource_tier: str = "medium") -> Dict[str, Any]:

        """Create configuration for a test agent."""

        resource_configs = {

            "light": {"cpu_quota": 10.0, "memory_mb": 256, "concurrent_requests": 5},

            "medium": {"cpu_quota": 25.0, "memory_mb": 512, "concurrent_requests": 10},

            "heavy": {"cpu_quota": 50.0, "memory_mb": 1024, "concurrent_requests": 20}

        }

        

        config = resource_configs.get(resource_tier, resource_configs["medium"])

        

        return {

            "tenant_id": tenant_id,

            "user_id": f"user_{tenant_id}_{uuid.uuid4().hex[:8]}",

            "resource_tier": resource_tier,

            "resource_limits": config,

            "isolation_settings": {

                "enable_resource_monitoring": True,

                "enable_performance_tracking": True,

                "violation_detection": True

            }

        }

    

    async def establish_baseline_metrics(self, tenant_id: str, duration: float = 5.0) -> IsolationTestMetrics:

        """Establish baseline performance metrics for a tenant."""

        logger.info(f"Establishing baseline for tenant {tenant_id} over {duration}s")

        

        start_time = time.time()

        cpu_samples = []

        memory_samples = []

        

        try:

            process = psutil.Process()

            

            # For test efficiency, limit samples and use larger intervals

            max_samples = min(10, int(duration / self.monitoring_interval))

            effective_interval = duration / max_samples if max_samples > 0 else self.monitoring_interval

            

            # Collect baseline samples efficiently

            for i in range(max_samples):

                cpu_samples.append(process.cpu_percent(interval=None))  # Non-blocking

                memory_samples.append(process.memory_info().rss / 1024 / 1024)

                

                # Only sleep if not the last sample

                if i < max_samples - 1:

                    await asyncio.sleep(effective_interval)

            

            baseline_metrics = IsolationTestMetrics(

                tenant_id=tenant_id,

                test_start_time=start_time,

                baseline_cpu=sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0,

                baseline_memory_mb=sum(memory_samples) / len(memory_samples) if memory_samples else 0.0

            )

            

            self.test_metrics[tenant_id] = baseline_metrics

            logger.info(f"Baseline established: CPU {baseline_metrics.baseline_cpu:.2f}%, Memory {baseline_metrics.baseline_memory_mb:.2f}MB")

            

            return baseline_metrics

            

        except Exception as e:

            logger.error(f"Failed to establish baseline for {tenant_id}: {e}")

            raise



    def validate_resource_limits(self, tenant_id: str, cpu_limit: float, memory_limit_mb: float) -> Dict[str, bool]:

        """Validate that a tenant stays within resource limits."""

        metrics = self.test_metrics.get(tenant_id)

        if not metrics:

            return {"valid": False, "reason": "No metrics available"}

        

        cpu_violation = metrics.peak_cpu > cpu_limit

        memory_violation = metrics.peak_memory_mb > memory_limit_mb

        

        validation_result = {

            "cpu_valid": not cpu_violation,

            "memory_valid": not memory_violation,

            "overall_valid": not (cpu_violation or memory_violation),

            "cpu_usage": metrics.peak_cpu,

            "memory_usage": metrics.peak_memory_mb,

            "cpu_limit": cpu_limit,

            "memory_limit": memory_limit_mb

        }

        

        if cpu_violation or memory_violation:

            logger.warning(f"Resource limit violation for {tenant_id}: {validation_result}")

        

        return validation_result



    def detect_cross_tenant_impact(self, source_tenant: str, target_tenants: List[str], 

                                  threshold_percentage: float = 10.0) -> List[IsolationViolation]:

        """Detect if source tenant is impacting other tenants."""

        violations = []

        source_metrics = self.test_metrics.get(source_tenant)

        

        if not source_metrics:

            return violations

        

        for target_tenant in target_tenants:

            target_metrics = self.test_metrics.get(target_tenant)

            if not target_metrics:

                continue

            

            # Calculate performance degradation

            if target_metrics.baseline_cpu > 0:

                cpu_degradation = ((target_metrics.peak_cpu - target_metrics.baseline_cpu) / 

                                 target_metrics.baseline_cpu) * 100

            else:

                cpu_degradation = 0

            

            if target_metrics.baseline_memory_mb > 0:

                memory_degradation = ((target_metrics.peak_memory_mb - target_metrics.baseline_memory_mb) / 

                                    target_metrics.baseline_memory_mb) * 100

            else:

                memory_degradation = 0

            

            max_degradation = max(cpu_degradation, memory_degradation)

            

            if max_degradation > threshold_percentage:

                violation = IsolationViolation(

                    source_tenant=source_tenant,

                    affected_tenant=target_tenant,

                    violation_type="performance",

                    severity=self._calculate_severity(max_degradation),

                    impact_percentage=max_degradation,

                    timestamp=time.time(),

                    details={

                        "cpu_degradation": cpu_degradation,

                        "memory_degradation": memory_degradation,

                        "threshold": threshold_percentage

                    }

                )

                violations.append(violation)

                self.violations.append(violation)

        

        return violations



    def _calculate_severity(self, impact_percentage: float) -> str:

        """Calculate violation severity based on impact percentage."""

        if impact_percentage >= 50:

            return "critical"

        elif impact_percentage >= 25:

            return "high"

        elif impact_percentage >= 15:

            return "medium"

        else:

            return "low"



    async def simulate_workload_burst(self, connection: WebSocketServerProtocol, 

                                    tenant_id: str, burst_size: int = 50, 

                                    burst_delay: float = 0.01) -> Dict[str, Any]:

        """Simulate a workload burst for testing isolation."""

        start_time = time.time()

        messages_sent = 0

        errors = 0

        

        try:

            for i in range(burst_size):

                message = {

                    "type": "burst_message",

                    "tenant_id": tenant_id,

                    "burst_id": f"{tenant_id}_burst_{int(start_time)}",

                    "message_number": i + 1,

                    "payload": "x" * 1000,  # 1KB payload

                    "timestamp": time.time()

                }

                

                try:

                    await connection.send(json.dumps(message))

                    messages_sent += 1

                    await asyncio.sleep(burst_delay)

                except Exception as e:

                    errors += 1

                    logger.warning(f"Error sending burst message {i}: {e}")

        

        except Exception as e:

            logger.error(f"Burst simulation failed for {tenant_id}: {e}")

        

        duration = time.time() - start_time

        

        return {

            "tenant_id": tenant_id,

            "burst_size": burst_size,

            "messages_sent": messages_sent,

            "errors": errors,

            "duration": duration,

            "message_rate": messages_sent / duration if duration > 0 else 0,

            "success_rate": (messages_sent / burst_size) * 100 if burst_size > 0 else 0

        }



    def generate_isolation_report(self) -> Dict[str, Any]:

        """Generate comprehensive isolation test report."""

        total_tenants = len(self.test_metrics)

        total_violations = len(self.violations)

        

        # Categorize violations by severity

        violation_by_severity = defaultdict(int)

        for violation in self.violations:

            violation_by_severity[violation.severity] += 1

        

        # Calculate average resource usage

        avg_cpu = sum(metrics.peak_cpu for metrics in self.test_metrics.values()) / total_tenants if total_tenants > 0 else 0

        avg_memory = sum(metrics.peak_memory_mb for metrics in self.test_metrics.values()) / total_tenants if total_tenants > 0 else 0

        

        # Find most impactful violations

        high_impact_violations = [v for v in self.violations if v.impact_percentage > 20]

        

        report = {

            "summary": {

                "total_tenants_tested": total_tenants,

                "total_violations": total_violations,

                "isolation_score": max(0, 100 - (total_violations / total_tenants * 10)) if total_tenants > 0 else 100,

                "test_status": "PASS" if total_violations == 0 else "FAIL"

            },

            "resource_usage": {

                "average_cpu_percent": avg_cpu,

                "average_memory_mb": avg_memory,

                "peak_cpu_usage": max((m.peak_cpu for m in self.test_metrics.values()), default=0),

                "peak_memory_usage": max((m.peak_memory_mb for m in self.test_metrics.values()), default=0)

            },

            "violations": {

                "by_severity": dict(violation_by_severity),

                "high_impact_count": len(high_impact_violations),

                "detailed_violations": [

                    {

                        "source": v.source_tenant,

                        "target": v.affected_tenant,

                        "type": v.violation_type,

                        "severity": v.severity,

                        "impact": v.impact_percentage

                    }

                    for v in high_impact_violations[:10]  # Top 10 violations

                ]

            },

            "performance_metrics": {

                tenant_id: {

                    "baseline_cpu": metrics.baseline_cpu,

                    "peak_cpu": metrics.peak_cpu,

                    "baseline_memory": metrics.baseline_memory_mb,

                    "peak_memory": metrics.peak_memory_mb,

                    "requests_processed": metrics.total_requests,

                    "failure_rate": (metrics.failed_requests / metrics.total_requests * 100) if metrics.total_requests > 0 else 0

                }

                for tenant_id, metrics in self.test_metrics.items()

            }

        }

        

        return report



def assert_isolation_quality(isolation_base: AgentIsolationBase, max_violations: int = 0, 

                           max_impact_percentage: float = 10.0):

    """Assert that isolation quality meets requirements."""

    report = isolation_base.generate_isolation_report()

    

    # Check violation count

    total_violations = report["summary"]["total_violations"]

    assert total_violations <= max_violations, f"Too many isolation violations: {total_violations} > {max_violations}"

    

    # Check impact severity

    high_impact_violations = [v for v in isolation_base.violations if v.impact_percentage > max_impact_percentage]

    assert len(high_impact_violations) == 0, f"High impact violations detected: {len(high_impact_violations)}"

    

    # Check isolation score

    isolation_score = report["summary"]["isolation_score"]

    assert isolation_score >= 90, f"Isolation score too low: {isolation_score} < 90"

    

    logger.info(f"Isolation quality assertion passed: {total_violations} violations, score {isolation_score}")



async def simulate_workload_burst(agent, burst_type: str = "cpu", duration: float = 5.0):

    """Simulate a workload burst for testing."""

    start_time = time.time()

    

    if burst_type == "cpu":

        # CPU intensive workload

        while time.time() - start_time < duration:

            _ = [i ** 2 for i in range(10000)]

            await asyncio.sleep(0.01)

    elif burst_type == "memory":

        # Memory intensive workload

        data = []

        while time.time() - start_time < duration:

            data.append([0] * 10000)

            await asyncio.sleep(0.1)

    elif burst_type == "io":

        # I/O intensive workload

        while time.time() - start_time < duration:

            _ = str(uuid.uuid4()) * 1000

            await asyncio.sleep(0.05)

    else:

        # Default mixed workload

        while time.time() - start_time < duration:

            _ = [i ** 2 for i in range(5000)]

            _ = str(uuid.uuid4()) * 100

            await asyncio.sleep(0.05)



def create_test_workload_message(tenant_id: str, message_type: str = "normal", 

                               payload_size: int = 100) -> Dict[str, Any]:

    """Create a standardized test workload message."""

    message_types = {

        "normal": {"complexity": "low", "resource_usage": "minimal"},

        "heavy": {"complexity": "high", "resource_usage": "intensive"},

        "burst": {"complexity": "medium", "resource_usage": "burst"},

        "leak": {"complexity": "medium", "resource_usage": "leak_simulation"}

    }

    

    config = message_types.get(message_type, message_types["normal"])

    

    return {

        "type": f"test_{message_type}",

        "tenant_id": tenant_id,

        "message_id": f"{tenant_id}_{message_type}_{uuid.uuid4().hex[:8]}",

        "payload": "x" * payload_size,

        "timestamp": time.time(),

        "test_config": config,

        "isolation_test": True

    }

