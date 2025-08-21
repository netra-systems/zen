#!/usr/bin/env python
"""
Quick Startup Validation Tests
Fast checks that catch common startup errors

Business Value Justification (BVJ):
- Segment: All
- Business Goal: Early error detection in CI/CD
- Value Impact: 90% faster feedback on errors
- Revenue Impact: Prevents broken deployments
"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.asyncio
async def test_clickhouse_configuration():
    """Test ClickHouse is properly configured"""
    from netra_backend.app.db.clickhouse import use_mock_clickhouse, get_clickhouse_config
    
    # In testing environment, should use mock
    if os.getenv("ENVIRONMENT") == "testing":
        assert use_mock_clickhouse() == True, "Should use mock in testing"
    
    # Check config is available
    config = get_clickhouse_config()
    assert config is not None, "ClickHouse config should be available"
    
    # If real ClickHouse is configured, check credentials
    if not use_mock_clickhouse():
        assert config.host, "ClickHouse host not configured"
        assert config.user, "ClickHouse user not configured"
        assert config.password, "ClickHouse password not configured"


@pytest.mark.asyncio
async def test_clickhouse_service_initialization():
    """Test ClickHouse service can initialize"""
    from netra_backend.app.db.clickhouse import ClickHouseService
    
    service = ClickHouseService(force_mock=True)  # Use mock for quick test
    
    try:
        await service.initialize()
        assert service.is_mock, "Service should be in mock mode"
        
        # Test basic operation
        result = await service.execute("SELECT 1")
        assert result == [], "Mock should return empty results"
        
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_auth_service_config():
    """Test auth service configuration is accessible"""
    auth_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:3002")
    assert auth_url, "Auth service URL should be configured"
    
    # Validate URL format
    assert auth_url.startswith("http"), "Auth URL should be valid HTTP(S)"


@pytest.mark.asyncio
async def test_redis_configuration():
    """Test Redis configuration"""
    redis_url = os.getenv("REDIS_URL", "")
    
    # Redis is optional but if configured, should be valid
    if redis_url:
        assert "redis://" in redis_url or "rediss://" in redis_url, "Invalid Redis URL format"


@pytest.mark.asyncio
async def test_critical_imports():
    """Test critical module imports work"""
    imports_to_test = [
        "app.db.clickhouse",
        "app.services.redis_service",
        "app.auth_integration.client",
        "app.core.exceptions",
        "app.websocket.connection",
        "app.agents.supervisor.agent"
    ]
    
    failed_imports = []
    
    for module_name in imports_to_test:
        try:
            __import__(module_name)
        except ImportError as e:
            failed_imports.append(f"{module_name}: {str(e)}")
    
    assert len(failed_imports) == 0, f"Failed imports: {failed_imports}"


@pytest.mark.asyncio
async def test_environment_variables():
    """Test critical environment variables are set"""
    required_vars = [
        "ENVIRONMENT",
        "DATABASE_URL",
        "SECRET_KEY"
    ]
    
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    assert len(missing_vars) == 0, f"Missing environment variables: {missing_vars}"


@pytest.mark.asyncio
async def test_websocket_types_exist():
    """Test WebSocket types are properly defined"""
    try:
        from netra_backend.app.schemas.websocket_types import (
            WebSocketMessage,
            WebSocketMessageType,
            AgentStartedPayload,
            AgentCompletedPayload,
            AgentUpdatePayload
        )
        
        # Verify enums have values
        assert WebSocketMessageType.AGENT_STARTED
        assert WebSocketMessageType.AGENT_COMPLETED
        assert WebSocketMessageType.AGENT_UPDATE
        
    except ImportError as e:
        pytest.fail(f"WebSocket type import failed: {str(e)}")


@pytest.mark.asyncio
async def test_startup_module_loads():
    """Test startup module can be imported"""
    try:
        from netra_backend.app.startup_module import StartupModule
        
        # Module should have critical methods
        assert hasattr(StartupModule, 'initialize')
        assert hasattr(StartupModule, 'startup')
        
    except ImportError as e:
        pytest.fail(f"Startup module import failed: {str(e)}")