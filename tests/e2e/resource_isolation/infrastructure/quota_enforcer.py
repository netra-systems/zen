"""
Quota Enforcer for Agent Isolation Testing

Enforces resource quotas for tenant agents.
"""

import time
import logging
import psutil

from .data_models import ResourceViolation

logger = logging.getLogger(__name__)

class QuotaEnforcer:
    """Enforce resource quotas for tenant agents."""
    
    def __init__(self, monitor):
        self.monitor = monitor
    
    async def enforce_cpu_quota(self, tenant_id: str, cpu_quota_percent: float):
        """Enforce CPU quota for a tenant (simulation)."""
        if tenant_id not in self.monitor.tenant_processes:
            return False
            
        process = self.monitor.tenant_processes[tenant_id]
        
        try:
            # In a real implementation, this would use cgroups or similar
            # For testing, we simulate quota enforcement by monitoring
            current_cpu = process.cpu_percent()
            
            if current_cpu > cpu_quota_percent:
                logger.warning(
                    f"CPU quota violation for {tenant_id}: "
                    f"{current_cpu:.1f}% > {cpu_quota_percent:.1f}%"
                )
                
                # Simulate quota enforcement (in reality, would throttle the process)
                # For testing purposes, we just record the violation
                violation = ResourceViolation(
                    tenant_id=tenant_id,
                    violation_type="cpu_quota",
                    severity="critical",
                    measured_value=current_cpu,
                    threshold_value=cpu_quota_percent,
                    timestamp=time.time()
                )
                
                self.monitor.violations.append(violation)
                return False
                
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    async def enforce_memory_quota(self, tenant_id: str, memory_quota_mb: float):
        """Enforce memory quota for a tenant (simulation)."""
        if tenant_id not in self.monitor.tenant_processes:
            return False
            
        process = self.monitor.tenant_processes[tenant_id]
        
        try:
            current_memory = process.memory_info().rss / 1024 / 1024
            
            if current_memory > memory_quota_mb:
                logger.warning(
                    f"Memory quota violation for {tenant_id}: "
                    f"{current_memory:.1f}MB > {memory_quota_mb:.1f}MB"
                )
                
                violation = ResourceViolation(
                    tenant_id=tenant_id,
                    violation_type="memory_quota",
                    severity="critical",
                    measured_value=current_memory,
                    threshold_value=memory_quota_mb,
                    timestamp=time.time()
                )
                
                self.monitor.violations.append(violation)
                return False
                
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False