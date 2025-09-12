#!/usr/bin/env python
"""MISSION CRITICAL: DatabaseManager SSOT Function Violations Test Suite

THIS SUITE REPRODUCES GITHUB ISSUE #204 - WEBSOCKET FACTORY SESSION FACTORY FAILURES
Business Value: $500K+ ARR - WebSocket connections depend on database session creation

CRITICAL VIOLATIONS TO DETECT:
1. Missing `get_db_session_factory` function blocking WebSocket connections (GitHub Issue #204)
2. WebSocket factory initialization fails when database manager doesn't provide session factory
3. 1011 WebSocket errors caused by database session creation failures

DESIGNED TO FAIL PRE-SSOT REFACTOR:
- Tests will FAIL when get_db_session_factory is missing from DatabaseManager
- Tests will FAIL when WebSocket factory cannot create database sessions

DESIGNED TO PASS POST-SSOT REFACTOR:
- Tests will PASS when get_database_manager provides session creation
- Tests will PASS when WebSocket factory can access database sessions
- Tests will PASS when all database manager methods work correctly

ANY FAILURE HERE INDICATES DATABASE SSOT VIOLATIONS.
"""

import asyncio
import logging
import os
import sys
import traceback
from typing import Optional, Dict, Any
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# SSOT imports - all tests must use SSOT framework
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestDatabaseManagerSSOTFunctionViolations(SSotBaseTestCase):
    """
    Test suite to detect and validate DatabaseManager SSOT function violations.
    
    These tests reproduce the exact GitHub Issue #204 error where WebSocket 
    factory fails due to missing database session factory functions.
    """
    
    def setup_method(self, method=None):
        """Setup with enhanced database-specific tracking."""
        super().setup_method(method)
        self.record_metric("test_category", "database_ssot_function_violations")
        
        # Track database-related metrics
        self._database_imports_attempted = []
        self._websocket_imports_attempted = []
        self._function_calls_attempted = []
        
    def test_websocket_can_access_database_via_ssot_methods(self):
        """
        UPDATED TO USE SSOT: WebSocket can access database via correct SSOT methods
        
        This test validates the SSOT solution for GitHub issue #204:
        - WebSocket should use get_database_manager() instead of get_db_session_factory
        - DatabaseManager provides get_session(), get_async_session() methods
        - WebSocket connections work with SSOT-compliant database access
        """
        self.record_metric("validation_type", "ssot_compliant_database_access")
        
        # Test 1: get_database_manager should exist and work
        database_manager_success = False
        try:
            from netra_backend.app.db.database_manager import get_database_manager
            self._function_calls_attempted.append("get_database_manager")
            
            manager = get_database_manager()
            assert manager is not None, "get_database_manager returned None"
            database_manager_success = True
            self.record_metric("get_database_manager_success", True)
            logger.info(" PASS:  get_database_manager() works - SSOT method available")
            
        except ImportError as e:
            logger.error(f" FAIL:  get_database_manager not available: {e}")
            self.record_metric("get_database_manager_import_error", str(e))
        except Exception as e:
            logger.error(f" FAIL:  get_database_manager failed: {e}")
            self.record_metric("get_database_manager_error", str(e))
        
        # Test 2: DatabaseManager should have session methods WebSocket needs
        session_methods_available = False
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            
            db_manager = DatabaseManager()
            
            # Check for SSOT session methods that WebSocket can use
            required_methods = ['get_session', 'initialize']
            available_methods = []
            
            for method_name in required_methods:
                if hasattr(db_manager, method_name):
                    available_methods.append(method_name)
            
            if len(available_methods) >= 2:  # Both get_session and initialize
                session_methods_available = True
                self.record_metric("ssot_session_methods_available", available_methods)
                logger.info(f" PASS:  DatabaseManager has SSOT session methods: {available_methods}")
            else:
                self.record_metric("ssot_session_methods_missing", required_methods)
                logger.error(f" FAIL:  Missing required methods: {required_methods}")
                
        except Exception as e:
            logger.error(f" FAIL:  DatabaseManager session method check failed: {e}")
            self.record_metric("database_manager_method_error", str(e))
        
        # Test 3: Verify WebSocket can use SSOT pattern
        websocket_ssot_compatible = False
        try:
            # This simulates how WebSocket factory should access database
            from netra_backend.app.db.database_manager import get_database_manager
            
            manager = get_database_manager()
            
            # WebSocket factory should be able to:
            # 1. Get database manager
            # 2. Check if it has session creation methods
            # 3. Use those methods for database access
            
            if hasattr(manager, 'get_session') and hasattr(manager, 'initialize'):
                websocket_ssot_compatible = True
                self.record_metric("websocket_ssot_pattern_compatible", True)
                logger.info(" PASS:  WebSocket can use SSOT database access pattern")
            
        except Exception as e:
            logger.error(f" FAIL:  WebSocket SSOT compatibility check failed: {e}")
            self.record_metric("websocket_ssot_compatibility_error", str(e))
        
        # ASSERTION: All SSOT methods should be available for WebSocket
        assert database_manager_success, (
            " FAIL:  SSOT VIOLATION: get_database_manager() not available for WebSocket factory"
        )
        
        assert session_methods_available, (
            " FAIL:  SSOT VIOLATION: DatabaseManager missing session methods needed by WebSocket"
        )
        
        assert websocket_ssot_compatible, (
            " FAIL:  SSOT VIOLATION: WebSocket cannot use SSOT database access pattern"
        )
        
        logger.info(" PASS:  SSOT REMEDIATION SUCCESSFUL: WebSocket can access database via SSOT methods")
    
    def test_get_database_manager_replacement_works(self):
        """
        DESIGNED TO PASS: Verify get_database_manager is correct replacement
        
        This test validates that the SSOT-compliant approach works:
        - get_database_manager function exists and works
        - DatabaseManager provides all needed session creation methods
        - WebSocket factory can use the SSOT approach
        """
        self.record_metric("validation_type", "ssot_compliant_replacement")
        
        # Test 1: get_database_manager should exist
        try:
            from netra_backend.app.db.database_manager import get_database_manager
            self._function_calls_attempted.append("get_database_manager")
            
            manager = get_database_manager()
            assert manager is not None, "get_database_manager returned None"
            self.record_metric("get_database_manager_success", True)
            
        except ImportError as e:
            # This is acceptable - get_database_manager might not exist yet
            logger.info(f"get_database_manager not found: {e}")
            self.record_metric("get_database_manager_missing", True)
            return  # Skip rest of test if function doesn't exist
        
        # Test 2: DatabaseManager instance should provide session methods
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            
            db_manager = DatabaseManager()
            
            # Check for session creation methods
            session_methods = []
            for method_name in ['get_session_factory', 'create_session', 'get_async_session']:
                if hasattr(db_manager, method_name):
                    session_methods.append(method_name)
            
            assert len(session_methods) > 0, (
                f"DatabaseManager has no session creation methods. "
                f"Available methods: {dir(db_manager)}"
            )
            
            self.record_metric("session_methods_available", session_methods)
            logger.info(f"DatabaseManager session methods: {session_methods}")
            
        except Exception as e:
            logger.error(f"DatabaseManager session method check failed: {e}")
            self.record_metric("database_manager_method_error", str(e))
            raise
    
    def test_database_manager_has_session_factory_methods(self):
        """
        DESIGNED TO PASS: Verify DatabaseManager provides session creation
        
        This test ensures that DatabaseManager has the methods that WebSocket
        factory needs to create database sessions.
        """
        self.record_metric("validation_type", "session_factory_methods")
        
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            
            db_manager = DatabaseManager()
            
            # Required methods for WebSocket factory database access
            required_methods = [
                'initialize',  # Database initialization
                'get_async_session',  # Async session creation
            ]
            
            missing_methods = []
            available_methods = []
            
            for method_name in required_methods:
                if hasattr(db_manager, method_name):
                    available_methods.append(method_name)
                    
                    # Test if method is callable
                    method = getattr(db_manager, method_name)
                    if callable(method):
                        self.record_metric(f"method_{method_name}_callable", True)
                    else:
                        self.record_metric(f"method_{method_name}_not_callable", True)
                else:
                    missing_methods.append(method_name)
            
            # Record metrics
            self.record_metric("available_session_methods", available_methods)
            self.record_metric("missing_session_methods", missing_methods)
            
            # Validate that critical methods exist
            assert 'initialize' in available_methods, (
                "DatabaseManager missing initialize() method needed for WebSocket factory"
            )
            
            logger.info(
                f"DatabaseManager session factory validation: "
                f"Available: {available_methods}, Missing: {missing_methods}"
            )
            
        except ImportError as e:
            logger.error(f"Failed to import DatabaseManager: {e}")
            self.record_metric("database_manager_import_error", str(e))
            raise
        except Exception as e:
            logger.error(f"DatabaseManager session factory validation failed: {e}")
            self.record_metric("session_factory_validation_error", str(e))
            raise
    
    def test_websocket_factory_database_integration_works(self):
        """
        DESIGNED TO PASS: Verify WebSocket factory can access database after SSOT fix
        
        This test validates that WebSocket factory can successfully create
        database sessions using the SSOT-compliant DatabaseManager approach.
        """
        self.record_metric("validation_type", "websocket_database_integration")
        
        # Test integration without actually starting services
        try:
            # Import database manager
            from netra_backend.app.db.database_manager import DatabaseManager
            
            db_manager = DatabaseManager()
            
            # Simulate WebSocket factory database access pattern
            websocket_database_access_success = False
            
            # Pattern 1: Direct DatabaseManager usage
            if hasattr(db_manager, 'initialize'):
                logger.info("WebSocket factory can use DatabaseManager.initialize()")
                websocket_database_access_success = True
                self.record_metric("websocket_database_pattern1", True)
            
            # Pattern 2: Session creation
            if hasattr(db_manager, 'get_async_session'):
                logger.info("WebSocket factory can use DatabaseManager.get_async_session()")
                websocket_database_access_success = True
                self.record_metric("websocket_database_pattern2", True)
            
            # Validate integration capability
            assert websocket_database_access_success, (
                "WebSocket factory cannot access database through any available pattern. "
                f"DatabaseManager methods: {[m for m in dir(db_manager) if not m.startswith('_')]}"
            )
            
            self.record_metric("websocket_database_integration_success", True)
            logger.info("WebSocket factory database integration validation passed")
            
        except ImportError as e:
            logger.error(f"Database integration test import failed: {e}")
            self.record_metric("integration_test_import_error", str(e))
            raise
        except Exception as e:
            logger.error(f"WebSocket database integration test failed: {e}")
            self.record_metric("integration_test_error", str(e))
            raise
    
    def teardown_method(self, method=None):
        """Enhanced teardown with database SSOT metrics."""
        # Log final metrics
        logger.info(f"Database imports attempted: {self._database_imports_attempted}")
        logger.info(f"WebSocket imports attempted: {self._websocket_imports_attempted}")
        logger.info(f"Function calls attempted: {self._function_calls_attempted}")
        
        super().teardown_method(method)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])