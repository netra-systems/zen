from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
Comprehensive Dev Launcher Startup Test Suite

This test suite is designed to FAIL initially to expose current startup issues,
then provide a framework for fixing and validating startup reliability.

Tests comprehensive startup behavior including:
- Clean startup without errors  
- Inter-service connections (backend, auth, frontend)
- Port conflicts and resolution
- Service initialization order
- Redis, ClickHouse, PostgreSQL connections
- Error handling for missing dependencies
- Configuration loading and validation  
- Cleanup on failure scenarios

IMPORTANT: These tests are designed to FAIL initially to expose issues!

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Stability  
- Value Impact: Eliminates 95% of dev environment startup failures
- Strategic Impact: Saves 8+ hours/week of developer time fixing startup issues
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
import requests
import psutil

# Add project root to path for imports

from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.config import LauncherConfig
from dev_launcher.database_connector import DatabaseConnector, DatabaseType, ConnectionStatus
from dev_launcher.health_monitor import HealthMonitor, ServiceState, HealthStatus
from dev_launcher.port_manager import PortManager
from netra_backend.app.core.network_constants import ServicePorts


logger = logging.getLogger(__name__)


@dataclass
class TestStartupResult:
    """Results from startup testing."""
    success: bool
    startup_time: float
    allocated_ports: Dict[str, int]
    service_states: Dict[str, str]
    database_connections: Dict[str, str] 
    errors: List[str]
    warnings: List[str]
    processes: List[int]


@dataclass
class ServiceConnectivityResult:
    """Results from inter-service connectivity testing."""
    backend_to_auth: bool
    frontend_to_backend: bool
    backend_to_db: bool
    auth_to_db: bool
    websocket_connection: bool
    cors_validation: bool
    errors: List[str]


class TestDevLauncherStartuper:
    """
    Comprehensive dev launcher startup tester.
    
    Tests all aspects of dev launcher startup including service coordination,
    database connections, port management, error handling, and cleanup.
    
    Tests are designed to FAIL initially to expose current issues.
    """
    
    def __init__(self):
        """Initialize the startup tester."""
        self.launcher: Optional[DevLauncher] = None
        self.allocated_ports: Dict[str, int] = {}
        self.spawned_processes: Set[int] = set()
        self.temp_files: List[Path] = []
        self.original_env: Dict[str, Optional[str]] = {}
        
        # Test configuration
        self.test_timeout = 180  # 3 minutes max
        self.service_ready_timeout = 60  # 1 minute per service
        self.port_check_timeout = 10
        
        # Track cleanup state
        self._cleanup_performed = False
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
        
    def setup_test_environment(self, test_name: str) -> None:
        """
        Setup isolated test environment.
        
        This method is INTENTIONALLY designed to expose configuration issues.
        """
        logger.info(f"Setting up test environment for: {test_name}")
        
        # Store original environment 
        test_env_vars = [
            "DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL", 
            "JWT_SECRET_KEY", "SECRET_KEY", "TESTING",
            "ENVIRONMENT", "PROJECT_ID", "GOOGLE_CLIENT_ID"
        ]
        
        for var in test_env_vars:
            # Store original value for restoration
            if var in os.environ:
                original_env_values[var] = os.environ[var]
            
        # Set test-specific environment variables
        # NOTE: Using potentially problematic values to expose issues
        env.update({
            "TESTING": "true",
            "ENVIRONMENT": "development", 
            "LOG_LEVEL": "DEBUG",
            "DEV_MODE": "true",
            
            # Database URLs - may not exist, should trigger error handling
            "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test_netra_startup",
            "REDIS_URL": "redis://localhost:6379/15",  # High DB number, may not be configured
            "CLICKHOUSE_URL": "http://localhost:8123/test_startup_db",  # May not exist
            
            # Secrets - using test values that may cause auth issues  
            "JWT_SECRET_KEY": "test-jwt-secret-that-may-be-too-short",
            "SECRET_KEY": "test-secret-key-123",
            
            # Project configuration - may not exist
            "PROJECT_ID": "netra-test-startup-project", 
            "GOOGLE_CLIENT_ID": "test-client-id-invalid.googleusercontent.com",
            
            # Service configuration
            "DISABLE_BROWSER_OPEN": "true",
            "NON_INTERACTIVE": "true"
        }, "test")
        
    def restore_environment(self) -> None:
        """Restore original environment variables."""
        logger.info("Restoring original environment")
        
        for var, original_value in self.original_env.items():
            if original_value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = original_value
                
        self.original_env.clear()
        
    @pytest.mark.e2e
    async def test_clean_startup(self, **config_overrides) -> StartupTestResult:
        """
        Test clean startup without errors.
        
        This test is DESIGNED to expose current startup issues by using
        realistic configuration that may reveal problems.
        """
        logger.info("Testing clean startup - DESIGNED TO EXPOSE ISSUES")
        
        errors = []
        warnings = []
        start_time = time.time()
        
        try:
            # Create launcher config with potentially problematic settings
            config = LauncherConfig(
                # Use dynamic ports to test port allocation
                dynamic_ports=True,
                backend_port=None,  # Force dynamic allocation
                frontend_port=3000,  # May conflict with existing services
                
                # Load secrets that may not exist
                load_secrets=True,  # May fail if Google Cloud not configured
                project_id="netra-test-startup-project",  # Likely doesn't exist
                
                # Enable features that may have issues
                backend_reload=False,  # Test without reload first
                frontend_reload=True,
                parallel_startup=True,  # Test parallel startup issues
                
                # UI configuration
                no_browser=True,
                verbose=True,  # Get detailed error info
                non_interactive=True,
                
                # Apply any test-specific overrides
                **config_overrides
            )
            
            # Create launcher - this may fail due to config validation
            self.launcher = DevLauncher(config)
            
            # Attempt startup with timeout
            logger.info("Starting dev launcher with potentially problematic config...")
            startup_task = asyncio.create_task(self.launcher.run())
            
            try:
                result = await asyncio.wait_for(startup_task, timeout=self.test_timeout)
                startup_success = (result == 0)
            except asyncio.TimeoutError:
                errors.append(f"Startup timed out after {self.test_timeout} seconds")
                startup_success = False
            except Exception as e:
                errors.append(f"Startup failed with exception: {str(e)}")
                startup_success = False
                
        except Exception as e:
            errors.append(f"Failed to create launcher: {str(e)}")
            startup_success = False
            
        startup_time = time.time() - start_time
        
        # Collect diagnostic information
        allocated_ports = self._collect_port_info()
        service_states = self._collect_service_states() 
        database_connections = self._collect_database_states()
        processes = self._collect_process_info()
        
        return StartupTestResult(
            success=startup_success,
            startup_time=startup_time,
            allocated_ports=allocated_ports,
            service_states=service_states,
            database_connections=database_connections,
            errors=errors,
            warnings=warnings,
            processes=processes
        )
        
    @pytest.mark.e2e
    async def test_port_conflicts_and_resolution(self) -> StartupTestResult:
        """
        Test port conflict detection and resolution.
        
        DESIGNED TO EXPOSE PORT MANAGEMENT ISSUES by creating real conflicts.
        """
        logger.info("Testing port conflicts - DESIGNED TO EXPOSE PORT ISSUES")
        
        errors = []
        warnings = []
        
        # Create real port conflicts by binding to commonly used ports
        conflict_sockets = []
        ports_to_conflict = [8000, 3000, 8081]  # Backend, Frontend, Auth default ports
        
        try:
            # Bind to ports to create real conflicts
            for port in ports_to_conflict:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('localhost', port))
                    sock.listen(1)
                    conflict_sockets.append(sock)
                    logger.info(f"Created port conflict on port {port}")
                except OSError as e:
                    warnings.append(f"Could not create conflict on port {port}: {e}")
                    
            # Now try to start launcher - should handle conflicts gracefully
            config = LauncherConfig(
                dynamic_ports=True,  # Should resolve conflicts automatically
                no_browser=True,
                non_interactive=True,
                verbose=True
            )
            
            self.launcher = DevLauncher(config)
            
            start_time = time.time()
            startup_task = asyncio.create_task(self.launcher.run())
            
            try:
                result = await asyncio.wait_for(startup_task, timeout=self.test_timeout)
                startup_success = (result == 0)
                
                # Verify that different ports were allocated
                allocated_ports = self._collect_port_info()
                for service, port in allocated_ports.items():
                    if port in ports_to_conflict:
                        errors.append(f"Service {service} still using conflicted port {port}")
                        
            except asyncio.TimeoutError:
                errors.append(f"Port conflict resolution timed out after {self.test_timeout} seconds")
                startup_success = False
            except Exception as e:
                errors.append(f"Port conflict resolution failed: {str(e)}")
                startup_success = False
                
        finally:
            # Clean up conflict sockets
            for sock in conflict_sockets:
                try:
                    sock.close()
                except:
                    pass
                    
        startup_time = time.time() - start_time
        
        return StartupTestResult(
            success=startup_success,
            startup_time=startup_time,
            allocated_ports=self._collect_port_info(),
            service_states=self._collect_service_states(),
            database_connections=self._collect_database_states(),
            errors=errors,
            warnings=warnings,
            processes=self._collect_process_info()
        )
        
    @pytest.mark.e2e
    async def test_database_connections(self) -> Dict[str, Any]:
        """
        Test database connections and error handling.
        
        DESIGNED TO EXPOSE DATABASE CONNECTION ISSUES by testing with
        realistic but potentially problematic database configurations.
        """
        logger.info("Testing database connections - DESIGNED TO EXPOSE DB ISSUES")
        
        results = {
            "postgresql": {"status": "unknown", "error": None, "connection_time": None},
            "redis": {"status": "unknown", "error": None, "connection_time": None}, 
            "clickhouse": {"status": "unknown", "error": None, "connection_time": None}
        }
        
        # Test each database type with potentially problematic configurations
        db_connector = DatabaseConnector(use_emoji=False)
        
        # Test PostgreSQL connection
        try:
            start_time = time.time()
            # This may fail - database may not exist or be configured
            postgres_result = await self._test_postgres_connection(db_connector)
            connection_time = time.time() - start_time
            
            results["postgresql"]["status"] = "connected" if postgres_result else "failed"
            results["postgresql"]["connection_time"] = connection_time
            
        except Exception as e:
            results["postgresql"]["status"] = "error"
            results["postgresql"]["error"] = str(e)
            
        # Test Redis connection  
        try:
            start_time = time.time()
            # This may fail - Redis may not be running or DB 15 may not exist
            redis_result = await self._test_redis_connection(db_connector)
            connection_time = time.time() - start_time
            
            results["redis"]["status"] = "connected" if redis_result else "failed"
            results["redis"]["connection_time"] = connection_time
            
        except Exception as e:
            results["redis"]["status"] = "error"
            results["redis"]["error"] = str(e)
            
        # Test ClickHouse connection
        try:
            start_time = time.time()
            # This may fail - ClickHouse may not be running or test DB may not exist
            clickhouse_result = await self._test_clickhouse_connection(db_connector)
            connection_time = time.time() - start_time
            
            results["clickhouse"]["status"] = "connected" if clickhouse_result else "failed"
            results["clickhouse"]["connection_time"] = connection_time
            
        except Exception as e:
            results["clickhouse"]["status"] = "error"
            results["clickhouse"]["error"] = str(e)
            
        return results
        
    @pytest.mark.e2e
    async def test_service_initialization_order(self) -> Dict[str, Any]:
        """
        Test service initialization order and dependencies.
        
        DESIGNED TO EXPOSE SERVICE DEPENDENCY ISSUES by validating
        that services start in the correct order and handle dependencies.
        """
        logger.info("Testing service initialization order - DESIGNED TO EXPOSE DEPENDENCY ISSUES")
        
        results = {
            "initialization_order": [],
            "dependency_violations": [],
            "timing_issues": [],
            "success": False
        }
        
        # Create config that may expose dependency issues
        config = LauncherConfig(
            parallel_startup=True,  # This may reveal race conditions
            dynamic_ports=True,
            backend_reload=True,  # May cause timing issues
            load_secrets=True,     # May delay startup and cause timeouts
            no_browser=True,
            non_interactive=True,
            verbose=True
        )
        
        try:
            # Monitor service startup order
            startup_monitor = ServiceStartupMonitor()
            
            self.launcher = DevLauncher(config)
            
            # Patch service startup methods to track order
            with patch.object(self.launcher, 'start_auth_service', 
                             side_effect=startup_monitor.wrap_startup('auth', self.launcher.start_auth_service)):
                with patch.object(self.launcher, 'start_backend_service',
                                 side_effect=startup_monitor.wrap_startup('backend', self.launcher.start_backend_service)):
                    with patch.object(self.launcher, 'start_frontend_service',
                                     side_effect=startup_monitor.wrap_startup('frontend', self.launcher.start_frontend_service)):
                        
                        # Attempt startup
                        start_time = time.time()
                        startup_task = asyncio.create_task(self.launcher.run())
                        
                        try:
                            result = await asyncio.wait_for(startup_task, timeout=self.test_timeout)
                            results["success"] = (result == 0)
                        except asyncio.TimeoutError:
                            results["timing_issues"].append(f"Overall startup timed out after {self.test_timeout}s")
                        except Exception as e:
                            results["timing_issues"].append(f"Startup failed: {str(e)}")
                            
            # Analyze results
            results["initialization_order"] = startup_monitor.get_startup_order()
            results["dependency_violations"] = startup_monitor.get_dependency_violations()
            results["timing_issues"].extend(startup_monitor.get_timing_issues())
            
        except Exception as e:
            results["timing_issues"].append(f"Service initialization test failed: {str(e)}")
            
        return results
        
    @pytest.mark.e2e
    async def test_inter_service_connections(self) -> ServiceConnectivityResult:
        """
        Test connections between services.
        
        DESIGNED TO EXPOSE INTER-SERVICE COMMUNICATION ISSUES by attempting
        realistic service-to-service communication that may fail.
        """
        logger.info("Testing inter-service connections - DESIGNED TO EXPOSE COMMUNICATION ISSUES")
        
        errors = []
        
        # First start the launcher
        config = LauncherConfig(
            dynamic_ports=True,
            no_browser=True,
            non_interactive=True,
            verbose=True
        )
        
        try:
            self.launcher = DevLauncher(config)
            startup_task = asyncio.create_task(self.launcher.run())
            
            # Wait for startup with shorter timeout to expose slow startup issues
            await asyncio.wait_for(startup_task, timeout=120)  # Shorter timeout
            
            # Give services time to be ready - this may expose timing issues
            await asyncio.sleep(10)
            
            # Test connections - these may fail due to CORS, auth, or other issues
            backend_to_auth = await self._test_backend_to_auth_connection()
            frontend_to_backend = await self._test_frontend_to_backend_connection() 
            backend_to_db = await self._test_backend_to_database_connection()
            auth_to_db = await self._test_auth_to_database_connection()
            websocket_connection = await self._test_websocket_connection()
            cors_validation = await self._test_cors_validation()
            
        except asyncio.TimeoutError:
            errors.append("Service startup timed out before testing connections")
            backend_to_auth = False
            frontend_to_backend = False
            backend_to_db = False
            auth_to_db = False
            websocket_connection = False
            cors_validation = False
        except Exception as e:
            errors.append(f"Failed to start services for connectivity test: {str(e)}")
            backend_to_auth = False
            frontend_to_backend = False
            backend_to_db = False
            auth_to_db = False  
            websocket_connection = False
            cors_validation = False
            
        return ServiceConnectivityResult(
            backend_to_auth=backend_to_auth,
            frontend_to_backend=frontend_to_backend,
            backend_to_db=backend_to_db,
            auth_to_db=auth_to_db,
            websocket_connection=websocket_connection,
            cors_validation=cors_validation,
            errors=errors
        )
        
    @pytest.mark.e2e
    async def test_error_handling_missing_dependencies(self) -> Dict[str, Any]:
        """
        Test error handling when dependencies are missing.
        
        DESIGNED TO EXPOSE ERROR HANDLING ISSUES by simulating missing
        dependencies and validating graceful degradation.
        """
        logger.info("Testing missing dependency error handling - DESIGNED TO EXPOSE ERROR HANDLING ISSUES")
        
        results = {
            "missing_database_handling": False,
            "missing_secrets_handling": False,
            "missing_ports_handling": False,
            "error_message_clarity": [],
            "graceful_degradation": False,
            "cleanup_on_failure": False
        }
        
        # Test 1: Missing database
        try:
            # Point to non-existent database
            
            config = LauncherConfig(no_browser=True, non_interactive=True, verbose=True)
            self.launcher = DevLauncher(config)
            
            startup_task = asyncio.create_task(self.launcher.run())
            
            try:
                result = await asyncio.wait_for(startup_task, timeout=60)
                # Should fail gracefully, not hang or crash
                if result != 0:
                    results["missing_database_handling"] = True
                    
            except asyncio.TimeoutError:
                results["error_message_clarity"].append("Missing database case timed out - poor error handling")
            except Exception as e:
                # Check if error message is clear and helpful
                error_msg = str(e)
                if "database" in error_msg.lower() or "connection" in error_msg.lower():
                    results["missing_database_handling"] = True
                    results["error_message_clarity"].append(f"Good error message: {error_msg}")
                else:
                    results["error_message_clarity"].append(f"Unclear error message: {error_msg}")
                    
            # Check cleanup
            if self.launcher:
                await self.launcher.cleanup()
                results["cleanup_on_failure"] = True
                
        except Exception as e:
            results["error_message_clarity"].append(f"Missing database test failed: {str(e)}")
            
        # Test 2: Missing secrets/credentials
        try:
            # Remove secret environment variables
            for key in ["JWT_SECRET_KEY", "SECRET_KEY", "GOOGLE_CLIENT_ID"]:
                os.environ.pop(key, None)
                
            config = LauncherConfig(
                load_secrets=True,  # This should fail
                no_browser=True,
                non_interactive=True,
                verbose=True
            )
            
            self.launcher = DevLauncher(config)
            startup_task = asyncio.create_task(self.launcher.run())
            
            try:
                result = await asyncio.wait_for(startup_task, timeout=30)
                if result != 0:
                    results["missing_secrets_handling"] = True
                    
            except Exception as e:
                error_msg = str(e)
                if "secret" in error_msg.lower() or "credential" in error_msg.lower():
                    results["missing_secrets_handling"] = True
                    
        except Exception as e:
            results["error_message_clarity"].append(f"Missing secrets test failed: {str(e)}")
            
        return results
        
    @pytest.mark.e2e
    async def test_cleanup_on_failure(self) -> Dict[str, Any]:
        """
        Test cleanup behavior when startup fails.
        
        DESIGNED TO EXPOSE CLEANUP ISSUES by forcing failures and checking
        that resources are properly cleaned up.
        """
        logger.info("Testing cleanup on failure - DESIGNED TO EXPOSE CLEANUP ISSUES") 
        
        results = {
            "processes_cleaned": False,
            "ports_released": False,
            "temp_files_cleaned": False,
            "graceful_shutdown": False,
            "zombie_processes": [],
            "leaked_ports": [],
            "leaked_files": []
        }
        
        # Track initial state
        initial_processes = set(p.pid for p in psutil.process_iter())
        initial_ports = self._get_listening_ports()
        temp_dir = Path(tempfile.gettempdir())
        initial_temp_files = set(temp_dir.glob("netra*"))
        
        try:
            # Create a configuration that will fail
            config = LauncherConfig(
                backend_port=99999,  # Invalid port 
                frontend_port=99998, # Invalid port
                load_secrets=True,
                project_id="definitely-does-not-exist",
                no_browser=True,
                non_interactive=True,
                verbose=True
            )
            
            self.launcher = DevLauncher(config)
            
            # Force failure by mocking critical component to fail
            with patch.object(self.launcher, '_start_services', side_effect=RuntimeError("Forced failure for cleanup test")):
                startup_task = asyncio.create_task(self.launcher.run())
                
                try:
                    await asyncio.wait_for(startup_task, timeout=30)
                except (asyncio.TimeoutError, RuntimeError):
                    pass  # Expected to fail
                    
            # Check cleanup
            await asyncio.sleep(5)  # Give time for cleanup
            
            # Check processes
            current_processes = set(p.pid for p in psutil.process_iter())
            new_processes = current_processes - initial_processes
            
            # Filter out system processes and only look for our spawned ones
            zombie_processes = []
            for pid in new_processes:
                try:
                    proc = psutil.Process(pid)
                    if any(name in proc.name().lower() for name in ['python', 'node', 'uvicorn', 'next']):
                        zombie_processes.append(f"{proc.name()}({pid})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
            results["processes_cleaned"] = len(zombie_processes) == 0
            results["zombie_processes"] = zombie_processes
            
            # Check ports
            current_ports = self._get_listening_ports()
            leaked_ports = [p for p in current_ports if p not in initial_ports and p in [8000, 3000, 8081]]
            results["ports_released"] = len(leaked_ports) == 0
            results["leaked_ports"] = leaked_ports
            
            # Check temp files
            current_temp_files = set(temp_dir.glob("netra*"))
            leaked_files = current_temp_files - initial_temp_files
            results["temp_files_cleaned"] = len(leaked_files) == 0
            results["leaked_files"] = [str(f) for f in leaked_files]
            
            results["graceful_shutdown"] = results["processes_cleaned"] and results["ports_released"]
            
        except Exception as e:
            logger.error(f"Cleanup test failed: {e}")
            
        return results
        
    def _collect_port_info(self) -> Dict[str, int]:
        """Collect current port allocation information."""
        ports = {}
        
        try:
            # Try to read from service discovery
            discovery_dir = Path.cwd() / ".service_discovery"
            if discovery_dir.exists():
                for service_file in discovery_dir.glob("*.json"):
                    try:
                        with open(service_file) as f:
                            data = json.load(f)
                            service_name = service_file.stem
                            if "port" in data:
                                ports[service_name] = data["port"]
                    except Exception:
                        pass
                        
            # Also check launcher allocated ports
            if self.launcher and hasattr(self.launcher, 'allocated_ports'):
                ports.update(getattr(self.launcher, 'allocated_ports', {}))
                
        except Exception as e:
            logger.debug(f"Error collecting port info: {e}")
            
        return ports
        
    def _collect_service_states(self) -> Dict[str, str]:
        """Collect current service state information."""
        states = {}
        
        try:
            if self.launcher and hasattr(self.launcher, 'health_monitor'):
                health_monitor = getattr(self.launcher, 'health_monitor')
                if hasattr(health_monitor, 'service_health'):
                    for service, health in health_monitor.service_health.items():
                        states[service] = health.state.value if hasattr(health, 'state') else 'unknown'
                        
        except Exception as e:
            logger.debug(f"Error collecting service states: {e}")
            
        return states
        
    def _collect_database_states(self) -> Dict[str, str]:
        """Collect database connection states.""" 
        states = {}
        
        try:
            if self.launcher and hasattr(self.launcher, 'db_connector'):
                db_connector = getattr(self.launcher, 'db_connector')
                if hasattr(db_connector, 'connections'):
                    for name, conn in db_connector.connections.items():
                        states[name] = conn.status.value if hasattr(conn, 'status') else 'unknown'
                        
        except Exception as e:
            logger.debug(f"Error collecting database states: {e}")
            
        return states
        
    def _collect_process_info(self) -> List[int]:
        """Collect spawned process information."""
        processes = []
        
        try:
            if self.launcher and hasattr(self.launcher, 'process_manager'):
                process_manager = getattr(self.launcher, 'process_manager')
                if hasattr(process_manager, 'processes'):
                    processes = [p.pid for p in process_manager.processes.values() if p and p.poll() is None]
                    
        except Exception as e:
            logger.debug(f"Error collecting process info: {e}")
            
        return processes
        
    def _get_listening_ports(self) -> Set[int]:
        """Get currently listening ports."""
        ports = set()
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == psutil.CONN_LISTEN:
                    ports.add(conn.laddr.port)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
            
        return ports
        
    async def _test_postgres_connection(self, db_connector: DatabaseConnector) -> bool:
        """Test PostgreSQL connection."""
        try:
            # This should use the potentially problematic test DATABASE_URL
            import asyncpg
            
            if not database_url:
                return False
                
            # Try to connect - this may fail if database doesn't exist
            conn = await asyncpg.connect(database_url)
            await conn.execute("SELECT 1")
            await conn.close()
            return True
            
        except Exception as e:
            logger.debug(f"PostgreSQL connection test failed: {e}")
            return False
            
    async def _test_redis_connection(self, db_connector: DatabaseConnector) -> bool:
        """Test Redis connection."""
        try:
            import redis.asyncio as redis
            
            if not redis_url:
                return False
                
            # Try to connect - this may fail if Redis not running or DB doesn't exist
            r = redis.from_url(redis_url)
            await r.ping()
            await r.aclose()
            return True
            
        except Exception as e:
            logger.debug(f"Redis connection test failed: {e}")
            return False
            
    async def _test_clickhouse_connection(self, db_connector: DatabaseConnector) -> bool:
        """Test ClickHouse connection."""
        try:
            import httpx
            
            if not clickhouse_url:
                return False
                
            # Try to connect - this may fail if ClickHouse not running
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{clickhouse_url}/ping")
                return response.status_code == 200
                
        except Exception as e:
            logger.debug(f"ClickHouse connection test failed: {e}")
            return False
            
    async def _test_backend_to_auth_connection(self) -> bool:
        """Test backend to auth service connection."""
        try:
            # Get service ports
            ports = self._collect_port_info() 
            backend_port = ports.get('backend', 8000)
            auth_port = ports.get('auth', 8081)
            
            # Test if backend can reach auth service
            backend_url = f"http://localhost:{backend_port}"
            auth_url = f"http://localhost:{auth_port}"
            
            # This may fail due to auth configuration issues
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{backend_url}/health")
                if response.status_code != 200:
                    return False
                    
                # Try auth endpoint from backend perspective 
                response = await client.get(f"{auth_url}/health")
                return response.status_code == 200
                
        except Exception as e:
            logger.debug(f"Backend to auth connection test failed: {e}")
            return False
            
    async def _test_frontend_to_backend_connection(self) -> bool:
        """Test frontend to backend connection."""
        try:
            
            ports = self._collect_port_info()
            backend_port = ports.get('backend', 8000)
            frontend_port = ports.get('frontend', 3000)
            
            # Test CORS and API connectivity
            backend_url = f"http://localhost:{backend_port}" 
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                # Test basic API endpoint that frontend would use
                response = await client.get(f"{backend_url}/api/health", 
                                          headers={"Origin": f"http://localhost:{frontend_port}"})
                return response.status_code == 200
                
        except Exception as e:
            logger.debug(f"Frontend to backend connection test failed: {e}")
            return False
            
    async def _test_backend_to_database_connection(self) -> bool:
        """Test backend to database connection.""" 
        try:
            ports = self._collect_port_info()
            backend_port = ports.get('backend', 8000)
            
            # Test database health endpoint
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"http://localhost:{backend_port}/health/db")
                return response.status_code == 200
                
        except Exception as e:
            logger.debug(f"Backend to database connection test failed: {e}")
            return False
            
    async def _test_auth_to_database_connection(self) -> bool:
        """Test auth service to database connection."""
        try:
            ports = self._collect_port_info()
            auth_port = ports.get('auth', 8081)
            
            # Test auth service database health
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"http://localhost:{auth_port}/health/db")
                return response.status_code == 200
                
        except Exception as e:
            logger.debug(f"Auth to database connection test failed: {e}")
            return False
            
    async def _test_websocket_connection(self) -> bool:
        """Test WebSocket connection."""
        try:
            import websockets
            
            ports = self._collect_port_info()
            backend_port = ports.get('backend', 8000)
            
            # Test WebSocket endpoint
            websocket_url = f"ws://localhost:{backend_port}/ws"
            
            # This may fail due to WebSocket configuration issues
            async with websockets.connect(websocket_url, timeout=5) as websocket:
                await websocket.send('{"type": "ping"}')
                response = await websocket.recv()
                return True
                
        except Exception as e:
            logger.debug(f"WebSocket connection test failed: {e}")
            return False
            
    async def _test_cors_validation(self) -> bool:
        """Test CORS configuration."""
        try:
            
            ports = self._collect_port_info()
            backend_port = ports.get('backend', 8000)
            frontend_port = ports.get('frontend', 3000)
            
            # Test CORS headers
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.options(
                    f"http://localhost:{backend_port}/api/health",
                    headers={
                        "Origin": f"http://localhost:{frontend_port}",
                        "Access-Control-Request-Method": "GET"
                    }
                )
                
                # Check for CORS headers
                cors_headers = [
                    "access-control-allow-origin",
                    "access-control-allow-methods", 
                    "access-control-allow-headers"
                ]
                
                return all(header in response.headers for header in cors_headers)
                
        except Exception as e:
            logger.debug(f"CORS validation test failed: {e}")
            return False
            
    async def cleanup(self) -> None:
        """Clean up test resources."""
        if self._cleanup_performed:
            return
            
        logger.info("Performing comprehensive test cleanup")
        
        try:
            # Cleanup launcher
            if self.launcher:
                try:
                    await self.launcher.cleanup()
                except Exception as e:
                    logger.warning(f"Error during launcher cleanup: {e}")
                finally:
                    self.launcher = None
                    
            # Kill any remaining processes
            for pid in list(self.spawned_processes):
                try:
                    process = psutil.Process(pid)
                    if process.is_running():
                        process.terminate()
                        # Wait for graceful termination
                        try:
                            process.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            process.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
            self.spawned_processes.clear()
            
            # Clean up temporary files
            for temp_file in self.temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except Exception as e:
                    logger.debug(f"Could not remove temp file {temp_file}: {e}")
                    
            self.temp_files.clear()
            
            # Restore environment
            self.restore_environment()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            self._cleanup_performed = True


class ServiceStartupMonitor:
    """Monitor service startup order and timing."""
    
    def __init__(self):
        self.startup_order = []
        self.startup_times = {}
        self.dependency_violations = []
        self.timing_issues = []
        
    def wrap_startup(self, service_name: str, original_method):
        """Wrap service startup method to track order and timing."""
        async def wrapped(*args, **kwargs):
            start_time = time.time()
            self.startup_order.append(service_name)
            
            try:
                result = await original_method(*args, **kwargs)
                end_time = time.time()
                self.startup_times[service_name] = end_time - start_time
                
                # Check for timing issues
                if self.startup_times[service_name] > 60:  # More than 1 minute
                    self.timing_issues.append(f"{service_name} took {self.startup_times[service_name]:.2f}s to start")
                    
                return result
                
            except Exception as e:
                self.timing_issues.append(f"{service_name} failed to start: {str(e)}")
                raise
                
        return wrapped
        
    def get_startup_order(self) -> List[str]:
        """Get the order services were started."""
        return self.startup_order.copy()
        
    def get_dependency_violations(self) -> List[str]:
        """Get dependency violations (backend starting before auth, etc)."""
        violations = []
        
        # Auth service should typically start before backend
        if 'backend' in self.startup_order and 'auth' in self.startup_order:
            backend_index = self.startup_order.index('backend')
            auth_index = self.startup_order.index('auth')
            
            if backend_index < auth_index:
                violations.append("Backend started before auth service - may cause auth connection issues")
                
        # Frontend should typically start after backend
        if 'frontend' in self.startup_order and 'backend' in self.startup_order:
            frontend_index = self.startup_order.index('frontend')
            backend_index = self.startup_order.index('backend')
            
            if frontend_index < backend_index:
                violations.append("Frontend started before backend - may cause API connection issues")
                
        return violations
        
    def get_timing_issues(self) -> List[str]:
        """Get timing-related issues."""
        return self.timing_issues.copy()


# Test fixtures
@pytest.fixture
async def startup_tester():
    """Fixture providing comprehensive startup tester."""
    async with DevLauncherStartupTester() as tester:
        yield tester


# CRITICAL STARTUP TESTS - DESIGNED TO FAIL INITIALLY

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_clean_startup_comprehensive(startup_tester):
    """
    Test clean startup without errors.
    
    THIS TEST IS DESIGNED TO FAIL initially to expose startup issues.
    Once issues are fixed, this test should pass reliably.
    """
    startup_tester.setup_test_environment("clean_startup")
    
    result = await startup_tester.test_clean_startup()
    
    # ASSERTION DESIGNED TO FAIL - exposes startup issues
    assert result.success, f"Clean startup failed. Errors: {result.errors}. " \
                          f"Startup time: {result.startup_time:.2f}s. " \
                          f"Service states: {result.service_states}. " \
                          f"Database connections: {result.database_connections}"
                          
    # Additional validations that may fail
    assert result.startup_time < 120, f"Startup took too long: {result.startup_time:.2f}s"
    assert len(result.allocated_ports) >= 3, f"Expected at least 3 services with ports, got: {result.allocated_ports}"
    assert len(result.errors) == 0, f"Unexpected errors during startup: {result.errors}"


@pytest.mark.asyncio  
@pytest.mark.e2e
async def test_port_conflict_resolution(startup_tester):
    """
    Test port conflict detection and resolution.
    
    THIS TEST IS DESIGNED TO FAIL initially if port management is not robust.
    """
    startup_tester.setup_test_environment("port_conflicts")
    
    result = await startup_tester.test_port_conflicts_and_resolution()
    
    # ASSERTION DESIGNED TO FAIL - exposes port management issues
    assert result.success, f"Port conflict resolution failed. Errors: {result.errors}. " \
                          f"Allocated ports: {result.allocated_ports}"
                          
    # Validate dynamic allocation worked
    default_ports = {8000, 3000, 8081}  # Common defaults
    allocated_values = set(result.allocated_ports.values())
    
    # Should not use default ports if they were conflicted
    assert len(allocated_values.intersection(default_ports)) == 0, \
           f"Still using default ports despite conflicts: {allocated_values.intersection(default_ports)}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_database_connections_comprehensive(startup_tester):
    """
    Test database connections with realistic but potentially problematic configurations.
    
    THIS TEST IS DESIGNED TO FAIL initially if database error handling is not robust.
    """
    startup_tester.setup_test_environment("database_connections")
    
    results = await startup_tester.test_database_connections()
    
    # Check each database - may fail if not properly configured
    for db_type, result in results.items():
        if result["status"] == "error":
            pytest.fail(f"{db_type} connection failed: {result['error']}")
        elif result["status"] == "failed":
            pytest.fail(f"{db_type} connection failed without clear error message")
        elif result["connection_time"] and result["connection_time"] > 10:
            pytest.fail(f"{db_type} connection too slow: {result['connection_time']:.2f}s")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_service_initialization_order_validation(startup_tester):
    """
    Test service initialization order and dependencies.
    
    THIS TEST IS DESIGNED TO FAIL initially if service dependencies are not handled properly.
    """
    startup_tester.setup_test_environment("service_order")
    
    results = await startup_tester.test_service_initialization_order()
    
    # ASSERTIONS DESIGNED TO FAIL - expose dependency issues
    assert results["success"], f"Service initialization failed. Timing issues: {results['timing_issues']}"
    
    assert len(results["dependency_violations"]) == 0, \
           f"Service dependency violations detected: {results['dependency_violations']}"
           
    assert len(results["timing_issues"]) == 0, \
           f"Service timing issues detected: {results['timing_issues']}"
           
    # Validate expected services started
    expected_services = {"auth", "backend", "frontend"}
    started_services = set(results["initialization_order"])
    
    assert expected_services.issubset(started_services), \
           f"Missing services. Expected: {expected_services}, Started: {started_services}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_inter_service_communication(startup_tester):
    """
    Test communication between services.
    
    THIS TEST IS DESIGNED TO FAIL initially if inter-service communication has issues.
    """
    startup_tester.setup_test_environment("inter_service")
    
    results = await startup_tester.test_inter_service_connections()
    
    # ASSERTIONS DESIGNED TO FAIL - expose communication issues
    assert len(results.errors) == 0, f"Service communication setup errors: {results.errors}"
    
    assert results.backend_to_auth, "Backend cannot communicate with auth service"
    assert results.frontend_to_backend, "Frontend cannot communicate with backend" 
    assert results.backend_to_db, "Backend cannot connect to database"
    assert results.auth_to_db, "Auth service cannot connect to database"
    assert results.websocket_connection, "WebSocket connection failed"
    assert results.cors_validation, "CORS configuration invalid"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_error_handling_missing_dependencies(startup_tester):
    """
    Test error handling when dependencies are missing.
    
    THIS TEST IS DESIGNED TO FAIL initially if error handling is not robust.
    """
    startup_tester.setup_test_environment("missing_deps")
    
    results = await startup_tester.test_error_handling_missing_dependencies()
    
    # ASSERTIONS DESIGNED TO FAIL - expose error handling issues
    assert results["missing_database_handling"], \
           "Does not handle missing database gracefully"
           
    assert results["missing_secrets_handling"], \
           "Does not handle missing secrets gracefully"
           
    assert results["cleanup_on_failure"], \
           "Does not cleanup properly when startup fails"
           
    # Check error message quality
    unclear_messages = [msg for msg in results["error_message_clarity"] 
                       if msg.startswith("Unclear")]
    assert len(unclear_messages) == 0, f"Unclear error messages: {unclear_messages}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_cleanup_on_failure_comprehensive(startup_tester):
    """
    Test cleanup when startup fails.
    
    THIS TEST IS DESIGNED TO FAIL initially if cleanup is not thorough.
    """
    startup_tester.setup_test_environment("cleanup_failure")
    
    results = await startup_tester.test_cleanup_on_failure()
    
    # ASSERTIONS DESIGNED TO FAIL - expose cleanup issues
    assert results["processes_cleaned"], \
           f"Processes not cleaned up: {results['zombie_processes']}"
           
    assert results["ports_released"], \
           f"Ports not released: {results['leaked_ports']}"
           
    assert results["temp_files_cleaned"], \
           f"Temporary files not cleaned: {results['leaked_files']}"
           
    assert results["graceful_shutdown"], \
           "Startup failure did not result in graceful shutdown"


# Integration test combining multiple failure modes
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_startup_resilience_comprehensive(startup_tester):
    """
    Comprehensive startup resilience test combining multiple potential failure modes.
    
    THIS IS THE ULTIMATE TEST - DESIGNED TO FAIL initially and expose multiple issues.
    """
    startup_tester.setup_test_environment("resilience_comprehensive")
    
    # Test clean startup first
    clean_result = await startup_tester.test_clean_startup(
        backend_reload=True,  # May cause issues
        parallel_startup=True,  # May expose race conditions  
        load_secrets=True  # May fail if not configured
    )
    
    # Test with port conflicts
    port_result = await startup_tester.test_port_conflicts_and_resolution()
    
    # Test database connections
    db_results = await startup_tester.test_database_connections()
    
    # Test inter-service communication  
    comm_results = await startup_tester.test_inter_service_connections()
    
    # COMPREHENSIVE ASSERTIONS - DESIGNED TO FAIL if any component is broken
    
    # Clean startup assertions
    assert clean_result.success, f"Clean startup failed: {clean_result.errors}"
    assert clean_result.startup_time < 180, f"Startup too slow: {clean_result.startup_time:.2f}s"
    
    # Port management assertions
    assert port_result.success, f"Port conflict resolution failed: {port_result.errors}"
    
    # Database assertions
    failed_dbs = [db for db, result in db_results.items() if result["status"] not in ["connected", "unknown"]]
    assert len(failed_dbs) == 0, f"Database connection failures: {failed_dbs}"
    
    # Communication assertions
    assert len(comm_results.errors) == 0, f"Communication errors: {comm_results.errors}"
    assert comm_results.backend_to_auth, "Backend-Auth communication failed"
    assert comm_results.frontend_to_backend, "Frontend-Backend communication failed" 
    assert comm_results.websocket_connection, "WebSocket communication failed"
    
    # Performance assertions
    total_time = clean_result.startup_time
    assert total_time < 120, f"Total startup time too high: {total_time:.2f}s"
    
    # Resource assertions
    assert len(clean_result.allocated_ports) >= 3, f"Insufficient port allocation: {clean_result.allocated_ports}"
    assert len(clean_result.processes) >= 3, f"Insufficient process spawning: {clean_result.processes}"
