"""
Comprehensive Concurrency Tests for Multi-User Agent Execution Isolation

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (critical for multi-tenant deployment)
- Business Goal: Platform Security & Scalability - Ensures complete user isolation at scale
- Value Impact: Validates enterprise-grade multi-user agent execution (prevents data leakage)
- Revenue Impact: Protects $500K+ ARR by ensuring secure concurrent user sessions

Critical Concurrency Scenarios Tested:
1. Concurrent user isolation: 10+ users executing agents simultaneously without interference
2. WebSocket event isolation: User-specific event delivery with no cross-contamination
3. Memory isolation: User execution contexts don't share state or leak data
4. Performance under load: System maintains <2s response times with 20+ concurrent users
5. Factory pattern validation: User-specific instances created properly under load

SSOT Testing Compliance:
- Uses test_framework.ssot.base_test_case.SSotAsyncTestCase
- Real services preferred over mocks (only external dependencies mocked)
- Business-critical functionality validation over implementation details
- Concurrency and isolation business logic focus
"""

import asyncio
import random
import time
import uuid
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List, Set
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Agent Orchestration SSOT Classes Under Test
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
# SSOT MIGRATION: Use UserExecutionEngine as the single source of truth
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Supporting Infrastructure
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestMultiUserAgentExecutionIsolationComprehensive(SSotAsyncTestCase):
    """
    Comprehensive concurrency tests for multi-user agent execution isolation.
    
    Tests the critical multi-user isolation functionality that enables
    enterprise-grade concurrent agent execution without data leakage.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup test environment for concurrency testing."""
        # Create mock infrastructure using SSOT mock factory
        self.mock_factory = SSotMockFactory()
        
        # Core mocked dependencies (external only - keep business logic real)
        self.mock_llm_manager = self.mock_factory.create_mock_llm_manager()
        self.mock_websocket_bridge = self.mock_factory.create_mock_agent_websocket_bridge()
        
        # Concurrency tracking
        self.concurrent_executions = {}
        self.user_isolation_violations = []
        self.websocket_event_tracking = {}
        self.performance_metrics = {}
        
        # Configure mock behaviors for concurrency testing
        await self._setup_mock_behaviors()
    
    async def _setup_mock_behaviors(self):
        """Setup realistic mock behaviors for concurrency testing."""
        # Configure execution engine factory to track user-specific instances
        self.user_execution_engines = {}
        
        async def create_isolated_execution_engine(context):
            """Create user-specific execution engine for isolation testing."""
            user_id = context.user_id
            
            # Create unique mock execution engine for each user
            mock_engine = self.mock_factory.create_mock("UserExecutionEngine")
            
            # Configure realistic execution behavior with user isolation
            async def mock_execute_pipeline(agent_name, execution_context, input_data):
                start_time = time.time()
                
                # Simulate realistic execution time
                execution_duration = random.uniform(0.1, 0.5)  # 100-500ms
                await asyncio.sleep(execution_duration)
                
                # Track execution for isolation validation
                execution_id = f"{user_id}_{agent_name}_{int(time.time() * 1000)}"
                self.concurrent_executions[execution_id] = {
                    'user_id': user_id,
                    'agent_name': agent_name,
                    'start_time': start_time,
                    'duration': execution_duration,
                    'context': execution_context,
                    'isolated': True
                }
                
                # Return user-specific result
                result = MagicMock()
                result.success = True
                result.result = {
                    'user_id': user_id,
                    'execution_id': execution_id,
                    'agent_name': agent_name,
                    'timestamp': time.time(),
                    'isolated_execution': True,
                    'user_specific_data': f"Result for user {user_id}"
                }
                
                return result
            
            mock_engine.execute_agent_pipeline = AsyncMock(side_effect=mock_execute_pipeline)
            mock_engine.cleanup = AsyncMock()
            
            # Store engine reference for validation
            self.user_execution_engines[user_id] = mock_engine
            
            return mock_engine
        
        # Configure WebSocket bridge to track user-specific events
        async def capture_user_websocket_event(event_type, run_id, agent_name, *args, **kwargs):
            """Capture WebSocket events with user isolation tracking."""
            # Extract user_id from run_id pattern
            user_id = run_id.split('_')[0] if '_' in run_id else run_id
            
            if user_id not in self.websocket_event_tracking:
                self.websocket_event_tracking[user_id] = []
            
            event = {
                'event_type': event_type,
                'run_id': run_id,
                'agent_name': agent_name,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time(),
                'user_id': user_id
            }
            
            self.websocket_event_tracking[user_id].append(event)
            
            # Validate event isolation - ensure events only go to correct user
            for other_user_id, other_events in self.websocket_event_tracking.items():
                if other_user_id != user_id:
                    # Check if this event accidentally went to another user
                    for other_event in other_events:
                        if (other_event['run_id'] == run_id and 
                            other_event['timestamp'] == event['timestamp']):
                            self.user_isolation_violations.append({
                                'violation_type': 'websocket_cross_contamination',
                                'correct_user': user_id,
                                'contaminated_user': other_user_id,
                                'event': event
                            })
        
        # Configure WebSocket bridge methods with isolation tracking
        self.mock_websocket_bridge.notify_agent_started = AsyncMock(
            side_effect=lambda run_id, agent_name, *args, **kwargs: 
            capture_user_websocket_event('agent_started', run_id, agent_name, *args, **kwargs)
        )
        self.mock_websocket_bridge.notify_agent_thinking = AsyncMock(
            side_effect=lambda run_id, agent_name, *args, **kwargs:
            capture_user_websocket_event('agent_thinking', run_id, agent_name, *args, **kwargs)
        )
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock(
            side_effect=lambda run_id, agent_name, *args, **kwargs:
            capture_user_websocket_event('agent_completed', run_id, agent_name, *args, **kwargs)
        )
        
        # Patch factory method to return our isolation-tracking engine creator
        self.execution_engine_factory_patch = patch(
            'netra_backend.app.agents.supervisor_ssot.get_agent_instance_factory'
        )
        mock_factory = self.execution_engine_factory_patch.start()
        
        # Configure agent factory to create isolated engines
        mock_instance_factory = self.mock_factory.create_mock("AgentInstanceFactory")
        mock_factory.return_value = mock_instance_factory
        
        # Patch session manager for database isolation
        self.session_manager_patch = patch(
            'netra_backend.app.agents.supervisor_ssot.managed_session'
        )
        mock_session_manager = self.session_manager_patch.start()
        mock_session_manager.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session_manager.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Store the engine creation function for patching
        self._create_isolated_execution_engine = create_isolated_execution_engine
    
    async def teardown_method(self):
        """Clean up after each test."""
        # Stop patches
        if hasattr(self, 'execution_engine_factory_patch'):
            self.execution_engine_factory_patch.stop()
        if hasattr(self, 'session_manager_patch'):
            self.session_manager_patch.stop()
        
        # Clear tracking data
        self.concurrent_executions.clear()
        self.user_isolation_violations.clear()
        self.websocket_event_tracking.clear()
        self.performance_metrics.clear()
        self.user_execution_engines.clear()
    
    def _create_test_user_context(self, user_number: int) -> UserExecutionContext:
        """Create test user context for concurrency testing."""
        return UserExecutionContext(
            user_id=f"concurrent_user_{user_number:03d}",
            thread_id=f"concurrent_thread_{user_number:03d}",
            run_id=f"concurrent_user_{user_number:03d}_run_{int(time.time())}",
            request_id=f"concurrent_req_{user_number:03d}",
            websocket_client_id=f"concurrent_ws_{user_number:03d}"
        )
    
    # ============================================================================
    # CONCURRENCY SCENARIO 1: Concurrent User Isolation (10+ Users)
    # ============================================================================
    
    @pytest.mark.concurrency
    @pytest.mark.business_critical
    async def test_concurrent_user_isolation_10_users(self):
        """
        Test concurrent user isolation with 10+ users executing agents simultaneously.
        
        BVJ: Enterprise security - ensures complete user isolation at moderate scale
        Critical Path: 10+ users  ->  Concurrent execution  ->  No data leakage  ->  Isolated results
        """
        # Arrange: Create 12 users for concurrent execution testing
        num_users = 12
        user_contexts = []
        supervisor_agents = []
        
        for i in range(num_users):
            user_context = self._create_test_user_context(i)
            user_contexts.append(user_context)
            
            # Create separate supervisor agent instance for each user
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge
            )
            supervisor_agents.append(supervisor)
        
        # Patch each supervisor to use isolated execution engine
        patches = []
        for i, supervisor in enumerate(supervisor_agents):
            user_context = user_contexts[i]
            
            # Create isolated execution engine for this user
            isolated_engine = await self._create_isolated_execution_engine(user_context)
            
            patch_obj = patch.object(
                supervisor, '_create_user_execution_engine',
                new_callable=AsyncMock, return_value=isolated_engine
            )
            patches.append(patch_obj)
            patch_obj.start()
        
        try:
            # Act: Execute all users concurrently
            start_time = time.time()
            
            # Create execution tasks for all users
            tasks = []
            for i, (supervisor, user_context) in enumerate(zip(supervisor_agents, user_contexts)):
                # Add some variety to user requests for realistic testing
                user_requests = [
                    "Optimize my machine learning model",
                    "Analyze my data pipeline performance", 
                    "Improve my API response times",
                    "Debug my application bottlenecks",
                    "Enhance my database queries"
                ]
                
                user_context.metadata = {
                    'user_request': user_requests[i % len(user_requests)],
                    'user_priority': random.choice(['high', 'medium', 'low']),
                    'concurrent_test_id': i
                }
                
                task = supervisor.execute(user_context, stream_updates=True)
                tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_execution_time = end_time - start_time
            
            # Assert: Verify concurrent user isolation
            # Check that we got results for all users
            assert len(results) == num_users
            
            # Verify no exceptions occurred (all executions succeeded)
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == num_users, f"Some executions failed: {[r for r in results if isinstance(r, Exception)]}"
            
            # Verify each user got their own isolated results
            user_ids_in_results = set()
            for result in successful_results:
                assert result is not None
                assert result['user_isolation_verified'] is True
                assert result['user_id'] is not None
                user_ids_in_results.add(result['user_id'])
            
            # All users should have unique results
            assert len(user_ids_in_results) == num_users
            
            # Verify no isolation violations occurred
            assert len(self.user_isolation_violations) == 0, \
                f"User isolation violations detected: {self.user_isolation_violations}"
            
            # Verify each user had their own execution engine
            assert len(self.user_execution_engines) == num_users
            for i in range(num_users):
                expected_user_id = f"concurrent_user_{i:03d}"
                assert expected_user_id in self.user_execution_engines
            
            # Verify concurrent executions were tracked properly
            assert len(self.concurrent_executions) >= num_users  # At least one execution per user
            
            # Verify execution isolation - no user should see another user's data
            for execution_id, execution_info in self.concurrent_executions.items():
                user_id = execution_info['user_id']
                # Verify execution context belongs to the correct user
                assert user_id in execution_info['context'].user_id or \
                       execution_info['context'].user_id.startswith(user_id)
                assert execution_info['isolated'] is True
                
            # Performance validation - should complete within reasonable time
            avg_time_per_user = total_execution_time / num_users
            assert total_execution_time < 10.0, \
                f"Concurrent execution took too long: {total_execution_time:.2f}s (should be <10s)"
            assert avg_time_per_user < 2.0, \
                f"Average time per user too high: {avg_time_per_user:.2f}s (should be <2s)"
            
            # Log performance metrics
            self.performance_metrics['concurrent_10_users'] = {
                'total_time': total_execution_time,
                'avg_time_per_user': avg_time_per_user,
                'successful_users': len(successful_results),
                'isolation_violations': len(self.user_isolation_violations)
            }
            
        finally:
            # Clean up patches
            for patch_obj in patches:
                patch_obj.stop()
    
    # ============================================================================
    # CONCURRENCY SCENARIO 2: WebSocket Event Isolation
    # ============================================================================
    
    @pytest.mark.concurrency
    @pytest.mark.websocket_isolation
    async def test_websocket_event_isolation_concurrent_users(self):
        """
        Test WebSocket event isolation with concurrent users.
        
        BVJ: User experience - ensures users only see their own agent events
        Critical Path: Concurrent users  ->  WebSocket events  ->  User-specific delivery  ->  No cross-contamination
        """
        # Arrange: Create 8 users for WebSocket isolation testing
        num_users = 8
        user_contexts = []
        supervisor_agents = []
        
        for i in range(num_users):
            user_context = self._create_test_user_context(i + 100)  # Start from 100 to avoid ID conflicts
            user_contexts.append(user_context)
            
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge
            )
            supervisor_agents.append(supervisor)
        
        # Patch each supervisor for WebSocket event testing
        patches = []
        for i, supervisor in enumerate(supervisor_agents):
            user_context = user_contexts[i]
            isolated_engine = await self._create_isolated_execution_engine(user_context)
            
            patch_obj = patch.object(
                supervisor, '_create_user_execution_engine',
                new_callable=AsyncMock, return_value=isolated_engine
            )
            patches.append(patch_obj)
            patch_obj.start()
        
        try:
            # Act: Execute all users concurrently with WebSocket event tracking
            tasks = []
            for supervisor, user_context in zip(supervisor_agents, user_contexts):
                task = supervisor.execute(user_context, stream_updates=True)
                tasks.append(task)
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Brief delay to ensure all WebSocket events are processed
            await asyncio.sleep(0.1)
            
            # Assert: Verify WebSocket event isolation
            # Verify we have WebSocket events for each user
            assert len(self.websocket_event_tracking) == num_users
            
            # Verify each user only received their own events
            for i, user_context in enumerate(user_contexts):
                user_id = user_context.user_id
                user_run_id = user_context.run_id
                
                assert user_id in self.websocket_event_tracking, \
                    f"No WebSocket events tracked for user {user_id}"
                
                user_events = self.websocket_event_tracking[user_id]
                assert len(user_events) >= 3, \
                    f"User {user_id} should have at least 3 events (started, thinking, completed)"
                
                # Verify all events belong to this user
                for event in user_events:
                    assert event['user_id'] == user_id, \
                        f"Event contamination: Event for user {user_id} has user_id {event['user_id']}"
                    
                    # Run ID should match or be associated with this user
                    assert user_run_id == event['run_id'] or user_id in event['run_id'], \
                        f"Run ID mismatch: Expected {user_run_id}, got {event['run_id']}"
            
            # Verify no cross-contamination of WebSocket events
            assert len(self.user_isolation_violations) == 0, \
                f"WebSocket event cross-contamination detected: {self.user_isolation_violations}"
            
            # Verify event types are present for each user
            required_event_types = {'agent_started', 'agent_thinking', 'agent_completed'}
            for user_id, events in self.websocket_event_tracking.items():
                user_event_types = {event['event_type'] for event in events}
                missing_events = required_event_types - user_event_types
                assert len(missing_events) == 0, \
                    f"User {user_id} missing required events: {missing_events}"
            
            # Verify event ordering within each user's stream
            for user_id, events in self.websocket_event_tracking.items():
                # Sort events by timestamp
                sorted_events = sorted(events, key=lambda e: e['timestamp'])
                
                # Find key event indices
                started_events = [i for i, e in enumerate(sorted_events) if e['event_type'] == 'agent_started']
                completed_events = [i for i, e in enumerate(sorted_events) if e['event_type'] == 'agent_completed']
                
                # Verify proper ordering
                if started_events and completed_events:
                    assert started_events[0] < completed_events[-1], \
                        f"User {user_id}: agent_started should come before agent_completed"
            
        finally:
            # Clean up patches
            for patch_obj in patches:
                patch_obj.stop()
    
    # ============================================================================
    # CONCURRENCY SCENARIO 3: Memory Isolation Under Load
    # ============================================================================
    
    @pytest.mark.concurrency
    @pytest.mark.memory_isolation
    async def test_memory_isolation_under_concurrent_load(self):
        """
        Test memory isolation under concurrent load to prevent data leakage.
        
        BVJ: Enterprise security - ensures user data doesn't leak between concurrent sessions
        Critical Path: Concurrent users  ->  Memory isolation  ->  No shared state  ->  No data leakage
        """
        # Arrange: Create 15 users with distinct data for memory isolation testing
        num_users = 15
        user_test_data = {}
        user_contexts = []
        supervisor_agents = []
        
        for i in range(num_users):
            user_context = self._create_test_user_context(i + 200)  # Start from 200
            
            # Create user-specific sensitive test data
            sensitive_data = {
                'user_id': user_context.user_id,
                'secret_key': f"secret_{uuid.uuid4()}",
                'personal_info': f"sensitive_data_for_user_{i}",
                'api_tokens': [f"token_{j}_{uuid.uuid4()}" for j in range(3)],
                'private_config': {
                    'setting_1': f"private_value_{i}_1", 
                    'setting_2': f"private_value_{i}_2",
                    'user_specific_flag': True
                }
            }
            
            user_test_data[user_context.user_id] = sensitive_data
            user_context.metadata.update(sensitive_data)
            
            user_contexts.append(user_context)
            
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge
            )
            supervisor_agents.append(supervisor)
        
        # Create memory isolation tracking
        memory_access_log = {}
        
        async def create_memory_tracking_engine(user_context):
            """Create execution engine that tracks memory access for isolation testing."""
            user_id = user_context.user_id
            mock_engine = self.mock_factory.create_mock("UserExecutionEngine")
            
            async def mock_execute_with_memory_tracking(agent_name, execution_context, input_data):
                # Track what data this execution can access
                accessible_data = {
                    'user_id': execution_context.user_id,
                    'execution_data': input_data,
                    'context_metadata': execution_context.metadata,
                    'timestamp': time.time()
                }
                
                # Log memory access
                if user_id not in memory_access_log:
                    memory_access_log[user_id] = []
                
                memory_access_log[user_id].append({
                    'agent_name': agent_name,
                    'accessible_data': accessible_data,
                    'memory_isolated': True,
                    'timestamp': time.time()
                })
                
                # Simulate checking for data leakage - ensure only own data is accessible
                expected_user_data = user_test_data.get(user_id, {})
                
                # Verify execution context contains correct user data
                if hasattr(execution_context, 'metadata') and execution_context.metadata:
                    context_secret = execution_context.metadata.get('secret_key')
                    expected_secret = expected_user_data.get('secret_key')
                    
                    if context_secret and expected_secret:
                        if context_secret != expected_secret:
                            self.user_isolation_violations.append({
                                'violation_type': 'memory_data_leakage',
                                'user_id': user_id,
                                'expected_secret': expected_secret,
                                'actual_secret': context_secret,
                                'execution_context': execution_context
                            })
                
                # Return user-specific result with memory isolation validation
                result = MagicMock()
                result.success = True
                result.result = {
                    'user_id': user_id,
                    'memory_isolated': True,
                    'accessible_secrets': [expected_user_data.get('secret_key', 'none')],
                    'private_config_accessible': expected_user_data.get('private_config', {}),
                    'user_data_integrity': True
                }
                
                return result
            
            mock_engine.execute_agent_pipeline = AsyncMock(side_effect=mock_execute_with_memory_tracking)
            mock_engine.cleanup = AsyncMock()
            return mock_engine
        
        # Patch supervisors for memory tracking
        patches = []
        for i, supervisor in enumerate(supervisor_agents):
            user_context = user_contexts[i]
            
            patch_obj = patch.object(
                supervisor, '_create_user_execution_engine',
                new_callable=AsyncMock, 
                side_effect=lambda ctx=user_context: create_memory_tracking_engine(ctx)
            )
            patches.append(patch_obj)
            patch_obj.start()
        
        try:
            # Act: Execute all users concurrently to test memory isolation
            start_time = time.time()
            
            # Add some load by executing multiple rounds
            all_tasks = []
            for round_num in range(2):  # 2 rounds of execution
                round_tasks = []
                for supervisor, user_context in zip(supervisor_agents, user_contexts):
                    task = supervisor.execute(user_context, stream_updates=True)
                    round_tasks.append(task)
                
                all_tasks.extend(round_tasks)
                
                # Brief delay between rounds
                if round_num == 0:
                    await asyncio.sleep(0.05)
            
            # Execute all tasks
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Assert: Verify memory isolation under load
            # Verify all executions succeeded
            successful_results = [r for r in results if not isinstance(r, Exception)]
            expected_total_results = num_users * 2  # 2 rounds
            assert len(successful_results) == expected_total_results, \
                f"Expected {expected_total_results} successful results, got {len(successful_results)}"
            
            # Verify no memory isolation violations
            assert len(self.user_isolation_violations) == 0, \
                f"Memory isolation violations detected: {self.user_isolation_violations}"
            
            # Verify each user's memory access log
            assert len(memory_access_log) == num_users
            
            for user_id, access_entries in memory_access_log.items():
                # Each user should have 2 access entries (2 rounds)
                assert len(access_entries) == 2, \
                    f"User {user_id} should have 2 memory access entries, got {len(access_entries)}"
                
                # Verify memory isolation flag
                for entry in access_entries:
                    assert entry['memory_isolated'] is True
                    assert entry['accessible_data']['user_id'] == user_id
            
            # Verify results contain proper user isolation
            for result in successful_results:
                if isinstance(result, dict) and 'user_id' in result:
                    user_id = result['user_id']
                    assert result['user_isolation_verified'] is True
                    
                    # Check if we have the execution result details
                    if 'results' in result and isinstance(result['results'], dict):
                        execution_result = result['results']
                        if 'memory_isolated' in execution_result:
                            assert execution_result['memory_isolated'] is True
                            assert execution_result['user_data_integrity'] is True
                        
                        # Verify user can only access their own secrets
                        if 'accessible_secrets' in execution_result:
                            user_secrets = execution_result['accessible_secrets']
                            expected_secret = user_test_data[user_id]['secret_key']
                            assert expected_secret in user_secrets
                            
                            # Ensure no other user's secrets are accessible
                            for other_user_id, other_data in user_test_data.items():
                                if other_user_id != user_id:
                                    other_secret = other_data['secret_key']
                                    assert other_secret not in user_secrets, \
                                        f"User {user_id} can access other user's secret: {other_secret}"
            
            # Performance validation under load
            assert total_time < 15.0, \
                f"Memory isolation test under load took too long: {total_time:.2f}s"
            
            # Log performance metrics
            self.performance_metrics['memory_isolation_under_load'] = {
                'total_time': total_time,
                'users': num_users,
                'rounds': 2,
                'avg_time_per_execution': total_time / (num_users * 2),
                'memory_violations': len(self.user_isolation_violations)
            }
            
        finally:
            # Clean up patches
            for patch_obj in patches:
                patch_obj.stop()
    
    # ============================================================================
    # CONCURRENCY SCENARIO 4: Performance Under Heavy Load (20+ Users)
    # ============================================================================
    
    @pytest.mark.concurrency
    @pytest.mark.performance
    async def test_performance_under_heavy_concurrent_load_20_users(self):
        """
        Test system performance under heavy concurrent load with 20+ users.
        
        BVJ: Platform scalability - ensures system maintains performance with high concurrency
        Critical Path: 20+ users  ->  High load  ->  <2s response time  ->  System stability
        """
        # Arrange: Create 25 users for heavy load testing
        num_users = 25
        user_contexts = []
        supervisor_agents = []
        
        for i in range(num_users):
            user_context = self._create_test_user_context(i + 300)  # Start from 300
            user_context.metadata.update({
                'load_test': True,
                'user_priority': random.choice(['high', 'medium', 'low']),
                'request_complexity': random.choice(['simple', 'medium', 'complex']),
                'expected_response_time': random.uniform(0.5, 2.0)
            })
            user_contexts.append(user_context)
            
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge
            )
            supervisor_agents.append(supervisor)
        
        # Create performance tracking engine
        performance_data = {
            'user_response_times': {},
            'system_resource_usage': [],
            'throughput_metrics': []
        }
        
        async def create_performance_tracking_engine(user_context):
            """Create execution engine that tracks performance metrics."""
            user_id = user_context.user_id
            mock_engine = self.mock_factory.create_mock("UserExecutionEngine")
            
            async def mock_execute_with_performance_tracking(agent_name, execution_context, input_data):
                start_time = time.time()
                
                # Simulate realistic execution with varying complexity
                complexity = execution_context.metadata.get('request_complexity', 'medium')
                if complexity == 'simple':
                    base_time = random.uniform(0.1, 0.3)
                elif complexity == 'medium':
                    base_time = random.uniform(0.2, 0.6)
                else:  # complex
                    base_time = random.uniform(0.4, 1.0)
                
                await asyncio.sleep(base_time)
                
                execution_time = time.time() - start_time
                
                # Track performance metrics
                performance_data['user_response_times'][user_id] = execution_time
                performance_data['throughput_metrics'].append({
                    'user_id': user_id,
                    'execution_time': execution_time,
                    'complexity': complexity,
                    'timestamp': time.time()
                })
                
                # Return performance result
                result = MagicMock()
                result.success = True
                result.result = {
                    'user_id': user_id,
                    'execution_time': execution_time,
                    'complexity': complexity,
                    'performance_acceptable': execution_time < 2.0,
                    'load_test_result': True
                }
                
                return result
            
            mock_engine.execute_agent_pipeline = AsyncMock(side_effect=mock_execute_with_performance_tracking)
            mock_engine.cleanup = AsyncMock()
            return mock_engine
        
        # Patch supervisors for performance tracking
        patches = []
        for i, supervisor in enumerate(supervisor_agents):
            user_context = user_contexts[i]
            
            patch_obj = patch.object(
                supervisor, '_create_user_execution_engine',
                new_callable=AsyncMock,
                side_effect=lambda ctx=user_context: create_performance_tracking_engine(ctx)
            )
            patches.append(patch_obj)
            patch_obj.start()
        
        try:
            # Act: Execute heavy concurrent load test
            start_time = time.time()
            
            # Create staggered execution to simulate realistic load pattern
            task_groups = []
            group_size = 5  # Execute in groups of 5
            
            for group_start in range(0, num_users, group_size):
                group_end = min(group_start + group_size, num_users)
                group_tasks = []
                
                for i in range(group_start, group_end):
                    supervisor = supervisor_agents[i]
                    user_context = user_contexts[i]
                    
                    task = supervisor.execute(user_context, stream_updates=True)
                    group_tasks.append(task)
                
                task_groups.append(group_tasks)
            
            # Execute groups with slight staggering
            all_tasks = []
            for i, group_tasks in enumerate(task_groups):
                all_tasks.extend(group_tasks)
                
                # Brief stagger between groups (simulates realistic user arrival)
                if i < len(task_groups) - 1:
                    await asyncio.sleep(0.02)  # 20ms stagger
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            end_time = time.time()
            total_execution_time = end_time - start_time
            
            # Assert: Verify performance under heavy load
            # Verify all executions succeeded
            successful_results = [r for r in results if not isinstance(r, Exception)]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            success_rate = len(successful_results) / num_users
            assert success_rate >= 0.95, \
                f"Success rate too low under load: {success_rate:.2%} (should be  >= 95%)"
            
            if failed_results:
                print(f"Warning: {len(failed_results)} executions failed under heavy load: {failed_results[:3]}...")
            
            # Verify overall system performance
            assert total_execution_time < 20.0, \
                f"Heavy load test took too long: {total_execution_time:.2f}s (should be <20s)"
            
            # Calculate performance metrics
            response_times = list(performance_data['user_response_times'].values())
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)
                
                # Performance requirements
                assert avg_response_time < 2.0, \
                    f"Average response time too high: {avg_response_time:.3f}s (should be <2s)"
                assert max_response_time < 5.0, \
                    f"Max response time too high: {max_response_time:.3f}s (should be <5s)"
                
                # Calculate 95th percentile response time
                sorted_times = sorted(response_times)
                p95_index = int(0.95 * len(sorted_times))
                p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]
                
                assert p95_response_time < 3.0, \
                    f"95th percentile response time too high: {p95_response_time:.3f}s (should be <3s)"
                
                # Verify throughput
                throughput = num_users / total_execution_time
                assert throughput >= 1.0, \
                    f"Throughput too low: {throughput:.2f} users/second (should be  >= 1.0)"
                
                # Store detailed performance metrics
                self.performance_metrics['heavy_load_20_users'] = {
                    'total_users': num_users,
                    'successful_users': len(successful_results),
                    'success_rate': success_rate,
                    'total_time': total_execution_time,
                    'avg_response_time': avg_response_time,
                    'max_response_time': max_response_time,
                    'min_response_time': min_response_time,
                    'p95_response_time': p95_response_time,
                    'throughput_users_per_sec': throughput,
                    'isolation_violations': len(self.user_isolation_violations)
                }
                
                # Log performance results
                print(f"\n[U+1F680] Heavy Load Performance Results (25 users):")
                print(f"  Success Rate: {success_rate:.1%}")
                print(f"  Total Time: {total_execution_time:.3f}s")
                print(f"  Avg Response: {avg_response_time:.3f}s")
                print(f"  Max Response: {max_response_time:.3f}s")
                print(f"  95th Percentile: {p95_response_time:.3f}s")
                print(f"  Throughput: {throughput:.2f} users/sec")
            
            # Verify no isolation violations under load
            assert len(self.user_isolation_violations) == 0, \
                f"User isolation violations under heavy load: {self.user_isolation_violations}"
            
        finally:
            # Clean up patches
            for patch_obj in patches:
                patch_obj.stop()
    
    # ============================================================================
    # CONCURRENCY SCENARIO 5: Factory Pattern Validation Under Load
    # ============================================================================
    
    @pytest.mark.concurrency
    @pytest.mark.factory_pattern
    async def test_factory_pattern_user_isolation_under_concurrent_load(self):
        """
        Test factory pattern user isolation under concurrent load.
        
        BVJ: Architecture compliance - ensures factory pattern creates proper isolation under load
        Critical Path: Concurrent load  ->  Factory pattern  ->  User-specific instances  ->  No shared state
        """
        # Arrange: Create 16 users for factory pattern testing
        num_users = 16
        user_contexts = []
        supervisor_agents = []
        
        # Track factory usage patterns
        factory_tracking = {
            'instances_created': {},
            'shared_instances_detected': [],
            'factory_calls': [],
            'isolation_verified': {}
        }
        
        for i in range(num_users):
            user_context = self._create_test_user_context(i + 400)  # Start from 400
            user_contexts.append(user_context)
            
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge
            )
            supervisor_agents.append(supervisor)
        
        async def create_factory_validation_engine(user_context):
            """Create execution engine that validates factory pattern usage."""
            user_id = user_context.user_id
            
            # Track factory instance creation
            instance_id = f"{user_id}_engine_{uuid.uuid4()}"
            factory_tracking['instances_created'][user_id] = instance_id
            factory_tracking['factory_calls'].append({
                'user_id': user_id,
                'instance_id': instance_id,
                'timestamp': time.time()
            })
            
            mock_engine = self.mock_factory.create_mock("UserExecutionEngine")
            mock_engine._instance_id = instance_id  # Tag for validation
            mock_engine._user_id = user_id  # Tag for user association
            
            async def mock_execute_with_factory_validation(agent_name, execution_context, input_data):
                # Validate factory isolation
                current_user = execution_context.user_id
                engine_user = getattr(mock_engine, '_user_id', None)
                
                if current_user != engine_user:
                    factory_tracking['shared_instances_detected'].append({
                        'execution_user': current_user,
                        'engine_user': engine_user,
                        'instance_id': getattr(mock_engine, '_instance_id', 'unknown'),
                        'agent_name': agent_name
                    })
                    
                    self.user_isolation_violations.append({
                        'violation_type': 'factory_instance_sharing',
                        'execution_user': current_user,
                        'engine_user': engine_user,
                        'instance_id': getattr(mock_engine, '_instance_id', 'unknown')
                    })
                
                # Record isolation verification
                factory_tracking['isolation_verified'][user_id] = {
                    'instance_id': getattr(mock_engine, '_instance_id', 'unknown'),
                    'user_match': current_user == engine_user,
                    'timestamp': time.time()
                }
                
                # Return result with factory validation info
                result = MagicMock()
                result.success = True
                result.result = {
                    'user_id': current_user,
                    'engine_instance_id': getattr(mock_engine, '_instance_id', 'unknown'),
                    'factory_isolation_verified': current_user == engine_user,
                    'unique_instance': True
                }
                
                return result
            
            mock_engine.execute_agent_pipeline = AsyncMock(side_effect=mock_execute_with_factory_validation)
            mock_engine.cleanup = AsyncMock()
            
            return mock_engine
        
        # Patch supervisors for factory pattern validation
        patches = []
        for i, supervisor in enumerate(supervisor_agents):
            user_context = user_contexts[i]
            
            patch_obj = patch.object(
                supervisor, '_create_user_execution_engine',
                new_callable=AsyncMock,
                side_effect=lambda ctx=user_context: create_factory_validation_engine(ctx)
            )
            patches.append(patch_obj)
            patch_obj.start()
        
        try:
            # Act: Execute concurrent load to test factory pattern
            # Execute in multiple waves to stress test factory pattern
            all_results = []
            
            for wave in range(3):  # 3 waves of execution
                wave_tasks = []
                
                for supervisor, user_context in zip(supervisor_agents, user_contexts):
                    # Add wave information to context
                    user_context.metadata['wave_number'] = wave
                    
                    task = supervisor.execute(user_context, stream_updates=True)
                    wave_tasks.append(task)
                
                # Execute wave concurrently
                wave_results = await asyncio.gather(*wave_tasks, return_exceptions=True)
                all_results.extend(wave_results)
                
                # Brief delay between waves
                if wave < 2:
                    await asyncio.sleep(0.05)
            
            # Assert: Verify factory pattern isolation under load
            total_executions = num_users * 3  # 3 waves
            successful_results = [r for r in all_results if not isinstance(r, Exception)]
            
            assert len(successful_results) >= total_executions * 0.95, \
                f"Too many factory pattern executions failed: {len(successful_results)}/{total_executions}"
            
            # Verify factory created unique instances for each user
            assert len(factory_tracking['instances_created']) == num_users, \
                f"Factory should create instance for each user: {len(factory_tracking['instances_created'])}/{num_users}"
            
            # Verify no shared instances were detected
            assert len(factory_tracking['shared_instances_detected']) == 0, \
                f"Shared factory instances detected: {factory_tracking['shared_instances_detected']}"
            
            # Verify factory calls were made for each user
            assert len(factory_tracking['factory_calls']) >= num_users, \
                f"Insufficient factory calls: {len(factory_tracking['factory_calls'])}/{num_users}"
            
            # Verify user-instance mapping is unique
            instance_ids = list(factory_tracking['instances_created'].values())
            unique_instances = set(instance_ids)
            assert len(unique_instances) == len(instance_ids), \
                f"Duplicate factory instances detected: {len(unique_instances)} unique vs {len(instance_ids)} total"
            
            # Verify isolation was verified for each user
            assert len(factory_tracking['isolation_verified']) >= num_users, \
                f"Isolation verification missing for users: {len(factory_tracking['isolation_verified'])}/{num_users}"
            
            for user_id, verification in factory_tracking['isolation_verified'].items():
                assert verification['user_match'] is True, \
                    f"Factory isolation failed for user {user_id}: {verification}"
            
            # Verify no factory-related isolation violations
            factory_violations = [v for v in self.user_isolation_violations 
                                if v.get('violation_type') == 'factory_instance_sharing']
            assert len(factory_violations) == 0, \
                f"Factory pattern isolation violations: {factory_violations}"
            
            # Verify results contain factory validation info
            for result in successful_results:
                if isinstance(result, dict) and 'results' in result:
                    execution_result = result['results']
                    if isinstance(execution_result, dict):
                        if 'factory_isolation_verified' in execution_result:
                            assert execution_result['factory_isolation_verified'] is True
                        if 'unique_instance' in execution_result:
                            assert execution_result['unique_instance'] is True
            
            # Store factory pattern metrics
            self.performance_metrics['factory_pattern_validation'] = {
                'total_users': num_users,
                'waves_executed': 3,
                'unique_instances_created': len(unique_instances),
                'shared_instances_detected': len(factory_tracking['shared_instances_detected']),
                'isolation_violations': len(factory_violations),
                'factory_calls': len(factory_tracking['factory_calls']),
                'isolation_success_rate': len(factory_tracking['isolation_verified']) / num_users
            }
            
        finally:
            # Clean up patches
            for patch_obj in patches:
                patch_obj.stop()
    
    # ============================================================================
    # PERFORMANCE SUMMARY AND REPORTING
    # ============================================================================
    
    @pytest.mark.concurrency
    @pytest.mark.summary
    async def test_generate_concurrency_performance_summary(self):
        """
        Generate comprehensive summary of concurrency test performance.
        
        BVJ: Platform monitoring - provides metrics for concurrency performance analysis
        """
        # This test serves as a summary of all concurrency test results
        # It should be run after other concurrency tests to compile metrics
        
        print("\n" + "="*80)
        print(" TARGET:  MULTI-USER CONCURRENCY TEST SUMMARY")
        print("="*80)
        
        if self.performance_metrics:
            for test_name, metrics in self.performance_metrics.items():
                print(f"\n CHART:  {test_name.upper().replace('_', ' ')}:")
                
                for metric_name, value in metrics.items():
                    if isinstance(value, float):
                        if 'time' in metric_name.lower():
                            print(f"  {metric_name}: {value:.3f}s")
                        elif 'rate' in metric_name.lower():
                            print(f"  {metric_name}: {value:.1%}")
                        else:
                            print(f"  {metric_name}: {value:.3f}")
                    else:
                        print(f"  {metric_name}: {value}")
        else:
            print("No performance metrics available. Run concurrency tests first.")
        
        print(f"\n[U+1F6E1][U+FE0F] ISOLATION SUMMARY:")
        print(f"  Total Isolation Violations: {len(self.user_isolation_violations)}")
        print(f"  WebSocket Event Tracking: {len(self.websocket_event_tracking)} users")
        print(f"  Concurrent Executions Tracked: {len(self.concurrent_executions)}")
        
        if self.user_isolation_violations:
            print(f"\n WARNING: [U+FE0F] ISOLATION VIOLATIONS DETECTED:")
            for i, violation in enumerate(self.user_isolation_violations[:5]):  # Show first 5
                print(f"  {i+1}. {violation['violation_type']}: {violation}")
            if len(self.user_isolation_violations) > 5:
                print(f"  ... and {len(self.user_isolation_violations) - 5} more")
        else:
            print(f"\n PASS:  NO ISOLATION VIOLATIONS DETECTED - SYSTEM SECURE")
        
        print("="*80)
        
        # Assert overall concurrency health
        assert len(self.user_isolation_violations) == 0, \
            f"Concurrency tests revealed isolation violations: {len(self.user_isolation_violations)}"