"""
Health checking and validation for deployed services.
"""

import asyncio
import aiohttp
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Result of a health check."""
    service_name: str
    status: HealthStatus
    response_time_ms: float
    checks: Dict[str, bool]
    message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class HealthChecker:
    """Comprehensive health checking for deployed services."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def check_service_health(self, 
                                  service_url: str, 
                                  service_name: str,
                                  health_endpoint: str = "/health") -> HealthCheckResult:
        """
        Check the health of a single service.
        
        Args:
            service_url: Base URL of the service
            service_name: Name of the service
            health_endpoint: Health check endpoint path
            
        Returns:
            HealthCheckResult object
        """
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        
        health_url = f"{service_url.rstrip('/')}{health_endpoint}"
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self.session.get(health_url) as response:
                response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        return self._parse_health_response(
                            service_name, 
                            data, 
                            response_time_ms
                        )
                    except json.JSONDecodeError:
                        # Basic health check passed
                        return HealthCheckResult(
                            service_name=service_name,
                            status=HealthStatus.HEALTHY,
                            response_time_ms=response_time_ms,
                            checks={"http": True},
                            message="Basic health check passed"
                        )
                else:
                    return HealthCheckResult(
                        service_name=service_name,
                        status=HealthStatus.UNHEALTHY,
                        response_time_ms=response_time_ms,
                        checks={"http": False},
                        message=f"HTTP {response.status}"
                    )
                    
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=self.timeout * 1000,
                checks={"http": False},
                message="Health check timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                checks={"http": False},
                message=str(e)
            )
    
    def _parse_health_response(self, 
                              service_name: str,
                              data: Dict[str, Any], 
                              response_time_ms: float) -> HealthCheckResult:
        """Parse structured health check response."""
        # Support multiple health check response formats
        
        # Format 1: Simple status
        if "status" in data:
            status_str = data["status"].lower()
            if status_str in ["healthy", "ok", "up"]:
                status = HealthStatus.HEALTHY
            elif status_str in ["degraded", "warning"]:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
        # Format 2: Checks based
        elif "checks" in data:
            checks = data["checks"]
            all_healthy = all(checks.values()) if isinstance(checks, dict) else True
            status = HealthStatus.HEALTHY if all_healthy else HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        checks = data.get("checks", {"http": True})
        message = data.get("message") or data.get("version")
        
        return HealthCheckResult(
            service_name=service_name,
            status=status,
            response_time_ms=response_time_ms,
            checks=checks,
            message=message
        )
    
    async def check_multiple_services(self, 
                                     services: List[Dict[str, str]]) -> Dict[str, HealthCheckResult]:
        """
        Check health of multiple services concurrently.
        
        Args:
            services: List of service configurations with 'name' and 'url' keys
            
        Returns:
            Dictionary mapping service names to health results
        """
        tasks = []
        for service in services:
            task = self.check_service_health(
                service["url"],
                service["name"],
                service.get("health_endpoint", "/health")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_results = {}
        for service, result in zip(services, results):
            if isinstance(result, Exception):
                health_results[service["name"]] = HealthCheckResult(
                    service_name=service["name"],
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0,
                    checks={"error": True},
                    message=str(result)
                )
            else:
                health_results[service["name"]] = result
        
        return health_results
    
    async def wait_for_healthy(self, 
                              service_url: str,
                              service_name: str,
                              max_wait_seconds: int = 300,
                              check_interval: int = 10) -> bool:
        """
        Wait for a service to become healthy.
        
        Args:
            service_url: Base URL of the service
            service_name: Name of the service
            max_wait_seconds: Maximum time to wait
            check_interval: Seconds between health checks
            
        Returns:
            True if service became healthy, False if timeout
        """
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=max_wait_seconds)
        
        while datetime.utcnow() < end_time:
            result = await self.check_service_health(service_url, service_name)
            
            if result.status == HealthStatus.HEALTHY:
                logger.info(f"{service_name} is healthy after {(datetime.utcnow() - start_time).seconds}s")
                return True
            
            logger.info(f"Waiting for {service_name} to become healthy... ({result.status.value})")
            await asyncio.sleep(check_interval)
        
        logger.error(f"{service_name} did not become healthy within {max_wait_seconds}s")
        return False
    
    def generate_health_report(self, results: Dict[str, HealthCheckResult]) -> str:
        """
        Generate a formatted health report.
        
        Args:
            results: Dictionary of health check results
            
        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 60,
            "SERVICE HEALTH REPORT",
            "=" * 60,
            f"Timestamp: {datetime.utcnow().isoformat()}",
            ""
        ]
        
        # Summary
        total = len(results)
        healthy = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
        degraded = sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY)
        
        report_lines.extend([
            "SUMMARY:",
            f"  Total Services: {total}",
            f"  Healthy: {healthy}",
            f"  Degraded: {degraded}",
            f"  Unhealthy: {unhealthy}",
            ""
        ])
        
        # Individual service details
        report_lines.append("SERVICE DETAILS:")
        for service_name, result in sorted(results.items()):
            status_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.DEGRADED: "⚠️",
                HealthStatus.UNHEALTHY: "❌",
                HealthStatus.UNKNOWN: "❓"
            }.get(result.status, "")
            
            report_lines.append(f"\n  {status_emoji} {service_name}:")
            report_lines.append(f"    Status: {result.status.value}")
            report_lines.append(f"    Response Time: {result.response_time_ms:.2f}ms")
            
            if result.checks:
                report_lines.append("    Checks:")
                for check_name, check_status in result.checks.items():
                    check_emoji = "✓" if check_status else "✗"
                    report_lines.append(f"      {check_emoji} {check_name}")
            
            if result.message:
                report_lines.append(f"    Message: {result.message}")
        
        report_lines.extend(["", "=" * 60])
        return "\n".join(report_lines)
    
    async def check_dependencies(self, 
                                service_name: str,
                                dependencies: List[Dict[str, str]]) -> Tuple[bool, List[str]]:
        """
        Check if all dependencies are healthy.
        
        Args:
            service_name: Name of the service checking dependencies
            dependencies: List of dependency configurations
            
        Returns:
            Tuple of (all_healthy, list_of_failed_dependencies)
        """
        results = await self.check_multiple_services(dependencies)
        
        failed_deps = []
        for dep_name, result in results.items():
            if result.status not in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                failed_deps.append(dep_name)
        
        all_healthy = len(failed_deps) == 0
        
        if not all_healthy:
            logger.warning(f"{service_name} has unhealthy dependencies: {', '.join(failed_deps)}")
        
        return all_healthy, failed_deps