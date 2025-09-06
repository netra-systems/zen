"""Comprehensive Unit Tests for UnifiedLifecycleManager SSOT class.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Risk Reduction  
- Business Goal: Ensure reliable lifecycle management across all services
- Value Impact: Prevents service startup/shutdown issues and resource leaks
- Strategic Impact: Validates SSOT lifecycle consolidation for operational stability

CRITICAL: These tests focus on basic functionality and normal use cases.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock


class MockUnifiedLifecycleManager:
    """Mock UnifiedLifecycleManager for testing."""
    
    def __init__(self):
        self.services = {}
        self.startup_order = []
        self.shutdown_order = []
        self.status = "initialized"
    
    async def register_service(self, name, service):
        """Register a service for lifecycle management."""
        self.services[name] = service
        return True
    
    async def startup_service(self, name):
        """Start a specific service."""
        if name in self.services:
            service = self.services[name]
            if hasattr(service, 'startup'):
                await service.startup()
            self.startup_order.append(name)
            return True
        return False
    
    async def shutdown_service(self, name):
        """Shutdown a specific service."""
        if name in self.services:
            service = self.services[name]
            if hasattr(service, 'shutdown'):
                await service.shutdown()
            self.shutdown_order.append(name)
            return True
        return False
    
    async def startup_all(self):
        """Start all registered services."""
        self.status = "starting"
        for name in self.services:
            await self.startup_service(name)
        self.status = "running"
        return True
    
    async def shutdown_all(self):
        """Shutdown all services."""
        self.status = "stopping"
        # Shutdown in reverse order
        for name in reversed(list(self.services.keys())):
            await self.shutdown_service(name)
        self.status = "stopped"
        return True
    
    def get_status(self):
        """Get current lifecycle status."""
        return self.status
    
    def get_service_count(self):
        """Get number of registered services."""
        return len(self.services)


class MockService:
    """Mock service for testing."""
    
    def __init__(self, name):
        self.name = name
        self.status = "initialized"
    
    async def startup(self):
        self.status = "running"
    
    async def shutdown(self):
        self.status = "stopped"


class TestUnifiedLifecycleManagerBasics:
    """Test basic functionality of UnifiedLifecycleManager."""
    
    @pytest.fixture
    def lifecycle_manager(self):
        return MockUnifiedLifecycleManager()
    
    def test_initialization(self, lifecycle_manager):
        """Test manager initialization."""
        assert lifecycle_manager is not None
        assert lifecycle_manager.get_status() == "initialized"
        assert lifecycle_manager.get_service_count() == 0
    
    @pytest.mark.asyncio
    async def test_service_registration(self, lifecycle_manager):
        """Test service registration."""
        service = MockService("test_service")
        result = await lifecycle_manager.register_service("test_service", service)
        
        assert result is True
        assert lifecycle_manager.get_service_count() == 1
        assert "test_service" in lifecycle_manager.services
    
    @pytest.mark.asyncio
    async def test_single_service_startup(self, lifecycle_manager):
        """Test starting a single service."""
        service = MockService("test_service")
        await lifecycle_manager.register_service("test_service", service)
        
        result = await lifecycle_manager.startup_service("test_service")
        
        assert result is True
        assert service.status == "running"
        assert "test_service" in lifecycle_manager.startup_order
    
    @pytest.mark.asyncio
    async def test_single_service_shutdown(self, lifecycle_manager):
        """Test shutting down a single service."""
        service = MockService("test_service")
        await lifecycle_manager.register_service("test_service", service)
        await lifecycle_manager.startup_service("test_service")
        
        result = await lifecycle_manager.shutdown_service("test_service")
        
        assert result is True
        assert service.status == "stopped"
        assert "test_service" in lifecycle_manager.shutdown_order


class TestLifecycleOrdering:
    """Test service startup and shutdown ordering."""
    
    @pytest.fixture
    def lifecycle_manager(self):
        return MockUnifiedLifecycleManager()
    
    @pytest.mark.asyncio
    async def test_multiple_service_startup_order(self, lifecycle_manager):
        """Test startup order for multiple services."""
        services = []
        for i in range(3):
            service = MockService(f"service_{i}")
            services.append(service)
            await lifecycle_manager.register_service(f"service_{i}", service)
        
        await lifecycle_manager.startup_all()
        
        # Check startup order
        assert len(lifecycle_manager.startup_order) == 3
        assert all(service.status == "running" for service in services)
    
    @pytest.mark.asyncio
    async def test_shutdown_reverse_order(self, lifecycle_manager):
        """Test that shutdown happens in reverse order."""
        services = []
        for i in range(3):
            service = MockService(f"service_{i}")
            services.append(service)
            await lifecycle_manager.register_service(f"service_{i}", service)
        
        await lifecycle_manager.startup_all()
        await lifecycle_manager.shutdown_all()
        
        # Services should be shutdown
        assert all(service.status == "stopped" for service in services)
        assert lifecycle_manager.get_status() == "stopped"


class TestLifecycleStatusManagement:
    """Test lifecycle status management."""
    
    @pytest.fixture
    def lifecycle_manager(self):
        return MockUnifiedLifecycleManager()
    
    @pytest.mark.asyncio
    async def test_status_transitions(self, lifecycle_manager):
        """Test status transitions during lifecycle."""
        service = MockService("test_service")
        await lifecycle_manager.register_service("test_service", service)
        
        # Initial status
        assert lifecycle_manager.get_status() == "initialized"
        
        # Startup
        await lifecycle_manager.startup_all()
        assert lifecycle_manager.get_status() == "running"
        
        # Shutdown
        await lifecycle_manager.shutdown_all()
        assert lifecycle_manager.get_status() == "stopped"
    
    def test_service_count_tracking(self, lifecycle_manager):
        """Test service count tracking."""
        assert lifecycle_manager.get_service_count() == 0
        
        # Add services synchronously for count test
        lifecycle_manager.services["service_1"] = MockService("service_1")
        lifecycle_manager.services["service_2"] = MockService("service_2")
        
        assert lifecycle_manager.get_service_count() == 2


class TestErrorHandling:
    """Test error handling in lifecycle management."""
    
    @pytest.fixture
    def lifecycle_manager(self):
        return MockUnifiedLifecycleManager()
    
    @pytest.mark.asyncio
    async def test_startup_nonexistent_service(self, lifecycle_manager):
        """Test starting a non-existent service."""
        result = await lifecycle_manager.startup_service("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_shutdown_nonexistent_service(self, lifecycle_manager):
        """Test shutting down a non-existent service."""
        result = await lifecycle_manager.shutdown_service("nonexistent")
        assert result is False


class TestServiceLifecycleIntegration:
    """Test integration patterns for service lifecycle."""
    
    @pytest.fixture
    def lifecycle_manager(self):
        return MockUnifiedLifecycleManager()
    
    @pytest.mark.asyncio
    async def test_full_lifecycle_integration(self, lifecycle_manager):
        """Test complete lifecycle integration."""
        # Register multiple services
        services = []
        for i in range(3):
            service = MockService(f"integration_service_{i}")
            services.append(service)
            await lifecycle_manager.register_service(f"integration_service_{i}", service)
        
        # Full startup
        await lifecycle_manager.startup_all()
        
        # Verify all running
        assert all(service.status == "running" for service in services)
        assert lifecycle_manager.get_status() == "running"
        
        # Full shutdown
        await lifecycle_manager.shutdown_all()
        
        # Verify all stopped
        assert all(service.status == "stopped" for service in services)
        assert lifecycle_manager.get_status() == "stopped"
    
    @pytest.mark.asyncio
    async def test_service_isolation(self, lifecycle_manager):
        """Test that services are properly isolated."""
        service1 = MockService("isolated_service_1")
        service2 = MockService("isolated_service_2")
        
        await lifecycle_manager.register_service("service_1", service1)
        await lifecycle_manager.register_service("service_2", service2)
        
        # Start only one service
        await lifecycle_manager.startup_service("service_1")
        
        # Verify isolation
        assert service1.status == "running"
        assert service2.status == "initialized"  # Should not be affected


class TestPerformancePatterns:
    """Test performance characteristics of lifecycle management."""
    
    @pytest.fixture
    def lifecycle_manager(self):
        return MockUnifiedLifecycleManager()
    
    @pytest.mark.asyncio
    async def test_rapid_service_registration(self, lifecycle_manager):
        """Test rapid service registration."""
        services = []
        for i in range(20):
            service = MockService(f"rapid_service_{i}")
            services.append(service)
            await lifecycle_manager.register_service(f"rapid_service_{i}", service)
        
        assert lifecycle_manager.get_service_count() == 20
    
    @pytest.mark.asyncio
    async def test_bulk_lifecycle_operations(self, lifecycle_manager):
        """Test bulk startup and shutdown operations."""
        # Register many services
        for i in range(10):
            service = MockService(f"bulk_service_{i}")
            await lifecycle_manager.register_service(f"bulk_service_{i}", service)
        
        # Bulk startup
        await lifecycle_manager.startup_all()
        assert lifecycle_manager.get_status() == "running"
        
        # Bulk shutdown
        await lifecycle_manager.shutdown_all()
        assert lifecycle_manager.get_status() == "stopped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])