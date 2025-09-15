"""
Multi-User WebSocket Isolation Tests - UnifiedIDManager Phase 2

Integration tests validating proper user isolation in WebSocket connections
with UnifiedIDManager. Tests concurrent user scenarios to prevent cross-user
state contamination.

Business Value Justification:
- Segment: Enterprise/All (Multi-user isolation critical for data security)
- Business Goal: Data Security & Regulatory Compliance
- Value Impact: Prevents user data leakage and enables HIPAA/SOC2 compliance
- Strategic Impact: Enterprise sales depend on proper user isolation
"""

import pytest
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


@pytest.mark.integration
@pytest.mark.real_services
class MultiUserWebSocketIsolationTests(SSotBaseTestCase):
    """
    Test multi-user WebSocket isolation with UnifiedIDManager.

    Validates that concurrent users have properly isolated
    WebSocket connections, IDs, and contexts.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()

    async def test_concurrent_websocket_connection_isolation(self, real_services_fixture):
        """
        Test concurrent WebSocket connections maintain user isolation.

        Creates multiple concurrent users, each establishing WebSocket
        connections, and validates no cross-user state contamination.
        """
        # Test configuration
        num_users = 20
        connections_per_user = 3
        concurrent_workers = 5

        # Track results
        all_connection_data = {}
        isolation_violations = []

        def create_user_websocket_connections(user_index):
            """Create WebSocket connections for a single user."""
            user_id = f"test_user_{user_index}"
            user_connections = []

            # Simulate user-specific context
            user_context = {
                'user_id': user_id,
                'session_start': threading.current_thread().ident,
                'test_scenario': 'multi_user_isolation'
            }

            # Create multiple connections for this user
            for conn_index in range(connections_per_user):
                # Generate connection-specific IDs using UnifiedIDManager
                connection_id = self.id_manager.generate_id(
                    IDType.WEBSOCKET,
                    prefix=f"user_{user_index}_conn_{conn_index}",
                    context=user_context
                )

                thread_id = self.id_manager.generate_id(
                    IDType.THREAD,
                    prefix=f"chat_{user_index}_{conn_index}",
                    context=user_context
                )

                run_id = self.id_manager.generate_id(
                    IDType.EXECUTION,
                    prefix=f"exec_{user_index}_{conn_index}",
                    context=user_context
                )

                connection_data = {
                    'user_id': user_id,
                    'connection_id': connection_id,
                    'thread_id': thread_id,
                    'run_id': run_id,
                    'user_context': user_context,
                    'thread_ident': threading.current_thread().ident
                }

                user_connections.append(connection_data)

            return user_id, user_connections

        # Execute concurrent user connection creation
        with ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            futures = [executor.submit(create_user_websocket_connections, i) for i in range(num_users)]

            for future in as_completed(futures):
                user_id, user_connections = future.result()
                all_connection_data[user_id] = user_connections

        # Validate isolation results
        total_connections = num_users * connections_per_user

        # Collect all connection IDs
        all_connection_ids = []
        all_thread_ids = []
        all_run_ids = []

        for user_id, user_connections in all_connection_data.items():
            for conn_data in user_connections:
                all_connection_ids.append(conn_data['connection_id'])
                all_thread_ids.append(conn_data['thread_id'])
                all_run_ids.append(conn_data['run_id'])

        # Test 1: All IDs must be unique (no duplicates)
        connection_uniqueness = len(set(all_connection_ids)) == len(all_connection_ids)
        thread_uniqueness = len(set(all_thread_ids)) == len(all_thread_ids)
        run_uniqueness = len(set(all_run_ids)) == len(all_run_ids)

        if not connection_uniqueness:
            isolation_violations.append('connection_id_duplicates')
        if not thread_uniqueness:
            isolation_violations.append('thread_id_duplicates')
        if not run_uniqueness:
            isolation_violations.append('run_id_duplicates')

        # Test 2: All IDs must be UnifiedIDManager compatible format
        incompatible_connections = [
            conn_id for conn_id in all_connection_ids
            if not self.id_manager.is_valid_id_format_compatible(conn_id)
        ]

        incompatible_threads = [
            thread_id for thread_id in all_thread_ids
            if not self.id_manager.is_valid_id_format_compatible(thread_id)
        ]

        incompatible_runs = [
            run_id for run_id in all_run_ids
            if not self.id_manager.is_valid_id_format_compatible(run_id)
        ]

        if incompatible_connections:
            isolation_violations.append(f'incompatible_connection_ids: {len(incompatible_connections)}')
        if incompatible_threads:
            isolation_violations.append(f'incompatible_thread_ids: {len(incompatible_threads)}')
        if incompatible_runs:
            isolation_violations.append(f'incompatible_run_ids: {len(incompatible_runs)}')

        # Test 3: User context isolation - no cross-contamination
        user_context_violations = 0
        for user_id, user_connections in all_connection_data.items():
            user_connection_ids = {conn['connection_id'] for conn in user_connections}

            # Check that this user's IDs don't appear in other users' contexts
            for other_user_id, other_user_connections in all_connection_data.items():
                if other_user_id != user_id:
                    other_connection_ids = {conn['connection_id'] for conn in other_user_connections}
                    overlap = user_connection_ids & other_connection_ids
                    if overlap:
                        user_context_violations += len(overlap)

        if user_context_violations > 0:
            isolation_violations.append(f'cross_user_context_contamination: {user_context_violations}')

        # Record comprehensive metrics
        self.record_metric('multi_user_isolation_test_results', {
            'total_users': num_users,
            'connections_per_user': connections_per_user,
            'total_connections': total_connections,
            'unique_connection_ids': len(set(all_connection_ids)),
            'unique_thread_ids': len(set(all_thread_ids)),
            'unique_run_ids': len(set(all_run_ids)),
            'incompatible_connections': len(incompatible_connections),
            'incompatible_threads': len(incompatible_threads),
            'incompatible_runs': len(incompatible_runs),
            'user_context_violations': user_context_violations,
            'isolation_violations': isolation_violations
        })

        # Assert perfect isolation
        assert len(isolation_violations) == 0, \
            f"Multi-user WebSocket isolation violations detected: {isolation_violations}. " \
            f"Generated {total_connections} connections for {num_users} users. " \
            f"This is critical for enterprise data security and regulatory compliance."

    async def test_websocket_id_user_context_binding(self, real_services_fixture):
        """
        Test WebSocket IDs properly bind to user contexts.

        Validates that WebSocket-generated IDs maintain proper
        association with their originating user context.
        """
        # Test with different user personas
        user_personas = [
            {'user_id': 'enterprise_admin_001', 'role': 'admin', 'tier': 'enterprise'},
            {'user_id': 'healthcare_user_002', 'role': 'clinician', 'tier': 'healthcare'},
            {'user_id': 'financial_analyst_003', 'role': 'analyst', 'tier': 'financial'},
            {'user_id': 'startup_founder_004', 'role': 'founder', 'tier': 'startup'},
            {'user_id': 'developer_tester_005', 'role': 'developer', 'tier': 'internal'}
        ]

        user_id_mappings = {}

        for persona in user_personas:
            user_id = persona['user_id']
            user_context = {
                'user_id': user_id,
                'role': persona['role'],
                'tier': persona['tier'],
                'compliance_level': 'HIPAA' if persona['tier'] == 'healthcare' else 'SOC2'
            }

            # Generate user-specific WebSocket infrastructure IDs
            websocket_connection_id = self.id_manager.generate_id(
                IDType.WEBSOCKET,
                prefix=f"ws_{persona['tier']}",
                context=user_context
            )

            chat_thread_id = self.id_manager.generate_id(
                IDType.THREAD,
                prefix=f"chat_{persona['role']}",
                context=user_context
            )

            agent_execution_id = self.id_manager.generate_id(
                IDType.EXECUTION,
                prefix=f"agent_{persona['tier']}",
                context=user_context
            )

            user_id_mappings[user_id] = {
                'persona': persona,
                'websocket_connection_id': websocket_connection_id,
                'chat_thread_id': chat_thread_id,
                'agent_execution_id': agent_execution_id,
                'user_context': user_context
            }

            # Validate ID metadata binding
            websocket_metadata = self.id_manager.get_id_metadata(websocket_connection_id)
            thread_metadata = self.id_manager.get_id_metadata(chat_thread_id)
            execution_metadata = self.id_manager.get_id_metadata(agent_execution_id)

            # Verify context binding
            assert websocket_metadata is not None, f"WebSocket ID {websocket_connection_id} not registered"
            assert thread_metadata is not None, f"Thread ID {chat_thread_id} not registered"
            assert execution_metadata is not None, f"Execution ID {agent_execution_id} not registered"

            # Verify user context preservation
            assert websocket_metadata.context.get('user_id') == user_id
            assert thread_metadata.context.get('role') == persona['role']
            assert execution_metadata.context.get('tier') == persona['tier']

        # Validate no cross-user context contamination
        context_contamination_issues = []

        for user_id_1, mapping_1 in user_id_mappings.items():
            for user_id_2, mapping_2 in user_id_mappings.items():
                if user_id_1 != user_id_2:
                    # User 1's IDs should not appear in User 2's ID registry with User 2's context
                    user_1_ids = [
                        mapping_1['websocket_connection_id'],
                        mapping_1['chat_thread_id'],
                        mapping_1['agent_execution_id']
                    ]

                    for user_1_id in user_1_ids:
                        metadata = self.id_manager.get_id_metadata(user_1_id)
                        if metadata and metadata.context.get('user_id') == user_id_2:
                            context_contamination_issues.append({
                                'id': user_1_id,
                                'expected_user': user_id_1,
                                'contaminated_with_user': user_id_2
                            })

        self.record_metric('user_context_binding_results', {
            'total_users_tested': len(user_personas),
            'total_ids_generated': len(user_personas) * 3,
            'context_contamination_issues': len(context_contamination_issues),
            'user_mappings_sample': {k: v for i, (k, v) in enumerate(user_id_mappings.items()) if i < 2}
        })

        assert len(context_contamination_issues) == 0, \
            f"Found {len(context_contamination_issues)} user context contamination issues: {context_contamination_issues}. " \
            f"User context binding is critical for enterprise security and regulatory compliance."

    async def test_websocket_performance_under_concurrent_load(self, real_services_fixture):
        """
        Test WebSocket ID generation performance under concurrent user load.

        Validates that UnifiedIDManager maintains acceptable performance
        when handling multiple concurrent WebSocket users.
        """
        import time
        import statistics

        # Performance test configuration
        num_concurrent_users = 50
        ids_per_user = 100
        max_workers = 10

        performance_results = {
            'user_generation_times': [],
            'id_generation_rates': [],
            'concurrent_performance_metrics': {}
        }

        def generate_user_websocket_ids(user_index):
            """Generate WebSocket IDs for a single user and measure performance."""
            user_id = f"perf_test_user_{user_index}"
            start_time = time.perf_counter()

            user_ids = []
            for id_index in range(ids_per_user):
                # Generate various WebSocket-related IDs
                id_types = [IDType.WEBSOCKET, IDType.THREAD, IDType.EXECUTION, IDType.REQUEST]
                for id_type in id_types:
                    generated_id = self.id_manager.generate_id(
                        id_type,
                        prefix=f"user_{user_index}_{id_index}",
                        context={'user_id': user_id, 'performance_test': True}
                    )
                    user_ids.append(generated_id)

            end_time = time.perf_counter()
            generation_time = end_time - start_time
            ids_generated = len(user_ids)
            generation_rate = ids_generated / generation_time if generation_time > 0 else 0

            return {
                'user_index': user_index,
                'user_id': user_id,
                'ids_generated': ids_generated,
                'generation_time': generation_time,
                'generation_rate': generation_rate,
                'sample_ids': user_ids[:5]  # Sample for validation
            }

        # Execute concurrent ID generation
        concurrent_start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(generate_user_websocket_ids, i) for i in range(num_concurrent_users)]
            results = [future.result() for future in as_completed(futures)]

        concurrent_end_time = time.perf_counter()
        total_concurrent_time = concurrent_end_time - concurrent_start_time

        # Analyze performance results
        generation_times = [r['generation_time'] for r in results]
        generation_rates = [r['generation_rate'] for r in results]
        total_ids_generated = sum(r['ids_generated'] for r in results)

        # Calculate statistics
        avg_generation_time = statistics.mean(generation_times)
        avg_generation_rate = statistics.mean(generation_rates)
        total_generation_rate = total_ids_generated / total_concurrent_time

        performance_results.update({
            'total_users': num_concurrent_users,
            'ids_per_user': ids_per_user * 4,  # 4 ID types per iteration
            'total_ids_generated': total_ids_generated,
            'total_concurrent_time': total_concurrent_time,
            'average_user_generation_time': avg_generation_time,
            'average_user_generation_rate': avg_generation_rate,
            'overall_generation_rate': total_generation_rate,
            'max_workers': max_workers
        })

        # Performance validation
        min_acceptable_rate_per_user = 1000  # IDs per second per user
        min_acceptable_overall_rate = 10000  # IDs per second overall
        max_acceptable_user_time = 1.0  # seconds per user

        performance_issues = []

        if avg_generation_rate < min_acceptable_rate_per_user:
            performance_issues.append(f'average_rate_too_slow: {avg_generation_rate:.1f} < {min_acceptable_rate_per_user}')

        if total_generation_rate < min_acceptable_overall_rate:
            performance_issues.append(f'overall_rate_too_slow: {total_generation_rate:.1f} < {min_acceptable_overall_rate}')

        if avg_generation_time > max_acceptable_user_time:
            performance_issues.append(f'user_generation_too_slow: {avg_generation_time:.2f}s > {max_acceptable_user_time}s')

        # Validate all generated IDs are format compatible
        format_validation_issues = []
        for result in results:
            for sample_id in result['sample_ids']:
                if not self.id_manager.is_valid_id_format_compatible(sample_id):
                    format_validation_issues.append(sample_id)

        if format_validation_issues:
            performance_issues.append(f'format_incompatible_ids: {len(format_validation_issues)}')

        self.record_metric('websocket_concurrent_performance_results', performance_results)
        self.record_metric('performance_issues', performance_issues)
        self.record_metric('format_validation_issues', len(format_validation_issues))

        assert len(performance_issues) == 0, \
            f"WebSocket ID generation performance issues under concurrent load: {performance_issues}. " \
            f"Generated {total_ids_generated} IDs for {num_concurrent_users} concurrent users " \
            f"in {total_concurrent_time:.2f}s (rate: {total_generation_rate:.1f} IDs/s). " \
            f"Performance is critical for supporting enterprise concurrent user loads."


if __name__ == '__main__':
    # MIGRATED: Use SSOT unified test runner
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category integration --pattern "*multi_user_websocket_isolation*" --real-services')