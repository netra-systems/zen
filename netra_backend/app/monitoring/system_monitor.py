"""
System monitoring and performance management.
Central orchestrator for system-wide monitoring capabilities.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, UTC
import asyncio
import psutil
import time

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SystemPerformanceMonitor:
    """Monitors system performance metrics and resource utilization."""
    
    def __init__(self):
        self._metrics_history: List[Dict[str, Any]] = []
        self._monitoring_active = False
        self._monitoring_interval = 30  # seconds
        logger.debug("Initialized SystemPerformanceMonitor")
    
    async def start_monitoring(self) -> None:
        """Start system performance monitoring."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        logger.info("Started system performance monitoring")
        
        # Start background monitoring task
        asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop system performance monitoring."""
        self._monitoring_active = False
        logger.info("Stopped system performance monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                metrics = await self._collect_system_metrics()
                self._metrics_history.append(metrics)
                
                # Keep only last 1440 entries (24 hours at 1 minute intervals)
                if len(self._metrics_history) > 1440:
                    self._metrics_history = self._metrics_history[-1440:]
                
                await asyncio.sleep(self._monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self._monitoring_interval)
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics (basic)
            net_io = psutil.net_io_counters()
            
            return {
                "timestamp": datetime.now(UTC),
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "memory_total_gb": memory.total / (1024**3),
                "memory_used_gb": memory.used / (1024**3),
                "memory_available_gb": memory.available / (1024**3),
                "memory_percent": memory.percent,
                "disk_total_gb": disk.total / (1024**3),
                "disk_used_gb": disk.used / (1024**3),
                "disk_free_gb": disk.free / (1024**3),
                "disk_percent": (disk.used / disk.total) * 100,
                "network_bytes_sent": net_io.bytes_sent,
                "network_bytes_recv": net_io.bytes_recv,
                "network_packets_sent": net_io.packets_sent,
                "network_packets_recv": net_io.packets_recv
            }
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {
                "timestamp": datetime.now(UTC),
                "error": str(e)
            }
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        return await self._collect_system_metrics()
    
    async def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history for specified time period."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        return [
            m for m in self._metrics_history
            if m.get("timestamp", datetime.min) > cutoff_time
        ]
    
    async def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for specified time period."""
        metrics_history = await self.get_metrics_history(hours)
        
        if not metrics_history:
            return {
                "summary": "No metrics available",
                "hours": hours,
                "samples": 0
            }
        
        # Calculate averages
        cpu_values = [m.get("cpu_percent", 0) for m in metrics_history if "cpu_percent" in m]
        memory_values = [m.get("memory_percent", 0) for m in metrics_history if "memory_percent" in m]
        disk_values = [m.get("disk_percent", 0) for m in metrics_history if "disk_percent" in m]
        
        return {
            "hours": hours,
            "samples": len(metrics_history),
            "avg_cpu_percent": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "max_cpu_percent": max(cpu_values) if cpu_values else 0,
            "avg_memory_percent": sum(memory_values) / len(memory_values) if memory_values else 0,
            "max_memory_percent": max(memory_values) if memory_values else 0,
            "avg_disk_percent": sum(disk_values) / len(disk_values) if disk_values else 0,
            "max_disk_percent": max(disk_values) if disk_values else 0,
            "timestamp": datetime.now(UTC)
        }


class MonitoringManager:
    """Central monitoring manager orchestrating all monitoring components."""
    
    def __init__(self):
        self.performance_monitor = SystemPerformanceMonitor()
        self._initialized = False
        logger.debug("Initialized MonitoringManager")
    
    async def initialize(self) -> None:
        """Initialize all monitoring components."""
        if self._initialized:
            return
        
        await self.performance_monitor.start_monitoring()
        self._initialized = True
        logger.info("MonitoringManager initialized")
    
    async def shutdown(self) -> None:
        """Shutdown all monitoring components."""
        await self.performance_monitor.stop_monitoring()
        self._initialized = False
        logger.info("MonitoringManager shut down")
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        current_metrics = await self.performance_monitor.get_current_metrics()
        
        # Determine health status based on metrics
        health_status = self._calculate_health_status(current_metrics)
        
        return {
            "status": health_status["status"],
            "score": health_status["score"],
            "issues": health_status["issues"],
            "current_metrics": current_metrics,
            "timestamp": datetime.now(UTC)
        }
    
    def _calculate_health_status(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate system health status from metrics."""
        issues = []
        score = 100
        
        # Check CPU usage
        cpu_percent = metrics.get("cpu_percent", 0)
        if cpu_percent > 90:
            issues.append(f"Critical CPU usage: {cpu_percent:.1f}%")
            score -= 30
        elif cpu_percent > 80:
            issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            score -= 15
        
        # Check memory usage
        memory_percent = metrics.get("memory_percent", 0)
        if memory_percent > 95:
            issues.append(f"Critical memory usage: {memory_percent:.1f}%")
            score -= 25
        elif memory_percent > 85:
            issues.append(f"High memory usage: {memory_percent:.1f}%")
            score -= 10
        
        # Check disk usage
        disk_percent = metrics.get("disk_percent", 0)
        if disk_percent > 95:
            issues.append(f"Critical disk usage: {disk_percent:.1f}%")
            score -= 20
        elif disk_percent > 90:
            issues.append(f"High disk usage: {disk_percent:.1f}%")
            score -= 10
        
        # Determine overall status
        if score >= 90:
            status = "healthy"
        elif score >= 70:
            status = "warning"
        elif score >= 50:
            status = "degraded"
        else:
            status = "critical"
        
        return {
            "status": status,
            "score": max(0, score),
            "issues": issues
        }
    
    async def get_monitoring_report(self) -> Dict[str, Any]:
        """Get comprehensive monitoring report."""
        health = await self.get_system_health()
        performance_summary = await self.performance_monitor.get_performance_summary(hours=24)
        
        return {
            "system_health": health,
            "performance_summary": performance_summary,
            "monitoring_active": self.performance_monitor._monitoring_active,
            "report_timestamp": datetime.now(UTC)
        }


# Global instances
performance_monitor = SystemPerformanceMonitor()
monitoring_manager = MonitoringManager()


__all__ = [
    "SystemPerformanceMonitor", 
    "MonitoringManager",
    "performance_monitor",
    "monitoring_manager",
]