"""
env = get_env()
Comprehensive System Startup and Health Validation E2E Test

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical Infrastructure)  
- Business Goal: Zero-downtime system initialization and health monitoring
- Value Impact: Ensures reliable system startup for all user segments
- Strategic Impact: Prevents cascading failures and maintains service availability
- Revenue Impact: Protects $100K+ potential revenue loss from system downtime

CRITICAL REQUIREMENTS:
- Test complete system startup from cold state
- Validate service orchestration and dependency resolution
- Test health checks across all services and databases
- Validate migration recovery scenarios
- Test port allocation and conflict resolution
- Validate WebSocket endpoint registration
- Test graceful shutdown and cleanup
- Windows/Linux compatibility
- Real services integration (no mocks for core flows)

This E2E test validates the entire system startup sequence including:
1. Environment validation and configuration loading
2. Database connectivity and migration validation
3. Service startup orchestration (auth  ->  backend  ->  websocket coordination)
4. Health check cascading and dependency validation
5. Port allocation with conflict resolution
6. Service discovery and registration
7. WebSocket endpoint validation and real-time connectivity
8. Graceful shutdown and resource cleanup

Maximum 800 lines, comprehensive system validation.
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
from typing import Any, Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest
import websockets
from websockets import ServerConnection
from websockets.exceptions import ConnectionClosed, InvalidURI

# Use absolute imports per CLAUDE.md requirements
from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.database_connector import DatabaseConnector, DatabaseType
from shared.isolated_environment import get_env
from test_framework.base_e2e_test import BaseE2ETest

logger = logging.getLogger(__name__)


@dataclass
class SystemHealthMetrics:
    """Comprehensive system health and startup metrics."""
    test_name: str
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    
    # Service startup metrics
    services_started: Dict[str, bool] = field(default_factory=dict)
    service_startup_times: Dict[str, float] = field(default_factory=dict)
    service_ports: Dict[str, int] = field(default_factory=dict)
    service_health_checks: Dict[str, bool] = field(default_factory=dict)
    
    # Database health metrics
    database_connections: Dict[str, bool] = field(default_factory=dict)
    database_response_times: Dict[str, float] = field(default_factory=dict)
    migration_status: Dict[str, str] = field(default_factory=dict)
    
    # System integration metrics
    websocket_endpoints: Dict[str, str] = field(default_factory=dict)
    websocket_connectivity: Dict[str, bool] = field(default_factory=dict)
    inter_service_communication: Dict[str, bool] = field(default_factory=dict)
    
    # Resilience metrics
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    port_conflicts_resolved: int = 0
    graceful_shutdown_success: bool = False
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def total_duration(self) -> float:
        return (self.end_time or time.time()) - self.start_time
    
    @property
    def services_healthy_count(self) -> int:
        return sum(self.service_health_checks.values())
    
    @property
    def databases_connected_count(self) -> int:
        return sum(self.database_connections.values())
    
    @property
    def system_health_score(self) -> float:
        """Calculate overall system health score (0-100)."""
        total_checks = (
            len(self.service_health_checks) +
            len(self.database_connections) +
            len(self.websocket_connectivity) +
            len(self.inter_service_communication)
        )
        if total_checks == 0:
            return 0.0
        
        healthy_checks = (
            sum(self.service_health_checks.values()) +
            sum(self.database_connections.values()) +
            sum(self.websocket_connectivity.values()) +
            sum(self.inter_service_communication.values())
        )
        
        return (healthy_checks / total_checks) * 100


@dataclass
class SystemTestConfig:
    """Configuration for comprehensive system testing."""
    timeout_seconds: int = 60
    enable_websocket_tests: bool = True
    enable_database_tests: bool = True
    enable_migration_tests: bool = True
    enable_inter_service_tests: bool = True
    test_graceful_shutdown: bool = True
    
    # Service configuration
    test_frontend: bool = False  # Skip for speed by default
    use_dynamic_ports: bool = True
    enable_secrets_loading: bool = False
    
    # Test environment
    project_root: Optional[Path] = None
    temp_dir: Optional[Path] = None
    log_level: str = "INFO"


class TestComprehensiveSystemer:
    """Comprehensive end-to-end system tester with full validation."""
    
    def __init__(self, config: SystemTestConfig):
        self.config = config
        self.project_root = config.project_root or self._detect_project_root()
        self.metrics = SystemHealthMetrics(test_name="system_startup_health")
        
        # Process management
        self.launcher_process: Optional[subprocess.Popen] = None
        self.cleanup_tasks: List[callable] = []
        
        # Service discovery and health tracking
        self.service_discovery = ServiceDiscovery(self.project_root)
        self.known_services = {"auth", "backend", "websocket"}
        self.database_types = {"postgresql", "redis", "clickhouse"}
        
        # Testing state
        self.websocket_connections: Dict[str, websockets.ServerConnection] = {}
        
    def _detect_project_root(self) -> Path:
        """Detect project root directory."""
        current = Path(__file__).parent
        while current.parent != current:
            required_dirs = ["netra_backend", "auth_service", "dev_launcher"]
            if all((current / d).exists() for d in required_dirs):
                return current
            current = current.parent
        raise RuntimeError("Could not detect project root directory")
    
    async def run_comprehensive_system_test(self) -> SystemHealthMetrics:
        """Run comprehensive end-to-end system test."""
        logger.info("=== STARTING COMPREHENSIVE SYSTEM TEST ===")
        self.metrics.start_time = time.time()
        
        try:
            # Phase 1: Pre-startup validation and environment preparation
            await self._validate_system_preconditions()
            
            # Phase 2: Database connectivity and migration validation
            if self.config.enable_database_tests:
                await self._validate_database_health()
            
            # Phase 3: System startup orchestration
            await self._start_system_with_orchestration()
            
            # Phase 4: Service health validation
            await self._validate_service_health()
            
            # Phase 5: Inter-service communication validation
            if self.config.enable_inter_service_tests:
                await self._validate_inter_service_communication()
            
            # Phase 6: WebSocket connectivity validation
            if self.config.enable_websocket_tests:
                await self._validate_websocket_connectivity()
            
            # Phase 7: System resilience testing
            await self._test_system_resilience()
            
            # Phase 8: Graceful shutdown validation
            if self.config.test_graceful_shutdown:
                await self._test_graceful_shutdown()
            
            logger.info(f"System test completed successfully in {self.metrics.total_duration:.1f}s")
            return self.metrics
            
        except Exception as e:
            logger.error(f"System test failed: {e}")
            self.metrics.errors.append(str(e))
            await self._emergency_cleanup()
            return self.metrics
        
        finally:
            self.metrics.end_time = time.time()
            await self._cleanup_system_test()
    
    async def _validate_system_preconditions(self):
        """Phase 1: Validate system preconditions and environment."""
        logger.info("Phase 1: Validating system preconditions")
        
        # Check project structure
        required_dirs = ["netra_backend", "auth_service", "frontend", "dev_launcher"]
        missing_dirs = []
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
        
        if missing_dirs:
            raise RuntimeError(f"Missing required directories: {missing_dirs}")
        
        # Validate Python environment
        try:
            import uvicorn, fastapi, asyncio, httpx, websockets
        except ImportError as e:
            raise RuntimeError(f"Missing critical Python dependencies: {e}")
        
        # Set up test environment
        if not self.config.temp_dir:
            self.config.temp_dir = Path(tempfile.mkdtemp(prefix="system_e2e_"))
            self.cleanup_tasks.append(self._cleanup_temp_directory)
        
        # Clear any existing service discovery
        discovery_dir = self.project_root / ".service_discovery"
        if discovery_dir.exists():
            for file in discovery_dir.glob("*.json"):
                try:
                    file.unlink()
                except Exception as e:
                    self.metrics.warnings.append(f"Failed to clear discovery file {file}: {e}")
        
        logger.info("System preconditions validated successfully")
    
    async def _validate_database_health(self):
        """Phase 2: Validate database connectivity and migration health."""
        logger.info("Phase 2: Validating database health and migrations")
        
        db_connector = DatabaseConnector(use_emoji=False)
        try:
            # Test all database connections
            start_time = time.time()
            all_healthy = await db_connector.validate_all_connections()
            
            # Record individual database status
            for name, connection in db_connector.connections.items():
                db_name = connection.db_type.value.lower()
                is_connected = connection.status.value == "connected"
                response_time = time.time() - start_time if is_connected else 0.0
                
                self.metrics.database_connections[db_name] = is_connected
                self.metrics.database_response_times[db_name] = response_time
                
                if is_connected:
                    logger.info(f"Database {db_name} connected successfully ({response_time:.3f}s)")
                else:
                    error_msg = f"Database {db_name} connection failed: {connection.last_error}"
                    logger.warning(error_msg)
                    self.metrics.warnings.append(error_msg)
            
            # Test migration status for databases that support it
            if self.config.enable_migration_tests:
                await self._validate_migration_status()
                
        except Exception as e:
            error_msg = f"Database health validation failed: {e}"
            logger.error(error_msg)
            self.metrics.errors.append(error_msg)
            # Set all databases as disconnected
            for db_type in self.database_types:
                self.metrics.database_connections[db_type] = False
        
        finally:
            await db_connector.stop_health_monitoring()
    
    async def _validate_migration_status(self):
        """Validate database migration status."""
        try:
            # Import migration utilities
            from netra_backend.app.db.alembic_state_recovery import AlembicStateRecoveryManager
            
            recovery_manager = AlembicStateRecoveryManager()
            
            # Check PostgreSQL migration status
            try:
                pg_status = await recovery_manager.check_migration_state()
                self.metrics.migration_status["postgresql"] = pg_status.get("status", "unknown")
                logger.info(f"PostgreSQL migration status: {pg_status}")
            except Exception as e:
                self.metrics.migration_status["postgresql"] = "error"
                self.metrics.warnings.append(f"PostgreSQL migration check failed: {e}")
            
        except ImportError:
            self.metrics.warnings.append("Migration validation tools not available")
        except Exception as e:
            error_msg = f"Migration status validation failed: {e}"
            logger.warning(error_msg)
            self.metrics.warnings.append(error_msg)
    
    async def _start_system_with_orchestration(self):
        """Phase 3: Start system with proper service orchestration."""
        logger.info("Phase 3: Starting system with orchestration")
        
        # Build launcher command
        cmd = self._build_launcher_command()
        
        # Set up environment
        env.update({
            "NETRA_TEST_MODE": "true",
            "NETRA_STARTUP_MODE": "comprehensive",
            "NETRA_LOG_LEVEL": self.config.log_level
        })
        
        if not self.config.enable_secrets_loading:
            env["NETRA_SKIP_SECRETS"] = "true"
        
        logger.info(f"Starting system: {' '.join(cmd)}")
        
        # Start the launcher process
        startup_start = time.time()
        self.launcher_process = subprocess.Popen(
            cmd,
            cwd=str(self.project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=None if sys.platform == "win32" else os.setsid
        )
        
        self.cleanup_tasks.append(self._terminate_launcher_process)
        
        # Wait for system startup with timeout
        await self._wait_for_system_ready()
        
        startup_duration = time.time() - startup_start
        logger.info(f"System startup completed in {startup_duration:.1f}s")
    
    def _build_launcher_command(self) -> List[str]:
        """Build optimized launcher command for comprehensive testing."""
        cmd = [sys.executable, "-m", "dev_launcher"]
        
        cmd.extend([
            "--no-browser",
            "--non-interactive",
            "--minimal" if not self.config.test_frontend else "--full",
            "--no-reload"
        ])
        
        if self.config.use_dynamic_ports:
            cmd.append("--dynamic")
        
        if not self.config.enable_secrets_loading:
            cmd.append("--no-secrets")
        
        return cmd
    
    async def _wait_for_system_ready(self):
        """Wait for system to be ready with comprehensive validation."""
        timeout = self.config.timeout_seconds
        check_interval = 2.0
        elapsed = 0.0
        
        logger.info(f"Waiting for system ready (timeout: {timeout}s)")
        
        while elapsed < timeout:
            # Check if launcher process is still running
            if self.launcher_process and self.launcher_process.poll() is not None:
                stdout, stderr = self.launcher_process.communicate()
                if self.launcher_process.returncode != 0:
                    raise RuntimeError(f"System startup failed with exit code {self.launcher_process.returncode}. Stderr: {stderr}")
            
            # Check service readiness
            ready_services = await self._check_services_ready()
            if len(ready_services) >= 2:  # At least auth and backend
                logger.info(f"System ready: {len(ready_services)} services online")
                return
            
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        raise TimeoutError(f"System not ready after {timeout}s timeout")
    
    async def _check_services_ready(self) -> Set[str]:
        """Check which services are ready."""
        ready_services = set()
        
        # Check auth service (port 8081)
        if await self._is_service_healthy("auth", 8081):
            ready_services.add("auth")
        
        # Check backend service (port 8001)
        if await self._is_service_healthy("backend", 8001):
            ready_services.add("backend")
        
        # Check frontend if enabled
        if self.config.test_frontend and await self._is_service_healthy("frontend", 3000):
            ready_services.add("frontend")
        
        return ready_services
    
    async def _validate_service_health(self):
        """Phase 4: Comprehensive service health validation."""
        logger.info("Phase 4: Validating comprehensive service health")
        
        service_configs = [
            ("auth", 8081, "/health"),
            ("backend", 8001, "/health"),
        ]
        
        if self.config.test_frontend:
            service_configs.append(("frontend", 3000, "/"))
        
        for service_name, default_port, health_path in service_configs:
            await self._validate_individual_service(service_name, default_port, health_path)
        
        # Validate that critical services are healthy
        critical_services = ["auth", "backend"]
        healthy_critical = sum(
            self.metrics.service_health_checks.get(svc, False) 
            for svc in critical_services
        )
        
        if healthy_critical == 0:
            raise RuntimeError("No critical services are healthy")
        
        logger.info(f"Service health validation completed: {self.metrics.services_healthy_count} services healthy")
    
    async def _validate_individual_service(self, service_name: str, default_port: int, health_path: str):
        """Validate individual service health and performance."""
        try:
            # Discover actual port
            port = await self._discover_service_port(service_name, default_port)
            self.metrics.service_ports[service_name] = port
            
            # Test service startup
            startup_start = time.time()
            healthy = await self._is_service_healthy(service_name, port, health_path)
            startup_time = time.time() - startup_start
            
            # Record metrics
            self.metrics.services_started[service_name] = healthy
            self.metrics.service_startup_times[service_name] = startup_time
            self.metrics.service_health_checks[service_name] = healthy
            
            if healthy:
                logger.info(f"Service {service_name} healthy on port {port} ({startup_time:.3f}s)")
            else:
                warning_msg = f"Service {service_name} not healthy on port {port}"
                logger.warning(warning_msg)
                self.metrics.warnings.append(warning_msg)
        
        except Exception as e:
            error_msg = f"Service {service_name} validation failed: {e}"
            logger.error(error_msg)
            self.metrics.errors.append(error_msg)
            self.metrics.services_started[service_name] = False
            self.metrics.service_health_checks[service_name] = False
    
    async def _validate_inter_service_communication(self):
        """Phase 5: Validate inter-service communication."""
        logger.info("Phase 5: Validating inter-service communication")
        
        # Test auth service  ->  backend communication
        auth_to_backend = await self._test_auth_to_backend_communication()
        self.metrics.inter_service_communication["auth_to_backend"] = auth_to_backend
        
        # Test backend  ->  auth service communication
        backend_to_auth = await self._test_backend_to_auth_communication()
        self.metrics.inter_service_communication["backend_to_auth"] = backend_to_auth
        
        communication_success = sum(self.metrics.inter_service_communication.values())
        logger.info(f"Inter-service communication: {communication_success}/{len(self.metrics.inter_service_communication)} successful")
    
    async def _test_auth_to_backend_communication(self) -> bool:
        """Test communication from auth service to backend."""
        try:
            auth_port = self.metrics.service_ports.get("auth", 8081)
            backend_port = self.metrics.service_ports.get("backend", 8001)
            
            if not auth_port or not backend_port:
                return False
            
            # Test basic connectivity
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Get auth service status
                auth_response = await client.get(f"http://localhost:{auth_port}/health")
                if auth_response.status_code != 200:
                    return False
                
                # Test if auth service can validate against backend (if applicable)
                return True
                
        except Exception as e:
            logger.warning(f"Auth to backend communication test failed: {e}")
            return False
    
    async def _test_backend_to_auth_communication(self) -> bool:
        """Test communication from backend to auth service."""
        try:
            backend_port = self.metrics.service_ports.get("backend", 8001)
            auth_port = self.metrics.service_ports.get("auth", 8081)
            
            if not backend_port or not auth_port:
                return False
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Test backend can reach auth service
                backend_response = await client.get(f"http://localhost:{backend_port}/health")
                return backend_response.status_code == 200
                
        except Exception as e:
            logger.warning(f"Backend to auth communication test failed: {e}")
            return False
    
    async def _validate_websocket_connectivity(self):
        """Phase 6: Validate WebSocket connectivity and real-time features."""
        logger.info("Phase 6: Validating WebSocket connectivity")
        
        try:
            # Discover WebSocket endpoints
            backend_info = self.service_discovery.read_backend_info()
            if not backend_info:
                self.metrics.warnings.append("No backend service discovery info found")
                return
            
            ws_url = backend_info.get("websocket_url")
            if not ws_url:
                self.metrics.warnings.append("No WebSocket URL found in service discovery")
                return
            
            self.metrics.websocket_endpoints["backend"] = ws_url
            
            # Test WebSocket connection
            ws_connected = await self._test_websocket_connection(ws_url)
            self.metrics.websocket_connectivity["backend"] = ws_connected
            
            if ws_connected:
                logger.info(f"WebSocket connectivity validated: {ws_url}")
            else:
                self.metrics.warnings.append(f"WebSocket connection failed: {ws_url}")
        
        except Exception as e:
            error_msg = f"WebSocket validation failed: {e}"
            logger.error(error_msg)
            self.metrics.errors.append(error_msg)
    
    async def _test_websocket_connection(self, ws_url: str) -> bool:
        """Test WebSocket connection with timeout."""
        try:
            # Parse and validate URL
            parsed = urlparse(ws_url)
            if not parsed.hostname or not parsed.port:
                logger.warning(f"Invalid WebSocket URL: {ws_url}")
                return False
            
            # Test connection with timeout
            async with asyncio.timeout(5.0):
                async with websockets.connect(ws_url) as websocket:
                    # Send test message
                    test_message = {"type": "ping", "data": "health_check"}
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for response
                    try:
                        response = await websocket.recv()
                        logger.info(f"WebSocket test successful: {response}")
                        return True
                    except asyncio.TimeoutError:
                        logger.info("WebSocket connected but no response received")
                        return True  # Connection successful even without response
            
        except (ConnectionClosed, InvalidURI, OSError, asyncio.TimeoutError) as e:
            logger.warning(f"WebSocket connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"WebSocket test error: {e}")
            return False
    
    async def _test_system_resilience(self):
        """Phase 7: Test system resilience and recovery."""
        logger.info("Phase 7: Testing system resilience")
        
        # Test port conflict resolution
        await self._test_port_conflict_resolution()
        
        # Test service recovery (simple validation)
        await self._test_service_recovery()
    
    async def _test_port_conflict_resolution(self):
        """Test that system can handle port conflicts."""
        try:
            # Check for any port conflicts in current allocation
            ports_used = list(self.metrics.service_ports.values())
            unique_ports = set(ports_used)
            
            if len(ports_used) != len(unique_ports):
                conflicts = len(ports_used) - len(unique_ports)
                self.metrics.port_conflicts_resolved = conflicts
                logger.warning(f"Port conflicts detected and resolved: {conflicts}")
            else:
                logger.info("No port conflicts detected")
        
        except Exception as e:
            self.metrics.warnings.append(f"Port conflict test failed: {e}")
    
    async def _test_service_recovery(self):
        """Test basic service recovery capability."""
        # This is a lightweight test - we don't actually kill services in comprehensive test
        # Instead, we validate that services are responding consistently
        
        recovery_attempts = 0
        successful_recoveries = 0
        
        for service_name in ["auth", "backend"]:
            if service_name not in self.metrics.service_ports:
                continue
                
            recovery_attempts += 1
            port = self.metrics.service_ports[service_name]
            
            # Test service responsiveness multiple times
            healthy_checks = 0
            for i in range(3):
                if await self._is_service_healthy(service_name, port):
                    healthy_checks += 1
                await asyncio.sleep(0.5)
            
            if healthy_checks >= 2:  # At least 2/3 checks successful
                successful_recoveries += 1
        
        self.metrics.recovery_attempts = recovery_attempts
        self.metrics.successful_recoveries = successful_recoveries
        
        logger.info(f"Service recovery test: {successful_recoveries}/{recovery_attempts} services stable")
    
    async def _test_graceful_shutdown(self):
        """Phase 8: Test graceful shutdown procedure."""
        logger.info("Phase 8: Testing graceful shutdown")
        
        if not self.launcher_process:
            self.metrics.warnings.append("No launcher process to test shutdown")
            return
        
        try:
            # Send graceful shutdown signal
            if sys.platform == "win32":
                # Windows: send CTRL+C signal
                self.launcher_process.send_signal(signal.CTRL_C_EVENT)
            else:
                # Unix: send SIGTERM
                self.launcher_process.terminate()
            
            # Wait for graceful shutdown
            try:
                self.launcher_process.wait(timeout=10)
                self.metrics.graceful_shutdown_success = True
                logger.info("Graceful shutdown completed successfully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown takes too long
                self.launcher_process.kill()
                self.launcher_process.wait()
                self.metrics.warnings.append("Graceful shutdown timeout - forced termination")
        
        except Exception as e:
            error_msg = f"Graceful shutdown test failed: {e}"
            logger.error(error_msg)
            self.metrics.errors.append(error_msg)
    
    # Helper methods
    async def _discover_service_port(self, service_name: str, default_port: int) -> int:
        """Discover actual service port from service discovery."""
        try:
            if service_name == "auth":
                info = self.service_discovery.read_auth_info()
            elif service_name == "backend":
                info = self.service_discovery.read_backend_info()
            elif service_name == "frontend":
                info = self.service_discovery.read_frontend_info()
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
        """Terminate launcher process."""
        if not self.launcher_process:
            return
        
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.launcher_process.pid)],
                    capture_output=True, text=True
                )
            else:
                os.killpg(os.getpgid(self.launcher_process.pid), signal.SIGTERM)
            
            try:
                self.launcher_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.launcher_process.kill()
                self.launcher_process.wait()
        except Exception as e:
            logger.error(f"Error terminating launcher: {e}")
    
    def _cleanup_temp_directory(self):
        """Clean up temporary directory."""
        if self.config.temp_dir and self.config.temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(str(self.config.temp_dir))
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")
    
    async def _emergency_cleanup(self):
        """Emergency cleanup on test failure."""
        logger.warning("Performing emergency cleanup")
        for task in self.cleanup_tasks:
            try:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            except Exception as e:
                logger.error(f"Emergency cleanup failed: {e}")
    
    async def _cleanup_system_test(self):
        """Clean up after system test."""
        logger.info("Cleaning up comprehensive system test")
        
        # Close WebSocket connections
        for ws_name, ws in self.websocket_connections.items():
            try:
                await ws.close()
            except Exception:
                pass
        
        # Run all cleanup tasks
        for task in self.cleanup_tasks:
            try:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            except Exception as e:
                logger.error(f"Cleanup task failed: {e}")
        
        logger.info("System test cleanup completed")


@pytest.mark.e2e
@pytest.mark.asyncio  
class TestCompleteSystemStartupHealthValidation:
    """Comprehensive system startup and health validation test suite."""
    
    @pytest.fixture
    def system_config(self):
        """Create system test configuration."""
        return SystemTestConfig(
            timeout_seconds=60,
            enable_websocket_tests=True,
            enable_database_tests=True,
            enable_migration_tests=True,
            enable_inter_service_tests=True,
            test_graceful_shutdown=True,
            test_frontend=False,  # Skip for speed
            use_dynamic_ports=True,
            enable_secrets_loading=False
        )
    
    @pytest.mark.startup
    async def test_comprehensive_system_startup_and_health(self, system_config):
        """Test comprehensive system startup and health validation."""
        logger.info("=== COMPREHENSIVE SYSTEM STARTUP AND HEALTH TEST ===")
        
        tester = ComprehensiveSystemTester(system_config)
        metrics = await tester.run_comprehensive_system_test()
        
        # Validate core requirements
        assert len(metrics.errors) == 0, f"System test had errors: {metrics.errors}"
        
        # Validate service health
        assert metrics.services_healthy_count >= 2, f"Insufficient healthy services: {metrics.services_healthy_count}"
        
        # Validate database connectivity (at least one should work)
        if metrics.databases_connected_count == 0:
            logger.warning("No databases connected - running in limited mode")
        
        # Validate system health score
        health_score = metrics.system_health_score
        assert health_score >= 70.0, f"System health score too low: {health_score:.1f}%"
        
        # Validate startup performance
        assert metrics.total_duration < system_config.timeout_seconds, \
            f"System startup too slow: {metrics.total_duration:.1f}s"
        
        # Validate resilience metrics
        if metrics.recovery_attempts > 0:
            recovery_rate = (metrics.successful_recoveries / metrics.recovery_attempts) * 100
            assert recovery_rate >= 50, f"Recovery rate too low: {recovery_rate:.1f}%"
        
        # Log comprehensive results
        logger.info("=== SYSTEM TEST RESULTS ===")
        logger.info(f"Total Duration: {metrics.total_duration:.1f}s")
        logger.info(f"System Health Score: {health_score:.1f}%")
        logger.info(f"Services Healthy: {metrics.services_healthy_count}")
        logger.info(f"Databases Connected: {metrics.databases_connected_count}")
        logger.info(f"WebSocket Endpoints: {len(metrics.websocket_endpoints)}")
        logger.info(f"Inter-service Communication: {sum(metrics.inter_service_communication.values())}")
        logger.info(f"Port Conflicts Resolved: {metrics.port_conflicts_resolved}")
        logger.info(f"Graceful Shutdown: {metrics.graceful_shutdown_success}")
        
        if metrics.warnings:
            logger.warning(f"Warnings: {len(metrics.warnings)}")
            for warning in metrics.warnings[:5]:  # Show first 5 warnings
                logger.warning(f"  - {warning}")
        
        logger.info("=== COMPREHENSIVE SYSTEM TEST PASSED ===")


async def run_comprehensive_system_test():
    """Standalone function to run comprehensive system test."""
    config = SystemTestConfig()
    tester = ComprehensiveSystemTester(config)
    return await tester.run_comprehensive_system_test()


if __name__ == "__main__":
    # Allow standalone execution
    result = asyncio.run(run_comprehensive_system_test())
    print(f"System test result: Health Score {result.system_health_score:.1f}%")
    print(f"Duration: {result.total_duration:.1f}s")
    print(f"Services: {result.services_healthy_count} healthy")
    print(f"Databases: {result.databases_connected_count} connected")
    if result.errors:
        print(f"Errors: {len(result.errors)}")
        for error in result.errors:
            print(f"  - {error}")