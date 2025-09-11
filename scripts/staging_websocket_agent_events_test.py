#!/usr/bin/env python3
"""
MISSION CRITICAL: WebSocket Agent Events Test for Staging
Business Value: $500K+ ARR - Core chat functionality

Tests the 5 REQUIRED WebSocket events for golden path:
1. agent_started - User must see agent began processing their problem
2. agent_thinking - Real-time reasoning visibility 
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User must know when valuable response is ready

This test validates the CRITICAL infrastructure for chat value delivery.
"""

import asyncio
import json
import time
import uuid
import websockets
from datetime import datetime
from typing import Dict, Any, List, Set


# Staging WebSocket URL
STAGING_WEBSOCKET_URL = "wss://netra-backend-staging-701982941522.us-central1.run.app/ws"

# Required WebSocket events for substantive chat value
REQUIRED_EVENTS = {
    "agent_started",
    "agent_thinking", 
    "tool_executing",
    "tool_completed",
    "agent_completed"
}


class WebSocketEventCapture:
    """Captures and validates WebSocket events from staging"""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_types: Set[str] = set()
        self.start_time = time.time()
        self.connected = False
        self.connection_ready = False
    
    def record_event(self, event_data: Dict[str, Any]) -> None:
        """Record an event with timestamp"""
        event_type = event_data.get("type", "unknown")
        event_with_timestamp = {
            **event_data,
            "capture_timestamp": time.time(),
            "relative_time": time.time() - self.start_time
        }
        
        self.events.append(event_with_timestamp)
        self.event_types.add(event_type)
        
        print(f"📨 Event captured: {event_type} (t+{event_with_timestamp['relative_time']:.3f}s)")
    
    def has_required_events(self) -> bool:
        """Check if all required events were received"""
        return REQUIRED_EVENTS.issubset(self.event_types)
    
    def get_missing_events(self) -> Set[str]:
        """Get events that were not received"""
        return REQUIRED_EVENTS - self.event_types
    
    def get_event_summary(self) -> Dict:
        """Get summary of captured events"""
        return {
            "total_events": len(self.events),
            "unique_types": len(self.event_types),
            "event_types": list(self.event_types),
            "required_events_received": len(REQUIRED_EVENTS & self.event_types),
            "required_events_total": len(REQUIRED_EVENTS),
            "missing_events": list(self.get_missing_events()),
            "has_all_required": self.has_required_events()
        }


async def test_websocket_connection_and_events():
    """Test WebSocket connection and event capture"""
    print("\n🔌 Testing WebSocket Connection and Event Capture...")
    
    capture = WebSocketEventCapture()
    test_duration = 30  # seconds
    
    try:
        print(f"Connecting to: {STAGING_WEBSOCKET_URL}")
        async with websockets.connect(
            STAGING_WEBSOCKET_URL,
            close_timeout=10,
            ping_interval=20,
            ping_timeout=10
        ) as websocket:
            capture.connected = True
            print("✅ WebSocket connection established")
            
            # Listen for initial connection messages
            print("🔄 Listening for WebSocket events...")
            start_listening = time.time()
            
            try:
                while time.time() - start_listening < test_duration:
                    # Set a shorter timeout for message receiving
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        
                        # Parse message
                        try:
                            event_data = json.loads(message)
                            capture.record_event(event_data)
                            
                            # Check for connection ready message
                            if (event_data.get("type") == "system_message" and 
                                event_data.get("data", {}).get("event") == "connection_established"):
                                capture.connection_ready = True
                                print("✅ WebSocket connection confirmed ready")
                                
                        except json.JSONDecodeError:
                            print(f"📄 Non-JSON message received: {message[:100]}...")
                            
                    except asyncio.TimeoutError:
                        print("⏱️  No new messages (timeout)")
                        # Send a ping to keep connection alive
                        await websocket.ping()
                        
            except websockets.exceptions.ConnectionClosed:
                print("🔌 WebSocket connection closed by server")
            except Exception as e:
                print(f"⚠️  Error during message listening: {e}")
            
            elapsed = time.time() - start_listening
            print(f"📊 Finished listening after {elapsed:.1f}s")
            
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False
    
    return capture


async def test_agent_event_simulation():
    """Simulate sending a message that should trigger agent events"""
    print("\n🤖 Testing Agent Event Simulation...")
    
    capture = WebSocketEventCapture()
    
    try:
        async with websockets.connect(
            STAGING_WEBSOCKET_URL,
            close_timeout=15
        ) as websocket:
            print("✅ Connected for agent event testing")
            
            # Wait for connection ready
            await asyncio.sleep(2)
            
            # Send a test message that should trigger agent workflow
            test_message = {
                "type": "chat_message",
                "data": {
                    "message": "Hello, can you help me optimize my business processes?",
                    "thread_id": str(uuid.uuid4()),
                    "user_id": "test-user-" + str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            print(f"📤 Sending test message: {test_message['data']['message']}")
            await websocket.send(json.dumps(test_message))
            
            # Listen for agent events
            print("🔄 Listening for agent events...")
            listen_duration = 60  # Give more time for agent processing
            start_time = time.time()
            
            while time.time() - start_time < listen_duration:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    
                    try:
                        event_data = json.loads(message)
                        capture.record_event(event_data)
                        
                        # Check if we've received all required events
                        if capture.has_required_events():
                            print("🎉 All required agent events received!")
                            break
                            
                    except json.JSONDecodeError:
                        print(f"📄 Non-JSON response: {message[:100]}...")
                        
                except asyncio.TimeoutError:
                    print("⏱️  Waiting for more events...")
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 Connection closed during agent test")
                    break
            
            elapsed = time.time() - start_time
            print(f"📊 Agent event test completed after {elapsed:.1f}s")
            
    except Exception as e:
        print(f"❌ Agent event simulation failed: {e}")
        return None
    
    return capture


async def main():
    """Run comprehensive WebSocket agent events test"""
    print("=" * 80)
    print("🚨 MISSION CRITICAL: WebSocket Agent Events Test")
    print("Business Impact: $500K+ ARR - Core Chat Functionality")
    print("Environment: Staging")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    print(f"🎯 Testing for {len(REQUIRED_EVENTS)} REQUIRED events:")
    for i, event in enumerate(REQUIRED_EVENTS, 1):
        print(f"   {i}. {event}")
    
    overall_start = time.time()
    
    # Test 1: Basic WebSocket Connection and Event Listening
    print(f"\n{'='*60}")
    print("TEST 1: WebSocket Connection and Event Capture")
    print(f"{'='*60}")
    
    connection_capture = await test_websocket_connection_and_events()
    
    if not connection_capture:
        print("❌ Connection test failed - aborting")
        return
    
    # Test 2: Agent Event Simulation
    print(f"\n{'='*60}")
    print("TEST 2: Agent Event Flow Simulation")
    print(f"{'='*60}")
    
    agent_capture = await test_agent_event_simulation()
    
    total_time = time.time() - overall_start
    
    # Results Analysis
    print(f"\n{'='*80}")
    print("🏁 WEBSOCKET AGENT EVENTS TEST RESULTS")
    print(f"{'='*80}")
    
    # Connection Test Results
    if connection_capture:
        conn_summary = connection_capture.get_event_summary()
        print(f"🔌 Connection Test:")
        print(f"   Connected: ✅")
        print(f"   Connection Ready: {'✅' if connection_capture.connection_ready else '❌'}")
        print(f"   Events Captured: {conn_summary['total_events']}")
        print(f"   Event Types: {conn_summary['event_types']}")
    
    # Agent Test Results
    if agent_capture:
        agent_summary = agent_capture.get_event_summary()
        print(f"\n🤖 Agent Event Test:")
        print(f"   Events Captured: {agent_summary['total_events']}")
        print(f"   Required Events: {agent_summary['required_events_received']}/{agent_summary['required_events_total']}")
        print(f"   Event Types Received: {agent_summary['event_types']}")
        
        if agent_summary['missing_events']:
            print(f"   ❌ Missing Events: {agent_summary['missing_events']}")
        else:
            print(f"   ✅ All required events received!")
    
    # Overall Assessment
    print(f"\n📊 OVERALL ASSESSMENT:")
    print(f"   Total Test Time: {total_time:.3f}s (Real test: {'✅' if total_time > 0.5 else '❌'})")
    
    # Success Criteria
    success_criteria = {
        "websocket_connects": connection_capture is not False,
        "connection_ready": connection_capture and connection_capture.connection_ready,
        "events_received": agent_capture and len(agent_capture.events) > 0,
        "all_required_events": agent_capture and agent_capture.has_required_events(),
        "real_execution_time": total_time > 0.5
    }
    
    print(f"\n🎯 SUCCESS CRITERIA:")
    for criterion, passed in success_criteria.items():
        status = "✅" if passed else "❌"
        print(f"{status} {criterion}")
    
    all_passed = all(success_criteria.values())
    
    print(f"\n{'🚀 GOLDEN PATH READY' if all_passed else '⚠️ ISSUES FOUND'}")
    
    if agent_capture:
        missing = agent_capture.get_missing_events()
        if missing:
            print(f"\n🚨 CRITICAL: Missing WebSocket events block chat value delivery:")
            for event in missing:
                print(f"   ❌ {event}")
            print(f"\n💡 These events are REQUIRED for substantive chat interactions!")
    
    return {
        'connection_test': connection_capture.get_event_summary() if connection_capture else None,
        'agent_test': agent_summary if agent_capture else None,
        'success_criteria': success_criteria,
        'overall_success': all_passed
    }


if __name__ == "__main__":
    asyncio.run(main())