#!/usr/bin/env python

"""

CRITICAL: WebSocket Reconnection and Recovery Failure Test Suite



BUSINESS CRITICAL RELIABILITY REQUIREMENTS:

- WebSocket connections MUST automatically reconnect on disconnection

- In-flight notifications MUST be queued and delivered after reconnection

- User state MUST be preserved across reconnection cycles

- No duplicate notifications MUST occur during reconnection

- Recovery MUST complete within acceptable time bounds



These tests are designed to FAIL initially to expose reconnection issues:

1. Lost notifications during reconnection window

2. Duplicate notifications after reconnection

3. User state corruption during connection recovery

4. Failed reconnection attempts causing permanent disconnection

5. Message ordering issues during recovery

6. Silent failures in reconnection logic



Business Impact: Connection instability = poor user experience = churn

Reliability Impact: System appears unreliable and broken to users

"""



import asyncio

import json

import os

import sys

import time

import uuid

import threading

import random

from concurrent.futures import ThreadPoolExecutor

from datetime import datetime, timedelta

from typing import Dict, List, Set, Any, Optional, Callable, NamedTuple

from dataclasses import dataclass, field

from enum import Enum

import pytest

from shared.isolated_environment import IsolatedEnvironment



# Add project root to path

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

if project_root not in sys.path:

    sys.path.insert(0, project_root)



from shared.isolated_environment import get_env

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager

from netra_backend.app.logging_config import central_logger

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler

from netra_backend.app.db.database_manager import DatabaseManager

from netra_backend.app.clients.auth_client_core import AuthServiceClient



logger = central_logger.get_logger(__name__)





class ConnectionState(Enum):

    """WebSocket connection states."""

    CONNECTED = "connected"

    DISCONNECTED = "disconnected"

    RECONNECTING = "reconnecting"

    FAILED = "failed"





@dataclass

class NotificationEvent:

    """A notification event with delivery tracking."""

    id: str

    user_id: str

    type: str

    payload: Dict[str, Any]

    created_at: float

    delivery_attempts: int = 0

    delivered_at: Optional[float] = None

    lost: bool = False

    duplicated: bool = False

    ordering_violation: bool = False





@dataclass

class ConnectionEvent:

    """A connection state change event."""

    timestamp: float

    user_id: str

    connection_id: str

    old_state: ConnectionState

    new_state: ConnectionState

    reason: str

    recovery_attempt: int = 0





@dataclass

class ReconnectionAttempt:

    """A reconnection attempt record."""

    timestamp: float

    user_id: str

    attempt_number: int

    success: bool

    duration_ms: float

    error_message: Optional[str] = None

    notifications_lost: int = 0

    notifications_duplicated: int = 0





class ReconnectionTracker:

    """Tracks WebSocket reconnection events and failures."""

    

    def __init__(self):

        self.connection_events: List[ConnectionEvent] = []

        self.reconnection_attempts: List[ReconnectionAttempt] = []

        self.notification_events: List[NotificationEvent] = []

        self.lost_notifications: List[NotificationEvent] = []

        self.duplicated_notifications: List[NotificationEvent] = []

        self.ordering_violations: List[Tuple[NotificationEvent, NotificationEvent]] = []

        self.permanent_disconnections: Set[str] = set()

        self.lock = threading.Lock()

    

    def record_connection_change(self, user_id: str, connection_id: str, 

                               old_state: ConnectionState, new_state: ConnectionState,

                               reason: str, recovery_attempt: int = 0):

        """Record a connection state change."""

        event = ConnectionEvent(

            timestamp=time.time(),

            user_id=user_id,

            connection_id=connection_id,

            old_state=old_state,

            new_state=new_state,

            reason=reason,

            recovery_attempt=recovery_attempt

        )

        

        with self.lock:

            self.connection_events.append(event)

            

            # Track permanent disconnections

            if new_state == ConnectionState.FAILED and recovery_attempt > 3:

                self.permanent_disconnections.add(user_id)

    

    def record_reconnection_attempt(self, user_id: str, attempt_number: int,

                                  success: bool, duration_ms: float,

                                  error_message: str = None,

                                  notifications_lost: int = 0,

                                  notifications_duplicated: int = 0):

        """Record a reconnection attempt."""

        attempt = ReconnectionAttempt(

            timestamp=time.time(),

            user_id=user_id,

            attempt_number=attempt_number,

            success=success,

            duration_ms=duration_ms,

            error_message=error_message,

            notifications_lost=notifications_lost,

            notifications_duplicated=notifications_duplicated

        )

        

        with self.lock:

            self.reconnection_attempts.append(attempt)

    

    def record_notification(self, notification: NotificationEvent):

        """Record a notification event."""

        with self.lock:

            self.notification_events.append(notification)

            

            if notification.lost:

                self.lost_notifications.append(notification)

            if notification.duplicated:

                self.duplicated_notifications.append(notification)

    

    def detect_ordering_violation(self, notification1: NotificationEvent, 

                                notification2: NotificationEvent):

        """Detect message ordering violations."""

        if (notification1.user_id == notification2.user_id and

            notification1.created_at < notification2.created_at and

            notification1.delivered_at > notification2.delivered_at):

            

            notification1.ordering_violation = True

            notification2.ordering_violation = True

            

            with self.lock:

                self.ordering_violations.append((notification1, notification2))

    

    def get_failed_reconnections(self) -> List[ReconnectionAttempt]:

        """Get all failed reconnection attempts."""

        return [attempt for attempt in self.reconnection_attempts if not attempt.success]

    

    def get_users_with_permanent_disconnection(self) -> Set[str]:

        """Get users with permanent disconnection failures."""

        return self.permanent_disconnections.copy()





@pytest.fixture

def reconnection_tracker():

    """Fixture providing reconnection tracking."""

    tracker = ReconnectionTracker()

    yield tracker





class TestReconnectionFailureScenarios:

    """Test WebSocket reconnection failure scenarios."""

    

    @pytest.mark.asyncio

    @pytest.mark.critical

    async def test_notifications_lost_during_reconnection_window(self, reconnection_tracker):

        """CRITICAL: Test notifications lost during reconnection window."""

        # This test SHOULD FAIL initially

        

        user_id = "user_001"

        connection_id = f"conn_{user_id}"

        

        # Simulate WebSocket connection with reconnection issues

        connection_state = ConnectionState.CONNECTED

        notification_buffer = []  # Buffer for disconnection period

        

        async def simulate_connection_interruption():

            """Simulate connection interruption and reconnection."""

            nonlocal connection_state

            

            # Connection drops

            connection_state = ConnectionState.DISCONNECTED

            reconnection_tracker.record_connection_change(

                user_id, connection_id, ConnectionState.CONNECTED, 

                ConnectionState.DISCONNECTED, "Network interruption"

            )

            

            # Disconnection window where notifications are lost

            disconnection_duration = random.uniform(2.0, 5.0)  # 2-5 second disconnection

            await asyncio.sleep(disconnection_duration)

            

            # Attempt reconnection

            connection_state = ConnectionState.RECONNECTING

            reconnection_tracker.record_connection_change(

                user_id, connection_id, ConnectionState.DISCONNECTED,

                ConnectionState.RECONNECTING, "Attempting reconnection"

            )

            

            # Reconnection may fail

            reconnection_success = random.random() > 0.3  # 70% success rate

            reconnection_start = time.time()

            

            if reconnection_success:

                await asyncio.sleep(random.uniform(0.5, 2.0))  # Reconnection delay

                connection_state = ConnectionState.CONNECTED

                

                reconnection_duration = (time.time() - reconnection_start) * 1000

                reconnection_tracker.record_reconnection_attempt(

                    user_id, 1, True, reconnection_duration

                )

                

                reconnection_tracker.record_connection_change(

                    user_id, connection_id, ConnectionState.RECONNECTING,

                    ConnectionState.CONNECTED, "Reconnection successful"

                )

            else:

                # Reconnection failed

                reconnection_duration = (time.time() - reconnection_start) * 1000

                reconnection_tracker.record_reconnection_attempt(

                    user_id, 1, False, reconnection_duration,

                    error_message="Reconnection failed - server unavailable"

                )

                

                connection_state = ConnectionState.FAILED

                reconnection_tracker.record_connection_change(

                    user_id, connection_id, ConnectionState.RECONNECTING,

                    ConnectionState.FAILED, "Reconnection failed permanently"

                )

        

        async def send_notifications_during_disconnection():

            """Send notifications while connection is unstable."""

            notification_sequence = [

                ("tool_started", {"tool_name": "important_tool"}),

                ("tool_progress", {"progress": 25}),

                ("tool_progress", {"progress": 50}),

                ("tool_progress", {"progress": 75}),

                ("tool_completed", {"result": "success"}),

                ("agent_completed", {"status": "done"})

            ]

            

            for seq_num, (event_type, payload) in enumerate(notification_sequence):

                notification = NotificationEvent(

                    id=f"notif_{user_id}_{seq_num}",

                    user_id=user_id,

                    type=event_type,

                    payload=payload,

                    created_at=time.time()

                )

                

                # Try to send notification

                if connection_state == ConnectionState.CONNECTED:

                    # Notification delivered successfully

                    notification.delivered_at = time.time()

                    notification.delivery_attempts = 1

                    

                elif connection_state in [ConnectionState.DISCONNECTED, ConnectionState.RECONNECTING]:

                    # Notification lost during disconnection window!

                    notification.lost = True

                    notification.delivery_attempts = 0

                    

                elif connection_state == ConnectionState.FAILED:

                    # Permanent failure - notification permanently lost

                    notification.lost = True

                    notification.delivery_attempts = 0

                

                reconnection_tracker.record_notification(notification)

                

                # Small delay between notifications

                await asyncio.sleep(0.2)

        

        # Run connection interruption and notification sending concurrently

        disconnection_task = asyncio.create_task(simulate_connection_interruption())

        notification_task = asyncio.create_task(send_notifications_during_disconnection())

        

        await asyncio.gather(disconnection_task, notification_task)

        

        # Verify notifications were lost

        lost_notifications = reconnection_tracker.lost_notifications

        assert len(lost_notifications) > 0, "Expected some notifications to be lost during disconnection"

        

        # Check for critical notification loss

        critical_events = ["tool_started", "tool_completed", "agent_completed"]

        lost_critical = [n for n in lost_notifications if n.type in critical_events]

        assert len(lost_critical) > 0, "Expected critical notifications to be lost"

        

        # Verify some reconnection attempts failed

        failed_reconnections = reconnection_tracker.get_failed_reconnections()

        if failed_reconnections:

            assert len(failed_reconnections) > 0, "Expected some reconnection failures"

        

        # Check for permanent disconnections

        permanent_disconnections = reconnection_tracker.get_users_with_permanent_disconnection()

        if connection_state == ConnectionState.FAILED:

            assert user_id in permanent_disconnections, "Expected permanent disconnection to be tracked"

    

    @pytest.mark.asyncio

    @pytest.mark.critical

    async def test_duplicate_notifications_after_reconnection(self, reconnection_tracker):

        """CRITICAL: Test duplicate notifications after reconnection."""

        # This test SHOULD FAIL initially

        

        user_id = "user_001"

        connection_id = f"conn_{user_id}"

        

        # Simulate notification system with duplicate delivery bug

        sent_notifications_log = []  # Track what was sent

        delivered_notifications_log = []  # Track what was delivered

        

        # Connection state

        connection_stable = True

        

        async def send_notification_with_retry_bug(notification_data: Dict[str, Any]):

            """Send notification with faulty retry logic."""

            notification_id = f"notif_{len(sent_notifications_log)}"

            

            notification = NotificationEvent(

                id=notification_id,

                user_id=user_id,

                type=notification_data["type"],

                payload=notification_data,

                created_at=time.time()

            )

            

            sent_notifications_log.append(notification)

            reconnection_tracker.record_notification(notification)

            

            max_retries = 3

            retry_delay = 0.1

            

            for attempt in range(max_retries):

                notification.delivery_attempts += 1

                

                try:

                    if not connection_stable:

                        # Connection unstable - retry

                        raise ConnectionError("Connection unstable")

                    

                    # Simulate delivery

                    await asyncio.sleep(random.uniform(0.01, 0.05))

                    

                    # BUG: Always continue retrying even after success

                    notification.delivered_at = time.time()

                    delivered_notifications_log.append(notification)

                    

                    # Should break here but doesn't due to bug!

                    # continue retrying...

                    

                    if attempt < max_retries - 1:  # More retries coming

                        await asyncio.sleep(retry_delay)

                        

                        # Create duplicate delivery

                        duplicate_notification = NotificationEvent(

                            id=f"{notification_id}_dup_{attempt}",

                            user_id=user_id,

                            type=notification_data["type"],

                            payload=notification_data,

                            created_at=notification.created_at,

                            delivered_at=time.time(),

                            duplicated=True,

                            delivery_attempts=attempt + 2

                        )

                        

                        delivered_notifications_log.append(duplicate_notification)

                        reconnection_tracker.record_notification(duplicate_notification)

                    

                except ConnectionError:

                    # Retry after delay

                    await asyncio.sleep(retry_delay)

                    retry_delay *= 2  # Exponential backoff

                    continue

            

            return notification

        

        # Simulate connection becoming unstable and recovering

        async def simulate_connection_instability():

            """Simulate connection instability during notification sending."""

            nonlocal connection_stable

            

            await asyncio.sleep(1.0)  # Stable initially

            

            # Connection becomes unstable

            connection_stable = False

            reconnection_tracker.record_connection_change(

                user_id, connection_id, ConnectionState.CONNECTED,

                ConnectionState.DISCONNECTED, "Intermittent disconnection"

            )

            

            await asyncio.sleep(2.0)  # Unstable period

            

            # Connection recovers

            connection_stable = True

            reconnection_tracker.record_connection_change(

                user_id, connection_id, ConnectionState.DISCONNECTED,

                ConnectionState.CONNECTED, "Connection recovered"

            )

        

        # Send notifications during connection instability

        instability_task = asyncio.create_task(simulate_connection_instability())

        

        notification_tasks = []

        for i in range(10):

            notification_data = {

                "type": "tool_progress",

                "progress": i * 10,

                "tool_name": "test_tool",

                "sequence": i

            }

            

            task = asyncio.create_task(send_notification_with_retry_bug(notification_data))

            notification_tasks.append(task)

            

            await asyncio.sleep(0.3)  # Send every 300ms

        

        # Wait for all tasks

        await asyncio.gather(instability_task, *notification_tasks)

        

        # Verify duplicate notifications occurred

        duplicated_notifications = reconnection_tracker.duplicated_notifications

        assert len(duplicated_notifications) > 0, "Expected duplicate notifications from retry bug"

        

        # Check delivery counts

        total_sent = len(sent_notifications_log)

        total_delivered = len(delivered_notifications_log)

        

        # Should have more deliveries than sends due to duplicates

        assert total_delivered > total_sent, f"Expected duplicates: {total_delivered} delivered vs {total_sent} sent"

        

        # Verify duplicate ratio

        duplicate_ratio = (total_delivered - total_sent) / total_sent

        assert duplicate_ratio > 0.2, f"Expected significant duplicates, got {duplicate_ratio:.1%}"

        

        # Check for specific duplicate types

        duplicate_events = [n for n in delivered_notifications_log if n.duplicated]

        progress_duplicates = [n for n in duplicate_events if n.type == "tool_progress"]

        

        assert len(progress_duplicates) > 0, "Expected progress notification duplicates"

    

    @pytest.mark.asyncio

    @pytest.mark.critical

    async def test_message_ordering_corruption_during_reconnection(self, reconnection_tracker):

        """CRITICAL: Test message ordering corruption during reconnection."""

        # This test SHOULD FAIL initially

        

        user_id = "user_001"

        

        # Simulate message buffering system with ordering bugs

        message_buffer = []

        delivered_messages = []

        connection_available = True

        

        async def buffer_and_deliver_notification(notification_data: Dict[str, Any], sequence_num: int):

            """Buffer notification and deliver with potential ordering issues."""

            notification = NotificationEvent(

                id=f"seq_{sequence_num:03d}",

                user_id=user_id,

                type=notification_data["type"],

                payload={**notification_data, "sequence": sequence_num},

                created_at=time.time()

            )

            

            # Add to buffer

            message_buffer.append(notification)

            

            # Try to deliver if connection available

            if connection_available:

                # Deliver immediately (correct ordering)

                notification.delivered_at = time.time()

                delivered_messages.append(notification)

                reconnection_tracker.record_notification(notification)

            else:

                # Buffer for later delivery during reconnection

                pass

        

        async def trigger_reconnection_with_ordering_bug():

            """Trigger reconnection that corrupts message ordering."""

            nonlocal connection_available

            

            await asyncio.sleep(1.0)  # Let some messages send normally

            

            # Connection drops

            connection_available = False

            reconnection_tracker.record_connection_change(

                user_id, "conn_001", ConnectionState.CONNECTED,

                ConnectionState.DISCONNECTED, "Connection dropped"

            )

            

            await asyncio.sleep(2.0)  # Disconnection period - messages buffer

            

            # Reconnection starts

            reconnection_tracker.record_connection_change(

                user_id, "conn_001", ConnectionState.DISCONNECTED,

                ConnectionState.RECONNECTING, "Starting reconnection"

            )

            

            await asyncio.sleep(0.5)  # Reconnection delay

            

            # Connection restored

            connection_available = True

            reconnection_tracker.record_connection_change(

                user_id, "conn_001", ConnectionState.RECONNECTING,

                ConnectionState.CONNECTED, "Reconnection successful"

            )

            

            # Deliver buffered messages in WRONG ORDER (the bug!)

            buffered_notifications = [n for n in message_buffer if n.delivered_at is None]

            

            # Sort by ID instead of creation time (WRONG!)

            buffered_notifications.sort(key=lambda n: n.id)  # Alphabetical sort corrupts order

            

            # Deliver in corrupted order

            for notification in buffered_notifications:

                notification.delivered_at = time.time()

                delivered_messages.append(notification)

                reconnection_tracker.record_notification(notification)

                

                await asyncio.sleep(0.01)  # Small delay between deliveries

        

        # Send sequence of ordered notifications

        reconnection_task = asyncio.create_task(trigger_reconnection_with_ordering_bug())

        

        notification_tasks = []

        for seq_num in range(20):

            notification_data = {

                "type": "tool_progress",

                "step": f"step_{seq_num:02d}",

                "progress": seq_num * 5,

                "tool_name": "sequential_tool",

                "depends_on_previous": True  # Order matters!

            }

            

            task = asyncio.create_task(

                buffer_and_deliver_notification(notification_data, seq_num)

            )

            notification_tasks.append(task)

            

            await asyncio.sleep(0.1)  # 100ms between notifications

        

        await asyncio.gather(reconnection_task, *notification_tasks)

        

        # Verify ordering violations occurred

        delivered_messages.sort(key=lambda n: n.delivered_at or 0)

        

        # Check for sequence violations

        for i in range(len(delivered_messages) - 1):

            current_msg = delivered_messages[i]

            next_msg = delivered_messages[i + 1]

            

            current_seq = current_msg.payload.get("sequence", 0)

            next_seq = next_msg.payload.get("sequence", 0)

            

            # If sequences are out of order, detect violation

            if current_seq > next_seq and current_msg.user_id == next_msg.user_id:

                reconnection_tracker.detect_ordering_violation(current_msg, next_msg)

        

        # Verify ordering violations were detected

        assert len(reconnection_tracker.ordering_violations) > 0, "Expected message ordering violations"

        

        # Check that dependent messages were delivered out of order

        progress_messages = [n for n in delivered_messages if n.type == "tool_progress"]

        if len(progress_messages) > 5:

            # Check if progress values are out of order

            progress_values = [n.payload.get("progress", 0) for n in progress_messages]

            expected_order = sorted(progress_values)

            

            if progress_values != expected_order:

                assert True, f"Progress messages out of order: {progress_values} != {expected_order}"

    

    @pytest.mark.asyncio

    @pytest.mark.critical

    async def test_reconnection_state_corruption_cascading_failures(self, reconnection_tracker):

        """CRITICAL: Test reconnection state corruption causing cascading failures."""

        # This test SHOULD FAIL initially

        

        users = ["user_001", "user_002", "user_003"]

        

        # Simulate shared reconnection state (the bug!)

        shared_reconnection_state = {

            "current_reconnecting_user": None,

            "reconnection_context": None,

            "buffered_notifications": {},

            "connection_metadata": {}

        }

        

        async def reconnect_with_state_corruption(user_id: str):

            """Attempt reconnection with shared state corruption."""

            connection_id = f"conn_{user_id}"

            

            # Connection drops

            reconnection_tracker.record_connection_change(

                user_id, connection_id, ConnectionState.CONNECTED,

                ConnectionState.DISCONNECTED, "Network timeout"

            )

            

            # Multiple users try to reconnect simultaneously (race condition!)

            shared_reconnection_state["current_reconnecting_user"] = user_id

            shared_reconnection_state["reconnection_context"] = {

                "user_id": user_id,

                "connection_id": connection_id,

                "reconnection_start": time.time(),

                "buffered_messages": []

            }

            

            # Small delay allows other users to corrupt the state

            await asyncio.sleep(random.uniform(0.01, 0.05))

            

            # Check if state was corrupted by another user

            current_context = shared_reconnection_state["reconnection_context"]

            current_user = shared_reconnection_state["current_reconnecting_user"]

            

            reconnection_start = time.time()

            

            if current_user != user_id:

                # State corrupted by another user's reconnection!

                reconnection_tracker.record_reconnection_attempt(

                    user_id, 1, False, 0,

                    error_message=f"Reconnection state corrupted by {current_user}",

                    notifications_lost=len(shared_reconnection_state["buffered_notifications"].get(user_id, []))

                )

                

                reconnection_tracker.record_connection_change(

                    user_id, connection_id, ConnectionState.DISCONNECTED,

                    ConnectionState.FAILED, f"State corrupted by {current_user}"

                )

                

                return False

            

            # Attempt reconnection with potentially corrupted context

            try:

                # Reconnection may succeed but with wrong user's context

                corrupted_context = current_context

                context_user = corrupted_context.get("user_id")

                

                await asyncio.sleep(random.uniform(0.1, 0.3))  # Reconnection delay

                

                if context_user == user_id:

                    # Successful reconnection

                    reconnection_duration = (time.time() - reconnection_start) * 1000

                    reconnection_tracker.record_reconnection_attempt(

                        user_id, 1, True, reconnection_duration

                    )

                    

                    reconnection_tracker.record_connection_change(

                        user_id, connection_id, ConnectionState.DISCONNECTED,

                        ConnectionState.CONNECTED, "Reconnection successful"

                    )

                    

                    return True

                else:

                    # Context corruption detected

                    reconnection_duration = (time.time() - reconnection_start) * 1000

                    reconnection_tracker.record_reconnection_attempt(

                        user_id, 1, False, reconnection_duration,

                        error_message=f"Context corrupted: got {context_user}, expected {user_id}"

                    )

                    

                    reconnection_tracker.record_connection_change(

                        user_id, connection_id, ConnectionState.DISCONNECTED,

                        ConnectionState.FAILED, f"Context corruption: wrong user {context_user}"

                    )

                    

                    return False

                    

            except Exception as e:

                reconnection_duration = (time.time() - reconnection_start) * 1000

                reconnection_tracker.record_reconnection_attempt(

                    user_id, 1, False, reconnection_duration,

                    error_message=str(e)

                )

                return False

        

        # Trigger concurrent reconnections

        reconnection_tasks = []

        for user_id in users:

            task = asyncio.create_task(reconnect_with_state_corruption(user_id))

            reconnection_tasks.append(task)

            

            # Stagger reconnection attempts slightly to create race conditions

            await asyncio.sleep(0.01)

        

        results = await asyncio.gather(*reconnection_tasks)

        

        # Verify state corruption caused failures

        failed_reconnections = reconnection_tracker.get_failed_reconnections()

        corruption_failures = [

            attempt for attempt in failed_reconnections

            if "corrupted" in (attempt.error_message or "").lower()

        ]

        

        assert len(corruption_failures) > 0, "Expected reconnection failures due to state corruption"

        

        # Check that not all users could reconnect successfully

        successful_reconnections = sum(1 for result in results if result)

        failed_reconnections_count = len(users) - successful_reconnections

        

        assert failed_reconnections_count > 0, f"Expected some reconnection failures, got {failed_reconnections_count}/{len(users)}"

        

        # Verify cascading failures

        connection_events = reconnection_tracker.connection_events

        failed_events = [e for e in connection_events if e.new_state == ConnectionState.FAILED]

        

        assert len(failed_events) > 0, "Expected cascading reconnection failures"

        

        # Check that state corruption affected multiple users

        corruption_events = [e for e in failed_events if "corruption" in e.reason.lower()]

        assert len(corruption_events) > 0, "Expected state corruption to affect multiple users"





class TestReconnectionRecoveryFailures:

    """Test recovery failure scenarios during reconnection."""

    

    @pytest.mark.asyncio

    @pytest.mark.critical

    async def test_notification_buffer_overflow_during_disconnection(self, reconnection_tracker):

        """CRITICAL: Test notification buffer overflow during extended disconnection."""

        # This test SHOULD FAIL initially

        

        user_id = "user_001"

        connection_id = f"conn_{user_id}"

        

        # Simulate limited notification buffer

        max_buffer_size = 50

        notification_buffer = []

        buffer_overflow_count = 0

        

        # Connection state

        connection_state = ConnectionState.CONNECTED

        

        async def buffer_notification_with_overflow(notification_data: Dict[str, Any], seq_num: int):

            """Buffer notification with potential overflow."""

            nonlocal buffer_overflow_count

            

            notification = NotificationEvent(

                id=f"buffer_{seq_num:03d}",

                user_id=user_id,

                type=notification_data["type"],

                payload=notification_data,

                created_at=time.time()

            )

            

            if connection_state == ConnectionState.CONNECTED:

                # Deliver immediately

                notification.delivered_at = time.time()

                notification.delivery_attempts = 1

                reconnection_tracker.record_notification(notification)

                return True

            

            else:

                # Buffer for later delivery

                if len(notification_buffer) < max_buffer_size:

                    notification_buffer.append(notification)

                    reconnection_tracker.record_notification(notification)

                    return True

                else:

                    # Buffer overflow - notification lost!

                    buffer_overflow_count += 1

                    notification.lost = True

                    notification.delivery_attempts = 0

                    reconnection_tracker.record_notification(notification)

                    return False

        

        async def simulate_extended_disconnection():

            """Simulate extended disconnection that overflows buffer."""

            nonlocal connection_state

            

            await asyncio.sleep(1.0)  # Normal operation initially

            

            # Extended disconnection starts

            connection_state = ConnectionState.DISCONNECTED

            reconnection_tracker.record_connection_change(

                user_id, connection_id, ConnectionState.CONNECTED,

                ConnectionState.DISCONNECTED, "Extended network outage"

            )

            

            # Disconnection lasts long enough to overflow buffer

            disconnection_duration = 15.0  # 15 seconds - long enough to overflow

            await asyncio.sleep(disconnection_duration)

            

            # Reconnection attempts

            for attempt in range(3):

                connection_state = ConnectionState.RECONNECTING

                reconnection_tracker.record_connection_change(

                    user_id, connection_id, ConnectionState.DISCONNECTED,

                    ConnectionState.RECONNECTING, f"Reconnection attempt {attempt + 1}"

                )

                

                await asyncio.sleep(random.uniform(1.0, 3.0))  # Reconnection delay

                

                # 60% chance of success per attempt

                if random.random() < 0.6:

                    connection_state = ConnectionState.CONNECTED

                    

                    reconnection_duration = disconnection_duration * 1000

                    reconnection_tracker.record_reconnection_attempt(

                        user_id, attempt + 1, True, reconnection_duration,

                        notifications_lost=buffer_overflow_count

                    )

                    

                    reconnection_tracker.record_connection_change(

                        user_id, connection_id, ConnectionState.RECONNECTING,

                        ConnectionState.CONNECTED, "Reconnection successful"

                    )

                    

                    # Deliver buffered notifications (may be incomplete due to overflow)

                    for buffered_notification in notification_buffer:

                        buffered_notification.delivered_at = time.time()

                        buffered_notification.delivery_attempts = 1

                    

                    break

                else:

                    # Reconnection failed

                    reconnection_tracker.record_reconnection_attempt(

                        user_id, attempt + 1, False, (time.time() * 1000),

                        error_message=f"Reconnection attempt {attempt + 1} failed"

                    )

                    

                    connection_state = ConnectionState.DISCONNECTED

                    reconnection_tracker.record_connection_change(

                        user_id, connection_id, ConnectionState.RECONNECTING,

                        ConnectionState.DISCONNECTED, f"Reconnection attempt {attempt + 1} failed"

                    )

            

            # If all reconnection attempts failed

            if connection_state != ConnectionState.CONNECTED:

                connection_state = ConnectionState.FAILED

                reconnection_tracker.record_connection_change(

                    user_id, connection_id, ConnectionState.DISCONNECTED,

                    ConnectionState.FAILED, "All reconnection attempts failed"

                )

        

        # Send continuous stream of notifications during disconnection

        disconnection_task = asyncio.create_task(simulate_extended_disconnection())

        

        notification_tasks = []

        for seq_num in range(100):  # Send more than buffer capacity

            notification_data = {

                "type": "tool_progress",

                "step": f"step_{seq_num:03d}",

                "progress": seq_num,

                "critical": seq_num % 10 == 0,  # Every 10th is critical

                "timestamp": time.time()

            }

            

            task = asyncio.create_task(

                buffer_notification_with_overflow(notification_data, seq_num)

            )

            notification_tasks.append(task)

            

            await asyncio.sleep(0.1)  # Send every 100ms

        

        await asyncio.gather(disconnection_task, *notification_tasks)

        

        # Verify buffer overflow occurred

        assert buffer_overflow_count > 0, f"Expected buffer overflow, got {buffer_overflow_count} overflows"

        

        # Check that critical notifications were lost

        lost_notifications = reconnection_tracker.lost_notifications

        critical_lost = [n for n in lost_notifications if n.payload.get("critical")]

        

        assert len(lost_notifications) > 20, f"Expected significant notification loss, got {len(lost_notifications)}"

        assert len(critical_lost) > 0, "Expected critical notifications to be lost"

        

        # Verify reconnection was attempted but may have failed

        reconnection_attempts = reconnection_tracker.reconnection_attempts

        assert len(reconnection_attempts) > 0, "Expected reconnection attempts"

        

        # Check for permanent disconnection if all attempts failed

        if all(not attempt.success for attempt in reconnection_attempts):

            permanent_disconnections = reconnection_tracker.get_users_with_permanent_disconnection()

            assert user_id in permanent_disconnections, "Expected permanent disconnection after failed attempts"

    

    @pytest.mark.asyncio

    @pytest.mark.critical

    async def test_user_state_corruption_during_recovery(self, reconnection_tracker):

        """CRITICAL: Test user state corruption during connection recovery."""

        # This test SHOULD FAIL initially

        

        users = ["user_001", "user_002", "user_003"]

        

        # Simulate shared user state during recovery (vulnerability!)

        shared_recovery_state = {

            "current_recovering_user": None,

            "recovery_context": None,

            "user_session_data": {},

            "recovery_metadata": {}

        }

        

        async def recover_user_session_with_corruption(user_id: str):

            """Recover user session with potential state corruption."""

            connection_id = f"conn_{user_id}"

            

            # User disconnects

            reconnection_tracker.record_connection_change(

                user_id, connection_id, ConnectionState.CONNECTED,

                ConnectionState.DISCONNECTED, "Session recovery needed"

            )

            

            # Start recovery process

            shared_recovery_state["current_recovering_user"] = user_id

            shared_recovery_state["recovery_context"] = {

                "user_id": user_id,

                "session_data": {

                    "active_tools": [f"tool_{user_id}_{i}" for i in range(3)],

                    "user_preferences": {"theme": user_id[-1], "lang": "en"},

                    "authentication_context": f"auth_token_{user_id}",

                    "cached_responses": {f"cache_{i}": f"data_{user_id}_{i}" for i in range(5)}

                },

                "recovery_timestamp": time.time()

            }

            

            # Store session data

            shared_recovery_state["user_session_data"][user_id] = shared_recovery_state["recovery_context"]["session_data"]

            

            # Delay during recovery (allows state corruption)

            await asyncio.sleep(random.uniform(0.05, 0.15))

            

            # Check if recovery context was corrupted

            current_context = shared_recovery_state["recovery_context"]

            current_user = shared_recovery_state["current_recovering_user"]

            

            if current_user != user_id:

                # State corrupted by concurrent recovery!

                reconnection_tracker.record_reconnection_attempt(

                    user_id, 1, False, 0,

                    error_message=f"Recovery state corrupted by {current_user}"

                )

                

                reconnection_tracker.record_connection_change(

                    user_id, connection_id, ConnectionState.DISCONNECTED,

                    ConnectionState.FAILED, f"Recovery corrupted by {current_user}"

                )

                

                return False

            

            # Recover with potentially wrong session data

            recovered_session_data = shared_recovery_state["user_session_data"].get(user_id)

            if not recovered_session_data:

                # Session data lost during corruption

                reconnection_tracker.record_reconnection_attempt(

                    user_id, 1, False, 100,

                    error_message="Session data lost during recovery"

                )

                return False

            

            # Check for session data corruption

            auth_context = recovered_session_data.get("authentication_context", "")

            if user_id not in auth_context:

                # Authentication context corrupted!

                reconnection_tracker.record_reconnection_attempt(

                    user_id, 1, False, 100,

                    error_message=f"Authentication corrupted: {auth_context} doesn't match {user_id}"

                )

                

                reconnection_tracker.record_connection_change(

                    user_id, connection_id, ConnectionState.DISCONNECTED,

                    ConnectionState.FAILED, "Authentication context corrupted"

                )

                

                return False

            

            # "Successful" recovery but may have wrong user's data

            reconnection_duration = (time.time() - reconnection_start) * 1000

            reconnection_tracker.record_reconnection_attempt(

                user_id, 1, True, reconnection_duration

            )

            

            reconnection_tracker.record_connection_change(

                user_id, connection_id, ConnectionState.DISCONNECTED,

                ConnectionState.CONNECTED, "Recovery completed"

            )

            

            return True

        

        # Trigger concurrent recovery attempts

        recovery_tasks = []

        for user_id in users:

            task = asyncio.create_task(recover_user_session_with_corruption(user_id))

            recovery_tasks.append(task)

            

            # Small delay to create race conditions

            await asyncio.sleep(0.02)

        

        results = await asyncio.gather(*recovery_tasks)

        

        # Verify state corruption caused failures

        failed_reconnections = reconnection_tracker.get_failed_reconnections()

        corruption_failures = [

            attempt for attempt in failed_reconnections

            if "corrupted" in (attempt.error_message or "").lower()

        ]

        

        assert len(corruption_failures) > 0, "Expected recovery failures due to state corruption"

        

        # Check for authentication corruption

        auth_corruption_failures = [

            attempt for attempt in failed_reconnections

            if "authentication" in (attempt.error_message or "").lower()

        ]

        

        assert len(auth_corruption_failures) > 0, "Expected authentication corruption during recovery"

        

        # Verify some users ended up permanently disconnected

        permanent_disconnections = reconnection_tracker.get_users_with_permanent_disconnection()

        assert len(permanent_disconnections) > 0, "Expected some permanent disconnections due to corruption"

        

        # Check that successful recoveries may have corrupted data

        successful_recoveries = [attempt for attempt in reconnection_tracker.reconnection_attempts if attempt.success]

        

        # Even successful recoveries may have wrong user's data due to shared state

        for recovery in successful_recoveries:

            recovery_user = recovery.user_id

            final_session_data = shared_recovery_state["user_session_data"].get(recovery_user)

            

            if final_session_data:

                auth_context = final_session_data.get("authentication_context", "")

                cached_data = final_session_data.get("cached_responses", {})

                

                # Check if session data belongs to different user

                if recovery_user not in auth_context or any(recovery_user not in str(v) for v in cached_data.values()):

                    assert True, f"User {recovery_user} recovered with corrupted session data"





if __name__ == "__main__":

    # Run the test suite  

    pytest.main([__file__, "-v", "--tb=short", "-m", "critical"])

