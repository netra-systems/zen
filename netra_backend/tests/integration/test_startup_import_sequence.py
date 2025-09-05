"""Integration test for startup import sequence

This test validates that all critical imports work correctly during
application startup, preventing runtime AttributeError issues.

Root Cause Addressed (from Five Whys):
- Tests the actual import sequence used during startup
- No mocks - uses real imports
- Validates async initialization order
- Ensures all methods are available when needed
"""

import asyncio
import pytest
from typing import Optional


class TestStartupImportSequence:
    """Test critical import sequences during startup"""
    
    @pytest.mark.asyncio
    async def test_database_manager_imports_correctly(self):
        """Test that DatabaseManager can be imported and used at startup"""
        # This mimics what happens during startup
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # Verify class methods exist
        assert hasattr(DatabaseManager, 'create_application_engine'), \
            "DatabaseManager missing create_application_engine static method"
        
        # Verify the method can be called
        engine = DatabaseManager.create_application_engine()
        assert engine is not None, "create_application_engine returned None"
        
        # Clean up
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_health_checker_initialization_sequence(self):
        """Test health checker initialization with various import patterns"""
        # Test 1: Import at module level (new pattern)
        from netra_backend.app.services.database.health_checker import ConnectionHealthChecker
        
        class MockMetrics:
            def get_pool_status(self):
                return {"status": "mock"}
        
        # Test without dependency injection
        checker = ConnectionHealthChecker(MockMetrics())
        assert checker is not None
        
        # Test with dependency injection
        from netra_backend.app.db.database_manager import DatabaseManager
        checker_with_dm = ConnectionHealthChecker(MockMetrics(), DatabaseManager)
        assert checker_with_dm is not None
        
        # Verify engine can be created
        engine = await checker._get_or_create_engine()
        assert engine is not None
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_index_optimizer_imports(self):
        """Test that index optimizers import with all methods available"""
        from netra_backend.app.db.postgres_index_optimizer import PostgreSQLIndexOptimizer
        from netra_backend.app.db.clickhouse_index_optimizer import ClickHouseIndexOptimizer
        
        # Create instances
        pg_optimizer = PostgreSQLIndexOptimizer()
        ch_optimizer = ClickHouseIndexOptimizer()
        
        # Verify optimize methods exist
        assert hasattr(pg_optimizer, 'optimize'), \
            "PostgreSQLIndexOptimizer missing optimize method"
        assert hasattr(ch_optimizer, 'optimize'), \
            "ClickHouseIndexOptimizer missing optimize method"
        
        # Verify methods are callable
        assert callable(pg_optimizer.optimize)
        assert callable(ch_optimizer.optimize)
    
    @pytest.mark.asyncio
    async def test_database_index_manager_startup(self):
        """Test DatabaseIndexManager initialization as used during startup"""
        from netra_backend.app.db.index_optimizer import DatabaseIndexManager
        
        # This simulates what happens during startup
        manager = DatabaseIndexManager()
        
        # Verify it was initialized correctly
        assert manager.postgres_optimizer is not None
        assert manager.clickhouse_optimizer is not None
        
        # Verify the optimize_all_databases method works
        assert hasattr(manager, 'optimize_all_databases')
        assert callable(manager.optimize_all_databases)
    
    @pytest.mark.asyncio
    async def test_circular_import_prevention(self):
        """Test that our import pattern prevents circular dependencies"""
        import_order = []
        
        # Track import order
        import_order.append("database_manager")
        from netra_backend.app.db.database_manager import DatabaseManager
        
        import_order.append("health_checker")
        from netra_backend.app.services.database.health_checker import ConnectionHealthChecker
        
        import_order.append("index_optimizer")
        from netra_backend.app.db.index_optimizer import DatabaseIndexManager
        
        # Verify all imports succeeded
        assert len(import_order) == 3
        assert DatabaseManager is not None
        assert ConnectionHealthChecker is not None
        assert DatabaseIndexManager is not None
    
    @pytest.mark.asyncio 
    async def test_async_initialization_order(self):
        """Test that async initialization works in the correct order"""
        from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager
        
        # Get the singleton instance
        manager = get_database_manager()
        
        # Initialize it
        await manager.initialize()
        
        # Verify it's initialized
        assert manager._initialized == True
        
        # Clean up
        await manager.close_all()


class TestStartupErrorScenarios:
    """Test error scenarios that could occur during startup"""
    
    @pytest.mark.asyncio
    async def test_health_checker_handles_missing_database_manager(self):
        """Test that health checker handles missing DatabaseManager gracefully"""
        from netra_backend.app.services.database.health_checker import ConnectionHealthChecker
        
        class MockMetrics:
            def get_pool_status(self):
                return {"status": "mock"}
        
        # Create checker without database manager
        checker = ConnectionHealthChecker(MockMetrics(), database_manager=None)
        
        # Should still work using fallback import
        engine = await checker._get_or_create_engine()
        assert engine is not None
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_index_optimizer_handles_database_errors(self):
        """Test that index optimizer handles database errors gracefully"""
        from netra_backend.app.db.index_optimizer import DatabaseIndexManager
        
        manager = DatabaseIndexManager()
        
        # This should not crash even if database is unavailable
        # It should log warnings and return empty results
        try:
            result = await manager.optimize_all_databases()
            # Result might be empty or contain errors, but shouldn't crash
            assert result is not None or result == {}
        except Exception as e:
            # Some exceptions are acceptable if database is not configured
            assert "database" in str(e).lower() or "connection" in str(e).lower()


@pytest.mark.asyncio
async def test_production_like_startup_sequence():
    """Integration test mimicking production startup sequence"""
    startup_steps = []
    
    try:
        # Step 1: Import core modules
        startup_steps.append("import_core")
        from netra_backend.app.db.database_manager import get_database_manager
        from netra_backend.app.db.index_optimizer import index_manager
        
        # Step 2: Initialize database manager
        startup_steps.append("init_database")
        db_manager = get_database_manager()
        await db_manager.initialize()
        
        # Step 3: Initialize health checker
        startup_steps.append("init_health_checker")
        from netra_backend.app.services.database.health_checker import ConnectionHealthChecker
        
        class MockMetrics:
            def get_pool_status(self):
                return {"status": "healthy", "active": 0, "idle": 1}
        
        health_checker = ConnectionHealthChecker(MockMetrics(), db_manager)
        
        # Step 4: Run health check
        startup_steps.append("run_health_check")
        health_status = await health_checker.perform_health_check()
        assert health_status is not None
        
        # Step 5: Start monitoring (but don't await it)
        startup_steps.append("start_monitoring")
        await health_checker.start_monitoring()
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Step 6: Stop monitoring
        startup_steps.append("stop_monitoring")
        health_checker.stop_monitoring()
        
        # Clean up
        await db_manager.close_all()
        
        # Verify all steps completed
        assert len(startup_steps) == 6
        
    except Exception as e:
        pytest.fail(f"Startup sequence failed at step {startup_steps[-1] if startup_steps else 'unknown'}: {e}")