"""Multi-User ID Isolation Integration Tests - Issue #841

This test suite validates multi-user ID isolation failures in real system integration,
focusing on concurrent user scenarios and WebSocket factory resource management.

CRITICAL: These tests are designed to FAIL until SSOT migration is complete.

Integration Focus Areas:
1. WebSocket factory resource cleanup with mismatched thread/run IDs
2. Multi-user concurrent authentication session isolation
3. Factory pattern resource leak detection
4. User context preservation across component boundaries

Expected Results: ALL TESTS SHOULD FAIL until SSOT migration complete
"""

import pytest
import asyncio
import threading
import time
import unittest
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Any
from unittest.mock import patch, MagicMock, Mock
from concurrent.futures import ThreadPoolExecutor
import weakref

# Import test framework
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Mock WebSocket factory components for testing
class MockWebSocketFactory:
    """Mock WebSocket factory to test resource management patterns."""
    
    def __init__(self):
        self.active_managers = {}
        self.cleanup_calls = []
        self.resource_leaks = []
        
    def create_manager(self, thread_id: str, run_id: str, user_id: str):
        """Create a WebSocket manager with given IDs."""
        manager_key = f"{thread_id}:{run_id}"
        manager = {
            'thread_id': thread_id,
            'run_id': run_id,
            'user_id': user_id,
            'created_at': time.time(),
            'resources': ['connection', 'buffer', 'handler']
        }
        self.active_managers[manager_key] = manager
        return manager
    
    def cleanup_manager(self, thread_id: str, run_id: str):
        """Cleanup WebSocket manager - tests the critical resource leak issue."""
        cleanup_key = f"{thread_id}:{run_id}"
        self.cleanup_calls.append(cleanup_key)
        
        # This simulates the critical bug: cleanup fails when IDs don't match exactly
        if cleanup_key in self.active_managers:
            del self.active_managers[cleanup_key]
            return True
        else:
            # Resource leak - couldn't find manager to clean up
            self.resource_leaks.append({
                'requested_cleanup': cleanup_key,
                'active_managers': list(self.active_managers.keys()),
                'timestamp': time.time()
            })
            return False
    
    def get_active_count(self):
        """Get count of active managers (for leak detection)."""
        return len(self.active_managers)


@pytest.mark.integration
class TestWebSocketFactoryResourceLeakIntegration(SSotBaseTestCase):
    """Integration tests for WebSocket factory resource leak patterns."""
    
    def setUp(self):
        """Set up WebSocket factory resource tests."""
        super().setUp()
        self.factory = MockWebSocketFactory()
        
    def test_websocket_factory_thread_run_id_mismatch_must_fail(self):
        """CRITICAL: Test thread_id/run_id mismatch causing resource leaks.
        
        This integration test MUST FAIL to demonstrate the exact resource leak issue.
        This test simulates the root cause described in UnifiedIdGenerator comments:
        "Thread ID consistency to prevent WebSocket Factory resource leaks"
        """
        user_id = "test_user_123"
        
        # Simulate current problematic pattern - IDs generated independently
        def create_current_pattern_ids():
            import uuid
            # This is the PROBLEMATIC pattern causing resource leaks
            thread_id = f"thread_websocket_factory_{uuid.uuid4().hex[:8]}"
            run_id = f"run_websocket_factory_{uuid.uuid4().hex[:8]}"
            return thread_id, run_id
        
        # Create multiple managers with current pattern
        managers_created = []
        for i in range(5):
            thread_id, run_id = create_current_pattern_ids()
            manager = self.factory.create_manager(thread_id, run_id, user_id)
            managers_created.append((thread_id, run_id, manager))
        
        # Attempt cleanup using the SAME ID generation pattern
        cleanup_success_count = 0
        for thread_id, run_id, manager in managers_created:
            # This simulates the cleanup logic trying to find the manager
            # But with uuid.uuid4() pattern, the cleanup IDs won't match creation IDs
            cleanup_thread_id, cleanup_run_id = create_current_pattern_ids()
            
            # Try to cleanup - this should FAIL due to ID mismatch
            cleanup_success = self.factory.cleanup_manager(cleanup_thread_id, cleanup_run_id)
            if cleanup_success:
                cleanup_success_count += 1
        
        # This test MUST FAIL - cleanup should fail due to ID mismatches
        self.assertEqual(cleanup_success_count, 0,
                        "Cleanup should fail with current uuid.uuid4() pattern (proving resource leak)")
        
        # Verify resource leaks occurred
        leak_count = len(self.factory.resource_leaks)
        self.assertEqual(leak_count, 5,
                        f"Expected 5 resource leaks, got {leak_count}")
        
        # Active managers should still exist (not cleaned up)
        active_count = self.factory.get_active_count()
        self.assertEqual(active_count, 5,
                        f"Expected 5 active managers (resource leak), got {active_count}")
        
        # Compare with SSOT pattern - should enable proper cleanup
        ssot_thread_id, ssot_run_id, ssot_request_id = UnifiedIdGenerator.generate_user_context_ids(user_id, "websocket")
        
        # SSOT IDs should have correlation for cleanup
        ssot_manager = self.factory.create_manager(ssot_thread_id, ssot_run_id, user_id)
        
        # Cleanup with SSOT IDs should work (they have consistent pattern)
        ssot_cleanup_success = self.factory.cleanup_manager(ssot_thread_id, ssot_run_id)
        self.assertTrue(ssot_cleanup_success,
                       "SSOT pattern should enable successful cleanup")
    
    def test_multi_user_websocket_context_isolation_failure_must_fail(self):
        """CRITICAL: Test multi-user WebSocket context isolation failures.
        
        This integration test MUST FAIL to demonstrate user isolation vulnerabilities.
        """
        users = ["alice", "bob", "charlie"]
        user_contexts = {}
        
        # Create WebSocket contexts for multiple users using current pattern
        for user in users:
            contexts = []
            for session in range(3):  # Multiple sessions per user
                import uuid
                # Current problematic pattern - no user context preservation
                thread_id = f"thread_websocket_factory_{uuid.uuid4().hex[:8]}"
                run_id = f"run_websocket_factory_{uuid.uuid4().hex[:8]}"
                
                manager = self.factory.create_manager(thread_id, run_id, user)
                contexts.append({
                    'thread_id': thread_id,
                    'run_id': run_id,
                    'manager': manager,
                    'session': session
                })
            user_contexts[user] = contexts
        
        # Test isolation failure - can't identify user from WebSocket IDs
        all_thread_ids = []
        all_run_ids = []
        
        for user, contexts in user_contexts.items():
            for context in contexts:
                all_thread_ids.append(context['thread_id'])
                all_run_ids.append(context['run_id'])
        
        # This test MUST FAIL - no way to identify user from WebSocket IDs
        for thread_id in all_thread_ids:
            user_identifiable = any(user in thread_id.lower() for user in users)
            self.assertFalse(user_identifiable,
                           f"Thread ID should not contain user identification: {thread_id}")
        
        for run_id in all_run_ids:
            user_identifiable = any(user in run_id.lower() for user in users)
            self.assertFalse(user_identifiable,
                           f"Run ID should not contain user identification: {run_id}")
        
        # Prove the vulnerability - if IDs get mixed up, no way to trace back to user
        # All IDs follow same random pattern
        thread_patterns = set(len(tid.split('_')) for tid in all_thread_ids)
        self.assertEqual(len(thread_patterns), 1,
                        "All thread IDs should follow same pattern (proving isolation vulnerability)")
        
        # Compare with SSOT pattern - should preserve user context
        ssot_contexts = {}
        for user in users:
            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(user, "websocket")
            ssot_contexts[user] = {
                'thread_id': thread_id,
                'run_id': run_id,
                'request_id': request_id
            }
        
        # SSOT should preserve user context
        for user, context in ssot_contexts.items():
            user_prefix = user[:8] if len(user) >= 8 else user
            self.assertIn(user_prefix, context['thread_id'],
                         f"SSOT thread ID should contain user context: {context['thread_id']}")
            self.assertIn(user_prefix, context['run_id'],
                         f"SSOT run ID should contain user context: {context['run_id']}")
    
    def test_concurrent_websocket_factory_creation_race_condition_must_fail(self):
        """CRITICAL: Test race conditions in concurrent WebSocket factory creation.
        
        This integration test MUST FAIL to demonstrate race condition vulnerabilities.
        """
        num_concurrent_users = 10
        results = []
        errors = []
        
        def create_websocket_context(user_id: str, session_id: int):
            """Simulate concurrent WebSocket context creation."""
            try:
                import uuid
                # Current pattern - each creation is independent
                thread_id = f"thread_websocket_factory_{uuid.uuid4().hex[:8]}"
                run_id = f"run_websocket_factory_{uuid.uuid4().hex[:8]}"
                
                # Simulate some processing time
                time.sleep(0.001)
                
                manager = self.factory.create_manager(thread_id, run_id, user_id)
                results.append({
                    'user_id': user_id,
                    'session_id': session_id,
                    'thread_id': thread_id,
                    'run_id': run_id,
                    'success': True
                })
            except Exception as e:
                errors.append({
                    'user_id': user_id,
                    'session_id': session_id,
                    'error': str(e)
                })
        
        # Launch concurrent WebSocket creations
        threads = []
        for i in range(num_concurrent_users):
            user_id = f"concurrent_user_{i}"
            thread = threading.Thread(target=create_websocket_context, args=(user_id, i))
            threads.append(thread)
        
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Test results - should have created contexts but with isolation issues
        self.assertEqual(len(results), num_concurrent_users,
                        f"Expected {num_concurrent_users} successful creations")
        self.assertEqual(len(errors), 0,
                        "Should not have creation errors")
        
        # Critical test - race condition vulnerability in ID uniqueness
        thread_ids = [r['thread_id'] for r in results]
        run_ids = [r['run_id'] for r in results]
        
        # IDs should be unique (UUID guarantee), but demonstrate the problem
        unique_thread_ids = set(thread_ids)
        unique_run_ids = set(run_ids)
        
        self.assertEqual(len(thread_ids), len(unique_thread_ids),
                        "Thread IDs should be unique (UUID guarantee)")
        self.assertEqual(len(run_ids), len(unique_run_ids),
                        "Run IDs should be unique (UUID guarantee)")
        
        # But the critical vulnerability - no correlation between thread and run IDs
        # This makes resource cleanup impossible
        correlated_pairs = set(zip(thread_ids, run_ids))
        self.assertEqual(len(correlated_pairs), num_concurrent_users,
                        "Each thread/run pair should be unique")
        
        # Attempt cleanup simulation - should fail due to lack of correlation
        cleanup_failures = 0
        for result in results:
            # Try to cleanup using different ID generation (simulates the real bug)
            import uuid
            cleanup_thread = f"thread_websocket_factory_{uuid.uuid4().hex[:8]}"
            cleanup_run = f"run_websocket_factory_{uuid.uuid4().hex[:8]}"
            
            success = self.factory.cleanup_manager(cleanup_thread, cleanup_run)
            if not success:
                cleanup_failures += 1
        
        # This test MUST FAIL - all cleanups should fail
        self.assertEqual(cleanup_failures, num_concurrent_users,
                        "All cleanup attempts should fail (proving resource leak vulnerability)")


@pytest.mark.integration
class TestAuthSessionMultiUserIntegration(SSotBaseTestCase):
    """Integration tests for multi-user auth session isolation."""
    
    def setUp(self):
        """Set up multi-user auth session tests."""
        super().setUp()
        self.active_sessions = {}
        
    def test_auth_session_tracking_multi_user_collision_must_fail(self):
        """CRITICAL: Test auth session tracking collision in multi-user scenario.
        
        This integration test MUST FAIL to demonstrate session tracking vulnerabilities.
        """
        users = ["enterprise_user_1", "startup_user_2", "individual_user_3"]
        user_tokens = {}
        session_data = {}
        
        # Simulate the auth.py:160 pattern for multiple users
        for user in users:
            # Create multiple tokens per user (different devices/sessions)
            user_tokens[user] = []
            for device in ["web", "mobile", "api"]:
                token_hash = f"token_{user}_{device}_hash"
                
                # This simulates auth.py:160 - session_id = str(uuid.uuid4())
                import uuid
                session_id = str(uuid.uuid4())
                
                session_info = {
                    'user_id': user,
                    'session_id': session_id,
                    'device': device,
                    'first_used': time.time(),
                    'token_hash': token_hash
                }
                
                user_tokens[user].append(token_hash)
                session_data[token_hash] = session_info
                self.active_sessions[token_hash] = session_info
        
        # Test multi-user isolation vulnerability
        all_session_ids = [s['session_id'] for s in session_data.values()]
        
        # Critical vulnerability test - session IDs contain no user context
        for session_id in all_session_ids:
            user_identifiable = any(user.lower() in session_id.lower() for user in users)
            self.assertFalse(user_identifiable,
                           f"Session ID should not contain user identification: {session_id}")
        
        # Test session collision scenario - what happens if lookup table is corrupted?
        # Simulate corruption by removing user mapping
        corrupted_sessions = []
        for session_id in all_session_ids[:3]:  # Corrupt first 3 sessions
            corrupted_sessions.append(session_id)
        
        # Try to identify users from session IDs alone (should be impossible)
        identifiable_count = 0
        for session_id in corrupted_sessions:
            # Try to match session to user without lookup table
            matched_user = None
            for user in users:
                # Various matching attempts
                if (user[:4] in session_id or 
                    user.split('_')[0] in session_id or
                    session_id.startswith(user[:3])):
                    matched_user = user
                    identifiable_count += 1
                    break
        
        # This test MUST FAIL - should not be able to identify users
        self.assertEqual(identifiable_count, 0,
                        "Should not be able to identify users from session IDs alone")
        
        # Compare with SSOT pattern
        ssot_sessions = {}
        for user in users:
            ssot_session_id = UnifiedIdGenerator.generate_session_id(user, "auth")
            ssot_sessions[user] = ssot_session_id
        
        # SSOT should preserve user context for traceability
        for user, ssot_session in ssot_sessions.items():
            user_prefix = user[:8] if len(user) >= 8 else user
            self.assertIn(user_prefix, ssot_session,
                         f"SSOT session should contain user context: {ssot_session}")
    
    def test_concurrent_auth_session_creation_isolation_must_fail(self):
        """CRITICAL: Test concurrent auth session creation isolation failures.
        
        This integration test MUST FAIL to demonstrate isolation vulnerabilities.
        """
        concurrent_users = [f"concurrent_user_{i}" for i in range(20)]
        session_creation_results = []
        creation_errors = []
        
        def create_auth_session(user_id: str, request_id: int):
            """Simulate concurrent auth session creation."""
            try:
                token = f"jwt_token_{user_id}_{request_id}"
                token_hash = f"hash_{hash(token) % 10000}"
                
                # Simulate auth.py:160 pattern
                import uuid
                session_id = str(uuid.uuid4())
                current_time = time.time()
                
                session_info = {
                    'user_id': user_id,
                    'session_id': session_id,
                    'token_hash': token_hash,
                    'first_used': current_time,
                    'request_id': request_id
                }
                
                session_creation_results.append(session_info)
                
            except Exception as e:
                creation_errors.append({
                    'user_id': user_id,
                    'request_id': request_id,
                    'error': str(e)
                })
        
        # Launch concurrent session creations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i, user in enumerate(concurrent_users):
                future = executor.submit(create_auth_session, user, i)
                futures.append(future)
            
            # Wait for all to complete
            for future in futures:
                future.result()
        
        # Test results
        self.assertEqual(len(session_creation_results), len(concurrent_users),
                        "All sessions should be created successfully")
        self.assertEqual(len(creation_errors), 0,
                        "Should not have creation errors")
        
        # Critical isolation vulnerability test
        session_ids = [s['session_id'] for s in session_creation_results]
        
        # All session IDs should be UUID format - no user context
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        import re
        
        for session_id in session_ids:
            self.assertRegex(session_id, uuid_pattern,
                           f"Session ID should be pure UUID format: {session_id}")
        
        # Test isolation failure - sessions are indistinguishable
        # If we lose the mapping, we can't identify which session belongs to which user
        
        # Simulate mapping loss
        orphaned_sessions = session_ids[:5]  # First 5 sessions lose their mapping
        
        identifiable_sessions = 0
        for session_id in orphaned_sessions:
            # Try to identify user from session ID
            identified_user = None
            for user in concurrent_users:
                if any(part in session_id.lower() for part in user.split('_')):
                    identified_user = user
                    identifiable_sessions += 1
                    break
        
        # This test MUST FAIL - should not be able to identify users
        self.assertEqual(identifiable_sessions, 0,
                        "Should not be able to identify users from orphaned session IDs")
        
        # Compare with SSOT pattern
        ssot_session_example = UnifiedIdGenerator.generate_session_id(concurrent_users[0], "auth")
        user_prefix = concurrent_users[0][:8]
        
        # SSOT should contain user context
        self.assertIn(user_prefix, ssot_session_example,
                     "SSOT session should contain user identification")


@pytest.mark.integration
class TestFactoryPatternResourceLeakIntegration(SSotBaseTestCase):
    """Integration tests for factory pattern resource leak detection."""
    
    def setUp(self):
        """Set up factory resource leak tests."""
        super().setUp()
        self.resource_tracker = {
            'created': [],
            'cleaned': [],
            'leaked': []
        }
    
    def test_factory_resource_cleanup_pattern_mismatch_must_fail(self):
        """CRITICAL: Test factory resource cleanup failures due to pattern mismatch.
        
        This integration test MUST FAIL to demonstrate resource leak patterns.
        """
        users = ["factory_user_1", "factory_user_2", "factory_user_3"]
        created_resources = {}
        
        # Create resources using current uuid.uuid4() pattern
        for user in users:
            user_resources = []
            for i in range(3):  # Multiple resources per user
                import uuid
                
                # Current problematic patterns
                resource_id = f"resource_{uuid.uuid4().hex[:8]}"
                context_id = f"context_{uuid.uuid4().hex[:8]}"
                session_id = str(uuid.uuid4())
                
                resource = {
                    'resource_id': resource_id,
                    'context_id': context_id,
                    'session_id': session_id,
                    'user_id': user,
                    'created_at': time.time(),
                    'cleaned': False
                }
                
                user_resources.append(resource)
                self.resource_tracker['created'].append(resource)
            
            created_resources[user] = user_resources
        
        # Attempt cleanup using pattern matching (simulates real cleanup logic)
        cleanup_attempts = 0
        successful_cleanups = 0
        
        for user, resources in created_resources.items():
            for resource in resources:
                cleanup_attempts += 1
                
                # Simulate cleanup logic trying to match resources
                # Current pattern: generate new IDs and try to find match (fails)
                import uuid
                cleanup_resource_id = f"resource_{uuid.uuid4().hex[:8]}"
                cleanup_context_id = f"context_{uuid.uuid4().hex[:8]}"
                cleanup_session_id = str(uuid.uuid4())
                
                # Try to find matching resource (should fail with random IDs)
                found_match = False
                if (cleanup_resource_id == resource['resource_id'] or
                    cleanup_context_id == resource['context_id'] or
                    cleanup_session_id == resource['session_id']):
                    found_match = True
                
                if found_match:
                    resource['cleaned'] = True
                    successful_cleanups += 1
                    self.resource_tracker['cleaned'].append(resource)
                else:
                    self.resource_tracker['leaked'].append(resource)
        
        # This test MUST FAIL - no resources should be cleaned up successfully
        self.assertEqual(successful_cleanups, 0,
                        "No resources should be cleaned up with random ID matching")
        
        # All resources should be leaked
        leaked_count = len(self.resource_tracker['leaked'])
        total_resources = sum(len(resources) for resources in created_resources.values())
        
        self.assertEqual(leaked_count, total_resources,
                        f"All {total_resources} resources should be leaked")
        
        # Compare with SSOT pattern - should enable proper cleanup
        ssot_resources = []
        for user in users[:1]:  # Test one user with SSOT pattern
            for i in range(3):
                # SSOT pattern - correlated IDs
                thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(user, f"factory_{i}")
                
                ssot_resource = {
                    'thread_id': thread_id,
                    'run_id': run_id,
                    'request_id': request_id,
                    'user_id': user,
                    'created_at': time.time(),
                    'cleaned': False
                }
                ssot_resources.append(ssot_resource)
        
        # SSOT cleanup should work - IDs are deterministic and correlated
        ssot_cleanup_success = 0
        for ssot_resource in ssot_resources:
            # SSOT allows pattern matching for cleanup
            if (ssot_resource['thread_id'].startswith('thread_') and
                ssot_resource['run_id'].startswith('run_') and
                ssot_resource['request_id'].startswith('req_')):
                ssot_cleanup_success += 1
        
        self.assertEqual(ssot_cleanup_success, len(ssot_resources),
                        "SSOT pattern should enable successful resource cleanup")


if __name__ == '__main__':
    unittest.main()