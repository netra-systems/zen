"""
Test Thread Routing Race Conditions

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Thread safety and data integrity in concurrent scenarios
- Value Impact: Race conditions cause data corruption and user isolation failures
- Strategic Impact: Multi-user platform reliability - concurrent users must be isolated

This test suite validates thread routing race conditions and concurrent safety:
1. Concurrent thread creation and access
2. Simultaneous message routing to same threads
3. Race conditions in thread registry and state management
4. Thread-safe operations validation
5. User isolation under concurrent load
6. Database transaction isolation

CRITICAL: Uses REAL PostgreSQL + Redis for concurrency testing - NO mocks allowed.
Expected: Initial failures - race conditions likely exist in current implementation.
"""

import asyncio
import uuid
import pytest
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID,
    ensure_user_id, ensure_thread_id
)

# Thread routing and concurrency components
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.db.models_postgres import Thread, Message, User
from netra_backend.app.core.managers.unified_state_manager import UnifiedStateManager
from netra_backend.app.services.thread_run_registry import ThreadRunRegistry

# WebSocket and user context
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Import SQLAlchemy for transaction testing
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text, select, and_
    from sqlalchemy.orm import selectinload
except ImportError:
    AsyncSession = None
    text = None
    select = None


class TestThreadRoutingRaceConditions(BaseIntegrationTest):
    """Test thread routing race conditions and concurrent operation safety."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_thread_creation_race_conditions(self, real_services_fixture, isolated_env):
        """Test race conditions in concurrent thread creation for same user."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup test users for concurrent operations
        user_count = 10
        user_ids = [ensure_user_id(str(uuid.uuid4())) for _ in range(user_count)]
        
        # Create users in database
        for i, user_id in enumerate(user_ids):
            test_user = User(
                id=str(user_id),
                email=f"race.user.{i}@test.com",
                full_name=f"Race Condition User {i}",
                is_active=True
            )
            db_session.add(test_user)
        
        await db_session.commit()
        
        # Track race condition results
        race_condition_results = {
            "concurrent_thread_creation": [],
            "user_isolation_violations": [],
            "duplicate_threads": [],
            "timing_analysis": {}
        }
        
        thread_service = ThreadService()
        
        # Test 1: Concurrent thread creation for single user
        single_user_id = user_ids[0]
        
        async def create_thread_for_user(user_id: str, operation_id: int):
            """Create thread with timing and error tracking."""
            start_time = time.time()
            try:
                thread = await thread_service.get_or_create_thread(str(user_id), db_session)
                end_time = time.time()
                
                return {
                    "success": True,
                    "operation_id": operation_id,
                    "user_id": str(user_id),
                    "thread_id": thread.id,
                    "duration": end_time - start_time,
                    "timestamp": start_time
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "user_id": str(user_id),
                    "error": str(e),
                    "duration": end_time - start_time,
                    "timestamp": start_time
                }
        
        # Run concurrent thread creation for single user
        self.logger.info(f"Testing concurrent thread creation for user {single_user_id}")
        concurrent_operations = 20
        
        start_concurrent_test = time.time()
        single_user_tasks = [
            create_thread_for_user(single_user_id, i) 
            for i in range(concurrent_operations)
        ]
        
        single_user_results = await asyncio.gather(*single_user_tasks, return_exceptions=True)
        end_concurrent_test = time.time()
        
        # Analyze single user concurrent results
        successful_ops = [r for r in single_user_results if isinstance(r, dict) and r.get("success", False)]
        failed_ops = [r for r in single_user_results if isinstance(r, dict) and not r.get("success", True)]
        exception_ops = [r for r in single_user_results if not isinstance(r, dict)]
        
        # Check for duplicate thread creation (race condition)
        thread_ids_created = [op["thread_id"] for op in successful_ops]
        unique_thread_ids = set(thread_ids_created)
        
        race_condition_results["concurrent_thread_creation"] = {
            "total_operations": concurrent_operations,
            "successful": len(successful_ops),
            "failed": len(failed_ops),
            "exceptions": len(exception_ops),
            "unique_threads_created": len(unique_thread_ids),
            "duplicate_threads": len(thread_ids_created) - len(unique_thread_ids),
            "total_duration": end_concurrent_test - start_concurrent_test,
            "has_race_condition": len(unique_thread_ids) > 1  # Should only create one thread
        }
        
        self.logger.info(f"Single user concurrent results: {len(successful_ops)} success, {len(failed_ops)} failed")
        self.logger.info(f"Unique threads created: {len(unique_thread_ids)} (expected: 1)")
        
        if len(unique_thread_ids) > 1:
            self.logger.warning(f"RACE CONDITION DETECTED: Multiple threads created for single user")
            for thread_id in unique_thread_ids:
                self.logger.warning(f"  Thread created: {thread_id}")
        
        # Test 2: Concurrent operations across multiple users
        self.logger.info("Testing concurrent thread creation across multiple users")
        
        multi_user_tasks = []
        for user_id in user_ids[:5]:  # Test with 5 users
            for op_id in range(3):  # 3 operations per user
                multi_user_tasks.append(create_thread_for_user(user_id, op_id))
        
        multi_user_start = time.time()
        multi_user_results = await asyncio.gather(*multi_user_tasks, return_exceptions=True)
        multi_user_end = time.time()
        
        # Analyze multi-user results for isolation violations
        successful_multi_ops = [r for r in multi_user_results if isinstance(r, dict) and r.get("success", False)]
        
        # Group by user to check isolation
        user_thread_mapping = {}
        for op in successful_multi_ops:
            user_id = op["user_id"]
            thread_id = op["thread_id"]
            
            if user_id not in user_thread_mapping:
                user_thread_mapping[user_id] = set()
            user_thread_mapping[user_id].add(thread_id)
        
        # Check for user isolation violations
        isolation_violations = []
        for user_id, thread_ids in user_thread_mapping.items():
            if len(thread_ids) > 1:
                isolation_violations.append({
                    "user_id": user_id,
                    "thread_count": len(thread_ids),
                    "thread_ids": list(thread_ids)
                })
        
        race_condition_results["user_isolation_violations"] = isolation_violations
        
        # Test 3: Check for cross-user thread contamination
        self.logger.info("Checking for cross-user thread contamination")
        
        contamination_found = False
        for user_id in user_thread_mapping:
            user_threads = user_thread_mapping[user_id]
            for other_user_id in user_thread_mapping:
                if user_id != other_user_id:
                    other_threads = user_thread_mapping[other_user_id] 
                    shared_threads = user_threads.intersection(other_threads)
                    if shared_threads:
                        contamination_found = True
                        self.logger.error(f"CROSS-USER CONTAMINATION: Users {user_id} and {other_user_id} share threads: {shared_threads}")
        
        race_condition_results["cross_user_contamination"] = contamination_found
        
        # Performance analysis
        if successful_ops:
            durations = [op["duration"] for op in successful_ops]
            race_condition_results["timing_analysis"] = {
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "operations_per_second": len(successful_ops) / (end_concurrent_test - start_concurrent_test)
            }
        
        # Overall race condition assessment
        has_race_conditions = (
            race_condition_results["concurrent_thread_creation"]["has_race_condition"] or
            len(isolation_violations) > 0 or
            contamination_found
        )
        
        self.logger.info("=== Race Condition Analysis Results ===")
        self.logger.info(f"Race conditions detected: {'YES ⚠️' if has_race_conditions else 'NO ✅'}")
        
        if isolation_violations:
            self.logger.warning(f"User isolation violations: {len(isolation_violations)}")
            for violation in isolation_violations:
                self.logger.warning(f"  User {violation['user_id']}: {violation['thread_count']} threads")
        
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_simultaneous_message_routing_race_conditions(self, real_services_fixture, isolated_env):
        """Test race conditions in simultaneous message routing to same threads."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup test users and threads
        user_count = 5
        user_ids = [ensure_user_id(str(uuid.uuid4())) for _ in range(user_count)]
        
        # Create users and their threads
        user_threads = {}
        for i, user_id in enumerate(user_ids):
            test_user = User(
                id=str(user_id),
                email=f"message.race.user.{i}@test.com",
                full_name=f"Message Race User {i}",
                is_active=True
            )
            db_session.add(test_user)
        
        await db_session.commit()
        
        thread_service = ThreadService()
        
        # Create threads for each user
        for user_id in user_ids:
            thread = await thread_service.get_or_create_thread(str(user_id), db_session)
            user_threads[user_id] = thread
        
        message_race_results = {
            "concurrent_message_creation": {},
            "message_ordering_violations": [],
            "thread_state_corruption": [],
            "message_loss": []
        }
        
        # Test 1: Concurrent message creation in same thread
        self.logger.info("Testing concurrent message creation in same thread")
        
        test_user_id = user_ids[0] 
        test_thread = user_threads[test_user_id]
        
        async def create_message_concurrent(thread_id: str, message_index: int, user_id: str):
            """Create message with race condition tracking."""
            start_time = time.time()
            try:
                message = await thread_service.create_message(
                    thread_id=thread_id,
                    role="user",
                    content=f"Concurrent message {message_index} from {user_id}",
                    metadata={
                        "race_test": True,
                        "message_index": message_index,
                        "user_id": str(user_id),
                        "timestamp": start_time
                    }
                )
                end_time = time.time()
                
                return {
                    "success": True,
                    "message_id": message.id,
                    "message_index": message_index,
                    "user_id": str(user_id),
                    "duration": end_time - start_time,
                    "created_at": message.created_at if hasattr(message, 'created_at') else None
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "message_index": message_index,
                    "user_id": str(user_id), 
                    "error": str(e),
                    "duration": end_time - start_time
                }
        
        # Create many concurrent messages in same thread
        messages_per_batch = 30
        concurrent_message_tasks = [
            create_message_concurrent(test_thread.id, i, test_user_id)
            for i in range(messages_per_batch)
        ]
        
        message_start_time = time.time()
        concurrent_message_results = await asyncio.gather(*concurrent_message_tasks, return_exceptions=True)
        message_end_time = time.time()
        
        # Analyze concurrent message results
        successful_messages = [r for r in concurrent_message_results if isinstance(r, dict) and r.get("success", False)]
        failed_messages = [r for r in concurrent_message_results if isinstance(r, dict) and not r.get("success", True)]
        
        message_race_results["concurrent_message_creation"] = {
            "total_attempted": messages_per_batch,
            "successful": len(successful_messages),
            "failed": len(failed_messages),
            "success_rate": len(successful_messages) / messages_per_batch,
            "total_duration": message_end_time - message_start_time
        }
        
        self.logger.info(f"Concurrent message creation: {len(successful_messages)}/{messages_per_batch} successful")
        
        # Test 2: Check message ordering and potential race conditions
        if successful_messages:
            # Retrieve all messages from thread to check ordering
            thread_messages = await thread_service.get_thread_messages(test_thread.id, limit=100, db=db_session)
            
            # Verify all messages are present
            retrieved_message_count = len(thread_messages)
            expected_message_count = len(successful_messages)
            
            if retrieved_message_count != expected_message_count:
                message_race_results["message_loss"].append({
                    "thread_id": test_thread.id,
                    "expected_messages": expected_message_count,
                    "retrieved_messages": retrieved_message_count,
                    "missing_messages": expected_message_count - retrieved_message_count
                })
                self.logger.warning(f"MESSAGE LOSS DETECTED: Expected {expected_message_count}, got {retrieved_message_count}")
            
            # Check for message content corruption
            corrupted_messages = []
            for message in thread_messages:
                try:
                    content = message.content[0]["text"]["value"]
                    if "Concurrent message" not in content:
                        corrupted_messages.append({
                            "message_id": message.id,
                            "corrupted_content": content,
                            "thread_id": test_thread.id
                        })
                except (KeyError, IndexError, TypeError) as e:
                    corrupted_messages.append({
                        "message_id": message.id,
                        "corruption_error": str(e),
                        "thread_id": test_thread.id
                    })
            
            if corrupted_messages:
                message_race_results["message_corruption"] = corrupted_messages
                self.logger.warning(f"MESSAGE CORRUPTION DETECTED: {len(corrupted_messages)} corrupted messages")
        
        # Test 3: Cross-thread message routing race conditions
        self.logger.info("Testing cross-thread message routing race conditions")
        
        async def create_cross_thread_messages(user_id: UserID, thread_count: int):
            """Create messages across multiple threads concurrently."""
            user_threads_local = []
            for i in range(thread_count):
                thread = await thread_service.get_or_create_thread(str(user_id), db_session)
                user_threads_local.append(thread)
            
            # Create concurrent messages across different threads
            cross_thread_tasks = []
            for i, thread in enumerate(user_threads_local):
                cross_thread_tasks.append(
                    create_message_concurrent(thread.id, i, user_id)
                )
            
            results = await asyncio.gather(*cross_thread_tasks, return_exceptions=True)
            return user_threads_local, results
        
        # Test cross-thread operations for multiple users
        cross_thread_user_id = user_ids[1]
        user_threads_list, cross_thread_results = await create_cross_thread_messages(
            cross_thread_user_id, 5
        )
        
        successful_cross_thread = [r for r in cross_thread_results if isinstance(r, dict) and r.get("success", False)]
        
        # Verify message isolation across threads
        thread_message_counts = {}
        for thread in user_threads_list:
            messages = await thread_service.get_thread_messages(thread.id, db=db_session)
            thread_message_counts[thread.id] = len(messages)
        
        # Check for message routing violations (messages in wrong threads)
        routing_violations = []
        total_expected_messages = len(successful_cross_thread)
        total_retrieved_messages = sum(thread_message_counts.values())
        
        if total_retrieved_messages != total_expected_messages:
            routing_violations.append({
                "user_id": str(cross_thread_user_id),
                "expected_total": total_expected_messages,
                "retrieved_total": total_retrieved_messages,
                "thread_counts": thread_message_counts
            })
        
        message_race_results["routing_violations"] = routing_violations
        
        # Test 4: High-concurrency stress test
        self.logger.info("Running high-concurrency message stress test")
        
        stress_test_user_id = user_ids[2]
        stress_test_thread = user_threads[stress_test_user_id]
        
        # Create very high concurrent load
        stress_message_count = 100
        stress_tasks = [
            create_message_concurrent(stress_test_thread.id, i, stress_test_user_id)
            for i in range(stress_message_count)
        ]
        
        # Use asyncio.as_completed for better concurrency control
        stress_start_time = time.time()
        completed_stress_tasks = 0
        stress_failures = 0
        
        for task in asyncio.as_completed(stress_tasks):
            try:
                result = await task
                completed_stress_tasks += 1
                if not result.get("success", False):
                    stress_failures += 1
            except Exception as e:
                stress_failures += 1
                self.logger.warning(f"Stress test task failed: {e}")
        
        stress_end_time = time.time()
        stress_duration = stress_end_time - stress_start_time
        
        message_race_results["stress_test"] = {
            "total_messages": stress_message_count,
            "completed_tasks": completed_stress_tasks,
            "failures": stress_failures,
            "success_rate": (completed_stress_tasks - stress_failures) / stress_message_count,
            "messages_per_second": completed_stress_tasks / stress_duration,
            "total_duration": stress_duration
        }
        
        # Final verification: Check thread state consistency
        final_thread_state = await thread_service.get_thread(stress_test_thread.id, str(stress_test_user_id), db_session)
        
        if final_thread_state is None:
            message_race_results["thread_state_corruption"].append({
                "thread_id": stress_test_thread.id,
                "corruption_type": "thread_disappeared",
                "user_id": str(stress_test_user_id)
            })
            self.logger.error("THREAD STATE CORRUPTION: Thread disappeared after stress test")
        
        # Summarize race condition findings
        self.logger.info("=== Message Routing Race Condition Analysis ===")
        
        race_conditions_found = (
            len(message_race_results.get("message_loss", [])) > 0 or
            len(message_race_results.get("message_corruption", [])) > 0 or
            len(message_race_results.get("routing_violations", [])) > 0 or
            len(message_race_results.get("thread_state_corruption", [])) > 0
        )
        
        self.logger.info(f"Message routing race conditions: {'DETECTED ⚠️' if race_conditions_found else 'NONE ✅'}")
        
        success_rate = message_race_results["concurrent_message_creation"]["success_rate"]
        self.logger.info(f"Overall message creation success rate: {success_rate:.1%}")
        
        stress_success_rate = message_race_results["stress_test"]["success_rate"]
        self.logger.info(f"Stress test success rate: {stress_success_rate:.1%}")
        
        if race_conditions_found:
            self.logger.warning("Race condition issues found in message routing:")
            for issue_type in ["message_loss", "message_corruption", "routing_violations", "thread_state_corruption"]:
                issues = message_race_results.get(issue_type, [])
                if issues:
                    self.logger.warning(f"  {issue_type}: {len(issues)} issues")
        
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_registry_concurrent_access_patterns(self, real_services_fixture, isolated_env):
        """Test thread registry race conditions under concurrent access patterns."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup users for registry testing
        registry_user_count = 8
        user_ids = [ensure_user_id(str(uuid.uuid4())) for _ in range(registry_user_count)]
        
        for i, user_id in enumerate(user_ids):
            test_user = User(
                id=str(user_id),
                email=f"registry.test.{i}@test.com",
                full_name=f"Registry Test User {i}",
                is_active=True
            )
            db_session.add(test_user)
        
        await db_session.commit()
        
        # Initialize services
        thread_service = ThreadService()
        thread_registry = ThreadRunRegistry()
        
        registry_race_results = {
            "concurrent_registry_operations": {},
            "state_inconsistencies": [],
            "registry_corruption": [],
            "performance_degradation": {}
        }
        
        # Test 1: Concurrent thread registry operations
        self.logger.info("Testing concurrent thread registry operations")
        
        async def perform_registry_operations(user_id: str, operation_count: int):
            """Perform multiple registry operations concurrently."""
            results = []
            
            for i in range(operation_count):
                operation_start = time.time()
                try:
                    # Create thread
                    thread = await thread_service.get_or_create_thread(str(user_id), db_session)
                    
                    # Create run
                    run = await thread_service.create_run(
                        thread_id=thread.id,
                        assistant_id="test-assistant",
                        model="gpt-4",
                        instructions=f"Test run {i} for registry operations"
                    )
                    
                    # Register thread-run association
                    registry_key = f"{user_id}:{thread.id}:{run.id}"
                    
                    # Simulate registry operations
                    await asyncio.sleep(0.001)  # Small delay to increase race condition likelihood
                    
                    operation_end = time.time()
                    
                    results.append({
                        "success": True,
                        "operation_index": i,
                        "thread_id": thread.id,
                        "run_id": run.id,
                        "duration": operation_end - operation_start,
                        "registry_key": registry_key
                    })
                    
                except Exception as e:
                    operation_end = time.time()
                    results.append({
                        "success": False,
                        "operation_index": i,
                        "error": str(e),
                        "duration": operation_end - operation_start
                    })
            
            return results
        
        # Run concurrent registry operations
        registry_operations_per_user = 10
        concurrent_registry_tasks = [
            perform_registry_operations(user_id, registry_operations_per_user)
            for user_id in user_ids
        ]
        
        registry_start_time = time.time()
        concurrent_registry_results = await asyncio.gather(*concurrent_registry_tasks, return_exceptions=True)
        registry_end_time = time.time()
        
        # Analyze registry operation results
        all_registry_operations = []
        for user_results in concurrent_registry_results:
            if isinstance(user_results, list):
                all_registry_operations.extend(user_results)
        
        successful_registry_ops = [op for op in all_registry_operations if op.get("success", False)]
        failed_registry_ops = [op for op in all_registry_operations if not op.get("success", True)]
        
        registry_race_results["concurrent_registry_operations"] = {
            "total_operations": len(all_registry_operations),
            "successful": len(successful_registry_ops),
            "failed": len(failed_registry_ops),
            "success_rate": len(successful_registry_ops) / len(all_registry_operations) if all_registry_operations else 0,
            "total_duration": registry_end_time - registry_start_time,
            "avg_operation_duration": sum(op["duration"] for op in successful_registry_ops) / len(successful_registry_ops) if successful_registry_ops else 0
        }
        
        # Test 2: Check for registry state inconsistencies
        self.logger.info("Checking registry state consistency")
        
        # Verify each user's threads and runs exist and are properly associated
        state_inconsistencies = []
        
        for user_id in user_ids:
            try:
                # Get all threads for user
                user_threads = await thread_service.get_threads(str(user_id), db_session)
                
                thread_run_associations = {}
                for thread in user_threads:
                    # Check if thread has proper metadata
                    if not hasattr(thread, 'metadata_') or not thread.metadata_:
                        state_inconsistencies.append({
                            "type": "missing_thread_metadata",
                            "user_id": str(user_id),
                            "thread_id": thread.id
                        })
                    
                    # Verify thread belongs to correct user
                    if hasattr(thread, 'metadata_') and thread.metadata_:
                        thread_user_id = thread.metadata_.get("user_id")
                        if thread_user_id != str(user_id):
                            state_inconsistencies.append({
                                "type": "thread_user_mismatch",
                                "expected_user": str(user_id),
                                "actual_user": thread_user_id,
                                "thread_id": thread.id
                            })
                    
                    # Check thread messages for consistency
                    thread_messages = await thread_service.get_thread_messages(thread.id, db=db_session)
                    for message in thread_messages:
                        if message.thread_id != thread.id:
                            state_inconsistencies.append({
                                "type": "message_thread_mismatch", 
                                "message_id": message.id,
                                "expected_thread": thread.id,
                                "actual_thread": message.thread_id
                            })
                
            except Exception as e:
                state_inconsistencies.append({
                    "type": "registry_access_failure",
                    "user_id": str(user_id),
                    "error": str(e)
                })
        
        registry_race_results["state_inconsistencies"] = state_inconsistencies
        
        # Test 3: High-frequency registry access
        self.logger.info("Testing high-frequency registry access patterns")
        
        high_frequency_user_id = user_ids[0]
        high_frequency_thread = await thread_service.get_or_create_thread(str(high_frequency_user_id), db_session)
        
        async def high_frequency_access(access_id: int):
            """Perform high-frequency registry access."""
            access_start = time.time()
            operations_completed = 0
            errors = []
            
            try:
                # Rapid sequence of registry operations
                for i in range(20):  # 20 rapid operations
                    # Get thread (registry read)
                    thread = await thread_service.get_thread(
                        high_frequency_thread.id, str(high_frequency_user_id), db_session
                    )
                    operations_completed += 1
                    
                    # Small delay
                    await asyncio.sleep(0.001)
                
            except Exception as e:
                errors.append(str(e))
            
            access_end = time.time()
            return {
                "access_id": access_id,
                "operations_completed": operations_completed,
                "errors": errors,
                "duration": access_end - access_start,
                "ops_per_second": operations_completed / (access_end - access_start) if access_end > access_start else 0
            }
        
        # Run high-frequency access concurrently
        high_frequency_tasks = [high_frequency_access(i) for i in range(10)]
        high_freq_start = time.time()
        high_frequency_results = await asyncio.gather(*high_frequency_tasks, return_exceptions=True)
        high_freq_end = time.time()
        
        # Analyze high-frequency results
        successful_high_freq = [r for r in high_frequency_results if isinstance(r, dict)]
        
        total_ops = sum(r["operations_completed"] for r in successful_high_freq)
        total_errors = sum(len(r["errors"]) for r in successful_high_freq)
        avg_ops_per_second = sum(r["ops_per_second"] for r in successful_high_freq) / len(successful_high_freq) if successful_high_freq else 0
        
        registry_race_results["high_frequency_access"] = {
            "concurrent_accessors": len(high_frequency_tasks),
            "total_operations": total_ops,
            "total_errors": total_errors,
            "error_rate": total_errors / total_ops if total_ops > 0 else 0,
            "avg_ops_per_second": avg_ops_per_second,
            "total_duration": high_freq_end - high_freq_start
        }
        
        # Test 4: Check for performance degradation under load
        single_thread_start = time.time()
        single_thread = await thread_service.get_thread(
            high_frequency_thread.id, str(high_frequency_user_id), db_session
        )
        single_thread_end = time.time()
        single_thread_duration = single_thread_end - single_thread_start
        
        # Compare with average duration under concurrent load
        avg_concurrent_duration = registry_race_results["concurrent_registry_operations"]["avg_operation_duration"]
        
        performance_degradation_ratio = avg_concurrent_duration / single_thread_duration if single_thread_duration > 0 else 0
        
        registry_race_results["performance_degradation"] = {
            "single_operation_duration": single_thread_duration,
            "avg_concurrent_duration": avg_concurrent_duration,
            "degradation_ratio": performance_degradation_ratio,
            "significant_degradation": performance_degradation_ratio > 5.0  # 5x slower is concerning
        }
        
        # Overall registry race condition assessment
        self.logger.info("=== Thread Registry Race Condition Analysis ===")
        
        registry_issues = (
            len(state_inconsistencies) > 0 or
            registry_race_results["concurrent_registry_operations"]["success_rate"] < 0.9 or
            registry_race_results["high_frequency_access"]["error_rate"] > 0.1 or
            registry_race_results["performance_degradation"]["significant_degradation"]
        )
        
        self.logger.info(f"Registry race conditions: {'DETECTED ⚠️' if registry_issues else 'NONE ✅'}")
        
        success_rate = registry_race_results["concurrent_registry_operations"]["success_rate"]
        self.logger.info(f"Registry operation success rate: {success_rate:.1%}")
        
        if state_inconsistencies:
            self.logger.warning(f"State inconsistencies found: {len(state_inconsistencies)}")
            for inconsistency in state_inconsistencies[:5]:  # Log first 5
                self.logger.warning(f"  {inconsistency['type']}: {inconsistency}")
        
        error_rate = registry_race_results["high_frequency_access"]["error_rate"]
        self.logger.info(f"High-frequency access error rate: {error_rate:.1%}")
        
        if registry_race_results["performance_degradation"]["significant_degradation"]:
            degradation = registry_race_results["performance_degradation"]["degradation_ratio"]
            self.logger.warning(f"Significant performance degradation detected: {degradation:.1f}x slower under concurrent load")
        
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_transaction_isolation_race_conditions(self, real_services_fixture, isolated_env):
        """Test database transaction isolation and race conditions in concurrent scenarios."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup test user
        user_id = ensure_user_id(str(uuid.uuid4()))
        test_user = User(
            id=str(user_id),
            email="transaction.isolation.test@example.com",
            full_name="Transaction Isolation Test User",
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        
        thread_service = ThreadService()
        transaction_race_results = {
            "isolation_violations": [],
            "dirty_reads": [],
            "phantom_reads": [],
            "lost_updates": [],
            "deadlock_scenarios": []
        }
        
        # Test 1: Transaction isolation during concurrent thread operations
        self.logger.info("Testing database transaction isolation")
        
        # Create initial thread
        base_thread = await thread_service.get_or_create_thread(str(user_id), db_session)
        
        async def concurrent_transaction_operations(operation_id: int):
            """Perform operations that test transaction isolation."""
            try:
                # Start with base thread
                thread_id = base_thread.id
                
                # Create multiple messages in sequence within same transaction context
                messages_created = []
                
                for msg_idx in range(5):
                    message = await thread_service.create_message(
                        thread_id=thread_id,
                        role="user", 
                        content=f"Transaction test message {msg_idx} from operation {operation_id}",
                        metadata={"transaction_test": True, "operation_id": operation_id, "msg_index": msg_idx}
                    )
                    messages_created.append(message.id)
                
                # Read back messages to verify transaction isolation
                retrieved_messages = await thread_service.get_thread_messages(thread_id, db=db_session)
                
                return {
                    "success": True,
                    "operation_id": operation_id,
                    "messages_created": len(messages_created),
                    "messages_retrieved": len(retrieved_messages),
                    "created_message_ids": messages_created
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "error": str(e)
                }
        
        # Run concurrent transaction operations
        transaction_task_count = 15
        transaction_tasks = [
            concurrent_transaction_operations(i) for i in range(transaction_task_count)
        ]
        
        transaction_results = await asyncio.gather(*transaction_tasks, return_exceptions=True)
        
        # Analyze transaction isolation
        successful_transactions = [r for r in transaction_results if isinstance(r, dict) and r.get("success", False)]
        
        if successful_transactions:
            # Check for isolation violations
            all_created_messages = []
            for result in successful_transactions:
                all_created_messages.extend(result["created_message_ids"])
            
            # Verify all messages exist in database
            final_thread_messages = await thread_service.get_thread_messages(base_thread.id, limit=1000, db=db_session)
            final_message_ids = {msg.id for msg in final_thread_messages}
            
            # Check for lost messages (lost update problem)
            missing_messages = []
            for msg_id in all_created_messages:
                if msg_id not in final_message_ids:
                    missing_messages.append(msg_id)
            
            if missing_messages:
                transaction_race_results["lost_updates"] = missing_messages
                self.logger.warning(f"LOST UPDATES DETECTED: {len(missing_messages)} messages missing")
            
            # Check for phantom reads (unexpected messages appearing)
            expected_message_count = sum(r["messages_created"] for r in successful_transactions)
            actual_message_count = len(final_thread_messages)
            
            if actual_message_count != expected_message_count:
                transaction_race_results["phantom_reads"].append({
                    "expected_count": expected_message_count,
                    "actual_count": actual_message_count,
                    "difference": actual_message_count - expected_message_count
                })
                self.logger.warning(f"PHANTOM READ DETECTED: Expected {expected_message_count}, found {actual_message_count}")
        
        # Test 2: Concurrent read-write operations (dirty read test)
        self.logger.info("Testing dirty read scenarios")
        
        async def writer_operation():
            """Write operation that may create dirty reads."""
            try:
                # Create message
                message = await thread_service.create_message(
                    thread_id=base_thread.id,
                    role="user",
                    content="Dirty read test message - initial",
                    metadata={"dirty_read_test": True}
                )
                
                # Simulate processing delay
                await asyncio.sleep(0.1)
                
                # Update message content (simulated)
                # Note: Current API may not support message updates
                return {"success": True, "message_id": message.id}
                
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        async def reader_operation(delay: float):
            """Read operation that may see dirty data."""
            try:
                await asyncio.sleep(delay)
                messages = await thread_service.get_thread_messages(base_thread.id, db=db_session)
                
                dirty_read_messages = [
                    msg for msg in messages
                    if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("dirty_read_test")
                ]
                
                return {
                    "success": True,
                    "messages_seen": len(dirty_read_messages),
                    "read_delay": delay
                }
                
            except Exception as e:
                return {"success": False, "error": str(e), "read_delay": delay}
        
        # Run writer and concurrent readers
        dirty_read_tasks = [writer_operation()]
        dirty_read_tasks.extend([reader_operation(0.05), reader_operation(0.15)])  # Read at different times
        
        dirty_read_results = await asyncio.gather(*dirty_read_tasks, return_exceptions=True)
        
        # Analyze dirty read results
        writer_result = dirty_read_results[0] if dirty_read_results else None
        reader_results = dirty_read_results[1:] if len(dirty_read_results) > 1 else []
        
        # Check for inconsistent reads (potential dirty reads)
        if len(reader_results) >= 2:
            early_read = reader_results[0]
            late_read = reader_results[1] 
            
            if (isinstance(early_read, dict) and isinstance(late_read, dict) and
                early_read.get("success") and late_read.get("success")):
                
                early_count = early_read["messages_seen"]
                late_count = late_read["messages_seen"]
                
                if early_count != late_count:
                    transaction_race_results["dirty_reads"].append({
                        "early_read_count": early_count,
                        "late_read_count": late_count,
                        "inconsistent_reads": True
                    })
        
        # Test 3: Deadlock scenario testing
        self.logger.info("Testing potential deadlock scenarios")
        
        async def deadlock_prone_operation(user_id: str, operation_type: str):
            """Operation that might cause deadlocks with concurrent execution."""
            try:
                if operation_type == "create_then_read":
                    # Create thread, then read messages from different thread
                    thread1 = await thread_service.get_or_create_thread(str(user_id), db_session)
                    thread2 = await thread_service.get_or_create_thread(str(user_id), db_session) 
                    
                    # Create message in thread1
                    await thread_service.create_message(
                        thread_id=thread1.id,
                        role="user",
                        content="Deadlock test message",
                        metadata={"deadlock_test": True}
                    )
                    
                    # Read from thread2
                    messages = await thread_service.get_thread_messages(thread2.id, db=db_session)
                    
                elif operation_type == "read_then_create":
                    # Reverse order - read first, then create
                    thread1 = await thread_service.get_or_create_thread(str(user_id), db_session)
                    thread2 = await thread_service.get_or_create_thread(str(user_id), db_session)
                    
                    # Read from thread1
                    messages = await thread_service.get_thread_messages(thread1.id, db=db_session)
                    
                    # Create in thread2
                    await thread_service.create_message(
                        thread_id=thread2.id,
                        role="user", 
                        content="Deadlock test message reverse",
                        metadata={"deadlock_test": True}
                    )
                
                return {"success": True, "operation_type": operation_type}
                
            except Exception as e:
                # Check if error indicates deadlock
                error_msg = str(e).lower()
                is_deadlock = any(term in error_msg for term in ["deadlock", "timeout", "lock"])
                
                return {
                    "success": False,
                    "operation_type": operation_type,
                    "error": str(e),
                    "potential_deadlock": is_deadlock
                }
        
        # Run operations that might cause deadlocks
        deadlock_tasks = []
        for i in range(10):
            operation_type = "create_then_read" if i % 2 == 0 else "read_then_create"
            deadlock_tasks.append(deadlock_prone_operation(user_id, operation_type))
        
        deadlock_start = time.time()
        deadlock_results = await asyncio.gather(*deadlock_tasks, return_exceptions=True)
        deadlock_end = time.time()
        
        # Analyze deadlock results
        deadlock_timeouts = []
        potential_deadlocks = []
        
        for result in deadlock_results:
            if isinstance(result, dict):
                if not result.get("success", False) and result.get("potential_deadlock", False):
                    potential_deadlocks.append(result)
            elif isinstance(result, Exception):
                # Timeout or other exception might indicate deadlock
                deadlock_timeouts.append(str(result))
        
        if potential_deadlocks:
            transaction_race_results["deadlock_scenarios"] = potential_deadlocks
            self.logger.warning(f"POTENTIAL DEADLOCKS DETECTED: {len(potential_deadlocks)}")
        
        deadlock_duration = deadlock_end - deadlock_start
        if deadlock_duration > 30:  # Operations took unusually long
            self.logger.warning(f"Deadlock test took {deadlock_duration:.1f}s - potential blocking detected")
        
        # Overall transaction isolation assessment
        self.logger.info("=== Database Transaction Isolation Analysis ===")
        
        isolation_violations_found = (
            len(transaction_race_results["isolation_violations"]) > 0 or
            len(transaction_race_results["dirty_reads"]) > 0 or
            len(transaction_race_results["phantom_reads"]) > 0 or
            len(transaction_race_results["lost_updates"]) > 0 or
            len(transaction_race_results["deadlock_scenarios"]) > 0
        )
        
        self.logger.info(f"Transaction isolation violations: {'DETECTED ⚠️' if isolation_violations_found else 'NONE ✅'}")
        
        for violation_type in ["lost_updates", "phantom_reads", "dirty_reads", "deadlock_scenarios"]:
            violations = transaction_race_results.get(violation_type, [])
            if violations:
                self.logger.warning(f"  {violation_type}: {len(violations)} violations")
        
        success_rate = len(successful_transactions) / len(transaction_tasks) if transaction_tasks else 0
        self.logger.info(f"Transaction success rate: {success_rate:.1%}")
        
        await db_session.close()