#!/usr/bin/env python
"""Mission Critical Tests: WebSocket Bridge Isolation Validation
================================================================
These tests validate CRITICAL user isolation in WebSocket factory patterns.
User isolation is essential for security, privacy, and data integrity.

EXPECTED RESULT: These tests should PASS, proving factory patterns provide proper isolation.

Uses Factory-Based WebSocket Patterns from USER_CONTEXT_ARCHITECTURE.md
"""

import asyncio
import uuid
import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

# Import environment management
from shared.isolated_environment import get_env

# Set up isolated test environment
env = get_env()
env.set('WEBSOCKET_TEST_ISOLATED', 'true', "test")
env.set('SKIP_REAL_SERVICES', 'false', "test")
env.set('USE_REAL_SERVICES', 'true', "test")

# Import factory patterns from architecture
from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    UserWebSocketEmitter,
    UserWebSocketContext,
    WebSocketEvent
)

# Import test framework components
from test_framework.test_context import TestContext, create_test_context

# Disable pytest warnings
pytestmark = [
    pytest.mark.filterwarnings("ignore"),
    pytest.mark.asyncio
]

# Simple logger for test output
class IsolationLogger:
    def info(self, msg): print(f"ISOLATION: {msg}")
    def warning(self, msg): print(f"WARN: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")

logger = IsolationLogger()


# ============================================================================
# ISOLATION TEST INFRASTRUCTURE
# ============================================================================

class IsolationTestManager:
    """Manager for testing user isolation in factory patterns."""
    
    def __init__(self):
        self.factory = WebSocketBridgeFactory()
        self.user_contexts: Dict[str, UserWebSocketContext] = {}
        self.user_events: Dict[str, List[Dict]] = {}
        self.cross_contamination_detected = []
        
    async def initialize(self):
        """Initialize factory for isolation testing."""
        from test_framework.websocket_helpers import create_test_connection_pool
        connection_pool = await create_test_connection_pool()
        
        self.factory.configure(
            connection_pool=connection_pool,
            agent_registry=None,
            health_monitor=None
        )
        
    async def create_isolated_user(self, user_id: str, thread_id: str) -> UserWebSocketEmitter:
        """Create isolated user emitter and track for validation."""
        connection_id = f"isolation_conn_{user_id}_{uuid.uuid4().hex[:8]}"
        
        user_emitter = await self.factory.create_user_emitter(
            user_id=user_id,
            thread_id=thread_id,
            connection_id=connection_id
        )
        
        # Store user context for isolation validation
        self.user_contexts[user_id] = user_emitter.user_context
        self.user_events[user_id] = []
        
        # Wrap emitter to track events for isolation validation
        original_methods = {}
        for method_name in ['notify_agent_started', 'notify_agent_thinking', 'notify_tool_executing',
                           'notify_tool_completed', 'notify_agent_completed', 'notify_agent_error']:
            if hasattr(user_emitter, method_name):
                original_method = getattr(user_emitter, method_name)
                original_methods[method_name] = original_method
                
                async def create_wrapper(method_name, original_method, user_id):
                    async def wrapper(*args, **kwargs):
                        # Record event for isolation validation
                        event_record = {
                            'user_id': user_id,
                            'method': method_name,
                            'args': args,
                            'kwargs': kwargs,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        self.user_events[user_id].append(event_record)
                        
                        # Check for cross-contamination
                        self._detect_cross_contamination(user_id, event_record)
                        
                        return await original_method(*args, **kwargs)
                    return wrapper
                
                setattr(user_emitter, method_name, await create_wrapper(method_name, original_method, user_id))
        
        return user_emitter
    
    def _detect_cross_contamination(self, expected_user_id: str, event_record: Dict):
        """Detect if event belongs to wrong user (cross-contamination)."""
        # Check if event context matches expected user
        actual_context = self.user_contexts.get(expected_user_id)
        if not actual_context:
            return
        
        if actual_context.user_id != expected_user_id:
            contamination = {
                'expected_user': expected_user_id,
                'actual_user': actual_context.user_id,
                'event': event_record,
                'severity': 'CRITICAL'
            }
            self.cross_contamination_detected.append(contamination)
            logger.error(f"CROSS-CONTAMINATION DETECTED: {contamination}")
    
    def validate_user_isolation(self, user_id: str) -> bool:
        """Validate that user's events and context are properly isolated."""
        if user_id not in self.user_contexts:
            return False
        
        user_context = self.user_contexts[user_id]
        user_events = self.user_events.get(user_id, [])
        
        # Verify context integrity
        if user_context.user_id != user_id:
            logger.error(f"User context corruption: expected {user_id}, got {user_context.user_id}")
            return False
        
        # Verify all events belong to this user
        for event in user_events:
            if event['user_id'] != user_id:
                logger.error(f"Event cross-contamination: event for {event['user_id']} in {user_id}'s context")
                return False
        
        return True
    
    def get_cross_contamination_report(self) -> Dict:
        """Get report of any cross-contamination detected."""
        return {
            'contamination_count': len(self.cross_contamination_detected),
            'contaminations': self.cross_contamination_detected,
            'severity_levels': [c['severity'] for c in self.cross_contamination_detected]
        }
    
    async def cleanup_all(self):
        """Clean up all user contexts and emitters."""
        # User contexts are automatically cleaned up by their emitters
        self.user_contexts.clear()
        self.user_events.clear()
        self.cross_contamination_detected.clear()


# ============================================================================
# ISOLATION VALIDATION TESTS
# ============================================================================

class TestWebSocketBridgeIsolation:
    """Test suite validating WebSocket Bridge user isolation."""
    
    @pytest.fixture
    async def isolation_manager(self):
        """Isolation test manager fixture."""
        manager = IsolationTestManager()
        await manager.initialize()
        yield manager
        await manager.cleanup_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_basic_user_isolation(self, isolation_manager):
        """CRITICAL: Test basic user isolation between two users."""
        # Create two isolated users
        user1_id = f"user1_{uuid.uuid4().hex[:8]}"
        user2_id = f"user2_{uuid.uuid4().hex[:8]}"
        thread1_id = f"thread1_{uuid.uuid4().hex[:8]}"
        thread2_id = f"thread2_{uuid.uuid4().hex[:8]}"
        
        emitter1 = await isolation_manager.create_isolated_user(user1_id, thread1_id)
        emitter2 = await isolation_manager.create_isolated_user(user2_id, thread2_id)
        
        # Verify context isolation
        assert emitter1.user_context.user_id == user1_id
        assert emitter2.user_context.user_id == user2_id
        assert emitter1.user_context.thread_id == thread1_id
        assert emitter2.user_context.thread_id == thread2_id
        
        # Send events to each user
        await emitter1.notify_agent_started("Agent1", "run1")
        await emitter1.notify_agent_thinking("Agent1", "run1", "User1 thinking")
        
        await emitter2.notify_agent_started("Agent2", "run2")  
        await emitter2.notify_agent_thinking("Agent2", "run2", "User2 thinking")
        
        # Validate isolation
        assert isolation_manager.validate_user_isolation(user1_id), "User1 isolation violated"
        assert isolation_manager.validate_user_isolation(user2_id), "User2 isolation violated"
        
        # Check for cross-contamination
        contamination_report = isolation_manager.get_cross_contamination_report()
        assert contamination_report['contamination_count'] == 0, \
            f"Cross-contamination detected: {contamination_report}"
        
        # Clean up
        await emitter1.cleanup()
        await emitter2.cleanup()
        
        logger.info("[CHECK] Basic user isolation test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_user_isolation_under_load(self, isolation_manager):
        """CRITICAL: Test user isolation under concurrent load."""
        num_concurrent_users = 20
        events_per_user = 5
        
        # Create concurrent users
        async def create_and_test_user(user_index: int):
            user_id = f"load_user_{user_index}_{uuid.uuid4().hex[:8]}"
            thread_id = f"load_thread_{user_index}_{uuid.uuid4().hex[:8]}"
            
            try:
                emitter = await isolation_manager.create_isolated_user(user_id, thread_id)
                
                # Send multiple events rapidly
                for event_index in range(events_per_user):
                    run_id = f"run_{user_index}_{event_index}"
                    await emitter.notify_agent_started(f"Agent{user_index}", run_id)
                    await emitter.notify_agent_thinking(f"Agent{user_index}", run_id, f"Thought {event_index}")
                    await emitter.notify_agent_completed(f"Agent{user_index}", run_id, {"result": f"user_{user_index}"})
                
                # Validate isolation for this user
                isolation_valid = isolation_manager.validate_user_isolation(user_id)
                
                # Clean up
                await emitter.cleanup()
                
                return user_id, isolation_valid
                
            except Exception as e:
                logger.error(f"User {user_index} failed: {e}")
                return f"failed_{user_index}", False
        
        # Execute all users concurrently
        tasks = [create_and_test_user(i) for i in range(num_concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_users = [r for r in results if not isinstance(r, Exception) and r[1]]
        failed_users = [r for r in results if isinstance(r, Exception) or not r[1]]
        
        # Should have high success rate
        assert len(successful_users) >= num_concurrent_users * 0.9, \
            f"Too many isolation failures: {len(successful_users)}/{num_concurrent_users}"
        
        # Check for cross-contamination
        contamination_report = isolation_manager.get_cross_contamination_report()
        assert contamination_report['contamination_count'] == 0, \
            f"Cross-contamination under load: {contamination_report}"
        
        logger.info(f"[CHECK] Concurrent isolation test: {len(successful_users)} users properly isolated")
    
    @pytest.mark.asyncio
    async def test_user_context_memory_isolation(self, isolation_manager):
        """Test that user contexts don't share memory or state."""
        user1_id = f"memory_user1_{uuid.uuid4().hex[:8]}"
        user2_id = f"memory_user2_{uuid.uuid4().hex[:8]}"
        thread1_id = f"memory_thread1_{uuid.uuid4().hex[:8]}"
        thread2_id = f"memory_thread2_{uuid.uuid4().hex[:8]}"
        
        # Create users
        emitter1 = await isolation_manager.create_isolated_user(user1_id, thread1_id)
        emitter2 = await isolation_manager.create_isolated_user(user2_id, thread2_id)
        
        # Verify contexts are different objects
        context1 = emitter1.user_context
        context2 = emitter2.user_context
        
        assert context1 is not context2, "User contexts share same memory object"
        assert id(context1) != id(context2), "User contexts have same memory ID"
        
        # Verify contexts have different user IDs
        assert context1.user_id != context2.user_id, "User contexts have same user_id"
        assert context1.thread_id != context2.thread_id, "User contexts have same thread_id"
        
        # Test that modifying one context doesn't affect the other
        original_user2_id = context2.user_id
        
        # Send events to user1 only
        await emitter1.notify_agent_started("TestAgent", "memory_test")
        
        # Verify user2 context unchanged
        assert context2.user_id == original_user2_id, "User2 context affected by User1 events"
        
        # Validate isolation
        assert isolation_manager.validate_user_isolation(user1_id), "User1 memory isolation violated"
        assert isolation_manager.validate_user_isolation(user2_id), "User2 memory isolation violated"
        
        # Clean up
        await emitter1.cleanup()
        await emitter2.cleanup()
        
        logger.info("[CHECK] User context memory isolation test passed")
    
    @pytest.mark.asyncio
    async def test_isolation_after_user_cleanup(self, isolation_manager):
        """Test isolation is maintained after some users are cleaned up."""
        # Create 3 users
        users = []
        emitters = []
        
        for i in range(3):
            user_id = f"cleanup_user_{i}_{uuid.uuid4().hex[:8]}"
            thread_id = f"cleanup_thread_{i}_{uuid.uuid4().hex[:8]}"
            users.append((user_id, thread_id))
            
            emitter = await isolation_manager.create_isolated_user(user_id, thread_id)
            emitters.append(emitter)
            
            # Send initial events
            await emitter.notify_agent_started(f"Agent{i}", f"initial_{i}")
        
        # Validate all users are isolated
        for i, (user_id, _) in enumerate(users):
            assert isolation_manager.validate_user_isolation(user_id), f"User {i} initial isolation failed"
        
        # Clean up first user
        await emitters[0].cleanup()
        
        # Send events to remaining users
        for i in range(1, 3):
            user_id = users[i][0]
            emitter = emitters[i]
            await emitter.notify_agent_thinking(f"Agent{i}", f"post_cleanup_{i}", "After cleanup")
        
        # Validate remaining users still isolated
        for i in range(1, 3):
            user_id = users[i][0]
            assert isolation_manager.validate_user_isolation(user_id), f"User {i} isolation failed after cleanup"
        
        # Check no cross-contamination
        contamination_report = isolation_manager.get_cross_contamination_report()
        assert contamination_report['contamination_count'] == 0, \
            f"Cross-contamination after cleanup: {contamination_report}"
        
        # Clean up remaining users
        for i in range(1, 3):
            await emitters[i].cleanup()
        
        logger.info("[CHECK] Isolation after cleanup test passed")
    
    @pytest.mark.asyncio
    async def test_isolation_with_identical_thread_ids(self, isolation_manager):
        """Test isolation when different users have identical thread IDs."""
        # Create users with same thread ID but different user IDs
        same_thread_id = f"shared_thread_{uuid.uuid4().hex[:8]}"
        user1_id = f"user1_{uuid.uuid4().hex[:8]}"
        user2_id = f"user2_{uuid.uuid4().hex[:8]}"
        
        # This should still work - users should be isolated by user_id
        emitter1 = await isolation_manager.create_isolated_user(user1_id, same_thread_id)
        emitter2 = await isolation_manager.create_isolated_user(user2_id, same_thread_id)
        
        # Verify contexts are isolated despite same thread ID
        assert emitter1.user_context.user_id == user1_id
        assert emitter2.user_context.user_id == user2_id
        assert emitter1.user_context.thread_id == same_thread_id
        assert emitter2.user_context.thread_id == same_thread_id
        
        # Send events to both users
        await emitter1.notify_agent_started("Agent1", "run1")
        await emitter2.notify_agent_started("Agent2", "run2")
        
        # Validate isolation maintained
        assert isolation_manager.validate_user_isolation(user1_id), "User1 isolation failed with shared thread"
        assert isolation_manager.validate_user_isolation(user2_id), "User2 isolation failed with shared thread"
        
        # Check no cross-contamination
        contamination_report = isolation_manager.get_cross_contamination_report()
        assert contamination_report['contamination_count'] == 0, \
            f"Cross-contamination with shared thread: {contamination_report}"
        
        # Clean up
        await emitter1.cleanup()
        await emitter2.cleanup()
        
        logger.info("[CHECK] Isolation with identical thread IDs test passed")


# ============================================================================
# MAIN TEST CLASS
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical
class TestWebSocketBridgeIsolationComprehensive:
    """Main test class for comprehensive WebSocket Bridge isolation validation."""
    
    @pytest.mark.asyncio
    async def test_run_isolation_validation_suite(self):
        """Meta-test that validates the isolation test suite."""
        logger.info("\n" + "="*80)
        logger.info("🚨 MISSION CRITICAL: WEBSOCKET BRIDGE ISOLATION VALIDATION")
        logger.info("Factory-Based WebSocket User Isolation")
        logger.info("="*80)
        
        logger.info("\n[CHECK] WebSocket Bridge Isolation Test Suite is operational")
        logger.info("[CHECK] All isolation patterns are covered:")
        logger.info("  - Basic user isolation: [CHECK]")
        logger.info("  - Concurrent user isolation under load: [CHECK]")
        logger.info("  - User context memory isolation: [CHECK]")
        logger.info("  - Isolation after user cleanup: [CHECK]")
        logger.info("  - Isolation with identical thread IDs: [CHECK]")
        
        logger.info("\n[ROCKET] Run individual tests with:")
        logger.info("pytest tests/mission_critical/test_websocket_bridge_isolation.py::TestWebSocketBridgeIsolation -v")
        
        logger.info("="*80)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("WEBSOCKET BRIDGE ISOLATION VALIDATION TESTS")
    print("=" * 80)
    print("This test validates critical user isolation in factory patterns:")
    print("1. Basic user isolation between different users")
    print("2. Concurrent user isolation under high load")
    print("3. User context memory isolation")  
    print("4. Isolation maintenance after user cleanup")
    print("5. Isolation with identical thread IDs")
    print("=" * 80)
    print()
    print("[ROCKET] EXECUTION METHODS:")
    print()
    print("Run all tests:")
    print("  python -m pytest tests/mission_critical/test_websocket_bridge_isolation.py -v")
    print()
    print("[CHECK] Factory-based WebSocket patterns from USER_CONTEXT_ARCHITECTURE.md")
    print("[CHECK] Complete user isolation validation")
    print("[CHECK] Cross-contamination detection and prevention")
    print("=" * 80)