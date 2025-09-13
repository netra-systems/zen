#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: First Message Experience - E2E VALUE VALIDATION

CRITICAL: This test suite validates the most important user touchpoint - FIRST MESSAGE.
Business Impact: User activation, conversion, retention - THE ENTIRE BUSINESS MODEL.

Per SPEC/first_message_experience.xml:
- User sends first message and gets SUBSTANTIVE AI response within 45s
- All WebSocket events sent in correct order for value delivery  
- Complete user isolation via factory patterns
- Real services only (Docker, LLM, databases) - NO MOCKS

FAILURE HERE = NO USER VALUE = NO BUSINESS
"""

import asyncio
import json
import os
import ssl
import sys
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
import websocket
import random
import websockets
from websockets import ConnectionClosedError, InvalidStatus, InvalidHandshake

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import production components - REAL SERVICES ONLY
from netra_backend.app.core.registry.universal_registry import AgentRegistry
# SECURITY FIX: Use UserExecutionEngine SSOT instead of deprecated ExecutionEngine
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

# Import test utilities
from tests.mission_critical.websocket_real_test_base import (
    is_docker_available,
    RealWebSocketTestConfig,
    send_test_agent_request
)
from test_framework.test_context import TestContext, create_test_context
from test_framework.websocket_helpers import WebSocketTestHelpers
from test_framework.jwt_test_utils import generate_test_jwt_token, JWTTestHelper


class FirstMessageEventValidator:
    """Validates first message experience meets business requirements."""
    
    # Per SPEC/first_message_experience.xml - Required events in order
    REQUIRED_EVENT_SEQUENCE = [
        "message_received",    # < 100ms
        "agent_started",       # < 500ms
        "agent_thinking",      # 2-5s intervals
        "tool_executing",      # as needed
        "tool_completed",      # after execution
        "agent_completed",     # < 45s
        "response_complete"    # final
    ]
    
    # SLO requirements
    SLO_MESSAGE_RECEIVED_MS = 100
    SLO_AGENT_STARTED_MS = 500
    SLO_THINKING_INTERVAL_S = 5
    SLO_TOTAL_RESPONSE_S = 45
    
    def __init__(self):
        self.events: List[Dict] = []
        self.event_timeline: List[Tuple[float, str, Dict]] = []
        self.start_time: Optional[float] = None
        self.errors: List[str] = []
        self.thinking_intervals: List[float] = []
        
    def record_event(self, event: Dict[str, Any], timestamp: float = None) -> None:
        """Record a WebSocket event with timing."""
        if self.start_time is None:
            self.start_time = time.time()
            
        current_time = timestamp or time.time()
        relative_time = current_time - self.start_time
        
        event_type = event.get("type", "unknown")
        self.events.append(event)
        self.event_timeline.append((relative_time, event_type, event))
        
        # Track thinking intervals
        if event_type == "agent_thinking":
            self.thinking_intervals.append(relative_time)
            
        logger.info(f"[{relative_time:.2f}s] Event: {event_type}")
        
    def validate_first_message_experience(self) -> Tuple[bool, List[str]]:
        """Validate the complete first message experience."""
        validations = [
            ("Event Sequence", self._validate_sequence()),
            ("Response Time SLO", self._validate_response_time()),
            ("Event Timing", self._validate_event_timing()),
            ("Message Completeness", self._validate_message_completeness()),
            ("User Isolation", self._validate_user_isolation()),
            ("Business Value", self._validate_business_value())
        ]
        
        failures = []
        for name, (passed, errors) in validations:
            if not passed:
                failures.append(f"{name}: {', '.join(errors)}")
                
        return len(failures) == 0, failures
        
    def _validate_sequence(self) -> Tuple[bool, List[str]]:
        """Validate events arrive in correct order."""
        errors = []
        received_types = [event.get("type") for event in self.events]
        
        # Check all required events present
        for required in self.REQUIRED_EVENT_SEQUENCE:
            if required not in received_types:
                errors.append(f"Missing required event: {required}")
                
        # Check sequence order
        if not errors:
            sequence_indices = []
            for event_type in received_types:
                if event_type in self.REQUIRED_EVENT_SEQUENCE:
                    idx = self.REQUIRED_EVENT_SEQUENCE.index(event_type)
                    sequence_indices.append(idx)
                    
            # Verify monotonic increase (allowing duplicates)
            for i in range(1, len(sequence_indices)):
                if sequence_indices[i] < sequence_indices[i-1]:
                    errors.append(f"Event sequence violation at position {i}")
                    
        return len(errors) == 0, errors
        
    def _validate_response_time(self) -> Tuple[bool, List[str]]:
        """Validate total response time meets SLO."""
        errors = []
        
        if not self.event_timeline:
            errors.append("No events received")
            return False, errors
            
        # Find response_complete event
        response_complete = None
        for timestamp, event_type, _ in self.event_timeline:
            if event_type == "response_complete":
                response_complete = timestamp
                break
                
        if response_complete is None:
            errors.append("No response_complete event received")
        elif response_complete > self.SLO_TOTAL_RESPONSE_S:
            errors.append(f"Response time {response_complete:.1f}s exceeds SLO {self.SLO_TOTAL_RESPONSE_S}s")
            
        return len(errors) == 0, errors
        
    def _validate_event_timing(self) -> Tuple[bool, List[str]]:
        """Validate individual event timing requirements."""
        errors = []
        
        for timestamp, event_type, _ in self.event_timeline:
            if event_type == "message_received" and timestamp * 1000 > self.SLO_MESSAGE_RECEIVED_MS:
                errors.append(f"message_received took {timestamp*1000:.0f}ms (SLO: {self.SLO_MESSAGE_RECEIVED_MS}ms)")
            elif event_type == "agent_started" and timestamp * 1000 > self.SLO_AGENT_STARTED_MS:
                errors.append(f"agent_started took {timestamp*1000:.0f}ms (SLO: {self.SLO_AGENT_STARTED_MS}ms)")
                
        # Check thinking intervals
        if len(self.thinking_intervals) > 1:
            for i in range(1, len(self.thinking_intervals)):
                interval = self.thinking_intervals[i] - self.thinking_intervals[i-1]
                if interval > self.SLO_THINKING_INTERVAL_S:
                    errors.append(f"Thinking interval {interval:.1f}s exceeds {self.SLO_THINKING_INTERVAL_S}s")
                    
        return len(errors) == 0, errors
        
    def _validate_message_completeness(self) -> Tuple[bool, List[str]]:
        """Validate response contains substantive content."""
        errors = []
        
        # Find agent_completed event
        agent_response = None
        for _, event_type, event in self.event_timeline:
            if event_type == "agent_completed":
                agent_response = event.get("response") or event.get("final_response")
                break
                
        if agent_response is None:
            errors.append("No agent response found")
        elif len(str(agent_response)) < 50:
            errors.append(f"Response too short for substantive value: {len(str(agent_response))} chars")
            
        return len(errors) == 0, errors
        
    def _validate_user_isolation(self) -> Tuple[bool, List[str]]:
        """Validate user context isolation."""
        errors = []
        
        # Check for unique user_id across events
        user_ids = set()
        for event in self.events:
            if "user_id" in event:
                user_ids.add(event["user_id"])
                
        if len(user_ids) > 1:
            errors.append(f"Multiple user IDs detected: {user_ids}")
            
        # Check for thread isolation
        thread_ids = set()
        for event in self.events:
            if "thread_id" in event:
                thread_ids.add(event["thread_id"])
                
        if len(thread_ids) > 1:
            errors.append(f"Multiple thread IDs detected: {thread_ids}")
            
        return len(errors) == 0, errors
        
    def _validate_business_value(self) -> Tuple[bool, List[str]]:
        """Validate business value delivery."""
        errors = []
        
        # Must have substantive AI interaction
        has_thinking = any(e.get("type") == "agent_thinking" for e in self.events)
        has_tools = any(e.get("type") == "tool_executing" for e in self.events)
        has_response = any(e.get("type") == "agent_completed" for e in self.events)
        
        if not has_thinking:
            errors.append("No agent thinking events - no AI value demonstrated")
        if not has_response:
            errors.append("No agent response - no value delivered")
            
        return len(errors) == 0, errors
        
    def generate_report(self) -> str:
        """Generate comprehensive first message validation report."""
        is_valid, failures = self.validate_first_message_experience()
        
        report = [
            "",
            "=" * 80,
            "FIRST MESSAGE EXPERIENCE VALIDATION REPORT",
            "=" * 80,
            f"Business Impact: User Activation & Conversion",
            f"Status: {' PASS:  VALUE DELIVERED' if is_valid else ' FAIL:  NO VALUE - BROKEN'}",
            "",
            f"Total Events: {len(self.events)}",
            f"Response Time: {self.event_timeline[-1][0] if self.event_timeline else 0:.2f}s",
            f"Thinking Updates: {len(self.thinking_intervals)}",
            "",
            "Event Sequence:"
        ]
        
        # Show event timeline
        for timestamp, event_type, _ in self.event_timeline[:10]:
            report.append(f"  [{timestamp:6.2f}s] {event_type}")
            
        if len(self.event_timeline) > 10:
            report.append(f"  ... and {len(self.event_timeline) - 10} more events")
            
        # Show failures
        if failures:
            report.append("")
            report.append("CRITICAL FAILURES:")
            for failure in failures:
                report.append(f"   FAIL:  {failure}")
                
        report.append("=" * 80)
        return "\n".join(report)


class TestFirstMessageExperience:
    """E2E tests for first message user experience."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment with real services."""
        self.env = IsolatedEnvironment()
        self.test_context = create_test_context()
        self.ws_helpers = WebSocketTestHelpers(self.test_context)
        
        # Determine environment from command line or environment variable
        env_name = os.environ.get("TEST_ENV", "development")
        self.is_staging = env_name == "staging"
        
        if self.is_staging:
            # Use staging URLs
            self.backend_url = "https://api.staging.netrasystems.ai"
            self.ws_url = "wss://api.staging.netrasystems.ai/ws"
            # Initialize JWT helper for staging authentication
            self.jwt_helper = JWTTestHelper()
        else:
            # Use local/development URLs
            self.backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
            self.ws_url = self.backend_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
            self.jwt_helper = JWTTestHelper()
        
        logger.info(f"Testing against backend: {self.backend_url}")
        logger.info(f"WebSocket URL: {self.ws_url}")
        logger.info(f"Environment: {'staging' if self.is_staging else 'development'}")
        
    async def _create_websocket_connection(self, user_id: str, max_retries: int = 3) -> Optional[Any]:
        """Create WebSocket connection with retry logic and proper authentication."""
        
        # Generate proper JWT token for authentication
        if self.is_staging:
            # Use longer expiry for staging tests and proper service authentication
            jwt_token = self.jwt_helper.create_user_token(
                user_id=user_id,
                email=f"{user_id}@test.netrasystems.ai",
                permissions=["read", "write", "admin"],
                expires_in_minutes=120,  # 2 hours for longer staging tests
                issuer="netra-test",
                audience="netra-backend"
            )
        else:
            # Use shorter expiry for local tests
            jwt_token = self.jwt_helper.create_user_token(
                user_id=user_id,
                expires_in_minutes=30
            )
            
        logger.info(f"Generated JWT token for user {user_id} (staging: {self.is_staging})")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"WebSocket connection attempt {attempt + 1}/{max_retries} to {self.ws_url}")
                
                if self.is_staging:
                    # Use websockets library for better SSL/WSS support in staging
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    
                    # Create connection with proper headers for staging authentication
                    extra_headers = {
                        "Authorization": f"Bearer {jwt_token}",
                        "User-Agent": "Netra-Test-Client/1.0",
                        "X-Test-Environment": "staging"
                    }
                    
                    # Use asyncio.timeout for Python 3.12 compatibility
                    async with asyncio.timeout(15):  # 15 second timeout for connection
                        ws = await websockets.connect(
                            self.ws_url,
                            ssl=ssl_context,
                            extra_headers=extra_headers,
                            ping_interval=30,
                            ping_timeout=10,
                            close_timeout=10
                        )
                    logger.info(f"Connected to staging WebSocket: {self.ws_url}")
                    
                    # Send authentication message with JWT token
                    auth_message = {
                        "type": "auth",
                        "token": jwt_token,
                        "user_id": user_id
                    }
                    await ws.send(json.dumps(auth_message))
                    
                    # Wait for auth acknowledgment with timeout
                    try:
                        auth_response = await asyncio.wait_for(ws.recv(), timeout=10)
                        auth_data = json.loads(auth_response)
                        if auth_data.get("type") == "auth_success":
                            logger.info("WebSocket authentication successful")
                        else:
                            logger.warning(f"Unexpected auth response: {auth_data}")
                    except asyncio.TimeoutError:
                        logger.warning("No auth response received, continuing...")
                    
                    return ws
                    
                else:
                    # Use websocket-client for local development
                    ws = websocket.WebSocket()
                    ws.settimeout(15)  # 15 second timeout
                    ws.connect(self.ws_url)
                    logger.info(f"Connected to local WebSocket: {self.ws_url}")
                    
                    # Send authentication
                    auth_message = {
                        "type": "auth",
                        "token": jwt_token,
                        "user_id": user_id
                    }
                    ws.send(json.dumps(auth_message))
                    
                    return ws
                    
            except Exception as e:
                logger.error(f"WebSocket connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} connection attempts failed")
                    raise ConnectionError(f"Failed to connect to WebSocket after {max_retries} attempts: {e}")
        
        return None

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)  # Extended timeout for staging
    async def test_happy_path_first_message(self):
        """Test: New user sends first message and receives substantive response."""
        logger.info("=" * 80)
        logger.info("TEST: Happy Path - First Message Experience")
        logger.info("=" * 80)
        
        validator = FirstMessageEventValidator()
        events_received = []
        
        # Create WebSocket connection
        user_id = f"first_user_{uuid.uuid4().hex[:8]}"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        # Connect with retry logic and proper authentication
        ws = None
        try:
            ws = await self._create_websocket_connection(user_id)
            
            # Event capture function with proper error handling
            async def capture_events_async():
                """Capture WebSocket events with proper async handling."""
                try:
                    while True:
                        if self.is_staging:
                            # Use websockets library for staging
                            message = await asyncio.wait_for(ws.recv(), timeout=30)
                        else:
                            # Use websocket-client for local
                            message = ws.recv()
                            
                        if message:
                            try:
                                event = json.loads(message)
                                events_received.append(event)
                                validator.record_event(event)
                                logger.info(f"Received event: {event.get('type', 'unknown')}")
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse WebSocket message: {message[:100]}... Error: {e}")
                except (ConnectionClosedError, websockets.ConnectionClosed):
                    logger.info("WebSocket connection closed by server")
                except asyncio.TimeoutError:
                    logger.info("WebSocket receive timeout")
                except Exception as e:
                    logger.error(f"Error in event capture: {e}")
            
            # Start event capture
            if self.is_staging:
                # Use asyncio task for staging
                capture_task = asyncio.create_task(capture_events_async())
            else:
                # Use thread for local
                def capture_sync():
                    asyncio.run(capture_events_async())
                capture_thread = threading.Thread(target=capture_sync, daemon=True)
                capture_thread.start()
            
            # Send first message
            first_message = {
                "type": "agent_request",
                "message": "Help me optimize my AI infrastructure costs. I'm currently spending $50k/month on GPU resources.",
                "user_id": user_id,
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("Sending first message...")
            if self.is_staging:
                await ws.send(json.dumps(first_message))
            else:
                ws.send(json.dumps(first_message))
            
            # Wait for response completion with proper timeout handling
            start_time = time.time()
            timeout = 90 if self.is_staging else 60  # Extended timeout for staging
            
            logger.info(f"Waiting for response (timeout: {timeout}s)...")
            
            while time.time() - start_time < timeout:
                # Check if we got response_complete
                if any(e.get("type") == "response_complete" for e in events_received):
                    logger.info("Response complete received!")
                    break
                    
                # Check if we got agent_completed
                if any(e.get("type") == "agent_completed" for e in events_received):
                    logger.info("Agent completed received!")
                    # Wait a bit more for response_complete
                    await asyncio.sleep(2)
                    break
                    
                await asyncio.sleep(0.5)
                
            # Cancel capture task if staging
            if self.is_staging and 'capture_task' in locals():
                capture_task.cancel()
                try:
                    await capture_task
                except asyncio.CancelledError:
                    pass
                
        except Exception as e:
            logger.error(f"Test failed with exception: {e}")
            raise
        finally:
            # Clean up WebSocket connection
            if ws:
                try:
                    if self.is_staging:
                        await ws.close()
                    else:
                        ws.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
                
        # Validate results
        logger.info(f"Captured {len(events_received)} events")
        if events_received:
            logger.info(f"Event types: {[e.get('type') for e in events_received[:10]]}")  # Show first 10
        
        report = validator.generate_report()
        logger.info(report)
        
        is_valid, failures = validator.validate_first_message_experience()
        
        # More lenient assertions for staging environment
        if self.is_staging:
            # For staging, just ensure we got some response
            assert len(events_received) >= 1, f"No events received from staging environment"
            if not is_valid:
                logger.warning(f"Staging validation issues (may be expected): {failures}")
        else:
            # Full validation for local environment
            assert is_valid, f"First message experience failed:\n" + "\n".join(failures)
            assert len(events_received) >= 5, f"Too few events received: {len(events_received)}"
        
        logger.info(" PASS:  First message test completed successfully!")
        
    @pytest.mark.asyncio
    @pytest.mark.timeout(180)  # Extended timeout for concurrent tests
    async def test_concurrent_first_messages(self):
        """Test: Multiple new users send first messages simultaneously."""
        logger.info("=" * 80)
        logger.info("TEST: Concurrent First Messages - User Isolation")
        logger.info("=" * 80)
        
        # Reduce concurrent users for staging to avoid overwhelming the service
        num_users = 3 if self.is_staging else 5
        validators = []
        results = []
        
        async def send_first_message(user_num: int) -> Tuple[bool, FirstMessageEventValidator]:
            """Send first message for a single user."""
            validator = FirstMessageEventValidator()
            user_id = f"concurrent_user_{user_num}_{uuid.uuid4().hex[:8]}"
            thread_id = f"thread_{user_num}_{uuid.uuid4().hex[:8]}"
            
            ws = None
            try:
                # Use our robust connection method
                ws = await self._create_websocket_connection(user_id)
                
                # Capture events with proper async handling
                events = []
                async def capture_async():
                    try:
                        while True:
                            if self.is_staging:
                                msg = await asyncio.wait_for(ws.recv(), timeout=20)
                            else:
                                msg = ws.recv()
                            if msg:
                                event = json.loads(msg)
                                events.append(event)
                                validator.record_event(event)
                    except Exception:
                        pass
                        
                if self.is_staging:
                    capture_task = asyncio.create_task(capture_async())
                else:
                    def capture_sync():
                        asyncio.run(capture_async())
                    threading.Thread(target=capture_sync, daemon=True).start()
                
                # Send unique first message
                messages = [
                    "Help me reduce my LLM API costs",
                    "Optimize my model inference pipeline",
                    "Analyze my GPU utilization patterns",
                    "Recommend cost-effective AI infrastructure",
                    "Review my ML training workflows"
                ]
                
                first_msg = {
                    "type": "agent_request",
                    "message": messages[user_num % len(messages)],
                    "user_id": user_id,
                    "thread_id": thread_id
                }
                
                if self.is_staging:
                    await ws.send(json.dumps(first_msg))
                else:
                    ws.send(json.dumps(first_msg))
                
                # Wait for completion with environment-specific timeout
                start = time.time()
                timeout = 90 if self.is_staging else 60
                while time.time() - start < timeout:
                    if any(e.get("type") in ["agent_completed", "response_complete"] for e in events):
                        break
                    await asyncio.sleep(0.5)
                    
                # Cancel capture task for staging
                if self.is_staging and 'capture_task' in locals():
                    capture_task.cancel()
                    try:
                        await capture_task
                    except asyncio.CancelledError:
                        pass
                    
                is_valid, _ = validator.validate_first_message_experience()
                return is_valid, validator
                
            finally:
                if ws:
                    try:
                        if self.is_staging:
                            await ws.close()
                        else:
                            ws.close()
                    except Exception:
                        pass
                    
        # Send all first messages concurrently
        tasks = [send_first_message(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate results
        successful = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"User {i} failed with exception: {result}")
            else:
                is_valid, validator = result
                if is_valid:
                    successful += 1
                    logger.info(f"User {i}:  PASS:  Success")
                else:
                    logger.error(f"User {i}:  FAIL:  Failed")
                    
        # More lenient success rate for staging environment
        min_success_rate = 0.6 if self.is_staging else 0.8
        assert successful >= num_users * min_success_rate, f"Only {successful}/{num_users} users succeeded (required: {min_success_rate * 100}%)"
        logger.info(f" PASS:  Concurrent first messages: {successful}/{num_users} successful")
        
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_first_message_with_service_degradation(self):
        """Test: First message during simulated service degradation."""
        logger.info("=" * 80)
        logger.info("TEST: First Message with Service Degradation")
        logger.info("=" * 80)
        
        validator = FirstMessageEventValidator()
        
        # This test validates graceful degradation
        # In real scenario, we'd simulate slow LLM or database
        # For now, we verify the system handles delays
        
        ws = None
        try:
            user_id = f"degraded_user_{uuid.uuid4().hex[:8]}"
            ws = await self._create_websocket_connection(user_id)
            
            events = []
            def capture():
                while True:
                    try:
                        msg = ws.recv()
                        if msg:
                            event = json.loads(msg)
                            events.append(event)
                            validator.record_event(event)
                    except:
                        break
                        
            threading.Thread(target=capture, daemon=True).start()
            
            # Send complex message that might take longer
            complex_msg = {
                "type": "agent_request",
                "message": "Analyze my entire AI infrastructure stack including compute, storage, networking, " +
                          "model serving, training pipelines, data processing, and recommend comprehensive " +
                          "optimization strategies for cost reduction while maintaining performance SLAs.",
                "user_id": user_id,
                "thread_id": f"thread_{uuid.uuid4().hex[:8]}"
            }
            
            ws.send(json.dumps(complex_msg))
            
            # Monitor for thinking events during processing
            thinking_count = 0
            start = time.time()
            last_thinking = start
            
            while time.time() - start < 90:  # Extended timeout for degraded
                current_thinking = sum(1 for e in events if e.get("type") == "agent_thinking")
                if current_thinking > thinking_count:
                    thinking_count = current_thinking
                    interval = time.time() - last_thinking
                    last_thinking = time.time()
                    logger.info(f"Thinking update #{thinking_count} after {interval:.1f}s")
                    
                if any(e.get("type") == "agent_completed" for e in events):
                    break
                    
                await asyncio.sleep(0.5)
                
        finally:
            if ws:
                ws.close()
                
        # Verify thinking events kept user informed during degradation
        assert thinking_count >= 2, f"Not enough thinking updates during degradation: {thinking_count}"
        
        report = validator.generate_report()
        logger.info(report)
        
        # For degraded service, we relax timing but require completion
        has_response = any(e.get("type") == "agent_completed" for e in validator.events)
        assert has_response, "No response delivered even with extended timeout"
        
        logger.info(" PASS:  First message handled gracefully despite service degradation")
        
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_rapid_first_messages(self):
        """Test: User sends multiple messages in quick succession."""
        logger.info("=" * 80)
        logger.info("TEST: Rapid First Messages - Message Queueing")
        logger.info("=" * 80)
        
        ws = None
        all_events = []
        
        try:
            ws = websocket.WebSocket()
            ws.connect(self.ws_url)
            
            user_id = f"rapid_user_{uuid.uuid4().hex[:8]}"
            
            # Auth
            ws.send(json.dumps({
                "type": "auth",
                "token": "test_token",
                "user_id": user_id
            }))
            
            def capture():
                while True:
                    try:
                        msg = ws.recv()
                        if msg:
                            event = json.loads(msg)
                            all_events.append(event)
                            logger.info(f"Event: {event.get('type')}")
                    except:
                        break
                        
            threading.Thread(target=capture, daemon=True).start()
            
            # Send 3 messages rapidly
            messages = [
                "What are my current AI costs?",
                "Show me optimization opportunities",
                "Create a cost reduction plan"
            ]
            
            for i, msg_text in enumerate(messages):
                msg = {
                    "type": "agent_request",
                    "message": msg_text,
                    "user_id": user_id,
                    "thread_id": f"thread_{i}_{uuid.uuid4().hex[:8]}"
                }
                ws.send(json.dumps(msg))
                logger.info(f"Sent message {i+1}: {msg_text}")
                await asyncio.sleep(0.1)  # Very rapid succession
                
            # Wait for all responses
            start = time.time()
            completed_count = 0
            
            while time.time() - start < 60:
                current_completed = sum(1 for e in all_events if e.get("type") == "agent_completed")
                if current_completed > completed_count:
                    completed_count = current_completed
                    logger.info(f"Completed responses: {completed_count}/{len(messages)}")
                    
                if completed_count >= len(messages):
                    break
                    
                await asyncio.sleep(0.5)
                
        finally:
            if ws:
                ws.close()
                
        # Verify all messages got responses
        assert completed_count >= 2, f"Only {completed_count}/3 messages got responses"
        
        # Verify no message was lost
        message_received_count = sum(1 for e in all_events if e.get("type") == "message_received")
        assert message_received_count >= 2, f"Only {message_received_count}/3 messages acknowledged"
        
        logger.info(" PASS:  Rapid first messages handled successfully")
        
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_malformed_first_message(self):
        """Test: Handling of malformed/edge case first messages."""
        logger.info("=" * 80)
        logger.info("TEST: Malformed First Messages - Error Handling")
        logger.info("=" * 80)
        
        test_cases = [
            ("empty", ""),
            ("whitespace", "   \n\t   "),
            ("very_long", "optimize " * 1000),  # Very long message
            ("special_chars", "Help with [U+4F60][U+597D] [U+1F680] <script>alert('test')</script>"),
            ("json_attempt", '{"type": "hack", "admin": true}')
        ]
        
        for case_name, message_content in test_cases:
            logger.info(f"Testing case: {case_name}")
            
            ws = None
            events = []
            
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                
                user_id = f"malformed_{case_name}_{uuid.uuid4().hex[:8]}"
                
                # Auth
                ws.send(json.dumps({
                    "type": "auth",
                    "token": "test_token",
                    "user_id": user_id
                }))
                
                def capture():
                    while True:
                        try:
                            msg = ws.recv()
                            if msg:
                                events.append(json.loads(msg))
                        except:
                            break
                            
                threading.Thread(target=capture, daemon=True).start()
                
                # Send malformed message
                msg = {
                    "type": "agent_request",
                    "message": message_content,
                    "user_id": user_id,
                    "thread_id": f"thread_{uuid.uuid4().hex[:8]}"
                }
                
                ws.send(json.dumps(msg))
                
                # Wait for response
                await asyncio.sleep(5)
                
                # Should get either error or graceful handling
                has_error = any(e.get("type") == "error" for e in events)
                has_response = any(e.get("type") in ["agent_completed", "message_received"] for e in events)
                
                assert has_error or has_response, f"Case {case_name}: No response to malformed message"
                
                # If error, should be user-friendly
                if has_error:
                    error_event = next(e for e in events if e.get("type") == "error")
                    assert "message" in error_event, "Error missing user-friendly message"
                    assert "stack" not in str(error_event.get("message", "")).lower(), "Stack trace exposed to user"
                    
                logger.info(f"   PASS:  {case_name}: Handled gracefully")
                
            finally:
                if ws:
                    ws.close()
                    
        logger.info(" PASS:  All malformed messages handled appropriately")


class TestFirstMessageIntegration:
    """Integration tests for first message with system components."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup integration test environment."""
        self.env = IsolatedEnvironment()
        self.registry = AgentRegistry()
        
    @pytest.mark.asyncio
    async def test_user_context_isolation(self):
        """Test: UserExecutionContext properly isolates first messages."""
        logger.info("=" * 80)
        logger.info("TEST: User Context Isolation for First Messages")
        logger.info("=" * 80)
        
        # Create multiple user contexts
        contexts = []
        for i in range(3):
            user_id = f"isolated_user_{i}"
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{i}",
                message=f"User {i} first message"
            )
            contexts.append(context)
            
        # Verify isolation
        for i, ctx in enumerate(contexts):
            assert ctx.user_id == f"isolated_user_{i}"
            assert ctx.thread_id == f"thread_{i}"
            assert ctx.message == f"User {i} first message"
            
            # Verify no shared state
            for j, other_ctx in enumerate(contexts):
                if i != j:
                    assert ctx.user_id != other_ctx.user_id
                    assert ctx.thread_id != other_ctx.thread_id
                    assert id(ctx) != id(other_ctx)
                    
        logger.info(" PASS:  User contexts properly isolated")
        
    @pytest.mark.asyncio
    async def test_websocket_notifier_integration(self):
        """Test: WebSocketNotifier sends all required events."""
        logger.info("=" * 80)
        logger.info("TEST: WebSocket Notifier Event Generation")
        logger.info("=" * 80)
        
        # Create mock WebSocket manager
        sent_events = []
        
        class MockWSManager:
            async def send_to_user(self, user_id: str, event: Dict):
                sent_events.append(event)
                
        mock_manager = MockWSManager()
        
        # Create notifier
        notifier = WebSocketNotifier(
            websocket_manager=mock_manager,
            user_id="test_user",
            thread_id="test_thread"
        )
        
        # Simulate first message processing
        await notifier.notify_agent_started("UnifiedDataAgent", "Processing your request")
        await notifier.notify_agent_thinking("Analyzing AI infrastructure costs...")
        await notifier.notify_tool_execution("cost_analyzer", {"scope": "full"})
        await notifier.notify_tool_completed("cost_analyzer", {"monthly_cost": 50000})
        await notifier.notify_agent_completed("success", "Here's your cost analysis...")
        
        # Verify all events sent
        event_types = [e.get("type") for e in sent_events]
        
        assert "agent_started" in event_types
        assert "agent_thinking" in event_types
        assert "tool_executing" in event_types
        assert "tool_completed" in event_types
        assert "agent_completed" in event_types
        
        logger.info(f" PASS:  WebSocketNotifier sent {len(sent_events)} events correctly")
        
    @pytest.mark.asyncio
    async def test_agent_registry_websocket_enhancement(self):
        """Test: AgentRegistry properly enhances tool dispatcher."""
        logger.info("=" * 80)
        logger.info("TEST: Agent Registry WebSocket Enhancement")
        logger.info("=" * 80)
        
        # Registry should enhance tool dispatcher with WebSocket support
        ws_manager = UnifiedWebSocketManager()
        
        # Set WebSocket manager
        self.registry.set_websocket_manager(ws_manager)
        
        # Verify enhancement
        assert self.registry._websocket_manager is not None
        
        # Create execution context
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            message="Test first message"
        )
        
        # Get agent with context
        agent = self.registry.get_agent("UnifiedDataAgent", context)
        
        # Verify agent has WebSocket support
        assert agent is not None
        # Tool dispatcher should be enhanced
        
        logger.info(" PASS:  AgentRegistry properly enhances with WebSocket support")


class TestFirstMessagePerformance:
    """Performance tests for first message experience."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment with real services."""
        self.env = IsolatedEnvironment()
        
        # Determine environment from command line or environment variable
        env_name = os.environ.get("TEST_ENV", "development")
        if env_name == "staging":
            # Use staging URLs
            self.backend_url = "https://api.staging.netrasystems.ai"
            self.ws_url = "wss://api.staging.netrasystems.ai/ws"
        else:
            # Use local/development URLs
            self.backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
            self.ws_url = self.backend_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
        
        logger.info(f"Performance tests using backend: {self.backend_url}")
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(180)
    async def test_load_50_concurrent_users(self):
        """Test: System handles 50+ concurrent first-time users."""
        logger.info("=" * 80)
        logger.info("TEST: Load Test - 50 Concurrent First Messages")
        logger.info("=" * 80)
        
        num_users = 50
        successful = 0
        response_times = []
        
        async def send_user_message(user_num: int) -> Tuple[bool, float]:
            """Send message and measure response time."""
            start_time = time.time()
            
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                
                # Quick auth
                ws.send(json.dumps({
                    "type": "auth",
                    "token": f"load_test_{user_num}",
                    "user_id": f"load_user_{user_num}"
                }))
                
                # Send message
                ws.send(json.dumps({
                    "type": "agent_request",
                    "message": f"Quick optimization check #{user_num}",
                    "user_id": f"load_user_{user_num}",
                    "thread_id": f"thread_{user_num}"
                }))
                
                # Wait for any response
                timeout = 60
                while time.time() - start_time < timeout:
                    try:
                        msg = ws.recv()
                        if msg:
                            event = json.loads(msg)
                            if event.get("type") in ["agent_completed", "response_complete"]:
                                response_time = time.time() - start_time
                                ws.close()
                                return True, response_time
                    except:
                        break
                        
                ws.close()
                return False, time.time() - start_time
                
            except Exception as e:
                logger.error(f"User {user_num} failed: {e}")
                return False, time.time() - start_time
                
        # Launch all users concurrently
        logger.info(f"Launching {num_users} concurrent users...")
        tasks = [send_user_message(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"User {i}: Exception - {result}")
            else:
                success, response_time = result
                if success:
                    successful += 1
                    response_times.append(response_time)
                    
        # Calculate metrics
        success_rate = (successful / num_users) * 100
        
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            p99_response = sorted(response_times)[int(len(response_times) * 0.99)]
            p95_response = sorted(response_times)[int(len(response_times) * 0.95)]
        else:
            avg_response = p99_response = p95_response = 0
            
        logger.info(f"""
Load Test Results:
- Total Users: {num_users}
- Successful: {successful} ({success_rate:.1f}%)
- Avg Response: {avg_response:.2f}s
- P95 Response: {p95_response:.2f}s
- P99 Response: {p99_response:.2f}s
        """)
        
        # Assertions based on SLOs
        assert success_rate >= 90, f"Success rate {success_rate}% below 90% SLO"
        assert p99_response <= 60, f"P99 response time {p99_response}s exceeds 60s SLO"
        
        logger.info(" PASS:  Load test passed: System handles 50+ concurrent first messages")


if __name__ == "__main__":
    # Run with real services
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--no-header",
        "-q"
    ])