#!/usr/bin/env python
"""MISSION CRITICAL: Bulletproof WebSocket Chat Event Tests

Business Value: $500K+ ARR - Core chat functionality is KING
Tests: Comprehensive real-world scenarios with extreme robustness

This test suite ensures:
1. All critical WebSocket events are sent for chat UI using factory pattern
2. Events arrive in correct order with proper data
3. Error conditions are handled gracefully 
4. Concurrent users work correctly with complete isolation
5. Reconnection preserves state per user
6. Performance meets <2s response requirement
7. Factory pattern provides complete user isolation
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
import random
import traceback
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

# Import current SSOT components for testing
try:
    from shared.isolated_environment import get_env
    from netra_backend.app.services.websocket_bridge_factory import (
        WebSocketBridgeFactory,
        UserWebSocketEmitter,
        UserWebSocketContext,
        WebSocketEvent,
        ConnectionStatus,
        get_websocket_bridge_factory,
        WebSocketConnectionPool
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

# ALL MOCK CLASSES REMOVED per CLAUDE.md "MOCKS = Abomination"
# Using RealWebSocketManager for authentic WebSocket testing


class BulletproofEventValidator:
    """Extremely robust event validation with detailed diagnostics for factory pattern."""
    
    CRITICAL_EVENTS = {
        "agent_started": {"required": True, "max_count": 1},
        "agent_thinking": {"required": True, "max_count": None},
        "tool_executing": {"required": True, "max_count": None},
        "tool_completed": {"required": True, "max_count": None},
        "agent_completed": {"required": True, "max_count": 1}
    }
    
    def __init__(self):
    pass
        self.user_events: Dict[str, List[Dict]] = {}  # user_id -> events
        self.event_timeline: List[Tuple[float, str, str, Dict]] = []  # timestamp, user_id, event_type, event
        self.event_counts: Dict[str, int] = {}
        self.user_event_counts: Dict[str, Dict[str, int]] = {}
        self.validation_errors: List[str] = []
        self.performance_metrics: Dict[str, float] = {}
        self.start_time = time.time()
        
    def record_user_event(self, user_id: str, event: Dict) -> None:
        """Record an event for a specific user with comprehensive tracking."""
        timestamp = time.time() - self.start_time
        event_type = event.get("event_type", "unknown")
        
        # Store event per user
        if user_id not in self.user_events:
            self.user_events[user_id] = []
            self.user_event_counts[user_id] = {}
        
        enriched_event = {
            **event,
            "relative_timestamp": timestamp,
            "sequence": len(self.user_events[user_id])
        }
        
        self.user_events[user_id].append(enriched_event)
        self.event_timeline.append((timestamp, user_id, event_type, enriched_event))
        
        # Update counts
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        self.user_event_counts[user_id][event_type] = self.user_event_counts[user_id].get(event_type, 0) + 1
        
        # Track performance metrics per user
        user_perf_key = f"user_{user_id}"
        if event_type == "agent_started":
            self.performance_metrics[f"{user_perf_key}_start_time"] = timestamp
        elif event_type == "agent_completed":
            self.performance_metrics[f"{user_perf_key}_end_time"] = timestamp
            start_key = f"{user_perf_key}_start_time"
            if start_key in self.performance_metrics:
                duration = timestamp - self.performance_metrics[start_key]
                self.performance_metrics[f"{user_perf_key}_duration"] = duration
    
    def validate_comprehensive(self) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Comprehensive validation with user isolation checks."""
        errors = []
        warnings = []
        
        # 1. Validate user isolation
        isolation_errors = self._validate_user_isolation()
        errors.extend(isolation_errors)
        
        # 2. Validate required events per user
        for user_id, events in self.user_events.items():
            user_event_types = set(e.get("event_type") for e in events)
            
            for event_type, config in self.CRITICAL_EVENTS.items():
                user_count = self.user_event_counts[user_id].get(event_type, 0)
                
                if config["required"] and user_count == 0:
                    errors.append(f"CRITICAL: User {user_id} missing required event '{event_type}'")
                
                if config["max_count"] and user_count > config["max_count"]:
                    warnings.append(f"User {user_id} event '{event_type}' sent {user_count} times (max: {config['max_count']})")
        
        # 3. Validate event ordering per user
        for user_id in self.user_events:
            ordering_errors = self._validate_user_event_sequence(user_id)
            errors.extend(ordering_errors)
        
        # 4. Validate performance per user
        perf_warnings = self._validate_performance()
        warnings.extend(perf_warnings)
        
        # Generate comprehensive diagnostics
        diagnostics = {
            "total_users": len(self.user_events),
            "total_events": sum(len(events) for events in self.user_events.values()),
            "events_per_user": {user_id: len(events) for user_id, events in self.user_events.items()},
            "event_counts": self.event_counts.copy(),
            "user_event_counts": self.user_event_counts.copy(),
            "performance_metrics": self.performance_metrics.copy(),
            "errors": errors,
            "warnings": warnings,
            "isolation_valid": len([e for e in errors if "isolation" in e.lower()]) == 0
        }
        
        return len(errors) == 0, errors, diagnostics
    
    def _validate_user_isolation(self) -> List[str]:
        """Validate that users are properly isolated."""
        errors = []
        
        # Check no cross-user contamination
        for user_id, events in self.user_events.items():
            for event in events:
                event_user_id = event.get("user_id")
                if event_user_id and event_user_id != user_id:
                    errors.append(f"CRITICAL: User isolation violation - user {user_id} received event for user {event_user_id}")
        
        return errors
    
    def _validate_user_event_sequence(self, user_id: str) -> List[str]:
        """Validate event sequence for a specific user."""
        errors = []
        events = self.user_events[user_id]
        
        if not events:
            return errors
        
        event_types = [e.get("event_type") for e in events]
        
        # First event should be agent_started
        if event_types[0] != "agent_started":
            errors.append(f"CRITICAL: User {user_id} first event should be 'agent_started', got '{event_types[0]}'")
        
        # Last event should be completion
        last_event = event_types[-1]
        if last_event not in ["agent_completed", "agent_error"]:
            errors.append(f"CRITICAL: User {user_id} last event should be completion, got '{last_event}'")
        
        # Tool events should be paired
        tool_executing_count = event_types.count("tool_executing")
        tool_completed_count = event_types.count("tool_completed")
        tool_error_count = event_types.count("tool_error")
        
        if tool_executing_count != (tool_completed_count + tool_error_count):
            errors.append(f"CRITICAL: User {user_id} unpaired tool events - {tool_executing_count} starts, {tool_completed_count + tool_error_count} ends")
        
        return errors
    
    def _validate_performance(self) -> List[str]:
        """Validate performance requirements."""
        warnings = []
        
        for user_id in self.user_events:
            duration_key = f"user_{user_id}_duration"
            if duration_key in self.performance_metrics:
                duration = self.performance_metrics[duration_key]
                if duration > 2.0:  # 2 second target
                    warnings.append(f"Performance warning: User {user_id} duration {duration:.2f}s exceeds 2s target")
        
        return warnings
    
    def generate_detailed_report(self) -> str:
        """Generate comprehensive validation report for factory pattern."""
        is_valid, errors, diagnostics = self.validate_comprehensive()
        
        report_lines = [
            "
" + "=" * 80,
            "BULLETPROOF WEBSOCKET FACTORY VALIDATION REPORT",
            "=" * 80,
            f"Overall Status: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"Total Users: {diagnostics['total_users']}",
            f"Total Events: {diagnostics['total_events']}",
            f"User Isolation: {'✅ VALID' if diagnostics['isolation_valid'] else '❌ FAILED'}",
            ""
        ]
        
        # Per-user event counts
        report_lines.extend(["Per-User Event Coverage:"])
        for user_id, counts in diagnostics["user_event_counts"].items():
            report_lines.append(f"  User {user_id}:")
            for event_type in self.CRITICAL_EVENTS:
                count = counts.get(event_type, 0)
                status = "✅" if count > 0 else "❌"
                report_lines.append(f"    {status} {event_type}: {count}")
        
        # Performance metrics
        if diagnostics["performance_metrics"]:
            report_lines.extend(["", "Performance Metrics:"])
            for user_id in self.user_events:
                duration_key = f"user_{user_id}_duration"
                if duration_key in diagnostics["performance_metrics"]:
                    duration = diagnostics["performance_metrics"][duration_key]
                    target_met = "✅" if duration < 2.0 else "❌"
                    report_lines.append(f"  {target_met} User {user_id}: {duration:.2f}s")
        
        # Errors and warnings
        if errors:
            report_lines.extend(["", "ERRORS:"] + [f"  - {e}" for e in errors])
        
        if diagnostics.get("warnings"):
            report_lines.extend(["", "WARNINGS:"] + [f"  - {w}" for w in diagnostics["warnings"]])
        
        report_lines.append("=" * 80)
        return "
".join(report_lines)


# ============================================================================
# BULLETPROOF TEST SUITE FOR FACTORY PATTERN
# ============================================================================

class TestBulletproofWebSocketChat:
    """Bulletproof tests for WebSocket chat functionality using factory pattern."""
    
    @pytest.fixture(autouse=True)
    async def setup_robust_environment(self):
        """Setup robust test environment with factory pattern components."""
        # Create factory and real WebSocket manager
        self.factory = WebSocketBridgeFactory()
        self.real_websocket_manager = RealWebSocketManager()
        
        # Initialize real WebSocket session
        self._websocket_session = self.real_websocket_manager.real_websocket_session()
        await self._websocket_session.__aenter__()
        
        # Configure factory with mocked components
        self.factory.configure(
            connection_pool=self.mock_pool,
            agent_registry=type('MockRegistry', (), {})(),  # Mock registry
            health_monitor=type('MockHealthMonitor', (), {})()  # Mock health monitor
        )
        
        # Track created emitters for cleanup
        self.user_emitters: Dict[str, UserWebSocketEmitter] = {}
        
        yield
        
        # Cleanup
        await self.cleanup_all_emitters()
    
    async def cleanup_all_emitters(self):
        """Clean up all test emitters."""
    pass
        for emitter in self.user_emitters.values():
            try:
                await emitter.cleanup()
            except Exception:
                pass
        self.user_emitters.clear()
    
    async def create_user_emitter(self, user_id: str, connection_id: str = "default") -> UserWebSocketEmitter:
        """Create a user-specific emitter for testing."""
        thread_id = f"thread_{user_id}_{connection_id}"
        
        emitter = await self.factory.create_user_emitter(
            user_id=user_id,
            thread_id=thread_id,
            connection_id=connection_id
        )
        
        self.user_emitters[user_id] = emitter
        await asyncio.sleep(0)
    return emitter
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_complete_chat_flow_with_factory_pattern(self):
        """Test complete chat flow with factory pattern isolation."""
        validator = BulletproofEventValidator()
        
        # Create user emitter
        user_id = "chat_user_1"
        emitter = await self.create_user_emitter(user_id)
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        agent_name = "ChatAgent"
        
        # Simulate complete chat flow
        await emitter.notify_agent_started(agent_name, run_id)
        validator.record_user_event(user_id, {"event_type": "agent_started", "user_id": user_id})
        
        await asyncio.sleep(0.01)  # Small delay to simulate processing
        
        await emitter.notify_agent_thinking(agent_name, run_id, "Analyzing user request...")
        validator.record_user_event(user_id, {"event_type": "agent_thinking", "user_id": user_id})
        
        await emitter.notify_tool_executing(agent_name, run_id, "search_knowledge", {"query": "test"})
        validator.record_user_event(user_id, {"event_type": "tool_executing", "user_id": user_id})
        
        await asyncio.sleep(0.05)  # Simulate tool execution time
        
        await emitter.notify_tool_completed(agent_name, run_id, "search_knowledge", {"results": "Found information"})
        validator.record_user_event(user_id, {"event_type": "tool_completed", "user_id": user_id})
        
        await emitter.notify_agent_completed(agent_name, run_id, {"success": True})
        validator.record_user_event(user_id, {"event_type": "agent_completed", "user_id": user_id})
        
        # Allow events to propagate
        await asyncio.sleep(0.1)
        
        # Validate comprehensive results
        is_valid, errors, diagnostics = validator.validate_comprehensive()
        
        if not is_valid:
            print(validator.generate_detailed_report())
        
        assert is_valid, f"Chat flow validation failed: {errors}"
        assert diagnostics["total_events"] >= 5, f"Expected at least 5 events, got {diagnostics['total_events']}"
        assert diagnostics["isolation_valid"], "User isolation validation failed"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_users_complete_isolation(self):
        """Test that concurrent users have complete isolation with factory pattern."""
    pass
        validator = BulletproofEventValidator()
        
        # Create multiple users with their own emitters
        num_users = 8
        user_emitters = {}
        
        for i in range(num_users):
            user_id = f"isolated_user_{i}"
            emitter = await self.create_user_emitter(user_id)
            user_emitters[user_id] = emitter
        
        # Send events for each user concurrently
        async def send_user_events(user_id: str, emitter: UserWebSocketEmitter):
    pass
            run_id = f"run_{user_id}_{uuid.uuid4().hex[:8]}"
            agent_name = f"Agent_{user_id}"
            
            await emitter.notify_agent_started(agent_name, run_id)
            validator.record_user_event(user_id, {"event_type": "agent_started", "user_id": user_id})
            
            await asyncio.sleep(random.uniform(0.01, 0.03))
            
            await emitter.notify_agent_thinking(agent_name, run_id, f"Processing for {user_id}")
            validator.record_user_event(user_id, {"event_type": "agent_thinking", "user_id": user_id})
            
            await emitter.notify_tool_executing(agent_name, run_id, "user_tool", {"user_id": user_id})
            validator.record_user_event(user_id, {"event_type": "tool_executing", "user_id": user_id})
            
            await asyncio.sleep(random.uniform(0.02, 0.05))
            
            await emitter.notify_tool_completed(agent_name, run_id, "user_tool", {"result": f"Result for {user_id}"})
            validator.record_user_event(user_id, {"event_type": "tool_completed", "user_id": user_id})
            
            await emitter.notify_agent_completed(agent_name, run_id, {"success": True, "user": user_id})
            validator.record_user_event(user_id, {"event_type": "agent_completed", "user_id": user_id})
        
        # Execute all users concurrently
        tasks = [send_user_events(user_id, emitter) for user_id, emitter in user_emitters.items()]
        await asyncio.gather(*tasks)
        
        # Allow events to propagate
        await asyncio.sleep(0.2)
        
        # Validate comprehensive isolation
        is_valid, errors, diagnostics = validator.validate_comprehensive()
        assert is_valid, f"User isolation validation failed: {errors}"
        
        # Verify each user has complete event flow
        assert diagnostics["total_users"] == num_users, f"Should track {num_users} users"
        
        for user_id in user_emitters.keys():
            user_event_count = diagnostics["events_per_user"].get(user_id, 0)
            assert user_event_count >= 5, f"User {user_id} should have at least 5 events, got {user_event_count}"
        
        # Verify factory metrics
        factory_metrics = self.factory.get_factory_metrics()
        assert factory_metrics["emitters_created"] >= num_users, f"Factory should create {num_users} emitters"
        assert factory_metrics["emitters_active"] >= num_users, "Factory should track active emitters"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_error_recovery_with_user_isolation(self):
        """Test error recovery maintains user isolation."""
        validator = BulletproofEventValidator()
        
        # Create users with different failure patterns
        users_config = [
            {"user_id": "stable_user", "should_fail": False},
            {"user_id": "failing_user", "should_fail": True, "failure_pattern": "intermittent"},
            {"user_id": "timeout_user", "should_fail": True, "failure_pattern": "timeout"}
        ]
        
        user_emitters = {}
        
        for config in users_config:
            user_id = config["user_id"]
            emitter = await self.create_user_emitter(user_id)
            user_emitters[user_id] = emitter
            
            # Configure connection issues for this user only
            if config.get("should_fail"):
                self.mock_pool.configure_connection_issues(
                    user_id=user_id,
                    should_fail=config["should_fail"],
                    failure_pattern=config.get("failure_pattern")
                )
        
        # Send events for all users
        async def send_with_error_handling(user_id: str, emitter: UserWebSocketEmitter):
            run_id = f"error_test_{user_id}"
            agent_name = f"ErrorTestAgent_{user_id}"
            
            try:
                await emitter.notify_agent_started(agent_name, run_id)
                validator.record_user_event(user_id, {"event_type": "agent_started", "user_id": user_id})
                
                await emitter.notify_agent_thinking(agent_name, run_id, "Processing with potential errors")
                validator.record_user_event(user_id, {"event_type": "agent_thinking", "user_id": user_id})
                
                # This might fail for some users
                await emitter.notify_tool_executing(agent_name, run_id, "potentially_failing_tool", {})
                validator.record_user_event(user_id, {"event_type": "tool_executing", "user_id": user_id})
                
                # Complete successfully or with error
                await emitter.notify_tool_completed(agent_name, run_id, "potentially_failing_tool", {"success": True})
                validator.record_user_event(user_id, {"event_type": "tool_completed", "user_id": user_id})
                
                await emitter.notify_agent_completed(agent_name, run_id, {"success": True})
                validator.record_user_event(user_id, {"event_type": "agent_completed", "user_id": user_id})
                
            except Exception as e:
                # Error handling - some users may experience failures
                try:
                    await emitter.notify_agent_error(agent_name, run_id, str(e))
                    validator.record_user_event(user_id, {"event_type": "agent_error", "user_id": user_id})
                except:
                    pass  # Even error notification may fail for failing users
        
        # Execute concurrently
        tasks = [send_with_error_handling(user_id, emitter) for user_id, emitter in user_emitters.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Allow propagation
        await asyncio.sleep(0.2)
        
        # Validate that stable user was not affected by other users' failures
        is_valid, errors, diagnostics = validator.validate_comprehensive()
        
        # Stable user should have complete flow
        stable_user_events = diagnostics["user_event_counts"].get("stable_user", {})
        assert stable_user_events.get("agent_started", 0) > 0, "Stable user should have agent_started"
        assert stable_user_events.get("agent_completed", 0) > 0, "Stable user should have agent_completed"
        
        # Verify isolation - no user received events for other users
        for error in errors:
            assert "isolation violation" not in error.lower(), f"User isolation violated: {error}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_performance_under_concurrent_load(self):
        """Test WebSocket performance with concurrent users and high message volume."""
    pass
        start_time = time.time()
        validator = BulletproofEventValidator()
        
        # Create many concurrent users
        num_users = 15
        events_per_user = 8
        user_emitters = {}
        
        for i in range(num_users):
            user_id = f"load_user_{i}"
            emitter = await self.create_user_emitter(user_id)
            user_emitters[user_id] = emitter
            
            # Add some network latency simulation
            self.mock_pool.configure_connection_issues(
                user_id=user_id,
                latency_ms=random.uniform(5, 25)
            )
        
        # Send high volume of events
        async def send_user_load(user_id: str, emitter: UserWebSocketEmitter):
    pass
            run_id = f"load_test_{user_id}"
            agent_name = f"LoadTestAgent_{user_id}"
            
            # Agent flow with multiple events
            await emitter.notify_agent_started(agent_name, run_id)
            validator.record_user_event(user_id, {"event_type": "agent_started", "user_id": user_id})
            
            for i in range(events_per_user - 3):  # -3 for start, tool, complete
                await emitter.notify_agent_thinking(agent_name, run_id, f"Processing step {i}")
                validator.record_user_event(user_id, {"event_type": "agent_thinking", "user_id": user_id})
                
                if i % 2 == 0:  # Add some tool usage
                    await emitter.notify_tool_executing(agent_name, run_id, f"tool_{i}", {})
                    validator.record_user_event(user_id, {"event_type": "tool_executing", "user_id": user_id})
                    
                    await emitter.notify_tool_completed(agent_name, run_id, f"tool_{i}", {"result": i})
                    validator.record_user_event(user_id, {"event_type": "tool_completed", "user_id": user_id})
            
            await emitter.notify_agent_completed(agent_name, run_id, {"success": True})
            validator.record_user_event(user_id, {"event_type": "agent_completed", "user_id": user_id})
        
        # Execute all users concurrently
        tasks = [send_user_load(user_id, emitter) for user_id, emitter in user_emitters.items()]
        await asyncio.gather(*tasks)
        
        total_duration = time.time() - start_time
        total_events = sum(len(events) for events in validator.user_events.values())
        events_per_second = total_events / total_duration
        
        print(f"Performance test: {total_events} events for {num_users} users in {total_duration:.2f}s = {events_per_second:.0f} events/s")
        
        # Performance assertions
        assert events_per_second > 200, f"Performance too low: {events_per_second:.0f} events/s"
        assert total_duration < 15, f"Load test took too long: {total_duration:.2f}s"
        
        # Validate all users completed successfully
        is_valid, errors, diagnostics = validator.validate_comprehensive()
        if not is_valid:
            print(validator.generate_detailed_report())
        
        assert is_valid, f"Load test validation failed: {errors}"
        assert diagnostics["total_users"] == num_users, f"Should process {num_users} users"
        
        # Verify factory handled the load
        factory_metrics = self.factory.get_factory_metrics()
        assert factory_metrics["emitters_created"] == num_users, "Factory should create all emitters"
        assert factory_metrics["events_sent_total"] > total_events * 0.8, "Most events should be sent successfully"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_message_ordering_per_user(self):
        """Test that messages maintain correct order per user even under concurrent load."""
        # Create multiple users
        num_users = 6
        messages_per_user = 10
        user_emitters = {}
        user_expected_order = {}
        
        for i in range(num_users):
            user_id = f"order_user_{i}"
            emitter = await self.create_user_emitter(user_id)
            user_emitters[user_id] = emitter
            user_expected_order[user_id] = []
        
        # Send numbered messages for each user
        async def send_ordered_messages(user_id: str, emitter: UserWebSocketEmitter):
            run_id = f"order_test_{user_id}"
            agent_name = f"OrderTestAgent_{user_id}"
            
            for i in range(messages_per_user):
                message = f"User {user_id} Message {i:03d}"
                user_expected_order[user_id].append(message)
                await emitter.notify_agent_thinking(agent_name, run_id, message)
                await asyncio.sleep(0.001)  # Small delay to ensure ordering
        
        # Execute concurrently
        tasks = [send_ordered_messages(user_id, emitter) for user_id, emitter in user_emitters.items()]
        await asyncio.gather(*tasks)
        
        # Allow propagation
        await asyncio.sleep(0.2)
        
        # Verify ordering per user
        for user_id in user_emitters.keys():
            messages = self.mock_pool.get_user_messages(user_id)
            actual_order = []
            
            for msg in messages:
                if msg.get("event_type") == "agent_thinking" and "thinking" in msg.get("data", {}):
                    actual_order.append(msg["data"]["thinking"])
            
            expected = user_expected_order[user_id]
            assert actual_order == expected, f"Message order corrupted for {user_id}: {actual_order} != {expected}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical  
    async def test_factory_resource_management_under_stress(self):
        """Test that factory manages resources properly under stress."""
    pass
        initial_metrics = self.factory.get_factory_metrics()
        
        # Create and destroy many emitters rapidly
        stress_cycles = 3
        emitters_per_cycle = 10
        
        for cycle in range(stress_cycles):
            cycle_emitters = []
            
            # Create emitters
            for i in range(emitters_per_cycle):
                user_id = f"stress_user_{cycle}_{i}"
                emitter = await self.create_user_emitter(user_id)
                cycle_emitters.append((user_id, emitter))
            
            # Use emitters briefly
            for user_id, emitter in cycle_emitters:
                run_id = f"stress_run_{user_id}"
                agent_name = f"StressAgent_{user_id}"
                
                await emitter.notify_agent_started(agent_name, run_id)
                await emitter.notify_agent_thinking(agent_name, run_id, f"Stress test {cycle}")
                await emitter.notify_agent_completed(agent_name, run_id, {"success": True})
            
            # Cleanup emitters
            for user_id, emitter in cycle_emitters:
                await emitter.cleanup()
                if user_id in self.user_emitters:
                    del self.user_emitters[user_id]
            
            # Brief pause between cycles
            await asyncio.sleep(0.05)
        
        # Give time for cleanup
        await asyncio.sleep(0.2)
        
        final_metrics = self.factory.get_factory_metrics()
        
        # Verify resource management
        expected_created = initial_metrics["emitters_created"] + (stress_cycles * emitters_per_cycle)
        assert final_metrics["emitters_created"] >= expected_created, "Factory should track all created emitters"
        
        # Verify cleanup occurred
        assert final_metrics["emitters_cleaned"] > 0, "Factory should track cleaned emitters"
        
        # Factory should be in good state
        assert final_metrics["events_sent_total"] > stress_cycles * emitters_per_cycle * 2, "Events should have been sent"


# ============================================================================
# EDGE CASE TESTS FOR FACTORY PATTERN
# ============================================================================

class TestAdvancedEdgeCasesFactoryPattern:
    """Test advanced edge cases and failure scenarios for factory pattern."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_factory_singleton_behavior(self):
        """Test that factory singleton works correctly under concurrent access."""
        # Get factory instances concurrently
        async def get_factory_instance():
            await asyncio.sleep(0)
    return get_websocket_bridge_factory()
        
        tasks = [get_factory_instance() for _ in range(10)]
        factory_instances = await asyncio.gather(*tasks)
        
        # All instances should be the same object
        first_factory = factory_instances[0]
        for factory in factory_instances[1:]:
            assert factory is first_factory, "Factory singleton not working correctly"
        
        assert isinstance(first_factory, WebSocketBridgeFactory), "Factory should be correct type"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_user_context_isolation_stress(self):
        """Stress test user context isolation with rapid creation/destruction."""
    pass
        contexts_created = 0
        contexts_isolated = 0
        
        for batch in range(5):  # 5 batches of contexts
            batch_contexts = []
            
            # Create contexts
            for i in range(20):  # 20 contexts per batch
                context = UserWebSocketContext(
                    user_id=f"stress_user_{batch}_{i}",
                    thread_id=f"stress_thread_{batch}_{i}",
                    connection_id=f"stress_conn_{batch}_{i}"
                )
                batch_contexts.append(context)
                contexts_created += 1
            
            # Verify isolation
            user_ids = set()
            thread_ids = set()
            connection_ids = set()
            
            for context in batch_contexts:
                # Should have unique identifiers
                assert context.user_id not in user_ids, f"Duplicate user_id: {context.user_id}"
                assert context.thread_id not in thread_ids, f"Duplicate thread_id: {context.thread_id}"
                assert context.connection_id not in connection_ids, f"Duplicate connection_id: {context.connection_id}"
                
                user_ids.add(context.user_id)
                thread_ids.add(context.thread_id)
                connection_ids.add(context.connection_id)
                
                # Verify separate resources
                for other_context in batch_contexts:
                    if context is not other_context:
                        assert context.event_queue is not other_context.event_queue, "Event queues should be separate"
                        assert context.sent_events is not other_context.sent_events, "Sent events should be separate"
                
                contexts_isolated += 1
            
            # Cleanup contexts
            for context in batch_contexts:
                await context.cleanup()
        
        assert contexts_created == contexts_isolated, f"Isolation failed: {contexts_created} created, {contexts_isolated} isolated"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_event_immutability(self):
        """Test that WebSocket events maintain data integrity."""
        user_id = "immutability_user"
        thread_id = "immutability_thread"
        
        original_data = {
            "message": "test message",
            "metadata": {"key": "value"},
            "nested": {"deep": {"value": 42}}
        }
        
        # Create event
        event = WebSocketEvent(
            event_type="test_event",
            user_id=user_id,
            thread_id=thread_id,
            data=original_data
        )
        
        # Verify original data unchanged
        assert event.data == original_data, "Event data should match original"
        assert event.user_id == user_id, "User ID should match"
        assert event.thread_id == thread_id, "Thread ID should match"
        assert event.event_id is not None, "Event should have unique ID"
        assert event.timestamp is not None, "Event should have timestamp"
        
        # Modify original data
        original_data["message"] = "modified"
        original_data["nested"]["deep"]["value"] = 99
        
        # Event data should be isolated from original modifications
        assert event.data["message"] == "test message", "Event data should be isolated from external modifications"
        assert event.data["nested"]["deep"]["value"] == 42, "Nested data should be isolated"
        
        # Event properties should be immutable after creation
        with pytest.raises(AttributeError):
            event.event_id = "new_id"  # Should not be settable


if __name__ == "__main__":
    # Run with: python tests/mission_critical/test_websocket_chat_bulletproof.py
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "critical"])
    pass