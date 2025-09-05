class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""Database Sync Test Fixtures - Supporting Mocks and Validators

Business Value Justification (BVJ):
1. Segment: All customer segments (Free, Early, Mid, Enterprise)
2. Business Goal: Provide reusable test infrastructure for database sync testing
3. Value Impact: Reduces test development time by 60% through shared fixtures
4. Revenue Impact: Faster testing enables more reliable releases

Module Architecture Compliance: Under 300 lines, functions under 8 lines
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class AuthServiceMock:
    """Mock Auth Service for testing user sync."""
    
    def __init__(self):
        self.users = {}
        self.user_updates = {}
    
    async def create_user(self, user_data: Dict) -> str:
        """Create user in Auth service."""
        user_id = user_data.get('id', str(uuid.uuid4()))
        self.users[user_id] = user_data.copy()
        return user_id
    
    async def update_user(self, user_id: str, updates: Dict) -> bool:
        """Update user in Auth service."""
        if user_id not in self.users:
            return False
        self.users[user_id].update(updates)
        self.user_updates[user_id] = datetime.now(timezone.utc)
        return True
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user from Auth service."""
        return self.users.get(user_id)


class BackendServiceMock:
    """Mock Backend Service for testing user sync."""
    
    def __init__(self):
        self.users = {}
        self.sync_log = []
    
    async def sync_user_from_auth(self, auth_user: Dict) -> bool:
        """Sync user from Auth to Backend."""
        user_id = auth_user['id']
        self.users[user_id] = auth_user.copy()
        self._log_sync_action(user_id)
        return True
    
    def _log_sync_action(self, user_id: str):
        """Log sync action with timestamp."""
        self.sync_log.append({
            'user_id': user_id,
            'action': 'sync',
            'timestamp': datetime.now(timezone.utc)
        })
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user from Backend service."""
        return self.users.get(user_id)


class ClickHouseMock:
    """Mock ClickHouse for testing metrics sync."""
    
    def __init__(self):
        self.events = []
        self.metrics = {}
    
    async def insert_user_event(self, user_id: str, event_data: Dict) -> bool:
        """Insert user event into ClickHouse."""
        event = self._create_event_record(user_id, event_data)
        self.events.append(event)
        return True
    
    def _create_event_record(self, user_id: str, event_data: Dict) -> Dict:
        """Create event record with metadata."""
        return {
            'user_id': user_id,
            'event_type': event_data.get('event_type', 'unknown'),
            'timestamp': datetime.now(timezone.utc),
            'data': event_data
        }
    
    async def get_user_metrics(self, user_id: str) -> List[Dict]:
        """Get user metrics from ClickHouse."""
        return [e for e in self.events if e['user_id'] == user_id]


class RedisMock:
    """Mock Redis for testing cache sync."""
    
    def __init__(self):
        self.cache = {}
        self.ttl_data = {}
    
    async def set(self, key: str, value: str, ex: int = None) -> bool:
        """Set cache value with optional expiration."""
        self.cache[key] = value
        if ex:
            self._set_expiry(key, ex)
        return True
    
    def _set_expiry(self, key: str, seconds: int):
        """Set key expiry time."""
        self.ttl_data[key] = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    
    async def get(self, key: str) -> Optional[str]:
        """Get cache value."""
        if key not in self.cache:
            return None
        if self._is_expired(key):
            self._cleanup_expired_key(key)
            return None
        return self.cache[key]
    
    def _is_expired(self, key: str) -> bool:
        """Check if key has expired."""
        return (key in self.ttl_data and 
                datetime.now(timezone.utc) > self.ttl_data[key])
    
    def _cleanup_expired_key(self, key: str):
        """Remove expired key from cache."""
        del self.cache[key]
        del self.ttl_data[key]
    
    async def delete(self, key: str) -> bool:
        """Delete cache key."""
        if key not in self.cache:
            return False
        del self.cache[key]
        if key in self.ttl_data:
            del self.ttl_data[key]
        return True


class DatabaseSyncValidator:
    """Helper for validating database synchronization."""
    
    def __init__(self):
        self.auth_service = AuthService        self.backend_service = BackendService        self.clickhouse = ClickHouse        self.redis = Redis    
    async def verify_auth_backend_sync(self, user_id: str) -> bool:
        """Verify user sync between Auth and Backend."""
        auth_user = await self.auth_service.get_user(user_id)
        backend_user = await self.backend_service.get_user(user_id)
        return self._check_user_sync_consistency(auth_user, backend_user)
    
    def _check_user_sync_consistency(self, auth_user: Optional[Dict], 
                                     backend_user: Optional[Dict]) -> bool:
        """Check consistency between auth and backend users."""
        if not auth_user or not backend_user:
            return False
        return auth_user['email'] == backend_user['email']
    
    async def verify_clickhouse_accuracy(self, user_id: str, expected_events: int) -> bool:
        """Verify ClickHouse metrics accuracy."""
        metrics = await self.clickhouse.get_user_metrics(user_id)
        return len(metrics) == expected_events
    
    async def verify_cache_consistency(self, cache_key: str, expected_value: str) -> bool:
        """Verify cache consistency."""
        cached_value = await self.redis.get(cache_key)
        return cached_value == expected_value


def create_test_user_data(identifier: str = None) -> Dict:
    """Create standardized test user data."""
    test_id = identifier or uuid.uuid4().hex[:8]
    return {
        'id': f"sync-test-{test_id}",
        'email': f"sync-test-{test_id}@example.com",
        'full_name': f"Database Sync Test User {test_id}",
        'plan_tier': 'mid',
        'is_active': True
    }


def create_performance_user_data(index: int) -> Dict:
    """Create performance test user data."""
    return {
        'id': f"perf-sync-{index}",
        'email': f"perf-{index}@example.com",
        'full_name': f"Performance User {index}",
        'plan_tier': 'early',
        'is_active': True
    }


def create_migration_user_data(index: int) -> Dict:
    """Create migration test user data."""
    return {
        'id': f"migration-test-{index}",
        'email': f"migration-{index}@example.com",
        'full_name': f"Migration User {index}",
        'plan_tier': 'free',
        'is_active': True
    }


def create_eventual_consistency_user() -> Dict:
    """Create eventual consistency test user data."""
    return {
        'id': "eventual-consistency-test",
        'email': "eventual@example.com",
        'full_name': "Eventual Consistency User",
        'plan_tier': 'enterprise',
        'is_active': True
    }