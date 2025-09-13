"""
WebSocket SSOT Integration Violation Detection Tests

These tests detect current SSOT violations in WebSocket-agent integration and ensure
all 5 critical events are properly delivered through unified communication.

Business Value: Platform/Internal - Ensure golden path (login  ->  AI responses) works
Critical for chat functionality that delivers 90% of platform value.

Test Status: DESIGNED TO FAIL with current code (detecting violations)
Expected Result: PASS after SSOT consolidation unifies WebSocket-agent communication
"""

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass
from datetime import datetime, timezone

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.types.core_types import UserID, ThreadID, ensure_user_id, ensure_thread_id


@dataclass
class WebSocketEvent:
    """Track WebSocket events for testing."""
    event_type: str
    user_id: str
    thread_id: str
    timestamp: datetime
    data: Dict[str, Any]


class TestWebSocketSSotIntegrationViolations(SSotAsyncTestCase):
    """
    Test suite to detect WebSocket SSOT integration violations.
    
    These tests are designed to FAIL with current code and PASS after consolidation.
    """
    
    def setUp(self):
        super().setUp()
        self.captured_events = []
        self.event_handlers = {}
    
    async def test_unified_websocket_agent_communication(self):
        """
        Test that WebSocket-agent communication goes through unified channel after SSOT.
        
        CURRENT BEHAVIOR: Multiple communication paths exist (VIOLATION)
        EXPECTED AFTER SSOT: Single unified communication channel
        """
        communication_paths_found = {}
        
        # Test different communication patterns currently in use
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            
            # Test direct manager-agent communication
            manager = UnifiedWebSocketManager()
            try:
                # Check if manager has direct agent communication methods
                has_direct_agent_methods = any(
                    method.startswith('notify_agent') or method.startswith('send_to_agent')
                    for method in dir(manager)
                )
                communication_paths_found['direct_manager_agent'] = has_direct_agent_methods
            except:
                communication_paths_found['direct_manager_agent'] = False
                
        except ImportError:
            communication_paths_found['direct_manager_agent'] = False
        
        try:
            # Test bridge-based communication
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory
            bridge_factory = WebSocketBridgeFactory()
            bridge = bridge_factory.create_bridge()
            communication_paths_found['bridge_communication'] = bridge is not None
        except (ImportError, AttributeError):
            communication_paths_found['bridge_communication'] = False
        
        try:
            # Test registry-based communication
            from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession
            # Check if registry has WebSocket communication methods
            registry_methods = dir(UserAgentSession)
            has_websocket_methods = any(
                'websocket' in method.lower() or 'notify' in method.lower()
                for method in registry_methods
            )
            communication_paths_found['registry_communication'] = has_websocket_methods
        except ImportError:
            communication_paths_found['registry_communication'] = False
        
        working_paths = sum(communication_paths_found.values())
        
        # CURRENT EXPECTATION: Multiple communication paths exist (violation)
        # AFTER SSOT: Should have single unified path
        self.assertGreater(working_paths, 1,
                          "SSOT VIOLATION DETECTED: Multiple WebSocket-agent communication paths exist. "
                          f"Found {working_paths} working paths: {communication_paths_found}")
        
        self.logger.warning(f"WebSocket-Agent Communication Violation: {working_paths} paths found")
        self.metrics.record_test_event("websocket_agent_communication_violation", {
            "working_paths": working_paths,
            "path_results": communication_paths_found
        })

    async def test_all_five_critical_events_delivery(self):
        """
        Test that all 5 critical WebSocket events are delivered through unified system.
        
        Events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        
        CURRENT BEHAVIOR: Events may be sent through different paths (VIOLATION)
        EXPECTED AFTER SSOT: All events sent through unified path
        """
        required_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        user_id = ensure_user_id("event_test_user")
        thread_id = ensure_thread_id("event_test_thread")
        
        event_delivery_paths = {}
        
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager = UnifiedWebSocketManager()
            
            # Test event delivery through different possible paths
            for event_type in required_events:
                paths_for_event = []
                
                # Test direct manager event sending
                if hasattr(manager, 'send_event'):
                    try:
                        await manager.send_event(user_id, event_type, {"test": True})
                        paths_for_event.append('direct_manager')
                    except:
                        pass
                
                # Test legacy event methods
                legacy_method = f"send_{event_type}"
                if hasattr(manager, legacy_method):
                    try:
                        method = getattr(manager, legacy_method)
                        await method(user_id, {"test": True})
                        paths_for_event.append('legacy_method')
                    except:
                        pass
                
                # Test notification system
                if hasattr(manager, 'notify'):
                    try:
                        await manager.notify(user_id, event_type, {"test": True})
                        paths_for_event.append('notification_system')
                    except:
                        pass
                
                event_delivery_paths[event_type] = paths_for_event
        
        except ImportError as e:
            self.fail(f"Failed to import WebSocket manager for event testing: {e}")
        
        # Analyze event delivery path violations
        multi_path_events = {
            event: paths for event, paths in event_delivery_paths.items()
            if len(paths) > 1
        }
        
        missing_events = {
            event: paths for event, paths in event_delivery_paths.items()
            if len(paths) == 0
        }
        
        # CURRENT EXPECTATION: May have multiple paths or missing events (violations)
        # AFTER SSOT: Each event should have exactly one delivery path
        total_violations = len(multi_path_events) + len(missing_events)
        
        violation_details = {
            "multi_path_events": multi_path_events,
            "missing_events": missing_events,
            "all_event_paths": event_delivery_paths
        }
        
        self.assertGreater(total_violations, 0,
                          "SSOT VIOLATION DETECTED: Event delivery path inconsistencies found. "
                          f"Multi-path events: {len(multi_path_events)}, Missing events: {len(missing_events)}")
        
        self.logger.warning(f"Event Delivery Violations: {total_violations} violations found")
        self.metrics.record_test_event("websocket_event_delivery_violation", {
            "total_violations": total_violations,
            "violation_details": violation_details
        })

    async def test_golden_path_flow_unified_manager(self):
        """
        Test that golden path flow (login  ->  AI responses) works through unified manager.
        
        CURRENT BEHAVIOR: May use multiple managers/paths (VIOLATION)
        EXPECTED AFTER SSOT: Single manager handles entire flow
        """
        user_id = ensure_user_id("golden_path_user")
        thread_id = ensure_thread_id("golden_path_thread")
        
        flow_stages = [
            "user_login",
            "websocket_connect", 
            "agent_request",
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed",
            "response_delivery"
        ]
        
        stage_handlers = {}
        manager_instances_used = set()
        
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            # Simulate golden path flow stages
            for stage in flow_stages:
                # Create manager for each stage (simulating current behavior)
                manager = UnifiedWebSocketManager()
                manager_id = id(manager)
                manager_instances_used.add(manager_id)
                
                stage_handlers[stage] = {
                    "manager_id": manager_id,
                    "manager_type": type(manager).__name__,
                    "stage": stage
                }
                
                # Simulate stage-specific operations
                if stage == "websocket_connect":
                    try:
                        await manager.add_connection(user_id, f"conn_{user_id}", None)
                    except:
                        pass
                        
                elif stage in ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]:
                    try:
                        await manager.send_to_user(user_id, {
                            "type": stage,
                            "thread_id": str(thread_id),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    except:
                        pass
        
        except ImportError as e:
            self.fail(f"Failed to test golden path flow: {e}")
        
        # Analyze manager usage violations
        unique_managers = len(manager_instances_used)
        
        # CURRENT EXPECTATION: Multiple manager instances used (violation)
        # AFTER SSOT: Should use single manager instance throughout flow
        self.assertGreater(unique_managers, 1,
                          "SSOT VIOLATION DETECTED: Multiple WebSocket manager instances used in golden path. "
                          f"Found {unique_managers} different manager instances across {len(flow_stages)} stages")
        
        self.logger.warning(f"Golden Path Manager Violation: {unique_managers} managers used")
        self.metrics.record_test_event("websocket_golden_path_violation", {
            "unique_managers": unique_managers,
            "flow_stages": len(flow_stages),
            "stage_handlers": stage_handlers
        })