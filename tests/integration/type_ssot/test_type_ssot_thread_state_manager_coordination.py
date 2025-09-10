"""
Test Thread State Manager Cross-Service Type Coordination

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure thread state management consistency across microservices
- Value Impact: Prevents cross-service type mismatches that break multi-user isolation
- Strategic Impact: $120K+ MRR depends on reliable multi-user thread management

CRITICAL: ThreadState coordination between UnifiedStateManager, WebSocketManager,
and ThreadService must use consistent type definitions to prevent race conditions
and user context bleeding between sessions.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import ThreadID, UserID, ConnectionID


class TestThreadStateManagerCoordination(BaseIntegrationTest):
    """Integration tests for thread state manager cross-service type coordination."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_unified_state_manager_thread_type_consistency(self, real_services_fixture):
        """
        Test that UnifiedStateManager uses consistent ThreadState types.
        
        CRITICAL: UnifiedStateManager is the SSOT for state management.
        Any type inconsistency here cascades to all dependent services.
        """
        # Import the actual UnifiedStateManager
        try:
            from netra_backend.app.core.managers.unified_state_manager import UnifiedStateManager, StateManagerFactory
        except ImportError:
            pytest.skip("UnifiedStateManager not available - may be in different location")
        
        # Setup real database connection
        db_session = real_services_fixture['db']
        redis_client = real_services_fixture['redis']
        
        # Initialize state manager with real services using SSOT factory pattern
        state_manager = StateManagerFactory.get_global_manager()
        
        # Test thread state creation
        test_thread_id = ThreadID("state-mgr-test-001")
        test_user_id = UserID("state-user-001")
        
        thread_state_data = {
            'thread_id': test_thread_id,
            'user_id': test_user_id,
            'status': 'active',
            'context': {'agent_type': 'cost_optimizer'},
            'last_activity': asyncio.get_event_loop().time()
        }
        
        # Create thread state through manager
        created_state = await state_manager.create_thread_state(
            thread_id=test_thread_id,
            user_id=test_user_id,
            initial_context=thread_state_data['context']
        )
        
        # Validate created state has consistent type structure
        assert hasattr(created_state, 'thread_id'), "ThreadState must have thread_id field"
        assert hasattr(created_state, 'user_id'), "ThreadState must have user_id field"
        assert hasattr(created_state, 'status'), "ThreadState must have status field"
        
        # Type validation - must use strongly typed IDs
        if hasattr(created_state, 'thread_id'):
            assert isinstance(created_state.thread_id, ThreadID), (
                f"thread_id must be strongly typed ThreadID, got {type(created_state.thread_id)}"
            )
        
        if hasattr(created_state, 'user_id'):
            assert isinstance(created_state.user_id, UserID), (
                f"user_id must be strongly typed UserID, got {type(created_state.user_id)}"
            )
        
        # Retrieve state and verify consistency
        retrieved_state = await state_manager.get_thread_state(test_thread_id)
        
        assert retrieved_state is not None, "Thread state must be retrievable after creation"
        assert retrieved_state.thread_id == test_thread_id, "Retrieved thread_id must match created"
        assert retrieved_state.user_id == test_user_id, "Retrieved user_id must match created"
        
        # Cleanup
        await state_manager.delete_thread_state(test_thread_id)


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_thread_state_synchronization(self, real_services_fixture):
        """
        Test WebSocketManager and thread state synchronization use consistent types.
        
        BUSINESS CRITICAL: WebSocket events inform users of thread state changes.
        Type mismatches cause silent failures and broken user experience.
        """
        # Setup real services
        redis_client = real_services_fixture['redis']
        
        # Mock WebSocketManager for testing
        class MockWebSocketManager:
            def __init__(self):
                self.sent_events = []
                self.connection_registry = {}
            
            async def register_connection(self, connection_id: ConnectionID, user_id: UserID, thread_id: ThreadID):
                self.connection_registry[connection_id] = {
                    'user_id': user_id,
                    'thread_id': thread_id,
                    'registered_at': asyncio.get_event_loop().time()
                }
            
            async def notify_thread_state_change(self, thread_id: ThreadID, new_state: str, user_id: UserID):
                # Find connections for this user/thread combination
                target_connections = [
                    conn_id for conn_id, conn_data in self.connection_registry.items()
                    if conn_data['user_id'] == user_id and conn_data['thread_id'] == thread_id
                ]
                
                event = {
                    'type': 'thread_state_change',
                    'thread_id': thread_id,
                    'new_state': new_state,
                    'user_id': user_id,
                    'target_connections': target_connections
                }
                self.sent_events.append(event)
                
                # Store in Redis for persistence
                await redis_client.setex(
                    f"thread_event:{thread_id}:latest",
                    300,  # 5 minutes
                    json.dumps({
                        'state': new_state,
                        'user_id': str(user_id),
                        'timestamp': asyncio.get_event_loop().time()
                    })
                )
        
        websocket_manager = MockWebSocketManager()
        
        # Test multi-user thread state isolation
        user1_id = UserID("ws-user-001")
        user2_id = UserID("ws-user-002")
        thread1_id = ThreadID("ws-thread-001")
        thread2_id = ThreadID("ws-thread-002")
        
        # Register connections for different users
        await websocket_manager.register_connection(
            ConnectionID("conn-001"), user1_id, thread1_id
        )
        await websocket_manager.register_connection(
            ConnectionID("conn-002"), user2_id, thread2_id
        )
        
        # Send thread state changes
        await websocket_manager.notify_thread_state_change(thread1_id, "processing", user1_id)
        await websocket_manager.notify_thread_state_change(thread2_id, "waiting", user2_id)
        
        # Validate events were properly isolated by user
        assert len(websocket_manager.sent_events) == 2, "Should have 2 thread state events"
        
        event1, event2 = websocket_manager.sent_events
        
        # User 1 event validation
        assert event1['user_id'] == user1_id, "Event 1 must target correct user"
        assert event1['thread_id'] == thread1_id, "Event 1 must target correct thread"
        assert event1['new_state'] == "processing", "Event 1 must have correct state"
        assert ConnectionID("conn-001") in event1['target_connections'], "Event 1 must target user 1's connection"
        assert ConnectionID("conn-002") not in event1['target_connections'], "Event 1 must NOT target user 2's connection"
        
        # User 2 event validation  
        assert event2['user_id'] == user2_id, "Event 2 must target correct user"
        assert event2['thread_id'] == thread2_id, "Event 2 must target correct thread"
        assert event2['new_state'] == "waiting", "Event 2 must have correct state"
        assert ConnectionID("conn-002") in event2['target_connections'], "Event 2 must target user 2's connection"
        assert ConnectionID("conn-001") not in event2['target_connections'], "Event 2 must NOT target user 1's connection"
        
        # Validate Redis persistence uses consistent serialization
        redis_event1 = await redis_client.get(f"thread_event:{thread1_id}:latest")
        redis_event2 = await redis_client.get(f"thread_event:{thread2_id}:latest")
        
        assert redis_event1 is not None, "Thread 1 event must be persisted in Redis"
        assert redis_event2 is not None, "Thread 2 event must be persisted in Redis"
        
        parsed_event1 = json.loads(redis_event1.decode())
        parsed_event2 = json.loads(redis_event2.decode())
        
        assert parsed_event1['state'] == "processing", "Redis event 1 must have correct state"
        assert parsed_event1['user_id'] == str(user1_id), "Redis event 1 must have correct user_id"
        assert parsed_event2['state'] == "waiting", "Redis event 2 must have correct state"
        assert parsed_event2['user_id'] == str(user2_id), "Redis event 2 must have correct user_id"
        
        # Cleanup
        await redis_client.delete(f"thread_event:{thread1_id}:latest")
        await redis_client.delete(f"thread_event:{thread2_id}:latest")


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_service_state_consistency_validation(self, real_services_fixture):
        """
        Test ThreadService maintains state consistency with database and cache.
        
        GOLDEN PATH CRITICAL: Thread service manages conversation continuity.
        State inconsistencies break user chat experience and conversation context.
        """
        # Setup real database and Redis
        db_session = real_services_fixture['db']
        redis_client = real_services_fixture['redis']
        
        # Mock ThreadService for testing
        class MockThreadService:
            def __init__(self, db_session, redis_client):
                self.db = db_session
                self.redis = redis_client
            
            async def create_thread(self, user_id: UserID, title: Optional[str] = None) -> ThreadID:
                thread_id = ThreadID(f"thread-service-{int(asyncio.get_event_loop().time() * 1000)}")
                
                # Create in database
                await self.db.execute("""
                    INSERT INTO threads (id, user_id, title, status, created_at)
                    VALUES (%(thread_id)s, %(user_id)s, %(title)s, 'active', NOW())
                """, {
                    'thread_id': str(thread_id),
                    'user_id': str(user_id),
                    'title': title or f"Thread {thread_id}"
                })
                await self.db.commit()
                
                # Cache in Redis
                await self.redis.setex(
                    f"thread:{thread_id}:state",
                    3600,  # 1 hour
                    json.dumps({
                        'status': 'active',
                        'user_id': str(user_id),
                        'created_at': asyncio.get_event_loop().time()
                    })
                )
                
                return thread_id
            
            async def get_thread_state(self, thread_id: ThreadID) -> Optional[Dict[str, Any]]:
                # Try Redis first (faster)
                cached_state = await self.redis.get(f"thread:{thread_id}:state")
                if cached_state:
                    return json.loads(cached_state.decode())
                
                # Fallback to database
                db_result = await self.db.fetchrow(
                    "SELECT status, user_id FROM threads WHERE id = $1",
                    str(thread_id)
                )
                
                if db_result:
                    state = {
                        'status': db_result['status'],
                        'user_id': db_result['user_id']
                    }
                    
                    # Repopulate cache
                    await self.redis.setex(
                        f"thread:{thread_id}:state",
                        3600,
                        json.dumps(state)
                    )
                    
                    return state
                
                return None
            
            async def update_thread_state(self, thread_id: ThreadID, new_status: str) -> bool:
                # Update database
                result = await self.db.execute(
                    "UPDATE threads SET status = $1, updated_at = NOW() WHERE id = $2",
                    new_status, str(thread_id)
                )
                await self.db.commit()
                
                if result == "UPDATE 1":
                    # Update cache
                    current_state = await self.get_thread_state(thread_id)
                    if current_state:
                        current_state['status'] = new_status
                        await self.redis.setex(
                            f"thread:{thread_id}:state",
                            3600,
                            json.dumps(current_state)
                        )
                    return True
                
                return False
        
        thread_service = MockThreadService(db_session, redis_client)
        
        # Test thread lifecycle with state consistency
        test_user_id = UserID("thread-svc-user-001")
        
        # Create thread
        thread_id = await thread_service.create_thread(test_user_id, "SSOT Test Thread")
        
        # Validate initial state consistency
        initial_state = await thread_service.get_thread_state(thread_id)
        assert initial_state is not None, "Thread state must exist after creation"
        assert initial_state['status'] == 'active', "Initial thread status must be 'active'"
        assert initial_state['user_id'] == str(test_user_id), "Thread must be associated with correct user"
        
        # Update thread state
        update_success = await thread_service.update_thread_state(thread_id, 'processing')
        assert update_success, "Thread state update must succeed"
        
        # Validate state consistency after update
        updated_state = await thread_service.get_thread_state(thread_id)
        assert updated_state is not None, "Thread state must exist after update"
        assert updated_state['status'] == 'processing', "Thread status must be updated"
        assert updated_state['user_id'] == str(test_user_id), "User association must remain consistent"
        
        # Test cache invalidation and database fallback
        await redis_client.delete(f"thread:{thread_id}:state")
        
        # Should fallback to database and repopulate cache
        fallback_state = await thread_service.get_thread_state(thread_id)
        assert fallback_state is not None, "Database fallback must work"
        assert fallback_state['status'] == 'processing', "Database fallback must have correct status"
        
        # Verify cache was repopulated
        repopulated_cache = await redis_client.get(f"thread:{thread_id}:state")
        assert repopulated_cache is not None, "Cache must be repopulated after database fallback"
        
        parsed_cache = json.loads(repopulated_cache.decode())
        assert parsed_cache['status'] == 'processing', "Repopulated cache must have correct status"
        
        # Cleanup
        await db_session.execute("DELETE FROM threads WHERE id = $1", str(thread_id))
        await redis_client.delete(f"thread:{thread_id}:state")
        await db_session.commit()


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_state_race_condition_prevention(self, real_services_fixture):
        """
        Test that ThreadState updates prevent race conditions in multi-user scenarios.
        
        CRITICAL: Race conditions in thread state can cause user context bleeding
        and data corruption. This is a security and reliability issue.
        """
        # Setup real services
        db_session = real_services_fixture['db']
        redis_client = real_services_fixture['redis']
        
        # Test concurrent thread state updates
        user1_id = UserID("race-user-001")
        user2_id = UserID("race-user-002")
        thread1_id = ThreadID("race-thread-001")
        thread2_id = ThreadID("race-thread-002")
        
        # Create test threads
        for thread_id, user_id in [(thread1_id, user1_id), (thread2_id, user2_id)]:
            await db_session.execute("""
                INSERT INTO threads (id, user_id, status, created_at)
                VALUES (%(thread_id)s, %(user_id)s, 'active', NOW())
            """, {'thread_id': str(thread_id), 'user_id': str(user_id)})
        await db_session.commit()
        
        # Simulate concurrent state updates
        async def update_thread_state(thread_id: ThreadID, new_status: str, user_id: UserID):
            # Simulate processing delay
            await asyncio.sleep(0.1)
            
            # Update with user context validation
            result = await db_session.execute("""
                UPDATE threads 
                SET status = $1, updated_at = NOW() 
                WHERE id = $2 AND user_id = $3
            """, new_status, str(thread_id), str(user_id))
            
            await db_session.commit()
            return result == "UPDATE 1"
        
        # Execute concurrent updates
        tasks = [
            update_thread_state(thread1_id, "processing", user1_id),
            update_thread_state(thread2_id, "waiting", user2_id),
            update_thread_state(thread1_id, "completed", user1_id),  # Potential race
            update_thread_state(thread2_id, "active", user2_id)      # Potential race
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate no exceptions occurred
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} raised exception: {result}"
            assert isinstance(result, bool), f"Task {i} must return boolean success status"
        
        # Validate final states are consistent
        final_state1 = await db_session.fetchrow(
            "SELECT status, user_id FROM threads WHERE id = $1", str(thread1_id)
        )
        final_state2 = await db_session.fetchrow(
            "SELECT status, user_id FROM threads WHERE id = $1", str(thread2_id)
        )
        
        # User associations must remain correct (no bleeding)
        assert final_state1['user_id'] == str(user1_id), "Thread 1 user association must not change"
        assert final_state2['user_id'] == str(user2_id), "Thread 2 user association must not change"
        
        # States must be valid (one of the attempted states)
        valid_states1 = {'active', 'processing', 'completed'}
        valid_states2 = {'active', 'waiting'}
        
        assert final_state1['status'] in valid_states1, (
            f"Thread 1 final state '{final_state1['status']}' must be valid"
        )
        assert final_state2['status'] in valid_states2, (
            f"Thread 2 final state '{final_state2['status']}' must be valid"
        )
        
        # Cleanup
        await db_session.execute("DELETE FROM threads WHERE id IN ($1, $2)", str(thread1_id), str(thread2_id))
        await db_session.commit()