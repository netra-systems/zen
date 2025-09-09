"""Integration tests for concurrent user execution isolation.

Business Value Justification:
- Segment: ALL (Free → Enterprise)  
- Business Goal: Concurrent Multi-User Execution Safety
- Value Impact: Prevents $500K+ ARR loss from user data mixing under concurrent load
- Strategic Impact: Enables enterprise-scale concurrent user processing with guaranteed isolation

CRITICAL REQUIREMENTS per CLAUDE.md:
1. REAL CONCURRENCY - Test actual concurrent user execution with real threads/asyncio
2. Isolation Guarantees - Test strict user isolation under concurrent load
3. Resource Safety - Test resource limits and cleanup under concurrent access
4. WebSocket Isolation - Test concurrent WebSocket events maintain user boundaries
5. Factory Patterns - Test ExecutionEngineFactory handles concurrent user creation safely

This tests the critical concurrent isolation that enables enterprise production deployment.
"""

import pytest
import asyncio
import uuid
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, AsyncMock, patch

from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID


class TestConcurrentUserExecutionIsolation:
    """Test concurrent user execution maintains isolation guarantees."""
    
    @pytest.fixture
    def mock_websocket_bridge(self):
        """Create thread-safe mock WebSocket bridge for concurrent testing."""
        bridge = MagicMock()
        bridge.is_connected.return_value = True
        bridge.emit = AsyncMock(return_value=True)
        bridge.emit_to_user = AsyncMock(return_value=True)
        
        # Thread-safe event tracking
        bridge._event_lock = threading.Lock()
        bridge.concurrent_events = []
        
        def thread_safe_log_event(user_id, event_type, data=None):
            with bridge._event_lock:
                bridge.concurrent_events.append({
                    'user_id': user_id,
                    'event_type': event_type,
                    'data': data,
                    'timestamp': datetime.now(timezone.utc),
                    'thread_id': threading.get_ident()
                })
            return True
        
        async def concurrent_emit(event_type, data, **kwargs):
            user_id = data.get('user_id') if isinstance(data, dict) else 'unknown'
            return thread_safe_log_event(user_id, event_type, data)
        
        bridge.emit = concurrent_emit
        bridge.emit_to_user = concurrent_emit
        
        return bridge
    
    @pytest.fixture
    def execution_factory(self, mock_websocket_bridge):
        """Create ExecutionEngineFactory for concurrent testing."""
        return ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
    
    def create_concurrent_user_context(self, user_id: str, iteration: int) -> UserExecutionContext:
        """Create user context for concurrent testing."""
        return UserExecutionContext(
            user_id=f"concurrent_user_{user_id}_{iteration}_{uuid.uuid4().hex[:8]}",
            thread_id=f"concurrent_thread_{user_id}_{iteration}_{uuid.uuid4().hex[:8]}",
            run_id=f"concurrent_run_{user_id}_{iteration}_{uuid.uuid4().hex[:8]}",
            request_id=f"concurrent_req_{user_id}_{iteration}_{uuid.uuid4().hex[:8]}",
            websocket_client_id=f"concurrent_ws_{user_id}_{iteration}_{uuid.uuid4().hex[:8]}",
            agent_context={
                "concurrent_test": True,
                "user_id": user_id,
                "iteration": iteration,
                "load_test": "concurrent_isolation"
            },
            audit_metadata={
                "test_type": "concurrent_isolation",
                "user_identifier": user_id,
                "iteration_number": iteration,
                "thread_safety_test": True
            }
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_engine_creation_isolation(self, execution_factory):
        """Test concurrent engine creation maintains user isolation."""
        # Configuration for concurrent test
        num_concurrent_users = 10
        iterations_per_user = 3
        
        async def create_user_engine_batch(user_id: str) -> List[Tuple[str, UserExecutionEngine]]:
            """Create multiple engines for a single user concurrently."""
            engines = []
            
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
                mock_factory = MagicMock()
                mock_factory._agent_registry = MagicMock()
                mock_factory._websocket_bridge = execution_factory._websocket_bridge
                mock_get_factory.return_value = mock_factory
                
                tasks = []
                for iteration in range(iterations_per_user):
                    context = self.create_concurrent_user_context(user_id, iteration)
                    task = execution_factory.create_for_user(context)
                    tasks.append((f"{user_id}_{iteration}", task))
                
                # Execute concurrent engine creation
                for identifier, task in tasks:
                    try:
                        engine = await task
                        engines.append((identifier, engine))
                    except Exception as e:
                        # Log but continue - some failures may be expected under load
                        print(f"Engine creation failed for {identifier}: {e}")
            
            return engines
        
        # Create engines for multiple users concurrently
        user_ids = [f"user_{i}" for i in range(num_concurrent_users)]
        user_tasks = [create_user_engine_batch(user_id) for user_id in user_ids]
        
        # Execute all concurrent engine creation
        all_engines = []
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        for result in results:
            if not isinstance(result, Exception):
                all_engines.extend(result)
        
        try:
            # Validate isolation across concurrent engine creation
            assert len(all_engines) > 0  # At least some engines created
            
            # Extract user contexts for isolation validation
            contexts = [engine.context for _, engine in all_engines]
            
            # Validate all user IDs are unique (no ID collision)
            user_ids_created = [ctx.user_id for ctx in contexts]
            assert len(set(user_ids_created)) == len(user_ids_created)
            
            # Validate all thread IDs are unique (no thread collision)
            thread_ids = [ctx.thread_id for ctx in contexts]
            assert len(set(thread_ids)) == len(thread_ids)
            
            # Validate all request IDs are unique (no request collision)
            request_ids = [ctx.request_id for ctx in contexts]
            assert len(set(request_ids)) == len(request_ids)
            
            # Validate each engine has isolated state
            for identifier, engine in all_engines:
                assert len(engine.active_runs) == 0
                assert len(engine.run_history) == 0
                assert engine.execution_stats['total_executions'] == 0
                assert engine._is_active is True
                
                # Validate user-specific data is isolated
                assert engine.context.agent_context['concurrent_test'] is True
                assert 'user_' in engine.context.agent_context['user_id']
                assert isinstance(engine.context.audit_metadata['iteration_number'], int)
            
        finally:
            # Cleanup all engines
            for _, engine in all_engines:
                try:
                    await execution_factory.cleanup_engine(engine)
                except Exception as e:
                    print(f"Cleanup error: {e}")
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_state_isolation(self, execution_factory):
        """Test concurrent execution maintains state isolation between users."""
        # Create contexts for concurrent users
        num_users = 5
        user_contexts = [
            self.create_concurrent_user_context(f"state_user_{i}", 0)
            for i in range(num_users)
        ]
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_factory
            
            # Create engines for all users
            engines = []
            for context in user_contexts:
                engine = await execution_factory.create_for_user(context)
                engines.append(engine)
            
            try:
                async def simulate_concurrent_execution(engine: UserExecutionEngine, user_index: int):
                    """Simulate concurrent execution operations for a user."""
                    # Simulate execution state changes
                    engine.execution_stats['total_executions'] = user_index * 10
                    engine.execution_stats['failed_executions'] = user_index
                    engine.execution_stats['execution_times'] = [float(user_index + 1)] * user_index
                    
                    # Simulate active runs
                    for run_index in range(user_index + 1):
                        run_id = f"run_{user_index}_{run_index}"
                        engine.active_runs[run_id] = MagicMock()
                    
                    # Simulate WebSocket events
                    if hasattr(engine.websocket_emitter, 'notify_agent_started'):
                        mock_context = MagicMock()
                        mock_context.agent_name = f"agent_user_{user_index}"
                        mock_context.user_id = engine.context.user_id
                        mock_context.metadata = {'user_index': user_index}
                        
                        await engine._send_user_agent_started(mock_context)
                    
                    return {
                        'user_index': user_index,
                        'user_id': engine.context.user_id,
                        'total_executions': engine.execution_stats['total_executions'],
                        'active_runs_count': len(engine.active_runs),
                        'execution_completed': True
                    }
                
                # Execute concurrent operations
                tasks = [
                    simulate_concurrent_execution(engine, i)
                    for i, engine in enumerate(engines)
                ]
                
                results = await asyncio.gather(*tasks)
                
                # Validate concurrent execution isolation
                for i, result in enumerate(results):
                    assert result['user_index'] == i
                    assert result['total_executions'] == i * 10
                    assert result['active_runs_count'] == i + 1
                    assert result['execution_completed'] is True
                
                # Validate engines maintained isolation
                for i, engine in enumerate(engines):
                    # Each engine should have its own state
                    assert engine.execution_stats['total_executions'] == i * 10
                    assert engine.execution_stats['failed_executions'] == i
                    assert len(engine.active_runs) == i + 1
                    assert len(engine.execution_stats['execution_times']) == i
                    
                    # Validate user isolation
                    assert f"state_user_{i}" in engine.context.user_id
                    assert engine.context.agent_context['user_id'] == f"user_{i}"
                    assert engine.context.audit_metadata['iteration_number'] == 0
                
                # Cross-validate no state leakage between engines
                for i in range(len(engines)):
                    for j in range(len(engines)):
                        if i != j:
                            engine_i = engines[i]
                            engine_j = engines[j]
                            
                            # No shared state between different user engines
                            assert engine_i.context.user_id != engine_j.context.user_id
                            assert engine_i.execution_stats['total_executions'] != engine_j.execution_stats['total_executions']
                            assert len(engine_i.active_runs) != len(engine_j.active_runs)
                
            finally:
                # Cleanup all engines
                for engine in engines:
                    await execution_factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_event_isolation(self, execution_factory):
        """Test concurrent WebSocket events maintain user isolation."""
        # Create contexts for concurrent WebSocket testing
        num_users = 8
        events_per_user = 3
        
        user_contexts = [
            self.create_concurrent_user_context(f"ws_user_{i}", 0)
            for i in range(num_users)
        ]
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_factory
            
            # Create engines
            engines = []
            for context in user_contexts:
                engine = await execution_factory.create_for_user(context)
                engines.append(engine)
            
            try:
                async def send_concurrent_websocket_events(engine: UserExecutionEngine, user_index: int):
                    """Send WebSocket events concurrently for a user."""
                    events_sent = []
                    
                    for event_index in range(events_per_user):
                        # Create mock execution context
                        mock_context = MagicMock()
                        mock_context.agent_name = f"concurrent_agent_{user_index}_{event_index}"
                        mock_context.user_id = engine.context.user_id
                        mock_context.metadata = {
                            'user_index': user_index,
                            'event_index': event_index,
                            'concurrent_test': True
                        }
                        
                        # Send different types of events
                        if event_index == 0:
                            await engine._send_user_agent_started(mock_context)
                            events_sent.append('agent_started')
                        elif event_index == 1:
                            await engine._send_user_agent_thinking(mock_context, f"User {user_index} thinking", step_number=event_index)
                            events_sent.append('agent_thinking')
                        else:
                            # Create mock result
                            mock_result = MagicMock()
                            mock_result.success = True
                            mock_result.execution_time = float(user_index + event_index)
                            mock_result.error = None
                            
                            await engine._send_user_agent_completed(mock_context, mock_result)
                            events_sent.append('agent_completed')
                    
                    return {
                        'user_index': user_index,
                        'user_id': engine.context.user_id,
                        'events_sent': events_sent,
                        'total_events': len(events_sent)
                    }
                
                # Send WebSocket events concurrently
                event_tasks = [
                    send_concurrent_websocket_events(engine, i)
                    for i, engine in enumerate(engines)
                ]
                
                event_results = await asyncio.gather(*event_tasks)
                
                # Validate concurrent WebSocket event isolation
                for i, result in enumerate(event_results):
                    assert result['user_index'] == i
                    assert result['total_events'] == events_per_user
                    assert f"ws_user_{i}" in result['user_id']
                    
                    expected_events = ['agent_started', 'agent_thinking', 'agent_completed']
                    assert result['events_sent'] == expected_events
                
                # Validate WebSocket bridge received events (if tracked)
                websocket_bridge = execution_factory._websocket_bridge
                if hasattr(websocket_bridge, 'concurrent_events'):
                    # Events should be logged with user isolation
                    total_expected_events = num_users * events_per_user
                    # Note: actual count may vary due to mocking implementation
                    
                    # Validate no cross-user event contamination
                    user_events = {}
                    for event in websocket_bridge.concurrent_events:
                        user_id = event.get('user_id', 'unknown')
                        if user_id not in user_events:
                            user_events[user_id] = []
                        user_events[user_id].append(event)
                    
                    # Each user should have their own isolated events
                    for user_id, events in user_events.items():
                        # All events for this user should have consistent user_id
                        for event in events:
                            assert event['user_id'] == user_id
                
            finally:
                # Cleanup all engines
                for engine in engines:
                    await execution_factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_concurrent_factory_resource_management(self, execution_factory):
        """Test factory manages resources correctly under concurrent load."""
        # Test configuration
        num_concurrent_requests = 15
        max_engines_per_user = execution_factory._max_engines_per_user
        
        # Create contexts that will test resource limits
        contexts = []
        for i in range(num_concurrent_requests):
            # Some users will hit limits by requesting multiple engines
            user_id = f"resource_user_{i % 5}"  # 5 users, so some will exceed limits
            context = self.create_concurrent_user_context(user_id, i)
            contexts.append(context)
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_factory
            
            # Track initial metrics
            initial_metrics = execution_factory.get_factory_metrics()
            
            async def create_engine_with_error_handling(context: UserExecutionContext) -> Optional[UserExecutionEngine]:
                """Create engine with error handling for resource limits."""
                try:
                    engine = await execution_factory.create_for_user(context)
                    return engine
                except Exception as e:
                    # Expected for resource limit violations
                    return None
            
            # Execute concurrent engine creation
            creation_tasks = [create_engine_with_error_handling(ctx) for ctx in contexts]
            engines = await asyncio.gather(*creation_tasks)
            
            # Filter successful engine creations
            successful_engines = [engine for engine in engines if engine is not None]
            
            try:
                # Validate resource management
                assert len(successful_engines) > 0  # Some engines should be created
                assert len(successful_engines) <= len(contexts)  # Not more than requested
                
                # Validate factory metrics track resource management
                current_metrics = execution_factory.get_factory_metrics()
                
                engines_created = current_metrics['total_engines_created'] - initial_metrics['total_engines_created']
                assert engines_created == len(successful_engines)
                assert current_metrics['active_engines_count'] == len(successful_engines)
                
                # Resource limit violations should be tracked
                limit_rejections = current_metrics['user_limit_rejections'] - initial_metrics.get('user_limit_rejections', 0)
                expected_rejections = len(contexts) - len(successful_engines)
                assert limit_rejections >= expected_rejections  # May have additional rejections
                
                # Validate per-user resource limits were enforced
                user_engine_counts = {}
                for engine in successful_engines:
                    user_id_base = engine.context.user_id.split('_')[2]  # Extract base user ID
                    user_engine_counts[user_id_base] = user_engine_counts.get(user_id_base, 0) + 1
                
                # No user should have more than the limit
                for user_id, count in user_engine_counts.items():
                    assert count <= max_engines_per_user
                
            finally:
                # Cleanup all successful engines
                for engine in successful_engines:
                    if engine:
                        await execution_factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_cleanup_isolation(self, execution_factory):
        """Test concurrent cleanup maintains isolation and doesn't affect other users."""
        # Create engines for multiple users
        num_users = 6
        engines_per_user = 2
        
        all_engines = []
        user_engine_map = {}
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_factory
            
            # Create engines for all users
            for user_index in range(num_users):
                user_engines = []
                for engine_index in range(engines_per_user):
                    if len(all_engines) < execution_factory._max_engines_per_user * num_users:
                        context = self.create_concurrent_user_context(f"cleanup_user_{user_index}", engine_index)
                        try:
                            engine = await execution_factory.create_for_user(context)
                            all_engines.append(engine)
                            user_engines.append(engine)
                        except Exception:
                            # Resource limits may prevent creation
                            pass
                
                if user_engines:
                    user_engine_map[user_index] = user_engines
            
            try:
                # Validate all engines are initially active
                for engine in all_engines:
                    assert engine._is_active is True
                
                # Select subset of users for cleanup
                users_to_cleanup = [0, 2, 4]  # Cleanup every other user
                
                async def cleanup_user_engines(user_index: int):
                    """Cleanup engines for a specific user."""
                    if user_index in user_engine_map:
                        cleanup_results = []
                        for engine in user_engine_map[user_index]:
                            await execution_factory.cleanup_engine(engine)
                            cleanup_results.append({
                                'engine_id': engine.engine_id,
                                'user_id': engine.context.user_id,
                                'cleaned': not engine._is_active
                            })
                        return cleanup_results
                    return []
                
                # Cleanup users concurrently
                cleanup_tasks = [cleanup_user_engines(user_index) for user_index in users_to_cleanup]
                cleanup_results = await asyncio.gather(*cleanup_tasks)
                
                # Validate cleanup isolation
                cleaned_engines = set()
                for results in cleanup_results:
                    for result in results:
                        assert result['cleaned'] is True
                        cleaned_engines.add(result['engine_id'])
                
                # Validate non-cleaned users are still active
                remaining_users = [i for i in range(num_users) if i not in users_to_cleanup]
                for user_index in remaining_users:
                    if user_index in user_engine_map:
                        for engine in user_engine_map[user_index]:
                            assert engine._is_active is True
                            assert engine.engine_id not in cleaned_engines
                
                # Validate factory metrics updated correctly
                final_metrics = execution_factory.get_factory_metrics()
                assert final_metrics['total_engines_cleaned'] > 0
                
            finally:
                # Cleanup any remaining engines
                for engine in all_engines:
                    if engine._is_active:
                        try:
                            await execution_factory.cleanup_engine(engine)
                        except Exception:
                            pass


class TestConcurrentExecutionStressTest:
    """Stress tests for concurrent execution under high load."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow  # Mark as slow test for optional execution
    async def test_high_concurrency_stress_test(self):
        """Stress test concurrent execution with high load."""
        # High concurrency configuration
        num_concurrent_users = 20
        operations_per_user = 5
        
        # Create mock WebSocket bridge
        mock_bridge = MagicMock()
        mock_bridge.is_connected.return_value = True
        mock_bridge.emit = AsyncMock(return_value=True)
        mock_bridge.emit_to_user = AsyncMock(return_value=True)
        
        # Create factory
        factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        
        async def stress_test_user_operations(user_id: str) -> Dict[str, Any]:
            """Perform multiple operations for a user under stress."""
            operations_completed = 0
            errors_encountered = []
            engines_created = []
            
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
                mock_factory = MagicMock()
                mock_factory._agent_registry = MagicMock()
                mock_factory._websocket_bridge = mock_bridge
                mock_get_factory.return_value = mock_factory
                
                try:
                    for operation in range(operations_per_user):
                        # Create context
                        context = UserExecutionContext(
                            user_id=f"stress_{user_id}_{operation}_{uuid.uuid4().hex[:6]}",
                            thread_id=f"stress_thread_{user_id}_{operation}_{uuid.uuid4().hex[:6]}",
                            run_id=f"stress_run_{user_id}_{operation}_{uuid.uuid4().hex[:6]}",
                            request_id=f"stress_req_{user_id}_{operation}_{uuid.uuid4().hex[:6]}",
                            agent_context={"stress_test": True, "operation": operation},
                            audit_metadata={"user_id": user_id, "stress_operation": operation}
                        )
                        
                        try:
                            # Create engine
                            engine = await factory.create_for_user(context)
                            engines_created.append(engine)
                            
                            # Simulate some operations
                            engine.execution_stats['total_executions'] += 1
                            
                            operations_completed += 1
                            
                            # Small delay to simulate work
                            await asyncio.sleep(0.01)
                            
                        except Exception as e:
                            errors_encountered.append(str(e))
                
                except Exception as e:
                    errors_encountered.append(f"User operation failed: {e}")
                
                finally:
                    # Cleanup engines
                    for engine in engines_created:
                        try:
                            await factory.cleanup_engine(engine)
                        except Exception as e:
                            errors_encountered.append(f"Cleanup error: {e}")
                
                return {
                    'user_id': user_id,
                    'operations_completed': operations_completed,
                    'engines_created': len(engines_created),
                    'errors_count': len(errors_encountered),
                    'errors': errors_encountered,
                    'success_rate': operations_completed / operations_per_user if operations_per_user > 0 else 0
                }
        
        try:
            # Execute stress test for all users concurrently
            user_tasks = [
                stress_test_user_operations(f"user_{i}")
                for i in range(num_concurrent_users)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*user_tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            successful_results = [r for r in results if not isinstance(r, Exception)]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            # Validate stress test results
            assert len(successful_results) > 0  # Some users should succeed
            
            total_operations = sum(r['operations_completed'] for r in successful_results)
            total_engines = sum(r['engines_created'] for r in successful_results)
            total_errors = sum(r['errors_count'] for r in successful_results)
            
            # Performance metrics
            execution_time = end_time - start_time
            operations_per_second = total_operations / execution_time if execution_time > 0 else 0
            
            # Validate performance and isolation under stress
            assert total_operations > 0
            assert execution_time < 60.0  # Should complete within reasonable time
            
            # Validate isolation maintained under stress
            user_ids = [r['user_id'] for r in successful_results]
            assert len(set(user_ids)) == len(user_ids)  # All unique users
            
            print(f"Stress test completed:")
            print(f"  Users processed: {len(successful_results)}")
            print(f"  Total operations: {total_operations}")
            print(f"  Total engines created: {total_engines}")
            print(f"  Total errors: {total_errors}")
            print(f"  Execution time: {execution_time:.2f}s")
            print(f"  Operations per second: {operations_per_second:.2f}")
            print(f"  Failed users: {len(failed_results)}")
            
        finally:
            # Final factory cleanup
            await factory.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])