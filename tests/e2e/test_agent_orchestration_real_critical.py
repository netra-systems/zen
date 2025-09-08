#!/usr/bin/env python3
"""
MISSION CRITICAL E2E TEST: Real Agent Orchestration for Chat Flow

THIS TEST MUST PASS OR CHAT IS BROKEN - THE CORE PRODUCT FUNCTIONALITY.
Business Value: $500K+ ARR - Core chat functionality

This test validates the MOST CRITICAL path:
User sends message → Agent processes → WebSocket events sent → User sees response

REQUIREMENTS FROM CLAUDE.md:
- NO MOCKS AT ALL - Uses REAL services only
- Tests the 5 REQUIRED WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Real WebSocket connections
- Real agent execution with real LLM
- Real database connections
- BASIC expected chat flow only - not edge cases
- TOUGH timing constraints for production readiness

KEY ARCHITECTURAL COMPLIANCE:
- Uses IsolatedEnvironment per unified_environment_management.xml
- Real WebSocket connections with actual backend
- Docker-compose for service dependencies
- < 3 second response time for basic queries
- Validates WebSocket agent integration per websocket_agent_integration_critical.xml

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Any, Optional

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import test framework for REAL services with SSOT authentication
from test_framework.environment_isolation import isolated_test_env, get_test_env_manager
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user
from tests.clients.websocket_client import WebSocketTestClient
from tests.clients.backend_client import BackendTestClient
from tests.clients.auth_client import AuthTestClient

# ============================================================================
# REAL WEBSOCKET EVENT VALIDATOR - NO MOCKS
# ============================================================================

class RealWebSocketEventValidator:
    """Validates WebSocket events using REAL service connections only."""
    
    # REQUIRED events per SPEC/learnings/websocket_agent_integration_critical.xml
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self, strict_timing: bool = True):
        self.strict_timing = strict_timing
        self.events: List[Dict[str, Any]] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.start_time = time.time()
        
    def record_event(self, event: Dict[str, Any]) -> None:
        """Record an event from real WebSocket connection."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        self.events.append(event.copy())
        self.event_timeline.append((timestamp, event_type, event.copy()))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        logger.info(f"[REAL EVENT] {event_type} at {timestamp:.2f}s: {event}")
        
    def validate_critical_chat_flow(self) -> tuple[bool, List[str]]:
        """Validate the CRITICAL chat flow requirements."""
        failures = []
        
        # 1. CRITICAL: All required events must be present
        missing_events = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing_events:
            failures.append(f"CRITICAL FAILURE: Missing required WebSocket events: {missing_events}")
        
        # 2. CRITICAL: Events must be in proper order
        if not self._validate_event_order():
            failures.append("CRITICAL FAILURE: WebSocket events out of order")
        
        # 3. CRITICAL: Tool events must be paired
        if not self._validate_tool_event_pairing():
            failures.append("CRITICAL FAILURE: Unpaired tool execution events")
        
        # 4. CRITICAL: Timing must be reasonable for chat UX
        if self.strict_timing and not self._validate_chat_timing():
            failures.append("CRITICAL FAILURE: Chat response timing too slow")
        
        # 5. CRITICAL: Events must have required data
        if not self._validate_event_data_completeness():
            failures.append("CRITICAL FAILURE: Incomplete event data")
        
        return len(failures) == 0, failures
    
    def _validate_event_order(self) -> bool:
        """Ensure events follow the critical chat flow order."""
        if not self.event_timeline:
            self.errors.append("No events received")
            return False
            
        # First event MUST be agent_started
        first_event = self.event_timeline[0][1]
        if first_event != "agent_started":
            self.errors.append(f"First event was '{first_event}', must be 'agent_started'")
            return False
        
        # Last event MUST be agent_completed
        last_event = self.event_timeline[-1][1] 
        if last_event != "agent_completed":
            self.errors.append(f"Last event was '{last_event}', must be 'agent_completed'")
            return False
            
        return True
    
    def _validate_tool_event_pairing(self) -> bool:
        """Ensure every tool_executing has a matching tool_completed."""
        tool_executing_count = self.event_counts.get("tool_executing", 0)
        tool_completed_count = self.event_counts.get("tool_completed", 0)
        
        if tool_executing_count != tool_completed_count:
            self.errors.append(f"Tool event mismatch: {tool_executing_count} executing, {tool_completed_count} completed")
            return False
            
        return True
    
    def _validate_chat_timing(self) -> bool:
        """Validate timing is acceptable for chat UX."""
        if not self.event_timeline:
            return True
            
        # Total flow must complete within 3 seconds for basic queries
        total_time = self.event_timeline[-1][0]
        if total_time > 3.0:
            self.errors.append(f"Chat flow too slow: {total_time:.2f}s (max 3.0s)")
            return False
            
        # Events should arrive within reasonable intervals
        for i in range(1, len(self.event_timeline)):
            prev_time = self.event_timeline[i-1][0]
            curr_time = self.event_timeline[i][0]
            gap = curr_time - prev_time
            
            # No single gap should exceed 1.5 seconds
            if gap > 1.5:
                event_type = self.event_timeline[i][1]
                self.errors.append(f"Event gap too large: {gap:.2f}s before {event_type}")
                return False
                
        return True
    
    def _validate_event_data_completeness(self) -> bool:
        """Validate that events contain required data fields."""
        for event in self.events:
            event_type = event.get("type")
            
            # All events must have timestamp
            if not event.get("timestamp"):
                self.errors.append(f"Event {event_type} missing timestamp")
                return False
            
            # Type-specific validations
            if event_type == "agent_started":
                if not event.get("agent_id") and not event.get("agent"):
                    self.errors.append("agent_started missing agent identifier")
                    return False
                    
            elif event_type == "tool_executing":
                if not event.get("tool_name") and not event.get("tool"):
                    self.errors.append("tool_executing missing tool identifier") 
                    return False
                    
            elif event_type == "agent_completed":
                if "result" not in event and "response" not in event:
                    self.errors.append("agent_completed missing result/response")
                    return False
                    
        return True


# ============================================================================
# REAL SERVICE TEST INFRASTRUCTURE
# ============================================================================

class RealServiceChatTester:
    """Tests real chat flow using actual services with SSOT authentication."""
    
    def __init__(self):
        self.auth_helper = None
        self.ws_auth_helper = None
        self.backend_client = None 
        self.ws_client = None
        self.test_user_token = None
        self.test_user_data = None
        self.test_env = None
        
    async def setup_real_services(self, isolated_env) -> None:
        """Setup real service connections using SSOT authentication patterns."""
        self.test_env = isolated_env
        
        # Ensure we're using REAL services, not mocks
        assert isolated_env.get("USE_REAL_SERVICES") != "false", "Must use real services"
        assert isolated_env.get("TESTING") == "1", "Must be in test mode"
        
        # Determine test environment
        test_environment = isolated_env.get("TEST_ENV", isolated_env.get("ENVIRONMENT", "test"))
        
        # CRITICAL: Use SSOT E2E authentication helper
        self.auth_helper = E2EAuthHelper(environment=test_environment)
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment=test_environment)
        
        # Create authenticated user using SSOT pattern
        unique_email = f"test_chat_{uuid.uuid4().hex[:8]}@example.com"
        self.test_user_token, self.test_user_data = await create_authenticated_user(
            environment=test_environment,
            email=unique_email
        )
        
        # Validate token was created successfully
        assert self.test_user_token, "CRITICAL: Failed to create authenticated user token"
        assert self.test_user_data, "CRITICAL: Failed to create authenticated user data"
        
        # Get service endpoints from environment
        backend_host = isolated_env.get("BACKEND_HOST", "localhost")
        backend_port = isolated_env.get("BACKEND_PORT", "8000")
        
        # Initialize backend client with authentication
        backend_url = f"http://{backend_host}:{backend_port}"
        self.backend_client = BackendTestClient(backend_url)
        
        # Setup WebSocket client using SSOT auth helper
        ws_url = f"ws://{backend_host}:{backend_port}/ws"
        self.ws_client = WebSocketTestClient(ws_url)
        
        # CRITICAL: Connect WebSocket with SSOT authentication - using token for now
        # Note: WebSocket client uses Authorization header internally when token is provided
        connected = await self.ws_client.connect(token=self.test_user_token, timeout=10.0)
        assert connected, "CRITICAL: Failed to establish authenticated WebSocket connection"
        
        logger.info(f"✅ Real services setup complete with SSOT auth (environment: {test_environment})")
        logger.info(f"✅ User authenticated: {self.test_user_data.get('email')}")
        logger.info(f"✅ WebSocket connected with proper authentication headers")
        
    async def test_critical_chat_flow(self, user_message: str, timeout: float = 5.0) -> tuple[bool, RealWebSocketEventValidator]:
        """Test the critical chat flow with real services."""
        assert self.ws_client, "WebSocket client not initialized"
        
        validator = RealWebSocketEventValidator(strict_timing=True)
        
        # Start monitoring WebSocket events
        event_collection_task = asyncio.create_task(
            self._collect_websocket_events(validator, timeout)
        )
        
        # Send chat message through real WebSocket
        await self.ws_client.send_chat(text=user_message)
        logger.info(f"Sent chat message: {user_message}")
        
        # Wait for agent processing to complete
        await event_collection_task
        
        # Validate the complete flow
        is_valid, failures = validator.validate_critical_chat_flow()
        
        if not is_valid:
            logger.error(f"Chat flow validation FAILED: {failures}")
        else:
            logger.info("Chat flow validation PASSED")
            
        return is_valid, validator
        
    async def _collect_websocket_events(self, validator: RealWebSocketEventValidator, timeout: float) -> None:
        """Collect WebSocket events until agent completion or timeout."""
        start_time = time.time()
        agent_completed = False
        
        while not agent_completed and (time.time() - start_time) < timeout:
            # CRITICAL: Receive message with short timeout - MUST NOT swallow exceptions
            message = await self.ws_client.receive(timeout=0.5)
            
            if message:
                validator.record_event(message)
                
                # Check if agent flow is complete
                if message.get("type") == "agent_completed":
                    agent_completed = True
                    logger.info("Agent execution completed")
                    
                # Also check for final_report as an alternative completion
                elif message.get("type") == "final_report":
                    agent_completed = True  
                    logger.info("Final report received, considering flow complete")
            
            # CRITICAL: No exception swallowing - let real errors propagate
                
        if not agent_completed:
            logger.warning(f"Agent execution did not complete within {timeout}s")
            
    async def cleanup(self) -> None:
        """Cleanup test resources."""
        if self.ws_client and self.ws_client._websocket:
            await self.ws_client.disconnect()
        
        # Cleanup is handled by isolated environment


# ============================================================================
# MISSION CRITICAL TEST CASES
# ============================================================================

class TestRealAgentOrchestrationCritical:
    """MISSION CRITICAL: Tests real agent orchestration for chat functionality."""
    
    @pytest.mark.asyncio
    async def test_basic_chat_flow_real_services(self, isolated_test_env):
        """
        MISSION CRITICAL TEST: Basic Chat Flow with Real Services
        
        This is THE most important test - validates the core chat functionality:
        1. User sends a simple message
        2. Agent processes with real LLM 
        3. All 5 required WebSocket events are sent
        4. Response comes back within 3 seconds
        5. Chat UI shows real-time updates
        
        This CANNOT regress - it's 90% of our product value.
        """
        tester = RealServiceChatTester()
        
        # CRITICAL: Start timing validation to prevent 0.00s execution
        test_start_time = time.time()
        
        try:
            # Setup real services 
            await tester.setup_real_services(isolated_test_env)
            
            # Test the most basic expected user query
            basic_query = "What are the top 3 ways to optimize cloud costs?"
            
            # Execute the critical chat flow
            start_time = time.time()
            is_valid, validator = await tester.test_critical_chat_flow(
                user_message=basic_query,
                timeout=5.0  # Strict timeout for chat UX
            )
            execution_time = time.time() - start_time
            
            # CRITICAL: Validate test actually executed (not 0.00s bypass)
            total_test_time = time.time() - test_start_time
            assert total_test_time >= 0.1, f"CRITICAL: E2E test executed too fast ({total_test_time:.3f}s) - indicates mocking or bypassing"
            
            # CRITICAL ASSERTIONS
            assert is_valid, f"CRITICAL FAILURE: Basic chat flow failed: {validator.errors}"
            
            # Validate all required events received
            missing_events = validator.REQUIRED_EVENTS - set(validator.event_counts.keys())
            assert len(missing_events) == 0, f"Missing critical WebSocket events: {missing_events}"
            
            # Validate execution time for chat UX
            assert execution_time <= 5.0, f"Chat response too slow: {execution_time:.2f}s"
            assert execution_time >= 0.1, f"CRITICAL: Chat execution too fast ({execution_time:.3f}s) - indicates mocking"
            
            # Validate event counts make sense
            assert validator.event_counts.get("agent_started", 0) >= 1, "No agent_started events"
            assert validator.event_counts.get("agent_thinking", 0) >= 1, "No agent_thinking events"
            assert validator.event_counts.get("tool_executing", 0) >= 1, "No tool_executing events"
            assert validator.event_counts.get("tool_completed", 0) >= 1, "No tool_completed events"
            assert validator.event_counts.get("agent_completed", 0) >= 1, "No agent_completed events"
            
            # Validate event timing
            total_flow_time = validator.event_timeline[-1][0] if validator.event_timeline else 0
            assert total_flow_time <= 3.0, f"Total flow time too slow: {total_flow_time:.2f}s"
            assert total_flow_time >= 0.1, f"CRITICAL: Event flow too fast ({total_flow_time:.3f}s) - indicates mocking"
            
            logger.info(f"✅ CRITICAL TEST PASSED: Basic chat flow completed in {execution_time:.2f}s with {len(validator.events)} events")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL TEST FAILED: {e}")
            raise
        finally:
            await tester.cleanup()
    
    @pytest.mark.asyncio 
    async def test_agent_thinking_visibility_real(self, isolated_test_env):
        """
        CRITICAL: Agent Thinking Visibility Test
        
        Users MUST see when agents are thinking/reasoning.
        This test ensures agent_thinking events are sent during processing.
        """
        tester = RealServiceChatTester()
        
        # CRITICAL: Start timing validation to prevent 0.00s execution
        test_start_time = time.time()
        
        try:
            await tester.setup_real_services(isolated_test_env)
            
            # Query that requires analysis (should generate thinking events)
            analysis_query = "Analyze my AWS infrastructure and provide optimization recommendations"
            
            is_valid, validator = await tester.test_critical_chat_flow(
                user_message=analysis_query,
                timeout=8.0  # Longer timeout for analysis
            )
            
            # CRITICAL: Validate test actually executed (not bypassed)
            total_test_time = time.time() - test_start_time
            assert total_test_time >= 0.1, f"CRITICAL: E2E test executed too fast ({total_test_time:.3f}s) - indicates mocking or bypassing"
            
            # CRITICAL: Must have thinking events
            thinking_count = validator.event_counts.get("agent_thinking", 0)
            assert thinking_count >= 1, f"No agent_thinking events found (got {thinking_count})"
            
            # CRITICAL: Thinking events should have meaningful content
            thinking_events = [e for e in validator.events if e.get("type") == "agent_thinking"]
            assert len(thinking_events) > 0, "No thinking events captured"
            
            for event in thinking_events:
                # Should have some kind of thought/reasoning content
                has_content = any(key in event for key in ["thought", "thinking", "analysis", "message", "content"])
                assert has_content, f"Thinking event lacks content: {event}"
            
            logger.info(f"✅ Agent thinking visibility verified with {thinking_count} thinking events")
            
        finally:
            await tester.cleanup()
    
    @pytest.mark.asyncio
    async def test_tool_execution_transparency_real(self, isolated_test_env):
        """
        CRITICAL: Tool Execution Transparency Test
        
        Users MUST see when agents are using tools.
        This validates tool_executing and tool_completed event pairs.
        """
        tester = RealServiceChatTester()
        
        # CRITICAL: Start timing validation to prevent 0.00s execution
        test_start_time = time.time()
        
        try:
            await tester.setup_real_services(isolated_test_env)
            
            # Query that definitely requires tool usage
            tool_query = "Generate a cost optimization report for my cloud infrastructure"
            
            is_valid, validator = await tester.test_critical_chat_flow(
                user_message=tool_query,
                timeout=10.0
            )
            
            # CRITICAL: Validate test actually executed (not bypassed)
            total_test_time = time.time() - test_start_time
            assert total_test_time >= 0.1, f"CRITICAL: E2E test executed too fast ({total_test_time:.3f}s) - indicates mocking or bypassing"
            
            # CRITICAL: Must have tool execution events
            tool_executing_count = validator.event_counts.get("tool_executing", 0)
            tool_completed_count = validator.event_counts.get("tool_completed", 0)
            
            assert tool_executing_count >= 1, f"No tool_executing events (got {tool_executing_count})"
            assert tool_completed_count >= 1, f"No tool_completed events (got {tool_completed_count})"
            assert tool_executing_count == tool_completed_count, f"Unmatched tool events: {tool_executing_count} executing, {tool_completed_count} completed"
            
            # CRITICAL: Tool events should identify the tools being used
            tool_executing_events = [e for e in validator.events if e.get("type") == "tool_executing"]
            for event in tool_executing_events:
                has_tool_id = any(key in event for key in ["tool_name", "tool", "tool_id"])
                assert has_tool_id, f"Tool executing event missing tool identifier: {event}"
            
            logger.info(f"✅ Tool execution transparency verified with {tool_executing_count} tool pairs")
            
        finally:
            await tester.cleanup()
    
    @pytest.mark.asyncio
    async def test_chat_completion_notification_real(self, isolated_test_env):
        """
        CRITICAL: Chat Completion Notification Test
        
        Users MUST know when agent processing is complete.
        This validates agent_completed events are reliably sent.
        """
        tester = RealServiceChatTester()
        
        # CRITICAL: Start timing validation to prevent 0.00s execution
        test_start_time = time.time()
        
        try:
            await tester.setup_real_services(isolated_test_env)
            
            # Simple query to ensure quick completion
            simple_query = "List 3 cloud cost optimization strategies"
            
            is_valid, validator = await tester.test_critical_chat_flow(
                user_message=simple_query,
                timeout=5.0
            )
            
            # CRITICAL: Validate test actually executed (not bypassed)
            total_test_time = time.time() - test_start_time
            assert total_test_time >= 0.1, f"CRITICAL: E2E test executed too fast ({total_test_time:.3f}s) - indicates mocking or bypassing"
            
            # CRITICAL: Must end with completion event
            assert len(validator.event_timeline) > 0, "No events received"
            
            last_event_type = validator.event_timeline[-1][1]
            completion_events = ["agent_completed", "final_report"]
            assert last_event_type in completion_events, f"Flow did not end with completion event (last: {last_event_type})"
            
            # CRITICAL: Completion event should have result/response
            completion_events = [e for e in validator.events if e.get("type") in ["agent_completed", "final_report"]]
            assert len(completion_events) >= 1, "No completion events found"
            
            for event in completion_events:
                has_result = any(key in event for key in ["result", "response", "final_response", "message"])
                assert has_result, f"Completion event missing result: {event}"
            
            logger.info(f"✅ Chat completion notification verified")
            
        finally:
            await tester.cleanup()
    
    @pytest.mark.asyncio
    async def test_concurrent_chat_sessions_real(self, isolated_test_env):
        """
        CRITICAL: Concurrent Chat Sessions Test
        
        Multiple users should be able to chat simultaneously without interference.
        This tests WebSocket event isolation between concurrent sessions.
        """
        # This test simulates what happens when multiple users are chatting
        testers = []
        
        # CRITICAL: Start timing validation to prevent 0.00s execution
        test_start_time = time.time()
        
        try:
            # Setup 3 concurrent chat sessions
            for i in range(3):
                tester = RealServiceChatTester()
                await tester.setup_real_services(isolated_test_env)
                testers.append(tester)
            
            # Send different queries concurrently
            queries = [
                "What are cloud optimization best practices?",
                "How can I reduce AWS costs?", 
                "Provide infrastructure scaling recommendations"
            ]
            
            # Execute all chat flows concurrently
            tasks = []
            for i, (tester, query) in enumerate(zip(testers, queries)):
                task = asyncio.create_task(
                    tester.test_critical_chat_flow(
                        user_message=f"[Session {i+1}] {query}",
                        timeout=10.0
                    )
                )
                tasks.append(task)
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks)
            
            # CRITICAL: Validate test actually executed (not bypassed)
            total_test_time = time.time() - test_start_time
            assert total_test_time >= 0.1, f"CRITICAL: E2E test executed too fast ({total_test_time:.3f}s) - indicates mocking or bypassing"
            
            # CRITICAL: All sessions should succeed
            for i, (is_valid, validator) in enumerate(results):
                assert is_valid, f"Session {i+1} failed: {validator.errors}"
                
                # Each session should have complete event flow
                missing_events = validator.REQUIRED_EVENTS - set(validator.event_counts.keys())
                assert len(missing_events) == 0, f"Session {i+1} missing events: {missing_events}"
                
                logger.info(f"✅ Session {i+1} completed with {len(validator.events)} events")
            
            logger.info(f"✅ Concurrent chat sessions test passed for {len(testers)} sessions")
            
        finally:
            # Cleanup all testers
            for tester in testers:
                await tester.cleanup()


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """
    Run the mission-critical real agent orchestration tests.
    
    These tests validate the core chat functionality using REAL services only.
    
    Usage:
        python test_agent_orchestration_real_critical.py
        pytest test_agent_orchestration_real_critical.py -v
        pytest test_agent_orchestration_real_critical.py::TestRealAgentOrchestrationCritical::test_basic_chat_flow_real_services -v
    """
    import sys
    
    logger.info("🚀 Starting MISSION CRITICAL real agent orchestration tests")
    logger.info("⚠️  USING REAL SERVICES ONLY - NO MOCKS")
    logger.info("📊 Testing core chat functionality for $500K+ ARR product")
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--timeout=120",  # Real services need more time
        "-x"  # Stop on first failure since these are critical
    ])
    
    if exit_code == 0:
        logger.info("✅ ALL MISSION CRITICAL TESTS PASSED - Chat functionality verified")
    else:
        logger.error("❌ MISSION CRITICAL TESTS FAILED - Chat functionality broken")
    
    sys.exit(exit_code)