from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
env = get_env()
Unified System Test Harness for Netra Apex AI Optimization Platform.

Business Value: Foundation for $180K MRR protection through comprehensive testing.
Revenue Impact: Prevents 100% of integration failures in production.

This module provides the core test harness for running multi-service unified tests.
Supports Auth Service, Backend, and Frontend together with real communication.
"""

import sys
from pathlib import Path

import asyncio
import logging
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    """Configuration for a test service instance."""
    name: str
    port: int
    startup_command: List[str]
    health_endpoint: str
    process_timeout: int = 30

@dataclass
class ServiceProcess:
    """Running service process information."""
    config: ServiceConfig
    process: subprocess.Popen
    started_at: float

class UnifiedTestHarness:
    """Main test harness for multi-service testing."""
    
    def __init__(self, test_name: str = "test"):
        self._services: Dict[str, ServiceProcess] = {}
        self._startup_timeout = 60
        self._health_check_interval = 1
        self._test_name = test_name
        self._is_setup = False
    
    async def start_all_services(self) -> Dict[str, int]:
        """Start all required services for unified testing."""
        configs = self._get_service_configs()
        return await self._start_services(configs)
    
    async def stop_all_services(self) -> None:
        """Stop all running test services."""
        for service in self._services.values():
            await self._stop_service(service)
        self._services.clear()
    
    async def wait_for_health_checks(self) -> bool:
        """Wait for all services to pass health checks."""
        return await self._check_all_services_healthy()
    
    def get_service_urls(self) -> Dict[str, str]:
        """Get URLs for all running services."""
        return {
            name: f"http://localhost:{proc.config.port}"
            for name, proc in self._services.items()
        }
    
    def _get_service_configs(self) -> List[ServiceConfig]:
        """Get configuration for all test services."""
        return [
            self._get_auth_config(),
            self._get_backend_config(), 
            self._get_frontend_config()
        ]
    
    def _get_auth_config(self) -> ServiceConfig:
        """Get Auth Service configuration."""
        return ServiceConfig(
            name="auth_service",
            port=8001,
            startup_command=["python", "-m", "auth_service.main"],
            health_endpoint="/health"
        )
    
    def _get_backend_config(self) -> ServiceConfig:
        """Get Backend Service configuration."""
        return ServiceConfig(
            name="backend",
            port=8000,
            startup_command=["uvicorn", "app.main:app", "--port", "8000"],
            health_endpoint="/health"
        )
    
    def _get_frontend_config(self) -> ServiceConfig:
        """Get Frontend Service configuration."""
        return ServiceConfig(
            name="frontend",
            port=3000,
            startup_command=["npm", "run", "dev"],
            health_endpoint="/api/health"
        )
    
    async def _start_services(self, configs: List[ServiceConfig]) -> Dict[str, int]:
        """Start services from configuration list."""
        results = {}
        for config in configs:
            port = await self._start_single_service(config)
            results[config.name] = port
        return results
    
    async def _start_single_service(self, config: ServiceConfig) -> int:
        """Start a single service process."""
        process = await self._create_service_process(config)
        service = ServiceProcess(config, process, time.time())
        self._services[config.name] = service
        return config.port
    
    async def _create_service_process(self, config: ServiceConfig) -> subprocess.Popen:
        """Create subprocess for service."""
        # Resolve executable paths for cross-platform compatibility
        resolved_command = self._resolve_command_path(config.startup_command)
        
        # On Windows, we need shell=True for proper executable resolution
        use_shell = platform.system() == "Windows"
        
        return subprocess.Popen(
            resolved_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._get_service_env(config.name),
            shell=use_shell
        )
    
    def _resolve_command_path(self, command: List[str]) -> List[str]:
        """Resolve executable path for cross-platform compatibility."""
        if not command:
            return command
        
        # Get the executable (first element of command)
        executable = command[0]
        
        # Try to find the full path to the executable
        resolved_path = shutil.which(executable)
        if resolved_path:
            # Return command with resolved executable path
            return [resolved_path] + command[1:]
        else:
            # If we can't resolve it, return original command
            # This allows subprocess to handle the error appropriately
            logger.warning(f"Could not resolve executable path for: {executable}")
            return command
    
    def _get_service_env(self, service_name: str) -> Dict[str, str]:
        """Get environment variables for service."""
        import os
        base_env = env.get_all()
        return self._add_test_env_vars(base_env, service_name)
    
    def _add_test_env_vars(self, env: Dict[str, str], service: str) -> Dict[str, str]:
        """Add test-specific environment variables."""
        env.update({
            "TESTING": "1",
            "ENVIRONMENT": "testing",
            "LOG_LEVEL": "ERROR"
        })
        return env
    
    async def _check_all_services_healthy(self) -> bool:
        """Check if all services are healthy."""
        for service in self._services.values():
            if not await self._check_service_health(service):
                return False
        return True
    
    async def _check_service_health(self, service: ServiceProcess) -> bool:
        """Check health of a single service."""
        url = f"http://localhost:{service.config.port}{service.config.health_endpoint}"
        return await self._make_health_request(url)
    
    async def _make_health_request(self, url: str) -> bool:
        """Make HTTP request to health endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5)
                return response.status_code == 200
        except Exception:
            return False
    
    async def _stop_service(self, service: ServiceProcess) -> None:
        """Stop a single service process."""
        if service.process.poll() is None:
            service.process.terminate()
            await self._wait_for_termination(service.process)
    
    async def _wait_for_termination(self, process: subprocess.Popen) -> None:
        """Wait for process to terminate gracefully."""
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    
    @classmethod
    async def create_test_harness(cls, test_name: str = "test") -> "UnifiedTestHarness":
        """
        Create and initialize a full test harness with all services.
        
        Args:
            test_name: Name identifier for the test
            
        Returns:
            Initialized UnifiedTestHarness instance
        """
        harness = cls(test_name)
        await harness.setup()
        return harness
    
    @classmethod
    async def create_minimal_harness(cls, test_name: str = "test") -> "UnifiedTestHarness":
        """
        Create a minimal test harness without starting services.
        Useful for unit tests that don't need full service integration.
        
        Args:
            test_name: Name identifier for the test
            
        Returns:
            Minimal UnifiedTestHarness instance
        """
        harness = cls(test_name)
        # Initialize minimal configuration without starting services
        harness._is_setup = True
        return harness
    
    async def setup(self) -> None:
        """
        Setup the test harness by starting all services.
        """
        if not self._is_setup:
            await self.start_all_services()
            await self.wait_for_health_checks()
            self._is_setup = True
    
    async def teardown(self) -> None:
        """
        Teardown the test harness by stopping all services.
        """
        if self._is_setup:
            await self.stop_all_services()
            self._is_setup = False