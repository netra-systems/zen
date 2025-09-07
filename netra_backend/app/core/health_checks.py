"""
Runtime Health Check System - Monitors critical components during runtime.

This module provides continuous health monitoring for critical system components,
enabling early detection of failures and providing observability into system health.

Business Value:
- Reduces MTTR through proactive monitoring
- Enables SRE teams to detect issues before users report them
- Provides metrics for SLO/SLI tracking
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import traceback

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    last_checked: datetime
    consecutive_failures: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class HealthMonitor:
    """
    Monitors system health at runtime.
    
    Provides health check endpoints and continuous monitoring
    of critical system components.
    """
    
    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.check_intervals = {
            "id_generation": 30,  # seconds
            "websocket": 10,
            "database": 60,
            "agents": 30,
            "memory": 5,
        }
        self.monitoring_task = None
        self.is_monitoring = False
    
    async def start_monitoring(self):
        """Start continuous health monitoring."""
        if self.is_monitoring:
            logger.warning("Health monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        last_check_times = {}
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # Check each component based on its interval
                for check_name, interval in self.check_intervals.items():
                    last_check = last_check_times.get(check_name, 0)
                    
                    if current_time - last_check >= interval:
                        await self._run_check(check_name)
                        last_check_times[check_name] = current_time
                
                # Sleep briefly before next iteration
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)  # Back off on error
    
    async def _run_check(self, check_name: str):
        """Run a specific health check."""
        start_time = time.time()
        
        try:
            if check_name == "id_generation":
                status, message, details = await self._check_id_generation()
            elif check_name == "websocket":
                status, message, details = await self._check_websocket()
            elif check_name == "database":
                status, message, details = await self._check_database()
            elif check_name == "agents":
                status, message, details = await self._check_agents()
            elif check_name == "memory":
                status, message, details = await self._check_memory()
            else:
                status = HealthStatus.UNKNOWN
                message = f"Unknown check: {check_name}"
                details = {}
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Update or create health check
            if check_name in self.checks:
                check = self.checks[check_name]
                check.status = status
                check.message = message
                check.duration_ms = duration_ms
                check.last_checked = datetime.now()
                check.details = details
                check.error = None
                
                # Update consecutive failures
                if status == HealthStatus.UNHEALTHY:
                    check.consecutive_failures += 1
                else:
                    check.consecutive_failures = 0
            else:
                self.checks[check_name] = HealthCheck(
                    name=check_name,
                    status=status,
                    message=message,
                    duration_ms=duration_ms,
                    last_checked=datetime.now(),
                    details=details
                )
            
            # Log if unhealthy
            if status == HealthStatus.UNHEALTHY:
                logger.error(f"Health check failed: {check_name} - {message}")
            elif status == HealthStatus.DEGRADED:
                logger.warning(f"Health check degraded: {check_name} - {message}")
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Check failed with exception: {str(e)}"
            
            self.checks[check_name] = HealthCheck(
                name=check_name,
                status=HealthStatus.UNHEALTHY,
                message=error_msg,
                duration_ms=duration_ms,
                last_checked=datetime.now(),
                error=traceback.format_exc()
            )
            
            logger.error(f"Health check exception for {check_name}: {e}")
    
    async def _check_id_generation(self) -> tuple[HealthStatus, str, Dict[str, Any]]:
        """Check UnifiedIDManager health."""
        try:
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            
            # Test generation
            test_thread = f"health_check_{int(time.time())}"
            run_id = UnifiedIDManager.generate_run_id(test_thread)
            
            # Test validation
            if not UnifiedIDManager.validate_run_id(run_id):
                return HealthStatus.UNHEALTHY, f"Invalid ID generated: {run_id}", {}
            
            # Test extraction
            extracted = UnifiedIDManager.extract_thread_id(run_id)
            if extracted != test_thread:
                return HealthStatus.UNHEALTHY, f"Extraction mismatch: {extracted} != {test_thread}", {}
            
            # Test performance (should be fast)
            start = time.time()
            for _ in range(100):
                UnifiedIDManager.generate_run_id(f"perf_test_{_}")
            duration = time.time() - start
            
            if duration > 0.1:  # 100 IDs should generate in < 100ms
                return HealthStatus.DEGRADED, f"Slow ID generation: {duration*1000:.1f}ms for 100 IDs", {
                    "avg_ms_per_id": duration * 10
                }
            
            return HealthStatus.HEALTHY, "ID generation working", {
                "sample_run_id": run_id,
                "perf_ms_per_100": duration * 1000
            }
            
        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), {"error": str(e)}
    
    async def _check_websocket(self) -> tuple[HealthStatus, str, Dict[str, Any]]:
        """Check WebSocket components health."""
        try:
            from netra_backend.app.websocket_core.unified_manager import get_websocket_manager
            
            manager = get_websocket_manager()
            
            # Check if manager exists
            if not manager:
                return HealthStatus.UNHEALTHY, "WebSocketManager not initialized", {}
            
            # Check active connections
            connection_count = len(manager.active_connections)
            
            # Check if accepting new connections
            if hasattr(manager, 'is_accepting_connections'):
                if not manager.is_accepting_connections:
                    return HealthStatus.DEGRADED, "Not accepting new connections", {
                        "active_connections": connection_count
                    }
            
            return HealthStatus.HEALTHY, f"{connection_count} active connections", {
                "active_connections": connection_count
            }
            
        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), {"error": str(e)}
    
    async def _check_database(self) -> tuple[HealthStatus, str, Dict[str, Any]]:
        """Check database connectivity."""
        try:
            from netra_backend.app.core.database import get_db_session
            
            # Try to get a session
            async with get_db_session() as session:
                # Try a simple query
                result = await session.execute("SELECT 1")
                if result:
                    return HealthStatus.HEALTHY, "Database responsive", {}
            
            return HealthStatus.UNHEALTHY, "Database not responding", {}
            
        except Exception as e:
            # Database might not be required for all operations
            return HealthStatus.DEGRADED, f"Database check failed: {str(e)}", {"error": str(e)}
    
    async def _check_agents(self) -> tuple[HealthStatus, str, Dict[str, Any]]:
        """Check agent system health using SSOT AgentRegistry."""
        try:
            # Use SSOT AgentRegistry from UniversalRegistry
            from netra_backend.app.core.registry.universal_registry import get_global_registry
            
            # Get the global agent registry instance
            registry = get_global_registry("agent")
            
            # Check if registry is initialized
            if not registry:
                return HealthStatus.UNHEALTHY, "AgentRegistry not initialized", {}
            
            # Check registry health
            if hasattr(registry, 'is_healthy') and not registry.is_healthy():
                return HealthStatus.UNHEALTHY, "AgentRegistry is not healthy", {}
            
            # Get registry stats
            stats = registry.get_stats() if hasattr(registry, 'get_stats') else {}
            agent_count = stats.get('registered_count', 0)
            
            if agent_count == 0:
                return HealthStatus.DEGRADED, "No agents registered", {"registered_agents": 0}
            
            return HealthStatus.HEALTHY, f"{agent_count} agents registered", {
                "registered_agents": agent_count,
                "registry_stats": stats
            }
            
        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), {"error": str(e)}
    
    async def _check_memory(self) -> tuple[HealthStatus, str, Dict[str, Any]]:
        """Check memory usage."""
        try:
            import psutil
            
            # Get memory info
            memory = psutil.virtual_memory()
            
            # Check thresholds
            if memory.percent > 90:
                return HealthStatus.UNHEALTHY, f"Critical memory usage: {memory.percent}%", {
                    "memory_percent": memory.percent,
                    "available_mb": memory.available / 1024 / 1024
                }
            elif memory.percent > 80:
                return HealthStatus.DEGRADED, f"High memory usage: {memory.percent}%", {
                    "memory_percent": memory.percent,
                    "available_mb": memory.available / 1024 / 1024
                }
            
            return HealthStatus.HEALTHY, f"Memory usage: {memory.percent}%", {
                "memory_percent": memory.percent,
                "available_mb": memory.available / 1024 / 1024
            }
            
        except ImportError:
            return HealthStatus.UNKNOWN, "psutil not installed", {}
        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), {"error": str(e)}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        # Run all checks if not monitored recently
        for check_name in self.check_intervals.keys():
            if check_name not in self.checks:
                await self._run_check(check_name)
            else:
                check = self.checks[check_name]
                # Re-run if stale (older than 5 minutes)
                if datetime.now() - check.last_checked > timedelta(minutes=5):
                    await self._run_check(check_name)
        
        # Determine overall status
        statuses = [check.status for check in self.checks.values()]
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Build response
        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "checks": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "duration_ms": check.duration_ms,
                    "last_checked": check.last_checked.isoformat(),
                    "consecutive_failures": check.consecutive_failures,
                    "details": check.details
                }
                for name, check in self.checks.items()
            }
        }
    
    async def get_readiness(self) -> tuple[bool, Dict[str, Any]]:
        """
        Check if system is ready to handle requests.
        
        Returns:
            (is_ready, details)
        """
        critical_checks = ["id_generation", "websocket", "agents"]
        
        for check_name in critical_checks:
            if check_name not in self.checks:
                await self._run_check(check_name)
        
        # System is ready if all critical checks are not UNHEALTHY
        for check_name in critical_checks:
            if check_name in self.checks:
                if self.checks[check_name].status == HealthStatus.UNHEALTHY:
                    return False, {
                        "ready": False,
                        "reason": f"{check_name} is unhealthy",
                        "failed_check": check_name
                    }
        
        return True, {"ready": True}
    
    async def get_liveness(self) -> tuple[bool, Dict[str, Any]]:
        """
        Check if system is alive (should it be restarted?).
        
        Returns:
            (is_alive, details)
        """
        # System is alive if it can perform basic operations
        try:
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            
            # Can we generate an ID?
            test_id = UnifiedIDManager.generate_run_id("liveness_check")
            
            return True, {"alive": True, "test_id": test_id}
            
        except Exception as e:
            return False, {"alive": False, "error": str(e)}


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create the global health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


# FastAPI endpoints (if using FastAPI)
async def health_endpoint():
    """Health check endpoint for /health."""
    monitor = get_health_monitor()
    return await monitor.get_health_status()


async def readiness_endpoint():
    """Readiness check endpoint for /ready."""
    monitor = get_health_monitor()
    is_ready, details = await monitor.get_readiness()
    return details, 200 if is_ready else 503


async def liveness_endpoint():
    """Liveness check endpoint for /alive."""
    monitor = get_health_monitor()
    is_alive, details = await monitor.get_liveness()
    return details, 200 if is_alive else 503


if __name__ == "__main__":
    # Test health checks
    async def main():
        monitor = HealthMonitor()
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Wait a bit for checks to run
        await asyncio.sleep(5)
        
        # Get status
        status = await monitor.get_health_status()
        
        import json
        print(json.dumps(status, indent=2, default=str))
        
        # Stop monitoring
        await monitor.stop_monitoring()
    
    asyncio.run(main())