"""

Resource Leak Detector for Agent Isolation Testing



Detects resource leaks in agent processes.

"""



import asyncio

import logging

import time

from collections import defaultdict

from typing import Dict, List



from tests.e2e.resource_isolation.infrastructure.data_models import ResourceMetrics



logger = logging.getLogger(__name__)



class ResourceLeakDetector:

    """Detect resource leaks in agent processes."""

    

    def __init__(self, monitor):

        self.monitor = monitor

        self.baseline_metrics: Dict[str, ResourceMetrics] = {}

    

    async def establish_baseline(self, stabilization_time: float = 30.0):

        """Establish baseline resource usage after stabilization."""

        logger.info(f"Establishing baseline over {stabilization_time}s...")

        await asyncio.sleep(stabilization_time)

        

        for tenant_id in self.monitor.tenant_processes.keys():

            summary = self.monitor.get_tenant_metrics_summary(tenant_id, window_seconds=10)

            if summary:

                self.baseline_metrics[tenant_id] = ResourceMetrics(

                    tenant_id=tenant_id,

                    timestamp=time.time(),

                    cpu_percent=summary["avg_cpu_percent"],

                    memory_mb=summary["avg_memory_mb"],

                    memory_percent=0.0,  # Not tracked in summary

                    threads=0  # Not tracked in summary

                )

        

        logger.info(f"Baseline established for {len(self.baseline_metrics)} tenants")



    def detect_memory_leaks(self, growth_threshold_mb: float = 50.0, 

                           growth_threshold_percent: float = 25.0) -> List[str]:

        """Detect potential memory leaks."""

        leaking_tenants = []

        

        for tenant_id, baseline in self.baseline_metrics.items():

            current_summary = self.monitor.get_tenant_metrics_summary(tenant_id, window_seconds=10)

            if not current_summary:

                continue

            

            current_memory = current_summary["avg_memory_mb"]

            memory_growth = current_memory - baseline.memory_mb

            growth_percentage = (memory_growth / baseline.memory_mb) * 100 if baseline.memory_mb > 0 else 0

            

            if (memory_growth > growth_threshold_mb and 

                growth_percentage > growth_threshold_percent):

                logger.warning(

                    f"Memory leak detected for {tenant_id}: "

                    f"{memory_growth:.1f}MB growth ({growth_percentage:.1f}%)"

                )

                leaking_tenants.append(tenant_id)

        

        return leaking_tenants



    def detect_all_leaks(self, cpu_threshold: float = 10.0, 

                        memory_threshold_mb: float = 50.0,

                        thread_threshold: int = 5) -> Dict[str, List[str]]:

        """Detect various types of resource leaks."""

        leaks = {

            "memory": self.detect_memory_leaks(memory_threshold_mb),

            "cpu": [],

            "threads": []

        }

        

        # CPU leak detection (sustained high usage)

        for tenant_id, baseline in self.baseline_metrics.items():

            current_summary = self.monitor.get_tenant_metrics_summary(tenant_id, window_seconds=30)

            if current_summary and current_summary["avg_cpu_percent"] > baseline.cpu_percent + cpu_threshold:

                leaks["cpu"].append(tenant_id)

        

        return leaks

