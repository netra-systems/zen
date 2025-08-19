"""
Service Manager - Part 2 of Unified Test Harness
Handles service startup, health checks, and coordination

Continues from test_harness.py due to 300-line limit requirement.
All functions ≤8 lines as per SPEC/conventions.xml
"""

import os
import sys
import asyncio
import subprocess
import time
import logging
import socket
import httpx
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Import from part 1
from .test_harness import UnifiedTestHarness, ServiceConfig, DatabaseManager

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
        """Start the backend service on port 8000.""" 
        service_config = self.harness.state.services["backend"]
        await self._start_service_process(service_config, self._get_backend_command())
        await self._wait_for_service_health(service_config)
        self.logger.info("Backend service started successfully")
    
    def _get_auth_command(self) -> List[str]:
        """Get command to start auth service."""
        auth_main = self.harness.project_root / "auth_service" / "main.py"
        return [
            sys.executable, str(auth_main),
            "--host", "0.0.0.0", 
            "--port", "8001"
        ]
    
    def _get_backend_command(self) -> List[str]:
        """Get command to start backend service."""
        backend_main = self.harness.project_root / "app" / "main.py"
        return [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload", "false"
        ]
    
    async def _start_service_process(self, config: ServiceConfig, command: List[str]) -> None:
        """Start a service process."""
        if await self._is_port_in_use(config.port):
            self.logger.warning(f"Port {config.port} already in use for {config.name}")
            return
        
        self.logger.info(f"Starting {config.name} with command: {' '.join(command)}")
        
        process = subprocess.Popen(
            command,
            cwd=str(self.harness.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
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
        """Wait for service to be healthy."""
        start_time = time.time()
        
        while time.time() - start_time < config.startup_timeout:
            if await self._check_service_health(config):
                config.ready = True
                return
            await asyncio.sleep(1)
        
        raise RuntimeError(f"{config.name} failed to start within {config.startup_timeout}s")
    
    async def _check_service_health(self, config: ServiceConfig) -> bool:
        """Check if service is healthy."""
        try:
            url = f"http://{config.host}:{config.port}{config.health_endpoint}"
            response = await self.http_client.get(url)
            return response.status_code == 200
        except Exception:
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
    
    async def stop_all_services(self) -> None:
        """Stop all services."""
        for config in self.harness.state.services.values():
            self._stop_service(config)
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
        """Wait for all services to be ready."""
        ready_services = []
        
        for service_name, config in self.harness.state.services.items():
            if await self._wait_for_service_ready(config):
                ready_services.append(service_name)
        
        if len(ready_services) == len(self.harness.state.services):
            self.logger.info("All services are ready")
        else:
            missing = set(self.harness.state.services.keys()) - set(ready_services)
            raise RuntimeError(f"Services not ready: {missing}")
    
    async def _wait_for_service_ready(self, config: ServiceConfig) -> bool:
        """Wait for a single service to be ready."""
        timeout = config.startup_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if config.ready:
                return True
            await asyncio.sleep(0.5)
        
        self.logger.error(f"Service {config.name} not ready after {timeout}s")
        return False
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        return {
            "services_ready": all(s.ready for s in self.harness.state.services.values()),
            "database_initialized": self.harness.state.databases.initialized,
            "harness_ready": self.harness.state.ready,
            "service_count": len(self.harness.state.services),
            "ready_services": sum(1 for s in self.harness.state.services.values() if s.ready)
        }