#!/usr/bin/env python3

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
E2E Golden Path Real Agent Validation

MISSION CRITICAL: This test validates that the golden path user flow ONLY uses real agents
and NEVER creates fallback handlers that degrade business value.

PURPOSE: Expose the "dumb fallback handler" anti-pattern by testing complete user flows
and ensuring only authentic AI agent responses are delivered to users.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure golden path delivers only authentic AI agent value
- Value Impact: Prevent degraded mock responses from reaching paying customers
- Strategic Impact: Protect $500K+ ARR by ensuring real AI value delivery

CRITICAL: This test must FAIL if any fallback handlers are used in the golden path.
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
import re

# CRITICAL: Add project root to Python path for imports  
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import websockets
from loguru import logger

# Import SSOT authentication - MANDATORY for E2E tests per CLAUDE.md
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper, 
    create_authenticated_user_context
)

# Import environment and types
from shared.isolated_environment import get_env
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

# Import BusinessValueValidator from mission critical test
from tests.mission_critical.test_fallback_handler_degradation_prevention import BusinessValueValidator


class GoldenPathTestClient:
    """
    Test client for golden path validation with fallback detection.
    
    This client monitors all WebSocket communications for fallback patterns
    and ensures only real agent responses are delivered.
    """
    
    def __init__(self, auth_helper: E2EWebSocketAuthHelper, validator: BusinessValueValidator):
        """Initialize golden path test client."""
        self.auth_helper = auth_helper
        self.validator = validator
        self.websocket = None
        self.events_received: List[Dict[str, Any]] = []
        self.start_time = None
        self.end_time = None
        
    async def connect(self, timeout: float = 15.0) -> None:
        """Connect to WebSocket with authentication."""
        logger.info("🔌 Golden Path: Connecting WebSocket for real agent validation")
        self.websocket = await self.auth_helper.connect_authenticated_websocket(timeout=timeout)
        self.start_time = time.time()
        logger.info("✅ Golden Path: WebSocket connected successfully")
    
    async def send_golden_path_request(self, request_content: str) -> None:
        """Send golden path business request that should trigger real agents."""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")
            
        request_message = {
            "type": "user_message",
            "content": request_content,
            "thread_id": f"golden-path-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.websocket.send(json.dumps(request_message))
        logger.info(f"📤 Golden Path: Sent business request: '{request_content[:50]}...'")
    
    async def receive_and_validate_events(self, timeout: float = 60.0, expected_events: int = 5) -> List[Dict[str, Any]]:
        """
        Receive WebSocket events and validate for fallback patterns.
        
        CRITICAL: This method fails hard if any fallback patterns are detected.
        """
        self.events_received = []
        end_time = time.time() + timeout
        
        logger.info(f"📨 Golden Path: Waiting for {expected_events} real agent events (timeout: {timeout}s)")
        
        while time.time() < end_time and len(self.events_received) < expected_events:
            try:
                # Receive event with short timeout for responsive checking
                message_str = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                event = json.loads(message_str)
                self.events_received.append(event)
                
                # CRITICAL: Validate event immediately for fallback patterns
                event_content = json.dumps(event)
                has_fallback, fallback_patterns = self.validator.validate_response_for_fallback_patterns(event_content)
                
                if has_fallback:
                    raise AssertionError(
                        f"🚨 GOLDEN PATH FAILURE: FALLBACK PATTERNS DETECTED\n"
                        f"Event type: {event.get('type', 'unknown')}\n"
                        f"Fallback patterns: {fallback_patterns}\n"
                        f"Event content: {event_content[:200]}...\n"
                        f"BUSINESS IMPACT: User receiving mock response instead of real AI value"
                    )
                
                logger.info(f"✅ Golden Path: Event {len(self.events_received)}/{expected_events} - {event.get('type', 'unknown')} (real agent)")
                
            except asyncio.TimeoutError:
                if len(self.events_received) >= expected_events:
                    break
                continue
            except websockets.ConnectionClosed:
                logger.error("🚨 Golden Path: WebSocket connection closed unexpectedly")
                break
        
        self.end_time = time.time()
        
        if len(self.events_received) < expected_events:
            raise AssertionError(
                f"🚨 GOLDEN PATH FAILURE: INSUFFICIENT EVENTS\n"
                f"Expected: {expected_events}, Received: {len(self.events_received)}\n"
                f"Events received: {[e.get('type') for e in self.events_received]}\n"
                f"BUSINESS IMPACT: Incomplete agent workflow - users not receiving full value"
            )
        
        return self.events_received
    
    def validate_golden_path_flow(self) -> None:
        """
        Validate that the complete golden path flow was executed with real agents.
        
        CRITICAL: This validates the 5 essential WebSocket events for business value.
        """
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        received_event_types = [event.get('type') for event in self.events_received]
        
        missing_events = [event_type for event_type in required_events if event_type not in received_event_types]
        
        if missing_events:
            raise AssertionError(
                f"🚨 GOLDEN PATH FAILURE: MISSING CRITICAL EVENTS\n"
                f"Missing: {missing_events}\n"
                f"Received: {received_event_types}\n"
                f"BUSINESS IMPACT: Incomplete agent workflow reduces user value"
            )
        
        # Validate processing duration indicates real work
        processing_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        if processing_duration < 2.0:
            raise AssertionError(
                f"🚨 GOLDEN PATH FAILURE: SUSPICIOUSLY FAST PROCESSING\n"
                f"Duration: {processing_duration:.2f}s (< 2.0s minimum for real agent work)\n"
                f"BUSINESS IMPACT: Fast processing indicates mock/template responses"
            )
        
        logger.info(f"✅ Golden Path: Real agent processing duration: {processing_duration:.2f}s")
    
    def validate_final_response_business_value(self) -> None:
        """
        Validate the final agent response contains authentic business value.
        
        CRITICAL: This ensures users receive real AI insights, not mock content.
        """
        completed_events = [e for e in self.events_received if e.get('type') == 'agent_completed']
        
        if not completed_events:
            raise AssertionError(
                f"🚨 GOLDEN PATH FAILURE: NO COMPLETION EVENT\n"
                f"BUSINESS IMPACT: Users not receiving final AI agent results"
            )
        
        final_response = completed_events[0].get('content', '')
        
        if len(final_response) < 50:
            raise AssertionError(
                f"🚨 GOLDEN PATH FAILURE: INSUFFICIENT RESPONSE LENGTH\n"
                f"Length: {len(final_response)} chars (< 50 minimum)\n"
                f"Response: '{final_response}'\n"
                f"BUSINESS IMPACT: Short response indicates template/mock content"
            )
        
        # Validate business value patterns
        has_business_value, business_patterns = self.validator.validate_response_for_business_value(final_response)
        
        if not has_business_value:
            raise AssertionError(
                f"🚨 GOLDEN PATH FAILURE: NO BUSINESS VALUE DETECTED\n"
                f"Response: '{final_response[:200]}...'\n"
                f"Business patterns found: {business_patterns}\n"
                f"BUSINESS IMPACT: Users receiving response without actionable insights"
            )
        
        # Final check for any fallback patterns in response
        has_fallback, fallback_patterns = self.validator.validate_response_for_fallback_patterns(final_response)
        
        if has_fallback:
            raise AssertionError(
                f"🚨 GOLDEN PATH FAILURE: FALLBACK PATTERNS IN FINAL RESPONSE\n"
                f"Patterns: {fallback_patterns}\n"
                f"Response: '{final_response[:200]}...'\n"
                f"BUSINESS IMPACT: Mock content delivered to paying customer"
            )
        
        logger.info(f"✅ Golden Path: Final response contains authentic business value ({len(final_response)} chars)")
    
    async def disconnect(self) -> None:
        """Disconnect WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None


@pytest.mark.e2e
@pytest.mark.mission_critical  
@pytest.mark.real_services
@pytest.mark.business_value_validation
@pytest.mark.fallback_prevention
class TestGoldenPathRealAgentValidation:
    """
    E2E Golden Path Real Agent Validation Test Suite
    
    CRITICAL: These tests ensure the golden path user flow NEVER uses fallback handlers
    and always delivers authentic AI agent business value to users.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up golden path test environment with real services."""
        # Initialize environment
        self.env = get_env()
        environment = self.env.get("TEST_ENV", "test")
        
        # Initialize auth helper with proper environment
        self.auth_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Initialize business value validator
        self.validator = BusinessValueValidator()
        
        # Initialize golden path test client
        self.golden_path_client = GoldenPathTestClient(self.auth_helper, self.validator)
        
        yield
        
        # Cleanup: Disconnect WebSocket
        asyncio.run(self.golden_path_client.disconnect())
    
    async def test_golden_path_cost_optimization_real_agents_only(self):
        """
        CRITICAL TEST: Golden path cost optimization flow uses only real agents.
        
        This test validates the primary revenue-generating user flow:
        User Request → Real Agent Processing → Business Value Delivery
        
        MUST FAIL if any fallback handlers are created during this flow.
        
        SUCCESS CRITERIA:
        - WebSocket connection established with real authentication
        - All 5 critical WebSocket events received from real agents
        - Processing duration indicates real AI work (≥ 2 seconds)
        - Final response contains authentic business insights
        - ZERO fallback patterns detected throughout flow
        
        FAILURE CONDITIONS:
        - Any fallback handler creation detected
        - Mock/template responses delivered to user
        - Missing critical WebSocket events
        - Suspiciously fast processing (< 2 seconds)
        """
        logger.info("🧪 GOLDEN PATH TEST: Cost optimization with real agents only")
        
        # Connect with real authentication
        await self.golden_path_client.connect(timeout=15.0)
        
        # Send primary business value request
        cost_optimization_request = (
            "Analyze my cloud infrastructure costs and provide detailed optimization recommendations "
            "with specific actionable insights for reducing spending while maintaining performance. "
            "Include cost breakdown analysis and identify the top 3 optimization opportunities."
        )
        
        await self.golden_path_client.send_golden_path_request(cost_optimization_request)
        
        # Receive and validate all events for fallback patterns
        events = await self.golden_path_client.receive_and_validate_events(timeout=60.0, expected_events=5)
        
        # Validate complete golden path flow
        self.golden_path_client.validate_golden_path_flow()
        
        # Validate final response business value
        self.golden_path_client.validate_final_response_business_value()
        
        logger.success("✅ GOLDEN PATH PASSED: Cost optimization delivered via real agents only")
    
    async def test_golden_path_data_analysis_real_agents_only(self):
        """
        CRITICAL TEST: Golden path data analysis flow uses only real agents.
        
        Tests the secondary high-value user flow for data analysis requests.
        MUST ensure no fallback handlers are created for analytical workloads.
        
        SUCCESS CRITERIA:
        - Complex analytical request processed by real agents
        - All WebSocket events delivered without fallback patterns
        - Response contains analytical insights and recommendations
        - Processing duration indicates real analytical work
        """
        logger.info("🧪 GOLDEN PATH TEST: Data analysis with real agents only")
        
        await self.golden_path_client.connect(timeout=15.0)
        
        # Send analytical business request
        analysis_request = (
            "Perform comprehensive analysis of my business data to identify performance trends, "
            "growth opportunities, and operational inefficiencies. Provide data-driven insights "
            "with specific recommendations for improving business outcomes."
        )
        
        await self.golden_path_client.send_golden_path_request(analysis_request)
        
        # Validate real agent processing
        events = await self.golden_path_client.receive_and_validate_events(timeout=60.0, expected_events=5)
        self.golden_path_client.validate_golden_path_flow()
        self.golden_path_client.validate_final_response_business_value()
        
        logger.success("✅ GOLDEN PATH PASSED: Data analysis delivered via real agents only")
    
    async def test_golden_path_rapid_succession_requests_no_fallbacks(self):
        """
        CRITICAL TEST: Multiple rapid golden path requests use only real agents.
        
        Tests the system under load to ensure fallback handlers are never created
        even when processing multiple high-value requests in rapid succession.
        
        SUCCESS CRITERIA:
        - Multiple business requests processed successfully
        - Each request handled by real agents (no fallbacks)
        - All requests deliver authentic business value
        - System maintains real agent quality under load
        """
        logger.info("🧪 GOLDEN PATH TEST: Rapid succession requests with real agents only")
        
        await self.golden_path_client.connect(timeout=15.0)
        
        requests = [
            "Optimize my infrastructure costs with detailed recommendations",
            "Analyze performance metrics and identify improvement opportunities", 
            "Provide strategic insights for business growth acceleration"
        ]
        
        for i, request in enumerate(requests, 1):
            logger.info(f"📤 Golden Path: Processing request {i}/{len(requests)}")
            
            await self.golden_path_client.send_golden_path_request(request)
            
            # Validate each request uses real agents
            events = await self.golden_path_client.receive_and_validate_events(timeout=45.0, expected_events=5)
            self.golden_path_client.validate_golden_path_flow()
            self.golden_path_client.validate_final_response_business_value()
            
            # Brief pause between requests
            await asyncio.sleep(1.0)
        
        logger.success("✅ GOLDEN PATH PASSED: All rapid succession requests used real agents only")


if __name__ == "__main__":
    """
    Run the E2E Golden Path Real Agent Validation test suite.
    
    This can be run directly or via pytest:
    
    Direct execution:
        python tests/e2e/test_golden_path_real_agent_validation.py
    
    Via pytest:
        pytest tests/e2e/test_golden_path_real_agent_validation.py -v
        
    Via unified test runner:
        python tests/unified_test_runner.py --test-file tests/e2e/test_golden_path_real_agent_validation.py --real-services
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        # Run via pytest
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        # Direct execution
        print("🧪 E2E: Golden Path Real Agent Validation Test Suite")
        print("📋 This suite ensures golden path flows use only real agents")
        print("⚠️  Tests are designed to FAIL HARD when fallback handlers are detected")
        print("🚀 Starting test execution...")
        
        # Run pytest with specific markers
        exit_code = pytest.main([
            __file__,
            "-v",
            "-x",  # Stop on first failure
            "--tb=short",
            "-m", "e2e and business_value_validation",
            "--durations=10"
        ])
        
        if exit_code == 0:
            print("✅ ALL TESTS PASSED: Golden path uses real agents only")
        else:
            print("🚨 TEST FAILURES: Fallback handlers detected in golden path - BLOCKS DEPLOYMENT")
            
        sys.exit(exit_code)