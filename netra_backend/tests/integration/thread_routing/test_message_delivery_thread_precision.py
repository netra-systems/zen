"""
Test Message Delivery Thread Precision Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure precise message routing to correct threads for accurate chat conversations
- Value Impact: Message routing failures corrupt user conversations and destroy business value
- Strategic Impact: Core message delivery precision is fundamental to AI chat platform reliability

This test suite validates message delivery thread precision with full infrastructure stack:
1. Messages delivered to correct thread only
2. Cross-thread contamination prevention
3. Thread message ordering and sequence integrity
4. Full stack integration (PostgreSQL + Redis + WebSocket)

CRITICAL: Uses REAL infrastructure stack - NO mocks allowed for integration testing.
Expected: Initial failures - message routing precision issues likely exist in current implementation.
"""

import asyncio
import uuid
import pytest
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set, Tuple
from unittest.mock import patch
from collections import defaultdict

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.lightweight_services import lightweight_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, WebSocketID, RequestID, RunID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id,
    WebSocketEventType, WebSocketMessage
)

# Full stack components for message routing
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.utils import generate_connection_id
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.db.models_postgres import Thread, Message, User

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
    from sqlalchemy import text, select, and_
except ImportError:
    AsyncSession = None
    select = None


class TestMessageDeliveryThreadPrecision(BaseIntegrationTest):
    """Test message delivery precision across full infrastructure stack."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_precise_message_delivery_to_correct_threads(self, lightweight_services_fixture, isolated_env):
        """Test messages are delivered only to the correct target thread."""
        
        # Check infrastructure availability
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Database not available")
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup Redis connection
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))
        
        try:
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup test scenario: multiple users with multiple threads
        user_count = 3
        threads_per_user = 4
        messages_per_thread = 5
        
        # Create users and threads
        users_threads_data = {}
        thread_service = ThreadService()
        
        for user_idx in range(user_count):
            user_id = ensure_user_id(str(uuid.uuid4()))
            
            # Create user in database
            test_user = User(
                id=str(user_id),
                email=f"precision.user.{user_idx}@test.com",
                full_name=f"Precision Test User {user_idx}",
                is_active=True
            )
            db_session.add(test_user)
            
            # Create threads for user
            user_threads = []
            for thread_idx in range(threads_per_user):
                thread = await thread_service.get_or_create_thread(str(user_id), db_session)
                user_threads.append(thread)
                self.logger.info(f"Created thread {thread.id} for user {user_id}")
            
            users_threads_data[user_id] = user_threads
        
        await db_session.commit()
        
        # Send targeted messages to specific threads
        message_delivery_log = []
        expected_thread_messages = defaultdict(list)
        
        for user_id, user_threads in users_threads_data.items():
            for thread_idx, thread in enumerate(user_threads):
                thread_id = ensure_thread_id(thread.id)
                
                # Send unique messages to this specific thread
                for msg_idx in range(messages_per_thread):
                    message_content = f"Precision test message {msg_idx} for user {user_id} thread {thread_idx}"
                    
                    # Create message with specific thread targeting
                    message = await thread_service.create_message(
                        thread_id=thread.id,
                        role="user",
                        content=message_content,
                        metadata={
                            "precision_test": True,
                            "target_user": str(user_id),
                            "target_thread_index": thread_idx,
                            "message_sequence": msg_idx,
                            "delivery_timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    
                    delivery_record = {
                        "message_id": message.id,
                        "target_thread": thread.id,
                        "target_user": str(user_id),
                        "content_signature": f"user{user_id}_thread{thread_idx}_msg{msg_idx}",
                        "expected_location": f"{user_id}:{thread.id}"
                    }
                    
                    message_delivery_log.append(delivery_record)
                    expected_thread_messages[thread.id].append(delivery_record)
        
        self.logger.info(f"Sent {len(message_delivery_log)} targeted messages across {sum(len(threads) for threads in users_threads_data.values())} threads")
        
        # Verify message precision delivery
        precision_violations = []
        
        for user_id, user_threads in users_threads_data.items():
            for thread in user_threads:
                thread_id = thread.id
                
                # Retrieve all messages in this thread
                thread_messages = await thread_service.get_thread_messages(thread_id, limit=100, db=db_session)
                
                # Filter messages from our precision test
                precision_messages = [
                    msg for msg in thread_messages 
                    if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("precision_test")
                ]
                
                expected_count = messages_per_thread
                actual_count = len(precision_messages)
                
                if actual_count != expected_count:
                    precision_violations.append(
                        f"Thread {thread_id} has {actual_count} messages, expected {expected_count}"
                    )
                
                # Verify each message belongs to this thread
                for message in precision_messages:
                    if message.thread_id != thread_id:
                        precision_violations.append(
                            f"Message {message.id} in thread {thread_id} has wrong thread_id: {message.thread_id}"
                        )
                    
                    # Verify message content targets this specific thread
                    message_content = message.content[0]["text"]["value"]
                    expected_user_signature = f"user {user_id}"
                    expected_thread_signature = f"thread {user_threads.index(thread)}"
                    
                    if expected_user_signature not in message_content:
                        precision_violations.append(
                            f"Message {message.id} content doesn't match target user {user_id}: {message_content}"
                        )
                    
                    if expected_thread_signature not in message_content:
                        precision_violations.append(
                            f"Message {message.id} content doesn't match target thread index: {message_content}"
                        )
        
        # Check for cross-thread contamination
        for user_id, user_threads in users_threads_data.items():
            user_thread_ids = {thread.id for thread in user_threads}
            
            for thread in user_threads:
                thread_messages = await thread_service.get_thread_messages(thread.id, db=db_session)
                
                for message in thread_messages:
                    if hasattr(message, 'metadata_') and message.metadata_ and message.metadata_.get("precision_test"):
                        # Check if message references other threads or users
                        message_content = message.content[0]["text"]["value"]
                        
                        # Check for references to other users
                        other_users = [uid for uid in users_threads_data.keys() if uid != user_id]
                        for other_user in other_users:
                            if f"user {other_user}" in message_content:
                                precision_violations.append(
                                    f"Message {message.id} in thread {thread.id} references wrong user {other_user}"
                                )
                        
                        # Check for references to other threads within same user
                        current_thread_idx = user_threads.index(thread)
                        for other_thread_idx, other_thread in enumerate(user_threads):
                            if other_thread_idx != current_thread_idx:
                                if f"thread {other_thread_idx}" in message_content:
                                    precision_violations.append(
                                        f"Message {message.id} in thread {thread.id} references wrong thread index {other_thread_idx}"
                                    )
        
        # Report precision violations
        if precision_violations:
            for violation in precision_violations[:10]:  # Show first 10 violations
                self.logger.error(f"PRECISION VIOLATION: {violation}")
            
            if len(precision_violations) > 10:
                self.logger.error(f"... and {len(precision_violations) - 10} more violations")
            
            raise AssertionError(f"Found {len(precision_violations)} message delivery precision violations")
        
        self.logger.info(f"Message delivery precision verified: {len(message_delivery_log)} messages delivered correctly")
        await redis_client.close()
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_message_ordering_and_sequence_integrity(self, lightweight_services_fixture, isolated_env):
        """Test message ordering and sequence integrity within threads."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Database not available")
        
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup test user and thread
        user_id = ensure_user_id(str(uuid.uuid4()))
        test_user = User(
            id=str(user_id),
            email="ordering.test@example.com",
            full_name="Message Ordering Test User",
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        
        thread_service = ThreadService()
        thread = await thread_service.get_or_create_thread(str(user_id), db_session)
        thread_id = ensure_thread_id(thread.id)
        
        # Test case 1: Sequential message creation with timing
        sequential_message_count = 20
        sequential_messages = []
        message_creation_times = []
        
        self.logger.info(f"Creating {sequential_message_count} sequential messages")
        
        for i in range(sequential_message_count):
            creation_start = time.time()
            
            message = await thread_service.create_message(
                thread_id=thread.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Sequential message {i:03d} - order verification",
                metadata={
                    "sequence_number": i,
                    "ordering_test": True,
                    "creation_timestamp": creation_start,
                    "role_pattern": "user" if i % 2 == 0 else "assistant"
                }
            )
            
            creation_duration = time.time() - creation_start
            sequential_messages.append(message)
            message_creation_times.append(creation_duration)
            
            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)
        
        # Retrieve messages and verify ordering
        retrieved_messages = await thread_service.get_thread_messages(thread.id, limit=50, db=db_session)
        
        # Filter ordering test messages
        ordering_messages = [
            msg for msg in retrieved_messages
            if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("ordering_test")
        ]
        
        assert len(ordering_messages) == sequential_message_count, \
            f"Expected {sequential_message_count} ordering messages, got {len(ordering_messages)}"
        
        # Verify chronological ordering (messages should be ordered by creation time)
        ordering_violations = []
        
        for i in range(len(ordering_messages) - 1):
            current_msg = ordering_messages[i]
            next_msg = ordering_messages[i + 1]
            
            current_seq = current_msg.metadata_.get("sequence_number")
            next_seq = next_msg.metadata_.get("sequence_number")
            
            # Check if sequence numbers are in correct order
            # Note: Messages might be returned in reverse chronological order
            if current_seq is not None and next_seq is not None:
                if abs(current_seq - next_seq) != 1:
                    # Allow for reverse order (newest first) or forward order (oldest first)
                    if not (current_seq == next_seq + 1 or current_seq == next_seq - 1):
                        ordering_violations.append(
                            f"Message sequence jump: position {i} has sequence {current_seq}, "
                            f"position {i+1} has sequence {next_seq}"
                        )
        
        # Test case 2: Concurrent message creation
        concurrent_batch_size = 10
        concurrent_batches = 3
        
        async def create_concurrent_messages(batch_id: int, batch_size: int):
            """Create a batch of messages concurrently."""
            batch_messages = []
            
            async def create_single_message(msg_index: int):
                message = await thread_service.create_message(
                    thread_id=thread.id,
                    role="user",
                    content=f"Concurrent batch {batch_id} message {msg_index}",
                    metadata={
                        "batch_id": batch_id,
                        "batch_message_index": msg_index,
                        "concurrent_test": True,
                        "creation_time": time.time()
                    }
                )
                return message
            
            # Create messages concurrently within batch
            batch_results = await asyncio.gather(*[
                create_single_message(i) for i in range(batch_size)
            ])
            
            return batch_results
        
        # Create concurrent batches
        self.logger.info(f"Creating {concurrent_batches} concurrent batches of {concurrent_batch_size} messages each")
        
        all_concurrent_results = []
        for batch_id in range(concurrent_batches):
            batch_results = await create_concurrent_messages(batch_id, concurrent_batch_size)
            all_concurrent_results.extend(batch_results)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        # Verify concurrent message integrity
        final_messages = await thread_service.get_thread_messages(thread.id, limit=100, db=db_session)
        
        concurrent_messages = [
            msg for msg in final_messages
            if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("concurrent_test")
        ]
        
        expected_concurrent_count = concurrent_batches * concurrent_batch_size
        assert len(concurrent_messages) == expected_concurrent_count, \
            f"Expected {expected_concurrent_count} concurrent messages, got {len(concurrent_messages)}"
        
        # Verify batch integrity
        batch_integrity_violations = []
        for batch_id in range(concurrent_batches):
            batch_messages = [
                msg for msg in concurrent_messages
                if msg.metadata_.get("batch_id") == batch_id
            ]
            
            if len(batch_messages) != concurrent_batch_size:
                batch_integrity_violations.append(
                    f"Batch {batch_id} has {len(batch_messages)} messages, expected {concurrent_batch_size}"
                )
            
            # Verify all messages in batch have correct batch_id
            for msg in batch_messages:
                if msg.metadata_.get("batch_id") != batch_id:
                    batch_integrity_violations.append(
                        f"Message {msg.id} in batch {batch_id} has wrong batch_id: {msg.metadata_.get('batch_id')}"
                    )
        
        # Test case 3: Message sequence integrity across mixed operations
        mixed_operations_count = 15
        
        async def mixed_message_operations():
            """Perform mixed message operations to test sequence integrity."""
            operations_log = []
            
            for i in range(mixed_operations_count):
                operation_type = i % 3
                
                if operation_type == 0:
                    # Create user message
                    message = await thread_service.create_message(
                        thread_id=thread.id,
                        role="user",
                        content=f"Mixed operation user message {i}",
                        metadata={"mixed_test": True, "operation_type": "user_message", "operation_index": i}
                    )
                    operations_log.append(f"user_message_{i}:{message.id}")
                
                elif operation_type == 1:
                    # Create assistant message
                    message = await thread_service.create_message(
                        thread_id=thread.id,
                        role="assistant",
                        content=f"Mixed operation assistant response {i}",
                        metadata={"mixed_test": True, "operation_type": "assistant_message", "operation_index": i}
                    )
                    operations_log.append(f"assistant_message_{i}:{message.id}")
                
                else:
                    # Create system message  
                    message = await thread_service.create_message(
                        thread_id=thread.id,
                        role="system",
                        content=f"Mixed operation system message {i}",
                        metadata={"mixed_test": True, "operation_type": "system_message", "operation_index": i}
                    )
                    operations_log.append(f"system_message_{i}:{message.id}")
                
                # Small delay between operations
                await asyncio.sleep(0.005)
            
            return operations_log
        
        mixed_operations_log = await mixed_message_operations()
        
        # Verify mixed operations integrity
        mixed_messages = await thread_service.get_thread_messages(thread.id, limit=200, db=db_session)
        mixed_test_messages = [
            msg for msg in mixed_messages
            if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("mixed_test")
        ]
        
        assert len(mixed_test_messages) == mixed_operations_count, \
            f"Expected {mixed_operations_count} mixed test messages, got {len(mixed_test_messages)}"
        
        # Verify operation type distribution
        operation_type_counts = defaultdict(int)
        for msg in mixed_test_messages:
            operation_type = msg.metadata_.get("operation_type")
            if operation_type:
                operation_type_counts[operation_type] += 1
        
        # Should have roughly equal distribution of operation types
        expected_per_type = mixed_operations_count // 3
        for operation_type, count in operation_type_counts.items():
            assert abs(count - expected_per_type) <= 1, \
                f"Operation type {operation_type} has {count} messages, expected ~{expected_per_type}"
        
        # Report any violations
        all_violations = ordering_violations + batch_integrity_violations
        if all_violations:
            for violation in all_violations[:5]:  # Show first 5 violations
                self.logger.error(f"ORDERING VIOLATION: {violation}")
            raise AssertionError(f"Found {len(all_violations)} message ordering violations")
        
        self.logger.info(f"Message ordering and sequence integrity verified successfully")
        avg_creation_time = sum(message_creation_times) / len(message_creation_times)
        self.logger.info(f"Average message creation time: {avg_creation_time*1000:.2f}ms")
        
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_full_stack_message_routing_websocket_integration(self, lightweight_services_fixture, isolated_env):
        """Test end-to-end message routing through WebSocket to database with thread precision."""
        
        # Check all infrastructure components
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Database not available")
        
        if not redis:
            pytest.skip("Redis not available - install redis package")
        
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup Redis connection
        env = get_env()
        redis_host = env.get("REDIS_HOST", "localhost")
        redis_port = int(env.get("REDIS_PORT", "6381"))
        
        try:
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await redis_client.ping()
        except Exception as e:
            pytest.skip(f"Redis not available at {redis_host}:{redis_port} - {e}")
        
        # Setup full stack test scenario
        user_id = ensure_user_id(str(uuid.uuid4()))
        websocket_id = ensure_websocket_id(generate_connection_id(user_id))
        
        # Create user in database
        test_user = User(
            id=str(user_id),
            email="fullstack.test@example.com",
            full_name="Full Stack Test User",
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        
        # Initialize services
        thread_service = ThreadService()
        websocket_manager = UnifiedWebSocketManager()
        
        # Create multiple threads for routing precision testing
        test_threads = []
        for i in range(3):
            thread = await thread_service.get_or_create_thread(str(user_id), db_session)
            test_threads.append(thread)
            self.logger.info(f"Created test thread {i}: {thread.id}")
        
        # Setup WebSocket connections for each thread
        websocket_thread_connections = {}
        
        for i, thread in enumerate(test_threads):
            thread_websocket_id = ensure_websocket_id(f"thread_{i}_{generate_connection_id(user_id)}")
            
            # Create user execution context for this thread
            user_context = UserExecutionContext(
                user_id=str(user_id),
                thread_id=thread.id,
                run_id=f"fullstack_test_{uuid.uuid4()}"
            )
            
            # Setup WebSocket connection state in Redis
            connection_info = {
                "websocket_id": str(thread_websocket_id),
                "user_id": str(user_id),
                "thread_id": thread.id,
                "connected_at": datetime.utcnow().isoformat(),
                "fullstack_test": True
            }
            
            connection_key = f"websocket:connection:{thread_websocket_id}"
            await redis_client.hset(connection_key, mapping=connection_info)
            
            # Add to thread mapping
            thread_mapping_key = f"websocket:thread_mapping:{thread.id}"
            await redis_client.sadd(thread_mapping_key, str(thread_websocket_id))
            
            websocket_thread_connections[thread.id] = {
                "websocket_id": thread_websocket_id,
                "user_context": user_context,
                "connection_info": connection_info
            }
        
        # Simulate full stack message flow: WebSocket -> Processing -> Database -> WebSocket Response
        full_stack_test_messages = []
        
        async def simulate_full_stack_message_flow(thread_id: str, message_index: int):
            """Simulate complete message flow through full stack."""
            flow_log = []
            websocket_info = websocket_thread_connections[thread_id]
            
            # Step 1: Incoming WebSocket message
            incoming_message = {
                "type": "user_message",
                "user_id": str(user_id),
                "thread_id": thread_id,
                "websocket_id": str(websocket_info["websocket_id"]),
                "content": f"Full stack test message {message_index} for thread {thread_id}",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4()),
                "fullstack_test": True
            }
            flow_log.append("websocket_message_received")
            
            # Step 2: Message processing and database storage
            stored_message = await thread_service.create_message(
                thread_id=thread_id,
                role="user",
                content=incoming_message["content"],
                metadata={
                    "websocket_id": incoming_message["websocket_id"],
                    "request_id": incoming_message["request_id"],
                    "fullstack_test": True,
                    "message_index": message_index,
                    "processing_timestamp": datetime.utcnow().isoformat()
                }
            )
            flow_log.append("message_stored_database")
            
            # Step 3: Simulate agent processing
            await asyncio.sleep(0.05)  # Simulate processing time
            
            agent_response_message = await thread_service.create_message(
                thread_id=thread_id,
                role="assistant",
                content=f"Full stack response {message_index} to your message in thread {thread_id}",
                metadata={
                    "request_id": incoming_message["request_id"],
                    "fullstack_test": True,
                    "response_to_message": stored_message.id,
                    "agent_processing_timestamp": datetime.utcnow().isoformat()
                }
            )
            flow_log.append("agent_response_stored")
            
            # Step 4: WebSocket response delivery simulation
            response_payload = {
                "type": "agent_response",
                "thread_id": thread_id,
                "message_id": agent_response_message.id,
                "content": agent_response_message.content,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": incoming_message["request_id"]
            }
            
            # Store response in Redis for WebSocket delivery
            response_key = f"websocket:pending_response:{websocket_info['websocket_id']}"
            await redis_client.lpush(response_key, json.dumps(response_payload))
            flow_log.append("websocket_response_queued")
            
            return {
                "incoming_message": incoming_message,
                "stored_message": stored_message,
                "agent_response": agent_response_message,
                "flow_log": flow_log,
                "thread_id": thread_id
            }
        
        # Execute full stack flows for all threads concurrently
        messages_per_thread = 5
        all_flow_tasks = []
        
        for thread in test_threads:
            for msg_index in range(messages_per_thread):
                task = simulate_full_stack_message_flow(thread.id, msg_index)
                all_flow_tasks.append(task)
        
        self.logger.info(f"Executing {len(all_flow_tasks)} full stack message flows")
        flow_results = await asyncio.gather(*all_flow_tasks)
        
        # Verify full stack routing precision
        routing_precision_violations = []
        
        # Group results by thread
        thread_flow_results = defaultdict(list)
        for result in flow_results:
            thread_flow_results[result["thread_id"]].append(result)
        
        # Verify each thread received correct messages
        for thread in test_threads:
            thread_id = thread.id
            thread_results = thread_flow_results[thread_id]
            
            # Should have exactly the expected number of flows
            expected_flows = messages_per_thread
            actual_flows = len(thread_results)
            
            if actual_flows != expected_flows:
                routing_precision_violations.append(
                    f"Thread {thread_id} has {actual_flows} flows, expected {expected_flows}"
                )
            
            # Verify database message storage precision
            thread_messages = await thread_service.get_thread_messages(thread_id, limit=50, db=db_session)
            fullstack_messages = [
                msg for msg in thread_messages
                if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("fullstack_test")
            ]
            
            # Should have user messages + agent responses
            expected_db_messages = messages_per_thread * 2  # user + agent response
            actual_db_messages = len(fullstack_messages)
            
            if actual_db_messages != expected_db_messages:
                routing_precision_violations.append(
                    f"Thread {thread_id} has {actual_db_messages} database messages, expected {expected_db_messages}"
                )
            
            # Verify message content precision
            for message in fullstack_messages:
                message_content = message.content[0]["text"]["value"]
                
                # Message should reference correct thread
                if thread_id not in message_content:
                    routing_precision_violations.append(
                        f"Message {message.id} in thread {thread_id} doesn't reference correct thread in content"
                    )
                
                # Check for cross-thread contamination
                other_thread_ids = [t.id for t in test_threads if t.id != thread_id]
                for other_thread_id in other_thread_ids:
                    if other_thread_id in message_content:
                        routing_precision_violations.append(
                            f"Message {message.id} in thread {thread_id} references other thread {other_thread_id}"
                        )
        
        # Verify WebSocket response queue precision
        for thread in test_threads:
            thread_id = thread.id
            websocket_info = websocket_thread_connections[thread_id]
            websocket_id = websocket_info["websocket_id"]
            
            # Check pending responses for this websocket
            response_key = f"websocket:pending_response:{websocket_id}"
            pending_responses = await redis_client.lrange(response_key, 0, -1)
            
            # Should have responses for this thread only
            for response_json in pending_responses:
                response_data = json.loads(response_json)
                
                if response_data["thread_id"] != thread_id:
                    routing_precision_violations.append(
                        f"WebSocket {websocket_id} for thread {thread_id} has response for wrong thread {response_data['thread_id']}"
                    )
        
        # Report any precision violations
        if routing_precision_violations:
            for violation in routing_precision_violations[:10]:  # Show first 10
                self.logger.error(f"FULL STACK ROUTING VIOLATION: {violation}")
            
            if len(routing_precision_violations) > 10:
                self.logger.error(f"... and {len(routing_precision_violations) - 10} more violations")
            
            raise AssertionError(f"Found {len(routing_precision_violations)} full stack routing precision violations")
        
        self.logger.info(f"Full stack message routing precision verified: {len(flow_results)} flows completed successfully")
        
        # Performance metrics
        successful_flows = len([r for r in flow_results if len(r["flow_log"]) == 4])
        flow_success_rate = successful_flows / len(flow_results)
        self.logger.info(f"Flow success rate: {flow_success_rate:.1%} ({successful_flows}/{len(flow_results)})")
        
        await redis_client.close()
        await db_session.close()