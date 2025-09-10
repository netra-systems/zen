#!/usr/bin/env python
"""
INTEGRATION TEST 5: Multi-User Execution Validation for SSOT

PURPOSE: Test concurrent UserExecutionEngine instances for multiple users with real isolation.
This validates the SSOT requirement that users are completely isolated in real execution scenarios.

Expected to FAIL before SSOT consolidation (proves multi-user issues in current engines)
Expected to PASS after SSOT consolidation (proves UserExecutionEngine handles multi-user correctly)

Business Impact: $500K+ ARR Golden Path protection - multi-user isolation prevents data leaks and conflicts
Integration Level: Tests with real threading, real async, real WebSocket events (NO DOCKER)
"""

import asyncio
import concurrent.futures
import sys
import os
import threading
import time
import uuid
from typing import Dict, List, Any, Set
from collections import defaultdict, Counter

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class RealWebSocketSimulator:
    """Simulates real WebSocket behavior for integration testing"""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.events_received = []
        self.connection_status = "connected"
        self.send_agent_event = AsyncMock(side_effect=self._handle_event)
        self._lock = threading.Lock()
        
    async def _handle_event(self, event_type: str, data: Dict[str, Any]):
        """Handle WebSocket event with real threading concerns"""
        with self._lock:
            timestamp = time.time()
            thread_id = threading.current_thread().ident
            
            event_record = {
                'event_type': event_type,
                'data': data,
                'user_id': self.user_id,
                'connection_id': self.connection_id,
                'timestamp': timestamp,
                'thread_id': thread_id,
                'order': len(self.events_received)
            }
            
            self.events_received.append(event_record)
            
            # Simulate real WebSocket latency
            await asyncio.sleep(0.001)
    
    def get_user_events(self) -> List[Dict[str, Any]]:
        """Get events for this user only"""
        with self._lock:
            return [event for event in self.events_received if event['user_id'] == self.user_id]
    
    def has_cross_user_contamination(self, expected_user_id: str) -> List[str]:
        """Check for events from other users"""
        contamination = []
        with self._lock:
            for event in self.events_received:
                if event['user_id'] != expected_user_id:
                    contamination.append(f"Event from {event['user_id']} received by {expected_user_id}")
        return contamination


class TestMultiUserExecutionValidation(SSotAsyncTestCase):
    """Integration Test 5: Validate multi-user execution with UserExecutionEngine SSOT"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_users = [
            {
                'user_id': f'integration_user_{i}',
                'session_id': f'integration_session_{i}',
                'connection_id': str(uuid.uuid4())
            }
            for i in range(10)  # Test with 10 concurrent users
        ]
        
    async def test_concurrent_user_execution_isolation(self):
        """Test that concurrent users are completely isolated during execution"""
        print("\n🔍 Testing concurrent user execution isolation...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        isolation_violations = []
        user_engines = {}
        user_websockets = {}
        
        # Create engines for all users
        for user_data in self.test_users:
            user_id = user_data['user_id']
            websocket = RealWebSocketSimulator(user_id, user_data['connection_id'])
            
            try:
                engine = UserExecutionEngine(
                    user_id=user_id,
                    session_id=user_data['session_id'],
                    websocket_manager=websocket
                )
                
                user_engines[user_id] = engine
                user_websockets[user_id] = websocket
                
            except Exception as e:
                isolation_violations.append(f"Failed to create engine for {user_id}: {e}")
        
        print(f"  ✅ Created {len(user_engines)} user execution engines")
        
        # Define realistic user execution scenarios
        user_scenarios = [
            {
                'name': 'data_analysis',
                'events': [
                    ('agent_started', {'task': 'data_analysis', 'dataset': 'user_data_{{user_index}}'}),
                    ('agent_thinking', {'thought': 'Analyzing dataset structure'}),
                    ('tool_executing', {'tool_name': 'data_analyzer', 'dataset_id': '{{user_index}}'}),
                    ('tool_completed', {'tool_name': 'data_analyzer', 'result': 'analysis_{{user_index}}'}),
                    ('agent_completed', {'result': 'Data analysis complete for user {{user_index}}'})
                ]
            },
            {
                'name': 'report_generation',
                'events': [
                    ('agent_started', {'task': 'report_generation', 'report_type': 'monthly_{{user_index}}'}),
                    ('agent_thinking', {'thought': 'Gathering report data'}),
                    ('tool_executing', {'tool_name': 'report_builder', 'user_id': '{{user_index}}'}),
                    ('tool_completed', {'tool_name': 'report_builder', 'report_id': 'report_{{user_index}}'}),
                    ('agent_thinking', {'thought': 'Formatting report'}),
                    ('agent_completed', {'result': 'Report generated for user {{user_index}}'})
                ]
            },
            {
                'name': 'optimization',
                'events': [
                    ('agent_started', {'task': 'optimization', 'target': 'user_workflow_{{user_index}}'}),
                    ('agent_thinking', {'thought': 'Analyzing current workflow'}),
                    ('tool_executing', {'tool_name': 'workflow_analyzer', 'user_context': '{{user_index}}'}),
                    ('tool_completed', {'tool_name': 'workflow_analyzer', 'optimizations': 'opt_{{user_index}}'}),
                    ('tool_executing', {'tool_name': 'optimization_engine', 'plan': 'opt_{{user_index}}'}),
                    ('tool_completed', {'tool_name': 'optimization_engine', 'result': 'optimized_{{user_index}}'}),
                    ('agent_completed', {'result': 'Workflow optimized for user {{user_index}}'})
                ]
            }
        ]
        
        async def execute_user_scenario(user_index: int, user_id: str):
            """Execute realistic scenario for a specific user"""
            try:
                engine = user_engines[user_id]
                scenario = user_scenarios[user_index % len(user_scenarios)]
                
                # Execute scenario events with user-specific data
                for event_type, event_data in scenario['events']:
                    # Replace placeholders with actual user data
                    user_specific_data = {}
                    for key, value in event_data.items():
                        if isinstance(value, str):
                            user_specific_data[key] = value.replace('{{user_index}}', str(user_index))
                        else:
                            user_specific_data[key] = value
                    
                    # Add user identification to all events
                    user_specific_data['_source_user'] = user_id
                    user_specific_data['_user_index'] = user_index
                    user_specific_data['_scenario'] = scenario['name']
                    
                    await engine.send_websocket_event(event_type, user_specific_data)
                    
                    # Realistic delay between events
                    await asyncio.sleep(0.01 + (user_index * 0.001))
                
                return f"success_{user_id}"
                
            except Exception as e:
                isolation_violations.append(f"User {user_id} execution failed: {e}")
                return f"error_{user_id}"
        
        # Execute scenarios concurrently for all users
        print(f"  🔄 Executing scenarios for {len(user_engines)} users concurrently...")
        
        concurrent_tasks = []
        for i, user_data in enumerate(self.test_users):
            user_id = user_data['user_id']
            if user_id in user_engines:
                task = execute_user_scenario(i, user_id)
                concurrent_tasks.append(task)
        
        # Wait for all executions to complete
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        print(f"  ✅ Concurrent execution completed in {execution_time:.2f} seconds")
        
        # Validate execution results
        successful_executions = sum(1 for result in results if isinstance(result, str) and result.startswith('success'))
        failed_executions = len(results) - successful_executions
        
        if failed_executions > len(results) * 0.1:  # Allow up to 10% failures
            isolation_violations.append(f"Too many failed executions: {failed_executions}/{len(results)}")
        
        print(f"  ✅ {successful_executions}/{len(results)} executions successful")
        
        # Validate user isolation - check for cross-user contamination
        for user_id, websocket in user_websockets.items():
            user_events = websocket.get_user_events()
            contamination = websocket.has_cross_user_contamination(user_id)
            
            if contamination:
                isolation_violations.extend(contamination)
            
            # Validate user events contain correct user data
            for event in user_events:
                event_data = event['data']
                if '_source_user' in event_data and event_data['_source_user'] != user_id:
                    isolation_violations.append(f"User {user_id} received event from {event_data['_source_user']}")
        
        print(f"  ✅ Cross-user contamination check completed")
        
        # Validate event distribution
        total_events = sum(len(ws.get_user_events()) for ws in user_websockets.values())
        avg_events_per_user = total_events / len(user_websockets) if user_websockets else 0
        
        print(f"  ✅ Total events processed: {total_events}")
        print(f"  ✅ Average events per user: {avg_events_per_user:.1f}")
        
        # Check for reasonable event distribution
        event_counts = [len(ws.get_user_events()) for ws in user_websockets.values()]
        if event_counts:
            min_events = min(event_counts)
            max_events = max(event_counts)
            
            if max_events > min_events * 2:  # Events should be relatively evenly distributed
                isolation_violations.append(f"Uneven event distribution: {min_events} - {max_events} events per user")
        
        # CRITICAL: Multi-user isolation is essential for platform security and reliability
        if isolation_violations:
            self.fail(f"Multi-user execution isolation violations: {isolation_violations}")
        
        print(f"  ✅ Multi-user execution isolation validated for {len(user_engines)} concurrent users")
    
    def test_user_context_data_isolation_integration(self):
        """Test that user context data is properly isolated in integration scenarios"""
        print("\n🔍 Testing user context data isolation in integration scenarios...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        context_violations = []
        user_contexts = {}
        
        # Create engines and set user-specific context data
        for user_data in self.test_users:
            user_id = user_data['user_id']
            websocket = RealWebSocketSimulator(user_id, user_data['connection_id'])
            
            try:
                engine = UserExecutionEngine(
                    user_id=user_id,
                    session_id=user_data['session_id'],
                    websocket_manager=websocket
                )
                
                # Get and validate user context
                if hasattr(engine, 'get_user_context'):
                    context = engine.get_user_context()
                    user_contexts[user_id] = context
                    
                    # Validate context contains correct user data
                    if context.get('user_id') != user_id:
                        context_violations.append(f"User {user_id} context has wrong user_id: {context.get('user_id')}")
                    
                    if context.get('session_id') != user_data['session_id']:
                        context_violations.append(f"User {user_id} context has wrong session_id")
                        
                else:
                    context_violations.append(f"Engine for {user_id} missing get_user_context method")
                
            except Exception as e:
                context_violations.append(f"Failed to create/test engine for {user_id}: {e}")
        
        print(f"  ✅ Created and validated context for {len(user_contexts)} users")
        
        # Test context isolation - no shared references
        context_ids = {}
        for user_id, context in user_contexts.items():
            context_id = id(context)
            if context_id in context_ids:
                context_violations.append(f"Shared context object detected between {context_ids[context_id]} and {user_id}")
            context_ids[context_id] = user_id
        
        print(f"  ✅ Context object isolation validated")
        
        # Test context data integrity
        for user_id, context in user_contexts.items():
            # Each context should be a dict
            if not isinstance(context, dict):
                context_violations.append(f"User {user_id} context is not a dict: {type(context)}")
                continue
            
            # Context should contain user-specific data
            required_fields = ['user_id', 'session_id']
            for field in required_fields:
                if field not in context:
                    context_violations.append(f"User {user_id} context missing {field}")
            
            # Context should not contain other users' data
            for other_user_id in user_contexts.keys():
                if other_user_id != user_id and other_user_id in str(context):
                    context_violations.append(f"User {user_id} context contains reference to {other_user_id}")
        
        print(f"  ✅ Context data integrity validated")
        
        # Test concurrent context access
        def access_user_context(user_id: str, iterations: int = 100):
            """Access user context multiple times to test thread safety"""
            context_accesses = []
            
            if user_id not in user_contexts:
                return f"error_no_context_{user_id}"
            
            try:
                for i in range(iterations):
                    context = user_contexts[user_id]
                    
                    # Validate context consistency
                    if context.get('user_id') != user_id:
                        return f"error_inconsistent_context_{user_id}_{i}"
                    
                    context_accesses.append(context.get('user_id'))
                    
                    # Small delay to allow thread interleaving
                    time.sleep(0.0001)
                
                # All accesses should return the same user_id
                unique_user_ids = set(context_accesses)
                if len(unique_user_ids) != 1 or list(unique_user_ids)[0] != user_id:
                    return f"error_context_contamination_{user_id}_{unique_user_ids}"
                
                return f"success_{user_id}_{len(context_accesses)}"
                
            except Exception as e:
                return f"error_exception_{user_id}_{e}"
        
        # Run concurrent context access tests
        print(f"  🔄 Testing concurrent context access...")
        
        with ThreadPoolExecutor(max_workers=len(self.test_users)) as executor:
            context_futures = {
                executor.submit(access_user_context, user_data['user_id'], 50): user_data['user_id']
                for user_data in self.test_users[:5]  # Test subset for performance
            }
            
            concurrent_results = {}
            for future in as_completed(context_futures, timeout=30):
                user_id = context_futures[future]
                try:
                    result = future.result()
                    concurrent_results[user_id] = result
                except Exception as e:
                    context_violations.append(f"Concurrent context access failed for {user_id}: {e}")
        
        # Validate concurrent access results
        for user_id, result in concurrent_results.items():
            if not result.startswith('success'):
                context_violations.append(f"Concurrent context access failed for {user_id}: {result}")
        
        print(f"  ✅ Concurrent context access completed for {len(concurrent_results)} users")
        
        # CRITICAL: Context isolation prevents data leaks between users
        if context_violations:
            self.fail(f"User context data isolation violations: {context_violations}")
        
        print(f"  ✅ User context data isolation validated in integration scenarios")
    
    async def test_performance_under_multi_user_load(self):
        """Test UserExecutionEngine performance under realistic multi-user load"""
        print("\n🔍 Testing performance under multi-user load...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        performance_violations = []
        
        # Performance test configuration
        load_users = 20  # Simulate 20 concurrent users
        events_per_user = 25  # Each user sends 25 events
        
        async def simulate_user_load(user_index: int):
            """Simulate realistic user load"""
            user_id = f"load_user_{user_index}"
            websocket = RealWebSocketSimulator(user_id, str(uuid.uuid4()))
            
            try:
                # Time engine creation
                creation_start = time.perf_counter()
                engine = UserExecutionEngine(
                    user_id=user_id,
                    session_id=f"load_session_{user_index}",
                    websocket_manager=websocket
                )
                creation_time = time.perf_counter() - creation_start
                
                # Time event processing
                processing_start = time.perf_counter()
                
                for event_num in range(events_per_user):
                    event_type = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'][event_num % 5]
                    
                    await engine.send_websocket_event(event_type, {
                        'user_index': user_index,
                        'event_num': event_num,
                        'load_test': True,
                        'timestamp': time.time()
                    })
                
                processing_time = time.perf_counter() - processing_start
                
                # Time cleanup
                cleanup_start = time.perf_counter()
                if hasattr(engine, 'cleanup'):
                    engine.cleanup()
                cleanup_time = time.perf_counter() - cleanup_start
                
                return {
                    'user_index': user_index,
                    'creation_time': creation_time,
                    'processing_time': processing_time,
                    'cleanup_time': cleanup_time,
                    'events_sent': len(websocket.get_user_events()),
                    'success': True
                }
                
            except Exception as e:
                performance_violations.append(f"Load test failed for user {user_index}: {e}")
                return {
                    'user_index': user_index,
                    'success': False,
                    'error': str(e)
                }
        
        # Run load test
        print(f"  🔄 Running load test with {load_users} concurrent users...")
        
        load_start_time = time.perf_counter()
        load_results = await asyncio.gather(*[simulate_user_load(i) for i in range(load_users)], return_exceptions=True)
        total_load_time = time.perf_counter() - load_start_time
        
        print(f"  ✅ Load test completed in {total_load_time:.2f} seconds")
        
        # Analyze performance results
        successful_results = [r for r in load_results if isinstance(r, dict) and r.get('success')]
        failed_count = len(load_results) - len(successful_results)
        
        if failed_count > load_users * 0.05:  # Allow up to 5% failures
            performance_violations.append(f"Too many load test failures: {failed_count}/{load_users}")
        
        if successful_results:
            # Calculate performance metrics
            creation_times = [r['creation_time'] for r in successful_results]
            processing_times = [r['processing_time'] for r in successful_results]
            cleanup_times = [r['cleanup_time'] for r in successful_results]
            events_sent = [r['events_sent'] for r in successful_results]
            
            avg_creation_time = sum(creation_times) / len(creation_times)
            avg_processing_time = sum(processing_times) / len(processing_times)
            avg_cleanup_time = sum(cleanup_times) / len(cleanup_times)
            total_events = sum(events_sent)
            
            print(f"  ✅ Average creation time: {avg_creation_time:.3f}s per user")
            print(f"  ✅ Average processing time: {avg_processing_time:.3f}s per user")
            print(f"  ✅ Average cleanup time: {avg_cleanup_time:.3f}s per user")
            print(f"  ✅ Total events processed: {total_events}")
            
            # Performance thresholds for multi-user scenarios
            if avg_creation_time > 0.5:  # 500ms per user creation is too slow
                performance_violations.append(f"Slow user creation: {avg_creation_time:.3f}s average")
            
            if avg_processing_time > 2.0:  # 2s for 25 events is too slow
                performance_violations.append(f"Slow event processing: {avg_processing_time:.3f}s average")
            
            if total_load_time > 30.0:  # 30s total for load test is too slow
                performance_violations.append(f"Slow overall load test: {total_load_time:.2f}s")
            
            # Validate event processing consistency
            expected_events_per_user = events_per_user
            for result in successful_results:
                if result['events_sent'] != expected_events_per_user:
                    performance_violations.append(f"User {result['user_index']} sent {result['events_sent']} events, expected {expected_events_per_user}")
        
        print(f"  ✅ {len(successful_results)}/{load_users} users completed successfully")
        
        # CRITICAL: Performance under load is essential for production readiness
        if performance_violations:
            self.fail(f"Multi-user load performance violations: {performance_violations}")
        
        print(f"  ✅ Performance validated under {load_users}-user load")


if __name__ == '__main__':
    unittest.main(verbosity=2)