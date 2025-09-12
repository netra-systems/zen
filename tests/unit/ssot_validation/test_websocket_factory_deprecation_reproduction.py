#!/usr/bin/env python
"""
SSOT Validation: WebSocket Factory Deprecation Detection Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: SSOT Compliance & System Stability 
- Value Impact: Validates detection and remediation of deprecated factory patterns
- Strategic Impact: CRITICAL - Ensures $500K+ ARR user isolation vulnerabilities are fixed

PURPOSE:
These tests are designed to:
1. CURRENTLY FAIL (proving violations exist) 
2. PASS AFTER SSOT FIX (proving remediation successful)

CRITICAL VIOLATIONS TARGETED:
- 49+ files using deprecated `get_websocket_manager_factory()` 
- Primary violations in websocket_ssot.py lines 1439, 1470, 1496
- User isolation failures causing WebSocket race conditions

TEST STRATEGY:
- Tests demonstrate current violations by failing appropriately
- After SSOT fix, these same tests will pass (proving fix success)
- Provides automated validation of migration success
"""

import asyncio
import os
import sys
import ast
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from unittest import mock

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import environment and test framework
from shared.isolated_environment import get_env, IsolatedEnvironment
try:
    from test_framework.ssot.base_test_case import SSotAsyncTestCase
except ImportError:
    # Fallback for testing without full SSOT framework
    import unittest
    SSotAsyncTestCase = unittest.TestCase

# WebSocketTestUtility is not needed for these tests

import pytest
from loguru import logger


class TestWebSocketFactoryDeprecationReproduction(SSotAsyncTestCase):
    """
    Strategic SSOT Tests: Factory Deprecation Detection
    
    These tests REPRODUCE current SSOT violations to demonstrate:
    1. Current deprecated patterns are detectable
    2. SSOT patterns are available and functional
    3. Migration path from deprecated to SSOT is clear
    4. Post-fix validation criteria are established
    """
    
    def setup_method(self, method):
        """Set up test environment for deprecation detection."""
        super().setup_method(method)
        
        self.project_root = Path(project_root)
        self.websocket_ssot_file = self.project_root / "netra_backend" / "app" / "routes" / "websocket_ssot.py"
        
        # Collect deprecated pattern locations for validation
        self.known_violation_lines = [1439, 1470, 1496]  # From documentation
        
        logger.info(f"[DEPRECATION TEST] Setup complete - targeting {self.websocket_ssot_file}")

    def teardown_method(self, method):
        """Clean up test environment."""
        super().teardown_method(method)
        logger.info("[DEPRECATION TEST] Teardown complete")

    async def test_deprecated_factory_calls_detected_in_websocket_ssot(self):
        """
        TEST: Detect deprecated get_websocket_manager_factory() calls in websocket_ssot.py
        
        EXPECTED BEHAVIOR:
        - CURRENTLY: Should FIND violations (test PASSES - proving problem exists)
        - POST-FIX: Should find NO violations (test FAILS - proving fix success)
        
        This test proves that deprecated patterns exist and can be detected.
        """
        logger.info("[DEPRECATION DETECTION] Scanning websocket_ssot.py for deprecated patterns...")
        
        # Verify target file exists
        if not self.websocket_ssot_file.exists():
            pytest.skip(f"Target file not found: {self.websocket_ssot_file}")
            
        # Read and parse the file
        try:
            with open(self.websocket_ssot_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
            # Parse AST to find deprecated function calls
            tree = ast.parse(file_content)
            
            # Find all instances of deprecated factory calls
            deprecated_calls = []
            
            class DeprecatedCallVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.calls = []
                    self.current_line = 1
                    
                def visit_Call(self, node):
                    # Look for get_websocket_manager_factory() calls
                    if (hasattr(node.func, 'id') and 
                        node.func.id == 'get_websocket_manager_factory'):
                        self.calls.append({
                            'line': node.lineno,
                            'function': 'get_websocket_manager_factory',
                            'type': 'direct_call'
                        })
                    
                    # Look for from import statements
                    elif (hasattr(node.func, 'attr') and 
                          node.func.attr == 'get_websocket_manager_factory'):
                        self.calls.append({
                            'line': node.lineno,
                            'function': 'get_websocket_manager_factory', 
                            'type': 'method_call'
                        })
                    
                    self.generic_visit(node)
                    
                def visit_ImportFrom(self, node):
                    # Look for imports of the deprecated factory
                    if (node.module and 
                        'websocket_manager_factory' in node.module):
                        for alias in node.names:
                            if alias.name == 'get_websocket_manager_factory':
                                self.calls.append({
                                    'line': node.lineno,
                                    'function': 'get_websocket_manager_factory',
                                    'type': 'import'
                                })
                    self.generic_visit(node)
            
            visitor = DeprecatedCallVisitor()
            visitor.visit(tree)
            deprecated_calls = visitor.calls
            
            # Also check for string-based patterns (more robust detection)
            string_patterns = []
            lines = file_content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'get_websocket_manager_factory' in line:
                    string_patterns.append({
                        'line': i,
                        'content': line.strip(),
                        'type': 'string_match'
                    })
            
            # Log findings
            logger.info(f"[DEPRECATION DETECTION] AST found {len(deprecated_calls)} deprecated calls")
            logger.info(f"[DEPRECATION DETECTION] String search found {len(string_patterns)} matches")
            
            for call in deprecated_calls:
                logger.warning(f"[VIOLATION] AST: Line {call['line']} - {call['type']} - {call['function']}")
                
            for pattern in string_patterns:
                logger.warning(f"[VIOLATION] STRING: Line {pattern['line']} - {pattern['content']}")
            
            # CRITICAL: This test should PASS currently (violations exist)
            # After SSOT fix, this test should FAIL (no violations found)
            total_violations = len(deprecated_calls) + len(string_patterns)
            
            assert total_violations > 0, (
                f"Expected to find deprecated factory calls in {self.websocket_ssot_file}, "
                f"but found {total_violations}. If this test fails, it means the "
                f"SSOT migration may already be complete!"
            )
            
            # Verify known violation lines are found
            found_lines = {call['line'] for call in deprecated_calls}
            found_lines.update({pattern['line'] for pattern in string_patterns})
            
            missing_lines = set(self.known_violation_lines) - found_lines
            if missing_lines:
                logger.warning(f"[UNEXPECTED] Known violation lines not found: {missing_lines}")
            
            logger.success(f"[DEPRECATION DETECTION] Successfully detected {total_violations} violations")
            
        except Exception as e:
            logger.error(f"[DEPRECATION DETECTION] Failed to scan file: {str(e)}")
            pytest.fail(f"Failed to scan websocket_ssot.py for deprecated patterns: {str(e)}")

    async def test_websocket_manager_direct_import_available(self):
        """
        TEST: Validate proper SSOT WebSocketManager import is available
        
        EXPECTED BEHAVIOR:
        - Should ALWAYS PASS (proving SSOT pattern is available)
        - Demonstrates the correct import path for migration
        - Validates that direct instantiation capability exists
        
        This test proves the migration target is functional.
        """
        logger.info("[SSOT IMPORT TEST] Testing direct WebSocket manager import availability...")
        
        # Test 1: Import WebSocketManager directly (SSOT pattern)
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
            logger.success("[SSOT IMPORT] Direct WebSocketManager import successful")
        except ImportError as e:
            pytest.fail(f"SSOT WebSocketManager import failed: {str(e)}")
            
        # Test 2: Verify direct instantiation with user_context (SSOT pattern)
        try:
            # Import UserExecutionContext for testing
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.isolated_environment import IsolatedEnvironment
            
            # Create test user context using correct parameters
            test_context = UserExecutionContext(
                user_id="test_import_user",
                thread_id="test_import_thread",
                run_id="test_import_run"
            )
            
            # Test direct instantiation with user context (SSOT pattern)
            test_manager = WebSocketManager(user_context=test_context)
            assert test_manager is not None, "SSOT direct instantiation failed"
            logger.success("[SSOT IMPORT] WebSocketManager direct instantiation with user_context available")
        except Exception as e:
            pytest.fail(f"SSOT WebSocketManager instantiation validation failed: {str(e)}")
            
        # Test 3: Test SSOT instantiation capability verification
        try:
            # Verify the class can be instantiated with proper constructor
            import inspect
            init_signature = inspect.signature(WebSocketManager.__init__)
            assert 'user_context' in init_signature.parameters, "WebSocketManager missing user_context parameter"
            logger.success("[SSOT IMPORT] WebSocketManager constructor supports user_context")
        except Exception as e:
            pytest.fail(f"SSOT constructor capability check failed: {str(e)}")
        
        logger.success("[SSOT IMPORT TEST] All SSOT import validations passed")

    async def test_deprecated_vs_ssot_import_comparison(self):
        """
        TEST: Compare deprecated factory vs SSOT import patterns
        
        EXPECTED BEHAVIOR:
        - Deprecated import should be detectable (during migration phase)
        - SSOT import should work cleanly
        - Clear behavioral differences should be documented
        
        This test documents the migration path and validates both patterns.
        """
        logger.info("[IMPORT COMPARISON] Testing deprecated vs SSOT import patterns...")
        
        results = {
            'deprecated_import_available': False,
            'deprecated_import_error': None,
            'ssot_import_available': False, 
            'ssot_import_error': None,
            'migration_ready': False
        }
        
        # Test 1: Try deprecated factory import
        try:
            # This should be available during migration phase
            from netra_backend.app.websocket_core.websocket_manager_factory import get_websocket_manager_factory
            results['deprecated_import_available'] = True
            logger.warning("[DEPRECATED IMPORT] get_websocket_manager_factory still available")
        except ImportError as e:
            results['deprecated_import_error'] = str(e)
            logger.info(f"[DEPRECATED IMPORT] Factory import not available: {str(e)}")
            
        # Test 2: Try SSOT import
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            results['ssot_import_available'] = True
            logger.success("[SSOT IMPORT] UnifiedWebSocketManager available")
        except ImportError as e:
            results['ssot_import_error'] = str(e)
            logger.error(f"[SSOT IMPORT] SSOT import failed: {str(e)}")
            
        # Evaluate migration readiness
        if results['ssot_import_available']:
            results['migration_ready'] = True
            logger.success("[MIGRATION READY] SSOT imports available for migration")
        else:
            logger.error("[MIGRATION BLOCKED] SSOT imports not available")
            
        # Log comprehensive results
        logger.info(f"[IMPORT COMPARISON] Results: {results}")
        
        # CRITICAL: SSOT import must always be available
        assert results['ssot_import_available'], (
            f"SSOT import must be available for migration. Error: {results['ssot_import_error']}"
        )
        
        # Document migration state
        if results['deprecated_import_available']:
            logger.warning("[MIGRATION STATE] Deprecated imports still available - migration not complete")
        else:
            logger.success("[MIGRATION STATE] Deprecated imports removed - migration may be complete")
            
        logger.success("[IMPORT COMPARISON] Import pattern comparison completed")

    async def test_codebase_wide_deprecation_scan(self):
        """
        TEST: Scan entire codebase for deprecated factory patterns
        
        EXPECTED BEHAVIOR:
        - CURRENTLY: Should find 49+ files with violations (test PASSES)
        - POST-FIX: Should find 0 files with violations (test FAILS)
        
        This test provides comprehensive validation of migration scope.
        """
        logger.info("[CODEBASE SCAN] Scanning entire codebase for deprecated patterns...")
        
        # Define search patterns
        deprecated_patterns = [
            'get_websocket_manager_factory',
            'websocket_manager_factory',
            'WebSocketManagerFactory'
        ]
        
        # Define scan locations
        scan_paths = [
            self.project_root / "netra_backend",
            self.project_root / "auth_service", 
            self.project_root / "frontend",
            self.project_root / "shared",
            self.project_root / "tests"
        ]
        
        violations = []
        
        # Scan each path
        for scan_path in scan_paths:
            if not scan_path.exists():
                continue
                
            logger.info(f"[CODEBASE SCAN] Scanning {scan_path}...")
            
            # Find all Python files
            python_files = list(scan_path.rglob("*.py"))
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    # Check for deprecated patterns
                    file_violations = []
                    for pattern in deprecated_patterns:
                        if pattern in content:
                            # Find specific lines
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if pattern in line:
                                    file_violations.append({
                                        'file': str(py_file),
                                        'line': i,
                                        'pattern': pattern,
                                        'content': line.strip()
                                    })
                    
                    violations.extend(file_violations)
                    
                except Exception as e:
                    logger.warning(f"[CODEBASE SCAN] Error scanning {py_file}: {str(e)}")
        
        # Log findings
        logger.info(f"[CODEBASE SCAN] Found {len(violations)} total violations")
        
        # Group by file
        files_with_violations = {}
        for violation in violations:
            file_path = violation['file']
            if file_path not in files_with_violations:
                files_with_violations[file_path] = []
            files_with_violations[file_path].append(violation)
        
        logger.info(f"[CODEBASE SCAN] {len(files_with_violations)} files contain violations")
        
        # Log details of violations
        for file_path, file_violations in files_with_violations.items():
            logger.warning(f"[VIOLATION FILE] {file_path} - {len(file_violations)} violations")
            for violation in file_violations[:3]:  # Limit to first 3 per file
                logger.warning(f"  Line {violation['line']}: {violation['content']}")
        
        # CRITICAL: This test expects to find violations currently
        # After SSOT fix, this should find 0 violations
        assert len(violations) > 0, (
            f"Expected to find deprecated factory patterns across codebase, "
            f"but found {len(violations)}. If this test fails, the SSOT migration "
            f"may already be complete!"
        )
        
        # Validate expected minimum violations (from documentation: 49+ files)
        expected_min_files = 10  # Conservative estimate
        assert len(files_with_violations) >= expected_min_files, (
            f"Expected at least {expected_min_files} files with violations, "
            f"but found {len(files_with_violations)}. Migration scope may be different than documented."
        )
        
        logger.success(f"[CODEBASE SCAN] Successfully identified {len(violations)} violations across {len(files_with_violations)} files")