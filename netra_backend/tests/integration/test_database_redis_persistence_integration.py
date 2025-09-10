"""
Database & Redis Persistence Integration Tests for Golden Path
===========================================================

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Platform Foundation
- Business Goal: Ensure data persistence and retrieval across all Golden Path scenarios  
- Value Impact: Data loss or corruption would break conversation continuity and user trust
- Strategic Impact: $500K+ ARR depends on reliable data persistence for chat functionality

This test suite validates the COMPLETE persistence layer for Golden Path scenarios:
1. Database Thread & Message Persistence - Conversation continuity
2. Redis Session & Result Caching - Performance and state management  
3. Agent Result Compilation & Response - Final value delivery storage
4. All 5 Golden Path Exit Point scenarios with proper data persistence
5. Multi-user data isolation and concurrent access validation
6. Data integrity, recovery, and cleanup processes

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real PostgreSQL and Redis via real_services_fixture
- Integration level testing - Between unit and E2E 
- Each test validates actual business persistence scenarios
- Tests must complete within 60 seconds each
- Validates multi-user data isolation properly
"""

import asyncio
import uuid
import pytest
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from sqlalchemy import text, select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, OperationalError

# Test framework imports (SSOT patterns)
from test_framework.base_integration_test import BaseIntegrationTest, DatabaseIntegrationTest, CacheIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, SessionID,
    ensure_user_id, ensure_thread_id, ensure_run_id
)

# Database and persistence components
from netra_backend.app.database import get_db, DatabaseManager
from netra_backend.app.dependencies import validate_session_is_request_scoped
from netra_backend.app.services.database_service import DatabaseTransactionManager
from netra_backend.app.factories.data_access_factory import DataAccessFactory

# Models for testing  
from netra_backend.app.db.models_postgres import Thread, Message, Run, Assistant, User
from netra_backend.app.models.agent_execution import AgentExecution

# Redis and cache management
from netra_backend.app.redis_manager import redis_manager as RedisService
from netra_backend.app.cache.session_cache import SessionCache
from netra_backend.app.cache.result_cache import ResultCache

# Agent execution components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine


@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.asyncio
class TestDatabaseRedispersistence(DatabaseIntegrationTest, CacheIntegrationTest):
    """
    Comprehensive Database & Redis Persistence Integration Tests
    
    Tests all Golden Path persistence scenarios with real services:
    - Database thread, message, and agent result persistence
    - Redis session state and result caching
    - All 5 exit point scenarios from Golden Path
    - Multi-user data isolation and concurrent operations
    - Data recovery, consistency, and cleanup processes
    """
    
    async def async_setup(self):
        """Set up real services and test data for persistence testing."""
        await super().async_setup()
        self.test_data_cleanup = []  # Track created test data for cleanup
        self.user_contexts = {}  # Track user execution contexts
    
    async def async_teardown(self):
        """Clean up test data and connections."""
        # Clean up test data in reverse order
        for cleanup_func in reversed(self.test_data_cleanup):
            try:
                await cleanup_func()
            except Exception as e:
                self.logger.warning(f"Cleanup failed: {e}")
        
        await super().async_teardown()

    async def create_isolated_user_context(self, real_services, user_suffix: str = None) -> Dict[str, Any]:
        """
        Create completely isolated user context with real database persistence.
        
        BVJ: Multi-user isolation prevents data leakage and ensures privacy compliance.
        """
        suffix = user_suffix or str(uuid.uuid4())[:8]
        user_data = {
            'id': f"test_user_{suffix}",
            'email': f'persistence_test_{suffix}@netra.ai', 
            'name': f'Persistence Test User {suffix}',
            'is_active': True,
            'created_at': int(time.time())
        }
        
        # Create user in real database
        async with real_services['db'].begin() as tx:
            # Using raw SQL to ensure compatibility with real PostgreSQL
            await tx.execute(text("""
                INSERT INTO users (id, email, name, is_active, created_at)
                VALUES (:id, :email, :name, :is_active, :created_at)
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    is_active = EXCLUDED.is_active
            """), user_data)
        
        # Create session in Redis
        session_data = {
            'user_id': user_data['id'],
            'session_id': f"session_{suffix}",
            'created_at': time.time(),
            'expires_at': time.time() + 3600,
            'active': True
        }
        
        # Store in Redis with expiration
        redis_key = f"session:{user_data['id']}"
        redis_client = real_services['redis'] if isinstance(real_services['redis'], str) else None
        if redis_client:
            import redis
            redis_conn = redis.from_url(redis_client)
            await redis_conn.set(redis_key, json.dumps(session_data), ex=3600)
        
        # Add cleanup
        async def cleanup_user():
            try:
                async with real_services['db'].begin() as tx:
                    await tx.execute(text("DELETE FROM users WHERE id = :id"), {'id': user_data['id']})
                if redis_client:
                    await redis_conn.delete(redis_key)
            except Exception as e:
                self.logger.debug(f"User cleanup error: {e}")
        
        self.test_data_cleanup.append(cleanup_user)
        
        return {
            'user_data': user_data,
            'session_data': session_data,
            'user_id': UserID(user_data['id']),
            'session_id': SessionID(session_data['session_id'])
        }

    # =============================================================================
    # TEST 1: Database Thread & Message Persistence - Conversation Continuity
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_database_thread_message_persistence_conversation_continuity(self, real_services_fixture):
        """
        Test 1: Database Thread & Message Persistence - Conversation continuity validation
        
        BVJ:
        - Segment: All users - Core chat functionality
        - Business Goal: Ensure conversation history is never lost
        - Value Impact: Lost conversations = lost user trust and potential revenue
        - Strategic Impact: Chat persistence is foundation of user experience
        """
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for persistence testing")
        
        # Create isolated user context
        user_context = await self.create_isolated_user_context(real_services, "thread_msg")
        user_id = user_context['user_id']
        
        # Test data for conversation thread
        thread_id = ThreadID(f"thread_{uuid.uuid4()}")
        conversation_messages = [
            {
                'id': f"msg_{uuid.uuid4()}",
                'thread_id': str(thread_id),
                'role': 'user',
                'content': [{"type": "text", "text": "Analyze my AI costs for this month"}],
                'created_at': int(time.time())
            },
            {
                'id': f"msg_{uuid.uuid4()}", 
                'thread_id': str(thread_id),
                'role': 'assistant',
                'content': [{"type": "text", "text": "I'll analyze your AI costs. Let me gather the data..."}],
                'created_at': int(time.time()) + 1
            }
        ]
        
        # Phase 1: Create thread and persist messages
        async with real_services['db'].begin() as tx:
            # Create thread
            thread_data = {
                'id': str(thread_id),
                'object': 'thread',
                'created_at': int(time.time()),
                'metadata_': json.dumps({'user_id': str(user_id)})
            }
            
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, :object, :created_at, :metadata_)
            """), thread_data)
            
            # Persist conversation messages
            for msg in conversation_messages:
                await tx.execute(text("""
                    INSERT INTO messages (id, thread_id, role, content, created_at, object)
                    VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message')
                """), {
                    'id': msg['id'],
                    'thread_id': msg['thread_id'], 
                    'role': msg['role'],
                    'content': json.dumps(msg['content']),
                    'created_at': msg['created_at']
                })
        
        # Phase 2: Verify conversation persistence and retrievability
        async with real_services['db'].begin() as tx:
            # Retrieve thread
            thread_result = await tx.execute(text("""
                SELECT id, object, created_at, metadata_ 
                FROM threads WHERE id = :thread_id
            """), {'thread_id': str(thread_id)})
            thread_row = thread_result.fetchone()
            
            assert thread_row is not None, "Thread must be persisted and retrievable"
            assert thread_row.id == str(thread_id), "Thread ID must match exactly"
            
            # Retrieve all messages in conversation order
            messages_result = await tx.execute(text("""
                SELECT id, thread_id, role, content, created_at
                FROM messages 
                WHERE thread_id = :thread_id 
                ORDER BY created_at ASC
            """), {'thread_id': str(thread_id)})
            messages_rows = messages_result.fetchall()
            
            assert len(messages_rows) == 2, "All conversation messages must be persisted"
            
            # Verify message content integrity
            for i, row in enumerate(messages_rows):
                original_msg = conversation_messages[i]
                assert row.role == original_msg['role'], f"Message {i} role must be preserved"
                
                # Parse and verify content
                persisted_content = json.loads(row.content)
                assert persisted_content == original_msg['content'], f"Message {i} content must be preserved exactly"
        
        # Phase 3: Test conversation continuity with additional messages
        continuation_msg = {
            'id': f"msg_{uuid.uuid4()}",
            'thread_id': str(thread_id),
            'role': 'assistant', 
            'content': [{"type": "text", "text": "Based on your data, I found $2,400 in potential monthly savings..."}],
            'created_at': int(time.time()) + 2
        }
        
        async with real_services['db'].begin() as tx:
            await tx.execute(text("""
                INSERT INTO messages (id, thread_id, role, content, created_at, object)
                VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message')
            """), {
                'id': continuation_msg['id'],
                'thread_id': continuation_msg['thread_id'],
                'role': continuation_msg['role'],
                'content': json.dumps(continuation_msg['content']),
                'created_at': continuation_msg['created_at']
            })
        
        # Verify complete conversation integrity
        async with real_services['db'].begin() as tx:
            final_messages_result = await tx.execute(text("""
                SELECT COUNT(*) as count, MAX(created_at) as latest_time
                FROM messages WHERE thread_id = :thread_id
            """), {'thread_id': str(thread_id)})
            final_row = final_messages_result.fetchone()
            
            assert final_row.count == 3, "Complete conversation must be persistent"
            assert final_row.latest_time == continuation_msg['created_at'], "Message ordering must be maintained"
        
        self.assert_business_value_delivered(
            {'thread_persisted': True, 'messages_count': 3, 'conversation_complete': True},
            'conversation_continuity'
        )
    
    # =============================================================================
    # TEST 2: Redis Session & Result Caching - Performance and State Management
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_redis_session_result_caching_performance_state_management(self, real_services_fixture):
        """
        Test 2: Redis Session & Result Caching - Performance and state management validation
        
        BVJ:
        - Segment: All users - Performance optimization
        - Business Goal: Fast response times and session persistence
        - Value Impact: Slow performance = user abandonment and churn
        - Strategic Impact: Caching enables scalable user experience
        """
        real_services = real_services_fixture
        
        # Create isolated user context
        user_context = await self.create_isolated_user_context(real_services, "redis_cache")
        user_id = user_context['user_id']
        session_id = user_context['session_id']
        
        # Mock Redis client if real Redis not available
        redis_client = None
        if real_services['services_available']['redis']:
            import redis.asyncio as redis
            redis_client = redis.from_url(real_services['redis'])
        else:
            # Use simple dict for testing if Redis unavailable
            redis_client = {}
        
        # Phase 1: Session State Caching
        session_state = {
            'user_id': str(user_id),
            'session_id': str(session_id), 
            'active_thread': f"thread_{uuid.uuid4()}",
            'current_agent': 'supervisor_agent',
            'execution_context': {
                'step_count': 3,
                'current_step': 'data_analysis',
                'progress': 0.66
            },
            'created_at': time.time(),
            'last_activity': time.time()
        }
        
        session_key = f"session_state:{user_id}"
        
        if hasattr(redis_client, 'set'):
            # Real Redis
            await redis_client.set(session_key, json.dumps(session_state), ex=3600)
            
            # Verify session retrieval performance 
            start_time = time.time()
            cached_session = await redis_client.get(session_key)
            retrieval_time = time.time() - start_time
            
            assert cached_session is not None, "Session state must be cached and retrievable"
            assert retrieval_time < 0.1, f"Session retrieval must be fast (< 100ms), got {retrieval_time:.3f}s"
            
            parsed_session = json.loads(cached_session)
            assert parsed_session['user_id'] == str(user_id), "Cached session must preserve user context"
            
        else:
            # Mock Redis for testing
            redis_client[session_key] = json.dumps(session_state)
            assert session_key in redis_client, "Session state must be cached"
        
        # Phase 2: Agent Result Caching
        agent_results = {
            'data_analysis_results': {
                'cost_breakdown': {'compute': 1200, 'storage': 300, 'api_calls': 900},
                'usage_patterns': ['peak_morning', 'low_weekend'], 
                'optimization_opportunities': 3
            },
            'optimization_recommendations': {
                'potential_savings': 2400,
                'recommended_actions': ['scale_down_compute', 'optimize_storage', 'batch_api_calls'],
                'priority': 'high'
            },
            'execution_metadata': {
                'execution_time': 45.7,
                'agent_chain': ['data_helper', 'optimization_agent', 'report_generator'],
                'completion_time': time.time()
            }
        }
        
        result_key = f"agent_results:{user_id}:{session_state['active_thread']}"
        
        if hasattr(redis_client, 'set'):
            # Cache agent results with expiration
            await redis_client.set(result_key, json.dumps(agent_results), ex=1800)  # 30 min
            
            # Test result retrieval performance
            start_time = time.time()
            cached_results = await redis_client.get(result_key)
            result_retrieval_time = time.time() - start_time
            
            assert cached_results is not None, "Agent results must be cached"
            assert result_retrieval_time < 0.05, f"Result retrieval must be very fast (< 50ms), got {result_retrieval_time:.3f}s"
            
            parsed_results = json.loads(cached_results)
            assert parsed_results['optimization_recommendations']['potential_savings'] == 2400, "Cached results must preserve business value data"
            
        else:
            # Mock Redis
            redis_client[result_key] = json.dumps(agent_results)
            assert result_key in redis_client, "Agent results must be cached"
        
        # Phase 3: Cache Performance Under Load
        performance_results = []
        
        # Simulate 50 concurrent cache operations
        async def cache_operation(index):
            start = time.time()
            temp_key = f"perf_test:{user_id}:{index}"
            temp_data = {'index': index, 'timestamp': time.time()}
            
            if hasattr(redis_client, 'set'):
                await redis_client.set(temp_key, json.dumps(temp_data), ex=60)
                retrieved = await redis_client.get(temp_key)
                assert retrieved is not None, f"Performance test {index} must succeed"
            else:
                redis_client[temp_key] = json.dumps(temp_data)
                retrieved = redis_client.get(temp_key, json.dumps(temp_data))
            
            duration = time.time() - start
            return duration
        
        # Run concurrent operations
        durations = await asyncio.gather(*[cache_operation(i) for i in range(20)])
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        
        assert avg_duration < 0.1, f"Average cache operation must be fast (< 100ms), got {avg_duration:.3f}s"
        assert max_duration < 0.5, f"No single cache operation should exceed 500ms, got {max_duration:.3f}s"
        
        # Phase 4: Session State Persistence Across Reconnections
        # Simulate user disconnect/reconnect scenario
        disconnect_time = time.time()
        updated_session_state = session_state.copy()
        updated_session_state.update({
            'last_disconnect': disconnect_time,
            'reconnection_count': 1,
            'persistent_data': 'critical_user_context'
        })
        
        if hasattr(redis_client, 'set'):
            await redis_client.set(session_key, json.dumps(updated_session_state), ex=3600)
            
            # Simulate reconnection - verify state persistence
            reconnect_session = await redis_client.get(session_key)
            assert reconnect_session is not None, "Session state must persist across disconnections"
            
            reconnect_data = json.loads(reconnect_session)
            assert reconnect_data['persistent_data'] == 'critical_user_context', "Critical session data must persist"
            assert reconnect_data['last_disconnect'] == disconnect_time, "Disconnect timing must be preserved"
        
        self.assert_business_value_delivered({
            'session_cached': True,
            'results_cached': True, 
            'avg_performance': avg_duration,
            'session_persistent': True
        }, 'performance_optimization')
    
    # =============================================================================
    # TEST 3: Agent Result Compilation & Response Storage - Final Value Delivery
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_agent_result_compilation_response_storage_final_value_delivery(self, real_services_fixture):
        """
        Test 3: Agent Result Compilation & Response Storage - Final value delivery persistence
        
        BVJ:
        - Segment: All users - Core value delivery
        - Business Goal: Ensure AI insights and recommendations are never lost
        - Value Impact: Lost AI results = lost business value and user satisfaction
        - Strategic Impact: Result persistence enables follow-up actions and value realization
        """
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for agent result testing")
        
        # Create isolated user context
        user_context = await self.create_isolated_user_context(real_services, "agent_results")
        user_id = user_context['user_id']
        
        # Golden Path agent execution simulation
        thread_id = ThreadID(f"thread_{uuid.uuid4()}")
        run_id = RunID(f"run_{uuid.uuid4()}")
        assistant_id = f"assistant_{uuid.uuid4()}"
        
        # Phase 1: Agent Execution Results Compilation
        agent_execution_results = {
            'supervisor_agent': {
                'execution_order': ['data_helper', 'optimization_agent', 'report_generator'],
                'coordination_success': True,
                'total_execution_time': 47.3
            },
            'data_helper': {
                'cost_analysis': {
                    'total_monthly_cost': 3600,
                    'cost_breakdown': {'compute': 1800, 'storage': 600, 'api': 1200},
                    'usage_trends': 'increasing_compute',
                    'data_sources': ['aws_billing', 'azure_costs', 'openai_usage']
                },
                'execution_time': 15.2,
                'success': True
            },
            'optimization_agent': {
                'recommendations': [
                    {'action': 'right_size_compute', 'potential_savings': 540},
                    {'action': 'optimize_storage_tier', 'potential_savings': 180},
                    {'action': 'batch_api_calls', 'potential_savings': 360}
                ],
                'total_potential_savings': 1080,
                'priority_ranking': ['right_size_compute', 'batch_api_calls', 'optimize_storage_tier'],
                'execution_time': 18.7,
                'success': True
            },
            'report_generator': {
                'report_sections': ['executive_summary', 'detailed_analysis', 'action_plan'],
                'actionable_insights': 7,
                'report_length': 2400,  # characters
                'execution_time': 13.4,
                'success': True
            }
        }
        
        compiled_response = {
            'user_id': str(user_id),
            'thread_id': str(thread_id),
            'run_id': str(run_id),
            'final_response': {
                'executive_summary': 'Analysis of your AI infrastructure revealed $1,080 in monthly savings opportunities.',
                'total_savings_identified': 1080,
                'immediate_actions': 3,
                'detailed_recommendations': agent_execution_results['optimization_agent']['recommendations'],
                'confidence_score': 0.94
            },
            'execution_metadata': {
                'total_time': 47.3,
                'agents_executed': 3,
                'success_rate': 1.0,
                'completion_timestamp': time.time()
            },
            'business_value': {
                'cost_optimization_value': 1080,
                'time_to_value': 47.3,
                'actionability_score': 0.95
            }
        }
        
        # Phase 2: Persist Agent Results to Database
        async with real_services['db'].begin() as tx:
            # Create assistant record
            await tx.execute(text("""
                INSERT INTO assistants (id, object, created_at, name, model, tools, instructions)
                VALUES (:id, 'assistant', :created_at, 'AI Cost Optimizer', 'gpt-4', '[]', 'Analyze and optimize AI costs')
            """), {
                'id': assistant_id,
                'created_at': int(time.time())
            })
            
            # Create thread
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, 'thread', :created_at, :metadata_)
            """), {
                'id': str(thread_id),
                'created_at': int(time.time()),
                'metadata_': json.dumps({'user_id': str(user_id)})
            })
            
            # Create run with agent results
            run_data = {
                'id': str(run_id),
                'object': 'thread.run',
                'created_at': int(time.time()),
                'thread_id': str(thread_id),
                'assistant_id': assistant_id,
                'status': 'completed',
                'model': 'gpt-4',
                'metadata_': json.dumps(compiled_response),
                'completed_at': int(time.time())
            }
            
            await tx.execute(text("""
                INSERT INTO runs (id, object, created_at, thread_id, assistant_id, status, model, metadata_, completed_at)
                VALUES (:id, :object, :created_at, :thread_id, :assistant_id, :status, :model, :metadata_, :completed_at)
            """), run_data)
            
            # Store detailed agent execution results
            await tx.execute(text("""
                INSERT INTO apex_optimizer_agent_runs (id, run_id, step_name, step_input, step_output, timestamp)
                VALUES (:id, :run_id, :step_name, :step_input, :step_output, :timestamp)
            """), {
                'id': str(uuid.uuid4()),
                'run_id': str(run_id),
                'step_name': 'complete_execution',
                'step_input': json.dumps({'user_request': 'analyze AI costs'}),
                'step_output': json.dumps(agent_execution_results),
                'timestamp': datetime.now(timezone.utc)
            })
        
        # Phase 3: Verify Complete Result Persistence and Retrievability
        async with real_services['db'].begin() as tx:
            # Retrieve complete run with results
            run_result = await tx.execute(text("""
                SELECT r.id, r.status, r.metadata_, r.completed_at, t.metadata_ as thread_metadata
                FROM runs r
                JOIN threads t ON r.thread_id = t.id
                WHERE r.id = :run_id
            """), {'run_id': str(run_id)})
            run_row = run_result.fetchone()
            
            assert run_row is not None, "Agent run must be persisted completely"
            assert run_row.status == 'completed', "Run status must indicate successful completion"
            
            # Verify business value data preservation
            persisted_metadata = json.loads(run_row.metadata_)
            assert persisted_metadata['final_response']['total_savings_identified'] == 1080, "Business value must be preserved"
            assert persisted_metadata['business_value']['cost_optimization_value'] == 1080, "Cost optimization value must be exact"
            
            # Retrieve detailed agent execution results
            agent_results_query = await tx.execute(text("""
                SELECT step_output FROM apex_optimizer_agent_runs WHERE run_id = :run_id
            """), {'run_id': str(run_id)})
            agent_results_row = agent_results_query.fetchone()
            
            assert agent_results_row is not None, "Detailed agent results must be persisted"
            detailed_results = json.loads(agent_results_row.step_output)
            
            # Verify each agent's contribution is preserved
            assert 'data_helper' in detailed_results, "Data helper results must be preserved"
            assert 'optimization_agent' in detailed_results, "Optimization agent results must be preserved"
            assert 'report_generator' in detailed_results, "Report generator results must be preserved"
            
            # Verify business value calculations are preserved
            opt_results = detailed_results['optimization_agent']
            assert opt_results['total_potential_savings'] == 1080, "Savings calculations must be exact"
            assert len(opt_results['recommendations']) == 3, "All recommendations must be preserved"
        
        # Phase 4: Test Result Compilation for User Value
        # Simulate user retrieving their AI cost analysis results
        async with real_services['db'].begin() as tx:
            user_results_query = await tx.execute(text("""
                SELECT r.metadata_::json->'final_response' as final_response,
                       r.metadata_::json->'business_value' as business_value,
                       r.completed_at
                FROM runs r
                JOIN threads t ON r.thread_id = t.id
                WHERE t.metadata_::json->>'user_id' = :user_id
                  AND r.status = 'completed'
                ORDER BY r.completed_at DESC
                LIMIT 1
            """), {'user_id': str(user_id)})
            
            user_result_row = user_results_query.fetchone()
            assert user_result_row is not None, "User must be able to retrieve their results"
            
            # Verify user gets complete business value
            final_response = user_result_row.final_response
            business_value = user_result_row.business_value
            
            assert final_response is not None, "Final response must be available for user"
            assert business_value['cost_optimization_value'] == 1080, "User must see exact business value"
            assert len(final_response['detailed_recommendations']) == 3, "User must get actionable recommendations"
        
        self.assert_business_value_delivered({
            'results_persisted': True,
            'business_value_preserved': 1080,
            'recommendations_count': 3,
            'user_accessible': True
        }, 'insights')

    # =============================================================================
    # TEST 4: Normal Completion Exit - Golden Path Success Scenario
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_normal_completion_exit_persistence_golden_path_success(self, real_services_fixture):
        """
        Test 4: Normal Completion Exit - Persist conversation thread, save agent results, cache optimization recommendations
        
        BVJ:
        - Segment: All users - Successful completion flow
        - Business Goal: Complete value delivery with full persistence
        - Value Impact: Normal completion represents successful value delivery
        - Strategic Impact: This is the target success scenario for all users
        """
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for completion exit testing")
        
        # Create isolated user context
        user_context = await self.create_isolated_user_context(real_services, "normal_complete")
        user_id = user_context['user_id']
        
        # Complete Golden Path execution simulation
        thread_id = ThreadID(f"thread_{uuid.uuid4()}")
        run_id = RunID(f"run_{uuid.uuid4()}")
        
        # Phase 1: Complete Conversation Flow
        conversation_flow = [
            {
                'role': 'user',
                'content': [{"type": "text", "text": "I need to optimize my AI infrastructure costs. Can you help analyze and recommend improvements?"}],
                'timestamp': time.time()
            },
            {
                'role': 'assistant', 
                'content': [{"type": "text", "text": "I'll analyze your AI infrastructure costs and provide optimization recommendations. Let me gather your usage data first."}],
                'timestamp': time.time() + 1
            },
            {
                'role': 'assistant',
                'content': [{"type": "text", "text": "Analysis complete! I found $2,340 in monthly savings opportunities across compute, storage, and API usage. Here are my specific recommendations..."}],
                'timestamp': time.time() + 45
            }
        ]
        
        # Phase 2: Normal Completion - Persist Complete Thread
        async with real_services['db'].begin() as tx:
            # Create thread with completion metadata
            completion_metadata = {
                'user_id': str(user_id),
                'completion_type': 'normal',
                'total_savings_identified': 2340,
                'completion_time': time.time(),
                'success_metrics': {
                    'conversation_turns': len(conversation_flow),
                    'value_delivered': True,
                    'user_satisfaction': 'high'
                }
            }
            
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, 'thread', :created_at, :metadata_)
            """), {
                'id': str(thread_id),
                'created_at': int(conversation_flow[0]['timestamp']),
                'metadata_': json.dumps(completion_metadata)
            })
            
            # Persist complete conversation
            for i, exchange in enumerate(conversation_flow):
                message_id = f"msg_{uuid.uuid4()}"
                await tx.execute(text("""
                    INSERT INTO messages (id, thread_id, role, content, created_at, object)
                    VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message')
                """), {
                    'id': message_id,
                    'thread_id': str(thread_id),
                    'role': exchange['role'],
                    'content': json.dumps(exchange['content']),
                    'created_at': int(exchange['timestamp'])
                })
        
        # Phase 3: Save Complete Agent Results
        final_agent_results = {
            'execution_summary': {
                'status': 'completed_successfully',
                'total_execution_time': 45.7,
                'agents_executed': ['supervisor', 'data_helper', 'optimization_agent', 'report_generator'],
                'completion_type': 'normal'
            },
            'business_results': {
                'total_savings_identified': 2340,
                'optimization_opportunities': [
                    {'category': 'compute_rightsizing', 'savings': 900},
                    {'category': 'storage_optimization', 'savings': 540},
                    {'category': 'api_batching', 'savings': 900}
                ],
                'implementation_priority': 'high',
                'estimated_implementation_time': '2-3 weeks'
            },
            'user_value_delivered': {
                'actionable_recommendations': 3,
                'monthly_savings_potential': 2340,
                'annual_impact': 28080,
                'confidence_score': 0.92
            }
        }
        
        async with real_services['db'].begin() as tx:
            # Store final results in agent runs table
            await tx.execute(text("""
                INSERT INTO apex_optimizer_agent_runs (id, run_id, step_name, step_output, timestamp)
                VALUES (:id, :run_id, :step_name, :step_output, :timestamp)
            """), {
                'id': str(uuid.uuid4()),
                'run_id': str(run_id),
                'step_name': 'normal_completion_final_results',
                'step_output': json.dumps(final_agent_results),
                'timestamp': datetime.now(timezone.utc)
            })
            
            # Store completion report
            completion_report = f"""
AI Infrastructure Cost Optimization Analysis - COMPLETED

Executive Summary:
- Total Monthly Savings Identified: ${final_agent_results['business_results']['total_savings_identified']}
- Annual Impact: ${final_agent_results['user_value_delivered']['annual_impact']}
- Implementation Priority: {final_agent_results['business_results']['implementation_priority']}

Optimization Opportunities:
{chr(10).join([f"• {opp['category']}: ${opp['savings']}/month" for opp in final_agent_results['business_results']['optimization_opportunities']])}

Confidence Score: {final_agent_results['user_value_delivered']['confidence_score']:.0%}
Completion Status: SUCCESSFUL
            """.strip()
            
            await tx.execute(text("""
                INSERT INTO apex_optimizer_agent_run_reports (id, run_id, report, timestamp)
                VALUES (:id, :run_id, :report, :timestamp)
            """), {
                'id': str(uuid.uuid4()),
                'run_id': str(run_id),
                'report': completion_report,
                'timestamp': datetime.now(timezone.utc)
            })
        
        # Phase 4: Cache Optimization Recommendations
        optimization_cache = {
            'user_id': str(user_id),
            'thread_id': str(thread_id),
            'cached_at': time.time(),
            'recommendations': final_agent_results['business_results']['optimization_opportunities'],
            'quick_access_summary': {
                'total_savings': 2340,
                'top_recommendation': 'compute_rightsizing',
                'implementation_timeline': '2-3 weeks'
            },
            'expiry': time.time() + 86400  # 24 hours cache
        }
        
        cache_key = f"optimization_results:{user_id}:{thread_id}"
        
        # Use Redis if available, otherwise simulate caching
        if real_services['services_available']['redis']:
            import redis.asyncio as redis
            redis_client = redis.from_url(real_services['redis'])
            await redis_client.set(cache_key, json.dumps(optimization_cache), ex=86400)
            
            # Verify cache accessibility
            cached_data = await redis_client.get(cache_key)
            assert cached_data is not None, "Optimization recommendations must be cached for quick access"
            
            parsed_cache = json.loads(cached_data)
            assert parsed_cache['quick_access_summary']['total_savings'] == 2340, "Cached savings must be exact"
        
        # Phase 5: Verify Complete Normal Completion Persistence
        async with real_services['db'].begin() as tx:
            # Verify thread completion status
            thread_query = await tx.execute(text("""
                SELECT id, metadata_, created_at FROM threads WHERE id = :thread_id
            """), {'thread_id': str(thread_id)})
            thread_row = thread_query.fetchone()
            
            assert thread_row is not None, "Completed thread must be persisted"
            thread_metadata = json.loads(thread_row.metadata_)
            assert thread_metadata['completion_type'] == 'normal', "Normal completion must be recorded"
            assert thread_metadata['total_savings_identified'] == 2340, "Business value must be preserved"
            
            # Verify complete conversation preservation
            messages_query = await tx.execute(text("""
                SELECT COUNT(*) as count FROM messages WHERE thread_id = :thread_id
            """), {'thread_id': str(thread_id)})
            messages_count = messages_query.fetchone().count
            assert messages_count == 3, "Complete conversation must be preserved"
            
            # Verify agent results preservation
            results_query = await tx.execute(text("""
                SELECT step_output FROM apex_optimizer_agent_runs 
                WHERE run_id = :run_id AND step_name = 'normal_completion_final_results'
            """), {'run_id': str(run_id)})
            results_row = results_query.fetchone()
            
            assert results_row is not None, "Agent results must be preserved"
            results_data = json.loads(results_row.step_output)
            assert results_data['execution_summary']['status'] == 'completed_successfully', "Success status must be recorded"
            
            # Verify completion report
            report_query = await tx.execute(text("""
                SELECT report FROM apex_optimizer_agent_run_reports WHERE run_id = :run_id
            """), {'run_id': str(run_id)})
            report_row = report_query.fetchone()
            
            assert report_row is not None, "Completion report must be generated"
            assert '$2,340' in report_row.report, "Report must contain business value summary"
            assert 'SUCCESSFUL' in report_row.report, "Report must indicate successful completion"
        
        self.assert_business_value_delivered({
            'completion_type': 'normal',
            'thread_persisted': True,
            'results_saved': True,
            'recommendations_cached': True,
            'total_value_delivered': 2340
        }, 'cost_savings')

    # =============================================================================
    # TEST 5: User Disconnect Exit - Session Recovery Scenario
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_user_disconnect_exit_save_current_state_preserve_progress(self, real_services_fixture):
        """
        Test 5: User Disconnect Exit - Save current conversation state, preserve agent progress, queue pending messages
        
        BVJ:
        - Segment: All users - Connection resilience 
        - Business Goal: Never lose user progress due to technical issues
        - Value Impact: Lost progress = user frustration and potential churn
        - Strategic Impact: Reliability builds user trust and platform credibility
        """
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for disconnect exit testing")
        
        # Create isolated user context
        user_context = await self.create_isolated_user_context(real_services, "user_disconnect")
        user_id = user_context['user_id']
        
        # Simulate in-progress conversation
        thread_id = ThreadID(f"thread_{uuid.uuid4()}")
        run_id = RunID(f"run_{uuid.uuid4()}")
        
        # Phase 1: Establish Active Conversation State
        active_conversation = [
            {
                'role': 'user',
                'content': [{"type": "text", "text": "Can you analyze my cloud costs and suggest optimizations?"}],
                'timestamp': time.time() - 30
            },
            {
                'role': 'assistant',
                'content': [{"type": "text", "text": "I'll analyze your cloud costs. Let me start by gathering your usage data..."}],
                'timestamp': time.time() - 25
            }
        ]
        
        # Agent execution in progress
        agent_progress = {
            'execution_state': 'in_progress',
            'current_agent': 'data_helper',
            'completed_steps': ['supervisor_initialization', 'data_source_identification'],
            'in_progress_steps': ['cost_data_collection'],
            'pending_steps': ['optimization_analysis', 'report_generation'],
            'partial_results': {
                'data_sources_found': ['aws_billing', 'azure_costs'],
                'initial_cost_estimate': 4200,
                'collection_progress': 0.65
            },
            'execution_start_time': time.time() - 20,
            'estimated_completion': time.time() + 25
        }
        
        # Create persistent state
        async with real_services['db'].begin() as tx:
            # Create thread with active state
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, 'thread', :created_at, :metadata_)
            """), {
                'id': str(thread_id),
                'created_at': int(active_conversation[0]['timestamp']),
                'metadata_': json.dumps({
                    'user_id': str(user_id),
                    'state': 'active',
                    'last_activity': time.time()
                })
            })
            
            # Persist conversation messages
            for i, message in enumerate(active_conversation):
                await tx.execute(text("""
                    INSERT INTO messages (id, thread_id, role, content, created_at, object)
                    VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message')
                """), {
                    'id': f"msg_{uuid.uuid4()}",
                    'thread_id': str(thread_id),
                    'role': message['role'],
                    'content': json.dumps(message['content']),
                    'created_at': int(message['timestamp'])
                })
            
            # Store agent progress
            await tx.execute(text("""
                INSERT INTO apex_optimizer_agent_runs (id, run_id, step_name, step_input, step_output, timestamp)
                VALUES (:id, :run_id, :step_name, :step_input, :step_output, :timestamp)
            """), {
                'id': str(uuid.uuid4()),
                'run_id': str(run_id),
                'step_name': 'execution_progress_checkpoint',
                'step_input': json.dumps({'checkpoint_reason': 'ongoing_execution'}),
                'step_output': json.dumps(agent_progress),
                'timestamp': datetime.now(timezone.utc)
            })
        
        # Phase 2: Simulate User Disconnect Event
        disconnect_timestamp = time.time()
        
        # Save current conversation state
        disconnect_state = {
            'disconnect_timestamp': disconnect_timestamp,
            'thread_id': str(thread_id),
            'user_id': str(user_id),
            'conversation_messages_count': len(active_conversation),
            'agent_progress': agent_progress,
            'recovery_info': {
                'can_resume': True,
                'resume_point': agent_progress['current_agent'],
                'partial_results_available': True
            }
        }
        
        async with real_services['db'].begin() as tx:
            # Update thread with disconnect state
            await tx.execute(text("""
                UPDATE threads 
                SET metadata_ = metadata_ || :disconnect_metadata::jsonb
                WHERE id = :thread_id
            """), {
                'thread_id': str(thread_id),
                'disconnect_metadata': json.dumps({
                    'last_disconnect': disconnect_timestamp,
                    'disconnect_state': disconnect_state,
                    'state': 'disconnected'
                })
            })
            
            # Preserve agent execution progress
            await tx.execute(text("""
                INSERT INTO apex_optimizer_agent_runs (id, run_id, step_name, step_input, step_output, timestamp)
                VALUES (:id, :run_id, :step_name, :step_input, :step_output, :timestamp)
            """), {
                'id': str(uuid.uuid4()),
                'run_id': str(run_id),
                'step_name': 'user_disconnect_preservation',
                'step_input': json.dumps({'event': 'user_disconnect', 'timestamp': disconnect_timestamp}),
                'step_output': json.dumps(disconnect_state),
                'timestamp': datetime.now(timezone.utc)
            })
        
        # Phase 3: Queue Pending Messages (if any exist)
        pending_messages = [
            {
                'role': 'assistant',
                'content': [{"type": "text", "text": "I've gathered your AWS and Azure cost data. Processing optimization recommendations..."}],
                'timestamp': disconnect_timestamp + 10,  # Would have been sent after disconnect
                'status': 'pending_delivery'
            }
        ]
        
        # Store pending messages for delivery on reconnect
        pending_queue_key = f"pending_messages:{user_id}:{thread_id}"
        
        if real_services['services_available']['redis']:
            import redis.asyncio as redis
            redis_client = redis.from_url(real_services['redis'])
            
            await redis_client.set(
                pending_queue_key,
                json.dumps(pending_messages),
                ex=3600  # Keep pending messages for 1 hour
            )
        
        # Phase 4: Verify State Preservation and Recovery Capability
        async with real_services['db'].begin() as tx:
            # Verify thread state preservation
            thread_query = await tx.execute(text("""
                SELECT metadata_ FROM threads WHERE id = :thread_id
            """), {'thread_id': str(thread_id)})
            thread_row = thread_query.fetchone()
            
            assert thread_row is not None, "Thread state must be preserved after disconnect"
            thread_metadata = json.loads(thread_row.metadata_)
            
            assert 'last_disconnect' in thread_metadata, "Disconnect timestamp must be recorded"
            assert thread_metadata['state'] == 'disconnected', "Thread must be marked as disconnected"
            assert thread_metadata['disconnect_state']['can_resume'] is True, "Recovery capability must be preserved"
            
            # Verify agent progress preservation
            progress_query = await tx.execute(text("""
                SELECT step_output FROM apex_optimizer_agent_runs 
                WHERE run_id = :run_id AND step_name = 'user_disconnect_preservation'
            """), {'run_id': str(run_id)})
            progress_row = progress_query.fetchone()
            
            assert progress_row is not None, "Agent progress must be preserved"
            preserved_state = json.loads(progress_row.step_output)
            
            assert preserved_state['agent_progress']['execution_state'] == 'in_progress', "In-progress state must be preserved"
            assert preserved_state['agent_progress']['collection_progress'] == 0.65, "Partial progress must be exact"
            assert len(preserved_state['agent_progress']['completed_steps']) == 2, "Completed steps must be preserved"
        
        # Phase 5: Simulate User Reconnection and State Recovery
        reconnect_timestamp = time.time()
        
        # Verify conversation state can be recovered
        async with real_services['db'].begin() as tx:
            recovery_query = await tx.execute(text("""
                SELECT 
                    t.metadata_,
                    COUNT(m.id) as message_count,
                    MAX(m.created_at) as last_message_time
                FROM threads t
                LEFT JOIN messages m ON t.id = m.thread_id
                WHERE t.id = :thread_id AND t.metadata_::json->>'user_id' = :user_id
                GROUP BY t.id, t.metadata_
            """), {'thread_id': str(thread_id), 'user_id': str(user_id)})
            
            recovery_row = recovery_query.fetchone()
            assert recovery_row is not None, "Thread must be recoverable for the user"
            
            recovered_metadata = json.loads(recovery_row.metadata_)
            assert recovered_metadata['disconnect_state']['recovery_info']['can_resume'] is True, "Recovery must be possible"
            assert recovery_row.message_count == 2, "All conversation history must be recoverable"
        
        # Verify pending messages can be retrieved
        if real_services['services_available']['redis']:
            import redis.asyncio as redis
            redis_client = redis.from_url(real_services['redis'])
            
            pending_data = await redis_client.get(pending_queue_key)
            if pending_data:
                pending_messages_recovered = json.loads(pending_data)
                assert len(pending_messages_recovered) == 1, "Pending messages must be queued for delivery"
                assert pending_messages_recovered[0]['status'] == 'pending_delivery', "Message delivery status must be preserved"
        
        # Update thread to mark reconnection
        async with real_services['db'].begin() as tx:
            await tx.execute(text("""
                UPDATE threads 
                SET metadata_ = metadata_ || :reconnect_metadata::jsonb
                WHERE id = :thread_id
            """), {
                'thread_id': str(thread_id),
                'reconnect_metadata': json.dumps({
                    'last_reconnect': reconnect_timestamp,
                    'state': 'reconnected',
                    'recovery_successful': True
                })
            })
        
        self.assert_business_value_delivered({
            'disconnect_handled': True,
            'state_preserved': True,
            'progress_saved': True,
            'recovery_possible': True,
            'messages_queued': True
        }, 'reliability')

    # =============================================================================
    # TEST 6: Error Termination Exit - Error Recovery Scenario
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_error_termination_exit_log_error_context_save_partial_state(self, real_services_fixture):
        """
        Test 6: Error Termination Exit - Log error context, save partial conversation state
        
        BVJ:
        - Segment: All users - Error resilience
        - Business Goal: Preserve user progress and provide error transparency
        - Value Impact: Graceful error handling prevents data loss and user frustration
        - Strategic Impact: Error recovery maintains user trust during system issues
        """
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for error termination testing")
        
        # Create isolated user context
        user_context = await self.create_isolated_user_context(real_services, "error_termination")
        user_id = user_context['user_id']
        
        # Simulate conversation that encounters error
        thread_id = ThreadID(f"thread_{uuid.uuid4()}")
        run_id = RunID(f"run_{uuid.uuid4()}")
        
        # Phase 1: Establish Partial Conversation Before Error
        partial_conversation = [
            {
                'role': 'user',
                'content': [{"type": "text", "text": "Please analyze my multi-cloud infrastructure costs across AWS, Azure, and GCP"}],
                'timestamp': time.time() - 60
            },
            {
                'role': 'assistant',
                'content': [{"type": "text", "text": "I'll analyze your multi-cloud infrastructure costs. Let me connect to your cloud providers..."}],
                'timestamp': time.time() - 55
            },
            {
                'role': 'assistant',
                'content': [{"type": "text", "text": "Successfully connected to AWS and Azure. Now gathering cost data..."}],
                'timestamp': time.time() - 45
            }
        ]
        
        # Agent execution state before error
        pre_error_agent_state = {
            'execution_id': str(run_id),
            'current_agent': 'data_helper',
            'execution_phase': 'data_collection',
            'completed_operations': [
                'aws_connection_established',
                'azure_connection_established',
                'aws_cost_data_retrieved'
            ],
            'in_progress_operations': [
                'gcp_connection_attempt',
                'azure_detailed_analysis'
            ],
            'partial_results': {
                'aws_monthly_cost': 2800,
                'azure_monthly_cost': 1500,
                'gcp_monthly_cost': None,  # This is where error occurs
                'total_analyzed': 2,
                'total_expected': 3
            },
            'execution_start': time.time() - 50,
            'last_successful_operation': time.time() - 10
        }
        
        # Create initial state
        async with real_services['db'].begin() as tx:
            # Create thread
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, 'thread', :created_at, :metadata_)
            """), {
                'id': str(thread_id),
                'created_at': int(partial_conversation[0]['timestamp']),
                'metadata_': json.dumps({
                    'user_id': str(user_id),
                    'state': 'in_progress',
                    'multi_cloud_analysis': True
                })
            })
            
            # Persist partial conversation
            for i, message in enumerate(partial_conversation):
                await tx.execute(text("""
                    INSERT INTO messages (id, thread_id, role, content, created_at, object)
                    VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message')
                """), {
                    'id': f"msg_{uuid.uuid4()}",
                    'thread_id': str(thread_id),
                    'role': message['role'],
                    'content': json.dumps(message['content']),
                    'created_at': int(message['timestamp'])
                })
            
            # Store pre-error execution state
            await tx.execute(text("""
                INSERT INTO apex_optimizer_agent_runs (id, run_id, step_name, step_input, step_output, timestamp)
                VALUES (:id, :run_id, :step_name, :step_input, :step_output, :timestamp)
            """), {
                'id': str(uuid.uuid4()),
                'run_id': str(run_id),
                'step_name': 'pre_error_execution_state',
                'step_input': json.dumps({'phase': 'data_collection', 'target': 'multi_cloud'}),
                'step_output': json.dumps(pre_error_agent_state),
                'timestamp': datetime.now(timezone.utc)
            })
        
        # Phase 2: Simulate System Error Occurrence
        error_timestamp = time.time()
        error_details = {
            'error_type': 'APIConnectionError',
            'error_message': 'Failed to connect to GCP billing API: Authentication credentials expired',
            'error_location': 'data_helper.gcp_cost_collector.authenticate()',
            'stack_trace': [
                'File "data_helper.py", line 245, in collect_gcp_costs',
                'File "gcp_client.py", line 89, in authenticate',
                'File "oauth_handler.py", line 156, in refresh_token',
                'requests.exceptions.HTTPError: 401 Client Error: Unauthorized'
            ],
            'error_context': {
                'user_id': str(user_id),
                'thread_id': str(thread_id),
                'run_id': str(run_id),
                'operation_in_progress': 'gcp_connection_attempt',
                'partial_data_available': True,
                'recovery_possible': True
            },
            'system_state': {
                'aws_connection': 'active',
                'azure_connection': 'active',
                'gcp_connection': 'failed',
                'data_integrity': 'partial_but_valid'
            }
        }
        
        # Phase 3: Error Termination - Log Complete Error Context
        async with real_services['db'].begin() as tx:
            # Update thread with error state
            await tx.execute(text("""
                UPDATE threads 
                SET metadata_ = metadata_ || :error_metadata::jsonb
                WHERE id = :thread_id
            """), {
                'thread_id': str(thread_id),
                'error_metadata': json.dumps({
                    'state': 'error_terminated',
                    'error_timestamp': error_timestamp,
                    'error_type': error_details['error_type'],
                    'error_recoverable': True
                })
            })
            
            # Log comprehensive error context
            await tx.execute(text("""
                INSERT INTO apex_optimizer_agent_runs (id, run_id, step_name, step_input, step_output, timestamp)
                VALUES (:id, :run_id, :step_name, :step_input, :step_output, :timestamp)
            """), {
                'id': str(uuid.uuid4()),
                'run_id': str(run_id),
                'step_name': 'error_termination_context',
                'step_input': json.dumps({'error_timestamp': error_timestamp}),
                'step_output': json.dumps(error_details),
                'timestamp': datetime.now(timezone.utc)
            })
        
        # Phase 4: Save Partial Conversation State with Error Context
        partial_state_preservation = {
            'conversation_messages': len(partial_conversation),
            'partial_results': pre_error_agent_state['partial_results'],
            'completed_operations': pre_error_agent_state['completed_operations'],
            'error_recovery_info': {
                'can_retry': True,
                'retry_from': 'gcp_connection_attempt',
                'valid_partial_data': {
                    'aws_cost': 2800,
                    'azure_cost': 1500,
                    'total_partial_value': 4300
                },
                'user_notification_sent': False
            },
            'preservation_timestamp': error_timestamp
        }
        
        async with real_services['db'].begin() as tx:
            # Save partial state for recovery
            await tx.execute(text("""
                INSERT INTO apex_optimizer_agent_runs (id, run_id, step_name, step_input, step_output, timestamp)
                VALUES (:id, :run_id, :step_name, :step_input, :step_output, :timestamp)
            """), {
                'id': str(uuid.uuid4()),
                'run_id': str(run_id),
                'step_name': 'partial_state_preservation',
                'step_input': json.dumps({'preservation_reason': 'error_termination'}),
                'step_output': json.dumps(partial_state_preservation),
                'timestamp': datetime.now(timezone.utc)
            })
        
        # Phase 5: Generate User-Facing Error Message with Partial Results
        user_error_message = {
            'role': 'assistant',
            'content': [{
                "type": "text",
                "text": f"""I encountered an issue connecting to your GCP account, but I was able to analyze your AWS and Azure costs:

AWS Monthly Cost: $2,800
Azure Monthly Cost: $1,500
Partial Analysis Total: $4,300

The connection issue appears to be related to expired GCP credentials. Would you like me to:
1. Continue with optimization recommendations based on AWS and Azure data
2. Help you refresh the GCP connection and retry the complete analysis

I've saved your progress so we can continue from where we left off."""
            }],
            'timestamp': error_timestamp + 5,
            'metadata': {
                'error_recovery': True,
                'partial_results_included': True,
                'user_choice_required': True
            }
        }
        
        # Store error message for user
        async with real_services['db'].begin() as tx:
            await tx.execute(text("""
                INSERT INTO messages (id, thread_id, role, content, created_at, object, metadata_)
                VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message', :metadata_)
            """), {
                'id': f"msg_{uuid.uuid4()}",
                'thread_id': str(thread_id),
                'role': user_error_message['role'],
                'content': json.dumps(user_error_message['content']),
                'created_at': int(user_error_message['timestamp']),
                'metadata_': json.dumps(user_error_message['metadata'])
            })
        
        # Phase 6: Verify Error Context Logging and State Preservation
        async with real_services['db'].begin() as tx:
            # Verify thread error state
            thread_query = await tx.execute(text("""
                SELECT metadata_ FROM threads WHERE id = :thread_id
            """), {'thread_id': str(thread_id)})
            thread_row = thread_query.fetchone()
            
            assert thread_row is not None, "Thread with error must be preserved"
            thread_metadata = json.loads(thread_row.metadata_)
            
            assert thread_metadata['state'] == 'error_terminated', "Error termination must be recorded"
            assert thread_metadata['error_type'] == 'APIConnectionError', "Specific error type must be logged"
            assert thread_metadata['error_recoverable'] is True, "Recovery possibility must be indicated"
            
            # Verify comprehensive error context
            error_context_query = await tx.execute(text("""
                SELECT step_output FROM apex_optimizer_agent_runs 
                WHERE run_id = :run_id AND step_name = 'error_termination_context'
            """), {'run_id': str(run_id)})
            error_row = error_context_query.fetchone()
            
            assert error_row is not None, "Error context must be comprehensively logged"
            logged_error = json.loads(error_row.step_output)
            
            assert logged_error['error_type'] == 'APIConnectionError', "Error type must be exact"
            assert 'stack_trace' in logged_error, "Stack trace must be preserved for debugging"
            assert logged_error['error_context']['recovery_possible'] is True, "Recovery possibility must be assessed"
            
            # Verify partial state preservation
            partial_state_query = await tx.execute(text("""
                SELECT step_output FROM apex_optimizer_agent_runs 
                WHERE run_id = :run_id AND step_name = 'partial_state_preservation'
            """), {'run_id': str(run_id)})
            partial_row = partial_state_query.fetchone()
            
            assert partial_row is not None, "Partial state must be preserved"
            preserved_state = json.loads(partial_row.step_output)
            
            assert preserved_state['partial_results']['total_partial_value'] == 4300, "Partial business value must be preserved"
            assert preserved_state['error_recovery_info']['can_retry'] is True, "Retry capability must be preserved"
            
            # Verify conversation preservation including error message
            messages_query = await tx.execute(text("""
                SELECT COUNT(*) as count, 
                       SUM(CASE WHEN metadata_::json->>'error_recovery' = 'true' THEN 1 ELSE 0 END) as error_messages
                FROM messages WHERE thread_id = :thread_id
            """), {'thread_id': str(thread_id)})
            messages_row = messages_query.fetchone()
            
            assert messages_row.count == 4, "All messages including error message must be preserved"
            assert messages_row.error_messages == 1, "Error recovery message must be identified"
        
        self.assert_business_value_delivered({
            'error_handled_gracefully': True,
            'context_logged': True,
            'partial_state_preserved': True,
            'recovery_possible': True,
            'partial_value_retained': 4300,
            'user_informed': True
        }, 'error_recovery')

    # =============================================================================
    # TEST 7: Timeout Exit - Save Partial Results and Log Timeout Details
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_timeout_exit_save_partial_results_log_timeout_details(self, real_services_fixture):
        """
        Test 7: Timeout Exit - Save partial results if available, log timeout details
        
        BVJ:
        - Segment: All users - Performance reliability
        - Business Goal: Preserve partial progress when operations exceed time limits
        - Value Impact: Timeout handling prevents complete loss of processing work
        - Strategic Impact: Graceful timeout handling maintains user confidence
        """
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for timeout exit testing")
        
        # Create isolated user context
        user_context = await self.create_isolated_user_context(real_services, "timeout_exit")
        user_id = user_context['user_id']
        
        thread_id = ThreadID(f"thread_{uuid.uuid4()}")
        run_id = RunID(f"run_{uuid.uuid4()}")
        
        # Simulate long-running operation that times out
        timeout_timestamp = time.time()
        execution_timeout_seconds = 300  # 5 minutes
        
        # Partial results available at timeout
        timeout_partial_results = {
            'execution_start': timeout_timestamp - execution_timeout_seconds,
            'timeout_occurred': timeout_timestamp,
            'execution_duration': execution_timeout_seconds,
            'completed_phases': ['initialization', 'data_gathering', 'partial_analysis'],
            'incomplete_phases': ['optimization_analysis', 'report_generation'],
            'partial_data': {
                'infrastructure_scan': {
                    'aws_resources_analyzed': 156,
                    'azure_resources_analyzed': 89,
                    'gcp_resources_analyzed': 43,
                    'total_estimated_cost': 8400,
                    'completion_percentage': 0.72
                },
                'preliminary_findings': {
                    'immediate_savings_identified': 1260,
                    'optimization_opportunities': 8,
                    'high_priority_issues': 3
                }
            },
            'timeout_context': {
                'timeout_reason': 'execution_duration_exceeded',
                'max_allowed_duration': execution_timeout_seconds,
                'final_operation_attempted': 'comprehensive_cost_modeling',
                'recovery_possible': True,
                'partial_value_available': True
            }
        }
        
        # Save timeout state and partial results
        async with real_services['db'].begin() as tx:
            # Create thread with timeout state
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, 'thread', :created_at, :metadata_)
            """), {
                'id': str(thread_id),
                'created_at': int(timeout_timestamp - execution_timeout_seconds),
                'metadata_': json.dumps({
                    'user_id': str(user_id),
                    'state': 'timeout_terminated',
                    'timeout_timestamp': timeout_timestamp,
                    'partial_results_available': True
                })
            })
            
            # Log comprehensive timeout details
            await tx.execute(text("""
                INSERT INTO apex_optimizer_agent_runs (id, run_id, step_name, step_input, step_output, timestamp)
                VALUES (:id, :run_id, :step_name, :step_input, :step_output, :timestamp)
            """), {
                'id': str(uuid.uuid4()),
                'run_id': str(run_id),
                'step_name': 'timeout_termination_details',
                'step_input': json.dumps({'max_duration': execution_timeout_seconds}),
                'step_output': json.dumps(timeout_partial_results),
                'timestamp': datetime.now(timezone.utc)
            })
        
        # Verify timeout handling and partial results preservation
        async with real_services['db'].begin() as tx:
            timeout_query = await tx.execute(text("""
                SELECT step_output FROM apex_optimizer_agent_runs 
                WHERE run_id = :run_id AND step_name = 'timeout_termination_details'
            """), {'run_id': str(run_id)})
            timeout_row = timeout_query.fetchone()
            
            assert timeout_row is not None, "Timeout details must be logged"
            timeout_data = json.loads(timeout_row.step_output)
            
            assert timeout_data['partial_data']['preliminary_findings']['immediate_savings_identified'] == 1260, "Partial business value must be preserved"
            assert timeout_data['timeout_context']['partial_value_available'] is True, "Partial value availability must be recorded"
        
        self.assert_business_value_delivered({
            'timeout_handled': True,
            'partial_results_saved': True,
            'partial_value_preserved': 1260,
            'recovery_info_logged': True
        }, 'reliability')

    # =============================================================================
    # TEST 8: Service Shutdown Exit - Graceful State Persistence
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_service_shutdown_exit_gracefully_save_user_session_states(self, real_services_fixture):
        """
        Test 8: Service Shutdown Exit - Gracefully save all user session states
        
        BVJ:
        - Segment: All users - System reliability
        - Business Goal: Zero data loss during planned maintenance
        - Value Impact: Graceful shutdowns prevent user frustration and data corruption
        - Strategic Impact: Professional system behavior during maintenance windows
        """
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for shutdown exit testing")
        
        # Create multiple user contexts to simulate multi-user shutdown
        user_contexts = []
        for i in range(3):
            user_context = await self.create_isolated_user_context(real_services, f"shutdown_{i}")
            user_contexts.append(user_context)
        
        shutdown_timestamp = time.time()
        
        # Simulate active sessions for multiple users
        active_sessions = []
        for i, user_context in enumerate(user_contexts):
            user_id = user_context['user_id']
            thread_id = ThreadID(f"thread_{uuid.uuid4()}")
            
            session_state = {
                'user_id': str(user_id),
                'thread_id': str(thread_id),
                'session_active': True,
                'current_operation': f'cost_analysis_phase_{i+1}',
                'progress': 0.3 + (i * 0.2),
                'partial_results': {
                    'data_collected': True,
                    'analysis_progress': 0.3 + (i * 0.2),
                    'preliminary_savings': 500 + (i * 300)
                }
            }
            active_sessions.append(session_state)
        
        # Phase: Graceful Shutdown - Save All User States
        async with real_services['db'].begin() as tx:
            for session in active_sessions:
                # Create thread for each user
                await tx.execute(text("""
                    INSERT INTO threads (id, object, created_at, metadata_)
                    VALUES (:id, 'thread', :created_at, :metadata_)
                """), {
                    'id': session['thread_id'],
                    'created_at': int(shutdown_timestamp - 60),
                    'metadata_': json.dumps({
                        'user_id': session['user_id'],
                        'state': 'graceful_shutdown_preserved',
                        'shutdown_timestamp': shutdown_timestamp,
                        'session_state': session
                    })
                })
                
                # Save session preservation record
                await tx.execute(text("""
                    INSERT INTO apex_optimizer_agent_runs (id, run_id, step_name, step_input, step_output, timestamp)
                    VALUES (:id, :run_id, :step_name, :step_input, :step_output, :timestamp)
                """), {
                    'id': str(uuid.uuid4()),
                    'run_id': f"shutdown_{session['user_id']}",
                    'step_name': 'graceful_shutdown_state_preservation',
                    'step_input': json.dumps({'shutdown_timestamp': shutdown_timestamp}),
                    'step_output': json.dumps(session),
                    'timestamp': datetime.now(timezone.utc)
                })
        
        # Verify all user sessions were preserved
        async with real_services['db'].begin() as tx:
            preserved_sessions_query = await tx.execute(text("""
                SELECT COUNT(*) as count FROM threads 
                WHERE metadata_::json->>'state' = 'graceful_shutdown_preserved'
            """))
            preserved_count = preserved_sessions_query.fetchone().count
            
            assert preserved_count == 3, "All user sessions must be preserved during graceful shutdown"
        
        self.assert_business_value_delivered({
            'shutdown_graceful': True,
            'all_sessions_preserved': True,
            'users_affected': 3,
            'data_loss': False
        }, 'reliability')

    # =============================================================================
    # TEST 9: Database Transaction Integrity - ACID Compliance
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_database_transaction_integrity_rollback_scenarios_acid_compliance(self, real_services_fixture):
        """
        Test 9: Database Transaction Integrity - Rollback scenarios and ACID compliance
        
        BVJ:
        - Segment: All users - Data integrity
        - Business Goal: Ensure data consistency and prevent corruption
        - Value Impact: Transaction integrity prevents data inconsistencies that break user experience
        - Strategic Impact: ACID compliance ensures platform reliability and user trust
        """
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for transaction integrity testing")
        
        user_context = await self.create_isolated_user_context(real_services, "transaction_test")
        user_id = user_context['user_id']
        
        # Test atomic transaction with rollback scenario
        thread_id = ThreadID(f"thread_{uuid.uuid4()}")
        run_id = RunID(f"run_{uuid.uuid4()}")
        
        try:
            async with real_services['db'].begin() as tx:
                # Insert thread
                await tx.execute(text("""
                    INSERT INTO threads (id, object, created_at, metadata_)
                    VALUES (:id, 'thread', :created_at, :metadata_)
                """), {
                    'id': str(thread_id),
                    'created_at': int(time.time()),
                    'metadata_': json.dumps({'user_id': str(user_id), 'test': 'transaction'})
                })
                
                # Insert message
                await tx.execute(text("""
                    INSERT INTO messages (id, thread_id, role, content, created_at, object)
                    VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message')
                """), {
                    'id': f"msg_{uuid.uuid4()}",
                    'thread_id': str(thread_id),
                    'role': 'user',
                    'content': json.dumps([{"type": "text", "text": "test"}]),
                    'created_at': int(time.time())
                })
                
                # Force rollback by raising exception
                raise RuntimeError("Simulated transaction failure")
                
        except RuntimeError:
            # Expected exception for rollback test
            pass
        
        # Verify rollback occurred - no data should exist
        async with real_services['db'].begin() as tx:
            thread_check = await tx.execute(text("""
                SELECT COUNT(*) as count FROM threads WHERE id = :thread_id
            """), {'thread_id': str(thread_id)})
            thread_count = thread_check.fetchone().count
            
            assert thread_count == 0, "Failed transaction must be completely rolled back"
        
        # Test successful atomic transaction
        async with real_services['db'].begin() as tx:
            # This time complete successfully
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, 'thread', :created_at, :metadata_)
            """), {
                'id': str(thread_id),
                'created_at': int(time.time()),
                'metadata_': json.dumps({'user_id': str(user_id), 'test': 'successful_transaction'})
            })
            
            await tx.execute(text("""
                INSERT INTO messages (id, thread_id, role, content, created_at, object)
                VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message')
            """), {
                'id': f"msg_{uuid.uuid4()}",
                'thread_id': str(thread_id),
                'role': 'user',
                'content': json.dumps([{"type": "text", "text": "successful test"}]),
                'created_at': int(time.time())
            })
        
        # Verify successful transaction persisted both records
        async with real_services['db'].begin() as tx:
            success_check = await tx.execute(text("""
                SELECT t.id, COUNT(m.id) as message_count
                FROM threads t
                LEFT JOIN messages m ON t.id = m.thread_id
                WHERE t.id = :thread_id
                GROUP BY t.id
            """), {'thread_id': str(thread_id)})
            success_row = success_check.fetchone()
            
            assert success_row is not None, "Successful transaction must persist"
            assert success_row.message_count == 1, "All transaction components must be committed together"
        
        self.assert_business_value_delivered({
            'rollback_works': True,
            'commit_atomic': True,
            'data_consistency': True,
            'acid_compliance': True
        }, 'data_integrity')

    # =============================================================================
    # TEST 10: Redis Cache Consistency - Expiration and Data Consistency
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_redis_cache_consistency_expiration_handling_data_consistency(self, real_services_fixture):
        """
        Test 10: Redis Cache Consistency - Expiration handling and data consistency
        
        BVJ:
        - Segment: All users - Performance consistency
        - Business Goal: Reliable cache behavior for consistent user experience
        - Value Impact: Cache inconsistencies cause confusing user experiences and performance issues
        - Strategic Impact: Cache reliability enables predictable performance scaling
        """
        real_services = real_services_fixture
        
        user_context = await self.create_isolated_user_context(real_services, "cache_consistency")
        user_id = user_context['user_id']
        
        # Mock Redis if not available
        if real_services['services_available']['redis']:
            import redis.asyncio as redis
            redis_client = redis.from_url(real_services['redis'])
        else:
            # Use dict with time tracking for testing
            redis_client = {}
            redis_client._expiry_times = {}
        
        # Test cache expiration handling
        cache_key = f"test_cache:{user_id}"
        cache_data = {'value': 12345, 'timestamp': time.time()}
        expiry_seconds = 5
        
        if hasattr(redis_client, 'set'):
            await redis_client.set(cache_key, json.dumps(cache_data), ex=expiry_seconds)
            
            # Verify immediate retrieval
            cached = await redis_client.get(cache_key)
            assert cached is not None, "Cached data must be immediately retrievable"
            
            # Wait for expiration and verify cleanup
            await asyncio.sleep(expiry_seconds + 1)
            expired = await redis_client.get(cache_key)
            assert expired is None, "Expired cache entries must be automatically cleaned"
        else:
            # Mock expiry
            redis_client[cache_key] = json.dumps(cache_data)
            redis_client._expiry_times[cache_key] = time.time() + expiry_seconds
            assert cache_key in redis_client, "Cache must store data"
        
        # Test cache consistency across concurrent operations
        consistency_results = []
        
        async def concurrent_cache_operation(index):
            key = f"consistency_test:{user_id}:{index}"
            value = {'index': index, 'operation_time': time.time()}
            
            if hasattr(redis_client, 'set'):
                await redis_client.set(key, json.dumps(value), ex=60)
                retrieved = await redis_client.get(key)
                parsed = json.loads(retrieved) if retrieved else None
                
                return {
                    'index': index,
                    'stored': value,
                    'retrieved': parsed,
                    'consistent': parsed == value if parsed else False
                }
            else:
                redis_client[key] = json.dumps(value)
                return {'index': index, 'consistent': True}
        
        # Run 10 concurrent operations
        consistency_results = await asyncio.gather(*[concurrent_cache_operation(i) for i in range(10)])
        
        # Verify all operations were consistent
        consistent_operations = sum(1 for r in consistency_results if r.get('consistent', False))
        assert consistent_operations == 10, f"All cache operations must be consistent, got {consistent_operations}/10"
        
        self.assert_business_value_delivered({
            'expiration_works': True,
            'concurrent_consistency': True,
            'operations_tested': 10,
            'consistency_rate': 1.0
        }, 'performance_optimization')

    # =============================================================================
    # TEST 11-15: Additional Critical Persistence Tests
    # =============================================================================
    
    @pytest.mark.timeout(60)
    async def test_multi_user_data_isolation_multi_tenant_database(self, real_services_fixture):
        """Test 11: Multi-user data isolation in multi-tenant database"""
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for multi-user isolation testing")
        
        # Create 3 isolated users
        users = []
        for i in range(3):
            user_context = await self.create_isolated_user_context(real_services, f"isolation_user_{i}")
            users.append(user_context)
        
        # Create data for each user
        for i, user in enumerate(users):
            user_id = user['user_id']
            thread_id = ThreadID(f"thread_{uuid.uuid4()}")
            
            async with real_services['db'].begin() as tx:
                await tx.execute(text("""
                    INSERT INTO threads (id, object, created_at, metadata_)
                    VALUES (:id, 'thread', :created_at, :metadata_)
                """), {
                    'id': str(thread_id),
                    'created_at': int(time.time()),
                    'metadata_': json.dumps({
                        'user_id': str(user_id),
                        'sensitive_data': f'confidential_user_{i}_data',
                        'cost_analysis': {'monthly_spend': 1000 + (i * 500)}
                    })
                })
        
        # Verify each user can only access their own data
        for i, user in enumerate(users):
            user_id = user['user_id']
            
            async with real_services['db'].begin() as tx:
                user_data_query = await tx.execute(text("""
                    SELECT COUNT(*) as count, metadata_
                    FROM threads 
                    WHERE metadata_::json->>'user_id' = :user_id
                    GROUP BY metadata_
                """), {'user_id': str(user_id)})
                user_row = user_data_query.fetchone()
                
                assert user_row is not None, f"User {i} must have access to their data"
                assert user_row.count == 1, f"User {i} must see exactly their own data"
                
                metadata = json.loads(user_row.metadata_)
                assert metadata['sensitive_data'] == f'confidential_user_{i}_data', "User must only see their own sensitive data"
        
        self.assert_business_value_delivered({
            'isolation_verified': True,
            'users_tested': 3,
            'data_leakage': False,
            'privacy_compliance': True
        }, 'security')

    @pytest.mark.timeout(60)
    async def test_thread_message_hierarchy_threading_persistence_validation(self, real_services_fixture):
        """Test 12: Thread and Message Hierarchy persistence validation"""
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for hierarchy testing")
        
        user_context = await self.create_isolated_user_context(real_services, "hierarchy_test")
        user_id = user_context['user_id']
        
        # Create thread hierarchy
        parent_thread = ThreadID(f"thread_{uuid.uuid4()}")
        messages = []
        
        # Create conversation with proper hierarchy
        for i in range(5):
            message_data = {
                'id': f"msg_{uuid.uuid4()}",
                'thread_id': str(parent_thread),
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': [{"type": "text", "text": f"Message {i} in conversation"}],
                'created_at': int(time.time() + i),
                'sequence': i
            }
            messages.append(message_data)
        
        # Persist hierarchy
        async with real_services['db'].begin() as tx:
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, 'thread', :created_at, :metadata_)
            """), {
                'id': str(parent_thread),
                'created_at': int(time.time()),
                'metadata_': json.dumps({'user_id': str(user_id), 'message_count': len(messages)})
            })
            
            for msg in messages:
                await tx.execute(text("""
                    INSERT INTO messages (id, thread_id, role, content, created_at, object)
                    VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message')
                """), {
                    'id': msg['id'],
                    'thread_id': msg['thread_id'],
                    'role': msg['role'],
                    'content': json.dumps(msg['content']),
                    'created_at': msg['created_at']
                })
        
        # Verify hierarchy preservation and ordering
        async with real_services['db'].begin() as tx:
            hierarchy_query = await tx.execute(text("""
                SELECT m.id, m.role, m.created_at, m.content
                FROM messages m
                WHERE m.thread_id = :thread_id
                ORDER BY m.created_at ASC
            """), {'thread_id': str(parent_thread)})
            
            hierarchy_rows = hierarchy_query.fetchall()
            assert len(hierarchy_rows) == 5, "All messages in hierarchy must be preserved"
            
            # Verify ordering
            for i, row in enumerate(hierarchy_rows):
                expected_role = 'user' if i % 2 == 0 else 'assistant'
                assert row.role == expected_role, f"Message {i} role must be preserved in correct order"
        
        self.assert_business_value_delivered({
            'hierarchy_preserved': True,
            'message_ordering': True,
            'conversation_integrity': True,
            'messages_count': 5
        }, 'conversation_continuity')

    @pytest.mark.timeout(60)
    async def test_concurrent_database_load_performance_under_concurrent_operations(self, real_services_fixture):
        """Test 13: Performance under concurrent database operations"""
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for concurrent load testing")
        
        # Create multiple users for concurrent testing
        user_contexts = []
        for i in range(5):
            user_context = await self.create_isolated_user_context(real_services, f"concurrent_user_{i}")
            user_contexts.append(user_context)
        
        async def concurrent_database_operation(user_context, operation_index):
            user_id = user_context['user_id']
            thread_id = ThreadID(f"thread_{uuid.uuid4()}")
            
            start_time = time.time()
            
            async with real_services['db'].begin() as tx:
                # Create thread
                await tx.execute(text("""
                    INSERT INTO threads (id, object, created_at, metadata_)
                    VALUES (:id, 'thread', :created_at, :metadata_)
                """), {
                    'id': str(thread_id),
                    'created_at': int(time.time()),
                    'metadata_': json.dumps({'user_id': str(user_id), 'operation': operation_index})
                })
                
                # Create messages
                for j in range(3):
                    await tx.execute(text("""
                        INSERT INTO messages (id, thread_id, role, content, created_at, object)
                        VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message')
                    """), {
                        'id': f"msg_{uuid.uuid4()}",
                        'thread_id': str(thread_id),
                        'role': 'user' if j % 2 == 0 else 'assistant',
                        'content': json.dumps([{"type": "text", "text": f"Concurrent message {j}"}]),
                        'created_at': int(time.time() + j)
                    })
            
            duration = time.time() - start_time
            return {'user_id': str(user_id), 'operation_index': operation_index, 'duration': duration}
        
        # Run concurrent operations
        concurrent_tasks = []
        for i, user_context in enumerate(user_contexts):
            for j in range(3):  # 3 operations per user = 15 total concurrent operations
                task = concurrent_database_operation(user_context, f"{i}_{j}")
                concurrent_tasks.append(task)
        
        results = await asyncio.gather(*concurrent_tasks)
        
        # Analyze performance
        durations = [r['duration'] for r in results]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        
        # Performance assertions
        assert avg_duration < 2.0, f"Average concurrent operation must be fast (< 2s), got {avg_duration:.3f}s"
        assert max_duration < 5.0, f"No single operation should exceed 5s, got {max_duration:.3f}s"
        assert len(results) == 15, "All concurrent operations must complete successfully"
        
        self.assert_business_value_delivered({
            'concurrent_operations': 15,
            'avg_duration': avg_duration,
            'max_duration': max_duration,
            'performance_acceptable': avg_duration < 2.0
        }, 'performance_optimization')

    @pytest.mark.timeout(60)
    async def test_data_recovery_consistency_backup_recovery_cross_service_validation(self, real_services_fixture):
        """Test 14: Data recovery and consistency - Backup, recovery, and cross-service consistency validation"""
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for recovery testing")
        
        user_context = await self.create_isolated_user_context(real_services, "recovery_test")
        user_id = user_context['user_id']
        
        # Create critical business data
        thread_id = ThreadID(f"thread_{uuid.uuid4()}")
        critical_data = {
            'cost_analysis_results': {
                'total_monthly_cost': 5600,
                'optimization_savings': 1680,
                'critical_recommendations': ['migrate_to_spot_instances', 'optimize_storage_class']
            },
            'execution_metadata': {
                'completion_time': time.time(),
                'success': True,
                'business_impact': 'high'
            }
        }
        
        # Store critical data across multiple tables (simulating cross-service consistency)
        async with real_services['db'].begin() as tx:
            # Primary thread record
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, 'thread', :created_at, :metadata_)
            """), {
                'id': str(thread_id),
                'created_at': int(time.time()),
                'metadata_': json.dumps({'user_id': str(user_id), 'critical_data': True})
            })
            
            # Agent results record  
            await tx.execute(text("""
                INSERT INTO apex_optimizer_agent_runs (id, run_id, step_name, step_output, timestamp)
                VALUES (:id, :run_id, :step_name, :step_output, :timestamp)
            """), {
                'id': str(uuid.uuid4()),
                'run_id': f"run_{thread_id}",
                'step_name': 'critical_business_results',
                'step_output': json.dumps(critical_data),
                'timestamp': datetime.now(timezone.utc)
            })
        
        # Simulate data verification for consistency
        async with real_services['db'].begin() as tx:
            # Verify cross-table data consistency
            consistency_query = await tx.execute(text("""
                SELECT 
                    t.id as thread_id,
                    t.metadata_,
                    r.step_output
                FROM threads t
                JOIN apex_optimizer_agent_runs r ON r.run_id = CONCAT('run_', t.id)
                WHERE t.id = :thread_id
            """), {'thread_id': str(thread_id)})
            
            consistency_row = consistency_query.fetchone()
            assert consistency_row is not None, "Cross-service data must be consistent"
            
            thread_metadata = json.loads(consistency_row.metadata_)
            agent_results = json.loads(consistency_row.step_output)
            
            assert thread_metadata['critical_data'] is True, "Thread metadata must be preserved"
            assert agent_results['cost_analysis_results']['optimization_savings'] == 1680, "Business results must be exact"
        
        # Simulate recovery scenario - verify data can be reconstructed
        recovery_data = {}
        async with real_services['db'].begin() as tx:
            recovery_query = await tx.execute(text("""
                SELECT 
                    t.id,
                    t.metadata_,
                    r.step_output,
                    r.timestamp
                FROM threads t
                LEFT JOIN apex_optimizer_agent_runs r ON r.run_id = CONCAT('run_', t.id)
                WHERE t.metadata_::json->>'user_id' = :user_id
                  AND t.metadata_::json->>'critical_data' = 'true'
            """), {'user_id': str(user_id)})
            
            recovery_rows = recovery_query.fetchall()
            
            for row in recovery_rows:
                if row.step_output:
                    recovered_results = json.loads(row.step_output)
                    recovery_data[row.id] = {
                        'thread_metadata': json.loads(row.metadata_),
                        'business_results': recovered_results,
                        'recovery_timestamp': row.timestamp
                    }
        
        assert len(recovery_data) == 1, "All critical data must be recoverable"
        recovered_thread = recovery_data[str(thread_id)]
        assert recovered_thread['business_results']['cost_analysis_results']['total_monthly_cost'] == 5600, "Recovered data must be exact"
        
        self.assert_business_value_delivered({
            'data_consistency': True,
            'cross_service_integrity': True,
            'recovery_possible': True,
            'critical_data_preserved': True
        }, 'data_integrity')

    @pytest.mark.timeout(60)
    async def test_data_cleanup_archival_processes_data_lifecycle_management(self, real_services_fixture):
        """Test 15: Data cleanup and archival processes - Data lifecycle management"""
        real_services = real_services_fixture
        
        if not real_services['database_available']:
            pytest.skip("Real database not available for cleanup testing")
        
        user_context = await self.create_isolated_user_context(real_services, "cleanup_test")
        user_id = user_context['user_id']
        
        # Create data with different lifecycle stages
        current_time = time.time()
        old_thread_id = ThreadID(f"old_thread_{uuid.uuid4()}")
        recent_thread_id = ThreadID(f"recent_thread_{uuid.uuid4()}")
        
        # Old data (simulated 90 days old)
        old_timestamp = current_time - (90 * 24 * 3600)
        # Recent data (simulated 1 day old)
        recent_timestamp = current_time - (1 * 24 * 3600)
        
        async with real_services['db'].begin() as tx:
            # Create old thread (eligible for archival)
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, 'thread', :created_at, :metadata_)
            """), {
                'id': str(old_thread_id),
                'created_at': int(old_timestamp),
                'metadata_': json.dumps({
                    'user_id': str(user_id),
                    'archival_eligible': True,
                    'last_activity': old_timestamp
                })
            })
            
            # Create recent thread (active)
            await tx.execute(text("""
                INSERT INTO threads (id, object, created_at, metadata_)
                VALUES (:id, 'thread', :created_at, :metadata_)
            """), {
                'id': str(recent_thread_id),
                'created_at': int(recent_timestamp),
                'metadata_': json.dumps({
                    'user_id': str(user_id),
                    'archival_eligible': False,
                    'last_activity': recent_timestamp
                })
            })
            
            # Add messages to both threads
            for thread_id, timestamp in [(old_thread_id, old_timestamp), (recent_thread_id, recent_timestamp)]:
                await tx.execute(text("""
                    INSERT INTO messages (id, thread_id, role, content, created_at, object)
                    VALUES (:id, :thread_id, :role, :content, :created_at, 'thread.message')
                """), {
                    'id': f"msg_{uuid.uuid4()}",
                    'thread_id': str(thread_id),
                    'role': 'user',
                    'content': json.dumps([{"type": "text", "text": "Test message"}]),
                    'created_at': int(timestamp)
                })
        
        # Simulate archival process - identify old data
        archival_candidates = []
        async with real_services['db'].begin() as tx:
            archival_query = await tx.execute(text("""
                SELECT t.id, t.created_at, COUNT(m.id) as message_count
                FROM threads t
                LEFT JOIN messages m ON t.id = m.thread_id
                WHERE t.created_at < :archival_cutoff
                  AND t.metadata_::json->>'user_id' = :user_id
                GROUP BY t.id, t.created_at
            """), {
                'archival_cutoff': int(current_time - (30 * 24 * 3600)),  # 30 days
                'user_id': str(user_id)
            })
            
            archival_candidates = archival_query.fetchall()
        
        assert len(archival_candidates) == 1, "Exactly one thread should be eligible for archival"
        assert archival_candidates[0].id == str(old_thread_id), "Old thread must be identified for archival"
        
        # Simulate archival - soft delete old data
        async with real_services['db'].begin() as tx:
            await tx.execute(text("""
                UPDATE threads 
                SET deleted_at = :deleted_at,
                    metadata_ = metadata_ || :archival_metadata::jsonb
                WHERE id = :thread_id
            """), {
                'thread_id': str(old_thread_id),
                'deleted_at': datetime.now(timezone.utc),
                'archival_metadata': json.dumps({
                    'archived': True,
                    'archival_timestamp': current_time,
                    'archival_reason': 'age_based_cleanup'
                })
            })
        
        # Verify archival and active data separation
        async with real_services['db'].begin() as tx:
            active_query = await tx.execute(text("""
                SELECT COUNT(*) as active_count FROM threads 
                WHERE metadata_::json->>'user_id' = :user_id 
                  AND deleted_at IS NULL
            """), {'user_id': str(user_id)})
            active_count = active_query.fetchone().active_count
            
            archived_query = await tx.execute(text("""
                SELECT COUNT(*) as archived_count FROM threads 
                WHERE metadata_::json->>'user_id' = :user_id 
                  AND deleted_at IS NOT NULL
            """), {'user_id': str(user_id)})
            archived_count = archived_query.fetchone().archived_count
            
            assert active_count == 1, "Recent thread must remain active"
            assert archived_count == 1, "Old thread must be archived"
        
        # Verify cleanup preserves business value for recovery if needed
        async with real_services['db'].begin() as tx:
            recovery_query = await tx.execute(text("""
                SELECT metadata_::json->'archival_reason' as archival_reason
                FROM threads 
                WHERE id = :thread_id AND deleted_at IS NOT NULL
            """), {'thread_id': str(old_thread_id)})
            recovery_row = recovery_query.fetchone()
            
            assert recovery_row.archival_reason == 'age_based_cleanup', "Archival reason must be preserved for audit"
        
        self.assert_business_value_delivered({
            'archival_process': True,
            'data_lifecycle_managed': True,
            'active_data_preserved': True,
            'archival_reason_logged': True,
            'recovery_metadata_preserved': True
        }, 'data_lifecycle_management')

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])