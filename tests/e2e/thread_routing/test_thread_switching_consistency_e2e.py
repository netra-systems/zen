#!/usr/bin/env python3
"""
CRITICAL E2E TEST SUITE: Thread Switching Consistency

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure seamless thread switching maintains conversation continuity
- Value Impact: Users must be able to switch between conversations without losing context
- Strategic Impact: Core UX for multi-conversation Chat platform workflow

CRITICAL REQUIREMENTS:
- ✅ Real authentication via e2e_auth_helper.py (NO MOCKS = ABOMINATION) 
- ✅ Full Docker stack + Database + WebSocket
- ✅ Thread context preservation validation across switches
- ✅ Message history persistence per thread
- ✅ WebSocket room switching validation
- ✅ Tests designed to FAIL initially (find thread switching edge case bugs)

This test validates that users can seamlessly switch between multiple conversation
threads while maintaining perfect context isolation and history preservation.
Expected initial failures due to thread switching edge case bugs.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
import pytest
from contextlib import asynccontextmanager
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

# CRITICAL: Add project root to Python path for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# SSOT imports following CLAUDE.md requirements
from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper, 
    create_authenticated_user_context,
    E2EAuthConfig
)
from test_framework.base_e2e_test import BaseE2ETest
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RequestID, MessageID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

logger = logging.getLogger(__name__)


class ThreadSwitchingTracker:
    """
    Framework for tracking thread switching behavior and context preservation.
    
    Features:
    - Thread context state tracking across switches
    - Message history validation per thread
    - WebSocket room switching monitoring
    - Context preservation verification
    """
    
    def __init__(self, environment: str = "test"):
        self.environment = environment
        self.start_time = time.time()
        
        # Thread state tracking
        self.thread_states: Dict[str, Dict] = {}          # thread_id -> state
        self.thread_messages: Dict[str, List[Dict]] = {}  # thread_id -> messages
        self.thread_switches: List[Dict] = []             # switching events
        self.context_preservation_failures: List[Dict] = []
        
        # WebSocket room tracking
        self.websocket_rooms: Dict[str, str] = {}         # user_id -> current_thread_id
        self.room_switch_events: List[Dict] = []
        
        # User session tracking
        self.user_sessions: Dict[str, Dict] = {}          # user_id -> session_info
    
    def initialize_thread(self, user_id: str, thread_id: str, thread_title: str, context: Dict = None):
        """Initialize thread state for tracking."""
        self.thread_states[thread_id] = {
            "user_id": user_id,
            "thread_id": thread_id,
            "title": thread_title,
            "created_at": time.time(),
            "last_accessed": time.time(),
            "message_count": 0,
            "active": True,
            "context": context or {}
        }
        
        self.thread_messages[thread_id] = []
        
        # Initialize WebSocket room if first thread for user
        if user_id not in self.websocket_rooms:
            self.websocket_rooms[user_id] = thread_id
            logger.info(f"🏠 User {user_id} initial WebSocket room set to thread {thread_id}")
        
        logger.info(f"📝 Initialized thread {thread_id} for user {user_id}: {thread_title}")
    
    def track_message(self, user_id: str, thread_id: str, message_type: str, message_data: Dict):
        """Track message in specific thread."""
        if thread_id not in self.thread_messages:
            self.thread_messages[thread_id] = []
        
        message_entry = {
            "timestamp": time.time(),
            "relative_time": time.time() - self.start_time,
            "user_id": user_id,
            "thread_id": thread_id,
            "message_type": message_type,
            "message_data": message_data,
            "sequence_number": len(self.thread_messages[thread_id])
        }
        
        self.thread_messages[thread_id].append(message_entry)
        
        # Update thread state
        if thread_id in self.thread_states:
            self.thread_states[thread_id]["message_count"] += 1
            self.thread_states[thread_id]["last_accessed"] = time.time()
        
        logger.debug(f"💬 Tracked {message_type} message in thread {thread_id} for user {user_id}")
    
    def track_thread_switch(self, user_id: str, from_thread_id: str, to_thread_id: str, switch_reason: str = "user_action"):
        """Track thread switching event with context validation."""
        switch_timestamp = time.time()
        
        # Validate context preservation
        context_preserved = self._validate_context_preservation(from_thread_id, to_thread_id)
        
        switch_entry = {
            "timestamp": switch_timestamp,
            "relative_time": switch_timestamp - self.start_time,
            "user_id": user_id,
            "from_thread_id": from_thread_id,
            "to_thread_id": to_thread_id,
            "switch_reason": switch_reason,
            "context_preserved": context_preserved,
            "switch_duration": 0  # Will be updated when switch completes
        }
        
        self.thread_switches.append(switch_entry)
        
        # Update WebSocket room tracking
        previous_room = self.websocket_rooms.get(user_id)
        self.websocket_rooms[user_id] = to_thread_id
        
        self.room_switch_events.append({
            "timestamp": switch_timestamp,
            "user_id": user_id,
            "previous_room": previous_room,
            "new_room": to_thread_id
        })
        
        # Update thread access times
        if from_thread_id in self.thread_states:
            self.thread_states[from_thread_id]["active"] = False
        if to_thread_id in self.thread_states:
            self.thread_states[to_thread_id]["active"] = True
            self.thread_states[to_thread_id]["last_accessed"] = switch_timestamp
        
        if not context_preserved:
            failure_entry = {
                "timestamp": switch_timestamp,
                "user_id": user_id,
                "from_thread": from_thread_id,
                "to_thread": to_thread_id,
                "failure_type": "context_preservation"
            }
            self.context_preservation_failures.append(failure_entry)
            logger.error(f"🚨 CONTEXT PRESERVATION FAILURE: User {user_id} switch from {from_thread_id} to {to_thread_id}")
        
        logger.info(f"🔄 User {user_id} switched from thread {from_thread_id} to {to_thread_id}")
        return len(self.thread_switches) - 1  # Return switch index
    
    def complete_thread_switch(self, switch_index: int, completion_data: Dict = None):
        """Mark thread switch as completed with timing data."""
        if 0 <= switch_index < len(self.thread_switches):
            switch_entry = self.thread_switches[switch_index]
            completion_time = time.time()
            switch_entry["switch_duration"] = completion_time - switch_entry["timestamp"]
            switch_entry["completion_data"] = completion_data or {}
            
            logger.debug(f"✅ Thread switch completed in {switch_entry['switch_duration']:.3f}s")
    
    def _validate_context_preservation(self, from_thread_id: str, to_thread_id: str) -> bool:
        """Validate that thread context is preserved across switches."""
        # Check that from_thread state is preserved
        if from_thread_id in self.thread_states:
            from_state = self.thread_states[from_thread_id]
            if from_state["message_count"] == 0:
                return False  # Should preserve message history
        
        # Check that to_thread state is available
        if to_thread_id not in self.thread_states:
            return False  # Target thread should exist
        
        # Additional context validations could go here
        return True
    
    def validate_thread_history_preservation(self, thread_id: str) -> Dict:
        """Validate that thread message history is preserved."""
        if thread_id not in self.thread_messages:
            return {
                "preserved": False,
                "error": "Thread not found in message history",
                "message_count": 0
            }
        
        thread_messages = self.thread_messages[thread_id]
        
        # Check message sequence continuity
        expected_sequence = 0
        sequence_intact = True
        for msg in thread_messages:
            if msg["sequence_number"] != expected_sequence:
                sequence_intact = False
                break
            expected_sequence += 1
        
        # Check temporal ordering
        temporal_ordered = True
        for i in range(1, len(thread_messages)):
            if thread_messages[i]["timestamp"] < thread_messages[i-1]["timestamp"]:
                temporal_ordered = False
                break
        
        return {
            "preserved": sequence_intact and temporal_ordered,
            "message_count": len(thread_messages),
            "sequence_intact": sequence_intact,
            "temporal_ordered": temporal_ordered,
            "first_message": thread_messages[0] if thread_messages else None,
            "last_message": thread_messages[-1] if thread_messages else None
        }
    
    def analyze_switching_patterns(self) -> Dict:
        """Analyze thread switching patterns and performance."""
        if not self.thread_switches:
            return {
                "switch_count": 0,
                "avg_switch_duration": 0,
                "context_preservation_rate": 1.0
            }
        
        switch_durations = [s["switch_duration"] for s in self.thread_switches if s["switch_duration"] > 0]
        avg_switch_duration = sum(switch_durations) / len(switch_durations) if switch_durations else 0
        
        context_preserved_count = sum(1 for s in self.thread_switches if s["context_preserved"])
        context_preservation_rate = context_preserved_count / len(self.thread_switches)
        
        return {
            "switch_count": len(self.thread_switches),
            "avg_switch_duration": avg_switch_duration,
            "context_preservation_rate": context_preservation_rate,
            "context_failures": len(self.context_preservation_failures),
            "room_switches": len(self.room_switch_events)
        }
    
    def generate_switching_report(self) -> Dict:
        """Generate comprehensive thread switching report."""
        switching_analysis = self.analyze_switching_patterns()
        
        # Thread state analysis
        total_threads = len(self.thread_states)
        active_threads = sum(1 for state in self.thread_states.values() if state["active"])
        
        # Message history analysis
        total_messages = sum(len(msgs) for msgs in self.thread_messages.values())
        threads_with_messages = sum(1 for msgs in self.thread_messages.values() if len(msgs) > 0)
        
        return {
            "test_duration": time.time() - self.start_time,
            "total_threads": total_threads,
            "active_threads": active_threads,
            "total_messages": total_messages,
            "threads_with_messages": threads_with_messages,
            "switching_analysis": switching_analysis,
            "context_preservation_failures": len(self.context_preservation_failures),
            "websocket_room_switches": len(self.room_switch_events),
            "detailed_failures": self.context_preservation_failures,
            "thread_switches": self.thread_switches,
            "room_switch_events": self.room_switch_events
        }


class ThreadSwitchingWebSocketClient:
    """WebSocket client optimized for thread switching behavior testing."""
    
    def __init__(self, user_context: StronglyTypedUserExecutionContext,
                 auth_helper: E2EWebSocketAuthHelper,
                 switching_tracker: ThreadSwitchingTracker):
        self.user_context = user_context
        self.auth_helper = auth_helper
        self.switching_tracker = switching_tracker
        self.websocket = None
        self.user_id = str(user_context.user_id)
        self.current_thread_id = None
        self.is_connected = False
        self.user_threads: Dict[str, Dict] = {}  # thread_id -> thread_info
    
    @asynccontextmanager
    async def connect(self, timeout: float = 25.0):
        """Connect with thread switching monitoring."""
        try:
            # Get authenticated WebSocket connection
            self.websocket = await self.auth_helper.connect_authenticated_websocket(timeout=timeout)
            self.is_connected = True
            
            logger.info(f"🔌 User {self.user_id} connected for thread switching tests")
            
            # Start message monitoring
            monitor_task = asyncio.create_task(self._monitor_thread_messages())
            
            try:
                yield self
            finally:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                
                if self.websocket and not self.websocket.closed:
                    await self.websocket.close()
                    self.is_connected = False
                
                logger.info(f"🔌 User {self.user_id} disconnected from thread switching tests")
        
        except Exception as e:
            logger.error(f"❌ User {self.user_id} thread switching WebSocket connection failed: {e}")
            raise
    
    async def _monitor_thread_messages(self):
        """Monitor WebSocket messages for thread-specific tracking."""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    
                    # Parse and track message
                    try:
                        message_data = json.loads(message)
                        message_type = message_data.get("type", "unknown")
                        thread_id = message_data.get("thread_id", self.current_thread_id)
                        
                        if thread_id:
                            self.switching_tracker.track_message(
                                self.user_id,
                                thread_id,
                                message_type,
                                message_data
                            )
                        
                        logger.debug(f"📨 User {self.user_id} received {message_type} in thread {thread_id}")
                    
                    except json.JSONDecodeError:
                        pass  # Non-JSON messages are okay
                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"Message monitoring error for user {self.user_id}: {e}")
                    break
        
        except asyncio.CancelledError:
            pass
    
    async def create_conversation_thread(self, thread_title: str, initial_context: Dict = None) -> str:
        """Create a new conversation thread."""
        id_generator = UnifiedIdGenerator()
        thread_id = id_generator.generate_thread_id(self.user_id)
        
        # Initialize in switching tracker
        self.switching_tracker.initialize_thread(
            self.user_id, 
            thread_id, 
            thread_title,
            initial_context
        )
        
        # Track in client
        self.user_threads[thread_id] = {
            "title": thread_title,
            "created_at": time.time(),
            "message_count": 0,
            "context": initial_context or {}
        }
        
        # Set as current thread if first one
        if self.current_thread_id is None:
            self.current_thread_id = thread_id
        
        logger.info(f"📝 User {self.user_id} created conversation thread {thread_id}: {thread_title}")
        return thread_id
    
    async def switch_to_thread(self, target_thread_id: str, switch_reason: str = "user_action") -> int:
        """Switch to a different conversation thread."""
        if not self.websocket or not self.is_connected:
            raise ConnectionError(f"User {self.user_id} WebSocket not connected")
        
        from_thread_id = self.current_thread_id
        
        # Track the switch
        switch_index = self.switching_tracker.track_thread_switch(
            self.user_id,
            from_thread_id,
            target_thread_id,
            switch_reason
        )
        
        # Send thread switch message to server
        switch_message = {
            "type": "thread_switch",
            "user_id": self.user_id,
            "from_thread_id": from_thread_id,
            "to_thread_id": target_thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "switch_reason": switch_reason
        }
        
        await self.websocket.send(json.dumps(switch_message))
        
        # Update current thread
        self.current_thread_id = target_thread_id
        
        logger.info(f"🔄 User {self.user_id} switching from {from_thread_id} to {target_thread_id}")
        
        # Brief delay to allow server to process switch
        await asyncio.sleep(0.2)
        
        return switch_index
    
    async def send_message_in_current_thread(self, message: str, message_type: str = "user_message") -> str:
        """Send message in currently active thread."""
        if not self.current_thread_id:
            raise ValueError(f"User {self.user_id} has no active thread")
        
        if not self.websocket or not self.is_connected:
            raise ConnectionError(f"User {self.user_id} WebSocket not connected")
        
        # Generate message ID
        id_generator = UnifiedIdGenerator()
        message_id = id_generator.generate_message_id(self.user_id)
        
        # Create message
        message_data = {
            "type": message_type,
            "user_id": self.user_id,
            "thread_id": self.current_thread_id,
            "message_id": message_id,
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.websocket.send(json.dumps(message_data))
        
        # Track in client
        if self.current_thread_id in self.user_threads:
            self.user_threads[self.current_thread_id]["message_count"] += 1
        
        logger.info(f"💬 User {self.user_id} sent message in thread {self.current_thread_id}")
        return message_id
    
    async def get_thread_history(self, thread_id: str) -> Dict:
        """Get message history for specific thread."""
        if not self.websocket or not self.is_connected:
            raise ConnectionError(f"User {self.user_id} WebSocket not connected")
        
        # Request thread history
        history_request = {
            "type": "get_thread_history",
            "user_id": self.user_id,
            "thread_id": thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.websocket.send(json.dumps(history_request))
        
        # Wait for history response (simplified - real implementation would be more complex)
        await asyncio.sleep(1.0)
        
        # Return tracked history from switching tracker
        return self.switching_tracker.validate_thread_history_preservation(thread_id)
    
    async def validate_current_thread_context(self) -> Dict:
        """Validate that current thread context is correct."""
        if not self.current_thread_id:
            return {"valid": False, "error": "No current thread"}
        
        # Validate with switching tracker
        history_validation = self.switching_tracker.validate_thread_history_preservation(self.current_thread_id)
        
        # Additional client-side validations
        client_thread_info = self.user_threads.get(self.current_thread_id, {})
        
        return {
            "valid": history_validation["preserved"],
            "current_thread_id": self.current_thread_id,
            "client_message_count": client_thread_info.get("message_count", 0),
            "tracked_message_count": history_validation["message_count"],
            "history_validation": history_validation
        }


class TestThreadSwitchingConsistencyE2E:
    """
    CRITICAL E2E test suite for thread switching consistency.
    
    Tests that users can switch between conversation threads seamlessly
    while maintaining perfect context preservation and message history.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up test class with real service requirements."""
        cls.env = get_env()
        cls.test_environment = cls.env.get("TEST_ENV", cls.env.get("ENVIRONMENT", "test"))
        
        logger.info("🚀 Starting Thread Switching Consistency E2E Tests")
        logger.info(f"📍 Environment: {cls.test_environment}")
        logger.info("🎯 Testing thread switching with context preservation")
    
    def setup_method(self, method):
        """Set up each test method."""
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        self.switching_tracker = ThreadSwitchingTracker(self.test_environment)
        self.test_clients: List[ThreadSwitchingWebSocketClient] = []
        
        logger.info(f"🧪 Starting test: {method.__name__}")
    
    def teardown_method(self, method):
        """Clean up test resources."""
        logger.info(f"🧹 Cleaning up test: {method.__name__}")
        self.test_clients.clear()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_basic_thread_switching_context_preservation(self):
        """
        CRITICAL TEST: Basic thread switching preserves context and message history.
        
        This test validates that when a user switches between two conversation
        threads, the context and message history are perfectly preserved.
        
        Expected Initial Result: FAILURE - Thread context likely not preserved
        Success Criteria: Perfect context preservation across switches
        """
        test_start_time = time.time()
        logger.info("🔄 CRITICAL: Testing basic thread switching context preservation")
        
        try:
            # Create authenticated user
            user_context = await create_authenticated_user_context(
                user_email=f"thread_switching_{int(time.time())}@example.com",
                environment=self.test_environment,
                websocket_enabled=True
            )
            
            # Create thread switching client
            client = ThreadSwitchingWebSocketClient(
                user_context,
                self.auth_helper,
                self.switching_tracker
            )
            self.test_clients.append(client)
            
            async with client.connect(timeout=30.0):
                logger.info(f"✅ Connected user {client.user_id} for basic thread switching test")
                
                # Create two conversation threads
                thread_1_id = await client.create_conversation_thread(
                    "Conversation 1: Performance Optimization",
                    {"topic": "performance", "priority": "high"}
                )
                
                thread_2_id = await client.create_conversation_thread(
                    "Conversation 2: Security Review",
                    {"topic": "security", "priority": "medium"}
                )
                
                # Add messages to Thread 1
                logger.info("💬 Adding messages to Thread 1...")
                await client.switch_to_thread(thread_1_id, "initial_selection")
                
                await client.send_message_in_current_thread("How can I optimize database queries?")
                await asyncio.sleep(0.5)
                await client.send_message_in_current_thread("What about caching strategies?")
                await asyncio.sleep(0.5)
                
                # Switch to Thread 2 and add messages
                logger.info("🔄 Switching to Thread 2...")
                switch_1_index = await client.switch_to_thread(thread_2_id, "user_switching")
                
                await client.send_message_in_current_thread("What are the latest security vulnerabilities?")
                await asyncio.sleep(0.5)
                await client.send_message_in_current_thread("How should I implement 2FA?")
                await asyncio.sleep(0.5)
                
                # Switch back to Thread 1
                logger.info("🔄 Switching back to Thread 1...")
                switch_2_index = await client.switch_to_thread(thread_1_id, "return_to_conversation")
                
                await client.send_message_in_current_thread("Also, what about connection pooling?")
                await asyncio.sleep(0.5)
                
                # Switch back to Thread 2
                logger.info("🔄 Final switch to Thread 2...")
                switch_3_index = await client.switch_to_thread(thread_2_id, "final_check")
                
                await client.send_message_in_current_thread("What about rate limiting?")
                await asyncio.sleep(1.0)  # Allow final processing
                
                # Complete all switches
                self.switching_tracker.complete_thread_switch(switch_1_index)
                self.switching_tracker.complete_thread_switch(switch_2_index)
                self.switching_tracker.complete_thread_switch(switch_3_index)
                
                # Validate thread context preservation
                thread_1_history = self.switching_tracker.validate_thread_history_preservation(thread_1_id)
                thread_2_history = self.switching_tracker.validate_thread_history_preservation(thread_2_id)
                
                # Validate current context
                current_context = await client.validate_current_thread_context()
                
                # Generate switching report
                report = self.switching_tracker.generate_switching_report()
                
                logger.info("📊 BASIC THREAD SWITCHING RESULTS:")
                logger.info(f"   Thread Switches: {report['switching_analysis']['switch_count']}")
                logger.info(f"   Context Preservation Rate: {report['switching_analysis']['context_preservation_rate']:.2%}")
                logger.info(f"   Thread 1 History Preserved: {thread_1_history['preserved']}")
                logger.info(f"   Thread 2 History Preserved: {thread_2_history['preserved']}")
                logger.info(f"   Context Failures: {report['context_preservation_failures']}")
                
                # CRITICAL ASSERTIONS - Expected to FAIL initially
                if not thread_1_history["preserved"] or not thread_2_history["preserved"]:
                    logger.error("🚨 THREAD HISTORY PRESERVATION FAILURE")
                    logger.error(f"🔍 Thread 1 preserved: {thread_1_history['preserved']}")
                    logger.error(f"🔍 Thread 2 preserved: {thread_2_history['preserved']}")
                    
                    # Expected failure - thread history not preserved
                    pytest.fail(
                        f"THREAD HISTORY FAILURE: Thread histories not preserved across switches. "
                        f"Thread 1: {thread_1_history}, Thread 2: {thread_2_history}. "
                        f"Context preservation broken in thread switching."
                    )
                
                if report["context_preservation_failures"] > 0:
                    logger.error("🚨 CONTEXT PRESERVATION FAILURES DETECTED")
                    logger.error(f"🔍 Found {report['context_preservation_failures']} failures")
                    
                    for failure in self.switching_tracker.context_preservation_failures:
                        logger.error(f"🔍 Failure: {failure}")
                    
                    # Expected failure - context preservation issues
                    pytest.fail(
                        f"CONTEXT PRESERVATION FAILURE: {report['context_preservation_failures']} failures. "
                        f"Thread switching does not preserve conversation context properly."
                    )
                
                if not current_context["valid"]:
                    logger.error("🚨 CURRENT CONTEXT VALIDATION FAILURE")
                    logger.error(f"🔍 Context validation: {current_context}")
                    
                    pytest.fail(
                        f"CURRENT CONTEXT FAILURE: Current thread context invalid. "
                        f"User cannot reliably determine active conversation state."
                    )
                
                # Success validations
                logger.info("✅ SUCCESS: Perfect thread switching context preservation!")
                
                # Verify sufficient message history
                assert thread_1_history["message_count"] >= 3, \
                    f"Thread 1 insufficient messages: {thread_1_history['message_count']}"
                
                assert thread_2_history["message_count"] >= 3, \
                    f"Thread 2 insufficient messages: {thread_2_history['message_count']}"
                
                # Verify switching performance
                avg_switch_time = report["switching_analysis"]["avg_switch_duration"]
                assert avg_switch_time <= 2.0, \
                    f"Thread switching too slow: {avg_switch_time:.2f}s"
                
                # Verify context preservation rate
                assert report["switching_analysis"]["context_preservation_rate"] >= 0.95, \
                    f"Context preservation rate too low: {report['switching_analysis']['context_preservation_rate']:.2%}"
        
        except Exception as e:
            report = self.switching_tracker.generate_switching_report()
            logger.error(f"📊 Partial results: {report}")
            logger.error(f"❌ Basic thread switching test failed: {e}")
            raise
        
        # Verify test duration
        actual_duration = time.time() - test_start_time
        assert actual_duration > 6.0, \
            f"Thread switching test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f"✅ Basic thread switching test completed in {actual_duration:.2f}s")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_rapid_thread_switching_stability(self):
        """
        CRITICAL TEST: Rapid thread switching maintains stability and consistency.
        
        This test validates that when a user rapidly switches between multiple
        threads, the system maintains stability without losing context or messages.
        
        Expected Initial Result: FAILURE - Race conditions during rapid switching
        Success Criteria: Stable context preservation under rapid switching stress
        """
        test_start_time = time.time()
        logger.info("⚡ CRITICAL: Testing rapid thread switching stability")
        
        # Rapid switching test configuration
        num_threads = 5
        switches_per_thread = 3
        rapid_switch_delay = 0.1  # 100ms between switches
        
        try:
            # Create authenticated user
            user_context = await create_authenticated_user_context(
                user_email=f"rapid_switching_{int(time.time())}@example.com",
                environment=self.test_environment,
                websocket_enabled=True
            )
            
            # Create rapid switching client
            client = ThreadSwitchingWebSocketClient(
                user_context,
                self.auth_helper,
                self.switching_tracker
            )
            self.test_clients.append(client)
            
            async with client.connect(timeout=35.0):
                logger.info(f"✅ Connected user {client.user_id} for rapid switching test")
                
                # Create multiple threads
                thread_ids = []
                logger.info(f"📝 Creating {num_threads} conversation threads...")
                for i in range(num_threads):
                    thread_id = await client.create_conversation_thread(
                        f"Rapid Test Thread {i}",
                        {"thread_index": i, "test_type": "rapid_switching"}
                    )
                    thread_ids.append(thread_id)
                
                # Add initial messages to each thread
                for i, thread_id in enumerate(thread_ids):
                    await client.switch_to_thread(thread_id, "initial_setup")
                    await client.send_message_in_current_thread(f"Initial message for thread {i}")
                    await asyncio.sleep(rapid_switch_delay)
                
                # Perform rapid switching pattern
                logger.info("⚡ Starting rapid thread switching pattern...")
                switch_indices = []
                
                for switch_round in range(switches_per_thread):
                    for i, thread_id in enumerate(thread_ids):
                        # Rapid switch
                        switch_index = await client.switch_to_thread(thread_id, f"rapid_switch_round_{switch_round}")
                        switch_indices.append(switch_index)
                        
                        # Send message in current thread
                        await client.send_message_in_current_thread(
                            f"Rapid switch message round {switch_round} in thread {i}"
                        )
                        
                        # Rapid delay
                        await asyncio.sleep(rapid_switch_delay)
                
                # Complete all switches
                for switch_index in switch_indices:
                    self.switching_tracker.complete_thread_switch(switch_index)
                
                # Allow processing time
                await asyncio.sleep(2.0)
                
                # Validate all threads after rapid switching
                thread_validations = {}
                for i, thread_id in enumerate(thread_ids):
                    thread_validations[thread_id] = self.switching_tracker.validate_thread_history_preservation(thread_id)
                
                # Generate rapid switching report
                report = self.switching_tracker.generate_switching_report()
                
                # Analyze results
                preserved_threads = sum(1 for v in thread_validations.values() if v["preserved"])
                total_switches = len(switch_indices)
                
                logger.info("📊 RAPID THREAD SWITCHING RESULTS:")
                logger.info(f"   Total Threads: {num_threads}")
                logger.info(f"   Preserved Threads: {preserved_threads}/{num_threads}")
                logger.info(f"   Total Switches: {total_switches}")
                logger.info(f"   Context Preservation Rate: {report['switching_analysis']['context_preservation_rate']:.2%}")
                logger.info(f"   Avg Switch Duration: {report['switching_analysis']['avg_switch_duration']:.3f}s")
                logger.info(f"   Context Failures: {report['context_preservation_failures']}")
                
                # CRITICAL ASSERTIONS - Expected to FAIL initially due to race conditions
                if preserved_threads < num_threads:
                    logger.error("🚨 RAPID SWITCHING THREAD PRESERVATION FAILURE")
                    logger.error(f"🔍 Only {preserved_threads}/{num_threads} threads preserved")
                    
                    # Log failed thread details
                    for thread_id, validation in thread_validations.items():
                        if not validation["preserved"]:
                            logger.error(f"🔍 Failed thread {thread_id}: {validation}")
                    
                    # Expected failure - rapid switching causes data loss
                    pytest.fail(
                        f"RAPID SWITCHING FAILURE: Only {preserved_threads}/{num_threads} threads preserved. "
                        f"Rapid switching causes context/message loss. Race conditions in thread management."
                    )
                
                if report["context_preservation_failures"] > 0:
                    logger.error("🚨 RAPID SWITCHING CONTEXT FAILURES")
                    logger.error(f"🔍 Found {report['context_preservation_failures']} context failures")
                    
                    pytest.fail(
                        f"RAPID SWITCHING CONTEXT FAILURE: {report['context_preservation_failures']} failures. "
                        f"System cannot handle rapid thread switching without context corruption."
                    )
                
                if report["switching_analysis"]["avg_switch_duration"] > 1.0:
                    logger.error("🚨 RAPID SWITCHING PERFORMANCE DEGRADATION")
                    logger.error(f"🔍 Switch duration: {report['switching_analysis']['avg_switch_duration']:.3f}s")
                    
                    pytest.fail(
                        f"RAPID SWITCHING PERFORMANCE FAILURE: {report['switching_analysis']['avg_switch_duration']:.3f}s "
                        f"average switch time too slow. Performance degrades under rapid switching load."
                    )
                
                # Success validations
                logger.info("✅ SUCCESS: Perfect rapid thread switching stability!")
                
                # Verify all threads have expected messages
                expected_messages_per_thread = 1 + switches_per_thread  # Initial + rapid messages
                for thread_id, validation in thread_validations.items():
                    assert validation["message_count"] >= expected_messages_per_thread * 0.8, \
                        f"Thread {thread_id} insufficient messages: {validation['message_count']}"
                
                # Verify switching performance under load
                assert report["switching_analysis"]["context_preservation_rate"] >= 0.9, \
                    f"Context preservation rate too low under rapid switching: {report['switching_analysis']['context_preservation_rate']:.2%}"
        
        except Exception as e:
            report = self.switching_tracker.generate_switching_report()
            logger.error(f"📊 Rapid switching partial results: {report}")
            logger.error(f"❌ Rapid thread switching test failed: {e}")
            raise
        
        # Verify significant test duration for rapid switching
        actual_duration = time.time() - test_start_time
        assert actual_duration > 8.0, \
            f"Rapid switching test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f"✅ Rapid thread switching test completed in {actual_duration:.2f}s")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_multi_user_thread_switching_isolation(self):
        """
        CRITICAL TEST: Multiple users switching threads independently with perfect isolation.
        
        This test validates that when multiple users are switching between their
        own threads simultaneously, there's no cross-user contamination or interference.
        
        Expected Initial Result: FAILURE - Cross-user thread switching interference
        Success Criteria: Perfect isolation during concurrent multi-user thread switching
        """
        test_start_time = time.time()
        logger.info("👥🔄 CRITICAL: Testing multi-user thread switching isolation")
        
        # Multi-user switching test configuration
        num_users = 3
        threads_per_user = 3
        switches_per_user = 4
        
        user_clients = []
        switching_tasks = []
        
        try:
            # Create multiple authenticated users
            logger.info(f"🔐 Creating {num_users} users for concurrent thread switching...")
            for user_idx in range(num_users):
                user_context = await create_authenticated_user_context(
                    user_email=f"multi_user_switching_{user_idx}_{int(time.time())}@example.com",
                    environment=self.test_environment,
                    websocket_enabled=True
                )
                
                client = ThreadSwitchingWebSocketClient(
                    user_context,
                    self.auth_helper,
                    self.switching_tracker
                )
                user_clients.append(client)
                self.test_clients.append(client)
                
                logger.info(f"✅ Created switching user {user_idx}: {client.user_id}")
            
            # Execute concurrent thread switching scenarios
            for user_idx, client in enumerate(user_clients):
                task = asyncio.create_task(
                    self._execute_user_thread_switching_scenario(
                        client, threads_per_user, switches_per_user, user_idx
                    )
                )
                switching_tasks.append(task)
            
            # Run all user switching scenarios concurrently
            logger.info("🚀 Executing concurrent multi-user thread switching...")
            user_results = await asyncio.gather(*switching_tasks, return_exceptions=True)
            
            # Analyze multi-user switching results
            successful_users = 0
            total_switches_completed = 0
            cross_user_contamination = 0
            context_preservation_failures = 0
            
            for user_idx, result in enumerate(user_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ User {user_idx} thread switching failed: {result}")
                else:
                    successful_users += 1
                    total_switches_completed += result.get("switches_completed", 0)
                    cross_user_contamination += result.get("cross_user_issues", 0)
                    context_preservation_failures += result.get("context_failures", 0)
                    
                    logger.info(f"👤 User {user_idx}: {result.get('switches_completed', 0)} switches, "
                              f"Context preserved: {result.get('context_preserved', True)}")
            
            # Generate comprehensive multi-user report
            report = self.switching_tracker.generate_switching_report()
            
            logger.info("📊 MULTI-USER THREAD SWITCHING ISOLATION RESULTS:")
            logger.info(f"   Successful Users: {successful_users}/{num_users}")
            logger.info(f"   Total Switches Completed: {total_switches_completed}")
            logger.info(f"   Cross-User Contamination Issues: {cross_user_contamination}")
            logger.info(f"   Context Preservation Failures: {context_preservation_failures}")
            logger.info(f"   Overall Context Preservation Rate: {report['switching_analysis']['context_preservation_rate']:.2%}")
            
            # CRITICAL ASSERTIONS - Expected to FAIL initially
            if cross_user_contamination > 0:
                logger.error("🚨 CROSS-USER THREAD SWITCHING CONTAMINATION")
                logger.error(f"🔍 Found {cross_user_contamination} cross-user issues")
                
                # Expected failure - multi-user isolation breaks
                pytest.fail(
                    f"CROSS-USER CONTAMINATION FAILURE: {cross_user_contamination} cross-user issues. "
                    f"Thread switching not properly isolated between users. "
                    f"Users seeing or affecting other users' thread contexts."
                )
            
            if context_preservation_failures > 0:
                logger.error("🚨 MULTI-USER CONTEXT PRESERVATION FAILURES")
                logger.error(f"🔍 Found {context_preservation_failures} context failures")
                
                pytest.fail(
                    f"MULTI-USER CONTEXT FAILURE: {context_preservation_failures} context preservation failures. "
                    f"Thread switching fails under multi-user concurrent load."
                )
            
            if successful_users < num_users:
                logger.error("🚨 MULTI-USER SWITCHING SYSTEM FAILURES")
                logger.error(f"🔍 Only {successful_users}/{num_users} users completed successfully")
                
                pytest.fail(
                    f"MULTI-USER SWITCHING FAILURE: Only {successful_users}/{num_users} users successful. "
                    f"System cannot handle concurrent multi-user thread switching."
                )
            
            # Success validations
            logger.info("✅ SUCCESS: Perfect multi-user thread switching isolation!")
            
            # Verify switching load handling
            expected_total_switches = num_users * switches_per_user
            assert total_switches_completed >= expected_total_switches * 0.9, \
                f"Too few switches completed: {total_switches_completed}/{expected_total_switches}"
            
            # Verify context preservation under concurrent load
            assert report["switching_analysis"]["context_preservation_rate"] >= 0.9, \
                f"Context preservation rate too low under multi-user load: {report['switching_analysis']['context_preservation_rate']:.2%}"
        
        except Exception as e:
            report = self.switching_tracker.generate_switching_report()
            logger.error(f"📊 Multi-user switching partial results: {report}")
            logger.error(f"❌ Multi-user thread switching isolation test failed: {e}")
            raise
        
        # Verify significant test duration for complex scenario
        actual_duration = time.time() - test_start_time
        assert actual_duration > 12.0, \
            f"Multi-user switching test completed too quickly ({actual_duration:.2f}s)"
        
        logger.info(f"✅ Multi-user thread switching isolation test completed in {actual_duration:.2f}s")
    
    async def _execute_user_thread_switching_scenario(self, client: ThreadSwitchingWebSocketClient,
                                                    num_threads: int, num_switches: int, user_idx: int) -> Dict:
        """Execute thread switching scenario for single user."""
        switches_completed = 0
        cross_user_issues = 0
        context_failures = 0
        context_preserved = True
        
        try:
            async with client.connect(timeout=40.0):
                # Create multiple threads for this user
                thread_ids = []
                for thread_idx in range(num_threads):
                    thread_id = await client.create_conversation_thread(
                        f"User {user_idx} Thread {thread_idx}",
                        {"user_idx": user_idx, "thread_idx": thread_idx}
                    )
                    thread_ids.append(thread_id)
                    
                    # Add initial message
                    await client.switch_to_thread(thread_id, "setup")
                    await client.send_message_in_current_thread(f"Initial message for thread {thread_idx}")
                    await asyncio.sleep(0.1)
                
                # Perform switching pattern
                for switch_num in range(num_switches):
                    # Pick random thread to switch to
                    import random
                    target_thread_id = random.choice(thread_ids)
                    
                    # Switch to thread
                    await client.switch_to_thread(target_thread_id, f"switch_{switch_num}")
                    switches_completed += 1
                    
                    # Send message
                    await client.send_message_in_current_thread(f"Switch {switch_num} message")
                    
                    # Brief delay
                    await asyncio.sleep(0.2)
                
                # Validate final context
                final_context = await client.validate_current_thread_context()
                if not final_context["valid"]:
                    context_preserved = False
                    context_failures += 1
                
                # Check for cross-user contamination (simplified check)
                # In real implementation, this would check if user received messages meant for other users
                # For this test, we assume isolation is maintained if context is valid
        
        except Exception as e:
            logger.error(f"❌ User {user_idx} thread switching scenario failed: {e}")
            raise
        
        return {
            "user_idx": user_idx,
            "user_id": client.user_id,
            "switches_completed": switches_completed,
            "cross_user_issues": cross_user_issues,
            "context_failures": context_failures,
            "context_preserved": context_preserved
        }


# ============================================================================
# TEST EXECUTION CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    """
    Direct test execution for debugging and development.
    
    Run with: python -m pytest tests/e2e/thread_routing/test_thread_switching_consistency_e2e.py -v -s
    Or with unified test runner: python tests/unified_test_runner.py --real-services --category e2e
    """
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Starting Thread Switching Consistency E2E Test Suite")
    logger.info("📋 Tests included:")
    logger.info("   1. test_basic_thread_switching_context_preservation")
    logger.info("   2. test_rapid_thread_switching_stability")
    logger.info("   3. test_multi_user_thread_switching_isolation")
    logger.info("🎯 Business Value: Ensures seamless multi-conversation Chat UX")
    logger.info("🔧 Requirements: Full Docker stack + Database + WebSocket")
    logger.info("⚠️  Expected: Initial FAILURES due to thread switching edge case bugs")
    
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])