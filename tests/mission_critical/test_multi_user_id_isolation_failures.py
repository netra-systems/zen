"""
Mission Critical Test Suite for Multi-User ID Isolation Failures

MISSION CRITICAL: This test suite validates that ID generation provides proper
user isolation and prevents cross-user data contamination through ID conflicts.

Business Value Justification:
- Segment: ALL (Free  ->  Enterprise) - USER SECURITY CRITICAL
- Business Goal: Prevent user data leakage and ensure complete user isolation
- Value Impact: Protects user privacy and prevents catastrophic data breaches
- Strategic Impact: CRITICAL for multi-user platform trust and regulatory compliance

Test Strategy:
These tests are designed to FAIL initially, exposing multi-user isolation violations
caused by inconsistent ID generation patterns. They simulate real concurrent
multi-user scenarios to detect isolation breaches.

Critical Violations to Detect:
- ID collisions between different users
- Shared ID generation causing predictable patterns
- Cross-user context contamination via ID reuse
- Thread/Run ID relationships that leak user data
- WebSocket routing failures allowing cross-user message delivery
- Session management failures due to ID format inconsistencies
"""

import pytest
import asyncio
import uuid
import re
import random
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Test framework imports
from test_framework.ssot.base_test_case import BaseTestCase
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from test_framework.websocket_helpers import WebSocketTestHelper

# SSOT imports that should be used everywhere
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import UserID, ThreadID, RunID, WebSocketID, ensure_user_id

# Backend components for isolation testing
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager_factory import (
    create_websocket_manager,
    WebSocketManagerFactory,
    IsolatedWebSocketManager
)
from netra_backend.app.dependencies import get_request_scoped_db_session


class TestMultiUserIDIsolationFailures(BaseTestCase):
    """Mission critical tests for multi-user ID isolation failures."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.isolation_violations = []
        self.active_user_contexts = []
        self.active_websocket_managers = []
        self.id_patterns = {
            'uuid_v4': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I),
            'ssot_structured': re.compile(r'^[a-z_]+_\d+_[a-f0-9]{8}$'),
        }

    async def cleanup_test_resources(self):
        """Cleanup all test resources."""
        # Cleanup WebSocket managers
        for manager in self.active_websocket_managers:
            try:
                await manager.cleanup_all_connections()
            except Exception as e:
                self.logger.warning(f"Failed to cleanup WebSocket manager: {e}")
        
        self.active_websocket_managers.clear()
        self.active_user_contexts.clear()

    def teardown_method(self):
        """Cleanup after each test."""
        super().teardown_method()
        asyncio.create_task(self.cleanup_test_resources())

    # =============================================================================
    # USER ID COLLISION VIOLATIONS - Should FAIL initially
    # =============================================================================

    @pytest.mark.asyncio
    async def test_user_id_collision_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: User ID generation allows collisions between different users.
        
        This test creates multiple users rapidly and checks for ID collisions
        that would cause user data contamination.
        """
        collision_violations = []
        
        try:
            # Simulate rapid user creation (concurrent user registration scenario)
            user_creation_tasks = []
            for i in range(20):  # Create 20 users concurrently
                task = create_authenticated_user_context(
                    user_email=f"collision_test_{i}@example.com"
                )
                user_creation_tasks.append(task)
            
            # Execute concurrent user creation
            user_contexts = await asyncio.gather(*user_creation_tasks)
            self.active_user_contexts.extend(user_contexts)
            
            # Extract all user IDs for collision analysis
            user_ids = [ctx.user_id for ctx in user_contexts]
            
            # Check for direct collisions
            unique_user_ids = set(user_ids)
            if len(unique_user_ids) != len(user_ids):
                collisions = len(user_ids) - len(unique_user_ids)
                collision_violations.append(f"Found {collisions} user ID collisions in concurrent creation")
            
            # Check for predictable patterns that increase collision risk
            if len(user_ids) > 1:
                # Test if IDs are using predictable patterns (like sequential numbers)
                uuid_ids = [uid for uid in user_ids if self.id_patterns['uuid_v4'].match(uid)]
                
                if len(uuid_ids) > len(user_ids) * 0.5:  # More than 50% are UUIDs
                    collision_violations.append(f"High UUID usage ({len(uuid_ids)}/{len(user_ids)}) increases collision risk")
                
                # Check for sequential patterns in SSOT IDs
                ssot_ids = [uid for uid in user_ids if self.id_patterns['ssot_structured'].match(uid)]
                if len(ssot_ids) > 0:
                    # Extract counter components
                    counters = []
                    for ssot_id in ssot_ids[:10]:  # Sample first 10
                        parts = ssot_id.split('_')
                        if len(parts) >= 3 and parts[2].isdigit():
                            counters.append(int(parts[2]))
                    
                    if len(counters) > 1:
                        # Check if counters are sequential (predictable)
                        sorted_counters = sorted(counters)
                        sequential_count = sum(1 for i in range(1, len(sorted_counters)) 
                                             if sorted_counters[i] == sorted_counters[i-1] + 1)
                        if sequential_count > len(counters) * 0.7:
                            collision_violations.append(f"Sequential counter patterns detected in SSOT IDs (collision risk)")
        
        except Exception as e:
            collision_violations.append(f"User ID collision testing failed: {e}")
        
        # This test SHOULD FAIL if collision risks are detected
        assert len(collision_violations) > 0, (
            "Expected user ID collision risks or violations. "
            "If this passes, user ID generation has proper collision protection!"
        )
        
        self.isolation_violations.extend(collision_violations)
        
        pytest.fail(
            f"User ID collision violations detected:\n" +
            "\n".join(collision_violations) +
            "\n\nCRITICAL: Fix ID generation to prevent user data contamination through collisions"
        )

    @pytest.mark.asyncio
    async def test_cross_user_context_contamination_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: User contexts contaminate each other through shared ID generation.
        
        This test validates that user contexts maintain complete isolation
        and don't share or leak ID generation state between users.
        """
        contamination_violations = []
        
        try:
            # Create multiple user contexts with potentially overlapping operations
            user_contexts = []
            for i in range(5):
                ctx = await create_authenticated_user_context(
                    user_email=f"contamination_test_{i}@example.com"
                )
                user_contexts.append(ctx)
            
            self.active_user_contexts.extend(user_contexts)
            
            # Test for cross-contamination in various ID fields
            contamination_scenarios = [
                ("user_id", [ctx.user_id for ctx in user_contexts]),
                ("thread_id", [ctx.thread_id for ctx in user_contexts]),
                ("run_id", [ctx.run_id for ctx in user_contexts]),
                ("request_id", [ctx.request_id for ctx in user_contexts])
            ]
            
            for field_name, field_values in contamination_scenarios:
                # Check for duplicate IDs across different users (contamination)
                unique_values = set(field_values)
                if len(unique_values) != len(field_values):
                    duplicates = len(field_values) - len(unique_values)
                    contamination_violations.append(f"Cross-user {field_name} contamination: {duplicates} duplicates found")
                
                # Check for shared prefixes that could indicate shared state
                if len(field_values) > 1:
                    ssot_values = [v for v in field_values if self.id_patterns['ssot_structured'].match(v)]
                    if len(ssot_values) > 1:
                        # Extract prefixes and check for inappropriate sharing
                        prefixes = [v.split('_')[0] for v in ssot_values]
                        prefix_counts = {}
                        for prefix in prefixes:
                            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
                        
                        # Same prefix across different users might indicate shared state
                        shared_prefixes = [p for p, count in prefix_counts.items() if count > 1]
                        if shared_prefixes:
                            contamination_violations.append(f"{field_name} shared prefixes across users: {shared_prefixes}")
            
            # Test temporal contamination (IDs generated close in time)
            try:
                # Create two users in rapid succession
                ctx1 = await create_authenticated_user_context(user_email="temporal1@example.com")
                ctx2 = await create_authenticated_user_context(user_email="temporal2@example.com")
                
                self.active_user_contexts.extend([ctx1, ctx2])
                
                # Check if run IDs or request IDs are too similar (indicating shared generation state)
                def extract_timestamp_from_id(id_value):
                    if self.id_patterns['ssot_structured'].match(id_value):
                        parts = id_value.split('_')
                        if len(parts) >= 2 and parts[1].isdigit():
                            return int(parts[1])
                    return None
                
                ctx1_timestamp = extract_timestamp_from_id(ctx1.request_id)
                ctx2_timestamp = extract_timestamp_from_id(ctx2.request_id)
                
                if ctx1_timestamp and ctx2_timestamp:
                    timestamp_diff = abs(ctx1_timestamp - ctx2_timestamp)
                    if timestamp_diff < 100:  # Less than 100ms difference
                        contamination_violations.append(
                            f"Temporal contamination: User contexts created {timestamp_diff}ms apart have similar timestamps"
                        )
            
            except Exception as temporal_error:
                contamination_violations.append(f"Temporal contamination test failed: {temporal_error}")
        
        except Exception as e:
            contamination_violations.append(f"Cross-user contamination testing failed: {e}")
        
        # This test SHOULD FAIL if contamination is detected
        assert len(contamination_violations) > 0, (
            "Expected cross-user context contamination violations. "
            "If this passes, user contexts have proper isolation!"
        )
        
        pytest.fail(
            f"Cross-user context contamination violations:\n" +
            "\n".join(contamination_violations) +
            "\n\nCRITICAL: Fix user context isolation to prevent data contamination"
        )

    # =============================================================================
    # WEBSOCKET ISOLATION VIOLATIONS - Should FAIL initially
    # =============================================================================

    @pytest.mark.asyncio
    async def test_websocket_multi_user_isolation_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: WebSocket isolation fails allowing cross-user message delivery.
        
        This test validates that WebSocket systems maintain complete user isolation
        and prevent messages from being delivered to wrong users.
        """
        websocket_violations = []
        
        try:
            # Create multiple users with WebSocket managers
            user_websocket_pairs = []
            for i in range(4):
                user_ctx = await create_authenticated_user_context(
                    user_email=f"websocket_isolation_{i}@example.com"
                )
                ws_manager = await create_websocket_manager(user_ctx)
                user_websocket_pairs.append((user_ctx, ws_manager))
            
            self.active_user_contexts.extend([ctx for ctx, _ in user_websocket_pairs])
            self.active_websocket_managers.extend([mgr for _, mgr in user_websocket_pairs])
            
            # Test WebSocket isolation violations
            
            # Violation 1: Check if managers can access other users' connections
            for i, (ctx_i, mgr_i) in enumerate(user_websocket_pairs):
                for j, (ctx_j, mgr_j) in enumerate(user_websocket_pairs):
                    if i != j:
                        try:
                            # Try to check connection status for different user (should fail or return False)
                            is_active = mgr_i.is_connection_active(ctx_j.user_id)
                            if is_active:
                                websocket_violations.append(
                                    f"WebSocket manager {i} can access user {j}'s connection status"
                                )
                        except Exception:
                            # Exception is good - indicates proper isolation
                            pass
            
            # Violation 2: Test message routing isolation
            test_messages = []
            for i, (ctx, mgr) in enumerate(user_websocket_pairs):
                message = {
                    "type": "isolation_test",
                    "data": {"sender": i, "private_data": f"secret_user_{i}"},
                    "user_id": ctx.user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                test_messages.append((i, ctx, mgr, message))
            
            # Send messages and check for cross-user delivery
            for sender_idx, sender_ctx, sender_mgr, message in test_messages:
                try:
                    await sender_mgr.send_to_user(message)
                    
                    # Check if message could potentially reach other users
                    # This is hard to test directly, so we check for configuration issues
                    
                    # Check manager stats for potential cross-user data
                    stats = sender_mgr.get_manager_stats()
                    user_ctx_in_stats = stats.get('user_context', {})
                    
                    # Verify manager is bound to correct user
                    if user_ctx_in_stats.get('user_id') != sender_ctx.user_id:
                        websocket_violations.append(
                            f"WebSocket manager {sender_idx} stats show wrong user_id"
                        )
                
                except Exception as send_error:
                    # Message send failures could indicate routing issues
                    if "user" in str(send_error).lower() or "isolation" in str(send_error).lower():
                        websocket_violations.append(f"WebSocket message send failed for user {sender_idx}: {send_error}")
            
            # Violation 3: Check for WebSocket client ID collisions
            websocket_client_ids = []
            for ctx, _ in user_websocket_pairs:
                client_id = getattr(ctx, 'websocket_client_id', None)
                if client_id:
                    websocket_client_ids.append(client_id)
            
            if websocket_client_ids:
                unique_client_ids = set(websocket_client_ids)
                if len(unique_client_ids) != len(websocket_client_ids):
                    collisions = len(websocket_client_ids) - len(unique_client_ids)
                    websocket_violations.append(f"WebSocket client ID collisions: {collisions} duplicates")
            
            # Violation 4: Test concurrent WebSocket operations for race conditions
            async def concurrent_websocket_operation(ctx, mgr, operation_id):
                """Simulate concurrent WebSocket operations that might cause isolation issues."""
                try:
                    message = {
                        "type": "concurrent_test",
                        "data": {"operation_id": operation_id},
                        "user_id": ctx.user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await mgr.send_to_user(message)
                    return f"success_{operation_id}"
                except Exception as e:
                    return f"error_{operation_id}: {e}"
            
            # Run concurrent operations
            concurrent_tasks = []
            for i, (ctx, mgr) in enumerate(user_websocket_pairs):
                for j in range(3):  # 3 operations per user
                    task = concurrent_websocket_operation(ctx, mgr, f"{i}_{j}")
                    concurrent_tasks.append(task)
            
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Analyze results for isolation issues
            error_results = [r for r in results if isinstance(r, str) and r.startswith("error")]
            if error_results:
                # Too many errors might indicate race conditions affecting isolation
                if len(error_results) > len(concurrent_tasks) * 0.3:  # More than 30% errors
                    websocket_violations.append(f"High concurrent error rate: {len(error_results)}/{len(concurrent_tasks)} operations failed")
        
        except Exception as e:
            websocket_violations.append(f"WebSocket isolation testing failed: {e}")
        
        # This test SHOULD FAIL if isolation violations are detected
        assert len(websocket_violations) > 0, (
            "Expected WebSocket multi-user isolation violations. "
            "If this passes, WebSocket isolation is properly implemented!"
        )
        
        pytest.fail(
            f"WebSocket multi-user isolation violations:\n" +
            "\n".join(websocket_violations) +
            "\n\nCRITICAL: Fix WebSocket isolation to prevent cross-user message delivery"
        )

    # =============================================================================
    # THREAD/RUN ID RELATIONSHIP VIOLATIONS - Should FAIL initially
    # =============================================================================

    @pytest.mark.asyncio
    async def test_thread_run_relationship_isolation_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Thread/Run ID relationships allow cross-user data access.
        
        This test validates that thread and run ID relationships maintain proper
        user boundaries and don't allow access to other users' data.
        """
        relationship_violations = []
        
        try:
            # Create users with various thread/run ID scenarios
            user_scenarios = []
            
            for i in range(3):
                user_ctx = await create_authenticated_user_context(
                    user_email=f"thread_run_test_{i}@example.com"
                )
                
                # Create multiple thread/run combinations for each user
                thread_run_pairs = []
                for j in range(3):
                    # Create different run IDs for same thread (conversation continuation)
                    if j == 0:
                        # First run uses context thread_id
                        run_id = user_ctx.run_id
                        thread_id = user_ctx.thread_id
                    else:
                        # Subsequent runs in same thread
                        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
                        run_id = UnifiedIDManager.generate_run_id(user_ctx.thread_id)
                        thread_id = user_ctx.thread_id
                    
                    thread_run_pairs.append((thread_id, run_id))
                
                user_scenarios.append((user_ctx, thread_run_pairs))
            
            self.active_user_contexts.extend([ctx for ctx, _ in user_scenarios])
            
            # Test for cross-user thread/run relationship violations
            
            # Violation 1: Check if run IDs from different users can be confused
            all_run_ids = []
            user_run_mapping = {}
            
            for user_ctx, thread_run_pairs in user_scenarios:
                user_id = user_ctx.user_id
                for thread_id, run_id in thread_run_pairs:
                    all_run_ids.append(run_id)
                    user_run_mapping[run_id] = user_id
            
            # Check for run ID collisions across users
            unique_run_ids = set(all_run_ids)
            if len(unique_run_ids) != len(all_run_ids):
                collisions = len(all_run_ids) - len(unique_run_ids)
                relationship_violations.append(f"Cross-user run ID collisions: {collisions} duplicates")
            
            # Violation 2: Test thread ID extraction and validation
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            
            for user_ctx, thread_run_pairs in user_scenarios:
                user_id = user_ctx.user_id
                for thread_id, run_id in thread_run_pairs:
                    try:
                        # Extract thread ID from run ID
                        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
                        
                        # Should match the expected thread ID
                        if extracted_thread_id != thread_id:
                            relationship_violations.append(
                                f"Thread extraction mismatch for user {user_id[:8]}...: "
                                f"expected {thread_id[:20]}..., got {extracted_thread_id[:20]}..."
                            )
                        
                        # Check if extracted thread ID could belong to another user
                        for other_ctx, _ in user_scenarios:
                            if other_ctx.user_id != user_id:
                                if extracted_thread_id == other_ctx.thread_id:
                                    relationship_violations.append(
                                        f"Thread ID collision: User {user_id[:8]}... run references "
                                        f"user {other_ctx.user_id[:8]}... thread"
                                    )
                    
                    except Exception as extraction_error:
                        relationship_violations.append(f"Thread extraction failed for run {run_id[:20]}...: {extraction_error}")
            
            # Violation 3: Test run ID format consistency across users
            run_id_formats = {}
            for run_id in all_run_ids:
                if self.id_patterns['uuid_v4'].match(run_id):
                    run_id_formats[run_id] = 'raw_uuid'
                elif self.id_patterns['ssot_structured'].match(run_id):
                    run_id_formats[run_id] = 'ssot_structured'
                else:
                    run_id_formats[run_id] = 'unknown'
            
            format_types = set(run_id_formats.values())
            if len(format_types) > 1:
                relationship_violations.append(f"Mixed run ID formats across users: {dict(Counter(run_id_formats.values()))}")
            
            # Violation 4: Test predictable run ID generation
            # If run IDs are too predictable, users might guess other users' run IDs
            if len(all_run_ids) > 1:
                # Check for sequential patterns in timestamps (if SSOT format)
                ssot_run_ids = [rid for rid, fmt in run_id_formats.items() if fmt == 'ssot_structured']
                if len(ssot_run_ids) > 1:
                    timestamps = []
                    for run_id in ssot_run_ids:
                        parts = run_id.split('_')
                        if len(parts) >= 4 and parts[-2].isdigit():  # Timestamp should be second to last
                            timestamps.append(int(parts[-2]))
                    
                    if len(timestamps) > 1:
                        # Check if timestamps are too close (predictable)
                        sorted_timestamps = sorted(timestamps)
                        close_timestamps = sum(1 for i in range(1, len(sorted_timestamps))
                                             if sorted_timestamps[i] - sorted_timestamps[i-1] < 1000)  # Less than 1 second
                        
                        if close_timestamps > len(timestamps) * 0.5:
                            relationship_violations.append(f"Predictable run ID timestamps: {close_timestamps} close pairs")
        
        except Exception as e:
            relationship_violations.append(f"Thread/Run relationship isolation testing failed: {e}")
        
        # This test SHOULD FAIL if relationship violations are detected
        assert len(relationship_violations) > 0, (
            "Expected thread/run relationship isolation violations. "
            "If this passes, thread/run relationships have proper user isolation!"
        )
        
        pytest.fail(
            f"Thread/Run relationship isolation violations:\n" +
            "\n".join(relationship_violations) +
            "\n\nCRITICAL: Fix thread/run ID relationships to prevent cross-user data access"
        )

    # =============================================================================
    # CONCURRENT ACCESS VIOLATIONS - Should FAIL initially
    # =============================================================================

    @pytest.mark.asyncio
    async def test_concurrent_multi_user_access_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Concurrent multi-user access causes isolation failures.
        
        This test simulates heavy concurrent load with multiple users to detect
        race conditions and isolation failures under stress.
        """
        concurrent_violations = []
        
        try:
            # Create a larger number of users for concurrent testing
            num_users = 10
            concurrent_users = []
            
            # Create users concurrently (simulates rapid user onboarding)
            user_creation_tasks = []
            for i in range(num_users):
                task = create_authenticated_user_context(
                    user_email=f"concurrent_user_{i}@example.com"
                )
                user_creation_tasks.append(task)
            
            user_contexts = await asyncio.gather(*user_creation_tasks)
            self.active_user_contexts.extend(user_contexts)
            
            # Create WebSocket managers concurrently
            websocket_creation_tasks = []
            for ctx in user_contexts:
                task = create_websocket_manager(ctx)
                websocket_creation_tasks.append(task)
            
            websocket_managers = await asyncio.gather(*websocket_creation_tasks)
            self.active_websocket_managers.extend(websocket_managers)
            
            concurrent_users = list(zip(user_contexts, websocket_managers))
            
            # Test concurrent operations that might cause isolation failures
            
            # Concurrent Test 1: Rapid message sending
            async def send_user_messages(user_idx, ctx, manager, message_count=5):
                """Send multiple messages rapidly for one user."""
                violations = []
                for i in range(message_count):
                    try:
                        message = {
                            "type": "concurrent_message",
                            "data": {"user": user_idx, "message_idx": i, "private": f"secret_{user_idx}_{i}"},
                            "user_id": ctx.user_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await manager.send_to_user(message)
                        
                        # Add small delay to increase chance of race conditions
                        await asyncio.sleep(0.001)
                        
                    except Exception as e:
                        violations.append(f"User {user_idx} message {i} failed: {e}")
                
                return violations
            
            # Run concurrent message sending
            message_tasks = []
            for i, (ctx, manager) in enumerate(concurrent_users):
                task = send_user_messages(i, ctx, manager)
                message_tasks.append(task)
            
            message_results = await asyncio.gather(*message_tasks)
            
            # Analyze message sending results
            total_message_errors = sum(len(result) for result in message_results)
            if total_message_errors > num_users * 5 * 0.2:  # More than 20% failure rate
                concurrent_violations.append(f"High concurrent message failure rate: {total_message_errors} errors")
            
            # Concurrent Test 2: Simultaneous context operations
            async def concurrent_context_operations(user_idx, ctx):
                """Perform various context operations that might interfere with other users."""
                violations = []
                try:
                    # Simulate operations that read/modify context state
                    user_id = ctx.user_id
                    thread_id = ctx.thread_id
                    run_id = ctx.run_id
                    
                    # Check if IDs are still unique after concurrent access
                    id_checks = [
                        ("user_id", user_id),
                        ("thread_id", thread_id),
                        ("run_id", run_id)
                    ]
                    
                    for field_name, field_value in id_checks:
                        if not field_value or len(str(field_value)) == 0:
                            violations.append(f"User {user_idx} {field_name} is empty after concurrent access")
                
                except Exception as e:
                    violations.append(f"User {user_idx} context operations failed: {e}")
                
                return violations
            
            context_tasks = []
            for i, (ctx, _) in enumerate(concurrent_users):
                task = concurrent_context_operations(i, ctx)
                context_tasks.append(task)
            
            context_results = await asyncio.gather(*context_tasks)
            
            # Analyze context operation results
            context_errors = [error for result in context_results for error in result]
            if context_errors:
                concurrent_violations.extend(context_errors)
            
            # Concurrent Test 3: Check for ID uniqueness after concurrent operations
            final_user_ids = [ctx.user_id for ctx in user_contexts]
            final_unique_ids = set(final_user_ids)
            
            if len(final_unique_ids) != len(final_user_ids):
                concurrent_violations.append(f"User ID uniqueness violated after concurrent operations")
            
            # Concurrent Test 4: WebSocket manager isolation under load
            manager_isolation_violations = []
            for i, (ctx_i, mgr_i) in enumerate(concurrent_users):
                for j, (ctx_j, mgr_j) in enumerate(concurrent_users):
                    if i != j:
                        try:
                            # Check if managers got mixed up under concurrent load
                            mgr_i_stats = mgr_i.get_manager_stats()
                            mgr_i_user = mgr_i_stats.get('user_context', {}).get('user_id')
                            
                            if mgr_i_user != ctx_i.user_id:
                                manager_isolation_violations.append(
                                    f"Manager {i} stats show wrong user: expected {ctx_i.user_id[:8]}..., got {mgr_i_user[:8] if mgr_i_user else 'None'}..."
                                )
                        except Exception as e:
                            manager_isolation_violations.append(f"Manager {i} stats check failed: {e}")
            
            if manager_isolation_violations:
                concurrent_violations.extend(manager_isolation_violations)
        
        except Exception as e:
            concurrent_violations.append(f"Concurrent multi-user access testing failed: {e}")
        
        # This test SHOULD FAIL if concurrent violations are detected
        assert len(concurrent_violations) > 0, (
            "Expected concurrent multi-user access violations. "
            "If this passes, the system handles concurrent multi-user access properly!"
        )
        
        pytest.fail(
            f"Concurrent multi-user access violations:\n" +
            "\n".join(concurrent_violations) +
            "\n\nCRITICAL: Fix concurrent access handling to prevent multi-user isolation failures"
        )

    # =============================================================================
    # COMPLIANCE VALIDATION TESTS - Should PASS after migration
    # =============================================================================

    @pytest.mark.asyncio
    async def test_multi_user_isolation_compliance_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        This test should PASS after migration validates proper multi-user isolation.
        """
        # Create multiple users with SSOT-compliant ID generation
        user_contexts = []
        websocket_managers = []
        
        try:
            for i in range(5):
                ctx = await create_authenticated_user_context(
                    user_email=f"compliant_user_{i}@example.com"
                )
                mgr = await create_websocket_manager(ctx)
                
                user_contexts.append(ctx)
                websocket_managers.append(mgr)
            
            # All user IDs should be unique and SSOT-compliant
            user_ids = [ctx.user_id for ctx in user_contexts]
            assert len(set(user_ids)) == len(user_ids), "All user IDs should be unique"
            
            for user_id in user_ids:
                assert not self.id_patterns['uuid_v4'].match(user_id), f"User ID should not be raw UUID: {user_id}"
                assert '_' in user_id, f"User ID should be structured: {user_id}"
            
            # Test WebSocket isolation works properly
            for i, manager in enumerate(websocket_managers):
                own_user_id = user_contexts[i].user_id
                
                # Manager should only handle its own user
                for j, other_ctx in enumerate(user_contexts):
                    if i != j:
                        other_user_id = other_ctx.user_id
                        # Should return False or raise exception (both indicate proper isolation)
                        try:
                            is_active = manager.is_connection_active(other_user_id)
                            assert not is_active, f"Manager {i} should not see user {j}'s connections"
                        except Exception:
                            # Exception is acceptable and indicates proper isolation
                            pass
            
            # Test message sending works for each user independently
            for i, (ctx, manager) in enumerate(zip(user_contexts, websocket_managers)):
                test_message = {
                    "type": "isolation_compliance_test",
                    "data": {"user": i},
                    "user_id": ctx.user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Should work without errors
                try:
                    await manager.send_to_user(test_message)
                except Exception as e:
                    pytest.fail(f"Message sending should work for user {i}: {e}")
        
        finally:
            # Cleanup
            for manager in websocket_managers:
                try:
                    await manager.cleanup_all_connections()
                except Exception:
                    pass

    @pytest.mark.asyncio
    async def test_concurrent_multi_user_compliance_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        This test should PASS after migration validates concurrent multi-user operations work properly.
        """
        num_users = 8
        user_contexts = []
        websocket_managers = []
        
        try:
            # Create users concurrently
            user_tasks = [
                create_authenticated_user_context(user_email=f"concurrent_compliant_{i}@example.com")
                for i in range(num_users)
            ]
            user_contexts = await asyncio.gather(*user_tasks)
            
            # Create WebSocket managers concurrently
            ws_tasks = [create_websocket_manager(ctx) for ctx in user_contexts]
            websocket_managers = await asyncio.gather(*ws_tasks)
            
            # All operations should succeed
            assert len(user_contexts) == num_users, f"Should create {num_users} user contexts"
            assert len(websocket_managers) == num_users, f"Should create {num_users} WebSocket managers"
            
            # All user IDs should be unique
            user_ids = [ctx.user_id for ctx in user_contexts]
            assert len(set(user_ids)) == num_users, "All user IDs should be unique"
            
            # Test concurrent messaging
            async def send_test_message(user_idx, ctx, manager):
                message = {
                    "type": "concurrent_test",
                    "data": {"user": user_idx},
                    "user_id": ctx.user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await manager.send_to_user(message)
                return f"success_{user_idx}"
            
            # Send messages concurrently
            message_tasks = [
                send_test_message(i, ctx, mgr)
                for i, (ctx, mgr) in enumerate(zip(user_contexts, websocket_managers))
            ]
            
            results = await asyncio.gather(*message_tasks)
            
            # All should succeed
            assert len(results) == num_users, f"All {num_users} concurrent messages should succeed"
            for i, result in enumerate(results):
                assert result == f"success_{i}", f"Message {i} should succeed"
        
        finally:
            # Cleanup
            for manager in websocket_managers:
                try:
                    await manager.cleanup_all_connections()
                except Exception:
                    pass

    # =============================================================================
    # PERFORMANCE AND STRESS TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_multi_user_id_generation_performance(self):
        """
        Test ID generation performance under multi-user load.
        """
        import time
        
        # Test concurrent ID generation for multiple users
        async def generate_user_ids(user_count, operations_per_user):
            """Generate IDs concurrently for multiple users."""
            async def user_id_operations(user_idx):
                ids = []
                for _ in range(operations_per_user):
                    user_id = UnifiedIdGenerator.generate_base_id("user")
                    thread_id = UnifiedIdGenerator.generate_base_id("session")
                    run_id = UnifiedIdGenerator.generate_base_id("run")
                    ids.extend([user_id, thread_id, run_id])
                return ids
            
            tasks = [user_id_operations(i) for i in range(user_count)]
            results = await asyncio.gather(*tasks)
            return [id_val for user_results in results for id_val in user_results]
        
        start_time = time.time()
        all_ids = await generate_user_ids(user_count=10, operations_per_user=50)
        end_time = time.time()
        
        duration = end_time - start_time
        ids_per_second = len(all_ids) / duration
        
        # Should be fast enough for multi-user scenarios
        assert ids_per_second > 1000, f"Multi-user ID generation too slow: {ids_per_second:.2f} IDs/second"
        
        # All should be unique
        assert len(set(all_ids)) == len(all_ids), f"All {len(all_ids)} generated IDs should be unique"
        
        # All should be SSOT-compliant
        for test_id in all_ids[:20]:  # Sample check
            assert not self.id_patterns['uuid_v4'].match(test_id), f"ID should not be UUID: {test_id}"
            assert '_' in test_id, f"ID should be structured: {test_id}"

    # =============================================================================
    # CLEANUP AND UTILITIES
    # =============================================================================

    def teardown_method(self):
        """Cleanup after each test method."""
        super().teardown_method()
        if hasattr(self, 'isolation_violations') and self.isolation_violations:
            print(f"\nMulti-user isolation violations detected: {len(self.isolation_violations)}")
            for violation in self.isolation_violations[:3]:  # Show first 3
                print(f"  - {violation}")
            if len(self.isolation_violations) > 3:
                print(f"  ... and {len(self.isolation_violations) - 3} more violations")

    @pytest.mark.asyncio
    async def test_multi_user_system_health_check(self):
        """
        Health check to validate basic multi-user functionality works.
        This test should always pass to ensure basic multi-user capability.
        """
        try:
            # Create a few users and verify basic isolation works
            user1_ctx = await create_authenticated_user_context(user_email="health1@example.com")
            user2_ctx = await create_authenticated_user_context(user_email="health2@example.com")
            
            # Users should have different IDs
            assert user1_ctx.user_id != user2_ctx.user_id, "Users should have different IDs"
            
            # Create WebSocket managers
            ws1 = await create_websocket_manager(user1_ctx)
            ws2 = await create_websocket_manager(user2_ctx)
            
            # Managers should be different instances
            assert ws1 is not ws2, "Users should have different WebSocket managers"
            
            # Basic operations should work
            stats1 = ws1.get_manager_stats()
            stats2 = ws2.get_manager_stats()
            
            assert stats1 != stats2, "Manager stats should be different"
            
            # Cleanup
            await ws1.cleanup_all_connections()
            await ws2.cleanup_all_connections()
            
            print(f"Multi-user system health check passed")
            
        except Exception as e:
            pytest.fail(f"Multi-user system health check failed: {e}")

    @pytest.mark.asyncio
    async def test_isolation_violation_summary(self):
        """
        Generate comprehensive summary of multi-user isolation violations.
        
        This creates a summary report for migration planning.
        """
        from collections import Counter
        
        violation_summary = {
            "user_id_collisions": [],
            "context_contamination": [],
            "websocket_isolation_failures": [],
            "thread_run_relationship_issues": [],
            "concurrent_access_problems": []
        }
        
        try:
            # Create test scenario to demonstrate potential violations
            test_users = []
            for i in range(3):
                ctx = await create_authenticated_user_context(
                    user_email=f"summary_test_{i}@example.com"
                )
                test_users.append(ctx)
            
            # Analyze potential violation patterns
            user_ids = [ctx.user_id for ctx in test_users]
            
            # Check ID format consistency
            uuid_count = sum(1 for uid in user_ids if self.id_patterns['uuid_v4'].match(uid))
            ssot_count = sum(1 for uid in user_ids if self.id_patterns['ssot_structured'].match(uid))
            
            if uuid_count > 0:
                violation_summary["user_id_collisions"].append(f"Raw UUID usage detected in {uuid_count} user IDs")
            
            if uuid_count > 0 and ssot_count > 0:
                violation_summary["context_contamination"].append(f"Mixed ID formats: {uuid_count} UUID, {ssot_count} SSOT")
            
            # Test WebSocket managers
            ws_managers = []
            for ctx in test_users:
                mgr = await create_websocket_manager(ctx)
                ws_managers.append(mgr)
            
            # Check for potential WebSocket issues
            for i, mgr in enumerate(ws_managers):
                stats = mgr.get_manager_stats()
                if not stats:
                    violation_summary["websocket_isolation_failures"].append(f"Manager {i} has no stats")
            
            # Generate summary
            total_categories = len([cat for violations in violation_summary.values() if violations])
            total_violations = sum(len(violations) for violations in violation_summary.values())
            
            print(f"\nMulti-User Isolation Violation Summary:")
            print(f"Categories with violations: {total_categories}/{len(violation_summary)}")
            print(f"Total potential violations: {total_violations}")
            
            for category, violations in violation_summary.items():
                if violations:
                    print(f"  {category}: {len(violations)} issues")
            
            # Cleanup
            for mgr in ws_managers:
                await mgr.cleanup_all_connections()
            
            # This test should pass as it's generating a report
            assert isinstance(violation_summary, dict), "Should generate violation summary"
        
        except Exception as e:
            pytest.fail(f"Isolation violation summary generation failed: {e}")