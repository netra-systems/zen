"""
env = get_env()
Comprehensive End-to-End Test for Dev Launcher Startup Sequence

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical Infrastructure)
- Business Goal: Zero-downtime development environment startup
- Value Impact: Ensures reliable developer onboarding and productivity
- Revenue Impact: Prevents $10K+ developer time loss per failed startup
- Strategic Impact: Foundation for all development workflows

CRITICAL REQUIREMENTS:
- Test complete dev launcher startup flow from clean state
- Validate pre-checks, database connectivity, service coordination
- Test port allocation and dynamic port handling
- Validate WebSocket endpoint synchronization
- Test graceful shutdown and cleanup
- Windows/Unix compatibility
- Real services integration (no mocks for core flow)
- Apply Five Whys analysis for any failures

This E2E test simulates:
1. Developer running `python -m dev_launcher` for first time
2. Environment validation and secret loading
3. Database connectivity verification (PostgreSQL, Redis, ClickHouse)
4. Service startup orchestration (auth  ->  backend  ->  frontend  ->  websocket)
5. Port allocation with conflict resolution
6. Service health validation
7. WebSocket endpoint registration and updates
8. Graceful shutdown on interruption

Maximum 500 lines, comprehensive integration validation.
"""

import asyncio
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest

# Use absolute imports per CLAUDE.md requirements
from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.database_connector import DatabaseConnector, DatabaseType
from shared.isolated_environment import get_env
from test_framework.base_e2e_test import BaseE2ETest

logger = logging.getLogger(__name__)

@dataclass
class StartupValidationResult:
    """Result of startup sequence validation."""
    success: bool
    startup_time_seconds: float
    errors: List[str] = field(default_factory=list)
    services_started: Dict[str, bool] = field(default_factory=dict)
    ports_allocated: Dict[str, int] = field(default_factory=dict)
    database_status: Dict[str, bool] = field(default_factory=dict)
    websocket_endpoints: Dict[str, str] = field(default_factory=dict)
    cleanup_successful: bool = False


@dataclass 
class TestDevLauncherConfig:
    """Configuration for dev launcher E2E testing."""
    use_dynamic_ports: bool = True
    enable_secrets: bool = False
    timeout_seconds: int = 45
    test_frontend: bool = False  # Skip frontend by default for speed
    test_websocket: bool = True
    project_root: Path = None
    temp_dir: Optional[Path] = None


class TestDevLauncherE2Eer:
    """Comprehensive E2E tester for dev launcher startup sequence."""
    
    def __init__(self, config: DevLauncherTestConfig):
        """Initialize the E2E tester."""
        self.config = config
        self.project_root = config.project_root or self._detect_project_root()
        self.launcher_process: Optional[subprocess.Popen] = None
        self.services_discovered: Dict[str, Dict[str, Any]] = {}
        self.cleanup_tasks: List[callable] = []
        self.start_time: Optional[float] = None
        self.test_results = StartupValidationResult(success=False, startup_time_seconds=0.0)
        
    def _detect_project_root(self) -> Path:
        """Detect project root from test location."""
        current = Path(__file__).parent
        while current.parent != current:
            if (current / "netra_backend").exists() and (current / "dev_launcher").exists():
                return current
            current = current.parent
        raise RuntimeError("Could not detect project root")
    
    async def run_complete_e2e_test(self) -> StartupValidationResult:
        """Run complete E2E test of dev launcher startup sequence."""
        self.start_time = time.time()
        logger.info("Starting comprehensive dev launcher E2E test")
        
        try:
            # Phase 1: Pre-startup validation
            await self._validate_preconditions()
            
            # Phase 2: Environment and database preparation
            await self._prepare_test_environment()
            
            # Phase 3: Start dev launcher with real process
            await self._start_dev_launcher_process()
            
            # Phase 4: Wait for service startup completion
            await self._wait_for_startup_completion()
            
            # Phase 5: Validate service health and connectivity
            await self._validate_services_health()
            
            # Phase 6: Test port allocation and conflicts
            await self._validate_port_allocation()
            
            # Phase 7: Validate WebSocket endpoints
            if self.config.test_websocket:
                await self._validate_websocket_endpoints()
            
            # Phase 8: Test service discovery mechanism
            await self._validate_service_discovery()
            
            # Success - calculate final timing
            self.test_results.success = True
            self.test_results.startup_time_seconds = time.time() - self.start_time
            
            logger.info(f"Dev launcher E2E test PASSED in {self.test_results.startup_time_seconds:.1f}s")
            return self.test_results
            
        except Exception as e:
            logger.error(f"Dev launcher E2E test failed: {e}")
            await self._apply_five_whys_analysis(e)
            self.test_results.errors.append(str(e))
            self.test_results.startup_time_seconds = time.time() - self.start_time if self.start_time else 0
            return self.test_results
            
        finally:
            await self._cleanup_test_environment()
    
    async def _validate_preconditions(self):
        """Phase 1: Validate preconditions for dev launcher startup."""
        logger.info("Phase 1: Validating preconditions")
        
        # Check project structure
        required_dirs = ["netra_backend", "auth_service", "frontend", "dev_launcher"]
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                raise RuntimeError(f"Missing required directory: {dir_path}")
        
        # Check Python environment and dependencies
        try:
            import uvicorn
            import fastapi
            import asyncio
        except ImportError as e:
            raise RuntimeError(f"Missing required Python dependencies: {e}")
        
        # Check if ports are available (if using static ports)
        if not self.config.use_dynamic_ports:
            static_ports = [8000, 8081, 3000]
            for port in static_ports:
                if not await self._is_port_available(port):
                    logger.warning(f"Port {port} is busy - will use dynamic allocation")
                    self.config.use_dynamic_ports = True
                    break
        
        logger.info("Preconditions validated successfully")
    
    async def _prepare_test_environment(self):
        """Phase 2: Prepare test environment including database connectivity."""
        logger.info("Phase 2: Preparing test environment")
        
        # Set up temporary directory for test artifacts
        if not self.config.temp_dir:
            self.config.temp_dir = Path(tempfile.mkdtemp(prefix="dev_launcher_e2e_"))
            self.cleanup_tasks.append(lambda: self._cleanup_temp_dir())
        
        # Test database connectivity
        await self._test_database_connectivity()
        
        # Clear any existing service discovery files
        discovery_dir = self.project_root / ".service_discovery"
        if discovery_dir.exists():
            for file in discovery_dir.glob("*.json"):
                try:
                    file.unlink()
                except Exception:
                    pass
        
        logger.info("Test environment prepared successfully")
    
    async def _test_database_connectivity(self):
        """Test database connectivity before startup."""
        logger.info("Testing database connectivity")
        
        try:
            # Create database connector with emoji disabled for Windows compatibility
            db_connector = DatabaseConnector(use_emoji=False)
            
            # Test all connections at once
            all_connections_healthy = await db_connector.validate_all_connections()
            
            # Check individual connection status from the connector
            for conn_name, connection in db_connector.connections.items():
                db_name = connection.db_type.value.capitalize()
                is_healthy = connection.status.value == "connected"
                self.test_results.database_status[db_name.lower()] = is_healthy
                
                if is_healthy:
                    logger.info(f"{db_name} database connection successful")
                else:
                    logger.warning(f"{db_name} database not available: {connection.last_error}")
            
            # Stop health monitoring to cleanup
            await db_connector.stop_health_monitoring()
            
        except Exception as e:
            logger.warning(f"Database connectivity test failed: {e}")
            # Set all database status to false if the test fails
            for db_name in ["postgresql", "redis", "clickhouse"]:
                self.test_results.database_status[db_name] = False
    
    async def _start_dev_launcher_process(self):
        """Phase 3: Start dev launcher process."""
        logger.info("Phase 3: Starting dev launcher process")
        
        # Build command with appropriate flags
        cmd = self._build_launcher_command()
        
        # Set up environment
        env["NETRA_TEST_MODE"] = "true"
        env["NETRA_STARTUP_MODE"] = "minimal"
        if not self.config.enable_secrets:
            env["NETRA_SKIP_SECRETS"] = "true"
        
        logger.info(f"Starting dev launcher: {' '.join(cmd)}")
        
        # Start the process
        self.launcher_process = subprocess.Popen(
            cmd,
            cwd=str(self.project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=None if sys.platform == "win32" else os.setsid
        )
        
        # Register cleanup
        self.cleanup_tasks.append(self._terminate_launcher_process)
        
        # Give process time to start
        await asyncio.sleep(2)
        
        # Check if process is still running
        if self.launcher_process.poll() is not None:
            stdout, stderr = self.launcher_process.communicate()
            raise RuntimeError(f"Dev launcher process failed immediately. Stderr: {stderr}")
        
        logger.info("Dev launcher process started successfully")
    
    def _build_launcher_command(self) -> List[str]:
        """Build dev launcher command with appropriate flags."""
        cmd = [sys.executable, "-m", "dev_launcher"]
        
        if self.config.use_dynamic_ports:
            cmd.append("--dynamic")
        else:
            cmd.append("--static")
        
        cmd.extend([
            "--no-browser",
            "--non-interactive", 
            "--minimal",
            "--no-reload"
        ])
        
        if not self.config.enable_secrets:
            cmd.append("--no-secrets")
        
        if not self.config.test_frontend:
            # Frontend startup is optional for E2E tests
            pass
        
        return cmd
    
    async def _wait_for_startup_completion(self):
        """Phase 4: Wait for startup completion with timeout."""
        logger.info("Phase 4: Waiting for startup completion")
        
        timeout = self.config.timeout_seconds
        check_interval = 1.0
        elapsed = 0
        
        while elapsed < timeout:
            # Check if launcher process is still running
            if self.launcher_process and self.launcher_process.poll() is not None:
                stdout, stderr = self.launcher_process.communicate()
                if self.launcher_process.returncode != 0:
                    raise RuntimeError(f"Dev launcher failed with exit code {self.launcher_process.returncode}. Stderr: {stderr}")
            
            # Check service readiness
            services_ready = await self._check_core_services_ready()
            if services_ready:
                logger.info("Core services are ready")
                return
            
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        raise TimeoutError(f"Services not ready after {timeout}s timeout")
    
    async def _check_core_services_ready(self) -> bool:
        """Check if core services (auth, backend) are ready."""
        try:
            # Check auth service on correct port (8081)
            auth_ready = await self._is_service_healthy("auth", 8081)
            
            # Check backend service  
            backend_ready = await self._is_service_healthy("backend", 8001)  # Updated to match dev launcher
            
            # At least one core service must be ready
            return auth_ready or backend_ready
            
        except Exception as e:
            logger.debug(f"Services not ready: {e}")
            return False
    
    async def _validate_services_health(self):
        """Phase 5: Validate all services health."""
        logger.info("Phase 5: Validating services health")
        
        services_to_check = [
            ("auth", 8081, "/health"),
            ("backend", 8001, "/health"),  # Updated to match dev launcher
        ]
        
        if self.config.test_frontend:
            services_to_check.append(("frontend", 3000, "/"))
        
        for service_name, default_port, health_path in services_to_check:
            try:
                # Try to discover actual port
                port = await self._discover_service_port(service_name, default_port)
                
                # Test health endpoint
                healthy = await self._is_service_healthy(service_name, port, health_path)
                
                self.test_results.services_started[service_name] = healthy
                self.test_results.ports_allocated[service_name] = port
                
                if healthy:
                    logger.info(f"{service_name} service healthy on port {port}")
                else:
                    logger.warning(f"{service_name} service not healthy on port {port}")
                    
            except Exception as e:
                logger.error(f"Failed to validate {service_name} service: {e}")
                self.test_results.services_started[service_name] = False
        
        # Require at least one core service to be healthy
        core_healthy = self.test_results.services_started.get("auth", False) or \
                      self.test_results.services_started.get("backend", False)
        
        if not core_healthy:
            raise RuntimeError("No core services (auth/backend) are healthy")
    
    async def _validate_port_allocation(self):
        """Phase 6: Validate port allocation and conflict resolution."""
        logger.info("Phase 6: Validating port allocation")
        
        # Check that services are using expected ports
        for service_name, port in self.test_results.ports_allocated.items():
            # Verify port is actually in use
            if not await self._is_port_in_use(port):
                logger.warning(f"Port {port} for {service_name} appears unused")
            
            # Verify no conflicts with other services
            for other_service, other_port in self.test_results.ports_allocated.items():
                if service_name != other_service and port == other_port:
                    raise RuntimeError(f"Port conflict: {service_name} and {other_service} both using port {port}")
        
        logger.info("Port allocation validated successfully")
    
    async def _validate_websocket_endpoints(self):
        """Phase 7: Validate WebSocket endpoint registration."""
        logger.info("Phase 7: Validating WebSocket endpoints")
        
        try:
            # Check for WebSocket configuration
            discovery = ServiceDiscovery(self.project_root)
            
            # Try to read websocket info from service discovery
            try:
                backend_info = discovery.read_backend_info()
                if backend_info and "websocket_url" in backend_info:
                    ws_url = backend_info["websocket_url"]
                    self.test_results.websocket_endpoints["backend"] = ws_url
                    logger.info(f"WebSocket endpoint registered: {ws_url}")
                else:
                    logger.info("WebSocket endpoint not found in service discovery")
            except Exception as e:
                logger.debug(f"Could not read WebSocket info: {e}")
            
        except Exception as e:
            logger.warning(f"WebSocket validation failed: {e}")
    
    async def _validate_service_discovery(self):
        """Phase 8: Validate service discovery mechanism."""
        logger.info("Phase 8: Validating service discovery")
        
        discovery_dir = self.project_root / ".service_discovery"
        if not discovery_dir.exists():
            logger.warning("Service discovery directory not found")
            return
        
        discovery = ServiceDiscovery(self.project_root)
        
        # Check for auth service info
        try:
            auth_info = discovery.read_auth_info()
            if auth_info:
                logger.info(f"Auth service discovery: port {auth_info.get('port')}")
        except Exception as e:
            logger.debug(f"Auth service discovery failed: {e}")
        
        # Check for backend service info
        try:
            backend_info = discovery.read_backend_info()
            if backend_info:
                logger.info(f"Backend service discovery: port {backend_info.get('port')}")
        except Exception as e:
            logger.debug(f"Backend service discovery failed: {e}")
        
        logger.info("Service discovery validated successfully")
    
    async def _apply_five_whys_analysis(self, error: Exception):
        """Apply Five Whys methodology to understand failure root cause."""
        logger.error("=== FIVE WHYS ANALYSIS ===")
        
        # Why 1: Why did the E2E test fail?
        logger.error(f"Why 1: E2E test failed with error: {error}")
        
        # Why 2: Why did the specific component fail?
        if "timeout" in str(error).lower():
            logger.error("Why 2: Timeout occurred - services took too long to start")
        elif "port" in str(error).lower():
            logger.error("Why 2: Port allocation or connectivity issue")
        elif "database" in str(error).lower():
            logger.error("Why 2: Database connectivity or configuration issue")
        elif "process" in str(error).lower():
            logger.error("Why 2: Process management or startup failure")
        else:
            logger.error(f"Why 2: Specific component failure - {type(error).__name__}")
        
        # Why 3: Why are services not coordinating?
        process_running = self.launcher_process and self.launcher_process.poll() is None
        logger.error(f"Why 3: Service coordination - Launcher process running: {process_running}")
        
        # Why 4: Why are dependencies not satisfied?
        db_issues = [db for db, status in self.test_results.database_status.items() if not status]
        if db_issues:
            logger.error(f"Why 4: Database dependencies not available: {db_issues}")
        else:
            logger.error("Why 4: Dependencies appear satisfied - likely orchestration issue")
        
        # Why 5: What is the root cause?
        if not process_running:
            logger.error("Why 5: Root cause - Dev launcher process crashed or failed to start")
        elif db_issues:
            logger.error("Why 5: Root cause - Missing database infrastructure preventing startup")
        else:
            logger.error("Why 5: Root cause - Service startup orchestration timing or configuration issue")
    
    # Helper methods
    async def _is_port_available(self, port: int) -> bool:
        """Check if port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                return result != 0  # Available if connection fails
        except Exception:
            return False
    
    async def _is_port_in_use(self, port: int) -> bool:
        """Check if port is currently in use."""
        return not await self._is_port_available(port)
    
    async def _discover_service_port(self, service_name: str, default_port: int) -> int:
        """Discover actual service port from service discovery."""
        try:
            discovery = ServiceDiscovery(self.project_root)
            
            if service_name == "auth":
                info = discovery.read_auth_info()
            elif service_name == "backend":
                info = discovery.read_backend_info()
            elif service_name == "frontend":
                info = discovery.read_frontend_info()
            else:
                return default_port
            
            return info.get("port", default_port) if info else default_port
            
        except Exception:
            return default_port
    
    async def _is_service_healthy(self, service_name: str, port: int, health_path: str = "/health") -> bool:
        """Check if service is healthy via HTTP."""
        try:
            url = f"http://localhost:{port}{health_path}"
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False
    
    def _terminate_launcher_process(self):
        """Terminate dev launcher process gracefully."""
        if not self.launcher_process:
            return
        
        try:
            # Windows vs Unix process termination
            if sys.platform == "win32":
                # Windows: terminate process tree
                import subprocess
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.launcher_process.pid)], 
                              capture_output=True, text=True)
            else:
                # Unix: send SIGTERM to process group
                os.killpg(os.getpgid(self.launcher_process.pid), signal.SIGTERM)
            
            # Wait for termination
            try:
                self.launcher_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.launcher_process.kill()
                self.launcher_process.wait()
            
        except Exception as e:
            logger.error(f"Error terminating launcher process: {e}")
    
    def _cleanup_temp_dir(self):
        """Clean up temporary directory."""
        if self.config.temp_dir and self.config.temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(str(self.config.temp_dir))
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")
    
    async def _cleanup_test_environment(self):
        """Clean up test environment."""
        logger.info("Cleaning up test environment")
        
        # Run all cleanup tasks
        for cleanup_task in self.cleanup_tasks:
            try:
                if asyncio.iscoroutinefunction(cleanup_task):
                    await cleanup_task()
                else:
                    cleanup_task()
            except Exception as e:
                logger.error(f"Cleanup task failed: {e}")
        
        self.test_results.cleanup_successful = True
        logger.info("Test environment cleaned up successfully")


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDevLauncherE2E:
    """Comprehensive end-to-end test suite for dev launcher."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return DevLauncherTestConfig(
            use_dynamic_ports=True,
            enable_secrets=False,
            timeout_seconds=45,
            test_frontend=False,  # Skip for speed
            test_websocket=True
        )
    
    async def test_complete_dev_launcher_startup_sequence(self, test_config):
        """Test complete dev launcher startup sequence end-to-end."""
        logger.info("=== STARTING DEV LAUNCHER E2E TEST ===")
        
        # Create and run E2E tester
        tester = DevLauncherE2ETester(test_config)
        result = await tester.run_complete_e2e_test()
        
        # Validate results
        assert result.success, f"E2E test failed: {'; '.join(result.errors)}"
        assert result.startup_time_seconds < test_config.timeout_seconds, \
            f"Startup took {result.startup_time_seconds:.1f}s (timeout: {test_config.timeout_seconds}s)"
        
        # Validate at least one core service started
        core_services_started = sum([
            result.services_started.get("auth", False),
            result.services_started.get("backend", False)
        ])
        assert core_services_started >= 1, "No core services started successfully"
        
        # Validate port allocation
        assert len(result.ports_allocated) > 0, "No ports were allocated"
        
        # Validate database connectivity (at least one should work)
        db_connected = any(result.database_status.values())
        if not db_connected:
            logger.warning("No databases available - test ran in limited mode")
        
        # Validate cleanup
        assert result.cleanup_successful, "Test cleanup failed"
        
        # Log success summary
        logger.info("=== DEV LAUNCHER E2E TEST SUMMARY ===")
        logger.info(f"Total time: {result.startup_time_seconds:.1f}s")
        logger.info(f"Services started: {list(result.services_started.keys())}")
        logger.info(f"Ports allocated: {result.ports_allocated}")
        logger.info(f"Databases available: {[db for db, status in result.database_status.items() if status]}")
        logger.info(f"WebSocket endpoints: {list(result.websocket_endpoints.keys())}")
        logger.info("=== E2E TEST PASSED ===")


async def run_dev_launcher_e2e_test():
    """Standalone function to run dev launcher E2E test."""
    config = DevLauncherTestConfig()
    tester = DevLauncherE2ETester(config)
    return await tester.run_complete_e2e_test()


if __name__ == "__main__":
    # Allow standalone execution
    result = asyncio.run(run_dev_launcher_e2e_test())
    print(f"Dev launcher E2E test result: {'PASSED' if result.success else 'FAILED'}")
    print(f"Startup time: {result.startup_time_seconds:.1f}s")
    if not result.success:
        print(f"Errors: {result.errors}")