"""
Service-Aware Testing Framework

Provides intelligent test execution that adapts to available services.
Tests run meaningful validations even when some services are unavailable.

Business Value: Enables continuous integration without full infrastructure setup.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass

import pytest
from tests.e2e.real_services_manager import RealServicesManager, ServiceStatus


class ServiceAvailability(Enum):
    """Service availability states."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class TestExecutionStrategy:
    """Strategy for test execution based on service availability."""
    available_services: Set[str]
    unavailable_services: Set[str]
    test_mode: str  # 'full', 'partial', 'mock', 'skip'
    fallback_strategy: str  # 'staging', 'mock', 'skip'


class ServiceAwareTestManager:
    """
    Manages test execution based on service availability.
    
    Key Features:
    - Service discovery and health checking
    - Intelligent test categorization
    - Fallback strategy implementation
    - Graceful degradation for missing services
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.service_manager = RealServicesManager()
        self.service_status: Dict[str, ServiceAvailability] = {}
        
    async def discover_available_services(self) -> Dict[str, ServiceAvailability]:
        """Discover which services are currently available."""
        self.logger.info("Discovering available services...")
        
        # Check service health
        health_results = await self.service_manager.check_all_service_health()
        
        service_availability = {}
        
        for service_name, details in health_results.get("services", {}).items():
            if details["healthy"]:
                service_availability[service_name] = ServiceAvailability.AVAILABLE
            elif details.get("circuit_breaker_state") == "open":
                service_availability[service_name] = ServiceAvailability.UNAVAILABLE
            else:
                service_availability[service_name] = ServiceAvailability.DEGRADED
        
        # Check for essential services not reported
        essential_services = {"backend", "auth_service", "database", "websocket"}
        for service in essential_services:
            if service not in service_availability:
                service_availability[service] = ServiceAvailability.UNKNOWN
        
        self.service_status = service_availability
        return service_availability
    
    def determine_test_strategy(self, required_services: Set[str]) -> TestExecutionStrategy:
        """Determine optimal test execution strategy."""
        available = set()
        unavailable = set()
        
        for service in required_services:
            status = self.service_status.get(service, ServiceAvailability.UNKNOWN)
            if status == ServiceAvailability.AVAILABLE:
                available.add(service)
            else:
                unavailable.add(service)
        
        # Determine test mode
        if len(unavailable) == 0:
            test_mode = "full"
            fallback_strategy = "none"
        elif len(available) >= len(unavailable):
            test_mode = "partial"
            fallback_strategy = "staging" if self._staging_available() else "mock"
        else:
            test_mode = "mock"
            fallback_strategy = "staging" if self._staging_available() else "skip"
        
        return TestExecutionStrategy(
            available_services=available,
            unavailable_services=unavailable,
            test_mode=test_mode,
            fallback_strategy=fallback_strategy
        )
    
    def _staging_available(self) -> bool:
        """Check if staging environment is available."""
        # Check for staging environment indicators
        import os
        return (
            os.environ.get("ENVIRONMENT") == "staging" or
            os.environ.get("USE_STAGING_SERVICES") == "true" or
            "run.app" in os.environ.get("NETRA_BACKEND_URL", "")
        )
    
    def create_service_fixtures(self, strategy: TestExecutionStrategy) -> Dict[str, pytest.fixture]:
        """Create pytest fixtures based on execution strategy."""
        fixtures = {}
        
        for service in strategy.available_services:
            fixtures[f"{service}_client"] = self._create_real_service_fixture(service)
        
        for service in strategy.unavailable_services:
            if strategy.fallback_strategy == "staging":
                fixtures[f"{service}_client"] = self._create_staging_fixture(service)
            elif strategy.fallback_strategy == "mock":
                fixtures[f"{service}_client"] = self._create_mock_fixture(service)
            else:
                fixtures[f"{service}_client"] = self._create_skip_fixture(service)
        
        return fixtures
    
    def _create_real_service_fixture(self, service_name: str):
        """Create fixture for real service connection."""
        @pytest.fixture
        async def real_service_fixture():
            # Return real service connection
            if service_name == "database":
                from netra_backend.app.db.database_manager import get_database
                return await get_database()
            elif service_name == "redis":
                from netra_backend.app.services.redis_client import get_redis_client
                return await get_redis_client()
            # Add other services as needed
            return None
        
        return real_service_fixture
    
    def _create_staging_fixture(self, service_name: str):
        """Create fixture for staging service connection."""
        @pytest.fixture
        async def staging_service_fixture():
            # Configure for staging and return connection
            self.logger.info(f"Using staging service for {service_name}")
            # Implementation would connect to staging services
            return f"staging_{service_name}_connection"
        
        return staging_service_fixture
    
    def _create_mock_fixture(self, service_name: str):
        """Create mock fixture for unavailable service."""
        @pytest.fixture
        def mock_service_fixture():
            from unittest.mock import AsyncMock, MagicMock
            self.logger.warning(f"Using mock for unavailable service: {service_name}")
            return AsyncMock() if "database" in service_name else MagicMock()
        
        return mock_service_fixture
    
    def _create_skip_fixture(self, service_name: str):
        """Create fixture that skips tests for unavailable service."""
        @pytest.fixture
        def skip_service_fixture():
            pytest.skip(f"Service {service_name} not available and no fallback configured")
        
        return skip_service_fixture


# Service-aware test decorators
def requires_services(*service_names):
    """Decorator that skips tests if required services are unavailable."""
    def decorator(test_func):
        @pytest.mark.asyncio
        async def wrapper(*args, **kwargs):
            manager = ServiceAwareTestManager()
            availability = await manager.discover_available_services()
            
            unavailable = []
            for service in service_names:
                if availability.get(service) not in [ServiceAvailability.AVAILABLE, ServiceAvailability.DEGRADED]:
                    unavailable.append(service)
            
            if unavailable:
                pytest.skip(f"Required services unavailable: {', '.join(unavailable)}")
            
            return await test_func(*args, **kwargs)
        return wrapper
    return decorator


def fallback_to_staging(*service_names):
    """Decorator that uses staging services when local services unavailable."""
    def decorator(test_func):
        @pytest.mark.asyncio
        async def wrapper(*args, **kwargs):
            manager = ServiceAwareTestManager()
            availability = await manager.discover_available_services()
            
            # Check if any required services are unavailable
            needs_staging = any(
                availability.get(service) == ServiceAvailability.UNAVAILABLE
                for service in service_names
            )
            
            if needs_staging and manager._staging_available():
                # Set up staging environment
                import os
                original_env = os.environ.get("ENVIRONMENT")
                os.environ["ENVIRONMENT"] = "staging"
                os.environ["USE_STAGING_SERVICES"] = "true"
                
                try:
                    return await test_func(*args, **kwargs)
                finally:
                    # Restore original environment
                    if original_env:
                        os.environ["ENVIRONMENT"] = original_env
                    else:
                        os.environ.pop("ENVIRONMENT", None)
                    os.environ.pop("USE_STAGING_SERVICES", None)
            
            return await test_func(*args, **kwargs)
        return wrapper
    return decorator


# Export main components
__all__ = [
    'ServiceAwareTestManager',
    'ServiceAvailability', 
    'TestExecutionStrategy',
    'requires_services',
    'fallback_to_staging'
]