"""Unit tests for migrations
Coverage Target: 70%
Business Value: Long-term maintainability
"""

import pytest
import asyncio
from netra_backend.app.db.migrations.migration_runner import MigrationRunner
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

class TestMigrations:
    """Test suite for Migrations"""

    @pytest.fixture
    async def instance(self):
        """Create test instance with proper session management."""
        env = IsolatedEnvironment()
        # Ensure required environment variables are set
        env.set('SECRET_KEY', 'test-secret-key-for-test-environment-only-32-chars-min')
        env.set('DATABASE_URL', 'postgresql://test:test@localhost:5432/test_db')
        
        db_manager = DatabaseTestManager()
        await db_manager.initialize()
        session = await db_manager.create_session()
        return MigrationRunner(session)

    @pytest.mark.asyncio
    async def test_initialization(self, instance):
        """Test proper initialization"""
        assert instance is not None
        assert instance.session is not None
        assert instance.migrations_executed == []
        assert instance.migration_history == []

    @pytest.mark.asyncio
    async def test_core_functionality(self, instance):
        """Test core business logic"""
        # Test migration status retrieval
        result = instance.get_migration_status()
        assert result is not None
        assert "executed_migrations" in result
        assert "pending_migrations" in result
        assert "migration_count" in result
        
        # Test running migrations
        migration_result = await instance.run_migrations(["test_migration_1"])
        assert migration_result is not None
        assert migration_result.get("success") is True
        assert "test_migration_1" in migration_result.get("migrations_run", [])

    @pytest.mark.asyncio
    async def test_error_handling(self, instance):
        """Test error scenarios"""
        # Test that rollback of non-existent migration returns error
        result = await instance.rollback_migration("non_existent_migration")
        assert result is not None
        assert result.get("success") is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_edge_cases(self, instance):
        """Test boundary conditions"""
        # Test with empty migration list (defaults to ["initial_schema", "add_indexes"])
        result = await instance.run_migrations([])
        assert result is not None
        assert result.get("success") is True
        assert len(result.get("migrations_run", [])) == 2  # Default migrations
        
        # Test migration status after running default migrations
        status = instance.get_migration_status()
        assert status.get("migration_count") == 2
        assert status.get("last_migration") == "add_indexes"

    @pytest.mark.asyncio
    async def test_validation(self, instance):
        """Test input validation"""
        # Test rollback with None input - should handle gracefully
        result = await instance.rollback_migration(None)
        assert result is not None
        assert result.get("success") is False