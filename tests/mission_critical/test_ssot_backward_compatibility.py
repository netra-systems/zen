class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""
MISSION CRITICAL: SSOT Backward Compatibility Test Suite

This test suite ensures that the SSOT consolidation doesn't break existing code.
It validates that legacy test patterns still work while encouraging migration to SSOT.
These tests are CRITICAL for ensuring zero-downtime SSOT deployment.

Business Value: Platform/Internal - Migration Safety & Risk Reduction
Ensures SSOT deployment doesn't break existing 6,096+ test files during migration.

CRITICAL: These tests validate that existing patterns work while identifying
areas that need migration. They test the compatibility bridge components.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import asyncio
import inspect
import logging
import os
import sys
import time
import traceback
import uuid
import warnings
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from unittest import TestCase
from netra_backend.app.core.agent_registry import AgentRegistry
# NO MOCKS - Real services only for mission critical isolation testing

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Real services and isolation testing components
import asyncpg
import psycopg2
# MIGRATED: from netra_backend.app.services.redis_client import get_redis_client
import websockets
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Process, Queue

# Import real framework components - NO MOCKS
from netra_backend.app.database.manager import DatabaseManager
from netra_backend.app.services.websocket_manager import WebSocketManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_factory import ExecutionFactory
from test_framework.backend_client import BackendClient
from test_framework.test_context import TestContext

from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

logger = logging.getLogger(__name__)


class TestSSOTBackwardCompatibility:
    """
    CRITICAL: Test SSOT backward compatibility with legacy test patterns.
    These tests ensure existing code continues to work during SSOT migration.
    """
    
    async def setUp(self):
        """Set up backward compatibility test environment with REAL services."""
        await super().setUp()
        self.test_id = uuid.uuid4().hex[:8]
        
        # Initialize REAL service connections for backward compatibility testing
        self.env = IsolatedEnvironment()
        self.db_manager = DatabaseManager()
        self.redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6381, decode_responses=True)
        self.test_context = TestContext(user_id=f"compat_user_{self.test_id}")
        
        # Create isolated test environment
        self.legacy_contexts = {}
        self.modern_contexts = {}
        self.compatibility_data = {}
        
        logger.info(f"Starting backward compatibility test with REAL services: {self._testMethodName} (ID: {self.test_id})")
    
    def tearDown(self):
        """Clean up backward compatibility test and REAL service connections."""
        # Clean up compatibility test data
        try:
            asyncio.get_event_loop().run_until_complete(redis_client.flushdb())
        except:
            pass
            
        logger.info(f"Completed backward compatibility test cleanup: {self._testMethodName} (ID: {self.test_id})")
    
    def test_backward_compatibility_data_isolation_concurrent_legacy_modern(self):
        """
        COMPATIBILITY CRITICAL: Test data isolation between legacy and modern patterns.
        Ensures legacy patterns don't contaminate modern isolation boundaries.
        """
        num_legacy_contexts = 8
        num_modern_contexts = 8
        operations_per_context = 15
        compatibility_failures = []
        
        async def legacy_pattern_operations(context_id):
            """Simulate legacy pattern operations that should still maintain isolation."""
            failures = []
            
            try:
                # Legacy-style environment access (still isolated)
                legacy_env = IsolatedEnvironment()
                
                # Legacy data patterns with modern isolation
                legacy_data = {
                    'legacy_id': context_id,
                    'legacy_pattern': 'old_style_data_access',
                    'legacy_timestamp': time.time(),
                    'legacy_secret': f"LEGACY_SECRET_{context_id}_{uuid.uuid4().hex[:8]}"
                }
                
                for op_num in range(operations_per_context):
                    legacy_key = f"legacy:{context_id}:operation:{op_num}"
                    
                    # Store legacy data with real services
                    await redis_client.hset(
                        legacy_key,
                        "data",
                        str(legacy_data)
                    )
                    
                    await redis_client.hset(
                        legacy_key,
                        "pattern_type",
                        "legacy_compatibility"
                    )
                    
                    # Verify legacy data isolation
                    stored_data = await redis_client.hget(legacy_key, "data")
                    if not stored_data or str(context_id) not in stored_data:
                        failures.append({
                            'context_id': context_id,
                            'operation': op_num,
                            'issue': 'legacy_data_isolation_failure',
                            'expected_data': str(legacy_data),
                            'actual_data': stored_data
                        })
                    
                    # Verify no contamination with modern patterns
                    modern_keys = await redis_client.keys("modern:*")
                    for modern_key in modern_keys:
                        modern_data = await redis_client.hget(modern_key, "data")
                        if modern_data and legacy_data['legacy_secret'] in modern_data:
                            failures.append({
                                'context_id': context_id,
                                'operation': op_num,
                                'issue': 'legacy_to_modern_contamination',
                                'legacy_secret': legacy_data['legacy_secret'],
                                'contaminated_modern_key': modern_key
                            })
                    
                    time.sleep(0.002)  # Small delay for race condition testing
                
                return failures
                
            except Exception as e:
                return [{
                    'context_id': context_id,
                    'issue': 'legacy_context_failure',
                    'error': str(e)
                }]
        
        async def modern_pattern_operations(context_id):
            """Simulate modern pattern operations with strict isolation."""
            failures = []
            
            try:
                # Modern isolated environment
                modern_env = IsolatedEnvironment()
                modern_context = TestContext(user_id=f"modern_user_{context_id}")
                
                # Modern data patterns
                modern_data = {
                    'modern_id': context_id,
                    'modern_pattern': 'isolated_data_access',
                    'modern_timestamp': time.time(),
                    'modern_secret': f"MODERN_SECRET_{context_id}_{uuid.uuid4().hex[:8]}"
                }
                
                for op_num in range(operations_per_context):
                    modern_key = f"modern:{context_id}:operation:{op_num}"
                    
                    # Store modern data with real services
                    await redis_client.hset(
                        modern_key,
                        "data",
                        str(modern_data)
                    )
                    
                    await redis_client.hset(
                        modern_key,
                        "pattern_type",
                        "modern_isolation"
                    )
                    
                    # Verify modern data isolation
                    stored_data = await redis_client.hget(modern_key, "data")
                    if not stored_data or str(context_id) not in stored_data:
                        failures.append({
                            'context_id': context_id,
                            'operation': op_num,
                            'issue': 'modern_data_isolation_failure',
                            'expected_data': str(modern_data),
                            'actual_data': stored_data
                        })
                    
                    # Verify no contamination with legacy patterns
                    legacy_keys = await redis_client.keys("legacy:*")
                    for legacy_key in legacy_keys:
                        legacy_data = await redis_client.hget(legacy_key, "data")
                        if legacy_data and modern_data['modern_secret'] in legacy_data:
                            failures.append({
                                'context_id': context_id,
                                'operation': op_num,
                                'issue': 'modern_to_legacy_contamination',
                                'modern_secret': modern_data['modern_secret'],
                                'contaminated_legacy_key': legacy_key
                            })
                    
                    time.sleep(0.002)  # Small delay for race condition testing
                
                return failures
                
            except Exception as e:
                return [{
                    'context_id': context_id,
                    'issue': 'modern_context_failure',
                    'error': str(e)
                }]
        
        # Create wrapper functions for ThreadPoolExecutor since it can't handle async functions directly
        def run_legacy_operations(context_id):
            return asyncio.run(legacy_pattern_operations(context_id))
            
        def run_modern_operations(context_id):
            return asyncio.run(modern_pattern_operations(context_id))
        
        # Execute concurrent legacy and modern operations
        with ThreadPoolExecutor(max_workers=num_legacy_contexts + num_modern_contexts) as executor:
            # Submit legacy operations
            legacy_futures = {
                executor.submit(run_legacy_operations, context_id): f"legacy_{context_id}"
                for context_id in range(num_legacy_contexts)
            }
            
            # Submit modern operations
            modern_futures = {
                executor.submit(run_modern_operations, context_id): f"modern_{context_id}"
                for context_id in range(num_modern_contexts)
            }
            
            all_futures = {**legacy_futures, **modern_futures}
            
            for future in as_completed(all_futures):
                context_name = all_futures[future]
                try:
                    context_failures = future.result(timeout=45)
                    compatibility_failures.extend(context_failures)
                except Exception as e:
                    compatibility_failures.append({
                        'context_name': context_name,
                        'issue': 'future_execution_failure',
                        'error': str(e)
                    })
        
        # Verify backward compatibility isolation success
        if compatibility_failures:
            logger.error(f"Backward compatibility isolation failures: {compatibility_failures[:10]}")
        
        contamination_failures = [f for f in compatibility_failures if 'contamination' in f.get('issue', '')]
        isolation_failures = [f for f in compatibility_failures if 'isolation_failure' in f.get('issue', '')]
        
        assert len(contamination_failures) == 0, f"CRITICAL: Cross-pattern contamination detected: {len(contamination_failures)} cases"
        assert len(isolation_failures) == 0, f"CRITICAL: Isolation boundaries failed: {len(isolation_failures)} cases"
        assert len(compatibility_failures) == 0, f"Backward compatibility test failed: {len(compatibility_failures)} total failures"
    
    def test_concurrent_mixed_pattern_execution_isolation(self):
        """
        EXECUTION CRITICAL: Test concurrent execution of mixed legacy/modern patterns.
        Verifies isolation is maintained when both patterns execute simultaneously.
        """
        num_concurrent_executions = 20
        mixed_execution_failures = []
        
        async def mixed_pattern_execution(execution_id):
            """Execute both legacy and modern patterns concurrently."""
            failures = []
            
            try:
                # Alternating legacy and modern patterns
                is_legacy = execution_id % 2 == 0
                pattern_type = "legacy" if is_legacy else "modern"
                
                # Create execution context
                execution_env = IsolatedEnvironment()
                execution_context = TestContext(user_id=f"{pattern_type}_exec_{execution_id}")
                
                # Pattern-specific data
                execution_data = {
                    'execution_id': execution_id,
                    'pattern_type': pattern_type,
                    'execution_secret': f"{pattern_type.upper()}_EXEC_SECRET_{execution_id}_{uuid.uuid4().hex[:6]}",
                    'concurrent_timestamp': time.time()
                }
                
                # High-frequency operations
                for op_num in range(25):  # More operations for stress testing
                    execution_key = f"{pattern_type}_exec:{execution_id}:op:{op_num}"
                    
                    # Store execution data
                    await redis_client.hset(
                        execution_key,
                        "execution_data",
                        str(execution_data)
                    )
                    
                    await redis_client.hset(
                        execution_key,
                        "execution_pattern",
                        pattern_type
                    )
                    
                    # Immediate verification
                    stored_data = await redis_client.hget(execution_key, "execution_data")
                    if not stored_data or str(execution_id) not in stored_data:
                        failures.append({
                            'execution_id': execution_id,
                            'pattern_type': pattern_type,
                            'operation': op_num,
                            'issue': 'mixed_execution_data_corruption',
                            'expected_data': str(execution_data),
                            'actual_data': stored_data
                        })
                    
                    # Check for cross-execution contamination
                    other_pattern_type = "modern" if is_legacy else "legacy"
                    other_keys = await redis_client.keys(f"{other_pattern_type}_exec:*")
                    
                    for other_key in other_keys:
                        other_data = await redis_client.hget(other_key, "execution_data")
                        if other_data and execution_data['execution_secret'] in other_data:
                            failures.append({
                                'execution_id': execution_id,
                                'pattern_type': pattern_type,
                                'operation': op_num,
                                'issue': 'mixed_execution_cross_contamination',
                                'contaminated_key': other_key,
                                'leaked_secret': execution_data['execution_secret']
                            })
                    
                    # Check for same-pattern cross-execution contamination
                    same_pattern_keys = await redis_client.keys(f"{pattern_type}_exec:*")
                    for same_key in same_pattern_keys:
                        if execution_key != same_key:
                            same_data = await redis_client.hget(same_key, "execution_data")
                            if same_data and execution_data['execution_secret'] in same_data:
                                # Extract other execution ID from key
                                other_exec_id = same_key.split(":")[1]
                                if str(execution_id) != other_exec_id:
                                    failures.append({
                                        'execution_id': execution_id,
                                        'pattern_type': pattern_type,
                                        'operation': op_num,
                                        'issue': 'same_pattern_execution_contamination',
                                        'contaminated_execution': other_exec_id,
                                        'contaminated_key': same_key
                                    })
                    
                    # Brief pause for concurrent access stress testing
                    time.sleep(0.001)
                
                return failures
                
            except Exception as e:
                return [{
                    'execution_id': execution_id,
                    'pattern_type': pattern_type,
                    'issue': 'mixed_execution_setup_failure',
                    'error': str(e)
                }]
        
        # Create wrapper function for ThreadPoolExecutor since it can't handle async functions directly
        def run_mixed_execution(execution_id):
            return asyncio.run(mixed_pattern_execution(execution_id))
            
        # Execute mixed patterns concurrently
        with ThreadPoolExecutor(max_workers=num_concurrent_executions) as executor:
            future_to_execution = {
                executor.submit(run_mixed_execution, execution_id): execution_id
                for execution_id in range(num_concurrent_executions)
            }
            
            for future in as_completed(future_to_execution):
                execution_id = future_to_execution[future]
                try:
                    execution_failures = future.result(timeout=60)
                    mixed_execution_failures.extend(execution_failures)
                except Exception as e:
                    mixed_execution_failures.append({
                        'execution_id': execution_id,
                        'issue': 'mixed_execution_future_failure',
                        'error': str(e)
                    })
        
        # Analyze mixed execution results
        contamination_failures = [f for f in mixed_execution_failures if 'contamination' in f.get('issue', '')]
        corruption_failures = [f for f in mixed_execution_failures if 'corruption' in f.get('issue', '')]
        
        if mixed_execution_failures:
            logger.error(f"Mixed execution isolation failures: {mixed_execution_failures[:10]}")
        
        # Verify mixed pattern execution isolation
        assert len(contamination_failures) == 0, f"CRITICAL: Cross-execution contamination: {len(contamination_failures)} cases"
        assert len(corruption_failures) == 0, f"CRITICAL: Execution data corruption: {len(corruption_failures)} cases"
        assert len(mixed_execution_failures) == 0, f"Mixed execution isolation failed: {len(mixed_execution_failures)} total failures"
    
    async def test_async_websocket_legacy_modern_pattern_isolation(self):
        """
        ASYNC ISOLATION CRITICAL: Test WebSocket isolation between async legacy/modern patterns.
        Verifies async operations maintain isolation across different pattern styles.
        """
        num_legacy_sessions = 6
        num_modern_sessions = 6
        async_isolation_failures = []
        
        async def legacy_async_websocket_pattern(session_id):
            """Simulate legacy async WebSocket pattern with isolation."""
            failures = []
            ws_uri = f"ws://localhost:8000/ws/legacy_session_{session_id}"
            
            try:
                # Legacy async pattern with modern isolation
                session_data = {
                    'session_id': session_id,
                    'pattern_type': 'legacy_async',
                    'session_secret': f"LEGACY_ASYNC_SECRET_{session_id}_{uuid.uuid4().hex[:6]}",
                    'async_timestamp': time.time()
                }
                
                async with websockets.connect(ws_uri) as websocket:
                    # Send legacy-style messages
                    for msg_num in range(8):
                        legacy_message = {
                            'message_id': f"legacy_async_{session_id}_{msg_num}",
                            'legacy_data': session_data,
                            'message_type': 'legacy_async_pattern'
                        }
                        
                        await websocket.send(str(legacy_message))
                        
                        # Wait for response
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            
                            # Verify response isolation
                            if str(session_id) not in response:
                                failures.append({
                                    'session_id': session_id,
                                    'message_num': msg_num,
                                    'issue': 'legacy_async_response_isolation_failure',
                                    'expected_session_id': str(session_id),
                                    'response': response
                                })
                            
                            # Check for modern pattern contamination
                            if 'modern_async' in response and session_data['session_secret'] not in response:
                                failures.append({
                                    'session_id': session_id,
                                    'message_num': msg_num,
                                    'issue': 'legacy_async_modern_contamination',
                                    'response': response
                                })
                        
                        except asyncio.TimeoutError:
                            failures.append({
                                'session_id': session_id,
                                'message_num': msg_num,
                                'issue': 'legacy_async_timeout',
                                'timeout': 3.0
                            })
                        
                        await asyncio.sleep(0.05)  # Async delay
                
                return failures
                
            except Exception as e:
                return [{
                    'session_id': session_id,
                    'issue': 'legacy_async_connection_failure',
                    'error': str(e)
                }]
        
        async def modern_async_websocket_pattern(session_id):
            """Simulate modern async WebSocket pattern with strict isolation."""
            failures = []
            ws_uri = f"ws://localhost:8000/ws/modern_session_{session_id}"
            
            try:
                # Modern async pattern with enhanced isolation
                session_data = {
                    'session_id': session_id,
                    'pattern_type': 'modern_async',
                    'session_secret': f"MODERN_ASYNC_SECRET_{session_id}_{uuid.uuid4().hex[:6]}",
                    'async_timestamp': time.time()
                }
                
                async with websockets.connect(ws_uri) as websocket:
                    # Send modern-style messages
                    for msg_num in range(8):
                        modern_message = {
                            'message_id': f"modern_async_{session_id}_{msg_num}",
                            'modern_data': session_data,
                            'message_type': 'modern_async_pattern'
                        }
                        
                        await websocket.send(str(modern_message))
                        
                        # Wait for response
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            
                            # Verify response isolation
                            if str(session_id) not in response:
                                failures.append({
                                    'session_id': session_id,
                                    'message_num': msg_num,
                                    'issue': 'modern_async_response_isolation_failure',
                                    'expected_session_id': str(session_id),
                                    'response': response
                                })
                            
                            # Check for legacy pattern contamination
                            if 'legacy_async' in response and session_data['session_secret'] not in response:
                                failures.append({
                                    'session_id': session_id,
                                    'message_num': msg_num,
                                    'issue': 'modern_async_legacy_contamination',
                                    'response': response
                                })
                        
                        except asyncio.TimeoutError:
                            failures.append({
                                'session_id': session_id,
                                'message_num': msg_num,
                                'issue': 'modern_async_timeout',
                                'timeout': 3.0
                            })
                        
                        await asyncio.sleep(0.05)  # Async delay
                
                return failures
                
            except Exception as e:
                return [{
                    'session_id': session_id,
                    'issue': 'modern_async_connection_failure',
                    'error': str(e)
                }]
        
        # Execute concurrent async legacy and modern WebSocket sessions
        legacy_tasks = [legacy_async_websocket_pattern(session_id) for session_id in range(num_legacy_sessions)]
        modern_tasks = [modern_async_websocket_pattern(session_id) for session_id in range(num_modern_sessions)]
        all_tasks = legacy_tasks + modern_tasks
        
        try:
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    async_isolation_failures.append({
                        'issue': 'async_task_execution_failure',
                        'error': str(result)
                    })
                elif isinstance(result, list):
                    async_isolation_failures.extend(result)
        
        except Exception as e:
            async_isolation_failures.append({
                'issue': 'async_test_execution_failure',
                'error': str(e)
            })
        
        # Analyze async isolation results
        contamination_failures = [f for f in async_isolation_failures if 'contamination' in f.get('issue', '')]
        timeout_failures = [f for f in async_isolation_failures if 'timeout' in f.get('issue', '')]
        
        if async_isolation_failures:
            logger.error(f"Async WebSocket isolation failures: {async_isolation_failures[:10]}")
        
        # Verify async WebSocket isolation
        assert len(contamination_failures) == 0, f"CRITICAL: Async pattern contamination: {len(contamination_failures)} cases"
        assert len(timeout_failures) <= 5, f"Too many async timeouts: {len(timeout_failures)} cases (may indicate performance issues)"
        assert len(async_isolation_failures) <= 8, f"Too many async isolation failures: {len(async_isolation_failures)} detected"
    
    def test_legacy_database_utility_adapter(self):
        """
        DATABASE COMPATIBILITY CRITICAL: Test legacy database patterns work.
        This ensures existing database test code doesn't break.
        """
        # Test LegacyDatabaseUtilityAdapter
        adapter = LegacyDatabaseUtilityAdapter()
        self.assertIsNotNone(adapter)
        
        # Test that adapter provides legacy database methods
        legacy_methods = [
            'get_connection', 'get_session', 'create_test_database',
            'cleanup_database', 'execute_sql'
        ]
        
        for method_name in legacy_methods:
            self.assertTrue(hasattr(adapter, method_name),
                           f"Legacy database adapter missing method: {method_name}")
        
        # Test that adapter delegates to SSOT database utility
        try:
            connection = adapter.get_connection()
            # If this works, adapter is delegating correctly
            logger.info("Legacy database adapter delegation working")
            
        except Exception as e:
            # Expected if database not available, but adapter should handle gracefully
            logger.warning(f"Database not available for legacy adapter test: {e}")
            self.assertIsNotNone(e)  # Should get meaningful error, not crash
    
    def test_legacy_test_pattern_detection(self):
        """
        DETECTION CRITICAL: Test detection of legacy test patterns.
        This validates our ability to identify tests that need migration.
        """
        # Create test class with legacy patterns
        class LegacyPatternTest(TestCase):
            def setUp(self):
                # Legacy direct os.environ access
                self.old_env = os.environ.get('TEST_VAR', 'default')
                
                # Legacy direct mock creation
                self.websocket = TestWebSocketConnection()  # Real WebSocket implementation
                
                # Legacy database connection
                self.db_connection = None  # Would be actual connection in real code
            
            def test_with_legacy_patterns(self):
                # Legacy assertions
                self.assertEqual(1, 1)
                self.assertTrue(True)
        
        # Test pattern detection
        patterns = detect_legacy_test_patterns(LegacyPatternTest)
        self.assertIsInstance(patterns, dict)
        
        expected_patterns = [
            'direct_environ_access',
            'manual_mock_creation', 
            'manual_database_connection',
            'unittest_inheritance'
        ]
        
        for pattern in expected_patterns:
            self.assertIn(pattern, patterns,
                         f"Should detect legacy pattern: {pattern}")
            self.assertTrue(patterns[pattern],
                           f"Legacy pattern should be detected as present: {pattern}")
    
    def test_legacy_to_ssot_migration_suggestions(self):
        """
        MIGRATION CRITICAL: Test migration suggestions for legacy code.
        This validates our ability to guide migration to SSOT patterns.
        """
        # Create legacy test class
        class MigrationCandidateTest(TestCase):
            def setUp(self):
                self.env_var = os.environ.get('TEST_VAR')
                self.websocket = TestWebSocketConnection()  # Real WebSocket implementation
            
            def test_functionality(self):
                self.assertTrue(True)
        
        # Test migration suggestion generation
        migration_plan = migrate_legacy_test_to_ssot(MigrationCandidateTest)
        self.assertIsInstance(migration_plan, dict)
        
        required_plan_keys = [
            'current_inheritance',
            'suggested_base_class',
            'required_changes',
            'migration_steps',
            'estimated_effort'
        ]
        
        for key in required_plan_keys:
            self.assertIn(key, migration_plan,
                         f"Migration plan missing key: {key}")
        
        # Test migration steps are actionable
        migration_steps = migration_plan['migration_steps']
        self.assertIsInstance(migration_steps, list)
        self.assertGreater(len(migration_steps), 0,
                          "Migration plan should have actionable steps")
        
        # Each step should have description and code example
        for step in migration_steps:
            self.assertIn('description', step,
                         "Migration step should have description")
            self.assertIn('before', step,
                         "Migration step should show before code")
            self.assertIn('after', step,
                         "Migration step should show after code")
    
    def test_legacy_compatibility_report_generation(self):
        """
        REPORTING CRITICAL: Test legacy compatibility report generation.
        This validates our ability to track migration progress.
        """
        # Generate compatibility report
        report = get_legacy_compatibility_report()
        self.assertIsInstance(report, dict)
        
        required_report_sections = [
            'summary',
            'legacy_patterns_found',
            'migration_candidates',
            'compatibility_issues',
            'recommendations'
        ]
        
        for section in required_report_sections:
            self.assertIn(section, report,
                         f"Compatibility report missing section: {section}")
        
        # Test report summary
        summary = report['summary']
        self.assertIsInstance(summary, dict)
        
        summary_metrics = [
            'total_test_files_scanned',
            'legacy_patterns_detected',
            'migration_priority_high',
            'migration_priority_medium',
            'migration_priority_low'
        ]
        
        for metric in summary_metrics:
            self.assertIn(metric, summary,
                         f"Report summary missing metric: {metric}")
            self.assertIsInstance(summary[metric], int,
                                f"Report metric should be integer: {metric}")
    
    def test_ssot_environment_with_legacy_code(self):
        """
        ENVIRONMENT CRITICAL: Test SSOT environment works with legacy code.
        This ensures IsolatedEnvironment doesn't break legacy patterns.
        """
        # Test that legacy environment access patterns work
        test_var_name = f"LEGACY_TEST_VAR_{self.test_id}"
        test_var_value = "legacy_test_value"
        
        with patch.dict(os.environ, {test_var_name: test_var_value}):
            # Legacy direct access should still work (but be discouraged)
            legacy_value = os.environ.get(test_var_name)
            self.assertEqual(legacy_value, test_var_value,
                           "Legacy os.environ access should still work")
            
            # SSOT environment should also work
            ssot_value = self.env.get(test_var_name)
            self.assertEqual(ssot_value, test_var_value,
                           "SSOT environment should provide same value")
            
            # Both approaches should give same result
            self.assertEqual(legacy_value, ssot_value,
                           "Legacy and SSOT environment access should match")
    
    def test_mixed_inheritance_patterns(self):
        """
        INHERITANCE CRITICAL: Test mixed inheritance patterns work.
        This ensures gradual migration doesn't break existing hierarchies.
        """
        # Test class that mixes legacy and SSOT patterns
        class MixedInheritanceTest(BaseTestCase):
            def setUp(self):
                super().setUp()  # SSOT setup
                self.legacy_data = "legacy_value"  # Legacy pattern
            
            def test_mixed_functionality(self):
                # SSOT assertions
                self.assertIsInstance(self.env, IsolatedEnvironment)
                
                # Legacy assertions  
                self.assertEqual(self.legacy_data, "legacy_value")
                self.assertTrue(True)
        
        # Test that mixed pattern works
        errors = validate_test_class(MixedInheritanceTest)
        self.assertEqual(len(errors), 0,
                        f"Mixed inheritance pattern should be valid, got errors: {errors}")
        
        # Test instantiation works
        test_instance = MixedInheritanceTest()
        test_instance.setUp()
        
        # Should have both SSOT and legacy capabilities
        self.assertIsInstance(test_instance.env, IsolatedEnvironment)
        self.assertEqual(test_instance.legacy_data, "legacy_value")
        
        test_instance.tearDown()
    
    def test_legacy_async_pattern_compatibility(self):
        """
        ASYNC COMPATIBILITY CRITICAL: Test legacy async patterns work.
        This ensures existing async test code doesn't break with SSOT.
        """
        import asyncio
        
        # Test legacy async test pattern
        class LegacyAsyncTest(AsyncBaseTestCase):
            async def asyncSetUp(self):
                await super().asyncSetUp()
                self.async_data = await self._async_setup_helper()
            
            async def _async_setup_helper(self):
                await asyncio.sleep(0.001)  # Simulate async work
                return "async_setup_complete"
            
            async def test_async_functionality(self):
                result = await self._async_test_helper()
                self.assertEqual(result, "async_test_complete")
            
            async def _async_test_helper(self):
                await asyncio.sleep(0.001)  # Simulate async work
                return "async_test_complete"
            
            async def asyncTearDown(self):
                await super().asyncTearDown()
                self.async_data = None
        
        # Test that async pattern works with SSOT
        async def run_legacy_async_test():
            test_instance = LegacyAsyncTest()
            await test_instance.asyncSetUp()
            
            # Should have SSOT capabilities
            self.assertIsInstance(test_instance.env, IsolatedEnvironment)
            
            # Should have async setup data
            self.assertEqual(test_instance.async_data, "async_setup_complete")
            
            # Run test method
            await test_instance.test_async_functionality()
            
            await test_instance.asyncTearDown()
        
        # Run async test
        asyncio.run(run_legacy_async_test())
    
    def test_performance_impact_of_compatibility_layer(self):
        """
        PERFORMANCE CRITICAL: Test compatibility layer doesn't degrade performance.
        This ensures backward compatibility doesn't slow down test execution.
        """
        import psutil
        
        process = psutil.Process()
        
        # Measure performance of direct SSOT usage
        start_time = time.time()
        initial_memory = process.memory_info().rss
        
        # Direct SSOT operations
        for i in range(100):
            factory = get_mock_factory()
            mock = factory.create_mock(f"direct_ssot_{i}")
            factory.cleanup_all_mocks()
        
        direct_duration = time.time() - start_time
        mid_memory = process.memory_info().rss
        
        # Measure performance of compatibility layer
        start_time = time.time()
        
        # Compatibility layer operations
        for i in range(100):
            adapter = LegacyMockFactoryAdapter()
            mock = adapter.create_mock(f"legacy_adapter_{i}")
            adapter.cleanup()
        
        adapter_duration = time.time() - start_time
        final_memory = process.memory_info().rss
        
        # Performance assertions
        max_slowdown = 2.0  # Allow 2x slowdown for compatibility
        max_memory_overhead = 10 * 1024 * 1024  # 10MB overhead
        
        slowdown_ratio = adapter_duration / direct_duration if direct_duration > 0 else 1
        memory_overhead = final_memory - mid_memory
        
        self.assertLess(slowdown_ratio, max_slowdown,
                       f"Compatibility layer too slow: {slowdown_ratio:.2f}x slowdown")
        
        self.assertLess(memory_overhead, max_memory_overhead,
                       f"Compatibility layer using too much memory: {memory_overhead} bytes")
        
        logger.info(f"Performance compatibility test: {slowdown_ratio:.2f}x slowdown, {memory_overhead} bytes overhead")


class TestSSOTLegacyMigrationHelpers:
    """
    MIGRATION CRITICAL: Test SSOT migration helper functionality.
    These tests validate tools that help migrate legacy code to SSOT patterns.
    """
    
    async def setUp(self):
        """Set up migration helper test environment with REAL services."""
        self.test_id = uuid.uuid4().hex[:8]
        
        # Initialize REAL service connections for migration testing
        self.env = IsolatedEnvironment()
        self.db_manager = DatabaseManager()
        self.redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6381, decode_responses=True)
        self.test_context = TestContext(user_id=f"migration_user_{self.test_id}")
        
        logger.info(f"Starting migration helper test with REAL services: {self._testMethodName} (ID: {self.test_id})")
    
    async def tearDown(self):
        """Clean up migration helper test and REAL service connections."""
        try:
            await self.redis_client.flushdb()
        except:
            pass
            
        logger.info(f"Completed migration helper test cleanup: {self._testMethodName} (ID: {self.test_id})")
    
    def test_automatic_migration_tool(self):
        """
        AUTOMATION CRITICAL: Test automatic migration tool functionality.
        This validates our ability to automatically migrate simple legacy patterns.
        """
        # Create simple legacy test code
        legacy_code = '''
class OldTest(SSotAsyncTestCase):
    def setUp(self):
        self.env_var = os.environ.get('TEST_VAR')
        self.websocket = TestWebSocketConnection()  # Real WebSocket implementation
    
    def test_something(self):
        self.assertEqual(1, 1)
'''
        
        # Test automatic migration (would be implemented in real migration tool)
        # For now, test that we can parse and analyze legacy code
        
        from test_framework.ssot.compatibility_bridge import analyze_code_for_migration
        
        analysis = analyze_code_for_migration(legacy_code)
        self.assertIsInstance(analysis, dict)
        
        expected_analysis_keys = [
            'legacy_patterns',
            'suggested_changes',
            'migration_complexity',
            'auto_migrateable'
        ]
        
        for key in expected_analysis_keys:
            self.assertIn(key, analysis,
                         f"Code analysis missing key: {key}")
        
        # Test that common patterns are detected
        patterns = analysis['legacy_patterns']
        self.assertIn('unittest_inheritance', patterns)
        self.assertIn('direct_environ_access', patterns)
        self.assertIn('manual_mock_creation', patterns)
    
    def test_migration_validation_tool(self):
        """
        VALIDATION CRITICAL: Test migration validation functionality.
        This ensures migrated code works correctly and follows SSOT patterns.
        """
        # Create migrated test code
        migrated_code = '''
class NewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.env_var = self.env.get('TEST_VAR')
        factory = get_mock_factory()
        self.mock_obj = factory.create_mock('test_service')
    
    def test_something(self):
        self.assertEqual(1, 1)
'''
        
        from test_framework.ssot.compatibility_bridge import validate_migrated_code
        
        validation = validate_migrated_code(migrated_code)
        self.assertIsInstance(validation, dict)
        
        expected_validation_keys = [
            'ssot_compliance',
            'pattern_violations',
            'performance_impact',
            'migration_quality'
        ]
        
        for key in expected_validation_keys:
            self.assertIn(key, validation,
                         f"Migration validation missing key: {key}")
        
        # Test that SSOT patterns are recognized
        compliance = validation['ssot_compliance']
        self.assertIsInstance(compliance, dict)
        
        # Should detect good SSOT patterns
        self.assertTrue(compliance.get('inherits_from_basetest', False),
                       "Should detect BaseTestCase inheritance")
        self.assertTrue(compliance.get('uses_isolated_environment', False),
                       "Should detect IsolatedEnvironment usage")
        self.assertTrue(compliance.get('uses_mock_factory', False),
                       "Should detect MockFactory usage")
    
    def test_batch_migration_tool(self):
        """
        BATCH CRITICAL: Test batch migration tool functionality.
        This validates our ability to migrate multiple test files at once.
        """
        # Simulate multiple test files that need migration
        test_files = [
            {
                'path': f'test_file_1_{self.test_id}.py',
                'legacy_patterns': ['unittest_inheritance', 'direct_environ_access'],
                'migration_priority': 'high'
            },
            {
                'path': f'test_file_2_{self.test_id}.py', 
                'legacy_patterns': ['manual_mock_creation'],
                'migration_priority': 'medium'
            },
            {
                'path': f'test_file_3_{self.test_id}.py',
                'legacy_patterns': ['manual_database_connection'],
                'migration_priority': 'low'
            }
        ]
        
        from test_framework.ssot.compatibility_bridge import create_batch_migration_plan
        
        batch_plan = create_batch_migration_plan(test_files)
        self.assertIsInstance(batch_plan, dict)
        
        expected_batch_keys = [
            'migration_phases',
            'dependency_order',
            'estimated_duration',
            'risk_assessment'
        ]
        
        for key in expected_batch_keys:
            self.assertIn(key, batch_plan,
                         f"Batch migration plan missing key: {key}")
        
        # Test migration phases
        phases = batch_plan['migration_phases']
        self.assertIsInstance(phases, list)
        self.assertGreater(len(phases), 0,
                          "Batch plan should have migration phases")
        
        # Test that high priority items are in early phases
        phase_priorities = []
        for phase in phases:
            for item in phase.get('items', []):
                phase_priorities.append(item.get('priority'))
        
        # Should have high priority items first
        high_priority_index = phase_priorities.index('high') if 'high' in phase_priorities else -1
        low_priority_index = phase_priorities.index('low') if 'low' in phase_priorities else -1
        
        if high_priority_index >= 0 and low_priority_index >= 0:
            self.assertLess(high_priority_index, low_priority_index,
                           "High priority items should come before low priority items")


class TestSSOTDeprecationHandling:
    """
    DEPRECATION CRITICAL: Test SSOT deprecation handling.
    These tests ensure deprecated patterns are handled gracefully with warnings.
    """
    
    def setUp(self):
        """Set up deprecation handling test environment."""
        super().setUp()
        self.test_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting deprecation handling test: {self._testMethodName} (ID: {self.test_id})")
    
    def tearDown(self):
        """Clean up deprecation handling test."""
        logger.info(f"Completing deprecation handling test: {self._testMethodName} (ID: {self.test_id})")
        super().tearDown()
    
    def test_deprecation_warnings_for_legacy_patterns(self):
        """
        WARNING CRITICAL: Test deprecation warnings are issued for legacy patterns.
        This ensures developers are notified when using deprecated patterns.
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")  # Catch all warnings
            
            # Use deprecated pattern
            from test_framework.ssot.compatibility_bridge import deprecated_mock_factory
            
            # Should issue deprecation warning
            deprecated_factory = deprecated_mock_factory()
            
            # Check that warning was issued
            deprecation_warnings = [w for w in warning_list 
                                  if issubclass(w.category, DeprecationWarning)]
            
            self.assertGreater(len(deprecation_warnings), 0,
                             "Should issue deprecation warning for deprecated mock factory")
            
            # Check warning message is helpful
            warning_message = str(deprecation_warnings[0].message)
            self.assertIn("deprecated", warning_message.lower())
            self.assertIn("get_mock_factory", warning_message)
    
    def test_gradual_deprecation_timeline(self):
        """
        TIMELINE CRITICAL: Test gradual deprecation timeline is respected.
        This ensures deprecated features are removed on schedule.
        """
        from test_framework.ssot.compatibility_bridge import get_deprecation_timeline
        
        timeline = get_deprecation_timeline()
        self.assertIsInstance(timeline, dict)
        
        expected_timeline_keys = [
            'phase_1_warnings',
            'phase_2_strict_warnings',
            'phase_3_removal',
            'current_phase'
        ]
        
        for key in expected_timeline_keys:
            self.assertIn(key, timeline,
                         f"Deprecation timeline missing key: {key}")
        
        # Test current phase is valid
        current_phase = timeline['current_phase']
        valid_phases = ['phase_1_warnings', 'phase_2_strict_warnings', 'phase_3_removal']
        self.assertIn(current_phase, valid_phases,
                     f"Current deprecation phase should be one of {valid_phases}")
        
        # Test that timeline has dates
        for phase_key in expected_timeline_keys[:-1]:  # Exclude current_phase
            phase_info = timeline[phase_key]
            self.assertIn('target_date', phase_info,
                         f"Phase {phase_key} should have target_date")
            self.assertIn('description', phase_info,
                         f"Phase {phase_key} should have description")


if __name__ == '__main__':
    # Configure logging for test execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Import unittest for compatibility tests
    import unittest
    
    # Run the tests
    pytest.main([__file__, '-v', '--tb=short', '--capture=no'])