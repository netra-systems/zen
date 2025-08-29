"""
Integration Tests for Migration State Recovery

Tests the complete integration of migration state recovery with existing systems.
Verifies that the critical migration issue fixes work end-to-end with real database
scenarios including startup, migration tracking, and database initialization.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Verify critical migration fixes prevent startup failures
- Value Impact: Ensures system reliability and operational continuity  
- Strategic Impact: Validates fix for the last major blocker to full system operation
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, List, Optional

from netra_backend.app.db.alembic_state_recovery import (
    MigrationStateManager,
    MigrationStateAnalyzer,
    AlembicStateRecovery,
    ensure_migration_state_healthy
)
from netra_backend.app.startup.migration_tracker import MigrationTracker
from netra_backend.app.db.migration_utils import get_current_revision


@pytest.mark.asyncio
class TestMigrationStateRecoveryIntegration:
    """Integration tests for migration state recovery across components"""
    
    async def test_end_to_end_recovery_for_critical_scenario(self):
        """Test complete recovery flow for the critical startup failure scenario"""
        database_url = "postgresql://test:test@localhost/test_db"
        
        # Mock the critical scenario: existing schema, no alembic_version
        def mock_create_engine(url):
            mock_engine = Mock()
            mock_conn = Mock()
            mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
            
            # Mock existing tables but no alembic_version
            mock_conn.execute.side_effect = self._simulate_critical_scenario
            return mock_engine
        
        with patch('sqlalchemy.create_engine', side_effect=mock_create_engine):
            with patch('alembic.config.Config'):
                with patch('alembic.command.stamp') as mock_stamp:
                    with patch('alembic.script.ScriptDirectory.from_config') as mock_script:
                        # Mock head revision
                        mock_script_dir = Mock()
                        mock_script_dir.get_current_head.return_value = "bb39e1c49e2d"
                        mock_script.return_value = mock_script_dir
                        
                        # Execute recovery
                        success, state_info = await ensure_migration_state_healthy(database_url)
                        
                        # Verify recovery succeeded
                        assert success is True, f"Recovery should succeed, got: {state_info}"
                        assert "INITIALIZE_ALEMBIC_VERSION" in str(state_info)
                        
                        # Verify stamp command was called
                        mock_stamp.assert_called_once()
    
    def _simulate_critical_scenario(self, query):
        """Simulate the critical scenario causing startup failures"""
        query_str = str(query)
        result = Mock()
        
        if "information_schema.tables" in query_str:
            # Existing schema with core tables
            result.fetchall.return_value = [
                ("users",), ("threads",), ("messages",), ("runs",), ("steps",)
            ]
        elif "SELECT version_num FROM alembic_version" in query_str:
            # No alembic_version table (this is the critical issue)
            result.fetchone.return_value = None
            raise Exception("relation \"alembic_version\" does not exist")
        elif "CREATE TABLE alembic_version" in query_str:
            # Allow table creation
            result.rowcount = 1
        elif "INSERT INTO alembic_version" in query_str:
            # Allow revision insertion
            result.rowcount = 1
        
        return result
    
    @pytest.mark.asyncio
    async def test_migration_tracker_integration(self):
        """Test integration with MigrationTracker"""
        database_url = "postgresql://test:test@localhost/test_db"
        
        # Create tracker with mocked state recovery
        with patch('netra_backend.app.db.alembic_state_recovery.ensure_migration_state_healthy') as mock_recovery:
            mock_recovery.return_value = (True, {"recovery_strategy": "INITIALIZE_ALEMBIC_VERSION"})
            
            # Create temporary directory for state file
            with tempfile.TemporaryDirectory() as temp_dir:
                tracker = MigrationTracker(database_url)
                tracker.state_file = Path(temp_dir) / "migration_state.json"
                
                # Mock the alembic configuration
                with patch.object(tracker, '_get_alembic_config') as mock_config:
                    with patch('netra_backend.app.db.migration_utils.get_current_revision', return_value="bb39e1c49e2d"):
                        with patch('netra_backend.app.db.migration_utils.get_head_revision', return_value="bb39e1c49e2d"):
                            
                            # Check migrations (this will trigger recovery)
                            state = await tracker.check_migrations()
                            
                            # Verify recovery was called
                            mock_recovery.assert_called_once_with(database_url)
                            
                            # Verify state is valid
                            assert state is not None
                            assert hasattr(state, 'current_version')
    
    @pytest.mark.asyncio
    async def test_database_initializer_coordination(self):
        """Test coordination with DatabaseInitializer"""
        from netra_backend.app.db.database_initializer import DatabaseInitializer, DatabaseConfig, DatabaseType
        
        # Create database config
        config = DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            host="localhost", port=5432, database="test_db",
            user="test", password="test"
        )
        
        initializer = DatabaseInitializer()
        initializer.add_database(config)
        
        # Mock the scenario where recovery is needed
        with patch('netra_backend.app.db.alembic_state_recovery.ensure_migration_state_healthy') as mock_recovery:
            mock_recovery.return_value = (True, {
                "recovery_strategy": "INITIALIZE_ALEMBIC_VERSION",
                "has_existing_schema": True,
                "requires_recovery": True
            })
            
            with patch('asyncpg.connect'):
                with patch('psycopg2.connect'):
                    # The DatabaseInitializer should coordinate with recovery
                    # This test ensures no conflicts between systems
                    
                    # Mock successful initialization
                    mock_conn = AsyncMock()
                    mock_conn.fetchval.side_effect = [
                        True,  # alembic_version exists (after recovery)
                        "bb39e1c49e2d"  # current revision
                    ]
                    mock_conn.fetch.return_value = [
                        {'table_name': 'users'}, 
                        {'table_name': 'alembic_version'},
                        {'table_name': 'sessions'}
                    ]
                    
                    with patch('asyncpg.connect', return_value=mock_conn):
                        result = await initializer._initialize_postgresql_schema(config)
                        
                        # Should coordinate successfully
                        assert result is True
    
    @pytest.mark.asyncio
    async def test_recovery_handles_various_database_states(self):
        """Test recovery handles various problematic database states"""
        database_url = "postgresql://test:test@localhost/test_db"
        manager = MigrationStateManager(database_url)
        
        # Test Case 1: Fresh database (should not need recovery)
        with patch.object(manager.analyzer, 'analyze_migration_state') as mock_analyze:
            mock_analyze.return_value = {
                "has_existing_schema": False,
                "has_alembic_version": False,
                "requires_recovery": False,
                "recovery_strategy": "NORMAL_MIGRATION"
            }
            
            success, state = await manager.ensure_healthy_migration_state()
            assert success is True
            assert state["recovery_strategy"] == "NORMAL_MIGRATION"
        
        # Test Case 2: Critical scenario (existing schema, no alembic_version)
        with patch.object(manager.analyzer, 'analyze_migration_state') as mock_analyze:
            with patch.object(manager.recovery, 'initialize_alembic_version_for_existing_schema', return_value=True):
                mock_analyze.side_effect = [
                    {  # Initial state
                        "has_existing_schema": True,
                        "has_alembic_version": False,
                        "requires_recovery": True,
                        "recovery_strategy": "INITIALIZE_ALEMBIC_VERSION"
                    },
                    {  # State after recovery
                        "has_existing_schema": True,
                        "has_alembic_version": True,
                        "requires_recovery": False,
                        "recovery_strategy": "NO_ACTION_NEEDED"
                    }
                ]
                
                success, final_state = await manager.ensure_healthy_migration_state()
                assert success is True
                assert final_state["recovery_strategy"] == "NO_ACTION_NEEDED"
        
        # Test Case 3: Partial migration (some tables missing)
        with patch.object(manager.analyzer, 'analyze_migration_state') as mock_analyze:
            with patch.object(manager.recovery, 'complete_partial_migration', return_value=True):
                mock_analyze.side_effect = [
                    {
                        "has_existing_schema": True,
                        "has_alembic_version": True,
                        "requires_recovery": True,
                        "recovery_strategy": "COMPLETE_PARTIAL_MIGRATION",
                        "missing_expected_tables": ["messages", "runs"]
                    },
                    {
                        "has_existing_schema": True,
                        "has_alembic_version": True,
                        "requires_recovery": False,
                        "recovery_strategy": "NO_ACTION_NEEDED"
                    }
                ]
                
                success, final_state = await manager.ensure_healthy_migration_state()
                assert success is True
                assert final_state["recovery_strategy"] == "NO_ACTION_NEEDED"
    
    @pytest.mark.asyncio
    async def test_startup_integration_prevents_failures(self):
        """Test that recovery integration prevents startup failures"""
        database_url = "postgresql://test:test@localhost/test_db"
        
        # Simulate the startup sequence that was previously failing
        startup_steps = []
        
        # Step 1: Migration state check (with recovery)
        with patch('netra_backend.app.db.alembic_state_recovery.ensure_migration_state_healthy') as mock_recovery:
            mock_recovery.return_value = (True, {"recovery_strategy": "INITIALIZE_ALEMBIC_VERSION"})
            
            success, recovery_info = await ensure_migration_state_healthy(database_url)
            startup_steps.append(("migration_state_recovery", success))
            
            assert success is True, "Migration state recovery should succeed"
        
        # Step 2: Migration tracking
        with patch('netra_backend.app.db.migration_utils.get_current_revision', return_value="bb39e1c49e2d"):
            with patch('netra_backend.app.db.migration_utils.get_head_revision', return_value="bb39e1c49e2d"):
                tracker = MigrationTracker(database_url)
                
                # This should now work without failure
                with tempfile.TemporaryDirectory() as temp_dir:
                    tracker.state_file = Path(temp_dir) / "migration_state.json" 
                    
                    state = await tracker.check_migrations()
                    startup_steps.append(("migration_check", state is not None))
        
        # Step 3: Database initialization (should coordinate properly)
        from netra_backend.app.db.database_initializer import DatabaseInitializer, DatabaseConfig, DatabaseType
        
        config = DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            host="localhost", port=5432, database="test_db",
            user="test", password="test"
        )
        
        initializer = DatabaseInitializer()
        initializer.add_database(config)
        
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = [
            True,  # alembic_version exists (recovered)
            "bb39e1c49e2d"  # current revision
        ]
        mock_conn.fetch.return_value = [{'table_name': 'users'}, {'table_name': 'alembic_version'}]
        
        with patch('asyncpg.connect', return_value=mock_conn):
            with patch('psycopg2.connect'):
                result = await initializer._initialize_postgresql_schema(config)
                startup_steps.append(("database_initialization", result))
        
        # Verify all startup steps succeeded
        for step_name, step_success in startup_steps:
            assert step_success is True, f"Startup step '{step_name}' should succeed"
        
        # This represents successful startup without migration failures
        assert len(startup_steps) == 3
        assert all(success for _, success in startup_steps)
    
    @pytest.mark.asyncio
    async def test_error_handling_graceful_degradation(self):
        """Test graceful error handling when recovery cannot be performed"""
        database_url = "postgresql://invalid_connection"
        
        # Test that connection failures are handled gracefully
        with patch('sqlalchemy.create_engine', side_effect=Exception("Connection failed")):
            success, state_info = await ensure_migration_state_healthy(database_url)
            
            # Should fail gracefully without crashing
            assert success is False
            assert "error" in state_info or "Connection failed" in str(state_info)
        
        # Test that recovery failures don't prevent system startup
        manager = MigrationStateManager(database_url)
        
        with patch.object(manager.analyzer, 'analyze_migration_state', side_effect=Exception("Analysis failed")):
            success, state = await manager.ensure_healthy_migration_state()
            
            # Should handle gracefully
            assert success is False
            assert "error" in state
    
    @pytest.mark.asyncio
    async def test_recovery_status_reporting(self):
        """Test comprehensive status reporting for recovery operations"""
        database_url = "postgresql://test:test@localhost/test_db"
        manager = MigrationStateManager(database_url)
        
        with patch.object(manager.analyzer, 'analyze_migration_state') as mock_analyze:
            mock_analyze.return_value = {
                "has_existing_schema": True,
                "has_alembic_version": False,
                "requires_recovery": True,
                "recovery_strategy": "INITIALIZE_ALEMBIC_VERSION",
                "existing_tables": ["users", "threads", "messages"],
                "current_revision": None,
                "analysis_timestamp": "2025-01-01T00:00:00"
            }
            
            report = await manager.get_migration_status_report()
            
            # Verify comprehensive reporting
            assert report["database_url"] == database_url
            assert report["health_status"] == "REQUIRES_RECOVERY"
            assert report["recommended_action"] == "INITIALIZE_ALEMBIC_VERSION"
            assert "migration_state" in report
            assert "timestamp" in report
            
            # Verify detailed state information
            state = report["migration_state"]
            assert state["has_existing_schema"] is True
            assert state["has_alembic_version"] is False
            assert len(state["existing_tables"]) == 3