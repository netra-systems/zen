"""Service Orchestrator for E2E Testing Infrastructure

CRITICAL MISSION: Fix service startup issues that are preventing chat functionality from working in E2E tests.

This orchestrator follows CLAUDE.md "Real Everything" principle:
- NO MOCKS in E2E testing (Real Everything > Integration > Unit)
- Starts actual Docker services before E2E tests run
- Validates service health with proper timeouts
- Provides robust service connectivity for WebSocket agent events
- Ensures backend services (localhost:8000, 8001) are available

Business Value Justification (BVJ):
1. Segment: All tiers (Free to Enterprise) - $2M+ ARR protection
2. Business Goal: Ensure reliable E2E test infrastructure for chat functionality
3. Value Impact: Prevents production bugs in core agent orchestration features
4. Revenue Impact: Protects against agent failure cascades that cause enterprise churn
"""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import socket

# CLAUDE.md compliance: Use IsolatedEnvironment for all environment access
from shared.isolated_environment import get_env
from test_framework.docker_port_discovery import DockerPortDiscovery, ServicePortMapping

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealth:
    """Service health status."""
    service_name: str
    is_healthy: bool
    port: int
    response_time_ms: float
    error_message: Optional[str] = None
    last_check: Optional[float] = None


@dataclass
class OrchestrationConfig:
    """Service orchestration configuration."""
    environment: str = "test"
    startup_timeout: float = 60.0
    health_check_timeout: float = 5.0
    health_check_retries: int = 12
    health_check_interval: float = 2.0
    required_services: List[str] = None
    
    def __post_init__(self):
        if self.required_services is None:
            self.required_services = ["postgres", "redis", "backend", "auth"]


class ServiceOrchestrator:
    """
    Service orchestrator for E2E testing infrastructure.
    
    Ensures all required services are running and healthy before E2E tests execute.
    Follows "Real Everything" principle from CLAUDE.md - no mocks in E2E testing.
    """
    
    def __init__(self, config: Optional[OrchestrationConfig] = None):
        """Initialize service orchestrator."""
        self.config = config or OrchestrationConfig()
        self.port_discovery = DockerPortDiscovery(use_test_services=True)
        self.service_health: Dict[str, ServiceHealth] = {}
        self.started_services: Set[str] = set()
        
        # Track environment setup
        env = get_env()
        self.environment = env.get("TEST_ENV", "test")
        
    async def orchestrate_services(self) -> Tuple[bool, Dict[str, ServiceHealth]]:
        """
        Orchestrate all required services for E2E testing.
        
        Returns:
            Tuple of (success, service_health_report)
        """
        logger.info("🚀 Starting E2E Service Orchestration")
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Required services: {self.config.required_services}")
        
        start_time = time.time()
        
        try:
            # Phase 1: Check Docker availability
            if not await self._check_docker_availability():
                return False, self._create_failure_report("Docker not available")
            
            # Phase 2: Start missing services
            startup_success = await self._start_missing_services()
            if not startup_success:
                return False, self._create_failure_report("Service startup failed")
            
            # Phase 3: Wait for services to be healthy
            health_success = await self._wait_for_services_healthy()
            if not health_success:
                return False, self._create_failure_report("Service health checks failed")
            
            # Phase 4: Configure environment variables
            self._configure_service_environment()
            
            elapsed = time.time() - start_time
            logger.info(f"✅ E2E Service Orchestration completed successfully in {elapsed:.1f}s")
            
            return True, self.service_health
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ E2E Service Orchestration failed after {elapsed:.1f}s: {e}")
            return False, self._create_failure_report(f"Orchestration exception: {e}")
    
    async def _check_docker_availability(self) -> bool:
        """Check if Docker is available and docker-compose files exist."""
        # Check Docker daemon
        if not self.port_discovery.docker_available:
            logger.error("❌ Docker daemon not available - E2E tests require Docker")
            logger.error("💡 Fix: Start Docker Desktop or install Docker")
            return False
        
        # Check for docker-compose files
        compose_file = self._get_compose_file()
        if not compose_file:
            logger.error("❌ No docker-compose files found")
            logger.error("💡 Expected: docker-compose.test.yml or docker-compose.yml")
            return False
        
        logger.info(f"✅ Docker available, using compose file: {compose_file}")
        return True
    
    async def _start_missing_services(self) -> bool:
        """Start missing Docker services."""
        logger.info("🔄 Checking and starting required services...")
        
        # Check current service status
        port_mappings = self.port_discovery.discover_all_ports()
        missing_services = []
        
        for service in self.config.required_services:
            if service not in port_mappings or not port_mappings[service].is_available:
                missing_services.append(service)
        
        if not missing_services:
            logger.info("✅ All required services are already running")
            return True
        
        logger.info(f"⚡ Starting missing services: {missing_services}")
        
        # Attempt to start services via docker-compose
        compose_file = self._get_compose_file()
        if not compose_file:
            logger.error("❌ Cannot start services - no compose file found")
            return False
        
        try:
            # Build service names for compose command
            service_names = self._map_to_compose_services(missing_services)
            
            cmd = ["docker", "compose", "-f", compose_file, "up", "-d"] + service_names
            logger.info(f"🚀 Executing: {' '.join(cmd)}")
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                result.communicate(), 
                timeout=self.config.startup_timeout
            )
            
            if result.returncode == 0:
                logger.info("✅ Services started successfully")
                self.started_services.update(missing_services)
                
                # Wait a moment for services to initialize
                await asyncio.sleep(3)
                return True
            else:
                logger.error(f"❌ Service startup failed with return code {result.returncode}")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False
                
        except asyncio.TimeoutError:
            logger.error(f"❌ Service startup timed out after {self.config.startup_timeout}s")
            return False
        except Exception as e:
            logger.error(f"❌ Service startup failed: {e}")
            return False
    
    async def _wait_for_services_healthy(self) -> bool:
        """Wait for all required services to be healthy."""
        logger.info("🏥 Waiting for services to be healthy...")
        
        # Get current port mappings
        port_mappings = self.port_discovery.discover_all_ports()
        
        # Create health check tasks
        health_tasks = []
        for service in self.config.required_services:
            if service in port_mappings:
                task = self._check_service_health(service, port_mappings[service])
                health_tasks.append(task)
        
        if not health_tasks:
            logger.error("❌ No services to check - this shouldn't happen")
            return False
        
        # Wait for all health checks to complete
        try:
            health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
            
            # Process results
            all_healthy = True
            for i, result in enumerate(health_results):
                service = self.config.required_services[i]
                
                if isinstance(result, Exception):
                    logger.error(f"❌ Health check failed for {service}: {result}")
                    all_healthy = False
                    self.service_health[service] = ServiceHealth(
                        service_name=service,
                        is_healthy=False,
                        port=0,
                        response_time_ms=0,
                        error_message=str(result)
                    )
                else:
                    self.service_health[service] = result
                    if result.is_healthy:
                        logger.info(f"✅ {service} healthy on port {result.port} ({result.response_time_ms:.1f}ms)")
                    else:
                        logger.error(f"❌ {service} unhealthy: {result.error_message}")
                        all_healthy = False
            
            return all_healthy
            
        except Exception as e:
            logger.error(f"❌ Health check coordination failed: {e}")
            return False
    
    async def _check_service_health(self, service: str, mapping: ServicePortMapping) -> ServiceHealth:
        """Check health of a specific service."""
        start_time = time.time()
        
        for attempt in range(self.config.health_check_retries):
            try:
                if service in ["postgres", "redis", "clickhouse"]:
                    # Database services - check port connectivity
                    is_healthy = await self._check_port_connectivity(
                        mapping.host, mapping.external_port, self.config.health_check_timeout
                    )
                    if is_healthy:
                        response_time = (time.time() - start_time) * 1000
                        return ServiceHealth(
                            service_name=service,
                            is_healthy=True,
                            port=mapping.external_port,
                            response_time_ms=response_time,
                            last_check=time.time()
                        )
                
                elif service in ["backend", "auth", "frontend"]:
                    # HTTP services - check health endpoint
                    health_url = f"http://{mapping.host}:{mapping.external_port}/health"
                    is_healthy = await self._check_http_health(health_url, self.config.health_check_timeout)
                    if is_healthy:
                        response_time = (time.time() - start_time) * 1000
                        return ServiceHealth(
                            service_name=service,
                            is_healthy=True,
                            port=mapping.external_port,
                            response_time_ms=response_time,
                            last_check=time.time()
                        )
                
                # Wait before retry
                if attempt < self.config.health_check_retries - 1:
                    await asyncio.sleep(self.config.health_check_interval)
                    
            except Exception as e:
                logger.debug(f"Health check attempt {attempt + 1} failed for {service}: {e}")
        
        # All attempts failed
        response_time = (time.time() - start_time) * 1000
        return ServiceHealth(
            service_name=service,
            is_healthy=False,
            port=mapping.external_port,
            response_time_ms=response_time,
            error_message=f"Failed after {self.config.health_check_retries} attempts",
            last_check=time.time()
        )
    
    async def _check_port_connectivity(self, host: str, port: int, timeout: float) -> bool:
        """Check if a port is connectable."""
        try:
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False
    
    async def _check_http_health(self, url: str, timeout: float) -> bool:
        """Check HTTP health endpoint."""
        try:
            # Use aiohttp if available, otherwise try basic connectivity
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                        return response.status == 200
            except ImportError:
                # Fallback to port connectivity check
                from urllib.parse import urlparse
                parsed = urlparse(url)
                return await self._check_port_connectivity(parsed.hostname, parsed.port, timeout)
        except Exception:
            return False
    
    def _configure_service_environment(self) -> None:
        """Configure environment variables with discovered service ports."""
        env = get_env()
        port_mappings = self.port_discovery.discover_all_ports()
        
        # Set service URLs for E2E tests
        for service, mapping in port_mappings.items():
            if mapping.is_available:
                service_url = self._build_service_url(service, mapping)
                if service_url:
                    env_var = f"{service.upper()}_SERVICE_URL"
                    env.set(env_var, service_url, source="service_orchestrator")
                    logger.info(f"🔧 {env_var}={service_url}")
        
        # Set specific URLs needed by E2E tests
        if "backend" in port_mappings and port_mappings["backend"].is_available:
            backend_port = port_mappings["backend"].external_port
            env.set("BACKEND_URL", f"http://localhost:{backend_port}", source="service_orchestrator")
            env.set("WEBSOCKET_URL", f"ws://localhost:{backend_port}/ws", source="service_orchestrator")
        
        if "auth" in port_mappings and port_mappings["auth"].is_available:
            auth_port = port_mappings["auth"].external_port
            env.set("AUTH_SERVICE_URL", f"http://localhost:{auth_port}", source="service_orchestrator")
        
        # Set database URLs
        if "postgres" in port_mappings and port_mappings["postgres"].is_available:
            postgres_port = port_mappings["postgres"].external_port
            db_url = f"postgresql://test:test@localhost:{postgres_port}/netra_test"
            env.set("DATABASE_URL", db_url, source="service_orchestrator")
        
        if "redis" in port_mappings and port_mappings["redis"].is_available:
            redis_port = port_mappings["redis"].external_port
            redis_url = f"redis://localhost:{redis_port}/1"
            env.set("REDIS_URL", redis_url, source="service_orchestrator")
    
    def _build_service_url(self, service: str, mapping: ServicePortMapping) -> Optional[str]:
        """Build service URL from port mapping."""
        if service in ["backend", "auth", "frontend"]:
            return f"http://{mapping.host}:{mapping.external_port}"
        elif service == "postgres":
            return f"postgresql://test:test@{mapping.host}:{mapping.external_port}/netra_test"
        elif service == "redis":
            return f"redis://{mapping.host}:{mapping.external_port}/1"
        elif service == "clickhouse":
            return f"http://{mapping.host}:{mapping.external_port}"
        return None
    
    def _map_to_compose_services(self, services: List[str]) -> List[str]:
        """Map service names to docker-compose service names."""
        # Map generic service names to compose service names
        service_mapping = {
            "postgres": "test-postgres",
            "redis": "test-redis", 
            "clickhouse": "test-clickhouse",
            "backend": "backend",  # These might be built on-demand
            "auth": "auth",
            "frontend": "frontend"
        }
        
        return [service_mapping.get(service, service) for service in services]
    
    def _get_compose_file(self) -> Optional[str]:
        """Get the appropriate docker-compose file."""
        compose_files = [
            "docker-compose.test.yml",
            "docker-compose.yml"
        ]
        
        for file_path in compose_files:
            if Path(file_path).exists():
                return file_path
        
        return None
    
    def _create_failure_report(self, reason: str) -> Dict[str, ServiceHealth]:
        """Create failure report for orchestration."""
        failure_health = {}
        for service in self.config.required_services:
            failure_health[service] = ServiceHealth(
                service_name=service,
                is_healthy=False,
                port=0,
                response_time_ms=0,
                error_message=reason,
                last_check=time.time()
            )
        return failure_health
    
    async def cleanup_services(self) -> None:
        """Cleanup services that were started by orchestrator."""
        if not self.started_services:
            return
        
        logger.info(f"🧹 Cleaning up started services: {list(self.started_services)}")
        
        compose_file = self._get_compose_file()
        if compose_file:
            try:
                service_names = self._map_to_compose_services(list(self.started_services))
                cmd = ["docker", "compose", "-f", compose_file, "stop"] + service_names
                
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await asyncio.wait_for(result.communicate(), timeout=30)
                
                if result.returncode == 0:
                    logger.info("✅ Services stopped successfully")
                else:
                    logger.warning("⚠️ Some services may not have stopped cleanly")
                    
            except Exception as e:
                logger.warning(f"⚠️ Service cleanup failed: {e}")
    
    def get_health_report(self) -> str:
        """Generate comprehensive health report."""
        if not self.service_health:
            return "No service health data available"
        
        report_lines = [
            "\n" + "=" * 60,
            "E2E SERVICE ORCHESTRATION HEALTH REPORT", 
            "=" * 60,
            f"Environment: {self.environment}",
            f"Services checked: {len(self.service_health)}",
        ]
        
        healthy_count = sum(1 for health in self.service_health.values() if health.is_healthy)
        report_lines.append(f"Healthy services: {healthy_count}/{len(self.service_health)}")
        report_lines.append("")
        
        for service, health in self.service_health.items():
            status = "✅ HEALTHY" if health.is_healthy else "❌ UNHEALTHY"
            report_lines.append(f"{service:12} | {status:12} | Port: {health.port:5} | {health.response_time_ms:6.1f}ms")
            if health.error_message:
                report_lines.append(f"             | Error: {health.error_message}")
        
        report_lines.append("=" * 60)
        return "\n".join(report_lines)


async def orchestrate_e2e_services(
    required_services: Optional[List[str]] = None,
    timeout: float = 60.0
) -> Tuple[bool, ServiceOrchestrator]:
    """
    Convenient function to orchestrate E2E services.
    
    Args:
        required_services: List of required services (default: postgres, redis, backend, auth)
        timeout: Startup timeout in seconds
        
    Returns:
        Tuple of (success, orchestrator)
    """
    if required_services is None:
        required_services = ["postgres", "redis", "backend", "auth"]
    
    config = OrchestrationConfig(
        required_services=required_services,
        startup_timeout=timeout
    )
    
    orchestrator = ServiceOrchestrator(config)
    success, _ = await orchestrator.orchestrate_services()
    
    return success, orchestrator


# Pytest integration
async def pytest_orchestrate_services():
    """Pytest integration for service orchestration."""
    success, orchestrator = await orchestrate_e2e_services()
    
    if not success:
        logger.error(orchestrator.get_health_report())
        raise RuntimeError("E2E Service orchestration failed - cannot run tests")
    
    logger.info(orchestrator.get_health_report())
    return orchestrator