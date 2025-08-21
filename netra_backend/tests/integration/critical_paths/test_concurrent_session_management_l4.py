"""
L4 Integration Test: Concurrent Session Management
Tests concurrent user sessions, resource contention, and consistency
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import random
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.config import settings
from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.services.resource_manager import ResourceManager

# Add project root to path
from netra_backend.app.services.session_service import SessionService

# Add project root to path


class TestConcurrentSessionManagementL4:
    """Concurrent session management testing"""
    
    @pytest.fixture
    async def session_infrastructure(self):
        """Session infrastructure setup"""
        return {
            'session_service': SessionService(),
            'auth_service': AuthService(),
            'resource_manager': ResourceManager(),
            'active_sessions': defaultdict(set),
            'resource_locks': {},
            'conflict_log': [],
            'metrics': {
                'total_sessions': 0,
                'concurrent_peak': 0,
                'conflicts': 0,
                'deadlocks': 0
            }
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_concurrent_session_creation_same_user(self, session_infrastructure):
        """Test concurrent session creation for the same user"""
        user_id = "user_concurrent_create"
        
        # Create sessions concurrently
        async def create_session(device_id):
            try:
                session = await session_infrastructure['session_service'].create_session(
                    user_id=user_id,
                    device_id=device_id,
                    ip_address=f"192.168.1.{random.randint(1, 255)}"
                )
                return {'success': True, 'session': session}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        # Launch 20 concurrent session creations
        tasks = [
            asyncio.create_task(create_session(f"device_{i}"))
            for i in range(20)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed but with unique session IDs
        successful = [r for r in results if r['success']]
        assert len(successful) == 20
        
        # Extract session IDs
        session_ids = [r['session']['session_id'] for r in successful]
        assert len(session_ids) == len(set(session_ids))  # All unique
        
        # Verify session limit enforcement
        user_sessions = await session_infrastructure['session_service'].get_user_sessions(user_id)
        assert len(user_sessions) <= settings.MAX_SESSIONS_PER_USER
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_resource_contention_between_sessions(self, session_infrastructure):
        """Test resource contention when multiple sessions access same resources"""
        resource_id = "shared_resource_1"
        
        # Create multiple sessions
        sessions = []
        for i in range(10):
            session = await session_infrastructure['session_service'].create_session(
                user_id=f"user_{i}",
                device_id=f"device_{i}"
            )
            sessions.append(session)
        
        # Track resource access
        access_order = []
        conflicts = []
        
        async def access_resource(session_id, duration=0.1):
            try:
                # Acquire resource lock
                lock = await session_infrastructure['resource_manager'].acquire_lock(
                    resource_id=resource_id,
                    session_id=session_id,
                    timeout=1.0
                )
                
                access_order.append({
                    'session_id': session_id,
                    'acquired_at': time.time()
                })
                
                # Simulate resource usage
                await asyncio.sleep(duration)
                
                # Release lock
                await session_infrastructure['resource_manager'].release_lock(
                    resource_id=resource_id,
                    session_id=session_id
                )
                
                return True
                
            except Exception as e:
                conflicts.append({
                    'session_id': session_id,
                    'error': str(e)
                })
                return False
        
        # All sessions try to access the resource concurrently
        tasks = [
            asyncio.create_task(
                access_resource(session['session_id'], random.uniform(0.05, 0.15))
            )
            for session in sessions
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify mutual exclusion
        for i in range(len(access_order) - 1):
            current = access_order[i]
            next_access = access_order[i + 1]
            # Next access should start after current finishes
            assert next_access['acquired_at'] >= current['acquired_at']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_session_state_consistency_under_concurrent_updates(self, session_infrastructure):
        """Test session state consistency with concurrent updates"""
        session_id = "session_consistency_test"
        
        # Create session with initial state
        session = await session_infrastructure['session_service'].create_session(
            user_id="user_consistency",
            device_id="device_1"
        )
        session_id = session['session_id']
        
        # Initialize counter
        await session_infrastructure['session_service'].update_session_data(
            session_id=session_id,
            data={'counter': 0, 'operations': []}
        )
        
        # Concurrent updates
        async def increment_counter(operation_id):
            # Read current value
            current_data = await session_infrastructure['session_service'].get_session_data(session_id)
            current_value = current_data['counter']
            
            # Simulate processing delay
            await asyncio.sleep(random.uniform(0.01, 0.05))
            
            # Update with increment
            new_value = current_value + 1
            await session_infrastructure['session_service'].update_session_data(
                session_id=session_id,
                data={
                    'counter': new_value,
                    'operations': current_data['operations'] + [operation_id]
                },
                version=current_data.get('version')  # Optimistic locking
            )
            
            return new_value
        
        # Launch 50 concurrent increments
        tasks = [
            asyncio.create_task(increment_counter(f"op_{i}"))
            for i in range(50)
        ]
        
        # Some might fail due to version conflicts
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_updates = [r for r in results if not isinstance(r, Exception)]
        
        # Final value should reflect successful updates
        final_data = await session_infrastructure['session_service'].get_session_data(session_id)
        
        # With optimistic locking, some updates might be retried
        assert final_data['counter'] <= 50
        assert len(final_data['operations']) == final_data['counter']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_session_cleanup_with_active_operations(self, session_infrastructure):
        """Test session cleanup while operations are in progress"""
        user_id = "user_cleanup"
        
        # Create multiple sessions
        sessions = []
        for i in range(5):
            session = await session_infrastructure['session_service'].create_session(
                user_id=user_id,
                device_id=f"device_{i}"
            )
            sessions.append(session)
        
        # Start long-running operations
        operation_tasks = []
        
        async def long_operation(session_id):
            try:
                # Mark session as having active operation
                await session_infrastructure['session_service'].mark_session_busy(session_id)
                
                # Simulate long operation
                await asyncio.sleep(2)
                
                # Mark as complete
                await session_infrastructure['session_service'].mark_session_idle(session_id)
                return "completed"
            except asyncio.CancelledError:
                return "cancelled"
            except Exception as e:
                return f"error: {e}"
        
        # Start operations on first 3 sessions
        for session in sessions[:3]:
            task = asyncio.create_task(long_operation(session['session_id']))
            operation_tasks.append(task)
        
        # Wait a bit for operations to start
        await asyncio.sleep(0.5)
        
        # Attempt to cleanup all user sessions
        cleanup_result = await session_infrastructure['session_service'].cleanup_user_sessions(
            user_id=user_id,
            force=False  # Should not interrupt active operations
        )
        
        # Only idle sessions should be cleaned
        assert cleanup_result['cleaned'] == 2  # sessions 3 and 4
        assert cleanup_result['skipped'] == 3  # sessions 0, 1, 2 (busy)
        
        # Cancel remaining operations
        for task in operation_tasks:
            task.cancel()
        
        await asyncio.gather(*operation_tasks, return_exceptions=True)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_deadlock_detection_and_resolution(self, session_infrastructure):
        """Test deadlock detection and resolution in concurrent sessions"""
        
        # Create two sessions
        session1 = await session_infrastructure['session_service'].create_session(
            user_id="user_1",
            device_id="device_1"
        )
        
        session2 = await session_infrastructure['session_service'].create_session(
            user_id="user_2",
            device_id="device_2"
        )
        
        deadlock_detected = False
        
        async def acquire_resources_order1(session_id):
            # Try to acquire resource A then B
            lock_a = await session_infrastructure['resource_manager'].acquire_lock(
                resource_id="resource_a",
                session_id=session_id,
                timeout=0.5
            )
            
            await asyncio.sleep(0.1)  # Hold lock A
            
            try:
                lock_b = await session_infrastructure['resource_manager'].acquire_lock(
                    resource_id="resource_b",
                    session_id=session_id,
                    timeout=0.5
                )
            except Exception as e:
                if "deadlock" in str(e).lower():
                    nonlocal deadlock_detected
                    deadlock_detected = True
                    # Release locks in reverse order
                    await session_infrastructure['resource_manager'].release_lock(
                        resource_id="resource_a",
                        session_id=session_id
                    )
                    raise
        
        async def acquire_resources_order2(session_id):
            # Try to acquire resource B then A (opposite order)
            lock_b = await session_infrastructure['resource_manager'].acquire_lock(
                resource_id="resource_b",
                session_id=session_id,
                timeout=0.5
            )
            
            await asyncio.sleep(0.1)  # Hold lock B
            
            try:
                lock_a = await session_infrastructure['resource_manager'].acquire_lock(
                    resource_id="resource_a",
                    session_id=session_id,
                    timeout=0.5
                )
            except Exception as e:
                if "deadlock" in str(e).lower():
                    nonlocal deadlock_detected
                    deadlock_detected = True
                    # Release locks
                    await session_infrastructure['resource_manager'].release_lock(
                        resource_id="resource_b",
                        session_id=session_id
                    )
                    raise
        
        # Run both concurrently (potential deadlock)
        task1 = asyncio.create_task(acquire_resources_order1(session1['session_id']))
        task2 = asyncio.create_task(acquire_resources_order2(session2['session_id']))
        
        results = await asyncio.gather(task1, task2, return_exceptions=True)
        
        # At least one should detect potential deadlock
        assert deadlock_detected or any(isinstance(r, asyncio.TimeoutError) for r in results)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_session_priority_scheduling(self, session_infrastructure):
        """Test priority-based session request scheduling"""
        
        # Create sessions with different priority levels
        priority_sessions = []
        
        for i in range(10):
            priority = 'high' if i < 2 else 'medium' if i < 5 else 'low'
            session = await session_infrastructure['session_service'].create_session(
                user_id=f"user_{i}",
                device_id=f"device_{i}",
                priority=priority
            )
            priority_sessions.append((session, priority))
        
        # Track execution order
        execution_order = []
        
        async def execute_request(session_id, priority):
            # Queue request
            position = await session_infrastructure['resource_manager'].queue_request(
                session_id=session_id,
                priority=priority
            )
            
            # Wait for turn
            await session_infrastructure['resource_manager'].wait_for_turn(session_id)
            
            execution_order.append({
                'session_id': session_id,
                'priority': priority,
                'executed_at': time.time()
            })
            
            # Simulate work
            await asyncio.sleep(0.05)
            
            # Complete request
            await session_infrastructure['resource_manager'].complete_request(session_id)
        
        # Submit all requests simultaneously
        tasks = [
            asyncio.create_task(execute_request(session['session_id'], priority))
            for session, priority in priority_sessions
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify priority ordering
        high_priority = [e for e in execution_order if e['priority'] == 'high']
        medium_priority = [e for e in execution_order if e['priority'] == 'medium']
        low_priority = [e for e in execution_order if e['priority'] == 'low']
        
        # High priority should execute first
        if high_priority and medium_priority:
            assert max(e['executed_at'] for e in high_priority) < min(e['executed_at'] for e in medium_priority)
        
        if medium_priority and low_priority:
            assert max(e['executed_at'] for e in medium_priority) < min(e['executed_at'] for e in low_priority)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_session_migration_under_load(self, session_infrastructure):
        """Test session migration between servers under load"""
        
        # Create sessions distributed across "servers"
        server1_sessions = []
        server2_sessions = []
        
        for i in range(20):
            session = await session_infrastructure['session_service'].create_session(
                user_id=f"user_{i}",
                device_id=f"device_{i}",
                server_id="server1" if i < 10 else "server2"
            )
            
            if i < 10:
                server1_sessions.append(session)
            else:
                server2_sessions.append(session)
        
        # Simulate load on server1
        server1_load = 0.9  # 90% loaded
        server2_load = 0.3  # 30% loaded
        
        # Migrate sessions from overloaded server
        migration_tasks = []
        
        async def migrate_session(session, from_server, to_server):
            # Save session state
            state = await session_infrastructure['session_service'].get_session_state(
                session['session_id']
            )
            
            # Simulate migration
            await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # Restore on new server
            await session_infrastructure['session_service'].restore_session(
                session_id=session['session_id'],
                state=state,
                server_id=to_server
            )
            
            return session['session_id']
        
        # Migrate half of server1 sessions to server2
        for session in server1_sessions[:5]:
            task = asyncio.create_task(
                migrate_session(session, "server1", "server2")
            )
            migration_tasks.append(task)
        
        migrated = await asyncio.gather(*migration_tasks)
        
        # Verify migrations completed
        assert len(migrated) == 5
        
        # Check load distribution after migration
        server1_final = await session_infrastructure['session_service'].count_sessions_on_server("server1")
        server2_final = await session_infrastructure['session_service'].count_sessions_on_server("server2")
        
        assert server1_final == 5
        assert server2_final == 15
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_session_rate_limiting_fairness(self, session_infrastructure):
        """Test fair rate limiting across concurrent sessions"""
        
        # Create sessions for different users
        sessions = []
        for i in range(3):
            for j in range(3):
                session = await session_infrastructure['session_service'].create_session(
                    user_id=f"user_{i}",
                    device_id=f"device_{i}_{j}"
                )
                sessions.append((session, f"user_{i}"))
        
        # Track request counts
        request_counts = defaultdict(int)
        rejected_counts = defaultdict(int)
        
        async def make_requests(session_id, user_id, num_requests=20):
            for i in range(num_requests):
                try:
                    allowed = await session_infrastructure['resource_manager'].check_rate_limit(
                        session_id=session_id,
                        user_id=user_id,
                        limit_per_second=5
                    )
                    
                    if allowed:
                        request_counts[user_id] += 1
                        await asyncio.sleep(0.05)  # Simulate request processing
                    else:
                        rejected_counts[user_id] += 1
                        
                except Exception:
                    rejected_counts[user_id] += 1
        
        # All sessions make requests concurrently
        tasks = [
            asyncio.create_task(make_requests(session['session_id'], user_id))
            for session, user_id in sessions
        ]
        
        await asyncio.gather(*tasks)
        
        # Each user should get fair share despite multiple sessions
        for user_id in ["user_0", "user_1", "user_2"]:
            # Should be roughly equal
            assert 40 <= request_counts[user_id] <= 80
            
        # Total accepted should respect global limits
        total_accepted = sum(request_counts.values())
        total_rejected = sum(rejected_counts.values())
        
        assert total_rejected > 0  # Some should be rate limited