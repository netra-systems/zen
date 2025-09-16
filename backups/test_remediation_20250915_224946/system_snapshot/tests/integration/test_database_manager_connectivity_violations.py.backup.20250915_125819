#!/usr/bin/env python3
"""INTEGRATION: DatabaseManager SSOT Connectivity Violation Detection

BUSINESS VALUE: $500K+ ARR - Database connectivity is foundation for all operations

DESIGNED TO FAIL when:
1. DatabaseManager cannot initialize properly
2. Database connections fail
3. WebSocket integration broken
4. Session factory methods missing
5. URL builder integration broken

DESIGNED TO PASS when:
1. DatabaseManager initializes correctly
2. All database connections work
3. WebSocket can access database sessions
4. All required methods present
5. URL construction works properly

ANY FAILURE HERE INDICATES BROKEN DATABASE CONNECTIVITY.
"""

import asyncio
import os
import sys
from typing import Dict, Any, Optional
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.integration
class TestDatabaseManagerConnectivityViolations(SSotAsyncTestCase):
    """Test suite to detect DatabaseManager connectivity violations."""

    async def test_database_manager_initialization_completeness(self):
        """MUST FAIL if DatabaseManager cannot initialize with all required components."""
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        # Test initialization
        db_manager = DatabaseManager()

        # Verify required attributes exist
        required_attributes = [
            '_engines',
            '_initialized',
            '_url_builder',
            'config'
        ]

        for attr in required_attributes:
            if not hasattr(db_manager, attr):
                pytest.fail(f"MISSING REQUIRED ATTRIBUTE: {attr}")

        # Test initialization process
        try:
            await db_manager.initialize()
        except Exception as e:
            pytest.fail(f"DATABASE MANAGER INITIALIZATION FAILED: {e}")

        if not db_manager._initialized:
            pytest.fail("DATABASE MANAGER NOT PROPERLY INITIALIZED")

    async def test_database_manager_required_methods_exist(self):
        """MUST FAIL if required DatabaseManager methods are missing."""
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        db_manager = DatabaseManager()

        # Critical methods required for WebSocket integration (GitHub Issue #204)
        required_methods = [
            'initialize',
            'get_postgres_session',
            'get_clickhouse_session',
            'get_db_session_factory',  # Critical for WebSocket factory
            'close_connections',
            '_get_postgres_url',
            '_get_clickhouse_url'
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(db_manager, method):
                missing_methods.append(method)

        if missing_methods:
            method_list = ', '.join(missing_methods)
            pytest.fail(f"MISSING REQUIRED METHODS: {method_list}")

    async def test_database_url_builder_integration(self):
        """MUST FAIL if DatabaseURLBuilder integration is broken."""
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Verify URL builder integration
        if db_manager._url_builder is None:
            pytest.fail("URL_BUILDER NOT INITIALIZED")

        # Test URL construction methods
        try:
            # These should not raise exceptions
            postgres_url = await db_manager._get_postgres_url()
            clickhouse_url = await db_manager._get_clickhouse_url()

            if not postgres_url:
                pytest.fail("POSTGRES URL CONSTRUCTION FAILED")
            if not clickhouse_url:
                pytest.fail("CLICKHOUSE URL CONSTRUCTION FAILED")

            # URLs should be properly formatted
            if not postgres_url.startswith(('postgresql://', 'postgresql+asyncpg://')):
                pytest.fail(f"INVALID POSTGRES URL FORMAT: {postgres_url}")
            if not clickhouse_url.startswith(('clickhouse://', 'clickhouse+asynch://')):
                pytest.fail(f"INVALID CLICKHOUSE URL FORMAT: {clickhouse_url}")

        except Exception as e:
            pytest.fail(f"URL CONSTRUCTION FAILED: {e}")

    async def test_websocket_database_session_factory_integration(self):
        """MUST FAIL if WebSocket factory cannot access database sessions.

        This test reproduces GitHub Issue #204 - WebSocket factory session factory failures.
        """
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        # Test WebSocket bridge factory integration
        try:
            from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory
        except ImportError:
            # If WebSocket bridge factory doesn't exist, test direct integration
            pass
        else:
            # Test WebSocket factory can access database sessions
            try:
                factory = WebSocketBridgeFactory()

                # This is the critical test - WebSocket factory MUST be able to get database sessions
                if hasattr(factory, 'get_db_session_factory'):
                    session_factory = factory.get_db_session_factory()
                    if not session_factory:
                        pytest.fail("WEBSOCKET FACTORY CANNOT CREATE DATABASE SESSIONS")
                else:
                    pytest.fail("WEBSOCKET FACTORY MISSING DB SESSION ACCESS METHODS")

            except Exception as e:
                pytest.fail(f"WEBSOCKET DATABASE INTEGRATION BROKEN: {e}")

        # Test direct DatabaseManager session factory
        db_manager = DatabaseManager()
        await db_manager.initialize()

        try:
            session_factory = db_manager.get_db_session_factory()
            if not session_factory:
                pytest.fail("DATABASE MANAGER SESSION FACTORY CREATION FAILED")
        except Exception as e:
            pytest.fail(f"SESSION FACTORY CREATION ERROR: {e}")

    async def test_database_connections_actually_work(self):
        """MUST FAIL if database connections cannot be established."""
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Test PostgreSQL connection
        try:
            async with db_manager.get_postgres_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1 as test_connection"))
                row = result.fetchone()
                if not row or row[0] != 1:
                    pytest.fail("POSTGRES CONNECTION TEST FAILED")
        except Exception as e:
            pytest.fail(f"POSTGRES CONNECTION FAILED: {e}")

        # Test ClickHouse connection
        try:
            async with db_manager.get_clickhouse_session() as session:
                result = await session.execute("SELECT 1 as test_connection")
                row = result.fetchone()
                if not row or row[0] != 1:
                    pytest.fail("CLICKHOUSE CONNECTION TEST FAILED")
        except Exception as e:
            pytest.fail(f"CLICKHOUSE CONNECTION FAILED: {e}")

    async def test_database_manager_engine_management(self):
        """MUST FAIL if database engines are not properly managed."""
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Check engines are created
        if 'postgres' not in db_manager._engines:
            pytest.fail("POSTGRES ENGINE NOT CREATED")
        if 'clickhouse' not in db_manager._engines:
            pytest.fail("CLICKHOUSE ENGINE NOT CREATED")

        # Test engine properties
        postgres_engine = db_manager._engines['postgres']
        clickhouse_engine = db_manager._engines['clickhouse']

        if not postgres_engine:
            pytest.fail("POSTGRES ENGINE IS NONE")
        if not clickhouse_engine:
            pytest.fail("CLICKHOUSE ENGINE IS NONE")

        # Test connection cleanup
        try:
            await db_manager.close_connections()
        except Exception as e:
            pytest.fail(f"CONNECTION CLEANUP FAILED: {e}")

    async def test_database_configuration_integration(self):
        """MUST FAIL if database configuration is not properly integrated."""
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        db_manager = DatabaseManager()

        # Verify configuration integration
        if not hasattr(db_manager, 'config') or db_manager.config is None:
            pytest.fail("DATABASE CONFIGURATION NOT PROPERLY INTEGRATED")

        await db_manager.initialize()

        # Test configuration usage
        try:
            # Configuration should provide database URLs
            postgres_url = await db_manager._get_postgres_url()
            clickhouse_url = await db_manager._get_clickhouse_url()

            # URLs should be non-empty and properly formatted
            if not postgres_url or len(postgres_url.strip()) == 0:
                pytest.fail("POSTGRES URL NOT PROVIDED BY CONFIGURATION")
            if not clickhouse_url or len(clickhouse_url.strip()) == 0:
                pytest.fail("CLICKHOUSE URL NOT PROVIDED BY CONFIGURATION")

        except Exception as e:
            pytest.fail(f"CONFIGURATION INTEGRATION FAILED: {e}")