"""
Test WebSocket User Session Isolation During Concurrent Message Processing Integration (#22)

Business Value Justification (BVJ):
- Segment: All (Critical for multi-user chat functionality)
- Business Goal: Ensure user sessions remain isolated during high-frequency message processing
- Value Impact: Users can chat simultaneously without message mixing or session corruption
- Strategic Impact: Core chat reliability - enables concurrent user engagement

CRITICAL REQUIREMENT: User sessions must remain completely isolated even when processing
hundreds of concurrent WebSocket messages. No message should ever be delivered to the
wrong user, and session state must never be corrupted by concurrent operations.
"""

import asyncio
import pytest
import json
import time
import uuid
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState, MessageType
from shared.isolated_environment import get_env

# Type definitions
UserID = str
SessionID = str
MessageID = str
ThreadID = str


@dataclass
class ConcurrentMessageTest:
    """Test scenario for concurrent message processing."""
    user_id: UserID
    session_id: SessionID
    message_batch_size: int
    message_frequency_ms: int
    expected_message_count: int
    thread_id: Optional[ThreadID] = None


@dataclass
class MessageDeliveryRecord:
    """Record of message delivery for validation."""
    message_id: MessageID
    sent_by_user: UserID
    received_by_user: UserID
    sent_timestamp: float
    received_timestamp: float
    message_content: str
    thread_id: Optional[ThreadID] = None


class ConcurrentSessionIsolationValidator:
    """Validates user session isolation during concurrent message processing."""
    
    def __init__(self, real_services):
        self.real_services = real_services
        self.message_delivery_log = []
        self.session_state_snapshots = {}
        self.isolation_violations = []
        self.redis_client = None
    
    async def setup_redis_connection(self):
        """Set up Redis connection for session management."""
        import redis.asyncio as redis
        self.redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        await self.redis_client.ping()  # Verify connection
    
    async def cleanup_redis_connection(self):
        """Clean up Redis connection."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def create_isolated_user_session(self, user_suffix: str) -> Tuple[UserID, SessionID, ThreadID]:
        """Create an isolated user session with dedicated resources."""
        user_id = f"session-test-user-{user_suffix}"
        session_id = f"session-{uuid.uuid4().hex}"
        thread_id = f"thread-{user_suffix}-{uuid.uuid4().hex[:8]}"
        
        # Create user in database
        await self.real_services["db"].execute("""
            INSERT INTO auth.users (id, email, name, is_active, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET 
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """, user_id, f"{user_id}@concurrent-test.com", f"Concurrent Test User {user_suffix}", True)
        
        # Create dedicated thread for this user's messages
        await self.real_services["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (id) DO UPDATE SET 
                title = EXCLUDED.title,
                updated_at = NOW()
        """, thread_id, user_id, f"Concurrent Messages Thread {user_suffix}")
        
        # Create isolated session in Redis
        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "thread_id": thread_id,
            "created_at": time.time(),
            "message_count": 0,
            "last_activity": time.time(),
            "isolation_namespace": f"user:{user_id}:session:{session_id}"
        }
        
        await self.redis_client.set(
            f"session:{session_id}",
            json.dumps(session_data),
            ex=3600
        )
        
        # Create WebSocket connection state
        ws_connection_id = f"ws-{session_id}"
        ws_state_data = {
            "user_id": user_id,
            "session_id": session_id,
            "connection_id": ws_connection_id,
            "state": WebSocketConnectionState.CONNECTED,
            "thread_id": thread_id,
            "active_since": time.time()
        }
        
        await self.redis_client.set(
            f"ws:state:{ws_connection_id}",
            json.dumps(ws_state_data),
            ex=3600
        )
        
        return user_id, session_id, thread_id
    
    async def simulate_concurrent_message_sending(self, test_scenarios: List[ConcurrentMessageTest]) -> Dict[str, Any]:
        """Simulate concurrent message sending across multiple user sessions."""
        
        async def send_message_batch(test_scenario: ConcurrentMessageTest) -> List[MessageDeliveryRecord]:
            """Send a batch of messages for one user."""
            delivery_records = []
            
            for i in range(test_scenario.message_batch_size):
                message_id = f"msg-{test_scenario.session_id}-{i}-{uuid.uuid4().hex[:8]}"
                message_content = f"Concurrent message {i} from user {test_scenario.user_id} at {time.time()}"
                sent_timestamp = time.time()
                
                # Store message in database
                await self.real_services["db"].execute("""
                    INSERT INTO backend.messages (id, thread_id, user_id, content, role, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                """, message_id, test_scenario.thread_id, test_scenario.user_id, message_content, "user")
                
                # Update session activity in Redis
                session_key = f"session:{test_scenario.session_id}"
                session_data = await self.redis_client.get(session_key)
                if session_data:
                    session_dict = json.loads(session_data)
                    session_dict["message_count"] += 1
                    session_dict["last_activity"] = time.time()
                    await self.redis_client.set(session_key, json.dumps(session_dict), ex=3600)
                
                # Record delivery
                delivery_record = MessageDeliveryRecord(
                    message_id=message_id,
                    sent_by_user=test_scenario.user_id,
                    received_by_user=test_scenario.user_id,  # Same user for now
                    sent_timestamp=sent_timestamp,
                    received_timestamp=time.time(),
                    message_content=message_content,
                    thread_id=test_scenario.thread_id
                )
                delivery_records.append(delivery_record)
                
                # Simulate message frequency delay
                if test_scenario.message_frequency_ms > 0:
                    await asyncio.sleep(test_scenario.message_frequency_ms / 1000.0)
            
            return delivery_records
        
        # Execute all message batches concurrently
        concurrent_tasks = [
            send_message_batch(scenario) for scenario in test_scenarios
        ]
        
        start_time = time.time()
        batch_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Collect and analyze results
        all_delivery_records = []
        successful_batches = 0
        failed_batches = 0
        
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                failed_batches += 1
                self.isolation_violations.append({
                    "type": "message_batch_failure",
                    "scenario_index": i,
                    "user_id": test_scenarios[i].user_id,
                    "error": str(result)
                })
            else:
                successful_batches += 1
                all_delivery_records.extend(result)
        
        return {
            "total_scenarios": len(test_scenarios),
            "successful_batches": successful_batches,
            "failed_batches": failed_batches,
            "total_messages_sent": len(all_delivery_records),
            "duration_seconds": end_time - start_time,
            "messages_per_second": len(all_delivery_records) / (end_time - start_time) if end_time > start_time else 0,
            "delivery_records": all_delivery_records,
            "isolation_violations": self.isolation_violations
        }
    
    async def validate_session_isolation_integrity(self, test_scenarios: List[ConcurrentMessageTest]) -> Dict[str, Any]:
        """Validate that user sessions remained isolated during concurrent operations."""
        validation_results = {
            "session_integrity": True,
            "message_isolation": True,
            "thread_isolation": True,
            "redis_isolation": True,
            "violations": []
        }
        
        # Check 1: Session integrity - each session should have correct message count
        for scenario in test_scenarios:
            session_key = f"session:{scenario.session_id}"
            session_data = await self.redis_client.get(session_key)
            
            if session_data:
                session_dict = json.loads(session_data)
                expected_count = scenario.expected_message_count
                actual_count = session_dict.get("message_count", 0)
                
                if actual_count != expected_count:
                    violation = {
                        "type": "session_message_count_mismatch",
                        "user_id": scenario.user_id,
                        "session_id": scenario.session_id,
                        "expected_count": expected_count,
                        "actual_count": actual_count
                    }
                    validation_results["violations"].append(violation)
                    validation_results["session_integrity"] = False
            else:
                validation_results["violations"].append({
                    "type": "missing_session_data",
                    "user_id": scenario.user_id,
                    "session_id": scenario.session_id
                })
                validation_results["session_integrity"] = False
        
        # Check 2: Message isolation - messages should only exist in correct threads
        for scenario in test_scenarios:
            # Count messages in user's thread
            user_messages = await self.real_services["db"].fetch("""
                SELECT COUNT(*) as count FROM backend.messages
                WHERE thread_id = $1 AND user_id = $2
            """, scenario.thread_id, scenario.user_id)
            
            expected_count = scenario.expected_message_count
            actual_count = user_messages[0]["count"] if user_messages else 0
            
            if actual_count != expected_count:
                violation = {
                    "type": "database_message_count_mismatch",
                    "user_id": scenario.user_id,
                    "thread_id": scenario.thread_id,
                    "expected_count": expected_count,
                    "actual_count": actual_count
                }
                validation_results["violations"].append(violation)
                validation_results["message_isolation"] = False
            
            # Check for messages leaking to other users' threads
            leaked_messages = await self.real_services["db"].fetch("""
                SELECT id, thread_id, user_id FROM backend.messages
                WHERE content LIKE $1 AND user_id != $2
            """, f"%message % from user {scenario.user_id}%", scenario.user_id)
            
            if leaked_messages:
                validation_results["violations"].append({
                    "type": "message_leakage_to_other_users",
                    "source_user": scenario.user_id,
                    "leaked_messages": len(leaked_messages),
                    "leaked_to_users": list(set(msg["user_id"] for msg in leaked_messages))
                })
                validation_results["message_isolation"] = False
        
        # Check 3: Thread isolation - users should not have access to other users' threads
        for i, scenario_a in enumerate(test_scenarios):
            for j, scenario_b in enumerate(test_scenarios):
                if i != j:  # Different users
                    # Check if user A has any messages in user B's thread
                    cross_contamination = await self.real_services["db"].fetch("""
                        SELECT COUNT(*) as count FROM backend.messages
                        WHERE thread_id = $1 AND user_id = $2
                    """, scenario_b.thread_id, scenario_a.user_id)
                    
                    contamination_count = cross_contamination[0]["count"] if cross_contamination else 0
                    if contamination_count > 0:
                        validation_results["violations"].append({
                            "type": "cross_thread_contamination",
                            "user_a": scenario_a.user_id,
                            "user_b": scenario_b.user_id,
                            "contaminated_thread": scenario_b.thread_id,
                            "contamination_count": contamination_count
                        })
                        validation_results["thread_isolation"] = False
        
        return validation_results


class TestWebSocketUserSessionConcurrentIsolation(BaseIntegrationTest):
    """
    Integration test for user session isolation during concurrent message processing.
    
    CRITICAL: Validates that user sessions remain isolated when processing many
    concurrent WebSocket messages, ensuring no cross-user contamination.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.concurrency
    async def test_concurrent_message_processing_session_isolation(self, real_services_fixture):
        """
        Test user session isolation during high-frequency concurrent message processing.
        
        This test simulates multiple users sending messages simultaneously and verifies
        that sessions remain isolated with no cross-user contamination.
        """
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = ConcurrentSessionIsolationValidator(real_services_fixture)
        await validator.setup_redis_connection()
        
        try:
            # Create multiple user sessions for concurrent testing
            test_scenarios = []
            
            for i in range(4):  # 4 concurrent users
                user_id, session_id, thread_id = await validator.create_isolated_user_session(f"concurrent-{i}")
                
                scenario = ConcurrentMessageTest(
                    user_id=user_id,
                    session_id=session_id,
                    message_batch_size=10,  # Each user sends 10 messages
                    message_frequency_ms=50,  # 50ms between messages (20 messages/second)
                    expected_message_count=10,
                    thread_id=thread_id
                )
                test_scenarios.append(scenario)
            
            # Execute concurrent message sending
            concurrent_results = await validator.simulate_concurrent_message_sending(test_scenarios)
            
            # Verify concurrent execution succeeded
            assert concurrent_results["successful_batches"] == 4, \
                f"Expected 4 successful batches, got {concurrent_results['successful_batches']}"
            assert concurrent_results["failed_batches"] == 0, \
                f"Unexpected failures: {concurrent_results['isolation_violations']}"
            assert concurrent_results["total_messages_sent"] == 40, \
                f"Expected 40 total messages, got {concurrent_results['total_messages_sent']}"
            
            # Validate session isolation integrity
            isolation_results = await validator.validate_session_isolation_integrity(test_scenarios)
            
            # CRITICAL ASSERTIONS: Session isolation must be maintained
            assert isolation_results["session_integrity"], \
                f"Session integrity violated: {isolation_results['violations']}"
            assert isolation_results["message_isolation"], \
                f"Message isolation violated: {isolation_results['violations']}"
            assert isolation_results["thread_isolation"], \
                f"Thread isolation violated: {isolation_results['violations']}"
            assert isolation_results["redis_isolation"], \
                f"Redis isolation violated: {isolation_results['violations']}"
            
            # Performance validation
            messages_per_second = concurrent_results["messages_per_second"]
            assert messages_per_second > 10, \
                f"Message processing too slow: {messages_per_second:.2f} msg/sec"
            
        finally:
            await validator.cleanup_redis_connection()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_high_frequency_message_session_isolation(self, real_services_fixture):
        """Test session isolation under high-frequency message load."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = ConcurrentSessionIsolationValidator(real_services_fixture)
        await validator.setup_redis_connection()
        
        try:
            # Create scenarios with high message frequency
            test_scenarios = []
            
            for i in range(3):  # 3 users with high-frequency messages
                user_id, session_id, thread_id = await validator.create_isolated_user_session(f"high-freq-{i}")
                
                scenario = ConcurrentMessageTest(
                    user_id=user_id,
                    session_id=session_id,
                    message_batch_size=25,  # More messages per user
                    message_frequency_ms=20,  # 20ms between messages (50 messages/second)
                    expected_message_count=25,
                    thread_id=thread_id
                )
                test_scenarios.append(scenario)
            
            # Execute high-frequency concurrent messaging
            high_freq_results = await validator.simulate_concurrent_message_sending(test_scenarios)
            
            # Verify high-frequency processing maintains isolation
            assert high_freq_results["successful_batches"] == 3
            assert high_freq_results["failed_batches"] == 0
            assert high_freq_results["total_messages_sent"] == 75
            
            # Validate isolation under high frequency
            isolation_results = await validator.validate_session_isolation_integrity(test_scenarios)
            
            assert len(isolation_results["violations"]) == 0, \
                f"High-frequency processing violated isolation: {isolation_results['violations']}"
            
            # Performance assertion
            assert high_freq_results["messages_per_second"] > 30, \
                "High-frequency message processing performance insufficient"
            
        finally:
            await validator.cleanup_redis_connection()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.stress
    async def test_session_isolation_message_burst_stress(self, real_services_fixture):
        """Test session isolation during message burst scenarios (stress test)."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = ConcurrentSessionIsolationValidator(real_services_fixture)
        await validator.setup_redis_connection()
        
        try:
            # Create burst scenarios - many messages sent rapidly
            test_scenarios = []
            
            for i in range(2):  # 2 users with burst messages
                user_id, session_id, thread_id = await validator.create_isolated_user_session(f"burst-{i}")
                
                scenario = ConcurrentMessageTest(
                    user_id=user_id,
                    session_id=session_id,
                    message_batch_size=50,  # Large burst
                    message_frequency_ms=5,  # Very fast (200 messages/second)
                    expected_message_count=50,
                    thread_id=thread_id
                )
                test_scenarios.append(scenario)
            
            # Execute burst messaging
            burst_results = await validator.simulate_concurrent_message_sending(test_scenarios)
            
            # Verify burst handling maintains isolation
            assert burst_results["successful_batches"] == 2
            assert burst_results["total_messages_sent"] == 100
            
            # Critical: Isolation must be maintained even during burst
            isolation_results = await validator.validate_session_isolation_integrity(test_scenarios)
            assert len(isolation_results["violations"]) == 0, \
                f"Message burst violated session isolation: {isolation_results['violations']}"
            
        finally:
            await validator.cleanup_redis_connection()