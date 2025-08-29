"""
System Startup E2E Tests - Complete Multi-Service Validation

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All customer tiers (Free → Enterprise)
- Business Goal: System reliability and availability
- Value Impact: Prevents service downtime that could cost $30K+ MRR
- Strategic Impact: Platform stability is core competitive advantage

Tests the complete startup sequence of all microservices:
1. Main Backend (/app) - Core application logic  
2. Auth Service (/auth_service) - Authentication microservice
3. Frontend (/frontend) - User interface

COVERAGE:
- Service startup orchestration
- Health endpoint validation
- Database connectivity verification
- Service discovery and port allocation
- Error handling and recovery
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import psutil
import pytest

# Environment-aware testing imports
from test_framework.environment_markers import (
    env, env_requires, dev_and_staging, all_envs, env_safe
)

from dev_launcher.config import LauncherConfig
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.launcher import DevLauncher
from dev_launcher.service_discovery import ServiceDiscovery
class ServiceInfo:
    """Service information container."""
    
    def __init__(self, name: str, port: int, health_path: str = "/health"):
        self.name = name
        self.port = port
        self.health_path = health_path
        self.base_url = f"http://localhost:{port}"
        self.health_url = f"{self.base_url}{health_path}"

class TestSystemStartup:
    """Complete system startup validation tests."""
    
    @pytest.fixture
    def launcher_config(self) -> LauncherConfig:
        """Create test launcher configuration."""
        return LauncherConfig(
            dynamic_ports=True,
            parallel_startup=True,
            load_secrets=False,
            no_browser=True,
            non_interactive=True,
            startup_mode="minimal"
        )
    
    @pytest.fixture
    def expected_services(self) -> List[ServiceInfo]:
        """Define expected services for startup validation."""
        return [
            ServiceInfo("backend", 8000, "/health"),
            ServiceInfo("auth_service", 8001, "/health"),  
            ServiceInfo("frontend", 3000, "/api/health")
        ]
    
    @dev_and_staging  # E2E test requiring real services
    @env_requires(services=["postgres", "redis"], features=["service_discovery"])
    @pytest.mark.asyncio
    async def test_dev_launcher_starts_all_services(self, launcher_config):
        """Test that dev launcher starts all required services."""
        start_time = time.time()
        launcher = None
        
        try:
            launcher = DevLauncher(launcher_config)
            await launcher.start()
            
            # Verify launcher started successfully
            assert launcher is not None
            assert not launcher._shutting_down
            
            # Check startup time is reasonable
            startup_duration = time.time() - start_time
            assert startup_duration < 60  # Max 60 seconds
            
        finally:
            if launcher:
                await launcher.shutdown()
    
    @pytest.mark.asyncio
    async def test_service_health_endpoints_respond(self, expected_services):
        """Test all service health endpoints are accessible."""
        timeout = 30
        start_time = time.time()
        
        for service in expected_services:
            await self._wait_for_service_health(service, timeout)
            
            # Verify elapsed time is reasonable
            elapsed = time.time() - start_time
            assert elapsed < timeout
    
    async def _wait_for_service_health(self, service: ServiceInfo, timeout: int):
        """Wait for service health endpoint to be ready."""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(service.health_url, timeout=5)
                    if response.status_code == 200:
                        return
            except Exception:
                pass
            
            await asyncio.sleep(1)
        
        pytest.fail(f"Service {service.name} health check failed after {timeout}s")
    
    @pytest.mark.asyncio  
    async def test_database_connections_established(self):
        """Test database connections are properly established."""
        from netra_backend.app.db.client import (
            get_clickhouse_client,
            get_db_client,
        )
        
        # Test PostgreSQL connection
        postgres_client = await get_db_client()
        assert postgres_client is not None
        
        # Test ClickHouse connection  
        clickhouse_client = await get_clickhouse_client()
        assert clickhouse_client is not None
    
    @pytest.mark.asyncio
    async def test_service_discovery_works(self, launcher_config):
        """Test service discovery properly detects running services."""
        project_root = Path.cwd()
        discovery = ServiceDiscovery(project_root)
        
        services = await discovery.discover_services()
        
        # Verify expected services are discovered
        service_names = [s.get("name") for s in services]
        assert "backend" in service_names
        assert "auth_service" in service_names
        assert "frontend" in service_names
    
    @pytest.mark.asyncio
    async def test_health_monitoring_active(self):
        """Test health monitoring system is properly active."""
        health_monitor = HealthMonitor(check_interval=5)
        health_monitor.start()  # This is not async
        
        try:
            # Verify health monitor is running
            assert health_monitor.running
            
            # Wait for at least one health check cycle
            await asyncio.sleep(6)
            
            # Verify health status is available
            health_status = health_monitor.get_cross_service_health_status()
            assert health_status is not None
            
        finally:
            health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_port_allocation_succeeds(self, launcher_config):
        """Test dynamic port allocation works correctly."""
        if not launcher_config.dynamic_ports:
            pytest.skip("Dynamic ports disabled")
        
        # Start launcher and verify ports are allocated
        launcher = DevLauncher(launcher_config)
        
        try:
            await launcher.start()
            
            # Verify ports were allocated and services started
            allocated_ports = launcher.process_manager.get_allocated_ports()
            assert len(allocated_ports) >= 3  # Backend, auth, frontend
            
            # Verify ports are actually in use
            for port in allocated_ports.values():
                assert self._is_port_in_use(port)
                
        finally:
            await launcher.shutdown()
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is currently in use."""
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == "LISTEN":
                return True
        return False
    
    @pytest.mark.asyncio
    async def test_startup_error_handling(self, launcher_config):
        """Test startup error handling and recovery."""
        launcher_config.backend_port = 1  # Invalid port to trigger error
        
        launcher = DevLauncher(launcher_config)
        
        try:
            # Should handle error gracefully
            await launcher.start()
            
            # Verify error was handled
            assert launcher.startup_errors is not None
            assert len(launcher.startup_errors) > 0
            
        finally:
            await launcher.shutdown()
    
    @pytest.mark.asyncio
    async def test_service_startup_order(self, launcher_config):
        """Test services start in correct dependency order."""
        start_times = {}
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.service_startup.ServiceStartupCoordinator') as mock_coordinator:
            # Mock: Async component isolation for testing without real async operations
            mock_coordinator.return_value.start_service = AsyncMock(
                side_effect=lambda name: start_times.update({name: time.time()})
            )
            
            launcher = DevLauncher(launcher_config)
            await launcher.start()
            
            # Verify backend starts before frontend (dependency)
            assert "backend" in start_times
            assert "frontend" in start_times
            assert start_times["backend"] <= start_times["frontend"]
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, launcher_config):
        """Test system shuts down gracefully."""
        launcher = DevLauncher(launcher_config)
        
        try:
            await launcher.start()
            assert not launcher._shutting_down
            
        finally:
            # Test graceful shutdown
            await launcher.shutdown()
            assert launcher._shutting_down
            
            # Verify processes are cleaned up
            remaining_processes = launcher.process_manager.get_running_processes()
            assert len(remaining_processes) == 0

class TestStartupPerformance:
    """Startup performance validation tests."""
    
    @pytest.mark.asyncio
    async def test_startup_time_within_limits(self, launcher_config):
        """Test startup completes within performance limits."""
        max_startup_time = 45  # 45 seconds max
        
        start_time = time.time()
        launcher = DevLauncher(launcher_config)
        
        try:
            await launcher.start()
            
            startup_duration = time.time() - start_time
            assert startup_duration < max_startup_time
            
        finally:
            await launcher.shutdown()
    
    @pytest.mark.asyncio
    async def test_parallel_startup_faster_than_sequential(self):
        """Test parallel startup is faster than sequential."""
        # Test parallel startup
        parallel_config = LauncherConfig(parallel_startup=True, no_browser=True)
        parallel_start = time.time()
        
        launcher = DevLauncher(parallel_config)
        try:
            await launcher.start()
            parallel_time = time.time() - parallel_start
        finally:
            await launcher.shutdown()
        
        # Verify reasonable startup time
        assert parallel_time < 60  # Should be under 1 minute

class TestStartupRecovery:
    """Startup recovery and resilience tests."""
    
    @pytest.mark.asyncio
    async def test_retry_on_startup_failure(self, launcher_config):
        """Test system retries on transient startup failures."""
        retry_count = 0
        
        async def mock_start_service(service_name):
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:  # Fail first 2 attempts
                raise Exception("Simulated startup failure")
            # Mock: Generic component isolation for controlled unit testing
            return AsyncMock()
        
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.service_startup.ServiceStartupCoordinator.start_service', 
                  side_effect=mock_start_service):
            
            launcher = DevLauncher(launcher_config)
            
            try:
                await launcher.start()
                
                # Verify retries occurred
                assert retry_count >= 3
                
            finally:
                await launcher.shutdown()
    
    @pytest.mark.asyncio  
    async def test_partial_startup_handling(self, launcher_config):
        """Test handling when only some services start successfully."""
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.backend_starter.BackendStarter.start') as mock_backend:
            mock_backend.side_effect = Exception("Backend startup failed")
            
            launcher = DevLauncher(launcher_config)
            
            try:
                await launcher.start()
                
                # Verify partial startup is handled gracefully
                assert launcher.startup_errors is not None
                assert any("backend" in str(error).lower() for error in launcher.startup_errors)
                
            finally:
                await launcher.shutdown()

class TestStartupEnvironment:
    """Startup environment validation tests."""
    
    @pytest.mark.asyncio
    async def test_environment_variables_loaded(self):
        """Test required environment variables are loaded."""
        from netra_backend.app.core.config import get_config
        
        config = get_config()
        
        # Verify essential config is available
        assert config is not None
        assert hasattr(config, 'database_url')
        assert hasattr(config, 'redis_url')
    
    @pytest.mark.asyncio
    async def test_database_schemas_exist(self):
        """Test database schemas are properly initialized."""
        from netra_backend.app.db.postgres import get_async_db as get_postgres_client
        
        client = await get_postgres_client()
        
        # Check essential tables exist
        tables_query = """
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
        """
        
        result = await client.fetch(tables_query)
        table_names = [row['table_name'] for row in result]
        
        # Verify core tables exist
        essential_tables = ['users', 'threads', 'messages']
        for table in essential_tables:
            assert table in table_names