"""

Performance Isolation Validator for Agent Testing



Validates performance isolation between tenants.

"""



import asyncio

import logging

import time

from typing import Dict, List



from tests.e2e.resource_isolation.infrastructure.data_models import (

    PerformanceImpactReport,

    ResourceMetrics,

)



logger = logging.getLogger(__name__)



class PerformanceIsolationValidator:

    """Validate performance isolation between tenants."""

    

    def __init__(self, monitor):

        self.monitor = monitor

    

    async def establish_performance_baseline(self, tenant_ids: List[str], duration: float = 30.0) -> Dict[str, ResourceMetrics]:

        """Establish performance baseline for normal load."""

        await asyncio.sleep(duration)

        baseline = {}

        

        for tenant_id in tenant_ids:

            summary = self.monitor.get_tenant_metrics_summary(tenant_id, window_seconds=duration)

            if summary:

                baseline[tenant_id] = ResourceMetrics(

                    tenant_id=tenant_id,

                    timestamp=time.time(),

                    cpu_percent=summary["avg_cpu_percent"],

                    memory_mb=summary["avg_memory_mb"],

                    memory_percent=0.0,

                    threads=0

                )

        

        return baseline



    async def measure_cross_tenant_impact(self, baseline: Dict[str, ResourceMetrics], 

                                        stressed_tenant: str, duration: float = 60.0) -> PerformanceImpactReport:

        """Measure performance impact when one tenant is under stress."""

        logger.info(f"Measuring cross-tenant impact with {stressed_tenant} under stress for {duration}s")

        

        # Wait for stress test duration

        await asyncio.sleep(duration)

        

        # Collect stressed metrics

        stressed_metrics = {}

        impact_percentages = {}

        

        for tenant_id, baseline_metrics in baseline.items():

            if tenant_id == stressed_tenant:

                continue  # Skip the stressed tenant itself

                

            current_summary = self.monitor.get_tenant_metrics_summary(tenant_id, window_seconds=30)

            if current_summary:

                stressed_metrics[tenant_id] = ResourceMetrics(

                    tenant_id=tenant_id,

                    timestamp=time.time(),

                    cpu_percent=current_summary["avg_cpu_percent"],

                    memory_mb=current_summary["avg_memory_mb"],

                    memory_percent=0.0,

                    threads=0

                )

                

                # Calculate performance impact

                cpu_impact = ((current_summary["avg_cpu_percent"] - baseline_metrics.cpu_percent) / 

                             baseline_metrics.cpu_percent * 100) if baseline_metrics.cpu_percent > 0 else 0

                

                memory_impact = ((current_summary["avg_memory_mb"] - baseline_metrics.memory_mb) / 

                               baseline_metrics.memory_mb * 100) if baseline_metrics.memory_mb > 0 else 0

                

                # Use the higher impact as the overall impact

                impact_percentages[tenant_id] = max(abs(cpu_impact), abs(memory_impact))

        

        return PerformanceImpactReport(

            baseline_metrics=baseline,

            stressed_metrics=stressed_metrics,

            impact_percentages=impact_percentages

        )

