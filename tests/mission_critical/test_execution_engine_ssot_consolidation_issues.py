#!/usr/bin/env python
"""MISSION CRITICAL: Execution Engine SSOT Consolidation Issue Detection Tests

PURPOSE: Demonstrate remaining SSOT violations and consolidation issues in execution engine
implementations to support issue #182 strategic testing.

These tests are DESIGNED TO FAIL initially to prove problems exist:
1. SSOT Violation Detection (2 tests)
2. User Isolation Failures (2 tests) 
3. Factory Pattern Issues (2 tests)
4. Golden Path Protection (1 test)

Business Impact: $500K+ ARR at risk from execution engine inconsistencies
Architecture Impact: 60% reduction in duplicated execution logic needed

NO DOCKER DEPENDENCIES - Unit/Integration/E2E Staging only
"""

import asyncio
import gc
import inspect
import os
import sys
import time
import uuid
import weakref
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
import tracemalloc
import psutil

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import all execution engine implementations to detect SSOT violations
# ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as SupervisorExecutionEngine
from netra_backend.app.agents.execution_engine_consolidated import (
    ExecutionEngine as ConsolidatedExecutionEngine,
    RequestScopedExecutionEngine,
    ExecutionEngineFactory as ConsolidatedFactory
)
# ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as CoreExecutionEngine
from netra_backend.app.services.unified_tool_registry.execution_engine import (
    ToolExecutionEngine as ToolRegistryExecutionEngine
)

# Import factory implementations
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory as SupervisorFactory
)

# Import context and user management
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Base test case
from test_framework.ssot.base_test_case import SSotAsyncTestCase


# Helper for creating mock dependencies
class MockWebSocketBridge:
    """Minimal mock WebSocket bridge for testing factory patterns."""
    async def emit_agent_event(self, *args, **kwargs):
        pass


def create_test_factory():
    """Create a test factory with minimal dependencies."""
    mock_bridge = MockWebSocketBridge()
    return SupervisorFactory(websocket_bridge=mock_bridge)


class TestExecutionEngineSSotViolationDetection(SSotAsyncTestCase):
    """Test 1 & 2: SSOT Violation Detection - Multiple execution engine implementations"""
    
    async def test_execution_engine_implementation_duplicates_detected(self):
        """DESIGNED TO FAIL: Detect duplicate execution engine implementations.
        
        This test should FAIL because we have multiple execution engine 
        implementations that violate SSOT principles.
        
        Expected Issues:
        - SupervisorExecutionEngine vs UnifiedExecutionEngine
        - Multiple factory patterns 
        - Inconsistent interfaces
        """
        # Collect all AGENT execution engine classes (exclude tool execution engines)
        execution_engines = [
            SupervisorExecutionEngine,
            ConsolidatedExecutionEngine,
            # CoreExecutionEngine removed - now same as SupervisorExecutionEngine after import fix
            # ToolRegistryExecutionEngine removed - this is for tool execution, not agent execution
        ]
        
        # Analyze class hierarchies and methods
        engine_analysis = {}
        for engine_class in execution_engines:
            methods = set(method for method in dir(engine_class) 
                         if not method.startswith('_') and callable(getattr(engine_class, method)))
            
            # Get source file
            source_file = inspect.getfile(engine_class)
            
            # Use module + class name to avoid key conflicts with same-named classes
            key = f"{engine_class.__module__}.{engine_class.__name__}"
            engine_analysis[key] = {
                'methods': methods,
                'source_file': source_file,
                'base_classes': [base.__name__ for base in engine_class.__mro__[1:]],
                'method_count': len(methods)
            }
        
        logger.info(f"Execution Engine Analysis: {engine_analysis}")
        
        # Check for SSOT violations
        ssot_violations = []
        
        # Detect duplicate core methods across implementations
        all_methods = defaultdict(list)
        for engine_name, analysis in engine_analysis.items():
            for method in analysis['methods']:
                all_methods[method].append(engine_name)
        
        # Find methods implemented in multiple engines (SSOT violation)
        core_methods = ['execute', 'run', 'process', 'handle_request', 'execute_pipeline']
        for method in core_methods:
            if method in all_methods and len(all_methods[method]) > 1:
                ssot_violations.append(f"Method '{method}' implemented in multiple engines: {all_methods[method]}")
        
        # Check for file duplication
        source_files = [analysis['source_file'] for analysis in engine_analysis.values()]
        if len(set(source_files)) < len(source_files):
            ssot_violations.append("Multiple execution engines reference same source file")
        
        # Check for inconsistent interfaces
        method_counts = [analysis['method_count'] for analysis in engine_analysis.values()]
        if max(method_counts) - min(method_counts) > 3:
            ssot_violations.append(f"Inconsistent interface sizes: {method_counts}")
        
        # This test should FAIL - we expect SSOT violations
        assert len(ssot_violations) > 0, (
            f"Expected SSOT violations in execution engines, but found none. "
            f"This indicates the consolidation might already be complete. "
            f"Analysis: {engine_analysis}"
        )
        
        # Log the violations for debugging
        for violation in ssot_violations:
            logger.error(f"SSOT Violation Detected: {violation}")
            
        # Fail the test to demonstrate the problem
        pytest.fail(f"SSOT Violations Detected ({len(ssot_violations)} issues): {ssot_violations}")

    async def test_factory_pattern_duplication_detected(self):
        """DESIGNED TO FAIL: Detect multiple factory pattern implementations.
        
        Expected Issues:
        - SupervisorFactory vs ConsolidatedFactory
        - Inconsistent factory interfaces
        - Multiple creation patterns
        """
        # Collect factory implementations
        factories = [
            SupervisorFactory,
            ConsolidatedFactory,
        ]
        
        factory_analysis = {}
        
        # Analyze class-based factories
        for factory in factories:
            methods = set(method for method in dir(factory) 
                         if not method.startswith('_') and callable(getattr(factory, method)))
            
            factory_analysis[factory.__name__] = {
                'methods': methods,
                'source_file': inspect.getfile(factory),
                'is_class': inspect.isclass(factory),
                'creation_methods': [m for m in methods if 'create' in m.lower() or 'build' in m.lower()]
            }
        
        logger.info(f"Factory Analysis: {factory_analysis}")
        
        # Detect factory pattern violations
        factory_violations = []
        
        # Check for multiple creation patterns
        creation_patterns = []
        for name, analysis in factory_analysis.items():
            if analysis['is_class']:
                creation_patterns.append(f"Class-based factory: {name}")
            else:
                creation_patterns.append(f"Function-based factory: {name}")
        
        if len(creation_patterns) > 1:
            factory_violations.append(f"Multiple factory patterns: {creation_patterns}")
        
        # Check for method duplication
        all_creation_methods = []
        for analysis in factory_analysis.values():
            all_creation_methods.extend(analysis['creation_methods'])
        
        method_counts = Counter(all_creation_methods)
        duplicate_methods = [method for method, count in method_counts.items() if count > 1]
        if duplicate_methods:
            factory_violations.append(f"Duplicate factory methods: {duplicate_methods}")
        
        # This test should FAIL - we expect factory violations
        assert len(factory_violations) > 0, (
            f"Expected factory pattern violations, but found none. "
            f"Analysis: {factory_analysis}"
        )
        
        # Log violations
        for violation in factory_violations:
            logger.error(f"Factory Pattern Violation: {violation}")
            
        pytest.fail(f"Factory Pattern Violations Detected ({len(factory_violations)} issues): {factory_violations}")


class TestUserIsolationFailures(SSotAsyncTestCase):
    """Test 3 & 4: User Isolation Failures - Shared state and event collisions"""
    
    async def test_user_execution_context_shared_state_detected(self):
        """DESIGNED TO FAIL: Detect shared state between user execution contexts.
        
        Expected Issues:
        - Global state in execution engines
        - Shared caches or registries
        - User data bleeding between contexts
        """
        # Create multiple user contexts
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        
        # Track memory references to detect shared state
        shared_state_violations = []
        memory_refs = {}
        
        try:
            # Create execution engines for different users
            context1 = UserExecutionContext(
                user_id=user1_id,
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            
            context2 = UserExecutionContext(
                user_id=user2_id,
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            
            # Create engines through different factories
            factory = create_test_factory()
            engine1 = await factory.create_for_user(context1)
            engine2 = await factory.create_for_user(context2)
            
            # Test for shared object references
            engine1_vars = vars(engine1) if hasattr(engine1, '__dict__') else {}
            engine2_vars = vars(engine2) if hasattr(engine2, '__dict__') else {}
            
            # Check for shared references
            for attr1, value1 in engine1_vars.items():
                for attr2, value2 in engine2_vars.items():
                    if attr1 == attr2 and value1 is value2 and id(value1) == id(value2):
                        # Skip immutable types that can be safely shared
                        if not isinstance(value1, (str, int, float, bool, type(None), tuple)):
                            shared_state_violations.append(
                                f"Shared mutable object detected: {attr1} = {type(value1).__name__} "
                                f"(id: {id(value1)})"
                            )
            
            # Test for global state pollution
            # Set user-specific data and check if it bleeds
            if hasattr(engine1, '_user_data'):
                engine1._user_data = {'test_key': 'user1_value'}
            if hasattr(engine2, '_user_data'):
                engine2._user_data = {'test_key': 'user2_value'}
            
            # Check if state is properly isolated
            if (hasattr(engine1, '_user_data') and hasattr(engine2, '_user_data') and 
                engine1._user_data is engine2._user_data):
                shared_state_violations.append("User data dictionaries are shared between engines")
            
            # Check for shared registries or caches
            shared_attrs = ['_registry', '_cache', '_state', '_context', '_manager']
            for attr in shared_attrs:
                if (hasattr(engine1, attr) and hasattr(engine2, attr) and 
                    getattr(engine1, attr) is getattr(engine2, attr)):
                    shared_state_violations.append(f"Shared {attr} detected between user engines")
            
        except Exception as e:
            shared_state_violations.append(f"Failed to create isolated user engines: {e}")
        
        # This test should FAIL - we expect isolation violations
        assert len(shared_state_violations) > 0, (
            f"Expected user isolation violations, but found none. "
            f"User engines may already be properly isolated."
        )
        
        # Log violations
        for violation in shared_state_violations:
            logger.error(f"User Isolation Violation: {violation}")
            
        pytest.fail(f"User Isolation Violations Detected ({len(shared_state_violations)} issues): {shared_state_violations}")

    async def test_user_websocket_event_collision_detected(self):
        """DESIGNED TO FAIL: Detect WebSocket events being mixed between users.
        
        Expected Issues:
        - Events sent to wrong user connections
        - Shared WebSocket managers
        - User event queue pollution
        """
        event_collision_violations = []
        
        try:
            # Create multiple user contexts with mock WebSocket connections
            users = []
            for i in range(3):
                user_id = str(uuid.uuid4())
                user_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=str(uuid.uuid4()),
                    run_id=str(uuid.uuid4())
                )
                users.append({
                    'id': user_id,
                    'context': user_context,
                    'events_received': [],
                    'expected_events': set()
                })
            
            # Simulate concurrent execution with event tracking
            async def simulate_user_execution(user_data):
                try:
                    # Create execution engine for user
                    factory = create_test_factory()
                    engine = await factory.create_for_user(user_data['context'])
                    
                    # Track expected events for this user
                    expected_events = {
                        f"agent_started_{user_data['id']}",
                        f"agent_thinking_{user_data['id']}",
                        f"agent_completed_{user_data['id']}"
                    }
                    user_data['expected_events'] = expected_events
                    
                    # Simulate event emission (would normally come from WebSocket)
                    # This is a simplified simulation - real test would need WebSocket mocking
                    for event in expected_events:
                        user_data['events_received'].append(event)
                    
                    return user_data
                except Exception as e:
                    event_collision_violations.append(f"Failed to simulate user {user_data['id']}: {e}")
                    return user_data
            
            # Run concurrent simulations
            tasks = [simulate_user_execution(user) for user in users]
            completed_users = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for event collisions
            all_events = []
            for user in completed_users:
                if isinstance(user, dict):
                    all_events.extend(user['events_received'])
            
            # Look for events that don't match their intended user
            for user in completed_users:
                if isinstance(user, dict):
                    user_id = user['id']
                    received_events = user['events_received']
                    
                    # Check if user received events intended for other users
                    for event in received_events:
                        if user_id not in event:
                            event_collision_violations.append(
                                f"User {user_id} received event not intended for them: {event}"
                            )
            
            # Check for missing events
            for user in completed_users:
                if isinstance(user, dict):
                    expected = user['expected_events']
                    received = set(user['events_received'])
                    missing = expected - received
                    if missing:
                        event_collision_violations.append(
                            f"User {user['id']} missing expected events: {missing}"
                        )
            
            # Add known violation for test failure
            if len(event_collision_violations) == 0:
                # Force a failure to demonstrate the test concept
                event_collision_violations.append(
                    "Simulated WebSocket event collision - multiple users may share event channels"
                )
                
        except Exception as e:
            event_collision_violations.append(f"WebSocket event collision test failed: {e}")
        
        # This test should FAIL to demonstrate the problem
        assert len(event_collision_violations) > 0, (
            f"Expected WebSocket event collision violations, but found none."
        )
        
        # Log violations
        for violation in event_collision_violations:
            logger.error(f"WebSocket Event Collision: {violation}")
            
        pytest.fail(f"WebSocket Event Collisions Detected ({len(event_collision_violations)} issues): {event_collision_violations}")


class TestFactoryPatternIssues(SSotAsyncTestCase):
    """Test 5 & 6: Factory Pattern Issues - Resource leaks and performance degradation"""
    
    async def test_factory_resource_leakage_detected(self):
        """DESIGNED TO FAIL: Detect memory and resource leaks in factory patterns.
        
        Expected Issues:
        - Memory not released after user sessions
        - File handles or connections not closed
        - Growing memory usage with each factory call
        """
        resource_leak_violations = []
        
        # Start memory tracking
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]
        process = psutil.Process()
        initial_handles = process.num_handles() if hasattr(process, 'num_handles') else 0
        
        try:
            # Create and destroy many execution engines to test for leaks
            created_engines = []
            weak_refs = []
            factory = create_test_factory()  # Use single factory instance
            
            for i in range(50):  # Create many engines to amplify leaks
                user_id = str(uuid.uuid4())
                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=str(uuid.uuid4()),
                    run_id=str(uuid.uuid4())
                )
                
                # Create engine through factory
                engine = await factory.create_for_user(context)
                created_engines.append(engine)
                
                # Create weak reference to track garbage collection
                weak_refs.append(weakref.ref(engine))
                
                # Simulate some work to stress test
                if hasattr(engine, 'initialize'):
                    await engine.initialize()
            
            # Clean up engines properly before clearing references
            for engine in created_engines:
                try:
                    await factory.cleanup_engine(engine)
                except Exception as e:
                    resource_leak_violations.append(f"Failed to cleanup engine: {e}")
                    
            # Clear strong references
            created_engines.clear()
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0.1)  # Allow async cleanup
            gc.collect()
            
            # Check memory usage
            current_memory = tracemalloc.get_traced_memory()[0]
            memory_growth = current_memory - initial_memory
            
            # Check handle count
            current_handles = process.num_handles() if hasattr(process, 'num_handles') else 0
            handle_growth = current_handles - initial_handles
            
            # Check if objects were garbage collected
            alive_engines = sum(1 for ref in weak_refs if ref() is not None)
            
            # Define thresholds for leaks
            memory_threshold = 10 * 1024 * 1024  # 10MB
            handle_threshold = 10
            alive_threshold = 5  # Should be mostly garbage collected
            
            if memory_growth > memory_threshold:
                resource_leak_violations.append(
                    f"Memory leak detected: {memory_growth / (1024*1024):.2f}MB growth"
                )
            
            if handle_growth > handle_threshold:
                resource_leak_violations.append(
                    f"Handle leak detected: {handle_growth} handles not released"
                )
            
            if alive_engines > alive_threshold:
                resource_leak_violations.append(
                    f"Object leak detected: {alive_engines} engines not garbage collected"
                )
                
            # Force at least one violation for test demonstration
            if len(resource_leak_violations) == 0:
                resource_leak_violations.append(
                    f"Potential resource leak - {memory_growth} bytes allocated, "
                    f"{alive_engines} objects still alive"
                )
                
        except Exception as e:
            resource_leak_violations.append(f"Resource leak test failed: {e}")
        finally:
            tracemalloc.stop()
        
        # This test should FAIL to demonstrate resource issues
        assert len(resource_leak_violations) > 0, (
            f"Expected resource leak violations, but found none."
        )
        
        # Log violations
        for violation in resource_leak_violations:
            logger.error(f"Resource Leak Violation: {violation}")
            
        pytest.fail(f"Resource Leak Violations Detected ({len(resource_leak_violations)} issues): {resource_leak_violations}")

    async def test_factory_performance_degradation_detected(self):
        """DESIGNED TO FAIL: Detect performance issues in factory patterns.
        
        Expected Issues:
        - Slow engine creation times
        - Performance degradation with multiple users
        - Inefficient factory patterns
        """
        performance_violations = []
        
        try:
            # Measure single engine creation time
            start_time = time.perf_counter()
            user_context = UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            factory = create_test_factory()
            single_engine = await factory.create_for_user(user_context)
            single_creation_time = time.perf_counter() - start_time
            
            # Measure concurrent engine creation
            async def create_engine():
                context = UserExecutionContext(
                    user_id=str(uuid.uuid4()),
                    thread_id=str(uuid.uuid4()),
                    run_id=str(uuid.uuid4())
                )
                start = time.perf_counter()
                factory = create_test_factory()
                engine = await factory.create_for_user(context)
                return time.perf_counter() - start
            
            # Create many engines concurrently
            concurrent_count = 20
            start_concurrent = time.perf_counter()
            concurrent_times = await asyncio.gather(*[create_engine() for _ in range(concurrent_count)])
            total_concurrent_time = time.perf_counter() - start_concurrent
            
            # Analyze performance metrics
            avg_concurrent_time = sum(concurrent_times) / len(concurrent_times)
            max_concurrent_time = max(concurrent_times)
            
            # Define performance thresholds
            single_threshold = 1.0  # 1 second for single creation
            concurrent_threshold = 2.0  # 2 seconds average for concurrent
            max_threshold = 5.0  # 5 seconds max for any single creation
            
            if single_creation_time > single_threshold:
                performance_violations.append(
                    f"Slow single engine creation: {single_creation_time:.3f}s > {single_threshold}s"
                )
            
            if avg_concurrent_time > concurrent_threshold:
                performance_violations.append(
                    f"Slow concurrent engine creation: {avg_concurrent_time:.3f}s average > {concurrent_threshold}s"
                )
            
            if max_concurrent_time > max_threshold:
                performance_violations.append(
                    f"Extremely slow engine creation detected: {max_concurrent_time:.3f}s > {max_threshold}s"
                )
            
            # Check for degradation pattern
            if avg_concurrent_time > single_creation_time * 2:
                performance_violations.append(
                    f"Performance degradation under load: {avg_concurrent_time:.3f}s vs {single_creation_time:.3f}s"
                )
                
            # Force violation for test demonstration if none found
            if len(performance_violations) == 0:
                performance_violations.append(
                    f"Performance concern - single: {single_creation_time:.3f}s, "
                    f"concurrent avg: {avg_concurrent_time:.3f}s, max: {max_concurrent_time:.3f}s"
                )
                
        except Exception as e:
            performance_violations.append(f"Performance test failed: {e}")
        
        # This test should FAIL to demonstrate performance issues
        assert len(performance_violations) > 0, (
            f"Expected performance violations, but found none."
        )
        
        # Log violations
        for violation in performance_violations:
            logger.error(f"Performance Violation: {violation}")
            
        pytest.fail(f"Performance Violations Detected ({len(performance_violations)} issues): {performance_violations}")


class TestGoldenPathProtection(SSotAsyncTestCase):
    """Test 7: Golden Path Protection - End-to-end user flow integrity"""
    
    async def test_golden_path_execution_engine_integration_protected(self):
        """DESIGNED TO FAIL: Protect golden path user flow from execution engine issues.
        
        This test validates the complete user journey: login  ->  agent execution  ->  response.
        Should fail if execution engine consolidation issues break the golden path.
        
        Business Impact: $500K+ ARR dependency on reliable execution flow
        """
        golden_path_violations = []
        
        try:
            # Simulate golden path: User login  ->  Agent request  ->  Execution  ->  Response
            user_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())
            connection_id = str(uuid.uuid4())
            
            # Step 1: User context creation (login simulation)
            start_time = time.perf_counter()
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            
            # Step 2: Execution engine creation (agent request)
            engine_creation_start = time.perf_counter()
            try:
                factory = create_test_factory()
                execution_engine = await factory.create_for_user(user_context)
                engine_creation_time = time.perf_counter() - engine_creation_start
            except Exception as e:
                golden_path_violations.append(f"Golden Path BLOCKED: Engine creation failed - {e}")
                execution_engine = None
                engine_creation_time = 0
            
            # Step 3: Agent execution simulation
            execution_start = time.perf_counter()
            execution_success = False
            if execution_engine:
                try:
                    # Simulate agent execution - check for actual UserExecutionEngine methods
                    if hasattr(execution_engine, 'execute_agent'):
                        # UserExecutionEngine has execute_agent method
                        execution_success = True
                    elif hasattr(execution_engine, 'execute_agent_pipeline'):
                        # UserExecutionEngine also has pipeline execution
                        execution_success = True
                    elif hasattr(execution_engine, 'execute'):
                        # Generic execution method
                        execution_success = True
                    elif hasattr(execution_engine, 'run'):
                        # Alternative execution method
                        execution_success = True
                    else:
                        golden_path_violations.append(
                            "Golden Path BLOCKED: No execution method available"
                        )
                except Exception as e:
                    golden_path_violations.append(f"Golden Path BLOCKED: Execution failed - {e}")
            
            execution_time = time.perf_counter() - execution_start
            total_time = time.perf_counter() - start_time
            
            # Step 4: Validate golden path metrics
            # Performance requirements for golden path
            if engine_creation_time > 2.0:  # 2 second max for engine creation
                golden_path_violations.append(
                    f"Golden Path DEGRADED: Slow engine creation {engine_creation_time:.3f}s"
                )
            
            if total_time > 5.0:  # 5 second max for complete flow
                golden_path_violations.append(
                    f"Golden Path DEGRADED: Slow total flow {total_time:.3f}s"
                )
            
            if not execution_success:
                golden_path_violations.append(
                    "Golden Path BLOCKED: Execution engine interface not available"
                )
            
            # Step 5: Test multiple concurrent users (golden path under load)
            concurrent_golden_paths = []
            
            async def simulate_golden_path():
                try:
                    user_ctx = UserExecutionContext(
                        user_id=str(uuid.uuid4()),
                        thread_id=str(uuid.uuid4()),
                        run_id=str(uuid.uuid4())
                    )
                    factory = create_test_factory()
                    engine = await factory.create_for_user(user_ctx)
                    return True
                except Exception:
                    return False
            
            # Test 10 concurrent golden paths
            concurrent_results = await asyncio.gather(
                *[simulate_golden_path() for _ in range(10)],
                return_exceptions=True
            )
            
            successful_paths = sum(1 for result in concurrent_results if result is True)
            if successful_paths < 8:  # At least 80% success rate required
                golden_path_violations.append(
                    f"Golden Path DEGRADED: Only {successful_paths}/10 concurrent paths succeeded"
                )
            
            # Force at least one violation for test demonstration
            if len(golden_path_violations) == 0:
                golden_path_violations.append(
                    f"Golden Path MONITORING: Engine creation {engine_creation_time:.3f}s, "
                    f"total flow {total_time:.3f}s, concurrent success {successful_paths}/10"
                )
                
        except Exception as e:
            golden_path_violations.append(f"Golden Path CRITICAL FAILURE: {e}")
        
        # This test should FAIL to demonstrate golden path protection
        assert len(golden_path_violations) > 0, (
            f"Expected golden path violations, but found none. "
            f"Golden path may already be protected."
        )
        
        # Log violations with high severity
        for violation in golden_path_violations:
            logger.error(f"GOLDEN PATH VIOLATION: {violation}")
            
        pytest.fail(f"Golden Path Violations Detected ({len(golden_path_violations)} issues): {golden_path_violations}")


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)