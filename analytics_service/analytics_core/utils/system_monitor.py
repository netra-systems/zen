"""
System Monitor Utility
Monitors system resources and performance metrics
"""
import logging
import psutil
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SystemMonitor:
    """System resource monitor for analytics service."""
    
    def __init__(self):
        """Initialize system monitor."""
        self.start_time = time.time()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else 0,
                "uptime_seconds": time.time() - self.start_time
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_usage_percent": 0,
                "uptime_seconds": time.time() - self.start_time
            }
    
    def get_process_info(self) -> Dict[str, Any]:
        """Get current process information."""
        try:
            process = psutil.Process()
            return {
                "pid": process.pid,
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(interval=0.1),
                "threads": process.num_threads()
            }
        except Exception as e:
            logger.error(f"Failed to get process info: {e}")
            return {
                "pid": 0,
                "memory_mb": 0,
                "cpu_percent": 0,
                "threads": 0
            }