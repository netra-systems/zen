"""
E2E tests for system introspection endpoints.

Tests health checks, configuration validation, and dependency status endpoints.
"""

import pytest
import httpx
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.e2e
class SystemIntrospectionTests:
    """Test suite for system introspection endpoints."""
    
    @pytest.mark.asyncio
    async def test_readiness_probe(self, client: httpx.AsyncClient):
        """Test readiness probe endpoint."""
        response = await client.get("/api/health/ready")
        
        # Service should be ready
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "checks" in data
        
        # Verify individual checks
        checks = data["checks"]
        assert "database" in checks or "agent_service" in checks or "circuit_breakers" in checks
    
    @pytest.mark.asyncio
    async def test_liveness_probe(self, client: httpx.AsyncClient):
        """Test liveness probe endpoint."""
        response = await client.get("/api/health/live")
        
        # Service should be alive
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded"]
        assert "checks" in data
        assert "event_loop" in data["checks"]
    
    @pytest.mark.asyncio
    async def test_startup_probe(self, client: httpx.AsyncClient):
        """Test startup probe endpoint."""
        response = await client.get("/api/health/startup")
        
        # Service should be started
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "checks" in data
        
        # Verify initialization checks
        for service in ["database", "agent_service", "auth_service", "configuration"]:
            if service in data["checks"]:
                assert data["checks"][service]["initialized"] is True
    
    @pytest.mark.asyncio
    async def test_system_info(self, client: httpx.AsyncClient):
        """Test system info endpoint."""
        response = await client.get("/api/system/info")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "version" in data
        assert "environment" in data
        assert "python_version" in data
        assert "platform" in data
        assert "hostname" in data
        assert "started_at" in data
    
    @pytest.mark.asyncio
    async def test_config_validation(self, client: httpx.AsyncClient):
        """Test configuration validation endpoint."""
        response = await client.get("/api/system/config/validate")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "valid" in data
        assert "errors" in data
        assert "warnings" in data
        assert "config_sources" in data
        assert "effective_config" in data
        
        # Sensitive values should be redacted
        if "JWT_SECRET_KEY" in data["effective_config"]:
            assert data["effective_config"]["JWT_SECRET_KEY"] == "***REDACTED***"
    
    @pytest.mark.asyncio
    async def test_dependencies_status(self, client: httpx.AsyncClient):
        """Test dependencies status endpoint."""
        response = await client.get("/api/system/dependencies/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "overall_status" in data
        assert "dependencies" in data
        assert "timestamp" in data
        
        # Verify at least one dependency is checked
        assert len(data["dependencies"]) > 0
        
        for dep in data["dependencies"]:
            assert "name" in dep
            assert "type" in dep
            assert "status" in dep
            assert dep["status"] in ["healthy", "degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_debug_routes(self, client: httpx.AsyncClient):
        """Test debug routes listing endpoint."""
        response = await client.get("/api/system/debug/routes")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify route structure
        for route in data:
            assert "path" in route
            assert "methods" in route
            assert isinstance(route["methods"], list)
    
    @pytest.mark.asyncio
    async def test_async_tasks_info(self, client: httpx.AsyncClient):
        """Test async tasks information endpoint."""
        response = await client.get("/api/system/debug/async_tasks")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_tasks" in data
        assert "tasks" in data
        assert isinstance(data["tasks"], list)
        
        # There should be at least one task (the current request handler)
        assert data["total_tasks"] > 0
    
    @pytest.mark.asyncio
    async def test_health_check_with_circuit_breaker_open(self, client: httpx.AsyncClient):
        """Test readiness probe when circuit breaker is open."""
        # First, trigger circuit breaker by forcing failures
        for _ in range(5):
            await client.post(
                "/api/agents/execute",
                json={
                    "type": "test_agent",
                    "message": "test",
                    "force_failure": True
                }
            )
        
        # Now check readiness
        response = await client.get("/api/health/ready")
        
        # Service should be degraded but still return 200
        assert response.status_code == 200
        data = response.json()
        
        # Status should reflect degradation if circuit breakers are open
        if "circuit_breakers" in data["checks"]:
            if data["checks"]["circuit_breakers"]["open_circuits"]:
                assert data["status"] in ["degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_system_introspection_integration(self, client: httpx.AsyncClient):
        """Test integration between different introspection endpoints."""
        # Get system info
        info_response = await client.get("/api/system/info")
        assert info_response.status_code == 200
        info_data = info_response.json()
        
        # Get health status
        health_response = await client.get("/api/health/ready")
        assert health_response.status_code == 200
        health_data = health_response.json()
        
        # Verify consistency between endpoints
        assert info_data["environment"] == health_data.get("environment", "development")
        
        # Get dependencies status
        deps_response = await client.get("/api/system/dependencies/status")
        assert deps_response.status_code == 200
        deps_data = deps_response.json()
        
        # If database is checked in health, it should also be in dependencies
        if "database" in health_data["checks"]:
            db_deps = [d for d in deps_data["dependencies"] if d["type"] == "database"]
            assert len(db_deps) > 0
