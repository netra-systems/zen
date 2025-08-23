#!/usr/bin/env python3
"""
GCP Health Monitoring System for Netra Apex Platform

Business Value: Ensures continuous monitoring of GCP services health,
detecting and reporting issues before they impact customers.
Provides real-time status dashboard and recovery tracking.

This script monitors all GCP services continuously until they are 100% healthy.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

import aiohttp
import requests
from colorama import Fore, Style, init

# Fix Unicode encoding issues on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Initialize colorama for Windows compatibility
init(autoreset=True)

class ServiceStatus(Enum):
    """Service health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """Configuration for a single health check."""
    name: str
    path: str
    expected_status: int = 200
    timeout: float = 10.0
    critical: bool = True

@dataclass
class ServiceConfig:
    """Configuration for a service to monitor."""
    name: str
    base_url: str
    health_checks: List[HealthCheck] = field(default_factory=list)
    display_name: str = ""

@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    url: str
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    error: Optional[str] = None
    healthy: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ServiceHealth:
    """Overall health status for a service."""
    service_name: str
    status: ServiceStatus
    checks: List[CheckResult] = field(default_factory=list)
    passed_checks: int = 0
    total_checks: int = 0
    last_update: datetime = field(default_factory=datetime.now)

class GCPHealthMonitor:
    """Continuous health monitoring system for GCP services."""
    
    def __init__(self, check_interval: int = 30, timeout_minutes: int = 60):
        """Initialize the health monitor."""
        self.check_interval = check_interval
        self.timeout_minutes = timeout_minutes
        self.start_time = datetime.now()
        self.services = self._configure_services()
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "status_changes": 0
        }
        self.previous_statuses: Dict[str, ServiceStatus] = {}
    
    def _configure_services(self) -> List[ServiceConfig]:
        """Configure all services to monitor."""
        return [
            ServiceConfig(
                name="auth",
                display_name="Auth Service",
                base_url="https://netra-auth-service-701982941522.us-central1.run.app",
                health_checks=[
                    HealthCheck("main_health", "/health", 200, 5.0, True),
                    HealthCheck("auth_health", "/auth/health", 200, 5.0, False),
                ]
            ),
            ServiceConfig(
                name="backend",
                display_name="Backend Service", 
                base_url="https://netra-backend-staging-701982941522.us-central1.run.app",
                health_checks=[
                    HealthCheck("main_health", "/health", 200, 10.0, True),
                    HealthCheck("readiness", "/health/ready", 200, 10.0, True),
                    HealthCheck("database", "/health/database", 200, 15.0, True),
                    HealthCheck("system", "/health/system", 200, 10.0, False),
                ]
            ),
            ServiceConfig(
                name="frontend",
                display_name="Frontend Service",
                base_url="https://netra-frontend-staging-701982941522.us-central1.run.app",
                health_checks=[
                    HealthCheck("main_page", "/", 200, 10.0, True),
                ]
            )
        ]
    
    async def start_monitoring(self) -> bool:
        """Start continuous monitoring until all services are healthy."""
        print(f"{Fore.CYAN}[MONITOR] Starting GCP Health Monitoring System{Style.RESET_ALL}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Timeout: {self.timeout_minutes} minutes")
        print(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        timeout_time = self.start_time + timedelta(minutes=self.timeout_minutes)
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            while datetime.now() < timeout_time:
                # Perform health checks
                service_healths = await self._check_all_services()
                
                # Display status
                self._display_status(service_healths)
                
                # Check if all services are healthy
                if self._all_services_healthy(service_healths):
                    print(f"\n{Fore.GREEN}[SUCCESS] ALL SERVICES ARE HEALTHY!{Style.RESET_ALL}")
                    self._display_final_summary()
                    return True
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
            
            print(f"\n{Fore.RED}[TIMEOUT] Monitoring timeout reached ({self.timeout_minutes} minutes){Style.RESET_ALL}")
            self._display_final_summary()
            return False
    
    async def _check_all_services(self) -> List[ServiceHealth]:
        """Check health of all configured services."""
        tasks = []
        for service in self.services:
            task = asyncio.create_task(self._check_service_health(service))
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    async def _check_service_health(self, service: ServiceConfig) -> ServiceHealth:
        """Check health of a single service."""
        results = []
        
        for health_check in service.health_checks:
            result = await self._perform_health_check(service.base_url, health_check)
            results.append(result)
            self.stats["total_checks"] += 1
            
            if result.healthy:
                self.stats["successful_checks"] += 1
            else:
                self.stats["failed_checks"] += 1
        
        # Determine overall service status
        passed_checks = sum(1 for r in results if r.healthy)
        total_checks = len(results)
        critical_checks = [r for r in results if not r.healthy and 
                          any(hc.critical for hc in service.health_checks if hc.name == r.name)]
        
        if passed_checks == total_checks:
            status = ServiceStatus.HEALTHY
        elif critical_checks:
            status = ServiceStatus.CRITICAL
        elif passed_checks > 0:
            status = ServiceStatus.DEGRADED
        else:
            status = ServiceStatus.UNKNOWN
        
        # Track status changes
        if service.name in self.previous_statuses:
            if self.previous_statuses[service.name] != status:
                self.stats["status_changes"] += 1
        self.previous_statuses[service.name] = status
        
        return ServiceHealth(
            service_name=service.name,
            status=status,
            checks=results,
            passed_checks=passed_checks,
            total_checks=total_checks,
            last_update=datetime.now()
        )
    
    async def _perform_health_check(self, base_url: str, health_check: HealthCheck) -> CheckResult:
        """Perform a single health check."""
        url = f"{base_url.rstrip('/')}{health_check.path}"
        start_time = time.time()
        
        try:
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=health_check.timeout)
            ) as response:
                response_time = time.time() - start_time
                
                # Special handling for frontend - check if it's actually serving content
                if health_check.name == "main_page" and response.status == 200:
                    text = await response.text()
                    if "404" in text or "Not Found" in text:
                        return CheckResult(
                            name=health_check.name,
                            url=url,
                            status_code=response.status,
                            response_time=response_time,
                            error="Page shows 404 content",
                            healthy=False
                        )
                
                healthy = response.status == health_check.expected_status
                
                return CheckResult(
                    name=health_check.name,
                    url=url,
                    status_code=response.status,
                    response_time=response_time,
                    healthy=healthy
                )
        
        except asyncio.TimeoutError:
            return CheckResult(
                name=health_check.name,
                url=url,
                error=f"Timeout after {health_check.timeout}s",
                healthy=False
            )
        except Exception as e:
            return CheckResult(
                name=health_check.name,
                url=url,
                error=str(e),
                healthy=False
            )
    
    def _display_status(self, service_healths: List[ServiceHealth]):
        """Display current status of all services."""
        # Clear screen for real-time updates
        os.system('cls' if os.name == 'nt' else 'clear')
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elapsed = datetime.now() - self.start_time
        
        print(f"{Fore.CYAN}=== GCP Health Monitor ==={Style.RESET_ALL}")
        print(f"Time: {current_time}")
        print(f"Elapsed: {str(elapsed).split('.')[0]}")
        print(f"Next check in: {self.check_interval} seconds")
        print()
        
        print(f"{Fore.CYAN}Service Status:{Style.RESET_ALL}")
        for health in service_healths:
            service_config = next(s for s in self.services if s.name == health.service_name)
            status_icon, status_color = self._get_status_display(health.status)
            
            print(f"{status_color}{status_icon} {service_config.display_name:<20} - "
                  f"{health.status.value.upper()} ({health.passed_checks}/{health.total_checks} checks passed){Style.RESET_ALL}")
        
        print()
        
        # Show failed checks
        failed_checks = []
        for health in service_healths:
            service_config = next(s for s in self.services if s.name == health.service_name)
            for check in health.checks:
                if not check.healthy:
                    failed_checks.append((service_config.display_name, check))
        
        if failed_checks:
            print(f"{Fore.RED}Failed Checks:{Style.RESET_ALL}")
            for service_name, check in failed_checks:
                error_msg = check.error or f"{check.status_code} response"
                print(f"- {service_name} {check.name}: {error_msg}")
        else:
            print(f"{Fore.GREEN}No failed checks!{Style.RESET_ALL}")
        
        print()
        
        # Show response times for healthy checks
        print(f"{Fore.CYAN}Response Times:{Style.RESET_ALL}")
        for health in service_healths:
            service_config = next(s for s in self.services if s.name == health.service_name)
            healthy_checks = [c for c in health.checks if c.healthy and c.response_time]
            if healthy_checks:
                avg_time = sum(c.response_time for c in healthy_checks) / len(healthy_checks)
                print(f"- {service_config.display_name}: {avg_time:.2f}s avg")
        
        print()
        
        # Show statistics
        success_rate = (self.stats["successful_checks"] / max(self.stats["total_checks"], 1)) * 100
        print(f"{Fore.CYAN}Statistics:{Style.RESET_ALL}")
        print(f"- Total checks: {self.stats['total_checks']}")
        print(f"- Success rate: {success_rate:.1f}%")
        print(f"- Status changes: {self.stats['status_changes']}")
        
        print("=" * 80)
    
    def _get_status_display(self, status: ServiceStatus) -> Tuple[str, str]:
        """Get display icon and color for status."""
        if status == ServiceStatus.HEALTHY:
            return "[OK]", Fore.GREEN
        elif status == ServiceStatus.DEGRADED:
            return "[WARN]", Fore.YELLOW
        elif status == ServiceStatus.CRITICAL:
            return "[FAIL]", Fore.RED
        else:
            return "[UNKN]", Fore.MAGENTA
    
    def _all_services_healthy(self, service_healths: List[ServiceHealth]) -> bool:
        """Check if all services are healthy."""
        return all(health.status == ServiceStatus.HEALTHY for health in service_healths)
    
    def _display_final_summary(self):
        """Display final monitoring summary."""
        total_time = datetime.now() - self.start_time
        
        print(f"\n{Fore.CYAN}=== Monitoring Summary ==={Style.RESET_ALL}")
        print(f"Total monitoring time: {str(total_time).split('.')[0]}")
        print(f"Total health checks performed: {self.stats['total_checks']}")
        print(f"Successful checks: {self.stats['successful_checks']}")
        print(f"Failed checks: {self.stats['failed_checks']}")
        print(f"Status changes detected: {self.stats['status_changes']}")
        
        if self.stats["total_checks"] > 0:
            success_rate = (self.stats["successful_checks"] / self.stats["total_checks"]) * 100
            print(f"Overall success rate: {success_rate:.1f}%")

def main():
    """Main entry point for the health monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GCP Health Monitoring System")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds (default: 30)")
    parser.add_argument("--timeout", type=int, default=60, help="Monitoring timeout in minutes (default: 60)")
    parser.add_argument("--single-run", action="store_true", help="Run checks once and exit")
    
    args = parser.parse_args()
    
    if args.single_run:
        # Run a single check for testing
        monitor = GCPHealthMonitor(args.interval, args.timeout)
        
        async def single_check():
            async with aiohttp.ClientSession() as session:
                monitor.session = session
                service_healths = await monitor._check_all_services()
                monitor._display_status(service_healths)
                return monitor._all_services_healthy(service_healths)
        
        try:
            all_healthy = asyncio.run(single_check())
            sys.exit(0 if all_healthy else 1)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Monitoring interrupted by user{Style.RESET_ALL}")
            sys.exit(1)
    else:
        # Continuous monitoring
        monitor = GCPHealthMonitor(args.interval, args.timeout)
        
        try:
            all_healthy = asyncio.run(monitor.start_monitoring())
            sys.exit(0 if all_healthy else 1)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Monitoring interrupted by user{Style.RESET_ALL}")
            monitor._display_final_summary()
            sys.exit(1)

if __name__ == "__main__":
    main()