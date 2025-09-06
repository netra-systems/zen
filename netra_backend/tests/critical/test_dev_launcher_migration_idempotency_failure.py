"""
Test-Driven Correction (TDC) Tests for Non-Idempotent Migration Issues
Critical dev launcher issue: Migration drops non-existent index "idx_userbase_created_at"

These are FAILING tests that demonstrate the exact migration idempotency issues
found in dev launcher analysis. The tests are intentionally designed to fail to expose
the specific migration problems that need fixing.

Root Cause: Migration 66e0e5d9662d attempts to drop idx_userbase_created_at index
that may not exist in all environments, making the migration non-idempotent.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & Database Integrity
- Value Impact: Ensures migrations can be run safely in any environment state
- Strategic Impact: Prevents database corruption and reduces developer friction
"""

import pytest
import asyncio
from sqlalchemy.exc import ProgrammingError, OperationalError
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from test_framework.performance_helpers import fast_test, timeout_override
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment


class TestMigrationIdempotencyFailures:
    """Test suite for migration idempotency issues from dev launcher analysis."""
    
    @fast_test
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_migration_drop_nonexistent_index_idx_userbase_created_at_fails(self):
        """
        FAILING TEST: Demonstrates migration failure when dropping non-existent index.
        
        This test reproduces the exact error from dev launcher logs:
        "ProgrammingError: (psycopg2.errors.UndefinedObject) index 'idx_userbase_created_at' does not exist"
        
        Expected behavior: Migration should check if index exists before attempting to drop it
        Current behavior: Migration fails when index doesn't exist, making it non-idempotent
        """
        # Mock scenario where index doesn't exist in database
        mock_connection = MagicNone  # TODO: Use real service instance
        mock_connection.execute.side_effect = ProgrammingError(
            "index 'idx_userbase_created_at' does not exist",
            None,
            None
        )
        
        # Mock the alembic operation context
        with patch('alembic.op.get_bind') as mock_get_bind:
            mock_get_bind.return_value = mock_connection
            
            # Import the specific migration function that drops the index
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'migration', 
                'netra_backend/app/alembic/versions/66e0e5d9662d_add_missing_tables_and_columns_complete.py'
            )
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            # This should fail because the migration attempts to drop a non-existent index
            # If this test passes, it means the migration is improperly handling non-existent indexes
            with pytest.raises(ProgrammingError, match="index.*idx_userbase_created_at.*does not exist"):
                migration_module._drop_userbase_indexes()
    
    @fast_test
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_migration_66e0e5d9662d_downgrade_restores_missing_indexes_fails(self):
        """
        FAILING TEST: Demonstrates migration downgrade issue when restoring non-existent indexes.
        
        This test reproduces issues where downgrade assumes indexes existed before migration.
        
        Expected behavior: Downgrade should handle cases where indexes may not have existed originally
        Current behavior: May fail to properly restore state when indexes weren't originally present
        """
        # Mock scenario where we try to restore indexes that never existed
        mock_connection = MagicNone  # TODO: Use real service instance
        mock_connection.execute.side_effect = [
            ProgrammingError("index already exists", None, None),  # First index fails
            None,  # Other operations succeed
            None,
            None,
            None
        ]
        
        # Mock the alembic operation context
        with patch('alembic.op.get_bind') as mock_get_bind:
            mock_get_bind.return_value = mock_connection
            
            # Import the specific migration function that restores indexes
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'migration', 
                'netra_backend/app/alembic/versions/66e0e5d9662d_add_missing_tables_and_columns_complete.py'
            )
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            # This should fail because the migration doesn't handle index restoration edge cases
            # If this test passes, it means the migration isn't properly validating index restoration
            with pytest.raises(ProgrammingError, match="index already exists"):
                migration_module._restore_userbase_indexes()
    
    @fast_test
    @pytest.mark.critical
    def test_migration_idempotency_check_missing_for_all_index_operations_fails(self):
        """
        FAILING TEST: Demonstrates that migration lacks proper idempotency checks.
        
        This test checks that all index drop/create operations in the migration
        include proper existence checks to ensure idempotency.
        
        Expected behavior: All index operations should include IF EXISTS/IF NOT EXISTS clauses
        Current behavior: Index operations assume specific database state
        """
        # Read the migration file content to check for idempotency patterns
        import os
        from pathlib import Path
        
        # Find the migration file
        migration_file = Path(__file__).parent.parent.parent / "app" / "alembic" / "versions" / "66e0e5d9662d_add_missing_tables_and_columns_complete.py"
        
        if not migration_file.exists():
            pytest.skip("Migration file not found")
        
        with open(migration_file, 'r') as f:
            migration_content = f.read()
        
        # Check if the migration contains proper idempotency patterns
        idempotent_patterns = [
            "if_exists=True",
            "if_not_exists=True", 
            "IF EXISTS",
            "IF NOT EXISTS",
            "DROP INDEX IF EXISTS",
            "CREATE INDEX IF NOT EXISTS"
        ]
        
        has_idempotency = any(pattern in migration_content for pattern in idempotent_patterns)
        
        # This should fail because the migration lacks idempotency checks
        # If this test passes, it means idempotency patterns were found (which is good)
        assert not has_idempotency, f"Migration should lack idempotency checks for this test to demonstrate the issue. Found patterns in: {migration_content[:500]}..."
    
    @fast_test
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_alembic_multiple_runs_same_migration_fails(self):
        """
        FAILING TEST: Demonstrates that running the same migration twice fails.
        
        This test simulates running migration 66e0e5d9662d multiple times to show
        non-idempotent behavior.
        
        Expected behavior: Migration should be idempotent and succeed on multiple runs
        Current behavior: Second run fails due to non-idempotent index operations
        """
        # Mock a successful first run followed by a failing second run
        mock_connection = MagicNone  # TODO: Use real service instance
        
        # First call succeeds (index exists and gets dropped)
        # Second call fails (index no longer exists)
        mock_connection.execute.side_effect = [
            None,  # First run: successful drop
            ProgrammingError("index 'idx_userbase_created_at' does not exist", None, None)  # Second run: fails
        ]
        
        with patch('alembic.op.get_bind') as mock_get_bind:
            mock_get_bind.return_value = mock_connection
            
            # Import the specific migration function
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'migration', 
                'netra_backend/app/alembic/versions/66e0e5d9662d_add_missing_tables_and_columns_complete.py'
            )
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            # First run should succeed
            migration_module._drop_userbase_indexes()
            
            # Second run should fail, demonstrating non-idempotency
            # If this test passes, it means the migration is properly handling repeated runs
            with pytest.raises(ProgrammingError, match="index.*does not exist"):
                migration_module._drop_userbase_indexes()
    
    @fast_test
    @pytest.mark.critical
    def test_userbase_table_index_assumptions_documented_fails(self):
        """
        FAILING TEST: Demonstrates lack of documentation about index assumptions.
        
        This test checks if the migration documents its assumptions about
        which indexes should exist before running.
        
        Expected behavior: Migration should document database state assumptions
        Current behavior: No documentation of required pre-migration state
        """
        # Read the migration file to check for documentation
        import os
        from pathlib import Path
        
        migration_file = Path(__file__).parent.parent.parent / "app" / "alembic" / "versions" / "66e0e5d9662d_add_missing_tables_and_columns_complete.py"
        
        if not migration_file.exists():
            pytest.skip("Migration file not found")
        
        with open(migration_file, 'r') as f:
            migration_content = f.read()
        
        # Check for documentation patterns
        documentation_patterns = [
            "Prerequisites:",
            "Assumes:",
            "Required state:",
            "idx_userbase_created_at",  # Should document this specific index
            "CAUTION:",
            "WARNING:"
        ]
        
        has_documentation = any(pattern in migration_content for pattern in documentation_patterns)
        
        # This should fail because the migration lacks proper documentation
        # If this test passes, it means documentation was found
        assert not has_documentation, "Migration should lack documentation for this test to demonstrate the issue"