"""System resource monitoring utilities."""

import psutil
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime


class SystemResourceMonitor:
    """System resource monitoring class."""
    
    def __init__(self, collection_interval: int = 60):
        """Initialize system resource monitor."""
        self.collection_interval = collection_interval
        self.is_monitoring = False
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information."""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free
        }
    
    def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        """Get disk usage information."""
        disk = psutil.disk_usage(path)
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": (disk.used / disk.total) * 100
        }
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics."""
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
    
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all system metrics."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {
                "usage_percent": self.get_cpu_usage(),
                "count": psutil.cpu_count()
            },
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "network": self.get_network_stats(),
            "process_count": len(psutil.pids())
        }
    
    async def start_monitoring(self):
        """Start continuous monitoring."""
        self.is_monitoring = True
        while self.is_monitoring:
            metrics = await self.collect_all_metrics()
            # In a real implementation, you would send these metrics to a monitoring system
            await asyncio.sleep(self.collection_interval)
    
    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.is_monitoring = False


class HealthMonitor:
    """System health monitoring class."""
    
    def __init__(self):
        """Initialize health monitor."""
        self.resource_monitor = SystemResourceMonitor()
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        metrics = await self.resource_monitor.collect_all_metrics()
        
        # Determine health status based on thresholds
        health_status = "healthy"
        issues = []
        
        if metrics["cpu"]["usage_percent"] > 90:
            health_status = "warning"
            issues.append("High CPU usage")
        
        if metrics["memory"]["percent"] > 85:
            health_status = "warning"  
            issues.append("High memory usage")
        
        if metrics["disk"]["percent"] > 90:
            health_status = "critical"
            issues.append("Low disk space")
        
        return {
            "status": health_status,
            "issues": issues,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }