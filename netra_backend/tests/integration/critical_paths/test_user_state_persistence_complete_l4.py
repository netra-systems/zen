"""
L4 Integration Test: User State Persistence Complete
Tests user state persistence across services, restarts, and failures
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
import pickle

from netra_backend.app.services.user_service import UserService
from netra_backend.app.services.session_service import SessionService
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.services.database_service import DatabaseService
from netra_backend.app.models.user import User, UserState, UserPreferences
from netra_backend.app.core.config import settings


class TestUserStatePersistenceCompleteL4:
    """Complete user state persistence testing"""
    
    @pytest.fixture
    async def persistence_stack(self):
        """Persistence infrastructure setup"""
        return {
            'user_service': UserService(),
            'session_service': SessionService(),
            'redis_service': RedisService(),
            'db_service': DatabaseService(),
            'state_snapshots': {},
            'sync_queue': [],
            'conflict_log': []
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_user_state_across_service_restart(self, persistence_stack):
        """Test user state persistence across service restart"""
        user_id = "user_restart_test"
        
        # Create user with complex state
        user_state = {
            'preferences': {
                'theme': 'dark',
                'language': 'en',
                'notifications': {
                    'email': True,
                    'push': False,
                    'frequency': 'daily'
                }
            },
            'workspace': {
                'current_project': 'project_123',
                'open_files': ['file1.py', 'file2.js'],
                'cursor_positions': {'file1.py': 42, 'file2.js': 100}
            },
            'session_data': {
                'last_activity': datetime.utcnow().isoformat(),
                'active_features': ['ai_assist', 'code_review'],
                'usage_credits': 1000
            }
        }
        
        # Save state
        await persistence_stack['user_service'].save_user_state(user_id, user_state)
        
        # Simulate service restart by clearing in-memory cache
        persistence_stack['user_service']._cache.clear()
        
        # Restore state
        restored_state = await persistence_stack['user_service'].get_user_state(user_id)
        
        # Verify complete state restoration
        assert restored_state['preferences']['theme'] == 'dark'
        assert restored_state['workspace']['current_project'] == 'project_123'
        assert len(restored_state['workspace']['open_files']) == 2
        assert restored_state['session_data']['usage_credits'] == 1000
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_user_preferences_sync_across_devices(self, persistence_stack):
        """Test user preferences synchronization across multiple devices"""
        user_id = "user_multi_device"
        
        # Device 1 updates preferences
        device1_prefs = {
            'theme': 'dark',
            'font_size': 14,
            'auto_save': True
        }
        
        await persistence_stack['user_service'].update_preferences(
            user_id=user_id,
            device_id="device_1",
            preferences=device1_prefs
        )
        
        # Device 2 updates different preferences
        device2_prefs = {
            'language': 'es',
            'timezone': 'UTC-5'
        }
        
        await persistence_stack['user_service'].update_preferences(
            user_id=user_id,
            device_id="device_2",
            preferences=device2_prefs
        )
        
        # Device 3 should see merged preferences
        merged_prefs = await persistence_stack['user_service'].get_preferences(
            user_id=user_id,
            device_id="device_3"
        )
        
        assert merged_prefs['theme'] == 'dark'
        assert merged_prefs['font_size'] == 14
        assert merged_prefs['language'] == 'es'
        assert merged_prefs['timezone'] == 'UTC-5'
        
        # Test conflict resolution when same key updated
        await persistence_stack['user_service'].update_preferences(
            user_id=user_id,
            device_id="device_1",
            preferences={'theme': 'light'},
            timestamp=time.time()
        )
        
        await persistence_stack['user_service'].update_preferences(
            user_id=user_id,
            device_id="device_2",
            preferences={'theme': 'auto'},
            timestamp=time.time() + 1  # Later timestamp wins
        )
        
        final_prefs = await persistence_stack['user_service'].get_preferences(user_id)
        assert final_prefs['theme'] == 'auto'  # Latest update wins
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_user_state_during_database_failure(self, persistence_stack):
        """Test user state persistence during database failure"""
        user_id = "user_db_failure"
        
        # Create initial state
        initial_state = {
            'level': 5,
            'experience': 2500,
            'achievements': ['first_login', 'week_streak'],
            'inventory': {'coins': 100, 'gems': 10}
        }
        
        await persistence_stack['user_service'].save_user_state(user_id, initial_state)
        
        # Simulate database failure
        original_db = persistence_stack['db_service']
        persistence_stack['db_service'] = None
        
        # Updates should go to Redis cache
        update_state = {
            'level': 6,
            'experience': 3000,
            'achievements': ['first_login', 'week_streak', 'level_up']
        }
        
        await persistence_stack['user_service'].save_user_state(user_id, update_state)
        
        # State should be retrievable from cache
        cached_state = await persistence_stack['user_service'].get_user_state(user_id)
        assert cached_state['level'] == 6
        assert 'level_up' in cached_state['achievements']
        
        # Restore database
        persistence_stack['db_service'] = original_db
        
        # Sync cache to database
        await persistence_stack['user_service'].sync_cache_to_database(user_id)
        
        # Verify state persisted to database
        db_state = await persistence_stack['db_service'].get_user_state(user_id)
        assert db_state['level'] == 6
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_user_activity_tracking_persistence(self, persistence_stack):
        """Test user activity tracking and persistence"""
        user_id = "user_activity"
        
        # Track various activities
        activities = [
            {'type': 'login', 'timestamp': time.time(), 'ip': '192.168.1.1'},
            {'type': 'page_view', 'page': '/dashboard', 'duration': 30},
            {'type': 'feature_use', 'feature': 'ai_chat', 'tokens_used': 100},
            {'type': 'file_edit', 'file': 'main.py', 'changes': 42},
            {'type': 'logout', 'timestamp': time.time() + 3600}
        ]
        
        for activity in activities:
            await persistence_stack['user_service'].track_activity(user_id, activity)
        
        # Retrieve activity history
        history = await persistence_stack['user_service'].get_activity_history(
            user_id=user_id,
            limit=10
        )
        
        assert len(history) == len(activities)
        assert history[0]['type'] == 'login'
        assert history[-1]['type'] == 'logout'
        
        # Test activity aggregation
        stats = await persistence_stack['user_service'].get_activity_stats(
            user_id=user_id,
            period='day'
        )
        
        assert stats['total_activities'] == len(activities)
        assert stats['unique_features_used'] == 1
        assert stats['total_tokens_used'] == 100
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_user_state_versioning(self, persistence_stack):
        """Test user state versioning and rollback"""
        user_id = "user_versioning"
        
        # Create version history
        versions = []
        for i in range(5):
            state = {
                'version': i + 1,
                'data': f'state_v{i + 1}',
                'timestamp': time.time() + i
            }
            
            version_id = await persistence_stack['user_service'].save_user_state_version(
                user_id=user_id,
                state=state
            )
            versions.append(version_id)
        
        # Get current version
        current = await persistence_stack['user_service'].get_user_state(user_id)
        assert current['version'] == 5
        
        # Rollback to version 3
        await persistence_stack['user_service'].rollback_user_state(
            user_id=user_id,
            version_id=versions[2]
        )
        
        # Verify rollback
        rolled_back = await persistence_stack['user_service'].get_user_state(user_id)
        assert rolled_back['version'] == 3
        assert rolled_back['data'] == 'state_v3'
        
        # Version history should be preserved
        history = await persistence_stack['user_service'].get_state_version_history(user_id)
        assert len(history) >= 5
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_user_state_bulk_operations(self, persistence_stack):
        """Test bulk user state operations"""
        user_ids = [f"user_bulk_{i}" for i in range(100)]
        
        # Bulk create user states
        states = {}
        for user_id in user_ids:
            states[user_id] = {
                'credits': 100,
                'tier': 'free',
                'created_at': time.time()
            }
        
        # Bulk save
        start_time = time.time()
        await persistence_stack['user_service'].bulk_save_states(states)
        save_time = time.time() - start_time
        
        # Should be efficient (< 1 second for 100 users)
        assert save_time < 1.0
        
        # Bulk update
        updates = {user_id: {'credits': 200} for user_id in user_ids[:50]}
        await persistence_stack['user_service'].bulk_update_states(updates)
        
        # Verify updates
        updated_states = await persistence_stack['user_service'].bulk_get_states(user_ids[:50])
        for user_id, state in updated_states.items():
            assert state['credits'] == 200
        
        # Non-updated should remain unchanged
        unchanged_states = await persistence_stack['user_service'].bulk_get_states(user_ids[50:])
        for user_id, state in unchanged_states.items():
            assert state['credits'] == 100
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_user_state_expiry_and_cleanup(self, persistence_stack):
        """Test user state expiry and cleanup mechanisms"""
        user_id = "user_expiry"
        
        # Create temporary state with TTL
        temp_state = {
            'session_token': 'temp_token_123',
            'verification_code': '123456',
            'ttl': 5  # 5 seconds
        }
        
        await persistence_stack['user_service'].save_temporary_state(
            user_id=user_id,
            state=temp_state,
            ttl=5
        )
        
        # State should exist initially
        retrieved = await persistence_stack['user_service'].get_temporary_state(user_id)
        assert retrieved['session_token'] == 'temp_token_123'
        
        # Wait for expiry
        await asyncio.sleep(6)
        
        # State should be expired
        expired = await persistence_stack['user_service'].get_temporary_state(user_id)
        assert expired is None
        
        # Test cleanup of old states
        old_user_ids = [f"old_user_{i}" for i in range(10)]
        for uid in old_user_ids:
            await persistence_stack['user_service'].save_user_state(
                uid,
                {'last_seen': time.time() - 86400 * 90}  # 90 days old
            )
        
        # Run cleanup
        cleaned = await persistence_stack['user_service'].cleanup_inactive_states(
            inactive_days=30
        )
        
        assert cleaned >= len(old_user_ids)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_user_state_migration(self, persistence_stack):
        """Test user state migration between schema versions"""
        user_id = "user_migration"
        
        # Old schema state
        old_state = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'settings': {
                'theme': 'dark'
            }
        }
        
        # Save with old schema
        await persistence_stack['db_service'].save_raw_state(user_id, old_state)
        
        # Define migration
        async def migrate_v1_to_v2(state):
            return {
                'profile': {
                    'name': state.get('name'),
                    'email': state.get('email')
                },
                'preferences': state.get('settings', {}),
                'schema_version': 2
            }
        
        # Apply migration
        await persistence_stack['user_service'].migrate_user_state(
            user_id=user_id,
            migration_func=migrate_v1_to_v2
        )
        
        # Verify migrated state
        migrated = await persistence_stack['user_service'].get_user_state(user_id)
        assert migrated['schema_version'] == 2
        assert migrated['profile']['name'] == 'John Doe'
        assert migrated['preferences']['theme'] == 'dark'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_user_state_consistency_validation(self, persistence_stack):
        """Test user state consistency validation and repair"""
        user_id = "user_consistency"
        
        # Create inconsistent state
        inconsistent_state = {
            'balance': -100,  # Invalid negative
            'level': 0,  # Invalid zero
            'achievements': ['dup', 'dup'],  # Duplicates
            'inventory': None,  # Should be dict
            'last_login': 'invalid_date'  # Invalid format
        }
        
        # Save inconsistent state directly
        await persistence_stack['redis_service'].set(
            f"user_state:{user_id}",
            json.dumps(inconsistent_state)
        )
        
        # Validate and repair
        validation_result = await persistence_stack['user_service'].validate_and_repair_state(
            user_id=user_id
        )
        
        assert not validation_result['was_valid']
        assert len(validation_result['errors']) > 0
        assert validation_result['repaired']
        
        # Get repaired state
        repaired = await persistence_stack['user_service'].get_user_state(user_id)
        assert repaired['balance'] >= 0
        assert repaired['level'] >= 1
        assert len(repaired['achievements']) == len(set(repaired['achievements']))
        assert isinstance(repaired['inventory'], dict)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_user_state_atomic_operations(self, persistence_stack):
        """Test atomic operations on user state"""
        user_id = "user_atomic"
        
        # Initialize state
        initial_state = {
            'counter': 0,
            'balance': 1000,
            'items': []
        }
        
        await persistence_stack['user_service'].save_user_state(user_id, initial_state)
        
        # Concurrent atomic increments
        async def increment_counter():
            return await persistence_stack['user_service'].atomic_increment(
                user_id=user_id,
                field='counter',
                amount=1
            )
        
        # Launch 100 concurrent increments
        tasks = [asyncio.create_task(increment_counter()) for _ in range(100)]
        await asyncio.gather(*tasks)
        
        # Counter should be exactly 100
        final_state = await persistence_stack['user_service'].get_user_state(user_id)
        assert final_state['counter'] == 100
        
        # Test atomic balance transfer
        user2_id = "user_atomic_2"
        await persistence_stack['user_service'].save_user_state(
            user2_id,
            {'balance': 500}
        )
        
        # Atomic transfer
        transfer_result = await persistence_stack['user_service'].atomic_transfer(
            from_user=user_id,
            to_user=user2_id,
            field='balance',
            amount=300
        )
        
        assert transfer_result['success']
        
        # Verify balances
        state1 = await persistence_stack['user_service'].get_user_state(user_id)
        state2 = await persistence_stack['user_service'].get_user_state(user2_id)
        
        assert state1['balance'] == 700
        assert state2['balance'] == 800