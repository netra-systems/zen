"""
E2E Test: Complete Authenticated Chat Workflow - MISSION CRITICAL Revenue Protection

BUSINESS IMPACT: Tests the complete chat workflow that generates 90% of platform revenue.
This E2E test validates the end-to-end golden path from user authentication to agent response.

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - Complete Chat Infrastructure  
- Business Goal: Revenue Protection - Ensure golden path delivers $500K+ ARR
- Value Impact: Validates complete authenticated chat workflow customers depend on
- Strategic Impact: Tests the PRIMARY VALUE-GENERATING FLOW of the entire platform

CRITICAL SUCCESS METRICS:
✅ User authenticates successfully with JWT/OAuth
✅ WebSocket connection established with auth headers  
✅ Agent execution triggered with real LLM integration
✅ All 5 critical WebSocket events delivered (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
✅ Real agent response with business value delivered to user
✅ End-to-end timing < 30 seconds for good UX

COMPLIANCE:
@compliance CLAUDE.md - E2E AUTH MANDATORY (Section 7.3) 
@compliance CLAUDE.md - WebSocket events enable substantive chat (Section 6)
@compliance CLAUDE.md - NO MOCKS in E2E tests
@compliance CLAUDE.md - Real services, real LLM for E2E
"""

import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# SSOT Imports - Authentication and Golden Path
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.ssot.websocket_golden_path_helpers import (
    WebSocketGoldenPathHelper,
    GoldenPathTestConfig,
    assert_golden_path_success
)
from test_framework.ssot.agent_event_validators import (
    AgentEventValidator,
    CriticalAgentEventType,
    assert_critical_events_received
)

# SSOT Imports - Types
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Test Framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.e2e
@pytest.mark.staging_compatible
class TestCompleteAuthenticatedChatWorkflowE2E(SSotBaseTestCase):
    """
    MISSION CRITICAL E2E Tests for Complete Authenticated Chat Workflow.
    
    These tests validate the complete golden path that customers experience
    when using the platform for AI-powered chat interactions.
    
    REVENUE PROTECTION: If these tests fail, the core business value is broken.
    """
    
    def setup_method(self):
        """Set up E2E test environment."""
        super().setup_method()
        
        # Initialize SSOT helpers
        self.environment = self.get_test_environment()
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.golden_path_helper = WebSocketGoldenPathHelper(environment=self.environment)
        
        # Test configuration optimized for environment
        self.config = GoldenPathTestConfig.for_environment(self.environment)
        
        # Track test metrics
        self.test_start_time = time.time()
        self.business_value_delivered = False
        
        print(f"\n🚀 MISSION CRITICAL E2E TEST STARTING - Environment: {self.environment}")
        print(f"📊 Target: Complete authenticated chat workflow with real services")
        print(f"💰 Business Impact: Validates $500K+ ARR revenue-generating flow")
    
    def teardown_method(self):
        """Clean up E2E test resources."""
        test_duration = time.time() - self.test_start_time
        
        if self.business_value_delivered:
            print(f"✅ MISSION CRITICAL E2E TEST PASSED - Duration: {test_duration:.2f}s")
            print(f"💰 Revenue-generating chat workflow validated successfully")
        else:
            print(f"❌ MISSION CRITICAL E2E TEST FAILED - Duration: {test_duration:.2f}s")
            print(f"🚨 REVENUE IMPACT: Core chat workflow is broken!")
        
        super().teardown_method()
    
    @pytest.mark.asyncio
    async def test_complete_authenticated_chat_workflow_golden_path(self):
        """
        MISSION CRITICAL: Complete authenticated chat workflow E2E test.
        
        Tests the complete golden path from authentication to agent response
        that generates 90% of platform revenue through chat interactions.
        
        BUSINESS IMPACT: If this test fails, customers cannot access core value.
        """
        print("\n🧪 MISSION CRITICAL: Testing complete authenticated chat workflow...")
        
        workflow_start = time.time()
        
        # STEP 1: User Authentication (MANDATORY for E2E)
        print("🔐 STEP 1: Authenticating user with JWT/OAuth...")
        
        user_context = await create_authenticated_user_context(
            user_email=f"golden_path_e2e_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "agent_execution", "websocket"],
            websocket_enabled=True
        )
        
        # Validate authentication context
        assert user_context.user_id is not None, "User ID must be present"
        assert user_context.websocket_client_id is not None, "WebSocket client ID required"
        assert "jwt_token" in user_context.agent_context, "JWT token required for auth"
        
        jwt_token = user_context.agent_context["jwt_token"]
        assert len(jwt_token) > 50, "JWT token should be substantial"
        
        auth_time = time.time() - workflow_start
        print(f"✅ User authenticated successfully in {auth_time:.2f}s")
        print(f"👤 User ID: {user_context.user_id}")
        print(f"🔗 Thread ID: {user_context.thread_id}")
        
        # STEP 2: WebSocket Connection with Authentication
        print("🔌 STEP 2: Establishing authenticated WebSocket connection...")
        
        connection_start = time.time()
        
        # Get authentication headers for WebSocket
        ws_headers = self.ws_auth_helper.get_websocket_headers(jwt_token)
        ws_headers.update({
            "X-User-ID": str(user_context.user_id),
            "X-Thread-ID": str(user_context.thread_id),
            "X-Request-ID": str(user_context.request_id),
            "X-WebSocket-Client-ID": str(user_context.websocket_client_id)
        })
        
        # Connect to WebSocket with authentication
        websocket_url = self.ws_auth_helper.config.websocket_url
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    websocket_url,
                    additional_headers=ws_headers,
                    ping_interval=30,
                    ping_timeout=15,
                    close_timeout=10
                ),
                timeout=self.config.connection_timeout
            )
            
            connection_time = time.time() - connection_start
            print(f"✅ WebSocket connected successfully in {connection_time:.2f}s")
            print(f"🌐 Connected to: {websocket_url}")
            
        except Exception as e:
            pytest.fail(f"CRITICAL FAILURE: WebSocket connection failed: {e}")
        
        try:
            # STEP 3: Send Chat Request (Business Value Trigger)
            print("💬 STEP 3: Sending authenticated chat request...")
            
            chat_request = {
                "type": "chat_message",
                "content": "Please analyze sample business data and provide strategic insights with actionable recommendations for improving customer retention and revenue growth",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "request_id": str(user_context.request_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_id": f"golden_path_msg_{uuid.uuid4().hex[:8]}",
                "business_context": "E2E test validating revenue-generating chat workflow"
            }
            
            await websocket.send(json.dumps(chat_request))
            request_time = time.time() - workflow_start
            print(f"📤 Chat request sent at {request_time:.2f}s")
            print(f"📝 Request: Business data analysis with strategic insights")
            
            # STEP 4: Agent Event Monitoring (CRITICAL WebSocket Events)
            print("📊 STEP 4: Monitoring critical agent events...")
            
            event_validator = AgentEventValidator(
                user_context=user_context,
                strict_mode=True,
                timeout_seconds=self.config.event_timeout
            )
            
            # Required critical events for business value
            required_events = {
                CriticalAgentEventType.AGENT_STARTED.value,
                CriticalAgentEventType.AGENT_THINKING.value,
                CriticalAgentEventType.TOOL_EXECUTING.value,
                CriticalAgentEventType.TOOL_COMPLETED.value,
                CriticalAgentEventType.AGENT_COMPLETED.value
            }
            
            received_events = []
            received_event_types = set()
            event_monitoring_start = time.time()
            
            print(f"🔍 Monitoring for {len(required_events)} critical events (timeout: {self.config.event_timeout}s)")
            
            while time.time() - event_monitoring_start < self.config.event_timeout:
                try:
                    # Wait for WebSocket message
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    message_data = json.loads(message)
                    
                    # Process agent event
                    if message_data.get("type") in required_events:
                        event_type = message_data["type"]
                        received_events.append(message_data)
                        received_event_types.add(event_type)
                        
                        event_time = time.time() - workflow_start
                        print(f"📨 Received: {event_type} at {event_time:.2f}s")
                        
                        # Record in validator
                        from test_framework.ssot.agent_event_validators import WebSocketEventMessage
                        event = WebSocketEventMessage.from_dict(message_data)
                        event_validator.record_event(event)
                        
                        # Check if we have all required events
                        if required_events.issubset(received_event_types):
                            print("✅ All critical agent events received!")
                            break
                    
                    # Also log other events for debugging
                    elif message_data.get("type"):
                        event_time = time.time() - workflow_start
                        print(f"📥 Other event: {message_data['type']} at {event_time:.2f}s")
                    
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Warning: Event processing error: {e}")
                    continue
            
            # STEP 5: Validate Critical Business Events
            print("✅ STEP 5: Validating critical business events...")
            
            validation_result = event_validator.perform_full_validation()
            
            # Critical business validation
            assert validation_result.is_valid, f"Event validation failed: {validation_result.error_message}"
            assert len(validation_result.missing_critical_events) == 0, f"Missing critical events: {validation_result.missing_critical_events}"
            assert validation_result.business_value_score >= 75.0, f"Business value score too low: {validation_result.business_value_score}"
            
            events_time = time.time() - workflow_start
            print(f"✅ Critical events validated in {events_time:.2f}s")
            print(f"📊 Business Value Score: {validation_result.business_value_score:.1f}%")
            print(f"🎯 Events Received: {len(received_events)}/{len(required_events)}")
            
            # STEP 6: Validate Agent Response Quality
            print("🎯 STEP 6: Validating agent response quality...")
            
            # Look for agent_completed event with response
            agent_response = None
            for event in received_events:
                if event.get("type") == "agent_completed":
                    agent_response = event.get("response") or event.get("message")
                    break
            
            if agent_response:
                # Validate response has business value content
                assert len(agent_response) > 50, "Agent response should be substantial"
                
                # Check for business-relevant keywords
                business_keywords = ["insights", "recommendations", "analysis", "strategy", "improve", "growth", "revenue"]
                found_keywords = [kw for kw in business_keywords if kw.lower() in agent_response.lower()]
                assert len(found_keywords) >= 2, f"Response should contain business value language: {found_keywords}"
                
                print(f"💡 Agent Response: {agent_response[:100]}...")
                print(f"🎯 Business Keywords Found: {found_keywords}")
                
                self.business_value_delivered = True
            else:
                print("⚠️ No agent response found in events")
            
            # STEP 7: Performance and UX Validation
            total_workflow_time = time.time() - workflow_start
            print(f"⏱️ STEP 7: Performance validation...")
            print(f"📊 Total Workflow Time: {total_workflow_time:.2f}s")
            
            # Business UX requirements
            assert total_workflow_time < 45.0, f"Workflow too slow for good UX: {total_workflow_time:.2f}s"
            assert auth_time < 5.0, f"Authentication too slow: {auth_time:.2f}s"
            assert connection_time < 10.0, f"WebSocket connection too slow: {connection_time:.2f}s"
            
            # STEP 8: Revenue Impact Assessment
            print("💰 STEP 8: Revenue impact assessment...")
            
            if self.business_value_delivered and total_workflow_time < 30.0 and len(received_events) >= 4:
                revenue_impact = "NO_IMPACT"  # Golden path working optimally
                print("🎉 EXCELLENT: Golden path delivers optimal customer experience")
            elif self.business_value_delivered and total_workflow_time < 45.0:
                revenue_impact = "LOW_IMPACT"  # Acceptable performance
                print("✅ GOOD: Golden path delivers acceptable customer experience")
            else:
                revenue_impact = "HIGH_IMPACT"  # Performance issues
                print("⚠️ WARNING: Golden path performance may impact customer satisfaction")
            
            print(f"📈 Revenue Impact Assessment: {revenue_impact}")
            
            # Final validation
            assert self.business_value_delivered, "CRITICAL: No business value delivered to user"
            assert len(received_events) >= 3, f"Insufficient agent events for good UX: {len(received_events)}"
            
        finally:
            # Clean up WebSocket connection
            if websocket and not websocket.closed:
                await websocket.close()
        
        print("🎉 MISSION CRITICAL E2E TEST COMPLETED SUCCESSFULLY!")
        print(f"✅ Complete authenticated chat workflow validated")
        print(f"💰 Revenue-generating golden path is working correctly")
    
    @pytest.mark.asyncio
    async def test_authenticated_chat_workflow_with_real_llm_integration(self):
        """
        CRITICAL: Authenticated chat workflow with real LLM integration.
        
        Tests that the complete workflow works with actual LLM integration
        to deliver real AI-powered responses to authenticated users.
        
        BUSINESS IMPACT: Validates the AI value proposition customers pay for.
        """
        print("\n🧪 CRITICAL: Testing authenticated chat with real LLM integration...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"llm_integration_e2e_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "llm_access", "agent_execution"],
            websocket_enabled=True
        )
        
        # STEP 2: Use Golden Path Helper for complete workflow
        async with self.golden_path_helper.authenticated_websocket_connection(user_context):
            # Send request that requires real LLM processing
            business_request = (
                "Please analyze the following business scenario and provide strategic recommendations: "
                "A SaaS company has 1000 customers, $100K MRR, 5% monthly churn rate, and wants to "
                "expand into enterprise market. What are the top 3 strategic priorities and "
                "implementation steps for the next 6 months?"
            )
            
            # Execute golden path flow with real LLM
            result = await self.golden_path_helper.execute_golden_path_flow(
                user_message=business_request,
                user_context=user_context,
                timeout=60.0  # Allow more time for real LLM processing
            )
            
            # Validate successful execution
            assert result.success, f"Golden path execution failed: {result.errors_encountered}"
            assert result.validation_result.is_valid, "Event validation failed"
            assert result.execution_metrics.business_value_score >= 70.0, "Insufficient business value"
            
            # Validate LLM-quality response
            events_with_responses = [
                event for event in result.events_received 
                if event.event_type == "agent_completed" and hasattr(event, 'data') and 
                ("response" in event.data or "message" in event.data)
            ]
            
            assert len(events_with_responses) > 0, "No agent response found"
            
            # Check response quality (should be substantial for real LLM)
            response_event = events_with_responses[0]
            response_text = response_event.data.get("response") or response_event.data.get("message", "")
            
            assert len(response_text) > 100, "LLM response should be substantial"
            assert any(keyword in response_text.lower() for keyword in ["strategy", "priority", "recommend", "implement"]), "Response should contain strategic business language"
            
            self.business_value_delivered = True
            
            print(f"✅ Real LLM integration successful")
            print(f"📊 Business Value Score: {result.execution_metrics.business_value_score:.1f}%")
            print(f"🤖 LLM Response Length: {len(response_text)} characters")
    
    @pytest.mark.asyncio
    async def test_chat_workflow_error_recovery_patterns(self):
        """
        CRITICAL: Chat workflow error recovery and resilience.
        
        Tests that the authenticated chat workflow can recover gracefully
        from common error scenarios while maintaining business value delivery.
        
        BUSINESS IMPACT: Ensures customer experience remains positive during edge cases.
        """
        print("\n🧪 CRITICAL: Testing chat workflow error recovery...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"error_recovery_e2e_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "error_recovery_test"],
            websocket_enabled=True
        )
        
        # STEP 2: Test workflow with challenging request
        challenging_request = (
            "Please analyze a dataset that doesn't exist and provide insights "
            "on quantum computing applications for medieval agriculture while "
            "calculating the ROI of unicorn investments"
        )
        
        async with self.golden_path_helper.authenticated_websocket_connection(user_context):
            # Execute workflow with error-prone request
            result = await self.golden_path_helper.execute_golden_path_flow(
                user_message=challenging_request,
                user_context=user_context,
                timeout=45.0
            )
            
            # Validate graceful handling (should not crash, may have limited success)
            if result.success:
                # Ideal case: system handled challenging request gracefully
                assert result.validation_result.is_valid
                self.business_value_delivered = True
                print("✅ System handled challenging request successfully")
                
            else:
                # Acceptable case: system failed gracefully with proper error handling
                assert len(result.errors_encountered) > 0, "Should have recorded error details"
                assert len(result.events_received) > 0, "Should have received some events even on failure"
                
                # Should still get agent_started event for good UX
                event_types = [event.event_type for event in result.events_received]
                assert "agent_started" in event_types, "Should get agent_started even on failure"
                
                print("✅ System failed gracefully with proper error handling")
                print(f"📊 Events received during failure: {len(result.events_received)}")
                print(f"🔍 Error details: {result.errors_encountered[:2]}")  # First 2 errors
            
            # Performance should still be reasonable
            assert result.execution_metrics.total_execution_time < 60.0, "Error handling should not cause excessive delays"


if __name__ == "__main__":
    """
    Run E2E tests for complete authenticated chat workflow.
    
    Usage:
        python -m pytest tests/e2e/test_complete_authenticated_chat_workflow_e2e.py -v
        python -m pytest tests/e2e/test_complete_authenticated_chat_workflow_e2e.py::TestCompleteAuthenticatedChatWorkflowE2E::test_complete_authenticated_chat_workflow_golden_path -v -s
    """
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))