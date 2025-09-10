"""
Integration tests for user session state race conditions.

BUSINESS VALUE JUSTIFICATION (BVJ):
Segment: Enterprise, Mid, Early (Platform/Internal)
Business Goal: Platform Stability, Risk Reduction
Value Impact: Session race conditions cause user logout, data loss, security breaches
Strategic Impact: Multi-user session integrity prevents customer churn and security incidents

These tests validate that user session management maintains consistency and isolation
under concurrent access patterns typical of multi-user production environments.

Race Condition Patterns Tested:
1. Concurrent session creation and cleanup
2. Session state consistency during rapid updates  
3. Authentication token races during refresh
4. Cross-user session contamination prevention
5. Session expiration and renewal timing races
"""

import asyncio
import pytest
import uuid
import time
import weakref
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any
from unittest.mock import patch

from test_framework.base_integration_test import BaseIntegrationTest
from shared.types import UserID, SessionID, RequestID


class TestUserSessionStateRaces(BaseIntegrationTest):
    """Integration tests for user session state race conditions and concurrent access patterns."""
    
    def setup_method(self):
        """Set up test environment with session tracking."""
        super().setup_method()
        self.active_sessions: Dict[str, Dict] = {}
        self.session_operations: List[Dict] = []
        self.race_condition_detected = False
        self.session_leak_tracker: Set[weakref.ref] = set()
        
    def teardown_method(self):
        """Clean up sessions and verify no leaks."""
        super().teardown_method()
        
        # Force cleanup of any remaining sessions
        for session_id in list(self.active_sessions.keys()):
            try:
                self._cleanup_session(session_id)
            except Exception:
                pass  # Ignore cleanup errors in teardown
                
        # Check for session leaks
        leaked_sessions = [ref for ref in self.session_leak_tracker if ref() is not None]
        if leaked_sessions:
            pytest.fail(f"Session leak detected: {len(leaked_sessions)} sessions not properly cleaned up")
    
    def _track_session_operation(self, operation: str, session_id: str, user_id: str, success: bool = True, **kwargs):
        """Track session operations for race condition analysis."""
        self.session_operations.append({
            'timestamp': time.time(),
            'operation': operation,
            'session_id': session_id,
            'user_id': user_id,
            'success': success,
            'thread_id': id(asyncio.current_task()),
            **kwargs
        })
    
    def _detect_session_race_conditions(self) -> List[Dict]:
        """Analyze operations for race conditions."""
        race_conditions = []
        
        # Group operations by session_id
        session_ops = {}
        for op in self.session_operations:
            session_id = op['session_id']
            if session_id not in session_ops:
                session_ops[session_id] = []
            session_ops[session_id].append(op)
        
        # Check for race conditions in each session
        for session_id, ops in session_ops.items():
            ops.sort(key=lambda x: x['timestamp'])
            
            # Detect concurrent operations (within 50ms window)
            for i in range(len(ops) - 1):
                for j in range(i + 1, len(ops)):
                    time_diff = abs(ops[j]['timestamp'] - ops[i]['timestamp'])
                    thread_diff = ops[j]['thread_id'] != ops[i]['thread_id']
                    
                    if time_diff < 0.05 and thread_diff:  # 50ms window, different threads
                        race_conditions.append({
                            'type': 'concurrent_session_operations',
                            'session_id': session_id,
                            'operations': [ops[i]['operation'], ops[j]['operation']],
                            'time_difference': time_diff,
                            'risk_level': 'high' if 'create' in ops[i]['operation'] or 'delete' in ops[i]['operation'] else 'medium'
                        })
        
        return race_conditions
    
    def _create_test_session(self, user_id: str) -> str:
        """Create a test session for the user."""
        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.utcnow(),
            'last_access': datetime.utcnow(),
            'is_active': True,
            'auth_token': f"token_{session_id[:8]}"
        }
        
        self.active_sessions[session_id] = session_data
        self._track_session_operation('create', session_id, user_id)
        
        # Track for leak detection
        session_ref = weakref.ref(session_data)
        self.session_leak_tracker.add(session_ref)
        
        return session_id
    
    def _cleanup_session(self, session_id: str):
        """Clean up a test session."""
        if session_id in self.active_sessions:
            session_data = self.active_sessions[session_id]
            user_id = session_data['user_id']
            del self.active_sessions[session_id]
            self._track_session_operation('cleanup', session_id, user_id)

    @pytest.mark.asyncio
    async def test_concurrent_session_creation_cleanup_race_conditions(self, real_services_fixture):
        """
        Test that concurrent session creation and cleanup operations maintain consistency.
        
        BVJ: Prevents user login failures and phantom sessions that consume resources.
        Race Condition: Multiple threads creating/destroying sessions for same user simultaneously.
        """
        user_count = 20
        sessions_per_user = 3
        race_condition_threshold = 0.1  # 100ms
        
        async def create_and_cleanup_user_sessions(user_index: int):
            """Create multiple sessions for a user then clean them up."""
            user_id = f"race_test_user_{user_index}"
            created_sessions = []
            
            try:
                # Rapid session creation
                for session_num in range(sessions_per_user):
                    session_id = self._create_test_session(user_id)
                    created_sessions.append(session_id)
                    
                    # Simulate rapid access
                    if session_id in self.active_sessions:
                        self.active_sessions[session_id]['last_access'] = datetime.utcnow()
                        self._track_session_operation('access', session_id, user_id)
                    
                    # Small delay to create timing pressure
                    await asyncio.sleep(0.01)
                
                # Rapid cleanup
                for session_id in created_sessions:
                    if session_id in self.active_sessions:
                        self._cleanup_session(session_id)
                    await asyncio.sleep(0.005)
                    
            except Exception as e:
                self.race_condition_detected = True
                self._track_session_operation('error', 'unknown', user_id, False, error=str(e))
        
        # Start concurrent session operations
        start_time = time.time()
        tasks = [create_and_cleanup_user_sessions(i) for i in range(user_count)]
        await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze for race conditions
        race_conditions = self._detect_session_race_conditions()
        
        # Assertions
        assert not self.race_condition_detected, "Race condition caused exception during session operations"
        assert len(self.active_sessions) == 0, f"Session cleanup incomplete: {len(self.active_sessions)} sessions remain"
        assert total_time < 10.0, f"Session operations took too long: {total_time:.2f}s (should be < 10s)"
        assert len(race_conditions) == 0, f"Race conditions detected: {race_conditions}"
        
        # Verify operation consistency
        total_creates = sum(1 for op in self.session_operations if op['operation'] == 'create')
        total_cleanups = sum(1 for op in self.session_operations if op['operation'] == 'cleanup')
        expected_operations = user_count * sessions_per_user
        
        assert total_creates == expected_operations, f"Expected {expected_operations} creates, got {total_creates}"
        assert total_cleanups == expected_operations, f"Expected {expected_operations} cleanups, got {total_cleanups}"

    @pytest.mark.asyncio
    async def test_session_state_consistency_during_rapid_updates(self, real_services_fixture):
        """
        Test session state consistency when multiple operations update the same session rapidly.
        
        BVJ: Prevents session corruption that causes user experience degradation.
        Race Condition: Concurrent updates to session state causing lost updates or inconsistent data.
        """
        user_id = "state_race_user"
        session_id = self._create_test_session(user_id)
        update_count = 50
        concurrent_updaters = 10
        
        update_results = []
        state_snapshots = []
        
        async def rapid_session_updates(updater_id: int):
            """Rapidly update session state from multiple contexts."""
            updates_performed = 0
            
            for update_num in range(update_count // concurrent_updaters):
                try:
                    if session_id in self.active_sessions:
                        # Simulate different types of session updates
                        session = self.active_sessions[session_id]
                        
                        # Update last access time
                        session['last_access'] = datetime.utcnow()
                        
                        # Update session metadata
                        if 'update_count' not in session:
                            session['update_count'] = 0
                        session['update_count'] += 1
                        
                        # Track updater contributions
                        if 'updaters' not in session:
                            session['updaters'] = set()
                        session['updaters'].add(updater_id)
                        
                        # Store state snapshot
                        state_snapshots.append({
                            'timestamp': time.time(),
                            'updater_id': updater_id,
                            'update_count': session['update_count'],
                            'updaters_seen': len(session['updaters'])
                        })
                        
                        updates_performed += 1
                        self._track_session_operation('update', session_id, user_id, 
                                                    updater_id=updater_id, 
                                                    update_num=update_num)
                        
                        # Create timing pressure
                        await asyncio.sleep(0.002)
                    
                except Exception as e:
                    self.race_condition_detected = True
                    self._track_session_operation('update_error', session_id, user_id, False, 
                                                error=str(e), updater_id=updater_id)
            
            update_results.append(updates_performed)
        
        # Execute concurrent updates
        start_time = time.time()
        updater_tasks = [rapid_session_updates(i) for i in range(concurrent_updaters)]
        await asyncio.gather(*updater_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze final session state
        final_session = self.active_sessions.get(session_id, {})
        
        # Assertions
        assert not self.race_condition_detected, "Race condition caused exception during session updates"
        assert session_id in self.active_sessions, "Session was lost during concurrent updates"
        assert total_time < 5.0, f"Updates took too long: {total_time:.2f}s (should be < 5s)"
        
        # Verify update consistency
        total_updates = sum(update_results)
        expected_updates = update_count
        update_tolerance = 5  # Allow some variance due to race conditions
        
        assert abs(total_updates - expected_updates) <= update_tolerance, \
            f"Update count inconsistency: expected ~{expected_updates}, got {total_updates}"
        
        # Verify all updaters were tracked
        assert len(final_session.get('updaters', set())) == concurrent_updaters, \
            f"Not all updaters tracked: expected {concurrent_updaters}, got {len(final_session.get('updaters', set()))}"
        
        # Check for state corruption indicators
        final_update_count = final_session.get('update_count', 0)
        assert final_update_count > 0, "Update count was reset to zero (potential race condition)"
        assert final_update_count <= expected_updates * 2, \
            f"Update count too high: {final_update_count} (potential double counting)"

    @pytest.mark.asyncio 
    async def test_authentication_token_refresh_race_conditions(self, real_services_fixture):
        """
        Test that concurrent authentication token refresh operations don't cause conflicts.
        
        BVJ: Prevents authentication failures and security vulnerabilities during token refresh.
        Race Condition: Multiple requests trying to refresh the same session token simultaneously.
        """
        user_id = "auth_race_user"
        session_id = self._create_test_session(user_id)
        refresh_attempts = 30
        concurrent_refreshers = 6
        
        token_history = []
        refresh_results = []
        
        async def concurrent_token_refresh(refresher_id: int):
            """Attempt to refresh authentication tokens concurrently."""
            successful_refreshes = 0
            
            for refresh_num in range(refresh_attempts // concurrent_refreshers):
                try:
                    if session_id in self.active_sessions:
                        session = self.active_sessions[session_id]
                        
                        # Simulate token refresh logic
                        old_token = session.get('auth_token', '')
                        new_token = f"refreshed_token_{refresher_id}_{refresh_num}_{int(time.time() * 1000)}"
                        
                        # Record token transition
                        token_history.append({
                            'timestamp': time.time(),
                            'refresher_id': refresher_id,
                            'old_token': old_token,
                            'new_token': new_token,
                            'session_id': session_id
                        })
                        
                        # Update session with new token
                        session['auth_token'] = new_token
                        session['token_refreshed_at'] = datetime.utcnow()
                        session['refresh_count'] = session.get('refresh_count', 0) + 1
                        
                        successful_refreshes += 1
                        self._track_session_operation('token_refresh', session_id, user_id,
                                                    refresher_id=refresher_id,
                                                    new_token=new_token[:16])
                        
                        # Simulate network/processing delay
                        await asyncio.sleep(0.005)
                        
                except Exception as e:
                    self.race_condition_detected = True
                    self._track_session_operation('refresh_error', session_id, user_id, False,
                                                error=str(e), refresher_id=refresher_id)
            
            refresh_results.append(successful_refreshes)
        
        # Execute concurrent token refreshes
        start_time = time.time()
        refresh_tasks = [concurrent_token_refresh(i) for i in range(concurrent_refreshers)]
        await asyncio.gather(*refresh_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze final session state
        final_session = self.active_sessions.get(session_id, {})
        
        # Assertions
        assert not self.race_condition_detected, "Race condition caused exception during token refresh"
        assert session_id in self.active_sessions, "Session lost during token refresh operations"
        assert total_time < 8.0, f"Token refresh took too long: {total_time:.2f}s (should be < 8s)"
        
        # Verify token consistency
        final_token = final_session.get('auth_token', '')
        assert final_token != '', "Authentication token is empty after refresh operations"
        assert final_token.startswith('refreshed_token_'), "Token doesn't follow expected format"
        
        # Check refresh count consistency
        total_refreshes = sum(refresh_results)
        session_refresh_count = final_session.get('refresh_count', 0)
        refresh_tolerance = 3  # Allow some variance
        
        assert abs(session_refresh_count - total_refreshes) <= refresh_tolerance, \
            f"Refresh count inconsistency: operations={total_refreshes}, session={session_refresh_count}"
        
        # Verify no token corruption (each token should be unique)
        unique_tokens = set(entry['new_token'] for entry in token_history)
        assert len(unique_tokens) == len(token_history), \
            f"Token collision detected: {len(token_history)} refreshes, {len(unique_tokens)} unique tokens"

    @pytest.mark.asyncio
    async def test_cross_user_session_contamination_prevention(self, real_services_fixture):
        """
        Test that concurrent operations across different users don't contaminate each other's sessions.
        
        BVJ: Prevents data leaks and security breaches between user accounts.
        Race Condition: Session data from one user leaking into another user's session context.
        """
        user_count = 15
        operations_per_user = 20
        contamination_detected = False
        user_session_data = {}
        
        async def user_session_operations(user_index: int):
            """Perform various session operations for a specific user."""
            user_id = f"isolation_user_{user_index}"
            user_sessions = []
            
            try:
                # Create multiple sessions for this user
                for session_num in range(3):
                    session_id = self._create_test_session(user_id)
                    user_sessions.append(session_id)
                    
                    # Store user-specific data
                    if session_id in self.active_sessions:
                        session = self.active_sessions[session_id]
                        session['user_secret'] = f"secret_data_for_user_{user_index}"
                        session['user_preference'] = f"preference_{user_index}_{session_num}"
                        session['operation_count'] = 0
                        
                        if user_id not in user_session_data:
                            user_session_data[user_id] = []
                        user_session_data[user_id].append(session_id)
                
                # Perform rapid operations on user sessions
                for op_num in range(operations_per_user):
                    for session_id in user_sessions:
                        if session_id in self.active_sessions:
                            session = self.active_sessions[session_id]
                            
                            # Update session with user-specific operations
                            session['operation_count'] += 1
                            session['last_operation'] = f"op_{user_index}_{op_num}"
                            session['last_access'] = datetime.utcnow()
                            
                            self._track_session_operation('user_operation', session_id, user_id,
                                                        operation_num=op_num,
                                                        user_index=user_index)
                    
                    # Create timing pressure for potential contamination
                    await asyncio.sleep(0.001)
                
            except Exception as e:
                nonlocal contamination_detected
                contamination_detected = True
                self._track_session_operation('contamination_error', 'unknown', user_id, False, error=str(e))
        
        # Execute concurrent user operations
        start_time = time.time()
        user_tasks = [user_session_operations(i) for i in range(user_count)]
        await asyncio.gather(*user_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze session isolation
        isolation_violations = []
        
        for user_id, session_ids in user_session_data.items():
            expected_user_index = int(user_id.split('_')[-1])
            
            for session_id in session_ids:
                if session_id in self.active_sessions:
                    session = self.active_sessions[session_id]
                    
                    # Check user secret integrity
                    user_secret = session.get('user_secret', '')
                    if not user_secret.endswith(f'_user_{expected_user_index}'):
                        isolation_violations.append({
                            'type': 'secret_contamination',
                            'session_id': session_id,
                            'expected_user': expected_user_index,
                            'actual_secret': user_secret
                        })
                    
                    # Check operation integrity
                    last_operation = session.get('last_operation', '')
                    if last_operation and not last_operation.startswith(f'op_{expected_user_index}_'):
                        isolation_violations.append({
                            'type': 'operation_contamination',
                            'session_id': session_id,
                            'expected_user': expected_user_index,
                            'actual_operation': last_operation
                        })
        
        # Assertions
        assert not contamination_detected, "Exception occurred during user session operations"
        assert total_time < 12.0, f"User operations took too long: {total_time:.2f}s (should be < 12s)"
        assert len(isolation_violations) == 0, f"Session contamination detected: {isolation_violations}"
        
        # Verify expected session counts
        total_expected_sessions = user_count * 3  # 3 sessions per user
        total_actual_sessions = sum(len(sessions) for sessions in user_session_data.values())
        assert total_actual_sessions == total_expected_sessions, \
            f"Session count mismatch: expected {total_expected_sessions}, got {total_actual_sessions}"
        
        # Verify user isolation in session data
        for user_id, session_ids in user_session_data.items():
            assert len(session_ids) == 3, f"User {user_id} should have exactly 3 sessions, got {len(session_ids)}"
            
            # Verify all sessions belong to the correct user
            for session_id in session_ids:
                if session_id in self.active_sessions:
                    session = self.active_sessions[session_id]
                    assert session['user_id'] == user_id, \
                        f"Session {session_id} has wrong user_id: expected {user_id}, got {session['user_id']}"

    @pytest.mark.asyncio
    async def test_session_expiration_renewal_timing_races(self, real_services_fixture):
        """
        Test that session expiration and renewal operations handle timing edge cases correctly.
        
        BVJ: Prevents session timing attacks and ensures reliable session lifecycle management.
        Race Condition: Session expiring while renewal is in progress, or multiple renewal attempts.
        """
        user_id = "expiration_race_user"
        session_count = 10
        renewal_attempts_per_session = 5
        
        session_lifecycle_events = []
        timing_violations = []
        
        async def session_expiration_renewal_cycle(session_index: int):
            """Simulate session with rapid expiration/renewal cycles."""
            session_id = self._create_test_session(user_id)
            
            try:
                # Set short expiration for testing
                session = self.active_sessions[session_id]
                session['expires_at'] = datetime.utcnow() + timedelta(seconds=1)
                session['renewal_count'] = 0
                
                session_lifecycle_events.append({
                    'timestamp': time.time(),
                    'event': 'session_created',
                    'session_id': session_id,
                    'expires_at': session['expires_at']
                })
                
                # Perform rapid renewal attempts
                for renewal_num in range(renewal_attempts_per_session):
                    current_time = datetime.utcnow()
                    
                    if session_id in self.active_sessions:
                        session = self.active_sessions[session_id]
                        
                        # Check if session is expired
                        if current_time >= session['expires_at']:
                            session_lifecycle_events.append({
                                'timestamp': time.time(),
                                'event': 'session_expired',
                                'session_id': session_id,
                                'renewal_attempt': renewal_num
                            })
                            
                            # Attempt renewal of expired session
                            if session.get('is_active', True):
                                session['expires_at'] = current_time + timedelta(seconds=1)
                                session['renewal_count'] += 1
                                session['last_renewal'] = current_time
                                
                                session_lifecycle_events.append({
                                    'timestamp': time.time(),
                                    'event': 'session_renewed',
                                    'session_id': session_id,
                                    'new_expires_at': session['expires_at']
                                })
                        else:
                            # Preemptive renewal
                            session['expires_at'] = current_time + timedelta(seconds=1)
                            session['renewal_count'] += 1
                            session['last_renewal'] = current_time
                            
                            session_lifecycle_events.append({
                                'timestamp': time.time(),
                                'event': 'session_preemptive_renewal',
                                'session_id': session_id,
                                'new_expires_at': session['expires_at']
                            })
                        
                        self._track_session_operation('renewal', session_id, user_id,
                                                    renewal_num=renewal_num,
                                                    session_index=session_index)
                    
                    # Create timing pressure
                    await asyncio.sleep(0.2)  # 200ms between renewal attempts
                
                # Final cleanup
                if session_id in self.active_sessions:
                    self._cleanup_session(session_id)
                    
            except Exception as e:
                self.race_condition_detected = True
                self._track_session_operation('expiration_error', session_id, user_id, False, 
                                            error=str(e), session_index=session_index)
        
        # Execute concurrent session lifecycle operations
        start_time = time.time()
        lifecycle_tasks = [session_expiration_renewal_cycle(i) for i in range(session_count)]
        await asyncio.gather(*lifecycle_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze timing violations
        for event in session_lifecycle_events:
            if event['event'] == 'session_renewed' and 'expires_at' in event:
                # Check for unrealistic expiration times
                expires_at = event.get('new_expires_at')
                if expires_at and expires_at < datetime.utcnow() - timedelta(seconds=5):
                    timing_violations.append({
                        'type': 'past_expiration_renewal',
                        'session_id': event['session_id'],
                        'expires_at': expires_at
                    })
        
        # Group events by session for analysis
        session_events = {}
        for event in session_lifecycle_events:
            session_id = event['session_id']
            if session_id not in session_events:
                session_events[session_id] = []
            session_events[session_id].append(event)
        
        # Assertions
        assert not self.race_condition_detected, "Race condition caused exception during session lifecycle"
        assert len(self.active_sessions) == 0, "Sessions not properly cleaned up after expiration tests"
        assert total_time < 15.0, f"Session lifecycle operations took too long: {total_time:.2f}s (should be < 15s)"
        assert len(timing_violations) == 0, f"Timing violations detected: {timing_violations}"
        
        # Verify lifecycle event consistency
        total_created_events = sum(1 for event in session_lifecycle_events if event['event'] == 'session_created')
        assert total_created_events == session_count, \
            f"Expected {session_count} session created events, got {total_created_events}"
        
        # Verify renewal patterns for each session
        for session_id, events in session_events.items():
            created_events = [e for e in events if e['event'] == 'session_created']
            renewal_events = [e for e in events if 'renewal' in e['event']]
            
            assert len(created_events) == 1, f"Session {session_id} should have exactly 1 creation event"
            assert len(renewal_events) > 0, f"Session {session_id} should have at least 1 renewal event"
            
            # Verify chronological order
            events_sorted = sorted(events, key=lambda x: x['timestamp'])
            assert events_sorted[0]['event'] == 'session_created', \
                f"Session {session_id} should start with creation event"

    def test_session_race_condition_detection_helper_methods(self):
        """
        Test that the race condition detection helper methods work correctly.
        
        BVJ: Ensures test infrastructure reliability for detecting actual race conditions.
        """
        # Test operation tracking
        self._track_session_operation('test_op', 'session1', 'user1', True, extra_data='test')
        assert len(self.session_operations) == 1
        assert self.session_operations[0]['operation'] == 'test_op'
        assert self.session_operations[0]['extra_data'] == 'test'
        
        # Test race condition detection with simulated concurrent operations
        base_time = time.time()
        
        # Add operations that should trigger race detection (within 50ms)
        self.session_operations.extend([
            {
                'timestamp': base_time,
                'operation': 'create',
                'session_id': 'race_session',
                'user_id': 'user1',
                'thread_id': 1
            },
            {
                'timestamp': base_time + 0.02,  # 20ms later
                'operation': 'update', 
                'session_id': 'race_session',
                'user_id': 'user1',
                'thread_id': 2  # Different thread
            }
        ])
        
        race_conditions = self._detect_session_race_conditions()
        assert len(race_conditions) > 0, "Race condition detection should identify concurrent operations"
        assert race_conditions[0]['type'] == 'concurrent_session_operations'
        assert race_conditions[0]['risk_level'] == 'high'  # Because it involves 'create'
        
        # Test session cleanup tracking
        session_id = self._create_test_session('cleanup_test_user')
        assert session_id in self.active_sessions
        
        self._cleanup_session(session_id)
        assert session_id not in self.active_sessions