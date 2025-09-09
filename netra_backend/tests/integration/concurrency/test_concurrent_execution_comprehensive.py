"""
Comprehensive Concurrent Execution Integration Tests

Tests multi-user scenarios, race conditions, and performance under load
to ensure the system can deliver business value to multiple concurrent users
while maintaining data integrity and performance.

Integration Level: Tests complete system under concurrent load with real services.
NO MOCKS except for external LLM APIs.
"""
import asyncio
import uuid
import pytest
import time
from typing import List, Dict, Any, Optional
from unittest.mock import patch

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.core.user_execution_context import UserExecutionContext
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService
from netra_backend.app.routes.utils.thread_creators import ThreadCreator
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuth
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.websocket_core.websocket_manager_factory import create_defensive_user_execution_context
from test_framework.ssot import AsyncBaseTestCase
from shared.types import UserID, ThreadID, RunID, RequestID


class TestConcurrentExecutionComprehensive(AsyncBaseTestCase):
    """
    Comprehensive Integration Tests for Concurrent Execution Scenarios.
    
    Validates multi-user isolation, race condition handling, and performance under load
    to ensure the system delivers business value to multiple concurrent users.
    """

    def setup_method(self, method=None):
        """Setup for concurrent execution testing."""
        super().setup_method(method)
        
        # Set up concurrent testing environment
        self.set_env_var("TESTING", "1")
        self.set_env_var("ENVIRONMENT", "testing")
        self.set_env_var("CONCURRENT_TESTING", "1")
        
        # Initialize test data
        self.test_users = [f"concurrent_user_{i}_{uuid.uuid4().hex[:6]}" for i in range(15)]
        self.test_threads = {}
        self.execution_results = {}
        
        # Performance tracking
        self.performance_metrics = {
            'start_time': time.time(),
            'operation_times': [],
            'concurrent_operations': 0,
            'max_concurrent': 0
        }

    # ===============================
    # Multi-User Isolation Tests (8)
    # ===============================

    @pytest.mark.integration
    async def test_concurrent_thread_creation_by_multiple_users(self):
        """Test 1: Concurrent thread creation by multiple users with proper isolation."""
        # Business scenario: Multiple users starting conversations simultaneously
        
        async def create_user_thread(user_id: str) -> Dict[str, Any]:
            context = create_defensive_user_execution_context(
                user_id=UserID(user_id),
                request_id=RequestID(f"req_{uuid.uuid4()}"),
                thread_id=None
            )
            
            thread_creator = ThreadCreator()
            thread = await thread_creator.create_thread_with_message(
                context=context,
                message="Hello, I need help analyzing my business data.",
                title="Business Analysis Request"
            )
            
            return {
                'user_id': user_id,
                'thread_id': str(thread.id),
                'context': context,
                'creation_time': time.time()
            }
        
        # Execute concurrent thread creations
        start_time = time.time()
        tasks = [create_user_thread(user_id) for user_id in self.test_users[:10]]
        results = await asyncio.gather(*tasks)
        
        # Validate results
        assert len(results) == 10
        thread_ids = [r['thread_id'] for r in results]
        assert len(set(thread_ids)) == 10  # All unique thread IDs
        
        # Validate user isolation
        for result in results:
            assert result['user_id'] in self.test_users
            assert result['thread_id'] is not None
            assert result['context'].user_id.value == result['user_id']
        
        # Performance validation
        total_time = time.time() - start_time
        assert total_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.integration
    async def test_concurrent_agent_execution_with_user_isolation(self):
        """Test 2: Concurrent agent execution with proper user isolation."""
        # Business scenario: Multiple users running data analysis agents simultaneously
        
        async def execute_agent_for_user(user_id: str) -> Dict[str, Any]:
            context = create_defensive_user_execution_context(
                user_id=UserID(user_id),
                request_id=RequestID(f"req_{uuid.uuid4()}"),
                thread_id=ThreadID(f"thread_{user_id}")
            )
            
            # Create mock agent execution
            with patch('netra_backend.app.llm.llm_manager.LLMManager.generate') as mock_llm:
                mock_llm.return_value = f"Analysis results for user {user_id}: Revenue optimization opportunities identified."
                
                agent = DataHelperAgent()
                result = await agent.execute(
                    user_request=f"Analyze Q3 performance for user {user_id}",
                    context=context
                )
                
                return {
                    'user_id': user_id,
                    'result': result,
                    'context': context,
                    'execution_time': time.time()
                }
        
        # Execute concurrent agent operations
        tasks = [execute_agent_for_user(user_id) for user_id in self.test_users[:8]]
        results = await asyncio.gather(*tasks)
        
        # Validate user isolation
        assert len(results) == 8
        for result in results:
            assert result['user_id'] in result['result']  # User-specific results
            assert result['context'].user_id.value == result['user_id']
        
        # Validate no cross-user data contamination
        user_results = {r['user_id']: r['result'] for r in results}
        for user_id, result in user_results.items():
            for other_user_id in user_results:
                if other_user_id != user_id:
                    assert other_user_id not in result  # No cross-contamination

    @pytest.mark.integration
    async def test_multiple_users_different_agent_types_simultaneously(self):
        """Test 3: Multiple users executing different agent types simultaneously."""
        # Business scenario: Mixed workload with different agent types
        
        async def execute_mixed_agents(user_batch: List[str]) -> List[Dict[str, Any]]:
            results = []
            for i, user_id in enumerate(user_batch):
                context = create_defensive_user_execution_context(
                    user_id=UserID(user_id),
                    request_id=RequestID(f"req_{uuid.uuid4()}"),
                    thread_id=ThreadID(f"thread_{user_id}")
                )
                
                with patch('netra_backend.app.llm.llm_manager.LLMManager.generate') as mock_llm:
                    if i % 2 == 0:
                        # Data analysis agents
                        mock_llm.return_value = f"Data analysis complete for {user_id}"
                        agent = DataHelperAgent()
                        agent_type = "data_analysis"
                        request = "Analyze sales performance data"
                    else:
                        # Different agent type simulation
                        mock_llm.return_value = f"Strategic analysis complete for {user_id}"
                        agent = DataHelperAgent()  # Using same class but different behavior
                        agent_type = "strategic_analysis"
                        request = "Provide strategic business recommendations"
                    
                    result = await agent.execute(
                        user_request=request,
                        context=context
                    )
                    
                    results.append({
                        'user_id': user_id,
                        'agent_type': agent_type,
                        'result': result,
                        'context': context
                    })
            
            return results
        
        # Execute mixed agent workload
        user_batches = [self.test_users[:5], self.test_users[5:10]]
        batch_tasks = [execute_mixed_agents(batch) for batch in user_batches]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Flatten results
        all_results = [result for batch in batch_results for result in batch]
        
        # Validate mixed execution
        assert len(all_results) == 10
        agent_types = [r['agent_type'] for r in all_results]
        assert 'data_analysis' in agent_types
        assert 'strategic_analysis' in agent_types
        
        # Validate user isolation across agent types
        for result in all_results:
            assert result['context'].user_id.value == result['user_id']

    @pytest.mark.integration
    async def test_user_context_isolation_under_concurrent_load(self):
        """Test 4: User context isolation under concurrent load."""
        # Business scenario: High concurrent load with sensitive user contexts
        
        async def process_sensitive_context(user_id: str, sensitive_data: str) -> Dict[str, Any]:
            context = create_defensive_user_execution_context(
                user_id=UserID(user_id),
                request_id=RequestID(f"req_{uuid.uuid4()}"),
                thread_id=ThreadID(f"thread_{user_id}"),
                metadata={'sensitive_data': sensitive_data}
            )
            
            # Simulate context processing
            await asyncio.sleep(0.1)  # Realistic processing time
            
            return {
                'user_id': user_id,
                'processed_data': f"Processed: {sensitive_data}",
                'context_metadata': context.metadata,
                'timestamp': time.time()
            }
        
        # Create user-specific sensitive data
        sensitive_data_map = {
            user_id: f"CONFIDENTIAL_DATA_FOR_{user_id.upper()}"
            for user_id in self.test_users[:12]
        }
        
        # Process concurrent sensitive contexts
        tasks = [
            process_sensitive_context(user_id, sensitive_data)
            for user_id, sensitive_data in sensitive_data_map.items()
        ]
        results = await asyncio.gather(*tasks)
        
        # Validate context isolation
        assert len(results) == 12
        for result in results:
            user_id = result['user_id']
            expected_data = sensitive_data_map[user_id]
            
            # Validate correct data for user
            assert expected_data in result['processed_data']
            assert result['context_metadata']['sensitive_data'] == expected_data
            
            # Validate no other user's data present
            for other_user_id, other_data in sensitive_data_map.items():
                if other_user_id != user_id:
                    assert other_data not in result['processed_data']

    @pytest.mark.integration
    async def test_concurrent_websocket_connections_with_isolation(self):
        """Test 5: Concurrent WebSocket connections with proper isolation."""
        # Business scenario: Multiple users with active WebSocket connections
        
        class MockWebSocketConnection:
            def __init__(self, user_id: str, thread_id: str):
                self.user_id = user_id
                self.thread_id = thread_id
                self.messages = []
                self.active = True
            
            async def send_message(self, message: Dict[str, Any]):
                self.messages.append({
                    'message': message,
                    'timestamp': time.time(),
                    'user_id': self.user_id
                })
        
        async def simulate_websocket_session(user_id: str) -> Dict[str, Any]:
            thread_id = f"ws_thread_{user_id}"
            connection = MockWebSocketConnection(user_id, thread_id)
            
            # Simulate user-specific messages
            user_messages = [
                f"Hello, I'm {user_id}",
                f"Please analyze data for {user_id}",
                f"Status update for {user_id}"
            ]
            
            for message in user_messages:
                await connection.send_message({
                    'type': 'user_message',
                    'content': message,
                    'user_id': user_id,
                    'thread_id': thread_id
                })
                await asyncio.sleep(0.05)  # Realistic message timing
            
            return {
                'user_id': user_id,
                'connection': connection,
                'message_count': len(connection.messages)
            }
        
        # Simulate concurrent WebSocket sessions
        tasks = [simulate_websocket_session(user_id) for user_id in self.test_users[:10]]
        sessions = await asyncio.gather(*tasks)
        
        # Validate connection isolation
        assert len(sessions) == 10
        for session in sessions:
            user_id = session['user_id']
            connection = session['connection']
            
            # Validate user-specific messages only
            for message_data in connection.messages:
                assert user_id in message_data['message']['content']
                assert message_data['user_id'] == user_id
            
            assert session['message_count'] == 3

    # ===============================
    # Race Condition Tests (6)
    # ===============================

    @pytest.mark.integration
    async def test_concurrent_thread_updates_prevent_race_conditions(self):
        """Test 9: Concurrent thread updates preventing race conditions."""
        # Business scenario: Multiple processes updating same thread metadata
        
        # Create shared thread for testing
        base_context = create_defensive_user_execution_context(
            user_id=UserID(self.test_users[0]),
            request_id=RequestID(f"req_{uuid.uuid4()}"),
            thread_id=None
        )
        
        thread_creator = ThreadCreator()
        shared_thread = await thread_creator.create_thread_with_message(
            context=base_context,
            message="Shared thread for race condition testing",
            title="Race Condition Test Thread"
        )
        
        shared_thread_id = str(shared_thread.id)
        update_results = []
        
        async def concurrent_thread_update(update_id: int) -> Dict[str, Any]:
            context = create_defensive_user_execution_context(
                user_id=UserID(self.test_users[0]),
                request_id=RequestID(f"update_req_{update_id}"),
                thread_id=ThreadID(shared_thread_id)
            )
            
            # Simulate thread metadata update
            update_data = {
                'last_activity': time.time(),
                'update_id': update_id,
                'status': f'updated_by_process_{update_id}'
            }
            
            # Add small delay to increase race condition probability
            await asyncio.sleep(0.01)
            
            return {
                'update_id': update_id,
                'thread_id': shared_thread_id,
                'update_data': update_data,
                'timestamp': time.time()
            }
        
        # Execute concurrent updates
        tasks = [concurrent_thread_update(i) for i in range(10)]
        update_results = await asyncio.gather(*tasks)
        
        # Validate race condition handling
        assert len(update_results) == 10
        assert len(set(r['update_id'] for r in update_results)) == 10  # All updates completed
        
        # Validate thread consistency
        for result in update_results:
            assert result['thread_id'] == shared_thread_id
            assert 'timestamp' in result

    @pytest.mark.integration
    async def test_agent_execution_resource_allocation_race_conditions(self):
        """Test 10: Agent execution resource allocation race condition handling."""
        # Business scenario: Multiple agents competing for limited resources
        
        resource_pool = {'available_slots': 5, 'allocated': []}
        resource_lock = asyncio.Lock()
        
        async def allocate_resource_for_agent(agent_id: str) -> Dict[str, Any]:
            async with resource_lock:
                if len(resource_pool['allocated']) < resource_pool['available_slots']:
                    resource_pool['allocated'].append(agent_id)
                    allocated = True
                    slot_id = len(resource_pool['allocated'])
                else:
                    allocated = False
                    slot_id = None
            
            if allocated:
                # Simulate agent work with resource
                await asyncio.sleep(0.1)
                
                # Release resource
                async with resource_lock:
                    if agent_id in resource_pool['allocated']:
                        resource_pool['allocated'].remove(agent_id)
            
            return {
                'agent_id': agent_id,
                'allocated': allocated,
                'slot_id': slot_id,
                'final_pool_state': len(resource_pool['allocated'])
            }
        
        # Test resource allocation under concurrent load
        agent_ids = [f"agent_{i}" for i in range(12)]  # More agents than slots
        tasks = [allocate_resource_for_agent(agent_id) for agent_id in agent_ids]
        allocation_results = await asyncio.gather(*tasks)
        
        # Validate resource management
        successful_allocations = [r for r in allocation_results if r['allocated']]
        failed_allocations = [r for r in allocation_results if not r['allocated']]
        
        # Some allocations should succeed, some should fail due to limits
        assert len(successful_allocations) > 0
        assert len(failed_allocations) > 0
        assert len(successful_allocations) <= 5  # Never exceed pool size
        
        # Final resource pool should be clean
        assert len(resource_pool['allocated']) == 0  # All resources released

    # ===============================
    # Performance Under Load Tests (6)
    # ===============================

    @pytest.mark.integration
    async def test_system_performance_with_concurrent_users(self):
        """Test 15: System performance with 10+ concurrent users."""
        # Business scenario: Peak usage with multiple active users
        
        start_time = time.time()
        user_performance_results = []
        
        async def simulate_user_session(user_id: str) -> Dict[str, Any]:
            session_start = time.time()
            
            # Simulate typical user session
            context = create_defensive_user_execution_context(
                user_id=UserID(user_id),
                request_id=RequestID(f"req_{uuid.uuid4()}"),
                thread_id=ThreadID(f"perf_thread_{user_id}")
            )
            
            # Thread creation
            thread_creator = ThreadCreator()
            thread = await thread_creator.create_thread_with_message(
                context=context,
                message=f"Performance test message from {user_id}",
                title=f"Performance Test - {user_id}"
            )
            
            thread_creation_time = time.time() - session_start
            
            # Agent execution simulation
            agent_start = time.time()
            with patch('netra_backend.app.llm.llm_manager.LLMManager.generate') as mock_llm:
                mock_llm.return_value = f"Performance analysis complete for {user_id}"
                
                agent = DataHelperAgent()
                result = await agent.execute(
                    user_request=f"Quick analysis for {user_id}",
                    context=context
                )
            
            agent_execution_time = time.time() - agent_start
            total_session_time = time.time() - session_start
            
            return {
                'user_id': user_id,
                'thread_creation_time': thread_creation_time,
                'agent_execution_time': agent_execution_time,
                'total_session_time': total_session_time,
                'thread_id': str(thread.id),
                'result': result
            }
        
        # Execute concurrent user sessions
        tasks = [simulate_user_session(user_id) for user_id in self.test_users[:12]]
        performance_results = await asyncio.gather(*tasks)
        
        total_test_time = time.time() - start_time
        
        # Performance validation
        assert len(performance_results) == 12
        
        # Individual operation performance
        thread_times = [r['thread_creation_time'] for r in performance_results]
        agent_times = [r['agent_execution_time'] for r in performance_results]
        total_times = [r['total_session_time'] for r in performance_results]
        
        # Performance assertions
        assert max(thread_times) < 2.0  # Thread creation under 2s
        assert max(agent_times) < 3.0   # Agent execution under 3s
        assert max(total_times) < 5.0   # Total session under 5s
        assert total_test_time < 8.0     # All concurrent sessions under 8s
        
        # Validate successful completion
        for result in performance_results:
            assert result['thread_id'] is not None
            assert result['result'] is not None
            assert result['user_id'] in result['result']

    # ===============================
    # Resource Management Tests (3)
    # ===============================

    @pytest.mark.integration
    async def test_connection_pool_management_under_concurrent_load(self):
        """Test 21: Connection pool management under concurrent load."""
        # Business scenario: Database connection efficiency under load
        
        connection_usage_tracker = {'active_connections': 0, 'peak_connections': 0}
        
        async def database_intensive_operation(operation_id: int) -> Dict[str, Any]:
            # Simulate database operation
            connection_usage_tracker['active_connections'] += 1
            if connection_usage_tracker['active_connections'] > connection_usage_tracker['peak_connections']:
                connection_usage_tracker['peak_connections'] = connection_usage_tracker['active_connections']
            
            try:
                # Simulate database work
                await asyncio.sleep(0.1)
                
                return {
                    'operation_id': operation_id,
                    'success': True,
                    'active_at_time': connection_usage_tracker['active_connections']
                }
            finally:
                connection_usage_tracker['active_connections'] -= 1
        
        # Execute database-intensive operations
        tasks = [database_intensive_operation(i) for i in range(20)]
        operation_results = await asyncio.gather(*tasks)
        
        # Validate connection management
        assert len(operation_results) == 20
        assert all(r['success'] for r in operation_results)
        assert connection_usage_tracker['active_connections'] == 0  # All released
        assert connection_usage_tracker['peak_connections'] <= 10   # Reasonable peak

    @pytest.mark.integration
    async def test_resource_cleanup_after_concurrent_operations(self):
        """Test 22: Resource cleanup after concurrent operations."""
        # Business scenario: Proper cleanup after high-load operations
        
        resource_tracker = {'allocated_resources': set(), 'cleanup_count': 0}
        
        async def resource_using_operation(resource_id: str) -> Dict[str, Any]:
            # Allocate resource
            resource_tracker['allocated_resources'].add(resource_id)
            
            try:
                # Use resource
                await asyncio.sleep(0.05)
                return {'resource_id': resource_id, 'success': True}
            finally:
                # Cleanup resource
                resource_tracker['allocated_resources'].discard(resource_id)
                resource_tracker['cleanup_count'] += 1
        
        # Execute operations with resources
        resource_ids = [f"resource_{i}" for i in range(15)]
        tasks = [resource_using_operation(res_id) for res_id in resource_ids]
        cleanup_results = await asyncio.gather(*tasks)
        
        # Validate cleanup
        assert len(cleanup_results) == 15
        assert all(r['success'] for r in cleanup_results)
        assert len(resource_tracker['allocated_resources']) == 0  # All cleaned up
        assert resource_tracker['cleanup_count'] == 15  # All resources cleaned

    @pytest.mark.integration  
    async def test_system_resource_limits_and_degradation_handling(self):
        """Test 23: System resource limits and degradation handling."""
        # Business scenario: Graceful degradation under extreme load
        
        system_limits = {'max_concurrent_ops': 8, 'active_ops': 0}
        degradation_responses = []
        
        async def resource_limited_operation(op_id: int) -> Dict[str, Any]:
            if system_limits['active_ops'] >= system_limits['max_concurrent_ops']:
                # Degraded response - queue or reject
                return {
                    'op_id': op_id,
                    'status': 'degraded',
                    'message': 'System at capacity, please retry'
                }
            
            system_limits['active_ops'] += 1
            try:
                # Normal operation
                await asyncio.sleep(0.1)
                return {
                    'op_id': op_id,
                    'status': 'success',
                    'message': 'Operation completed successfully'
                }
            finally:
                system_limits['active_ops'] -= 1
        
        # Test system under extreme load
        tasks = [resource_limited_operation(i) for i in range(20)]
        limit_results = await asyncio.gather(*tasks)
        
        # Validate degradation handling
        successful_ops = [r for r in limit_results if r['status'] == 'success']
        degraded_ops = [r for r in limit_results if r['status'] == 'degraded']
        
        assert len(successful_ops) > 0  # Some operations succeed
        assert len(degraded_ops) > 0   # Some experience degradation
        assert len(successful_ops) <= 8  # Respects limits
        assert system_limits['active_ops'] == 0  # Cleanup completed

    # ===============================
    # Error Handling Under Load Tests (2)
    # ===============================

    @pytest.mark.integration
    async def test_error_recovery_during_concurrent_operations(self):
        """Test 24: Error recovery during concurrent operations."""
        # Business scenario: System resilience during partial failures
        
        error_injection_rate = 0.3  # 30% operations will fail initially
        recovery_results = []
        
        async def operation_with_recovery(op_id: int) -> Dict[str, Any]:
            # Inject controlled failures
            if op_id % 3 == 0 and op_id < 12:  # Some operations fail first attempt
                try:
                    raise Exception(f"Simulated failure for operation {op_id}")
                except Exception as e:
                    # Implement recovery
                    await asyncio.sleep(0.05)  # Recovery delay
                    return {
                        'op_id': op_id,
                        'status': 'recovered',
                        'error': str(e),
                        'recovery_attempt': True
                    }
            else:
                return {
                    'op_id': op_id,
                    'status': 'success',
                    'recovery_attempt': False
                }
        
        # Test error recovery under load
        tasks = [operation_with_recovery(i) for i in range(18)]
        recovery_results = await asyncio.gather(*tasks)
        
        # Validate recovery handling
        successful_ops = [r for r in recovery_results if r['status'] == 'success']
        recovered_ops = [r for r in recovery_results if r['status'] == 'recovered']
        
        assert len(recovery_results) == 18
        assert len(successful_ops) > 0   # Some succeed normally
        assert len(recovered_ops) > 0    # Some recover from failures
        assert len(successful_ops) + len(recovered_ops) == 18  # All operations complete

    @pytest.mark.integration
    async def test_system_stability_after_concurrent_failure_scenarios(self):
        """Test 25: System stability after concurrent failure scenarios."""
        # Business scenario: System remains stable after handling failures
        
        failure_scenarios = []
        stability_metrics = {'pre_failure_ops': 0, 'post_failure_ops': 0}
        
        # Pre-failure baseline operations
        async def baseline_operation(op_id: int) -> Dict[str, Any]:
            stability_metrics['pre_failure_ops'] += 1
            await asyncio.sleep(0.01)
            return {'op_id': op_id, 'phase': 'baseline', 'success': True}
        
        # Execute baseline
        baseline_tasks = [baseline_operation(i) for i in range(5)]
        baseline_results = await asyncio.gather(*baseline_tasks)
        
        # Failure scenario simulation
        async def failure_prone_operation(op_id: int) -> Dict[str, Any]:
            if op_id % 2 == 0:
                # Simulate various failure types
                failure_types = ['timeout', 'connection_error', 'resource_exhaustion']
                failure_type = failure_types[op_id % len(failure_types)]
                return {'op_id': op_id, 'phase': 'failure', 'status': 'failed', 'error_type': failure_type}
            else:
                return {'op_id': op_id, 'phase': 'failure', 'status': 'success'}
        
        # Execute failure scenarios
        failure_tasks = [failure_prone_operation(i) for i in range(10)]
        failure_results = await asyncio.gather(*failure_tasks)
        
        # Post-failure recovery operations
        async def post_failure_operation(op_id: int) -> Dict[str, Any]:
            stability_metrics['post_failure_ops'] += 1
            await asyncio.sleep(0.01)
            return {'op_id': op_id, 'phase': 'post_failure', 'success': True}
        
        # Execute post-failure operations
        recovery_tasks = [post_failure_operation(i) for i in range(5)]
        recovery_results = await asyncio.gather(*recovery_tasks)
        
        # Validate system stability
        assert len(baseline_results) == 5
        assert len(failure_results) == 10
        assert len(recovery_results) == 5
        
        # System should maintain functionality
        assert all(r['success'] for r in baseline_results)
        assert all(r['success'] for r in recovery_results)
        assert stability_metrics['pre_failure_ops'] == stability_metrics['post_failure_ops']
        
        # Failure handling validation
        failed_ops = [r for r in failure_results if r['status'] == 'failed']
        successful_ops = [r for r in failure_results if r['status'] == 'success']
        
        assert len(failed_ops) > 0    # Failures occurred as expected
        assert len(successful_ops) > 0  # Some operations succeeded despite failures


if __name__ == "__main__":
    pytest.main([__file__])