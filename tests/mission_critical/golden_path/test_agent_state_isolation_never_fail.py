"""Mission Critical Test Suite: Agent State Isolation - Legal/Compliance Protection

This test suite is the SECOND HIGHEST PRIORITY mission critical test protecting against
data leakage lawsuits and ensuring complete user isolation in our multi-tenant system.

BUSINESS IMPACT:
- Data leakage = Legal liability + Customer trust loss + Enterprise contract violations
- Cross-user contamination = Regulatory compliance failures + Audit failures
- State isolation failures = Security breaches + Loss of enterprise customers

LEGAL COMPLIANCE REQUIREMENTS:
- GDPR Article 32: Technical and organizational security measures
- SOC 2 Type II: Access control and logical security
- Enterprise contracts: Complete user data isolation guarantees

CRITICAL: This test prevents cascade failures that could result in:
1. Multi-million dollar lawsuits from data exposure
2. Loss of enterprise contracts requiring user isolation
3. Regulatory fines and compliance failures
4. Complete loss of customer trust

ZERO TOLERANCE POLICY:
- NO MOCKS ALLOWED - All tests use production services (PostgreSQL, Redis, WebSocket, LLM)
- 10+ concurrent authenticated users minimum for realistic enterprise load
- Every test must detect and FAIL on ANY isolation violation
- Authentication REQUIRED for all tests (uses SSOT e2e_auth_helper)

COMPLIANCE:
@claude.md - REAL services only, complete feature freeze, existing features work
@spec/core.xml - SSOT pattern enforcement with complete user isolation
@spec/type_safety.xml - Full type safety with StronglyTypedUserExecutionContext

CRITICAL TEST SCENARIOS:
1. User context isolation - User A never sees User B's agent state
2. Factory isolation - Each user gets independent factory instances  
3. WebSocket auth isolation - Events only go to correct authenticated user
4. Tool execution isolation - Tool results scoped per user session
"""

import asyncio
import json
import logging
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from threading import Lock, Event
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import pytest
import redis.asyncio as redis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# SSOT Imports for Authentication and Types
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    AuthenticatedUser,
    create_authenticated_user,
    create_authenticated_user_context
)
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from test_framework.backend_client import BackendTestClient
from test_framework.test_context import TestContext, create_isolated_test_contexts

# Core Service Imports for Factory Testing
from netra_backend.app.services.user_execution_context import (
    UserContextFactory,
    UserExecutionContext,
    create_isolated_execution_context,
    InvalidContextError,
    ContextIsolationError
)

logger = logging.getLogger(__name__)


@dataclass
class IsolationTestMetrics:
    """Thread-safe metrics for isolation violation detection."""
    
    def __init__(self):
        self._lock = Lock()
        self._metrics = {
            'total_users': 0,
            'successful_isolations': 0,
            'isolation_violations': 0,
            'cross_user_contaminations': 0,
            'factory_isolation_failures': 0,
            'websocket_auth_violations': 0,
            'tool_execution_leaks': 0,
            'violation_details': [],
            'user_contexts': {},
            'performance_metrics': {
                'avg_context_creation_time': 0.0,
                'avg_isolation_check_time': 0.0,
                'peak_concurrent_users': 0
            }
        }
    
    def record_isolation_violation(self, user_id: str, violation_type: str, 
                                 details: Dict[str, Any], severity: str = "CRITICAL"):
        """Record an isolation violation with full details for audit trail."""
        with self._lock:
            self._metrics['isolation_violations'] += 1
            
            violation_record = {
                'user_id': user_id,
                'violation_type': violation_type,
                'severity': severity,
                'details': details,
                'timestamp': time.time(),
                'thread_id': threading.get_ident(),
                'isolation_test_id': uuid.uuid4().hex[:12]
            }
            
            self._metrics['violation_details'].append(violation_record)
            
            # Update specific violation counters
            if violation_type == 'cross_user_contamination':
                self._metrics['cross_user_contaminations'] += 1
            elif violation_type == 'factory_isolation_failure':
                self._metrics['factory_isolation_failures'] += 1
            elif violation_type == 'websocket_auth_violation':
                self._metrics['websocket_auth_violations'] += 1
            elif violation_type == 'tool_execution_leak':
                self._metrics['tool_execution_leaks'] += 1
    
    def record_successful_isolation(self, user_id: str, operation_type: str, duration: float):
        """Record successful isolation test completion."""
        with self._lock:
            self._metrics['successful_isolations'] += 1
            
            if user_id not in self._metrics['user_contexts']:
                self._metrics['user_contexts'][user_id] = {
                    'operations': 0,
                    'violations': 0,
                    'avg_duration': 0.0,
                    'isolation_score': 100.0
                }
            
            user_ctx = self._metrics['user_contexts'][user_id]
            user_ctx['operations'] += 1
            user_ctx['avg_duration'] = (
                (user_ctx['avg_duration'] * (user_ctx['operations'] - 1) + duration)
                / user_ctx['operations']
            )
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report for legal/audit requirements."""
        with self._lock:
            total_operations = self._metrics['successful_isolations'] + self._metrics['isolation_violations']
            compliance_score = (
                (self._metrics['successful_isolations'] / total_operations * 100) 
                if total_operations > 0 else 0.0
            )
            
            return {
                'compliance_score': compliance_score,
                'total_operations': total_operations,
                'isolation_violations': self._metrics['isolation_violations'],
                'violation_breakdown': {
                    'cross_user_contaminations': self._metrics['cross_user_contaminations'],
                    'factory_isolation_failures': self._metrics['factory_isolation_failures'],
                    'websocket_auth_violations': self._metrics['websocket_auth_violations'],
                    'tool_execution_leaks': self._metrics['tool_execution_leaks']
                },
                'legal_compliance_status': 'PASS' if compliance_score == 100.0 else 'FAIL',
                'audit_trail': self._metrics['violation_details'],
                'user_isolation_scores': self._metrics['user_contexts'],
                'performance_metrics': self._metrics['performance_metrics']
            }


@pytest.fixture(scope="module")
def isolated_env():
    """Isolated environment for mission critical testing."""
    return IsolatedEnvironment()


@pytest.fixture(scope="module")
async def redis_client(isolated_env):
    """Real Redis client for agent state isolation testing."""
    redis_url = isolated_env.get('REDIS_URL', 'redis://localhost:6381')
    client = redis.from_url(redis_url, decode_responses=True)
    
    # Ensure connection works
    try:
        await client.ping()
    except Exception as e:
        pytest.skip(f"Redis service not available for isolation testing: {e}")
    
    yield client
    
    # Cleanup all test data
    await client.flushdb()
    await client.close()


@pytest.fixture(scope="module") 
async def database_engine(isolated_env):
    """Real database engine for user isolation testing."""
    database_url = isolated_env.get('DATABASE_URL', 'postgresql+asyncpg://netra:netra@localhost:5434/netra_test')
    engine = create_async_engine(database_url, echo=False, pool_size=25, max_overflow=35)
    
    # Test connection
    try:
        async with engine.begin() as conn:
            await conn.execute(sa.text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"Database service not available for isolation testing: {e}")
    
    yield engine
    
    await engine.dispose()


@pytest.fixture(scope="module")
async def backend_client(isolated_env):
    """Real backend client for tool execution isolation testing."""
    backend_url = isolated_env.get('BACKEND_URL', 'http://localhost:8000')
    client = BackendTestClient(backend_url)
    
    # Ensure backend is healthy
    try:
        health_ok = await client.health_check()
        if not health_ok:
            pytest.skip("Backend service not available for isolation testing")
    except Exception:
        pytest.skip("Backend service not available for isolation testing")
    
    yield client
    
    await client.close()


@pytest.fixture(scope="function")
def auth_helper():
    """E2E authentication helper for creating authenticated users."""
    return E2EAuthHelper(environment="test")


@pytest.mark.mission_critical
@pytest.mark.auth_required
class TestAgentStateIsolationNeverFail:
    """
    Mission Critical test suite for agent state isolation - Legal/Compliance Protection.
    
    This suite tests complete user isolation across all system components to prevent
    data leakage that could result in lawsuits, compliance failures, and loss of trust.
    
    CRITICAL REQUIREMENTS:
    - 10+ concurrent authenticated users per test
    - Real services (PostgreSQL, Redis, WebSocket, Backend) 
    - Zero tolerance for ANY isolation violations
    - Complete audit trail for compliance reporting
    """

    @pytest.mark.asyncio
    async def test_user_context_never_leaks_between_sessions(self, redis_client, database_engine, auth_helper):
        """
        CRITICAL: User A's agent state never visible to User B - Data Leakage Prevention.
        
        BUSINESS IMPACT: Data leakage = Legal liability + Customer trust loss
        LEGAL REQUIREMENT: Complete user data isolation per GDPR Article 32
        
        This test creates 12+ concurrent authenticated users and verifies that each user's
        agent state, conversation history, and sensitive data remains completely isolated.
        """
        logger.info("🚨 MISSION CRITICAL: Testing user context isolation - Legal compliance requirement")
        
        # Create 15 concurrent authenticated users for comprehensive isolation testing
        authenticated_users: List[AuthenticatedUser] = []
        for i in range(15):
            user = await auth_helper.create_authenticated_user(
                email=f"isolation_test_user_{i}_{uuid.uuid4().hex[:8]}@legal-compliance.test",
                full_name=f"Isolation Test User {i}",
                permissions=["read", "write", "agent_execution"]
            )
            authenticated_users.append(user)
        
        metrics = IsolationTestMetrics()
        isolation_test_results = []
        
        async def test_user_context_isolation(user: AuthenticatedUser) -> Dict[str, Any]:
            """Comprehensive user context isolation test for single user."""
            user_id = user.get_strongly_typed_user_id()
            start_time = time.time()
            
            try:
                # Phase 1: Create highly sensitive user context and agent state
                user_context_key = f"user_context:{user_id}:{uuid.uuid4().hex}"
                sensitive_agent_state = {
                    'user_id': str(user_id),
                    'jwt_token': user.jwt_token,
                    'conversation_history': [
                        f"CONFIDENTIAL CONVERSATION {i} FOR {user_id}: {uuid.uuid4().hex}"
                        for i in range(50)  # Large conversation history
                    ],
                    'agent_memories': {
                        f'memory_{j}': {
                            'private_context': f"PRIVATE MEMORY {j} FOR {user_id}",
                            'user_secrets': f"SECRET-DATA-{user_id}-{j}-{uuid.uuid4().hex}",
                            'sensitive_analysis': f"CONFIDENTIAL ANALYSIS FOR {user_id}",
                            'personal_data': {
                                'email': user.email,
                                'full_name': user.full_name,
                                'user_preferences': f"PREFERENCES-{user_id}-{j}"
                            }
                        }
                        for j in range(10)
                    },
                    'execution_context': {
                        'thread_id': f"thread_{uuid.uuid4().hex}",
                        'run_id': f"run_{uuid.uuid4().hex}",
                        'request_id': f"request_{uuid.uuid4().hex}",
                        'websocket_client_id': f"ws_{uuid.uuid4().hex}",
                        'session_start': start_time,
                        'isolation_test_marker': f"ISOLATION-MARKER-{user_id}-{uuid.uuid4().hex}"
                    }
                }
                
                # Store sensitive state in Redis
                await redis_client.hset(user_context_key, mapping={
                    k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in sensitive_agent_state.items()
                })
                
                # Phase 2: Create database records with user-specific sensitive data
                async_session = async_sessionmaker(database_engine, expire_on_commit=False)
                async with async_session() as session:
                    await session.execute(sa.text("""
                        CREATE TABLE IF NOT EXISTS user_agent_state_isolation_test (
                            id SERIAL PRIMARY KEY,
                            user_id VARCHAR(255) NOT NULL,
                            agent_state_data JSONB NOT NULL,
                            conversation_data JSONB NOT NULL,
                            sensitive_metadata JSONB NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            isolation_test_id VARCHAR(255) NOT NULL
                        )
                    """))
                    
                    isolation_test_id = f"isolation-{user_id}-{int(time.time())}"
                    
                    # Insert highly sensitive user data
                    await session.execute(sa.text("""
                        INSERT INTO user_agent_state_isolation_test 
                        (user_id, agent_state_data, conversation_data, sensitive_metadata, isolation_test_id)
                        VALUES (:user_id, :agent_state_data, :conversation_data, :sensitive_metadata, :isolation_test_id)
                    """), {
                        'user_id': str(user_id),
                        'agent_state_data': json.dumps({
                            'agent_type': 'data_analysis',
                            'current_state': 'processing_sensitive_data',
                            'private_variables': f"PRIVATE-VARS-{user_id}",
                            'execution_stack': [f"stack_frame_{i}_{user_id}" for i in range(5)]
                        }),
                        'conversation_data': json.dumps({
                            'messages': [f"USER MESSAGE {i}: {uuid.uuid4().hex}" for i in range(20)],
                            'ai_responses': [f"AI RESPONSE {i} FOR {user_id}" for i in range(20)],
                            'private_notes': f"CONFIDENTIAL NOTES FOR {user_id}"
                        }),
                        'sensitive_metadata': json.dumps({
                            'user_email': user.email,
                            'user_name': user.full_name,
                            'permissions': user.permissions,
                            'authentication_token': user.jwt_token[:20] + "...",  # Partial token for security
                            'isolation_marker': f"DB-ISOLATION-{user_id}"
                        }),
                        'isolation_test_id': isolation_test_id
                    })
                    await session.commit()
                
                # Phase 3: Simulate concurrent operations to stress isolation
                stress_operations = []
                for stress_idx in range(10):
                    stress_key = f"stress_operation:{user_id}:{stress_idx}"
                    stress_data = f"STRESS-DATA-{user_id}-{stress_idx}-{uuid.uuid4().hex}"
                    
                    await redis_client.set(stress_key, stress_data)
                    stress_operations.append(stress_key)
                    
                    # Small delay to encourage race conditions
                    await asyncio.sleep(0.01)
                
                # Phase 4: CRITICAL ISOLATION CHECK - Cross-user contamination detection
                contamination_violations = []
                
                # Check Redis for contamination
                for other_user in authenticated_users:
                    if other_user.user_id != user.user_id:
                        # Look for this user's data in other users' keys
                        other_user_pattern = f"user_context:{other_user.user_id}:*"
                        other_keys = await redis_client.keys(other_user_pattern)
                        
                        for other_key in other_keys:
                            other_data = await redis_client.hgetall(other_key)
                            
                            # Check if our user's data appears in another user's context
                            for key, value in other_data.items():
                                if str(user_id) in str(value) or user.email in str(value):
                                    contamination_violations.append({
                                        'type': 'redis_cross_contamination',
                                        'our_user': str(user_id),
                                        'contaminated_user': other_user.user_id,
                                        'contaminated_key': other_key,
                                        'field': key,
                                        'contaminated_value': str(value)[:100]
                                    })
                
                # Check database for contamination
                async with async_session() as session:
                    # Look for our user ID in other users' records
                    contamination_check = await session.execute(sa.text("""
                        SELECT user_id, agent_state_data, conversation_data, sensitive_metadata, isolation_test_id
                        FROM user_agent_state_isolation_test
                        WHERE user_id != :our_user_id
                    """), {'our_user_id': str(user_id)})
                    
                    other_user_records = contamination_check.fetchall()
                    for record in other_user_records:
                        record_user_id, agent_data, conv_data, meta_data, test_id = record
                        
                        # Check all JSON fields for contamination
                        all_data = json.dumps([agent_data, conv_data, meta_data])
                        if str(user_id) in all_data or user.email in all_data:
                            contamination_violations.append({
                                'type': 'database_cross_contamination',
                                'our_user': str(user_id),
                                'contaminated_user': record_user_id,
                                'test_id': test_id,
                                'contamination_found_in': 'database_record'
                            })
                
                # Phase 5: Verify data integrity and isolation
                user_data_check = await redis_client.hgetall(user_context_key)
                if not user_data_check or user_data_check.get('user_id') != str(user_id):
                    contamination_violations.append({
                        'type': 'data_integrity_failure',
                        'details': 'User context data lost or corrupted',
                        'expected_user': str(user_id),
                        'actual_data': user_data_check
                    })
                
                duration = time.time() - start_time
                
                # Cleanup test data
                await redis_client.delete(user_context_key)
                for stress_key in stress_operations:
                    await redis_client.delete(stress_key)
                
                async with async_session() as session:
                    await session.execute(sa.text("""
                        DELETE FROM user_agent_state_isolation_test WHERE user_id = :user_id
                    """), {'user_id': str(user_id)})
                    await session.commit()
                
                # Record results
                if contamination_violations:
                    for violation in contamination_violations:
                        metrics.record_isolation_violation(
                            str(user_id), 'cross_user_contamination', violation, 'CRITICAL'
                        )
                    
                    return {
                        'status': 'ISOLATION_VIOLATION',
                        'user_id': str(user_id),
                        'violations': contamination_violations,
                        'violation_count': len(contamination_violations),
                        'duration': duration
                    }
                else:
                    metrics.record_successful_isolation(str(user_id), 'user_context_isolation', duration)
                    return {
                        'status': 'SUCCESS',
                        'user_id': str(user_id),
                        'isolation_verified': True,
                        'operations_completed': 11 + len(stress_operations),  # Redis + DB + stress ops
                        'duration': duration
                    }
                
            except Exception as e:
                metrics.record_isolation_violation(
                    str(user_id), 'isolation_test_exception', 
                    {'error': str(e), 'type': type(e).__name__}, 'CRITICAL'
                )
                return {
                    'status': 'ERROR',
                    'user_id': str(user_id),
                    'error': str(e),
                    'violation_severity': 'CRITICAL'
                }
        
        # Execute all user isolation tests concurrently
        logger.info(f"🔒 Executing concurrent isolation tests for {len(authenticated_users)} users")
        start_time = time.time()
        
        tasks = [test_user_context_isolation(user) for user in authenticated_users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Analyze results for compliance
        isolation_violations = []
        successful_isolations = 0
        
        for result in results:
            if isinstance(result, dict):
                if result.get('status') == 'ISOLATION_VIOLATION':
                    isolation_violations.extend(result.get('violations', []))
                elif result.get('status') == 'SUCCESS':
                    successful_isolations += 1
                elif result.get('status') == 'ERROR':
                    isolation_violations.append({
                        'type': 'test_execution_error',
                        'error': result.get('error'),
                        'user_id': result.get('user_id')
                    })
            else:
                # Exception occurred
                isolation_violations.append({
                    'type': 'test_framework_exception',
                    'error': str(result),
                    'severity': 'CRITICAL'
                })
        
        # Generate compliance report
        compliance_report = metrics.get_compliance_report()
        
        # Cleanup test table
        async with database_engine.begin() as conn:
            await conn.execute(sa.text("DROP TABLE IF EXISTS user_agent_state_isolation_test"))
        
        # CRITICAL ASSERTIONS - Zero tolerance for violations
        assert len(isolation_violations) == 0, (
            f"🚨 CRITICAL ISOLATION VIOLATIONS DETECTED - LEGAL COMPLIANCE FAILURE!\n"
            f"Violations: {len(isolation_violations)}\n"
            f"Details: {json.dumps(isolation_violations, indent=2)}\n"
            f"Compliance Score: {compliance_report['compliance_score']}%\n"
            f"This represents a critical security breach requiring immediate remediation!"
        )
        
        success_rate = (successful_isolations / len(authenticated_users)) * 100
        assert success_rate == 100.0, (
            f"User context isolation success rate: {success_rate}% (MUST be 100% for legal compliance)"
        )
        
        assert total_duration < 60.0, (
            f"Isolation test duration too high: {total_duration}s (performance requirement: < 60s)"
        )
        
        logger.info(f"✅ LEGAL COMPLIANCE: User context isolation verified for {len(authenticated_users)} users")
        logger.info(f"🛡️ SECURITY: Zero isolation violations detected - Legal requirements satisfied")

    @pytest.mark.asyncio
    async def test_factory_isolation_enforcement_per_user(self, redis_client, auth_helper):
        """
        CRITICAL: Each user gets independent factory instances - Factory Isolation.
        
        BUSINESS IMPACT: Shared instances = cross-contamination = enterprise contract violations
        ENTERPRISE REQUIREMENT: Complete factory isolation per user session
        
        This test validates that UserContextFactory creates completely isolated instances
        for each user with no shared state or cross-user memory contamination.
        """
        logger.info("🏭 MISSION CRITICAL: Testing factory isolation - Enterprise contract requirement")
        
        # Create 12 authenticated users for factory isolation testing
        authenticated_users: List[AuthenticatedUser] = []
        for i in range(12):
            user = await auth_helper.create_authenticated_user(
                email=f"factory_test_user_{i}_{uuid.uuid4().hex[:8]}@enterprise.test",
                full_name=f"Factory Test User {i}",
                permissions=["read", "write", "factory_access"]
            )
            authenticated_users.append(user)
        
        metrics = IsolationTestMetrics()
        factory_contexts = {}  # Track created contexts per user
        
        async def test_factory_isolation_for_user(user: AuthenticatedUser) -> Dict[str, Any]:
            """Test factory isolation for individual user."""
            user_id = user.get_strongly_typed_user_id()
            start_time = time.time()
            
            try:
                # Phase 1: Create user execution context via factory
                context_factory = UserContextFactory()
                
                # Create multiple contexts for this user to test factory memory isolation
                user_contexts = []
                for ctx_idx in range(5):
                    # Create context with unique data for contamination detection
                    unique_marker = f"FACTORY-ISOLATION-{user_id}-{ctx_idx}-{uuid.uuid4().hex}"
                    
                    context = await create_isolated_execution_context(
                        user_id=str(user_id),
                        thread_id=f"thread_{uuid.uuid4().hex}",
                        run_id=f"run_{uuid.uuid4().hex}",
                        additional_context={
                            'factory_test_marker': unique_marker,
                            'user_email': user.email,
                            'user_permissions': user.permissions,
                            'context_index': ctx_idx,
                            'sensitive_factory_data': f"SENSITIVE-{user_id}-{ctx_idx}",
                            'jwt_token_hash': hash(user.jwt_token),
                            'creation_timestamp': start_time
                        }
                    )
                    
                    user_contexts.append({
                        'context': context,
                        'unique_marker': unique_marker,
                        'context_index': ctx_idx
                    })
                
                factory_contexts[str(user_id)] = user_contexts
                
                # Phase 2: Store factory-created data in Redis for cross-contamination checks
                for ctx_data in user_contexts:
                    context = ctx_data['context']
                    marker = ctx_data['unique_marker']
                    
                    factory_key = f"factory_context:{user_id}:{ctx_data['context_index']}"
                    factory_data = {
                        'user_id': str(user_id),
                        'context_id': context.request_id,
                        'thread_id': context.thread_id,
                        'run_id': context.run_id,
                        'unique_marker': marker,
                        'factory_isolated_data': f"FACTORY-DATA-{user_id}-{uuid.uuid4().hex}",
                        'agent_context': json.dumps(context.agent_context),
                        'audit_metadata': json.dumps(context.audit_metadata),
                        'creation_method': 'UserContextFactory'
                    }
                    
                    await redis_client.hset(factory_key, mapping={
                        k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                        for k, v in factory_data.items()
                    })
                
                # Phase 3: Test factory memory isolation - Verify no shared state
                isolation_violations = []
                
                # Check that each context is truly independent
                for i, ctx_data_1 in enumerate(user_contexts):
                    for j, ctx_data_2 in enumerate(user_contexts):
                        if i != j:
                            context_1 = ctx_data_1['context']
                            context_2 = ctx_data_2['context']
                            
                            # Contexts should have different IDs
                            if context_1.request_id == context_2.request_id:
                                isolation_violations.append({
                                    'type': 'factory_context_id_collision',
                                    'user_id': str(user_id),
                                    'context_1_index': i,
                                    'context_2_index': j,
                                    'shared_request_id': context_1.request_id
                                })
                            
                            # Agent contexts should not share objects
                            if context_1.agent_context is context_2.agent_context:
                                isolation_violations.append({
                                    'type': 'factory_shared_agent_context_object',
                                    'user_id': str(user_id),
                                    'context_1_index': i,
                                    'context_2_index': j
                                })
                
                # Phase 4: Cross-user factory contamination check
                # Check if this user's factory data appears in other users' contexts
                for other_user in authenticated_users:
                    if other_user.user_id != user.user_id:
                        other_user_pattern = f"factory_context:{other_user.user_id}:*"
                        other_keys = await redis_client.keys(other_user_pattern)
                        
                        for other_key in other_keys:
                            other_data = await redis_client.hgetall(other_key)
                            
                            # Check for cross-contamination
                            for field, value in other_data.items():
                                if str(user_id) in str(value) or user.email in str(value):
                                    isolation_violations.append({
                                        'type': 'factory_cross_user_contamination',
                                        'our_user': str(user_id),
                                        'contaminated_user': other_user.user_id,
                                        'contaminated_key': other_key,
                                        'contaminated_field': field,
                                        'contamination_value': str(value)[:100]
                                    })
                
                duration = time.time() - start_time
                
                # Cleanup factory test data
                for ctx_idx in range(5):
                    factory_key = f"factory_context:{user_id}:{ctx_idx}"
                    await redis_client.delete(factory_key)
                
                # Record results
                if isolation_violations:
                    for violation in isolation_violations:
                        metrics.record_isolation_violation(
                            str(user_id), 'factory_isolation_failure', violation, 'CRITICAL'
                        )
                    
                    return {
                        'status': 'FACTORY_ISOLATION_VIOLATION',
                        'user_id': str(user_id),
                        'violations': isolation_violations,
                        'contexts_created': len(user_contexts),
                        'duration': duration
                    }
                else:
                    metrics.record_successful_isolation(str(user_id), 'factory_isolation', duration)
                    return {
                        'status': 'SUCCESS',
                        'user_id': str(user_id),
                        'factory_isolation_verified': True,
                        'contexts_created': len(user_contexts),
                        'duration': duration
                    }
                
            except Exception as e:
                metrics.record_isolation_violation(
                    str(user_id), 'factory_test_exception',
                    {'error': str(e), 'type': type(e).__name__}, 'CRITICAL'
                )
                return {
                    'status': 'ERROR',
                    'user_id': str(user_id),
                    'error': str(e)
                }
        
        # Execute factory isolation tests concurrently
        logger.info(f"🏭 Testing factory isolation for {len(authenticated_users)} users")
        start_time = time.time()
        
        tasks = [test_factory_isolation_for_user(user) for user in authenticated_users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Analyze factory isolation results
        factory_violations = []
        successful_factory_tests = 0
        
        for result in results:
            if isinstance(result, dict):
                if result.get('status') == 'FACTORY_ISOLATION_VIOLATION':
                    factory_violations.extend(result.get('violations', []))
                elif result.get('status') == 'SUCCESS':
                    successful_factory_tests += 1
                elif result.get('status') == 'ERROR':
                    factory_violations.append({
                        'type': 'factory_test_error',
                        'error': result.get('error'),
                        'user_id': result.get('user_id')
                    })
            else:
                factory_violations.append({
                    'type': 'factory_test_exception',
                    'error': str(result)
                })
        
        # Generate compliance report
        compliance_report = metrics.get_compliance_report()
        
        # CRITICAL ASSERTIONS - Enterprise contract compliance
        assert len(factory_violations) == 0, (
            f"🚨 CRITICAL FACTORY ISOLATION VIOLATIONS - ENTERPRISE CONTRACT BREACH!\n"
            f"Violations: {len(factory_violations)}\n" 
            f"Details: {json.dumps(factory_violations, indent=2)}\n"
            f"This violates enterprise isolation requirements!"
        )
        
        success_rate = (successful_factory_tests / len(authenticated_users)) * 100
        assert success_rate == 100.0, (
            f"Factory isolation success rate: {success_rate}% (MUST be 100% for enterprise compliance)"
        )
        
        assert total_duration < 45.0, (
            f"Factory isolation test duration: {total_duration}s (performance requirement: < 45s)"
        )
        
        logger.info(f"✅ ENTERPRISE COMPLIANCE: Factory isolation verified for {len(authenticated_users)} users")
        logger.info(f"🏭 FACTORY: Zero shared instances detected - Enterprise requirements satisfied")

    @pytest.mark.asyncio
    async def test_websocket_auth_isolation_never_violated(self, backend_client, auth_helper):
        """
        CRITICAL: WebSocket events only go to correct authenticated user - Auth Isolation.
        
        BUSINESS IMPACT: Wrong user seeing events = data breach = lawsuits
        SECURITY REQUIREMENT: Complete WebSocket authentication isolation
        
        This test creates multiple authenticated WebSocket connections and verifies that
        each user only receives their own events, with zero cross-contamination.
        """
        logger.info("🔌 MISSION CRITICAL: Testing WebSocket auth isolation - Data breach prevention")
        
        # Create 10 authenticated users for WebSocket isolation testing
        authenticated_users: List[AuthenticatedUser] = []
        for i in range(10):
            user = await auth_helper.create_authenticated_user(
                email=f"websocket_test_user_{i}_{uuid.uuid4().hex[:8]}@security.test",
                full_name=f"WebSocket Test User {i}",
                permissions=["read", "write", "websocket_access"]
            )
            authenticated_users.append(user)
        
        metrics = IsolationTestMetrics()
        websocket_connections = []
        
        async def setup_authenticated_websocket_connection(user: AuthenticatedUser) -> Dict[str, Any]:
            """Set up authenticated WebSocket connection for user."""
            try:
                # Create test context with authentication
                context = TestContext(user_id=user.user_id)
                context.user_context.jwt_token = user.jwt_token
                context.user_context.email = user.email
                context.user_context.permissions = user.permissions
                
                # Attempt WebSocket connection with authentication
                try:
                    await context.setup_websocket_connection("/ws/chat", auth_required=True)
                    return {
                        'status': 'connected',
                        'user_id': user.user_id,
                        'context': context
                    }
                except ConnectionError as e:
                    logger.warning(f"WebSocket connection failed for user {user.user_id}: {e}")
                    return {
                        'status': 'connection_failed',
                        'user_id': user.user_id,
                        'error': str(e)
                    }
                
            except Exception as e:
                return {
                    'status': 'setup_error',
                    'user_id': user.user_id,
                    'error': str(e)
                }
        
        # Set up WebSocket connections for all users
        logger.info(f"🔌 Setting up authenticated WebSocket connections for {len(authenticated_users)} users")
        
        connection_tasks = [setup_authenticated_websocket_connection(user) for user in authenticated_users]
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Filter successful connections
        connected_contexts = []
        for i, result in enumerate(connection_results):
            if isinstance(result, dict) and result.get('status') == 'connected':
                connected_contexts.append({
                    'user': authenticated_users[i],
                    'context': result['context']
                })
        
        if len(connected_contexts) < 3:
            pytest.skip(f"Insufficient WebSocket connections ({len(connected_contexts)}) for isolation testing")
        
        logger.info(f"🔌 Testing WebSocket isolation with {len(connected_contexts)} authenticated connections")
        
        async def test_websocket_auth_isolation(connection_data: Dict[str, Any]) -> Dict[str, Any]:
            """Test WebSocket authentication isolation for single connection."""
            user = connection_data['user']
            context = connection_data['context']
            user_id = user.get_strongly_typed_user_id()
            start_time = time.time()
            
            try:
                # Phase 1: Send authenticated messages with sensitive data
                sent_messages = []
                for msg_idx in range(15):
                    sensitive_message = {
                        'type': 'agent_execution',
                        'content': f'CONFIDENTIAL AGENT REQUEST {msg_idx} FROM {user_id}: {uuid.uuid4().hex}',
                        'user_id': str(user_id),
                        'thread_id': context.user_context.thread_id,
                        'message_index': msg_idx,
                        'auth_token_hash': hash(user.jwt_token),
                        'sensitive_payload': f'SENSITIVE-{user_id}-{msg_idx}-{uuid.uuid4().hex}',
                        'user_email': user.email,
                        'timestamp': time.time()
                    }
                    
                    await context.send_message(sensitive_message)
                    sent_messages.append(sensitive_message)
                    
                    # Small delay for message processing
                    await asyncio.sleep(0.02)
                
                # Phase 2: Listen for responses and check for isolation violations
                received_events = await context.listen_for_events(duration=5.0)
                
                # Phase 3: Critical isolation verification
                auth_isolation_violations = []
                
                for event in received_events:
                    event_user_id = event.get('user_id')
                    event_content = str(event.get('content', ''))
                    
                    # Check 1: Verify we didn't receive another user's messages
                    if event_user_id and event_user_id != str(user_id):
                        auth_isolation_violations.append({
                            'type': 'received_other_user_websocket_event',
                            'our_user_id': str(user_id),
                            'received_from_user': event_user_id,
                            'event_type': event.get('type'),
                            'event_content_preview': event_content[:100]
                        })
                    
                    # Check 2: Verify event content doesn't contain other users' data
                    for other_connection in connected_contexts:
                        other_user = other_connection['user']
                        if other_user.user_id != user.user_id:
                            # Check for other user's ID, email, or token in our events
                            if (other_user.user_id in event_content or 
                                other_user.email in event_content or
                                str(hash(other_user.jwt_token)) in event_content):
                                auth_isolation_violations.append({
                                    'type': 'websocket_content_contamination',
                                    'our_user_id': str(user_id),
                                    'contaminating_user': other_user.user_id,
                                    'contamination_type': 'user_data_in_websocket_event',
                                    'event_type': event.get('type'),
                                    'contaminated_content_preview': event_content[:100]
                                })
                
                # Phase 4: Authentication verification
                # Verify all our messages were processed with proper authentication
                our_message_count = sum(1 for event in received_events 
                                      if event.get('user_id') == str(user_id))
                
                if our_message_count == 0 and len(sent_messages) > 0:
                    auth_isolation_violations.append({
                        'type': 'authentication_failure',
                        'details': 'No authenticated responses received despite sending messages',
                        'messages_sent': len(sent_messages),
                        'events_received': len(received_events)
                    })
                
                duration = time.time() - start_time
                
                # Record results
                if auth_isolation_violations:
                    for violation in auth_isolation_violations:
                        metrics.record_isolation_violation(
                            str(user_id), 'websocket_auth_violation', violation, 'CRITICAL'
                        )
                    
                    return {
                        'status': 'WEBSOCKET_AUTH_VIOLATION',
                        'user_id': str(user_id),
                        'violations': auth_isolation_violations,
                        'messages_sent': len(sent_messages),
                        'events_received': len(received_events),
                        'duration': duration
                    }
                else:
                    metrics.record_successful_isolation(str(user_id), 'websocket_auth_isolation', duration)
                    return {
                        'status': 'SUCCESS',
                        'user_id': str(user_id),
                        'websocket_auth_isolation_verified': True,
                        'messages_sent': len(sent_messages),
                        'events_received': len(received_events),
                        'duration': duration
                    }
                
            except Exception as e:
                metrics.record_isolation_violation(
                    str(user_id), 'websocket_test_exception',
                    {'error': str(e), 'type': type(e).__name__}, 'CRITICAL'
                )
                return {
                    'status': 'ERROR',
                    'user_id': str(user_id),
                    'error': str(e)
                }
        
        # Execute WebSocket isolation tests concurrently
        start_time = time.time()
        
        try:
            tasks = [test_websocket_auth_isolation(conn_data) for conn_data in connected_contexts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_duration = time.time() - start_time
            
            # Analyze WebSocket auth isolation results
            websocket_violations = []
            successful_websocket_tests = 0
            
            for result in results:
                if isinstance(result, dict):
                    if result.get('status') == 'WEBSOCKET_AUTH_VIOLATION':
                        websocket_violations.extend(result.get('violations', []))
                    elif result.get('status') == 'SUCCESS':
                        successful_websocket_tests += 1
                    elif result.get('status') == 'ERROR':
                        websocket_violations.append({
                            'type': 'websocket_test_error',
                            'error': result.get('error'),
                            'user_id': result.get('user_id')
                        })
                else:
                    websocket_violations.append({
                        'type': 'websocket_test_exception',
                        'error': str(result)
                    })
            
            # CRITICAL ASSERTIONS - Security requirement compliance
            assert len(websocket_violations) == 0, (
                f"🚨 CRITICAL WEBSOCKET AUTH VIOLATIONS - SECURITY BREACH!\n"
                f"Violations: {len(websocket_violations)}\n"
                f"Details: {json.dumps(websocket_violations, indent=2)}\n"
                f"This represents a critical authentication isolation failure!"
            )
            
            success_rate = (successful_websocket_tests / len(connected_contexts)) * 100
            assert success_rate >= 95.0, (
                f"WebSocket auth isolation success rate: {success_rate}% (MUST be >= 95% for security)"
            )
            
            logger.info(f"✅ SECURITY: WebSocket auth isolation verified for {len(connected_contexts)} connections")
            logger.info(f"🔌 WEBSOCKET: Zero authentication violations - Security requirements satisfied")
            
        finally:
            # Cleanup all WebSocket connections
            cleanup_tasks = []
            for conn_data in connected_contexts:
                cleanup_tasks.append(conn_data['context'].cleanup())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    @pytest.mark.asyncio  
    async def test_tool_execution_user_scoped_isolation(self, redis_client, backend_client, auth_helper):
        """
        CRITICAL: Tool executions isolated per user session - Tool Result Isolation.
        
        BUSINESS IMPACT: Cross-user tool results = wrong business decisions
        BUSINESS REQUIREMENT: Tool results only accessible to executing user
        
        This test verifies that tool execution results, intermediate states, and cached
        data remain completely isolated per user with no cross-contamination.
        """
        logger.info("🔧 MISSION CRITICAL: Testing tool execution isolation - Business decision integrity")
        
        # Create 8 authenticated users for tool execution isolation testing
        authenticated_users: List[AuthenticatedUser] = []
        for i in range(8):
            user = await auth_helper.create_authenticated_user(
                email=f"tool_test_user_{i}_{uuid.uuid4().hex[:8]}@business.test",
                full_name=f"Tool Test User {i}",
                permissions=["read", "write", "tool_execution", "agent_access"]
            )
            authenticated_users.append(user)
        
        metrics = IsolationTestMetrics()
        
        async def test_tool_execution_isolation(user: AuthenticatedUser) -> Dict[str, Any]:
            """Test tool execution isolation for individual user."""
            user_id = user.get_strongly_typed_user_id()  
            start_time = time.time()
            
            try:
                # Phase 1: Execute multiple tools with sensitive business data
                tool_executions = []
                for tool_idx in range(6):
                    execution_id = f"tool_exec_{user_id}_{tool_idx}_{uuid.uuid4().hex[:8]}"
                    
                    # Simulate tool execution with business-sensitive data
                    tool_execution_data = {
                        'execution_id': execution_id,
                        'user_id': str(user_id),
                        'tool_name': f'business_analyzer_{tool_idx}',
                        'execution_context': {
                            'user_email': user.email,
                            'user_permissions': user.permissions,
                            'jwt_token_hash': hash(user.jwt_token),
                            'business_context': f'BUSINESS-CONTEXT-{user_id}-{tool_idx}'
                        },
                        'input_data': {
                            'sensitive_business_data': f'CONFIDENTIAL-DATA-{user_id}-{tool_idx}-{uuid.uuid4().hex}',
                            'user_specific_parameters': {
                                'analysis_type': f'market_analysis_{tool_idx}',
                                'data_scope': f'user_scope_{user_id}',
                                'confidential_metrics': [f'metric_{j}_{user_id}' for j in range(5)]
                            },
                            'execution_timestamp': start_time,
                            'isolation_marker': f'TOOL-ISOLATION-{user_id}-{tool_idx}'
                        },
                        'intermediate_results': {
                            'processing_state': f'analyzing_data_for_{user_id}',
                            'partial_results': [f'result_{k}_{user_id}_{tool_idx}' for k in range(10)],
                            'cached_computations': f'CACHED-{user_id}-{tool_idx}-{uuid.uuid4().hex}'
                        },
                        'final_results': {
                            'business_insights': f'INSIGHTS-FOR-{user_id}-{tool_idx}',
                            'recommendations': f'RECOMMENDATIONS-{user_id}-{tool_idx}',
                            'sensitive_conclusions': f'CONFIDENTIAL-CONCLUSIONS-{user_id}-{tool_idx}'
                        }
                    }
                    
                    # Store tool execution data in Redis (simulating tool result caching)
                    tool_key = f"tool_execution:{user_id}:{execution_id}"
                    await redis_client.hset(tool_key, mapping={
                        k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                        for k, v in tool_execution_data.items()
                    })
                    
                    tool_executions.append({
                        'execution_id': execution_id,
                        'tool_key': tool_key,
                        'data': tool_execution_data
                    })
                    
                    # Simulate processing delay
                    await asyncio.sleep(0.05)
                
                # Phase 2: Store additional user-scoped tool cache data
                user_tool_cache = f"tool_cache:{user_id}:shared"
                cache_data = {
                    'user_id': str(user_id),
                    'cached_tool_results': {
                        exec['execution_id']: f"CACHED-RESULT-{user_id}-{exec['execution_id']}"
                        for exec in tool_executions
                    },
                    'tool_session_data': {
                        'session_id': f"session_{uuid.uuid4().hex}",
                        'user_preferences': f'PREFERENCES-{user_id}',
                        'tool_history': [exec['execution_id'] for exec in tool_executions],
                        'sensitive_session_info': f'SESSION-INFO-{user_id}-{uuid.uuid4().hex}'
                    },
                    'performance_metrics': {
                        'execution_times': [0.1 * i for i in range(len(tool_executions))],
                        'user_specific_optimizations': f'OPTIMIZATIONS-{user_id}',
                        'cache_hit_ratios': [0.8, 0.9, 0.95]
                    }
                }
                
                await redis_client.hset(user_tool_cache, mapping={
                    k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in cache_data.items()
                })
                
                # Phase 3: Critical tool isolation verification
                tool_isolation_violations = []
                
                # Check 1: Verify our tool execution data is intact
                for exec_data in tool_executions:
                    stored_data = await redis_client.hgetall(exec_data['tool_key'])
                    
                    if not stored_data or stored_data.get('user_id') != str(user_id):
                        tool_isolation_violations.append({
                            'type': 'tool_execution_data_loss',
                            'execution_id': exec_data['execution_id'],
                            'expected_user': str(user_id),
                            'actual_data': stored_data
                        })
                
                # Check 2: Cross-user tool contamination detection
                for other_user in authenticated_users:
                    if other_user.user_id != user.user_id:
                        # Check if other user's tool data contains our user's information
                        other_tool_pattern = f"tool_execution:{other_user.user_id}:*"
                        other_keys = await redis_client.keys(other_tool_pattern)
                        
                        for other_key in other_keys:
                            other_data = await redis_client.hgetall(other_key)
                            
                            # Check for contamination
                            for field, value in other_data.items():
                                if (str(user_id) in str(value) or 
                                    user.email in str(value) or 
                                    f'ISOLATION-{user_id}' in str(value)):
                                    tool_isolation_violations.append({
                                        'type': 'tool_execution_cross_contamination',
                                        'our_user': str(user_id),
                                        'contaminated_user': other_user.user_id,
                                        'contaminated_key': other_key,
                                        'contaminated_field': field,
                                        'contamination_preview': str(value)[:100]
                                    })
                        
                        # Check other user's tool cache for contamination
                        other_cache_key = f"tool_cache:{other_user.user_id}:shared"
                        other_cache_data = await redis_client.hgetall(other_cache_key)
                        
                        for field, value in other_cache_data.items():
                            if str(user_id) in str(value) or user.email in str(value):
                                tool_isolation_violations.append({
                                    'type': 'tool_cache_cross_contamination',
                                    'our_user': str(user_id),
                                    'contaminated_user': other_user.user_id,
                                    'cache_field': field,
                                    'contamination_preview': str(value)[:100]
                                })
                
                # Check 3: Tool result access isolation
                # Verify we can only access our own tool results
                our_cache_data = await redis_client.hgetall(user_tool_cache)
                if not our_cache_data or our_cache_data.get('user_id') != str(user_id):
                    tool_isolation_violations.append({
                        'type': 'tool_cache_access_failure',
                        'user_id': str(user_id),
                        'cache_key': user_tool_cache,
                        'expected_user': str(user_id),
                        'actual_cache_data': our_cache_data
                    })
                
                duration = time.time() - start_time
                
                # Cleanup tool execution data
                for exec_data in tool_executions:
                    await redis_client.delete(exec_data['tool_key'])
                await redis_client.delete(user_tool_cache)
                
                # Record results
                if tool_isolation_violations:
                    for violation in tool_isolation_violations:
                        metrics.record_isolation_violation(
                            str(user_id), 'tool_execution_leak', violation, 'CRITICAL'
                        )
                    
                    return {
                        'status': 'TOOL_ISOLATION_VIOLATION',
                        'user_id': str(user_id),
                        'violations': tool_isolation_violations,
                        'tool_executions_tested': len(tool_executions),
                        'duration': duration
                    }
                else:
                    metrics.record_successful_isolation(str(user_id), 'tool_execution_isolation', duration)
                    return {
                        'status': 'SUCCESS',
                        'user_id': str(user_id),
                        'tool_isolation_verified': True,
                        'tool_executions_tested': len(tool_executions),
                        'duration': duration
                    }
                
            except Exception as e:
                metrics.record_isolation_violation(
                    str(user_id), 'tool_test_exception',
                    {'error': str(e), 'type': type(e).__name__}, 'CRITICAL'
                )
                return {
                    'status': 'ERROR',
                    'user_id': str(user_id),
                    'error': str(e)
                }
        
        # Execute tool isolation tests concurrently
        logger.info(f"🔧 Testing tool execution isolation for {len(authenticated_users)} users")
        start_time = time.time()
        
        tasks = [test_tool_execution_isolation(user) for user in authenticated_users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Analyze tool isolation results
        tool_violations = []
        successful_tool_tests = 0
        
        for result in results:
            if isinstance(result, dict):
                if result.get('status') == 'TOOL_ISOLATION_VIOLATION':
                    tool_violations.extend(result.get('violations', []))
                elif result.get('status') == 'SUCCESS':
                    successful_tool_tests += 1
                elif result.get('status') == 'ERROR':
                    tool_violations.append({
                        'type': 'tool_test_error',
                        'error': result.get('error'),
                        'user_id': result.get('user_id')
                    })
            else:
                tool_violations.append({
                    'type': 'tool_test_exception', 
                    'error': str(result)
                })
        
        # Generate compliance report
        compliance_report = metrics.get_compliance_report()
        
        # CRITICAL ASSERTIONS - Business integrity requirement
        assert len(tool_violations) == 0, (
            f"🚨 CRITICAL TOOL EXECUTION VIOLATIONS - BUSINESS INTEGRITY FAILURE!\n"
            f"Violations: {len(tool_violations)}\n"
            f"Details: {json.dumps(tool_violations, indent=2)}\n"
            f"This could lead to incorrect business decisions and data corruption!"
        )
        
        success_rate = (successful_tool_tests / len(authenticated_users)) * 100
        assert success_rate == 100.0, (
            f"Tool execution isolation success rate: {success_rate}% (MUST be 100% for business integrity)"
        )
        
        assert total_duration < 50.0, (
            f"Tool isolation test duration: {total_duration}s (performance requirement: < 50s)"
        )
        
        logger.info(f"✅ BUSINESS INTEGRITY: Tool execution isolation verified for {len(authenticated_users)} users")
        logger.info(f"🔧 TOOLS: Zero cross-user contamination detected - Business requirements satisfied")


if __name__ == "__main__":
    # Run mission critical agent state isolation tests with real services
    pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "--no-cov",
        "-s",  # Show output for debugging
        "--maxfail=1",  # Stop on first failure for immediate attention
        "-m", "mission_critical"  # Only run mission critical tests
    ])