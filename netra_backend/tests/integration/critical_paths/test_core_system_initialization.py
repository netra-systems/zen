"""Core System Initialization Critical Path Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers)  
- Business Goal: Platform Stability and Service Availability
- Value Impact: Ensures 99.9% uptime SLA, prevents $15K-50K MRR loss from outages
- Strategic Impact: Foundation for all customer-facing features and revenue generation

Critical Path: Service discovery -> Health checks -> Database readiness -> Agent initialization -> WebSocket availability
Coverage: Microservice startup orchestration, dependency resolution, graceful degradation
"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from test_framework import setup_test_path
from pathlib import Path
import sys

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.config import Settings
from netra_backend.app.services.database.connection_manager import (

    DatabaseConnectionManager,

)

from netra_backend.app.services.health_check_service import HealthCheckService
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

class SystemInitializationManager:

    """Manages system initialization testing with real component validation."""
    
    def __init__(self):

        self.services = {}

        self.health_status = {}

        self.startup_times = {}
        
    async def start_service(self, service_name: str, service_class, **kwargs) -> bool:

        """Start a service and track initialization time."""

        start_time = time.time()

        try:

            if service_name == "database":

                service = DatabaseConnectionManager()

                await service.initialize()

            elif service_name == "redis":

                service = RedisService()

                await service.connect()

            elif service_name == "websocket":

                service = WebSocketManager()

                await service.initialize()

            elif service_name == "health_check":

                service = HealthCheckService()

                await service.start()

            else:

                service = service_class(**kwargs)

                if hasattr(service, 'initialize'):

                    await service.initialize()
                    
            self.services[service_name] = service

            self.startup_times[service_name] = time.time() - start_time

            self.health_status[service_name] = "healthy"

            return True

        except Exception as e:

            logger.error(f"Failed to start {service_name}: {e}")

            self.health_status[service_name] = f"unhealthy: {str(e)}"

            return False
    
    async def check_service_health(self, service_name: str) -> Dict:

        """Check individual service health status."""

        if service_name not in self.services:

            return {"status": "not_started", "details": "Service not initialized"}
            
        service = self.services[service_name]

        try:

            if hasattr(service, 'health_check'):

                result = await service.health_check()

                return {"status": "healthy", "details": result}

            elif hasattr(service, 'ping'):

                await service.ping()

                return {"status": "healthy", "details": "ping successful"}

            else:

                return {"status": "healthy", "details": "service running"}

        except Exception as e:

            return {"status": "unhealthy", "details": str(e)}
    
    async def get_system_health(self) -> Dict:

        """Get comprehensive system health status."""

        health_results = {}

        for service_name in self.services:

            health_results[service_name] = await self.check_service_health(service_name)
        
        overall_healthy = all(

            result["status"] == "healthy" 

            for result in health_results.values()

        )
        
        return {

            "overall_status": "healthy" if overall_healthy else "degraded",

            "services": health_results,

            "startup_times": self.startup_times,

            "timestamp": time.time()

        }

@pytest.fixture

async def system_manager():

    """Create system initialization manager for testing."""

    manager = SystemInitializationManager()

    yield manager
    
    # Cleanup

    for service in manager.services.values():

        if hasattr(service, 'shutdown'):

            try:

                await service.shutdown()

            except Exception:

                pass

@pytest.mark.asyncio

async def test_microservice_startup_orchestration(system_manager):

    """Test that all microservices start in correct dependency order."""
    # Define startup sequence based on dependencies

    startup_sequence = [

        ("redis", RedisService),

        ("database", DatabaseConnectionManager), 

        ("health_check", HealthCheckService),

        ("websocket", WebSocketManager),

    ]
    
    startup_results = []
    
    # Start services in dependency order

    for service_name, service_class in startup_sequence:

        result = await system_manager.start_service(service_name, service_class)

        startup_results.append((service_name, result))
        
        # Verify service started before continuing

        assert result, f"Failed to start {service_name}"
        
        # Allow time for initialization

        await asyncio.sleep(0.1)
    
    # Verify all services started successfully

    assert all(result for _, result in startup_results)
    
    # Verify startup times are reasonable (< 5 seconds each)

    for service_name, startup_time in system_manager.startup_times.items():

        assert startup_time < 5.0, f"{service_name} took too long to start: {startup_time}s"
    
    # Verify health checks pass

    system_health = await system_manager.get_system_health()

    assert system_health["overall_status"] == "healthy"

@pytest.mark.asyncio

async def test_dependency_resolution_chain(system_manager):

    """Test that services properly handle dependency failures."""
    # Start Redis first

    redis_started = await system_manager.start_service("redis", RedisService)

    assert redis_started
    
    # Simulate database failure

    with patch('app.services.database.connection_manager.DatabaseConnectionManager.initialize', 

               side_effect=Exception("Database unavailable")):

        db_started = await system_manager.start_service("database", DatabaseConnectionManager)

        assert not db_started
    
    # Verify dependent services handle graceful degradation

    health_started = await system_manager.start_service("health_check", HealthCheckService)
    # Health check should start even if database fails (degraded mode)

    assert health_started
    
    # Verify system reports degraded status

    system_health = await system_manager.get_system_health()

    assert system_health["overall_status"] == "degraded"

    assert system_health["services"]["database"]["status"] == "unhealthy"

@pytest.mark.asyncio

async def test_health_check_endpoints_integration(system_manager):

    """Test health check endpoints provide accurate service status."""
    # Start core services

    await system_manager.start_service("redis", RedisService)

    await system_manager.start_service("database", DatabaseConnectionManager)

    await system_manager.start_service("health_check", HealthCheckService)
    
    # Get health status

    health_status = await system_manager.get_system_health()
    
    # Verify health check structure

    assert "overall_status" in health_status

    assert "services" in health_status

    assert "startup_times" in health_status

    assert "timestamp" in health_status
    
    # Verify individual service health

    for service_name in ["redis", "database", "health_check"]:

        service_health = health_status["services"][service_name]

        assert service_health["status"] == "healthy"

        assert "details" in service_health
    
    # Verify startup time tracking

    for service_name in ["redis", "database", "health_check"]:

        assert service_name in health_status["startup_times"]

        assert health_status["startup_times"][service_name] > 0

@pytest.mark.asyncio 

async def test_graceful_shutdown_sequence(system_manager):

    """Test that services shut down gracefully in reverse dependency order."""
    # Start all services

    startup_sequence = [

        ("redis", RedisService),

        ("database", DatabaseConnectionManager),

        ("health_check", HealthCheckService),

        ("websocket", WebSocketManager),

    ]
    
    for service_name, service_class in startup_sequence:

        await system_manager.start_service(service_name, service_class)
    
    # Verify all services healthy

    initial_health = await system_manager.get_system_health()

    assert initial_health["overall_status"] == "healthy"
    
    # Shutdown in reverse order  

    shutdown_sequence = list(reversed(startup_sequence))
    
    for service_name, _ in shutdown_sequence:

        service = system_manager.services[service_name]

        if hasattr(service, 'shutdown'):

            start_time = time.time()

            await service.shutdown()

            shutdown_time = time.time() - start_time
            
            # Verify shutdown completed quickly (< 3 seconds)

            assert shutdown_time < 3.0, f"{service_name} shutdown took too long: {shutdown_time}s"
        
        # Remove from active services

        del system_manager.services[service_name]
    
    # Verify all services shut down

    assert len(system_manager.services) == 0

@pytest.mark.asyncio

async def test_startup_performance_benchmarks(system_manager):

    """Test that system startup meets performance requirements."""

    startup_sequence = [

        ("redis", RedisService),

        ("database", DatabaseConnectionManager),

        ("health_check", HealthCheckService),

        ("websocket", WebSocketManager),

    ]
    
    total_start_time = time.time()
    
    # Start all services

    for service_name, service_class in startup_sequence:

        await system_manager.start_service(service_name, service_class)
    
    total_startup_time = time.time() - total_start_time
    
    # Verify overall startup time < 15 seconds

    assert total_startup_time < 15.0, f"Total startup time too long: {total_startup_time}s"
    
    # Verify individual service startup times

    performance_requirements = {

        "redis": 2.0,      # Redis should start quickly

        "database": 5.0,   # Database may take longer  

        "health_check": 1.0, # Health check should be fast

        "websocket": 3.0,  # WebSocket initialization

    }
    
    for service_name, max_time in performance_requirements.items():

        actual_time = system_manager.startup_times[service_name]

        assert actual_time < max_time, f"{service_name} startup too slow: {actual_time}s > {max_time}s"
    
    # Verify system is healthy after startup

    final_health = await system_manager.get_system_health()

    assert final_health["overall_status"] == "healthy"