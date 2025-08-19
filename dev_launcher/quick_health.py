"""
Quick health checker for lightweight startup health validation.

Provides lightweight health checks (< 500ms total), skips detailed checks on startup,
implements progressive health validation, async health monitoring, and quick readiness checks only.
"""

import time
import socket
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    WARNING = "warning" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check definition."""
    name: str
    check_func: callable
    timeout: float = 0.1
    critical: bool = False
    quick_only: bool = True


@dataclass
class HealthResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    duration: float
    message: str
    details: Optional[Dict[str, Any]] = None


class QuickHealthChecker:
    """
    Lightweight health checker optimized for startup performance.
    
    Performs minimal health checks during startup (< 500ms total),
    with progressive validation and async monitoring capabilities.
    """
    
    def __init__(self, timeout_budget: float = 0.5):
        """Initialize with total timeout budget for all checks."""
        self.timeout_budget = timeout_budget
        self.quick_checks: List[HealthCheck] = []
        self.detailed_checks: List[HealthCheck] = []
        self.last_results: Dict[str, HealthResult] = {}
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def register_quick_check(self, name: str, check_func: callable, 
                           timeout: float = 0.1, critical: bool = False):
        """Register a quick health check for startup."""
        check = HealthCheck(name, check_func, timeout, critical, True)
        self.quick_checks.append(check)
    
    def register_detailed_check(self, name: str, check_func: callable,
                              timeout: float = 1.0, critical: bool = False):
        """Register a detailed health check for background monitoring."""
        check = HealthCheck(name, check_func, timeout, critical, False)
        self.detailed_checks.append(check)
    
    def _execute_single_check(self, check: HealthCheck) -> HealthResult:
        """Execute a single health check with timeout."""
        start_time = time.time()
        try:
            result = check.check_func()
            duration = time.time() - start_time
            return self._process_check_result(check, result, duration)
        except Exception as e:
            duration = time.time() - start_time
            status = HealthStatus.UNHEALTHY if check.critical else HealthStatus.WARNING
            message = f"{check.name} check failed: {str(e)[:100]}"
            return HealthResult(check.name, status, duration, message)
    
    def _process_check_result(self, check: HealthCheck, result: Any, duration: float) -> HealthResult:
        """Process check result and create HealthResult."""
        if isinstance(result, bool):
            status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
            message = f"{check.name} check {'passed' if result else 'failed'}"
            return HealthResult(check.name, status, duration, message)
        elif isinstance(result, tuple) and len(result) >= 2:
            status, message = result[:2]
            details = result[2] if len(result) > 2 else None
            return HealthResult(check.name, status, duration, message, details)
        return HealthResult(check.name, HealthStatus.HEALTHY, duration, str(result))
    
    def run_quick_checks(self) -> Dict[str, HealthResult]:
        """Run only quick checks optimized for startup performance."""
        start_time = time.time()
        results = {}
        
        # Sort by timeout to run fastest checks first
        sorted_checks = sorted(self.quick_checks, key=lambda c: c.timeout)
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_check = {
                executor.submit(self._execute_single_check, check): check 
                for check in sorted_checks
            }
            
            for future in as_completed(future_to_check, timeout=self.timeout_budget):
                elapsed = time.time() - start_time
                if elapsed > self.timeout_budget:
                    logger.warning("Quick health checks exceeded timeout budget")
                    break
                
                try:
                    result = future.result(timeout=0.1)
                    results[result.name] = result
                    self.last_results[result.name] = result
                except Exception as e:
                    check = future_to_check[future]
                    result = HealthResult(
                        check.name, HealthStatus.UNKNOWN, 
                        elapsed, f"Check timeout: {e}"
                    )
                    results[result.name] = result
        
        total_duration = time.time() - start_time
        logger.debug(f"Quick health checks completed in {total_duration:.3f}s")
        return results
    
    def check_port_available(self, port: int, host: str = "localhost") -> Tuple[HealthStatus, str]:
        """Quick port availability check."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.05)  # 50ms timeout
                result = sock.connect_ex((host, port))
                if result == 0:
                    return HealthStatus.HEALTHY, f"Port {port} is accessible"
                else:
                    return HealthStatus.UNHEALTHY, f"Port {port} not accessible"
        except Exception as e:
            return HealthStatus.WARNING, f"Port {port} check failed: {str(e)[:50]}"
    
    def check_service_responding(self, port: int, path: str = "/health") -> Tuple[HealthStatus, str]:
        """Quick service response check without full HTTP request."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.1)  # 100ms timeout
                result = sock.connect_ex(("localhost", port))
                if result == 0:
                    return HealthStatus.HEALTHY, f"Service on port {port} responding"
                else:
                    return HealthStatus.WARNING, f"Service on port {port} not responding"
        except Exception:
            return HealthStatus.UNHEALTHY, f"Cannot connect to service on port {port}"
    
    def check_directory_accessible(self, path: str) -> Tuple[HealthStatus, str]:
        """Quick directory accessibility check."""
        try:
            from pathlib import Path
            path_obj = Path(path)
            if path_obj.exists() and path_obj.is_dir():
                return HealthStatus.HEALTHY, f"Directory {path} accessible"
            else:
                return HealthStatus.WARNING, f"Directory {path} not found"
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Directory check failed: {str(e)[:50]}"
    
    def check_process_running(self, process_name: str) -> Tuple[HealthStatus, str]:
        """Quick process existence check."""
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if process_name.lower() in proc.info['name'].lower():
                    return HealthStatus.HEALTHY, f"Process {process_name} running"
            return HealthStatus.WARNING, f"Process {process_name} not found"
        except Exception as e:
            return HealthStatus.UNKNOWN, f"Process check failed: {str(e)[:50]}"
    
    async def run_async_health_monitoring(self, interval: int = 30) -> None:
        """Run continuous health monitoring in background."""
        logger.info(f"Starting async health monitoring (interval: {interval}s)")
        while True:
            try:
                await asyncio.sleep(interval)
                results = await self._run_detailed_checks_async()
                self._process_monitoring_results(results)
            except asyncio.CancelledError:
                logger.info("Async health monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def _run_detailed_checks_async(self) -> Dict[str, HealthResult]:
        """Run detailed health checks asynchronously."""
        loop = asyncio.get_event_loop()
        results = {}
        tasks = [(c.name, loop.run_in_executor(self.executor, self._execute_single_check, c)) for c in self.detailed_checks]
        for name, task in tasks:
            try:
                results[name] = await asyncio.wait_for(task, timeout=2.0)
            except asyncio.TimeoutError:
                results[name] = HealthResult(name, HealthStatus.WARNING, 2.0, "Detailed check timeout")
        return results
    
    def _process_monitoring_results(self, results: Dict[str, HealthResult]):
        """Process monitoring results and take actions if needed."""
        failures = [r for r in results.values() if r.status == HealthStatus.UNHEALTHY]
        if failures:
            logger.warning(f"Critical health failures: {len(failures)}")
            for failure in failures:
                logger.warning(f"  - {failure.name}: {failure.message}")
        self.last_results.update(results)
    
    def get_startup_readiness_score(self) -> Tuple[float, Dict[str, Any]]:
        """Calculate readiness score based on quick checks."""
        if not self.last_results:
            return 0.0, {"message": "No health checks performed yet"}
        total_checks = len(self.last_results)
        healthy_checks = sum(1 for r in self.last_results.values() if r.status == HealthStatus.HEALTHY)
        score = healthy_checks / total_checks if total_checks > 0 else 0.0
        details = {
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "check_results": {n: {"status": r.status.value, "message": r.message} for n, r in self.last_results.items()}
        }
        return score, details
    
    def is_ready_for_startup(self, minimum_score: float = 0.8) -> bool:
        """Check if system is ready for startup based on health score."""
        score, _ = self.get_startup_readiness_score()
        return score >= minimum_score
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get summary of current health status."""
        if not self.last_results:
            return {"status": "no_checks", "message": "No health checks performed"}
        status_counts = {s.value: sum(1 for r in self.last_results.values() if r.status == s) for s in HealthStatus}
        overall_status = self._determine_overall_status(status_counts)
        return {
            "overall_status": overall_status.value,
            "status_counts": status_counts,
            "total_checks": len(self.last_results),
            "last_check_time": max(r.duration for r in self.last_results.values()) if self.last_results else 0
        }
    
    def _determine_overall_status(self, counts: Dict[str, int]) -> HealthStatus:
        """Determine overall health status from counts."""
        if counts.get("unhealthy", 0) > 0:
            return HealthStatus.UNHEALTHY
        elif counts.get("warning", 0) > 0:
            return HealthStatus.WARNING
        elif counts.get("unknown", 0) > 0:
            return HealthStatus.UNKNOWN
        return HealthStatus.HEALTHY
    
    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        logger.debug("Quick health checker cleanup completed")


# Factory functions for common health checks
def create_standard_quick_checks(checker: QuickHealthChecker, config: Dict[str, Any]):
    """Create standard set of quick health checks."""
    if "backend_port" in config:
        checker.register_quick_check("backend_port", lambda: checker.check_port_available(config["backend_port"]), 0.05, True)
    if "frontend_port" in config:
        checker.register_quick_check("frontend_port", lambda: checker.check_port_available(config["frontend_port"]), 0.05, True)
    if "project_root" in config:
        checker.register_quick_check("project_directory", lambda: checker.check_directory_accessible(config["project_root"]), 0.02, True)
    temp_dir = "/tmp" if not config.get("windows") else "C:\\temp"
    checker.register_quick_check("temp_directory", lambda: checker.check_directory_accessible(temp_dir), 0.02, False)


def create_service_response_checks(checker: QuickHealthChecker, services: Dict[str, Dict[str, Any]]):
    """Create service response health checks."""
    for service_name, service_config in services.items():
        port = service_config.get("port")
        if port:
            checker.register_detailed_check(f"{service_name}_response", lambda p=port: checker.check_service_responding(p), 0.2, service_config.get("critical", False))