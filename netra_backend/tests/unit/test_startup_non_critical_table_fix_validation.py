"""
Test Non-Critical Table Startup Logic Fix Validation

This test validates the critical fix implemented for lines 143-158 in startup_module.py
to resolve tangled startup logic where non-critical tables were incorrectly blocking startup.

CRITICAL FIX TESTED:
- Non-critical tables (credit_transactions, agent_executions, subscriptions) should NOT block startup
- Critical tables (users, threads, messages, runs, assistants) MUST still block startup when missing
- Both graceful and strict modes should allow startup with missing non-critical tables
- Strict mode should provide enhanced logging without exceptions for non-critical tables

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Prevent false startup failures that block production deployments
- Value Impact: Eliminates broken deployments when optional features are not ready
- Strategic Impact: Ensures core chat functionality always available regardless of non-critical table status
"""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI

# Absolute imports following CLAUDE.md guidelines
from netra_backend.app.startup_module import _verify_required_database_tables_exist
from shared.isolated_environment import get_env

# Set test environment
env = get_env()
env.set("ENVIRONMENT", "testing", "test")
env.set("TESTING", "true", "test")


class MockEngine:
    """Mock database engine for testing table validation."""
    
    def __init__(self, existing_tables=None):
        self.existing_tables = existing_tables or set()
        self._disposed = False
        
    def connect(self):
        # Return an async context manager
        class AsyncContextManager:
            def __init__(self, connection):
                self.connection = connection
            
            async def __aenter__(self):
                return self.connection
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
        return AsyncContextManager(MockConnection(self.existing_tables))
    
    async def dispose(self):
        self._disposed = True


class MockConnection:
    """Mock database connection for testing."""
    
    def __init__(self, existing_tables):
        self.existing_tables = existing_tables
        self._transaction = None
        
    def begin(self):
        self._transaction = MockTransaction()
        return self._transaction
        
    async def execute(self, query):
        # Mock the information_schema query result
        return MockResult(self.existing_tables)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockTransaction:
    """Mock database transaction."""
    
    async def commit(self):
        pass
        
    async def rollback(self):
        pass
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockResult:
    """Mock database query result."""
    
    def __init__(self, existing_tables):
        self.existing_tables = existing_tables
        
    def fetchall(self):
        return [(table,) for table in self.existing_tables]


class TestStartupNonCriticalTableFix:
    """Test the non-critical table startup logic fix."""
    
    def setup_method(self):
        """Setup test logging."""
        self.logger = logging.getLogger("test_startup_validation")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers to prevent duplicate messages
        self.logger.handlers = []
        
        # Add test handler
        self.log_messages = []
        handler = logging.Handler()
        handler.emit = lambda record: self.log_messages.append(record.getMessage())
        self.logger.addHandler(handler)
    
    @pytest.mark.asyncio
    async def test_critical_tables_missing_behavior_graceful_mode(self):
        """Test that missing critical tables log warnings in graceful mode (current behavior)."""
        # Setup: Mock missing critical tables (users, threads)
        existing_tables = {'messages', 'runs', 'assistants'}  # Missing users, threads
        
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    # Setup expected tables (critical + non-critical)
                    mock_base.metadata.tables.keys.return_value = {
                        'users', 'threads', 'messages', 'runs', 'assistants',  # Critical
                        'credit_transactions', 'agent_executions', 'subscriptions'  # Non-critical
                    }
                    
                    # Current behavior: In graceful mode, critical table RuntimeError is caught
                    # and converted to a warning. This is existing behavior, not related to the fix.
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
                    
                    # Verify the critical table error was logged
                    log_text = ' '.join(self.log_messages)
                    assert "CRITICAL STARTUP FAILURE" in log_text
                    assert "Missing CRITICAL database tables" in log_text
    
    @pytest.mark.asyncio
    async def test_critical_tables_missing_blocks_startup_strict_mode(self):
        """Test that missing critical tables STILL block startup in strict mode."""
        # Setup: Mock missing critical table (users)
        existing_tables = {'threads', 'messages', 'runs', 'assistants'}  # Missing users
        
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    # Setup expected tables
                    mock_base.metadata.tables.keys.return_value = {
                        'users', 'threads', 'messages', 'runs', 'assistants',  # Critical
                        'credit_transactions', 'agent_executions', 'subscriptions'  # Non-critical
                    }
                    
                    # Should raise RuntimeError for missing critical tables
                    with pytest.raises(RuntimeError) as exc_info:
                        await _verify_required_database_tables_exist(self.logger, graceful_startup=False)
                    
                    assert "Missing critical database tables" in str(exc_info.value)
                    assert "users" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_non_critical_tables_missing_allows_startup_graceful_mode(self):
        """Test that missing non-critical tables DON'T block startup in graceful mode."""
        # Setup: All critical tables present, non-critical tables missing
        existing_tables = {'users', 'threads', 'messages', 'runs', 'assistants'}  # All critical present
        # Missing: credit_transactions, agent_executions, subscriptions
        
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    # Setup expected tables (critical + non-critical)
                    mock_base.metadata.tables.keys.return_value = {
                        'users', 'threads', 'messages', 'runs', 'assistants',  # Critical
                        'credit_transactions', 'agent_executions', 'subscriptions'  # Non-critical
                    }
                    
                    # Should NOT raise exception - startup should continue
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
                    
                    # Verify appropriate warning messages were logged
                    log_text = ' '.join(self.log_messages)
                    assert "Missing non-critical database tables" in log_text
                    assert "credit_transactions" in log_text or "agent_executions" in log_text
                    assert "Continuing with degraded functionality - core chat will work" in log_text
    
    @pytest.mark.asyncio 
    async def test_non_critical_tables_missing_allows_startup_strict_mode(self):
        """CRITICAL TEST: Non-critical tables DON'T block startup in STRICT mode (the fix)."""
        # Setup: All critical tables present, non-critical tables missing
        existing_tables = {'users', 'threads', 'messages', 'runs', 'assistants'}  # All critical present
        # Missing: credit_transactions, agent_executions, subscriptions
        
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    # Setup expected tables (critical + non-critical)
                    mock_base.metadata.tables.keys.return_value = {
                        'users', 'threads', 'messages', 'runs', 'assistants',  # Critical
                        'credit_transactions', 'agent_executions', 'subscriptions'  # Non-critical
                    }
                    
                    # CRITICAL TEST: Should NOT raise exception even in strict mode
                    # This is the main fix being tested
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=False)
                    
                    # Verify strict mode logging messages
                    log_text = ' '.join(self.log_messages)
                    assert "Missing non-critical database tables" in log_text
                    assert "STRICT MODE: Missing non-critical tables logged for operations team" in log_text
                    assert "Features affected may include: advanced analytics, credit tracking, agent execution history" in log_text
                    assert "Non-critical tables don't block startup in any mode" in log_text
    
    @pytest.mark.asyncio
    async def test_all_tables_present_succeeds_both_modes(self):
        """Test that when all tables are present, both modes succeed."""
        # Setup: All tables present
        existing_tables = {
            'users', 'threads', 'messages', 'runs', 'assistants',  # Critical
            'credit_transactions', 'agent_executions', 'subscriptions'  # Non-critical
        }
        
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    mock_base.metadata.tables.keys.return_value = existing_tables
                    
                    # Should succeed in graceful mode
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
                    
                    # Should succeed in strict mode
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=False)
                    
                    # Verify success message
                    log_text = ' '.join(self.log_messages)
                    assert "All" in log_text and "required database tables are present" in log_text
    
    @pytest.mark.asyncio
    async def test_mixed_critical_non_critical_missing_graceful_behavior(self):
        """Test that missing BOTH critical and non-critical tables logs warnings in graceful mode."""
        # Setup: Missing both critical and non-critical tables
        existing_tables = {'messages', 'runs'}  # Missing users, threads, assistants (critical) + all non-critical
        
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = MockEngine(existing_tables)
            
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                with patch('netra_backend.app.db.base.Base') as mock_base:
                    mock_base.metadata.tables.keys.return_value = {
                        'users', 'threads', 'messages', 'runs', 'assistants',  # Critical
                        'credit_transactions', 'agent_executions', 'subscriptions'  # Non-critical
                    }
                    
                    # Current behavior: In graceful mode, critical table errors are caught and logged
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
                    
                    # Verify critical table error was logged  
                    log_text = ' '.join(self.log_messages)
                    assert "CRITICAL STARTUP FAILURE" in log_text
                    assert "Missing CRITICAL database tables" in log_text
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_graceful_mode(self):
        """Test that database connection failure is handled gracefully in graceful mode."""
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = None  # Simulate engine failure
            
            # Should not raise exception in graceful mode
            await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
            
            # Verify warning message
            log_text = ' '.join(self.log_messages)
            assert "Failed to get database engine" in log_text
            assert "continuing without table verification" in log_text
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_strict_mode(self):
        """Test that database connection failure raises exception in strict mode."""
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = None  # Simulate engine failure
            
            # Should raise RuntimeError in strict mode
            with pytest.raises(RuntimeError) as exc_info:
                await _verify_required_database_tables_exist(self.logger, graceful_startup=False)
            
            assert "Failed to get database engine" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_table_query_exception_handling(self):
        """Test handling of database query exceptions."""
        
        class FailingConnection:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
            def begin(self):
                return MockTransaction()
            async def execute(self, query):
                raise Exception("Database query failed")
        
        class FailingEngine:
            def connect(self):
                # Return an async context manager
                class AsyncContextManager:
                    async def __aenter__(self):
                        return FailingConnection()
                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        pass
                return AsyncContextManager()
            async def dispose(self):
                pass
        
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            mock_get_engine.return_value = FailingEngine()
            
            with patch('netra_backend.app.startup_module._import_all_models') as mock_import:
                # Should not raise in graceful mode
                await _verify_required_database_tables_exist(self.logger, graceful_startup=True)
                
                # Should raise in strict mode
                with pytest.raises(RuntimeError):
                    await _verify_required_database_tables_exist(self.logger, graceful_startup=False)
    
    def test_critical_table_definitions(self):
        """Test that critical table definitions are correct."""
        # Verify the SSOT critical table definitions match what's in the code
        expected_critical_tables = {'users', 'threads', 'messages', 'runs', 'assistants'}
        
        # This is from the actual code - these are the core chat functionality tables
        # Import the function and examine its critical_tables definition
        import inspect
        source = inspect.getsource(_verify_required_database_tables_exist)
        
        # Verify the critical tables are defined as expected
        assert "'users'" in source
        assert "'threads'" in source  
        assert "'messages'" in source
        assert "'runs'" in source
        assert "'assistants'" in source
        assert "Core chat functionality" in source
    
    def test_non_critical_examples(self):
        """Test that the examples of non-critical tables are correctly identified."""
        # These should be identified as non-critical based on the fix
        non_critical_examples = {'credit_transactions', 'agent_executions', 'subscriptions'}
        critical_tables = {'users', 'threads', 'messages', 'runs', 'assistants'}
        
        # Verify no overlap between critical and non-critical examples
        assert len(non_critical_examples & critical_tables) == 0
        
        # Verify these would be classified as non-critical
        all_tables = critical_tables | non_critical_examples
        non_critical_computed = all_tables - critical_tables
        
        for table in non_critical_examples:
            assert table in non_critical_computed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])