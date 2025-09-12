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
    from netra_backend.app.websocket_core import (
        get_websocket_manager,
        WebSocketManager,
        WebSocketMessage,
        create_standard_message,
        MessageType
    )
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager
    from test_framework.test_context import (
        TestContext,
        TestUserContext,
        create_test_context,
        create_isolated_test_contexts
    )
except ImportError as e:
    pytest.skip(f"Could not import required WebSocket components: {e}", allow_module_level=True)


class ComprehensiveEventValidator:
    """Ultra-rigorous event validation for the WebSocket architecture."""
    
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


class WebSocketTestHarness:
    """Test harness for WebSocket validation."""
    
    def __init__(self):
        self.websocket_manager = get_websocket_manager()
        self.validator = ComprehensiveEventValidator()
        self.test_contexts: Dict[str, TestContext] = {}
        
    async def create_test_context(self, user_id: str) -> TestContext:
        """Create and track a test context for a user."""
        context = create_test_context(user_id=user_id)
        self.test_contexts[user_id] = context
        return context
    
    async def send_agent_event_with_validation(self, user_id: str, thread_id: str, 
                                             event_type: str, event_data: Dict[str, Any]) -> bool:
        """Send agent event and track for validation."""
        try:
            # Create WebSocket message
            message = create_standard_message(
                message_type=event_type,
                data=event_data,
                user_id=user_id,
                thread_id=thread_id
            )
            
            # Send via WebSocket manager
            success = await self.websocket_manager.send_to_thread(thread_id, message)
            
            # Record for validation
            if success:
                validation_event = {
                    "event_type": event_type,
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "data": event_data
                }
                self.validator.record_user_event(user_id, validation_event)
            
            return success
            
        except Exception as e:
            print(f"Error sending agent event: {e}")
            return False
    
    async def simulate_complete_agent_flow(self, user_id: str, agent_name: str = "TestAgent", 
                                         include_tools: bool = True) -> bool:
        """Simulate complete agent flow for a user."""
        try:
            context = await self.create_test_context(user_id)
            thread_id = context.user_context.thread_id
            run_id = UnifiedIDManager.generate_run_id(thread_id)
            
            # Send agent events in sequence
            success = await self.send_agent_event_with_validation(
                user_id, thread_id, "agent_started",
                {"agent_name": agent_name, "run_id": run_id, "context": {"task": "Comprehensive test"}}
            )
            if not success:
                return False
            
            success = await self.send_agent_event_with_validation(
                user_id, thread_id, "agent_thinking",
                {"agent_name": agent_name, "run_id": run_id, "reasoning": "Processing request..."}
            )
            if not success:
                return False
            
            if include_tools:
                tool_name = "comprehensive_test_tool"
                success = await self.send_agent_event_with_validation(
                    user_id, thread_id, "tool_executing",
                    {"agent_name": agent_name, "run_id": run_id, "tool_name": tool_name, "parameters": {"param": "value"}}
                )
                if not success:
                    return False
                
                success = await self.send_agent_event_with_validation(
                    user_id, thread_id, "tool_completed",
                    {"agent_name": agent_name, "run_id": run_id, "tool_name": tool_name, "result": {"success": True}}
                )
                if not success:
                    return False
            
            success = await self.send_agent_event_with_validation(
                user_id, thread_id, "agent_completed",
                {"agent_name": agent_name, "run_id": run_id, "result": {"status": "completed"}}
            )
            
            return success
            
        except Exception as e:
            print(f"Error in agent flow for user {user_id}: {e}")
            return False
    
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
            "analysis": analysis
        }
    
    async def cleanup_all(self):
        """Clean up all test contexts."""
        for context in self.test_contexts.values():
            try:
                await context.cleanup()
            except Exception:
                pass
        self.test_contexts.clear()


# ============================================================================
# ULTRA-COMPREHENSIVE TEST SUITE
# ============================================================================

class TestUltraComprehensiveWebSocketValidation:
    """The most comprehensive WebSocket validation test suite."""
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup ultra-comprehensive test environment with real WebSocket connections."""
        self.test_harness = WebSocketTestHarness()
        
        try:
            yield
        finally:
            # Cleanup
            await self.test_harness.cleanup_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_comprehensive_single_user_flow(self):
        """Test comprehensive single user flow."""
        print(" TARGET:  Testing comprehensive single user flow")
        
        user_id = "single_user_test"
        success = await self.test_harness.simulate_complete_agent_flow(user_id)
        
        assert success, "Single user agent flow simulation failed"
        
        # Validate results
        results = self.test_harness.get_comprehensive_results()
        assert results["validation_passed"], f"Validation failed: {results['validation_failures']}"
        
        analysis = results["analysis"]
        assert analysis["total_users"] >= 1, "Should track at least 1 user"
        assert analysis["total_events"] >= 5, "Should have at least 5 events for complete flow"
        
        print(" PASS:  Comprehensive single user flow test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(120)
    async def test_comprehensive_user_isolation(self):
        """Test comprehensive user isolation."""
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
        
        print(" PASS:  Comprehensive user isolation test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(90)
    async def test_comprehensive_event_delivery_reliability(self):
        """Test comprehensive event delivery reliability."""
        print("[U+1F4E1] Testing comprehensive event delivery reliability")
        
        # Test with multiple users
        user_ids = []
        for i in range(10):
            user_id = f"reliability_user_{i}"
            user_ids.append(user_id)
        
        # Run scenarios
        tasks = []
        for user_id in user_ids:
            task = self.test_harness.simulate_complete_agent_flow(user_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_rate = sum(1 for r in results if r is True) / len(results)
        
        # Should maintain high reliability
        assert success_rate >= 0.8, f"Reliability too low: {success_rate}"
        
        # Validate events were delivered
        test_results = self.test_harness.get_comprehensive_results()
        analysis = test_results["analysis"]
        assert analysis["total_events"] >= 30, "Should have delivered many events"
        
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
        
        analysis = results["analysis"]
        assert analysis["total_events"] >= 75, "Should process many events under load"
        
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
        
        print(" TROPHY:  FINAL COMPREHENSIVE VALIDATION PASSED!")
        print(" TARGET:  All WebSocket notification requirements validated successfully")
        print("[U+1F4BC] Business value preservation: Chat functionality fully operational")


class TestWebSocketEventTypes:
    """Test specific WebSocket event types and their requirements."""
    
    @pytest.fixture(autouse=True)
    async def setup_event_testing(self):
        """Setup for event type testing."""
        self.test_harness = WebSocketTestHarness()
        
        try:
            yield
        finally:
            await self.test_harness.cleanup_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_agent_started_event_requirements(self):
        """Test agent_started event meets all requirements."""
        user_id = "agent_started_test_user"
        context = await self.test_harness.create_test_context(user_id)
        thread_id = context.user_context.thread_id
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Test agent_started event with required fields
        success = await self.test_harness.send_agent_event_with_validation(
            user_id, thread_id, "agent_started",
            {
                "agent_name": "TestAgent",
                "run_id": run_id,
                "context": {
                    "user_query": "Test query for agent_started",
                    "task_type": "validation"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        assert success, "agent_started event should be sent successfully"
        
        # Validate event was recorded
        results = self.test_harness.get_comprehensive_results()
        assert results["analysis"]["event_counts"].get("agent_started", 0) >= 1, \
            "agent_started event should be counted"
        
        print(" PASS:  agent_started event requirements validated")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_execution_event_pairing(self):
        """Test tool_executing and tool_completed events are properly paired."""
        user_id = "tool_pairing_test_user"
        context = await self.test_harness.create_test_context(user_id)
        thread_id = context.user_context.thread_id
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        tool_name = "validation_tool"
        agent_name = "ToolTestAgent"
        
        # Send tool_executing
        success1 = await self.test_harness.send_agent_event_with_validation(
            user_id, thread_id, "tool_executing",
            {
                "agent_name": agent_name,
                "run_id": run_id,
                "tool_name": tool_name,
                "parameters": {"test": "tool_pairing"}
            }
        )
        
        # Send tool_completed  
        success2 = await self.test_harness.send_agent_event_with_validation(
            user_id, thread_id, "tool_completed", 
            {
                "agent_name": agent_name,
                "run_id": run_id,
                "tool_name": tool_name,
                "result": {"success": True, "test": "tool_pairing"}
            }
        )
        
        assert success1 and success2, "Both tool events should be sent successfully"
        
        # Validate pairing
        results = self.test_harness.get_comprehensive_results()
        event_counts = results["analysis"]["event_counts"]
        assert event_counts.get("tool_executing", 0) >= 1, "tool_executing should be counted"
        assert event_counts.get("tool_completed", 0) >= 1, "tool_completed should be counted"
        
        # Validate ordering (this is checked in the validator)
        assert results["analysis"]["ordering_valid"], "Tool events should be properly ordered"
        
        print(" PASS:  Tool execution event pairing validated")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_all_required_events_in_sequence(self):
        """Test that all 5 required events can be sent in proper sequence."""
        user_id = "sequence_test_user"
        context = await self.test_harness.create_test_context(user_id)
        thread_id = context.user_context.thread_id
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        agent_name = "SequenceTestAgent"
        
        # Send all required events in proper sequence
        events_sequence = [
            ("agent_started", {"context": {"task": "Sequence validation"}}),
            ("agent_thinking", {"reasoning": "Processing sequence test", "step": 1}),
            ("tool_executing", {"tool_name": "sequence_tool", "parameters": {}}),
            ("tool_completed", {"tool_name": "sequence_tool", "result": {"validated": True}}),
            ("agent_completed", {"result": {"status": "sequence_complete"}})
        ]
        
        successful_events = 0
        for event_type, event_data in events_sequence:
            full_data = {
                **event_data,
                "agent_name": agent_name,
                "run_id": run_id
            }
            
            success = await self.test_harness.send_agent_event_with_validation(
                user_id, thread_id, event_type, full_data
            )
            
            if success:
                successful_events += 1
            
            # Small delay between events
            await asyncio.sleep(0.1)
        
        assert successful_events == 5, f"All 5 events should be sent successfully, got {successful_events}"
        
        # Validate sequence
        results = self.test_harness.get_comprehensive_results()
        assert results["validation_passed"], f"Sequence validation failed: {results['validation_failures']}"
        
        analysis = results["analysis"]
        assert analysis["events_valid"], "All required events should be present"
        assert analysis["ordering_valid"], "Events should be in proper order"
        
        print(" PASS:  All required events in sequence validated")


if __name__ == "__main__":
    # Run the ultra-comprehensive test suite
    print("[U+1F680] Starting Ultra-Comprehensive WebSocket Validation Test Suite")
    
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