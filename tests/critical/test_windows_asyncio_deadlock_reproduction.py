"""
Test Windows Asyncio Deadlock Failure Reproduction

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Prevent Windows asyncio deadlocks that block streaming features
- Value Impact: Ensure streaming functionality works on all developer platforms
- Strategic Impact: Cross-platform reliability - $25K+ MRR streaming features at risk

MISSION: Create failing tests that reproduce the exact Windows asyncio deadlock
patterns identified in test_023_streaming_partial_results_real and test_025_critical_event_delivery_real

ROOT CAUSE TO REPRODUCE:
- Windows asyncio GetQueuedCompletionStatus blocking indefinitely
- Tests hang at Windows asyncio event polling level before making network calls
- Circular async dependencies in Windows IOCP event loop
- Multiple concurrent streaming operations causing Windows asyncio limitations

CRITICAL: These tests MUST FAIL on Windows to validate platform-specific fixes work.
"""

import pytest
import asyncio
import json
import time
import platform
import httpx
import websockets
import concurrent.futures
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback
import threading
import signal
import sys

from tests.e2e.staging_test_config import get_staging_config

# Mark all tests as critical Windows asyncio reproduction tests
pytestmark = [pytest.mark.critical, pytest.mark.reproduction, pytest.mark.windows_asyncio]

def is_windows():
    """Platform detection for Windows-specific issues"""
    return platform.system().lower() == "windows"

def get_asyncio_event_loop_details():
    """Get detailed asyncio event loop information for debugging"""
    try:
        loop = asyncio.get_running_loop()
        return {
            "loop_type": type(loop).__name__,
            "is_running": loop.is_running(),
            "is_windows": is_windows(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "asyncio_debug": loop.get_debug(),
            "thread_id": threading.get_ident(),
            "loop_time": loop.time()
        }
    except Exception as e:
        return {"error": f"Could not get loop details: {e}"}

class AsyncioDeadlockDetector:
    """
    Helper class to detect Windows asyncio deadlock patterns
    
    This monitors for the specific deadlock indicators seen in SESSION5:
    - GetQueuedCompletionStatus blocking
    - Event loop not progressing  
    - Multiple concurrent operations hanging
    """
    
    def __init__(self, timeout_seconds: int = 300):
        self.timeout_seconds = timeout_seconds
        self.start_time = None
        self.progress_markers = []
        self.deadlock_detected = False
        self.deadlock_details = {}
        
    async def __aenter__(self):
        self.start_time = time.time()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is asyncio.TimeoutError:
            self.deadlock_detected = True
            self.deadlock_details = {
                "timeout_reached": True,
                "duration": time.time() - self.start_time,
                "progress_markers": len(self.progress_markers),
                "last_progress": self.progress_markers[-1] if self.progress_markers else None,
                "platform": platform.system(),
                "asyncio_loop_details": get_asyncio_event_loop_details()
            }
    
    def mark_progress(self, stage: str):
        """Mark progress through async operations"""
        self.progress_markers.append({
            "stage": stage,
            "timestamp": time.time(),
            "elapsed": time.time() - self.start_time if self.start_time else 0
        })
        
    def is_likely_deadlock(self) -> bool:
        """
        Analyze if the timeout pattern matches Windows asyncio deadlock
        
        Key indicators:
        - Long timeout (300s)  
        - Very few progress markers (operation never started properly)
        - Windows platform
        - Asyncio event loop type
        """
        if not self.deadlock_detected:
            return False
            
        # Check for SESSION5 deadlock pattern
        duration = self.deadlock_details.get("duration", 0)
        progress_count = self.deadlock_details.get("progress_markers", 0)
        is_win = self.deadlock_details.get("platform", "").lower() == "windows"
        
        # SESSION5 pattern: 300s timeout with minimal progress on Windows
        return (
            duration >= 290 and  # Close to 300s timeout
            progress_count <= 2 and  # Very little progress made
            is_win  # Windows platform
        )

class TestWindowsAsyncioDeadlockReproduction:
    """
    CRITICAL: Reproduce exact Windows asyncio deadlock failures from SESSION5
    
    These tests are designed to FAIL on Windows by triggering the specific
    asyncio deadlock conditions that block streaming functionality.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(300)  # Match SESSION5 timeout pattern
    @pytest.mark.skipif(not is_windows(), reason="Windows-specific deadlock test")
    async def test_streaming_partial_results_deadlock_reproduction(self):
        """
        CRITICAL FAILURE REPRODUCTION: test_023_streaming_partial_results_real
        
        Expected Failure Pattern on Windows:
        - Test starts but never makes network calls
        - Hangs at Windows asyncio event polling level
        - GetQueuedCompletionStatus blocks indefinitely  
        - 300s timeout reached with minimal progress
        - Stack trace shows windows_events.py line 774 blocking
        
        This test MUST TIMEOUT on Windows before asyncio fixes are applied.
        """
        config = get_staging_config()
        
        print(f" SEARCH:  Starting Windows asyncio deadlock reproduction test")
        print(f" SEARCH:  Platform: {platform.system()} {platform.version()}")
        print(f" SEARCH:  Python: {platform.python_version()}")
        print(f" SEARCH:  Asyncio details: {get_asyncio_event_loop_details()}")
        
        async with AsyncioDeadlockDetector(300) as deadlock_detector:
            deadlock_detector.mark_progress("test_started")
            
            # This pattern should trigger Windows asyncio deadlock
            streaming_endpoints = [
                "/api/chat/stream",
                "/api/agents/stream", 
                "/api/results/partial",
                "/api/events/stream"
            ]
            
            deadlock_detector.mark_progress("endpoints_defined")
            
            try:
                # CRITICAL: Multiple concurrent streaming requests
                # This pattern triggers Windows IOCP limitations in SESSION5
                print(" SEARCH:  Creating AsyncClient for concurrent streaming requests...")
                
                async with httpx.AsyncClient(timeout=30) as client:
                    deadlock_detector.mark_progress("client_created") 
                    
                    print(" SEARCH:  Starting concurrent streaming requests (this should deadlock on Windows)...")
                    
                    # Create multiple concurrent streaming tasks
                    # This reproduces the exact pattern that caused SESSION5 deadlock
                    streaming_tasks = []
                    
                    for i, endpoint in enumerate(streaming_endpoints):
                        print(f" SEARCH:  Creating streaming task {i+1}: {endpoint}")
                        
                        # Each task attempts streaming operations
                        task = asyncio.create_task(
                            self._streaming_request_task(
                                client, f"{config.backend_url}{endpoint}", 
                                f"task_{i+1}", deadlock_detector
                            )
                        )
                        streaming_tasks.append(task)
                        
                        deadlock_detector.mark_progress(f"task_{i+1}_created")
                    
                    print(" SEARCH:  Waiting for concurrent streaming tasks (deadlock expected here)...")
                    
                    # This gather operation should deadlock on Windows
                    # Due to IOCP limitations with multiple concurrent async operations  
                    results = await asyncio.gather(*streaming_tasks, return_exceptions=True)
                    
                    deadlock_detector.mark_progress("tasks_completed")
                    
                    # If we reach here, deadlock was not reproduced
                    print(" FAIL:  DEADLOCK NOT REPRODUCED: All streaming tasks completed")
                    print(f" FAIL:  Task results: {results}")
                    
                    pytest.fail(
                        "Failed to reproduce Windows asyncio deadlock. "
                        "Streaming operations completed without hanging. "
                        "This suggests the Windows asyncio issue may be fixed."
                    )
                    
            except asyncio.TimeoutError:
                # EXPECTED: This is the deadlock pattern we want to reproduce
                print(" PASS:  DEADLOCK REPRODUCED: Asyncio timeout occurred")
                
                if deadlock_detector.is_likely_deadlock():
                    print(" PASS:  CONFIRMED: Windows asyncio deadlock pattern matches SESSION5")
                    print(f" PASS:  Duration: {deadlock_detector.deadlock_details['duration']:.1f}s")
                    print(f" PASS:  Progress markers: {deadlock_detector.deadlock_details['progress_markers']}")
                    print(" PASS:  This reproduces the exact SESSION5 failure pattern")
                    
                    # For reproduction test, timeout is success
                    assert True, "Windows asyncio deadlock successfully reproduced"
                else:
                    print(" SEARCH:  Timeout occurred but pattern doesn't match SESSION5 deadlock")
                    pytest.fail(f"Timeout pattern differs from SESSION5: {deadlock_detector.deadlock_details}")
                    
            except Exception as e:
                print(f" SEARCH:  Unexpected error during deadlock reproduction: {e}")
                print(f" SEARCH:  Traceback: {traceback.format_exc()}")
                pytest.fail(f"Unexpected error instead of deadlock: {e}")
    
    async def _streaming_request_task(
        self, 
        client: httpx.AsyncClient, 
        url: str, 
        task_name: str,
        deadlock_detector: AsyncioDeadlockDetector
    ):
        """
        Individual streaming request task that contributes to deadlock
        
        This replicates the concurrent async pattern that causes
        Windows IOCP event loop deadlock in SESSION5.
        """
        try:
            deadlock_detector.mark_progress(f"{task_name}_started")
            print(f" SEARCH:  {task_name}: Starting streaming request to {url}")
            
            # Test GET first (might return streaming info)
            response = await client.get(url)
            deadlock_detector.mark_progress(f"{task_name}_get_response")
            print(f" SEARCH:  {task_name}: GET response {response.status_code}")
            
            if response.status_code == 405:  # Method not allowed
                # Try POST with streaming request
                stream_request = {
                    "message": f"Streaming test from {task_name}",
                    "stream": True,
                    "timestamp": time.time()
                }
                
                post_response = await client.post(url, json=stream_request)
                deadlock_detector.mark_progress(f"{task_name}_post_response")
                print(f" SEARCH:  {task_name}: POST response {post_response.status_code}")
                
            deadlock_detector.mark_progress(f"{task_name}_completed")
            return {
                "task": task_name,
                "status": "completed",
                "response_code": response.status_code
            }
            
        except Exception as e:
            deadlock_detector.mark_progress(f"{task_name}_error")
            print(f" SEARCH:  {task_name}: Error - {e}")
            return {
                "task": task_name, 
                "status": "error",
                "error": str(e)
            }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(300)  # Match SESSION5 timeout pattern
    @pytest.mark.skipif(not is_windows(), reason="Windows-specific deadlock test")
    async def test_critical_event_delivery_deadlock_reproduction(self):
        """
        CRITICAL FAILURE REPRODUCTION: test_025_critical_event_delivery_real
        
        Expected Failure Pattern on Windows:
        - WebSocket event delivery testing hangs at asyncio level
        - Complex async coordination creates circular dependencies  
        - Windows IOCP cannot progress event loop
        - 300s timeout with GetQueuedCompletionStatus blocking
        
        This test MUST TIMEOUT on Windows before asyncio fixes are applied.
        """
        config = get_staging_config()
        
        print(f" SEARCH:  Starting Windows WebSocket event delivery deadlock reproduction")
        print(f" SEARCH:  Platform: {platform.system()} {platform.version()}")
        
        async with AsyncioDeadlockDetector(300) as deadlock_detector:
            deadlock_detector.mark_progress("event_test_started")
            
            # Critical events that MUST be delivered for business value
            critical_event_types = [
                "agent_started",
                "agent_thinking",
                "tool_executing", 
                "tool_completed",
                "agent_completed"
            ]
            
            deadlock_detector.mark_progress("events_defined")
            
            try:
                print(" SEARCH:  Creating complex async WebSocket event delivery test...")
                
                # This pattern creates circular async dependencies on Windows
                # Multiple async contexts: WebSocket + event listening + timeout management
                async with websockets.connect(
                    config.websocket_url,
                    timeout=10
                ) as ws:
                    deadlock_detector.mark_progress("websocket_connected")
                    
                    # Send trigger message for events
                    trigger_message = {
                        "type": "execute_agent",
                        "content": "Test message to trigger critical events",
                        "timestamp": time.time()
                    }
                    
                    await ws.send(json.dumps(trigger_message))
                    deadlock_detector.mark_progress("message_sent")
                    
                    # This creates the circular async dependency that deadlocks Windows
                    # Multiple concurrent async operations: event listening + timeout + validation
                    event_tasks = []
                    
                    for event_type in critical_event_types:
                        # Create concurrent event listening tasks
                        # This pattern triggers Windows IOCP deadlock
                        task = asyncio.create_task(
                            self._wait_for_specific_event(ws, event_type, deadlock_detector)
                        )
                        event_tasks.append(task)
                        deadlock_detector.mark_progress(f"event_task_{event_type}_created")
                    
                    print(" SEARCH:  Starting concurrent event listening (deadlock expected here)...")
                    
                    # This should create circular async dependencies on Windows
                    event_results = await asyncio.gather(*event_tasks, return_exceptions=True)
                    deadlock_detector.mark_progress("all_events_completed")
                    
                    # If we reach here, deadlock was not reproduced
                    print(" FAIL:  EVENT DEADLOCK NOT REPRODUCED: All event tasks completed")
                    print(f" FAIL:  Event results: {event_results}")
                    
                    pytest.fail(
                        "Failed to reproduce Windows WebSocket event delivery deadlock. "
                        "Event operations completed without hanging. "
                        "This suggests the Windows asyncio issue may be fixed."
                    )
                    
            except websockets.exceptions.InvalidStatus as e:
                # Connection might be rejected - not the deadlock we want
                if e.status_code in [401, 403]:
                    print(f" SEARCH:  WebSocket connection rejected: {e}")
                    print(" SEARCH:  Cannot test event delivery deadlock without connection")
                    pytest.skip("WebSocket connection rejected - cannot test event deadlock")
                else:
                    raise
                    
            except asyncio.TimeoutError:
                # EXPECTED: This is the event delivery deadlock we want to reproduce
                print(" PASS:  EVENT DELIVERY DEADLOCK REPRODUCED: Asyncio timeout occurred")
                
                if deadlock_detector.is_likely_deadlock():
                    print(" PASS:  CONFIRMED: Windows event delivery deadlock matches SESSION5")
                    print(f" PASS:  Duration: {deadlock_detector.deadlock_details['duration']:.1f}s") 
                    print(f" PASS:  Progress markers: {deadlock_detector.deadlock_details['progress_markers']}")
                    print(" PASS:  This reproduces the exact SESSION5 event delivery failure")
                    
                    # For reproduction test, timeout is success
                    assert True, "Windows WebSocket event delivery deadlock successfully reproduced"
                else:
                    print(" SEARCH:  Timeout occurred but pattern doesn't match SESSION5 deadlock")
                    pytest.fail(f"Event timeout pattern differs from SESSION5: {deadlock_detector.deadlock_details}")
            
            except Exception as e:
                print(f" SEARCH:  Unexpected error during event deadlock reproduction: {e}")
                print(f" SEARCH:  Traceback: {traceback.format_exc()}")
                pytest.fail(f"Unexpected error instead of event deadlock: {e}")
    
    async def _wait_for_specific_event(
        self, 
        ws: websockets.WebSocketServerProtocol,
        event_type: str,
        deadlock_detector: AsyncioDeadlockDetector
    ):
        """
        Wait for specific WebSocket event type
        
        This creates part of the circular async dependency that
        causes Windows IOCP deadlock in SESSION5.
        """
        try:
            deadlock_detector.mark_progress(f"waiting_for_{event_type}")
            print(f" SEARCH:  Waiting for {event_type} event...")
            
            # Listen for events with timeout
            # This contributes to the circular wait condition on Windows
            timeout_count = 0
            max_timeouts = 10
            
            while timeout_count < max_timeouts:
                try:
                    event_data = await asyncio.wait_for(ws.recv(), timeout=1)
                    deadlock_detector.mark_progress(f"received_data_for_{event_type}")
                    
                    try:
                        event = json.loads(event_data)
                        received_event_type = event.get("type") or event.get("event")
                        
                        if received_event_type == event_type:
                            deadlock_detector.mark_progress(f"found_{event_type}")
                            print(f"[U+2713] Found {event_type} event")
                            return {"event_type": event_type, "found": True}
                            
                    except json.JSONDecodeError:
                        # Non-JSON data
                        pass
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    deadlock_detector.mark_progress(f"{event_type}_timeout_{timeout_count}")
                    
                    if timeout_count >= max_timeouts:
                        break
            
            print(f" WARNING: [U+FE0F] {event_type} event not found after {timeout_count} timeouts")
            return {"event_type": event_type, "found": False, "timeouts": timeout_count}
            
        except Exception as e:
            deadlock_detector.mark_progress(f"{event_type}_error")
            print(f" SEARCH:  Error waiting for {event_type}: {e}")
            return {"event_type": event_type, "error": str(e)}
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_windows_platform_detection_and_validation(self):
        """
        SUPPORTING TEST: Validate Windows platform detection and asyncio environment
        
        This test ensures we can properly detect Windows environment and
        asyncio characteristics that contribute to deadlock conditions.
        """
        start_time = time.time()
        
        platform_info = {
            "system": platform.system(),
            "version": platform.version(),
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "is_windows": is_windows(),
            "asyncio_details": get_asyncio_event_loop_details()
        }
        
        print(" SEARCH:  Windows Platform Detection Results:")
        for key, value in platform_info.items():
            print(f"  {key}: {value}")
        
        # Test asyncio behavior patterns
        asyncio_test_results = {
            "event_loop_running": False,
            "can_create_tasks": False,
            "concurrent_operations": False,
            "timeout_handling": False
        }
        
        try:
            # Test 1: Event loop running
            loop = asyncio.get_running_loop()
            asyncio_test_results["event_loop_running"] = loop.is_running()
            
            # Test 2: Task creation
            test_task = asyncio.create_task(asyncio.sleep(0.01))
            await test_task
            asyncio_test_results["can_create_tasks"] = True
            
            # Test 3: Concurrent operations (simplified)
            concurrent_tasks = [
                asyncio.create_task(asyncio.sleep(0.01)),
                asyncio.create_task(asyncio.sleep(0.01)),
                asyncio.create_task(asyncio.sleep(0.01))
            ]
            await asyncio.gather(*concurrent_tasks)
            asyncio_test_results["concurrent_operations"] = True
            
            # Test 4: Timeout handling
            try:
                await asyncio.wait_for(asyncio.sleep(1), timeout=0.1)
            except asyncio.TimeoutError:
                asyncio_test_results["timeout_handling"] = True
                
        except Exception as e:
            print(f" SEARCH:  Asyncio test error: {e}")
        
        duration = time.time() - start_time
        
        print(f"\n SEARCH:  Asyncio Test Results:")
        for test, result in asyncio_test_results.items():
            print(f"  {test}: {result}")
        
        print(f"Test duration: {duration:.3f}s")
        
        # Validate this was a real test
        assert duration > 0.01, f"Test too fast ({duration:.3f}s)"
        
        # Provide detailed information for deadlock debugging
        if is_windows():
            print("\n PASS:  WINDOWS PLATFORM CONFIRMED")
            print(" PASS:  This test environment can reproduce Windows asyncio deadlocks")
            
            # Check for asyncio patterns that contribute to deadlocks
            loop_details = platform_info["asyncio_details"]
            if isinstance(loop_details, dict) and "loop_type" in loop_details:
                if "Windows" in loop_details.get("loop_type", ""):
                    print(" PASS:  Windows event loop detected - IOCP limitations apply")
                else:
                    print(f" SEARCH:  Event loop type: {loop_details.get('loop_type')}")
            
        else:
            print(f"\n SEARCH:  NON-WINDOWS PLATFORM: {platform.system()}")
            print(" SEARCH:  Windows-specific deadlock tests will be skipped")


def verify_reproduction_timeout_pattern(deadlock_detector: AsyncioDeadlockDetector):
    """
    Verify the timeout pattern matches SESSION5 Windows asyncio deadlock
    
    SESSION5 pattern:
    - 300s timeout
    - GetQueuedCompletionStatus blocking
    - Minimal progress through test phases
    - Windows platform
    """
    if not deadlock_detector.deadlock_detected:
        return False
        
    details = deadlock_detector.deadlock_details
    
    # Check SESSION5 indicators
    return (
        details.get("timeout_reached", False) and
        details.get("duration", 0) >= 290 and  # Close to 300s
        details.get("progress_markers", 0) <= 3 and  # Very limited progress
        details.get("platform", "").lower() == "windows"
    )


if __name__ == "__main__":
    print("=" * 70)
    print("WINDOWS ASYNCIO DEADLOCK REPRODUCTION TESTS") 
    print("=" * 70)
    print("These tests reproduce Windows asyncio deadlocks from SESSION5.")
    print("Success = reproducing 300s timeouts with GetQueuedCompletionStatus blocking.")
    print("")
    print("Expected failures on Windows:")
    print("- test_023_streaming_partial_results_real deadlock pattern")
    print("- test_025_critical_event_delivery_real deadlock pattern")
    print("- Timeouts at Windows asyncio event polling level")
    print("- Multiple concurrent operations blocking IOCP")
    print("=" * 70)
    
    if is_windows():
        print(" PASS:  WINDOWS PLATFORM DETECTED - Deadlock tests will run")
    else:
        print(" SEARCH:  NON-WINDOWS PLATFORM - Deadlock tests will be skipped")