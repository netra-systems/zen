#!/usr/bin/env python3
"""
Health Check Validation Tests
Tests to identify and catch the 503 Service Unavailable health check issues.
"""

import os
import asyncio
import pytest
from fastapi import FastAPI, HTTPException
from unittest.mock import patch, MagicMock

# Set environment before imports
os.environ['SKIP_CLICKHOUSE_INIT'] = 'true'

from app.routes.health import ready, health_interface
from app.dependencies import get_db_dependency  
from app.startup_module import setup_database_connections
from app.core.health import HealthLevel


class TestHealthCheckIssues:
    """Test cases to catch the specific health check configuration issues."""
    
    def test_import_timing_issue(self):
        """Test that demonstrates the import caching issue with async_engine."""
        # Import before initialization
        from app.db.postgres import async_engine as engine_before_init
        
        # Initialize database
        app = FastAPI()
        setup_database_connections(app)
        
        # Import after initialization  
        from app.db.postgres import async_engine as engine_after_init
        
        # The cached import should still be None
        assert engine_before_init is None, "Engine before init should be None"
        assert engine_after_init is None, "Cached import still returns None even after init"
        
        # But core module should have the engine
        from app.db.postgres_core import async_engine as core_engine
        assert core_engine is not None, "Core engine should exist after initialization"
        
        print(f"✓ Import timing issue confirmed: {engine_before_init=}, {engine_after_init=}, {core_engine is not None=}")

    async def test_database_health_checker_failure(self):
        """Test that health checkers fail when using cached imports."""
        # Test individual postgres health checker
        postgres_checker = health_interface._checkers.get("postgres")
        assert postgres_checker is not None, "Postgres checker should be registered"
        
        # This should fail with "Database engine not initialized"
        result = await postgres_checker.check_health()
        assert result.status == "unhealthy", "Health check should fail"
        assert "Database engine not initialized" in result.details.get("error_message", ""), "Should get engine not initialized error"
        
        print(f"✓ Database health checker fails as expected: {result.details}")

    async def test_standard_health_returns_unhealthy(self):
        """Test that standard health check returns unhealthy due to postgres failure."""
        health_status = await health_interface.get_health_status(HealthLevel.STANDARD)
        
        assert health_status["status"] == "unhealthy", "Overall status should be unhealthy"
        assert "postgres" in health_status["checks"], "Should include postgres check"
        assert health_status["checks"]["postgres"] is False, "Postgres check should fail"
        
        print(f"✓ Standard health check returns unhealthy: {health_status['status']}")

    async def test_ready_endpoint_503_error(self):
        """Test that /ready endpoint returns 503 Service Unavailable."""
        # Mock a database session
        db_gen = get_db_dependency()
        db = await db_gen.__anext__()
        
        # This should raise HTTPException with 503
        with pytest.raises(HTTPException) as exc_info:
            await ready(db)
        
        assert exc_info.value.status_code == 503, "Should return 503 Service Unavailable"
        assert exc_info.value.detail == "Service Unavailable", "Should have correct error message"
        
        await db_gen.aclose()
        print(f"✓ Ready endpoint returns 503 as expected: {exc_info.value.status_code}")

    def test_nc_session_factory_mystery(self):
        """Test to investigate the mysterious 'nc_session_factory: True' configuration."""
        # This was mentioned in the original issue but doesn't actually exist
        # Documenting that this was a red herring
        
        # Search for any nc_session_factory references
        import app.db.postgres_core as core_module
        import app.dependencies as deps_module
        
        # Check if any attributes contain 'nc_session_factory'  
        core_attrs = [attr for attr in dir(core_module) if 'nc_session_factory' in attr.lower()]
        deps_attrs = [attr for attr in dir(deps_module) if 'nc_session_factory' in attr.lower()]
        
        assert len(core_attrs) == 0, f"No nc_session_factory attributes should exist in core: {core_attrs}"
        assert len(deps_attrs) == 0, f"No nc_session_factory attributes should exist in deps: {deps_attrs}"
        
        print("✓ nc_session_factory was a red herring - no such configuration exists")


def test_health_check_engine_import_fix():
    """Test a potential fix for the health check engine import issue."""
    
    def get_fresh_engine():
        """Get a fresh reference to the async engine after initialization."""
        import importlib
        import app.db.postgres_core
        
        # Reload the module to get fresh references (not recommended for production)
        # Better solution would be to use a function call instead of module-level import
        importlib.reload(app.db.postgres_core)
        return app.db.postgres_core.async_engine
    
    # Test the fresh import approach
    app = FastAPI()
    setup_database_connections(app)
    
    fresh_engine = get_fresh_engine()
    assert fresh_engine is not None, "Fresh engine import should work"
    
    print(f"✓ Fresh engine import works: {fresh_engine is not None}")


if __name__ == "__main__":
    """Run the validation tests."""
    print("Running Health Check Validation Tests...\n")
    
    # Run synchronous tests
    test_instance = TestHealthCheckIssues()
    test_instance.test_import_timing_issue()
    test_instance.test_nc_session_factory_mystery()
    test_health_check_engine_import_fix()
    
    # Run async tests
    async def run_async_tests():
        await test_instance.test_database_health_checker_failure()
        await test_instance.test_standard_health_returns_unhealthy()
        await test_instance.test_ready_endpoint_503_error()
    
    asyncio.run(run_async_tests())
    
    print("\n✅ All validation tests completed successfully!")
    print("\nSUMMARY:")
    print("- Confirmed import timing/caching issue with async_engine")
    print("- Health checks fail due to stale None references")
    print("- This causes 503 Service Unavailable errors")
    print("- nc_session_factory was a red herring (doesn't exist)")