#!/usr/bin/env python
"""
Agent Registry WebSocket Bridge Integration Tests - Exposing Factory Pattern Gaps

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Agent execution affects all users
- Business Goal: Expose Agent Registry WebSocket integration failures preventing agent business value
- Value Impact: Agent Registry enables agent execution that delivers 90% of chat business value
- Strategic Impact: Factory pattern migration gaps causing Data Helper Agent 0% success rate

CRITICAL MISSION: These tests are designed to FAIL and expose specific integration gaps:
1. Agent Registry missing WebSocket manager integration
2. Factory pattern vs singleton pattern architectural mismatches  
3. WebSocket bridge creation failures in multi-user contexts
4. Agent execution without proper WebSocket event emission

TEST FAILURE EXPECTATIONS:
- Agent Registry WebSocket manager not properly initialized
- Factory pattern WebSocket bridge creation failures
- Missing WebSocket event emissions during agent execution
- Multi-user isolation failures in WebSocket context

This test suite intentionally exposes the Agent Registry WebSocket integration
gaps that prevent Data Helper Agents from delivering business value.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

# SSOT imports per CLAUDE.md requirements
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, RunID
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Critical imports for testing Agent Registry WebSocket integration
try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession
    from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
    from netra_backend.app.services.user_execution_context import UserExecutionContext
except ImportError as e:
    # Expected in some test environments - we'll test for this gap
    print(f"[EXPECTED IMPORT ERROR] Agent Registry components not available: {e}")
    AgentRegistry = None
    UnifiedToolDispatcher = None
    UserExecutionContext = None


@dataclass
class AgentRegistryIntegrationGap:
    """Data structure for capturing Agent Registry WebSocket integration gaps."""
    
    test_name: str
    gap_type: str
    component: str
    error_message: str
    expected_gap: bool
    business_impact: str
    timestamp: str
    technical_details: Dict[str, Any]
    fix_complexity: str = "medium"  # low, medium, high, critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert integration gap to dictionary for analysis."""
        return {
            "test_name": self.test_name,
            "gap_type": self.gap_type,
            "component": self.component,
            "error_message": self.error_message,
            "expected_gap": self.expected_gap,
            "business_impact": self.business_impact,
            "timestamp": self.timestamp,
            "technical_details": self.technical_details,
            "fix_complexity": self.fix_complexity
        }


class MockWebSocketManager:
    """Mock WebSocket manager for testing Agent Registry integration gaps."""
    
    def __init__(self, should_fail: bool = False, failure_mode: str = "creation"):
        self.should_fail = should_fail
        self.failure_mode = failure_mode
        self.bridge_creation_attempts = []
        self.user_contexts_processed = []
        
    def create_bridge(self, user_context):
        """Create WebSocket bridge - may fail to test integration gaps."""
        self.bridge_creation_attempts.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": getattr(user_context, 'user_id', 'unknown'),
            "context_type": type(user_context).__name__
        })
        
        self.user_contexts_processed.append(user_context)
        
        if self.should_fail:
            if self.failure_mode == "creation":
                raise Exception("WebSocket bridge creation failed - missing factory integration")
            elif self.failure_mode == "user_context":
                raise ValueError("Invalid user context for WebSocket bridge creation")
            elif self.failure_mode == "permissions":
                raise PermissionError("WebSocket bridge creation not authorized")
        
        return MockWebSocketBridge(user_context)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to user - may fail to test integration gaps."""
        if self.should_fail and self.failure_mode == "send":
            raise Exception("WebSocket message sending failed - no active connections")
        
        # Mock successful send
        return True


class MockWebSocketBridge:
    """Mock WebSocket bridge to test Agent Registry integration."""
    
    def __init__(self, user_context):
        self.user_context = user_context
        self.events_emitted = []
        self.is_functional = True
        
    async def emit_agent_started(self, agent_type: str, message: str = None):
        """Emit agent started event - track for integration testing."""
        event = {
            "type": "agent_started",
            "agent_type": agent_type,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": getattr(self.user_context, 'user_id', 'unknown')
        }
        self.events_emitted.append(event)
        
    async def emit_agent_thinking(self, reasoning: str):
        """Emit agent thinking event."""
        event = {
            "type": "agent_thinking",
            "reasoning": reasoning,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": getattr(self.user_context, 'user_id', 'unknown')
        }
        self.events_emitted.append(event)
        
    async def emit_tool_executing(self, tool_name: str, parameters: Dict[str, Any] = None):
        """Emit tool executing event."""
        event = {
            "type": "tool_executing",
            "tool_name": tool_name,
            "parameters": parameters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": getattr(self.user_context, 'user_id', 'unknown')
        }
        self.events_emitted.append(event)
        
    async def emit_tool_completed(self, tool_name: str, result: Dict[str, Any]):
        """Emit tool completed event."""
        event = {
            "type": "tool_completed",
            "tool_name": tool_name,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": getattr(self.user_context, 'user_id', 'unknown')
        }
        self.events_emitted.append(event)
        
    async def emit_agent_completed(self, result: Dict[str, Any], agent_type: str = None):
        """Emit agent completed event."""
        event = {
            "type": "agent_completed",
            "agent_type": agent_type,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": getattr(self.user_context, 'user_id', 'unknown')
        }
        self.events_emitted.append(event)


class TestAgentRegistryWebSocketBridge(BaseIntegrationTest):
    """Integration tests designed to expose Agent Registry WebSocket bridge gaps."""
    
    def __init__(self):
        super().__init__()
        self.env = get_env()
        self.integration_gaps: List[AgentRegistryIntegrationGap] = []
        self.agent_registry = None
        self.mock_websocket_manager = None
        
    def setup_method(self):
        """Setup for each test method with gap tracking."""
        print(f"[INFO] Agent Registry WebSocket Bridge Integration Test Setup")
        
        # Initialize mock WebSocket manager for testing
        self.mock_websocket_manager = MockWebSocketManager()
        
        # Try to initialize Agent Registry - this may fail due to integration gaps
        if AgentRegistry:
            try:
                # Create tool dispatcher factory for testing
                async def mock_tool_dispatcher_factory(user_context, websocket_bridge=None):
                    return MockToolDispatcher(user_context, websocket_bridge)
                
                self.agent_registry = AgentRegistry(
                    tool_dispatcher_factory=mock_tool_dispatcher_factory
                )
                print(f"[INFO] Agent Registry initialized for testing")
                
            except Exception as e:
                self.capture_integration_gap(
                    test_name="setup_agent_registry_initialization",
                    gap_type="agent_registry_initialization_failure",
                    component="AgentRegistry",
                    error_message=str(e),
                    expected_gap=True,
                    business_impact="Agent Registry cannot be initialized - blocks all agent execution",
                    fix_complexity="critical",
                    technical_details={
                        "error_type": type(e).__name__,
                        "setup_phase": "agent_registry_creation"
                    }
                )
        else:
            self.capture_integration_gap(
                test_name="setup_agent_registry_imports",
                gap_type="missing_agent_registry_imports",
                component="ImportSystem",
                error_message="Agent Registry components not available for import",
                expected_gap=True,
                business_impact="Agent Registry cannot be imported - complete system failure",
                fix_complexity="critical",
                technical_details={
                    "missing_components": ["AgentRegistry", "UnifiedToolDispatcher", "UserExecutionContext"]
                }
            )
    
    def capture_integration_gap(
        self,
        test_name: str,
        gap_type: str,
        component: str,
        error_message: str,
        expected_gap: bool,
        business_impact: str,
        fix_complexity: str = "medium",
        technical_details: Optional[Dict[str, Any]] = None
    ):
        """Capture structured integration gap for analysis."""
        gap = AgentRegistryIntegrationGap(
            test_name=test_name,
            gap_type=gap_type,
            component=component,
            error_message=error_message,
            expected_gap=expected_gap,
            business_impact=business_impact,
            timestamp=datetime.now(timezone.utc).isoformat(),
            technical_details=technical_details or {},
            fix_complexity=fix_complexity
        )
        
        self.integration_gaps.append(gap)
        
        # Log gap for immediate visibility
        gap_status = "EXPECTED" if expected_gap else "UNEXPECTED"
        print(f"[{gap_status} GAP] {test_name}: {business_impact}")
        print(f"[COMPONENT] {component} - {gap_type}")
        print(f"[ERROR] {error_message}")
        if technical_details:
            print(f"[TECHNICAL] {json.dumps(technical_details, indent=2)}")
    
    # ===================== Agent Registry WebSocket Manager Integration Tests =====================
    
    @pytest.mark.integration
    async def test_agent_registry_websocket_manager_initialization_gap(self):
        """
        Test Agent Registry WebSocket manager initialization gap.
        
        EXPECTED TO FAIL: This should expose missing WebSocket manager initialization
        in Agent Registry that prevents proper WebSocket event emission.
        
        Integration Gap: Agent Registry WebSocket manager not properly integrated
        """
        test_name = "agent_registry_websocket_manager_initialization"
        
        if not self.agent_registry:
            self.capture_integration_gap(
                test_name=test_name,
                gap_type="agent_registry_unavailable",
                component="AgentRegistry",
                error_message="Agent Registry not available for testing",
                expected_gap=True,
                business_impact="Cannot test WebSocket integration - Agent Registry missing",
                fix_complexity="critical"
            )
            return
        
        try:
            # Test WebSocket manager integration
            initial_websocket_manager = getattr(self.agent_registry, 'websocket_manager', None)
            
            if initial_websocket_manager is None:
                self.capture_integration_gap(
                    test_name=test_name,
                    gap_type="missing_websocket_manager_integration",
                    component="AgentRegistry",
                    error_message="Agent Registry has no websocket_manager attribute",
                    expected_gap=True,
                    business_impact="Agent Registry cannot emit WebSocket events - no real-time user feedback",
                    fix_complexity="high",
                    technical_details={
                        "agent_registry_attributes": dir(self.agent_registry),
                        "websocket_manager_present": False
                    }
                )
            
            # Test WebSocket manager setting functionality
            try:
                if hasattr(self.agent_registry, 'set_websocket_manager_async'):
                    await self.agent_registry.set_websocket_manager_async(self.mock_websocket_manager)
                    
                    # Verify manager was set
                    updated_manager = getattr(self.agent_registry, 'websocket_manager', None)
                    if updated_manager != self.mock_websocket_manager:
                        self.capture_integration_gap(
                            test_name=test_name,
                            gap_type="websocket_manager_setting_failure",
                            component="AgentRegistry",
                            error_message="WebSocket manager not properly set in Agent Registry",
                            expected_gap=True,
                            business_impact="WebSocket manager cannot be configured - integration broken",
                            fix_complexity="high"
                        )
                    else:
                        # Unexpected success - integration may be working
                        self.capture_integration_gap(
                            test_name=test_name,
                            gap_type="websocket_manager_integration_working",
                            component="AgentRegistry",
                            error_message="WebSocket manager integration appears functional",
                            expected_gap=False,
                            business_impact="WebSocket integration may be resolved",
                            fix_complexity="low"
                        )
                        
                else:
                    self.capture_integration_gap(
                        test_name=test_name,
                        gap_type="missing_websocket_manager_setter",
                        component="AgentRegistry",
                        error_message="Agent Registry missing set_websocket_manager_async method",
                        expected_gap=True,
                        business_impact="Cannot configure WebSocket manager - missing API",
                        fix_complexity="high",
                        technical_details={
                            "available_methods": [m for m in dir(self.agent_registry) if not m.startswith('_')]
                        }
                    )
                    
            except Exception as setter_error:
                self.capture_integration_gap(
                    test_name=test_name,
                    gap_type="websocket_manager_setter_error",
                    component="AgentRegistry",
                    error_message=str(setter_error),
                    expected_gap=True,
                    business_impact="WebSocket manager setter throws exceptions - integration broken",
                    fix_complexity="high",
                    technical_details={
                        "error_type": type(setter_error).__name__
                    }
                )
                
        except Exception as test_error:
            self.capture_integration_gap(
                test_name=test_name,
                gap_type="test_execution_error",
                component="TestFramework",
                error_message=str(test_error),
                expected_gap=False,
                business_impact="Cannot test WebSocket integration due to test framework issues",
                fix_complexity="medium",
                technical_details={"error_type": type(test_error).__name__}
            )
            raise
    
    @pytest.mark.integration
    async def test_agent_registry_websocket_bridge_creation_gap(self):
        """
        Test Agent Registry WebSocket bridge creation gap in factory pattern.
        
        EXPECTED TO FAIL: This should expose WebSocket bridge creation failures
        when Agent Registry tries to create per-user WebSocket bridges.
        
        Integration Gap: Factory pattern WebSocket bridge creation not working
        """
        test_name = "agent_registry_websocket_bridge_creation"
        
        if not self.agent_registry:
            self.capture_integration_gap(
                test_name=test_name,
                gap_type="agent_registry_unavailable",
                component="AgentRegistry",
                error_message="Agent Registry not available for bridge testing",
                expected_gap=True,
                business_impact="Cannot test WebSocket bridge creation",
                fix_complexity="critical"
            )
            return
        
        try:
            # Create test user context for bridge creation
            user_context = await create_authenticated_user_context(
                user_email="bridge_test@example.com",
                environment="test"
            )
            
            # Set up WebSocket manager that will fail during bridge creation
            failing_websocket_manager = MockWebSocketManager(should_fail=True, failure_mode="creation")
            
            try:
                if hasattr(self.agent_registry, 'set_websocket_manager_async'):
                    await self.agent_registry.set_websocket_manager_async(failing_websocket_manager)
                
                # Test user session creation with WebSocket bridge
                if hasattr(self.agent_registry, 'create_agent_for_user'):
                    # This should fail when trying to create WebSocket bridge
                    agent = await self.agent_registry.create_agent_for_user(
                        user_id=user_context.user_id,
                        agent_type="triage",
                        user_context=user_context,
                        websocket_manager=failing_websocket_manager
                    )
                    
                    # If this succeeds, it means bridge creation was bypassed
                    self.capture_integration_gap(
                        test_name=test_name,
                        gap_type="websocket_bridge_creation_bypassed",
                        component="AgentRegistry",
                        error_message="Agent creation succeeded without WebSocket bridge",
                        expected_gap=True,
                        business_impact="WebSocket bridge creation not integrated - agents work but no events",
                        fix_complexity="high",
                        technical_details={
                            "agent_created": True,
                            "bridge_creation_attempts": len(failing_websocket_manager.bridge_creation_attempts)
                        }
                    )
                    
                else:
                    self.capture_integration_gap(
                        test_name=test_name,
                        gap_type="missing_agent_creation_method",
                        component="AgentRegistry",
                        error_message="Agent Registry missing create_agent_for_user method",
                        expected_gap=True,
                        business_impact="Cannot create agents with WebSocket integration",
                        fix_complexity="critical"
                    )
                    
            except Exception as bridge_error:
                # EXPECTED: Should fail with bridge creation error
                error_message = str(bridge_error).lower()
                
                bridge_error_patterns = ["bridge", "factory", "websocket", "creation", "integration"]
                is_bridge_error = any(pattern in error_message for pattern in bridge_error_patterns)
                
                if is_bridge_error:
                    self.capture_integration_gap(
                        test_name=test_name,
                        gap_type="websocket_bridge_creation_failure",
                        component="WebSocketBridgeFactory",
                        error_message=str(bridge_error),
                        expected_gap=True,
                        business_impact="WebSocket bridge creation fails - no real-time events for users",
                        fix_complexity="high",
                        technical_details={
                            "error_type": type(bridge_error).__name__,
                            "is_bridge_error": is_bridge_error,
                            "bridge_patterns_found": [p for p in bridge_error_patterns if p in error_message]
                        }
                    )
                else:
                    self.capture_integration_gap(
                        test_name=test_name,
                        gap_type="agent_creation_failure",
                        component="AgentRegistry",
                        error_message=str(bridge_error),
                        expected_gap=True,
                        business_impact="Agent creation fails when WebSocket integration attempted",
                        fix_complexity="high",
                        technical_details={
                            "error_type": type(bridge_error).__name__
                        }
                    )
                    
        except Exception as test_error:
            self.capture_integration_gap(
                test_name=test_name,
                gap_type="test_execution_error",
                component="TestFramework",
                error_message=str(test_error),
                expected_gap=False,
                business_impact="Cannot test WebSocket bridge creation",
                fix_complexity="medium",
                technical_details={"error_type": type(test_error).__name__}
            )
            raise
    
    @pytest.mark.integration
    async def test_agent_registry_websocket_event_emission_gap(self):
        """
        Test Agent Registry WebSocket event emission gap during agent execution.
        
        EXPECTED TO FAIL: This should expose missing WebSocket event emission
        during agent execution that prevents real-time user feedback.
        
        Integration Gap: Agent execution not emitting required WebSocket events
        """
        test_name = "agent_registry_websocket_event_emission"
        
        if not self.agent_registry:
            self.capture_integration_gap(
                test_name=test_name,
                gap_type="agent_registry_unavailable",
                component="AgentRegistry",
                error_message="Agent Registry not available for event testing",
                expected_gap=True,
                business_impact="Cannot test WebSocket event emission",
                fix_complexity="critical"
            )
            return
        
        try:
            # Set up working WebSocket manager for event testing
            working_websocket_manager = MockWebSocketManager(should_fail=False)
            
            if hasattr(self.agent_registry, 'set_websocket_manager_async'):
                await self.agent_registry.set_websocket_manager_async(working_websocket_manager)
            
            # Create test user context
            user_context = await create_authenticated_user_context(
                user_email="event_test@example.com",
                environment="test"
            )
            
            # Test agent creation and execution with WebSocket event emission
            if hasattr(self.agent_registry, 'create_agent_for_user'):
                try:
                    # Create agent
                    agent = await self.agent_registry.create_agent_for_user(
                        user_id=user_context.user_id,
                        agent_type="data",  # Data helper agent for testing
                        user_context=user_context,
                        websocket_manager=working_websocket_manager
                    )
                    
                    if agent:
                        # Test user session WebSocket bridge functionality
                        if hasattr(self.agent_registry, 'get_user_session'):
                            user_session = await self.agent_registry.get_user_session(user_context.user_id)
                            
                            if user_session:
                                # Check if user session has WebSocket bridge
                                websocket_bridge = getattr(user_session, '_websocket_bridge', None)
                                
                                if websocket_bridge is None:
                                    self.capture_integration_gap(
                                        test_name=test_name,
                                        gap_type="missing_websocket_bridge_in_session",
                                        component="UserAgentSession",
                                        error_message="User session has no WebSocket bridge",
                                        expected_gap=True,
                                        business_impact="User sessions cannot emit WebSocket events - no real-time feedback",
                                        fix_complexity="high",
                                        technical_details={
                                            "user_session_attributes": dir(user_session),
                                            "websocket_bridge_present": False
                                        }
                                    )
                                else:
                                    # Test WebSocket event emission
                                    try:
                                        await websocket_bridge.emit_agent_started(agent_type="data", message="Testing event emission")
                                        await websocket_bridge.emit_agent_thinking(reasoning="Testing WebSocket integration")
                                        await websocket_bridge.emit_tool_executing(tool_name="test_tool", parameters={"test": True})
                                        await websocket_bridge.emit_tool_completed(tool_name="test_tool", result={"success": True})
                                        await websocket_bridge.emit_agent_completed(result={"test": "completed"}, agent_type="data")
                                        
                                        # Check if events were properly emitted
                                        events_emitted = getattr(websocket_bridge, 'events_emitted', [])
                                        
                                        if len(events_emitted) < 5:
                                            self.capture_integration_gap(
                                                test_name=test_name,
                                                gap_type="insufficient_websocket_events",
                                                component="WebSocketBridge",
                                                error_message=f"Only {len(events_emitted)} events emitted, expected 5",
                                                expected_gap=True,
                                                business_impact="Incomplete WebSocket events - poor user experience",
                                                fix_complexity="medium",
                                                technical_details={
                                                    "events_emitted": len(events_emitted),
                                                    "expected_events": 5,
                                                    "event_types": [e.get("type") for e in events_emitted]
                                                }
                                            )
                                        else:
                                            # Unexpected success - events working properly
                                            self.capture_integration_gap(
                                                test_name=test_name,
                                                gap_type="websocket_events_working",
                                                component="WebSocketBridge",
                                                error_message="WebSocket events emitted successfully",
                                                expected_gap=False,
                                                business_impact="WebSocket event emission appears functional",
                                                fix_complexity="low",
                                                technical_details={
                                                    "events_emitted": len(events_emitted),
                                                    "event_types": [e.get("type") for e in events_emitted]
                                                }
                                            )
                                            
                                    except Exception as event_error:
                                        self.capture_integration_gap(
                                            test_name=test_name,
                                            gap_type="websocket_event_emission_error",
                                            component="WebSocketBridge",
                                            error_message=str(event_error),
                                            expected_gap=True,
                                            business_impact="WebSocket event emission fails - no user feedback",
                                            fix_complexity="high",
                                            technical_details={
                                                "error_type": type(event_error).__name__
                                            }
                                        )
                                        
                            else:
                                self.capture_integration_gap(
                                    test_name=test_name,
                                    gap_type="missing_user_session",
                                    component="AgentRegistry",
                                    error_message="User session not found after agent creation",
                                    expected_gap=True,
                                    business_impact="User sessions not properly managed - multi-user isolation broken",
                                    fix_complexity="high"
                                )
                                
                        else:
                            self.capture_integration_gap(
                                test_name=test_name,
                                gap_type="missing_user_session_getter",
                                component="AgentRegistry",
                                error_message="Agent Registry missing get_user_session method",
                                expected_gap=True,
                                business_impact="Cannot access user sessions - WebSocket integration impossible",
                                fix_complexity="critical"
                            )
                            
                    else:
                        self.capture_integration_gap(
                            test_name=test_name,
                            gap_type="agent_creation_returned_none",
                            component="AgentRegistry",
                            error_message="Agent creation returned None",
                            expected_gap=True,
                            business_impact="Agent creation fails silently - no agents available for execution",
                            fix_complexity="high"
                        )
                        
                except Exception as agent_error:
                    self.capture_integration_gap(
                        test_name=test_name,
                        gap_type="agent_creation_error",
                        component="AgentRegistry",
                        error_message=str(agent_error),
                        expected_gap=True,
                        business_impact="Agent creation fails - no business value delivery possible",
                        fix_complexity="critical",
                        technical_details={
                            "error_type": type(agent_error).__name__
                        }
                    )
                    
            else:
                self.capture_integration_gap(
                    test_name=test_name,
                    gap_type="missing_agent_creation_method",
                    component="AgentRegistry",
                    error_message="Agent Registry missing create_agent_for_user method",
                    expected_gap=True,
                    business_impact="Cannot create agents - complete system failure",
                    fix_complexity="critical"
                )
                
        except Exception as test_error:
            self.capture_integration_gap(
                test_name=test_name,
                gap_type="test_execution_error",
                component="TestFramework",
                error_message=str(test_error),
                expected_gap=False,
                business_impact="Cannot test WebSocket event emission",
                fix_complexity="medium",
                technical_details={"error_type": type(test_error).__name__}
            )
            raise
    
    # ===================== Multi-User Isolation Tests =====================
    
    @pytest.mark.integration
    async def test_agent_registry_multi_user_websocket_isolation_gap(self):
        """
        Test Agent Registry multi-user WebSocket isolation gap.
        
        EXPECTED TO FAIL: This should expose multi-user isolation failures
        in WebSocket event delivery that could cause data leakage.
        
        Integration Gap: Multi-user WebSocket isolation not properly implemented
        """
        test_name = "agent_registry_multi_user_websocket_isolation"
        
        if not self.agent_registry:
            self.capture_integration_gap(
                test_name=test_name,
                gap_type="agent_registry_unavailable",
                component="AgentRegistry",
                error_message="Agent Registry not available for isolation testing",
                expected_gap=True,
                business_impact="Cannot test multi-user isolation",
                fix_complexity="critical"
            )
            return
        
        try:
            # Set up WebSocket manager for multi-user testing
            isolation_websocket_manager = MockWebSocketManager(should_fail=False)
            
            if hasattr(self.agent_registry, 'set_websocket_manager_async'):
                await self.agent_registry.set_websocket_manager_async(isolation_websocket_manager)
            
            # Create two different user contexts
            user_alice_context = await create_authenticated_user_context(
                user_email="alice@example.com",
                user_id="alice_user_123",
                environment="test"
            )
            
            user_bob_context = await create_authenticated_user_context(
                user_email="bob@example.com", 
                user_id="bob_user_456",
                environment="test"
            )
            
            # Test agent creation for both users
            if hasattr(self.agent_registry, 'create_agent_for_user'):
                try:
                    # Create agents for both users
                    alice_agent = await self.agent_registry.create_agent_for_user(
                        user_id=user_alice_context.user_id,
                        agent_type="triage",
                        user_context=user_alice_context,
                        websocket_manager=isolation_websocket_manager
                    )
                    
                    bob_agent = await self.agent_registry.create_agent_for_user(
                        user_id=user_bob_context.user_id,
                        agent_type="triage",
                        user_context=user_bob_context,
                        websocket_manager=isolation_websocket_manager
                    )
                    
                    if alice_agent and bob_agent:
                        # Test user session isolation
                        if hasattr(self.agent_registry, 'get_user_session'):
                            alice_session = await self.agent_registry.get_user_session(user_alice_context.user_id)
                            bob_session = await self.agent_registry.get_user_session(user_bob_context.user_id)
                            
                            if alice_session and bob_session:
                                # Check if sessions are properly isolated
                                if alice_session == bob_session:
                                    self.capture_integration_gap(
                                        test_name=test_name,
                                        gap_type="user_session_not_isolated",
                                        component="AgentRegistry",
                                        error_message="Same user session returned for different users",
                                        expected_gap=True,
                                        business_impact="CRITICAL: Multi-user data leakage - security breach",
                                        fix_complexity="critical",
                                        technical_details={
                                            "alice_user_id": str(user_alice_context.user_id),
                                            "bob_user_id": str(user_bob_context.user_id),
                                            "sessions_identical": True
                                        }
                                    )
                                
                                # Test WebSocket bridge isolation
                                alice_bridge = getattr(alice_session, '_websocket_bridge', None)
                                bob_bridge = getattr(bob_session, '_websocket_bridge', None)
                                
                                if alice_bridge and bob_bridge:
                                    if alice_bridge == bob_bridge:
                                        self.capture_integration_gap(
                                            test_name=test_name,
                                            gap_type="websocket_bridge_not_isolated",
                                            component="WebSocketBridge",
                                            error_message="Same WebSocket bridge for different users",
                                            expected_gap=True,
                                            business_impact="CRITICAL: WebSocket events may leak between users",
                                            fix_complexity="critical",
                                            technical_details={
                                                "bridge_isolation": False,
                                                "bridges_identical": True
                                            }
                                        )
                                    
                                    # Test event isolation by emitting events for each user
                                    try:
                                        await alice_bridge.emit_agent_started(agent_type="triage", message="Alice's agent started")
                                        await bob_bridge.emit_agent_started(agent_type="triage", message="Bob's agent started")
                                        
                                        # Check event isolation
                                        alice_events = getattr(alice_bridge, 'events_emitted', [])
                                        bob_events = getattr(bob_bridge, 'events_emitted', [])
                                        
                                        # Verify events are properly isolated
                                        alice_user_ids = set(e.get("user_id") for e in alice_events)
                                        bob_user_ids = set(e.get("user_id") for e in bob_events)
                                        
                                        if alice_user_ids.intersection(bob_user_ids):
                                            self.capture_integration_gap(
                                                test_name=test_name,
                                                gap_type="websocket_event_cross_contamination",
                                                component="WebSocketBridge",
                                                error_message="WebSocket events cross-contamination between users",
                                                expected_gap=True,
                                                business_impact="CRITICAL: User events leaking between sessions",
                                                fix_complexity="critical",
                                                technical_details={
                                                    "alice_user_ids": list(alice_user_ids),
                                                    "bob_user_ids": list(bob_user_ids),
                                                    "cross_contamination": True
                                                }
                                            )
                                        else:
                                            # Isolation working properly - unexpected success
                                            self.capture_integration_gap(
                                                test_name=test_name,
                                                gap_type="websocket_isolation_working",
                                                component="WebSocketBridge",
                                                error_message="WebSocket isolation appears functional",
                                                expected_gap=False,
                                                business_impact="Multi-user WebSocket isolation working correctly",
                                                fix_complexity="low",
                                                technical_details={
                                                    "alice_events": len(alice_events),
                                                    "bob_events": len(bob_events),
                                                    "isolation_verified": True
                                                }
                                            )
                                            
                                    except Exception as event_error:
                                        self.capture_integration_gap(
                                            test_name=test_name,
                                            gap_type="multi_user_event_emission_error",
                                            component="WebSocketBridge",
                                            error_message=str(event_error),
                                            expected_gap=True,
                                            business_impact="WebSocket event emission fails in multi-user context",
                                            fix_complexity="high",
                                            technical_details={
                                                "error_type": type(event_error).__name__
                                            }
                                        )
                                        
                                else:
                                    self.capture_integration_gap(
                                        test_name=test_name,
                                        gap_type="missing_websocket_bridges",
                                        component="UserAgentSession",
                                        error_message="WebSocket bridges not found in user sessions",
                                        expected_gap=True,
                                        business_impact="WebSocket bridges not created for user sessions",
                                        fix_complexity="high",
                                        technical_details={
                                            "alice_bridge_present": bool(alice_bridge),
                                            "bob_bridge_present": bool(bob_bridge)
                                        }
                                    )
                                    
                            else:
                                self.capture_integration_gap(
                                    test_name=test_name,
                                    gap_type="missing_user_sessions",
                                    component="AgentRegistry",
                                    error_message="User sessions not found for multi-user test",
                                    expected_gap=True,
                                    business_impact="User session management not working",
                                    fix_complexity="high",
                                    technical_details={
                                        "alice_session_present": bool(alice_session),
                                        "bob_session_present": bool(bob_session)
                                    }
                                )
                                
                        else:
                            self.capture_integration_gap(
                                test_name=test_name,
                                gap_type="missing_user_session_getter",
                                component="AgentRegistry",
                                error_message="Agent Registry missing get_user_session method",
                                expected_gap=True,
                                business_impact="Cannot test multi-user isolation without session access",
                                fix_complexity="critical"
                            )
                            
                    else:
                        self.capture_integration_gap(
                            test_name=test_name,
                            gap_type="multi_user_agent_creation_failure",
                            component="AgentRegistry",
                            error_message="Failed to create agents for multi-user testing",
                            expected_gap=True,
                            business_impact="Multi-user agent creation not working",
                            fix_complexity="high",
                            technical_details={
                                "alice_agent_created": bool(alice_agent),
                                "bob_agent_created": bool(bob_agent)
                            }
                        )
                        
                except Exception as multi_user_error:
                    self.capture_integration_gap(
                        test_name=test_name,
                        gap_type="multi_user_setup_error",
                        component="AgentRegistry",
                        error_message=str(multi_user_error),
                        expected_gap=True,
                        business_impact="Multi-user setup fails - isolation cannot be tested",
                        fix_complexity="high",
                        technical_details={
                            "error_type": type(multi_user_error).__name__
                        }
                    )
                    
            else:
                self.capture_integration_gap(
                    test_name=test_name,
                    gap_type="missing_agent_creation_method",
                    component="AgentRegistry",
                    error_message="Agent Registry missing create_agent_for_user method",
                    expected_gap=True,
                    business_impact="Cannot create agents for multi-user testing",
                    fix_complexity="critical"
                )
                
        except Exception as test_error:
            self.capture_integration_gap(
                test_name=test_name,
                gap_type="test_execution_error",
                component="TestFramework",
                error_message=str(test_error),
                expected_gap=False,
                business_impact="Cannot test multi-user WebSocket isolation",
                fix_complexity="medium",
                technical_details={"error_type": type(test_error).__name__}
            )
            raise
    
    # ===================== Integration Gap Analysis and Reporting =====================
    
    @pytest.mark.integration
    async def test_agent_registry_integration_gap_analysis(self):
        """
        Generate comprehensive Agent Registry integration gap analysis.
        
        This test analyzes all captured integration gaps and generates a structured
        report of Agent Registry WebSocket integration issues discovered.
        """
        test_name = "agent_registry_integration_gap_analysis"
        
        print(f"\n{'='*90}")
        print(f"AGENT REGISTRY WEBSOCKET INTEGRATION GAP ANALYSIS REPORT")
        print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        print(f"Total Integration Gaps Captured: {len(self.integration_gaps)}")
        print(f"{'='*90}")
        
        # Categorize gaps by component and severity
        gap_categories = {}
        critical_gaps = []
        high_severity_gaps = []
        expected_gaps = []
        unexpected_gaps = []
        
        for gap in self.integration_gaps:
            component = gap.component
            if component not in gap_categories:
                gap_categories[component] = []
            gap_categories[component].append(gap)
            
            if gap.fix_complexity == "critical":
                critical_gaps.append(gap)
            elif gap.fix_complexity == "high":
                high_severity_gaps.append(gap)
            
            if gap.expected_gap:
                expected_gaps.append(gap)
            else:
                unexpected_gaps.append(gap)
        
        # Print categorized analysis
        print(f"\nINTEGRATION GAPS BY COMPONENT:")
        for component, gaps in gap_categories.items():
            print(f"  {component.upper()}: {len(gaps)} gaps")
            for gap in gaps:
                status = "EXPECTED" if gap.expected_gap else "UNEXPECTED"
                severity = gap.fix_complexity.upper()
                print(f"    - {gap.gap_type}: {gap.business_impact} ({status}, {severity})")
        
        print(f"\nCRITICAL GAPS REQUIRING IMMEDIATE ATTENTION: {len(critical_gaps)}")
        for gap in critical_gaps:
            print(f"   ALERT:  {gap.component}: {gap.business_impact}")
            print(f"     Gap: {gap.gap_type}")
            print(f"     Error: {gap.error_message}")
        
        print(f"\nHIGH SEVERITY GAPS: {len(high_severity_gaps)}")
        for gap in high_severity_gaps:
            print(f"   WARNING: [U+FE0F]  {gap.component}: {gap.business_impact}")
            print(f"     Gap: {gap.gap_type}")
        
        print(f"\nEXPECTED vs UNEXPECTED GAPS:")
        print(f"  Expected: {len(expected_gaps)} (integration gaps successfully exposed)")
        print(f"  Unexpected: {len(unexpected_gaps)} (test framework or resolved issues)")
        
        if unexpected_gaps:
            print(f"\nUNEXPECTED GAP DETAILS:")
            for gap in unexpected_gaps:
                print(f"  - {gap.component}: {gap.error_message}")
        
        # Generate structured report for analysis
        integration_gap_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_gaps": len(self.integration_gaps),
            "critical_gaps": len(critical_gaps),
            "high_severity_gaps": len(high_severity_gaps),
            "expected_gaps": len(expected_gaps),
            "unexpected_gaps": len(unexpected_gaps),
            "gap_categories": {k: len(v) for k, v in gap_categories.items()},
            "key_business_impacts": list(set(gap.business_impact for gap in self.integration_gaps)),
            "detailed_gaps": [gap.to_dict() for gap in self.integration_gaps]
        }
        
        # Priority recommendations based on gap analysis
        priority_fixes = []
        if any(gap.gap_type == "missing_agent_registry_imports" for gap in self.integration_gaps):
            priority_fixes.append("P0: Fix Agent Registry import issues - complete system failure")
        if any(gap.gap_type == "missing_websocket_manager_integration" for gap in self.integration_gaps):
            priority_fixes.append("P1: Implement WebSocket manager integration in Agent Registry")
        if any(gap.gap_type == "websocket_bridge_creation_failure" for gap in self.integration_gaps):
            priority_fixes.append("P1: Fix WebSocket bridge factory pattern implementation")
        if any(gap.gap_type == "user_session_not_isolated" for gap in self.integration_gaps):
            priority_fixes.append("P0: CRITICAL - Fix multi-user session isolation (security risk)")
        
        print(f"\nPRIORITY FIXES RECOMMENDED:")
        for i, fix in enumerate(priority_fixes, 1):
            print(f"  {i}. {fix}")
        
        print(f"\nSTRUCTURED REPORT SUMMARY:")
        print(f"Components with gaps: {len(gap_categories)}")
        print(f"Business impacts identified: {len(integration_gap_report['key_business_impacts'])}")
        for impact in integration_gap_report['key_business_impacts']:
            print(f"  - {impact}")
        
        print(f"\n{'='*90}")
        print(f"AGENT REGISTRY WEBSOCKET INTEGRATION GAP ANALYSIS COMPLETE")
        print(f"Report available for remediation planning and implementation")
        print(f"{'='*90}\n")
        
        # Verify that we successfully captured integration gaps
        assert len(self.integration_gaps) > 0, "No integration gaps were exposed - tests may need revision"
        assert len(expected_gaps) > 0, "No expected gaps captured - integration gap detection not working"
        
        # Store report as class attribute for potential further use
        self.integration_gap_report = integration_gap_report
        
        return integration_gap_report


class MockToolDispatcher:
    """Mock tool dispatcher for testing Agent Registry integration."""
    
    def __init__(self, user_context, websocket_bridge=None):
        self.user_context = user_context
        self.websocket_bridge = websocket_bridge
        self.tools_executed = []
        
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any] = None):
        """Mock tool execution for testing."""
        execution_record = {
            "tool_name": tool_name,
            "parameters": parameters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": getattr(self.user_context, 'user_id', 'unknown')
        }
        self.tools_executed.append(execution_record)
        
        # Simulate WebSocket events during tool execution
        if self.websocket_bridge:
            await self.websocket_bridge.emit_tool_executing(tool_name, parameters)
            await self.websocket_bridge.emit_tool_completed(tool_name, {"success": True})
        
        return {"success": True, "result": "mock_execution"}


# Integration with pytest fixtures and markers
if __name__ == "__main__":
    import asyncio
    
    async def run_direct_tests():
        """Run tests directly for development and debugging."""
        print("Starting Agent Registry WebSocket Bridge Integration Tests...")
        
        test_instance = TestAgentRegistryWebSocketBridge()
        test_instance.setup_method()
        
        try:
            # Run key tests to expose integration gaps
            await test_instance.test_agent_registry_websocket_manager_initialization_gap()
            await test_instance.test_agent_registry_websocket_bridge_creation_gap()
            await test_instance.test_agent_registry_websocket_event_emission_gap()
            await test_instance.test_agent_registry_multi_user_websocket_isolation_gap()
            
            # Generate analysis report
            report = await test_instance.test_agent_registry_integration_gap_analysis()
            
            print(f" PASS:  Agent Registry integration gap testing completed")
            print(f"    ->  {report['total_gaps']} integration gaps captured")
            print(f"    ->  {report['critical_gaps']} critical gaps requiring immediate attention")
            print(f"    ->  {report['expected_gaps']} expected gaps successfully exposed")
            
        except Exception as e:
            print(f"[U+2717] Agent Registry integration gap testing encountered issues: {e}")
            raise
    
    # Run tests if executed directly
    asyncio.run(run_direct_tests())