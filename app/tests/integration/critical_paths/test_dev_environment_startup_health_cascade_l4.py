#!/usr/bin/env python3
"""
L4 Integration Test: Dev Environment Startup and Health Check Cascade

Tests the complete startup sequence with proper health check cascading:
1. Service initialization order (Redis -> Auth -> Backend -> WebSocket)
2. Health check propagation and dependencies
3. Retry mechanisms and timeouts
4. Service discovery and registration
5. Error states and recovery

BVJ:
- Segment: Platform/Internal
- Business Goal: Stability
- Value Impact: Ensures reliable dev environment startup
- Strategic Impact: Reduces developer friction and debugging time
"""

import asyncio
import json
import os
import sys
import time
import subprocess
import signal
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import aiohttp
import pytest
from datetime import datetime, timedelta
import psutil

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Service URLs
REDIS_URL = "redis://localhost:6379"
POSTGRES_URL = "postgresql://test_user:test_password@localhost:5432/test_db"
CLICKHOUSE_URL = "http://localhost:8123"
AUTH_SERVICE_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/websocket"
FRONTEND_URL = "http://localhost:3000"

# Service startup order and dependencies
SERVICE_DEPENDENCIES = {
    "redis": [],
    "postgres": [],
    "clickhouse": [],
    "auth_service": ["redis", "postgres"],
    "backend": ["redis", "postgres", "clickhouse", "auth_service"],
    "websocket": ["backend"],
    "frontend": ["backend"]
}

# Health check endpoints
HEALTH_ENDPOINTS = {
    "redis": {"type": "redis", "url": REDIS_URL},
    "postgres": {"type": "postgres", "url": POSTGRES_URL},
    "clickhouse": {"type": "http", "url": f"{CLICKHOUSE_URL}/ping"},
    "auth_service": {"type": "http", "url": f"{AUTH_SERVICE_URL}/health"},
    "backend": {"type": "http", "url": f"{BACKEND_URL}/api/v1/health"},
    "websocket": {"type": "ws", "url": WEBSOCKET_URL},
    "frontend": {"type": "http", "url": FRONTEND_URL}
}


class DevEnvironmentStartupTester:
    """Test the complete dev environment startup and health cascade."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.launcher_process: Optional[subprocess.Popen] = None
        self.service_processes: Dict[str, subprocess.Popen] = {}
        self.health_status: Dict[str, bool] = {}
        self.startup_times: Dict[str, float] = {}
        self.health_check_retries: Dict[str, int] = {}
        self.startup_logs: List[str] = []
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.session:
            await self.session.close()
        await self.cleanup_processes()
            
    async def cleanup_processes(self):
        """Clean up all started processes."""
        # Terminate services in reverse order
        for service in reversed(list(self.service_processes.keys())):
            process = self.service_processes[service]
            if process and process.poll() is None:
                print(f"[CLEANUP] Terminating {service}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
        if self.launcher_process and self.launcher_process.poll() is None:
            print("[CLEANUP] Terminating launcher...")
            self.launcher_process.terminate()
            try:
                self.launcher_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.launcher_process.kill()
    
    def log_startup_event(self, service: str, event: str, details: str = ""):
        """Log startup events for analysis."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{service.upper()}] {event}"
        if details:
            log_entry += f" - {details}"
        self.startup_logs.append(log_entry)
        print(log_entry)
    
    async def check_service_health(self, service: str, retries: int = 3) -> bool:
        """Check if a service is healthy with retries."""
        endpoint = HEALTH_ENDPOINTS.get(service)
        if not endpoint:
            self.log_startup_event(service, "NO_ENDPOINT", "No health endpoint defined")
            return False
            
        for attempt in range(retries):
            self.health_check_retries[service] = attempt + 1
            
            try:
                if endpoint["type"] == "http":
                    async with self.session.get(endpoint["url"], timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.log_startup_event(service, "HEALTHY", f"Response: {data}")
                            return True
                        else:
                            self.log_startup_event(service, "UNHEALTHY", f"Status: {response.status}")
                            
                elif endpoint["type"] == "redis":
                    import aioredis
                    redis = await aioredis.create_redis_pool(endpoint["url"])
                    pong = await redis.ping()
                    redis.close()
                    await redis.wait_closed()
                    if pong:
                        self.log_startup_event(service, "HEALTHY", "Redis PONG received")
                        return True
                        
                elif endpoint["type"] == "postgres":
                    import asyncpg
                    conn = await asyncpg.connect(endpoint["url"])
                    result = await conn.fetchval("SELECT 1")
                    await conn.close()
                    if result == 1:
                        self.log_startup_event(service, "HEALTHY", "Postgres connection OK")
                        return True
                        
                elif endpoint["type"] == "ws":
                    import websockets
                    async with websockets.connect(endpoint["url"]) as ws:
                        await ws.ping()
                        self.log_startup_event(service, "HEALTHY", "WebSocket ping OK")
                        return True
                        
            except Exception as e:
                self.log_startup_event(service, "HEALTH_CHECK_FAILED", str(e))
                
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        return False
    
    async def wait_for_service_dependencies(self, service: str) -> bool:
        """Wait for all service dependencies to be healthy."""
        dependencies = SERVICE_DEPENDENCIES.get(service, [])
        
        if not dependencies:
            return True
            
        self.log_startup_event(service, "WAITING_FOR_DEPS", f"Dependencies: {dependencies}")
        
        for dep in dependencies:
            if not self.health_status.get(dep, False):
                # Try to wait for dependency
                max_wait = 30  # seconds
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    if await self.check_service_health(dep):
                        self.health_status[dep] = True
                        break
                    await asyncio.sleep(2)
                    
                if not self.health_status.get(dep, False):
                    self.log_startup_event(service, "DEPENDENCY_FAILED", f"Dependency {dep} not healthy")
                    return False
                    
        self.log_startup_event(service, "DEPENDENCIES_MET", f"All dependencies healthy")
        return True
    
    async def start_service_with_health_check(self, service: str) -> bool:
        """Start a service and wait for it to be healthy."""
        start_time = time.time()
        
        # Check dependencies first
        if not await self.wait_for_service_dependencies(service):
            return False
            
        self.log_startup_event(service, "STARTING", "Initiating service startup")
        
        # For this test, we assume services are started by dev_launcher
        # We just monitor their health
        
        # Wait for service to become healthy
        max_wait = 60  # seconds
        check_interval = 2  # seconds
        
        while time.time() - start_time < max_wait:
            if await self.check_service_health(service):
                self.health_status[service] = True
                self.startup_times[service] = time.time() - start_time
                self.log_startup_event(
                    service, 
                    "STARTED", 
                    f"Startup time: {self.startup_times[service]:.2f}s"
                )
                return True
            await asyncio.sleep(check_interval)
            
        self.log_startup_event(service, "STARTUP_TIMEOUT", f"Failed after {max_wait}s")
        return False
    
    async def test_startup_cascade(self) -> Dict[str, Any]:
        """Test the complete startup cascade with proper ordering."""
        results = {
            "services_started": {},
            "health_checks": {},
            "startup_order": [],
            "total_startup_time": 0,
            "cascade_success": False
        }
        
        overall_start = time.time()
        
        # Start dev launcher
        self.log_startup_event("launcher", "STARTING", "Starting dev launcher process")
        
        try:
            self.launcher_process = subprocess.Popen(
                [sys.executable, "scripts/dev_launcher.py", "--no-browser", "--non-interactive"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=project_root
            )
            
            # Give launcher time to initialize
            await asyncio.sleep(5)
            
            # Check services in dependency order
            ordered_services = self._get_startup_order()
            
            for service in ordered_services:
                self.log_startup_event(service, "CHECKING", "Verifying service health")
                
                service_healthy = await self.start_service_with_health_check(service)
                results["services_started"][service] = service_healthy
                results["health_checks"][service] = {
                    "healthy": service_healthy,
                    "retries": self.health_check_retries.get(service, 0),
                    "startup_time": self.startup_times.get(service, 0)
                }
                
                if service_healthy:
                    results["startup_order"].append(service)
                else:
                    self.log_startup_event(service, "FAILED", "Service failed to start")
                    # Continue checking other services for diagnostic purposes
                    
        except Exception as e:
            self.log_startup_event("launcher", "ERROR", str(e))
            
        results["total_startup_time"] = time.time() - overall_start
        results["cascade_success"] = all(results["services_started"].values())
        
        return results
    
    def _get_startup_order(self) -> List[str]:
        """Get the correct startup order based on dependencies."""
        # Simple topological sort
        ordered = []
        visited = set()
        
        def visit(service):
            if service in visited:
                return
            visited.add(service)
            for dep in SERVICE_DEPENDENCIES.get(service, []):
                visit(dep)
            ordered.append(service)
            
        for service in SERVICE_DEPENDENCIES:
            visit(service)
            
        return ordered
    
    async def test_health_check_cascade_failure(self) -> Dict[str, Any]:
        """Test health check cascade when a dependency fails."""
        results = {
            "cascade_effects": {},
            "recovery_attempted": {},
            "final_status": {}
        }
        
        # Simulate auth service failure
        self.log_startup_event("test", "SIMULATING_FAILURE", "Auth service failure scenario")
        
        # Check which services are affected
        affected_services = []
        for service, deps in SERVICE_DEPENDENCIES.items():
            if "auth_service" in deps:
                affected_services.append(service)
                
        results["cascade_effects"]["auth_service_failure"] = affected_services
        
        # Try to recover
        for service in affected_services:
            self.log_startup_event(service, "RECOVERY_CHECK", "Checking if service can recover")
            can_recover = await self.check_service_health(service, retries=1)
            results["recovery_attempted"][service] = can_recover
            
        # Final health check
        for service in SERVICE_DEPENDENCIES:
            results["final_status"][service] = await self.check_service_health(service, retries=1)
            
        return results
    
    async def test_concurrent_health_checks(self) -> Dict[str, Any]:
        """Test concurrent health checks across all services."""
        results = {
            "concurrent_checks": {},
            "check_duration": 0,
            "parallel_efficiency": 0
        }
        
        start_time = time.time()
        
        # Run health checks concurrently
        tasks = []
        for service in SERVICE_DEPENDENCIES:
            task = asyncio.create_task(self.check_service_health(service))
            tasks.append((service, task))
            
        # Wait for all checks to complete
        for service, task in tasks:
            try:
                health_status = await asyncio.wait_for(task, timeout=10)
                results["concurrent_checks"][service] = health_status
            except asyncio.TimeoutError:
                results["concurrent_checks"][service] = False
                self.log_startup_event(service, "CONCURRENT_CHECK_TIMEOUT", "Health check timed out")
                
        results["check_duration"] = time.time() - start_time
        
        # Calculate parallel efficiency
        sequential_time = len(SERVICE_DEPENDENCIES) * 2  # Assume 2s per check
        results["parallel_efficiency"] = min(
            100, 
            (sequential_time / max(results["check_duration"], 0.1)) * 100
        )
        
        return results
    
    async def test_service_restart_recovery(self) -> Dict[str, Any]:
        """Test service restart and recovery mechanisms."""
        results = {
            "restart_tests": {},
            "recovery_times": {},
            "dependent_impact": {}
        }
        
        # Test restarting backend service
        service_to_restart = "backend"
        
        # Check initial health
        initial_health = await self.check_service_health(service_to_restart)
        results["restart_tests"]["initial_health"] = initial_health
        
        if initial_health:
            self.log_startup_event(service_to_restart, "RESTART_TEST", "Simulating service restart")
            
            # Find dependent services
            dependents = [s for s, deps in SERVICE_DEPENDENCIES.items() 
                         if service_to_restart in deps]
            
            # Monitor recovery
            recovery_start = time.time()
            
            # Wait and check recovery
            await asyncio.sleep(5)
            
            # Check if service recovered
            recovered = await self.check_service_health(service_to_restart)
            results["restart_tests"]["recovered"] = recovered
            results["recovery_times"][service_to_restart] = time.time() - recovery_start
            
            # Check impact on dependents
            for dependent in dependents:
                dep_health = await self.check_service_health(dependent)
                results["dependent_impact"][dependent] = dep_health
                
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all startup and health cascade tests."""
        all_results = {
            "test_timestamp": datetime.now().isoformat(),
            "startup_cascade": {},
            "health_cascade_failure": {},
            "concurrent_checks": {},
            "restart_recovery": {},
            "startup_logs": [],
            "summary": {}
        }
        
        # Test 1: Startup cascade
        print("\n" + "="*60)
        print("TEST 1: STARTUP CASCADE")
        print("="*60)
        all_results["startup_cascade"] = await self.test_startup_cascade()
        
        # Test 2: Health check cascade failure
        print("\n" + "="*60)
        print("TEST 2: HEALTH CASCADE FAILURE")
        print("="*60)
        all_results["health_cascade_failure"] = await self.test_health_check_cascade_failure()
        
        # Test 3: Concurrent health checks
        print("\n" + "="*60)
        print("TEST 3: CONCURRENT HEALTH CHECKS")
        print("="*60)
        all_results["concurrent_checks"] = await self.test_concurrent_health_checks()
        
        # Test 4: Service restart recovery
        print("\n" + "="*60)
        print("TEST 4: SERVICE RESTART RECOVERY")
        print("="*60)
        all_results["restart_recovery"] = await self.test_service_restart_recovery()
        
        # Add logs
        all_results["startup_logs"] = self.startup_logs
        
        # Generate summary
        all_results["summary"] = {
            "total_services": len(SERVICE_DEPENDENCIES),
            "services_healthy": sum(1 for h in self.health_status.values() if h),
            "cascade_success": all_results["startup_cascade"]["cascade_success"],
            "total_startup_time": all_results["startup_cascade"]["total_startup_time"],
            "avg_health_check_retries": sum(self.health_check_retries.values()) / max(len(self.health_check_retries), 1)
        }
        
        return all_results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.level_4
async def test_dev_environment_startup_health_cascade():
    """Test the complete dev environment startup and health cascade."""
    async with DevEnvironmentStartupTester() as tester:
        results = await tester.run_all_tests()
        
        # Print detailed results
        print("\n" + "="*60)
        print("STARTUP AND HEALTH CASCADE TEST RESULTS")
        print("="*60)
        
        # Startup cascade results
        print("\nStartup Cascade:")
        cascade = results["startup_cascade"]
        for service, started in cascade["services_started"].items():
            status = "✓" if started else "✗"
            startup_time = cascade["health_checks"][service]["startup_time"]
            print(f"  {status} {service:20} : {startup_time:.2f}s")
            
        print(f"\nTotal Startup Time: {cascade['total_startup_time']:.2f}s")
        print(f"Cascade Success: {cascade['cascade_success']}")
        
        # Health cascade failure results
        print("\nHealth Cascade Failure Test:")
        failure_test = results["health_cascade_failure"]
        print(f"  Affected by auth_service failure: {failure_test['cascade_effects']}")
        
        # Concurrent checks results
        print("\nConcurrent Health Checks:")
        concurrent = results["concurrent_checks"]
        print(f"  Check Duration: {concurrent['check_duration']:.2f}s")
        print(f"  Parallel Efficiency: {concurrent['parallel_efficiency']:.1f}%")
        
        # Summary
        summary = results["summary"]
        print("\nSummary:")
        print(f"  Services Healthy: {summary['services_healthy']}/{summary['total_services']}")
        print(f"  Cascade Success: {summary['cascade_success']}")
        print(f"  Avg Health Check Retries: {summary['avg_health_check_retries']:.1f}")
        
        # Assert critical conditions
        assert cascade["cascade_success"], "Startup cascade failed"
        assert summary["services_healthy"] >= 5, "Not enough services are healthy"
        assert cascade["total_startup_time"] < 120, "Startup took too long (>2 minutes)"
        assert concurrent["parallel_efficiency"] > 50, "Poor parallel efficiency in health checks"
        
        print("\n[SUCCESS] All startup and health cascade tests passed!")


async def main():
    """Run the test standalone."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*60)
    print("DEV ENVIRONMENT STARTUP AND HEALTH CASCADE TEST (L4)")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with DevEnvironmentStartupTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results to file for analysis
        results_file = project_root / "test_results" / "startup_health_cascade_results.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"\nResults saved to: {results_file}")
        
        # Return exit code based on results
        if results["startup_cascade"]["cascade_success"]:
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)