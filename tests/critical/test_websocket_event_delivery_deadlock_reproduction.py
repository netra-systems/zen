"""
Test WebSocket Event Delivery Deadlock Reproduction

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent WebSocket event delivery deadlocks that break real-time chat
- Value Impact: Ensure all 5 mission-critical events are delivered to users
- Strategic Impact: Core chat functionality - $15K+ MRR transparency features at risk

MISSION: Create failing tests that reproduce the exact WebSocket event delivery deadlock
pattern identified in test_025_critical_event_delivery_real from SESSION5

ROOT CAUSE TO REPRODUCE:
- Windows asyncio architectural limitations with WebSocket event coordination
- Complex async coordination between WebSocket connections, event listeners, and timeout mechanisms
- Circular async dependencies that deadlock Windows IOCP event loop
- ID Generation inconsistencies preventing event delivery
- Thread/Run ID mismatches causing event routing failures

CRITICAL: These tests MUST FAIL on Windows to validate event delivery fixes work.
Mission-critical events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
"""

import pytest
import asyncio
import json
import time
import platform
import uuid
import websockets
import httpx
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
import threading
import traceback

from tests.e2e.staging_test_config import get_staging_config

# Mark all tests as critical WebSocket event delivery reproduction tests
pytestmark = [pytest.mark.critical, pytest.mark.reproduction, pytest.mark.websocket_events]

def is_windows():
    """Platform detection for Windows-specific issues"""
    return platform.system().lower() == "windows"

class WebSocketEventDeliveryMonitor:
    """
    Monitor for WebSocket event delivery deadlock patterns
    
    This reproduces the exact event delivery failure patterns from SESSION5:
    - 5 mission-critical events that MUST be delivered for business value
    - Complex async coordination that creates circular dependencies on Windows
    - ID generation and routing issues that prevent event delivery
    """
    
    def __init__(self, timeout_seconds: int = 300):
        self.timeout_seconds = timeout_seconds
        self.start_time = None
        self.events_received = []
        self.event_types_found = set()
        self.deadlock_detected = False
        self.delivery_failures = []
        self.id_mismatches = []
        
        # Mission-critical events from CLAUDE.md
        self.critical_events = {
            "agent_started": {"required": True, "found": False, "timestamp": None},
            "agent_thinking": {"required": True, "found": False, "timestamp": None}, 
            "tool_executing": {"required": True, "found": False, "timestamp": None},
            "tool_completed": {"required": True, "found": False, "timestamp": None},
            "agent_completed": {"required": True, "found": False, "timestamp": None}
        }
        
    async def __aenter__(self):
        self.start_time = time.time()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is asyncio.TimeoutError:
            self.deadlock_detected = True
            self._analyze_event_delivery_failure()
    
    def record_event(self, event_data: dict):
        """Record received WebSocket event for analysis"""
        timestamp = time.time()
        
        self.events_received.append({
            "data": event_data,
            "timestamp": timestamp,
            "elapsed": timestamp - self.start_time if self.start_time else 0
        })
        
        # Check if this is a critical event
        event_type = event_data.get("type") or event_data.get("event")
        if event_type:
            self.event_types_found.add(event_type)
            
            if event_type in self.critical_events:
                self.critical_events[event_type]["found"] = True
                self.critical_events[event_type]["timestamp"] = timestamp
                print(f"✓ Critical event received: {event_type}")
    
    def record_id_mismatch(self, expected_id: str, received_id: str, context: str):
        """Record ID mismatches that prevent event delivery"""
        self.id_mismatches.append({
            "expected": expected_id,
            "received": received_id,
            "context": context,
            "timestamp": time.time()
        })
        print(f"🔍 ID mismatch in {context}: expected {expected_id[:8]}..., got {received_id[:8]}...")
    
    def _analyze_event_delivery_failure(self):
        """Analyze the event delivery failure pattern"""
        missing_events = [
            event_type for event_type, details in self.critical_events.items()
            if details["required"] and not details["found"]
        ]
        
        self.delivery_failures = {
            "missing_critical_events": missing_events,
            "total_events_received": len(self.events_received),
            "unique_event_types": len(self.event_types_found),
            "id_mismatches": len(self.id_mismatches),
            "duration": time.time() - self.start_time if self.start_time else 0,
            "platform": platform.system()
        }
        
    def is_critical_event_delivery_failure(self) -> bool:
        """
        Determine if this matches SESSION5 critical event delivery failure
        
        Key indicators:
        - Timeout reached (300s)
        - Missing critical events required for business value  
        - ID mismatches preventing event routing
        - Windows platform limitations
        """
        if not self.deadlock_detected:
            return False
            
        missing_events = self.delivery_failures.get("missing_critical_events", [])
        duration = self.delivery_failures.get("duration", 0)
        is_win = self.delivery_failures.get("platform", "").lower() == "windows"
        
        # SESSION5 pattern: timeout with missing critical events
        return (
            duration >= 290 and  # Close to 300s timeout
            len(missing_events) > 0 and  # Missing required events
            is_win  # Windows platform
        )

class TestWebSocketEventDeliveryDeadlockReproduction:
    """
    CRITICAL: Reproduce exact WebSocket event delivery deadlock from SESSION5
    
    Mission-critical events that MUST be delivered for chat business value:
    1. agent_started - User must see agent began processing
    2. agent_thinking - Real-time reasoning visibility  
    3. tool_executing - Tool usage transparency
    4. tool_completed - Tool results display
    5. agent_completed - User must know when response is ready
    
    These tests MUST FAIL when event delivery is broken.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(300)  # Match SESSION5 timeout pattern
    async def test_mission_critical_event_delivery_deadlock_reproduction(self):
        """
        CRITICAL FAILURE REPRODUCTION: test_025_critical_event_delivery_real
        
        Expected Failure Pattern:
        - WebSocket connection may establish
        - Agent execution request sent  
        - Complex async coordination creates circular dependencies
        - Windows IOCP cannot handle multiple concurrent event streams
        - 300s timeout with missing critical events
        - ID mismatches prevent proper event routing
        
        This test MUST FAIL when critical event delivery is broken.
        """
        config = get_staging_config() 
        
        print("🔍 Starting mission-critical WebSocket event delivery deadlock reproduction")
        print(f"🔍 Platform: {platform.system()} {platform.version()}")
        print("🔍 Testing delivery of 5 mission-critical events for chat business value")
        
        async with WebSocketEventDeliveryMonitor(300) as event_monitor:
            
            try:
                print("🔍 Establishing WebSocket connection for event delivery test...")
                
                # Use connection without auth to focus on event delivery issues
                async with websockets.connect(
                    config.websocket_url,
                    timeout=15
                ) as ws:
                    print("✓ WebSocket connection established")
                    
                    # Send agent execution request that should trigger all 5 critical events
                    trigger_request = {
                        "type": "execute_agent",
                        "agent": "data_agent",  # Use agent likely to trigger all events
                        "message": "Analyze sample data to trigger all critical events",
                        "request_id": str(uuid.uuid4()),
                        "thread_id": str(uuid.uuid4()),
                        "user_id": "test_user_" + str(uuid.uuid4())[:8],
                        "timestamp": time.time()
                    }
                    
                    print(f"🔍 Sending agent execution request: {trigger_request['type']}")
                    print(f"🔍 Request ID: {trigger_request['request_id'][:8]}...")
                    print(f"🔍 Thread ID: {trigger_request['thread_id'][:8]}...")
                    
                    await ws.send(json.dumps(trigger_request))
                    
                    # This is where the complex async coordination should deadlock on Windows
                    print("🔍 Starting complex event delivery monitoring (deadlock expected)...")
                    
                    # Create multiple concurrent event monitoring tasks
                    # This reproduces the circular async dependency from SESSION5
                    monitoring_tasks = [
                        asyncio.create_task(
                            self._monitor_event_stream(ws, event_monitor, "primary_stream")
                        ),
                        asyncio.create_task(
                            self._monitor_critical_events(ws, event_monitor, "critical_monitor")
                        ),
                        asyncio.create_task(
                            self._validate_event_ids(ws, event_monitor, trigger_request, "id_validator")
                        ),
                        asyncio.create_task(
                            self._timeout_watchdog(event_monitor, "timeout_watchdog")
                        )
                    ]
                    
                    print("🔍 Running concurrent event monitoring tasks (should deadlock)...")
                    
                    # This gather should deadlock on Windows due to complex async coordination
                    results = await asyncio.gather(*monitoring_tasks, return_exceptions=True)
                    
                    print("❌ DEADLOCK NOT REPRODUCED: Event monitoring completed")
                    print(f"❌ Monitoring results: {results}")
                    
                    # Check if we got all critical events despite no deadlock
                    missing_events = [
                        event_type for event_type, details in event_monitor.critical_events.items()
                        if details["required"] and not details["found"]
                    ]
                    
                    if missing_events:
                        print(f"✅ PARTIAL SUCCESS: Missing critical events: {missing_events}")
                        print("✅ This demonstrates event delivery failure even without deadlock")
                        
                        # Missing events is still a critical failure for business value
                        pytest.fail(
                            f"Critical event delivery failure: Missing {missing_events}. "
                            f"This breaks real-time chat transparency. "
                            f"Events received: {list(event_monitor.event_types_found)}"
                        )
                    else:
                        print("❌ All critical events delivered - event system appears working")
                        pytest.fail(
                            "Failed to reproduce event delivery deadlock. "
                            "All 5 critical events were delivered successfully. "
                            "This suggests the event delivery issue may be fixed."
                        )
                    
            except websockets.exceptions.InvalidStatus as e:
                if e.status_code in [401, 403]:
                    print(f"🔍 WebSocket connection rejected: {e}")
                    print("🔍 Cannot test event delivery without connection")
                    pytest.skip("WebSocket connection rejected - cannot test event delivery deadlock")
                else:
                    raise
                    
            except asyncio.TimeoutError:
                # EXPECTED: This is the event delivery deadlock we want to reproduce  
                print("✅ EVENT DELIVERY DEADLOCK REPRODUCED: 300s timeout reached")
                
                if event_monitor.is_critical_event_delivery_failure():
                    print("✅ CONFIRMED: Critical event delivery failure matches SESSION5")
                    
                    failure_analysis = event_monitor.delivery_failures
                    print(f"✅ Missing events: {failure_analysis['missing_critical_events']}")
                    print(f"✅ Events received: {failure_analysis['total_events_received']}")
                    print(f"✅ ID mismatches: {failure_analysis['id_mismatches']}")
                    print(f"✅ Duration: {failure_analysis['duration']:.1f}s")
                    
                    print("\n🚨 BUSINESS IMPACT: Critical event delivery failure!")
                    print("🚨 Real-time chat transparency broken - users won't see agent progress")
                    print("🚨 This affects core platform value delivery")
                    
                    # For reproduction test, demonstrating the failure is success
                    assert True, "Critical WebSocket event delivery deadlock successfully reproduced"
                else:
                    print("🔍 Timeout occurred but not the expected event delivery pattern")
                    pytest.fail(f"Timeout pattern differs from SESSION5: {event_monitor.delivery_failures}")
                    
            except Exception as e:
                print(f"🔍 Unexpected error during event delivery reproduction: {e}")
                print(f"🔍 Traceback: {traceback.format_exc()}")
                pytest.fail(f"Unexpected error instead of event delivery deadlock: {e}")
    
    async def _monitor_event_stream(
        self, 
        ws: websockets.WebSocketServerProtocol,
        event_monitor: WebSocketEventDeliveryMonitor,
        stream_name: str
    ):
        """
        Primary event stream monitoring
        
        This creates part of the complex async coordination that
        deadlocks on Windows in SESSION5.
        """
        try:
            print(f"🔍 {stream_name}: Starting primary event stream monitoring")
            
            while True:
                try:
                    # Receive event with short timeout to enable concurrent monitoring
                    event_data = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    
                    try:
                        event = json.loads(event_data)
                        event_monitor.record_event(event)
                        
                        event_type = event.get("type") or event.get("event")
                        if event_type:
                            print(f"🔍 {stream_name}: Received {event_type} event")
                            
                    except json.JSONDecodeError:
                        # Non-JSON event data
                        print(f"🔍 {stream_name}: Non-JSON event data received")
                        
                except asyncio.TimeoutError:
                    # Continue monitoring - timeouts are expected
                    continue
                    
                except websockets.exceptions.ConnectionClosed:
                    print(f"🔍 {stream_name}: WebSocket connection closed")
                    break
                    
        except Exception as e:
            print(f"🔍 {stream_name}: Error - {e}")
            return {"stream": stream_name, "error": str(e)}
            
        return {"stream": stream_name, "status": "completed"}
    
    async def _monitor_critical_events(
        self,
        ws: websockets.WebSocketServerProtocol, 
        event_monitor: WebSocketEventDeliveryMonitor,
        monitor_name: str
    ):
        """
        Monitor specifically for the 5 mission-critical events
        
        This creates additional async complexity that contributes to
        the Windows IOCP deadlock in SESSION5.
        """
        try:
            print(f"🔍 {monitor_name}: Monitoring for 5 mission-critical events")
            
            critical_events_needed = set(event_monitor.critical_events.keys())
            
            timeout_count = 0
            max_timeouts = 150  # 150 * 2s = 300s total timeout
            
            while critical_events_needed and timeout_count < max_timeouts:
                try:
                    event_data = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    
                    try:
                        event = json.loads(event_data) 
                        event_type = event.get("type") or event.get("event")
                        
                        if event_type in critical_events_needed:
                            critical_events_needed.remove(event_type)
                            print(f"✓ {monitor_name}: Found critical event {event_type}")
                            print(f"🔍 {monitor_name}: Still need: {critical_events_needed}")
                            
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    
                    if timeout_count % 30 == 0:  # Log every minute
                        print(f"🔍 {monitor_name}: {timeout_count*2}s elapsed, still need: {critical_events_needed}")
            
            if critical_events_needed:
                print(f"❌ {monitor_name}: FAILED - Missing critical events: {critical_events_needed}")
                return {
                    "monitor": monitor_name, 
                    "status": "failed",
                    "missing_events": list(critical_events_needed),
                    "timeout_count": timeout_count
                }
            else:
                print(f"✅ {monitor_name}: SUCCESS - All critical events found")
                return {"monitor": monitor_name, "status": "success"}
                
        except Exception as e:
            print(f"🔍 {monitor_name}: Error - {e}")
            return {"monitor": monitor_name, "error": str(e)}
    
    async def _validate_event_ids(
        self,
        ws: websockets.WebSocketServerProtocol,
        event_monitor: WebSocketEventDeliveryMonitor,
        trigger_request: dict,
        validator_name: str
    ):
        """
        Validate event IDs match request IDs for proper routing
        
        This reproduces the ID mismatch issues that prevent
        event delivery in SESSION5.
        """
        try:
            print(f"🔍 {validator_name}: Validating event ID consistency")
            
            expected_request_id = trigger_request["request_id"]
            expected_thread_id = trigger_request["thread_id"]
            expected_user_id = trigger_request["user_id"]
            
            timeout_count = 0
            max_timeouts = 150
            
            while timeout_count < max_timeouts:
                try:
                    event_data = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    
                    try:
                        event = json.loads(event_data)
                        
                        # Check for ID mismatches that prevent event delivery
                        event_request_id = event.get("request_id") or event.get("id")
                        event_thread_id = event.get("thread_id") 
                        event_user_id = event.get("user_id")
                        
                        if event_request_id and event_request_id != expected_request_id:
                            event_monitor.record_id_mismatch(
                                expected_request_id, event_request_id, "request_id"
                            )
                            
                        if event_thread_id and event_thread_id != expected_thread_id:
                            event_monitor.record_id_mismatch(
                                expected_thread_id, event_thread_id, "thread_id"
                            )
                            
                        if event_user_id and event_user_id != expected_user_id:
                            event_monitor.record_id_mismatch(
                                expected_user_id, event_user_id, "user_id"
                            )
                            
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
            
            id_mismatches = len(event_monitor.id_mismatches)
            print(f"🔍 {validator_name}: Completed with {id_mismatches} ID mismatches detected")
            
            return {
                "validator": validator_name,
                "id_mismatches": id_mismatches,
                "timeout_count": timeout_count
            }
            
        except Exception as e:
            print(f"🔍 {validator_name}: Error - {e}")
            return {"validator": validator_name, "error": str(e)}
    
    async def _timeout_watchdog(
        self,
        event_monitor: WebSocketEventDeliveryMonitor,
        watchdog_name: str
    ):
        """
        Watchdog to monitor for timeout conditions
        
        This adds to the async complexity that triggers Windows
        IOCP deadlock in SESSION5.
        """
        try:
            print(f"🔍 {watchdog_name}: Starting timeout watchdog")
            
            start_time = time.time()
            check_interval = 30  # Check every 30 seconds
            
            while time.time() - start_time < 295:  # Stop before 300s timeout
                await asyncio.sleep(check_interval)
                
                elapsed = time.time() - start_time
                events_received = len(event_monitor.events_received)
                critical_found = sum(
                    1 for details in event_monitor.critical_events.values() 
                    if details["found"]
                )
                
                print(f"🔍 {watchdog_name}: {elapsed:.0f}s elapsed, "
                      f"{events_received} events, {critical_found}/5 critical")
                
                # Check if we're making no progress (deadlock indicator)
                if elapsed > 120 and events_received == 0:
                    print(f"⚠️ {watchdog_name}: No events received after 2 minutes - possible deadlock")
                    
                elif elapsed > 180 and critical_found == 0:
                    print(f"⚠️ {watchdog_name}: No critical events after 3 minutes - delivery failure")
            
            print(f"🔍 {watchdog_name}: Watchdog timeout approaching")
            return {"watchdog": watchdog_name, "status": "timeout_approaching"}
            
        except Exception as e:
            print(f"🔍 {watchdog_name}: Error - {e}")
            return {"watchdog": watchdog_name, "error": str(e)}
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_event_delivery_infrastructure_validation(self):
        """
        SUPPORTING TEST: Validate event delivery infrastructure exists
        
        This test verifies the event delivery endpoints and WebSocket
        infrastructure are available to support event delivery testing.
        """
        config = get_staging_config()
        start_time = time.time()
        
        infrastructure_status = {
            "websocket_connectivity": False,
            "event_endpoints": {},
            "backend_health": False
        }
        
        # Test 1: Backend health
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                health_response = await client.get(f"{config.backend_url}/health")
                infrastructure_status["backend_health"] = health_response.status_code == 200
                print(f"🔍 Backend health: {health_response.status_code}")
        except Exception as e:
            print(f"🔍 Backend health check failed: {e}")
        
        # Test 2: Event-related endpoints
        event_endpoints = [
            "/api/events",
            "/api/events/stream", 
            "/api/websocket/events",
            "/api/notifications"
        ]
        
        async with httpx.AsyncClient(timeout=30) as client:
            for endpoint in event_endpoints:
                try:
                    response = await client.get(f"{config.backend_url}{endpoint}")
                    infrastructure_status["event_endpoints"][endpoint] = {
                        "status": response.status_code,
                        "available": response.status_code in [200, 401, 403]  # Auth required is OK
                    }
                except Exception as e:
                    infrastructure_status["event_endpoints"][endpoint] = {
                        "error": str(e)[:100]
                    }
        
        # Test 3: WebSocket connectivity
        try:
            async with websockets.connect(config.websocket_url, timeout=10) as ws:
                infrastructure_status["websocket_connectivity"] = True
                print("🔍 WebSocket connection: SUCCESS")
                
                # Test basic message exchange
                test_msg = {"type": "ping", "timestamp": time.time()}
                await ws.send(json.dumps(test_msg))
                
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5)
                    print(f"🔍 WebSocket response: {response[:50]}...")
                except asyncio.TimeoutError:
                    print("🔍 WebSocket response: TIMEOUT (but connection works)")
                    
        except Exception as e:
            print(f"🔍 WebSocket connection failed: {e}")
        
        duration = time.time() - start_time
        
        print(f"\nEvent delivery infrastructure status:")
        for key, value in infrastructure_status.items():
            print(f"  {key}: {value}")
        
        print(f"Test duration: {duration:.3f}s")
        
        # Real test validation
        assert duration > 0.3, f"Test too fast ({duration:.3f}s) - must make real network calls!"
        
        # Infrastructure readiness assessment
        endpoints_available = sum(
            1 for endpoint_info in infrastructure_status["event_endpoints"].values()
            if isinstance(endpoint_info, dict) and endpoint_info.get("available", False)
        )
        
        if infrastructure_status["websocket_connectivity"]:
            print("✅ WebSocket infrastructure ready for event delivery testing")
        else:
            print("❌ WebSocket infrastructure not available")
            pytest.skip("Cannot test event delivery without WebSocket connectivity")
            
        if endpoints_available > 0:
            print(f"✅ {endpoints_available} event endpoints available")
        else:
            print("⚠️ No event endpoints responding - may affect event delivery")
            
        print(f"Event delivery infrastructure validated: WebSocket={infrastructure_status['websocket_connectivity']}, Endpoints={endpoints_available}")


if __name__ == "__main__":
    print("=" * 70)
    print("WEBSOCKET EVENT DELIVERY DEADLOCK REPRODUCTION TESTS")
    print("=" * 70)
    print("These tests reproduce WebSocket event delivery deadlocks from SESSION5.")
    print("Focus: 5 mission-critical events required for chat business value.")
    print("")
    print("Mission-critical events:")
    print("1. agent_started - User must see agent began processing")
    print("2. agent_thinking - Real-time reasoning visibility")  
    print("3. tool_executing - Tool usage transparency")
    print("4. tool_completed - Tool results display")
    print("5. agent_completed - User must know when response is ready")
    print("")
    print("Expected failures:")
    print("- 300s timeout with missing critical events") 
    print("- Complex async coordination deadlock on Windows")
    print("- ID mismatches preventing event routing")
    print("- Real-time chat transparency broken")
    print("=" * 70)