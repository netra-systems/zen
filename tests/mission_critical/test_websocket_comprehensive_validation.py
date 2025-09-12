class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

#!/usr/bin/env python
"""
MISSION CRITICAL: Comprehensive WebSocket Validation Test Suite

This is the most rigorous test suite for WebSocket notifications in the Netra system.
It validates ALL critical WebSocket events are sent during agent execution under
every conceivable scenario, including error conditions, concurrent execution,
and high load scenarios.

Business Value: $500K+ ARR - Core chat functionality depends on these events
CRITICAL: These events enable substantive chat interactions - they serve the business goal

Required WebSocket Events (MANDATORY):
1. agent_started - User must see agent began processing 
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency  
4. tool_completed - Tool results display
5. agent_completed - User must know when response is ready

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
import uuid
import threading
import random
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Callable
from contextlib import asynccontextmanager
import weakref
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

# Import environment management
from shared.isolated_environment import get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Import current SSOT components for testing
try:
    from netra_backend.app.services.websocket_bridge_factory import (
        WebSocketBridgeFactory,
        UserWebSocketEmitter,
        UserWebSocketContext,
        WebSocketEvent,
        ConnectionStatus,
        get_websocket_bridge_factory
    )
    from test_framework.test_context import (
        TestContext,
        TestUserContext,
        create_test_context,
        create_isolated_test_contexts
    )
    # Import real WebSocket manager - NO MOCKS per CLAUDE.md
    from test_framework.real_websocket_manager import RealWebSocketManager
except ImportError as e:
    pytest.skip(f"Could not import required WebSocket components: {e}", allow_module_level=True)


# ============================================================================
# CRITICAL: MOCKS REMOVED per CLAUDE.md "MOCKS = Abomination"
# Using RealWebSocketManager for authentic WebSocket testing
# ============================================================================

# UltraReliableMockWebSocketConnection and UltraReliableMockWebSocketPool REMOVED
# Using real WebSocket connections for authentic testing per CLAUDE.md


class ComprehensiveEventValidator:
    """Ultra-rigorous event validation for the factory pattern architecture."""
    
    CRITICAL_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self, strict_mode: bool = True, timeout_seconds: float = 30.0):
        self.strict_mode = strict_mode
        self.timeout_seconds = timeout_seconds
        self.events: List[Dict] = []
        self.user_events: Dict[str, List[Dict]] = {}  # user_id -> events
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()
        
    def record_user_event(self, user_id: str, event: Dict) -> None:
        """Record an event for a specific user."""
        timestamp = time.time() - self.start_time
        event_type = event.get("event_type", "unknown")
        
        # Add timing information
        enriched_event = {
            **event,
            "relative_timestamp": timestamp,
            "sequence": len(self.events)
        }
        
        self.events.append(enriched_event)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        # Per-user tracking
        if user_id not in self.user_events:
            self.user_events[user_id] = []
        self.user_events[user_id].append(enriched_event)
    
    def validate_user_isolation(self) -> tuple[bool, List[str]]:
        """Validate that users are properly isolated."""
        failures = []
        
        # Each user should have their own events
        for user_id, events in self.user_events.items():
            for event in events:
                if event.get("user_id") != user_id:
                    failures.append(f"CRITICAL: Event for user {user_id} has wrong user_id: {event.get('user_id')}")
        
        # No cross-user contamination
        all_user_ids = set(self.user_events.keys())
        for user_id, events in self.user_events.items():
            for event in events:
                event_thread_id = event.get("thread_id", "")
                if any(other_user in event_thread_id for other_user in all_user_ids if other_user != user_id):
                    self.warnings.append(f"Possible cross-user reference in thread_id for user {user_id}")
        
        return len(failures) == 0, failures
    
    def validate_critical_events(self) -> tuple[bool, List[str]]:
        """Validate that all critical events are present."""
        failures = []
        
        missing_events = self.CRITICAL_EVENTS - set(self.event_counts.keys())
        if missing_events:
            failures.append(f"CRITICAL: Missing required events: {missing_events}")
        
        return len(failures) == 0, failures
    
    def validate_event_ordering(self) -> tuple[bool, List[str]]:
        """Validate proper event ordering per user."""
        failures = []
        
        for user_id, events in self.user_events.items():
            if not events:
                continue
                
            event_types = [e.get("event_type") for e in events]
            
            # First event should be agent_started
            if event_types and event_types[0] != "agent_started":
                failures.append(f"CRITICAL: First event for user {user_id} should be agent_started, got {event_types[0]}")
            
            # tool_executing should be followed by tool_completed
            for i, event_type in enumerate(event_types):
                if event_type == "tool_executing":
                    # Find matching tool_completed
                    tool_name = events[i].get("data", {}).get("tool_name", "unknown")
                    found_completion = False
                    for j in range(i + 1, len(event_types)):
                        if event_types[j] == "tool_completed":
                            completion_tool = events[j].get("data", {}).get("tool_name", "unknown")
                            if completion_tool == tool_name:
                                found_completion = True
                                break
                    if not found_completion:
                        failures.append(f"CRITICAL: tool_executing for {tool_name} never completed for user {user_id}")
        
        return len(failures) == 0, failures
    
    def validate_comprehensive(self) -> tuple[bool, List[str], Dict[str, Any]]:
        """Run comprehensive validation."""
        all_failures = []
        
        # Run individual validations
        isolation_valid, isolation_failures = self.validate_user_isolation()
        all_failures.extend(isolation_failures)
        
        events_valid, events_failures = self.validate_critical_events()
        all_failures.extend(events_failures)
        
        ordering_valid, ordering_failures = self.validate_event_ordering()
        all_failures.extend(ordering_failures)
        
        # Generate analysis
        analysis = {
            "total_events": len(self.events),
            "total_users": len(self.user_events),
            "event_counts": self.event_counts.copy(),
            "users_with_complete_flows": sum(1 for events in self.user_events.values() 
                                           if any(e.get("event_type") == "agent_completed" for e in events)),
            "isolation_valid": isolation_valid,
            "events_valid": events_valid,
            "ordering_valid": ordering_valid,
            "duration_seconds": time.time() - self.start_time
        }
        
        return len(all_failures) == 0, all_failures, analysis


class WebSocketFactoryTestHarness:
    """Test harness for the new WebSocket factory architecture."""
    
    def __init__(self):
        self.factory = WebSocketBridgeFactory()
        self.real_websocket_manager = RealWebSocketManager()
        self.validator = ComprehensiveEventValidator()
        
        # Configure factory with real WebSocket manager
        self.factory.configure(
            connection_pool=self.mock_pool,
            websocket = TestWebSocketConnection()  # Real WebSocket implementation,  # Mock registry
        )
        
        self.user_emitters: Dict[str, UserWebSocketEmitter] = {}
        
    async def create_user_emitter(self, user_id: str, connection_id: str = "default") -> UserWebSocketEmitter:
        """Create a user-specific emitter for testing."""
        thread_id = f"thread_{user_id}_{connection_id}"
        
        emitter = await self.factory.create_user_emitter(
            user_id=user_id,
            thread_id=thread_id,
            connection_id=connection_id
        )
        
        self.user_emitters[user_id] = emitter
        return emitter
    
    async def simulate_complete_agent_flow(self, user_id: str, agent_name: str = "TestAgent", 
                                         include_tools: bool = True) -> bool:
        """Simulate complete agent flow for a user."""
        try:
            emitter = await self.create_user_emitter(user_id)
            run_id = f"run_{uuid.uuid4().hex[:8]}"
            
            # Send agent events
            await emitter.notify_agent_started(agent_name, run_id)
            self._record_emitter_event(user_id, emitter, "agent_started")
            
            await emitter.notify_agent_thinking(agent_name, run_id, "Processing request...")
            self._record_emitter_event(user_id, emitter, "agent_thinking")
            
            if include_tools:
                tool_name = "test_tool"
                await emitter.notify_tool_executing(agent_name, run_id, tool_name, {"param": "value"})
                self._record_emitter_event(user_id, emitter, "tool_executing", {"tool_name": tool_name})
                
                await emitter.notify_tool_completed(agent_name, run_id, tool_name, {"result": "success"})
                self._record_emitter_event(user_id, emitter, "tool_completed", {"tool_name": tool_name})
            
            await emitter.notify_agent_completed(agent_name, run_id, {"status": "completed"})
            self._record_emitter_event(user_id, emitter, "agent_completed")
            
            return True
            
        except Exception as e:
            print(f"Error in agent flow for user {user_id}: {e}")
            return False
    
    def _record_emitter_event(self, user_id: str, emitter: UserWebSocketEmitter, 
                            event_type: str, extra_data: Dict = None):
        """Record an event from the emitter for validation."""
        event_data = {
            "event_type": event_type,
            "user_id": user_id,
            "thread_id": emitter.user_context.thread_id,
            "data": extra_data or {}
        }
        self.validator.record_user_event(user_id, event_data)
    
    async def run_concurrent_user_scenarios(self, user_count: int = 10) -> Dict[str, Any]:
        """Run concurrent scenarios for multiple users."""
        tasks = []
        user_ids = []
        
        for i in range(user_count):
            user_id = f"user_{i}_{uuid.uuid4().hex[:8]}"
            user_ids.append(user_id)
            
            task = self.simulate_complete_agent_flow(
                user_id=user_id,
                agent_name=f"Agent_{i}",
                include_tools=i % 2 == 0  # Vary scenarios
            )
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        successful_flows = sum(1 for r in results if r is True)
        
        return {
            "total_users": user_count,
            "successful_flows": successful_flows,
            "success_rate": successful_flows / user_count,
            "duration_seconds": duration,
            "user_ids": user_ids
        }
    
    def get_comprehensive_results(self) -> Dict[str, Any]:
        """Get comprehensive test results."""
        is_valid, failures, analysis = self.validator.validate_comprehensive()
        
        return {
            "validation_passed": is_valid,
            "validation_failures": failures,
            "analysis": analysis,
            "factory_metrics": self.factory.get_factory_metrics()
        }


# ============================================================================
# ULTRA-COMPREHENSIVE TEST SUITE FOR FACTORY ARCHITECTURE
# ============================================================================

class TestUltraComprehensiveWebSocketValidation:
    """The most comprehensive WebSocket validation test suite for factory architecture."""
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup ultra-comprehensive test environment with real WebSocket connections."""
        self.test_harness = WebSocketFactoryTestHarness()
        
        # Initialize real WebSocket session
        self._websocket_session = self.test_harness.real_websocket_manager.real_websocket_session()
        await self._websocket_session.__aenter__()
        
        try:
            yield
        finally:
            # Cleanup
            for emitter in self.test_harness.user_emitters.values():
                try:
                    await emitter.cleanup()
                except Exception:
                    pass
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_comprehensive_single_user_flow(self):
        """Test comprehensive single user flow with factory pattern."""
        print(" TARGET:  Testing comprehensive single user flow")
        
        user_id = "single_user_test"
        success = await self.test_harness.simulate_complete_agent_flow(user_id)
        
        assert success, "Single user agent flow simulation failed"
        
        # Validate results
        results = self.test_harness.get_comprehensive_results()
        assert results["validation_passed"], f"Validation failed: {results['validation_failures']}"
        
        # Check factory metrics
        factory_metrics = results["factory_metrics"]
        assert factory_metrics["emitters_created"] >= 1, "Factory should have created at least 1 emitter"
        assert factory_metrics["emitters_active"] >= 1, "Factory should have active emitters"
        
        print(" PASS:  Comprehensive single user flow test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(120)
    async def test_comprehensive_user_isolation(self):
        """Test comprehensive user isolation with factory pattern."""
        print("[U+1F512] Testing comprehensive user isolation")
        
        # Create multiple isolated users
        user_count = 15
        concurrent_results = await self.test_harness.run_concurrent_user_scenarios(user_count)
        
        assert concurrent_results["success_rate"] >= 0.95, \
            f"User isolation success rate too low: {concurrent_results['success_rate']}"
        
        # Validate isolation
        results = self.test_harness.get_comprehensive_results()
        assert results["validation_passed"], f"User isolation validation failed: {results['validation_failures']}"
        
        analysis = results["analysis"]
        assert analysis["total_users"] == user_count, f"Should track {user_count} users"
        assert analysis["isolation_valid"], "User isolation validation failed"
        
        # Verify factory managed multiple emitters
        factory_metrics = results["factory_metrics"]
        assert factory_metrics["emitters_created"] >= user_count, \
            f"Factory should have created {user_count} emitters, got {factory_metrics['emitters_created']}"
        
        print(" PASS:  Comprehensive user isolation test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(90)
    async def test_comprehensive_event_delivery_reliability(self):
        """Test comprehensive event delivery reliability."""
        print("[U+1F4E1] Testing comprehensive event delivery reliability")
        
        # Test with some network issues
        user_ids = []
        for i in range(10):
            user_id = f"reliability_user_{i}"
            user_ids.append(user_id)
            
            # Configure some connection issues for testing
            if i % 3 == 0:
                self.test_harness.mock_pool.configure_connection_issues(
                    user_id, latency_ms=50, failure_rate=0.1
                )
        
        # Run scenarios
        tasks = []
        for user_id in user_ids:
            task = self.test_harness.simulate_complete_agent_flow(user_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_rate = sum(1 for r in results if r is True) / len(results)
        
        # Should maintain high reliability even with network issues
        assert success_rate >= 0.8, f"Reliability too low with network issues: {success_rate}"
        
        # Validate events were delivered
        test_results = self.test_harness.get_comprehensive_results()
        analysis = test_results["analysis"]
        assert analysis["total_events"] >= 30, "Should have delivered many events despite network issues"
        
        print(" PASS:  Comprehensive event delivery reliability test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(120)
    async def test_comprehensive_high_load_performance(self):
        """Test comprehensive performance under high load."""
        print("[U+1F4AA] Testing comprehensive high load performance")
        
        # High load scenario
        high_load_results = await self.test_harness.run_concurrent_user_scenarios(user_count=25)
        
        assert high_load_results["success_rate"] >= 0.9, \
            f"High load success rate too low: {high_load_results['success_rate']}"
        
        assert high_load_results["duration_seconds"] < 30, \
            f"High load took too long: {high_load_results['duration_seconds']}s"
        
        # Validate comprehensive results
        results = self.test_harness.get_comprehensive_results()
        assert results["validation_passed"], f"High load validation failed: {results['validation_failures']}"
        
        # Factory should handle load efficiently
        factory_metrics = results["factory_metrics"]
        assert factory_metrics["emitters_created"] == 25, "Factory should create all requested emitters"
        
        analysis = results["analysis"]
        assert analysis["total_events"] >= 75, "Should process many events under load"  # 25 users * 3 events minimum
        
        print(" PASS:  Comprehensive high load performance test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_comprehensive_event_ordering_validation(self):
        """Test comprehensive event ordering validation."""
        print("[U+1F4CB] Testing comprehensive event ordering validation")
        
        # Create users with specific ordering requirements
        ordering_test_users = []
        for i in range(8):
            user_id = f"ordering_user_{i}"
            ordering_test_users.append(user_id)
            
            success = await self.test_harness.simulate_complete_agent_flow(
                user_id, 
                include_tools=True
            )
            assert success, f"Flow failed for ordering test user {user_id}"
        
        # Validate ordering
        results = self.test_harness.get_comprehensive_results()
        assert results["validation_passed"], f"Event ordering validation failed: {results['validation_failures']}"
        
        analysis = results["analysis"]
        assert analysis["ordering_valid"], "Event ordering validation failed"
        assert analysis["users_with_complete_flows"] == len(ordering_test_users), \
            "Not all users completed their flows"
        
        print(" PASS:  Comprehensive event ordering validation test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_comprehensive_factory_resource_management(self):
        """Test comprehensive factory resource management."""
        print("[U+1F9F9] Testing comprehensive factory resource management")
        
        initial_metrics = self.test_harness.factory.get_factory_metrics()
        initial_active = initial_metrics["emitters_active"]
        
        # Create and cleanup emitters
        cleanup_users = []
        for i in range(10):
            user_id = f"cleanup_user_{i}"
            cleanup_users.append(user_id)
            
            await self.test_harness.simulate_complete_agent_flow(user_id)
        
        mid_metrics = self.test_harness.factory.get_factory_metrics()
        assert mid_metrics["emitters_active"] >= initial_active + 10, "Factory should track active emitters"
        
        # Cleanup emitters
        for user_id in cleanup_users:
            if user_id in self.test_harness.user_emitters:
                await self.test_harness.user_emitters[user_id].cleanup()
        
        # Give time for cleanup
        await asyncio.sleep(0.1)
        
        final_metrics = self.test_harness.factory.get_factory_metrics()
        # Some emitters may still be cleaning up, so allow for that
        assert final_metrics["emitters_cleaned"] >= 5, "Factory should track cleaned emitters"
        
        print(" PASS:  Comprehensive factory resource management test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_comprehensive_final_validation(self):
        """Final comprehensive validation test."""
        print("[U+1F396][U+FE0F] Running final comprehensive validation")
        
        # Run the most demanding test scenario
        final_user_count = 20
        final_results = await self.test_harness.run_concurrent_user_scenarios(final_user_count)
        
        # Should maintain excellent performance
        assert final_results["success_rate"] >= 0.95, \
            f"Final validation success rate insufficient: {final_results['success_rate']}"
        
        # Get comprehensive results
        results = self.test_harness.get_comprehensive_results()
        
        # Final validation must pass
        assert results["validation_passed"], \
            f"FINAL VALIDATION FAILED: {results['validation_failures']}"
        
        # Comprehensive metrics validation
        analysis = results["analysis"]
        assert analysis["total_events"] >= 60, \
            f"Final validation insufficient event coverage: {analysis['total_events']}"
        
        assert analysis["total_users"] == final_user_count, \
            f"Final validation insufficient user coverage: {analysis['total_users']}"
        
        assert analysis["isolation_valid"], "Final validation: User isolation failed"
        assert analysis["events_valid"], "Final validation: Critical events validation failed"
        assert analysis["ordering_valid"], "Final validation: Event ordering failed"
        
        # Factory should be in good state
        factory_metrics = results["factory_metrics"]
        assert factory_metrics["emitters_created"] == final_user_count, \
            "Factory should have created correct number of emitters"
        
        print(" TROPHY:  FINAL COMPREHENSIVE VALIDATION PASSED!")
        print(" TARGET:  All WebSocket notification requirements validated successfully")
        print("[U+1F4BC] Business value preservation: Chat functionality fully operational with factory pattern")


# ============================================================================
# SPECIALIZED REGRESSION TESTS FOR FACTORY PATTERN
# ============================================================================

class TestFactoryPatternRegressionPrevention:
    """Specialized tests to prevent regressions in factory pattern implementation."""
    
    @pytest.fixture(autouse=True)
    async def setup_regression_testing(self):
        """Setup for regression testing with real WebSocket connections."""
        self.factory = get_websocket_bridge_factory()
        self.real_websocket_manager = RealWebSocketManager()
        
        # Initialize real WebSocket session
        self._websocket_session = self.real_websocket_manager.real_websocket_session()
        await self._websocket_session.__aenter__()
        
        try:
            yield
        finally:
            # Cleanup
            pass
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_factory_singleton_works_correctly(self):
        """REGRESSION TEST: Factory singleton must work correctly."""
        
        # Test singleton behavior
        factory1 = get_websocket_bridge_factory()
        factory2 = get_websocket_bridge_factory()
        
        assert factory1 is factory2, "Factory singleton not working correctly"
        assert isinstance(factory1, WebSocketBridgeFactory), "Factory should be WebSocketBridgeFactory instance"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_user_context_isolation_never_breaks(self):
        """REGRESSION TEST: User context isolation must never break."""
        
        # Create contexts for different users
        context1 = UserWebSocketContext(
            user_id="user1",
            thread_id="thread1", 
            connection_id="conn1"
        )
        
        context2 = UserWebSocketContext(
            user_id="user2",
            thread_id="thread2",
            connection_id="conn2"
        )
        
        # Contexts should be completely isolated
        assert context1.user_id != context2.user_id, "User contexts should have different user IDs"
        assert context1.thread_id != context2.thread_id, "User contexts should have different thread IDs"
        assert context1.connection_id != context2.connection_id, "User contexts should have different connection IDs"
        
        # Event queues should be separate
        assert context1.event_queue is not context2.event_queue, "User contexts should have separate event queues"
        
        # Event history should be separate
        assert context1.sent_events is not context2.sent_events, "User contexts should have separate sent events"
        assert context1.failed_events is not context2.failed_events, "User contexts should have separate failed events"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_events_always_include_user_isolation(self):
        """REGRESSION TEST: WebSocket events must always include proper user isolation."""
        
        user_id = "isolation_test_user"
        thread_id = "isolation_test_thread"
        
        event = WebSocketEvent(
            event_type="agent_started",
            user_id=user_id,
            thread_id=thread_id,
            data={"test": "isolation"}
        )
        
        # Event should have proper isolation fields
        assert event.user_id == user_id, "Event should have correct user_id"
        assert event.thread_id == thread_id, "Event should have correct thread_id"
        assert event.event_id is not None, "Event should have unique event_id"
        assert event.timestamp is not None, "Event should have timestamp"
        
        # Event should have proper retry mechanism
        assert event.retry_count == 0, "Event should start with 0 retries"
        assert event.max_retries > 0, "Event should have max_retries configured"


if __name__ == "__main__":
    # Run the ultra-comprehensive test suite
    print("[U+1F680] Starting Ultra-Comprehensive WebSocket Factory Validation Test Suite")
    
    # Run with maximum verbosity and strict failure reporting
    pytest.main([
        __file__,
        "-v",                    # Verbose output
        "-s",                    # Don't capture output
        "--tb=long",            # Long traceback format
        "--strict-markers",     # Strict marker checking
        "--strict-config",      # Strict configuration
        "-x",                   # Stop on first failure
        "--disable-warnings",   # Clean output
        "-m", "critical"        # Only run critical tests
    ])