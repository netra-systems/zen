"""Tests for ServiceRegistry functionality."""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from netra_backend.app.core.service_interfaces import (
    BaseService,
    ServiceRegistry,
    service_registry,
)

class TestServiceRegistry:
    """Test ServiceRegistry functionality."""
    
    def test_initialization(self):
        """Test ServiceRegistry initialization."""
        registry = ServiceRegistry()
        
        assert len(registry._services) == 0
    
    def test_register_service(self):
        """Test registering a service."""
        registry = ServiceRegistry()
        service = BaseService("test-service")
        
        registry.register(service)
        
        assert registry.get_service("test-service") == service
        assert "test-service" in registry.get_all_services()
    
    def test_get_service_not_found(self):
        """Test getting non-existent service."""
        registry = ServiceRegistry()
        
        result = registry.get_service("non-existent")
        
        assert result == None

    def _create_test_services(self):
        """Helper: Create test services."""
        service1 = BaseService("service1")
        service2 = BaseService("service2")
        return service1, service2

    def _register_services(self, registry, service1, service2):
        """Helper: Register services in registry."""
        registry.register(service1)
        registry.register(service2)

    def _verify_all_services(self, all_services, service1, service2):
        """Helper: Verify all services collection."""
        assert len(all_services) == 2
        assert all_services["service1"] == service1
        assert all_services["service2"] == service2

    def test_get_all_services(self):
        """Test getting all services."""
        registry = ServiceRegistry()
        service1, service2 = self._create_test_services()
        
        self._register_services(registry, service1, service2)
        
        all_services = registry.get_all_services()
        
        self._verify_all_services(all_services, service1, service2)

    def _verify_initialization_state(self, service1, service2):
        """Helper: Verify services are initialized."""
        assert service1.is_initialized
        assert service2.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_all(self):
        """Test initializing all services."""
        registry = ServiceRegistry()
        service1, service2 = self._create_test_services()
        
        self._register_services(registry, service1, service2)
        
        await registry.initialize_all()
        
        self._verify_initialization_state(service1, service2)

    def _verify_shutdown_state(self, service1, service2):
        """Helper: Verify services are shut down."""
        assert not service1.is_initialized
        assert not service2.is_initialized

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        """Test shutting down all services."""
        registry = ServiceRegistry()
        service1, service2 = self._create_test_services()
        
        self._register_services(registry, service1, service2)
        
        await registry.initialize_all()
        await registry.shutdown_all()
        
        self._verify_shutdown_state(service1, service2)

    def _verify_health_results(self, health_results):
        """Helper: Verify health check results."""
        assert len(health_results) == 2
        assert health_results["service1"].service_name == "service1"
        assert health_results["service2"].service_name == "service2"

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check for all services."""
        registry = ServiceRegistry()
        service1, service2 = self._create_test_services()
        
        self._register_services(registry, service1, service2)
        
        await registry.initialize_all()
        
        health_results = await registry.health_check_all()
        
        self._verify_health_results(health_results)

    def _verify_unhealthy_result(self, health_results, service_name, error_text):
        """Helper: Verify unhealthy service result."""
        assert health_results[service_name].status == "unhealthy"
        assert error_text in health_results[service_name].metrics.get("error", "")

    @pytest.mark.asyncio
    async def test_health_check_all_with_exception(self):
        """Test health check when service raises exception."""
        registry = ServiceRegistry()
        service = BaseService("faulty-service")
        
        registry.register(service)
        
        # Mock health check to raise exception
        with patch.object(service, 'health_check', side_effect=Exception("Health check failed")):
            health_results = await registry.health_check_all()
            
            self._verify_unhealthy_result(health_results, "faulty-service", "Health check failed")

class TestGlobalServiceRegistry:
    """Test global service registry."""
    
    def test_global_registry_exists(self):
        """Test that global service registry exists."""
        assert service_registry != None
        assert isinstance(service_registry, ServiceRegistry)

    def _clear_registry(self):
        """Helper: Clear global registry."""
        service_registry._services.clear()

    def _verify_global_service(self, service):
        """Helper: Verify service in global registry."""
        retrieved = service_registry.get_service("global-test-service")
        assert retrieved == service

    def test_global_registry_operations(self):
        """Test operations on global registry."""
        # Clear registry first
        self._clear_registry()
        
        service = BaseService("global-test-service")
        service_registry.register(service)
        
        self._verify_global_service(service)
        
        # Clean up
        self._clear_registry()

@pytest.fixture(autouse=True)
def clean_global_registry():
    """Fixture to clean global service registry between tests."""
    original_services = service_registry._services.copy()
    service_registry._services.clear()
    yield
    service_registry._services = original_services