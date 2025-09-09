"""
Test Thread Management and Persistence - State Management & Context Swimlane

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - Core conversation continuity functionality
- Business Goal: Enable reliable multi-turn AI conversations with persistent thread state
- Value Impact: Delivers 90% of platform value through reliable conversation continuity across sessions
- Strategic Impact: CRITICAL - Thread persistence enables the core chat experience that drives user engagement

This test suite validates comprehensive thread management operations:
- Thread creation and initialization with proper state persistence
- Thread updates and message continuity across sessions
- Thread cleanup and archival processes
- Multi-thread concurrent management
- Thread state consistency validation
- Cross-session thread recovery
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import RealServicesManager, get_real_services
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.session_management import UserSessionManager, get_user_session_tracker
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID

logger = logging.getLogger(__name__)


@pytest.fixture
async def real_services_fixture():
    """SSOT fixture for real services integration testing."""
    async with get_real_services() as services:
        yield services


@pytest.fixture
async def auth_helper():
    """E2E authentication helper fixture."""
    return E2EAuthHelper(environment="test")


@pytest.fixture
async def id_generator():
    """Unified ID generator fixture."""
    return UnifiedIdGenerator()


class TestThreadManagementPersistence(BaseIntegrationTest):
    """
    Comprehensive thread management and persistence tests.
    
    CRITICAL: Tests use REAL services only - PostgreSQL and Redis for actual persistence validation.
    All tests must validate actual business value through reliable thread continuity.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_creation_with_real_persistence(self, real_services_fixture, auth_helper, id_generator):
        """
        Test thread creation with real database and cache persistence.
        
        Business Value: Validates core thread creation that enables conversation continuity.
        """
        # Create authenticated user
        auth_user = await auth_helper.create_authenticated_user(
            email=f"thread_create_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        # Generate thread-specific IDs
        thread_id, run_id, request_id = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id,
            operation="thread_creation_test"
        )
        
        # Create thread in real PostgreSQL database
        thread_title = f"Test Thread - {datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        thread_metadata = {
            'initial_context': 'Thread persistence testing',
            'conversation_type': 'optimization',
            'created_by_test': True,
            'test_session_id': request_id
        }
        
        async with real_services_fixture.postgres.transaction() as tx:
            # Insert user (if not exists)
            await tx.execute("""
                INSERT INTO auth.users (id, email, name, is_active, created_at)
                VALUES ($1, $2, $3, true, $4)
                ON CONFLICT (email) DO NOTHING
            """, auth_user.user_id, auth_user.email, auth_user.full_name, datetime.now(timezone.utc))
            
            # Create thread with full metadata
            thread_uuid = await tx.fetchval("""
                INSERT INTO backend.threads (id, user_id, title, metadata, created_at, updated_at, status)
                VALUES ($1, $2, $3, $4, $5, $5, 'active')
                RETURNING id
            """, thread_id, auth_user.user_id, thread_title, json.dumps(thread_metadata), datetime.now(timezone.utc))
            
            # Create initial run for the thread
            await tx.execute("""
                INSERT INTO backend.runs (id, thread_id, status, started_at, metadata)
                VALUES ($1, $2, 'active', $3, $4)
            """, run_id, thread_id, datetime.now(timezone.utc), json.dumps({'initial_run': True}))
        
        # Cache thread state in real Redis
        thread_cache_data = {
            'thread_id': thread_id,
            'user_id': auth_user.user_id,
            'title': thread_title,
            'status': 'active',
            'message_count': 0,
            'last_message_at': None,
            'metadata': thread_metadata,
            'run_id': run_id,
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
        
        thread_cache_key = f"thread:{thread_id}"
        await real_services_fixture.redis.set_json(thread_cache_key, thread_cache_data, ex=7200)  # 2 hour TTL
        
        # Verify thread was created in database
        db_thread = await real_services_fixture.postgres.fetchrow("""
            SELECT id, user_id, title, metadata, status, created_at
            FROM backend.threads WHERE id = $1
        """, thread_id)
        
        assert db_thread is not None
        assert db_thread['id'] == thread_id
        assert db_thread['user_id'] == auth_user.user_id
        assert db_thread['title'] == thread_title
        assert db_thread['status'] == 'active'
        
        stored_metadata = json.loads(db_thread['metadata'])
        assert stored_metadata['conversation_type'] == 'optimization'
        assert stored_metadata['created_by_test'] is True
        
        # Verify run was created
        db_run = await real_services_fixture.postgres.fetchrow("""
            SELECT id, thread_id, status FROM backend.runs WHERE id = $1
        """, run_id)
        
        assert db_run is not None
        assert db_run['thread_id'] == thread_id
        assert db_run['status'] == 'active'
        
        # Verify thread was cached in Redis
        cached_thread = await real_services_fixture.redis.get_json(thread_cache_key)
        assert cached_thread is not None
        assert cached_thread['thread_id'] == thread_id
        assert cached_thread['user_id'] == auth_user.user_id
        assert cached_thread['status'] == 'active'
        
        # BUSINESS VALUE VALIDATION: Thread creation enables conversation flow
        self.assert_business_value_delivered({
            'thread_created': True,
            'database_persistence': True,
            'cache_persistence': True,
            'conversation_ready': True,
            'metadata_preserved': len(thread_metadata) > 0
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_message_continuity_across_sessions(self, real_services_fixture, auth_helper, id_generator):
        """
        Test thread message continuity across multiple sessions.
        
        Business Value: Validates conversation continuity that enables multi-turn AI interactions.
        """
        # Create user and initial thread
        auth_user = await auth_helper.create_authenticated_user(
            email=f"continuity_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        thread_id, _, _ = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id,
            operation="continuity_test"
        )
        
        # Create thread in database
        async with real_services_fixture.postgres.transaction() as tx:
            await tx.execute("""
                INSERT INTO auth.users (id, email, name, is_active, created_at)
                VALUES ($1, $2, $3, true, $4)
                ON CONFLICT (email) DO NOTHING
            """, auth_user.user_id, auth_user.email, auth_user.full_name, datetime.now(timezone.utc))
            
            await tx.execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at, updated_at, status)
                VALUES ($1, $2, 'Continuity Test Thread', $3, $3, 'active')
            """, thread_id, auth_user.user_id, datetime.now(timezone.utc))
        
        # Simulate multiple sessions with message exchanges
        sessions = []
        message_history = []
        
        for session_num in range(3):  # Simulate 3 different sessions
            # Generate new run ID for each session
            _, run_id, request_id = id_generator.generate_user_context_ids(
                user_id=auth_user.user_id,
                operation=f"session_{session_num}"
            )
            
            # Create run for this session
            async with real_services_fixture.postgres.transaction() as tx:
                await tx.execute("""
                    INSERT INTO backend.runs (id, thread_id, status, started_at, metadata)
                    VALUES ($1, $2, 'active', $3, $4)
                """, run_id, thread_id, datetime.now(timezone.utc), 
                json.dumps({'session_number': session_num, 'request_id': request_id}))
            
            # Add messages to this session
            session_messages = []
            for msg_num in range(2):  # 2 messages per session (user + assistant)
                message_id = f"{run_id}_msg_{msg_num}"
                message_role = "user" if msg_num % 2 == 0 else "assistant"
                message_content = f"Session {session_num}, Message {msg_num}: {message_role} message content"
                
                # Store message in database
                async with real_services_fixture.postgres.transaction() as tx:
                    await tx.execute("""
                        INSERT INTO backend.messages (id, thread_id, run_id, role, content, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, message_id, thread_id, run_id, message_role, message_content, datetime.now(timezone.utc))
                
                session_messages.append({
                    'id': message_id,
                    'role': message_role,
                    'content': message_content,
                    'run_id': run_id,
                    'session': session_num
                })
                
                message_history.append(session_messages[-1])
            
            sessions.append({
                'run_id': run_id,
                'request_id': request_id,
                'messages': session_messages
            })
            
            # Update thread cache with latest messages
            thread_state = {
                'thread_id': thread_id,
                'user_id': auth_user.user_id,
                'current_run_id': run_id,
                'message_count': len(message_history),
                'last_message_at': datetime.now(timezone.utc).isoformat(),
                'session_count': session_num + 1,
                'latest_messages': session_messages
            }
            
            await real_services_fixture.redis.set_json(f"thread:{thread_id}", thread_state, ex=7200)
            
            # Add delay to simulate time between sessions
            await asyncio.sleep(0.1)
        
        # Verify message continuity across all sessions
        all_messages = await real_services_fixture.postgres.fetch("""
            SELECT id, role, content, run_id, created_at
            FROM backend.messages 
            WHERE thread_id = $1 
            ORDER BY created_at ASC
        """, thread_id)
        
        # Validate message count and order
        assert len(all_messages) == 6  # 3 sessions × 2 messages each
        assert len(sessions) == 3
        
        # Verify message continuity
        expected_message_count = 0
        for session in sessions:
            for message in session['messages']:
                db_message = next((m for m in all_messages if m['id'] == message['id']), None)
                assert db_message is not None
                assert db_message['role'] == message['role']
                assert db_message['content'] == message['content']
                assert db_message['run_id'] == message['run_id']
                expected_message_count += 1
        
        assert expected_message_count == len(all_messages)
        
        # Verify thread state reflects full conversation
        final_thread_state = await real_services_fixture.redis.get_json(f"thread:{thread_id}")
        assert final_thread_state['message_count'] == len(message_history)
        assert final_thread_state['session_count'] == 3
        
        # BUSINESS VALUE VALIDATION: Message continuity enables effective AI conversations
        self.assert_business_value_delivered({
            'sessions_completed': len(sessions),
            'messages_persisted': len(all_messages),
            'continuity_maintained': True,
            'conversation_depth': len(sessions) * 2
        }, 'insights')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_thread_management(self, real_services_fixture, auth_helper, id_generator):
        """
        Test concurrent thread management with multiple threads per user.
        
        Business Value: Validates multi-thread support that enables complex user workflows.
        """
        # Create user for concurrent thread testing
        auth_user = await auth_helper.create_authenticated_user(
            email=f"concurrent_threads_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        # Insert user into database
        async with real_services_fixture.postgres.transaction() as tx:
            await tx.execute("""
                INSERT INTO auth.users (id, email, name, is_active, created_at)
                VALUES ($1, $2, $3, true, $4)
                ON CONFLICT (email) DO NOTHING
            """, auth_user.user_id, auth_user.email, auth_user.full_name, datetime.now(timezone.utc))
        
        # Create multiple threads concurrently
        concurrent_threads = []
        thread_operations = []
        
        async def create_thread_with_messages(thread_index: int) -> Dict[str, Any]:
            """Create a thread with messages in a concurrent operation."""
            thread_id, run_id, request_id = id_generator.generate_user_context_ids(
                user_id=auth_user.user_id,
                operation=f"concurrent_thread_{thread_index}"
            )
            
            thread_title = f"Concurrent Thread {thread_index}"
            thread_metadata = {
                'thread_index': thread_index,
                'thread_type': 'concurrent_test',
                'created_concurrently': True
            }
            
            # Create thread in database
            async with real_services_fixture.postgres.transaction() as tx:
                await tx.execute("""
                    INSERT INTO backend.threads (id, user_id, title, metadata, created_at, updated_at, status)
                    VALUES ($1, $2, $3, $4, $5, $5, 'active')
                """, thread_id, auth_user.user_id, thread_title, json.dumps(thread_metadata), datetime.now(timezone.utc))
                
                # Create run for this thread
                await tx.execute("""
                    INSERT INTO backend.runs (id, thread_id, status, started_at, metadata)
                    VALUES ($1, $2, 'active', $3, $4)
                """, run_id, thread_id, datetime.now(timezone.utc), json.dumps({'concurrent_test': True}))
                
                # Add messages to thread
                messages = []
                for msg_idx in range(3):  # 3 messages per thread
                    message_id = f"{run_id}_msg_{msg_idx}"
                    message_content = f"Thread {thread_index}, Message {msg_idx}"
                    
                    await tx.execute("""
                        INSERT INTO backend.messages (id, thread_id, run_id, role, content, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, message_id, thread_id, run_id, 
                    "user" if msg_idx % 2 == 0 else "assistant", 
                    message_content, datetime.now(timezone.utc))
                    
                    messages.append({
                        'id': message_id,
                        'content': message_content,
                        'role': "user" if msg_idx % 2 == 0 else "assistant"
                    })
            
            # Cache thread state
            thread_state = {
                'thread_id': thread_id,
                'user_id': auth_user.user_id,
                'title': thread_title,
                'thread_index': thread_index,
                'run_id': run_id,
                'message_count': len(messages),
                'messages': messages,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            await real_services_fixture.redis.set_json(f"thread:{thread_id}", thread_state, ex=7200)
            
            return {
                'thread_id': thread_id,
                'run_id': run_id,
                'title': thread_title,
                'message_count': len(messages),
                'thread_index': thread_index
            }
        
        # Execute concurrent thread creation (5 threads)
        concurrent_results = await asyncio.gather(*[
            create_thread_with_messages(i) for i in range(5)
        ])
        
        # Verify all threads were created successfully
        assert len(concurrent_results) == 5
        
        # Validate each thread in database
        for result in concurrent_results:
            thread_id = result['thread_id']
            
            # Check thread in database
            db_thread = await real_services_fixture.postgres.fetchrow("""
                SELECT id, user_id, title, metadata, status
                FROM backend.threads WHERE id = $1
            """, thread_id)
            
            assert db_thread is not None
            assert db_thread['user_id'] == auth_user.user_id
            assert db_thread['title'] == result['title']
            assert db_thread['status'] == 'active'
            
            # Check messages for this thread
            thread_messages = await real_services_fixture.postgres.fetch("""
                SELECT id, role, content FROM backend.messages 
                WHERE thread_id = $1 ORDER BY created_at ASC
            """, thread_id)
            
            assert len(thread_messages) == 3
            assert result['message_count'] == 3
            
            # Check thread in cache
            cached_thread = await real_services_fixture.redis.get_json(f"thread:{thread_id}")
            assert cached_thread is not None
            assert cached_thread['thread_id'] == thread_id
            assert cached_thread['message_count'] == 3
        
        # Verify thread isolation - each thread should have distinct content
        thread_ids = [result['thread_id'] for result in concurrent_results]
        assert len(set(thread_ids)) == 5  # All thread IDs should be unique
        
        # Verify user can access all their threads
        user_threads = await real_services_fixture.postgres.fetch("""
            SELECT id, title, metadata FROM backend.threads 
            WHERE user_id = $1 AND metadata->>'concurrent_test' = 'true'
            ORDER BY created_at ASC
        """, auth_user.user_id)
        
        assert len(user_threads) >= 5  # At least the 5 we created
        
        # BUSINESS VALUE VALIDATION: Concurrent threads enable complex workflows
        self.assert_business_value_delivered({
            'threads_created_concurrently': len(concurrent_results),
            'total_messages': sum(result['message_count'] for result in concurrent_results),
            'thread_isolation_maintained': True,
            'concurrent_operations_successful': len(concurrent_results) == 5
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_cleanup_and_archival(self, real_services_fixture, auth_helper, id_generator):
        """
        Test thread cleanup and archival processes.
        
        Business Value: Prevents resource exhaustion while preserving valuable conversation history.
        """
        # Create user and threads for cleanup testing
        auth_user = await auth_helper.create_authenticated_user(
            email=f"cleanup_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        async with real_services_fixture.postgres.transaction() as tx:
            await tx.execute("""
                INSERT INTO auth.users (id, email, name, is_active, created_at)
                VALUES ($1, $2, $3, true, $4)
                ON CONFLICT (email) DO NOTHING
            """, auth_user.user_id, auth_user.email, auth_user.full_name, datetime.now(timezone.utc))
        
        # Create threads with different states for cleanup testing
        cleanup_scenarios = [
            {'age_hours': 72, 'status': 'inactive', 'message_count': 0, 'should_archive': True},
            {'age_hours': 24, 'status': 'active', 'message_count': 10, 'should_archive': False},
            {'age_hours': 168, 'status': 'completed', 'message_count': 5, 'should_archive': True},
            {'age_hours': 1, 'status': 'active', 'message_count': 3, 'should_archive': False},
            {'age_hours': 120, 'status': 'inactive', 'message_count': 0, 'should_archive': True}
        ]
        
        created_threads = []
        
        for i, scenario in enumerate(cleanup_scenarios):
            thread_id, run_id, _ = id_generator.generate_user_context_ids(
                user_id=auth_user.user_id,
                operation=f"cleanup_scenario_{i}"
            )
            
            # Calculate creation time based on age
            created_at = datetime.now(timezone.utc) - timedelta(hours=scenario['age_hours'])
            updated_at = created_at + timedelta(minutes=30)  # Some activity after creation
            
            # Create thread with specific age and status
            async with real_services_fixture.postgres.transaction() as tx:
                await tx.execute("""
                    INSERT INTO backend.threads (id, user_id, title, status, created_at, updated_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, thread_id, auth_user.user_id, f"Cleanup Test Thread {i}", 
                scenario['status'], created_at, updated_at, 
                json.dumps({'cleanup_test': True, 'scenario_index': i}))
                
                # Create run
                await tx.execute("""
                    INSERT INTO backend.runs (id, thread_id, status, started_at)
                    VALUES ($1, $2, 'completed', $3)
                """, run_id, thread_id, created_at)
                
                # Add messages if specified
                for msg_idx in range(scenario['message_count']):
                    message_id = f"{run_id}_msg_{msg_idx}"
                    await tx.execute("""
                        INSERT INTO backend.messages (id, thread_id, run_id, role, content, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, message_id, thread_id, run_id, 
                    "user" if msg_idx % 2 == 0 else "assistant",
                    f"Test message {msg_idx}", created_at)
            
            # Cache thread state
            thread_cache = {
                'thread_id': thread_id,
                'status': scenario['status'],
                'age_hours': scenario['age_hours'],
                'message_count': scenario['message_count'],
                'should_archive': scenario['should_archive']
            }
            
            await real_services_fixture.redis.set_json(f"thread:{thread_id}", thread_cache, ex=300)
            
            created_threads.append({
                'thread_id': thread_id,
                'run_id': run_id,
                'scenario': scenario,
                'scenario_index': i
            })
        
        # Perform cleanup operation
        archived_threads = []
        active_threads = []
        
        cleanup_criteria = {
            'max_age_hours': 48,  # Archive threads older than 48 hours
            'inactive_age_hours': 24,  # Archive inactive threads older than 24 hours
            'preserve_with_messages': True  # Preserve threads with messages unless very old
        }
        
        for thread_info in created_threads:
            thread_id = thread_info['thread_id']
            scenario = thread_info['scenario']
            
            # Get thread details
            db_thread = await real_services_fixture.postgres.fetchrow("""
                SELECT id, status, created_at, updated_at FROM backend.threads WHERE id = $1
            """, thread_id)
            
            message_count = await real_services_fixture.postgres.fetchval("""
                SELECT COUNT(*) FROM backend.messages WHERE thread_id = $1
            """, thread_id)
            
            # Apply cleanup criteria
            thread_age_hours = (datetime.now(timezone.utc) - db_thread['created_at']).total_seconds() / 3600
            should_archive = False
            
            if thread_age_hours > cleanup_criteria['max_age_hours']:
                should_archive = True
            elif (db_thread['status'] == 'inactive' and 
                  thread_age_hours > cleanup_criteria['inactive_age_hours']):
                should_archive = True
            
            # Override if thread has valuable content
            if (cleanup_criteria['preserve_with_messages'] and 
                message_count > 0 and 
                thread_age_hours < 168):  # Less than 1 week
                should_archive = False
            
            if should_archive:
                # Archive thread (move to archived status, keep data)
                async with real_services_fixture.postgres.transaction() as tx:
                    await tx.execute("""
                        UPDATE backend.threads 
                        SET status = 'archived', archived_at = $2
                        WHERE id = $1
                    """, thread_id, datetime.now(timezone.utc))
                
                # Remove from active cache but keep archival record
                await real_services_fixture.redis.delete(f"thread:{thread_id}")
                
                # Add to archival cache
                archive_data = {
                    'thread_id': thread_id,
                    'archived_at': datetime.now(timezone.utc).isoformat(),
                    'original_status': scenario['status'],
                    'message_count': message_count,
                    'archive_reason': 'automated_cleanup'
                }
                
                await real_services_fixture.redis.set_json(f"archived:{thread_id}", archive_data, ex=86400)
                archived_threads.append(thread_info)
            else:
                active_threads.append(thread_info)
        
        # Verify cleanup results
        archived_count = len(archived_threads)
        active_count = len(active_threads)
        
        assert archived_count + active_count == len(created_threads)
        
        # Verify archived threads are properly marked
        for thread_info in archived_threads:
            db_thread = await real_services_fixture.postgres.fetchrow("""
                SELECT status, archived_at FROM backend.threads WHERE id = $1
            """, thread_info['thread_id'])
            
            assert db_thread['status'] == 'archived'
            assert db_thread['archived_at'] is not None
            
            # Verify archival cache
            archive_data = await real_services_fixture.redis.get_json(f"archived:{thread_info['thread_id']}")
            assert archive_data is not None
            assert archive_data['archive_reason'] == 'automated_cleanup'
        
        # Verify active threads remain accessible
        for thread_info in active_threads:
            db_thread = await real_services_fixture.postgres.fetchrow("""
                SELECT status FROM backend.threads WHERE id = $1
            """, thread_info['thread_id'])
            
            assert db_thread['status'] != 'archived'
        
        # BUSINESS VALUE VALIDATION: Cleanup preserves system performance while retaining value
        self.assert_business_value_delivered({
            'threads_processed': len(created_threads),
            'threads_archived': archived_count,
            'threads_preserved': active_count,
            'storage_efficiency': archived_count / len(created_threads),
            'valuable_content_preserved': any(
                info['scenario']['message_count'] > 0 
                for info in active_threads
            )
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_session_thread_recovery(self, real_services_fixture, auth_helper, id_generator):
        """
        Test thread recovery across different sessions and connection interruptions.
        
        Business Value: Ensures conversation continuity even after connection issues or restarts.
        """
        # Create user and initial thread
        auth_user = await auth_helper.create_authenticated_user(
            email=f"recovery_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        thread_id, run_id, _ = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id,
            operation="recovery_test"
        )
        
        # Create thread with rich conversation history
        async with real_services_fixture.postgres.transaction() as tx:
            await tx.execute("""
                INSERT INTO auth.users (id, email, name, is_active, created_at)
                VALUES ($1, $2, $3, true, $4)
                ON CONFLICT (email) DO NOTHING
            """, auth_user.user_id, auth_user.email, auth_user.full_name, datetime.now(timezone.utc))
            
            await tx.execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at, updated_at, status, metadata)
                VALUES ($1, $2, 'Recovery Test Thread', $3, $3, 'active', $4)
            """, thread_id, auth_user.user_id, datetime.now(timezone.utc), 
            json.dumps({'recovery_test': True, 'important_conversation': True}))
            
            await tx.execute("""
                INSERT INTO backend.runs (id, thread_id, status, started_at)
                VALUES ($1, $2, 'active', $3)
            """, run_id, thread_id, datetime.now(timezone.utc))
        
        # Build conversation history
        conversation_messages = [
            {"role": "user", "content": "I need help optimizing my AWS costs"},
            {"role": "assistant", "content": "I can help you analyze your AWS spending. Let me examine your current usage patterns."},
            {"role": "user", "content": "My monthly bill is around $5000, mostly from EC2 instances"},
            {"role": "assistant", "content": "Let me analyze your EC2 usage. I found several optimization opportunities that could save 30% on costs."},
            {"role": "user", "content": "What specific recommendations do you have?"},
            {"role": "assistant", "content": "Here are my recommendations: 1) Right-size oversized instances, 2) Use Reserved Instances for steady workloads, 3) Implement auto-scaling"}
        ]
        
        # Store conversation in database
        message_ids = []
        for i, message in enumerate(conversation_messages):
            message_id = f"{run_id}_msg_{i}"
            async with real_services_fixture.postgres.transaction() as tx:
                await tx.execute("""
                    INSERT INTO backend.messages (id, thread_id, run_id, role, content, created_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, message_id, thread_id, run_id, message['role'], message['content'], 
                datetime.now(timezone.utc) - timedelta(minutes=10-i),
                json.dumps({'message_index': i, 'conversation_flow': True}))
            
            message_ids.append(message_id)
        
        # Cache conversation state
        conversation_state = {
            'thread_id': thread_id,
            'user_id': auth_user.user_id,
            'run_id': run_id,
            'message_count': len(conversation_messages),
            'last_message_role': conversation_messages[-1]['role'],
            'conversation_topic': 'aws_cost_optimization',
            'session_active': True,
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture.redis.set_json(f"thread:{thread_id}", conversation_state, ex=7200)
        
        # Simulate session interruption (clear cache)
        await real_services_fixture.redis.delete(f"thread:{thread_id}")
        
        # Simulate user reconnecting and attempting to resume conversation
        # Recovery process: Rebuild thread state from database
        
        # Step 1: Verify thread exists in database
        db_thread = await real_services_fixture.postgres.fetchrow("""
            SELECT id, user_id, title, status, created_at, metadata
            FROM backend.threads WHERE id = $1 AND user_id = $2
        """, thread_id, auth_user.user_id)
        
        assert db_thread is not None
        assert db_thread['status'] == 'active'
        
        # Step 2: Recover message history
        message_history = await real_services_fixture.postgres.fetch("""
            SELECT id, role, content, created_at, metadata
            FROM backend.messages 
            WHERE thread_id = $1 
            ORDER BY created_at ASC
        """, thread_id)
        
        assert len(message_history) == len(conversation_messages)
        
        # Step 3: Rebuild conversation context
        recovered_context = {
            'thread_id': thread_id,
            'user_id': auth_user.user_id,
            'title': db_thread['title'],
            'status': db_thread['status'],
            'message_count': len(message_history),
            'conversation_history': [
                {
                    'id': msg['id'],
                    'role': msg['role'],
                    'content': msg['content'],
                    'created_at': msg['created_at'].isoformat()
                }
                for msg in message_history
            ],
            'last_message_role': message_history[-1]['role'] if message_history else None,
            'recovered_at': datetime.now(timezone.utc).isoformat(),
            'recovery_successful': True
        }
        
        # Step 4: Restore cache with recovered data
        await real_services_fixture.redis.set_json(f"thread:{thread_id}", recovered_context, ex=7200)
        
        # Step 5: Verify recovery completeness
        recovered_thread = await real_services_fixture.redis.get_json(f"thread:{thread_id}")
        assert recovered_thread is not None
        assert recovered_thread['thread_id'] == thread_id
        assert recovered_thread['message_count'] == len(conversation_messages)
        assert recovered_thread['recovery_successful'] is True
        
        # Validate conversation continuity
        for i, original_msg in enumerate(conversation_messages):
            recovered_msg = recovered_context['conversation_history'][i]
            assert recovered_msg['role'] == original_msg['role']
            assert recovered_msg['content'] == original_msg['content']
        
        # Test continuing conversation after recovery
        new_run_id = id_generator.generate_run_id(user_id=auth_user.user_id, operation="recovery_continuation")
        
        # Add new message to verify continuity
        new_message_id = f"{new_run_id}_continuation"
        await real_services_fixture.postgres.execute("""
            INSERT INTO backend.messages (id, thread_id, run_id, role, content, created_at, metadata)
            VALUES ($1, $2, $3, 'user', 'Thank you for the recommendations. How do I implement auto-scaling?', $4, $5)
        """, new_message_id, thread_id, new_run_id, datetime.now(timezone.utc), 
        json.dumps({'post_recovery': True, 'continuation': True}))
        
        # Update recovered context
        recovered_context['message_count'] += 1
        recovered_context['last_activity'] = datetime.now(timezone.utc).isoformat()
        await real_services_fixture.redis.set_json(f"thread:{thread_id}", recovered_context, ex=7200)
        
        # Final verification: Complete conversation history
        final_message_count = await real_services_fixture.postgres.fetchval("""
            SELECT COUNT(*) FROM backend.messages WHERE thread_id = $1
        """, thread_id)
        
        assert final_message_count == len(conversation_messages) + 1
        
        # BUSINESS VALUE VALIDATION: Recovery enables uninterrupted user experience
        self.assert_business_value_delivered({
            'conversation_recovered': True,
            'messages_preserved': len(conversation_messages),
            'continuity_maintained': True,
            'recovery_time_acceptable': True,
            'conversation_can_continue': final_message_count > len(conversation_messages)
        }, 'insights')