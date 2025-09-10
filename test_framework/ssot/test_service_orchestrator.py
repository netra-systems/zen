"""
TestServiceOrchestrator - SSOT for Test Service Management
=========================================================

Automatically starts and manages Docker services for tests to resolve localhost:8000 timeouts.
Integrates with UnifiedDockerManager following SSOT compliance patterns.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Infrastructure  
2. Business Goal: Eliminate localhost:8000 timeout failures in mission-critical tests
3. Value Impact: Prevent test failures that block deployment and development velocity
4. Revenue Impact: Protects $500K+ ARR by ensuring reliable chat functionality testing

Architecture Compliance:
- SSOT Integration: Uses UnifiedDockerManager as single source for Docker operations
- Environment Aware: Detects staging vs local and adjusts endpoints accordingly  
- Health Validation: Ensures services are truly ready before proceeding with tests
- Graceful Degradation: Falls back gracefully when Docker not available

Critical for GitHub Issue #136 - TestServiceOrchestrator Implementation.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Union, Any
from enum import Enum
from pathlib import Path

from shared.isolated_environment import get_env
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType, ServiceHealth
from test_framework.ssot.service_availability_detector import ServiceAvailabilityDetector

# Environment access through IsolatedEnvironment
env = get_env()

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Types of services that can be orchestrated for tests."""
    BACKEND = "backend"
    AUTH = "auth"
    POSTGRES = "postgres"
    REDIS = "redis"
    WEBSOCKET = "websocket"  # Part of backend but tracked separately for clarity


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration for different environments."""
    local_url: str
    staging_url: Optional[str] = None
    health_path: str = "/health"
    required_for_tests: bool = True
    timeout_seconds: int = 30


@dataclass 
class TestServiceConfig:
    """Configuration for test service orchestration."""
    auto_start_services: bool = True
    wait_for_health: bool = True
    health_check_timeout: int = 60
    environment_detection: bool = True
    fallback_to_staging: bool = True
    required_services: Set[ServiceType] = field(default_factory=lambda: {
        ServiceType.BACKEND, 
        ServiceType.POSTGRES, 
        ServiceType.REDIS
    })


class EnvironmentServiceResolver:
    """
    Resolves service endpoints based on environment detection.
    
    Provides environment-aware endpoint resolution to prevent localhost:8000 timeouts
    when services aren't available locally.
    """
    
    def __init__(self):
        self.env = get_env()
        self._service_endpoints = self._initialize_endpoints()
        
    def _initialize_endpoints(self) -> Dict[ServiceType, ServiceEndpoint]:
        """Initialize service endpoint mappings."""
        return {
            ServiceType.BACKEND: ServiceEndpoint(
                local_url="http://localhost:8000",
                staging_url="https://backend-staging-123456789-uc.a.run.app",
                health_path="/health"
            ),
            ServiceType.AUTH: ServiceEndpoint(
                local_url="http://localhost:8001", 
                staging_url="https://auth-staging-123456789-uc.a.run.app",
                health_path="/health"
            ),
            ServiceType.POSTGRES: ServiceEndpoint(
                local_url="postgresql://localhost:5432/netra_test",
                staging_url=None,  # Use staging connection string from env
                health_path="/health",
                required_for_tests=True
            ),
            ServiceType.REDIS: ServiceEndpoint(
                local_url="redis://localhost:6379",
                staging_url=None,  # Use staging connection string from env  
                health_path="/health",
                required_for_tests=True
            )
        }
    
    def get_endpoint_url(self, service_type: ServiceType, prefer_staging: bool = False) -> str:
        """
        Get the appropriate endpoint URL for a service.
        
        Args:
            service_type: Type of service to get endpoint for
            prefer_staging: If True, prefer staging over local even if local available
            
        Returns:
            Service endpoint URL
        """
        endpoint = self._service_endpoints.get(service_type)
        if not endpoint:
            raise ValueError(f"Unknown service type: {service_type}")
            
        # If prefer_staging and staging available, use staging
        if prefer_staging and endpoint.staging_url:
            return endpoint.staging_url
            
        # Check if local service is available
        if self._is_local_service_available(endpoint.local_url):
            return endpoint.local_url
            
        # Fall back to staging if available
        if endpoint.staging_url:
            logger.info(f"Local service {service_type} not available, using staging: {endpoint.staging_url}")
            return endpoint.staging_url
            
        # Return local as last resort (will likely fail but maintains expected behavior)
        logger.warning(f"No staging fallback for {service_type}, using local: {endpoint.local_url}")
        return endpoint.local_url
    
    def _is_local_service_available(self, url: str) -> bool:
        """Check if a local service is available."""
        try:
            import requests
            # Quick health check
            response = requests.get(f"{url}/health", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_websocket_url(self, prefer_staging: bool = False) -> str:
        """Get WebSocket URL based on backend endpoint."""
        backend_url = self.get_endpoint_url(ServiceType.BACKEND, prefer_staging)
        return backend_url.replace("http://", "ws://").replace("https://", "wss://")


class TestServiceOrchestrator:
    """
    SSOT for test service orchestration and management.
    
    Automatically starts required Docker services for tests and provides environment-aware
    endpoint resolution to prevent localhost:8000 timeout failures.
    
    Features:
    - Automatic service startup/shutdown via UnifiedDockerManager
    - Health check validation before proceeding with tests  
    - Environment detection and staging fallback
    - Graceful degradation when Docker not available
    - Service dependency mapping for different test categories
    """
    
    def __init__(self, config: Optional[TestServiceConfig] = None):
        self.config = config or TestServiceConfig()
        self.docker_manager = UnifiedDockerManager()
        self.resolver = EnvironmentServiceResolver()
        self.availability_detector = ServiceAvailabilityDetector()
        
        self._started_services: Set[str] = set()
        self._environment_type: Optional[EnvironmentType] = None
        
    async def setup_for_tests(self, test_category: str = "mission_critical") -> Dict[str, Any]:
        """
        Setup services required for the specified test category.
        
        Args:
            test_category: Category of tests being run (mission_critical, integration, etc.)
            
        Returns:
            Dictionary with service endpoints and status information
        """
        logger.info(f"Setting up services for test category: {test_category}")
        
        # Determine required services based on test category
        required_services = self._get_required_services_for_category(test_category)
        
        # Check current environment
        environment_info = await self._detect_environment()
        
        # Start services if needed and possible
        service_status = await self._ensure_services_available(required_services)
        
        # Build endpoint configuration
        endpoints = self._build_endpoint_config(required_services, environment_info)
        
        return {
            "endpoints": endpoints,
            "service_status": service_status,
            "environment": environment_info,
            "docker_available": self.docker_manager.is_docker_available(),
            "started_services": list(self._started_services)
        }
    
    async def teardown_after_tests(self) -> None:
        """Clean up services started for tests."""
        if not self._started_services:
            return
            
        logger.info(f"Cleaning up started services: {self._started_services}")
        
        try:
            # Only stop services we started (don't interfere with existing development)
            for service in self._started_services:
                await self.docker_manager.stop_service(service)
                
            self._started_services.clear()
            
        except Exception as e:
            logger.warning(f"Error during service cleanup: {e}")
    
    def _get_required_services_for_category(self, category: str) -> Set[ServiceType]:
        """Determine required services based on test category."""
        service_map = {
            "mission_critical": {ServiceType.BACKEND, ServiceType.POSTGRES, ServiceType.REDIS, ServiceType.AUTH},
            "integration": {ServiceType.BACKEND, ServiceType.POSTGRES, ServiceType.REDIS},
            "websocket": {ServiceType.BACKEND, ServiceType.REDIS},
            "unit": set(),  # Unit tests shouldn't need external services
            "api": {ServiceType.BACKEND, ServiceType.AUTH},
            "database": {ServiceType.POSTGRES, ServiceType.REDIS}
        }
        
        return service_map.get(category, {ServiceType.BACKEND})
    
    async def _detect_environment(self) -> Dict[str, Any]:
        """Detect current environment and service availability."""
        environment_info = {
            "type": "unknown",
            "docker_available": self.docker_manager.is_docker_available(),
            "local_services_detected": False,
            "staging_accessible": False
        }
        
        # Check if local services are running
        local_backend_available = self.resolver._is_local_service_available("http://localhost:8000")
        environment_info["local_services_detected"] = local_backend_available
        
        # Determine environment type
        if local_backend_available:
            environment_info["type"] = "local_development"
        elif environment_info["docker_available"]:
            environment_info["type"] = "docker_development"
        else:
            environment_info["type"] = "staging_fallback"
            
        return environment_info
    
    async def _ensure_services_available(self, required_services: Set[ServiceType]) -> Dict[str, Any]:
        """Ensure required services are available, starting them if needed."""
        service_status = {}
        
        if not self.config.auto_start_services:
            logger.info("Auto-start disabled, skipping service startup")
            return service_status
            
        if not self.docker_manager.is_docker_available():
            logger.info("Docker not available, skipping service startup")
            return service_status
        
        # Map service types to Docker service names
        service_name_map = {
            ServiceType.BACKEND: "backend",
            ServiceType.AUTH: "auth", 
            ServiceType.POSTGRES: "postgres",
            ServiceType.REDIS: "redis"
        }
        
        services_to_start = []
        for service_type in required_services:
            if service_type in service_name_map:
                service_name = service_name_map[service_type]
                services_to_start.append(service_name)
        
        if not services_to_start:
            return service_status
            
        logger.info(f"Starting required services: {services_to_start}")
        
        try:
            # Use UnifiedDockerManager to start services
            success = await self.docker_manager.ensure_services_running(
                services_to_start, 
                timeout=self.config.health_check_timeout
            )
            
            if success:
                self._started_services.update(services_to_start)
                service_status["started"] = services_to_start
                service_status["status"] = "healthy"
                
                # Wait a bit for services to fully initialize
                await asyncio.sleep(2)
                
            else:
                service_status["status"] = "failed"
                logger.error("Failed to start required services")
                
        except Exception as e:
            logger.error(f"Error starting services: {e}")
            service_status["status"] = "error"
            service_status["error"] = str(e)
            
        return service_status
    
    def _build_endpoint_config(self, required_services: Set[ServiceType], environment_info: Dict[str, Any]) -> Dict[str, str]:
        """Build endpoint configuration for tests."""
        endpoints = {}
        
        # Prefer staging if local services not detected and Docker not available
        prefer_staging = (
            environment_info["type"] == "staging_fallback" or
            not environment_info["local_services_detected"]
        )
        
        for service_type in required_services:
            try:
                if service_type == ServiceType.WEBSOCKET:
                    endpoints["websocket_url"] = self.resolver.get_websocket_url(prefer_staging)
                else:
                    key = f"{service_type.value}_url"
                    endpoints[key] = self.resolver.get_endpoint_url(service_type, prefer_staging)
                    
            except Exception as e:
                logger.warning(f"Could not resolve endpoint for {service_type}: {e}")
                
        return endpoints


# Convenience functions for common test patterns
async def setup_mission_critical_services() -> Dict[str, Any]:
    """Setup services specifically for mission-critical tests."""
    orchestrator = TestServiceOrchestrator()
    return await orchestrator.setup_for_tests("mission_critical")


async def setup_integration_services() -> Dict[str, Any]:
    """Setup services for integration tests."""
    orchestrator = TestServiceOrchestrator()
    return await orchestrator.setup_for_tests("integration")


def get_test_endpoints(service_info: Dict[str, Any]) -> Dict[str, str]:
    """Extract endpoint URLs from service info."""
    return service_info.get("endpoints", {})


def is_docker_environment(service_info: Dict[str, Any]) -> bool:
    """Check if tests are running in Docker environment."""
    env_info = service_info.get("environment", {})
    return env_info.get("type") == "docker_development"


def should_skip_docker_tests(service_info: Dict[str, Any]) -> bool:
    """Determine if Docker-dependent tests should be skipped."""
    return not service_info.get("docker_available", False)