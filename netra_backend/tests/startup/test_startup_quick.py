from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
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

import os
import sys
from pathlib import Path

import pytest

# Add parent directory to path

@pytest.mark.asyncio
async def test_clickhouse_configuration():
    """Test ClickHouse is properly configured"""
    from netra_backend.app.db.clickhouse import (
        get_clickhouse_config,
        use_mock_clickhouse,
    )
    
    # In testing environment, should use mock
    if get_env().get("ENVIRONMENT") == "testing":
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
    auth_url = get_env().get("AUTH_SERVICE_URL", "http://localhost:3002")
    assert auth_url, "Auth service URL should be configured"
    
    # Validate URL format
    assert auth_url.startswith("http"), "Auth URL should be valid HTTP(S)"

@pytest.mark.asyncio
async def test_redis_configuration():
    """Test Redis configuration"""
    redis_url = get_env().get("REDIS_URL", "")
    
    # Redis is optional but if configured, should be valid
    if redis_url:
        assert "redis://" in redis_url or "rediss://" in redis_url, "Invalid Redis URL format"

@pytest.mark.asyncio
async def test_critical_imports():
    """Test critical module imports work"""
    imports_to_test = [
        "netra_backend.app.db.clickhouse",
        "netra_backend.app.services.redis_service",
        "netra_backend.app.auth_integration",
        "netra_backend.app.core.exceptions",
        "netra_backend.app.websocket.connection_manager",
        "netra_backend.app.agents.supervisor"
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
        if not get_env().get(var):
            missing_vars.append(var)
    
    assert len(missing_vars) == 0, f"Missing environment variables: {missing_vars}"

@pytest.mark.asyncio
async def test_websocket_types_exist():
    """Test WebSocket types are properly defined"""
    try:
        from netra_backend.app.schemas.websocket_payloads import (
            AgentStartedPayload,
        )
        from netra_backend.app.schemas.websocket_models import (
            AgentUpdatePayload,
        )
        from netra_backend.app.schemas import (
            WebSocketMessage,
            WebSocketMessageType,
        )
        
        # Verify enums have values
        assert WebSocketMessageType.AGENT_STARTED
        assert WebSocketMessageType.AGENT_UPDATE
        # Note: AGENT_COMPLETED may not exist as an enum value
        
    except ImportError as e:
        pytest.fail(f"WebSocket type import failed: {str(e)}")

@pytest.mark.asyncio
async def test_startup_module_loads():
    """Test startup module can be imported"""
    try:
        from netra_backend.app import startup_module
        
        # Module should have critical functions
        assert hasattr(startup_module, 'initialize_logging')
        assert hasattr(startup_module, 'run_complete_startup')
        assert hasattr(startup_module, 'initialize_core_services')
        
    except ImportError as e:
        pytest.fail(f"Startup module import failed: {str(e)}")
