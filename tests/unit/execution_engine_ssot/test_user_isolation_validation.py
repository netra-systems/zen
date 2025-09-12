#!/usr/bin/env python
"""
UNIT TEST 1: UserExecutionEngine User Isolation Validation

PURPOSE: Test that UserExecutionEngine instances don't share state between different users.
This test validates the SSOT requirement that each user has completely isolated execution context.

Expected to FAIL before SSOT consolidation (proves problem exists)
Expected to PASS after SSOT consolidation (proves UserExecutionEngine works)

Business Impact: $500K+ ARR Golden Path protection - user isolation prevents data leaks
"""

import asyncio
import gc
import sys
import os
import threading
import time
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from unittest.mock import Mock, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class MockWebSocketManager:
    """Mock WebSocket manager for testing user isolation"""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events_sent = []
        self.send_agent_event = AsyncMock(side_effect=self._record_event)
    
    async def _record_event(self, event_type: str, data: Dict[str, Any]):
        """Record events sent for validation"""
        self.events_sent.append({
            'event_type': event_type,
            'data': data,
            'user_id': self.user_id,
            'timestamp': time.time()
        })


class TestUserExecutionEngineIsolationValidation(SSotAsyncTestCase):
    """Unit Test 1: Validate UserExecutionEngine user isolation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_users = [
            {'id': f'user_{i}', 'session': f'session_{i}'} 
            for i in range(5)
        ]
        
    async def test_user_state_isolation_complete(self):
        """Test that user states are completely isolated between UserExecutionEngine instances"""
        print("\n SEARCH:  Testing user state isolation in UserExecutionEngine...")
        
        try:
            # Import here to catch import errors
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        isolation_violations = []
        engines = {}
        
        # Create engines for different users
        for user in self.test_users:
            mock_ws = MockWebSocketManager(user['id'])
            
            try:
                engine = UserExecutionEngine(
                    user_id=user['id'],
                    session_id=user['session'],
                    websocket_manager=mock_ws
                )
                engines[user['id']] = {
                    'engine': engine,
                    'websocket': mock_ws
                }
            except Exception as e:
                isolation_violations.append(f"Failed to create engine for {user['id']}: {e}")
        
        if not engines:
            self.fail("No engines could be created for testing")
        
        # Test 1: User ID isolation
        user_ids = set()
        for user_id, data in engines.items():
            engine_user_id = getattr(data['engine'], 'user_id', None)
            if engine_user_id in user_ids:
                isolation_violations.append(f"Duplicate user_id detected: {engine_user_id}")
            user_ids.add(engine_user_id)
            
            if engine_user_id != user_id:
                isolation_violations.append(f"Engine user_id mismatch: expected {user_id}, got {engine_user_id}")
        
        print(f"   PASS:  Created {len(engines)} engines with unique user IDs")
        
        # Test 2: Session ID isolation
        session_ids = set()
        for user_id, data in engines.items():
            engine_session_id = getattr(data['engine'], 'session_id', None)
            if engine_session_id in session_ids:
                isolation_violations.append(f"Duplicate session_id detected: {engine_session_id}")
            session_ids.add(engine_session_id)
        
        print(f"   PASS:  All engines have unique session IDs")
        
        # Test 3: WebSocket manager isolation
        websocket_managers = set()
        for user_id, data in engines.items():
            ws_manager = getattr(data['engine'], 'websocket_manager', None)
            ws_id = id(ws_manager)
            if ws_id in websocket_managers:
                isolation_violations.append(f"Shared WebSocket manager detected for {user_id}")
            websocket_managers.add(ws_id)
        
        print(f"   PASS:  All engines have isolated WebSocket managers")
        
        # Test 4: User context isolation
        for user_id, data in engines.items():
            engine = data['engine']
            if hasattr(engine, 'get_user_context'):
                try:
                    context = engine.get_user_context()
                    if context.get('user_id') != user_id:
                        isolation_violations.append(f"User context mismatch for {user_id}")
                except Exception as e:
                    isolation_violations.append(f"Failed to get user context for {user_id}: {e}")
        
        print(f"   PASS:  User contexts properly isolated")
        
        # Test 5: Check for shared mutable objects
        shared_objects = []
        engine_vars = {}
        
        for user_id, data in engines.items():
            engine = data['engine']
            if hasattr(engine, '__dict__'):
                engine_vars[user_id] = vars(engine)
        
        # Compare engine variables for shared references
        user_pairs = [(u1, u2) for u1 in engine_vars.keys() for u2 in engine_vars.keys() if u1 < u2]
        
        for user1, user2 in user_pairs:
            vars1 = engine_vars[user1]
            vars2 = engine_vars[user2]
            
            for attr1, value1 in vars1.items():
                for attr2, value2 in vars2.items():
                    if (attr1 == attr2 and value1 is value2 and 
                        not isinstance(value1, (str, int, float, bool, type(None), tuple, frozenset))):
                        shared_objects.append(f"Shared mutable object {attr1} between {user1} and {user2}")
        
        if shared_objects:
            isolation_violations.extend(shared_objects)
        else:
            print(f"   PASS:  No shared mutable objects detected")
        
        # Test 6: Concurrent modification isolation
        async def modify_user_data(user_id: str, engine: Any):
            """Modify user-specific data in parallel"""
            try:
                # Try to set user-specific data
                if hasattr(engine, '_user_data'):
                    engine._user_data = {'test_key': f'value_for_{user_id}'}
                elif hasattr(engine, 'user_data'):
                    engine.user_data = {'test_key': f'value_for_{user_id}'}
                
                # Send a user-specific event
                await engine.send_websocket_event('test_isolation', {
                    'user_id': user_id,
                    'test_data': f'isolation_test_{user_id}'
                })
                
                return f"success_{user_id}"
            except Exception as e:
                return f"error_{user_id}_{e}"
        
        # Run concurrent modifications
        modification_tasks = []
        for user_id, data in engines.items():
            task = modify_user_data(user_id, data['engine'])
            modification_tasks.append(task)
        
        modification_results = await asyncio.gather(*modification_tasks, return_exceptions=True)
        
        # Verify modifications didn't interfere with each other
        for i, result in enumerate(modification_results):
            user_id = self.test_users[i]['id']
            if not isinstance(result, str) or not result.startswith('success'):
                isolation_violations.append(f"Concurrent modification failed for {user_id}: {result}")
        
        print(f"   PASS:  Concurrent modifications completed without interference")
        
        # Validate WebSocket event isolation
        for user_id, data in engines.items():
            websocket = data['websocket']
            events = websocket.events_sent
            
            # Each user should have exactly one event
            if len(events) != 1:
                isolation_violations.append(f"User {user_id} has {len(events)} events, expected 1")
            elif events[0]['data']['user_id'] != user_id:
                isolation_violations.append(f"User {user_id} received event for different user")
        
        print(f"   PASS:  WebSocket events properly isolated")
        
        # CRITICAL: This test should PASS after SSOT consolidation
        # If violations are found, UserExecutionEngine isolation is broken
        if isolation_violations:
            self.fail(f"User isolation violations detected: {isolation_violations}")
        
        print(f"   PASS:  All {len(engines)} UserExecutionEngine instances properly isolated")
    
    async def test_user_memory_isolation_no_leaks(self):
        """Test that user engine instances don't leak memory between users"""
        print("\n SEARCH:  Testing memory isolation and leak prevention...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        memory_violations = []
        
        # Create and destroy engines to test for memory leaks
        weak_refs = []
        
        for i in range(10):
            user_id = f'temp_user_{i}'
            mock_ws = MockWebSocketManager(user_id)
            
            try:
                engine = UserExecutionEngine(
                    user_id=user_id,
                    session_id=f'temp_session_{i}',
                    websocket_manager=mock_ws
                )
                
                # Create weak reference to track garbage collection
                weak_refs.append(weakref.ref(engine))
                
                # Do some work with the engine
                context = engine.get_user_context() if hasattr(engine, 'get_user_context') else {}
                await engine.send_websocket_event('test_memory', {'data': f'test_{i}'})
                
                # Explicitly delete the engine
                del engine
                
            except Exception as e:
                memory_violations.append(f"Failed to create/test engine {i}: {e}")
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow async cleanup
        gc.collect()
        
        # Check if engines were properly garbage collected
        alive_engines = sum(1 for ref in weak_refs if ref() is not None)
        
        if alive_engines > 2:  # Allow for some GC delay
            memory_violations.append(f"Memory leak: {alive_engines} engines not garbage collected")
        else:
            print(f"   PASS:  {len(weak_refs) - alive_engines}/{len(weak_refs)} engines properly garbage collected")
        
        # Test rapid creation/destruction for stress testing
        for batch in range(3):
            batch_engines = []
            for i in range(5):
                user_id = f'batch_{batch}_user_{i}'
                mock_ws = MockWebSocketManager(user_id)
                
                try:
                    engine = UserExecutionEngine(
                        user_id=user_id,
                        session_id=f'batch_{batch}_session_{i}',
                        websocket_manager=mock_ws
                    )
                    batch_engines.append(engine)
                except Exception as e:
                    memory_violations.append(f"Batch {batch} engine {i} creation failed: {e}")
            
            # Clear batch
            batch_engines.clear()
            gc.collect()
        
        print(f"   PASS:  Stress test completed - rapid creation/destruction")
        
        # CRITICAL: Memory violations indicate SSOT implementation problems
        if memory_violations:
            self.fail(f"Memory isolation violations: {memory_violations}")
        
        print(f"   PASS:  Memory isolation validated - no leaks detected")
    
    async def test_user_thread_safety_validation(self):
        """Test that UserExecutionEngine is thread-safe for concurrent users"""
        print("\n SEARCH:  Testing thread safety for concurrent user access...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        thread_safety_violations = []
        shared_data = {
            'engines_created': 0,
            'events_sent': 0,
            'errors': []
        }
        lock = threading.Lock()
        
        def create_and_test_engine(user_index: int):
            """Thread worker function"""
            user_id = f'thread_user_{user_index}'
            mock_ws = MockWebSocketManager(user_id)
            
            try:
                # Create engine
                engine = UserExecutionEngine(
                    user_id=user_id,
                    session_id=f'thread_session_{user_index}',
                    websocket_manager=mock_ws
                )
                
                with lock:
                    shared_data['engines_created'] += 1
                
                # Test basic operations
                context = engine.get_user_context() if hasattr(engine, 'get_user_context') else {}
                
                # Test async operation in thread
                async def send_event():
                    await engine.send_websocket_event('thread_test', {
                        'thread_id': threading.current_thread().ident,
                        'user_id': user_id
                    })
                
                # Run async operation
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(send_event())
                    with lock:
                        shared_data['events_sent'] += 1
                finally:
                    loop.close()
                
                return f"success_{user_index}"
                
            except Exception as e:
                with lock:
                    shared_data['errors'].append(f"Thread {user_index}: {e}")
                return f"error_{user_index}"
        
        # Create multiple threads
        num_threads = 8
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_user = {
                executor.submit(create_and_test_engine, i): i 
                for i in range(num_threads)
            }
            
            # Wait for completion
            results = {}
            for future in future_to_user:
                user_index = future_to_user[future]
                try:
                    result = future.result(timeout=30)
                    results[user_index] = result
                except Exception as e:
                    thread_safety_violations.append(f"Thread {user_index} exception: {e}")
        
        # Validate results
        if shared_data['errors']:
            thread_safety_violations.extend(shared_data['errors'])
        
        expected_engines = num_threads
        expected_events = num_threads
        
        if shared_data['engines_created'] != expected_engines:
            thread_safety_violations.append(
                f"Expected {expected_engines} engines, got {shared_data['engines_created']}"
            )
        
        if shared_data['events_sent'] != expected_events:
            thread_safety_violations.append(
                f"Expected {expected_events} events, got {shared_data['events_sent']}"
            )
        
        success_count = sum(1 for result in results.values() if result.startswith('success'))
        if success_count != num_threads:
            thread_safety_violations.append(f"Only {success_count}/{num_threads} threads succeeded")
        
        print(f"   PASS:  {success_count}/{num_threads} threads completed successfully")
        print(f"   PASS:  {shared_data['engines_created']} engines created")
        print(f"   PASS:  {shared_data['events_sent']} events sent")
        
        # CRITICAL: Thread safety violations indicate SSOT implementation problems
        if thread_safety_violations:
            self.fail(f"Thread safety violations: {thread_safety_violations}")
        
        print(f"   PASS:  Thread safety validated for concurrent user access")


if __name__ == '__main__':
    unittest.main(verbosity=2)