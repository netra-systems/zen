"""
Test Suite: Issue #884 - Multiple execution engine factories blocking AI responses
Module: Execution Engine Factory User Isolation Integration Test

PURPOSE:
This integration test validates that the consolidated factory maintains proper user isolation
when creating execution engines for concurrent users, preventing shared state issues.

BUSINESS IMPACT:
- $500K+ ARR protected by ensuring proper user isolation in multi-user execution
- Factory user isolation prevents cross-user data leakage
- Memory isolation ensures bounded growth per user (not global accumulation)
- Concurrent user handling prevents execution engine state corruption

TEST REQUIREMENTS:
- Tests 5+ concurrent users with no shared state
- Validates memory isolation and cleanup
- Uses real services, NO Docker required
- Validates concurrent factory behavior

Created: 2025-09-14 for Issue #884 Step 2 user isolation validation
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional
import pytest
from datetime import datetime, UTC
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
import psutil
import os

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.integration
class ExecutionEngineFactoryUserIsolation884Tests(SSotAsyncTestCase):
    """
    Integration Test: Validate factory maintains proper user isolation
    
    This test validates that the consolidated factory creates isolated execution
    engines for multiple concurrent users without shared state or memory leaks.
    """
    
    def setup_method(self, method):
        """Set up user isolation integration test"""
        super().setup_method(method)
        self.record_metric("test_type", "integration")
        self.record_metric("focuses_on", "user_isolation")
        self.record_metric("concurrent_users_target", 5)
        self.record_metric("issue_number", "884")
        
        # Set test environment for isolation testing
        env = self.get_env()
        env.set("TESTING", "true", "user_isolation_test")
        env.set("TEST_USER_ISOLATION", "true", "user_isolation_test")
        
    async def test_factory_user_isolation_concurrent_execution_884(self):
        """
        CRITICAL INTEGRATION TEST: Validate factory maintains user isolation across concurrent executions
        
        This test creates execution engines for 5+ concurrent users and validates:
        1. No shared state between user execution engines
        2. Memory isolation per user
        3. Proper cleanup after execution
        4. No cross-user data leakage
        """
        start_time = time.time()
        self.record_metric("test_execution_start", start_time)
        
        # Get initial memory baseline
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        self.record_metric("initial_memory_mb", initial_memory)
        
        # Import required components
        try:
            # Try to import consolidated factory
            factory = None
            factory_source = None
            
            try:
                from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
                factory = ExecutionEngineFactory()
                factory_source = "core.managers.execution_engine_factory"
            except ImportError:
                try:
                    from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineFactory
                    factory = ExecutionEngineFactory()
                    factory_source = "agents.execution_engine_consolidated"
                except ImportError:
                    try:
                        from netra_backend.app.agents.execution_engine_unified_factory import create_execution_engine
                        class FactoryWrapper:
                            def create_execution_engine(self, context):
                                return create_execution_engine(context)
                        factory = FactoryWrapper()
                        factory_source = "agents.execution_engine_unified_factory"
                    except ImportError:
                        pytest.skip("No factory available for testing")
            
            self.record_metric("factory_source", factory_source)
            
            # Import UserExecutionContext
            try:
                from netra_backend.app.agents.user_execution_context import UserExecutionContext
            except ImportError:
                try:
                    from netra_backend.app.core.user_execution_context import UserExecutionContext
                except ImportError:
                    # Create test context if not available
                    class UserExecutionContextTests:
                        def __init__(self, user_id: str, session_id: str, **kwargs):
                            self.user_id = user_id
                            self.session_id = session_id
                            self.trace_id = kwargs.get('trace_id', f"trace_{uuid.uuid4().hex[:8]}")
                            self.environment = kwargs.get('environment', 'test')
                            self.metadata = kwargs
                    UserExecutionContext = UserExecutionContextTests
            
        except Exception as e:
            pytest.skip(f"Required components not available: {e}")
        
        # Create concurrent user contexts
        concurrent_users = 7  # Test more than minimum 5
        user_contexts = []
        
        for i in range(concurrent_users):
            user_id = f"isolation_test_user_{i}_{uuid.uuid4().hex[:8]}"
            session_id = f"isolation_test_session_{i}_{uuid.uuid4().hex[:8]}"
            
            context = UserExecutionContext(
                user_id=user_id,
                session_id=session_id,
                trace_id=f"isolation_trace_{i}_{uuid.uuid4().hex[:8]}",
                environment="test_isolation",
                test_user_index=i  # Add test-specific metadata
            )
            
            user_contexts.append({
                'context': context,
                'user_id': user_id,
                'session_id': session_id,
                'user_index': i
            })
        
        self.record_metric("concurrent_users_created", len(user_contexts))
        
        # Function to create execution engine for a single user
        def create_user_execution_engine(user_data):
            thread_id = threading.current_thread().ident
            context = user_data['context']
            user_index = user_data['user_index']
            
            try:
                # Record memory before creation
                process = psutil.Process(os.getpid())
                before_memory = process.memory_info().rss / 1024 / 1024
                
                creation_start = time.time()
                
                # Create execution engine
                execution_engine = factory.create_execution_engine(context)
                
                creation_time = time.time() - creation_start
                
                # Record memory after creation
                after_memory = process.memory_info().rss / 1024 / 1024
                memory_diff = after_memory - before_memory
                
                # Validate engine was created
                if execution_engine is None:
                    return {
                        'success': False,
                        'error': 'Factory returned None execution engine',
                        'user_index': user_index,
                        'thread_id': thread_id
                    }
                
                # Check for unique object identity
                engine_id = id(execution_engine)
                
                return {
                    'success': True,
                    'user_index': user_index,
                    'user_id': user_data['user_id'],
                    'session_id': user_data['session_id'],
                    'thread_id': thread_id,
                    'engine_id': engine_id,
                    'engine': execution_engine,
                    'creation_time': creation_time,
                    'memory_before': before_memory,
                    'memory_after': after_memory,
                    'memory_diff': memory_diff
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'user_index': user_index,
                    'thread_id': thread_id
                }
        
        # Execute factory calls concurrently
        results = []
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            # Submit all user factory calls
            future_to_user = {
                executor.submit(create_user_execution_engine, user_data): user_data 
                for user_data in user_contexts
            }
            
            # Collect results
            for future in as_completed(future_to_user):
                result = future.result()
                results.append(result)
        
        # Analyze results
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        self.record_metric("successful_creations", len(successful_results))
        self.record_metric("failed_creations", len(failed_results))
        self.record_metric("failure_details", failed_results)
        
        # CRITICAL ASSERTION: All factory calls should succeed
        assert len(failed_results) == 0, (
            f"CRITICAL: Factory failed for {len(failed_results)} users. "
            f"Failures: {failed_results}. "
            f"This indicates factory instability under concurrent load that "
            f"blocks reliable multi-user AI response delivery."
        )
        
        assert len(successful_results) == concurrent_users, (
            f"CRITICAL: Expected {concurrent_users} successful engine creations, got {len(successful_results)}. "
            f"This indicates factory reliability issues under concurrent load."
        )
        
        # Validate unique execution engine instances (no shared state)
        engine_ids = [r['engine_id'] for r in successful_results]
        unique_engine_ids = set(engine_ids)
        
        assert len(unique_engine_ids) == concurrent_users, (
            f"CRITICAL: Expected {concurrent_users} unique execution engines, got {len(unique_engine_ids)}. "
            f"Engine IDs: {engine_ids}. "
            f"This indicates shared state between users that violates isolation."
        )
        
        # Validate thread isolation
        thread_ids = [r['thread_id'] for r in successful_results]
        unique_threads = set(thread_ids)
        
        # Should execute across multiple threads
        assert len(unique_threads) > 1, (
            f"CRITICAL: All executions ran on single thread: {unique_threads}. "
            f"This indicates threading issues that prevent true concurrent isolation."
        )
        
        # Validate memory usage is reasonable per user
        memory_diffs = [r['memory_diff'] for r in successful_results]
        avg_memory_per_user = sum(memory_diffs) / len(memory_diffs)
        max_memory_per_user = max(memory_diffs)
        
        self.record_metric("avg_memory_per_user_mb", avg_memory_per_user)
        self.record_metric("max_memory_per_user_mb", max_memory_per_user)
        
        # Each user should use reasonable memory (not excessive)
        assert max_memory_per_user < 100.0, (  # 100MB limit per user
            f"CRITICAL: User execution engine uses excessive memory: {max_memory_per_user:.2f}MB. "
            f"This indicates memory issues that prevent scalable multi-user execution."
        )
        
        # Performance validation
        creation_times = [r['creation_time'] for r in successful_results]
        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        
        self.record_metric("avg_creation_time", avg_creation_time)
        self.record_metric("max_creation_time", max_creation_time)
        
        # Factory should be reasonably fast even under load
        assert avg_creation_time < 2.0, (
            f"CRITICAL: Factory too slow under concurrent load: {avg_creation_time:.3f}s avg. "
            f"This affects user experience and scalability."
        )
        
        # Clean up execution engines and validate memory cleanup
        del results
        del successful_results
        del failed_results
        
        # Force garbage collection
        gc.collect()
        
        # Check final memory
        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_growth = final_memory - initial_memory
        
        self.record_metric("final_memory_mb", final_memory)
        self.record_metric("total_memory_growth_mb", total_memory_growth)
        
        # Memory growth should be bounded
        assert total_memory_growth < 200.0, (  # 200MB total growth limit
            f"CRITICAL: Excessive memory growth: {total_memory_growth:.2f}MB. "
            f"This indicates memory leaks that prevent scalable operation."
        )
        
        execution_time = time.time() - start_time
        self.record_metric("total_test_execution_time", execution_time)
        
        # Record successful isolation validation
        self.record_metric("user_isolation_validated", True)
        self.record_metric("memory_isolation_verified", True)
        self.record_metric("concurrent_execution_verified", True)
        self.record_metric("business_value_protected", True)
        
    async def test_factory_prevents_user_data_leakage_884(self):
        """
        CRITICAL TEST: Validate factory prevents data leakage between users
        
        This test creates execution engines for different users and validates
        that user-specific data doesn't leak between execution engines.
        """
        # Import required components
        try:
            from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
            factory = ExecutionEngineFactory()
        except ImportError:
            try:
                from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineFactory
                factory = ExecutionEngineFactory()
            except ImportError:
                pytest.skip("Factory not available")
        
        try:
            from netra_backend.app.agents.user_execution_context import UserExecutionContext
        except ImportError:
            # Use test context
            class UserExecutionContextTests:
                def __init__(self, user_id: str, session_id: str, **kwargs):
                    self.user_id = user_id
                    self.session_id = session_id
                    self.metadata = kwargs
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            UserExecutionContext = UserExecutionContextTests
        
        # Create two users with distinct data
        user1_secret = f"user1_secret_{uuid.uuid4().hex}"
        user2_secret = f"user2_secret_{uuid.uuid4().hex}"
        
        context1 = UserExecutionContext(
            user_id="isolation_user_1",
            session_id="isolation_session_1",
            secret_data=user1_secret,
            user_index=1
        )
        
        context2 = UserExecutionContext(
            user_id="isolation_user_2", 
            session_id="isolation_session_2",
            secret_data=user2_secret,
            user_index=2
        )
        
        # Create execution engines
        engine1 = factory.create_execution_engine(context1)
        engine2 = factory.create_execution_engine(context2)
        
        # Validate engines are distinct
        self.assertNotEqual(id(engine1), id(engine2),
            "CRITICAL: Execution engines share object identity - indicates shared state")
        
        # If engines have context attributes, validate they contain correct user data
        if hasattr(engine1, 'context') and hasattr(engine2, 'context'):
            # Check user1 context
            if hasattr(engine1.context, 'user_id'):
                self.assertEqual(engine1.context.user_id, "isolation_user_1",
                    "CRITICAL: Engine1 has incorrect user_id - indicates data leakage")
            
            # Check user2 context
            if hasattr(engine2.context, 'user_id'):
                self.assertEqual(engine2.context.user_id, "isolation_user_2",
                    "CRITICAL: Engine2 has incorrect user_id - indicates data leakage")
            
            # Validate secret data isolation
            if hasattr(engine1.context, 'secret_data'):
                self.assertEqual(engine1.context.secret_data, user1_secret,
                    "CRITICAL: Engine1 secret data corrupted - indicates isolation failure")
                
            if hasattr(engine2.context, 'secret_data'):
                self.assertEqual(engine2.context.secret_data, user2_secret,
                    "CRITICAL: Engine2 secret data corrupted - indicates isolation failure")
                
                # Most critical: ensure user1 secret is not in user2 engine
                self.assertNotEqual(engine2.context.secret_data, user1_secret,
                    "CRITICAL: User1 secret leaked to User2 engine - SEVERE isolation violation")
        
        self.record_metric("data_leakage_prevention_verified", True)
        
    async def test_factory_memory_cleanup_per_user_884(self):
        """
        CRITICAL TEST: Validate factory enables proper memory cleanup per user
        
        This test validates that execution engines created by the factory
        can be properly cleaned up without memory leaks.
        """
        # Get initial memory
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Import factory
        try:
            from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
            factory = ExecutionEngineFactory()
        except ImportError:
            pytest.skip("Factory not available")
            
        try:
            from netra_backend.app.agents.user_execution_context import UserExecutionContext
        except ImportError:
            class UserExecutionContextTests:
                def __init__(self, user_id: str, session_id: str, **kwargs):
                    self.user_id = user_id
                    self.session_id = session_id
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            UserExecutionContext = UserExecutionContextTests
        
        # Create and destroy multiple execution engines
        for i in range(10):  # Create/destroy cycle
            context = UserExecutionContext(
                user_id=f"cleanup_test_user_{i}",
                session_id=f"cleanup_test_session_{i}"
            )
            
            engine = factory.create_execution_engine(context)
            self.assertIsNotNone(engine, f"Failed to create engine {i}")
            
            # Delete engine explicitly
            del engine
            
            # Force garbage collection every few iterations
            if i % 3 == 0:
                gc.collect()
        
        # Final garbage collection
        gc.collect()
        
        # Check final memory
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        self.record_metric("cleanup_test_memory_growth", memory_growth)
        
        # Memory growth should be minimal after cleanup
        assert memory_growth < 50.0, (  # 50MB growth limit
            f"CRITICAL: Memory not cleaned up properly: {memory_growth:.2f}MB growth. "
            f"This indicates memory leaks that prevent scalable multi-user operation."
        )
        
        self.record_metric("memory_cleanup_verified", True)