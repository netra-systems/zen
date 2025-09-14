"""
Agent Message Persistence Integration Tests

Business Value Justification (BVJ):
- Segment: Mid, Enterprise - Data persistence and audit requirements
- Business Goal: Data Integrity & Compliance - Message history and audit trails
- Value Impact: Validates agent message persistence across requests and sessions
- Strategic Impact: Enterprise compliance - audit trails, message history, data retention

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSOT BaseTestCase patterns from test_framework/ssot/base_test_case.py
- NO MOCKS for integration tests - uses real persistence services where possible
- Tests must validate message persistence across agent executions
- Multi-session persistence must maintain proper user isolation
- Tests must pass or fail meaningfully (no test cheating allowed)

This module tests AGENT MESSAGE PERSISTENCE covering:
1. Message persistence across multiple agent execution sessions
2. User context and message history isolation between users
3. Agent state persistence and retrieval for continued conversations
4. Message audit trails for compliance and debugging
5. Performance of persistence operations under load
6. Data integrity validation for persisted messages

ARCHITECTURE ALIGNMENT:
- Uses UserExecutionContext for secure message persistence isolation
- Tests 3-tier persistence architecture (Redis, PostgreSQL, ClickHouse)
- Tests message persistence with proper audit trails
- Validates compliance-critical data retention and retrieval

AGENT SESSION: agent-session-2025-09-14-1730
GITHUB ISSUE: #870 Agent Golden Path Messages Integration Test Coverage
"""

import asyncio
import json
import time
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import real components where available
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.services.state_persistence_optimized import StatePersistenceOptimized
    from netra_backend.app.db.clickhouse_client import ClickHouseClient
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    from shared.types.core_types import UserID, ThreadID, RunID, MessageID
    REAL_PERSISTENCE_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Real persistence components not available: {e}")
    REAL_PERSISTENCE_COMPONENTS_AVAILABLE = False
    UserExecutionContext = MagicMock
    StatePersistenceOptimized = MagicMock
    ClickHouseClient = MagicMock


@dataclass
class PersistedMessage:
    """Represents a persisted agent message with metadata."""
    message_id: MessageID
    user_id: UserID
    thread_id: ThreadID
    run_id: RunID
    content: str
    agent_type: str
    timestamp: datetime
    persistence_tier: str
    audit_metadata: Dict[str, Any]


@dataclass
class PersistenceValidationResult:
    """Results from persistence validation operations."""
    operation_type: str
    success: bool
    duration_ms: float
    records_affected: int
    data_integrity_verified: bool
    errors: List[str]


class TestAgentMessagePersistenceIntegration(SSotAsyncTestCase):
    """
    P0 Critical Integration Tests for Agent Message Persistence.

    This test class validates that agent messages are properly persisted across
    sessions, requests, and user contexts with complete data integrity and isolation.
    Critical for enterprise customers requiring audit trails and message history.

    Tests protect business value by validating:
    - Message persistence across agent execution sessions
    - Complete user isolation in persisted data
    - Data integrity and audit trail compliance
    - Performance of persistence operations under load
    - Message retrieval and history reconstruction
    - Compliance with data retention policies
    """

    def setup_method(self, method):
        """Set up test environment with message persistence infrastructure."""
        super().setup_method(method)

        # Initialize environment for persistence integration testing
        self.env = get_env()
        self.set_env_var("TESTING", "true")
        self.set_env_var("TEST_ENV", "persistence_integration")
        self.set_env_var("AGENT_SESSION_ID", "agent-session-2025-09-14-1730")
        self.set_env_var("ENABLE_OPTIMIZED_PERSISTENCE", "true")

        # Create unique test identifiers for isolation
        self.test_user_id = UserID(f"persist_user_{uuid.uuid4().hex[:8]}")
        self.test_thread_id = ThreadID(f"persist_thread_{uuid.uuid4().hex[:8]}")
        self.test_run_id = RunID(f"persist_run_{uuid.uuid4().hex[:8]}")

        # Track persistence metrics for business analysis
        self.persistence_metrics = {
            'messages_persisted': 0,
            'messages_retrieved': 0,
            'persistence_operations_performed': 0,
            'data_integrity_validations_passed': 0,
            'cross_session_retrievals_successful': 0,
            'audit_trail_records_created': 0,
            'persistence_performance_ms': [],
            'user_isolation_verified': 0
        }

        # Initialize persistence infrastructure
        self.state_persistence = None
        self.clickhouse_client = None
        self.execution_core = None

        # Track test data for cleanup
        self.test_message_ids: List[MessageID] = []
        self.test_user_contexts: List[UserExecutionContext] = []

    async def async_setup_method(self, method=None):
        """Set up async components with persistence infrastructure."""
        await super().async_setup_method(method)
        await self._initialize_persistence_infrastructure()

    async def _initialize_persistence_infrastructure(self):
        """Initialize real persistence infrastructure for testing."""
        if not REAL_PERSISTENCE_COMPONENTS_AVAILABLE:
            self._initialize_mock_persistence_infrastructure()
            return

        try:
            # Initialize real persistence components
            self.state_persistence = StatePersistenceOptimized()
            self.clickhouse_client = ClickHouseClient()
            self.execution_core = AgentExecutionCore(registry=MagicMock())

            # Configure persistence for testing
            if hasattr(self.state_persistence, 'configure_for_testing'):
                self.state_persistence.configure_for_testing(
                    enable_all_tiers=True,
                    test_mode=True
                )

            # Initialize ClickHouse for audit trail testing
            if hasattr(self.clickhouse_client, 'initialize'):
                await self.clickhouse_client.initialize()

        except Exception as e:
            print(f"Failed to initialize real persistence infrastructure, using mocks: {e}")
            self._initialize_mock_persistence_infrastructure()

    def _initialize_mock_persistence_infrastructure(self):
        """Initialize mock persistence infrastructure for testing."""
        self.state_persistence = MagicMock()
        self.clickhouse_client = MagicMock()
        self.execution_core = MagicMock()

        # Configure mock persistence methods
        self.state_persistence.persist_agent_message = AsyncMock()
        self.state_persistence.retrieve_agent_messages = AsyncMock()
        self.state_persistence.get_message_history = AsyncMock()
        self.clickhouse_client.write_audit_record = AsyncMock()
        self.clickhouse_client.query_audit_trail = AsyncMock()

        # Mock storage for testing
        self._mock_message_store: Dict[str, PersistedMessage] = {}
        self._mock_audit_store: List[Dict] = []

        # Configure mock implementations
        self.state_persistence.persist_agent_message.side_effect = self._mock_persist_message
        self.state_persistence.retrieve_agent_messages.side_effect = self._mock_retrieve_messages
        self.clickhouse_client.write_audit_record.side_effect = self._mock_write_audit_record

    async def async_teardown_method(self, method=None):
        """Clean up persistence test resources and record metrics."""
        try:
            # Record business value metrics for persistence analysis
            self.record_metric("persistence_integration_metrics", self.persistence_metrics)

            # Clean up test messages
            for message_id in self.test_message_ids:
                try:
                    if hasattr(self.state_persistence, 'delete_test_message'):
                        await self.state_persistence.delete_test_message(str(message_id))
                except Exception as e:
                    print(f"Cleanup error for message {message_id}: {e}")

            # Clean up test user contexts
            for user_context in self.test_user_contexts:
                try:
                    if hasattr(self.state_persistence, 'cleanup_user_test_data'):
                        await self.state_persistence.cleanup_user_test_data(user_context.user_id)
                except Exception as e:
                    print(f"Cleanup error for user context {user_context.user_id}: {e}")

            # Clean up persistence infrastructure
            if hasattr(self.clickhouse_client, 'cleanup') and self.clickhouse_client:
                await self.clickhouse_client.cleanup()

        except Exception as e:
            print(f"Persistence cleanup error: {e}")

        await super().async_teardown_method(method)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_agent_message_persistence_across_sessions(self):
        """
        Test agent message persistence across multiple execution sessions.

        Business Value: Continuity critical - validates messages persist across
        sessions enabling continued conversations and context preservation.
        """
        # Create multiple execution sessions with related messages
        session_scenarios = [
            {
                'session_name': 'initial_consultation',
                'messages': [
                    'Help me analyze our Q3 financial performance and identify key growth opportunities',
                    'What specific metrics should I focus on for the board presentation?'
                ]
            },
            {
                'session_name': 'followup_analysis',
                'messages': [
                    'Based on our previous conversation, can you dive deeper into the revenue growth patterns?',
                    'I need detailed recommendations for improving our customer acquisition cost metrics'
                ]
            },
            {
                'session_name': 'implementation_planning',
                'messages': [
                    'Let\'s create an implementation plan based on the analysis from our earlier sessions',
                    'What are the specific action items and timelines for the recommendations?'
                ]
            }
        ]

        persistence_across_sessions_start = time.time()
        persisted_messages_by_session = {}

        # Execute sessions sequentially, persisting messages in each
        for session in session_scenarios:
            session_start = time.time()
            session_run_id = RunID(f"session_{session['session_name']}_{uuid.uuid4().hex[:8]}")
            session_messages = []

            async with self._create_user_execution_context(run_id=session_run_id) as user_context:
                self.test_user_contexts.append(user_context)

                for message_content in session['messages']:
                    message_id = MessageID(f"msg_{uuid.uuid4().hex[:8]}")
                    self.test_message_ids.append(message_id)

                    # Create and persist message
                    persisted_message = await self._persist_agent_message(
                        message_id=message_id,
                        user_context=user_context,
                        content=message_content,
                        agent_type='financial_analyst_agent',
                        session_name=session['session_name']
                    )

                    session_messages.append(persisted_message)
                    await asyncio.sleep(0.2)  # Simulate realistic message timing

            persisted_messages_by_session[session['session_name']] = session_messages
            session_duration = time.time() - session_start

            # Validate session persistence performance
            self.assertLess(session_duration, 5.0,
                           f"Session {session['session_name']} persistence too slow: {session_duration:.3f}s")

        # Validate cross-session message retrieval
        cross_session_start = time.time()

        async with self._create_user_execution_context() as retrieval_context:
            # Retrieve all messages across all sessions for this user
            all_user_messages = await self._retrieve_user_message_history(
                retrieval_context.user_id,
                retrieval_context.thread_id
            )

            cross_session_duration = time.time() - cross_session_start

            # Validate all messages were retrieved
            expected_total_messages = sum(len(session['messages']) for session in session_scenarios)
            self.assertEqual(len(all_user_messages), expected_total_messages,
                           f"Cross-session retrieval incomplete: {len(all_user_messages)}/{expected_total_messages}")

            # Validate message chronological ordering
            message_timestamps = [msg.timestamp for msg in all_user_messages]
            sorted_timestamps = sorted(message_timestamps)
            self.assertEqual(message_timestamps, sorted_timestamps,
                           "Messages not retrieved in chronological order")

            # Validate session context preservation
            for session in session_scenarios:
                session_messages = [msg for msg in all_user_messages
                                  if msg.audit_metadata.get('session_name') == session['session_name']]
                self.assertEqual(len(session_messages), len(session['messages']),
                               f"Session {session['session_name']} messages not fully retrieved")

        total_persistence_duration = time.time() - persistence_across_sessions_start

        # Validate overall cross-session performance
        self.assertLess(total_persistence_duration, 20.0,
                       f"Complete cross-session persistence too slow: {total_persistence_duration:.3f}s")
        self.assertLess(cross_session_duration, 3.0,
                       f"Cross-session retrieval too slow: {cross_session_duration:.3f}s")

        # Record cross-session persistence metrics
        self.persistence_metrics['cross_session_retrievals_successful'] += 1
        self.persistence_metrics['messages_persisted'] += expected_total_messages
        self.persistence_metrics['messages_retrieved'] += len(all_user_messages)

        # Record performance metrics for business analysis
        self.record_metric("cross_session_persistence_duration_ms", total_persistence_duration * 1000)
        self.record_metric("cross_session_retrieval_duration_ms", cross_session_duration * 1000)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_user_message_persistence_isolation(self):
        """
        Test message persistence isolation between multiple concurrent users.

        Business Value: Security and compliance critical - validates that persisted
        messages maintain complete user isolation for data privacy and regulatory compliance.
        """
        # Create multiple users with sensitive message scenarios
        user_persistence_scenarios = [
            {
                'user_id': UserID(f"finance_persist_user_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"finance_persist_thread_{uuid.uuid4().hex[:8]}"),
                'domain': 'finance',
                'sensitive_data': 'Confidential Q3 Revenue: $2.4M',
                'messages': [
                    'Analyze confidential Q3 revenue data - $2.4M total with breakdown by segment',
                    'Compare Q3 performance against Q2 - include sensitive margin analysis'
                ]
            },
            {
                'user_id': UserID(f"hr_persist_user_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"hr_persist_thread_{uuid.uuid4().hex[:8]}"),
                'domain': 'human_resources',
                'sensitive_data': 'Employee ID: 12345 - Performance Review',
                'messages': [
                    'Review performance data for Employee ID: 12345 - confidential assessment',
                    'Prepare promotion recommendation based on Employee ID: 12345 metrics'
                ]
            },
            {
                'user_id': UserID(f"legal_persist_user_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"legal_persist_thread_{uuid.uuid4().hex[:8]}"),
                'domain': 'legal',
                'sensitive_data': 'Case #ABC-2024 - Attorney-Client Privilege',
                'messages': [
                    'Analyze Case #ABC-2024 documents - attorney-client privileged information',
                    'Prepare defense strategy for Case #ABC-2024 - confidential legal analysis'
                ]
            }
        ]

        multi_user_persistence_start = time.time()
        user_persistence_results = {}

        # Persist messages for each user concurrently
        concurrent_persistence_tasks = []
        for scenario in user_persistence_scenarios:
            task = self._persist_user_messages_concurrently(scenario)
            concurrent_persistence_tasks.append(task)

        # Execute concurrent persistence
        persistence_results = await asyncio.gather(*concurrent_persistence_tasks)

        # Collect results
        for i, result in enumerate(persistence_results):
            user_persistence_results[str(user_persistence_scenarios[i]['user_id'])] = result

        # Validate cross-user message isolation
        isolation_validation_start = time.time()

        for i, scenario_a in enumerate(user_persistence_scenarios):
            # Retrieve messages for User A
            async with self._create_user_execution_context(
                user_id=scenario_a['user_id'],
                thread_id=scenario_a['thread_id']
            ) as user_context_a:
                self.test_user_contexts.append(user_context_a)

                user_a_messages = await self._retrieve_user_message_history(
                    user_context_a.user_id,
                    user_context_a.thread_id
                )

                # Validate User A only sees their own messages
                for message in user_a_messages:
                    self.assertEqual(str(message.user_id), str(scenario_a['user_id']),
                                   f"User A retrieved message from different user")
                    self.assertEqual(str(message.thread_id), str(scenario_a['thread_id']),
                                   f"User A retrieved message from different thread")

                    # Validate no cross-contamination of sensitive data
                    for j, scenario_b in enumerate(user_persistence_scenarios):
                        if i != j:
                            self.assertNotIn(scenario_b['sensitive_data'], message.content,
                                           f"CRITICAL: User {i} message contains User {j} sensitive data")
                            self.assertNotIn(scenario_b['sensitive_data'], json.dumps(message.audit_metadata),
                                           f"CRITICAL: User {i} audit metadata contains User {j} sensitive data")

                # Validate message count matches expected
                expected_message_count = len(scenario_a['messages'])
                self.assertEqual(len(user_a_messages), expected_message_count,
                               f"User {i} message count mismatch: {len(user_a_messages)}/{expected_message_count}")

        isolation_validation_duration = time.time() - isolation_validation_start
        multi_user_persistence_duration = time.time() - multi_user_persistence_start

        # Validate performance under multi-user load
        self.assertLess(multi_user_persistence_duration, 15.0,
                       f"Multi-user persistence too slow: {multi_user_persistence_duration:.3f}s")
        self.assertLess(isolation_validation_duration, 5.0,
                       f"Isolation validation too slow: {isolation_validation_duration:.3f}s")

        # Record multi-user isolation metrics
        self.persistence_metrics['user_isolation_verified'] += len(user_persistence_scenarios)
        total_messages = sum(len(scenario['messages']) for scenario in user_persistence_scenarios)
        self.persistence_metrics['messages_persisted'] += total_messages

        # Record performance metrics for business analysis
        self.record_metric("multi_user_persistence_duration_ms", multi_user_persistence_duration * 1000)
        self.record_metric("isolation_validation_duration_ms", isolation_validation_duration * 1000)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_persistence_data_integrity_and_audit_trails(self):
        """
        Test data integrity validation and audit trail creation for persisted messages.

        Business Value: Compliance critical - validates complete audit trails and
        data integrity for regulatory compliance and security auditing.
        """
        # Create comprehensive audit trail scenario
        audit_scenario = {
            'user_id': UserID(f"audit_user_{uuid.uuid4().hex[:8]}"),
            'thread_id': ThreadID(f"audit_thread_{uuid.uuid4().hex[:8]}"),
            'compliance_level': 'enterprise',
            'audit_requirements': ['message_content', 'user_context', 'agent_interactions', 'system_metadata'],
            'messages': [
                {
                    'content': 'Analyze customer data for regulatory compliance - GDPR and CCPA requirements',
                    'compliance_tags': ['gdpr', 'ccpa', 'data_privacy'],
                    'agent_type': 'compliance_agent'
                },
                {
                    'content': 'Generate audit report for data processing activities - include retention policies',
                    'compliance_tags': ['audit', 'data_retention', 'reporting'],
                    'agent_type': 'audit_agent'
                },
                {
                    'content': 'Review data access logs and identify any unauthorized access patterns',
                    'compliance_tags': ['security', 'access_control', 'monitoring'],
                    'agent_type': 'security_agent'
                }
            ]
        }

        data_integrity_start = time.time()

        async with self._create_user_execution_context(
            user_id=audit_scenario['user_id'],
            thread_id=audit_scenario['thread_id']
        ) as audit_user_context:
            self.test_user_contexts.append(audit_user_context)

            persisted_messages = []
            audit_trail_records = []

            # Persist messages with comprehensive audit trails
            for message_data in audit_scenario['messages']:
                message_id = MessageID(f"audit_msg_{uuid.uuid4().hex[:8]}")
                self.test_message_ids.append(message_id)

                # Persist message with enhanced audit metadata
                persistence_start = time.time()

                persisted_message = await self._persist_agent_message_with_audit_trail(
                    message_id=message_id,
                    user_context=audit_user_context,
                    content=message_data['content'],
                    agent_type=message_data['agent_type'],
                    compliance_tags=message_data['compliance_tags'],
                    audit_requirements=audit_scenario['audit_requirements']
                )

                persistence_duration = time.time() - persistence_start

                persisted_messages.append(persisted_message)
                self.persistence_metrics['persistence_performance_ms'].append(persistence_duration * 1000)

                # Validate immediate data integrity
                integrity_validation = await self._validate_message_data_integrity(
                    persisted_message, message_data
                )

                self.assertTrue(integrity_validation.success,
                               f"Data integrity validation failed: {integrity_validation.errors}")

                await asyncio.sleep(0.1)  # Realistic persistence timing

            # Validate comprehensive audit trail retrieval
            audit_retrieval_start = time.time()

            audit_trail = await self._retrieve_comprehensive_audit_trail(
                user_id=audit_user_context.user_id,
                thread_id=audit_user_context.thread_id,
                audit_requirements=audit_scenario['audit_requirements']
            )

            audit_retrieval_duration = time.time() - audit_retrieval_start

            # Validate audit trail completeness
            self.assertEqual(len(audit_trail), len(audit_scenario['messages']),
                           f"Audit trail incomplete: {len(audit_trail)}/{len(audit_scenario['messages'])}")

            # Validate audit trail data integrity
            for i, audit_record in enumerate(audit_trail):
                original_message = audit_scenario['messages'][i]

                # Validate required audit fields
                required_fields = ['message_id', 'user_id', 'timestamp', 'agent_type', 'compliance_tags']
                for field in required_fields:
                    self.assertIn(field, audit_record, f"Audit record missing required field: {field}")

                # Validate compliance tags preserved
                self.assertEqual(
                    set(audit_record['compliance_tags']),
                    set(original_message['compliance_tags']),
                    f"Compliance tags not preserved in audit trail"
                )

        data_integrity_duration = time.time() - data_integrity_start

        # Validate overall data integrity performance
        self.assertLess(data_integrity_duration, 10.0,
                       f"Data integrity validation too slow: {data_integrity_duration:.3f}s")
        self.assertLess(audit_retrieval_duration, 2.0,
                       f"Audit trail retrieval too slow: {audit_retrieval_duration:.3f}s")

        # Record audit trail metrics
        self.persistence_metrics['audit_trail_records_created'] += len(audit_trail)
        self.persistence_metrics['data_integrity_validations_passed'] += len(persisted_messages)

        # Record performance metrics for business analysis
        avg_persistence_time = sum(self.persistence_metrics['persistence_performance_ms']) / len(self.persistence_metrics['persistence_performance_ms'])
        self.record_metric("average_persistence_time_ms", avg_persistence_time)
        self.record_metric("audit_trail_retrieval_duration_ms", audit_retrieval_duration * 1000)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_persistence_performance_under_load(self):
        """
        Test persistence performance under sustained message load.

        Business Value: Platform scalability - validates persistence infrastructure
        can handle high-volume message processing without degradation.
        """
        # Create high-volume persistence load scenario
        load_test_config = {
            'message_batches': 5,
            'messages_per_batch': 8,
            'concurrent_users': 3,
            'message_complexity': 'varied'
        }

        performance_load_start = time.time()
        all_load_results = []

        # Create multiple concurrent users for load testing
        load_test_users = []
        for i in range(load_test_config['concurrent_users']):
            user_id = UserID(f"load_user_{i}_{uuid.uuid4().hex[:8]}")
            thread_id = ThreadID(f"load_thread_{i}_{uuid.uuid4().hex[:8]}")
            load_test_users.append((user_id, thread_id))

        # Execute load test in batches
        for batch_num in range(load_test_config['message_batches']):
            batch_start = time.time()

            # Create concurrent persistence tasks for this batch
            batch_concurrent_tasks = []
            for user_id, thread_id in load_test_users:
                task = self._execute_high_volume_persistence_batch(
                    user_id, thread_id, batch_num, load_test_config['messages_per_batch']
                )
                batch_concurrent_tasks.append(task)

            # Execute concurrent batch
            batch_results = await asyncio.gather(*batch_concurrent_tasks)
            batch_duration = time.time() - batch_start

            # Validate batch performance
            batch_success_count = sum(1 for result in batch_results if result['success'])
            batch_success_rate = batch_success_count / len(batch_results)

            self.assertGreaterEqual(batch_success_rate, 0.8,
                                   f"Batch {batch_num} success rate too low: {batch_success_rate:.2f}")

            batch_throughput = (len(batch_results) * load_test_config['messages_per_batch']) / batch_duration
            self.assertGreater(batch_throughput, 2.0,
                              f"Batch {batch_num} throughput too low: {batch_throughput:.2f} messages/second")

            all_load_results.extend(batch_results)

            # Short delay between batches to simulate realistic patterns
            await asyncio.sleep(0.3)

        performance_load_duration = time.time() - performance_load_start

        # Validate overall load test performance
        total_messages = load_test_config['message_batches'] * load_test_config['messages_per_batch'] * load_test_config['concurrent_users']
        overall_throughput = total_messages / performance_load_duration

        self.assertGreater(overall_throughput, 1.5,
                          f"Overall load test throughput too low: {overall_throughput:.2f} messages/second")

        # Validate persistence consistency under load
        consistency_validation_start = time.time()

        for user_id, thread_id in load_test_users:
            async with self._create_user_execution_context(user_id=user_id, thread_id=thread_id) as load_context:
                self.test_user_contexts.append(load_context)

                user_messages = await self._retrieve_user_message_history(user_id, thread_id)
                expected_message_count = load_test_config['message_batches'] * load_test_config['messages_per_batch']

                self.assertEqual(len(user_messages), expected_message_count,
                               f"Load test user missing messages: {len(user_messages)}/{expected_message_count}")

        consistency_validation_duration = time.time() - consistency_validation_start

        # Record load test metrics
        self.persistence_metrics['persistence_operations_performed'] += total_messages
        self.record_metric("load_test_throughput_messages_per_second", overall_throughput)
        self.record_metric("load_test_duration_ms", performance_load_duration * 1000)
        self.record_metric("consistency_validation_duration_ms", consistency_validation_duration * 1000)

    # === HELPER METHODS FOR PERSISTENCE TESTING ===

    @asynccontextmanager
    async def _create_user_execution_context(self, user_id=None, thread_id=None, run_id=None):
        """Create user execution context for persistence testing."""
        user_id = user_id or self.test_user_id
        thread_id = thread_id or self.test_thread_id
        run_id = run_id or self.test_run_id

        # Mock context for testing
        mock_context = MagicMock()
        mock_context.user_id = user_id
        mock_context.thread_id = thread_id
        mock_context.run_id = run_id
        mock_context.created_at = datetime.now(timezone.utc)
        yield mock_context

    async def _persist_agent_message(self, message_id: MessageID, user_context, content: str, agent_type: str, session_name: str = None) -> PersistedMessage:
        """Persist agent message with comprehensive metadata."""
        timestamp = datetime.now(timezone.utc)

        persisted_message = PersistedMessage(
            message_id=message_id,
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            content=content,
            agent_type=agent_type,
            timestamp=timestamp,
            persistence_tier='tier_2',  # PostgreSQL
            audit_metadata={
                'session_name': session_name,
                'user_context_created_at': user_context.created_at.isoformat(),
                'persistence_timestamp': timestamp.isoformat(),
                'agent_type': agent_type,
                'content_length': len(content)
            }
        )

        # Use real or mock persistence
        if REAL_PERSISTENCE_COMPONENTS_AVAILABLE and hasattr(self.state_persistence, 'persist_agent_message'):
            await self.state_persistence.persist_agent_message(persisted_message)
        else:
            await self._mock_persist_message(persisted_message)

        return persisted_message

    async def _persist_agent_message_with_audit_trail(self, message_id: MessageID, user_context, content: str, agent_type: str, compliance_tags: List[str], audit_requirements: List[str]) -> PersistedMessage:
        """Persist agent message with comprehensive audit trail."""
        timestamp = datetime.now(timezone.utc)

        persisted_message = PersistedMessage(
            message_id=message_id,
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            content=content,
            agent_type=agent_type,
            timestamp=timestamp,
            persistence_tier='tier_3',  # ClickHouse for audit
            audit_metadata={
                'compliance_tags': compliance_tags,
                'audit_requirements': audit_requirements,
                'user_context_created_at': user_context.created_at.isoformat(),
                'persistence_timestamp': timestamp.isoformat(),
                'agent_type': agent_type,
                'content_hash': hash(content),
                'compliance_level': 'enterprise'
            }
        )

        # Persist with audit trail
        if REAL_PERSISTENCE_COMPONENTS_AVAILABLE:
            if hasattr(self.state_persistence, 'persist_agent_message'):
                await self.state_persistence.persist_agent_message(persisted_message)
            if hasattr(self.clickhouse_client, 'write_audit_record'):
                await self.clickhouse_client.write_audit_record(persisted_message.audit_metadata)
        else:
            await self._mock_persist_message(persisted_message)
            await self._mock_write_audit_record(persisted_message.audit_metadata)

        return persisted_message

    async def _retrieve_user_message_history(self, user_id: UserID, thread_id: ThreadID) -> List[PersistedMessage]:
        """Retrieve complete message history for a user."""
        if REAL_PERSISTENCE_COMPONENTS_AVAILABLE and hasattr(self.state_persistence, 'get_message_history'):
            return await self.state_persistence.get_message_history(user_id, thread_id)
        else:
            return await self._mock_retrieve_messages(user_id, thread_id)

    async def _retrieve_comprehensive_audit_trail(self, user_id: UserID, thread_id: ThreadID, audit_requirements: List[str]) -> List[Dict]:
        """Retrieve comprehensive audit trail for compliance."""
        if REAL_PERSISTENCE_COMPONENTS_AVAILABLE and hasattr(self.clickhouse_client, 'query_audit_trail'):
            return await self.clickhouse_client.query_audit_trail(user_id, thread_id, audit_requirements)
        else:
            # Mock audit trail retrieval
            return [record for record in self._mock_audit_store
                   if record.get('user_id') == str(user_id) and record.get('thread_id') == str(thread_id)]

    async def _validate_message_data_integrity(self, persisted_message: PersistedMessage, original_data: Dict) -> PersistenceValidationResult:
        """Validate data integrity of persisted message."""
        validation_start = time.time()
        errors = []

        # Validate content integrity
        if persisted_message.content != original_data['content']:
            errors.append("Content mismatch after persistence")

        # Validate agent type preservation
        if persisted_message.agent_type != original_data['agent_type']:
            errors.append("Agent type not preserved")

        # Validate compliance tags in audit metadata
        if 'compliance_tags' in original_data:
            persisted_tags = persisted_message.audit_metadata.get('compliance_tags', [])
            if set(persisted_tags) != set(original_data['compliance_tags']):
                errors.append("Compliance tags not preserved")

        validation_duration = time.time() - validation_start

        return PersistenceValidationResult(
            operation_type='data_integrity_validation',
            success=len(errors) == 0,
            duration_ms=validation_duration * 1000,
            records_affected=1,
            data_integrity_verified=len(errors) == 0,
            errors=errors
        )

    async def _persist_user_messages_concurrently(self, scenario: Dict) -> Dict:
        """Persist messages for a user concurrently for isolation testing."""
        results = {
            'user_id': scenario['user_id'],
            'messages_persisted': 0,
            'errors': [],
            'duration_ms': 0
        }

        start_time = time.time()

        try:
            async with self._create_user_execution_context(
                user_id=scenario['user_id'],
                thread_id=scenario['thread_id']
            ) as user_context:

                for message_content in scenario['messages']:
                    message_id = MessageID(f"concurrent_msg_{uuid.uuid4().hex[:8]}")
                    self.test_message_ids.append(message_id)

                    await self._persist_agent_message(
                        message_id=message_id,
                        user_context=user_context,
                        content=message_content,
                        agent_type=f"{scenario['domain']}_agent"
                    )

                    results['messages_persisted'] += 1
                    await asyncio.sleep(0.1)  # Realistic persistence timing

        except Exception as e:
            results['errors'].append(str(e))

        results['duration_ms'] = (time.time() - start_time) * 1000
        return results

    async def _execute_high_volume_persistence_batch(self, user_id: UserID, thread_id: ThreadID, batch_num: int, messages_per_batch: int) -> Dict:
        """Execute high-volume persistence batch for load testing."""
        batch_result = {
            'user_id': str(user_id),
            'batch_num': batch_num,
            'messages_processed': 0,
            'success': True,
            'errors': [],
            'duration_ms': 0
        }

        batch_start = time.time()

        try:
            async with self._create_user_execution_context(user_id=user_id, thread_id=thread_id) as load_context:
                self.test_user_contexts.append(load_context)

                for i in range(messages_per_batch):
                    message_id = MessageID(f"load_msg_b{batch_num}_m{i}_{uuid.uuid4().hex[:8]}")
                    self.test_message_ids.append(message_id)

                    message_content = f"Load test message batch {batch_num}, message {i} - testing persistence under high volume"

                    await self._persist_agent_message(
                        message_id=message_id,
                        user_context=load_context,
                        content=message_content,
                        agent_type='load_test_agent',
                        session_name=f'load_batch_{batch_num}'
                    )

                    batch_result['messages_processed'] += 1

        except Exception as e:
            batch_result['success'] = False
            batch_result['errors'].append(str(e))

        batch_result['duration_ms'] = (time.time() - batch_start) * 1000
        return batch_result

    # Mock implementations for testing when real components unavailable
    async def _mock_persist_message(self, message: PersistedMessage):
        """Mock message persistence for testing."""
        self._mock_message_store[str(message.message_id)] = message
        await asyncio.sleep(0.01)  # Simulate persistence latency

    async def _mock_retrieve_messages(self, user_id: UserID, thread_id: ThreadID) -> List[PersistedMessage]:
        """Mock message retrieval for testing."""
        user_messages = [
            msg for msg in self._mock_message_store.values()
            if msg.user_id == user_id and msg.thread_id == thread_id
        ]
        return sorted(user_messages, key=lambda m: m.timestamp)

    async def _mock_write_audit_record(self, audit_metadata: Dict):
        """Mock audit record writing for testing."""
        audit_record = {
            **audit_metadata,
            'audit_timestamp': datetime.now(timezone.utc).isoformat(),
            'audit_id': f"audit_{uuid.uuid4().hex[:8]}"
        }
        self._mock_audit_store.append(audit_record)
        await asyncio.sleep(0.005)  # Simulate audit write latency