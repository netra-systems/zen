"""Tests for the service interface system."""

import pytest
import asyncio
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from app.core.service_interfaces import (
    BaseServiceMixin,
    BaseService,
    DatabaseService,
    CRUDService,
    AsyncTaskService,
    ServiceRegistry,
    ServiceHealth,
    ServiceMetrics,
    service_registry,
)
from app.core.exceptions_service import ServiceError
from app.core.exceptions_database import RecordNotFoundError


class MockModel:
    """Mock database model for testing."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestBaseServiceMixin:
    """Test BaseServiceMixin functionality."""
    
    def test_initialization(self):
        """Test BaseServiceMixin initialization."""
        mixin = BaseServiceMixin()
        
        assert not mixin.is_initialized
        assert isinstance(mixin.metrics, ServiceMetrics)
        assert len(mixin._background_tasks) == 0
    
    def test_update_metrics_success(self):
        """Test updating metrics for successful operation."""
        mixin = BaseServiceMixin()
        initial_total = mixin.metrics.requests_total
        initial_successful = mixin.metrics.requests_successful
        
        mixin._update_metrics(success=True, response_time=0.5)
        
        assert mixin.metrics.requests_total == initial_total + 1
        assert mixin.metrics.requests_successful == initial_successful + 1
        assert mixin.metrics.requests_failed == 0
        assert mixin.metrics.average_response_time == 0.5
    
    def test_update_metrics_failure(self):
        """Test updating metrics for failed operation."""
        mixin = BaseServiceMixin()
        initial_total = mixin.metrics.requests_total
        initial_failed = mixin.metrics.requests_failed
        
        mixin._update_metrics(success=False, response_time=1.0)
        
        assert mixin.metrics.requests_total == initial_total + 1
        assert mixin.metrics.requests_failed == initial_failed + 1
        assert mixin.metrics.requests_successful == 0
        assert mixin.metrics.average_response_time == 1.0
    
    def test_update_metrics_average_calculation(self):
        """Test average response time calculation."""
        mixin = BaseServiceMixin()
        
        mixin._update_metrics(success=True, response_time=1.0)
        assert mixin.metrics.average_response_time == 1.0
        
        mixin._update_metrics(success=True, response_time=3.0)
        assert mixin.metrics.average_response_time == 2.0  # (1.0 + 3.0) / 2
    
    @pytest.mark.asyncio
    async def test_create_background_task(self):
        """Test creating background tasks."""
        mixin = BaseServiceMixin()
        
        async def dummy_task():
            await asyncio.sleep(0.1)
            return "done"
        
        task = mixin._create_background_task(dummy_task())
        assert task in mixin._background_tasks
        
        # Task should be removed when done
        result = await task
        assert result == "done"
    
    @pytest.mark.asyncio
    async def test_cancel_background_tasks(self):
        """Test cancelling background tasks."""
        mixin = BaseServiceMixin()
        
        async def long_task():
            await asyncio.sleep(10)  # Long task
        
        # Create some background tasks
        task1 = mixin._create_background_task(long_task())
        task2 = mixin._create_background_task(long_task())
        
        assert len(mixin._background_tasks) == 2
        
        # Cancel all tasks
        await mixin._cancel_background_tasks()
        
        assert len(mixin._background_tasks) == 0
        assert task1.cancelled()
        assert task2.cancelled()


class TestBaseService:
    """Test BaseService functionality."""
    
    def test_initialization(self):
        """Test BaseService initialization."""
        service = BaseService("test-service")
        
        assert service.service_name == "test-service"
        assert not service.is_initialized
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful service initialization."""
        service = BaseService("test-service")
        
        await service.initialize()
        
        assert service.is_initialized
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test service initialization failure."""
        service = BaseService("test-service")
        
        # Mock the implementation to fail
        async def failing_init():
            raise Exception("Init failed")
        
        with patch.object(service, '_initialize_impl', side_effect=failing_init):
            with patch('app.core.error_context.ErrorContext.get_all_context', return_value={}):
                with pytest.raises(ServiceError):
                    await service.initialize()
                
                assert not service.is_initialized
    
    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test that initialize is idempotent."""
        service = BaseService("test-service")
        
        # Mock the implementation to track calls
        with patch.object(service, '_initialize_impl') as mock_init:
            await service.initialize()
            await service.initialize()  # Second call
            
            mock_init.assert_called_once()  # Should only be called once
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test service shutdown."""
        service = BaseService("test-service")
        await service.initialize()
        
        await service.shutdown()
        
        assert not service.is_initialized
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when service is healthy."""
        service = BaseService("test-service")
        await service.initialize()
        
        health = await service.health_check()
        
        assert isinstance(health, ServiceHealth)
        assert health.service_name == "test-service"
        assert health.status == "healthy"
        assert isinstance(health.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_health_check_with_dependencies(self):
        """Test health check with dependencies."""
        service = BaseService("test-service")
        
        # Mock dependency check
        with patch.object(service, '_check_dependencies', return_value={"db": "healthy", "cache": "unhealthy"}):
            health = await service.health_check()
            
            assert health.status == "degraded"  # Should be degraded due to unhealthy dependency
            assert health.dependencies == {"db": "healthy", "cache": "unhealthy"}
    
    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        """Test health check when an exception occurs."""
        service = BaseService("test-service")
        
        # Mock dependency check to raise exception
        with patch.object(service, '_check_dependencies', side_effect=Exception("Health check failed")):
            health = await service.health_check()
            
            assert health.status == "unhealthy"
            assert "Health check failed" in health.metrics.get("error", "")


class TestDatabaseService:
    """Test DatabaseService functionality."""
    
    def test_initialization(self):
        """Test DatabaseService initialization."""
        service = DatabaseService("db-service")
        
        assert service.service_name == "db-service"
        assert service._session_factory == None
    
    def test_set_session_factory(self):
        """Test setting session factory."""
        service = DatabaseService("db-service")
        mock_factory = Mock()
        
        service.set_session_factory(mock_factory)
        
        assert service._session_factory == mock_factory
    
    @pytest.mark.asyncio
    async def test_get_db_session_no_factory(self):
        """Test getting DB session without factory configured."""
        service = DatabaseService("db-service")
        
        with pytest.raises(ServiceError) as exc_info:
            async with service.get_db_session():
                pass
        
        assert "Database session factory not configured" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_db_session_success(self):
        """Test successful DB session acquisition."""
        service = DatabaseService("db-service")
        
        # Mock session with close method
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Create a context manager that returns the mock session
        class MockAsyncContextManager:
            def __init__(self, session):
                self.session = session
            
            async def __aenter__(self):
                return self.session
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None  # The service will handle the close
        
        def mock_factory():
            return MockAsyncContextManager(mock_session)
        
        service.set_session_factory(mock_factory)
        
        async with service.get_db_session() as session:
            assert session == mock_session
        
        # The service calls close in the finally block
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_db_session_exception(self):
        """Test DB session with exception handling."""
        service = DatabaseService("db-service")
        
        # Mock session that handles exceptions
        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        class MockAsyncContextManager:
            def __init__(self, session):
                self.session = session
            
            async def __aenter__(self):
                return self.session
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None  # Let service handle error
        
        def mock_factory():
            return MockAsyncContextManager(mock_session)
        
        service.set_session_factory(mock_factory)
        
        # Mock the ErrorContext.get_all_context to return empty dict
        with patch('app.core.error_context.ErrorContext.get_all_context', return_value={}):
            with pytest.raises(ServiceError):
                async with service.get_db_session():
                    raise Exception("Database error")
        
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestCRUDService:
    """Test CRUDService functionality."""
    
    @pytest.fixture
    def crud_service(self):
        """Create a CRUD service for testing."""
        service = CRUDService("crud-service", MockModel, MockModel)
        
        # Mock session factory
        async def mock_factory():
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            return mock_session
        
        service.set_session_factory(mock_factory)
        return service
    
    @pytest.mark.asyncio
    async def test_create_entity(self, crud_service):
        """Test creating an entity."""
        mock_data = {"name": "test", "value": 123}
        
        with patch.object(crud_service, 'get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Mock entity creation
            mock_entity = MockModel(id=1, name="test", value=123)
            mock_session.add = Mock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            
            with patch.object(crud_service, '_to_response_schema', return_value=mock_entity):
                result = await crud_service.create(mock_data)
                
                assert result == mock_entity
                mock_session.add.assert_called_once()
                mock_session.commit.assert_called_once()
                mock_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_found(self, crud_service):
        """Test getting entity by ID when found."""
        entity_id = 1
        mock_entity = MockModel(id=entity_id, name="test")
        
        with patch.object(crud_service, 'get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.get = AsyncMock(return_value=mock_entity)
            
            with patch.object(crud_service, '_to_response_schema', return_value=mock_entity):
                result = await crud_service.get_by_id(entity_id)
                
                assert result == mock_entity
                mock_session.get.assert_called_once_with(MockModel, entity_id)
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, crud_service):
        """Test getting entity by ID when not found."""
        entity_id = 999
        
        with patch.object(crud_service, 'get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.get = AsyncMock(return_value=None)
            
            result = await crud_service.get_by_id(entity_id)
            
            assert result == None
    
    @pytest.mark.asyncio
    async def test_update_entity_success(self, crud_service):
        """Test updating an existing entity."""
        entity_id = 1
        update_data = {"name": "updated"}
        mock_entity = MockModel(id=entity_id, name="original")
        
        with patch.object(crud_service, 'get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.get = AsyncMock(return_value=mock_entity)
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            
            with patch.object(crud_service, '_to_response_schema', return_value=mock_entity):
                result = await crud_service.update(entity_id, update_data)
                
                assert result == mock_entity
                assert mock_entity.name == "updated"  # Field should be updated
    
    @pytest.mark.asyncio
    async def test_update_entity_not_found(self, crud_service):
        """Test updating non-existent entity."""
        entity_id = 999
        update_data = {"name": "updated"}
        
        with patch.object(crud_service, 'get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.get = AsyncMock(return_value=None)
            
            with pytest.raises(RecordNotFoundError):
                await crud_service.update(entity_id, update_data)
    
    @pytest.mark.asyncio
    async def test_delete_entity_success(self, crud_service):
        """Test deleting an existing entity."""
        entity_id = 1
        mock_entity = MockModel(id=entity_id, name="test")
        
        with patch.object(crud_service, 'get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.get = AsyncMock(return_value=mock_entity)
            mock_session.delete = AsyncMock()
            mock_session.commit = AsyncMock()
            
            result = await crud_service.delete(entity_id)
            
            assert result == True
            mock_session.delete.assert_called_once_with(mock_entity)
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_entity_not_found(self, crud_service):
        """Test deleting non-existent entity."""
        entity_id = 999
        
        with patch.object(crud_service, 'get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.get = AsyncMock(return_value=None)
            
            result = await crud_service.delete(entity_id)
            
            assert result == False
    
    @pytest.mark.asyncio
    async def test_exists_true(self, crud_service):
        """Test entity exists check when entity exists."""
        entity_id = 1
        mock_entity = MockModel(id=entity_id)
        
        with patch.object(crud_service, 'get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.get = AsyncMock(return_value=mock_entity)
            
            result = await crud_service.exists(entity_id)
            
            assert result == True
    
    @pytest.mark.asyncio
    async def test_exists_false(self, crud_service):
        """Test entity exists check when entity doesn't exist."""
        entity_id = 999
        
        with patch.object(crud_service, 'get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.get = AsyncMock(return_value=None)
            
            result = await crud_service.exists(entity_id)
            
            assert result == False


class TestAsyncTaskService:
    """Test AsyncTaskService functionality."""
    
    def test_initialization(self):
        """Test AsyncTaskService initialization."""
        service = AsyncTaskService("task-service")
        
        assert service.service_name == "task-service"
        assert hasattr(service, '_background_running')
        if hasattr(service, '_background_running'):
            assert not service._background_running
        if hasattr(service, '_monitor_task'):
            assert service._monitor_task == None
    
    @pytest.mark.asyncio
    async def test_start_background_tasks(self):
        """Test starting background tasks."""
        service = AsyncTaskService("task-service")
        
        # Mock the implementation
        with patch.object(service, '_start_background_tasks_impl') as mock_start:
            await service.start_background_tasks()
            
            assert service._background_running
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_background_tasks_idempotent(self):
        """Test that starting background tasks is idempotent."""
        service = AsyncTaskService("task-service")
        
        with patch.object(service, '_start_background_tasks_impl') as mock_start:
            await service.start_background_tasks()
            await service.start_background_tasks()  # Second call
            
            mock_start.assert_called_once()  # Should only be called once
    
    @pytest.mark.asyncio
    async def test_stop_background_tasks(self):
        """Test stopping background tasks."""
        service = AsyncTaskService("task-service")
        
        # Start tasks first
        with patch.object(service, '_start_background_tasks_impl'):
            await service.start_background_tasks()
        
        # Now stop them
        with patch.object(service, '_stop_background_tasks_impl') as mock_stop:
            with patch.object(service, '_cancel_background_tasks') as mock_cancel:
                await service.stop_background_tasks()
                
                assert not service._background_running
                mock_stop.assert_called_once()
                mock_cancel.assert_called_once()


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
    
    def test_get_all_services(self):
        """Test getting all services."""
        registry = ServiceRegistry()
        service1 = BaseService("service1")
        service2 = BaseService("service2")
        
        registry.register(service1)
        registry.register(service2)
        
        all_services = registry.get_all_services()
        
        assert len(all_services) == 2
        assert all_services["service1"] == service1
        assert all_services["service2"] == service2
    
    @pytest.mark.asyncio
    async def test_initialize_all(self):
        """Test initializing all services."""
        registry = ServiceRegistry()
        service1 = BaseService("service1")
        service2 = BaseService("service2")
        
        registry.register(service1)
        registry.register(service2)
        
        await registry.initialize_all()
        
        assert service1.is_initialized
        assert service2.is_initialized
    
    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        """Test shutting down all services."""
        registry = ServiceRegistry()
        service1 = BaseService("service1")
        service2 = BaseService("service2")
        
        registry.register(service1)
        registry.register(service2)
        
        await registry.initialize_all()
        await registry.shutdown_all()
        
        assert not service1.is_initialized
        assert not service2.is_initialized
    
    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check for all services."""
        registry = ServiceRegistry()
        service1 = BaseService("service1")
        service2 = BaseService("service2")
        
        registry.register(service1)
        registry.register(service2)
        
        await registry.initialize_all()
        
        health_results = await registry.health_check_all()
        
        assert len(health_results) == 2
        assert health_results["service1"].service_name == "service1"
        assert health_results["service2"].service_name == "service2"
    
    @pytest.mark.asyncio
    async def test_health_check_all_with_exception(self):
        """Test health check when service raises exception."""
        registry = ServiceRegistry()
        service = BaseService("faulty-service")
        
        registry.register(service)
        
        # Mock health check to raise exception
        with patch.object(service, 'health_check', side_effect=Exception("Health check failed")):
            health_results = await registry.health_check_all()
            
            assert health_results["faulty-service"].status == "unhealthy"
            assert "Health check failed" in health_results["faulty-service"].metrics.get("error", "")


class TestServiceModels:
    """Test service model classes."""
    
    def test_service_health_creation(self):
        """Test ServiceHealth model creation."""
        health = ServiceHealth(
            service_name="test-service",
            status="healthy",
            timestamp=datetime.now(UTC),
            dependencies={"db": "healthy"},
            metrics={"requests": 100}
        )
        
        assert health.service_name == "test-service"
        assert health.status == "healthy"
        assert health.dependencies == {"db": "healthy"}
        assert health.metrics == {"requests": 100}
    
    def test_service_metrics_creation(self):
        """Test ServiceMetrics model creation."""
        metrics = ServiceMetrics(
            requests_total=100,
            requests_successful=95,
            requests_failed=5,
            average_response_time=0.25
        )
        
        assert metrics.requests_total == 100
        assert metrics.requests_successful == 95
        assert metrics.requests_failed == 5
        assert metrics.average_response_time == 0.25


class TestGlobalServiceRegistry:
    """Test global service registry."""
    
    def test_global_registry_exists(self):
        """Test that global service registry exists."""
        assert service_registry != None
        assert isinstance(service_registry, ServiceRegistry)
    
    def test_global_registry_operations(self):
        """Test operations on global registry."""
        # Clear registry first
        service_registry._services.clear()
        
        service = BaseService("global-test-service")
        service_registry.register(service)
        
        retrieved = service_registry.get_service("global-test-service")
        assert retrieved == service
        
        # Clean up
        service_registry._services.clear()


@pytest.fixture(autouse=True)
def clean_global_registry():
    """Fixture to clean global service registry between tests."""
    original_services = service_registry._services.copy()
    service_registry._services.clear()
    yield
    service_registry._services = original_services