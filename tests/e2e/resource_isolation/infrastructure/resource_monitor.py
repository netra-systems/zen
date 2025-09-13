"""

Resource Monitor for Agent Isolation Testing



Monitors resource usage across multiple tenant agents.

"""



import asyncio

import logging

import os

import statistics

import time

from collections import defaultdict

from typing import Dict, List, Optional



import psutil



from tests.e2e.resource_isolation.infrastructure.data_models import (

    RESOURCE_LIMITS,

    ResourceMetrics,

    ResourceViolation,

)



logger = logging.getLogger(__name__)



class ResourceMonitor:

    """Monitor resource usage across multiple tenant agents."""

    

    def __init__(self, monitoring_interval: float = 1.0):

        self.monitoring_interval = monitoring_interval

        self.tenant_processes: Dict[str, psutil.Process] = {}

        self.metrics_history: Dict[str, List[ResourceMetrics]] = defaultdict(list)

        self.violations: List[ResourceViolation] = []

        self.violation_callbacks: List[callable] = []

        self.monitoring_task: Optional[asyncio.Task] = None

        self.monitoring_active = False

        self.lock = asyncio.Lock()

        

    def register_agent_process(self, tenant_id: str, process: psutil.Process):

        """Register an agent process for monitoring."""

        self.tenant_processes[tenant_id] = process

        if tenant_id not in self.metrics_history:

            self.metrics_history[tenant_id] = []

        logger.info(f"Registered process for tenant {tenant_id}: PID {process.pid}")

        

    def unregister_agent_process(self, tenant_id: str):

        """Unregister an agent process."""

        if tenant_id in self.tenant_processes:

            del self.tenant_processes[tenant_id]

            logger.info(f"Unregistered process for tenant {tenant_id}")



    async def start_monitoring(self):

        """Start resource monitoring."""

        if self.monitoring_active:

            return

            

        self.monitoring_active = True

        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("Resource monitoring started")



    async def stop_monitoring(self):

        """Stop resource monitoring."""

        self.monitoring_active = False

        if self.monitoring_task:

            self.monitoring_task.cancel()

            try:

                await self.monitoring_task

            except asyncio.CancelledError:

                pass

        logger.info("Resource monitoring stopped")



    async def _monitoring_loop(self):

        """Main monitoring loop."""

        try:

            while self.monitoring_active:

                current_time = time.time()

                

                async with self.lock:

                    # Collect system-wide metrics

                    system_metrics = self._collect_system_metrics()

                    

                    # Collect per-process metrics

                    for tenant_id, process in list(self.tenant_processes.items()):

                        try:

                            if process.is_running():

                                metrics = self._collect_process_metrics(tenant_id, process, current_time)

                                self.metrics_history[tenant_id].append(metrics)

                                

                                # Limit history size

                                if len(self.metrics_history[tenant_id]) > 1000:

                                    self.metrics_history[tenant_id] = self.metrics_history[tenant_id][-500:]

                                

                                # Check for violations

                                await self._check_resource_violations(metrics)

                            else:

                                logger.warning(f"Process for tenant {tenant_id} is no longer running")

                                del self.tenant_processes[tenant_id]

                                

                        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:

                            logger.warning(f"Error monitoring tenant {tenant_id}: {e}")

                            if tenant_id in self.tenant_processes:

                                del self.tenant_processes[tenant_id]

                

                await asyncio.sleep(self.monitoring_interval)

                

        except asyncio.CancelledError:

            logger.info("Monitoring loop cancelled")

        except Exception as e:

            logger.error(f"Monitoring loop error: {e}")



    def _collect_system_metrics(self) -> Dict[str, float]:

        """Collect system-wide resource metrics."""

        return {

            "cpu_percent": psutil.cpu_percent(),

            "memory_percent": psutil.virtual_memory().percent,

            "memory_available_mb": psutil.virtual_memory().available / 1024 / 1024,

            "disk_usage_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,

            "load_avg": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0.0

        }



    def _collect_process_metrics(self, tenant_id: str, process: psutil.Process, timestamp: float) -> ResourceMetrics:

        """Collect metrics for a specific process."""

        try:

            memory_info = process.memory_info()

            

            return ResourceMetrics(

                tenant_id=tenant_id,

                timestamp=timestamp,

                cpu_percent=process.cpu_percent(),

                memory_mb=memory_info.rss / 1024 / 1024,

                memory_percent=process.memory_percent(),

                threads=process.num_threads(),

                handles=process.num_handles() if hasattr(process, 'num_handles') else 0,

                io_reads=process.io_counters().read_count if hasattr(process, 'io_counters') else 0,

                io_writes=process.io_counters().write_count if hasattr(process, 'io_counters') else 0

            )

        except (psutil.NoSuchProcess, psutil.AccessDenied):

            # Return zero metrics if process is gone

            return ResourceMetrics(

                tenant_id=tenant_id,

                timestamp=timestamp,

                cpu_percent=0.0,

                memory_mb=0.0,

                memory_percent=0.0,

                threads=0

            )



    async def _check_resource_violations(self, metrics: ResourceMetrics):

        """Check for resource usage violations."""

        violations = []

        

        # CPU violation check

        if metrics.cpu_percent > RESOURCE_LIMITS["per_agent_cpu_max"]:

            violation = ResourceViolation(

                tenant_id=metrics.tenant_id,

                violation_type="cpu",

                severity="critical" if metrics.cpu_percent > 50 else "warning",

                measured_value=metrics.cpu_percent,

                threshold_value=RESOURCE_LIMITS["per_agent_cpu_max"],

                timestamp=metrics.timestamp

            )

            violations.append(violation)

        

        # Memory violation check

        if metrics.memory_mb > RESOURCE_LIMITS["per_agent_memory_mb"]:

            violation = ResourceViolation(

                tenant_id=metrics.tenant_id,

                violation_type="memory",

                severity="critical" if metrics.memory_mb > 1024 else "warning",

                measured_value=metrics.memory_mb,

                threshold_value=RESOURCE_LIMITS["per_agent_memory_mb"],

                timestamp=metrics.timestamp

            )

            violations.append(violation)

        

        # Add violations and trigger callbacks

        for violation in violations:

            self.violations.append(violation)

            await self._trigger_violation_callbacks(violation)



    async def _trigger_violation_callbacks(self, violation: ResourceViolation):

        """Trigger registered violation callbacks."""

        for callback in self.violation_callbacks:

            try:

                await callback(violation)

            except Exception as e:

                logger.error(f"Violation callback error: {e}")



    def register_violation_callback(self, callback: callable):

        """Register a callback for resource violations."""

        self.violation_callbacks.append(callback)



    def get_tenant_metrics_summary(self, tenant_id: str, window_seconds: int = 60) -> Dict[str, float]:

        """Get summary metrics for a tenant over a time window."""

        if tenant_id not in self.metrics_history:

            return {}

        

        current_time = time.time()

        cutoff_time = current_time - window_seconds

        

        recent_metrics = [

            m for m in self.metrics_history[tenant_id] 

            if m.timestamp >= cutoff_time

        ]

        

        if not recent_metrics:

            return {}

        

        cpu_values = [m.cpu_percent for m in recent_metrics]

        memory_values = [m.memory_mb for m in recent_metrics]

        

        return {

            "avg_cpu_percent": statistics.mean(cpu_values),

            "max_cpu_percent": max(cpu_values),

            "avg_memory_mb": statistics.mean(memory_values),

            "max_memory_mb": max(memory_values),

            "sample_count": len(recent_metrics),

            "violation_count": len([v for v in self.violations if v.tenant_id == tenant_id and v.timestamp >= cutoff_time])

        }



    def detect_noisy_neighbors(self, threshold_factor: float = 2.0) -> List[str]:

        """Detect tenants with abnormally high resource usage."""

        noisy_tenants = []

        

        # Calculate average resource usage across all tenants

        all_cpu_values = []

        all_memory_values = []

        

        for tenant_metrics in self.metrics_history.values():

            if tenant_metrics:

                latest_metric = tenant_metrics[-1]

                all_cpu_values.append(latest_metric.cpu_percent)

                all_memory_values.append(latest_metric.memory_mb)

        

        if not all_cpu_values:

            return noisy_tenants

        

        avg_cpu = statistics.mean(all_cpu_values)

        avg_memory = statistics.mean(all_memory_values)

        

        # Find tenants exceeding threshold

        for tenant_id, metrics in self.metrics_history.items():

            if metrics:

                latest = metrics[-1]

                if (latest.cpu_percent > avg_cpu * threshold_factor or 

                    latest.memory_mb > avg_memory * threshold_factor):

                    noisy_tenants.append(tenant_id)

        

        return noisy_tenants

