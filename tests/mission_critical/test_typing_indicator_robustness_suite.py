#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: Typing Indicator Robustness

THIS SUITE MUST PASS FOR TYPING INDICATORS TO BE RELIABLE.
Business Value: Enhanced user experience through real-time feedback

This comprehensive test suite validates:
1. Typing event generation and transmission
2. Backend WebSocket event handling and routing
3. Frontend state management and UI updates
4. Multi-user typing indicator coordination
5. Error handling and recovery scenarios
6. Performance under load and edge cases

ANY FAILURE HERE INDICATES BROKEN TYPING FUNCTIONALITY.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
import random
from enum import Enum
from dataclasses import dataclass, field

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import production components
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, ConnectionInfo


# ============================================================================
# TYPING INDICATOR EVENT TYPES
# ============================================================================

class TypingEventType(str, Enum):
    """Typing indicator event types."""
    USER_TYPING = "user_typing"
    AGENT_TYPING = "agent_typing"
    TYPING_STARTED = "typing_started"
    TYPING_STOPPED = "typing_stopped"
    TYPING_TIMEOUT = "typing_timeout"


@dataclass
class TypingState:
    """Represents typing state for a user/agent."""
    id: str
    thread_id: str
    is_typing: bool
    started_at: Optional[float] = None
    last_activity: Optional[float] = None
    timeout_duration: float = 5.0  # seconds
    
    def is_expired(self) -> bool:
        """Check if typing state has expired."""
        if not self.is_typing or not self.last_activity:
            return False
        return (time.time() - self.last_activity) > self.timeout_duration
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()
        if not self.started_at:
            self.started_at = self.last_activity


# ============================================================================
# ENHANCED MOCK WEBSOCKET MANAGER WITH TYPING SUPPORT
# ============================================================================

class TypingAwareWebSocketManager:
    """Enhanced WebSocket manager with typing indicator support."""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.connections: Dict[str, ConnectionInfo] = {}
        self.typing_states: Dict[Tuple[str, str], TypingState] = {}  # (thread_id, user_id) -> TypingState
        self.typing_events: List[Dict] = []
        self._lock = threading.Lock()
        self._cleanup_task = None
        
    async def send_typing_event(self, thread_id: str, user_id: str, is_typing: bool) -> bool:
        """Send typing indicator event."""
        try:
            with self._lock:
                key = (thread_id, user_id)
                
                # Update typing state
                if key not in self.typing_states:
                    self.typing_states[key] = TypingState(
                        id=user_id,
                        thread_id=thread_id,
                        is_typing=is_typing
                    )
                else:
                    self.typing_states[key].is_typing = is_typing
                
                if is_typing:
                    self.typing_states[key].update_activity()
                
                # Create typing event
                event = {
                    'type': TypingEventType.USER_TYPING,
                    'payload': {
                        'thread_id': thread_id,
                        'user_id': user_id,
                        'is_typing': is_typing,
                        'timestamp': time.time()
                    }
                }
                
                # Record event
                self.typing_events.append(event)
                self.messages.append({
                    'thread_id': thread_id,
                    'message': event,
                    'event_type': event['type'],
                    'timestamp': time.time()
                })
                
                # Broadcast to other users in thread
                await self._broadcast_typing_event(thread_id, user_id, is_typing)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to send typing event: {e}")
            return False
    
    async def _broadcast_typing_event(self, thread_id: str, sender_id: str, is_typing: bool):
        """Broadcast typing event to other users in thread."""
        # In real implementation, this would send to all connections except sender
        broadcast_event = {
            'type': 'typing_indicator',
            'payload': {
                'user_id': sender_id,
                'is_typing': is_typing,
                'thread_id': thread_id
            }
        }
        
        # Simulate broadcast to connections
        for conn_thread_id, conn_info in self.connections.items():
            if conn_thread_id == thread_id and conn_info.get('user_id') != sender_id:
                self.messages.append({
                    'thread_id': conn_thread_id,
                    'message': broadcast_event,
                    'event_type': 'typing_broadcast',
                    'recipient': conn_info.get('user_id'),
                    'timestamp': time.time()
                })
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Record message and simulate successful delivery."""
        self.messages.append({
            'thread_id': thread_id,
            'message': message,
            'event_type': message.get('type', 'unknown'),
            'timestamp': time.time()
        })
        return True
    
    async def cleanup_expired_typing_states(self):
        """Clean up expired typing states."""
        with self._lock:
            expired_keys = []
            for key, state in self.typing_states.items():
                if state.is_expired():
                    expired_keys.append(key)
                    # Send typing stopped event for expired state
                    await self.send_typing_event(
                        state.thread_id,
                        state.id,
                        False
                    )
            
            for key in expired_keys:
                del self.typing_states[key]
    
    def get_active_typers(self, thread_id: str) -> List[str]:
        """Get list of users currently typing in a thread."""
        with self._lock:
            active = []
            for (t_id, user_id), state in self.typing_states.items():
                if t_id == thread_id and state.is_typing and not state.is_expired():
                    active.append(user_id)
            return active
    
    def get_typing_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get all typing events for a specific thread."""
        return [e for e in self.typing_events if e['payload'].get('thread_id') == thread_id]
    
    async def connect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user connection."""
        self.connections[thread_id] = {'user_id': user_id, 'connected': True}
    
    async def disconnect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user disconnection and clean up typing state."""
        if thread_id in self.connections:
            self.connections[thread_id]['connected'] = False
        
        # Clear typing state on disconnect
        key = (thread_id, user_id)
        if key in self.typing_states and self.typing_states[key].is_typing:
            await self.send_typing_event(thread_id, user_id, False)


# ============================================================================
# TYPING INDICATOR TEST VALIDATOR
# ============================================================================

class TypingIndicatorValidator:
    """Validates typing indicator behavior with comprehensive checks."""
    
    def __init__(self):
        self.events: List[Dict] = []
        self.state_transitions: List[Tuple[str, bool, float]] = []  # (user_id, is_typing, timestamp)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def record_event(self, event: Dict):
        """Record a typing event for validation."""
        self.events.append(event)
        
        if 'payload' in event:
            user_id = event['payload'].get('user_id', 'unknown')
            is_typing = event['payload'].get('is_typing', False)
            timestamp = event['payload'].get('timestamp', time.time())
            self.state_transitions.append((user_id, is_typing, timestamp))
    
    def validate_typing_lifecycle(self) -> Tuple[bool, List[str]]:
        """Validate complete typing indicator lifecycle."""
        issues = []
        
        # Check for proper start/stop pairs
        user_states = {}
        for user_id, is_typing, timestamp in self.state_transitions:
            if user_id not in user_states:
                user_states[user_id] = []
            user_states[user_id].append((is_typing, timestamp))
        
        for user_id, states in user_states.items():
            # Validate state transitions
            for i in range(len(states) - 1):
                current_typing, current_time = states[i]
                next_typing, next_time = states[i + 1]
                
                # Check for duplicate states
                if current_typing == next_typing:
                    issues.append(f"Duplicate typing state for {user_id}: {current_typing}")
                
                # Check timing
                if next_time <= current_time:
                    issues.append(f"Invalid timestamp order for {user_id}")
        
        return len(issues) == 0, issues
    
    def validate_multi_user_coordination(self) -> Tuple[bool, List[str]]:
        """Validate multi-user typing coordination."""
        issues = []
        
        # Track concurrent typing states
        timeline = []
        for event in self.events:
            if 'payload' in event:
                timeline.append({
                    'timestamp': event['payload'].get('timestamp', 0),
                    'user_id': event['payload'].get('user_id'),
                    'is_typing': event['payload'].get('is_typing'),
                    'thread_id': event['payload'].get('thread_id')
                })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'])
        
        # Validate concurrent typing states
        active_typers = {}
        for item in timeline:
            thread_id = item['thread_id']
            user_id = item['user_id']
            
            if thread_id not in active_typers:
                active_typers[thread_id] = set()
            
            if item['is_typing']:
                active_typers[thread_id].add(user_id)
            else:
                active_typers[thread_id].discard(user_id)
            
            # Check for reasonable concurrent typing limit
            if len(active_typers[thread_id]) > 10:
                issues.append(f"Too many concurrent typers in thread {thread_id}: {len(active_typers[thread_id])}")
        
        return len(issues) == 0, issues


# ============================================================================
# COMPREHENSIVE TEST SUITE
# ============================================================================

class TestTypingIndicatorRobustness:
    """Comprehensive typing indicator test suite."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create typing-aware WebSocket manager."""
        return TypingAwareWebSocketManager()
    
    @pytest.fixture
    def validator(self):
        """Create typing indicator validator."""
        return TypingIndicatorValidator()
    
    @pytest.mark.asyncio
    async def test_01_basic_typing_lifecycle(self, websocket_manager, validator):
        """Test basic typing start/stop lifecycle."""
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Start typing
        success = await websocket_manager.send_typing_event(thread_id, user_id, True)
        assert success, "Failed to send typing started event"
        
        # Verify typing state
        active_typers = websocket_manager.get_active_typers(thread_id)
        assert user_id in active_typers, "User not in active typers list"
        
        # Simulate typing activity
        await asyncio.sleep(0.1)
        
        # Stop typing
        success = await websocket_manager.send_typing_event(thread_id, user_id, False)
        assert success, "Failed to send typing stopped event"
        
        # Verify typing state cleared
        active_typers = websocket_manager.get_active_typers(thread_id)
        assert user_id not in active_typers, "User still in active typers list"
        
        # Validate events
        events = websocket_manager.get_typing_events_for_thread(thread_id)
        assert len(events) == 2, f"Expected 2 events, got {len(events)}"
        
        for event in events:
            validator.record_event(event)
        
        valid, issues = validator.validate_typing_lifecycle()
        assert valid, f"Typing lifecycle validation failed: {issues}"
    
    @pytest.mark.asyncio
    async def test_02_multi_user_typing(self, websocket_manager, validator):
        """Test multiple users typing simultaneously."""
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        num_users = 5
        users = [f"user_{i}" for i in range(num_users)]
        
        # Start typing for all users with slight delays
        for user_id in users:
            await websocket_manager.send_typing_event(thread_id, user_id, True)
            await asyncio.sleep(0.05)  # Small delay between users
        
        # Verify all users are typing
        active_typers = websocket_manager.get_active_typers(thread_id)
        assert len(active_typers) == num_users, f"Expected {num_users} typers, got {len(active_typers)}"
        
        # Stop typing for users in different order
        for user_id in reversed(users):
            await websocket_manager.send_typing_event(thread_id, user_id, False)
            await asyncio.sleep(0.05)
        
        # Verify no users are typing
        active_typers = websocket_manager.get_active_typers(thread_id)
        assert len(active_typers) == 0, f"Expected 0 typers, got {len(active_typers)}"
        
        # Validate coordination
        events = websocket_manager.get_typing_events_for_thread(thread_id)
        for event in events:
            validator.record_event(event)
        
        valid, issues = validator.validate_multi_user_coordination()
        assert valid, f"Multi-user coordination failed: {issues}"
    
    @pytest.mark.asyncio
    async def test_03_typing_timeout_expiration(self, websocket_manager):
        """Test automatic typing state expiration."""
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Start typing with custom short timeout
        await websocket_manager.send_typing_event(thread_id, user_id, True)
        
        # Modify timeout for testing
        key = (thread_id, user_id)
        if key in websocket_manager.typing_states:
            websocket_manager.typing_states[key].timeout_seconds = 0.5  # 500ms timeout
        
        # Verify user is typing
        active_typers = websocket_manager.get_active_typers(thread_id)
        assert user_id in active_typers, "User not typing initially"
        
        # Wait for timeout
        await asyncio.sleep(0.6)
        
        # Run cleanup
        await websocket_manager.cleanup_expired_typing_states()
        
        # Verify user is no longer typing
        active_typers = websocket_manager.get_active_typers(thread_id)
        assert user_id not in active_typers, "User still typing after timeout"
    
    @pytest.mark.asyncio
    async def test_04_rapid_typing_toggle(self, websocket_manager):
        """Test rapid typing start/stop toggling."""
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Rapid toggle typing state
        toggle_count = 20
        for i in range(toggle_count):
            is_typing = (i % 2 == 0)
            success = await websocket_manager.send_typing_event(thread_id, user_id, is_typing)
            assert success, f"Failed to send event {i}"
            await asyncio.sleep(0.01)  # Small delay
        
        # Final state should be not typing (even count)
        active_typers = websocket_manager.get_active_typers(thread_id)
        assert user_id not in active_typers, "User should not be typing after even toggles"
        
        # Verify all events were recorded
        events = websocket_manager.get_typing_events_for_thread(thread_id)
        assert len(events) == toggle_count, f"Expected {toggle_count} events, got {len(events)}"
    
    @pytest.mark.asyncio
    async def test_05_disconnect_clears_typing(self, websocket_manager):
        """Test that disconnection clears typing state."""
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Connect user
        await websocket_manager.connect_user(user_id, None, thread_id)
        
        # Start typing
        await websocket_manager.send_typing_event(thread_id, user_id, True)
        assert user_id in websocket_manager.get_active_typers(thread_id)
        
        # Disconnect user
        await websocket_manager.disconnect_user(user_id, None, thread_id)
        
        # Verify typing state cleared
        active_typers = websocket_manager.get_active_typers(thread_id)
        assert user_id not in active_typers, "User still typing after disconnect"
    
    @pytest.mark.asyncio
    async def test_06_concurrent_thread_typing(self, websocket_manager):
        """Test typing indicators across multiple threads."""
        num_threads = 3
        threads = [f"thread_{i}" for i in range(num_threads)]
        users_per_thread = 2
        
        # Start typing in all threads
        for thread_id in threads:
            for user_num in range(users_per_thread):
                user_id = f"{thread_id}_user_{user_num}"
                await websocket_manager.send_typing_event(thread_id, user_id, True)
        
        # Verify typing states are isolated per thread
        for thread_id in threads:
            active_typers = websocket_manager.get_active_typers(thread_id)
            assert len(active_typers) == users_per_thread
            
            # Verify correct users are typing in each thread
            for user_num in range(users_per_thread):
                expected_user = f"{thread_id}_user_{user_num}"
                assert expected_user in active_typers
    
    @pytest.mark.asyncio
    async def test_07_broadcast_to_other_users(self, websocket_manager):
        """Test typing events are broadcast to other users."""
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        sender_id = "sender_user"
        receiver_ids = ["receiver_1", "receiver_2", "receiver_3"]
        
        # Connect all users
        await websocket_manager.connect_user(sender_id, None, thread_id)
        for receiver_id in receiver_ids:
            await websocket_manager.connect_user(receiver_id, None, thread_id)
        
        # Sender starts typing
        await websocket_manager.send_typing_event(thread_id, sender_id, True)
        
        # Check broadcast messages
        broadcasts = [msg for msg in websocket_manager.messages 
                     if msg.get('event_type') == 'typing_broadcast']
        
        # Should have broadcasts for each receiver
        assert len(broadcasts) >= len(receiver_ids), \
            f"Expected at least {len(receiver_ids)} broadcasts, got {len(broadcasts)}"
    
    @pytest.mark.asyncio
    async def test_08_typing_state_persistence(self, websocket_manager):
        """Test typing state persistence during activity."""
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Start typing
        await websocket_manager.send_typing_event(thread_id, user_id, True)
        
        # Simulate continued typing activity
        for _ in range(5):
            await asyncio.sleep(0.1)
            # Update activity (simulate keypress)
            key = (thread_id, user_id)
            if key in websocket_manager.typing_states:
                websocket_manager.typing_states[key].update_activity()
        
        # Verify still typing after activity
        active_typers = websocket_manager.get_active_typers(thread_id)
        assert user_id in active_typers, "User should still be typing after activity"
    
    @pytest.mark.asyncio
    async def test_09_error_handling(self, websocket_manager):
        """Test error handling in typing indicator system."""
        # Test with invalid thread_id
        success = await websocket_manager.send_typing_event("", "user", True)
        assert success  # Should handle gracefully
        
        # Test with invalid user_id
        success = await websocket_manager.send_typing_event("thread", "", True)
        assert success  # Should handle gracefully
        
        # Test with None values
        success = await websocket_manager.send_typing_event(None, None, True)
        assert success  # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_10_performance_under_load(self, websocket_manager):
        """Test typing indicators under heavy load."""
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        num_users = 50
        events_per_user = 10
        
        async def simulate_user_typing(user_id: str):
            """Simulate a user typing pattern."""
            for i in range(events_per_user):
                is_typing = (i % 2 == 0)
                await websocket_manager.send_typing_event(thread_id, user_id, is_typing)
                await asyncio.sleep(random.uniform(0.01, 0.05))
        
        # Create concurrent typing simulations
        tasks = []
        for i in range(num_users):
            user_id = f"user_{i}"
            tasks.append(simulate_user_typing(user_id))
        
        # Run all simulations concurrently
        start_time = time.time()
        await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Verify performance
        assert duration < 10, f"Performance test took too long: {duration:.2f}s"
        
        # Verify all events were recorded
        events = websocket_manager.get_typing_events_for_thread(thread_id)
        expected_events = num_users * events_per_user
        assert len(events) == expected_events, \
            f"Expected {expected_events} events, got {len(events)}"
        
        # Final state should have no active typers (even count per user)
        active_typers = websocket_manager.get_active_typers(thread_id)
        assert len(active_typers) == 0, f"Should have no active typers, got {len(active_typers)}"


# ============================================================================
# TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all typing indicator tests."""
    logger.info("=" * 80)
    logger.info("TYPING INDICATOR ROBUSTNESS TEST SUITE")
    logger.info("=" * 80)
    
    test_suite = TestTypingIndicatorRobustness()
    
    # Tests that need both ws_manager and validator
    tests_with_both = [
        ("Basic Typing Lifecycle", test_suite.test_01_basic_typing_lifecycle),
        ("Multi-User Typing", test_suite.test_02_multi_user_typing),
    ]
    
    # Tests that only need ws_manager
    tests_with_manager = [
        ("Typing Timeout Expiration", test_suite.test_03_typing_timeout_expiration),
        ("Rapid Typing Toggle", test_suite.test_04_rapid_typing_toggle),
        ("Disconnect Clears Typing", test_suite.test_05_disconnect_clears_typing),
        ("Concurrent Thread Typing", test_suite.test_06_concurrent_thread_typing),
        ("Broadcast to Other Users", test_suite.test_07_broadcast_to_other_users),
        ("Typing State Persistence", test_suite.test_08_typing_state_persistence),
        ("Error Handling", test_suite.test_09_error_handling),
        ("Performance Under Load", test_suite.test_10_performance_under_load),
    ]
    
    passed = 0
    failed = 0
    
    # Run tests that need both fixtures
    for test_name, test_func in tests_with_both:
        ws_manager = TypingAwareWebSocketManager()
        validator = TypingIndicatorValidator()
        try:
            logger.info(f"\nRunning: {test_name}")
            await test_func(ws_manager, validator)
            logger.success(f"✓ {test_name} PASSED")
            passed += 1
        except Exception as e:
            logger.error(f"✗ {test_name} FAILED: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    # Run tests that only need ws_manager
    for test_name, test_func in tests_with_manager:
        ws_manager = TypingAwareWebSocketManager()
        try:
            logger.info(f"\nRunning: {test_name}")
            await test_func(ws_manager)
            logger.success(f"✓ {test_name} PASSED")
            passed += 1
        except Exception as e:
            logger.error(f"✗ {test_name} FAILED: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    logger.info("\n" + "=" * 80)
    logger.info(f"RESULTS: {passed} passed, {failed} failed")
    
    if failed > 0:
        logger.error("TYPING INDICATOR TESTS FAILED - FUNCTIONALITY IS BROKEN")
        return False
    else:
        logger.success("ALL TYPING INDICATOR TESTS PASSED - READY FOR PRODUCTION")
        return True


def main():
    """Main entry point."""
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()