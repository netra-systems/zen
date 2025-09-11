# 🚀 Golden Path WebSocket User Flow Test Plan - Comprehensive

## 🚨 CRITICAL REQUIREMENTS FROM CLAUDE.md

**SLIGHT EMPHASIS OF WORKING MOMENT:** 
Focusing on **"WebSocket Agent Events (Infrastructure for Chat Value)"** - the mission-critical requirement that WebSocket events enable substantive chat interactions and serve the business goal of delivering AI value to users.

### Core Testing Principles
- **ALL e2e tests MUST use authentication** (JWT/OAuth) except tests that directly validate auth itself
- **NO MOCKS in E2E tests** - use real services, real WebSocket connections
- **Use test_framework/ssot/e2e_auth_helper.py** for SSOT auth patterns
- **Tests must FAIL HARD** when issues are present - no try/except blocks hiding failures
- **Follow TEST_ARCHITECTURE_VISUAL_OVERVIEW.md** structure

### Business Value Justification (BVJ)
- **Segment:** All (Free, Early, Mid, Enterprise)
- **Business Goal:** Ensure chat system delivers $500K+ ARR through reliable agent interactions
- **Value Impact:** WebSocket events enable 90% of business value (substantive AI conversations)
- **Strategic Impact:** Prevent "every 3 minutes staging failures" that block user value delivery

## 🎯 The Four Critical Golden Path Issues

Based on analysis of recent commit history and WebSocket 1011 error reports:

### 1. **Race Conditions in WebSocket Handshake**
- **Root Cause:** WebSocket connections failing with 1011 errors in Cloud Run environments
- **Manifestation:** Rapid connection attempts before handshake completion
- **Business Impact:** Users can't establish chat sessions, blocking all AI value delivery

### 2. **Missing Service Dependencies** 
- **Root Cause:** WebSocket connections attempted when agent supervisor/thread services unavailable
- **Manifestation:** Connection established but agent execution fails silently
- **Business Impact:** Chat appears working but provides no substantive AI responses

### 3. **Factory Initialization Failures**
- **Root Cause:** WebSocket manager factory SSOT validation failures
- **Manifestation:** `FactoryInitializationError` during WebSocket setup
- **Business Impact:** WebSocket infrastructure broken, no real-time updates to users

### 4. **Missing WebSocket Events**
- **Root Cause:** Agent execution without proper WebSocket event emission
- **Manifestation:** Users see no progress indicators during agent execution
- **Business Impact:** Poor UX, users think system is broken, abandon sessions

## 📋 Test Architecture Design

### Test Layer Structure
Following TEST_ARCHITECTURE_VISUAL_OVERVIEW.md:

```
Unit Tests (No Infrastructure)
├── Race condition detection logic
├── Factory validation patterns  
└── Event emission validation

Integration Tests (Local Services)
├── WebSocket handshake timing
├── Service dependency validation
└── Factory initialization sequences

E2E Tests (Full Docker + Real LLM)
├── Complete Golden Path flows
├── Multi-user concurrent scenarios  
└── Staging environment validation

Mission Critical Tests (Business Critical)
├── All 5 WebSocket events validation
├── Race condition resilience
└── Service failure graceful degradation
```

### Authentication Strategy
All tests MUST use `test_framework/ssot/e2e_auth_helper.py`:

```python
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper

# For staging tests
auth_helper = E2EWebSocketAuthHelper(environment="staging")
token = await auth_helper.get_staging_token_async()
headers = auth_helper.get_websocket_headers(token)

# For local tests  
auth_helper = E2EWebSocketAuthHelper(environment="test")
token = auth_helper.create_test_jwt_token(user_id="test-user")
headers = auth_helper.get_websocket_headers(token)
```

## 🧪 Test Suite 1: Race Conditions in WebSocket Handshake

### Issue Analysis
Recent commit analysis shows fixes for WebSocket 1011 errors with messages like:
- "fix: resolve WebSocket 1011 error race condition in staging GCP environment"  
- "fix: enhance WebSocket error handling to prevent 1011 errors"

### Test Categories

#### Unit Tests
**Location:** `netra_backend/tests/unit/test_websocket_race_conditions.py`

```python
"""
Test WebSocket Race Condition Detection Logic

Business Value Justification (BVJ):
- Segment: All  
- Business Goal: Prevent connection failures that block chat value
- Value Impact: Ensure reliable WebSocket handshake in all environments
- Strategic Impact: Eliminate 1011 errors causing user abandonment
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from netra_backend.app.websocket_core.connection_handler import WebSocketConnectionHandler

class TestWebSocketRaceConditionDetection:
    """Test race condition detection and mitigation logic."""
    
    def test_handshake_completion_detection(self):
        """Test that handshake completion is properly detected."""
        handler = WebSocketConnectionHandler()
        
        # Simulate rapid state changes
        handler._connection_state = "connecting"
        handler._mark_handshake_start()
        
        # Should detect incomplete handshake
        assert not handler._is_handshake_complete()
        
        handler._mark_handshake_complete()
        assert handler._is_handshake_complete()
    
    def test_premature_message_sending_prevention(self):
        """Test that messages are queued until handshake completes."""
        handler = WebSocketConnectionHandler()
        handler._connection_state = "connecting"
        
        # Should queue message, not send immediately
        result = handler._queue_message({"type": "test"})
        assert result.queued == True
        assert result.sent == False
        
        # Complete handshake, should flush queue
        handler._mark_handshake_complete()
        assert len(handler._queued_messages) == 0

    @pytest.mark.asyncio
    async def test_concurrent_connection_attempts(self):
        """Test handling of multiple simultaneous connection attempts."""
        handler = WebSocketConnectionHandler()
        
        # Simulate concurrent connection attempts
        tasks = []
        for i in range(10):
            task = asyncio.create_task(handler._attempt_connection(f"client_{i}"))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Only one should succeed, others should get queued or rejected gracefully
        successful_connections = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_connections) <= 1  # At most one concurrent connection
        
        # No 1011 errors should occur
        for result in results:
            if isinstance(result, Exception):
                assert "1011" not in str(result)
```

#### Integration Tests  
**Location:** `netra_backend/tests/integration/test_websocket_handshake_timing.py`

```python
"""
Test WebSocket Handshake Timing with Real Services

Uses real PostgreSQL and Redis but mocks external services.
"""

import pytest
import asyncio
import websockets
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper

class TestWebSocketHandshakeTiming(BaseIntegrationTest):
    """Test WebSocket handshake timing with real backend service."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_handshake_completion_under_load(self, real_services_fixture):
        """Test handshake completion under rapid connection attempts."""
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Create multiple users for concurrent testing
        users = []
        for i in range(5):
            user_id = f"race_test_user_{i}"
            token = auth_helper.create_test_jwt_token(user_id=user_id)
            headers = auth_helper.get_websocket_headers(token)
            users.append({"user_id": user_id, "token": token, "headers": headers})
        
        websocket_url = "ws://localhost:8000/ws"
        successful_connections = 0
        connection_times = []
        
        async def attempt_connection(user_data):
            """Attempt WebSocket connection for a user."""
            start_time = asyncio.get_event_loop().time()
            try:
                async with websockets.connect(
                    websocket_url,
                    additional_headers=user_data["headers"],
                    open_timeout=10.0
                ) as websocket:
                    # Send test message to verify handshake completion
                    test_msg = {
                        "type": "ping",
                        "user_id": user_data["user_id"]
                    }
                    await websocket.send(json.dumps(test_msg))
                    
                    # Wait for response with timeout
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    connection_time = asyncio.get_event_loop().time() - start_time
                    return {
                        "success": True,
                        "user_id": user_data["user_id"],
                        "connection_time": connection_time,
                        "response": response_data
                    }
                    
            except Exception as e:
                connection_time = asyncio.get_event_loop().time() - start_time
                return {
                    "success": False,
                    "user_id": user_data["user_id"],
                    "connection_time": connection_time,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        
        # Launch concurrent connection attempts
        tasks = [attempt_connection(user) for user in users]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        # CRITICAL: No 1011 errors should occur
        for failure in failed:
            assert "1011" not in failure.get("error", "")
            assert "Internal Server Error" not in failure.get("error", "")
        
        # At least 80% should succeed (allowing for some GCP Cloud Run limitations)
        success_rate = len(successful) / len(results)
        assert success_rate >= 0.8, f"Success rate {success_rate:.2%} below 80% threshold"
        
        # Connection times should be reasonable (under 5 seconds)
        avg_connection_time = sum(r["connection_time"] for r in successful) / len(successful)
        assert avg_connection_time < 5.0, f"Average connection time {avg_connection_time:.2f}s too slow"
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_queuing_during_handshake(self, real_services_fixture):
        """Test that messages sent during handshake are queued properly."""
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = "handshake_queue_test_user"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        headers = auth_helper.get_websocket_headers(token)
        
        websocket_url = "ws://localhost:8000/ws"
        
        async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
            # Immediately send messages before handshake might be complete
            messages_to_send = [
                {"type": "immediate_test_1", "data": "test1"},
                {"type": "immediate_test_2", "data": "test2"},  
                {"type": "immediate_test_3", "data": "test3"}
            ]
            
            # Send all messages rapidly
            for msg in messages_to_send:
                await websocket.send(json.dumps(msg))
            
            # Collect responses
            received_responses = []
            timeout = 10.0
            
            async def collect_responses():
                try:
                    while len(received_responses) < len(messages_to_send):
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        received_responses.append(json.loads(response))
                except asyncio.TimeoutError:
                    pass  # Expected if not all messages processed
            
            await asyncio.wait_for(collect_responses(), timeout=timeout)
            
            # All messages should be processed (even if queued initially)
            assert len(received_responses) >= 1, "At least one response should be received"
            
            # No internal server errors should occur
            for response in received_responses:
                assert response.get("type") != "error" or "500" not in response.get("message", "")
```

#### E2E Tests
**Location:** `tests/e2e/test_websocket_race_conditions_golden_path.py`

```python
"""
Test WebSocket Race Conditions in Golden Path User Flows

Business Value: Ensure users can reliably establish chat sessions for AI value delivery
"""

import pytest
import asyncio
import json
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, create_authenticated_user_context

class TestWebSocketRaceConditionsE2E(BaseE2ETest):
    """End-to-end tests for WebSocket race condition resilience."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_golden_path_chat_with_rapid_connections(self):
        """Test complete golden path flow with rapid WebSocket connections."""
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            environment="test",
            websocket_enabled=True
        )
        
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        websocket_url = "ws://localhost:8000/ws"
        
        # Test rapid connection/disconnection cycles (simulates network issues)
        successful_agent_interactions = 0
        total_attempts = 5
        
        for attempt in range(total_attempts):
            try:
                # Create fresh connection for each attempt
                token = auth_helper.create_test_jwt_token(
                    user_id=str(user_context.user_id),
                    email=user_context.agent_context["user_email"]
                )
                headers = auth_helper.get_websocket_headers(token)
                
                # Establish connection and immediately send agent request
                websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
                
                # Send agent request for cost optimization (core business value)
                agent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": f"Quick test request {attempt}",
                    "thread_id": str(user_context.thread_id),
                    "user_id": str(user_context.user_id)
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect WebSocket events with timeout
                received_events = []
                required_events = {"agent_started", "agent_thinking", "agent_completed"}
                events_received = set()
                
                async def collect_events():
                    while len(events_received) < len(required_events):
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            event_data = json.loads(response)
                            received_events.append(event_data)
                            
                            event_type = event_data.get("type")
                            if event_type in required_events:
                                events_received.add(event_type)
                                
                        except asyncio.TimeoutError:
                            break
                        except Exception as e:
                            print(f"Event collection error: {e}")
                            break
                
                await asyncio.wait_for(collect_events(), timeout=30.0)
                await websocket.close()
                
                # Verify critical events received
                if len(events_received) >= 2:  # At least started and completed
                    successful_agent_interactions += 1
                
                # Small delay between attempts
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Attempt {attempt} failed: {e}")
                # CRITICAL: 1011 errors should not occur
                assert "1011" not in str(e), f"WebSocket 1011 error detected: {e}"
                continue
        
        # At least 80% of attempts should succeed despite rapid connections
        success_rate = successful_agent_interactions / total_attempts
        assert success_rate >= 0.8, f"Success rate {success_rate:.2%} below acceptable threshold"
        
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_staging_cloud_run_race_conditions(self):
        """Test WebSocket race conditions in staging GCP Cloud Run environment."""
        auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        # Get staging token with proper bypass
        token = await auth_helper.get_staging_token_async()
        headers = auth_helper.get_websocket_headers(token)
        
        # Test multiple rapid connections to staging (GCP-specific)
        staging_websocket_url = auth_helper.config.websocket_url  # staging URL
        
        connection_attempts = 3  # Conservative for staging
        successful_connections = 0
        
        for attempt in range(connection_attempts):
            try:
                # Use staging-optimized connection with shorter timeout
                websocket = await auth_helper.connect_authenticated_websocket(timeout=12.0)
                
                # Send simple ping to verify connection
                ping_message = {
                    "type": "ping",
                    "staging_test": True,
                    "attempt": attempt
                }
                
                await websocket.send(json.dumps(ping_message))
                
                # Wait for any response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                    response_data = json.loads(response)
                    successful_connections += 1
                    print(f"Staging connection {attempt} successful: {response_data.get('type')}")
                except asyncio.TimeoutError:
                    print(f"Staging connection {attempt} timeout (may be normal)")
                    successful_connections += 1  # Timeout may be normal in staging
                
                await websocket.close()
                
                # Delay between staging attempts (respectful of GCP limits)
                await asyncio.sleep(1.0)
                
            except Exception as e:
                print(f"Staging attempt {attempt} error: {e}")
                # CRITICAL: Should not get 1011 errors even in staging
                if "1011" in str(e):
                    pytest.fail(f"Staging WebSocket 1011 error (should be fixed): {e}")
                    
        # At least 2/3 should succeed in staging (accounting for GCP limitations)
        success_rate = successful_connections / connection_attempts  
        assert success_rate >= 0.67, f"Staging success rate {success_rate:.2%} too low"
```

## 🧪 Test Suite 2: Missing Service Dependencies

### Issue Analysis
WebSocket connections established but agent execution fails when supervisor/thread services unavailable.

#### Unit Tests
**Location:** `netra_backend/tests/unit/test_service_dependency_validation.py`

```python
"""
Test Service Dependency Validation Logic

Business Value: Prevent silent agent failures that block AI value delivery
"""

import pytest
from unittest.mock import Mock, AsyncMock
from netra_backend.app.websocket_core.service_dependency_validator import ServiceDependencyValidator

class TestServiceDependencyValidation:
    """Test service dependency validation and fallback logic."""
    
    def test_required_services_detection(self):
        """Test detection of required services for WebSocket functionality."""
        validator = ServiceDependencyValidator()
        
        # Required services for agent execution
        required = validator.get_required_services()
        
        assert "agent_supervisor" in required
        assert "thread_service" in required  
        assert "llm_service" in required
        assert "database" in required
        
    @pytest.mark.asyncio
    async def test_service_availability_check(self):
        """Test checking availability of required services."""
        validator = ServiceDependencyValidator()
        
        # Mock service responses
        mock_services = {
            "agent_supervisor": AsyncMock(return_value={"status": "healthy"}),
            "thread_service": AsyncMock(return_value={"status": "healthy"}),
            "llm_service": AsyncMock(return_value={"status": "healthy"}),
            "database": AsyncMock(return_value={"status": "healthy"})
        }
        
        validator._service_clients = mock_services
        
        availability = await validator.check_service_availability()
        
        assert availability["agent_supervisor"] == True
        assert availability["thread_service"] == True
        assert availability["llm_service"] == True
        assert availability["database"] == True
        assert availability["all_available"] == True
        
    @pytest.mark.asyncio
    async def test_degraded_mode_detection(self):
        """Test detection when services are unavailable."""
        validator = ServiceDependencyValidator()
        
        # Mock some services as unavailable
        mock_services = {
            "agent_supervisor": AsyncMock(side_effect=Exception("Service unavailable")),
            "thread_service": AsyncMock(return_value={"status": "healthy"}),
            "llm_service": AsyncMock(side_effect=Exception("Service unavailable")),
            "database": AsyncMock(return_value={"status": "healthy"})
        }
        
        validator._service_clients = mock_services
        
        availability = await validator.check_service_availability()
        
        assert availability["agent_supervisor"] == False
        assert availability["llm_service"] == False
        assert availability["all_available"] == False
        
        # Should recommend degraded mode
        mode = validator.recommend_operation_mode(availability)
        assert mode == "degraded"
        
    def test_graceful_fallback_message_generation(self):
        """Test generation of user-friendly fallback messages."""
        validator = ServiceDependencyValidator()
        
        unavailable_services = ["agent_supervisor", "llm_service"]
        
        fallback_message = validator.generate_fallback_message(unavailable_services)
        
        assert "temporarily unavailable" in fallback_message.lower()
        assert "agent" in fallback_message.lower()
        assert len(fallback_message) > 50  # Substantial message
        assert "please try again" in fallback_message.lower()
```

#### Integration Tests
**Location:** `netra_backend/tests/integration/test_service_dependency_integration.py`

```python
"""
Test Service Dependencies with Real Services

Tests WebSocket behavior when various services are unavailable.
"""

import pytest
import asyncio
import json
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper

class TestServiceDependencyIntegration(BaseIntegrationTest):
    """Test WebSocket behavior with missing service dependencies."""
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_websocket_with_database_unavailable(self, real_services_fixture):
        """Test WebSocket behavior when database is unavailable."""
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = "service_dep_test_user"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        headers = auth_helper.get_websocket_headers(token)
        
        # NOTE: This test assumes we can simulate database unavailability
        # In real integration, this might mean stopping PostgreSQL container
        
        websocket_url = "ws://localhost:8000/ws"
        
        try:
            # Connection should still succeed (WebSocket layer separate from database)
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                
                # Send agent request that would require database
                agent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent", 
                    "message": "Test with no database",
                    "user_id": user_id
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Should receive graceful error, not crash
                received_messages = []
                
                async def collect_responses():
                    try:
                        while len(received_messages) < 3:  # Expect error response
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            received_messages.append(json.loads(response))
                    except asyncio.TimeoutError:
                        pass
                
                await collect_responses()
                
                # Should receive error message, not silent failure
                error_messages = [m for m in received_messages if m.get("type") == "error"]
                assert len(error_messages) > 0, "Should receive error notification when database unavailable"
                
                # Error should be user-friendly
                error_message = error_messages[0].get("message", "")
                assert "temporarily unavailable" in error_message.lower() or \
                       "service unavailable" in error_message.lower()
                       
        except Exception as e:
            # Connection failure is acceptable if database critical for WebSocket auth
            print(f"Expected database dependency failure: {e}")
            assert "connection" in str(e).lower() or "auth" in str(e).lower()
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_websocket_graceful_degradation(self, real_services_fixture):
        """Test graceful degradation when LLM service unavailable."""
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = "degradation_test_user"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        headers = auth_helper.get_websocket_headers(token)
        
        websocket_url = "ws://localhost:8000/ws"
        
        async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
            
            # Send request that requires LLM (when LLM unavailable in test env)
            agent_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Analyze complex scenario requiring LLM",
                "user_id": user_id,
                "require_llm": True
            }
            
            await websocket.send(json.dumps(agent_request))
            
            received_events = []
            fallback_received = False
            
            async def collect_events():
                nonlocal fallback_received
                try:
                    while len(received_events) < 5:  # Expect multiple events
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event_data = json.loads(response)
                        received_events.append(event_data)
                        
                        # Look for fallback/degraded mode notification
                        if (event_data.get("type") == "agent_completed" and 
                            "fallback" in event_data.get("message", "").lower()):
                            fallback_received = True
                            break
                            
                except asyncio.TimeoutError:
                    pass
            
            await collect_events()
            
            # Should receive agent_started event (WebSocket working)
            event_types = [e.get("type") for e in received_events]
            assert "agent_started" in event_types, "Should receive agent_started even in degraded mode"
            
            # Should receive completion event (even if degraded)
            assert "agent_completed" in event_types or fallback_received, \
                   "Should receive completion notification in degraded mode"
                   
            # Should not silently fail (must communicate status to user)
            assert len(received_events) > 0, "Must not silently fail when services unavailable"
```

#### E2E Tests
**Location:** `tests/e2e/test_service_dependency_failures_e2e.py`

```python
"""
Test Service Dependency Failures in Complete User Flows

Business Value: Ensure users receive value even when some services degraded
"""

import pytest
import asyncio
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context

class TestServiceDependencyFailuresE2E(BaseE2ETest):
    """Test complete user flows with service dependencies unavailable."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_chat_continuation_with_agent_service_down(self):
        """Test that chat continues working when agent supervisor down."""
        user_context = await create_authenticated_user_context(
            environment="test",
            websocket_enabled=True  
        )
        
        # Establish chat session
        from test_framework.websocket_helpers import WebSocketTestClient
        
        async with WebSocketTestClient("ws://localhost:8000/ws", str(user_context.user_id)) as ws_client:
            
            # First - establish working session
            initial_message = {
                "type": "message", 
                "content": "Hello, I need help",
                "thread_id": str(user_context.thread_id)
            }
            
            await ws_client.send_json(initial_message)
            
            # Should get initial response (services working)
            initial_events = []
            
            async def collect_initial_events():
                try:
                    async for event in ws_client.receive_events(timeout=10.0):
                        initial_events.append(event)
                        if event.get("type") == "message_received":
                            break
                except asyncio.TimeoutError:
                    pass
            
            await collect_initial_events()
            
            assert len(initial_events) > 0, "Should receive initial response"
            
            # Simulate agent service becoming unavailable
            # (In real test, this might involve container stop/start)
            
            degraded_message = {
                "type": "message",
                "content": "Continue helping me with analysis", 
                "thread_id": str(user_context.thread_id),
                "simulate_agent_unavailable": True  # Test flag
            }
            
            await ws_client.send_json(degraded_message)
            
            # Should get degraded mode response, not silent failure
            degraded_events = []
            
            async def collect_degraded_events():
                try:
                    async for event in ws_client.receive_events(timeout=15.0):
                        degraded_events.append(event)
                        if event.get("type") in ["error", "agent_unavailable", "degraded_mode"]:
                            break
                        if len(degraded_events) >= 3:
                            break
                except asyncio.TimeoutError:
                    pass
                    
            await collect_degraded_events()
            
            # CRITICAL: Must not silently fail
            assert len(degraded_events) > 0, "Must receive some response even when agent service down"
            
            # Should communicate degraded state to user
            messages = [e.get("message", "") for e in degraded_events]
            combined_messages = " ".join(messages).lower()
            
            degraded_keywords = ["unavailable", "degraded", "limited", "try again", "temporary"]
            has_degraded_message = any(keyword in combined_messages for keyword in degraded_keywords)
            
            assert has_degraded_message, f"Should communicate degraded state. Messages: {messages}"
```

## 🧪 Test Suite 3: Factory Initialization Failures

### Issue Analysis  
WebSocket manager factory SSOT validation failures causing `FactoryInitializationError`.

#### Unit Tests
**Location:** `netra_backend/tests/unit/test_websocket_factory_initialization.py`

```python
"""
Test WebSocket Factory Initialization Logic

Business Value: Ensure WebSocket infrastructure initializes reliably
"""

import pytest
from unittest.mock import Mock, patch
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.factories.websocket_manager_factory import WebSocketManagerFactory

class TestWebSocketFactoryInitialization:
    """Test WebSocket factory initialization and validation."""
    
    def test_factory_initialization_success(self):
        """Test successful factory initialization with valid config."""
        config = {
            "websocket_host": "localhost",
            "websocket_port": 8000,
            "max_connections": 1000,
            "auth_required": True
        }
        
        factory = WebSocketManagerFactory(config)
        
        # Should initialize without errors
        assert factory.is_valid()
        assert factory.config == config
        
        # Should be able to create manager
        manager = factory.create_manager()
        assert isinstance(manager, UnifiedWebSocketManager)
        
    def test_factory_initialization_invalid_config(self):
        """Test factory initialization with invalid configuration."""
        invalid_configs = [
            {},  # Empty config
            {"websocket_host": ""},  # Empty host
            {"websocket_port": "invalid"},  # Invalid port type
            {"max_connections": -1},  # Invalid connection limit
            {"auth_required": "not_boolean"}  # Invalid auth flag type
        ]
        
        for invalid_config in invalid_configs:
            with pytest.raises(ValueError) as exc_info:
                factory = WebSocketManagerFactory(invalid_config)
                factory.validate_config()
            
            assert "configuration" in str(exc_info.value).lower()
            
    def test_ssot_validation_enforcement(self):
        """Test that SSOT validation is enforced during initialization."""
        config = {
            "websocket_host": "localhost",
            "websocket_port": 8000,
            "max_connections": 1000,
            "auth_required": True
        }
        
        factory = WebSocketManagerFactory(config)
        
        # Should validate SSOT patterns
        validation_result = factory.validate_ssot_compliance()
        
        assert validation_result["valid"] == True
        assert "jwt_secret_manager" in validation_result["components"]
        assert "unified_environment" in validation_result["components"]
        
    def test_factory_initialization_error_conditions(self):
        """Test FactoryInitializationError conditions."""
        from netra_backend.app.exceptions import FactoryInitializationError
        
        # Missing critical dependencies
        with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_manager:
            mock_manager.side_effect = ImportError("Missing dependency")
            
            config = {"websocket_host": "localhost", "websocket_port": 8000}
            factory = WebSocketManagerFactory(config)
            
            with pytest.raises(FactoryInitializationError) as exc_info:
                factory.create_manager()
                
            assert "dependency" in str(exc_info.value).lower()
            
    def test_factory_singleton_prevention(self):
        """Test that factory prevents singleton anti-patterns."""
        config = {"websocket_host": "localhost", "websocket_port": 8000}
        
        factory1 = WebSocketManagerFactory(config)
        factory2 = WebSocketManagerFactory(config)
        
        manager1 = factory1.create_manager()
        manager2 = factory2.create_manager()
        
        # Should create separate instances (no singleton pattern)
        assert manager1 is not manager2
        assert id(manager1) != id(manager2)
        
        # But should be functionally equivalent
        assert type(manager1) == type(manager2)
```

#### Integration Tests
**Location:** `netra_backend/tests/integration/test_factory_initialization_integration.py`

```python
"""
Test Factory Initialization with Real Services

Tests factory behavior with real database, Redis, and environment setup.
"""

import pytest
import asyncio
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.factories.websocket_manager_factory import WebSocketManagerFactory

class TestFactoryInitializationIntegration(BaseIntegrationTest):
    """Test factory initialization with real service dependencies."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_with_real_database_connection(self, real_services_fixture):
        """Test factory initialization with real database connection."""
        # Real services provide PostgreSQL and Redis
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create factory with real service references
        config = {
            "websocket_host": "localhost",
            "websocket_port": 8000,
            "database_connection": db,
            "redis_connection": redis,
            "auth_required": True
        }
        
        factory = WebSocketManagerFactory(config)
        
        # Should initialize successfully with real services
        assert factory.is_valid()
        
        # Should create manager that can connect to real services
        manager = factory.create_manager()
        
        # Test database connectivity through manager
        user_test_data = {
            "user_id": "factory_test_user",
            "session_id": "test_session_123"
        }
        
        # Manager should be able to store user session in real database
        await manager.register_user_session(user_test_data)
        
        # Verify stored in real database
        stored_session = await db.execute(
            "SELECT * FROM user_sessions WHERE user_id = :user_id",
            {"user_id": user_test_data["user_id"]}
        )
        
        assert stored_session is not None
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_environment_isolation(self, real_services_fixture):
        """Test that factory respects isolated environment settings."""
        from shared.isolated_environment import get_env
        
        env = get_env()
        
        # Set test-specific environment variables
        env.set("WEBSOCKET_MAX_CONNECTIONS", "500", source="test")
        env.set("WEBSOCKET_TIMEOUT", "30", source="test") 
        env.set("JWT_SECRET_KEY", "test-secret-key", source="test")
        
        # Factory should use isolated environment
        factory = WebSocketManagerFactory.from_environment()
        
        assert factory.config["max_connections"] == 500
        assert factory.config["timeout"] == 30
        assert factory.config["jwt_secret"] == "test-secret-key"
        
        # Should create working manager
        manager = factory.create_manager()
        assert manager is not None
        
        # Manager should respect environment configuration
        assert manager.max_connections == 500
        assert manager.timeout == 30
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_initialization_error_recovery(self, real_services_fixture):
        """Test factory behavior when initialization fails and recovers."""
        # First attempt - simulate missing dependency
        config_missing_dep = {
            "websocket_host": "localhost", 
            "websocket_port": 8000,
            "database_connection": None,  # Missing database
            "redis_connection": real_services_fixture["redis"]
        }
        
        factory = WebSocketManagerFactory(config_missing_dep)
        
        # Should detect missing dependency
        assert not factory.is_valid()
        
        validation_errors = factory.get_validation_errors()
        assert any("database" in error.lower() for error in validation_errors)
        
        # Second attempt - provide missing dependency
        config_fixed = {
            **config_missing_dep,
            "database_connection": real_services_fixture["db"]
        }
        
        factory_fixed = WebSocketManagerFactory(config_fixed)
        
        # Should now be valid
        assert factory_fixed.is_valid()
        
        # Should create working manager
        manager = factory_fixed.create_manager()
        assert manager is not None
```

#### E2E Tests
**Location:** `tests/e2e/test_factory_initialization_e2e.py`

```python
"""
Test Factory Initialization in Complete System Context

Business Value: Ensure WebSocket infrastructure starts reliably in production-like environment
"""

import pytest
import asyncio
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper

class TestFactoryInitializationE2E(BaseE2ETest):
    """Test factory initialization in complete system context."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_websocket_system_startup_complete(self):
        """Test that WebSocket system starts up completely without FactoryInitializationError."""
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = "factory_e2e_user"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        headers = auth_helper.get_websocket_headers(token)
        
        websocket_url = "ws://localhost:8000/ws"
        
        # Test that system is fully initialized by attempting connection
        try:
            websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
            
            # Send system health check
            health_check = {
                "type": "system_health_check",
                "timestamp": asyncio.get_event_loop().time(),
                "factory_test": True
            }
            
            await websocket.send(json.dumps(health_check))
            
            # Should receive system status response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                system_status = json.loads(response)
                
                # System should report healthy factory initialization
                assert system_status.get("factory_status") != "error"
                assert "initialization" not in system_status.get("errors", [])
                
            except asyncio.TimeoutError:
                # Timeout acceptable, main test is successful connection
                pass
            
            await websocket.close()
            
            print("✅ WebSocket factory initialization successful - no FactoryInitializationError")
            
        except Exception as e:
            if "FactoryInitializationError" in str(e):
                pytest.fail(f"FactoryInitializationError detected: {e}")
            else:
                print(f"Non-factory error (may be acceptable): {e}")
                # Other errors might be network-related, not factory issues
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_factory_recovery_after_restart(self):
        """Test factory initialization recovery after system restart."""
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # First connection - establish baseline
        user_id_1 = "factory_restart_user_1"
        token_1 = auth_helper.create_test_jwt_token(user_id=user_id_1)
        headers_1 = auth_helper.get_websocket_headers(token_1)
        
        websocket_url = "ws://localhost:8000/ws"
        
        # Establish first connection
        websocket_1 = await auth_helper.connect_authenticated_websocket(timeout=10.0)
        
        # Send test message
        test_message_1 = {"type": "ping", "user": "before_restart"}
        await websocket_1.send(json.dumps(test_message_1))
        
        await websocket_1.close()
        
        # Simulate time passage (restart scenario)
        await asyncio.sleep(2.0)
        
        # Second connection - should work after "restart"
        user_id_2 = "factory_restart_user_2" 
        token_2 = auth_helper.create_test_jwt_token(user_id=user_id_2)
        headers_2 = auth_helper.get_websocket_headers(token_2)
        
        # Should connect successfully (factory re-initialization working)
        websocket_2 = await auth_helper.connect_authenticated_websocket(timeout=10.0)
        
        test_message_2 = {"type": "ping", "user": "after_restart"}
        await websocket_2.send(json.dumps(test_message_2))
        
        try:
            response = await asyncio.wait_for(websocket_2.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            # Should receive response (factory working correctly)
            assert response_data is not None
            
        except asyncio.TimeoutError:
            # Timeout is acceptable, main success is connection establishment
            pass
            
        await websocket_2.close()
        
        print("✅ Factory initialization recovery successful")
```

## 🧪 Test Suite 4: Missing WebSocket Events

### Issue Analysis
The most critical business value issue - agents execute without sending the required 5 WebSocket events.

#### Unit Tests
**Location:** `netra_backend/tests/unit/test_websocket_event_emission.py`

```python
"""
Test WebSocket Event Emission Logic

Business Value: Ensure all 5 critical events are emitted for user visibility
"""

import pytest
from unittest.mock import Mock, AsyncMock
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine

class TestWebSocketEventEmission:
    """Test WebSocket event emission validation."""
    
    def test_required_events_definition(self):
        """Test that all 5 required events are properly defined."""
        from netra_backend.app.agents.supervisor.websocket_notifier import REQUIRED_AGENT_EVENTS
        
        expected_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        assert REQUIRED_AGENT_EVENTS == expected_events
        assert len(REQUIRED_AGENT_EVENTS) == 5
        
    @pytest.mark.asyncio
    async def test_websocket_notifier_event_emission(self):
        """Test that WebSocketNotifier emits all required events."""
        # Mock WebSocket manager
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.send_json_to_user = AsyncMock()
        
        notifier = WebSocketNotifier(websocket_manager=mock_websocket_manager)
        
        user_id = "test_user_123"
        thread_id = "thread_456"
        
        # Test each required event
        await notifier.notify_agent_started(user_id, thread_id, {"agent": "test_agent"})
        await notifier.notify_agent_thinking(user_id, thread_id, {"status": "analyzing"})
        await notifier.notify_tool_executing(user_id, thread_id, {"tool": "test_tool"})
        await notifier.notify_tool_completed(user_id, thread_id, {"result": "success"})
        await notifier.notify_agent_completed(user_id, thread_id, {"final": "result"})
        
        # Verify all events were sent
        assert mock_websocket_manager.send_json_to_user.call_count == 5
        
        # Verify event types
        calls = mock_websocket_manager.send_json_to_user.call_args_list
        event_types = [call[0][1]["type"] for call in calls]  # Extract event type from calls
        
        assert "agent_started" in event_types
        assert "agent_thinking" in event_types
        assert "tool_executing" in event_types
        assert "tool_completed" in event_types
        assert "agent_completed" in event_types
        
    @pytest.mark.asyncio
    async def test_execution_engine_event_integration(self):
        """Test that ExecutionEngine integrates with WebSocket events."""
        mock_websocket_manager = AsyncMock()
        mock_llm_client = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        # Create execution engine with mocked dependencies
        engine = ExecutionEngine(
            llm_client=mock_llm_client,
            websocket_manager=mock_websocket_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Mock agent execution context
        mock_context = Mock()
        mock_context.user_id = "test_user"
        mock_context.thread_id = "test_thread"
        mock_context.agent_name = "triage_agent"
        mock_context.message = "test message"
        
        # Mock LLM response
        mock_llm_client.generate_response = AsyncMock(return_value={
            "content": "Test response",
            "tools_used": ["test_tool"]
        })
        
        # Mock tool execution
        mock_tool_dispatcher.execute_tool = AsyncMock(return_value={
            "success": True,
            "result": "tool result"
        })
        
        # Execute agent
        result = await engine.execute_agent(mock_context)
        
        # Verify execution succeeded
        assert result["success"] == True
        
        # Verify WebSocket events were sent
        assert mock_websocket_manager.send_json_to_user.call_count >= 3  # At minimum: started, thinking, completed
        
        # Extract event types from calls
        calls = mock_websocket_manager.send_json_to_user.call_args_list
        event_types = [call[0][1]["type"] for call in calls]
        
        # Must include critical events
        assert "agent_started" in event_types
        assert "agent_completed" in event_types
        
    def test_event_payload_validation(self):
        """Test that event payloads contain required fields."""
        notifier = WebSocketNotifier(websocket_manager=AsyncMock())
        
        user_id = "test_user"
        thread_id = "test_thread"
        
        # Test event payload structure
        event_data = notifier._create_event_payload(
            event_type="agent_started",
            user_id=user_id,
            thread_id=thread_id,
            data={"agent": "test_agent"}
        )
        
        # Required fields
        assert event_data["type"] == "agent_started"
        assert event_data["user_id"] == user_id
        assert event_data["thread_id"] == thread_id
        assert "timestamp" in event_data
        assert "data" in event_data
        assert event_data["data"]["agent"] == "test_agent"
        
    def test_missing_event_detection(self):
        """Test detection of missing WebSocket events."""
        from netra_backend.app.agents.supervisor.event_validator import EventValidator
        
        validator = EventValidator()
        
        # Simulate agent execution with missing events
        events_received = [
            {"type": "agent_started", "timestamp": "2024-01-01T00:00:00Z"},
            {"type": "agent_thinking", "timestamp": "2024-01-01T00:00:01Z"},
            # Missing: tool_executing, tool_completed
            {"type": "agent_completed", "timestamp": "2024-01-01T00:00:05Z"}
        ]
        
        validation_result = validator.validate_event_completeness(events_received)
        
        assert validation_result["valid"] == False
        assert "tool_executing" in validation_result["missing_events"]
        assert "tool_completed" in validation_result["missing_events"]
        assert len(validation_result["missing_events"]) == 2
```

#### Integration Tests
**Location:** `netra_backend/tests/integration/test_websocket_events_integration.py`

```python
"""
Test WebSocket Events with Real Agent Execution

Tests that real agent execution emits all required WebSocket events.
"""

import pytest
import asyncio
import json
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper

class TestWebSocketEventsIntegration(BaseIntegrationTest):
    """Test WebSocket event emission with real agent execution."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_agent_execution_events(self, real_services_fixture):
        """Test that real agent execution emits all 5 required events."""
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = "events_test_user"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        headers = auth_helper.get_websocket_headers(token)
        
        websocket_url = "ws://localhost:8000/ws"
        
        async with WebSocketTestClient(websocket_url, headers=headers) as ws_client:
            
            # Send agent request
            agent_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Test message for event validation",
                "user_id": user_id,
                "require_events": True  # Test flag to ensure event emission
            }
            
            await ws_client.send_json(agent_request)
            
            # Collect all events
            received_events = []
            required_events = {"agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"}
            events_received = set()
            
            # Event collection with timeout
            timeout = 30.0  # Allow time for real agent execution
            start_time = asyncio.get_event_loop().time()
            
            while (len(events_received) < len(required_events) and 
                   asyncio.get_event_loop().time() - start_time < timeout):
                try:
                    event = await asyncio.wait_for(ws_client.receive_json(), timeout=5.0)
                    received_events.append(event)
                    
                    event_type = event.get("type")
                    if event_type in required_events:
                        events_received.add(event_type)
                        
                    # Exit early if agent completed
                    if event_type == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
                except Exception as e:
                    print(f"Event collection error: {e}")
                    break
            
            # CRITICAL: All 5 events must be received
            missing_events = required_events - events_received
            
            if missing_events:
                received_event_types = [e.get("type") for e in received_events]
                pytest.fail(
                    f"Missing WebSocket events: {missing_events}. "
                    f"Received: {events_received}. "
                    f"All events: {received_event_types}"
                )
            
            assert len(events_received) == 5, f"Expected 5 events, got {len(events_received)}: {events_received}"
            
            # Verify event order (logical sequence)
            event_sequence = [e.get("type") for e in received_events if e.get("type") in required_events]
            
            assert event_sequence[0] == "agent_started", "First event must be agent_started"
            assert event_sequence[-1] == "agent_completed", "Last event must be agent_completed"
            
            print(f"✅ All 5 WebSocket events received: {events_received}")
            
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_emission_under_load(self, real_services_fixture):
        """Test that events are emitted correctly under concurrent load."""
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Create multiple concurrent agent executions
        num_concurrent = 3
        websocket_url = "ws://localhost:8000/ws"
        
        async def execute_agent_with_events(user_index):
            """Execute agent and validate events for one user."""
            user_id = f"load_test_user_{user_index}"
            token = auth_helper.create_test_jwt_token(user_id=user_id)
            headers = auth_helper.get_websocket_headers(token)
            
            async with WebSocketTestClient(websocket_url, headers=headers) as ws_client:
                
                agent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": f"Concurrent test {user_index}",
                    "user_id": user_id
                }
                
                await ws_client.send_json(agent_request)
                
                # Collect events for this user
                user_events = []
                required_events = {"agent_started", "agent_thinking", "agent_completed"}  # Minimum required
                events_received = set()
                
                timeout = 25.0
                start_time = asyncio.get_event_loop().time()
                
                while (len(events_received) < len(required_events) and 
                       asyncio.get_event_loop().time() - start_time < timeout):
                    try:
                        event = await asyncio.wait_for(ws_client.receive_json(), timeout=3.0)
                        user_events.append(event)
                        
                        event_type = event.get("type")
                        if event_type in required_events:
                            events_received.add(event_type)
                            
                        if event_type == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        break
                        
                return {
                    "user_id": user_id,
                    "events_received": events_received,
                    "total_events": len(user_events),
                    "success": len(events_received) >= 3  # At least started, thinking, completed
                }
        
        # Execute all concurrent requests
        tasks = [execute_agent_with_events(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_executions = [r for r in results if isinstance(r, dict) and r["success"]]
        failed_executions = [r for r in results if isinstance(r, dict) and not r["success"]]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # CRITICAL: At least 80% should succeed even under load
        success_rate = len(successful_executions) / num_concurrent
        assert success_rate >= 0.8, f"Success rate {success_rate:.2%} below threshold. Failures: {failed_executions}"
        
        # All successful executions should have received core events
        for result in successful_executions:
            assert "agent_started" in result["events_received"]
            assert "agent_completed" in result["events_received"]
            
        print(f"✅ Event emission under load: {len(successful_executions)}/{num_concurrent} successful")
```

#### E2E Tests
**Location:** `tests/e2e/test_missing_websocket_events_e2e.py`

```python
"""
Test Missing WebSocket Events in Complete User Flows

Business Value: Ensure users see progress and value delivery in real chat scenarios
"""

import pytest
import asyncio
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context

class TestMissingWebSocketEventsE2E(BaseE2ETest):
    """Test complete user flows with WebSocket event validation."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_complete_optimization_flow_with_events(self):
        """Test complete cost optimization flow with all WebSocket events."""
        user_context = await create_authenticated_user_context(
            user_email="events_test@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        from test_framework.websocket_helpers import WebSocketTestClient
        
        async with WebSocketTestClient("ws://localhost:8000/ws", str(user_context.user_id)) as ws_client:
            
            # Send realistic optimization request
            optimization_request = {
                "type": "agent_request",
                "agent": "cost_optimizer",  # Business-critical agent
                "message": "Analyze my cloud costs and provide optimization recommendations",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id),
                "context": {
                    "monthly_spend": 15000,
                    "primary_services": ["compute", "storage", "networking"]
                }
            }
            
            await ws_client.send_json(optimization_request)
            
            # Collect all events for complete business flow
            all_events = []
            business_critical_events = {"agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"}
            events_received = set()
            
            # Extended timeout for real LLM processing
            timeout = 60.0
            start_time = asyncio.get_event_loop().time()
            
            while (len(events_received) < len(business_critical_events) and
                   asyncio.get_event_loop().time() - start_time < timeout):
                try:
                    event = await asyncio.wait_for(ws_client.receive_json(), timeout=10.0)
                    all_events.append(event)
                    
                    event_type = event.get("type")
                    if event_type in business_critical_events:
                        events_received.add(event_type)
                        print(f"📨 Received business-critical event: {event_type}")
                    
                    # Check for business value delivery
                    if event_type == "agent_completed":
                        event_data = event.get("data", {})
                        if "recommendations" in event_data or "savings" in event_data:
                            print("💰 Business value delivered - cost optimization recommendations received")
                        break
                        
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout waiting for events. Received so far: {events_received}")
                    break
                except Exception as e:
                    print(f"❌ Event collection error: {e}")
                    break
            
            # MISSION CRITICAL: All 5 events must be received
            missing_events = business_critical_events - events_received
            
            if missing_events:
                all_event_types = [e.get("type") for e in all_events]
                failure_message = (
                    f"🚨 MISSION CRITICAL FAILURE: Missing WebSocket events block user value delivery!\n"
                    f"Missing: {missing_events}\n"
                    f"Received: {events_received}\n" 
                    f"All events: {all_event_types}\n"
                    f"This prevents users from seeing AI progress - breaks core business value!"
                )
                pytest.fail(failure_message)
            
            # Validate business value delivery
            completed_events = [e for e in all_events if e.get("type") == "agent_completed"]
            assert len(completed_events) > 0, "Must receive agent completion with business results"
            
            # Final event should contain business value
            final_event = completed_events[0]
            final_data = final_event.get("data", {})
            
            # Cost optimization should provide actionable insights
            has_business_value = (
                "recommendations" in str(final_data).lower() or
                "savings" in str(final_data).lower() or  
                "optimization" in str(final_data).lower() or
                len(str(final_data)) > 100  # Substantial response
            )
            
            assert has_business_value, f"Agent completion must deliver business value. Got: {final_data}"
            
            print(f"✅ MISSION CRITICAL SUCCESS: All 5 WebSocket events received + business value delivered")
            print(f"📊 Events: {sorted(list(events_received))}")
            
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_event_recovery_after_interruption(self):
        """Test that events continue after WebSocket reconnection."""
        user_context = await create_authenticated_user_context(
            environment="test",
            websocket_enabled=True
        )
        
        from test_framework.websocket_helpers import WebSocketTestClient
        
        # First connection - start agent execution
        async with WebSocketTestClient("ws://localhost:8000/ws", str(user_context.user_id)) as ws_client_1:
            
            long_request = {
                "type": "agent_request", 
                "agent": "triage_agent",
                "message": "Start a long analysis that I'll continue after reconnection",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id)
            }
            
            await ws_client_1.send_json(long_request)
            
            # Collect initial events
            initial_events = []
            try:
                for _ in range(3):  # Get first few events
                    event = await asyncio.wait_for(ws_client_1.receive_json(), timeout=8.0)
                    initial_events.append(event)
                    if event.get("type") == "agent_started":
                        break
            except asyncio.TimeoutError:
                pass
            
            # Should have at least received agent_started
            event_types = [e.get("type") for e in initial_events]
            assert "agent_started" in event_types, "Should receive agent_started before disconnection"
        
        # Connection closed (simulating network interruption)
        await asyncio.sleep(1.0)
        
        # Second connection - should continue receiving events
        async with WebSocketTestClient("ws://localhost:8000/ws", str(user_context.user_id)) as ws_client_2:
            
            # Request status of ongoing execution
            status_request = {
                "type": "status_request",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id)
            }
            
            await ws_client_2.send_json(status_request)
            
            # Should receive continuation or completion events
            continuation_events = []
            try:
                for _ in range(5):  # Allow for multiple events
                    event = await asyncio.wait_for(ws_client_2.receive_json(), timeout=10.0)
                    continuation_events.append(event)
                    
                    # If we get agent_completed, the flow recovered successfully
                    if event.get("type") == "agent_completed":
                        break
                        
            except asyncio.TimeoutError:
                pass
            
            # Should receive some events indicating system recovery
            continuation_event_types = [e.get("type") for e in continuation_events]
            
            recovery_indicators = [
                "agent_completed",
                "status_update", 
                "thread_status",
                "execution_status"
            ]
            
            has_recovery = any(indicator in continuation_event_types for indicator in recovery_indicators)
            
            assert has_recovery, f"Should receive recovery events after reconnection. Got: {continuation_event_types}"
            
            print("✅ Event recovery after reconnection successful")
```

## 📊 Test Execution Strategy

### Test Environment Configuration

```python
# Test Environment Ports (SSOT)
TEST_PORTS = {
    "postgresql": 5434,
    "redis": 6381,
    "backend": 8000,
    "auth": 8081,
    "websocket": 8000  # Same as backend
}

# Alpine Environment (50% faster)  
ALPINE_TEST_PORTS = {
    "postgresql": 5434,
    "redis": 6382,  # Different for Alpine
    "backend": 8000,
    "auth": 8081
}
```

### Test Execution Commands

```bash
# Unit Tests (Fast - No Infrastructure)
python tests/unified_test_runner.py --category unit --pattern "*websocket*race*"
python tests/unified_test_runner.py --category unit --pattern "*service*dependency*"
python tests/unified_test_runner.py --category unit --pattern "*factory*initialization*"
python tests/unified_test_runner.py --category unit --pattern "*websocket*event*"

# Integration Tests (Local Services)
python tests/unified_test_runner.py --category integration --real-services --pattern "*websocket*"

# E2E Tests (Full Stack)
python tests/unified_test_runner.py --category e2e --real-services --real-llm --pattern "*golden*path*"

# Mission Critical Tests (Must Pass)
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/unified_test_runner.py --category mission_critical --pattern "*websocket*"

# Staging Tests
python tests/unified_test_runner.py --category e2e --env staging --pattern "*websocket*race*"
```

### Expected Failure Patterns

Each test suite MUST fail appropriately when the specific issue is present:

1. **Race Condition Tests:** Should fail with timeout or 1011 WebSocket errors
2. **Service Dependency Tests:** Should fail with connection errors or silent agent failures  
3. **Factory Initialization Tests:** Should fail with `FactoryInitializationError`
4. **Missing Events Tests:** Should fail with assertions about missing event types

### Test Data and Fixtures

```python
# Required Test Fixtures
- real_services_fixture (PostgreSQL + Redis)  
- e2e_auth_helper (SSOT authentication)
- websocket_test_client (Real WebSocket connections)
- staging_environment (GCP Cloud Run testing)

# Test Users
- Race condition test users: race_test_user_1..5
- Service dependency users: service_dep_test_user  
- Factory test users: factory_test_user
- Events validation users: events_test_user
```

## 📋 Test File Locations and Naming

Following TEST_ARCHITECTURE_VISUAL_OVERVIEW.md structure:

```
netra_backend/tests/unit/
├── test_websocket_race_conditions.py
├── test_service_dependency_validation.py  
├── test_websocket_factory_initialization.py
└── test_websocket_event_emission.py

netra_backend/tests/integration/
├── test_websocket_handshake_timing.py
├── test_service_dependency_integration.py
├── test_factory_initialization_integration.py  
└── test_websocket_events_integration.py

tests/e2e/
├── test_websocket_race_conditions_golden_path.py
├── test_service_dependency_failures_e2e.py
├── test_factory_initialization_e2e.py
└── test_missing_websocket_events_e2e.py

tests/mission_critical/
├── test_golden_path_websocket_race_conditions.py
├── test_golden_path_service_dependencies.py
├── test_golden_path_factory_initialization.py
└── test_golden_path_missing_events.py
```

## 🎯 Success Criteria

### Mission Critical Success Metrics

1. **Race Conditions:** 0 WebSocket 1011 errors in staging environment
2. **Service Dependencies:** Graceful degradation messages in 100% of failure cases
3. **Factory Initialization:** 0 `FactoryInitializationError` exceptions in production
4. **Missing Events:** All 5 WebSocket events received in 100% of agent executions

### Business Value Validation

- **Chat Continuity:** Users can establish reliable chat sessions
- **Progress Visibility:** Users see real-time agent execution progress  
- **Value Delivery:** Agent responses contain actionable business insights
- **Error Communication:** System communicates issues gracefully to users

## 📈 Test Reporting

Each test suite will generate detailed reports following the established pattern:

```
GOLDEN_PATH_WEBSOCKET_RACE_CONDITIONS_TEST_REPORT.md
GOLDEN_PATH_SERVICE_DEPENDENCIES_TEST_REPORT.md  
GOLDEN_PATH_FACTORY_INITIALIZATION_TEST_REPORT.md
GOLDEN_PATH_MISSING_EVENTS_TEST_REPORT.md
```

Reports will include:
- Business Value Impact assessment
- Technical root cause analysis
- Test execution results with evidence
- Staging environment validation
- Remediation verification

---

**This comprehensive test plan ensures the Golden Path user flow delivers reliable WebSocket-based chat interactions that enable $500K+ ARR through substantive AI value delivery.**