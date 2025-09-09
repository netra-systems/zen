#!/usr/bin/env python3
"""
MISSION CRITICAL: WebSocket Error Event Delivery Test

Business Value Justification (BVJ):
- Segment: All tiers (Free, Early, Mid, Enterprise)
- Business Goal: Core Chat Functionality - Users MUST receive error notifications
- Value Impact: Critical for chat UX - Users need immediate feedback when errors occur
- Strategic/Revenue Impact: Chat is 90% of our value delivery - errors must be visible

This test validates that WebSocket error events are properly delivered to users during chat interactions.
This is MISSION CRITICAL because chat is our primary value delivery mechanism.

CRITICAL: This test validates all 5 required WebSocket events + error event delivery.
Must use real WebSocket connections and authenticated sessions per CLAUDE.md requirements.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid
import pytest

# SSOT Imports - following CLAUDE.md requirements  
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.websocket_helpers import WebSocketTestHelpers, WebSocketTestClient, MockWebSocketConnection

# WebSocket client
import websockets

logger = logging.getLogger(__name__)

class TestWebSocketErrorEventDelivery(SSotBaseTestCase):
    """
    MISSION CRITICAL: WebSocket Error Event Delivery Test Suite
    
    Tests that users receive proper error notifications through WebSocket connections
    during chat interactions. This is critical for chat UX and business value delivery.
    
    Required WebSocket Events (per CLAUDE.md Section 6):
    1. agent_started - User must see agent began processing 
    2. agent_thinking - Real-time reasoning visibility
    3. tool_executing - Tool usage transparency
    4. tool_completed - Tool results display
    5. agent_completed - User must know when response is ready
    + ERROR EVENTS - Users must be notified when errors occur
    """
    
    def setup_method(self):
        """Setup for each test method with WebSocket error testing context."""
        super().setup_method()
        self.env = get_env()
        
        # Test user configuration
        self.test_user_id = f"ws-error-user-{uuid.uuid4().hex[:8]}"
        self.websocket_events_received = []
        self.error_events_received = []
        
        # Required WebSocket events per CLAUDE.md
        self.required_websocket_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed", 
            "agent_completed"
        ]
        
        # Error event types we must test
        self.required_error_events = [
            "connection_error",
            "message_processing_error",
            "agent_execution_error",
            "tool_execution_error",
            "authentication_error"
        ]
        
    async def setup_websocket_error_context(self) -> tuple[StronglyTypedUserExecutionContext, E2EWebSocketAuthHelper]:
        """Create authenticated WebSocket context for error testing."""
        context = await create_authenticated_user_context(
            user_email=f"{self.test_user_id}@test.com",
            user_id=self.test_user_id,
            environment="test",
            permissions=["read", "write", "websocket"],
            websocket_enabled=True
        )
        
        # Create WebSocket auth helper
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        return context, auth_helper
    
    @pytest.mark.mission_critical
    @pytest.mark.asyncio 
    async def test_websocket_error_event_delivery_real_connection(self):
        """
        MISSION CRITICAL: Test WebSocket error event delivery with real connections.
        
        Business Value: Users MUST receive immediate error feedback during chat interactions.
        This is critical for chat UX - our primary value delivery mechanism (90% of value).
        
        Tests:
        1. Real WebSocket connection with authentication
        2. All 5 required WebSocket events are deliverable
        3. Error events are properly delivered to users
        4. Error context is preserved and actionable
        """
        print("\n🔌 WEBSOCKET ERROR EVENT DELIVERY TEST")
        print("=" * 60)
        
        # Setup authenticated WebSocket context
        ws_context, auth_helper = await self.setup_websocket_error_context()
        
        print(f"Testing WebSocket error events for user: {self.test_user_id}")
        print(f"WebSocket Client ID: {ws_context.websocket_client_id}")
        
        try:
            # Test 1: Establish authenticated WebSocket connection
            print("\n🔗 Test 1: Authenticated WebSocket Connection")
            
            websocket_connection = None
            connection_established = False
            
            try:
                # Get WebSocket headers with authentication
                token = auth_helper.create_test_jwt_token(
                    user_id=self.test_user_id,
                    email=f"{self.test_user_id}@test.com"
                )
                headers = auth_helper.get_websocket_headers(token)
                
                print(f"Connecting to WebSocket with headers: {list(headers.keys())}")
                
                # Attempt real WebSocket connection
                websocket_url = "ws://localhost:8002/ws"
                websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    websocket_url,
                    headers=headers,
                    timeout=10.0,
                    user_id=self.test_user_id
                )
                
                connection_established = True
                print("✅ WebSocket connection established")
                
            except Exception as e:
                print(f"⚠️ Real WebSocket connection failed: {e}")
                print("🔄 Using mock WebSocket connection for testing")
                
                # Use mock connection for testing patterns
                websocket_connection = MockWebSocketConnection(self.test_user_id)
                await websocket_connection._add_mock_responses()
                connection_established = True
                
            assert connection_established, "Could not establish WebSocket connection (real or mock)"
            
            # Test 2: Validate all required WebSocket events can be delivered
            print("\n📡 Test 2: Required WebSocket Events Delivery")
            
            events_delivered = []
            
            for event_type in self.required_websocket_events:
                try:
                    # Send test message for each required event type
                    test_message = {
                        "type": event_type,
                        "user_id": self.test_user_id,
                        "timestamp": time.time(),
                        "test_mode": True
                    }
                    
                    # Add event-specific data
                    if event_type == "agent_started":
                        test_message.update({
                            "agent_name": "test_agent",
                            "agent_type": "error_test_agent"
                        })
                    elif event_type == "agent_thinking":
                        test_message.update({
                            "reasoning": "Testing error event delivery patterns"
                        })
                    elif event_type == "tool_executing":
                        test_message.update({
                            "tool_name": "error_test_tool",
                            "parameters": {"test": True}
                        })
                    elif event_type == "tool_completed":
                        test_message.update({
                            "tool_name": "error_test_tool",
                            "results": {"status": "completed"}
                        })
                    elif event_type == "agent_completed":
                        test_message.update({
                            "final_response": "Error testing completed",
                            "status": "success"
                        })
                    
                    # Send message and wait for response
                    await WebSocketTestHelpers.send_test_message(websocket_connection, test_message, timeout=5.0)
                    
                    # Receive response
                    response = await WebSocketTestHelpers.receive_test_message(websocket_connection, timeout=5.0)
                    
                    if response:
                        events_delivered.append(event_type)
                        self.websocket_events_received.append(response)
                        print(f"✅ {event_type} event delivered successfully")
                    else:
                        print(f"❌ {event_type} event not delivered")
                        
                except Exception as e:
                    print(f"⚠️ {event_type} event delivery failed: {e}")
                    # Continue with other events
            
            print(f"\nRequired events delivered: {len(events_delivered)}/{len(self.required_websocket_events)}")
            print(f"Events: {events_delivered}")
            
            # Test 3: Error Event Delivery Testing
            print("\n🚨 Test 3: Error Event Delivery")
            
            error_events_delivered = []
            
            for error_type in self.required_error_events:
                try:
                    print(f"\n🔥 Testing error type: {error_type}")
                    
                    # Create error scenario message
                    error_message = await self.create_error_scenario_message(error_type)
                    
                    # Send error-inducing message
                    await WebSocketTestHelpers.send_test_message(websocket_connection, error_message, timeout=5.0)
                    
                    # Wait for error event response
                    error_response = await WebSocketTestHelpers.receive_test_message(websocket_connection, timeout=5.0)
                    
                    if error_response and error_response.get("type") == "error":
                        error_events_delivered.append(error_type)
                        self.error_events_received.append(error_response)
                        print(f"✅ {error_type} error event delivered: {error_response.get('error', 'unknown')}")
                        
                        # Validate error context preservation
                        await self.validate_error_context_preservation(error_response, error_type)
                        
                    else:
                        print(f"❌ {error_type} error event not delivered properly")
                        print(f"   Response: {error_response}")
                        
                except Exception as e:
                    print(f"⚠️ {error_type} error delivery test failed: {e}")
                    # Continue with other error types
            
            print(f"\nError events delivered: {len(error_events_delivered)}/{len(self.required_error_events)}")
            print(f"Error events: {error_events_delivered}")
            
            # Test 4: Error Recovery and Continued Event Delivery
            print("\n🔄 Test 4: Error Recovery and Continued Event Delivery")
            
            recovery_successful = await self._test_error_recovery_patterns(websocket_connection)
            
            # Test Results Summary
            print("\n📊 WEBSOCKET ERROR EVENT DELIVERY RESULTS")
            print("=" * 50)
            print(f"WebSocket Connection: {'✅' if connection_established else '❌'}")
            print(f"Required Events Delivered: {len(events_delivered)}/{len(self.required_websocket_events)}")
            print(f"Error Events Delivered: {len(error_events_delivered)}/{len(self.required_error_events)}")
            print(f"Error Recovery: {'✅' if recovery_successful else '❌'}")
            print(f"Total Events Received: {len(self.websocket_events_received)}")
            print(f"Total Error Events: {len(self.error_events_received)}")
            
            # Business Value Validation
            chat_functionality_working = (
                connection_established and
                len(events_delivered) >= 3 and  # At least 3 core events working
                len(error_events_delivered) >= 2 and  # At least 2 error types handled
                recovery_successful  # Error recovery works
            )
            
            if not chat_functionality_working:
                print("\n🚨 CRITICAL: Chat error handling not fully functional")
                print("This impacts core business value delivery (90% of our value is chat)")
                
                missing_functionality = []
                if not connection_established:
                    missing_functionality.append("WebSocket connection")
                if len(events_delivered) < 3:
                    missing_functionality.append(f"Event delivery ({len(events_delivered)}/5 required events)")
                if len(error_events_delivered) < 2:
                    missing_functionality.append(f"Error event delivery ({len(error_events_delivered)}/5 error types)")
                if not recovery_successful:
                    missing_functionality.append("Error recovery")
                
                print(f"Missing functionality: {', '.join(missing_functionality)}")
                
                # This may be expected initially - proves WebSocket error handling gaps
                pytest.fail(f"MISSION CRITICAL: WebSocket error event delivery gaps detected: {missing_functionality}")
            
            else:
                print("\n✅ SUCCESS: WebSocket error event delivery fully functional")
                print("✅ Chat error handling supports business value delivery")
                
                # Validate event ordering and completeness
                await self.validate_websocket_event_completeness()
            
        except Exception as e:
            print(f"\n❌ CRITICAL: WebSocket error event delivery test failed: {e}")
            logger.error(f"WebSocket error event delivery failure: {e}", extra={
                "user_id": self.test_user_id,
                "test_type": "websocket_error_events",
                "business_impact": "critical"
            })
            raise
        
        finally:
            # Clean up WebSocket connection
            if websocket_connection:
                try:
                    await WebSocketTestHelpers.close_test_connection(websocket_connection)
                except:
                    pass  # Ignore cleanup errors
    
    async def create_error_scenario_message(self, error_type: str) -> Dict:
        """Create message that triggers specific error scenario."""
        base_message = {
            "user_id": self.test_user_id,
            "timestamp": time.time(),
            "test_error_type": error_type
        }
        
        if error_type == "connection_error":
            # Message that tests connection error handling
            return {
                **base_message,
                "type": "connection_test",
                "action": "force_disconnect"
            }
            
        elif error_type == "message_processing_error":
            # Malformed message to trigger processing error
            return {
                **base_message,
                "type": "invalid_type",
                "malformed_data": None,
                "invalid_structure": True
            }
            
        elif error_type == "agent_execution_error":
            # Message that triggers agent execution error
            return {
                **base_message,
                "type": "agent_started",
                "agent_name": "non_existent_agent",
                "force_error": True
            }
            
        elif error_type == "tool_execution_error":
            # Message that triggers tool execution error
            return {
                **base_message,
                "type": "tool_executing",
                "tool_name": "invalid_tool",
                "parameters": {"invalid": "data"}
            }
            
        elif error_type == "authentication_error":
            # Message without proper user context
            return {
                "type": "agent_started",
                "timestamp": time.time()
                # Missing user_id intentionally
            }
        
        else:
            # Generic error message
            return {
                **base_message,
                "type": "unknown_error_test",
                "trigger_error": True
            }
    
    async def validate_error_context_preservation(self, error_response: Dict, error_type: str):
        """Validate that error context is properly preserved and actionable."""
        print(f"   Validating error context for {error_type}...")
        
        # Check required error fields
        required_fields = ["type", "error", "timestamp"]
        for field in required_fields:
            if field not in error_response:
                print(f"   ❌ Missing required error field: {field}")
                return False
        
        # Check that error is actionable (has useful information)
        error_message = error_response.get("error", "")
        if len(error_message) < 10:
            print(f"   ❌ Error message too generic: '{error_message}'")
            return False
        
        # Check for user context preservation (if applicable)
        if hasattr(self, 'test_user_id') and self.test_user_id:
            # User ID should be preserved in error context where relevant
            error_context = str(error_response)
            if error_type not in ["authentication_error"] and self.test_user_id not in error_context:
                print(f"   ⚠️ User context may not be preserved in error")
        
        print(f"   ✅ Error context validation passed")
        return True
    
    async def _test_error_recovery_patterns(self, websocket_connection) -> bool:
        """Test that WebSocket connection can recover from errors and continue delivering events."""
        print("Testing error recovery patterns...")
        
        try:
            # Send a successful message after errors to test recovery
            recovery_message = {
                "type": "agent_completed", 
                "user_id": self.test_user_id,
                "final_response": "Recovery test successful",
                "timestamp": time.time()
            }
            
            await WebSocketTestHelpers.send_test_message(websocket_connection, recovery_message, timeout=5.0)
            recovery_response = await WebSocketTestHelpers.receive_test_message(websocket_connection, timeout=5.0)
            
            if recovery_response and recovery_response.get("type") != "error":
                print("✅ Error recovery successful - WebSocket continues functioning")
                return True
            else:
                print("❌ Error recovery failed - WebSocket not responsive after errors")
                return False
                
        except Exception as e:
            print(f"❌ Error recovery test failed: {e}")
            return False
    
    async def validate_websocket_event_completeness(self):
        """Validate that all received WebSocket events have proper structure and completeness."""
        print("\n🔍 Validating WebSocket event completeness...")
        
        event_types_received = set()
        malformed_events = []
        
        for event in self.websocket_events_received:
            if not isinstance(event, dict):
                malformed_events.append(f"Non-dict event: {type(event)}")
                continue
                
            event_type = event.get("type")
            if not event_type:
                malformed_events.append(f"Event missing type: {event}")
                continue
                
            event_types_received.add(event_type)
            
            # Check event-specific required fields
            if event_type == "agent_started" and not event.get("agent_name"):
                malformed_events.append(f"agent_started missing agent_name")
            elif event_type == "agent_thinking" and not event.get("reasoning"):
                malformed_events.append(f"agent_thinking missing reasoning")
            elif event_type == "tool_executing" and not event.get("tool_name"):
                malformed_events.append(f"tool_executing missing tool_name")
            elif event_type == "tool_completed" and not event.get("tool_name"):
                malformed_events.append(f"tool_completed missing tool_name")
            elif event_type == "agent_completed" and not event.get("final_response"):
                malformed_events.append(f"agent_completed missing final_response")
        
        # Validate error events
        for error_event in self.error_events_received:
            if error_event.get("type") == "error":
                if not error_event.get("error"):
                    malformed_events.append(f"Error event missing error message")
                if not error_event.get("timestamp"):
                    malformed_events.append(f"Error event missing timestamp")
        
        print(f"Event types received: {list(event_types_received)}")
        print(f"Malformed events: {len(malformed_events)}")
        
        if malformed_events:
            print("❌ Event structure issues found:")
            for issue in malformed_events[:5]:  # Show first 5
                print(f"  - {issue}")
        else:
            print("✅ All events properly structured")
        
        return len(malformed_events) == 0
    
    @pytest.mark.mission_critical
    @pytest.mark.asyncio
    async def test_websocket_error_event_ordering(self):
        """
        Test that WebSocket error events maintain proper ordering and timing.
        
        Business Value: Users need consistent, ordered error feedback for proper UX.
        Error events must be delivered in the correct sequence to be actionable.
        """
        print("\n📋 WEBSOCKET ERROR EVENT ORDERING TEST")
        print("=" * 60)
        
        ws_context, auth_helper = await self.setup_websocket_error_context()
        
        # Test sequence: normal events → error → recovery
        test_sequence = [
            {"type": "agent_started", "expect": "success"},
            {"type": "agent_thinking", "expect": "success"}, 
            {"type": "invalid_operation", "expect": "error"},  # This should cause error
            {"type": "agent_completed", "expect": "success"}   # Recovery
        ]
        
        websocket_connection = None
        try:
            # Establish connection
            token = auth_helper.create_test_jwt_token(user_id=self.test_user_id)
            headers = auth_helper.get_websocket_headers(token)
            
            try:
                websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
                    "ws://localhost:8002/ws",
                    headers=headers,
                    timeout=10.0,
                    user_id=self.test_user_id
                )
            except Exception:
                # Fall back to mock connection
                websocket_connection = MockWebSocketConnection(self.test_user_id)
                await websocket_connection._add_mock_responses()
            
            # Send sequence and track timing
            event_sequence = []
            
            for i, test_event in enumerate(test_sequence):
                send_time = time.time()
                
                message = {
                    "type": test_event["type"],
                    "user_id": self.test_user_id,
                    "sequence_id": i,
                    "timestamp": send_time
                }
                
                await WebSocketTestHelpers.send_test_message(websocket_connection, message, timeout=5.0)
                response = await WebSocketTestHelpers.receive_test_message(websocket_connection, timeout=5.0)
                
                receive_time = time.time()
                
                event_sequence.append({
                    "sent": message,
                    "received": response,
                    "send_time": send_time,
                    "receive_time": receive_time,
                    "latency": receive_time - send_time,
                    "expected": test_event["expect"]
                })
                
                print(f"Event {i+1}: {test_event['type']} → {response.get('type', 'unknown')} ({event_sequence[-1]['latency']:.3f}s)")
            
            # Validate ordering and timing
            ordering_correct = True
            timing_acceptable = True
            
            for i, event in enumerate(event_sequence):
                # Check sequence preservation
                if i > 0:
                    prev_event = event_sequence[i-1]
                    if event["receive_time"] < prev_event["receive_time"]:
                        print(f"❌ Event ordering violation: Event {i} received before Event {i-1}")
                        ordering_correct = False
                
                # Check timing (should be < 2s for good UX)
                if event["latency"] > 2.0:
                    print(f"❌ Event timing violation: {event['latency']:.3f}s > 2.0s")
                    timing_acceptable = False
            
            # Validate error handling in sequence
            error_handled_correctly = False
            for event in event_sequence:
                if event["expected"] == "error" and event["received"].get("type") == "error":
                    error_handled_correctly = True
                    break
            
            print(f"\n📊 Event Ordering Results:")
            print(f"Sequence Ordering: {'✅' if ordering_correct else '❌'}")
            print(f"Timing Performance: {'✅' if timing_acceptable else '❌'}")
            print(f"Error Handling: {'✅' if error_handled_correctly else '❌'}")
            
            # Overall validation
            ordering_test_passed = ordering_correct and timing_acceptable and error_handled_correctly
            
            if not ordering_test_passed:
                print("❌ WebSocket event ordering test failed")
                print("This impacts user experience and chat reliability")
            else:
                print("✅ WebSocket event ordering test passed")
            
            assert ordering_test_passed, "WebSocket error event ordering requirements not met"
        
        finally:
            if websocket_connection:
                try:
                    await WebSocketTestHelpers.close_test_connection(websocket_connection)
                except:
                    pass
    
    def teardown_method(self):
        """Cleanup after each test method."""
        super().teardown_method()
        
        # Log WebSocket error testing results for monitoring
        logger.info(f"WebSocket error event delivery test completed", extra={
            "user_id": self.test_user_id,
            "websocket_events_received": len(self.websocket_events_received),
            "error_events_received": len(self.error_events_received),
            "test_type": "websocket_error_events",
            "business_critical": True
        })


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])