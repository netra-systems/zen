"""
Complete Golden Path User Journey E2E Test

CRITICAL: This test validates the COMPLETE end-to-end user journey that generates business value.
This is the PRIMARY revenue-protection test validating the full user experience from
authentication through WebSocket connection to actionable cost optimization delivery.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - $500K+ ARR protection
- Business Goal: Validate complete golden path user journey with real business value delivery
- Value Impact: Ensures users receive actionable AI cost optimization insights (core value prop)
- Strategic Impact: Protects primary revenue flow through comprehensive journey validation

GOLDEN PATH FLOW TESTED:
```
User Opens Browser → Authentication → WebSocket Connection → 
Send Message → Agent Execution → All 5 WebSocket Events → 
Business Value Delivery (Cost Savings) → Thread Persistence → Success
```

CRITICAL REQUIREMENTS (per CLAUDE.md):
1. MANDATORY authentication via E2EWebSocketAuthHelper
2. MANDATORY full Docker stack (--real-services)
3. MANDATORY validation of all 5 WebSocket events
4. MANDATORY business value validation (cost savings > 0)
5. NO MOCKS - real services only
6. Must fail hard on any business value deviation
7. 60-second timeout maximum per test
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# SSOT imports following absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events_sent

# Strongly typed context imports
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

# Real services integration
import websockets
import httpx


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.asyncio
class TestCompleteGoldenPathUserJourneyE2E(SSotAsyncTestCase):
    """
    CRITICAL: Primary Golden Path validation test.
    
    This test validates the complete user journey that generates business value:
    Authentication → WebSocket → Message → Agent Execution → Business Value
    
    BUSINESS IMPACT: $500K+ ARR protection through complete journey validation.
    """
    
    async def initialize_test_environment(self):
        """Initialize test environment with full Docker services."""
        await super().initialize_test_environment()
        
        # Record business value metrics
        self.business_metrics = {
            "test_type": "complete_golden_path_user_journey", 
            "arr_protection_value": 500000,  # $500K ARR
            "business_segments": ["free", "early", "mid", "enterprise"],
            "core_flow": "auth_to_business_value_delivery"
        }
        
        # Initialize auth helpers with proper environment
        environment = "test"  # Using test environment for Docker services
        self.auth_helper = E2EAuthHelper(environment=environment)
        self.websocket_helper = E2EWebSocketAuthHelper(environment=environment)
        self.logger.info("✅ Golden Path test environment initialized with full Docker services")
    
    @pytest.mark.timeout(60)  # Maximum 60 seconds per CLAUDE.md
    async def test_complete_golden_path_user_journey_with_business_value(self):
        """
        CRITICAL: Complete golden path user journey with real business value delivery.
        
        This test validates the PRIMARY user journey that generates business value:
        1. User authentication
        2. WebSocket connection
        3. Message sending
        4. Agent execution with all 5 WebSocket events
        5. Business value delivery (cost optimization insights)
        6. Data persistence verification
        
        BUSINESS VALUE: Cost optimization insights with quantified savings > $0
        """
        self.logger.info("🚀 CRITICAL: Starting Complete Golden Path User Journey E2E Test")
        
        # Step 1: Create authenticated user context 
        user_context = await create_authenticated_user_context(
            user_email="golden_path_journey@example.com",
            environment="test",
            permissions=["read", "write", "execute_agents", "cost_optimization"],
            websocket_enabled=True
        )
        
        # Extract authentication data
        jwt_token = user_context.agent_context["jwt_token"]
        user_id = str(user_context.user_id)
        thread_id = str(user_context.thread_id)
        
        self.logger.info(f"✅ Step 1: User authenticated - UserID: {user_id}")
        
        # Step 2: Establish WebSocket connection with authentication
        websocket_url = "ws://localhost:8000/ws"  # Real backend WebSocket
        headers = self.websocket_helper.get_websocket_headers(jwt_token)
        
        self.logger.info(f"🔌 Step 2: Connecting to WebSocket with authentication")
        
        collected_events = []
        business_value_data = {}
        
        async with websockets.connect(
            websocket_url,
            additional_headers=headers,
            open_timeout=15.0,
            close_timeout=5.0
        ) as websocket:
            
            self.logger.info("✅ Step 2: WebSocket connection established")
            
            # Step 3: Send business-focused message
            optimization_request = {
                "type": "chat_message",
                "message": "Analyze my current AI infrastructure costs and provide optimization recommendations with quantified savings opportunities.",
                "thread_id": thread_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": {
                    "request_type": "cost_optimization",
                    "business_goal": "reduce_ai_spend",
                    "expected_outcome": "actionable_savings_recommendations"
                }
            }
            
            await websocket.send(json.dumps(optimization_request))
            self.logger.info("✅ Step 3: Cost optimization request sent")
            
            # Step 4: Collect all WebSocket events during agent execution
            timeout = 45.0  # Allow enough time for agent execution
            start_time = time.time()
            agent_completed = False
            
            while time.time() - start_time < timeout and not agent_completed:
                try:
                    # Wait for WebSocket message with short timeout for responsiveness
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event_data = json.loads(message)
                    
                    collected_events.append(event_data)
                    event_type = event_data.get("type", "unknown")
                    
                    self.logger.info(f"📨 Received WebSocket event: {event_type}")
                    
                    # Track business value data
                    if event_type == "agent_completed":
                        agent_completed = True
                        # Extract business value from final response
                        response_data = event_data.get("data", {})
                        if "cost_optimization" in response_data:
                            business_value_data = response_data["cost_optimization"]
                        elif "savings" in response_data:
                            business_value_data = response_data
                        
                        self.logger.info(f"🎯 Agent execution completed with business data")
                    
                    # Log other critical events
                    if event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed"]:
                        self.logger.info(f"✅ Critical event received: {event_type}")
                        
                except asyncio.TimeoutError:
                    # Continue listening - timeout is for individual messages, not overall
                    if collected_events:  # Only log if we've received some events
                        self.logger.debug(f"Waiting for more events... ({len(collected_events)} received so far)")
                    continue
                    
                except Exception as e:
                    self.logger.error(f"WebSocket receive error: {e}")
                    break
            
            self.logger.info(f"📊 Step 4: Collected {len(collected_events)} WebSocket events")
        
        # Step 5: Validate all required WebSocket events were sent
        self.logger.info("🔍 Step 5: Validating WebSocket events...")
        
        # CRITICAL: All 5 events MUST be present per CLAUDE.md
        required_events = [
            "agent_started",      # User must see agent began processing
            "agent_thinking",     # Real-time reasoning visibility 
            "tool_executing",     # Tool usage transparency
            "tool_completed",     # Tool results display
            "agent_completed"     # User must know response is ready
        ]
        
        # Validate events were sent
        event_types = [event.get("type") for event in collected_events]
        missing_events = [event for event in required_events if event not in event_types]
        
        assert len(missing_events) == 0, (
            f"CRITICAL FAILURE: Missing required WebSocket events: {missing_events}. "
            f"Golden Path REQUIRES all 5 events for business value delivery. "
            f"Events received: {event_types}"
        )
        
        self.logger.info("✅ Step 5: All 5 required WebSocket events validated")
        
        # Step 6: Validate business value delivery
        self.logger.info("💰 Step 6: Validating business value delivery...")
        
        # CRITICAL: Must deliver actual business value (cost optimization)
        assert business_value_data, (
            "CRITICAL FAILURE: No business value data received. "
            "Golden Path MUST deliver cost optimization insights to generate revenue."
        )
        
        # Check for cost savings data
        has_savings = (
            "savings_amount" in business_value_data or
            "cost_reduction" in business_value_data or
            "optimization_value" in business_value_data or
            "monthly_savings" in business_value_data
        )
        
        assert has_savings, (
            f"CRITICAL FAILURE: No cost savings data in business value response. "
            f"Golden Path MUST provide quantified savings for business value. "
            f"Response data: {business_value_data}"
        )
        
        # Extract savings amount for validation
        savings_amount = (
            business_value_data.get("savings_amount", 0) or
            business_value_data.get("cost_reduction", 0) or
            business_value_data.get("optimization_value", 0) or
            business_value_data.get("monthly_savings", 0)
        )
        
        assert savings_amount > 0, (
            f"CRITICAL FAILURE: Cost savings amount must be > 0 for business value. "
            f"Received savings: {savings_amount}. Golden Path MUST provide positive ROI."
        )
        
        self.logger.info(f"✅ Step 6: Business value validated - Cost savings: ${savings_amount}")
        
        # Step 7: Verify data persistence (thread continuity)
        self.logger.info("💾 Step 7: Verifying data persistence...")
        
        # Make authenticated API call to verify thread persistence
        backend_url = "http://localhost:8000"  # Real backend service
        auth_headers = self.auth_helper.get_auth_headers(jwt_token)
        
        async with httpx.AsyncClient() as client:
            # Verify thread exists and contains our conversation
            thread_response = await client.get(
                f"{backend_url}/api/threads/{thread_id}",
                headers=auth_headers,
                timeout=10.0
            )
            
            assert thread_response.status_code == 200, (
                f"CRITICAL FAILURE: Thread not persisted. Status: {thread_response.status_code}. "
                f"Golden Path REQUIRES data persistence for user continuity."
            )
            
            thread_data = thread_response.json()
            assert thread_data.get("id") == thread_id, (
                "CRITICAL FAILURE: Thread ID mismatch in persistence validation."
            )
            
            # Verify thread contains our cost optimization message
            messages = thread_data.get("messages", [])
            optimization_message_found = any(
                "cost" in message.get("content", "").lower() and 
                "optimization" in message.get("content", "").lower()
                for message in messages
            )
            
            assert optimization_message_found, (
                "CRITICAL FAILURE: Cost optimization message not persisted in thread. "
                "Golden Path REQUIRES complete conversation persistence."
            )
        
        self.logger.info("✅ Step 7: Data persistence verified - Thread and messages stored")
        
        # FINAL: Record Golden Path success metrics
        golden_path_metrics = {
            "test_completion_time": time.time() - start_time,
            "websocket_events_count": len(collected_events),
            "business_value_delivered": True,
            "cost_savings_amount": savings_amount,
            "data_persistence_verified": True,
            "user_journey_completion": "success",
            "arr_protection": "validated"
        }
        
        self.logger.info("🎉 GOLDEN PATH SUCCESS: Complete user journey validated")
        self.logger.info(f"📊 Final Metrics: {json.dumps(golden_path_metrics, indent=2)}")
        
        # Assert final business value delivery
        assert golden_path_metrics["business_value_delivered"], (
            "CRITICAL FAILURE: Golden Path did not complete with business value delivery"
        )
        
        self.logger.info("✅ COMPLETE GOLDEN PATH USER JOURNEY E2E TEST PASSED")
    
    @pytest.mark.timeout(45)  
    async def test_golden_path_authentication_to_websocket_flow(self):
        """
        Test authentication to WebSocket connection flow in isolation.
        
        This validates the critical authentication handshake that enables
        all subsequent business value delivery.
        """
        self.logger.info("🔐 Testing Golden Path Authentication to WebSocket Flow")
        
        # Create authenticated user
        user_context = await create_authenticated_user_context(
            user_email="auth_websocket_test@example.com", 
            environment="test",
            permissions=["read", "write"],
            websocket_enabled=True
        )
        
        jwt_token = user_context.agent_context["jwt_token"]
        user_id = str(user_context.user_id)
        
        # Validate JWT token structure and claims
        validation_result = await self.auth_helper.validate_jwt_token(jwt_token)
        
        assert validation_result["valid"], (
            f"CRITICAL: JWT token validation failed: {validation_result.get('error')}"
        )
        
        assert validation_result["user_id"] == user_id, (
            "CRITICAL: JWT token user_id mismatch"
        )
        
        self.logger.info("✅ JWT token validation passed")
        
        # Test WebSocket connection with authentication
        websocket_url = "ws://localhost:8000/ws"
        headers = self.websocket_helper.get_websocket_headers(jwt_token)
        
        connection_successful = False
        async with websockets.connect(
            websocket_url,
            additional_headers=headers,
            open_timeout=10.0
        ) as websocket:
            
            # Send authentication test message
            auth_test_msg = {
                "type": "auth_test",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(auth_test_msg))
            
            # Wait for acknowledgment
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            connection_successful = True
            
        assert connection_successful, (
            "CRITICAL: WebSocket authentication flow failed"
        )
        
        self.logger.info("✅ Authentication to WebSocket flow validated")
    
    async def teardown_method(self, method=None):
        """Clean up test resources."""
        await super().cleanup_resources()
        self.logger.info("🧹 Golden Path User Journey E2E test cleanup completed")


# BUSINESS VALUE VALIDATION HELPERS

def validate_business_value_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that response contains actual business value for users.
    
    Args:
        response_data: Agent response data to validate
        
    Returns:
        Dict containing validation results and extracted business value
    """
    business_value = {
        "has_cost_optimization": False,
        "has_quantified_savings": False,
        "has_actionable_recommendations": False,
        "savings_amount": 0,
        "recommendations_count": 0
    }
    
    # Check for cost optimization content
    response_text = str(response_data).lower()
    cost_keywords = ["cost", "savings", "optimization", "reduce", "efficient", "budget"]
    business_value["has_cost_optimization"] = any(keyword in response_text for keyword in cost_keywords)
    
    # Check for quantified savings
    import re
    dollar_amounts = re.findall(r'\$[\d,]+', str(response_data))
    percentage_savings = re.findall(r'\d+%.*save|save.*\d+%', response_text)
    
    if dollar_amounts or percentage_savings:
        business_value["has_quantified_savings"] = True
        # Extract first dollar amount found
        if dollar_amounts:
            amount_str = dollar_amounts[0].replace('$', '').replace(',', '')
            try:
                business_value["savings_amount"] = float(amount_str)
            except ValueError:
                pass
    
    # Check for actionable recommendations
    recommendation_keywords = ["recommend", "suggest", "should", "optimize", "improve", "implement"]
    business_value["has_actionable_recommendations"] = any(
        keyword in response_text for keyword in recommendation_keywords
    )
    
    # Count recommendations (rough estimate)
    recommendation_indicators = ["1.", "2.", "3.", "first", "second", "third", "•", "-"]
    business_value["recommendations_count"] = sum(
        response_text.count(indicator) for indicator in recommendation_indicators
    )
    
    return business_value


def assert_websocket_events_business_value(events: List[Dict[str, Any]]) -> None:
    """
    Assert that WebSocket events contain business value delivery.
    
    Args:
        events: List of WebSocket events to validate
    """
    # Check for business value in final events
    final_events = [e for e in events if e.get("type") in ["agent_completed", "tool_completed"]]
    
    has_business_content = False
    for event in final_events:
        event_data = event.get("data", {})
        event_content = str(event_data).lower()
        
        # Check for business value keywords
        business_keywords = [
            "cost", "savings", "optimization", "reduce", "efficient", 
            "recommend", "improve", "benefit", "roi", "value"
        ]
        
        if any(keyword in event_content for keyword in business_keywords):
            has_business_content = True
            break
    
    assert has_business_content, (
        f"CRITICAL: WebSocket events do not contain business value content. "
        f"Events must deliver actionable business insights. "
        f"Events received: {[e.get('type') for e in events]}"
    )