"""
Test WebSocket Application State Distributed State Consistency Checks Integration

Business Value Justification (BVJ):
- Segment: Enterprise (Large-scale deployments)
- Business Goal: Ensure data consistency across distributed system components and background processes
- Value Impact: Enterprise customers can trust system reliability at scale
- Strategic Impact: Foundation for horizontal scaling and enterprise deployment

This test validates that application state remains consistent across distributed
system components, including WebSocket events, background processes, scheduled
tasks, and multiple service instances. The system must detect and resolve
consistency issues automatically.
"""

import asyncio
import pytest
import json
import time
import random
from typing import Dict, Any, List, Optional, Set, Tuple
from uuid import uuid4
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState
from shared.types import UserID, ThreadID, MessageID
from shared.isolated_environment import get_env


class ConsistencyViolationType(Enum):
    """Types of consistency violations that can occur."""
    POSTGRES_REDIS_MISMATCH = "postgres_redis_mismatch"
    WEBSOCKET_DATABASE_MISMATCH = "websocket_database_mismatch"
    STALE_CACHE_DATA = "stale_cache_data"
    ORPHANED_RESOURCES = "orphaned_resources"
    DUPLICATE_RESOURCES = "duplicate_resources"
    MISSING_REFERENCES = "missing_references"
    CONCURRENT_MODIFICATION_CONFLICT = "concurrent_modification_conflict"
    BACKGROUND_PROCESS_INCONSISTENCY = "background_process_inconsistency"


@dataclass
class ConsistencyViolation:
    """Represents a detected consistency violation."""
    violation_type: ConsistencyViolationType
    resource_type: str
    resource_id: str
    description: str
    detected_at: float
    severity: str  # 'low', 'medium', 'high', 'critical'
    expected_state: Optional[Dict[str, Any]] = None
    actual_state: Optional[Dict[str, Any]] = None
    affected_users: List[str] = field(default_factory=list)
    resolution_required: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'violation_type': self.violation_type.value,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'description': self.description,
            'detected_at': self.detected_at,
            'severity': self.severity,
            'expected_state': self.expected_state,
            'actual_state': self.actual_state,
            'affected_users': self.affected_users,
            'resolution_required': self.resolution_required
        }


class DistributedConsistencyChecker:
    """Performs distributed state consistency checks across all system components."""
    
    def __init__(self, services, state_manager):
        self.services = services
        self.state_manager = state_manager
        self.violations: List[ConsistencyViolation] = []
        self.consistency_metrics = {
            'checks_performed': 0,
            'violations_detected': 0,
            'violations_resolved': 0,
            'check_duration_seconds': 0.0
        }
    
    async def perform_comprehensive_consistency_check(self, 
                                                    user_ids: List[str],
                                                    thread_ids: List[str],
                                                    message_ids: List[str]) -> Dict[str, Any]:
        """Perform comprehensive consistency check across all components."""
        check_start_time = time.time()
        
        # Check 1: PostgreSQL vs Redis consistency
        await self._check_postgres_redis_consistency(thread_ids, message_ids)
        
        # Check 2: WebSocket vs Database consistency
        await self._check_websocket_database_consistency(user_ids, thread_ids)
        
        # Check 3: Cache staleness detection
        await self._check_cache_staleness(thread_ids, message_ids)
        
        # Check 4: Orphaned resource detection
        await self._check_orphaned_resources(user_ids, thread_ids, message_ids)
        
        # Check 5: Duplicate resource detection
        await self._check_duplicate_resources(thread_ids, message_ids)
        
        # Check 6: Reference integrity validation
        await self._check_reference_integrity(thread_ids, message_ids)
        
        # Check 7: Concurrent modification conflicts
        await self._check_concurrent_modification_conflicts(thread_ids)
        
        # Check 8: Background process consistency
        await self._check_background_process_consistency(user_ids, thread_ids)
        
        check_end_time = time.time()
        self.consistency_metrics['check_duration_seconds'] = check_end_time - check_start_time
        self.consistency_metrics['checks_performed'] += 1
        self.consistency_metrics['violations_detected'] = len(self.violations)
        
        return {
            'violations_found': len(self.violations),
            'violations': [v.to_dict() for v in self.violations],
            'consistency_score': self._calculate_consistency_score(),
            'metrics': self.consistency_metrics.copy()
        }
    
    async def _check_postgres_redis_consistency(self, thread_ids: List[str], message_ids: List[str]):
        """Check consistency between PostgreSQL and Redis."""
        # Check threads
        for thread_id in thread_ids:
            # Get from PostgreSQL
            db_thread = await self.services.postgres.fetchrow("""
                SELECT id, user_id, title, metadata, updated_at
                FROM backend.threads WHERE id = $1
            """, thread_id)
            
            # Get from Redis
            cached_thread = await self.services.redis.get_json(f"thread:{thread_id}")
            
            if db_thread and not cached_thread:
                self.violations.append(ConsistencyViolation(
                    violation_type=ConsistencyViolationType.POSTGRES_REDIS_MISMATCH,
                    resource_type='thread',
                    resource_id=thread_id,
                    description='Thread exists in PostgreSQL but missing from Redis cache',
                    detected_at=time.time(),
                    severity='medium',
                    expected_state={'cached': True},
                    actual_state={'cached': False}
                ))
            
            elif db_thread and cached_thread:
                # Check for data inconsistencies
                if cached_thread.get('title') != db_thread['title']:
                    self.violations.append(ConsistencyViolation(
                        violation_type=ConsistencyViolationType.POSTGRES_REDIS_MISMATCH,
                        resource_type='thread',
                        resource_id=thread_id,
                        description=f'Thread title mismatch: DB="{db_thread["title"]}", Cache="{cached_thread.get("title")}"',
                        detected_at=time.time(),
                        severity='high',
                        expected_state={'title': db_thread['title']},
                        actual_state={'title': cached_thread.get('title')}
                    ))
                
                if cached_thread.get('user_id') != str(db_thread['user_id']):
                    self.violations.append(ConsistencyViolation(
                        violation_type=ConsistencyViolationType.POSTGRES_REDIS_MISMATCH,
                        resource_type='thread',
                        resource_id=thread_id,
                        description='Thread user_id mismatch between PostgreSQL and Redis',
                        detected_at=time.time(),
                        severity='critical',
                        expected_state={'user_id': str(db_thread['user_id'])},
                        actual_state={'user_id': cached_thread.get('user_id')},
                        affected_users=[str(db_thread['user_id'])]
                    ))
            
            elif not db_thread and cached_thread:
                self.violations.append(ConsistencyViolation(
                    violation_type=ConsistencyViolationType.POSTGRES_REDIS_MISMATCH,
                    resource_type='thread',
                    resource_id=thread_id,
                    description='Thread exists in Redis cache but missing from PostgreSQL',
                    detected_at=time.time(),
                    severity='critical',
                    expected_state={'exists': False},
                    actual_state={'cached': True},
                    affected_users=[cached_thread.get('user_id')] if cached_thread.get('user_id') else []
                ))
        
        # Check messages
        for message_id in message_ids:
            db_message = await self.services.postgres.fetchrow("""
                SELECT id, thread_id, user_id, content, role
                FROM backend.messages WHERE id = $1
            """, message_id)
            
            cached_message = await self.services.redis.get_json(f"message:{message_id}")
            
            if db_message and cached_message:
                # Check for content inconsistencies
                if cached_message.get('content') != db_message['content']:
                    self.violations.append(ConsistencyViolation(
                        violation_type=ConsistencyViolationType.POSTGRES_REDIS_MISMATCH,
                        resource_type='message',
                        resource_id=message_id,
                        description='Message content mismatch between PostgreSQL and Redis',
                        detected_at=time.time(),
                        severity='high',
                        expected_state={'content': db_message['content']},
                        actual_state={'content': cached_message.get('content')},
                        affected_users=[str(db_message['user_id'])]
                    ))
    
    async def _check_websocket_database_consistency(self, user_ids: List[str], thread_ids: List[str]):
        """Check consistency between WebSocket state and database."""
        for user_id in user_ids:
            # Find all connections for this user
            # In a real system, we'd have a registry of active connections
            # For testing, we'll simulate checking known connection patterns
            
            # Get user's threads from database
            user_threads = await self.services.postgres.fetch("""
                SELECT id FROM backend.threads WHERE user_id = $1
            """, user_id)
            
            db_thread_ids = set(str(t['id']) for t in user_threads)
            
            # Simulate checking WebSocket states for this user
            # In practice, you'd iterate through active connections
            mock_connection_ids = [f"conn_{user_id}_{i}" for i in range(2)]  # Simulate 2 connections per user
            
            for connection_id in mock_connection_ids:
                ws_state = self.state_manager.get_websocket_state(connection_id, 'connection_info')
                
                if ws_state:
                    ws_user_id = ws_state.get('user_id')
                    if ws_user_id != user_id:
                        self.violations.append(ConsistencyViolation(
                            violation_type=ConsistencyViolationType.WEBSOCKET_DATABASE_MISMATCH,
                            resource_type='websocket',
                            resource_id=connection_id,
                            description=f'WebSocket user_id mismatch: expected {user_id}, got {ws_user_id}',
                            detected_at=time.time(),
                            severity='critical',
                            expected_state={'user_id': user_id},
                            actual_state={'user_id': ws_user_id},
                            affected_users=[user_id]
                        ))
                    
                    # Check if current_thread_id is valid
                    current_thread_id = ws_state.get('current_thread_id')
                    if current_thread_id and current_thread_id not in db_thread_ids:
                        self.violations.append(ConsistencyViolation(
                            violation_type=ConsistencyViolationType.WEBSOCKET_DATABASE_MISMATCH,
                            resource_type='websocket',
                            resource_id=connection_id,
                            description=f'WebSocket references non-existent thread: {current_thread_id}',
                            detected_at=time.time(),
                            severity='high',
                            expected_state={'valid_thread_reference': True},
                            actual_state={'thread_exists': False},
                            affected_users=[user_id]
                        ))
    
    async def _check_cache_staleness(self, thread_ids: List[str], message_ids: List[str]):
        """Check for stale cache data."""
        staleness_threshold = 3600  # 1 hour in seconds
        current_time = time.time()
        
        for thread_id in thread_ids:
            cached_thread = await self.services.redis.get_json(f"thread:{thread_id}")
            
            if cached_thread:
                cached_at = cached_thread.get('cached_at', 0)
                if current_time - cached_at > staleness_threshold:
                    # Check if database has been updated since cache
                    db_thread = await self.services.postgres.fetchrow("""
                        SELECT updated_at FROM backend.threads WHERE id = $1
                    """, thread_id)
                    
                    if db_thread:
                        db_updated_at = db_thread['updated_at'].timestamp()
                        if db_updated_at > cached_at:
                            self.violations.append(ConsistencyViolation(
                                violation_type=ConsistencyViolationType.STALE_CACHE_DATA,
                                resource_type='thread',
                                resource_id=thread_id,
                                description=f'Stale cache: DB updated at {db_updated_at}, cached at {cached_at}',
                                detected_at=time.time(),
                                severity='medium',
                                expected_state={'cache_fresh': True},
                                actual_state={'stale_duration_seconds': current_time - cached_at}
                            ))
    
    async def _check_orphaned_resources(self, user_ids: List[str], thread_ids: List[str], message_ids: List[str]):
        """Check for orphaned resources."""
        # Check for messages without valid threads
        orphaned_messages = await self.services.postgres.fetch("""
            SELECT m.id, m.thread_id
            FROM backend.messages m
            LEFT JOIN backend.threads t ON m.thread_id = t.id
            WHERE t.id IS NULL AND m.id = ANY($1)
        """, message_ids)
        
        for orphaned_msg in orphaned_messages:
            self.violations.append(ConsistencyViolation(
                violation_type=ConsistencyViolationType.ORPHANED_RESOURCES,
                resource_type='message',
                resource_id=str(orphaned_msg['id']),
                description=f'Orphaned message: references non-existent thread {orphaned_msg["thread_id"]}',
                detected_at=time.time(),
                severity='high',
                expected_state={'valid_thread_reference': True},
                actual_state={'thread_exists': False},
                resolution_required=True
            ))
        
        # Check for threads without valid users
        orphaned_threads = await self.services.postgres.fetch("""
            SELECT t.id, t.user_id
            FROM backend.threads t
            LEFT JOIN auth.users u ON t.user_id = u.id
            WHERE u.id IS NULL AND t.id = ANY($1)
        """, thread_ids)
        
        for orphaned_thread in orphaned_threads:
            self.violations.append(ConsistencyViolation(
                violation_type=ConsistencyViolationType.ORPHANED_RESOURCES,
                resource_type='thread',
                resource_id=str(orphaned_thread['id']),
                description=f'Orphaned thread: references non-existent user {orphaned_thread["user_id"]}',
                detected_at=time.time(),
                severity='critical',
                expected_state={'valid_user_reference': True},
                actual_state={'user_exists': False},
                resolution_required=True
            ))
    
    async def _check_duplicate_resources(self, thread_ids: List[str], message_ids: List[str]):
        """Check for duplicate resources."""
        # Check for duplicate cache entries
        for thread_id in thread_ids:
            cache_keys = [
                f"thread:{thread_id}",
                f"thread_cache:{thread_id}",
                f"cached_thread_{thread_id}"
            ]
            
            existing_keys = []
            for key in cache_keys:
                if await self.services.redis.exists(key):
                    existing_keys.append(key)
            
            if len(existing_keys) > 1:
                self.violations.append(ConsistencyViolation(
                    violation_type=ConsistencyViolationType.DUPLICATE_RESOURCES,
                    resource_type='thread_cache',
                    resource_id=thread_id,
                    description=f'Duplicate cache entries found: {existing_keys}',
                    detected_at=time.time(),
                    severity='medium',
                    expected_state={'single_cache_entry': True},
                    actual_state={'duplicate_keys': existing_keys}
                ))
    
    async def _check_reference_integrity(self, thread_ids: List[str], message_ids: List[str]):
        """Check reference integrity across the system."""
        # Verify all message thread references are valid
        for message_id in message_ids:
            message = await self.services.postgres.fetchrow("""
                SELECT id, thread_id FROM backend.messages WHERE id = $1
            """, message_id)
            
            if message:
                thread_exists = await self.services.postgres.fetchval("""
                    SELECT EXISTS(SELECT 1 FROM backend.threads WHERE id = $1)
                """, message['thread_id'])
                
                if not thread_exists:
                    self.violations.append(ConsistencyViolation(
                        violation_type=ConsistencyViolationType.MISSING_REFERENCES,
                        resource_type='message',
                        resource_id=message_id,
                        description=f'Message references missing thread: {message["thread_id"]}',
                        detected_at=time.time(),
                        severity='high',
                        expected_state={'thread_exists': True},
                        actual_state={'thread_exists': False}
                    ))
    
    async def _check_concurrent_modification_conflicts(self, thread_ids: List[str]):
        """Check for concurrent modification conflicts."""
        for thread_id in thread_ids:
            # Simulate checking for conflicting updates
            # In practice, this would check version numbers, timestamps, etc.
            
            db_thread = await self.services.postgres.fetchrow("""
                SELECT id, updated_at FROM backend.threads WHERE id = $1
            """, thread_id)
            
            cached_thread = await self.services.redis.get_json(f"thread:{thread_id}")
            
            if db_thread and cached_thread:
                db_updated_at = db_thread['updated_at'].timestamp()
                cache_updated_at = cached_thread.get('updated_at')
                
                if cache_updated_at and abs(db_updated_at - float(cache_updated_at)) > 300:  # 5 minute difference
                    self.violations.append(ConsistencyViolation(
                        violation_type=ConsistencyViolationType.CONCURRENT_MODIFICATION_CONFLICT,
                        resource_type='thread',
                        resource_id=thread_id,
                        description=f'Potential concurrent modification: DB and cache timestamps differ significantly',
                        detected_at=time.time(),
                        severity='medium',
                        expected_state={'timestamp_sync': True},
                        actual_state={'db_time': db_updated_at, 'cache_time': cache_updated_at}
                    ))
    
    async def _check_background_process_consistency(self, user_ids: List[str], thread_ids: List[str]):
        """Check consistency with background processes."""
        # Simulate checking background process artifacts
        # This could include job queues, scheduled tasks, analytics updates, etc.
        
        for user_id in user_ids:
            # Check if user's thread count matches actual count
            db_thread_count = await self.services.postgres.fetchval("""
                SELECT COUNT(*) FROM backend.threads WHERE user_id = $1
            """, user_id)
            
            # Simulate checking a background process that maintains user stats
            cached_user_stats = await self.services.redis.get_json(f"user_stats:{user_id}")
            
            if cached_user_stats:
                cached_thread_count = cached_user_stats.get('thread_count', 0)
                
                if cached_thread_count != db_thread_count:
                    self.violations.append(ConsistencyViolation(
                        violation_type=ConsistencyViolationType.BACKGROUND_PROCESS_INCONSISTENCY,
                        resource_type='user_stats',
                        resource_id=user_id,
                        description=f'User stats inconsistent: cached={cached_thread_count}, actual={db_thread_count}',
                        detected_at=time.time(),
                        severity='low',
                        expected_state={'thread_count': db_thread_count},
                        actual_state={'thread_count': cached_thread_count},
                        affected_users=[user_id]
                    ))
    
    def _calculate_consistency_score(self) -> float:
        """Calculate overall consistency score (0-100)."""
        if not self.violations:
            return 100.0
        
        # Weight violations by severity
        severity_weights = {
            'low': 1,
            'medium': 3,
            'high': 7,
            'critical': 15
        }
        
        total_weight = sum(severity_weights.get(v.severity, 1) for v in self.violations)
        max_possible_weight = len(self.violations) * severity_weights['critical']
        
        consistency_score = max(0, 100 - (total_weight / max_possible_weight * 100))
        return consistency_score
    
    async def resolve_violations(self) -> Dict[str, Any]:
        """Attempt to resolve detected consistency violations."""
        resolved_count = 0
        resolution_failures = []
        
        for violation in self.violations:
            try:
                success = await self._resolve_single_violation(violation)
                if success:
                    resolved_count += 1
                    violation.resolution_required = False
                else:
                    resolution_failures.append(violation.resource_id)
            except Exception as e:
                resolution_failures.append(f"{violation.resource_id}: {str(e)}")
        
        self.consistency_metrics['violations_resolved'] = resolved_count
        
        return {
            'resolved_count': resolved_count,
            'resolution_failures': resolution_failures,
            'success_rate': (resolved_count / len(self.violations)) * 100 if self.violations else 100
        }
    
    async def _resolve_single_violation(self, violation: ConsistencyViolation) -> bool:
        """Attempt to resolve a single consistency violation."""
        if violation.violation_type == ConsistencyViolationType.POSTGRES_REDIS_MISMATCH:
            if violation.resource_type == 'thread':
                # Refresh cache from PostgreSQL
                db_thread = await self.services.postgres.fetchrow("""
                    SELECT id, user_id, title, metadata, updated_at
                    FROM backend.threads WHERE id = $1
                """, violation.resource_id)
                
                if db_thread:
                    await self.services.redis.set_json(f"thread:{violation.resource_id}", {
                        'id': str(db_thread['id']),
                        'user_id': str(db_thread['user_id']),
                        'title': db_thread['title'],
                        'metadata': db_thread['metadata'],
                        'updated_at': db_thread['updated_at'].timestamp(),
                        'refreshed_at': time.time()
                    }, ex=3600)
                    return True
        
        elif violation.violation_type == ConsistencyViolationType.STALE_CACHE_DATA:
            # Force cache refresh
            await self.services.redis.delete(f"thread:{violation.resource_id}")
            return True
        
        elif violation.violation_type == ConsistencyViolationType.ORPHANED_RESOURCES:
            # Delete orphaned resources
            if violation.resource_type == 'message':
                await self.services.postgres.execute("""
                    DELETE FROM backend.messages WHERE id = $1
                """, violation.resource_id)
                return True
        
        return False


class TestWebSocketApplicationStateDistributedConsistencyChecks(BaseIntegrationTest):
    """Test distributed state consistency checks across WebSocket events and background processes."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_comprehensive_distributed_consistency_validation(self, real_services_fixture):
        """Test comprehensive consistency validation across all distributed components."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        # Create distributed consistency checker
        consistency_checker = DistributedConsistencyChecker(services, state_manager)
        
        # Set up test environment with multiple users and resources
        users = []
        all_thread_ids = []
        all_message_ids = []
        
        for i in range(3):
            # Create user
            user_data = await self.create_test_user_context(services, {
                'email': f'consistency-user-{i}@example.com',
                'name': f'Consistency Test User {i}'
            })
            user_id = UserID(user_data['id'])
            users.append(str(user_id))
            
            # Create threads for user
            user_thread_ids = []
            for j in range(2):
                thread_id = await services.postgres.fetchval("""
                    INSERT INTO backend.threads (user_id, title, metadata)
                    VALUES ($1, $2, $3)
                    RETURNING id
                """, str(user_id), f"Consistency Thread {j}", json.dumps({
                    'user_index': i,
                    'thread_index': j,
                    'consistency_test': True
                }))
                
                thread_id = ThreadID(str(thread_id))
                user_thread_ids.append(str(thread_id))
                all_thread_ids.append(str(thread_id))
                
                # Cache thread in Redis
                await services.redis.set_json(f"thread:{thread_id}", {
                    'id': str(thread_id),
                    'user_id': str(user_id),
                    'title': f'Consistency Thread {j}',
                    'cached_at': time.time(),
                    'user_index': i,
                    'thread_index': j
                }, ex=3600)
                
                # Create messages for thread
                for k in range(2):
                    message_id = MessageID(str(uuid4()))
                    await services.postgres.execute("""
                        INSERT INTO backend.messages (id, thread_id, user_id, content, role)
                        VALUES ($1, $2, $3, $4, $5)
                    """, str(message_id), str(thread_id), str(user_id), 
                         f"Consistency message {k}", "user")
                    
                    all_message_ids.append(str(message_id))
                    
                    # Cache message in Redis
                    await services.redis.set_json(f"message:{message_id}", {
                        'id': str(message_id),
                        'thread_id': str(thread_id),
                        'user_id': str(user_id),
                        'content': f"Consistency message {k}",
                        'role': 'user',
                        'cached_at': time.time()
                    }, ex=3600)
            
            # Set up WebSocket state
            connection_id = f"conn_{user_id}_0"
            state_manager.set_websocket_state(connection_id, 'connection_info', {
                'user_id': str(user_id),
                'connection_id': connection_id,
                'current_thread_id': user_thread_ids[0] if user_thread_ids else None,
                'thread_count': len(user_thread_ids),
                'state': WebSocketConnectionState.CONNECTED.value,
                'user_index': i
            })
            
            # Create background process artifacts (user stats)
            await services.redis.set_json(f"user_stats:{user_id}", {
                'user_id': str(user_id),
                'thread_count': len(user_thread_ids),
                'message_count': len(user_thread_ids) * 2,  # 2 messages per thread
                'last_updated': time.time()
            }, ex=3600)
        
        # Perform initial consistency check (should be clean)
        initial_check = await consistency_checker.perform_comprehensive_consistency_check(
            users, all_thread_ids, all_message_ids
        )
        
        self.logger.info(f"Initial consistency check:")
        self.logger.info(f"  Violations found: {initial_check['violations_found']}")
        self.logger.info(f"  Consistency score: {initial_check['consistency_score']:.1f}%")
        
        # The initial check should show a clean system
        assert initial_check['violations_found'] == 0, f"Initial system should be consistent, found {initial_check['violations_found']} violations"
        assert initial_check['consistency_score'] >= 99.0, f"Initial consistency score too low: {initial_check['consistency_score']:.1f}%"
        
        # Introduce various consistency violations for testing
        
        # 1. Create PostgreSQL-Redis mismatch
        test_thread_id = all_thread_ids[0]
        await services.postgres.execute("""
            UPDATE backend.threads SET title = $2 WHERE id = $1
        """, test_thread_id, "Updated Title in DB Only")
        
        # 2. Create stale cache entry
        stale_thread_id = all_thread_ids[1]
        await services.redis.set_json(f"thread:{stale_thread_id}", {
            'id': stale_thread_id,
            'user_id': users[0],
            'title': 'Stale Title',
            'cached_at': time.time() - 7200,  # 2 hours old
            'updated_at': time.time() - 3600   # 1 hour old
        }, ex=3600)
        
        # 3. Create orphaned message
        orphaned_message_id = MessageID(str(uuid4()))
        await services.postgres.execute("""
            INSERT INTO backend.messages (id, thread_id, user_id, content, role)
            VALUES ($1, $2, $3, $4, $5)
        """, str(orphaned_message_id), '00000000-0000-0000-0000-000000000000', users[0], "Orphaned message", "user")
        all_message_ids.append(str(orphaned_message_id))
        
        # 4. Create WebSocket-Database mismatch
        invalid_connection_id = f"conn_{users[0]}_invalid"
        state_manager.set_websocket_state(invalid_connection_id, 'connection_info', {
            'user_id': users[0],
            'connection_id': invalid_connection_id,
            'current_thread_id': '00000000-0000-0000-0000-000000000000',  # Non-existent thread
            'state': WebSocketConnectionState.CONNECTED.value
        })
        
        # 5. Create duplicate cache entries
        duplicate_thread_id = all_thread_ids[2]
        await services.redis.set_json(f"thread_cache:{duplicate_thread_id}", {
            'id': duplicate_thread_id,
            'title': 'Duplicate Cache Entry'
        }, ex=3600)
        
        # 6. Create background process inconsistency
        await services.redis.set_json(f"user_stats:{users[0]}", {
            'user_id': users[0],
            'thread_count': 999,  # Wrong count
            'message_count': 888,  # Wrong count
            'last_updated': time.time()
        }, ex=3600)
        
        # Perform consistency check after introducing violations
        violated_check = await consistency_checker.perform_comprehensive_consistency_check(
            users, all_thread_ids, all_message_ids
        )
        
        self.logger.info(f"Consistency check with violations:")
        self.logger.info(f"  Violations found: {violated_check['violations_found']}")
        self.logger.info(f"  Consistency score: {violated_check['consistency_score']:.1f}%")
        self.logger.info(f"  Check duration: {violated_check['metrics']['check_duration_seconds']:.3f}s")
        
        # Analyze detected violations
        violations_by_type = {}
        violations_by_severity = {}
        
        for violation in violated_check['violations']:
            vtype = violation['violation_type']
            severity = violation['severity']
            
            violations_by_type[vtype] = violations_by_type.get(vtype, 0) + 1
            violations_by_severity[severity] = violations_by_severity.get(severity, 0) + 1
        
        self.logger.info(f"  Violations by type: {violations_by_type}")
        self.logger.info(f"  Violations by severity: {violations_by_severity}")
        
        # Validate that violations were detected
        assert violated_check['violations_found'] >= 5, f"Expected at least 5 violations, detected {violated_check['violations_found']}"
        assert violated_check['consistency_score'] < 95.0, f"Consistency score should drop with violations: {violated_check['consistency_score']:.1f}%"
        
        # Validate specific violation types were detected
        detected_types = set(v['violation_type'] for v in violated_check['violations'])
        expected_types = {
            ConsistencyViolationType.POSTGRES_REDIS_MISMATCH.value,
            ConsistencyViolationType.ORPHANED_RESOURCES.value,
            ConsistencyViolationType.WEBSOCKET_DATABASE_MISMATCH.value,
            ConsistencyViolationType.BACKGROUND_PROCESS_INCONSISTENCY.value
        }
        
        found_expected_types = expected_types.intersection(detected_types)
        assert len(found_expected_types) >= 3, f"Expected to detect at least 3 violation types, found: {found_expected_types}"
        
        # Test violation resolution
        resolution_result = await consistency_checker.resolve_violations()
        
        self.logger.info(f"Violation resolution:")
        self.logger.info(f"  Resolved: {resolution_result['resolved_count']}")
        self.logger.info(f"  Failed: {len(resolution_result['resolution_failures'])}")
        self.logger.info(f"  Success rate: {resolution_result['success_rate']:.1f}%")
        
        # Some violations should be resolvable
        assert resolution_result['resolved_count'] > 0, "At least some violations should be resolvable"
        assert resolution_result['success_rate'] >= 50.0, f"Resolution success rate too low: {resolution_result['success_rate']:.1f}%"
        
        # Perform final consistency check
        final_check = await consistency_checker.perform_comprehensive_consistency_check(
            users, all_thread_ids, all_message_ids
        )
        
        self.logger.info(f"Final consistency check after resolution:")
        self.logger.info(f"  Violations found: {final_check['violations_found']}")
        self.logger.info(f"  Consistency score: {final_check['consistency_score']:.1f}%")
        
        # System should be more consistent after resolution
        improvement = final_check['consistency_score'] - violated_check['consistency_score']
        assert improvement > 0, f"Consistency should improve after resolution, change: {improvement:.1f}%"
        
        # BUSINESS VALUE: Comprehensive consistency monitoring and resolution
        self.assert_business_value_delivered({
            'violation_detection': violated_check['violations_found'] >= 5,
            'comprehensive_checking': len(detected_types) >= 3,
            'violation_resolution': resolution_result['resolved_count'] > 0,
            'consistency_improvement': improvement > 0
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_distributed_consistency_under_concurrent_load(self, real_services_fixture):
        """Test distributed consistency checks under concurrent load with multiple processes."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        consistency_checker = DistributedConsistencyChecker(services, state_manager)
        
        # Create test user and resources
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        
        # Create shared thread for concurrent operations
        shared_thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, title, metadata)
            VALUES ($1, $2, $3)
            RETURNING id
        """, str(user_id), "Concurrent Load Test Thread", json.dumps({
            'load_test': True,
            'expected_operations': 50
        }))
        
        shared_thread_id = ThreadID(str(shared_thread_id))
        
        # Set up WebSocket state
        connection_id = str(uuid4())
        state_manager.set_websocket_state(connection_id, 'connection_info', {
            'user_id': str(user_id),
            'connection_id': connection_id,
            'current_thread_id': str(shared_thread_id),
            'state': WebSocketConnectionState.CONNECTED.value
        })
        
        # Concurrent operation functions
        async def concurrent_database_operations(operation_count: int):
            """Simulate concurrent database operations."""
            for i in range(operation_count):
                message_id = MessageID(str(uuid4()))
                await services.postgres.execute("""
                    INSERT INTO backend.messages (id, thread_id, user_id, content, role)
                    VALUES ($1, $2, $3, $4, $5)
                """, str(message_id), str(shared_thread_id), str(user_id), 
                     f"Concurrent message {i}", "user")
                
                await asyncio.sleep(0.01)  # Small delay
        
        async def concurrent_cache_operations(operation_count: int):
            """Simulate concurrent cache operations."""
            for i in range(operation_count):
                cache_key = f"concurrent_data:{i}"
                await services.redis.set_json(cache_key, {
                    'thread_id': str(shared_thread_id),
                    'user_id': str(user_id),
                    'operation_index': i,
                    'timestamp': time.time()
                }, ex=300)
                
                await asyncio.sleep(0.01)
        
        async def concurrent_websocket_operations(operation_count: int):
            """Simulate concurrent WebSocket state updates."""
            for i in range(operation_count):
                current_state = state_manager.get_websocket_state(connection_id, 'connection_info')
                if current_state:
                    current_state['operation_count'] = current_state.get('operation_count', 0) + 1
                    current_state['last_operation'] = i
                    current_state['last_update'] = time.time()
                    state_manager.set_websocket_state(connection_id, 'connection_info', current_state)
                
                await asyncio.sleep(0.01)
        
        async def periodic_consistency_checks():
            """Perform periodic consistency checks during load."""
            checks_performed = 0
            violations_detected = 0
            
            for _ in range(10):  # 10 checks during load test
                await asyncio.sleep(0.2)  # Check every 200ms
                
                check_result = await consistency_checker.perform_comprehensive_consistency_check(
                    [str(user_id)], [str(shared_thread_id)], []
                )
                
                checks_performed += 1
                violations_detected += check_result['violations_found']
            
            return {
                'checks_performed': checks_performed,
                'violations_detected': violations_detected,
                'avg_violations_per_check': violations_detected / checks_performed if checks_performed > 0 else 0
            }
        
        # Run concurrent operations with periodic consistency checks
        operation_count = 10  # Reduced for test performance
        
        start_time = time.time()
        
        # Execute concurrent operations
        results = await asyncio.gather(
            concurrent_database_operations(operation_count),
            concurrent_cache_operations(operation_count),
            concurrent_websocket_operations(operation_count),
            periodic_consistency_checks(),
            return_exceptions=True
        )
        
        end_time = time.time()
        test_duration = end_time - start_time
        
        # Analyze results
        periodic_check_results = results[3] if len(results) > 3 and not isinstance(results[3], Exception) else {
            'checks_performed': 0,
            'violations_detected': 0,
            'avg_violations_per_check': 0
        }
        
        # Perform final comprehensive check
        final_check = await consistency_checker.perform_comprehensive_consistency_check(
            [str(user_id)], [str(shared_thread_id)], []
        )
        
        # Verify final state
        final_message_count = await services.postgres.fetchval("""
            SELECT COUNT(*) FROM backend.messages WHERE thread_id = $1
        """, str(shared_thread_id))
        
        cache_key_count = len(await services.redis.keys("concurrent_data:*"))
        
        final_ws_state = state_manager.get_websocket_state(connection_id, 'connection_info')
        
        self.logger.info(f"Concurrent load test results:")
        self.logger.info(f"  Test duration: {test_duration:.2f}s")
        self.logger.info(f"  Messages created: {final_message_count}")
        self.logger.info(f"  Cache entries created: {cache_key_count}")
        self.logger.info(f"  WebSocket operations: {final_ws_state.get('operation_count', 0) if final_ws_state else 0}")
        self.logger.info(f"  Periodic checks performed: {periodic_check_results['checks_performed']}")
        self.logger.info(f"  Violations detected during load: {periodic_check_results['violations_detected']}")
        self.logger.info(f"  Final consistency score: {final_check['consistency_score']:.1f}%")
        
        # Validate system behavior under load
        assert final_message_count == operation_count, f"Expected {operation_count} messages, got {final_message_count}"
        assert cache_key_count == operation_count, f"Expected {operation_count} cache entries, got {cache_key_count}"
        assert final_ws_state is not None, "WebSocket state lost during load test"
        assert final_ws_state.get('operation_count', 0) == operation_count, f"WebSocket operations not tracked correctly"
        
        # Consistency should remain reasonably high under load
        assert final_check['consistency_score'] >= 85.0, f"Consistency degraded too much under load: {final_check['consistency_score']:.1f}%"
        
        # Periodic checks should not show excessive violations
        avg_violations = periodic_check_results['avg_violations_per_check']
        assert avg_violations <= 2.0, f"Too many violations detected during load: {avg_violations:.1f} avg per check"
        
        # BUSINESS VALUE: System maintains consistency under concurrent load
        self.assert_business_value_delivered({
            'load_test_completion': test_duration < 30.0,
            'data_consistency_under_load': final_message_count == operation_count,
            'state_consistency_under_load': final_ws_state.get('operation_count', 0) == operation_count,
            'consistency_monitoring_under_load': periodic_check_results['checks_performed'] >= 8,
            'acceptable_violation_rate': avg_violations <= 2.0
        }, 'automation')