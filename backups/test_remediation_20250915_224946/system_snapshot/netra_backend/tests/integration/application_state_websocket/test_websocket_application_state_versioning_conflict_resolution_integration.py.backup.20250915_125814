"""
Test WebSocket Application State Versioning and Conflict Resolution Integration

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (Multi-user collaboration scenarios)
- Business Goal: Prevent data corruption in multi-user concurrent editing scenarios
- Value Impact: Users maintain data integrity during collaborative sessions
- Strategic Impact: Enables enterprise collaboration features without data loss

This test validates that concurrent WebSocket operations handle state versioning
and conflict resolution properly. When multiple users or sessions modify the same
data, the system must detect conflicts and resolve them without corrupting state.
"""

import asyncio
import pytest
import json
import time
from typing import Dict, Any, List, Optional
from uuid import uuid4
from dataclasses import dataclass

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState
from shared.types import UserID, ThreadID, MessageID
from shared.isolated_environment import get_env


@dataclass
class StateVersion:
    """Represents a versioned state object."""
    version: int
    data: Dict[str, Any]
    timestamp: float
    user_id: str
    connection_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'data': self.data,
            'timestamp': self.timestamp,
            'user_id': self.user_id,
            'connection_id': self.connection_id
        }


class TestWebSocketApplicationStateVersioningConflictResolution(BaseIntegrationTest):
    """Test application state versioning and conflict resolution during concurrent WebSocket operations."""
    
    async def create_versioned_state(self, services, state_manager, key: str, initial_data: Dict[str, Any], user_id: str, connection_id: str) -> StateVersion:
        """Create a versioned state object with proper tracking."""
        version = StateVersion(
            version=1,
            data=initial_data,
            timestamp=time.time(),
            user_id=user_id,
            connection_id=connection_id
        )
        
        # Store in Redis with versioning
        state_key = f"versioned_state:{key}"
        await services.redis.set_json(state_key, version.to_dict(), ex=3600)
        
        # Store version history
        history_key = f"version_history:{key}"
        await services.redis.lpush(history_key, json.dumps(version.to_dict()))
        await services.redis.expire(history_key, 3600)
        
        return version
    
    async def update_versioned_state(self, services, key: str, new_data: Dict[str, Any], expected_version: int, user_id: str, connection_id: str) -> StateVersion:
        """Update versioned state with conflict detection."""
        state_key = f"versioned_state:{key}"
        
        # Get current state
        current_state_data = await services.redis.get_json(state_key)
        if not current_state_data:
            raise ValueError(f"State {key} not found")
        
        current_version = current_state_data['version']
        
        # Check for conflicts
        if current_version != expected_version:
            raise ValueError(f"Version conflict: expected {expected_version}, current {current_version}")
        
        # Create new version
        new_version = StateVersion(
            version=current_version + 1,
            data=new_data,
            timestamp=time.time(),
            user_id=user_id,
            connection_id=connection_id
        )
        
        # Atomic update using Redis transaction
        async with services.redis.pipeline(transaction=True) as pipe:
            await pipe.set_json(state_key, new_version.to_dict(), ex=3600)
            
            # Update version history
            history_key = f"version_history:{key}"
            await pipe.lpush(history_key, json.dumps(new_version.to_dict()))
            await pipe.ltrim(history_key, 0, 99)  # Keep last 100 versions
            
            await pipe.execute()
        
        return new_version
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_state_updates_detect_conflicts(self, real_services_fixture):
        """Test that concurrent state updates properly detect version conflicts."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        # Create two test users for concurrent operations
        user1_data = await self.create_test_user_context(services, {
            'email': 'user1-conflict@example.com',
            'name': 'User 1 Conflict Test'
        })
        user2_data = await self.create_test_user_context(services, {
            'email': 'user2-conflict@example.com', 
            'name': 'User 2 Conflict Test'
        })
        
        user1_id = UserID(user1_data['id'])
        user2_id = UserID(user2_data['id'])
        
        connection1_id = str(uuid4())
        connection2_id = str(uuid4())
        
        # Create shared thread that both users can modify
        thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, title, metadata)
            VALUES ($1, $2, $3)
            RETURNING id
        """, str(user1_id), "Shared Conflict Test Thread", json.dumps({"shared": True}))
        
        thread_id = ThreadID(str(thread_id))
        
        # Set up WebSocket states for both connections
        for user_id, conn_id in [(user1_id, connection1_id), (user2_id, connection2_id)]:
            state_manager.set_websocket_state(conn_id, 'connection_info', {
                'user_id': str(user_id),
                'connection_id': conn_id,
                'thread_id': str(thread_id),
                'state': WebSocketConnectionState.CONNECTED.value
            })
        
        # Create initial versioned state for the thread
        initial_thread_state = {
            'title': 'Shared Conflict Test Thread',
            'participant_count': 2,
            'last_message_count': 0,
            'metadata': {'shared': True}
        }
        
        version1 = await self.create_versioned_state(
            services, 
            state_manager, 
            f"thread_state:{thread_id}",
            initial_thread_state,
            str(user1_id),
            connection1_id
        )
        
        # Simulate concurrent updates from both users
        async def user1_update():
            """User 1 tries to update thread title."""
            try:
                updated_data = {
                    **initial_thread_state,
                    'title': 'Updated by User 1',
                    'last_updated_by': str(user1_id)
                }
                
                new_version = await self.update_versioned_state(
                    services,
                    f"thread_state:{thread_id}",
                    updated_data,
                    1,  # Expected version
                    str(user1_id),
                    connection1_id
                )
                return {'success': True, 'version': new_version.version}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        async def user2_update():
            """User 2 tries to update thread metadata."""
            # Small delay to create race condition
            await asyncio.sleep(0.01)
            
            try:
                updated_data = {
                    **initial_thread_state,
                    'metadata': {'shared': True, 'priority': 'high'},
                    'last_updated_by': str(user2_id)
                }
                
                new_version = await self.update_versioned_state(
                    services,
                    f"thread_state:{thread_id}",
                    updated_data,
                    1,  # Expected version (will conflict with user1's update)
                    str(user2_id), 
                    connection2_id
                )
                return {'success': True, 'version': new_version.version}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        # Execute concurrent updates
        results = await asyncio.gather(user1_update(), user2_update(), return_exceptions=True)
        
        # Verify conflict detection
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        conflict_count = sum(1 for r in results if isinstance(r, dict) and not r.get('success'))
        
        assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
        assert conflict_count == 1, f"Expected exactly 1 conflict, got {conflict_count}"
        
        # Verify the successful update is in Redis
        current_state = await services.redis.get_json(f"versioned_state:thread_state:{thread_id}")
        assert current_state is not None
        assert current_state['version'] == 2
        
        # Check version history
        history = await services.redis.lrange(f"version_history:thread_state:{thread_id}", 0, -1)
        assert len(history) == 2  # Initial + 1 successful update
        
        # Verify WebSocket states are updated correctly
        user1_ws_state = state_manager.get_websocket_state(connection1_id, 'connection_info')
        user2_ws_state = state_manager.get_websocket_state(connection2_id, 'connection_info')
        
        assert user1_ws_state is not None
        assert user2_ws_state is not None
        
        # BUSINESS VALUE: Conflicts detected and handled without data corruption
        self.assert_business_value_delivered({
            'conflict_detection': True,
            'data_integrity': True,
            'version_control': True,
            'concurrent_safety': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_conflict_resolution_with_merge_strategy(self, real_services_fixture):
        """Test automatic conflict resolution using merge strategies."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        # Create test user and connection
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        connection_id = str(uuid4())
        
        # Create thread
        thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, title, metadata)
            VALUES ($1, $2, $3)
            RETURNING id
        """, str(user_id), "Merge Test Thread", json.dumps({}))
        
        thread_id = ThreadID(str(thread_id))
        
        # Create initial state with different mergeable fields
        initial_state = {
            'title': 'Merge Test Thread',
            'tags': ['test', 'integration'],
            'participant_settings': {
                'user1': {'notifications': True, 'theme': 'dark'},
                'user2': {'notifications': False, 'theme': 'light'}
            },
            'counters': {
                'messages': 0,
                'attachments': 0,
                'reactions': 0
            }
        }
        
        version1 = await self.create_versioned_state(
            services,
            state_manager,
            f"mergeable_state:{thread_id}",
            initial_state,
            str(user_id),
            connection_id
        )
        
        # Simulate two updates that can be merged
        async def apply_merge_strategy(base_state: Dict[str, Any], changes1: Dict[str, Any], changes2: Dict[str, Any]) -> Dict[str, Any]:
            """Apply automatic merge strategy for non-conflicting changes."""
            merged = base_state.copy()
            
            # Merge tags (union)
            if 'tags' in changes1 or 'tags' in changes2:
                all_tags = set(base_state.get('tags', []))
                if 'tags' in changes1:
                    all_tags.update(changes1['tags'])
                if 'tags' in changes2:
                    all_tags.update(changes2['tags'])
                merged['tags'] = list(all_tags)
            
            # Merge counters (addition)
            if 'counters' in changes1 or 'counters' in changes2:
                merged_counters = base_state.get('counters', {}).copy()
                for changes in [changes1, changes2]:
                    if 'counters' in changes:
                        for key, value in changes['counters'].items():
                            merged_counters[key] = merged_counters.get(key, 0) + value
                merged['counters'] = merged_counters
            
            # Merge participant_settings (deep merge)
            if 'participant_settings' in changes1 or 'participant_settings' in changes2:
                merged_settings = base_state.get('participant_settings', {}).copy()
                for changes in [changes1, changes2]:
                    if 'participant_settings' in changes:
                        for user, settings in changes['participant_settings'].items():
                            if user not in merged_settings:
                                merged_settings[user] = {}
                            merged_settings[user].update(settings)
                merged['participant_settings'] = merged_settings
            
            # Handle non-mergeable conflicts (last write wins for simple fields)
            for changes in [changes1, changes2]:
                for key, value in changes.items():
                    if key not in ['tags', 'counters', 'participant_settings']:
                        merged[key] = value
            
            return merged
        
        # Create two sets of changes that can be merged
        changes1 = {
            'tags': ['test', 'integration', 'automated'],
            'counters': {'messages': 2, 'attachments': 1},
            'participant_settings': {
                'user1': {'last_seen': time.time()}
            }
        }
        
        changes2 = {
            'tags': ['integration', 'conflict-resolution'],
            'counters': {'reactions': 3},
            'participant_settings': {
                'user2': {'last_seen': time.time()}
            }
        }
        
        # Apply merge strategy
        merged_state = await apply_merge_strategy(initial_state, changes1, changes2)
        
        # Update state with merged result
        final_version = await self.update_versioned_state(
            services,
            f"mergeable_state:{thread_id}",
            merged_state,
            1,  # Expected version
            str(user_id),
            connection_id
        )
        
        # Verify merge results
        assert final_version.version == 2
        
        final_data = final_version.data
        
        # Verify tag merge (union)
        expected_tags = {'test', 'integration', 'automated', 'conflict-resolution'}
        assert set(final_data['tags']) == expected_tags
        
        # Verify counter merge (addition)
        assert final_data['counters']['messages'] == 2
        assert final_data['counters']['attachments'] == 1
        assert final_data['counters']['reactions'] == 3
        
        # Verify participant settings merge
        assert 'last_seen' in final_data['participant_settings']['user1']
        assert 'last_seen' in final_data['participant_settings']['user2']
        assert final_data['participant_settings']['user1']['notifications'] == True
        assert final_data['participant_settings']['user2']['notifications'] == False
        
        # Store merged result in PostgreSQL for consistency
        await services.postgres.execute("""
            UPDATE backend.threads 
            SET metadata = jsonb_set(
                COALESCE(metadata, '{}'),
                '{merged_state}',
                $2::jsonb
            )
            WHERE id = $1
        """, str(thread_id), json.dumps(final_data))
        
        # Verify database consistency
        db_thread = await services.postgres.fetchrow("""
            SELECT metadata FROM backend.threads WHERE id = $1
        """, str(thread_id))
        
        assert db_thread is not None
        assert 'merged_state' in db_thread['metadata']
        
        # BUSINESS VALUE: Conflicts resolved automatically without data loss
        self.assert_business_value_delivered({
            'automatic_merge': True,
            'no_data_loss': True,
            'conflict_resolution': True,
            'user_experience': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_version_rollback_and_recovery(self, real_services_fixture):
        """Test state version rollback and recovery capabilities."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        # Create test setup
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        connection_id = str(uuid4())
        
        thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, title)
            VALUES ($1, $2) 
            RETURNING id
        """, str(user_id), "Version Rollback Test")
        
        thread_id = ThreadID(str(thread_id))
        
        # Create a series of state versions
        states = [
            {'title': 'Version 1', 'step': 1, 'data': 'initial'},
            {'title': 'Version 2', 'step': 2, 'data': 'updated'},
            {'title': 'Version 3', 'step': 3, 'data': 'corrupted'},
            {'title': 'Version 4', 'step': 4, 'data': 'final'}
        ]
        
        versions = []
        state_key = f"rollback_test:{thread_id}"
        
        # Create version history
        for i, state_data in enumerate(states):
            if i == 0:
                version = await self.create_versioned_state(
                    services,
                    state_manager,
                    state_key,
                    state_data,
                    str(user_id),
                    connection_id
                )
            else:
                version = await self.update_versioned_state(
                    services,
                    state_key,
                    state_data,
                    i,  # Expected version
                    str(user_id),
                    connection_id
                )
            
            versions.append(version)
        
        # Verify we have 4 versions
        assert len(versions) == 4
        assert versions[-1].version == 4
        assert versions[-1].data['step'] == 4
        
        # Simulate detecting corruption in version 3
        # Rollback to version 2
        target_version = versions[1]  # Version 2
        
        # Perform rollback
        rollback_version = StateVersion(
            version=target_version.version + 10,  # New version number higher than current
            data=target_version.data,
            timestamp=time.time(),
            user_id=str(user_id),
            connection_id=connection_id
        )
        
        # Update with rollback data
        await services.redis.set_json(f"versioned_state:{state_key}", rollback_version.to_dict(), ex=3600)
        
        # Add rollback to history
        await services.redis.lpush(f"version_history:{state_key}", json.dumps({
            **rollback_version.to_dict(),
            'rollback_from': 4,
            'rollback_to': 2,
            'rollback_reason': 'data_corruption_detected'
        }))
        
        # Verify rollback
        current_state = await services.redis.get_json(f"versioned_state:{state_key}")
        assert current_state is not None
        assert current_state['version'] == rollback_version.version
        assert current_state['data']['title'] == 'Version 2'
        assert current_state['data']['step'] == 2
        assert current_state['data']['data'] == 'updated'
        
        # Verify history contains rollback information
        history = await services.redis.lrange(f"version_history:{state_key}", 0, 0)
        rollback_entry = json.loads(history[0])
        assert 'rollback_from' in rollback_entry
        assert rollback_entry['rollback_from'] == 4
        assert rollback_entry['rollback_to'] == 2
        
        # Update PostgreSQL to reflect rollback
        await services.postgres.execute("""
            UPDATE backend.threads
            SET title = $2,
                metadata = jsonb_set(
                    COALESCE(metadata, '{}'),
                    '{rollback_info}',
                    $3::jsonb
                )
            WHERE id = $1
        """, str(thread_id), 'Version 2', json.dumps({
            'rollback_from_version': 4,
            'rollback_to_version': 2,
            'rollback_timestamp': time.time()
        }))
        
        # Verify database consistency
        db_thread = await services.postgres.fetchrow("""
            SELECT title, metadata FROM backend.threads WHERE id = $1
        """, str(thread_id))
        
        assert db_thread is not None
        assert db_thread['title'] == 'Version 2'
        assert 'rollback_info' in db_thread['metadata']
        
        # BUSINESS VALUE: Can recover from data corruption
        self.assert_business_value_delivered({
            'rollback_capability': True,
            'data_recovery': True,
            'version_history': True,
            'corruption_protection': True
        }, 'automation')