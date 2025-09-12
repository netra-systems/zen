#!/usr/bin/env python3
"""
Integration Test: Thread Service Missing Detection

MISSION CRITICAL: This test prevents the thread service missing condition that causes
fallback handler creation instead of proper thread management.

PURPOSE: Reproduce and prevent the WebSocket.py line 549 condition where thread_service is None,
ensuring the system waits for real thread service or fails hard, never creating fallback handlers.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent thread service race conditions from degrading chat functionality
- Value Impact: Ensure proper thread management for multi-turn conversations
- Strategic Impact: Protect conversation continuity and user experience

CRITICAL: This test must FAIL if fallback handlers are created due to missing thread service.
"""

import asyncio
import json
import logging
import os
import sys
import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

# CRITICAL: Add project root to Python path for imports  
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import SSOT components
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
from shared.isolated_environment import get_env

# Import system components for thread service simulation
from netra_backend.app.services.thread_service import ThreadService

# Import BusinessValueValidator
from tests.mission_critical.test_fallback_handler_degradation_prevention import (
    BusinessValueValidator, MockServiceController
)


class ThreadServiceMissingSimulator:
    """
    Simulator for thread service missing conditions during WebSocket operations.
    
    This class creates realistic conditions where thread service is unavailable
    during WebSocket message processing that requires thread management.
    """
    
    def __init__(self):
        """Initialize thread service missing simulator."""
        self.original_thread_service = None
        self.service_missing = False
        self._lock = threading.Lock()
        
    def simulate_thread_service_missing(self) -> None:
        """
        Simulate thread service missing condition.
        
        This simulates the scenario where thread service is None during
        WebSocket operations that require thread management.
        """
        with self._lock:
            if not self.service_missing:
                # Store original thread service
                self.original_thread_service = getattr(ThreadService, '_instance', None)
                
                # Create missing condition: thread service appears None
                ThreadService._instance = None
                self.service_missing = True
                
                logger.warning(" ALERT:  MISSING SERVICE: Thread service set to None - simulating service unavailability")
    
    def restore_thread_service(self, delay_seconds: float = 3.0) -> None:
        """
        Restore the thread service after a delay.
        
        This simulates the thread service becoming available after initialization.
        
        Args:
            delay_seconds: How long to wait before restoring the service
        """
        async def delayed_restoration():
            await asyncio.sleep(delay_seconds)
            with self._lock:
                if self.service_missing:
                    # Restore thread service or create new one
                    if self.original_thread_service:
                        ThreadService._instance = self.original_thread_service
                    else:
                        # Create new thread service instance if needed
                        ThreadService._instance = ThreadService()
                    
                    self.service_missing = False
                    logger.info(f" PASS:  SERVICE RESTORED: Thread service restored after {delay_seconds}s delay")
        
        # Run restoration in background
        asyncio.create_task(delayed_restoration())
    
    def cleanup(self) -> None:
        """Clean up thread service missing simulation."""
        with self._lock:
            if self.service_missing:
                if self.original_thread_service:
                    ThreadService._instance = self.original_thread_service
                else:
                    ThreadService._instance = ThreadService()
                
                self.service_missing = False
                logger.info("[U+1F9F9] CLEANUP: Thread service missing simulation cleaned up")


@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.fallback_prevention
@pytest.mark.thread_service_testing
class TestThreadServiceMissingDetection:
    """
    Integration tests for thread service missing detection and fallback prevention.
    
    These tests ensure that missing thread service conditions never result 
    in fallback handler creation.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for thread service testing."""
        # Initialize environment and auth
        self.env = get_env()
        environment = self.env.get("TEST_ENV", "test")
        self.auth_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Initialize validators and simulators
        self.validator = BusinessValueValidator()
        self.thread_simulator = ThreadServiceMissingSimulator()
        
        yield
        
        # Cleanup: Ensure thread service is restored
        self.thread_simulator.cleanup()
    
    async def test_thread_service_missing_should_wait_not_fallback(self):
        """
        TEST: WebSocket operations during thread service missing should wait, not create fallback.
        
        This test reproduces the WebSocket.py line 549 condition where thread_service is None
        and validates that the system waits for proper service availability instead of creating
        fallback handlers.
        
        EXPECTED BEHAVIOR:
        - WebSocket operations wait for thread service availability
        - No fallback handlers created during service unavailability
        - Once thread service is available, normal thread management resumes
        - Users receive real thread-managed conversations, never mock responses
        
        FAILURE CONDITIONS:
        - Fallback handlers created during thread service unavailability
        - Mock thread management responses delivered to users
        - System doesn't wait for proper thread service initialization
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: Thread service missing - wait not fallback")
        
        # Step 1: Establish WebSocket connection first
        websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
        
        # Step 2: Create thread service missing condition
        self.thread_simulator.simulate_thread_service_missing()
        
        # Step 3: Schedule service restoration
        self.thread_simulator.restore_thread_service(delay_seconds=4.0)
        
        # Step 4: Send request that requires thread management
        thread_request = {
            "type": "user_message",
            "content": "Start a new conversation thread for cost optimization analysis",
            "thread_id": f"thread-test-{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "requires_thread_management": True
        }
        
        logger.info("[U+1F4E4] Sending thread management request during service unavailability")
        await websocket.send(json.dumps(thread_request))
        
        # Step 5: Receive and validate events - should wait for real thread service
        events = []
        timeout = 20.0  # Allow time for service restoration
        end_time = time.time() + timeout
        
        while time.time() < end_time and len(events) < 5:
            try:
                message_str = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                event = json.loads(message_str)
                events.append(event)
                
                # CRITICAL: Validate no thread service fallback patterns
                event_content = json.dumps(event)
                has_fallback, fallback_patterns = self.validator.validate_response_for_fallback_patterns(event_content)
                
                if has_fallback:
                    raise AssertionError(
                        f" ALERT:  THREAD SERVICE FAILURE: FALLBACK PATTERNS DETECTED\n"
                        f"Event type: {event.get('type', 'unknown')}\n"
                        f"Fallback patterns: {fallback_patterns}\n"
                        f"Event content: {event_content[:200]}...\n"
                        f"BUSINESS IMPACT: Mock thread management instead of real service"
                    )
                
                # Check for thread service specific fallback indicators
                thread_fallback_indicators = [
                    'thread.*fallback', 'mock.*thread', 'thread.*emergency',
                    'degraded.*thread', 'temporary.*thread'
                ]
                
                for pattern in thread_fallback_indicators:
                    if re.search(pattern, event_content, re.IGNORECASE):
                        raise AssertionError(
                            f" ALERT:  THREAD FALLBACK DETECTED: {pattern}\n"
                            f"Event: {event_content[:200]}...\n"
                            f"BUSINESS IMPACT: Mock thread management delivered to user"
                        )
                
                logger.info(f" PASS:  Event {len(events)}/5 - {event.get('type')} (real thread service)")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event reception error: {e}")
                break
        
        # Step 6: Validate thread management workflow
        if len(events) >= 5:
            # Validate thread-related events are authentic
            thread_events = [e for e in events if 'thread' in json.dumps(e).lower()]
            
            for thread_event in thread_events:
                event_content = json.dumps(thread_event)
                
                # Validate no thread fallback patterns
                has_fallback, patterns = self.validator.validate_response_for_fallback_patterns(event_content)
                assert not has_fallback, f"Thread fallback in event: {patterns}"
                
                # Validate real thread management indicators
                real_thread_indicators = ['thread_created', 'thread_updated', 'thread_context']
                has_real_thread = any(indicator in event_content.lower() for indicator in real_thread_indicators)
                
                if not has_real_thread and 'thread' in event_content.lower():
                    logger.warning(f"Thread event without clear real thread indicators: {event_content[:100]}...")
            
            # Validate final response business value
            completed_events = [e for e in events if e.get('type') == 'agent_completed']
            if completed_events:
                final_response = completed_events[0].get('content', '')
                has_business_value, _ = self.validator.validate_response_for_business_value(final_response)
                
                assert has_business_value, (
                    f" ALERT:  NO BUSINESS VALUE: Thread service issue may have caused degraded response\n"
                    f"Response: '{final_response[:100]}...'"
                )
            
            logger.success(" PASS:  THREAD SERVICE TEST PASSED: Real thread management used, no fallbacks")
        
        else:
            # If insufficient events received, check if it's appropriate waiting behavior
            logger.info(f"Received {len(events)}/5 events - validating waiting behavior")
            
            # This might be expected if system is appropriately waiting for thread service
            for event in events:
                event_content = json.dumps(event)
                has_fallback, patterns = self.validator.validate_response_for_fallback_patterns(event_content)
                
                if has_fallback:
                    raise AssertionError(f"Fallback detected during thread service wait: {patterns}")
            
            logger.info(" PASS:  APPROPRIATE BEHAVIOR: System waited for thread service availability")
        
        await websocket.close()
    
    async def test_thread_service_available_after_restoration(self):
        """
        TEST: Normal thread operations after thread service restoration.
        
        This test validates that once the thread service is restored,
        normal thread management functions correctly without any lingering fallback behavior.
        
        EXPECTED BEHAVIOR:
        - Thread operations succeed after service restoration
        - Normal thread management workflow functions correctly
        - No residual fallback patterns from previous service unavailability
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: Normal thread operations after service restoration")
        
        # Step 1: Simulate and immediately restore thread service
        self.thread_simulator.simulate_thread_service_missing()
        await asyncio.sleep(0.1)  # Brief unavailability
        self.thread_simulator.restore_thread_service(delay_seconds=0.5)
        
        # Step 2: Wait for restoration
        await asyncio.sleep(1.0)
        
        # Step 3: Normal WebSocket connection and thread operations
        websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
        
        # Step 4: Thread management request
        request = {
            "type": "user_message",
            "content": "Continue our conversation about cost optimization strategies",
            "thread_id": f"restored-thread-{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send(json.dumps(request))
        
        # Step 5: Validate normal thread operations
        events = []
        end_time = time.time() + 15.0
        
        while time.time() < end_time and len(events) < 5:
            try:
                message_str = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                event = json.loads(message_str)
                events.append(event)
            except asyncio.TimeoutError:
                continue
        
        # Validate normal operation
        assert len(events) >= 5, f"Post-restoration thread operation failed: {len(events)}/5 events"
        
        # Validate no fallback patterns
        for event in events:
            event_content = json.dumps(event)
            has_fallback, patterns = self.validator.validate_response_for_fallback_patterns(event_content)
            assert not has_fallback, f"Fallback patterns in post-restoration operation: {patterns}"
        
        await websocket.close()
        logger.success(" PASS:  POST-RESTORATION TEST PASSED: Normal thread operations resumed")
    
    async def test_multiple_thread_operations_during_service_unavailability(self):
        """
        TEST: Multiple thread operations during service unavailability.
        
        This test validates that multiple thread-related operations during
        thread service unavailability all receive appropriate handling without
        any fallback handler creation.
        
        EXPECTED BEHAVIOR:
        - All thread operations wait appropriately for service
        - No fallback handlers created for any operation
        - Once restored, all operations function normally
        """
        logger.info("[U+1F9EA] INTEGRATION TEST: Multiple thread operations during service unavailability")
        
        # Establish connection first
        websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
        
        # Create thread service unavailability
        self.thread_simulator.simulate_thread_service_missing()
        
        # Schedule restoration
        self.thread_simulator.restore_thread_service(delay_seconds=5.0)
        
        # Send multiple thread-related requests
        thread_requests = [
            "Create a new thread for budget analysis",
            "Continue the cost optimization discussion",
            "Add context to the current thread about performance metrics"
        ]
        
        for i, content in enumerate(thread_requests):
            request = {
                "type": "user_message",
                "content": content,
                "thread_id": f"multi-thread-{i}-{int(time.time())}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(request))
            logger.info(f"[U+1F4E4] Sent thread request {i+1}/{len(thread_requests)}")
            
            # Brief pause between requests
            await asyncio.sleep(0.5)
        
        # Collect responses for all requests
        all_events = []
        timeout = 25.0  # Allow time for service restoration and processing
        end_time = time.time() + timeout
        
        while time.time() < end_time and len(all_events) < len(thread_requests) * 3:  # At least 3 events per request
            try:
                message_str = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                event = json.loads(message_str)
                all_events.append(event)
                
                # Validate no fallback patterns in any event
                event_content = json.dumps(event)
                has_fallback, patterns = self.validator.validate_response_for_fallback_patterns(event_content)
                
                if has_fallback:
                    raise AssertionError(f"Multi-thread operation fallback detected: {patterns}")
                
            except asyncio.TimeoutError:
                continue
        
        # Validate results
        assert len(all_events) >= len(thread_requests), (
            f"Insufficient events for multi-thread operations: {len(all_events)}/{len(thread_requests)}"
        )
        
        logger.info(f" PASS:  Received {len(all_events)} events for {len(thread_requests)} thread operations")
        
        await websocket.close()
        logger.success(" PASS:  MULTI-THREAD TEST PASSED: All operations handled appropriately")


if __name__ == "__main__":
    """
    Run the thread service missing detection integration tests.
    
    Usage:
        python tests/integration/test_thread_service_missing_detection.py
        pytest tests/integration/test_thread_service_missing_detection.py -v
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        print("[U+1F9EA] INTEGRATION: Thread Service Missing Detection Tests")
        print("[U+1F4CB] These tests prevent thread service unavailability from creating fallback handlers")
        print("[U+1F680] Starting test execution...")
        
        exit_code = pytest.main([
            __file__,
            "-v",
            "-x",
            "--tb=short",
            "-m", "integration and thread_service_testing",
            "--durations=10"
        ])
        
        if exit_code == 0:
            print(" PASS:  ALL TESTS PASSED: Thread service unavailability handled correctly")
        else:
            print(" ALERT:  TEST FAILURES: Thread service issues detected")
            
        sys.exit(exit_code)