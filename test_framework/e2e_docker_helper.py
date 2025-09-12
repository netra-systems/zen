"""
E2E Docker Helper - The ONE way to run E2E tests with Docker
===========================================================

CRITICAL: This is the ONLY way to run E2E tests with Docker.
- NO fallbacks
- NO alternatives 
- Docker or FAIL
- Uses EXACTLY docker-compose.alpine-test.yml
- Clear setup and teardown
- Predictable test isolation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability - reliable E2E tests enable confident deployments
- Value Impact: Eliminates random test failures that block releases
- Strategic Impact: Enables CI/CD reliability and faster development velocity
"""

import asyncio
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from shared.isolated_environment import get_env
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType

logger = logging.getLogger(__name__)
env = get_env()


class E2EDockerHelper:
    """
    The ONE way to run E2E tests with Docker.
    
    CRITICAL PRINCIPLES:
    1. ALWAYS uses docker-compose.alpine-test.yml
    2. NO fallback logic - Docker or FAIL
    3. Clear error messages if Docker not available
    4. Predictable test isolation between runs
    5. Dedicated test ports to avoid conflicts
    """
    
    # Dedicated E2E test ports - different from dev/staging
    E2E_PORTS = {
        "ALPINE_TEST_POSTGRES_PORT": "5435",
        "ALPINE_TEST_REDIS_PORT": "6382", 
        "ALPINE_TEST_CLICKHOUSE_HTTP": "8126",
        "ALPINE_TEST_CLICKHOUSE_TCP": "9003",
        "ALPINE_TEST_BACKEND_PORT": "8002",
        "ALPINE_TEST_AUTH_PORT": "8083",
        "ALPINE_TEST_FRONTEND_PORT": "3002"
    }
    
    def __init__(self, test_id: Optional[str] = None):
        """
        Initialize E2E Docker Helper.
        
        Args:
            test_id: Optional test identifier for isolation
        """
        self.test_id = test_id or f"e2e-{int(time.time())}"
        self.project_name = f"netra-e2e-test-{self.test_id}"
        self.compose_file = None
        self.service_urls = {}
        self.manager = None
        
        # Validate Docker availability immediately
        self._validate_docker_or_fail()
    
    def _validate_docker_or_fail(self):
        """Validate Docker is available or raise clear error."""
        try:
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("Docker command failed")
                
            # Check if Docker daemon is running
            result = subprocess.run(
                ["docker", "info"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "Docker daemon is not running. Please start Docker Desktop or Docker daemon and try again."
                )
                
        except (subprocess.TimeoutExpired, FileNotFoundError, RuntimeError) as e:
            raise RuntimeError(
                f" FAIL:  DOCKER REQUIRED: E2E tests require Docker to be installed and running.\n"
                f"   Error: {e}\n"
                f"   Please:\n"
                f"   1. Install Docker Desktop (Windows/Mac) or Docker Engine (Linux)\n"
                f"   2. Start the Docker daemon\n"
                f"   3. Run 'docker --version' to verify installation\n"
                f"   4. Try running E2E tests again\n"
                f"   NO FALLBACK AVAILABLE - Docker is mandatory for E2E tests."
            )
    
    async def setup_e2e_environment(self, timeout: int = 180) -> Dict[str, str]:
        """
        Setup Docker environment for E2E tests.
        
        Args:
            timeout: Maximum time to wait for services (default: 180s)
            
        Returns:
            Dictionary of service URLs for tests
            
        Raises:
            RuntimeError: If setup fails
        """
        logger.info(f"[U+1F680] Setting up E2E environment (test_id: {self.test_id})")
        
        try:
            # 1. Validate Docker available
            self._validate_docker_or_fail()
            
            # 2. Use EXACTLY docker-compose.alpine-test.yml
            project_root = Path(env.get("PROJECT_ROOT", Path(__file__).parent.parent))
            self.compose_file = project_root / "docker-compose.alpine-test.yml"
            
            if not self.compose_file.exists():
                raise RuntimeError(
                    f" FAIL:  CRITICAL: Required E2E compose file not found: {self.compose_file}\n"
                    f"   E2E tests require docker-compose.alpine-test.yml to exist.\n"
                    f"   Please ensure the file exists in the project root."
                )
            
            logger.info(f"   [U+1F4E6] Using compose file: {self.compose_file}")
            
            # 3. Clean previous test artifacts
            await self._clean_previous_artifacts()
            
            # 4. Start services with health checks
            await self._start_services_with_health_checks(timeout)
            
            # 5. Return service URLs
            self.service_urls = {
                "backend": f"http://localhost:{self.E2E_PORTS['ALPINE_TEST_BACKEND_PORT']}",
                "auth": f"http://localhost:{self.E2E_PORTS['ALPINE_TEST_AUTH_PORT']}",
                "frontend": f"http://localhost:{self.E2E_PORTS['ALPINE_TEST_FRONTEND_PORT']}",
                "websocket": f"ws://localhost:{self.E2E_PORTS['ALPINE_TEST_BACKEND_PORT']}/ws",
                "postgres": f"postgresql://test:test@localhost:{self.E2E_PORTS['ALPINE_TEST_POSTGRES_PORT']}/netra_test",
                "redis": f"redis://localhost:{self.E2E_PORTS['ALPINE_TEST_REDIS_PORT']}/0"
            }
            
            logger.info(" PASS:  E2E environment ready!")
            logger.info(f"   Backend: {self.service_urls['backend']}")
            logger.info(f"   Auth: {self.service_urls['auth']}")
            logger.info(f"   WebSocket: {self.service_urls['websocket']}")
            
            return self.service_urls
            
        except Exception as e:
            logger.error(f" FAIL:  E2E environment setup failed: {e}")
            # Attempt cleanup on failure
            await self.teardown_e2e_environment()
            raise RuntimeError(f"E2E environment setup failed: {e}")
    
    async def _clean_previous_artifacts(self):
        """Clean test data and stale containers using reliability patches."""
        logger.info("   [U+1F9F9] Cleaning previous test artifacts...")
        
        try:
            # Use reliability patches for comprehensive cleanup
            from test_framework.docker_reliability_patches import DockerReliabilityPatcher
            
            patcher = DockerReliabilityPatcher("e2e")
            
            # Check and resolve port conflicts
            conflicts = patcher.check_port_conflicts()
            if conflicts:
                logger.warning(f"   Found {len(conflicts)} port conflicts, resolving...")
                if not patcher.resolve_port_conflicts(force_kill=True):
                    logger.error("    FAIL:  Could not resolve all port conflicts")
                    raise RuntimeError("Port conflicts prevent E2E Docker setup")
            
            # Clean up stale resources
            cleanup_results = {
                "containers": patcher.clean_stale_containers(max_age_hours=1),
                "volumes": patcher.clean_stale_volumes(max_age_hours=1), 
                "networks": patcher.clean_stale_networks()
            }
            
            logger.info(f"   Cleaned: {cleanup_results['containers']} containers, "
                       f"{cleanup_results['volumes']} volumes, "
                       f"{cleanup_results['networks']} networks")
            
            # Clean up project-specific resources
            test_env = os.environ.copy()
            test_env.update(self.E2E_PORTS)
            test_env["COMPOSE_PROJECT_NAME"] = self.project_name
            
            # Stop and remove any existing containers with this project name
            subprocess.run([
                "docker-compose", "-f", str(self.compose_file),
                "-p", self.project_name,
                "down", "-v", "--remove-orphans"
            ], capture_output=True, timeout=60, env=test_env)
            
            logger.info("    PASS:  Previous artifacts cleaned")
            
        except Exception as e:
            logger.warning(f"    WARNING: [U+FE0F]  Could not clean all previous artifacts: {e}")
            # Don't fail setup for cleanup issues
    
    async def _start_services_with_health_checks(self, timeout: int):
        """Start services and wait for them to be healthy."""
        logger.info("   [U+1F528] Building and starting E2E services...")
        
        test_env = os.environ.copy()
        test_env.update(self.E2E_PORTS)
        test_env["COMPOSE_PROJECT_NAME"] = self.project_name
        test_env["DOCKER_BUILDKIT"] = "1"  # Enable BuildKit for faster builds
        
        # Build and start services
        cmd = [
            "docker-compose", "-f", str(self.compose_file),
            "-p", self.project_name,
            "up", "-d", "--build"
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout, 
                env=test_env
            )
            
            if result.returncode != 0:
                logger.error(f" FAIL:  Failed to start E2E services:")
                logger.error(f"   Command: {' '.join(cmd)}")
                logger.error(f"   stderr: {result.stderr}")
                logger.error(f"   stdout: {result.stdout}")
                raise RuntimeError(f"Docker compose failed: {result.stderr}")
            
            logger.info("    PASS:  Services started, waiting for health checks...")
            
            # Wait for services to be healthy
            await self._wait_for_services_healthy(test_env, timeout)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"E2E service startup timed out after {timeout}s")
    
    async def _wait_for_services_healthy(self, test_env: Dict[str, str], timeout: int):
        """Wait for all services to be healthy."""
        required_services = [
            "alpine-test-postgres", 
            "alpine-test-redis", 
            "alpine-test-clickhouse", 
            "alpine-test-backend", 
            "alpine-test-auth", 
            "alpine-test-frontend"
        ]
        
        start_time = time.time()
        healthy_services = set()
        
        logger.info("   [U+23F3] Waiting for services to become healthy...")
        
        while time.time() - start_time < timeout:
            try:
                # Check service health
                result = subprocess.run([
                    "docker-compose", "-f", str(self.compose_file),
                    "-p", self.project_name,
                    "ps", "--format", "json"
                ], capture_output=True, text=True, timeout=10, env=test_env)
                
                if result.returncode == 0:
                    import json
                    current_healthy = set()
                    
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            try:
                                container = json.loads(line)
                                # Check if healthy or running (for services without health checks)
                                if (container.get('Health', '').lower() == 'healthy' or 
                                    (container.get('State', '').lower() == 'running' and 
                                     'healthy' in container.get('Status', '').lower())):
                                    current_healthy.add(container['Service'])
                            except (json.JSONDecodeError, KeyError):
                                continue
                    
                    # Check if all required services are healthy
                    if current_healthy.issuperset(required_services):
                        logger.info("    PASS:  All E2E services are healthy")
                        return
                    
                    # Show progress for newly healthy services
                    newly_healthy = current_healthy - healthy_services
                    if newly_healthy:
                        logger.info(f"   [U+1F7E2] Healthy: {', '.join(newly_healthy)}")
                        healthy_services.update(newly_healthy)
                
                await asyncio.sleep(3)  # Check every 3 seconds
                
            except Exception as e:
                logger.debug(f"Health check error: {e}")
                await asyncio.sleep(3)
        
        # If we reach here, timeout occurred
        await self._collect_failure_logs(test_env)
        raise RuntimeError(f"Services failed to become healthy within {timeout}s")
    
    async def _collect_failure_logs(self, test_env: Dict[str, str]):
        """Collect logs from failed services for debugging."""
        try:
            logger.error(" SEARCH:  Collecting failure logs for debugging...")
            
            result = subprocess.run([
                "docker-compose", "-f", str(self.compose_file),
                "-p", self.project_name,
                "logs", "--tail=20"
            ], capture_output=True, text=True, timeout=30, env=test_env)
            
            if result.stdout:
                logger.error("Failed E2E Service Logs:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.error(f"   {line}")
            
        except Exception as e:
            logger.warning(f"Could not collect failure logs: {e}")
    
    async def teardown_e2e_environment(self):
        """Clean teardown after tests."""
        if not self.compose_file:
            logger.info("No E2E environment to tear down")
            return
        
        try:
            logger.info(f"[U+1F9F9] Tearing down E2E environment (test_id: {self.test_id})")
            
            test_env = os.environ.copy()
            test_env.update(self.E2E_PORTS)
            test_env["COMPOSE_PROJECT_NAME"] = self.project_name
            
            # Stop and remove containers
            result = subprocess.run([
                "docker-compose", "-f", str(self.compose_file),
                "-p", self.project_name,
                "down", "-v", "--remove-orphans"
            ], capture_output=True, text=True, timeout=60, env=test_env)
            
            if result.returncode != 0:
                logger.warning(f"Warning during teardown: {result.stderr}")
            else:
                logger.info("    PASS:  E2E environment cleaned up")
            
        except Exception as e:
            logger.warning(f"Warning during E2E teardown: {e}")
        finally:
            # Clean up internal state
            self.service_urls = {}
    
    def get_service_urls(self) -> Dict[str, str]:
        """Get service URLs for tests."""
        if not self.service_urls:
            raise RuntimeError(
                "E2E environment not set up. Call setup_e2e_environment() first."
            )
        return self.service_urls
    
    def get_service_url(self, service: str) -> str:
        """Get URL for a specific service."""
        urls = self.get_service_urls()
        if service not in urls:
            available = ', '.join(urls.keys())
            raise ValueError(f"Unknown service '{service}'. Available: {available}")
        return urls[service]


# Convenience functions for direct usage
async def setup_e2e_docker_environment(test_id: Optional[str] = None, timeout: int = 180) -> Tuple[E2EDockerHelper, Dict[str, str]]:
    """
    Convenience function to setup E2E Docker environment.
    
    Args:
        test_id: Optional test identifier
        timeout: Setup timeout in seconds
        
    Returns:
        Tuple of (helper_instance, service_urls)
    """
    helper = E2EDockerHelper(test_id=test_id)
    service_urls = await helper.setup_e2e_environment(timeout=timeout)
    return helper, service_urls


async def teardown_e2e_docker_environment(helper: E2EDockerHelper):
    """
    Convenience function to teardown E2E Docker environment.
    
    Args:
        helper: E2EDockerHelper instance to teardown
    """
    await helper.teardown_e2e_environment()


# Pytest integration
def pytest_e2e_docker_fixture():
    """Pytest fixture factory for E2E Docker environment."""
    import pytest
    
    @pytest.fixture(scope="session")
    async def e2e_docker_environment():
        """Pytest fixture that provides E2E Docker environment."""
        helper, service_urls = await setup_e2e_docker_environment()
        
        yield helper, service_urls
        
        await teardown_e2e_docker_environment(helper)
    
    return e2e_docker_environment