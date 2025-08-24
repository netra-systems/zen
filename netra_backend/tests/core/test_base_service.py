"""Tests for BaseService functionality."""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from netra_backend.app.core.exceptions_service import ServiceError

from netra_backend.app.core.service_interfaces import BaseService, ServiceHealth

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

    async def _mock_failing_init(self):
        """Helper: Create failing initialization."""
        raise Exception("Init failed")

    def _setup_error_context_mock(self):
        """Helper: Setup error context mock."""
        return patch('app.core.error_context.ErrorContext.get_all_context', return_value={})

    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test service initialization failure."""
        service = BaseService("test-service")
        
        # Mock the implementation to fail
        with patch.object(service, '_initialize_impl', side_effect=self._mock_failing_init):
            with self._setup_error_context_mock():
                with pytest.raises(ServiceError):
                    await service.initialize()
                
                assert not service.is_initialized

    def _verify_initialization_count(self, mock_init, expected_calls):
        """Helper: Verify initialization call count."""
        assert mock_init.call_count == expected_calls

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test that initialize is idempotent."""
        service = BaseService("test-service")
        
        # Mock the implementation to track calls
        with patch.object(service, '_initialize_impl') as mock_init:
            await service.initialize()
            await service.initialize()  # Second call
            
            self._verify_initialization_count(mock_init, 1)  # Should only be called once

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test service shutdown."""
        service = BaseService("test-service")
        await service.initialize()
        
        await service.shutdown()
        
        assert not service.is_initialized

    def _verify_health_basic_properties(self, health, service_name):
        """Helper: Verify basic health check properties."""
        assert isinstance(health, ServiceHealth)
        assert health.service_name == service_name
        assert isinstance(health.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when service is healthy."""
        service = BaseService("test-service")
        await service.initialize()
        
        health = await service.health_check()
        
        self._verify_health_basic_properties(health, "test-service")
        assert health.status == "healthy"

    def _mock_dependencies_check(self, deps):
        """Helper: Create dependencies check mock."""
        return patch.object(self, '_check_dependencies', return_value=deps)

    def _verify_degraded_health(self, health, expected_deps):
        """Helper: Verify degraded health status."""
        assert health.status == "degraded"
        assert health.dependencies == expected_deps

    @pytest.mark.asyncio
    async def test_health_check_with_dependencies(self):
        """Test health check with dependencies."""
        service = BaseService("test-service")
        deps = {"db": "healthy", "cache": "unhealthy"}
        
        # Mock dependency check
        with patch.object(service, '_check_dependencies', return_value=deps):
            health = await service.health_check()
            
            self._verify_degraded_health(health, deps)

    def _mock_health_exception(self):
        """Helper: Create health check exception."""
        return Exception("Health check failed")

    def _verify_unhealthy_status(self, health, error_text):
        """Helper: Verify unhealthy status with error."""
        assert health.status == "unhealthy"
        assert error_text in health.metrics.get("error", "")

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        """Test health check when an exception occurs."""
        service = BaseService("test-service")
        
        # Mock dependency check to raise exception
        with patch.object(service, '_check_dependencies', side_effect=self._mock_health_exception()):
            health = await service.health_check()
            
            self._verify_unhealthy_status(health, "Health check failed")