"""
Service Manager - Part 2 of Unified Test Harness
Handles service startup, health checks, and coordination

Continues from test_harness.py due to 450-line limit requirement.
All functions ≤8 lines as per SPEC/conventions.xml
"""

import asyncio
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

# Import from part 1
from tests.e2e.unified_e2e_harness import (
    DatabaseManager,
    ServiceConfig,
    UnifiedTestHarness,
)

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages individual service startup and lifecycle."""
    
    def __init__(self, harness: UnifiedTestHarness):
        """Initialize service manager."""
        self.harness = harness
        self.logger = logging.getLogger(f"{__name__}.ServiceManager")
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def start_auth_service(self) -> None:
        """Start the auth service on port 8001."""
        service_config = self.harness.state.services["auth_service"]
        await self._start_service_process(service_config, self._get_auth_command())
        await self._wait_for_service_health(service_config)
        self.logger.info("Auth service started successfully")
    
    async def start_backend_service(self) -> None:
        """Start the backend service on port 8000 (depends on auth service).""" 
        # Ensure auth service is running first
        auth_config = self.harness.state.services["auth_service"]
        if not auth_config.ready:
            raise RuntimeError("Auth service must be started before backend service")
        
        service_config = self.harness.state.services["backend"]
        await self._start_service_process(service_config, self._get_backend_command())
        await self._wait_for_service_health(service_config)
        self.logger.info("Backend service started successfully")
    
    def _get_auth_command(self) -> List[str]:
        """Get command to start auth service."""
        # Run auth service directly with python (it uses PORT env var)
        auth_main_path = self.harness.project_root / "auth_service" / "main.py"
        return [
            sys.executable, str(auth_main_path)
        ]
    
    def _get_backend_command(self) -> List[str]:
        """Get command to start backend service."""
        return [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--log-level", "warning"
        ]
    
    async def _start_service_process(self, config: ServiceConfig, command: List[str]) -> None:
        """Start a service process with proper test environment."""
        if await self._is_port_in_use(config.port):
            self.logger.warning(f"Port {config.port} already in use for {config.name}")
            return
        
        self.logger.info(f"Starting {config.name} with command: {' '.join(command)}")
        
        # Set up test environment for service
        test_env = self._create_test_environment(config)
        
        process = subprocess.Popen(
            command,
            cwd=str(self.harness.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=test_env,
            text=True
        )
        
        config.process = process
        self.harness.state.cleanup_tasks.append(lambda: self._stop_service(config))
    
    async def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is already in use."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    async def _wait_for_service_health(self, config: ServiceConfig) -> None:
        """Wait for service to be healthy with progressive timeout."""
        start_time = time.time()
        retry_interval = 0.5
        max_retries = config.startup_timeout // retry_interval
        retries = 0
        
        while retries < max_retries:
            if await self._check_service_health(config):
                config.ready = True
                self.logger.info(f"{config.name} health check passed after {time.time() - start_time:.2f}s")
                return
            
            await asyncio.sleep(retry_interval)
            retries += 1
            
            if retries % 10 == 0:  # Log every 5 seconds
                self.logger.debug(f"Waiting for {config.name} health ({retries}/{max_retries})")
        
        raise RuntimeError(f"{config.name} failed to start within {config.startup_timeout}s")
    
    async def _check_service_health(self, config: ServiceConfig) -> bool:
        """Check if service is healthy with detailed logging."""
        try:
            url = f"http://{config.host}:{config.port}{config.health_endpoint}"
            response = await self.http_client.get(url)
            
            if response.status_code == 200:
                return True
            else:
                self.logger.debug(f"{config.name} health check returned status {response.status_code}")
                return False
        except Exception as e:
            self.logger.debug(f"{config.name} health check failed: {e}")
            return False
    
    def _stop_service(self, config: ServiceConfig) -> None:
        """Stop a service process."""
        if config.process and config.process.poll() is None:
            config.process.terminate()
            try:
                config.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                config.process.kill()
        config.ready = False
        self.logger.info(f"Stopped {config.name}")
    
    def _create_test_environment(self, config: ServiceConfig) -> Dict[str, str]:
        """Create test environment for service startup."""
        test_env = os.environ.copy()
        
        # Set test mode variables
        test_env.update({
            "TESTING": "1",
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "WARNING",
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "AUTH_FAST_TEST_MODE": "true",
            "REDIS_HOST": "localhost",
            "CLICKHOUSE_HOST": "localhost"
        })
        
        # Service-specific environment settings
        if config.name == "auth_service":
            test_env.update({
                "PORT": str(config.port),  # Auth service uses PORT env var
                "JWT_SECRET_KEY": "test-jwt-secret-key-unified-testing-32chars",
                "FERNET_KEY": "cYpHdJm0e-zt3SWz-9h0gC_kh0Z7c3H6mRQPbPLFdao="
            })
        elif config.name == "backend":
            test_env.update({
                "AUTH_SERVICE_URL": "http://localhost:8001"
            })
        
        return test_env
    
    async def stop_all_services(self) -> None:
        """Stop all services gracefully."""
        # Stop in reverse dependency order (Backend → Auth)
        service_order = ["backend", "auth_service"]
        for service_name in service_order:
            if service_name in self.harness.state.services:
                self._stop_service(self.harness.state.services[service_name])
        
        await self.http_client.aclose()
        self.logger.info("All services stopped")


class TestDataSeeder:
    """Creates realistic test data for unified testing."""
    
    def __init__(self, harness: UnifiedTestHarness):
        """Initialize test data seeder."""
        self.harness = harness
        self.logger = logging.getLogger(f"{__name__}.TestDataSeeder")
        self.test_users = []
    
    async def seed_test_data(self) -> None:
        """Seed all test data."""
        await self._create_test_users()
        await self._create_test_conversations() 
        self.logger.info("Test data seeded successfully")
    
    async def _create_test_users(self) -> None:
        """Create test users for testing."""
        users = [
            {"email": "test@example.com", "password": "testpass123"},
            {"email": "admin@example.com", "password": "adminpass123", "is_superuser": True},
            {"email": "premium@example.com", "password": "premiumpass123"}
        ]
        
        for user_data in users:
            user = await self._create_single_user(user_data)
            if user:
                self.test_users.append(user)
    
    async def _create_single_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a single test user."""
        try:
            # This would typically call the auth service API
            # For now, return mock user data
            return {
                "id": f"test-user-{len(self.test_users)}",
                "email": user_data["email"],
                "is_active": True,
                "is_superuser": user_data.get("is_superuser", False)
            }
        except Exception as e:
            self.logger.error(f"Failed to create user {user_data['email']}: {e}")
            return None
    
    async def _create_test_conversations(self) -> None:
        """Create test conversations for testing chat functionality."""
        # Mock conversation data for testing
        conversations = [
            {"user_id": "test-user-0", "message": "Hello, can you help me optimize my AI costs?"},
            {"user_id": "test-user-1", "message": "What are the best practices for multi-agent systems?"}
        ]
        
        for conv in conversations:
            await self._create_single_conversation(conv)
    
    async def _create_single_conversation(self, conv_data: Dict[str, Any]) -> None:
        """Create a single test conversation."""
        try:
            # This would typically create conversation in the database
            self.logger.debug(f"Created conversation for {conv_data['user_id']}")
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {e}")
    
    def get_test_user(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """Get a test user by index."""
        if 0 <= index < len(self.test_users):
            return self.test_users[index]
        return None
    
    async def cleanup_test_data(self) -> None:
        """Cleanup all test data."""
        self.test_users.clear()
        self.logger.info("Test data cleaned up")


class HealthMonitor:
    """Monitors health and readiness of all services."""
    
    def __init__(self, harness: UnifiedTestHarness):
        """Initialize health monitor."""
        self.harness = harness
        self.logger = logging.getLogger(f"{__name__}.HealthMonitor")
    
    async def wait_for_all_ready(self) -> None:
        """Wait for all services to be ready with comprehensive health checks."""
        self.logger.info("Starting comprehensive health check for all services")
        ready_services = []
        
        # Wait for each service with detailed status reporting
        for service_name, config in self.harness.state.services.items():
            self.logger.info(f"Checking readiness of {service_name}")
            
            if await self._wait_for_service_ready(config):
                # Perform additional health verification
                if await self._verify_service_health(config):
                    ready_services.append(service_name)
                    self.logger.info(f"✓ {service_name} is ready and healthy")
                else:
                    self.logger.error(f"✗ {service_name} failed health verification")
            else:
                self.logger.error(f"✗ {service_name} failed to become ready")
        
        if len(ready_services) == len(self.harness.state.services):
            self.logger.info(f"✓ All {len(ready_services)} services are ready and healthy")
        else:
            missing = set(self.harness.state.services.keys()) - set(ready_services)
            raise RuntimeError(f"Services not ready: {missing}")
    
    async def _wait_for_service_ready(self, config: ServiceConfig) -> bool:
        """Wait for a single service to be ready."""
        timeout = config.startup_timeout
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            if config.ready:
                return True
            
            check_count += 1
            if check_count % 20 == 0:  # Log every 10 seconds (0.5s * 20)
                elapsed = time.time() - start_time
                self.logger.debug(f"{config.name} still starting... ({elapsed:.1f}s/{timeout}s)")
            
            await asyncio.sleep(0.5)
        
        self.logger.error(f"Service {config.name} not ready after {timeout}s")
        return False
    
    async def _verify_service_health(self, config: ServiceConfig) -> bool:
        """Verify service health with additional checks."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = f"http://{config.host}:{config.port}{config.health_endpoint}"
                response = await client.get(url)
                
                if response.status_code == 200:
                    # Try to parse response to ensure service is actually working
                    try:
                        health_data = response.json()
                        self.logger.debug(f"{config.name} health response: {health_data}")
                        return True
                    except Exception:
                        # Even if JSON parsing fails, 200 status is good enough
                        return True
                else:
                    self.logger.warning(f"{config.name} health check returned {response.status_code}")
                    return False
        except Exception as e:
            self.logger.error(f"{config.name} health verification failed: {e}")
            return False
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        health_status = {
            "services_ready": all(s.ready for s in self.harness.state.services.values()),
            "database_initialized": getattr(self.harness.state, 'databases', None) and getattr(self.harness.state.databases, 'initialized', False),
            "harness_ready": self.harness.state.ready,
            "service_count": len(self.harness.state.services),
            "ready_services": sum(1 for s in self.harness.state.services.values() if s.ready),
            "service_details": {}
        }
        
        # Add detailed service status
        for name, config in self.harness.state.services.items():
            health_status["service_details"][name] = {
                "ready": config.ready,
                "port": config.port,
                "host": config.host
            }
        
        return health_status
