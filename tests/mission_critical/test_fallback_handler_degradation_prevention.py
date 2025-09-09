#!/usr/bin/env python3
"""MISSION CRITICAL: Fallback Handler Degradation Prevention Test Suite

THIS SUITE MUST PASS OR THE PRODUCT IS BROKEN.
Business Value: $500K+ ARR - Core agent business value protection

PURPOSE: This test suite prevents the fallback handler anti-pattern that degrades
business value by ensuring users NEVER receive mock responses instead of real AI agent value.

CRITICAL: These tests are designed to **FAIL HARD** when fallback handlers are created,
ensuring only real agent infrastructure delivers responses to users.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core system reliability
- Business Goal: Prevent fallback handlers from degrading real agent business value  
- Value Impact: Ensure users always receive authentic AI agent responses, not mock fallbacks
- Strategic Impact: Protects core business value delivery and prevents service degradation

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
from unittest.mock import patch, MagicMock
import threading
import re

# CRITICAL: Add project root to Python path for imports  
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import websockets
from loguru import logger

# Import environment and types after path setup
from shared.isolated_environment import get_env
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Import SSOT authentication - MANDATORY for E2E tests per CLAUDE.md
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper, 
    create_authenticated_user_context
)

# Import production components to validate against fallback creation
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.startup_manager import StartupManager

# Import test base for real services
from test_framework.base_e2e_test import BaseE2ETest


# =============================================================================
# SUPPORT CLASSES FOR FALLBACK DETECTION AND SERVICE CONTROL
# =============================================================================

class MockServiceController:
    """
    Controller for simulating service unavailability during race conditions.
    
    This class enables testing of fallback handler creation scenarios by
    temporarily disabling services to simulate startup/connection race conditions.
    """
    
    def __init__(self):
        """Initialize service controller for fallback testing."""
        self.original_services: Dict[str, Any] = {}
        self.disabled_services: Set[str] = set()
        self._lock = threading.Lock()
        
    def disable_agent_supervisor(self) -> None:
        """
        Disable agent supervisor to simulate race condition.
        
        This simulates the WebSocket.py line 529 condition where supervisor is None,
        which should cause the system to fail hard, not create fallback handlers.
        """
        with self._lock:
            if 'agent_supervisor' not in self.disabled_services:
                # Store original for restoration
                self.original_services['agent_supervisor'] = AgentRegistry._instance
                # Simulate None supervisor (race condition)
                AgentRegistry._instance = None
                self.disabled_services.add('agent_supervisor')
                logger.warning("🚨 MockServiceController: Agent supervisor DISABLED - simulating race condition")
    
    def disable_thread_service(self) -> None:
        """
        Disable thread service to simulate race condition.
        
        This simulates the WebSocket.py line 549 condition where thread_service is None,
        which should cause the system to fail hard, not create fallback handlers.
        """
        with self._lock:
            if 'thread_service' not in self.disabled_services:
                # Store original for restoration
                self.original_services['thread_service'] = getattr(ThreadService, '_instance', None)
                # Simulate None thread_service (race condition)
                if hasattr(ThreadService, '_instance'):
                    ThreadService._instance = None
                self.disabled_services.add('thread_service')
                logger.warning("🚨 MockServiceController: Thread service DISABLED - simulating race condition")
    
    def set_startup_incomplete(self) -> None:
        """
        Set startup_complete=False to simulate boot race condition.
        
        This simulates incomplete startup scenarios that should cause waiting
        or failure, not fallback handler creation.
        """
        with self._lock:
            if 'startup_incomplete' not in self.disabled_services:
                # Store original startup state
                self.original_services['startup_complete'] = getattr(StartupManager, '_startup_complete', True)
                # Force startup incomplete
                StartupManager._startup_complete = False
                self.disabled_services.add('startup_incomplete')
                logger.warning("🚨 MockServiceController: Startup INCOMPLETE - simulating boot race condition")
    
    def disable_all_services(self) -> None:
        """Disable all services to test cascade failure prevention."""
        self.disable_agent_supervisor()
        self.disable_thread_service() 
        self.set_startup_incomplete()
        logger.error("🚨 MockServiceController: ALL SERVICES DISABLED - testing cascade failure prevention")
    
    def restore_all_services(self) -> None:
        """Restore all disabled services to original state."""
        with self._lock:
            # Restore agent supervisor
            if 'agent_supervisor' in self.disabled_services:
                AgentRegistry._instance = self.original_services.get('agent_supervisor')
                self.disabled_services.discard('agent_supervisor')
                
            # Restore thread service
            if 'thread_service' in self.disabled_services:
                if hasattr(ThreadService, '_instance'):
                    ThreadService._instance = self.original_services.get('thread_service')
                self.disabled_services.discard('thread_service')
                
            # Restore startup state
            if 'startup_incomplete' in self.disabled_services:
                StartupManager._startup_complete = self.original_services.get('startup_complete', True)
                self.disabled_services.discard('startup_incomplete')
                
            logger.info("✅ MockServiceController: All services RESTORED")
    
    def is_service_disabled(self, service_name: str) -> bool:
        """Check if a service is currently disabled."""
        return service_name in self.disabled_services


class BusinessValueValidator:
    """
    Validator for distinguishing real agent responses from mock/fallback content.
    
    This class detects fallback patterns that indicate degraded business value
    and validates authentic agent responses that provide real business insights.
    
    CRITICAL: Any detection of fallback patterns should cause test failure.
    """
    
    # Fallback Handler Signatures (FORBIDDEN - cause test failure)
    FALLBACK_PATTERNS = {
        'agent_processed': r'Agent processed your message',
        'fallback_handler': r'FallbackAgentHandler',
        'processing_message': r'Processing your message',
        'response_generator': r'response_generator',
        'chat_agent': r'ChatAgent',  # Generic fallback name
    }
    
    # Emergency Handler Patterns (FORBIDDEN - cause test failure)
    EMERGENCY_PATTERNS = {
        'emergency_websocket': r'EmergencyWebSocketManager',
        'emergency_mode': r'emergency_mode',
        'degraded_functionality': r'degraded functionality',
        'limited_functionality': r'limited functionality',
    }
    
    # Service Degradation Indicators (FORBIDDEN - cause test failure)
    DEGRADATION_PATTERNS = {
        'service_info': r'service_info',
        'missing_dependencies': r'missing_dependencies',
        'fallback_active': r'fallback_active', 
        'reduced_functionality': r'reduced functionality',
    }
    
    # Real Business Value Indicators (REQUIRED for authentic responses)
    BUSINESS_VALUE_PATTERNS = {
        'cost_optimization': r'cost.optimization',
        'data_analysis': r'data.analysis',
        'recommendations': r'recommendations',
        'insights': r'insights',
        'action_items': r'action.items',
        'analysis_results': r'analysis.results',
        'optimization_opportunities': r'optimization.opportunities',
    }
    
    # Real Tool Execution Indicators (REQUIRED for authentic processing)
    TOOL_EXECUTION_PATTERNS = {
        'tool_result': r'tool_result',
        'analysis_complete': r'analysis.complete',
        'data_processed': r'data.processed',
        'optimization_complete': r'optimization.complete',
    }
    
    def __init__(self):
        """Initialize business value validator."""
        self.detected_patterns: Dict[str, List[str]] = {
            'fallback': [],
            'emergency': [],
            'degradation': [],
            'business_value': [],
            'tool_execution': []
        }
    
    def validate_response_for_fallback_patterns(self, response_content: str) -> Tuple[bool, List[str]]:
        """
        Validate response content for forbidden fallback patterns.
        
        Args:
            response_content: Response content to validate
            
        Returns:
            Tuple of (has_fallback_patterns, detected_patterns)
            
        CRITICAL: If has_fallback_patterns is True, test should FAIL.
        """
        detected = []
        content_lower = response_content.lower()
        
        # Check for fallback handler patterns
        for pattern_name, pattern in self.FALLBACK_PATTERNS.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                detected.append(f"FALLBACK: {pattern_name}")
                self.detected_patterns['fallback'].append(pattern_name)
        
        # Check for emergency handler patterns
        for pattern_name, pattern in self.EMERGENCY_PATTERNS.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                detected.append(f"EMERGENCY: {pattern_name}")
                self.detected_patterns['emergency'].append(pattern_name)
        
        # Check for service degradation patterns
        for pattern_name, pattern in self.DEGRADATION_PATTERNS.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                detected.append(f"DEGRADATION: {pattern_name}")
                self.detected_patterns['degradation'].append(pattern_name)
        
        has_fallback = len(detected) > 0
        return has_fallback, detected
    
    def validate_response_for_business_value(self, response_content: str) -> Tuple[bool, List[str]]:
        """
        Validate response content for authentic business value indicators.
        
        Args:
            response_content: Response content to validate
            
        Returns:
            Tuple of (has_business_value, detected_indicators)
            
        CRITICAL: If has_business_value is False, test should FAIL.
        """
        detected = []
        content_lower = response_content.lower()
        
        # Check for business value patterns
        for pattern_name, pattern in self.BUSINESS_VALUE_PATTERNS.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                detected.append(f"BUSINESS: {pattern_name}")
                self.detected_patterns['business_value'].append(pattern_name)
        
        # Check for tool execution patterns
        for pattern_name, pattern in self.TOOL_EXECUTION_PATTERNS.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                detected.append(f"TOOL: {pattern_name}")
                self.detected_patterns['tool_execution'].append(pattern_name)
        
        has_business_value = len(detected) > 0
        return has_business_value, detected
    
    def validate_websocket_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate WebSocket events for business value vs fallback indicators.
        
        Args:
            events: List of WebSocket events to validate
            
        Returns:
            Dictionary with validation results and detected patterns
        """
        validation_result = {
            'total_events': len(events),
            'fallback_events': 0,
            'business_value_events': 0,
            'required_events_present': [],
            'forbidden_patterns_detected': [],
            'is_valid': True,
            'failure_reason': None
        }
        
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        present_event_types = {event.get('type') for event in events}
        
        # Check for required WebSocket events
        validation_result['required_events_present'] = list(required_events.intersection(present_event_types))
        missing_events = required_events - present_event_types
        
        if missing_events:
            validation_result['is_valid'] = False
            validation_result['failure_reason'] = f"Missing required events: {missing_events}"
        
        # Validate each event content
        for event in events:
            event_content = json.dumps(event).lower()
            
            # Check for fallback patterns in events
            has_fallback, fallback_patterns = self.validate_response_for_fallback_patterns(event_content)
            if has_fallback:
                validation_result['fallback_events'] += 1
                validation_result['forbidden_patterns_detected'].extend(fallback_patterns)
                validation_result['is_valid'] = False
                if not validation_result['failure_reason']:
                    validation_result['failure_reason'] = f"Fallback patterns detected: {fallback_patterns}"
            
            # Check for business value patterns in events
            has_business_value, business_patterns = self.validate_response_for_business_value(event_content)
            if has_business_value:
                validation_result['business_value_events'] += 1
        
        return validation_result
    
    def assert_no_fallback_patterns(self, content: str, context: str = "response") -> None:
        """
        Assert that content contains no fallback patterns.
        
        Args:
            content: Content to validate
            context: Context description for error messages
            
        Raises:
            AssertionError: If fallback patterns are detected
        """
        has_fallback, patterns = self.validate_response_for_fallback_patterns(content)
        
        if has_fallback:
            error_message = (
                f"🚨 FALLBACK HANDLER DETECTED in {context}: {patterns}\n"
                f"Content sample: {content[:200]}...\n"
                f"BUSINESS IMPACT: Users receiving mock responses instead of real AI agent value.\n"
                f"This violates SSOT principles and provides no business value while appearing to 'work'."
            )
            raise AssertionError(error_message)
    
    def assert_has_business_value(self, content: str, context: str = "response") -> None:
        """
        Assert that content contains authentic business value indicators.
        
        Args:
            content: Content to validate
            context: Context description for error messages
            
        Raises:
            AssertionError: If no business value indicators are detected
        """
        has_business_value, patterns = self.validate_response_for_business_value(content)
        
        if not has_business_value:
            error_message = (
                f"🚨 NO BUSINESS VALUE DETECTED in {context}\n"
                f"Content sample: {content[:200]}...\n"
                f"BUSINESS IMPACT: Response lacks authentic AI agent insights.\n"
                f"Users should receive actionable business value, not generic content."
            )
            raise AssertionError(error_message)


class WebSocketTestClient:
    """
    E2E WebSocket test client with proper authentication and fallback detection.
    
    This client provides real WebSocket testing capabilities while detecting
    any fallback handler creation that would degrade business value.
    """
    
    def __init__(self, auth_helper: E2EWebSocketAuthHelper, validator: BusinessValueValidator):
        """
        Initialize WebSocket test client.
        
        Args:
            auth_helper: E2E WebSocket authentication helper 
            validator: Business value validator for fallback detection
        """
        self.auth_helper = auth_helper
        self.validator = validator
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.received_events: List[Dict[str, Any]] = []
        self.connection_start_time: Optional[float] = None
        self.is_connected = False
        
    async def connect(self, timeout: float = 10.0) -> None:
        """
        Connect to WebSocket with authentication.
        
        Args:
            timeout: Connection timeout in seconds
            
        Raises:
            TimeoutError: If connection times out
            AssertionError: If connection fails due to fallback handlers
        """
        self.connection_start_time = time.time()
        
        try:
            self.websocket = await self.auth_helper.connect_authenticated_websocket(timeout=timeout)
            self.is_connected = True
            logger.info("✅ WebSocket test client connected successfully")
            
        except Exception as e:
            error_message = f"WebSocket connection failed: {e}"
            
            # Check if failure might be due to fallback handlers
            if "fallback" in str(e).lower() or "mock" in str(e).lower():
                error_message += "\n🚨 POSSIBLE FALLBACK HANDLER ISSUE: Connection failure may indicate fallback creation"
            
            logger.error(error_message)
            raise AssertionError(error_message)
    
    async def send_agent_request(self, message: str, thread_id: Optional[str] = None) -> None:
        """
        Send agent request via WebSocket.
        
        Args:
            message: Agent request message
            thread_id: Optional thread ID (auto-generated if not provided)
            
        Raises:
            AssertionError: If WebSocket not connected
        """
        if not self.is_connected or not self.websocket:
            raise AssertionError("WebSocket not connected - cannot send agent request")
        
        thread_id = thread_id or f"test-thread-{uuid.uuid4().hex[:8]}"
        
        request = {
            "type": "agent_request",
            "message": message,
            "thread_id": thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"test-request-{uuid.uuid4().hex[:8]}"
        }
        
        await self.websocket.send(json.dumps(request))
        logger.info(f"📤 Sent agent request: {message[:50]}...")
    
    async def receive_events(self, timeout: float = 30.0, expected_events: int = 5) -> List[Dict[str, Any]]:
        """
        Receive WebSocket events with fallback detection.
        
        Args:
            timeout: Timeout for receiving events
            expected_events: Number of events expected (5 for complete agent flow)
            
        Returns:
            List of received WebSocket events
            
        Raises:
            AssertionError: If fallback patterns detected or timeout occurs
        """
        if not self.is_connected or not self.websocket:
            raise AssertionError("WebSocket not connected - cannot receive events")
        
        events = []
        start_time = time.time()
        
        try:
            while len(events) < expected_events and (time.time() - start_time) < timeout:
                # Wait for next event with shorter timeout
                event_timeout = min(5.0, timeout - (time.time() - start_time))
                
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=event_timeout)
                    event = json.loads(message)
                    events.append(event)
                    self.received_events.append(event)
                    
                    # CRITICAL: Check each event for fallback patterns immediately
                    event_content = json.dumps(event)
                    self.validator.assert_no_fallback_patterns(
                        event_content, 
                        context=f"WebSocket event {event.get('type', 'unknown')}"
                    )
                    
                    logger.info(f"📥 Received event: {event.get('type', 'unknown')}")
                    
                    # Check for completion
                    if event.get('type') == 'agent_completed':
                        logger.info("✅ Agent completed - checking for additional events")
                        # Brief wait for any additional events
                        await asyncio.sleep(0.5)
                        break
                        
                except asyncio.TimeoutError:
                    if len(events) == 0:
                        # No events received at all - potential fallback issue
                        raise AssertionError(
                            f"🚨 NO EVENTS RECEIVED within {event_timeout}s - potential fallback handler blocking events"
                        )
                    else:
                        # Some events received, continue waiting
                        logger.warning(f"⏳ Timeout waiting for event {len(events)+1}, continuing...")
                        continue
        
        except Exception as e:
            error_message = f"Error receiving events: {e}"
            
            # Enhanced error context for fallback detection
            if "fallback" in str(e).lower():
                error_message += "\n🚨 FALLBACK HANDLER DETECTED during event reception"
            elif len(events) == 0:
                error_message += f"\n🚨 NO EVENTS RECEIVED - possible service unavailability or fallback blocking"
            elif len(events) < expected_events:
                error_message += f"\n⚠️ INCOMPLETE EVENT SEQUENCE: {len(events)}/{expected_events} events received"
            
            raise AssertionError(error_message)
        
        # Validate received events
        if len(events) == 0:
            raise AssertionError("🚨 ZERO EVENTS RECEIVED - indicates fallback handlers or service failure")
        
        logger.info(f"✅ Received {len(events)} WebSocket events")
        return events
    
    async def disconnect(self) -> None:
        """Disconnect WebSocket connection."""
        if self.websocket and self.is_connected:
            await self.websocket.close()
            self.is_connected = False
            logger.info("🔌 WebSocket test client disconnected")
    
    def get_connection_duration(self) -> float:
        """Get connection duration in seconds."""
        if self.connection_start_time:
            return time.time() - self.connection_start_time
        return 0.0
    
    def assert_processing_duration_indicates_real_work(self, min_duration: float = 2.0) -> None:
        """
        Assert that processing duration indicates real work, not mock responses.
        
        Args:
            min_duration: Minimum duration for real processing
            
        Raises:
            AssertionError: If processing was too fast (indicates mock/fallback)
        """
        duration = self.get_connection_duration()
        
        if duration < min_duration:
            raise AssertionError(
                f"🚨 SUSPICIOUSLY FAST PROCESSING: {duration:.2f}s < {min_duration}s\n"
                f"BUSINESS IMPACT: Fast responses indicate mock/fallback handlers, not real AI processing.\n"
                f"Users should receive authentic agent processing, not instant mock responses."
            )


# =============================================================================
# MISSION CRITICAL TEST SUITE - FALLBACK HANDLER PREVENTION
# =============================================================================

@pytest.mark.e2e
@pytest.mark.mission_critical
@pytest.mark.real_services
@pytest.mark.fallback_prevention
class TestFallbackHandlerDegradationPrevention(BaseE2ETest):
    """
    Mission Critical Test Suite: Fallback Handler Degradation Prevention
    
    PURPOSE: Prevent fallback handler anti-pattern that degrades business value
    by ensuring users receive real AI agent responses, not mock fallback content.
    
    CRITICAL: These tests FAIL HARD when fallback handlers are detected.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment with fallback detection capabilities."""
        # Initialize service controller for race condition simulation
        self.service_controller = MockServiceController()
        
        # Initialize business value validator
        self.validator = BusinessValueValidator()
        
        # Initialize E2E WebSocket auth helper
        self.auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Initialize WebSocket test client
        self.ws_client = WebSocketTestClient(self.auth_helper, self.validator)
        
        yield
        
        # Cleanup: Restore all services and disconnect WebSocket
        self.service_controller.restore_all_services()
        asyncio.run(self.ws_client.disconnect())
        
    @pytest.mark.business_value_validation
    async def test_real_agent_provides_authentic_business_value(self):
        """
        BASELINE TEST: Validate that real agents provide authentic business value.
        
        PURPOSE: Establish baseline for authentic agent responses vs fallback content.
        This test must pass to confirm the system can deliver real business value.
        
        SUCCESS CRITERIA:
        - All 5 WebSocket events received: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        - Processing duration >= 2 seconds (real processing time)
        - Final response contains actionable business insights
        - Response length > 50 characters with optimization content
        - NO fallback patterns detected
        
        FAILURE CONDITIONS:
        - Any mock indicators in responses
        - Missing critical WebSocket events  
        - Suspiciously fast processing (instant responses)
        - Generic or template-like content
        """
        logger.info("🧪 TEST: Real agent provides authentic business value (BASELINE)")
        
        # Connect WebSocket with full real infrastructure
        await self.ws_client.connect(timeout=15.0)
        
        # Send high-value business request requiring analysis
        business_request = (
            "Analyze my cloud infrastructure costs and provide specific optimization recommendations "
            "with actionable insights for reducing spending while maintaining performance."
        )
        
        await self.ws_client.send_agent_request(business_request)
        logger.info("📤 Sent high-value business analysis request")
        
        # Receive and validate all WebSocket events
        events = await self.ws_client.receive_events(timeout=60.0, expected_events=5)
        
        # Assert minimum event count
        assert len(events) >= 5, f"🚨 INSUFFICIENT EVENTS: {len(events)}/5 - missing critical agent workflow events"
        
        # Validate WebSocket events for business value
        event_validation = self.validator.validate_websocket_events(events)
        
        assert event_validation['is_valid'], (
            f"🚨 EVENT VALIDATION FAILED: {event_validation['failure_reason']}\n"
            f"Forbidden patterns: {event_validation['forbidden_patterns_detected']}\n"
            f"Required events present: {event_validation['required_events_present']}"
        )
        
        # Validate processing duration indicates real work
        self.ws_client.assert_processing_duration_indicates_real_work(min_duration=2.0)
        
        # Find agent_completed event for final response validation
        completed_events = [e for e in events if e.get('type') == 'agent_completed']
        assert len(completed_events) > 0, "🚨 NO AGENT_COMPLETED EVENT - incomplete agent workflow"
        
        final_response = completed_events[0].get('content', '')
        assert len(final_response) > 50, (
            f"🚨 INSUFFICIENT RESPONSE LENGTH: {len(final_response)} chars - indicates mock/template response"
        )
        
        # Validate final response contains authentic business value
        self.validator.assert_has_business_value(final_response, context="final agent response")
        self.validator.assert_no_fallback_patterns(final_response, context="final agent response")
        
        logger.success("✅ BASELINE PASSED: Real agent provides authentic business value")
    
    async def test_agent_supervisor_unavailable_should_fail_hard(self):
        """
        TEST SCENARIO 1: Agent Supervisor Unavailable Race Condition
        
        REPRODUCES: WebSocket.py line 529 condition where supervisor is None
        
        EXPECTATION: System should WAIT for real supervisor or FAIL, 
        never use _create_fallback_agent_handler
        
        TEST FLOW:
        1. Create authenticated user context
        2. Connect WebSocket BEFORE disabling supervisor (simulates race condition)
        3. Disable agent_supervisor after connection established  
        4. Send agent request that would trigger fallback handler
        5. ASSERT: System fails hard or waits, NO fallback content delivered
        
        CRITICAL: Any fallback response should cause test FAILURE.
        """
        logger.info("🧪 TEST: Agent supervisor unavailable should fail hard")
        
        # Step 1: Connect WebSocket with real infrastructure first
        await self.ws_client.connect(timeout=10.0)
        logger.info("✅ WebSocket connected with real supervisor")
        
        # Step 2: Disable agent supervisor to simulate race condition
        self.service_controller.disable_agent_supervisor()
        
        # Step 3: Send agent request that would trigger fallback handler
        try:
            await self.ws_client.send_agent_request("Test message requiring supervisor")
            logger.info("📤 Sent request with supervisor unavailable")
            
            # Step 4: Attempt to receive events - should fail or get proper error
            try:
                events = await self.ws_client.receive_events(timeout=10.0, expected_events=5)
                
                # If we get events, they MUST NOT contain fallback patterns
                for event in events:
                    event_content = json.dumps(event)
                    self.validator.assert_no_fallback_patterns(
                        event_content, 
                        context=f"event during supervisor unavailability"
                    )
                
                # If we received a completion event, validate it's not fallback content
                completed_events = [e for e in events if e.get('type') == 'agent_completed']
                if completed_events:
                    final_response = completed_events[0].get('content', '')
                    self.validator.assert_no_fallback_patterns(
                        final_response, 
                        context="response during supervisor unavailability"
                    )
                    
                    # Response should either be a proper error or real agent content
                    if "error" not in final_response.lower():
                        self.validator.assert_has_business_value(
                            final_response, 
                            context="non-error response during supervisor unavailability"
                        )
                        
                logger.warning("⚠️ System continued processing despite supervisor unavailability - validating response quality")
                
            except AssertionError as e:
                # Expected outcome - system should fail when supervisor unavailable
                if "FALLBACK HANDLER DETECTED" in str(e):
                    # CRITICAL FAILURE: Fallback handler was used
                    raise AssertionError(
                        f"🚨 CRITICAL FAILURE: Fallback handler created when supervisor unavailable\n"
                        f"BUSINESS IMPACT: Users receiving mock responses instead of proper error/waiting.\n"
                        f"Original error: {e}"
                    )
                else:
                    # Good outcome - system failed appropriately
                    logger.success(f"✅ EXPECTED FAILURE: System failed appropriately when supervisor unavailable: {e}")
                    return
            
            except Exception as e:
                # System properly failed - this is expected behavior
                error_msg = str(e)
                if "fallback" in error_msg.lower() or "mock" in error_msg.lower():
                    raise AssertionError(
                        f"🚨 FALLBACK DETECTED in error handling: {error_msg}\n"
                        f"System should fail cleanly without fallback references."
                    )
                else:
                    logger.success(f"✅ EXPECTED FAILURE: System failed cleanly when supervisor unavailable: {error_msg}")
                    return
        
        except Exception as e:
            # System properly failed during send - this is acceptable
            error_msg = str(e)
            if "fallback" in error_msg.lower():
                raise AssertionError(
                    f"🚨 FALLBACK DETECTED during send: {error_msg}\n"
                    f"System should fail without creating fallback handlers."
                )
            else:
                logger.success(f"✅ EXPECTED FAILURE: System failed to send when supervisor unavailable: {error_msg}")
                return
        
        logger.success("✅ PASSED: No fallback handlers created during supervisor unavailability")
    
    async def test_thread_service_unavailable_should_fail_hard(self):
        """
        TEST SCENARIO 2: Thread Service Missing Race Condition
        
        REPRODUCES: WebSocket.py line 549 condition where thread_service is None
        
        EXPECTATION: System should WAIT for real thread_service or FAIL
        
        TEST FLOW:
        1. Establish authenticated WebSocket connection
        2. Disable thread_service simulating initialization race
        3. Send message requiring thread management
        4. ASSERT: System waits/fails hard, NO thread service fallback responses
        
        CRITICAL: No thread service fallback handlers should be created.
        """
        logger.info("🧪 TEST: Thread service unavailable should fail hard")
        
        # Connect WebSocket with real infrastructure
        await self.ws_client.connect(timeout=10.0)
        logger.info("✅ WebSocket connected with real thread service")
        
        # Disable thread service to simulate race condition
        self.service_controller.disable_thread_service()
        
        # Send message requiring thread management
        try:
            await self.ws_client.send_agent_request("Create a new analysis thread for cost optimization")
            logger.info("📤 Sent thread management request with thread service unavailable")
            
            # Attempt to receive events - should fail appropriately
            try:
                events = await self.ws_client.receive_events(timeout=10.0, expected_events=5)
                
                # Validate no thread service fallback patterns
                for event in events:
                    event_content = json.dumps(event)
                    # Check for thread service specific fallback patterns
                    if re.search(r'thread.*fallback|mock.*thread|temporary.*thread', event_content, re.IGNORECASE):
                        raise AssertionError(
                            f"🚨 THREAD SERVICE FALLBACK DETECTED: {event_content[:200]}...\n"
                            f"Thread operations should fail hard, not use fallback thread management."
                        )
                    
                    self.validator.assert_no_fallback_patterns(
                        event_content, 
                        context="event during thread service unavailability"
                    )
                
                logger.warning("⚠️ System processed thread request despite thread service unavailability")
                
            except AssertionError as e:
                if "FALLBACK HANDLER DETECTED" in str(e) or "THREAD SERVICE FALLBACK" in str(e):
                    raise AssertionError(
                        f"🚨 CRITICAL FAILURE: Thread service fallback handler created\n"
                        f"BUSINESS IMPACT: Mock thread management instead of proper failure.\n"
                        f"Original error: {e}"
                    )
                else:
                    logger.success(f"✅ EXPECTED FAILURE: System failed appropriately without thread service: {e}")
                    return
            
            except Exception as e:
                error_msg = str(e)
                if "thread" in error_msg.lower() and "fallback" in error_msg.lower():
                    raise AssertionError(f"🚨 THREAD FALLBACK DETECTED: {error_msg}")
                else:
                    logger.success(f"✅ EXPECTED FAILURE: System failed cleanly without thread service: {error_msg}")
                    return
        
        except Exception as e:
            error_msg = str(e)
            if "fallback" in error_msg.lower() and "thread" in error_msg.lower():
                raise AssertionError(f"🚨 THREAD FALLBACK in send operation: {error_msg}")
            else:
                logger.success(f"✅ EXPECTED FAILURE: Send failed appropriately without thread service: {error_msg}")
                return
        
        logger.success("✅ PASSED: No thread service fallback handlers created")
    
    async def test_startup_incomplete_should_wait_or_fail_not_fallback(self):
        """
        TEST SCENARIO 3: Startup Race Condition
        
        REPRODUCES: startup_complete=False race conditions during system boot
        
        EXPECTATION: Wait for startup_complete=True or fail with clear error
        
        TEST FLOW:
        1. Force startup_complete=False to simulate boot race condition
        2. Attempt WebSocket connection during "startup"
        3. Send agent request during incomplete startup  
        4. ASSERT: System waits or fails clearly, NO startup fallback content
        
        CRITICAL: No startup fallback content should be delivered to users.
        """
        logger.info("🧪 TEST: Startup incomplete should wait or fail, not fallback")
        
        # Force startup incomplete to simulate boot race condition
        self.service_controller.set_startup_incomplete()
        
        # Attempt WebSocket connection during startup
        try:
            await self.ws_client.connect(timeout=15.0)  # Longer timeout for potential waiting
            logger.info("✅ WebSocket connected despite incomplete startup")
            
            # Send agent request during incomplete startup
            try:
                await self.ws_client.send_agent_request("Test request during system startup")
                logger.info("📤 Sent request during incomplete startup")
                
                # Attempt to receive events
                try:
                    events = await self.ws_client.receive_events(timeout=15.0, expected_events=5)
                    
                    # Validate no startup fallback patterns
                    for event in events:
                        event_content = json.dumps(event)
                        # Check for startup-specific fallback patterns
                        if re.search(r'startup.*fallback|boot.*mock|initialization.*temporary', event_content, re.IGNORECASE):
                            raise AssertionError(
                                f"🚨 STARTUP FALLBACK DETECTED: {event_content[:200]}...\n"
                                f"System should wait for complete startup, not provide startup fallback content."
                            )
                        
                        self.validator.assert_no_fallback_patterns(
                            event_content, 
                            context="event during incomplete startup"
                        )
                    
                    # If we get a completion, ensure it's either proper error or full business value
                    completed_events = [e for e in events if e.get('type') == 'agent_completed']
                    if completed_events:
                        final_response = completed_events[0].get('content', '')
                        if "startup" not in final_response.lower() and "initialization" not in final_response.lower():
                            # If not a startup-related error, should have full business value
                            self.validator.assert_has_business_value(
                                final_response, 
                                context="response during startup (non-startup-error)"
                            )
                    
                    logger.warning("⚠️ System processed request despite incomplete startup - validating response quality")
                    
                except AssertionError as e:
                    if "FALLBACK HANDLER DETECTED" in str(e) or "STARTUP FALLBACK" in str(e):
                        raise AssertionError(
                            f"🚨 CRITICAL FAILURE: Startup fallback handler created\n"
                            f"BUSINESS IMPACT: Mock startup responses instead of proper waiting/error.\n"
                            f"Original error: {e}"
                        )
                    else:
                        logger.success(f"✅ EXPECTED BEHAVIOR: System handled startup appropriately: {e}")
                        return
                
                except Exception as e:
                    error_msg = str(e)
                    if "startup" in error_msg.lower() and "fallback" in error_msg.lower():
                        raise AssertionError(f"🚨 STARTUP FALLBACK DETECTED: {error_msg}")
                    else:
                        logger.success(f"✅ EXPECTED BEHAVIOR: System failed/waited appropriately during startup: {error_msg}")
                        return
            
            except Exception as e:
                error_msg = str(e)
                if "fallback" in error_msg.lower():
                    raise AssertionError(f"🚨 FALLBACK DETECTED during startup send: {error_msg}")
                else:
                    logger.success(f"✅ EXPECTED BEHAVIOR: Send operation handled startup appropriately: {error_msg}")
                    return
        
        except Exception as e:
            # Connection failed during startup - this is acceptable behavior
            error_msg = str(e)
            if "fallback" in error_msg.lower():
                raise AssertionError(f"🚨 STARTUP FALLBACK in connection: {error_msg}")
            else:
                logger.success(f"✅ EXPECTED BEHAVIOR: Connection handled incomplete startup appropriately: {error_msg}")
                return
        
        logger.success("✅ PASSED: No startup fallback handlers created during incomplete startup")
    
    async def test_multiple_service_failures_should_not_cascade_to_fallbacks(self):
        """
        TEST SCENARIO 5: Multiple Service Failure Cascade Prevention
        
        PURPOSE: Prevent fallback handler cascades during multiple service failures
        
        TEST FLOW:
        1. Simultaneously disable multiple services (supervisor, thread_service, startup_complete)
        2. Send high-value business request
        3. ASSERT: Clear failure, not fallback cascade
        
        CRITICAL: Multiple fallback handlers should NEVER be created.
        This scenario tests the most dangerous anti-pattern where multiple
        service failures lead to cascading fallback creation.
        """
        logger.info("🧪 TEST: Multiple service failures should not cascade to fallbacks")
        
        # Disable ALL services to test cascade failure prevention
        self.service_controller.disable_all_services()
        logger.error("🚨 ALL SERVICES DISABLED - testing cascade failure prevention")
        
        # Attempt WebSocket connection with all services down
        try:
            await self.ws_client.connect(timeout=10.0)
            logger.warning("⚠️ WebSocket connected despite all services being disabled")
            
            # Send high-value business request
            try:
                await self.ws_client.send_agent_request(
                    "Provide comprehensive cost optimization analysis with detailed recommendations"
                )
                logger.info("📤 Sent business request with all services disabled")
                
                # Attempt to receive events
                try:
                    events = await self.ws_client.receive_events(timeout=10.0, expected_events=5)
                    
                    # CRITICAL: Check for cascading fallback patterns
                    fallback_count = 0
                    cascade_patterns = []
                    
                    for event in events:
                        event_content = json.dumps(event)
                        
                        # Count fallback indicators
                        has_fallback, patterns = self.validator.validate_response_for_fallback_patterns(event_content)
                        if has_fallback:
                            fallback_count += 1
                            cascade_patterns.extend(patterns)
                        
                        # Check for multiple service fallback indicators
                        multiple_fallback_indicators = [
                            'supervisor.*fallback', 'thread.*fallback', 'startup.*fallback',
                            'emergency.*mode', 'degraded.*functionality', 'cascade.*fallback'
                        ]
                        
                        for pattern in multiple_fallback_indicators:
                            if re.search(pattern, event_content, re.IGNORECASE):
                                cascade_patterns.append(f"CASCADE: {pattern}")
                    
                    # CRITICAL FAILURE: Multiple fallback patterns detected
                    if fallback_count > 1:
                        raise AssertionError(
                            f"🚨 CRITICAL FAILURE: CASCADING FALLBACK HANDLERS DETECTED\n"
                            f"Fallback count: {fallback_count}\n"
                            f"Cascade patterns: {cascade_patterns}\n"
                            f"BUSINESS IMPACT: Multiple mock services masking system failures.\n"
                            f"System should fail cleanly, not create fallback cascade."
                        )
                    
                    # CRITICAL FAILURE: Any fallback patterns during multiple service failure
                    if fallback_count > 0:
                        raise AssertionError(
                            f"🚨 CRITICAL FAILURE: Fallback handlers during multiple service failures\n"
                            f"Patterns detected: {cascade_patterns}\n"
                            f"BUSINESS IMPACT: Mock responses masking critical system failure.\n"
                            f"Users should get clear error, not degraded mock functionality."
                        )
                    
                    logger.warning("⚠️ System somehow processed request despite all services disabled - unusual but validating response")
                    
                    # If system somehow processed successfully, validate it's authentic
                    completed_events = [e for e in events if e.get('type') == 'agent_completed']
                    if completed_events:
                        final_response = completed_events[0].get('content', '')
                        self.validator.assert_has_business_value(
                            final_response, 
                            context="response despite multiple service failures"
                        )
                        logger.info("✅ Response contains authentic business value despite service issues")
                
                except AssertionError as e:
                    if "CASCADING FALLBACK" in str(e) or "FALLBACK HANDLERS" in str(e):
                        # Critical failure - cascading fallbacks detected
                        raise e
                    else:
                        # Expected behavior - system failed appropriately
                        logger.success(f"✅ EXPECTED BEHAVIOR: System failed appropriately with multiple service failures: {e}")
                        return
                
                except Exception as e:
                    error_msg = str(e)
                    if "cascade" in error_msg.lower() or "multiple.*fallback" in error_msg.lower():
                        raise AssertionError(f"🚨 CASCADE FALLBACK DETECTED: {error_msg}")
                    else:
                        logger.success(f"✅ EXPECTED BEHAVIOR: System failed cleanly with multiple service failures: {error_msg}")
                        return
            
            except Exception as e:
                error_msg = str(e)
                if "fallback" in error_msg.lower():
                    raise AssertionError(f"🚨 FALLBACK DETECTED during send with multiple service failures: {error_msg}")
                else:
                    logger.success(f"✅ EXPECTED BEHAVIOR: Send failed appropriately with multiple service failures: {error_msg}")
                    return
        
        except Exception as e:
            # Connection failed with multiple services down - this is expected
            error_msg = str(e)
            if "fallback" in error_msg.lower() or "cascade" in error_msg.lower():
                raise AssertionError(f"🚨 CASCADE FALLBACK in connection: {error_msg}")
            else:
                logger.success(f"✅ EXPECTED BEHAVIOR: Connection failed cleanly with multiple service failures: {error_msg}")
                return
        
        logger.success("✅ PASSED: No cascading fallback handlers created during multiple service failures")


if __name__ == "__main__":
    """
    Run the fallback handler degradation prevention test suite.
    
    This can be run directly or via pytest:
    
    Direct execution:
        python tests/mission_critical/test_fallback_handler_degradation_prevention.py
    
    Via pytest:
        pytest tests/mission_critical/test_fallback_handler_degradation_prevention.py -v
        
    Via unified test runner:
        python tests/unified_test_runner.py --test-file tests/mission_critical/test_fallback_handler_degradation_prevention.py --real-services
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        # Run via pytest
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        # Direct execution
        print("🧪 MISSION CRITICAL: Fallback Handler Degradation Prevention Test Suite")
        print("📋 This suite tests for fallback handler anti-patterns that degrade business value")
        print("⚠️  Tests are designed to FAIL HARD when fallback handlers are detected")
        print("🚀 Starting test execution...")
        
        # Run pytest with specific markers
        exit_code = pytest.main([
            __file__,
            "-v",
            "-x",  # Stop on first failure
            "--tb=short",
            "-m", "mission_critical",
            "--durations=10"
        ])
        
        if exit_code == 0:
            print("✅ ALL TESTS PASSED: No fallback handler degradation detected")
        else:
            print("🚨 TEST FAILURES: Fallback handler degradation detected - BLOCKS DEPLOYMENT")
            
        sys.exit(exit_code)