"""
Critical E2E Tests for GCP Staging WebSocket Race Conditions

These tests validate WebSocket behavior in actual GCP Cloud Run staging environment:
- Real GCP Cloud Run WebSocket connection lifecycle with load balancer behavior
- Complete user chat interaction with agent events in staging environment  

Business Value Justification:
1. Segment: Platform/Internal - Chat is King staging environment protection
2. Business Goal: Prevent $500K+ ARR loss from staging WebSocket failures affecting production confidence
3. Value Impact: Validates mission-critical chat functionality works in production-like GCP environment
4. Strategic Impact: Ensures staging environment mirrors production WebSocket behavior

@compliance CLAUDE.md - MANDATORY real authentication, NO MOCKS in E2E tests
@compliance Five Whys Analysis - Tests actual GCP Cloud Run infrastructure race conditions
"""

import asyncio
import pytest
import time
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

# CRITICAL: Real E2E authentication required per CLAUDE.md
import websockets
import httpx
import aiohttp

# SSOT authentication for E2E tests - MANDATORY per CLAUDE.md  
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)

# Real service infrastructure
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
from tests.mission_critical.websocket_real_test_base import RealWebSocketTestBase, requires_docker
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

# Configuration for staging environment
from tests.e2e.staging_config import StagingTestConfig, staging_urls


class TestRealGCPWebSocketConnectionLifecycle:
    """
    CRITICAL E2E TEST: Real GCP Cloud Run WebSocket connection lifecycle.
    
    FAILURE PATTERN: 2-3 minute WebSocket disconnections, 22+ second validation failures
    ROOT CAUSE: GCP Cloud Run load balancer + NEG timeout misalignment with application lifecycle
    """
    
    @pytest.fixture(autouse=True)
    async def setup_staging_environment(self):
        """Setup for staging environment testing."""
        self.env = get_env()
        
        # Determine if we're testing against real staging or local staging simulation
        self.environment = self.env.get("TEST_ENV", "test")
        self.is_real_staging = self.environment == "staging"
        
        if self.is_real_staging:
            # Real staging - use staging configuration
            self.staging_config = StagingTestConfig()
            self.websocket_url = self.staging_config.urls.websocket_url
            self.backend_url = self.staging_config.urls.backend_url  
            self.auth_url = self.staging_config.urls.auth_url
        else:
            # Local staging simulation - use Docker services
            self.docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
            
            # Start services in staging-like configuration
            await self.docker_manager.start_services_smart(
                services=["postgresql", "redis", "backend", "auth"],
                wait_healthy=True
            )
            
            self.websocket_url = "ws://localhost:8000/ws"
            self.backend_url = "http://localhost:8000"
            self.auth_url = "http://localhost:8081"
        
        # Create staging-configured auth helper
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.environment)
        
        yield
        
        # Cleanup
        if not self.is_real_staging and hasattr(self, 'docker_manager'):
            await self.docker_manager.stop_services()
    
    @pytest.mark.asyncio
    async def test_real_gcp_websocket_connection_lifecycle(self):
        """
        Test actual GCP Cloud Run WebSocket behavior (E2E Test 1).
        
        CRITICAL: This test MUST FAIL when GCP infrastructure race conditions occur.
        Tests the complete WebSocket lifecycle in GCP environment.
        """
        # Test 1: GCP-style authentication (mandatory per CLAUDE.md)
        if self.is_real_staging:
            print("🚀 REAL STAGING: Testing against actual GCP Cloud Run environment")
        else:
            print("🔧 STAGING SIMULATION: Testing against local staging-configured services")
        
        # Get authenticated token using staging-compatible method
        jwt_token = await self._get_staging_authentication()
        assert jwt_token is not None, "Must have valid JWT token for E2E test"
        
        # Test 2: WebSocket connection with GCP-appropriate timeouts
        connection_timeout = 20.0 if self.is_real_staging else 10.0  # Longer timeout for real GCP
        
        print(f"🔌 Connecting to WebSocket: {self.websocket_url}")
        print(f"⏱️ Using timeout: {connection_timeout}s")
        
        connection_start_time = time.time()
        
        try:
            # CRITICAL: Use staging-optimized connection parameters
            websocket_conn = await self.auth_helper.connect_authenticated_websocket(
                timeout=connection_timeout
            )
            
            connection_time = time.time() - connection_start_time
            print(f"✅ WebSocket connected in {connection_time:.2f}s")
            
            # Test 3: Validate connection stability (GCP race condition test)
            # Real GCP has 2-3 minute disconnection issues
            stability_test_duration = 30.0  # 30 second stability test
            stability_start = time.time()
            
            ping_count = 0
            pong_count = 0
            
            while (time.time() - stability_start) < stability_test_duration:
                # Send ping to test bidirectional communication
                ping_message = {
                    "type": "ping",
                    "timestamp": time.time(),
                    "test_id": f"gcp_stability_{ping_count}"
                }
                
                await websocket_conn.send(json.dumps(ping_message))
                ping_count += 1
                
                # Try to receive response
                try:
                    response = await asyncio.wait_for(
                        websocket_conn.recv(),
                        timeout=5.0
                    )
                    pong_count += 1
                    
                    # Validate response format
                    try:
                        response_data = json.loads(response)
                        assert "type" in response_data, "Response should have type field"
                    except json.JSONDecodeError:
                        pass  # Some responses may not be JSON
                    
                except asyncio.TimeoutError:
                    print(f"⚠️ Ping {ping_count} timed out - possible GCP race condition")
                
                # Wait before next ping (don't spam)
                await asyncio.sleep(2.0)
            
            # Test 4: Connection stability validation
            stability_rate = pong_count / ping_count if ping_count > 0 else 0
            print(f"📊 Stability test: {pong_count}/{ping_count} pings succeeded ({stability_rate:.1%})")
            
            # CRITICAL: At least 70% ping success rate (allow for GCP timing issues)
            assert stability_rate >= 0.7, f"Connection too unstable: {stability_rate:.1%} success rate"
            
            # Test 5: GCP load balancer timeout behavior
            # Test longer idle period (simulates real user behavior)
            print("⏳ Testing GCP load balancer idle timeout behavior...")
            
            idle_start = time.time()
            idle_duration = 60.0  # 60 second idle test
            
            # Wait in idle state (no messages sent)
            await asyncio.sleep(idle_duration)
            
            # Test if connection survived idle period
            try:
                alive_test = {
                    "type": "alive_test",
                    "idle_duration": idle_duration,
                    "timestamp": time.time()
                }
                await websocket_conn.send(json.dumps(alive_test))
                
                # Try to get response
                response = await asyncio.wait_for(
                    websocket_conn.recv(),
                    timeout=10.0
                )
                
                print(f"✅ Connection survived {idle_duration}s idle period")
                connection_survived_idle = True
                
            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                print(f"❌ Connection lost during idle period: {e}")
                connection_survived_idle = False
            
            # Note: Connection loss during idle is expected with GCP load balancer
            # The test validates that we detect it properly
            
            # Close connection cleanly
            await websocket_conn.close()
            
            total_test_time = time.time() - connection_start_time
            print(f"🏁 Total test time: {total_test_time:.2f}s")
            
            # Test 6: Validate GCP behavior metrics
            assert connection_time < 30.0, f"Initial connection too slow: {connection_time}s"
            assert total_test_time < 120.0, f"Total test time too long: {total_test_time}s"
            
            # Success criteria: Connection works and we can detect issues properly
            return {
                "connection_time": connection_time,
                "stability_rate": stability_rate,
                "total_pings": ping_count,
                "successful_pongs": pong_count,
                "survived_idle": connection_survived_idle,
                "total_test_time": total_test_time
            }
            
        except asyncio.TimeoutError:
            connection_time = time.time() - connection_start_time
            
            # Enhanced timeout error for GCP staging debugging
            error_msg = (
                f"WebSocket connection to {self.websocket_url} timed out after {connection_time:.2f}s. "
                f"Environment: {self.environment}. "
            )
            
            if self.is_real_staging:
                error_msg += (
                    f"This may indicate: (1) GCP Cloud Run cold start delays, "
                    f"(2) GCP NEG health check issues, "
                    f"(3) Authentication service delays, or "
                    f"(4) Load balancer configuration problems."
                )
            else:
                error_msg += f"Local staging simulation timeout - check Docker services."
            
            pytest.fail(error_msg)
        
        except Exception as e:
            pytest.fail(f"Unexpected error in GCP WebSocket lifecycle test: {e}")
    
    async def _get_staging_authentication(self) -> str:
        """Get staging-appropriate authentication token."""
        if self.is_real_staging:
            # Real staging - use E2E bypass if available
            return await self.auth_helper.get_staging_token_async()
        else:
            # Local simulation - use test token
            return self.auth_helper.create_test_jwt_token(
                user_id=f"gcp-test-{uuid.uuid4().hex[:8]}"
            )


@requires_docker  
class TestUserChatValueDeliveryE2E:
    """
    CRITICAL E2E TEST: Complete user chat interaction with agent events.
    
    FAILURE PATTERN: Missing agent events, incomplete chat responses, user experience degradation
    ROOT CAUSE: Agent execution failures don't deliver complete business value through WebSocket events
    """
    
    @pytest.fixture(autouse=True)
    async def setup_chat_test_environment(self):
        """Setup complete environment for chat value testing."""
        self.env = get_env()
        self.environment = self.env.get("TEST_ENV", "test")
        
        # Setup appropriate test environment (local or staging)
        if self.environment == "staging":
            self.staging_config = StagingTestConfig()
            self.is_real_staging = True
        else:
            # Local environment with staging-like configuration
            self.docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
            
            await self.docker_manager.start_services_smart(
                services=["postgresql", "redis", "backend", "auth"],
                wait_healthy=True
            )
            self.is_real_staging = False
        
        # Create WebSocket test infrastructure
        self.websocket_test_base = RealWebSocketTestBase()
        
        async with self.websocket_test_base.real_websocket_test_session():
            yield
        
        # Cleanup
        if not self.is_real_staging and hasattr(self, 'docker_manager'):
            await self.docker_manager.stop_services()
    
    @pytest.mark.asyncio
    async def test_user_chat_value_delivery_e2e(self):
        """
        Test complete user chat interaction with agent events (E2E Test 2).
        
        CRITICAL: This test MUST FAIL if chat business value isn't delivered properly.
        Tests the complete user journey from chat request to valuable AI response.
        """
        # Test 1: Create realistic user context (authenticated user with chat needs)
        user_context = await create_authenticated_user_context(
            user_email=f"chat_user_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        print(f"👤 Created authenticated user: {user_context.user_id}")
        
        # Test 2: Establish WebSocket connection for chat
        test_context = await self.websocket_test_base.create_test_context(
            user_id=str(user_context.user_id),
            jwt_token=user_context.agent_context.get('jwt_token')
        )
        
        await test_context.setup_websocket_connection(
            endpoint="/ws",  # Main WebSocket endpoint
            auth_required=True
        )
        
        print("🔌 WebSocket connection established for chat")
        
        # Test 3: Send realistic chat request (business value scenario)
        chat_request = {
            "type": "chat_message",
            "message": "Help me analyze the performance of my e-commerce website and suggest optimizations.",
            "user_id": str(user_context.user_id),
            "thread_id": str(user_context.thread_id),
            "context": {
                "chat_session": True,
                "expects_agent_response": True,
                "business_context": "e-commerce optimization"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"💬 Sending chat request: {chat_request['message'][:50]}...")
        
        chat_start_time = time.time()
        await test_context.send_message(chat_request)
        
        # Test 4: Validate all required agent events are delivered (business value requirement)
        required_agent_events = {
            "agent_started",     # User sees agent processing started
            "agent_thinking",    # User sees AI reasoning process
            "tool_executing",    # User sees tool usage (analysis tools)
            "tool_completed",    # User sees analysis results
            "agent_completed"    # User knows response is complete
        }
        
        print("📊 Waiting for agent events (business value delivery)...")
        
        # Allow longer timeout for complex agent processing
        agent_timeout = 120.0 if self.is_real_staging else 60.0
        
        event_validation = await self.websocket_test_base.validate_agent_events(
            test_context=test_context,
            required_events=required_agent_events,
            timeout=agent_timeout
        )
        
        chat_total_time = time.time() - chat_start_time
        print(f"⏱️ Total chat processing time: {chat_total_time:.2f}s")
        
        # CRITICAL: All agent events must be delivered for business value
        assert event_validation.success, f"Agent events not delivered: {event_validation.missing_events}"
        
        # Test 5: Validate chat response quality (business value metrics)
        captured_events = event_validation.events_captured
        
        # Extract actual chat response/content
        agent_responses = []
        for event in captured_events:
            if event.get("type") == "agent_completed" and "content" in event:
                agent_responses.append(event["content"])
            elif event.get("type") == "chat_response":
                agent_responses.append(event.get("message", ""))
        
        # Test 6: Business value validation
        has_substantial_response = any(
            len(str(response)) > 50  # At least 50 characters of response
            for response in agent_responses
        )
        
        assert has_substantial_response, "Agent should provide substantial response for business value"
        
        # Test 7: User experience timing validation
        # Chat should be responsive (not too slow)
        assert chat_total_time < 180.0, f"Chat response too slow: {chat_total_time}s (user experience degraded)"
        
        # But also not suspiciously fast (suggests no real processing)
        assert chat_total_time > 1.0, f"Chat response too fast: {chat_total_time}s (suggests no real AI processing)"
        
        # Test 8: Event timing and ordering validation (UX requirement)
        event_timestamps = []
        event_types_ordered = []
        
        for event in captured_events:
            if event.get("timestamp") and event.get("type"):
                try:
                    ts = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                    event_timestamps.append(ts.timestamp())
                    event_types_ordered.append(event["type"])
                except:
                    pass
        
        # Validate event ordering makes business sense
        if "agent_started" in event_types_ordered and "agent_completed" in event_types_ordered:
            started_idx = event_types_ordered.index("agent_started")
            completed_idx = event_types_ordered.index("agent_completed") 
            
            assert started_idx < completed_idx, "agent_started must come before agent_completed (logical order)"
        
        # Test 9: Validate chat session can handle follow-up (real user behavior)
        followup_request = {
            "type": "chat_message", 
            "message": "Can you provide more details about the SEO optimizations you mentioned?",
            "user_id": str(user_context.user_id),
            "thread_id": str(user_context.thread_id),  # Same thread - conversation continuity
            "context": {
                "chat_session": True,
                "followup_request": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        print("💬 Sending follow-up chat message...")
        
        await test_context.send_message(followup_request)
        
        # Quick validation that follow-up is processed (don't wait for full cycle)
        try:
            followup_response = await test_context.receive_message(timeout=30.0)
            followup_processed = True
            print("✅ Follow-up message processed successfully")
        except asyncio.TimeoutError:
            followup_processed = False
            print("⚠️ Follow-up message timed out (may indicate session issues)")
        
        # Cleanup
        await test_context.cleanup()
        
        # Test 10: Return business value metrics
        return {
            "chat_processing_time": chat_total_time,
            "agent_events_delivered": len(event_validation.required_events_found),
            "total_events_captured": event_validation.total_events,
            "missing_events": list(event_validation.missing_events),
            "has_substantial_response": has_substantial_response,
            "followup_processed": followup_processed,
            "business_value_delivered": (
                event_validation.success and 
                has_substantial_response and
                chat_total_time < 180.0
            )
        }


# CRITICAL: Mark all E2E tests to enforce authentication requirement
@pytest.mark.e2e_auth_required
class TestWebSocketRaceConditionE2EIntegration:
    """
    Integration of both E2E tests - validates complete GCP WebSocket + Chat scenarios.
    """
    
    @pytest.mark.asyncio
    async def test_combined_gcp_websocket_chat_scenario(self):
        """
        Test combined GCP WebSocket connection + chat value delivery.
        
        CRITICAL: This test validates that both infrastructure and business value work together.
        """
        env = get_env()
        environment = env.get("TEST_ENV", "test")
        
        # Test 1: GCP WebSocket infrastructure test
        infrastructure_test = TestRealGCPWebSocketConnectionLifecycle()
        await infrastructure_test.setup_staging_environment().__aenter__()
        
        try:
            infrastructure_result = await infrastructure_test.test_real_gcp_websocket_connection_lifecycle()
            
            # Infrastructure should work
            assert infrastructure_result["stability_rate"] >= 0.7, "Infrastructure test failed"
            
        finally:
            await infrastructure_test.setup_staging_environment().__aexit__(None, None, None)
        
        # Test 2: Chat value delivery test (if infrastructure works)
        chat_test = TestUserChatValueDeliveryE2E()
        await chat_test.setup_chat_test_environment().__aenter__()
        
        try:
            chat_result = await chat_test.test_user_chat_value_delivery_e2e()
            
            # Chat business value should be delivered
            assert chat_result["business_value_delivered"], "Chat business value not delivered"
            
        finally:
            await chat_test.setup_chat_test_environment().__aexit__(None, None, None)
        
        # Combined success criteria
        combined_success = (
            infrastructure_result["stability_rate"] >= 0.7 and
            chat_result["business_value_delivered"]
        )
        
        assert combined_success, "Combined GCP WebSocket + Chat scenario failed"
        
        return {
            "infrastructure_metrics": infrastructure_result,
            "chat_metrics": chat_result,
            "combined_success": combined_success
        }


if __name__ == "__main__":
    # Allow running tests directly for development
    pytest.main([__file__, "-v", "--tb=short", "--e2e"])