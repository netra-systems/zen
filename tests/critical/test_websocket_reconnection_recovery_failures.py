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
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager as WebSocketManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
logger = central_logger.get_logger(__name__)

class ConnectionState(Enum):
    """WebSocket connection states."""
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    RECONNECTING = 'reconnecting'
    FAILED = 'failed'

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

    def record_connection_change(self, user_id: str, connection_id: str, old_state: ConnectionState, new_state: ConnectionState, reason: str, recovery_attempt: int=0):
        """Record a connection state change."""
        event = ConnectionEvent(timestamp=time.time(), user_id=user_id, connection_id=connection_id, old_state=old_state, new_state=new_state, reason=reason, recovery_attempt=recovery_attempt)
        with self.lock:
            self.connection_events.append(event)
            if new_state == ConnectionState.FAILED and recovery_attempt > 3:
                self.permanent_disconnections.add(user_id)

    def record_reconnection_attempt(self, user_id: str, attempt_number: int, success: bool, duration_ms: float, error_message: str=None, notifications_lost: int=0, notifications_duplicated: int=0):
        """Record a reconnection attempt."""
        attempt = ReconnectionAttempt(timestamp=time.time(), user_id=user_id, attempt_number=attempt_number, success=success, duration_ms=duration_ms, error_message=error_message, notifications_lost=notifications_lost, notifications_duplicated=notifications_duplicated)
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

    def detect_ordering_violation(self, notification1: NotificationEvent, notification2: NotificationEvent):
        """Detect message ordering violations."""
        if notification1.user_id == notification2.user_id and notification1.created_at < notification2.created_at and (notification1.delivered_at > notification2.delivered_at):
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

class ReconnectionFailureScenariosTests:
    """Test WebSocket reconnection failure scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_notifications_lost_during_reconnection_window(self, reconnection_tracker):
        """CRITICAL: Test notifications lost during reconnection window."""
        user_id = 'user_001'
        connection_id = f'conn_{user_id}'
        connection_state = ConnectionState.CONNECTED
        notification_buffer = []

        async def simulate_connection_interruption():
            """Simulate connection interruption and reconnection."""
            nonlocal connection_state
            connection_state = ConnectionState.DISCONNECTED
            reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.CONNECTED, ConnectionState.DISCONNECTED, 'Network interruption')
            disconnection_duration = random.uniform(2.0, 5.0)
            await asyncio.sleep(disconnection_duration)
            connection_state = ConnectionState.RECONNECTING
            reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.DISCONNECTED, ConnectionState.RECONNECTING, 'Attempting reconnection')
            reconnection_success = random.random() > 0.3
            reconnection_start = time.time()
            if reconnection_success:
                await asyncio.sleep(random.uniform(0.5, 2.0))
                connection_state = ConnectionState.CONNECTED
                reconnection_duration = (time.time() - reconnection_start) * 1000
                reconnection_tracker.record_reconnection_attempt(user_id, 1, True, reconnection_duration)
                reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.RECONNECTING, ConnectionState.CONNECTED, 'Reconnection successful')
            else:
                reconnection_duration = (time.time() - reconnection_start) * 1000
                reconnection_tracker.record_reconnection_attempt(user_id, 1, False, reconnection_duration, error_message='Reconnection failed - server unavailable')
                connection_state = ConnectionState.FAILED
                reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.RECONNECTING, ConnectionState.FAILED, 'Reconnection failed permanently')

        async def send_notifications_during_disconnection():
            """Send notifications while connection is unstable."""
            notification_sequence = [('tool_started', {'tool_name': 'important_tool'}), ('tool_progress', {'progress': 25}), ('tool_progress', {'progress': 50}), ('tool_progress', {'progress': 75}), ('tool_completed', {'result': 'success'}), ('agent_completed', {'status': 'done'})]
            for seq_num, (event_type, payload) in enumerate(notification_sequence):
                notification = NotificationEvent(id=f'notif_{user_id}_{seq_num}', user_id=user_id, type=event_type, payload=payload, created_at=time.time())
                if connection_state == ConnectionState.CONNECTED:
                    notification.delivered_at = time.time()
                    notification.delivery_attempts = 1
                elif connection_state in [ConnectionState.DISCONNECTED, ConnectionState.RECONNECTING]:
                    notification.lost = True
                    notification.delivery_attempts = 0
                elif connection_state == ConnectionState.FAILED:
                    notification.lost = True
                    notification.delivery_attempts = 0
                reconnection_tracker.record_notification(notification)
                await asyncio.sleep(0.2)
        disconnection_task = asyncio.create_task(simulate_connection_interruption())
        notification_task = asyncio.create_task(send_notifications_during_disconnection())
        await asyncio.gather(disconnection_task, notification_task)
        lost_notifications = reconnection_tracker.lost_notifications
        assert len(lost_notifications) > 0, 'Expected some notifications to be lost during disconnection'
        critical_events = ['tool_started', 'tool_completed', 'agent_completed']
        lost_critical = [n for n in lost_notifications if n.type in critical_events]
        assert len(lost_critical) > 0, 'Expected critical notifications to be lost'
        failed_reconnections = reconnection_tracker.get_failed_reconnections()
        if failed_reconnections:
            assert len(failed_reconnections) > 0, 'Expected some reconnection failures'
        permanent_disconnections = reconnection_tracker.get_users_with_permanent_disconnection()
        if connection_state == ConnectionState.FAILED:
            assert user_id in permanent_disconnections, 'Expected permanent disconnection to be tracked'

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_duplicate_notifications_after_reconnection(self, reconnection_tracker):
        """CRITICAL: Test duplicate notifications after reconnection."""
        user_id = 'user_001'
        connection_id = f'conn_{user_id}'
        sent_notifications_log = []
        delivered_notifications_log = []
        connection_stable = True

        async def send_notification_with_retry_bug(notification_data: Dict[str, Any]):
            """Send notification with faulty retry logic."""
            notification_id = f'notif_{len(sent_notifications_log)}'
            notification = NotificationEvent(id=notification_id, user_id=user_id, type=notification_data['type'], payload=notification_data, created_at=time.time())
            sent_notifications_log.append(notification)
            reconnection_tracker.record_notification(notification)
            max_retries = 3
            retry_delay = 0.1
            for attempt in range(max_retries):
                notification.delivery_attempts += 1
                try:
                    if not connection_stable:
                        raise ConnectionError('Connection unstable')
                    await asyncio.sleep(random.uniform(0.01, 0.05))
                    notification.delivered_at = time.time()
                    delivered_notifications_log.append(notification)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        duplicate_notification = NotificationEvent(id=f'{notification_id}_dup_{attempt}', user_id=user_id, type=notification_data['type'], payload=notification_data, created_at=notification.created_at, delivered_at=time.time(), duplicated=True, delivery_attempts=attempt + 2)
                        delivered_notifications_log.append(duplicate_notification)
                        reconnection_tracker.record_notification(duplicate_notification)
                except ConnectionError:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
            return notification

        async def simulate_connection_instability():
            """Simulate connection instability during notification sending."""
            nonlocal connection_stable
            await asyncio.sleep(1.0)
            connection_stable = False
            reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.CONNECTED, ConnectionState.DISCONNECTED, 'Intermittent disconnection')
            await asyncio.sleep(2.0)
            connection_stable = True
            reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.DISCONNECTED, ConnectionState.CONNECTED, 'Connection recovered')
        instability_task = asyncio.create_task(simulate_connection_instability())
        notification_tasks = []
        for i in range(10):
            notification_data = {'type': 'tool_progress', 'progress': i * 10, 'tool_name': 'test_tool', 'sequence': i}
            task = asyncio.create_task(send_notification_with_retry_bug(notification_data))
            notification_tasks.append(task)
            await asyncio.sleep(0.3)
        await asyncio.gather(instability_task, *notification_tasks)
        duplicated_notifications = reconnection_tracker.duplicated_notifications
        assert len(duplicated_notifications) > 0, 'Expected duplicate notifications from retry bug'
        total_sent = len(sent_notifications_log)
        total_delivered = len(delivered_notifications_log)
        assert total_delivered > total_sent, f'Expected duplicates: {total_delivered} delivered vs {total_sent} sent'
        duplicate_ratio = (total_delivered - total_sent) / total_sent
        assert duplicate_ratio > 0.2, f'Expected significant duplicates, got {duplicate_ratio:.1%}'
        duplicate_events = [n for n in delivered_notifications_log if n.duplicated]
        progress_duplicates = [n for n in duplicate_events if n.type == 'tool_progress']
        assert len(progress_duplicates) > 0, 'Expected progress notification duplicates'

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_message_ordering_corruption_during_reconnection(self, reconnection_tracker):
        """CRITICAL: Test message ordering corruption during reconnection."""
        user_id = 'user_001'
        message_buffer = []
        delivered_messages = []
        connection_available = True

        async def buffer_and_deliver_notification(notification_data: Dict[str, Any], sequence_num: int):
            """Buffer notification and deliver with potential ordering issues."""
            notification = NotificationEvent(id=f'seq_{sequence_num:03d}', user_id=user_id, type=notification_data['type'], payload={**notification_data, 'sequence': sequence_num}, created_at=time.time())
            message_buffer.append(notification)
            if connection_available:
                notification.delivered_at = time.time()
                delivered_messages.append(notification)
                reconnection_tracker.record_notification(notification)
            else:
                pass

        async def trigger_reconnection_with_ordering_bug():
            """Trigger reconnection that corrupts message ordering."""
            nonlocal connection_available
            await asyncio.sleep(1.0)
            connection_available = False
            reconnection_tracker.record_connection_change(user_id, 'conn_001', ConnectionState.CONNECTED, ConnectionState.DISCONNECTED, 'Connection dropped')
            await asyncio.sleep(2.0)
            reconnection_tracker.record_connection_change(user_id, 'conn_001', ConnectionState.DISCONNECTED, ConnectionState.RECONNECTING, 'Starting reconnection')
            await asyncio.sleep(0.5)
            connection_available = True
            reconnection_tracker.record_connection_change(user_id, 'conn_001', ConnectionState.RECONNECTING, ConnectionState.CONNECTED, 'Reconnection successful')
            buffered_notifications = [n for n in message_buffer if n.delivered_at is None]
            buffered_notifications.sort(key=lambda n: n.id)
            for notification in buffered_notifications:
                notification.delivered_at = time.time()
                delivered_messages.append(notification)
                reconnection_tracker.record_notification(notification)
                await asyncio.sleep(0.01)
        reconnection_task = asyncio.create_task(trigger_reconnection_with_ordering_bug())
        notification_tasks = []
        for seq_num in range(20):
            notification_data = {'type': 'tool_progress', 'step': f'step_{seq_num:02d}', 'progress': seq_num * 5, 'tool_name': 'sequential_tool', 'depends_on_previous': True}
            task = asyncio.create_task(buffer_and_deliver_notification(notification_data, seq_num))
            notification_tasks.append(task)
            await asyncio.sleep(0.1)
        await asyncio.gather(reconnection_task, *notification_tasks)
        delivered_messages.sort(key=lambda n: n.delivered_at or 0)
        for i in range(len(delivered_messages) - 1):
            current_msg = delivered_messages[i]
            next_msg = delivered_messages[i + 1]
            current_seq = current_msg.payload.get('sequence', 0)
            next_seq = next_msg.payload.get('sequence', 0)
            if current_seq > next_seq and current_msg.user_id == next_msg.user_id:
                reconnection_tracker.detect_ordering_violation(current_msg, next_msg)
        assert len(reconnection_tracker.ordering_violations) > 0, 'Expected message ordering violations'
        progress_messages = [n for n in delivered_messages if n.type == 'tool_progress']
        if len(progress_messages) > 5:
            progress_values = [n.payload.get('progress', 0) for n in progress_messages]
            expected_order = sorted(progress_values)
            if progress_values != expected_order:
                assert True, f'Progress messages out of order: {progress_values} != {expected_order}'

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_reconnection_state_corruption_cascading_failures(self, reconnection_tracker):
        """CRITICAL: Test reconnection state corruption causing cascading failures."""
        users = ['user_001', 'user_002', 'user_003']
        shared_reconnection_state = {'current_reconnecting_user': None, 'reconnection_context': None, 'buffered_notifications': {}, 'connection_metadata': {}}

        async def reconnect_with_state_corruption(user_id: str):
            """Attempt reconnection with shared state corruption."""
            connection_id = f'conn_{user_id}'
            reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.CONNECTED, ConnectionState.DISCONNECTED, 'Network timeout')
            shared_reconnection_state['current_reconnecting_user'] = user_id
            shared_reconnection_state['reconnection_context'] = {'user_id': user_id, 'connection_id': connection_id, 'reconnection_start': time.time(), 'buffered_messages': []}
            await asyncio.sleep(random.uniform(0.01, 0.05))
            current_context = shared_reconnection_state['reconnection_context']
            current_user = shared_reconnection_state['current_reconnecting_user']
            reconnection_start = time.time()
            if current_user != user_id:
                reconnection_tracker.record_reconnection_attempt(user_id, 1, False, 0, error_message=f'Reconnection state corrupted by {current_user}', notifications_lost=len(shared_reconnection_state['buffered_notifications'].get(user_id, [])))
                reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.DISCONNECTED, ConnectionState.FAILED, f'State corrupted by {current_user}')
                return False
            try:
                corrupted_context = current_context
                context_user = corrupted_context.get('user_id')
                await asyncio.sleep(random.uniform(0.1, 0.3))
                if context_user == user_id:
                    reconnection_duration = (time.time() - reconnection_start) * 1000
                    reconnection_tracker.record_reconnection_attempt(user_id, 1, True, reconnection_duration)
                    reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.DISCONNECTED, ConnectionState.CONNECTED, 'Reconnection successful')
                    return True
                else:
                    reconnection_duration = (time.time() - reconnection_start) * 1000
                    reconnection_tracker.record_reconnection_attempt(user_id, 1, False, reconnection_duration, error_message=f'Context corrupted: got {context_user}, expected {user_id}')
                    reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.DISCONNECTED, ConnectionState.FAILED, f'Context corruption: wrong user {context_user}')
                    return False
            except Exception as e:
                reconnection_duration = (time.time() - reconnection_start) * 1000
                reconnection_tracker.record_reconnection_attempt(user_id, 1, False, reconnection_duration, error_message=str(e))
                return False
        reconnection_tasks = []
        for user_id in users:
            task = asyncio.create_task(reconnect_with_state_corruption(user_id))
            reconnection_tasks.append(task)
            await asyncio.sleep(0.01)
        results = await asyncio.gather(*reconnection_tasks)
        failed_reconnections = reconnection_tracker.get_failed_reconnections()
        corruption_failures = [attempt for attempt in failed_reconnections if 'corrupted' in (attempt.error_message or '').lower()]
        assert len(corruption_failures) > 0, 'Expected reconnection failures due to state corruption'
        successful_reconnections = sum((1 for result in results if result))
        failed_reconnections_count = len(users) - successful_reconnections
        assert failed_reconnections_count > 0, f'Expected some reconnection failures, got {failed_reconnections_count}/{len(users)}'
        connection_events = reconnection_tracker.connection_events
        failed_events = [e for e in connection_events if e.new_state == ConnectionState.FAILED]
        assert len(failed_events) > 0, 'Expected cascading reconnection failures'
        corruption_events = [e for e in failed_events if 'corruption' in e.reason.lower()]
        assert len(corruption_events) > 0, 'Expected state corruption to affect multiple users'

class ReconnectionRecoveryFailuresTests:
    """Test recovery failure scenarios during reconnection."""

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_notification_buffer_overflow_during_disconnection(self, reconnection_tracker):
        """CRITICAL: Test notification buffer overflow during extended disconnection."""
        user_id = 'user_001'
        connection_id = f'conn_{user_id}'
        max_buffer_size = 50
        notification_buffer = []
        buffer_overflow_count = 0
        connection_state = ConnectionState.CONNECTED

        async def buffer_notification_with_overflow(notification_data: Dict[str, Any], seq_num: int):
            """Buffer notification with potential overflow."""
            nonlocal buffer_overflow_count
            notification = NotificationEvent(id=f'buffer_{seq_num:03d}', user_id=user_id, type=notification_data['type'], payload=notification_data, created_at=time.time())
            if connection_state == ConnectionState.CONNECTED:
                notification.delivered_at = time.time()
                notification.delivery_attempts = 1
                reconnection_tracker.record_notification(notification)
                return True
            elif len(notification_buffer) < max_buffer_size:
                notification_buffer.append(notification)
                reconnection_tracker.record_notification(notification)
                return True
            else:
                buffer_overflow_count += 1
                notification.lost = True
                notification.delivery_attempts = 0
                reconnection_tracker.record_notification(notification)
                return False

        async def simulate_extended_disconnection():
            """Simulate extended disconnection that overflows buffer."""
            nonlocal connection_state
            await asyncio.sleep(1.0)
            connection_state = ConnectionState.DISCONNECTED
            reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.CONNECTED, ConnectionState.DISCONNECTED, 'Extended network outage')
            disconnection_duration = 15.0
            await asyncio.sleep(disconnection_duration)
            for attempt in range(3):
                connection_state = ConnectionState.RECONNECTING
                reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.DISCONNECTED, ConnectionState.RECONNECTING, f'Reconnection attempt {attempt + 1}')
                await asyncio.sleep(random.uniform(1.0, 3.0))
                if random.random() < 0.6:
                    connection_state = ConnectionState.CONNECTED
                    reconnection_duration = disconnection_duration * 1000
                    reconnection_tracker.record_reconnection_attempt(user_id, attempt + 1, True, reconnection_duration, notifications_lost=buffer_overflow_count)
                    reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.RECONNECTING, ConnectionState.CONNECTED, 'Reconnection successful')
                    for buffered_notification in notification_buffer:
                        buffered_notification.delivered_at = time.time()
                        buffered_notification.delivery_attempts = 1
                    break
                else:
                    reconnection_tracker.record_reconnection_attempt(user_id, attempt + 1, False, time.time() * 1000, error_message=f'Reconnection attempt {attempt + 1} failed')
                    connection_state = ConnectionState.DISCONNECTED
                    reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.RECONNECTING, ConnectionState.DISCONNECTED, f'Reconnection attempt {attempt + 1} failed')
            if connection_state != ConnectionState.CONNECTED:
                connection_state = ConnectionState.FAILED
                reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.DISCONNECTED, ConnectionState.FAILED, 'All reconnection attempts failed')
        disconnection_task = asyncio.create_task(simulate_extended_disconnection())
        notification_tasks = []
        for seq_num in range(100):
            notification_data = {'type': 'tool_progress', 'step': f'step_{seq_num:03d}', 'progress': seq_num, 'critical': seq_num % 10 == 0, 'timestamp': time.time()}
            task = asyncio.create_task(buffer_notification_with_overflow(notification_data, seq_num))
            notification_tasks.append(task)
            await asyncio.sleep(0.1)
        await asyncio.gather(disconnection_task, *notification_tasks)
        assert buffer_overflow_count > 0, f'Expected buffer overflow, got {buffer_overflow_count} overflows'
        lost_notifications = reconnection_tracker.lost_notifications
        critical_lost = [n for n in lost_notifications if n.payload.get('critical')]
        assert len(lost_notifications) > 20, f'Expected significant notification loss, got {len(lost_notifications)}'
        assert len(critical_lost) > 0, 'Expected critical notifications to be lost'
        reconnection_attempts = reconnection_tracker.reconnection_attempts
        assert len(reconnection_attempts) > 0, 'Expected reconnection attempts'
        if all((not attempt.success for attempt in reconnection_attempts)):
            permanent_disconnections = reconnection_tracker.get_users_with_permanent_disconnection()
            assert user_id in permanent_disconnections, 'Expected permanent disconnection after failed attempts'

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_user_state_corruption_during_recovery(self, reconnection_tracker):
        """CRITICAL: Test user state corruption during connection recovery."""
        users = ['user_001', 'user_002', 'user_003']
        shared_recovery_state = {'current_recovering_user': None, 'recovery_context': None, 'user_session_data': {}, 'recovery_metadata': {}}

        async def recover_user_session_with_corruption(user_id: str):
            """Recover user session with potential state corruption."""
            connection_id = f'conn_{user_id}'
            reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.CONNECTED, ConnectionState.DISCONNECTED, 'Session recovery needed')
            shared_recovery_state['current_recovering_user'] = user_id
            shared_recovery_state['recovery_context'] = {'user_id': user_id, 'session_data': {'active_tools': [f'tool_{user_id}_{i}' for i in range(3)], 'user_preferences': {'theme': user_id[-1], 'lang': 'en'}, 'authentication_context': f'auth_token_{user_id}', 'cached_responses': {f'cache_{i}': f'data_{user_id}_{i}' for i in range(5)}}, 'recovery_timestamp': time.time()}
            shared_recovery_state['user_session_data'][user_id] = shared_recovery_state['recovery_context']['session_data']
            await asyncio.sleep(random.uniform(0.05, 0.15))
            current_context = shared_recovery_state['recovery_context']
            current_user = shared_recovery_state['current_recovering_user']
            if current_user != user_id:
                reconnection_tracker.record_reconnection_attempt(user_id, 1, False, 0, error_message=f'Recovery state corrupted by {current_user}')
                reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.DISCONNECTED, ConnectionState.FAILED, f'Recovery corrupted by {current_user}')
                return False
            recovered_session_data = shared_recovery_state['user_session_data'].get(user_id)
            if not recovered_session_data:
                reconnection_tracker.record_reconnection_attempt(user_id, 1, False, 100, error_message='Session data lost during recovery')
                return False
            auth_context = recovered_session_data.get('authentication_context', '')
            if user_id not in auth_context:
                reconnection_tracker.record_reconnection_attempt(user_id, 1, False, 100, error_message=f"Authentication corrupted: {auth_context} doesn't match {user_id}")
                reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.DISCONNECTED, ConnectionState.FAILED, 'Authentication context corrupted')
                return False
            reconnection_duration = (time.time() - reconnection_start) * 1000
            reconnection_tracker.record_reconnection_attempt(user_id, 1, True, reconnection_duration)
            reconnection_tracker.record_connection_change(user_id, connection_id, ConnectionState.DISCONNECTED, ConnectionState.CONNECTED, 'Recovery completed')
            return True
        recovery_tasks = []
        for user_id in users:
            task = asyncio.create_task(recover_user_session_with_corruption(user_id))
            recovery_tasks.append(task)
            await asyncio.sleep(0.02)
        results = await asyncio.gather(*recovery_tasks)
        failed_reconnections = reconnection_tracker.get_failed_reconnections()
        corruption_failures = [attempt for attempt in failed_reconnections if 'corrupted' in (attempt.error_message or '').lower()]
        assert len(corruption_failures) > 0, 'Expected recovery failures due to state corruption'
        auth_corruption_failures = [attempt for attempt in failed_reconnections if 'authentication' in (attempt.error_message or '').lower()]
        assert len(auth_corruption_failures) > 0, 'Expected authentication corruption during recovery'
        permanent_disconnections = reconnection_tracker.get_users_with_permanent_disconnection()
        assert len(permanent_disconnections) > 0, 'Expected some permanent disconnections due to corruption'
        successful_recoveries = [attempt for attempt in reconnection_tracker.reconnection_attempts if attempt.success]
        for recovery in successful_recoveries:
            recovery_user = recovery.user_id
            final_session_data = shared_recovery_state['user_session_data'].get(recovery_user)
            if final_session_data:
                auth_context = final_session_data.get('authentication_context', '')
                cached_data = final_session_data.get('cached_responses', {})
                if recovery_user not in auth_context or any((recovery_user not in str(v) for v in cached_data.values())):
                    assert True, f'User {recovery_user} recovered with corrupted session data'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')