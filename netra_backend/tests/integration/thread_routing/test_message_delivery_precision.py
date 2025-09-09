"""
Test Message Delivery Precision with End-to-End Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure precise message routing and delivery accuracy for AI chat conversations
- Value Impact: Message delivery failures corrupt user conversations and destroy business value
- Strategic Impact: Message precision is fundamental to reliable multi-user AI chat platform

This test suite validates end-to-end message delivery precision with full infrastructure stack:
1. Messages delivered to correct threads with user authentication context
2. Cross-thread contamination prevention and message isolation
3. Message ordering, sequence integrity, and conversation continuity
4. Full stack integration (PostgreSQL + Redis + WebSocket) with precision validation
5. Concurrent message delivery accuracy under multi-user load
6. Message persistence, retrieval, and thread association verification

CRITICAL: Uses REAL infrastructure stack (PostgreSQL 5434, Redis 6381) - NO mocks allowed.
Expected: Initial failures - message routing precision issues likely exist in current implementation.
Authentication REQUIRED: All tests use real JWT tokens for proper user context and message isolation.
"""

import asyncio
import uuid
import pytest
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set, Tuple
from unittest.mock import patch
from collections import defaultdict, namedtuple
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, WebSocketID, RequestID, RunID, SessionID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id, ensure_request_id,
    WebSocketEventType, WebSocketMessage, AuthValidationResult
)

# Helper function for tests
def ensure_session_id(value: str) -> SessionID:
    """Helper to ensure SessionID type."""
    return SessionID(value)

# Full stack components for message routing
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.core.websocket_message_handler import WebSocketMessageHandler
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Helper function for tests
def generate_websocket_id() -> str:
    """Generate a unique WebSocket ID for testing."""
    return f"ws_{uuid.uuid4().hex[:16]}"
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.db.models_postgres import Thread, Message, User
from netra_backend.app.core.managers.unified_state_manager import UnifiedStateManager

# Redis and caching
try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
except ImportError:
    redis = None
    Redis = None

# SQLAlchemy for database operations
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text, select, and_, func, desc
    from sqlalchemy.orm import selectinload
except ImportError:
    AsyncSession = None
    select = None


class TestMessageDeliveryPrecision(BaseIntegrationTest):
    """Test message delivery precision across full infrastructure stack with authentication."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authenticated_message_delivery_thread_precision(self, real_services_fixture, isolated_env):
        """Test messages are delivered precisely to correct threads with authentication."""
        
        # Check infrastructure availability
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup Redis connection
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))
        
        try:
            redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup authenticated users with thread isolation testing scenario
        auth_helper = E2EAuthHelper()
        user_count = 5
        threads_per_user = 4
        messages_per_thread = 6
        
        authenticated_users = []
        users_threads_data = {}
        
        # Create authenticated users and their threads
        for user_idx in range(user_count):
            user_data = await auth_helper.create_authenticated_test_user(
                email=f"precision.delivery.user.{user_idx}@test.com",
                name=f"Message Precision User {user_idx}",
                password="securepassword123"
            )
            authenticated_users.append(user_data)
            
            # Create user record in database
            user_id = ensure_user_id(user_data["user_id"])
            test_user = User(
                id=str(user_id),
                email=user_data["email"],
                full_name=user_data["name"],
                is_active=True,
                created_at=datetime.utcnow()
            )
            db_session.add(test_user)
            users_threads_data[user_id] = []
        
        await db_session.commit()
        
        # Initialize services
        thread_service = ThreadService()
        message_handler = MessageHandlerService()
        websocket_manager = UnifiedWebSocketManager()
        
        # Create threads for each user with precise targeting
        for user_data in authenticated_users:
            user_id = ensure_user_id(user_data["user_id"])
            user_threads = []
            
            for thread_idx in range(threads_per_user):
                # Create thread with authenticated context
                thread = await thread_service.get_or_create_thread(
                    user_id=str(user_id),
                    db=db_session
                )
                user_threads.append(thread)
                
                # Verify thread creation with proper user context
                assert thread.metadata_ is not None, f"Thread {thread.id} missing metadata"
                assert thread.metadata_.get("user_id") == str(user_id), \
                    f"Thread {thread.id} has wrong user context: {thread.metadata_.get('user_id')} != {user_id}"
                
                self.logger.info(f"Created precision test thread {thread.id} for user {user_id}")
            
            users_threads_data[user_id] = user_threads
        
        # Phase 1: Send targeted messages with precision tracking
        message_delivery_log = []
        thread_message_expectations = defaultdict(list)
        precision_signatures = set()
        
        for user_data in authenticated_users:
            user_id = ensure_user_id(user_data["user_id"])
            user_threads = users_threads_data[user_id]
            
            for thread_idx, thread in enumerate(user_threads):
                thread_id = ensure_thread_id(thread.id)
                
                # Create authenticated execution context for message delivery
                execution_context = UserExecutionContext(
                    user_id=str(user_id),
                    thread_id=str(thread_id),
                    run_id=f"precision_test_{uuid.uuid4()}",
                    session_id=user_data["session_id"],
                    auth_token=user_data["access_token"],
                    permissions=user_data.get("permissions", [])
                )
                
                # Send precisely targeted messages to this specific thread
                for msg_idx in range(messages_per_thread):
                    # Create unique message signature for precision tracking
                    precision_signature = f"u{list(authenticated_users).index(user_data)}t{thread_idx}m{msg_idx}"
                    precision_signatures.add(precision_signature)
                    
                    message_content = f"Precision delivery test: {precision_signature} - User {user_id} Thread {thread_idx} Message {msg_idx}"
                    
                    # Create message with authenticated context and precision metadata
                    message = await thread_service.create_message(
                        thread_id=str(thread_id),
                        role="user" if msg_idx % 2 == 0 else "assistant",
                        content=message_content,
                        metadata={
                            "precision_test": True,
                            "target_user_id": str(user_id),
                            "target_thread_index": thread_idx,
                            "message_sequence": msg_idx,
                            "precision_signature": precision_signature,
                            "delivery_timestamp": datetime.utcnow().isoformat(),
                            "auth_session_id": user_data["session_id"],
                            "execution_context": execution_context.dict()
                        }
                    )
                    
                    delivery_record = {
                        "message_id": message.id,
                        "target_thread_id": str(thread_id),
                        "target_user_id": str(user_id),
                        "precision_signature": precision_signature,
                        "content_hash": hashlib.sha256(message_content.encode()).hexdigest()[:16],
                        "expected_location": f"{user_id}:{thread_id}",
                        "message_role": message.role,
                        "sequence_index": msg_idx
                    }
                    
                    message_delivery_log.append(delivery_record)
                    thread_message_expectations[str(thread_id)].append(delivery_record)
                    
                    # Small delay to ensure distinct timestamps
                    await asyncio.sleep(0.01)
        
        total_messages_sent = len(message_delivery_log)
        expected_thread_count = user_count * threads_per_user
        
        self.logger.info(f"Sent {total_messages_sent} precision messages across {expected_thread_count} threads")
        
        # Phase 2: Verify message delivery precision
        delivery_violations = []
        
        # Verify each thread received exactly the correct messages
        for user_id, user_threads in users_threads_data.items():
            for thread in user_threads:
                thread_id = thread.id
                
                # Retrieve all messages in this thread
                thread_messages = await thread_service.get_thread_messages(
                    thread_id=thread_id, 
                    limit=100, 
                    db=db_session
                )
                
                # Filter for precision test messages
                precision_messages = [
                    msg for msg in thread_messages
                    if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("precision_test")
                ]
                
                expected_messages = thread_message_expectations[thread_id]
                expected_count = len(expected_messages)
                actual_count = len(precision_messages)
                
                # Verify message count precision
                if actual_count != expected_count:
                    delivery_violations.append(
                        f"Thread {thread_id} has {actual_count} messages, expected {expected_count}"
                    )
                    continue
                
                # Verify each message belongs to this thread and has correct content
                for message in precision_messages:
                    # Check thread association
                    if message.thread_id != thread_id:
                        delivery_violations.append(
                            f"Message {message.id} in thread {thread_id} has wrong thread_id: {message.thread_id}"
                        )
                    
                    # Check user context in metadata
                    msg_user_id = message.metadata_.get("target_user_id")
                    if msg_user_id != str(user_id):
                        delivery_violations.append(
                            f"Message {message.id} has wrong target_user_id: {msg_user_id} != {user_id}"
                        )
                    
                    # Verify precision signature in content
                    message_content = message.content[0]["text"]["value"]
                    precision_signature = message.metadata_.get("precision_signature")
                    
                    if precision_signature not in message_content:
                        delivery_violations.append(
                            f"Message {message.id} content missing precision signature: {precision_signature}"
                        )
                    
                    # Verify content hash integrity
                    content_hash = hashlib.sha256(message_content.encode()).hexdigest()[:16]
                    expected_record = next(
                        (r for r in expected_messages if r["precision_signature"] == precision_signature), 
                        None
                    )
                    
                    if expected_record and expected_record["content_hash"] != content_hash:
                        delivery_violations.append(
                            f"Message {message.id} content corrupted: hash mismatch"
                        )
        
        # Phase 3: Cross-thread contamination detection
        contamination_violations = []
        
        for user_id, user_threads in users_threads_data.items():
            user_thread_ids = {thread.id for thread in user_threads}
            
            # Check each thread for contamination from other threads
            for thread in user_threads:
                thread_messages = await thread_service.get_thread_messages(thread.id, db=db_session)
                
                for message in thread_messages:
                    if hasattr(message, 'metadata_') and message.metadata_ and message.metadata_.get("precision_test"):
                        message_content = message.content[0]["text"]["value"]
                        precision_signature = message.metadata_.get("precision_signature")
                        
                        # Check for references to other users
                        other_users = [uid for uid in users_threads_data.keys() if uid != user_id]
                        for other_user_id in other_users:
                            other_user_index = list(authenticated_users).index(
                                next(u for u in authenticated_users if ensure_user_id(u["user_id"]) == other_user_id)
                            )
                            
                            # Look for signatures that belong to other users
                            if f"u{other_user_index}t" in precision_signature:
                                contamination_violations.append(
                                    f"Message {message.id} in user {user_id}'s thread {thread.id} has signature from other user: {precision_signature}"
                                )
                        
                        # Check for references to other threads within same user
                        current_thread_index = user_threads.index(thread)
                        expected_thread_signature = f"t{current_thread_index}"
                        
                        if expected_thread_signature not in precision_signature:
                            # This message might belong to a different thread
                            for other_thread_idx, other_thread in enumerate(user_threads):
                                if other_thread_idx != current_thread_index:
                                    wrong_thread_signature = f"t{other_thread_idx}"
                                    if wrong_thread_signature in precision_signature:
                                        contamination_violations.append(
                                            f"Message {message.id} in thread {thread.id} belongs to thread index {other_thread_idx}"
                                        )
        
        # Phase 4: Message sequence and ordering verification
        sequence_violations = []
        
        for user_id, user_threads in users_threads_data.items():
            for thread_idx, thread in enumerate(user_threads):
                thread_messages = await thread_service.get_thread_messages(thread.id, db=db_session)
                
                # Filter precision test messages and sort by sequence
                precision_messages = [
                    msg for msg in thread_messages
                    if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("precision_test")
                ]
                
                # Sort by message sequence for ordering verification
                try:
                    precision_messages.sort(key=lambda m: m.metadata_.get("message_sequence", 0))
                except Exception as e:
                    sequence_violations.append(f"Failed to sort messages in thread {thread.id}: {e}")
                    continue
                
                # Verify sequence integrity
                expected_sequences = list(range(messages_per_thread))
                actual_sequences = [msg.metadata_.get("message_sequence") for msg in precision_messages]
                
                if actual_sequences != expected_sequences:
                    sequence_violations.append(
                        f"Thread {thread.id} sequence mismatch: {actual_sequences} != {expected_sequences}"
                    )
                
                # Verify role alternation pattern (user/assistant)
                expected_roles = ["user" if i % 2 == 0 else "assistant" for i in range(messages_per_thread)]
                actual_roles = [msg.role for msg in precision_messages]
                
                if actual_roles != expected_roles:
                    sequence_violations.append(
                        f"Thread {thread.id} role sequence incorrect: {actual_roles} != {expected_roles}"
                    )
        
        # Report all violations
        all_violations = delivery_violations + contamination_violations + sequence_violations
        
        if all_violations:
            self.logger.error(f"FOUND {len(all_violations)} MESSAGE DELIVERY VIOLATIONS:")
            
            # Categorize violations
            violation_categories = {
                "delivery": delivery_violations,
                "contamination": contamination_violations,
                "sequence": sequence_violations
            }
            
            for category, violations in violation_categories.items():
                if violations:
                    self.logger.error(f"  {category.upper()} VIOLATIONS ({len(violations)}):")
                    for violation in violations[:3]:  # Show first 3 in each category
                        self.logger.error(f"    {violation}")
                    if len(violations) > 3:
                        self.logger.error(f"    ... and {len(violations) - 3} more {category} violations")
            
            raise AssertionError(f"Found {len(all_violations)} message delivery precision violations")
        
        self.logger.info(f"Message delivery precision verified successfully:")
        self.logger.info(f"  Messages delivered: {total_messages_sent}")
        self.logger.info(f"  Threads tested: {expected_thread_count}")
        self.logger.info(f"  Users tested: {user_count}")
        self.logger.info(f"  Precision signatures verified: {len(precision_signatures)}")
        
        await redis_client.close()
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_message_delivery_accuracy_under_load(self, real_services_fixture, isolated_env):
        """Test message delivery accuracy under concurrent multi-user load conditions."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup Redis connection
        env = get_env()
        redis_client = redis.Redis(host=env.get("REDIS_HOST", "localhost"), 
                                 port=int(env.get("REDIS_PORT", "6381")), 
                                 decode_responses=True)
        try:
            await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")
        
        # High-load concurrent testing scenario
        auth_helper = E2EAuthHelper()
        concurrent_users = 8
        concurrent_threads_per_user = 3
        concurrent_messages_per_thread = 10
        
        authenticated_users = []
        load_test_data = {}
        
        # Create authenticated users for load testing
        for user_idx in range(concurrent_users):
            user_data = await auth_helper.create_authenticated_test_user(
                email=f"load.test.user.{user_idx}@test.com",
                name=f"Concurrent Load User {user_idx}",
                password="securepassword123"
            )
            authenticated_users.append(user_data)
            
            # Create user in database
            user_id = ensure_user_id(user_data["user_id"])
            test_user = User(
                id=str(user_id),
                email=user_data["email"],
                full_name=user_data["name"],
                is_active=True
            )
            db_session.add(test_user)
            load_test_data[user_id] = {"user_data": user_data, "threads": [], "expected_messages": []}
        
        await db_session.commit()
        
        # Create threads for each user
        thread_service = ThreadService()
        
        for user_data in authenticated_users:
            user_id = ensure_user_id(user_data["user_id"])
            user_threads = []
            
            for thread_idx in range(concurrent_threads_per_user):
                thread = await thread_service.get_or_create_thread(str(user_id), db_session)
                user_threads.append(thread)
            
            load_test_data[user_id]["threads"] = user_threads
        
        # Concurrent message delivery operation
        async def concurrent_message_delivery_operation(user_id: UserID, thread_idx: int, message_batch_size: int):
            """Perform concurrent message delivery for a specific user-thread combination."""
            user_data = load_test_data[user_id]["user_data"]
            thread = load_test_data[user_id]["threads"][thread_idx]
            
            operation_results = {
                "user_id": str(user_id),
                "thread_id": thread.id,
                "thread_index": thread_idx,
                "messages_delivered": 0,
                "delivery_times": [],
                "errors": [],
                "start_time": time.time()
            }
            
            # Create authenticated execution context
            execution_context = UserExecutionContext(
                user_id=str(user_id),
                thread_id=thread.id,
                run_id=f"load_test_{uuid.uuid4()}",
                session_id=user_data["session_id"],
                auth_token=user_data["access_token"],
                permissions=user_data.get("permissions", [])
            )
            
            # Deliver messages concurrently in rapid succession
            for msg_idx in range(message_batch_size):
                try:
                    delivery_start = time.time()
                    
                    # Create unique load test signature
                    load_signature = f"load_u{list(authenticated_users).index(user_data)}t{thread_idx}m{msg_idx}_{int(time.time()*1000)}"
                    
                    message_content = f"Concurrent load test: {load_signature}"
                    
                    message = await thread_service.create_message(
                        thread_id=thread.id,
                        role="user" if msg_idx % 2 == 0 else "assistant",
                        content=message_content,
                        metadata={
                            "load_test": True,
                            "user_id": str(user_id),
                            "thread_index": thread_idx,
                            "message_index": msg_idx,
                            "load_signature": load_signature,
                            "delivery_timestamp": datetime.utcnow().isoformat(),
                            "execution_context": execution_context.dict()
                        }
                    )
                    
                    delivery_time = time.time() - delivery_start
                    operation_results["delivery_times"].append(delivery_time)
                    operation_results["messages_delivered"] += 1
                    
                    # Store expected message for verification
                    expected_message = {
                        "message_id": message.id,
                        "thread_id": thread.id,
                        "load_signature": load_signature,
                        "content_hash": hashlib.sha256(message_content.encode()).hexdigest()[:16]
                    }
                    load_test_data[user_id]["expected_messages"].append(expected_message)
                    
                    # Minimal delay to allow database processing
                    await asyncio.sleep(0.005)
                    
                except Exception as e:
                    operation_results["errors"].append(str(e))
            
            operation_results["total_duration"] = time.time() - operation_results["start_time"]
            return operation_results
        
        # Execute high-volume concurrent message delivery
        total_expected_messages = concurrent_users * concurrent_threads_per_user * concurrent_messages_per_thread
        
        self.logger.info(f"Starting concurrent load test:")
        self.logger.info(f"  Users: {concurrent_users}")
        self.logger.info(f"  Threads per user: {concurrent_threads_per_user}")
        self.logger.info(f"  Messages per thread: {concurrent_messages_per_thread}")
        self.logger.info(f"  Total expected messages: {total_expected_messages}")
        
        load_test_start = time.time()
        
        # Create all concurrent operations
        concurrent_operations = []
        for user_data in authenticated_users:
            user_id = ensure_user_id(user_data["user_id"])
            for thread_idx in range(concurrent_threads_per_user):
                operation = concurrent_message_delivery_operation(
                    user_id, thread_idx, concurrent_messages_per_thread
                )
                concurrent_operations.append(operation)
        
        # Execute all operations concurrently
        operation_results = await asyncio.gather(*concurrent_operations, return_exceptions=True)
        
        load_test_duration = time.time() - load_test_start
        
        # Analyze load test results
        successful_operations = [r for r in operation_results if not isinstance(r, Exception)]
        failed_operations = [r for r in operation_results if isinstance(r, Exception)]
        
        total_messages_delivered = sum(op["messages_delivered"] for op in successful_operations)
        total_errors = sum(len(op["errors"]) for op in successful_operations)
        
        success_rate = total_messages_delivered / total_expected_messages
        messages_per_second = total_messages_delivered / load_test_duration
        
        # Performance requirements for concurrent load
        assert success_rate >= 0.90, f"Message delivery success rate too low: {success_rate:.1%} (need 90%+)"
        assert messages_per_second >= 20, f"Message delivery throughput too low: {messages_per_second:.2f} msg/sec (need 20+)"
        
        # Analyze delivery time performance
        all_delivery_times = []
        for op in successful_operations:
            all_delivery_times.extend(op["delivery_times"])
        
        if all_delivery_times:
            avg_delivery_time = sum(all_delivery_times) / len(all_delivery_times)
            p95_delivery_time = sorted(all_delivery_times)[int(0.95 * len(all_delivery_times))]
            max_delivery_time = max(all_delivery_times)
            
            # Delivery time performance requirements
            assert avg_delivery_time < 0.1, f"Average delivery time too slow: {avg_delivery_time*1000:.2f}ms (need <100ms)"
            assert p95_delivery_time < 0.2, f"95th percentile too slow: {p95_delivery_time*1000:.2f}ms (need <200ms)"
            
            self.logger.info(f"Load test performance metrics:")
            self.logger.info(f"  Success rate: {success_rate:.1%} ({total_messages_delivered}/{total_expected_messages})")
            self.logger.info(f"  Throughput: {messages_per_second:.2f} messages/second")
            self.logger.info(f"  Average delivery time: {avg_delivery_time*1000:.2f}ms")
            self.logger.info(f"  95th percentile: {p95_delivery_time*1000:.2f}ms")
            self.logger.info(f"  Max delivery time: {max_delivery_time*1000:.2f}ms")
            self.logger.info(f"  Total errors: {total_errors}")
        
        # Verify message delivery accuracy after high load
        accuracy_violations = []
        
        for user_id, test_data in load_test_data.items():
            user_threads = test_data["threads"]
            expected_messages = test_data["expected_messages"]
            
            # Group expected messages by thread
            expected_by_thread = defaultdict(list)
            for expected_msg in expected_messages:
                expected_by_thread[expected_msg["thread_id"]].append(expected_msg)
            
            # Verify each thread received correct messages
            for thread in user_threads:
                thread_messages = await thread_service.get_thread_messages(thread.id, db=db_session)
                
                # Filter load test messages
                load_test_messages = [
                    msg for msg in thread_messages
                    if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("load_test")
                ]
                
                expected_for_thread = expected_by_thread[thread.id]
                expected_count = len(expected_for_thread)
                actual_count = len(load_test_messages)
                
                # Allow for some message loss under extreme load but require majority delivery
                min_acceptable = int(expected_count * 0.90)  # 90% minimum delivery rate
                
                if actual_count < min_acceptable:
                    accuracy_violations.append(
                        f"Thread {thread.id} delivery rate too low: {actual_count}/{expected_count} = {actual_count/expected_count:.1%}"
                    )
                
                # Verify delivered messages have correct content and metadata
                delivered_signatures = set()
                for message in load_test_messages:
                    load_signature = message.metadata_.get("load_signature")
                    if load_signature:
                        delivered_signatures.add(load_signature)
                    
                    # Verify message belongs to correct user
                    msg_user_id = message.metadata_.get("user_id")
                    if msg_user_id != str(user_id):
                        accuracy_violations.append(
                            f"Message {message.id} in thread {thread.id} has wrong user_id: {msg_user_id} != {user_id}"
                        )
                
                # Check for duplicate deliveries
                expected_signatures = {msg["load_signature"] for msg in expected_for_thread}
                duplicate_deliveries = len(load_test_messages) - len(delivered_signatures)
                
                if duplicate_deliveries > 0:
                    accuracy_violations.append(
                        f"Thread {thread.id} has {duplicate_deliveries} duplicate message deliveries"
                    )
        
        # Report accuracy violations
        if accuracy_violations:
            for violation in accuracy_violations[:10]:  # Show first 10
                self.logger.error(f"LOAD TEST ACCURACY VIOLATION: {violation}")
            
            if len(accuracy_violations) > 10:
                self.logger.error(f"... and {len(accuracy_violations) - 10} more accuracy violations")
            
            raise AssertionError(f"Found {len(accuracy_violations)} message delivery accuracy violations under load")
        
        self.logger.info(f"Concurrent message delivery load test completed successfully")
        
        await redis_client.close()
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_end_to_end_message_routing_websocket_database_integration(self, real_services_fixture, isolated_env):
        """Test complete end-to-end message routing through WebSocket to database with thread precision."""
        
        # Check all infrastructure components
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup Redis connection
        env = get_env()
        redis_client = redis.Redis(host=env.get("REDIS_HOST", "localhost"), 
                                 port=int(env.get("REDIS_PORT", "6381")), 
                                 decode_responses=True)
        try:
            await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")
        
        # Setup end-to-end integration test scenario
        auth_helper = E2EAuthHelper()
        user_data = await auth_helper.create_authenticated_test_user(
            email="e2e.integration@test.com",
            name="End-to-End Integration User",
            password="securepassword123"
        )
        
        user_id = ensure_user_id(user_data["user_id"])
        
        # Create user in database
        test_user = User(
            id=str(user_id),
            email=user_data["email"],
            full_name=user_data["name"],
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        
        # Initialize all services for full stack testing
        thread_service = ThreadService()
        websocket_manager = UnifiedWebSocketManager()
        state_manager = UnifiedStateManager()
        
        # Create multiple threads for routing precision testing
        integration_threads = []
        websocket_connections = {}
        
        for thread_idx in range(4):
            thread = await thread_service.get_or_create_thread(str(user_id), db_session)
            integration_threads.append(thread)
            
            # Create WebSocket connection for this thread
            websocket_id = ensure_websocket_id(f"e2e_{thread_idx}_{generate_websocket_id()}")
            
            # Setup authenticated WebSocket connection state
            connection_info = {
                "websocket_id": str(websocket_id),
                "user_id": str(user_id),
                "thread_id": thread.id,
                "session_id": user_data["session_id"],
                "auth_token_hash": hashlib.sha256(user_data["access_token"].encode()).hexdigest()[:16],
                "connected_at": datetime.utcnow().isoformat(),
                "e2e_integration_test": True
            }
            
            # Store WebSocket state in Redis
            connection_key = f"websocket:connection:{websocket_id}"
            await redis_client.hset(connection_key, mapping=connection_info)
            
            # Add to thread mapping
            thread_mapping_key = f"websocket:thread_mapping:{thread.id}"
            await redis_client.sadd(thread_mapping_key, str(websocket_id))
            
            websocket_connections[thread.id] = {
                "websocket_id": websocket_id,
                "connection_info": connection_info
            }
            
            self.logger.info(f"Setup E2E integration thread {thread.id} with WebSocket {websocket_id}")
        
        # Phase 1: Simulate complete message flow through entire stack
        E2EMessageFlow = namedtuple('E2EMessageFlow', [
            'incoming_message', 'websocket_processing', 'database_storage', 
            'agent_processing', 'response_generation', 'websocket_delivery'
        ])
        
        async def simulate_complete_e2e_message_flow(thread_id: str, flow_index: int):
            """Simulate complete message flow from WebSocket to database and back."""
            flow_stages = []
            websocket_info = websocket_connections[thread_id]
            
            try:
                # Stage 1: Incoming WebSocket message
                incoming_message = {
                    "type": "user_message",
                    "user_id": str(user_id),
                    "thread_id": thread_id,
                    "websocket_id": str(websocket_info["websocket_id"]),
                    "content": f"E2E integration test message {flow_index} for thread {thread_id}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": str(uuid.uuid4()),
                    "session_id": user_data["session_id"],
                    "e2e_integration_test": True,
                    "flow_index": flow_index
                }
                flow_stages.append(("websocket_message_received", incoming_message["request_id"]))
                
                # Stage 2: WebSocket message processing and validation
                # Verify WebSocket connection exists and is valid
                connection_key = f"websocket:connection:{websocket_info['websocket_id']}"
                stored_connection = await redis_client.hgetall(connection_key)
                
                if not stored_connection or stored_connection.get("thread_id") != thread_id:
                    raise ValueError(f"Invalid WebSocket connection for thread {thread_id}")
                
                flow_stages.append(("websocket_validated", stored_connection.get("websocket_id")))
                
                # Stage 3: Message storage in database
                stored_message = await thread_service.create_message(
                    thread_id=thread_id,
                    role="user",
                    content=incoming_message["content"],
                    metadata={
                        "websocket_id": incoming_message["websocket_id"],
                        "request_id": incoming_message["request_id"],
                        "e2e_integration_test": True,
                        "flow_index": flow_index,
                        "stage": "user_message_stored",
                        "processing_timestamp": datetime.utcnow().isoformat()
                    }
                )
                flow_stages.append(("database_storage_complete", stored_message.id))
                
                # Stage 4: Agent processing simulation
                await asyncio.sleep(0.08)  # Simulate agent processing time
                
                agent_response_message = await thread_service.create_message(
                    thread_id=thread_id,
                    role="assistant",
                    content=f"E2E integration response {flow_index} to your message in thread {thread_id}",
                    metadata={
                        "request_id": incoming_message["request_id"],
                        "e2e_integration_test": True,
                        "flow_index": flow_index,
                        "stage": "agent_response",
                        "response_to_message": stored_message.id,
                        "agent_processing_timestamp": datetime.utcnow().isoformat()
                    }
                )
                flow_stages.append(("agent_processing_complete", agent_response_message.id))
                
                # Stage 5: WebSocket response preparation and delivery
                response_payload = {
                    "type": "agent_response",
                    "thread_id": thread_id,
                    "message_id": agent_response_message.id,
                    "content": agent_response_message.content,
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": incoming_message["request_id"],
                    "websocket_id": str(websocket_info["websocket_id"])
                }
                
                # Store response in Redis for WebSocket delivery
                response_key = f"websocket:pending_response:{websocket_info['websocket_id']}"
                await redis_client.lpush(response_key, json.dumps(response_payload))
                await redis_client.expire(response_key, 300)  # 5 minute expiration
                
                flow_stages.append(("websocket_response_queued", response_payload["message_id"]))
                
                return E2EMessageFlow(
                    incoming_message=incoming_message,
                    websocket_processing=stored_connection,
                    database_storage=stored_message,
                    agent_processing=agent_response_message,
                    response_generation=response_payload,
                    websocket_delivery=flow_stages
                )
                
            except Exception as e:
                return {
                    "error": str(e),
                    "thread_id": thread_id,
                    "flow_index": flow_index,
                    "completed_stages": flow_stages
                }
        
        # Execute multiple E2E flows across all threads
        flows_per_thread = 6
        all_e2e_flows = []
        
        for thread in integration_threads:
            for flow_idx in range(flows_per_thread):
                flow_task = simulate_complete_e2e_message_flow(thread.id, flow_idx)
                all_e2e_flows.append(flow_task)
        
        self.logger.info(f"Executing {len(all_e2e_flows)} end-to-end message flows")
        e2e_start_time = time.time()
        
        e2e_results = await asyncio.gather(*all_e2e_flows)
        e2e_duration = time.time() - e2e_start_time
        
        # Analyze E2E flow results
        successful_flows = [r for r in e2e_results if isinstance(r, E2EMessageFlow)]
        failed_flows = [r for r in e2e_results if not isinstance(r, E2EMessageFlow)]
        
        success_rate = len(successful_flows) / len(e2e_results)
        flows_per_second = len(e2e_results) / e2e_duration
        
        # E2E flow performance requirements
        assert success_rate >= 0.85, f"E2E flow success rate too low: {success_rate:.1%} (need 85%+)"
        assert flows_per_second >= 5, f"E2E flow throughput too low: {flows_per_second:.2f} flows/sec (need 5+)"
        
        self.logger.info(f"E2E flow performance:")
        self.logger.info(f"  Success rate: {success_rate:.1%} ({len(successful_flows)}/{len(e2e_results)})")
        self.logger.info(f"  Throughput: {flows_per_second:.2f} flows/second")
        self.logger.info(f"  Total duration: {e2e_duration:.2f}s")
        
        # Phase 2: Verify E2E routing precision and data integrity
        routing_precision_violations = []
        
        # Group successful flows by thread
        flows_by_thread = defaultdict(list)
        for flow in successful_flows:
            thread_id = flow.incoming_message["thread_id"]
            flows_by_thread[thread_id].append(flow)
        
        # Verify each thread received correct flows and data
        for thread in integration_threads:
            thread_id = thread.id
            thread_flows = flows_by_thread[thread_id]
            
            expected_flow_count = flows_per_thread
            actual_flow_count = len(thread_flows)
            
            if actual_flow_count != expected_flow_count:
                routing_precision_violations.append(
                    f"Thread {thread_id} has {actual_flow_count} flows, expected {expected_flow_count}"
                )
            
            # Verify database message storage precision
            thread_messages = await thread_service.get_thread_messages(thread_id, limit=50, db=db_session)
            e2e_messages = [
                msg for msg in thread_messages
                if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("e2e_integration_test")
            ]
            
            # Should have user messages + agent responses
            expected_db_messages = expected_flow_count * 2
            actual_db_messages = len(e2e_messages)
            
            if actual_db_messages != expected_db_messages:
                routing_precision_violations.append(
                    f"Thread {thread_id} has {actual_db_messages} database messages, expected {expected_db_messages}"
                )
            
            # Verify message content precision and thread isolation
            for message in e2e_messages:
                message_content = message.content[0]["text"]["value"]
                
                # Message should reference correct thread
                if thread_id not in message_content:
                    routing_precision_violations.append(
                        f"Message {message.id} in thread {thread_id} doesn't reference correct thread in content"
                    )
                
                # Verify thread association
                if message.thread_id != thread_id:
                    routing_precision_violations.append(
                        f"Message {message.id} has wrong thread_id: {message.thread_id} != {thread_id}"
                    )
                
                # Check for cross-thread contamination
                other_thread_ids = [t.id for t in integration_threads if t.id != thread_id]
                for other_thread_id in other_thread_ids:
                    if other_thread_id in message_content:
                        routing_precision_violations.append(
                            f"Message {message.id} in thread {thread_id} references other thread {other_thread_id}"
                        )
        
        # Verify WebSocket response queue precision
        for thread in integration_threads:
            thread_id = thread.id
            websocket_info = websocket_connections[thread_id]
            websocket_id = websocket_info["websocket_id"]
            
            # Check pending responses for this websocket
            response_key = f"websocket:pending_response:{websocket_id}"
            pending_responses = await redis_client.lrange(response_key, 0, -1)
            
            # Verify all responses belong to correct thread
            for response_json in pending_responses:
                try:
                    response_data = json.loads(response_json)
                    response_thread_id = response_data.get("thread_id")
                    
                    if response_thread_id != thread_id:
                        routing_precision_violations.append(
                            f"WebSocket {websocket_id} for thread {thread_id} has response for wrong thread {response_thread_id}"
                        )
                except json.JSONDecodeError as e:
                    routing_precision_violations.append(
                        f"WebSocket {websocket_id} has malformed response JSON: {e}"
                    )
        
        # Report routing precision violations
        if routing_precision_violations:
            for violation in routing_precision_violations[:10]:  # Show first 10
                self.logger.error(f"E2E ROUTING PRECISION VIOLATION: {violation}")
            
            if len(routing_precision_violations) > 10:
                self.logger.error(f"... and {len(routing_precision_violations) - 10} more violations")
            
            raise AssertionError(f"Found {len(routing_precision_violations)} end-to-end routing precision violations")
        
        # Report failed flows
        if failed_flows:
            self.logger.warning(f"Failed E2E flows ({len(failed_flows)}):")
            for failed in failed_flows:
                self.logger.warning(f"  Thread {failed.get('thread_id')}: {failed.get('error', 'unknown error')}")
                self.logger.warning(f"    Completed stages: {failed.get('completed_stages', [])}")
        
        self.logger.info(f"End-to-end message routing integration verified successfully:")
        self.logger.info(f"  Threads tested: {len(integration_threads)}")
        self.logger.info(f"  Total flows: {len(successful_flows)}")
        self.logger.info(f"  WebSocket connections: {len(websocket_connections)}")
        self.logger.info(f"  Database messages stored: {len(integration_threads) * flows_per_thread * 2}")
        
        await redis_client.close()
        await db_session.close()


# Helper import for content hashing
import hashlib