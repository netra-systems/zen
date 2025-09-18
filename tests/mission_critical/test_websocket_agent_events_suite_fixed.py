"""
Mission Critical WebSocket Agent Events Test Suite - SSOT Implementation with Unified Schema

Business Value Justification (BVJ):
- Segment: ALL (Free/Early/Mid/Enterprise/Platform)
- Business Goal: Agent Golden Path Protection - Ensures reliable WebSocket event delivery
- Value Impact: Validates the 5 critical events that enable $500K+ ARR chat functionality
- Revenue Impact: Protects high-value ARR by ensuring reliable WebSocket agent integration

This test suite validates the 5 required WebSocket events using the unified event schema
to prevent Issue #984 (missing tool_name and results fields) from recurring.

Required Events:
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency (requires tool_name)
4. tool_completed - Tool results display (requires tool_name, results)
5. agent_completed - User knows response is ready

Architecture: Uses unified event schema from event_schema.py as SSOT
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Unified Event Schema - SSOT for Issue #984 fix
from netra_backend.app.websocket_core.event_schema import (
    WebSocketEventType,
    create_agent_started_event,
    create_agent_thinking_event,
    create_tool_executing_event,
    create_tool_completed_event,
    create_agent_completed_event,
    validate_event_schema
)

# Test Context Infrastructure
from test_framework.test_context import WebSocketContext, create_test_context
from test_framework.websocket_helpers import WebSocketTestHelpers


class UnifiedEventValidator:
    """
    Mission Critical Event Validator using unified schema - Issue #984 fix.
    
    This validator enforces the unified event schema to prevent
    test/production mismatches that were causing 5/8 test failures.
    """

    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []
        self.event_counts: Dict[str, int] = {}
        self.validation_errors: List[str] = []
        self.schema_errors: Dict[str, List[str]] = {}
        self.start_time = time.time()

    def record(self, event: Dict) -> None:
        """Record and validate an event using unified schema."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")

        # Validate event against unified schema
        if event_type in self.REQUIRED_EVENTS:
            schema_errors = validate_event_schema(event, event_type)
            if schema_errors:
                self.schema_errors[event_type] = schema_errors
                if self.strict_mode:
                    self.validation_errors.extend(schema_errors)

        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1

    def validate_critical_requirements(self) -> tuple[bool, List[str]]:
        """Validate that ALL critical requirements are met with unified schema."""
        failures = []

        # 1. Check for required events
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"CRITICAL: Missing required events: {missing}")

        # 2. Validate schema compliance for all events  
        if self.schema_errors:
            for event_type, errors in self.schema_errors.items():
                failures.append(f"SCHEMA ERROR in {event_type}: {errors}")

        # 3. Validate tool events have required fields (Issue #984 fix)
        tool_executing_events = [e for e in self.events if e.get("type") == "tool_executing"]
        for event in tool_executing_events:
            if not event.get("tool_name"):
                failures.append("CRITICAL: tool_executing event missing tool_name field")

        tool_completed_events = [e for e in self.events if e.get("type") == "tool_completed"]
        for event in tool_completed_events:
            if not event.get("tool_name"):
                failures.append("CRITICAL: tool_completed event missing tool_name field")
            if "results" not in event:
                failures.append("CRITICAL: tool_completed event missing results field")

        # 4. Validate event ordering
        if not self._validate_event_order():
            failures.append("CRITICAL: Invalid event order")

        return len(failures) == 0, failures

    def _validate_event_order(self) -> bool:
        """Ensure events follow logical order."""
        if not self.event_timeline:
            return False

        # First event must be agent_started
        if self.event_timeline[0][1] != "agent_started":
            return False

        # Last event should be completion
        last_event = self.event_timeline[-1][1]
        if last_event not in ["agent_completed", "final_report"]:
            return False

        return True


class WebSocketAgentEventsUnifiedTests(SSotAsyncTestCase):
    """
    MISSION CRITICAL: WebSocket Agent Events Tests with Unified Schema
    
    Business Value: $500K+ ARR Golden Path Protection using unified event schema
    Critical Path: WebSocket Events → Agent Integration → Chat Functionality
    
    Issue #984 Fix: Uses unified event schema to prevent test/production mismatches
    that were causing 5/8 mission critical tests to fail due to missing fields.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_unified_websocket_test_environment(self):
        """Setup test environment with unified event schema validation."""
        # Create mock infrastructure using SSOT mock factory
        self.mock_factory = SSotMockFactory()
        
        # Core mocked dependencies
        self.mock_execution_engine = self.mock_factory.create_mock("ExecutionEngine")
        self.mock_websocket_manager = self.mock_factory.create_mock("WebSocketManager")
        self.mock_db_session = self.mock_factory.create_mock("AsyncSession")
        
        # Test user context for isolation testing
        self.test_user_context = MagicMock()
        self.test_user_context.user_id = "test_user_001"
        self.test_user_context.thread_id = "test_thread_001"
        self.test_user_context.run_id = "test_run_001"
        self.test_user_context.request_id = "test_req_001"
        self.test_user_context.websocket_client_id = "test_ws_001"
        self.test_user_context.add_execution_result = MagicMock()
        
        # Setup mock behaviors
        await self._setup_unified_mock_behaviors()
    
    async def _setup_unified_mock_behaviors(self):
        """Setup mock behaviors that create events using unified schema."""
        
        async def mock_execute_agent(context, user_context=None):
            execution_time = 0.1
            await asyncio.sleep(execution_time)
            
            # Create agent events using unified schema
            agent_started_event = create_agent_started_event(
                user_id=self.test_user_context.user_id,
                thread_id=self.test_user_context.thread_id,
                run_id=self.test_user_context.run_id,
                agent_name="test_agent",
                message="Agent test_agent started"
            )
            
            agent_thinking_event = create_agent_thinking_event(
                user_id=self.test_user_context.user_id,
                thread_id=self.test_user_context.thread_id,
                run_id=self.test_user_context.run_id,
                agent_name="test_agent",
                thought="Processing request with test_agent"
            )
            
            tool_executing_event = create_tool_executing_event(
                user_id=self.test_user_context.user_id,
                thread_id=self.test_user_context.thread_id,
                run_id=self.test_user_context.run_id,
                agent_name="test_agent",
                tool_name="test_tool",  # CRITICAL: Required field (Issue #984 fix)
                parameters={"query": "test query"}
            )
            
            tool_completed_event = create_tool_completed_event(
                user_id=self.test_user_context.user_id,
                thread_id=self.test_user_context.thread_id,
                run_id=self.test_user_context.run_id,
                agent_name="test_agent",
                tool_name="test_tool",  # CRITICAL: Required field (Issue #984 fix)
                results={"output": "test result"},  # CRITICAL: Required field (Issue #984 fix)
                success=True,
                duration_ms=execution_time * 1000
            )
            
            agent_completed_event = create_agent_completed_event(
                user_id=self.test_user_context.user_id,
                thread_id=self.test_user_context.thread_id,
                run_id=self.test_user_context.run_id,
                agent_name="test_agent",
                final_response="Agent test_agent completed successfully"
            )
            
            # Store events for validation
            self.generated_events = [
                agent_started_event,
                agent_thinking_event,
                tool_executing_event,
                tool_completed_event,
                agent_completed_event
            ]
            
            return {"success": True, "agent_name": "test_agent", "duration": execution_time}
        
        self.mock_execution_engine.execute_agent = AsyncMock(side_effect=mock_execute_agent)
        
        # Configure WebSocket manager
        self.mock_websocket_manager.notify_pipeline_started = AsyncMock()
        self.mock_websocket_manager.notify_pipeline_step = AsyncMock()
        self.mock_websocket_manager.notify_pipeline_completed = AsyncMock()
    
    @pytest.mark.mission_critical
    @pytest.mark.business_critical
    async def test_unified_websocket_agent_events_schema_validation(self):
        """
        MISSION CRITICAL: Test unified WebSocket event schema prevents Issue #984.
        
        BVJ: $500K+ ARR protection - validates schema compliance for core chat functionality
        Critical Path: Unified Schema → Event Validation → Test/Production Consistency
        
        Issue #984 Fix: This test ensures tool_name and results fields are present
        in tool events, preventing the test/production schema mismatch.
        """
        
        # Arrange: Setup validator with unified schema
        validator = UnifiedEventValidator(strict_mode=True)
        
        # Act: Create test events using unified schema
        test_events = [
            create_agent_started_event(
                user_id="test_user_001",
                thread_id="test_thread_001", 
                run_id="test_run_001",
                agent_name="test_agent"
            ),
            create_agent_thinking_event(
                user_id="test_user_001",
                thread_id="test_thread_001",
                run_id="test_run_001", 
                agent_name="test_agent",
                thought="Analyzing request"
            ),
            create_tool_executing_event(
                user_id="test_user_001",
                thread_id="test_thread_001",
                run_id="test_run_001",
                agent_name="test_agent",
                tool_name="cost_analyzer",  # CRITICAL: Required field (Issue #984 fix)
                parameters={"query": "analyze costs"}
            ),
            create_tool_completed_event(
                user_id="test_user_001",
                thread_id="test_thread_001",
                run_id="test_run_001",
                agent_name="test_agent", 
                tool_name="cost_analyzer",  # CRITICAL: Required field (Issue #984 fix)
                results={"savings": 5000.0},  # CRITICAL: Required field (Issue #984 fix)
                success=True
            ),
            create_agent_completed_event(
                user_id="test_user_001",
                thread_id="test_thread_001",
                run_id="test_run_001",
                agent_name="test_agent",
                final_response="Analysis complete"
            )
        ]
        
        # Record all events
        for event in test_events:
            validator.record(event)
        
        # Assert: Validate all requirements are met with unified schema
        success, failures = validator.validate_critical_requirements()
        
        if not success:
            error_details = "\\n".join([
                "❌ CRITICAL: Unified Schema Validation FAILED",
                f"Events generated: {len(validator.events)}",
                f"Event types: {list(validator.event_counts.keys())}",
                f"Required events: {validator.REQUIRED_EVENTS}",
                f"Schema errors: {validator.schema_errors}",
                "Failures:",
                *failures
            ])
            pytest.fail(error_details)
        
        # Validate critical fields are present (Issue #984 fix)
        tool_executing_events = [e for e in test_events if e.get("type") == "tool_executing"]
        for event in tool_executing_events:
            assert event.get("tool_name"), f"tool_executing event missing tool_name: {event}"
        
        tool_completed_events = [e for e in test_events if e.get("type") == "tool_completed"]
        for event in tool_completed_events:
            assert event.get("tool_name"), f"tool_completed event missing tool_name: {event}"
            assert "results" in event, f"tool_completed event missing results: {event}"
        
        # Validate all required events are present
        assert len(validator.events) >= 5, f"Expected at least 5 events, got {len(validator.events)}"
        assert validator.event_counts.get("agent_started", 0) >= 1, "Missing agent_started event"
        assert validator.event_counts.get("agent_thinking", 0) >= 1, "Missing agent_thinking event"
        assert validator.event_counts.get("tool_executing", 0) >= 1, "Missing tool_executing event"
        assert validator.event_counts.get("tool_completed", 0) >= 1, "Missing tool_completed event"
        assert validator.event_counts.get("agent_completed", 0) >= 1, "Missing agent_completed event"
        
        print(f"✅ Unified Schema Validation PASSED - {len(validator.events)} events validated")
    
    @pytest.mark.mission_critical
    @pytest.mark.business_critical
    async def test_tool_events_required_fields_issue_984_fix(self):
        """
        MISSION CRITICAL: Test tool events have required fields - Issue #984 fix.
        
        BVJ: System reliability - prevents test failures due to missing fields
        Critical Path: Tool Events → Required Fields → Schema Compliance
        
        This test specifically validates the Issue #984 fix where tool_name and
        results fields were missing from tool events, causing test/production mismatches.
        """
        
        # Arrange: Create tool events with required fields
        tool_executing_event = create_tool_executing_event(
            user_id="test_user_001",
            thread_id="test_thread_001",
            run_id="test_run_001",
            agent_name="test_agent",
            tool_name="data_analyzer",  # CRITICAL: Issue #984 fix
            parameters={"dataset": "cost_data", "period": "30d"}
        )
        
        tool_completed_event = create_tool_completed_event(
            user_id="test_user_001", 
            thread_id="test_thread_001",
            run_id="test_run_001",
            agent_name="test_agent",
            tool_name="data_analyzer",  # CRITICAL: Issue #984 fix
            results={  # CRITICAL: Issue #984 fix
                "analysis": "Cost optimization opportunities identified",
                "savings_potential": 12500.0,
                "recommendations": ["Optimize GPU usage", "Consolidate storage"]
            },
            success=True,
            duration_ms=2500.0
        )
        
        # Act: Validate events have required fields
        tool_executing_errors = validate_event_schema(tool_executing_event, "tool_executing")
        tool_completed_errors = validate_event_schema(tool_completed_event, "tool_completed")
        
        # Assert: No validation errors for required fields
        assert not tool_executing_errors, f"tool_executing validation failed: {tool_executing_errors}"
        assert not tool_completed_errors, f"tool_completed validation failed: {tool_completed_errors}"
        
        # Assert: Critical fields are present
        assert tool_executing_event.get("tool_name") == "data_analyzer", "tool_executing missing tool_name"
        assert tool_completed_event.get("tool_name") == "data_analyzer", "tool_completed missing tool_name" 
        assert "results" in tool_completed_event, "tool_completed missing results field"
        assert isinstance(tool_completed_event["results"], dict), "results must be a dictionary"
        
        # Assert: Results contain meaningful data
        results = tool_completed_event["results"]
        assert "analysis" in results, "results missing analysis"
        assert "savings_potential" in results, "results missing savings_potential"
        assert results["savings_potential"] > 0, "savings_potential should be positive"
        
        print(f"✅ Tool Events Required Fields Validation PASSED - Issue #984 fix verified")


# Test execution entry point
if __name__ == "__main__":
    print("\\n" + "=" * 80)
    print("MISSION CRITICAL WEBSOCKET AGENT EVENTS TEST SUITE - UNIFIED SCHEMA")
    print("Issue #984 Fix: WebSocket events missing critical fields (tool_name, results)")
    print("=" * 80)
    print()
    print("Business Value: $500K+ ARR - Core chat functionality")
    print("Testing: Unified event schema prevents test/production mismatches")
    print("Architecture: Single Source of Truth for event structures")
    print("\\nRunning unified schema validation tests...")
    
    # Run the unified schema tests
    import subprocess
    import sys
    
    try:
        result = subprocess.run([
            sys.executable, 
            "-m", "pytest",
            __file__,
            "-v", "--tb=short",
            "-k", "test_unified_websocket_agent_events"
        ], capture_output=True, text=True, timeout=60)
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\\n{result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("[FAIL] Test execution timed out after 60 seconds")
    except Exception as e:
        print(f"[FAIL] Error running tests: {e}")
    
    print("\\n[COMPLETE] Unified schema validation test execution finished.")