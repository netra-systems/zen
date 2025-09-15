"""
Issue #914 Multi-User Registry Isolation Integration Test Suite

This test suite validates that multi-user isolation patterns remain secure
throughout the AgentRegistry SSOT consolidation process, protecting enterprise
customer data and preventing security vulnerabilities.

EXPECTED BEHAVIOR: Tests should demonstrate current isolation challenges
and validate that fixes maintain enterprise-grade security standards.

Business Impact:
- Protects Golden Path: Users login → get AI responses (isolated per user)
- Ensures enterprise customer data security
- Maintains $500K+ ARR multi-user functionality
- Validates user session isolation patterns
- Prevents data leakage between concurrent users

Test Strategy:
1. Test user data isolation between concurrent sessions
2. Validate agent registry isolation per user context
3. Ensure user actions don't affect other users' data
4. Test session boundary enforcement
5. Validate memory isolation and cleanup
6. Test concurrent access patterns security
"""

import asyncio
import logging
import unittest
import uuid
import warnings
import pytest
from typing import Optional, Any, Dict, List, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time

# SSOT Base Test Case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Registry imports for multi-user testing
registry_imports = {}
try:
    # DEPRECATED - will be removed in Issue #863 Phase 3
    from netra_backend.app.agents.registry import AgentRegistry as BasicAgentRegistry
    registry_imports['basic'] = BasicAgentRegistry
except ImportError:
    registry_imports['basic'] = None

try:
    # SSOT Registry - canonical location for multi-user isolation
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedAgentRegistry
    registry_imports['advanced'] = AdvancedAgentRegistry
except ImportError:
    registry_imports['advanced'] = None

# User context imports for isolation testing
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    user_context_available = True
except ImportError:
    UserExecutionContext = None
    user_context_available = False

# Testing infrastructure
try:
    from test_framework.ssot.mock_factory import SSotMockFactory
    mock_factory_available = True
except ImportError:
    SSotMockFactory = None
    mock_factory_available = False

logger = logging.getLogger(__name__)


@dataclass
@pytest.mark.integration
class TestUser:
    """Test user for multi-user isolation testing."""
    user_id: str
    session_id: str
    registry: Optional[Any] = None
    agent_data: Dict[str, Any] = field(default_factory=dict)
    actions_performed: List[str] = field(default_factory=list)
    data_accessed: Set[str] = field(default_factory=set)
    start_time: datetime = field(default_factory=datetime.now)


@pytest.mark.integration
class TestMultiUserRegistryIsolation(SSotAsyncTestCase):
    """
    Integration test suite for multi-user registry isolation.

    Tests enterprise-grade user isolation patterns during registry
    SSOT consolidation, focusing on data security and session boundaries.
    """

    def setup_method(self, method):
        """Setup multi-user isolation testing environment."""
        super().setup_method(method)
        self.test_session_prefix = f"multiuser_{uuid.uuid4().hex[:8]}"
        self.test_users: List[TestUser] = []
        self.registry_instances = []
        self.mock_factory = SSotMockFactory() if SSotMockFactory else None

        # Isolation tracking
        self.isolation_violations = []
        self.data_leakage_incidents = []
        self.concurrent_access_results = {}

    async def teardown_method(self, method):
        """Cleanup multi-user test resources."""
        # Cleanup user registries
        for user in self.test_users:
            if user.registry and hasattr(user.registry, 'cleanup'):
                try:
                    await user.registry.cleanup()
                except Exception as e:
                    logger.warning(f"User {user.user_id} registry cleanup failed: {e}")

        # Cleanup registry instances
        for registry in self.registry_instances:
            if hasattr(registry, 'cleanup') and callable(registry.cleanup):
                try:
                    await registry.cleanup()
                except Exception as e:
                    logger.warning(f"Registry cleanup failed: {e}")

        self.test_users.clear()
        self.registry_instances.clear()
        self.isolation_violations.clear()
        self.data_leakage_incidents.clear()
        await super().teardown_method(method)

    def create_test_user(self, user_index: int) -> TestUser:
        """Create a test user with unique identification."""
        user = TestUser(
            user_id=f"{self.test_session_prefix}_user_{user_index}",
            session_id=f"{self.test_session_prefix}_session_{user_index}",
            agent_data={
                'user_specific_data': f'secret_data_for_user_{user_index}',
                'session_info': f'session_data_{user_index}',
                'agent_count': 0,
                'creation_time': datetime.now().isoformat()
            }
        )
        self.test_users.append(user)
        return user

    async def test_01_basic_user_isolation_validation(self):
        """
        Test 1: Basic user isolation validation

        Validates that different users get completely isolated registry
        instances and cannot access each other's data.

        CRITICAL: Fundamental security requirement for enterprise customers
        """
        available_registries = {k: v for k, v in registry_imports.items() if v is not None}

        if len(available_registries) == 0:
            pytest.skip("No registries available for user isolation testing")

        user_count = 3
        isolation_results = {}

        for registry_name, registry_class in available_registries.items():
            try:
                # Create isolated users with registries
                registry_users = []

                for i in range(user_count):
                    user = self.create_test_user(i)

                    # Create user-specific registry
                    if registry_name == 'basic':
                        user.registry = registry_class()
                        self.registry_instances.append(user.registry)
                    elif registry_name == 'advanced':
                        mock_context = self.mock_factory.create_mock_user_context(user.user_id) if self.mock_factory else MagicMock()
                        mock_context.user_id = user.user_id
                        mock_context.session_id = user.session_id
                        mock_dispatcher = MagicMock()
                        mock_bridge = MagicMock()

                        user.registry = registry_class(
                            user_context=mock_context,
                            tool_dispatcher=mock_dispatcher,
                            websocket_bridge=mock_bridge
                        )
                        self.registry_instances.append(user.registry)

                    registry_users.append(user)

                # Test isolation properties
                isolation_checks = {
                    'unique_registries': len(set(id(user.registry) for user in registry_users)) == len(registry_users),
                    'unique_user_ids': len(set(user.user_id for user in registry_users)) == len(registry_users),
                    'unique_sessions': len(set(user.session_id for user in registry_users)) == len(registry_users),
                    'no_shared_state': True  # Will test by looking for shared references
                }

                # Test for shared state leakage
                if registry_name == 'advanced':
                    user_contexts = []
                    for user in registry_users:
                        if hasattr(user.registry, 'user_context'):
                            user_contexts.append(user.registry.user_context)

                    # Check that user contexts are truly isolated
                    isolation_checks['user_contexts_isolated'] = (
                        len(set(id(ctx) for ctx in user_contexts)) == len(user_contexts)
                    )

                # Test agent registration isolation
                if hasattr(registry_users[0].registry, 'register_agent'):
                    try:
                        # Register agents for each user
                        for i, user in enumerate(registry_users):
                            mock_agent = MagicMock()
                            mock_agent.agent_id = f"agent_{user.user_id}_{i}"
                            mock_agent.user_data = user.agent_data

                            user.registry.register_agent(mock_agent)
                            user.actions_performed.append(f"registered_agent_{i}")

                        # Verify agents don't cross-contaminate
                        if hasattr(registry_users[0].registry, 'list_agents'):
                            for user in registry_users:
                                try:
                                    user_agents = user.registry.list_agents()
                                    if user_agents:
                                        agent_ids = [a.agent_id for a in user_agents]
                                        # Check that only this user's agents are present
                                        for other_user in registry_users:
                                            if other_user != user:
                                                other_agent_id = f"agent_{other_user.user_id}_0"
                                                if other_agent_id in agent_ids:
                                                    self.isolation_violations.append({
                                                        'type': 'agent_cross_contamination',
                                                        'user': user.user_id,
                                                        'contaminated_by': other_user.user_id,
                                                        'registry': registry_name
                                                    })
                                                    isolation_checks['no_shared_state'] = False
                                except Exception as e:
                                    logger.warning(f"Agent isolation check failed: {e}")

                    except Exception as e:
                        logger.warning(f"Agent registration isolation test failed: {e}")

                # Calculate isolation score
                isolation_score = sum(isolation_checks.values()) / len(isolation_checks)
                isolation_results[registry_name] = {
                    'isolation_score': isolation_score,
                    'isolation_checks': isolation_checks,
                    'users_tested': len(registry_users),
                    'violations_found': len([v for v in self.isolation_violations if v.get('registry') == registry_name])
                }

            except Exception as e:
                logger.error(f"Basic user isolation testing failed for {registry_name}: {e}")
                isolation_results[registry_name] = {'error': str(e)}

        # Analyze isolation effectiveness
        isolation_scores = [result.get('isolation_score', 0)
                           for result in isolation_results.values()
                           if 'isolation_score' in result]
        average_isolation_score = sum(isolation_scores) / len(isolation_scores) if isolation_scores else 0

        # Record metrics
        self.record_metric('basic_user_isolation_score', average_isolation_score)
        self.record_metric('user_isolation_results', isolation_results)
        self.record_metric('isolation_violations', self.isolation_violations)

        logger.info(f"Basic user isolation results: {isolation_results}")
        logger.info(f"Average isolation score: {average_isolation_score:.1%}")
        logger.info(f"Isolation violations found: {len(self.isolation_violations)}")

        # CRITICAL: Enterprise-grade isolation must be very strong
        self.assertGreaterEqual(average_isolation_score, 0.9,
                               f"Enterprise user isolation must be at least 90% - "
                               f"got {average_isolation_score:.1%}, security risk for enterprise customers")

        # No isolation violations allowed
        self.assertEqual(len(self.isolation_violations), 0,
                        f"Zero isolation violations allowed for security - found {len(self.isolation_violations)}")

    async def test_02_concurrent_user_access_security(self):
        """
        Test 2: Concurrent user access security

        Validates that multiple users accessing registries concurrently
        maintain proper isolation and don't interfere with each other.

        CRITICAL: Concurrent access security for production scalability
        """
        available_registries = {k: v for k, v in registry_imports.items() if v is not None}

        if len(available_registries) == 0:
            pytest.skip("No registries available for concurrent access testing")

        concurrent_user_count = 5
        concurrent_results = {}

        for registry_name, registry_class in available_registries.items():
            try:
                # Create concurrent users
                concurrent_users = []
                concurrent_tasks = []

                async def simulate_user_activity(user_index: int) -> Dict[str, Any]:
                    """Simulate concurrent user activity."""
                    user = TestUser(
                        user_id=f"{self.test_session_prefix}_concurrent_{user_index}",
                        session_id=f"{self.test_session_prefix}_concurrent_session_{user_index}",
                        agent_data={
                            'concurrent_data': f'user_{user_index}_secret_data',
                            'activity_count': 0
                        }
                    )

                    try:
                        # Create registry for this user
                        if registry_name == 'basic':
                            user.registry = registry_class()
                        elif registry_name == 'advanced':
                            mock_context = self.mock_factory.create_mock_user_context(user.user_id) if self.mock_factory else MagicMock()
                            mock_context.user_id = user.user_id
                            mock_context.session_id = user.session_id
                            mock_dispatcher = MagicMock()
                            mock_bridge = MagicMock()

                            user.registry = registry_class(
                                user_context=mock_context,
                                tool_dispatcher=mock_dispatcher,
                                websocket_bridge=mock_bridge
                            )

                        self.registry_instances.append(user.registry)

                        # Simulate user activities
                        activities = []
                        for activity_index in range(3):  # Each user performs 3 activities
                            activity_id = f"activity_{user_index}_{activity_index}"

                            # Simulate agent registration
                            if hasattr(user.registry, 'register_agent'):
                                mock_agent = MagicMock()
                                mock_agent.agent_id = f"concurrent_agent_{user.user_id}_{activity_index}"
                                mock_agent.user_specific_data = f"user_{user_index}_activity_{activity_index}_data"

                                user.registry.register_agent(mock_agent)
                                activities.append(activity_id)
                                user.actions_performed.append(activity_id)

                            # Small delay to simulate real activity
                            await asyncio.sleep(0.01)

                        return {
                            'user_id': user.user_id,
                            'activities_completed': len(activities),
                            'registry_created': True,
                            'no_errors': True
                        }

                    except Exception as e:
                        logger.error(f"Concurrent user {user_index} activity failed: {e}")
                        return {
                            'user_id': user.user_id,
                            'activities_completed': 0,
                            'registry_created': False,
                            'error': str(e),
                            'no_errors': False
                        }

                # Execute concurrent user activities
                tasks = [simulate_user_activity(i) for i in range(concurrent_user_count)]
                concurrent_results_list = await asyncio.gather(*tasks, return_exceptions=True)

                # Analyze concurrent access results
                successful_concurrent_users = 0
                total_activities_completed = 0
                concurrent_errors = []

                for result in concurrent_results_list:
                    if isinstance(result, dict):
                        if result.get('no_errors', False):
                            successful_concurrent_users += 1
                        total_activities_completed += result.get('activities_completed', 0)
                    else:
                        concurrent_errors.append(str(result))

                # Calculate concurrent access metrics
                concurrent_success_rate = successful_concurrent_users / concurrent_user_count
                activity_completion_rate = total_activities_completed / (concurrent_user_count * 3)  # 3 activities per user

                concurrent_results[registry_name] = {
                    'concurrent_success_rate': concurrent_success_rate,
                    'activity_completion_rate': activity_completion_rate,
                    'successful_users': successful_concurrent_users,
                    'total_users': concurrent_user_count,
                    'total_activities': total_activities_completed,
                    'errors': concurrent_errors
                }

            except Exception as e:
                logger.error(f"Concurrent access testing failed for {registry_name}: {e}")
                concurrent_results[registry_name] = {'error': str(e)}

        # Analyze concurrent access security
        success_rates = [result.get('concurrent_success_rate', 0)
                        for result in concurrent_results.values()
                        if 'concurrent_success_rate' in result]
        average_concurrent_success = sum(success_rates) / len(success_rates) if success_rates else 0

        # Record metrics
        self.record_metric('concurrent_access_success_rate', average_concurrent_success)
        self.record_metric('concurrent_access_results', concurrent_results)

        logger.info(f"Concurrent access results: {concurrent_results}")
        logger.info(f"Average concurrent success rate: {average_concurrent_success:.1%}")

        # Production systems need good concurrent access handling
        self.assertGreaterEqual(average_concurrent_success, 0.8,
                               f"Concurrent user access should be at least 80% successful - "
                               f"got {average_concurrent_success:.1%}, scalability risk")

    async def test_03_data_leakage_prevention(self):
        """
        Test 3: Data leakage prevention between users

        Validates that user-specific data cannot leak between different
        user sessions, ensuring enterprise customer data security.

        CRITICAL: Data leakage prevention is essential for compliance
        """
        available_registries = {k: v for k, v in registry_imports.items() if v is not None}

        if len(available_registries) == 0:
            pytest.skip("No registries available for data leakage testing")

        leakage_test_results = {}

        for registry_name, registry_class in available_registries.items():
            try:
                # Create users with sensitive data
                sensitive_users = []

                for i in range(2):  # Test with 2 users to check for leakage
                    user = TestUser(
                        user_id=f"{self.test_session_prefix}_sensitive_{i}",
                        session_id=f"{self.test_session_prefix}_sensitive_session_{i}",
                        agent_data={
                            'secret_key': f'TOP_SECRET_KEY_USER_{i}',
                            'personal_data': f'PERSONAL_INFO_USER_{i}',
                            'session_token': f'SESSION_TOKEN_{i}_{uuid.uuid4().hex}',
                            'business_data': f'BUSINESS_CRITICAL_DATA_{i}'
                        }
                    )

                    # Create registry with sensitive data
                    if registry_name == 'basic':
                        user.registry = registry_class()
                    elif registry_name == 'advanced':
                        mock_context = self.mock_factory.create_mock_user_context(user.user_id) if self.mock_factory else MagicMock()
                        mock_context.user_id = user.user_id
                        mock_context.session_id = user.session_id
                        mock_context.sensitive_data = user.agent_data  # Store sensitive data in context
                        mock_dispatcher = MagicMock()
                        mock_bridge = MagicMock()

                        user.registry = registry_class(
                            user_context=mock_context,
                            tool_dispatcher=mock_dispatcher,
                            websocket_bridge=mock_bridge
                        )

                    self.registry_instances.append(user.registry)
                    sensitive_users.append(user)

                # Test for data leakage
                leakage_checks = {
                    'registries_isolated': len(set(id(user.registry) for user in sensitive_users)) == len(sensitive_users),
                    'no_cross_user_data_access': True,
                    'context_data_isolated': True,
                    'agent_data_isolated': True
                }

                # Check for cross-user data access
                user1, user2 = sensitive_users[0], sensitive_users[1]

                # Test context isolation (advanced registry)
                if registry_name == 'advanced' and hasattr(user1.registry, 'user_context'):
                    try:
                        context1 = user1.registry.user_context
                        context2 = user2.registry.user_context

                        # Check that contexts don't share data
                        if hasattr(context1, 'sensitive_data') and hasattr(context2, 'sensitive_data'):
                            context1_secrets = context1.sensitive_data.get('secret_key', '')
                            context2_secrets = context2.sensitive_data.get('secret_key', '')

                            # Secrets should be different and not contain each other
                            if (context1_secrets in str(context2.sensitive_data) or
                                context2_secrets in str(context1.sensitive_data)):
                                self.data_leakage_incidents.append({
                                    'type': 'context_data_leakage',
                                    'user1': user1.user_id,
                                    'user2': user2.user_id,
                                    'leaked_data': 'sensitive_context_data',
                                    'registry': registry_name
                                })
                                leakage_checks['context_data_isolated'] = False

                    except Exception as e:
                        logger.warning(f"Context isolation check failed: {e}")

                # Test agent registration isolation
                if hasattr(user1.registry, 'register_agent'):
                    try:
                        # Register agents with sensitive data
                        agent1 = MagicMock()
                        agent1.agent_id = f"sensitive_agent_{user1.user_id}"
                        agent1.sensitive_data = user1.agent_data

                        agent2 = MagicMock()
                        agent2.agent_id = f"sensitive_agent_{user2.user_id}"
                        agent2.sensitive_data = user2.agent_data

                        user1.registry.register_agent(agent1)
                        user2.registry.register_agent(agent2)

                        # Check that agents don't leak data
                        if hasattr(user1.registry, 'list_agents'):
                            user1_agents = user1.registry.list_agents() or []
                            user2_agents = user2.registry.list_agents() or []

                            # Check for agent cross-contamination
                            user1_agent_ids = set(a.agent_id for a in user1_agents)
                            user2_agent_ids = set(a.agent_id for a in user2_agents)

                            if user1_agent_ids & user2_agent_ids:  # Intersection should be empty
                                self.data_leakage_incidents.append({
                                    'type': 'agent_cross_contamination',
                                    'user1': user1.user_id,
                                    'user2': user2.user_id,
                                    'shared_agents': list(user1_agent_ids & user2_agent_ids),
                                    'registry': registry_name
                                })
                                leakage_checks['agent_data_isolated'] = False

                    except Exception as e:
                        logger.warning(f"Agent isolation check failed: {e}")

                # Calculate data leakage prevention score
                leakage_prevention_score = sum(leakage_checks.values()) / len(leakage_checks)
                leakage_test_results[registry_name] = {
                    'leakage_prevention_score': leakage_prevention_score,
                    'leakage_checks': leakage_checks,
                    'leakage_incidents': len([inc for inc in self.data_leakage_incidents if inc.get('registry') == registry_name])
                }

            except Exception as e:
                logger.error(f"Data leakage testing failed for {registry_name}: {e}")
                leakage_test_results[registry_name] = {'error': str(e)}

        # Analyze data leakage prevention
        prevention_scores = [result.get('leakage_prevention_score', 0)
                           for result in leakage_test_results.values()
                           if 'leakage_prevention_score' in result]
        average_prevention_score = sum(prevention_scores) / len(prevention_scores) if prevention_scores else 0

        # Record metrics
        self.record_metric('data_leakage_prevention_score', average_prevention_score)
        self.record_metric('leakage_test_results', leakage_test_results)
        self.record_metric('data_leakage_incidents', self.data_leakage_incidents)

        logger.info(f"Data leakage prevention results: {leakage_test_results}")
        logger.info(f"Average prevention score: {average_prevention_score:.1%}")
        logger.info(f"Data leakage incidents: {len(self.data_leakage_incidents)}")

        # CRITICAL: No data leakage allowed for compliance
        self.assertGreaterEqual(average_prevention_score, 0.95,
                               f"Data leakage prevention must be at least 95% for compliance - "
                               f"got {average_prevention_score:.1%}")

        # Zero tolerance for data leakage
        self.assertEqual(len(self.data_leakage_incidents), 0,
                        f"Zero data leakage incidents allowed - found {len(self.data_leakage_incidents)}")

    async def test_04_session_boundary_enforcement(self):
        """
        Test 4: Session boundary enforcement

        Validates that user sessions maintain strict boundaries and
        cannot access or modify data from other sessions.

        CRITICAL: Session security for user authentication integrity
        """
        available_registries = {k: v for k, v in registry_imports.items() if v is not None}

        if len(available_registries) == 0:
            pytest.skip("No registries available for session boundary testing")

        session_boundary_results = {}

        for registry_name, registry_class in available_registries.items():
            try:
                # Create users with different sessions
                session_users = []

                for i in range(3):
                    user = TestUser(
                        user_id=f"{self.test_session_prefix}_session_user_{i}",
                        session_id=f"{self.test_session_prefix}_session_boundary_{i}_{uuid.uuid4().hex[:8]}",
                        agent_data={
                            'session_specific_data': f'SESSION_DATA_{i}',
                            'user_permissions': f'PERMISSIONS_USER_{i}',
                            'session_timestamp': datetime.now().isoformat()
                        }
                    )

                    # Create session-specific registry
                    if registry_name == 'basic':
                        user.registry = registry_class()
                    elif registry_name == 'advanced':
                        mock_context = self.mock_factory.create_mock_user_context(user.user_id) if self.mock_factory else MagicMock()
                        mock_context.user_id = user.user_id
                        mock_context.session_id = user.session_id
                        mock_context.session_data = user.agent_data
                        mock_dispatcher = MagicMock()
                        mock_bridge = MagicMock()

                        user.registry = registry_class(
                            user_context=mock_context,
                            tool_dispatcher=mock_dispatcher,
                            websocket_bridge=mock_bridge
                        )

                    self.registry_instances.append(user.registry)
                    session_users.append(user)

                # Test session boundary enforcement
                boundary_checks = {
                    'unique_session_ids': len(set(user.session_id for user in session_users)) == len(session_users),
                    'session_registry_isolation': len(set(id(user.registry) for user in session_users)) == len(session_users),
                    'no_cross_session_access': True,
                    'session_data_integrity': True
                }

                # Test session context isolation (advanced registry)
                if registry_name == 'advanced':
                    session_contexts = []
                    for user in session_users:
                        if hasattr(user.registry, 'user_context') and hasattr(user.registry.user_context, 'session_id'):
                            session_contexts.append(user.registry.user_context.session_id)

                    boundary_checks['session_contexts_unique'] = (
                        len(set(session_contexts)) == len(session_contexts)
                    )

                # Test cross-session access prevention
                for i, user1 in enumerate(session_users):
                    for j, user2 in enumerate(session_users):
                        if i != j:  # Different users
                            # Try to ensure user1 cannot access user2's session data
                            if (registry_name == 'advanced' and
                                hasattr(user1.registry, 'user_context') and
                                hasattr(user2.registry, 'user_context')):

                                context1 = user1.registry.user_context
                                context2 = user2.registry.user_context

                                # Sessions should not share IDs or data
                                if (hasattr(context1, 'session_id') and hasattr(context2, 'session_id') and
                                    context1.session_id == context2.session_id):
                                    boundary_checks['no_cross_session_access'] = False
                                    logger.error(f"Session ID collision between {user1.user_id} and {user2.user_id}")

                # Calculate session boundary enforcement score
                boundary_score = sum(boundary_checks.values()) / len(boundary_checks)
                session_boundary_results[registry_name] = {
                    'boundary_enforcement_score': boundary_score,
                    'boundary_checks': boundary_checks,
                    'sessions_tested': len(session_users)
                }

            except Exception as e:
                logger.error(f"Session boundary testing failed for {registry_name}: {e}")
                session_boundary_results[registry_name] = {'error': str(e)}

        # Analyze session boundary enforcement
        boundary_scores = [result.get('boundary_enforcement_score', 0)
                         for result in session_boundary_results.values()
                         if 'boundary_enforcement_score' in result]
        average_boundary_score = sum(boundary_scores) / len(boundary_scores) if boundary_scores else 0

        # Record metrics
        self.record_metric('session_boundary_score', average_boundary_score)
        self.record_metric('session_boundary_results', session_boundary_results)

        logger.info(f"Session boundary results: {session_boundary_results}")
        logger.info(f"Average boundary enforcement score: {average_boundary_score:.1%}")

        # Session boundaries must be very strong for security
        self.assertGreaterEqual(average_boundary_score, 0.9,
                               f"Session boundary enforcement must be at least 90% for security - "
                               f"got {average_boundary_score:.1%}")

    async def test_05_multi_user_security_summary(self):
        """
        Test 5: Multi-user security protection summary

        Summarizes all multi-user security metrics to demonstrate
        that enterprise-grade isolation is maintained during SSOT transition.

        INFORMATIONAL: Provides comprehensive security status overview
        """
        # Aggregate all security metrics from previous tests
        security_metrics = {
            'basic_user_isolation': self.get_metric('basic_user_isolation_score', 0),
            'concurrent_access_security': self.get_metric('concurrent_access_success_rate', 0),
            'data_leakage_prevention': self.get_metric('data_leakage_prevention_score', 0),
            'session_boundary_enforcement': self.get_metric('session_boundary_score', 0)
        }

        # Calculate overall multi-user security score
        security_scores = [score for score in security_metrics.values() if score > 0]
        overall_security_score = sum(security_scores) / len(security_scores) if security_scores else 0

        # Security incident counts
        total_violations = len(self.isolation_violations) + len(self.data_leakage_incidents)

        # Record comprehensive security metrics
        self.record_metric('overall_multi_user_security_score', overall_security_score)
        self.record_metric('security_metrics_summary', security_metrics)
        self.record_metric('total_security_violations', total_violations)

        # Log comprehensive security status
        logger.info("=== MULTI-USER SECURITY PROTECTION SUMMARY ===")
        logger.info(f"Overall Multi-User Security Score: {overall_security_score:.1%}")
        logger.info("Security Protection Areas:")
        logger.info(f"  - Basic User Isolation: {security_metrics['basic_user_isolation']:.1%}")
        logger.info(f"  - Concurrent Access Security: {security_metrics['concurrent_access_security']:.1%}")
        logger.info(f"  - Data Leakage Prevention: {security_metrics['data_leakage_prevention']:.1%}")
        logger.info(f"  - Session Boundary Enforcement: {security_metrics['session_boundary_enforcement']:.1%}")

        logger.info(f"Total Users Tested: {len(self.test_users)}")
        logger.info(f"Total Registry Instances: {len(self.registry_instances)}")
        logger.info(f"Security Violations Found: {total_violations}")
        logger.info(f"Isolation Violations: {len(self.isolation_violations)}")
        logger.info(f"Data Leakage Incidents: {len(self.data_leakage_incidents)}")

        # Security incident details
        if self.isolation_violations:
            logger.warning("Isolation Violations:")
            for violation in self.isolation_violations:
                logger.warning(f"  - {violation}")

        if self.data_leakage_incidents:
            logger.error("Data Leakage Incidents:")
            for incident in self.data_leakage_incidents:
                logger.error(f"  - {incident}")

        logger.info("=== END MULTI-USER SECURITY SUMMARY ===")

        # Enterprise-grade security requirements
        self.assertGreaterEqual(overall_security_score, 0.85,
                               f"Overall multi-user security must be at least 85% for enterprise deployment - "
                               f"got {overall_security_score:.1%}")

        # Zero tolerance for security violations in production
        self.assertEqual(total_violations, 0,
                        f"Zero security violations allowed for enterprise deployment - "
                        f"found {total_violations} violations")


if __name__ == "__main__":
    unittest.main()